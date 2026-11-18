from django.db import migrations


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


def seed_animations(apps, schema_editor):
    AnimationRegistry = apps.get_model("core", "AnimationRegistry")
    database = schema_editor.connection.alias

    for animation_id, label, engine, category, duration in ANIMATIONS:
        AnimationRegistry.objects.using(database).get_or_create(
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


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0048_animationregistry"),
    ]

    operations = [
        migrations.RunPython(
            seed_animations,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
