from django.core.management.base import BaseCommand
from django.db import transaction
import pycountry_convert as pc

from companies.models import Country, Region


CONTINENT_TO_REGION = {
    "AF": "Africa",
    "NA": "Americas",
    "SA": "Americas",
    "AS": "Asia",
    "EU": "Europe",
    "OC": "Oceania",
    "AN": "Oceania",
}


class Command(BaseCommand):
    help = "Assign all countries to their standard geographic regions."

    @transaction.atomic
    def handle(self, *args, **options):
        regions = {
            region.name: region
            for region in Region.objects.filter(
                name__in={
                    "Africa",
                    "Americas",
                    "Asia",
                    "Europe",
                    "Oceania",
                }
            )
        }

        updated = 0
        skipped = []

        for country in Country.objects.all().order_by("code"):
            try:
                continent = pc.country_alpha2_to_continent_code(country.code)
                region_name = CONTINENT_TO_REGION.get(continent)
            except Exception:
                region_name = None

            if not region_name or region_name not in regions:
                skipped.append(country.code)
                continue

            region = regions[region_name]

            if country.region_id != region.id:
                country.region = region
                country.save(update_fields=["region", "updated_at"])
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Country region assignment completed. Updated: {updated}, Skipped: {len(skipped)}"
            )
        )

        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Countries without region mapping: {', '.join(skipped)}"
                )
            )
