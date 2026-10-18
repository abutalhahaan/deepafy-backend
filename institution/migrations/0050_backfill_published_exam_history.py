from django.db import migrations


def mark_existing_published_exams(apps, schema_editor):
    InstitutionExam = apps.get_model("institution", "InstitutionExam")
    db_alias = schema_editor.connection.alias
    InstitutionExam.objects.using(db_alias).filter(
        is_published=True,
        has_been_published=False,
    ).update(has_been_published=True)


class Migration(migrations.Migration):
    dependencies = [
        ("institution", "0049_institutionexam_has_been_published"),
    ]

    operations = [
        migrations.RunPython(
            mark_existing_published_exams,
            migrations.RunPython.noop,
        ),
    ]
