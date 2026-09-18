from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=255)
    internal_id = models.CharField(max_length=50, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
class FeatureAccessControl(TimeStampedModel):
    ACCOUNT_TYPES = [
        ('personal', 'Personal'),
        ('professional', 'Professional'),
        ('company', 'Company'),
    ]

    feature_key = models.CharField(max_length=150)
    feature_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='personal')
    category = models.CharField(max_length=100, blank=True)
    is_enabled = models.BooleanField(default=True)
    access_level = models.CharField(
        max_length=20,
        choices=[
            ("free", "Free"),
            ("premium", "Premium"),
        ],
        default="premium",
    )
    trial_enabled = models.BooleanField(default=False)
    trial_days = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["category", "feature_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["feature_key", "account_type"],
                name="unique_feature_per_account_type",
            ),
        ]

    def __str__(self):
        return self.feature_name


class UserFeatureTrial(TimeStampedModel):
    user = models.ForeignKey(
        "identity.UserIdentity",
        on_delete=models.CASCADE,
        related_name="feature_trials",
    )
    feature = models.ForeignKey(
        FeatureAccessControl,
        on_delete=models.CASCADE,
        related_name="user_trials",
    )
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "feature"],
                name="unique_user_feature_trial",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.feature.feature_name}"


class PremiumPackage(TimeStampedModel):
    name = models.CharField(max_length=150)
    duration_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="BDT")
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["duration_days", "name"]

    def __str__(self):
        return f"{self.name} - {self.duration_days} days"


class UserPremiumSubscription(TimeStampedModel):
    user = models.ForeignKey(
        "identity.UserIdentity",
        on_delete=models.CASCADE,
        related_name="premium_subscriptions",
    )
    package = models.ForeignKey(
        PremiumPackage,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-expires_at"]

    def __str__(self):
        return f"{self.user} - {self.package.name}"


class PaymentMethod(TimeStampedModel):
    METHOD_TYPES = [
        ('manual', 'Manual Payment'),
        ('gateway', 'Payment Gateway'),
    ]

    VERIFICATION_TYPES = [
        ('manual', 'Manual Approval'),
        ('automatic', 'Automatic Verification'),
    ]
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES, default='manual')

    name = models.CharField(max_length=150, unique=True)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES, default='manual')
    provider_key = models.CharField(max_length=100, blank=True)
    logo_url = models.URLField(blank=True)
    instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class PaymentMethodField(TimeStampedModel):
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('textarea', 'Long Text'),
        ('url', 'URL'),
    ]

    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE, related_name='fields')
    field_key = models.CharField(max_length=100)
    field_label = models.CharField(max_length=150)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    value = models.TextField(blank=True)
    placeholder = models.CharField(max_length=255, blank=True)
    help_text = models.CharField(max_length=500, blank=True)
    is_required = models.BooleanField(default=False)
    is_customer_input = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'field_label']
        constraints = [
            models.UniqueConstraint(fields=['payment_method', 'field_key'], name='unique_payment_method_field_key'),
        ]

    def __str__(self):
        return f'{self.payment_method.name} - {self.field_label}'


class PaymentTransaction(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey('identity.UserIdentity', on_delete=models.PROTECT, related_name='payment_transactions')
    package = models.ForeignKey(PremiumPackage, on_delete=models.PROTECT, related_name='payment_transactions')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    transaction_id = models.CharField(max_length=150, unique=True)
    payment_reference = models.CharField(max_length=150, blank=True)
    payment_details = models.JSONField(default=dict, blank=True)
    sender_account = models.CharField(max_length=100, blank=True)
    proof_file = models.FileField(upload_to='payment_proofs/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.transaction_id} - {self.user}'

class PersonalFontStyle(TimeStampedModel):
    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('premium', 'Premium'),
    ]

    font_key = models.CharField(max_length=100, unique=True)
    font_name = models.CharField(max_length=150)
    font_family = models.CharField(max_length=255)
    font_source = models.URLField(max_length=500, blank=True, default='')
    local_font_file = models.FileField(upload_to='personal_fonts/', blank=True, null=True)
    font_weights = models.CharField(max_length=100, blank=True, default='')
    language_support = models.CharField(max_length=255, blank=True, default='')
    category = models.CharField(max_length=50, default='Standard')
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='free')
    is_enabled = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'font_name']

    def __str__(self):
        return self.font_name


class UserFontFavorite(TimeStampedModel):
    personal_account = models.ForeignKey(
        'identity.PersonalAccount',
        on_delete=models.CASCADE,
        related_name='favorite_fonts',
    )
    font = models.ForeignKey(
        PersonalFontStyle,
        on_delete=models.CASCADE,
        related_name='user_favorites',
    )

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=('personal_account', 'font'),
                name='unique_user_font_favorite',
            ),
        ]

    def __str__(self):
        return f'{self.personal_account_id} - {self.font.font_key}'

class ColleagueSetting(TimeStampedModel):
    is_enabled = models.BooleanField(default=True)
    allow_user_remove = models.BooleanField(default=False)
    allow_status_change = models.BooleanField(default=True)
    require_mutual_confirmation = models.BooleanField(default=True)
    running_status_enabled = models.BooleanField(default=True)
    previous_status_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Colleague Setting"
        verbose_name_plural = "Colleague Settings"

    def __str__(self):
        return "Colleague Settings"

class CentralPopupSetting(TimeStampedModel):
    SIZE_CHOICES = [
        ("small", "Small"),
        ("medium", "Medium"),
        ("large", "Large"),
        ("custom", "Custom"),
        ("fullscreen", "Fullscreen"),
    ]

    POSITION_CHOICES = [
        ("center", "Center"),
        ("top", "Top"),
        ("bottom", "Bottom"),
        ("left", "Left"),
        ("right", "Right"),
    ]

    popups = models.ManyToManyField(
        "CentralPopupRegistry",
        related_name="settings",
        blank=True,
    )

    all_popups = models.BooleanField(
        default=False,
    )

    country = models.ForeignKey(
        "organization.Country",
        on_delete=models.PROTECT,
        related_name="popup_settings",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    size = models.CharField(
        max_length=20,
        choices=SIZE_CHOICES,
        default="medium",
    )

    position = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES,
        default="center",
    )

    width = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    height = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    # Content
    content_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    content_subtitle = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    content_body = models.TextField(
        blank=True,
        default="",
    )

    button_url = models.URLField(
        blank=True,
        default="",
    )

    # Schedule
    schedule_enabled = models.BooleanField(
        default=False,
    )

    start_date = models.DateField(
        blank=True,
        null=True,
    )

    end_date = models.DateField(
        blank=True,
        null=True,
    )

    repeat_yearly = models.BooleanField(
        default=False,
    )

    display_start_time = models.TimeField(
        blank=True,
        null=True,
    )

    display_end_time = models.TimeField(
        blank=True,
        null=True,
    )

    # Background
    background_color = models.CharField(
        max_length=20,
        blank=True,
        default="#ffffff",
    )

    background_opacity = models.PositiveSmallIntegerField(
        default=100,
    )

    background_image = models.ImageField(
        upload_to="popup/backgrounds/",
        blank=True,
        null=True,
    )

    # Border / Shadow
    border = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    border_radius = models.CharField(
        max_length=30,
        default="18px",
    )

    box_shadow = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    # Backdrop
    backdrop_enabled = models.BooleanField(
        default=True,
    )

    backdrop_color = models.CharField(
        max_length=20,
        default="#0f172a",
    )

    backdrop_opacity = models.PositiveSmallIntegerField(
        default=55,
    )

    backdrop_blur = models.PositiveSmallIntegerField(
        default=6,
    )

    # Close Behaviour
    show_close_button = models.BooleanField(
        default=True,
    )

    close_on_outside_click = models.BooleanField(
        default=True,
    )

    close_on_escape = models.BooleanField(
        default=True,
    )

    auto_close_enabled = models.BooleanField(
        default=False,
    )

    auto_close_seconds = models.PositiveIntegerField(
        default=0,
    )

    # Typography
    font_family = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    title_font_size = models.CharField(
        max_length=30,
        default="20px",
    )

    title_font_weight = models.CharField(
        max_length=30,
        default="600",
    )

    title_color = models.CharField(
        max_length=20,
        default="#111827",
    )

    body_font_size = models.CharField(
        max_length=30,
        default="16px",
    )

    body_font_weight = models.CharField(
        max_length=30,
        default="400",
    )

    body_color = models.CharField(
        max_length=20,
        default="#374151",
    )

    line_height = models.CharField(
        max_length=30,
        default="1.5",
    )

    letter_spacing = models.CharField(
        max_length=30,
        default="normal",
    )

    text_align = models.CharField(
        max_length=20,
        choices=[
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        default="left",
    )

    # Header
    header_enabled = models.BooleanField(
        default=True,
    )

    header_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    header_subtitle = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    header_alignment = models.CharField(
        max_length=20,
        choices=[
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        default="left",
    )

    header_height = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    header_border = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # Button
    button_enabled = models.BooleanField(
        default=True,
    )

    button_text = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    button_background_color = models.CharField(
        max_length=20,
        default="#0A66C2",
    )

    button_text_color = models.CharField(
        max_length=20,
        default="#ffffff",
    )

    button_font_size = models.CharField(
        max_length=30,
        default="14px",
    )

    button_font_weight = models.CharField(
        max_length=30,
        default="500",
    )

    button_border = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    button_border_radius = models.CharField(
        max_length=30,
        default="8px",
    )

    button_padding = models.CharField(
        max_length=50,
        default="10px 18px",
    )

    button_alignment = models.CharField(
        max_length=20,
        choices=[
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        default="left",
    )

    # Animation
    animation = models.CharField(
        max_length=30,
        choices=[
            ("fade", "Fade"),
            ("scale", "Scale"),
            ("slide-up", "Slide Up"),
            ("slide-down", "Slide Down"),
            ("slide-left", "Slide Left"),
            ("slide-right", "Slide Right"),
            ("none", "None"),
        ],
        default="scale",
    )

    animation_duration = models.PositiveIntegerField(
        default=220,
    )

    # Mobile / Responsive
    mobile_enabled = models.BooleanField(
        default=True,
    )

    mobile_width = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    mobile_height = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    mobile_position = models.CharField(
        max_length=20,
        choices=[
            ("center", "Center"),
            ("top", "Top"),
            ("bottom", "Bottom"),
            ("left", "Left"),
            ("right", "Right"),
        ],
        default="bottom",
    )

    mobile_bottom_sheet = models.BooleanField(
        default=False,
    )

    mobile_border_radius = models.CharField(
        max_length=30,
        default="18px",
    )

    mobile_padding = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["country__name", "id"]

    def __str__(self):
        popup_names = ", ".join(
            self.popups.values_list("popup_id", flat=True)
        )
        return f"{popup_names or 'No Popup'} - {self.country.name}"


class CentralPopupRegistry(TimeStampedModel):
    POPUP_TYPES = [
        ("special_day", "Special Day"),
        ("iconic_person", "Iconic Person"),
        ("memorial", "Memorial / Tribute"),
        ("national_event", "National Event"),
        ("announcement", "Announcement"),
        ("custom", "Custom"),
    ]

    popup_id = models.CharField(
        max_length=100,
        unique=True,
    )

    popup_name = models.CharField(
        max_length=255,
    )

    popup_type = models.CharField(
        max_length=30,
        choices=POPUP_TYPES,
        default="custom",
    )

    is_active = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["display_order", "popup_name"]

    def __str__(self):
        return f"{self.popup_name} ({self.popup_id})"
