"""SPEC-ORDER-014 TASK-001: LineItemRackNumberSummaryView (TDD).

Coverage targets (see plan.md M2):
  T1  not-shipped filter definition — not_shipped/shipment_confirmed/received/
      outbound_scheduled included, shipped excluded (AC-RACKSUM-001/007)
  T2  cross-order grouping by rack_number, each item keeps its own
      order_name (AC-RACKSUM-004/004b)
  T3  empty rack_number LineItems grouped into a single unassigned bucket
      (AC-RACKSUM-004a)
  T4  total_quantity sums member quantities, null quantity treated as 0
      (AC-RACKSUM-005)
  T5  member LineItem dict includes order_name/sku/title/quantity/
      logistics_status (AC-RACKSUM-006)
  T6  Order fully shipped is excluded entirely; partially shipped Order only
      contributes its not-shipped LineItems (AC-RACKSUM-007/007a)
  T7  response has no pagination fields (AC-RACKSUM-008)
  T8  arbitrary/bypass query params are ignored (AC-RACKSUM-002a)
  T9  zero not-shipped LineItems system-wide -> {"groups": []}
  T10 unauthenticated request -> 401
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, Order, Refund

User = get_user_model()

RACK_SUMMARY_URL = "/api/purchase-orders/line-items/rack-number-summary/"


def _make_order(shopify_order_id: int = 400001, store_type: str = "gimssine", **kwargs) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type=store_type, **kwargs)


def _make_line_item(
    order: Order, shopify_line_item_id: int = 1, sku: str = "SKU-RACKSUM-001", **kwargs
) -> LineItem:
    defaults = {"quantity": 1, "title": "Test Book"}
    defaults.update(kwargs)
    return LineItem.objects.create(
        order=order, shopify_line_item_id=shopify_line_item_id, sku=sku, **defaults
    )


def _flatten_line_items(groups: list[dict]) -> list[dict]:
    items = []
    for group in groups:
        items.extend(group["line_items"])
    return items


def _find_group(groups: list[dict], rack_number: str) -> dict | None:
    for group in groups:
        if group["rack_number"] == rack_number:
            return group
    return None


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec014_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.mark.django_db
class TestNotShippedFilter:
    """T1: AC-RACKSUM-001/007 — not-shipped statuses included, shipped excluded."""

    def test_all_not_shipped_statuses_are_included(self, auth_client):
        order = _make_order()
        statuses = ["not_shipped", "shipment_confirmed", "received", "outbound_scheduled"]
        for idx, status_value in enumerate(statuses):
            _make_line_item(
                order,
                shopify_line_item_id=idx + 1,
                sku=f"SKU-T1-{idx}",
                rack_number=f"A-{idx}",
                logistics_status=status_value,
            )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        skus = {item["sku"] for item in _flatten_line_items(response.json()["groups"])}
        assert skus == {f"SKU-T1-{idx}" for idx in range(len(statuses))}

    def test_shipped_status_is_excluded(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-T1-SHIPPED",
            rack_number="A-9",
            logistics_status="shipped",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        skus = {item["sku"] for item in _flatten_line_items(response.json()["groups"])}
        assert "SKU-T1-SHIPPED" not in skus


@pytest.mark.django_db
class TestCrossOrderGrouping:
    """T2: AC-RACKSUM-004/004b — same rack_number across different Orders is
    grouped together, each item retains its own order_number."""

    def test_same_rack_number_different_orders_grouped_together(self, auth_client):
        order1 = _make_order(shopify_order_id=400101, name="#1001")
        order2 = _make_order(shopify_order_id=400102, name="#1002")
        _make_line_item(order1, sku="SKU-T2-A", rack_number="B-1", logistics_status="received")
        _make_line_item(
            order2,
            shopify_line_item_id=2,
            sku="SKU-T2-B",
            rack_number="B-1",
            logistics_status="received",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        groups = response.json()["groups"]
        group = _find_group(groups, "B-1")
        assert group is not None
        assert len(group["line_items"]) == 2
        order_names = {item["order_name"] for item in group["line_items"]}
        assert order_names == {"#1001", "#1002"}


@pytest.mark.django_db
class TestUnassignedBucket:
    """T3: AC-RACKSUM-004a — empty rack_number LineItems go into a single
    unassigned bucket, not dropped."""

    def test_empty_rack_number_grouped_as_unassigned(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-T3-A",
            rack_number="",
            logistics_status="not_shipped",
        )
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-T3-B",
            rack_number="",
            logistics_status="received",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        groups = response.json()["groups"]
        unassigned = _find_group(groups, "")
        assert unassigned is not None
        assert unassigned["is_unassigned"] is True
        skus = {item["sku"] for item in unassigned["line_items"]}
        assert skus == {"SKU-T3-A", "SKU-T3-B"}


@pytest.mark.django_db
class TestTotalQuantity:
    """T4: AC-RACKSUM-005 — total_quantity sums member quantities, null
    quantity treated as 0."""

    def test_total_quantity_sums_members_with_null_as_zero(self, auth_client):
        order = _make_order()
        _make_line_item(order, sku="SKU-T4-A", rack_number="C-1", quantity=3)
        _make_line_item(
            order, shopify_line_item_id=2, sku="SKU-T4-B", rack_number="C-1", quantity=None
        )
        _make_line_item(
            order, shopify_line_item_id=3, sku="SKU-T4-C", rack_number="C-1", quantity=5
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        groups = response.json()["groups"]
        group = _find_group(groups, "C-1")
        assert group["total_quantity"] == 8


@pytest.mark.django_db
class TestMemberFields:
    """T5: AC-RACKSUM-006 — each member LineItem dict includes order_name/
    sku/title/quantity/logistics_status."""

    def test_member_line_item_has_required_fields(self, auth_client):
        order = _make_order(name="#2001")
        _make_line_item(
            order,
            sku="SKU-T5",
            title="Some Title",
            rack_number="D-1",
            quantity=4,
            logistics_status="outbound_scheduled",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        groups = response.json()["groups"]
        group = _find_group(groups, "D-1")
        item = group["line_items"][0]
        assert item["order_name"] == "#2001"
        assert item["sku"] == "SKU-T5"
        assert item["title"] == "Some Title"
        assert item["quantity"] == 4
        assert item["logistics_status"] == "outbound_scheduled"
        assert "id" in item


@pytest.mark.django_db
class TestOrderNameField:
    """SPEC-ORDER-014 regression: the summary view must display
    `Order.name` (the authoritative Shopify-style display identifier, e.g.
    "#EB10011778"), never `Order.order_number` (int, unreliable/divergent
    for manually-entered EB-prefixed orders). An EB order's order_number
    holds an unrelated integer completely disconnected from its name."""

    def test_eb_prefixed_order_shows_order_name_not_order_number(self, auth_client):
        order = _make_order(order_number=1778, name="#EB10011778")
        _make_line_item(
            order,
            sku="SKU-EB",
            rack_number="EB-01",
            logistics_status="not_shipped",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        groups = response.json()["groups"]
        group = _find_group(groups, "EB-01")
        item = group["line_items"][0]
        assert item["order_name"] == "#EB10011778"
        assert "order_number" not in item


@pytest.mark.django_db
class TestOrderLevelExclusion:
    """T6: AC-RACKSUM-007/007a — Order fully shipped excluded entirely;
    partially shipped Order contributes only its not-shipped LineItems."""

    def test_order_fully_shipped_is_excluded_entirely(self, auth_client):
        order = _make_order(order_number=3001)
        _make_line_item(order, sku="SKU-T6-A", rack_number="E-1", logistics_status="shipped")
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-T6-B",
            rack_number="E-1",
            logistics_status="shipped",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        groups = response.json()["groups"]
        assert _find_group(groups, "E-1") is None

    def test_order_partially_shipped_includes_only_not_shipped_items(self, auth_client):
        order = _make_order(order_number=3002)
        _make_line_item(order, sku="SKU-T6-C", rack_number="E-2", logistics_status="shipped")
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-T6-D",
            rack_number="E-2",
            logistics_status="received",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        groups = response.json()["groups"]
        group = _find_group(groups, "E-2")
        skus = {item["sku"] for item in group["line_items"]}
        assert skus == {"SKU-T6-D"}


@pytest.mark.django_db
class TestOrderCancelledExclusion:
    """Regression: LineItems with purchase_status="order_cancelled" must be
    excluded from the rack-number summary even when logistics_status is not
    "shipped" (mirrors the exclusion precedent used elsewhere for cancelled
    purchases)."""

    def test_order_cancelled_line_item_is_excluded(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-CANCELLED",
            rack_number="Z-1",
            logistics_status="not_shipped",
            purchase_status="order_cancelled",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        skus = {item["sku"] for item in _flatten_line_items(response.json()["groups"])}
        assert "SKU-CANCELLED" not in skus

    def test_non_cancelled_not_shipped_line_item_still_included(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-NOT-CANCELLED",
            rack_number="Z-2",
            logistics_status="not_shipped",
            purchase_status="unordered",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        skus = {item["sku"] for item in _flatten_line_items(response.json()["groups"])}
        assert "SKU-NOT-CANCELLED" in skus


@pytest.mark.django_db
class TestRefundExclusion:
    """Regression: a fully refunded (주문취소된) LineItem must not appear in the
    rack-number summary, and a partially refunded one must contribute only its
    net (quantity - refunded) amount.

    Same rule UnorderedItemsView / the reorder-candidate views already apply —
    the summary view was the only cross-order LineItem list that skipped it,
    so cancelled items kept showing up under their rack number."""

    def _refund(self, order, line_item, quantity, shopify_refund_id=900001):
        return Refund.objects.create(
            order=order,
            shopify_refund_id=shopify_refund_id,
            line_item_id=line_item.shopify_line_item_id,
            quantity=quantity,
        )

    def test_fully_refunded_line_item_is_excluded(self, auth_client):
        order = _make_order()
        li = _make_line_item(
            order,
            sku="SKU-REFUNDED-FULL",
            rack_number="R-1",
            quantity=1,
            logistics_status="not_shipped",
        )
        self._refund(order, li, 1)

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        skus = {item["sku"] for item in _flatten_line_items(response.json()["groups"])}
        assert "SKU-REFUNDED-FULL" not in skus

    def test_partially_refunded_line_item_contributes_net_quantity(self, auth_client):
        order = _make_order()
        li = _make_line_item(
            order,
            sku="SKU-REFUNDED-PART",
            rack_number="R-2",
            quantity=3,
            logistics_status="not_shipped",
        )
        self._refund(order, li, 1)

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        group = _find_group(response.json()["groups"], "R-2")
        assert group is not None
        assert group["total_quantity"] == 2
        assert group["line_items"][0]["quantity"] == 2

    def test_unrefunded_line_item_keeps_full_quantity(self, auth_client):
        order = _make_order()
        _make_line_item(
            order,
            sku="SKU-NO-REFUND",
            rack_number="R-3",
            quantity=2,
            logistics_status="not_shipped",
        )

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        group = _find_group(response.json()["groups"], "R-3")
        assert group is not None
        assert group["total_quantity"] == 2
        assert group["line_items"][0]["quantity"] == 2

    def test_refund_of_another_order_does_not_leak(self, auth_client):
        """Refund rows are keyed by (order_id, shopify_line_item_id) — a refund
        recorded under a different Order must not suppress this LineItem."""
        order_a = _make_order(shopify_order_id=400901)
        order_b = _make_order(shopify_order_id=400902)
        li_a = _make_line_item(
            order_a,
            shopify_line_item_id=7001,
            sku="SKU-CROSS-A",
            rack_number="R-4",
            quantity=1,
            logistics_status="not_shipped",
        )
        _make_line_item(
            order_b,
            shopify_line_item_id=7001,
            sku="SKU-CROSS-B",
            rack_number="R-4",
            quantity=1,
            logistics_status="not_shipped",
        )
        self._refund(order_a, li_a, 1)

        response = auth_client.get(RACK_SUMMARY_URL)

        skus = {item["sku"] for item in _flatten_line_items(response.json()["groups"])}
        assert "SKU-CROSS-A" not in skus
        assert "SKU-CROSS-B" in skus


@pytest.mark.django_db
class TestNoPagination:
    """T7: AC-RACKSUM-008 — response contains no pagination fields."""

    def test_response_has_no_pagination_fields(self, auth_client):
        order = _make_order()
        _make_line_item(order, sku="SKU-T7", rack_number="F-1", logistics_status="received")

        response = auth_client.get(RACK_SUMMARY_URL)

        body = response.json()
        assert "page" not in body
        assert "next" not in body
        assert "previous" not in body
        assert "count" not in body
        assert set(body.keys()) == {"groups"}


@pytest.mark.django_db
class TestQueryParamsIgnored:
    """T8: AC-RACKSUM-002a — bypass/unknown query params do not disable the
    not-shipped filter."""

    def test_bypass_query_param_is_ignored(self, auth_client):
        order = _make_order()
        _make_line_item(
            order, sku="SKU-T8-SHIPPED", rack_number="G-1", logistics_status="shipped"
        )
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-T8-NOTSHIPPED",
            rack_number="G-1",
            logistics_status="received",
        )

        response = auth_client.get(RACK_SUMMARY_URL, {"include_shipped": "true"})

        groups = response.json()["groups"]
        skus = {item["sku"] for item in _flatten_line_items(groups)}
        assert skus == {"SKU-T8-NOTSHIPPED"}


@pytest.mark.django_db
class TestEmptySystemWide:
    """T9: zero not-shipped LineItems system-wide -> {"groups": []}."""

    def test_zero_not_shipped_line_items_returns_empty_groups(self, auth_client):
        order = _make_order()
        _make_line_item(order, sku="SKU-T9", rack_number="H-1", logistics_status="shipped")

        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        assert response.json() == {"groups": []}

    def test_no_line_items_at_all_returns_empty_groups(self, auth_client):
        response = auth_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 200
        assert response.json() == {"groups": []}


@pytest.mark.django_db
class TestAuthentication:
    """T10: unauthenticated request -> 401."""

    def test_unauthenticated_request_returns_401(self, anon_client):
        response = anon_client.get(RACK_SUMMARY_URL)

        assert response.status_code == 401
