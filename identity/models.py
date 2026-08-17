import uuid

from django.db import models


class UserIdentity(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_VERIFICATION = "pending_verification", "Pending Verification"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"
        RESTRICTED = "restricted", "Restricted"
        LOCKED = "locked", "Locked"
        DEACTIVATED = "deactivated", "Deactivated"
        DELETED = "deleted", "Deleted"

    user_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(
        max_length=30,
        blank=True,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.user_id)


class AccountType(models.Model):
    class Type(models.TextChoices):
        PERSONAL = "personal", "Personal Account"
        PROFESSIONAL = "professional", "Professional Account"
        COMPANY = "company", "Company Account"

    identity = models.ForeignKey(
        UserIdentity,
        on_delete=models.CASCADE,
        related_name="account_types",
    )
    account_type = models.CharField(
        max_length=30,
        choices=Type.choices,
    )
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["identity", "account_type"],
                name="unique_account_type_per_identity",
            )
        ]
        ordering = ["account_type"]

    def __str__(self):
        return (
            f"{self.identity.user_id} - "
            f"{self.get_account_type_display()}"
        )


class Language(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.CharField(
        max_length=20,
        unique=True,
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

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PersonalAccount(models.Model):
    identity = models.OneToOneField(
        UserIdentity,
        on_delete=models.CASCADE,
        related_name="personal_account",
    )

    display_name = models.CharField(
        max_length=255,
        blank=True,
    )

    username = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    bio = models.TextField(
        blank=True,
    )

    mother_tongue = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mother_tongue_users",
    )

    permanent_country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personal_permanent_addresses",
    )

    permanent_city = models.CharField(
        max_length=255,
        blank=True,
    )

    permanent_area = models.CharField(
        max_length=255,
        blank=True,
    )

    permanent_full_address = models.TextField(
        blank=True,
    )

    present_country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personal_present_addresses",
    )

    present_city = models.CharField(
        max_length=255,
        blank=True,
    )

    present_area = models.CharField(
        max_length=255,
        blank=True,
    )

    present_full_address = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            self.display_name
            or self.username
            or f"Personal Account - {self.identity.user_id}"
        )


class PersonalInterestedCategory(models.Model):
    personal_account = models.ForeignKey(
        PersonalAccount,
        on_delete=models.CASCADE,
        related_name="interested_categories",
    )

    category = models.ForeignKey(
        "category_engine.Category",
        on_delete=models.PROTECT,
        related_name="personal_interested_categories",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["personal_account", "category"],
                name="unique_personal_interested_category",
            )
        ]
        ordering = ["category__name"]

    def __str__(self):
        return (
            f"{self.personal_account.identity.user_id} - "
            f"{self.category.name}"
        )


class Hobby(models.Model):
    name = models.CharField(
        max_length=100,
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class PersonalHobby(models.Model):
    personal_account = models.ForeignKey(
        PersonalAccount,
        on_delete=models.CASCADE,
        related_name="hobbies",
    )

    hobby = models.ForeignKey(
        Hobby,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personal_selections",
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["personal_account", "hobby"],
                name="unique_personal_hobby",
            )
        ]
        ordering = ["hobby__display_order", "hobby__name"]

    def __str__(self):
        return (
            f"{self.personal_account.identity.user_id} - "
            f"{self.hobby.name}"
        )


class ProfessionalAccount(models.Model):
    identity = models.OneToOneField(
        UserIdentity,
        on_delete=models.CASCADE,
        related_name="professional_account",
    )

    professional_title = models.CharField(
        max_length=255,
        blank=True,
    )

    profession = models.CharField(
        max_length=255,
        blank=True,
    )

    industry = models.CharField(
        max_length=255,
        blank=True,
    )

    professional_summary = models.TextField(
        blank=True,
    )

    focus_job_area = models.TextField(
        blank=True,
    )

    future_goal = models.TextField(
        blank=True,
    )

    background_color = models.CharField(
        max_length=20,
        default="#FFFFFF",
    )

    tab_colors = models.JSONField(
        default=dict,
        blank=True,
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
        return f"Professional Account - {self.identity.user_id}"


class AcademicBackground(models.Model):
    professional_account = models.ForeignKey(
        ProfessionalAccount,
        on_delete=models.CASCADE,
        related_name="academic_backgrounds",
    )

    qualification = models.CharField(
        max_length=255,
    )

    institution = models.CharField(
        max_length=255,
    )

    field_of_study = models.CharField(
        max_length=255,
        blank=True,
    )

    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="academic_backgrounds",
    )

    city = models.CharField(
        max_length=255,
        blank=True,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    is_current = models.BooleanField(
        default=False,
    )

    result = models.CharField(
        max_length=100,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
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

    class Meta:
        ordering = [
            "display_order",
            "-start_date",
            "qualification",
        ]

    def __str__(self):
        return (
            f"{self.qualification} - "
            f"{self.institution}"
        )


class JobExperience(models.Model):
    professional_account = models.ForeignKey(
        ProfessionalAccount,
        on_delete=models.CASCADE,
        related_name="job_experiences",
    )

    company = models.CharField(
        max_length=255,
    )

    job_title = models.CharField(
        max_length=255,
    )

    employment_type = models.CharField(
        max_length=100,
        blank=True,
    )

    location = models.CharField(
        max_length=255,
        blank=True,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    is_current = models.BooleanField(
        default=False,
    )

    description = models.TextField(
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
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
        return f"{self.job_title} - {self.company}"


class Skill(models.Model):
    name = models.CharField(
        max_length=200,
        unique=True,
    )

    slug = models.SlugField(
        unique=True,
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
        return self.name


class ProfessionalSkill(models.Model):

    class SkillLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        EXPERT = "expert", "Expert"

    professional_account = models.ForeignKey(
        ProfessionalAccount,
        on_delete=models.CASCADE,
        related_name="skills",
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
    )

    skill_level = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,
        default=SkillLevel.INTERMEDIATE,
    )

    years_of_experience = models.PositiveIntegerField(
        default=0,
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

    class Meta:
        unique_together = (
            "professional_account",
            "skill",
        )

    def __str__(self):
        return (
            f"{self.professional_account.id} - "
            f"{self.skill.name}"
        )