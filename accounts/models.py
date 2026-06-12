from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from core.models import TimeStampedModel


class UserManager(BaseUserManager):
    def create_user(self, mobile, password=None, **extra_fields):
        if not mobile:
            raise ValueError("شماره موبایل الزامی است")
        user = self.model(mobile=mobile, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.PLATFORM_ADMIN)
        return self.create_user(mobile, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    class Role(models.TextChoices):
        PLATFORM_ADMIN = "platform_admin", "ادمین پلتفرم"
        CUSTOMER = "customer", "مشتری"
        FORWARDER_ADMIN = "forwarder_admin", "ادمین فورواردر"
        FORWARDER_EXPERT = "forwarder_expert", "کارشناس فورواردر"
        FORWARDER_FINANCE = "forwarder_finance", "کارمند مالی فورواردر"

    mobile = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.CUSTOMER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.mobile})"

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"


# ─── Customer ────────────────────────────────────────────────────────────────

class CustomerProfile(TimeStampedModel):
    """شخص حقیقی"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    national_code = models.CharField(max_length=10, unique=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = "پروفایل مشتری حقیقی"
        verbose_name_plural = "پروفایل‌های مشتری حقیقی"


class CompanyType(models.TextChoices):
    PRIVATE_JOINT_STOCK = "private_joint_stock", "سهامی خاص"
    PUBLIC_JOINT_STOCK = "public_joint_stock", "سهامی عام"
    LIMITED_LIABILITY = "limited_liability", "مسئولیت محدود"
    COOPERATIVE = "cooperative", "تعاونی"
    GENERAL_PARTNERSHIP = "general_partnership", "تضامنی"
    OTHER = "other", "سایر"


class CustomerCompanyProfile(TimeStampedModel):
    """مشتری حقوقی — یک کاربر فقط یک شرکت"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_company_profile")
    company_type = models.CharField(max_length=30, choices=CompanyType.choices)
    national_id = models.CharField(max_length=11, unique=True, verbose_name="شناسه ملی شرکت")
    registration_number = models.CharField(max_length=20, unique=True)
    ceo_first_name = models.CharField(max_length=100)
    ceo_last_name = models.CharField(max_length=100)
    ceo_national_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=15)
    postal_code = models.CharField(max_length=10)
    address = models.TextField()

    def __str__(self):
        return self.national_id

    class Meta:
        verbose_name = "پروفایل مشتری حقوقی"
        verbose_name_plural = "پروفایل‌های مشتری حقوقی"


class CustomerBusinessInfo(TimeStampedModel):
    """اطلاعات تجاری مکمل مشتری برای ثبت سفارش"""
    customer = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="business_info",
        limit_choices_to={"role": User.Role.CUSTOMER}
    )
    delivery_address = models.TextField(blank=True)
    usual_cargo_type = models.CharField(max_length=200, blank=True)
    credit_limit = models.DecimalField(max_digits=20, decimal_places=0, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "اطلاعات تجاری مشتری"
        verbose_name_plural = "اطلاعات تجاری مشتریان"


# ─── Identity Documents ───────────────────────────────────────────────────────

class IdentityDocument(TimeStampedModel):
    class DocType(models.TextChoices):
        NATIONAL_CARD = "national_card", "کارت ملی"
        BIRTH_CERTIFICATE = "birth_certificate", "شناسنامه"
        ESTABLISHMENT_NOTICE = "establishment_notice", "آگهی تاسیس"
        ARTICLES_OF_ASSOCIATION = "articles_of_association", "اساسنامه"
        CEO_NATIONAL_CARD = "ceo_national_card", "کارت ملی مدیر عامل"

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار بررسی"
        APPROVED = "approved", "تایید شده"
        REJECTED = "rejected", "رد شده"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=30, choices=DocType.choices)
    file = models.FileField(upload_to="identity_docs/%Y/%m/")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "مدرک هویتی"
        verbose_name_plural = "مدارک هویتی"
