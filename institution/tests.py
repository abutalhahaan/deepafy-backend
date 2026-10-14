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

    def test_published_exam_rejects_grade_range_changes(self):
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

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("Unpublish the exam first.", response.data["detail"])
        self.assertFalse(scale.ranges.exists())
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

    def test_published_exam_prevents_grade_range_update_and_delete(self):
        from institution.models import (
            InstitutionGradeScale,
            InstitutionGradeRange,
            InstitutionExam,
        )

        scale = InstitutionGradeScale.objects.create(
            institution=self.institution,
            name="Protected Grade Scale",
        )
        grade = InstitutionGradeRange.objects.create(
            grade_scale=scale,
            grade_name="A",
            min_percentage=80,
            max_percentage=100,
            grade_point=5,
        )
        InstitutionExam.objects.create(
            institution=self.institution,
            academic_session=self.session,
            academic_level=self.level,
            name="Published Protection Test",
            category="INTERNAL",
            exam_type="Class Test",
            full_marks=100,
            pass_mark=33,
            grade_scale=scale,
            is_published=True,
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

        self.assertEqual(update_response.status_code, 400)
        self.assertEqual(delete_response.status_code, 400)
        grade.refresh_from_db()
        self.assertEqual(grade.grade_name, "A")

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
        self.assertIn("Unpublish the exam first.", response.data["detail"])
        self.assertEqual(
            InstitutionExamSubject.objects.filter(exam=exam).count(),
            1,
        )

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
