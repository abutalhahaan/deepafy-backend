from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import AdministrativeLocation, Country, LocationLevel


UPAZILAS = {
    "Bandarban": [
        "Ali Kadam",
        "Bandarban Sadar",
        "Lama",
        "Naikhongchhari",
        "Rowangchhari",
        "Ruma",
        "Thanchi",
    ],
    "Brahmanbaria": [
        "Akhaura",
        "Ashuganj",
        "Banchharampur",
        "Bijoynagar",
        "Brahmanbaria Sadar",
        "Kasba",
        "Nabinagar",
        "Nasirnagar",
        "Sarail",
    ],
    "Chandpur": [
        "Chandpur Sadar",
        "Faridganj",
        "Haimchar",
        "Haziganj",
        "Kachua",
        "Matlab North",
        "Matlab South",
        "Shahrasti",
    ],
    "Chattogram": [
        "Anwara",
        "Banshkhali",
        "Boalkhali",
        "Chandanaish",
        "Fatikchhari",
        "Hathazari",
        "Lohagara",
        "Mirsharai",
        "Patiya",
        "Rangunia",
        "Raozan",
        "Sandwip",
        "Satkania",
        "Sitakunda",
    ],
    "Cumilla": [
        "Barura",
        "Brahmanpara",
        "Burichang",
        "Chandina",
        "Chauddagram",
        "Cumilla Adarsha Sadar",
        "Cumilla Sadar South",
        "Daudkandi",
        "Debidwar",
        "Homna",
        "Laksam",
        "Meghna",
        "Monohargonj",
        "Muradnagar",
        "Nangalkot",
        "Titas",
    ],
    "Cox's Bazar": [
        "Chakaria",
        "Cox's Bazar Sadar",
        "Eidgaon",
        "Kutubdia",
        "Maheshkhali",
        "Pekua",
        "Ramu",
        "Teknaf",
        "Ukhia",
    ],
    "Feni": [
        "Chhagalnaiya",
        "Daganbhuiyan",
        "Feni Sadar",
        "Fulgazi",
        "Parshuram",
        "Sonagazi",
    ],
    "Khagrachhari": [
        "Dighinala",
        "Khagrachhari Sadar",
        "Lakshmichhari",
        "Mahalchhari",
        "Manikchhari",
        "Matiranga",
        "Panchhari",
        "Ramgarh",
    ],
    "Lakshmipur": [
        "Kamalnagar",
        "Lakshmipur Sadar",
        "Raipur",
        "Ramganj",
        "Ramgati",
    ],
    "Noakhali": [
        "Begumganj",
        "Chatkhil",
        "Companiganj",
        "Hatiya",
        "Kabirhat",
        "Noakhali Sadar",
        "Senbagh",
        "Sonaimuri",
        "Subarnachar",
    ],
    "Rangamati": [
        "Baghaichhari",
        "Barkal",
        "Belaichhari",
        "Juraichhari",
        "Kaptai",
        "Kawkhali",
        "Langadu",
        "Naniarchar",
        "Rajasthali",
        "Rangamati Sadar",
    ],
}


class Command(BaseCommand):
    help = "Seed Chattogram Division Upazilas."

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
                f"Chattogram Upazila seed completed. Created: {created}, Updated: {updated}"
            )
        )
