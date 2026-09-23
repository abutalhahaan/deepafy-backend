import re

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import (
    AdministrativeLocation,
    Country,
    LocationLevel,
)


DISTRICT_URL = "https://bangladesh.gov.bd/views/district-list/"
UPAZILA_URL = "https://bangladesh.gov.bd/views/upazila-list/%E0%A6%89%E0%A6%AA%E0%A6%9C%E0%A7%87%E0%A6%B2%E0%A6%BE-%E0%A6%B8%E0%A6%AE%E0%A7%82%E0%A6%B9/"


class Command(BaseCommand):
    help = "Seed Bangladesh Division, District and Upazila data."

    def fetch_page(self, url):
        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/153.0 Safari/537.36"
                )
            },
        )

        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return BeautifulSoup(response.text, "html.parser")

    def clean_name(self, value):
        value = re.sub(r"\s+", " ", value or "")
        value = value.strip()

        suffixes = [
            " উপজেলা",
            " জেলা",
        ]

        for suffix in suffixes:
            if value.endswith(suffix):
                value = value[: -len(suffix)].strip()

        return value

    def get_tables(self, soup):
        return soup.find_all("table")

    def parse_districts(self, soup):
        divisions = {}

        for table in self.get_tables(soup):
            current_division = None

            for row in table.find_all("tr"):
                cells = row.find_all(["th", "td"])

                if len(cells) < 2:
                    continue

                division = self.clean_name(cells[0].get_text(" ", strip=True))
                district = self.clean_name(cells[1].get_text(" ", strip=True))

                if not division or not district:
                    continue

                if division in {
                    "বিভাগ",
                    "Division",
                }:
                    continue

                current_division = division

                divisions.setdefault(
                    current_division,
                    [],
                )

                if district not in divisions[current_division]:
                    divisions[current_division].append(district)

        return divisions

    def parse_upazilas(self, soup):
        data = {}

        current_division = None
        current_district = None

        for table in self.get_tables(soup):
            for row in table.find_all("tr"):
                cells = row.find_all(["th", "td"])

                if len(cells) < 2:
                    continue

                first = self.clean_name(
                    cells[0].get_text(" ", strip=True)
                )
                second = self.clean_name(
                    cells[1].get_text(" ", strip=True)
                )

                if not first or not second:
                    continue

                if first == "বিভাগ":
                    continue

                if first in {
                    "ঢাকা বিভাগ",
                    "চট্টগ্রাম বিভাগ",
                    "খুলনা বিভাগ",
                    "রাজশাহী বিভাগ",
                    "সিলেট বিভাগ",
                    "রংপুর বিভাগ",
                    "ময়মনসিংহ বিভাগ",
                    "বরিশাল বিভাগ",
                }:
                    current_division = first.replace(
                        " বিভাগ",
                        "",
                    )
                    continue

                if second == "উপজেলা":
                    continue

                current_district = first

                data.setdefault(
                    current_division,
                    {},
                )

                data[current_division].setdefault(
                    current_district,
                    [],
                )

                if second not in data[current_division][current_district]:
                    data[current_division][current_district].append(
                        second
                    )

        return data

    def get_level_map(self, country):
        return {
            level.level: level
            for level in LocationLevel.objects.filter(
                country=country,
                is_active=True,
            )
        }

    @transaction.atomic
    def handle(self, *args, **options):
        country = Country.objects.filter(
            code__iexact="BD",
            is_active=True,
        ).first()

        if not country:
            self.stdout.write(
                self.style.ERROR(
                    "Bangladesh country record was not found."
                )
            )
            return

        levels = self.get_level_map(country)

        required_levels = [1, 2, 3]

        missing = [
            level
            for level in required_levels
            if level not in levels
        ]

        if missing:
            self.stdout.write(
                self.style.ERROR(
                    f"Missing LocationLevel(s): {missing}"
                )
            )
            return

        self.stdout.write(
            "Downloading Bangladesh administrative data..."
        )

        try:
            district_soup = self.fetch_page(DISTRICT_URL)
            upazila_soup = self.fetch_page(UPAZILA_URL)
        except requests.RequestException as exc:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to download official data: {exc}"
                )
            )
            return

        districts_by_division = self.parse_districts(
            district_soup
        )

        upazilas_by_division = self.parse_upazilas(
            upazila_soup
        )

        created = 0
        updated = 0

        for division_name, district_names in districts_by_division.items():
            division, was_created = (
                AdministrativeLocation.objects.update_or_create(
                    country=country,
                    level=levels[1],
                    parent=None,
                    name=division_name,
                    defaults={
                        "is_active": True,
                        "sort_order": 0,
                    },
                )
            )

            if was_created:
                created += 1
            else:
                updated += 1

            division_upazilas = upazilas_by_division.get(
                division_name,
                {},
            )

            for district_name in district_names:
                district, was_created = (
                    AdministrativeLocation.objects.update_or_create(
                        country=country,
                        level=levels[2],
                        parent=division,
                        name=district_name,
                        defaults={
                            "is_active": True,
                            "sort_order": 0,
                        },
                    )
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

                upazila_names = division_upazilas.get(
                    district_name,
                    [],
                )

                for upazila_name in upazila_names:
                    _, was_created = (
                        AdministrativeLocation.objects.update_or_create(
                            country=country,
                            level=levels[3],
                            parent=district,
                            name=upazila_name,
                            defaults={
                                "is_active": True,
                                "sort_order": 0,
                            },
                        )
                    )

                    if was_created:
                        created += 1
                    else:
                        updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Bangladesh administrative locations "
                "seed completed. "
                f"Created: {created}, Updated: {updated}"
            )
        )