from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/categories/",
        include("category_engine.urls"),
    ),
    path(
        "api/organizations/",
        include("companies.urls")
    ),
    path(
        "api/identity/",
        include("identity.urls"),
    ),
    path(
        "api/homepage/",
        include("homepage.urls"),
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )