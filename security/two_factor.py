import secrets
import hmac
import string
import uuid

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import SecurityMethod, RecoveryCode, SecurityProfile


def get_fernet():
    key = getattr(settings, "TOTP_ENCRYPTION_KEY", None)
    if not key:
        raise RuntimeError("TOTP_ENCRYPTION_KEY is not configured.")
    return Fernet(key.encode())


def encrypt_totp_secret(secret):
    return get_fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted_secret):
    try:
        return get_fernet().decrypt(encrypted_secret.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        raise ValueError("Unable to decrypt TOTP secret.")


def generate_totp_secret():
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret, account_name, issuer="Deepafy"):
    return pyotp.TOTP(secret).provisioning_uri(
        name=account_name,
        issuer_name=issuer,
    )


def verify_totp_code(secret, code):
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_recovery_codes(count=10):
    alphabet = string.ascii_uppercase + string.digits
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(alphabet) for _ in range(16))
        codes.append("-".join(raw[i:i + 4] for i in range(0, 16, 4)))
    return codes


def normalize_recovery_code(code):
    if not isinstance(code, str):
        return ""
    return code.replace("-", "").replace(" ", "").strip().upper()


@transaction.atomic
def replace_recovery_codes(profile, count=10):
    RecoveryCode.objects.filter(
        profile=profile,
        used_at__isnull=True,
    ).update(used_at=timezone.now())

    codes = generate_recovery_codes(count)
    batch_id = uuid.uuid4()

    RecoveryCode.objects.bulk_create([
        RecoveryCode(
            profile=profile,
            batch_id=batch_id,
            code_hash=make_password(normalize_recovery_code(code)),
        )
        for code in codes
    ])

    return codes


@transaction.atomic
def consume_recovery_code(profile, code):
    normalized = normalize_recovery_code(code)
    if len(normalized) != 16:
        return False

    candidates = RecoveryCode.objects.select_for_update().filter(
        profile=profile,
        used_at__isnull=True,
    )

    for recovery_code in candidates:
        if check_password(normalized, recovery_code.code_hash):
            recovery_code.used_at = timezone.now()
            recovery_code.save(update_fields=["used_at"])
            return True

    return False


def get_active_totp_method(profile):
    return SecurityMethod.objects.filter(
        profile=profile,
        method=SecurityMethod.Method.TOTP,
        status=SecurityMethod.Status.ACTIVE,
    ).first()



MAX_TWO_FACTOR_ATTEMPTS = 3
TWO_FACTOR_LOCKOUT_MINUTES = 15


@transaction.atomic
def check_two_factor_lockout(profile):
    locked_profile = SecurityProfile.objects.select_for_update().get(
        pk=profile.pk
    )
    now = timezone.now()

    if locked_profile.two_factor_locked_until:
        if locked_profile.two_factor_locked_until > now:
            return True, locked_profile.two_factor_locked_until

        locked_profile.two_factor_verification_attempts = 0
        locked_profile.two_factor_locked_until = None
        locked_profile.save(update_fields=[
            "two_factor_verification_attempts",
            "two_factor_locked_until",
        ])

    return False, None


@transaction.atomic
def register_failed_two_factor_attempt(profile):
    locked_profile = SecurityProfile.objects.select_for_update().get(
        pk=profile.pk
    )
    now = timezone.now()

    if (
        locked_profile.two_factor_locked_until
        and locked_profile.two_factor_locked_until > now
    ):
        return True, locked_profile.two_factor_locked_until

    if locked_profile.two_factor_locked_until:
        locked_profile.two_factor_verification_attempts = 0
        locked_profile.two_factor_locked_until = None

    locked_profile.two_factor_verification_attempts += 1

    if (
        locked_profile.two_factor_verification_attempts
        >= MAX_TWO_FACTOR_ATTEMPTS
    ):
        locked_profile.two_factor_locked_until = (
            now + timezone.timedelta(minutes=TWO_FACTOR_LOCKOUT_MINUTES)
        )

    locked_profile.save(update_fields=[
        "two_factor_verification_attempts",
        "two_factor_locked_until",
    ])

    return (
        bool(locked_profile.two_factor_locked_until),
        locked_profile.two_factor_locked_until,
    )


@transaction.atomic
def reset_two_factor_attempts(profile):
    locked_profile = SecurityProfile.objects.select_for_update().get(
        pk=profile.pk
    )
    locked_profile.two_factor_verification_attempts = 0
    locked_profile.two_factor_locked_until = None
    locked_profile.save(update_fields=[
        "two_factor_verification_attempts",
        "two_factor_locked_until",
    ])

def verify_and_consume_totp_code(method, secret, code, now=None):
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return False

    totp = pyotp.TOTP(secret)
    current_step = totp.timecode(now or timezone.now())

    for candidate_step in (current_step - 1, current_step, current_step + 1):
        if candidate_step < 0:
            continue

        expected_code = totp.generate_otp(candidate_step)
        if not hmac.compare_digest(expected_code, code):
            continue

        updated = SecurityMethod.objects.filter(pk=method.pk).filter(
            Q(last_totp_step__isnull=True) |
            Q(last_totp_step__lt=candidate_step)
        ).update(last_totp_step=candidate_step)

        return updated == 1

    return False
