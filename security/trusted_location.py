import math
from decimal import Decimal, InvalidOperation

from .models import TrustedLocation, SecurityProfile


MAX_GPS_ACCURACY_METERS = 1000
EARTH_RADIUS_METERS = 6_371_000


def validate_gps_coordinates(latitude, longitude, accuracy_meters):
    try:
        if any(isinstance(value, bool) for value in (
            latitude, longitude, accuracy_meters
        )):
            return False

        latitude = Decimal(str(latitude))
        longitude = Decimal(str(longitude))
        accuracy_meters = Decimal(str(accuracy_meters))

    except (InvalidOperation, TypeError, ValueError):
        return False

    if not all(value.is_finite() for value in (
        latitude, longitude, accuracy_meters
    )):
        return False

    return (
        Decimal("-90") <= latitude <= Decimal("90")
        and Decimal("-180") <= longitude <= Decimal("180")
        and Decimal("0") < accuracy_meters
        <= Decimal(str(MAX_GPS_ACCURACY_METERS))
    )


def calculate_distance_meters(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(
        math.radians,
        map(float, (lat1, lon1, lat2, lon2)),
    )

    delta_latitude = lat2 - lat1
    delta_longitude = lon2 - lon1

    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_longitude / 2) ** 2
    )

    central_angle = 2 * math.atan2(
        math.sqrt(haversine),
        math.sqrt(1 - haversine),
    )

    return EARTH_RADIUS_METERS * central_angle


def verify_trusted_location(identity, latitude, longitude, accuracy_meters):
    if not validate_gps_coordinates(
        latitude, longitude, accuracy_meters
    ):
        return {
            "verified": False,
            "reason": "invalid_or_unavailable_gps",
        }

    profile = SecurityProfile.objects.filter(
        identity=identity
    ).first()

    if profile is None:
        return {
            "verified": False,
            "reason": "security_profile_not_found",
        }

    locations = TrustedLocation.objects.filter(
        profile=profile,
        is_active=True,
    )

    if not locations.exists():
        return {
            "verified": False,
            "reason": "no_enabled_trusted_locations",
        }

    accuracy_meters = float(accuracy_meters)

    for location in locations:
        distance_meters = calculate_distance_meters(
            latitude,
            longitude,
            location.latitude,
            location.longitude,
        )

        if (
            distance_meters + accuracy_meters
            <= location.radius_meters
        ):
            return {
                "verified": True,
                "reason": "trusted_location_match",
                "location_id": location.id,
            }

    return {
        "verified": False,
        "reason": "outside_trusted_locations",
    }
