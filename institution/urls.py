from django.urls import path

from .views import (
    institution_type_list,
    institution_profile_by_username,
    institution_appearance_update, institution_profile_update,
)


urlpatterns = [
    path(
        "profile/username/<str:username>/",
        institution_profile_by_username,
        name="institution-profile-by-username",
    ),
    path(
        "profile/appearance/",
        institution_appearance_update,
        name="institution-appearance-update",
    ),
    path(
        "profile/update/",
        institution_profile_update,
        name="institution-profile-update",
    ),
    path(
        "types/",
        institution_type_list,
        name="institution-type-list",
    ),
]
