"""Tests for the backfill_missing_orders management command.

Recovery path for orders permanently skipped by the pre-fix sync_store()
watermark bug. Diffs Shopify's open orders (created since a given date)
against the local Order table in one query and creates only what is
missing — it must never touch an order that already exists.
"""

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from order.models import Order

_GET_HEADERS_TARGET = "order.management.commands.backfill_missing_orders._get_with_headers"
_FULFILLMENT_TARGET = (
    "order.management.commands.backfill_missing_orders._build_fulfillment_location_data"
)


def _make_shopify_order(shopify_id: int, note: str | None = None) -> dict:
    return {
        "id": shopify_id,
        "order_number": shopify_id,
        "name": f"#{shopify_id}",
        "financial_status": "paid",
        "fulfillment_status": None,
        "total_price": "100.00",
        "subtotal_price": "90.00",
        "total_tax": "10.00",
        "total_discounts": "0.00",
        "total_shipping_price_set": None,
        "currency": "USD",
        "gateway": "manual",
        "note": note,
        "tags": "",
        "cancel_reason": None,
        "source_name": "web",
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-02T00:00:00Z",
        "closed_at": None,
        "cancelled_at": None,
        "processed_at": None,
        "customer": None,
        "shipping_address": None,
        "line_items": [],
        "shipping_lines": [],
        "refunds": [],
        "email": None,
        "phone": None,
    }


# ---------------------------------------------------------------------------
# 6. The command creates only the missing orders and leaves existing ones
#    untouched.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_backfill_creates_only_missing_orders_leaves_existing_untouched():
    Order.objects.create(
        shopify_order_id=1,
        store_type="gimssine",
        order_number=1,
        name="#1",
        note="manually edited note — must survive",
        shopify_created_at=timezone.now(),
    )

    shopify_orders = [
        _make_shopify_order(1, note="Shopify's current note for #1"),
        _make_shopify_order(2, note="Shopify note for #2"),
    ]

    with (
        patch(_GET_HEADERS_TARGET, return_value=({"orders": shopify_orders}, {})),
        patch(_FULFILLMENT_TARGET, return_value=("", {})),
    ):
        call_command("backfill_missing_orders", "--store", "gimssine")

    # Existing order #1 is untouched — its note was NOT overwritten from
    # Shopify's (differing) note value.
    order1 = Order.objects.get(shopify_order_id=1, store_type="gimssine")
    assert order1.note == "manually edited note — must survive"

    # Missing order #2 was created.
    assert Order.objects.filter(shopify_order_id=2, store_type="gimssine").exists()
    assert Order.objects.filter(store_type="gimssine").count() == 2


# ---------------------------------------------------------------------------
# 7. --dry-run writes nothing.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_backfill_dry_run_writes_nothing():
    shopify_orders = [_make_shopify_order(3, note="Shopify note for #3")]

    with (
        patch(_GET_HEADERS_TARGET, return_value=({"orders": shopify_orders}, {})),
        patch(_FULFILLMENT_TARGET, return_value=("", {})),
    ):
        call_command("backfill_missing_orders", "--store", "gimssine", "--dry-run")

    assert Order.objects.filter(shopify_order_id=3, store_type="gimssine").exists() is False
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_backfill_does_not_advance_watermark():
    """The repair path must never advance StoreSyncWatermark — that is
    precisely the bug it exists to recover from."""
    from order.models import StoreSyncWatermark

    shopify_orders = [_make_shopify_order(4, note="Shopify note for #4")]

    with (
        patch(_GET_HEADERS_TARGET, return_value=({"orders": shopify_orders}, {})),
        patch(_FULFILLMENT_TARGET, return_value=("", {})),
    ):
        call_command("backfill_missing_orders", "--store", "gimssine")

    assert Order.objects.filter(shopify_order_id=4, store_type="gimssine").exists()
    assert StoreSyncWatermark.objects.filter(store_type="gimssine").exists() is False
