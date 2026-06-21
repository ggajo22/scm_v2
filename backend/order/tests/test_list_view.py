import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import Order, Refund

User = get_user_model()
URL = "/api/orders/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="list_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def make_order(shopify_order_id, store_type="gimssine", financial_status="pending",
               fulfillment_status=None, shopify_created_at=None, **kwargs):
    return Order.objects.create(
        shopify_order_id=shopify_order_id,
        store_type=store_type,
        financial_status=financial_status,
        fulfillment_status=fulfillment_status,
        shopify_created_at=shopify_created_at or timezone.now(),
        **kwargs,
    )


@pytest.mark.django_db
def test_list_requires_auth():
    client = APIClient()
    res = client.get(URL)
    assert res.status_code == 401


@pytest.mark.django_db
def test_list_returns_empty(auth_client):
    res = auth_client.get(URL)
    assert res.status_code == 200
    assert res.data["count"] == 0
    assert res.data["results"] == []


@pytest.mark.django_db
def test_list_filter_store_type(auth_client):
    make_order(1001, store_type="gimssine")
    make_order(1002, store_type="etoile")
    res = auth_client.get(URL, {"store_type": "gimssine"})
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["store_type"] == "gimssine"


@pytest.mark.django_db
def test_list_filter_financial_status(auth_client):
    make_order(2001, financial_status="paid")
    make_order(2002, financial_status="pending")
    res = auth_client.get(URL, {"financial_status": "paid"})
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["financial_status"] == "paid"


@pytest.mark.django_db
def test_list_filter_fulfillment_status_unfulfilled(auth_client):
    make_order(3001, fulfillment_status=None)
    make_order(3002, fulfillment_status="fulfilled")
    res = auth_client.get(URL, {"fulfillment_status": "unfulfilled"})
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["fulfillment_status"] is None


@pytest.mark.django_db
def test_list_filter_date_range(auth_client):
    import datetime
    old_dt = timezone.make_aware(datetime.datetime(2024, 1, 1))
    new_dt = timezone.make_aware(datetime.datetime(2025, 6, 15))
    make_order(4001, shopify_created_at=old_dt)
    make_order(4002, shopify_created_at=new_dt)
    res = auth_client.get(URL, {"date_from": "2025-01-01", "date_to": "2025-12-31"})
    assert res.status_code == 200
    assert res.data["count"] == 1


@pytest.mark.django_db
def test_list_date_from_after_date_to(auth_client):
    res = auth_client.get(URL, {"date_from": "2025-12-31", "date_to": "2025-01-01"})
    assert res.status_code == 400


@pytest.mark.django_db
def test_list_has_refund_field_true(auth_client):
    order = make_order(5001)
    Refund.objects.create(order=order, shopify_refund_id=9001)
    res = auth_client.get(URL)
    assert res.status_code == 200
    assert res.data["results"][0]["has_refund"] is True


@pytest.mark.django_db
def test_list_has_refund_field_false(auth_client):
    make_order(5002)
    res = auth_client.get(URL)
    assert res.status_code == 200
    assert res.data["results"][0]["has_refund"] is False


@pytest.mark.django_db
def test_list_pagination(auth_client):
    import datetime
    for i in range(51):
        dt = timezone.make_aware(datetime.datetime(2025, 1, 1) + datetime.timedelta(hours=i))
        make_order(6000 + i, shopify_created_at=dt)
    res = auth_client.get(URL)
    assert res.status_code == 200
    assert res.data["count"] == 51
    assert len(res.data["results"]) == 50
    assert res.data["next"] is not None


@pytest.mark.django_db
def test_list_ordered_by_created_desc(auth_client):
    import datetime
    dt1 = timezone.make_aware(datetime.datetime(2025, 1, 1))
    dt2 = timezone.make_aware(datetime.datetime(2025, 6, 1))
    make_order(7001, shopify_created_at=dt1)
    make_order(7002, shopify_created_at=dt2)
    res = auth_client.get(URL)
    assert res.status_code == 200
    ids = [r["shopify_order_id"] for r in res.data["results"]]
    assert ids[0] == 7002  # newer first


# ---------------------------------------------------------------------------
# SPEC-ORDER-002: search query parameter
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_search_by_order_number(auth_client):
    """?search=1234 matches order with order_number=1234."""
    make_order(8001, order_number=1234)
    make_order(8002, order_number=9999)
    res = auth_client.get(URL, {"search": "1234"})
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["shopify_order_id"] == 8001


@pytest.mark.django_db
def test_search_by_name_with_hash(auth_client):
    """?search=#1234 (URL-decoded) matches order with name='#1234'."""
    make_order(8003, name="#1234")
    make_order(8004, name="#9999")
    res = auth_client.get(URL, {"search": "#1234"})
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["shopify_order_id"] == 8003


@pytest.mark.django_db
def test_search_by_sku_isbn(auth_client):
    """?search=9788901234567 (13-digit ISBN) matches order containing LineItem.sku."""
    from order.models import LineItem
    order = make_order(8005)
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=20001,
        sku="9788901234567",
    )
    other = make_order(8006)
    LineItem.objects.create(
        order=other,
        shopify_line_item_id=20002,
        sku="9780000000000",
    )
    res = auth_client.get(URL, {"search": "9788901234567"})
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["shopify_order_id"] == 8005


@pytest.mark.django_db
def test_search_empty_returns_all(auth_client):
    """?search= (empty string) returns all orders without filtering."""
    make_order(8007)
    make_order(8008)
    res = auth_client.get(URL, {"search": ""})
    assert res.status_code == 200
    assert res.data["count"] == 2


@pytest.mark.django_db
def test_search_no_match_returns_empty(auth_client):
    """?search=9999999 returns empty list when no order matches."""
    make_order(8009, order_number=1111)
    res = auth_client.get(URL, {"search": "9999999"})
    assert res.status_code == 200
    assert res.data["count"] == 0


@pytest.mark.django_db
def test_search_combined_with_store_type(auth_client):
    """?search=1234&store_type=gimssine applies both filters with AND."""
    make_order(8010, order_number=1234, store_type="gimssine")
    make_order(8011, order_number=1234, store_type="etoile")
    res = auth_client.get(URL, {"search": "1234", "store_type": "gimssine"})
    assert res.status_code == 200
    assert res.data["count"] == 1
    assert res.data["results"][0]["shopify_order_id"] == 8010


@pytest.mark.django_db
def test_search_sku_no_duplicate_orders(auth_client):
    """Order with multiple matching line items must appear only once."""
    from order.models import LineItem
    order = make_order(8012)
    LineItem.objects.create(order=order, shopify_line_item_id=30001, sku="9788901234567")
    LineItem.objects.create(order=order, shopify_line_item_id=30002, sku="9788901234567")
    res = auth_client.get(URL, {"search": "9788901234567"})
    assert res.status_code == 200
    assert res.data["count"] == 1
