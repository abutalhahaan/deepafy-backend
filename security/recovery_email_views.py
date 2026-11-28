import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from identity.models import UserIdentity
from .models import SecurityProfile
from .recovery_email import (
    send_recovery_email_otp,
    verify_recovery_email_otp,
)


logger = logging.getLogger(__name__)


def mask_recovery_email(email):
    if not email or "@" not in email:
        return None

    local, domain = email.split("@", 1)
    visible = local[:2]
    return f"{visible}{'*' * max(3, len(local) - len(visible))}@{domain}"


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def recovery_email_status(request):
    profile, _ = SecurityProfile.objects.get_or_create(
        identity=request.user,
    )

    if request.method == "GET":
        return Response({
            "has_recovery_email": bool(profile.recovery_email),
            "recovery_email": mask_recovery_email(profile.recovery_email),
            "has_pending_email": bool(profile.pending_recovery_email),
            "pending_email": mask_recovery_email(profile.pending_recovery_email),
        })

    if request.method == "DELETE":
        old_email = profile.recovery_email

        profile.recovery_email = ""
        profile.pending_recovery_email = ""
        profile.save(update_fields=[
            "recovery_email",
            "pending_recovery_email",
            "updated_at",
        ])

        if old_email:
            try:
                send_mail(
                    subject="Deepafy Security Alert: Recovery Email Removed",
                    message=(
                        "Your Recovery Email was removed from your Deepafy "
                        "account. If you did not make this change, secure "
                        "your account immediately."
                    ),
                    from_email=(
                        settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
                    ),
                    recipient_list=[old_email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception(
                    "Unable to send recovery email removal alert for profile %s.",
                    profile.pk,
                )

        return Response({"message": "Recovery email removed."})

    email = request.data.get("email")

    if not isinstance(email, str):
        return Response(
            {"detail": "A valid email address is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    email = email.strip().lower()

    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {"detail": "Enter a valid email address."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if email == (request.user.email or "").strip().lower():
        return Response(
            {"detail": "Recovery email must be different from your primary email."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if UserIdentity.objects.filter(email__iexact=email).exclude(
        pk=request.user.pk,
    ).exists():
        return Response(
            {"detail": "This email address is already associated with another account."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    success, message = send_recovery_email_otp(profile, email)

    if not success:
        return Response(
            {"detail": message},
            status=status.HTTP_429_TOO_MANY_REQUESTS
            if "wait" in message.lower()
            else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    profile.pending_recovery_email = email
    profile.save(update_fields=[
        "pending_recovery_email",
        "updated_at",
    ])

    return Response({"message": message})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_recovery_email(request):
    profile, _ = SecurityProfile.objects.get_or_create(
        identity=request.user,
    )

    email = profile.pending_recovery_email
    otp = request.data.get("otp")

    if not email:
        return Response(
            {"detail": "No pending recovery email verification."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(otp, str) or len(otp) != 6 or not otp.isdigit():
        return Response(
            {"detail": "Enter a valid six-digit verification code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    success, message = verify_recovery_email_otp(
        profile,
        email,
        otp,
    )

    if not success:
        return Response(
            {"detail": message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    old_email = profile.recovery_email

    profile.recovery_email = email
    profile.pending_recovery_email = ""
    profile.save(update_fields=[
        "recovery_email",
        "pending_recovery_email",
        "updated_at",
    ])

    if old_email and old_email.lower() != email.lower():
        try:
            send_mail(
                subject="Deepafy Security Alert: Recovery Email Changed",
                message=(
                    "The Recovery Email on your Deepafy account was changed. "
                    "If you did not make this change, secure your account "
                    "immediately."
                ),
                from_email=(
                    settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
                ),
                recipient_list=[old_email],
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Unable to send recovery email change alert for profile %s.",
                profile.pk,
            )

    return Response({
        "message": message,
        "has_recovery_email": True,
        "recovery_email": mask_recovery_email(profile.recovery_email),
    })
