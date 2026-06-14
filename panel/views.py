from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import RateForm, RateTierFormSet, StaffForm, BranchForm, ForwarderDocumentsForm
from accounts.models import User, IdentityDocument
from forwarders.models import ForwarderBranch, ForwarderStaff, ForwarderCompany

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from locations.models import Port, City
import json
from rates.models import Rate, CargoType
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.db import transaction
import io
import xlsxwriter
import pandas as pd
from django.db.models import Q
from orders.models import CargoRequest, OrderStatus, OrderHistory
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from rates.models import TransportMode
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncQuarter, TruncYear
import jdatetime
# ایمپورت‌های اضافه شده برای سطح دسترسی
from .decorators import forwarder_required
def get_forwarder_verification_status(user):
    """
    خروجی:
    - no_company: هنوز اطلاعات شرکت ثبت نشده
    - pending: شرکت ثبت شده ولی تایید نشده
    - verified: شرکت تایید شده
    - not_forwarder_admin: کاربر ادمین فورواردر نیست
    """
    if not user.is_authenticated or user.role != User.Role.FORWARDER_ADMIN:
        return "not_forwarder_admin", None

    try:
        company = user.forwarder_company
    except ForwarderCompany.DoesNotExist:
        return "no_company", None

    if company.is_verified and company.is_active:
        return "verified", company

    return "pending", company

@login_required
@forwarder_required
def documents_view(request):
    """
    صفحه مدارک و مستندات فورواردر.
    فورواردر بعد از ثبت‌نام اولیه وارد این صفحه می‌شود،
    اطلاعات شرکت و مدارک را ارسال می‌کند و تا تایید کارشناس
    اجازه استفاده از سایر بخش‌های پنل را ندارد.
    """
    user = request.user
    status, company = get_forwarder_verification_status(user)

    if status == "not_forwarder_admin":
        return HttpResponseForbidden("شما دسترسی مشاهده این صفحه را ندارید.")

    documents = IdentityDocument.objects.filter(user=user).order_by("-created_at")

    if request.method == "POST":
        form = ForwarderDocumentsForm(request.POST, request.FILES, user=user, company=company)

        if form.is_valid():
            with transaction.atomic():
                applicant_role = form.cleaned_data["applicant_role"]

                if applicant_role == ForwarderDocumentsForm.ApplicantRole.CEO:
                    ceo_first_name = user.first_name
                    ceo_last_name = user.last_name
                    ceo_mobile = user.mobile
                    ceo_national_code = form.cleaned_data["ceo_national_code"]
                else:
                    ceo_first_name = form.cleaned_data["ceo_first_name"]
                    ceo_last_name = form.cleaned_data["ceo_last_name"]
                    ceo_mobile = form.cleaned_data["ceo_mobile"]
                    ceo_national_code = form.cleaned_data["ceo_national_code"]

                company, created = ForwarderCompany.objects.update_or_create(
                    admin_user=user,
                    defaults={
                        "company_name": form.cleaned_data["company_name"],
                        "company_type": form.cleaned_data["company_type"],
                        "national_id": form.cleaned_data["national_id"],
                        "registration_number": form.cleaned_data["registration_number"],
                        "ceo_first_name": ceo_first_name,
                        "ceo_last_name": ceo_last_name,
                        "ceo_national_code": ceo_national_code,
                        "phone": form.cleaned_data["phone"],
                        "email": form.cleaned_data["email"],
                        "postal_code": form.cleaned_data["postal_code"],
                        "address": form.cleaned_data["address"],

                        # مهم:
                        # بعد از ارسال مدارک، شرکت فعال عملیاتی نیست تا کارشناس تایید کند.
                        "is_verified": False,
                        "is_active": False,
                    },
                )

                uploaded_docs = {
                    "articles_of_association": IdentityDocument.DocType.ARTICLES_OF_ASSOCIATION,
                    "establishment_notice": IdentityDocument.DocType.ESTABLISHMENT_NOTICE,
                    "latest_changes": IdentityDocument.DocType.LATEST_CHANGES,
                    "ceo_national_card": IdentityDocument.DocType.CEO_NATIONAL_CARD,
                }

                for file_field, doc_type in uploaded_docs.items():
                    uploaded_file = request.FILES.get(file_field)
                    if uploaded_file:
                        # اگر کاربر دوباره مدارک را ارسال کرد، مدرک قبلی از همان نوع رد/آرشیو منطقی ندارد
                        # اما برای سادگی، مدرک جدید ساخته می‌شود و مدارک قبلی باقی می‌مانند.
                        IdentityDocument.objects.create(
                            user=user,
                            doc_type=doc_type,
                            company=company,
                            file=uploaded_file,
                            status=IdentityDocument.Status.PENDING,
                        )

                messages.success(
                    request,
                    "اطلاعات و مدارک شما با موفقیت ثبت شد و در انتظار بررسی کارشناس قرار گرفت."
                )
                return redirect("forwarder_panel:documents")

        else:
            messages.error(request, "لطفاً خطاهای فرم را بررسی و اصلاح کنید.")

    else:
        form = ForwarderDocumentsForm(user=user, company=company)

    status, company = get_forwarder_verification_status(user)

    context = {
        "form": form,
        "company": company,
        "documents": documents,
        "verification_status": status,
        "registered_user": user,
    }

    return render(request, "forwarder_panel/documents.html", context)


@login_required
@forwarder_required
def rate_create_view(request):
    # دریافت لیست پورت‌ها برای فیلتر داینامیک در فرانت‌اند
    ports_data = list(Port.objects.values('id', 'name', 'port_type'))
    ports_json = json.dumps(ports_data)

    if request.method == 'POST':
        form = RateForm(request.POST)
        
        # ۱. مقداردهی مالک نرخ قبل از اعتبارسنجی (is_valid) تا خطای مدل رخ ندهد
        form.instance.forwarder = request.user.forwarder_company 
        
        # ۲. پاس دادن instance فرم اصلی به فرم‌ست
        formset = RateTierFormSet(request.POST, instance=form.instance)
        
        if form.is_valid() and formset.is_valid():
            # ۳. ذخیره مستقیم (دیگر نیازی به commit=False نیست)
            form.save()
            formset.save()
            
            messages.success(request, "نرخ با موفقیت ذخیره شد.")
            return redirect('forwarder_panel:rate_list')
    else:
        form = RateForm()
        formset = RateTierFormSet()

    return render(request, 'forwarder_panel/rate_form.html', {
        'form': form,
        'formset': formset,
        'ports_json': ports_json
    })


@login_required
@forwarder_required
def rate_list_view(request):
    forwarder_company = getattr(request.user, 'forwarder_company', None)
    
    if forwarder_company:
        rates = Rate.objects.filter(forwarder=forwarder_company).select_related(
            'destination_country', 'destination_city', 'destination_port'
        ).prefetch_related('cargo_types').order_by('-created_at')
        
        # دریافت مقادیر فیلتر از URL
        country_id = request.GET.get('country')
        city_id = request.GET.get('city')
        mode = request.GET.get('mode')
        cargo_id = request.GET.get('cargo')
        status = request.GET.get('status')
        
        # اعمال فیلترها
        if country_id:
            rates = rates.filter(destination_country_id=country_id)
        if city_id:
            rates = rates.filter(destination_city_id=city_id)
        if mode:
            rates = rates.filter(transport_mode=mode)
        if cargo_id:
            rates = rates.filter(cargo_types__id=cargo_id)
        if status in ['active', 'inactive']:
            rates = rates.filter(is_active=(status == 'active'))

        # استخراج داده‌های یکتا برای پر کردن دراپ‌داون‌های فیلتر
        filter_countries = Rate.objects.filter(forwarder=forwarder_company, destination_country__isnull=False).values('destination_country__id', 'destination_country__name').distinct()
        filter_cities = Rate.objects.filter(forwarder=forwarder_company, destination_city__isnull=False).values('destination_city__id', 'destination_city__name').distinct()
        filter_cargos = CargoType.objects.filter(rates__forwarder=forwarder_company).distinct()
        
        # دریافت نام‌های نمایشی روش‌های حمل
        transport_modes = []
        mode_choices = dict(Rate._meta.get_field('transport_mode').choices)
        used_modes = Rate.objects.filter(forwarder=forwarder_company).values_list('transport_mode', flat=True).distinct()
        for m in used_modes:
            if m in mode_choices:
                transport_modes.append({'id': m, 'name': mode_choices[m]})
                
    else:
        rates = []
        filter_countries = filter_cities = filter_cargos = transport_modes = []

    context = {
        'rates': rates,
        'filter_countries': filter_countries,
        'filter_cities': filter_cities,
        'filter_cargos': filter_cargos,
        'transport_modes': transport_modes,
    }
    return render(request, 'forwarder_panel/rate_list.html', context)


@login_required
@forwarder_required
@require_POST
def toggle_rate_status(request, rate_id):
    rate = get_object_or_404(Rate, id=rate_id, forwarder=getattr(request.user, 'forwarder_company', None))
    
    try:
        data = json.loads(request.body)
        is_active = data.get('is_active', False)
        
        rate.is_active = is_active
        rate.save()
        
        return JsonResponse({'success': True, 'is_active': rate.is_active})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@forwarder_required
@require_POST
def delete_rate(request, rate_id):
    rate = get_object_or_404(Rate, id=rate_id, forwarder=getattr(request.user, 'forwarder_company', None))
    
    try:
        rate.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


class RateDetailUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Rate
    form_class = RateForm
    template_name = 'forwarder_panel/rate_detail.html'
    success_url = reverse_lazy('forwarder_panel:rate_list')
    
    def test_func(self):
        allowed_roles = [
            User.Role.FORWARDER_ADMIN, 
            User.Role.FORWARDER_EXPERT, 
            User.Role.FORWARDER_FINANCE
        ]

        if self.request.user.role not in allowed_roles:
            return False

        if self.request.user.role == User.Role.FORWARDER_ADMIN:
            try:
                company = self.request.user.forwarder_company
            except ForwarderCompany.DoesNotExist:
                return False

            return company.is_verified and company.is_active

        staff_profile = getattr(self.request.user, "forwarder_staff", None)
        if staff_profile:
            return staff_profile.company.is_verified and staff_profile.company.is_active

        return False


    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            if self.request.user.role == User.Role.FORWARDER_ADMIN:
                messages.warning(self.request, "برای استفاده از این بخش، ابتدا مدارک شرکت باید تایید شود.")
                return redirect("forwarder_panel:documents")
            return HttpResponseForbidden("شما دسترسی مشاهده این صفحه را ندارید.")
        return super().handle_no_permission()

    
    def get_queryset(self):
        forwarder_company = getattr(self.request.user, 'forwarder_company', None)
        if forwarder_company:
            return Rate.objects.filter(forwarder=forwarder_company)
        return Rate.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ports_data = list(Port.objects.values('id', 'name', 'port_type'))
        context['ports_json'] = json.dumps(ports_data)
        
        if self.request.POST:
            context['formset'] = RateTierFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = RateTierFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        with transaction.atomic():
            self.object = form.save()
            
            if formset.is_valid():
                formset.instance = self.object
                formset.save()
            else:
                return self.render_to_response(self.get_context_data(form=form))
                
        messages.success(self.request, "تغییرات با موفقیت ذخیره شد.")
        return super().form_valid(form)


@login_required
@forwarder_required
def load_cargo_types(request):
    transport_mode = request.GET.get('transport_mode')
    print(f"درخواست AJAX برای نوع کالا دریافت شد. روش حمل: {transport_mode}")
    cargo_types_list = list(CargoType.objects.filter(transport_mode=transport_mode).values('id', 'name'))
    print(f"نتیجه فیلتر: {cargo_types_list}")
    return JsonResponse(cargo_types_list, safe=False)


@login_required
@forwarder_required
@require_POST
def rate_bulk_delete(request):
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        
        if not ids:
            return JsonResponse({'success': False, 'error': 'لیست شناسه‌ها خالی است.'}, status=400)

        forwarder_company = getattr(request.user, 'forwarder_company', None)
        
        if forwarder_company:
            Rate.objects.filter(id__in=ids, forwarder=forwarder_company).delete()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'}, status=403)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@forwarder_required
def download_rate_template_excel(request):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    ws_data = workbook.add_worksheet('فرم ورود نرخ‌ها')
    ws_source = workbook.add_worksheet('DataSources')
    
    shipping_methods = ['دریایی', 'هوایی', 'زمینی', 'ریلی']
    provinces = ['تهران', 'هرمزگان', 'آذربایجان غربی', 'خراسان رضوی'] 
    countries = ['ایران', 'امارات', 'آلمان', 'ترکیه', 'چین'] 
    cities = ['تهران', 'بندرعباس', 'دبی', 'فرانکفورت', 'استانبول', 'شانگهای']
    ports = ['جبل علی', 'بندر شهید رجایی', 'هامبورگ']
    cargo_types = ['عمومی', 'خطرناک', 'فاسدشدنی', 'دارویی']
    container_sizes = ['20ft', '40ft']
    container_types = ['Standard', 'High Cube', 'Reefer', 'Open Top']
    pricing_units = ['کانتینر', 'کیلوگرم', 'CBM', 'ماشین کامل']

    sources = [
        ('A', shipping_methods), ('B', provinces), ('C', cities), 
        ('D', countries), ('E', ports), ('F', cargo_types),
        ('G', container_sizes), ('H', container_types), ('I', pricing_units)
    ]
    
    for col_letter, data_list in sources:
        for row_num, item in enumerate(data_list):
            ws_source.write(f'{col_letter}{row_num + 1}', str(item))

    headers = [
        'روش حمل', 'استان مبدا', 'شهر مبدا', 'کشور مقصد', 'شهر مقصد', 
        'پورت مقصد', 'نوع کالا', 'اعتبار تا (YYYY-MM-DD)', 'از وزن', 'تا وزن', 
        'سایز کانتینر', 'نوع کانتینر', 'واحد قیمت‌گذاری', 'مبلغ'
    ]
    
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
    
    for col_num, header in enumerate(headers):
        ws_data.write(0, col_num, header, header_format)
        ws_data.set_column(col_num, col_num, 15) 

    max_rows = 500
    
    validations = {
        0:  ('A', len(shipping_methods)), 
        1:  ('B', len(provinces)),        
        2:  ('C', len(cities)),           
        3:  ('D', len(countries)),        
        4:  ('C', len(cities)),           
        5:  ('E', len(ports)),            
        6:  ('F', len(cargo_types)),      
        10: ('G', len(container_sizes)),  
        11: ('H', len(container_types)),  
        12: ('I', len(pricing_units)),    
    }

    for col_index, (source_col, items_count) in validations.items():
        if items_count > 0:
            ws_data.data_validation(1, col_index, max_rows, col_index, {
                'validate': 'list',
                'source': f'=DataSources!${source_col}$1:${source_col}${items_count}'
            })

    workbook.close()
    
    output.seek(0)
    response = HttpResponse(
        output.read(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Bulk_Rate_Template.xlsx"'
    return response


@login_required
@forwarder_required
def upload_rate_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        
        if not excel_file:
            messages.error(request, 'لطفاً یک فایل انتخاب کنید.')
            return redirect('forwarder_panel:rate_list')
            
        try:
            df = pd.read_excel(excel_file, sheet_name='فرم ورود نرخ‌ها')
            df = df.dropna(how='all')
            
            for index, row in df.iterrows():
                shipping_method = row.get('روش حمل')
                origin_province = row.get('استان مبدا')
                amount = row.get('مبلغ')
                
            messages.success(request, 'نرخ‌ها با موفقیت بارگذاری شدند.')
            
        except Exception as e:
            messages.error(request, f'خطا در پردازش فایل: {str(e)}')
            
        return redirect('forwarder_panel:rate_list')


@login_required
@forwarder_required
def branch_list_view(request):
    company = getattr(request.user, 'forwarder_company', None)
    branches = ForwarderBranch.objects.filter(company=company).order_by('-created_at')
    return render(request, 'forwarder_panel/branch_list.html', {'branches': branches})


@login_required
@forwarder_required
def branch_create_view(request):
    company = getattr(request.user, 'forwarder_company', None)
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save(forwarder_company=company)
            messages.success(request, "شعبه با موفقیت افزوده شد.")
            return redirect('forwarder_panel:branch_list')
    else:
        form = BranchForm()
    return render(request, 'forwarder_panel/branch_form.html', {'form': form})


@login_required
@forwarder_required
def branch_update_view(request, pk):
    company = getattr(request.user, 'forwarder_company', None)
    branch = get_object_or_404(ForwarderBranch, pk=pk, company=company)
    
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save(forwarder_company=company)
            messages.success(request, "تغییرات شعبه ذخیره شد.")
            return redirect('forwarder_panel:branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'forwarder_panel/branch_form.html', {'form': form, 'branch': branch})


@login_required
@forwarder_required
@require_POST
def toggle_branch_status(request, pk):
    company = getattr(request.user, 'forwarder_company', None)
    branch = get_object_or_404(ForwarderBranch, pk=pk, company=company)
    data = json.loads(request.body)
    branch.is_active = data.get('is_active', False)
    branch.save()
    return JsonResponse({'success': True, 'is_active': branch.is_active})


# --- بخش کارمندان (Staff) ---
@login_required
@forwarder_required
def staff_list_view(request):
    company = getattr(request.user, 'forwarder_company', None)
    staff = ForwarderStaff.objects.filter(company=company).select_related('user').order_by('-created_at')
    return render(request, 'forwarder_panel/staff_list.html', {'staff': staff})


@login_required
@forwarder_required
def staff_create_view(request):
    company = getattr(request.user, 'forwarder_company', None)
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save(forwarder_company=company)
            messages.success(request, "کارمند با موفقیت افزوده شد.")
            return redirect('forwarder_panel:staff_list')
    else:
        form = StaffForm()
    return render(request, 'forwarder_panel/staff_form.html', {'form': form})


@login_required
@forwarder_required
def load_cities(request):
    province_id = request.GET.get('province_id')
    if province_id:
        cities = City.objects.filter(province_id=province_id).order_by('name')
        city_list = list(cities.values('id', 'name'))
        return JsonResponse(city_list, safe=False)
    return JsonResponse([], safe=False)


# ==============================================================================
# مدیریت سفارشات فورواردر
# ==============================================================================
@login_required
@forwarder_required
def order_list_view(request):
    """
    نمایش لیست سفارشات مربوط به فورواردر، فیلترینگ و امکان تغییر وضعیت گروهی.
    """
    forwarder_company = getattr(request.user, 'forwarder_company', None)
    
    # -------------------------------------------------------------------------
    # بخش اول: پردازش درخواست‌های POST برای تغییر وضعیت گروهی
    # -------------------------------------------------------------------------
    if request.method == 'POST':
        new_status = request.POST.get('bulk_status')
        selected_orders = request.POST.getlist('selected_orders')
        
        if new_status and selected_orders:
            try:
                # استفاده از atomic برای اطمینان از انجام کامل یا لغو کامل تراکنش‌ها
                with transaction.atomic():
                    # فیلتر ایمن: فقط سفارشاتی که متعلق به شرکت این کاربر هستند آپدیت شوند
                    orders_to_update = CargoRequest.objects.filter(
                        id__in=selected_orders, 
                        selected_rate__forwarder=forwarder_company
                    )
                    
                    updated_count = 0
                    for order in orders_to_update:
                        old_status = order.status
                        
                        # در صورتی که وضعیت جدید با وضعیت قبلی تفاوت داشت اعمال شود
                        if old_status != new_status:
                            order.status = new_status
                            order.save(update_fields=['status'])
                            
                            # ثبت لاگ دقیق در OrderHistory مشابه با order_detail_view
                            OrderHistory.objects.create(
                                order=order,
                                changed_by=request.user,
                                field_name='status',
                                old_value=old_status,
                                new_value=new_status,
                                note="تغییر وضعیت گروهی از لیست سفارشات"
                            )
                            updated_count += 1
                            
                messages.success(request, f"وضعیت {updated_count} سفارش با موفقیت به‌روزرسانی شد.")
            except Exception as e:
                messages.error(request, f"خطا در بروزرسانی گروهی سفارشات: {e}")
        else:
            messages.warning(request, "لطفاً حداقل یک سفارش و یک وضعیت جدید برای اعمال انتخاب کنید.")
            
        # جلوگیری از ارسال مجدد فرم هنگام رفرش صفحه
        return redirect('forwarder_panel:order_list')

    # -------------------------------------------------------------------------
    # بخش دوم: پردازش درخواست‌های GET برای جستجو، فیلتر و رندر صفحه
    # -------------------------------------------------------------------------
    if forwarder_company:
        # دریافت پایه سفارشاتی که متعلق به این فورواردر است و پیش‌نویس نیستند
        orders = CargoRequest.objects.filter(
            selected_rate__forwarder=forwarder_company
        ).exclude(status=OrderStatus.DRAFT).select_related(
            'customer', 'destination_port', 'origin_city', 'selected_rate', 'cargo_type'
        ).order_by('-created_at')
        
        # استخراج پارامترهای GET از URL
        search_query = request.GET.get('q', '')
        country_id = request.GET.get('country')
        city_id = request.GET.get('city')
        mode = request.GET.get('mode')
        status = request.GET.get('status')
        
        # اعمال فیلتر جستجو (با استفاده از OR های متوالی)
        if search_query:
            orders = orders.filter(
                Q(id__icontains=search_query) |
                Q(sender_name__icontains=search_query) |
                Q(sender_national_id__icontains=search_query) |
                Q(sender_phone__icontains=search_query) |
                Q(customer__mobile__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query)
            )
            
        # اعمال فیلترهای دراپ‌داون
        if country_id:
            orders = orders.filter(destination_port__city__province__country_id=country_id)
        if city_id:
            orders = orders.filter(destination_port__city_id=city_id)
        if mode:
            orders = orders.filter(transport_mode=mode)
        if status:
            orders = orders.filter(status=status)

        # تهیه داده‌های لازم برای پر کردن فرم فیلترها (شهرهای دارای سفارش و وضعیت‌ها)
        city_ids = CargoRequest.objects.filter(
            selected_rate__forwarder=forwarder_company
        ).exclude(status=OrderStatus.DRAFT).values_list('destination_port__city_id', flat=True).distinct()
        
        filter_cities = City.objects.filter(id__in=city_ids)        
        transport_modes = [{'id': k, 'name': v} for k, v in CargoRequest._meta.get_field('transport_mode').choices]
        order_statuses = [{'id': k, 'name': v} for k, v in OrderStatus.choices if k != OrderStatus.DRAFT]
        
    else:
        orders = []
        filter_cities = transport_modes = order_statuses = []

    context = {
        'orders': orders,
        'filter_cities': filter_cities,
        'transport_modes': transport_modes,
        'order_statuses': order_statuses,
    }
    
    # اطمینان از بازگشت رندر برای درخواست‌های GET
    return render(request, 'forwarder_panel/order_list.html', context)


@login_required
@forwarder_required
def order_detail_view(request, order_id):
    forwarder_company = getattr(request.user, 'forwarder_company', None)
    order = get_object_or_404(
        CargoRequest, 
        id=order_id, 
        selected_rate__forwarder=forwarder_company
    )
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        note = request.POST.get('note', '')
        
        if new_status and new_status in dict(OrderStatus.choices):
            old_status = order.status
            order.status = new_status
            order.save()
            
            OrderHistory.objects.create(
                order=order,
                changed_by=request.user,
                field_name='status',
                old_value=old_status,
                new_value=new_status,
                note=note
            )
            messages.success(request, "وضعیت سفارش با موفقیت بروزرسانی شد.")
            return redirect('forwarder_panel:order_detail', order_id=order.id)

    return render(request, 'forwarder_panel/order_detail.html', {'order': order, 'statuses': OrderStatus.choices})

@login_required
@forwarder_required
def dashboard_view(request):
    forwarder_company = getattr(request.user, 'forwarder_company', None)
    
    # تاریخ ۷ روز پیش
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    # فیلتر سفارشات مرتبط با این فورواردر در ۷ روز گذشته (بدون در نظر گرفتن پیش‌نویس‌ها)
    recent_orders = CargoRequest.objects.filter(
        selected_rate__forwarder=forwarder_company,
        created_at__gte=seven_days_ago
    ).exclude(status=OrderStatus.DRAFT)
    
    # 1. تعداد کل سفارشات و مبلغ فروش در 7 روز گذشته
    total_orders_count = recent_orders.count()
    total_sales = recent_orders.aggregate(total=Sum('final_price'))['total'] or 0
    
    # 2. پرفروش‌ترین روش حمل در 7 روز گذشته
    top_transport_mode = recent_orders.values('transport_mode').annotate(
        order_count=Count('id'),
        total_sales=Sum('final_price')
    ).order_by('-order_count').first()
    
    # تبدیل کد روش حمل به نام نمایشی (مثلا sea_fcl به دریایی FCL)
    mode_choices = dict(TransportMode.choices)
    if top_transport_mode:
        top_transport_mode['display_name'] = mode_choices.get(top_transport_mode['transport_mode'], top_transport_mode['transport_mode'])
    
    # 3. پرفروش‌ترین مقصد در 7 روز گذشته
    top_destination = recent_orders.values('destination_port__city__name').annotate(
        order_count=Count('id'),
        total_sales=Sum('final_price')
    ).order_by('-order_count').first()

    # 4. آمار نرخ‌های فعال این فورواردر
    active_rates = Rate.objects.filter(forwarder=forwarder_company, is_active=True)
    total_active_rates = active_rates.count()
    
    # 5. گروه‌بندی نرخ‌ها بر اساس مسیر و روش حمل
    rates_by_route = active_rates.values(
        'origin_city__name', 
        'destination_city__name', 
        'transport_mode'
    ).annotate(
        rate_count=Count('id')
    ).order_by('-rate_count')

    # اضافه کردن نام نمایشی روش حمل به لیست نرخ‌ها
    for r in rates_by_route:
        r['mode_display'] = mode_choices.get(r['transport_mode'], r['transport_mode'])

    context = {
        'total_orders_count': total_orders_count,
        'total_sales': total_sales,
        'top_transport_mode': top_transport_mode,
        'top_destination': top_destination,
        'total_active_rates': total_active_rates,
        'rates_by_route': rates_by_route,
    }
    
    return render(request, 'forwarder_panel/dashboard.html', context)
@login_required
@forwarder_required
def get_sales_chart_data(request):
    """
    دریافت داده‌های نمودار فروش بر اساس بازه زمانی و تاریخ (فرمت تاریخ شمسی است).
    """
    forwarder_company = getattr(request.user, 'forwarder_company', None)
    
    # دریافت پارامترها از درخواست GET
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    interval = request.GET.get('interval', 'daily')

    # فیلتر پایه: سفارشات متعلق به این شرکت که پیش‌نویس نیستند
    orders = CargoRequest.objects.filter(
        selected_rate__forwarder=forwarder_company
    ).exclude(status=OrderStatus.DRAFT)

    # تبدیل تاریخ شمسی به میلادی و اعمال فیلتر تاریخ
    try:
        if start_date_str:
            y, m, d = map(int, start_date_str.split('/'))
            start_date = jdatetime.date(y, m, d).togregorian()
            orders = orders.filter(created_at__date__gte=start_date)
        
        if end_date_str:
            y, m, d = map(int, end_date_str.split('/'))
            end_date = jdatetime.date(y, m, d).togregorian()
            orders = orders.filter(created_at__date__lte=end_date)
    except Exception as e:
        return JsonResponse({'error': 'فرمت تاریخ نامعتبر است. لطفاً فرمت YYYY/MM/DD را رعایت کنید.'}, status=400)

    # انتخاب نوع گروه‌بندی (Truncation) بر اساس بازه زمانی
    trunc_mapping = {
        'daily': TruncDay('created_at'),
        'weekly': TruncWeek('created_at'),
        'monthly': TruncMonth('created_at'),
        'quarterly': TruncQuarter('created_at'),
        'yearly': TruncYear('created_at'),
    }
    
    trunc_func = trunc_mapping.get(interval, TruncDay('created_at'))

    # گروه‌بندی داده‌ها و محاسبه مجموع مبالغ (فروش)
    sales_data = orders.annotate(
        period=trunc_func
    ).values('period').annotate(
        total_sales=Sum('final_price')
    ).order_by('period')

    # آماده‌سازی آرایه‌ها برای خروجی JSON (فرانت‌اند)
    dates = []
    amounts = []

    for item in sales_data:
        if item['period']:
            # تبدیل مجدد تاریخ میلادی دیتابیس به رشته شمسی برای نمایش در نمودار
            jalali_date = jdatetime.datetime.fromgregorian(datetime=item['period']).strftime('%Y/%m/%d')
            dates.append(jalali_date)
            # اگر مقداری ثبت نشده بود صفر در نظر بگیرد
            amounts.append(item['total_sales'] or 0)

    return JsonResponse({
        'dates': dates,
        'amounts': amounts
    })
@login_required
@forwarder_required
def report_view(request):
    """
    نمایش صفحه اصلی گزارشات شامل نمودار فروش
    """
    return render(request, 'forwarder_panel/report.html')

