from django.db import models
from accounts.models import User, CompanyType
from locations.models import Province, City
from core.models import TimeStampedModel


class ForwarderCompany(TimeStampedModel):
    """شرکت فورواردر مادر"""
    admin_user = models.OneToOneField(
        User, on_delete=models.PROTECT, related_name="forwarder_company",
        limit_choices_to={"role": User.Role.FORWARDER_ADMIN}
    )
    company_name = models.CharField(max_length=255, verbose_name="نام شرکت") 
    company_type = models.CharField(max_length=30, choices=CompanyType.choices)
    national_id = models.CharField(max_length=11, unique=True)
    registration_number = models.CharField(max_length=20, unique=True)
    ceo_first_name = models.CharField(max_length=100)
    ceo_last_name = models.CharField(max_length=100)
    ceo_national_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    postal_code = models.CharField(max_length=10)
    address = models.TextField()
    logo = models.ImageField(upload_to="forwarder_logos/", null=True, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    linkedin = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.national_id

    class Meta:
        verbose_name = "شرکت فورواردر"
        verbose_name_plural = "شرکت‌های فورواردر"


class ForwarderBranch(TimeStampedModel):
    """شعبه فورواردر — اکانت مستقل دارد"""
    company = models.ForeignKey(ForwarderCompany, on_delete=models.CASCADE, related_name="branches")
    branch_user = models.OneToOneField(
        User, on_delete=models.PROTECT, related_name="forwarder_branch"
    )
    name = models.CharField(max_length=200)
    representative_first_name = models.CharField(max_length=100)
    representative_last_name = models.CharField(max_length=100)
    representative_mobile = models.CharField(max_length=15)
    province = models.ForeignKey(Province, on_delete=models.PROTECT)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    address = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.company} - {self.name}"

    class Meta:
        verbose_name = "شعبه فورواردر"
        verbose_name_plural = "شعب فورواردر"


class ForwarderStaff(TimeStampedModel):
    """کارمندان شرکت فورواردر"""
    company = models.ForeignKey(ForwarderCompany, on_delete=models.CASCADE, related_name="staff")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="forwarder_staff")

    def __str__(self):
        return f"{self.user} @ {self.company}"

    class Meta:
        verbose_name = "کارمند فورواردر"
        verbose_name_plural = "کارمندان فورواردر"
