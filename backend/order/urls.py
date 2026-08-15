from django.urls import path

from .purchase_order_views import (
    ConfirmOrderView,
    DailyReviewExcelView,
    DamagedExchangeSearchView,
    DamagedExchangeSubmitView,
    DistributorVendorRuleDeleteView,
    DistributorVendorRuleListCreateView,
    ExcludedItemsView,
    GenerateOrderFileView,
    LineItemBulkRackNumberUpdateView,
    LineItemBulkStatusUpdateView,
    LineItemLogisticsStatusBulkUpdateView,
    LineItemLogisticsStatusUpdateView,
    LineItemRackNumberSummaryView,
    LineItemRackNumberUpdateView,
    LineItemStatusUpdateView,
    OutboundForceCandidateView,
    OutboundForceProcessView,
    OutboundProcessView,
    PurchaseOrderListView,
    RunComparisonView,
    UnorderedItemsView,
    UploadDailyReviewView,
    UploadOutboundView,
    UploadRackNumberView,
    UploadVendorFileView,
    UploadVendorShipmentView,
    UploadWarehouseReceiptView,
    VendorComparisonView,
)
from .shopify_sku_set_views import ShopifySkuSetDetailView, ShopifySkuSetListCreateView
from .views import (
    ExchangeRateDetailView,
    ExchangeRateListCreateView,
    LineItemNoteExportView,
    LineItemNoteListCreateView,
    LineItemNoteResolveView,
    LineItemNoteUnresolvedListView,
    OrderDetailView,
    OrderListView,
    OrderNoteListView,
    OrderNoteResolveView,
    OrderResyncView,
    OrderSyncView,
)
from .warehouse_views import (
    WarehouseStockBulkView,
    WarehouseStockDeleteView,
    WarehouseStockListView,
    WarehouseStockUpsertView,
)

urlpatterns = [
    # SPEC-SHOPIFY-SKU-SET-001: Bundle SKU mapping endpoints
    path("shopify-sku-sets/", ShopifySkuSetListCreateView.as_view(), name="shopify-sku-set-list"),
    path("shopify-sku-sets/<str:bundle_sku>/", ShopifySkuSetDetailView.as_view(), name="shopify-sku-set-detail"),
    # Shopify order sync and list
    path("orders/sync/", OrderSyncView.as_view(), name="order-sync"),
    path("orders/notes/", OrderNoteListView.as_view(), name="order-note-list"),
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>/sync/", OrderResyncView.as_view(), name="order-resync"),
    path("orders/<int:pk>/resolve-note/", OrderNoteResolveView.as_view(), name="order-note-resolve"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    # Purchase order endpoints (more specific paths must come before the generic list)
    path("purchase-orders/daily-review-excel/", DailyReviewExcelView.as_view(), name="po-daily-review-excel"),
    path("purchase-orders/upload-daily-review/", UploadDailyReviewView.as_view(), name="po-upload-daily-review"),
    path("purchase-orders/unordered/", UnorderedItemsView.as_view(), name="po-unordered"),
    # SPEC-ORDER-018: read-only excluded-items list (restore candidates).
    # Fully static path, so the line-items/<int:pk>/... patterns below cannot
    # shadow it — "excluded-items" is not an int (same reasoning as the
    # SPEC-ORDER-014 rack-number-summary path). Must stay above the generic
    # "purchase-orders/" list at the bottom of this block.
    path("purchase-orders/excluded-items/", ExcludedItemsView.as_view(), name="po-excluded-items"),
    path("purchase-orders/generate-order-file/", GenerateOrderFileView.as_view(), name="po-generate"),
    path("purchase-orders/upload-vendor-file/", UploadVendorFileView.as_view(), name="po-upload"),
    path("purchase-orders/run-comparison/", RunComparisonView.as_view(), name="po-run-comparison"),
    path("purchase-orders/comparison/", VendorComparisonView.as_view(), name="po-comparison"),
    path("purchase-orders/confirm/", ConfirmOrderView.as_view(), name="po-confirm"),
    # SPEC-PURCHASE-ORDER-004: bulk-status must precede <int:pk>/status/ to avoid URL conflict
    path("purchase-orders/line-items/bulk-status/", LineItemBulkStatusUpdateView.as_view(), name="po-line-item-bulk-status"),
    path("purchase-orders/line-items/<int:pk>/status/", LineItemStatusUpdateView.as_view(), name="po-line-item-status"),
    # SPEC-PURCHASE-ORDER-011: damaged-exchange row-level submission, same
    # <int:pk>/<segment>/ group as status/logistics-status/rack-number above
    # ("damaged-exchange" is a distinct literal segment, so no shadowing risk).
    path(
        "purchase-orders/line-items/<int:pk>/damaged-exchange/",
        DamagedExchangeSubmitView.as_view(),
        name="po-line-item-damaged-exchange",
    ),
    # SPEC-ORDER-011: bulk-logistics-status must precede <int:pk>/logistics-status/
    path(
        "purchase-orders/line-items/bulk-logistics-status/",
        LineItemLogisticsStatusBulkUpdateView.as_view(),
        name="po-line-item-bulk-logistics-status",
    ),
    path(
        "purchase-orders/line-items/<int:pk>/logistics-status/",
        LineItemLogisticsStatusUpdateView.as_view(),
        name="po-line-item-logistics-status",
    ),
    # SPEC-ORDER-013: bulk-rack-number must precede <int:pk>/rack-number/
    path(
        "purchase-orders/line-items/bulk-rack-number/",
        LineItemBulkRackNumberUpdateView.as_view(),
        name="po-line-item-bulk-rack-number",
    ),
    path(
        "purchase-orders/line-items/<int:pk>/rack-number/",
        LineItemRackNumberUpdateView.as_view(),
        name="po-line-item-rack-number",
    ),
    path(
        "purchase-orders/upload-rack-number/",
        UploadRackNumberView.as_view(),
        name="po-upload-rack-number",
    ),
    # SPEC-ORDER-014: cross-order read-only rack_number summary (GET only,
    # no <int:pk> conflict possible — path segment is all letters/hyphens)
    path(
        "purchase-orders/line-items/rack-number-summary/",
        LineItemRackNumberSummaryView.as_view(),
        name="po-line-item-rack-number-summary",
    ),
    # SPEC-PURCHASE-ORDER-011: cross-order read-only ISBN search (GET only,
    # no <int:pk> conflict possible — same reasoning as rack-number-summary
    # above).
    path(
        "purchase-orders/line-items/damaged-exchange-search/",
        DamagedExchangeSearchView.as_view(),
        name="po-line-item-damaged-exchange-search",
    ),
    # SPEC-ORDER-015: outbound processing. Both paths are fully static (no
    # <int:pk> segment), so the line-items/<int:pk>/... patterns above cannot
    # shadow them — "outbound-process" is not an int and never matches <int:pk>
    # (same reasoning as the SPEC-ORDER-014 rack-number-summary path).
    path(
        "purchase-orders/line-items/outbound-process/",
        OutboundProcessView.as_view(),
        name="po-line-item-outbound-process",
    ),
    path(
        "purchase-orders/upload-outbound/",
        UploadOutboundView.as_view(),
        name="po-upload-outbound",
    ),
    # SPEC-ORDER-016: force outbound processing. Both paths are fully static
    # (no <int:pk> segment), so the line-items/<int:pk>/... patterns above
    # cannot shadow them — "outbound-force-candidates" is not an int, and those
    # patterns carry an extra trailing segment besides. Placed next to the
    # SPEC-ORDER-015 outbound pair for locality (same reasoning as that pair).
    path(
        "purchase-orders/line-items/outbound-force-candidates/",
        OutboundForceCandidateView.as_view(),
        name="po-line-item-outbound-force-candidates",
    ),
    path(
        "purchase-orders/line-items/outbound-force-process/",
        OutboundForceProcessView.as_view(),
        name="po-line-item-outbound-force-process",
    ),
    path(
        "purchase-orders/upload-vendor-shipment/",
        UploadVendorShipmentView.as_view(),
        name="po-upload-vendor-shipment",
    ),
    path(
        "purchase-orders/upload-warehouse-receipt/",
        UploadWarehouseReceiptView.as_view(),
        name="po-upload-warehouse-receipt",
    ),
    path("purchase-orders/vendor-rules/", DistributorVendorRuleListCreateView.as_view(), name="po-rules"),
    path("purchase-orders/vendor-rules/<int:pk>/", DistributorVendorRuleDeleteView.as_view(), name="po-rule-delete"),
    path("purchase-orders/", PurchaseOrderListView.as_view(), name="po-list"),
    # SPEC-ORDER-010: LineItemNote endpoints
    path("orders/line-item-notes/export/", LineItemNoteExportView.as_view(), name="line-item-note-export"),
    path("orders/line-item-notes/", LineItemNoteUnresolvedListView.as_view(), name="line-item-note-unresolved"),
    path("orders/line-item-notes/<int:pk>/resolve/", LineItemNoteResolveView.as_view(), name="line-item-note-resolve"),
    path("orders/line-items/<int:pk>/notes/", LineItemNoteListCreateView.as_view(), name="line-item-note-list-create"),
    # ExchangeRate endpoints (SPEC-ORDER-009)
    path("exchange-rates/", ExchangeRateListCreateView.as_view(), name="exchange-rate-list"),
    path("exchange-rates/<str:date>/", ExchangeRateDetailView.as_view(), name="exchange-rate-detail"),
    # Warehouse stock endpoints
    path("warehouse/stock/bulk/", WarehouseStockBulkView.as_view(), name="warehouse-stock-bulk"),
    path("warehouse/stock/<int:pk>/", WarehouseStockDeleteView.as_view(), name="warehouse-stock-delete"),
    path("warehouse/stock/", WarehouseStockListView.as_view(), name="warehouse-stock-list"),
    path("warehouse/stock/upsert/", WarehouseStockUpsertView.as_view(), name="warehouse-stock-upsert"),
]
