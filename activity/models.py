from django.db import models
from identity.models import PersonalAccount


class Activity(models.Model):
    class ActivityCategory(models.TextChoices):
        PERSONAL = "personal", "Personal"
        PROFESSIONAL = "professional", "Professional"
        BUSINESS = "business", "Business / Company"
        EDUCATION = "education", "Education"

    personal_account = models.ForeignKey(
        PersonalAccount,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    category = models.CharField(
        max_length=30,
        choices=ActivityCategory.choices,
    )

    activity_type = models.CharField(
        max_length=100,
    )

    content = models.TextField(
        blank=True,
    )

    is_published = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.personal_account} - {self.activity_type}"

class ActivityLike(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="likes",
    )

    personal_account = models.ForeignKey(
        PersonalAccount,
        on_delete=models.CASCADE,
        related_name="activity_likes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "personal_account"],
                name="unique_activity_like",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.personal_account} liked Activity #{self.activity_id}"

class ActivityComment(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    personal_account = models.ForeignKey(
        PersonalAccount,
        on_delete=models.CASCADE,
        related_name="activity_comments",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )

    content = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.personal_account} commented on Activity #{self.activity_id}"
