from django.core.exceptions import ValidationError


def validate_category_name(name):
    if not name or not name.strip():
        raise ValidationError("Category name cannot be empty.")

    if len(name.strip()) > 255:
        raise ValidationError(
            "Category name cannot exceed 255 characters."
        )


def validate_category_slug(slug):
    if not slug or not slug.strip():
        raise ValidationError("Category slug cannot be empty.")

    if len(slug.strip()) > 255:
        raise ValidationError(
            "Category slug cannot exceed 255 characters."
        )

from .models import Category


def validate_category_visibility(visibility):
    valid_values = {
        Category.VISIBILITY_PUBLIC,
        Category.VISIBILITY_HIDDEN,
        Category.VISIBILITY_DISABLED,
    }

    if visibility not in valid_values:
        raise ValidationError(
            "Invalid category visibility."
        )

def validate_category_parent(category, parent):
    if parent is None:
        return

    if category is not None and category.pk == parent.pk:
        raise ValidationError(
            "A category cannot be its own parent."
        )

def validate_category_parent_status(parent):
    if parent is None:
        return

    if parent.is_deleted:
        raise ValidationError(
            "A deleted category cannot be used as a parent."
        )

def validate_category_parent_hierarchy(category, parent):
    if parent is None:
        return

    current = parent

    while current is not None:
        if category is not None and current.pk == category.pk:
            raise ValidationError(
                "A category cannot be placed under its own descendant."
            )

        current = current.parent