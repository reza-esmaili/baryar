from rest_framework import generics
from locations.models import Province, City, Country, DestinationCity, Port
from .serializers import (
    ProvinceSerializer, CitySerializer, CountrySerializer, 
    DestinationCitySerializer, PortSerializer
)

class ProvinceListAPIView(generics.ListAPIView):
    queryset = Province.objects.all()
    serializer_class = ProvinceSerializer

class CityListAPIView(generics.ListAPIView):
    serializer_class = CitySerializer

    def get_queryset(self):
        queryset = City.objects.all()
        province_id = self.request.query_params.get('province_id')
        if province_id:
            queryset = queryset.filter(province_id=province_id)
        return queryset

class CountryListAPIView(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

class DestinationCityListAPIView(generics.ListAPIView):
    serializer_class = DestinationCitySerializer

    def get_queryset(self):
        queryset = DestinationCity.objects.all()
        country_id = self.request.query_params.get('country_id')
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        return queryset

class PortListAPIView(generics.ListAPIView):
    serializer_class = PortSerializer

    def get_queryset(self):
        queryset = Port.objects.all()
        country_id = self.request.query_params.get('country_id')
        city_id = self.request.query_params.get('city_id')
        transport_mode = self.request.query_params.get('transport_mode')

        if country_id:
            # اصلاح: فیلتر کردن کشور از طریق شهر متصل به پورت
            queryset = queryset.filter(city__country_id=country_id)
            
        if city_id:
            queryset = queryset.filter(city_id=city_id)
            
        if transport_mode:
            # اصلاح: نام فیلد در مدل شما port_type است
            queryset = queryset.filter(port_type=transport_mode)
            
        return queryset
