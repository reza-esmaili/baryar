from django.db import models
from accounts.models import User
from locations.models import Province, City, Port
from rates.models import Rate, CargoType, CargoSubCategory, TransportMode, ContainerSize, ContainerType 
from core.models import TimeStampedModel

class OrderStatus(models.TextChoices):
    DRAFT = 'draft', 'پیش‌نویس (نیاز به تکمیل اطلاعات)'
    PENDING = 'pending', 'در انتظار تایید فورواردر'
    ACCEPTED = 'accepted', 'تایید شده'
    REJECTED = 'rejected', 'رد شده'
    COMPLETED = 'completed', 'تکمیل شده'
class ShippingProcedure(models.TextChoices):
    PASSENGER = "passenger", "مسافری"
    COMMERCIAL = "commercial", "تجاری"

class CargoRequest(TimeStampedModel):
    """مدل اصلی درخواست/سفارش حمل کالا توسط مشتری"""
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cargo_requests', verbose_name='مشتری')
    

    # مشخصات مسیر و کالا (مرحله اول)
    origin_city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='origin_requests', verbose_name='شهر مبدا')
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

