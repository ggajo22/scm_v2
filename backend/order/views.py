from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Order
from .serializers import OrderListSerializer
from .shopify_orders import sync_store


class OrderSyncView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        store_results = {}
        for store_type in ["gimssine", "etoile"]:
            try:
                with transaction.atomic():
                    result = sync_store(store_type)
                    store_results[store_type] = result
            except Exception as e:
                store_results[store_type] = {
                    "synced_count": 0,
                    "updated_count": 0,
                    "error": str(e),
                }

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

        return qs
