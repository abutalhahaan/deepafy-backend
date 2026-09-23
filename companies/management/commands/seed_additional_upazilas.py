from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


ADDITIONAL_UPAZILAS = {
    "Chattogram": [
        "Fatikchhari North",
    ],
    "Cumilla": [
        "Bangra",
    ],
    "Mymensingh": [
        "South Gafargaon",
    ],
    "Bogura": [
        "Mokamtala",
    ],
    "Cox's Bazar": [
        "Matamuhuri",
    ],
    "Thakurgaon": [
        "Ruhia",
        "Bhulli",
    ],
    "Lakshmipur": [
        "Chandraganj",
    ],
}


class Command(BaseCommand):
    help = "Seed additional Bangladesh administrative locations."

    @transaction.atomic
    def handle(self, *args, **options):
        country = Country.objects.get(code="BD")

        upazila_level = LocationLevel.objects.get(
            country=country,
            level=3,
            code="UPAZILA",
        )

        district_level = LocationLevel.objects.get(
            country=country,
            level=2,
            code="DISTRICT",
        )

        created = 0
        updated = 0

        for district_name, locations in ADDITIONAL_UPAZILAS.items():
            district = AdministrativeLocation.objects.get(
                country=country,
                level=district_level,
                name=district_name,
            )

            last_sort_order = (
                AdministrativeLocation.objects.filter(
                    country=country,
                    level=upazila_level,
                    parent=district,
                ).order_by("-sort_order").values_list("sort_order", flat=True).first()
                or 0
            )

            for name in locations:
                obj, was_created = AdministrativeLocation.objects.update_or_create(
                    country=country,
                    level=upazila_level,
                    parent=district,
                    name=name,
                    defaults={
                        "sort_order": last_sort_order + 1,
                        "is_active": True,
                    },
                )

                if was_created:
                    created += 1
                    last_sort_order += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Additional Upazila seed completed. "
                f"Created: {created}, Updated: {updated}"
            )
        )
