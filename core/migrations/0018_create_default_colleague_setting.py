from django.db import migrations


def create_default_colleague_setting(apps, schema_editor):
    ColleagueSetting = apps.get_model("core", "ColleagueSetting")
    ColleagueSetting.objects.get_or_create(
        id=1,
        defaults={
            "is_enabled": True,
            "allow_user_remove": False,
            "allow_status_change": True,
            "require_mutual_confirmation": True,
            "running_status_enabled": True,
            "previous_status_enabled": True,
        },
    )


def remove_default_colleague_setting(apps, schema_editor):
    ColleagueSetting = apps.get_model("core", "ColleagueSetting")
    ColleagueSetting.objects.filter(id=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_colleaguesetting"),
    ]

    operations = [
        migrations.RunPython(
            create_default_colleague_setting,
            remove_default_colleague_setting,
        ),
    ]
