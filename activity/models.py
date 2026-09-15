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
