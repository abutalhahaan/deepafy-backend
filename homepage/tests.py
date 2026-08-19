from django.urls import reverse
from rest_framework.test import APITestCase

from .models import (
    HomepageCTA,
    HomepageHero,
    HomepageSection,
    PlatformStatistic,
)


class HomepageAPITests(APITestCase):
    def test_homepage_api_returns_visible_content(self):
        HomepageSection.objects.create(
            section_type=HomepageSection.SectionType.HERO,
            title="Hero",
            display_order=1,
            is_visible=True,
        )

        HomepageSection.objects.create(
            section_type=HomepageSection.SectionType.RECENT_NEEDAFY,
            title="Hidden Section",
            display_order=2,
            is_visible=False,
        )

        HomepageHero.objects.create(
            media_type=HomepageHero.MediaType.IMAGE,
            title="Active Hero",
            display_order=1,
            is_active=True,
        )

        HomepageHero.objects.create(
            media_type=HomepageHero.MediaType.IMAGE,
            title="Inactive Hero",
            display_order=2,
            is_active=False,
        )

        PlatformStatistic.objects.create(
            title="Products",
            value="100",
            icon="package",
            display_order=2,
            is_visible=True,
        )

        PlatformStatistic.objects.create(
            title="Businesses",
            value="50",
            icon="building",
            display_order=1,
            is_visible=True,
        )

        PlatformStatistic.objects.create(
            title="Hidden Statistic",
            value="0",
            display_order=3,
            is_visible=False,
        )

        HomepageCTA.objects.create(
            title="Active CTA",
            description="Join Deepafy",
            button_label="Get Started",
            button_url="/register",
            is_active=True,
        )

        HomepageCTA.objects.create(
            title="Inactive CTA",
            description="Hidden CTA",
            button_label="Hidden",
            button_url="/hidden",
            is_active=False,
        )

        response = self.client.get("/api/homepage/")

        self.assertEqual(response.status_code, 200)

        data = response.data

        self.assertEqual(len(data["sections"]), 1)
        self.assertEqual(
            data["sections"][0]["title"],
            "Hero",
        )

        self.assertEqual(len(data["heroes"]), 1)
        self.assertEqual(
            data["heroes"][0]["title"],
            "Active Hero",
        )

        self.assertEqual(len(data["statistics"]), 2)
        self.assertEqual(
            data["statistics"][0]["title"],
            "Businesses",
        )
        self.assertEqual(
            data["statistics"][1]["title"],
            "Products",
        )

        self.assertIsNotNone(data["cta"])
        self.assertEqual(
            data["cta"]["title"],
            "Active CTA",
        )