from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.choices import ShippingProcedure

# === انتخاب‌های سیستم ===

class TransportMode(models.TextChoices):
    AIR = 'air', 'هوایی'
    SEA_FCL = 'sea_fcl', 'دریایی FCL'
    SEA_LCL = 'sea_lcl', 'دریایی LCL'
    LAND = 'land', 'زمینی'
    RAIL = 'rail', 'ریلی' 

class CargoType(models.Model):
    name = models.CharField(max_length=100, verbose_name="عنوان دسته اصلی کالا")
    transport_mode = models.CharField(
        max_length=20, 
        choices=TransportMode.choices, 
        verbose_name="وابسته به روش حمل"
    )

    class Meta:
        verbose_name = "نوع کالا (دسته اصلی)"
        verbose_name_plural = "انواع کالا (دسته‌های اصلی)"

    def __str__(self):
        return f"{self.name} ({self.get_transport_mode_display()})"

class CargoSubCategory(models.Model):
    category = models.ForeignKey(
        CargoType, 
        on_delete=models.CASCADE, 
        related_name='subcategories',
        verbose_name="دسته اصلی"
    )
    name = models.CharField(max_length=150, verbose_name="عنوان زیردسته")
    # فیلد جدید توضیحات
    description = models.TextField(verbose_name="توضیحات", blank=True, null=True)

    class Meta:
        verbose_name = "زیردسته کالا"
        verbose_name_plural = "زیردسته‌های کالا"

    def __str__(self):
        return f"{self.name} (زیرمجموعه: {self.category.name})"


class PricingUnit(models.TextChoices):
    FIXED = 'fixed', 'نرخ ثابت (Fixed)'
    PER_KG = 'per_kg', 'به ازای هر کیلوگرم (Per KG)'
    PER_CONTAINER = 'per_container', 'به ازای هر کانتینر (Per Container)'

class ContainerSize(models.TextChoices):
    FT_20 = '20ft', '۲۰ فوت'
    FT_40_STD = '40ft_std', '۴۰ فوت استاندارد'
    FT_40_HC = '40ft_hc', '۴۰ فوت های‌کیوب'
    FT_45_HC = '45ft_hc', '۴۵ فوت های‌کیوب'

class ContainerType(models.TextChoices):
    DRY = 'dry', 'خشک استاندارد'
    REEFER = 'reefer', 'یخچالی'
    OPEN_TOP = 'open_top', 'روباز از بالا'
    FLAT_RACK = 'flat_rack', 'تخت'
    PLATFORM = 'platform', 'پلتفرم'
    TANK = 'tank', 'تانکی'
    VENTILATED = 'ventilated', 'دارای تهویه'
    INSULATED = 'insulated', 'عایق‌بندی‌شده'
    DOUBLE_DOOR = 'double_door', 'دو درب'


# === مدل اصلی نرخ ===
class Rate(models.Model):
    # --- مالک نرخ (فورواردر یا شعبه) ---
    forwarder = models.ForeignKey(
        'forwarders.ForwarderCompany', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='rates',
        verbose_name="شرکت فورواردر"
    )
    shipping_procedure = models.CharField(
        max_length=20,
        choices=ShippingProcedure.choices,
        default=ShippingProcedure.COMMERCIAL,
        verbose_name="رویه ارسال"
    )

    branch = models.ForeignKey(
        'forwarders.ForwarderBranch', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='rates',
        verbose_name="شعبه فورواردر"
    )

    transport_mode = models.CharField(
        max_length=20, 
        choices=TransportMode.choices,
        verbose_name="روش حمل"
    )

    # --- مبدا (Origin) ---
    origin_province = models.ForeignKey(
        'locations.Province', 
        on_delete=models.PROTECT, 
        related_name='origin_rates',
        verbose_name="استان مبدا"
    )
    # توجه: این فیلد همچنان به CargoType (دسته اصلی) متصل است تا در هنگام استعلام اولیه مشکلی ایجاد نشود
    cargo_types = models.ManyToManyField(
        CargoType,
        verbose_name="نوع کالا (دسته‌های تحت پوشش)",
        related_name="rates",
        blank=True
    )
    origin_city = models.ForeignKey(
        'locations.City', 
        on_delete=models.PROTECT, 
        related_name='origin_rates',
        verbose_name="شهر مبدا"
    )

    # --- مقصد (Destination) ---
    destination_country = models.ForeignKey(
        'locations.Country', 
        on_delete=models.PROTECT, 
        related_name='destination_rates',
        verbose_name="کشور مقصد"
    )
    destination_city = models.ForeignKey(
        'locations.DestinationCity', 
        on_delete=models.PROTECT, 
        related_name='destination_rates',
        verbose_name="شهر مقصد"
    )
    destination_port = models.ForeignKey(
        'locations.Port', 
        on_delete=models.PROTECT, 
        related_name='destination_rates',
        verbose_name="پورت/فرودگاه مقصد"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="وضعیت فعال بودن"
    )
    valid_until = models.DateField(
        verbose_name="تاریخ اعتبار"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "نرخ پایه"
        verbose_name_plural = "نرخ‌های پایه"

    def __str__(self):
        owner = self.branch.name if self.branch else (self.forwarder.national_id if self.forwarder else "ناشناس")
        return f"نرخ {owner} از {self.origin_city.name} به {self.destination_port.name} ({self.get_transport_mode_display()})"
    
    @property
    def is_currently_active(self):
        if not self.is_active:
            return False
        if self.valid_until < timezone.now().date():
            return False
        return True
    
    def clean(self):
        super().clean()
        
        # ۱. بررسی مالکیت نرخ
        if not self.forwarder and not self.branch:
            raise ValidationError("باید یکی از موارد 'شرکت فورواردر' یا 'شعبه' مشخص شود.")
        if self.forwarder and self.branch:
            raise ValidationError("نرخ نمی‌تواند همزمان متعلق به شرکت و شعبه باشد. فقط یکی را انتخاب کنید.")

        # ۲. اعتبارسنجی ارتباط مبدا
        if self.origin_province and self.origin_city:
            if self.origin_city.province != self.origin_province:
                raise ValidationError({'origin_city': 'شهر مبدا انتخاب شده متعلق به این استان نیست.'})

        # ۳. اعتبارسنجی ارتباط مقصد
        if self.destination_country and self.destination_city:
            if self.destination_city.country != self.destination_country:
                raise ValidationError({'destination_city': 'شهر مقصد انتخاب شده متعلق به این کشور نیست.'})
        
        if self.destination_city and self.destination_port:
            if self.destination_port.city != self.destination_city:
                raise ValidationError({'destination_port': 'پورت/فرودگاه مقصد متعلق به این شهر نیست.'})

        # ۴. اعتبارسنجی نوع پورت
        if self.destination_port and self.transport_mode:
            port_type = str(self.destination_port.port_type).lower()
            t_mode = str(self.transport_mode).lower()

            if t_mode == 'air' and port_type != 'air':
                raise ValidationError({'destination_port': f'برای حمل هوایی، مقصد باید فرودگاه باشد. (مقدار فعلی پورت: {port_type})'})
            
            if t_mode in ['sea_fcl', 'sea_lcl'] and port_type != 'sea':
                raise ValidationError({'destination_port': f'برای حمل دریایی، مقصد باید بندر دریایی باشد. (مقدار فعلی پورت: {port_type})'})

            if t_mode in ['land', 'rail'] and port_type not in ['land', 'rail']:
                raise ValidationError({'destination_port': f'برای حمل زمینی/ریلی، مقصد باید گمرک زمینی یا ریلی باشد. (مقدار فعلی پورت: {port_type})'})
            
            if self.valid_until:
                base_date = self.created_at.date() if self.created_at else timezone.now().date()
                if self.valid_until <= base_date:
                    raise ValidationError({
                        'valid_until': 'تاریخ اعتبار باید حداقل ۲۴ ساعت (یک روز) پس از تاریخ ثبت باشد و نمی‌تواند تاریخ امروز یا گذشته باشد.'
                    })

# === مدل ردیف‌های قیمتی (تیرهای نرخ) ===
class RateTier(models.Model):
    rate = models.ForeignKey(
        Rate, 
        on_delete=models.CASCADE, 
        related_name='tiers',
        verbose_name='نرخ مرتبط'
    )
    pricing_unit = models.CharField(
        max_length=20, 
        choices=PricingUnit.choices, 
        verbose_name='واحد قیمت‌گذاری'
    )
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name='مبلغ'
    )

    weight_from = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='از وزن (KG)'
    )
    weight_to = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='تا وزن (KG)'
    )

    container_size = models.CharField(
        max_length=20, choices=ContainerSize.choices, null=True, blank=True, verbose_name='ابعاد کانتینر'
    )
    container_type = models.CharField(
        max_length=20, choices=ContainerType.choices, null=True, blank=True, verbose_name='نوع کانتینر'
    )

    class Meta:
        verbose_name = 'ردیف قیمتی'
        verbose_name_plural = 'ردیف‌های قیمتی'

    def __str__(self):
        return f"{self.rate} - {self.price} {self.get_pricing_unit_display()}"

    def clean(self):
        t_mode = self.rate.transport_mode 

        if t_mode == TransportMode.AIR:
            if self.pricing_unit not in [PricingUnit.FIXED, PricingUnit.PER_KG]:
                raise ValidationError({'pricing_unit': 'واحد قیمت برای حمل هوایی باید "نرخ ثابت" یا "به ازای هر کیلوگرم" باشد.'})
            
            if self.weight_from is None or self.weight_to is None:
                raise ValidationError('برای حمل هوایی، تعیین مقادیر "از وزن" و "تا وزن" الزامی است.')
            
            if self.container_size or self.container_type:
                raise ValidationError('در حمل هوایی نباید اطلاعات کانتینر پر شود.')

        elif t_mode == TransportMode.SEA_FCL:
            if self.pricing_unit != PricingUnit.PER_CONTAINER:
                raise ValidationError({'pricing_unit': 'واحد قیمت برای دریایی FCL باید "به ازای هر کانتینر" باشد.'})
            
            if not self.container_size or not self.container_type:
                raise ValidationError('برای حمل دریایی FCL، تعیین "ابعاد کانتینر" و "نوع کانتینر" الزامی است.')
            
            if self.weight_from is not None or self.weight_to is not None:
                raise ValidationError('در حمل دریایی FCL نیازی به تعیین بازه وزنی نیست.')

        elif t_mode in [TransportMode.LAND, TransportMode.RAIL]:
            pass
