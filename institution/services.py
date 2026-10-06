from django.db import transaction

from institution.models import (
    InstitutionProfile,
    Student,
    StudentIdSequence,
    StudentInstitutionIdentity,
)


@transaction.atomic
def generate_global_student_id(institution: InstitutionProfile) -> str:
    """
    Generate the next permanent Global Student ID for an institution.

    Example:
        DUDHB-000001
        DUDHB-000002
    """

    if not institution.global_identity_code:
        raise ValueError(
            "Institution must have a Global Institution Identity Code "
            "before creating a student."
        )

    sequence, _ = StudentIdSequence.objects.select_for_update().get_or_create(
        institution=institution,
        defaults={"next_number": 1},
    )

    number = sequence.next_number

    sequence.next_number = number + 1
    sequence.save(update_fields=["next_number", "updated_at"])

    return f"{institution.global_identity_code}-{number:06d}"



@transaction.atomic
def get_or_create_student_institution_identity(
    student: Student,
    institution: InstitutionProfile,
) -> StudentInstitutionIdentity:
    """
    Return the student's identity for an institution.

    Same student + same institution:
        Reuse the existing institution-specific ID.

    Same student + different institution:
        Create a new institution-specific ID and preserve all
        previous institution identities.
    """

    identity = (
        StudentInstitutionIdentity.objects
        .select_for_update()
        .filter(
            student=student,
            institution=institution,
        )
        .first()
    )

    if identity:
        return identity

    institution_student_id = generate_global_student_id(institution)

    return StudentInstitutionIdentity.objects.create(
        student=student,
        institution=institution,
        global_student_id=institution_student_id,
    )
