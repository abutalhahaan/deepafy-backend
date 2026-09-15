import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from identity.models import PersonalAccount
from identity.permissions import (
    require_authentication,
)

from .models import Activity
from core.services.html_sanitizer import sanitize_html


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def activity_create(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "detail": "Invalid JSON."
            },
            status=400,
        )

    activity_type = str(
        data.get("activity_type", "")
    ).strip()

    content = sanitize_html(
        str(data.get("content", "")).strip()
    )

    category = str(
        data.get("category", "personal")
    ).strip()

    if not activity_type:
        return JsonResponse(
            {
                "detail": "Activity type is required."
            },
            status=400,
        )

    if category not in {
        choice.value
        for choice in Activity.ActivityCategory
    }:
        return JsonResponse(
            {
                "detail": "Invalid activity category."
            },
            status=400,
        )

    try:
        personal_account = (
            PersonalAccount.objects.get(
                identity_id=request.authenticated_identity.id
            )
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail": "Personal account not found."
            },
            status=404,
        )

    activity = Activity.objects.create(
        personal_account=personal_account,
        category=category,
        activity_type=activity_type,
        content=content,
    )

    return JsonResponse(
        {
            "id": activity.id,
            "personal_account_id": activity.personal_account_id,
            "author": {
                "id": activity.personal_account.id,
                "display_name": activity.personal_account.display_name,
                "username": activity.personal_account.username,
                "profile_photo": (
                    activity.personal_account.profile_photo.url
                    if activity.personal_account.profile_photo
                    else ""
                ),
                "first_name": activity.personal_account.identity.first_name,
                "last_name": activity.personal_account.identity.last_name,
            },
            "category": activity.category,
            "activity_type": activity.activity_type,
            "content": activity.content,
            "is_published": activity.is_published,
            "created_at": activity.created_at,
            "updated_at": activity.updated_at,
        },
        status=201,
    )



@csrf_exempt
@require_http_methods(["GET"])
@require_authentication
def activity_feed(request):
    activities = Activity.objects.filter(
        is_published=True
    ).select_related(
        "personal_account"
    )[:20]

    return JsonResponse(
        {
            "results": [
                {
                    "id": activity.id,
                    "personal_account_id": activity.personal_account_id,
                    "author": {
                        "id": activity.personal_account.id,
                        "display_name": activity.personal_account.display_name,
                        "username": activity.personal_account.username,
                        "profile_photo": (
                            activity.personal_account.profile_photo.url
                            if activity.personal_account.profile_photo
                            else ""
                        ),
                        "first_name": activity.personal_account.identity.first_name,
                        "last_name": activity.personal_account.identity.last_name,
                    },
                    "category": activity.category,
                    "activity_type": activity.activity_type,
                    "content": activity.content,
                    "is_published": activity.is_published,
                    "created_at": activity.created_at,
                    "updated_at": activity.updated_at,
                }
                for activity in activities
            ]
        }
    )
