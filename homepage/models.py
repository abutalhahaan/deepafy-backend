from django.db import models

from core.models import TimeStampedModel


class HomepageSection(TimeStampedModel):
    class SectionType(models.TextChoices):
        HERO = "hero", "Hero"
        RECENT_NEEDAFY = "recent_needafy", "Recent Needafy Posts"
        RECENT_PRODUCT_LISTINGS = (
            "recent_product_listings",
            "Recent Product Listings",
        )
        TOP_MANUFACTURERS = "top_manufacturers", "Top Manufacturers"
        RECENT_JOBS = "recent_jobs", "Recent Posted Jobs"
        TRENDING_PRODUCTS = "trending_products", "Trending Products"
        TOP_VERIFIED_SUPPLIERS = (
            "top_verified_suppliers",
            "Top Verified Suppliers",
        )
        FEATURED_BRANDS = "featured_brands", "Featured Brands"
        BUSINESS_UPDATES = "business_updates", "Business Updates"
        FEATURED_SERVICES = "featured_services", "Featured Services"
        PLATFORM_STATISTICS = (
            "platform_statistics",
            "Platform Statistics",
        )
        JOIN_DEEPAFY = "join_deepafy", "Join Deepafy"

    section_type = models.CharField(
        max_length=100,
        choices=SectionType.choices,
        unique=True,
    )

    title = models.CharField(
        max_length=255,
        blank=True,
    )

    subtitle = models.TextField(
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_visible = models.BooleanField(
        default=True,
    )

    show_view_all = models.BooleanField(
        default=True,
    )

    view_all_label = models.CharField(
        max_length=100,
        default="View All",
    )

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.get_section_type_display()


class HomepageHero(TimeStampedModel):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
    )

    media_url = models.URLField(
        blank=True,
    )

    media_file = models.ImageField(
        upload_to="homepage/heroes/",
        blank=True,
        null=True,
    )

    title = models.CharField(
        max_length=255,
        blank=True,
    )

    desktop_position = models.CharField(
        max_length=50,
        default="center",
    )

    mobile_position = models.CharField(
        max_length=50,
        default="center",
    )

    object_fit = models.CharField(
        max_length=20,
        default="cover",
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    cta_label = models.CharField(
        max_length=100,
        blank=True,
    )

    cta_url = models.CharField(
        max_length=255,
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.title or f"Homepage Hero #{self.pk}"


class PlatformStatistic(TimeStampedModel):
    title = models.CharField(
        max_length=100,
    )

    value = models.CharField(
        max_length=100,
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_visible = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.title


class HomepageCTA(TimeStampedModel):
    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    button_label = models.CharField(
        max_length=100,
        default="Create Account",
    )

    button_url = models.CharField(
        max_length=255,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.title