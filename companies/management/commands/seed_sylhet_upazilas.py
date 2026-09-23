from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


SYLHET_UPAZILAS = {
    "Habiganj": [
        "Ajmiriganj",
        "Bahubal",
        "Baniachong",
        "Chunarughat",
        "Habiganj Sadar",
        "Lakhai",
        "Madhabpur",
        "Nabiganj",
        "Shayestaganj",
    ],
    "Moulvibazar": [
        "Barlekha",
        "Juri",
        "Kamalganj",
        "Kulaura",
        "Moulvibazar Sadar",
        "Rajnagar",
        "Sreemangal",
    ],
    "Sunamganj": [
        "Bishwambharpur",
        "Chhatak",
        "Derai",
        "Dharampasha",
        "Dowarabazar",
        "Jagannathpur",
        "Jamalganj",
        "Madhyanagar",
        "Shalla",
        "Shantiganj",
        "Sunamganj Sadar",
        "Tahirpur",
    ],
    "Sylhet": [
        "Balaganj",
        "Beanibazar",
        "Bishwanath",
        "Companiganj",
        "Dakshin Surma",
        "Fenchuganj",
        "Golapganj",
        "Gowainghat",
        "Jaintiapur",
        "Kanaighat",
        "Osmani Nagar",
        "Sylhet Sadar",
        "Zakiganj",
    ],
}


class Command(BaseCommand):
    help = "Seed Sylhet Division upazilas."

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
            name="Sylhet",
        )

        created = 0
        updated = 0

        for district_name, upazilas in SYLHET_UPAZILAS.items():
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
                f"Sylhet Upazila seed completed. "
                f"Created: {created}, Updated: {updated}"
            )
        )
