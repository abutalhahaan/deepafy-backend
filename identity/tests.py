from django.test import TestCase

from .models import AccountType, PersonalAccount, UserIdentity


class UserIdentityModelTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="test@example.com",
            mobile_number="01700000000",
        )

    def test_identity_creation(self):
        self.assertEqual(
            self.identity.email,
            "test@example.com",
        )
        self.assertEqual(
            self.identity.mobile_number,
            "01700000000",
        )

    def test_identity_uuid_created(self):
        self.assertIsNotNone(
            self.identity.user_id,
        )

    def test_identity_default_status(self):
        self.assertEqual(
            self.identity.status,
            UserIdentity.Status.DRAFT,
        )

    def test_identity_default_active(self):
        self.assertTrue(
            self.identity.is_active,
        )

    def test_identity_string(self):
        self.assertEqual(
            str(self.identity),
            str(self.identity.user_id),
        )


class AccountTypeModelTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="account@example.com",
            mobile_number="01700000001",
        )

    def test_account_type_creation(self):
        account_type = AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PERSONAL,
            is_primary=True,
            is_active=True,
        )

        self.assertEqual(
            account_type.identity,
            self.identity,
        )
        self.assertEqual(
            account_type.account_type,
            "personal",
        )
        self.assertTrue(
            account_type.is_primary,
        )
        self.assertTrue(
            account_type.is_active,
        )

    def test_account_type_string(self):
        account_type = AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.COMPANY,
        )

        self.assertIn(
            "Company Account",
            str(account_type),
        )

    def test_multiple_account_types_allowed(self):
        personal = AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PERSONAL,
        )

        company = AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.COMPANY,
        )

        self.assertEqual(
            self.identity.account_types.count(),
            2,
        )
        self.assertNotEqual(
            personal.account_type,
            company.account_type,
        )


class PersonalAccountModelTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="personal@example.com",
            mobile_number="01700000002",
        )

    def test_personal_account_creation(self):
        personal_account = PersonalAccount.objects.create(
            identity=self.identity,
            is_active=True,
        )

        self.assertEqual(
            personal_account.identity,
            self.identity,
        )
        self.assertTrue(
            personal_account.is_active,
        )

    def test_personal_account_string(self):
        personal_account = PersonalAccount.objects.create(
            identity=self.identity,
        )

        self.assertIn(
            "Personal Account",
            str(personal_account),
        )

    def test_one_personal_account_per_identity(self):
        PersonalAccount.objects.create(
            identity=self.identity,
        )

        with self.assertRaises(Exception):
            PersonalAccount.objects.create(
                identity=self.identity,
            )

class PersonalAccountUpdateTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="personalupdate@example.com",
            mobile_number="01700000005",
        )

        self.personal_account = PersonalAccount.objects.create(
            identity=self.identity,
            is_active=True,
        )

    def test_personal_account_update(self):
        self.personal_account.is_active = False
        self.personal_account.save()

        self.personal_account.refresh_from_db()

        self.assertFalse(
            self.personal_account.is_active,
        )