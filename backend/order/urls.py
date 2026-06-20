from django.urls import path

from .views import OrderListView, OrderSyncView

urlpatterns = [
    path("orders/sync/", OrderSyncView.as_view(), name="order-sync"),
    path("orders/", OrderListView.as_view(), name="order-list"),
]
