from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from urllib.parse import urlparse, parse_qs
import re
import json

from core.services.feature_access import get_feature_access
from core.views import IsDeepafyAdmin
from .models import (
    InstitutionTypeGroup,
    InstitutionProfile,
    InstitutionAuthority,
    InstitutionAcademicData,
    InstitutionAcademicLevel,
    InstitutionAcademicSession,
    InstitutionStaffService,
    UnclaimedPerson,
    UnclaimedPersonQualification,
    Subject,
)
from identity.models import UserIdentity, AcademicBackground



@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_academic_sessions(request):
    """
    List or create academic sessions for the authenticated institution.
    """

    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        sessions = InstitutionAcademicSession.objects.filter(
            institution=profile,
            is_active=True,
        )

        return Response({
            "count": sessions.count(),
            "results": [
                {
                    "id": session.id,
                    "name": session.name,
                    "start_date": session.start_date.isoformat(),
                    "end_date": session.end_date.isoformat(),
                    "status": session.status,
                    "is_current": session.is_current,
                    "is_active": session.is_active,
                }
                for session in sessions
            ],
        })

    data = request.data

    name = str(data.get("name") or "").strip()
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    session_status = str(
        data.get("status")
        or InstitutionAcademicSession.STATUS_UPCOMING
    ).strip().upper()

    if not name:
        return Response(
            {"detail": "Session name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not start_date or not end_date:
        return Response(
            {"detail": "Start date and end date are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    valid_statuses = {
        choice[0]
        for choice in InstitutionAcademicSession.STATUS_CHOICES
    }

    if session_status not in valid_statuses:
        return Response(
            {"detail": "Invalid session status."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if InstitutionAcademicSession.objects.filter(
        institution=profile,
        name=name,
    ).exists():
        return Response(
            {"detail": "This session already exists for this institution."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from datetime import date

        parsed_start = date.fromisoformat(str(start_date))
        parsed_end = date.fromisoformat(str(end_date))
    except ValueError:
        return Response(
            {"detail": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if parsed_end < parsed_start:
        return Response(
            {"detail": "End date cannot be before start date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    is_current = bool(data.get("is_current", False))

    if is_current:
        InstitutionAcademicSession.objects.filter(
            institution=profile,
            is_current=True,
        ).update(is_current=False)

    session = InstitutionAcademicSession.objects.create(
        institution=profile,
        name=name,
        start_date=parsed_start,
        end_date=parsed_end,
        status=session_status,
        is_current=is_current,
    )

    return Response(
        {
            "id": session.id,
            "name": session.name,
            "start_date": session.start_date.isoformat(),
            "end_date": session.end_date.isoformat(),
            "status": session.status,
            "is_current": session.is_current,
            "is_active": session.is_active,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_academic_session_detail(request, session_id):
    """
    Update an academic session owned by the authenticated institution.
    """

    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        session = InstitutionAcademicSession.objects.get(
            id=session_id,
            institution=profile,
            is_active=True,
        )
    except InstitutionAcademicSession.DoesNotExist:
        return Response(
            {"detail": "Academic session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    data = request.data

    # Archived sessions are historical records and are locked.
    if session.status == InstitutionAcademicSession.STATUS_ARCHIVED:
        return Response(
            {"detail": "Archived sessions cannot be edited."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Closed sessions keep their historical identity.
    if session.status == InstitutionAcademicSession.STATUS_CLOSED:
        if "name" in data:
            return Response(
                {"detail": "Closed session name cannot be changed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    name = str(data.get("name", session.name)).strip()
    start_date = data.get(
        "start_date",
        session.start_date.isoformat(),
    )
    end_date = data.get(
        "end_date",
        session.end_date.isoformat(),
    )
    session_status = str(
        data.get("status", session.status)
    ).strip().upper()

    if not name:
        return Response(
            {"detail": "Session name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    valid_statuses = {
        choice[0]
        for choice in InstitutionAcademicSession.STATUS_CHOICES
    }

    if session_status not in valid_statuses:
        return Response(
            {"detail": "Invalid session status."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if InstitutionAcademicSession.objects.filter(
        institution=profile,
        name=name,
    ).exclude(id=session.id).exists():
        return Response(
            {"detail": "This session already exists for this institution."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from datetime import date

        parsed_start = date.fromisoformat(str(start_date))
        parsed_end = date.fromisoformat(str(end_date))
    except ValueError:
        return Response(
            {"detail": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if parsed_end < parsed_start:
        return Response(
            {"detail": "End date cannot be before start date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    is_current = bool(
        data.get("is_current", session.is_current)
    )

    if is_current:
        InstitutionAcademicSession.objects.filter(
            institution=profile,
            is_current=True,
        ).exclude(id=session.id).update(
            is_current=False
        )

    session.name = name
    session.start_date = parsed_start
    session.end_date = parsed_end
    session.status = session_status
    session.is_current = is_current
    session.save(
        update_fields=[
            "name",
            "start_date",
            "end_date",
            "status",
            "is_current",
            "updated_at",
        ]
    )

    return Response({
        "id": session.id,
        "name": session.name,
        "start_date": session.start_date.isoformat(),
        "end_date": session.end_date.isoformat(),
        "status": session.status,
        "is_current": session.is_current,
        "is_active": session.is_active,
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def institution_subjects(request):
    """
    List active global subjects or create a new global subject.

    An authenticated institution owner can create a subject.
    Once created, the subject becomes available globally.
    """

    if request.method == "GET":
        query = str(request.query_params.get("q") or "").strip()

        subjects = Subject.objects.filter(
            is_active=True,
        )

        if query:
            subjects = subjects.filter(
                name__icontains=query,
            )

        subjects = subjects.order_by("name")[:50]

        return Response({
            "count": subjects.count(),
            "results": [
                {
                    "id": subject.id,
                    "name": subject.name,
                    "code": subject.code,
                }
                for subject in subjects
            ],
        })

    if not IsDeepafyAdmin().has_permission(request, None):
        return Response(
            {"detail": "Only Deepafy Admin can create subjects."},
            status=status.HTTP_403_FORBIDDEN,
        )

    data = request.data

    name = str(data.get("name") or "").strip()
    code = str(data.get("code") or "").strip()

    if not name:
        return Response(
            {"detail": "Subject name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = Subject.objects.filter(
        name__iexact=name,
    ).first()

    if existing:
        return Response(
            {
                "detail": "This subject already exists.",
                "subject": {
                    "id": existing.id,
                    "name": existing.name,
                    "code": existing.code,
                },
            },
            status=status.HTTP_409_CONFLICT,
        )

    subject = Subject.objects.create(
        name=name,
        code=code,
    )

    return Response(
        {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsDeepafyAdmin])
def institution_subject_detail(request, subject_id):
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response(
            {"detail": "Subject not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    data = request.data

    if "name" in data:
        name = str(data.get("name") or "").strip()

        if not name:
            return Response(
                {"detail": "Subject name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        duplicate = Subject.objects.filter(
            name__iexact=name,
        ).exclude(
            id=subject.id,
        ).exists()

        if duplicate:
            return Response(
                {"detail": "This subject already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        subject.name = name

    if "code" in data:
        subject.code = str(data.get("code") or "").strip()

    if "is_active" in data:
        subject.is_active = bool(data.get("is_active"))

    subject.save()

    return Response({
        "id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "is_active": subject.is_active,
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_staff_services(request):
    """
    List or create institution-specific staff service records.

    The authenticated user must own the institution profile.
    """

    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        services = (
            InstitutionStaffService.objects
            .filter(
                institution=profile,
                is_active=True,
            )
            .select_related("identity", "identity__personal_account")
            .order_by("-joining_date", "identity_id")
        )

        results = [
            {
                "id": service.id,
                "identity_id": service.identity_id,
                "username": service.identity.username,
                "first_name": service.identity.first_name,
                "last_name": service.identity.last_name,
                "profile_photo": (
                    service.identity.personal_account.profile_photo.url
                    if (
                        hasattr(service.identity, "personal_account")
                        and service.identity.personal_account.profile_photo
                    )
                    else None
                ),
                "cover_photo": (
                    service.identity.personal_account.cover_photo.url
                    if (
                        hasattr(service.identity, "personal_account")
                        and service.identity.personal_account.cover_photo
                    )
                    else None
                ),
                "educational_qualifications": [
                    {
                        "education_level": academic.education_level,
                        "degree_certificate": academic.degree_certificate,
                        "field_of_study": academic.field_of_study,
                        "specialization": academic.specialization,
                        "start_year": academic.start_year,
                        "end_year": academic.end_year,
                    }
                    for academic in AcademicBackground.objects.filter(
                        personal_account__identity=service.identity,
                        visibility=AcademicBackground.Visibility.PUBLIC,
                        is_active=True,
                    ).order_by(
                        "display_order",
                        "-end_year",
                        "-start_year",
                    )
                ],
                "designation": service.designation,
                "department": service.department,
                "employment_type": service.employment_type,
                "joining_date": service.joining_date,
                "retirement_date": service.retirement_date,
                "leaving_date": service.leaving_date,
                "passing_date": service.passing_date,
                "status": service.status,
                "bio": service.bio,
                "subjects": [
                    {
                        "id": subject.id,
                        "name": subject.name,
                        "code": subject.code,
                    }
                    for subject in service.subjects.filter(
                        is_active=True
                    ).order_by("name")
                ],
            }
            for service in services
        ]

        return Response({
            "count": len(results),
            "results": results,
        })

    data = request.data

    try:
        identity_id = int(data.get("identity_id"))
    except (TypeError, ValueError):
        return Response(
            {"detail": "A valid identity_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        identity = UserIdentity.objects.get(
            id=identity_id,
            is_active=True,
        )
    except UserIdentity.DoesNotExist:
        return Response(
            {"detail": "Deepafy Identity not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    designation = str(
        data.get("designation") or ""
    ).strip()

    joining_date = data.get("joining_date")

    if not designation or not joining_date:
        return Response(
            {
                "detail": (
                    "Designation and joining_date are required."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    staff_status = data.get(
        "status",
        InstitutionStaffService.STATUS_RUNNING,
    )

    valid_statuses = {
        choice[0]
        for choice in InstitutionStaffService.STATUS_CHOICES
    }

    if staff_status not in valid_statuses:
        return Response(
            {"detail": "Invalid staff status."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    leaving_date = data.get("leaving_date") or None
    retirement_date = data.get("retirement_date") or None
    passing_date = data.get("passing_date") or None

    if (
        staff_status == InstitutionStaffService.STATUS_FORMER
        and not leaving_date
    ):
        return Response(
            {"detail": "Leaving date is required for Former Staff."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        staff_status == InstitutionStaffService.STATUS_RETIRED
        and not retirement_date
    ):
        return Response(
            {
                "detail": (
                    "Retirement date is required for Retired Alumni."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        staff_status == InstitutionStaffService.STATUS_IN_MEMORY
        and not passing_date
    ):
        return Response(
            {
                "detail": (
                    "Passing date is required for In Memory."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    raw_subject_ids = data.get("subject_ids", [])

    if raw_subject_ids in (None, ""):
        raw_subject_ids = []

    if not isinstance(raw_subject_ids, list):
        return Response(
            {"detail": "subject_ids must be a list."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        subject_ids = list({
            int(subject_id)
            for subject_id in raw_subject_ids
        })
    except (TypeError, ValueError):
        return Response(
            {"detail": "subject_ids must contain valid IDs."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    subjects = Subject.objects.filter(
        id__in=subject_ids,
        is_active=True,
    )

    if subjects.count() != len(subject_ids):
        return Response(
            {"detail": "One or more selected subjects are invalid."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if InstitutionStaffService.objects.filter(
        institution=profile,
        identity=identity,
    ).exists():
        return Response(
            {
                "detail": (
                    "This Deepafy person is already "
                    "connected to this institution."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )

    service = InstitutionStaffService.objects.create(
        institution=profile,
        identity=identity,
        designation=designation,
        department=str(
            data.get("department") or ""
        ).strip(),
        employment_type=str(
            data.get("employment_type") or ""
        ).strip(),
        joining_date=joining_date,
        retirement_date=retirement_date,
        leaving_date=leaving_date,
        passing_date=passing_date,
        status=staff_status,
        bio=str(
            data.get("bio") or ""
        ).strip(),
    )

    service.subjects.set(subjects)

    return Response(
        {
            "id": service.id,
            "identity_id": service.identity_id,
            "username": identity.username,
            "first_name": identity.first_name,
            "last_name": identity.last_name,
            "designation": service.designation,
            "department": service.department,
            "employment_type": service.employment_type,
            "joining_date": service.joining_date,
            "retirement_date": service.retirement_date,
            "leaving_date": service.leaving_date,
            "passing_date": service.passing_date,
            "status": service.status,
            "bio": service.bio,
            "subjects": [
                {
                    "id": subject.id,
                    "name": subject.name,
                    "code": subject.code,
                }
                for subject in service.subjects.filter(
                    is_active=True
                ).order_by("name")
            ],
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_unclaimed_staff(request):
    """
    List or create manual institution staff records.

    These records are for people who are not yet connected to a
    Deepafy Identity. Cover photo and Deepafy identity are not used.
    """

    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        people = (
            UnclaimedPerson.objects
            .filter(
                institution=profile,
                is_active=True,
            )
            .order_by("-joining_date", "full_name")
        )

        results = [
            {
                "id": person.id,
                "full_name": person.full_name,
                "profile_photo": (
                    person.profile_photo.url
                    if person.profile_photo
                    else None
                ),
                "designation": person.designation,
                "department": person.department,
                "employment_type": person.employment_type,
                "joining_date": person.joining_date,
                "retirement_date": person.retirement_date,
                "leaving_date": person.leaving_date,
                "passing_date": person.passing_date,
                "status": person.status,
                "bio": person.bio,
                "educational_qualifications": [
                    {
                        "education_level": qualification.education_level,
                        "degree_certificate": qualification.degree_certificate,
                        "field_of_study": qualification.field_of_study,
                        "specialization": qualification.specialization,
                        "start_year": qualification.start_year,
                        "end_year": qualification.end_year,
                    }
                    for qualification in person.educational_qualifications.all()
                ],
            }
            for person in people
        ]

        return Response({
            "count": len(results),
            "results": results,
        })

    data = request.data

    full_name = str(data.get("full_name") or "").strip()
    designation = str(data.get("designation") or "").strip()
    joining_date = data.get("joining_date")

    if not full_name or not designation or not joining_date:
        return Response(
            {
                "detail": (
                    "Full name, designation and joining_date are required."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    staff_status = data.get(
        "status",
        UnclaimedPerson.STATUS_RUNNING,
    )

    valid_statuses = {
        choice[0]
        for choice in UnclaimedPerson.STATUS_CHOICES
    }

    if staff_status not in valid_statuses:
        return Response(
            {"detail": "Invalid staff status."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    leaving_date = data.get("leaving_date") or None
    retirement_date = data.get("retirement_date") or None
    passing_date = data.get("passing_date") or None

    if (
        staff_status == UnclaimedPerson.STATUS_FORMER
        and not leaving_date
    ):
        return Response(
            {"detail": "Leaving date is required for Former Staff."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        staff_status == UnclaimedPerson.STATUS_RETIRED
        and not retirement_date
    ):
        return Response(
            {
                "detail": (
                    "Retirement date is required for Retired Alumni."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        staff_status == UnclaimedPerson.STATUS_IN_MEMORY
        and not passing_date
    ):
        return Response(
            {
                "detail": "Passing date is required for In Memory."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile_photo = request.FILES.get("profile_photo")

    person = UnclaimedPerson.objects.create(
        institution=profile,
        full_name=full_name,
        profile_photo=profile_photo,
        designation=designation,
        department=str(data.get("department") or "").strip(),
        employment_type=str(
            data.get("employment_type") or ""
        ).strip(),
        joining_date=joining_date,
        retirement_date=retirement_date,
        leaving_date=leaving_date,
        passing_date=passing_date,
        status=staff_status,
        bio=str(data.get("bio") or "").strip(),
    )

    # Save educational qualifications for manually added staff.
    educational_qualifications = data.get(
        "educational_qualifications",
        []
    )

    if isinstance(educational_qualifications, str):
        try:
            educational_qualifications = json.loads(
                educational_qualifications
            )
        except (TypeError, ValueError):
            educational_qualifications = []

    if isinstance(educational_qualifications, list):
        for qualification in educational_qualifications:
            if not isinstance(qualification, dict):
                continue

            education_level = str(
                qualification.get("education_level") or ""
            ).strip()

            degree_certificate = str(
                qualification.get("degree_certificate") or ""
            ).strip()

            if not education_level or not degree_certificate:
                continue

            start_year = qualification.get("start_year") or None
            end_year = qualification.get("end_year") or None

            UnclaimedPersonQualification.objects.create(
                person=person,
                education_level=education_level,
                degree_certificate=degree_certificate,
                field_of_study=str(
                    qualification.get("field_of_study") or ""
                ).strip(),
                specialization=str(
                    qualification.get("specialization") or ""
                ).strip(),
                start_year=start_year,
                end_year=end_year,
            )

    return Response(
        {
            "id": person.id,
            "full_name": person.full_name,
            "profile_photo": (
                person.profile_photo.url
                if person.profile_photo
                else None
            ),
            "designation": person.designation,
            "department": person.department,
            "employment_type": person.employment_type,
            "joining_date": person.joining_date,
            "retirement_date": person.retirement_date,
            "leaving_date": person.leaving_date,
            "passing_date": person.passing_date,
            "status": person.status,
            "bio": person.bio,
            "educational_qualifications": [
                {
                    "education_level": qualification.education_level,
                    "degree_certificate": qualification.degree_certificate,
                    "field_of_study": qualification.field_of_study,
                    "specialization": qualification.specialization,
                    "start_year": qualification.start_year,
                    "end_year": qualification.end_year,
                }
                for qualification in person.educational_qualifications.all()
            ],
        },
        status=status.HTTP_201_CREATED,
    )


def extract_map_coordinates(map_url):
    decoded_url = map_url.replace('\u0026', '&')
    parsed = urlparse(decoded_url)
    query_params = parse_qs(parsed.query)

    def valid_coordinates(lat, lon):
        try:
            lat_value = float(lat)
            lon_value = float(lon)
        except (TypeError, ValueError):
            return None

        if -90 <= lat_value <= 90 and -180 <= lon_value <= 180:
            return lat_value, lon_value
        return None

    coordinate_pattern = re.compile(
        r'(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)'
    )

    for key in ('center', 'll', 'q', 'query'):
        for value in query_params.get(key, []):
            match = coordinate_pattern.search(value)
            if match:
                coordinates = valid_coordinates(match.group(1), match.group(2))
                if coordinates:
                    return coordinates

    match = re.search(
        r'/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',
        decoded_url,
    )
    if match:
        coordinates = valid_coordinates(match.group(1), match.group(2))
        if coordinates:
            return coordinates

    match = coordinate_pattern.search(decoded_url)
    if match:
        coordinates = valid_coordinates(match.group(1), match.group(2))
        if coordinates:
            return coordinates

    return None


@api_view(["GET"])
def institution_authority_list(request):
    """
    Return active authorities/boards configured for an
    institution's country and institution type.
    """

    country_id = request.GET.get("country")
    institution_type_id = request.GET.get("institution_type")

    queryset = InstitutionAuthority.objects.filter(
        is_active=True
    ).prefetch_related(
        "institution_types"
    )

    if country_id:
        queryset = queryset.filter(
            country_id=country_id
        )

    if institution_type_id:
        queryset = queryset.filter(
            institution_types__id=institution_type_id
        ).distinct()

    result = {
        "education_boards": [],
        "academic_affiliations": [],
        "regulatory_authorities": [],
        "governing_authorities": [],
    }

    for authority in queryset.order_by(
        "display_order",
        "name",
    ):
        item = {
            "id": authority.id,
            "name": authority.name,
            "short_name": authority.short_name,
            "code": authority.code,
            "relationship_type": authority.relationship_type,
        }

        if authority.relationship_type == "education_board":
            result["education_boards"].append(item)

        elif authority.relationship_type == "academic_affiliation":
            result["academic_affiliations"].append(item)

        elif authority.relationship_type == "regulatory_authority":
            result["regulatory_authorities"].append(item)

        elif authority.relationship_type == "governing_authority":
            result["governing_authorities"].append(item)

    return Response({
        "country": country_id,
        "institution_type": institution_type_id,
        "results": result,
    })


@api_view(["GET"])
def institution_type_list(request):
    groups = InstitutionTypeGroup.objects.filter(
        is_active=True
    ).prefetch_related("institution_types")

    data = []

    for group in groups:
        types = [
            {
                "id": institution_type.id,
                "name": institution_type.name,
            }
            for institution_type in group.institution_types.all()
            if institution_type.is_active
        ]

        if types:
            data.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "types": types,
                }
            )

    return Response(
        {
            "groups": data,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def institution_profile_by_username(request, username):
    from .models import InstitutionProfile

    try:
        profile = (
            InstitutionProfile.objects
            .select_related(
                "identity",
                "institution_type",
                "institution_type__group",
                "country",
                "administrative_location",
            )
            .get(
                identity__username=username,
                identity__is_active=True,
                is_active=True,
            )
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    location = profile.administrative_location

    location_hierarchy = []
    current_location = location

    while current_location:
        location_hierarchy.append({
            "id": str(current_location.location_id),
            "name": current_location.name,
            "level": current_location.level.level,
            "level_name": current_location.level.name,
        })
        current_location = current_location.parent

    return Response(
        {
            "user_id": str(profile.identity.user_id),
            "username": profile.identity.username,
            "institution_name": profile.institution_name,
            "institution_type": {
                "id": profile.institution_type.id,
                "name": profile.institution_type.name,
                "group": profile.institution_type.group.name,
            },
            "institution_types": [
                {
                    "id": item.id,
                    "name": item.name,
                    "group": item.group.name,
                }
                for item in profile.institution_types.select_related("group").all()
            ],
            "established_year": profile.established_year,
            "tagline": profile.tagline,
            "description": profile.description,
            "mission": profile.mission,
            "vision": profile.vision,
            "total_students": profile.total_students,
            "total_teachers": profile.total_teachers,
            "total_staff": profile.total_staff,
            "teacher_student_ratio": (
                round(profile.total_students / profile.total_teachers, 2)
                if profile.total_students is not None and profile.total_teachers
                else None
            ),
            "management_type": profile.management_type,
            "mpo_status": profile.mpo_status,
            "institution_code": profile.institution_code,
            "eiin": profile.eiin,
            "affiliation_board": profile.affiliation_board,
            "affiliations": [
                {
                    "id": authority.id,
                    "name": authority.name,
                    "short_name": authority.short_name,
                    "code": authority.code,
                    "relationship_type": authority.relationship_type,
                }
                for authority in profile.affiliations.filter(is_active=True).order_by(
                    "display_order", "name"
                )
            ],
            "map_location_url": profile.map_location_url,
            "map_latitude": float(profile.map_latitude) if profile.map_latitude is not None else None,
            "map_longitude": float(profile.map_longitude) if profile.map_longitude is not None else None,
            "country": {
                "id": profile.country.id,
                "name": profile.country.name,
                "code": profile.country.code,
            },
            "administrative_location": (
                {
                    "id": str(location.location_id),
                    "name": location.name,
                    "level": location.level.level,
                    "level_name": location.level.name,
                }
                if location
                else None
            ),
            "location_hierarchy": location_hierarchy,
            "full_address": profile.full_address,
            "website": profile.website,
            "email": profile.email,
            "phone": profile.phone,
            "logo": request.build_absolute_uri(profile.logo.url)
            if profile.logo
            else None,
            "cover_photo": request.build_absolute_uri(profile.cover_photo.url)
            if profile.cover_photo
            else None,
            "featured_image": request.build_absolute_uri(profile.featured_image.url)
            if profile.featured_image
            else None,
            "background_color": profile.background_color,
            "background_image": (
                request.build_absolute_uri(profile.background_image.url)
                if profile.background_image
                else None
            ),
            "tab_colors": profile.tab_colors,
            "is_verified": profile.is_verified,
        }
    )


@api_view(["GET", "PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_appearance_update(request):
    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    if request.method == "GET":
        return Response({
            "background_color": profile.background_color,
            "background_image": (
                request.build_absolute_uri(profile.background_image.url)
                if profile.background_image
                else None
            ),
        })

    color_access = get_feature_access(
        request,
        "activity_background_color",
    )

    image_access = get_feature_access(
        request,
        "activity_wallpaper",
    )

    background_color = request.data.get("background_color")

    if background_color is not None:
        if color_access["access"] not in ["free", "premium", "trial"]:
            return Response(
                {"detail": "Premium access required for Background Color."},
                status=403,
            )

        profile.background_color = background_color

    if "background_image" in request.FILES:
        if image_access["access"] not in ["free", "premium", "trial"]:
            return Response(
                {"detail": "Premium access required for Background Image."},
                status=403,
            )

        profile.background_image = request.FILES["background_image"]

    update_fields = [
        "background_color",
        "background_image",
    ]

    if "cover_photo" in request.FILES:
        profile.cover_photo = request.FILES["cover_photo"]
        update_fields.append("cover_photo")

    if "logo" in request.FILES:
        profile.logo = request.FILES["logo"]
        update_fields.append("logo")

    if "featured_image" in request.FILES:
        profile.featured_image = request.FILES["featured_image"]
        update_fields.append("featured_image")

    profile.save(update_fields=update_fields)

    return Response({
        "background_color": profile.background_color,
        "background_image": (
            request.build_absolute_uri(profile.background_image.url)
            if profile.background_image
            else None
        ),
        "cover_photo": (
            request.build_absolute_uri(profile.cover_photo.url)
            if profile.cover_photo
            else None
        ),
        "featured_image": (
            request.build_absolute_uri(profile.featured_image.url)
            if profile.featured_image
            else None
        ),
        "logo": (
            request.build_absolute_uri(profile.logo.url)
            if profile.logo
            else None
        ),
    })


@api_view(["PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_profile_update(request):
    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    fields = [
        "institution_name",
        "established_year",
        "tagline",
        "description",
        "mission",
        "vision",
        "total_students",
        "total_teachers",
        "total_staff",
        "management_type",
        "mpo_status",
        "institution_code",
        "eiin",
        "affiliation_board",
        "full_address",
        "website",
        "email",
        "phone",
    ]

    for field in fields:
        if field in request.data:
            setattr(profile, field, request.data.get(field))

    if "institution_types" in request.data:
        values = request.data.get("institution_types")

        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError:
                return Response(
                    {"detail": "Invalid institution types format."},
                    status=400,
                )

        if not isinstance(values, list):
            return Response(
                {"detail": "Institution types must be a list."},
                status=400,
            )

        try:
            type_ids = [int(value) for value in values if value not in [None, ""]]
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid institution type."},
                status=400,
            )

        if not type_ids:
            return Response(
                {"detail": "Select at least one institution type."},
                status=400,
            )

        profile.institution_type_id = type_ids[0]
        profile.save(update_fields=["institution_type"])
        profile.institution_types.set(type_ids)

    elif "institution_type" in request.data:
        try:
            profile.institution_type_id = int(request.data.get("institution_type"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid institution type."},
                status=400,
            )

    if "country" in request.data:
        try:
            profile.country_id = int(request.data.get("country"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid country."},
                status=400,
            )

    if "administrative_location" in request.data:
        value = request.data.get("administrative_location")
        profile.administrative_location_id = (
            int(value) if value not in [None, ""] else None
        )

    if "affiliation_ids" in request.data:
        values = request.data.get("affiliation_ids")

        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError:
                return Response(
                    {"detail": "Invalid affiliation IDs format."},
                    status=400,
                )

        if not isinstance(values, list):
            return Response(
                {"detail": "Affiliation IDs must be a list."},
                status=400,
            )

        try:
            affiliation_ids = [
                int(value)
                for value in values
                if value not in [None, ""]
            ]
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid affiliation ID."},
                status=400,
            )

        authorities = InstitutionAuthority.objects.filter(
            id__in=affiliation_ids,
            country_id=profile.country_id,
            is_active=True,
        )

        if len(affiliation_ids) != authorities.count():
            return Response(
                {
                    "detail": (
                        "One or more selected affiliations are invalid "
                        "for this institution's country."
                    )
                },
                status=400,
            )

        profile.affiliations.set(authorities)

    if "featured_image" in request.FILES:
        profile.featured_image = request.FILES["featured_image"]

    if "map_location_url" in request.data:
        map_location_url = str(request.data.get("map_location_url") or "").strip()

        if not map_location_url:
            profile.map_location_url = ""
            profile.map_latitude = None
            profile.map_longitude = None
        else:
            parsed_url = urlparse(map_location_url)

            if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
                return Response(
                    {"detail": "Enter a valid map location URL."},
                    status=400,
                )

            coordinates = extract_map_coordinates(map_location_url)

            if not coordinates:
                return Response(
                    {
                        "detail": "Could not extract latitude and longitude from the map URL. Please use a map URL containing coordinates."
                    },
                    status=400,
                )

            profile.map_location_url = map_location_url
            profile.map_latitude = coordinates[0]
            profile.map_longitude = coordinates[1]

    # Admin-controlled Authority / Affiliation
    if "affiliation_ids" in request.data:
        from institution.models import InstitutionAuthority

        raw_affiliation_ids = request.data.get("affiliation_ids")

        if isinstance(raw_affiliation_ids, str):
            try:
                raw_affiliation_ids = json.loads(raw_affiliation_ids)
            except json.JSONDecodeError:
                return Response(
                    {"detail": "Invalid affiliation IDs format."},
                    status=400,
                )

        if raw_affiliation_ids in [None, ""]:
            raw_affiliation_ids = []

        if not isinstance(raw_affiliation_ids, list):
            return Response(
                {"detail": "Affiliation IDs must be a list."},
                status=400,
            )

        try:
            affiliation_ids = [
                int(value)
                for value in raw_affiliation_ids
                if value not in [None, ""]
            ]
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid affiliation ID."},
                status=400,
            )

        authorities = InstitutionAuthority.objects.filter(
            id__in=affiliation_ids,
            country_id=profile.country_id,
            is_active=True,
        ).prefetch_related("institution_types")

        selected_type_ids = set(
            profile.institution_types.values_list("id", flat=True)
        )

        invalid_authorities = []

        for authority in authorities:
            authority_type_ids = set(
                authority.institution_types.values_list("id", flat=True)
            )

            if not authority_type_ids.intersection(selected_type_ids):
                invalid_authorities.append(authority.id)

        if invalid_authorities:
            return Response(
                {
                    "detail": (
                        "One or more selected authorities are not valid "
                        "for the selected institution type."
                    )
                },
                status=400,
            )

        if len(authorities) != len(set(affiliation_ids)):
            return Response(
                {"detail": "One or more affiliations are invalid or inactive."},
                status=400,
            )

        profile.affiliations.set(authorities)

        # New Authority/Affiliation system is now the source of truth.
        profile.affiliation_board = ""

    profile.save()

    return Response({
        "institution_name": profile.institution_name,
        "institution_type": profile.institution_type_id,
        "institution_types": list(
            profile.institution_types.values_list("id", flat=True)
        ),
        "established_year": profile.established_year,
        "tagline": profile.tagline,
        "description": profile.description,
        "mission": profile.mission,
        "vision": profile.vision,
        "featured_image": (
            request.build_absolute_uri(profile.featured_image.url)
            if profile.featured_image
            else None
        ),
        "total_students": profile.total_students,
        "total_teachers": profile.total_teachers,
        "total_staff": profile.total_staff,
        "teacher_student_ratio": (
            round(profile.total_students / profile.total_teachers, 2)
            if profile.total_students is not None and profile.total_teachers
            else None
        ),
        "management_type": profile.management_type,
        "mpo_status": profile.mpo_status,
        "institution_code": profile.institution_code,
        "eiin": profile.eiin,
        "affiliation_board": profile.affiliation_board,
        "affiliations": [
            {
                "id": authority.id,
                "name": authority.name,
                "short_name": authority.short_name,
                "code": authority.code,
                "relationship_type": authority.relationship_type,
            }
            for authority in profile.affiliations.all()
        ],
        "map_location_url": profile.map_location_url,
        "map_latitude": float(profile.map_latitude) if profile.map_latitude is not None else None,
        "map_longitude": float(profile.map_longitude) if profile.map_longitude is not None else None,
        "country": profile.country_id,
        "administrative_location": profile.administrative_location_id,
        "full_address": profile.full_address,
        "website": profile.website,
        "email": profile.email,
        "phone": profile.phone,
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_academic_levels(request):
    """
    GET:
        Return all academic levels for the authenticated institution.

    POST:
        Create a new academic level.
    """

    institution = getattr(
        request.user,
        "institution_profile",
        None,
    )

    if institution is None:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        levels = InstitutionAcademicLevel.objects.filter(
            institution=institution
        )

        return Response(
            [
                {
                    "id": level.id,
                    "type": level.level_type,
                    "name": level.name,
                    "parent": level.parent or None,
                }
                for level in levels
            ],
            status=status.HTTP_200_OK,
        )

    level_type = str(
        request.data.get("type", "Class")
    ).strip() or "Class"

    name = str(
        request.data.get("name", "")
    ).strip()

    parent = str(
        request.data.get("parent", "")
    ).strip()

    if not name:
        return Response(
            {"detail": "Level name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    level, created = InstitutionAcademicLevel.objects.get_or_create(
        institution=institution,
        level_type=level_type,
        name=name,
        parent=parent,
    )

    return Response(
        {
            "id": level.id,
            "type": level.level_type,
            "name": level.name,
            "parent": level.parent or None,
            "created": created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def institution_academic_levels_public(request, username):
    """
    Public read-only academic levels for an institution homepage.
    """

    try:
        profile = InstitutionProfile.objects.get(
            username=username,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    levels = InstitutionAcademicLevel.objects.filter(
        institution=profile
    )

    return Response(
        [
            {
                "id": level.id,
                "type": level.level_type,
                "name": level.name,
                "parent": level.parent or None,
            }
            for level in levels
        ],
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_academic_level_delete(request, level_id):

    institution = getattr(
        request.user,
        "institution_profile",
        None,
    )

    if institution is None:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    level = InstitutionAcademicLevel.objects.filter(
        id=level_id,
        institution=institution,
    ).first()

    if level is None:
        return Response(
            {"detail": "Academic level not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    level.delete()

    return Response(
        {"detail": "Academic level deleted successfully."},
        status=status.HTTP_204_NO_CONTENT,
    )

@api_view(["GET"])
@permission_classes([AllowAny])
def institution_academic_summary(request, username):
    """
    Public academic summary for the institution homepage.
    Returns the latest saved Students academic record.
    """

    try:
        profile = InstitutionProfile.objects.get(
            identity__username=username,
            identity__is_active=True,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    latest = (
        InstitutionAcademicData.objects
        .filter(
            institution=profile,
            category="Students",
        )
        .order_by("-date", "-updated_at")
        .first()
    )

    if latest is None:
        return Response(
            {
                "total": 0,
                "male": 0,
                "female": 0,
                "present": 0,
                "leave": 0,
                "absent": 0,
                "attendance_rate": 0,
                "date": None,
            },
            status=status.HTTP_200_OK,
        )

    attendance_rate = (
        round((latest.present / latest.total) * 100, 1)
        if latest.total > 0
        else 0
    )

    return Response(
        {
            "total": latest.total,
            "male": latest.male,
            "female": latest.female,
            "present": latest.present,
            "leave": latest.leave,
            "absent": latest.absent,
            "attendance_rate": attendance_rate,
            "date": latest.date.isoformat(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def institution_academic_overview(request, username):
    """
    Public academic overview for the institution homepage.

    Returns the latest saved academic record for:
    - Students
    - Teachers
    - Staff
    """

    try:
        profile = InstitutionProfile.objects.get(
            identity__username=username,
            identity__is_active=True,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    categories = ["Students", "Teachers", "Staff"]

    latest_records = {}

    for category in categories:
        record = (
            InstitutionAcademicData.objects
            .filter(
                institution=profile,
                category=category,
            )
            .order_by("-date", "-updated_at")
            .first()
        )

        if record is None:
            latest_records[category] = None
            continue

        attendance_rate = (
            round((record.present / record.total) * 100, 1)
            if record.total > 0
            else 0
        )

        latest_records[category] = {
            "total": record.total,
            "male": record.male,
            "female": record.female,
            "present": record.present,
            "leave": record.leave,
            "absent": record.absent,
            "attendance_rate": attendance_rate,
            "date": record.date.isoformat(),
        }

    return Response(
        {
            "students": latest_records["Students"],
            "teachers": latest_records["Teachers"],
            "staff": latest_records["Staff"],
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST", "PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_academic_data(request):
    """
    GET:
        Return academic data for the authenticated institution.

    POST/PUT:
        Create or update academic data for a date + category.
    """

    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    if request.method == "GET":
        date = request.query_params.get("date")
        category = request.query_params.get("category")

        queryset = InstitutionAcademicData.objects.filter(
            institution=profile
        )

        if date:
            queryset = queryset.filter(date=date)

        if category:
            queryset = queryset.filter(category=category)

        data = [
            {
                "id": item.id,
                "date": item.date.isoformat(),
                "category": item.category,
                "total": item.total,
                "male": item.male,
                "female": item.female,
                "male_present": item.male_present,
                "male_leave": item.male_leave,
                "female_present": item.female_present,
                "female_leave": item.female_leave,
                "present": item.present,
                "leave": item.leave,
                "absent": item.absent,
            }
            for item in queryset
        ]

        return Response({"results": data})

    data = request.data

    date = data.get("date")
    category = data.get("category")

    if date:
        from datetime import date as date_type

        if isinstance(date, str):
            try:
                date = date_type.fromisoformat(date)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=400,
                )

    if not date:
        return Response(
            {"detail": "Date is required."},
            status=400,
        )

    if not category:
        return Response(
            {"detail": "Category is required."},
            status=400,
        )

    numeric_fields = [
        "total",
        "male",
        "female",
        "male_present",
        "male_leave",
        "female_present",
        "female_leave",
    ]

    values = {}

    for field in numeric_fields:
        value = data.get(field)

        if value in [None, ""]:
            return Response(
                {"detail": f"{field} is required."},
                status=400,
            )

        try:
            value = int(value)
        except (TypeError, ValueError):
            return Response(
                {"detail": f"{field} must be an integer."},
                status=400,
            )

        if value < 0:
            return Response(
                {"detail": f"{field} cannot be negative."},
                status=400,
            )

        values[field] = value

    if values["male"] + values["female"] != values["total"]:
        return Response(
            {"detail": "Male + Female must equal Total."},
            status=400,
        )

    if (
        values["male_present"] + values["male_leave"]
        > values["male"]
    ):
        return Response(
            {
                "detail":
                    "Male Present + Male Leave cannot exceed Total Male."
            },
            status=400,
        )

    if (
        values["female_present"] + values["female_leave"]
        > values["female"]
    ):
        return Response(
            {
                "detail":
                    "Female Present + Female Leave cannot exceed Total Female."
            },
            status=400,
        )

    male_absent = (
        values["male"]
        - values["male_present"]
        - values["male_leave"]
    )

    female_absent = (
        values["female"]
        - values["female_present"]
        - values["female_leave"]
    )

    values["present"] = (
        values["male_present"]
        + values["female_present"]
    )

    values["leave"] = (
        values["male_leave"]
        + values["female_leave"]
    )

    values["absent"] = (
        male_absent
        + female_absent
    )

    academic_data, created = InstitutionAcademicData.objects.update_or_create(
        institution=profile,
        date=date,
        category=category,
        defaults=values,
    )

    return Response(
        {
            "id": academic_data.id,
            "date": academic_data.date.isoformat(),
            "category": academic_data.category,
            "total": academic_data.total,
            "male": academic_data.male,
            "female": academic_data.female,
            "male_present": academic_data.male_present,
            "male_leave": academic_data.male_leave,
            "female_present": academic_data.female_present,
            "female_leave": academic_data.female_leave,
            "present": academic_data.present,
            "leave": academic_data.leave,
            "absent": academic_data.absent,
            "created": created,
        },
        status=201 if created else 200,
    )
