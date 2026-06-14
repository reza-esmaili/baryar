from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import User, OTPCode
from accounts.services import SMSIRException, check_otp_security
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    RequestRegisterOTPSerializer,
    VerifyRegisterOTPSerializer,
    RequestLoginOTPSerializer,
    VerifyLoginOTPSerializer,
    RequestPasswordResetOTPSerializer,
    VerifyPasswordResetOTPSerializer,
)


def build_token_response(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "mobile": user.mobile,
            "role": user.role,
        },
    }


def perform_security_check(mobile, purpose):
    requires_captcha, attempts = check_otp_security(mobile, purpose)

    if requires_captcha:
        return Response(
            {
                "detail": "تعداد تلاش‌های ناموفق زیاد است. لطفاً کپچا را تکمیل کنید.",
                "require_captcha": True,
                "code": "captcha_required",
                "attempts": attempts,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    return None


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    ورود قبلی با شماره موبایل و رمز عبور.
    این بخش حفظ شده و برای Flutter/JWT همچنان کار می‌کند.
    """
    serializer_class = CustomTokenObtainPairSerializer


class RegisterAPIView(generics.CreateAPIView):
    """
    ثبت‌نام قبلی با رمز عبور.
    برای جلوگیری از خراب شدن کلاینت‌های قبلی حفظ شده است.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CheckMobileAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")

        if not mobile:
            return Response(
                {"error": "شماره موبایل الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mobile = OTPCode.normalize_mobile(mobile)
        exists = User.objects.filter(mobile=mobile).exists()

        return Response({"exists": exists})


class BaseRequestOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = serializer.save()
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except SMSIRException as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(result, status=status.HTTP_200_OK)


class BaseVerifyOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None
    purpose = None

    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")

        security_error = perform_security_check(mobile, self.purpose)
        if security_error:
            return security_error

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return self.handle_success(serializer)

    def handle_success(self, serializer):
        raise NotImplementedError


class RequestRegisterOTPAPIView(BaseRequestOTPAPIView):
    serializer_class = RequestRegisterOTPSerializer


class VerifyRegisterOTPAPIView(BaseVerifyOTPAPIView):
    serializer_class = VerifyRegisterOTPSerializer
    purpose = OTPCode.Purpose.REGISTER

    def handle_success(self, serializer):
        user = serializer.save()
        return Response(build_token_response(user), status=status.HTTP_201_CREATED)


class RequestLoginOTPAPIView(BaseRequestOTPAPIView):
    serializer_class = RequestLoginOTPSerializer


class VerifyLoginOTPAPIView(BaseVerifyOTPAPIView):
    serializer_class = VerifyLoginOTPSerializer
    purpose = OTPCode.Purpose.LOGIN

    def handle_success(self, serializer):
        user = serializer.validated_data["user"]
        return Response(build_token_response(user), status=status.HTTP_200_OK)


class RequestPasswordResetOTPAPIView(BaseRequestOTPAPIView):
    serializer_class = RequestPasswordResetOTPSerializer


class VerifyPasswordResetOTPAPIView(BaseVerifyOTPAPIView):
    serializer_class = VerifyPasswordResetOTPSerializer
    purpose = OTPCode.Purpose.PASSWORD_RESET

    def handle_success(self, serializer):
        serializer.save()
        return Response(
            {"message": "رمز عبور با موفقیت تغییر کرد."},
            status=status.HTTP_200_OK,
        )
