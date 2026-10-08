from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("institution", "0029_studentenrollment_admission_type_master"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE "institution_institutionholiday_new" (
                            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                            "from_date" date NOT NULL,
                            "to_date" date NOT NULL,
                            "name" varchar(255) NOT NULL,
                            "is_active" bool NOT NULL,
                            "created_at" datetime NOT NULL,
                            "updated_at" datetime NOT NULL,
                            "institution_id" bigint NOT NULL
                                REFERENCES "institution_institutionprofile" ("id")
                                DEFERRABLE INITIALLY DEFERRED,
                            "academic_session_id" bigint NULL
                                REFERENCES "institution_institutionacademicsession" ("id")
                                DEFERRABLE INITIALLY DEFERRED,
                            CONSTRAINT "unique_institution_holiday_range"
                                UNIQUE (
                                    "institution_id",
                                    "academic_session_id",
                                    "from_date",
                                    "to_date"
                                )
                        );

                        INSERT INTO "institution_institutionholiday_new"
                        (
                            "id",
                            "from_date",
                            "to_date",
                            "name",
                            "is_active",
                            "created_at",
                            "updated_at",
                            "institution_id",
                            "academic_session_id"
                        )
                        SELECT
                            "id",
                            "date",
                            "date",
                            "name",
                            "is_active",
                            "created_at",
                            "updated_at",
                            "institution_id",
                            NULL
                        FROM "institution_institutionholiday";

                        DROP TABLE "institution_institutionholiday";

                        ALTER TABLE
                            "institution_institutionholiday_new"
                        RENAME TO
                            "institution_institutionholiday";

                        CREATE INDEX
                            "institution_institutionholiday_institution_id_7fd918b3"
                        ON "institution_institutionholiday"
                            ("institution_id");

                        CREATE INDEX
                            "institution_institutionholiday_academic_session_id_idx"
                        ON "institution_institutionholiday"
                            ("academic_session_id");
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="institutionholiday",
                    name="date",
                ),
                migrations.AddField(
                    model_name="institutionholiday",
                    name="from_date",
                    field=models.DateField(),
                ),
                migrations.AddField(
                    model_name="institutionholiday",
                    name="to_date",
                    field=models.DateField(),
                ),
                migrations.AddField(
                    model_name="institutionholiday",
                    name="academic_session",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.CASCADE,
                        related_name="holidays",
                        to="institution.institutionacademicsession",
                    ),
                ),
                migrations.AlterModelOptions(
                    name="institutionholiday",
                    options={"ordering": ["from_date"]},
                ),
                migrations.RemoveConstraint(
                    model_name="institutionholiday",
                    name="unique_institution_holiday_date",
                ),
                migrations.AddConstraint(
                    model_name="institutionholiday",
                    constraint=models.UniqueConstraint(
                        fields=[
                            "institution",
                            "academic_session",
                            "from_date",
                            "to_date",
                        ],
                        name="unique_institution_holiday_range",
                    ),
                ),
            ],
        ),
    ]
