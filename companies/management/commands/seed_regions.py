from django.core.management.base import BaseCommand
from companies.models import Region


REGIONS = [
    ("Africa", 1),
    ("Americas", 2),
    ("Asia", 3),
    ("Europe", 4),
    ("Oceania", 5),
]


class Command(BaseCommand):
    help = "Seed the standard global regions."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for name, sort_order in REGIONS:
            region, was_created = Region.objects.update_or_create(
                name=name,
                defaults={
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Region seed completed. Created: {created}, Updated: {updated}"
            )
        )
