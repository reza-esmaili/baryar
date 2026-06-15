from django.contrib import admin
# orders/admin.py
from .models import CargoRequest

@admin.register(CargoRequest)
class CargoRequestAdmin(admin.ModelAdmin):
    # این فیلد برای حل خطای E039 ضروری است
    search_fields = ['tracking_code', 'customer__user__username'] 
    # بقیه تنظیمات قبلی شما...
