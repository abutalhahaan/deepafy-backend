from django.db import models


class JobCategory(models.Model):
    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
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
            "display_order",
            "name",
        ]

    def __str__(self):
        return self.name


class JobInterest(models.Model):
    professional_account = models.ForeignKey(
        "identity.ProfessionalAccount",
        on_delete=models.CASCADE,
        related_name="job_interests",
    )

    job_category = models.ForeignKey(
        JobCategory,
        on_delete=models.CASCADE,
        related_name="interested_professionals",
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
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "professional_account",
                    "job_category",
                ],
                name=(
                    "unique_professional_job_interest"
                ),
            ),
        ]

        ordering = [
            "job_category__display_order",
            "job_category__name",
        ]

    def __str__(self):
        return (
            f"{self.professional_account.identity.user_id} - "
            f"{self.job_category.name}"
        )