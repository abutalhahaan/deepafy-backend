from django.contrib import admin

from .models import (
    GetStartedPageSettings,
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

@admin.register(GetStartedPageSettings)
class GetStartedPageSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "font_family",
        "is_active",
    )

    list_editable = (
        "is_active",
    )

    fieldsets = (
        (
            "Page Content",
            {
                "fields": (
                    "title",
                    "subtitle",
                    "left_heading",
                    "left_description",
                )
            },
        ),
        (
            "Personal Account Card",
            {
                "fields": (
                    "personal_title",
                    "personal_description",
                )
            },
        ),
        (
            "Company Account Card",
            {
                "fields": (
                    "company_title",
                    "company_description",
                )
            },
        ),
        (
            "Login Settings",
            {
                "fields": (
                    "login_text",
                )
            },
        ),
        (
            "Color Settings",
            {
                "fields": (
                    "page_background_color",
                    "left_panel_color",
                    "heading_color",
                    "text_color",
                    "personal_card_color",
                    "company_card_color",
                    "border_color",
                )
            },
        ),
        (
            "Typography Settings",
            {
                "fields": (
                    "font_family",
                    "title_font_size",
                    "subtitle_font_size",
                    "heading_font_size",
                    "body_font_size",
                    "card_title_font_size",
                    "card_text_font_size",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                )
            },
        ),
    )    