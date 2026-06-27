"""SPEC-ORDER-003: Order Detail endpoint tests (TDD RED phase)."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import Customer, LineItem, Order, Refund, ShippingAddress

User = get_user_model()
DETAIL_URL = "/api/orders/{pk}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="detail_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def order(db) -> Order:
    """Minimal order with no related objects."""
    return Order.objects.create(
        shopify_order_id=99001,
        store_type="gimssine",
        financial_status="paid",
        shopify_created_at=timezone.now(),
    )


@pytest.fixture
def order_with_customer(db) -> Order:
    customer = Customer.objects.create(
        shopify_customer_id=1001,
        first_name="길동",
        last_name="홍",
        email="hong@example.com",
        phone="010-1234-5678",
    )
    return Order.objects.create(
        shopify_order_id=99002,
        store_type="gimssine",
        financial_status="paid",
        shopify_created_at=timezone.now(),
        customer=customer,
    )


@pytest.fixture
def order_with_shipping(db) -> Order:
    order = Order.objects.create(
        shopify_order_id=99003,
        store_type="gimssine",
        financial_status="paid",
        shopify_created_at=timezone.now(),
    )
    ShippingAddress.objects.create(
        order=order,
        name="홍 길동",
        first_name="길동",
        last_name="홍",
        address1="서울특별시 강남구 테헤란로 123",
        city="서울",
        country="South Korea",
        country_code="KR",
        zip="06241",
    )
    return order


@pytest.fixture
def order_with_line_items(db) -> Order:
    order = Order.objects.create(
        shopify_order_id=99004,
        store_type="gimssine",
        financial_status="paid",
        shopify_created_at=timezone.now(),
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=11001,
        title="테스트 상품 A",
        quantity=2,
        price="15000.00",
    )
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=11002,
        title="테스트 상품 B",
        quantity=1,
        price="30000.00",
    )
    return order


@pytest.fixture
def order_with_refunds(db) -> Order:
    order = Order.objects.create(
        shopify_order_id=99005,
        store_type="gimssine",
        financial_status="refunded",
        shopify_created_at=timezone.now(),
    )
    Refund.objects.create(
        order=order,
        shopify_refund_id=55001,
        note="고객 요청 환불",
        subtotal="15000.00",
        total_tax="0.00",
    )
    return order


# ---------------------------------------------------------------------------
# REQ-OD-003: HTTP 200 + OrderDetailSerializer data on valid ID
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_order_detail_returns_200(auth_client: APIClient, order: Order) -> None:
    """REQ-OD-003: valid pk → 200 with core fields present."""
    url = DETAIL_URL.format(pk=order.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    data = res.data
    assert data["id"] == order.pk
    assert data["shopify_order_id"] == order.shopify_order_id
    assert "name" in data
    assert "financial_status" in data
    assert "line_items" in data
    assert "shipping_address" in data
    assert "customer" in data
    assert "refunds" in data
    assert "shipping_lines" in data


# ---------------------------------------------------------------------------
# REQ-OD-004: HTTP 404 on missing ID
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_order_detail_returns_404_for_missing_id(auth_client: APIClient) -> None:
    """REQ-OD-004: non-existent pk → 404."""
    url = DETAIL_URL.format(pk=99999999)
    res = auth_client.get(url)
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# REQ-OD-002: IsAuthenticated guard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_order_detail_requires_authentication(order: Order) -> None:
    """REQ-OD-002: unauthenticated request → 401."""
    client = APIClient()
    url = DETAIL_URL.format(pk=order.pk)
    res = client.get(url)
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# REQ-OD-001: nested serializers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_detail_contains_line_items(
    auth_client: APIClient, order_with_line_items: Order
) -> None:
    """REQ-OD-001: order with 2 line items → both returned in response."""
    url = DETAIL_URL.format(pk=order_with_line_items.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    line_items = res.data["line_items"]
    assert len(line_items) == 2
    titles = {item["title"] for item in line_items}
    assert "테스트 상품 A" in titles
    assert "테스트 상품 B" in titles


@pytest.mark.django_db
def test_order_detail_contains_shipping_address(
    auth_client: APIClient, order_with_shipping: Order
) -> None:
    """REQ-OD-001: order with ShippingAddress → address fields present."""
    url = DETAIL_URL.format(pk=order_with_shipping.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    addr = res.data["shipping_address"]
    assert addr is not None
    assert addr["city"] == "서울"
    assert addr["country_code"] == "KR"
    assert addr["zip"] == "06241"


@pytest.mark.django_db
def test_order_detail_contains_refunds_when_present(
    auth_client: APIClient, order_with_refunds: Order
) -> None:
    """REQ-OD-001: order with Refund → refund data present."""
    url = DETAIL_URL.format(pk=order_with_refunds.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    refunds = res.data["refunds"]
    assert len(refunds) == 1
    assert refunds[0]["shopify_refund_id"] == 55001
    assert refunds[0]["note"] == "고객 요청 환불"


@pytest.mark.django_db
def test_order_detail_has_refund_false_when_no_refunds(
    auth_client: APIClient, order: Order
) -> None:
    """REQ-OD-001: no refunds → has_refund=False."""
    url = DETAIL_URL.format(pk=order.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["has_refund"] is False


@pytest.mark.django_db
def test_order_detail_has_refund_true_when_refunds_exist(
    auth_client: APIClient, order_with_refunds: Order
) -> None:
    """REQ-OD-001: with refunds → has_refund=True."""
    url = DETAIL_URL.format(pk=order_with_refunds.pk)
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["has_refund"] is True
