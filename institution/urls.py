from django.urls import path

from .views import (
    institution_type_list,
    institution_authority_list,
    institution_profile_by_username,
    institution_appearance_update,
    institution_profile_update,
    institution_academic_data,
    institution_academic_levels,
    institution_academic_level_delete,
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
    path(
        "authorities/",
        institution_authority_list,
        name="institution-authority-list",
    ),
    path(
        "academic/levels/",
        institution_academic_levels,
        name="institution-academic-levels",
    ),
    path(
        "academic/levels/<int:level_id>/",
        institution_academic_level_delete,
        name="institution-academic-level-delete",
    ),
    path(
        "academic/",
        institution_academic_data,
        name="institution-academic-data",
    ),
]
