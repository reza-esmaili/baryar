from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('rates/', include('rates.urls')), 
    path('panel/', include('panel.urls', namespace='forwarder_panel')),
    path('auth/', include('customer.urls', namespace='customer')),
    
    # مسیر جدید برای اپلیکیشن سفارشات/درخواست‌های مشتری
    path('orders/', include('orders.urls', namespace='orders')), 
    path('locations/', include('locations.urls')),
    path('api/v1/orders/', include('orders.api.v1.urls')),
    path('api/v1/locations/', include('locations.api.v1.urls')),
    path('api/v1/accounts/', include('accounts.api.v1.urls')),
    path('api/v1/panel/', include('panel.api.v1.urls')),
    path('api/v1/rates/', include('rates.api.v1.urls')),


]
