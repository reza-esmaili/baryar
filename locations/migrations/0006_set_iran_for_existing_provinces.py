from django.db import migrations


def set_iran_for_existing_provinces(apps, schema_editor):
    Country = apps.get_model("locations", "Country")
    Province = apps.get_model("locations", "Province")

    iran, created = Country.objects.get_or_create(
        code="IRN",
        defaults={
            "name": "ایران",
            "is_active": True,
        }
    )

    Province.objects.filter(country__isnull=True).update(country=iran)


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0005_province_country_alter_province_unique_together"),
    ]

    operations = [
        migrations.RunPython(set_iran_for_existing_provinces, migrations.RunPython.noop),
    ]
