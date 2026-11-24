from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from identity.models import UserIdentity

from .trusted_location import verify_trusted_location
from .trusted_location_verification import issue_trusted_location_verification

from .models import (
    SecurityProfile,
    SecurityPreference,
    TrustedLocation,
)


def get_security_records(identity):
    profile, _ = SecurityProfile.objects.get_or_create(
        identity=identity,
    )
    preference, _ = SecurityPreference.objects.get_or_create(
        profile=profile,
    )
    return profile, preference


def sync_trusted_location_security(profile, preference):
    locations = TrustedLocation.objects.filter(profile=profile)
    has_enabled_locations = locations.filter(is_active=True).exists()

    if has_enabled_locations:
        preference.trusted_location_enabled = True
        preference.trusted_location_pending = False
    elif not preference.trusted_location_pending:
        preference.trusted_location_enabled = False

    preference.trusted_location_enabled_since = None
    preference.save(update_fields=[
        "trusted_location_enabled",
        "trusted_location_pending",
        "trusted_location_enabled_since",
        "updated_at",
    ])

    return has_enabled_locations


def serialize_trusted_location(location):
    return {
        "id": location.id,
        "name": location.name,
        "map_url": location.map_url,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracy_meters": location.accuracy_meters,
        "radius_km": location.radius_meters // 1000,
        "is_enabled": location.is_active,
        "created_at": location.created_at,
        "updated_at": location.updated_at,
    }


def validate_location_data(data, existing=None):
    existing = existing or {}

    name = data.get("name", existing.get("name"))
    latitude = data.get("latitude", existing.get("latitude"))
    longitude = data.get("longitude", existing.get("longitude"))
    radius_km = data.get("radius_km", existing.get("radius_km"))
    radius_meters = data.get("radius_meters", existing.get("radius_meters"))
    map_url = data.get("map_url", existing.get("map_url", ""))
    accuracy = data.get("accuracy_meters", existing.get("accuracy_meters"))

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Location name is required.")

    name = name.strip()
    if len(name) > 100:
        raise ValueError("Location name cannot exceed 100 characters.")

    try:
        latitude = TrustedLocation._meta.get_field("latitude").clean(
            Decimal(str(latitude)), None
        )
        longitude = TrustedLocation._meta.get_field("longitude").clean(
            Decimal(str(longitude)), None
        )
        if radius_km is not None:
            if isinstance(radius_km, bool):
                raise ValueError
            radius_km = Decimal(str(radius_km))
            if radius_km not in (Decimal("5"), Decimal("10"), Decimal("20"), Decimal("50"), Decimal("100")):
                raise ValueError
            radius_meters = int(radius_km * 1000)
        radius_meters = TrustedLocation._meta.get_field("radius_meters").clean(
            radius_meters, None
        )
        map_url = TrustedLocation._meta.get_field("map_url").clean(map_url, None)
        if accuracy in ("", None):
            accuracy = None
        else:
            accuracy = TrustedLocation._meta.get_field("accuracy_meters").clean(
                accuracy, None
            )
    except (ValidationError, TypeError, ValueError, InvalidOperation):
        raise ValueError("Invalid coordinates or radius.")

    return {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "radius_meters": radius_meters,
        "map_url": map_url,
        "accuracy_meters": accuracy,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def trusted_location_list_create(request):
    profile, _ = get_security_records(request.user)

    if request.method == "GET":
        locations = TrustedLocation.objects.filter(
            profile=profile,
        ).order_by("-created_at")

        results = [serialize_trusted_location(item) for item in locations]
        return Response({"count": len(results), "locations": results})

    try:
        values = validate_location_data(request.data)
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    location = TrustedLocation.objects.create(
        profile=profile,
        **values,
    )
    _, preference = get_security_records(request.user)
    sync_trusted_location_security(profile, preference)

    return Response(
        {
            "message": "Trusted location created.",
            "location": serialize_trusted_location(location),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def trusted_location_detail(request, location_id):
    profile, _ = get_security_records(request.user)

    location = get_object_or_404(
        TrustedLocation,
        id=location_id,
        profile=profile,
    )

    if request.method == "DELETE":
        location.delete()
        _, preference = get_security_records(request.user)
        sync_trusted_location_security(profile, preference)
        return Response(
            {"message": "Trusted location deleted."},
            status=status.HTTP_200_OK,
        )

    allowed_fields = {
        "name",
        "map_url",
        "latitude",
        "longitude",
        "accuracy_meters",
        "radius_km",
        "radius_meters",
        "is_enabled",
    }

    if not isinstance(request.data, dict):
        return Response(
            {"detail": "Invalid request data."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not request.data or set(request.data.keys()) - allowed_fields:
        return Response(
            {"detail": "Invalid or unsupported fields."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        values = validate_location_data(
            request.data,
            existing={
                "name": location.name,
                "map_url": location.map_url,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "accuracy_meters": location.accuracy_meters,
                "radius_km": location.radius_meters // 1000,
                "radius_meters": location.radius_meters,
            },
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "is_enabled" in request.data:
        if not isinstance(request.data["is_enabled"], bool):
            return Response(
                {"detail": "is_enabled must be true or false."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        location.is_active = request.data["is_enabled"]

    for field, value in values.items():
        setattr(location, field, value)

    location.save()
    _, preference = get_security_records(request.user)
    sync_trusted_location_security(profile, preference)

    return Response({
        "message": "Trusted location updated.",
        "location": serialize_trusted_location(location),
    })


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def trusted_location_settings(request):
    profile, preference = get_security_records(request.user)

    if request.method == "GET":
        return Response({
            "restriction_enabled": preference.trusted_location_enabled,
            "trusted_location_pending": preference.trusted_location_pending,
            "has_enabled_locations": TrustedLocation.objects.filter(
                profile=profile, is_active=True
            ).exists(),
            "created_at": preference.created_at,
            "updated_at": preference.updated_at,
        })

    if (
        not isinstance(request.data, dict)
        or set(request.data.keys()) != {"restriction_enabled"}
        or not isinstance(request.data.get("restriction_enabled"), bool)
    ):
        return Response(
            {
                "detail": (
                    "Provide restriction_enabled as true or false."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    enabled = request.data["restriction_enabled"]

    if enabled:
        has_enabled_locations = TrustedLocation.objects.filter(
            profile=profile,
            is_active=True,
        ).exists()

        preference.trusted_location_enabled = True
        preference.trusted_location_pending = not has_enabled_locations
    else:
        TrustedLocation.objects.filter(
            profile=profile,
            is_active=True,
        ).update(is_active=False)
        preference.trusted_location_enabled = False
        preference.trusted_location_pending = False

    preference.trusted_location_enabled_since = None
    preference.save(update_fields=[
        "trusted_location_enabled",
        "trusted_location_pending",
        "trusted_location_enabled_since",
        "updated_at",
    ])

    return Response({
        "message": "Trusted location setting updated.",
        "restriction_enabled": preference.trusted_location_enabled,
        "trusted_location_pending": preference.trusted_location_pending,
        "has_enabled_locations": TrustedLocation.objects.filter(
            profile=profile, is_active=True
        ).exists(),
        "created_at": preference.created_at,
        "updated_at": preference.updated_at,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_trusted_location_pending(request):
    profile, preference = get_security_records(request.user)

    if not preference.trusted_location_pending:
        return Response({
            "message": "No pending trusted location restriction.",
            "restriction_enabled": preference.trusted_location_enabled,
        })

    has_enabled_locations = TrustedLocation.objects.filter(
        profile=profile,
        is_active=True,
    ).exists()

    if has_enabled_locations:
        preference.trusted_location_pending = False
        preference.trusted_location_enabled = True
        preference.save(update_fields=[
            "trusted_location_pending",
            "trusted_location_enabled",
            "updated_at",
        ])
    else:
        preference.trusted_location_pending = False
        preference.trusted_location_enabled = False
        preference.save(update_fields=[
            "trusted_location_pending",
            "trusted_location_enabled",
            "updated_at",
        ])

    return Response({
        "message": "Pending trusted location restriction cancelled.",
        "restriction_enabled": preference.trusted_location_enabled,
        "trusted_location_pending": preference.trusted_location_pending,
        "has_enabled_locations": has_enabled_locations,
    })


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_login_location(request):
    identifier = request.data.get("identifier")

    if not isinstance(identifier, str) or not identifier.strip():
        return Response(
            {"verified": False, "detail": "Invalid verification request."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    identifier = identifier.strip()

    identity = (
        UserIdentity.objects.filter(username=identifier).first()
        or UserIdentity.objects.filter(email=identifier).first()
        or UserIdentity.objects.filter(mobile_number=identifier).first()
    )

    if identity is None:
        return Response(
            {"verified": False, "detail": "Location verification failed."},
            status=status.HTTP_403_FORBIDDEN,
        )

    profile, preference = get_security_records(identity)

    if not preference.trusted_location_enabled:
        return Response({
            "verified": True,
            "restriction_enabled": False,
            "verification_token": None,
        })

    result = verify_trusted_location(
        identity,
        request.data.get("latitude"),
        request.data.get("longitude"),
        request.data.get("accuracy_meters"),
    )

    if not result["verified"]:
        return Response(
            {
                "verified": False,
                "restriction_enabled": True,
                "detail": "Trusted location verification failed.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    token = issue_trusted_location_verification(identity)

    return Response({
        "verified": True,
        "restriction_enabled": True,
        "verification_token": token,
        "expires_in": 90,
    })
