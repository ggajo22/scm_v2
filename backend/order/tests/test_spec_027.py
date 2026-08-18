"""SPEC-ORDER-027: LineItemRackNumberSummaryView group-level received_quantity
aggregation (TDD).

group.received_quantity = Sum(min(li.received_quantity, net_qty)) over every
contributing LineItem, independent of logistics_status. net_qty reuses the
existing refund-netted value computed at purchase_order_views.py:3446.

Coverage (see acceptance.md for full Given-When-Then + mutation mapping):
  AC-RACKRECV-001  partial receipt (status not yet transitioned) still counts
                    — catches M1 (jointly with AC-004)
  AC-RACKRECV-002  clamp: refund shrinks net_qty after full receipt
                    — catches M2 (refund path, jointly with AC-003)
  AC-RACKRECV-003  clamp: NULL quantity makes net_qty 0 (defensive/pin case)
                    — catches M2 (NULL path, jointly with AC-002)
  AC-RACKRECV-004  multi-item group summation
                    — catches M1 (jointly with AC-001)
  AC-RACKRECV-005  field exists even when value is 0
                    — catches M3 (representative case)
  AC-RACKRECV-006  unassigned (is_unassigned) group aggregates identically
                    — catches M4 (sole)
  AC-RACKRECV-012  received_quantity accumulator is isolated per group
                    — catches M8 (sole)
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, Order, Refund

User = get_user_model()

RACK_SUMMARY_URL = "/api/purchase-orders/line-items/rack-number-summary/"


def _make_order(shopify_order_id: int = 500001, store_type: str = "gimssine", **kwargs) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type=store_type, **kwargs)


def _make_line_item(
    order: Order, shopify_line_item_id: int = 1, sku: str = "SKU-RACKRECV-001", **kwargs
) -> LineItem:
    defaults = {"quantity": 1, "title": "Test Book"}
    defaults.update(kwargs)
    return LineItem.objects.create(
        order=order, shopify_line_item_id=shopify_line_item_id, sku=sku, **defaults
    )


def _refund(order, line_item, quantity, shopify_refund_id=900001):
    return Refund.objects.create(
        order=order,
        shopify_refund_id=shopify_refund_id,
        line_item_id=line_item.shopify_line_item_id,
        quantity=quantity,
    )


def _find_group(groups: list[dict], rack_number: str) -> dict | None:
    for group in groups:
        if group["rack_number"] == rack_number:
            return group
    return None


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec027_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.mark.django_db
class TestPartialReceiptStatusIndependent:
    """AC-RACKRECV-001: partial receipt (status not yet transitioned to
    "received") still contributes its received_quantity — status-gating is
    forbidden (REQ-RACKRECV-004)."""

    def test_partial_receipt_counts_even_when_status_not_received(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-AC001",
            rack_number="P-1",
            quantity=5,
            received_quantity=3,
            logistics_status="shipment_confirmed",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        group = _find_group(response.json()["groups"], "P-1")
        assert group is not None
        assert group["total_quantity"] == 5
        assert group["received_quantity"] == 3


@pytest.mark.django_db
class TestClampAfterRefund:
    """AC-RACKRECV-002: after full receipt, a later refund shrinks net_qty —
    received_quantity must be clamped to the new net_qty, not left at the
    stale raw received_quantity."""

    def test_clamp_applies_when_refund_shrinks_net_qty(self, auth_client):
        order = _make_order()
        li = _make_line_item(
            order,
            sku="SKU-AC002",
            rack_number="P-2",
            quantity=5,
            received_quantity=5,
            logistics_status="received",
        )
        _refund(order, li, 2)

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        group = _find_group(response.json()["groups"], "P-2")
        assert group is not None
        assert group["total_quantity"] == 3
        assert group["received_quantity"] == 3


@pytest.mark.django_db
class TestClampWithNullQuantity:
    """AC-RACKRECV-003: quantity=None makes net_qty 0 — received_quantity
    must be clamped to 0, not left at the raw received_quantity. Defensive/
    pin case per acceptance.md N6 (not reachable via the current write path,
    but the write path is out of scope here — only the read-side clamp)."""

    def test_clamp_applies_when_quantity_is_null(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-AC003",
            rack_number="P-3",
            quantity=None,
            received_quantity=4,
            logistics_status="received",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        group = _find_group(response.json()["groups"], "P-3")
        assert group is not None
        assert group["total_quantity"] == 0
        assert group["received_quantity"] == 0


@pytest.mark.django_db
class TestMultiItemGroupSummation:
    """AC-RACKRECV-004: received_quantity sums across multiple LineItems in
    the same group, independent of each item's logistics_status."""

    def test_received_quantity_sums_across_members(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-AC004-1",
            rack_number="P-4",
            quantity=2,
            received_quantity=2,
            logistics_status="received",
        )
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-AC004-2",
            rack_number="P-4",
            quantity=4,
            received_quantity=1,
            logistics_status="shipment_confirmed",
        )
        _make_line_item(
            order,
            shopify_line_item_id=3,
            sku="SKU-AC004-3",
            rack_number="P-4",
            quantity=3,
            received_quantity=0,
            logistics_status="not_shipped",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        group = _find_group(response.json()["groups"], "P-4")
        assert group is not None
        assert group["total_quantity"] == 9
        assert group["received_quantity"] == 3


@pytest.mark.django_db
class TestReceivedQuantityFieldExists:
    """AC-RACKRECV-005: received_quantity key exists in the group dict even
    when its value is 0 — guards against key omission masked by a coincidental
    zero value."""

    def test_field_exists_with_zero_value(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-AC005",
            rack_number="P-5",
            quantity=3,
            received_quantity=0,
            logistics_status="not_shipped",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        group = _find_group(response.json()["groups"], "P-5")
        assert group is not None
        assert "received_quantity" in group
        assert group["received_quantity"] == 0
        assert group["total_quantity"] == 3


@pytest.mark.django_db
class TestUnassignedGroupAggregation:
    """AC-RACKRECV-006: the unassigned (rack_number="") bucket aggregates
    received_quantity identically to named groups — no special-case skip."""

    def test_unassigned_group_aggregates_received_quantity(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-AC006",
            rack_number="",
            quantity=5,
            received_quantity=2,
            logistics_status="received",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        group = _find_group(response.json()["groups"], "")
        assert group is not None
        assert group["is_unassigned"] is True
        assert group["total_quantity"] == 5
        assert group["received_quantity"] == 2


@pytest.mark.django_db
class TestReceivedQuantityGroupIsolation:
    """AC-RACKRECV-012: the received_quantity accumulator must be isolated
    per group — a shared/global accumulator would leak values between groups
    when there is more than one group in the response."""

    def test_received_quantity_does_not_leak_between_groups(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-AC012-1",
            rack_number="Q-1",
            quantity=5,
            received_quantity=3,
            logistics_status="received",
        )
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-AC012-2",
            rack_number="Q-2",
            quantity=4,
            received_quantity=1,
            logistics_status="received",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        groups = response.json()["groups"]
        group_q1 = _find_group(groups, "Q-1")
        group_q2 = _find_group(groups, "Q-2")
        assert group_q1 is not None
        assert group_q2 is not None
        assert group_q1["total_quantity"] == 5
        assert group_q1["received_quantity"] == 3
        assert group_q2["total_quantity"] == 4
        assert group_q2["received_quantity"] == 1
