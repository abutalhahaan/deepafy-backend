import uuid

from django.db import models


class Category(models.Model):
    category_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="unique_category_name_per_parent",
            ),
            models.UniqueConstraint(
                fields=["parent", "slug"],
                name="unique_category_slug_per_parent",
            ),
        ]

    def __str__(self):
        return self.name