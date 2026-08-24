import json

from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken

from identity.models import (
    ProfessionalAccount,
    UserIdentity,
)

from .models import (
    JobCategory,
    JobInterest,
)


class JobCategoryTests(TestCase):
    def setUp(self):
        self.job_category = JobCategory.objects.create(
            name="Software Development",
            slug="software-development",
            description="Software and technology jobs.",
        )

    def test_job_category_creation(self):
        self.assertEqual(
            self.job_category.name,
            "Software Development",
        )

        self.assertEqual(
            self.job_category.slug,
            "software-development",
        )

        self.assertTrue(
            self.job_category.is_active
        )

    def test_job_category_string(self):
        self.assertEqual(
            str(self.job_category),
            "Software Development",
        )

    def test_job_category_list_api(self):
        response = self.client.get(
            "/api/jobs/categories/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["count"],
            1,
        )

        self.assertEqual(
            data["results"][0]["id"],
            self.job_category.id,
        )


class JobInterestTests(TestCase):
    def setUp(self):
        self.identity = UserIdentity.objects.create(
            email="job-interest@example.com",
        )

        self.professional_account = (
            ProfessionalAccount.objects.create(
                identity=self.identity,
            )
        )

        self.job_category = JobCategory.objects.create(
            name="Software Development",
            slug="software-development",
        )

    def test_job_interest_creation(self):
        job_interest = JobInterest.objects.create(
            professional_account=self.professional_account,
            job_category=self.job_category,
        )

        self.assertEqual(
            job_interest.professional_account,
            self.professional_account,
        )

        self.assertEqual(
            job_interest.job_category,
            self.job_category,
        )

        self.assertTrue(
            job_interest.is_active
        )

    def test_job_interest_string(self):
        job_interest = JobInterest.objects.create(
            professional_account=self.professional_account,
            job_category=self.job_category,
        )

        self.assertEqual(
            str(job_interest),
            (
                f"{self.identity.user_id} - "
                f"{self.job_category.name}"
            ),
        )

    def test_duplicate_job_interest_not_allowed(self):
        JobInterest.objects.create(
            professional_account=self.professional_account,
            job_category=self.job_category,
        )

        with self.assertRaises(Exception):
            JobInterest.objects.create(
                professional_account=self.professional_account,
                job_category=self.job_category,
            )

    def test_job_interest_list_api(self):
        JobInterest.objects.create(
            professional_account=self.professional_account,
            job_category=self.job_category,
        )

        response = self.client.get(
            f"/api/jobs/"
            f"{self.professional_account.id}/"
            "interests/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["count"],
            1,
        )

        self.assertEqual(
            data["results"][0]["job_category"]["id"],
            self.job_category.id,
        )

    def test_job_interest_add_requires_authentication(
        self,
    ):
        response = self.client.post(
            f"/api/jobs/{self.professional_account.id}/interests/add/",
            data=json.dumps(
                {
                    "job_category_id":
                    self.job_category.id,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_other_user_cannot_add_job_interest(
        self,
    ):
        other_identity = UserIdentity.objects.create(
            email="other-job-interest@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.post(
            f"/api/jobs/{self.professional_account.id}/interests/add/",
            data=json.dumps(
                {
                    "job_category_id":
                    self.job_category.id,
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

    def test_job_interest_add_api(self):
        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.post(
            f"/api/jobs/"
            f"{self.professional_account.id}/"
            f"interests/add/",
            data=json.dumps(
               {
                    "job_category_id":
                    self.job_category.id,
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

        self.assertTrue(
            JobInterest.objects.filter(
                professional_account=
                self.professional_account,
                job_category=self.job_category,
            ).exists()
        )

    def test_job_interest_remove_requires_authentication(
        self,
    ):
        JobInterest.objects.create(
            professional_account=self.professional_account,
            job_category=self.job_category,
        )

        response = self.client.delete(
            f"/api/jobs/"
            f"{self.professional_account.id}/"
            f"interests/"
            f"{self.job_category.id}/remove/",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_other_user_cannot_remove_job_interest(
        self,
    ):
        JobInterest.objects.create(
            professional_account=self.professional_account,
            job_category=self.job_category,
        )

        other_identity = UserIdentity.objects.create(
            email="other-job-remove@example.com",
        )

        refresh = RefreshToken.for_user(
            other_identity
        )

        response = self.client.delete(
            f"/api/jobs/"
            f"{self.professional_account.id}/"
            f"interests/"
            f"{self.job_category.id}/remove/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_job_interest_remove_api(self):
        JobInterest.objects.create(
            professional_account=self.professional_account,
            job_category=self.job_category,
        )

        refresh = RefreshToken.for_user(
            self.identity
        )

        response = self.client.delete(
            f"/api/jobs/"
            f"{self.professional_account.id}/"
            f"interests/"
            f"{self.job_category.id}/remove/",
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            JobInterest.objects.filter(
                professional_account=
                self.professional_account,
                job_category=self.job_category,
            ).exists()
        )