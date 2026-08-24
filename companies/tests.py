from django.test import TestCase

from identity.models import UserIdentity

from .models import (
    AdministrativeAssignment,
    AdministrativeRole,
    Country,
    CountryDepartment,
    Company,
    CompanyRelationship,
    Region,
)


class CompanyModelTests(TestCase):
    def setUp(self):
        self.organization = Company.objects.create(
            name="Test Company",
            company_type="manufacturer",
            country="Bangladesh",
            business_email="test@example.com",
            business_mobile_number="01700000000",
            registered_address="Dhaka, Bangladesh",
            primary_contact_person="Abu Talha",
        )

    def test_organization_creation(self):
        self.assertEqual(
            self.organization.name,
            "Test Company",
        )
        self.assertEqual(
            self.organization.company_type,
            "manufacturer",
        )
        self.assertEqual(
            self.organization.country,
            "Bangladesh",
        )

    def test_organization_uuid_created(self):
        self.assertIsNotNone(
            self.organization.company_id,
        )

    def test_organization_string(self):
        self.assertEqual(
            str(self.organization),
            "Test Company",
        )


class CompanyRelationshipTests(TestCase):
    def setUp(self):
        self.organization = Company.objects.create(
            name="Test Company",
            company_type="manufacturer",
            country="Bangladesh",
            business_email="test@example.com",
            business_mobile_number="01700000000",
            registered_address="Dhaka, Bangladesh",
            primary_contact_person="Abu Talha",
        )

        self.identity = UserIdentity.objects.create(
            email="employee@example.com",
            mobile_number="01700000001",
        )

    def test_relationship_creation(self):
        relationship = CompanyRelationship.objects.create(
            company=self.organization,
            identity=self.identity,
            relationship_type=(
                CompanyRelationship.RelationshipType.EMPLOYEE
            ),
            membership_status=(
                CompanyRelationship.MembershipStatus.ACTIVE
            ),
        )

        self.assertEqual(
            relationship.company,
            self.organization,
        )
        self.assertEqual(
            relationship.identity,
            self.identity,
        )
        self.assertEqual(
            relationship.relationship_type,
            "employee",
        )
        self.assertEqual(
            relationship.membership_status,
            "active",
        )


class AdministrativeRoleTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="admin@example.com",
            mobile_number="01700000002",
        )

    def test_administrative_role_creation(self):
        role = AdministrativeRole.objects.create(
            identity=self.identity,
            role_type=AdministrativeRole.RoleType.SUPER_ADMIN,
            is_active=True,
        )

        self.assertEqual(
            role.identity,
            self.identity,
        )
        self.assertEqual(
            role.role_type,
            "super_admin",
        )
        self.assertTrue(role.is_active)

    def test_administrative_role_string(self):
        role = AdministrativeRole.objects.create(
            identity=self.identity,
            role_type=AdministrativeRole.RoleType.OWNER,
        )

        self.assertIn(
            "Owner",
            str(role),
        )


class AdministrativeAssignmentTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="staff@example.com",
            mobile_number="01700000003",
        )

        self.boss = UserIdentity.objects.create(
            email="boss@example.com",
            mobile_number="01700000004",
        )

        self.role = AdministrativeRole.objects.create(
            identity=self.identity,
            role_type=(
                AdministrativeRole.RoleType.GLOBAL_DEPARTMENT_ADMIN
            ),
        )

    def test_assignment_creation(self):
        assignment = AdministrativeAssignment.objects.create(
            identity=self.identity,
            role=self.role,
            reporting_boss=self.boss,
            is_primary=True,
            is_active=True,
        )

        self.assertEqual(
            assignment.identity,
            self.identity,
        )
        self.assertEqual(
            assignment.role,
            self.role,
        )
        self.assertEqual(
            assignment.reporting_boss,
            self.boss,
        )
        self.assertTrue(
            assignment.is_primary,
        )
        self.assertTrue(
            assignment.is_active,
        )

    def test_assignment_without_reporting_boss(self):
        assignment = AdministrativeAssignment.objects.create(
            identity=self.identity,
            role=self.role,
        )

        self.assertIsNone(
            assignment.reporting_boss,
        )


class RegionCountryDepartmentTests(TestCase):
    def setUp(self):
        self.region = Region.objects.create(
            name="South Asia",
        )

        self.country = Country.objects.create(
            region=self.region,
            name="Bangladesh",
            code="BD",
        )

        self.department = CountryDepartment.objects.create(
            country=self.country,
            name="Textile Department",
            code="TEXTILE",
        )

    def test_region_creation(self):
        self.assertEqual(
            self.region.name,
            "South Asia",
        )
        self.assertTrue(
            self.region.is_active,
        )

    def test_country_creation(self):
        self.assertEqual(
            self.country.name,
            "Bangladesh",
        )
        self.assertEqual(
            self.country.code,
            "BD",
        )
        self.assertEqual(
            self.country.region,
            self.region,
        )

    def test_department_creation(self):
        self.assertEqual(
            self.department.name,
            "Textile Department",
        )
        self.assertEqual(
            self.department.code,
            "TEXTILE",
        )
        self.assertEqual(
            self.department.country,
            self.country,
        )

    def test_department_string(self):
        self.assertEqual(
            str(self.department),
            "Bangladesh - Textile Department",
        )