import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from identity.permissions import (
    is_owner,
    permission_denied,
    require_authentication,
)

from identity.models import ProfessionalAccount

from .models import (
    JobCategory,
    JobInterest,
)


def serialize_job_category(job_category):
    return {
        "id": job_category.id,
        "name": job_category.name,
        "slug": job_category.slug,
        "description": job_category.description,
        "display_order": job_category.display_order,
        "is_active": job_category.is_active,
    }


def serialize_job_interest(job_interest):
    return {
        "id": job_interest.id,
        "professional_account_id":
        job_interest.professional_account_id,
        "job_category":
        serialize_job_category(
            job_interest.job_category
        ),
        "is_active": job_interest.is_active,
        "created_at":
        job_interest.created_at.isoformat(),
        "updated_at":
        job_interest.updated_at.isoformat(),
    }


@require_http_methods(["GET"])
def job_category_list(request):
    job_categories = (
        JobCategory.objects
        .filter(is_active=True)
        .order_by(
            "display_order",
            "name",
        )
    )

    results = [
        serialize_job_category(job_category)
        for job_category in job_categories
    ]

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def job_interest_add(
    request,
    professional_account_id,
):
    try:
        professional_account = (
            ProfessionalAccount.objects.get(
                id=professional_account_id
            )
        )
    except ProfessionalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Professional account not found."
            },
            status=404,
        )

    if not is_owner(
        request.authenticated_identity,
        professional_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to add "
            "job interest to this professional account."
        )

    try:
        data = json.loads(
            request.body or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail": "Invalid JSON."
            },
            status=400,
        )

    job_category_id = data.get(
        "job_category_id"
    )

    if not job_category_id:
        return JsonResponse(
            {
                "detail":
                "job_category_id is required."
            },
            status=400,
        )

    try:
        job_category = JobCategory.objects.get(
            id=job_category_id,
            is_active=True,
        )
    except JobCategory.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Active job category not found."
            },
            status=404,
        )

    job_interest, created = (
        JobInterest.objects.get_or_create(
            professional_account=professional_account,
            job_category=job_category,
            defaults={
                "is_active": True,
            },
        )
    )

    if not created:
        return JsonResponse(
            {
                "detail":
                "This job category is already added "
                "to the professional account."
            },
            status=400,
        )

    return JsonResponse(
        serialize_job_interest(
            job_interest
        ),
        status=201,
    )


@require_http_methods(["GET"])
def job_interest_list(
    request,
    professional_account_id,
):
    try:
        professional_account = (
            ProfessionalAccount.objects.get(
                id=professional_account_id
            )
        )
    except ProfessionalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Professional account not found."
            },
            status=404,
        )

    job_interests = (
        JobInterest.objects
        .filter(
            professional_account=professional_account,
            is_active=True,
            job_category__is_active=True,
        )
        .select_related(
            "job_category"
        )
        .order_by(
            "job_category__display_order",
            "job_category__name",
        )
    )

    results = [
        serialize_job_interest(
            job_interest
        )
        for job_interest in job_interests
    ]

    return JsonResponse(
        {
            "professional_account_id":
            professional_account.id,
            "count": len(results),
            "results": results,
        }
    )


@csrf_exempt
@require_http_methods(["DELETE"])
@require_authentication
def job_interest_remove(
    request,
    professional_account_id,
    job_category_id,
):
    try:
        professional_account = (
            ProfessionalAccount.objects.get(
                id=professional_account_id
            )
        )
    except ProfessionalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Professional account not found."
            },
            status=404,
        )

    if not is_owner(
        request.authenticated_identity,
        professional_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to remove "
            "job interest from this professional account."
        )

    try:
        job_interest = (
            JobInterest.objects.get(
                professional_account=professional_account,
                job_category_id=job_category_id,
            )
        )
    except JobInterest.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Job interest not found."
            },
            status=404,
        )

    job_interest.delete()

    return JsonResponse(
        {
            "detail":
            "Job interest removed successfully."
        },
        status=200,
    )