# rates/views.py

from django.http import JsonResponse
from locations.models import City, DestinationCity, Port

def load_cities(request):
    province_id = request.GET.get('province_id')
    cities = City.objects.filter(province_id=province_id).order_by('name')
    return JsonResponse(list(cities.values('id', 'name')), safe=False)

def load_destination_cities(request):
    country_id = request.GET.get('country_id')
    cities = DestinationCity.objects.filter(country_id=country_id).order_by('name')
    return JsonResponse(list(cities.values('id', 'name')), safe=False)

def load_ports(request):
    city_id = request.GET.get('city_id')
    transport_mode = request.GET.get('transport_mode')
    
    ports = Port.objects.filter(city_id=city_id)

    # فیلتر کردن پورتها بر اساس روش حمل
    if transport_mode == 'air':
        ports = ports.filter(port_type='air')
    elif transport_mode in ['sea_fcl', 'sea_lcl']:
        ports = ports.filter(port_type='sea')
    elif transport_mode in ['land', 'rail']: # اصلاح برای پوشش هر دو
        ports = ports.filter(port_type__in=['land', 'rail'])
    
    return JsonResponse(list(ports.values('id', 'name')), safe=False)
