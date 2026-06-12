from django.urls import path
from . import views

app_name = 'panel_api_v1'

urlpatterns = [
    # داشبورد فورواردر (آمارها و نمودارها)
    path('dashboard/', views.ForwarderDashboardAPIView.as_view(), name='forwarder-dashboard'),
    
    # لیست سفارشات ارجاع شده به فورواردر (با قابلیت فیلتر و جستجو)
    path('orders/', views.ForwarderOrderListAPIView.as_view(), name='forwarder-order-list'),
    
    # تغییر وضعیت یک سفارش خاص
    path('orders/<int:pk>/status/', views.ForwarderOrderStatusUpdateAPIView.as_view(), name='forwarder-order-status-update'),
]
