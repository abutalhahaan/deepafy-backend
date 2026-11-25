from django.urls import path

from .two_factor_views import (
    verify_two_factor_login,
    two_factor_status,
    setup_totp,
    verify_totp_setup,
    regenerate_recovery_codes,
    disable_two_factor,
)

from .views import (
    verify_login_location,
    trusted_location_list_create,
    trusted_location_detail,
    trusted_location_settings,
    cancel_trusted_location_pending,
)

urlpatterns = [
    path(
        "two-factor/status/",
        two_factor_status,
        name="two-factor-status",
    ),
    path(
        "two-factor/setup/",
        setup_totp,
        name="two-factor-setup",
    ),
    path(
        "two-factor/verify-setup/",
        verify_totp_setup,
        name="two-factor-verify-setup",
    ),
    path(
        "two-factor/regenerate-recovery-codes/",
        regenerate_recovery_codes,
        name="two-factor-regenerate-recovery-codes",
    ),
    path(
        "two-factor/disable/",
        disable_two_factor,
        name="two-factor-disable",
    ),

    path(
        "trusted-locations/",
        trusted_location_list_create,
        name="trusted-location-list-create",
    ),
    path(
        "trusted-locations/<int:location_id>/",
        trusted_location_detail,
        name="trusted-location-detail",
    ),
    path(
        "trusted-location-settings/",
        trusted_location_settings,
        name="trusted-location-settings",
    ),
    path(
        "trusted-location-pending-cancel/",
        cancel_trusted_location_pending,
        name="trusted-location-pending-cancel",
    ),
    path(
        "verify-login-location/",
        verify_login_location,
        name="verify-login-location",
    ),
    path(
        "verify-two-factor-login/",
        verify_two_factor_login,
        name="verify-two-factor-login",
    ),
]
