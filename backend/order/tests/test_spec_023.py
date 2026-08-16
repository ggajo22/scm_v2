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

from order.models import Customer, ExchangeRate, LineItem, Order

User = get_user_model()
LIST_URL = "/api/orders/"
DETAIL_URL = "/api/orders/{pk}/"

EXCHANGE_RATE_TABLE = "orders_exchangerate"

# AC-OLIST-021: baseline (JWT user lookup 1 + pagination COUNT 1 + main
# SELECT 1 + prefetch_related x3: refunds/line_items/customer) re-measured
# in this session (M0) as 6, matching spec.md REQ-OLIST-022a. +1 batched
# ExchangeRate query (REQ-OLIST-019) = 7.
TOTAL_QUERY_COUNT = 7

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
def test_ac014_any_unordered_triggers_unordered(auth_client):
    order = _make_order()
    _make_line_item(order, sku="ISBN-A", purchase_status="unordered", quantity=1)
    _make_line_item(order, sku="ISBN-B", purchase_status="in_stock", quantity=1)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert item["purchase_display"] == "unordered"


@pytest.mark.django_db
def test_ac015_none_unordered_yields_ordered(auth_client):
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
def test_ac021_total_query_count_exact_seven_and_page_size_invariant(auth_client):
    """AC-OLIST-021 [HARD]: absolute constant 7, identical for a 1-order page
    and a 5-order page (customer-connected trackable orders, per M0/REQ-022a)."""
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
