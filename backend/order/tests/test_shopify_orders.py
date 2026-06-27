from unittest.mock import patch

import pytest

from order.shopify_orders import (
    _decimal_or_none,
    _parse_next_page_info,
    fetch_all_open_orders,
)


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
