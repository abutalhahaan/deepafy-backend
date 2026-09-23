from django.contrib import admin

from .models import InstitutionType, InstitutionTypeGroup


@admin.register(InstitutionTypeGroup)
class InstitutionTypeGroupAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "sort_order",
        "is_active",
    ]

    list_filter = [
        "is_active",
    ]

    search_fields = [
        "name",
    ]

    list_editable = [
        "sort_order",
        "is_active",
    ]

    ordering = [
        "sort_order",
        "name",
    ]


@admin.register(InstitutionType)
class InstitutionTypeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "group",
        "sort_order",
        "is_active",
    ]

    list_filter = [
        "group",
        "is_active",
    ]

    search_fields = [
        "name",
        "group__name",
    ]

    list_editable = [
        "sort_order",
        "is_active",
    ]

    ordering = [
        "group",
        "sort_order",
        "name",
    ]
