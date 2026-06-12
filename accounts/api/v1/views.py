from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from accounts.models import User
from .serializers import (
    CustomTokenObtainPairSerializer, 
    RegisterSerializer, 
    UserProfileSerializer
)

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    API لاگین: دریافت شماره موبایل و رمز عبور و برگرداندن Access Token و Refresh Token
    """
    serializer_class = CustomTokenObtainPairSerializer

class RegisterAPIView(generics.CreateAPIView):
    """
    API ثبت‌نام کاربر جدید (مشتری یا فورواردر بسته به role ارسالی)
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    API دریافت و ویرایش اطلاعات پایه کاربر لاگین شده
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
from rest_framework.views import APIView
from rest_framework.response import Response

class CheckMobileAPIView(APIView):
    """
    API بررسی وجود شماره موبایل در سیستم
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        mobile = request.data.get('mobile')
        if not mobile:
            return Response({"error": "شماره موبایل الزامی است."}, status=400)
        
        exists = User.objects.filter(mobile=mobile).exists()
        return Response({"exists": exists})
