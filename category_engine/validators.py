from django.core.exceptions import ValidationError

from .models import Category, CategoryRelationship


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


def validate_category_visibility(visibility):
    valid_values = {
        Category.VISIBILITY_PUBLIC,
        Category.VISIBILITY_HIDDEN,
        Category.VISIBILITY_DISABLED,
    }

    if visibility not in valid_values:
        raise ValidationError("Invalid category visibility.")


def validate_category_relationship(parent, child):
    if parent is None or child is None:
        raise ValidationError(
            "Both parent and child categories are required."
        )

    if parent.pk == child.pk:
        raise ValidationError(
            "A category cannot be related to itself."
        )

    if parent.is_deleted:
        raise ValidationError(
            "A deleted category cannot be used as a parent."
        )

    if child.is_deleted:
        raise ValidationError(
            "A deleted category cannot be used as a child."
        )

    stack = [child]
    visited = set()

    while stack:
        current = stack.pop()

        if current.pk in visited:
            continue

        visited.add(current.pk)

        if current.pk == parent.pk:
            raise ValidationError(
                "This relationship would create a circular category hierarchy."
            )

        relationships = CategoryRelationship.objects.filter(
            parent=current,
            is_active=True,
        ).select_related("child")

        for relationship in relationships:
            stack.append(relationship.child)