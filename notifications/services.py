from .models import Notification


def create_notification(
    *,
    user,
    category,
    notification_type,
    title,
    message,
    source="",
    action_url="",
    priority="normal",
):
    return Notification.objects.create(
        user=user,
        category=category,
        notification_type=notification_type,
        title=title,
        message=message,
        source=source,
        action_url=action_url,
        priority=priority,
    )
