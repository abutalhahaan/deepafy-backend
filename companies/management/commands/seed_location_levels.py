from django.core.management.base import BaseCommand
from companies.models import Country, LocationLevel


LOCATION_LEVELS = {
    "BD": [
        (1, "Division", "DIVISION"),
        (2, "District", "DISTRICT"),
        (3, "Upazila", "UPAZILA"),
    ],
    "IN": [
        (1, "State", "STATE"),
        (2, "District", "DISTRICT"),
        (3, "Subdistrict", "SUBDISTRICT"),
    ],
    "PK": [
        (1, "Province", "PROVINCE"),
        (2, "Division", "DIVISION"),
        (3, "District", "DISTRICT"),
        (4, "Tehsil", "TEHSIL"),
    ],
    "NP": [
        (1, "Province", "PROVINCE"),
        (2, "District", "DISTRICT"),
        (3, "Municipality", "MUNICIPALITY"),
    ],
    "LK": [
        (1, "Province", "PROVINCE"),
        (2, "District", "DISTRICT"),
        (3, "Divisional Secretariat", "DIVISIONAL_SECRETARIAT"),
    ],
    "AE": [
        (1, "Emirate", "EMIRATE"),
        (2, "Municipality", "MUNICIPALITY"),
    ],
    "SA": [
        (1, "Province", "PROVINCE"),
        (2, "Governorate", "GOVERNORATE"),
    ],
    "QA": [
        (1, "Municipality", "MUNICIPALITY"),
        (2, "Zone", "ZONE"),
    ],
    "KW": [
        (1, "Governorate", "GOVERNORATE"),
        (2, "Area", "AREA"),
    ],
    "OM": [
        (1, "Governorate", "GOVERNORATE"),
        (2, "Wilayat", "WILAYAT"),
    ],
    "BH": [
        (1, "Governorate", "GOVERNORATE"),
        (2, "Municipality", "MUNICIPALITY"),
    ],
    "MY": [
        (1, "State", "STATE"),
        (2, "District", "DISTRICT"),
    ],
    "ID": [
        (1, "Province", "PROVINCE"),
        (2, "Regency/City", "REGENCY_CITY"),
        (3, "District", "DISTRICT"),
    ],
    "VN": [
        (1, "Province", "PROVINCE"),
        (2, "District", "DISTRICT"),
    ],
    "TH": [
        (1, "Province", "PROVINCE"),
        (2, "District", "DISTRICT"),
        (3, "Subdistrict", "SUBDISTRICT"),
    ],
    "PH": [
        (1, "Province", "PROVINCE"),
        (2, "City/Municipality", "CITY_MUNICIPALITY"),
        (3, "Barangay", "BARANGAY"),
    ],
    "CN": [
        (1, "Province", "PROVINCE"),
        (2, "Prefecture", "PREFECTURE"),
        (3, "County", "COUNTY"),
    ],
    "JP": [
        (1, "Prefecture", "PREFECTURE"),
        (2, "Municipality", "MUNICIPALITY"),
    ],
    "KR": [
        (1, "Province/Special City", "PROVINCE_SPECIAL_CITY"),
        (2, "City/County/District", "CITY_COUNTY_DISTRICT"),
    ],
    "US": [
        (1, "State", "STATE"),
        (2, "County", "COUNTY"),
    ],
    "CA": [
        (1, "Province/Territory", "PROVINCE_TERRITORY"),
        (2, "Census Division", "CENSUS_DIVISION"),
    ],
    "AU": [
        (1, "State/Territory", "STATE_TERRITORY"),
        (2, "Local Government Area", "LOCAL_GOVERNMENT_AREA"),
    ],
    "DE": [
        (1, "State", "STATE"),
        (2, "District", "DISTRICT"),
    ],
    "FR": [
        (1, "Region", "REGION"),
        (2, "Department", "DEPARTMENT"),
    ],
    "IT": [
        (1, "Region", "REGION"),
        (2, "Province", "PROVINCE"),
    ],
    "ES": [
        (1, "Autonomous Community", "AUTONOMOUS_COMMUNITY"),
        (2, "Province", "PROVINCE"),
    ],
    "BR": [
        (1, "State", "STATE"),
        (2, "Municipality", "MUNICIPALITY"),
    ],
    "MX": [
        (1, "State", "STATE"),
        (2, "Municipality", "MUNICIPALITY"),
    ],
    "ZA": [
        (1, "Province", "PROVINCE"),
        (2, "District Municipality", "DISTRICT_MUNICIPALITY"),
        (3, "Local Municipality", "LOCAL_MUNICIPALITY"),
    ],
}


class Command(BaseCommand):
    help = "Seed country-specific administrative location levels."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        skipped = 0

        countries = {
            country.code.upper(): country
            for country in Country.objects.all()
        }

        for country_code, levels in LOCATION_LEVELS.items():
            country = countries.get(country_code)

            if not country:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Country not found: {country_code}"
                    )
                )
                continue

            for level_number, name, code in levels:
                _, was_created = LocationLevel.objects.update_or_create(
                    country=country,
                    level=level_number,
                    defaults={
                        "name": name,
                        "code": code,
                        "is_active": True,
                        "sort_order": level_number,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Location level seed completed. "
                f"Created: {created}, Updated: {updated}, "
                f"Skipped countries: {skipped}"
            )
        )
