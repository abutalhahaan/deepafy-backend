from django.urls import path

from . import views


urlpatterns = [
    path(
        "appearance/",
        views.activity_appearance,
        name="activity-appearance",
    ),
    path(
        "appearance/background-color/",
        views.activity_background_color_update,
        name="activity-background-color-update",
    ),
    path(
        "appearance/wallpaper/",
        views.activity_wallpaper_update,
        name="activity-wallpaper-update",
    ),
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
        "institution/create/",
        views.institution_activity_create,
        name="institution-activity-create",
    ),
    path(
        "institution/<str:username>/",
        views.institution_activity_feed,
        name="institution-activity-feed",
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
