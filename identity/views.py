import json
import secrets

from datetime import timedelta
from core.services.image_processor import process_image

from django.http.multipartparser import (
    MultiPartParser,
    MultiPartParserError,
)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import (
    AcademicBackground,
    AccountType,
    Hobby,
    JobExperience,
    ProfessionalSkill,
    Skill,
    PersonalAccount,
    PersonalHobby,
    PersonalInterestedCategory,
    PasswordResetOTP,
    ProfessionalAccount,
    UserIdentity,
)

from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    VerifyOTPSerializer,
)

def serialize_identity(identity):
    return {
        "id": identity.id,
        "user_id": str(identity.user_id),
        "first_name": identity.first_name,
        "last_name": identity.last_name,
        "username": identity.username,
        "email": identity.email,
        "mobile_number": identity.mobile_number,
        "is_email_verified": identity.is_email_verified,
        "is_mobile_verified": identity.is_mobile_verified,
        "status": identity.status,
        "is_active": identity.is_active,
        "created_at": identity.created_at.isoformat(),
        "updated_at": identity.updated_at.isoformat(),
    }


def serialize_hobby(hobby):
    return {
        "id": hobby.id,
        "name": hobby.name,
        "slug": hobby.slug,
        "description": hobby.description,
        "is_active": hobby.is_active,
        "display_order": hobby.display_order,
        "created_at": hobby.created_at.isoformat(),
        "updated_at": hobby.updated_at.isoformat(),
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

        "display_name": personal_account.display_name,
        "username": personal_account.username,
        "bio": personal_account.bio,

        "mother_tongue_id":
        personal_account.mother_tongue_id,

        "mother_tongue_name": (
            personal_account.mother_tongue.name
            if personal_account.mother_tongue
            else None
        ),

        "permanent_country_id":
        personal_account.permanent_country_id,

        "permanent_country_name": (
            personal_account.permanent_country.name
            if personal_account.permanent_country
            else None
        ),

        "permanent_city":
        personal_account.permanent_city,

        "permanent_area":
        personal_account.permanent_area,

        "permanent_full_address":
        personal_account.permanent_full_address,

        "present_country_id":
        personal_account.present_country_id,

        "present_country_name": (
            personal_account.present_country.name
            if personal_account.present_country
            else None
        ),

        "present_city":
        personal_account.present_city,

        "present_area":
        personal_account.present_area,

        "present_full_address":
        personal_account.present_full_address,

        "profile_photo": (
            personal_account.profile_photo.url
            if personal_account.profile_photo
            else None
        ),

        "cover_photo": (
            personal_account.cover_photo.url
            if personal_account.cover_photo
            else None
        ),

        "date_of_birth": (
            str(personal_account.date_of_birth)
            if personal_account.date_of_birth
            else None
        ),

        "gender": personal_account.gender,

        "nationality_id":
        personal_account.nationality_id,

        "nationality_name": (
            personal_account.nationality.name
            if personal_account.nationality
            else None
        ),

        "is_active": personal_account.is_active,

        "created_at":
        personal_account.created_at.isoformat(),

        "updated_at":
        personal_account.updated_at.isoformat(),
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
        "bio",
        "date_of_birth",
        "gender",
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

    if "mother_tongue_id" in data:
        mother_tongue_id = data.get("mother_tongue_id")

        if mother_tongue_id:
            personal_account.mother_tongue_id = mother_tongue_id
        else:
            personal_account.mother_tongue = None

    if "nationality_id" in data:
        nationality_id = data.get("nationality_id")

        if nationality_id:
            personal_account.nationality_id = nationality_id
        else:
            personal_account.nationality = None

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
        serialize_personal_account(personal_account)
    )

@csrf_exempt
@require_http_methods(["POST"])
def personal_account_photos_update(request, identity_id):
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

    old_profile_photo = None
    old_cover_photo = None

    try:
        if "profile_photo" in request.FILES:
            processed_profile_photo = process_image(
                request.FILES["profile_photo"],
                preset="profile",
            )

            if personal_account.profile_photo:
                old_profile_photo = (
                    personal_account.profile_photo.name
                )

            personal_account.profile_photo = (
                processed_profile_photo
            )

        if "cover_photo" in request.FILES:
            processed_cover_photo = process_image(
                request.FILES["cover_photo"],
                preset="cover",
            )

            if personal_account.cover_photo:
                old_cover_photo = (
                    personal_account.cover_photo.name
                )

            personal_account.cover_photo = (
                processed_cover_photo
            )

    except ValueError as error:
        return JsonResponse(
            {"detail": str(error)},
            status=400,
        )

    if (
        "profile_photo" not in request.FILES
        and "cover_photo" not in request.FILES
    ):
        return JsonResponse(
            {
                "detail": (
                    "Provide profile_photo or cover_photo."
                )
            },
            status=400,
        )

    personal_account.save()

    if old_profile_photo:
        personal_account.profile_photo.storage.delete(
            old_profile_photo
        )

    if old_cover_photo:
        personal_account.cover_photo.storage.delete(
            old_cover_photo
        )

    return JsonResponse(
        serialize_personal_account(personal_account)
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
        "personal_account_id": academic.personal_account_id,
        "institution_name": academic.institution_name,
        "institution_type": academic.institution_type,
        "country_id": academic.country_id,
        "country_name": (
            academic.country.name
            if academic.country
            else None
        ),
        "education_level": academic.education_level,
        "degree_certificate": academic.degree_certificate,
        "field_of_study": academic.field_of_study,
        "specialization": academic.specialization,
        "start_year": academic.start_year,
        "end_year": academic.end_year,
        "is_currently_studying": (
            academic.is_currently_studying
        ),
        "result_type": academic.result_type,
        "result": academic.result,
        "description": academic.description,
        "certificate": (
            academic.certificate.url
            if academic.certificate
            else None
        ),
        "visibility": academic.visibility,
        "display_order": academic.display_order,
        "is_active": academic.is_active,
        "created_at": academic.created_at.isoformat(),
        "updated_at": academic.updated_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["POST"])
def academic_background_create(request):
    if request.content_type.startswith(
        "multipart/form-data"
    ):
        data = request.POST
        certificate = request.FILES.get(
            "certificate"
        )
    else:
        try:
            data = json.loads(
                request.body or "{}"
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"detail": "Invalid JSON."},
                status=400,
            )

        certificate = None

    personal_account_id = data.get(
        "personal_account_id"
    )

    if not personal_account_id:
        return JsonResponse(
            {
                "detail":
                "personal_account_id is required."
            },
            status=400,
        )

    try:
        personal_account = PersonalAccount.objects.get(
            id=personal_account_id
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Personal account not found."
            },
            status=404,
        )

    required_fields = [
        "institution_name",
        "institution_type",
        "country_id",
        "education_level",
        "degree_certificate",
        "start_year",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:
        return JsonResponse(
            {
                "detail":
                "Required fields are missing.",
                "fields": missing_fields,
            },
            status=400,
        )

    academic = AcademicBackground.objects.create(
        personal_account=personal_account,
        institution_name=data.get(
            "institution_name"
        ),
        institution_type=data.get(
            "institution_type"
        ),
        country_id=data.get(
            "country_id"
        ),
        education_level=data.get(
            "education_level"
        ),
        degree_certificate=data.get(
            "degree_certificate"
        ),
        field_of_study=data.get(
            "field_of_study",
            "",
        ),
        specialization=data.get(
            "specialization",
            "",
        ),
        start_year=data.get(
            "start_year"
        ),
        end_year=(
            data.get("end_year")
            or None
        ),
        is_currently_studying=(
            str(
                data.get(
                    "is_currently_studying",
                    False,
                )
            ).lower()
            in ["true", "1", "yes"]
        ),
        result_type=data.get(
            "result_type",
            "",
        ),
        result=data.get(
            "result",
            "",
        ),
        description=data.get(
            "description",
            "",
        ),
        certificate=certificate,
        visibility=data.get(
            "visibility",
            AcademicBackground.Visibility.PUBLIC,
        ),
        display_order=data.get(
            "display_order",
            0,
        ),
        is_active=(
            str(
                data.get(
                    "is_active",
                    True,
                )
            ).lower()
            not in ["false", "0", "no"]
        ),
    )

    return JsonResponse(
        serialize_academic_background(academic),
        status=201,
    )


@require_http_methods(["GET"])
def academic_background_list(request, identity_id):
    try:
        personal_account = PersonalAccount.objects.get(
            identity_id=identity_id
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Personal account not found."
            },
            status=404,
        )

    academics = AcademicBackground.objects.filter(
        personal_account=personal_account
    )

    results = [
        serialize_academic_background(academic)
        for academic in academics
    ]

    return JsonResponse(
        {
            "personal_account_id": personal_account.id,
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
            {
                "detail":
                "Academic background not found."
            },
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
            {
                "detail":
                "Academic background not found."
            },
            status=404,
        )

    if (
        request.content_type
        and request.content_type.startswith(
            "multipart/form-data"
        )
    ):
        try:
            data, files = MultiPartParser(
                request.META,
                request,
                request.upload_handlers,
            ).parse()

            certificate = files.get(
                "certificate"
            )

            print("FILES:", files)

        except MultiPartParserError:
            return JsonResponse(
                {
                    "detail":
                    "Invalid multipart form data."
                },
                status=400,
            )

    else:
        try:
            data = json.loads(
                request.body or "{}"
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"detail": "Invalid JSON."},
                status=400,
            )

        certificate = None

    fields = [
        "institution_name",
        "institution_type",
        "education_level",
        "degree_certificate",
        "field_of_study",
        "specialization",
        "start_year",
        "end_year",
        "is_currently_studying",
        "result_type",
        "result",
        "description",
        "visibility",
        "display_order",
        "is_active",
    ]

    for field in fields:
        if field in data:
            value = data.get(field)

            if field == "end_year":
                value = value or None

            elif field == "is_currently_studying":
                value = (
                    str(value).lower()
                    in ["true", "1", "yes"]
                )

            elif field == "is_active":
                value = (
                    str(value).lower()
                    not in ["false", "0", "no"]
                )

            setattr(
                academic,
                field,
                value,
            )

    if "country_id" in data:
        academic.country_id = data.get(
            "country_id"
        )

    if certificate:
        academic.certificate = certificate

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
            {
                "detail":
                "Academic background not found."
            },
            status=404,
        )

    academic.delete()

    return JsonResponse(
        {
            "detail":
            "Academic background deleted successfully."
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

def serialize_skill(skill):
    return {
        "id": skill.id,
        "name": skill.name,
        "slug": skill.slug,
        "is_active": skill.is_active,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


def serialize_professional_skill(professional_skill):
    return {
        "id": professional_skill.id,
        "professional_account_id": (
            professional_skill.professional_account_id
        ),
        "skill_id": professional_skill.skill_id,
        "skill_name": professional_skill.skill.name,
        "skill_level": professional_skill.skill_level,
        "years_of_experience": (
            professional_skill.years_of_experience
        ),
        "is_active": professional_skill.is_active,
        "created_at": (
            professional_skill.created_at.isoformat()
        ),
        "updated_at": (
            professional_skill.updated_at.isoformat()
        ),
    }


@csrf_exempt
@require_http_methods(["POST"])
def skill_create(request):
    try:
        data = json.loads(request.body or "{}")

        name = data.get("name", "").strip()
        slug = data.get("slug", "").strip()

        if not name:
            return JsonResponse(
                {"detail": "Skill name is required."},
                status=400,
            )

        if not slug:
            return JsonResponse(
                {"detail": "Skill slug is required."},
                status=400,
            )

        if Skill.objects.filter(name=name).exists():
            return JsonResponse(
                {"detail": "This skill already exists."},
                status=400,
            )

        if Skill.objects.filter(slug=slug).exists():
            return JsonResponse(
                {"detail": "This skill slug already exists."},
                status=400,
            )

        skill = Skill.objects.create(
            name=name,
            slug=slug,
            is_active=data.get("is_active", True),
        )

        return JsonResponse(
            serialize_skill(skill),
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@require_http_methods(["GET"])
def skill_list(request):
    skills = Skill.objects.all()

    results = [
        serialize_skill(skill)
        for skill in skills
    ]

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def professional_skill_create(request):
    try:
        data = json.loads(request.body or "{}")

        professional_account_id = data.get(
            "professional_account_id"
        )
        skill_id = data.get("skill_id")

        if not professional_account_id:
            return JsonResponse(
                {
                    "detail":
                    "professional_account_id is required."
                },
                status=400,
            )

        if not skill_id:
            return JsonResponse(
                {
                    "detail":
                    "skill_id is required."
                },
                status=400,
            )

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

        try:
            skill = Skill.objects.get(
                id=skill_id,
                is_active=True,
            )
        except Skill.DoesNotExist:
            return JsonResponse(
                {
                    "detail":
                    "Skill not found."
                },
                status=404,
            )

        if ProfessionalSkill.objects.filter(
            professional_account=professional_account,
            skill=skill,
        ).exists():
            return JsonResponse(
                {
                    "detail":
                    "This skill is already added."
                },
                status=400,
            )

        professional_skill = ProfessionalSkill.objects.create(
            professional_account=professional_account,
            skill=skill,
            skill_level=data.get(
                "skill_level",
                ProfessionalSkill.SkillLevel.INTERMEDIATE,
            ),
            years_of_experience=data.get(
                "years_of_experience",
                0,
            ),
            is_active=data.get(
                "is_active",
                True,
            ),
        )

        return JsonResponse(
            serialize_professional_skill(
                professional_skill
            ),
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )


@require_http_methods(["GET"])
def professional_skill_list(request, identity_id):
    try:
        professional_account = (
            ProfessionalAccount.objects.get(
                identity_id=identity_id
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

    professional_skills = ProfessionalSkill.objects.filter(
        professional_account=professional_account
    )

    results = [
        serialize_professional_skill(
            professional_skill
        )
        for professional_skill in professional_skills
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
def professional_skill_detail(
    request,
    professional_skill_id,
):
    try:
        professional_skill = (
            ProfessionalSkill.objects.get(
                id=professional_skill_id
            )
        )
    except ProfessionalSkill.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Professional skill not found."
            },
            status=404,
        )

    return JsonResponse(
        serialize_professional_skill(
            professional_skill
        )
    )


@csrf_exempt
@require_http_methods(["PATCH"])
def professional_skill_update(
    request,
    professional_skill_id,
):
    try:
        professional_skill = (
            ProfessionalSkill.objects.get(
                id=professional_skill_id
            )
        )
    except ProfessionalSkill.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Professional skill not found."
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
        "skill_level",
        "years_of_experience",
        "is_active",
    ]

    for field in fields:
        if field in data:
            setattr(
                professional_skill,
                field,
                data[field],
            )

    professional_skill.save()

    return JsonResponse(
        serialize_professional_skill(
            professional_skill
        )
    )


@csrf_exempt
@require_http_methods(["DELETE"])
def professional_skill_delete(
    request,
    professional_skill_id,
):
    try:
        professional_skill = (
            ProfessionalSkill.objects.get(
                id=professional_skill_id
            )
        )
    except ProfessionalSkill.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Professional skill not found."
            },
            status=404,
        )

    professional_skill.delete()

    return JsonResponse(
        {
            "detail":
            "Professional skill deleted successfully."
        }
    )

# Personal Languages

@require_http_methods(["GET", "POST"])
def personal_languages(request, personal_account_id):
    try:
        personal_account = PersonalAccount.objects.get(
            id=personal_account_id,
            is_active=True,
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Personal account not found."},
            status=404,
        )

    if request.method == "GET":
        languages = (
            PersonalLanguage.objects
            .filter(
                personal_account=personal_account,
                is_active=True,
            )
            .select_related("language")
            .order_by("language__name")
        )

        data = [
            {
                "id": item.id,
                "language_id": item.language.id,
                "language_name": item.language.name,
                "language_code": item.language.code,
                "proficiency": item.proficiency,
            }
            for item in languages
        ]

        return JsonResponse(
            {
                "count": len(data),
                "results": data,
            },
            status=200,
        )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    language_id = payload.get("language_id")
    proficiency = payload.get("proficiency")

    if not language_id:
        return JsonResponse(
            {"detail": "language_id is required."},
            status=400,
        )

    if proficiency not in dict(PersonalLanguage.Proficiency.choices):
        return JsonResponse(
            {"detail": "Invalid proficiency."},
            status=400,
        )

    try:
        language = Language.objects.get(
            id=language_id,
            is_active=True,
        )
    except Language.DoesNotExist:
        return JsonResponse(
            {"detail": "Language not found."},
            status=404,
        )

    if PersonalLanguage.objects.filter(
        personal_account=personal_account,
        language=language,
        is_active=True,
    ).exists():
        return JsonResponse(
            {"detail": "This language is already added."},
            status=409,
        )

    personal_language = PersonalLanguage.objects.create(
        personal_account=personal_account,
        language=language,
        proficiency=proficiency,
    )

    return JsonResponse(
        {
            "id": personal_language.id,
            "language_id": language.id,
            "language_name": language.name,
            "language_code": language.code,
            "proficiency": personal_language.proficiency,
        },
        status=201,
    )


@require_http_methods(["GET", "PATCH", "DELETE"])
def personal_language_detail(request, language_id):
    try:
        personal_language = (
            PersonalLanguage.objects
            .select_related(
                "personal_account",
                "language",
            )
            .get(
                id=language_id,
                is_active=True,
            )
        )
    except PersonalLanguage.DoesNotExist:
        return JsonResponse(
            {"detail": "Personal language not found."},
            status=404,
        )

    if request.method == "GET":
        return JsonResponse(
            {
                "id": personal_language.id,
                "personal_account_id": personal_language.personal_account.id,
                "language_id": personal_language.language.id,
                "language_name": personal_language.language.name,
                "language_code": personal_language.language.code,
                "proficiency": personal_language.proficiency,
            },
            status=200,
        )

    if request.method == "DELETE":
        personal_language.is_active = False
        personal_language.save(
            update_fields=["is_active", "updated_at"],
        )

        return JsonResponse(
            {"detail": "Personal language deleted."},
            status=200,
        )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    proficiency = payload.get("proficiency")

    if proficiency is not None:
        if proficiency not in dict(PersonalLanguage.Proficiency.choices):
            return JsonResponse(
                {"detail": "Invalid proficiency."},
                status=400,
            )

        personal_language.proficiency = proficiency

    if "language_id" in payload:
        language_id = payload.get("language_id")

        try:
            language = Language.objects.get(
                id=language_id,
                is_active=True,
            )
        except Language.DoesNotExist:
            return JsonResponse(
                {"detail": "Language not found."},
                status=404,
            )

        duplicate_exists = (
            PersonalLanguage.objects
            .filter(
                personal_account=personal_language.personal_account,
                language=language,
                is_active=True,
            )
            .exclude(id=personal_language.id)
            .exists()
        )

        if duplicate_exists:
            return JsonResponse(
                {"detail": "This language is already added."},
                status=409,
            )

        personal_language.language = language

    personal_language.save()

    return JsonResponse(
        {
            "id": personal_language.id,
            "personal_account_id": personal_language.personal_account.id,
            "language_id": personal_language.language.id,
            "language_name": personal_language.language.name,
            "language_code": personal_language.language.code,
            "proficiency": personal_language.proficiency,
        },
        status=200,
    )

@csrf_exempt
@require_http_methods(["POST"])
def signup(request):
    try:
        data = json.loads(request.body or "{}")

        serializer = SignupSerializer(data=data)

        if not serializer.is_valid():
            return JsonResponse(
                {
                    "errors": serializer.errors,
                },
                status=400,
            )

        identity = serializer.save()

        return JsonResponse(
            {
                "message": "Signup successful.",
                "user": serialize_identity(identity),
            },
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail": "Invalid JSON.",
            },
            status=400,
        )

@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    try:
        data = json.loads(request.body or "{}")

        serializer = LoginSerializer(data=data)

        if not serializer.is_valid():
            return JsonResponse(
                {
                    "errors": serializer.errors,
                },
                status=400,
            )

        identifier = serializer.validated_data[
            "identifier"
        ].strip()

        password = serializer.validated_data[
            "password"
        ]

        identity = (
            UserIdentity.objects.filter(
                username=identifier
            ).first()
        )

        if identity is None:
            identity = (
                UserIdentity.objects.filter(
                    email=identifier
                ).first()
            )

        if identity is None:
            identity = (
                UserIdentity.objects.filter(
                    mobile_number=identifier
                ).first()
            )

        if identity is None:
            return JsonResponse(
                {
                    "detail": "Invalid login credentials.",
                },
                status=401,
            )

        if not identity.check_password(password):
            return JsonResponse(
                {
                    "detail": "Invalid login credentials.",
                },
                status=401,
            )

        if not identity.is_active:
            return JsonResponse(
                {
                    "detail": "This account is inactive.",
                },
                status=403,
            )

        identity.last_login = timezone.now()
        identity.save(
            update_fields=["last_login"],
        )

        return JsonResponse(
            {
                "message": "Login successful.",
                "user": serialize_identity(identity),
            },
            status=200,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail": "Invalid JSON.",
            },
            status=400,
        )       
@csrf_exempt
@require_http_methods(["POST"])
def forgot_password(request):
    try:
        data = json.loads(request.body or "{}")

        serializer = ForgotPasswordSerializer(
            data=data
        )

        if not serializer.is_valid():
            return JsonResponse(
                {
                    "errors": serializer.errors,
                },
                status=400,
            )

        identifier = serializer.validated_data[
            "identifier"
        ].strip()

        identity = (
            UserIdentity.objects.filter(
                username=identifier
            ).first()
        )

        if identity is None:
            identity = (
                UserIdentity.objects.filter(
                    email=identifier
                ).first()
            )

        if identity is None:
            identity = (
                UserIdentity.objects.filter(
                    mobile_number=identifier
                ).first()
            )

        if identity is None:
            return JsonResponse(
                {
                    "detail": "Account not found.",
                },
                status=404,
            )

        PasswordResetOTP.objects.filter(
            identity=identity,
            is_used=False,
        ).update(
            is_used=True,
        )

        otp = str(
            secrets.randbelow(900000) + 100000
        )

        expires_at = (
            timezone.now()
            + timedelta(minutes=10)
        )

        PasswordResetOTP.objects.create(
            identity=identity,
            otp=otp,
            expires_at=expires_at,
        )

        return JsonResponse(
            {
                "message": "Password reset OTP generated.",
                "user_id": str(identity.user_id),
                "otp": otp,
                "expires_at": expires_at.isoformat(),
            },
            status=200,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail": "Invalid JSON.",
            },
            status=400,
        )        

@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    try:
        data = json.loads(request.body or "{}")

        serializer = VerifyOTPSerializer(
            data=data
        )

        if not serializer.is_valid():
            return JsonResponse(
                {
                    "errors": serializer.errors,
                },
                status=400,
            )

        user_id = serializer.validated_data[
            "user_id"
        ]

        otp = serializer.validated_data[
            "otp"
        ]

        try:
            identity = UserIdentity.objects.get(
                user_id=user_id
            )
        except UserIdentity.DoesNotExist:
            return JsonResponse(
                {
                    "detail": "User not found.",
                },
                status=404,
            )

        password_reset_otp = (
            PasswordResetOTP.objects.filter(
                identity=identity,
                otp=otp,
                is_used=False,
            ).order_by(
                "-created_at"
            ).first()
        )

        if password_reset_otp is None:
            return JsonResponse(
                {
                    "detail": "Invalid OTP.",
                },
                status=400,
            )

        if password_reset_otp.expires_at < timezone.now():
            password_reset_otp.is_used = True
            password_reset_otp.save(
                update_fields=["is_used"],
            )

            return JsonResponse(
                {
                    "detail": "OTP has expired.",
                },
                status=400,
            )

        password_reset_otp.is_used = True
        password_reset_otp.is_verified = True

        password_reset_otp.save(
            update_fields=[
                "is_used",
                "is_verified",
            ],
        )

        return JsonResponse(
            {
                "message": "OTP verified successfully.",
                "user_id": str(identity.user_id),
            },
            status=200,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail": "Invalid JSON.",
            },
            status=400,
        )   

@csrf_exempt
@require_http_methods(["POST"])
def reset_password(request):
    try:
        data = json.loads(request.body or "{}")

        serializer = ResetPasswordSerializer(
            data=data
        )

        if not serializer.is_valid():
            return JsonResponse(
                {
                    "errors": serializer.errors,
                },
                status=400,
            )

        user_id = serializer.validated_data[
            "user_id"
        ]

        new_password = serializer.validated_data[
            "new_password"
        ]

        try:
            identity = UserIdentity.objects.get(
                user_id=user_id
            )
        except UserIdentity.DoesNotExist:
            return JsonResponse(
                {
                    "detail": "User not found.",
                },
                status=404,
            )

        password_reset_otp = (
            PasswordResetOTP.objects.filter(
                identity=identity,
                is_verified=True,
                is_used=True,
            ).order_by(
                "-created_at"
            ).first()
        )

        if password_reset_otp is None:
            return JsonResponse(
                {
                    "detail": (
                        "Password reset verification "
                        "is required."
                    ),
                },
                status=400,
            )

        identity.set_password(new_password)
        identity.save(
            update_fields=["password"],
        )

        password_reset_otp.is_verified = False
        password_reset_otp.save(
            update_fields=["is_verified"],
        )

        return JsonResponse(
            {
                "message": (
                    "Password reset successfully."
                ),
            },
            status=200,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail": "Invalid JSON.",
            },
            status=400,
        )    

@require_http_methods(["GET"])
def hobby_list(request):
    hobbies = Hobby.objects.all()

    results = [
        serialize_hobby(hobby)
        for hobby in hobbies
    ]

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def hobby_create(request):
    try:
        data = json.loads(
            request.body or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    name = data.get(
        "name",
        "",
    ).strip()

    slug = data.get(
        "slug",
        "",
    ).strip()

    if not name:
        return JsonResponse(
            {"detail": "Hobby name is required."},
            status=400,
        )

    if not slug:
        return JsonResponse(
            {"detail": "Hobby slug is required."},
            status=400,
        )

    if Hobby.objects.filter(
        name__iexact=name
    ).exists():
        return JsonResponse(
            {
                "detail":
                "A hobby with this name already exists."
            },
            status=400,
        )

    if Hobby.objects.filter(
        slug=slug
    ).exists():
        return JsonResponse(
            {
                "detail":
                "A hobby with this slug already exists."
            },
            status=400,
        )

    hobby = Hobby.objects.create(
        name=name,
        slug=slug,
        description=data.get(
            "description",
            "",
        ),
        is_active=data.get(
            "is_active",
            True,
        ),
        display_order=data.get(
            "display_order",
            0,
        ),
    )

    return JsonResponse(
        serialize_hobby(hobby),
        status=201,
    )       

@csrf_exempt
@require_http_methods(["PATCH"])
def hobby_update(request, hobby_id):
    try:
        hobby = Hobby.objects.get(
            id=hobby_id
        )
    except Hobby.DoesNotExist:
        return JsonResponse(
            {"detail": "Hobby not found."},
            status=404,
        )

    try:
        data = json.loads(
            request.body or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    if "name" in data:
        name = data.get(
            "name",
            "",
        ).strip()

        if not name:
            return JsonResponse(
                {"detail": "Hobby name cannot be empty."},
                status=400,
            )

        duplicate = (
            Hobby.objects.filter(
                name__iexact=name
            )
            .exclude(id=hobby.id)
            .exists()
        )

        if duplicate:
            return JsonResponse(
                {
                    "detail":
                    "A hobby with this name already exists."
                },
                status=400,
            )

        hobby.name = name

    if "slug" in data:
        slug = data.get(
            "slug",
            "",
        ).strip()

        if not slug:
            return JsonResponse(
                {"detail": "Hobby slug cannot be empty."},
                status=400,
            )

        duplicate = (
            Hobby.objects.filter(
                slug=slug
            )
            .exclude(id=hobby.id)
            .exists()
        )

        if duplicate:
            return JsonResponse(
                {
                    "detail":
                    "A hobby with this slug already exists."
                },
                status=400,
            )

        hobby.slug = slug

    fields = [
        "description",
        "is_active",
        "display_order",
    ]

    for field in fields:
        if field in data:
            setattr(
                hobby,
                field,
                data[field],
            )

    hobby.save()

    return JsonResponse(
        serialize_hobby(hobby)
    )  

@csrf_exempt
@require_http_methods(["DELETE"])
def hobby_delete(request, hobby_id):
    try:
        hobby = Hobby.objects.get(
            id=hobby_id
        )
    except Hobby.DoesNotExist:
        return JsonResponse(
            {"detail": "Hobby not found."},
            status=404,
        )

    hobby.delete()

    return JsonResponse(
        {
            "detail":
            "Hobby deleted successfully."
        }
    )

@csrf_exempt
@require_http_methods(["PATCH"])
def hobby_reorder(request):
    try:
        data = json.loads(
            request.body or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    hobby_ids = data.get(
        "hobby_ids"
    )

    if not isinstance(
        hobby_ids,
        list,
    ):
        return JsonResponse(
            {
                "detail":
                "hobby_ids must be a list."
            },
            status=400,
        )

    if not hobby_ids:
        return JsonResponse(
            {
                "detail":
                "hobby_ids cannot be empty."
            },
            status=400,
        )

    if len(hobby_ids) != len(
        set(hobby_ids)
    ):
        return JsonResponse(
            {
                "detail":
                "Duplicate hobby IDs are not allowed."
            },
            status=400,
        )

    hobbies = Hobby.objects.filter(
        id__in=hobby_ids
    )

    if hobbies.count() != len(hobby_ids):
        return JsonResponse(
            {
                "detail":
                "One or more hobbies were not found."
            },
            status=404,
        )

    for index, hobby_id in enumerate(
        hobby_ids,
        start=1,
    ):
        Hobby.objects.filter(
            id=hobby_id
        ).update(
            display_order=index
        )

    ordered_hobbies = Hobby.objects.filter(
        id__in=hobby_ids
    ).order_by(
        "display_order"
    )

    return JsonResponse(
        {
            "detail":
            "Hobbies reordered successfully.",
            "results": [
                serialize_hobby(hobby)
                for hobby in ordered_hobbies
            ],
        }
    )

def serialize_personal_hobby(personal_hobby):
    return {
        "id": personal_hobby.id,
        "personal_account_id": (
            personal_hobby.personal_account_id
        ),
        "hobby": serialize_hobby(
            personal_hobby.hobby
        ),
        "is_active": personal_hobby.is_active,
        "created_at": (
            personal_hobby.created_at.isoformat()
        ),
        "updated_at": (
            personal_hobby.updated_at.isoformat()
        ),
    }


@csrf_exempt
@require_http_methods(["POST"])
def personal_hobby_add(request, personal_account_id):
    try:
        personal_account = PersonalAccount.objects.get(
            id=personal_account_id
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Personal account not found."
            },
            status=404,
        )

    try:
        data = json.loads(
            request.body or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    hobby_id = data.get("hobby_id")

    if not hobby_id:
        return JsonResponse(
            {
                "detail":
                "hobby_id is required."
            },
            status=400,
        )

    try:
        hobby = Hobby.objects.get(
            id=hobby_id,
            is_active=True,
        )
    except Hobby.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Active hobby not found."
            },
            status=404,
        )

    personal_hobby, created = (
        PersonalHobby.objects.get_or_create(
            personal_account=personal_account,
            hobby=hobby,
            defaults={
                "is_active": True,
            },
        )
    )

    if not created:
        return JsonResponse(
            {
                "detail":
                "This hobby is already added "
                "to the personal account."
            },
            status=400,
        )

    return JsonResponse(
        serialize_personal_hobby(
            personal_hobby
        ),
        status=201,
    )


@require_http_methods(["GET"])
def personal_hobby_list(request, personal_account_id):
    try:
        personal_account = PersonalAccount.objects.get(
            id=personal_account_id
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Personal account not found."
            },
            status=404,
        )

    personal_hobbies = (
        PersonalHobby.objects
        .filter(
            personal_account=personal_account,
            is_active=True,
            hobby__is_active=True,
        )
        .select_related("hobby")
        .order_by(
            "hobby__display_order",
            "hobby__name",
        )
    )

    results = [
        serialize_personal_hobby(
            personal_hobby
        )
        for personal_hobby in personal_hobbies
    ]

    return JsonResponse(
        {
            "personal_account_id":
            personal_account.id,
            "count": len(results),
            "results": results,
        }
    )


@csrf_exempt
@require_http_methods(["DELETE"])
def personal_hobby_remove(
    request,
    personal_account_id,
    hobby_id,
):
    try:
        personal_hobby = (
            PersonalHobby.objects.get(
                personal_account_id=personal_account_id,
                hobby_id=hobby_id,
            )
        )
    except PersonalHobby.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Personal hobby not found."
            },
            status=404,
        )

    personal_hobby.delete()

    return JsonResponse(
        {
            "detail":
            "Hobby removed from personal account."
        }
    )
