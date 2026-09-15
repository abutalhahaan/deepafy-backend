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
]
