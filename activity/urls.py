from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.activity_feed,
        name="activity-feed",
    ),
    path(
        "create/",
        views.activity_create,
        name="activity-create",
    ),
    path(
        "<int:activity_id>/comments/",
        views.activity_comments,
        name="activity-comments",
    ),
    path(
        "<int:activity_id>/like/",
        views.activity_like,
        name="activity-like",
    ),
]
