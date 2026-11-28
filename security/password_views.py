import logging

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import SecurityProfile
from .jwt_authentication import create_versioned_refresh_token
from .password_login import reset_password_login_attempts
from .two_factor import (
    get_active_totp_method,
    decrypt_totp_secret,
    verify_and_consume_totp_code,
    consume_recovery_code,
    check_two_factor_lockout,
    register_failed_two_factor_attempt,
    reset_two_factor_attempts,
)


logger = logging.getLogger(__name__)


def send_password_change_alert(identity, recovery_email=""):
    recipients = {
        email.strip().lower()
        for email in (
            getattr(identity, "email", ""),
            recovery_email,
        )
        if isinstance(email, str) and email.strip()
    }

    if not recipients:
        return

    attempted_at = timezone.localtime().strftime(
        "%d %B %Y, %I:%M:%S %p %Z"
    )

    for recipient in recipients:
        try:
            send_mail(
                subject="Deepafy Security Alert: Password Changed",
                message=(
                    "Your Deepafy account password was changed successfully.\n\n"
                    f"Time: {attempted_at}\n\n"
                    "If you did not make this change, secure your account "
                    "immediately.\n\n"
                    "All previous login sessions have been revoked.\n\n"
                    "This is an automated security notification. "
                    "Your password is never included in this email."
                ),
                from_email=(
                    settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
                ),
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Unable to send password change alert for identity ID %s.",
                getattr(identity, "pk", "unknown"),
            )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")
    confirm_password = request.data.get("confirm_password")

    if not all(
        isinstance(value, str) and value
        for value in (current_password, new_password, confirm_password)
    ):
        return Response(
            {"detail": "All password fields are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not request.user.check_password(current_password):
        return Response(
            {"detail": "Current password is incorrect."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_password != confirm_password:
        return Response(
            {"detail": "New password and confirmation do not match."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.user.check_password(new_password):
        return Response(
            {"detail": "New password must be different from the current password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_password(new_password, user=request.user)
    except ValidationError as exc:
        return Response(
            {"detail": list(exc.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile = None

    with transaction.atomic():
        profile = SecurityProfile.objects.select_for_update().get(
            identity=request.user,
        )

        if profile.two_factor_enabled:
            locked, locked_until = check_two_factor_lockout(profile)

            if locked:
                return Response(
                    {
                        "detail": "Too many failed verification attempts. Try again after 15 minutes.",
                        "locked_until": locked_until.isoformat(),
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            code = request.data.get("code")
            recovery_code = request.data.get("recovery_code")
            verified = False

            method = get_active_totp_method(profile)

            try:
                if (
                    method
                    and isinstance(code, str)
                    and code.isdigit()
                    and len(code) == 6
                ):
                    secret = decrypt_totp_secret(method.encrypted_secret)
                    verified = verify_and_consume_totp_code(
                        method,
                        secret,
                        code,
                    )
                elif isinstance(recovery_code, str) and recovery_code:
                    verified = consume_recovery_code(
                        profile,
                        recovery_code,
                    )
            except ValueError:
                verified = False

            if not verified:
                locked, locked_until = register_failed_two_factor_attempt(
                    profile,
                )
                response_data = {
                    "detail": "Two-factor verification failed."
                }

                if locked:
                    response_data["locked_until"] = locked_until.isoformat()

                return Response(
                    response_data,
                    status=(
                        status.HTTP_429_TOO_MANY_REQUESTS
                        if locked
                        else status.HTTP_400_BAD_REQUEST
                    ),
                )

            reset_two_factor_attempts(profile)

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])

        profile.token_version += 1
        profile.password_changed_at = timezone.now()
        profile.save(update_fields=[
            "token_version",
            "password_changed_at",
            "updated_at",
        ])

        reset_password_login_attempts(profile)

        recovery_email = profile.recovery_email

    refresh = create_versioned_refresh_token(request.user)

    send_password_change_alert(
        request.user,
        recovery_email,
    )

    return Response(
        {
            "message": "Password changed successfully. Other sessions have been logged out.",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_200_OK,
    )
