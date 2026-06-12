from rest_framework import serializers
from locations.models import Province, City, Country, DestinationCity, Port

class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ['id', 'name']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'province']

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name']

class DestinationCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinationCity
        fields = ['id', 'name', 'country']

class PortSerializer(serializers.ModelSerializer):
    # اگر فرانت‌اند دقیقاً کلید transport_mode را توقع دارد، آن را به port_type متصل می‌کنیم
    transport_mode = serializers.CharField(source='port_type', read_only=True)
    # اگر نیاز به آیدی کشور دارید، باید آن را از طریق شهر استخراج کنید
    country = serializers.IntegerField(source='city.country.id', read_only=True)

    class Meta:
        model = Port
        fields = ['id', 'name', 'country', 'city', 'transport_mode', 'port_type', 'code']
