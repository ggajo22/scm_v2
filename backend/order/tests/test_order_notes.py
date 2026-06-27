"""Tests for order note resolution feature (OrderNoteListView, OrderNoteResolveView)."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import Customer, Order

User = get_user_model()

NOTE_LIST_URL = "/api/orders/notes/"
RESOLVE_URL = "/api/orders/{pk}/resolve-note/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="note_test_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def order_with_note(db) -> Order:
    """Order with a non-empty note and note_resolved=False (default)."""
    return Order.objects.create(
        shopify_order_id=88001,
        store_type="gimssine",
        financial_status="paid",
        shopify_created_at=timezone.now(),
        note="배송 전 연락 바람",
    )


@pytest.fixture
def order_with_resolved_note(db) -> Order:
    """Order with a note that has already been resolved."""
    return Order.objects.create(
        shopify_order_id=88002,
        store_type="gimssine",
        financial_status="paid",
        shopify_created_at=timezone.now(),
        note="이미 처리된 메모",
        note_resolved=True,
    )


@pytest.fixture
def order_without_note(db) -> Order:
    """Order with note=None."""
    return Order.objects.create(
        shopify_order_id=88003,
        store_type="gimssine",
        financial_status="paid",
        shopify_created_at=timezone.now(),
        note=None,
    )


@pytest.fixture
def order_with_empty_note(db) -> Order:
    """Order with note='' (empty string)."""
    return Order.objects.create(
        shopify_order_id=88004,
        store_type="gimssine",
        financial_status="paid",
        shopify_created_at=timezone.now(),
        note="",
    )


@pytest.fixture
def order_with_customer_and_note(db) -> Order:
    """Order with customer and a note."""
    customer = Customer.objects.create(
        shopify_customer_id=2001,
        first_name="철수",
        last_name="김",
        email="kim@example.com",
    )
    return Order.objects.create(
        shopify_order_id=88005,
        store_type="etoile",
        financial_status="pending",
        shopify_created_at=timezone.now(),
        note="포장 주의",
        customer=customer,
    )


# ---------------------------------------------------------------------------
# GET /api/orders/notes/ tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_note_list_returns_orders_with_unresolved_notes(
    auth_client: APIClient, order_with_note: Order
) -> None:
    """Order with note and note_resolved=False must appear in the list."""
    res = auth_client.get(NOTE_LIST_URL)
    assert res.status_code == 200
    ids = [item["id"] for item in res.data]
    assert order_with_note.pk in ids


@pytest.mark.django_db
def test_note_list_excludes_resolved_notes(
    auth_client: APIClient, order_with_resolved_note: Order
) -> None:
    """Order with note_resolved=True must NOT appear in the list."""
    res = auth_client.get(NOTE_LIST_URL)
    assert res.status_code == 200
    ids = [item["id"] for item in res.data]
    assert order_with_resolved_note.pk not in ids


@pytest.mark.django_db
def test_note_list_excludes_orders_without_notes(
    auth_client: APIClient, order_without_note: Order, order_with_empty_note: Order
) -> None:
    """Orders with note=None or note='' must NOT appear in the list."""
    res = auth_client.get(NOTE_LIST_URL)
    assert res.status_code == 200
    ids = [item["id"] for item in res.data]
    assert order_without_note.pk not in ids
    assert order_with_empty_note.pk not in ids


@pytest.mark.django_db
def test_note_list_requires_authentication(order_with_note: Order) -> None:
    """Unauthenticated request to notes list must return 401."""
    client = APIClient()
    res = client.get(NOTE_LIST_URL)
    assert res.status_code == 401


@pytest.mark.django_db
def test_note_list_response_contains_expected_fields(
    auth_client: APIClient, order_with_customer_and_note: Order
) -> None:
    """Response items must contain required fields including nested customer."""
    res = auth_client.get(NOTE_LIST_URL)
    assert res.status_code == 200
    assert len(res.data) >= 1
    item = next(i for i in res.data if i["id"] == order_with_customer_and_note.pk)
    assert "id" in item
    assert "shopify_order_id" in item
    assert "note" in item
    assert "note_resolved" in item
    assert item["note_resolved"] is False
    assert "customer" in item
    assert item["customer"]["first_name"] == "철수"


# ---------------------------------------------------------------------------
# PATCH /api/orders/{pk}/resolve-note/ tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_note_returns_200(
    auth_client: APIClient, order_with_note: Order
) -> None:
    """PATCH resolve-note on existing order must return 200 with note_resolved=True."""
    url = RESOLVE_URL.format(pk=order_with_note.pk)
    res = auth_client.patch(url)
    assert res.status_code == 200
    assert res.data["note_resolved"] is True


@pytest.mark.django_db
def test_resolve_note_persists_in_db(
    auth_client: APIClient, order_with_note: Order
) -> None:
    """After PATCH, note_resolved=True must be persisted in the database."""
    url = RESOLVE_URL.format(pk=order_with_note.pk)
    auth_client.patch(url)
    order_with_note.refresh_from_db()
    assert order_with_note.note_resolved is True


@pytest.mark.django_db
def test_resolve_note_returns_404_for_missing_order(
    auth_client: APIClient,
) -> None:
    """PATCH resolve-note with non-existent pk must return 404."""
    url = RESOLVE_URL.format(pk=99999999)
    res = auth_client.patch(url)
    assert res.status_code == 404


@pytest.mark.django_db
def test_resolve_note_requires_authentication(order_with_note: Order) -> None:
    """Unauthenticated PATCH to resolve-note must return 401."""
    client = APIClient()
    url = RESOLVE_URL.format(pk=order_with_note.pk)
    res = client.patch(url)
    assert res.status_code == 401


@pytest.mark.django_db
def test_resolve_note_removes_order_from_note_list(
    auth_client: APIClient, order_with_note: Order
) -> None:
    """After PATCH resolve-note, the order must no longer appear in GET /orders/notes/."""
    # Verify order appears in list before resolving
    list_res = auth_client.get(NOTE_LIST_URL)
    assert list_res.status_code == 200
    ids_before = [item["id"] for item in list_res.data]
    assert order_with_note.pk in ids_before

    # Resolve the note
    resolve_url = RESOLVE_URL.format(pk=order_with_note.pk)
    patch_res = auth_client.patch(resolve_url)
    assert patch_res.status_code == 200

    # Verify order no longer appears in list
    list_res_after = auth_client.get(NOTE_LIST_URL)
    assert list_res_after.status_code == 200
    ids_after = [item["id"] for item in list_res_after.data]
    assert order_with_note.pk not in ids_after
