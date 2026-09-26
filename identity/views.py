import json
import secrets

from datetime import date, timedelta
from core.services.image_processor import process_image
from core.models import ColleagueSetting
from notifications.services import create_notification

from django.http.multipartparser import (
    MultiPartParser,
    MultiPartParserError,
)

from django.http import JsonResponse
from django.db import models, transaction
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from category_engine.models import Category
from companies.models import Country

from .permissions import (

    get_authenticated_identity,

    get_authenticated_personal_account,

    is_owner,

    permission_denied,

    require_authentication,

)

from .models import (
    AcademicBackground,
    AccountType,
    Connection,
    Colleague,
    Follow,
    Hobby,
    JobExperience,
    Language,
    Skill,
    PersonalAccount,
    PersonalContact,
    PersonalHighestAcademicBackground,
    PersonalLanguage,
    PersonalRunningProfession,
    PersonalHobby,
    PersonalInterestedCategory,
    PersonalResponsibility,
    PasswordResetOTP,
    ProfessionalAccount,
    SocialMediaPlatform,
    UserIdentity,
    UserSocialMedia,
)

from .serializers import (
    ForgotPasswordSerializer,
    InstitutionSignupSerializer,
    LoginSerializer,
    PersonalResponsibilitySerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    VerifyOTPSerializer,
)


@csrf_exempt
def follow_create(request, following_id):
    if request.method != "POST":
        return JsonResponse(
            {"detail": "Method not allowed."},
            status=405,
        )

    follower = get_authenticated_identity(request)

    if follower is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    if follower.id == following_id:
        return JsonResponse(
            {
                "success": False,
                "detail": "You cannot follow yourself.",
            },
            status=400,
        )

    try:
        following = UserIdentity.objects.get(id=following_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "User not found."},
            status=404,
        )

    follow, created = Follow.objects.get_or_create(
        follower=follower,
        following=following,
    )

    return JsonResponse(
        {
            "success": True,
            "status": "following",
            "created": created,
            "follow_id": follow.id,
        },
        status=201 if created else 200,
    )



def follow_status(request, target_id):
    if request.method != "GET":
        return JsonResponse(
            {"detail": "Method not allowed."},
            status=405,
        )

    viewer = get_authenticated_identity(request)

    if viewer is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        target = UserIdentity.objects.get(id=target_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "User not found."},
            status=404,
        )

    is_following = Follow.objects.filter(
        follower=viewer,
        following=target,
    ).exists()

    return JsonResponse(
        {
            "success": True,
            "status": "self"
            if viewer.id == target.id
            else "following"
            if is_following
            else "not_following",
            "is_following": is_following,
            "followers_count": Follow.objects.filter(
                following=target,
            ).count(),
            "following_count": Follow.objects.filter(
                follower=target,
            ).count(),
        },
        status=200,
    )

@csrf_exempt

def followers_list(request, target_id):
    if request.method != "GET":
        return JsonResponse(
            {"detail": "Method not allowed."},
            status=405,
        )

    viewer = get_authenticated_identity(request)

    if viewer is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        target = UserIdentity.objects.get(id=target_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "User not found."},
            status=404,
        )

    follows = (
        Follow.objects
        .filter(following=target)
        .select_related("follower")
    )

    return JsonResponse(
        {
            "success": True,
            "count": follows.count(),
            "followers": [
                serialize_identity(follow.follower)
                for follow in follows
            ],
        },
        status=200,
    )


def following_list(request, target_id):
    if request.method != "GET":
        return JsonResponse(
            {"detail": "Method not allowed."},
            status=405,
        )

    viewer = get_authenticated_identity(request)

    if viewer is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        target = UserIdentity.objects.get(id=target_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "User not found."},
            status=404,
        )

    follows = (
        Follow.objects
        .filter(follower=target)
        .select_related("following")
    )

    return JsonResponse(
        {
            "success": True,
            "count": follows.count(),
            "following": [
                serialize_identity(follow.following)
                for follow in follows
            ],
        },
        status=200,
    )

@csrf_exempt
def follow_remove(request, following_id):
    if request.method != "DELETE":
        return JsonResponse(
            {"detail": "Method not allowed."},
            status=405,
        )

    follower = get_authenticated_identity(request)

    if follower is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    deleted, _ = Follow.objects.filter(
        follower=follower,
        following_id=following_id,
    ).delete()

    if deleted == 0:
        return JsonResponse(
            {
                "success": True,
                "status": "not_following",
                "already_removed": True,
            },
            status=200,
        )

    return JsonResponse(
        {
            "success": True,
            "status": "not_following",
        },
        status=200,
    )

@csrf_exempt
def colleague_request_create(request, receiver_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    sender = get_authenticated_identity(request)

    if sender is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    settings = ColleagueSetting.objects.first()

    if settings is None or not settings.is_enabled:
        return JsonResponse(
            {"detail": "Colleague feature is currently disabled."},
            status=403,
        )

    try:
        receiver = UserIdentity.objects.get(id=receiver_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "User not found."},
            status=404,
        )

    if sender.id == receiver.id:
        return JsonResponse(
            {"detail": "You cannot add yourself as a colleague."},
            status=400,
        )

    existing = Colleague.objects.filter(
        sender=sender,
        receiver=receiver,
    ).first()

    if existing is not None:
        if existing.request_status == Colleague.RequestStatus.PENDING:
            return JsonResponse(
                {
                    "success": True,
                    "status": "pending",
                    "already_pending": True,
                    "colleague_id": existing.id,
                },
                status=200,
            )

        if existing.request_status == Colleague.RequestStatus.ACCEPTED:
            return JsonResponse(
                {
                    "success": True,
                    "status": "accepted",
                    "already_colleague": True,
                    "colleague_id": existing.id,
                },
                status=200,
            )

        if existing.request_status == Colleague.RequestStatus.DECLINED:
            existing.request_status = Colleague.RequestStatus.PENDING
            existing.status = Colleague.Status.RUNNING
            existing.save(
                update_fields=[
                    "request_status",
                    "status",
                    "updated_at",
                ]
            )

            create_notification(
                user=receiver,
                category="system",
                notification_type="colleague_request",
                title="New colleague request",
                message=(
                    f"{sender.first_name} {sender.last_name} "
                    "sent you a colleague request."
                ).strip(),
                source="colleague",
                action_url="/connections",
                priority="normal",
            )

            return JsonResponse(
                {
                    "success": True,
                    "status": existing.request_status,
                    "colleague_id": existing.id,
                    "resent": True,
                },
                status=200,
            )

    reverse = Colleague.objects.filter(
        sender=receiver,
        receiver=sender,
    ).first()

    if reverse is not None:
        if reverse.request_status == Colleague.RequestStatus.PENDING:
            return JsonResponse(
                {
                    "success": False,
                    "detail": "This user has already sent you a colleague request.",
                    "status": "pending_received",
                    "colleague_id": reverse.id,
                },
                status=409,
            )

        if reverse.request_status == Colleague.RequestStatus.ACCEPTED:
            return JsonResponse(
                {
                    "success": True,
                    "status": "accepted",
                    "already_colleague": True,
                    "colleague_id": reverse.id,
                },
                status=200,
            )

    colleague = Colleague.objects.create(
        sender=sender,
        receiver=receiver,
        request_status=Colleague.RequestStatus.PENDING,
    )

    create_notification(
        user=receiver,
        category="system",
        notification_type="colleague_request",
        title="New colleague request",
        message=(
            f"{sender.first_name} {sender.last_name} "
            "sent you a colleague request."
        ).strip(),
        source="colleague",
        action_url="/connections",
        priority="normal",
    )

    return JsonResponse(
        {
            "success": True,
            "status": colleague.request_status,
            "colleague_id": colleague.id,
        },
        status=201,
    )


@csrf_exempt
def colleague_status_update(request, colleague_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    current_user = get_authenticated_identity(request)

    if current_user is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    settings = ColleagueSetting.objects.first()

    if settings is None or not settings.is_enabled:
        return JsonResponse(
            {"detail": "Colleague feature is currently disabled."},
            status=403,
        )

    if not settings.allow_status_change:
        return JsonResponse(
            {"detail": "Colleague status changes are currently disabled."},
            status=403,
        )

    try:
        colleague = Colleague.objects.get(
            id=colleague_id,
            request_status=Colleague.RequestStatus.ACCEPTED,
        )
    except Colleague.DoesNotExist:
        return JsonResponse(
            {"detail": "Accepted colleague relationship not found."},
            status=404,
        )

    if current_user.id not in (colleague.sender_id, colleague.receiver_id):
        return JsonResponse(
            {"detail": "You are not part of this colleague relationship."},
            status=403,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON body."},
            status=400,
        )

    new_status = data.get("status")

    if new_status not in (
        Colleague.Status.RUNNING,
        Colleague.Status.PREVIOUS,
    ):
        return JsonResponse(
            {
                "detail": "Invalid status.",
                "allowed_statuses": [
                    Colleague.Status.RUNNING,
                    Colleague.Status.PREVIOUS,
                ],
            },
            status=400,
        )

    if (
        new_status == Colleague.Status.RUNNING
        and not settings.running_status_enabled
    ):
        return JsonResponse(
            {"detail": "Running colleague status is currently disabled."},
            status=403,
        )

    if (
        new_status == Colleague.Status.PREVIOUS
        and not settings.previous_status_enabled
    ):
        return JsonResponse(
            {"detail": "Previous colleague status is currently disabled."},
            status=403,
        )

    if colleague.status == new_status:
        return JsonResponse(
            {
                "success": True,
                "status": colleague.status,
                "colleague_id": colleague.id,
                "changed": False,
            },
            status=200,
        )

    colleague.status = new_status
    colleague.save(update_fields=["status", "updated_at"])

    other_user = (
        colleague.receiver
        if colleague.sender_id == current_user.id
        else colleague.sender
    )

    create_notification(
        user=other_user,
        category="system",
        notification_type="colleague_status_changed",
        title="Colleague status updated",
        message=(
            f"{current_user.first_name} {current_user.last_name} "
            f"changed your colleague relationship to "
            f"{colleague.get_status_display()}."
        ).strip(),
        source="colleague",
        action_url="/connections",
        priority="normal",
    )

    return JsonResponse(
        {
            "success": True,
            "status": colleague.status,
            "colleague_id": colleague.id,
            "changed": True,
        },
        status=200,
    )


@csrf_exempt
def colleague_request_cancel(request, colleague_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    current_user = get_authenticated_identity(request)

    if current_user is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    settings = ColleagueSetting.objects.first()

    if settings is None or not settings.is_enabled:
        return JsonResponse(
            {"detail": "Colleague feature is currently disabled."},
            status=403,
        )

    try:
        colleague = Colleague.objects.get(
            id=colleague_id,
            sender=current_user,
            request_status=Colleague.RequestStatus.PENDING,
        )
    except Colleague.DoesNotExist:
        return JsonResponse(
            {"detail": "Pending colleague request not found."},
            status=404,
        )

    colleague.delete()

    return JsonResponse(
        {
            "success": True,
            "status": "cancelled",
            "colleague_id": colleague_id,
        },
        status=200,
    )


@csrf_exempt
def colleague_request_decline(request, colleague_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    current_user = get_authenticated_identity(request)

    if current_user is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    settings = ColleagueSetting.objects.first()

    if settings is None or not settings.is_enabled:
        return JsonResponse(
            {"detail": "Colleague feature is currently disabled."},
            status=403,
        )

    try:
        colleague = Colleague.objects.select_related(
            "sender",
            "receiver",
        ).get(
            id=colleague_id,
            receiver=current_user,
            request_status=Colleague.RequestStatus.PENDING,
        )
    except Colleague.DoesNotExist:
        return JsonResponse(
            {"detail": "Pending colleague request not found."},
            status=404,
        )

    colleague.request_status = Colleague.RequestStatus.DECLINED
    colleague.save(update_fields=["request_status", "updated_at"])

    sender = colleague.sender

    create_notification(
        user=sender,
        category="system",
        notification_type="colleague_request_declined",
        title="Colleague request declined",
        message=(
            f"{current_user.first_name} {current_user.last_name} "
            "declined your colleague request."
        ).strip(),
        source="colleague",
        action_url="/connections",
        priority="normal",
    )

    return JsonResponse(
        {
            "success": True,
            "status": colleague.request_status,
            "colleague_id": colleague.id,
        },
        status=200,
    )


@csrf_exempt
def colleague_request_accept(request, colleague_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    current_user = get_authenticated_identity(request)

    if current_user is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    settings = ColleagueSetting.objects.first()

    if settings is None or not settings.is_enabled:
        return JsonResponse(
            {"detail": "Colleague feature is currently disabled."},
            status=403,
        )

    try:
        colleague = Colleague.objects.select_related(
            "sender",
            "receiver",
        ).get(
            id=colleague_id,
            receiver=current_user,
            request_status=Colleague.RequestStatus.PENDING,
        )
    except Colleague.DoesNotExist:
        return JsonResponse(
            {"detail": "Pending colleague request not found."},
            status=404,
        )

    colleague.request_status = Colleague.RequestStatus.ACCEPTED
    colleague.status = Colleague.Status.RUNNING
    colleague.save(update_fields=["request_status", "status", "updated_at"])

    sender = colleague.sender

    create_notification(
        user=sender,
        category="system",
        notification_type="colleague_request_accepted",
        title="Colleague request accepted",
        message=(
            f"{current_user.first_name} {current_user.last_name} "
            "accepted your colleague request."
        ).strip(),
        source="colleague",
        action_url="/connections",
        priority="normal",
    )

    return JsonResponse(
        {
            "success": True,
            "status": colleague.request_status,
            "colleague_status": colleague.status,
            "colleague_id": colleague.id,
        },
        status=200,
    )


@csrf_exempt
def profile_colleague_list(request, username):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    settings = ColleagueSetting.objects.first()

    if settings is None or not settings.is_enabled:
        return JsonResponse(
            {"detail": "Colleague feature is currently disabled."},
            status=403,
        )

    try:
        profile_user = UserIdentity.objects.get(
            username=username,
            is_active=True,
        )
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Profile user not found."},
            status=404,
        )

    accepted_colleagues = Colleague.objects.filter(
        models.Q(sender=profile_user) | models.Q(receiver=profile_user),
        request_status=Colleague.RequestStatus.ACCEPTED,
    ).select_related("sender", "receiver")

    def serialize_profile_colleague(colleague):
        other_user = (
            colleague.receiver
            if colleague.sender_id == profile_user.id
            else colleague.sender
        )

        return {
            "colleague_id": colleague.id,
            "user_id": other_user.id,
            "username": other_user.username,
            "first_name": other_user.first_name,
            "last_name": other_user.last_name,
            "status": colleague.status,
            "request_status": colleague.request_status,
            "request_type": "colleague",
            "created_at": colleague.created_at.isoformat(),
            "updated_at": colleague.updated_at.isoformat(),
        }

    all_colleagues = [
        serialize_profile_colleague(colleague)
        for colleague in accepted_colleagues
    ]

    running_colleagues = [
        item
        for item in all_colleagues
        if item["status"] == Colleague.Status.RUNNING
    ]

    previous_colleagues = [
        item
        for item in all_colleagues
        if item["status"] == Colleague.Status.PREVIOUS
    ]

    return JsonResponse(
        {
            "success": True,
            "profile": {
                "id": profile_user.id,
                "username": profile_user.username,
            },
            "all_colleagues": all_colleagues,
            "running_colleagues": running_colleagues,
            "previous_colleagues": previous_colleagues,
        },
        status=200,
    )


def colleague_list(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    current_user = get_authenticated_identity(request)

    if current_user is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    settings = ColleagueSetting.objects.first()

    if settings is None or not settings.is_enabled:
        return JsonResponse(
            {"detail": "Colleague feature is currently disabled."},
            status=403,
        )

    received_requests = Colleague.objects.filter(
        receiver=current_user,
        request_status=Colleague.RequestStatus.PENDING,
    )

    sent_requests = Colleague.objects.filter(
        sender=current_user,
        request_status=Colleague.RequestStatus.PENDING,
    )

    accepted_colleagues = Colleague.objects.filter(
        models.Q(sender=current_user) | models.Q(receiver=current_user),
        request_status=Colleague.RequestStatus.ACCEPTED,
    )

    def serialize_colleague(colleague, request_type):
        other_user = (
            colleague.receiver
            if colleague.sender_id == current_user.id
            else colleague.sender
        )

        return {
            "colleague_id": colleague.id,
            "user_id": other_user.id,
            "username": other_user.username,
            "first_name": other_user.first_name,
            "last_name": other_user.last_name,
            "status": colleague.status,
            "request_status": colleague.request_status,
            "request_type": request_type,
            "created_at": colleague.created_at.isoformat(),
            "updated_at": colleague.updated_at.isoformat(),
        }

    all_colleagues = [
        serialize_colleague(colleague, "colleague")
        for colleague in accepted_colleagues
    ]

    running_colleagues = [
        item for item in all_colleagues
        if item["status"] == Colleague.Status.RUNNING
    ]

    previous_colleagues = [
        item for item in all_colleagues
        if item["status"] == Colleague.Status.PREVIOUS
    ]

    return JsonResponse(
        {
            "success": True,
            "all_colleagues": all_colleagues,
            "running_colleagues": running_colleagues,
            "previous_colleagues": previous_colleagues,
            "received_requests": [
                serialize_colleague(colleague, "received")
                for colleague in received_requests
            ],
            "sent_requests": [
                serialize_colleague(colleague, "sent")
                for colleague in sent_requests
            ],
        },
        status=200,
    )


@csrf_exempt
def connection_request_create(request, receiver_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    sender = get_authenticated_identity(request)

    if sender is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        receiver = UserIdentity.objects.get(id=receiver_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "User not found."},
            status=404,
        )

    if sender.id == receiver.id:
        return JsonResponse(
            {"detail": "You cannot send a connection request to yourself."},
            status=400,
        )

    existing = Connection.objects.filter(
        sender=sender,
        receiver=receiver,
    ).first()

    if existing is not None:
        if existing.status == Connection.Status.PENDING:
            return JsonResponse(
                {"success": True, "status": "pending", "already_pending": True},
                status=200,
            )

        if existing.status == Connection.Status.ACCEPTED:
            return JsonResponse(
                {"success": True, "status": "accepted", "already_connected": True},
                status=200,
            )

        if existing.status == Connection.Status.BLOCKED:
            return JsonResponse(
                {"success": False, "detail": "Connection is blocked."},
                status=403,
            )

    reverse = Connection.objects.filter(
        sender=receiver,
        receiver=sender,
    ).first()

    if reverse is not None:
        if reverse.status == Connection.Status.PENDING:
            return JsonResponse(
                {
                    "success": False,
                    "detail": "This user has already sent you a connection request.",
                    "status": "pending_received",
                },
                status=409,
            )

        if reverse.status == Connection.Status.ACCEPTED:
            return JsonResponse(
                {"success": True, "status": "accepted", "already_connected": True},
                status=200,
            )

        if reverse.status == Connection.Status.BLOCKED:
            return JsonResponse(
                {"success": False, "detail": "Connection is blocked."},
                status=403,
            )

    connection = Connection.objects.create(
        sender=sender,
        receiver=receiver,
        status=Connection.Status.PENDING,
    )

    return JsonResponse(
        {
            "success": True,
            "status": connection.status,
            "connection_id": connection.id,
        },
        status=201,
    )


@csrf_exempt
def connection_list(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    current_user = get_authenticated_identity(request)

    if current_user is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    connections = Connection.objects.filter(
        models.Q(sender=current_user, status=Connection.Status.ACCEPTED)
        | models.Q(receiver=current_user, status=Connection.Status.ACCEPTED)
    )

    received_requests = Connection.objects.filter(
        receiver=current_user,
        status=Connection.Status.PENDING,
    )

    sent_requests = Connection.objects.filter(
        sender=current_user,
        status=Connection.Status.PENDING,
    )

    def serialize_connection(connection, request_type):
        other_user = (
            connection.receiver
            if connection.sender_id == current_user.id
            else connection.sender
        )

        return {
            "connection_id": connection.id,
            "user_id": other_user.id,
            "username": other_user.username,
            "first_name": other_user.first_name,
            "last_name": other_user.last_name,
            "status": connection.status,
            "request_type": request_type,
            "created_at": connection.created_at.isoformat(),
        }

    return JsonResponse(
        {
            "success": True,
            "connections": [
                serialize_connection(connection, "connected")
                for connection in connections
            ],
            "received_requests": [
                serialize_connection(connection, "received")
                for connection in received_requests
            ],
            "sent_requests": [
                serialize_connection(connection, "sent")
                for connection in sent_requests
            ],
        },
        status=200,
    )



@csrf_exempt
def profile_connection_list(request, username):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    try:
        profile_user = UserIdentity.objects.get(
            username=username,
            is_active=True,
        )
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Profile user not found."},
            status=404,
        )

    connections = Connection.objects.filter(
        models.Q(sender=profile_user, status=Connection.Status.ACCEPTED)
        | models.Q(receiver=profile_user, status=Connection.Status.ACCEPTED)
    )

    def serialize_connection(connection):
        other_user = (
            connection.receiver
            if connection.sender_id == profile_user.id
            else connection.sender
        )

        return {
            "connection_id": connection.id,
            "user_id": other_user.id,
            "username": other_user.username,
            "first_name": other_user.first_name,
            "last_name": other_user.last_name,
            "status": connection.status,
            "request_type": "connected",
            "created_at": connection.created_at.isoformat(),
        }

    return JsonResponse(
        {
            "success": True,
            "profile": {
                "id": profile_user.id,
                "username": profile_user.username,
            },
            "connections": [
                serialize_connection(connection)
                for connection in connections
            ],
        },
        status=200,
    )

def connection_status(request, target_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    current_user = get_authenticated_identity(request)

    if current_user is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    if current_user.id == target_id:
        return JsonResponse(
            {
                "success": True,
                "status": "self",
                "connection_id": None,
            },
            status=200,
        )

    connection = Connection.objects.filter(
        sender=current_user,
        receiver_id=target_id,
    ).first()

    if connection is not None:
        if connection.status == Connection.Status.PENDING:
            return JsonResponse(
                {
                    "success": True,
                    "status": "pending_sent",
                    "connection_id": connection.id,
                },
                status=200,
            )

        if connection.status == Connection.Status.ACCEPTED:
            return JsonResponse(
                {
                    "success": True,
                    "status": "connected",
                    "connection_id": connection.id,
                },
                status=200,
            )

        return JsonResponse(
            {
                "success": True,
                "status": connection.status,
                "connection_id": connection.id,
            },
            status=200,
        )

    reverse = Connection.objects.filter(
        sender_id=target_id,
        receiver=current_user,
    ).first()

    if reverse is not None:
        if reverse.status == Connection.Status.PENDING:
            return JsonResponse(
                {
                    "success": True,
                    "status": "pending_received",
                    "connection_id": reverse.id,
                },
                status=200,
            )

        if reverse.status == Connection.Status.ACCEPTED:
            return JsonResponse(
                {
                    "success": True,
                    "status": "connected",
                    "connection_id": reverse.id,
                },
                status=200,
            )

        return JsonResponse(
            {
                "success": True,
                "status": reverse.status,
                "connection_id": reverse.id,
            },
            status=200,
        )

    return JsonResponse(
        {
            "success": True,
            "status": "none",
            "connection_id": None,
        },
        status=200,
    )


@csrf_exempt
def connection_request_cancel(request, connection_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    sender = get_authenticated_identity(request)

    if sender is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        connection = Connection.objects.get(id=connection_id)
    except Connection.DoesNotExist:
        return JsonResponse(
            {"detail": "Connection request not found."},
            status=404,
        )

    if connection.sender_id != sender.id:
        return JsonResponse(
            {"detail": "You are not allowed to cancel this request."},
            status=403,
        )

    if connection.status != Connection.Status.PENDING:
        return JsonResponse(
            {
                "success": False,
                "detail": "Only pending connection requests can be cancelled.",
                "status": connection.status,
            },
            status=409,
        )

    connection.delete()

    return JsonResponse(
        {
            "success": True,
            "status": "cancelled",
            "connection_id": connection_id,
        },
        status=200,
    )


@csrf_exempt
def connection_request_decline(request, connection_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    receiver = get_authenticated_identity(request)

    if receiver is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        connection = Connection.objects.get(id=connection_id)
    except Connection.DoesNotExist:
        return JsonResponse(
            {"detail": "Connection request not found."},
            status=404,
        )

    if connection.receiver_id != receiver.id:
        return JsonResponse(
            {"detail": "You are not allowed to decline this request."},
            status=403,
        )

    if connection.status == Connection.Status.DECLINED:
        return JsonResponse(
            {
                "success": True,
                "status": Connection.Status.DECLINED,
                "already_declined": True,
                "connection_id": connection.id,
            },
            status=200,
        )

    if connection.status != Connection.Status.PENDING:
        return JsonResponse(
            {
                "success": False,
                "detail": "Only pending connection requests can be declined.",
                "status": connection.status,
            },
            status=409,
        )

    connection.status = Connection.Status.DECLINED
    connection.save(update_fields=["status", "updated_at"])

    return JsonResponse(
        {
            "success": True,
            "status": connection.status,
            "connection_id": connection.id,
        },
        status=200,
    )


@csrf_exempt
def connection_request_accept(request, connection_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    receiver = get_authenticated_identity(request)

    if receiver is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        connection = Connection.objects.get(id=connection_id)
    except Connection.DoesNotExist:
        return JsonResponse(
            {"detail": "Connection request not found."},
            status=404,
        )

    if connection.receiver_id != receiver.id:
        return JsonResponse(
            {"detail": "You are not allowed to accept this request."},
            status=403,
        )

    if connection.status == Connection.Status.ACCEPTED:
        return JsonResponse(
            {
                "success": True,
                "status": Connection.Status.ACCEPTED,
                "already_accepted": True,
                "connection_id": connection.id,
            },
            status=200,
        )

    if connection.status != Connection.Status.PENDING:
        return JsonResponse(
            {
                "success": False,
                "detail": "Only pending connection requests can be accepted.",
                "status": connection.status,
            },
            status=409,
        )

    connection.status = Connection.Status.ACCEPTED
    connection.save(update_fields=["status", "updated_at"])

    return JsonResponse(
        {
            "success": True,
            "status": connection.status,
            "connection_id": connection.id,
        },
        status=200,
    )


def get_authenticated_personal_account(
    request,
    identity_id,
):
    authenticated_identity = (
        get_authenticated_identity(request)
    )

    if authenticated_identity is None:
        return None, JsonResponse(
            {
                "detail":
                "Authentication credentials were not provided."
            },
            status=401,
        )

    try:
        personal_account = PersonalAccount.objects.get(
            identity_id=identity_id
        )
    except PersonalAccount.DoesNotExist:
        return None, JsonResponse(
            {
                "detail":
                "Personal account not found."
            },
            status=404,
        )

    if (
        personal_account.identity_id
        != authenticated_identity.id
    ):
        return None, JsonResponse(
            {
                "detail":
                "You do not have permission to modify this personal account."
            },
            status=403,
        )

    return personal_account, None

def get_authenticated_personal_account_by_id(
    request,
    personal_account_id,
):
    authenticated_identity = (
        get_authenticated_identity(
            request
        )
    )

    if authenticated_identity is None:
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "Authentication credentials were not provided."
                },
                status=401,
            ),
        )

    try:
        personal_account = (
            PersonalAccount.objects.get(
                id=personal_account_id
            )
        )

    except PersonalAccount.DoesNotExist:
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "Personal account not found."
                },
                status=404,
            ),
        )

    if (
        personal_account.identity_id
        != authenticated_identity.id
    ):
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "You do not have permission to modify this account."
                },
                status=403,
            ),
        )

    return (
        personal_account,
        None,
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

        "background_color":
        personal_account.background_color,

        "background_image": (
            personal_account.background_image.url
            if personal_account.background_image
            else None
        ),

        "tab_colors":
        personal_account.tab_colors,

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
def identity_search(request):
    query = request.GET.get("q", "").strip()

    if not query:
        return JsonResponse({
            "count": 0,
            "results": [],
        })

    identities = (
        UserIdentity.objects
        .filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
        .filter(is_active=True)
        .order_by("username", "id")[:20]
    )

    results = [
        serialize_identity(identity)
        for identity in identities
        if identity.username
    ]

    return JsonResponse({
        "count": len(results),
        "results": results,
    })


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
@require_authentication
def identity_update(request, identity_id):
    try:
        identity = UserIdentity.objects.get(id=identity_id)
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Identity not found."},
            status=404,
        )

    if not is_owner(
        request.authenticated_identity,
        identity.id,
    ):
        return permission_denied(
            "You do not have permission to update this identity."
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
@require_authentication
def identity_delete(request, identity_id):
    try:
        identity = UserIdentity.objects.get(
            id=identity_id
        )
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {"detail": "Identity not found."},
            status=404,
        )

    if not is_owner(
        request.authenticated_identity,
        identity.id,
    ):
        return permission_denied(
            "You do not have permission to delete this identity."
        )

    identity.delete()

    return JsonResponse(
        {
            "detail":
            "Identity deleted successfully."
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
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

        if not is_owner(
            request.authenticated_identity,
            identity.id,
        ):
            return permission_denied(
                "You do not have permission to create an account type for this identity."
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

        requested_primary = bool(data.get("is_primary", False))
        is_active = bool(data.get("is_active", True))

        with transaction.atomic():
            has_primary = AccountType.objects.filter(
                identity=identity,
                is_active=True,
                is_primary=True,
            ).exists()

            is_primary = requested_primary or not has_primary

            if is_primary:
                AccountType.objects.filter(
                    identity=identity,
                    is_primary=True,
                ).update(is_primary=False)

            account = AccountType.objects.create(
                identity=identity,
                account_type=account_type,
                is_primary=is_primary,
                is_active=is_active,
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


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def account_type_switch(request):
    try:
        data = json.loads(request.body or "{}")
        identity_id = data.get("identity_id")
        account_type = data.get("account_type")

        if not identity_id:
            return JsonResponse({"detail": "identity_id is required."}, status=400)

        if not account_type:
            return JsonResponse({"detail": "account_type is required."}, status=400)

        if not any(value == account_type for value, _ in AccountType.Type.choices):
            return JsonResponse({"detail": "Invalid account_type."}, status=400)

        try:
            identity = UserIdentity.objects.get(id=identity_id)
        except UserIdentity.DoesNotExist:
            return JsonResponse({"detail": "Identity not found."}, status=404)

        if not is_owner(request.authenticated_identity, identity.id):
            return permission_denied(
                "You do not have permission to switch the account type for this identity."
            )

        try:
            account = AccountType.objects.get(
                identity=identity,
                account_type=account_type,
                is_active=True,
            )
        except AccountType.DoesNotExist:
            return JsonResponse(
                {"detail": "Active account type not found."},
                status=404,
            )

        with transaction.atomic():
            AccountType.objects.filter(
                identity=identity,
                is_primary=True,
            ).update(is_primary=False)

            account.is_primary = True
            account.save(update_fields=["is_primary", "updated_at"])

        return JsonResponse(serialize_account_type(account))

    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)


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
@require_authentication
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

        if not is_owner(
            request.authenticated_identity,
            identity.id,
        ):
            return permission_denied(
                "You do not have permission to create a personal account for this identity."
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
def public_personal_account_by_username(
    request,
    username,
):
    try:

        personal_account = (
            PersonalAccount.objects.get(
                username=username
            )
        )

    except PersonalAccount.DoesNotExist:

        return JsonResponse(
            {
                "detail":
                    "Personal account not found."
            },
            status=404,
        )

    return JsonResponse(
        serialize_personal_account(
            personal_account
        )
    )


@require_http_methods(["GET"])
def public_personal_experiences_by_username(
    request,
    username,
):
    try:

        personal_account = (
            PersonalAccount.objects.get(
                username=username
            )
        )

    except PersonalAccount.DoesNotExist:

        return JsonResponse(
            {
                "detail":
                    "Personal account not found."
            },
            status=404,
        )

    experiences = JobExperience.objects.filter(
        personal_account=personal_account,
        is_active=True,
    ).order_by(
        "display_order",
        "-start_date",
    )

    results = [
        serialize_personal_job_experience(
            experience
        )
        for experience in experiences
    ]

    return JsonResponse(
        {
            "personal_account_id":
                personal_account.id,
            "count":
                len(results),
            "results":
                results,
        }
    )


@require_http_methods(["GET"])
@require_authentication
def personal_account_detail(request, identity_id):

    authenticated_identity = (
        request.authenticated_identity
    )

    if authenticated_identity.id != identity_id:

        return JsonResponse(
            {
                "detail":
                    "You do not have permission to view this account."
            },
            status=403,
        )

    try:

        personal_account = (
            PersonalAccount.objects.get(
                identity_id=authenticated_identity.id
            )
        )

    except PersonalAccount.DoesNotExist:

        return JsonResponse(
            {
                "detail":
                    "Personal account not found."
            },
            status=404,
        )

    return JsonResponse(
        serialize_personal_account(
            personal_account
        )
    )

@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_authentication
def personal_contact_list_create(request, personal_account_id):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

    if request.method == "GET":
        contacts = PersonalContact.objects.filter(
            personal_account=personal_account
        ).order_by(
            "-is_primary",
            "contact_type",
            "created_at",
        )

        return JsonResponse(
            {
                "results": [
                    {
                        "id": contact.id,
                        "contact_type": contact.contact_type,
                        "value": contact.value,
                        "is_primary": contact.is_primary,
                        "is_verified": contact.is_verified,
                    }
                    for contact in contacts
                ]
            }
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    contact_type = data.get("contact_type", "").strip().lower()
    value = data.get("value", "").strip()

    if contact_type not in (
        PersonalContact.ContactType.EMAIL,
        PersonalContact.ContactType.PHONE,
    ):
        return JsonResponse(
            {"detail": "Invalid contact type."},
            status=400,
        )

    if not value:
        return JsonResponse(
            {"detail": "Contact value cannot be empty."},
            status=400,
        )

    normalized_value = value.lower() if contact_type == "email" else (
        "".join(value.split())
    )

    if PersonalContact.objects.filter(
        contact_type=contact_type,
        normalized_value=normalized_value,
    ).exists():
        return JsonResponse(
            {"detail": "This contact is already in use."},
            status=400,
        )

    identity_field = "email" if contact_type == "email" else "mobile_number"

    identity_filter = {
        identity_field: normalized_value,
    }

    if UserIdentity.objects.filter(
        **identity_filter
    ).exclude(
        id=personal_account.identity_id
    ).exists():
        return JsonResponse(
            {"detail": "This contact is already in use."},
            status=400,
        )

    current_identity_value = getattr(
        personal_account.identity,
        identity_field,
        "",
    )

    current_identity_normalized = (
        current_identity_value.lower()
        if contact_type == "email" and current_identity_value
        else "".join(current_identity_value.split())
        if current_identity_value
        else ""
    )

    if (
        current_identity_normalized
        and current_identity_normalized == normalized_value
    ):
        return JsonResponse(
            {"detail": "This contact is already in use."},
            status=400,
        )

    is_primary = bool(data.get("is_primary", False))

    with transaction.atomic():
        if is_primary:
            PersonalContact.objects.filter(
                personal_account=personal_account,
                contact_type=contact_type,
                is_primary=True,
            ).update(is_primary=False)

        contact = PersonalContact.objects.create(
            personal_account=personal_account,
            contact_type=contact_type,
            value=value,
            normalized_value=normalized_value,
            is_primary=is_primary,
        )

        identity = personal_account.identity

        if is_primary and contact_type == "email":
            identity.email = value
            identity.save(update_fields=["email"])

        if is_primary and contact_type == "phone":
            identity.mobile_number = value
            identity.save(update_fields=["mobile_number"])

    return JsonResponse(
        {
            "id": contact.id,
            "contact_type": contact.contact_type,
            "value": contact.value,
            "is_primary": contact.is_primary,
            "is_verified": contact.is_verified,
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
@require_authentication
def personal_contact_update_delete(request, personal_account_id, contact_id):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

    try:
        contact = PersonalContact.objects.get(
            id=contact_id,
            personal_account=personal_account,
        )
    except PersonalContact.DoesNotExist:
        return JsonResponse(
            {"detail": "Contact not found."},
            status=404,
        )

    if request.method == "DELETE":
        was_primary = contact.is_primary
        contact_type = contact.contact_type

        with transaction.atomic():
            contact.delete()

            if was_primary:
                identity = personal_account.identity

                if contact_type == "email":
                    replacement = (
                        PersonalContact.objects
                        .filter(
                            personal_account=personal_account,
                            contact_type="email",
                        )
                        .order_by("created_at")
                        .first()
                    )

                    if replacement:
                        replacement.is_primary = True
                        replacement.save(update_fields=["is_primary"])
                        identity.email = replacement.value
                    else:
                        identity.email = ""

                    identity.save(update_fields=["email"])

                elif contact_type == "phone":
                    replacement = (
                        PersonalContact.objects
                        .filter(
                            personal_account=personal_account,
                            contact_type="phone",
                        )
                        .order_by("created_at")
                        .first()
                    )

                    if replacement:
                        replacement.is_primary = True
                        replacement.save(update_fields=["is_primary"])
                        identity.mobile_number = replacement.value
                    else:
                        identity.mobile_number = ""

                    identity.save(update_fields=["mobile_number"])

        return JsonResponse(
            {"detail": "Contact deleted successfully."}
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    if "value" in data:
        value = data.get("value", "").strip()

        if not value:
            return JsonResponse(
                {"detail": "Contact value cannot be empty."},
                status=400,
            )

        normalized_value = (
            value.lower()
            if contact.contact_type == "email"
            else "".join(value.split())
        )

        if PersonalContact.objects.filter(
            contact_type=contact.contact_type,
            normalized_value=normalized_value,
        ).exclude(id=contact.id).exists():
            return JsonResponse(
                {"detail": "This contact is already in use."},
                status=400,
            )

        contact.value = value
        contact.normalized_value = normalized_value

    if "is_primary" in data:
        is_primary = bool(data.get("is_primary"))

        with transaction.atomic():
            if is_primary:
                PersonalContact.objects.filter(
                    personal_account=personal_account,
                    contact_type=contact.contact_type,
                    is_primary=True,
                ).exclude(id=contact.id).update(
                    is_primary=False
                )

            contact.is_primary = is_primary
            contact.save()

            identity = personal_account.identity

            if contact.contact_type == "email":
                if is_primary:
                    identity.email = contact.value
                elif identity.email == contact.value:
                    replacement = (
                        PersonalContact.objects
                        .filter(
                            personal_account=personal_account,
                            contact_type="email",
                            is_primary=True,
                        )
                        .exclude(id=contact.id)
                        .first()
                    )
                    identity.email = replacement.value if replacement else ""
                identity.save(update_fields=["email"])

            elif contact.contact_type == "phone":
                if is_primary:
                    identity.mobile_number = contact.value
                elif identity.mobile_number == contact.value:
                    replacement = (
                        PersonalContact.objects
                        .filter(
                            personal_account=personal_account,
                            contact_type="phone",
                            is_primary=True,
                        )
                        .exclude(id=contact.id)
                        .first()
                    )
                    identity.mobile_number = replacement.value if replacement else ""
                identity.save(update_fields=["mobile_number"])

    else:
        contact.save()

        if contact.is_primary:
            identity = personal_account.identity
            if contact.contact_type == "email":
                identity.email = contact.value
                identity.save(update_fields=["email"])
            elif contact.contact_type == "phone":
                identity.mobile_number = contact.value
                identity.save(update_fields=["mobile_number"])

    return JsonResponse(
        {
            "id": contact.id,
            "contact_type": contact.contact_type,
            "value": contact.value,
            "is_primary": contact.is_primary,
            "is_verified": contact.is_verified,
        }
    )


@csrf_exempt
@require_http_methods(["PATCH"])
@require_authentication
def personal_account_update(request, identity_id):
    personal_account, error_response = (
        get_authenticated_personal_account(
            request,
            identity_id,
        )
    )

    if error_response is not None:
        return error_response

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    identity = personal_account.identity

    if "first_name" in data:
        identity.first_name = data["first_name"]

    if "last_name" in data:
        identity.last_name = data["last_name"]

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
            personal_username_exists = (
                PersonalAccount.objects
                .filter(username=username)
                .exclude(id=personal_account.id)
                .exists()
            )

            identity_username_exists = (
                UserIdentity.objects
                .filter(username=username)
                .exclude(id=identity.id)
                .exists()
            )

            if personal_username_exists or identity_username_exists:
                return JsonResponse(
                    {"detail": "This username already exists."},
                    status=400,
                )

            identity.username = username

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
            if not Country.objects.filter(
                id=present_country_id,
                is_active=True,
            ).exists():
                return JsonResponse(
                    {"detail": "Selected country is not available."},
                    status=400,
                )

            personal_account.present_country_id = (
                present_country_id
            )
        else:
            personal_account.present_country = None

    identity.save()
    personal_account.save()

    return JsonResponse(
        serialize_personal_account(personal_account)
    )


@csrf_exempt
@require_http_methods(["PATCH"])
@require_authentication
def personal_background_color_update(
    request,
    identity_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account(
            request,
            identity_id,
        )
    )

    if error_response is not None:
        return error_response

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

    background_color = data.get(
        "background_color"
    )

    if not background_color:
        return JsonResponse(
            {
                "detail":
                "background_color is required."
            },
            status=400,
        )

    if not isinstance(
        background_color,
        str,
    ):
        return JsonResponse(
            {
                "detail":
                "background_color must be a string."
            },
            status=400,
        )

    if not background_color.startswith("#"):
        return JsonResponse(
            {
                "detail":
                "background_color must be a valid hex color."
            },
            status=400,
        )

    if len(background_color) not in (
        4,
        7,
    ):
        return JsonResponse(
            {
                "detail":
                "background_color must be a valid hex color."
            },
            status=400,
        )

    hex_value = background_color[1:]

    if not all(
        character in "0123456789abcdefABCDEF"
        for character in hex_value
    ):
        return JsonResponse(
            {
                "detail":
                "background_color must be a valid hex color."
            },
            status=400,
        )

    personal_account.background_color = (
        background_color.upper()
    )

    personal_account.background_image = None

    personal_account.save(
        update_fields=[
            "background_color",
            "background_image",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "id": personal_account.id,
            "identity_id":
            personal_account.identity_id,
            "background_color":
            personal_account.background_color,
        }
    )

@csrf_exempt
@require_http_methods(["PATCH"])
@require_authentication
def personal_tab_colors_update(
    request,
    identity_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account(
            request,
            identity_id,
        )
    )

    if error_response is not None:
        return error_response

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

    tab_colors = data.get(
        "tab_colors"
    )

    if tab_colors is None:
        return JsonResponse(
            {
                "detail":
                "tab_colors is required."
            },
            status=400,
        )

    if not isinstance(
        tab_colors,
        dict,
    ):
        return JsonResponse(
            {
                "detail":
                "tab_colors must be an object."
            },
            status=400,
        )

    personal_account.tab_colors = tab_colors

    personal_account.save(
        update_fields=[
            "tab_colors",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "id": personal_account.id,
            "identity_id":
            personal_account.identity_id,
            "tab_colors":
            personal_account.tab_colors,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def personal_account_photos_update(request, identity_id):
    personal_account, error_response = (
        get_authenticated_personal_account(
            request,
            identity_id,
        )
    )

    if error_response is not None:
        return error_response

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


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def personal_background_image_update(
    request,
    identity_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account(
            request,
            identity_id,
        )
    )

    if error_response is not None:
        return error_response

    if "background_image" not in request.FILES:
        return JsonResponse(
            {
                "detail":
                "background_image is required."
            },
            status=400,
        )

    old_background_image = None

    try:
        processed_background_image = process_image(
            request.FILES["background_image"],
            preset="background",
        )
    except ValueError as error:
        return JsonResponse(
            {
                "detail": str(error)
            },
            status=400,
        )

    if personal_account.background_image:
        old_background_image = (
            personal_account.background_image.name
        )

    personal_account.background_image = (
        processed_background_image
    )

    personal_account.save()

    if old_background_image:
        personal_account.background_image.storage.delete(
            old_background_image
        )

    return JsonResponse(
        serialize_personal_account(
            personal_account
        )
    )

@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def professional_background_image_update(
    request,
    identity_id,
):
    if not is_owner(
        request.authenticated_identity,
        identity_id,
    ):
        return permission_denied(
            "You do not have permission to update "
            "this professional account background image."
        )

    try:
        identity = UserIdentity.objects.get(
            id=identity_id
        )

        professional_account = (
            identity.professional_account
        )

    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {
                "detail": "Identity not found."
            },
            status=404,
        )

    except ProfessionalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Professional account not found."
            },
            status=404,
        )

    if "background_image" not in request.FILES:
        return JsonResponse(
            {
                "detail":
                "background_image is required."
            },
            status=400,
        )

    old_background_image = None

    try:
        processed_background_image = process_image(
            request.FILES["background_image"],
            preset="background",
        )
    except ValueError as error:
        return JsonResponse(
            {
                "detail": str(error)
            },
            status=400,
        )

    if professional_account.background_image:
        old_background_image = (
            professional_account.background_image.name
        )

    professional_account.background_image = (
        processed_background_image
    )

    professional_account.save()

    if old_background_image:
        professional_account.background_image.storage.delete(
            old_background_image
        )

    return JsonResponse(
        serialize_professional_account(
            professional_account
        )
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
        "background_image": (
            professional_account.background_image.url
            if professional_account.background_image
            else None
        ),
        "tab_colors": professional_account.tab_colors,
        "is_active": professional_account.is_active,
        "created_at": professional_account.created_at.isoformat(),
        "updated_at": professional_account.updated_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def professional_account_create(request):
    try:
        data = json.loads(request.body or "{}")

        identity_id = data.get("identity_id")

        if not identity_id:
            return JsonResponse(
                {"detail": "identity_id is required."},
                status=400,
            )

        if not is_owner(
            request.authenticated_identity,
            identity_id,
        ):
            return permission_denied(
                "You do not have permission to create this professional account."
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
@require_authentication
def professional_background_color_update(
    request,
    identity_id,
):
    if not is_owner(
        request.authenticated_identity,
        identity_id,
    ):
        return permission_denied(
            "You do not have permission to update "
            "this professional account background color."
        )

    try:
        identity = UserIdentity.objects.get(
            id=identity_id
        )

        professional_account = (
            identity.professional_account
        )

    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {
                "detail": "Identity not found."
            },
            status=404,
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

    background_color = data.get(
        "background_color"
    )

    if not background_color:
        return JsonResponse(
            {
                "detail":
                "background_color is required."
            },
            status=400,
        )

    if not isinstance(
        background_color,
        str,
    ):
        return JsonResponse(
            {
                "detail":
                "background_color must be a string."
            },
            status=400,
        )

    if not background_color.startswith("#"):
        return JsonResponse(
            {
                "detail":
                "background_color must be a valid hex color."
            },
            status=400,
        )

    if len(background_color) not in (
        4,
        7,
    ):
        return JsonResponse(
            {
                "detail":
                "background_color must be a valid hex color."
            },
            status=400,
        )

    hex_value = background_color[1:]

    if not all(
        character in "0123456789abcdefABCDEF"
        for character in hex_value
    ):
        return JsonResponse(
            {
                "detail":
                "background_color must be a valid hex color."
            },
            status=400,
        )

    professional_account.background_color = (
        background_color.upper()
    )

    professional_account.save(
        update_fields=[
            "background_color",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "id": professional_account.id,
            "identity_id":
            professional_account.identity_id,
            "background_color":
            professional_account.background_color,
        }
    )


@csrf_exempt
@require_http_methods(["PATCH"])
@require_authentication
def professional_tab_colors_update(
    request,
    identity_id,
):
    if not is_owner(
        request.authenticated_identity,
        identity_id,
    ):
        return permission_denied(
            "You do not have permission to update "
            "this professional account tab colors."
        )

    try:
        identity = UserIdentity.objects.get(
            id=identity_id
        )

        professional_account = (
            identity.professional_account
        )

    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {
                "detail": "Identity not found."
            },
            status=404,
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

    tab_colors = data.get(
        "tab_colors"
    )

    if tab_colors is None:
        return JsonResponse(
            {
                "detail":
                "tab_colors is required."
            },
            status=400,
        )

    if not isinstance(
        tab_colors,
        dict,
    ):
        return JsonResponse(
            {
                "detail":
                "tab_colors must be an object."
            },
            status=400,
        )

    professional_account.tab_colors = (
        tab_colors
    )

    professional_account.save(
        update_fields=[
            "tab_colors",
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "id": professional_account.id,
            "identity_id":
            professional_account.identity_id,
            "tab_colors":
            professional_account.tab_colors,
        }
    )


@csrf_exempt
@require_http_methods(["PATCH"])
@require_authentication
def professional_account_update(request, identity_id):
    if not is_owner(
        request.authenticated_identity,
        identity_id,
    ):
        return permission_denied(
            "You do not have permission to update this professional account."
        )

    try:
        identity = UserIdentity.objects.get(
            id=identity_id
        )

        professional_account = (
            identity.professional_account
        )

    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Identity not found."
            },
            status=404,
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
        data = json.loads(
            request.body or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail":
                "Invalid JSON."
            },
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

@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def personal_running_profession_selection(request, personal_account_id):
    if request.method == "GET":
        try:
            personal_account = PersonalAccount.objects.get(id=personal_account_id)
        except PersonalAccount.DoesNotExist:
            return JsonResponse({"detail": "Personal account not found."}, status=404)


        selections = (
            PersonalRunningProfession.objects
            .filter(personal_account=personal_account)
            .select_related("job_experience")
            .order_by("created_at")
        )

        return JsonResponse({
            "personal_account_id": personal_account.id,
            "job_experience_ids": [
                selection.job_experience_id
                for selection in selections
            ],
            "results": [
                serialize_personal_job_experience(
                    selection.job_experience
                )
                for selection in selections
            ],
        })

    personal_account, error_response = get_authenticated_personal_account_by_id(request, personal_account_id)
    if error_response is not None:
        return error_response

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    job_experience_ids = data.get("job_experience_ids")

    if not isinstance(job_experience_ids, list):
        return JsonResponse(
            {"detail": "job_experience_ids must be an array."},
            status=400,
        )

    try:
        job_experience_ids = [
            int(value)
            for value in job_experience_ids
        ]
    except (TypeError, ValueError):
        return JsonResponse(
            {"detail": "Invalid job experience ID."},
            status=400,
        )

    job_experiences = JobExperience.objects.filter(
        id__in=job_experience_ids,
        personal_account=personal_account,
        is_active=True,
    )

    if job_experiences.count() != len(set(job_experience_ids)):
        return JsonResponse(
            {
                "detail":
                "One or more selected job experiences are not available."
            },
            status=400,
        )

    with transaction.atomic():
        PersonalRunningProfession.objects.filter(
            personal_account=personal_account
        ).delete()

        PersonalRunningProfession.objects.bulk_create([
            PersonalRunningProfession(
                personal_account=personal_account,
                job_experience=job_experience,
            )
            for job_experience in job_experiences
        ])

    selections = (
        PersonalRunningProfession.objects
        .filter(personal_account=personal_account)
        .select_related("job_experience")
        .order_by("created_at")
    )

    return JsonResponse({
        "personal_account_id": personal_account.id,
        "job_experience_ids": [
            selection.job_experience_id
            for selection in selections
        ],
        "results": [
            serialize_personal_job_experience(
                selection.job_experience
            )
            for selection in selections
        ],
    })


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def personal_highest_academic_selection(request, personal_account_id):
    if request.method == "GET":
        try:
            personal_account = PersonalAccount.objects.get(id=personal_account_id)
        except PersonalAccount.DoesNotExist:
            return JsonResponse({"detail": "Personal account not found."}, status=404)


        try:
            selection = (
                PersonalHighestAcademicBackground.objects
                .select_related("academic_background")
                .get(personal_account=personal_account)
            )
        except PersonalHighestAcademicBackground.DoesNotExist:
            return JsonResponse({
                "personal_account_id": personal_account.id,
                "academic_background_id": None,
                "result": None,
            })

        return JsonResponse({
            "personal_account_id": personal_account.id,
            "academic_background_id": (
                selection.academic_background_id
            ),
            "result": serialize_academic_background(
                selection.academic_background
            ),
        })

    personal_account, error_response = get_authenticated_personal_account_by_id(request, personal_account_id)
    if error_response is not None:
        return error_response

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    academic_background_id = data.get("academic_background_id")

    if academic_background_id in (None, ""):
        PersonalHighestAcademicBackground.objects.filter(
            personal_account=personal_account
        ).delete()

        return JsonResponse({
            "personal_account_id": personal_account.id,
            "academic_background_id": None,
            "result": None,
        })

    try:
        academic_background_id = int(academic_background_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"detail": "Invalid academic background ID."},
            status=400,
        )

    try:
        academic_background = AcademicBackground.objects.get(
            id=academic_background_id,
            personal_account=personal_account,
        )
    except AcademicBackground.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Selected academic background is not available."
            },
            status=400,
        )

    selection, _ = (
        PersonalHighestAcademicBackground.objects.update_or_create(
            personal_account=personal_account,
            defaults={
                "academic_background": academic_background,
            },
        )
    )

    return JsonResponse({
        "personal_account_id": personal_account.id,
        "academic_background_id": selection.academic_background_id,
        "result": serialize_academic_background(
            selection.academic_background
        ),
    })


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
@require_authentication
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

    if not is_owner(
        request.authenticated_identity,
        personal_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to add an academic background to this personal account."
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
@require_authentication
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

    if not is_owner(
        request.authenticated_identity,
        academic.personal_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to update this academic background."
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
@require_authentication
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

    if not is_owner(
        request.authenticated_identity,
        academic.personal_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to delete this academic background."
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


def serialize_personal_job_experience(experience):
    return {
        "id": experience.id,
        "personal_account_id": (
            experience.personal_account_id
        ),
        "company": experience.company,
        "job_title": experience.job_title,
        "employment_type": experience.employment_type,
        "location": experience.location,
        "start_date": (
            experience.start_date.isoformat()
            if experience.start_date
            else None
        ),
        "end_date": (
            experience.end_date.isoformat()
            if experience.end_date
            else None
        ),
        "is_current": experience.is_current,
        "description": experience.description,
        "display_order": experience.display_order,
        "is_active": experience.is_active,
        "created_at": (
            experience.created_at.isoformat()
        ),
        "updated_at": (
            experience.updated_at.isoformat()
        ),
    }


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
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

        if not is_owner(
            request.authenticated_identity,
            professional_account.identity_id,
        ):
            return permission_denied(
                "You do not have permission to create job experience for this professional account."
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


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def personal_job_experience_create(
    request,
    personal_account_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

    try:
        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail":
                "Invalid JSON."
            },
            status=400,
        )

    try:
        start_date = data.get(
            "start_date"
        )

        end_date = data.get(
            "end_date"
        )

        if start_date:
            start_date = date.fromisoformat(
                start_date
            )

        else:
            start_date = None

        if end_date:
            end_date = date.fromisoformat(
                end_date
            )

        else:
            end_date = None

    except (TypeError, ValueError):
        return JsonResponse(
            {
                "detail":
                "Invalid date format. Use YYYY-MM-DD."
            },
            status=400,
        )

    experience = JobExperience.objects.create(
        personal_account=personal_account,

        company=data.get(
            "company",
            "",
        ),

        job_title=data.get(
            "job_title",
            "",
        ),

        employment_type=data.get(
            "employment_type",
            "",
        ),

        location=data.get(
            "location",
            "",
        ),

        start_date=start_date,

        end_date=end_date,

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
        serialize_personal_job_experience(
            experience
        ),
        status=201,
    )


@require_http_methods(["GET"])
@require_authentication
def personal_job_experience_list(
    request,
    personal_account_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

    experiences = JobExperience.objects.filter(
        personal_account=personal_account,
        is_active=True,
    ).order_by(
        "display_order",
        "-start_date",
    )

    results = [
        serialize_personal_job_experience(
            experience
        )
        for experience in experiences
    ]

    return JsonResponse(
        {
            "personal_account_id":
            personal_account.id,
            "count": len(results),
            "results": results,
        }
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

# ============================================================
# PERSONAL RESPONSIBILITIES
# ============================================================

@require_http_methods(["GET"])
def public_personal_responsibilities_by_username(request, username):
    try:
        personal_account = PersonalAccount.objects.get(username=username)
    except PersonalAccount.DoesNotExist:
        return JsonResponse({"detail": "Personal account not found."}, status=404)

    responsibilities = PersonalResponsibility.objects.filter(
        personal_account=personal_account,
        is_active=True,
    ).order_by("display_order", "id")

    results = PersonalResponsibilitySerializer(
        responsibilities,
        many=True,
    ).data

    return JsonResponse({
        "personal_account_id": personal_account.id,
        "count": len(results),
        "results": results,
    })


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def personal_responsibility_create(
    request,
    personal_account_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

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

    title = data.get(
        "title",
        "",
    ).strip()

    if not title:
        return JsonResponse(
            {
                "detail":
                "Responsibility title is required."
            },
            status=400,
        )

    responsibility = PersonalResponsibility.objects.create(
        personal_account=personal_account,
        title=title,
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
        PersonalResponsibilitySerializer(
            responsibility
        ).data,
        status=201,
    )


@require_http_methods(["GET"])
@require_authentication
def personal_responsibility_list(
    request,
    personal_account_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

    responsibilities = (
        PersonalResponsibility.objects.filter(
            personal_account=personal_account,
            is_active=True,
        ).order_by(
            "display_order",
            "id",
        )
    )

    results = PersonalResponsibilitySerializer(
        responsibilities,
        many=True,
    ).data

    return JsonResponse(
        {
            "personal_account_id":
            personal_account.id,
            "count":
            len(results),
            "results":
            results,
        }
    )


@csrf_exempt
@require_http_methods(["PATCH"])
@require_authentication
def personal_responsibility_update(
    request,
    personal_account_id,
    responsibility_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

    try:
        responsibility = PersonalResponsibility.objects.get(
            id=responsibility_id,
            personal_account=personal_account,
        )
    except PersonalResponsibility.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Responsibility not found."
            },
            status=404,
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

    if "title" in data:
        title = data.get(
            "title",
            "",
        ).strip()

        if not title:
            return JsonResponse(
                {
                    "detail":
                    "Responsibility title is required."
                },
                status=400,
            )

        responsibility.title = title

    if "description" in data:
        responsibility.description = data.get(
            "description",
            "",
        )

    if "display_order" in data:
        responsibility.display_order = data.get(
            "display_order",
            0,
        )

    if "is_active" in data:
        responsibility.is_active = data.get(
            "is_active",
            True,
        )

    responsibility.save()

    return JsonResponse(
        PersonalResponsibilitySerializer(
            responsibility
        ).data
    )


@csrf_exempt
@require_http_methods(["DELETE"])
@require_authentication
def personal_responsibility_delete(
    request,
    personal_account_id,
    responsibility_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

    try:
        responsibility = PersonalResponsibility.objects.get(
            id=responsibility_id,
            personal_account=personal_account,
        )
    except PersonalResponsibility.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Responsibility not found."
            },
            status=404,
        )

    responsibility.delete()

    return JsonResponse(
        {
            "detail":
            "Responsibility deleted successfully."
        }
    )


@csrf_exempt
@require_http_methods(["PATCH"])
@require_authentication
def personal_job_experience_update(
    request,
    personal_account_id,
    experience_id,
):
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

    if not experience.personal_account:
        return JsonResponse(
            {
                "detail":
                "This job experience is not linked to a personal account."
            },
            status=400,
        )

    if not is_owner(
        request.authenticated_identity,
        experience.personal_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to update this job experience."
        )

    try:
        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail":
                "Invalid JSON."
            },
            status=400,
        )

    try:
        if "start_date" in data:

            start_date = data.get(
                "start_date"
            )

            experience.start_date = (
                date.fromisoformat(start_date)
                if start_date
                else None
            )


        if "end_date" in data:

            end_date = data.get(
                "end_date"
            )

            experience.end_date = (
                date.fromisoformat(end_date)
                if end_date
                else None
            )

    except (TypeError, ValueError):

        return JsonResponse(
            {
                "detail":
                "Invalid date format. Use YYYY-MM-DD."
            },
            status=400,
        )


    fields = [
        "company",
        "job_title",
        "employment_type",
        "location",
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
                data.get(field),
            )


    if experience.is_current:

        experience.end_date = None


    experience.save()


    return JsonResponse(
        serialize_personal_job_experience(
            experience
        )
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
@require_authentication
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

    if not is_owner(
        request.authenticated_identity,
        experience.professional_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to update this job experience."
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
@require_authentication
def personal_job_experience_delete(
    request,
    personal_account_id,
    experience_id,
):
    try:
        experience = JobExperience.objects.get(
            id=experience_id,
            personal_account_id=personal_account_id,
        )

    except JobExperience.DoesNotExist:

        return JsonResponse(
            {
                "detail":
                "Job experience not found."
            },
            status=404,
        )

    if not experience.personal_account:
        return JsonResponse(
            {
                "detail":
                "This job experience is not linked to a personal account."
            },
            status=400,
        )

    if not is_owner(
        request.authenticated_identity,
        experience.personal_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to delete this job experience."
        )

    experience.delete()

    return JsonResponse(
        {
            "detail":
            "Job experience deleted successfully."
        }
    )    


@csrf_exempt
@require_http_methods(["DELETE"])
@require_authentication
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

    if not is_owner(
        request.authenticated_identity,
        experience.professional_account.identity_id,
    ):
        return permission_denied(
            "You do not have permission to delete this job experience."
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


# Languages

@csrf_exempt
@require_http_methods(["GET", "POST"])
def languages(request, personal_account_id):

    if request.method == "GET":
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

    personal_account, error_response = (
        get_authenticated_personal_account(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

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

    if proficiency not in dict(
        PersonalLanguage.Proficiency.choices
    ):
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


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def language_detail(request, language_id):
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

    authenticated_identity = get_authenticated_identity(
        request
    )

    if authenticated_identity is None:
        return JsonResponse(
            {
                "detail":
                "Authentication credentials were not provided."
            },
            status=401,
        )

    if (
        personal_language.personal_account.identity_id
        != authenticated_identity.id
    ):
        return JsonResponse(
            {
                "detail":
                "You do not have permission to modify this language."
            },
            status=403,
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
def institution_signup(request):
    try:
        data = json.loads(request.body or "{}")
        serializer = InstitutionSignupSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({"errors": serializer.errors}, status=400)
        from institution.models import (
            InstitutionProfile,
            InstitutionType,
            InstitutionAuthority,
        )
        from companies.models import Country, AdministrativeLocation
        validated = serializer.validated_data
        institution_types = InstitutionType.objects.filter(
            id__in=validated["institution_type_ids"],
            is_active=True,
        ).order_by("id")

        if not institution_types.exists():
            return JsonResponse(
                {"errors": {"institution_type_ids": ["Invalid institution types."]}},
                status=400,
            )

        country = Country.objects.get(
            id=validated["country_id"],
            is_active=True,
        )

        affiliation_ids = validated.get("affiliation_ids", [])

        authorities = InstitutionAuthority.objects.filter(
            id__in=affiliation_ids,
            country=country,
            is_active=True,
        ).prefetch_related("institution_types")

        valid_type_ids = set(
            institution_types.values_list("id", flat=True)
        )

        invalid_authorities = []

        for authority in authorities:
            authority_type_ids = set(
                authority.institution_types.values_list("id", flat=True)
            )

            if not authority_type_ids.intersection(valid_type_ids):
                invalid_authorities.append(authority.id)

        if invalid_authorities:
            return JsonResponse(
                {
                    "errors": {
                        "affiliation_ids": [
                            "One or more selected authorities are not valid for the selected institution type."
                        ]
                    }
                },
                status=400,
            )

        if len(authorities) != len(set(affiliation_ids)):
            return JsonResponse(
                {
                    "errors": {
                        "affiliation_ids": [
                            "One or more selected authorities are invalid or inactive."
                        ]
                    }
                },
                status=400,
            )
        administrative_location = None
        location_id = validated.get("administrative_location_id")
        if location_id:
            administrative_location = AdministrativeLocation.objects.filter(location_id=location_id, country=country, is_active=True).first()
            if administrative_location is None:
                return JsonResponse({"errors": {"administrative_location_id": ["Invalid administrative location."]}}, status=400)
        password = validated.pop("password")
        with transaction.atomic():
            identity = UserIdentity.objects.create(first_name=validated.get("first_name", ""), last_name=validated.get("last_name", ""), username=validated["username"], email=validated["email"], mobile_number=validated["mobile_number"])
            identity.set_password(password)
            identity.save()
            AccountType.objects.create(identity=identity, account_type=AccountType.Type.INSTITUTION, is_primary=True, is_active=True)
            institution_profile = InstitutionProfile.objects.create(
                identity=identity,
                institution_name=validated["institution_name"],
                institution_type=institution_types.first(),
                established_year=validated.get("established_year"),
                management_type=validated.get("management_type", ""),
                mpo_status=validated.get("mpo_status", ""),
                tagline=validated.get("tagline", ""),
                description=validated.get("description", ""),
                country=country,
                administrative_location=administrative_location,
                full_address=validated.get("full_address", ""),
                website=validated.get("website", ""),
                email=validated["email"],
                phone=validated.get("phone", "") or validated["mobile_number"],
            )

            institution_profile.institution_types.set(institution_types)
            institution_profile.affiliations.set(authorities)
        refresh = RefreshToken.for_user(identity)
        return JsonResponse({"message": "Institution account created successfully.", "access": str(refresh.access_token), "refresh": str(refresh), "user": serialize_identity(identity), "account_type": "institution"}, status=201)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

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

        refresh = RefreshToken.for_user(identity)

        return JsonResponse(
            {
                "message": "Login successful.",

                "access": str(refresh.access_token),

                "refresh": str(refresh),

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

        refresh = RefreshToken.for_user(identity)

        return JsonResponse(
            {
                "message": "Login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
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
def logout(request):
    try:
        data = json.loads(request.body or "{}")
        refresh_token = data.get("refresh")

        if not refresh_token:
            return JsonResponse({"detail": "Refresh token is required."}, status=400)

        token = RefreshToken(refresh_token)
        token.blacklist()

        return JsonResponse({"message": "Logout successful."}, status=200)

    except Exception:
        return JsonResponse({"detail": "Invalid or expired refresh token."}, status=400)


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

@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def user_social_media_create(request):
    identity = get_authenticated_identity(request)

    if identity is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    platform_id = data.get("platform_id")
    username = data.get("username", "").strip()

    if not platform_id:
        return JsonResponse(
            {"detail": "Platform is required."},
            status=400,
        )

    if not username:
        return JsonResponse(
            {"detail": "Username is required."},
            status=400,
        )

    try:
        platform = SocialMediaPlatform.objects.get(
            id=platform_id,
            is_active=True,
        )
    except SocialMediaPlatform.DoesNotExist:
        return JsonResponse(
            {"detail": "Social media platform not found or inactive."},
            status=404,
        )

    if UserSocialMedia.objects.filter(
        identity=identity,
        platform=platform,
    ).exists():
        return JsonResponse(
            {"detail": "This social media platform is already added."},
            status=400,
        )

    social_media = UserSocialMedia.objects.create(
        identity=identity,
        platform=platform,
        username=username,
    )

    return JsonResponse(
        {
            "id": social_media.id,
            "platform_id": platform.id,
            "platform_name": platform.name,
            "platform_slug": platform.slug,
            "icon": platform.icon.url if platform.icon else None,
            "username": social_media.username,
            "url": social_media.url,
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
@require_authentication
def user_social_media_delete(request, social_media_id):
    identity = get_authenticated_identity(request)

    if identity is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        social_media = UserSocialMedia.objects.get(
            id=social_media_id,
            identity=identity,
        )
    except UserSocialMedia.DoesNotExist:
        return JsonResponse(
            {"detail": "Social media link not found."},
            status=404,
        )

    if request.method == "PATCH":
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse(
                {"detail": "Invalid JSON."},
                status=400,
            )

        username = data.get("username", "").strip()

        if not username:
            return JsonResponse(
                {"detail": "Username is required."},
                status=400,
            )

        social_media.username = username
        social_media.save()

        return JsonResponse(
            {
                "id": social_media.id,
                "platform_id": social_media.platform_id,
                "platform_name": social_media.platform.name,
                "platform_slug": social_media.platform.slug,
                "icon": social_media.platform.icon.url if social_media.platform.icon else None,
                "username": social_media.username,
                "url": social_media.url,
            }
        )

    identity = get_authenticated_identity(request)

    if identity is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    try:
        social_media = UserSocialMedia.objects.get(
            id=social_media_id,
            identity=identity,
        )
    except UserSocialMedia.DoesNotExist:
        return JsonResponse(
            {"detail": "Social media link not found."},
            status=404,
        )

    social_media.delete()

    return JsonResponse(
        {"detail": "Social media link removed successfully."}
    )


@require_http_methods(["GET"])
def user_social_media_list(request):
    identity = get_authenticated_identity(request)
    target_personal_account_id = request.GET.get("personal_account_id")

    if target_personal_account_id:
        try:
            target_personal_account = PersonalAccount.objects.get(id=target_personal_account_id)
        except PersonalAccount.DoesNotExist:
            return JsonResponse({"detail": "Personal account not found."}, status=404)
        identity = target_personal_account.identity

    elif identity is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    social_media = UserSocialMedia.objects.select_related(
        "platform"
    ).filter(
        identity=identity,
        platform__is_active=True,
    ).order_by(
        "platform__display_order",
        "platform__name",
    )

    results = [
        {
            "id": item.id,
            "platform_id": item.platform_id,
            "platform_name": item.platform.name,
            "platform_slug": item.platform.slug,
            "icon": item.platform.icon.url if item.platform.icon else None,
            "username": item.username,
            "url": item.url,
        }
        for item in social_media
    ]

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        }
    )


@require_http_methods(["GET"])
def social_media_platform_list(request):
    platforms = SocialMediaPlatform.objects.filter(is_active=True).order_by(
        "display_order", "name"
    )

    results = [
        {
            "id": platform.id,
            "name": platform.name,
            "slug": platform.slug,
            "icon": platform.icon.url if platform.icon else None,
            "url_template": platform.url_template,
            "display_order": platform.display_order,
        }
        for platform in platforms
    ]

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        }
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

def serialize_personal_hobby(
    personal_hobby
):

    return {
        "id": personal_hobby.id,

        "personal_account_id": (
            personal_hobby.personal_account_id
        ),

        "name": personal_hobby.name,

        "is_active": (
            personal_hobby.is_active
        ),

        "created_at": (
            personal_hobby.created_at.isoformat()
        ),

        "updated_at": (
            personal_hobby.updated_at.isoformat()
        ),
    }

def serialize_personal_interested_category(
    personal_interested_category
):
    category = personal_interested_category.category

    return {
        "id": personal_interested_category.id,
        "personal_account_id": (
            personal_interested_category.personal_account_id
        ),
        "category": {
            "id": category.id,
            "category_id": str(category.category_id),
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "is_featured": category.is_featured,
            "display_order": category.display_order,
            "visibility": category.visibility,
        },
        "is_active": (
            personal_interested_category.is_active
        ),
        "created_at": (
            personal_interested_category.created_at.isoformat()
        ),
        "updated_at": (
            personal_interested_category.updated_at.isoformat()
        ),
    }


@csrf_exempt
@require_http_methods(["POST"])
def personal_hobby_add(
    request,
    personal_account_id,
):

    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response


    try:

        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "detail":
                "Invalid JSON."
            },
            status=400,
        )


    name = data.get(
        "name",
        "",
    ).strip()


    if not name:

        return JsonResponse(
            {
                "detail":
                "Hobby name is required."
            },
            status=400,
        )


    personal_hobby, created = (
        PersonalHobby.objects.get_or_create(
            personal_account=personal_account,
            name=name,
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
def personal_hobby_list(
    request,
    personal_account_id,
):

    try:

        personal_account = (
            PersonalAccount.objects.get(
                id=personal_account_id
            )
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
        )
        .order_by(
            "created_at"
        )
    )


    results = [

        serialize_personal_hobby(
            personal_hobby
        )

        for personal_hobby
        in personal_hobbies

    ]


    return JsonResponse(
        {
            "personal_account_id":
            personal_account.id,

            "count":
            len(results),

            "results":
            results,
        }
    )


@require_http_methods(["GET"])
def personal_hobby_list(
    request,
    personal_account_id,
):

    try:

        personal_account = (
            PersonalAccount.objects.get(
                id=personal_account_id
            )
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
        )
        .order_by(
            "created_at"
        )
    )


    results = [

        serialize_personal_hobby(
            personal_hobby
        )

        for personal_hobby
        in personal_hobbies

    ]


    return JsonResponse(
        {
            "personal_account_id":
            personal_account.id,

            "count":
            len(results),

            "results":
            results,
        }
    )


@csrf_exempt
@require_http_methods(
    ["DELETE"]
)
def personal_hobby_remove(
    request,
    personal_account_id,
    personal_hobby_id,
):

    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:

        return error_response


    try:

        personal_hobby = (
            PersonalHobby.objects.get(
                id=personal_hobby_id,
                personal_account=personal_account,
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
        },
        status=200,
    )


@require_http_methods(["GET"])
def personal_interested_category_list(
    request,
    personal_account_id,
):
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

    personal_interested_categories = (
        PersonalInterestedCategory.objects
        .filter(
            personal_account=personal_account,
            is_active=True,
            category__visibility=Category.VISIBILITY_PUBLIC,
        )
        .select_related("category")
        .order_by(
            "category__display_order",
            "category__name",
        )
    )

    results = [
        serialize_personal_interested_category(
            personal_interested_category
        )
        for personal_interested_category
        in personal_interested_categories
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
@require_http_methods(
    ["POST"]
)
def personal_interested_category_add(
    request,
    personal_account_id,
):

    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:

        return error_response


    try:

        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "detail":
                "Invalid JSON."
            },
            status=400,
        )


    category_id = data.get(
        "category_id"
    )


    if not category_id:

        return JsonResponse(
            {
                "detail":
                "Category ID is required."
            },
            status=400,
        )


    try:

        category = Category.objects.get(
            id=category_id,
            visibility=Category.VISIBILITY_PUBLIC,
        )

    except Category.DoesNotExist:

        return JsonResponse(
            {
                "detail":
                "Category not found."
            },
            status=404,
        )


    personal_interested_category, created = (
        PersonalInterestedCategory.objects.get_or_create(
            personal_account=personal_account,
            category=category,
            defaults={
                "is_active": True,
            },
        )
    )


    if not created:

        return JsonResponse(
            {
                "detail":
                "This category is already added "
                "to the personal account."
            },
            status=400,
        )


    return JsonResponse(
        serialize_personal_interested_category(
            personal_interested_category
        ),
        status=201,
    )

@csrf_exempt
@require_http_methods(["DELETE"])
def personal_interested_category_remove(
    request,
    personal_account_id,
    category_id,
):
    personal_account, error_response = (
        get_authenticated_personal_account_by_id(
            request,
            personal_account_id,
        )
    )

    if error_response is not None:
        return error_response

    try:
        personal_interested_category = (
            PersonalInterestedCategory.objects.get(
                personal_account=personal_account,
                category_id=category_id,
            )
        )
    except PersonalInterestedCategory.DoesNotExist:
        return JsonResponse(
            {
                "detail":
                "Personal interested category not found."
            },
            status=404,
        )

    personal_interested_category.delete()

    return JsonResponse(
        {
            "detail":
            "Category removed from personal account."
        },
        status=200,
    )

@require_http_methods(["GET"])
def public_profile_by_username(request, username):
    try:
        identity = UserIdentity.objects.get(
            username=username,
            is_active=True,
        )
    except UserIdentity.DoesNotExist:
        return JsonResponse(
            {
                "detail": "Profile not found."
            },
            status=404,
        )

    account_types = (
        identity.account_types
        .filter(is_active=True)
        .order_by("-is_primary", "id")
    )

    primary_account = account_types.first()

    if primary_account is None:
        return JsonResponse(
            {
                "detail": "No active account type found."
            },
            status=404,
        )

    return JsonResponse(
        {
            "user_id": str(identity.user_id),
            "username": identity.username,
            "account_type": primary_account.account_type,
        }
    )
