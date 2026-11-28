from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import SecurityProfile


class VersionedJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        profile, _ = SecurityProfile.objects.get_or_create(
            identity=user,
        )

        token_version = validated_token.get("token_version", 0)

        if token_version != profile.token_version:
            raise AuthenticationFailed(
                "This session has expired. Please log in again.",
                code="token_version_mismatch",
            )

        return user


def create_versioned_refresh_token(user):
    from rest_framework_simplejwt.tokens import RefreshToken

    profile, _ = SecurityProfile.objects.get_or_create(
        identity=user,
    )

    refresh = RefreshToken.for_user(user)
    refresh["token_version"] = profile.token_version

    return refresh
