from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import InstitutionTypeGroup


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
