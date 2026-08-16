import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework import generics
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import IsSuperAdmin

from .excel_utils import generate_line_item_notes_excel
from .models import ExchangeRate, LineItem, LineItemNote, Order, StoreSyncWatermark
from .serializers import (
    ExchangeRateSerializer,
    LineItemNoteSerializer,
    LineItemNoteUnresolvedSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    OrderNoteSerializer,
)
from .shopify_orders import sync_single_order_from_shopify, sync_store

# SPEC-PURCHASE-ORDER-011: canonical store list for the sync-status endpoint.
# Mirrors the literal store lists already used elsewhere in this app
# (OrderSyncView.post above, management/commands/sync_orders.py STORE_TYPES).
SYNC_STATUS_STORE_TYPES = ["gimssine", "etoile"]


class OrderDetailView(RetrieveAPIView):
    """REQ-OD-002: GET /api/orders/{pk}/ — single order with full nested detail."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer

    def get_queryset(self):
        # @MX:NOTE: [AUTO] select_related covers FK/O2O (single JOIN), prefetch_related covers
        # reverse FK collections (separate queries, avoids cartesian product)
        return Order.objects.select_related(
            "customer", "shipping_address"
        ).prefetch_related(
            "line_items__notes__author", "shipping_lines", "refunds"
        )


class OrderSyncView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _sync_store_safe(self, store_type):
        try:
            with transaction.atomic():
                return sync_store(store_type)
        except Exception as e:
            return {"synced_count": 0, "updated_count": 0, "error": str(e)}

    def post(self, request):
        store_results = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(self._sync_store_safe, store_type): store_type
                for store_type in ["gimssine", "etoile"]
            }
            for future in as_completed(futures):
                store_results[futures[future]] = future.result()

        status_val = (
            "completed"
            if all(r["error"] is None for r in store_results.values())
            else "partial"
        )
        return Response(
            {
                "status": status_val,
                "stores": store_results,
                "total_synced": sum(r["synced_count"] for r in store_results.values()),
                "total_updated": sum(r["updated_count"] for r in store_results.values()),
            }
        )


class OrderSyncStatusView(APIView):
    """GET /api/orders/sync-status/ — surfaces the last time the scheduled
    Shopify sync (sync_store(), run every 5 minutes by a Windows scheduled
    task) actually executed, per store, so a super_admin can tell the
    scheduled job stopped even when it has been quiet (no new Shopify
    activity) rather than failing.

    Deliberately reads StoreSyncWatermark.last_run_at, NOT
    last_synced_updated_at or updated_at — see the StoreSyncWatermark model
    docstring and sync_store() for why those columns can sit stale for hours
    on a perfectly healthy sync and would make this indicator useless.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        # Single query for all watermark rows; canonical stores that have no
        # row yet (or aren't in the DB at all) fall back to nulls below.
        watermarks_by_store = {
            row["store_type"]: row
            for row in StoreSyncWatermark.objects.filter(
                store_type__in=SYNC_STATUS_STORE_TYPES
            ).values("store_type", "last_run_at", "last_synced_updated_at")
        }

        stores = []
        top_level_last_run_at = None
        any_unknown = False
        for store_type in SYNC_STATUS_STORE_TYPES:
            row = watermarks_by_store.get(store_type)
            last_run_at = row["last_run_at"] if row else None
            last_synced_updated_at = row["last_synced_updated_at"] if row else None
            stores.append(
                {
                    "store_type": store_type,
                    "last_run_at": last_run_at,
                    "last_synced_updated_at": last_synced_updated_at,
                }
            )
            if last_run_at is None:
                # Missing watermark row or NULL last_run_at both mean
                # "unknown" — MIN cannot be trusted once any store is
                # unknown, so the top-level value must be null too
                # (unknown beats falsely-fresh).
                any_unknown = True
            elif top_level_last_run_at is None or last_run_at < top_level_last_run_at:
                # MIN across stores, not MAX: a single silently-stopped
                # store must make the top-level value look stale, which a
                # MAX would hide.
                top_level_last_run_at = last_run_at

        return Response(
            {
                "last_run_at": None if any_unknown else top_level_last_run_at,
                "stores": stores,
            }
        )


class OrderPagination(PageNumberPagination):
    page_size = 50


# SPEC-ORDER-023 REQ-OLIST-024: the only 6 accepted `logistics_display`
# filter values -- anything else is ignored (fail-open, REQ-OLIST-024a,
# AC-OLIST-022f), never mapped to a "no rows match" condition.
LOGISTICS_DISPLAY_FILTER_VALUES = {
    "not_shipped",
    "shipment_confirmed",
    "outbound_scheduled",
    "partial_shipped",
    "shipped",
    "partial",
}


# @MX:WARN: [AUTO] SPEC-ORDER-023 REQ-OLIST-023~025: this Exists-based SQL
# filter MUST implement the exact same priority order as
# OrderListSerializer._derive_line_item_states (the Python display path) --
# shipped > partial_shipped > outbound_scheduled > uniform-passthrough >
# partial. Editing one path without the other breaks AC-OLIST-022~022e
# (each asserts filter results AND the returned orders' displayed value
# together). `trackable_qs` mirrors the same sku__isnull=False definition
# used by the display path and by purchase_order_views._recompute_order_
# aggregates (design decision D) -- never Order.status.
# @MX:REASON: silent SQL/Python priority drift is undetectable by type
# checkers or linters and only surfaces as wrong search results in
# production; this pairing is the single riskiest edit surface in the SPEC.
def _apply_logistics_display_filter(qs, value):
    trackable_qs = LineItem.objects.filter(order=OuterRef("pk"), sku__isnull=False)
    qs = qs.annotate(
        li_has_trackable=Exists(trackable_qs),
        li_not_all_shipped=Exists(trackable_qs.exclude(logistics_status="shipped")),
        li_any_partial=Exists(trackable_qs.filter(shipped_quantity__gt=0)),
        li_not_all_received=Exists(trackable_qs.exclude(logistics_status="received")),
        li_not_all_not_shipped=Exists(trackable_qs.exclude(logistics_status="not_shipped")),
        li_not_all_shipment_confirmed=Exists(
            trackable_qs.exclude(logistics_status="shipment_confirmed")
        ),
        li_not_all_outbound_scheduled=Exists(
            trackable_qs.exclude(logistics_status="outbound_scheduled")
        ),
    )

    all_shipped = Q(li_has_trackable=True) & Q(li_not_all_shipped=False)
    any_partial = Q(li_any_partial=True)
    all_received = Q(li_has_trackable=True) & Q(li_not_all_received=False)
    all_not_shipped = Q(li_has_trackable=True) & Q(li_not_all_not_shipped=False)
    all_shipment_confirmed = Q(li_has_trackable=True) & Q(li_not_all_shipment_confirmed=False)
    all_outbound_scheduled = Q(li_has_trackable=True) & Q(li_not_all_outbound_scheduled=False)

    if value == "shipped":
        q = all_shipped
    elif value == "partial_shipped":
        q = ~all_shipped & any_partial
    elif value == "outbound_scheduled":
        q = ~all_shipped & ~any_partial & (all_received | all_outbound_scheduled)
    elif value == "not_shipped":
        q = ~all_shipped & ~any_partial & ~all_received & all_not_shipped
    elif value == "shipment_confirmed":
        q = ~all_shipped & ~any_partial & ~all_received & all_shipment_confirmed
    else:  # "partial" (REQ-OLIST-011a): none of the 6 uniform buckets match
        q = (
            Q(li_has_trackable=True)
            & ~all_shipped
            & ~any_partial
            & ~all_received
            & ~all_not_shipped
            & ~all_shipment_confirmed
            & ~all_outbound_scheduled
        )

    return qs.filter(q)


class OrderListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        # SPEC-ORDER-023 v1.4.0 REQ-OLIST-021: "line_items__purchase_orders"
        # feeds _is_awaiting_purchase (serializers.py) the PurchaseOrder
        # linkage REQ-OLIST-013 requires. One extra M2M query for the whole
        # page regardless of page size — without it the serializer would fall
        # back to one query per line item.
        qs = Order.objects.prefetch_related(
            "refunds", "line_items", "line_items__purchase_orders", "customer"
        ).order_by("-shopify_created_at")
        params = self.request.query_params

        store_type = params.get("store_type")
        if store_type:
            qs = qs.filter(store_type=store_type)

        financial_status = params.get("financial_status")
        if financial_status:
            qs = qs.filter(financial_status=financial_status)

        location = params.get("location")
        if location:
            parts = [p for p in location.split("/") if p]
            if len(parts) > 1:
                q = Q()
                for part in parts:
                    q &= Q(location__contains=part)
                qs = qs.filter(q)
            else:
                qs = qs.filter(location=location)

        fulfillment_status = params.get("fulfillment_status")
        if fulfillment_status:
            if fulfillment_status == "unfulfilled":
                qs = qs.filter(fulfillment_status__isnull=True)
            else:
                qs = qs.filter(fulfillment_status=fulfillment_status)

        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise ValidationError({"detail": "date_from must be before date_to"})
        if date_from:
            qs = qs.filter(shopify_created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(shopify_created_at__date__lte=date_to)

        # @MX:ANCHOR: [AUTO] search filter — called by every GET /api/orders/ request
        # @MX:REASON: fan_in >= 3 (view, tests, frontend); Q expression joins line_items so distinct() is mandatory
        search: str = params.get("search", "").strip()
        if search:
            numeric = search.lstrip("#")
            q = Q(name__icontains=search)
            if numeric.isdigit():
                try:
                    q |= Q(order_number=int(numeric))
                except (ValueError, OverflowError):
                    pass
            # ISBN / SKU pattern: 10–13 digits
            if numeric.isdigit() and 10 <= len(numeric) <= 13:
                q |= Q(line_items__sku=numeric)
            qs = qs.filter(q).distinct()

        # SPEC-ORDER-023 REQ-OLIST-023/024a: unrecognized values are ignored
        # entirely (fail-open) -- never mapped to a zero-result filter.
        logistics_display = params.get("logistics_display")
        if logistics_display in LOGISTICS_DISPLAY_FILTER_VALUES:
            qs = _apply_logistics_display_filter(qs, logistics_display)

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["exchange_rate_history"] = getattr(self, "_exchange_rate_history", [])
        return context

    # @MX:NOTE: [AUTO] SPEC-ORDER-023 REQ-OLIST-019/020/021/022a: single
    # page-level batch load, replacing what would otherwise be up to 50
    # per-order ExchangeRate queries (~130ms each against this remote RDS
    # instance, ~6.5s worst case) if OrderDetailSerializer's per-instance
    # memoized _get_exchange_rate were reused unmodified in a list context.
    # No lower bound on effective_date (slim `values_list` projection of the
    # full history instead of a lookback window, design decision A) --
    # shopify_created_at can be arbitrarily old, and a lower bound risks
    # missing the same fallback record _get_exchange_rate would have found
    # (REQ-OLIST-020). `.date()` is called directly on shopify_created_at
    # (never via timezone.localtime()) so the resolved calendar date is
    # identical to _get_exchange_rate's regardless of the deployment's
    # TIME_ZONE setting (AC-OLIST-020a).
    def _load_exchange_rate_history(self, orders):
        dates = [o.shopify_created_at.date() for o in orders if o.shopify_created_at]
        if not dates:
            return []
        max_date = max(dates)
        return list(
            ExchangeRate.objects.filter(effective_date__lte=max_date)
            .order_by("effective_date")
            .values_list("effective_date", "rate")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        iterable = page if page is not None else queryset
        self._exchange_rate_history = self._load_exchange_rate_history(iterable)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrderNoteListView(ListAPIView):
    """List orders that have a non-empty note and note_resolved=False."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = OrderNoteSerializer
    pagination_class = None  # return plain array, not paginated envelope

    def get_queryset(self):
        return (
            Order.objects
            .filter(note__isnull=False, note_resolved=False)
            .exclude(note="")
            .select_related("customer")
            .order_by("-shopify_created_at")
        )


class OrderNoteResolveView(APIView):
    """Mark an order's note as resolved."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        order.note_resolved = True
        order.save(update_fields=["note_resolved"])
        return Response({"note_resolved": True}, status=status.HTTP_200_OK)


class OrderResyncView(APIView):
    """REQ-RS-001: POST /api/orders/{pk}/sync/ — re-fetch single order from Shopify."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int) -> Response:
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # SPEC-SHOPIFY-SKU-SET-002 REQ-SKUSET2-003: a bundle-mapped line item
            # now expands into N per-member-ISBN LineItem.update_or_create() calls
            # inside _sync_single_order(). Without an outer transaction, a crash
            # or network failure mid-loop during a resync (unlike initial sync,
            # which already runs sync_store() inside transaction.atomic() via
            # OrderSyncView._sync_store_safe) could persist only SOME member ISBN
            # rows for a bundle, breaking the "N rows always share a consistent
            # member set" invariant the stale-deletion and refund-subquery logic
            # both implicitly rely on. Wrapping mirrors the existing sync_store()
            # atomic pattern above.
            with transaction.atomic():
                sync_single_order_from_shopify(order.shopify_order_id, order.store_type)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return Response(
                    {"error": "Shopify에서 주문을 찾을 수 없습니다."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except urllib.error.URLError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        qs = Order.objects.select_related(
            "customer", "shipping_address"
        ).prefetch_related(
            "line_items__notes__author", "shipping_lines", "refunds"
        )
        order = qs.get(pk=pk)
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExchangeRateListCreateView(generics.ListCreateAPIView):
    """REQ-004, REQ-005: GET/POST /api/exchange-rates/ — 환율 목록 조회 및 생성."""

    queryset = ExchangeRate.objects.all().order_by("-effective_date")
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]


class ExchangeRateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """REQ-006, REQ-007, REQ-008: GET/PUT/DELETE /api/exchange-rates/{date}/."""

    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "effective_date"
    lookup_url_kwarg = "date"


class LineItemNoteListCreateView(generics.ListCreateAPIView):
    """SPEC-ORDER-010: GET/POST /api/orders/line-items/{pk}/notes/ — 품목 노트 목록 및 생성."""

    serializer_class = LineItemNoteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        line_item_pk = self.kwargs["pk"]
        return LineItemNote.objects.filter(line_item_id=line_item_pk).select_related("author")

    def perform_create(self, serializer):
        line_item_pk = self.kwargs["pk"]
        line_item = get_object_or_404(LineItem, pk=line_item_pk)
        serializer.save(author=self.request.user, line_item=line_item)


class LineItemNoteUnresolvedListView(generics.ListAPIView):
    """SPEC-ORDER-010: GET /api/orders/line-item-notes/ — 미해결 품목 노트 목록."""

    serializer_class = LineItemNoteUnresolvedSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            LineItemNote.objects.filter(is_resolved=False)
            .select_related("line_item__order", "author")
            .order_by("-created_at")
        )


class LineItemNoteResolveView(APIView):
    """SPEC-ORDER-010: PATCH /api/orders/line-item-notes/{pk}/resolve/ — 품목 노트 해결."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        note = get_object_or_404(LineItemNote, pk=pk)
        note.is_resolved = True
        note.save(update_fields=["is_resolved"])
        return Response({"is_resolved": True})


class LineItemNoteExportView(APIView):
    """GET /api/orders/line-item-notes/export/?publisher=agape|sungseoyunion|other — 타출판사 노트 엑셀 다운로드."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    PUBLISHER_LABELS = {
        "agape": "아가페",
        "sungseoyunion": "성서유니온",
        "other": "기타",
    }

    def get(self, request):
        publisher = request.query_params.get("publisher", "other")

        qs = (
            LineItemNote.objects.filter(is_resolved=False, note_type="타출판사")
            .select_related("line_item__order", "author")
            .order_by("-created_at")
        )

        if publisher == "agape":
            qs = qs.filter(content="아가페")
        elif publisher == "sungseoyunion":
            qs = qs.filter(content="성서유니온")
        else:
            qs = qs.exclude(content__in=["아가페", "성서유니온"])

        notes = [
            {
                "order_name": n.line_item.order.name if n.line_item and n.line_item.order else "",
                "line_item_sku": n.line_item.sku if n.line_item else "",
                "line_item_title": n.line_item.title if n.line_item else "",
                "content": n.content,
                "author_username": n.author.username if n.author else "",
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "",
                "confirmed_distributor": n.line_item.confirmed_distributor if n.line_item else "",
            }
            for n in qs
        ]

        file_bytes = generate_line_item_notes_excel(notes)
        label = self.PUBLISHER_LABELS.get(publisher, "기타")
        filename = f"타출판사_메모_{label}.xlsx"

        qs.update(is_resolved=True)

        response = HttpResponse(
            file_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
