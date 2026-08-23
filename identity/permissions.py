from functools import wraps

from django.http import JsonResponse

from rest_framework_simplejwt.authentication import (
    JWTAuthentication,
)


def get_authenticated_identity(request):
    jwt_authentication = JWTAuthentication()

    try:
        authenticated_user = (
            jwt_authentication.authenticate(request)
        )
    except Exception:
        return None

    if authenticated_user is None:
        return None

    user, _token = authenticated_user

    return user


def require_authentication(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        authenticated_identity = (
            get_authenticated_identity(request)
        )

        if authenticated_identity is None:
            return JsonResponse(
                {
                    "detail":
                    "Authentication credentials were not provided."
                },
                status=401,
            )

        request.authenticated_identity = (
            authenticated_identity
        )

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapped_view


def is_owner(
    authenticated_identity,
    owner_identity_id,
):
    return (
        authenticated_identity.id
        == owner_identity_id
    )


def permission_denied(message="Permission denied."):
    return JsonResponse(
        {
            "detail": message,
        },
        status=403,
    )