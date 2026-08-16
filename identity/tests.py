from django.test import TestCase

from category_engine.models import Category

from .models import (
    AcademicBackground,
    AccountType,
    Hobby,
    PersonalAccount,
    PersonalHobby,
    PersonalInterestedCategory,
    ProfessionalAccount,
    UserIdentity,
    JobExperience,
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

        self.hobby = Hobby.objects.create(
            name="Photography",
            slug="photography",
        )

    def test_hobby_creation(self):
        personal_hobby = PersonalHobby.objects.create(
            personal_account=self.personal_account,
            hobby=self.hobby,
        )

        self.assertEqual(
            personal_hobby.personal_account,
            self.personal_account,
        )
        self.assertEqual(
            personal_hobby.hobby,
            self.hobby,
        )
        self.assertTrue(
            personal_hobby.is_active,
        )

    def test_hobby_string(self):
        personal_hobby = PersonalHobby.objects.create(
            personal_account=self.personal_account,
            hobby=self.hobby,
        )

        self.assertEqual(
            str(personal_hobby),
            f"{self.identity.user_id} - {self.hobby.name}",
        )

    def test_duplicate_hobby_not_allowed(self):
        PersonalHobby.objects.create(
            personal_account=self.personal_account,
            hobby=self.hobby,
        )

        with self.assertRaises(Exception):
            PersonalHobby.objects.create(
                personal_account=self.personal_account,
                hobby=self.hobby,
            )

class AcademicBackgroundTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="academic@example.com",
        )

        self.professional_account = ProfessionalAccount.objects.create(
            identity=self.identity,
            professional_title="Software Engineer",
        )

    def test_academic_background_creation(self):
        academic = AcademicBackground.objects.create(
            professional_account=self.professional_account,
            qualification="Bachelor of Science",
            institution="University of Dhaka",
            field_of_study="Computer Science",
            city="Dhaka",
            result="CGPA 3.75",
        )

        self.assertEqual(
            academic.qualification,
            "Bachelor of Science",
        )
        self.assertEqual(
            academic.institution,
            "University of Dhaka",
        )
        self.assertEqual(
            academic.field_of_study,
            "Computer Science",
        )

    def test_multiple_academic_backgrounds_allowed(self):
        AcademicBackground.objects.create(
            professional_account=self.professional_account,
            qualification="Bachelor of Science",
            institution="University of Dhaka",
        )

        AcademicBackground.objects.create(
            professional_account=self.professional_account,
            qualification="Master of Science",
            institution="BUET",
        )

        self.assertEqual(
            AcademicBackground.objects.filter(
                professional_account=self.professional_account
            ).count(),
            2,
        )

    def test_academic_background_string(self):
        academic = AcademicBackground.objects.create(
            professional_account=self.professional_account,
            qualification="Bachelor of Science",
            institution="University of Dhaka",
        )

        self.assertEqual(
            str(academic),
            "Bachelor of Science - University of Dhaka",
        )

    def test_academic_background_deleted_with_professional_account(self):
        AcademicBackground.objects.create(
            professional_account=self.professional_account,
            qualification="Bachelor of Science",
            institution="University of Dhaka",
        )

        self.professional_account.delete()

        self.assertEqual(
            AcademicBackground.objects.count(),
            0,
        )

class JobExperienceTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="job@example.com",
        )

        self.professional_account = ProfessionalAccount.objects.create(
            identity=self.identity,
            professional_title="Software Engineer",
        )

    def test_job_experience_creation(self):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
            employment_type="Full-time",
            location="Dhaka",
            start_date="2022-01-01",
            end_date="2024-12-31",
            is_current=False,
            description="Backend and API development.",
        )

        self.assertEqual(
            experience.professional_account,
            self.professional_account,
        )
        self.assertEqual(
            experience.company,
            "ABC Technologies",
        )
        self.assertEqual(
            experience.job_title,
            "Software Engineer",
        )
        self.assertEqual(
            experience.employment_type,
            "Full-time",
        )
        self.assertEqual(
            experience.location,
            "Dhaka",
        )

    def test_multiple_job_experiences_allowed(self):
        JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        JobExperience.objects.create(
            professional_account=self.professional_account,
            company="XYZ Solutions",
            job_title="Senior Software Engineer",
        )

        self.assertEqual(
            JobExperience.objects.filter(
                professional_account=self.professional_account
            ).count(),
            2,
        )

    def test_current_job_experience(self):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="Current Company",
            job_title="Senior Engineer",
            is_current=True,
        )

        self.assertTrue(experience.is_current)
        self.assertIsNone(experience.end_date)

    def test_job_experience_string(self):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        self.assertEqual(
            str(experience),
            "Software Engineer - ABC Technologies",
        )

    def test_job_experience_deleted_with_professional_account(self):
        JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        self.professional_account.delete()

        self.assertEqual(
            JobExperience.objects.count(),
            0,
        )

class JobExperienceAPITests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="api-job@example.com",
        )

        self.professional_account = ProfessionalAccount.objects.create(
            identity=self.identity,
            professional_title="Software Engineer",
        )

    def test_job_experience_create_api(self):
        response = self.client.post(
            "/api/identity/job-experiences/create/",
            data={
                "professional_account_id": self.professional_account.id,
                "company": "ABC Technologies",
                "job_title": "Software Engineer",
                "employment_type": "Full-time",
                "location": "Dhaka",
                "start_date": "2022-01-01",
                "is_current": True,
                "description": "Backend development.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        self.assertEqual(
            response.json()["company"],
            "ABC Technologies",
        )

        self.assertTrue(
            JobExperience.objects.filter(
                professional_account=self.professional_account,
                company="ABC Technologies",
            ).exists()
        )

    def test_job_experience_list_api(self):
        JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        response = self.client.get(
            f"/api/identity/{self.identity.id}/job-experiences/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_job_experience_detail_api(self):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        response = self.client.get(
            f"/api/identity/job-experiences/{experience.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["job_title"],
            "Software Engineer",
        )

    def test_job_experience_update_api(self):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        response = self.client.patch(
            f"/api/identity/job-experiences/{experience.id}/update/",
            data={
                "job_title": "Senior Software Engineer",
                "company": "XYZ Solutions",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        experience.refresh_from_db()

        self.assertEqual(
            experience.job_title,
            "Senior Software Engineer",
        )

        self.assertEqual(
            experience.company,
            "XYZ Solutions",
        )

    def test_job_experience_delete_api(self):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        response = self.client.delete(
            f"/api/identity/job-experiences/{experience.id}/delete/"
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            JobExperience.objects.filter(
                id=experience.id
            ).exists()
        )
