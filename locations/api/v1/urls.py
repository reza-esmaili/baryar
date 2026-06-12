from django.urls import path
from . import views

app_name = 'locations_api_v1'

urlpatterns = [
    path('provinces/', views.ProvinceListAPIView.as_view(), name='province-list'),
    path('cities/', views.CityListAPIView.as_view(), name='city-list'),
    path('countries/', views.CountryListAPIView.as_view(), name='country-list'),
    path('destination-cities/', views.DestinationCityListAPIView.as_view(), name='destination-city-list'),
    path('ports/', views.PortListAPIView.as_view(), name='port-list'),
]
