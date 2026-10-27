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


class InstitutionResultsAPITests(APITestCase):
    """API tests for institution class subjects, exams and marks."""

    def setUp(self):
        from datetime import date
        from institution.models import (
            Subject,
            InstitutionAcademicLevel,
            InstitutionAcademicSession,
        )

        country_model = apps.get_model("organization", "Country")
        region_model = country_model._meta.get_field(
            "region"
        ).remote_field.model

        region = region_model.objects.create(name="Results Test Region")
        country = country_model.objects.create(
            region=region,
            name="Results Test Country",
            code="RST",
        )

        group = InstitutionTypeGroup.objects.create(
            name="Results Test Group"
        )
        institution_type = InstitutionType.objects.create(
            group=group,
            name="Results Test Type",
        )

        self.owner = UserIdentity.objects.create(
            email="results-owner@example.com",
            username="results_owner",
        )
        self.other_owner = UserIdentity.objects.create(
            email="results-other@example.com",
            username="results_other",
        )

        self.institution = InstitutionProfile.objects.create(
            identity=self.owner,
            institution_name="Results Test Institution",
            institution_type=institution_type,
            country=country,
            global_identity_code="RST",
        )
        self.other_institution = InstitutionProfile.objects.create(
            identity=self.other_owner,
            institution_name="Other Results Institution",
            institution_type=institution_type,
            country=country,
            global_identity_code="RST2",
        )

        self.level = InstitutionAcademicLevel.objects.create(
            institution=self.institution,
            level_type="Class",
            name="Class 6",
        )
        self.other_level = InstitutionAcademicLevel.objects.create(
            institution=self.other_institution,
            level_type="Class",
            name="Class 6",
        )
        self.session = InstitutionAcademicSession.objects.create(
            institution=self.institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status="ACTIVE",
            is_current=True,
        )
        self.other_session = InstitutionAcademicSession.objects.create(
            institution=self.other_institution,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status="ACTIVE",
            is_current=True,
        )
        self.subject = Subject.objects.create(
            name="Results Test Mathematics",
            code="RTM",
            is_active=True,
        )

        self.client.force_authenticate(user=self.owner)



    def test_department_settings_owner_can_update_all_permissions(self):
        from institution.models import Department

        department = Department.objects.create(
            name="Settings Owner Test Department"
        )
        self.institution.departments.add(department)

        payload = {
            "can_manage_students": True,
            "can_manage_subjects": True,
            "can_manage_attendance": False,
            "can_manage_marks": True,
            "can_manage_results": False,
            "can_publish_results": True,
        }

        response = self.client.put(
            reverse("institution-department-settings", args=[department.id]),
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        for field, expected in payload.items():
            self.assertEqual(response.data[field], expected)

        response = self.client.get(
            reverse("institution-department-settings", args=[department.id])
        )
        self.assertEqual(response.status_code, 200, response.data)
        for field, expected in payload.items():
            self.assertEqual(response.data[field], expected)

    def test_other_institution_owner_cannot_access_department_settings(self):
        from institution.models import Department

        department = Department.objects.create(
            name="Settings Restricted Department"
        )
        self.institution.departments.add(department)

        self.client.force_authenticate(user=self.other_owner)
        response = self.client.put(
            reverse("institution-department-settings", args=[department.id]),
            {"can_manage_marks": True},
            format="json",
        )
        self.assertEqual(response.status_code, 404, response.data)

    def test_department_admin_cannot_update_department_settings(self):
        from institution.models import Department, InstitutionDepartmentAdmin

        department = Department.objects.create(
            name="Settings Admin Restricted Department"
        )
        self.institution.departments.add(department)

        admin = UserIdentity.objects.create(
            email="settings-department-admin@example.com",
            username="settings_department_admin",
        )
        InstitutionDepartmentAdmin.objects.create(
            institution=self.institution,
            department=department,
            identity=admin,
            assigned_by=self.owner,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.put(
            reverse("institution-department-settings", args=[department.id]),
            {"can_manage_marks": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_department_admin_can_only_list_marks_for_assigned_department(self):
        from institution.models import (
            Department,
            InstitutionDepartmentAdmin,
            Student,
            StudentEnrollment,
        )

        own_department = Department.objects.create(name="Results Own Department")
        other_department = Department.objects.create(name="Results Other Department")
        self.institution.departments.add(own_department, other_department)

        admin = UserIdentity.objects.create(
            email="results-department-admin@example.com",
            username="results_department_admin",
        )
        InstitutionDepartmentAdmin.objects.create(
            institution=self.institution,
            department=own_department,
            identity=admin,
            assigned_by=self.owner,
        )

        from institution.models import InstitutionDepartmentSettings

        InstitutionDepartmentSettings.objects.update_or_create(
            institution=self.institution,
            department=own_department,
            defaults={"can_manage_marks": True},
        )

        exam_subject, own_enrollment = self._create_exam_subject_and_enrollment()
        own_enrollment.department = own_department
        own_enrollment.save(update_fields=["department"])

        other_student = Student.objects.create(
            global_student_id="RST-000099",
            name="Other Department Student",
        )
        other_enrollment = StudentEnrollment.objects.create(
            student=other_student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            roll="99",
            department=other_department,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            reverse("institution-exam-marks", args=[exam_subject.id])
        )

        self.assertEqual(response.status_code, 200, response.data)
        returned_ids = {
            row["enrollment_id"] for row in response.data["results"]
        }
        self.assertIn(own_enrollment.id, returned_ids)
        self.assertNotIn(other_enrollment.id, returned_ids)

    def test_department_admin_cannot_save_marks_for_another_department(self):
        from institution.models import (
            Department,
            InstitutionDepartmentAdmin,
            Student,
            StudentEnrollment,
            InstitutionExamMark,
        )

        own_department = Department.objects.create(name="Marks Own Department")
        other_department = Department.objects.create(name="Marks Other Department")
        self.institution.departments.add(own_department, other_department)

        admin = UserIdentity.objects.create(
            email="marks-department-admin@example.com",
            username="marks_department_admin",
        )
        InstitutionDepartmentAdmin.objects.create(
            institution=self.institution,
            department=own_department,
            identity=admin,
            assigned_by=self.owner,
        )

        exam_subject, _ = self._create_exam_subject_and_enrollment()
        other_student = Student.objects.create(
            global_student_id="RST-000098",
            name="Forbidden Marks Student",
        )
        other_enrollment = StudentEnrollment.objects.create(
            student=other_student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            roll="98",
            department=other_department,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("institution-exam-marks", args=[exam_subject.id]),
            {
                "enrollment_id": other_enrollment.id,
                "marks_obtained": "80",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(
            InstitutionExamMark.objects.filter(
                exam_subject=exam_subject,
                enrollment=other_enrollment,
            ).exists()
        )

    def test_class_subject_assignment_and_listing(self):
        response = self.client.post(
            reverse("institution-class-subjects"),
            {
                "academic_level_id": self.level.id,
                "subject_id": self.subject.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        listed = self.client.get(
            reverse("institution-class-subjects"),
            {"academic_level_id": self.level.id},
        )
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertTrue(
            any(
                item["subject_id"] == self.subject.id
                for item in listed.data["results"]
            )
        )

    def test_class_subject_cannot_be_assigned_to_another_institutions_level(self):
        response = self.client.post(
            reverse("institution-class-subjects"),
            {
                "academic_level_id": self.other_level.id,
                "subject_id": self.subject.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_exam_rejects_pass_mark_above_full_marks(self):
        response = self.client.post(
            reverse("institution-exams"),
            {
                "academic_session_id": self.session.id,
                "academic_level_id": self.level.id,
                "name": "Invalid Pass Mark Test",
                "category": "INTERNAL",
                "exam_type": "Class Test",
                "full_marks": "100",
                "pass_mark": "101",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_exam_cannot_use_another_institutions_session(self):
        response = self.client.post(
            reverse("institution-exams"),
            {
                "academic_session_id": self.other_session.id,
                "academic_level_id": self.level.id,
                "name": "Foreign Session Test",
                "category": "INTERNAL",
                "exam_type": "Class Test",
                "full_marks": "100",
                "pass_mark": "33",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_exam_creation_and_subject_assignment(self):
        assigned = self.client.post(
            reverse("institution-class-subjects"),
            {
                "academic_level_id": self.level.id,
                "subject_id": self.subject.id,
            },
            format="json",
        )
        self.assertEqual(assigned.status_code, 201, assigned.data)

        created = self.client.post(
            reverse("institution-exams"),
            {
                "academic_session_id": self.session.id,
                "academic_level_id": self.level.id,
                "name": "First Class Test",
                "category": "INTERNAL",
                "exam_type": "Class Test",
                "full_marks": "100",
                "pass_mark": "33",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)

        exam_id = created.data.get("id")
        self.assertIsNotNone(exam_id)

        subject_response = self.client.post(
            reverse("institution-exam-subjects", args=[exam_id]),
            {
                "subject_id": self.subject.id,
                "full_marks": "100",
                "pass_mark": "33",
            },
            format="json",
        )
        self.assertEqual(
            subject_response.status_code,
            201,
            subject_response.data,
        )

    def test_results_email_rejects_unpublished_exam(self):
        exam_subject, enrollment = self._create_exam_subject_and_enrollment()

        response = self.client.post(
            reverse(
                "institution-exam-results-send-email",
                args=[exam_subject.exam.id],
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Publish", response.data["detail"])

    def test_results_email_requires_smtp_configuration(self):
        from django.test import override_settings

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        exam = exam_subject.exam
        exam.is_published = True
        exam.save(update_fields=["is_published"])

        with override_settings(
            EMAIL_HOST="",
            EMAIL_HOST_USER="",
            EMAIL_HOST_PASSWORD="",
        ):
            response = self.client.post(
                reverse(
                    "institution-exam-results-send-email",
                    args=[exam.id],
                ),
                {},
                format="json",
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("SMTP", response.data["detail"])

    def test_results_email_cannot_access_another_institutions_exam(self):
        from institution.models import InstitutionExam

        other_exam = InstitutionExam.objects.create(
            institution=self.other_institution,
            academic_session=self.other_session,
            academic_level=self.other_level,
            name="Other Institution Exam",
            category="INTERNAL",
            exam_type="Class Test",
            full_marks=100,
            pass_mark=33,
            is_published=True,
        )

        response = self.client.post(
            reverse(
                "institution-exam-results-send-email",
                args=[other_exam.id],
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_results_request_is_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("institution-exams"))
        self.assertIn(response.status_code, (401, 403))

    def _create_exam_subject_and_enrollment(self):
        from institution.models import (
            Student,
            StudentEnrollment,
            InstitutionClassSubject,
            InstitutionExam,
            InstitutionExamSubject,
        )

        InstitutionClassSubject.objects.create(
            institution=self.institution,
            academic_level=self.level,
            subject=self.subject,
        )
        exam = InstitutionExam.objects.create(
            institution=self.institution,
            academic_session=self.session,
            academic_level=self.level,
            name="Marks Test Exam",
            category="INTERNAL",
            exam_type="Class Test",
            full_marks=100,
            pass_mark=33,
        )
        exam_subject = InstitutionExamSubject.objects.create(
            exam=exam,
            subject=self.subject,
            full_marks=100,
            pass_mark=33,
        )
        student = Student.objects.create(
            global_student_id="RST-000001",
            name="Results Test Student",
        )
        enrollment = StudentEnrollment.objects.create(
            student=student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            roll="1",
        )
        return exam_subject, enrollment

    def test_student_marks_can_be_saved_and_updated(self):
        from institution.models import InstitutionExamMark

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        url = reverse(
            "institution-exam-marks",
            args=[exam_subject.id],
        )

        first = self.client.post(
            url,
            {
                "enrollment_id": enrollment.id,
                "marks_obtained": "75",
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["marks_obtained"], "75")

        second = self.client.post(
            url,
            {
                "enrollment_id": enrollment.id,
                "marks_obtained": "82",
            },
            format="json",
        )
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data["marks_obtained"], "82")
        self.assertEqual(
            InstitutionExamMark.objects.filter(
                exam_subject=exam_subject,
                enrollment=enrollment,
            ).count(),
            1,
        )

    def test_absent_student_can_be_saved_without_marks(self):
        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        response = self.client.post(
            reverse("institution-exam-marks", args=[exam_subject.id]),
            {
                "enrollment_id": enrollment.id,
                "is_absent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["is_absent"])
        self.assertIsNone(response.data["marks_obtained"])

    def test_marks_list_includes_students_without_saved_marks(self):
        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        response = self.client.get(
            reverse("institution-exam-marks", args=[exam_subject.id])
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

        row = response.data["results"][0]
        self.assertEqual(row["enrollment_id"], enrollment.id)
        self.assertIsNone(row["marks_obtained"])
        self.assertFalse(row["is_absent"])

    def test_marks_above_full_marks_are_rejected(self):
        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        response = self.client.post(
            reverse("institution-exam-marks", args=[exam_subject.id]),
            {
                "enrollment_id": enrollment.id,
                "marks_obtained": "101",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_enrollment_from_another_session_is_rejected(self):
        from institution.models import Student, StudentEnrollment

        exam_subject, _ = self._create_exam_subject_and_enrollment()
        student = Student.objects.create(
            global_student_id="RST-000002",
            name="Other Session Student",
        )
        other_enrollment = StudentEnrollment.objects.create(
            student=student,
            institution=self.institution,
            academic_session=self.other_session,
            class_name=self.level.name,
            roll="2",
        )
        response = self.client.post(
            reverse("institution-exam-marks", args=[exam_subject.id]),
            {
                "enrollment_id": other_enrollment.id,
                "marks_obtained": "70",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


    def test_department_admin_cannot_list_other_department_marks(self):
        from institution.models import (
            Department,
            InstitutionDepartmentAdmin,
            Student,
            StudentEnrollment,
        )

        own_department = Department.objects.create(name="Marks Access Own")
        other_department = Department.objects.create(name="Marks Access Other")
        self.institution.departments.add(own_department, other_department)

        admin = UserIdentity.objects.create(
            email="marks-access-admin@example.com",
            username="marks_access_admin",
        )
        InstitutionDepartmentAdmin.objects.create(
            institution=self.institution,
            department=own_department,
            identity=admin,
            assigned_by=self.owner,
        )

        from institution.models import InstitutionDepartmentSettings

        InstitutionDepartmentSettings.objects.update_or_create(
            institution=self.institution,
            department=own_department,
            defaults={"can_manage_marks": True},
        )

        exam_subject, own_enrollment = self._create_exam_subject_and_enrollment()
        own_enrollment.department = own_department
        own_enrollment.save(update_fields=["department"])

        other_student = Student.objects.create(
            global_student_id="RST-000097",
            name="Other Department Marks Student",
        )
        other_enrollment = StudentEnrollment.objects.create(
            student=other_student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            roll="97",
            department=other_department,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            reverse("institution-exam-marks", args=[exam_subject.id])
        )

        self.assertEqual(response.status_code, 200, response.data)
        returned_ids = {
            row["enrollment_id"] for row in response.data["results"]
        }
        self.assertIn(own_enrollment.id, returned_ids)
        self.assertNotIn(other_enrollment.id, returned_ids)

    def test_department_admin_can_list_only_assigned_department_subjects(self):
        from institution.models import (
            Department,
            InstitutionDepartmentAdmin,
            InstitutionClassSubject,
        )

        own_department = Department.objects.create(name="Subjects Access Own")
        other_department = Department.objects.create(name="Subjects Access Other")
        self.institution.departments.add(own_department, other_department)

        admin = UserIdentity.objects.create(
            email="subjects-access-admin@example.com",
            username="subjects_access_admin",
        )
        InstitutionDepartmentAdmin.objects.create(
            institution=self.institution,
            department=own_department,
            identity=admin,
            assigned_by=self.owner,
        )

        from institution.models import InstitutionDepartmentSettings

        InstitutionDepartmentSettings.objects.create(
            institution=self.institution,
            department=own_department,
            can_manage_subjects=True,
        )

        own_assignment = InstitutionClassSubject.objects.create(
            institution=self.institution,
            academic_level=self.level,
            department=own_department,
            subject=self.subject,
            is_active=True,
        )
        other_subject = type(self.subject).objects.create(
            name="Other Department Test Subject",
            code="ODTS",
            is_active=True,
        )
        other_assignment = InstitutionClassSubject.objects.create(
            institution=self.institution,
            academic_level=self.level,
            department=other_department,
            subject=other_subject,
            is_active=True,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            reverse("institution-class-subjects"),
            {"academic_level_id": self.level.id},
        )

        self.assertEqual(response.status_code, 200, response.data)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(own_assignment.id, returned_ids)
        self.assertNotIn(other_assignment.id, returned_ids)

    def test_department_admin_cannot_assign_subject_to_another_department(self):
        from institution.models import Department, InstitutionDepartmentAdmin

        own_department = Department.objects.create(name="Subjects Write Own")
        other_department = Department.objects.create(name="Subjects Write Other")
        self.institution.departments.add(own_department, other_department)

        admin = UserIdentity.objects.create(
            email="subjects-write-admin@example.com",
            username="subjects_write_admin",
        )
        InstitutionDepartmentAdmin.objects.create(
            institution=self.institution,
            department=own_department,
            identity=admin,
            assigned_by=self.owner,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("institution-class-subjects"),
            {
                "academic_level_id": self.level.id,
                "department_id": other_department.id,
                "subjects": [
                    {
                        "subject_id": self.subject.id,
                        "full_marks": 100,
                        "pass_mark": 33,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403, response.data)
    def test_grade_scale_can_be_created_and_listed(self):
        response = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "General Grading", "is_default": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["name"], "General Grading")

        listed = self.client.get(reverse("institution-grade-scales"))
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertTrue(
            any(item["name"] == "General Grading" for item in listed.data["results"])
        )

    def test_creating_default_grade_scale_clears_previous_default(self):
        from institution.models import InstitutionGradeScale

        first = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "First Default Scale", "is_default": True},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)

        second = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "Second Default Scale", "is_default": True},
            format="json",
        )
        self.assertEqual(second.status_code, 201, second.data)

        defaults = InstitutionGradeScale.objects.filter(
            institution=self.institution,
            is_default=True,
        )
        self.assertEqual(defaults.count(), 1)
        self.assertEqual(defaults.get().id, second.data["id"])

    def test_duplicate_default_scale_preserves_existing_default(self):
        from institution.models import InstitutionGradeScale

        first = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "Existing Default", "is_default": True},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)

        second = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "Another Default", "is_default": True},
            format="json",
        )
        self.assertEqual(second.status_code, 201, second.data)

        duplicate = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "Existing Default", "is_default": True},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.data)

        defaults = InstitutionGradeScale.objects.filter(
            institution=self.institution,
            is_default=True,
        )
        self.assertEqual(defaults.count(), 1)
        self.assertEqual(defaults.get().id, second.data["id"])

    def test_valid_grade_range_can_be_created(self):
        scale_response = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "Valid Range Scale"},
            format="json",
        )
        self.assertEqual(scale_response.status_code, 201, scale_response.data)

        response = self.client.post(
            reverse(
                "institution-grade-ranges",
                args=[scale_response.data["id"]],
            ),
            {
                "grade_name": "A",
                "min_percentage": "80",
                "max_percentage": "100",
                "grade_point": "5.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_decimal_grade_point_is_accepted_on_create_and_update(self):
        from institution.models import InstitutionGradeRange, InstitutionGradeScale

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Decimal GPA Scale",
            maximum_gpa="5.00",
        )

        create_response = self.client.post(
            reverse("institution-grade-ranges", args=[scale.id]),
            {
                "grade_name": "A",
                "min_percentage": "80",
                "max_percentage": "100",
                "grade_point": "4.5",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)

        grade = InstitutionGradeRange.objects.get(
            grade_scale=scale,
            grade_name="A",
        )
        self.assertEqual(grade.grade_point, 4.5)

        update_response = self.client.patch(
            reverse(
                "institution-grade-range-detail",
                args=[scale.id, grade.id],
            ),
            {"grade_point": "3.75"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)

        grade.refresh_from_db()
        self.assertEqual(grade.grade_point, 3.75)

    def test_grade_point_cannot_exceed_maximum_gpa(self):
        from institution.models import InstitutionGradeScale, InstitutionGradeRange

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="GPA Validation Scale",
            maximum_gpa="5.00",
        )

        url = reverse(
            "institution-grade-ranges",
            args=[scale.id],
        )

        invalid_create = self.client.post(
            url,
            {
                "grade_name": "A+",
                "min_percentage": "80",
                "max_percentage": "100",
                "grade_point": "5.01",
            },
            format="json",
        )
        self.assertEqual(invalid_create.status_code, 400)

        valid_create = self.client.post(
            url,
            {
                "grade_name": "A",
                "min_percentage": "80",
                "max_percentage": "100",
                "grade_point": "5.00",
            },
            format="json",
        )
        self.assertEqual(valid_create.status_code, 201, valid_create.data)

        grade = InstitutionGradeRange.objects.get(
            grade_scale=scale,
            grade_name="A",
        )

        invalid_update = self.client.patch(
            reverse(
                "institution-grade-range-detail",
                args=[scale.id, grade.id],
            ),
            {"grade_point": "5.01"},
            format="json",
        )
        self.assertEqual(invalid_update.status_code, 400)

        grade.refresh_from_db()
        self.assertEqual(str(grade.grade_point), "5.00")

    def test_published_exam_allows_new_grade_range(self):
        from institution.models import InstitutionGradeScale, InstitutionExam

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Published Results Scale",
        )
        exam = InstitutionExam.objects.create(
            institution=self.institution,
            academic_session=self.session,
            academic_level=self.level,
            name="Published Grade Protection Exam",
            category="INTERNAL",
            exam_type="Class Test",
            full_marks=100,
            pass_mark=33,
            grade_scale=scale,
            is_published=True,
            has_been_published=True,
            grading_snapshot={
                "grade_scale_id": scale.id,
                "name": scale.name,
                "maximum_gpa": "5.00",
                "is_active": True,
                "ranges": [],
            },
        )

        response = self.client.post(
            reverse("institution-grade-ranges", args=[scale.id]),
            {
                "grade_name": "A",
                "min_percentage": "80",
                "max_percentage": "100",
                "grade_point": "5.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(scale.ranges.count(), 1)
        exam.refresh_from_db()
        self.assertEqual(exam.grading_snapshot["ranges"], [])
        self.assertTrue(exam.is_published)

    def test_overlapping_grade_ranges_are_rejected(self):
        scale_response = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "Overlap Test Scale"},
            format="json",
        )
        self.assertEqual(scale_response.status_code, 201, scale_response.data)
        url = reverse(
            "institution-grade-ranges",
            args=[scale_response.data["id"]],
        )

        first = self.client.post(
            url,
            {
                "grade_name": "A",
                "min_percentage": "80",
                "max_percentage": "100",
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)

        second = self.client.post(
            url,
            {
                "grade_name": "B",
                "min_percentage": "70",
                "max_percentage": "85",
            },
            format="json",
        )
        self.assertEqual(second.status_code, 400, second.data)

    def test_invalid_grade_percentage_is_rejected(self):
        scale_response = self.client.post(
            reverse("institution-grade-scales"),
            {"name": "Invalid Percentage Scale"},
            format="json",
        )
        self.assertEqual(scale_response.status_code, 201, scale_response.data)

        response = self.client.post(
            reverse(
                "institution-grade-ranges",
                args=[scale_response.data["id"]],
            ),
            {
                "grade_name": "Invalid",
                "min_percentage": "-1",
                "max_percentage": "100",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_grade_scale_from_another_institution_is_not_accessible(self):
        from institution.models import InstitutionGradeScale

        other_scale = InstitutionGradeScale.objects.create(
            institution=self.other_institution,
            name="Other Institution Scale",
        )
        response = self.client.get(
            reverse(
                "institution-grade-ranges",
                args=[other_scale.id],
            )
        )
        self.assertEqual(response.status_code, 404, response.data)

    def test_grade_range_can_be_updated(self):
        from institution.models import InstitutionGradeScale, InstitutionGradeRange

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Editable Grade Scale",
        )
        grade = InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="A",
            min_percentage=80,
            max_percentage=100,
            grade_point=5,
        )

        response = self.client.patch(
            reverse(
                "institution-grade-range-detail",
                args=[scale.id, grade.id],
            ),
            {
                "grade_name": "A+",
                "min_percentage": "85",
                "max_percentage": "100",
                "grade_point": "5.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        grade.refresh_from_db()
        self.assertEqual(grade.grade_name, "A+")
        self.assertEqual(str(grade.min_percentage), "85.00")

    def test_grade_range_can_be_deleted(self):
        from institution.models import InstitutionGradeScale, InstitutionGradeRange

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Deletable Grade Scale",
        )
        grade = InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="F",
            min_percentage=0,
            max_percentage=39.99,
            grade_point=0,
        )

        response = self.client.delete(
            reverse(
                "institution-grade-range-detail",
                args=[scale.id, grade.id],
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(InstitutionGradeRange.objects.filter(id=grade.id).exists())

    def test_grade_range_from_another_institution_cannot_be_modified(self):
        from institution.models import InstitutionGradeScale, InstitutionGradeRange

        scale = InstitutionGradeScale.objects.create(
            institution=self.other_institution,
            name="Foreign Grade Scale",
        )
        grade = InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="A",
            min_percentage=80,
            max_percentage=100,
            grade_point=5,
        )

        url = reverse(
            "institution-grade-range-detail",
            args=[scale.id, grade.id],
        )
        update_response = self.client.patch(
            url,
            {"grade_name": "Changed"},
            format="json",
        )
        delete_response = self.client.delete(url)

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        grade.refresh_from_db()
        self.assertEqual(grade.grade_name, "A")

    def test_published_exam_allows_grade_range_update_and_delete(self):
        from institution.models import (
            InstitutionGradeScale,
            InstitutionGradeRange,
            InstitutionExam,
        )

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Editable Grade Scale",
        )
        grade = InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="A",
            min_percentage=80,
            max_percentage=100,
            grade_point=5,
        )
        exam = InstitutionExam.objects.create(
            institution=self.institution,
            academic_session=self.session,
            academic_level=self.level,
            name="Published Snapshot Test",
            category="INTERNAL",
            exam_type="Class Test",
            full_marks=100,
            pass_mark=33,
            grade_scale=scale,
            is_published=True,
            has_been_published=True,
            grading_snapshot={
                "grade_scale_id": scale.id,
                "name": scale.name,
                "maximum_gpa": "5.00",
                "is_active": True,
                "ranges": [
                    {
                        "id": grade.id,
                        "grade_name": "A",
                        "min_percentage": "80.00",
                        "max_percentage": "100.00",
                        "grade_point": "5.00",
                    }
                ],
            },
        )

        url = reverse(
            "institution-grade-range-detail",
            args=[scale.id, grade.id],
        )
        update_response = self.client.patch(
            url,
            {"grade_name": "Changed"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)

        delete_response = self.client.delete(url)
        self.assertEqual(delete_response.status_code, 204, getattr(delete_response, "data", None))

        exam.refresh_from_db()
        self.assertEqual(exam.grading_snapshot["ranges"][0]["grade_name"], "A")
        self.assertFalse(scale.ranges.filter(id=grade.id).exists())

    def test_exam_can_use_own_grade_scale(self):
        from institution.models import InstitutionGradeScale

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Exam Specific Scale",
        )
        response = self.client.post(
            reverse("institution-exams"),
            {
                "academic_session_id": self.session.id,
                "academic_level_id": self.level.id,
                "grade_scale_id": scale.id,
                "name": "Graded Class Test",
                "category": "INTERNAL",
                "exam_type": "Class Test",
                "full_marks": "100",
                "pass_mark": "33",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["grade_scale_id"], scale.id)
        self.assertEqual(response.data["grade_scale"], scale.name)

    def test_exam_rejects_another_institutions_grade_scale(self):
        from institution.models import InstitutionGradeScale

        other_scale = InstitutionGradeScale.objects.create(
            institution=self.other_institution,
            name="Foreign Exam Scale",
        )
        response = self.client.post(
            reverse("institution-exams"),
            {
                "academic_session_id": self.session.id,
                "academic_level_id": self.level.id,
                "grade_scale_id": other_scale.id,
                "name": "Invalid Graded Test",
                "category": "INTERNAL",
                "exam_type": "Class Test",
                "full_marks": "100",
                "pass_mark": "33",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)

    def test_exam_without_grade_scale_remains_supported(self):
        response = self.client.post(
            reverse("institution-exams"),
            {
                "academic_session_id": self.session.id,
                "academic_level_id": self.level.id,
                "name": "Unconfigured Grade Test",
                "category": "INTERNAL",
                "exam_type": "Class Test",
                "full_marks": "100",
                "pass_mark": "33",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data["grade_scale_id"])
        self.assertIsNone(response.data["grade_scale"])

    def test_exam_results_are_incomplete_when_marks_are_missing(self):
        exam_subject, enrollment = self._create_exam_subject_and_enrollment()

        response = self.client.get(
            reverse(
                "institution-exam-results",
                args=[exam_subject.exam_id],
            )
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["statistics"]["total_students"], 1)
        self.assertEqual(response.data["statistics"]["incomplete"], 1)
        self.assertEqual(response.data["results"][0]["status"], "INCOMPLETE")
        self.assertIsNone(response.data["results"][0]["percentage"])

    def test_exam_results_calculate_subject_and_overall_statistics(self):
        from institution.models import InstitutionExamMark

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        InstitutionExamMark.objects.create(
            exam_subject=exam_subject,
            enrollment=enrollment,
            marks_obtained=80,
        )

        response = self.client.get(
            reverse(
                "institution-exam-results",
                args=[exam_subject.exam_id],
            )
        )

        self.assertEqual(response.status_code, 200, response.data)
        result = response.data["results"][0]
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["total_obtained"], "80.00")
        self.assertEqual(result["percentage"], "80.00")
        self.assertEqual(result["subjects"][0]["status"], "PASS")
        self.assertEqual(response.data["statistics"]["completed"], 1)
        self.assertEqual(response.data["statistics"]["passed"], 1)
        self.assertEqual(response.data["statistics"]["failed"], 0)
        self.assertEqual(response.data["statistics"]["pass_rate"], "100.00")

    def test_exam_results_assign_merit_roll_by_fail_count_and_marks(self):
        from institution.models import (
            Subject,
            InstitutionExamMark,
            InstitutionExamSubject,
            Student,
            StudentEnrollment,
            InstitutionClassSubject,
        )

        exam_subject, first_enrollment = self._create_exam_subject_and_enrollment()
        exam = exam_subject.exam

        second_subject = Subject.objects.create(
            name="Results Test English",
            code="RTE",
            is_active=True,
        )
        InstitutionClassSubject.objects.create(
            institution=self.institution,
            academic_level=self.level,
            subject=second_subject,
        )
        second_exam_subject = InstitutionExamSubject.objects.create(
            exam=exam,
            subject=second_subject,
            full_marks=100,
            pass_mark=33,
        )

        second_student = Student.objects.create(
            global_student_id="RST-000002",
            name="Second Results Student",
        )
        second_enrollment = StudentEnrollment.objects.create(
            student=second_student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            roll="2",
        )

        third_student = Student.objects.create(
            global_student_id="RST-000003",
            name="Third Results Student",
        )
        third_enrollment = StudentEnrollment.objects.create(
            student=third_student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            roll="3",
        )

        marks = [
            # One failed subject, total 150.
            (exam_subject, first_enrollment, 20),
            (second_exam_subject, first_enrollment, 130),
            # No failed subjects, total 120: should rank first.
            (exam_subject, second_enrollment, 60),
            (second_exam_subject, second_enrollment, 60),
            # No failed subjects, total 120; higher top subject mark wins.
            (exam_subject, third_enrollment, 80),
            (second_exam_subject, third_enrollment, 40),
        ]
        for subject, enrollment, obtained in marks:
            InstitutionExamMark.objects.create(
                exam_subject=subject,
                enrollment=enrollment,
                marks_obtained=obtained,
            )

        response = self.client.get(
            reverse("institution-exam-results", args=[exam.id])
        )

        self.assertEqual(response.status_code, 200, response.data)
        results = response.data["results"]
        self.assertEqual(
            [item["enrollment_id"] for item in results],
            [third_enrollment.id, second_enrollment.id, first_enrollment.id],
        )
        self.assertEqual([item["merit_roll"] for item in results], [1, 2, 3])
        self.assertEqual(first_enrollment.roll, "1")
        self.assertEqual(second_enrollment.roll, "2")
        self.assertEqual(third_enrollment.roll, "3")

    def test_exam_results_reject_another_institutions_exam(self):
        from institution.models import InstitutionExam

        other_exam = InstitutionExam.objects.create(
            institution=self.other_institution,
            academic_session=self.other_session,
            academic_level=self.other_level,
            name="Private Other Exam",
            category="INTERNAL",
            exam_type="Class Test",
            full_marks=100,
            pass_mark=33,
        )

        response = self.client.get(
            reverse("institution-exam-results", args=[other_exam.id])
        )

        self.assertEqual(response.status_code, 404, response.data)

    def test_exam_publish_rejects_grade_scale_with_percentage_gap(self):
        from institution.models import (
            InstitutionGradeScale,
            InstitutionGradeRange,
        )

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        exam = exam_subject.exam

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Incomplete Coverage Scale",
        )
        exam.grade_scale = scale
        exam.save(update_fields=["grade_scale"])

        InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="A",
            min_percentage="80.00",
            max_percentage="100.00",
            grade_point="5.00",
        )

        response = self.client.post(
            reverse("institution-exam-publish", args=[exam.id]),
            {"is_published": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("cover 0.00 to 100.00", response.data["detail"])

        exam.refresh_from_db()
        self.assertFalse(exam.is_published)

    def test_exam_publish_rejects_incomplete_marks(self):
        from institution.models import InstitutionGradeScale, InstitutionGradeRange

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Complete Scale For Missing Marks",
        )
        InstitutionGradeRange.objects.create(
            grade_scale=scale, grade_name="F",
            min_percentage="0.00", max_percentage="39.99", grade_point="0",
        )
        InstitutionGradeRange.objects.create(
            grade_scale=scale, grade_name="A",
            min_percentage="40.00", max_percentage="100.00", grade_point="5",
        )
        exam_subject.exam.grade_scale = scale
        exam_subject.exam.save(update_fields=["grade_scale"])

        response = self.client.post(
            reverse("institution-exam-publish", args=[exam_subject.exam_id]),
            {"is_published": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(
            response.data["detail"],
            "Cannot publish: some student marks are incomplete.",
        )

    def test_exam_publish_succeeds_when_all_marks_are_complete(self):
        from institution.models import (
            InstitutionExamMark,
            InstitutionExam,
            InstitutionGradeScale,
            InstitutionGradeRange,
        )

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Complete Scale For Successful Publish",
        )
        InstitutionGradeRange.objects.create(
            grade_scale=scale, grade_name="F",
            min_percentage="0.00", max_percentage="39.99", grade_point="0",
        )
        InstitutionGradeRange.objects.create(
            grade_scale=scale, grade_name="A",
            min_percentage="40.00", max_percentage="100.00", grade_point="5",
        )
        exam_subject.exam.grade_scale = scale
        exam_subject.exam.save(update_fields=["grade_scale"])

        InstitutionExamMark.objects.create(
            exam_subject=exam_subject,
            enrollment=enrollment,
            marks_obtained=80,
        )

        response = self.client.post(
            reverse("institution-exam-publish", args=[exam_subject.exam_id]),
            {"is_published": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_published"])

        exam = InstitutionExam.objects.get(id=exam_subject.exam_id)
        self.assertTrue(exam.is_published)


    def _create_publish_department_admin(self, can_publish=True):
        from institution.models import (
            Department,
            InstitutionDepartmentAdmin,
            InstitutionDepartmentSettings,
        )

        department = Department.objects.create(
            name="Publish Test Department"
        )
        self.institution.departments.add(department)

        admin = UserIdentity.objects.create(
            email="publish-department-admin@example.com",
            username="publish_department_admin",
        )
        InstitutionDepartmentAdmin.objects.create(
            institution=self.institution,
            department=department,
            identity=admin,
            assigned_by=self.owner,
        )
        InstitutionDepartmentSettings.objects.create(
            institution=self.institution,
            department=department,
            can_publish_results=can_publish,
        )
        return admin, department

    def test_department_admin_can_publish_and_unpublish_own_department_exam(self):
        from institution.models import (
            InstitutionExam,
            InstitutionExamMark,
            InstitutionGradeScale,
            InstitutionGradeRange,
        )

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        admin, department = self._create_publish_department_admin(
            can_publish=True
        )
        enrollment.department = department
        enrollment.save(update_fields=["department"])

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Department Publish Test Scale",
        )
        InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="F",
            min_percentage="0.00",
            max_percentage="39.99",
            grade_point="0",
        )
        InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="A",
            min_percentage="40.00",
            max_percentage="100.00",
            grade_point="5",
        )
        exam = exam_subject.exam
        exam.grade_scale = scale
        exam.save(update_fields=["grade_scale"])

        InstitutionExamMark.objects.create(
            exam_subject=exam_subject,
            enrollment=enrollment,
            marks_obtained=80,
        )

        self.client.force_authenticate(user=admin)

        publish_response = self.client.post(
            reverse("institution-exam-publish", args=[exam.id]),
            {"is_published": True},
            format="json",
        )
        self.assertEqual(
            publish_response.status_code, 200, publish_response.data
        )
        self.assertTrue(publish_response.data["is_published"])

        unpublish_response = self.client.post(
            reverse("institution-exam-publish", args=[exam.id]),
            {"is_published": False},
            format="json",
        )
        self.assertEqual(
            unpublish_response.status_code, 200, unpublish_response.data
        )
        self.assertFalse(unpublish_response.data["is_published"])

        exam.refresh_from_db()
        self.assertFalse(exam.is_published)

    def test_department_admin_cannot_publish_without_permission(self):
        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        admin, department = self._create_publish_department_admin(
            can_publish=False
        )
        enrollment.department = department
        enrollment.save(update_fields=["department"])

        self.client.force_authenticate(user=admin)
        for publish_value in (True, False):
            with self.subTest(is_published=publish_value):
                response = self.client.post(
                    reverse(
                        "institution-exam-publish",
                        args=[exam_subject.exam_id],
                    ),
                    {"is_published": publish_value},
                    format="json",
                )
                self.assertEqual(
                    response.status_code, 403, response.data
                )

    def test_department_admin_cannot_publish_exam_with_multiple_departments(self):
        from institution.models import (
            Department,
            Student,
            StudentEnrollment,
        )

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        admin, assigned_department = self._create_publish_department_admin(
            can_publish=True
        )
        other_department = Department.objects.create(
            name="Other Publish Test Department"
        )
        self.institution.departments.add(other_department)

        enrollment.department = assigned_department
        enrollment.save(update_fields=["department"])

        other_student = Student.objects.create(
            global_student_id="RST-000002",
            name="Other Department Student",
        )
        StudentEnrollment.objects.create(
            student=other_student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            roll="2",
            department=other_department,
        )

        self.client.force_authenticate(user=admin)
        for publish_value in (True, False):
            with self.subTest(is_published=publish_value):
                response = self.client.post(
                    reverse(
                        "institution-exam-publish",
                        args=[exam_subject.exam_id],
                    ),
                    {"is_published": publish_value},
                    format="json",
                )
                self.assertEqual(
                    response.status_code, 403, response.data
                )

    def test_grading_snapshot_survives_scale_edit_unpublish_and_republish(self):
        from institution.models import (
            InstitutionExam,
            InstitutionExamMark,
            InstitutionGradeScale,
            InstitutionGradeRange,
        )

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Original Snapshot Scale",
        )
        InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="F",
            min_percentage="0.00",
            max_percentage="39.99",
            grade_point="0.00",
        )
        InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="A",
            min_percentage="40.00",
            max_percentage="100.00",
            grade_point="5.00",
        )
        exam_subject.exam.grade_scale = scale
        exam_subject.exam.save(update_fields=["grade_scale"])
        InstitutionExamMark.objects.create(
            exam_subject=exam_subject,
            enrollment=enrollment,
            marks_obtained=80,
        )

        publish_url = reverse(
            "institution-exam-publish",
            args=[exam_subject.exam_id],
        )
        first_publish = self.client.post(
            publish_url,
            {"is_published": True},
            format="json",
        )
        self.assertEqual(first_publish.status_code, 200, first_publish.data)

        exam = InstitutionExam.objects.get(id=exam_subject.exam_id)
        original_snapshot = exam.grading_snapshot
        self.assertIsNotNone(original_snapshot)
        self.assertEqual(original_snapshot["name"], "Original Snapshot Scale")
        self.assertEqual(
            [item["grade_name"] for item in original_snapshot["ranges"]],
            ["F", "A"],
        )

        unpublish = self.client.post(
            publish_url,
            {"is_published": False},
            format="json",
        )
        self.assertEqual(unpublish.status_code, 200, unpublish.data)

        scale.name = "Edited Scale Name"
        scale.save(update_fields=["name"])
        grade_a = scale.ranges.get(grade_name="A")
        grade_a.grade_name = "A+"
        grade_a.grade_point = "4.00"
        grade_a.save(update_fields=["grade_name", "grade_point"])

        republish = self.client.post(
            publish_url,
            {"is_published": True},
            format="json",
        )
        self.assertEqual(republish.status_code, 200, republish.data)

        exam.refresh_from_db()
        self.assertEqual(exam.grading_snapshot, original_snapshot)

        results = self.client.get(
            reverse("institution-exam-results", args=[exam.id])
        )
        self.assertEqual(results.status_code, 200, results.data)
        self.assertEqual(results.data["grade_scale"], "Original Snapshot Scale")
        self.assertEqual(results.data["results"][0]["subjects"][0]["grade"], "A")
        self.assertEqual(
            results.data["results"][0]["subjects"][0]["grade_point"],
            "5.00",
        )


    def test_exam_publish_rejects_another_institutions_exam(self):
        from institution.models import InstitutionExam

        other_exam = InstitutionExam.objects.create(
            institution=self.other_institution,
            academic_session=self.other_session,
            academic_level=self.other_level,
            name="Private Publish Test",
            category="INTERNAL",
            exam_type="Class Test",
            full_marks=100,
            pass_mark=33,
        )

        response = self.client.post(
            reverse("institution-exam-publish", args=[other_exam.id]),
            {"is_published": True},
            format="json",
        )

        self.assertEqual(response.status_code, 404, response.data)

    def test_published_exam_rejects_marks_changes(self):
        from institution.models import InstitutionExamMark

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        InstitutionExamMark.objects.create(
            exam_subject=exam_subject,
            enrollment=enrollment,
            marks_obtained=75,
        )
        exam_subject.exam.is_published = True
        exam_subject.exam.save(update_fields=["is_published"])

        response = self.client.post(
            reverse("institution-exam-marks", args=[exam_subject.id]),
            {
                "enrollment_id": enrollment.id,
                "marks_obtained": "82",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("Unpublish the exam first.", response.data["detail"])
        saved_mark = InstitutionExamMark.objects.get(
            exam_subject=exam_subject,
            enrollment=enrollment,
        )
        self.assertEqual(str(saved_mark.marks_obtained), "75.00")

    def test_published_exam_rejects_subject_changes(self):
        from institution.models import InstitutionExamSubject

        exam_subject, _ = self._create_exam_subject_and_enrollment()
        exam = exam_subject.exam
        exam.is_published = True
        exam.save(update_fields=["is_published"])

        response = self.client.post(
            reverse("institution-exam-subjects", args=[exam.id]),
            {
                "subject_id": self.subject.id,
                "full_marks": "100",
                "pass_mark": "33",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("already been published", response.data["detail"])
        self.assertEqual(
            InstitutionExamSubject.objects.filter(exam=exam).count(),
            1,
        )

    def test_unpublished_exam_still_rejects_subject_changes_after_first_publish(self):
        from institution.models import InstitutionExam, InstitutionExamSubject

        exam_subject, _ = self._create_exam_subject_and_enrollment()
        exam = exam_subject.exam

        exam.is_published = True
        exam.has_been_published = True
        exam.save(update_fields=["is_published", "has_been_published"])

        response = self.client.post(
            reverse("institution-exam-publish", args=[exam.id]),
            {"is_published": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        response = self.client.post(
            reverse("institution-exam-subjects", args=[exam.id]),
            {
                "subject_id": self.subject.id,
                "full_marks": "100",
                "pass_mark": "33",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("already been published", response.data["detail"])
        self.assertEqual(InstitutionExamSubject.objects.filter(exam=exam).count(), 1)

    def test_unpublished_exam_allows_marks_changes_after_first_publish(self):
        from institution.models import InstitutionExamMark

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        InstitutionExamMark.objects.create(
            exam_subject=exam_subject,
            enrollment=enrollment,
            marks_obtained=75,
        )
        exam = exam_subject.exam
        exam.is_published = True
        exam.has_been_published = True
        exam.save(update_fields=["is_published", "has_been_published"])

        response = self.client.post(
            reverse("institution-exam-publish", args=[exam.id]),
            {"is_published": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

        response = self.client.post(
            reverse("institution-exam-marks", args=[exam_subject.id]),
            {
                "enrollment_id": enrollment.id,
                "marks_obtained": "82",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["marks_obtained"], "82")

    def test_unpublished_exam_allows_marks_changes(self):
        from institution.models import InstitutionExamMark

        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        InstitutionExamMark.objects.create(
            exam_subject=exam_subject,
            enrollment=enrollment,
            marks_obtained=75,
        )

        response = self.client.post(
            reverse("institution-exam-marks", args=[exam_subject.id]),
            {
                "enrollment_id": enrollment.id,
                "marks_obtained": "82",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["marks_obtained"], "82")


    def _create_versioned_grade_scale(self):
        from institution.models import (
            InstitutionGradeScale,
            InstitutionGradeRange,
            InstitutionGradeScaleVersion,
        )

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Version Test Scale",
            maximum_gpa="5.00",
            is_default=True,
            is_active=True,
        )
        ranges = [
            ("A", "80.00", "100.00", "5.00"),
            ("B", "60.00", "79.99", "4.00"),
            ("F", "0.00", "59.99", "0.00"),
        ]
        for grade_name, minimum, maximum, point in ranges:
            InstitutionGradeRange.objects.create(
                grade_scale=scale,
                grade_name=grade_name,
                min_percentage=minimum,
                max_percentage=maximum,
                grade_point=point,
            )

        version = InstitutionGradeScaleVersion.objects.create(
            grade_scale=scale,
            version_number=1,
            name=scale.name,
            maximum_gpa=scale.maximum_gpa,
            ranges_snapshot=[
                {
                    "grade_name": grade_name,
                    "min_percentage": minimum,
                    "max_percentage": maximum,
                    "grade_point": point,
                }
                for grade_name, minimum, maximum, point in ranges
            ],
            is_active=True,
        )
        scale.active_version = version
        scale.save(update_fields=["active_version"])
        return scale, version

    def test_grade_scale_version_does_not_increment_without_changes(self):
        from institution.models import InstitutionGradeScaleVersion

        scale, version = self._create_versioned_grade_scale()
        url = reverse(
            "institution-grade-scale-versions",
            args=[scale.id],
        )
        payload = {
            "name": scale.name,
            "maximum_gpa": "5.00",
            "ranges": version.ranges_snapshot,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["created"])
        self.assertEqual(
            InstitutionGradeScaleVersion.objects.filter(
                grade_scale=scale
            ).count(),
            1,
        )

    def test_grade_scale_version_increments_when_configuration_changes(self):
        from institution.models import InstitutionGradeScaleVersion

        scale, version = self._create_versioned_grade_scale()
        url = reverse(
            "institution-grade-scale-versions",
            args=[scale.id],
        )
        payload = {
            "name": scale.name,
            "maximum_gpa": "5.00",
            "ranges": [
                {
                    **item,
                    "grade_point": (
                        "4.50" if item["grade_name"] == "B"
                        else item["grade_point"]
                    ),
                }
                for item in version.ranges_snapshot
            ],
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["created"])
        self.assertEqual(response.data["version"]["version_number"], 2)
        self.assertEqual(
            InstitutionGradeScaleVersion.objects.filter(
                grade_scale=scale
            ).count(),
            2,
        )

    def test_grade_scale_previous_version_can_be_activated(self):
        from institution.models import (
            InstitutionGradeScaleVersion,
            InstitutionGradeRange,
        )

        scale, version1 = self._create_versioned_grade_scale()
        save_url = reverse(
            "institution-grade-scale-versions",
            args=[scale.id],
        )
        changed_ranges = [
            {
                **item,
                "grade_point": (
                    "4.50" if item["grade_name"] == "B"
                    else item["grade_point"]
                ),
            }
            for item in version1.ranges_snapshot
        ]
        response = self.client.post(
            save_url,
            {
                "name": scale.name,
                "maximum_gpa": "5.00",
                "ranges": changed_ranges,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        version2_id = response.data["version"]["id"]

        activate_url = reverse(
            "institution-grade-scale-activate-version",
            args=[scale.id, version1.id],
        )
        response = self.client.post(activate_url, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        scale.refresh_from_db()
        self.assertEqual(scale.active_version_id, version1.id)
        self.assertEqual(
            InstitutionGradeScaleVersion.objects.get(id=version1.id).is_active,
            True,
        )
        self.assertFalse(
            InstitutionGradeScaleVersion.objects.get(id=version2_id).is_active
        )
        restored = list(
            InstitutionGradeRange.objects.filter(grade_scale=scale)
            .order_by("grade_name")
            .values_list("grade_name", "grade_point")
        )
        self.assertEqual(
            [(name, str(point)) for name, point in restored],
            [("A", "5.00"), ("B", "4.00"), ("F", "0.00")],
        )


    def _create_department_admin_for_access_test(
        self, *, can_manage_students=False, can_manage_attendance=False
    ):
        from institution.models import (
            Department,
            InstitutionDepartmentAdmin,
            InstitutionDepartmentSettings,
        )

        department = Department.objects.create(
            name="Access Test Department"
        )
        self.institution.departments.add(department)

        admin = UserIdentity.objects.create(
            email="access-department-admin@example.com",
            username="access_department_admin",
        )
        InstitutionDepartmentAdmin.objects.create(
            institution=self.institution,
            department=department,
            identity=admin,
            assigned_by=self.owner,
        )
        InstitutionDepartmentSettings.objects.create(
            institution=self.institution,
            department=department,
            can_manage_students=can_manage_students,
            can_manage_attendance=can_manage_attendance,
        )
        return admin, department

    def test_department_admin_student_endpoints_require_permission(self):
        admin, _department = self._create_department_admin_for_access_test()
        self.client.force_authenticate(user=admin)

        create_response = self.client.get(
            reverse("institution-student-create")
        )
        self.assertEqual(create_response.status_code, 403, create_response.data)

        enrollment_response = self.client.get(
            reverse("institution-student-enrollment"),
            {"global_student_id": "UNKNOWN-STUDENT"},
        )
        self.assertEqual(
            enrollment_response.status_code, 403, enrollment_response.data
        )

    def test_department_admin_can_list_students_only_in_assigned_department(self):
        from institution.models import (
            Student,
            StudentEnrollment,
            StudentInstitutionIdentity,
        )

        admin, own_department = self._create_department_admin_for_access_test(
            can_manage_students=True
        )
        other_department = self._create_extra_department_for_access_test()

        own_student = Student.objects.create(
            global_student_id="RST-OWN-001",
            name="Own Department Student",
        )
        StudentInstitutionIdentity.objects.create(
            student=own_student,
            institution=self.institution,
            global_student_id=own_student.global_student_id,
        )
        StudentEnrollment.objects.create(
            student=own_student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            department=own_department,
            roll="1",
        )

        other_student = Student.objects.create(
            global_student_id="RST-OTHER-001",
            name="Other Department Student",
        )
        StudentInstitutionIdentity.objects.create(
            student=other_student,
            institution=self.institution,
            global_student_id=other_student.global_student_id,
        )
        StudentEnrollment.objects.create(
            student=other_student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            department=other_department,
            roll="2",
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("institution-student-create"))

        self.assertEqual(response.status_code, 200, response.data)
        returned_ids = {
            student["global_student_id"]
            for student in response.data["students"]
        }
        self.assertIn(own_student.global_student_id, returned_ids)
        self.assertNotIn(other_student.global_student_id, returned_ids)

    def test_department_admin_cannot_access_other_department_student_enrollment(self):
        from institution.models import (
            Student,
            StudentEnrollment,
            StudentInstitutionIdentity,
        )

        admin, _own_department = self._create_department_admin_for_access_test(
            can_manage_students=True
        )
        other_department = self._create_extra_department_for_access_test()

        student = Student.objects.create(
            global_student_id="RST-OTHER-002",
            name="Restricted Department Student",
        )
        StudentInstitutionIdentity.objects.create(
            student=student,
            institution=self.institution,
            global_student_id=student.global_student_id,
        )
        StudentEnrollment.objects.create(
            student=student,
            institution=self.institution,
            academic_session=self.session,
            class_name=self.level.name,
            department=other_department,
            roll="3",
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            reverse("institution-student-enrollment"),
            {"global_student_id": student.global_student_id},
        )

        self.assertEqual(response.status_code, 403, response.data)

    def test_department_admin_attendance_endpoints_require_permission(self):
        admin, _department = self._create_department_admin_for_access_test()
        self.client.force_authenticate(user=admin)

        monthly_response = self.client.get(
            reverse("institution-attendance-monthly"),
            {"year": 2026, "month": 10},
        )
        self.assertEqual(
            monthly_response.status_code, 403, monthly_response.data
        )

        save_response = self.client.post(
            reverse("institution-student-attendance-save"),
            {"date": "2026-10-25", "enrollment_id": 999999, "status": "P"},
            format="json",
        )
        self.assertEqual(save_response.status_code, 403, save_response.data)

    def test_department_admin_cannot_change_attendance_for_other_department(self):
        from datetime import date
        from institution.models import StudentEnrollment

        admin, assigned_department = self._create_department_admin_for_access_test(
            can_manage_attendance=True
        )
        _exam_subject, enrollment = self._create_exam_subject_and_enrollment()

        other_department = self._create_extra_department_for_access_test()
        enrollment.department = other_department
        enrollment.save(update_fields=["department"])

        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("institution-student-attendance-save"),
            {
                "date": date.today().isoformat(),
                "enrollment_id": enrollment.id,
                "status": "P",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404, response.data)

    def test_department_admin_can_save_attendance_in_assigned_department(self):
        from datetime import date
        from institution.models import StudentAttendance

        admin, department = self._create_department_admin_for_access_test(
            can_manage_attendance=True
        )
        _exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        enrollment.department = department
        enrollment.save(update_fields=["department"])

        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("institution-student-attendance-save"),
            {
                "date": date.today().isoformat(),
                "enrollment_id": enrollment.id,
                "status": "P",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            StudentAttendance.objects.filter(
                enrollment=enrollment,
                date=date.today(),
                status="P",
            ).exists()
        )

    def test_department_admin_can_save_marks_in_assigned_department(self):
        from institution.models import (
            InstitutionDepartmentSettings,
            InstitutionExamMark,
        )

        admin, department = self._create_department_admin_for_access_test()
        InstitutionDepartmentSettings.objects.update_or_create(
            institution=self.institution,
            department=department,
            defaults={"can_manage_marks": True},
        )
        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        enrollment.department = department
        enrollment.save(update_fields=["department"])

        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("institution-exam-marks", args=[exam_subject.id]),
            {
                "enrollment_id": enrollment.id,
                "marks_obtained": "75",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            InstitutionExamMark.objects.filter(
                exam_subject=exam_subject,
                enrollment=enrollment,
                marks_obtained=75,
            ).exists()
        )

    def test_department_admin_can_access_results_for_assigned_department(self):
        from institution.models import InstitutionDepartmentSettings

        admin, department = self._create_department_admin_for_access_test()
        InstitutionDepartmentSettings.objects.update_or_create(
            institution=self.institution,
            department=department,
            defaults={"can_manage_results": True},
        )
        exam_subject, enrollment = self._create_exam_subject_and_enrollment()
        enrollment.department = department
        enrollment.save(update_fields=["department"])

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            reverse("institution-exam-results", args=[exam_subject.exam_id])
        )

        self.assertEqual(response.status_code, 200, response.data)
        returned_ids = {
            item["enrollment_id"] for item in response.data["results"]
        }
        self.assertIn(enrollment.id, returned_ids)

    def _create_extra_department_for_access_test(self):
        from institution.models import Department

        department = Department.objects.create(
            name="Other Access Test Department"
        )
        self.institution.departments.add(department)
        return department


class StudentSubjectAPITests(APITestCase):
    def setUp(self):
        from institution.models import StudentSubject

        country_model = apps.get_model("organization", "Country")
        region_model = country_model._meta.get_field(
            "region"
        ).remote_field.model

        region = region_model.objects.create(name="Student Subject Test Region")
        country = country_model.objects.create(
            region=region,
            name="Student Subject Test Country",
            code="SST",
        )

        group = InstitutionTypeGroup.objects.create(
            name="Student Subject Test Group"
        )
        institution_type = InstitutionType.objects.create(
            group=group,
            name="Student Subject Test Type",
        )

        self.owner = UserIdentity.objects.create(
            email="student-subject-owner@example.com",
            username="student_subject_owner",
        )
        self.other_owner = UserIdentity.objects.create(
            email="student-subject-other@example.com",
            username="student_subject_other",
        )
        self.admin = UserIdentity.objects.create(
            email="student-subject-admin@example.com",
            username="student_subject_admin",
            is_staff=True,
        )

        self.institution = InstitutionProfile.objects.create(
            identity=self.owner,
            institution_name="Student Subject Test Institution",
            institution_type=institution_type,
            country=country,
        )
        self.other_institution = InstitutionProfile.objects.create(
            identity=self.other_owner,
            institution_name="Other Student Subject Institution",
            institution_type=institution_type,
            country=country,
        )

        self.list_url = reverse("institution-student-subjects")
        self.detail_url = lambda subject_id: reverse(
            "institution-student-subject-detail",
            kwargs={"student_subject_id": subject_id},
        )
        self.StudentSubject = StudentSubject

    def test_owner_can_create_global_subject(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.list_url,
            {"name": "Bangla", "code": "BAN"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        subject = self.StudentSubject.objects.get(id=response.data["id"])
        self.assertIsNone(subject.institution_id)
        self.assertEqual(subject.created_by, self.owner)
        self.assertEqual(subject.name, "Bangla")
        self.assertEqual(response.data["scope"], "global")

    def test_admin_can_create_global_subject(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.list_url,
            {"name": "Global Mathematics", "code": "GM"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        subject = self.StudentSubject.objects.get(id=response.data["id"])
        self.assertIsNone(subject.institution_id)
        self.assertEqual(subject.created_by, self.admin)

    def test_owner_cannot_rename_global_subject_even_if_owner_created_it(self):
        subject = self.StudentSubject.objects.create(
            name="Science",
            institution=None,
            created_by=self.owner,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            self.detail_url(subject.id),
            {"name": "General Science"},
            format="json",
        )

        self.assertEqual(response.status_code, 403, response.data)
        subject.refresh_from_db()
        self.assertEqual(subject.name, "Science")

    def test_owner_cannot_deactivate_global_subject(self):
        subject = self.StudentSubject.objects.create(
            name="Global History",
            institution=None,
            created_by=self.owner,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            self.detail_url(subject.id),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, 403, response.data)
        subject.refresh_from_db()
        self.assertTrue(subject.is_active)

    def test_admin_can_rename_global_subject_without_changing_id(self):
        subject = self.StudentSubject.objects.create(
            name="Bangla",
            institution=None,
            created_by=self.owner,
        )
        original_id = subject.id
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.detail_url(subject.id),
            {"name": "Bengali Language"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        subject.refresh_from_db()
        self.assertEqual(subject.id, original_id)
        self.assertEqual(subject.name, "Bengali Language")

    def test_admin_can_deactivate_global_subject(self):
        subject = self.StudentSubject.objects.create(
            name="Global Geography",
            institution=None,
            created_by=self.owner,
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.detail_url(subject.id),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        subject.refresh_from_db()
        self.assertFalse(subject.is_active)

    def test_duplicate_global_subject_name_is_rejected_case_insensitively(self):
        self.StudentSubject.objects.create(
            name="Bangla",
            institution=None,
            created_by=self.owner,
        )
        self.client.force_authenticate(user=self.other_owner)

        response = self.client.post(
            self.list_url,
            {"name": "BANGLA", "code": "BAN"},
            format="json",
        )

        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(
            self.StudentSubject.objects.filter(name__iexact="Bangla").count(),
            1,
        )

    def test_owner_can_list_global_subjects_created_by_others(self):
        subject = self.StudentSubject.objects.create(
            name="Global English",
            institution=None,
            created_by=self.admin,
        )
        self.client.force_authenticate(user=self.other_owner)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200, response.data)
        returned_ids = [item["id"] for item in response.data["results"]]
        self.assertIn(subject.id, returned_ids)

    def test_unauthenticated_request_is_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertIn(response.status_code, (401, 403))


    def test_admin_can_delete_global_subject(self):
        subject = self.StudentSubject.objects.create(
            name="Global Biology",
            institution=None,
            created_by=self.owner,
        )
        subject_id = subject.id
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.detail_url(subject_id))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            self.StudentSubject.objects.filter(id=subject_id).exists()
        )

    def test_owner_cannot_delete_global_subject(self):
        subject = self.StudentSubject.objects.create(
            name="Global Physics",
            institution=None,
            created_by=self.owner,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.detail_url(subject.id))

        self.assertEqual(response.status_code, 403, response.data)
        self.assertTrue(
            self.StudentSubject.objects.filter(id=subject.id).exists()
        )


class InstitutionExamTypeAPITests(APITestCase):
    def setUp(self):
        from institution.models import (
            CentralExamType,
            InstitutionExamTypeSelection,
        )

        country_model = apps.get_model("organization", "Country")
        region_model = country_model._meta.get_field(
            "region"
        ).remote_field.model
        region = region_model.objects.create(name="Exam Type Test Region")
        country = country_model.objects.create(
            region=region,
            name="Exam Type Test Country",
            code="ETT",
        )
        group = InstitutionTypeGroup.objects.create(
            name="Exam Type Test Group"
        )
        institution_type = InstitutionType.objects.create(
            group=group,
            name="Exam Type Test Institution Type",
        )

        self.owner = UserIdentity.objects.create(
            email="exam-type-owner@example.com",
            username="exam_type_owner",
        )
        self.other_owner = UserIdentity.objects.create(
            email="exam-type-other@example.com",
            username="exam_type_other",
        )
        self.admin = UserIdentity.objects.create(
            email="exam-type-admin@example.com",
            username="exam_type_admin",
            is_staff=True,
        )

        self.institution = InstitutionProfile.objects.create(
            identity=self.owner,
            institution_name="Exam Type Test Institution",
            institution_type=institution_type,
            country=country,
        )
        self.other_institution = InstitutionProfile.objects.create(
            identity=self.other_owner,
            institution_name="Other Exam Type Institution",
            institution_type=institution_type,
            country=country,
        )

        self.url = reverse("institution-exam-types")
        self.CentralExamType = CentralExamType
        self.InstitutionExamTypeSelection = InstitutionExamTypeSelection

    def test_anonymous_user_cannot_create_global_exam_type(self):
        response = self.client.post(
            self.url,
            {"name": "Anonymous Exam Type"},
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(
            self.CentralExamType.objects.filter(
                name="Anonymous Exam Type"
            ).exists()
        )

    def test_owner_can_select_existing_exam_type(self):
        exam_type = self.CentralExamType.objects.create(name="Annual Exam")
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"exam_type_id": exam_type.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            self.InstitutionExamTypeSelection.objects.filter(
                institution=self.institution,
                exam_type=exam_type,
            ).exists()
        )

    def test_repeated_selection_does_not_create_duplicate(self):
        exam_type = self.CentralExamType.objects.create(name="Half Yearly Exam")
        self.client.force_authenticate(user=self.owner)

        first = self.client.post(
            self.url,
            {"exam_type_id": exam_type.id},
            format="json",
        )
        second = self.client.post(
            self.url,
            {"exam_type_id": exam_type.id},
            format="json",
        )

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(
            self.InstitutionExamTypeSelection.objects.filter(
                institution=self.institution,
                exam_type=exam_type,
            ).count(),
            1,
        )

    def test_exam_type_selection_is_institution_specific(self):
        exam_type = self.CentralExamType.objects.create(name="Model Test")
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.url,
            {"exam_type_id": exam_type.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        self.client.force_authenticate(user=self.other_owner)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200, response.data)
        item = next(
            result
            for result in response.data["results"]
            if result["id"] == exam_type.id
        )
        self.assertFalse(item["selected"])

    def test_owner_can_remove_only_their_selection(self):
        exam_type = self.CentralExamType.objects.create(name="Test Exam")
        self.InstitutionExamTypeSelection.objects.create(
            institution=self.institution,
            exam_type=exam_type,
        )
        self.InstitutionExamTypeSelection.objects.create(
            institution=self.other_institution,
            exam_type=exam_type,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(
            f"{self.url}?exam_type_id={exam_type.id}",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(
            self.InstitutionExamTypeSelection.objects.filter(
                institution=self.institution,
                exam_type=exam_type,
            ).exists()
        )
        self.assertTrue(
            self.InstitutionExamTypeSelection.objects.filter(
                institution=self.other_institution,
                exam_type=exam_type,
            ).exists()
        )
