from django.db import models


class InstitutionTypeGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class InstitutionType(models.Model):
    group = models.ForeignKey(
        InstitutionTypeGroup,
        on_delete=models.PROTECT,
        related_name="institution_types",
    )
    name = models.CharField(max_length=150)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group", "sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "name"],
                name="unique_institution_type_per_group",
            )
        ]

    def __str__(self):
        return f"{self.group.name} - {self.name}"
