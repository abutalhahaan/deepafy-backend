from rest_framework.response import Response
from rest_framework.views import APIView

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

        return Response(
            {
                "sections": HomepageSectionSerializer(
                    sections,
                    many=True,
                    context={"request": request},
                ).data,
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