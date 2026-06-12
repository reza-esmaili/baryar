from django.contrib import admin
from .models import ForwarderCompany, ForwarderBranch, ForwarderStaff


class BranchInline(admin.TabularInline):
    model = ForwarderBranch
    extra = 0
    fields = ["name", "branch_user", "province", "city", "is_active"]


class StaffInline(admin.TabularInline):
    model = ForwarderStaff
    extra = 0


@admin.register(ForwarderCompany)
class ForwarderCompanyAdmin(admin.ModelAdmin):
    list_display = ["company_name" , "national_id", "admin_user", "is_verified", "is_active"]
    list_filter = ["is_verified", "is_active"]
    search_fields = ["national_id", "registration_number"]
    inlines = [BranchInline, StaffInline]
    actions = ["verify_companies"]

    @admin.action(description="تایید شرکت‌های انتخاب‌شده")
    def verify_companies(self, request, queryset):
        queryset.update(is_verified=True)


admin.site.register(ForwarderBranch)
admin.site.register(ForwarderStaff)
