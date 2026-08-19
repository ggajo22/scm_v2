"""SPEC-ORDER-029 (v0.5.0) — sync_order_cancellations management command tests.

Covers AC-CANC-013~018 and AC-CANC-025 (7 cases; AC-CANC-017/025 each split
into 2 scenarios). Patch targets follow acceptance.md §0.2:

- group 1 (write-result assertions): order.shopify_orders._get_with_headers
- group 2 (store-level failure injection):
  order.management.commands.sync_order_cancellations.open_candidate_order_ids
  with a store-keyed side_effect
- group 3 (chunk-level failure injection): order.shopify_orders.fetch_order_status_by_ids
- group 4 (call-argument capture):
  order.management.commands.sync_order_cancellations.open_candidate_order_ids
"""

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.utils import OperationalError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from order.models import LineItem, Order, PurchaseOrder, Refund, ShippingLine, StoreSyncWatermark
from order.shopify_orders import open_candidate_order_ids, reconcile_order_status_for_ids

DOMAIN = "shop.myshopify.com"
TOKEN = "token123"

_GET_HEADERS_TARGET = "order.shopify_orders._get_with_headers"
_FETCH_BY_IDS_TARGET = "order.shopify_orders.fetch_order_status_by_ids"
_OPEN_CANDIDATE_TARGET = "order.management.commands.sync_order_cancellations.open_candidate_order_ids"


# ---------------------------------------------------------------------------
# AC-CANC-013 — StoreSyncWatermark untouched + actual reflection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_013_watermark_untouched_order_reflected():
    t_old = timezone.now() - timezone.timedelta(days=1)
    t_old2 = timezone.now() - timezone.timedelta(hours=1)
    StoreSyncWatermark.objects.create(
        store_type="gimssine", last_synced_updated_at=t_old, last_run_at=t_old2
    )
    Order.objects.create(shopify_order_id=90013, store_type="gimssine")

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90013, "cancelled_at": "2026-08-11T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command("sync_order_cancellations", "--store", "gimssine")

    watermark = StoreSyncWatermark.objects.get(store_type="gimssine")
    assert watermark.last_synced_updated_at == t_old
    assert watermark.last_run_at == t_old2

    order = Order.objects.get(shopify_order_id=90013)
    assert order.cancelled_at == parse_datetime("2026-08-11T00:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-014 — detection command passes closed_grace_days=30
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_014_detection_passes_closed_grace_days_30():
    with patch(_OPEN_CANDIDATE_TARGET, return_value=[]) as mock_candidates:
        call_command("sync_order_cancellations", "--store", "gimssine")

    mock_candidates.assert_called_once_with("gimssine", closed_grace_days=30)


# ---------------------------------------------------------------------------
# AC-CANC-015 — one store's failure does not block the other
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_015_one_store_failure_does_not_block_other():
    Order.objects.create(shopify_order_id=90015, store_type="etoile")

    def side_effect(store_type, closed_grace_days=None):
        if store_type == "gimssine":
            raise RuntimeError("shopify 500")
        return open_candidate_order_ids(store_type, closed_grace_days=closed_grace_days)

    with (
        patch(_OPEN_CANDIDATE_TARGET, side_effect=side_effect),
        patch(
            _GET_HEADERS_TARGET,
            return_value=(
                {"orders": [{"id": 90015, "cancelled_at": None, "closed_at": "2026-08-09T00:00:00Z"}]},
                {},
            ),
        ),
    ):
        with pytest.raises(CommandError):
            call_command("sync_order_cancellations")

    order = Order.objects.get(shopify_order_id=90015)
    assert order.closed_at == parse_datetime("2026-08-09T00:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-016 — one chunk's failure does not block the rest, failed ids recorded
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_016_chunk_failure_isolated_ids_recorded():
    Order.objects.create(shopify_order_id=900161, store_type="gimssine")
    Order.objects.create(shopify_order_id=900162, store_type="gimssine")

    def side_effect(domain, token, shopify_order_ids):
        ids = list(shopify_order_ids)
        if ids == [900161]:
            raise RuntimeError("boom")
        if ids == [900162]:
            return [{"id": 900162, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]
        raise AssertionError(f"unexpected chunk: {ids}")

    with patch(_FETCH_BY_IDS_TARGET, side_effect=side_effect):
        result = reconcile_order_status_for_ids(
            "gimssine", DOMAIN, TOKEN, [900161, 900162], chunk_size=1
        )

    assert Order.objects.get(shopify_order_id=900162).cancelled_at == parse_datetime("2026-08-01T00:00:00Z")
    assert len(result["chunk_failures"]) == 1
    assert result["chunk_failures"][0]["ids"] == [900161]


# ---------------------------------------------------------------------------
# AC-CANC-017 — non-zero exit code for both store-level and chunk-level failures
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_017_scenario1_store_level_failure_raises():
    def side_effect(store_type, closed_grace_days=None):
        if store_type == "gimssine":
            raise RuntimeError("shopify 500")
        return []

    with patch(_OPEN_CANDIDATE_TARGET, side_effect=side_effect):
        with pytest.raises(CommandError, match="gimssine"):
            call_command("sync_order_cancellations")


@pytest.mark.django_db
def test_ac_cancc_017_scenario2_chunk_level_failure_raises_partial():
    Order.objects.create(shopify_order_id=900171, store_type="gimssine")
    Order.objects.create(shopify_order_id=900172, store_type="etoile")

    def side_effect(domain, token, shopify_order_ids):
        ids = list(shopify_order_ids)
        if ids == [900171]:
            raise RuntimeError("boom")
        if ids == [900172]:
            return [{"id": 900172, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]
        raise AssertionError(f"unexpected chunk: {ids}")

    with patch(_FETCH_BY_IDS_TARGET, side_effect=side_effect):
        with pytest.raises(CommandError, match="partial"):
            call_command("sync_order_cancellations")

    assert Order.objects.get(shopify_order_id=900172).cancelled_at == parse_datetime("2026-08-01T00:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-018 — manual fields + LineItem/ShippingLine/Refund fully preserved
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_018_manual_fields_and_related_rows_preserved():
    order = Order.objects.create(
        shopify_order_id=90018,
        store_type="gimssine",
        status="shipped",
        note="고객 특별 요청 메모",
        ready_to_ship=True,
    )
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=70180,
        sku="ISBN-90018",
        quantity=1,
        logistics_status="shipment_confirmed",
        rack_number="A-7",
        received_quantity=2,
        purchase_status="in_stock",
        original_sku="9788901234567",
    )
    po = PurchaseOrder.objects.create(
        sku="ISBN-90018", title="Test", distributor="booxen", quantity=1, status="pending"
    )
    po.line_items.add(li)
    ShippingLine.objects.create(order=order, shopify_shipping_line_id=88018, title="Standard")
    Refund.objects.create(order=order, shopify_refund_id=99018, quantity=1)

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90018, "cancelled_at": "2026-08-11T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command("sync_order_cancellations", "--store", "gimssine")

    order.refresh_from_db()
    li.refresh_from_db()
    assert order.cancelled_at == parse_datetime("2026-08-11T00:00:00Z")
    assert order.status == "shipped"
    assert order.note == "고객 특별 요청 메모"
    assert order.ready_to_ship is True

    assert li.logistics_status == "shipment_confirmed"
    assert li.rack_number == "A-7"
    assert li.received_quantity == 2
    assert li.purchase_status == "in_stock"
    assert li.original_sku == "9788901234567"
    assert list(li.purchase_orders.all()) == [po]

    assert ShippingLine.objects.filter(order=order).count() == 1
    assert Refund.objects.filter(order=order).count() == 1


# ---------------------------------------------------------------------------
# AC-CANC-025 — lock-wait-timeout failures are soft (no CommandError) when
# ALL of a store's failures are lock timeouts; a mix is still hard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_025_scenario1_all_lock_timeout_is_soft_failure():
    from io import StringIO

    Order.objects.create(shopify_order_id=900251, store_type="gimssine")
    Order.objects.create(shopify_order_id=900252, store_type="etoile")

    def side_effect(domain, token, shopify_order_ids):
        ids = list(shopify_order_ids)
        if ids == [900251]:
            raise OperationalError("(1205, 'Lock wait timeout exceeded; try restarting transaction')")
        if ids == [900252]:
            return [{"id": 900252, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]
        raise AssertionError(f"unexpected chunk: {ids}")

    stderr = StringIO()
    with patch(_FETCH_BY_IDS_TARGET, side_effect=side_effect):
        call_command("sync_order_cancellations", stderr=stderr)

    assert Order.objects.get(shopify_order_id=900252).cancelled_at == parse_datetime("2026-08-01T00:00:00Z")
    output = stderr.getvalue()
    assert "gimssine" in output
    assert "900251" in output


@pytest.mark.django_db
def test_ac_cancc_025_scenario2_mixed_failure_is_still_hard():
    Order.objects.create(shopify_order_id=900253, store_type="gimssine")
    Order.objects.create(shopify_order_id=900254, store_type="etoile")

    def side_effect(domain, token, shopify_order_ids):
        ids = list(shopify_order_ids)
        if ids == [900253]:
            raise ValueError("malformed response")
        if ids == [900254]:
            return [{"id": 900254, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]
        raise AssertionError(f"unexpected chunk: {ids}")

    with patch(_FETCH_BY_IDS_TARGET, side_effect=side_effect):
        with pytest.raises(CommandError, match="gimssine"):
            call_command("sync_order_cancellations")
