import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


class SecurityProfile(models.Model):
    identity = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_profile",
    )

    two_factor_enabled = models.BooleanField(default=False)
    two_factor_verification_attempts = models.PositiveSmallIntegerField(default=0)
    two_factor_locked_until = models.DateTimeField(null=True, blank=True)

    failed_password_attempts = models.PositiveSmallIntegerField(default=0)
    password_login_locked_until = models.DateTimeField(null=True, blank=True)
    password_login_disabled = models.BooleanField(default=False)

    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    token_version = models.PositiveIntegerField(default=0)

    recovery_email = models.EmailField(
        blank=True,
        default="",
    )

    pending_recovery_email = models.EmailField(
        blank=True,
        default="",
    )

    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_security_activity_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Security Profile: {self.identity}"


class RecoveryEmailVerification(models.Model):
    profile = models.ForeignKey(
        SecurityProfile,
        on_delete=models.CASCADE,
        related_name="recovery_email_verifications",
    )

    email = models.EmailField()

    otp_hash = models.CharField(max_length=128)

    expires_at = models.DateTimeField()

    failed_attempts = models.PositiveSmallIntegerField(
        default=0,
    )

    locked_until = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["profile", "created_at"],
                name="rec_email_prof_created_idx",
            ),
        ]

    def __str__(self):
        return f"Recovery Email Verification: {self.profile.identity}"


class SecurityPolicy(models.Model):
    class TwoFactorMethod(models.TextChoices):
        TOTP = "totp", "Authenticator App"
        EMAIL_OTP = "email_otp", "Email OTP"
        SMS_OTP = "sms_otp", "SMS OTP"
        PASSKEY = "passkey", "Passkey"

    policy_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    key = models.CharField(
        max_length=50,
        unique=True,
        default="global",
    )

    name = models.CharField(
        max_length=150,
        default="Global Security Policy",
    )

    description = models.TextField(blank=True, default="")

    allowed_2fa_methods = models.JSONField(
        default=list,
    )

    two_factor_required = models.BooleanField(
        default=False,
    )

    otp_expiry_seconds = models.PositiveIntegerField(
        default=300,
    )

    otp_max_attempts = models.PositiveSmallIntegerField(
        default=5,
    )

    trusted_device_expiry_days = models.PositiveIntegerField(
        default=30,
    )

    step_up_validity_seconds = models.PositiveIntegerField(
        default=300,
    )

    login_max_attempts = models.PositiveSmallIntegerField(
        default=5,
    )

    login_lockout_minutes = models.PositiveIntegerField(
        default=15,
    )

    action_verification_levels = models.JSONField(
        default=dict,
    )

    is_active = models.BooleanField(default=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_policies_updated",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="uniq_active_security_policy",
            ),
        ]

    def __str__(self):
        return self.name


class SecurityMethod(models.Model):
    class Method(models.TextChoices):
        TOTP = "totp", "Authenticator App"
        EMAIL_OTP = "email_otp", "Email OTP"
        SMS_OTP = "sms_otp", "SMS OTP"
        PASSKEY = "passkey", "Passkey"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Verification"
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"

    method_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    profile = models.ForeignKey(
        SecurityProfile,
        on_delete=models.CASCADE,
        related_name="methods",
    )

    method = models.CharField(
        max_length=20,
        choices=Method.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    is_primary = models.BooleanField(default=False)

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    encrypted_secret = models.TextField(blank=True, default="")
    last_totp_step = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "method"],
                name="uniq_security_method_per_profile",
            ),
            models.UniqueConstraint(
                fields=["profile"],
                condition=Q(is_primary=True),
                name="uniq_primary_security_method",
            ),
        ]

    def __str__(self):
        return f"{self.profile.identity}: {self.get_method_display()}"


class SecurityPreference(models.Model):
    profile = models.OneToOneField(
        SecurityProfile,
        on_delete=models.CASCADE,
        related_name="preferences",
    )

    remember_device_enabled = models.BooleanField(
        default=False,
    )

    trusted_location_enabled = models.BooleanField(
        default=False,
    )

    trusted_location_pending = models.BooleanField(
        default=False,
    )

    trusted_location_enabled_since = models.DateTimeField(
        null=True,
        blank=True,
    )

    login_alerts_enabled = models.BooleanField(
        default=True,
    )

    security_alerts_enabled = models.BooleanField(
        default=True,
    )

    session_alerts_enabled = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Security Preferences: {self.profile.identity}"


class TrustedLocation(models.Model):
    location_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    profile = models.ForeignKey(
        SecurityProfile,
        on_delete=models.CASCADE,
        related_name="trusted_locations",
    )

    name = models.CharField(max_length=100)

    map_url = models.URLField(blank=True, default="")

    accuracy_meters = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    radius_meters = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(latitude__gte=-90, latitude__lte=90),
                name="trusted_location_latitude_valid",
            ),
            models.CheckConstraint(
                condition=Q(longitude__gte=-180, longitude__lte=180),
                name="trusted_location_longitude_valid",
            ),
            models.CheckConstraint(
                condition=Q(radius_meters__gt=0),
                name="trusted_location_radius_positive",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.profile.identity})"


class TrustedLocationVerification(models.Model):
    profile = models.ForeignKey(
        SecurityProfile,
        on_delete=models.CASCADE,
        related_name="trusted_location_verifications",
    )

    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["profile", "expires_at"],
                name="trust_verify_prof_exp_idx",
            ),
        ]

    def __str__(self):
        return f"Location Verification: {self.profile.identity}"


class RecoveryCode(models.Model):
    profile = models.ForeignKey(
        SecurityProfile,
        on_delete=models.CASCADE,
        related_name="recovery_codes",
    )
    batch_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    code_hash = models.CharField(max_length=128)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["profile", "used_at"],
                name="recovery_profile_used_idx",
            ),
        ]

    def __str__(self):
        return f"Recovery Code: {self.profile.identity}"


class TwoFactorLoginChallenge(models.Model):
    profile = models.ForeignKey(
        SecurityProfile,
        on_delete=models.CASCADE,
        related_name="two_factor_challenges",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["profile", "expires_at"],
                name="twofactor_prof_exp_idx",
            ),
        ]

    def __str__(self):
        return f"2FA Login Challenge: {self.profile.identity}"
