from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    DocumentType,
    DocumentRule,
    OrderDocument,
    AdditionalDocumentRequest,
    AdditionalDocumentUpload,
    OrderDocumentStatus,
    AdditionalRequestStatus,
)


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "code",
        "allowed_extensions",
        "max_file_size_mb",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "created_at",
    ]

    search_fields = [
        "title",
        "code",
        "description",
    ]

    prepopulated_fields = {
        "code": ("title",)
    }

    ordering = ["title"]


@admin.register(DocumentRule)
class DocumentRuleAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "document_type",
        "shipping_procedure",
        "transport_mode",
        "destination_country",
        "cargo_type",
        "cargo_subcategory",
        "is_required",
        "is_active",
        "priority",
        "specificity_display",
    ]

    list_filter = [
        "is_active",
        "is_required",
        "shipping_procedure",
        "transport_mode",
        "destination_country",
        "cargo_type",
        "requirement_level",
    ]

    search_fields = [
        "title",
        "document_type__title",
        "destination_country__name",
        "cargo_type__name",
        "cargo_subcategory__name",
        "customer_description",
        "admin_note",
    ]

    autocomplete_fields = [
        "document_type",
        "destination_country",
        "cargo_type",
        "cargo_subcategory",
    ]

    fieldsets = (
        ("اطلاعات اصلی قانون", {
            "fields": (
                "title",
                "document_type",
                "is_required",
                "is_active",
                "priority",
                "requirement_level",
            )
        }),
        ("شرط‌های اعمال قانون", {
            "fields": (
                "shipping_procedure",
                "transport_mode",
                "destination_country",
                "cargo_type",
                "cargo_subcategory",
            )
        }),
        ("توضیحات", {
            "fields": (
                "customer_description",
                "admin_note",
            )
        }),
    )

    def specificity_display(self, obj):
        return obj.specificity_score

    specificity_display.short_description = "امتیاز اختصاصی بودن"


@admin.register(OrderDocument)
class OrderDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order",
        "document_type",
        "status",
        "is_required",
        "file_link",
        "uploaded_by",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    ]

    list_filter = [
        "status",
        "is_required",
        "document_type",
        "created_at",
        "reviewed_at",
    ]

    search_fields = [
        "order__id",
        "order__customer__mobile",
        "order__customer__first_name",
        "order__customer__last_name",
        "document_type__title",
        "rejection_reason",
    ]

    autocomplete_fields = [
        "order",
        "document_type",
        "source_rule",
        "uploaded_by",
        "reviewed_by",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "reviewed_at",
        "file_preview",
    ]

    actions = [
        "approve_documents",
        "reject_documents",
    ]

    fieldsets = (
        ("اطلاعات مدرک", {
            "fields": (
                "order",
                "document_type",
                "source_rule",
                "is_required",
                "status",
                "file",
                "file_preview",
            )
        }),
        ("آپلود و توضیحات", {
            "fields": (
                "uploaded_by",
                "customer_note",
                "forwarder_note",
            )
        }),
        ("بررسی", {
            "fields": (
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            )
        }),
        ("زمان‌ها", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">مشاهده فایل</a>',
                obj.file.url
            )
        return "-"

    file_link.short_description = "فایل"

    def file_preview(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">دانلود/مشاهده فایل</a>',
                obj.file.url
            )
        return "فایلی آپلود نشده است."

    file_preview.short_description = "پیش‌نمایش فایل"

    def approve_documents(self, request, queryset):
        updated = queryset.update(
            status=OrderDocumentStatus.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            rejection_reason="",
        )

        self.message_user(request, f"{updated} مدرک تایید شد.")

    approve_documents.short_description = "تایید مدارک انتخاب‌شده"

    def reject_documents(self, request, queryset):
        updated = queryset.update(
            status=OrderDocumentStatus.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )

        self.message_user(request, f"{updated} مدرک رد شد.")

    reject_documents.short_description = "رد مدارک انتخاب‌شده"


class AdditionalDocumentUploadInline(admin.TabularInline):
    model = AdditionalDocumentUpload
    extra = 0
    readonly_fields = [
        "uploaded_by",
        "file",
        "customer_note",
        "created_at",
    ]

    can_delete = False


@admin.register(AdditionalDocumentRequest)
class AdditionalDocumentRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order",
        "title",
        "document_display",
        "status",
        "requested_by",
        "expires_at",
        "upload_link",
        "sms_sent_at",
        "created_at",
    ]

    list_filter = [
        "status",
        "document_type",
        "created_at",
        "expires_at",
    ]

    search_fields = [
        "order__id",
        "order__customer__mobile",
        "order__customer__first_name",
        "order__customer__last_name",
        "title",
        "description",
        "custom_document_title",
    ]

    autocomplete_fields = [
        "order",
        "requested_by",
        "document_type",
    ]

    readonly_fields = [
        "token",
        "upload_link",
        "created_at",
        "updated_at",
        "sms_sent_at",
    ]

    inlines = [
        AdditionalDocumentUploadInline,
    ]

    fieldsets = (
        ("اطلاعات درخواست", {
            "fields": (
                "order",
                "requested_by",
                "title",
                "description",
                "document_type",
                "custom_document_title",
                "status",
            )
        }),
        ("لینک و زمان‌بندی", {
            "fields": (
                "token",
                "upload_link",
                "expires_at",
                "sms_sent_at",
            )
        }),
        ("زمان‌ها", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def document_display(self, obj):
        return obj.document_title

    document_display.short_description = "مدرک"

    def upload_link(self, obj):
        if not obj.pk:
            return "-"

        url = obj.get_upload_url()

        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            url,
            url
        )

    upload_link.short_description = "لینک آپلود"


@admin.register(AdditionalDocumentUpload)
class AdditionalDocumentUploadAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "request",
        "uploaded_by",
        "file_link",
        "created_at",
    ]

    list_filter = [
        "created_at",
    ]

    search_fields = [
        "request__title",
        "request__order__id",
        "uploaded_by__mobile",
    ]

    autocomplete_fields = [
        "request",
        "uploaded_by",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "file_link",
    ]

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">مشاهده فایل</a>',
                obj.file.url
            )
        return "-"

    file_link.short_description = "فایل"
