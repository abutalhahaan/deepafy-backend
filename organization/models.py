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