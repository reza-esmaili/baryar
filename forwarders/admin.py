from django.contrib import admin
from django.utils.html import format_html

from accounts.models import IdentityDocument
from .models import ForwarderCompany, ForwarderBranch, ForwarderStaff


class IdentityDocumentInline(admin.TabularInline):
    model = IdentityDocument
    extra = 0
    fields = ["doc_type", "file_link", "status", "admin_note"]
    readonly_fields = ["file_link"]

    def file_link(self, obj):
        if obj and obj.file:
            return format_html('<a href="{}" target="_blank">مشاهده فایل</a>', obj.file.url)
        return "-"
    file_link.short_description = "فایل"


class BranchInline(admin.TabularInline):
    model = ForwarderBranch
    extra = 0
    fields = ["name", "branch_user", "province", "city", "is_active"]


class StaffInline(admin.TabularInline):
    model = ForwarderStaff
    extra = 0


@admin.register(ForwarderCompany)
class ForwarderCompanyAdmin(admin.ModelAdmin):
    list_display = ["company_name", "national_id", "admin_user", "is_verified", "is_active"]
    list_filter = ["is_verified", "is_active"]
    search_fields = ["national_id", "registration_number", "company_name"]
    inlines = [IdentityDocumentInline, BranchInline, StaffInline]
    actions = ["verify_companies"]

    @admin.action(description="تایید شرکت‌های انتخاب‌شده")
    def verify_companies(self, request, queryset):
        queryset.update(is_verified=True)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        company = form.instance

        docs = company.identity_documents.all()
        if docs.exists():
            all_approved = all(doc.status == IdentityDocument.Status.APPROVED for doc in docs)
            if company.is_verified != all_approved:
                company.is_verified = all_approved
                company.save(update_fields=["is_verified"])

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        docs = obj.identity_documents.all()
        if docs.exists():
            all_approved = all(doc.status == IdentityDocument.Status.APPROVED for doc in docs)
            if obj.is_verified != all_approved:
                obj.is_verified = all_approved
                obj.save(update_fields=["is_verified"])


admin.site.register(ForwarderBranch)
admin.site.register(ForwarderStaff)
