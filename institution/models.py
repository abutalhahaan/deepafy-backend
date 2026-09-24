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


class InstitutionProfile(models.Model):
    identity = models.OneToOneField(
        "identity.UserIdentity",
        on_delete=models.CASCADE,
        related_name="institution_profile",
    )

    institution_name = models.CharField(
        max_length=255,
    )

    institution_type = models.ForeignKey(
        InstitutionType,
        on_delete=models.PROTECT,
        related_name="institutions",
    )

    institution_types = models.ManyToManyField(
        InstitutionType,
        related_name="institution_profiles",
        blank=True,
    )

    established_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    tagline = models.CharField(
        max_length=500,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        related_name="institution_profiles",
    )

    administrative_location = models.ForeignKey(
        "organization.AdministrativeLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="institution_profiles",
    )

    full_address = models.TextField(
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    logo = models.ImageField(
        upload_to="institution_logos/",
        null=True,
        blank=True,
    )

    cover_photo = models.ImageField(
        upload_to="institution_covers/",
        null=True,
        blank=True,
    )

    background_color = models.CharField(
        max_length=20,
        default="#FFFFFF",
    )

    background_image = models.ImageField(
        upload_to="institution_backgrounds/",
        null=True,
        blank=True,
    )

    tab_colors = models.JSONField(
        default=dict,
        blank=True,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            self.institution_name
            or f"Institution - {self.identity.user_id}"
        )
