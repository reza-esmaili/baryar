from rest_framework import serializers
from rates.models import Rate, RateTier, CargoType, CargoSubCategory
from locations.models import City, DestinationCity, Port

class CargoSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CargoSubCategory
        fields = ['id', 'name', 'description']

class CargoTypeSerializer(serializers.ModelSerializer):
    subcategories = CargoSubCategorySerializer(many=True, read_only=True)
    transport_mode_display = serializers.CharField(source='get_transport_mode_display', read_only=True)

    class Meta:
        model = CargoType
        fields = ['id', 'name', 'transport_mode', 'transport_mode_display', 'subcategories']

class RateTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateTier
        fields = ['id', 'pricing_unit', 'price', 'weight_from', 'weight_to', 'container_size', 'container_type']

    def validate(self, data):
        # از آنجایی که RateTier در مدل به Rate وابسته است، اعتبارسنجی نهایی 
        # در سطح RateSerializer انجام می‌شود. اما می‌توان چک‌های اولیه را اینجا گذاشت.
        return data

class RateSerializer(serializers.ModelSerializer):
    tiers = RateTierSerializer(many=True)
    is_currently_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Rate
        fields = [
            'id', 'forwarder', 'branch', 'transport_mode', 
            'origin_province', 'origin_city', 'cargo_types',
            'destination_country', 'destination_city', 'destination_port',
            'is_active', 'valid_until', 'is_currently_active', 'tiers'
        ]

    def validate(self, data):
        # ساخت یک نمونه موقت برای اجرای متد clean مدل
        instance = Rate(**data)
        # برای فیلدهای ManyToMany (cargo_types) باید از دیتای موقت صرف نظر کنیم چون هنوز ذخیره نشده‌اند
        if 'cargo_types' in data:
            del instance.cargo_types
            
        try:
            instance.clean()
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            from django.core.exceptions import ValidationError as DjangoValidationError
            if isinstance(e, DjangoValidationError):
                raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else list(e.messages))
            raise serializers.ValidationError(str(e))
            
        return data

    def create(self, validated_data):
        tiers_data = validated_data.pop('tiers', [])
        cargo_types = validated_data.pop('cargo_types', [])
        
        # ساخت نرخ اصلی
        rate = Rate.objects.create(**validated_data)
        
        # تخصیص انواع کالا
        rate.cargo_types.set(cargo_types)

        # ساخت ردیف‌های قیمتی وابسته
        for tier_data in tiers_data:
            tier = RateTier(rate=rate, **tier_data)
            tier.clean() # فراخوانی clean برای هر ردیف قیمتی
            tier.save()
            
        return rate

    def update(self, instance, validated_data):
        tiers_data = validated_data.pop('tiers', None)
        cargo_types = validated_data.pop('cargo_types', None)

        # آپدیت فیلدهای اصلی
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # آپدیت ManyToMany
        if cargo_types is not None:
            instance.cargo_types.set(cargo_types)

        # آپدیت ردیف‌های قیمتی (حذف قبلی‌ها و ساخت جدیدها برای سادگی)
        if tiers_data is not None:
            instance.tiers.all().delete()
            for tier_data in tiers_data:
                tier = RateTier(rate=instance, **tier_data)
                tier.clean()
                tier.save()

        return instance
