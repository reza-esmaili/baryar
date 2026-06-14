from django.contrib import admin
from .models import (
    Ticket,
    TicketMessage,
    TicketTransfer,
    SupportDepartment,
    TicketTopic,
    SupportAgent,
)


# =========================
# Inline: Messages
# =========================
class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1
    readonly_fields = ("created_at",)
    fields = ("message", "attachment", "created_at")
    ordering = ("created_at",)


# =========================
# Inline: Transfers
# =========================
class TicketTransferInline(admin.TabularInline):
    model = TicketTransfer
    extra = 0
    readonly_fields = ("created_at",)
    ordering = ("created_at",)


# =========================
# Department Admin
# =========================
@admin.register(SupportDepartment)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sla_response_minutes",
        "sla_resolve_minutes",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)


# =========================
# Topic Admin
# =========================
@admin.register(TicketTopic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("title",)


# =========================
# Agent Admin
# =========================
@admin.register(SupportAgent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("user", "is_supervisor", "is_active")
    list_filter = ("is_supervisor", "is_active")
    filter_horizontal = ("departments",)


# =========================
# Ticket Admin
# =========================
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    inlines = [TicketMessageInline, TicketTransferInline]

    list_display = (
        "id",
        "number",
        "user",
        "subject",
        "status",
        "department",
        "priority",
        "created_at",
    )

    list_filter = (
        "department",
        "priority",
        "status",
    )

    search_fields = (
        "number",
        "subject",
        "user__mobile",
    )

    readonly_fields = ("created_at",)

    # ✅ مدیریت ذخیره پیام‌ها و تغییر وضعیت تیکت
    def save_formset(self, request, form, formset, change):
        if formset.model == TicketMessage:

            instances = formset.save(commit=False)

            for instance in instances:

                is_new = instance.pk is None

                # اگر پیام جدید است
                if is_new:
                    instance.sender = request.user

                instance.save()

                # ✅ اگر پیام جدید بود و تیکت بسته نبود
                if is_new:
                    ticket = instance.ticket

                    if ticket.status != "closed":
                        ticket.status = "answered"
                        ticket.save()

            formset.save_m2m()

        else:
            super().save_formset(request, form, formset, change)
