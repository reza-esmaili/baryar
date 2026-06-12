from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import openpyxl

from .models import Rate, RateTier, CargoType, CargoSubCategory, TransportMode

# ==========================================
# Forms & Mappings
# ==========================================

class CargoExcelImportForm(forms.Form):
    excel_file = forms.FileField(label="فایل اکسل (ستون‌ها: نوع حمل، دسته، زیرگروه، توضیح)")

TRANSPORT_MODE_MAP = {
    'هوایی': TransportMode.AIR,
    'air': TransportMode.AIR,
    'دریایی fcl': TransportMode.SEA_FCL,
    'sea_fcl': TransportMode.SEA_FCL,
    'دریایی lcl': TransportMode.SEA_LCL,
    'sea_lcl': TransportMode.SEA_LCL,
    'زمینی': TransportMode.LAND,
    'land': TransportMode.LAND,
    'ریلی': TransportMode.RAIL,
    'rail': TransportMode.RAIL,
}

# ==========================================
# Inlines
# ==========================================

class CargoSubCategoryInline(admin.TabularInline):
    """
    برای اینکه بتوانید در صفحه ساخت/ویرایش دسته اصلی، 
    به راحتی زیردسته‌های آن را هم مدیریت کنید.
    """
    model = CargoSubCategory
    extra = 1

class RateTierInline(admin.TabularInline):
    model = RateTier
    extra = 1
    
    fieldsets = (
        (None, {
            'fields': (
                ('pricing_unit', 'price'),
                ('weight_from', 'weight_to'),
                ('container_size', 'container_type'),
            ),
            'classes': ('tier-fields',),  
        }),
    )

# ==========================================
# Cargo Type & SubCategory Admin
# ==========================================

@admin.register(CargoType)
class CargoTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'transport_mode')
    list_filter = ('transport_mode',)
    search_fields = ('name',)
    inlines = [CargoSubCategoryInline]
    
    # قالب اختصاصی برای نمایش دکمه آپلود
    change_list_template = "admin/rate/cargotype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel), name='rate_cargotype_import_excel'),
        ]
        return custom_urls + urls

    def import_excel(self, request):
        if request.method == "POST":
            form = CargoExcelImportForm(request.POST, request.FILES)
            if form.is_valid():
                excel_file = request.FILES["excel_file"]
                try:
                    wb = openpyxl.load_workbook(excel_file, data_only=True)
                    sheet = wb.active
                    
                    count = 0
                    # فرض: سطر اول هدر است. ستون‌ها: 0:نوع حمل, 1:دسته اصلی, 2:زیرگروه, 3:توضیح
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        t_mode_raw = str(row[0]).strip().lower() if row[0] else None
                        category_name = str(row[1]).strip() if row[1] else None
                        subcategory_name = str(row[2]).strip() if row[2] else None
                        description = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                        
                        if t_mode_raw and category_name and subcategory_name:
                            t_mode = TRANSPORT_MODE_MAP.get(t_mode_raw)
                            
                            if t_mode:
                                # 1. بررسی وجود دسته اصلی و انتخاب اولین مورد برای جلوگیری از خطای دیتابیس تکراری
                                category_qs = CargoType.objects.filter(name=category_name, transport_mode=t_mode)
                                if category_qs.exists():
                                    category_obj = category_qs.first()
                                else:
                                    category_obj = CargoType.objects.create(name=category_name, transport_mode=t_mode)


                                
                                # 2. ایجاد یا به‌روزرسانی زیردسته به همراه توضیحات
                                CargoSubCategory.objects.update_or_create(
                                    category=category_obj,
                                    name=subcategory_name,
                                    defaults={'description': description}
                                )
                                count += 1
                                
                    messages.success(request, f"عملیات موفق. {count} ردیف کالا/زیرگروه بررسی و ثبت شد.")
                    return redirect("..")
                except Exception as e:
                    messages.error(request, f"خطا در پردازش فایل: {e}")
        else:
            form = CargoExcelImportForm()
            
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            opts=self.model._meta,
            title="آپلود فایل اکسل دسته‌بندی کالا",
        )
        # تغییر مسیر قالب به قالب اختصاصی آپلود دسته‌بندی کالا
        return render(request, "admin/rate/cargotype_excel_form.html", context)


@admin.register(CargoSubCategory)
class CargoSubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'description')
    list_filter = ('category__transport_mode', 'category')
    search_fields = ('name', 'category__name')


# ==========================================
# Rate Admin
# ==========================================

@admin.register(Rate)
class RateAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'transport_mode', 'is_currently_active', 'created_at')
    list_filter = ('transport_mode', 'is_active', 'origin_province', 'destination_country')
    search_fields = ('origin_city__name', 'destination_port__name')
    
    filter_horizontal = ('cargo_types',)
    
    fieldsets = (
        ('مالکیت و روش حمل', {
            'fields': ('forwarder', 'branch', 'transport_mode', 'cargo_types') 
        }),
        ('مبدا', {
            'fields': ('origin_province', 'origin_city')
        }),
        ('مقصد', {
            'fields': ('destination_country', 'destination_city', 'destination_port')
        }),
        ('وضعیت و اعتبار', {
            'fields': ('is_active', 'valid_until') 
        }),
    )
    
    inlines = [RateTierInline]

    class Media:
        js = ('admin/js/rate_form.js',)
