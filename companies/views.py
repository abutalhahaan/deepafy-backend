import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Company


def _company_data(company):
    return {
        "id": company.id,
        "company_id": str(company.company_id),
        "name": company.name,
        "company_type": company.company_type,
        "country": company.country,
        "business_email": company.business_email,
        "business_mobile_number": (
            company.business_mobile_number
        ),
        "registered_address": company.registered_address,
        "primary_contact_person": (
            company.primary_contact_person
        ),
        "created_at": company.created_at.isoformat(),
        "updated_at": company.updated_at.isoformat(),
    }


@require_http_methods(["GET"])
def company_list(request):
    companies = Company.objects.all().order_by("name")

    return JsonResponse(
        {
            "count": companies.count(),
            "results": [
                _company_data(company)
                for company in companies
            ],
        }
    )


@require_http_methods(["GET"])
def company_detail(request, company_id):
    try:
        company = Company.objects.get(
            id=company_id
        )
    except Company.DoesNotExist:
        return JsonResponse(
            {"detail": "Company not found."},
            status=404,
        )

    return JsonResponse(
        _company_data(company)
    )


@csrf_exempt
@require_http_methods(["POST"])
def company_create(request):
    try:
        data = json.loads(request.body or "{}")

        company = Company.objects.create(
            name=data.get("name", ""),
            company_type=data.get(
                "company_type",
                "",
            ),
            country=data.get(
                "country",
                "",
            ),
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
            _company_data(company),
            status=201,
        )

    except (
        ValidationError,
        ValueError,
        TypeError,
    ) as exc:
        return JsonResponse(
            {"detail": str(exc)},
            status=400,
        )


@csrf_exempt
@require_http_methods(["PATCH"])
def company_update(request, company_id):
    try:
        company = Company.objects.get(
            id=company_id
        )
    except Company.DoesNotExist:
        return JsonResponse(
            {"detail": "Company not found."},
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")

        allowed_fields = {
            "name",
            "company_type",
            "country",
            "business_email",
            "business_mobile_number",
            "registered_address",
            "primary_contact_person",
        }

        for field in allowed_fields:
            if field in data:
                setattr(
                    company,
                    field,
                    data[field],
                )

        company.save()

        return JsonResponse(
            _company_data(company)
        )

    except (
        ValidationError,
        ValueError,
        TypeError,
    ) as exc:
        return JsonResponse(
            {"detail": str(exc)},
            status=400,
        )


@csrf_exempt
@require_http_methods(["DELETE"])
def company_delete(request, company_id):
    try:
        company = Company.objects.get(
            id=company_id
        )
    except Company.DoesNotExist:
        return JsonResponse(
            {"detail": "Company not found."},
            status=404,
        )

    company.delete()

    return JsonResponse(
        {
            "detail": (
                "Company deleted successfully."
            )
        }
    )