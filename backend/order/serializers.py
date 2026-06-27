from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from .models import Customer, ExchangeRate, LineItem, Order, Refund, ShippingAddress, ShippingLine


class CustomerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["shopify_customer_id", "first_name", "last_name", "email"]


class OrderListSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    has_refund = serializers.SerializerMethodField()
    line_items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "shopify_order_id",
            "store_type",
            "order_number",
            "name",
            "financial_status",
            "fulfillment_status",
            "total_price",
            "currency",
            "shopify_created_at",
            "customer",
            "has_refund",
            "line_items_count",
            "location",
        ]

    def get_has_refund(self, obj):
        # relies on prefetch_related("refunds") in the view queryset
        return obj.refunds.exists()

    def get_line_items_count(self, obj):
        return obj.line_items.count()


# ---------------------------------------------------------------------------
# SPEC-ORDER-003: Order Detail serializers
# ---------------------------------------------------------------------------


class CustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["shopify_customer_id", "first_name", "last_name", "email", "phone"]


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = [
            "name", "first_name", "last_name", "address1", "address2",
            "city", "province", "province_code", "country", "country_code", "zip", "phone",
        ]


class LineItemDetailSerializer(serializers.ModelSerializer):
    # @MX:ANCHOR: [AUTO] LineItemDetailSerializer — serializes confirmed purchase fields
    # @MX:REASON: Extended by SPEC-ORDER-008; confirmed_price/distributor/at added for margin calc
    confirmed_price = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, read_only=True)
    confirmed_distributor = serializers.CharField(allow_null=True, read_only=True)
    confirmed_at = serializers.DateTimeField(allow_null=True, read_only=True)

    class Meta:
        model = LineItem
        fields = [
            "id", "shopify_line_item_id", "title", "variant_title", "sku",
            "quantity", "price", "total_discount", "fulfillment_status", "vendor", "grams",
            "location", "note",
            "confirmed_price", "confirmed_distributor", "confirmed_at",
        ]


class ShippingLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingLine
        fields = ["title", "code", "price", "source"]


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            "shopify_refund_id", "note", "shopify_created_at",
            "line_item_id", "quantity", "subtotal", "total_tax",
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    # @MX:ANCHOR: [AUTO] Fan-in >= 3: called by OrderDetailView, test suite, frontend client
    # @MX:REASON: Central serializer for order detail; all nested domain data flows through here
    customer = CustomerDetailSerializer(read_only=True)
    shipping_address = ShippingAddressSerializer(read_only=True)
    line_items = LineItemDetailSerializer(many=True, read_only=True)
    shipping_lines = ShippingLineSerializer(many=True, read_only=True)
    refunds = RefundSerializer(many=True, read_only=True)
    has_refund = serializers.SerializerMethodField()
    margin_amount = serializers.SerializerMethodField()
    margin_rate = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "shopify_order_id", "store_type", "order_number", "name",
            "email", "phone", "financial_status", "fulfillment_status",
            "total_price", "subtotal_price", "total_tax", "total_discounts",
            "total_shipping_price_set", "currency", "gateway", "note", "note_resolved", "tags",
            "cancel_reason", "source_name", "shopify_created_at",
            "shopify_updated_at", "closed_at", "cancelled_at", "processed_at",
            "has_refund", "customer", "shipping_address",
            "line_items", "shipping_lines", "refunds",
            "margin_amount", "margin_rate",
        ]

    def get_has_refund(self, obj: Order) -> bool:
        return obj.refunds.exists()

    def _get_exchange_rate(self, obj: Order):
        """
        Look up exchange rate for order date with fallback to prior date.
        Returns ExchangeRate instance or None.
        REQ-003, REQ-013
        """
        if not obj.shopify_created_at:
            return None
        order_date = obj.shopify_created_at.date()
        return ExchangeRate.objects.filter(
            effective_date__lte=order_date
        ).order_by("-effective_date").first()

    def get_margin_amount(self, obj: Order):
        """
        REQ-010, REQ-011:
        - USD total_price를 환율로 KRW 환산 후 confirmed_cost_krw 차감
        - 환율 없으면 None 반환
        - confirmed_price=null 항목은 부분 합산에서 제외
        """
        er = self._get_exchange_rate(obj)
        if er is None:
            return None
        confirmed_cost_krw = Decimal("0")
        has_any_confirmed = False
        for item in obj.line_items.all():
            if item.confirmed_price is not None:
                has_any_confirmed = True
                confirmed_cost_krw += item.confirmed_price * (item.quantity or 0)
        if not has_any_confirmed:
            return None
        total_price_krw = Decimal(str(obj.total_price or "0")) * er.rate
        return str(total_price_krw - confirmed_cost_krw)

    def get_margin_rate(self, obj: Order):
        """
        REQ-012, REQ-013:
        - 분모는 total_price_krw (KRW 환산값)
        - 환율 재조회 (API 호출당 최대 2 쿼리 — 허용 범위)
        """
        margin_str = self.get_margin_amount(obj)
        if margin_str is None:
            return None
        er = self._get_exchange_rate(obj)
        if er is None:
            return None
        total_price_krw = Decimal(str(obj.total_price or "0")) * er.rate
        if total_price_krw == Decimal("0"):
            return None
        rate = (Decimal(margin_str) / total_price_krw * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return str(rate)


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ["effective_date", "rate", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class OrderNoteSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "shopify_order_id", "store_type", "order_number", "name",
            "note", "note_resolved", "shopify_created_at", "customer",
        ]
