from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import CargoRequestForm, CargoDimensionFormSet, OrderCompletionForm
from .services import calculate_and_match_rates
from .models import CargoRequest, OrderStatus, OrderHistory
from rates.models import CargoType, Rate, CargoSubCategory

@login_required
def create_cargo_request(request):
    """مرحله اول: فقط رندر کردن فرم خالی برای نمایش به کاربر"""
    form = CargoRequestForm()
    formset = CargoDimensionFormSet()

    return render(request, 'customer_panel/create_request.html', {
        'form': form,
        'formset': formset
    })

@login_required
def ajax_calculate_rates(request):
    """دریافت داده‌های فرم با AJAX و برگرداندن لیست قیمت‌ها بدون ذخیره در دیتابیس"""
    if request.method == 'POST':
        form = CargoRequestForm(request.POST)
        formset = CargoDimensionFormSet(request.POST)
        
        if form.is_valid():
            is_fcl = form.cleaned_data.get('transport_mode') in ['sea_fcl', 'FCL']
            
            if is_fcl or formset.is_valid():
                dimensions_data = [] if is_fcl else formset.cleaned_data
                
                # فراخوانی سرویس مچینگ با داده‌های خام
                match_data = calculate_and_match_rates(form.cleaned_data, dimensions_data)
                
                return JsonResponse({
                    'success': True,
                    'chargeable_weight': match_data['chargeable_weight'],
                    'rates': match_data['results']
                })
        
        return JsonResponse({'success': False, 'errors': form.errors})
        
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def submit_order(request):
    """وقتی کاربر یکی از نرخ‌ها را انتخاب کرد، داده‌ها را به عنوان پیش‌نویس (DRAFT) ذخیره می‌کند"""
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
                
                rate = get_object_or_404(Rate, id=selected_rate_id)
                cargo_request.selected_rate = rate
                cargo_request.chargeable_weight = chargeable_weight
                cargo_request.final_price = final_price
                
                # --- تغییر مهم: وضعیت به جای PENDING روی DRAFT تنظیم می‌شود ---
                cargo_request.status = OrderStatus.DRAFT
                
                if is_fcl:
                    cargo_request.container_size = form.cleaned_data.get('container_size')
                    cargo_request.container_type = form.cleaned_data.get('container_type')
                    cargo_request.container_count = form.cleaned_data.get('container_count')
                    
                cargo_request.save()
                
                if not is_fcl:
                    dimensions = formset.save(commit=False)
                    for dim in dimensions:
                        dim.cargo_request = cargo_request
                        dim.save()

                # ثبت اولین لاگ در تاریخچه
                OrderHistory.objects.create(
                    order=cargo_request,
                    changed_by=request.user,
                    note="نرخ انتخاب شد و سفارش به عنوان پیش‌نویس ثبت گردید."
                )
                    
                # هدایت به مرحله دوم (تکمیل اطلاعات)
                return redirect('orders:complete_order_details', order_id=cargo_request.id) 
                
    return redirect('orders:create_request')

@login_required
def complete_order_details(request, order_id):
    cargo_request = get_object_or_404(
        CargoRequest,
        id=order_id,
        customer=request.user,
        status=OrderStatus.DRAFT,
    )

    if request.method == "POST":
        form = OrderCompletionForm(request.POST, instance=cargo_request, user=request.user)

        if form.is_valid():
            order = form.save(commit=False)

            # پر کردن دستی مقادیر قفل شده
            order.sender_city = order.origin_city
            order.sender_province = order.origin_city.province

            order.status = OrderStatus.PENDING
            order.save()
            form.save_m2m()

            OrderHistory.objects.create(
                order=order,
                changed_by=request.user,
                note="اطلاعات تکمیلی وارد شد و سفارش برای فورواردر ارسال گردید.",
            )

            return redirect("customer:order_list")

    else:
        form = OrderCompletionForm(instance=cargo_request, user=request.user)

    national_id = ""

    if hasattr(request.user, "customer_profile"):
        national_id = request.user.customer_profile.national_code
    elif hasattr(request.user, "customer_company_profile"):
        national_id = request.user.customer_company_profile.national_id

    return render(
        request,
        "customer_panel/complete_request.html",
        {
            "form": form,
            "cargo_request": cargo_request,
            "user_phone": request.user.mobile,
            "user_national_id": national_id,
        },
    )

def load_cargo_types(request):
    transport_mode = request.GET.get('transport_mode')
    if transport_mode:
        cargo_types = CargoType.objects.filter(transport_mode=transport_mode).values('id', 'name')
        return JsonResponse(list(cargo_types), safe=False)
    return JsonResponse([], safe=False)

def load_cargo_subcategories(request):
    """لودر AJAX برای زیردسته‌های کالا در صورت نیاز به لود داینامیک"""
    category_id = request.GET.get('category_id')
    if category_id:
        subs = CargoSubCategory.objects.filter(category_id=category_id).values('id', 'name')
        return JsonResponse(list(subs), safe=False)
    return JsonResponse([], safe=False)