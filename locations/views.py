from django.http import JsonResponse
from .models import City, DestinationCity, Port

def load_cities(request):
    province_id = request.GET.get('province_id')
    cities = City.objects.filter(province_id=province_id, is_active=True).values('id', 'name')
    return JsonResponse(list(cities), safe=False)

def load_destination_cities(request):
    country_id = request.GET.get('country_id')
    dest_cities = DestinationCity.objects.filter(country_id=country_id, is_active=True).values('id', 'name')
    return JsonResponse(list(dest_cities), safe=False)
def load_ports(request):
    city_id = request.GET.get('city_id')
    transport_mode = request.GET.get('transport_mode')
    
    ports = Port.objects.none()
    
    if city_id:
        ports = Port.objects.filter(city_id=city_id, is_active=True)
        
        if transport_mode:
            # همسان‌سازی نوع حمل با نوع پورت دیتابیس
            if 'sea' in transport_mode.lower():
                ports = ports.filter(port_type='sea')
            elif 'air' in transport_mode.lower():
                ports = ports.filter(port_type='air')
            elif 'land' in transport_mode.lower():
                ports = ports.filter(port_type='land')

    return JsonResponse(list(ports.values('id', 'name')), safe=False)