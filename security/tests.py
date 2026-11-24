from django.test import TestCase

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
