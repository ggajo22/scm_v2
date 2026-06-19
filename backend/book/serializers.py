from rest_framework import serializers


# @MX:ANCHOR: [AUTO] BookDetailSerializer — primary read serializer for book search results
# @MX:REASON: REQ-SEARCH-007/011 define the response contract; callers include BookListViewSet and any future list endpoints
class BookDetailSerializer(serializers.Serializer):
    """Flat book representation combining Inven + Info fields."""
    inven_SKU = serializers.CharField()
    name = serializers.CharField(source="info.name")
    price_sale = serializers.FloatField(source="info.price_sale")
    status_of_shopify = serializers.IntegerField()


class StatusCountSerializer(serializers.Serializer):
    status = serializers.IntegerField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class DashboardMetricsSerializer(serializers.Serializer):
    status_counts = StatusCountSerializer(many=True)
    shopify_created_24h = serializers.IntegerField()
    error_total = serializers.IntegerField()
    error_rows = StatusCountSerializer(many=True)
    waiting_total = serializers.IntegerField()
    unresolved_note_count = serializers.IntegerField()
    sale_zero_count = serializers.IntegerField()
    cost_zero_count = serializers.IntegerField()
