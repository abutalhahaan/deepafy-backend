from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


RANGPUR_UPAZILAS = {
    "Dinajpur": [
        "Birampur",
        "Birganj",
        "Biral",
        "Bochaganj",
        "Chirirbandar",
        "Dinajpur Sadar",
        "Fulbari",
        "Ghoraghat",
        "Hakimpur",
        "Kaharole",
        "Khansama",
        "Nawabganj",
        "Parbatipur",
    ],
    "Gaibandha": [
        "Fulchhari",
        "Gaibandha Sadar",
        "Gobindaganj",
        "Palashbari",
        "Sadullapur",
        "Saghata",
        "Sundarganj",
    ],
    "Kurigram": [
        "Bhurungamari",
        "Char Rajibpur",
        "Chilmari",
        "Kurigram Sadar",
        "Nageshwari",
        "Phulbari",
        "Rajarhat",
        "Raomari",
        "Ulipur",
    ],
    "Lalmonirhat": [
        "Aditmari",
        "Hatibandha",
        "Kaliganj",
        "Lalmonirhat Sadar",
        "Patgram",
    ],
    "Nilphamari": [
        "Dimla",
        "Domar",
        "Jaldhaka",
        "Kishoreganj",
        "Nilphamari Sadar",
        "Saidpur",
    ],
    "Panchagarh": [
        "Atwari",
        "Boda",
        "Debiganj",
        "Panchagarh Sadar",
        "Tetulia",
    ],
    "Rangpur": [
        "Badarganj",
        "Gangachara",
        "Kaunia",
        "Mithapukur",
        "Pirganj",
        "Pirgachha",
        "Rangpur Sadar",
        "Taraganj",
    ],
    "Thakurgaon": [
        "Baliadangi",
        "Haripur",
        "Pirganj",
        "Ranisankail",
        "Thakurgaon Sadar",
    ],
}


class Command(BaseCommand):
    help = "Seed Rangpur Division upazilas."

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
            name="Rangpur",
        )

        created = 0
        updated = 0

        for district_name, upazilas in RANGPUR_UPAZILAS.items():
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
                f"Rangpur Upazila seed completed. "
                f"Created: {created}, Updated: {updated}"
            )
        )
