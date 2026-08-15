from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/categories/",
        include("category_engine.urls"),
    ),
    path(
        "api/organizations/",
        include("organization.urls"),
    ),
]