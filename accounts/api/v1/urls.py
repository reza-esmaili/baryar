from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # ورود (دریافت توکن)
    path('login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # رفرش توکن
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # ثبت نام
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    # پروفایل کاربر
    path('profile/', views.UserProfileAPIView.as_view(), name='user_profile'),
    path('check-mobile/', views.CheckMobileAPIView.as_view(), name='check_mobile'),

]
