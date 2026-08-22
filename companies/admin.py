from django.contrib import admin

from .models import (
    AdministrativeAssignment,
    AdministrativeRole,
    Company,
    CompanyRelationship,
    Country,
    CountryDepartment,
    Region,
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
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_active",
    ]

    search_fields = [
        "name",
    ]

    ordering = [
        "name",
    ]


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "phone_code",
        "region",
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
        "name",
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