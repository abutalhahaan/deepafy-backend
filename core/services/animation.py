from django.core.exceptions import ValidationError


DEFAULT_ANIMATION_SETTINGS = {
    "enabled": True,
    "preset": "scale",
    "duration": 180,
    "easing": "ease-out",
    "intensity": 1,
}

ALLOWED_COMPONENT_TYPES = {
    "button", "popup", "tab", "dropdown", "modal", "card", "menu", "menu_button",
}

from core.animation_registry.registry import get_animation_ids


ALLOWED_EASINGS = {
    "linear", "ease", "ease-in",
    "ease-out", "ease-in-out", "spring",
}

ALLOWED_SETTINGS_FIELDS = {
    "enabled", "preset", "duration", "easing", "intensity",
}


def validate_animation_settings(settings):
    if not isinstance(settings, dict):
        raise ValidationError("Animation settings must be an object.")

    unknown_fields = set(settings) - ALLOWED_SETTINGS_FIELDS
    if unknown_fields:
        raise ValidationError(
            f"Unknown animation settings: {sorted(unknown_fields)}"
        )

    validated = dict(settings)

    if "enabled" in validated and not isinstance(validated["enabled"], bool):
        raise ValidationError("enabled must be a boolean.")

    if "preset" in validated and validated["preset"] not in get_animation_ids(active_only=True):
        raise ValidationError("Invalid animation preset.")

    if "duration" in validated:
        value = validated["duration"]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError("duration must be an integer.")
        if not 0 <= value <= 2000:
            raise ValidationError("duration must be between 0 and 2000.")

    if "easing" in validated and validated["easing"] not in ALLOWED_EASINGS:
        raise ValidationError("Invalid animation easing.")

    if "intensity" in validated:
        value = validated["intensity"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError("intensity must be a number.")
        if not 0 <= value <= 2:
            raise ValidationError("intensity must be between 0 and 2.")

    return validated


def validate_component_overrides(overrides):
    if not isinstance(overrides, list):
        raise ValidationError("component_overrides must be a list.")

    validated = []

    for item in overrides:
        if not isinstance(item, dict):
            raise ValidationError("Each component override must be an object.")

        if set(item) - {"componentType", "componentId", "settings"}:
            raise ValidationError("Unknown component override field.")

        component_type = item.get("componentType")
        if component_type not in ALLOWED_COMPONENT_TYPES:
            raise ValidationError("Invalid animation component type.")

        component_id = item.get("componentId")
        if component_id is not None:
            if not isinstance(component_id, str) or not component_id.strip():
                raise ValidationError("componentId must be a non-empty string.")
            if len(component_id) > 255:
                raise ValidationError("componentId cannot exceed 255 characters.")

        if "settings" not in item:
            raise ValidationError("Component override settings are required.")

        validated.append({
            "componentType": component_type,
            **({"componentId": component_id} if component_id is not None else {}),
            "settings": validate_animation_settings(item["settings"]),
        })

    return validated


def resolve_animation_settings(
    global_default=None,
    account_default=None,
    user_preference=None,
    component_type=None,
    component_id=None,
    user_customization_enabled=False,
):
    resolved = dict(DEFAULT_ANIMATION_SETTINGS)

    resolved.update(validate_animation_settings(global_default or {}))
    resolved.update(validate_animation_settings(account_default or {}))

    if user_customization_enabled and user_preference:
        if not isinstance(user_preference, dict):
            raise ValidationError("User preference must be an object.")

        resolved.update(
            validate_animation_settings(
                user_preference.get("global_override", {})
            )
        )

        overrides = validate_component_overrides(
            user_preference.get("component_overrides", [])
        )

        if component_type:
            if component_type not in ALLOWED_COMPONENT_TYPES:
                raise ValidationError("Invalid animation component type.")

            for item in overrides:
                if (
                    item["componentType"] == component_type
                    and "componentId" not in item
                ):
                    resolved.update(item["settings"])

            if component_id is not None:
                for item in overrides:
                    if (
                        item["componentType"] == component_type
                        and item.get("componentId") == component_id
                    ):
                        resolved.update(item["settings"])

    return resolved
