from rest_framework import serializers

from .models import (
    GetStartedPageSettings,
    HomepageCTA,
    HomepageHero,
    HomepageSection,
    PlatformStatistic,
)


class HomepageSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomepageSection
        fields = (
            "id",
            "section_type",
            "data_source",
            "title",
            "subtitle",
            "display_order",
            "card_limit",
            "is_visible",
            "show_view_all",
            "view_all_label",
            "view_all_url",
        )


class HomepageHeroSerializer(serializers.ModelSerializer):
    media_file = serializers.SerializerMethodField()

    class Meta:
        model = HomepageHero
        fields = (
            "id",
            "media_type",
            "media_url",
            "media_file",
            "title",
            "description",
            "cta_label",
            "cta_url",
            "desktop_position",
            "mobile_position",
            "object_fit",
            "alt_text",
            "display_order",
            "is_active",
        )
    def get_media_file(self, obj):
        if obj.media_file:
            request = self.context.get("request")

            if request:
                return request.build_absolute_uri(
                    obj.media_file.url
                )

            return obj.media_file.url

        return None


class PlatformStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformStatistic
        fields = (
            "id",
            "title",
            "value",
            "icon",
            "display_order",
        )


class HomepageCTASerializer(serializers.ModelSerializer):
    class Meta:
        model = HomepageCTA
        fields = (
            "id",
            "title",
            "description",
            "button_label",
            "button_url",
        )
class GetStartedPageSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GetStartedPageSettings
        fields = (
            "id",
            "title",
            "subtitle",
            "left_heading",
            "left_description",
            "personal_title",
            "personal_description",
            "company_title",
            "company_description",
            "login_text",
            "page_background_color",
            "left_panel_color",
            "heading_color",
            "text_color",
            "personal_card_color",
            "company_card_color",
            "border_color",
            "font_family",
            "title_font_size",
            "subtitle_font_size",
            "heading_font_size",
            "body_font_size",
            "card_title_font_size",
            "card_text_font_size",
        )
