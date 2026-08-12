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