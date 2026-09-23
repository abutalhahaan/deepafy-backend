from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


KHULNA_UPAZILAS = {
    "Bagerhat": [
        "Bagerhat Sadar",
        "Chitalmari",
        "Fakirhat",
        "Kachua",
        "Mollahat",
        "Mongla",
        "Morrelganj",
        "Rampal",
        "Sarankhola",
    ],
    "Chuadanga": [
        "Alamdanga",
        "Chuadanga Sadar",
        "Damurhuda",
        "Jibannagar",
    ],
    "Jashore": [
        "Abhaynagar",
        "Bagherpara",
        "Chaugachha",
        "Jashore Sadar",
        "Jhikargachha",
        "Keshabpur",
        "Manirampur",
        "Sharsha",
    ],
    "Jhenaidah": [
        "Harinakunda",
        "Jhenaidah Sadar",
        "Kaliganj",
        "Kotchandpur",
        "Maheshpur",
        "Shailkupa",
    ],
    "Khulna": [
        "Batiaghata",
        "Dacope",
        "Dumuria",
        "Dighalia",
        "Koyra",
        "Paikgachha",
        "Phultala",
        "Rupsa",
        "Terokhada",
        "Khulna Sadar",
    ],
    "Kushtia": [
        "Bheramara",
        "Daulatpur",
        "Khoksa",
        "Kumarkhali",
        "Kushtia Sadar",
        "Mirpur",
    ],
    "Magura": [
        "Magura Sadar",
        "Mohammadpur",
        "Shalikha",
        "Sreepur",
    ],
    "Meherpur": [
        "Gangni",
        "Meherpur Sadar",
        "Mujibnagar",
    ],
    "Narail": [
        "Kalia",
        "Lohagara",
        "Narail Sadar",
    ],
    "Satkhira": [
        "Assasuni",
        "Debhata",
        "Kalaroa",
        "Kaliganj",
        "Satkhira Sadar",
        "Shyamnagar",
        "Tala",
    ],
}


class Command(BaseCommand):
    help = "Seed Khulna Division upazilas."

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
            name="Khulna",
        )

        created = 0
        updated = 0

        for district_name, upazilas in KHULNA_UPAZILAS.items():
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
                f"Khulna Upazila seed completed. "
                f"Created: {created}, Updated: {updated}"
            )
        )
