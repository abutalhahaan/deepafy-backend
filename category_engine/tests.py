from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Category, CategoryRelationship
from .services import (
    add_category_relationship,
    create_category,
    remove_category_relationship,
)


class CategoryServiceTests(TestCase):
    def test_create_root_category(self):
        category = create_category(
            name="Apparel",
            slug="apparel",
        )

        self.assertEqual(category.name, "Apparel")
        self.assertEqual(category.slug, "apparel")
        self.assertEqual(
            Category.objects.filter(pk=category.pk).exists(),
            True,
        )

    def test_create_nested_category(self):
        parent = create_category(
            name="Apparel",
            slug="apparel",
        )

        child = create_category(
            name="T-Shirts",
            slug="t-shirts",
            parent=parent,
        )

        self.assertTrue(
            CategoryRelationship.objects.filter(
                parent=parent,
                child=child,
                is_active=True,
            ).exists()
        )

    def test_category_cannot_be_its_own_parent(self):
        category = create_category(
            name="Apparel",
            slug="apparel",
        )

        with self.assertRaises(ValidationError):
            add_category_relationship(
                parent=category,
                child=category,
            )

    def test_circular_relationship_is_rejected(self):
        apparel = create_category(
            name="Apparel",
            slug="apparel",
        )

        textile = create_category(
            name="Textile",
            slug="textile",
        )

        garments = create_category(
            name="Garments",
            slug="garments",
        )

        add_category_relationship(
            parent=apparel,
            child=textile,
        )

        add_category_relationship(
            parent=textile,
            child=garments,
        )

        with self.assertRaises(ValidationError):
            add_category_relationship(
                parent=garments,
                child=apparel,
            )

    def test_deleted_parent_is_rejected(self):
        parent = create_category(
            name="Apparel",
            slug="apparel",
        )

        child = create_category(
            name="T-Shirts",
            slug="t-shirts",
        )

        parent.soft_delete()

        with self.assertRaises(ValidationError):
            add_category_relationship(
                parent=parent,
                child=child,
            )

    def test_deleted_child_is_rejected(self):
        parent = create_category(
            name="Apparel",
            slug="apparel",
        )

        child = create_category(
            name="T-Shirts",
            slug="t-shirts",
        )

        child.soft_delete()

        with self.assertRaises(ValidationError):
            add_category_relationship(
                parent=parent,
                child=child,
            )

    def test_duplicate_relationship_is_not_created(self):
        parent = create_category(
            name="Apparel",
            slug="apparel",
        )

        child = create_category(
            name="T-Shirts",
            slug="t-shirts",
        )

        first = add_category_relationship(
            parent=parent,
            child=child,
        )

        second = add_category_relationship(
            parent=parent,
            child=child,
        )

        self.assertEqual(first.pk, second.pk)

        self.assertEqual(
            CategoryRelationship.objects.filter(
                parent=parent,
                child=child,
            ).count(),
            1,
        )

    def test_remove_relationship_soft_deletes_relationship(self):
        parent = create_category(
            name="Apparel",
            slug="apparel",
        )

        child = create_category(
            name="T-Shirts",
            slug="t-shirts",
        )

        relationship = add_category_relationship(
            parent=parent,
            child=child,
        )

        removed = remove_category_relationship(
            parent=parent,
            child=child,
        )

        self.assertEqual(removed.pk, relationship.pk)
        self.assertFalse(removed.is_active)

    def test_inactive_relationship_can_be_restored(self):
        parent = create_category(
            name="Apparel",
            slug="apparel",
        )

        child = create_category(
            name="T-Shirts",
            slug="t-shirts",
        )

        relationship = add_category_relationship(
            parent=parent,
            child=child,
        )

        remove_category_relationship(
            parent=parent,
            child=child,
        )

        restored = add_category_relationship(
            parent=parent,
            child=child,
            display_order=5,
        )

        self.assertEqual(restored.pk, relationship.pk)
        self.assertTrue(restored.is_active)
        self.assertEqual(restored.display_order, 5)