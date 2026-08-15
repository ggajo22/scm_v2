"""Tests for GET /api/orders/sync-status/ (SPEC-PURCHASE-ORDER-011).

Exposes StoreSyncWatermark.last_run_at per store so a super_admin can see
whether the scheduled Shopify sync has silently stopped, even on a quiet
sync cycle where last_synced_updated_at does not move.
"""

from datetime import datetime, timezone as dt_timezone

import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import AdminUserFactory, SuperAdminFactory
from order.models import StoreSyncWatermark

SYNC_STATUS_URL = "/api/orders/sync-status/"


@pytest.fixture
def super_admin_client(db):
    user = SuperAdminFactory(username="sa_sync_status")
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin_client(db):
    user = AdminUserFactory(username="admin_sync_status")
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestOrderSyncStatusPermissions:
    def test_admin_role_forbidden(self, admin_client):
        resp = admin_client.get(SYNC_STATUS_URL)
        assert resp.status_code == 403

    def test_super_admin_role_allowed(self, super_admin_client):
        resp = super_admin_client.get(SYNC_STATUS_URL)
        assert resp.status_code == 200

    def test_unauthenticated_denied(self):
        resp = APIClient().get(SYNC_STATUS_URL)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestOrderSyncStatusResponseShape:
    def test_top_level_last_run_at_is_min_across_stores(self, super_admin_client):
        StoreSyncWatermark.objects.create(
            store_type="gimssine",
            last_run_at=datetime(2026, 8, 15, 10, 30, 27, tzinfo=dt_timezone.utc),
            last_synced_updated_at=datetime(2026, 8, 15, 7, 46, 17, tzinfo=dt_timezone.utc),
        )
        StoreSyncWatermark.objects.create(
            store_type="etoile",
            last_run_at=datetime(2026, 8, 15, 10, 30, 24, tzinfo=dt_timezone.utc),
            last_synced_updated_at=datetime(2026, 8, 15, 5, 27, 10, tzinfo=dt_timezone.utc),
        )

        resp = super_admin_client.get(SYNC_STATUS_URL)

        assert resp.status_code == 200
        data = resp.json()
        # MIN, not MAX — the earlier (etoile) store's last_run_at must win.
        assert data["last_run_at"] == "2026-08-15T10:30:24Z"
        stores_by_type = {s["store_type"]: s for s in data["stores"]}
        assert set(stores_by_type) == {"gimssine", "etoile"}
        assert stores_by_type["gimssine"]["last_run_at"] == "2026-08-15T10:30:27Z"
        assert stores_by_type["gimssine"]["last_synced_updated_at"] == "2026-08-15T07:46:17Z"
        assert stores_by_type["etoile"]["last_run_at"] == "2026-08-15T10:30:24Z"

    def test_top_level_null_when_any_store_last_run_at_is_null(self, super_admin_client):
        StoreSyncWatermark.objects.create(
            store_type="gimssine",
            last_run_at=datetime(2026, 8, 15, 10, 30, 27, tzinfo=dt_timezone.utc),
            last_synced_updated_at=datetime(2026, 8, 15, 7, 46, 17, tzinfo=dt_timezone.utc),
        )
        StoreSyncWatermark.objects.create(
            store_type="etoile",
            last_run_at=None,
            last_synced_updated_at=None,
        )

        resp = super_admin_client.get(SYNC_STATUS_URL)

        assert resp.status_code == 200
        data = resp.json()
        assert data["last_run_at"] is None
        stores_by_type = {s["store_type"]: s for s in data["stores"]}
        assert stores_by_type["etoile"]["last_run_at"] is None

    def test_top_level_null_and_store_present_when_watermark_row_missing(self, super_admin_client):
        """Only gimssine has ever synced (etoile has no watermark row at all).
        Every canonical store must still appear in `stores`, and the missing
        row must be treated the same as a null last_run_at for the top level
        value (unknown beats falsely fresh)."""
        StoreSyncWatermark.objects.create(
            store_type="gimssine",
            last_run_at=datetime(2026, 8, 15, 10, 30, 27, tzinfo=dt_timezone.utc),
            last_synced_updated_at=datetime(2026, 8, 15, 7, 46, 17, tzinfo=dt_timezone.utc),
        )
        assert StoreSyncWatermark.objects.filter(store_type="etoile").exists() is False

        resp = super_admin_client.get(SYNC_STATUS_URL)

        assert resp.status_code == 200
        data = resp.json()
        assert data["last_run_at"] is None
        stores_by_type = {s["store_type"]: s for s in data["stores"]}
        assert set(stores_by_type) == {"gimssine", "etoile"}
        assert stores_by_type["etoile"]["last_run_at"] is None
        assert stores_by_type["etoile"]["last_synced_updated_at"] is None

    def test_no_watermark_rows_at_all(self, super_admin_client):
        resp = super_admin_client.get(SYNC_STATUS_URL)

        assert resp.status_code == 200
        data = resp.json()
        assert data["last_run_at"] is None
        stores_by_type = {s["store_type"]: s for s in data["stores"]}
        assert set(stores_by_type) == {"gimssine", "etoile"}
        assert all(s["last_run_at"] is None for s in data["stores"])
