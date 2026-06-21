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
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .excel_utils import (
    auto_select_distributor,
    generate_order_excel,
    parse_vendor_excel,
)
from .models import DistributorVendorRule, LineItem, PurchaseOrder, VendorComparison

VALID_DISTRIBUTORS = {"bookseen", "kyobo", "choeumgoyuk", "agape"}
VENDOR_FILE_DISTRIBUTORS = {"bookseen", "kyobo"}
VENDOR_RULE_DISTRIBUTORS = {"choeumgoyuk", "agape"}

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
        line_items = (
            LineItem.objects.filter(sku__isnull=False)
            .exclude(purchase_orders__isnull=False)
            .select_related("order")
            .order_by("-order__shopify_created_at")
        )

        rule_map: dict[str, str] = dict(
            DistributorVendorRule.objects.values_list("publisher_name", "distributor")
        )

        results = []
        for li in line_items:
            order = li.order
            order_name = order.name or (f"#{order.order_number}" if order.order_number else None)
            results.append(
                {
                    "id": li.pk,
                    "order_name": order_name,
                    "sku": li.sku,
                    "title": li.title or "",
                    "vendor": li.vendor or "",
                    "quantity": li.quantity or 0,
                    "auto_distributor": rule_map.get(li.vendor or ""),
                }
            )

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

        # Aggregate quantities for requested SKUs from unordered LineItems
        requested = set(skus)
        agg_qs = (
            LineItem.objects.filter(sku__in=requested)
            .exclude(purchase_orders__isnull=False)
            .values("sku", "title")
            .annotate(total_quantity=Sum("quantity"))
        )
        found_map: dict[str, dict] = {row["sku"]: row for row in agg_qs}
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

        comparisons = []
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
                    "bookseen_available": available,
                    "bookseen_price": price,
                    "bookseen_stock": stock,
                    "bookseen_returnable": returnable,
                    "bookseen_status": vendor_status,
                    "bookseen_arrival": arrival,
                }
            else:  # kyobo
                defaults = {
                    "kyobo_available": available,
                    "kyobo_price": price,
                    "kyobo_stock": stock,
                    "kyobo_returnable": returnable,
                    "kyobo_status": vendor_status,
                    "kyobo_publisher": publisher,
                    "kyobo_ordered_qty": ordered_qty,
                    "kyobo_total_price": total_price,
                }

            vc, _ = VendorComparison.objects.update_or_create(sku=sku, defaults=defaults)

            # Re-fetch to compute auto-selection with latest values
            vc.refresh_from_db()
            selected = auto_select_distributor(
                bookseen_available=vc.bookseen_available,
                bookseen_price=vc.bookseen_price,
                kyobo_available=vc.kyobo_available,
                kyobo_price=vc.kyobo_price,
            )
            if selected != vc.selected_distributor:
                vc.selected_distributor = selected
                vc.save(update_fields=["selected_distributor"])

            comparisons.append(
                {"sku": sku, "available": available, "price": str(price) if price is not None else None}
            )

        return Response(
            {
                "parsed_count": len(comparisons),
                "distributor": distributor,
                "comparisons": comparisons,
            }
        )


# ---------------------------------------------------------------------------
# M4b: Vendor comparison list
# ---------------------------------------------------------------------------


class VendorComparisonView(APIView):
    """
    GET /api/purchase-orders/comparison/

    Returns all VendorComparison records.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        qs = VendorComparison.objects.all().order_by("sku")
        results = []
        for vc in qs:
            results.append(
                {
                    "sku": vc.sku,
                    "bookseen_available": vc.bookseen_available,
                    "bookseen_price": str(vc.bookseen_price) if vc.bookseen_price is not None else None,
                    "bookseen_stock": vc.bookseen_stock,
                    "bookseen_returnable": vc.bookseen_returnable,
                    "bookseen_status": vc.bookseen_status,
                    "bookseen_arrival": vc.bookseen_arrival,
                    "kyobo_available": vc.kyobo_available,
                    "kyobo_price": str(vc.kyobo_price) if vc.kyobo_price is not None else None,
                    "kyobo_stock": vc.kyobo_stock,
                    "kyobo_returnable": vc.kyobo_returnable,
                    "kyobo_status": vc.kyobo_status,
                    "kyobo_publisher": vc.kyobo_publisher,
                    "kyobo_ordered_qty": vc.kyobo_ordered_qty,
                    "kyobo_total_price": str(vc.kyobo_total_price) if vc.kyobo_total_price is not None else None,
                    "selected_distributor": vc.selected_distributor,
                }
            )
        return Response({"count": len(results), "results": results})


# ---------------------------------------------------------------------------
# M5: Confirm orders
# ---------------------------------------------------------------------------


class ConfirmOrderView(APIView):
    """
    POST /api/purchase-orders/confirm/

    Body: {"items": [{"sku": str, "distributor": str, "quantity": int, "unit_price": str}]}

    Creates PurchaseOrder records and links unordered LineItems via M2M.
    Uses @transaction.atomic to prevent partial writes.

    # @MX:WARN: [AUTO] Atomic transaction with select_for_update — potential lock contention under high concurrency
    # @MX:REASON: select_for_update() needed to prevent double-linking of LineItems; deadlock risk if multiple confirm requests overlap
    """

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

                    if not sku or not dist or qty is None:
                        raise ValueError("sku, distributor, and quantity are required for each item.")

                    if dist not in VALID_DISTRIBUTORS:
                        raise ValueError(f"Invalid distributor: {dist}")

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

        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"created_count": len(created_ids), "purchase_order_ids": created_ids},
            status=status.HTTP_201_CREATED,
        )


class ConflictError(Exception):
    """Raised when a 409 Conflict response should be returned."""


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
    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "sku", "title", "distributor", "quantity",
            "unit_price", "status", "created_at", "updated_at",
        ]


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
        qs = PurchaseOrder.objects.all().order_by("-created_at")
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
        serializer = PurchaseOrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
