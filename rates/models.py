from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.choices import ShippingProcedure


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

    description = models.TextField(
        verbose_name="توضیحات",
        blank=True,
        null=True
    )

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


class ExtraChargeType(models.TextChoices):
    NOT_AVAILABLE = 'not_available', 'ارائه نمی‌شود'
    FREE = 'free', 'رایگان'
    FIXED = 'fixed', 'هزینه ثابت'
    PER_KG = 'per_kg', 'به ازای هر کیلوگرم'


class Rate(models.Model):

    forwarder = models.ForeignKey(
        'forwarders.ForwarderCompany',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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
        null=True,
        blank=True,
        related_name='rates',
        verbose_name="شعبه فورواردر"
    )

    transport_mode = models.CharField(
        max_length=20,
        choices=TransportMode.choices,
        verbose_name="روش حمل"
    )

    origin_country = models.ForeignKey(
        'locations.Country',
        on_delete=models.PROTECT,
        related_name='origin_rates',
        verbose_name="کشور مبدا",
        null=True,
        blank=True,
    )

    origin_province = models.ForeignKey(
        'locations.Province',
        on_delete=models.PROTECT,
        related_name='origin_rates',
        verbose_name="استان مبدا"
    )

    origin_city = models.ForeignKey(
        'locations.City',
        on_delete=models.PROTECT,
        related_name='origin_rates',
        verbose_name="شهر مبدا"
    )

    cargo_types = models.ManyToManyField(
        CargoType,
        verbose_name="نوع کالا (دسته‌های تحت پوشش)",
        related_name="rates",
        blank=True
    )

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

    packaging_charge_type = models.CharField(
        max_length=20,
        choices=ExtraChargeType.choices,
        default=ExtraChargeType.NOT_AVAILABLE,
        verbose_name="نوع هزینه بسته‌بندی"
    )

    packaging_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="مبلغ بسته‌بندی"
    )

    doorstep_packaging_charge_type = models.CharField(
        max_length=20,
        choices=ExtraChargeType.choices,
        default=ExtraChargeType.NOT_AVAILABLE,
        verbose_name="نوع هزینه تحویل و بسته‌بندی درب محل"
    )

    doorstep_packaging_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="مبلغ تحویل و بسته‌بندی درب محل"
    )

    add_vat = models.BooleanField(
        default=False,
        verbose_name="افزودن ۱۰٪ ارزش افزوده به نرخ‌ها"
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

        paid_types = [
            ExtraChargeType.FIXED,
            ExtraChargeType.PER_KG,
        ]

        free_types = [
            ExtraChargeType.NOT_AVAILABLE,
            ExtraChargeType.FREE,
        ]

        packaging_price = self.packaging_price or 0
        doorstep_price = self.doorstep_packaging_price or 0

        if self.packaging_charge_type in paid_types and packaging_price <= 0:
            raise ValidationError({
                "packaging_price": "برای هزینه بسته‌بندی ثابت یا کیلویی، مبلغ باید بیشتر از صفر باشد."
            })

        if self.packaging_charge_type in free_types and packaging_price != 0:
            raise ValidationError({
                "packaging_price": "وقتی بسته‌بندی رایگان است یا ارائه نمی‌شود، مبلغ باید صفر باشد."
            })

        if self.doorstep_packaging_charge_type in paid_types and doorstep_price <= 0:
            raise ValidationError({
                "doorstep_packaging_price": "برای هزینه بسته‌بندی و تحویل در محل، مبلغ باید بیشتر از صفر باشد."
            })

        if self.doorstep_packaging_charge_type in free_types and doorstep_price != 0:
            raise ValidationError({
                "doorstep_packaging_price": "وقتی بسته‌بندی و تحویل در محل رایگان است یا ارائه نمی‌شود، مبلغ باید صفر باشد."
            })

        if not self.forwarder and not self.branch:
            raise ValidationError("باید یکی از موارد 'شرکت فورواردر' یا 'شعبه' مشخص شود.")

        if self.forwarder and self.branch:
            raise ValidationError("نرخ نمی‌تواند همزمان متعلق به شرکت و شعبه باشد.")

        if self.origin_country and self.origin_province:
            if self.origin_province.country_id != self.origin_country_id:
                raise ValidationError({
                    "origin_province": "استان مبدا متعلق به کشور انتخاب‌شده نیست."
                })

        if self.origin_province and self.origin_city:
            if self.origin_city.province_id != self.origin_province_id:
                raise ValidationError({
                    "origin_city": "شهر مبدا متعلق به این استان نیست."
                })

        if self.destination_country and self.destination_city:
            if self.destination_city.country_id != self.destination_country_id:
                raise ValidationError({
                    "destination_city": "شهر مقصد متعلق به این کشور نیست."
                })

        if self.destination_city and self.destination_port:
            if self.destination_port.city_id != self.destination_city_id:
                raise ValidationError({
                    "destination_port": "پورت مقصد متعلق به این شهر نیست."
                })

        if self.destination_port and self.transport_mode:

            port_type = str(self.destination_port.port_type).lower()
            t_mode = str(self.transport_mode).lower()

            if t_mode == "air" and port_type != "air":
                raise ValidationError({
                    "destination_port": "برای حمل هوایی مقصد باید فرودگاه باشد."
                })

            if t_mode in ["sea_fcl", "sea_lcl"] and port_type != "sea":
                raise ValidationError({
                    "destination_port": "برای حمل دریایی مقصد باید بندر دریایی باشد."
                })

            if t_mode in ["land", "rail"] and port_type not in ["land", "rail"]:
                raise ValidationError({
                    "destination_port": "برای حمل زمینی یا ریلی مقصد باید گمرک زمینی یا ریلی باشد."
                })

        if self.valid_until:
            base_date = self.created_at.date() if self.created_at else timezone.now().date()

            if self.valid_until <= base_date:
                raise ValidationError({
                    "valid_until": "تاریخ اعتبار باید حداقل یک روز بعد از تاریخ ثبت باشد."
                })


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
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    weight_to = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    container_size = models.CharField(
        max_length=20,
        choices=ContainerSize.choices,
        null=True,
        blank=True
    )

    container_type = models.CharField(
        max_length=20,
        choices=ContainerType.choices,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'ردیف قیمتی'
        verbose_name_plural = 'ردیف‌های قیمتی'

    def __str__(self):
        return f"{self.rate} - {self.price}"

    def clean(self):

        t_mode = self.rate.transport_mode

        if t_mode == TransportMode.AIR:

            if self.pricing_unit not in [PricingUnit.FIXED, PricingUnit.PER_KG]:
                raise ValidationError("واحد قیمت برای حمل هوایی باید ثابت یا کیلویی باشد.")

            if self.weight_from is None or self.weight_to is None:
                raise ValidationError("برای حمل هوایی تعیین بازه وزن الزامی است.")

            if self.container_size or self.container_type:
                raise ValidationError("در حمل هوایی اطلاعات کانتینر نباید پر شود.")

        elif t_mode == TransportMode.SEA_FCL:

            if self.pricing_unit != PricingUnit.PER_CONTAINER:
                raise ValidationError("در حمل FCL قیمت باید بر اساس کانتینر باشد.")

            if not self.container_size or not self.container_type:
                raise ValidationError("برای FCL نوع و سایز کانتینر الزامی است.")

            if self.weight_from is not None or self.weight_to is not None:
                raise ValidationError("در FCL بازه وزن استفاده نمی‌شود.")
