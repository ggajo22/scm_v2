from django.urls import path

from .purchase_order_views import (
    ConfirmOrderView,
    DailyReviewExcelView,
    DistributorVendorRuleDeleteView,
    DistributorVendorRuleListCreateView,
    GenerateOrderFileView,
    LineItemBulkRackNumberUpdateView,
    LineItemBulkStatusUpdateView,
    LineItemLogisticsStatusBulkUpdateView,
    LineItemLogisticsStatusUpdateView,
    LineItemRackNumberSummaryView,
    LineItemRackNumberUpdateView,
    LineItemStatusUpdateView,
    PurchaseOrderListView,
    RunComparisonView,
    UnorderedItemsView,
    UploadDailyReviewView,
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
    path("purchase-orders/generate-order-file/", GenerateOrderFileView.as_view(), name="po-generate"),
    path("purchase-orders/upload-vendor-file/", UploadVendorFileView.as_view(), name="po-upload"),
    path("purchase-orders/run-comparison/", RunComparisonView.as_view(), name="po-run-comparison"),
    path("purchase-orders/comparison/", VendorComparisonView.as_view(), name="po-comparison"),
    path("purchase-orders/confirm/", ConfirmOrderView.as_view(), name="po-confirm"),
    # SPEC-PURCHASE-ORDER-004: bulk-status must precede <int:pk>/status/ to avoid URL conflict
    path("purchase-orders/line-items/bulk-status/", LineItemBulkStatusUpdateView.as_view(), name="po-line-item-bulk-status"),
    path("purchase-orders/line-items/<int:pk>/status/", LineItemStatusUpdateView.as_view(), name="po-line-item-status"),
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
