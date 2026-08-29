from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import Category, CategoryRelationship
from .services import (
    add_category_relationship,
    create_category,
    delete_category,
    remove_category_relationship,
    restore_category,
    update_category,
)


def _category_data(category):
    return {
        "id": category.id,
        "category_id": str(category.category_id),
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "is_featured": category.is_featured,
        "display_order": category.display_order,
        "visibility": category.visibility,
        "is_deleted": category.is_deleted,
        "created_at": category.created_at.isoformat(),
        "updated_at": category.updated_at.isoformat(),
    }

def _category_tree(category):
    children = CategoryRelationship.objects.filter(
        parent=category,
        is_active=True,
        child__is_deleted=False,
    ).select_related("child").order_by(
        "display_order",
        "child__name",
    )

    return {
        "id": category.id,
        "category_id": str(category.category_id),
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "is_featured": category.is_featured,
        "display_order": category.display_order,
        "visibility": category.visibility,
        "children": [
            _category_tree(
                relationship.child
            )
            for relationship in children
        ],
    }

@require_http_methods(["GET"])
def category_tree(request):
    categories = Category.objects.filter(
        is_deleted=False,
    ).filter(
        parent_relationships__isnull=True,
    ).distinct().order_by(
        "display_order",
        "name",
    )

    return JsonResponse(
        {
            "count": categories.count(),
            "results": [
                _category_tree(category)
                for category in categories
            ],
        }
    )


@require_http_methods(["GET"])
def category_list(request):
    categories = Category.objects.all().order_by(
        "display_order",
        "name",
    )

    return JsonResponse(
        {
            "count": categories.count(),
            "results": [
                _category_data(category)
                for category in categories
            ],
        }
    )


@require_http_methods(["GET"])
def category_detail(request, category_id):
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return JsonResponse(
            {"detail": "Category not found."},
            status=404,
        )

    return JsonResponse(_category_data(category))


@csrf_exempt
@require_http_methods(["POST"])
def category_create(request):
    import json

    try:
        data = json.loads(request.body or "{}")

        category = create_category(
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            description=data.get("description", ""),
            is_featured=data.get("is_featured", False),
            display_order=data.get("display_order", 0),
            visibility=data.get(
                "visibility",
                Category.VISIBILITY_PUBLIC,
            ),
        )

        parent_id = data.get("parent_id")

        if parent_id is not None:
            try:
                parent = Category.objects.get(id=parent_id)
            except Category.DoesNotExist:
                category.delete()
                return JsonResponse(
                    {"detail": "Parent category not found."},
                    status=404,
                )

            add_category_relationship(
                parent=parent,
                child=category,
                display_order=data.get("display_order", 0),
            )

        return JsonResponse(
            _category_data(category),
            status=201,
        )

    except (ValidationError, ValueError, TypeError) as exc:
        return JsonResponse(
            {"detail": str(exc)},
            status=400,
        )


@csrf_exempt
@require_http_methods(["PATCH"])
def category_update(request, category_id):
    import json

    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return JsonResponse(
            {"detail": "Category not found."},
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")

        allowed_fields = {
            "name",
            "slug",
            "description",
            "is_featured",
            "display_order",
            "visibility",
        }

        changes = {
            field: data[field]
            for field in allowed_fields
            if field in data
        }

        category = update_category(
            category,
            **changes,
        )

        return JsonResponse(_category_data(category))

    except (ValidationError, ValueError, TypeError) as exc:
        return JsonResponse(
            {"detail": str(exc)},
            status=400,
        )


@csrf_exempt
@require_http_methods(["DELETE"])
def category_delete(request, category_id):
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return JsonResponse(
            {"detail": "Category not found."},
            status=404,
        )

    delete_category(category)

    return JsonResponse(
        {
            "detail": "Category deleted successfully.",
            "category": _category_data(category),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def category_restore(request, category_id):
    try:
        category = Category.objects.deleted_only().get(
            id=category_id
        )
    except Category.DoesNotExist:
        return JsonResponse(
            {"detail": "Deleted category not found."},
            status=404,
        )

    restore_category(category)

    return JsonResponse(_category_data(category))


@require_http_methods(["GET"])
def category_relationships(request, category_id):
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return JsonResponse(
            {"detail": "Category not found."},
            status=404,
        )

    children = CategoryRelationship.objects.filter(
        parent=category,
        is_active=True,
    ).select_related("child")

    parents = CategoryRelationship.objects.filter(
        child=category,
        is_active=True,
    ).select_related("parent")

    return JsonResponse(
        {
            "category": _category_data(category),
            "parents": [
                _category_data(
                    relationship.parent
                )
                for relationship in parents
            ],
            "children": [
                _category_data(
                    relationship.child
                )
                for relationship in children
            ],
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def category_relationship_create(request):
    import json

    try:
        data = json.loads(request.body or "{}")

        parent_id = data.get("parent_id")
        child_id = data.get("child_id")

        if parent_id is None or child_id is None:
            return JsonResponse(
                {
                    "detail": (
                        "parent_id and child_id are required."
                    )
                },
                status=400,
            )

        try:
            parent = Category.objects.get(id=parent_id)
            child = Category.objects.get(id=child_id)
        except Category.DoesNotExist:
            return JsonResponse(
                {"detail": "Parent or child category not found."},
                status=404,
            )

        relationship = add_category_relationship(
            parent=parent,
            child=child,
            display_order=data.get(
                "display_order",
                0,
            ),
        )

        return JsonResponse(
            {
                "id": relationship.id,
                "parent_id": relationship.parent.id,
                "child_id": relationship.child.id,
                "display_order": relationship.display_order,
                "is_active": relationship.is_active,
            },
            status=201,
        )

    except (ValidationError, ValueError, TypeError) as exc:
        return JsonResponse(
            {"detail": str(exc)},
            status=400,
        )


@csrf_exempt
@require_http_methods(["DELETE"])
def category_relationship_delete(request):
    import json

    try:
        data = json.loads(request.body or "{}")

        parent_id = data.get("parent_id")
        child_id = data.get("child_id")

        if parent_id is None or child_id is None:
            return JsonResponse(
                {
                    "detail": (
                        "parent_id and child_id are required."
                    )
                },
                status=400,
            )

        parent = Category.objects.get(id=parent_id)
        child = Category.objects.get(id=child_id)

        relationship = remove_category_relationship(
            parent=parent,
            child=child,
        )

        if relationship is None:
            return JsonResponse(
                {"detail": "Relationship not found."},
                status=404,
            )

        return JsonResponse(
            {
                "detail": (
                    "Category relationship removed successfully."
                )
            }
        )

    except Category.DoesNotExist:
        return JsonResponse(
            {"detail": "Parent or child category not found."},
            status=404,
        )

    except (ValidationError, ValueError, TypeError) as exc:
        return JsonResponse(
            {"detail": str(exc)},
            status=400,
        )