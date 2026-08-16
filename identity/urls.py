from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.identity_list,
        name="identity-list",
    ),
    path(
        "create/",
        views.identity_create,
        name="identity-create",
    ),
    path(
        "<int:identity_id>/",
        views.identity_detail,
        name="identity-detail",
    ),
    path(
        "<int:identity_id>/update/",
        views.identity_update,
        name="identity-update",
    ),
    path(
        "<int:identity_id>/delete/",
        views.identity_delete,
        name="identity-delete",
    ),
    path(
        "<int:identity_id>/account-types/",
        views.account_type_list,
        name="account-type-list",
    ),
    path(
        "account-types/create/",
        views.account_type_create,
        name="account-type-create",
    ),
    path(
        "personal-accounts/create/",
        views.personal_account_create,
        name="personal-account-create",
    ),
    path(
        "<int:identity_id>/personal-account/",
        views.personal_account_detail,
        name="personal-account-detail",
    ),
    path(
        "<int:identity_id>/personal-account/update/",
        views.personal_account_update,
        name="personal-account-update",
    ),

    # Job Experience
    path(
        "job-experiences/create/",
        views.job_experience_create,
        name="job-experience-create",
    ),
    path(
        "<int:identity_id>/job-experiences/",
        views.job_experience_list,
        name="job-experience-list",
    ),
    path(
        "job-experiences/<int:experience_id>/",
        views.job_experience_detail,
        name="job-experience-detail",
    ),
    path(
        "job-experiences/<int:experience_id>/update/",
        views.job_experience_update,
        name="job-experience-update",
    ),
    path(
        "job-experiences/<int:experience_id>/delete/",
        views.job_experience_delete,
        name="job-experience-delete",
    ),
]