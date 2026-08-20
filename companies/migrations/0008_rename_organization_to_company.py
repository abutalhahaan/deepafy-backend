import django.db.models
import django.db.models.deletion
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0015_rename_proficiency_level_personallanguage_proficiency_and_more"),
        ("organization", "0007_countrydepartment"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="organizationrelationship",
            name="unique_organization_identity_relationship",
        ),

        migrations.RenameModel(
            old_name="Organization",
            new_name="Company",
        ),

        migrations.RenameModel(
            old_name="OrganizationRelationship",
            new_name="CompanyRelationship",
        ),

        migrations.RenameField(
            model_name="company",
            old_name="organization_id",
            new_name="company_id",
        ),

        migrations.RenameField(
            model_name="company",
            old_name="organization_type",
            new_name="company_type",
        ),

        migrations.RenameField(
            model_name="companyrelationship",
            old_name="organization",
            new_name="company",
        ),

        migrations.AlterField(
            model_name="companyrelationship",
            name="identity",
            field=django.db.models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="company_relationships",
                to="identity.useridentity",
            ),
        ),

        migrations.AlterModelOptions(
            name="companyrelationship",
            options={
                "ordering": ["company", "relationship_type"],
            },
        ),

        migrations.AddConstraint(
            model_name="companyrelationship",
            constraint=django.db.models.UniqueConstraint(
                fields=("company", "identity"),
                name="unique_company_identity_relationship",
            ),
        ),
    ]