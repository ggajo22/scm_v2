from django.urls import path

from .purchase_order_views import (
    ConfirmOrderView,
    DailyReviewExcelView,
    DistributorVendorRuleDeleteView,
    DistributorVendorRuleListCreateView,
    GenerateOrderFileView,
    LineItemBulkStatusUpdateView,
    LineItemStatusUpdateView,
    PurchaseOrderListView,
    RunComparisonView,
    UnorderedItemsView,
    UploadDailyReviewView,
    UploadVendorFileView,
    VendorComparisonView,
)
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
