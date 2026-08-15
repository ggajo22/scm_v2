"""SPEC-ORDER-021: 마진 계산에 배송비·한국창고비 반영 (TDD).

T1~T13 map 1:1 to AC-COST-001~013 in `.moai/specs/SPEC-ORDER-021/acceptance.md`.
"""
import re
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import ExchangeRate, LineItem, Order

User = get_user_model()
DETAIL_URL = "/api/orders/{pk}/"
LIST_URL = "/api/orders/"

# AC-COST-009 (b): `orders_line_item` must be matched exactly, not as a
# substring — `LineItemNote.Meta.db_table = "orders_line_item_note"`
# (order/models.py:296-298) is a superstring of it and would otherwise be
# double-counted (audit D1).
LINE_ITEM_TABLE_RE = re.compile(r"orders_line_item(?!_)")
# `orders_exchangerate` (order/models.py:507) is not a substring of any other
# table name in this schema, so plain `in` matching is safe here (AC-COST-009 c).
EXCHANGE_RATE_TABLE = "orders_exchangerate"

# AC-COST-009 (a): total query count for GET /api/orders/{pk}/ must be
# identical regardless of line item count, and pinned to an absolute value
# measured against the correct (memoized) implementation — see
# test_spec_018.py-style precedent (`UNORDERED_ENDPOINT_QUERY_COUNT`), not a
# guess. Measured directly (CaptureQueriesContext) against the
# SPEC-ORDER-021 implementation: 7 queries for both a 1-line-item and a
# 5-line-item order — JWT auth user lookup, the select_related Order query,
# 3 prefetch_related queries (line_items__notes__author, shipping_lines,
# refunds), and exactly 1 memoized ExchangeRate query (AC-COST-009 c).
ORDER_DETAIL_QUERY_COUNT = 7


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec021_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def _make_order(total_price, shopify_order_id, **kwargs):
    return Order.objects.create(
        shopify_order_id=shopify_order_id,
        store_type="gimssine",
        financial_status="paid",
        total_price=Decimal(total_price),
        shopify_created_at=timezone.now(),
        **kwargs,
    )


def _make_line_item(order, shopify_line_item_id, quantity=None, confirmed_price=None, grams=None):
    return LineItem.objects.create(
        order=order,
        shopify_line_item_id=shopify_line_item_id,
        title="테스트 상품",
        quantity=quantity,
        confirmed_price=confirmed_price,
        grams=grams,
    )


@pytest.fixture
def rate_1000(db):
    """1 USD = 1000.00 KRW — shared by T1~T8, T13 (divides evenly)."""
    return ExchangeRate.objects.create(
        effective_date=timezone.now().date(), rate=Decimal("1000.00")
    )


# ---------------------------------------------------------------------------
# T1 (AC-COST-001) — single-SKU, 3-book order Korea-warehouse fee
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t1_single_sku_korea_warehouse_fee(auth_client, rate_1000):
    order = _make_order("100.00", 921001)
    _make_line_item(order, 1, quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["margin_amount"] == "67.75"
    assert res.data["korea_warehouse_cost"] == "2.25"
    assert res.data["shipping_cost"] == "0.00"
    assert res.data["total_weight_grams"] == 0


# ---------------------------------------------------------------------------
# T2 (AC-COST-002) — base fee is per-order, not per-line-item
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t2_base_fee_is_per_order_not_per_line_item(auth_client, rate_1000):
    order = _make_order("100.00", 921002)
    _make_line_item(order, 1, quantity=2, confirmed_price=Decimal("10000.00"), grams=0)
    _make_line_item(order, 2, quantity=1, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    # Must match T1 exactly — a per-line-item base fee bug would diverge here.
    assert res.data["margin_amount"] == "67.75"


# ---------------------------------------------------------------------------
# T3 (AC-COST-003) — weight-based shipping cost + rounding artifact
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t3_weight_based_shipping_cost_and_rounding(auth_client, rate_1000):
    order = _make_order("200.00", 921003)
    _make_line_item(order, 1, quantity=3, confirmed_price=Decimal("10000.00"), grams=500)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 1500
    assert res.data["shipping_cost"] == "8.18"
    assert res.data["korea_warehouse_cost"] == "2.25"
    assert res.data["margin_amount"] == "159.58"
    assert res.data["margin_rate"] == "79.79"


# ---------------------------------------------------------------------------
# T4 (AC-COST-004) — grams=None treated same as grams=0
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t4_grams_none_treated_as_zero(auth_client, rate_1000):
    order = _make_order("50.00", 921004)
    _make_line_item(order, 1, quantity=2, confirmed_price=Decimal("5000.00"), grams=None)
    _make_line_item(order, 2, quantity=1, confirmed_price=Decimal("5000.00"), grams=0)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["margin_amount"] == "32.75"
    assert res.data["total_weight_grams"] == 0
    assert res.data["shipping_cost"] == "0.00"


# ---------------------------------------------------------------------------
# T5 (AC-COST-005) — unconfirmed line items count toward weight/book count
# but not toward confirmed cost
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t5_unconfirmed_line_items_counted_in_weight_and_books_only(auth_client, rate_1000):
    order = _make_order("100.00", 921005)
    _make_line_item(order, 1, quantity=2, confirmed_price=Decimal("10000.00"), grams=300)
    _make_line_item(order, 2, quantity=1, confirmed_price=None, grams=600)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 1200
    assert res.data["margin_amount"] == "71.21"


# ---------------------------------------------------------------------------
# T6 (AC-COST-006) — no ExchangeRate -> all 5 fields present and null
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t6_no_exchange_rate_all_five_fields_null(auth_client, db):
    # No ExchangeRate fixture at all — same line-item shape as T1.
    order = _make_order("100.00", 921006)
    _make_line_item(order, 1, quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    for field in (
        "margin_amount",
        "margin_rate",
        "shipping_cost",
        "korea_warehouse_cost",
        "total_weight_grams",
    ):
        assert field in res.data, f"{field} missing from response"
        assert res.data[field] is None, f"{field} expected None, got {res.data[field]!r}"


# ---------------------------------------------------------------------------
# T7 (AC-COST-007) — no confirmed_price anywhere -> all 5 fields present and
# null, even though weight data exists
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t7_no_confirmed_price_all_five_fields_null(auth_client, rate_1000):
    order = _make_order("100.00", 921007)
    _make_line_item(order, 1, quantity=3, confirmed_price=None, grams=500)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    for field in (
        "margin_amount",
        "margin_rate",
        "shipping_cost",
        "korea_warehouse_cost",
        "total_weight_grams",
    ):
        assert field in res.data, f"{field} missing from response"
        assert res.data[field] is None, f"{field} expected None, got {res.data[field]!r}"


# ---------------------------------------------------------------------------
# T8 (AC-COST-008) — total_book_count == 0 -> korea_warehouse_cost == 0.00
# (no base fee)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t8_zero_book_count_means_zero_korea_warehouse_fee(auth_client, rate_1000):
    order = _make_order("50.00", 921008)
    _make_line_item(order, 1, quantity=None, confirmed_price=Decimal("5000.00"), grams=None)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["korea_warehouse_cost"] == "0.00"
    assert res.data["margin_amount"] == "50.00"


# ---------------------------------------------------------------------------
# T9 (AC-COST-009) — query-count invariant
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t9_query_count_invariant_across_line_item_count(auth_client, rate_1000):
    warmup_order = _make_order("10.00", 921100)
    _make_line_item(warmup_order, 1, quantity=1, confirmed_price=Decimal("1000.00"), grams=100)

    order_x = _make_order("100.00", 921101)
    _make_line_item(order_x, 1, quantity=1, confirmed_price=Decimal("1000.00"), grams=100)

    order_y = _make_order("500.00", 921102)
    for i in range(5):
        _make_line_item(
            order_y, i + 1, quantity=1, confirmed_price=Decimal("1000.00"), grams=100
        )

    # Warm-up request outside the measurement window (test_spec_018.py:490-492
    # precedent) so a first-request-only query does not skew X vs Y asymmetrically.
    auth_client.get(DETAIL_URL.format(pk=warmup_order.pk))

    with CaptureQueriesContext(connection) as ctx_x:
        res_x = auth_client.get(DETAIL_URL.format(pk=order_x.pk))
    with CaptureQueriesContext(connection) as ctx_y:
        res_y = auth_client.get(DETAIL_URL.format(pk=order_y.pk))

    assert res_x.status_code == 200
    assert res_y.status_code == 200

    queries_x = [q["sql"] for q in ctx_x.captured_queries]
    queries_y = [q["sql"] for q in ctx_y.captured_queries]

    # (a) absolute, identical query count regardless of line item count
    assert len(queries_x) == len(queries_y) == ORDER_DETAIL_QUERY_COUNT, (
        f"query count must be a fixed constant: X={len(queries_x)}, "
        f"Y={len(queries_y)}, expected={ORDER_DETAIL_QUERY_COUNT}"
    )

    # (b) exactly one query touches `orders_line_item` (exact match, not the
    # `orders_line_item_note` superstring)
    for label, queries in (("X", queries_x), ("Y", queries_y)):
        line_item_hits = [sql for sql in queries if LINE_ITEM_TABLE_RE.search(sql)]
        assert len(line_item_hits) == 1, (
            f"{label}: expected exactly 1 orders_line_item query, got "
            f"{len(line_item_hits)}: {line_item_hits}"
        )

    # (c) exactly one query touches `orders_exchangerate` (memoization)
    for label, queries in (("X", queries_x), ("Y", queries_y)):
        rate_hits = [sql for sql in queries if EXCHANGE_RATE_TABLE in sql]
        assert len(rate_hits) == 1, (
            f"{label}: expected exactly 1 orders_exchangerate query, got "
            f"{len(rate_hits)}: {rate_hits}"
        )


# ---------------------------------------------------------------------------
# T10 (AC-COST-010) — list endpoint never exposes the 3 new fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t10_list_endpoint_does_not_expose_cost_breakdown(auth_client, rate_1000):
    order = _make_order("100.00", 921010)
    _make_line_item(order, 1, quantity=3, confirmed_price=Decimal("10000.00"), grams=500)

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    items = res.data.get("results", res.data) if isinstance(res.data, dict) else res.data
    assert len(items) >= 1
    for item in items:
        assert "shipping_cost" not in item
        assert "korea_warehouse_cost" not in item
        assert "total_weight_grams" not in item


# ---------------------------------------------------------------------------
# T12 (AC-COST-012) — korea_warehouse_usd conversion uses the real exchange
# rate, not a hardcoded /1000 constant
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t12_korea_warehouse_conversion_uses_real_exchange_rate(auth_client, db):
    ExchangeRate.objects.create(
        effective_date=timezone.now().date(), rate=Decimal("1250.00")
    )
    order = _make_order("100.00", 921012)
    _make_line_item(order, 1, quantity=3, confirmed_price=Decimal("12500.00"), grams=0)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["korea_warehouse_cost"] == "1.80"
    assert res.data["margin_amount"] == "68.20"


# ---------------------------------------------------------------------------
# T13 (AC-COST-013) — ROUND_HALF_UP distinguished from ROUND_HALF_EVEN
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_t13_round_half_up_distinguished_from_round_half_even(auth_client, rate_1000):
    order = _make_order("50.00", 921013)
    _make_line_item(order, 1, quantity=1, confirmed_price=Decimal("10000.00"), grams=500)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["shipping_cost"] == "2.73"
