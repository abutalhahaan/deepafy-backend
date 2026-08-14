from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.category_list,
        name="category-list",
    ),
    path(
        "create/",
        views.category_create,
        name="category-create",
    ),
    path(
        "<int:category_id>/",
        views.category_detail,
        name="category-detail",
    ),
    path(
        "<int:category_id>/update/",
        views.category_update,
        name="category-update",
    ),
    path(
        "<int:category_id>/delete/",
        views.category_delete,
        name="category-delete",
    ),
    path(
        "<int:category_id>/restore/",
        views.category_restore,
        name="category-restore",
    ),
    path(
        "<int:category_id>/relationships/",
        views.category_relationships,
        name="category-relationships",
    ),
    path(
        "relationships/create/",
        views.category_relationship_create,
        name="category-relationship-create",
    ),
    path(
        "relationships/delete/",
        views.category_relationship_delete,
        name="category-relationship-delete",
    ),
]