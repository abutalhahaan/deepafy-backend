from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


UPAZILAS = {
    "Barguna": [
        "Amtali",
        "Bamna",
        "Barguna Sadar",
        "Betagi",
        "Patharghata",
        "Taltali",
    ],
    "Barishal": [
        "Agailjhara",
        "Babuganj",
        "Bakerganj",
        "Banaripara",
        "Gournadi",
        "Hizla",
        "Barishal Sadar",
        "Mehendiganj",
        "Muladi",
        "Wazirpur",
    ],
    "Bhola": [
        "Bhola Sadar",
        "Borhanuddin",
        "Daulatkhan",
        "Lalmohan",
        "Manpura",
        "Tazumuddin",
        "Char Fasson",
    ],
    "Jhalokathi": [
        "Jhalokathi Sadar",
        "Nalchity",
        "Kathalia",
        "Rajapur",
    ],
    "Patuakhali": [
        "Bauphal",
        "Dashmina",
        "Dumki",
        "Kalapara",
        "Mirzaganj",
        "Patuakhali Sadar",
        "Rangabali",
        "Galachipa",
    ],
    "Pirojpur": [
        "Bhandaria",
        "Kawkhali",
        "Mathbaria",
        "Nazirpur",
        "Pirojpur Sadar",
        "Nesarabad",
        "Indurkani",
    ],
}


class Command(BaseCommand):
    help = "Seed Barishal Division Upazilas."

    @transaction.atomic
    def handle(self, *args, **options):
        country = Country.objects.get(code="BD")
        level = LocationLevel.objects.get(
            country=country,
            code="UPAZILA",
        )

        created = 0
        updated = 0

        for district_name, upazilas in UPAZILAS.items():
            district = AdministrativeLocation.objects.get(
                country=country,
                level__code="DISTRICT",
                name=district_name,
            )

            for sort_order, name in enumerate(upazilas, start=1):
                location, was_created = AdministrativeLocation.objects.update_or_create(
                    country=country,
                    level=level,
                    parent=district,
                    name=name,
                    defaults={
                        "is_active": True,
                        "sort_order": sort_order,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Barishal Upazila seed completed. Created: {created}, Updated: {updated}"
            )
        )
