from rest_framework import generics, permissions, status
from rest_framework.response import Response
from orders.models import CargoRequest
from .serializers import CargoRequestSerializer, RateCalculationRequestSerializer
from orders.services import calculate_and_match_rates  # از کامنت خارج شد

class CalculateRatesAPIView(generics.GenericAPIView):
    serializer_class = RateCalculationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            dimensions = validated_data.get('dimensions', [])
            
            # فراخوانی سرویس محاسبه
            result = calculate_and_match_rates(validated_data, dimensions)
            
            return Response({"message": "نرخ محاسبه شد", "data": result}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CargoRequestListCreateAPIView(generics.ListCreateAPIView):
    # کدهای قبلی شما... (بدون تغییر)
    serializer_class = CargoRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CargoRequest.objects.filter(customer=self.request.user).order_by('-created_at')

class CargoRequestDetailAPIView(generics.RetrieveUpdateAPIView):
    # کدهای قبلی شما... (بدون تغییر)
    serializer_class = CargoRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CargoRequest.objects.filter(customer=self.request.user)
