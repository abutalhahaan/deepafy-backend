from django.core.management.base import BaseCommand

from core.models import AnimationRegistry


ANIMATIONS = [
    ("none", "None", "native", "basic", 0),
    ("fade", "Fade", "motion", "basic", 180),
    ("scale", "Scale", "motion", "transform", 180),
    ("zoom", "Zoom", "motion", "transform", 220),
    ("slide-up", "Slide Up", "motion", "directional", 220),
    ("slide-down", "Slide Down", "motion", "directional", 220),
    ("slide-left", "Slide Left", "motion", "directional", 220),
    ("slide-right", "Slide Right", "motion", "directional", 220),
    ("blur", "Blur", "motion", "advanced", 250),
    ("liquid", "Liquid", "gsap", "advanced", 350),
    ("genie", "Genie", "gsap", "special", 450),
    ("jitter", "Jitter", "gsap", "special", 320),
    ("raindrop", "Raindrop", "gsap", "special", 700),
]


class Command(BaseCommand):
    help = "Seed built-in animations into the animation registry."

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0

        for animation_id, label, engine, category, duration in ANIMATIONS:
            _, created = AnimationRegistry.objects.get_or_create(
                id=animation_id,
                defaults={
                    "label": label,
                    "engine": engine,
                    "category": category,
                    "default_duration": duration,
                    "default_easing": "ease-out",
                    "active": True,
                    "description": f"Built-in {label} animation.",
                },
            )

            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Animation seeding completed. "
                f"Created: {created_count}, Existing: {existing_count}"
            )
        )
