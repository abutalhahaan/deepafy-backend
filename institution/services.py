from django.db import transaction

from institution.models import InstitutionProfile, StudentIdSequence


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
