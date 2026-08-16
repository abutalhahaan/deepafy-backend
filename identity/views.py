import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import (
    AcademicBackground,
    AccountType,
    Hobby,
    JobExperience,
    PersonalAccount,
    PersonalHobby,
    PersonalInterestedCategory,
    ProfessionalAccount,
    UserIdentity,
)


def serialize_identity(identity):
    return {
        "id": identity.id,
        "user_id": str(identity.user_id),
        "email": identity.email,
        "mobile_number": identity.mobile_number,
        "status": identity.status,
        "is_active": identity.is_active,
        "created_at": identity.created_at.isoformat(),
        "updated_at": identity.updated_at.isoformat(),
    }


def serialize_account_type(account_type):
    return {
        "id": account_type.id,
        "identity_id": account_type.identity_id,
        "account_type": account_type.account_type,
        "is_primary": account_type.is_primary,
        "is_active": account_type.is_active,
        "created_at": account_type.created_at.isoformat(),
        "updated_at": account_type.updated_at.isoformat(),
    }


def serialize_personal_account(personal_account):
    return {
        "id": personal_account.id,
        "identity_id": personal_account.identity_id,
        "is_active": personal_account.is_active,
        "created_at": personal_account.created_at.isoformat(),
        "updated_at": personal_account.updated_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["POST"])
def identity_create(request):
    try:
        data = json.loads(request.body or "{}")

        email = data.get("email", "").strip()

        if not email:
            return JsonResponse(
                {"detail": "Email is required."},
                status=400,
            )

        if UserIdentity.objects.filter(email=email).exists():
            return JsonResponse(
                {"detail": "An identity with this email already exists."},
                status=400,
            )

        identity = UserIdentity.objects.create(
            email=email,
            mobile_number=data.get("mobile_number", ""),
            status=data.get(
                "status",
                UserIdentity.Status.DRAFT,
            ),
            is_active=data.get("is_active", True),
        )

        return JsonResponse(
            serialize_identity(identity),
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@require_http_methods(["GET"])
def identity_list(request):
    identities = UserIdentity.objects.all()

    results = [
        serialize_identity(identity)
        for identity in identities
    ]

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        }
    )


@require_http_methods(["GET"])
def identity_detail(request, identity_id):
    try:
        identity = UserIdentity.objects.get(id=identity_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Identity not found."},
            status=404,
        )

    return JsonResponse(
        serialize_identity(identity)
    )


@csrf_exempt
@require_http_methods(["PATCH"])
def identity_update(request, identity_id):
    try:
        identity = UserIdentity.objects.get(id=identity_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Identity not found."},
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")

        if "email" in data:
            email = data.get("email", "").strip()

            if not email:
                return JsonResponse(
                    {"detail": "Email cannot be empty."},
                    status=400,
                )

            if UserIdentity.objects.filter(
                email=email
            ).exclude(
                id=identity.id
            ).exists():
                return JsonResponse(
                    {"detail": "An identity with this email already exists."},
                    status=400,
                )

            identity.email = email

        if "mobile_number" in data:
            identity.mobile_number = data.get(
                "mobile_number",
                "",
            )

        if "status" in data:
            identity.status = data.get("status")

        if "is_active" in data:
            identity.is_active = data.get("is_active")

        identity.save()

        return JsonResponse(
            serialize_identity(identity)
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@csrf_exempt
@require_http_methods(["DELETE"])
def identity_delete(request, identity_id):
    try:
        identity = UserIdentity.objects.get(id=identity_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Identity not found."},
            status=404,
        )

    identity.delete()

    return JsonResponse(
        {
            "detail": "Identity deleted successfully."
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def account_type_create(request):
    try:
        data = json.loads(request.body or "{}")

        identity_id = data.get("identity_id")
        account_type = data.get("account_type")

        if not identity_id:
            return JsonResponse(
                {"detail": "identity_id is required."},
                status=400,
            )

        if not account_type:
            return JsonResponse(
                {"detail": "account_type is required."},
                status=400,
            )

        try:
            identity = UserIdentity.objects.get(
                id=identity_id
            )
        except UserIdentity.DoesNotExist:
            return JsonResponse(
                {"detail": "Identity not found."},
                status=404,
            )

        if not any(
            value == account_type
            for value, _ in AccountType.Type.choices
        ):
            return JsonResponse(
                {"detail": "Invalid account_type."},
                status=400,
            )

        if AccountType.objects.filter(
            identity=identity,
            account_type=account_type,
        ).exists():
            return JsonResponse(
                {"detail": "This account type already exists."},
                status=400,
            )

        account = AccountType.objects.create(
            identity=identity,
            account_type=account_type,
            is_primary=data.get("is_primary", False),
            is_active=data.get("is_active", True),
        )

        return JsonResponse(
            serialize_account_type(account),
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@require_http_methods(["GET"])
def account_type_list(request, identity_id):
    try:
        identity = UserIdentity.objects.get(id=identity_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Identity not found."},
            status=404,
        )

    account_types = identity.account_types.all()

    results = [
        serialize_account_type(account)
        for account in account_types
    ]

    return JsonResponse(
        {
            "identity_id": identity.id,
            "count": len(results),
            "results": results,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def personal_account_create(request):
    try:
        data = json.loads(request.body or "{}")

        identity_id = data.get("identity_id")

        if not identity_id:
            return JsonResponse(
                {"detail": "identity_id is required."},
                status=400,
            )

        try:
            identity = UserIdentity.objects.get(
                id=identity_id
            )
        except UserIdentity.DoesNotExist:
            return JsonResponse(
                {"detail": "Identity not found."},
                status=404,
            )

        if PersonalAccount.objects.filter(
            identity=identity
        ).exists():
            return JsonResponse(
                {"detail": "Personal account already exists."},
                status=400,
            )

        personal_account = PersonalAccount.objects.create(
            identity=identity,
            is_active=data.get("is_active", True),
        )

        return JsonResponse(
            serialize_personal_account(
                personal_account
            ),
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@require_http_methods(["GET"])
def personal_account_detail(request, identity_id):
    try:
        personal_account = PersonalAccount.objects.get(
            identity_id=identity_id
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Personal account not found."},
            status=404,
        )

    return JsonResponse(
        serialize_personal_account(
            personal_account
        )
    )

@csrf_exempt
@require_http_methods(["PATCH"])
def personal_account_update(request, identity_id):
    try:
        identity = UserIdentity.objects.get(id=identity_id)
        personal_account = identity.personal_account
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Identity not found."},
            status=404,
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Personal account not found."},
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    fields = [
        "display_name",
        "username",
        "permanent_city",
        "permanent_area",
        "permanent_full_address",
        "present_city",
        "present_area",
        "present_full_address",
        "is_active",
    ]

    for field in fields:
        if field in data:
            setattr(personal_account, field, data[field])

    if "username" in data:
        username = data.get("username")

        if username:
            username_exists = (
                PersonalAccount.objects
                .filter(username=username)
                .exclude(id=personal_account.id)
                .exists()
            )

            if username_exists:
                return JsonResponse(
                    {"detail": "This username already exists."},
                    status=400,
                )

    if "permanent_country_id" in data:
        permanent_country_id = data.get("permanent_country_id")

        if permanent_country_id:
            personal_account.permanent_country_id = (
                permanent_country_id
            )
        else:
            personal_account.permanent_country = None

    if "present_country_id" in data:
        present_country_id = data.get("present_country_id")

        if present_country_id:
            personal_account.present_country_id = (
                present_country_id
            )
        else:
            personal_account.present_country = None

    personal_account.save()

    return JsonResponse(
        {
            "id": personal_account.id,
            "identity_id": personal_account.identity_id,
            "display_name": personal_account.display_name,
            "username": personal_account.username,
            "permanent_country_id": (
                personal_account.permanent_country_id
            ),
            "permanent_city": personal_account.permanent_city,
            "permanent_area": personal_account.permanent_area,
            "permanent_full_address": (
                personal_account.permanent_full_address
            ),
            "present_country_id": (
                personal_account.present_country_id
            ),
            "present_city": personal_account.present_city,
            "present_area": personal_account.present_area,
            "present_full_address": (
                personal_account.present_full_address
            ),
            "is_active": personal_account.is_active,
            "created_at": personal_account.created_at.isoformat(),
            "updated_at": personal_account.updated_at.isoformat(),
        }
    )



def serialize_professional_account(professional_account):
    return {
        "id": professional_account.id,
        "identity_id": professional_account.identity_id,
        "professional_title": professional_account.professional_title,
        "profession": professional_account.profession,
        "industry": professional_account.industry,
        "professional_summary": professional_account.professional_summary,
        "focus_job_area": professional_account.focus_job_area,
        "future_goal": professional_account.future_goal,
        "background_color": professional_account.background_color,
        "tab_colors": professional_account.tab_colors,
        "is_active": professional_account.is_active,
        "created_at": professional_account.created_at.isoformat(),
        "updated_at": professional_account.updated_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["POST"])
def professional_account_create(request):
    try:
        data = json.loads(request.body or "{}")

        identity_id = data.get("identity_id")

        if not identity_id:
            return JsonResponse(
                {"detail": "identity_id is required."},
                status=400,
            )

        try:
            identity = UserIdentity.objects.get(
                id=identity_id
            )
        except UserIdentity.DoesNotExist:
            return JsonResponse(
                {"detail": "Identity not found."},
                status=404,
            )

        if ProfessionalAccount.objects.filter(
            identity=identity
        ).exists():
            return JsonResponse(
                {"detail": "Professional account already exists."},
                status=400,
            )

        professional_account = ProfessionalAccount.objects.create(
            identity=identity,
            professional_title=data.get(
                "professional_title",
                "",
            ),
            profession=data.get(
                "profession",
                "",
            ),
            industry=data.get(
                "industry",
                "",
            ),
            professional_summary=data.get(
                "professional_summary",
                "",
            ),
            focus_job_area=data.get(
                "focus_job_area",
                "",
            ),
            future_goal=data.get(
                "future_goal",
                "",
            ),
            background_color=data.get(
                "background_color",
                "#FFFFFF",
            ),
            tab_colors=data.get(
                "tab_colors",
                {},
            ),
            is_active=data.get(
                "is_active",
                True,
            ),
        )

        return JsonResponse(
            serialize_professional_account(
                professional_account
            ),
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@require_http_methods(["GET"])
def professional_account_detail(request, identity_id):
    try:
        professional_account = ProfessionalAccount.objects.get(
            identity_id=identity_id
        )
    except ProfessionalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Professional account not found."},
            status=404,
        )

    return JsonResponse(
        serialize_professional_account(
            professional_account
        )
    )


@csrf_exempt
@require_http_methods(["PATCH"])
def professional_account_update(request, identity_id):
    try:
        identity = UserIdentity.objects.get(
            id=identity_id
        )
        professional_account = identity.professional_account

    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Identity not found."},
            status=404,
        )

    except ProfessionalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Professional account not found."},
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    fields = [
        "professional_title",
        "profession",
        "industry",
        "professional_summary",
        "focus_job_area",
        "future_goal",
        "background_color",
        "tab_colors",
        "is_active",
    ]

    for field in fields:
        if field in data:
            setattr(
                professional_account,
                field,
                data[field],
            )

    professional_account.save()

    return JsonResponse(
        serialize_professional_account(
            professional_account
        )
    )

def serialize_academic_background(academic):
    return {
        "id": academic.id,
        "professional_account_id": academic.professional_account_id,
        "qualification": academic.qualification,
        "institution": academic.institution,
        "field_of_study": academic.field_of_study,
        "country_id": academic.country_id,
        "city": academic.city,
        "start_date": (
    experience.start_date.isoformat()
    if hasattr(experience.start_date, "isoformat")
    else experience.start_date
    if experience.start_date
    else None
),
"end_date": (
    experience.end_date.isoformat()
    if hasattr(experience.end_date, "isoformat")
    else experience.end_date
    if experience.end_date
    else None
),
        "is_current": academic.is_current,
        "result": academic.result,
        "description": academic.description,
        "display_order": academic.display_order,
        "is_active": academic.is_active,
        "created_at": academic.created_at.isoformat(),
        "updated_at": academic.updated_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["POST"])
def academic_background_create(request):
    try:
        data = json.loads(request.body or "{}")

        professional_account_id = data.get(
            "professional_account_id"
        )

        if not professional_account_id:
            return JsonResponse(
                {"detail": "professional_account_id is required."},
                status=400,
            )

        try:
            professional_account = ProfessionalAccount.objects.get(
                id=professional_account_id
            )
        except ProfessionalAccount.DoesNotExist:
            return JsonResponse(
                {"detail": "Professional account not found."},
                status=404,
            )

        academic = AcademicBackground.objects.create(
            professional_account=professional_account,
            qualification=data.get("qualification", ""),
            institution=data.get("institution", ""),
            field_of_study=data.get("field_of_study", ""),
            country_id=data.get("country_id"),
            city=data.get("city", ""),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            is_current=data.get("is_current", False),
            result=data.get("result", ""),
            description=data.get("description", ""),
            display_order=data.get("display_order", 0),
            is_active=data.get("is_active", True),
        )

        return JsonResponse(
            serialize_academic_background(academic),
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@require_http_methods(["GET"])
def academic_background_list(request, identity_id):
    try:
        professional_account = ProfessionalAccount.objects.get(
            identity_id=identity_id
        )
    except ProfessionalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Professional account not found."},
            status=404,
        )

    academics = AcademicBackground.objects.filter(
        professional_account=professional_account
    )

    results = [
        serialize_academic_background(academic)
        for academic in academics
    ]

    return JsonResponse(
        {
            "professional_account_id": professional_account.id,
            "count": len(results),
            "results": results,
        }
    )


@require_http_methods(["GET"])
def academic_background_detail(request, academic_id):
    try:
        academic = AcademicBackground.objects.get(
            id=academic_id
        )
    except AcademicBackground.DoesNotExist:
        return JsonResponse(
            {"detail": "Academic background not found."},
            status=404,
        )

    return JsonResponse(
        serialize_academic_background(academic)
    )


@csrf_exempt
@require_http_methods(["PATCH"])
def academic_background_update(request, academic_id):
    try:
        academic = AcademicBackground.objects.get(
            id=academic_id
        )
    except AcademicBackground.DoesNotExist:
        return JsonResponse(
            {"detail": "Academic background not found."},
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    fields = [
        "qualification",
        "institution",
        "field_of_study",
        "city",
        "start_date",
        "end_date",
        "is_current",
        "result",
        "description",
        "display_order",
        "is_active",
    ]

    for field in fields:
        if field in data:
            setattr(
                academic,
                field,
                data[field],
            )

    if "country_id" in data:
        country_id = data.get("country_id")

        if country_id:
            academic.country_id = country_id
        else:
            academic.country = None

    academic.save()

    return JsonResponse(
        serialize_academic_background(academic)
    )


@csrf_exempt
@require_http_methods(["DELETE"])
def academic_background_delete(request, academic_id):
    try:
        academic = AcademicBackground.objects.get(
            id=academic_id
        )
    except AcademicBackground.DoesNotExist:
        return JsonResponse(
            {"detail": "Academic background not found."},
            status=404,
        )

    academic.delete()

    return JsonResponse(
        {
            "detail": "Academic background deleted successfully."
        }
    )

def serialize_job_experience(experience):
    return {
        "id": experience.id,
        "professional_account_id": experience.professional_account_id,
        "company": experience.company,
        "job_title": experience.job_title,
        "employment_type": experience.employment_type,
        "location": experience.location,
        "start_date": (
    experience.start_date.isoformat()
    if hasattr(experience.start_date, "isoformat")
    else experience.start_date
    if experience.start_date
    else None
),
"end_date": (
    experience.end_date.isoformat()
    if hasattr(experience.end_date, "isoformat")
    else experience.end_date
    if experience.end_date
    else None
),
        "is_current": experience.is_current,
        "description": experience.description,
        "display_order": experience.display_order,
        "is_active": experience.is_active,
        "created_at": experience.created_at.isoformat(),
        "updated_at": experience.updated_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["POST"])
def job_experience_create(request):
    try:
        data = json.loads(request.body or "{}")

        professional_account_id = data.get(
            "professional_account_id"
        )

        if not professional_account_id:
            return JsonResponse(
                {
                    "detail":
                    "professional_account_id is required."
                },
                status=400,
            )

        try:
            professional_account = ProfessionalAccount.objects.get(
                id=professional_account_id
            )
        except ProfessionalAccount.DoesNotExist:
            return JsonResponse(
                {
                    "detail":
                    "Professional account not found."
                },
                status=404,
            )

        experience = JobExperience.objects.create(
            professional_account=professional_account,
            company=data.get("company", ""),
            job_title=data.get("job_title", ""),
            employment_type=data.get(
                "employment_type",
                "",
            ),
            location=data.get(
                "location",
                "",
            ),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            is_current=data.get(
                "is_current",
                False,
            ),
            description=data.get(
                "description",
                "",
            ),
            display_order=data.get(
                "display_order",
                0,
            ),
            is_active=data.get(
                "is_active",
                True,
            ),
        )

        return JsonResponse(
            serialize_job_experience(experience),
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@require_http_methods(["GET"])
def job_experience_list(request, identity_id):
    try:
        professional_account = ProfessionalAccount.objects.get(
            identity_id=identity_id
        )
    except ProfessionalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Professional account not found."
            },
            status=404,
        )

    experiences = JobExperience.objects.filter(
        professional_account=professional_account
    )

    results = [
        serialize_job_experience(experience)
        for experience in experiences
    ]

    return JsonResponse(
        {
            "professional_account_id":
            professional_account.id,
            "count": len(results),
            "results": results,
        }
    )


@require_http_methods(["GET"])
def job_experience_detail(request, experience_id):
    try:
        experience = JobExperience.objects.get(
            id=experience_id
        )
    except JobExperience.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Job experience not found."
            },
            status=404,
        )

    return JsonResponse(
        serialize_job_experience(experience)
    )


@csrf_exempt
@require_http_methods(["PATCH"])
def job_experience_update(request, experience_id):
    try:
        experience = JobExperience.objects.get(
            id=experience_id
        )
    except JobExperience.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Job experience not found."
            },
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    fields = [
        "company",
        "job_title",
        "employment_type",
        "location",
        "start_date",
        "end_date",
        "is_current",
        "description",
        "display_order",
        "is_active",
    ]

    for field in fields:
        if field in data:
            setattr(
                experience,
                field,
                data[field],
            )

    experience.save()

    return JsonResponse(
        serialize_job_experience(experience)
    )


@csrf_exempt
@require_http_methods(["DELETE"])
def job_experience_delete(request, experience_id):
    try:
        experience = JobExperience.objects.get(
            id=experience_id
        )
    except JobExperience.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Job experience not found."
            },
            status=404,
        )

    experience.delete()

    return JsonResponse(
        {
            "detail":
            "Job experience deleted successfully."
        }
    )