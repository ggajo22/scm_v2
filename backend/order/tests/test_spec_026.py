"""SPEC-ORDER-026: 비용/마진 계산의 환불 순액화 (TDD).

Test functions map to AC-NET-001~AC-NET-016 in
`.moai/specs/SPEC-ORDER-026/acceptance.md` — 17 acceptance criteria across 21
tests (AC-NET-003/004/006a/006b each split into 2). See that document for the
full Given/When/Then narrative and the mutation each fixture discriminates.

[HARD] Five of these are invariant-PRESERVING criteria that pass on unmodified
code by design: AC-NET-009, 010, 013, 014, 016. Their passing is not evidence
of a broken fixture. AC-NET-009/010 are the only defence against a
+1-query-per-serialized-order regression (up to +50 per list page).

[HARD] Fixture conventions (acceptance.md §0.1):
  1. `shopify_line_item_id >= 17_000_000_000_000` — `Refund.line_item_id` joins
     to `LineItem.shopify_line_item_id`, NOT to `LineItem.pk`. Small ids can
     collide with autoincrement pks and let a wrong-join-key mutation pass.
  2. The refund helper MUST set `subtotal`/`total_tax` — the borrowed helper in
     test_spec_023.py:866-872 does not, and without them the revenue side of
     the netting is never exercised.
  3. All money assertions compare strings — the 7 getters return strings.
  4. `margin_rate` null assertions use `is None`, never `.get()`.

Helper note (plan.md R17): all three borrowed helpers needed extending, so this
suite defines its own local copies rather than mutating the originals —
`_make_order` (test_spec_021.py:74 calls `Decimal(total_price)` unconditionally
and cannot express `total_price=None`), `_make_line_item` (no `purchase_status`
argument), `_refund` (no `subtotal`/`total_tax` arguments).
"""
from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

import order.serializers as order_serializers
from order.models import Customer, ExchangeRate, LineItem, Order, Refund

User = get_user_model()
DETAIL_URL = "/api/orders/{pk}/"
LIST_URL = "/api/orders/"

# AC-NET-009 (c) / AC-NET-010 (b): `orders_exchangerate` (models.py:516) and
# `orders_refund` (models.py:335) are not substrings of any other table name in
# this schema, so plain `in` matching is safe (research.md §4.1). Contrast
# `orders_line_item`, a prefix of `orders_line_item_note`, which forced a regex
# in test_spec_021.py:30.
EXCHANGE_RATE_TABLE = "orders_exchangerate"
REFUND_TABLE = "orders_refund"

# AC-NET-009 (a): absolute constant decided by the SPEC (REQ-NET-031), not
# re-pinned from a measurement. Identical to `ORDER_DETAIL_QUERY_COUNT` in
# test_spec_021.py:48, whose unmodified passing is part of this SPEC's DoD.
# If the measurement is not 8, that is a REQ-NET-031 violation to report, not a
# new baseline to record.
ORDER_DETAIL_QUERY_COUNT = 8

# AC-NET-010 (a): identical to `TOTAL_QUERY_COUNT` in test_spec_023.py:34,
# pinned by AC-OLIST-021's [HARD] guarantee (REQ-OLIST-021).
ORDER_LIST_QUERY_COUNT = 8

# AC-NET-016: the 7 cost fields whose single computation point this SPEC edits.
COST_FIELDS = (
    "margin_amount",
    "margin_rate",
    "shipping_cost",
    "korea_warehouse_cost",
    "total_weight_grams",
    "confirmed_cost",
    "total_cost",
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec026_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


_next_shopify_order_id = iter(range(926000, 927000))
_next_shopify_refund_id = iter(range(9260000, 9269999))
_next_shopify_customer_id = iter(range(9600000, 9600999))
# [HARD] acceptance.md §0.1-1: stay above 17_000_000_000_000 so a
# LineItem.pk-based join cannot pass by coincidence (mutation M8).
_next_shopify_line_item_id = iter(range(17_851_226_300_000, 17_851_226_399_999))

_UNSET = object()


def _make_order(total_price, shopify_order_id=None, **kwargs):
    """test_spec_021.py:69-77 shape, except `total_price=None` is expressible.

    plan.md R17 / audit N9: the original calls `Decimal(total_price)`
    unconditionally, which raises TypeError on None — and AC-NET-006b(b)
    requires `Order.total_price IS NULL` (the column is nullable,
    models.py:63).
    """
    if shopify_order_id is None:
        shopify_order_id = next(_next_shopify_order_id)
    kwargs.setdefault("store_type", "gimssine")
    kwargs.setdefault("financial_status", "paid")
    kwargs.setdefault("shopify_created_at", timezone.now())
    return Order.objects.create(
        shopify_order_id=shopify_order_id,
        total_price=Decimal(total_price) if total_price is not None else None,
        **kwargs,
    )


def _make_line_item(
    order,
    shopify_line_item_id=None,
    quantity=None,
    confirmed_price=None,
    grams=None,
    **kwargs,
):
    """test_spec_021.py:80-88 shape plus **kwargs, so AC-NET-013 can set
    `purchase_status` (the original helper has no such argument)."""
    if shopify_line_item_id is None:
        shopify_line_item_id = next(_next_shopify_line_item_id)
    return LineItem.objects.create(
        order=order,
        shopify_line_item_id=shopify_line_item_id,
        title="테스트 상품",
        quantity=quantity,
        confirmed_price=confirmed_price,
        grams=grams,
        **kwargs,
    )


def _refund(line_item, quantity, subtotal=None, total_tax=None, line_item_id=_UNSET):
    """test_spec_023.py:866-872 shape plus `subtotal`/`total_tax`/`line_item_id`.

    acceptance.md §0.1-2: the original sets neither money column, so reusing it
    verbatim would leave the revenue side of the netting completely unverified.
    `line_item_id` is overridable so AC-NET-007 can store a NULL join key and
    AC-NET-008 a non-matching one.
    """
    return Refund.objects.create(
        order=line_item.order,
        shopify_refund_id=next(_next_shopify_refund_id),
        line_item_id=(
            line_item.shopify_line_item_id if line_item_id is _UNSET else line_item_id
        ),
        quantity=quantity,
        subtotal=subtotal,
        total_tax=total_tax,
    )


@pytest.fixture
def rate_1000(db):
    """1 USD = 1000.00 KRW — divides evenly, shared by most criteria."""
    return ExchangeRate.objects.create(
        effective_date=timezone.now().date(), rate=Decimal("1000.00")
    )


def _get_item(res, shopify_order_id):
    for item in res.data["results"]:
        if item["shopify_order_id"] == shopify_order_id:
            return item
    raise AssertionError(f"order {shopify_order_id} not found in results")


def _net_paid(order):
    """The frontend's 최종 결제 금액 formula, recomputed outside the backend
    (OrderDetailPage.tsx:159-163)."""
    return Decimal(str(order.total_price or "0")) - sum(
        (r.subtotal or Decimal("0")) + (r.total_tax or Decimal("0"))
        for r in order.refunds.all()
    )


# ---------------------------------------------------------------------------
# Shared fixture builders (AC-NET-001 and AC-NET-002 shapes are reused by
# AC-NET-003, AC-NET-011 and AC-NET-016)
# ---------------------------------------------------------------------------


def _build_ac001_order():
    """Order #37454's production AGGREGATES (gross 4453g / 74100 KRW, net
    3418g / 49500 KRW, refunds 37.28 USD, total_price 116.04, rate 1427.11).
    Per-line-item values are synthesised — the investigation session captured
    only the aggregates (acceptance.md AC-NET-001 note, research.md §5).
    Check: 900+850+834+834 = 3418, +535+500 = 4453;
           13000+12500+12000+12000 = 49500, +16000+8600 = 74100.
    """
    ExchangeRate.objects.create(
        effective_date=timezone.now().date(), rate=Decimal("1427.11")
    )
    order = _make_order("116.04")
    for grams, price in (
        (900, "13000.00"),
        (850, "12500.00"),
        (834, "12000.00"),
        (834, "12000.00"),
    ):
        _make_line_item(order, quantity=1, confirmed_price=Decimal(price), grams=grams)
    r1 = _make_line_item(
        order, quantity=1, confirmed_price=Decimal("16000.00"), grams=535
    )
    r2 = _make_line_item(
        order, quantity=1, confirmed_price=Decimal("8600.00"), grams=500
    )
    _refund(r1, 1, subtotal=Decimal("24.00"), total_tax=Decimal("0.00"))
    _refund(r2, 1, subtotal=Decimal("13.28"), total_tax=Decimal("0.00"))
    return order


AC001_EXPECTED = {
    "total_weight_grams": 3418,
    "confirmed_cost": "34.69",
    "shipping_cost": "18.63",
    "korea_warehouse_cost": "1.93",
    "total_cost": "55.24",
    "margin_amount": "23.52",
    "margin_rate": "29.86",
}


def _build_ac002_order():
    """A genuinely PARTIAL refund: quantity 3, one unit refunded -> net 2.

    [HARD] This shape is the sole discriminator for mutation M4 (copying the
    boolean include/exclude filter at serializers.py:186-191, under which a
    surviving line item keeps its FULL quantity). #37454 cannot catch M4 — every
    refunded line there is refunded in full, so both forms agree.
    """
    order = _make_order("100.00")
    line_item = _make_line_item(
        order,
        shopify_line_item_id=17_851_226_325_297,
        quantity=3,
        confirmed_price=Decimal("10000.00"),
        grams=500,
    )
    _refund(line_item, 1, subtotal=Decimal("20.00"), total_tax=Decimal("0.00"))
    return order


AC002_EXPECTED = {
    "total_weight_grams": 1000,
    "confirmed_cost": "20.00",
    "shipping_cost": "5.45",
    "korea_warehouse_cost": "1.75",
    "total_cost": "27.20",
    "margin_amount": "52.80",
    "margin_rate": "66.00",
}


# ---------------------------------------------------------------------------
# AC-NET-001 — production aggregate reproduction: order #37454
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_001_production_aggregate_reproduction(auth_client):
    """AC-NET-001 (M1, M2, M3): 49500/1427.11 = 34.685483 · 5.45x3.418 =
    18.62810 · (1250+500x3)/1427.11 = 1.926971 · sum 55.240554 · revenue
    116.04-37.28 = 78.76 · margin 23.519446 · rate 29.862171."""
    order = _build_ac001_order()

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    for field, expected in AC001_EXPECTED.items():
        assert res.data[field] == expected, field


# ---------------------------------------------------------------------------
# AC-NET-002 — [핵심] true partial refund: quantity 3, 1 refunded -> net 2
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_002_partial_refund_reduces_quantity_proportionally(auth_client, rate_1000):
    """AC-NET-002 (M1, M2, M3, M4-sole, M8): net quantity 2 -> 1000g, 20000 KRW.

    `total_weight_grams == 1000` is the single discriminator: M3, M4 and M8 all
    surface as the one observable fact "a partial refund did not reduce the
    quantity" and all return 1500.
    """
    order = _build_ac002_order()

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    for field, expected in AC002_EXPECTED.items():
        assert res.data[field] == expected, field


# ---------------------------------------------------------------------------
# AC-NET-003 — backend margin reconciles with the screen's 최종 결제 금액
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "builder,needs_rate_1000",
    [
        pytest.param(_build_ac001_order, False, id="ac001-37454"),
        pytest.param(_build_ac002_order, True, id="ac002-partial"),
    ],
)
def test_ac_net_003_margin_reconciles_with_net_paid(
    auth_client, db, builder, needs_rate_1000
):
    """AC-NET-003 (M2): margin_amount + total_cost == net paid amount.

    Both fixtures were selected to reconcile with residual 0, so exact equality
    is asserted. The general case may differ by up to 0.01 USD because
    margin_amount and total_cost are each quantized once (design decision B) —
    AC-NET-005 and AC-NET-015 pin that residual directly.

    This does NOT discriminate M3 (revenue-only netting satisfies the identity
    trivially); M3 is caught by AC-NET-001/002.
    """
    if needs_rate_1000:
        ExchangeRate.objects.create(
            effective_date=timezone.now().date(), rate=Decimal("1000.00")
        )
    order = builder()

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    net_paid = _net_paid(order)
    assert (
        Decimal(res.data["margin_amount"]) + Decimal(res.data["total_cost"]) == net_paid
    )


# ---------------------------------------------------------------------------
# AC-NET-004 — every line fully refunded: the decided values of all 7 fields
# ---------------------------------------------------------------------------


def _build_ac004_order():
    order = _make_order("30.00")
    line_item = _make_line_item(
        order, quantity=2, confirmed_price=Decimal("10000.00"), grams=500
    )
    _refund(line_item, 2, subtotal=Decimal("30.00"), total_tax=Decimal("0.00"))
    return order


@pytest.mark.django_db
def test_ac_net_004a_fully_refunded_order_detail(auth_client, rate_1000):
    """AC-NET-004 (a) (M1, M3, zero-book-count branch): net quantity 0 leaves
    the 7 fields at "0.00"/0 — NOT null, because `has_any_confirmed` is
    evaluated before netting (REQ-NET-024) — and the book-count-0 branch
    (serializers.py:54-59) keeps the Korea base fee off."""
    order = _build_ac004_order()

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 0
    assert res.data["confirmed_cost"] == "0.00"
    assert res.data["shipping_cost"] == "0.00"
    assert res.data["korea_warehouse_cost"] == "0.00"
    assert res.data["total_cost"] == "0.00"
    assert res.data["margin_amount"] == "0.00"
    assert "margin_rate" in res.data
    assert res.data["margin_rate"] is None


@pytest.mark.django_db
def test_ac_net_004b_fully_refunded_order_list(auth_client, rate_1000):
    """AC-NET-004 (b): the zero-revenue gate has a SECOND implementation site
    on the list path (serializers.py:283-284), a different code block from the
    detail gate (:570-571). Deleting it passes (a) while raising
    ZeroDivisionError / decimal.InvalidOperation here."""
    order = _build_ac004_order()

    res = auth_client.get(LIST_URL)

    assert res.status_code == 200
    item = _get_item(res, order.shopify_order_id)
    assert "margin_rate" in item
    assert item["margin_rate"] is None


# ---------------------------------------------------------------------------
# AC-NET-005 — `has_any_confirmed` is evaluated BEFORE netting
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_005_has_any_confirmed_evaluated_before_netting(auth_client, rate_1000):
    """AC-NET-005 (post-netting-gate mutation, M2): the only line carrying a
    confirmed_price is fully refunded, yet the 7 fields stay non-null.

    5.45x0.3 = 1.635 -> "1.64" · (1250+500x0)/1000 = 1.25 · sum 2.885 -> "2.89"
    · revenue 50.00-20.00 = 30.00 · margin 27.115 -> "27.12" · rate 90.38333.
    """
    order = _make_order("50.00")
    a = _make_line_item(order, quantity=1, confirmed_price=Decimal("10000.00"), grams=500)
    _make_line_item(order, quantity=1, confirmed_price=None, grams=300)
    _refund(a, 1, subtotal=Decimal("20.00"), total_tax=Decimal("0.00"))

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 300
    assert res.data["confirmed_cost"] == "0.00"
    assert res.data["shipping_cost"] == "1.64"
    assert res.data["korea_warehouse_cost"] == "1.25"
    assert res.data["total_cost"] == "2.89"
    assert res.data["margin_amount"] == "27.12"
    assert res.data["margin_rate"] == "90.38"

    # Characterization: this fixture's reconciliation residual is exactly +0.01
    # (27.12 + 2.89 = 30.01 vs net paid 30.00), because margin_amount and
    # total_cost are each quantized once. Pinning it proves the residual is real
    # (so AC-NET-003 must not demand exact equality in general) and that it stays
    # within REQ-NET-043's bound. Under M2 the net paid would be gross 50.00 and
    # the residual 20.01, breaking both lines.
    net_paid = Decimal("30.00")
    residual = (
        Decimal(res.data["margin_amount"]) + Decimal(res.data["total_cost"])
    ) - net_paid
    assert residual == Decimal("0.01")
    assert abs(residual) <= Decimal("0.01")


# ---------------------------------------------------------------------------
# AC-NET-006a — over-refund: quantity-side floor max(..., 0)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "line_item_quantity,refund_quantity",
    [
        pytest.param(1, 2, id="refund-exceeds-quantity"),
        pytest.param(None, 1, id="null-quantity-with-refund"),
    ],
)
def test_ac_net_006a_quantity_floor(
    auth_client, rate_1000, line_item_quantity, refund_quantity
):
    """AC-NET-006a (M5, quantity side): both cases net to max(-1, 0) = 0.

    Without the floor both return total_weight_grams -500, confirmed_cost
    "-10.00", and — because book count -1 does not satisfy the `== 0` branch —
    a Korea warehouse BASE FEE of "1.25" charged on an order with no books.
    """
    order = _make_order("50.00")
    line_item = _make_line_item(
        order,
        quantity=line_item_quantity,
        confirmed_price=Decimal("10000.00"),
        grams=500,
    )
    _refund(
        line_item,
        refund_quantity,
        subtotal=Decimal("30.00"),
        total_tax=Decimal("0.00"),
    )

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 0
    assert res.data["confirmed_cost"] == "0.00"
    assert res.data["shipping_cost"] == "0.00"
    assert res.data["korea_warehouse_cost"] == "0.00"
    assert res.data["total_cost"] == "0.00"
    assert res.data["margin_amount"] == "20.00"
    assert res.data["margin_rate"] == "100.00"


# ---------------------------------------------------------------------------
# AC-NET-006b — over-refund: revenue-side floor max(..., 0)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "total_price",
    [
        pytest.param("10.00", id="refund-exceeds-total-price"),
        pytest.param(None, id="null-total-price-with-refund"),
    ],
)
def test_ac_net_006b_revenue_floor(auth_client, rate_1000, total_price):
    """AC-NET-006b (M5, revenue side): both cases floor net revenue at 0.

    Without the floor net revenue goes negative and, since cost is 0, negative
    divided by negative renders a +100% margin rate on a fully-and-then-some
    refunded order. `total_price IS NULL` (models.py:63) is the more exposed
    shape: `0 - refund` is negative for ANY refund amount.
    """
    order = _make_order(total_price)
    line_item = _make_line_item(
        order, quantity=1, confirmed_price=Decimal("5000.00"), grams=0
    )
    _refund(line_item, 1, subtotal=Decimal("15.00"), total_tax=Decimal("0.00"))

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 0
    assert res.data["total_cost"] == "0.00"
    assert res.data["margin_amount"] == "0.00"
    assert "margin_rate" in res.data
    assert res.data["margin_rate"] is None


# ---------------------------------------------------------------------------
# AC-NET-007 — NULL durability: line_item_id / quantity / subtotal / total_tax
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_007_null_durability(auth_client, rate_1000):
    """AC-NET-007 (NULL guard deletion -> 500; revenue-side "matched only").

    R1 has a NULL join key so its quantity 5 reduces nothing; R2's quantity is
    NULL -> 0; only R3 zeroes B. Net confirmed 3x10000 = 30000 KRW. Revenue
    100.00 - (3.00+0 + 0+0 + 8.00+0.80) = 88.20 — every refund row counts on the
    revenue side, matched or not.
    """
    order = _make_order("100.00")
    a = _make_line_item(order, quantity=3, confirmed_price=Decimal("10000.00"), grams=0)
    b = _make_line_item(order, quantity=1, confirmed_price=Decimal("10000.00"), grams=0)
    _refund(a, 5, subtotal=Decimal("3.00"), total_tax=None, line_item_id=None)
    _refund(a, None, subtotal=None, total_tax=None)
    _refund(b, 1, subtotal=Decimal("8.00"), total_tax=Decimal("0.80"))

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 0
    assert res.data["confirmed_cost"] == "30.00"
    assert res.data["korea_warehouse_cost"] == "2.25"
    assert res.data["total_cost"] == "32.25"
    assert res.data["margin_amount"] == "55.95"
    assert res.data["margin_rate"] == "63.44"
    assert (
        Decimal(res.data["margin_amount"]) + Decimal(res.data["total_cost"])
        == Decimal("88.20")
    )


# ---------------------------------------------------------------------------
# AC-NET-008 — an unmatched refund reduces revenue only, never quantity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_008_unmatched_refund_reduces_revenue_only(auth_client, rate_1000):
    """AC-NET-008 (revenue-side "matched only" mutation): mirrors what the
    frontend already does — OrderDetailPage.tsx:159-162 applies no filter and
    renders unmatched rows separately at :491-504."""
    order = _make_order("100.00")
    line_item = _make_line_item(
        order,
        shopify_line_item_id=17_851_226_358_065,
        quantity=2,
        confirmed_price=Decimal("10000.00"),
        grams=0,
    )
    _refund(
        line_item,
        2,
        subtotal=Decimal("25.00"),
        total_tax=Decimal("0.00"),
        line_item_id=17_999_999_999_999,
    )

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["confirmed_cost"] == "20.00"
    assert res.data["korea_warehouse_cost"] == "1.75"
    assert res.data["total_cost"] == "21.75"
    assert res.data["margin_amount"] == "53.25"
    assert res.data["margin_rate"] == "71.00"


# ---------------------------------------------------------------------------
# AC-NET-009 — [MUST-PASS] detail API query-count invariant
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_009_detail_query_count_invariant(auth_client, rate_1000):
    """AC-NET-009 [MUST-PASS] (M6, detail path).

    [HARD] Passing on unmodified code is CORRECT — this is an invariant-
    PRESERVING criterion. Do not "fix" the fixture because it passes: together
    with AC-NET-010 it is the only defence against R3 (one refund query per
    serialized order, ~130ms each against this remote RDS instance).

    Netting must read `obj.refunds.all()` from the prefetch cache
    (views.py:53-59). `Refund.objects.filter(...)`, `obj.refunds.filter(...)`,
    or the Subquery/OuterRef pattern at purchase_order_views.py:334-342 all
    break (b) — and (a) too on order Y.
    """
    warmup_order = _make_order("10.00")
    warmup_item = _make_line_item(
        warmup_order, quantity=1, confirmed_price=Decimal("1000.00"), grams=100
    )
    _refund(warmup_item, 1, subtotal=Decimal("1.00"), total_tax=Decimal("0.00"))

    order_x = _make_order("100.00")
    item_x = _make_line_item(
        order_x, quantity=2, confirmed_price=Decimal("1000.00"), grams=100
    )
    _refund(item_x, 1, subtotal=Decimal("10.00"), total_tax=Decimal("0.00"))

    order_y = _make_order("500.00")
    for _ in range(5):
        item_y = _make_line_item(
            order_y, quantity=2, confirmed_price=Decimal("1000.00"), grams=100
        )
        _refund(item_y, 1, subtotal=Decimal("10.00"), total_tax=Decimal("0.00"))

    # Warm-up outside the measurement window (test_spec_021.py:281-283).
    auth_client.get(DETAIL_URL.format(pk=warmup_order.pk))

    with CaptureQueriesContext(connection) as ctx_x:
        res_x = auth_client.get(DETAIL_URL.format(pk=order_x.pk))
    with CaptureQueriesContext(connection) as ctx_y:
        res_y = auth_client.get(DETAIL_URL.format(pk=order_y.pk))

    assert res_x.status_code == 200
    assert res_y.status_code == 200

    queries_x = [q["sql"] for q in ctx_x.captured_queries]
    queries_y = [q["sql"] for q in ctx_y.captured_queries]

    # (a) absolute, identical count regardless of line item / refund count
    assert len(queries_x) == len(queries_y) == ORDER_DETAIL_QUERY_COUNT, (
        f"query count must be a fixed constant: X={len(queries_x)}, "
        f"Y={len(queries_y)}, expected={ORDER_DETAIL_QUERY_COUNT}"
    )

    # (b) exactly one query touches `orders_refund`
    for label, queries in (("X", queries_x), ("Y", queries_y)):
        refund_hits = [sql for sql in queries if REFUND_TABLE in sql]
        assert len(refund_hits) == 1, (
            f"{label}: expected exactly 1 orders_refund query, got "
            f"{len(refund_hits)}: {refund_hits}"
        )

    # (c) exactly one query touches `orders_exchangerate` (AC-COST-009 c)
    for label, queries in (("X", queries_x), ("Y", queries_y)):
        rate_hits = [sql for sql in queries if EXCHANGE_RATE_TABLE in sql]
        assert len(rate_hits) == 1, (
            f"{label}: expected exactly 1 orders_exchangerate query, got "
            f"{len(rate_hits)}: {rate_hits}"
        )


# ---------------------------------------------------------------------------
# AC-NET-010 — [MUST-PASS] list API query-count invariant (page-size agnostic)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_010_list_query_count_invariant(auth_client, rate_1000):
    """AC-NET-010 [MUST-PASS] (M6, list path — the highest-value target).

    [HARD] Passing on unmodified code is CORRECT (invariant preservation).
    `OrderPagination.page_size = 50` (views.py:159-160), so a per-order refund
    query costs up to +50 queries per page (~+6.5s). This keeps SPEC-ORDER-023
    REQ-OLIST-021's [HARD] guarantee intact.
    """
    solo_customer = Customer.objects.create(
        shopify_customer_id=next(_next_shopify_customer_id)
    )
    order_solo = _make_order("100.00", store_type="gimssine", customer=solo_customer)
    item_solo = _make_line_item(
        order_solo, quantity=2, confirmed_price=Decimal("1000.00"), grams=0
    )
    _refund(item_solo, 1, subtotal=Decimal("10.00"), total_tax=Decimal("0.00"))

    for _ in range(4):
        customer = Customer.objects.create(
            shopify_customer_id=next(_next_shopify_customer_id)
        )
        other = _make_order("100.00", store_type="etoile", customer=customer)
        other_item = _make_line_item(
            other, quantity=2, confirmed_price=Decimal("1000.00"), grams=0
        )
        _refund(other_item, 1, subtotal=Decimal("10.00"), total_tax=Decimal("0.00"))

    # warm-up (test_spec_023.py:667-668)
    auth_client.get(LIST_URL, {"store_type": "gimssine"})

    with CaptureQueriesContext(connection) as ctx_one:
        res_one = auth_client.get(LIST_URL, {"store_type": "gimssine"})
    with CaptureQueriesContext(connection) as ctx_five:
        res_five = auth_client.get(LIST_URL)

    assert res_one.status_code == 200
    assert res_five.status_code == 200
    assert res_one.data["count"] == 1
    assert res_five.data["count"] == 5

    # (a) identical total, independent of page size
    assert len(ctx_one.captured_queries) == ORDER_LIST_QUERY_COUNT
    assert len(ctx_five.captured_queries) == ORDER_LIST_QUERY_COUNT

    # (b) exactly one query touches `orders_refund` in each
    for label, ctx in (("one", ctx_one), ("five", ctx_five)):
        refund_hits = [
            q["sql"] for q in ctx.captured_queries if REFUND_TABLE in q["sql"]
        ]
        assert len(refund_hits) == 1, (
            f"{label}: expected exactly 1 orders_refund query, got "
            f"{len(refund_hits)}: {refund_hits}"
        )


# ---------------------------------------------------------------------------
# AC-NET-011 — the list 마진율 and the detail 마진율 agree
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_011_list_and_detail_margin_rate_agree(auth_client):
    """AC-NET-011 (M9): equality alone is insufficient — two gross values are
    also equal — so the absolute "29.86" is asserted alongside it. Putting the
    netting in either caller instead of the shared
    `_compute_cost_breakdown_for_rate` splits the two surfaces."""
    order = _build_ac001_order()

    res_detail = auth_client.get(DETAIL_URL.format(pk=order.pk))
    res_list = auth_client.get(LIST_URL)

    assert res_detail.status_code == 200
    assert res_list.status_code == 200
    item = _get_item(res_list, order.shopify_order_id)

    assert res_detail.data["margin_rate"] == "29.86"
    assert item["margin_rate"] == "29.86"
    assert res_detail.data["margin_rate"] == item["margin_rate"]


# ---------------------------------------------------------------------------
# AC-NET-012 — no intermediate rounding
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_012_no_intermediate_rounding(auth_client, rate_1000):
    """AC-NET-012 (M7-sole): net confirmed 10005 KRW -> 10.005, the only
    fixture whose net confirmed amount ends in a 5, so pre-rounding is
    observable only here (T15's rounding trap plus a partial refund).

    total_cost quantizes 10.005+2.725+1.25 = 13.980 exactly once (design
    decision B, get_total_cost docstring). Rounding the terms first gives 13.99.
    """
    order = _make_order("100.00")
    line_item = _make_line_item(
        order, quantity=2, confirmed_price=Decimal("10005.00"), grams=500
    )
    _refund(line_item, 1, subtotal=Decimal("10.00"), total_tax=Decimal("0.00"))

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 500
    assert res.data["confirmed_cost"] == "10.01"
    assert res.data["shipping_cost"] == "2.73"
    assert res.data["korea_warehouse_cost"] == "1.25"
    assert res.data["total_cost"] == "13.98"
    assert res.data["margin_amount"] == "76.02"
    assert res.data["margin_rate"] == "84.47"

    naive_sum = (
        Decimal(res.data["confirmed_cost"])
        + Decimal(res.data["shipping_cost"])
        + Decimal(res.data["korea_warehouse_cost"])
    )
    assert naive_sum == Decimal("13.99")
    assert res.data["total_cost"] == "13.98"
    assert Decimal(res.data["total_cost"]) != naive_sum
    assert (
        Decimal(res.data["margin_amount"]) + Decimal(res.data["total_cost"])
        == Decimal("90.00")
    )


# ---------------------------------------------------------------------------
# AC-NET-013 — `purchase_status` is not a netting signal (Exclusions 1)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_013_purchase_status_is_not_a_netting_signal(auth_client, rate_1000):
    """AC-NET-013 (out-of-scope mutation).

    [HARD] Passing on unmodified code is CORRECT — this pins a NON-goal.
    `purchase_status="order_cancelled"` rows carry no Refund, so their revenue
    never drops; excluding them from cost only would overstate margin in the
    opposite direction. Only `Refund` moves both sides symmetrically.
    """
    order = _make_order("100.00")
    _make_line_item(
        order,
        quantity=3,
        confirmed_price=Decimal("10000.00"),
        grams=0,
        purchase_status="order_cancelled",
    )

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["confirmed_cost"] == "30.00"
    assert res.data["korea_warehouse_cost"] == "2.25"
    assert res.data["total_cost"] == "32.25"
    assert res.data["margin_amount"] == "67.75"
    assert res.data["margin_rate"] == "67.75"


# ---------------------------------------------------------------------------
# AC-NET-014 — orders without refunds are byte-for-byte unchanged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_014_order_without_refunds_unchanged(auth_client, rate_1000):
    """AC-NET-014 (constant/formula mutations).

    [HARD] Passing on unmodified code is CORRECT — backward compatibility.
    Existing basis: margin_amount/korea_warehouse_cost/shipping_cost/
    total_weight_grams from T1 (test_spec_021.py:112-115), confirmed_cost from
    T14 (:385-395). total_cost and margin_rate have no prior assertion on this
    fixture — this criterion pins them for the first time.
    """
    order = _make_order("100.00")
    _make_line_item(order, quantity=3, confirmed_price=Decimal("10000.00"), grams=0)

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["margin_amount"] == "67.75"
    assert res.data["korea_warehouse_cost"] == "2.25"
    assert res.data["shipping_cost"] == "0.00"
    assert res.data["total_weight_grams"] == 0
    assert res.data["confirmed_cost"] == "30.00"
    assert res.data["total_cost"] == "32.25"
    assert res.data["margin_rate"] == "67.75"


# ---------------------------------------------------------------------------
# AC-NET-015 — [핵심] two refund rows on the SAME line item: sum, not overwrite
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_015_two_refunds_on_same_line_item_accumulate(auth_client, rate_1000):
    """AC-NET-015 (M10-sole, M1): refunded quantity 1+1 = 2 -> net max(3-2,0)=1.

    [HARD] The two rows point at the SAME shopify_line_item_id with DIFFERENT
    shopify_refund_ids — exactly the shape `unique_together = ("order",
    "shopify_refund_id", "line_item_id")` (models.py:342) permits, and exactly
    the shape production split refunds take. If they ever point at different
    line items this criterion stops discriminating M10 entirely.

    Under M10 (`refunded_qty[id] = qty` instead of `+=`) the total refunded
    quantity reads 1, not 2, so net quantity is 2 and six of the seven fields
    diverge. The revenue side uses a separate accumulator and is unaffected, so
    net revenue stays 80.00 either way.

    10000/1000 = 10.00 · 5.45x0.5 = 2.725 -> "2.73" · 1250/1000 = 1.25 ·
    sum 13.975 -> ROUND_HALF_UP -> "13.98" · revenue 100.00-20.00 = 80.00 ·
    margin 66.025 -> "66.03" · rate 82.53125 -> "82.53".
    """
    order = _make_order("100.00")
    line_item = _make_line_item(
        order,
        shopify_line_item_id=17_851_226_325_297,
        quantity=3,
        confirmed_price=Decimal("10000.00"),
        grams=500,
    )
    r1 = _refund(line_item, 1, subtotal=Decimal("10.00"), total_tax=Decimal("0.00"))
    r2 = _refund(line_item, 1, subtotal=Decimal("10.00"), total_tax=Decimal("0.00"))
    assert r1.line_item_id == r2.line_item_id == 17_851_226_325_297
    assert r1.shopify_refund_id != r2.shopify_refund_id

    res = auth_client.get(DETAIL_URL.format(pk=order.pk))

    assert res.status_code == 200
    assert res.data["total_weight_grams"] == 500
    assert res.data["confirmed_cost"] == "10.00"
    assert res.data["shipping_cost"] == "2.73"
    assert res.data["korea_warehouse_cost"] == "1.25"
    assert res.data["total_cost"] == "13.98"
    assert res.data["margin_amount"] == "66.03"
    assert res.data["margin_rate"] == "82.53"

    # Residual characterization (mirrors AC-NET-005): 66.03 + 13.98 = 80.01 vs
    # net paid 80.00. Under M10 the residual collapses to 0.00
    # (52.80 + 27.20 = 80.00), so these two lines discriminate M10 as well.
    net_paid = Decimal("80.00")
    residual = (
        Decimal(res.data["margin_amount"]) + Decimal(res.data["total_cost"])
    ) - net_paid
    assert residual == Decimal("0.01")
    assert abs(residual) <= Decimal("0.01")


# ---------------------------------------------------------------------------
# AC-NET-016 — memoization contract: one computation per serialized order
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_net_016_memoization_contract_one_call_per_order(auth_client):
    """AC-NET-016 (M11-sole).

    [HARD] Passing on unmodified code is CORRECT — invariant preservation.
    Assertion (a) compares the spied response against a baseline response taken
    OUTSIDE the spy, never against AC-NET-001's netted expectations, so it holds
    both before and after the change. That form is also what detects a missing
    `wraps=`: a bare MagicMock supports `is None`, `__getitem__`, `.quantize()`
    and `== Decimal("0")`, so weak non-null assertions would not notice, but the
    getters would return `str(MagicMock.quantize(...))` reprs that differ from
    the baseline.

    M11 (a getter calling `_compute_cost_breakdown_uncached` directly, or the
    cache lookup at serializers.py:531-536 deleted) makes DRF's 7 independently
    evaluated SerializerMethodFields produce call_count 7. This is the ONLY
    observable signal: query counts do not move, because the netting reads the
    prefetch cache and `_get_exchange_rate` is separately memoized
    (serializers.py:466-498).
    """
    order = _build_ac001_order()
    url = DETAIL_URL.format(pk=order.pk)

    res_baseline = auth_client.get(url)

    with mock.patch(
        "order.serializers._compute_cost_breakdown_for_rate",
        wraps=order_serializers._compute_cost_breakdown_for_rate,
    ) as spy:
        res_spied = auth_client.get(url)

    # (a) the spy observes without intervening
    assert res_spied.status_code == res_baseline.status_code == 200
    assert {k: res_spied.data[k] for k in COST_FIELDS} == {
        k: res_baseline.data[k] for k in COST_FIELDS
    }

    # (b) exactly one computation per serialized order
    assert spy.call_count == 1
