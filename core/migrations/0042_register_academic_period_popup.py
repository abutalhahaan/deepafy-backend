from django.db import migrations


def register_popup(apps, schema_editor):
    Registry = apps.get_model("core", "CentralPopupRegistry")
    Registry.objects.get_or_create(
        popup_id="academic-period-management",
        defaults={
            "popup_name": "Academic Period Management",
            "popup_type": "custom",
            "is_active": True,
            "display_order": 50,
        },
    )


def unregister_popup(apps, schema_editor):
    Registry = apps.get_model("core", "CentralPopupRegistry")
    Registry.objects.filter(
        popup_id="academic-period-management"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0041_register_academic_central_popups"),
    ]

    operations = [
        migrations.RunPython(register_popup, unregister_popup),
    ]
