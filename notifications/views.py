from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)

    data = [
        {
            "id": notification.id,
            "category": notification.category,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "source": notification.source,
            "action_url": notification.action_url,
            "priority": notification.priority,
            "is_read": notification.is_read,
            "created_at": notification.created_at,
        }
        for notification in notifications
    ]

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_unread_count(request):
    count = Notification.objects.filter(
        user=request.user,
        is_read=False,
    ).count()

    return Response({"unread_count": count})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user,
    )

    notification.is_read = True
    notification.save(update_fields=["is_read"])

    return Response({
        "success": True,
        "id": notification.id,
        "is_read": True,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_mark_all_read(request):
    updated = Notification.objects.filter(
        user=request.user,
        is_read=False,
    ).update(is_read=True)

    return Response({
        "success": True,
        "updated": updated,
    })
