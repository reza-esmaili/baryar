from django.db import models
from core.models import TimeStampedModel


class Province(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"


class City(TimeStampedModel):
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name="cities")
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.province.name}"

    class Meta:
        unique_together = ("province", "name")
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"


class Country(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True)  # ISO 3166-1 alpha-3
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "کشور"
        verbose_name_plural = "کشورها"


class DestinationCity(TimeStampedModel):
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="cities")
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.country.name}"

    class Meta:
        unique_together = ("country", "name")
        verbose_name = "شهر مقصد"
        verbose_name_plural = "شهرهای مقصد"


class Port(TimeStampedModel):
    class PortType(models.TextChoices):
        SEA = "sea", "بندر"
        AIR = "air", "فرودگاه" 
        land = "land", "گمرک زمینی"
        rail  = "rail", "گمرک ریلی"

    city = models.ForeignKey(DestinationCity, on_delete=models.PROTECT, related_name="ports")
    name = models.CharField(max_length=150)
    port_type = models.CharField(max_length=5, choices=PortType.choices)
    code = models.CharField(max_length=10, blank=True)  # IATA / UN/LOCODE
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_port_type_display()})"

    class Meta:
        verbose_name = "بندر / فرودگاه"
        verbose_name_plural = "بنادر و فرودگاه‌ها"
