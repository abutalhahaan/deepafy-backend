from django.contrib import admin

from .models import SocialMediaPlatform, UserSocialMedia


@admin.register(SocialMediaPlatform)
class SocialMediaPlatformAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "display_order",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("display_order", "name")


@admin.register(UserSocialMedia)
class UserSocialMediaAdmin(admin.ModelAdmin):
    list_display = (
        "identity",
        "platform",
        "username",
        "url",
        "created_at",
    )
    list_filter = ("platform",)
    search_fields = (
        "username",
        "identity__email",
        "platform__name",
    )
    ordering = ("platform__display_order", "platform__name")
