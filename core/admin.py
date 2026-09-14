from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseRedirect

# Register your models here.

from .models import FeatureAccessControl, PersonalFontStyle

@admin.register(FeatureAccessControl)
class FeatureAccessControlAdmin(admin.ModelAdmin):
    list_display = (
        "feature_name",
        "account_type",
        "category",
        "access_level",
        "trial_enabled",
        "trial_days",
        "is_enabled",
    )
    list_filter = (
        "account_type",
        "category",
        "access_level",
        "trial_enabled",
        "is_enabled",
    )
    search_fields = (
        "feature_name",
        "feature_key",
        "description",
    )
    ordering = ("category", "feature_name")


from .models import PremiumPackage, UserPremiumSubscription


@admin.register(PremiumPackage)
class PremiumPackageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "duration_days",
        "price",
        "currency",
        "is_active",
    )
    list_filter = (
        "is_active",
        "currency",
    )
    search_fields = (
        "name",
        "description",
    )
    ordering = (
        "duration_days",
        "name",
    )


@admin.register(UserPremiumSubscription)
class UserPremiumSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "package",
        "started_at",
        "expires_at",
        "is_active",
    )
    list_filter = (
        "is_active",
        "package",
    )
    search_fields = (
        "user__email",
        "user__username",
        "package__name",
    )
    ordering = (
        "-expires_at",
    )


from .models import PaymentMethod, PaymentMethodField, PaymentTransaction


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'method_type', 'verification_type', 'provider_key', 'is_active', 'display_order')
    list_filter = ('method_type', 'is_active')
    search_fields = ('name', 'provider_key', 'instructions')
    ordering = ('display_order', 'name')


@admin.register(PaymentMethodField)
class PaymentMethodFieldAdmin(admin.ModelAdmin):
    list_display = ('field_label', 'payment_method', 'field_type', 'is_required', 'is_customer_input', 'is_active', 'display_order')
    list_filter = ('field_type', 'is_required', 'is_active', 'payment_method')
    search_fields = ('field_label', 'field_key', 'help_text')
    ordering = ('payment_method', 'display_order', 'field_label')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'package', 'payment_method', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'package', 'currency')
    search_fields = ('transaction_id', 'payment_reference', 'sender_account', 'user__email', 'user__username')
    readonly_fields = ('transaction_id', 'status', 'created_at', 'updated_at', 'verified_at')
    fields = (
        'transaction_id',
        'user',
        'package',
        'payment_method',
        'amount',
        'currency',
        'payment_reference',
        'sender_account',
        'payment_details',
        'proof_file',
        'status',
        'admin_note',
        'verified_at',
        'created_at',
        'updated_at',
    )
    ordering = ('-created_at',)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST' and request.POST.get('_review') in {'approve', 'reject'}:
            from .views import review_payment_transaction

            request.POST = request.POST.copy()
            request.POST['action'] = request.POST.get('_review')
            response = review_payment_transaction(request, int(object_id))

            if response.status_code == 200:
                if request.POST.get('_review') == 'approve':
                    self.message_user(request, 'Payment approved and Premium subscription activated.', messages.SUCCESS)
                else:
                    self.message_user(request, 'Payment rejected successfully.', messages.SUCCESS)
            else:
                self.message_user(request, response.data.get('detail', 'Payment review failed.'), messages.ERROR)

            return HttpResponseRedirect(request.path)

        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(PersonalFontStyle)
class PersonalFontStyleAdmin(admin.ModelAdmin):
    list_display = ('font_name', 'category', 'access_level', 'is_enabled', 'display_order')
    list_filter = ('category', 'access_level', 'is_enabled')
    search_fields = ('font_name', 'font_key', 'font_family')
    ordering = ('display_order', 'font_name')
