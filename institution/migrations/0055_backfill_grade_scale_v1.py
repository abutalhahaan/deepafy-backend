from django.db import migrations


def create_initial_versions(apps, schema_editor):
    GradeScale = apps.get_model("institution", "InstitutionGradeScale")
    GradeRange = apps.get_model("institution", "InstitutionGradeRange")
    GradeScaleVersion = apps.get_model(
        "institution", "InstitutionGradeScaleVersion"
    )

    db_alias = schema_editor.connection.alias

    for scale in GradeScale.objects.using(db_alias).all().iterator():
        existing = GradeScaleVersion.objects.using(db_alias).filter(
            grade_scale_id=scale.pk,
            version_number=1,
        ).first()

        if existing is None:
            ranges = list(
                GradeRange.objects.using(db_alias)
                .filter(grade_scale_id=scale.pk)
                .order_by("-min_percentage", "grade_name")
                .values(
                    "grade_name",
                    "min_percentage",
                    "max_percentage",
                    "grade_point",
                )
            )

            snapshot = [
                {
                    "grade_name": item["grade_name"],
                    "min_percentage": str(item["min_percentage"]),
                    "max_percentage": str(item["max_percentage"]),
                    "grade_point": (
                        str(item["grade_point"])
                        if item["grade_point"] is not None
                        else None
                    ),
                }
                for item in ranges
            ]

            existing = GradeScaleVersion.objects.using(db_alias).create(
                grade_scale_id=scale.pk,
                version_number=1,
                name=scale.name,
                maximum_gpa=scale.maximum_gpa,
                ranges_snapshot=snapshot,
                is_active=bool(scale.is_active),
            )

        if scale.is_active and scale.active_version_id is None:
            GradeScale.objects.using(db_alias).filter(pk=scale.pk).update(
                active_version_id=existing.pk
            )


class Migration(migrations.Migration):
    dependencies = [
        ("institution", "0054_institutiongradescale_active_version"),
    ]

    operations = [
        migrations.RunPython(
            create_initial_versions,
            migrations.RunPython.noop,
        ),
    ]
