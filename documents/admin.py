from django.contrib import admin
from django import forms

from locations.models import City, DestinationCity, Port

from .models import (
    AdditionalDocumentRequest,
    AdditionalDocumentUpload,
    DocumentRule,
    DocumentType,
    OrderDocument,
)


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "code",
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

    ordering = [
        "title",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

class DocumentRuleAdminForm(forms.ModelForm):
    class Meta:
        model = DocumentRule
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # در حالت اولیه، فیلدهای وابسته را خالی می‌کنیم
        self.fields["origin_city"].queryset = City.objects.filter(is_active=True)
        self.fields["destination_city"].queryset = DestinationCity.objects.filter(is_active=True)
        self.fields["destination_port"].queryset = Port.objects.filter(is_active=True)


        # -------------------------
        # Origin City
        # -------------------------
        if "origin_province" in self.data:
            try:
                province_id = int(self.data.get("origin_province"))
                self.fields["origin_city"].queryset = City.objects.filter(
                    province_id=province_id,
                    is_active=True
                ).order_by("name")
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.origin_province_id:
            self.fields["origin_city"].queryset = City.objects.filter(
                province_id=self.instance.origin_province_id,
                is_active=True
            ).order_by("name")

        # اگر instance شهر دارد ولی استان ندارد، برای جلوگیری از ناپدید شدن مقدار قبلی
        elif self.instance.pk and self.instance.origin_city_id:
            self.fields["origin_city"].queryset = City.objects.filter(
                pk=self.instance.origin_city_id
            )

        # -------------------------
        # Destination City
        # -------------------------
        if "destination_country" in self.data:
            try:
                country_id = int(self.data.get("destination_country"))
                self.fields["destination_city"].queryset = DestinationCity.objects.filter(
                    country_id=country_id,
                    is_active=True
                ).order_by("name")
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.destination_country_id:
            self.fields["destination_city"].queryset = DestinationCity.objects.filter(
                country_id=self.instance.destination_country_id,
                is_active=True
            ).order_by("name")

        elif self.instance.pk and self.instance.destination_city_id:
            self.fields["destination_city"].queryset = DestinationCity.objects.filter(
                pk=self.instance.destination_city_id
            )

        # -------------------------
        # Destination Port
        # -------------------------
        if "destination_city" in self.data:
            try:
                city_id = int(self.data.get("destination_city"))
                self.fields["destination_port"].queryset = Port.objects.filter(
                    city_id=city_id,
                    is_active=True
                ).order_by("name")
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.destination_city_id:
            self.fields["destination_port"].queryset = Port.objects.filter(
                city_id=self.instance.destination_city_id,
                is_active=True
            ).order_by("name")

        elif self.instance.pk and self.instance.destination_port_id:
            self.fields["destination_port"].queryset = Port.objects.filter(
                pk=self.instance.destination_port_id
            )


@admin.register(DocumentRule)
class DocumentRuleAdmin(admin.ModelAdmin):
    form = DocumentRuleAdminForm

    list_display = [
        "title",
        "document_type",
        "requirement_level",
        "shipping_procedure",
        "transport_mode",
        "origin_province",
        "origin_city",
        "destination_country",
        "destination_city",
        "destination_port",
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
        "requirement_level",
        "shipping_procedure",
        "transport_mode",
        "origin_province",
        "origin_city",
        "destination_country",
        "destination_city",
        "destination_port",
        "cargo_type",
        "cargo_subcategory",
    ]

    search_fields = [
        "title",
        "document_type__title",
        "document_type__code",
        "origin_province__name",
        "origin_city__name",
        "destination_country__name",
        "destination_city__name",
        "destination_port__name",
        "destination_port__code",
        "cargo_type__name",
        "cargo_subcategory__name",
        "customer_description",
        "admin_note",
    ]

    autocomplete_fields = [
        "document_type",
        "cargo_type",
        "cargo_subcategory",
    ]

    readonly_fields = [
        "specificity_display",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "اطلاعات اصلی قانون",
            {
                "fields": (
                    "title",
                    "document_type",
                    "requirement_level",
                    "is_required",
                    "is_active",
                    "priority",
                    "specificity_display",
                )
            },
        ),
        (
            "شرط‌های اعمال قانون",
            {
                "fields": (
                    "shipping_procedure",
                    "transport_mode",
                    "origin_province",
                    "origin_city",
                    "destination_country",
                    "destination_city",
                    "destination_port",
                    "cargo_type",
                    "cargo_subcategory",
                )
            },
        ),
        (
            "توضیحات",
            {
                "fields": (
                    "customer_description",
                    "admin_note",
                )
            },
        ),
        (
            "زمان‌ها",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    ordering = [
        "-priority",
        "title",
    ]

    class Media:
        js = (
            "admin/documents/documentrule_dynamic.js",
            "admin/documents/documentrule_dependent_fields.js",
        )

    @admin.display(description="امتیاز اختصاصی بودن")
    def specificity_display(self, obj):
        return obj.specificity_score

@admin.register(OrderDocument)
class OrderDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "document_type",
        "status",
        "is_required",
        "uploaded_by",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    ]

    list_filter = [
        "status",
        "is_required",
        "reviewed_at",
        "created_at",
        "document_type",
    ]

    search_fields = [
        "order__id",
        "document_type__title",
        "document_type__code",
        "uploaded_by__username",
        "uploaded_by__first_name",
        "uploaded_by__last_name",
        "reviewed_by__username",
        "reviewed_by__first_name",
        "reviewed_by__last_name",
        "admin_note",
    ]

    autocomplete_fields = [
        "order",
        "document_type",
        "uploaded_by",
        "reviewed_by",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "reviewed_at",
    ]

    fieldsets = (
        (
            "اطلاعات اصلی",
            {
                "fields": (
                    "order",
                    "document_type",
                    "is_required",
                    "status",
                )
            },
        ),
        (
            "فایل",
            {
                "fields": (
                    "file",
                    "uploaded_by",
                )
            },
        ),
        (
            "بررسی",
            {
                "fields": (
                    "reviewed_by",
                    "reviewed_at",
                    "admin_note",
                )
            },
        ),
        (
            "زمان‌ها",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    ordering = [
        "-created_at",
    ]


@admin.register(AdditionalDocumentRequest)
class AdditionalDocumentRequestAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "document_type",
        "requested_by",
        "status",
        "created_at",
        "expires_at",
    ]

    list_filter = [
        "status",
        "created_at",
        "expires_at",
        "document_type",
    ]

    search_fields = [
        "order__id",
        "document_type__title",
        "document_type__code",
        "requested_by__username",
        "requested_by__first_name",
        "requested_by__last_name",
        "description",
        "admin_note",
    ]

    autocomplete_fields = [
        "order",
        "document_type",
        "requested_by",
    ]

    readonly_fields = [
        "token",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "اطلاعات درخواست",
            {
                "fields": (
                    "order",
                    "document_type",
                    "requested_by",
                    "status",
                    "token",
                    "expires_at",
                )
            },
        ),
        (
            "توضیحات",
            {
                "fields": (
                    "description",
                    "admin_note",
                )
            },
        ),
        (
            "زمان‌ها",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    ordering = [
        "-created_at",
    ]

@admin.register(AdditionalDocumentUpload)
class AdditionalDocumentUploadAdmin(admin.ModelAdmin):
    list_display = [
        "request",
        "created_at",
    ]

    list_filter = [
        "created_at",
        "request__status",
        "request__document_type",
    ]

    search_fields = [
        "request__order__id",
        "request__document_type__title",
        "request__document_type__code",
        "note",
    ]

    autocomplete_fields = [
        "request",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "اطلاعات آپلود",
            {
                "fields": (
                    "request",
                    "file",
                    "note",
                )
            },
        ),
        (
            "زمان‌ها",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    ordering = [
        "-created_at",
    ]
