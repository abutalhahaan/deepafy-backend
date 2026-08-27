from functools import wraps

from django.http import JsonResponse

from rest_framework_simplejwt.authentication import (
    JWTAuthentication,
)

from .models import PersonalAccount


def get_authenticated_identity(request):
    jwt_authentication = JWTAuthentication()

    print(
        "AUTHORIZATION HEADER:",
        request.headers.get("Authorization")
    )

    try:
        authenticated_user = (
            jwt_authentication.authenticate(request)
        )

    except Exception as error:

        print(
            "JWT AUTHENTICATION ERROR:",
            repr(error)
        )

        return None

    print(
        "AUTHENTICATED USER:",
        authenticated_user
    )

    if authenticated_user is None:
        return None

    user, _token = authenticated_user

    return user


def get_authenticated_personal_account(
    request,
    identity_id,
):
    authenticated_identity = (
        get_authenticated_identity(
            request
        )
    )

    if authenticated_identity is None:
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "Authentication credentials were not provided."
                },
                status=401,
            ),
        )

    if authenticated_identity.id != identity_id:
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "You do not have permission to modify this account."
                },
                status=403,
            ),
        )

    try:
        personal_account = (
            authenticated_identity.personal_account
        )

    except Exception:
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "Personal account not found."
                },
                status=404,
            ),
        )

    return (
        personal_account,
        None,
    )

def get_authenticated_personal_account_by_id(
    request,
    personal_account_id,
):
    authenticated_identity = (
        get_authenticated_identity(
            request
        )
    )

    if authenticated_identity is None:
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "Authentication credentials were not provided."
                },
                status=401,
            ),
        )

    try:
        personal_account = (
            PersonalAccount.objects.get(
                id=personal_account_id
            )
        )
    except PersonalAccount.DoesNotExist:
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "Personal account not found."
                },
                status=404,
            ),
        )

    if personal_account.identity_id != authenticated_identity.id:
        return (
            None,
            JsonResponse(
                {
                    "detail":
                        "You do not have permission to modify this account."
                },
                status=403,
            ),
        )

    return (
        personal_account,
        None,
    )


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