from rest_framework import serializers

from .models import (
    AcademicBackground,
    AccountType,
    Hobby,
    PersonalAccount,
    PersonalHobby,
    PersonalInterestedCategory,
    ProfessionalAccount,
    UserIdentity,
)


class UserIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserIdentity
        fields = [
            "user_id",
            "email",
            "mobile_number",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user_id",
            "created_at",
            "updated_at",
        ]


class AccountTypeSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(
        source="get_account_type_display",
        read_only=True,
    )

    class Meta:
        model = AccountType
        fields = [
            "id",
            "account_type",
            "account_type_display",
            "is_primary",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class PersonalInterestedCategorySerializer(
    serializers.ModelSerializer
):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = PersonalInterestedCategory
        fields = [
            "id",
            "category",
            "category_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category_name",
            "created_at",
            "updated_at",
        ]


class HobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = Hobby
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "display_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class PersonalHobbySerializer(serializers.ModelSerializer):
    hobby_name = serializers.CharField(
        source="hobby.name",
        read_only=True,
    )

    class Meta:
        model = PersonalHobby
        fields = [
            "id",
            "hobby",
            "hobby_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "hobby_name",
            "created_at",
            "updated_at",
        ]


class PersonalAccountSerializer(serializers.ModelSerializer):
    permanent_country_name = serializers.CharField(
        source="permanent_country.name",
        read_only=True,
    )
    present_country_name = serializers.CharField(
        source="present_country.name",
        read_only=True,
    )

    class Meta:
        model = PersonalAccount
        fields = [
            "id",
            "identity",
            "display_name",
            "username",
            "permanent_country",
            "permanent_country_name",
            "permanent_city",
            "permanent_area",
            "permanent_full_address",
            "present_country",
            "present_country_name",
            "present_city",
            "present_area",
            "present_full_address",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "identity",
            "permanent_country_name",
            "present_country_name",
            "created_at",
            "updated_at",
        ]


class ProfessionalAccountSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProfessionalAccount
        fields = [
            "id",
            "identity",
            "professional_title",
            "profession",
            "industry",
            "professional_summary",
            "focus_job_area",
            "future_goal",
            "background_color",
            "tab_colors",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "identity",
            "created_at",
            "updated_at",
        ]



class AcademicBackgroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicBackground
        fields = [
            "id",
            "professional_account",
            "qualification",
            "institution",
            "field_of_study",
            "country",
            "city",
            "start_date",
            "end_date",
            "is_current",
            "result",
            "description",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]