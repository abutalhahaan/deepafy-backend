from django.contrib import admin
from django import forms
from django.contrib import messages
from django.utils import timezone
from core.services.image_processor import process_image
from django.http import HttpResponseRedirect

# Register your models here.

from .models import FeatureAccessControl, PersonalFontStyle, ColleagueSetting, CentralPopupSetting, CentralPopupRegistry

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
    fieldsets = (
        ('Font Information', {'fields': ('font_key', 'font_name', 'font_family', 'category')}),
        ('Font Loading', {'fields': ('font_source', 'local_font_file', 'font_weights', 'language_support')}),
        ('Access & Display', {'fields': ('access_level', 'is_enabled', 'display_order')}),
    )


@admin.register(ColleagueSetting)
class ColleagueSettingAdmin(admin.ModelAdmin):
    list_display = (
        "is_enabled",
        "allow_user_remove",
        "allow_status_change",
        "require_mutual_confirmation",
        "running_status_enabled",
        "previous_status_enabled",
        "updated_at",
    )

    list_filter = (
        "is_enabled",
        "allow_user_remove",
        "allow_status_change",
        "require_mutual_confirmation",
        "running_status_enabled",
        "previous_status_enabled",
    )

    @admin.display(description="Popup IDs")
    def popup_names(self, obj):
        return ", ".join(
            obj.popups.values_list("popup_id", flat=True)
        )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Colleague System",
            {
                "fields": (
                    "is_enabled",
                )
            },
        ),
        (
            "User Permissions",
            {
                "fields": (
                    "allow_user_remove",
                    "allow_status_change",
                    "require_mutual_confirmation",
                )
            },
        ),
        (
            "Status Options",
            {
                "fields": (
                    "running_status_enabled",
                    "previous_status_enabled",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not ColleagueSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class CentralPopupSettingForm(forms.ModelForm):
    all_popups = forms.BooleanField(
        required=False,
        label="All Popup IDs",
        help_text="Enable this to apply this setting to all active registered popups.",
    )

    class Meta:
        model = CentralPopupSetting
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["popups"].queryset = (
            CentralPopupRegistry.objects
            .filter(is_active=True)
            .order_by("display_order", "popup_name")
        )

        self.fields["country"].queryset = (
            self.fields["country"].queryset
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["popups"].required = False

        # ---------------------------------------------------------------
        # Central Popup Admin Help Text
        # ---------------------------------------------------------------
        help_texts = {
            "popups": "Select the specific Popup ID(s) that should use this setting.",
            "country": "Select the country whose users should receive this popup.",
            "is_enabled": "Turn this popup configuration on or off.",

            "content_title": "Main heading displayed inside the popup.",
            "content_subtitle": "Short supporting text displayed below the main heading.",
            "content_body": "Main message or content displayed inside the popup.",
            "button_url": "Destination URL opened when the popup action button is used.",

            "schedule_enabled": "Enable this when the popup should appear only during a defined period.",
            "start_date": "Date from which this popup configuration becomes active.",
            "end_date": "Date after which this popup configuration stops being active.",
            "repeat_yearly": "Repeat the configured date range every year.",
            "display_start_time": "Daily time from which the popup may be displayed.",
            "display_end_time": "Daily time after which the popup should stop being displayed.",

            "size": "Overall popup size preset.",
            "position": "Where the popup appears on the screen.",
            "width": "Popup width. Example: 600px or 80%.",
            "height": "Popup height. Example: 500px or 80vh.",

            "background_color": "Background color used when no background image is displayed.",
            "background_opacity": "Transparency level of the popup background color.",
            "background_image": "Image displayed as the popup background. When an image exists, the image takes priority over the background color.",

            "border": "Popup border style, width, and color. Example: 2px solid #0A66C2.",
            "border_radius": "Roundness of the popup corners.",
            "box_shadow": "Shadow displayed around the popup.",

            "backdrop_enabled": "Enable the dimmed/blurred layer behind the popup.",
            "backdrop_color": "Color applied to the area behind the popup.",
            "backdrop_opacity": "Transparency level of the backdrop.",
            "backdrop_blur": "Amount of blur applied to the page behind the popup, in pixels.",

            "show_close_button": "Show or hide the popup close (×) button.",
            "close_on_outside_click": "Allow the popup to close when the user clicks outside it.",
            "close_on_escape": "Allow the popup to close when the user presses Escape.",
            "auto_close_enabled": "Automatically close the popup after a defined number of seconds.",
            "auto_close_seconds": "Number of seconds before automatic popup closing.",
        }

        for field_name, help_text in help_texts.items():
            if field_name in self.fields:
                self.fields[field_name].help_text = help_text

        # ---------------------------------------------------------------
        # Typography and Header Admin Help Text
        # ---------------------------------------------------------------
        additional_help_texts = {
            "font_family": (
                "Font family used throughout the popup text."
            ),
            "title_font_size": (
                "Font size of the main popup title. Example: 28px."
            ),
            "title_font_weight": (
                "Font thickness of the popup title. Example: 400, 600, or 700."
            ),
            "title_color": (
                "Text color of the popup title."
            ),
            "body_font_size": (
                "Font size of the popup body text."
            ),
            "body_font_weight": (
                "Font thickness of the popup body text."
            ),
            "body_color": (
                "Text color of the popup body."
            ),
            "line_height": (
                "Vertical spacing between lines of popup text."
            ),
            "letter_spacing": (
                "Spacing between individual characters."
            ),
            "text_align": (
                "Default text alignment: left, center, or right."
            ),

            "header_enabled": (
                "Enable or disable the centrally controlled popup header."
            ),
            "header_title": (
                "Title displayed in the popup header."
            ),
            "header_subtitle": (
                "Supporting text displayed below the header title."
            ),
            "header_alignment": (
                "Alignment of the header content: left, center, or right."
            ),
            "header_height": (
                "Height of the popup header area."
            ),
            "header_border": (
                "Border or separator applied to the popup header."
            ),

            "button_enabled": (
                "Enable or disable the centrally controlled popup button."
            ),
            "button_text": (
                "Text displayed inside the popup button."
            ),
            "button_background_color": (
                "Background color of the popup button."
            ),
            "button_text_color": (
                "Text color of the popup button."
            ),
            "button_font_size": (
                "Font size of the popup button text."
            ),
            "button_font_weight": (
                "Font thickness of the popup button text."
            ),
            "button_border": (
                "Border style, width, and color of the popup button."
            ),
            "button_border_radius": (
                "Roundness of the popup button corners."
            ),
            "button_padding": (
                "Internal spacing inside the button. Example: 12px 28px."
            ),
            "button_alignment": (
                "Position of the button: left, center, or right."
            ),

            "animation": (
                "Animation used when the popup opens. Example: fade, scale, or slide."
            ),
            "animation_duration": (
                "Opening animation duration in milliseconds. Example: 400."
            ),

            "mobile_enabled": (
                "Enable separate responsive settings for mobile devices."
            ),
            "mobile_width": (
                "Popup width on mobile. Example: 100%."
            ),
            "mobile_height": (
                "Popup height on mobile. Example: 80vh."
            ),
            "mobile_position": (
                "Popup position on mobile devices."
            ),
            "mobile_bottom_sheet": (
                "Display the popup as a bottom sheet attached to the bottom of the screen."
            ),
            "mobile_border_radius": (
                "Corner roundness of the popup on mobile."
            ),
            "mobile_padding": (
                "Internal spacing inside the popup on mobile."
            ),
        }

        for field_name, help_text in additional_help_texts.items():
            if field_name in self.fields:
                self.fields[field_name].help_text = help_text



    def clean_background_image(self):
        uploaded_file = self.cleaned_data.get("background_image")

        if not uploaded_file:
            return uploaded_file

        # Only process a newly uploaded image.
        # Existing saved images are left unchanged.
        if not hasattr(uploaded_file, "read"):
            return uploaded_file

        try:
            return process_image(
                uploaded_file,
                "popup_background",
            )
        except ValueError as error:
            raise forms.ValidationError(str(error)) from error

    def clean(self):
        cleaned_data = super().clean()

        all_popups = cleaned_data.get("all_popups")
        popups = cleaned_data.get("popups")
        country = cleaned_data.get("country")

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        start_time = cleaned_data.get("display_start_time")
        end_time = cleaned_data.get("display_end_time")

        schedule_enabled = cleaned_data.get("schedule_enabled")

        # ---------------------------------------------------------------
        # Popup selection validation
        # ---------------------------------------------------------------

        if all_popups and popups:
            self.add_error(
                "popups",
                "When All Popup IDs is enabled, do not select individual Popup IDs.",
            )

        elif not all_popups and not popups:
            self.add_error(
                "popups",
                "Select at least one Popup ID or enable All Popup IDs.",
            )

        # ---------------------------------------------------------------
        # Schedule validation
        # ---------------------------------------------------------------

        if schedule_enabled:
            if start_date and end_date and start_date > end_date:
                self.add_error(
                    "end_date",
                    "End date cannot be earlier than start date.",
                )

            if start_time and end_time and start_time > end_time:
                self.add_error(
                    "display_end_time",
                    "Display end time cannot be earlier than display start time.",
                )

        # ---------------------------------------------------------------
        # Duplicate / overlapping configuration validation
        # ---------------------------------------------------------------

        if country:
            existing_settings = (
                CentralPopupSetting.objects
                .filter(country=country)
                .prefetch_related("popups")
            )

            if self.instance and self.instance.pk:
                existing_settings = existing_settings.exclude(
                    pk=self.instance.pk
                )

            if all_popups:
                if existing_settings.exists():
                    self.add_error(
                        "country",
                        "This country already has Popup Settings. "
                        "All Popup IDs would conflict with the existing configuration.",
                    )

            elif popups:
                selected_ids = set(
                    popups.values_list("id", flat=True)
                )

                for existing in existing_settings:
                    if existing.all_popups:
                        self.add_error(
                            "country",
                            "This country already has an All Popup IDs configuration.",
                        )
                        break

                    existing_ids = set(
                        existing.popups.values_list("id", flat=True)
                    )

                    overlap = selected_ids & existing_ids

                    if overlap:
                        overlap_names = list(
                            CentralPopupRegistry.objects
                            .filter(id__in=overlap)
                            .values_list("popup_id", flat=True)
                        )

                        self.add_error(
                            "popups",
                            "These Popup IDs are already configured for this country: "
                            + ", ".join(overlap_names),
                        )
                        break

        return cleaned_data


@admin.register(CentralPopupSetting)
class CentralPopupSettingAdmin(admin.ModelAdmin):
    form = CentralPopupSettingForm
    list_display = (
        "popup_names",
        "country",
        "is_enabled",
        "size",
        "position",
        "width",
        "height",
        "animation",
        "mobile_enabled",
        "updated_at",
    )

    list_filter = (
        "is_enabled",
        "size",
        "position",
        "country",
        "animation",
        "mobile_enabled",
        "backdrop_enabled",
        "header_enabled",
        "button_enabled",
    )

    search_fields = (
        "popups__popup_id",
        "popups__popup_name",
        "country__name",
        "country__code",
        "header_title",
        "header_subtitle",
        "button_text",
    )

    ordering = (
        "country__name",
        "id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    @admin.display(description="Popup IDs")
    def popup_names(self, obj):
        return ", ".join(
            obj.popups.values_list("popup_id", flat=True)
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "country":
            kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                is_active=True
            ).order_by("name")

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs,
        )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "popups":
            kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                is_active=True
            ).order_by("display_order", "popup_name")

        return super().formfield_for_manytomany(
            db_field,
            request,
            **kwargs,
        )

    fieldsets = (
        (
            "Popup Identity",
            {
                "fields": (
                    "all_popups",
                    "popups",
                    "country",
                    "is_enabled",
                )
            },
        ),
        (
            "Content",
            {
                "fields": (
                    "content_title",
                    "content_subtitle",
                    "content_body",
                    "button_url",
                )
            },
        ),
        (
            "Schedule",
            {
                "fields": (
                    "schedule_enabled",
                    "start_date",
                    "end_date",
                    "repeat_yearly",
                    "display_start_time",
                    "display_end_time",
                )
            },
        ),
        (
            "Layout",
            {
                "fields": (
                    "size",
                    "position",
                    "width",
                    "height",
                )
            },
        ),
        (
            "Background",
            {
                "fields": (
                    "background_color",
                    "background_opacity",
                    "background_image",
                )
            },
        ),
        (
            "Border & Shadow",
            {
                "fields": (
                    "border",
                    "border_radius",
                    "box_shadow",
                )
            },
        ),
        (
            "Backdrop",
            {
                "fields": (
                    "backdrop_enabled",
                    "backdrop_color",
                    "backdrop_opacity",
                    "backdrop_blur",
                )
            },
        ),
        (
            "Close Behaviour",
            {
                "fields": (
                    "show_close_button",
                    "close_on_outside_click",
                    "close_on_escape",
                    "auto_close_enabled",
                    "auto_close_seconds",
                )
            },
        ),
        (
            "Typography",
            {
                "fields": (
                    "font_family",
                    "title_font_size",
                    "title_font_weight",
                    "title_color",
                    "body_font_size",
                    "body_font_weight",
                    "body_color",
                    "line_height",
                    "letter_spacing",
                    "text_align",
                )
            },
        ),
        (
            "Header",
            {
                "fields": (
                    "header_enabled",
                    "header_title",
                    "header_subtitle",
                    "header_alignment",
                    "header_height",
                    "header_border",
                )
            },
        ),
        (
            "Button",
            {
                "fields": (
                    "button_enabled",
                    "button_text",
                    "button_background_color",
                    "button_text_color",
                    "button_font_size",
                    "button_font_weight",
                    "button_border",
                    "button_border_radius",
                    "button_padding",
                    "button_alignment",
                )
            },
        ),
        (
            "Animation",
            {
                "fields": (
                    "animation",
                    "animation_duration",
                )
            },
        ),
        (
            "Mobile / Responsive",
            {
                "fields": (
                    "mobile_enabled",
                    "mobile_width",
                    "mobile_height",
                    "mobile_position",
                    "mobile_bottom_sheet",
                    "mobile_border_radius",
                    "mobile_padding",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(CentralPopupRegistry)
class CentralPopupRegistryAdmin(admin.ModelAdmin):
    list_display = (
        "popup_name",
        "popup_id",
        "popup_type",
        "is_active",
        "display_order",
        "updated_at",
    )

    list_filter = (
        "popup_type",
        "is_active",
    )

    search_fields = (
        "popup_name",
        "popup_id",
    )

    ordering = (
        "display_order",
        "popup_name",
    )

    fieldsets = (
        (
            "Popup Identity",
            {
                "fields": (
                    "popup_name",
                    "popup_id",
                    "popup_type",
                    "is_active",
                    "display_order",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
