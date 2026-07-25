from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from django.db import connection
from django.test.utils import CaptureQueriesContext

from order.shopify_orders import (
    _decimal_or_none,
    _parse_next_page_info,
    _sync_single_order,
    fetch_all_open_orders,
)
from order.models import LineItem, Order, PurchaseOrder, ShopifySkuSetMapping


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


# ---------------------------------------------------------------------------
# SPEC-SHOPIFY-SKU-SET-002: sync-time bundle expansion (REQ-SKUSET2-003/004/005)
# ---------------------------------------------------------------------------

_BUNDLE_SKU = "GITANMATH-F SET"


def _make_bundle_mapping(bundle_sku=_BUNDLE_SKU, member_isbns=("ISBN-A", "ISBN-B")):
    """Create a ShopifySkuSetMapping row per member ISBN, in sort_order."""
    for i, isbn in enumerate(member_isbns):
        ShopifySkuSetMapping.objects.create(bundle_sku=bundle_sku, member_isbn=isbn, sort_order=i)


@pytest.mark.django_db
def test_sync_bundle_sku_expands_to_member_isbn_rows():
    """AC-003-1: a bundle SKU line item expands into one LineItem row per
    member ISBN, all sharing the same shopify_line_item_id, each with the
    FULL (undivided) quantity and the rest of the fields copied verbatim."""
    _make_bundle_mapping()
    order = Order.objects.create(
        shopify_order_id=910001,
        store_type="gimssine",
        order_number=41001,
        name="#41001",
        shopify_created_at=timezone.now(),
    )
    li = _make_shopify_line_item(9101, sku=_BUNDLE_SKU)
    li["quantity"] = 2
    order_data = _make_order_data(910001, [li])

    _sync_single_order(order_data, "gimssine")

    rows = LineItem.objects.filter(order=order, shopify_line_item_id=9101).order_by("sku")
    assert rows.count() == 2
    assert list(rows.values_list("sku", flat=True)) == ["ISBN-A", "ISBN-B"]
    for row in rows:
        assert row.quantity == 2  # full bundle quantity, not divided
        assert row.title == "Test Book"
        assert row.vendor == "Test Publisher"
        assert row.price == Decimal("5000.00")


@pytest.mark.django_db
def test_sync_regular_sku_unaffected_by_unrelated_bundle_mapping():
    """AC-003-2: a SKU with no bundle mapping is synced as a single row
    exactly as before, even when unrelated bundle mappings exist."""
    _make_bundle_mapping(bundle_sku="OTHER-SET", member_isbns=("OTHER-ISBN",))
    order = Order.objects.create(
        shopify_order_id=910002,
        store_type="gimssine",
        order_number=41002,
        name="#41002",
        shopify_created_at=timezone.now(),
    )
    li = _make_shopify_line_item(9102, sku="REGULAR-SKU")
    order_data = _make_order_data(910002, [li])

    _sync_single_order(order_data, "gimssine")

    assert LineItem.objects.filter(order=order, shopify_line_item_id=9102).count() == 1
    li_row = LineItem.objects.get(order=order, shopify_line_item_id=9102)
    assert li_row.sku == "REGULAR-SKU"


@pytest.mark.django_db
def test_sync_bundle_map_loaded_exactly_once_per_order():
    """AC-003-3: ShopifySkuSetMapping is queried exactly once per
    _sync_single_order call, no matter how many bundle SKU line items
    the order contains."""
    _make_bundle_mapping(bundle_sku="SET-1", member_isbns=("ISBN-1",))
    _make_bundle_mapping(bundle_sku="SET-2", member_isbns=("ISBN-2",))
    _make_bundle_mapping(bundle_sku="SET-3", member_isbns=("ISBN-3",))
    Order.objects.create(
        shopify_order_id=910003,
        store_type="gimssine",
        order_number=41003,
        name="#41003",
        shopify_created_at=timezone.now(),
    )
    line_items = [
        _make_shopify_line_item(9103, sku="SET-1"),
        _make_shopify_line_item(9104, sku="SET-2"),
        _make_shopify_line_item(9105, sku="SET-3"),
    ]
    order_data = _make_order_data(910003, line_items)

    with CaptureQueriesContext(connection) as ctx:
        _sync_single_order(order_data, "gimssine")

    mapping_queries = [
        q for q in ctx.captured_queries if "order_shopify_sku_set_mapping" in q["sql"]
    ]
    assert len(mapping_queries) == 1


@pytest.mark.django_db
def test_sync_removes_all_bundle_member_rows_when_unordered_and_line_item_disappears():
    """AC-004-1: when a previously-expanded bundle line item is no longer
    reported by Shopify, all N expanded member rows are deleted (still
    filtered purely by shopify_line_item_id — REQ-SKUSET2-004)."""
    _make_bundle_mapping()
    Order.objects.create(
        shopify_order_id=910004,
        store_type="gimssine",
        order_number=41004,
        name="#41004",
        shopify_created_at=timezone.now(),
    )
    li = _make_shopify_line_item(9106, sku=_BUNDLE_SKU)
    order_data = _make_order_data(910004, [li])
    _sync_single_order(order_data, "gimssine")
    rows_qs = LineItem.objects.filter(order__shopify_order_id=910004, shopify_line_item_id=9106)
    assert rows_qs.count() == 2

    order_data_empty = _make_order_data(910004, [])
    _sync_single_order(order_data_empty, "gimssine")

    assert rows_qs.count() == 0


@pytest.mark.django_db
def test_sync_keeps_purchase_ordered_bundle_member_rows_when_line_item_disappears():
    """AC-004-2: expanded member rows already linked to a PurchaseOrder
    survive even when Shopify stops reporting the shared line item;
    unordered siblings are still removed."""
    _make_bundle_mapping()
    Order.objects.create(
        shopify_order_id=910005,
        store_type="gimssine",
        order_number=41005,
        name="#41005",
        shopify_created_at=timezone.now(),
    )
    li = _make_shopify_line_item(9107, sku=_BUNDLE_SKU)
    order_data = _make_order_data(910005, [li])
    _sync_single_order(order_data, "gimssine")
    li_a = LineItem.objects.get(
        order__shopify_order_id=910005, shopify_line_item_id=9107, sku="ISBN-A"
    )
    po = PurchaseOrder.objects.create(
        sku="ISBN-A", title="Test", distributor="booxen", quantity=2, status="pending"
    )
    po.line_items.add(li_a)

    order_data_empty = _make_order_data(910005, [])
    _sync_single_order(order_data_empty, "gimssine")

    assert LineItem.objects.filter(pk=li_a.pk).exists()
    assert not LineItem.objects.filter(
        order__shopify_order_id=910005, shopify_line_item_id=9107, sku="ISBN-B"
    ).exists()


@pytest.mark.django_db
def test_sync_bundle_member_rows_share_correct_location():
    """AC-005-1: all N expanded member rows receive the same, correct
    location value derived from line_item_location_map (REQ-SKUSET2-005)."""
    _make_bundle_mapping()
    Order.objects.create(
        shopify_order_id=910006,
        store_type="gimssine",
        order_number=41006,
        name="#41006",
        shopify_created_at=timezone.now(),
    )
    li = _make_shopify_line_item(9108, sku=_BUNDLE_SKU)
    order_data = _make_order_data(910006, [li])

    _sync_single_order(order_data, "gimssine", line_item_location_map={9108: "NJ"})

    rows = LineItem.objects.filter(order__shopify_order_id=910006, shopify_line_item_id=9108)
    assert rows.count() == 2
    for row in rows:
        assert row.location == "NJ"


@pytest.mark.django_db
def test_sync_bundle_sku_zero_quantity_expands_with_zero_quantity():
    """Edge case (acceptance.md 엣지 케이스 목록): a bundle line item with
    quantity=0 expands into member rows that each also carry quantity=0."""
    _make_bundle_mapping()
    Order.objects.create(
        shopify_order_id=910007,
        store_type="gimssine",
        order_number=41007,
        name="#41007",
        shopify_created_at=timezone.now(),
    )
    li = _make_shopify_line_item(9109, sku=_BUNDLE_SKU)
    li["quantity"] = 0
    order_data = _make_order_data(910007, [li])

    _sync_single_order(order_data, "gimssine")

    rows = LineItem.objects.filter(order__shopify_order_id=910007, shopify_line_item_id=9109)
    assert rows.count() == 2
    for row in rows:
        assert row.quantity == 0


@pytest.mark.django_db
def test_sync_null_sku_line_item_not_looked_up_as_bundle():
    """Edge case (acceptance.md 엣지 케이스 목록): a line item with sku=None is
    never matched against the (string-keyed) bundle map and is synced as a
    single row exactly as before."""
    Order.objects.create(
        shopify_order_id=910008,
        store_type="gimssine",
        order_number=41008,
        name="#41008",
        shopify_created_at=timezone.now(),
    )
    li = _make_shopify_line_item(9110, sku=None)
    order_data = _make_order_data(910008, [li])

    _sync_single_order(order_data, "gimssine")

    rows_qs = LineItem.objects.filter(order__shopify_order_id=910008, shopify_line_item_id=9110)
    assert rows_qs.count() == 1
    assert rows_qs.get().sku is None


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
