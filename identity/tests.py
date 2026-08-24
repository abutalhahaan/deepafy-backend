import io
import json

from PIL import Image

from rest_framework_simplejwt.tokens import RefreshToken

from django.core.files.uploadedfile import SimpleUploadedFile

from django.test import TestCase

from category_engine.models import Category

from companies.models import Country, Region

from .models import (
    AcademicBackground,
    AccountType,
    Hobby,
    JobExperience,
    Language,
    PersonalAccount,
    PersonalHobby,
    PersonalInterestedCategory,
    PersonalLanguage,
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
        self.assertEqual(self.identity.email, "test@example.com")
        self.assertEqual(self.identity.mobile_number, "01700000000")
        self.assertEqual(self.identity.status, "active")

    def test_identity_uuid_created(self):
        self.assertIsNotNone(self.identity.user_id)

    def test_identity_string(self):
        self.assertEqual(
            str(self.identity),
            self.identity.email,
        )


class UserIdentityAPITests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="api@example.com",
            mobile_number="01700000000",
            status=UserIdentity.Status.ACTIVE,
        )  

    def test_identity_update_api(self):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.patch(
            f"/api/identity/{self.identity.id}/update/",
            data={
                "mobile_number":
                    "01800000000",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["mobile_number"],
            "01800000000",
        )              

    def test_identity_delete_api(self):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.delete(
            f"/api/identity/{self.identity.id}/delete/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            UserIdentity.objects.filter(
                id=self.identity.id
            ).exists()
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

        self.assertEqual(account_type.identity, self.identity)
        self.assertEqual(account_type.account_type, "personal")
        self.assertTrue(account_type.is_primary)
        self.assertTrue(account_type.is_active)

    def test_account_type_string(self):
        account_type = AccountType.objects.create(
            identity=self.identity,
            account_type=AccountType.Type.PERSONAL,
        )

        self.assertIn("Personal Account", str(account_type))

class AccountTypeAPITests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="account-api@example.com",
        )      

    def test_account_type_create_api(self):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.post(
            "/api/identity/account-types/create/",
            data={
                "identity_id": self.identity.id,
                "account_type":
                    AccountType.Type.PERSONAL,
                "is_primary": True,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.json()["account_type"],
            AccountType.Type.PERSONAL,
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
        self.assertTrue(self.personal_account.is_active)

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


class PersonalAccountAPITests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="personal-api@example.com",
        )

        self.personal_account = PersonalAccount.objects.create(
            identity=self.identity,
        )

    def test_personal_account_update_api(self):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.patch(
            f"/api/identity/{self.identity.id}/personal-account/update/",
            data={
                "display_name": "Abu Talha",
                "bio": "Deepafy developer",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["display_name"],
            "Abu Talha",
        )

        self.assertEqual(
            response.json()["bio"],
            "Deepafy developer",
        )

    def test_other_user_cannot_update_personal_account(self):
        other_identity = UserIdentity.objects.create(
            email="other-user@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.patch(
            f"/api/identity/{self.identity.id}/personal-account/update/",
            data={
                "display_name": "Unauthorized User",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )   

    def test_unauthenticated_user_cannot_update_personal_account_photos(
        self,
    ):
        response = self.client.post(
            f"/api/identity/{self.identity.id}/personal-account/photos/",
        )

        self.assertEqual(
            response.status_code,
            401,
        )        

    def test_other_user_cannot_update_personal_account_photos(self):
        other_identity = UserIdentity.objects.create(
            email="other-photo-user@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.post(
            f"/api/identity/{self.identity.id}/personal-account/photos/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )    

    def test_owner_can_update_personal_account_photos(self):
        refresh = RefreshToken.for_user(
            self.identity
        )

        image_file = io.BytesIO()

        image = Image.new(
            "RGB",
            (100, 100),
            "white",
        )

        image.save(
            image_file,
            format="JPEG",
        )

        image_file.seek(0)

        uploaded_image = SimpleUploadedFile(
            "profile.jpg",
            image_file.getvalue(),
            content_type="image/jpeg",
        )   

        response = self.client.post(
            f"/api/identity/{self.identity.id}/personal-account/photos/",
            data={
                "profile_photo": uploaded_image,
            },
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )            

    def test_personal_account_create_api(self):
        new_identity = UserIdentity.objects.create(
            email="personal-create-api@example.com",
        )

        refresh = RefreshToken.for_user(
            new_identity
        )

        response = self.client.post(
            "/api/identity/personal-accounts/create/",
            data={
                "identity_id": new_identity.id,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.json()["identity_id"],
            new_identity.id,
        )

class PersonalLanguageTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="language@example.com",
        )

        self.personal_account = PersonalAccount.objects.create(
            identity=self.identity,
        )

        self.language = Language.objects.create(
            name="English",
            code="en",
        )

    def test_language_creation(self):
        self.assertEqual(self.language.name, "English")
        self.assertEqual(self.language.code, "en")
        self.assertTrue(self.language.is_active)

    def test_language_string(self):
        self.assertEqual(
            str(self.language),
            "English",
        )

    def test_personal_language_creation(self):
        personal_language = PersonalLanguage.objects.create(
            personal_account=self.personal_account,
            language=self.language,
            proficiency="fluent",
        )

        self.assertEqual(
            personal_language.personal_account,
            self.personal_account,
        )

        self.assertEqual(
            personal_language.language,
            self.language,
        )

        self.assertEqual(
            personal_language.proficiency,
            "fluent",
        )

        self.assertTrue(personal_language.is_active)

    def test_personal_language_string(self):
        personal_language = PersonalLanguage.objects.create(
            personal_account=self.personal_account,
            language=self.language,
            proficiency="fluent",
        )

        self.assertEqual(
            str(personal_language),
            (
                f"{self.identity.user_id} - "
                f"{self.language.name}"
            ),
        )

    def test_multiple_personal_languages_allowed(self):
        second_language = Language.objects.create(
            name="Bangla",
            code="bn",
        )

        PersonalLanguage.objects.create(
            personal_account=self.personal_account,
            language=self.language,
            proficiency="fluent",
        )

        PersonalLanguage.objects.create(
            personal_account=self.personal_account,
            language=second_language,
            proficiency="native",
        )

        self.assertEqual(
            PersonalLanguage.objects.filter(
                personal_account=self.personal_account
            ).count(),
            2,
        )

    def test_duplicate_personal_language_not_allowed(self):
        PersonalLanguage.objects.create(
            personal_account=self.personal_account,
            language=self.language,
            proficiency="fluent",
        )

        with self.assertRaises(Exception):
            PersonalLanguage.objects.create(
                personal_account=self.personal_account,
                language=self.language,
                proficiency="fluent",
            )

    def test_language_detail_patch_requires_authentication(self):
        personal_language = PersonalLanguage.objects.create(
            personal_account=self.personal_account,
            language=self.language,
            proficiency="fluent",
        )

        response = self.client.patch(
            f"/api/identity/languages/{personal_language.id}/",
            data=json.dumps(
                {
                    "proficiency": "native",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )


    def test_language_detail_patch_other_user_forbidden(self):
        personal_language = PersonalLanguage.objects.create(
            personal_account=self.personal_account,
            language=self.language,
            proficiency="fluent",
        )

        other_identity = UserIdentity.objects.create(
            email="other@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.patch(
            f"/api/identity/languages/{personal_language.id}/",
            data=json.dumps(
                {
                    "proficiency": "native",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )


    def test_language_detail_patch_owner_allowed(self):
        personal_language = PersonalLanguage.objects.create(
            personal_account=self.personal_account,
            language=self.language,
            proficiency="fluent",
        )

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.patch(
            f"/api/identity/languages/{personal_language.id}/",
            data=json.dumps(
                {
                    "proficiency": "native",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        personal_language.refresh_from_db()

        self.assertEqual(
            personal_language.proficiency,
            "native",
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

        self.assertTrue(interested_category.is_active)

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

    def test_interested_category_list_api(self):
        PersonalInterestedCategory.objects.create(
            personal_account=self.personal_account,
            category=self.category,
        )

        response = self.client.get(
            f"/api/identity/{self.personal_account.id}/"
            "interested-categories/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["personal_account_id"],
            self.personal_account.id,
        )

        self.assertEqual(
            data["count"],
            1,
        )

        self.assertEqual(
            data["results"][0]["category"]["id"],
            self.category.id,
        )


    def test_interested_category_add_api(self):
        response = self.client.post(
            f"/api/identity/{self.personal_account.id}/"
            "interested-categories/add/",
            data=json.dumps(
                {
                    "category_id": self.category.id,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            PersonalInterestedCategory.objects.filter(
                personal_account=self.personal_account,
                category=self.category,
            ).exists()
        )


    def test_interested_category_remove_api(self):
        PersonalInterestedCategory.objects.create(
            personal_account=self.personal_account,
            category=self.category,
        )

        response = self.client.delete(
            f"/api/identity/{self.personal_account.id}/"
            f"interested-categories/{self.category.id}/remove/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            PersonalInterestedCategory.objects.filter(
                personal_account=self.personal_account,
                category=self.category,
            ).exists()
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

        self.assertTrue(personal_hobby.is_active)

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

        self.personal_account = PersonalAccount.objects.create(
            identity=self.identity,
        )

        self.region = Region.objects.create(
            name="Asia",
        )

        self.country = Country.objects.create(
            region=self.region,
            name="Bangladesh",
            code="BD",
            phone_code="+880",
        )

    def test_academic_background_creation(self):
        academic = AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="University of Dhaka",
            institution_type="University",
            country=self.country,
            education_level="Undergraduate",
            degree_certificate="Bachelor of Science",
            field_of_study="Computer Science",
            specialization="Software Engineering",
            start_year=2018,
            end_year=2022,
            is_currently_studying=False,
            result_type="CGPA",
            result="3.75",
            description="Computer Science program.",
        )

        self.assertEqual(
            academic.institution_name,
            "University of Dhaka",
        )

        self.assertEqual(
            academic.degree_certificate,
            "Bachelor of Science",
        )

        self.assertEqual(
            academic.field_of_study,
            "Computer Science",
        )

        self.assertEqual(
            academic.country,
            self.country,
        )

    def test_multiple_academic_backgrounds_allowed(self):
        AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="University of Dhaka",
            institution_type="University",
            country=self.country,
            education_level="Undergraduate",
            degree_certificate="Bachelor of Science",
            start_year=2018,
            end_year=2022,
        )

        AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="BUET",
            institution_type="University",
            country=self.country,
            education_level="Postgraduate",
            degree_certificate="Master of Science",
            start_year=2023,
            end_year=2025,
        )

        self.assertEqual(
            AcademicBackground.objects.filter(
                personal_account=self.personal_account,
            ).count(),
            2,
        )

    def test_academic_background_string(self):
        academic = AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="University of Dhaka",
            institution_type="University",
            country=self.country,
            education_level="Undergraduate",
            degree_certificate="Bachelor of Science",
            start_year=2018,
        )

        self.assertEqual(
            str(academic),
            "Bachelor of Science - University of Dhaka",
        )

    def test_academic_background_deleted_with_personal_account(self):
        AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="University of Dhaka",
            institution_type="University",
            country=self.country,
            education_level="Undergraduate",
            degree_certificate="Bachelor of Science",
            start_year=2018,
        )

        self.personal_account.delete()

        self.assertEqual(
            AcademicBackground.objects.count(),
            0,
        )


class ProfessionalAccountAPITests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="professional@example.com",
        )

        self.professional_account = (
            ProfessionalAccount.objects.create(
                identity=self.identity,
                professional_title="Software Engineer",
            )
        )

    def test_professional_account_update_requires_authentication(
        self,
    ):
        response = self.client.patch(
            f"/api/identity/{self.identity.id}/professional-account/update/",
            data=json.dumps(
                {
                    "professional_title":
                        "Senior Software Engineer",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_professional_account_update_other_user_forbidden(
        self,
    ):
        other_identity = UserIdentity.objects.create(
            email="other-professional@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.patch(
            f"/api/identity/{self.identity.id}/professional-account/update/",
            data=json.dumps(
                {
                    "professional_title":
                        "Senior Software Engineer",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_professional_account_update_owner_allowed(
        self,
    ):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.patch(
            f"/api/identity/{self.identity.id}/professional-account/update/",
            data=json.dumps(
                {
                    "professional_title":
                        "Senior Software Engineer",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.professional_account.refresh_from_db()

        self.assertEqual(
            self.professional_account.professional_title,
            "Senior Software Engineer",
        )

    def test_professional_account_create_owner_allowed(
        self,
    ):
        new_identity = UserIdentity.objects.create(
            email="professional-create@example.com",
        )

        refresh = RefreshToken.for_user(
            new_identity
        )

        response = self.client.post(
            "/api/identity/professional-accounts/create/",
            data={
                "identity_id": new_identity.id,
                "professional_title":
                    "Software Engineer",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.json()["identity_id"],
            new_identity.id,
        )


    def test_other_user_cannot_create_professional_account(
        self,
    ):
        target_identity = UserIdentity.objects.create(
            email="target-professional@example.com",
        )

        other_identity = UserIdentity.objects.create(
            email="other-professional-create@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.post(
            "/api/identity/professional-accounts/create/",
            data={
                "identity_id": target_identity.id,
                "professional_title":
                    "Unauthorized Professional",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
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

    def test_job_experience_create_requires_authentication(
        self,
    ):
        response = self.client.post(
            "/api/identity/job-experiences/create/",
            data=json.dumps(
                {
                    "professional_account_id":
                        self.professional_account.id,
                    "company": "ABC Technologies",
                    "job_title": "Software Engineer",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_other_user_cannot_create_job_experience(
        self,
    ):
        other_identity = UserIdentity.objects.create(
            email="other-job-create@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.post(
            "/api/identity/job-experiences/create/",
            data=json.dumps(
                {
                    "professional_account_id":
                        self.professional_account.id,
                    "company": "Unauthorized Company",
                    "job_title": "Unauthorized Job",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )        

    def test_job_experience_create_api(self):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.post(
            "/api/identity/job-experiences/create/",
            data=json.dumps(
                {
                    "professional_account_id":
                        self.professional_account.id,
                    "company": "ABC Technologies",
                    "job_title": "Software Engineer",
                    "employment_type": "Full-time",
                    "location": "Dhaka",
                    "start_date": "2022-01-01",
                    "is_current": True,
                    "description": "Backend development.",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
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

    def test_job_experience_update_requires_authentication(
        self,
    ):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        response = self.client.patch(
            f"/api/identity/job-experiences/"
            f"{experience.id}/update/",
            data=json.dumps(
                {
                    "job_title": "Unauthorized Update",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )        

    def test_other_user_cannot_update_job_experience(
        self,
    ):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        other_identity = UserIdentity.objects.create(
            email="other-job-update@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.patch(
            f"/api/identity/job-experiences/{experience.id}/update/",
            data=json.dumps(
                {
                    "job_title":
                        "Unauthorized Update",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )        

    def test_job_experience_update_api(self):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.patch(
            f"/api/identity/job-experiences/{experience.id}/update/",
            data=json.dumps(
                {
                    "job_title":
                        "Senior Software Engineer",
                    "company":
                        "XYZ Solutions",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        experience.refresh_from_db()

        self.assertEqual(
            experience.job_title,
            "Senior Software Engineer",
        )

        self.assertEqual(
            experience.company,
            "XYZ Solutions",
        )    

    def test_job_experience_delete_requires_authentication(
        self,
    ):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        response = self.client.delete(
            f"/api/identity/job-experiences/"
            f"{experience.id}/delete/",
        )

        self.assertEqual(
            response.status_code,
            401,
        )        

    def test_other_user_cannot_delete_job_experience(
        self,
    ):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        other_identity = UserIdentity.objects.create(
            email="other-job-delete@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.delete(
            f"/api/identity/job-experiences/{experience.id}/delete/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )        

    def test_job_experience_delete_api(self):
        experience = JobExperience.objects.create(
            professional_account=self.professional_account,
            company="ABC Technologies",
            job_title="Software Engineer",
        )

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.delete(
            f"/api/identity/job-experiences/{experience.id}/delete/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

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
        self.assertEqual(self.skill.name, "Python")
        self.assertEqual(self.skill.slug, "python")
        self.assertTrue(self.skill.is_active)

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
        refresh = RefreshToken.for_user(
            self.identity
        )

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
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
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

        self.assertEqual(response.status_code, 200)

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

        self.assertEqual(response.status_code, 200)

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

        refresh = RefreshToken.for_user(
            self.identity
        )        

        response = self.client.patch(
            f"/api/identity/professional-skills/{professional_skill.id}/update/",
            data={
                "skill_level":
                    ProfessionalSkill.SkillLevel.EXPERT,
                "years_of_experience": 6,
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(response.status_code, 200)

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

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.delete(
            f"/api/identity/professional-skills/{professional_skill.id}/delete/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
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


class ProfessionalSkillAPITests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="api-professional-skill@example.com",
        )

        self.professional_account = (
            ProfessionalAccount.objects.create(
                identity=self.identity,
                professional_title="Software Engineer",
            )
        )

        self.skill = Skill.objects.create(
            name="Python",
            slug="python",
        )

    def test_professional_skill_create_requires_authentication(
        self,
    ):
        response = self.client.post(
            "/api/identity/professional-skills/create/",
            data=json.dumps(
                {
                    "professional_account_id":
                        self.professional_account.id,
                    "skill_id":
                        self.skill.id,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_other_user_cannot_create_professional_skill(
        self,
    ):
        other_identity = UserIdentity.objects.create(
            email="other-professional-skill@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.post(
            "/api/identity/professional-skills/create/",
            data=json.dumps(
                {
                    "professional_account_id":
                        self.professional_account.id,
                    "skill_id":
                        self.skill.id,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_create_professional_skill(
        self,
    ):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.post(
            "/api/identity/professional-skills/create/",
            data=json.dumps(
                {
                    "professional_account_id":
                        self.professional_account.id,
                    "skill_id":
                        self.skill.id,
                    "skill_level":
                        ProfessionalSkill.SkillLevel.EXPERT,
                    "years_of_experience": 5,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            201,
        )

    def test_other_user_cannot_update_professional_skill(
        self,
    ):
        professional_skill = (
            ProfessionalSkill.objects.create(
                professional_account=
                    self.professional_account,
                skill=self.skill,
            )
        )

        other_identity = UserIdentity.objects.create(
            email="other-professional-skill-update@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.patch(
            f"/api/identity/professional-skills/"
            f"{professional_skill.id}/update/",
            data=json.dumps(
                {
                    "years_of_experience": 10,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_update_professional_skill(
        self,
    ):
        professional_skill = (
            ProfessionalSkill.objects.create(
                professional_account=
                    self.professional_account,
                skill=self.skill,
                years_of_experience=2,
            )
        )

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.patch(
            f"/api/identity/professional-skills/"
            f"{professional_skill.id}/update/",
            data=json.dumps(
                {
                    "years_of_experience": 6,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_other_user_cannot_delete_professional_skill(
        self,
    ):
        professional_skill = (
            ProfessionalSkill.objects.create(
                professional_account=
                    self.professional_account,
                skill=self.skill,
            )
        )

        other_identity = UserIdentity.objects.create(
            email="other-professional-skill-delete@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.delete(
            f"/api/identity/professional-skills/"
            f"{professional_skill.id}/delete/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_delete_professional_skill(
        self,
    ):
        professional_skill = (
            ProfessionalSkill.objects.create(
                professional_account=
                    self.professional_account,
                skill=self.skill,
            )
        )

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.delete(
            f"/api/identity/professional-skills/"
            f"{professional_skill.id}/delete/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )


class AcademicBackgroundAPITests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="api-academic@example.com",
        )

        self.personal_account = (
            PersonalAccount.objects.create(
                identity=self.identity,
            )
        )

        self.region = Region.objects.create(
            name="Asia",
        )

        self.country = Country.objects.create(
            region=self.region,
            name="Bangladesh",
            code="BD",
        )

    def test_academic_background_create_requires_authentication(
        self,
    ):
        response = self.client.post(
            "/api/identity/academic-backgrounds/create/",
            data=json.dumps(
                {
                    "personal_account_id":
                        self.personal_account.id,
                    "institution_name":
                        "Dhaka University",
                    "institution_type":
                        "University",
                    "country_id":
                        self.country.id,
                    "education_level":
                        "Bachelor",
                    "degree_certificate":
                        "BSc",
                    "start_year":
                        2020,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_other_user_cannot_create_academic_background(
        self,
    ):
        other_identity = UserIdentity.objects.create(
            email="other-academic-create@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.post(
            "/api/identity/academic-backgrounds/create/",
            data=json.dumps(
                {
                    "personal_account_id":
                        self.personal_account.id,
                    "institution_name":
                        "Dhaka University",
                    "institution_type":
                        "University",
                    "country_id":
                        self.country.id,
                    "education_level":
                        "Bachelor",
                    "degree_certificate":
                        "BSc",
                    "start_year":
                        2020,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_create_academic_background(
        self,
    ):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.post(
            "/api/identity/academic-backgrounds/create/",
            data=json.dumps(
                {
                    "personal_account_id":
                        self.personal_account.id,
                    "institution_name":
                        "Dhaka University",
                    "institution_type":
                        "University",
                    "country_id":
                        self.country.id,
                    "education_level":
                        "Bachelor",
                    "degree_certificate":
                        "BSc",
                    "start_year":
                        2020,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            201,
        )

    def test_other_user_cannot_update_academic_background(
        self,
    ):
        academic = AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="Dhaka University",
            institution_type="University",
            country=self.country,
            education_level="Bachelor",
            degree_certificate="BSc",
            start_year=2020,
        )

        other_identity = UserIdentity.objects.create(
            email="other-academic-update@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.patch(
            f"/api/identity/academic-backgrounds/"
            f"{academic.id}/update/",
            data=json.dumps(
                {
                    "result": "3.80",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_update_academic_background(
        self,
    ):
        academic = AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="Dhaka University",
            institution_type="University",
            country=self.country,
            education_level="Bachelor",
            degree_certificate="BSc",
            start_year=2020,
        )

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.patch(
            f"/api/identity/academic-backgrounds/"
            f"{academic.id}/update/",
            data=json.dumps(
                {
                    "result": "3.80",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_other_user_cannot_delete_academic_background(
        self,
    ):
        academic = AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="Dhaka University",
            institution_type="University",
            country=self.country,
            education_level="Bachelor",
            degree_certificate="BSc",
            start_year=2020,
        )

        other_identity = UserIdentity.objects.create(
            email="other-academic-delete@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.delete(
            f"/api/identity/academic-backgrounds/"
            f"{academic.id}/delete/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_owner_can_delete_academic_background(
        self,
    ):
        academic = AcademicBackground.objects.create(
            personal_account=self.personal_account,
            institution_name="Dhaka University",
            institution_type="University",
            country=self.country,
            education_level="Bachelor",
            degree_certificate="BSc",
            start_year=2020,
        )

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.delete(
            f"/api/identity/academic-backgrounds/"
            f"{academic.id}/delete/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            AcademicBackground.objects.filter(
                id=academic.id
            ).exists()
        )        