from rest_framework import serializers

from .models import (
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
            "title",
            "subtitle",
            "display_order",
            "is_visible",
            "show_view_all",
            "view_all_label",
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