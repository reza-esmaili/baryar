from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rates', views.RateViewSet, basename='rate')

urlpatterns = [
    # ویوهای Router (مدیریت نرخ)
    path('', include(router.urls)),
    
    # لیست کالاها
    path('cargo-types/', views.CargoTypeListView.as_view(), name='api_cargo_types'),

    # ویوهای بارگذاری اطلاعات پایه (جایگزین AJAX)
    path('locations/cities/', views.api_load_cities, name='api_cities'),
    path('locations/destination-cities/', views.api_load_destination_cities, name='api_destination_cities'),
    path('locations/ports/', views.api_load_ports, name='api_ports'),
]
