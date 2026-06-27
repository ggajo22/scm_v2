from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from .models import Customer, LineItem, Order, Refund, ShippingAddress, ShippingLine


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

    def get_margin_amount(self, obj: Order):
        # Returns Decimal margin or None if ALL line_items have null confirmed_price.
        # Uses prefetch_related line_items (already prefetched by OrderDetailView).
        # IMPORTANT: uses Decimal arithmetic only — never float().
        line_items = obj.line_items.all()
        has_any_confirmed = False
        confirmed_cost = Decimal("0")
        for item in line_items:
            if item.confirmed_price is not None:
                has_any_confirmed = True
                confirmed_cost += Decimal(str(item.confirmed_price)) * (item.quantity or 0)
        if not has_any_confirmed:
            return None
        total = Decimal(str(obj.total_price or "0"))
        return str(total - confirmed_cost)

    def get_margin_rate(self, obj: Order):
        # Returns margin_rate = (margin_amount / total_price) * 100, 2dp ROUND_HALF_UP.
        # Returns None if margin_amount is None or total_price is 0.
        margin_amount_str = self.get_margin_amount(obj)
        if margin_amount_str is None:
            return None
        total = Decimal(str(obj.total_price or "0"))
        if total == Decimal("0"):
            return None
        margin = Decimal(margin_amount_str)
        rate = (margin / total * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return str(rate)


class OrderNoteSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "shopify_order_id", "store_type", "order_number", "name",
            "note", "note_resolved", "shopify_created_at", "customer",
        ]
