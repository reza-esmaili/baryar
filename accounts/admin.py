from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, CustomerProfile, CustomerCompanyProfile,
    CustomerBusinessInfo, IdentityDocument
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-created_at"]
    list_display = ["mobile", "first_name", "last_name", "role", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["mobile", "first_name", "last_name", "email"]
    fieldsets = (
        (None, {"fields": ("mobile", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "email")}),
        ("دسترسی‌ها", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("mobile", "first_name", "last_name", "email", "role", "password1", "password2"),
        }),
    )


@admin.register(IdentityDocument)
class IdentityDocumentAdmin(admin.ModelAdmin):
    list_display = ["user", "doc_type", "status", "created_at"]
    list_filter = ["doc_type", "status"]
    search_fields = ["user__mobile", "user__first_name", "user__last_name"]
    actions = ["approve_docs", "reject_docs"]

    @admin.action(description="تایید مدارک انتخاب‌شده")
    def approve_docs(self, request, queryset):
        queryset.update(status=IdentityDocument.Status.APPROVED)

    @admin.action(description="رد مدارک انتخاب‌شده")
    def reject_docs(self, request, queryset):
        queryset.update(status=IdentityDocument.Status.REJECTED)


admin.site.register(CustomerProfile)
admin.site.register(CustomerCompanyProfile)
admin.site.register(CustomerBusinessInfo)
