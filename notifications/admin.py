from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "category",
        "notification_type",
        "priority",
        "is_read",
        "created_at",
    )
    list_filter = (
        "category",
        "notification_type",
        "priority",
        "is_read",
    )
    search_fields = (
        "title",
        "message",
        "source",
        "user__email",
        "user__username",
    )
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
