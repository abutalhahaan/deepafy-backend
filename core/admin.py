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


class ButtonBorderWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            forms.Select(
                choices=[
                    ("0px", "None"), ("1px", "1px"), ("2px", "2px"),
                    ("3px", "3px"), ("4px", "4px"), ("5px", "5px"),
                    ("6px", "6px"), ("8px", "8px"), ("10px", "10px"),
                ],
                attrs={"class": "central-popup-button-border-width"},
            ),
            forms.Select(
                choices=[
                    ("none", "None"), ("solid", "Solid"),
                    ("dashed", "Dashed"), ("dotted", "Dotted"),
                    ("double", "Double"),
                ],
                attrs={"class": "central-popup-button-border-style"},
            ),
            forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "central-popup-color-picker central-popup-button-border-color",
                }
            ),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            return ["0px", "solid", "#FFFFFF"]

        parts = value.split()

        width = parts[0] if len(parts) >= 1 else "0px"
        style = parts[1] if len(parts) >= 2 else "solid"
        color = parts[2] if len(parts) >= 3 else "#FFFFFF"

        return [width, style, color]


class ButtonBorderField(forms.MultiValueField):
    def __init__(self, *args, **kwargs):
        fields = [
            forms.ChoiceField(
                choices=[
                    ("0px", "None"), ("1px", "1px"), ("2px", "2px"),
                    ("3px", "3px"), ("4px", "4px"), ("5px", "5px"),
                    ("6px", "6px"), ("8px", "8px"), ("10px", "10px"),
                ],
                required=False,
            ),
            forms.ChoiceField(
                choices=[
                    ("none", "None"), ("solid", "Solid"),
                    ("dashed", "Dashed"), ("dotted", "Dotted"),
                    ("double", "Double"),
                ],
                required=False,
            ),
            forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={"type": "color"}),
            ),
        ]

        kwargs.setdefault("require_all_fields", False)
        kwargs["widget"] = ButtonBorderWidget()

        super().__init__(fields=fields, *args, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return ""

        width = data_list[0] or "0px"
        style = data_list[1] or "solid"
        color = data_list[2] or "#FFFFFF"

        if width == "0px" or style == "none":
            return "0px none #FFFFFF"

        return f"{width} {style} {color}"


class CentralPopupSettingForm(forms.ModelForm):
    BORDER_WIDTH_CHOICES = [
        ("0", "None"),
        ("1px", "1px"),
        ("2px", "2px"),
        ("3px", "3px"),
        ("4px", "4px"),
        ("5px", "5px"),
        ("6px", "6px"),
        ("8px", "8px"),
        ("10px", "10px"),
    ]

    BORDER_STYLE_CHOICES = [
        ("none", "None"),
        ("solid", "Solid"),
        ("dashed", "Dashed"),
        ("dotted", "Dotted"),
        ("double", "Double"),
    ]

    FONT_FAMILY_CHOICES = [
        ("", "Default / System"),
        ("Arial, sans-serif", "Arial"),
        ("Inter, sans-serif", "Inter"),
        ("Roboto, sans-serif", "Roboto"),
        ("Poppins, sans-serif", "Poppins"),
        ("Montserrat, sans-serif", "Montserrat"),
        ("Open Sans, sans-serif", "Open Sans"),
        ("Lato, sans-serif", "Lato"),
        ("Nunito, sans-serif", "Nunito"),
        ("Merriweather, serif", "Merriweather"),
        ("Georgia, serif", "Georgia"),
        ("Times New Roman, serif", "Times New Roman"),
        ("Courier New, monospace", "Courier New"),
    ]

    BUTTON_RADIUS_CHOICES = [
        ("0px", "0px"),
        ("2px", "2px"),
        ("4px", "4px"),
        ("6px", "6px"),
        ("8px", "8px"),
        ("10px", "10px"),
        ("12px", "12px"),
        ("16px", "16px"),
        ("20px", "20px"),
        ("24px", "24px"),
        ("30px", "30px"),
        ("50px", "50px"),
    ]

    BUTTON_BORDER_WIDTH_CHOICES = [
        ("0px", "None"),
        ("1px", "1px"),
        ("2px", "2px"),
        ("3px", "3px"),
        ("4px", "4px"),
        ("5px", "5px"),
        ("6px", "6px"),
        ("8px", "8px"),
        ("10px", "10px"),
    ]

    BUTTON_BORDER_STYLE_CHOICES = [
        ("none", "None"),
        ("solid", "Solid"),
        ("dashed", "Dashed"),
        ("dotted", "Dotted"),
        ("double", "Double"),
    ]

    BUTTON_PADDING_CHOICES = [
        ("4px 8px", "4px 8px"),
        ("6px 12px", "6px 12px"),
        ("8px 16px", "8px 16px"),
        ("10px 18px", "10px 18px"),
        ("10px 20px", "10px 20px"),
        ("12px 24px", "12px 24px"),
        ("14px 28px", "14px 28px"),
        ("16px 32px", "16px 32px"),
        ("18px 36px", "18px 36px"),
        ("20px 40px", "20px 40px"),
    ]

    FONT_SIZE_CHOICES = [
        ("", "Default"),
        ("12px", "12px"),
        ("14px", "14px"),
        ("16px", "16px"),
        ("18px", "18px"),
        ("20px", "20px"),
        ("22px", "22px"),
        ("24px", "24px"),
        ("28px", "28px"),
        ("32px", "32px"),
        ("36px", "36px"),
        ("40px", "40px"),
        ("48px", "48px"),
        ("56px", "56px"),
        ("64px", "64px"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ---------------------------------------------------------------
        # Font Family — centralized dropdown
        # ---------------------------------------------------------------
        font_family_fields = [
            "font_family",
            "header_title_font_family",
            "header_subtitle_font_family",
            "tab_font_family",
            "button_font_family",
        ]

        for field_name in font_family_fields:
            if field_name in self.fields:
                original = self.fields[field_name]
                self.fields[field_name] = forms.ChoiceField(
                    required=False,
                    choices=self.FONT_FAMILY_CHOICES,
                    initial=original.initial,
                    label=original.label,
                    help_text=original.help_text,
                    widget=forms.Select(attrs={
                        "class": "central-popup-font-family",
                    }),
                )

        # ---------------------------------------------------------------
        # Font Size — centralized dropdown
        # ---------------------------------------------------------------
        font_size_fields = [
            "title_font_size",
            "body_font_size",
            "header_title_font_size",
            "header_subtitle_font_size",
            "tab_font_size",
            "button_font_size",
        ]

        for field_name in font_size_fields:
            if field_name in self.fields:
                original = self.fields[field_name]
                self.fields[field_name] = forms.ChoiceField(
                    required=False,
                    choices=self.FONT_SIZE_CHOICES,
                    initial=original.initial,
                    label=original.label,
                    help_text=original.help_text,
                    widget=forms.Select(attrs={
                        "class": "central-popup-font-size",
                    }),
                )

        # ---------------------------------------------------------------
        # Button Border — Width / Style / Color
        # ---------------------------------------------------------------
        if "button_border" in self.fields:
            original = self.fields["button_border"]

            self.fields["button_border"] = ButtonBorderField(
                required=False,
                label=original.label,
                help_text="Set the popup button border width, style, and color.",
                initial=original.initial,
            )

        # ---------------------------------------------------------------
        # Button Border Radius
        # ---------------------------------------------------------------
        if "button_border_radius" in self.fields:
            original = self.fields["button_border_radius"]
            self.fields["button_border_radius"] = forms.ChoiceField(
                required=False,
                choices=self.BUTTON_RADIUS_CHOICES,
                initial=original.initial,
                label=original.label,
                help_text=original.help_text,
                widget=forms.Select(attrs={
                    "class": "central-popup-button-radius",
                }),
            )

        # ---------------------------------------------------------------
        # Button Padding
        # ---------------------------------------------------------------
        if "button_padding" in self.fields:
            original = self.fields["button_padding"]
            self.fields["button_padding"] = forms.ChoiceField(
                required=False,
                choices=self.BUTTON_PADDING_CHOICES,
                initial=original.initial,
                label=original.label,
                help_text=original.help_text,
                widget=forms.Select(attrs={
                    "class": "central-popup-button-padding",
                }),
            )

        # ---------------------------------------------------------------
        # Border Width
        # ---------------------------------------------------------------
        if "border_width" in self.fields:
            original = self.fields["border_width"]
            self.fields["border_width"] = forms.ChoiceField(
                required=False,
                choices=self.BORDER_WIDTH_CHOICES,
                initial=original.initial,
                label=original.label,
                help_text=original.help_text,
                widget=forms.Select(attrs={
                    "class": "central-popup-border-width",
                }),
            )

        # ---------------------------------------------------------------
        # Border Style
        # ---------------------------------------------------------------
        if "border_style" in self.fields:
            original = self.fields["border_style"]
            self.fields["border_style"] = forms.ChoiceField(
                required=False,
                choices=self.BORDER_STYLE_CHOICES,
                initial=original.initial,
                label=original.label,
                help_text=original.help_text,
                widget=forms.Select(attrs={
                    "class": "central-popup-border-style",
                }),
            )

        # ---------------------------------------------------------------
        # All Color Fields — centralized color picker
        # ---------------------------------------------------------------
        color_fields = [
            "background_color",
            "header_background_color",
            "header_title_color",
            "header_subtitle_color",
            "body_color",
            "body_secondary_color",
            "body_link_color",
            "tab_background_color",
            "tab_active_background_color",
            "tab_text_color",
            "tab_active_text_color",
            "tab_border_color",
            "border_color",
            "button_border_color",
            "button_background_color",
            "button_text_color",
            "backdrop_color",
        ]

        for field_name in color_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.TextInput(
                    attrs={
                        "type": "color",
                        "class": "vTextField central-popup-color-picker",
                    }
                )

        # ---------------------------------------------------------------
        # Background priority is controlled automatically by JS.
        # ---------------------------------------------------------------
        if "background_visual_priority" in self.fields:
            self.fields["background_visual_priority"].widget = forms.HiddenInput()


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
            "popups": "এই সেটিং কোন কোন Popup ID-তে প্রযোজ্য হবে তা নির্বাচন করুন।",
            "country": "কোন দেশের ব্যবহারকারীদের জন্য এই Popup দেখানো হবে তা নির্বাচন করুন।",
            "is_enabled": "এই Popup configuration চালু বা বন্ধ করুন।",

            "content_title": "Popup-এর ভেতরে প্রদর্শিত প্রধান শিরোনাম।",
            "content_subtitle": "প্রধান শিরোনামের নিচে প্রদর্শিত সংক্ষিপ্ত সহায়ক লেখা।",
            "content_body": "Popup-এর ভেতরে প্রদর্শিত মূল বার্তা বা বিষয়বস্তু।",
            "button_url": "Popup-এর action button-এ ক্লিক করলে যে URL-এ ব্যবহারকারী যাবে।",

            "schedule_enabled": "নির্দিষ্ট সময়ের মধ্যে Popup দেখাতে চাইলে এটি চালু করুন।",
            "start_date": "যে তারিখ থেকে এই Popup configuration কার্যকর হবে।",
            "end_date": "যে তারিখের পর এই Popup configuration আর কার্যকর থাকবে না।",
            "repeat_yearly": "নির্ধারিত তারিখের সময়সীমা প্রতি বছর পুনরায় কার্যকর করুন।",
            "display_start_time": "প্রতিদিন যে সময় থেকে Popup দেখানো শুরু হতে পারবে।",
            "display_end_time": "প্রতিদিন যে সময়ের পর Popup দেখানো বন্ধ হবে।",

            "size": "Popup-এর সামগ্রিক আকারের preset।",
            "position": "স্ক্রিনের কোন অবস্থানে Popup প্রদর্শিত হবে।",
            "width": "Popup-এর প্রস্থ নির্ধারণ করে। যেমন: 600px বা 80%。",
            "height": "Popup-এর উচ্চতা নির্ধারণ করে। যেমন: 500px বা 80vh।",

            "background_color": "Background image ব্যবহার না হলে Popup-এর পেছনে যে রং দেখা যাবে।",
            "background_opacity": "Popup-এর background color কতটা স্বচ্ছ হবে তা নির্ধারণ করে।",
            "background_image": (
                "Upload the popup background image. A newly changed/uploaded image "
                "automatically becomes the active background."
            ),
            "background_visual_priority": (
                "Automatically controlled by the latest background color change "
                "or image upload."
            ),

            "border": "Popup border style, width, and color. Example: 2px solid #0A66C2.",
            "border_radius": "Popup-এর চারটি corner কতটা গোল হবে তা নির্ধারণ করে।",
            "box_shadow": "Popup-এর চারপাশে প্রদর্শিত shadow বা ছায়া।",

            "backdrop_enabled": "Popup-এর পেছনে অন্ধকার বা blur করা overlay চালু/বন্ধ করে।",
            "backdrop_color": "Popup-এর পেছনের overlay-এর রং নির্ধারণ করে।",
            "backdrop_opacity": "Popup-এর পেছনের overlay কতটা স্বচ্ছ হবে তা নির্ধারণ করে।",
            "backdrop_blur": "Popup-এর পেছনের page কত pixel blur হবে তা নির্ধারণ করে।",

            "show_close_button": "Popup-এর Close (×) button দেখাবে কি না।",
            "close_on_outside_click": "Popup-এর বাইরে ক্লিক করলে Popup বন্ধ হবে কি না।",
            "close_on_escape": "Keyboard-এর Escape চাপলে Popup বন্ধ হবে কি না।",
            "auto_close_enabled": "নির্দিষ্ট কয়েক সেকেন্ড পর Popup নিজে থেকে বন্ধ হবে কি না।",
            "auto_close_seconds": "Popup নিজে থেকে বন্ধ হওয়ার আগে কত সেকেন্ড অপেক্ষা করবে।",
        }

        for field_name, help_text in help_texts.items():
            if field_name in self.fields:
                self.fields[field_name].help_text = help_text

        # ---------------------------------------------------------------
        # Typography and Header Admin Help Text
        # ---------------------------------------------------------------
        additional_help_texts = {
            "font_family": (
                "Popup-এর লেখাগুলোতে কোন Font Family ব্যবহার হবে তা নির্ধারণ করে।"
            ),
            "title_font_size": (
                "Popup-এর প্রধান Title-এর লেখার আকার নির্ধারণ করে। যেমন: 28px।"
            ),
            "title_font_weight": (
                "Popup-এর প্রধান Title-এর লেখার মোটা/পাতলা হওয়ার মাত্রা নির্ধারণ করে। যেমন: 400, 600 বা 700।"
            ),
            "title_color": (
                "Popup-এর প্রধান Title-এর লেখার রং নির্ধারণ করে।"
            ),
            "body_font_size": (
                "Popup-এর মূল লেখার আকার নির্ধারণ করে।"
            ),
            "body_font_weight": (
                "Popup-এর মূল লেখার মোটা/পাতলা হওয়ার মাত্রা নির্ধারণ করে।"
            ),
            "body_color": (
                "Popup-এর মূল লেখার রং নির্ধারণ করে।"
            ),
            "line_height": (
                "এক লাইনের লেখা থেকে পরের লাইনের লেখার উল্লম্ব দূরত্ব নির্ধারণ করে।"
            ),
            "letter_spacing": (
                "প্রতিটি অক্ষরের মধ্যে কতটুকু ফাঁকা থাকবে তা নির্ধারণ করে।"
            ),
            "text_align": (
                "Popup-এর সাধারণ লেখার alignment নির্ধারণ করে: Left, Center বা Right।"
            ),

            "header_enabled": (
                "Popup-এর Header অংশটি চালু বা বন্ধ করে।"
            ),
            "header_title": (
                "Popup-এর Header অংশে প্রদর্শিত Title।"
            ),
            "header_subtitle": (
                "Header Title-এর নিচে প্রদর্শিত সহায়ক লেখা।"
            ),
            "header_alignment": (
                "Header-এর content কোথায় থাকবে তা নির্ধারণ করে: Left, Center বা Right।"
            ),
            "header_height": (
                "Popup-এর Header অংশের উচ্চতা নির্ধারণ করে।"
            ),
            "header_border": (
                "Header-এর চারপাশে বা নিচে Border/Separator নির্ধারণ করে।"
            ),

            "button_enabled": (
                "Popup-এর Action Button চালু বা বন্ধ করে।"
            ),
            "button_text": (
                "Popup-এর Button-এর ভেতরে যে লেখা দেখা যাবে।"
            ),
            "button_background_color": (
                "Popup Button-এর background-এর রং নির্ধারণ করে।"
            ),
            "button_text_color": (
                "Popup Button-এর লেখার রং নির্ধারণ করে।"
            ),
            "button_font_size": (
                "Popup Button-এর লেখার আকার নির্ধারণ করে।"
            ),
            "button_font_weight": (
                "Popup Button-এর লেখার মোটা/পাতলা হওয়ার মাত্রা নির্ধারণ করে।"
            ),
            "button_border_radius": (
                "Popup Button-এর corner কতটা গোল হবে তা নির্ধারণ করে।"
            ),
            "button_padding": (
                "Button-এর ভেতরের চারপাশে কতটুকু ফাঁকা জায়গা থাকবে তা নির্ধারণ করে। যেমন: 12px 28px।"
            ),
            "button_alignment": (
                "Popup Button কোথায় থাকবে তা নির্ধারণ করে: Left, Center বা Right।"
            ),

            "animation": (
                "Popup খোলার সময় কোন ধরনের animation ব্যবহার হবে তা নির্ধারণ করে। যেমন: Fade, Scale বা Slide।"
            ),
            "animation_duration": (
                "Popup খোলার animation কত মিলিসেকেন্ড চলবে তা নির্ধারণ করে। যেমন: 400।"
            ),

            "mobile_enabled": (
                "Mobile device-এর জন্য আলাদা Popup settings চালু বা বন্ধ করে।"
            ),
            "mobile_width": (
                "Mobile device-এ Popup-এর প্রস্থ নির্ধারণ করে। যেমন: 100%।"
            ),
            "mobile_height": (
                "Mobile device-এ Popup-এর উচ্চতা নির্ধারণ করে। যেমন: 80vh।"
            ),
            "mobile_position": (
                "Mobile device-এ Popup স্ক্রিনের কোন অবস্থানে থাকবে তা নির্ধারণ করে।"
            ),
            "mobile_bottom_sheet": (
                "Popup-কে Mobile-এর স্ক্রিনের নিচে সংযুক্ত Bottom Sheet হিসেবে দেখায়।"
            ),
            "mobile_border_radius": (
                "Mobile device-এ Popup-এর corner কতটা গোল হবে তা নির্ধারণ করে।"
            ),
            "mobile_padding": (
                "Mobile device-এ Popup-এর ভেতরের চারপাশে কতটুকু ফাঁকা জায়গা থাকবে তা নির্ধারণ করে।"
            ),
        }

        for field_name, help_text in additional_help_texts.items():
            if field_name in self.fields:
                self.fields[field_name].help_text = help_text





    all_popups = forms.BooleanField(
        required=False,
        label="All Popup IDs",
        help_text="Enable this to apply this setting to all active registered popups.",
    )

    class Meta:
        model = CentralPopupSetting
        fields = "__all__"

    class Media:
        css = {
            "all": (
                "core/css/central_popup_admin.css",
            )
        }
        js = (
            "core/js/central_popup_admin.js",
        )

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
                    "background_visual_priority",
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
                    "border_width",
                    "border_style",
                    "border_color",
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
            "Body Typography & Colors",
            {
                "fields": (
                    "font_family",
                    "body_font_size",
                    "body_font_weight",
                    "body_color",
                    "body_secondary_color",
                    "body_link_color",
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
                    "header_background_color",
                    "header_alignment",
                    "header_height",
                    "header_border",
                    "header_title_color",
                    "header_title_font_family",
                    "header_title_font_size",
                    "header_title_font_weight",
                    "header_title_line_height",
                    "header_title_letter_spacing",
                    "header_subtitle_color",
                    "header_subtitle_font_family",
                    "header_subtitle_font_size",
                    "header_subtitle_font_weight",
                    "header_subtitle_line_height",
                    "header_subtitle_letter_spacing",
                    "header_title",
                    "header_subtitle",
                )
            },
        ),
        (
            "Tabs",
            {
                "fields": (
                    "tab_background_color",
                    "tab_active_background_color",
                    "tab_text_color",
                    "tab_active_text_color",
                    "tab_border_color",
                    "tab_font_family",
                    "tab_font_size",
                    "tab_font_weight",
                    "tab_active_font_weight",
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
