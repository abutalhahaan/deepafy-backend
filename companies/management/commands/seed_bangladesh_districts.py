from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


DISTRICTS = {
    "Barishal": [
        "Barguna",
        "Barishal",
        "Bhola",
        "Jhalokathi",
        "Patuakhali",
        "Pirojpur",
    ],
    "Chattogram": [
        "Bandarban",
        "Brahmanbaria",
        "Chandpur",
        "Chattogram",
        "Cumilla",
        "Cox's Bazar",
        "Feni",
        "Khagrachhari",
        "Lakshmipur",
        "Noakhali",
        "Rangamati",
    ],
    "Dhaka": [
        "Dhaka",
        "Faridpur",
        "Gazipur",
        "Gopalganj",
        "Kishoreganj",
        "Madaripur",
        "Manikganj",
        "Munshiganj",
        "Narayanganj",
        "Narsingdi",
        "Rajbari",
        "Shariatpur",
        "Tangail",
    ],
    "Khulna": [
        "Bagerhat",
        "Chuadanga",
        "Jashore",
        "Jhenaidah",
        "Khulna",
        "Kushtia",
        "Magura",
        "Meherpur",
        "Narail",
        "Satkhira",
    ],
    "Mymensingh": [
        "Jamalpur",
        "Mymensingh",
        "Netrokona",
        "Sherpur",
    ],
    "Rajshahi": [
        "Bogura",
        "Joypurhat",
        "Naogaon",
        "Natore",
        "Chapainawabganj",
        "Pabna",
        "Rajshahi",
        "Sirajganj",
    ],
    "Rangpur": [
        "Dinajpur",
        "Gaibandha",
        "Kurigram",
        "Lalmonirhat",
        "Nilphamari",
        "Panchagarh",
        "Rangpur",
        "Thakurgaon",
    ],
    "Sylhet": [
        "Habiganj",
        "Moulvibazar",
        "Sunamganj",
        "Sylhet",
    ],
}


class Command(BaseCommand):
    help = "Seed the 64 Bangladesh districts under the correct divisions."

    @transaction.atomic
    def handle(self, *args, **options):
        country = Country.objects.get(code="BD")
        level = LocationLevel.objects.get(
            country=country,
            code="DISTRICT",
        )

        created = 0
        updated = 0

        for division_name, districts in DISTRICTS.items():
            division = AdministrativeLocation.objects.get(
                country=country,
                level__code="DIVISION",
                name=division_name,
            )

            for sort_order, district_name in enumerate(districts, start=1):
                location, was_created = AdministrativeLocation.objects.update_or_create(
                    country=country,
                    level=level,
                    parent=division,
                    name=district_name,
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
                f"Bangladesh district seed completed. Created: {created}, Updated: {updated}"
            )
        )
