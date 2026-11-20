from django.contrib import admin

from .models import (
    SecurityProfile,
    SecurityPreference,
    SecurityPolicy,
    SecurityMethod,
)


@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "key",
        "two_factor_required",
        "is_active",
        "updated_at",
    )
    list_filter = (
        "is_active",
        "two_factor_required",
    )
    search_fields = ("name", "key")
    readonly_fields = (
        "policy_id",
        "created_at",
        "updated_at",
        "updated_by",
    )

    fieldsets = (
        ("Policy Information", {
            "fields": (
                "policy_id",
                "key",
                "name",
                "description",
                "is_active",
            ),
        }),
        ("Two-Factor Authentication", {
            "fields": (
                "allowed_2fa_methods",
                "two_factor_required",
            ),
        }),
        ("OTP Security", {
            "fields": (
                "otp_expiry_seconds",
                "otp_max_attempts",
                "login_max_attempts",
                "login_lockout_minutes",
            ),
        }),
        ("Device and Step-up Security", {
            "fields": (
                "trusted_device_expiry_days",
                "step_up_validity_seconds",
                "action_verification_levels",
            ),
        }),
        ("Audit Information", {
            "fields": (
                "updated_by",
                "created_at",
                "updated_at",
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SecurityProfile)
class SecurityProfileAdmin(admin.ModelAdmin):
    list_display = (
        "identity",
        "two_factor_enabled",
        "last_verified_at",
        "created_at",
    )
    list_filter = ("two_factor_enabled",)
    search_fields = (
        "identity__email",
        "identity__username",
    )
    readonly_fields = (
        "identity",
        "two_factor_enabled",
        "password_changed_at",
        "last_verified_at",
        "last_security_activity_at",
        "created_at",
        "updated_at",
    )


@admin.register(SecurityMethod)
class SecurityMethodAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "method",
        "status",
        "is_primary",
        "verified_at",
    )
    list_filter = ("method", "status", "is_primary")
    search_fields = ("profile__identity__email",)
    readonly_fields = (
        "method_id",
        "profile",
        "method",
        "status",
        "is_primary",
        "verified_at",
        "last_used_at",
        "created_at",
        "updated_at",
    )


@admin.register(SecurityPreference)
class SecurityPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "remember_device_enabled",
        "login_alerts_enabled",
        "security_alerts_enabled",
    )
    search_fields = ("profile__identity__email",)
    readonly_fields = (
        "profile",
        "remember_device_enabled",
        "login_alerts_enabled",
        "security_alerts_enabled",
        "session_alerts_enabled",
        "created_at",
        "updated_at",
    )
