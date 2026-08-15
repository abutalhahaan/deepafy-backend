from django.test import TestCase

from category_engine.models import Category

from .models import (
    AccountType,
    PersonalAccount,
    PersonalHobby,
    PersonalInterestedCategory,
    UserIdentity,
)


class UserIdentityTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="test@example.com",
            mobile_number="01700000000",
            status=UserIdentity.Status.ACTIVE,
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
        self.assertEqual(
            self.identity.status,
            "active",
        )

    def test_identity_uuid_created(self):
        self.assertIsNotNone(
            self.identity.user_id,
        )

    def test_identity_string(self):
        self.assertEqual(
            str(self.identity),
            str(self.identity.user_id),
        )


class AccountTypeTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="account@example.com",
        )

    def test_account_type_creation(self):
        account_type = AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PERSONAL,
            is_primary=True,
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
            account_type=AccountType.Type.PERSONAL,
        )

        self.assertIn(
            "Personal Account",
            str(account_type),
        )


class PersonalAccountTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="personal@example.com",
        )

        self.personal_account = PersonalAccount.objects.create(
            identity=self.identity,
        )

    def test_personal_account_creation(self):
        self.assertEqual(
            self.personal_account.identity,
            self.identity,
        )
        self.assertTrue(
            self.personal_account.is_active,
        )

    def test_personal_account_string(self):
        self.assertEqual(
            str(self.personal_account),
            f"Personal Account - {self.identity.user_id}",
        )


class PersonalInterestedCategoryTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="interested@example.com",
        )

        self.personal_account = PersonalAccount.objects.create(
            identity=self.identity,
        )

        self.category = Category.objects.create(
            name="T-Shirts",
            slug="t-shirts",
        )

    def test_interested_category_creation(self):
        interested_category = (
            PersonalInterestedCategory.objects.create(
                personal_account=self.personal_account,
                category=self.category,
            )
        )

        self.assertEqual(
            interested_category.personal_account,
            self.personal_account,
        )
        self.assertEqual(
            interested_category.category,
            self.category,
        )
        self.assertTrue(
            interested_category.is_active,
        )

    def test_interested_category_string(self):
        interested_category = (
            PersonalInterestedCategory.objects.create(
                personal_account=self.personal_account,
                category=self.category,
            )
        )

        self.assertEqual(
            str(interested_category),
            (
                f"{self.identity.user_id} - "
                f"{self.category.name}"
            ),
        )

    def test_duplicate_interested_category_not_allowed(self):
        PersonalInterestedCategory.objects.create(
            personal_account=self.personal_account,
            category=self.category,
        )

        with self.assertRaises(Exception):
            PersonalInterestedCategory.objects.create(
                personal_account=self.personal_account,
                category=self.category,
            )


class PersonalHobbyTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="hobby@example.com",
        )

        self.personal_account = PersonalAccount.objects.create(
            identity=self.identity,
        )

    def test_hobby_creation(self):
        hobby = PersonalHobby.objects.create(
            personal_account=self.personal_account,
            name="Photography",
        )

        self.assertEqual(
            hobby.personal_account,
            self.personal_account,
        )
        self.assertEqual(
            hobby.name,
            "Photography",
        )
        self.assertTrue(
            hobby.is_active,
        )

    def test_hobby_string(self):
        hobby = PersonalHobby.objects.create(
            personal_account=self.personal_account,
            name="Traveling",
        )

        self.assertEqual(
            str(hobby),
            f"{self.identity.user_id} - Traveling",
        )

    def test_duplicate_hobby_not_allowed(self):
        PersonalHobby.objects.create(
            personal_account=self.personal_account,
            name="Reading",
        )

        with self.assertRaises(Exception):
            PersonalHobby.objects.create(
                personal_account=self.personal_account,
                name="Reading",
            )