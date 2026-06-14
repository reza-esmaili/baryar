from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # JWT login با رمز عبور - حفظ شده
    path("login/", views.CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ثبت‌نام قبلی - حفظ شده
    path("register/", views.RegisterAPIView.as_view(), name="register"),

    # پروفایل
    path("profile/", views.UserProfileAPIView.as_view(), name="user_profile"),
    path("check-mobile/", views.CheckMobileAPIView.as_view(), name="check_mobile"),

    # OTP Register
    path("register/request-otp/", views.RequestRegisterOTPAPIView.as_view(), name="register_request_otp"),
    path("register/verify-otp/", views.VerifyRegisterOTPAPIView.as_view(), name="register_verify_otp"),

    # OTP Login
    path("login/request-otp/", views.RequestLoginOTPAPIView.as_view(), name="login_request_otp"),
    path("login/verify-otp/", views.VerifyLoginOTPAPIView.as_view(), name="login_verify_otp"),

    # OTP Password Reset
    path("password-reset/request-otp/", views.RequestPasswordResetOTPAPIView.as_view(), name="password_reset_request_otp"),
    path("password-reset/verify-otp/", views.VerifyPasswordResetOTPAPIView.as_view(), name="password_reset_verify_otp"),
]
