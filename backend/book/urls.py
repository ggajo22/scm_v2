from django.urls import path

from book.views import (
    BookInfoUpdateView,
    BookListViewSet,
    BookNoteCreateView,
    BookNoteResolveView,
    BookRetrieveView,
    BooksenCategoryListView,
    BookShopifyStatusView,
    DashboardMetricsView,
    EtoileShopifyStatusView,
    EtoileTagsView,
    InvenSkuBulkAddView,
    ShopifyLiveInfoView,
)

urlpatterns = [
    # SPEC-INVEN-ADD-001: bulk ISBN add
    path("book/inven-skus/", InvenSkuBulkAddView.as_view(), name="book-inven-skus"),
    path("book/dashboard/metrics/", DashboardMetricsView.as_view(), name="book-dashboard-metrics"),
    path(
        "book/booksen-categories/",
        BooksenCategoryListView.as_view(),
        name="book-booksen-categories",
    ),
    # REQ-SEARCH-001: book search endpoint
    path(
        "book/search/",
        BookListViewSet.as_view({"get": "list"}),
        name="book-search",
    ),
    # SPEC-BOOK-EDIT-001: book detail and edit endpoints
    # Note: specific path "book/notes/<int:pk>/resolve/" must come before "book/<int:pk>/"
    path("book/notes/<int:pk>/resolve/", BookNoteResolveView.as_view(), name="book-note-resolve"),
    path("book/<int:pk>/", BookRetrieveView.as_view(), name="book-detail"),
    path("book/<int:pk>/info/", BookInfoUpdateView.as_view(), name="book-info-update"),
    path("book/<int:pk>/notes/", BookNoteCreateView.as_view(), name="book-note-create"),
    path(
        "book/<int:pk>/shopify-status/",
        BookShopifyStatusView.as_view(),
        name="book-shopify-status",
    ),
    path(
        "book/<int:pk>/etoile-shopify-status/",
        EtoileShopifyStatusView.as_view(),
        name="book-etoile-shopify-status",
    ),
    path("book/<int:pk>/etoile-tags/", EtoileTagsView.as_view(), name="book-etoile-tags"),
    # SPEC-SHOPIFY-INFO-001: real-time Shopify product info
    path(
        "book/<int:pk>/shopify-live-info/",
        ShopifyLiveInfoView.as_view(),
        name="book-shopify-live-info",
    ),
]
