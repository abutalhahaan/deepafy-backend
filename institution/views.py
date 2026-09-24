from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.services.feature_access import get_feature_access
from .models import InstitutionTypeGroup, InstitutionProfile


@api_view(["GET"])
def institution_type_list(request):
    groups = InstitutionTypeGroup.objects.filter(
        is_active=True
    ).prefetch_related("institution_types")

    data = []

    for group in groups:
        types = [
            {
                "id": institution_type.id,
                "name": institution_type.name,
            }
            for institution_type in group.institution_types.all()
            if institution_type.is_active
        ]

        if types:
            data.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "types": types,
                }
            )

    return Response(
        {
            "groups": data,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def institution_profile_by_username(request, username):
    from .models import InstitutionProfile

    try:
        profile = (
            InstitutionProfile.objects
            .select_related(
                "identity",
                "institution_type",
                "institution_type__group",
                "country",
                "administrative_location",
            )
            .get(
                identity__username=username,
                identity__is_active=True,
                is_active=True,
            )
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    location = profile.administrative_location

    location_hierarchy = []
    current_location = location

    while current_location:
        location_hierarchy.append({
            "id": str(current_location.location_id),
            "name": current_location.name,
            "level": current_location.level.level,
            "level_name": current_location.level.name,
        })
        current_location = current_location.parent

    return Response(
        {
            "user_id": str(profile.identity.user_id),
            "username": profile.identity.username,
            "institution_name": profile.institution_name,
            "institution_type": {
                "id": profile.institution_type.id,
                "name": profile.institution_type.name,
                "group": profile.institution_type.group.name,
            },
            "institution_types": [
                {
                    "id": item.id,
                    "name": item.name,
                    "group": item.group.name,
                }
                for item in profile.institution_types.select_related("group").all()
            ],
            "established_year": profile.established_year,
            "tagline": profile.tagline,
            "description": profile.description,
            "country": {
                "id": profile.country.id,
                "name": profile.country.name,
                "code": profile.country.code,
            },
            "administrative_location": (
                {
                    "id": str(location.location_id),
                    "name": location.name,
                    "level": location.level.level,
                    "level_name": location.level.name,
                }
                if location
                else None
            ),
            "location_hierarchy": location_hierarchy,
            "full_address": profile.full_address,
            "website": profile.website,
            "email": profile.email,
            "phone": profile.phone,
            "logo": request.build_absolute_uri(profile.logo.url)
            if profile.logo
            else None,
            "cover_photo": request.build_absolute_uri(profile.cover_photo.url)
            if profile.cover_photo
            else None,
            "background_color": profile.background_color,
            "background_image": (
                request.build_absolute_uri(profile.background_image.url)
                if profile.background_image
                else None
            ),
            "tab_colors": profile.tab_colors,
            "is_verified": profile.is_verified,
        }
    )


@api_view(["GET", "PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_appearance_update(request):
    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    if request.method == "GET":
        return Response({
            "background_color": profile.background_color,
            "background_image": (
                request.build_absolute_uri(profile.background_image.url)
                if profile.background_image
                else None
            ),
        })

    color_access = get_feature_access(
        request,
        "activity_background_color",
    )

    image_access = get_feature_access(
        request,
        "activity_wallpaper",
    )

    background_color = request.data.get("background_color")

    if background_color is not None:
        if color_access["access"] not in ["free", "premium", "trial"]:
            return Response(
                {"detail": "Premium access required for Background Color."},
                status=403,
            )

        profile.background_color = background_color

    if "background_image" in request.FILES:
        if image_access["access"] not in ["free", "premium", "trial"]:
            return Response(
                {"detail": "Premium access required for Background Image."},
                status=403,
            )

        profile.background_image = request.FILES["background_image"]

    update_fields = [
        "background_color",
        "background_image",
    ]

    if "cover_photo" in request.FILES:
        profile.cover_photo = request.FILES["cover_photo"]
        update_fields.append("cover_photo")

    if "logo" in request.FILES:
        profile.logo = request.FILES["logo"]
        update_fields.append("logo")

    profile.save(update_fields=update_fields)

    return Response({
        "background_color": profile.background_color,
        "background_image": (
            request.build_absolute_uri(profile.background_image.url)
            if profile.background_image
            else None
        ),
        "cover_photo": (
            request.build_absolute_uri(profile.cover_photo.url)
            if profile.cover_photo
            else None
        ),
        "logo": (
            request.build_absolute_uri(profile.logo.url)
            if profile.logo
            else None
        ),
    })


@api_view(["PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_profile_update(request):
    try:
        profile = InstitutionProfile.objects.get(
            identity=request.user,
            is_active=True,
        )
    except InstitutionProfile.DoesNotExist:
        return Response(
            {"detail": "Institution profile not found."},
            status=404,
        )

    fields = [
        "institution_name",
        "established_year",
        "tagline",
        "description",
        "full_address",
        "website",
        "email",
        "phone",
    ]

    for field in fields:
        if field in request.data:
            setattr(profile, field, request.data.get(field))

    if "institution_types" in request.data:
        values = request.data.get("institution_types")

        if not isinstance(values, list):
            return Response(
                {"detail": "Institution types must be a list."},
                status=400,
            )

        try:
            type_ids = [int(value) for value in values if value not in [None, ""]]
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid institution type."},
                status=400,
            )

        if not type_ids:
            return Response(
                {"detail": "Select at least one institution type."},
                status=400,
            )

        profile.institution_type_id = type_ids[0]
        profile.save(update_fields=["institution_type"])
        profile.institution_types.set(type_ids)

    elif "institution_type" in request.data:
        try:
            profile.institution_type_id = int(request.data.get("institution_type"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid institution type."},
                status=400,
            )

    if "country" in request.data:
        try:
            profile.country_id = int(request.data.get("country"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid country."},
                status=400,
            )

    if "administrative_location" in request.data:
        value = request.data.get("administrative_location")
        profile.administrative_location_id = (
            int(value) if value not in [None, ""] else None
        )

    profile.save()

    return Response({
        "institution_name": profile.institution_name,
        "institution_type": profile.institution_type_id,
        "institution_types": list(
            profile.institution_types.values_list("id", flat=True)
        ),
        "established_year": profile.established_year,
        "tagline": profile.tagline,
        "description": profile.description,
        "country": profile.country_id,
        "administrative_location": profile.administrative_location_id,
        "full_address": profile.full_address,
        "website": profile.website,
        "email": profile.email,
        "phone": profile.phone,
    })
