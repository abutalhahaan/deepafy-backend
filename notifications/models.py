from django.conf import settings
from django.db import models


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ("system", "System"),
        ("activity", "Activity"),
        ("matching", "Matching"),
        ("message", "Message"),
        ("premium", "Premium"),
        ("verification", "Verification"),
        ("company", "Company"),
        ("job", "Job"),
        ("product", "Product"),
        ("needafy", "Needafy / RFQ"),
        ("admin", "Admin"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="system",
    )
    notification_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    message = models.TextField()
    source = models.CharField(max_length=100, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="normal",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["category", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.user}"
