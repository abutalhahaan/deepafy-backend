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


class InstitutionAffiliationType(models.TextChoices):
    EDUCATION_BOARD = "education_board", "Education Board"
    ACADEMIC_AFFILIATION = "academic_affiliation", "Academic Affiliation"
    REGULATORY_AUTHORITY = "regulatory_authority", "Regulatory Authority"
    GOVERNING_AUTHORITY = "governing_authority", "Governing Authority"


class InstitutionAuthority(models.Model):
    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        related_name="institution_authorities",
    )

    institution_types = models.ManyToManyField(
        InstitutionType,
        related_name="authorities",
        blank=True,
    )

    name = models.CharField(max_length=255)

    short_name = models.CharField(
        max_length=100,
        blank=True,
    )

    relationship_type = models.CharField(
        max_length=40,
        choices=InstitutionAffiliationType.choices,
    )

    code = models.CharField(
        max_length=100,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "country",
                    "name",
                    "relationship_type",
                ],
                name="unique_country_authority_relationship",
            )
        ]

    def __str__(self):
        return self.name


class InstitutionAcademicLevel(models.Model):
    institution = models.ForeignKey(
        "InstitutionProfile",
        on_delete=models.CASCADE,
        related_name="academic_levels",
    )

    level_type = models.CharField(
        max_length=50,
        default="Class",
    )

    name = models.CharField(
        max_length=100,
    )

    parent = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "institution",
                    "level_type",
                    "name",
                    "parent",
                ],
                name="unique_institution_academic_level",
            )
        ]
        indexes = [
            models.Index(
                fields=["institution", "level_type"],
                name="academic_level_inst_type_idx",
            ),
            models.Index(
                fields=["institution", "name"],
                name="academic_level_inst_name_idx",
            ),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.level_type}: {self.name} ({self.parent})"
        return f"{self.level_type}: {self.name}"


class InstitutionAcademicData(models.Model):
    institution = models.ForeignKey(
        "InstitutionProfile",
        on_delete=models.CASCADE,
        related_name="academic_data",
    )

    date = models.DateField()

    category = models.CharField(
        max_length=100,
        help_text="Students, Teachers, Staff, Class 1, Class 2, etc.",
    )

    total = models.PositiveIntegerField(default=0)
    male = models.PositiveIntegerField(default=0)
    female = models.PositiveIntegerField(default=0)

    # Daily gender-wise attendance
    male_present = models.PositiveIntegerField(default=0)
    male_leave = models.PositiveIntegerField(default=0)
    female_present = models.PositiveIntegerField(default=0)
    female_leave = models.PositiveIntegerField(default=0)

    # Calculated aggregate attendance
    present = models.PositiveIntegerField(default=0)
    leave = models.PositiveIntegerField(default=0)
    absent = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "category"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "date", "category"],
                name="unique_institution_academic_date_category",
            )
        ]
        indexes = [
            models.Index(
                fields=["institution", "date"],
                name="academic_institution_date_idx",
            ),
            models.Index(
                fields=["institution", "category"],
                name="academic_inst_cat_idx",
            ),
        ]

    def __str__(self):
        return f"{self.institution.institution_name} - {self.category} - {self.date}"


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

    affiliations = models.ManyToManyField(
        InstitutionAuthority,
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

    mission = models.TextField(
        blank=True,
    )

    vision = models.TextField(
        blank=True,
    )

    total_students = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    total_teachers = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    total_staff = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    management_type = models.CharField(
        max_length=30,
        blank=True,
        choices=[
            ('government', 'Government'),
            ('non_government', 'Non-Government'),
        ],
    )

    mpo_status = models.CharField(
        max_length=30,
        blank=True,
        choices=[
            ('mpo', 'MPO'),
            ('non_mpo', 'Non-MPO'),
            ('not_applicable', 'Not Applicable'),
        ],
    )

    institution_code = models.CharField(
        max_length=100,
        blank=True,
    )

    eiin = models.CharField(
        max_length=50,
        blank=True,
    )

    affiliation_board = models.CharField(
        max_length=255,
        blank=True,
    )

    map_location_url = models.URLField(
        max_length=1000,
        blank=True,
    )

    map_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    map_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
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

    featured_image = models.ImageField(
        upload_to="institution_featured/",
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
