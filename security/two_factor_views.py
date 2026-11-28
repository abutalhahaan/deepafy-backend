import base64
import hashlib
from io import BytesIO

import qrcode

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import SecurityMethod, SecurityProfile, TwoFactorLoginChallenge
from .jwt_authentication import create_versioned_refresh_token
from .two_factor import (
    generate_totp_secret,
    encrypt_totp_secret,
    decrypt_totp_secret,
    get_totp_provisioning_uri,
    verify_totp_code,
    verify_and_consume_totp_code,
    replace_recovery_codes,
    get_active_totp_method,
    consume_recovery_code,
    check_two_factor_lockout,
    register_failed_two_factor_attempt,
    reset_two_factor_attempts,
)


def create_totp_qr(provisioning_uri):
    image = qrcode.make(provisioning_uri)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def two_factor_status(request):
    profile, _ = SecurityProfile.objects.get_or_create(
        identity=request.user,
    )
    method = get_active_totp_method(profile)

    return Response({
        "two_factor_enabled": profile.two_factor_enabled,
        "authenticator_enabled": bool(method),
        "recovery_codes_remaining": profile.recovery_codes.filter(
            used_at__isnull=True,
        ).count(),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def setup_totp(request):
    profile, _ = SecurityProfile.objects.get_or_create(
        identity=request.user,
    )

    existing = SecurityMethod.objects.filter(
        profile=profile,
        method=SecurityMethod.Method.TOTP,
    ).first()

    if existing and existing.status == SecurityMethod.Status.ACTIVE:
        return Response(
            {"detail": "Authenticator App is already enabled."},
            status=status.HTTP_409_CONFLICT,
        )

    secret = generate_totp_secret()
    encrypted_secret = encrypt_totp_secret(secret)

    method, _ = SecurityMethod.objects.update_or_create(
        profile=profile,
        method=SecurityMethod.Method.TOTP,
        defaults={
            "status": SecurityMethod.Status.PENDING,
            "is_primary": False,
            "encrypted_secret": encrypted_secret,
            "verified_at": None,
            "last_used_at": None,
        },
    )

    uri = get_totp_provisioning_uri(
        secret,
        account_name=request.user.email or request.user.username,
        issuer="Deepafy",
    )

    return Response({
        "message": "Scan the QR code with your Authenticator App, then verify the 6-digit code.",
        "qr_code": create_totp_qr(uri),
        "provisioning_uri": uri,
        "secret": secret,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_totp_setup(request):
    profile, _ = SecurityProfile.objects.get_or_create(
        identity=request.user,
    )

    locked, locked_until = check_two_factor_lockout(profile)
    if locked:
        return Response(
            {
                "detail": "Too many failed attempts. Try again after 15 minutes.",
                "locked_until": locked_until.isoformat(),
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    code = request.data.get("code")
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        locked, locked_until = register_failed_two_factor_attempt(profile)
        response_data = {"detail": "Enter a valid 6-digit authenticator code."}
        if locked:
            response_data["locked_until"] = locked_until.isoformat()
        return Response(
            response_data,
            status=status.HTTP_429_TOO_MANY_REQUESTS if locked else status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        method = SecurityMethod.objects.select_for_update().filter(
            profile=profile,
            method=SecurityMethod.Method.TOTP,
            status=SecurityMethod.Status.PENDING,
        ).first()

        if not method or not method.encrypted_secret:
            return Response(
                {"detail": "No pending Authenticator setup found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            secret = decrypt_totp_secret(method.encrypted_secret)
        except ValueError:
            return Response(
                {"detail": "Authenticator setup could not be verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verify_and_consume_totp_code(method, secret, code):
            locked, locked_until = register_failed_two_factor_attempt(profile)
            response_data = {"detail": "Invalid authenticator code."}
            if locked:
                response_data["locked_until"] = locked_until.isoformat()
            return Response(
                response_data,
                status=status.HTTP_429_TOO_MANY_REQUESTS if locked else status.HTTP_400_BAD_REQUEST,
            )

        SecurityMethod.objects.filter(
            profile=profile,
            is_primary=True,
        ).exclude(pk=method.pk).update(is_primary=False)

        method.status = SecurityMethod.Status.ACTIVE
        method.is_primary = True
        method.verified_at = timezone.now()
        method.last_used_at = timezone.now()
        method.save(update_fields=[
            "status",
            "is_primary",
            "verified_at",
            "last_used_at",
            "updated_at",
        ])

        profile.two_factor_enabled = True
        profile.last_verified_at = timezone.now()
        profile.last_security_activity_at = timezone.now()
        profile.save(update_fields=[
            "two_factor_enabled",
            "last_verified_at",
            "last_security_activity_at",
            "updated_at",
        ])

        reset_two_factor_attempts(profile)
        recovery_codes = replace_recovery_codes(profile)

    return Response({
        "message": "Two-factor authentication enabled successfully.",
        "two_factor_enabled": True,
        "recovery_codes": recovery_codes,
        "recovery_codes_remaining": len(recovery_codes),
        "warning": "Save these recovery codes securely. They will not be shown again.",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def regenerate_recovery_codes(request):
    profile, _ = SecurityProfile.objects.get_or_create(
        identity=request.user,
    )

    locked, locked_until = check_two_factor_lockout(profile)
    if locked:
        return Response(
            {
                "detail": "Too many failed attempts. Try again after 15 minutes.",
                "locked_until": locked_until.isoformat(),
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    method = get_active_totp_method(profile)
    if not profile.two_factor_enabled or not method:
        return Response(
            {"detail": "Two-factor authentication is not enabled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    code = request.data.get("code")
    recovery_code = request.data.get("recovery_code")
    verified = False

    try:
        if isinstance(code, str) and code.isdigit() and len(code) == 6:
            secret = decrypt_totp_secret(method.encrypted_secret)
            verified = verify_and_consume_totp_code(method, secret, code)
        elif recovery_code:
            verified = consume_recovery_code(profile, recovery_code)
    except ValueError:
        verified = False

    if not verified:
        locked, locked_until = register_failed_two_factor_attempt(profile)
        response_data = {"detail": "Verification failed."}
        if locked:
            response_data["locked_until"] = locked_until.isoformat()
        return Response(
            response_data,
            status=status.HTTP_429_TOO_MANY_REQUESTS if locked else status.HTTP_400_BAD_REQUEST,
        )

    reset_two_factor_attempts(profile)
    codes = replace_recovery_codes(profile)

    return Response({
        "message": "Recovery codes regenerated successfully.",
        "recovery_codes": codes,
        "recovery_codes_remaining": len(codes),
        "warning": "Previous recovery codes are now invalid. Save these codes securely.",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def disable_two_factor(request):
    profile, _ = SecurityProfile.objects.get_or_create(
        identity=request.user,
    )

    locked, locked_until = check_two_factor_lockout(profile)
    if locked:
        return Response(
            {
                "detail": "Too many failed attempts. Try again after 15 minutes.",
                "locked_until": locked_until.isoformat(),
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    method = get_active_totp_method(profile)
    if not profile.two_factor_enabled or not method:
        return Response(
            {"detail": "Two-factor authentication is not enabled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    code = request.data.get("code")
    recovery_code = request.data.get("recovery_code")
    verified = False

    try:
        if isinstance(code, str) and code.isdigit() and len(code) == 6:
            secret = decrypt_totp_secret(method.encrypted_secret)
            verified = verify_and_consume_totp_code(method, secret, code)
        elif recovery_code:
            verified = consume_recovery_code(profile, recovery_code)
    except ValueError:
        verified = False

    if not verified:
        locked, locked_until = register_failed_two_factor_attempt(profile)
        response_data = {"detail": "Verification failed."}
        if locked:
            response_data["locked_until"] = locked_until.isoformat()
        return Response(
            response_data,
            status=status.HTTP_429_TOO_MANY_REQUESTS if locked else status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        method.status = SecurityMethod.Status.DISABLED
        method.is_primary = False
        method.encrypted_secret = ""
        method.save(update_fields=[
            "status",
            "is_primary",
            "encrypted_secret",
            "updated_at",
        ])

        profile.two_factor_enabled = False
        profile.two_factor_verification_attempts = 0
        profile.two_factor_locked_until = None
        profile.save(update_fields=[
            "two_factor_enabled",
            "two_factor_verification_attempts",
            "two_factor_locked_until",
            "updated_at",
        ])

        profile.recovery_codes.filter(
            used_at__isnull=True,
        ).update(used_at=timezone.now())

    return Response({
        "message": "Two-factor authentication disabled successfully.",
        "two_factor_enabled": False,
    })



@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_two_factor_login(request):
    import hashlib
    from rest_framework_simplejwt.tokens import RefreshToken

    challenge_token = request.data.get("challenge_token")
    code = request.data.get("code")
    recovery_code = request.data.get("recovery_code")

    if not isinstance(challenge_token, str) or not challenge_token:
        return Response(
            {"detail": "Login challenge token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token_hash = hashlib.sha256(challenge_token.encode()).hexdigest()

    with transaction.atomic():
        challenge = (
            TwoFactorLoginChallenge.objects
            .select_for_update()
            .select_related("profile", "profile__identity")
            .filter(token_hash=token_hash)
            .first()
        )

        if not challenge:
            return Response(
                {"detail": "Invalid login challenge."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        profile = challenge.profile

        locked, locked_until = check_two_factor_lockout(profile)
        if locked:
            return Response(
                {
                    "detail": "Too many failed attempts. Try again after 15 minutes.",
                    "code": "two_factor_locked",
                    "locked_until": locked_until.isoformat(),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        now = timezone.now()

        if challenge.consumed_at:
            return Response(
                {"detail": "This login challenge has already been used."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if challenge.expires_at <= now:
            return Response(
                {"detail": "Login challenge has expired. Please log in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not profile.two_factor_enabled:
            return Response(
                {"detail": "Two-factor authentication is not enabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        method = get_active_totp_method(profile)
        if not method or not method.encrypted_secret:
            return Response(
                {"detail": "Two-factor authentication is not properly configured."},
                status=status.HTTP_403_FORBIDDEN,
            )

        verified = False
        used_recovery_code = False

        try:
            if isinstance(code, str) and code.isdigit() and len(code) == 6:
                secret = decrypt_totp_secret(method.encrypted_secret)
                verified = verify_and_consume_totp_code(method, secret, code)
            elif recovery_code:
                verified = consume_recovery_code(profile, recovery_code)
                used_recovery_code = verified
        except ValueError:
            verified = False

        if not verified:
            challenge.attempts += 1
            challenge.save(update_fields=["attempts"])

            locked, locked_until = register_failed_two_factor_attempt(profile)
            response_data = {"detail": "Invalid authenticator or recovery code."}

            if locked:
                response_data["code"] = "two_factor_locked"
                response_data["locked_until"] = locked_until.isoformat()

            return Response(
                response_data,
                status=(
                    status.HTTP_429_TOO_MANY_REQUESTS
                    if locked
                    else status.HTTP_400_BAD_REQUEST
                ),
            )

        challenge.consumed_at = now
        challenge.save(update_fields=["consumed_at"])

        method.last_used_at = now
        method.save(update_fields=["last_used_at", "updated_at"])

        reset_two_factor_attempts(profile)

        identity = profile.identity
        identity.last_login = now
        identity.save(update_fields=["last_login"])

        refresh = create_versioned_refresh_token(identity)

        from identity.views import serialize_identity

        return Response({
            "message": "Login successful.",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": serialize_identity(identity),
            "recovery_code_used": used_recovery_code,
        }, status=status.HTTP_200_OK)
