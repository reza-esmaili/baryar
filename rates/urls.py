# rates/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('ajax/load-cities/', views.load_cities, name='ajax_load_cities'),
    path('ajax/load-destination-cities/', views.load_destination_cities, name='ajax_load_destination_cities'),
    path('ajax/load-ports/', views.load_ports, name='ajax_load_ports'),
]

