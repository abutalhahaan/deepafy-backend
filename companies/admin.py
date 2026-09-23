from django.contrib import admin

from .models import (
    AdministrativeAssignment,
    AdministrativeRole,
    Company,
    CompanyRelationship,
    Country,
    CountryDepartment,
    Region,
    LocationLevel,
    AdministrativeLocation,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "company_type",
        "country",
        "business_email",
        "business_mobile_number",
        "created_at",
    ]

    search_fields = [
        "name",
        "company_type",
        "country",
        "business_email",
    ]

    ordering = [
        "name",
    ]


@admin.register(CompanyRelationship)
class CompanyRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        "company",
        "identity",
        "relationship_type",
        "membership_status",
        "created_at",
    ]

    list_filter = [
        "relationship_type",
        "membership_status",
    ]

    search_fields = [
        "company__name",
        "identity__email",
    ]


@admin.register(AdministrativeRole)
class AdministrativeRoleAdmin(admin.ModelAdmin):
    list_display = [
        "identity",
        "role_type",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "role_type",
        "is_active",
    ]

    search_fields = [
        "identity__email",
    ]


@admin.register(AdministrativeAssignment)
class AdministrativeAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "identity",
        "role",
        "reporting_boss",
        "is_primary",
        "is_active",
    ]

    list_filter = [
        "is_primary",
        "is_active",
    ]

    search_fields = [
        "identity__email",
        "reporting_boss__email",
    ]


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "sort_order",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_active",
    ]

    list_editable = [
        "sort_order",
        "is_active",
    ]

    search_fields = [
        "name",
    ]

    ordering = [
        "sort_order",
        "name",
    ]


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "phone_code",
        "region",
        "sort_order",
        "is_active",
    ]

    list_filter = [
        "region",
        "is_active",
    ]

    search_fields = [
        "name",
        "code",
        "phone_code",
    ]

    ordering = [
        "sort_order",
        "name",
    ]

    list_editable = [
        "sort_order",
        "is_active",
    ]


@admin.register(CountryDepartment)
class CountryDepartmentAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "country",
        "is_active",
    ]

    list_filter = [
        "country",
        "is_active",
    ]

    search_fields = [
        "name",
        "code",
        "country__name",
    ]

    ordering = [
        "country",
        "name",
    ]

@admin.register(LocationLevel)
class LocationLevelAdmin(admin.ModelAdmin):
    list_display = [
        "country",
        "level",
        "name",
        "code",
        "sort_order",
        "is_active",
    ]

    list_filter = [
        "country",
        "is_active",
    ]

    search_fields = [
        "country__name",
        "name",
        "code",
    ]

    ordering = [
        "country",
        "level",
        "sort_order",
        "name",
    ]

    list_editable = [
        "name",
        "code",
        "sort_order",
        "is_active",
    ]


@admin.register(AdministrativeLocation)
class AdministrativeLocationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "country",
        "level",
        "parent",
        "sort_order",
        "is_active",
    ]

    list_filter = [
        "country",
        "level",
        "is_active",
    ]

    search_fields = [
        "name",
        "code",
        "country__name",
        "level__name",
        "parent__name",
    ]

    ordering = [
        "country",
        "level",
        "sort_order",
        "name",
    ]

    list_editable = [
        "sort_order",
        "is_active",
    ]
