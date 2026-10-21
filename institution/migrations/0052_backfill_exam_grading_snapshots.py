from django.db import migrations


def backfill_grading_snapshots(apps, schema_editor):
    InstitutionExam = apps.get_model("institution", "InstitutionExam")
    InstitutionGradeRange = apps.get_model("institution", "InstitutionGradeRange")
    db_alias = schema_editor.connection.alias

    exams = (
        InstitutionExam.objects.using(db_alias)
        .filter(has_been_published=True, grading_snapshot__isnull=True)
        .exclude(grade_scale_id__isnull=True)
        .select_related("grade_scale")
        .iterator()
    )

    for exam in exams:
        scale = exam.grade_scale
        if scale is None:
            continue

        ranges = (
            InstitutionGradeRange.objects.using(db_alias)
            .filter(grade_scale_id=scale.id)
            .order_by("min_percentage", "id")
        )

        exam.grading_snapshot = {
            "grade_scale_id": scale.id,
            "name": scale.name,
            "maximum_gpa": str(scale.maximum_gpa),
            "is_active": scale.is_active,
            "ranges": [
                {
                    "id": item.id,
                    "grade_name": item.grade_name,
                    "min_percentage": str(item.min_percentage),
                    "max_percentage": str(item.max_percentage),
                    "grade_point": (
                        str(item.grade_point)
                        if item.grade_point is not None
                        else None
                    ),
                }
                for item in ranges
            ],
        }
        exam.save(
            using=db_alias,
            update_fields=["grading_snapshot"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("institution", "0051_institutionexam_grading_snapshot"),
    ]

    operations = [
        migrations.RunPython(
            backfill_grading_snapshots,
            migrations.RunPython.noop,
        ),
    ]
