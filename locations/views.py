from django.http import JsonResponse
from .models import Country, Province, City, DestinationCity, Port


def load_provinces(request):
    country_id = request.GET.get("country_id")

    provinces = Province.objects.none()

    if country_id:
        provinces = Province.objects.filter(
            country_id=country_id,
            is_active=True
        ).order_by("name")

    return JsonResponse(list(provinces.values("id", "name")), safe=False)


def load_cities(request):
    province_id = request.GET.get("province_id")

    cities = City.objects.none()

    if province_id:
        cities = City.objects.filter(
            province_id=province_id,
            is_active=True
        ).order_by("name")

    return JsonResponse(list(cities.values("id", "name")), safe=False)


def load_destination_cities(request):
    country_id = request.GET.get("country_id")

    dest_cities = DestinationCity.objects.none()

    if country_id:
        dest_cities = DestinationCity.objects.filter(
            country_id=country_id,
            is_active=True
        ).order_by("name")

    return JsonResponse(list(dest_cities.values("id", "name")), safe=False)


def load_ports(request):
    city_id = request.GET.get("city_id")
    transport_mode = request.GET.get("transport_mode")

    ports = Port.objects.none()

    if city_id:
        ports = Port.objects.filter(city_id=city_id, is_active=True)

        if transport_mode:
            if transport_mode == "air":
                ports = ports.filter(port_type="air")
            elif transport_mode in ["sea_fcl", "sea_lcl"]:
                ports = ports.filter(port_type="sea")
            elif transport_mode == "land":
                ports = ports.filter(port_type="land")
            elif transport_mode == "rail":
                ports = ports.filter(port_type="rail")

    return JsonResponse(list(ports.values("id", "name")), safe=False)
