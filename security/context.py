from django.db.models import F
from identity.models import (
    AccountType,
    PersonalAccount,
    ProfessionalAccount,
)
from companies.models import (
    CompanyRelationship,
    AdministrativeAssignment,
)
from institution.models import (
    InstitutionProfile,
    InstitutionDepartmentAdmin,
)


def get_available_account_contexts(identity):
    """
    Return all active account contexts available to an identity.

    Authentication and permission authorization remain separate.
    """

    if (
        identity is None
        or not getattr(identity, "pk", None)
        or not identity.is_active
        or identity.status != identity.Status.ACTIVE
    ):
        return []

    contexts = []

    active_account_types = {
        account.account_type: account
        for account in AccountType.objects.filter(
            identity=identity,
            is_active=True,
        )
    }

    # Personal Account
    personal_type = active_account_types.get(
        AccountType.Type.PERSONAL
    )

    if personal_type:
        personal = PersonalAccount.objects.filter(
            identity=identity,
            is_active=True,
        ).first()

        if personal:
            contexts.append({
                "context_type": "personal",
                "context_id": str(personal.pk),
                "label": personal.display_name or personal.username or "Personal Account",
                "role": "owner",
                "is_primary": personal_type.is_primary,
                "metadata": {
                    "account_type_id": personal_type.pk,
                },
            })

    # Professional Account
    professional_type = active_account_types.get(
        AccountType.Type.PROFESSIONAL
    )

    if professional_type:
        professional = ProfessionalAccount.objects.filter(
            identity=identity,
            is_active=True,
        ).first()

        if professional:
            contexts.append({
                "context_type": "professional",
                "context_id": str(professional.pk),
                "label": professional.professional_title or "Professional Account",
                "role": "owner",
                "is_primary": professional_type.is_primary,
                "metadata": {
                    "account_type_id": professional_type.pk,
                },
            })

    # Company contexts
    company_relationships = (
        CompanyRelationship.objects.filter(
            identity=identity,
            membership_status=CompanyRelationship.MembershipStatus.ACTIVE,
        )
        .select_related("company")
        .order_by("company__name", "id")
    )

    for relationship in company_relationships:
        contexts.append({
            "context_type": "company",
            "context_id": str(relationship.company.company_id),
            "label": relationship.company.name,
            "role": relationship.relationship_type,
            "is_primary": False,
            "metadata": {
                "relationship_id": relationship.pk,
                "membership_status": relationship.membership_status,
            },
        })

    # Institution owner contexts
    institutions = list(
        InstitutionProfile.objects.filter(
            identity=identity,
            is_active=True,
        ).order_by("institution_name", "id")
    )

    institution_account_type = active_account_types.get(
        AccountType.Type.INSTITUTION
    )
    institution_is_primary = bool(
        institution_account_type
        and institution_account_type.is_primary
        and len(institutions) == 1
    )

    for institution in institutions:
        contexts.append({
            "context_type": "institution",
            "context_id": str(institution.pk),
            "label": institution.institution_name,
            "role": "owner",
"is_primary": institution_is_primary,
            "metadata": {
                "institution_id": institution.pk,
                "access_scope": "institution",
            },
        })

    # Institution Department Admin contexts
    department_assignments = (
        InstitutionDepartmentAdmin.objects.filter(
            identity=identity,
            is_active=True,
            institution__is_active=True,
            department__is_active=True,
            institution__departments__id=F("department_id"),
        )
        .select_related("institution", "department")
        .order_by("institution__institution_name", "department__name", "id")
    )

    for assignment in department_assignments:
        contexts.append({
            "context_type": "institution_department",
            "context_id": str(assignment.pk),
            "label": (
                f"{assignment.institution.institution_name}"
                f" - {assignment.department.name}"
            ),
            "role": "department_admin",
            "is_primary": False,
            "metadata": {
                "institution_id": assignment.institution_id,
                "department_id": assignment.department_id,
                "assignment_id": assignment.pk,
                "access_scope": "department",
            },
        })

    # Global administrative contexts
    admin_assignments = (
        AdministrativeAssignment.objects.filter(
            identity=identity,
            is_active=True,
            role__is_active=True,
            role__identity=identity,
        )
        .select_related("role")
        .order_by("-is_primary", "role__role_type", "id")
    )

    for assignment in admin_assignments:
        contexts.append({
            "context_type": "global_admin",
            "context_id": str(assignment.pk),
            "label": assignment.role.get_role_type_display(),
            "role": assignment.role.role_type,
            "is_primary": False,
            "metadata": {
                "assignment_id": assignment.pk,
                "role_id": assignment.role_id,
            },
        })

    return contexts


def get_primary_account_context(identity):
    """
    Return the primary context, or None when no primary context exists.
    """

    contexts = get_available_account_contexts(identity)

    return next(
        (
            context
            for context in contexts
            if context["is_primary"]
        ),
        None,
    )
