from django.test import TestCase

from category_engine.models import Category

from .models import (
    AcademicBackground,
    AccountType,
    Hobby,
    JobExperience,
    PersonalAccount,
    PersonalHobby,
    PersonalInterestedCategory,
    ProfessionalAccount,
    ProfessionalSkill,
    Skill,
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

    def test_personal_account_bio(self):
        self.personal_account.bio = (
            "Professional sourcing and marketplace specialist."
        )
        self.personal_account.save()

        self.personal_account.refresh_from_db()

        self.assertEqual(
            self.personal_account.bio,
            "Professional sourcing and marketplace specialist.",
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


class SkillTests(TestCase):
    def setUp(self):
        self.skill = Skill.objects.create(
            name="Python",
            slug="python",
        )

    def test_skill_creation(self):
        self.assertEqual(
            self.skill.name,
            "Python",
        )
        self.assertEqual(
            self.skill.slug,
            "python",
        )
        self.assertTrue(
            self.skill.is_active,
        )

    def test_skill_string(self):
        self.assertEqual(
            str(self.skill),
            "Python",
        )

    def test_multiple_skills_allowed(self):
        Skill.objects.create(
            name="Django",
            slug="django",
        )

        self.assertEqual(
            Skill.objects.count(),
            2,
        )

    def test_skill_deleted(self):
        skill_id = self.skill.id

        self.skill.delete()

        self.assertFalse(
            Skill.objects.filter(
                id=skill_id
            ).exists()
        )


class ProfessionalSkillTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="skill@example.com",
        )

        self.professional_account = ProfessionalAccount.objects.create(
            identity=self.identity,
            professional_title="Software Engineer",
        )

        self.skill = Skill.objects.create(
            name="Python",
            slug="python",
        )

    def test_professional_skill_creation(self):
        professional_skill = ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
            skill_level=ProfessionalSkill.SkillLevel.INTERMEDIATE,
            years_of_experience=3,
        )

        self.assertEqual(
            professional_skill.professional_account,
            self.professional_account,
        )
        self.assertEqual(
            professional_skill.skill,
            self.skill,
        )
        self.assertEqual(
            professional_skill.skill_level,
            ProfessionalSkill.SkillLevel.INTERMEDIATE,
        )
        self.assertEqual(
            professional_skill.years_of_experience,
            3,
        )
        self.assertTrue(
            professional_skill.is_active,
        )

    def test_professional_skill_string(self):
        professional_skill = ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
        )

        self.assertIn(
            "Python",
            str(professional_skill),
        )

    def test_multiple_professional_skills_allowed(self):
        django_skill = Skill.objects.create(
            name="Django",
            slug="django",
        )

        ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
        )

        ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=django_skill,
        )

        self.assertEqual(
            ProfessionalSkill.objects.filter(
                professional_account=self.professional_account
            ).count(),
            2,
        )

    def test_duplicate_professional_skill_not_allowed(self):
        ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
        )

        with self.assertRaises(Exception):
            ProfessionalSkill.objects.create(
                professional_account=self.professional_account,
                skill=self.skill,
            )

    def test_professional_skill_deleted_with_professional_account(self):
        ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
        )

        self.professional_account.delete()

        self.assertEqual(
            ProfessionalSkill.objects.count(),
            0,
        )


class SkillAPITests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="api-skill@example.com",
        )

        self.professional_account = ProfessionalAccount.objects.create(
            identity=self.identity,
            professional_title="Software Engineer",
        )

        self.skill = Skill.objects.create(
            name="Python",
            slug="python",
        )

    def test_skill_create_api(self):
        response = self.client.post(
            "/api/identity/skills/create/",
            data={
                "name": "Django",
                "slug": "django",
            },
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.json()["name"],
            "Django",
        )

        self.assertTrue(
            Skill.objects.filter(
                name="Django"
            ).exists()
        )

    def test_skill_list_api(self):
        response = self.client.get(
            "/api/identity/skills/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["count"],
            1,
        )

    def test_professional_skill_create_api(self):
        response = self.client.post(
            "/api/identity/professional-skills/create/",
            data={
                "professional_account_id":
                    self.professional_account.id,
                "skill_id": self.skill.id,
                "skill_level":
                    ProfessionalSkill.SkillLevel.EXPERT,
                "years_of_experience": 5,
            },
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.json()["skill_name"],
            "Python",
        )

        self.assertEqual(
            response.json()["years_of_experience"],
            5,
        )

    def test_professional_skill_list_api(self):
        ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
        )

        response = self.client.get(
            f"/api/identity/{self.identity.id}/professional-skills/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["count"],
            1,
        )

    def test_professional_skill_detail_api(self):
        professional_skill = ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
        )

        response = self.client.get(
            f"/api/identity/professional-skills/{professional_skill.id}/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["skill_name"],
            "Python",
        )

    def test_professional_skill_update_api(self):
        professional_skill = ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
            skill_level=ProfessionalSkill.SkillLevel.INTERMEDIATE,
            years_of_experience=2,
        )

        response = self.client.patch(
            f"/api/identity/professional-skills/{professional_skill.id}/update/",
            data={
                "skill_level":
                    ProfessionalSkill.SkillLevel.EXPERT,
                "years_of_experience": 6,
            },
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        professional_skill.refresh_from_db()

        self.assertEqual(
            professional_skill.skill_level,
            ProfessionalSkill.SkillLevel.EXPERT,
        )

        self.assertEqual(
            professional_skill.years_of_experience,
            6,
        )

    def test_professional_skill_delete_api(self):
        professional_skill = ProfessionalSkill.objects.create(
            professional_account=self.professional_account,
            skill=self.skill,
        )

        response = self.client.delete(
            f"/api/identity/professional-skills/{professional_skill.id}/delete/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            ProfessionalSkill.objects.filter(
                id=professional_skill.id
            ).exists()
        )
