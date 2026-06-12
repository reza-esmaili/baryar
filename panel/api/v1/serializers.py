from rest_framework import serializers
from orders.models import CargoRequest, OrderHistory

class ForwarderOrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.user.get_full_name', read_only=True)
    destination_port_name = serializers.CharField(source='destination_port.name', read_only=True)
    
    class Meta:
        model = CargoRequest
        fields = ['id', 'tracking_code', 'customer_name', 'transport_mode', 'destination_port_name', 'status', 'created_at', 'final_price']

class ForwarderOrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[]) # در ویو مقداردهی می‌شود
    note = serializers.CharField(required=False, allow_blank=True)
