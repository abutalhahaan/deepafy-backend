from datetime import date

from django.apps import apps
from django.urls import reverse
from rest_framework.test import APITestCase

from identity.models import UserIdentity
from institution.models import (
    InstitutionTypeGroup,
    InstitutionType,
    InstitutionProfile,
    InstitutionStaffService,
    UnclaimedPerson,
    InstitutionStaffAttendance,
    InstitutionAttendanceSettings,
    InstitutionHoliday,
)


class InstitutionStaffAttendanceAPITests(APITestCase):
    def setUp(self):
        # Resolve Country through the actual model relation so this test
        # works even if its Django app label differs from its module path.
        country_model = apps.get_model("organization", "Country")
        region_model = country_model._meta.get_field(
            "region"
        ).remote_field.model

        region = region_model.objects.create(name="Test Region")
        self.country = country_model.objects.create(
            region=region,
            name="Test Country",
            code="TST",
        )

        group = InstitutionTypeGroup.objects.create(
            name="Test Institution Group"
        )
        institution_type = InstitutionType.objects.create(
            group=group,
            name="Test Institution Type",
        )

        self.owner = UserIdentity.objects.create(
            email="attendance-owner@example.com",
            username="attendance_owner",
        )
        self.other_owner = UserIdentity.objects.create(
            email="attendance-other@example.com",
            username="attendance_other",
        )
        self.staff_identity = UserIdentity.objects.create(
            email="attendance-staff@example.com",
            username="attendance_staff",
        )
        self.other_staff_identity = UserIdentity.objects.create(
            email="attendance-other-staff@example.com",
            username="attendance_other_staff",
        )

        self.institution = InstitutionProfile.objects.create(
            identity=self.owner,
            institution_name="Test Institution",
            institution_type=institution_type,
            country=self.country,
        )
        self.other_institution = InstitutionProfile.objects.create(
            identity=self.other_owner,
            institution_name="Other Test Institution",
            institution_type=institution_type,
            country=self.country,
        )

        self.staff = InstitutionStaffService.objects.create(
            institution=self.institution,
            identity=self.staff_identity,
            designation="Teacher",
            joining_date=date(2020, 1, 1),
        )
        self.other_staff = InstitutionStaffService.objects.create(
            institution=self.other_institution,
            identity=self.other_staff_identity,
            designation="Teacher",
            joining_date=date(2020, 1, 1),
        )

        self.url = reverse("institution-staff-attendance-save")
        self.attendance_date = "2026-10-05"  # Monday

        self.client.force_authenticate(user=self.owner)

    def payload(self, **overrides):
        data = {
            "staff_service_id": self.staff.id,
            "date": self.attendance_date,
            "status": "P",
        }
        data.update(overrides)
        return data

    def test_unauthenticated_request_is_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(
            InstitutionStaffAttendance.objects.count(),
            0,
        )

    def test_attendance_is_created(self):
        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["created"])
        self.assertEqual(response.data["status"], "P")
        self.assertEqual(
            InstitutionStaffAttendance.objects.filter(
                staff_service=self.staff,
                date=self.attendance_date,
            ).count(),
            1,
        )

    def test_same_date_attendance_is_updated_not_duplicated(self):
        first_response = self.client.post(
            self.url,
            self.payload(status="P"),
            format="json",
        )
        second_response = self.client.post(
            self.url,
            self.payload(status="A"),
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        self.assertFalse(second_response.data["created"])

        records = InstitutionStaffAttendance.objects.filter(
            staff_service=self.staff,
            date=self.attendance_date,
        )
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.get().status, "A")

    def test_invalid_attendance_status_is_rejected(self):
        response = self.client.post(
            self.url,
            self.payload(status="X"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            InstitutionStaffAttendance.objects.count(),
            0,
        )

    def test_staff_from_another_institution_is_rejected(self):
        response = self.client.post(
            self.url,
            self.payload(staff_service_id=self.other_staff.id),
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            InstitutionStaffAttendance.objects.count(),
            0,
        )

    def test_weekly_holiday_rejects_attendance(self):
        InstitutionAttendanceSettings.objects.create(
            institution=self.institution,
            weekly_holidays=[0],  # Monday
        )

        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("weekly holiday", response.data["detail"])
        self.assertEqual(
            InstitutionStaffAttendance.objects.count(),
            0,
        )

    def test_institution_holiday_rejects_attendance(self):
        InstitutionHoliday.objects.create(
            institution=self.institution,
            from_date=date(2026, 10, 5),
            to_date=date(2026, 10, 5),
            name="Test Holiday",
        )

        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("institution holiday", response.data["detail"])
        self.assertEqual(
            InstitutionStaffAttendance.objects.count(),
            0,
        )

    def test_manual_staff_attendance_is_created(self):
        person = UnclaimedPerson.objects.create(
            institution=self.institution,
            full_name="Manual Test Staff",
            designation="Assistant Teacher",
            joining_date=date(2020, 1, 1),
        )

        response = self.client.post(
            self.url,
            {
                "unclaimed_person_id": person.id,
                "date": self.attendance_date,
                "status": "P",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["created"])

        record = InstitutionStaffAttendance.objects.get(
            unclaimed_person=person,
            date=self.attendance_date,
        )
        self.assertEqual(record.status, "P")
        self.assertIsNone(record.staff_service_id)

    def test_manual_staff_same_date_attendance_is_updated_not_duplicated(self):
        person = UnclaimedPerson.objects.create(
            institution=self.institution,
            full_name="Manual Update Staff",
            designation="Assistant Teacher",
            joining_date=date(2020, 1, 1),
        )
        payload = {
            "unclaimed_person_id": person.id,
            "date": self.attendance_date,
            "status": "P",
        }
        first = self.client.post(self.url, payload, format="json")
        payload["status"] = "A"
        second = self.client.post(self.url, payload, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data["created"])

        records = InstitutionStaffAttendance.objects.filter(
            unclaimed_person=person, date=self.attendance_date
        )
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.get().status, "A")

    def test_manual_staff_from_another_institution_is_rejected(self):
        person = UnclaimedPerson.objects.create(
            institution=self.other_institution,
            full_name="Other Institution Staff",
            designation="Teacher",
            joining_date=date(2020, 1, 1),
        )
        response = self.client.post(
            self.url,
            {
                "unclaimed_person_id": person.id,
                "date": self.attendance_date,
                "status": "P",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            InstitutionStaffAttendance.objects.filter(
                unclaimed_person=person
            ).exists()
        )

    def test_both_staff_identifiers_are_rejected(self):
        person = UnclaimedPerson.objects.create(
            institution=self.institution,
            full_name="Manual Both IDs Staff",
            designation="Teacher",
            joining_date=date(2020, 1, 1),
        )
        response = self.client.post(
            self.url,
            {
                "staff_service_id": self.staff.id,
                "unclaimed_person_id": person.id,
                "date": self.attendance_date,
                "status": "P",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(InstitutionStaffAttendance.objects.count(), 0)

    def test_monthly_api_returns_both_staff_sources_and_saved_statuses(self):
        person = UnclaimedPerson.objects.create(
            institution=self.institution,
            full_name="Monthly Manual Staff",
            designation="Assistant Teacher",
            joining_date=date(2020, 1, 1),
        )
        deepafy = self.client.post(
            self.url,
            {
                "staff_service_id": self.staff.id,
                "date": self.attendance_date,
                "status": "P",
            },
            format="json",
        )
        manual = self.client.post(
            self.url,
            {
                "unclaimed_person_id": person.id,
                "date": self.attendance_date,
                "status": "A",
            },
            format="json",
        )
        self.assertEqual(deepafy.status_code, 201)
        self.assertEqual(manual.status_code, 201)

        response = self.client.get(
            reverse("institution-staff-attendance-monthly"),
            {"year": 2026, "month": 10},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        rows = response.data["teachers_staff"]
        deepafy_row = next(row for row in rows if row["staff_source"] == "deepafy")
        manual_row = next(row for row in rows if row["staff_source"] == "manual")
        self.assertEqual(deepafy_row["attendance"]["5"], "P")
        self.assertEqual(manual_row["attendance"]["5"], "A")
