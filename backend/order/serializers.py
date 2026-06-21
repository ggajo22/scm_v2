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
    class Meta:
        model = LineItem
        fields = [
            "id", "shopify_line_item_id", "title", "variant_title", "sku",
            "quantity", "price", "total_discount", "fulfillment_status", "vendor", "grams",
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

    class Meta:
        model = Order
        fields = [
            "id", "shopify_order_id", "store_type", "order_number", "name",
            "email", "phone", "financial_status", "fulfillment_status",
            "total_price", "subtotal_price", "total_tax", "total_discounts",
            "total_shipping_price_set", "currency", "gateway", "note", "tags",
            "cancel_reason", "source_name", "shopify_created_at",
            "shopify_updated_at", "closed_at", "cancelled_at", "processed_at",
            "has_refund", "customer", "shipping_address",
            "line_items", "shipping_lines", "refunds",
        ]

    def get_has_refund(self, obj: Order) -> bool:
        return obj.refunds.exists()
