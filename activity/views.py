import json

from django.http import JsonResponse
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from identity.models import PersonalAccount
from identity.permissions import (
    is_owner,
    permission_denied,
    require_authentication,
)

from .models import Activity, ActivityAppearance, ActivityComment, ActivityDefaultAppearance, ActivityLike
from core.services.html_sanitizer import sanitize_html
from core.services.image_processor import process_image
from core.services.feature_access import get_feature_access
from notifications.services import create_notification


def _get_activity_default_appearance():
    return ActivityDefaultAppearance.objects.order_by("id").first()


def _notify_activity_comment_participants(*, activity, comment, actor_user):
    recipients = {activity.personal_account.identity}

    if comment.parent_id is None:
        participants = ActivityComment.objects.filter(
            activity=activity,
        ).select_related("personal_account__identity")

        for participant in participants:
            recipients.add(participant.personal_account.identity)
    else:
        thread_comments = ActivityComment.objects.filter(
            models.Q(id=comment.parent_id) | models.Q(parent_id=comment.parent_id)
        ).select_related("personal_account__identity")

        for participant in thread_comments:
            recipients.add(participant.personal_account.identity)

    recipients.discard(actor_user)

    if comment.parent_id is None:
        notification_type = "activity_comment"
        title = "New Comment on Your Activity"
        message = (
            f"{comment.personal_account.display_name or 'Someone'} "
            "commented on an activity."
        )
    else:
        notification_type = "activity_comment_reply"
        title = "New Reply on Activity Comment"
        message = (
            f"{comment.personal_account.display_name or 'Someone'} "
            "replied to an activity comment."
        )

    for recipient in recipients:
        create_notification(
            user=recipient,
            category="activity",
            notification_type=notification_type,
            title=title,
            message=message,
            source="activity",
            action_url=f"/activity?activity={activity.id}&comment={comment.id}",
            priority="normal",
        )


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
            "liked": False,
            "like_count": 0,
            "comment_count": 0,
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
                    "liked": ActivityLike.objects.filter(
                        activity=activity,
                        personal_account__identity_id=request.authenticated_identity.id,
                    ).exists(),
                    "like_count": ActivityLike.objects.filter(
                        activity=activity
                    ).count(),
                    "comment_count": ActivityComment.objects.filter(
                        activity=activity
                    ).count(),
                    "is_published": activity.is_published,
                    "created_at": activity.created_at,
                    "updated_at": activity.updated_at,
                }
                for activity in activities
            ]
        }
    )

@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_authentication
def activity_comments(request, activity_id):
    try:
        activity = Activity.objects.get(
            id=activity_id,
            is_published=True,
        )
    except Activity.DoesNotExist:
        return JsonResponse(
            {"detail": "Activity not found."},
            status=404,
        )

    if request.method == "GET":
        comments = ActivityComment.objects.filter(
            activity=activity,
            parent__isnull=True,
        ).select_related(
            "personal_account",
            "personal_account__identity",
        )

        return JsonResponse(
            {
                "results": [
                    {
                        "id": comment.id,
                        "activity_id": comment.activity_id,
                        "parent_id": comment.parent_id,
                        "content": comment.content,
                        "created_at": comment.created_at,
                        "updated_at": comment.updated_at,
                        "author": {
                            "id": comment.personal_account.id,
                            "display_name": comment.personal_account.display_name,
                            "username": comment.personal_account.username,
                            "profile_photo": (
                                comment.personal_account.profile_photo.url
                                if comment.personal_account.profile_photo
                                else ""
                            ),
                            "first_name": comment.personal_account.identity.first_name,
                            "last_name": comment.personal_account.identity.last_name,
                        },
                        "replies": [
                            {
                                "id": reply.id,
                                "activity_id": reply.activity_id,
                                "parent_id": reply.parent_id,
                                "content": reply.content,
                                "created_at": reply.created_at,
                                "updated_at": reply.updated_at,
                                "author": {
                                    "id": reply.personal_account.id,
                                    "display_name": reply.personal_account.display_name,
                                    "username": reply.personal_account.username,
                                    "profile_photo": (
                                        reply.personal_account.profile_photo.url
                                        if reply.personal_account.profile_photo
                                        else ""
                                    ),
                                    "first_name": reply.personal_account.identity.first_name,
                                    "last_name": reply.personal_account.identity.last_name,
                                },
                            }
                            for reply in comment.replies.all()
                        ],
                    }
                    for comment in comments
                ],
                "comment_count": ActivityComment.objects.filter(
                    activity=activity
                ).count(),
            }
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    content = sanitize_html(
        str(data.get("content", "")).strip()
    )

    if not content or content == "<p></p>":
        return JsonResponse(
            {"detail": "Comment content is required."},
            status=400,
        )

    parent_id = data.get("parent_id")
    parent = None

    if parent_id is not None:
        try:
            parent = ActivityComment.objects.get(
                id=int(parent_id),
                activity=activity,
            )
        except (ActivityComment.DoesNotExist, ValueError, TypeError):
            return JsonResponse(
                {"detail": "Parent comment not found."},
                status=404,
            )

    try:
        personal_account = PersonalAccount.objects.get(
            identity_id=request.authenticated_identity.id
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Personal account not found."},
            status=404,
        )

    comment = ActivityComment.objects.create(
        activity=activity,
        personal_account=personal_account,
        parent=parent,
        content=content,
    )

    _notify_activity_comment_participants(
        activity=activity,
        comment=comment,
        actor_user=personal_account.identity,
    )

    return JsonResponse(
        {
            "id": comment.id,
            "activity_id": comment.activity_id,
            "parent_id": comment.parent_id,
            "content": comment.content,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
            "author": {
                "id": personal_account.id,
                "display_name": personal_account.display_name,
                "username": personal_account.username,
                "profile_photo": (
                    personal_account.profile_photo.url
                    if personal_account.profile_photo
                    else ""
                ),
                "first_name": personal_account.identity.first_name,
                "last_name": personal_account.identity.last_name,
            },
            "replies": [],
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def activity_like(request, activity_id):
    try:
        activity = Activity.objects.get(
            id=activity_id,
            is_published=True,
        )
    except Activity.DoesNotExist:
        return JsonResponse(
            {
                "detail": "Activity not found."
            },
            status=404,
        )

    try:
        personal_account = PersonalAccount.objects.get(
            identity_id=request.authenticated_identity.id
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {
                "detail": "Personal account not found."
            },
            status=404,
        )

    like = ActivityLike.objects.filter(
        activity=activity,
        personal_account=personal_account,
    ).first()

    if like:
        like.delete()
        liked = False
    else:
        ActivityLike.objects.create(
            activity=activity,
            personal_account=personal_account,
        )
        liked = True

    like_count = ActivityLike.objects.filter(
        activity=activity
    ).count()

    return JsonResponse(
        {
            "activity_id": activity.id,
            "liked": liked,
            "like_count": like_count,
        }
    )


@csrf_exempt
@require_http_methods(["GET"])
@require_authentication
def activity_appearance(request):
    try:
        personal_account = PersonalAccount.objects.get(
            identity_id=request.authenticated_identity.id,
            is_active=True,
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Personal account not found."},
            status=404,
        )

    appearance = ActivityAppearance.objects.filter(
        personal_account=personal_account,
    ).first()

    default_appearance = _get_activity_default_appearance()

    if appearance:
        background_color = (
            appearance.background_color
            or (
                default_appearance.background_color
                if default_appearance and default_appearance.is_enabled
                else "#F5F8FC"
            )
        )
        wallpaper = (
            appearance.wallpaper.url
            if appearance.wallpaper
            else (
                default_appearance.wallpaper.url
                if default_appearance and default_appearance.is_enabled and default_appearance.wallpaper
                else ""
            )
        )
        appearance_id = appearance.id
        created_at = appearance.created_at
        updated_at = appearance.updated_at
    else:
        background_color = (
            default_appearance.background_color
            if default_appearance and default_appearance.is_enabled
            else "#F5F8FC"
        )
        wallpaper = (
            default_appearance.wallpaper.url
            if default_appearance and default_appearance.is_enabled and default_appearance.wallpaper
            else ""
        )
        appearance_id = None
        created_at = None
        updated_at = None

    return JsonResponse(
        {
            "id": appearance_id,
            "personal_account_id": personal_account.id,
            "background_color": background_color,
            "wallpaper": wallpaper,
            "created_at": created_at,
            "updated_at": updated_at,
        }
    )


@csrf_exempt
@require_http_methods(["PUT"])
@require_authentication
def activity_background_color_update(request):
    access = get_feature_access(request, "activity_background_color")

    if access["access"] == "error":
        return JsonResponse(
            {"detail": access["detail"]},
            status=400,
        )

    if access["access"] == "locked":
        return JsonResponse(
            {
                "detail": "This feature is not available for the current account.",
                "feature_key": "activity_background_color",
            },
            status=403,
        )

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    background_color = str(
        data.get("background_color", "")
    ).strip()

    if not background_color:
        return JsonResponse(
            {"detail": "background_color is required."},
            status=400,
        )

    if not background_color.startswith("#") or len(background_color) not in {4, 7}:
        return JsonResponse(
            {"detail": "Invalid background color."},
            status=400,
        )

    try:
        int(background_color[1:], 16)
    except ValueError:
        return JsonResponse(
            {"detail": "Invalid background color."},
            status=400,
        )

    try:
        personal_account = PersonalAccount.objects.get(
            identity_id=request.authenticated_identity.id,
            is_active=True,
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Personal account not found."},
            status=404,
        )

    appearance, _ = ActivityAppearance.objects.get_or_create(
        personal_account=personal_account,
    )

    appearance.background_color = background_color.upper()
    appearance.save(update_fields=["background_color", "updated_at"])

    return JsonResponse(
        {
            "id": appearance.id,
            "personal_account_id": appearance.personal_account_id,
            "background_color": appearance.background_color,
            "wallpaper": (
                appearance.wallpaper.url
                if appearance.wallpaper
                else ""
            ),
            "updated_at": appearance.updated_at,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
@require_authentication
def activity_wallpaper_update(request):
    access = get_feature_access(request, "activity_wallpaper")

    if access["access"] == "error":
        return JsonResponse(
            {"detail": access["detail"]},
            status=400,
        )

    if access["access"] == "locked":
        return JsonResponse(
            {
                "detail": "This feature is not available for the current account.",
                "feature_key": "activity_wallpaper",
            },
            status=403,
        )

    try:
        personal_account = PersonalAccount.objects.get(
            identity_id=request.authenticated_identity.id,
            is_active=True,
        )
    except PersonalAccount.DoesNotExist:
        return JsonResponse(
            {"detail": "Personal account not found."},
            status=404,
        )

    if "wallpaper" not in request.FILES:
        return JsonResponse(
            {"detail": "wallpaper is required."},
            status=400,
        )

    old_wallpaper = None

    try:
        processed_wallpaper = process_image(
            request.FILES["wallpaper"],
            preset="background",
        )
    except ValueError as error:
        return JsonResponse(
            {"detail": str(error)},
            status=400,
        )

    appearance, _ = ActivityAppearance.objects.get_or_create(
        personal_account=personal_account,
    )

    if appearance.wallpaper:
        old_wallpaper = appearance.wallpaper.name

    appearance.wallpaper = processed_wallpaper
    appearance.save(update_fields=["wallpaper", "updated_at"])

    if old_wallpaper:
        appearance.wallpaper.storage.delete(old_wallpaper)

    return JsonResponse(
        {
            "id": appearance.id,
            "personal_account_id": appearance.personal_account_id,
            "background_color": appearance.background_color,
            "wallpaper": (
                appearance.wallpaper.url
                if appearance.wallpaper
                else ""
            ),
            "updated_at": appearance.updated_at,
        }
    )
