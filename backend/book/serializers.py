from rest_framework import serializers

from book.constants import ETOILE_STATUS_LABELS
from book.models import (
    BookNote,
    EtoileBookInfo,
    EtoileBookInven,
    EtoileShopifyProduct,
    Info,
    Shopify_product,
)

# Only ETOILE status 80 means the book is actually live on the ETOILE store;
# -1 / 0 / 12 are registered-but-not-selling states (see ETOILE_STATUS_LABELS).
ETOILE_LISTED_STATUS = 80


# @MX:ANCHOR: [AUTO] BookDetailSerializer — primary read serializer for book search results
# @MX:REASON: REQ-SEARCH-007/011 define the response contract; callers include BookListViewSet and any future list endpoints
class BookDetailSerializer(serializers.Serializer):
    """Flat book view: Inven + Info + ETOILE listing state (search results + list)."""
    id = serializers.IntegerField()
    inven_SKU = serializers.CharField()
    name = serializers.CharField(source="info.name")
    cover_image_url = serializers.CharField(source="info.cover_image_url")
    status_of_shopify = serializers.IntegerField()
    etoile_listed = serializers.SerializerMethodField()
    etoile_status_label = serializers.SerializerMethodField()

    def _etoile(self, obj):
        # Reverse OneToOne: RelatedObjectDoesNotExist subclasses AttributeError, so the
        # getattr default covers "no ETOILE record". Requires select_related('etoile_inven')
        # upstream — without it this is one query per row.
        return getattr(obj, "etoile_inven", None)

    def get_etoile_listed(self, obj) -> bool:
        etoile = self._etoile(obj)
        return etoile is not None and etoile.status_of_shopify == ETOILE_LISTED_STATUS

    def get_etoile_status_label(self, obj) -> str:
        etoile = self._etoile(obj)
        if etoile is None:
            return "미등록"
        if etoile.status_of_shopify is None:
            return "상태 없음"
        return ETOILE_STATUS_LABELS.get(etoile.status_of_shopify, "정의되지 않은 상태")


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


# ---------------------------------------------------------------------------
# SPEC-BOOK-EDIT-001 serializers
# ---------------------------------------------------------------------------

class ShopifyProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shopify_product
        fields = [
            "id", "product_id", "variant_id", "inventory_item_id",
            "shopify_price", "is_new_arrival", "image_url",
        ]


class BookNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookNote
        fields = [
            "id", "note_type", "content", "is_resolved",
            "resolved_at", "created_by", "created_at",
        ]


class EtoileShopifyProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtoileShopifyProduct
        fields = [
            "id", "product_id", "variant_id", "inventory_item_id",
            "shopify_price", "is_new_arrival", "image_url",
        ]


class EtoileBookInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtoileBookInfo
        fields = ["id", "name_en", "desc_en", "preview_urls", "tags", "updated_at"]


class EtoileBookInvenSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtoileBookInven
        fields = ["id", "status_of_shopify", "updated_at"]


class InfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Info
        fields = [
            "id", "status", "price_sale", "name", "useruse1", "useruse2", "price",
            "opndate", "outrt2", "qty", "retyn",
            "booxen_cate_cd1", "booxen_cate_cd2", "booxen_cate_cd3",
            "page", "weight", "kyobo_weight", "kyobo_status", "kyobo_supply_price",
            "yes24_weight", "aladin_weight", "manual_weight",
            "dim1", "dim2", "dim3", "image_detail",
            "cover_image_url", "cover_image_url2",
            "desc_table", "desc_pub", "desc_author", "desc_desc",
            "kyobo_category1", "kyobo_category2", "kyobo_category3",
            "kyobo_category4", "kyobo_category5",
            "updated_at",
        ]


# SPEC-FAST-LISTING-ADD-001 serializer
class FastListingSkuBulkSerializer(serializers.Serializer):
    """Validate fast-listing bulk request — skus must be a non-empty list."""
    skus = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )


# SPEC-INVEN-ADD-001 serializer
class InvenSkuBulkAddSerializer(serializers.Serializer):
    """Validate bulk SKU add request — skus must be a non-empty list."""
    skus = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )


# SPEC-ETOILE-INVEN-ADD-001 serializer
class EtoileInvenSkuBulkAddSerializer(serializers.Serializer):
    """Validate Etoile bulk SKU add request — skus must be a non-empty list."""
    skus = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )


class InfoUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH /api/book/{id}/info/ — all fields optional (partial update)."""
    class Meta:
        model = Info
        fields = [
            "status", "price_sale", "name", "useruse1", "useruse2", "price",
            "opndate", "qty",
            "booxen_cate_cd1", "booxen_cate_cd2", "booxen_cate_cd3",
            "page", "weight", "kyobo_weight", "kyobo_status", "kyobo_supply_price",
            "yes24_weight", "aladin_weight", "manual_weight",
            "dim1", "dim2", "dim3", "image_detail",
            "cover_image_url", "cover_image_url2",
            "desc_table", "desc_pub", "desc_author", "desc_desc",
            "kyobo_category1", "kyobo_category2", "kyobo_category3",
            "kyobo_category4", "kyobo_category5",
        ]
        extra_kwargs = {
            "dim1": {"allow_null": True},
            "dim2": {"allow_null": True},
            "dim3": {"allow_null": True},
            "manual_weight": {"allow_null": True},
            "cover_image_url2": {"allow_null": True},
            "image_detail": {"allow_blank": True},
        }
