from django.urls import path

from .views import (
    GetStartedPageSettingsAPIView,
    HomepageAPIView,
)


urlpatterns = [
    path("", HomepageAPIView.as_view(), name="homepage"),
    path(
        "get-started/",
        GetStartedPageSettingsAPIView.as_view(),
        name="get-started-page-settings",
    ),
]
