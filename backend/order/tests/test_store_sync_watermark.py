"""Tests for the StoreSyncWatermark-based sync_store() fetch cursor.

Regression coverage for the incident where sync_single_order_from_shopify
(single-order resync) bumped Order.shopify_updated_at on an OLD order past
what sync_store() had actually swept, jumping the store-wide MAX forward and
permanently skipping every order created in between. sync_store() now reads
its fetch watermark from StoreSyncWatermark instead of
MAX(Order.shopify_updated_at).
"""

from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.utils import timezone

from order.models import Order, StoreSyncWatermark
from order.shopify_orders import sync_single_order_from_shopify, sync_store


def _make_shopify_order_payload(shopify_id: int, updated_at: str) -> dict:
    return {
        "id": shopify_id,
        "order_number": 1001,
        "name": f"#{shopify_id}",
        "financial_status": "paid",
        "fulfillment_status": None,
        "total_price": "100.00",
        "subtotal_price": "90.00",
        "total_tax": "10.00",
        "total_discounts": "0.00",
        "total_shipping_price_set": None,
        "currency": "USD",
        "gateway": "stripe",
        "note": None,
        "tags": "",
        "cancel_reason": None,
        "source_name": "web",
        "created_at": "2026-08-01T00:00:00Z",
        "updated_at": updated_at,
        "closed_at": None,
        "cancelled_at": None,
        "processed_at": None,
        "customer": None,
        "shipping_address": None,
        "billing_address": None,
        "line_items": [],
        "shipping_lines": [],
        "refunds": [],
    }


# ---------------------------------------------------------------------------
# 1. Regression test for the incident: an old order carrying a far-newer
#    shopify_updated_at (from a single-order resync) must NOT advance the
#    fetch watermark. sync_store() must still request from the stored
#    watermark, not from MAX(Order.shopify_updated_at).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resynced_old_order_does_not_advance_fetch_watermark():
    StoreSyncWatermark.objects.create(
        store_type="gimssine",
        last_synced_updated_at=datetime(2026, 8, 13, 22, 11, 30, tzinfo=dt_timezone.utc),
    )
    # Simulates order #37413 after being individually resynced: its
    # shopify_updated_at (2026-08-15T02:24:08Z) is far newer than the stored
    # watermark, but it must be irrelevant to the next sync_store() fetch.
    Order.objects.create(
        shopify_order_id=37413,
        store_type="gimssine",
        order_number=37413,
        name="#37413",
        shopify_created_at=timezone.now(),
        shopify_updated_at=datetime(2026, 8, 15, 2, 24, 8, tzinfo=dt_timezone.utc),
    )

    with patch("order.shopify_orders.fetch_all_open_orders", return_value=[]) as mock_fetch:
        sync_store("gimssine")

    mock_fetch.assert_called_once()
    assert mock_fetch.call_args.kwargs["updated_at_min"] == "2026-08-13T22:11:30Z"


# ---------------------------------------------------------------------------
# 2. sync_store() advances the watermark to the max updated_at of the
#    returned batch (not to a global MAX over the Order table).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sync_store_advances_watermark_to_batch_max():
    StoreSyncWatermark.objects.create(
        store_type="gimssine",
        last_synced_updated_at=datetime(2026, 8, 1, 0, 0, 0, tzinfo=dt_timezone.utc),
    )
    orders = [
        _make_shopify_order_payload(500001, "2026-08-10T05:00:00Z"),
        # Offset form (Shopify's real format): 2026-08-12T09:30:00-07:00 ==
        # 2026-08-12T16:30:00Z, which is the later of the two.
        _make_shopify_order_payload(500002, "2026-08-12T09:30:00-07:00"),
    ]

    with (
        patch("order.shopify_orders.fetch_all_open_orders", return_value=orders),
        patch("order.shopify_orders._build_fulfillment_location_data", return_value=("", {})),
    ):
        sync_store("gimssine")

    watermark = StoreSyncWatermark.objects.get(store_type="gimssine")
    assert watermark.last_synced_updated_at == datetime(2026, 8, 12, 16, 30, 0, tzinfo=dt_timezone.utc)


# ---------------------------------------------------------------------------
# 3. The watermark never moves backwards.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sync_store_watermark_never_moves_backwards():
    StoreSyncWatermark.objects.create(
        store_type="gimssine",
        last_synced_updated_at=datetime(2026, 8, 14, 10, 0, 0, tzinfo=dt_timezone.utc),
    )
    # An order older than the current watermark (should not occur in
    # practice given the updated_at_min filter, but the code must not trust
    # that and must guard explicitly).
    orders = [_make_shopify_order_payload(500003, "2026-08-10T00:00:00Z")]

    with (
        patch("order.shopify_orders.fetch_all_open_orders", return_value=orders),
        patch("order.shopify_orders._build_fulfillment_location_data", return_value=("", {})),
    ):
        sync_store("gimssine")

    watermark = StoreSyncWatermark.objects.get(store_type="gimssine")
    assert watermark.last_synced_updated_at == datetime(2026, 8, 14, 10, 0, 0, tzinfo=dt_timezone.utc)


# ---------------------------------------------------------------------------
# 4. A single-order resync leaves the watermark row unchanged.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_single_order_resync_does_not_touch_watermark():
    watermark = StoreSyncWatermark.objects.create(
        store_type="gimssine",
        last_synced_updated_at=datetime(2026, 8, 13, 22, 11, 30, tzinfo=dt_timezone.utc),
    )
    order_data = _make_shopify_order_payload(37413, "2026-08-15T02:24:08Z")

    with (
        patch("order.shopify_orders._get_with_headers", return_value=({"order": order_data}, {})),
        patch("order.shopify_orders._build_fulfillment_location_data", return_value=("", {})),
    ):
        sync_single_order_from_shopify(37413, "gimssine")

    watermark.refresh_from_db()
    assert watermark.last_synced_updated_at == datetime(2026, 8, 13, 22, 11, 30, tzinfo=dt_timezone.utc)
    assert StoreSyncWatermark.objects.filter(store_type="gimssine").count() == 1


@pytest.mark.django_db
def test_single_order_resync_does_not_create_watermark_row():
    """No StoreSyncWatermark row exists yet — a single-order resync must not
    create one either. Only sync_store() manages this table."""
    order_data = _make_shopify_order_payload(37414, "2026-08-15T02:24:08Z")

    with (
        patch("order.shopify_orders._get_with_headers", return_value=({"order": order_data}, {})),
        patch("order.shopify_orders._build_fulfillment_location_data", return_value=("", {})),
    ):
        sync_single_order_from_shopify(37414, "gimssine")

    assert StoreSyncWatermark.objects.filter(store_type="gimssine").count() == 0


# ---------------------------------------------------------------------------
# 5. First run with a NULL watermark seeds from the existing Order MAX.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 6. last_run_at (SPEC-PURCHASE-ORDER-011): staleness-detection cursor,
#    deliberately distinct from last_synced_updated_at / updated_at. Must
#    advance on EVERY successful sync_store() run, including a quiet run
#    (zero orders fetched) and a run whose watermark does not advance.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_quiet_run_with_zero_orders_still_updates_last_run_at():
    """Regression guard for the updated_at trap: a quiet cycle (no new
    Shopify activity) must still record that the sync actually ran, or the
    staleness indicator this field exists for becomes useless."""
    watermark = StoreSyncWatermark.objects.create(
        store_type="gimssine",
        last_synced_updated_at=datetime(2026, 8, 13, 22, 11, 30, tzinfo=dt_timezone.utc),
    )
    assert watermark.last_run_at is None

    before = timezone.now()
    with patch("order.shopify_orders.fetch_all_open_orders", return_value=[]):
        sync_store("gimssine")
    after = timezone.now()

    watermark.refresh_from_db()
    assert watermark.last_run_at is not None
    assert before <= watermark.last_run_at <= after
    # The fetch cursor itself must remain untouched on a quiet run.
    assert watermark.last_synced_updated_at == datetime(2026, 8, 13, 22, 11, 30, tzinfo=dt_timezone.utc)


@pytest.mark.django_db
def test_non_advancing_watermark_run_still_updates_last_run_at():
    """batch_max equal to the stored watermark (no advance) must still
    update last_run_at — the update_fields list on that save path must not
    silently omit it."""
    watermark = StoreSyncWatermark.objects.create(
        store_type="gimssine",
        last_synced_updated_at=datetime(2026, 8, 14, 10, 0, 0, tzinfo=dt_timezone.utc),
    )
    orders = [_make_shopify_order_payload(500004, "2026-08-14T10:00:00Z")]

    before = timezone.now()
    with (
        patch("order.shopify_orders.fetch_all_open_orders", return_value=orders),
        patch("order.shopify_orders._build_fulfillment_location_data", return_value=("", {})),
    ):
        sync_store("gimssine")
    after = timezone.now()

    watermark.refresh_from_db()
    assert watermark.last_run_at is not None
    assert before <= watermark.last_run_at <= after
    # Watermark itself must not have moved (batch_max == last_updated).
    assert watermark.last_synced_updated_at == datetime(2026, 8, 14, 10, 0, 0, tzinfo=dt_timezone.utc)


@pytest.mark.django_db
def test_raising_run_leaves_last_run_at_unchanged():
    """A run that raises must not appear fresh. sync_store() itself does not
    catch exceptions, but the real caller (OrderSyncView) wraps the call in
    transaction.atomic() so any partial writes roll back; this test exercises
    that same contract directly."""
    from django.db import transaction

    watermark = StoreSyncWatermark.objects.create(
        store_type="gimssine",
        last_synced_updated_at=datetime(2026, 8, 13, 22, 11, 30, tzinfo=dt_timezone.utc),
    )
    assert watermark.last_run_at is None

    with patch("order.shopify_orders.fetch_all_open_orders", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            with transaction.atomic():
                sync_store("gimssine")

    watermark.refresh_from_db()
    assert watermark.last_run_at is None
    assert watermark.last_synced_updated_at == datetime(2026, 8, 13, 22, 11, 30, tzinfo=dt_timezone.utc)


@pytest.mark.django_db
def test_sync_store_seeds_null_watermark_from_order_max():
    Order.objects.create(
        shopify_order_id=600001,
        store_type="gimssine",
        order_number=600001,
        name="#600001",
        shopify_created_at=timezone.now(),
        shopify_updated_at=datetime(2026, 7, 1, 0, 0, 0, tzinfo=dt_timezone.utc),
    )
    Order.objects.create(
        shopify_order_id=600002,
        store_type="gimssine",
        order_number=600002,
        name="#600002",
        shopify_created_at=timezone.now(),
        shopify_updated_at=datetime(2026, 7, 15, 0, 0, 0, tzinfo=dt_timezone.utc),
    )
    assert StoreSyncWatermark.objects.filter(store_type="gimssine").exists() is False

    with patch("order.shopify_orders.fetch_all_open_orders", return_value=[]) as mock_fetch:
        result = sync_store("gimssine")

    mock_fetch.assert_called_once()
    assert mock_fetch.call_args.kwargs["updated_at_min"] == "2026-07-15T00:00:00Z"
    assert result["updated_at_min"] == "2026-07-15T00:00:00Z"
    watermark = StoreSyncWatermark.objects.get(store_type="gimssine")
    assert watermark.last_synced_updated_at == datetime(2026, 7, 15, 0, 0, 0, tzinfo=dt_timezone.utc)
