"""Tests for OrderResyncView — POST /api/orders/{id}/sync/"""
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import Order, Refund

User = get_user_model()
RESYNC_URL = "/api/orders/{pk}/sync/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="resync_test_user", password="testpass123")

@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client

@pytest.fixture
def gimssine_order(db) -> Order:
    return Order.objects.create(
        shopify_order_id=99001,
        store_type="gimssine",
        order_number=5001,
        name="#5001",
        financial_status="pending",
        shopify_created_at=timezone.now(),
    )

# Test 1: 200 + refreshed data on success
@pytest.mark.django_db
def test_resync_returns_200_on_success(auth_client, gimssine_order):
    shopify_response = {
        "order": {
            "id": gimssine_order.shopify_order_id,
            "order_number": 5001,
            "name": "#5001",
            "financial_status": "paid",  # changed
            "fulfillment_status": None,
            "total_price": "29900.00",
            "subtotal_price": "29900.00",
            "total_tax": "0.00",
            "total_discounts": "0.00",
            "total_shipping_price_set": None,
            "currency": "KRW",
            "gateway": "manual",
            "note": None,
            "tags": "",
            "cancel_reason": None,
            "source_name": "web",
            "created_at": "2026-06-22T00:00:00Z",
            "updated_at": "2026-06-22T01:00:00Z",
            "closed_at": None,
            "cancelled_at": None,
            "processed_at": "2026-06-22T00:00:00Z",
            "customer": None,
            "shipping_address": None,
            "line_items": [],
            "shipping_lines": [],
            "refunds": [],
            "email": None,
            "phone": None,
        }
    }
    with patch("order.views.sync_single_order_from_shopify") as mock_sync:
        mock_sync.return_value = shopify_response["order"]
        url = RESYNC_URL.format(pk=gimssine_order.pk)
        res = auth_client.post(url)
    assert res.status_code == 200
    assert "id" in res.data
    assert "line_items" in res.data

# Test 2: 404 for missing local order
@pytest.mark.django_db
def test_resync_returns_404_for_missing_order(auth_client):
    url = RESYNC_URL.format(pk=99999999)
    res = auth_client.post(url)
    assert res.status_code == 404

# Test 3: 401 for unauthenticated
@pytest.mark.django_db
def test_resync_requires_authentication(gimssine_order):
    client = APIClient()
    url = RESYNC_URL.format(pk=gimssine_order.pk)
    res = client.post(url)
    assert res.status_code == 401

# Test 4: 502 on Shopify network error
@pytest.mark.django_db
def test_resync_returns_502_on_network_error(auth_client, gimssine_order):
    with patch("order.views.sync_single_order_from_shopify") as mock_sync:
        mock_sync.side_effect = urllib.error.URLError("Connection refused")
        url = RESYNC_URL.format(pk=gimssine_order.pk)
        res = auth_client.post(url)
    assert res.status_code == 502
    assert "error" in res.data

# Test 5: 404 when Shopify returns 404 (deleted order)
@pytest.mark.django_db
def test_resync_returns_404_when_shopify_order_deleted(auth_client, gimssine_order):
    http_error = urllib.error.HTTPError(
        url="", code=404, msg="Not Found", hdrs=MagicMock(), fp=None
    )
    with patch("order.views.sync_single_order_from_shopify") as mock_sync:
        mock_sync.side_effect = http_error
        url = RESYNC_URL.format(pk=gimssine_order.pk)
        res = auth_client.post(url)
    assert res.status_code == 404
    assert "error" in res.data

# Test 6: 502 on Shopify 5xx error
@pytest.mark.django_db
def test_resync_returns_502_on_shopify_server_error(auth_client, gimssine_order):
    http_error = urllib.error.HTTPError(
        url="", code=500, msg="Internal Server Error", hdrs=MagicMock(), fp=None
    )
    with patch("order.views.sync_single_order_from_shopify") as mock_sync:
        mock_sync.side_effect = http_error
        url = RESYNC_URL.format(pk=gimssine_order.pk)
        res = auth_client.post(url)
    assert res.status_code == 502
    assert "error" in res.data


def _base_shopify_order(order_obj, refunds=None):
    """Build a minimal Shopify order dict for resync tests."""
    return {
        "id": order_obj.shopify_order_id,
        "order_number": order_obj.order_number,
        "name": order_obj.name,
        "financial_status": order_obj.financial_status,
        "fulfillment_status": None,
        "total_price": "0.00",
        "subtotal_price": "0.00",
        "total_tax": "0.00",
        "total_discounts": "0.00",
        "total_shipping_price_set": None,
        "currency": "KRW",
        "gateway": "manual",
        "note": None,
        "tags": "",
        "cancel_reason": None,
        "source_name": "web",
        "created_at": "2026-06-22T00:00:00Z",
        "updated_at": "2026-06-22T01:00:00Z",
        "closed_at": None,
        "cancelled_at": None,
        "processed_at": "2026-06-22T00:00:00Z",
        "customer": None,
        "shipping_address": None,
        "line_items": [],
        "shipping_lines": [],
        "refunds": refunds if refunds is not None else [],
        "email": None,
        "phone": None,
    }


# SPEC-ORDER-005 Case A: new refund from Shopify (DB had none)
@pytest.mark.django_db
def test_resync_refund_case_a_new_refund_created(auth_client, gimssine_order):
    """Case A: DB has no refund, Shopify returns one → refund is created after resync."""
    assert Refund.objects.filter(order=gimssine_order).count() == 0

    shopify_order_data = _base_shopify_order(
        gimssine_order,
        refunds=[{"id": 999, "note": "test refund", "created_at": "2026-06-22T00:00:00Z", "refund_line_items": []}],
    )
    with patch("order.shopify_orders._get_with_headers") as mock_fetch:
        mock_fetch.return_value = ({"order": shopify_order_data}, {})
        url = RESYNC_URL.format(pk=gimssine_order.pk)
        res = auth_client.post(url)

    assert res.status_code == 200
    assert Refund.objects.filter(order=gimssine_order).count() == 1
    assert res.data.get("has_refund") is True


# SPEC-ORDER-005 Case B: stale refund cleared (DB had refund, Shopify returns empty)
@pytest.mark.django_db
def test_resync_refund_case_b_stale_refund_cleared(auth_client, gimssine_order):
    """Case B: DB has a refund, Shopify returns empty list → refund is removed after resync."""
    Refund.objects.create(
        order=gimssine_order,
        shopify_refund_id=123,
        note="old refund",
    )
    assert Refund.objects.filter(order=gimssine_order).count() == 1

    shopify_order_data = _base_shopify_order(gimssine_order, refunds=[])
    with patch("order.shopify_orders._get_with_headers") as mock_fetch:
        mock_fetch.return_value = ({"order": shopify_order_data}, {})
        url = RESYNC_URL.format(pk=gimssine_order.pk)
        res = auth_client.post(url)

    assert res.status_code == 200
    assert Refund.objects.filter(order=gimssine_order).count() == 0
    assert res.data.get("has_refund") is False


# SPEC-ORDER-005 Case C: no duplication (same refund in DB and Shopify)
@pytest.mark.django_db
def test_resync_refund_case_c_no_duplication(auth_client, gimssine_order):
    """Case C: DB has refund id=123, Shopify returns same id=123 → only 1 refund remains."""
    Refund.objects.create(
        order=gimssine_order,
        shopify_refund_id=123,
        note="existing refund",
    )
    assert Refund.objects.filter(order=gimssine_order).count() == 1

    shopify_order_data = _base_shopify_order(
        gimssine_order,
        refunds=[{"id": 123, "note": "existing refund", "created_at": "2026-06-22T00:00:00Z", "refund_line_items": []}],
    )
    with patch("order.shopify_orders._get_with_headers") as mock_fetch:
        mock_fetch.return_value = ({"order": shopify_order_data}, {})
        url = RESYNC_URL.format(pk=gimssine_order.pk)
        res = auth_client.post(url)

    assert res.status_code == 200
    assert Refund.objects.filter(order=gimssine_order).count() == 1
    assert res.data.get("has_refund") is True
