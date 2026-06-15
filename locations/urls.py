from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    
    # مسیرهای AJAX
    path('ajax/cities/', views.load_cities, name='ajax_load_cities'),
    path('ajax/destination-cities/', views.load_destination_cities, name='ajax_load_destination_cities'),
    path('ajax/ports/', views.load_ports, name='ajax_load_ports'),
]
