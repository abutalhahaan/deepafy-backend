import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class SecurityProfile(models.Model):
    identity = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_profile",
    )

    two_factor_enabled = models.BooleanField(default=False)

    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
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
