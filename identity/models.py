import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models


class UserIdentity(AbstractBaseUser):
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

    password = models.CharField(
        max_length=128,
        default="!",
    ) 

    first_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    username = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )

    email = models.EmailField(
        unique=True,
    )

    mobile_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
    )

    is_email_verified = models.BooleanField(
        default=False,
    )

    is_mobile_verified = models.BooleanField(
        default=False,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
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

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.username or self.email or str(self.user_id)


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

class PersonalLanguage(models.Model):
    class Proficiency(models.TextChoices):
        BASIC = "basic", "Basic"
        CONVERSATIONAL = "conversational", "Conversational"
        FLUENT = "fluent", "Fluent"
        NATIVE = "native", "Native"

    personal_account = models.ForeignKey(
        "PersonalAccount",
        on_delete=models.CASCADE,
        related_name="languages",
    )

    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name="personal_languages",
    )

    proficiency = models.CharField(
        max_length=30,
        choices=Proficiency.choices,
        default=Proficiency.CONVERSATIONAL,
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
                fields=["personal_account", "language"],
                name="unique_personal_language",
            )
        ]
        ordering = ["language__name"]

    def __str__(self):
        return (
            f"{self.personal_account.identity.user_id} - "
            f"{self.language.name}"
        )

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

    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        null=True,
        blank=True,
    )

    cover_photo = models.ImageField(
        upload_to="cover_photos/",
        null=True,
        blank=True,
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
    )

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        PREFER_NOT_TO_SAY = (
            "prefer_not_to_say",
            "Prefer not to say",
        )

    gender = models.CharField(
        max_length=30,
        choices=Gender.choices,
        blank=True,
    )

    nationality = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personal_nationalities",
    )

    background_color = models.CharField(
        max_length=20,
        default="#FFFFFF",
    )

    background_image = models.ImageField(
        upload_to="personal_backgrounds/",
        null=True,
        blank=True,
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

    background_image = models.ImageField(
        upload_to="professional_backgrounds/",
        null=True,
        blank=True,
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
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        CONNECTIONS = "connections", "Connections"
        PRIVATE = "private", "Private"

    personal_account = models.ForeignKey(
        PersonalAccount,
        on_delete=models.CASCADE,
        related_name="academic_backgrounds",
        null=True,
        blank=True,
    )

    institution_name = models.CharField(
        max_length=255,
    )

    institution_type = models.CharField(
        max_length=100,
    )

    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        related_name="personal_academic_backgrounds",
    )

    education_level = models.CharField(
        max_length=100,
    )

    degree_certificate = models.CharField(
        max_length=255,
    )

    field_of_study = models.CharField(
        max_length=255,
        blank=True,
    )

    specialization = models.CharField(
        max_length=255,
        blank=True,
    )

    start_year = models.PositiveIntegerField()

    end_year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    is_currently_studying = models.BooleanField(
        default=False,
    )

    result_type = models.CharField(
        max_length=100,
        blank=True,
    )

    result = models.CharField(
        max_length=100,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    certificate = models.FileField(
        upload_to="academic_certificates/",
        null=True,
        blank=True,
    )

    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
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
            "-start_year",
            "institution_name",
        ]

    def __str__(self):
        return (
            f"{self.degree_certificate} - "
            f"{self.institution_name}"
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

class PasswordResetOTP(models.Model):
    identity = models.ForeignKey(
        UserIdentity,
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )

    otp = models.CharField(
        max_length=6,
    )

    expires_at = models.DateTimeField()

    is_used = models.BooleanField(
        default=False,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Password Reset OTP - "
            f"{self.identity.user_id}"
        )        