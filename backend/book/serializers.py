from rest_framework import serializers


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
