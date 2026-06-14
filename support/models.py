from django.db import models, transaction
from django.db.models import Max
from django.db.models.functions import Substr, Cast
from django.conf import settings

class PanelType(models.TextChoices):
    FORWARDER = "forwarder", "فورواردر"
    CUSTOMER = "customer", "مشتری"


class SupportDepartment(models.Model):
    name = models.CharField(max_length=120)
    panel_type = models.CharField(
        max_length=20,
        choices=PanelType.choices,
        default=PanelType.CUSTOMER
    )
    is_active = models.BooleanField(default=True)
    sla_response_minutes = models.IntegerField(default=60)
    sla_resolve_minutes = models.IntegerField(default=1440)

    def __str__(self):
        return f"{self.name} ({self.get_panel_type_display()})"


class TicketTopic(models.Model):
    department = models.ForeignKey(
        SupportDepartment,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    title = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.department} - {self.title}"


class SupportAgent(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    departments = models.ManyToManyField(
        SupportDepartment,
        related_name="agents"
    )
    is_supervisor = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.user)


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "باز"
        PENDING = "pending", "در انتظار کاربر"
        ANSWERED = "answered", "پاسخ داده شد"
        CLOSED = "closed", "بسته شد"

    class Priority(models.TextChoices):
        LOW = "low", "کم"
        NORMAL = "normal", "عادی"
        HIGH = "high", "زیاد"
        URGENT = "urgent", "فوری"

    number = models.CharField(
        max_length=20,
        unique=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    department = models.ForeignKey(
        SupportDepartment,
        on_delete=models.PROTECT
    )
    topic = models.ForeignKey(
        TicketTopic,
        on_delete=models.PROTECT
    )
    subject = models.CharField(max_length=255)
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    assigned_agent = models.ForeignKey(
        SupportAgent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    unread_for_user = models.BooleanField(default=False)
    unread_for_agent = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.number:
            # تعیین پیشوند بر اساس پنل
            prefix = "FWD" if self.department.panel_type == PanelType.FORWARDER else "CUS"
            
            with transaction.atomic():
                # پیدا کردن آخرین شماره ثبت شده برای این پنل خاص
                # فیلتر کردن بر اساس پیشوند برای جدا سازی شماره ها
                last_number_entry = Ticket.objects.filter(
                    number__startswith=f"{prefix}-"
                ).annotate(
                    numeric_part=Cast(Substr('number', 5), models.IntegerField())
                ).aggregate(max_val=Max('numeric_part'))['max_val'] or 0
                
                new_number = last_number_entry + 1
                self.number = f"{prefix}-{new_number:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.number


class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    message = models.TextField()
    attachment = models.FileField(
        upload_to="tickets/attachments/",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket.number} message"


class TicketTransfer(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="transfers"
    )
    from_department = models.ForeignKey(
        SupportDepartment,
        on_delete=models.PROTECT,
        related_name="transfer_from"
    )
    to_department = models.ForeignKey(
        SupportDepartment,
        on_delete=models.PROTECT,
        related_name="transfer_to"
    )
    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TicketActivity(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="activities"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
