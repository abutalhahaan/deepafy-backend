from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.organization_list,
        name="organization-list",
    ),
    path(
        "<int:organization_id>/",
        views.organization_detail,
        name="organization-detail",
    ),
    path(
        "create/",
        views.organization_create,
        name="organization-create",
    ),
    path(
        "<int:organization_id>/update/",
        views.organization_update,
        name="organization-update",
    ),
    path(
        "<int:organization_id>/delete/",
        views.organization_delete,
        name="organization-delete",
    ),
]