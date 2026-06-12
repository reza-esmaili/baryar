from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Rate


@receiver(post_save, sender=Rate)
def deactivate_expired_rate(sender, instance, **kwargs):
    if instance.valid_until < timezone.now().date() and instance.is_active:
        Rate.objects.filter(pk=instance.pk).update(is_active=False)
