from django.core.management.base import BaseCommand

from core.models import AnimationRegistry


ANIMATIONS = [
    ("none", "None", "native", "basic", 0),
    ("slide-down", "Slide Down", "motion", "directional", 220),
    ("slide-left", "Slide Left", "motion", "directional", 220),
    ("slide-right", "Slide Right", "motion", "directional", 220),
    ("slide-up", "Slide Up", "motion", "directional", 220),
    ("jitter", "Jitter", "gsap", "special", 320),
]


class Command(BaseCommand):
    help = "Seed built-in animations into the animation registry."

    def handle(self, *args, **options):
        active_ids = [item[0] for item in ANIMATIONS]

        deactivated_count = AnimationRegistry.objects.exclude(
            id__in=active_ids
        ).update(active=False)

        for animation_id, label, engine, category, duration in ANIMATIONS:
            AnimationRegistry.objects.update_or_create(
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Animation seeding completed. Active: {len(ANIMATIONS)}, "
                f"Deactivated: {deactivated_count}"
            )
        )
