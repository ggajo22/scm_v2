from django.urls import path

from book.views import BookListViewSet, DashboardMetricsView

urlpatterns = [
    path("book/dashboard/metrics/", DashboardMetricsView.as_view(), name="book-dashboard-metrics"),
    # REQ-SEARCH-001: book search endpoint
    path(
        "book/search/",
        BookListViewSet.as_view({"get": "list"}),
        name="book-search",
    ),
]
