"""SPEC-ORDER-008: confirmed_price / confirmed_distributor / confirmed_at + margin fields (TDD RED phase)."""
import datetime as dt_module
import pytest
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import Customer, ExchangeRate, LineItem, Order

User = get_user_model()
DETAIL_URL = "/api/orders/{pk}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec008_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def order_with_confirmed_items(db) -> Order:
    """Order with two line_items: one has confirmed_price set, one does not."""
    order = Order.objects.create(
        shopify_order_id=88001,
        store_type="gimssine",
        financial_status="paid",
        total_price=Decimal("50000.00"),
        shopify_created_at=timezone.now(),
    )
    confirmed_at = datetime(2024, 3, 15, 12, 0, 0, tzinfo=dt_timezone.utc)
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=22001,
        title="상품 A",
        quantity=2,
        price="15000.00",
        confirmed_price=Decimal("12000.00"),
        confirmed_distributor="북센",
        confirmed_at=confirmed_at,
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=22002,
        title="상품 B",
        quantity=1,
        price="20000.00",
        confirmed_price=None,
        confirmed_distributor=None,
        confirmed_at=None,
    )
    return order


@pytest.fixture
def order_all_confirmed(db) -> Order:
    """Order where ALL line_items have confirmed_price set."""
    order = Order.objects.create(
        shopify_order_id=88002,
        store_type="gimssine",
        financial_status="paid",
        total_price=Decimal("60000.00"),
        shopify_created_at=timezone.now(),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=22003,
        title="상품 C",
        quantity=2,
        price="20000.00",
        confirmed_price=Decimal("15000.00"),
        confirmed_distributor="교보",
        confirmed_at=timezone.now(),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=22004,
        title="상품 D",
        quantity=1,
        price="20000.00",
        confirmed_price=Decimal("18000.00"),
        confirmed_distributor="교보",
        confirmed_at=timezone.now(),
    )
    return order


@pytest.fixture
def exchange_rate_today(db):
    """ExchangeRate for today: 1 USD = 1300.00 KRW. Required for margin calculations."""
    return ExchangeRate.objects.create(
        effective_date=dt_module.date.today(),
        rate=Decimal("1300.00"),

    )


@pytest.fixture
def order_all_null_confirmed(db) -> Order:
    """Order where ALL line_items have confirmed_price=None → margin must be null."""
    order = Order.objects.create(
        shopify_order_id=88003,
        store_type="gimssine",
        financial_status="paid",
        total_price=Decimal("30000.00"),
        shopify_created_at=timezone.now(),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=22005,
        title="상품 E",
        quantity=2,
        price="15000.00",
        confirmed_price=None,
        confirmed_distributor=None,
        confirmed_at=None,
    )
    return order


@pytest.fixture
def order_confirmed_price_zero(db) -> Order:
    """Order where confirmed_price=0.00 (zero must be treated as valid, not null)."""
    order = Order.objects.create(
        shopify_order_id=88004,
        store_type="gimssine",
        financial_status="paid",
        total_price=Decimal("20000.00"),
        shopify_created_at=timezone.now(),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=22006,
        title="상품 F",
        quantity=2,
        price="10000.00",
        confirmed_price=Decimal("0.00"),
        confirmed_distributor="북센",
        confirmed_at=timezone.now(),
    )
    return order


# ---------------------------------------------------------------------------
# REQ-008-001: line_item contains confirmed_price, confirmed_distributor, confirmed_at
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_line_item_contains_confirmed_price_when_set(
    auth_client: APIClient,
    order_with_confirmed_items: Order,
) -> None:
    """REQ-008-001: line_item with confirmed_price set → field appears in response."""
    url = DETAIL_URL.format(pk=order_with_confirmed_items.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    items = {item["shopify_line_item_id"]: item for item in res.data["line_items"]}
    item_a = items[22001]
    assert "confirmed_price" in item_a
    assert "confirmed_distributor" in item_a
    assert "confirmed_at" in item_a
    assert item_a["confirmed_price"] == "12000.00"
    assert item_a["confirmed_distributor"] == "북센"
    assert item_a["confirmed_at"] is not None


# ---------------------------------------------------------------------------
# REQ-008-002: confirmed_price / confirmed_distributor return null when unset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_line_item_confirmed_fields_null_when_unset(
    auth_client: APIClient,
    order_with_confirmed_items: Order,
) -> None:
    """REQ-008-002: line_item with no confirmed data → confirmed fields are null."""
    url = DETAIL_URL.format(pk=order_with_confirmed_items.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    items = {item["shopify_line_item_id"]: item for item in res.data["line_items"]}
    item_b = items[22002]
    assert item_b["confirmed_price"] is None
    assert item_b["confirmed_distributor"] is None
    assert item_b["confirmed_at"] is None


# ---------------------------------------------------------------------------
# REQ-008-003: margin_amount = total_price - sum(confirmed_price * quantity) for non-null items
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_margin_amount_calculation_with_partial_confirmed(
    auth_client: APIClient,
    order_with_confirmed_items: Order,
    exchange_rate_today,
) -> None:
    """REQ-008-003: partial confirmed → margin uses USD→KRW conversion (SPEC-ORDER-009 fix).

    total_price = 50000.00 USD, rate = 1300.00 KRW/USD
    total_price_krw = 50000.00 * 1300.00 = 65,000,000
    Item A: confirmed_price=12000 KRW, quantity=2 → cost=24000 KRW
    Item B: confirmed_price=None → excluded
    margin_amount = 65,000,000 - 24,000 = 64,976,000
    """
    url = DETAIL_URL.format(pk=order_with_confirmed_items.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    margin = res.data.get("margin_amount")
    assert margin is not None
    assert Decimal(str(margin)) == Decimal("64976000.00")


# ---------------------------------------------------------------------------
# REQ-008-004: ALL line_items have null confirmed_price → margin_amount = null, margin_rate = null
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_margin_amount_is_null_when_all_confirmed_price_null(
    auth_client: APIClient,
    order_all_null_confirmed: Order,
) -> None:
    """REQ-008-004: all confirmed_price=None → margin_amount=null, margin_rate=null."""
    url = DETAIL_URL.format(pk=order_all_null_confirmed.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data.get("margin_amount") is None
    assert res.data.get("margin_rate") is None


# ---------------------------------------------------------------------------
# REQ-008-005: margin_rate = (margin_amount / total_price) * 100, 2 decimal places ROUND_HALF_UP
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_margin_rate_calculation_rounds_to_2_decimal_places(
    auth_client: APIClient,
    order_all_confirmed: Order,
    exchange_rate_today,
) -> None:
    """REQ-008-005: margin_rate uses total_price_krw as denominator (SPEC-ORDER-009 fix).

    total_price = 60000.00 USD, rate = 1300.00 KRW/USD
    total_price_krw = 60000.00 * 1300.00 = 78,000,000
    Item C: confirmed_price=15000 KRW, quantity=2 → cost=30000
    Item D: confirmed_price=18000 KRW, quantity=1 → cost=18000
    confirmed_cost_krw = 48,000
    margin_amount = 78,000,000 - 48,000 = 77,952,000
    margin_rate = (77,952,000 / 78,000,000) * 100 = 99.94 (ROUND_HALF_UP)
    """
    url = DETAIL_URL.format(pk=order_all_confirmed.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data.get("margin_amount") is not None
    assert Decimal(str(res.data["margin_amount"])) == Decimal("77952000.00")
    assert res.data.get("margin_rate") is not None
    assert Decimal(str(res.data["margin_rate"])) == Decimal("99.94")


# ---------------------------------------------------------------------------
# REQ-008-006: confirmed_price=0.00 is valid (not treated as null)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_confirmed_price_zero_is_valid_not_null(
    auth_client: APIClient,
    order_confirmed_price_zero: Order,
    exchange_rate_today,
) -> None:
    """REQ-008-006: confirmed_price=0.00 is valid (SPEC-ORDER-009 fix applied).

    total_price = 20000.00 USD, rate = 1300.00 KRW/USD
    total_price_krw = 20000.00 * 1300.00 = 26,000,000
    Item F: confirmed_price=0.00 KRW, quantity=2 → cost=0
    margin_amount = 26,000,000 - 0 = 26,000,000
    margin_rate = (26,000,000 / 26,000,000) * 100 = 100.00
    """
    url = DETAIL_URL.format(pk=order_confirmed_price_zero.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    items = res.data["line_items"]
    assert len(items) == 1
    # confirmed_price=0.00 is not null
    assert items[0]["confirmed_price"] == "0.00"
    # margin must be calculated (not None)
    assert res.data.get("margin_amount") is not None
    assert Decimal(str(res.data["margin_amount"])) == Decimal("26000000.00")
    assert res.data.get("margin_rate") is not None
    assert Decimal(str(res.data["margin_rate"])) == Decimal("100.00")
