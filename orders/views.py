from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .forms import CargoRequestForm, CargoDimensionFormSet, OrderCompletionForm
from .services import calculate_and_match_rates , calculate_extra_charge, money
from .models import CargoRequest, OrderStatus, OrderHistory
from django.utils import timezone
from rates.models import CargoType, Rate, CargoSubCategory , ExtraChargeType
from documents.services import sync_order_required_documents ,OrderDocument
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from decimal import Decimal

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
                    'actual_weight': match_data.get('actual_weight', 0),        # اضافه شد
                    'volumetric_weight': match_data.get('volumetric_weight', 0), # اضافه شد
                    'chargeable_weight': match_data.get('chargeable_weight', 0),
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

        if form.is_valid() and selected_rate_id:

            is_fcl = form.cleaned_data.get('transport_mode') in ['sea_fcl', 'FCL']

            if is_fcl or formset.is_valid():

                # داده‌های ابعاد برای سرویس محاسبه
                dimensions_data = [] if is_fcl else formset.cleaned_data

                # محاسبه مجدد نرخ‌ها در سرور (برای جلوگیری از دستکاری قیمت)
                match_data = calculate_and_match_rates(
                    form.cleaned_data,
                    dimensions_data
                )

                selected_result = None

                for item in match_data["results"]:
                    if str(item["rate_id"]) == str(selected_rate_id):
                        selected_result = item
                        break

                if not selected_result:
                    messages.error(request, "نرخ انتخاب شده معتبر نیست یا منقضی شده است.")
                    return redirect('orders:create_request')

                cargo_request = form.save(commit=False)
                cargo_request.customer = request.user

                # دریافت شیء نرخ
                rate = get_object_or_404(Rate, id=selected_rate_id)

                # اعتبارسنجی امنیتی
                if rate.transport_mode != cargo_request.transport_mode:
                    messages.error(request, "نرخ انتخاب‌شده با روش حمل سفارش مطابقت ندارد.")
                    return redirect('orders:create_request')

                if rate.shipping_procedure != cargo_request.shipping_procedure:
                    messages.error(request, "نرخ انتخاب‌شده با رویه ارسال سفارش مطابقت ندارد.")
                    return redirect('orders:create_request')

                cargo_request.selected_rate = rate
                cargo_request.needs_packaging = form.cleaned_data.get('needs_packaging', False)
                cargo_request.needs_doorstep_packaging = False


                # ذخیره وزن محاسبه شده
                cargo_request.chargeable_weight = match_data["chargeable_weight"]

                # ذخیره breakdown قیمت
                cargo_request.base_shipping_price = selected_result["base_shipping_price"]
                cargo_request.packaging_price = selected_result["packaging_price"]
                cargo_request.doorstep_packaging_price = selected_result["doorstep_packaging_price"]
                cargo_request.vat_amount = selected_result["vat_amount"]
                cargo_request.price_subtotal = selected_result["subtotal"]

                # قیمت نهایی
                cargo_request.final_price = selected_result["total_price"]

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

                # ثبت تاریخچه
                OrderHistory.objects.create(
                    order=cargo_request,
                    changed_by=request.user,
                    note="نرخ انتخاب شد و سفارش به عنوان پیش‌نویس ثبت گردید."
                )

                return redirect(
                    'orders:complete_order_details',
                    order_id=cargo_request.id
                )

    return redirect('orders:create_request')

@login_required
def complete_order_details(request, order_id):
    cargo_request = get_object_or_404(
        CargoRequest,
        id=order_id,
        customer=request.user,
    )
    selected_rate = cargo_request.selected_rate

    doorstep_option = None

    if selected_rate and selected_rate.doorstep_packaging_charge_type != ExtraChargeType.NOT_AVAILABLE:
        doorstep_amount = calculate_extra_charge(
            selected_rate.doorstep_packaging_charge_type,
            selected_rate.doorstep_packaging_price,
            cargo_request.chargeable_weight
        )

        if selected_rate.doorstep_packaging_charge_type == ExtraChargeType.FREE:
            doorstep_label = "رایگان"
        elif selected_rate.doorstep_packaging_charge_type == ExtraChargeType.FIXED:
            doorstep_label = f"{money(doorstep_amount):,} ریال"
            doorstep_hint = "هزینه ثابت"
        elif selected_rate.doorstep_packaging_charge_type == ExtraChargeType.PER_KG:
            doorstep_label = f"{money(doorstep_amount):,} ریال"
            doorstep_hint = f"بر اساس وزن محاسبه‌شده: {cargo_request.chargeable_weight} کیلوگرم"
        else:
            doorstep_label = ""
            doorstep_hint = ""

        doorstep_option = {
            "amount": doorstep_amount,
            "label": doorstep_label,
            "hint": doorstep_hint if selected_rate.doorstep_packaging_charge_type != ExtraChargeType.FREE else "",
            "charge_type": selected_rate.doorstep_packaging_charge_type,
        }


    # اطمینان از ساخت مدارک موردنیاز
    sync_order_required_documents(cargo_request)

    if request.method == "POST":
        form = OrderCompletionForm(
            request.POST,
            request.FILES,
            instance=cargo_request,
            user=request.user
        )

        if form.is_valid():
            order = form.save(commit=False)

            order.sender_city = order.origin_city
            order.sender_province = order.origin_city.province

            if form.is_valid():
                order = form.save(commit=False)

                order.sender_city = order.origin_city
                order.sender_province = order.origin_city.province

                wants_doorstep = request.POST.get("needs_doorstep_packaging") == "on"

                order.needs_doorstep_packaging = False
                order.doorstep_packaging_price = 0

                if wants_doorstep and order.selected_rate:
                    rate = order.selected_rate

                    if rate.doorstep_packaging_charge_type != ExtraChargeType.NOT_AVAILABLE:
                        doorstep_amount = calculate_extra_charge(
                            rate.doorstep_packaging_charge_type,
                            rate.doorstep_packaging_price,
                            order.chargeable_weight
                        )

                        order.needs_doorstep_packaging = True
                        order.doorstep_packaging_price = money(doorstep_amount)

                        base_shipping_price = Decimal(str(order.base_shipping_price or 0))
                        packaging_price = Decimal(str(order.packaging_price or 0))
                        doorstep_price = Decimal(str(order.doorstep_packaging_price or 0))

                        subtotal = base_shipping_price + packaging_price + doorstep_price

                        if rate.add_vat:
                            vat_amount = subtotal * Decimal("0.10")
                        else:
                            vat_amount = Decimal("0.00")

                        order.price_subtotal = money(subtotal)
                        order.vat_amount = money(vat_amount)
                        order.final_price = money(subtotal + vat_amount)

                order.status = OrderStatus.PENDING

                order.save()
                form.save_m2m()


            # sync دوباره مدارک
            sync_order_required_documents(order)

            documents = OrderDocument.objects.select_related(
                "document_type"
            ).filter(order=order)

            # ذخیره فایل‌ها
            for doc in documents:
                uploaded_file = request.FILES.get(f"doc_{doc.id}")

                if uploaded_file:
                    doc.file = uploaded_file
                    doc.uploaded_by = request.user
                    doc.status = "uploaded"
                    doc.save()

            # ثبت تاریخچه
            OrderHistory.objects.create(
                order=order,
                changed_by=request.user,
                note="اطلاعات سفارش تکمیل و مدارک بارگذاری شد و سفارش ثبت نهایی گردید."
            )

            return redirect("customer:order_detail", pk=order.id)
    else:
        form = OrderCompletionForm(
            instance=cargo_request,
            user=request.user
        )

    documents = OrderDocument.objects.select_related(
        "document_type"
    ).filter(
        order=cargo_request
    ).order_by("document_type__title")

    return render(
        request,
        "customer_panel/complete_request.html",
        {
            "form": form,
            "cargo_request": cargo_request,
            "documents": documents,
            "doorstep_option": doorstep_option,
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


def generate_order_invoice_pdf(request, order_id):
    order = get_object_or_404(CargoRequest, id=order_id)
    
    context = {
        'order': order,
        'today': timezone.now(),
        'base_url': request.build_absolute_uri('/')[:-1] # برای پیدا کردن آدرس کامل فایل‌های استاتیک
    }

    html_string = render_to_string('orders/pdf/invoice_template.html', context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Invoice-{order.id}.pdf"'

    # اضافه کردن آدرس اصلی سایت برای بارگذاری صحیح استایل‌ها
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    
    return response
