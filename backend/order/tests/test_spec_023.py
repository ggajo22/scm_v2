"""SPEC-ORDER-023: 주문목록 표시 컬럼 개편 (마진율/물류상태/발주상태) — 백엔드 TDD.

Test functions map 1:1 to AC-OLIST-006~025 (backend-facing, including
013a/017a/018a/018b/020a/022a~f) in
`.moai/specs/SPEC-ORDER-023/acceptance.md`. See that document and
`spec.md` for the full Given/When/Then narrative and mutation rationale
behind each fixture choice.
"""
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import Customer, ExchangeRate, LineItem, Order, PurchaseOrder, Refund

User = get_user_model()
LIST_URL = "/api/orders/"
DETAIL_URL = "/api/orders/{pk}/"

EXCHANGE_RATE_TABLE = "orders_exchangerate"

# AC-OLIST-021: baseline (JWT user lookup 1 + pagination COUNT 1 + main
# SELECT 1 + prefetch_related x3: refunds/line_items/customer) re-measured
# in this session (M0) as 6, matching spec.md REQ-OLIST-022a. +1 batched
# ExchangeRate query (REQ-OLIST-019) +1 line_items__purchase_orders M2M
# prefetch (REQ-OLIST-021, v1.4.0) = 8.
TOTAL_QUERY_COUNT = 8

# AC-OLIST-025: the full OrderDetailSerializer field set (serializers.py
# Meta.fields, `:190-217`) must be byte-identical after the margin-formula
# extraction refactor — no field added or removed.
DETAIL_SERIALIZER_FIELDS = {
    "id", "shopify_order_id", "store_type", "order_number", "name",
    "email", "phone", "financial_status", "fulfillment_status",
    "total_price", "subtotal_price", "total_tax", "total_discounts",
    "total_shipping_price_set", "currency", "gateway", "note", "note_resolved", "tags",
    "cancel_reason", "source_name", "shopify_created_at",
    "shopify_updated_at", "closed_at", "cancelled_at", "processed_at",
    "has_refund", "customer", "shipping_address",
    "line_items", "shipping_lines", "refunds",
    "margin_amount", "margin_rate",
    "shipping_cost", "korea_warehouse_cost", "total_weight_grams",
    "confirmed_cost", "total_cost",
    "exchange_rate", "exchange_rate_date",
    "status",
    "ready_to_ship",
    # 주문상세/주문목록 표시 일원화: 상세도 목록과 같은 파생 값을 노출한다.
    "logistics_display",
    "purchase_display",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec023_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


_next_shopify_order_id = iter(range(923000, 924000))


def _make_order(shopify_order_id=None, **kwargs):
    if shopify_order_id is None:
        shopify_order_id = next(_next_shopify_order_id)
    kwargs.setdefault("store_type", "gimssine")
    kwargs.setdefault("financial_status", "paid")
    kwargs.setdefault("shopify_created_at", timezone.now())
    return Order.objects.create(shopify_order_id=shopify_order_id, **kwargs)


_next_line_item_id = iter(range(1, 100000))


def _make_line_item(order, **kwargs):
    kwargs.setdefault("shopify_line_item_id", next(_next_line_item_id))
    kwargs.setdefault("title", "테스트 상품")
    return LineItem.objects.create(order=order, **kwargs)


def _link_purchase_order(line_item, distributor="kyobo", status="confirmed"):
    """AC-OLIST-014/014a/014b: reproduce the production "발주 완료" shape —
    a PurchaseOrder linked via the M2M while the line item's own
    purchase_status stays "unordered" (PURCHASE_STATUS_CHOICES has no
    "ordered" value; purchase_order_views.py:1131 only adds the link).
    """
    po = PurchaseOrder.objects.create(
        sku=line_item.sku or "ISBN000",
        title=line_item.title,
        distributor=distributor,
        quantity=line_item.quantity or 1,
        status=status,
    )
    po.line_items.add(line_item)
    return po


def _get_item(res, shopify_order_id):
    for item in res.data["results"]:
        if item["shopify_order_id"] == shopify_order_id:
            return item
    raise AssertionError(f"order {shopify_order_id} not found in results")


# ---------------------------------------------------------------------------
# Standard logistics dataset (Order A~H, spec.md/acceptance.md) — shared by
# AC-OLIST-022~022f so filter mutations that only "any"-match one status are
# actually discriminated (v1.2.0 H1-new/H2-new, v1.2.1 N1/N2).
# ---------------------------------------------------------------------------


@pytest.fixture
def standard_dataset(db):
    orders = {}

    order_a = _make_order()
    _make_line_item(
        order_a, sku="ISBN-A", logistics_status="shipped", quantity=5, shipped_quantity=5,
    )
    orders["A"] = order_a

    order_b = _make_order()
    _make_line_item(
        order_b, sku="ISBN-B1", logistics_status="outbound_scheduled",
        shipped_quantity=4, quantity=10,
    )
    _make_line_item(
        order_b, sku="ISBN-B2", logistics_status="outbound_scheduled",
        shipped_quantity=0, quantity=5,
    )
    orders["B"] = order_b

    order_c = _make_order()
    _make_line_item(
        order_c, sku="ISBN-C1", logistics_status="received", shipped_quantity=0, quantity=3,
    )
    _make_line_item(
        order_c, sku="ISBN-C2", logistics_status="received", shipped_quantity=0, quantity=2,
    )
    orders["C"] = order_c

    order_d = _make_order()
    _make_line_item(
        order_d, sku="ISBN-D1", logistics_status="outbound_scheduled",
        shipped_quantity=0, quantity=3,
    )
    _make_line_item(
        order_d, sku="ISBN-D2", logistics_status="outbound_scheduled",
        shipped_quantity=0, quantity=2,
    )
    orders["D"] = order_d

    order_e = _make_order()
    _make_line_item(
        order_e, sku="ISBN-E", logistics_status="not_shipped", shipped_quantity=0, quantity=5,
    )
    orders["E"] = order_e

    order_f = _make_order()
    _make_line_item(
        order_f, sku="ISBN-F", logistics_status="shipment_confirmed",
        shipped_quantity=0, quantity=4,
    )
    orders["F"] = order_f

    order_g = _make_order()
    _make_line_item(
        order_g, sku="ISBN-G1", logistics_status="not_shipped", shipped_quantity=0, quantity=3,
    )
    _make_line_item(
        order_g, sku="ISBN-G2", logistics_status="shipment_confirmed",
        shipped_quantity=0, quantity=2,
    )
    orders["G"] = order_g

    order_h = _make_order()
    _make_line_item(
        order_h, sku="ISBN-H1", logistics_status="outbound_scheduled",
        shipped_quantity=0, quantity=3,
    )
    _make_line_item(
        order_h, sku="ISBN-H2", logistics_status="shipment_confirmed",
        shipped_quantity=0, quantity=2,
    )
    orders["H"] = order_h

    return orders


# ---------------------------------------------------------------------------
# 물류상태 파생 — AC-OLIST-006~013a
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac006_all_shipped_realistic_fixture(auth_client):
    """AC-OLIST-006: rule 1 must be evaluated before rule 2, even though this
    realistic fixture (shipped_quantity == quantity > 0) also satisfies
    rule 2's condition."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN001", logistics_status="shipped", quantity=5, shipped_quantity=5,
    )

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["logistics_display"] == "shipped"


@pytest.mark.django_db
def test_ac007_partial_shipped_threshold_gt_zero_not_gte_quantity(auth_client):
    """AC-OLIST-007: `shipped_quantity > 0` (NOT `>= quantity`) must trigger
    rule 2 even when no item is fully shipped."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-A", logistics_status="outbound_scheduled",
        shipped_quantity=4, quantity=10,
    )
    _make_line_item(
        order, sku="ISBN-B", logistics_status="outbound_scheduled",
        shipped_quantity=0, quantity=5,
    )

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["logistics_display"] == "partial_shipped"


@pytest.mark.django_db
def test_ac008_shipped_quantity_zero_is_not_partial(auth_client):
    """AC-OLIST-008: shipped_quantity=0 must NOT trigger rule 2."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN001", logistics_status="not_shipped", shipped_quantity=0, quantity=5,
    )

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["logistics_display"] == "not_shipped"


@pytest.mark.django_db
def test_ac009_priority_inversion_received_with_partial_shipment(auth_client):
    """AC-OLIST-009 [HARD]: rule 2 must be evaluated before rule 3 — a single
    `received` line item with shipped_quantity>0 must resolve to
    partial_shipped, NOT outbound_scheduled."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN001", logistics_status="received", shipped_quantity=3, quantity=10,
    )

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["logistics_display"] == "partial_shipped"


@pytest.mark.django_db
def test_ac010_all_received_to_outbound_scheduled(auth_client):
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-A", logistics_status="received", shipped_quantity=0, quantity=3,
    )
    _make_line_item(
        order, sku="ISBN-B", logistics_status="received", shipped_quantity=0, quantity=2,
    )

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["logistics_display"] == "outbound_scheduled"


@pytest.mark.django_db
def test_ac011_non_trackable_excluded_both_logistics_and_purchase(auth_client):
    """AC-OLIST-011 [HARD]: sku__isnull=False must gate BOTH the logistics
    and purchase derivations independently (H4)."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN001", logistics_status="received", shipped_quantity=0,
        quantity=5, purchase_status="in_stock",
    )
    # non-trackable: sku=None, extreme values that would flip both
    # derivations if the sku__isnull=False filter were missing anywhere.
    _make_line_item(order, sku=None, shipped_quantity=99, quantity=1)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["logistics_display"] == "outbound_scheduled"
    assert item["purchase_display"] == "ordered"


@pytest.mark.django_db
def test_ac012_zero_trackable_key_present_and_null(auth_client):
    """AC-OLIST-012 [H1]: `"logistics_display" in item` — key existence, not
    just `.get()` — is required so an unimplemented field cannot pass."""
    order = _make_order()
    _make_line_item(order, sku=None, shipped_quantity=0, quantity=1)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert "logistics_display" in item
    assert item["logistics_display"] is None


@pytest.mark.django_db
def test_ac013_rule4_uniform_passthrough(auth_client):
    order = _make_order()
    _make_line_item(
        order, sku="ISBN001", logistics_status="shipment_confirmed",
        shipped_quantity=0, quantity=3,
    )

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["logistics_display"] == "shipment_confirmed"


@pytest.mark.django_db
def test_ac013a_rule4a_mixed_states_to_partial(auth_client):
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-A", logistics_status="not_shipped", shipped_quantity=0, quantity=3,
    )
    _make_line_item(
        order, sku="ISBN-B", logistics_status="shipment_confirmed", shipped_quantity=0, quantity=2,
    )

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["logistics_display"] == "partial"


# ---------------------------------------------------------------------------
# 발주상태 파생 — AC-OLIST-014~016
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac014_any_awaiting_purchase_triggers_unordered(auth_client):
    """AC-OLIST-014 [HARD] (강화 v1.4.0): `any` vs `all` AND the PurchaseOrder
    linkage condition. B is `unordered` but already linked to a confirmed
    PurchaseOrder, so it is NOT awaiting purchase — only A is."""
    order = _make_order()
    item_a = _make_line_item(order, sku="ISBN-A", purchase_status="unordered", quantity=1)
    item_b = _make_line_item(order, sku="ISBN-B", purchase_status="unordered", quantity=1)
    _link_purchase_order(item_b)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    assert _get_item(res, order.shopify_order_id)["purchase_display"] == "unordered"

    # Remove the only genuinely-awaiting item: B alone must NOT be 미발주.
    # A `purchase_status`-only derivation returns "unordered" here and fails.
    item_a.delete()

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    assert _get_item(res, order.shopify_order_id)["purchase_display"] == "ordered"


@pytest.mark.django_db
def test_ac014a_purchase_order_linked_items_are_ordered(auth_client):
    """AC-OLIST-014a [HARD] (신규 v1.4.0): direct reproduction of production
    order #38360 — 8 trackable line items, all `purchase_status="unordered"`,
    each linked to its own confirmed PurchaseOrder. This is the shape 97.5%
    of production orders have."""
    order = _make_order()
    for i in range(8):
        li = _make_line_item(
            order, sku=f"ISBN-38360-{i}", purchase_status="unordered", quantity=1
        )
        _link_purchase_order(li, distributor="kyobo" if i < 4 else "booxen")

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    assert _get_item(res, order.shopify_order_id)["purchase_display"] == "ordered"


@pytest.mark.django_db
def test_ac014b_damaged_exchange_is_unordered_despite_linkage(auth_client):
    """AC-OLIST-014b [HARD] (신규 v1.4.0): `damaged_exchange` re-enters the
    reorder queue regardless of PurchaseOrder linkage — matching
    `_reorder_candidate_filter` (purchase_order_views.py:107-110). Applying
    the linkage exception uniformly across every purchase_status yields
    "ordered" here and diverges from the 미발주 목록 탭."""
    order = _make_order()
    item_a = _make_line_item(
        order, sku="ISBN-A", purchase_status="damaged_exchange", quantity=1
    )
    _link_purchase_order(item_a)
    _make_line_item(order, sku="ISBN-B", purchase_status="in_stock", quantity=1)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    assert _get_item(res, order.shopify_order_id)["purchase_display"] == "unordered"


@pytest.mark.django_db
def test_ac015_none_awaiting_purchase_yields_ordered(auth_client):
    order = _make_order()
    _make_line_item(order, sku="ISBN-A", purchase_status="in_stock", quantity=1)
    _make_line_item(order, sku="ISBN-B", purchase_status="cs_required", quantity=1)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["purchase_display"] == "ordered"


@pytest.mark.django_db
def test_ac016_zero_trackable_purchase_display_null(auth_client):
    """AC-OLIST-016: both sub-cases — (a) all line items sku=None, (b) zero
    line items at all."""
    order_a = _make_order()
    _make_line_item(order_a, sku=None, quantity=1)

    order_b = _make_order()

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item_a = _get_item(res, order_a.shopify_order_id)
    item_b = _get_item(res, order_b.shopify_order_id)
    assert "purchase_display" in item_a and item_a["purchase_display"] is None
    assert "purchase_display" in item_b and item_b["purchase_display"] is None


# ---------------------------------------------------------------------------
# 마진율 — AC-OLIST-017~018b
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac017_margin_rate_value_and_forbidden_fields(auth_client):
    ExchangeRate.objects.create(effective_date=timezone.now().date(), rate=Decimal("1000.00"))
    order = _make_order(total_price=Decimal("100.00"))
    _make_line_item(order, sku="ISBN001", quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["margin_rate"] == "67.75"
    for forbidden in (
        "margin_amount", "shipping_cost", "korea_warehouse_cost",
        "confirmed_cost", "total_cost", "total_weight_grams",
    ):
        assert forbidden not in item


@pytest.mark.django_db
def test_ac017a_margin_rate_quantized_once_not_from_rounded_components(auth_client):
    """AC-OLIST-017a: must quantize once from the unrounded Decimal sum, not
    re-derive from already-rounded confirmed_cost/shipping_cost/
    korea_warehouse_cost strings (would land at 86.01 instead of 86.02)."""
    ExchangeRate.objects.create(effective_date=timezone.now().date(), rate=Decimal("1000.00"))
    order = _make_order(total_price=Decimal("100.00"))
    _make_line_item(
        order, sku="ISBN001", quantity=1, confirmed_price=Decimal("10005.00"), grams=500,
    )

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["margin_rate"] == "86.02"


@pytest.mark.django_db
def test_ac018_margin_rate_null_no_confirmed_price(auth_client):
    ExchangeRate.objects.create(effective_date=timezone.now().date(), rate=Decimal("1000.00"))
    order = _make_order(total_price=Decimal("100.00"))
    _make_line_item(order, sku="ISBN001", quantity=3, confirmed_price=None, grams=0)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert "margin_rate" in item
    assert item["margin_rate"] is None


@pytest.mark.django_db
def test_ac018a_margin_rate_null_no_exchange_rate_returns_200_not_500(auth_client, db):
    """AC-OLIST-018a [H3]: the batch loader must return None, never raise
    IndexError, when no ExchangeRate record qualifies."""
    order = _make_order(total_price=Decimal("100.00"))
    _make_line_item(order, sku="ISBN001", quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert "margin_rate" in item
    assert item["margin_rate"] is None


@pytest.mark.django_db
def test_ac018b_margin_rate_null_total_price_zero(auth_client):
    ExchangeRate.objects.create(effective_date=timezone.now().date(), rate=Decimal("1000.00"))
    order = _make_order(total_price=Decimal("0.00"))
    _make_line_item(order, sku="ISBN001", quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert "margin_rate" in item
    assert item["margin_rate"] is None


# ---------------------------------------------------------------------------
# 성능 불변식 — AC-OLIST-019~021
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac019_batch_exchange_rate_load_accuracy_and_single_query(auth_client):
    d1 = timezone.now().date()
    d2 = d1 - timedelta(days=10)
    ExchangeRate.objects.create(effective_date=d1, rate=Decimal("1000.00"))
    ExchangeRate.objects.create(effective_date=d2, rate=Decimal("1250.00"))

    order_x = _make_order(
        total_price=Decimal("100.00"),
        shopify_created_at=timezone.make_aware(datetime.combine(d1, datetime.min.time())),
    )
    _make_line_item(order_x, sku="ISBN-X", quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    order_y = _make_order(
        total_price=Decimal("100.00"),
        shopify_created_at=timezone.make_aware(datetime.combine(d2, datetime.min.time())),
    )
    _make_line_item(order_y, sku="ISBN-Y", quantity=3, confirmed_price=Decimal("12500.00"), grams=0)

    # warm-up
    auth_client.get(LIST_URL)

    with CaptureQueriesContext(connection) as ctx:
        res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item_x = _get_item(res, order_x.shopify_order_id)
    item_y = _get_item(res, order_y.shopify_order_id)
    assert item_x["margin_rate"] == "67.75"
    assert item_y["margin_rate"] == "68.20"

    rate_hits = [q["sql"] for q in ctx.captured_queries if EXCHANGE_RATE_TABLE in q["sql"]]
    assert len(rate_hits) == 1, (
        f"expected exactly 1 orders_exchangerate query, got {len(rate_hits)}"
    )


@pytest.mark.django_db
def test_ac020_batch_load_fallback_preserved(auth_client):
    order_date = timezone.now().date()
    fallback_date = order_date - timedelta(days=3)
    ExchangeRate.objects.create(effective_date=fallback_date, rate=Decimal("1000.00"))

    order = _make_order(
        total_price=Decimal("100.00"),
        shopify_created_at=timezone.make_aware(datetime.combine(order_date, datetime.min.time())),
    )
    _make_line_item(order, sku="ISBN001", quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["margin_rate"] == "67.75"


@pytest.mark.django_db
def test_ac020a_batch_load_date_uses_utc_not_localtime(auth_client):
    """AC-OLIST-020a [HARD]: batch loader must call `.date()` directly on the
    UTC-aware `shopify_created_at`, NOT `timezone.localtime(...).date()` —
    otherwise a KST override shifts 23:30 UTC into the next calendar day and
    picks the wrong rate."""
    with override_settings(TIME_ZONE="Asia/Seoul"):
        ExchangeRate.objects.create(effective_date="2026-08-01", rate=Decimal("1000.00"))
        ExchangeRate.objects.create(effective_date="2026-08-02", rate=Decimal("1200.00"))
        order = _make_order(
            total_price=Decimal("100.00"),
            shopify_created_at=datetime(2026, 8, 1, 23, 30, tzinfo=dt_timezone.utc),
        )
        _make_line_item(
            order, sku="ISBN001", quantity=3, confirmed_price=Decimal("10000.00"), grams=0,
        )

        res = auth_client.get(LIST_URL)

        assert res.status_code == 200
        item = _get_item(res, order.shopify_order_id)
        assert item["margin_rate"] == "67.75"


@pytest.mark.django_db
def test_ac021_total_query_count_exact_eight_and_page_size_invariant(auth_client):
    """AC-OLIST-021 [HARD]: absolute constant 8 (7 before v1.4.0 added the
    line_items__purchase_orders prefetch), identical for a 1-order page and a
    5-order page (customer-connected trackable orders, per M0/REQ-022a)."""
    customer_solo = Customer.objects.create(shopify_customer_id=970001)
    order_solo = _make_order(
        store_type="gimssine",
        total_price=Decimal("100.00"),
        customer=customer_solo,
    )
    _make_line_item(
        order_solo, sku="ISBN-SOLO", quantity=1, confirmed_price=Decimal("1000.00"), grams=0,
    )

    other_orders = []
    for i in range(4):
        customer = Customer.objects.create(shopify_customer_id=970100 + i)
        order = _make_order(
            store_type="etoile",
            total_price=Decimal("100.00"),
            customer=customer,
        )
        _make_line_item(
            order, sku=f"ISBN-{i}", quantity=1, confirmed_price=Decimal("1000.00"), grams=0,
        )
        other_orders.append(order)

    ExchangeRate.objects.create(effective_date=timezone.now().date(), rate=Decimal("1000.00"))

    # warm-up
    auth_client.get(LIST_URL, {"store_type": "gimssine"})

    with CaptureQueriesContext(connection) as ctx_one:
        res_one = auth_client.get(LIST_URL, {"store_type": "gimssine"})
    with CaptureQueriesContext(connection) as ctx_five:
        res_five = auth_client.get(LIST_URL)

    assert res_one.status_code == 200
    assert res_five.status_code == 200
    assert res_one.data["count"] == 1
    assert res_five.data["count"] == 5

    assert len(ctx_one.captured_queries) == TOTAL_QUERY_COUNT
    assert len(ctx_five.captured_queries) == TOTAL_QUERY_COUNT


# ---------------------------------------------------------------------------
# 물류상태 필터 — AC-OLIST-022~023
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac022_filter_partial_shipped(auth_client, standard_dataset):
    res = auth_client.get(LIST_URL, {"logistics_display": "partial_shipped"})

    assert res.status_code == 200
    assert res.data["count"] == 1
    ids = {item["shopify_order_id"] for item in res.data["results"]}
    assert ids == {standard_dataset["B"].shopify_order_id}
    b_item = _get_item(res, standard_dataset["B"].shopify_order_id)
    assert b_item["logistics_display"] == "partial_shipped"


@pytest.mark.django_db
def test_ac022a_filter_shipped(auth_client, standard_dataset):
    res = auth_client.get(LIST_URL, {"logistics_display": "shipped"})

    assert res.status_code == 200
    assert res.data["count"] == 1
    ids = {item["shopify_order_id"] for item in res.data["results"]}
    assert ids == {standard_dataset["A"].shopify_order_id}
    a_item = _get_item(res, standard_dataset["A"].shopify_order_id)
    assert a_item["logistics_display"] == "shipped"


@pytest.mark.django_db
def test_ac022b_filter_not_shipped(auth_client, standard_dataset):
    res = auth_client.get(LIST_URL, {"logistics_display": "not_shipped"})

    assert res.status_code == 200
    assert res.data["count"] == 1
    ids = {item["shopify_order_id"] for item in res.data["results"]}
    assert ids == {standard_dataset["E"].shopify_order_id}
    e_item = _get_item(res, standard_dataset["E"].shopify_order_id)
    assert e_item["logistics_display"] == "not_shipped"


@pytest.mark.django_db
def test_ac022c_filter_shipment_confirmed(auth_client, standard_dataset):
    res = auth_client.get(LIST_URL, {"logistics_display": "shipment_confirmed"})

    assert res.status_code == 200
    assert res.data["count"] == 1
    ids = {item["shopify_order_id"] for item in res.data["results"]}
    assert ids == {standard_dataset["F"].shopify_order_id}
    f_item = _get_item(res, standard_dataset["F"].shopify_order_id)
    assert f_item["logistics_display"] == "shipment_confirmed"


@pytest.mark.django_db
def test_ac022d_filter_outbound_scheduled_both_causes(auth_client, standard_dataset):
    """AC-OLIST-022d [H2-new/N1]: both rule-3 (Order C) and rule-4 (Order D)
    causes of outbound_scheduled must be included, and Order H (mixed,
    contains an outbound_scheduled item but is NOT uniform) must NOT."""
    res = auth_client.get(LIST_URL, {"logistics_display": "outbound_scheduled"})

    assert res.status_code == 200
    assert res.data["count"] == 2
    ids = {item["shopify_order_id"] for item in res.data["results"]}
    assert ids == {
        standard_dataset["C"].shopify_order_id,
        standard_dataset["D"].shopify_order_id,
    }
    c_item = _get_item(res, standard_dataset["C"].shopify_order_id)
    d_item = _get_item(res, standard_dataset["D"].shopify_order_id)
    assert c_item["logistics_display"] == "outbound_scheduled"
    assert d_item["logistics_display"] == "outbound_scheduled"


@pytest.mark.django_db
def test_ac022e_filter_partial(auth_client, standard_dataset):
    res = auth_client.get(LIST_URL, {"logistics_display": "partial"})

    assert res.status_code == 200
    assert res.data["count"] == 2
    ids = {item["shopify_order_id"] for item in res.data["results"]}
    assert ids == {
        standard_dataset["G"].shopify_order_id,
        standard_dataset["H"].shopify_order_id,
    }
    g_item = _get_item(res, standard_dataset["G"].shopify_order_id)
    h_item = _get_item(res, standard_dataset["H"].shopify_order_id)
    assert g_item["logistics_display"] == "partial"
    assert h_item["logistics_display"] == "partial"


@pytest.mark.django_db
def test_ac022f_invalid_filter_value_is_fail_open(auth_client, standard_dataset):
    res = auth_client.get(LIST_URL, {"logistics_display": "bogus_value"})

    assert res.status_code == 200
    assert res.data["count"] == 8


@pytest.mark.django_db
def test_ac023_filter_query_count_invariant(auth_client):
    for i in range(5):
        order = _make_order()
        _make_line_item(
            order, sku=f"ISBN-{i}", logistics_status="outbound_scheduled",
            shipped_quantity=4, quantity=10,
        )

    # warm-up
    auth_client.get(LIST_URL)

    with CaptureQueriesContext(connection) as ctx_unfiltered:
        res_unfiltered = auth_client.get(LIST_URL)
    with CaptureQueriesContext(connection) as ctx_filtered:
        res_filtered = auth_client.get(LIST_URL, {"logistics_display": "partial_shipped"})

    assert res_unfiltered.data["count"] == 5
    assert res_filtered.data["count"] == 5
    assert len(ctx_unfiltered.captured_queries) == len(ctx_filtered.captured_queries)


# ---------------------------------------------------------------------------
# 회귀 — AC-OLIST-024~025
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac024_backend_parameter_regression_with_concrete_counts(auth_client):
    # fulfillment_status="fulfilled" on these 3 avoids colliding with the
    # "unfulfilled" (fulfillment_status IS NULL) count below -- Order's
    # fulfillment_status has no model default, so it would otherwise be
    # NULL and match "unfulfilled" too.
    _make_order(financial_status="paid", fulfillment_status="fulfilled")
    _make_order(financial_status="refunded", fulfillment_status="fulfilled")
    _make_order(financial_status="pending", fulfillment_status="fulfilled")

    # financial_status="other" avoids colliding with the "paid" count above
    # -- _make_order defaults financial_status to "paid" otherwise.
    order_unfulfilled = _make_order(financial_status="other", fulfillment_status=None)
    _make_order(financial_status="other", fulfillment_status="fulfilled")

    res_financial = auth_client.get(LIST_URL, {"financial_status": "paid"})
    res_fulfillment = auth_client.get(LIST_URL, {"fulfillment_status": "unfulfilled"})

    assert res_financial.status_code == 200
    assert res_financial.data["count"] == 1
    assert res_financial.data["results"][0]["financial_status"] == "paid"

    assert res_fulfillment.status_code == 200
    assert res_fulfillment.data["count"] == 1
    assert (
        res_fulfillment.data["results"][0]["shopify_order_id"]
        == order_unfulfilled.shopify_order_id
    )


@pytest.mark.django_db
def test_ac025_detail_serializer_field_set_unchanged(auth_client):
    ExchangeRate.objects.create(effective_date=timezone.now().date(), rate=Decimal("1000.00"))
    order = _make_order(total_price=Decimal("100.00"))
    _make_line_item(order, sku="ISBN001", quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert set(res.data.keys()) == DETAIL_SERIALIZER_FIELDS
    assert res.data["margin_amount"] == "67.75"
    assert res.data["korea_warehouse_cost"] == "2.25"
    assert res.data["shipping_cost"] == "0.00"
    assert res.data["total_weight_grams"] == 0


# ---------------------------------------------------------------------------
# 환불(취소) 수량 차감 — 사용자 보고: 주문 #37830이 전체출고인데 부분출고로 표시
#
# 전량 환불된 LineItem은 고객이 더 이상 받을 물건이 아니므로 출고/발주 판정의
# 대상이 아니다. UnorderedItemsView와 _fully_refunded_line_item_ids가 이미
# 쓰는 규칙(잔여 수량 0 이하 -> 제외)을 표시 경로와 필터 경로에도 적용한다.
# 표시 경로(serializers._derive_line_item_states)와 SQL 필터 경로
# (views._apply_logistics_display_filter)는 항상 같은 판정을 내야 한다.
# ---------------------------------------------------------------------------


def _refund(line_item, quantity):
    return Refund.objects.create(
        order=line_item.order,
        shopify_refund_id=next(_next_line_item_id),
        line_item_id=line_item.shopify_line_item_id,
        quantity=quantity,
    )


@pytest.mark.django_db
def test_fully_refunded_item_excluded_from_logistics_display(auth_client):
    """주문 #37830 재현: 살아있는 품목이 전부 출고면 전체출고."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-LIVE", logistics_status="shipped", quantity=1, shipped_quantity=1
    )
    cancelled = _make_line_item(
        order, sku="ISBN-CANCELLED", logistics_status="not_shipped", quantity=1, shipped_quantity=0
    )
    _refund(cancelled, 1)

    res = auth_client.get(LIST_URL)

    assert _get_item(res, order.shopify_order_id)["logistics_display"] == "shipped"


@pytest.mark.django_db
def test_fully_refunded_item_excluded_from_logistics_filter(auth_client):
    """표시 경로와 SQL 필터 경로가 같은 판정을 낸다."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-LIVE", logistics_status="shipped", quantity=1, shipped_quantity=1
    )
    cancelled = _make_line_item(
        order, sku="ISBN-CANCELLED", logistics_status="not_shipped", quantity=1, shipped_quantity=0
    )
    _refund(cancelled, 1)

    res_shipped = auth_client.get(LIST_URL, {"logistics_display": "shipped"})
    res_partial = auth_client.get(LIST_URL, {"logistics_display": "partial_shipped"})

    assert [o["shopify_order_id"] for o in res_shipped.data["results"]] == [
        order.shopify_order_id
    ]
    assert order.shopify_order_id not in [
        o["shopify_order_id"] for o in res_partial.data["results"]
    ]


@pytest.mark.django_db
def test_partially_refunded_item_stays_in_scope(auth_client):
    """부분 환불은 제외 사유가 아니다 — 잔여 수량이 남아 있으므로 계속 판정 대상."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-LIVE", logistics_status="shipped", quantity=1, shipped_quantity=1
    )
    partial = _make_line_item(
        order, sku="ISBN-PARTIAL", logistics_status="not_shipped", quantity=3, shipped_quantity=0
    )
    _refund(partial, 1)

    res = auth_client.get(LIST_URL)

    assert _get_item(res, order.shopify_order_id)["logistics_display"] == "partial_shipped"


@pytest.mark.django_db
def test_every_item_fully_refunded_yields_null_display(auth_client):
    """전량 취소된 주문은 출고/발주 상태가 없다 (표시값 없음)."""
    order = _make_order()
    a = _make_line_item(
        order, sku="ISBN-A", logistics_status="shipped", quantity=1, shipped_quantity=1
    )
    b = _make_line_item(
        order, sku="ISBN-B", logistics_status="not_shipped", quantity=2, shipped_quantity=0
    )
    _refund(a, 1)
    _refund(b, 2)

    item = _get_item(auth_client.get(LIST_URL), order.shopify_order_id)

    assert item["logistics_display"] is None
    assert item["purchase_display"] is None


@pytest.mark.django_db
def test_fully_refunded_item_excluded_from_purchase_display(auth_client):
    """취소된 미발주 품목이 주문 전체를 미발주로 끌어내리지 않는다."""
    order = _make_order()
    ordered = _make_line_item(order, sku="ISBN-ORDERED", quantity=1, purchase_status="unordered")
    _link_purchase_order(ordered)
    cancelled = _make_line_item(
        order, sku="ISBN-CANCELLED", quantity=1, purchase_status="unordered"
    )
    _refund(cancelled, 1)

    res = auth_client.get(LIST_URL)

    assert _get_item(res, order.shopify_order_id)["purchase_display"] == "ordered"


# ---------------------------------------------------------------------------
# 주문상세/주문목록 표시 일원화
#
# 주문상세는 저장 컬럼 Order.status를 그대로 보여줬고, 그 컬럼은
# _recompute_order_aggregates가 호출될 때만 갱신된다. 출고 경로(일반/강제)는
# 그 함수를 호출하지 않으므로 출고를 처리해도 상세 배지는 옛 값에 머문다 —
# 프로덕션 3,693건 중 508건이 목록과 다른 값을 보여주고 있었다.
# 두 화면이 같은 파생 함수를 공유하게 해 구조적으로 어긋날 수 없게 한다.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_detail_logistics_display_matches_list(auth_client):
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-D1", logistics_status="shipped", quantity=2, shipped_quantity=2
    )
    _make_line_item(
        order, sku="ISBN-D2", logistics_status="not_shipped", quantity=2, shipped_quantity=1
    )

    list_value = _get_item(auth_client.get(LIST_URL), order.shopify_order_id)[
        "logistics_display"
    ]
    detail = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert detail.status_code == 200
    assert detail.data["logistics_display"] == list_value == "partial_shipped"
    assert detail.data["purchase_display"] == "unordered"


@pytest.mark.django_db
def test_detail_display_ignores_stale_stored_status(auth_client):
    """저장 컬럼이 낡아 있어도 상세는 LineItem에서 즉석 파생한 값을 보여준다."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-STALE", logistics_status="shipped", quantity=1, shipped_quantity=1
    )
    Order.objects.filter(pk=order.pk).update(status="not_shipped")

    detail = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert detail.data["status"] == "not_shipped"  # 저장 컬럼은 그대로 노출
    assert detail.data["logistics_display"] == "shipped"


@pytest.mark.django_db
def test_detail_display_nets_refunds_like_list(auth_client):
    """상세도 전량 환불 품목을 제외한다 (주문 #37830 형태)."""
    order = _make_order()
    _make_line_item(
        order, sku="ISBN-LIVE", logistics_status="shipped", quantity=1, shipped_quantity=1
    )
    cancelled = _make_line_item(
        order, sku="ISBN-CANCELLED", logistics_status="not_shipped", quantity=1, shipped_quantity=0
    )
    _refund(cancelled, 1)

    detail = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert detail.data["logistics_display"] == "shipped"
