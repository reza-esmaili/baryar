from rest_framework import serializers
from accounts.models import User, CustomerProfile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # اضافه کردن نقش کاربر به داخل توکن
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # برگرداندن اطلاعات پایه کاربر به همراه توکن در زمان لاگین
        data.update({
            'user': {
                'id': self.user.id,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'mobile': self.user.mobile,
                'role': self.user.role,
            }
        })
        return data

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'mobile', 'password', 'role']
        # نقش به صورت پیش‌فرض مشتری است اما می‌تواند توسط کلاینت برای ثبت‌نام فورواردر ارسال شود
        extra_kwargs = {'role': {'required': False}}

    def create(self, validated_data):
        role = validated_data.get('role', User.Role.CUSTOMER)
        user = User.objects.create_user(
            mobile=validated_data['mobile'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=role
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'mobile', 'email', 'role']
