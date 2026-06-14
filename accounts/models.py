import hashlib
import os
import random
import re

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone

from core.models import TimeStampedModel


class UserManager(BaseUserManager):
    def normalize_mobile(self, mobile):
        return OTPCode.normalize_mobile(mobile)

    def create_user(self, mobile, password=None, **extra_fields):
        if not mobile:
            raise ValueError("شماره موبایل الزامی است")

        mobile = self.normalize_mobile(mobile)
        user = self.model(mobile=mobile, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.PLATFORM_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser باید is_staff=True داشته باشد.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser باید is_superuser=True داشته باشد.")

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

    def save(self, *args, **kwargs):
        if self.mobile:
            self.mobile = OTPCode.normalize_mobile(self.mobile)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.mobile})"

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"


class OTPCode(TimeStampedModel):
    class Purpose(models.TextChoices):
        REGISTER = "register", "ثبت‌نام"
        LOGIN = "login", "ورود"
        PASSWORD_RESET = "password_reset", "فراموشی رمز عبور"

    mobile = models.CharField(max_length=15, db_index=True)
    purpose = models.CharField(max_length=30, choices=Purpose.choices, db_index=True)
    code_hash = models.CharField(max_length=128)

    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    sent_count = models.PositiveSmallIntegerField(default=1)
    last_sent_at = models.DateTimeField(default=timezone.now)

    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = "کد یکبار مصرف"
        verbose_name_plural = "کدهای یکبار مصرف"
        indexes = [
            models.Index(fields=["mobile", "purpose", "is_used"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.mobile} - {self.purpose}"

    @staticmethod
    def normalize_mobile(mobile):
        if not mobile:
            return ""

        mobile = str(mobile).strip()
        mobile = mobile.replace(" ", "").replace("-", "")

        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        arabic_digits = "٠١٢٣٤٥٦٧٨٩"
        english_digits = "0123456789"

        translation_map = {}
        for p, e in zip(persian_digits, english_digits):
            translation_map[ord(p)] = e
        for a, e in zip(arabic_digits, english_digits):
            translation_map[ord(a)] = e

        mobile = mobile.translate(translation_map)

        if mobile.startswith("+98"):
            mobile = "0" + mobile[3:]
        elif mobile.startswith("0098"):
            mobile = "0" + mobile[4:]
        elif mobile.startswith("98") and len(mobile) == 12:
            mobile = "0" + mobile[2:]

        return mobile

    @staticmethod
    def is_valid_mobile(mobile):
        mobile = OTPCode.normalize_mobile(mobile)
        return bool(re.match(r"^09\d{9}$", mobile))

    @staticmethod
    def generate_code():
        length = int(getattr(settings, "OTP_CODE_LENGTH", 6))
        start = 10 ** (length - 1)
        end = (10 ** length) - 1
        return str(random.randint(start, end))

    @staticmethod
    def hash_code(code):
        secret = getattr(settings, "SECRET_KEY", "")
        raw = f"{code}:{secret}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def get_expire_seconds():
        return int(getattr(settings, "OTP_EXPIRE_SECONDS", 120))

    @classmethod
    def create_otp(cls, mobile, purpose, code=None):
        mobile = cls.normalize_mobile(mobile)
        code = code or cls.generate_code()

        with transaction.atomic():
            cls.objects.select_for_update().filter(
                mobile=mobile,
                purpose=purpose,
                is_used=False,
            ).update(is_used=True)

            otp = cls.objects.create(
                mobile=mobile,
                purpose=purpose,
                code_hash=cls.hash_code(code),
                expires_at=timezone.now() + timezone.timedelta(seconds=cls.get_expire_seconds()),
                last_sent_at=timezone.now(),
            )

        return otp, code

    def is_expired(self):
        return timezone.now() > self.expires_at

    def requires_captcha(self):
        threshold = int(getattr(settings, "OTP_CAPTCHA_AFTER_ATTEMPTS", 3))
        return self.attempts >= threshold

    def can_verify(self):
        max_attempts = int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))
        return not self.is_used and not self.is_expired() and self.attempts < max_attempts

    def verify(self, code):
        if not self.can_verify():
            return False

        if self.code_hash == self.hash_code(str(code).strip()):
            self.is_used = True
            self.save(update_fields=["is_used", "updated_at"])
            return True

        self.attempts += 1
        self.save(update_fields=["attempts", "updated_at"])
        return False


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
        User,
        on_delete=models.CASCADE,
        related_name="business_info",
        limit_choices_to={"role": User.Role.CUSTOMER},
    )
    delivery_address = models.TextField(blank=True)
    usual_cargo_type = models.CharField(max_length=200, blank=True)
    credit_limit = models.DecimalField(max_digits=20, decimal_places=0, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "اطلاعات تجاری مشتری"
        verbose_name_plural = "اطلاعات تجاری مشتریان"


def identity_document_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1]

    if instance.company:
        company_name = instance.company.company_name.strip()
        safe_company_name = re.sub(r'[\\/:*?"<>|]+', "_", company_name)
        safe_company_name = re.sub(r"\s+", "_", safe_company_name)
        return f"identity_docs/{safe_company_name}/{instance.doc_type}{ext}"

    mobile = instance.user.mobile if instance.user_id else "unknown"
    safe_mobile = re.sub(r'[\\/:*?"<>|]+', "_", mobile)
    return f"identity_docs/{safe_mobile}/{instance.doc_type}{ext}"


class IdentityDocument(TimeStampedModel):
    class DocType(models.TextChoices):
        NATIONAL_CARD = "national_card", "کارت ملی نماینده"
        BIRTH_CERTIFICATE = "birth_certificate", "شناسنامه"
        ESTABLISHMENT_NOTICE = "establishment_notice", "آگهی تاسیس"
        ARTICLES_OF_ASSOCIATION = "articles_of_association", "اساسنامه"
        LATEST_CHANGES = "latest_changes", "آخرین تغییرات روزنامه رسمی"
        CEO_NATIONAL_CARD = "ceo_national_card", "کارت ملی مدیر عامل"

    company = models.ForeignKey(
        "forwarders.ForwarderCompany",
        on_delete=models.CASCADE,
        related_name="identity_documents",
        null=True,
        blank=True,
        verbose_name="شرکت فورواردر",
    )

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار بررسی"
        APPROVED = "approved", "تایید شده"
        REJECTED = "rejected", "رد شده"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=30, choices=DocType.choices)
    file = models.FileField(upload_to=identity_document_upload_to)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "مدرک هویتی"
        verbose_name_plural = "مدارک هویتی"
