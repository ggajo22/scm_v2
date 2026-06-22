"""SPEC-ORDER-006: Order location tests — RED phase

Tests for:
- _fetch_locations helper
- _sync_single_order with location_map
- sync_store and sync_single_order_from_shopify pass location_map
"""
from unittest.mock import MagicMock, patch

import pytest

from order.shopify_orders import _fetch_locations, _sync_single_order


# ---------------------------------------------------------------------------
# _fetch_locations tests
# ---------------------------------------------------------------------------


def test_fetch_locations_returns_code_dict():
    """Fetch locations API and return {location_id: code} where code is name suffix after '_'."""
    mock_data = {
        "locations": [
            {"id": 85951578417, "name": "GIMSSINE_CA"},
            {"id": 111320793393, "name": "GIMSSINE_KR"},
            {"id": 101550260529, "name": "GIMSSINE_NJ"},
        ]
    }
    with patch("order.shopify_orders._get_with_headers", return_value=(mock_data, {})):
        result = _fetch_locations("example.myshopify.com", "token123")

    assert result == {
        85951578417: "CA",
        111320793393: "KR",
        101550260529: "NJ",
    }


def test_fetch_locations_handles_names_without_underscore():
    """Location names without underscore should produce empty string code."""
    mock_data = {
        "locations": [
            {"id": 111, "name": "GIMSSINE"},
        ]
    }
    with patch("order.shopify_orders._get_with_headers", return_value=(mock_data, {})):
        result = _fetch_locations("example.myshopify.com", "token123")

    assert result == {111: ""}


def test_fetch_locations_returns_empty_dict_on_error():
    """Any exception from the API should return empty dict (graceful degradation)."""
    with patch(
        "order.shopify_orders._get_with_headers",
        side_effect=Exception("connection error"),
    ):
        result = _fetch_locations("example.myshopify.com", "token123")

    assert result == {}


def test_fetch_locations_etoile_locations():
    """Etoile store locations are correctly parsed."""
    mock_data = {
        "locations": [
            {"id": 76370411705, "name": "ETOILE_CA"},
            {"id": 79188459705, "name": "ETOILE_NJ"},
        ]
    }
    with patch("order.shopify_orders._get_with_headers", return_value=(mock_data, {})):
        result = _fetch_locations("etoile.myshopify.com", "token456")

    assert result == {
        76370411705: "CA",
        79188459705: "NJ",
    }


def test_fetch_locations_calls_locations_json_endpoint():
    """_fetch_locations must call the locations.json Shopify endpoint."""
    mock_data = {"locations": []}
    with patch("order.shopify_orders._get_with_headers", return_value=(mock_data, {})) as mock_get:
        _fetch_locations("shop.myshopify.com", "mytoken")

    mock_get.assert_called_once_with("shop.myshopify.com", "mytoken", "locations.json")


# ---------------------------------------------------------------------------
# _sync_single_order with location_map tests
# ---------------------------------------------------------------------------


def _make_order_data(shopify_id: int = 12345, location_id=85951578417) -> dict:
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
        "line_items": [],
        "shipping_lines": [],
        "refunds": [],
        "location_id": location_id,
    }


@pytest.mark.django_db
def test_sync_sets_location_from_location_map():
    """When location_map is provided and order has location_id, Order.location is set."""
    from order.models import Order

    order_data = _make_order_data(shopify_id=200001, location_id=85951578417)
    location_map = {85951578417: "CA", 111320793393: "KR"}

    _sync_single_order(order_data, "gimssine", location_map=location_map)

    order = Order.objects.get(shopify_order_id=200001, store_type="gimssine")
    assert order.location == "CA"


@pytest.mark.django_db
def test_sync_sets_empty_location_when_location_id_null():
    """When order has location_id=null, Order.location should be empty string."""
    from order.models import Order

    order_data = _make_order_data(shopify_id=200002, location_id=None)
    location_map = {85951578417: "CA"}

    _sync_single_order(order_data, "gimssine", location_map=location_map)

    order = Order.objects.get(shopify_order_id=200002, store_type="gimssine")
    assert order.location == ""


@pytest.mark.django_db
def test_sync_sets_empty_location_when_no_location_map():
    """When location_map is None (backward compat), Order.location should be empty string."""
    from order.models import Order

    order_data = _make_order_data(shopify_id=200003, location_id=85951578417)

    _sync_single_order(order_data, "gimssine", location_map=None)

    order = Order.objects.get(shopify_order_id=200003, store_type="gimssine")
    assert order.location == ""


@pytest.mark.django_db
def test_sync_sets_empty_location_when_location_id_not_in_map():
    """When location_id is not in location_map, Order.location should be empty string."""
    from order.models import Order

    order_data = _make_order_data(shopify_id=200004, location_id=99999999)
    location_map = {85951578417: "CA"}

    _sync_single_order(order_data, "gimssine", location_map=location_map)

    order = Order.objects.get(shopify_order_id=200004, store_type="gimssine")
    assert order.location == ""


# ---------------------------------------------------------------------------
# sync_store passes location_map — integration-style mock tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sync_store_fetches_and_passes_location_map():
    """sync_store must call _fetch_locations exactly once (uses real settings domain/token)."""
    with (
        patch("order.shopify_orders.fetch_all_open_orders", return_value=[]),
        patch("order.shopify_orders._fetch_locations", return_value={85951578417: "CA"}) as mock_loc,
    ):
        from order.shopify_orders import sync_store

        sync_store("gimssine")

        # Verify _fetch_locations is called once — exact args come from settings (real values)
        assert mock_loc.call_count == 1


@pytest.mark.django_db
def test_sync_single_order_from_shopify_fetches_and_passes_location_map():
    """sync_single_order_from_shopify must call _fetch_locations and pass result to _sync_single_order."""
    fake_order = _make_order_data(shopify_id=300001, location_id=85951578417)
    location_map = {85951578417: "CA"}

    with (
        patch(
            "order.shopify_orders._get_with_headers",
            return_value=({"order": fake_order}, {}),
        ),
        patch(
            "order.shopify_orders._fetch_locations",
            return_value=location_map,
        ) as mock_loc,
        patch("order.shopify_orders._sync_single_order") as mock_sync,
    ):
        from order.shopify_orders import sync_single_order_from_shopify

        sync_single_order_from_shopify(300001, "gimssine")

        # _fetch_locations must be called exactly once
        assert mock_loc.call_count == 1
        # _sync_single_order must receive the location_map from _fetch_locations
        mock_sync.assert_called_once_with(fake_order, "gimssine", location_map=location_map)
