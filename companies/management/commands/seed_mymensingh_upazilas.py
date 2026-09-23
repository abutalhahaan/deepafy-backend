from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


MYMENSINGH_UPAZILAS = {
    "Jamalpur": [
        "Baksiganj",
        "Dewanganj",
        "Islampur",
        "Jamalpur Sadar",
        "Madarganj",
        "Melandaha",
        "Sarishabari",
    ],
    "Mymensingh": [
        "Bhaluka",
        "Dhobaura",
        "Fulbaria",
        "Gaffargaon",
        "Gauripur",
        "Haluaghat",
        "Ishwarganj",
        "Mymensingh Sadar",
        "Muktagachha",
        "Nandail",
        "Phulpur",
        "Tarakanda",
        "Trishal",
    ],
    "Netrokona": [
        "Atpara",
        "Barhatta",
        "Durgapur",
        "Khaliajuri",
        "Kalmakanda",
        "Kendua",
        "Madan",
        "Mohanganj",
        "Netrokona Sadar",
        "Purbadhala",
    ],
    "Sherpur": [
        "Jhenaigati",
        "Nakla",
        "Nalitabari",
        "Sherpur Sadar",
        "Sreebardi",
    ],
}


class Command(BaseCommand):
    help = "Seed Mymensingh Division upazilas."

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

        division = AdministrativeLocation.objects.get(
            country=country,
            level__level=1,
            name="Mymensingh",
        )

        created = 0
        updated = 0

        for district_name, upazilas in MYMENSINGH_UPAZILAS.items():
            district = AdministrativeLocation.objects.get(
                country=country,
                level=district_level,
                parent=division,
                name=district_name,
            )

            for sort_order, name in enumerate(upazilas, start=1):
                obj, was_created = AdministrativeLocation.objects.update_or_create(
                    country=country,
                    level=upazila_level,
                    parent=district,
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
                f"Mymensingh Upazila seed completed. "
                f"Created: {created}, Updated: {updated}"
            )
        )
