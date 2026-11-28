from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APIRequestFactory, force_authenticate

from security.models import RecoveryEmailVerification
from security.login_email import send_login_attempt_alert
from security.recovery_email import (
    send_recovery_email_otp,
    verify_recovery_email_otp,
)
from security.recovery_email_views import (
    recovery_email_status,
    verify_recovery_email,
)

from datetime import timedelta

from django.utils import timezone

from security.models import TrustedLocationVerification
from security.trusted_location_verification import (
    issue_trusted_location_verification,
    consume_trusted_location_verification,
)

from identity.models import UserIdentity
from security.models import SecurityProfile, SecurityPreference, TrustedLocation


class SecurityProfileSignalTests(TestCase):
    def test_security_profile_is_created_with_new_identity(self):
        identity = UserIdentity.objects.create(
            email="security-test@example.com",
            mobile_number="01800000001",
        )

        self.assertTrue(
            SecurityProfile.objects.filter(
                identity=identity,
            ).exists()
        )

    def test_identity_update_does_not_create_duplicate_profile(self):
        identity = UserIdentity.objects.create(
            email="security-update@example.com",
            mobile_number="01800000002",
        )

        identity.first_name = "Updated"
        identity.save()

        self.assertEqual(
            SecurityProfile.objects.filter(
                identity=identity,
            ).count(),
            1,
        )

    def test_each_identity_has_separate_security_profile(self):
        first = UserIdentity.objects.create(
            email="security-first@example.com",
            mobile_number="01800000003",
        )

        second = UserIdentity.objects.create(
            email="security-second@example.com",
            mobile_number="01800000004",
        )

        self.assertEqual(
            SecurityProfile.objects.count(),
            2,
        )

        self.assertNotEqual(
            first.security_profile.pk,
            second.security_profile.pk,
        )


    def test_security_preference_is_created_with_new_identity(self):
        identity = UserIdentity.objects.create(
            email="security-preference-test@example.com",
            mobile_number="01800000005",
        )

        preference = SecurityPreference.objects.get(
            profile__identity=identity,
        )

        self.assertFalse(preference.trusted_location_enabled)


from companies.models import (
    AdministrativeAssignment,
    AdministrativeRole,
    Company,
    CompanyRelationship,
    Country,
    Region,
)
from identity.models import (
    AccountType,
    PersonalAccount,
    ProfessionalAccount,
)
from institution.models import (
    Department,
    InstitutionDepartmentAdmin,
    InstitutionProfile,
    InstitutionType,
    InstitutionTypeGroup,
)
from security.context import (
    get_available_account_contexts,
    get_primary_account_context,
)


class AccountContextResolverTests(TestCase):
    def setUp(self):
        self.identity = self.create_identity("context-owner")

        self.region = Region.objects.create(
            name="Context Test Region",
        )
        self.country = Country.objects.create(
            region=self.region,
            name="Context Test Country",
            code="CTX",
        )
        self.type_group = InstitutionTypeGroup.objects.create(
            name="Context Test Group",
        )
        self.institution_type = InstitutionType.objects.create(
            group=self.type_group,
            name="Context Test Institution Type",
        )

    def create_identity(self, prefix, status=None):
        values = {
            "email": f"{prefix}@example.com",
            "username": prefix,
            "status": status or UserIdentity.Status.ACTIVE,
        }
        return UserIdentity.objects.create(**values)

    def create_company(self, name):
        return Company.objects.create(
            name=name,
            company_type="manufacturer",
            country="Bangladesh",
            business_email=f"{name.lower().replace(' ', '')}@example.com",
            business_mobile_number="01700000000",
            registered_address="Dhaka, Bangladesh",
            primary_contact_person="Test Contact",
        )

    def create_institution(self, identity, name):
        return InstitutionProfile.objects.create(
            identity=identity,
            institution_name=name,
            institution_type=self.institution_type,
            country=self.country,
        )

    def test_personal_and_professional_contexts(self):
        AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PERSONAL,
            is_primary=True,
        )
        PersonalAccount.objects.create(
            identity=self.identity,
            display_name="Personal Test",
        )

        AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PROFESSIONAL,
            is_active=True,
        )
        ProfessionalAccount.objects.create(
            identity=self.identity,
            professional_title="Software Engineer",
        )

        contexts = get_available_account_contexts(self.identity)
        context_types = {item["context_type"] for item in contexts}

        self.assertIn("personal", context_types)
        self.assertIn("professional", context_types)
        self.assertEqual(len(contexts), 2)

    def test_multiple_active_company_contexts_are_returned(self):
        first_company = self.create_company("Context Company One")
        second_company = self.create_company("Context Company Two")
        pending_company = self.create_company("Context Company Pending")

        CompanyRelationship.objects.create(
            company=first_company,
            identity=self.identity,
            relationship_type=CompanyRelationship.RelationshipType.OWNER,
            membership_status=CompanyRelationship.MembershipStatus.ACTIVE,
        )
        CompanyRelationship.objects.create(
            company=second_company,
            identity=self.identity,
            relationship_type=CompanyRelationship.RelationshipType.MANAGER,
            membership_status=CompanyRelationship.MembershipStatus.ACTIVE,
        )
        CompanyRelationship.objects.create(
            company=pending_company,
            identity=self.identity,
            relationship_type=CompanyRelationship.RelationshipType.MEMBER,
            membership_status=CompanyRelationship.MembershipStatus.PENDING,
        )

        contexts = get_available_account_contexts(self.identity)
        company_contexts = [
            item for item in contexts
            if item["context_type"] == "company"
        ]

        self.assertEqual(len(company_contexts), 2)
        self.assertEqual(
            {item["label"] for item in company_contexts},
            {"Context Company One", "Context Company Two"},
        )

    def test_institution_owner_and_department_admin_contexts(self):
        owner = self.create_identity("institution-owner")
        admin = self.create_identity("institution-department-admin")

        institution = self.create_institution(
            owner,
            "Context Test Institution",
        )
        department = Department.objects.create(
            name="Context Test Department",
        )
        institution.departments.add(department)

        InstitutionDepartmentAdmin.objects.create(
            institution=institution,
            department=department,
            identity=admin,
            is_active=True,
        )

        owner_contexts = get_available_account_contexts(owner)
        admin_contexts = get_available_account_contexts(admin)

        self.assertTrue(
            any(
                item["context_type"] == "institution"
                for item in owner_contexts
            )
        )
        self.assertTrue(
            any(
                item["context_type"] == "institution_department"
                for item in admin_contexts
            )
        )

    def test_global_admin_context_requires_matching_active_role(self):
        own_role = AdministrativeRole.objects.create(
            identity=self.identity,
            role_type=AdministrativeRole.RoleType.SUPER_ADMIN,
            is_active=True,
        )
        AdministrativeAssignment.objects.create(
            identity=self.identity,
            role=own_role,
            is_active=True,
        )

        other_identity = self.create_identity("other-global-admin")
        foreign_role = AdministrativeRole.objects.create(
            identity=other_identity,
            role_type=AdministrativeRole.RoleType.CO_SUPER_ADMIN,
            is_active=True,
        )
        AdministrativeAssignment.objects.create(
            identity=self.identity,
            role=foreign_role,
            is_active=True,
        )

        contexts = get_available_account_contexts(self.identity)
        admin_contexts = [
            item for item in contexts
            if item["context_type"] == "global_admin"
        ]

        self.assertEqual(len(admin_contexts), 1)
        self.assertEqual(admin_contexts[0]["role"], "super_admin")

    def test_inactive_identity_gets_no_contexts(self):
        inactive_identity = self.create_identity(
            "inactive-context",
            status=UserIdentity.Status.INACTIVE,
        )

        self.assertEqual(
            get_available_account_contexts(inactive_identity),
            [],
        )

    def test_primary_context_returns_primary_account(self):
        AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PERSONAL,
            is_primary=True,
        )
        PersonalAccount.objects.create(
            identity=self.identity,
            display_name="Primary Personal",
        )

        AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PROFESSIONAL,
            is_primary=False,
        )
        ProfessionalAccount.objects.create(
            identity=self.identity,
            professional_title="Secondary Professional",
        )

        primary = get_primary_account_context(self.identity)

        self.assertIsNotNone(primary)
        self.assertEqual(primary["context_type"], "personal")

    def test_primary_institution_owner_context(self):
        AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.INSTITUTION,
            is_primary=True,
        )
        self.create_institution(
            self.identity,
            "Primary Test Institution",
        )

        primary = get_primary_account_context(self.identity)

        self.assertIsNotNone(primary)
        self.assertEqual(primary["context_type"], "institution")
        self.assertEqual(primary["label"], "Primary Test Institution")

    def test_primary_global_admin_role_is_not_primary_account(self):
        role = AdministrativeRole.objects.create(
            identity=self.identity,
            role_type=AdministrativeRole.RoleType.SUPER_ADMIN,
            is_active=True,
        )
        AdministrativeAssignment.objects.create(
            identity=self.identity,
            role=role,
            is_active=True,
            is_primary=True,
        )

        contexts = get_available_account_contexts(self.identity)
        admin_context = next(
            item for item in contexts
            if item["context_type"] == "global_admin"
        )

        self.assertFalse(admin_context["is_primary"])
        self.assertIsNone(get_primary_account_context(self.identity))

    def test_inactive_account_type_is_not_returned(self):
        AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PERSONAL,
            is_active=False,
        )
        PersonalAccount.objects.create(
            identity=self.identity,
        )

        self.assertEqual(
            get_available_account_contexts(self.identity),
            [],
        )


class TrustedLocationTokenTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="trusted-token-test@example.com",
            mobile_number="01800000991",
        )

    def test_valid_token_can_only_be_consumed_once(self):
        token = issue_trusted_location_verification(self.identity)

        self.assertTrue(
            consume_trusted_location_verification(self.identity, token)
        )
        self.assertFalse(
            consume_trusted_location_verification(self.identity, token)
        )

    def test_expired_token_is_rejected(self):
        token = issue_trusted_location_verification(self.identity)

        TrustedLocationVerification.objects.filter(
            profile=self.identity.security_profile,
        ).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        self.assertFalse(
            consume_trusted_location_verification(self.identity, token)
        )

    def test_empty_token_is_rejected(self):
        self.assertFalse(
            consume_trusted_location_verification(self.identity, "")
        )


class TrustedLocationStateSyncTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from security.views import (
            trusted_location_settings,
            trusted_location_detail,
        )

        self.factory = APIRequestFactory()
        self.force_authenticate = force_authenticate
        self.settings_view = trusted_location_settings
        self.detail_view = trusted_location_detail

        self.identity = UserIdentity.objects.create(
            email="location-sync@example.com",
            mobile_number="01800000999",
        )
        self.profile = SecurityProfile.objects.get(identity=self.identity)
        self.preference = SecurityPreference.objects.get(profile=self.profile)

    def call_settings(self, enabled):
        request = self.factory.patch(
            "/trusted-location-settings/",
            {"restriction_enabled": enabled},
            format="json",
        )
        self.force_authenticate(request, user=self.identity)
        return self.settings_view(request)

    def call_location_update(self, location, enabled):
        request = self.factory.patch(
            f"/trusted-locations/{location.id}/",
            {"is_enabled": enabled},
            format="json",
        )
        self.force_authenticate(request, user=self.identity)
        return self.detail_view(request, location_id=location.id)

    def create_location(self, name, active=True):
        return TrustedLocation.objects.create(
            profile=self.profile,
            name=name,
            latitude="23.810300",
            longitude="90.412500",
            radius_meters=10000,
            is_active=active,
        )

    def test_main_security_can_be_enabled_before_first_location(self):
        response = self.call_settings(True)

        self.preference.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.preference.trusted_location_enabled)

    def test_enabling_one_location_enables_main_security(self):
        location = self.create_location("Home", active=False)

        response = self.call_location_update(location, True)

        self.preference.refresh_from_db()
        location.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(location.is_active)
        self.assertTrue(self.preference.trusted_location_enabled)

    def test_main_security_stays_enabled_while_any_location_is_enabled(self):
        first = self.create_location("Home", active=True)
        second = self.create_location("Office", active=True)
        self.preference.trusted_location_enabled = True
        self.preference.save()

        self.call_location_update(first, False)

        self.preference.refresh_from_db()
        self.assertTrue(self.preference.trusted_location_enabled)
        self.assertTrue(second.is_active)

    def test_all_locations_off_turns_main_security_off(self):
        first = self.create_location("Home", active=True)
        second = self.create_location("Office", active=True)
        self.preference.trusted_location_enabled = True
        self.preference.save()

        self.call_location_update(first, False)
        self.call_location_update(second, False)

        self.preference.refresh_from_db()
        self.assertFalse(self.preference.trusted_location_enabled)

    def test_final_main_off_disables_all_locations_without_deleting(self):
        first = self.create_location("Home", active=True)
        second = self.create_location("Office", active=True)
        self.preference.trusted_location_enabled = True
        self.preference.save()

        response = self.call_settings(False)

        self.preference.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.preference.trusted_location_enabled)
        self.assertFalse(first.is_active)
        self.assertFalse(second.is_active)
        self.assertEqual(
            TrustedLocation.objects.filter(profile=self.profile).count(),
            2,
        )

    def test_main_security_becomes_pending_when_saved_locations_are_all_off(self):
        self.create_location("Home", active=False)

        response = self.call_settings(True)

        self.preference.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.preference.trusted_location_enabled)
        self.assertTrue(self.preference.trusted_location_pending)
        self.assertTrue(response.data["trusted_location_pending"])

    def test_deleting_last_enabled_location_turns_main_security_off(self):
        location = self.create_location("Home", active=True)
        self.preference.trusted_location_enabled = True
        self.preference.save()

        request = self.factory.delete(
            f"/trusted-locations/{location.id}/"
        )
        self.force_authenticate(request, user=self.identity)
        response = self.detail_view(request, location_id=location.id)

        self.preference.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.preference.trusted_location_enabled)
        self.assertFalse(
            TrustedLocation.objects.filter(pk=location.pk).exists()
        )


class TwoFactorServiceTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="twofactor-test@example.com",
            mobile_number="01700000001",
        )
        self.profile = SecurityProfile.objects.get(identity=self.identity)

    def test_generates_ten_unique_recovery_codes(self):
        from security.two_factor import replace_recovery_codes

        codes = replace_recovery_codes(self.profile)

        self.assertEqual(len(codes), 10)
        self.assertEqual(len(set(codes)), 10)
        self.assertEqual(
            self.profile.recovery_codes.filter(used_at__isnull=True).count(),
            10,
        )

    def test_recovery_code_can_only_be_used_once(self):
        from security.two_factor import (
            replace_recovery_codes,
            consume_recovery_code,
        )

        codes = replace_recovery_codes(self.profile)
        code = codes[0]

        self.assertTrue(consume_recovery_code(self.profile, code))
        self.assertFalse(consume_recovery_code(self.profile, code))

    def test_regeneration_invalidates_previous_codes(self):
        from security.two_factor import (
            replace_recovery_codes,
            consume_recovery_code,
        )

        old_codes = replace_recovery_codes(self.profile)
        new_codes = replace_recovery_codes(self.profile)

        self.assertFalse(consume_recovery_code(self.profile, old_codes[0]))
        self.assertTrue(consume_recovery_code(self.profile, new_codes[0]))

    def test_totp_generation_and_verification(self):
        import pyotp
        from security.two_factor import verify_totp_code

        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()

        self.assertTrue(verify_totp_code(secret, code))
        self.assertFalse(verify_totp_code(secret, "12345"))

    def test_totp_secret_encryption_and_decryption(self):
        from security.two_factor import (
            generate_totp_secret,
            encrypt_totp_secret,
            decrypt_totp_secret,
        )

        secret = generate_totp_secret()
        encrypted = encrypt_totp_secret(secret)

        self.assertNotEqual(encrypted, secret)
        self.assertEqual(decrypt_totp_secret(encrypted), secret)



class TotpReplayProtectionTests(TestCase):
    def setUp(self):
        import pyotp
        from security.models import SecurityMethod

        self.identity = UserIdentity.objects.create(
            email="totp-replay@example.com",
            mobile_number="01700000009",
        )
        self.profile = SecurityProfile.objects.get(identity=self.identity)
        self.secret = pyotp.random_base32()
        self.method = SecurityMethod.objects.create(
            profile=self.profile,
            method=SecurityMethod.Method.TOTP,
            status=SecurityMethod.Status.ACTIVE,
            encrypted_secret="test-encrypted-secret",
        )
        self.totp = pyotp.TOTP(self.secret)

    def test_valid_totp_is_accepted_once_only(self):
        from security.two_factor import verify_and_consume_totp_code

        now = timezone.now()
        code = self.totp.at(now)

        self.assertTrue(
            verify_and_consume_totp_code(self.method, self.secret, code, now)
        )
        self.assertFalse(
            verify_and_consume_totp_code(self.method, self.secret, code, now)
        )
        self.method.refresh_from_db()
        self.assertEqual(self.method.last_totp_step, self.totp.timecode(now))

    def test_previously_consumed_step_is_rejected_in_valid_window(self):
        from datetime import datetime, timezone as datetime_timezone
        from security.two_factor import verify_and_consume_totp_code

        first_step = self.totp.timecode(timezone.now())
        first_time = datetime.fromtimestamp(
            first_step * 30 + 1, tz=datetime_timezone.utc
        )
        first_code = self.totp.generate_otp(first_step)
        self.assertTrue(
            verify_and_consume_totp_code(
                self.method, self.secret, first_code, first_time
            )
        )

        next_step_time = datetime.fromtimestamp(
            (first_step + 1) * 30 + 1, tz=datetime_timezone.utc
        )
        self.assertFalse(
            verify_and_consume_totp_code(
                self.method, self.secret, first_code, next_step_time
            )
        )

    def test_new_totp_step_is_accepted(self):
        from datetime import datetime, timezone as datetime_timezone
        from security.two_factor import verify_and_consume_totp_code

        first_step = self.totp.timecode(timezone.now())
        first_time = datetime.fromtimestamp(
            first_step * 30 + 1, tz=datetime_timezone.utc
        )
        self.assertTrue(
            verify_and_consume_totp_code(
                self.method, self.secret,
                self.totp.generate_otp(first_step), first_time
            )
        )

        next_step = first_step + 1
        next_time = datetime.fromtimestamp(
            next_step * 30 + 1, tz=datetime_timezone.utc
        )
        self.assertTrue(
            verify_and_consume_totp_code(
                self.method, self.secret,
                self.totp.generate_otp(next_step), next_time
            )
        )

    def test_invalid_totp_is_rejected_without_consuming_step(self):
        from security.two_factor import verify_and_consume_totp_code

        now = timezone.now()
        self.assertFalse(
            verify_and_consume_totp_code(
                self.method, self.secret, "000000", now
            )
        )
        self.method.refresh_from_db()
        self.assertIsNone(self.method.last_totp_step)


class TotpSetupReplayIntegrationTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from security.two_factor_views import setup_totp, verify_totp_setup

        self.factory = APIRequestFactory()
        self.force_authenticate = force_authenticate
        self.setup_view = setup_totp
        self.verify_view = verify_totp_setup
        self.identity = UserIdentity.objects.create(
            email="totp-setup-replay@example.com",
            mobile_number="01700000010",
        )
        self.profile = SecurityProfile.objects.get(identity=self.identity)

    def call_view(self, view, data=None):
        request = self.factory.post("/two-factor-test/", data or {}, format="json")
        self.force_authenticate(request, user=self.identity)
        return view(request)

    def test_successful_setup_consumes_totp_step(self):
        import pyotp
        from security.models import SecurityMethod

        setup_response = self.call_view(self.setup_view)
        self.assertEqual(setup_response.status_code, 200)
        secret = setup_response.data["secret"]
        code = pyotp.TOTP(secret).now()

        response = self.call_view(self.verify_view, {"code": code})

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        method = SecurityMethod.objects.get(
            profile=self.profile,
            method=SecurityMethod.Method.TOTP,
        )
        self.assertTrue(self.profile.two_factor_enabled)
        self.assertIsNotNone(method.last_totp_step)

    def test_invalid_setup_code_does_not_consume_totp_step(self):
        from security.models import SecurityMethod

        setup_response = self.call_view(self.setup_view)
        self.assertEqual(setup_response.status_code, 200)

        response = self.call_view(self.verify_view, {"code": "000000"})

        self.assertEqual(response.status_code, 400)
        method = SecurityMethod.objects.get(
            profile=self.profile,
            method=SecurityMethod.Method.TOTP,
        )
        self.assertIsNone(method.last_totp_step)


class TwoFactorLockoutTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="twofactor-lockout@example.com",
            mobile_number="01700000002",
        )
        self.profile = SecurityProfile.objects.get(identity=self.identity)

    def test_three_failed_attempts_lock_for_fifteen_minutes(self):
        from datetime import timedelta
        from django.utils import timezone
        from security.two_factor import register_failed_two_factor_attempt

        for attempt in range(3):
            locked, locked_until = register_failed_two_factor_attempt(
                self.profile
            )

        self.profile.refresh_from_db()

        self.assertTrue(locked)
        self.assertIsNotNone(locked_until)
        self.assertEqual(self.profile.two_factor_verification_attempts, 3)
        self.assertGreaterEqual(
            locked_until,
            timezone.now() + timedelta(minutes=14, seconds=59),
        )
        self.assertLessEqual(
            locked_until,
            timezone.now() + timedelta(minutes=15, seconds=1),
        )

    def test_successful_verification_resets_attempts_and_lockout(self):
        from security.two_factor import (
            register_failed_two_factor_attempt,
            reset_two_factor_attempts,
        )

        for _ in range(3):
            register_failed_two_factor_attempt(self.profile)

        reset_two_factor_attempts(self.profile)
        self.profile.refresh_from_db()

        self.assertEqual(self.profile.two_factor_verification_attempts, 0)
        self.assertIsNone(self.profile.two_factor_locked_until)


class PasswordLoginLockoutTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="password-lockout@example.com",
            mobile_number="01700000003",
        )
        self.profile = SecurityProfile.objects.get(
            identity=self.identity,
        )

    def test_three_failed_attempts_lock_for_one_hour(self):
        from datetime import timedelta
        from security.password_login import register_failed_password_attempt

        for _ in range(3):
            result = register_failed_password_attempt(self.profile)

        self.profile.refresh_from_db()

        self.assertFalse(result["disabled"])
        self.assertIsNotNone(result["locked_until"])
        self.assertEqual(self.profile.failed_password_attempts, 3)
        self.assertGreaterEqual(
            result["locked_until"],
            timezone.now() + timedelta(minutes=59, seconds=59),
        )
        self.assertLessEqual(
            result["locked_until"],
            timezone.now() + timedelta(hours=1, seconds=1),
        )

    def test_fourth_failed_attempt_after_expiry_locks_for_six_hours(self):
        from datetime import timedelta
        from security.password_login import register_failed_password_attempt

        for _ in range(3):
            register_failed_password_attempt(self.profile)

        self.profile.refresh_from_db()
        self.profile.password_login_locked_until = (
            timezone.now() - timedelta(seconds=1)
        )
        self.profile.save(update_fields=["password_login_locked_until"])

        result = register_failed_password_attempt(self.profile)

        self.profile.refresh_from_db()

        self.assertEqual(result["attempts"], 4)
        self.assertFalse(result["disabled"])
        self.assertGreaterEqual(
            result["locked_until"],
            timezone.now() + timedelta(hours=5, minutes=59),
        )
        self.assertLessEqual(
            result["locked_until"],
            timezone.now() + timedelta(hours=6, seconds=1),
        )

    def test_fifth_failed_attempt_after_expiry_locks_for_twenty_four_hours(self):
        from datetime import timedelta
        from security.password_login import register_failed_password_attempt

        for expected_attempt in range(1, 5):
            result = register_failed_password_attempt(self.profile)
            if expected_attempt in (3, 4):
                self.profile.refresh_from_db()
                self.profile.password_login_locked_until = (
                    timezone.now() - timedelta(seconds=1)
                )
                self.profile.save(
                    update_fields=["password_login_locked_until"]
                )

        result = register_failed_password_attempt(self.profile)

        self.profile.refresh_from_db()

        self.assertEqual(result["attempts"], 5)
        self.assertFalse(result["disabled"])
        self.assertGreaterEqual(
            result["locked_until"],
            timezone.now() + timedelta(hours=23, minutes=59),
        )
        self.assertLessEqual(
            result["locked_until"],
            timezone.now() + timedelta(hours=24, seconds=1),
        )

    def test_sixth_failed_attempt_disables_password_login(self):
        from datetime import timedelta
        from security.password_login import register_failed_password_attempt

        for attempt in range(1, 6):
            register_failed_password_attempt(self.profile)
            if attempt in (3, 4, 5):
                self.profile.refresh_from_db()
                self.profile.password_login_locked_until = (
                    timezone.now() - timedelta(seconds=1)
                )
                self.profile.save(
                    update_fields=["password_login_locked_until"]
                )

        result = register_failed_password_attempt(self.profile)

        self.profile.refresh_from_db()

        self.assertTrue(result["disabled"])
        self.assertTrue(self.profile.password_login_disabled)
        self.assertEqual(self.profile.failed_password_attempts, 6)

    def test_disabled_password_login_cannot_be_used(self):
        from security.password_login import check_password_login_access

        self.profile.password_login_disabled = True
        self.profile.save(update_fields=["password_login_disabled"])

        result = check_password_login_access(self.profile)

        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "password_login_disabled")

    def test_expired_lockout_allows_next_attempt(self):
        from datetime import timedelta
        from security.password_login import (
            check_password_login_access,
            register_failed_password_attempt,
        )

        for _ in range(3):
            register_failed_password_attempt(self.profile)

        self.profile.refresh_from_db()
        self.profile.password_login_locked_until = (
            timezone.now() - timedelta(seconds=1)
        )
        self.profile.save(update_fields=["password_login_locked_until"])

        result = check_password_login_access(self.profile)

        self.assertTrue(result["allowed"])

    def test_password_reset_clears_all_login_restrictions(self):
        from datetime import timedelta
        from security.password_login import (
            register_failed_password_attempt,
            reset_password_login_attempts,
        )

        self.profile.failed_password_attempts = 6
        self.profile.password_login_disabled = True
        self.profile.password_login_locked_until = (
            timezone.now() + timedelta(hours=1)
        )
        self.profile.save(update_fields=[
            "failed_password_attempts",
            "password_login_disabled",
            "password_login_locked_until",
        ])

        reset_password_login_attempts(self.profile)
        self.profile.refresh_from_db()

        self.assertEqual(self.profile.failed_password_attempts, 0)
        self.assertFalse(self.profile.password_login_disabled)
        self.assertIsNone(self.profile.password_login_locked_until)




class PasswordLoginProtectionStatusTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.identity = UserIdentity.objects.create(
            email="protection-status@example.com",
            mobile_number="01700000999",
        )
        self.profile = SecurityProfile.objects.get(identity=self.identity)
        self.preference = SecurityPreference.objects.get(profile=self.profile)

    def get_status(self):
        from security.views import password_login_protection_status

        request = self.factory.get("/password-login-protection/")
        force_authenticate(request, user=self.identity)
        return password_login_protection_status(request)

    def test_active_password_login_status(self):
        response = self.get_status()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["login_status"], "active")
        self.assertEqual(response.data["failed_attempts"], 0)

    def test_temporary_lockout_status(self):
        self.profile.password_login_locked_until = (
            timezone.now() + timedelta(hours=1)
        )
        self.profile.save(update_fields=["password_login_locked_until"])

        response = self.get_status()
        self.assertEqual(response.data["login_status"], "temporarily_locked")
        self.assertGreater(response.data["remaining_seconds"], 0)

    def test_disabled_password_login_status(self):
        self.profile.password_login_disabled = True
        self.profile.save(update_fields=["password_login_disabled"])

        response = self.get_status()
        self.assertEqual(response.data["login_status"], "disabled")

    def test_login_alert_status(self):
        self.preference.login_alerts_enabled = False
        self.preference.save(update_fields=["login_alerts_enabled"])

        response = self.get_status()
        self.assertFalse(response.data["login_alerts_enabled"])


class LoginAttemptEmailAlertTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="login-alert-test@example.com",
            mobile_number="01700000998",
        )
        self.profile = SecurityProfile.objects.get(identity=self.identity)
        self.preference = SecurityPreference.objects.get(profile=self.profile)

    @patch("security.login_email.send_mail", return_value=1)
    def test_email_is_sent_when_alerts_enabled(self, mocked_mail):
        self.preference.login_alerts_enabled = True
        self.preference.save(update_fields=["login_alerts_enabled"])

        result = send_login_attempt_alert(self.identity, "success")

        self.assertTrue(result)
        mocked_mail.assert_called_once()

    @patch("security.login_email.send_mail", return_value=1)
    def test_email_is_not_sent_when_alerts_disabled(self, mocked_mail):
        self.preference.login_alerts_enabled = False
        self.preference.save(update_fields=["login_alerts_enabled"])

        result = send_login_attempt_alert(self.identity, "success")

        self.assertFalse(result)
        mocked_mail.assert_not_called()

    @patch("security.login_email.send_mail", return_value=1)
    def test_email_is_sent_when_preference_record_missing(self, mocked_mail):
        self.preference.delete()

        result = send_login_attempt_alert(self.identity, "success")

        self.assertTrue(result)
        mocked_mail.assert_called_once()


class RecoveryEmailTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.identity = UserIdentity.objects.create(
            email="recovery-test@example.com",
            mobile_number="01800000888",
        )
        self.profile = SecurityProfile.objects.get(
            identity=self.identity,
        )

    def test_recovery_email_is_not_changed_before_verification(self):
        self.profile.recovery_email = "old-recovery@example.com"
        self.profile.save(update_fields=["recovery_email"])

        with patch("security.recovery_email.send_mail", return_value=1):
            request = self.factory.post(
                "/api/security/recovery-email/",
                {"email": "new-recovery@example.com"},
                format="json",
            )
            force_authenticate(request, user=self.identity)
            response = recovery_email_status(request)

        self.profile.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.profile.recovery_email,
            "old-recovery@example.com",
        )
        self.assertEqual(
            self.profile.pending_recovery_email,
            "new-recovery@example.com",
        )

    def test_otp_is_hashed_and_can_be_verified_once(self):
        with patch(
            "security.recovery_email.send_mail",
            return_value=1,
        ) as mocked_mail:
            success, _ = send_recovery_email_otp(
                self.profile,
                "recovery-otp@example.com",
            )

        self.assertTrue(success)

        verification = RecoveryEmailVerification.objects.get(
            profile=self.profile,
        )
        sent_message = mocked_mail.call_args.kwargs["message"]
        otp = sent_message.split("code is: ")[1].splitlines()[0]

        self.assertNotEqual(verification.otp_hash, otp)
        self.assertTrue(verification.otp_hash.startswith("pbkdf2_"))

        verified, _ = verify_recovery_email_otp(
            self.profile,
            "recovery-otp@example.com",
            otp,
        )
        self.assertTrue(verified)

        verified_again, _ = verify_recovery_email_otp(
            self.profile,
            "recovery-otp@example.com",
            otp,
        )
        self.assertFalse(verified_again)

    def test_three_wrong_attempts_trigger_two_minute_lockout(self):
        with patch(
            "security.recovery_email.send_mail",
            return_value=1,
        ):
            send_recovery_email_otp(
                self.profile,
                "recovery-lock@example.com",
            )

        for _ in range(3):
            verify_recovery_email_otp(
                self.profile,
                "recovery-lock@example.com",
                "000000",
            )

        verification = RecoveryEmailVerification.objects.get(
            profile=self.profile,
        )
        self.assertEqual(verification.failed_attempts, 3)
        self.assertIsNotNone(verification.locked_until)

        verified, message = verify_recovery_email_otp(
            self.profile,
            "recovery-lock@example.com",
            "123456",
        )
        self.assertFalse(verified)
        self.assertIn("Too many", message)

    def test_expired_otp_is_rejected(self):
        with patch(
            "security.recovery_email.send_mail",
            return_value=1,
        ):
            send_recovery_email_otp(
                self.profile,
                "recovery-expired@example.com",
            )

        verification = RecoveryEmailVerification.objects.get(
            profile=self.profile,
        )
        verification.expires_at = timezone.now() - timedelta(seconds=1)
        verification.save(update_fields=["expires_at"])

        verified, message = verify_recovery_email_otp(
            self.profile,
            "recovery-expired@example.com",
            "123456",
        )

        self.assertFalse(verified)
        self.assertIn("expired", message.lower())

    def test_recovery_email_api_verifies_pending_email(self):
        self.profile.pending_recovery_email = "recovery-api@example.com"
        self.profile.save(update_fields=["pending_recovery_email"])

        with patch(
            "security.recovery_email.send_mail",
            return_value=1,
        ) as mocked_mail:
            send_recovery_email_otp(
                self.profile,
                "recovery-api@example.com",
            )

        sent_message = mocked_mail.call_args.kwargs["message"]
        otp = sent_message.split("code is: ")[1].splitlines()[0]

        request = self.factory.post(
            "/api/security/recovery-email/verify/",
            {"otp": otp},
            format="json",
        )
        force_authenticate(request, user=self.identity)
        response = verify_recovery_email(request)

        self.profile.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.profile.recovery_email,
            "recovery-api@example.com",
        )
        self.assertEqual(self.profile.pending_recovery_email, "")


class ChangePasswordTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from security.jwt_authentication import create_versioned_refresh_token

        self.client = APIClient()
        self.identity = UserIdentity.objects.create(
            email="change-password@example.com",
            username="change-password-test",
            status=UserIdentity.Status.ACTIVE,
        )
        self.identity.set_password("Current-Strong!Pass-2026")
        self.identity.save()

        self.profile = SecurityProfile.objects.get(
            identity=self.identity,
        )

        self.old_refresh = create_versioned_refresh_token(self.identity)
        self.old_access = self.old_refresh.access_token

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.old_access}",
        )

        self.url = "/api/security/change-password/"

        self.valid_data = {
            "current_password": "Current-Strong!Pass-2026",
            "new_password": "Deepafy-New!Strong-2026",
            "confirm_password": "Deepafy-New!Strong-2026",
        }

    def test_wrong_current_password_is_rejected(self):
        data = {
            **self.valid_data,
            "current_password": "Wrong-Current-Password",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)
        self.identity.refresh_from_db()
        self.assertTrue(
            self.identity.check_password("Current-Strong!Pass-2026")
        )

    def test_password_confirmation_mismatch_is_rejected(self):
        data = {
            **self.valid_data,
            "confirm_password": "Different-Password!2026",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_same_password_is_rejected(self):
        data = {
            **self.valid_data,
            "new_password": "Current-Strong!Pass-2026",
            "confirm_password": "Current-Strong!Pass-2026",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)

    def test_weak_password_is_rejected(self):
        data = {
            **self.valid_data,
            "new_password": "12345678",
            "confirm_password": "12345678",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)

    @patch("security.password_views.send_password_change_alert")
    def test_successful_change_rotates_tokens_and_resets_password_lockout(
        self,
        send_alert,
    ):
        self.profile.failed_password_attempts = 5
        self.profile.password_login_disabled = True
        self.profile.password_login_locked_until = timezone.now() + timedelta(
            hours=1,
        )
        self.profile.save()

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        self.identity.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertTrue(
            self.identity.check_password("Deepafy-New!Strong-2026")
        )
        self.assertEqual(self.profile.token_version, 1)
        self.assertIsNotNone(self.profile.password_changed_at)
        self.assertEqual(self.profile.failed_password_attempts, 0)
        self.assertFalse(self.profile.password_login_disabled)
        self.assertIsNone(self.profile.password_login_locked_until)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.old_access}",
        )
        old_token_response = self.client.get(
            "/api/security/two-factor/status/",
        )
        self.assertEqual(old_token_response.status_code, 401)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
        )
        new_token_response = self.client.get(
            "/api/security/two-factor/status/",
        )
        self.assertEqual(new_token_response.status_code, 200)

        old_refresh_response = self.client.post(
            "/api/identity/token/refresh/",
            {"refresh": str(self.old_refresh)},
            format="json",
        )
        self.assertEqual(old_refresh_response.status_code, 401)

        send_alert.assert_called_once()

    def enable_totp(self):
        import pyotp
        from security.models import SecurityMethod
        from security.two_factor import encrypt_totp_secret

        secret = pyotp.random_base32()
        method = SecurityMethod.objects.create(
            profile=self.profile,
            method=SecurityMethod.Method.TOTP,
            status=SecurityMethod.Status.ACTIVE,
            is_primary=True,
            encrypted_secret=encrypt_totp_secret(secret),
        )
        self.profile.two_factor_enabled = True
        self.profile.save(update_fields=["two_factor_enabled"])
        return secret, method

    @patch("security.password_views.send_password_change_alert")
    def test_password_change_requires_valid_totp(self, send_alert):
        import pyotp

        secret, method = self.enable_totp()
        data = {
            **self.valid_data,
            "code": pyotp.TOTP(secret).now(),
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 200)
        self.identity.refresh_from_db()
        self.assertTrue(
            self.identity.check_password("Deepafy-New!Strong-2026")
        )
        send_alert.assert_called_once()

    def test_invalid_totp_does_not_change_password(self):
        self.enable_totp()
        data = {
            **self.valid_data,
            "code": "000000",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)
        self.identity.refresh_from_db()
        self.assertTrue(
            self.identity.check_password("Current-Strong!Pass-2026")
        )

    @patch("security.password_views.send_password_change_alert")
    def test_password_change_accepts_single_use_recovery_code(
        self,
        send_alert,
    ):
        from security.two_factor import replace_recovery_codes

        self.enable_totp()
        codes = replace_recovery_codes(self.profile)

        data = {
            **self.valid_data,
            "recovery_code": codes[0],
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 200)

        self.identity.refresh_from_db()
        self.assertTrue(
            self.identity.check_password("Deepafy-New!Strong-2026")
        )
        send_alert.assert_called_once()

    def test_three_invalid_totp_attempts_trigger_fifteen_minute_lockout(self):
        from datetime import timedelta

        self.enable_totp()

        for attempt in range(3):
            response = self.client.post(
                self.url,
                {**self.valid_data, "code": "000000"},
                format="json",
            )

        self.assertEqual(response.status_code, 429)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.two_factor_verification_attempts, 3)
        self.assertIsNotNone(self.profile.two_factor_locked_until)
        self.assertGreaterEqual(
            self.profile.two_factor_locked_until,
            timezone.now() + timedelta(minutes=14, seconds=59),
        )
