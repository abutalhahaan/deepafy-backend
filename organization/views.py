import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Organization


def _organization_data(organization):
    return {
        "id": organization.id,
        "organization_id": str(organization.organization_id),
        "name": organization.name,
        "organization_type": organization.organization_type,
        "country": organization.country,
        "business_email": organization.business_email,
        "business_mobile_number": organization.business_mobile_number,
        "registered_address": organization.registered_address,
        "primary_contact_person": organization.primary_contact_person,
        "created_at": organization.created_at.isoformat(),
        "updated_at": organization.updated_at.isoformat(),
    }


@require_http_methods(["GET"])
def organization_list(request):
    organizations = Organization.objects.all().order_by("name")

    return JsonResponse(
        {
            "count": organizations.count(),
            "results": [
                _organization_data(organization)
                for organization in organizations
            ],
        }
    )


@require_http_methods(["GET"])
def organization_detail(request, organization_id):
    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return JsonResponse(
            {"detail": "Organization not found."},
            status=404,
        )

    return JsonResponse(_organization_data(organization))


@csrf_exempt
@require_http_methods(["POST"])
def organization_create(request):
    try:
        data = json.loads(request.body or "{}")

        organization = Organization.objects.create(
            name=data.get("name", ""),
            organization_type=data.get(
                "organization_type",
                "",
            ),
            country=data.get("country", ""),
            business_email=data.get(
                "business_email",
                "",
            ),
            business_mobile_number=data.get(
                "business_mobile_number",
                "",
            ),
            registered_address=data.get(
                "registered_address",
                "",
            ),
            primary_contact_person=data.get(
                "primary_contact_person",
                "",
            ),
        )

        return JsonResponse(
            _organization_data(organization),
            status=201,
        )

    except (ValidationError, ValueError, TypeError) as exc:
        return JsonResponse(
            {"detail": str(exc)},
            status=400,
        )


@csrf_exempt
@require_http_methods(["PATCH"])
def organization_update(request, organization_id):
    try:
        organization = Organization.objects.get(
            id=organization_id
        )
    except Organization.DoesNotExist:
        return JsonResponse(
            {"detail": "Organization not found."},
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")

        allowed_fields = {
            "name",
            "organization_type",
            "country",
            "business_email",
            "business_mobile_number",
            "registered_address",
            "primary_contact_person",
        }

        for field in allowed_fields:
            if field in data:
                setattr(
                    organization,
                    field,
                    data[field],
                )

        organization.save()

        return JsonResponse(
            _organization_data(organization)
        )

    except (ValidationError, ValueError, TypeError) as exc:
        return JsonResponse(
            {"detail": str(exc)},
            status=400,
        )


@csrf_exempt
@require_http_methods(["DELETE"])
def organization_delete(request, organization_id):
    try:
        organization = Organization.objects.get(
            id=organization_id
        )
    except Organization.DoesNotExist:
        return JsonResponse(
            {"detail": "Organization not found."},
            status=404,
        )

    organization.delete()

    return JsonResponse(
        {
            "detail": (
                "Organization deleted successfully."
            )
        }
    )