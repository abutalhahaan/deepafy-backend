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


class AccountType(models.Model):
    class Type(models.TextChoices):
        PERSONAL = "personal", "Personal Account"
        PROFESSIONAL = "professional", "Professional Account"
        COMPANY = "company", "Company Account"

    identity = models.ForeignKey(
        UserIdentity,
        on_delete=models.CASCADE,
        related_name="account_types",
    )
    account_type = models.CharField(
        max_length=30,
        choices=Type.choices,
    )
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["identity", "account_type"],
                name="unique_account_type_per_identity",
            )
        ]
        ordering = ["account_type"]

    def __str__(self):
        return (
            f"{self.identity.user_id} - "
            f"{self.get_account_type_display()}"
        )


class PersonalAccount(models.Model):
    identity = models.OneToOneField(
        UserIdentity,
        on_delete=models.CASCADE,
        related_name="personal_account",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Personal Account - {self.identity.user_id}"


class PersonalInterestedCategory(models.Model):
    personal_account = models.ForeignKey(
        PersonalAccount,
        on_delete=models.CASCADE,
        related_name="interested_categories",
    )
    category = models.ForeignKey(
        "category_engine.Category",
        on_delete=models.PROTECT,
        related_name="personal_interested_categories",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["personal_account", "category"],
                name="unique_personal_interested_category",
            )
        ]
        ordering = ["category__name"]

    def __str__(self):
        return (
            f"{self.personal_account.identity.user_id} - "
            f"{self.category.name}"
        )


class PersonalHobby(models.Model):
    personal_account = models.ForeignKey(
        PersonalAccount,
        on_delete=models.CASCADE,
        related_name="hobbies",
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["personal_account", "name"],
                name="unique_personal_hobby",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return (
            f"{self.personal_account.identity.user_id} - "
            f"{self.name}"
        )