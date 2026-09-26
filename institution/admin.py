from django.contrib import admin

from .models import (
    InstitutionType,
    InstitutionTypeGroup,
    InstitutionProfile,
    InstitutionAuthority,
)


@admin.register(InstitutionAuthority)
class InstitutionAuthorityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "short_name",
        "country",
        "relationship_type",
        "is_active",
        "display_order",
    )

    list_filter = (
        "country",
        "relationship_type",
        "is_active",
    )

    search_fields = (
        "name",
        "short_name",
        "code",
    )

    filter_horizontal = (
        "institution_types",
    )

    ordering = (
        "country",
        "relationship_type",
        "display_order",
        "name",
    )


@admin.register(InstitutionProfile)
class InstitutionProfileAdmin(admin.ModelAdmin):
    list_display = (
        "institution_name",
        "country",
        "institution_type",
        "is_verified",
        "is_active",
    )

    list_filter = (
        "country",
        "institution_type",
        "is_verified",
        "is_active",
    )

    search_fields = (
        "institution_name",
    )


admin.site.register(InstitutionType)
admin.site.register(InstitutionTypeGroup)
