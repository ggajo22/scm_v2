from django.urls import path

from book.views import DashboardMetricsView

urlpatterns = [
    path("book/dashboard/metrics/", DashboardMetricsView.as_view(), name="book-dashboard-metrics"),
]
