import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone

from .models import RecoveryEmailVerification


logger = logging.getLogger(__name__)

OTP_VALIDITY = timedelta(minutes=10)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_MAX_ATTEMPTS = 3
OTP_LOCKOUT_DURATION = timedelta(minutes=2)


def send_recovery_email_otp(profile, email):
    email = (email or "").strip().lower()
    now = timezone.now()

    latest = RecoveryEmailVerification.objects.filter(
        profile=profile,
    ).order_by("-created_at").first()

    if latest and now < latest.created_at + OTP_RESEND_COOLDOWN:
        return False, "Please wait before requesting another verification code."

    RecoveryEmailVerification.objects.filter(
        profile=profile,
        used_at__isnull=True,
    ).update(used_at=now)

    otp = f"{secrets.randbelow(1_000_000):06d}"

    verification = RecoveryEmailVerification.objects.create(
        profile=profile,
        email=email,
        otp_hash=make_password(otp),
        expires_at=now + OTP_VALIDITY,
    )

    subject = "Deepafy: Verify Your Recovery Email"
    message = (
        "Hello,\n\n"
        f"Your Deepafy Recovery Email verification code is: {otp}\n\n"
        "This code expires in 10 minutes and can only be used once.\n"
        "If you did not request this code, you can ignore this email.\n\n"
        "This is an automated security message from Deepafy."
    )

    try:
        sent = send_mail(
            subject=subject,
            message=message,
            from_email=(
                settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
            ),
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        verification.used_at = now
        verification.save(update_fields=["used_at"])
        logger.exception(
            "Unable to send recovery email verification for profile %s.",
            profile.pk,
        )
        return False, "Unable to send the verification email."

    if not sent:
        verification.used_at = now
        verification.save(update_fields=["used_at"])
        return False, "Unable to send the verification email."

    return True, "Verification code sent."


def verify_recovery_email_otp(profile, email, otp):
    email = (email or "").strip().lower()
    now = timezone.now()

    verification = RecoveryEmailVerification.objects.filter(
        profile=profile,
        email=email,
        used_at__isnull=True,
    ).order_by("-created_at").first()

    if verification is None:
        return False, "Invalid or expired verification code."

    if verification.locked_until:
        if now < verification.locked_until:
            return False, "Too many incorrect attempts. Please try again later."

        verification.failed_attempts = 0
        verification.locked_until = None
        verification.save(update_fields=["failed_attempts", "locked_until"])

    if now >= verification.expires_at:
        verification.used_at = now
        verification.save(update_fields=["used_at"])
        return False, "Verification code has expired."

    if not check_password(str(otp), verification.otp_hash):
        verification.failed_attempts += 1
        update_fields = ["failed_attempts"]

        if verification.failed_attempts >= OTP_MAX_ATTEMPTS:
            verification.locked_until = now + OTP_LOCKOUT_DURATION
            update_fields.append("locked_until")

        verification.save(update_fields=update_fields)

        if verification.failed_attempts >= OTP_MAX_ATTEMPTS:
            return False, "Too many incorrect attempts. Please try again in 2 minutes."

        return False, "Invalid verification code."

    verification.verified_at = now
    verification.used_at = now
    verification.save(update_fields=["verified_at", "used_at"])

    return True, "Recovery email verified."
