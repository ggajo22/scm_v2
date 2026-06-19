import re
from datetime import timedelta

from django.db import connection
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


def _ft_ids_by_score(q: str, limit: int = 50) -> list[int]:
    """Return inven_ids sorted by FULLTEXT relevance score descending."""
    sql = """
        SELECT inven_id
        FROM book_info
        WHERE MATCH(name) AGAINST (%s IN BOOLEAN MODE)
        ORDER BY MATCH(name) AGAINST (%s IN BOOLEAN MODE) DESC
        LIMIT %s
    """
    with connection.cursor() as cur:
        cur.execute(sql, [q, q, limit])
        return [r[0] for r in cur.fetchall()]


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

        # Text path: FULLTEXT ngram search sorted by relevance score
        safe_q = _sanitize_ft(search)
        if not safe_q:
            return qs.none()

        ordered_ids = _ft_ids_by_score(safe_q)
        if not ordered_ids:
            return qs.none()

        # Preserve relevance order in DB via FIELD() — keeps QuerySet for pagination
        placeholders = ','.join(['%s'] * len(ordered_ids))
        return qs.filter(id__in=ordered_ids).order_by(
            RawSQL(f"FIELD(book_inven.id, {placeholders})", ordered_ids)
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
