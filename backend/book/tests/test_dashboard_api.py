"""
Tests for GET /api/book/dashboard/metrics/ — SPEC-BOOK-DASHBOARD-001
REQ-BD-001 through REQ-BD-011
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from book.models import BookNote, Info, Inven, Shopify_product

User = get_user_model()

DASHBOARD_URL = "/api/book/dashboard/metrics/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="dashboard_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.mark.django_db
class TestDashboardAuthGuard:
    """REQ-BD-001: unauthenticated request must return 401."""

    def test_unauthenticated_returns_401(self, api_client):
        resp = api_client.get(DASHBOARD_URL)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestDashboardResponseShape:
    """REQ-BD-002: authenticated request returns 200 with all 8 fields as integers."""

    def test_authenticated_returns_all_8_fields(self, auth_client):
        resp = auth_client.get(DASHBOARD_URL)
        assert resp.status_code == 200
        data = resp.data

        # All 8 required fields must be present
        assert "status_counts" in data
        assert "shopify_created_24h" in data
        assert "error_total" in data
        assert "error_rows" in data
        assert "waiting_total" in data
        assert "unresolved_note_count" in data
        assert "sale_zero_count" in data
        assert "cost_zero_count" in data

        # Numeric fields must be integers
        assert isinstance(data["shopify_created_24h"], int)
        assert isinstance(data["error_total"], int)
        assert isinstance(data["waiting_total"], int)
        assert isinstance(data["unresolved_note_count"], int)
        assert isinstance(data["sale_zero_count"], int)
        assert isinstance(data["cost_zero_count"], int)

        # List fields must be lists
        assert isinstance(data["status_counts"], list)
        assert isinstance(data["error_rows"], list)


@pytest.mark.django_db
class TestDashboardErrorMetrics:
    """REQ-BD-005/006: error_total and error_rows aggregate correctly."""

    def test_error_metrics_aggregation(self, auth_client):
        # Create 3 Inven with status=31 (error) and 2 with status=44 (error)
        for _ in range(3):
            Inven.objects.create(
                inven_SKU="SKU-31",
                vendor="v",
                store="s",
                status_of_shopify=31,
            )
        for _ in range(2):
            Inven.objects.create(
                inven_SKU="SKU-44",
                vendor="v",
                store="s",
                status_of_shopify=44,
            )

        resp = auth_client.get(DASHBOARD_URL)
        assert resp.status_code == 200
        data = resp.data

        assert data["error_total"] == 5

        # error_rows must contain both status 31 and 44
        error_statuses = {row["status"] for row in data["error_rows"]}
        assert 31 in error_statuses
        assert 44 in error_statuses

        # Verify counts in error_rows
        row_31 = next(r for r in data["error_rows"] if r["status"] == 31)
        row_44 = next(r for r in data["error_rows"] if r["status"] == 44)
        assert row_31["count"] == 3
        assert row_44["count"] == 2


@pytest.mark.django_db
class TestDashboardEmptyData:
    """REQ-BD-003: with no records, all numeric fields are 0 and list fields are empty."""

    def test_empty_data_returns_zeros(self, auth_client):
        resp = auth_client.get(DASHBOARD_URL)
        assert resp.status_code == 200
        data = resp.data

        assert data["shopify_created_24h"] == 0
        assert data["error_total"] == 0
        assert data["waiting_total"] == 0
        assert data["unresolved_note_count"] == 0
        assert data["sale_zero_count"] == 0
        assert data["cost_zero_count"] == 0
        assert data["status_counts"] == []
        assert data["error_rows"] == []


@pytest.mark.django_db
class TestDashboardShopify24hBoundary:
    """REQ-BD-004: Shopify_product created exactly 24h ago must NOT be counted."""

    def test_shopify_created_24h_boundary(self, auth_client):
        from django.utils import timezone

        inven = Inven.objects.create(
            inven_SKU="SKU-BOUNDARY",
            vendor="v",
            store="s",
            status_of_shopify=100,
        )

        # Create a Shopify_product with created_at exactly 24h ago (boundary — not within 24h)
        exactly_24h_ago = timezone.now() - timedelta(hours=24)

        # Patch timezone.now so the filter boundary is predictable
        with patch("book.views.timezone.now", return_value=timezone.now()):
            # Manually set created_at to exactly 24h ago via update (bypasses auto_now_add)
            sp = Shopify_product.objects.create(inven=inven, product_id="P-BOUNDARY")
            Shopify_product.objects.filter(pk=sp.pk).update(created_at=exactly_24h_ago)

            resp = auth_client.get(DASHBOARD_URL)

        assert resp.status_code == 200
        # Exactly 24h ago uses __gt (strictly greater than), so this should NOT be counted
        assert resp.data["shopify_created_24h"] == 0
