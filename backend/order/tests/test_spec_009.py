"""SPEC-ORDER-009: ExchangeRate 모델 및 주문일 기준 USD→KRW 환율 적용 마진 계산 (TDD)."""
import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import ExchangeRate, LineItem, Order

User = get_user_model()

EXCHANGE_RATE_LIST_URL = "/api/exchange-rates/"
EXCHANGE_RATE_DETAIL_URL = "/api/exchange-rates/{date}/"
ORDER_DETAIL_URL = "/api/orders/{pk}/"


# ---------------------------------------------------------------------------
# Fixtures: auth
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec009_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# Fixtures: ExchangeRate
# ---------------------------------------------------------------------------


@pytest.fixture
def exchange_rate_2026_01_15(db):
    """2026-01-15 환율: 1 USD = 1300.00 KRW."""
    return ExchangeRate.objects.create(
        effective_date="2026-01-15",
        rate=Decimal("1300.00"),
        source="manual",
    )


@pytest.fixture
def exchange_rate_2026_01_10(db):
    """2026-01-10 환율: 1 USD = 1280.00 KRW (폴백 테스트용)."""
    return ExchangeRate.objects.create(
        effective_date="2026-01-10",
        rate=Decimal("1280.00"),
        source="manual",
    )


# ---------------------------------------------------------------------------
# Fixtures: Orders for margin tests
# ---------------------------------------------------------------------------


@pytest.fixture
def order_with_confirmed_items_usd(db):
    """
    total_price = 100.00 USD, shopify_created_at = 2026-01-15
    line_item A: confirmed_price=50000 KRW, quantity=2
    line_item B: confirmed_price=null
    """
    order = Order.objects.create(
        shopify_order_id=99020,
        store_type="gimssine",
        financial_status="paid",
        total_price="100.00",
        shopify_created_at=timezone.make_aware(
            datetime.datetime(2026, 1, 15, 12, 0, 0)
        ),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=12010,
        title="상품 A",
        quantity=2,
        price="50.00",
        confirmed_price="50000.00",
        confirmed_distributor="bookseen",
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=12011,
        title="상품 B",
        quantity=1,
        price="50.00",
        confirmed_price=None,
        confirmed_distributor=None,
    )
    return order


@pytest.fixture
def order_dated_2026_01_12(db):
    """
    Order dated 2026-01-12 (falls between 2026-01-10 and 2026-01-15).
    총 가격: 50.00 USD, confirmed_price=30000 KRW, quantity=1
    폴백 환율 테스트: effective_date=2026-01-10 (1280.00) 적용되어야 함
    """
    order = Order.objects.create(
        shopify_order_id=99021,
        store_type="gimssine",
        financial_status="paid",
        total_price="50.00",
        shopify_created_at=timezone.make_aware(
            datetime.datetime(2026, 1, 12, 10, 0, 0)
        ),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=12020,
        title="상품 C",
        quantity=1,
        price="50.00",
        confirmed_price="30000.00",
        confirmed_distributor="bookseen",
    )
    return order


@pytest.fixture
def order_no_exchange_rate(db):
    """환율 데이터가 없을 때를 위한 주문 (shopify_created_at = 2025-01-01)."""
    order = Order.objects.create(
        shopify_order_id=99022,
        store_type="gimssine",
        financial_status="paid",
        total_price="100.00",
        shopify_created_at=timezone.make_aware(
            datetime.datetime(2025, 1, 1, 0, 0, 0)
        ),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=12030,
        title="상품 D",
        quantity=1,
        price="100.00",
        confirmed_price="50000.00",
        confirmed_distributor="bookseen",
    )
    return order


# ---------------------------------------------------------------------------
# Module 3: 마진 계산 수정 (REQ-010, REQ-011, REQ-012, REQ-013)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_margin_uses_exchange_rate_for_krw_conversion(
    auth_client: APIClient,
    order_with_confirmed_items_usd: Order,
    exchange_rate_2026_01_15,
) -> None:
    """REQ-010, REQ-012: USD→KRW 환산 후 마진 계산.

    total_price = 100.00 USD, rate = 1300.00 KRW/USD
    total_price_krw = 100.00 * 1300.00 = 130000.00
    confirmed_cost_krw = 50000.00 * 2 = 100000.00 (item B는 null 제외)
    margin_amount = 130000.00 - 100000.00 = 30000.00
    margin_rate = (30000 / 130000) * 100 = 23.08 (ROUND_HALF_UP)
    """
    url = ORDER_DETAIL_URL.format(pk=order_with_confirmed_items_usd.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    margin = res.data.get("margin_amount")
    assert margin is not None
    assert Decimal(str(margin)) == Decimal("30000.00")
    rate = res.data.get("margin_rate")
    assert rate is not None
    assert Decimal(str(rate)) == Decimal("23.08")


@pytest.mark.django_db
def test_margin_fallback_to_prior_date_rate(
    auth_client: APIClient,
    order_dated_2026_01_12: Order,
    exchange_rate_2026_01_10,
    exchange_rate_2026_01_15,
) -> None:
    """REQ-003, REQ-012: 주문일 이전 가장 최근 환율 폴백 적용.

    order date = 2026-01-12
    available rates: 2026-01-10 (1280.00), 2026-01-15 (1300.00)
    fallback → 2026-01-10 (1280.00) 적용

    total_price = 50.00 USD * 1280.00 = 64000.00 KRW
    confirmed_cost = 30000.00 * 1 = 30000.00 KRW
    margin_amount = 64000.00 - 30000.00 = 34000.00
    margin_rate = (34000 / 64000) * 100 = 53.13
    """
    url = ORDER_DETAIL_URL.format(pk=order_dated_2026_01_12.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    margin = res.data.get("margin_amount")
    assert margin is not None
    assert Decimal(str(margin)) == Decimal("34000.00")
    rate = res.data.get("margin_rate")
    assert rate is not None
    assert Decimal(str(rate)) == Decimal("53.13")


@pytest.mark.django_db
def test_margin_null_when_no_exchange_rate(
    auth_client: APIClient,
    order_no_exchange_rate: Order,
) -> None:
    """REQ-011: 환율 레코드가 없을 때 margin_amount=null, margin_rate=null."""
    url = ORDER_DETAIL_URL.format(pk=order_no_exchange_rate.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data.get("margin_amount") is None
    assert res.data.get("margin_rate") is None


# ---------------------------------------------------------------------------
# Module 2: 환율 REST API (REQ-004 ~ REQ-009)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_exchange_rate_list_returns_200(
    auth_client: APIClient,
    exchange_rate_2026_01_15,
    exchange_rate_2026_01_10,
) -> None:
    """REQ-004: GET /api/exchange-rates/ → 최신순 목록 200 반환."""
    res = auth_client.get(EXCHANGE_RATE_LIST_URL)
    assert res.status_code == 200
    # Handle both paginated ({"results": [...]}) and non-paginated ([...]) responses
    items = res.data.get("results", res.data) if isinstance(res.data, dict) else res.data
    dates = [item["effective_date"] for item in items]
    # 최신순 정렬: 2026-01-15 이 2026-01-10보다 먼저
    assert dates.index("2026-01-15") < dates.index("2026-01-10")


@pytest.mark.django_db
def test_exchange_rate_create_returns_201(auth_client: APIClient) -> None:
    """REQ-005: POST /api/exchange-rates/ → HTTP 201 신규 생성."""
    payload = {"effective_date": "2026-02-01", "rate": "1320.00", "source": "manual"}
    res = auth_client.post(EXCHANGE_RATE_LIST_URL, payload, format="json")
    assert res.status_code == 201
    assert res.data["effective_date"] == "2026-02-01"
    assert Decimal(res.data["rate"]) == Decimal("1320.00")


@pytest.mark.django_db
def test_exchange_rate_retrieve_returns_200(
    auth_client: APIClient,
    exchange_rate_2026_01_15,
) -> None:
    """REQ-006: GET /api/exchange-rates/{date}/ → HTTP 200 단건 조회."""
    url = EXCHANGE_RATE_DETAIL_URL.format(date="2026-01-15")
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["effective_date"] == "2026-01-15"
    assert Decimal(res.data["rate"]) == Decimal("1300.00")


@pytest.mark.django_db
def test_exchange_rate_retrieve_returns_404_for_missing_date(
    auth_client: APIClient,
) -> None:
    """REQ-006: GET /api/exchange-rates/{date}/ → HTTP 404 (존재하지 않는 날짜)."""
    url = EXCHANGE_RATE_DETAIL_URL.format(date="2099-12-31")
    res = auth_client.get(url)
    assert res.status_code == 404


@pytest.mark.django_db
def test_exchange_rate_update_returns_200(
    auth_client: APIClient,
    exchange_rate_2026_01_15,
) -> None:
    """REQ-007: PUT /api/exchange-rates/{date}/ → HTTP 200 수정."""
    url = EXCHANGE_RATE_DETAIL_URL.format(date="2026-01-15")
    payload = {"effective_date": "2026-01-15", "rate": "1350.00", "source": "manual"}
    res = auth_client.put(url, payload, format="json")
    assert res.status_code == 200
    assert Decimal(res.data["rate"]) == Decimal("1350.00")


@pytest.mark.django_db
def test_exchange_rate_delete_returns_204(
    auth_client: APIClient,
    exchange_rate_2026_01_15,
) -> None:
    """REQ-008: DELETE /api/exchange-rates/{date}/ → HTTP 204."""
    url = EXCHANGE_RATE_DETAIL_URL.format(date="2026-01-15")
    res = auth_client.delete(url)
    assert res.status_code == 204
    # 삭제 후 조회 → 404
    res2 = auth_client.get(url)
    assert res2.status_code == 404


@pytest.mark.django_db
def test_exchange_rate_duplicate_date_returns_400(
    auth_client: APIClient,
    exchange_rate_2026_01_15,
) -> None:
    """REQ-009: 동일 날짜 POST → HTTP 400."""
    payload = {"effective_date": "2026-01-15", "rate": "1310.00", "source": "manual"}
    res = auth_client.post(EXCHANGE_RATE_LIST_URL, payload, format="json")
    assert res.status_code == 400
    assert "effective_date" in res.data


@pytest.mark.django_db
def test_exchange_rate_unauthenticated_returns_401() -> None:
    """인증 없이 환율 API 요청 → HTTP 401."""
    client = APIClient()
    res = client.get(EXCHANGE_RATE_LIST_URL)
    assert res.status_code == 401
