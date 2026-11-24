from django.urls import path

from .views import (
    verify_login_location,
    trusted_location_list_create,
    trusted_location_detail,
    trusted_location_settings,
    cancel_trusted_location_pending,
)

urlpatterns = [
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
]
