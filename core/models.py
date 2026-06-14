from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SmsLog(models.Model):
    mobile = models.CharField(max_length=15)
    template_key = models.CharField(max_length=50) # مثلا 'otp' یا 'order_created'
    parameters = models.JSONField(default=dict)
    response_data = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mobile} - {self.template_key} - {self.status}"
