from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .forms import CargoRequestForm, CargoDimensionFormSet, OrderCompletionForm
from .services import calculate_and_match_rates
from .models import CargoRequest, OrderStatus, OrderHistory

from rates.models import CargoType, Rate, CargoSubCategory
from documents.services import sync_order_required_documents


@login_required
def create_cargo_request(request):
    """
    مرحله اول ثبت سفارش
    -------------------
    فقط فرم خالی درخواست بار و فرم ابعاد کالا را برای کاربر نمایش می‌دهد.
    در این مرحله هیچ داده‌ای در دیتابیس ذخیره نمی‌شود.
    """

    form = CargoRequestForm()
    formset = CargoDimensionFormSet()

    return render(request, 'customer_panel/create_request.html', {
        'form': form,
        'formset': formset
    })


@login_required
def ajax_calculate_rates(request):
    """
    محاسبه نرخ‌ها با AJAX
    ---------------------
    داده‌های فرم از طریق AJAX ارسال می‌شوند و بدون ذخیره در دیتابیس
    نرخ‌های قابل ارائه توسط فورواردرها محاسبه و برگردانده می‌شوند.
    """

    if request.method == 'POST':

        form = CargoRequestForm(request.POST)
        formset = CargoDimensionFormSet(request.POST)

        if form.is_valid():

            # بررسی اینکه حمل FCL است یا خیر
            is_fcl = form.cleaned_data.get('transport_mode') in ['sea_fcl', 'FCL']

            if is_fcl or formset.is_valid():

                # در حالت FCL ابعاد نداریم
                dimensions_data = [] if is_fcl else formset.cleaned_data

                # فراخوانی سرویس مچینگ نرخ
                match_data = calculate_and_match_rates(
                    form.cleaned_data,
                    dimensions_data
                )

                return JsonResponse({
                    'success': True,
                    'chargeable_weight': match_data['chargeable_weight'],
                    'rates': match_data['results']
                })

        return JsonResponse({
            'success': False,
            'errors': form.errors
        })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })


@login_required
def submit_order(request):
    """
    مرحله انتخاب نرخ
    ----------------
    وقتی کاربر یکی از نرخ‌ها را انتخاب می‌کند:
    - سفارش در دیتابیس ذخیره می‌شود
    - وضعیت آن DRAFT قرار می‌گیرد
    - سپس کاربر به مرحله تکمیل اطلاعات هدایت می‌شود
    """

    if request.method == 'POST':

        form = CargoRequestForm(request.POST)
        formset = CargoDimensionFormSet(request.POST)

        selected_rate_id = request.POST.get('selected_rate_id')
        chargeable_weight = request.POST.get('chargeable_weight')
        final_price = request.POST.get('final_price')

        if form.is_valid() and selected_rate_id:

            is_fcl = form.cleaned_data.get('transport_mode') in ['sea_fcl', 'FCL']

            if is_fcl or formset.is_valid():

                cargo_request = form.save(commit=False)
                cargo_request.customer = request.user

                # نرخ انتخاب شده
                rate = get_object_or_404(Rate, id=selected_rate_id)
                cargo_request.selected_rate = rate

                cargo_request.chargeable_weight = chargeable_weight
                cargo_request.final_price = final_price

                # سفارش هنوز نهایی نشده
                cargo_request.status = OrderStatus.DRAFT

                # اطلاعات کانتینر در حالت FCL
                if is_fcl:
                    cargo_request.container_size = form.cleaned_data.get('container_size')
                    cargo_request.container_type = form.cleaned_data.get('container_type')
                    cargo_request.container_count = form.cleaned_data.get('container_count')

                cargo_request.save()

                # ذخیره ابعاد در حالت LCL / AIR
                if not is_fcl:
                    dimensions = formset.save(commit=False)

                    for dim in dimensions:
                        dim.cargo_request = cargo_request
                        dim.save()

                # ثبت در تاریخچه سفارش
                OrderHistory.objects.create(
                    order=cargo_request,
                    changed_by=request.user,
                    note="نرخ انتخاب شد و سفارش به عنوان پیش‌نویس ثبت گردید."
                )

                # هدایت به مرحله تکمیل اطلاعات سفارش
                return redirect(
                    'orders:complete_order_details',
                    order_id=cargo_request.id
                )

    return redirect('orders:create_request')


@login_required
def complete_order_details(request, order_id):
    """
    مرحله تکمیل اطلاعات سفارش
    -------------------------
    کاربر اطلاعات فرستنده و جزئیات نهایی سفارش را وارد می‌کند.

    بعد از ذخیره:
    - مدارک مورد نیاز بر اساس Rule Engine ساخته می‌شوند
    - کاربر به صفحه آپلود مدارک هدایت می‌شود
    """

    cargo_request = get_object_or_404(
        CargoRequest,
        id=order_id,
        customer=request.user,
        status=OrderStatus.DRAFT,
    )

    if request.method == "POST":

        form = OrderCompletionForm(
            request.POST,
            instance=cargo_request,
            user=request.user
        )

        if form.is_valid():

            order = form.save(commit=False)

            # شهر مبدا به عنوان شهر فرستنده در نظر گرفته می‌شود
            order.sender_city = order.origin_city
            order.sender_province = order.origin_city.province

            # هنوز سفارش ارسال نشده (منتظر مدارک)
            order.status = OrderStatus.DRAFT

            order.save()
            form.save_m2m()

            # ایجاد لیست مدارک مورد نیاز
            sync_order_required_documents(order)

            # انتقال کاربر به صفحه آپلود مدارک
            return redirect(
                "documents:order_documents",
                order_id=order.id
            )

    else:
        form = OrderCompletionForm(
            instance=cargo_request,
            user=request.user
        )

    # بسیار مهم:
    # در هر حالت باید HttpResponse برگردانده شود
    return render(
        request,
        "customer_panel/complete_request.html",
        {
            "form": form,
            "cargo_request": cargo_request
        }
    )


def load_cargo_types(request):
    """
    AJAX Loader
    -----------
    دریافت دسته‌های کالا بر اساس نوع حمل
    (هوایی، دریایی، زمینی)
    """

    transport_mode = request.GET.get('transport_mode')

    if transport_mode:
        cargo_types = CargoType.objects.filter(
            transport_mode=transport_mode
        ).values('id', 'name')

        return JsonResponse(list(cargo_types), safe=False)

    return JsonResponse([], safe=False)


def load_cargo_subcategories(request):
    """
    AJAX Loader
    -----------
    دریافت زیر دسته‌های کالا بر اساس دسته اصلی
    """

    category_id = request.GET.get('category_id')

    if category_id:
        subs = CargoSubCategory.objects.filter(
            category_id=category_id
        ).values('id', 'name')

        return JsonResponse(list(subs), safe=False)

    return JsonResponse([], safe=False)
