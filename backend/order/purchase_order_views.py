"""
Purchase order API views for SPEC-PURCHASE-ORDER-001 M2~M7.

Endpoints:
  M2  GET  /api/purchase-orders/unordered/
  M3  POST /api/purchase-orders/generate-order-file/
  M4a POST /api/purchase-orders/upload-vendor-file/
  M4b GET  /api/purchase-orders/comparison/
  M5  POST /api/purchase-orders/confirm/
  M6  GET/POST /api/purchase-orders/vendor-rules/
  M6  DELETE   /api/purchase-orders/vendor-rules/<id>/
  M7  GET  /api/purchase-orders/

# @MX:ANCHOR: [AUTO] All views require JWT auth; public API contract for purchase order flow
# @MX:REASON: Central fan-in point for purchase order lifecycle (unordered → generate → upload → confirm)
"""

from collections import defaultdict
from datetime import date
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from django.db import IntegrityError, transaction
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .excel_utils import (
    _NOTE_TYPE_STATUS_MAP,
    auto_select_distributor,
    generate_daily_review_excel,
    generate_order_excel,
    parse_daily_review_excel,
    parse_outbound_excel,
    parse_rack_number_excel,
    parse_vendor_excel,
    parse_vendor_shipment_excel,
    parse_warehouse_receipt_excel,
)
from .models import (
    LOGISTICS_STATUS_CHOICES,
    BooxenData,
    DistributorVendorRule,
    KyoboData,
    LineItem,
    LineItemNote,
    Order,
    PurchaseOrder,
    Refund,
    VendorComparison,
    WarehouseStock,
    Yes24Data,
)

VALID_DISTRIBUTORS = {"booxen", "kyobo", "yes24", "choeumgoyuk", "agape", "sungseoyunion",
                      "warehouse_korea", "warehouse_ca", "warehouse_nj"}
VENDOR_FILE_DISTRIBUTORS = {"booxen", "kyobo", "yes24"}
VENDOR_RULE_DISTRIBUTORS = {"choeumgoyuk", "agape", "sungseoyunion"}

EXCEL_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# @MX:NOTE: [AUTO] Shared reorder-candidate eligibility filter (SPEC-PURCHASE-ORDER-010).
# Fan-in == 4 (UnorderedItemsView, RunComparisonView, DailyReviewExcelView,
# UploadDailyReviewView's SKU-batch query) would normally qualify for @MX:ANCHOR,
# but this file is already at its configured anchor_per_file limit (3, see
# .moai/config/sections/mx.yaml) with 4 pre-existing ANCHOR tags — demoted to
# NOTE rather than pushing the file further over budget or demoting unrelated
# pre-existing tags out of scope for this SPEC.
def _reorder_candidate_filter(queryset):
    """
    REQ-DMG-005: widen a LineItem queryset so it includes:
      - LineItems with purchase_status="unordered" that are NOT linked to any
        existing PurchaseOrder (original behavior), OR
      - LineItems with purchase_status="damaged_exchange", regardless of
        existing PurchaseOrder linkage.

    Implemented as a single `.exclude()` call so the multi-valued
    `purchase_orders` relation is evaluated as a NOT EXISTS subquery rather
    than a JOIN — this avoids duplicate rows for LineItems linked to 2+
    PurchaseOrders without needing `.distinct()` (verified empirically via
    TestUnorderedItemsViewDamagedExchange.test_damaged_exchange_linked_to_two_purchase_orders_no_duplicate_rows).
    """
    return (
        queryset.filter(Q(purchase_status="unordered") | Q(purchase_status="damaged_exchange"))
        .exclude(purchase_status="unordered", purchase_orders__isnull=False)
    )


# @MX:NOTE: [AUTO] Order.status + Order.ready_to_ship aggregate recomputation
# (SPEC-ORDER-011, extended by SPEC-ORDER-012). Fan-in == 8
# (UploadVendorShipmentView, UploadWarehouseReceiptView,
# LineItemLogisticsStatusUpdateView, LineItemLogisticsStatusBulkUpdateView,
# ConfirmOrderView, LineItemStatusUpdateView, LineItemBulkStatusUpdateView,
# UploadDailyReviewView) would normally qualify for @MX:ANCHOR, but this
# file is already at its configured anchor_per_file limit (3, see
# .moai/config/sections/mx.yaml) with 4 pre-existing ANCHOR tags — demoted
# to NOTE, same precedent as _reorder_candidate_filter above
# (SPEC-PURCHASE-ORDER-010).
def _recompute_order_aggregates(order_ids) -> None:
    """
    REQ-LOGI-008/009/010: recompute Order.status as an aggregate over
    trackable (sku not null) child LineItems' logistics_status — the shared
    value when uniform, "partial" when 2+ distinct values are present, unset
    (None) when no trackable LineItems exist for that Order.

    SPEC-ORDER-012 REQ-RTS-002/003/003a/004: in the same pass, recompute
    Order.ready_to_ship over the same trackable LineItem set: LineItems with
    purchase_status="order_cancelled" are excluded entirely; if none remain,
    `None`; else `False` if any remaining LineItem has
    purchase_status="cs_required"; else `True` iff every remaining LineItem
    has logistics_status="received" OR purchase_status="in_stock" (`False`
    otherwise).

    Two-query design so the number of queries issued depends on the number
    of distinct Orders in `order_ids`, never on the number of LineItems that
    were updated (SPEC-PURCHASE-ORDER-009 N+1-avoidance precedent,
    REQ-RTS-004a):
      1. one SELECT for (order_id, logistics_status, purchase_status)
         triples of every trackable LineItem under `order_ids`, grouped in
         Python.
      2. one UPDATE (Case/When for both `status` and `ready_to_ship`)
         covering every Order in `order_ids` in a single statement.

    No-op (zero queries) when `order_ids` is empty.
    """
    order_id_list = list(order_ids)
    if not order_id_list:
        return

    items_by_order: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for order_id, logistics_status, purchase_status in LineItem.objects.filter(
        order_id__in=order_id_list, sku__isnull=False
    ).values_list("order_id", "logistics_status", "purchase_status"):
        items_by_order[order_id].append((logistics_status, purchase_status))

    status_field = CharField(max_length=50, null=True)
    ready_field = BooleanField(null=True)
    status_whens = []
    ready_whens = []
    for order_id in order_id_list:
        items = items_by_order.get(order_id)

        # REQ-LOGI-008/009/010: Order.status aggregate.
        if not items:
            new_status = None
        else:
            statuses = {logistics_status for logistics_status, _ in items}
            new_status = next(iter(statuses)) if len(statuses) == 1 else "partial"
        status_whens.append(When(id=order_id, then=Value(new_status, output_field=status_field)))

        # SPEC-ORDER-012 REQ-RTS-002: Order.ready_to_ship aggregate.
        non_cancelled = [it for it in (items or []) if it[1] != "order_cancelled"]
        if not non_cancelled:
            ready_to_ship = None
        elif any(purchase_status == "cs_required" for _, purchase_status in non_cancelled):
            ready_to_ship = False
        else:
            ready_to_ship = all(
                logistics_status == "received" or purchase_status == "in_stock"
                for logistics_status, purchase_status in non_cancelled
            )
        ready_whens.append(When(id=order_id, then=Value(ready_to_ship, output_field=ready_field)))

    Order.objects.filter(id__in=order_id_list).update(
        status=Case(
            *status_whens, default=Value(None, output_field=status_field), output_field=status_field
        ),
        ready_to_ship=Case(
            *ready_whens, default=Value(None, output_field=ready_field), output_field=ready_field
        ),
    )


def _apply_logistics_transition(
    rows: list[dict],
    eligibility_filter: Q,
    target_status: str,
) -> tuple[int, int, set[int]]:
    """
    Shared (order_name, sku)-matching/transition/bulk_update helper for
    UploadVendorShipmentView (REQ-LOGI-003) and UploadWarehouseReceiptView
    (REQ-LOGI-005). Safety fix: previously matched on SKU alone, which let a
    shipment/receipt upload naming ONE order flip every LineItem sharing
    that SKU across EVERY order (mirrors the SPEC-ORDER-015 outbound bug,
    see _process_outbound_rows). `rows` is the parsed
    {"name": str, "sku": str} list; `eligibility_filter` is each view's own
    current-status Q gate, applied alongside the resolved order/sku filters.

    Counting convention mirrors UploadDailyReviewView (REQ-LOGI-004): counts
    are per distinct (order_name, sku) pair, not per LineItem row — a pair
    that expands into multiple LineItem rows still counts once, and
    `matched_count + skipped_count == len({(name, sku) for row in rows})`
    always holds (AC-LOGI-004).

    Returns (matched_count, skipped_count, affected_order_ids) —
    `affected_order_ids` is collected from the already-fetched LineItem
    instances (zero extra queries), for the caller to pass to
    `_recompute_order_aggregates()`.
    """
    pairs = {(row["name"], row["sku"]) for row in rows}

    # Order.name carries no uniqueness constraint (unique_together is
    # (shopify_order_id, store_type)), so several orders may share a name.
    # `.order_by("pk")` + setdefault resolves that collision exactly like
    # _process_outbound_rows does — oldest-wins — rather than inheriting
    # whatever order MySQL happens to return rows in.
    orders_by_name: dict[str, Order] = {}
    names = {name for name, _ in pairs if name}
    if names:
        for candidate in Order.objects.filter(name__in=names).order_by("pk"):
            orders_by_name.setdefault(candidate.name, candidate)

    # One fetch for every eligible LineItem across all resolved orders,
    # grouped by (order_id, sku) so the loop below is a dict lookup — mirrors
    # _process_outbound_rows' single-fetch-then-python-group approach.
    lineitems_by_key: dict[tuple[int, str], list] = defaultdict(list)
    if orders_by_name:
        skus = {sku for _, sku in pairs}
        eligible = LineItem.objects.filter(
            eligibility_filter,
            order_id__in=[o.id for o in orders_by_name.values()],
            sku__in=skus,
        ).select_for_update()
        for li in eligible:
            lineitems_by_key[(li.order_id, li.sku)].append(li)

    matched_count = 0
    skipped_count = 0
    to_update: list = []
    affected_order_ids: set[int] = set()

    for name, sku in pairs:
        order = orders_by_name.get(name) if name else None
        if order is None:
            skipped_count += 1
            continue

        lis = lineitems_by_key.get((order.id, sku))
        if not lis:
            skipped_count += 1
            continue

        for li in lis:
            li.logistics_status = target_status
            affected_order_ids.add(li.order_id)
        to_update.extend(lis)
        matched_count += 1

    if to_update:
        LineItem.objects.bulk_update(to_update, ["logistics_status"])

    return matched_count, skipped_count, affected_order_ids


# ---------------------------------------------------------------------------
# M2: Unordered line items
# ---------------------------------------------------------------------------


class UnorderedItemsView(APIView):
    """
    GET /api/purchase-orders/unordered/

    Returns LineItems (aggregated by SKU) that are NOT yet linked to any PurchaseOrder.
    Each result includes auto_distributor derived from DistributorVendorRule.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        # Subquery: total refunded qty for each (order_id, shopify_line_item_id) pair
        refund_sum_sq = (
            Refund.objects.filter(
                order_id=OuterRef("order_id"),
                line_item_id=OuterRef("shopify_line_item_id"),
            )
            .values("order_id", "line_item_id")
            .annotate(total=Sum("quantity"))
            .values("total")[:1]
        )

        line_items = (
            _reorder_candidate_filter(LineItem.objects.filter(sku__isnull=False))
            .annotate(
                refunded_qty=Coalesce(
                    Subquery(refund_sum_sq, output_field=IntegerField()),
                    0,
                )
            )
            .select_related("order")
            .order_by("-order__shopify_created_at")
        )

        rule_map: dict[str, str] = dict(
            DistributorVendorRule.objects.values_list("publisher_name", "distributor")
        )

        results = []
        for li in line_items:
            net_qty = max((li.quantity or 0) - li.refunded_qty, 0)
            if net_qty == 0:
                continue  # Fully refunded — exclude from unordered list
            order = li.order
            order_name = order.name or (f"#{order.order_number}" if order.order_number else None)
            results.append(
                {
                    "id": li.pk,
                    "order_name": order_name,
                    "sku": li.sku,
                    "title": li.title or "",
                    "vendor": li.vendor or "",
                    "quantity": net_qty,
                    "purchase_status": li.purchase_status,
                    "auto_distributor": rule_map.get(li.vendor or ""),
                }
            )

        # SPEC-SHOPIFY-SKU-SET-002 REQ-SKUSET2-007: bundle expansion now happens
        # at Shopify-sync time (see shopify_orders._sync_single_order), so
        # LineItem.sku is already the real ISBN here — no display-time
        # expansion needed.
        return Response({"count": len(results), "results": results})


# ---------------------------------------------------------------------------
# M3: Generate order Excel file
# ---------------------------------------------------------------------------


class GenerateOrderFileView(APIView):
    """
    POST /api/purchase-orders/generate-order-file/

    Body: {"distributor": str, "skus": [str, ...]}

    Returns:
      - Excel binary (Content-Type xlsx) when all SKUs are found.
      - JSON {"warning": ..., "unknown_skus": [...]} when some/all SKUs are not found.
      - HTTP 400 for empty skus or invalid distributor.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response | HttpResponse:
        distributor = request.data.get("distributor")
        skus = request.data.get("skus")

        # Validate inputs
        if not distributor:
            return Response(
                {"detail": "distributor is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if distributor not in VALID_DISTRIBUTORS:
            return Response(
                {"detail": f"Invalid distributor. Choose from: {sorted(VALID_DISTRIBUTORS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not skus:
            return Response(
                {"detail": "skus must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # SPEC-SHOPIFY-SKU-SET-002 REQ-SKUSET2-009: bundle SKUs are already
        # expanded into real-ISBN LineItem rows at Shopify-sync time, so a
        # requested SKU matches LineItem.sku directly — no bundle-mapping
        # reverse lookup needed (reverts the commit 6d2dfc4 reactive patch).
        requested = set(skus)
        refund_sum_sq = (
            Refund.objects.filter(
                order_id=OuterRef("order_id"),
                line_item_id=OuterRef("shopify_line_item_id"),
            )
            .values("order_id", "line_item_id")
            .annotate(total=Sum("quantity"))
            .values("total")[:1]
        )
        # REQ-DMG-008 (corrected, evaluator-active Phase 2.8a FAIL fix):
        # damaged_exchange SKUs are realistically still linked to their
        # ORIGINAL PurchaseOrder (they were already ordered once, then came
        # back damaged) — the original assumption that this view needed no
        # code change was wrong. Admit damaged_exchange LineItems regardless
        # of linkage, same exception as _reorder_candidate_filter(). Kept as
        # an inline .exclude() (not a call to _reorder_candidate_filter())
        # because this view's base filter is `sku__in=requested`, not
        # `purchase_status__in=[...]` — it never restricted eligibility by
        # purchase_status at all, only by linkage.
        li_qs = (
            LineItem.objects.filter(sku__in=requested)
            .exclude(
                Q(purchase_orders__isnull=False)
                & ~Q(purchase_status="damaged_exchange")
            )
            .annotate(
                refunded_qty=Coalesce(
                    Subquery(refund_sum_sq, output_field=IntegerField()),
                    0,
                )
            )
            .values("sku", "title", "quantity", "refunded_qty")
        )
        found_map: dict[str, dict] = {}
        for row in li_qs:
            net = max((row["quantity"] or 0) - row["refunded_qty"], 0)
            if net == 0:
                continue
            sku = row["sku"]
            if sku not in found_map:
                found_map[sku] = {"sku": sku, "title": row["title"] or "", "total_quantity": 0}
            found_map[sku]["total_quantity"] += net
        unknown_skus = [s for s in skus if s not in found_map]

        if unknown_skus:
            return Response(
                {
                    "warning": f"{len(unknown_skus)} SKU(s) not found in unordered line items.",
                    "unknown_skus": unknown_skus,
                }
            )

        # All SKUs are valid → return Excel binary
        skus_data = [
            {
                "sku": row["sku"],
                "title": row["title"] or "",
                "total_quantity": row["total_quantity"] or 0,
            }
            for row in found_map.values()
        ]
        excel_bytes = generate_order_excel(skus_data, distributor)
        today = date.today().strftime("%Y%m%d")
        filename = f"{distributor}_order_{today}.xlsx"

        response = HttpResponse(excel_bytes, content_type=EXCEL_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ---------------------------------------------------------------------------
# M4a: Upload vendor Excel file
# ---------------------------------------------------------------------------


class UploadVendorFileView(APIView):
    """
    POST /api/purchase-orders/upload-vendor-file/

    Multipart: distributor (booxen|kyobo) + file (.xlsx/.xls)
    Parses the Excel file and upserts VendorComparison records.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    # @MX:WARN: [AUTO] Complex branch count for Excel parsing + upsert logic
    # @MX:REASON: Multiple validation paths (file ext, distributor, parse errors, upsert) exceed branch threshold

    def post(self, request) -> Response:
        distributor = request.data.get("distributor")
        uploaded_file = request.FILES.get("file")

        if not distributor or distributor not in VENDOR_FILE_DISTRIBUTORS:
            return Response(
                {"detail": f"distributor must be one of: {sorted(VENDOR_FILE_DISTRIBUTORS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not uploaded_file:
            return Response(
                {"detail": "file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file extension
        filename = uploaded_file.name or ""
        if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
            return Response(
                {"detail": "Invalid file format. Only .xlsx and .xls are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_bytes = uploaded_file.read()
            parsed_rows = parse_vendor_excel(file_bytes, distributor)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        upserted_skus = []
        for row in parsed_rows:
            sku = row["sku"]
            available = row["available"]
            price = Decimal(str(row["price"])) if row["price"] is not None else None
            stock = row.get("stock")
            returnable = row.get("returnable")
            vendor_status = row.get("status")
            arrival = row.get("arrival")
            publisher = row.get("publisher")
            ordered_qty = row.get("ordered_qty")
            raw_total = row.get("total_price")
            total_price = Decimal(str(raw_total)) if raw_total is not None else None

            if distributor == "booxen":
                defaults = {
                    "available": available,
                    "price": price,
                    "stock": stock,
                    "returnable": returnable,
                    "status": vendor_status,
                    "arrival": arrival,
                }
                BooxenData.objects.update_or_create(sku=sku, defaults=defaults)
            elif distributor == "yes24":
                raw_list_price = row.get("list_price")
                list_price = Decimal(str(raw_list_price)) if raw_list_price is not None else None
                defaults = {
                    "price": price,
                    "list_price": list_price,
                    "status": vendor_status,
                }
                Yes24Data.objects.update_or_create(sku=sku, defaults=defaults)
            else:  # kyobo
                defaults = {
                    "available": available,
                    "price": price,
                    "stock": stock,
                    "returnable": returnable,
                    "status": vendor_status,
                    "publisher": publisher,
                    "ordered_qty": ordered_qty,
                    "total_price": total_price,
                }
                KyoboData.objects.update_or_create(sku=sku, defaults=defaults)
            upserted_skus.append(sku)

        return Response(
            {
                "parsed_count": len(upserted_skus),
                "distributor": distributor,
            }
        )


# ---------------------------------------------------------------------------
# M4b: Run comparison — match unordered LineItems with vendor data
# ---------------------------------------------------------------------------


class RunComparisonView(APIView):
    """
    POST /api/purchase-orders/run-comparison/

    Runs auto_select_distributor for every SKU that has unordered LineItems,
    saves the result back to VendorComparison, and returns the matched data.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        refund_sum_sq = (
            Refund.objects.filter(
                order_id=OuterRef("order_id"),
                line_item_id=OuterRef("shopify_line_item_id"),
            )
            .values("order_id", "line_item_id")
            .annotate(total=Sum("quantity"))
            .values("total")[:1]
        )

        line_items = (
            _reorder_candidate_filter(LineItem.objects.filter(sku__isnull=False))
            .annotate(
                refunded_qty=Coalesce(
                    Subquery(refund_sum_sq, output_field=IntegerField()),
                    0,
                )
            )
            .select_related("order")
        )

        # Group unordered LineItems by SKU
        sku_data: dict[str, dict] = {}
        for li in line_items:
            net_qty = max((li.quantity or 0) - li.refunded_qty, 0)
            if net_qty == 0:
                continue
            sku = li.sku
            if sku not in sku_data:
                sku_data[sku] = {"total_qty": 0, "line_items": [], "title": li.title or ""}
            sku_data[sku]["total_qty"] += net_qty
            order = li.order
            order_name = order.name or (f"#{order.order_number}" if order.order_number else None)
            sku_data[sku]["line_items"].append(
                {"id": li.pk, "order_name": order_name, "quantity": net_qty}
            )

        if not sku_data:
            return Response({"count": 0, "results": []})

        all_skus = list(sku_data.keys())

        rules = list(DistributorVendorRule.objects.values_list("publisher_name", "distributor"))

        wstock_map: dict[str, dict[str, int]] = {}
        for s in WarehouseStock.objects.filter(isbn__in=all_skus):
            wstock_map.setdefault(s.isbn, {})
            wstock_map[s.isbn][s.location] = s.quantity

        bs_map: dict[str, BooxenData] = {
            bd.sku: bd for bd in BooxenData.objects.filter(sku__in=all_skus)
        }
        ky_map: dict[str, KyoboData] = {
            kd.sku: kd for kd in KyoboData.objects.filter(sku__in=all_skus)
        }

        results = []
        for sku, data in sku_data.items():
            bs = bs_map.get(sku)
            ky = ky_map.get(sku)
            total_qty = data["total_qty"]
            stocks = wstock_map.get(sku, {})

            if bs is not None or ky is not None:
                vc_ns = SimpleNamespace(
                    booxen_price=bs.price if bs else None,
                    booxen_stock=bs.stock if bs else None,
                    booxen_returnable=bs.returnable if bs else None,
                    booxen_status=bs.status if bs else None,
                    kyobo_price=ky.price if ky else None,
                    kyobo_stock=ky.stock if ky else None,
                    kyobo_returnable=ky.returnable if ky else None,
                    kyobo_status=ky.status if ky else None,
                    kyobo_publisher=ky.publisher if ky else None,
                )
                sel = auto_select_distributor(
                    vc=vc_ns,
                    total_qty=total_qty,
                    korea_stock=stocks.get("korea", 0),
                    ca_stock=stocks.get("ca", 0),
                    nj_stock=stocks.get("nj", 0),
                    vendor_rules=rules,
                )

                # Save comparison result back to VendorComparison
                vc_obj, _ = VendorComparison.objects.get_or_create(sku=sku)
                vc_obj.selected_distributor = sel["selected_distributor"]
                vc_obj.candidate_basis = sel["candidate_basis"]
                vc_obj.price_diff = sel["price_diff"]
                vc_obj.price_diff_alert = sel["price_diff_alert"]
                vc_obj.save()

                # Confirmed price on LineItem
                now = timezone.now()
                selected = sel["selected_distributor"]
                if selected == "booxen":
                    confirmed_price = bs.price if bs else None
                    confirmed_dist = "booxen"
                elif selected == "kyobo":
                    confirmed_price = ky.price if ky else None
                    confirmed_dist = "kyobo"
                else:
                    confirmed_price = None
                    confirmed_dist = selected

                li_ids = [li["id"] for li in data["line_items"]]
                LineItem.objects.filter(pk__in=li_ids).update(
                    confirmed_price=confirmed_price,
                    confirmed_distributor=confirmed_dist,
                    confirmed_at=now,
                )

                results.append({
                    "sku": sku,
                    "title": data["title"],
                    "total_qty": total_qty,
                    "line_items": data["line_items"],
                    "booxen_available": bs.available if bs else None,
                    "booxen_price": str(bs.price) if bs and bs.price is not None else None,
                    "booxen_stock": bs.stock if bs else None,
                    "kyobo_available": ky.available if ky else None,
                    "kyobo_price": str(ky.price) if ky and ky.price is not None else None,
                    "kyobo_stock": ky.stock if ky else None,
                    "selected_distributor": sel["selected_distributor"],
                    "candidate_basis": sel["candidate_basis"],
                    "price_diff": str(sel["price_diff"]) if sel["price_diff"] is not None else None,
                    "price_diff_alert": sel["price_diff_alert"],
                    "confirmed_price": str(confirmed_price) if confirmed_price is not None else None,
                    "confirmed_distributor": confirmed_dist,
                })
            else:
                results.append({
                    "sku": sku,
                    "title": data["title"],
                    "total_qty": total_qty,
                    "line_items": data["line_items"],
                    "booxen_available": None,
                    "booxen_price": None,
                    "booxen_stock": None,
                    "kyobo_available": None,
                    "kyobo_price": None,
                    "kyobo_stock": None,
                    "selected_distributor": None,
                    "candidate_basis": None,
                    "price_diff": None,
                    "price_diff_alert": None,
                    "confirmed_price": None,
                    "confirmed_distributor": None,
                })

        return Response({"count": len(results), "results": results})


# ---------------------------------------------------------------------------
# M4c: Vendor comparison list (legacy — full VendorComparison records)
# ---------------------------------------------------------------------------


class VendorComparisonView(APIView):
    """
    GET /api/purchase-orders/comparison/

    Returns all VendorComparison records.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        comparisons = list(VendorComparison.objects.all().order_by("sku"))
        all_skus = [vc.sku for vc in comparisons]

        # Pre-fetch vendor data from the new split tables
        bs_map: dict[str, BooxenData] = {
            bd.sku: bd for bd in BooxenData.objects.filter(sku__in=all_skus)
        }
        ky_map: dict[str, KyoboData] = {
            kd.sku: kd for kd in KyoboData.objects.filter(sku__in=all_skus)
        }

        # Pre-fetch data for auto-selection (single queries, not per-row)
        rules = list(DistributorVendorRule.objects.values_list("publisher_name", "distributor"))
        all_stocks = WarehouseStock.objects.all()
        stock_map: dict[str, dict[str, int]] = {}
        for s in all_stocks:
            stock_map.setdefault(s.isbn, {"korea": 0, "ca": 0, "nj": 0})
            stock_map[s.isbn][s.location] = s.quantity

        total_qty_qs = (
            LineItem.objects
            .filter(purchase_orders__isnull=True, sku__isnull=False)
            .values("sku")
            .annotate(total=Sum("quantity"))
        )
        qty_by_sku: dict[str, int] = {row["sku"]: row["total"] or 0 for row in total_qty_qs}

        results = []
        for vc in comparisons:
            isbn = vc.sku
            bs = bs_map.get(isbn)
            ky = ky_map.get(isbn)
            total_qty = qty_by_sku.get(isbn, 0)
            wstock = stock_map.get(isbn, {"korea": 0, "ca": 0, "nj": 0})

            vc_ns = SimpleNamespace(
                booxen_price=bs.price if bs else None,
                booxen_stock=bs.stock if bs else None,
                booxen_returnable=bs.returnable if bs else None,
                booxen_status=bs.status if bs else None,
                kyobo_price=ky.price if ky else None,
                kyobo_stock=ky.stock if ky else None,
                kyobo_returnable=ky.returnable if ky else None,
                kyobo_status=ky.status if ky else None,
                kyobo_publisher=ky.publisher if ky else None,
            )
            result = auto_select_distributor(
                vc=vc_ns,
                total_qty=total_qty,
                korea_stock=wstock["korea"],
                ca_stock=wstock["ca"],
                nj_stock=wstock["nj"],
                vendor_rules=rules,
            )
            vc.selected_distributor = result["selected_distributor"]
            vc.candidate_basis = result["candidate_basis"]
            vc.price_diff = result["price_diff"]
            vc.price_diff_alert = result["price_diff_alert"]
            vc.save(
                update_fields=[
                    "selected_distributor", "candidate_basis",
                    "price_diff", "price_diff_alert", "updated_at",
                ]
            )

            # Serialize booxen_returnable as "가능"/"불가"/null
            bs_returnable = bs.returnable if bs else None
            if bs_returnable is True:
                bs_returnable_display = "가능"
            elif bs_returnable is False:
                bs_returnable_display = "불가"
            else:
                bs_returnable_display = None

            # Serialize kyobo_returnable as "Y"/"N"/null
            ky_returnable = ky.returnable if ky else None
            if ky_returnable is True:
                ky_returnable_display = "Y"
            elif ky_returnable is False:
                ky_returnable_display = "N"
            else:
                ky_returnable_display = None

            results.append(
                {
                    "sku": vc.sku,
                    "booxen_available": bs.available if bs else None,
                    "booxen_price": str(bs.price) if bs and bs.price is not None else None,
                    "booxen_stock": bs.stock if bs else None,
                    "booxen_returnable": bs_returnable_display,
                    "booxen_status": bs.status if bs else None,
                    "booxen_arrival": bs.arrival if bs else None,
                    "kyobo_available": ky.available if ky else None,
                    "kyobo_price": str(ky.price) if ky and ky.price is not None else None,
                    "kyobo_stock": ky.stock if ky else None,
                    "kyobo_returnable": ky_returnable_display,
                    "kyobo_status": ky.status if ky else None,
                    "kyobo_publisher": ky.publisher if ky else None,
                    "kyobo_ordered_qty": ky.ordered_qty if ky else None,
                    "kyobo_total_price": (
                        str(ky.total_price) if ky and ky.total_price is not None else None
                    ),
                    "selected_distributor": vc.selected_distributor,
                    "candidate_basis": vc.candidate_basis,
                    "price_diff": str(vc.price_diff) if vc.price_diff is not None else None,
                    "price_diff_alert": vc.price_diff_alert,
                }
            )
        return Response({"count": len(results), "results": results})


# ---------------------------------------------------------------------------
# M5: Confirm orders
# ---------------------------------------------------------------------------


class ConfirmOrderView(APIView):
    """
    POST /api/purchase-orders/confirm/

    Body: {"items": [{"sku": str, "distributor": str, "quantity": int, "unit_price": str,
                      "purchase_status": str (optional), "note": str|null (optional)}]}

    Creates PurchaseOrder records and links unordered LineItems via M2M.
    Also updates LineItem fields: confirmed_distributor, purchase_status (if provided),
    note (if key present and non-empty, or null to clear).
    Uses @transaction.atomic to prevent partial writes.

    SPEC-ORDER-012 REQ-RTS-003a/004: recomputes every affected Order's
    status/ready_to_ship aggregates once per request after the loop above.

    # @MX:WARN: [AUTO] Atomic transaction with select_for_update — potential lock contention under high concurrency
    # @MX:REASON: select_for_update() needed to prevent double-linking of LineItems; deadlock risk if multiple confirm requests overlap
    """

    # @MX:ANCHOR: [AUTO] Public confirm endpoint — fan_in >= 3 (router, tests, frontend)
    # @MX:REASON: Central purchase order confirmation entry point; field update logic must stay consistent with REQ-CON-012/022/032

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        items = request.data.get("items")
        if not items:
            return Response(
                {"detail": "items must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_ids = []
        # SPEC-ORDER-012 REQ-RTS-003a/004: order_ids touched across every
        # SKU in this request, recomputed once after the loop — not once
        # per SKU (N+1 avoidance, same discipline as
        # _apply_logistics_transition's affected_order_ids).
        affected_order_ids: set[int] = set()

        try:
            with transaction.atomic():
                for item in items:
                    sku = item.get("sku")
                    dist = item.get("distributor")
                    qty = item.get("quantity")
                    raw_price = item.get("unit_price")
                    # REQ-CON-022: optional purchase_status per item
                    purchase_status = item.get("purchase_status")
                    # REQ-CON-032/033/034: use sentinel to distinguish absent vs explicit null
                    _MISSING = object()
                    note_value = item.get("note", _MISSING)
                    note_key_present = "note" in item

                    if not sku or qty is None:
                        raise ValueError("sku and quantity are required for each item.")

                    # REQ-CON-013: reject empty/whitespace-only distributor; allow any non-empty free text
                    if not dist or not dist.strip():
                        raise ValueError("distributor must not be empty.")

                    # REQ-CON-022: validate purchase_status if provided
                    if purchase_status is not None:
                        valid_ps = [c[0] for c in LineItem.PURCHASE_STATUS_CHOICES]
                        if purchase_status not in valid_ps:
                            raise ValueError(
                                f"Invalid purchase_status: '{purchase_status}'. "
                                f"Valid choices: {valid_ps}"
                            )

                    # Find unordered LineItems for this SKU with a lock.
                    # REQ-DMG-005B: also admit LineItems whose purchase_status
                    # is "damaged_exchange", regardless of existing
                    # PurchaseOrder linkage — expressed as a single .exclude()
                    # call (NOT EXISTS subquery) so the M2M join never
                    # duplicates rows, matching _reorder_candidate_filter's
                    # approach for the other 4 sites.
                    unordered_lis = list(
                        LineItem.objects.filter(sku=sku)
                        .exclude(
                            Q(purchase_orders__isnull=False)
                            & ~Q(purchase_status="damaged_exchange")
                        )
                        .select_for_update()
                    )

                    if not unordered_lis:
                        # Check whether all are already linked (conflict) or none exist
                        linked = LineItem.objects.filter(sku=sku, purchase_orders__isnull=False).exists()
                        if linked:
                            # All existing LineItems for this SKU are already linked
                            raise ConflictError(f"LineItems for SKU '{sku}' are already linked to a PurchaseOrder.")
                        # No LineItems at all for this SKU
                        raise ValueError(f"No unordered LineItems found for SKU '{sku}'.")

                    # Double-link guard: the select_for_update + exclude already handles this,
                    # but verify by checking if any returned LI is somehow already linked.
                    # REQ-DMG-005B: a damaged_exchange LineItem is expected to
                    # legitimately be linked already — only flag non-damaged_exchange
                    # linked LineItems as a conflict.
                    already_linked = [
                        li for li in unordered_lis
                        if li.purchase_status != "damaged_exchange" and li.purchase_orders.exists()
                    ]
                    if already_linked:
                        raise ConflictError(f"Some LineItems for SKU '{sku}' are already linked.")

                    unit_price = None
                    if raw_price is not None:
                        try:
                            unit_price = Decimal(str(raw_price))
                        except InvalidOperation:
                            raise ValueError(f"Invalid unit_price: {raw_price}")

                    # Determine title from first LineItem
                    title = unordered_lis[0].title or sku

                    po = PurchaseOrder.objects.create(
                        sku=sku,
                        title=title,
                        distributor=dist,
                        quantity=qty,
                        unit_price=unit_price,
                        status="pending",
                    )
                    po.line_items.add(*unordered_lis)
                    created_ids.append(po.pk)

                    # REQ-CON-012: update confirmed_distributor on all linked LineItems
                    update_fields = ["confirmed_distributor", "confirmed_price"]
                    for li in unordered_lis:
                        li.confirmed_distributor = dist
                        li.confirmed_price = unit_price

                    # REQ-DMG-006: auto-reset damaged_exchange -> unordered for this
                    # confirmation batch, applied before the explicit purchase_status
                    # override below so a client-supplied value always wins (REQ-CON-022).
                    damaged_exchange_reset = False
                    for li in unordered_lis:
                        if li.purchase_status == "damaged_exchange":
                            li.purchase_status = "unordered"
                            damaged_exchange_reset = True
                    if damaged_exchange_reset:
                        update_fields.append("purchase_status")

                    # REQ-CON-022/023: update purchase_status only when explicitly provided
                    if purchase_status is not None:
                        for li in unordered_lis:
                            li.purchase_status = purchase_status
                        if "purchase_status" not in update_fields:
                            update_fields.append("purchase_status")

                    # REQ-CON-032/033/034: handle note field — migrated to LineItemNote (SPEC-ORDER-010)
                    if note_key_present:
                        note_raw = item["note"]
                        if note_raw is not None and note_raw != "":
                            # REQ-CON-032: non-empty string → create LineItemNote
                            for li in unordered_lis:
                                LineItemNote.objects.create(
                                    line_item=li,
                                    content=note_raw,
                                    author=None,
                                    assignee="발주",
                                )
                        # REQ-CON-033: empty string "" → skip
                        # REQ-CON-034: null → no longer clears (field removed from LineItem)

                    LineItem.objects.bulk_update(unordered_lis, update_fields)
                    affected_order_ids.update(li.order_id for li in unordered_lis)

                # SPEC-ORDER-012 REQ-RTS-003a/004/004a: one recompute call
                # for the whole request, regardless of how many SKUs/items
                # were processed above.
                _recompute_order_aggregates(affected_order_ids)

        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"created_count": len(created_ids), "purchase_order_ids": created_ids},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Daily Review: Download + Upload
# ---------------------------------------------------------------------------

_DISTRIBUTOR_CODE_TO_LABEL: dict[str, str] = {
    "booxen": "북센",
    "kyobo": "교보",
    "choeumgoyuk": "처음교육",
    "agape": "타출판사",
    "sungseoyunion": "타출판사",
    "warehouse": "재고",
    "warehouse_west": "재고(서부)",
    "check_required": "확인필요",
}

_OTHER_PUBLISHER_MEMO: dict[str, str] = {
    "agape": "아가페",
    "sungseoyunion": "성서유니온",
}


class DailyReviewExcelView(APIView):
    """
    GET /api/purchase-orders/daily-review-excel/

    Generates and downloads a 22-column Daily Order Review Excel file
    containing all unordered LineItems with joined vendor/warehouse data.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> HttpResponse:
        refund_sum_sq = (
            Refund.objects.filter(
                order_id=OuterRef("order_id"),
                line_item_id=OuterRef("shopify_line_item_id"),
            )
            .values("order_id", "line_item_id")
            .annotate(total=Sum("quantity"))
            .values("total")[:1]
        )

        line_items = (
            _reorder_candidate_filter(LineItem.objects.filter(sku__isnull=False))
            .annotate(
                refunded_qty=Coalesce(
                    Subquery(refund_sum_sq, output_field=IntegerField()),
                    0,
                )
            )
            .select_related("order")
            .prefetch_related("notes")
            .order_by("order__order_number")
        )

        # Exclude fully refunded line items (same logic as UnorderedItemsView)
        line_items = [li for li in line_items if (li.quantity or 0) - li.refunded_qty > 0]

        skus = list({li.sku for li in line_items if li.sku})
        booxen_map = {bd.sku: bd for bd in BooxenData.objects.filter(sku__in=skus)}
        kyobo_map = {kd.sku: kd for kd in KyoboData.objects.filter(sku__in=skus)}

        # Real-time: vendor rules and warehouse stocks for auto-selection
        vendor_rules = list(DistributorVendorRule.objects.values_list("publisher_name", "distributor"))
        stock_map: dict[str, dict[str, int]] = {}
        for ws_obj in WarehouseStock.objects.filter(isbn__in=skus):
            stock_map.setdefault(ws_obj.isbn, {"korea": 0, "ca": 0, "nj": 0})
            stock_map[ws_obj.isbn][ws_obj.location] = ws_obj.quantity

        # Total qty per SKU for warehouse stock comparison
        qty_by_sku: dict[str, int] = {}
        for li in line_items:
            qty_by_sku[li.sku] = qty_by_sku.get(li.sku, 0) + (li.quantity or 0)

        rows = []
        for li in line_items:
            sku = li.sku
            bd = booxen_map.get(sku)
            kd = kyobo_map.get(sku)

            wstock = stock_map.get(sku, {"korea": 0, "ca": 0, "nj": 0})

            bs_price = float(bd.price) if bd and bd.price is not None else None
            ky_price = float(kd.price) if kd and kd.price is not None else None
            price_diff: float | None = None
            price_diff_alert = False
            if bs_price is not None and ky_price is not None:
                price_diff = bs_price - ky_price
                price_diff_alert = abs(price_diff) > 3000

            # Real-time auto-selection using current rules and stocks
            vc_ns = SimpleNamespace(
                booxen_price=bd.price if bd else None,
                booxen_stock=bd.stock if bd else None,
                booxen_returnable=bd.returnable if bd else None,
                booxen_status=bd.status if bd else None,
                kyobo_price=kd.price if kd else None,
                kyobo_stock=kd.stock if kd else None,
                kyobo_returnable=kd.returnable if kd else None,
                kyobo_status=kd.status if kd else None,
                kyobo_publisher=kd.publisher if kd else None,
            )
            sel = auto_select_distributor(
                vc=vc_ns,
                total_qty=qty_by_sku.get(sku, 0),
                korea_stock=wstock["korea"],
                ca_stock=wstock["ca"],
                nj_stock=wstock["nj"],
                vendor_rules=vendor_rules,
            )

            rows.append({
                "order_name": li.order.name if li.order else "",
                "sku": sku,
                "title": li.title or "",
                "quantity": li.quantity or 0,
                "location": li.location or "",
                "note": (li.notes.first().content if li.notes.exists() else ""),
                "korea_stock": stock_map.get(sku, {}).get("korea", 0),
                "ca_stock": stock_map.get(sku, {}).get("ca", 0),
                "nj_stock": stock_map.get(sku, {}).get("nj", 0),
                "bs_price": bs_price,
                "bs_stock": bd.stock if bd else None,
                "ky_price": ky_price,
                "bs_status": bd.status if bd else None,
                "ky_stock": kd.stock if kd else None,
                "ky_status": kd.status if kd else None,
                "price_diff": price_diff,
                "bs_arrival": bd.arrival if bd else None,
                "bs_returnable": bd.returnable if bd else None,
                "ky_available": kd.available if kd else None,
                "ky_returnable": kd.returnable if kd else None,
                "price_diff_alert": price_diff_alert,
                "publisher": kd.publisher if kd else None,
                "candidate_basis": sel["candidate_basis"],
                "selected": _DISTRIBUTOR_CODE_TO_LABEL.get(sel["selected_distributor"] or "", ""),
                "other_publisher_memo": _OTHER_PUBLISHER_MEMO.get(sel["selected_distributor"] or ""),
            })

        file_bytes = generate_daily_review_excel(rows)
        today = date.today().strftime("%Y%m%d")
        filename = f"Daily_Order_Review_{today}.xlsx"

        response = HttpResponse(file_bytes, content_type=EXCEL_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# @MX:ANCHOR: [AUTO] Grouped vendor-table upsert shared by Booxen/Kyobo/Yes24Data
# @MX:REASON: Fan-in == 3 (called once per vendor table from UploadDailyReviewView.post());
# SPEC-PURCHASE-ORDER-009 REQ-PO9-001/002 batching entry point — changing its
# grouping logic affects the Bug-1-fix (legacy field preservation) invariant
# for all three vendor tables at once.
def _batch_upsert_vendor_data(model, sku_to_fields: dict) -> None:
    """
    Batch-upsert vendor rows keyed by SKU.

    Replaces a per-SKU `Model.objects.update_or_create(sku=sku, defaults=...)`
    loop with grouped `bulk_create(update_conflicts=True, ...)` calls
    (SPEC-PURCHASE-ORDER-009 REQ-PO9-001).

    `sku_to_fields` maps sku -> a dict of only the fields that should be
    written for that row (same convention `update_or_create`'s `defaults`
    used) — a field is omitted entirely when its source column did not exist
    in the uploaded file, so it is never overwritten (SPEC-PURCHASE-ORDER-008
    Bug-1-fix). Because `bulk_create(update_conflicts=True)` requires every
    object in one call to share the same `update_fields`, rows are grouped by
    their field-presence signature and one batch call is issued per group
    (REQ-PO9-002) — in practice this is a small, fixed number of groups
    (legacy vs new-template columns present, price-included vs price-omitted),
    never one group per row.

    Note: `unique_fields` is intentionally NOT passed to `bulk_create()` —
    this project's DB backend is MySQL, whose native `INSERT ... ON DUPLICATE
    KEY UPDATE` targets whichever unique constraint conflicts without needing
    it specified, and Django's MySQL backend reports
    `supports_update_conflicts_with_target = False`; passing `unique_fields`
    there raises `NotSupportedError` at runtime.
    """
    if not sku_to_fields:
        return

    groups: dict[frozenset, list[str]] = defaultdict(list)
    for sku, fields in sku_to_fields.items():
        groups[frozenset(fields.keys())].append(sku)

    for signature, skus in groups.items():
        objs = [model(sku=sku, **sku_to_fields[sku]) for sku in skus]
        if not signature:
            # Nothing to update for this group — only ensure the row exists
            # (mirrors update_or_create(defaults={}) leaving an existing
            # row's fields untouched).
            model.objects.bulk_create(objs, ignore_conflicts=True)
        else:
            model.objects.bulk_create(
                objs,
                update_conflicts=True,
                update_fields=list(signature),
            )


class UploadDailyReviewView(APIView):
    """
    POST /api/purchase-orders/upload-daily-review/

    Multipart: file (.xlsx)
    Parses the Daily Review Excel file (legacy self-generated format or the
    external "Daily Order Review Template", auto-detected — SPEC-PURCHASE-ORDER-008),
    reads the '선택' column (Korean display name), and confirms purchase
    orders for rows with a valid, recognized selection. For non-warehouse
    distributor codes (booxen/kyobo/yes24) this creates a new PurchaseOrder
    with status="confirmed" — this upload IS the distributor's confirmed
    response, unlike ConfirmOrderView's status="pending" staging step.
    Independently of that selection, every row with a non-empty SKU also
    syncs BooxenData/KyoboData/Yes24Data (Part B — REQ-PO8-014).
    Rows with empty or unrecognized '선택' are skipped from PO/CS/warehouse
    confirmation only.

    SPEC-ORDER-012 REQ-RTS-003a/004: recomputes every Order status/
    ready_to_ship aggregate touched by any of the three branches, once per
    upload request.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    # @MX:WARN: [AUTO] High branch count: per-row vendor upsert (Booxen/Kyobo/Yes24)
    # plus CS/warehouse/PO confirmation logic
    # @MX:REASON: Mirrors UploadVendorFileView's parsing/upsert complexity;
    # SPEC-PURCHASE-ORDER-008 explicitly scoped out extracting a shared helper

    def post(self, request) -> Response:
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded.name or ""
        if not filename.endswith(".xlsx"):
            return Response(
                {"detail": "Invalid file format. Only .xlsx is supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_bytes = uploaded.read()
            parsed_rows = parse_daily_review_excel(file_bytes)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Deduplicate by SKU — last row wins if same ISBN appears multiple
        # times. Part B (vendor-table sync, below) stays SKU-only: it's a
        # per-book attribute (stock/price data), not an order-specific one.
        sku_map: dict[str, dict] = {}
        # REQ-PO8-018: Part A (CS/warehouse/non-warehouse confirmation, the
        # main loop further below) resolves independently per
        # (order_name, sku) pair instead of collapsing by SKU alone — bug
        # fix for real production data where two different orders sharing
        # one SKU with DIFFERENT '선택' decisions silently lost one order's
        # decision to the other's (the later row in the file won, and BOTH
        # orders' LineItems ended up linked to the winning row's
        # PurchaseOrder). Last-row-wins within the SAME (name, sku) pair is
        # still fine — that is a genuine duplicate row, not a cross-order
        # collision.
        pair_map: dict[tuple[str, str], dict] = {}
        for row in parsed_rows:
            sku_map[row["sku"]] = row
            pair_map[(row.get("name") or "", row["sku"])] = row

        confirmed_count = 0
        skipped_count = 0
        errors: list[dict] = []
        confirmed_by_distributor: dict[str, list] = {}

        # Warehouse distributor code → location mapping (legacy location-suffixed codes)
        _WAREHOUSE_LOCATION_MAP: dict[str, str] = {
            "warehouse_korea": "korea",
            "warehouse_ca": "ca",
            "warehouse_nj": "nj",
        }
        # REQ-PO8-008: new template's generic 'warehouse' code resolves location
        # from the row's note value (Status column) instead of a suffixed code.
        _WAREHOUSE_NOTE_LOCATION_MAP: dict[str, str] = {
            "한국재고": "korea",
            "Fullerton재고": "ca",
            "NJ재고": "nj",
        }

        try:
            with transaction.atomic():
                # ---------------------------------------------------------
                # Pass 1 (Python only, no DB writes): build the vendor-table
                # field dicts for every SKU (SPEC-PURCHASE-ORDER-009
                # REQ-PO9-001/002). Field-presence semantics are byte-for-byte
                # identical to the original per-SKU update_or_create() calls —
                # only *when* the DB write happens has changed.
                # ---------------------------------------------------------
                booxen_field_map: dict[str, dict] = {}
                yes24_field_map: dict[str, dict] = {}
                kyobo_field_map: dict[str, dict] = {}
                booxen_price_needed: set[str] = set()
                kyobo_price_needed: set[str] = set()
                yes24_price_needed: set[str] = set()

                for sku, item in sku_map.items():
                    # Part B (REQ-PO8-014): vendor-table sync — runs for every row
                    # with a non-empty SKU, independent of '선택'. Price fields are
                    # omitted from defaults when the row has no value so a blank
                    # price never overwrites (and defeats) the price fallback the
                    # confirmation logic below performs for this same SKU (AC-006).
                    #
                    # Bug-1-fix: every other Part B field is only added to
                    # `defaults` when its key is present in `item` — i.e. when
                    # parse_daily_review_excel() found the source column in
                    # this file's header. A legacy-format upload (whose header
                    # lacks these columns under these names) therefore never
                    # writes None/False over an existing vendor-table value.
                    booxen_defaults: dict = {}
                    if "bs_stock" in item:
                        booxen_defaults["stock"] = item["bs_stock"]
                    if "bs_status" in item:
                        booxen_defaults["status"] = item["bs_status"]
                    if "bs_arrival" in item:
                        booxen_defaults["arrival"] = item["bs_arrival"]
                    if "bs_returnable" in item:
                        booxen_defaults["returnable"] = item["bs_returnable"]
                    if "bs_available" in item:
                        booxen_defaults["available"] = item["bs_available"]
                    if item.get("bs_price") is not None:
                        booxen_defaults["price"] = Decimal(str(item["bs_price"]))
                    else:
                        booxen_price_needed.add(sku)
                    booxen_field_map[sku] = booxen_defaults

                    yes24_defaults: dict = {}
                    if "yes24_status" in item:
                        yes24_defaults["status"] = item["yes24_status"]
                    if item.get("yes24_price") is not None:
                        yes24_defaults["price"] = Decimal(str(item["yes24_price"]))
                    else:
                        yes24_price_needed.add(sku)
                    yes24_field_map[sku] = yes24_defaults

                    kyobo_defaults: dict = {}
                    if "ky_stock" in item:
                        kyobo_defaults["stock"] = item["ky_stock"]
                    if "ky_available" in item:
                        kyobo_defaults["available"] = item["ky_available"]
                    if "ky_status" in item:
                        kyobo_defaults["status"] = item["ky_status"]
                    if "ky_returnable" in item:
                        kyobo_defaults["returnable"] = item["ky_returnable"]
                    if "ky_publisher" in item:
                        kyobo_defaults["publisher"] = item["ky_publisher"]
                    if item.get("ky_price") is not None:
                        kyobo_defaults["price"] = Decimal(str(item["ky_price"]))
                    else:
                        kyobo_price_needed.add(sku)
                    if "ky_list_price" in item:
                        raw_list_price = item["ky_list_price"]
                        kyobo_defaults["list_price"] = (
                            Decimal(str(raw_list_price)) if raw_list_price is not None else None
                        )
                    kyobo_field_map[sku] = kyobo_defaults

                # REQ-PO9-001/002: one grouped bulk upsert per vendor table
                # instead of one update_or_create() per SKU per table.
                _batch_upsert_vendor_data(BooxenData, booxen_field_map)
                _batch_upsert_vendor_data(Yes24Data, yes24_field_map)
                _batch_upsert_vendor_data(KyoboData, kyobo_field_map)

                # Vendor price fallback (used below when the Excel row itself
                # has no price): fetched in bulk once per vendor table,
                # instead of a per-SKU .filter(sku=sku).first() inside the
                # loop. Reading after the batch upsert above reproduces the
                # original per-SKU ordering (that SKU's own vendor sync,
                # which never touches "price" when the Excel row has none,
                # already ran before this same SKU's fallback read).
                booxen_price_by_sku = (
                    {b.sku: b.price for b in BooxenData.objects.filter(sku__in=booxen_price_needed)}
                    if booxen_price_needed
                    else {}
                )
                kyobo_price_by_sku = (
                    {k.sku: k.price for k in KyoboData.objects.filter(sku__in=kyobo_price_needed)}
                    if kyobo_price_needed
                    else {}
                )
                yes24_price_by_sku = (
                    {y.sku: y.price for y in Yes24Data.objects.filter(sku__in=yes24_price_needed)}
                    if yes24_price_needed
                    else {}
                )

                # REQ-PO8-018: Order.name resolution for the (order_name,
                # sku)-scoped main loop below. Mirrors
                # _apply_logistics_transition / _process_outbound_rows'
                # oldest-pk-wins tie-break — Order.name carries no
                # uniqueness constraint (unique_together is
                # (shopify_order_id, store_type)), so several orders may
                # share a name.
                order_names = {name for name, _ in pair_map if name}
                orders_by_name: dict[str, Order] = {}
                if order_names:
                    for candidate in Order.objects.filter(name__in=order_names).order_by("pk"):
                        orders_by_name.setdefault(candidate.name, candidate)

                # REQ-PO9-004 (REQ-PO8-018 update): a single filter query for
                # every eligible LineItem across all resolved orders, grouped
                # by (order_id, sku) in Python — an order-aware replacement
                # for the previous SKU-only grouping that let one order's
                # row apply its confirmation to every other order sharing
                # the same SKU.
                all_skus = list(sku_map.keys())
                lineitems_by_key: dict[tuple[int, str], list] = defaultdict(list)
                if orders_by_name:
                    order_ids = [o.id for o in orders_by_name.values()]
                    for li in (
                        _reorder_candidate_filter(
                            LineItem.objects.filter(sku__in=all_skus, order_id__in=order_ids)
                        ).select_for_update()
                    ):
                        lineitems_by_key[(li.order_id, li.sku)].append(li)

                # REQ-PO9-005: LineItemNote instances collected here and
                # inserted with a single bulk_create() after the loop,
                # instead of one create() call per LineItem.
                pending_notes: list = []
                # Deferred LineItem field updates, grouped by which fields
                # each branch touches — bulk_update() requires the same
                # field list for every object in one call, so one
                # bulk_update() per branch replaces one per SKU.
                cs_status_updates: list = []
                warehouse_li_updates: list = []
                nonwarehouse_li_updates: list = []
                # REQ-PO9-006: (sku, location, total_qty) entries for the
                # warehouse floor-at-0 deduction, applied as a single
                # batched Case/When update after the loop — see the
                # investigation note below the loop for why this is safe.
                warehouse_stock_entries: list[tuple[str, str, int]] = []
                # REQ-PO9-007 (REQ-PO8-018 update): non-warehouse-branch
                # LineItems, grouped by (sku, distributor) rather than by
                # sku alone — this is what lets the PurchaseOrder-creation
                # step below batch multiple orders that genuinely agree on
                # the same distributor into one PurchaseOrder (preserving
                # the pre-existing batching behavior), while no longer
                # letting a DIFFERENT order's warehouse/CS/other-distributor
                # choice for the same SKU get folded into that group.
                # `po_creates` is built from this dict after the loop; see
                # the investigation note below the loop for the M2M-linking
                # strategy.
                po_creates: list = []
                po_group_lineitems: dict[tuple[str, str], list] = defaultdict(list)

                for (name, sku), item in pair_map.items():
                    order = orders_by_name.get(name) if name else None
                    if order is None:
                        # Blank order-name cell, or a name that does not
                        # match any Order — same skip convention as
                        # _apply_logistics_transition / _process_outbound_rows.
                        skipped_count += 1
                        continue

                    distributor_code = item["distributor"]
                    note = item.get("note")
                    note_type = item.get("note_type")

                    unordered_lis = lineitems_by_key.get((order.id, sku), [])

                    if not unordered_lis:
                        skipped_count += 1
                        continue

                    title = unordered_lis[0].title or sku
                    total_qty = sum(li.quantity or 0 for li in unordered_lis)

                    if note_type and not distributor_code:
                        # CS case: update purchase_status and create note
                        new_status = _NOTE_TYPE_STATUS_MAP[note_type]
                        for li in unordered_lis:
                            li.purchase_status = new_status
                        cs_status_updates.extend(unordered_lis)
                        if note is not None:
                            for li in unordered_lis:
                                pending_notes.append(
                                    LineItemNote(
                                        line_item=li,
                                        content=note,
                                        author=None,
                                        note_type=note_type,
                                        assignee="CS",
                                    )
                                )
                        confirmed_count += 1
                        continue

                    if distributor_code is None:
                        # REQ-PO8-011: empty or unrecognized '선택' (e.g. 합계/total/
                        # check legend values) — skip PO/CS/warehouse confirmation.
                        # Vendor sync above already ran regardless.
                        skipped_count += 1
                        continue

                    is_warehouse = (
                        distributor_code in _WAREHOUSE_LOCATION_MAP
                        or distributor_code == "warehouse"
                    )
                    if is_warehouse:
                        if distributor_code == "warehouse":
                            # REQ-PO8-008: resolve location from the Status value
                            loc = _WAREHOUSE_NOTE_LOCATION_MAP.get(note or "")
                            if loc is None:
                                skipped_count += 1
                                continue
                            # The generic 'warehouse' code carries no location, so
                            # persist the resolved, location-suffixed code instead —
                            # otherwise confirmed_distributor loses the location and
                            # the frontend's 창고(한국)/창고(CA)/창고(NJ) labels (keyed
                            # on warehouse_korea/warehouse_ca/warehouse_nj) are
                            # unreachable. Only the LineItem field write uses this;
                            # stock deduction, note assignee and the response summary
                            # keep using `loc` / the original `distributor_code`.
                            resolved_distributor_code = f"warehouse_{loc}"
                        else:
                            loc = _WAREHOUSE_LOCATION_MAP[distributor_code]
                            # Already location-suffixed (legacy Excel input) — as-is.
                            resolved_distributor_code = distributor_code

                        # Deferred atomic stock deduction (floor at 0) — see
                        # REQ-PO9-006 investigation note below the loop.
                        warehouse_stock_entries.append((sku, loc, total_qty))

                        # REQ-PO5-005: Set purchase_status = "in_stock"
                        for li in unordered_lis:
                            li.purchase_status = "in_stock"
                            li.confirmed_distributor = resolved_distributor_code
                        warehouse_li_updates.extend(unordered_lis)
                        if note is not None:
                            # REQ-PO8-009: assignee determined by resolved location
                            # (also fixes legacy warehouse_ca/nj always logging 한국창고)
                            assignee = "한국창고" if loc == "korea" else "미국창고"
                            for li in unordered_lis:
                                pending_notes.append(
                                    LineItemNote(
                                        line_item=li,
                                        content=note,
                                        author=None,
                                        assignee=assignee,
                                    )
                                )

                    else:
                        # Non-warehouse: accumulate into this row's own
                        # (sku, distributor) group instead of creating a
                        # PurchaseOrder immediately (REQ-PO8-018) — the
                        # actual PurchaseOrder rows are materialized from
                        # `po_group_lineitems` after the loop, once every
                        # row's own decision has been resolved. Prefer
                        # prices from the Excel file; fall back to DB.
                        unit_price = None
                        if distributor_code == "booxen":
                            unit_price = item.get("bs_price")
                            if unit_price is None:
                                unit_price = booxen_price_by_sku.get(sku)
                        elif distributor_code == "kyobo":
                            unit_price = item.get("ky_price")
                            if unit_price is None:
                                unit_price = kyobo_price_by_sku.get(sku)
                        elif distributor_code == "yes24":
                            # REQ-PO8-010
                            unit_price = item.get("yes24_price")
                            if unit_price is None:
                                unit_price = yes24_price_by_sku.get(sku)

                        for li in unordered_lis:
                            li.confirmed_distributor = distributor_code
                            li.confirmed_price = unit_price
                            # REQ-DMG-006: auto-reset damaged_exchange -> unordered
                            # for this upload's own confirmation batch — new PO
                            # is being created/linked for this SKU right now.
                            if li.purchase_status == "damaged_exchange":
                                li.purchase_status = "unordered"
                        nonwarehouse_li_updates.extend(unordered_lis)
                        # First-processed row for a given (sku, distributor)
                        # group determines the resulting PurchaseOrder's
                        # title/unit_price — the post-loop build reads those
                        # back off group_lis[0] (already set above) instead
                        # of tracking a second per-group dict.
                        po_group_lineitems[(sku, distributor_code)].extend(unordered_lis)

                    # REQ-PO5-007: Track confirmed by distributor
                    confirmed_by_distributor.setdefault(distributor_code, []).append(
                        {"sku": sku, "title": title, "quantity": total_qty}
                    )
                    confirmed_count += 1

                # REQ-PO9-006 investigation (REQ-PO8-018 update): the
                # floor-at-0 deduction for a given WarehouseStock row
                # depends only on that row's own current `quantity` (via
                # Case/When quantity__gte=total_qty) — never on any other
                # row's value. This previously relied on sku_map's SKU-only
                # dedup to guarantee each (sku, location) pair appeared at
                # most once per upload; now that Part A resolves rows
                # independently per (order_name, sku), two DIFFERENT orders
                # can legitimately pick the SAME warehouse location for the
                # SAME sku within one upload, so entries are aggregated by
                # (sku, location) here before building the Case/When list —
                # a duplicate When clause for the same isbn+location would
                # otherwise only apply the FIRST matching entry (Case takes
                # the first true When), silently dropping the other order's
                # deduction.
                if warehouse_stock_entries:
                    aggregated_stock_entries: dict[tuple[str, str], int] = defaultdict(int)
                    for entry_sku, loc, entry_qty in warehouse_stock_entries:
                        aggregated_stock_entries[(entry_sku, loc)] += entry_qty

                    stock_filter = Q()
                    case_whens = []
                    for (entry_sku, loc), total_qty in aggregated_stock_entries.items():
                        stock_filter |= Q(isbn=entry_sku, location=loc)
                        case_whens.append(
                            When(
                                isbn=entry_sku,
                                location=loc,
                                quantity__gte=total_qty,
                                then=F("quantity") - total_qty,
                            )
                        )
                    WarehouseStock.objects.filter(stock_filter).update(
                        quantity=Case(
                            *case_whens,
                            default=Value(0),
                            output_field=IntegerField(),
                        )
                    )

                # REQ-PO9-005: single bulk_create() for every LineItemNote
                # collected across the CS and warehouse branches.
                if pending_notes:
                    LineItemNote.objects.bulk_create(pending_notes)

                # One bulk_update() per distinct field set touched, instead
                # of one per SKU.
                if cs_status_updates:
                    LineItem.objects.bulk_update(cs_status_updates, ["purchase_status"])
                if warehouse_li_updates:
                    LineItem.objects.bulk_update(
                        warehouse_li_updates, ["purchase_status", "confirmed_distributor"]
                    )
                if nonwarehouse_li_updates:
                    # REQ-DMG-006: "purchase_status" is included unconditionally
                    # (bulk_update requires one shared field list per call) — a
                    # no-op for LineItems that were never damaged_exchange.
                    LineItem.objects.bulk_update(
                        nonwarehouse_li_updates,
                        ["confirmed_distributor", "confirmed_price", "purchase_status"],
                    )

                # SPEC-ORDER-012 REQ-RTS-003a/004: one recompute call per
                # upload request, merging order_ids across all three
                # branches — not once per branch (N+1 avoidance, same
                # discipline as ConfirmOrderView).
                affected_order_ids = {
                    li.order_id
                    for li in cs_status_updates + warehouse_li_updates + nonwarehouse_li_updates
                }
                _recompute_order_aggregates(affected_order_ids)

                # REQ-PO8-018: materialize one PurchaseOrder per (sku,
                # distributor) group now that non-warehouse rows accumulate
                # by that key instead of by SKU alone — this is what
                # preserves batching for orders that genuinely agree on the
                # same distributor (quantity is the sum across every
                # LineItem in the group, spanning however many orders
                # contributed to it) while no longer letting a different
                # order's warehouse/CS/other-distributor choice for the same
                # SKU get folded in. group_lis[0] carries the
                # first-processed row's own title/confirmed_price (already
                # set in the loop above), reproducing the original per-SKU
                # first-seen-wins fallback resolution without a second dict.
                for (group_sku, group_distributor), group_lis in po_group_lineitems.items():
                    first_li = group_lis[0]
                    po_creates.append(
                        PurchaseOrder(
                            sku=group_sku,
                            title=first_li.title or group_sku,
                            distributor=group_distributor,
                            quantity=sum(li.quantity or 0 for li in group_lis),
                            unit_price=first_li.confirmed_price,
                            # Daily Review upload reflects the distributor's
                            # actual confirmed response, so the PO it creates
                            # starts "confirmed" rather than "pending" — unlike
                            # ConfirmOrderView, which stages a PO before that
                            # response exists.
                            status="confirmed",
                        )
                    )

                # REQ-PO9-007 (REQ-PO8-018 update): batch-create every
                # non-warehouse-branch PurchaseOrder in a single
                # bulk_create(), then batch-link the M2M `line_items`
                # relation through the through-table's own bulk_create()
                # instead of one `.add()` call per PO.
                #
                # Empirically verified (throwaway test against this
                # project's real MySQL backend, Django 5.1.6): objects
                # passed to PurchaseOrder.objects.bulk_create() do NOT come
                # back with `.pk` populated for multi-row batches — Django's
                # MySQL backend does not report
                # `can_return_rows_from_bulk_insert`, so there is no
                # reliable way to zip the input list against the created
                # rows by position. Falling back to a safe re-query
                # strategy instead of an ID-matching heuristic:
                #
                # 1. Capture `t_before` immediately before the bulk_create()
                #    call.
                # 2. Re-query PurchaseOrder rows by
                #    `sku__in=<this batch's SKUs>` AND
                #    `created_at__gte=t_before`, grouped by (sku,
                #    distributor) — REQ-PO8-018 update: the same SKU can now
                #    legitimately have multiple simultaneous POs to
                #    different distributors within one batch (structurally
                #    possible before too, but now the primary grouping key
                #    since `po_group_lineitems` is keyed by
                #    (sku, distributor)), so disambiguation must include
                #    distributor, not SKU alone.
                # 3. If a (sku, distributor) pair somehow yields more than
                #    one match in that narrow window (e.g. a genuinely
                #    concurrent request creating a PurchaseOrder for the
                #    same sku+distributor), keep the highest-pk (most
                #    recently inserted) row for that pair, since it is the
                #    one this call just inserted.
                #
                # This trades one extra SELECT for the batch (still O(1),
                # not O(N)) in exchange for correctness without a fragile
                # heuristic.
                if po_creates:
                    t_before_bulk_create = timezone.now()
                    PurchaseOrder.objects.bulk_create(po_creates)

                    po_skus = {group_sku for group_sku, _ in po_group_lineitems}
                    po_by_group: dict[tuple[str, str], PurchaseOrder] = {}
                    for po in PurchaseOrder.objects.filter(
                        sku__in=po_skus, created_at__gte=t_before_bulk_create
                    ):
                        group_key = (po.sku, po.distributor)
                        existing = po_by_group.get(group_key)
                        if existing is None or po.pk > existing.pk:
                            po_by_group[group_key] = po

                    through_model = PurchaseOrder.line_items.through
                    through_rows = [
                        through_model(
                            purchaseorder_id=po_by_group[group_key].pk,
                            lineitem_id=li.pk,
                        )
                        for group_key, group_lis in po_group_lineitems.items()
                        for li in group_lis
                    ]
                    if through_rows:
                        through_model.objects.bulk_create(through_rows)

        except Exception as exc:
            return Response(
                {"detail": f"처리 중 오류가 발생했습니다: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "confirmed_count": confirmed_count,
                "skipped_count": skipped_count,
                "errors": errors,
                "confirmed_by_distributor": confirmed_by_distributor,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# SPEC-ORDER-011: logistics_status uploads
# ---------------------------------------------------------------------------


class UploadVendorShipmentView(APIView):
    """
    POST /api/purchase-orders/upload-vendor-shipment/

    Multipart: file (.xlsx)
    REQ-LOGI-003/004: parses a vendor-shipment-confirmation Excel file
    ((order_name, SKU) schema — see excel_utils.parse_vendor_shipment_excel)
    and transitions matching LineItems' logistics_status from "not_shipped"
    to "shipment_confirmed". Matching rule: (Order.name, sku) exact match
    AND purchase_status != "unordered" AND logistics_status == "not_shipped"
    (REQ-LOGI-003b safety fix — SKU alone previously matched every order
    sharing that SKU; same-name collisions resolve oldest-Order-wins).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded.name or ""
        if not filename.endswith(".xlsx"):
            return Response(
                {"detail": "Invalid file format. Only .xlsx is supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_bytes = uploaded.read()
            parsed_rows = parse_vendor_shipment_excel(file_bytes)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        try:
            with transaction.atomic():
                eligibility_filter = Q(logistics_status="not_shipped") & ~Q(
                    purchase_status="unordered"
                )
                matched_count, skipped_count, affected_order_ids = _apply_logistics_transition(
                    parsed_rows, eligibility_filter, "shipment_confirmed"
                )
                _recompute_order_aggregates(affected_order_ids)
        except Exception as exc:
            # REQ-LOGI-003b: single all-or-nothing operation — any exception
            # rolls back the whole transaction.atomic() block above.
            return Response(
                {"detail": f"처리 중 오류가 발생했습니다: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"matched_count": matched_count, "skipped_count": skipped_count},
            status=status.HTTP_200_OK,
        )


def _process_warehouse_receipt_rows(rows: list[dict]) -> dict:
    """
    SPEC-ORDER-011 REQ-LOGI-015/016: match, judge and apply warehouse-
    receiving counts for a batch of rows, atomically. Mirrors
    `_process_outbound_rows` (SPEC-ORDER-015) structurally, but the row
    shape is {"name": str, "sku": str} (see
    `excel_utils.parse_warehouse_receipt_excel`, which now delegates to
    `_parse_name_sku_xlsx`) — there is no quantity column. Each row is
    exactly one physically received unit, so `received_count` below is a
    COUNT of rows sharing an (order name, sku) key, not a summed `total`
    column (REQ-LOGI-016, design correction — supersedes the REQ-LOGI-005c
    3-column contract this function previously matched). Everything
    downstream of that count is unchanged from REQ-LOGI-015:
    `received_quantity` / `received_at` accumulation in place of
    `shipped_quantity` / `shipped_at`, and logistics_status="received" in
    place of "shipped".

    Deliberately WITHOUT the outbound function's "total == 0 as a
    US-warehouse completion signal" special case (REQ-OUTBOUND-009-area) —
    a row-per-unit format has no cell that can read 0, so that branch has no
    analog here.

    Eligibility gate is unchanged from the pre-quantity-model behavior:
    logistics_status IN ("not_shipped", "shipment_confirmed") — this is what
    allows the direct 미입고 -> 입고 path when a vendor never sent a
    shipment-confirmation upload, and it stays satisfied across multiple
    partial-receipt uploads because logistics_status is left untouched below
    the completion threshold (REQ-LOGI-015a).

    Returns a dict with `matched` / `unmatched` / `quantity_exceeded` item
    lists, their `*_count` totals, and `affected_order_ids` (only orders
    whose LineItem was actually written, for the caller to pass to
    `_recompute_order_aggregates()`). `UploadWarehouseReceiptView` collapses
    this into the pre-existing {"matched_count", "skipped_count"} response
    shape — the detailed categorization here is internal only.
    """
    matched: list[dict] = []
    unmatched: list[dict] = []
    quantity_exceeded: list[dict] = []
    affected_order_ids: set[int] = set()

    # REQ-LOGI-016: rows sharing an (order name, sku) key are COUNTED — each
    # row is one received unit — before any matching or quantity judgement.
    # Same grouping-before-matching structure as REQ-OUTBOUND-007's
    # summation, just counting instead of summing a quantity cell.
    grouped: dict[tuple[str, str], int] = {}
    for row in rows:
        order_name = str(row.get("name") or "").strip()
        sku = str(row.get("sku") or "").strip()

        # No quantity column exists to validate anymore; the only invalid
        # shape left is a blank order name or blank SKU, neither of which
        # can form a usable grouping key. `_parse_name_sku_xlsx` already
        # drops blank-SKU rows before they reach here, but a blank
        # order-name row still flows through (same convention as
        # parse_outbound_excel/parse_rack_number_excel), so it is rejected
        # here instead — reusing `_process_outbound_rows`' "invalid_row"
        # reason for a row that cannot be processed.
        if not order_name or not sku:
            unmatched.append(
                {
                    "name": order_name,
                    "sku": sku,
                    "received_count": 0,
                    "reason": "invalid_row",
                }
            )
            continue

        key = (order_name, sku)
        grouped[key] = grouped.get(key, 0) + 1

    # One transaction for the whole batch, so a failure part-way through
    # leaves no partially-applied rows behind.
    with transaction.atomic():
        orders_by_name: dict[str, Order] = {}
        if grouped:
            name_matches = Order.objects.filter(
                name__in={name for name, _ in grouped}
            ).order_by("pk")
            for candidate in name_matches:
                orders_by_name.setdefault(candidate.name, candidate)

        # REQ-LOGI-005b safety fix carries over: eligibility is gated by
        # logistics_status here (unlike outbound, which has none), scoped to
        # the resolved orders/skus in one query.
        line_items_by_key: dict[tuple[int, str], list[LineItem]] = {}
        if orders_by_name:
            sku_matches = LineItem.objects.filter(
                logistics_status__in=["not_shipped", "shipment_confirmed"],
                order_id__in=[o.id for o in orders_by_name.values()],
                sku__in={sku for _, sku in grouped},
            ).order_by("pk")
            for candidate_item in sku_matches:
                line_items_by_key.setdefault(
                    (candidate_item.order_id, candidate_item.sku), []
                ).append(candidate_item)

        to_update: list[LineItem] = []

        for (order_name, sku), received_count in grouped.items():
            order = orders_by_name.get(order_name)
            if order is None:
                unmatched.append(
                    {
                        "name": order_name,
                        "sku": sku,
                        "received_count": received_count,
                        "reason": "order_not_found",
                    }
                )
                continue

            # Only an exact single match is actionable — zero matches and 2+
            # matches are both reported unmatched, same as
            # _process_outbound_rows (no rule for splitting a count across
            # ambiguous candidates).
            candidates = line_items_by_key.get((order.id, sku), [])
            if len(candidates) != 1:
                unmatched.append(
                    {
                        "name": order_name,
                        "sku": sku,
                        "received_count": received_count,
                        "reason": (
                            "line_item_not_found" if not candidates else "multiple_line_items"
                        ),
                    }
                )
                continue

            line_item = candidates[0]
            # NULL quantity == 0 capacity, same convention as REQ-OUTBOUND-009.
            effective_quantity = line_item.quantity or 0

            if line_item.received_quantity + received_count > effective_quantity:
                quantity_exceeded.append(
                    {
                        "name": order_name,
                        "sku": sku,
                        "received_count": received_count,
                        "line_item_id": line_item.id,
                        "received_quantity": line_item.received_quantity,
                        "quantity": line_item.quantity,
                        "reason": "quantity_exceeded",
                    }
                )
                continue

            # REQ-LOGI-015: accumulate and stamp the processing time.
            line_item.received_quantity += received_count
            line_item.received_at = timezone.now()

            # Advance to "received" only once the cumulative quantity reaches
            # `quantity`; below that threshold logistics_status is left
            # exactly as it was (so the eligibility filter above still
            # matches it on a later partial-completing upload).
            if line_item.received_quantity >= effective_quantity:
                line_item.logistics_status = "received"

            to_update.append(line_item)
            affected_order_ids.add(order.id)
            matched.append(
                {
                    "name": order_name,
                    "sku": sku,
                    "received_count": received_count,
                    "line_item_id": line_item.id,
                    "received_quantity": line_item.received_quantity,
                    "quantity": line_item.quantity,
                    "logistics_status": line_item.logistics_status,
                }
            )

        if to_update:
            LineItem.objects.bulk_update(
                to_update, ["received_quantity", "received_at", "logistics_status"]
            )

    return {
        "matched": matched,
        "unmatched": unmatched,
        "quantity_exceeded": quantity_exceeded,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "quantity_exceeded_count": len(quantity_exceeded),
        "affected_order_ids": affected_order_ids,
    }


class UploadWarehouseReceiptView(APIView):
    """
    POST /api/purchase-orders/upload-warehouse-receipt/

    Multipart: file (.xlsx)
    REQ-LOGI-016: parses a warehouse-receiving-results Excel file (order
    name / SKU schema, NO quantity column — see
    excel_utils.parse_warehouse_receipt_excel, which now delegates to
    _parse_name_sku_xlsx). Each row represents exactly one physically
    received unit, so repeated (order name, sku) rows express the received
    quantity; _process_warehouse_receipt_rows COUNTS rows per key and
    ACCUMULATES that count into LineItem.received_quantity
    (SPEC-ORDER-015-style quantity model, otherwise unchanged), stamping
    received_at on every matched row. logistics_status only advances to
    "received" once received_quantity reaches quantity — a partial receipt
    leaves logistics_status untouched, so a later upload can complete it
    (REQ-LOGI-015a). Matching rule: (Order.name, sku) exact match AND
    logistics_status IN ("not_shipped", "shipment_confirmed") — allows the
    direct 미입고 -> 입고 path when the vendor never sent a shipment
    confirmation (Decision C, unchanged from REQ-LOGI-005). REQ-LOGI-005b
    safety fix still applies: SKU alone would match every order sharing
    that SKU; same-name collisions resolve oldest-Order-wins. A row count
    that would push received_quantity past quantity is rejected as
    quantity_exceeded with no partial write; a row with a blank order name
    or blank SKU is rejected as invalid_row before matching (REQ-LOGI-016).
    Never touches WarehouseStock.quantity (Decision B / REQ-LOGI-006) — this
    remains a pure LineItem field, not an inventory event.

    Response shape is unchanged from the pre-quantity-model version:
    {"matched_count": int, "skipped_count": int}. matched_count counts
    distinct (name, sku) pairs that accumulated some quantity this call
    (whether or not that crossed the "received" threshold); skipped_count
    folds every unmatched (any reason) and quantity_exceeded outcome into
    one count — same per-pair counting convention as REQ-LOGI-004.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded.name or ""
        if not filename.endswith(".xlsx"):
            return Response(
                {"detail": "Invalid file format. Only .xlsx is supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_bytes = uploaded.read()
            parsed_rows = parse_warehouse_receipt_excel(file_bytes)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        try:
            with transaction.atomic():
                result = _process_warehouse_receipt_rows(parsed_rows)
                _recompute_order_aggregates(result["affected_order_ids"])
        except Exception as exc:
            # REQ-LOGI-005a: same all-or-nothing behavior as REQ-LOGI-003b
            return Response(
                {"detail": f"처리 중 오류가 발생했습니다: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "matched_count": result["matched_count"],
                "skipped_count": result["unmatched_count"] + result["quantity_exceeded_count"],
            },
            status=status.HTTP_200_OK,
        )


class ConflictError(Exception):
    """Raised when a 409 Conflict response should be returned."""


# ---------------------------------------------------------------------------
# SPEC-PURCHASE-ORDER-004: Single line item status update
# ---------------------------------------------------------------------------


class LineItemStatusUpdateView(APIView):
    """
    PATCH /api/purchase-orders/line-items/<pk>/status/

    Updates the purchase_status of a single LineItem.

    SPEC-ORDER-012 REQ-RTS-003a: recomputes the parent Order's status/
    ready_to_ship aggregates after the write.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int) -> Response:
        try:
            li = LineItem.objects.get(pk=pk)
        except LineItem.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        purchase_status_value = request.data.get("purchase_status")
        valid_choices = [c[0] for c in LineItem.PURCHASE_STATUS_CHOICES]
        if purchase_status_value not in valid_choices:
            return Response(
                {"error": f"Invalid purchase_status. Valid choices: {valid_choices}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        li.purchase_status = purchase_status_value
        li.save(update_fields=["purchase_status"])
        _recompute_order_aggregates([li.order_id])
        return Response(
            {
                "id": li.id,
                "purchase_status": li.purchase_status,
                "sku": li.sku,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# SPEC-PURCHASE-ORDER-004: Bulk line item status update
# ---------------------------------------------------------------------------


class LineItemBulkStatusUpdateView(APIView):
    """
    PATCH /api/purchase-orders/line-items/bulk-status/

    Updates purchase_status for multiple LineItems at once.
    Body: {"ids": [int, ...], "purchase_status": str}

    SPEC-ORDER-012 REQ-RTS-003a/004: recomputes every affected Order's
    status/ready_to_ship aggregates in one batched call after the write.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request) -> Response:
        ids = request.data.get("ids", [])
        purchase_status_value = request.data.get("purchase_status")

        valid_choices = [c[0] for c in LineItem.PURCHASE_STATUS_CHOICES]

        if not ids:
            return Response(
                {"error": "ids must not be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if purchase_status_value not in valid_choices:
            return Response(
                {"error": f"Invalid purchase_status. Valid choices: {valid_choices}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = LineItem.objects.filter(pk__in=ids)
        existing_ids = set(existing.values_list("id", flat=True))
        missing_ids = [i for i in ids if i not in existing_ids]

        # SPEC-ORDER-012 REQ-RTS-003a: order_ids must be captured BEFORE
        # .update() — QuerySet.update() does not return the affected
        # instances (same constraint as LineItemLogisticsStatusBulkUpdateView).
        affected_order_ids = list(existing.values_list("order_id", flat=True).distinct())

        updated_count = existing.update(purchase_status=purchase_status_value)

        _recompute_order_aggregates(affected_order_ids)

        return Response(
            {
                "updated_count": updated_count,
                "missing_ids": missing_ids,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# SPEC-ORDER-011: LineItem.logistics_status manual status update (single/bulk)
# ---------------------------------------------------------------------------


class LineItemLogisticsStatusUpdateView(APIView):
    """
    PATCH /api/purchase-orders/line-items/<pk>/logistics-status/

    REQ-LOGI-007/007a: updates the logistics_status of a single LineItem,
    then recomputes its parent Order's status (REQ-LOGI-009).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int) -> Response:
        try:
            li = LineItem.objects.get(pk=pk)
        except LineItem.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        logistics_status_value = request.data.get("logistics_status")
        valid_choices = [c[0] for c in LOGISTICS_STATUS_CHOICES]
        if logistics_status_value not in valid_choices:
            # REQ-LOGI-007a: must identify which value was invalid.
            return Response(
                {
                    "error": (
                        f"Invalid logistics_status: {logistics_status_value!r}. "
                        f"Valid choices: {valid_choices}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        li.logistics_status = logistics_status_value
        li.save(update_fields=["logistics_status"])
        _recompute_order_aggregates([li.order_id])
        return Response(
            {
                "id": li.id,
                "logistics_status": li.logistics_status,
                "sku": li.sku,
            },
            status=status.HTTP_200_OK,
        )


class LineItemLogisticsStatusBulkUpdateView(APIView):
    """
    PATCH /api/purchase-orders/line-items/bulk-logistics-status/

    REQ-LOGI-007/007a/010: updates logistics_status for multiple LineItems
    at once, then recomputes every affected Order's status in one batched
    call (REQ-LOGI-010).
    Body: {"ids": [int, ...], "logistics_status": str}
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request) -> Response:
        ids = request.data.get("ids", [])
        logistics_status_value = request.data.get("logistics_status")

        valid_choices = [c[0] for c in LOGISTICS_STATUS_CHOICES]

        if not ids:
            return Response(
                {"error": "ids must not be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if logistics_status_value not in valid_choices:
            # REQ-LOGI-007a: must identify which value was invalid.
            return Response(
                {
                    "error": (
                        f"Invalid logistics_status: {logistics_status_value!r}. "
                        f"Valid choices: {valid_choices}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = LineItem.objects.filter(pk__in=ids)
        existing_ids = set(existing.values_list("id", flat=True))
        missing_ids = [i for i in ids if i not in existing_ids]

        # REQ-LOGI-010: order_ids must be captured BEFORE .update() —
        # QuerySet.update() does not return the affected instances, so this
        # is the only chance to know which Orders need recomputation.
        affected_order_ids = list(existing.values_list("order_id", flat=True).distinct())

        updated_count = existing.update(logistics_status=logistics_status_value)

        _recompute_order_aggregates(affected_order_ids)

        return Response(
            {
                "updated_count": updated_count,
                "missing_ids": missing_ids,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# SPEC-ORDER-013: LineItem.rack_number manual update (single/bulk) + upload
# ---------------------------------------------------------------------------


def _validate_rack_number_value(value) -> str | None:
    """REQ-RACK-003b/004: shared validation for the rack_number PATCH
    endpoints — returns an error message when the value exceeds the field's
    max_length (10), else None. Duplicate values across LineItems are never
    rejected (REQ-RACK-013 — no uniqueness constraint)."""
    if not isinstance(value, str) or len(value) > 10:
        return "rack_number must be a string of at most 10 characters."
    return None


class LineItemRackNumberUpdateView(APIView):
    """
    PATCH /api/purchase-orders/line-items/<pk>/rack-number/

    REQ-RACK-003/003a/003b: updates the rack_number of a single LineItem.
    rack_number is a pure manual/upload field (REQ-RACK-002) — unlike
    purchase_status/logistics_status, this view never calls
    _recompute_order_aggregates(); there is no Order-level rack_number
    aggregate to recompute.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int) -> Response:
        try:
            li = LineItem.objects.get(pk=pk)
        except LineItem.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        rack_number_value = request.data.get("rack_number", "")
        error = _validate_rack_number_value(rack_number_value)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        li.rack_number = rack_number_value
        li.save(update_fields=["rack_number"])
        return Response(
            {
                "id": li.id,
                "rack_number": li.rack_number,
                "sku": li.sku,
            },
            status=status.HTTP_200_OK,
        )


# @MX:NOTE: [AUTO] rack_number is not an Order-level aggregate
# (REQ-RACK-002) — this view intentionally never calls
# _recompute_order_aggregates(), unlike LineItemBulkStatusUpdateView /
# LineItemLogisticsStatusBulkUpdateView above. Do not add that call here.
class LineItemBulkRackNumberUpdateView(APIView):
    """
    PATCH /api/purchase-orders/line-items/bulk-rack-number/

    REQ-RACK-004/004a: updates rack_number for multiple LineItems at once.
    Body: {"ids": [int, ...], "rack_number": str}
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request) -> Response:
        ids = request.data.get("ids", [])
        rack_number_value = request.data.get("rack_number", "")

        if not ids:
            return Response(
                {"error": "ids must not be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        error = _validate_rack_number_value(rack_number_value)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        existing = LineItem.objects.filter(pk__in=ids)
        existing_ids = set(existing.values_list("id", flat=True))
        missing_ids = [i for i in ids if i not in existing_ids]

        updated_count = existing.update(rack_number=rack_number_value)

        return Response(
            {
                "updated_count": updated_count,
                "missing_ids": missing_ids,
            },
            status=status.HTTP_200_OK,
        )


class UploadRackNumberView(APIView):
    """
    POST /api/purchase-orders/upload-rack-number/

    Multipart: file (.xlsx)
    REQ-RACK-006/006a/006b/007: parses a 3-column (order identifier/SKU/rack
    number) Excel file and applies rack_number to every LineItem matching a
    parsed row's (order_name, sku) pair. The order identifier is matched
    against `Order.name` (Shopify's order display name, e.g. "#37349") via
    exact string equality — NOT `Order.order_number` (design fix,
    same-day follow-up to SPEC-ORDER-013) — since the two fields diverge for
    manually-entered "EB"-prefixed orders.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded.name or ""
        if not filename.endswith(".xlsx"):
            return Response(
                {"detail": "Invalid file format. Only .xlsx is supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_bytes = uploaded.read()
            parsed_rows = parse_rack_number_excel(file_bytes)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # REQ-RACK-006b: last-row-wins dedup keyed on (order_name, sku).
        # Rows whose order-identifier cell is blank/empty carry
        # order_name=None (see parse_rack_number_excel) and must NOT be
        # deduped against each other under the same (None, sku) key — there
        # is no reliable identity to merge them on, so each keeps its own
        # row index in the key, ensuring every such row is still counted
        # (as skipped) below.
        dedup_map: dict[tuple, dict] = {}
        for idx, row in enumerate(parsed_rows):
            key = (
                (row["order_name"], row["sku"])
                if row["order_name"] is not None
                else (None, idx)
            )
            dedup_map[key] = row

        matched_count = 0
        skipped_count = 0
        try:
            with transaction.atomic():
                # @MX:WARN: [AUTO] A single (order_name, sku) key may match
                # 2+ LineItems (SPEC-SHOPIFY-SKU-SET-002 unique_together
                # allows duplicate SKUs per order via distinct
                # shopify_line_item_id) — ALL matching LineItems receive the
                # same rack_number value, not just one (결정 E).
                # @MX:REASON: intentional per SPEC-ORDER-013 결정 E — no way
                # to disambiguate which specific LineItem an Excel row
                # targets when duplicates exist; treated as "same physical
                # book, same rack" by design, not a bug.
                for row in dedup_map.values():
                    order_name = row["order_name"]
                    sku = row["sku"]

                    if order_name is None:
                        # Blank order-identifier cell -> treated the same
                        # as "order not found" -> skip (REQ-RACK-006a).
                        skipped_count += 1
                        continue

                    # Design fix (same-day follow-up to SPEC-ORDER-013):
                    # match against Order.name (exact string, e.g.
                    # "#37349" or "#EB10011778"), NOT Order.order_number —
                    # the two fields diverge for manually-entered
                    # "EB"-prefixed orders, where order_number cannot encode
                    # the identifier at all.
                    order = Order.objects.filter(name=order_name).first()
                    if order is None:
                        # REQ-RACK-006a: order not found -> skip.
                        skipped_count += 1
                        continue

                    line_items = LineItem.objects.filter(order=order, sku=sku)
                    if not line_items.exists():
                        # REQ-RACK-006a: no matching LineItem -> skip.
                        skipped_count += 1
                        continue

                    line_items.update(rack_number=row["rack_number"])
                    matched_count += 1
        except Exception as exc:
            return Response(
                {"detail": f"처리 중 오류가 발생했습니다: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"matched_count": matched_count, "skipped_count": skipped_count},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# SPEC-ORDER-014: cross-order rack_number summary (read-only aggregate)
# ---------------------------------------------------------------------------


# @MX:NOTE: [AUTO] no pagination and application-level grouping (rather than
# DB-level annotate) mirror UnorderedItemsView above (M2) — grouping needs
# each member LineItem's order_name/sku/title/quantity/logistics_status
# together, which annotate-only aggregation cannot produce in one query.
# @MX:WARN: [AUTO] returns every not-yet-shipped LineItem system-wide in a
# single non-paginated payload — response size grows with unshipped LineItem
# count and could become slow at large scale.
# @MX:REASON: intentional per SPEC-ORDER-014 결정 B — unshipped LineItems are
# naturally scope-limited (excludes the "shipped" majority); pagination is
# explicitly deferred to a follow-up SPEC if this becomes a real problem.
class LineItemRackNumberSummaryView(APIView):
    """
    GET /api/purchase-orders/line-items/rack-number-summary/

    REQ-RACKSUM-001~008: cross-order read-only aggregate of every LineItem
    that has not yet shipped (logistics_status != "shipped"), grouped by
    rack_number. LineItems with an empty rack_number are grouped into a
    single unassigned bucket (REQ-RACKSUM-004a) rather than dropped.
    Also excludes LineItems with purchase_status="order_cancelled",
    mirroring the same exclusion used elsewhere for cancelled purchases.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        line_items = (
            LineItem.objects.exclude(logistics_status="shipped")
            .exclude(purchase_status="order_cancelled")
            .select_related("order")
            .order_by("rack_number", "order__order_number")
        )

        groups: dict[str, dict] = {}
        for li in line_items:
            key = li.rack_number  # "" -> unassigned bucket (REQ-RACKSUM-004a)
            group = groups.setdefault(
                key,
                {
                    "rack_number": key,
                    "is_unassigned": key == "",
                    "total_quantity": 0,
                    "line_items": [],
                },
            )
            # REQ-RACKSUM-005: null quantity treated as 0, mirroring
            # UnorderedItemsView's `li.quantity or 0` convention.
            group["total_quantity"] += li.quantity or 0
            group["line_items"].append(
                {
                    "id": li.id,
                    "order_name": li.order.name,
                    "sku": li.sku,
                    "title": li.title,
                    "quantity": li.quantity,
                    "logistics_status": li.logistics_status,
                }
            )

        # REQ-RACKSUM-004/004a: named groups sorted alphabetically by
        # rack_number, unassigned bucket always last.
        named = sorted(
            (g for k, g in groups.items() if k != ""),
            key=lambda g: g["rack_number"],
        )
        unassigned = [groups[""]] if "" in groups else []

        return Response({"groups": named + unassigned}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# SPEC-ORDER-015: outbound processing (Korea warehouse -> US warehouse)
# ---------------------------------------------------------------------------


def _parse_total(value) -> tuple[int, bool]:
    """Coerce an outbound row's quantity cell to int, reporting whether the
    input actually SPELLED a number.

    Returns `(parsed, parsed_ok)`. On failure `parsed` is 0 — the same fallback
    the previous `_to_int` helper applied — but `parsed_ok` is False, so the
    caller can tell a real 0 apart from a blank/garbage cell that merely
    DEFAULTED to one.

    That distinction is load-bearing rather than cosmetic. A genuine 0 unlocks
    the US-warehouse completion path below (it closes the shipment out); a
    defaulted 0 must not, or an empty Total cell or a stray Excel error value
    would be indistinguishable from a deliberate business signal. Before that
    completion path existed the two were interchangeable, because every
    non-positive total was rejected identically.
    """
    try:
        return int(value), True
    except (TypeError, ValueError):
        # Covers None (TypeError), "" / "  " / "abc" / "#N/A" (ValueError).
        return 0, False


# `confirmed_distributor` values meaning "already in a US warehouse". A
# LineItem confirmed against one of these never travels Korea -> US, so an
# outbound row for it carries total 0 and is read as a completion signal
# instead of an unshippable amount. The suffixed codes match the location map
# the Daily Review confirm flow writes (see _WAREHOUSE_LOCATION_MAP above);
# "warehouse_korea" is deliberately absent — Korea stock DOES ship.
_US_WAREHOUSE_DISTRIBUTORS: frozenset[str] = frozenset({"warehouse_ca", "warehouse_nj"})


# @MX:NOTE: [AUTO] Two non-obvious business rules live here, both deliberate
# SPEC-ORDER-015 design decisions rather than incidental behaviour:
#   (설계 결정 C, REQ-OUTBOUND-007) duplicate (order name, sku) rows in ONE
#   request are SUMMED and judged once — NOT last-row-wins as
#   UploadRackNumberView does. Judging row-by-row would let two rows that each
#   fit under `quantity` jointly overshoot it.
#   (설계 결정 B, REQ-OUTBOUND-009) a NULL `quantity` is read as 0 capacity, so
#   any positive request against it is rejected as over-capacity instead of
#   being silently applied against an unknown limit.
#   (설계 결정 A, REQ-OUTBOUND-005a) a 2+ LineItem match is reported unmatched
#   and left untouched — there is no quantity-distribution rule.
#   (spec.md Exclusions) a NEGATIVE `total` is rejected per row before
#   summation. shipped_quantity must never decrease: 출고 취소/되돌리기(undo)
#   is explicitly out of scope, and a negative total would otherwise reach
#   that excluded capability through ordinary input.
#   (US-warehouse completion) a group summing to exactly 0 is judged AFTER
#   matching, not before: for a LineItem whose confirmed_distributor is a US
#   warehouse it completes the item, for anything else it stays invalid_total.
#   That split is why the pre-grouping filter rejects `< 0` rather than `<= 0`.
#   Because that 0 carries meaning, it must be a zero the input actually
#   SPELLED — an unreadable quantity is rejected pre-grouping rather than
#   defaulted to 0, so a blank cell cannot impersonate the completion signal.
# @MX:NOTE: [AUTO] All database access is BATCHED into a fixed number of
# queries — 1 Order fetch + 1 LineItem fetch + 1 bulk_update — regardless of
# how many (order name, sku) groups the request carries. The original
# implementation ran those three queries once PER GROUP, so an 8-row upload
# cost ~24 round trips and a 50-row upload ~150. Against the remote MySQL
# instance this project uses (~130ms round-trip latency) that made response
# time scale linearly with input size (~3s at 8 rows, ~19s at 50). The cost
# here is dominated by the NUMBER of queries, not the work inside them, so
# every new lookup added below must be batched too. Matching, quantity
# judgement and status transition are deliberately pure-Python passes over the
# already-fetched objects. Pinned by test_spec_015.py T8, which asserts the
# query count is IDENTICAL for a 2-group and a 10-group batch.
# @MX:WARN: [AUTO] LineItems are read and updated without select_for_update()
# locking — two concurrent outbound requests targeting the same LineItem can
# both pass the over-capacity check against the same stale shipped_quantity
# and jointly push it past `quantity`.
# @MX:REASON: known, accepted gap carried over from UploadRackNumberView
# (which updates rack_number lock-free the same way); SPEC-ORDER-015 plan.md
# "동시성" explicitly defers row-level locking to a follow-up SPEC. Add
# select_for_update() here first if this is ever revisited.
def _process_outbound_rows(rows: list[dict]) -> dict:
    """
    SPEC-ORDER-015 REQ-OUTBOUND-003~011/013: match, judge and apply outbound
    quantities for a batch of rows, atomically.

    Shared entry point for OutboundProcessView (manual JSON) and
    UploadOutboundView (Excel) — both supply rows shaped
    {"name": str, "sku": str, "total": int}, so the two endpoints are
    guaranteed to produce identical results for equivalent input.

    Returns a dict with `matched` / `unmatched` / `quantity_exceeded` item
    lists plus their `*_count` totals (REQ-OUTBOUND-014). `unmatched` reasons
    are `order_not_found`, `line_item_not_found`, `multiple_line_items`,
    `invalid_total` (negative quantity, an unreadable quantity, or a zero
    quantity on a LineItem that is not confirmed against a US warehouse) and
    `invalid_row` (malformed input shape).
    """
    matched: list[dict] = []
    unmatched: list[dict] = []
    quantity_exceeded: list[dict] = []

    # REQ-OUTBOUND-007 (설계 결정 C): rows sharing an (order name, sku) key
    # are SUMMED into one combined quantity before any matching or quantity
    # judgement — not last-row-wins.
    grouped: dict[tuple[str, str], int] = {}
    for row in rows:
        # Defensive: OutboundProcessView rejects malformed rows with 400 and
        # parse_outbound_excel only ever emits well-formed dicts, but this is
        # a shared entry point — degrade to a reported row instead of raising
        # AttributeError (which would surface as an opaque 500).
        if not isinstance(row, dict):
            unmatched.append(
                {"name": "", "sku": "", "total": 0, "reason": "invalid_row"}
            )
            continue

        order_name = str(row.get("name") or "").strip()
        sku = str(row.get("sku") or "").strip()
        total, total_ok = _parse_total(row.get("total"))

        # A quantity that could not be READ is rejected here alongside the
        # negative guard, and for the same structural reason: it must never
        # reach the post-matching zero branch. `_parse_total` falls back to 0,
        # and on a US-warehouse LineItem a 0 CLOSES THE SHIPMENT OUT — so a
        # blank cell, a text cell or an Excel error value would otherwise be
        # silently promoted into a deliberate "already in the US warehouse"
        # completion signal. Rejecting pre-grouping also stops a garbage row
        # from disappearing as a silent +0 into a legitimate row's sum, which
        # is the same argument that puts the negative guard here.
        #
        # The reason code is deliberately REUSED rather than split: both a
        # negative and an unreadable total mean "the total value was not
        # usable", callers already handle `invalid_total`, and this is exactly
        # the verdict an unreadable total received before the completion path
        # existed. Pinned by TestZeroTotalRequiresAGenuineParsedZero.
        if not total_ok:
            unmatched.append(
                {
                    "name": order_name,
                    "sku": sku,
                    "total": total,
                    "reason": "invalid_total",
                }
            )
            continue

        # spec.md Exclusions forbid 출고 취소/되돌리기 (undo): shipped_quantity
        # must never decrease. A negative `total` would reach exactly that
        # excluded capability through ordinary input, so it is rejected here,
        # per row and STRICTLY BEFORE summation. Rejecting after summation
        # would let a negative row quietly shrink a legitimate positive one for
        # the same key. Pinned by
        # test_negative_row_cannot_offset_a_positive_row_for_the_same_key and
        # test_negative_row_never_reaches_the_matching_stage_at_all.
        #
        # A total of exactly 0 is NOT rejected here: it may be a US-warehouse
        # completion signal, and that verdict needs `confirmed_distributor`,
        # which only exists on the matched LineItem. So zero rows fall through
        # into grouping and are judged after matching instead (see below).
        if total < 0:
            unmatched.append(
                {
                    "name": order_name,
                    "sku": sku,
                    "total": total,
                    "reason": "invalid_total",
                }
            )
            continue

        key = (order_name, sku)
        grouped[key] = grouped.get(key, 0) + total

    # REQ-OUTBOUND-011/013: one transaction for the whole batch, so a failure
    # part-way through leaves no partially-applied rows behind.
    with transaction.atomic():
        # REQ-OUTBOUND-003/003a: matched on `Order.name` exact string
        # equality ("#37349", "#EB10011778"). The `order_number` column is
        # deliberately never consulted — the two diverge for manually-entered
        # "EB"-prefixed orders, which is exactly why SPEC-ORDER-013 abandoned
        # it as a matching key.
        #
        # `Order.name` carries no uniqueness constraint (unique_together is
        # (shopify_order_id, store_type)), so several orders may share a name.
        # The per-group `.filter(name=X).first()` this replaces resolved that
        # collision via Django's implicit `ORDER BY pk` fallback on an
        # unordered queryset, i.e. oldest-wins. `.order_by("pk")` + setdefault
        # reproduces that tie-break exactly rather than inheriting whatever
        # order MySQL happens to return rows in.
        orders_by_name: dict[str, Order] = {}
        if grouped:
            name_matches = Order.objects.filter(
                name__in={name for name, _ in grouped}
            ).order_by("pk")
            for candidate in name_matches:
                orders_by_name.setdefault(candidate.name, candidate)

        # One fetch for every LineItem that could satisfy any group, keyed by
        # (order id, sku) so the 0 / 1 / 2+ branching below is a dict lookup.
        # `order_id__in` and `sku__in` are independent filters, so this also
        # drags in pairs nobody requested (order A holding a sku that only
        # another group asked for). That is harmless precisely because the
        # loop below only ever looks up keys built from `grouped` — the
        # cross-product entries are never reachable.
        # REQ-OUTBOUND-006: no logistics_status filter here on purpose — a
        # LineItem in any pipeline state is eligible for outbound.
        line_items_by_key: dict[tuple[int, str], list[LineItem]] = {}
        if orders_by_name:
            sku_matches = LineItem.objects.filter(
                order_id__in=[o.id for o in orders_by_name.values()],
                sku__in={sku for _, sku in grouped},
            ).order_by("pk")
            for candidate_item in sku_matches:
                line_items_by_key.setdefault(
                    (candidate_item.order_id, candidate_item.sku), []
                ).append(candidate_item)

        # Every LineItem the judgement pass decides to write, flushed in one
        # bulk_update after the loop.
        to_update: list[LineItem] = []

        for (order_name, sku), total in grouped.items():
            order = orders_by_name.get(order_name)
            if order is None:
                unmatched.append(
                    {
                        "name": order_name,
                        "sku": sku,
                        "total": total,
                        "reason": "order_not_found",
                    }
                )
                continue

            # REQ-OUTBOUND-004/005/005a (설계 결정 A): only an exact single
            # match is actionable. Zero matches and 2+ matches are BOTH
            # reported as unmatched — there is no rule for splitting a
            # quantity across ambiguous candidates, so nothing is written
            # rather than guessing.
            candidates = line_items_by_key.get((order.id, sku), [])
            if len(candidates) != 1:
                unmatched.append(
                    {
                        "name": order_name,
                        "sku": sku,
                        "total": total,
                        "reason": (
                            "line_item_not_found" if not candidates else "multiple_line_items"
                        ),
                    }
                )
                continue

            line_item = candidates[0]
            # REQ-OUTBOUND-009 (설계 결정 B): NULL quantity == 0 capacity.
            effective_quantity = line_item.quantity or 0

            # A group whose rows SUM to exactly 0 carries no shippable amount,
            # so it is normally invalid_total. The one exception is a LineItem
            # confirmed against a US warehouse: it was never physically shipped
            # Korea -> US because it was already sitting in the destination
            # warehouse, so a zero is a completion signal rather than a missing
            # quantity. The decision needs `confirmed_distributor`, which lives
            # on the matched LineItem, which is why zero survives the pre-
            # grouping filter and is judged here instead.
            # Note this keys off the SUMMED total: a 0 row plus a 5 row for the
            # same key is an ordinary 5-unit shipment (REQ-OUTBOUND-007), and
            # a negative total can never arrive here at all — it was rejected
            # per row before grouping.
            if total == 0:
                if line_item.confirmed_distributor not in _US_WAREHOUSE_DISTRIBUTORS:
                    unmatched.append(
                        {
                            "name": order_name,
                            "sku": sku,
                            "total": total,
                            "reason": "invalid_total",
                        }
                    )
                    continue

                # max(), never a bare assignment: an already-complete (or
                # anomalously over-shipped) LineItem must not be pulled back
                # DOWN to `quantity`. shipped_quantity may only ever grow —
                # same undo-prevention invariant the negative guard enforces.
                line_item.shipped_quantity = max(
                    line_item.shipped_quantity, effective_quantity
                )
                line_item.shipped_at = timezone.now()
                # Reuse of the REQ-OUTBOUND-010 threshold below, not a special
                # -case status write: reaching the full quantity is what makes
                # this "shipped", exactly as for a positive total.
                if line_item.shipped_quantity >= effective_quantity:
                    line_item.logistics_status = "shipped"

                to_update.append(line_item)
                matched.append(
                    {
                        "name": order_name,
                        "sku": sku,
                        "total": total,
                        "line_item_id": line_item.id,
                        "shipped_quantity": line_item.shipped_quantity,
                        "quantity": line_item.quantity,
                        "logistics_status": line_item.logistics_status,
                    }
                )
                continue

            if line_item.shipped_quantity + total > effective_quantity:
                quantity_exceeded.append(
                    {
                        "name": order_name,
                        "sku": sku,
                        "total": total,
                        "line_item_id": line_item.id,
                        "shipped_quantity": line_item.shipped_quantity,
                        "quantity": line_item.quantity,
                        "reason": "quantity_exceeded",
                    }
                )
                continue

            # REQ-OUTBOUND-008: accumulate and stamp the processing time.
            line_item.shipped_quantity += total
            line_item.shipped_at = timezone.now()

            # REQ-OUTBOUND-010/010a: advance to "shipped" only once the
            # cumulative quantity reaches `quantity`; below that threshold
            # logistics_status is left exactly as it was. This only ever
            # writes the pre-existing "shipped" choice — SPEC-ORDER-015 adds
            # no new LOGISTICS_STATUS_CHOICES value.
            # Note that the bulk write below always includes logistics_status
            # in its column list, so a below-threshold match rewrites the
            # field with the value it was loaded with. That is a deliberate
            # no-op, not a reset: the object still carries its own current
            # status here because this branch did not touch it.
            if line_item.shipped_quantity >= effective_quantity:
                line_item.logistics_status = "shipped"

            to_update.append(line_item)
            matched.append(
                {
                    "name": order_name,
                    "sku": sku,
                    "total": total,
                    "line_item_id": line_item.id,
                    "shipped_quantity": line_item.shipped_quantity,
                    "quantity": line_item.quantity,
                    "logistics_status": line_item.logistics_status,
                }
            )

        # One write for the whole batch instead of one save() per matched row.
        # bulk_update writes every listed column for every object, unlike the
        # conditional update_fields this replaces — safe here because each
        # object already carries its intended final value for all three
        # columns by the time it lands in `to_update`.
        if to_update:
            LineItem.objects.bulk_update(
                to_update, ["shipped_quantity", "shipped_at", "logistics_status"]
            )

    # REQ-OUTBOUND-014: three categories, each with its item list and count.
    return {
        "matched": matched,
        "unmatched": unmatched,
        "quantity_exceeded": quantity_exceeded,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "quantity_exceeded_count": len(quantity_exceeded),
    }


class OutboundProcessView(APIView):
    """
    POST /api/purchase-orders/line-items/outbound-process/

    REQ-OUTBOUND-011: manual-entry outbound processing.
    Body: {"rows": [{"name": str, "sku": str, "total": int}, ...]}
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    REQUIRED_ROW_KEYS = ("name", "sku", "total")

    def post(self, request) -> Response:
        rows = request.data.get("rows", [])
        if not isinstance(rows, list):
            return Response(
                {"detail": "rows must be a list."}, status=status.HTTP_400_BAD_REQUEST
            )

        # A structurally invalid body is a client error. Without this check a
        # non-dict item reaches row.get() and raises AttributeError, which the
        # caller would see as an opaque 500 instead of an actionable 400.
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                return Response(
                    {"detail": f"rows[{index}] must be an object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            missing = [k for k in self.REQUIRED_ROW_KEYS if k not in row]
            if missing:
                return Response(
                    {"detail": f"rows[{index}] is missing required key(s): {', '.join(missing)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            result = _process_outbound_rows(rows)
        except Exception as exc:
            return Response(
                {"detail": f"처리 중 오류가 발생했습니다: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)


class UploadOutboundView(APIView):
    """
    POST /api/purchase-orders/upload-outbound/

    Multipart: file (.xlsx)
    REQ-OUTBOUND-013: Excel-driven outbound processing. Parses the upload with
    `parse_outbound_excel` and hands the rows to the same
    `_process_outbound_rows` the manual endpoint uses, so both paths cannot
    drift apart (REQ-OUTBOUND-011/013). A header the parser cannot resolve
    surfaces as HTTP 422 (REQ-OUTBOUND-012a).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded.name or ""
        if not filename.endswith(".xlsx"):
            return Response(
                {"detail": "Invalid file format. Only .xlsx is supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parsed_rows = parse_outbound_excel(uploaded.read())
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        try:
            result = _process_outbound_rows(parsed_rows)
        except Exception as exc:
            return Response(
                {"detail": f"처리 중 오류가 발생했습니다: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# M6: Distributor vendor rules
# ---------------------------------------------------------------------------


class DistributorVendorRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistributorVendorRule
        fields = ["id", "publisher_name", "distributor", "created_at"]

    def validate_distributor(self, value: str) -> str:
        if value not in VENDOR_RULE_DISTRIBUTORS:
            raise serializers.ValidationError(
                f"Invalid distributor. Must be one of: {sorted(VENDOR_RULE_DISTRIBUTORS)}."
            )
        return value


class DistributorVendorRuleListCreateView(APIView):
    """
    GET  /api/purchase-orders/vendor-rules/  → list all rules
    POST /api/purchase-orders/vendor-rules/  → create a new rule (publisher_name unique → 409)
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        rules = DistributorVendorRule.objects.all().order_by("publisher_name")
        serializer = DistributorVendorRuleSerializer(rules, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})

    def post(self, request) -> Response:
        publisher_name = request.data.get("publisher_name")
        # Check for duplicate before DRF validation to return 409 instead of 400
        if publisher_name and DistributorVendorRule.objects.filter(
            publisher_name=publisher_name
        ).exists():
            return Response(
                {"detail": "A rule for this publisher_name already exists."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = DistributorVendorRuleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "A rule for this publisher_name already exists."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DistributorVendorRuleDeleteView(APIView):
    """
    DELETE /api/purchase-orders/vendor-rules/<pk>/  → delete rule (404 if not found)
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk: int) -> Response:
        try:
            rule = DistributorVendorRule.objects.get(pk=pk)
        except DistributorVendorRule.DoesNotExist:
            return Response(
                {"detail": "Vendor rule not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# M7: Purchase order list
# ---------------------------------------------------------------------------


class PurchaseOrderPagination(PageNumberPagination):
    page_size = 50


class PurchaseOrderSerializer(serializers.ModelSerializer):
    net_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "sku", "title", "distributor", "quantity",
            "net_quantity",
            "unit_price", "status", "created_at", "updated_at",
        ]


def _attach_net_quantity(purchase_orders: list) -> None:
    """
    Attach net_quantity to each PurchaseOrder instance in-place.

    net_quantity = (sum of LineItem.quantity for linked items)
                   - (sum of Refund.quantity for those items)

    Falls back to PurchaseOrder.quantity when no LineItems are linked.

    Uses Python-level aggregation to stay compatible with both SQLite (tests)
    and MySQL (production), avoiding raw SQL with dialect-specific quoting.

    # @MX:ANCHOR: [AUTO] Computes net_quantity for the PO list response page
    # @MX:REASON: Called by PurchaseOrderListView.get(); fan-in from test suite and view
    """
    if not purchase_orders:
        return

    po_ids = [po.pk for po in purchase_orders]

    # Fetch all line items linked to these POs with their refund sums
    li_qs = (
        LineItem.objects.filter(purchase_orders__in=po_ids)
        .prefetch_related("purchase_orders")
        .annotate(
            refunded_qty=Coalesce(
                Subquery(
                    Refund.objects.filter(
                        order_id=OuterRef("order_id"),
                        line_item_id=OuterRef("shopify_line_item_id"),
                    )
                    .values("order_id", "line_item_id")
                    .annotate(total=Sum("quantity"))
                    .values("total")[:1],
                    output_field=IntegerField(),
                ),
                0,
            )
        )
        .values("id", "quantity", "refunded_qty", "purchase_orders__id")
    )

    # Aggregate per PO
    po_net: dict[int, int] = {}
    for row in li_qs:
        po_id = row["purchase_orders__id"]
        li_qty = row["quantity"] or 0
        refunded = row["refunded_qty"] or 0
        net = max(li_qty - refunded, 0)
        po_net[po_id] = po_net.get(po_id, 0) + net

    for po in purchase_orders:
        if po.pk in po_net:
            po.net_quantity = po_net[po.pk]
        else:
            # No linked LineItems → use PO's own quantity
            po.net_quantity = po.quantity


class PurchaseOrderListView(APIView):
    """
    GET /api/purchase-orders/

    List PurchaseOrders with optional filters:
      - distributor: exact match
      - status: exact match
      - date_from: created_at__gte (YYYY-MM-DD)
      - date_to:   created_at__lte (YYYY-MM-DD)

    Ordered by -created_at, paginated 50/page.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        # SPEC-PURCHASE-ORDER-003: exclude fully-refunded POs
        # Subquery: total refunded quantity for a specific (order_id, shopify_line_item_id)
        refund_sum_sq = (
            Refund.objects.filter(
                order_id=OuterRef("order_id"),
                line_item_id=OuterRef("shopify_line_item_id"),
            )
            .values("order_id", "line_item_id")
            .annotate(total=Sum("quantity"))
            .values("total")[:1]
        )

        # LineItem with remaining quantity (refunded_qty < original quantity)
        unrefunded_li = LineItem.objects.annotate(
            refunded_qty=Coalesce(
                Subquery(refund_sum_sq, output_field=IntegerField()),
                0,
            )
        ).filter(
            purchase_orders=OuterRef("pk"),
            refunded_qty__lt=F("quantity"),
        )

        # Any LineItem linked to this PO
        any_li = LineItem.objects.filter(purchase_orders=OuterRef("pk"))

        # Exclude POs where all linked LineItems are fully refunded
        qs = (
            PurchaseOrder.objects.exclude(
                Exists(any_li) & ~Exists(unrefunded_li)
            )
            .order_by("-created_at")
        )

        params = request.query_params

        distributor = params.get("distributor")
        if distributor:
            qs = qs.filter(distributor=distributor)

        po_status = params.get("status")
        if po_status:
            qs = qs.filter(status=po_status)

        date_from = params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        paginator = PurchaseOrderPagination()
        page = paginator.paginate_queryset(qs, request)

        # Compute net_quantity for each PO in the current page
        _attach_net_quantity(page)

        serializer = PurchaseOrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
