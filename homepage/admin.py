from django.contrib import admin

from .models import (
    HomepageCTA,
    HomepageHero,
    HomepageSection,
    PlatformStatistic,
)


@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = (
        "section_type",
        "title",
        "data_source",
        "card_limit",
        "display_order",
        "is_visible",
        "show_view_all",
    )

    list_editable = (
        "data_source",
        "card_limit",
        "display_order",
        "is_visible",
        "show_view_all",
    )

    search_fields = (
        "section_type",
        "title",
        "subtitle",
    )

    list_filter = (
        "data_source",
        "is_visible",
        "show_view_all",
    )

    ordering = (
        "display_order",
        "id",
    )

    fieldsets = (
        (
            "Section Information",
            {
                "fields": (
                    "section_type",
                    "title",
                    "subtitle",
                    "data_source",
                )
            },
        ),
        (
            "Display Settings",
            {
                "fields": (
                    "display_order",
                    "card_limit",
                    "is_visible",
                )
            },
        ),
        (
            "View All Settings",
            {
                "fields": (
                    "show_view_all",
                    "view_all_label",
                    "view_all_url",
                )
            },
        ),
    )

@admin.register(HomepageHero)
class HomepageHeroAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "media_type",
        "display_order",
        "is_active",
    )
    list_editable = (
        "display_order",
        "is_active",
    )
    ordering = ("display_order", "id")


@admin.register(PlatformStatistic)
class PlatformStatisticAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "value",
        "display_order",
        "is_visible",
    )
    list_editable = (
        "display_order",
        "is_visible",
    )
    ordering = ("display_order", "id")


@admin.register(HomepageCTA)
class HomepageCTAAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "button_label",
        "is_active",
    )
    list_editable = (
        "is_active",
    )