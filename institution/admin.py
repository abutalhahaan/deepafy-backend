from django.contrib import admin

from .models import (
    InstitutionType,
    InstitutionTypeGroup,
    InstitutionProfile,
    InstitutionAuthority,
    Subject,
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


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering = (
        "name",
    )

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(InstitutionType)
admin.site.register(InstitutionTypeGroup)
