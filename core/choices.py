from django.db import models

class ShippingProcedure(models.TextChoices):
    PASSENGER = "passenger", "مسافری"
    COMMERCIAL = "commercial", "تجاری"
