import uuid

from django.db import models


class Category(models.Model):
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_HIDDEN = "hidden"
    VISIBILITY_DISABLED = "disabled"

    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, "Public"),
        (VISIBILITY_HIDDEN, "Hidden"),
        (VISIBILITY_DISABLED, "Disabled"),
    ]

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
    visibility = models.CharField(
         max_length=20,
         choices=VISIBILITY_CHOICES,
         default=VISIBILITY_PUBLIC,
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

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


class CategoryTranslation(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language_code = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["language_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "language_code"],
                name="unique_category_translation_language",
            )
        ]

    def __str__(self):
        return f"{self.category.name} - {self.language_code}"



class CategoryCountryOverride(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="country_overrides",
    )
    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        related_name="category_overrides",
    )
    is_enabled = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "category"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "country"],
                name="unique_category_country_override",
            )
        ]

    def __str__(self):
        return f"{self.category.name} - {self.country.name}"
class CategoryVersion(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="category_versions",
    )
 
    previous_configuration = models.JSONField(default=dict)
    current_configuration = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.category.name} - {self.created_at}"