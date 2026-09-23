from django.urls import path

from .views import institution_type_list


urlpatterns = [
    path(
        "types/",
        institution_type_list,
        name="institution-type-list",
    ),
]
