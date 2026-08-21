from django.db import models

from core.models import TimeStampedModel


class HomepageSection(TimeStampedModel):
    class SectionType(models.TextChoices):
        HERO = "hero", "Hero"
        MARKETPLACE = "marketplace", "Marketplace"
        POSTED_REQUIREMENTS = (
            "posted_requirements",
            "Posted Requirements",
        )
        MANUFACTURERS = "manufacturers", "Manufacturers"
        SUPPLIERS = "suppliers", "Suppliers"
        SERVICES = "services", "Services"
        JOBS = "jobs", "Jobs"
        IMPORTERS_EXPORTERS = (
            "importers_exporters",
            "Importers & Exporters",
        )
        OPPORTUNITIES = "opportunities", "Opportunities"

    class DataSource(models.TextChoices):
        PRODUCTS = "products", "Products"
        NEEDAFY_POSTS = "needafy_posts", "Needafy Posts"
        ORGANIZATIONS = "organizations", "Organizations"
        SERVICES = "services", "Services"
        JOBS = "jobs", "Jobs"
        OPPORTUNITIES = "opportunities", "Opportunities"
        CUSTOM = "custom", "Custom"

    section_type = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique section identifier.",
    )

    data_source = models.CharField(
        max_length=100,
        choices=DataSource.choices,
        default=DataSource.CUSTOM,
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

    card_limit = models.PositiveIntegerField(
        default=6,
        help_text="Maximum number of items to display.",
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

    view_all_url = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.title or self.section_type


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

class GetStartedPageSettings(TimeStampedModel):
    title = models.CharField(
        max_length=255,
        default="Join Deepafy",
    )

    subtitle = models.TextField(
        blank=True,
        default="Create your account and get started.",
    )

    left_heading = models.CharField(
        max_length=255,
        default="Your journey starts here.",
    )

    left_description = models.TextField(
        blank=True,
    )

    personal_title = models.CharField(
        max_length=255,
        default="Personal Account",
    )

    personal_description = models.TextField(
        blank=True,
    )

    company_title = models.CharField(
        max_length=255,
        default="Company Account",
    )

    company_description = models.TextField(
        blank=True,
    )

    login_text = models.CharField(
        max_length=100,
        default="Log in",
    )

    # Colors
    page_background_color = models.CharField(
        max_length=20,
        default="#F8FAFC",
    )

    left_panel_color = models.CharField(
        max_length=20,
        default="#0A66C2",
    )

    heading_color = models.CharField(
        max_length=20,
        default="#111827",
    )

    text_color = models.CharField(
        max_length=20,
        default="#6B7280",
    )

    personal_card_color = models.CharField(
        max_length=20,
        default="#FFFFFF",
    )

    company_card_color = models.CharField(
        max_length=20,
        default="#FFFFFF",
    )

    border_color = models.CharField(
        max_length=20,
        default="#E5E7EB",
    )

    # Typography
    font_family = models.CharField(
        max_length=100,
        default="Inter",
    )

    title_font_size = models.PositiveIntegerField(
        default=36,
    )

    subtitle_font_size = models.PositiveIntegerField(
        default=16,
    )

    heading_font_size = models.PositiveIntegerField(
        default=40,
    )

    body_font_size = models.PositiveIntegerField(
        default=16,
    )

    card_title_font_size = models.PositiveIntegerField(
        default=20,
    )

    card_text_font_size = models.PositiveIntegerField(
        default=14,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return "Get Started Page Settings"        