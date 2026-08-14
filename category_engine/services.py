from django.db import transaction

from .models import Category


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