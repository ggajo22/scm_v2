"""SPEC-ORDER-029 (v0.5.0) — backfill_order_cancellations management command
tests. Covers AC-CANC-019~023 (5 cases).

Patch targets follow acceptance.md §0.2:
- group 1 (write-result assertions): order.shopify_orders._get_with_headers
- group 4 (call-argument capture):
  order.management.commands.backfill_order_cancellations.open_candidate_order_ids
"""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils.dateparse import parse_datetime

from order.models import LineItem, Order, PurchaseOrder, Refund, ShippingLine

_GET_HEADERS_TARGET = "order.shopify_orders._get_with_headers"
_OPEN_CANDIDATE_TARGET = (
    "order.management.commands.backfill_order_cancellations.open_candidate_order_ids"
)


# ---------------------------------------------------------------------------
# AC-CANC-019 — backfill command passes closed_grace_days=None (unbounded)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_019_backfill_passes_closed_grace_days_none():
    with patch(_OPEN_CANDIDATE_TARGET, return_value=[]) as mock_candidates:
        call_command("backfill_order_cancellations", "--store", "gimssine")

    mock_candidates.assert_called_once_with("gimssine", closed_grace_days=None)


# ---------------------------------------------------------------------------
# AC-CANC-020 — existing unreflected cancellation (52-case type) is reflected
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_020_existing_unreflected_cancellation_reflected():
    Order.objects.create(shopify_order_id=90020, store_type="gimssine")

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90020, "cancelled_at": "2026-07-01T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command("backfill_order_cancellations", "--store", "gimssine")

    order = Order.objects.get(shopify_order_id=90020)
    assert order.cancelled_at == parse_datetime("2026-07-01T00:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-021 — --dry-run writes nothing, but reports diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_021_dry_run_writes_nothing_but_reports():
    Order.objects.create(shopify_order_id=90021, store_type="gimssine")

    stdout = StringIO()
    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90021, "cancelled_at": "2026-07-02T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command(
            "backfill_order_cancellations", "--store", "gimssine", "--dry-run", stdout=stdout
        )

    order = Order.objects.get(shopify_order_id=90021)
    assert order.cancelled_at is None

    output = stdout.getvalue()
    assert "90021" in output
    assert "would_change" in output


# ---------------------------------------------------------------------------
# AC-CANC-022 — manual fields + LineItem/ShippingLine/Refund fully preserved
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_022_manual_fields_and_related_rows_preserved():
    order = Order.objects.create(
        shopify_order_id=90022,
        store_type="gimssine",
        status="shipped",
        note="고객 특별 요청 메모",
        ready_to_ship=True,
    )
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=70220,
        sku="ISBN-90022",
        quantity=1,
        logistics_status="shipment_confirmed",
        rack_number="A-7",
        received_quantity=2,
        purchase_status="in_stock",
        original_sku="9788901234567",
    )
    po = PurchaseOrder.objects.create(
        sku="ISBN-90022", title="Test", distributor="booxen", quantity=1, status="pending"
    )
    po.line_items.add(li)
    ShippingLine.objects.create(order=order, shopify_shipping_line_id=88022, title="Standard")
    Refund.objects.create(order=order, shopify_refund_id=99022, quantity=1)

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90022, "cancelled_at": "2026-08-11T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command("backfill_order_cancellations", "--store", "gimssine")

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
# AC-CANC-023 — re-running backfill twice does not create duplicate rows or raise
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_023_idempotent_rerun_no_duplicates():
    Order.objects.create(shopify_order_id=90023, store_type="gimssine")

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90023, "cancelled_at": "2026-07-03T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command("backfill_order_cancellations", "--store", "gimssine")

        order = Order.objects.get(shopify_order_id=90023)
        assert order.cancelled_at == parse_datetime("2026-07-03T00:00:00Z")

        call_command("backfill_order_cancellations", "--store", "gimssine")

    order.refresh_from_db()
    assert order.cancelled_at == parse_datetime("2026-07-03T00:00:00Z")
    assert Order.objects.filter(shopify_order_id=90023).count() == 1
