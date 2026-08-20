from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.company_list,
        name="company-list",
    ),

    path(
        "<int:company_id>/",
        views.company_detail,
        name="company-detail",
    ),

    path(
        "create/",
        views.company_create,
        name="company-create",
    ),

    path(
        "<int:company_id>/update/",
        views.company_update,
        name="company-update",
    ),

    path(
        "<int:company_id>/delete/",
        views.company_delete,
        name="company-delete",
    ),
]