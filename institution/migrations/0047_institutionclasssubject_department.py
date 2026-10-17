from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("institution", "0046_institutionprofile_departments"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="institutionclasssubject",
            name="unique_inst_level_period_subject",
        ),
        migrations.AddField(
            model_name="institutionclasssubject",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="institution_class_subjects",
                to="institution.department",
            ),
        ),
        migrations.AddConstraint(
            model_name="institutionclasssubject",
            constraint=models.UniqueConstraint(
                fields=(
                    "institution",
                    "academic_level",
                    "department",
                    "academic_period",
                    "subject",
                ),
                name="unique_inst_level_period_subject",
            ),
        ),
    ]
