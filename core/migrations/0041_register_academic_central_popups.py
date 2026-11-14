from django.db import migrations


def register_popups(apps, schema_editor):
    Registry = apps.get_model("core", "CentralPopupRegistry")
    popups = [
        ("add-academic-session", "Add Academic Session", 10),
        ("add-academic-level", "Add Academic Level", 20),
        ("add-subject", "Add Subject", 30),
        ("add-department", "Add Department", 40),
    ]
    for popup_id, popup_name, order in popups:
        Registry.objects.get_or_create(
            popup_id=popup_id,
            defaults={"popup_name": popup_name, "popup_type": "custom", "is_active": True, "display_order": order},
        )


def unregister_popups(apps, schema_editor):
    Registry = apps.get_model("core", "CentralPopupRegistry")
    Registry.objects.filter(popup_id__in=[
        "add-academic-session", "add-academic-level", "add-subject", "add-department"
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0040_calendar_calendarcountry_usercalendarfavorite")]
    operations = [migrations.RunPython(register_popups, unregister_popups)]
