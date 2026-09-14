from django.urls import path

from .views import notification_list, notification_unread_count, notification_mark_read, notification_mark_all_read

urlpatterns = [
    path("", notification_list, name="notification-list"),
    path("unread-count/", notification_unread_count, name="notification-unread-count"),
    path("<int:notification_id>/read/", notification_mark_read, name="notification-mark-read"),
    path("mark-all-read/", notification_mark_all_read, name="notification-mark-all-read"),
]
