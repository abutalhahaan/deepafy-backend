from django.db import models
from django.core.validators import RegexValidator


class Subject(models.Model):
    """
    Global Deepafy subject master.

    An institution can create a new subject. Once created,
    the subject becomes available to other institutions
    for selection.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
    )

    code = models.CharField(
        max_length=100,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class InstitutionTypeGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class InstitutionType(models.Model):
    group = models.ForeignKey(
        InstitutionTypeGroup,
        on_delete=models.PROTECT,
        related_name="institution_types",
    )
    name = models.CharField(max_length=150)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group", "sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "name"],
                name="unique_institution_type_per_group",
            )
        ]

    def __str__(self):
        return f"{self.group.name} - {self.name}"


class InstitutionAffiliationType(models.TextChoices):
    EDUCATION_BOARD = "education_board", "Education Board"
    ACADEMIC_AFFILIATION = "academic_affiliation", "Academic Affiliation"
    REGULATORY_AUTHORITY = "regulatory_authority", "Regulatory Authority"
    GOVERNING_AUTHORITY = "governing_authority", "Governing Authority"


class InstitutionAuthority(models.Model):
    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        related_name="institution_authorities",
    )

    institution_types = models.ManyToManyField(
        InstitutionType,
        related_name="authorities",
        blank=True,
    )

    name = models.CharField(max_length=255)

    short_name = models.CharField(
        max_length=100,
        blank=True,
    )

    relationship_type = models.CharField(
        max_length=40,
        choices=InstitutionAffiliationType.choices,
    )

    code = models.CharField(
        max_length=100,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "country",
                    "name",
                    "relationship_type",
                ],
                name="unique_country_authority_relationship",
            )
        ]

    def __str__(self):
        return self.name


class InstitutionAcademicLevel(models.Model):
    institution = models.ForeignKey(
        "InstitutionProfile",
        on_delete=models.CASCADE,
        related_name="academic_levels",
    )

    level_type = models.CharField(
        max_length=50,
        default="Class",
    )

    name = models.CharField(
        max_length=100,
    )

    parent = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "institution",
                    "level_type",
                    "name",
                    "parent",
                ],
                name="unique_institution_academic_level",
            )
        ]
        indexes = [
            models.Index(
                fields=["institution", "level_type"],
                name="academic_level_inst_type_idx",
            ),
            models.Index(
                fields=["institution", "name"],
                name="academic_level_inst_name_idx",
            ),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.level_type}: {self.name} ({self.parent})"
        return f"{self.level_type}: {self.name}"


class InstitutionAdmissionType(models.Model):
    """
    Institution-specific admission type master.

    Admission types are managed independently from academic levels so
    each institution can use the admission workflow that applies to it.
    """

    institution = models.ForeignKey(
        "InstitutionProfile",
        on_delete=models.CASCADE,
        related_name="admission_types",
    )

    name = models.CharField(
        max_length=100,
    )

    code = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_institution_admission_type",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "is_active"],
                name="admission_type_inst_active_idx",
            ),
        ]

    def __str__(self):
        return self.name


class InstitutionAcademicData(models.Model):
    institution = models.ForeignKey(
        "InstitutionProfile",
        on_delete=models.CASCADE,
        related_name="academic_data",
    )

    date = models.DateField()

    category = models.CharField(
        max_length=100,
        help_text="Students, Teachers, Staff, Class 1, Class 2, etc.",
    )

    total = models.PositiveIntegerField(default=0)
    male = models.PositiveIntegerField(default=0)
    female = models.PositiveIntegerField(default=0)

    # Daily gender-wise attendance
    male_present = models.PositiveIntegerField(default=0)
    male_leave = models.PositiveIntegerField(default=0)
    female_present = models.PositiveIntegerField(default=0)
    female_leave = models.PositiveIntegerField(default=0)

    # Calculated aggregate attendance
    present = models.PositiveIntegerField(default=0)
    leave = models.PositiveIntegerField(default=0)
    absent = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "category"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "date", "category"],
                name="unique_institution_academic_date_category",
            )
        ]
        indexes = [
            models.Index(
                fields=["institution", "date"],
                name="academic_institution_date_idx",
            ),
            models.Index(
                fields=["institution", "category"],
                name="academic_inst_cat_idx",
            ),
        ]

    def __str__(self):
        return f"{self.institution.institution_name} - {self.category} - {self.date}"


class InstitutionProfile(models.Model):
    identity = models.OneToOneField(
        "identity.UserIdentity",
        on_delete=models.CASCADE,
        related_name="institution_profile",
    )

    institution_name = models.CharField(
        max_length=255,
    )

    institution_type = models.ForeignKey(
        InstitutionType,
        on_delete=models.PROTECT,
        related_name="institutions",
    )

    institution_types = models.ManyToManyField(
        InstitutionType,
        related_name="institution_profiles",
        blank=True,
    )

    affiliations = models.ManyToManyField(
        InstitutionAuthority,
        related_name="institution_profiles",
        blank=True,
    )

    established_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    tagline = models.CharField(
        max_length=500,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    mission = models.TextField(
        blank=True,
    )

    vision = models.TextField(
        blank=True,
    )

    total_students = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    total_teachers = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    total_staff = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    management_type = models.CharField(
        max_length=30,
        blank=True,
        choices=[
            ('government', 'Government'),
            ('non_government', 'Non-Government'),
        ],
    )

    mpo_status = models.CharField(
        max_length=30,
        blank=True,
        choices=[
            ('mpo', 'MPO'),
            ('non_mpo', 'Non-MPO'),
            ('not_applicable', 'Not Applicable'),
        ],
    )

    institution_code = models.CharField(
        max_length=100,
        blank=True,
    )

    global_identity_code = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z0-9]{3,8}$",
                message="Global Identity Code must be 3 to 8 English letters or numbers.",
            )
        ],
    )

    eiin = models.CharField(
        max_length=50,
        blank=True,
    )

    affiliation_board = models.CharField(
        max_length=255,
        blank=True,
    )

    map_location_url = models.URLField(
        max_length=1000,
        blank=True,
    )

    map_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    map_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        related_name="institution_profiles",
    )

    administrative_location = models.ForeignKey(
        "organization.AdministrativeLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="institution_profiles",
    )

    full_address = models.TextField(
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    logo = models.ImageField(
        upload_to="institution_logos/",
        null=True,
        blank=True,
    )

    cover_photo = models.ImageField(
        upload_to="institution_covers/",
        null=True,
        blank=True,
    )

    featured_image = models.ImageField(
        upload_to="institution_featured/",
        null=True,
        blank=True,
    )

    background_color = models.CharField(
        max_length=20,
        default="#FFFFFF",
    )

    background_image = models.ImageField(
        upload_to="institution_backgrounds/",
        null=True,
        blank=True,
    )

    tab_colors = models.JSONField(
        default=dict,
        blank=True,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def save(self, *args, **kwargs):
        if self.global_identity_code:
            self.global_identity_code = self.global_identity_code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            self.institution_name
            or f"Institution - {self.identity.user_id}"
        )



class InstitutionAcademicSession(models.Model):
    STATUS_UPCOMING = "UPCOMING"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_CLOSED = "CLOSED"
    STATUS_ARCHIVED = "ARCHIVED"

    STATUS_CHOICES = [
        (STATUS_UPCOMING, "Upcoming"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    institution = models.ForeignKey(
        InstitutionProfile,
        on_delete=models.CASCADE,
        related_name="academic_sessions",
    )

    name = models.CharField(max_length=100)

    start_date = models.DateField()

    end_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_UPCOMING,
    )

    is_current = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_institution_academic_session",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "status"],
                name="acad_sess_inst_status_idx",
            ),
            models.Index(
                fields=["institution", "is_current"],
                name="acad_sess_inst_current_idx",
            ),
        ]

    def __str__(self):
        return f"{self.institution.institution_name} - {self.name}"

class UnclaimedPerson(models.Model):
    STATUS_RUNNING = "RUNNING"
    STATUS_FORMER = "FORMER"
    STATUS_RETIRED = "RETIRED"
    STATUS_IN_MEMORY = "IN_MEMORY"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_FORMER, "Former Staff"),
        (STATUS_RETIRED, "Retired Alumni"),
        (STATUS_IN_MEMORY, "In Memory"),
    ]

    institution = models.ForeignKey(
        InstitutionProfile,
        on_delete=models.CASCADE,
        related_name="unclaimed_people",
    )

    full_name = models.CharField(max_length=255)

    profile_photo = models.ImageField(
        upload_to="institution_staff/unclaimed/",
        null=True,
        blank=True,
    )

    designation = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True)
    employment_type = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField()
    retirement_date = models.DateField(null=True, blank=True)
    leaving_date = models.DateField(null=True, blank=True)
    passing_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
    )

    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-joining_date", "full_name"]
        indexes = [
            models.Index(
                fields=["institution", "status"],
                name="unclaimed_status_idx",
            ),
            models.Index(
                fields=["institution", "full_name"],
                name="unclaimed_name_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.full_name} - {self.designation} - "
            f"{self.institution.institution_name}"
        )


class UnclaimedPersonQualification(models.Model):
    """
    Educational qualification for a manually added institution staff member.
    One UnclaimedPerson can have multiple qualifications.
    """

    person = models.ForeignKey(
        UnclaimedPerson,
        on_delete=models.CASCADE,
        related_name="educational_qualifications",
    )

    education_level = models.CharField(max_length=100)
    degree_certificate = models.CharField(max_length=255)
    field_of_study = models.CharField(
        max_length=255,
        blank=True,
    )
    specialization = models.CharField(
        max_length=255,
        blank=True,
    )
    start_year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    end_year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-end_year", "-start_year", "id"]

    def __str__(self):
        return (
            f"{self.person.full_name} - "
            f"{self.degree_certificate}"
        )


class InstitutionStaffService(models.Model):
    """
    Institution-specific employment/service record for a Deepafy Identity.

    The Identity represents the person globally.
    This model represents that person's service at one institution.
    """

    STATUS_RUNNING = "RUNNING"
    STATUS_FORMER = "FORMER"
    STATUS_RETIRED = "RETIRED"
    STATUS_IN_MEMORY = "IN_MEMORY"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_FORMER, "Former Staff"),
        (STATUS_RETIRED, "Retired Alumni"),
        (STATUS_IN_MEMORY, "In Memory"),
    ]

    institution = models.ForeignKey(
        InstitutionProfile,
        on_delete=models.CASCADE,
        related_name="staff_services",
    )

    identity = models.ForeignKey(
        "identity.UserIdentity",
        on_delete=models.PROTECT,
        related_name="institution_staff_services",
    )

    subjects = models.ManyToManyField(
        Subject,
        related_name="staff_services",
        blank=True,
    )

    designation = models.CharField(
        max_length=255,
    )

    department = models.CharField(
        max_length=255,
        blank=True,
    )

    employment_type = models.CharField(
        max_length=100,
        blank=True,
    )

    joining_date = models.DateField()

    retirement_date = models.DateField(
        null=True,
        blank=True,
    )

    leaving_date = models.DateField(
        null=True,
        blank=True,
    )

    passing_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
    )

    bio = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-joining_date",
            "identity_id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "identity"],
                name="unique_institution_staff_identity",
            )
        ]
        indexes = [
            models.Index(
                fields=["institution", "status"],
                name="inst_staff_status_idx",
            ),
            models.Index(
                fields=["identity", "status"],
                name="identity_staff_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.identity.username or self.identity.user_id} - "
            f"{self.designation} - "
            f"{self.institution.institution_name}"
        )

class StudentIdSequence(models.Model):
    """
    Permanent per-institution sequence for Global Student IDs.

    Example:
        DUDHB-000001
        DUDHB-000002
        DUDHB-000003
    """

    institution = models.OneToOneField(
        InstitutionProfile,
        on_delete=models.PROTECT,
        related_name="student_id_sequence",
    )

    next_number = models.PositiveBigIntegerField(
        default=1,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.institution.institution_name} - "
            f"Next Student Number: {self.next_number}"
        )


class Student(models.Model):
    """
    Global student identity.

    A student has one permanent Deepafy Student record.
    Institution-specific academic information belongs to StudentEnrollment.
    """

    STATUS_ACTIVE = "ACTIVE"
    STATUS_INACTIVE = "INACTIVE"
    STATUS_DECEASED = "DECEASED"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
        (STATUS_DECEASED, "Deceased"),
    ]

    global_student_id = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    name = models.CharField(max_length=255)

    father_name = models.CharField(
        max_length=255,
        blank=True,
    )

    mother_name = models.CharField(
        max_length=255,
        blank=True,
    )

    gender = models.CharField(
        max_length=20,
        blank=True,
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
    )

    blood_group = models.CharField(
        max_length=10,
        blank=True,
    )

    mobile = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    present_location = models.ForeignKey(
        "organization.AdministrativeLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students_present",
    )

    present_address = models.TextField(
        blank=True,
    )

    permanent_location = models.ForeignKey(
        "organization.AdministrativeLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students_permanent",
    )

    permanent_address = models.TextField(
        blank=True,
    )

    guardian_name = models.CharField(
        max_length=255,
        blank=True,
    )

    guardian_relationship = models.CharField(
        max_length=100,
        blank=True,
    )

    guardian_mobile = models.CharField(
        max_length=30,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.global_student_id} - {self.name}"


class StudentInstitutionIdentity(models.Model):
    """
    Institution-specific identity for a student.

    A student keeps a separate Student ID in each institution.
    Previous institution IDs remain preserved as historical identities.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="institution_identities",
    )

    institution = models.ForeignKey(
        InstitutionProfile,
        on_delete=models.PROTECT,
        related_name="student_identities",
    )

    global_student_id = models.CharField(
        max_length=30,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "global_student_id"],
                name="unique_student_id_per_institution",
            ),
            models.UniqueConstraint(
                fields=["student", "institution"],
                name="unique_student_institution_identity",
            ),
        ]

    def __str__(self):
        return (
            f"{self.global_student_id} - "
            f"{self.institution.institution_name}"
        )


class InstitutionAttendanceSettings(models.Model):
    """
    Institution-level attendance configuration.

    Weekly holidays are controlled by the institution.
    Weekday values follow Python's convention:
    Monday=0 ... Sunday=6.
    """

    institution = models.OneToOneField(
        InstitutionProfile,
        on_delete=models.CASCADE,
        related_name="attendance_settings",
    )

    weekly_holidays = models.JSONField(
        default=list,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Attendance Settings - {self.institution}"


class InstitutionHoliday(models.Model):
    """
    Institution-specific holiday date range within an academic session.
    """

    institution = models.ForeignKey(
        InstitutionProfile,
        on_delete=models.CASCADE,
        related_name="attendance_holidays",
    )

    academic_session = models.ForeignKey(
        "InstitutionAcademicSession",
        on_delete=models.CASCADE,
        related_name="holidays",
        null=True,
        blank=True,
    )

    from_date = models.DateField()

    to_date = models.DateField()

    name = models.CharField(
        max_length=255,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    @property
    def total_days(self):
        return (self.to_date - self.from_date).days + 1

    class Meta:
        ordering = ["from_date"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "institution",
                    "academic_session",
                    "from_date",
                    "to_date",
                ],
                name="unique_institution_holiday_range",
            ),
        ]

    def __str__(self):
        return f"{self.institution} - {self.from_date} to {self.to_date} - {self.name}"


class StudentAttendance(models.Model):
    """
    Daily attendance linked to the student's institution enrollment.

    The enrollment remains the source of the student's academic identity.
    """

    STATUS_PRESENT = "P"
    STATUS_ABSENT = "A"
    STATUS_LEAVE = "L"

    STATUS_CHOICES = [
        (STATUS_PRESENT, "Present"),
        (STATUS_ABSENT, "Absent"),
        (STATUS_LEAVE, "Leave"),
    ]

    enrollment = models.ForeignKey(
        "StudentEnrollment",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )

    date = models.DateField()

    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default=STATUS_PRESENT,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "date"],
                name="unique_enrollment_attendance_date",
            ),
        ]
        indexes = [
            models.Index(
                fields=["enrollment", "date"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.enrollment.student.global_student_id} - "
            f"{self.date} - {self.status}"
        )


class StudentProfilePhoto(models.Model):
    """
    Historical student profile photos.

    A photo can be associated with an academic year/session without
    overwriting previous photos.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="profile_photos",
    )

    academic_year = models.PositiveSmallIntegerField()

    photo = models.ImageField(
        upload_to="student_profile_photos/",
    )

    is_current = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-academic_year", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_year"],
                name="unique_student_photo_academic_year",
            ),
        ]

    def __str__(self):
        return f"{self.student.global_student_id} - {self.academic_year}"


class StudentEnrollment(models.Model):
    """
    Institution-specific academic enrollment.

    A student can have multiple enrollments across institutions and
    academic sessions while keeping the same Global Student ID.
    """

    STATUS_RUNNING = "RUNNING"
    STATUS_GRADUATED = "GRADUATED"
    STATUS_TRANSFERRED = "TRANSFERRED"
    STATUS_DROPPED = "DROPPED"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_GRADUATED, "Graduated"),
        (STATUS_TRANSFERRED, "Transferred"),
        (STATUS_DROPPED, "Dropped"),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )

    institution = models.ForeignKey(
        InstitutionProfile,
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )

    academic_session = models.ForeignKey(
        "InstitutionAcademicSession",
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )

    class_name = models.CharField(
        max_length=255,
    )

    department = models.ForeignKey(
        "Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="student_enrollments",
    )

    section = models.CharField(
        max_length=100,
        blank=True,
    )

    roll = models.CharField(
        max_length=100,
        blank=True,
    )

    admission_date = models.DateField(
        null=True,
        blank=True,
    )

    PREVIOUS_INSTITUTION_NA = "N/A"
    PREVIOUS_INSTITUTION_MANUAL = "MANUAL"
    PREVIOUS_INSTITUTION_DEEPAFY = "DEEPAFY"

    PREVIOUS_INSTITUTION_TYPE_CHOICES = [
        (PREVIOUS_INSTITUTION_NA, "N/A"),
        (PREVIOUS_INSTITUTION_MANUAL, "Manual"),
        (PREVIOUS_INSTITUTION_DEEPAFY, "Deepafy Institution"),
    ]

    previous_institution_type = models.CharField(
        max_length=20,
        choices=PREVIOUS_INSTITUTION_TYPE_CHOICES,
        default=PREVIOUS_INSTITUTION_NA,
    )

    previous_institution_profile = models.ForeignKey(
        InstitutionProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_student_enrollments",
    )

    previous_institution_name = models.CharField(
        max_length=255,
        blank=True,
    )

    previous_institution = models.CharField(
        max_length=255,
        blank=True,
    )

    admission_type = models.CharField(
        max_length=100,
        blank=True,
    )

    admission_type_master = models.ForeignKey(
        "InstitutionAdmissionType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_enrollments",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "student",
                    "institution",
                    "academic_session",
                ],
                name="unique_student_institution_session",
            ),
        ]

    def __str__(self):
        return (
            f"{self.student.global_student_id} - "
            f"{self.institution.institution_name} - "
            f"{self.academic_session.name}"
        )


class StudentEnrollmentAcademicValue(models.Model):
    """
    Dynamic academic value for an institution-specific student enrollment.

    The academic level definition comes from InstitutionAcademicLevel.
    This allows different institution types to use different academic
    structures without forcing Department/Class/Section fields everywhere.
    """

    enrollment = models.ForeignKey(
        StudentEnrollment,
        on_delete=models.CASCADE,
        related_name="academic_values",
    )

    academic_level = models.ForeignKey(
        InstitutionAcademicLevel,
        on_delete=models.PROTECT,
        related_name="student_values",
    )

    value = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["academic_level__created_at", "academic_level__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "academic_level"],
                name="unique_enrollment_academic_level_value",
            ),
        ]
        indexes = [
            models.Index(
                fields=["enrollment", "academic_level"],
                name="enrollment_academic_level_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.enrollment.student.global_student_id} - "
            f"{self.academic_level.name}: {self.value}"
        )


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
