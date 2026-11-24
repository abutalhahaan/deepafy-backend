import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import SecurityProfile, TrustedLocationVerification


VERIFICATION_TOKEN_TTL_SECONDS = 90


def issue_trusted_location_verification(identity):
    profile = SecurityProfile.objects.filter(
        identity=identity
    ).first()

    if profile is None:
        raise ValueError("Security profile not found.")

    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    TrustedLocationVerification.objects.create(
        profile=profile,
        token_hash=token_hash,
        expires_at=timezone.now() + timedelta(
            seconds=VERIFICATION_TOKEN_TTL_SECONDS
        ),
    )

    return raw_token


def consume_trusted_location_verification(identity, raw_token):
    if not isinstance(raw_token, str) or not raw_token.strip():
        return False

    profile = SecurityProfile.objects.filter(
        identity=identity
    ).first()

    if profile is None:
        return False

    token_hash = hashlib.sha256(
        raw_token.strip().encode("utf-8")
    ).hexdigest()

    now = timezone.now()

    with transaction.atomic():
        updated = TrustedLocationVerification.objects.filter(
            profile=profile,
            token_hash=token_hash,
            used_at__isnull=True,
            expires_at__gt=now,
        ).update(used_at=now)

        return updated == 1
