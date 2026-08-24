from django.urls import path

from . import views


urlpatterns = [
    path(
        "categories/",
        views.job_category_list,
        name="job-category-list",
    ),
    path(
        "<int:professional_account_id>/interests/add/",
        views.job_interest_add,
       name="job-interest-add",
    ),
    path(
        "<int:professional_account_id>/interests/",
        views.job_interest_list,
        name="job-interest-list",
    ),
    path(
        "<int:professional_account_id>/interests/"
        "<int:job_category_id>/remove/",
        views.job_interest_remove,
        name="job-interest-remove",
    ),
]