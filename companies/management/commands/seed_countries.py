from django.core.management.base import BaseCommand
from django.db import transaction
import phonenumbers
import pycountry

from companies.models import Country, Region


def get_phone_code(alpha2):
    try:
        regions = phonenumbers.region_codes_for_country_code(
            phonenumbers.country_code_for_region(alpha2)
        )
        if alpha2 in regions:
            code = phonenumbers.country_code_for_region(alpha2)
            return f"+{code}"
    except Exception:
        pass
    return ""


def get_flag_emoji(alpha2):
    if len(alpha2) != 2:
        return ""
    return "".join(
        chr(127397 + ord(char))
        for char in alpha2.upper()
    )


class Command(BaseCommand):
    help = "Seed or update all countries with ISO codes, phone codes and flag emojis."

    @transaction.atomic
    def handle(self, *args, **options):
        region, _ = Region.objects.get_or_create(
            name="Global",
            defaults={
                "is_active": True,
            },
        )

        created = 0
        updated = 0

        for country in pycountry.countries:
            code = country.alpha_2
            name = country.name
            phone_code = get_phone_code(code)
            flag_emoji = get_flag_emoji(code)

            obj, was_created = Country.objects.update_or_create(
                code=code,
                defaults={
                    "region": region,
                    "name": name,
                    "phone_code": phone_code,
                    "flag_emoji": flag_emoji,
                    "is_active": True,
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Country seed completed. Created: {created}, Updated: {updated}"
            )
        )
