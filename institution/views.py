from rest_framework.decorators import api_view, authentication_classes, permission_classes
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
                    "id": location.location_id,
                    "name": location.name,
                    "level": location.level.level,
                    "level_name": location.level.name,
                }
                if location
                else None
            ),
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


@api_view(["PUT"])
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

    profile.save(update_fields=[
        "background_color",
        "background_image",
    ])

    return Response({
        "background_color": profile.background_color,
        "background_image": (
            request.build_absolute_uri(profile.background_image.url)
            if profile.background_image
            else None
        ),
    })
