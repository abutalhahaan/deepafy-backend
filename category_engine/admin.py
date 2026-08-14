from django.contrib import admin

from .models import (
    Category,
    CategoryCountryOverride,
    CategoryRelationship,
    CategoryTranslation,
    CategoryVersion,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "visibility",
        "is_featured",
        "display_order",
        "is_deleted",
        "updated_at",
    )

    list_filter = (
        "visibility",
        "is_featured",
        "is_deleted",
    )

    search_fields = (
        "name",
        "slug",
        "category_id",
    )

    ordering = (
        "display_order",
        "name",
    )


@admin.register(CategoryRelationship)
class CategoryRelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "parent",
        "child",
        "display_order",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "parent__name",
        "child__name",
        "parent__slug",
        "child__slug",
    )

    ordering = (
        "display_order",
        "parent",
        "child",
    )


@admin.register(CategoryTranslation)
class CategoryTranslationAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "language_code",
        "name",
        "updated_at",
    )

    list_filter = (
        "language_code",
    )

    search_fields = (
        "category__name",
        "category__slug",
        "language_code",
        "name",
    )


@admin.register(CategoryCountryOverride)
class CategoryCountryOverrideAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "country",
        "is_enabled",
        "display_order",
        "updated_at",
    )

    list_filter = (
        "is_enabled",
        "country",
    )

    search_fields = (
        "category__name",
        "category__slug",
        "country__name",
    )


@admin.register(CategoryVersion)
class CategoryVersionAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "country",
        "created_at",
    )

    list_filter = (
        "country",
    )

    search_fields = (
        "category__name",
        "category__slug",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "category",
        "country",
        "previous_configuration",
        "current_configuration",
        "created_at",
    )