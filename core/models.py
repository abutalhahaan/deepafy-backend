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
