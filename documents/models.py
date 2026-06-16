import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.models import TimeStampedModel
from rates.models import TransportMode, CargoType, CargoSubCategory
from core.choices import ShippingProcedure

class DocumentRequirementLevel(models.TextChoices):
    GENERAL = "general", "عمومی"
    SHIPPING_PROCEDURE = "shipping_procedure", "بر اساس رویه ارسال"
    DESTINATION = "destination", "بر اساس مقصد"
    ORIGIN = "origin", "بر اساس مبدا"
    TRANSPORT_MODE = "transport_mode", "بر اساس روش حمل"
    CARGO_TYPE = "cargo_type", "بر اساس دسته کالا"
    CARGO_SUBCATEGORY = "cargo_subcategory", "بر اساس زیردسته کالا"
    CUSTOM = "custom", "سفارشی"


class OrderDocumentStatus(models.TextChoices):
    PENDING_UPLOAD = "pending_upload", "در انتظار آپلود"
    UPLOADED = "uploaded", "آپلود شده"
    APPROVED = "approved", "تایید شده"
    REJECTED = "rejected", "رد شده"


class AdditionalRequestStatus(models.TextChoices):
    OPEN = "open", "باز"
    COMPLETED = "completed", "تکمیل شده"
    EXPIRED = "expired", "منقضی شده"
    CANCELLED = "cancelled", "لغو شده"


class DocumentType(TimeStampedModel):
    """
    نوع مدرک پایه.
    مثال:
    - فاکتور فروش
    - پکینگ لیست
    - کارت بازرگانی
    - مجوز بهداشت
    """

    title = models.CharField(
        max_length=255,
        verbose_name="عنوان مدرک"
    )

    code = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="کد یکتا"
    )

    description = models.TextField(
        blank=True,
        verbose_name="توضیحات"
    )

    allowed_extensions = models.CharField(
        max_length=255,
        default="pdf,jpg,jpeg,png",
        verbose_name="پسوندهای مجاز",
        help_text="با کاما جدا شود. مثال: pdf,jpg,png"
    )

    max_file_size_mb = models.PositiveIntegerField(
        default=10,
        verbose_name="حداکثر حجم فایل بر حسب مگابایت"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )

    class Meta:
        verbose_name = "نوع مدرک"
        verbose_name_plural = "انواع مدارک"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_allowed_extensions_list(self):
        return [
            item.strip().lower().replace(".", "")
            for item in self.allowed_extensions.split(",")
            if item.strip()
        ]


class DocumentRule(TimeStampedModel):
    """
    قانون مدارک.

    هر رکورد مشخص می‌کند که در چه شرایطی یک مدرک لازم است.

    مثال:
    - رویه تجاری + حمل هوایی => فاکتور فروش
    - رویه تجاری + حمل هوایی + امارات => مجوز X
    - حمل هوایی + مواد غذایی => مجوز بهداشت
    """

    title = models.CharField(
        max_length=255,
        verbose_name="عنوان قانون"
    )

    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="rules",
        verbose_name="نوع مدرک"
    )

    shipping_procedure = models.CharField(
        max_length=20,
        choices=ShippingProcedure.choices,
        null=True,
        blank=True,
        verbose_name="رویه ارسال"
    )

    transport_mode = models.CharField(
        max_length=20,
        choices=TransportMode.choices,
        null=True,
        blank=True,
        verbose_name="روش حمل"
    )
    origin_province = models.ForeignKey(
        "locations.Province",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_rules",
        verbose_name="استان مبدا"
    )

    origin_city = models.ForeignKey(
        "locations.City",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_rules",
        verbose_name="شهر مبدا"
    )

    destination_country = models.ForeignKey(
        "locations.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_rules",
        verbose_name="کشور مقصد"
    )
    destination_city = models.ForeignKey(
        "locations.DestinationCity",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_rules",
        verbose_name="شهر مقصد"
    )

    destination_port = models.ForeignKey(
        "locations.Port",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_rules",
        verbose_name="پورت/فرودگاه/گمرک مقصد"
    )

    
    cargo_type = models.ForeignKey(
        CargoType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_rules",
        verbose_name="دسته اصلی کالا"
    )

    cargo_subcategory = models.ForeignKey(
        CargoSubCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_rules",
        verbose_name="زیردسته کالا"
    )

    is_required = models.BooleanField(
        default=True,
        verbose_name="اجباری است؟"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )

    priority = models.PositiveIntegerField(
        default=0,
        verbose_name="اولویت",
        help_text="هرچه عدد بزرگ‌تر باشد، قانون اختصاصی‌تر/مهم‌تر در نظر گرفته می‌شود."
    )

    requirement_level = models.CharField(
        max_length=30,
        choices=DocumentRequirementLevel.choices,
        default=DocumentRequirementLevel.GENERAL,
        verbose_name="سطح قانون"
    )

    admin_note = models.TextField(
        blank=True,
        verbose_name="یادداشت داخلی ادمین"
    )

    customer_description = models.TextField(
        blank=True,
        verbose_name="توضیح قابل نمایش به مشتری"
    )

    class Meta:
        verbose_name = "قانون مدرک"
        verbose_name_plural = "قوانین مدارک"
        ordering = ["-priority", "title"]
        indexes = [
            models.Index(fields=["shipping_procedure"]),
            models.Index(fields=["transport_mode"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_required"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.document_type}"

    def clean(self):
        super().clean()

        if self.origin_province and self.origin_city:
            if self.origin_city.province_id != self.origin_province_id:
                raise ValidationError({
                    "origin_city": "شهر مبدا انتخاب‌شده متعلق به استان مبدا نیست."
                })

        if self.destination_country and self.destination_city:
            if self.destination_city.country_id != self.destination_country_id:
                raise ValidationError({
                    "destination_city": "شهر مقصد انتخاب‌شده متعلق به کشور مقصد نیست."
                })

        if self.destination_city and self.destination_port:
            if self.destination_port.city_id != self.destination_city_id:
                raise ValidationError({
                    "destination_port": "پورت/فرودگاه/گمرک مقصد متعلق به شهر مقصد نیست."
                })

        if self.cargo_subcategory and self.cargo_type:
            if self.cargo_subcategory.category_id != self.cargo_type_id:
                raise ValidationError({
                    "cargo_subcategory": "زیردسته انتخاب شده متعلق به دسته اصلی انتخاب‌شده نیست."
                })

        if self.cargo_type and self.transport_mode:
            if self.cargo_type.transport_mode != self.transport_mode:
                raise ValidationError({
                    "cargo_type": "دسته کالا انتخاب شده با روش حمل انتخاب‌شده همخوانی ندارد."
                })

        conditional_fields = [
            self.shipping_procedure,
            self.transport_mode,
            self.origin_province_id,
            self.origin_city_id,
            self.destination_country_id,
            self.destination_city_id,
            self.destination_port_id,
            self.cargo_type_id,
            self.cargo_subcategory_id,
        ]

        has_any_condition = any(conditional_fields)

        if self.requirement_level == DocumentRequirementLevel.GENERAL and has_any_condition:
            raise ValidationError({
                "requirement_level": "برای قانون عمومی نباید هیچ شرطی مانند رویه ارسال، مبدا، مقصد، روش حمل یا کالا انتخاب شود."
            })

        if self.requirement_level == DocumentRequirementLevel.SHIPPING_PROCEDURE and not self.shipping_procedure:
            raise ValidationError({
                "shipping_procedure": "برای سطح قانون رویه ارسال، انتخاب رویه ارسال الزامی است."
            })

        if self.requirement_level == DocumentRequirementLevel.TRANSPORT_MODE and not self.transport_mode:
            raise ValidationError({
                "transport_mode": "برای سطح قانون روش حمل، انتخاب روش حمل الزامی است."
            })

        if self.requirement_level == DocumentRequirementLevel.ORIGIN:
            if not self.origin_province and not self.origin_city:
                raise ValidationError({
                    "origin_city": "برای سطح قانون مبدا، حداقل استان یا شهر مبدا باید انتخاب شود."
                })

        if self.requirement_level == DocumentRequirementLevel.DESTINATION:
            if not self.destination_country and not self.destination_city and not self.destination_port:
                raise ValidationError({
                    "destination_country": "برای سطح قانون مقصد، حداقل کشور، شهر یا پورت مقصد باید انتخاب شود."
                })

        if self.requirement_level == DocumentRequirementLevel.CARGO_TYPE and not self.cargo_type:
            raise ValidationError({
                "cargo_type": "برای سطح قانون دسته کالا، انتخاب دسته اصلی کالا الزامی است."
            })

        if self.requirement_level == DocumentRequirementLevel.CARGO_SUBCATEGORY and not self.cargo_subcategory:
            raise ValidationError({
                "cargo_subcategory": "برای سطح قانون زیردسته کالا، انتخاب زیردسته کالا الزامی است."
            })
            
    @property
    def specificity_score(self):
        """
        برای تشخیص اختصاصی بودن قانون.
        هرچه شرط‌های بیشتری داشته باشد، امتیاز بالاتر است.
        """
        score = 0

        if self.shipping_procedure:
            score += 1
        if self.transport_mode:
            score += 1
        if self.origin_province_id:
            score += 1
        if self.origin_city_id:
            score += 1
        if self.destination_country_id:
            score += 1
        if self.destination_city_id:
            score += 1
        if self.destination_port_id:
            score += 1
        if self.cargo_type_id:
            score += 1
        if self.cargo_subcategory_id:
            score += 1

        return score


def order_document_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()

    order_id = instance.order_id or "unknown_order"
    doc_code = instance.document_type.code if instance.document_type_id else "document"

    return f"order_documents/order_{order_id}/{doc_code}/{uuid.uuid4()}{ext}"


class OrderDocument(TimeStampedModel):
    """
    مدرک موردنیاز برای یک سفارش مشخص.

    این رکوردها بهتر است هنگام ورود کاربر به مرحله مدارک ساخته شوند.
    """

    order = models.ForeignKey(
        "orders.CargoRequest",
        on_delete=models.CASCADE,
        related_name="required_documents",
        verbose_name="سفارش"
    )

    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="order_documents",
        verbose_name="نوع مدرک"
    )

    source_rule = models.ForeignKey(
        DocumentRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_documents",
        verbose_name="قانون ایجادکننده"
    )

    file = models.FileField(
        upload_to=order_document_upload_to,
        null=True,
        blank=True,
        verbose_name="فایل"
    )

    status = models.CharField(
        max_length=30,
        choices=OrderDocumentStatus.choices,
        default=OrderDocumentStatus.PENDING_UPLOAD,
        verbose_name="وضعیت"
    )

    is_required = models.BooleanField(
        default=True,
        verbose_name="اجباری"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_order_documents",
        verbose_name="آپلودکننده"
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_order_documents",
        verbose_name="بررسی‌کننده"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان بررسی"
    )

    rejection_reason = models.TextField(
        blank=True,
        verbose_name="دلیل رد"
    )

    customer_note = models.TextField(
        blank=True,
        verbose_name="توضیح مشتری"
    )

    forwarder_note = models.TextField(
        blank=True,
        verbose_name="توضیح فورواردر"
    )

    class Meta:
        verbose_name = "مدرک سفارش"
        verbose_name_plural = "مدارک سفارش"
        ordering = ["document_type__title"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "document_type"],
                name="unique_document_type_per_order"
            )
        ]

    def __str__(self):
        return f"{self.order_id} - {self.document_type}"

    def clean(self):
        super().clean()

        if self.file and self.document_type_id:
            self.validate_file()

    def validate_file(self):
        if not self.file:
            return

        filename = self.file.name
        ext = os.path.splitext(filename)[1].lower().replace(".", "")

        allowed = self.document_type.get_allowed_extensions_list()

        if ext not in allowed:
            raise ValidationError({
                "file": f"پسوند فایل مجاز نیست. پسوندهای مجاز: {', '.join(allowed)}"
            })

        max_size = self.document_type.max_file_size_mb * 1024 * 1024

        if self.file.size > max_size:
            raise ValidationError({
                "file": f"حجم فایل نباید بیشتر از {self.document_type.max_file_size_mb} مگابایت باشد."
            })

    @property
    def is_uploaded(self):
        return bool(self.file)

    def mark_uploaded(self, user=None):
        self.status = OrderDocumentStatus.UPLOADED
        if user:
            self.uploaded_by = user
        self.save(update_fields=["status", "uploaded_by", "updated_at"])

    def approve(self, user):
        self.status = OrderDocumentStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.rejection_reason = ""
        self.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ])

    def reject(self, user, reason=""):
        self.status = OrderDocumentStatus.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ])


class AdditionalDocumentRequest(TimeStampedModel):
    """
    درخواست مدرک جدید توسط فورواردر بعد از ثبت سفارش.

    این مدل یک لینک اختصاصی برای مشتری می‌سازد.
    """

    order = models.ForeignKey(
        "orders.CargoRequest",
        on_delete=models.CASCADE,
        related_name="additional_document_requests",
        verbose_name="سفارش"
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_additional_document_requests",
        verbose_name="درخواست‌کننده"
    )

    title = models.CharField(
        max_length=255,
        verbose_name="عنوان درخواست"
    )

    description = models.TextField(
        verbose_name="توضیحات برای مشتری"
    )

    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="additional_requests",
        verbose_name="نوع مدرک"
    )

    custom_document_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="عنوان مدرک سفارشی",
        help_text="اگر نوع مدرک از لیست انتخاب نشده، این فیلد پر شود."
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="توکن لینک"
    )

    status = models.CharField(
        max_length=30,
        choices=AdditionalRequestStatus.choices,
        default=AdditionalRequestStatus.OPEN,
        verbose_name="وضعیت"
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ انقضا"
    )

    sms_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان ارسال پیامک"
    )

    class Meta:
        verbose_name = "درخواست مدرک تکمیلی"
        verbose_name_plural = "درخواست‌های مدارک تکمیلی"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - Order #{self.order_id}"

    def clean(self):
        super().clean()

        if not self.document_type and not self.custom_document_title:
            raise ValidationError(
                "باید یا نوع مدرک انتخاب شود یا عنوان مدرک سفارشی وارد شود."
            )

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def document_title(self):
        if self.document_type:
            return self.document_type.title
        return self.custom_document_title

    def get_upload_url(self):
        from django.urls import reverse
        return reverse("documents:additional_upload", kwargs={"token": self.token})


def additional_document_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    request_id = instance.request_id or "unknown_request"
    return f"additional_documents/request_{request_id}/{uuid.uuid4()}{ext}"


class AdditionalDocumentUpload(TimeStampedModel):
    """
    فایل آپلود شده برای درخواست مدرک تکمیلی.
    """

    request = models.ForeignKey(
        AdditionalDocumentRequest,
        on_delete=models.CASCADE,
        related_name="uploads",
        verbose_name="درخواست"
    )

    file = models.FileField(
        upload_to=additional_document_upload_to,
        verbose_name="فایل"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="additional_document_uploads",
        verbose_name="آپلودکننده"
    )

    customer_note = models.TextField(
        blank=True,
        verbose_name="توضیح مشتری"
    )

    class Meta:
        verbose_name = "فایل مدرک تکمیلی"
        verbose_name_plural = "فایل‌های مدارک تکمیلی"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Upload for {self.request}"
