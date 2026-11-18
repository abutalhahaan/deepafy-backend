from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from identity.models import AccountType, UserIdentity
from core.models import (
    AnimationGlobalSetting,
    AnimationAccountSetting,
    AnimationUserPreference,
    AnimationRegistry,
)


class AnimationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = UserIdentity.objects.create(
            first_name="Animation",
            last_name="User",
            username="animation_user",
            email="animation_user@example.com",
            is_active=True,
        )

        self.personal = AccountType.objects.create(
            identity=self.user,
            account_type=AccountType.Type.PERSONAL,
            is_primary=True,
            is_active=True,
        )

        self.company = AccountType.objects.create(
            identity=self.user,
            account_type=AccountType.Type.COMPANY,
            is_primary=False,
            is_active=True,
        )

        AnimationGlobalSetting.objects.create(
            pk=1,
            user_customization_enabled=True,
            global_default={
                "enabled": True,
                "preset": "fade",
                "duration": 200,
                "easing": "ease-out",
                "intensity": 1,
            },
        )

        AnimationAccountSetting.objects.create(
            account_type="personal",
            settings={"preset": "scale"},
        )

        AnimationAccountSetting.objects.create(
            account_type="company",
            settings={"preset": "zoom"},
        )

        self.authenticate(self.user)

    def authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def test_user_settings_requires_authentication(self):
        self.client.credentials()

        response = self.client.get(
            "/api/core/animation/settings/"
        )

        self.assertEqual(response.status_code, 401)

    def test_user_receives_active_account_settings(self):
        response = self.client.get(
            "/api/core/animation/settings/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["account_type"], "personal")
        self.assertEqual(response.data["settings"]["preset"], "scale")

    def test_preferences_are_isolated_by_account_type(self):
        response = self.client.patch(
            "/api/core/animation/preferences/",
            {"global_override": {"preset": "blur"}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.personal.is_primary = False
        self.personal.save(update_fields=["is_primary"])

        self.company.is_primary = True
        self.company.save(update_fields=["is_primary"])

        response = self.client.get(
            "/api/core/animation/settings/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["account_type"], "company")
        self.assertEqual(response.data["settings"]["preset"], "zoom")
        self.assertEqual(response.data["preferences"]["global_override"], {})

        self.assertTrue(
            AnimationUserPreference.objects.filter(
                identity=self.user,
                account_type="personal",
                global_override={"preset": "blur"},
            ).exists()
        )

    def test_customization_disabled_preserves_saved_preferences(self):
        self.client.patch(
            "/api/core/animation/preferences/",
            {"global_override": {"preset": "blur"}},
            format="json",
        )

        global_setting = AnimationGlobalSetting.objects.get(pk=1)
        global_setting.user_customization_enabled = False
        global_setting.save(update_fields=["user_customization_enabled"])

        response = self.client.patch(
            "/api/core/animation/preferences/",
            {"global_override": {"preset": "liquid"}},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        preference = AnimationUserPreference.objects.get(
            identity=self.user,
            account_type="personal",
        )

        self.assertEqual(
            preference.global_override,
            {"preset": "blur"},
        )

        response = self.client.get(
            "/api/core/animation/settings/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["settings"]["preset"], "scale")

    def test_invalid_animation_settings_are_rejected(self):
        invalid_payloads = [
            {"preset": "unknown-preset"},
            {"duration": 2001},
            {"intensity": 2.1},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.patch(
                    "/api/core/animation/preferences/",
                    {"global_override": payload},
                    format="json",
                )

                self.assertEqual(response.status_code, 400)

    def test_non_admin_cannot_access_admin_settings(self):
        response = self.client.get(
            "/api/core/admin/animation/settings/"
        )

        self.assertEqual(response.status_code, 403)

    def test_staff_can_update_admin_settings(self):
        admin = UserIdentity.objects.create(
            username="animation_admin",
            email="animation_admin@example.com",
            is_active=True,
            is_staff=True,
        )

        self.authenticate(admin)

        response = self.client.patch(
            "/api/core/admin/animation/settings/",
            {
                "user_customization_enabled": False,
                "global_default": {"preset": "zoom"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["user_customization_enabled"])
        self.assertEqual(response.data["global_default"]["preset"], "zoom")

    def test_admin_rejects_invalid_account_type_settings(self):
        admin = UserIdentity.objects.create(
            username="animation_admin_2",
            email="animation_admin_2@example.com",
            is_active=True,
            is_superuser=True,
        )

        self.authenticate(admin)

        response = self.client.patch(
            "/api/core/admin/animation/account-settings/",
            {
                "account_type": "personal",
                "settings": {"preset": "invalid"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_rejects_unknown_account_type(self):
        admin = UserIdentity.objects.create(
            username="animation_admin_3",
            email="animation_admin_3@example.com",
            is_active=True,
            is_staff=True,
        )

        self.authenticate(admin)

        response = self.client.patch(
            "/api/core/admin/animation/account-settings/",
            {
                "account_type": "persoanl",
                "settings": {"preset": "scale"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            AnimationAccountSetting.objects.filter(
                account_type="persoanl"
            ).exists()
        )



    def test_animation_registry_requires_authentication(self):
        self.client.credentials()

        response = self.client.get(
            "/api/core/animation/registry/"
        )

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_receives_active_animation_registry(self):
        response = self.client.get(
            "/api/core/animation/registry/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["count"], 13)
        self.assertEqual(len(response.data["animations"]), 13)

        required_fields = {
            "id",
            "label",
            "engine",
            "category",
            "default_duration",
            "default_easing",
        }

        for animation in response.data["animations"]:
            with self.subTest(animation=animation["id"]):
                self.assertTrue(required_fields.issubset(animation.keys()))
                self.assertTrue(animation["active"])

    def test_registry_defaults_are_used_for_selected_preset(self):
        AnimationRegistry.objects.filter(pk="zoom").update(
            default_duration=480,
            default_easing="spring",
        )
        AnimationAccountSetting.objects.update_or_create(
            account_type="personal",
            defaults={"settings": {"preset": "zoom"}},
        )

        response = self.client.get("/api/core/animation/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["settings"]["preset"], "zoom")
        self.assertEqual(response.data["settings"]["duration"], 480)
        self.assertEqual(response.data["settings"]["easing"], "spring")

    def test_explicit_duration_and_easing_override_registry_defaults(self):
        AnimationRegistry.objects.filter(pk="zoom").update(
            default_duration=480,
            default_easing="spring",
        )
        AnimationAccountSetting.objects.update_or_create(
            account_type="personal",
            defaults={
                "settings": {
                    "preset": "zoom",
                    "duration": 350,
                    "easing": "linear",
                }
            },
        )

        response = self.client.get("/api/core/animation/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["settings"]["duration"], 350)
        self.assertEqual(response.data["settings"]["easing"], "linear")

    def test_user_preset_override_uses_registry_defaults(self):
        AnimationRegistry.objects.filter(pk="liquid").update(
            default_duration=620,
            default_easing="ease-in-out",
        )
        AnimationUserPreference.objects.create(
            identity=self.user,
            account_type="personal",
            global_override={"preset": "liquid"},
        )

        response = self.client.get("/api/core/animation/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["settings"]["preset"], "liquid")
        self.assertEqual(response.data["settings"]["duration"], 620)
        self.assertEqual(response.data["settings"]["easing"], "ease-in-out")
