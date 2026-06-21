from django.urls import path

from .purchase_order_views import (
    ConfirmOrderView,
    DistributorVendorRuleDeleteView,
    DistributorVendorRuleListCreateView,
    GenerateOrderFileView,
    PurchaseOrderListView,
    UnorderedItemsView,
    UploadVendorFileView,
    VendorComparisonView,
)
from .views import OrderDetailView, OrderListView, OrderNoteListView, OrderNoteResolveView, OrderResyncView, OrderSyncView
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
    path("purchase-orders/unordered/", UnorderedItemsView.as_view(), name="po-unordered"),
    path("purchase-orders/generate-order-file/", GenerateOrderFileView.as_view(), name="po-generate"),
    path("purchase-orders/upload-vendor-file/", UploadVendorFileView.as_view(), name="po-upload"),
    path("purchase-orders/comparison/", VendorComparisonView.as_view(), name="po-comparison"),
    path("purchase-orders/confirm/", ConfirmOrderView.as_view(), name="po-confirm"),
    path("purchase-orders/vendor-rules/", DistributorVendorRuleListCreateView.as_view(), name="po-rules"),
    path("purchase-orders/vendor-rules/<int:pk>/", DistributorVendorRuleDeleteView.as_view(), name="po-rule-delete"),
    path("purchase-orders/", PurchaseOrderListView.as_view(), name="po-list"),
    # Warehouse stock endpoints
    path("warehouse/stock/bulk/", WarehouseStockBulkView.as_view(), name="warehouse-stock-bulk"),
    path("warehouse/stock/<int:pk>/", WarehouseStockDeleteView.as_view(), name="warehouse-stock-delete"),
    path("warehouse/stock/", WarehouseStockListView.as_view(), name="warehouse-stock-list"),
    path("warehouse/stock/upsert/", WarehouseStockUpsertView.as_view(), name="warehouse-stock-upsert"),
]
