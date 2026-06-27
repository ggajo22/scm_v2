from unittest.mock import patch

import pytest
from django.utils import timezone

from order.shopify_orders import (
    _decimal_or_none,
    _parse_next_page_info,
    _sync_single_order,
    fetch_all_open_orders,
)
from order.models import LineItem, Order, PurchaseOrder


def _make_order_data(shopify_id, line_items=None):
    return {
        "id": shopify_id,
        "order_number": 33529,
        "name": "#33529",
        "financial_status": "paid",
        "fulfillment_status": None,
        "total_price": "10000.00",
        "subtotal_price": "10000.00",
        "total_tax": "0.00",
        "total_discounts": "0.00",
        "total_shipping_price_set": None,
        "currency": "KRW",
        "gateway": "manual",
        "note": None,
        "tags": "",
        "cancel_reason": None,
        "source_name": "web",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T01:00:00Z",
        "closed_at": None,
        "cancelled_at": None,
        "processed_at": "2026-01-01T00:00:00Z",
        "customer": None,
        "shipping_address": None,
        "line_items": line_items or [],
        "shipping_lines": [],
        "refunds": [],
        "email": None,
        "phone": None,
    }


def _make_shopify_line_item(li_id, sku="ISBN001"):
    return {
        "id": li_id,
        "product_id": 1,
        "variant_id": 1,
        "title": "Test Book",
        "variant_title": None,
        "sku": sku,
        "quantity": 2,
        "price": "5000.00",
        "total_discount": "0.00",
        "fulfillment_status": None,
        "vendor": "Test Publisher",
        "grams": 0,
    }


@pytest.mark.django_db
def test_sync_preserves_purchase_status_on_resync():
    """Resyncing an order must not reset purchase_status back to 'unordered'."""
    order = Order.objects.create(
        shopify_order_id=900001,
        store_type="gimssine",
        order_number=33529,
        name="#33529",
        shopify_created_at=timezone.now(),
    )
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=7001,
        sku="ISBN001",
        quantity=2,
        purchase_status="on_hold",
    )

    order_data = _make_order_data(900001, [_make_shopify_line_item(7001)])
    _sync_single_order(order_data, "gimssine")

    li.refresh_from_db()
    assert li.purchase_status == "on_hold"


@pytest.mark.django_db
def test_sync_new_line_item_defaults_to_unordered():
    """Newly added line items (not in DB yet) must default to 'unordered'."""
    order = Order.objects.create(
        shopify_order_id=900002,
        store_type="gimssine",
        order_number=33530,
        name="#33530",
        shopify_created_at=timezone.now(),
    )

    order_data = _make_order_data(900002, [_make_shopify_line_item(7002, sku="ISBN002")])
    _sync_single_order(order_data, "gimssine")

    li = LineItem.objects.get(order=order, shopify_line_item_id=7002)
    assert li.purchase_status == "unordered"


@pytest.mark.django_db
def test_sync_removes_orphaned_line_item_without_po():
    """Line items that disappear from Shopify and have no PO should be deleted."""
    order = Order.objects.create(
        shopify_order_id=900003,
        store_type="gimssine",
        order_number=33531,
        name="#33531",
        shopify_created_at=timezone.now(),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=8001,
        sku="ISBN003",
        quantity=1,
        purchase_status="unordered",
    )

    order_data = _make_order_data(900003, [])  # no line items anymore
    _sync_single_order(order_data, "gimssine")

    assert not LineItem.objects.filter(order=order, shopify_line_item_id=8001).exists()


@pytest.mark.django_db
def test_sync_keeps_orphaned_line_item_with_po():
    """Line items linked to a PurchaseOrder must not be deleted even if Shopify no longer reports them."""
    order = Order.objects.create(
        shopify_order_id=900004,
        store_type="gimssine",
        order_number=33532,
        name="#33532",
        shopify_created_at=timezone.now(),
    )
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=9001,
        sku="ISBN004",
        quantity=1,
        purchase_status="unordered",
    )
    po = PurchaseOrder.objects.create(sku="ISBN004", title="Test", distributor="bookseen", quantity=1, status="pending")
    po.line_items.add(li)

    order_data = _make_order_data(900004, [])  # line item removed from Shopify
    _sync_single_order(order_data, "gimssine")

    assert LineItem.objects.filter(order=order, shopify_line_item_id=9001).exists()


def test_parse_next_page_info_with_next():
    link = '<https://shop.myshopify.com/admin/api/2024-10/orders.json?limit=250&page_info=abc123>; rel="next"'
    assert _parse_next_page_info(link) == "abc123"


def test_parse_next_page_info_only_prev():
    link = '<https://shop.myshopify.com/admin/api/2024-10/orders.json?limit=250&page_info=prev99>; rel="previous"'
    assert _parse_next_page_info(link) is None


def test_parse_next_page_info_prev_and_next():
    link = (
        '<https://shop.myshopify.com/admin/api/2024-10/orders.json?page_info=prev99>; rel="previous", '
        '<https://shop.myshopify.com/admin/api/2024-10/orders.json?page_info=next42>; rel="next"'
    )
    assert _parse_next_page_info(link) == "next42"


def test_parse_next_page_info_none_header():
    assert _parse_next_page_info(None) is None


def test_parse_next_page_info_empty_string():
    assert _parse_next_page_info("") is None


def test_decimal_or_none_empty_string():
    assert _decimal_or_none("") is None


def test_decimal_or_none_none():
    assert _decimal_or_none(None) is None


def test_decimal_or_none_value():
    assert _decimal_or_none("9.99") == "9.99"


def test_fetch_all_orders_single_page():
    orders_page1 = [{"id": 1}, {"id": 2}]
    with patch("order.shopify_orders._get_with_headers") as mock_get:
        mock_get.return_value = ({"orders": orders_page1}, {})
        result = fetch_all_open_orders("shop.myshopify.com", "token123")
    assert result == orders_page1
    assert mock_get.call_count == 1


def test_fetch_all_orders_two_pages():
    orders_page1 = [{"id": 1}]
    orders_page2 = [{"id": 2}]
    link_with_next = '<https://shop.myshopify.com/admin/api/2024-10/orders.json?page_info=page2>; rel="next"'

    call_count = 0

    def side_effect(domain, token, path):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"orders": orders_page1}, {"Link": link_with_next}
        return {"orders": orders_page2}, {}

    with patch("order.shopify_orders._get_with_headers", side_effect=side_effect):
        result = fetch_all_open_orders("shop.myshopify.com", "token123")

    assert result == [{"id": 1}, {"id": 2}]
    assert call_count == 2
