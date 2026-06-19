import re
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.expressions import RawSQL
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

_FT_SPECIAL = re.compile(r'[+\-><()~*"@]')


def _sanitize_ft(q: str) -> str:
    return _FT_SPECIAL.sub(' ', q).strip()


def _build_ft_query(q: str) -> str:
    """Require ALL whitespace-separated terms (BOOLEAN MODE AND semantics)."""
    sanitized = _sanitize_ft(q)
    if not sanitized:
        return ''
    return ' '.join(f'+{term}' for term in sanitized.split())


from book.constants import ERROR_STATUSES, LISTED_STATUSES, STATUS_LABELS, WAITING_STATUSES
from book.models import BookNote, Info, Inven, Shopify_product
from book.serializers import BookDetailSerializer, DashboardMetricsSerializer


# @MX:ANCHOR: [AUTO] BookListViewSet.list — search endpoint for book inventory
# @MX:REASON: REQ-SEARCH-001 through REQ-SEARCH-008 all served by this single list action
class BookListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/book/search/?search=<query>
    Two-path search:
      - digits only → inven_SKU startswith (index scan, fast)
      - text        → FULLTEXT MATCH AGAINST ngram on info.name (Korean-aware)
    REQ-SEARCH-001 to REQ-SEARCH-008
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = BookDetailSerializer

    def get_queryset(self):
        # REQ-SEARCH-008: select_related avoids N+1 on info fields
        qs = Inven.objects.select_related("info")
        search = self.request.query_params.get("search", "").strip()
        if not search:
            return qs.order_by("id")

        # ISBN path: digits only → startswith uses the inven_SKU index
        if search.isdigit():
            return qs.filter(inven_SKU__startswith=search).order_by("id")

        # Text path: annotate relevance score so DRF paginator gets the full result set
        # (avoids the 50-item LIMIT that broke pagination)
        # _build_ft_query prefixes each token with + so BOOLEAN MODE requires ALL terms
        safe_q = _build_ft_query(search)
        if not safe_q:
            return qs.none()

        # filter(info__isnull=False) forces the book_info JOIN into COUNT queries too;
        # without it, select_related JOIN is stripped on .count() and MATCH fails.
        return (
            qs
            .filter(info__isnull=False)
            .extra(
                select={"relevance": "MATCH(`book_info`.`name`) AGAINST (%s IN BOOLEAN MODE)"},
                select_params=[safe_q],
                where=["MATCH(`book_info`.`name`) AGAINST (%s IN BOOLEAN MODE) > 0"],
                params=[safe_q],
            )
            .order_by("-relevance")
        )


class DashboardMetricsView(APIView):
    # @MX:ANCHOR: [AUTO] DashboardMetricsView.get — single entry point for all 8 dashboard metrics
    # @MX:REASON: REQ-BD-001 through REQ-BD-011 all flow through this method;
    # changes affect all metrics
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        # REQ-BD-003: status_counts — aggregate Inven by status_of_shopify
        raw_counts = (
            Inven.objects.values("status_of_shopify")
            .annotate(count=Count("id"))
            .order_by("status_of_shopify")
        )
        status_counts = [
            {
                "status": row["status_of_shopify"],
                "label": STATUS_LABELS.get(row["status_of_shopify"], "Unknown"),
                "count": row["count"],
            }
            for row in raw_counts
        ]

        # REQ-BD-004: shopify_created_24h — Shopify products created strictly within last 24h
        shopify_created_24h = Shopify_product.objects.filter(
            created_at__gt=now - timedelta(hours=24)
        ).count()

        # REQ-BD-005/006: error metrics — derived from status_counts (no extra query)
        error_rows = [row for row in status_counts if row["status"] in ERROR_STATUSES]
        error_total = sum(row["count"] for row in error_rows)

        # REQ-BD-007: waiting_total
        waiting_total = Inven.objects.filter(
            status_of_shopify__in=WAITING_STATUSES
        ).count()

        # REQ-BD-008: unresolved GENERAL notes
        unresolved_note_count = BookNote.objects.filter(
            note_type="GENERAL", is_resolved=False
        ).count()

        # REQ-BD-009: listed items with sale price = 0
        sale_zero_count = Info.objects.filter(
            price_sale=0,
            inven__status_of_shopify__in=LISTED_STATUSES,
        ).count()

        # REQ-BD-010: listed items with both price and kyobo_supply_price = 0
        cost_zero_count = Info.objects.filter(
            price=0,
            kyobo_supply_price=0,
            inven__status_of_shopify__in=LISTED_STATUSES,
        ).count()

        payload = {
            "status_counts": status_counts,
            "shopify_created_24h": shopify_created_24h,
            "error_total": error_total,
            "error_rows": error_rows,
            "waiting_total": waiting_total,
            "unresolved_note_count": unresolved_note_count,
            "sale_zero_count": sale_zero_count,
            "cost_zero_count": cost_zero_count,
        }

        serializer = DashboardMetricsSerializer(payload)
        return Response(serializer.data)
