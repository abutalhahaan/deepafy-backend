from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from urllib.parse import urlparse, parse_qs
import re
import json

from core.services.feature_access import get_feature_access
from .models import InstitutionTypeGroup, InstitutionProfile, InstitutionAuthority, InstitutionAcademicData, InstitutionAcademicLevel
from .models import InstitutionAuthority


def extract_map_coordinates(map_url):
    decoded_url = map_url.replace('\u0026', '&')
    parsed = urlparse(decoded_url)
    query_params = parse_qs(parsed.query)

    def valid_coordinates(lat, lon):
        try:
            lat_value = float(lat)
            lon_value = float(lon)
        except (TypeError, ValueError):
            return None

        if -90 <= lat_value <= 90 and -180 <= lon_value <= 180:
            return lat_value, lon_value
        return None

    coordinate_pattern = re.compile(
        r'(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)'
    )

    for key in ('center', 'll', 'q', 'query'):
        for value in query_params.get(key, []):
            match = coordinate_pattern.search(value)
            if match:
                coordinates = valid_coordinates(match.group(1), match.group(2))
                if coordinates:
                    return coordinates

    match = re.search(
        r'/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',
        decoded_url,
    )
    if match:
        coordinates = valid_coordinates(match.group(1), match.group(2))
        if coordinates:
            return coordinates

    match = coordinate_pattern.search(decoded_url)
    if match:
        coordinates = valid_coordinates(match.group(1), match.group(2))
        if coordinates:
            return coordinates

    return None


@api_view(["GET"])
def institution_authority_list(request):
    """
    Return active authorities/boards configured for an
    institution's country and institution type.
    """

    country_id = request.GET.get("country")
    institution_type_id = request.GET.get("institution_type")

    queryset = InstitutionAuthority.objects.filter(
        is_active=True
    ).prefetch_related(
        "institution_types"
    )

    if country_id:
        queryset = queryset.filter(
            country_id=country_id
        )

    if institution_type_id:
        queryset = queryset.filter(
            institution_types__id=institution_type_id
        ).distinct()

    result = {
        "education_boards": [],
        "academic_affiliations": [],
        "regulatory_authorities": [],
        "governing_authorities": [],
    }

    for authority in queryset.order_by(
        "display_order",
        "name",
    ):
        item = {
            "id": authority.id,
            "name": authority.name,
            "short_name": authority.short_name,
            "code": authority.code,
            "relationship_type": authority.relationship_type,
        }

        if authority.relationship_type == "education_board":
            result["education_boards"].append(item)

        elif authority.relationship_type == "academic_affiliation":
            result["academic_affiliations"].append(item)

        elif authority.relationship_type == "regulatory_authority":
            result["regulatory_authorities"].append(item)

        elif authority.relationship_type == "governing_authority":
            result["governing_authorities"].append(item)

    return Response({
        "country": country_id,
        "institution_type": institution_type_id,
        "results": result,
    })


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
            "mission": profile.mission,
            "vision": profile.vision,
            "total_students": profile.total_students,
            "total_teachers": profile.total_teachers,
            "total_staff": profile.total_staff,
            "teacher_student_ratio": (
                round(profile.total_students / profile.total_teachers, 2)
                if profile.total_students is not None and profile.total_teachers
                else None
            ),
            "management_type": profile.management_type,
            "mpo_status": profile.mpo_status,
            "institution_code": profile.institution_code,
            "eiin": profile.eiin,
            "affiliation_board": profile.affiliation_board,
            "affiliations": [
                {
                    "id": authority.id,
                    "name": authority.name,
                    "short_name": authority.short_name,
                    "code": authority.code,
                    "relationship_type": authority.relationship_type,
                }
                for authority in profile.affiliations.filter(is_active=True).order_by(
                    "display_order", "name"
                )
            ],
            "map_location_url": profile.map_location_url,
            "map_latitude": float(profile.map_latitude) if profile.map_latitude is not None else None,
            "map_longitude": float(profile.map_longitude) if profile.map_longitude is not None else None,
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
            "featured_image": request.build_absolute_uri(profile.featured_image.url)
            if profile.featured_image
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

    if "featured_image" in request.FILES:
        profile.featured_image = request.FILES["featured_image"]
        update_fields.append("featured_image")

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
        "featured_image": (
            request.build_absolute_uri(profile.featured_image.url)
            if profile.featured_image
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
        "mission",
        "vision",
        "total_students",
        "total_teachers",
        "total_staff",
        "management_type",
        "mpo_status",
        "institution_code",
        "eiin",
        "affiliation_board",
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

        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError:
                return Response(
                    {"detail": "Invalid institution types format."},
                    status=400,
                )

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

    if "affiliation_ids" in request.data:
        values = request.data.get("affiliation_ids")

        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError:
                return Response(
                    {"detail": "Invalid affiliation IDs format."},
                    status=400,
                )

        if not isinstance(values, list):
            return Response(
                {"detail": "Affiliation IDs must be a list."},
                status=400,
            )

        try:
            affiliation_ids = [
                int(value)
                for value in values
                if value not in [None, ""]
            ]
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid affiliation ID."},
                status=400,
            )

        authorities = InstitutionAuthority.objects.filter(
            id__in=affiliation_ids,
            country_id=profile.country_id,
            is_active=True,
        )

        if len(affiliation_ids) != authorities.count():
            return Response(
                {
                    "detail": (
                        "One or more selected affiliations are invalid "
                        "for this institution's country."
                    )
                },
                status=400,
            )

        profile.affiliations.set(authorities)

    if "featured_image" in request.FILES:
        profile.featured_image = request.FILES["featured_image"]

    if "map_location_url" in request.data:
        map_location_url = str(request.data.get("map_location_url") or "").strip()

        if not map_location_url:
            profile.map_location_url = ""
            profile.map_latitude = None
            profile.map_longitude = None
        else:
            parsed_url = urlparse(map_location_url)

            if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
                return Response(
                    {"detail": "Enter a valid map location URL."},
                    status=400,
                )

            coordinates = extract_map_coordinates(map_location_url)

            if not coordinates:
                return Response(
                    {
                        "detail": "Could not extract latitude and longitude from the map URL. Please use a map URL containing coordinates."
                    },
                    status=400,
                )

            profile.map_location_url = map_location_url
            profile.map_latitude = coordinates[0]
            profile.map_longitude = coordinates[1]

    # Admin-controlled Authority / Affiliation
    if "affiliation_ids" in request.data:
        from institution.models import InstitutionAuthority

        raw_affiliation_ids = request.data.get("affiliation_ids")

        if isinstance(raw_affiliation_ids, str):
            try:
                raw_affiliation_ids = json.loads(raw_affiliation_ids)
            except json.JSONDecodeError:
                return Response(
                    {"detail": "Invalid affiliation IDs format."},
                    status=400,
                )

        if raw_affiliation_ids in [None, ""]:
            raw_affiliation_ids = []

        if not isinstance(raw_affiliation_ids, list):
            return Response(
                {"detail": "Affiliation IDs must be a list."},
                status=400,
            )

        try:
            affiliation_ids = [
                int(value)
                for value in raw_affiliation_ids
                if value not in [None, ""]
            ]
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid affiliation ID."},
                status=400,
            )

        authorities = InstitutionAuthority.objects.filter(
            id__in=affiliation_ids,
            country_id=profile.country_id,
            is_active=True,
        ).prefetch_related("institution_types")

        selected_type_ids = set(
            profile.institution_types.values_list("id", flat=True)
        )

        invalid_authorities = []

        for authority in authorities:
            authority_type_ids = set(
                authority.institution_types.values_list("id", flat=True)
            )

            if not authority_type_ids.intersection(selected_type_ids):
                invalid_authorities.append(authority.id)

        if invalid_authorities:
            return Response(
                {
                    "detail": (
                        "One or more selected authorities are not valid "
                        "for the selected institution type."
                    )
                },
                status=400,
            )

        if len(authorities) != len(set(affiliation_ids)):
            return Response(
                {"detail": "One or more affiliations are invalid or inactive."},
                status=400,
            )

        profile.affiliations.set(authorities)

        # New Authority/Affiliation system is now the source of truth.
        profile.affiliation_board = ""

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
        "mission": profile.mission,
        "vision": profile.vision,
        "featured_image": (
            request.build_absolute_uri(profile.featured_image.url)
            if profile.featured_image
            else None
        ),
        "total_students": profile.total_students,
        "total_teachers": profile.total_teachers,
        "total_staff": profile.total_staff,
        "teacher_student_ratio": (
            round(profile.total_students / profile.total_teachers, 2)
            if profile.total_students is not None and profile.total_teachers
            else None
        ),
        "management_type": profile.management_type,
        "mpo_status": profile.mpo_status,
        "institution_code": profile.institution_code,
        "eiin": profile.eiin,
        "affiliation_board": profile.affiliation_board,
        "affiliations": [
            {
                "id": authority.id,
                "name": authority.name,
                "short_name": authority.short_name,
                "code": authority.code,
                "relationship_type": authority.relationship_type,
            }
            for authority in profile.affiliations.all()
        ],
        "map_location_url": profile.map_location_url,
        "map_latitude": float(profile.map_latitude) if profile.map_latitude is not None else None,
        "map_longitude": float(profile.map_longitude) if profile.map_longitude is not None else None,
        "country": profile.country_id,
        "administrative_location": profile.administrative_location_id,
        "full_address": profile.full_address,
        "website": profile.website,
        "email": profile.email,
        "phone": profile.phone,
    })


@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_academic_levels(request):
    """
    GET:
        Return all academic levels for the authenticated institution.

    POST:
        Create a new academic level.
    """

    institution = getattr(
        request.user,
        "institution_profile",
        None,
    )

    if institution is None:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        levels = InstitutionAcademicLevel.objects.filter(
            institution=institution
        )

        return Response(
            [
                {
                    "id": level.id,
                    "type": level.level_type,
                    "name": level.name,
                    "parent": level.parent or None,
                }
                for level in levels
            ],
            status=status.HTTP_200_OK,
        )

    level_type = str(
        request.data.get("type", "Class")
    ).strip() or "Class"

    name = str(
        request.data.get("name", "")
    ).strip()

    parent = str(
        request.data.get("parent", "")
    ).strip()

    if not name:
        return Response(
            {"detail": "Level name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    level, created = InstitutionAcademicLevel.objects.get_or_create(
        institution=institution,
        level_type=level_type,
        name=name,
        parent=parent,
    )

    return Response(
        {
            "id": level.id,
            "type": level.level_type,
            "name": level.name,
            "parent": level.parent or None,
            "created": created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def institution_academic_level_delete(request, level_id):

    institution = getattr(
        request.user,
        "institution_profile",
        None,
    )

    if institution is None:
        return Response(
            {"detail": "Institution profile not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    level = InstitutionAcademicLevel.objects.filter(
        id=level_id,
        institution=institution,
    ).first()

    if level is None:
        return Response(
            {"detail": "Academic level not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    level.delete()

    return Response(
        {"detail": "Academic level deleted successfully."},
        status=status.HTTP_204_NO_CONTENT,
    )

@api_view(["GET", "POST", "PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])

def institution_academic_data(request):
    """
    GET:
        Return academic data for the authenticated institution.

    POST/PUT:
        Create or update academic data for a date + category.
    """

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
        date = request.query_params.get("date")
        category = request.query_params.get("category")

        queryset = InstitutionAcademicData.objects.filter(
            institution=profile
        )

        if date:
            queryset = queryset.filter(date=date)

        if category:
            queryset = queryset.filter(category=category)

        data = [
            {
                "id": item.id,
                "date": item.date.isoformat(),
                "category": item.category,
                "total": item.total,
                "male": item.male,
                "female": item.female,
                "male_present": item.male_present,
                "male_leave": item.male_leave,
                "female_present": item.female_present,
                "female_leave": item.female_leave,
                "present": item.present,
                "leave": item.leave,
                "absent": item.absent,
            }
            for item in queryset
        ]

        return Response({"results": data})

    data = request.data

    date = data.get("date")
    category = data.get("category")

    if not date:
        return Response(
            {"detail": "Date is required."},
            status=400,
        )

    if not category:
        return Response(
            {"detail": "Category is required."},
            status=400,
        )

    numeric_fields = [
        "total",
        "male",
        "female",
        "male_present",
        "male_leave",
        "female_present",
        "female_leave",
    ]

    values = {}

    for field in numeric_fields:
        value = data.get(field)

        if value in [None, ""]:
            return Response(
                {"detail": f"{field} is required."},
                status=400,
            )

        try:
            value = int(value)
        except (TypeError, ValueError):
            return Response(
                {"detail": f"{field} must be an integer."},
                status=400,
            )

        if value < 0:
            return Response(
                {"detail": f"{field} cannot be negative."},
                status=400,
            )

        values[field] = value

    if values["male"] + values["female"] != values["total"]:
        return Response(
            {"detail": "Male + Female must equal Total."},
            status=400,
        )

    if (
        values["male_present"] + values["male_leave"]
        > values["male"]
    ):
        return Response(
            {
                "detail":
                    "Male Present + Male Leave cannot exceed Total Male."
            },
            status=400,
        )

    if (
        values["female_present"] + values["female_leave"]
        > values["female"]
    ):
        return Response(
            {
                "detail":
                    "Female Present + Female Leave cannot exceed Total Female."
            },
            status=400,
        )

    male_absent = (
        values["male"]
        - values["male_present"]
        - values["male_leave"]
    )

    female_absent = (
        values["female"]
        - values["female_present"]
        - values["female_leave"]
    )

    values["present"] = (
        values["male_present"]
        + values["female_present"]
    )

    values["leave"] = (
        values["male_leave"]
        + values["female_leave"]
    )

    values["absent"] = (
        male_absent
        + female_absent
    )

    academic_data, created = InstitutionAcademicData.objects.update_or_create(
        institution=profile,
        date=date,
        category=category,
        defaults=values,
    )

    return Response(
        {
            "id": academic_data.id,
            "date": academic_data.date.isoformat(),
            "category": academic_data.category,
            "total": academic_data.total,
            "male": academic_data.male,
            "female": academic_data.female,
            "male_present": academic_data.male_present,
            "male_leave": academic_data.male_leave,
            "female_present": academic_data.female_present,
            "female_leave": academic_data.female_leave,
            "present": academic_data.present,
            "leave": academic_data.leave,
            "absent": academic_data.absent,
            "created": created,
        },
        status=201 if created else 200,
    )
