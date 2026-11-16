from core.models import AnimationRegistry


ANIMATION_ENGINES = {"native", "motion", "gsap"}

ANIMATION_CATEGORIES = {
    "basic",
    "transform",
    "directional",
    "advanced",
    "special",
}


def register_animation(
    animation_id,
    label,
    engine,
    category,
    default_duration=220,
    default_easing="ease-out",
    active=True,
    description="",
):
    animation_id = animation_id.strip().lower()

    if not animation_id:
        raise ValueError("Animation ID is required.")

    if engine not in ANIMATION_ENGINES:
        raise ValueError("Unsupported animation engine.")

    if category not in ANIMATION_CATEGORIES:
        raise ValueError("Unsupported animation category.")

    if not isinstance(default_duration, int) or not 0 <= default_duration <= 2000:
        raise ValueError("Invalid default animation duration.")

    animation, _ = AnimationRegistry.objects.update_or_create(
        id=animation_id,
        defaults={
            "label": label,
            "engine": engine,
            "category": category,
            "default_duration": default_duration,
            "default_easing": default_easing,
            "active": active,
            "description": description,
        },
    )

    return animation_to_dict(animation)


def animation_to_dict(animation):
    return {
        "id": animation.id,
        "label": animation.label,
        "engine": animation.engine,
        "category": animation.category,
        "default_duration": animation.default_duration,
        "default_easing": animation.default_easing,
        "active": animation.active,
        "description": animation.description,
    }


def get_animation(animation_id):
    animation = AnimationRegistry.objects.filter(pk=animation_id).first()
    return animation_to_dict(animation) if animation else None


def get_all_animations(active_only=False):
    queryset = AnimationRegistry.objects.all()

    if active_only:
        queryset = queryset.filter(active=True)

    return [
        animation_to_dict(animation)
        for animation in queryset
    ]


def get_animation_ids(active_only=True):
    queryset = AnimationRegistry.objects.all()

    if active_only:
        queryset = queryset.filter(active=True)

    return set(queryset.values_list("id", flat=True))


def update_animation_status(animation_id, active):
    updated = AnimationRegistry.objects.filter(pk=animation_id).update(
        active=bool(active)
    )

    if not updated:
        raise KeyError(f"Unknown animation: {animation_id}")
