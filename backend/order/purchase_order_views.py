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

from datetime import date
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from django.db import IntegrityError, transaction
from django.db.models import Case, Count, Exists, F, IntegerField, OuterRef, Subquery, Sum, Value, When
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
    parse_vendor_excel,
)
from .models import BookseenData, DistributorVendorRule, KyoboData, LineItem, LineItemNote, PurchaseOrder, Refund, ShopifySkuSetMapping, VendorComparison, WarehouseStock

VALID_DISTRIBUTORS = {"bookseen", "kyobo", "choeumgoyuk", "agape", "sungseoyunion",
                      "warehouse_korea", "warehouse_ca", "warehouse_nj"}
VENDOR_FILE_DISTRIBUTORS = {"bookseen", "kyobo"}
VENDOR_RULE_DISTRIBUTORS = {"choeumgoyuk", "agape", "sungseoyunion"}

EXCEL_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


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
            LineItem.objects.filter(sku__isnull=False, purchase_status="unordered")
            .exclude(purchase_orders__isnull=False)
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

        # @MX:NOTE: [AUTO] Bundle expansion: if sku matches ShopifySkuSetMapping, expand to member ISBNs
        # @MX:SPEC: SPEC-SHOPIFY-SKU-SET-001 REQ-SKU-SET-003
        from collections import defaultdict as _defaultdict
        bundle_map: dict[str, list[str]] = _defaultdict(list)
        for mapping in ShopifySkuSetMapping.objects.order_by("bundle_sku", "sort_order").values("bundle_sku", "member_isbn"):
            bundle_map[mapping["bundle_sku"]].append(mapping["member_isbn"])

        expanded = []
        for item in results:
            sku = item["sku"]
            if sku in bundle_map:
                for member_isbn in bundle_map[sku]:
                    expanded.append({
                        **item,
                        "sku": member_isbn,
                        "is_bundle_member": True,
                        "bundle_sku": sku,
                    })
            else:
                expanded.append({**item, "is_bundle_member": False, "bundle_sku": None})

        return Response({"count": len(expanded), "results": expanded})


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

        # Aggregate net quantities (after refunds) for requested SKUs from unordered LineItems
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
        li_qs = (
            LineItem.objects.filter(sku__in=requested)
            .exclude(purchase_orders__isnull=False)
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

    Multipart: distributor (bookseen|kyobo) + file (.xlsx/.xls)
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

            if distributor == "bookseen":
                defaults = {
                    "available": available,
                    "price": price,
                    "stock": stock,
                    "returnable": returnable,
                    "status": vendor_status,
                    "arrival": arrival,
                }
                BookseenData.objects.update_or_create(sku=sku, defaults=defaults)
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
            LineItem.objects.filter(sku__isnull=False, purchase_status="unordered")
            .exclude(purchase_orders__isnull=False)
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

        bs_map: dict[str, BookseenData] = {
            bd.sku: bd for bd in BookseenData.objects.filter(sku__in=all_skus)
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
                    bookseen_price=bs.price if bs else None,
                    bookseen_stock=bs.stock if bs else None,
                    bookseen_returnable=bs.returnable if bs else None,
                    bookseen_status=bs.status if bs else None,
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
                if selected == "bookseen":
                    confirmed_price = bs.price if bs else None
                    confirmed_dist = "bookseen"
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
                    "bookseen_available": bs.available if bs else None,
                    "bookseen_price": str(bs.price) if bs and bs.price is not None else None,
                    "bookseen_stock": bs.stock if bs else None,
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
                    "bookseen_available": None,
                    "bookseen_price": None,
                    "bookseen_stock": None,
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
        bs_map: dict[str, BookseenData] = {
            bd.sku: bd for bd in BookseenData.objects.filter(sku__in=all_skus)
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
                bookseen_price=bs.price if bs else None,
                bookseen_stock=bs.stock if bs else None,
                bookseen_returnable=bs.returnable if bs else None,
                bookseen_status=bs.status if bs else None,
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

            # Serialize bookseen_returnable as "가능"/"불가"/null
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
                    "bookseen_available": bs.available if bs else None,
                    "bookseen_price": str(bs.price) if bs and bs.price is not None else None,
                    "bookseen_stock": bs.stock if bs else None,
                    "bookseen_returnable": bs_returnable_display,
                    "bookseen_status": bs.status if bs else None,
                    "bookseen_arrival": bs.arrival if bs else None,
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

                    # Find unordered LineItems for this SKU with a lock
                    unordered_lis = list(
                        LineItem.objects.filter(sku=sku)
                        .exclude(purchase_orders__isnull=False)
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
                    # but verify by checking if any returned LI is somehow already linked
                    already_linked = [li for li in unordered_lis if li.purchase_orders.exists()]
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
                    update_fields = ["confirmed_distributor"]
                    for li in unordered_lis:
                        li.confirmed_distributor = dist

                    # REQ-CON-022/023: update purchase_status only when explicitly provided
                    if purchase_status is not None:
                        for li in unordered_lis:
                            li.purchase_status = purchase_status
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
    "bookseen": "북센",
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
            LineItem.objects.filter(sku__isnull=False, purchase_status="unordered")
            .exclude(purchase_orders__isnull=False)
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
        bookseen_map = {bd.sku: bd for bd in BookseenData.objects.filter(sku__in=skus)}
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
            bd = bookseen_map.get(sku)
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
                bookseen_price=bd.price if bd else None,
                bookseen_stock=bd.stock if bd else None,
                bookseen_returnable=bd.returnable if bd else None,
                bookseen_status=bd.status if bd else None,
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


class UploadDailyReviewView(APIView):
    """
    POST /api/purchase-orders/upload-daily-review/

    Multipart: file (.xlsx)
    Parses the Daily Review Excel file, reads the '선택' column (Korean display name),
    and confirms purchase orders for rows with a valid selection.
    Rows with empty '선택' are skipped.
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
            parsed_rows = parse_daily_review_excel(file_bytes)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Deduplicate by SKU — last row wins if same ISBN appears multiple times
        sku_map: dict[str, dict] = {}
        for row in parsed_rows:
            sku_map[row["sku"]] = row

        confirmed_count = 0
        skipped_count = 0
        errors: list[dict] = []
        confirmed_by_distributor: dict[str, list] = {}

        # Warehouse distributor code → location mapping
        _WAREHOUSE_LOCATION_MAP: dict[str, str] = {
            "warehouse_korea": "korea",
            "warehouse_ca": "ca",
            "warehouse_nj": "nj",
        }

        try:
            with transaction.atomic():
                for sku, item in sku_map.items():
                    distributor_code = item["distributor"]
                    note = item.get("note")
                    note_type = item.get("note_type")

                    unordered_lis = list(
                        LineItem.objects.filter(sku=sku, purchase_status="unordered")
                        .exclude(purchase_orders__isnull=False)
                        .select_for_update()
                    )

                    if not unordered_lis:
                        skipped_count += 1
                        continue

                    title = unordered_lis[0].title or sku
                    total_qty = sum(li.quantity or 0 for li in unordered_lis)
                    li_ids = [li.pk for li in unordered_lis]

                    if note_type and not distributor_code:
                        # CS case: update purchase_status and create note
                        new_status = _NOTE_TYPE_STATUS_MAP[note_type]
                        for li in unordered_lis:
                            li.purchase_status = new_status
                        LineItem.objects.bulk_update(unordered_lis, ["purchase_status"])
                        if note is not None:
                            for li in unordered_lis:
                                LineItemNote.objects.create(
                                    line_item=li,
                                    content=note,
                                    author=None,
                                    note_type=note_type,
                                    assignee="CS",
                                )
                        confirmed_count += 1
                        continue

                    if distributor_code in _WAREHOUSE_LOCATION_MAP:
                        # REQ-PO5-004: Warehouse branch — deduct stock, set in_stock, no PO
                        loc = _WAREHOUSE_LOCATION_MAP[distributor_code]

                        # Atomic stock deduction: floor at 0
                        WarehouseStock.objects.filter(isbn=sku, location=loc).update(
                            quantity=Case(
                                When(quantity__gte=total_qty, then=F("quantity") - total_qty),
                                default=Value(0),
                                output_field=IntegerField(),
                            )
                        )

                        # REQ-PO5-005: Set purchase_status = "in_stock"
                        update_fields = ["purchase_status", "confirmed_distributor"]
                        for li in unordered_lis:
                            li.purchase_status = "in_stock"
                            li.confirmed_distributor = distributor_code
                        if note is not None:
                            # Migrated to LineItemNote (SPEC-ORDER-010)
                            for li in unordered_lis:
                                LineItemNote.objects.create(
                                    line_item=li,
                                    content=note,
                                    author=None,
                                    assignee="한국창고",
                                )

                        LineItem.objects.bulk_update(unordered_lis, update_fields)

                    else:
                        # Non-warehouse: existing flow — create PurchaseOrder
                        unit_price = None
                        if distributor_code == "bookseen":
                            bd = BookseenData.objects.filter(sku=sku).first()
                            if bd:
                                unit_price = bd.price
                        elif distributor_code == "kyobo":
                            kd = KyoboData.objects.filter(sku=sku).first()
                            if kd:
                                unit_price = kd.price

                        po = PurchaseOrder.objects.create(
                            sku=sku,
                            title=title,
                            distributor=distributor_code,
                            quantity=total_qty,
                            unit_price=unit_price,
                            status="pending",
                        )
                        po.line_items.add(*unordered_lis)

                        update_fields = ["confirmed_distributor"]
                        for li in unordered_lis:
                            li.confirmed_distributor = distributor_code

                        LineItem.objects.bulk_update(unordered_lis, update_fields)

                    # REQ-PO5-007: Track confirmed by distributor
                    confirmed_by_distributor.setdefault(distributor_code, []).append(
                        {"sku": sku, "title": title, "quantity": total_qty}
                    )
                    confirmed_count += 1

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


class ConflictError(Exception):
    """Raised when a 409 Conflict response should be returned."""


# ---------------------------------------------------------------------------
# SPEC-PURCHASE-ORDER-004: Single line item status update
# ---------------------------------------------------------------------------


class LineItemStatusUpdateView(APIView):
    """
    PATCH /api/purchase-orders/line-items/<pk>/status/

    Updates the purchase_status of a single LineItem.
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

        updated_count = existing.update(purchase_status=purchase_status_value)

        return Response(
            {
                "updated_count": updated_count,
                "missing_ids": missing_ids,
            },
            status=status.HTTP_200_OK,
        )


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
