import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework import generics
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import ExchangeRate, Order
from .serializers import ExchangeRateSerializer, OrderDetailSerializer, OrderListSerializer, OrderNoteSerializer
from .shopify_orders import sync_single_order_from_shopify, sync_store


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
            "line_items", "shipping_lines", "refunds"
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


class OrderPagination(PageNumberPagination):
    page_size = 50


class OrderListView(ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        qs = Order.objects.prefetch_related("refunds", "line_items", "customer").order_by(
            "-shopify_created_at"
        )
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

        return qs


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
            "line_items", "shipping_lines", "refunds"
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
