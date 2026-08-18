from django.urls import path

from .views import HomepageAPIView


urlpatterns = [
    path("", HomepageAPIView.as_view(), name="homepage"),
]