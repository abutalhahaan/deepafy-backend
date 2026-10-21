from institution.models import Department
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from urllib.parse import urlparse, parse_qs
from django.db import IntegrityError, transaction
from django.db.models import Q
import re
import json
from django.utils import timezone
from django.core.mail import send_mail

from core.services.feature_access import get_feature_access
from institution.services import generate_global_student_id
from core.views import IsDeepafyAdmin
from .models import (
    InstitutionTypeGroup,
    InstitutionProfile,
    InstitutionAuthority,
    InstitutionAcademicData,
    InstitutionAcademicLevel,
    InstitutionAdmissionType,
    InstitutionAcademicSession,
    InstitutionResultPeriodSettings,
    InstitutionStaffService,
    InstitutionStaffAttendance,
    UnclaimedPerson,
    UnclaimedPersonQualification,
    Subject,
    Student,
    StudentEnrollment,
    StudentEnrollmentAcademicValue,
    StudentInstitutionIdentity,
    StudentProfilePhoto,
    InstitutionAttendanceSettings,
    InstitutionHoliday,
    StudentAttendance,
    InstitutionClassSubject,
    StudentSubject,
    CentralExamType,
    InstitutionExamTypeSelection,
    InstitutionExam,
    InstitutionExamSubject,
    InstitutionExamMark,
    InstitutionGradeScale,
    InstitutionGradeRange,
    InstitutionGradeScaleVersion,
)
from identity.models import UserIdentity, AcademicBackground


def sync_staff_retirement_status(institution):
    """
    Automatically move staff whose retirement date has arrived
    from RUNNING to RETIRED.

    Applies to both:
    - Deepafy staff (InstitutionStaffService)
    - Manual staff (UnclaimedPerson)

    Records are preserved and remain active so they can appear
    in the existing Retired Alumni section.
    """

    today = timezone.localdate()

    InstitutionStaffService.objects.filter(
        institution=institution,
        is_active=True,
        status=InstitutionStaffService.STATUS_RUNNING,
        retirement_date__isnull=False,
        retirement_date__lte=today,
    ).update(
        status=InstitutionStaffService.STATUS_RETIRED,
    )

    UnclaimedPerson.objects.filter(
        institution=institution,
        is_active=True,
        status=UnclaimedPerson.STATUS_RUNNING,
        retirement_date__isnull=False,
        retirement_date__lte=today,
    ).update(
        status=UnclaimedPerson.STATUS_RETIRED,
    )



@api_view(["GET", "PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_result_period_settings(request):
    """Read or save the authenticated institution's result period settings."""
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
        settings = InstitutionResultPeriodSettings.objects.filter(
            institution=profile
        ).first()
        return Response({
            "years": settings.years if settings else [],
            "semesters": settings.semesters if settings else [],
        })

    data = request.data
    years = data.get("years")
    semesters = data.get("semesters")

    if not isinstance(years, list) or not isinstance(semesters, list):
        return Response(
            {"detail": "Years and semesters must both be lists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    allowed_years = [
        f"{n}{'st' if n == 1 else 'nd' if n == 2 else 'rd' if n == 3 else 'th'} Year"
        for n in range(1, 5)
    ]
    allowed_semesters = [
        f"{n}{'st' if n == 1 else 'nd' if n == 2 else 'rd' if n == 3 else 'th'} Semester"
        for n in range(1, 21)
    ]

    if (
        any(not isinstance(v, str) or v not in allowed_years for v in years)
        or any(
            not isinstance(v, str) or v not in allowed_semesters
            for v in semesters
        )
    ):
        return Response(
            {"detail": "One or more Year or Semester options are invalid."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    settings, _ = InstitutionResultPeriodSettings.objects.get_or_create(
        institution=profile,
    )
    settings.years = [v for v in allowed_years if v in years]
    settings.semesters = [v for v in allowed_semesters if v in semesters]
    settings.save(update_fields=["years", "semesters", "updated_at"])

    return Response({
        "years": settings.years,
        "semesters": settings.semesters,
    })


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
        from datetime import date, timedelta, timedelta

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
        from datetime import date, timedelta

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



@api_view(["GET", "PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_selected_departments(request):
    """List or save the authenticated institution's selected global departments."""
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

    if request.method == "PUT":
        department_ids = request.data.get("department_ids")
        if not isinstance(department_ids, list):
            return Response(
                {"detail": "department_ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            department_ids = list({int(value) for value in department_ids})
        except (TypeError, ValueError):
            return Response(
                {"detail": "Every department ID must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        departments = Department.objects.filter(
            id__in=department_ids,
            is_active=True,
        )
        if departments.count() != len(department_ids):
            return Response(
                {"detail": "One or more departments do not exist or are inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.departments.set(departments)

    selected = profile.departments.filter(is_active=True).order_by("name")
    return Response({
        "results": [
            {
                "id": department.id,
                "name": department.name,
                "code": department.code,
            }
            for department in selected
        ],
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def institution_departments(request):
    """
    List active global departments or create a department.

    Department creation is restricted to Deepafy Admin.
    """

    if request.method == "GET":
        query = str(request.query_params.get("q") or "").strip()

        departments = Department.objects.filter(is_active=True)

        if query:
            departments = departments.filter(name__icontains=query)

        departments = departments.order_by("name")[:100]

        return Response({
            "count": departments.count(),
            "results": [
                {
                    "id": department.id,
                    "name": department.name,
                    "code": department.code,
                    "is_active": department.is_active,
                }
                for department in departments
            ],
        })

    if not IsDeepafyAdmin().has_permission(request, None):
        return Response(
            {"detail": "Only Deepafy Admin can create departments."},
            status=status.HTTP_403_FORBIDDEN,
        )

    data = request.data

    name = str(data.get("name") or "").strip()
    code = str(data.get("code") or "").strip()

    if not name:
        return Response(
            {"detail": "Department name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = Department.objects.filter(name__iexact=name).first()

    if existing:
        return Response(
            {
                "detail": "This department already exists.",
                "department": {
                    "id": existing.id,
                    "name": existing.name,
                    "code": existing.code,
                    "is_active": existing.is_active,
                },
            },
            status=status.HTTP_409_CONFLICT,
        )

    department = Department.objects.create(
        name=name,
        code=code,
        is_active=True,
    )

    return Response(
        {
            "id": department.id,
            "name": department.name,
            "code": department.code,
            "is_active": department.is_active,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsDeepafyAdmin])
def institution_department_detail(request, department_id):
    try:
        department = Department.objects.get(id=department_id)
    except Department.DoesNotExist:
        return Response(
            {"detail": "Department not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    data = request.data

    if "name" in data:
        name = str(data.get("name") or "").strip()

        if not name:
            return Response(
                {"detail": "Department name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        duplicate = (
            Department.objects
            .filter(name__iexact=name)
            .exclude(id=department.id)
            .exists()
        )

        if duplicate:
            return Response(
                {"detail": "This department already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        department.name = name

    if "code" in data:
        department.code = str(data.get("code") or "").strip()

    if "is_active" in data:
        department.is_active = bool(data.get("is_active"))

    department.save()

    return Response({
        "id": department.id,
        "name": department.name,
        "code": department.code,
        "is_active": department.is_active,
    })

@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_student_subjects(request):
    """List or create Student Subjects within the caller's allowed scope."""

    is_admin = IsDeepafyAdmin().has_permission(request, None)
    profile = None

    if not is_admin:
        try:
            profile = InstitutionProfile.objects.get(
                identity=request.user,
                is_active=True,
            )
        except InstitutionProfile.DoesNotExist:
            return Response(
                {"detail": "Active institution profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    if request.method == "GET":
        query = str(request.query_params.get("q") or "").strip()
        subjects = StudentSubject.objects.filter(is_active=True)

        if is_admin:
            # Admin can inspect global and institution-owned subjects.
            scope = str(request.query_params.get("scope") or "all").strip().lower()
            if scope == "global":
                subjects = subjects.filter(institution__isnull=True)
            elif scope == "institution":
                subjects = subjects.filter(institution__isnull=False)
            elif scope != "all":
                return Response(
                    {"detail": "scope must be global, institution, or all."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Institution owners can see global subjects and their own subjects.
            subjects = subjects.filter(
                Q(institution__isnull=True) | Q(institution=profile)
            )

        if query:
            subjects = subjects.filter(
                Q(name__icontains=query) | Q(code__icontains=query)
            )

        subjects = subjects.order_by("name", "id")[:100]
        results = [
            {
                "id": subject.id,
                "name": subject.name,
                "code": subject.code,
                "scope": "global" if subject.institution_id is None else "institution",
                "institution_id": subject.institution_id,
            }
            for subject in subjects
        ]
        return Response({"count": len(results), "results": results})

    data = request.data
    name = str(data.get("name") or "").strip()
    code = str(data.get("code") or "").strip()

    if not name:
        return Response(
            {"detail": "Student Subject name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Every Student Subject is global, regardless of who creates it.
    duplicate_query = StudentSubject.objects.filter(name__iexact=name)

    existing = duplicate_query.first()
    if existing:
        return Response(
            {
                "detail": "This Student Subject already exists in this scope.",
                "subject": {
                    "id": existing.id,
                    "name": existing.name,
                    "code": existing.code,
                    "scope": "global" if existing.institution_id is None else "institution",
                },
            },
            status=status.HTTP_409_CONFLICT,
        )

    subject = StudentSubject.objects.create(
        name=name,
        code=code,
        institution=None,
        created_by=request.user,
    )

    return Response(
        {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "scope": "global" if subject.institution_id is None else "institution",
            "institution_id": subject.institution_id,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_student_subject_detail(request, student_subject_id):
    """Update or deactivate a Student Subject within the caller's scope."""

    is_admin = IsDeepafyAdmin().has_permission(request, None)

    try:
        if not is_admin:
            return Response(
                {"detail": "Only Deepafy Admin can modify global Student Subjects."},
                status=status.HTTP_403_FORBIDDEN,
            )
        subject = StudentSubject.objects.get(id=student_subject_id)
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Active institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except StudentSubject.DoesNotExist:
        return Response(
            {"detail": "Student Subject not found in your permitted scope."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        if not is_admin:
            return Response(
                {"detail": "Only Deepafy Admin can delete global Student Subjects."},
                status=status.HTTP_403_FORBIDDEN,
            )

        subject.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    data = request.data

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            return Response(
                {"detail": "Student Subject name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        duplicates = StudentSubject.objects.filter(
            name__iexact=name,
        ).exclude(id=subject.id)

        if duplicates.exists():
            return Response(
                {"detail": "This Student Subject already exists in this scope."},
                status=status.HTTP_409_CONFLICT,
            )

        subject.name = name

    if "code" in data:
        subject.code = str(data.get("code") or "").strip()

    if "is_active" in data:
        value = data.get("is_active")
        if not isinstance(value, bool):
            return Response(
                {"detail": "is_active must be true or false."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subject.is_active = value

    subject.save()

    return Response({
        "id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "is_active": subject.is_active,
        "scope": "global" if subject.institution_id is None else "institution",
        "institution_id": subject.institution_id,
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

        subjects = subjects.order_by("name")

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

    is_deepafy_admin = IsDeepafyAdmin().has_permission(request, None)

    is_institution_owner = (
        request.user
        and request.user.is_authenticated
        and InstitutionProfile.objects.filter(
            identity=request.user,
            is_active=True,
        ).exists()
    )

    if not (is_deepafy_admin or is_institution_owner):
        return Response(
            {
                "detail": (
                    "An active institution profile or Deepafy Admin "
                    "permission is required to create subjects."
                )
            },
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
        sync_staff_retirement_status(profile)

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
        sync_staff_retirement_status(profile)

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
            "global_identity_code": profile.global_identity_code,
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


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_previous_search(request):
    """
    Search active Deepafy institutions for previous-institution selection.

    Searchable identifiers:
    - Username
    - EIIN
    - Institution Code
    - Global Institution Identity (GIID)

    Internal InstitutionProfile ID is intentionally never exposed.
    """

    query = str(request.query_params.get("q", "")).strip()

    if len(query) < 2:
        return Response(
            {
                "count": 0,
                "results": [],
            },
            status=status.HTTP_200_OK,
        )

    profiles = (
        InstitutionProfile.objects
        .select_related(
            "identity",
            "institution_type",
        )
        .filter(
            is_active=True,
            identity__is_active=True,
        )
        .filter(
            Q(identity__username__icontains=query)
            | Q(eiin__icontains=query)
            | Q(institution_code__icontains=query)
            | Q(global_identity_code__icontains=query)
        )
        .order_by("institution_name")[:20]
    )

    results = []

    for profile in profiles:
        results.append(
            {
                "username": profile.identity.username,
                "institution_name": profile.institution_name,
                "eiin": profile.eiin or "",
                "institution_code": profile.institution_code or "",
                "global_identity_code": profile.global_identity_code or "",
                "institution_type": (
                    profile.institution_type.name
                    if profile.institution_type
                    else ""
                ),
            }
        )

    return Response(
        {
            "count": len(results),
            "results": results,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_global_identity_check(request):
    code = str(request.query_params.get("code", "")).strip().upper()

    if not code:
        return Response(
            {
                "available": False,
                "detail": "Global Identity Code is required.",
            },
            status=400,
        )

    if not re.fullmatch(r"[A-Z0-9]{3,8}", code):
        return Response(
            {
                "available": False,
                "detail": "Global Identity Code must be 3 to 8 English letters or numbers.",
            },
            status=400,
        )

    existing = InstitutionProfile.objects.filter(
        global_identity_code=code,
        is_active=True,
    ).first()

    if existing is None:
        return Response({
            "available": True,
            "code": code,
        })

    if existing.identity_id == request.user.id:
        return Response({
            "available": True,
            "code": code,
            "current": True,
        })

    return Response({
        "available": False,
        "code": code,
    })


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

    if "global_identity_code" in request.data:
        requested_code = request.data.get("global_identity_code")

        if requested_code:
            requested_code = str(requested_code).strip().upper()

        if profile.global_identity_code:
            if requested_code and requested_code != profile.global_identity_code:
                return Response(
                    {
                        "detail": "Global Identity Code cannot be changed after it has been set."
                    },
                    status=400,
                )
        elif requested_code:
            profile.global_identity_code = requested_code

    if "institution_code" in request.data:
        requested_code = request.data.get("institution_code")

        if requested_code is not None:
            requested_code = str(requested_code).strip()

        if profile.institution_code:
            if requested_code and requested_code != profile.institution_code:
                return Response(
                    {
                        "detail": "Institution Code cannot be changed after it has been set."
                    },
                    status=400,
                )
        elif requested_code:
            profile.institution_code = requested_code

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

        if value in [None, ""]:
            profile.administrative_location_id = None
        else:
            try:
                from companies.models import AdministrativeLocation

                location = AdministrativeLocation.objects.get(
                    location_id=str(value),
                    country_id=profile.country_id,
                    is_active=True,
                )
            except AdministrativeLocation.DoesNotExist:
                return Response(
                    {"detail": "Invalid administrative location."},
                    status=400,
                )

            profile.administrative_location_id = location.id

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

    try:
        profile.save()
    except IntegrityError as exc:
        if "global_identity_code" in str(exc):
            return Response(
                {
                    "detail": "This Global Institution Identity Code is already in use."
                },
                status=400,
            )
        raise

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
        "global_identity_code": profile.global_identity_code,
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
def institution_student_create(request):
    """
    Create a student Basic Profile.

    Academic enrollment is intentionally NOT created here.
    Enrollment will be added later from the Student Profile.
    """
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    if request.method == "GET":
        global_student_id = str(
            request.query_params.get("global_student_id", "")
        ).strip()

        # List all students belonging to the current institution.
        # A specific student is returned below when global_student_id is provided.
        if not global_student_id:
            identities = list(
                institution.student_identities
                .select_related("student")
                .order_by("-id")
            )

            student_ids = [identity.student.id for identity in identities]

            enrollments = (
                StudentEnrollment.objects
                .filter(
                    institution=institution,
                    student_id__in=student_ids,
                )
                .select_related(
                    "academic_session",
                    "department",
                )
                .prefetch_related(
                    "academic_values__academic_level",
                )
                .order_by("-id")
            )

            enrollment_by_student = {}

            for enrollment in enrollments:
                existing = enrollment_by_student.get(enrollment.student_id)

                if existing is None:
                    enrollment_by_student[enrollment.student_id] = enrollment
                    continue

                if (
                    enrollment.academic_session.is_current
                    and not existing.academic_session.is_current
                ):
                    enrollment_by_student[enrollment.student_id] = enrollment

            return Response(
                {
                    "found": True,
                    "students": [
                        {
                            "id": identity.student.id,
                            "global_student_id": identity.global_student_id,
                            "name": identity.student.name,
                            "father_name": identity.student.father_name,
                            "mother_name": identity.student.mother_name,
                            "gender": identity.student.gender,
                            "date_of_birth": identity.student.date_of_birth,
                            "blood_group": identity.student.blood_group,
                            "mobile": identity.student.mobile,
                            "email": identity.student.email,
                            "present_address": identity.student.present_address,
                            "permanent_address": identity.student.permanent_address,
                            "guardian_name": identity.student.guardian_name,
                            "guardian_relationship": identity.student.guardian_relationship,
                            "guardian_mobile": identity.student.guardian_mobile,
                            "guardian_email": identity.student.guardian_email,
                            "enrollment": (
                                {
                                    "id": enrollment.id,
                                    "academic_session": {
                                        "id": enrollment.academic_session.id,
                                        "name": enrollment.academic_session.name,
                                        "is_current": enrollment.academic_session.is_current,
                                    },
                                    "class_name": enrollment.class_name,
                                    "department": (
                                        {
                                            "id": enrollment.department.id,
                                            "name": enrollment.department.name,
                                            "code": enrollment.department.code,
                                        }
                                        if enrollment.department
                                        else None
                                    ),
                                    "section": enrollment.section,
                                    "roll": enrollment.roll,
                                    "admission_date": enrollment.admission_date,
                                    "status": enrollment.status,
                                    "academic_values": [
                                        {
                                            "id": academic_value.id,
                                            "academic_level_id": academic_value.academic_level.id,
                                            "type": academic_value.academic_level.level_type,
                                            "name": academic_value.academic_level.name,
                                            "parent": academic_value.academic_level.parent or None,
                                            "value": academic_value.value,
                                        }
                                        for academic_value in enrollment.academic_values.all()
                                    ],
                                }
                                if (enrollment := enrollment_by_student.get(identity.student.id))
                                else None
                            ),
                        }
                        for identity in identities
                    ],
                },
                status=200,
            )

        try:
            student = (
                Student.objects
                .prefetch_related(
                    "institution_identities__institution",
                )
                .get(global_student_id=global_student_id)
            )
        except Student.DoesNotExist:
            return Response(
                {
                    "found": False,
                    "detail": "No Deepafy student profile found.",
                },
                status=404,
            )

        identities = list(
            student.institution_identities.all()
        )

        current_identity = next(
            (
                identity
                for identity in identities
                if identity.institution_id == institution.id
            ),
            None,
        )

        def build_student_location(location):
            if not location:
                return None

            hierarchy = []
            current_location = location

            while current_location:
                hierarchy.append({
                    "id": str(current_location.location_id),
                    "name": current_location.name,
                    "level": current_location.level.level,
                    "level_name": current_location.level.name,
                })
                current_location = current_location.parent

            hierarchy.reverse()

            return {
                "country": (
                    {
                        "id": location.country.id,
                        "name": location.country.name,
                        "code": location.country.code,
                    }
                    if location.country
                    else None
                ),
                "location": {
                    "id": str(location.location_id),
                    "name": location.name,
                    "level": location.level.level,
                    "level_name": location.level.name,
                },
                "hierarchy": hierarchy,
            }

        present_location_data = build_student_location(
            student.present_location
        )
        permanent_location_data = build_student_location(
            student.permanent_location
        )

        current_student_photo = (
            StudentProfilePhoto.objects
            .filter(student=student, is_current=True)
            .order_by('-academic_year', '-created_at')
            .first()
        )

        return Response(
            {
                "found": True,
                "can_import": current_identity is None,
                "same_institution": current_identity is not None,
                "student": {
                    "id": student.id,
                    "global_student_id": (
                        current_identity.global_student_id
                        if current_identity
                        else None
                    ),
                    "name": student.name,
                    "photo": (
                        current_student_photo.photo.url
                        if current_student_photo and current_student_photo.photo
                        else None
                    ),
                    "father_name": student.father_name,
                    "mother_name": student.mother_name,
                    "gender": student.gender,
                    "date_of_birth": student.date_of_birth,
                    "blood_group": student.blood_group,
                    "mobile": student.mobile,
                    "email": student.email,
                    "present_address": student.present_address,
                    "present_location": present_location_data,
                    "permanent_address": student.permanent_address,
                    "permanent_location": permanent_location_data,
                    "guardian_name": student.guardian_name,
                    "guardian_relationship": student.guardian_relationship,
                    "guardian_mobile": student.guardian_mobile,
                    "guardian_email": student.guardian_email,
                },
                "institution_identities": [
                    {
                        "institution_id": identity.institution_id,
                        "institution_name": (
                            identity.institution.institution_name
                        ),
                        "global_student_id": identity.global_student_id,
                    }
                    for identity in identities
                ],
            },
            status=200,
        )

    if not institution.global_identity_code:
        return Response(
            {
                "detail": (
                    "Global Institution Identity must be configured "
                    "before adding students."
                )
            },
            status=400,
        )

    name = str(request.data.get("name", "")).strip()

    if not name:
        return Response(
            {
                "detail": "Student name is required.",
                "fields": ["name"],
            },
            status=400,
        )

    from django.db import transaction

    try:
        from companies.models import AdministrativeLocation

        present_location_id = request.data.get("present_location_id") or None
        permanent_location_id = request.data.get("permanent_location_id") or None

        present_location = None
        permanent_location = None

        if present_location_id:
            try:
                present_location = AdministrativeLocation.objects.get(
                    location_id=present_location_id,
                    is_active=True,
                )
            except AdministrativeLocation.DoesNotExist:
                return Response(
                    {"detail": "Invalid present address location."},
                    status=400,
                )

        if permanent_location_id:
            try:
                permanent_location = AdministrativeLocation.objects.get(
                    location_id=permanent_location_id,
                    is_active=True,
                )
            except AdministrativeLocation.DoesNotExist:
                return Response(
                    {"detail": "Invalid permanent address location."},
                    status=400,
                )

        with transaction.atomic():
            global_student_id = generate_global_student_id(institution)

            student = Student.objects.create(
                global_student_id=global_student_id,
                name=name,
                father_name=str(
                    request.data.get("father_name", "")
                ).strip(),
                mother_name=str(
                    request.data.get("mother_name", "")
                ).strip(),
                gender=str(
                    request.data.get("gender", "")
                ).strip(),
                date_of_birth=(
                    request.data.get("date_of_birth") or None
                ),
                blood_group=str(
                    request.data.get("blood_group", "")
                ).strip(),
                mobile=str(
                    request.data.get("mobile", "")
                ).strip(),
                email=str(
                    request.data.get("email", "")
                ).strip(),
                present_location=present_location,
                present_address=str(
                    request.data.get("present_address", "")
                ).strip(),
                permanent_location=permanent_location,
                permanent_address=str(
                    request.data.get("permanent_address", "")
                ).strip(),
                guardian_name=str(
                    request.data.get("guardian_name", "")
                ).strip(),
                guardian_relationship=str(
                    request.data.get("guardian_relationship", "")
                ).strip(),
                guardian_mobile=str(
                    request.data.get("guardian_mobile", "")
                ).strip(),
                guardian_email=str(
                    request.data.get("guardian_email", "")
                ).strip(),
            )

            StudentInstitutionIdentity.objects.create(
                student=student,
                institution=institution,
                global_student_id=global_student_id,
            )

            student_photo = request.FILES.get("photo")
            if student_photo:
                from django.utils import timezone

                StudentProfilePhoto.objects.create(
                    student=student,
                    academic_year=timezone.now().year,
                    photo=student_photo,
                    is_current=True,
                )

    except Exception as exc:
        return Response(
            {
                "detail": "Student profile creation failed.",
                "error": str(exc),
            },
            status=400,
        )

    return Response(
        {
            "detail": "Student profile created successfully.",
            "student": {
                "id": student.id,
                "global_student_id": student.global_student_id,
                "name": student.name,
            },
        },
        status=201,
    )


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_student_photo_update(request, student_id):
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response(
            {"detail": "Student not found."},
            status=404,
        )

    if not StudentInstitutionIdentity.objects.filter(
        student=student,
        institution=institution,
    ).exists():
        return Response(
            {"detail": "Student does not belong to this institution."},
            status=403,
        )

    photo = request.FILES.get("photo")
    if not photo:
        return Response(
            {"detail": "Profile photo is required."},
            status=400,
        )

    from django.utils import timezone

    current_year = timezone.now().year

    StudentProfilePhoto.objects.filter(
        student=student,
        is_current=True,
    ).update(is_current=False)

    current_photo = StudentProfilePhoto.objects.filter(
        student=student,
        academic_year=current_year,
    ).first()

    if current_photo:
        current_photo.photo = photo
        current_photo.is_current = True
        current_photo.save(update_fields=["photo", "is_current"])
    else:
        current_photo = StudentProfilePhoto.objects.create(
            student=student,
            academic_year=current_year,
            photo=photo,
            is_current=True,
        )

    return Response(
        {
            "detail": "Student profile photo updated successfully.",
            "photo": current_photo.photo.url if current_photo.photo else None,
        },
        status=200,
    )


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_student_enrollment(request):
    """
    List or save institution-specific academic enrollment for a student.

    Enrollment is linked through the student's Global Student ID.
    """

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    global_student_id = str(
        request.query_params.get("global_student_id")
        if request.method == "GET"
        else request.data.get("global_student_id", "")
    ).strip()

    if not global_student_id:
        return Response(
            {"detail": "Global Student ID is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        student = Student.objects.get(
            global_student_id=global_student_id,
        )
    except Student.DoesNotExist:
        return Response(
            {"detail": "Student not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not StudentInstitutionIdentity.objects.filter(
        student=student,
        institution=institution,
    ).exists():
        return Response(
            {"detail": "Student does not belong to this institution."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "GET":
        enrollments = (
            StudentEnrollment.objects
            .filter(
                student=student,
                institution=institution,
            )
            .select_related("academic_session", "department", "previous_institution_profile", "admission_type_master")
            .prefetch_related(
                "academic_values__academic_level"
            )
        )

        return Response(
            {
                "found": True,
                "global_student_id": global_student_id,
                "enrollments": [
                    {
                        "id": enrollment.id,
                        "academic_session": {
                            "id": enrollment.academic_session.id,
                            "name": enrollment.academic_session.name,
                            "start_date": enrollment.academic_session.start_date,
                            "end_date": enrollment.academic_session.end_date,
                            "status": enrollment.academic_session.status,
                            "is_current": enrollment.academic_session.is_current,
                        },
                        "class_name": enrollment.class_name,
                        "academic_period": enrollment.academic_period,
                        "academic_values": [
                            {
                                "id": academic_value.id,
                                "academic_level_id": academic_value.academic_level.id,
                                "type": academic_value.academic_level.level_type,
                                "name": academic_value.academic_level.name,
                                "parent": academic_value.academic_level.parent or None,
                                "value": academic_value.value,
                            }
                            for academic_value in enrollment.academic_values.all()
                        ],
                        "department": (
                            {
                                "id": enrollment.department.id,
                                "name": enrollment.department.name,
                                "code": enrollment.department.code,
                            }
                            if enrollment.department
                            else None
                        ),
                        "section": enrollment.section,
                        "roll": enrollment.roll,
                        "admission_date": enrollment.admission_date,
                        "previous_institution_type": enrollment.previous_institution_type,
                        "previous_institution_profile": (
                            {
                                "username": enrollment.previous_institution_profile.identity.username,
                                "institution_name": enrollment.previous_institution_profile.institution_name,
                                "eiin": enrollment.previous_institution_profile.eiin or "",
                                "institution_code": enrollment.previous_institution_profile.institution_code or "",
                                "global_identity_code": enrollment.previous_institution_profile.global_identity_code or "",
                            }
                            if enrollment.previous_institution_profile
                            else None
                        ),
                        "previous_institution_name": enrollment.previous_institution_name,
                        "previous_institution": enrollment.previous_institution,
                        "admission_type_master": (
                            {
                                "id": enrollment.admission_type_master.id,
                                "name": enrollment.admission_type_master.name,
                                "code": enrollment.admission_type_master.code,
                                "description": enrollment.admission_type_master.description,
                            }
                            if enrollment.admission_type_master
                            else None
                        ),
                        "admission_type": enrollment.admission_type,
                        "status": enrollment.status,
                    }
                    for enrollment in enrollments
                ],
            },
            status=status.HTTP_200_OK,
        )

    try:
        academic_session_id = int(
            request.data.get("academic_session_id")
        )
    except (TypeError, ValueError):
        return Response(
            {"detail": "Valid academic_session_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        academic_session = InstitutionAcademicSession.objects.get(
            id=academic_session_id,
            institution=institution,
        )
    except InstitutionAcademicSession.DoesNotExist:
        return Response(
            {"detail": "Academic session not found for this institution."},
            status=status.HTTP_404_NOT_FOUND,
        )

    department = None
    department_id = request.data.get("department_id")

    if department_id not in (None, "", 0, "0"):
        try:
            department = Department.objects.get(
                id=int(department_id),
                is_active=True,
            )
        except (Department.DoesNotExist, TypeError, ValueError):
            return Response(
                {"detail": "Invalid department."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    class_name = str(
        request.data.get("class_name", "")
    ).strip()

    academic_values_data = request.data.get("academic_values", [])

    if academic_values_data in (None, ""):
        academic_values_data = []

    if not isinstance(academic_values_data, list):
        return Response(
            {"detail": "academic_values must be a list."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    validated_academic_values = []

    for item in academic_values_data:
        if not isinstance(item, dict):
            return Response(
                {"detail": "Each academic value must be an object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            academic_level_id = int(item.get("academic_level_id"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Valid academic_level_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        academic_level = InstitutionAcademicLevel.objects.filter(
            id=academic_level_id,
            institution=institution,
        ).first()

        if academic_level is None:
            return Response(
                {
                    "detail": (
                        f"Academic level {academic_level_id} "
                        "does not belong to this institution."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        value = str(item.get("value", "")).strip()

        validated_academic_values.append(
            (academic_level, value)
        )

    dynamic_class_name = ""
    dynamic_section = ""

    for academic_level, value in validated_academic_values:
        if academic_level.level_type.strip().lower() == "class":
            dynamic_class_name = value
        elif academic_level.level_type.strip().lower() == "section":
            dynamic_section = value

    if dynamic_class_name:
        class_name = dynamic_class_name

    section = dynamic_section or str(
        request.data.get("section", "")
    ).strip()

    raw_previous_type = request.data.get("previous_institution_type")
    legacy_previous_institution = str(
        request.data.get("previous_institution", "")
    ).strip()

    if raw_previous_type in (None, "") and legacy_previous_institution:
        previous_institution_type = StudentEnrollment.PREVIOUS_INSTITUTION_MANUAL
    else:
        previous_institution_type = str(
            raw_previous_type
            or StudentEnrollment.PREVIOUS_INSTITUTION_NA
        ).strip().upper()

    valid_previous_types = {
        choice[0]
        for choice in StudentEnrollment.PREVIOUS_INSTITUTION_TYPE_CHOICES
    }

    if previous_institution_type not in valid_previous_types:
        return Response(
            {
                "detail": "Invalid previous institution type.",
                "allowed": sorted(valid_previous_types),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    previous_institution_profile = None
    previous_institution_name = ""
    previous_institution = ""

    if previous_institution_type == StudentEnrollment.PREVIOUS_INSTITUTION_MANUAL:
        previous_institution_name = str(
            request.data.get("previous_institution_name")
            or legacy_previous_institution
            or ""
        ).strip()

        if not previous_institution_name:
            return Response(
                {
                    "detail": (
                        "Previous institution name is required "
                        "for Manual selection."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_institution = previous_institution_name

    elif previous_institution_type == StudentEnrollment.PREVIOUS_INSTITUTION_DEEPAFY:
        previous_institution_username = str(
            request.data.get("previous_institution_username", "")
        ).strip().lstrip("@")

        if not previous_institution_username:
            return Response(
                {
                    "detail": (
                        "Previous institution username is required "
                        "for Deepafy Institution."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_institution_profile = (
            InstitutionProfile.objects
            .select_related("identity")
            .filter(
                identity__username__iexact=previous_institution_username,
                identity__is_active=True,
                is_active=True,
            )
            .first()
        )

        if previous_institution_profile is None:
            return Response(
                {
                    "detail": "Deepafy institution not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if previous_institution_profile.id == institution.id:
            return Response(
                {
                    "detail": (
                        "Current institution cannot be selected "
                        "as the previous institution."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_institution_name = (
            previous_institution_profile.institution_name
        )
        previous_institution = previous_institution_name

    raw_admission_type_master_id = request.data.get(
        "admission_type_master_id"
    )

    admission_type_master = None
    admission_type = str(
        request.data.get("admission_type", "")
    ).strip()

    if raw_admission_type_master_id not in (None, "", 0, "0"):
        try:
            admission_type_master = (
                InstitutionAdmissionType.objects.get(
                    id=int(raw_admission_type_master_id),
                    institution=institution,
                    is_active=True,
                )
            )
        except (
            InstitutionAdmissionType.DoesNotExist,
            TypeError,
            ValueError,
        ):
            return Response(
                {
                    "detail": (
                        "Invalid admission type for this institution."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        admission_type = admission_type_master.name

    status_value = str(
        request.data.get(
            "status",
            StudentEnrollment.STATUS_RUNNING,
        )
    ).strip().upper()

    valid_statuses = {
        choice[0]
        for choice in StudentEnrollment.STATUS_CHOICES
    }

    if status_value not in valid_statuses:
        return Response(
            {
                "detail": "Invalid enrollment status.",
                "allowed": sorted(valid_statuses),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    admission_date = request.data.get("admission_date") or None

    if admission_date:
        from django.utils.dateparse import parse_date

        admission_date = parse_date(str(admission_date))

        if admission_date is None:
            return Response(
                {"detail": "Invalid admission_date. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    enrollment, created = StudentEnrollment.objects.update_or_create(
        student=student,
        institution=institution,
        academic_session=academic_session,
        defaults={
            "class_name": class_name,
            "academic_period": str(request.data.get("academic_period", "")).strip(),
            "department": department,
            "section": section,
            "roll": str(
                request.data.get("roll", "")
            ).strip(),
            "admission_date": admission_date,
            "previous_institution_type": previous_institution_type,
            "previous_institution_profile": previous_institution_profile,
            "previous_institution_name": previous_institution_name,
            "previous_institution": previous_institution,
            "admission_type_master": admission_type_master,
            "admission_type": admission_type,
            "status": status_value,
        },
    )

    StudentEnrollmentAcademicValue.objects.filter(
        enrollment=enrollment,
    ).exclude(
        academic_level__in=[
            academic_level
            for academic_level, _ in validated_academic_values
        ]
    ).delete()

    for academic_level, value in validated_academic_values:
        StudentEnrollmentAcademicValue.objects.update_or_create(
            enrollment=enrollment,
            academic_level=academic_level,
            defaults={
                "value": value,
            },
        )

    return Response(
        {
            "detail": (
                "Academic enrollment created successfully."
                if created
                else "Academic enrollment updated successfully."
            ),
            "created": created,
            "enrollment": {
                "id": enrollment.id,
                "global_student_id": student.global_student_id,
                "academic_session": {
                    "id": academic_session.id,
                    "name": academic_session.name,
                },
                "class_name": enrollment.class_name,
                "academic_period": enrollment.academic_period,
                "academic_values": [
                    {
                        "id": academic_value.id,
                        "academic_level_id": academic_value.academic_level.id,
                        "type": academic_value.academic_level.level_type,
                        "name": academic_value.academic_level.name,
                        "parent": academic_value.academic_level.parent or None,
                        "value": academic_value.value,
                    }
                    for academic_value in enrollment.academic_values.select_related(
                        "academic_level"
                    ).all()
                ],
                "department": (
                    {
                        "id": department.id,
                        "name": department.name,
                        "code": department.code,
                    }
                    if department
                    else None
                ),
                "section": enrollment.section,
                "roll": enrollment.roll,
                "admission_date": enrollment.admission_date,
                "previous_institution_type": enrollment.previous_institution_type,
                "previous_institution_profile": (
                    {
                        "username": enrollment.previous_institution_profile.identity.username,
                        "institution_name": enrollment.previous_institution_profile.institution_name,
                        "eiin": enrollment.previous_institution_profile.eiin or "",
                        "institution_code": enrollment.previous_institution_profile.institution_code or "",
                        "global_identity_code": enrollment.previous_institution_profile.global_identity_code or "",
                    }
                    if enrollment.previous_institution_profile
                    else None
                ),
                "previous_institution_name": enrollment.previous_institution_name,
                "previous_institution": enrollment.previous_institution,
                "admission_type_master": (
                    {
                        "id": enrollment.admission_type_master.id,
                        "name": enrollment.admission_type_master.name,
                        "code": enrollment.admission_type_master.code,
                        "description": enrollment.admission_type_master.description,
                    }
                    if enrollment.admission_type_master
                    else None
                ),
                "admission_type": enrollment.admission_type,
                "status": enrollment.status,
            },
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_admission_types(request):
    """
    List or create admission types for the authenticated institution.
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
        admission_types = InstitutionAdmissionType.objects.filter(
            institution=institution,
            is_active=True,
        )

        return Response(
            [
                {
                    "id": admission_type.id,
                    "name": admission_type.name,
                    "code": admission_type.code,
                    "description": admission_type.description,
                }
                for admission_type in admission_types
            ],
            status=status.HTTP_200_OK,
        )

    name = str(request.data.get("name", "")).strip()
    code = str(request.data.get("code", "")).strip()
    description = str(request.data.get("description", "")).strip()

    if not name:
        return Response(
            {"detail": "Admission type name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    admission_type, created = InstitutionAdmissionType.objects.get_or_create(
        institution=institution,
        name=name,
        defaults={
            "code": code,
            "description": description,
        },
    )

    if not created:
        changed = False

        if code and admission_type.code != code:
            admission_type.code = code
            changed = True

        if description and admission_type.description != description:
            admission_type.description = description
            changed = True

        if changed:
            admission_type.save(
                update_fields=["code", "description", "updated_at"]
            )

    return Response(
        {
            "id": admission_type.id,
            "name": admission_type.name,
            "code": admission_type.code,
            "description": admission_type.description,
            "created": created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


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

@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_attendance_weekly_holidays(request):
    """
    Get or update weekly holidays for the institution.
    Weekday values follow Python convention:
    Monday=0 ... Sunday=6.
    """

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    settings_obj, _ = InstitutionAttendanceSettings.objects.get_or_create(
        institution=institution,
    )

    if request.method == "GET":
        weekly_holidays = settings_obj.weekly_holidays

        if not isinstance(weekly_holidays, list):
            weekly_holidays = []

        return Response({
            "weekly_holidays": weekly_holidays,
        })

    weekly_holidays = request.data.get("weekly_holidays")

    if not isinstance(weekly_holidays, list):
        return Response(
            {"detail": "weekly_holidays must be a list."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        weekly_holidays = sorted(
            set(int(day) for day in weekly_holidays)
        )
    except (TypeError, ValueError):
        return Response(
            {"detail": "Weekly holiday values must be integers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if any(day < 0 or day > 6 for day in weekly_holidays):
        return Response(
            {"detail": "Weekly holiday values must be between 0 and 6."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    settings_obj.weekly_holidays = weekly_holidays
    settings_obj.save(update_fields=["weekly_holidays", "updated_at"])

    return Response({
        "weekly_holidays": weekly_holidays,
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_attendance_holidays(request):
    """
    List or create institution holiday date ranges for an academic session.
    """

    from datetime import date, timedelta

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        session_id = request.query_params.get("academic_session")

        holidays = InstitutionHoliday.objects.filter(
            institution=institution,
            is_active=True,
        )

        if session_id:
            try:
                holidays = holidays.filter(
                    academic_session_id=int(session_id)
                )
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Invalid academic session."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        holidays = holidays.select_related(
            "academic_session",
        ).order_by("from_date", "id")

        return Response({
            "count": holidays.count(),
            "results": [
                {
                    "id": holiday.id,
                    "academic_session": (
                        holiday.academic_session_id
                    ),
                    "academic_session_name": (
                        holiday.academic_session.name
                        if holiday.academic_session
                        else None
                    ),
                    "from_date": holiday.from_date.isoformat(),
                    "to_date": holiday.to_date.isoformat(),
                    "total_days": holiday.total_days,
                    "name": holiday.name,
                    "is_active": holiday.is_active,
                }
                for holiday in holidays
            ],
        })

    data = request.data

    session_id = data.get("academic_session")
    from_date_raw = data.get("from_date")
    to_date_raw = data.get("to_date")
    name = str(data.get("name") or "").strip()

    if not session_id:
        return Response(
            {"detail": "Academic session is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        session = InstitutionAcademicSession.objects.get(
            id=int(session_id),
            institution=institution,
            is_active=True,
        )
    except (
        TypeError,
        ValueError,
        InstitutionAcademicSession.DoesNotExist,
    ):
        return Response(
            {"detail": "Academic session not found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not from_date_raw:
        return Response(
            {"detail": "From date is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from_date = date.fromisoformat(str(from_date_raw))
        to_date = (
            date.fromisoformat(str(to_date_raw))
            if to_date_raw
            else from_date
        )
    except ValueError:
        return Response(
            {"detail": "Invalid holiday date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if from_date > to_date:
        return Response(
            {"detail": "From date cannot be after to date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not name:
        return Response(
            {"detail": "Holiday name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        from_date < session.start_date
        or to_date > session.end_date
    ):
        return Response(
            {
                "detail": (
                    "Holiday dates must be within the academic session."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing_exact = InstitutionHoliday.objects.filter(
        institution=institution,
        academic_session=session,
        from_date=from_date,
        to_date=to_date,
    ).first()

    if existing_exact:
        if existing_exact.is_active:
            return Response(
                {
                    "detail": (
                        "This holiday already exists for the selected dates."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_exact.name = name
        existing_exact.is_active = True
        existing_exact.save(
            update_fields=["name", "is_active", "updated_at"]
        )
        holiday = existing_exact
    else:
        overlapping = InstitutionHoliday.objects.filter(
            institution=institution,
            academic_session=session,
            is_active=True,
            from_date__lte=to_date,
            to_date__gte=from_date,
        ).exists()

        if overlapping:
            return Response(
                {
                    "detail": (
                        "This holiday date range overlaps "
                        "with an existing holiday."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        holiday = InstitutionHoliday.objects.create(
            institution=institution,
            academic_session=session,
            from_date=from_date,
            to_date=to_date,
            name=name,
            is_active=True,
        )


    return Response(
        {
            "id": holiday.id,
            "academic_session": holiday.academic_session_id,
            "academic_session_name": session.name,
            "from_date": holiday.from_date.isoformat(),
            "to_date": holiday.to_date.isoformat(),
            "total_days": holiday.total_days,
            "name": holiday.name,
            "is_active": holiday.is_active,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_attendance_holiday_detail(request, holiday_id):
    """
    Update or soft-delete one institution holiday.
    """

    from datetime import date

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        holiday = InstitutionHoliday.objects.get(
            id=holiday_id,
            institution=institution,
            is_active=True,
        )
    except InstitutionHoliday.DoesNotExist:
        return Response(
            {"detail": "Holiday not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        holiday.is_active = False
        holiday.save(update_fields=["is_active", "updated_at"])

        return Response(
            {"detail": "Holiday deleted successfully."},
            status=status.HTTP_200_OK,
        )

    data = request.data

    name = str(
        data.get("name", holiday.name) or ""
    ).strip()

    from_date_raw = data.get(
        "from_date",
        holiday.from_date.isoformat(),
    )
    to_date_raw = data.get(
        "to_date",
        holiday.to_date.isoformat(),
    )

    if not name:
        return Response(
            {"detail": "Holiday name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from_date = date.fromisoformat(str(from_date_raw))
        to_date = (
            date.fromisoformat(str(to_date_raw))
            if to_date_raw
            else from_date
        )
    except ValueError:
        return Response(
            {"detail": "Invalid holiday date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if from_date > to_date:
        return Response(
            {"detail": "From date cannot be after to date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session = holiday.academic_session

    if session and (
        from_date < session.start_date
        or to_date > session.end_date
    ):
        return Response(
            {
                "detail": (
                    "Holiday dates must be within the academic session."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    overlapping = (
        InstitutionHoliday.objects.filter(
            institution=institution,
            academic_session=session,
            is_active=True,
            from_date__lte=to_date,
            to_date__gte=from_date,
        )
        .exclude(id=holiday.id)
        .exists()
    )

    if overlapping:
        return Response(
            {
                "detail": (
                    "This holiday date range overlaps "
                    "with an existing holiday."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    holiday.name = name
    holiday.from_date = from_date
    holiday.to_date = to_date
    holiday.save(
        update_fields=[
            "name",
            "from_date",
            "to_date",
            "updated_at",
        ],
    )

    return Response({
        "id": holiday.id,
        "academic_session": holiday.academic_session_id,
        "academic_session_name": (
            session.name if session else None
        ),
        "from_date": holiday.from_date.isoformat(),
        "to_date": holiday.to_date.isoformat(),
        "total_days": holiday.total_days,
        "name": holiday.name,
        "is_active": holiday.is_active,
    })


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_attendance_monthly(request):
    """
    Return monthly student attendance sheet for the authenticated institution.

    H (Holiday) is derived from weekly holidays and specific institution holidays.
    StudentAttendance stores only P/A/L.
    """

    from calendar import monthrange
    from datetime import date, timedelta

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        year = int(request.query_params.get("year"))
        month = int(request.query_params.get("month"))
    except (TypeError, ValueError):
        today = date.today()
        year = today.year
        month = today.month

    if month < 1 or month > 12:
        return Response(
            {"detail": "Invalid month."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if year < 2000 or year > 2100:
        return Response(
            {"detail": "Invalid year."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session_id = request.query_params.get("academic_session")
    academic_filters_raw = request.query_params.get("academic_filters")
    academic_filters = {}

    if academic_filters_raw:
        try:
            parsed_filters = json.loads(academic_filters_raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return Response(
                {"detail": "Invalid academic filters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(parsed_filters, dict):
            return Response(
                {"detail": "Academic filters must be an object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        academic_filters = parsed_filters

    enrollments = (
        StudentEnrollment.objects
        .filter(
            institution=institution,
        )
        .select_related(
            "student",
            "academic_session",
            "department",
        )
        .prefetch_related(
            "academic_values__academic_level",
        )
    )

    if session_id:
        try:
            enrollments = enrollments.filter(
                academic_session_id=int(session_id)
            )
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid academic session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    global_student_id = str(
        request.query_params.get("global_student_id", "")
    ).strip()

    if global_student_id:
        enrollments = enrollments.filter(
            student__global_student_id=global_student_id
        )

    if academic_filters:
        for level_id, selected_value in academic_filters.items():
            try:
                level_id = int(level_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Invalid academic level."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            selected_value = str(selected_value or "").strip()
            if not selected_value or selected_value == "all":
                continue

            level_exists = InstitutionAcademicLevel.objects.filter(
                id=level_id,
                institution=institution,
            ).exists()

            if not level_exists:
                return Response(
                    {"detail": "Academic level not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            enrollments = enrollments.filter(
                academic_values__academic_level_id=level_id,
                academic_values__value=selected_value,
            )

    enrollments = enrollments.order_by(
        "roll",
        "student__name",
        "id",
    )

    first_day = date(year, month, 1)
    last_day_number = monthrange(year, month)[1]
    last_day = date(year, month, last_day_number)

    settings_obj = InstitutionAttendanceSettings.objects.filter(
        institution=institution,
    ).first()

    weekly_holidays = set(
        settings_obj.weekly_holidays
        if settings_obj and isinstance(
            settings_obj.weekly_holidays,
            list,
        )
        else []
    )

    holiday_ranges = InstitutionHoliday.objects.filter(
        institution=institution,
        academic_session_id=int(session_id) if session_id else None,
        from_date__lte=last_day,
        to_date__gte=first_day,
        is_active=True,
    )

    holidays = {}

    for holiday in holiday_ranges:
        current_date = max(holiday.from_date, first_day)
        holiday_end = min(holiday.to_date, last_day)

        while current_date <= holiday_end:
            holidays[current_date] = holiday.name
            current_date += timedelta(days=1)

    attendance_records = StudentAttendance.objects.filter(
        enrollment__in=enrollments,
        date__range=(first_day, last_day),
    ).values(
        "enrollment_id",
        "date",
        "status",
    )

    attendance_map = {
        (
            record["enrollment_id"],
            record["date"],
        ): record["status"]
        for record in attendance_records
    }

    today = date.today()

    dates = []

    for day in range(1, last_day_number + 1):
        current_date = date(year, month, day)

        if current_date in holidays:
            status_code = "H"
            holiday_name = holidays[current_date]
        elif current_date.weekday() in weekly_holidays:
            status_code = "H"
            holiday_name = "Weekly Holiday"
        else:
            status_code = None
            holiday_name = None

        dates.append(
            {
                "date": current_date.isoformat(),
                "day": day,
                "weekday": current_date.strftime("%A"),
                "is_today": current_date == today,
                "is_past": current_date < today,
                "is_future": current_date > today,
                "is_holiday": status_code == "H",
                "holiday_name": holiday_name,
                "default_status": (
                    status_code
                    if status_code == "H"
                    else "P"
                ),
            }
        )

    students = []

    for enrollment in enrollments:
        daily = {}

        for date_info in dates:
            current_date = date.fromisoformat(
                date_info["date"]
            )

            if date_info["is_holiday"]:
                daily[str(date_info["day"])] = "H"
                continue

            saved_status = attendance_map.get(
                (enrollment.id, current_date)
            )

            daily[str(date_info["day"])] = (
                saved_status
                if saved_status
                else "P"
            )

        students.append(
            {
                "enrollment_id": enrollment.id,
                "student_id": enrollment.student_id,
                "global_student_id": (
                    enrollment.student.global_student_id
                ),
                "student_name": enrollment.student.name,
                "roll": enrollment.roll,
                "class_name": enrollment.class_name,
                "department": (
                    {
                        "id": enrollment.department_id,
                        "name": enrollment.department.name,
                    }
                    if enrollment.department
                    else None
                ),
                "section": enrollment.section,
                "academic_values": [
                    {
                        "id": value.id,
                        "academic_level_id": value.academic_level_id,
                        "type": value.academic_level.level_type,
                        "name": value.academic_level.name,
                        "parent": value.academic_level.parent,
                        "value": value.value,
                    }
                    for value in enrollment.academic_values.all()
                ],
                "academic_session": {
                    "id": enrollment.academic_session_id,
                    "name": enrollment.academic_session.name,
                    "is_current": (
                        enrollment.academic_session.is_current
                    ),
                },
                "attendance": daily,
            }
        )

    return Response(
        {
            "year": year,
            "month": month,
            "days_in_month": last_day_number,
            "today": today.isoformat(),
            "dates": dates,
            "students": students,
            "count": len(students),
        }
    )

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_staff_attendance_save(request):
    """
    Create or update one daily attendance record for an active running
    teacher or staff member.

    This endpoint is completely separate from student attendance.
    """

    from datetime import date

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    from institution.models import UnclaimedPerson

    staff_service_id = request.data.get("staff_service_id")
    unclaimed_person_id = request.data.get("unclaimed_person_id")
    attendance_date_raw = request.data.get("date")
    attendance_status = str(
        request.data.get("status") or ""
    ).strip().upper()

    # Exactly one staff identifier must be supplied.
    has_staff_service = (
        staff_service_id is not None
        and str(staff_service_id).strip() != ""
    )
    has_manual_staff = (
        unclaimed_person_id is not None
        and str(unclaimed_person_id).strip() != ""
    )

    if has_staff_service == has_manual_staff:
        return Response(
            {
                "detail": (
                    "Provide exactly one of staff_service_id "
                    "or unclaimed_person_id."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    staff_service = None
    unclaimed_person = None

    try:
        if has_staff_service:
            staff_service_id = int(staff_service_id)
            staff_service = InstitutionStaffService.objects.get(
                id=staff_service_id,
                institution=institution,
                status=InstitutionStaffService.STATUS_RUNNING,
                is_active=True,
            )
        else:
            unclaimed_person_id = int(unclaimed_person_id)
            unclaimed_person = UnclaimedPerson.objects.get(
                id=unclaimed_person_id,
                institution=institution,
                status=UnclaimedPerson.STATUS_RUNNING,
                is_active=True,
            )
    except (TypeError, ValueError):
        return Response(
            {"detail": "Invalid staff identifier."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except (
        InstitutionStaffService.DoesNotExist,
        UnclaimedPerson.DoesNotExist,
    ):
        return Response(
            {"detail": "Active running staff member not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        attendance_date = date.fromisoformat(
            str(attendance_date_raw)
        )
    except (TypeError, ValueError):
        return Response(
            {"detail": "Invalid attendance date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if attendance_status not in {
        InstitutionStaffAttendance.STATUS_PRESENT,
        InstitutionStaffAttendance.STATUS_ABSENT,
        InstitutionStaffAttendance.STATUS_LEAVE,
    }:
        return Response(
            {"detail": "Attendance status must be P, A, or L."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    settings_obj = InstitutionAttendanceSettings.objects.filter(
        institution=institution,
    ).first()

    weekly_holidays = set(
        settings_obj.weekly_holidays
        if settings_obj
        and isinstance(settings_obj.weekly_holidays, list)
        else []
    )

    if attendance_date.weekday() in weekly_holidays:
        return Response(
            {"detail": "Attendance cannot be recorded on a weekly holiday."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    holiday_exists = InstitutionHoliday.objects.filter(
        institution=institution,
        from_date__lte=attendance_date,
        to_date__gte=attendance_date,
        is_active=True,
    ).exists()

    if holiday_exists:
        return Response(
            {"detail": "Attendance cannot be recorded on an institution holiday."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    attendance_lookup = {
        "staff_service": staff_service,
        "unclaimed_person": unclaimed_person,
        "date": attendance_date,
    }

    attendance, created = InstitutionStaffAttendance.objects.update_or_create(
        **attendance_lookup,
        defaults={
            "status": attendance_status,
        },
    )

    return Response(
        {
            "id": attendance.id,
            "staff_service_id": attendance.staff_service_id,
            "unclaimed_person_id": attendance.unclaimed_person_id,
            "date": attendance.date.isoformat(),
            "status": attendance.status,
            "created": created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_staff_attendance_monthly(request):
    """
    Return monthly attendance for active running teachers and staff.

    This is completely separate from student attendance.

    Staff can come from two independent sources:
    - Deepafy staff: InstitutionStaffService
    - Manual staff: UnclaimedPerson

    No academic session, class, section, or student enrollment data is used.
    """

    from calendar import monthrange
    from datetime import date, timedelta

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    sync_staff_retirement_status(institution)

    try:
        year = int(request.query_params.get("year"))
        month = int(request.query_params.get("month"))
    except (TypeError, ValueError):
        today = date.today()
        year = today.year
        month = today.month

    if month < 1 or month > 12:
        return Response(
            {"detail": "Invalid month."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if year < 2000 or year > 2100:
        return Response(
            {"detail": "Invalid year."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    staff_services = list(
        InstitutionStaffService.objects
        .filter(
            institution=institution,
            status=InstitutionStaffService.STATUS_RUNNING,
            is_active=True,
        )
        .select_related("identity")
        .order_by(
            "designation",
            "identity__first_name",
            "identity__last_name",
            "identity_id",
        )
    )

    manual_staff = list(
        UnclaimedPerson.objects
        .filter(
            institution=institution,
            status=UnclaimedPerson.STATUS_RUNNING,
            is_active=True,
        )
        .order_by(
            "designation",
            "full_name",
            "id",
        )
    )

    first_day = date(year, month, 1)
    last_day_number = monthrange(year, month)[1]
    last_day = date(year, month, last_day_number)

    settings_obj = InstitutionAttendanceSettings.objects.filter(
        institution=institution,
    ).first()

    weekly_holidays = set(
        settings_obj.weekly_holidays
        if settings_obj
        and isinstance(settings_obj.weekly_holidays, list)
        else []
    )

    holiday_ranges = InstitutionHoliday.objects.filter(
        institution=institution,
        from_date__lte=last_day,
        to_date__gte=first_day,
        is_active=True,
    )

    holidays = {}

    for holiday in holiday_ranges:
        current_date = max(holiday.from_date, first_day)
        holiday_end = min(holiday.to_date, last_day)

        while current_date <= holiday_end:
            holidays[current_date] = holiday.name
            current_date += timedelta(days=1)

    attendance_records = (
        InstitutionStaffAttendance.objects
        .filter(date__range=(first_day, last_day))
        .filter(
            Q(staff_service__in=staff_services)
            | Q(unclaimed_person__in=manual_staff)
        )
        .values(
            "staff_service_id",
            "unclaimed_person_id",
            "date",
            "status",
        )
    )

    attendance_map = {}

    for record in attendance_records:
        if record["staff_service_id"] is not None:
            attendance_map[
                (
                    "deepafy",
                    record["staff_service_id"],
                    record["date"],
                )
            ] = record["status"]

        if record["unclaimed_person_id"] is not None:
            attendance_map[
                (
                    "manual",
                    record["unclaimed_person_id"],
                    record["date"],
                )
            ] = record["status"]

    today = date.today()
    dates = []

    for day in range(1, last_day_number + 1):
        current_date = date(year, month, day)

        if current_date in holidays:
            status_code = "H"
            holiday_name = holidays[current_date]
        elif current_date.weekday() in weekly_holidays:
            status_code = "H"
            holiday_name = "Weekly Holiday"
        else:
            status_code = None
            holiday_name = None

        dates.append(
            {
                "date": current_date.isoformat(),
                "day": day,
                "weekday": current_date.strftime("%A"),
                "is_today": current_date == today,
                "is_past": current_date < today,
                "is_future": current_date > today,
                "is_holiday": status_code == "H",
                "holiday_name": holiday_name,
                "default_status": (
                    status_code
                    if status_code == "H"
                    else "P"
                ),
            }
        )

    teachers_staff = []

    for service in staff_services:
        daily = {}

        for date_info in dates:
            current_date = date.fromisoformat(
                date_info["date"]
            )

            if date_info["is_holiday"]:
                daily[str(date_info["day"])] = "H"
                continue

            saved_status = attendance_map.get(
                ("deepafy", service.id, current_date)
            )

            daily[str(date_info["day"])] = (
                saved_status
                if saved_status
                else "P"
            )

        teachers_staff.append(
            {
                "staff_source": "deepafy",
                "staff_service_id": service.id,
                "unclaimed_person_id": None,
                "identity_id": service.identity_id,
                "name": (
                    f"{service.identity.first_name or ''} "
                    f"{service.identity.last_name or ''}"
                ).strip() or service.identity.username,
                "username": service.identity.username,
                "designation": service.designation,
                "department": service.department,
                "attendance": daily,
            }
        )

    for person in manual_staff:
        daily = {}

        for date_info in dates:
            current_date = date.fromisoformat(
                date_info["date"]
            )

            if date_info["is_holiday"]:
                daily[str(date_info["day"])] = "H"
                continue

            saved_status = attendance_map.get(
                ("manual", person.id, current_date)
            )

            daily[str(date_info["day"])] = (
                saved_status
                if saved_status
                else "P"
            )

        teachers_staff.append(
            {
                "staff_source": "manual",
                "staff_service_id": None,
                "unclaimed_person_id": person.id,
                "identity_id": None,
                "name": person.full_name,
                "username": None,
                "designation": person.designation,
                "department": person.department,
                "attendance": daily,
            }
        )

    teachers_staff.sort(
        key=lambda staff: (
            (staff["designation"] or "").lower(),
            (staff["name"] or "").lower(),
        )
    )

    return Response(
        {
            "year": year,
            "month": month,
            "days_in_month": last_day_number,
            "today": today.isoformat(),
            "dates": dates,
            "teachers_staff": teachers_staff,
            "count": len(teachers_staff),
        }
    )



@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_class_student_roster(request):
    """List existing running students by academic session and level."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    session_id = request.query_params.get("academic_session_id")
    level_id = request.query_params.get("academic_level_id")
    department_id = request.query_params.get("department_id")
    academic_period = request.query_params.get("academic_period")

    if not session_id or not level_id:
        return Response(
            {"detail": "academic_session_id and academic_level_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        session = InstitutionAcademicSession.objects.get(
            id=session_id,
            institution=institution,
            is_active=True,
        )
        level = InstitutionAcademicLevel.objects.get(
            id=level_id,
            institution=institution,
        )
    except (
        InstitutionAcademicSession.DoesNotExist,
        InstitutionAcademicLevel.DoesNotExist,
        ValueError,
        TypeError,
    ):
        return Response(
            {"detail": "Academic session or level not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    enrollments = StudentEnrollment.objects.filter(
        institution=institution,
        academic_session=session,
        status=StudentEnrollment.STATUS_RUNNING,
    ).select_related("student")

    if academic_period:
        enrollments = enrollments.filter(academic_period=academic_period)

    if department_id:
        try:
            department_id = int(department_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "department_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrollments = enrollments.filter(department_id=department_id)

    dynamic_ids = StudentEnrollmentAcademicValue.objects.filter(
        academic_level=level,
        value__iexact=level.name,
        enrollment__in=enrollments,
    ).values_list("enrollment_id", flat=True)

    enrollments = enrollments.filter(
        Q(id__in=dynamic_ids) | Q(class_name__iexact=level.name)
    ).order_by("roll", "student__name", "id")

    return Response({
        "count": enrollments.count(),
        "results": [
            {
                "enrollment_id": e.id,
                "student_id": e.student_id,
                "student_name": e.student.name,
                "global_student_id": e.student.global_student_id,
            }
            for e in enrollments
        ],
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_class_subjects(request):
    """List or save subjects and marks for an institution's academic level."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        level_id = request.query_params.get("academic_level_id")
        if not level_id:
            return Response(
                {"detail": "academic_level_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            level = InstitutionAcademicLevel.objects.get(
                id=level_id,
                institution=institution,
            )
        except (InstitutionAcademicLevel.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "Academic level not found for this institution."},
                status=status.HTTP_404_NOT_FOUND,
            )

        academic_period = request.query_params.get("academic_period", "")
        department_id = request.query_params.get("department_id")
        assignments = InstitutionClassSubject.objects.filter(
            institution=institution,
            academic_level=level,
            academic_period=academic_period,
            is_active=True,
            subject__is_active=True,
        )
        if department_id:
            try:
                department_id = int(department_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "department_id must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not institution.departments.filter(id=department_id, is_active=True).exists():
                return Response(
                    {"detail": "Select a department assigned to this institution."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            assignments = assignments.filter(department_id=department_id)

        assignments = assignments.select_related("academic_level", "subject", "department")

        return Response({
            "count": assignments.count(),
            "results": [
                {
                    "id": item.id,
                    "academic_level_id": item.academic_level_id,
                    "academic_level": item.academic_level.name,
                    "academic_period": item.academic_period,
                    "department_id": item.department_id,
                    "department": item.department.name if item.department_id else None,
                    "subject_id": item.subject_id,
                    "subject": item.subject.name,
                    "code": item.subject.code,
                    "full_marks": item.full_marks,
                    "pass_mark": item.pass_mark,
                }
                for item in assignments
            ],
        })

    level_id = request.data.get("academic_level_id")
    academic_period = str(request.data.get("academic_period") or "").strip()
    department_id = request.data.get("department_id")
    department = None
    if department_id not in (None, ""):
        try:
            department_id = int(department_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "department_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        department = institution.departments.filter(
            id=department_id,
            is_active=True,
        ).first()
        if department is None:
            return Response(
                {"detail": "Select a department assigned to this institution."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    items = request.data.get("subjects")

    # Batch mode: {"academic_level_id": 1, "subjects": [
    #   {"subject_id": 2, "full_marks": 100, "pass_mark": 33}
    # ]}
    if items is not None:
        if not level_id or not isinstance(items, list) or not items:
            return Response(
                {"detail": "academic_level_id and a non-empty subjects list are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            level = InstitutionAcademicLevel.objects.get(
                id=level_id,
                institution=institution,
            )
        except (InstitutionAcademicLevel.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "Academic level not found for this institution."},
                status=status.HTTP_404_NOT_FOUND,
            )

        seen_subject_ids = set()
        validated_items = []

        for item in items:
            if not isinstance(item, dict):
                return Response(
                    {"detail": "Each subject entry must be an object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            subject_id = item.get("subject_id")
            try:
                subject_id = int(subject_id)
                full_marks = int(item.get("full_marks", 100))
                pass_mark = int(item.get("pass_mark", 33))
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Subject ID and marks must be valid integers."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if subject_id in seen_subject_ids:
                return Response(
                    {"detail": f"Duplicate subject ID: {subject_id}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            seen_subject_ids.add(subject_id)

            if full_marks <= 0 or pass_mark < 0 or pass_mark > full_marks:
                return Response(
                    {"detail": "Full marks must be positive and pass mark must be between 0 and full marks."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                subject = Subject.objects.get(id=subject_id, is_active=True)
            except Subject.DoesNotExist:
                return Response(
                    {"detail": f"Active central subject {subject_id} not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            validated_items.append((subject, full_marks, pass_mark))

        saved = []
        with transaction.atomic():
            for subject, full_marks, pass_mark in validated_items:
                assignment, created = InstitutionClassSubject.objects.get_or_create(
                    institution=institution,
                    academic_level=level,
                    department=department,
                    academic_period=academic_period,
                    subject=subject,
                    defaults={
                        "is_active": True,
                        "full_marks": full_marks,
                        "pass_mark": pass_mark,
                    },
                )

                fields_to_update = []
                if not assignment.is_active:
                    assignment.is_active = True
                    fields_to_update.append("is_active")
                if assignment.full_marks != full_marks:
                    assignment.full_marks = full_marks
                    fields_to_update.append("full_marks")
                if assignment.pass_mark != pass_mark:
                    assignment.pass_mark = pass_mark
                    fields_to_update.append("pass_mark")
                if fields_to_update:
                    assignment.save(update_fields=fields_to_update)

                saved.append({
                    "id": assignment.id,
                    "academic_level_id": level.id,
                    "academic_level": level.name,
                    "academic_period": assignment.academic_period,
                    "department_id": assignment.department_id,
                    "department": assignment.department.name if assignment.department_id else None,
                    "subject_id": subject.id,
                    "subject": subject.name,
                    "code": subject.code,
                    "full_marks": assignment.full_marks,
                    "pass_mark": assignment.pass_mark,
                    "created": created,
                })

        return Response(
            {"count": len(saved), "results": saved},
            status=status.HTTP_200_OK,
        )

    # Backward-compatible single-subject mode.
    subject_id = request.data.get("subject_id")
    if not level_id or not subject_id:
        return Response(
            {"detail": "academic_level_id and subject_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        level = InstitutionAcademicLevel.objects.get(
            id=level_id,
            institution=institution,
        )
    except (InstitutionAcademicLevel.DoesNotExist, ValueError, TypeError):
        return Response(
            {"detail": "Academic level not found for this institution."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        subject = Subject.objects.get(id=subject_id, is_active=True)
    except (Subject.DoesNotExist, ValueError, TypeError):
        return Response(
            {"detail": "Active central subject not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        full_marks = int(request.data.get("full_marks", 100))
        pass_mark = int(request.data.get("pass_mark", 33))
    except (TypeError, ValueError):
        return Response(
            {"detail": "Marks must be valid integers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if full_marks <= 0 or pass_mark < 0 or pass_mark > full_marks:
        return Response(
            {"detail": "Full marks must be positive and pass mark must be between 0 and full marks."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    assignment, created = InstitutionClassSubject.objects.get_or_create(
        institution=institution,
        academic_level=level,
        department=department,
        academic_period=academic_period,
        subject=subject,
        defaults={
            "is_active": True,
            "full_marks": full_marks,
            "pass_mark": pass_mark,
        },
    )

    update_fields = []
    if not assignment.is_active:
        assignment.is_active = True
        update_fields.append("is_active")
    if assignment.full_marks != full_marks:
        assignment.full_marks = full_marks
        update_fields.append("full_marks")
    if assignment.pass_mark != pass_mark:
        assignment.pass_mark = pass_mark
        update_fields.append("pass_mark")
    if update_fields:
        assignment.save(update_fields=update_fields)

    return Response(
        {
            "id": assignment.id,
            "academic_level_id": level.id,
            "academic_level": level.name,
            "academic_period": assignment.academic_period,
            "department_id": assignment.department_id,
            "department": assignment.department.name if assignment.department_id else None,
            "subject_id": subject.id,
            "subject": subject.name,
            "code": subject.code,
            "full_marks": assignment.full_marks,
            "pass_mark": assignment.pass_mark,
            "created": created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_class_subject_detail(request, assignment_id):
    """Deactivate a subject assignment owned by the authenticated institution."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        assignment = InstitutionClassSubject.objects.get(
            id=assignment_id,
            institution=institution,
        )
    except InstitutionClassSubject.DoesNotExist:
        return Response(
            {"detail": "Subject assignment not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    assignment.is_active = False
    assignment.save(update_fields=["is_active"])
    return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(["GET", "POST", "DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def institution_exam_types(request):
    """List central exam types and manage each institution's selections."""

    user = getattr(request, "user", None)
    institution = None

    if user and user.is_authenticated:
        institution = InstitutionProfile.objects.filter(
            identity=user,
            is_active=True,
        ).first()

    if request.method == "GET":
        queryset = CentralExamType.objects.filter(is_active=True)
        search = request.query_params.get("q", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        results = list(queryset.order_by("name").values("id", "name")[:50])
        selected_ids = set()

        if institution:
            selected_ids = set(
                InstitutionExamTypeSelection.objects.filter(
                    institution=institution,
                    exam_type_id__in=[item["id"] for item in results],
                ).values_list("exam_type_id", flat=True)
            )

        for item in results:
            item["selected"] = item["id"] in selected_ids

        return Response({"count": len(results), "results": results})

    is_deepafy_admin = IsDeepafyAdmin().has_permission(request, None)
    if not (is_deepafy_admin or institution):
        return Response(
            {"detail": "Only an institution owner or Deepafy admin can manage exam types."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "DELETE":
        if not institution:
            return Response(
                {"detail": "An active institution profile is required to remove a selection."},
                status=status.HTTP_403_FORBIDDEN,
            )

        exam_type_id = (
            request.query_params.get("exam_type_id")
            or request.query_params.get("id")
        )
        if not exam_type_id:
            return Response(
                {"detail": "exam_type_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = InstitutionExamTypeSelection.objects.filter(
            institution=institution,
            exam_type_id=exam_type_id,
        ).delete()

        return Response({
            "removed": bool(deleted),
            "exam_type_id": exam_type_id,
        })

    # POST with exam_type_id selects an existing central type.
    exam_type_id = request.data.get("exam_type_id") or request.data.get("id")
    if exam_type_id:
        if not institution:
            return Response(
                {"detail": "An active institution profile is required to save a selection."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            exam_type = CentralExamType.objects.get(
                pk=exam_type_id,
                is_active=True,
            )
        except (CentralExamType.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "Exam type not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        selection, created = InstitutionExamTypeSelection.objects.get_or_create(
            institution=institution,
            exam_type=exam_type,
        )
        return Response(
            {
                "id": exam_type.id,
                "name": exam_type.name,
                "selected": True,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    # Only an institution owner or Deepafy admin may create a shared exam type.
    if not (is_deepafy_admin or institution):
        return Response(
            {"detail": "Only an institution owner or Deepafy admin can create exam types."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # POST with name creates a shared central type, then selects it for this institution.
    name = request.data.get("name", "")
    if not isinstance(name, str):
        return Response(
            {"detail": "Exam type name must be text."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    name = name.strip()

    if not name:
        return Response(
            {"detail": "Exam type name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(name) > 100:
        return Response(
            {"detail": "Exam type name cannot exceed 100 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            exam_type = CentralExamType.objects.filter(name__iexact=name).first()
            created = False

            if exam_type is None:
                exam_type = CentralExamType.objects.create(name=name)
                created = True

            if institution:
                InstitutionExamTypeSelection.objects.get_or_create(
                    institution=institution,
                    exam_type=exam_type,
                )

    except IntegrityError:
        exam_type = CentralExamType.objects.filter(name__iexact=name).first()
        if exam_type is None:
            raise
        if institution:
            InstitutionExamTypeSelection.objects.get_or_create(
                institution=institution,
                exam_type=exam_type,
            )

    result = {
        "id": exam_type.id,
        "name": exam_type.name,
        "selected": bool(institution),
    }
    if created:
        return Response(result, status=status.HTTP_201_CREATED)
    return Response(result, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_exams(request):
    """List or create examinations for the authenticated institution."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        session_id = request.query_params.get("academic_session_id")
        level_id = request.query_params.get("academic_level_id")
        academic_period = str(
            request.query_params.get("academic_period") or ""
        ).strip()

        default_grade_scale = InstitutionGradeScale.objects.filter(
            institution=institution,
            is_active=True,
            is_default=True,
        ).first()

        if default_grade_scale is None:
            default_grade_scale = InstitutionGradeScale.objects.filter(
                institution=institution,
                is_active=True,
            ).order_by("id").first()

        # Auto-create missing exams from saved exam types.
        if session_id and level_id:
            selected_types = CentralExamType.objects.filter(
                is_active=True,
                institution_selections__institution=institution,
            ).distinct()

            for exam_type in selected_types:
                exam, created = InstitutionExam.objects.get_or_create(
                    institution=institution,
                    academic_session_id=session_id,
                    academic_level_id=level_id,
                    academic_period=academic_period,
                    name=exam_type.name,
                    defaults={
                        "category": "INTERNAL",
                        "exam_type": exam_type.name,
                        "central_exam_type": exam_type,
                        "grade_scale": default_grade_scale,
                    },
                )
                if exam.grade_scale_id is None and default_grade_scale is not None:
                    exam.grade_scale = default_grade_scale
                    exam.save(update_fields=["grade_scale", "updated_at"])

                if not created and exam.central_exam_type_id is None:
                    exam.central_exam_type = exam_type
                    exam.exam_type = exam_type.name
                    exam.save(update_fields=["central_exam_type", "exam_type"])

        exams = InstitutionExam.objects.filter(
            institution=institution,
        ).select_related(
            "academic_session",
            "academic_level",
            "grade_scale",
            "central_exam_type",
        )

        selected_exam_type_ids = InstitutionExamTypeSelection.objects.filter(
            institution=institution,
        ).values_list("exam_type_id", flat=True)

        exams = exams.filter(
            central_exam_type_id__in=selected_exam_type_ids,
        )

        session_id = request.query_params.get("academic_session_id")
        level_id = request.query_params.get("academic_level_id")
        academic_period = str(
            request.query_params.get("academic_period") or ""
        ).strip()

        if session_id:
            exams = exams.filter(academic_session_id=session_id)
        if level_id:
            exams = exams.filter(academic_level_id=level_id)
        if academic_period:
            exams = exams.filter(academic_period=academic_period)

        return Response({
            "count": exams.count(),
            "results": [
                {
                    "id": exam.id,
                    "name": exam.name,
                    "academic_period": exam.academic_period,
                    "category": exam.category,
                    "exam_type": (
                        exam.central_exam_type.name
                        if exam.central_exam_type_id
                        else exam.exam_type
                    ),
                    "exam_type_id": exam.central_exam_type_id,
                    "exam_date": (
                        exam.exam_date.isoformat()
                        if exam.exam_date else None
                    ),
                    "academic_session_id": exam.academic_session_id,
                    "academic_session": exam.academic_session.name,
                    "academic_level_id": exam.academic_level_id,
                    "academic_level": exam.academic_level.name,
                    "grade_scale_id": exam.grade_scale_id,
                    "grade_scale": (
                        exam.grade_scale.name if exam.grade_scale else None
                    ),
                    "full_marks": str(exam.full_marks),
                    "pass_mark": str(exam.pass_mark),
                    "is_published": exam.is_published,
                    "has_been_published": exam.has_been_published,
                }
                for exam in exams
            ],
        })

    data = request.data
    name = str(data.get("name") or "").strip()
    exam_type_id = data.get("exam_type_id")
    exam_type = str(data.get("exam_type") or "").strip()
    category = str(data.get("category") or "INTERNAL").strip()
    academic_period = str(data.get("academic_period") or "").strip()

    central_exam_type = None
    if exam_type_id not in (None, ""):
        try:
            central_exam_type = CentralExamType.objects.get(
                id=exam_type_id,
                is_active=True,
            )
        except (CentralExamType.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "exam_type_id must reference an active exam type."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        exam_type = central_exam_type.name

    if academic_period:
        period_settings = InstitutionResultPeriodSettings.objects.filter(
            institution=institution
        ).first()
        enabled_periods = set(
            (period_settings.years or []) + (period_settings.semesters or [])
        ) if period_settings else set()
        if academic_period not in enabled_periods:
            return Response(
                {"detail": "academic_period must be enabled in Result Period Settings."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if not name or not exam_type:
        return Response(
            {"detail": "name and either exam_type_id or exam_type are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    valid_categories = {
        choice[0]
        for choice in InstitutionExam.CATEGORY_CHOICES
    }
    if category not in valid_categories:
        return Response(
            {"detail": "Invalid exam category."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        session = InstitutionAcademicSession.objects.get(
            id=data.get("academic_session_id"),
            institution=institution,
            is_active=True,
        )
        level = InstitutionAcademicLevel.objects.get(
            id=data.get("academic_level_id"),
            institution=institution,
        )
    except (
        InstitutionAcademicSession.DoesNotExist,
        InstitutionAcademicLevel.DoesNotExist,
        ValueError,
        TypeError,
    ):
        return Response(
            {"detail": "Valid academic_session_id and academic_level_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from decimal import Decimal, InvalidOperation

        full_marks = Decimal(str(data.get("full_marks", "100")))
        pass_mark = Decimal(str(data.get("pass_mark", "33")))
    except (InvalidOperation, TypeError, ValueError):
        return Response(
            {"detail": "full_marks and pass_mark must be valid numbers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        not full_marks.is_finite()
        or not pass_mark.is_finite()
        or full_marks <= 0
        or pass_mark < 0
        or pass_mark > full_marks
    ):
        return Response(
            {"detail": "Require full_marks > 0 and 0 <= pass_mark <= full_marks."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    grade_scale_id = data.get("grade_scale_id")
    grade_scale = None

    if grade_scale_id not in (None, ""):
        try:
            grade_scale = InstitutionGradeScale.objects.get(
                id=grade_scale_id,
                institution=institution,
                is_active=True,
            )
        except (
            InstitutionGradeScale.DoesNotExist,
            ValueError,
            TypeError,
        ):
            return Response(
                {
                    "detail": (
                        "grade_scale_id must reference an active "
                        "grade scale belonging to this institution."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    exam_date = data.get("exam_date") or None
    if exam_date:
        from datetime import date
        try:
            exam_date = date.fromisoformat(str(exam_date))
        except ValueError:
            return Response(
                {"detail": "exam_date must use YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        exam = InstitutionExam.objects.create(
            institution=institution,
            academic_session=session,
            academic_level=level,
            grade_scale=grade_scale,
            academic_period=academic_period,
            name=name,
            category=category,
            exam_type=exam_type,
            central_exam_type=central_exam_type,
            exam_date=exam_date,
            full_marks=full_marks,
            pass_mark=pass_mark,
        )
    except IntegrityError:
        return Response(
            {"detail": "An exam with this name already exists for this session and level."},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "id": exam.id,
            "name": exam.name,
            "academic_period": exam.academic_period,
            "category": exam.category,
            "exam_type": (
                exam.central_exam_type.name
                if exam.central_exam_type_id
                else exam.exam_type
            ),
            "exam_type_id": exam.central_exam_type_id,
            "exam_date": exam.exam_date.isoformat() if exam.exam_date else None,
            "academic_session_id": exam.academic_session_id,
            "academic_level_id": exam.academic_level_id,
            "grade_scale_id": exam.grade_scale_id,
            "grade_scale": (
                exam.grade_scale.name if exam.grade_scale else None
            ),
            "full_marks": str(exam.full_marks),
            "pass_mark": str(exam.pass_mark),
            "is_published": exam.is_published,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_exam_students(request, exam_id):
    """List existing students for the exam's session and academic level."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        exam = InstitutionExam.objects.select_related(
            "academic_session", "academic_level"
        ).get(
            id=exam_id,
            institution=institution,
            academic_session__institution=institution,
            academic_level__institution=institution,
        )
    except InstitutionExam.DoesNotExist:
        return Response(
            {"detail": "Exam not found for this institution."},
            status=status.HTTP_404_NOT_FOUND,
        )

    enrollments = StudentEnrollment.objects.filter(
        institution=institution,
        academic_session=exam.academic_session,
        status=StudentEnrollment.STATUS_RUNNING,
    ).select_related("student")

    dynamic_ids = StudentEnrollmentAcademicValue.objects.filter(
        academic_level=exam.academic_level,
        value__iexact=exam.academic_level.name,
        enrollment__in=enrollments,
    ).values_list("enrollment_id", flat=True)

    enrollments = enrollments.filter(
        Q(id__in=dynamic_ids)
        | Q(class_name__iexact=exam.academic_level.name)
    ).order_by("roll", "student__name", "id")

    return Response({
        "count": enrollments.count(),
        "results": [
            {
                "enrollment_id": e.id,
                "student_id": e.student_id,
                "global_student_id": e.student.global_student_id,
                "student_name": e.student.name,
                "roll": e.roll,
                "class_name": e.class_name,
                "section": e.section,
            }
            for e in enrollments
        ],
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_exam_subjects(request, exam_id):
    """List or add subjects to an institution-owned examination."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        exam = InstitutionExam.objects.get(
            id=exam_id,
            institution=institution,
            academic_session__institution=institution,
            academic_level__institution=institution,
        )
    except InstitutionExam.DoesNotExist:
        return Response(
            {"detail": "Exam not found for this institution."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        items = exam.exam_subjects.filter(
            subject__is_active=True,
        ).select_related("subject")

        return Response({
            "count": items.count(),
            "results": [
                {
                    "id": item.id,
                    "subject_id": item.subject_id,
                    "subject": item.subject.name,
                    "code": item.subject.code,
                    "full_marks": str(item.full_marks),
                    "pass_mark": str(item.pass_mark),
                }
                for item in items
            ],
        })

    if request.method == "POST" and (exam.is_published or exam.has_been_published):
        return Response(
            {
                "detail": (
                    "Cannot modify exam subjects because this exam has already been published."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = request.data
    subject_id = data.get("subject_id")

    try:
        subject = Subject.objects.get(
            id=subject_id,
            is_active=True,
        )
    except (Subject.DoesNotExist, ValueError, TypeError):
        return Response(
            {"detail": "Valid active subject_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Only subjects assigned to this exam's academic level are allowed.
    if not InstitutionClassSubject.objects.filter(
        institution=institution,
        academic_level=exam.academic_level,
        subject=subject,
        is_active=True,
    ).exists():
        return Response(
            {
                "detail": (
                    "Assign this subject to the academic level "
                    "before adding it to the exam."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    from decimal import Decimal, InvalidOperation

    try:
        full_marks = Decimal(str(data.get("full_marks", "100")))
        pass_mark = Decimal(str(data.get("pass_mark", "33")))
    except (InvalidOperation, TypeError, ValueError):
        return Response(
            {"detail": "full_marks and pass_mark must be valid numbers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        not full_marks.is_finite()
        or not pass_mark.is_finite()
        or full_marks <= 0
        or pass_mark < 0
        or pass_mark > full_marks
    ):
        return Response(
            {"detail": "Require full_marks > 0 and 0 <= pass_mark <= full_marks."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    item, created = InstitutionExamSubject.objects.get_or_create(
        exam=exam,
        subject=subject,
        defaults={
            "full_marks": full_marks,
            "pass_mark": pass_mark,
        },
    )

    if not created:
        return Response(
            {"detail": "This subject is already assigned to the exam."},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "id": item.id,
            "subject_id": item.subject_id,
            "subject": item.subject.name,
            "full_marks": str(item.full_marks),
            "pass_mark": str(item.pass_mark),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_exam_marks(request, exam_subject_id):
    """List or save student marks for an exam subject."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        exam_subject = InstitutionExamSubject.objects.select_related(
            "exam",
            "subject",
            "exam__academic_session",
            "exam__academic_level",
        ).get(
            id=exam_subject_id,
            exam__institution=institution,
            exam__academic_session__institution=institution,
            exam__academic_level__institution=institution,
        )
    except InstitutionExamSubject.DoesNotExist:
        return Response(
            {"detail": "Exam subject not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        exam = exam_subject.exam
        enrollments = StudentEnrollment.objects.filter(
            institution=institution,
            academic_session=exam.academic_session,
            status=StudentEnrollment.STATUS_RUNNING,
        ).select_related("student")

        # Support dynamic academic-level values and legacy class_name values.
        dynamic_enrollment_ids = StudentEnrollmentAcademicValue.objects.filter(
            academic_level=exam.academic_level,
            value__iexact=exam.academic_level.name,
            enrollment__in=enrollments,
        ).values_list("enrollment_id", flat=True)

        enrollments = enrollments.filter(
            Q(id__in=dynamic_enrollment_ids)
            | Q(
                class_name__iexact=exam.academic_level.name,
            )
        ).order_by("roll", "student__name", "id")

        saved_marks = {
            mark.enrollment_id: mark
            for mark in InstitutionExamMark.objects.filter(
                exam_subject=exam_subject,
                enrollment__in=enrollments,
            )
        }

        results = []
        for enrollment in enrollments:
            mark = saved_marks.get(enrollment.id)
            results.append({
                "id": mark.id if mark else None,
                "enrollment_id": enrollment.id,
                "student_name": enrollment.student.name,
                "roll": enrollment.roll,
                "class_name": enrollment.class_name,
                "section": enrollment.section,
                "marks_obtained": (
                    str(mark.marks_obtained)
                    if mark and mark.marks_obtained is not None
                    else None
                ),
                "is_absent": mark.is_absent if mark else False,
                "remarks": mark.remarks if mark else "",
            })

        return Response({
            "exam_subject_id": exam_subject.id,
            "subject": exam_subject.subject.name,
            "full_marks": str(exam_subject.full_marks),
            "pass_mark": str(exam_subject.pass_mark),
            "count": len(results),
            "results": results,
        })

    if request.method == "POST" and exam_subject.exam.is_published:
        return Response(
            {
                "detail": (
                    "Cannot modify marks after results are published. "
                    "Unpublish the exam first."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = request.data
    enrollment_id = data.get("enrollment_id")
    is_absent = data.get("is_absent", False)

    if not enrollment_id:
        return Response(
            {"detail": "enrollment_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(is_absent, bool):
        return Response(
            {"detail": "is_absent must be true or false."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            institution=institution,
            academic_session=exam_subject.exam.academic_session,
            status=StudentEnrollment.STATUS_RUNNING,
        )
    except (
        StudentEnrollment.DoesNotExist,
        ValueError,
        TypeError,
    ):
        return Response(
            {"detail": "Student enrollment does not match this exam."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    exam_level = exam_subject.exam.academic_level
    level_value = StudentEnrollmentAcademicValue.objects.filter(
        enrollment=enrollment,
        academic_level=exam_level,
    ).values_list("value", flat=True).first()

    # Use the dynamic academic value when available. Legacy enrollments
    # without a value for this level fall back to class_name.
    enrolled_level_name = (
        level_value.strip()
        if level_value is not None and level_value.strip()
        else enrollment.class_name.strip()
    )

    if enrolled_level_name.casefold() != exam_level.name.strip().casefold():
        return Response(
            {"detail": "Student enrollment does not match this exam's academic level."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from decimal import Decimal, InvalidOperation

    raw_marks = data.get("marks_obtained")

    if is_absent:
        marks_obtained = None
    else:
        if raw_marks is None or raw_marks == "":
            return Response(
                {
                    "detail": (
                        "marks_obtained is required unless the student "
                        "is marked absent."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            marks_obtained = Decimal(str(raw_marks))
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"detail": "marks_obtained must be a valid number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            not marks_obtained.is_finite()
            or marks_obtained < 0
            or marks_obtained > exam_subject.full_marks
        ):
            return Response(
                {
                    "detail": (
                        "marks_obtained must be between 0 and "
                        f"{exam_subject.full_marks}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    mark, created = InstitutionExamMark.objects.update_or_create(
        exam_subject=exam_subject,
        enrollment=enrollment,
        defaults={
            "marks_obtained": marks_obtained,
            "is_absent": is_absent,
            "remarks": str(data.get("remarks") or "").strip()[:255],
        },
    )

    return Response(
        {
            "id": mark.id,
            "exam_subject_id": exam_subject.id,
            "enrollment_id": enrollment.id,
            "marks_obtained": (
                str(mark.marks_obtained)
                if mark.marks_obtained is not None
                else None
            ),
            "is_absent": mark.is_absent,
            "remarks": mark.remarks,
            "created": created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET", "POST", "PATCH"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_grade_scales(request):
    """List or create grading scales owned by the authenticated institution."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        scales = InstitutionGradeScale.objects.filter(
            institution=institution,
        ).prefetch_related("ranges")

        return Response({
            "count": scales.count(),
            "results": [
                {
                    "id": scale.id,
                    "name": scale.name,
                    "maximum_gpa": str(scale.maximum_gpa),
                    "is_default": scale.is_default,
                    "is_active": scale.is_active,
                    "ranges": [
                        {
                            "id": item.id,
                            "grade_name": item.grade_name,
                            "min_percentage": str(item.min_percentage),
                            "max_percentage": str(item.max_percentage),
                            "grade_point": (
                                str(item.grade_point)
                                if item.grade_point is not None
                                else None
                            ),
                        }
                        for item in scale.ranges.all()
                    ],
                }
                for scale in scales
            ],
        })

    if request.method == "PATCH":
        from decimal import Decimal, InvalidOperation

        try:
            scale_id = int(request.data.get("id"))
            scale = InstitutionGradeScale.objects.get(
                id=scale_id,
                institution=institution,
            )
        except (TypeError, ValueError, InstitutionGradeScale.DoesNotExist):
            return Response(
                {"detail": "Grading scale not found for this institution."},
                status=status.HTTP_404_NOT_FOUND,
            )

        name = str(request.data.get("name", scale.name) or "").strip()
        if not name:
            return Response(
                {"detail": "name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            maximum_gpa = Decimal(str(request.data.get("maximum_gpa", scale.maximum_gpa)))
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"detail": "maximum_gpa must be a valid number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not maximum_gpa.is_finite() or maximum_gpa <= 0 or maximum_gpa > Decimal("999.99"):
            return Response(
                {"detail": "Maximum GPA must be greater than 0 and at most 999.99."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if InstitutionGradeScale.objects.filter(
            institution=institution,
            name__iexact=name,
        ).exclude(id=scale.id).exists():
            return Response(
                {"detail": "A grading scale with this name already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        scale.name = name
        scale.maximum_gpa = maximum_gpa
        scale.save(update_fields=["name", "maximum_gpa"])

        return Response({
            "id": scale.id,
            "name": scale.name,
            "maximum_gpa": str(scale.maximum_gpa),
            "is_default": scale.is_default,
            "is_active": scale.is_active,
        })

    name = str(request.data.get("name") or "").strip()
    if not name:
        return Response(
            {"detail": "name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from decimal import Decimal, InvalidOperation

    try:
        maximum_gpa = Decimal(str(request.data.get("maximum_gpa", "5.00")))
    except (InvalidOperation, TypeError, ValueError):
        return Response(
            {"detail": "maximum_gpa must be a valid number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not maximum_gpa.is_finite() or maximum_gpa <= 0 or maximum_gpa > Decimal("999.99"):
        return Response(
            {"detail": "maximum_gpa must be greater than 0 and at most 999.99."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            if InstitutionGradeScale.objects.filter(
                institution=institution,
                name=name,
            ).exists():
                return Response(
                    {"detail": "A grading scale with this name already exists."},
                    status=status.HTTP_409_CONFLICT,
                )

            make_default = request.data.get("is_default", False) is True

            if make_default:
                InstitutionGradeScale.objects.filter(
                    institution=institution,
                    is_default=True,
                ).update(is_default=False)

            scale = InstitutionGradeScale.objects.create(
                institution=institution,
                name=name,
                maximum_gpa=maximum_gpa,
                is_default=make_default,
                is_active=True,
            )
    except IntegrityError:
        return Response(
            {"detail": "A grading scale with this name already exists or could not be created."},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "id": scale.id,
            "name": scale.name,
            "maximum_gpa": str(scale.maximum_gpa),
            "is_default": scale.is_default,
            "is_active": scale.is_active,
            "ranges": [],
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PUT", "PATCH", "DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_grade_range_detail(request, scale_id, range_id):
    """Update or delete a grade range belonging to an institution-owned scale."""
    from decimal import Decimal, InvalidOperation

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        scale = InstitutionGradeScale.objects.get(
            id=scale_id,
            institution=institution,
        )
        item = InstitutionGradeRange.objects.get(
            id=range_id,
            grade_scale=scale,
        )
    except (InstitutionGradeScale.DoesNotExist, InstitutionGradeRange.DoesNotExist, ValueError, TypeError):
        return Response(
            {"detail": "Grading scale or grade range not found for this institution."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    data = request.data
    grade_name = str(data.get("grade_name", item.grade_name) or "").strip()
    if not grade_name:
        return Response(
            {"detail": "grade_name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        minimum = Decimal(str(data.get("min_percentage", item.min_percentage)))
        maximum = Decimal(str(data.get("max_percentage", item.max_percentage)))
        raw_point = data.get("grade_point", item.grade_point)
        grade_point = Decimal(str(raw_point)) if raw_point not in (None, "") else None
    except (InvalidOperation, TypeError, ValueError):
        return Response(
            {"detail": "Percentage values and grade_point must be valid numbers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    values = [minimum, maximum]
    if grade_point is not None:
        values.append(grade_point)

    if (
        any(not value.is_finite() for value in values)
        or minimum < 0
        or maximum > 100
        or minimum > maximum
        or (
            grade_point is not None
            and (
                grade_point < 0
                or grade_point > scale.maximum_gpa
            )
        )
    ):
        return Response(
            {
                "detail": (
                    "Require 0 <= min_percentage <= max_percentage <= 100 "
                    "and 0 <= grade_point <= maximum_gpa."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    duplicates = scale.ranges.exclude(id=item.id)
    if duplicates.filter(grade_name__iexact=grade_name).exists():
        return Response(
            {"detail": "This grade name already exists in the scale."},
            status=status.HTTP_409_CONFLICT,
        )

    if duplicates.filter(
        min_percentage__lte=maximum,
        max_percentage__gte=minimum,
    ).exists():
        return Response(
            {"detail": "This percentage range overlaps an existing grade range."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    item.grade_name = grade_name
    item.min_percentage = minimum
    item.max_percentage = maximum
    item.grade_point = grade_point
    item.save(update_fields=[
        "grade_name",
        "min_percentage",
        "max_percentage",
        "grade_point",
    ])

    return Response({
        "id": item.id,
        "grade_name": item.grade_name,
        "min_percentage": str(item.min_percentage),
        "max_percentage": str(item.max_percentage),
        "grade_point": str(item.grade_point) if item.grade_point is not None else None,
    })

@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_grade_ranges(request, scale_id):
    """List or add percentage ranges to an institution-owned grading scale."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        scale = InstitutionGradeScale.objects.get(
            id=scale_id,
            institution=institution,
        )
    except (InstitutionGradeScale.DoesNotExist, ValueError, TypeError):
        return Response(
            {"detail": "Grading scale not found for this institution."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        ranges = scale.ranges.all()
        return Response({
            "count": ranges.count(),
            "results": [
                {
                    "id": item.id,
                    "grade_name": item.grade_name,
                    "min_percentage": str(item.min_percentage),
                    "max_percentage": str(item.max_percentage),
                    "grade_point": (
                        str(item.grade_point)
                        if item.grade_point is not None
                        else None
                    ),
                }
                for item in ranges
            ],
        })

    from decimal import Decimal, InvalidOperation

    grade_name = str(request.data.get("grade_name") or "").strip()
    if not grade_name:
        return Response(
            {"detail": "grade_name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        minimum = Decimal(str(request.data.get("min_percentage")))
        maximum = Decimal(str(request.data.get("max_percentage")))
        raw_point = request.data.get("grade_point")
        grade_point = (
            Decimal(str(raw_point))
            if raw_point not in (None, "")
            else None
        )
    except (InvalidOperation, TypeError, ValueError):
        return Response(
            {"detail": "Percentage values and grade_point must be valid numbers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    values = [minimum, maximum]
    if grade_point is not None:
        values.append(grade_point)

    if (
        any(not value.is_finite() for value in values)
        or minimum < 0
        or maximum > 100
        or minimum > maximum
        or (
            grade_point is not None
            and (
                grade_point < 0
                or grade_point > scale.maximum_gpa
            )
        )
    ):
        return Response(
            {
                "detail": (
                    "Require 0 <= min_percentage <= max_percentage <= 100 "
                    "and 0 <= grade_point <= maximum_gpa."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if scale.ranges.filter(grade_name__iexact=grade_name).exists():
        return Response(
            {"detail": "This grade name already exists in the scale."},
            status=status.HTTP_409_CONFLICT,
        )

    overlap = scale.ranges.filter(
        min_percentage__lte=maximum,
        max_percentage__gte=minimum,
    ).exists()
    if overlap:
        return Response(
            {"detail": "This percentage range overlaps an existing grade range."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    item = InstitutionGradeRange.objects.create(
        grade_scale=scale,
        grade_name=grade_name,
        min_percentage=minimum,
        max_percentage=maximum,
        grade_point=grade_point,
    )

    return Response(
        {
            "id": item.id,
            "grade_name": item.grade_name,
            "min_percentage": str(item.min_percentage),
            "max_percentage": str(item.max_percentage),
            "grade_point": (
                str(item.grade_point)
                if item.grade_point is not None
                else None
            ),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_exam_publish(request, exam_id):
    """Publish or unpublish results for an institution-owned exam."""
    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        exam = InstitutionExam.objects.get(
            id=exam_id,
            institution=institution,
            academic_session__institution=institution,
            academic_level__institution=institution,
        )
    except InstitutionExam.DoesNotExist:
        return Response(
            {"detail": "Exam not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    publish = request.data.get("is_published")
    if not isinstance(publish, bool):
        return Response(
            {"detail": "is_published must be true or false."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if publish:
        if not exam.grade_scale_id:
            return Response(
                {
                    "detail": (
                        "Cannot publish: select a grade scale that covers "
                        "0.00 to 100.00 without gaps or overlaps."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from decimal import Decimal

        grade_ranges = list(
            exam.grade_scale.ranges.all().order_by(
                "min_percentage", "id"
            )
        )

        valid_coverage = (
            bool(grade_ranges)
            and grade_ranges[0].min_percentage == Decimal("0.00")
            and grade_ranges[-1].max_percentage == Decimal("100.00")
        )

        if valid_coverage:
            for index in range(1, len(grade_ranges)):
                previous = grade_ranges[index - 1]
                current = grade_ranges[index]

                if (
                    current.min_percentage
                    != previous.max_percentage + Decimal("0.01")
                ):
                    valid_coverage = False
                    break

        if not valid_coverage:
            return Response(
                {
                    "detail": (
                        "Cannot publish: the selected grade scale must "
                        "cover 0.00 to 100.00 without gaps or overlaps."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        exam_subjects = list(
            InstitutionExamSubject.objects.filter(exam=exam)
        )
        if not exam_subjects:
            return Response(
                {"detail": "Add at least one subject before publishing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrollments = StudentEnrollment.objects.filter(
            institution=institution,
            academic_session=exam.academic_session,
            status=StudentEnrollment.STATUS_RUNNING,
        )

        dynamic_enrollment_ids = StudentEnrollmentAcademicValue.objects.filter(
            academic_level=exam.academic_level,
            value__iexact=exam.academic_level.name,
            enrollment__in=enrollments,
        ).values_list("enrollment_id", flat=True)

        eligible_enrollments = enrollments.filter(
            Q(id__in=dynamic_enrollment_ids)
            | Q(class_name__iexact=exam.academic_level.name)
        )
        enrollment_ids = list(
            eligible_enrollments.values_list("id", flat=True)
        )

        if not enrollment_ids:
            return Response(
                {"detail": "No eligible students found for this exam."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        marks = InstitutionExamMark.objects.filter(
            exam_subject__in=exam_subjects,
            enrollment_id__in=enrollment_ids,
        )
        saved_marks = {
            (mark.exam_subject_id, mark.enrollment_id): mark
            for mark in marks
        }

        missing = []
        for enrollment_id in enrollment_ids:
            for exam_subject in exam_subjects:
                mark = saved_marks.get((exam_subject.id, enrollment_id))
                if mark is None or (
                    not mark.is_absent and mark.marks_obtained is None
                ):
                    missing.append({
                        "enrollment_id": enrollment_id,
                        "exam_subject_id": exam_subject.id,
                    })

        if missing:
            return Response(
                {
                    "detail": "Cannot publish: some student marks are incomplete.",
                    "incomplete_entries": len(missing),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    exam.is_published = publish
    update_fields = ["is_published", "updated_at"]

    if publish and not exam.has_been_published:
        exam.has_been_published = True
        update_fields.append("has_been_published")

    # Freeze the grading configuration on the first successful publish.
    # Keep the original snapshot when the exam is unpublished and republished.
    if publish and exam.grading_snapshot is None:
        scale = exam.grade_scale
        snapshot_ranges = scale.ranges.all().order_by("min_percentage", "id")
        exam.grading_snapshot = {
            "grade_scale_id": scale.id,
            "name": scale.name,
            "maximum_gpa": str(scale.maximum_gpa),
            "is_active": scale.is_active,
            "ranges": [
                {
                    "id": grade_range.id,
                    "grade_name": grade_range.grade_name,
                    "min_percentage": str(grade_range.min_percentage),
                    "max_percentage": str(grade_range.max_percentage),
                    "grade_point": (
                        str(grade_range.grade_point)
                        if grade_range.grade_point is not None
                        else None
                    ),
                }
                for grade_range in snapshot_ranges
            ],
        }
        update_fields.append("grading_snapshot")

    exam.save(update_fields=update_fields)

    return Response({
        "exam_id": exam.id,
        "is_published": exam.is_published,
        "detail": "Results published." if publish else "Results unpublished.",
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def institution_exam_results(request, exam_id):
    """Calculate subject-wise and overall results for an institution exam."""
    from decimal import Decimal

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        exam = InstitutionExam.objects.select_related(
            "academic_session",
            "academic_level",
            "grade_scale",
        ).get(
            id=exam_id,
            institution=institution,
            academic_session__institution=institution,
            academic_level__institution=institution,
        )
    except InstitutionExam.DoesNotExist:
        return Response(
            {"detail": "Exam not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    exam_subjects = list(
        InstitutionExamSubject.objects.filter(
            exam=exam,
        ).select_related("subject").order_by("subject__name", "id")
    )

    if not exam_subjects:
        return Response(
            {
                "exam_id": exam.id,
                "exam_name": exam.name,
                "status": "INCOMPLETE",
                "detail": "Add at least one subject before calculating results.",
                "count": 0,
                "results": [],
                "statistics": {
                    "total_students": 0,
                    "completed": 0,
                    "incomplete": 0,
                    "passed": 0,
                    "failed": 0,
                    "pass_rate": None,
                },
            }
        )

    enrollments = StudentEnrollment.objects.filter(
        institution=institution,
        academic_session=exam.academic_session,
        status=StudentEnrollment.STATUS_RUNNING,
    ).select_related("student").prefetch_related("student__profile_photos")

    department_id = request.query_params.get("department_id")
    if department_id:
        try:
            department_id = int(department_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid department_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        enrollments = enrollments.filter(department_id=department_id)

    search_query = str(request.query_params.get("search", "")).strip()
    if search_query:
        enrollments = enrollments.filter(
            Q(student__name__icontains=search_query)
            | Q(roll__icontains=search_query)
            | Q(student__global_student_id__icontains=search_query)
        )

    dynamic_enrollment_ids = StudentEnrollmentAcademicValue.objects.filter(
        academic_level=exam.academic_level,
        value__iexact=exam.academic_level.name,
        enrollment__in=enrollments,
    ).values_list("enrollment_id", flat=True)

    enrollments = list(
        enrollments.filter(
            Q(id__in=dynamic_enrollment_ids)
            | Q(class_name__iexact=exam.academic_level.name)
        ).order_by("roll", "student__name", "id")
    )

    enrollment_ids = [item.id for item in enrollments]
    subject_ids = [item.id for item in exam_subjects]

    saved_marks = {
        (mark.exam_subject_id, mark.enrollment_id): mark
        for mark in InstitutionExamMark.objects.filter(
            exam_subject_id__in=subject_ids,
            enrollment_id__in=enrollment_ids,
        )
    }

    grading_snapshot = exam.grading_snapshot
    grade_ranges = []

    if grading_snapshot and isinstance(grading_snapshot, dict):
        grade_ranges = [
            {
                "min_percentage": Decimal(item["min_percentage"]),
                "max_percentage": Decimal(item["max_percentage"]),
                "grade_name": item["grade_name"],
                "grade_point": (
                    Decimal(item["grade_point"])
                    if item.get("grade_point") is not None
                    else None
                ),
            }
            for item in grading_snapshot.get("ranges", [])
        ]
    elif exam.grade_scale and exam.grade_scale.is_active:
        grade_ranges = [
            {
                "min_percentage": grade_range.min_percentage,
                "max_percentage": grade_range.max_percentage,
                "grade_name": grade_range.grade_name,
                "grade_point": grade_range.grade_point,
            }
            for grade_range in exam.grade_scale.ranges.all().order_by(
                "min_percentage"
            )
        ]

    def grade_for_percentage(percentage):
        for grade_range in grade_ranges:
            if (
                grade_range["min_percentage"]
                <= percentage
                <= grade_range["max_percentage"]
            ):
                return {
                    "grade": grade_range["grade_name"],
                    "grade_point": (
                        str(grade_range["grade_point"])
                        if grade_range["grade_point"] is not None
                        else None
                    ),
                }
        return {"grade": None, "grade_point": None}

    results = []
    completed_count = 0
    incomplete_count = 0
    passed_count = 0
    failed_count = 0

    for enrollment in enrollments:
        subject_results = []
        total_obtained = Decimal("0")
        total_full_marks = Decimal("0")
        all_subjects_entered = True
        all_subjects_passed = True
        subject_grade_points = []
        all_grade_points_available = bool(grade_ranges)

        for exam_subject in exam_subjects:
            mark = saved_marks.get((exam_subject.id, enrollment.id))
            full_marks = exam_subject.full_marks
            pass_mark = exam_subject.pass_mark
            total_full_marks += full_marks

            if mark is None:
                all_subjects_entered = False
                subject_results.append({
                    "exam_subject_id": exam_subject.id,
                    "subject_id": exam_subject.subject_id,
                    "subject": exam_subject.subject.name,
                    "marks_obtained": None,
                    "full_marks": str(full_marks),
                    "pass_mark": str(pass_mark),
                    "percentage": None,
                    "grade": None,
                    "grade_point": None,
                    "is_absent": False,
                    "status": "INCOMPLETE",
                })
                continue

            if mark.is_absent:
                all_subjects_passed = False
                subject_results.append({
                    "exam_subject_id": exam_subject.id,
                    "subject_id": exam_subject.subject_id,
                    "subject": exam_subject.subject.name,
                    "marks_obtained": None,
                    "full_marks": str(full_marks),
                    "pass_mark": str(pass_mark),
                    "percentage": None,
                    "grade": None,
                    "grade_point": None,
                    "is_absent": True,
                    "status": "ABSENT",
                })
                continue

            obtained = mark.marks_obtained
            if obtained is None:
                all_subjects_entered = False
                subject_results.append({
                    "exam_subject_id": exam_subject.id,
                    "subject_id": exam_subject.subject_id,
                    "subject": exam_subject.subject.name,
                    "marks_obtained": None,
                    "full_marks": str(full_marks),
                    "pass_mark": str(pass_mark),
                    "percentage": None,
                    "grade": None,
                    "grade_point": None,
                    "is_absent": False,
                    "status": "INCOMPLETE",
                })
                continue

            total_obtained += obtained
            percentage = (
                obtained * Decimal("100") / full_marks
                if full_marks > 0
                else Decimal("0")
            )
            grade_data = grade_for_percentage(percentage)
            subject_passed = obtained >= pass_mark

            if not subject_passed:
                all_subjects_passed = False

            if grade_data["grade_point"] is None:
                all_grade_points_available = False
            else:
                subject_grade_points.append(
                    Decimal(grade_data["grade_point"])
                )

            subject_results.append({
                "exam_subject_id": exam_subject.id,
                "subject_id": exam_subject.subject_id,
                "subject": exam_subject.subject.name,
                "marks_obtained": str(obtained),
                "full_marks": str(full_marks),
                "pass_mark": str(pass_mark),
                "percentage": str(percentage.quantize(Decimal("0.01"))),
                "grade": grade_data["grade"],
                "grade_point": grade_data["grade_point"],
                "is_absent": False,
                "status": "PASS" if subject_passed else "FAIL",
            })

        percentage = (
            total_obtained * Decimal("100") / total_full_marks
            if total_full_marks > 0
            else Decimal("0")
        )

        if not all_subjects_entered:
            overall_status = "INCOMPLETE"
            overall_grade = None
            gpa = None
            incomplete_count += 1
        else:
            completed_count += 1
            overall_status = "PASS" if all_subjects_passed else "FAIL"

            if all_subjects_passed:
                passed_count += 1
            else:
                failed_count += 1

            overall_grade_data = grade_for_percentage(percentage)
            overall_grade = overall_grade_data["grade"]

            if (
                all_subjects_passed
                and all_grade_points_available
                and len(subject_grade_points) == len(exam_subjects)
            ):
                gpa = str(
                    (
                        sum(subject_grade_points) / Decimal(len(subject_grade_points))
                    ).quantize(Decimal("0.01"))
                )
            else:
                gpa = None

        results.append({
            "enrollment_id": enrollment.id,
            "student_name": enrollment.student.name,
            "global_student_id": enrollment.student.global_student_id,
            "profile_photo": next(
                (
                    photo.photo.url
                    for photo in enrollment.student.profile_photos.all()
                    if photo.is_current and photo.photo
                ),
                None,
            ),
            "roll": enrollment.roll,
            "class_name": enrollment.class_name,
            "section": enrollment.section,
            "total_obtained": str(total_obtained),
            "total_full_marks": str(total_full_marks),
            "percentage": (
                str(percentage.quantize(Decimal("0.01")))
                if all_subjects_entered
                else None
            ),
            "grade": overall_grade,
            "gpa": gpa,
            "status": overall_status,
            "subjects": subject_results,
        })

    # Automatic merit roll: complete results first, then fewer failed
    # subjects, higher total marks, and higher individual marks.
    def merit_sort_key(result):
        subjects = result["subjects"]
        failed_subjects = sum(
            1 for subject in subjects
            if subject.get("status") in ("FAIL", "ABSENT")
        )
        subject_marks = sorted(
            (
                Decimal(str(subject["marks_obtained"]))
                if subject.get("marks_obtained") is not None
                else Decimal("-1")
                for subject in subjects
            ),
            reverse=True,
        )
        return (
            result["status"] == "INCOMPLETE",
            failed_subjects,
            -Decimal(result["total_obtained"]),
            tuple(-mark for mark in subject_marks),
            result["enrollment_id"],
        )

    results.sort(key=merit_sort_key)
    for merit_roll, result in enumerate(results, start=1):
        result["merit_roll"] = merit_roll

    pass_rate = (
        str(
            (
                Decimal(passed_count) * Decimal("100")
                / Decimal(completed_count)
            ).quantize(Decimal("0.01"))
        )
        if completed_count
        else None
    )

    return Response({
        "exam_id": exam.id,
        "exam_name": exam.name,
        "category": exam.category,
        "academic_session_id": exam.academic_session_id,
        "academic_level_id": exam.academic_level_id,
        "grade_scale_id": (
            grading_snapshot.get("grade_scale_id")
            if grading_snapshot
            else exam.grade_scale_id
        ),
        "grade_scale": (
            grading_snapshot.get("name")
            if grading_snapshot
            else (exam.grade_scale.name if exam.grade_scale else None)
        ),
        "status": "CALCULATED",
        "count": len(results),
        "results": results,
        "statistics": {
            "total_students": len(results),
            "completed": completed_count,
            "incomplete": incomplete_count,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": pass_rate,
        },
    })


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_exam_results_send_email(request, exam_id):
    """Email published exam results to students and their guardians."""
    from django.conf import settings

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        exam = InstitutionExam.objects.get(
            id=exam_id,
            institution=institution,
            academic_session__institution=institution,
            academic_level__institution=institution,
        )
    except InstitutionExam.DoesNotExist:
        return Response(
            {"detail": "Exam not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not exam.is_published:
        return Response(
            {"detail": "Publish the exam results before sending emails."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return Response(
            {"detail": "SMTP is not configured. No emails were sent."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    department_id = request.data.get("department_id")
    params = {}

    if department_id not in (None, ""):
        try:
            department_id = int(department_id)
            if department_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid department_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        params["department_id"] = department_id

    # Reuse the existing result calculation, including its grading and merit logic.
    from rest_framework.test import APIRequestFactory, force_authenticate

    internal_request = APIRequestFactory().get(
        "/internal-results/",
        data=params,
    )
    force_authenticate(internal_request, user=request.user)
    calculated = institution_exam_results(internal_request, exam_id)

    if calculated.status_code != status.HTTP_200_OK:
        return Response(
            {"detail": "Could not calculate exam results."},
            status=calculated.status_code,
        )

    data = calculated.data
    if data.get("status") != "CALCULATED":
        return Response(
            {"detail": "Exam results are not ready to send."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    rows = data.get("results", [])
    enrollment_ids = [
        row["enrollment_id"]
        for row in rows
        if row.get("enrollment_id") is not None
    ]
    enrollments = StudentEnrollment.objects.filter(
        institution=institution,
        academic_session=exam.academic_session,
        id__in=enrollment_ids,
    ).select_related("student")
    enrollment_map = {item.id: item for item in enrollments}

    sent = 0
    skipped = 0
    failed = 0

    for row in rows:
        enrollment = enrollment_map.get(row.get("enrollment_id"))
        if enrollment is None:
            skipped += 1
            continue

        student = enrollment.student
        recipients = list(dict.fromkeys(
            address.strip().lower()
            for address in (student.email, student.guardian_email)
            if address and address.strip()
        ))

        if not recipients:
            skipped += 1
            continue

        subject_lines = [
            (
                f"- {item.get('subject', 'Subject')}: "
                f"{item.get('marks_obtained') if item.get('marks_obtained') is not None else 'Not entered'}"
                f"/{item.get('full_marks', '-')}; "
                f"Grade: {item.get('grade') or '-'}; "
                f"Status: {item.get('status', '-')}"
            )
            for item in row.get("subjects", [])
        ]

        message = "\n".join([
            f"Exam: {exam.name}",
            f"Institution: {institution.institution_name}",
            f"Student: {row.get('student_name', student.name)}",
            f"Class: {row.get('class_name', enrollment.class_name)}",
            f"Section: {row.get('section') or enrollment.section or '-'}",
            f"Roll: {row.get('roll') or enrollment.roll or '-'}",
            f"Merit Roll: {row.get('merit_roll') or '-'}",
            f"Total: {row.get('total_obtained', '-')}/{row.get('total_full_marks', '-')}",
            f"Percentage: {row.get('percentage') or '-'}%",
            f"Grade: {row.get('grade') or '-'}",
            f"GPA: {row.get('gpa') or '-'}",
            f"Overall Status: {row.get('status', '-')}",
            "",
            "Subject-wise results:",
            *subject_lines,
        ])

        for recipient in recipients:
            try:
                count = send_mail(
                    subject=f"Exam Result: {exam.name}",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                if count:
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

    return Response({
        "exam_id": exam.id,
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "detail": "Email sending process completed.",
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_grade_scale_versions(request, scale_id):
    """List immutable grading versions or save a new version when config changes."""
    from decimal import Decimal, InvalidOperation

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
        scale = InstitutionGradeScale.objects.get(
            id=scale_id,
            institution=institution,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except InstitutionGradeScale.DoesNotExist:
        return Response(
            {"detail": "Grading scale not found for this institution."},
            status=status.HTTP_404_NOT_FOUND,
        )

    def version_payload(version):
        return {
            "id": version.id,
            "version_number": version.version_number,
            "name": version.name,
            "maximum_gpa": str(version.maximum_gpa),
            "ranges": version.ranges_snapshot,
            "is_active": version.is_active,
            "created_at": version.created_at.isoformat(),
        }

    if request.method == "GET":
        versions = scale.versions.all()
        return Response({
            "active_version_id": scale.active_version_id,
            "count": versions.count(),
            "results": [version_payload(v) for v in versions],
        })

    data = request.data
    name = str(data.get("name", scale.name) or "").strip()
    if not name:
        return Response(
            {"detail": "name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        maximum_gpa = Decimal(str(data.get("maximum_gpa", scale.maximum_gpa)))
        raw_ranges = data.get("ranges")
        if not isinstance(raw_ranges, list) or not raw_ranges:
            raise ValueError("ranges must be a non-empty list")

        normalized_ranges = []
        seen_names = set()

        for item in raw_ranges:
            if not isinstance(item, dict):
                raise ValueError("Each range must be an object.")

            grade_name = str(item.get("grade_name") or "").strip()
            minimum = Decimal(str(item.get("min_percentage")))
            maximum = Decimal(str(item.get("max_percentage")))
            raw_point = item.get("grade_point")
            point = Decimal(str(raw_point)) if raw_point not in (None, "") else None

            if not grade_name:
                raise ValueError("Every range requires a grade_name.")
            if grade_name.casefold() in seen_names:
                raise ValueError("Grade names must be unique.")
            seen_names.add(grade_name.casefold())

            values = [minimum, maximum]
            if point is not None:
                values.append(point)

            if (
                any(not value.is_finite() for value in values)
                or minimum < 0
                or maximum > 100
                or minimum > maximum
                or (point is not None and (point < 0 or point > maximum_gpa))
            ):
                raise ValueError("Invalid percentage range or grade point.")

            normalized_ranges.append({
                "grade_name": grade_name,
                "min_percentage": f"{minimum:.2f}",
                "max_percentage": f"{maximum:.2f}",
                "grade_point": f"{point:.2f}" if point is not None else None,
            })

    except (InvalidOperation, TypeError, ValueError, KeyError) as exc:
        return Response(
            {"detail": str(exc) or "Invalid grading configuration."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        not maximum_gpa.is_finite()
        or maximum_gpa <= 0
        or maximum_gpa > Decimal("999.99")
    ):
        return Response(
            {"detail": "maximum_gpa must be greater than 0 and at most 999.99."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    normalized_ranges.sort(
        key=lambda item: (
            -Decimal(item["min_percentage"]),
            item["grade_name"].casefold(),
        )
    )

    for previous, current in zip(normalized_ranges, normalized_ranges[1:]):
        if Decimal(current["max_percentage"]) >= Decimal(previous["min_percentage"]):
            return Response(
                {"detail": "This percentage range overlaps another grade range."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if Decimal(normalized_ranges[-1]["min_percentage"]) != Decimal("0.00"):
        return Response(
            {"detail": "Grade ranges must start at 0.00 percent."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if Decimal(normalized_ranges[0]["max_percentage"]) != Decimal("100.00"):
        return Response(
            {"detail": "Grade ranges must end at 100.00 percent."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        scale = InstitutionGradeScale.objects.select_for_update().get(
            id=scale.id,
            institution=institution,
        )
        latest = scale.versions.order_by("-version_number").first()

        current_config = {
            "name": scale.name,
            "maximum_gpa": f"{Decimal(scale.maximum_gpa):.2f}",
            "ranges": sorted(
                [
                    {
                        "grade_name": r.grade_name,
                        "min_percentage": f"{Decimal(r.min_percentage):.2f}",
                        "max_percentage": f"{Decimal(r.max_percentage):.2f}",
                        "grade_point": (
                            f"{Decimal(r.grade_point):.2f}"
                            if r.grade_point is not None else None
                        ),
                    }
                    for r in scale.ranges.all()
                ],
                key=lambda item: (
                    -Decimal(item["min_percentage"]),
                    item["grade_name"].casefold(),
                ),
            ),
        }
        requested_config = {
            "name": name,
            "maximum_gpa": f"{maximum_gpa:.2f}",
            "ranges": normalized_ranges,
        }

        if current_config == requested_config and latest is not None:
            version = latest
            created = False
        else:
            version = InstitutionGradeScaleVersion.objects.create(
                grade_scale=scale,
                version_number=(latest.version_number + 1) if latest else 1,
                name=name,
                maximum_gpa=maximum_gpa,
                ranges_snapshot=normalized_ranges,
                is_active=True,
            )
            scale.versions.exclude(id=version.id).update(is_active=False)

            scale.name = name
            scale.maximum_gpa = maximum_gpa
            scale.active_version = version
            scale.save(update_fields=[
                "name", "maximum_gpa", "active_version", "updated_at"
            ])

            scale.ranges.all().delete()
            InstitutionGradeRange.objects.bulk_create([
                InstitutionGradeRange(
                    grade_scale=scale,
                    grade_name=item["grade_name"],
                    min_percentage=Decimal(item["min_percentage"]),
                    max_percentage=Decimal(item["max_percentage"]),
                    grade_point=(
                        Decimal(item["grade_point"])
                        if item["grade_point"] is not None else None
                    ),
                )
                for item in normalized_ranges
            ])
            created = True

    return Response(
        {
            "created": created,
            "active_version_id": scale.active_version_id,
            "version": version_payload(version),
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_grade_scale_activate_version(request, scale_id, version_id):
    """Activate a saved grading version and restore its ranges atomically."""
    from decimal import Decimal

    try:
        institution = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
        scale = InstitutionGradeScale.objects.get(
            id=scale_id,
            institution=institution,
        )
        version = InstitutionGradeScaleVersion.objects.get(
            id=version_id,
            grade_scale=scale,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except (
        InstitutionGradeScale.DoesNotExist,
        InstitutionGradeScaleVersion.DoesNotExist,
    ):
        return Response(
            {"detail": "Grading scale or version not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    with transaction.atomic():
        scale = InstitutionGradeScale.objects.select_for_update().get(
            id=scale.id,
            institution=institution,
        )
        version = InstitutionGradeScaleVersion.objects.get(
            id=version.id,
            grade_scale=scale,
        )

        scale.versions.exclude(id=version.id).update(is_active=False)
        version.is_active = True
        version.save(update_fields=["is_active"])

        scale.name = version.name
        scale.maximum_gpa = version.maximum_gpa
        scale.active_version = version
        scale.save(update_fields=[
            "name", "maximum_gpa", "active_version", "updated_at"
        ])

        scale.ranges.all().delete()
        InstitutionGradeRange.objects.bulk_create([
            InstitutionGradeRange(
                grade_scale=scale,
                grade_name=item["grade_name"],
                min_percentage=Decimal(item["min_percentage"]),
                max_percentage=Decimal(item["max_percentage"]),
                grade_point=(
                    Decimal(item["grade_point"])
                    if item.get("grade_point") is not None else None
                ),
            )
            for item in version.ranges_snapshot
        ])

    return Response({
        "detail": "Grading version activated.",
        "active_version_id": version.id,
        "version_number": version.version_number,
        "name": version.name,
        "maximum_gpa": str(version.maximum_gpa),
        "ranges": version.ranges_snapshot,
    })
