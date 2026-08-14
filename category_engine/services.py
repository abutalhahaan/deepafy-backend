from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Category, CategoryRelationship


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
    return Category.objects.create(
        name=name,
        slug=slug,
        description=description,
        parent=parent,
        is_featured=is_featured,
        display_order=display_order,
        visibility=visibility,
    )

@transaction.atomic
def update_category(category, **changes):
    allowed_fields = {
        "name",
        "slug",
        "description",
        "parent",
        "is_featured",
        "display_order",
        "visibility",
    }

    for field, value in changes.items():
        if field in allowed_fields:
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
def add_category_relationship(parent, child, display_order=0):
    if parent.is_deleted:
        raise ValidationError(
            "A deleted category cannot be used as a parent."
        )

    if child.is_deleted:
        raise ValidationError(
            "A deleted category cannot be used as a child."
        )

    if parent.pk == child.pk:
        raise ValidationError(
            "A category cannot be related to itself."
        )

    current = parent

    while current is not None:
        if current.pk == child.pk:
            raise ValidationError(
                "This relationship would create a circular category hierarchy."
            )

        current = current.parent

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
    relationship.save(update_fields=["is_active", "updated_at"])

    return relationship