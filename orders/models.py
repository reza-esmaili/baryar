from django.db import models
from accounts.models import User
from locations.models import Country, Province, City, Port
from rates.models import Rate, CargoType, CargoSubCategory, TransportMode, ContainerSize, ContainerType 
from core.models import TimeStampedModel
from core.choices import ShippingProcedure
from django.core.exceptions import ValidationError

class OrderStatus(models.TextChoices):
    DRAFT = 'draft', 'پیش‌نویس (نیاز به تکمیل اطلاعات)'
    PENDING = 'pending', 'در انتظار تایید فورواردر'
    ACCEPTED = 'accepted', 'تایید شده'
    REJECTED = 'rejected', 'رد شده'
    COMPLETED = 'completed', 'تکمیل شده'


class CargoRequest(TimeStampedModel):
    """مدل اصلی درخواست/سفارش حمل کالا توسط مشتری"""
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cargo_requests', verbose_name='مشتری')
    

    # مشخصات مسیر و کالا (مرحله اول)
    origin_country = models.ForeignKey(Country,on_delete=models.PROTECT,related_name="origin_requests",verbose_name="کشور مبدا",null=True,blank=True,)

    origin_province = models.ForeignKey(Province,on_delete=models.PROTECT,related_name="origin_requests",verbose_name="استان مبدا",null=True,blank=True,)

    origin_city = models.ForeignKey(City,on_delete=models.PROTECT,related_name="origin_requests",verbose_name="شهر مبدا")

    destination_port = models.ForeignKey(Port, on_delete=models.PROTECT, verbose_name='پورت/فرودگاه مقصد')
    transport_mode = models.CharField(max_length=20, choices=TransportMode.choices, verbose_name='روش حمل درخواست‌شده')
    shipping_procedure = models.CharField(max_length=20,choices=ShippingProcedure.choices,default=ShippingProcedure.COMMERCIAL,verbose_name="رویه ارسال")
    cargo_type = models.ForeignKey(CargoType, on_delete=models.PROTECT, verbose_name='نوع کالا (دسته اصلی)')
    
    # اوزان
    actual_weight = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='وزن واقعی (KG)')
    chargeable_weight = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='وزن قابل پرداخت (Chargeable)')
    
    # فیلدهای مربوط به کانتینر (FCL)
    container_size = models.CharField(max_length=20, choices=ContainerSize.choices, null=True, blank=True, verbose_name='ابعاد کانتینر')
    container_type = models.CharField(max_length=20, choices=ContainerType.choices, null=True, blank=True, verbose_name='نوع کانتینر')
    container_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد کانتینر')
    
    # انتخاب نهایی مشتری
    selected_rate = models.ForeignKey(Rate, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='نرخ انتخاب شده فورواردر')
    final_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='قیمت نهایی محاسبه شده')
    needs_packaging = models.BooleanField(
        default=False,
        verbose_name="نیاز به بسته‌بندی"
    )

    needs_doorstep_packaging = models.BooleanField(
        default=False,
        verbose_name="نیاز به بسته‌بندی و تحویل در محل"
    )

    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT, verbose_name='وضعیت درخواست')

    # +++ فیلدهای جدید اضافه شده برای مرحله دوم (تکمیل اطلاعات) +++
    
    # جزئیات دقیق کالا
    cargo_subcategories = models.ManyToManyField(
        CargoSubCategory, 
        blank=True, 
        verbose_name='زیردسته‌های کالا',
        related_name='requests'
    )
    other_cargo_details = models.CharField(max_length=255, null=True, blank=True, verbose_name='سایر جزئیات کالا (در صورت نبود در لیست)')
    base_shipping_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="هزینه حمل"
    )

    packaging_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="هزینه بسته‌بندی"
    )

    doorstep_packaging_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="هزینه تحویل و بسته‌بندی درب محل"
    )

    vat_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="مبلغ ارزش افزوده"
    )

    price_subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="جمع قبل از ارزش افزوده"
    )

    # +++ فیلدهای هویتی مالک بار / فرستنده +++
    sender_name = models.CharField(max_length=150, null=True, blank=True, verbose_name='نام و نام خانوادگی فرستنده')
    sender_national_id = models.CharField(max_length=10, null=True, blank=True, verbose_name='کد ملی فرستنده')
    sender_phone = models.CharField(max_length=15, null=True, blank=True, verbose_name='شماره تماس فرستنده')
    sender_province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True, related_name='sender_requests', verbose_name='استان فرستنده')
    sender_city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='sender_city_requests', verbose_name='شهر فرستنده')
    sender_address = models.TextField(null=True, blank=True, verbose_name='آدرس دقیق پستی فرستنده')

    class Meta:
        verbose_name = "درخواست حمل"
        verbose_name_plural = "درخواست‌های حمل"

    def __str__(self):
        return f"Order #{self.id} - {self.customer} ({self.origin_city} to {self.destination_port})"

    def clean(self):
        super().clean()

        if self.origin_country and self.origin_province:
            if self.origin_province.country_id != self.origin_country_id:
                raise ValidationError({
                    "origin_province": "استان مبدا متعلق به کشور انتخاب‌شده نیست."
                })

        if self.origin_province and self.origin_city:
            if self.origin_city.province_id != self.origin_province_id:
                raise ValidationError({
                    "origin_city": "شهر مبدا متعلق به استان انتخاب‌شده نیست."
                })

class CargoDimension(models.Model):
    """مدل ابعاد کالا (مشتری می‌تواند نامحدود از این ردیف‌ها برای یک درخواست ثبت کند)"""
    cargo_request = models.ForeignKey(CargoRequest, on_delete=models.CASCADE, related_name='dimensions')
    length = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='طول (cm)')
    width = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='عرض (cm)')
    height = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='ارتفاع (cm)')
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')

    class Meta:
        verbose_name = "ابعاد کالا"
        verbose_name_plural = "ابعاد کالاها"

    @property
    def volume_cm3(self):
        """محاسبه حجم به سانتی‌متر مکعب"""
        # فرمول: $Volume = Length \times Width \times Height \times Quantity$
        return self.length * self.width * self.height * self.quantity


# +++ مدل جدید برای لاگ‌گیری و ثبت تاریخچه تغییرات سفارش +++
class OrderHistory(TimeStampedModel):
    """مدل ثبت تاریخچه تغییرات سفارشات و یادداشت‌های فورواردر"""
    order = models.ForeignKey(CargoRequest, on_delete=models.CASCADE, related_name='history', verbose_name='سفارش مرتبط')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='کاربر تغییر دهنده')
    
    # ثبت تغییرات فیلدها
    field_name = models.CharField(max_length=50, null=True, blank=True, verbose_name='فیلد تغییر یافته')
    old_value = models.TextField(null=True, blank=True, verbose_name='مقدار قبلی')
    new_value = models.TextField(null=True, blank=True, verbose_name='مقدار جدید')
    
    # یادداشت‌های سیستم یا فورواردر
    note = models.TextField(null=True, blank=True, verbose_name='یادداشت / پیام')

    class Meta:
        verbose_name = "تاریخچه سفارش"
        verbose_name_plural = "تاریخچه سفارشات"
        ordering = ['-created_at']

    def __str__(self):
        return f"History for Order #{self.order.id} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

