from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


RAJSHAHI_UPAZILAS = {
    "Bogura": [
        "Adamdighi",
        "Bogura Sadar",
        "Dhunat",
        "Dhupchanchia",
        "Gabtali",
        "Kahaloo",
        "Nandigram",
        "Sariakandi",
        "Shajahanpur",
        "Sherpur",
        "Shibganj",
        "Sonatala",
    ],
    "Joypurhat": [
        "Akkelpur",
        "Joypurhat Sadar",
        "Kalai",
        "Khetlal",
        "Panchbibi",
    ],
    "Naogaon": [
        "Atrai",
        "Badalgachhi",
        "Dhamoirhat",
        "Manda",
        "Mahadevpur",
        "Naogaon Sadar",
        "Niamatpur",
        "Patnitala",
        "Porsha",
        "Raninagar",
        "Sapahar",
    ],
    "Natore": [
        "Bagatipara",
        "Baraigram",
        "Gurudaspur",
        "Lalpur",
        "Natore Sadar",
        "Singra",
    ],
    "Chapainawabganj": [
        "Bholahat",
        "Gomastapur",
        "Nachole",
        "Chapainawabganj Sadar",
        "Shibganj",
    ],
    "Pabna": [
        "Atgharia",
        "Bera",
        "Bhangura",
        "Chatmohar",
        "Faridpur",
        "Ishwardi",
        "Pabna Sadar",
        "Santhia",
        "Sujanagar",
    ],
    "Rajshahi": [
        "Bagha",
        "Bagmara",
        "Charghat",
        "Durgapur",
        "Godagari",
        "Mohanpur",
        "Paba",
        "Putia",
        "Tanore",
        "Rajshahi Sadar",
    ],
    "Sirajganj": [
        "Belkuchi",
        "Chauhali",
        "Kamarkhanda",
        "Kazipur",
        "Raiganj",
        "Shahjadpur",
        "Sirajganj Sadar",
        "Tarash",
        "Ullapara",
    ],
}


class Command(BaseCommand):
    help = "Seed Rajshahi Division upazilas."

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
            name="Rajshahi",
        )

        created = 0
        updated = 0

        for district_name, upazilas in RAJSHAHI_UPAZILAS.items():
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
                f"Rajshahi Upazila seed completed. "
                f"Created: {created}, Updated: {updated}"
            )
        )
