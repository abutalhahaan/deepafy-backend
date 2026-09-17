from django.contrib import admin

from core.services.image_processor import process_image

from .models import ActivityDefaultAppearance


@admin.register(ActivityDefaultAppearance)
class ActivityDefaultAppearanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "background_color",
        "wallpaper",
        "is_enabled",
        "updated_at",
    )

    list_editable = (
        "is_enabled",
    )

    fieldsets = (
        (
            "Activity Default Appearance",
            {
                "fields": (
                    "background_color",
                    "wallpaper",
                    "is_enabled",
                )
            },
        ),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        uploaded_wallpaper = request.FILES.get("wallpaper")
        if uploaded_wallpaper:
            processed_wallpaper = process_image(
                uploaded_wallpaper,
                preset="background",
            )
            obj.wallpaper = processed_wallpaper

        super().save_model(request, obj, form, change)
