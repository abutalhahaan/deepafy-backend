from rest_framework.response import Response
from rest_framework.views import APIView

from companies.models import Company

from .models import (
    HomepageCTA,
    HomepageHero,
    HomepageSection,
    PlatformStatistic,
)
from .serializers import (
    HomepageCTASerializer,
    HomepageHeroSerializer,
    HomepageSectionSerializer,
    PlatformStatisticSerializer,
)


class HomepageAPIView(APIView):
    def get(self, request):
        sections = HomepageSection.objects.filter(
            is_visible=True,
        ).order_by(
            "display_order",
            "id",
        )

        heroes = HomepageHero.objects.filter(
            is_active=True,
        ).order_by(
            "display_order",
            "id",
        )

        statistics = PlatformStatistic.objects.filter(
            is_visible=True,
        ).order_by(
            "display_order",
            "id",
        )

        cta = HomepageCTA.objects.filter(
            is_active=True,
        ).first()

        serialized_sections = HomepageSectionSerializer(
            sections,
            many=True,
            context={"request": request},
        ).data

        for section in serialized_sections:
            if section["data_source"] == "companies":
                companies = Company.objects.all().order_by(
                    "-created_at"
                )[:section["card_limit"]]

                section["items"] = [
                    {
                        "id": company.id,
                        "name": company.name,
                        "organization_type": (
                            company.organization_type
                        ),
                        "country": company.country,
                    }
                    for company in companies
                ]
            else:
                section["items"] = []

        return Response(
            {
                "sections": serialized_sections,
                "heroes": HomepageHeroSerializer(
                    heroes,
                    many=True,
                    context={"request": request},
                ).data,
                "statistics": PlatformStatisticSerializer(
                    statistics,
                    many=True,
                    context={"request": request},
                ).data,
                "cta": HomepageCTASerializer(
                    cta,
                    context={"request": request},
                ).data
                if cta
                else None,
            }
        )