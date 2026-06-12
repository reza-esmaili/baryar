from django.urls import path
from .views import CalculateRatesAPIView, CargoRequestListCreateAPIView, CargoRequestDetailAPIView

app_name = 'orders_api_v1'

urlpatterns = [
    # محاسبه نرخ (بدون ذخیره در دیتابیس)
    path('calculate-rates/', CalculateRatesAPIView.as_view(), name='calculate_rates'),
    
    # مدیریت سفارشات (ایجاد و لیست)
    path('requests/', CargoRequestListCreateAPIView.as_view(), name='cargo_request_list_create'),
    path('requests/<int:pk>/', CargoRequestDetailAPIView.as_view(), name='cargo_request_detail'),
]
