from rest_framework import viewsets, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rates.models import Rate, CargoType
from locations.models import City, DestinationCity, Port
from .serializers import RateSerializer, CargoTypeSerializer

class CargoTypeListView(generics.ListAPIView):
    """لیست انواع کالا و زیردسته‌های آن‌ها"""
    queryset = CargoType.objects.prefetch_related('subcategories').all()
    serializer_class = CargoTypeSerializer
    permission_classes = [AllowAny] # یا IsAuthenticated بسته به نیاز پروژه

class RateViewSet(viewsets.ModelViewSet):
    """مدیریت کامل نرخ‌ها (CRUD)"""
    serializer_class = RateSerializer
    permission_classes = [IsAuthenticated] # پیشنهاد می‌شود پرمیشن فورواردر قرار دهید

    def get_queryset(self):
        user = self.request.user
        # اگر می‌خواهید هر فورواردر فقط نرخ‌های خودش را ببیند:
        # return Rate.objects.filter(forwarder__user=user).prefetch_related('tiers', 'cargo_types')
        
        # برای تست تمام نرخ‌ها را برمی‌گردانیم:
        return Rate.objects.prefetch_related('tiers', 'cargo_types').all()

# === API های جایگزین AJAX برای دریافت اطلاعات پایه ===

@api_view(['GET'])
@permission_classes([AllowAny])
def api_load_cities(request):
    province_id = request.GET.get('province_id')
    if not province_id:
        return Response([])
    cities = City.objects.filter(province_id=province_id).values('id', 'name')
    return Response(list(cities))

@api_view(['GET'])
@permission_classes([AllowAny])
def api_load_destination_cities(request):
    country_id = request.GET.get('country_id')
    if not country_id:
        return Response([])
    cities = DestinationCity.objects.filter(country_id=country_id).values('id', 'name')
    return Response(list(cities))

@api_view(['GET'])
@permission_classes([AllowAny])
def api_load_ports(request):
    city_id = request.GET.get('city_id')
    transport_mode = request.GET.get('transport_mode')
    
    if not city_id:
        return Response([])

    ports = Port.objects.filter(city_id=city_id)

    if transport_mode == 'air':
        ports = ports.filter(port_type='air')
    elif transport_mode in ['sea_fcl', 'sea_lcl']:
        ports = ports.filter(port_type='sea')
    elif transport_mode in ['land', 'rail']:
        ports = ports.filter(port_type__in=['land', 'rail'])
    
    return Response(list(ports.values('id', 'name')))
