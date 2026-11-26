from django.db import transaction
from django.utils import timezone

from .models import SecurityProfile


PASSWORD_LOGIN_LOCKOUTS = {
    3: 60,
    4: 360,
    5: 1440,
}

MAX_FAILED_PASSWORD_ATTEMPTS = 6


@transaction.atomic
def check_password_login_access(profile):
    locked_profile = SecurityProfile.objects.select_for_update().get(
        pk=profile.pk
    )

    if locked_profile.password_login_disabled:
        return {
            "allowed": False,
            "reason": "password_login_disabled",
            "locked_until": None,
        }

    now = timezone.now()
    locked_until = locked_profile.password_login_locked_until

    if locked_until and locked_until > now:
        return {
            "allowed": False,
            "reason": "password_login_locked",
            "locked_until": locked_until,
        }

    if locked_until:
        locked_profile.password_login_locked_until = None
        locked_profile.save(
            update_fields=["password_login_locked_until"]
        )

    return {
        "allowed": True,
        "reason": None,
        "locked_until": None,
    }


@transaction.atomic
def register_failed_password_attempt(profile):
    locked_profile = SecurityProfile.objects.select_for_update().get(
        pk=profile.pk
    )

    if locked_profile.password_login_disabled:
        return {
            "disabled": True,
            "locked_until": None,
            "attempts": locked_profile.failed_password_attempts,
        }

    now = timezone.now()
    locked_until = locked_profile.password_login_locked_until

    if locked_until and locked_until > now:
        return {
            "disabled": False,
            "locked_until": locked_until,
            "attempts": locked_profile.failed_password_attempts,
        }

    locked_profile.password_login_locked_until = None
    locked_profile.failed_password_attempts += 1

    attempts = locked_profile.failed_password_attempts

    if attempts >= MAX_FAILED_PASSWORD_ATTEMPTS:
        locked_profile.password_login_disabled = True

    elif attempts in PASSWORD_LOGIN_LOCKOUTS:
        locked_profile.password_login_locked_until = (
            now + timezone.timedelta(
                minutes=PASSWORD_LOGIN_LOCKOUTS[attempts]
            )
        )

    locked_profile.save(update_fields=[
        "failed_password_attempts",
        "password_login_locked_until",
        "password_login_disabled",
    ])

    return {
        "disabled": locked_profile.password_login_disabled,
        "locked_until": locked_profile.password_login_locked_until,
        "attempts": attempts,
    }


@transaction.atomic
def reset_password_login_attempts(profile):
    locked_profile = SecurityProfile.objects.select_for_update().get(
        pk=profile.pk
    )

    locked_profile.failed_password_attempts = 0
    locked_profile.password_login_locked_until = None
    locked_profile.password_login_disabled = False

    locked_profile.save(update_fields=[
        "failed_password_attempts",
        "password_login_locked_until",
        "password_login_disabled",
    ])

    return locked_profile
