import uuid

from django.db import models


class Organization(models.Model):
    organization_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    name = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    business_email = models.EmailField()
    business_mobile_number = models.CharField(max_length=30)
    registered_address = models.TextField()
    primary_contact_person = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationRelationship(models.Model):
    class RelationshipType(models.TextChoices):
        OWNER = "owner", "Owner"
        CO_OWNER = "co_owner", "Co-Owner"
        ADMINISTRATOR = "administrator", "Administrator"
        MANAGER = "manager", "Manager"
        EMPLOYEE = "employee", "Employee / Staff"
        MEMBER = "member", "Member"

    class MembershipStatus(models.TextChoices):
        INVITED = "invited", "Invited"
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REMOVED = "removed", "Removed"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="relationships",
    )
    identity = models.ForeignKey(
        "identity.UserIdentity",
        on_delete=models.CASCADE,
        related_name="organization_relationships",
    )
    relationship_type = models.CharField(
        max_length=30,
        choices=RelationshipType.choices,
    )
    membership_status = models.CharField(
        max_length=30,
        choices=MembershipStatus.choices,
        default=MembershipStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "identity"],
                name="unique_organization_identity_relationship",
            )
        ]
        ordering = ["organization", "relationship_type"]

    def __str__(self):
        return (
            f"{self.identity.user_id} - "
            f"{self.organization.name} - "
            f"{self.get_relationship_type_display()}"
        )
class AdministrativeRole(models.Model):
    class RoleType(models.TextChoices):
        OWNER = "owner", "Owner"
        CO_OWNER = "co_owner", "Co-Owner"
        SUPER_ADMIN = "super_admin", "Super Admin"
        CO_SUPER_ADMIN = "co_super_admin", "Co-Super Admin"
        GLOBAL_DEPARTMENT_ADMIN = (
            "global_department_admin",
            "Global Department Admin",
        )
        CO_GLOBAL_DEPARTMENT_ADMIN = (
            "co_global_department_admin",
            "Co-Global Department Admin",
        )
        REGIONAL_ADMIN = "regional_admin", "Regional Admin"
        CO_REGIONAL_ADMIN = "co_regional_admin", "Co-Regional Admin"
        COUNTRY_ADMIN = "country_admin", "Country Admin"
        CO_COUNTRY_ADMIN = "co_country_admin", "Co-Country Admin"
        COUNTRY_DEPARTMENT_ADMIN = (
            "country_department_admin",
            "Country Department Admin",
        )
        CO_COUNTRY_DEPARTMENT_ADMIN = (
            "co_country_department_admin",
            "Co-Country Department Admin",
        )
        STAFF = "staff", "Staff"

    identity = models.ForeignKey(
        "identity.UserIdentity",
        on_delete=models.CASCADE,
        related_name="administrative_roles",
    )
    role_type = models.CharField(
        max_length=40,
        choices=RoleType.choices,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role_type"]

    def __str__(self):
        return (
            f"{self.identity.user_id} - "
            f"{self.get_role_type_display()}"
        )
class AdministrativeAssignment(models.Model):
    identity = models.ForeignKey(
        "identity.UserIdentity",
        on_delete=models.CASCADE,
        related_name="administrative_assignments",
    )
    role = models.ForeignKey(
        AdministrativeRole,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    reporting_boss = models.ForeignKey(
        "identity.UserIdentity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinate_administrative_assignments",
    )
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.identity.user_id} - "
            f"{self.role.get_role_type_display()}"
        )
class Region(models.Model):
    region_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name