from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User, OTPCode
from accounts.services import request_otp, verify_otp


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "mobile"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        if "mobile" in attrs:
            attrs["mobile"] = OTPCode.normalize_mobile(attrs["mobile"])

        data = super().validate(attrs)

        data.update({
            "user": {
                "id": self.user.id,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "mobile": self.user.mobile,
                "role": self.user.role,
            }
        })

        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["first_name", "last_name", "mobile", "password", "role"]
        extra_kwargs = {"role": {"required": False}}

    def validate_mobile(self, value):
        mobile = OTPCode.normalize_mobile(value)

        if not OTPCode.is_valid_mobile(mobile):
            raise serializers.ValidationError("شماره موبایل معتبر نیست.")

        if User.objects.filter(mobile=mobile).exists():
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است.")

        return mobile

    def create(self, validated_data):
        role = validated_data.get("role", User.Role.CUSTOMER)

        return User.objects.create_user(
            mobile=validated_data["mobile"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role=role,
        )


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "mobile", "email", "role"]
        read_only_fields = ["id", "mobile", "role"]


class RequestRegisterOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField()
    captcha_token = serializers.CharField(required=False, allow_blank=True)
    cf_turnstile_response = serializers.CharField(required=False, allow_blank=True)

    def validate_mobile(self, value):
        mobile = OTPCode.normalize_mobile(value)

        if not OTPCode.is_valid_mobile(mobile):
            raise serializers.ValidationError("شماره موبایل معتبر نیست.")

        if User.objects.filter(mobile=mobile).exists():
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است.")

        return mobile

    def save(self):
        return request_otp(
            mobile=self.validated_data["mobile"],
            purpose=OTPCode.Purpose.REGISTER,
        )


class VerifyRegisterOTPSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    mobile = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    code = serializers.CharField(max_length=6, min_length=6)
    captcha_token = serializers.CharField(required=False, allow_blank=True)
    cf_turnstile_response = serializers.CharField(required=False, allow_blank=True)

    def validate_mobile(self, value):
        mobile = OTPCode.normalize_mobile(value)

        if not OTPCode.is_valid_mobile(mobile):
            raise serializers.ValidationError("شماره موبایل معتبر نیست.")

        if User.objects.filter(mobile=mobile).exists():
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است.")

        return mobile

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("کد تایید باید عددی باشد.")
        return value

    def validate(self, attrs):
        ok = verify_otp(
            mobile=attrs["mobile"],
            purpose=OTPCode.Purpose.REGISTER,
            code=attrs["code"],
        )

        if not ok:
            raise serializers.ValidationError("کد تایید نامعتبر یا منقضی شده است.")

        return attrs

    def create(self, validated_data):
        validated_data.pop("code", None)
        validated_data.pop("captcha_token", None)
        validated_data.pop("cf_turnstile_response", None)

        role = validated_data.pop("role", User.Role.CUSTOMER)
        password = validated_data.pop("password")

        user = User(
            role=role,
            **validated_data,
        )
        user.set_password(password)
        user.save()
        return user


class RequestLoginOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField()

    def validate_mobile(self, value):
        mobile = OTPCode.normalize_mobile(value)

        if not OTPCode.is_valid_mobile(mobile):
            raise serializers.ValidationError("شماره موبایل معتبر نیست.")

        if not User.objects.filter(mobile=mobile, is_active=True).exists():
            raise serializers.ValidationError("کاربری با این شماره موبایل وجود ندارد.")

        return mobile

    def save(self):
        return request_otp(
            mobile=self.validated_data["mobile"],
            purpose=OTPCode.Purpose.LOGIN,
        )


class VerifyLoginOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField()
    code = serializers.CharField(max_length=6, min_length=6)
    captcha_token = serializers.CharField(required=False, allow_blank=True)
    cf_turnstile_response = serializers.CharField(required=False, allow_blank=True)

    def validate_mobile(self, value):
        return OTPCode.normalize_mobile(value)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("کد تایید باید عددی باشد.")
        return value

    def validate(self, attrs):
        mobile = attrs["mobile"]

        ok = verify_otp(
            mobile=mobile,
            purpose=OTPCode.Purpose.LOGIN,
            code=attrs["code"],
        )

        if not ok:
            raise serializers.ValidationError("کد تایید نامعتبر یا منقضی شده است.")

        try:
            user = User.objects.get(mobile=mobile, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("کاربر یافت نشد.")

        attrs["user"] = user
        return attrs


class RequestPasswordResetOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField()

    def validate_mobile(self, value):
        mobile = OTPCode.normalize_mobile(value)

        if not OTPCode.is_valid_mobile(mobile):
            raise serializers.ValidationError("شماره موبایل معتبر نیست.")

        if not User.objects.filter(mobile=mobile, is_active=True).exists():
            raise serializers.ValidationError("کاربری با این شماره موبایل وجود ندارد.")

        return mobile

    def save(self):
        return request_otp(
            mobile=self.validated_data["mobile"],
            purpose=OTPCode.Purpose.PASSWORD_RESET,
        )


class VerifyPasswordResetOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField()
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    captcha_token = serializers.CharField(required=False, allow_blank=True)
    cf_turnstile_response = serializers.CharField(required=False, allow_blank=True)

    def validate_mobile(self, value):
        return OTPCode.normalize_mobile(value)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("کد تایید باید عددی باشد.")
        return value

    def validate(self, attrs):
        ok = verify_otp(
            mobile=attrs["mobile"],
            purpose=OTPCode.Purpose.PASSWORD_RESET,
            code=attrs["code"],
        )

        if not ok:
            raise serializers.ValidationError("کد تایید نامعتبر یا منقضی شده است.")

        return attrs

    def save(self):
        user = User.objects.get(mobile=self.validated_data["mobile"], is_active=True)
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user
