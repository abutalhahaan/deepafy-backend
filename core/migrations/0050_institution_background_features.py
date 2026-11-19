from django.db import migrations


FEATURES = [
    {
        "feature_key": "institution_background_color",
        "feature_name": "Institution Background Color",
        "account_type": "institution",
        "category": "Institution Appearance",
        "is_enabled": True,
        "access_level": "free",
        "trial_enabled": False,
        "trial_days": 0,
        "description": "Customize the institution profile background color.",
    },
    {
        "feature_key": "institution_background_image",
        "feature_name": "Institution Background Image",
        "account_type": "institution",
        "category": "Institution Appearance",
        "is_enabled": True,
        "access_level": "free",
        "trial_enabled": False,
        "trial_days": 0,
        "description": "Upload and customize the institution profile background image.",
    },
]


def add_institution_features(apps, schema_editor):
    FeatureAccessControl = apps.get_model("core", "FeatureAccessControl")
    database = schema_editor.connection.alias

    for feature in FEATURES:
        FeatureAccessControl.objects.using(database).get_or_create(
            feature_key=feature["feature_key"],
            account_type="institution",
            defaults=feature,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0049_seed_builtin_animations"),
    ]

    operations = [
        migrations.RunPython(
            add_institution_features,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
