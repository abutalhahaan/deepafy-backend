import uuid

from django.db import models


class UserIdentity(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_VERIFICATION = "pending_verification", "Pending Verification"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"
        RESTRICTED = "restricted", "Restricted"
        LOCKED = "locked", "Locked"
        DEACTIVATED = "deactivated", "Deactivated"
        DELETED = "deleted", "Deleted"

    user_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(
        max_length=30,
        blank=True,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.user_id)