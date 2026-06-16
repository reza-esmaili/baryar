from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # مرحله اول
    path("request/new/", views.create_cargo_request, name="create_request"),
    path("ajax/calculate-rates/", views.ajax_calculate_rates, name="ajax_calculate_rates"),

    # ثبت پیش‌نویس بعد از انتخاب نرخ
    path("request/submit/", views.submit_order, name="submit_order"),

    # مرحله دوم، تکمیل اطلاعات
    path("request/<int:order_id>/complete/", views.complete_order_details, name="complete_order_details"),

    # AJAX loaders
    path("ajax/cargo-types/", views.load_cargo_types, name="ajax_load_cargo_types"),
    path("ajax/cargo-subcategories/", views.load_cargo_subcategories, name="ajax_load_cargo_subcategories"),
    path('invoice/<int:order_id>/download/', views.generate_order_invoice_pdf, name='generate_invoice'),

]
