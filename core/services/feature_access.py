from datetime import timedelta

from django.utils import timezone

from core.models import FeatureAccessControl, UserFeatureTrial, UserPremiumSubscription
from identity.permissions import get_current_account_type, get_authenticated_identity
from identity.models import AccountType


def get_current_feature(request, feature_key, account_type=None):
    if account_type:
        authenticated_identity = get_authenticated_identity(request)

        if authenticated_identity is None:
            return None, None, "Authentication credentials were not provided."

        current_account_type = (
            AccountType.objects
            .filter(
                identity=authenticated_identity,
                account_type=account_type,
                is_active=True,
            )
            .first()
        )

        if current_account_type is None:
            return None, None, "Requested account type is not available for this user."
    else:
        current_account_type = get_current_account_type(request)

        if current_account_type is None:
            return None, None, "No active primary account type found."

    try:
        feature = FeatureAccessControl.objects.get(
            feature_key=feature_key,
            account_type=current_account_type.account_type,
            is_enabled=True,
        )
    except FeatureAccessControl.DoesNotExist:
        return None, current_account_type, "Feature not configured for the current account type."

    return feature, current_account_type, None


def get_feature_access(request, feature_key, account_type=None):
    feature, current_account_type, error = get_current_feature(
        request,
        feature_key,
        account_type=account_type,
    )

    if error:
        return {
            "access": "error",
            "feature_key": feature_key,
            "account_type": (
                current_account_type.account_type
                if current_account_type
                else None
            ),
            "detail": error,
        }

    if feature.access_level == "free":
        return {
            "access": "free",
            "feature_key": feature.feature_key,
            "account_type": feature.account_type,
        }

    now = timezone.now()

    premium_subscription = UserPremiumSubscription.objects.filter(
        user=request.user,
        is_active=True,
        expires_at__gt=now,
        package__is_active=True,
    ).first()

    if premium_subscription:
        return {
            "access": "premium",
            "feature_key": feature.feature_key,
            "account_type": feature.account_type,
            "premium_active": True,
            "expires_at": premium_subscription.expires_at,
        }

    trial = UserFeatureTrial.objects.filter(
        user=request.user,
        feature=feature,
        is_active=True,
    ).first()

    if trial and trial.expires_at > now:
        return {
            "access": "trial",
            "feature_key": feature.feature_key,
            "account_type": feature.account_type,
            "trial_active": True,
            "expires_at": trial.expires_at,
        }

    return {
        "access": "locked",
        "feature_key": feature.feature_key,
        "account_type": feature.account_type,
        "trial_available": bool(
            feature.trial_enabled
            and feature.trial_days > 0
            and not trial
        ),
    }


def start_feature_trial_for_user(request, feature):
    now = timezone.now()

    trial, created = UserFeatureTrial.objects.get_or_create(
        user=request.user,
        feature=feature,
        defaults={
            "started_at": now,
            "expires_at": now + timedelta(days=feature.trial_days),
            "is_active": True,
        },
    )

    if not created:
        if trial.expires_at > now and trial.is_active:
            return {
                "access": "trial",
                "feature_key": feature.feature_key,
                "trial_active": True,
                "expires_at": trial.expires_at,
            }

        return {
            "access": "locked",
            "trial_available": False,
            "trial_expired": True,
            "feature_key": feature.feature_key,
        }

    return {
        "access": "trial",
        "feature_key": feature.feature_key,
        "trial_active": True,
        "started_at": trial.started_at,
        "expires_at": trial.expires_at,
        "trial_days": feature.trial_days,
    }
