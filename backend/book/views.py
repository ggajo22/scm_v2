from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from book.constants import ERROR_STATUSES, LISTED_STATUSES, STATUS_LABELS, WAITING_STATUSES
from book.models import BookNote, Info, Inven, Shopify_product
from book.serializers import DashboardMetricsSerializer


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
