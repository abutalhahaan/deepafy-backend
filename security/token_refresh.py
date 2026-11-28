from django.contrib.auth import get_user_model

from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import SecurityProfile


class VersionedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)

        if not user_id:
            raise InvalidToken("Invalid refresh token.")

        try:
            user = get_user_model().objects.get(
                **{api_settings.USER_ID_FIELD: user_id}
            )
        except get_user_model().DoesNotExist:
            raise InvalidToken("Invalid refresh token.")

        profile, _ = SecurityProfile.objects.get_or_create(
            identity=user,
        )

        if refresh.payload.get("token_version", 0) != profile.token_version:
            raise InvalidToken(
                "This session has expired. Please log in again."
            )

        return super().validate(attrs)


class VersionedTokenRefreshView(TokenRefreshView):
    serializer_class = VersionedTokenRefreshSerializer
