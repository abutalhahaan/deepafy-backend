from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Category, CategoryRelationship
from .validators import (
    validate_category_name,
    validate_category_relationship,
    validate_category_slug,
    validate_category_visibility,
)


@transaction.atomic
def create_category(
    *,
    name,
    slug,
    description="",
    parent=None,
    is_featured=False,
    display_order=0,
    visibility=Category.VISIBILITY_PUBLIC,
):
    validate_category_name(name)
    validate_category_slug(slug)
    validate_category_visibility(visibility)

    category = Category.objects.create(
        name=name.strip(),
        slug=slug.strip(),
        description=description,
        is_featured=is_featured,
        display_order=display_order,
        visibility=visibility,
    )

    if parent is not None:
        add_category_relationship(
            parent=parent,
            child=category,
            display_order=display_order,
        )

    return category


@transaction.atomic
def update_category(category, **changes):
    allowed_fields = {
        "name",
        "slug",
        "description",
        "is_featured",
        "display_order",
        "visibility",
    }

    for field, value in changes.items():
        if field not in allowed_fields:
            continue

        if field == "name":
            validate_category_name(value)
            value = value.strip()

        elif field == "slug":
            validate_category_slug(value)
            value = value.strip()

        elif field == "visibility":
            validate_category_visibility(value)

        setattr(category, field, value)

    category.save()
    return category


@transaction.atomic
def delete_category(category):
    category.soft_delete()
    return category


@transaction.atomic
def restore_category(category):
    category.restore()
    return category


@transaction.atomic
def add_category_relationship(
    parent,
    child,
    display_order=0,
):
    validate_category_relationship(parent, child)

    relationship, created = CategoryRelationship.objects.get_or_create(
        parent=parent,
        child=child,
        defaults={
            "display_order": display_order,
            "is_active": True,
        },
    )

    if not created and not relationship.is_active:
        relationship.is_active = True
        relationship.display_order = display_order
        relationship.save(
            update_fields=[
                "is_active",
                "display_order",
                "updated_at",
            ]
        )

    return relationship


@transaction.atomic
def remove_category_relationship(parent, child):
    try:
        relationship = CategoryRelationship.objects.get(
            parent=parent,
            child=child,
        )
    except CategoryRelationship.DoesNotExist:
        return None

    relationship.is_active = False
    relationship.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    return relationship