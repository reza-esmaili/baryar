from rest_framework import serializers
from orders.models import CargoRequest, CargoDimension, OrderHistory

class CargoDimensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CargoDimension
        fields = ['id', 'length', 'width', 'height', 'quantity', 'volume_cm3']
        read_only_fields = ['volume_cm3']


class CargoRequestSerializer(serializers.ModelSerializer):
    # استفاده از required=False به این دلیل است که برای حمل FCL نیازی به ابعاد نداریم
    dimensions = CargoDimensionSerializer(many=True, required=False)
    
    class Meta:
        model = CargoRequest
        fields = '__all__'
        read_only_fields = ['customer', 'status', 'final_price', 'chargeable_weight']

    def validate(self, data):
        # در صورت آپدیت جزئی (PATCH)، ممکن است transport_mode در دیتا نباشد، پس از instance می‌خوانیم
        t_mode = data.get('transport_mode')
        if not t_mode and self.instance:
            t_mode = self.instance.transport_mode

        dimensions = data.get('dimensions', [])
        
        # بررسی منطق FCL و LCL/Air/Land
        if t_mode in ['sea_fcl', 'FCL']:
            # در حمل FCL داشتن اطلاعات کانتینر الزامی است
            container_size = data.get('container_size') or (self.instance.container_size if self.instance else None)
            container_type = data.get('container_type') or (self.instance.container_type if self.instance else None)
            container_count = data.get('container_count') or (self.instance.container_count if self.instance else None)
            
            if not container_size or not container_type or not container_count:
                raise serializers.ValidationError("برای حمل FCL (فول کانتینر)، اطلاعات سایز، نوع و تعداد کانتینر الزامی است.")
        else:
            # در حمل‌های غیر FCL (مثل هوایی، دریایی LCL و زمینی) داشتن ابعاد الزامی است
            # اگر حالت آپدیت است و ابعاد ارسال نشده، فرض می‌کنیم ابعاد قبلی معتبر هستند
            if not dimensions and not self.instance:
                raise serializers.ValidationError("برای این نوع حمل، وارد کردن حداقل یک ردیف ابعاد کالا الزامی است.")
                
        return data

    def create(self, validated_data):
        # جداسازی ابعاد و زیردسته‌ها از دیتای اصلی (برای جلوگیری از خطای TypeError در ManyToMany)
        dimensions_data = validated_data.pop('dimensions', [])
        cargo_subcategories = validated_data.pop('cargo_subcategories', [])
        
        # انتساب مشتری به کاربر لاگین شده (به صورت ایمن)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['customer'] = request.user
        
        # ایجاد درخواست اصلی
        cargo_request = CargoRequest.objects.create(**validated_data)
        
        # اختصاص دادن زیردسته‌ها (فیلد ManyToMany)
        if cargo_subcategories:
            cargo_request.cargo_subcategories.set(cargo_subcategories)
        
        # ایجاد ردیف‌های ابعاد
        for dim_data in dimensions_data:
            CargoDimension.objects.create(cargo_request=cargo_request, **dim_data)
            
        return cargo_request

    def update(self, instance, validated_data):
        # بررسی وجود ابعاد و زیردسته‌ها در دیتای ورودی برای آپدیت
        dimensions_data = validated_data.pop('dimensions', None)
        cargo_subcategories = validated_data.pop('cargo_subcategories', None)
        
        # آپدیت فیلدهای اصلی CargoRequest
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # آپدیت فیلد ManyToMany برای زیردسته‌ها
        if cargo_subcategories is not None:
            instance.cargo_subcategories.set(cargo_subcategories)

        # اگر ابعاد جدیدی ارسال شده بود، ابعاد قبلی را پاک کرده و جدیدها را می‌سازیم
        if dimensions_data is not None:
            instance.dimensions.all().delete()
            for dim_data in dimensions_data:
                CargoDimension.objects.create(cargo_request=instance, **dim_data)

        return instance


class OrderHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderHistory
        fields = '__all__'


class RateDimensionSerializer(serializers.Serializer):
    """سریالایزر برای دریافت ابعاد کالا صرفاً جهت محاسبه (بدون ذخیره)"""
    length = serializers.FloatField(help_text="طول (سانتی‌متر)")
    width = serializers.FloatField(help_text="عرض (سانتی‌متر)")
    height = serializers.FloatField(help_text="ارتفاع (سانتی‌متر)")
    quantity = serializers.IntegerField(default=1, help_text="تعداد")


class RateCalculationRequestSerializer(serializers.Serializer):
    """سریالایزر برای دریافت اطلاعات استعلام نرخ و اتصال به سرویس محاسباتی"""
    transport_mode = serializers.CharField(max_length=50)
    origin_id = serializers.IntegerField(help_text="شناسه مبدا (شهر یا پورت)")
    destination_id = serializers.IntegerField(help_text="شناسه مقصد (شهر یا پورت)")
    
    # فیلدهای مربوط به FCL
    container_size = serializers.CharField(max_length=20, required=False)
    container_type = serializers.CharField(max_length=50, required=False)
    container_count = serializers.IntegerField(required=False)
    
    # فیلدهای مربوط به بارهای نیازمند محاسبه وزن حجمی (هوایی، زمینی، LCL)
    gross_weight = serializers.FloatField(required=False, help_text="وزن ناخالص کل (کیلوگرم)")
    dimensions = RateDimensionSerializer(many=True, required=False)

    def validate(self, data):
        t_mode = data.get('transport_mode')
        
        if t_mode in ['sea_fcl', 'FCL']:
            if not all([data.get('container_size'), data.get('container_type'), data.get('container_count')]):
                raise serializers.ValidationError("برای استعلام نرخ FCL، اطلاعات کانتینر (سایز، نوع و تعداد) الزامی است.")
        else:
            if not data.get('gross_weight'):
                raise serializers.ValidationError("برای این نوع حمل، وارد کردن وزن ناخالص (gross_weight) الزامی است.")
            if not data.get('dimensions'):
                raise serializers.ValidationError("برای محاسبه وزن حجمی این نوع حمل، وارد کردن ابعاد کالا الزامی است.")
                
        return data
