from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # مرحله اول
    path('request/new/', views.create_cargo_request, name='create_request'),
    path('ajax/calculate-rates/', views.ajax_calculate_rates, name='ajax_calculate_rates'), 
    
    # ثبت پیش‌نویس بعد از انتخاب نرخ
    path('request/submit/', views.submit_order, name='submit_order'), 
    
    # مرحله دوم (تکمیل اطلاعات)
    path('request/<int:order_id>/complete/', views.complete_order_details, name='complete_order_details'),
    
    # AJAX loaders
    path('ajax/cargo-types/', views.load_cargo_types, name='ajax_load_cargo_types'),
    path('ajax/cargo-subcategories/', views.load_cargo_subcategories, name='ajax_load_cargo_subcategories'),
    
    # یک صفحه موفقیت تستی (اگر قبلا ساخته‌اید، این خط را حذف یا ویرایش کنید)
    # path('request/success/', views.order_success_page, name='order_success_page'),
]
