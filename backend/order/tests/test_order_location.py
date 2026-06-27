"""SPEC-ORDER-006: Order location tests

Tests for:
- _build_fulfillment_location_data helper
- _sync_single_order with location_code and line_item_location_map
- sync_store skips fulfillment API for existing orders (new optimization)
- sync_single_order_from_shopify passes location data
"""
from unittest.mock import patch

import pytest

from order.shopify_orders import _build_fulfillment_location_data, _sync_single_order


# ---------------------------------------------------------------------------
# _build_fulfillment_location_data tests
# ---------------------------------------------------------------------------


def test_build_fulfillment_location_returns_location_code_and_map():
    """Returns (order_location, line_item_map) from fulfillment_orders API."""
    mock_data = {
        "fulfillment_orders": [
            {
                "assigned_location": {"name": "GIMSSINE_NJ"},
                "line_items": [
                    {"line_item_id": 1001},
                    {"line_item_id": 1002},
                ],
            }
        ]
    }
    with patch("order.shopify_orders._get_with_headers", return_value=(mock_data, {})):
        loc, line_map = _build_fulfillment_location_data("shop.myshopify.com", "token", 99)

    assert loc == "NJ"
    assert line_map == {1001: "NJ", 1002: "NJ"}


def test_build_fulfillment_location_multiple_fulfillment_orders():
    """Multiple fulfillment orders produce joined location code."""
    mock_data = {
        "fulfillment_orders": [
            {
                "assigned_location": {"name": "GIMSSINE_NJ"},
                "line_items": [{"line_item_id": 1001}],
            },
            {
                "assigned_location": {"name": "GIMSSINE_CA"},
                "line_items": [{"line_item_id": 1002}],
            },
        ]
    }
    with patch("order.shopify_orders._get_with_headers", return_value=(mock_data, {})):
        loc, line_map = _build_fulfillment_location_data("shop.myshopify.com", "token", 99)

    assert loc == "NJ/CA"
    assert line_map == {1001: "NJ", 1002: "CA"}


def test_build_fulfillment_location_handles_names_without_underscore():
    """Location names without underscore produce empty string code."""
    mock_data = {
        "fulfillment_orders": [
            {
                "assigned_location": {"name": "GIMSSINE"},
                "line_items": [{"line_item_id": 1001}],
            }
        ]
    }
    with patch("order.shopify_orders._get_with_headers", return_value=(mock_data, {})):
        loc, line_map = _build_fulfillment_location_data("shop.myshopify.com", "token", 99)

    assert loc == ""
    assert line_map == {1001: ""}


def test_build_fulfillment_location_returns_empty_on_error():
    """Any exception from the API returns ("", {})."""
    with patch(
        "order.shopify_orders._get_with_headers",
        side_effect=Exception("connection error"),
    ):
        loc, line_map = _build_fulfillment_location_data("shop.myshopify.com", "token", 99)

    assert loc == ""
    assert line_map == {}


def test_build_fulfillment_location_etoile_store():
    """Etoile store fulfillment orders are correctly parsed."""
    mock_data = {
        "fulfillment_orders": [
            {
                "assigned_location": {"name": "ETOILE_CA"},
                "line_items": [{"line_item_id": 2001}],
            }
        ]
    }
    with patch("order.shopify_orders._get_with_headers", return_value=(mock_data, {})):
        loc, line_map = _build_fulfillment_location_data("etoile.myshopify.com", "token456", 55)

    assert loc == "CA"
    assert line_map == {2001: "CA"}


# ---------------------------------------------------------------------------
# _sync_single_order with location_code and line_item_location_map
# ---------------------------------------------------------------------------


def _make_order_data(shopify_id: int = 12345, line_item_ids: list | None = None) -> dict:
    line_items = []
    for lid in (line_item_ids or []):
        line_items.append({"id": lid, "price": "50.00", "quantity": 1, "title": "Test Item"})
    return {
        "id": shopify_id,
        "order_number": 1001,
        "name": "#1001",
        "financial_status": "paid",
        "fulfillment_status": None,
        "total_price": "100.00",
        "subtotal_price": "90.00",
        "total_tax": "10.00",
        "total_discounts": "0.00",
        "total_shipping_price_set": None,
        "currency": "CAD",
        "gateway": "stripe",
        "note": None,
        "tags": "",
        "cancel_reason": None,
        "source_name": "web",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "closed_at": None,
        "cancelled_at": None,
        "processed_at": None,
        "customer": None,
        "shipping_address": None,
        "billing_address": None,
        "line_items": line_items,
        "shipping_lines": [],
        "refunds": [],
    }


@pytest.mark.django_db
def test_sync_sets_order_location_from_location_code():
    """location_code is stored on the Order."""
    from order.models import Order

    _sync_single_order(_make_order_data(200001), "gimssine", location_code="NJ")

    order = Order.objects.get(shopify_order_id=200001, store_type="gimssine")
    assert order.location == "NJ"


@pytest.mark.django_db
def test_sync_sets_empty_location_when_no_location_code():
    """Without location_code, Order.location is empty string."""
    from order.models import Order

    _sync_single_order(_make_order_data(200002), "gimssine")

    order = Order.objects.get(shopify_order_id=200002, store_type="gimssine")
    assert order.location == ""


@pytest.mark.django_db
def test_sync_sets_line_item_location_from_map():
    """line_item_location_map sets location on each LineItem."""
    from order.models import LineItem

    _sync_single_order(
        _make_order_data(200003, line_item_ids=[5001]),
        "gimssine",
        location_code="NJ",
        line_item_location_map={5001: "NJ"},
    )

    li = LineItem.objects.get(shopify_line_item_id=5001)
    assert li.location == "NJ"


@pytest.mark.django_db
def test_sync_sets_empty_line_item_location_when_no_map():
    """Without line_item_location_map, LineItem.location is empty string."""
    from order.models import LineItem

    _sync_single_order(_make_order_data(200004, line_item_ids=[5002]), "gimssine")

    li = LineItem.objects.get(shopify_line_item_id=5002)
    assert li.location == ""


# ---------------------------------------------------------------------------
# sync_store: new optimization — skip fulfillment API for existing orders
# ---------------------------------------------------------------------------


def _make_shopify_order_payload(shopify_id: int) -> dict:
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
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
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


@pytest.mark.django_db
def test_sync_store_skips_fulfillment_api_for_existing_orders():
    """sync_store must NOT call _build_fulfillment_location_data for existing orders."""
    from django.utils import timezone
    from order.models import Order

    Order.objects.create(
        shopify_order_id=400001,
        store_type="gimssine",
        financial_status="paid",
        shopify_updated_at=timezone.now(),
        location="NJ",
    )

    with (
        patch("order.shopify_orders.fetch_all_open_orders", return_value=[_make_shopify_order_payload(400001)]),
        patch("order.shopify_orders._build_fulfillment_location_data") as mock_build,
    ):
        from order.shopify_orders import sync_store

        sync_store("gimssine")

    mock_build.assert_not_called()


@pytest.mark.django_db
def test_sync_store_calls_fulfillment_api_for_new_orders():
    """sync_store must call _build_fulfillment_location_data exactly once for each new order."""
    with (
        patch("order.shopify_orders.fetch_all_open_orders", return_value=[_make_shopify_order_payload(400002)]),
        patch("order.shopify_orders._build_fulfillment_location_data", return_value=("NJ", {})) as mock_build,
    ):
        from order.shopify_orders import sync_store

        sync_store("gimssine")

    assert mock_build.call_count == 1


@pytest.mark.django_db
def test_sync_single_order_from_shopify_passes_location_data():
    """sync_single_order_from_shopify fetches and passes fulfillment location."""
    fake_order = _make_shopify_order_payload(300001)

    with (
        patch("order.shopify_orders._get_with_headers", return_value=({"order": fake_order}, {})),
        patch("order.shopify_orders._build_fulfillment_location_data", return_value=("NJ", {5001: "NJ"})) as mock_build,
        patch("order.shopify_orders._sync_single_order") as mock_sync,
    ):
        from order.shopify_orders import sync_single_order_from_shopify

        sync_single_order_from_shopify(300001, "gimssine")

    assert mock_build.call_count == 1
    mock_sync.assert_called_once_with(
        fake_order, "gimssine", location_code="NJ", line_item_location_map={5001: "NJ"}
    )
