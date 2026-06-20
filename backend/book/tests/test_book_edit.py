"""
Tests for PATCH /api/book/{id}/info/ and BookNote endpoints — SPEC-BOOK-EDIT-001
REQ-BKEDIT-007 through REQ-BKEDIT-015
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from book.models import BookNote, Info, Inven

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="edit_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def make_book(sku: str = "ISBN-EDIT-001", title: str = "Edit Test Book",
              price_sale: float = 10000.0) -> Inven:
    """Helper: create Inven + Info pair."""
    inven = Inven.objects.create(
        inven_SKU=sku,
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name=title,
        price_sale=price_sale,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    return inven


# ---------------------------------------------------------------------------
# REQ-BKEDIT-007: PATCH /api/book/{id}/info/ — partial update
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_patch_info_updates_fields(auth_client, db):
    """PATCH /api/book/{id}/info/ with partial fields must update and return 200."""
    inven = make_book("ISBN-PATCH-001", "Original Title", price_sale=10000.0)

    payload = {"name": "Updated Title", "price_sale": 20000.0}
    resp = auth_client.patch(f"/api/book/{inven.id}/info/", payload, format="json")
    assert resp.status_code == 200

    data = resp.json()
    assert data["name"] == "Updated Title"
    assert data["price_sale"] == 20000.0

    # Verify DB updated
    inven.info.refresh_from_db()
    assert inven.info.name == "Updated Title"
    assert inven.info.price_sale == 20000.0


# ---------------------------------------------------------------------------
# REQ-BKEDIT-008: PATCH info with invalid field type → 400
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_patch_info_invalid_field_type_returns_400(auth_client, db):
    """PATCH /api/book/{id}/info/ with invalid price type must return 400."""
    inven = make_book("ISBN-PATCH-002")

    payload = {"price_sale": "not-a-number"}
    resp = auth_client.patch(f"/api/book/{inven.id}/info/", payload, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# REQ-BKEDIT-009: PATCH info unauthenticated → 401
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_patch_info_unauthenticated_returns_401(db):
    """PATCH /api/book/{id}/info/ without JWT must return 401."""
    inven = make_book("ISBN-PATCH-003")
    client = APIClient()
    resp = client.patch(f"/api/book/{inven.id}/info/", {"name": "Hack"}, format="json")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# REQ-BKEDIT-010: POST /api/book/{id}/notes/ — GENERAL note
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_add_note_general(auth_client, user, db):
    """POST /api/book/{id}/notes/ with GENERAL type must create note and return 201."""
    inven = make_book("ISBN-NOTE-001")

    payload = {"note_type": "GENERAL", "content": "General note content"}
    resp = auth_client.post(f"/api/book/{inven.id}/notes/", payload, format="json")
    assert resp.status_code == 201

    data = resp.json()
    assert data["note_type"] == "GENERAL"
    assert data["content"] == "General note content"
    assert data["is_resolved"] is False
    assert data["created_by"] == user.username

    # Verify note was created in DB
    assert BookNote.objects.filter(inven=inven, note_type="GENERAL").exists()


# ---------------------------------------------------------------------------
# REQ-BKEDIT-011: POST /api/book/{id}/notes/ — SHIPPING note
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_add_note_shipping(auth_client, user, db):
    """POST /api/book/{id}/notes/ with SHIPPING type must create note and return 201."""
    inven = make_book("ISBN-NOTE-002")

    payload = {"note_type": "SHIPPING", "content": "Shipping note content"}
    resp = auth_client.post(f"/api/book/{inven.id}/notes/", payload, format="json")
    assert resp.status_code == 201

    data = resp.json()
    assert data["note_type"] == "SHIPPING"
    assert data["content"] == "Shipping note content"
    assert data["created_by"] == user.username


# ---------------------------------------------------------------------------
# REQ-BKEDIT-012: POST notes with no content → 400
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_add_note_missing_content_returns_400(auth_client, db):
    """POST /api/book/{id}/notes/ without content must return 400."""
    inven = make_book("ISBN-NOTE-003")

    payload = {"note_type": "GENERAL"}
    resp = auth_client.post(f"/api/book/{inven.id}/notes/", payload, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# REQ-BKEDIT-013: PATCH /api/book/notes/{note_id}/resolve/ — success
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_resolve_note_success(auth_client, db):
    """PATCH /api/book/notes/{note_id}/resolve/ must resolve GENERAL note and return 200."""
    inven = make_book("ISBN-RESOLVE-001")
    note = BookNote.objects.create(
        inven=inven,
        note_type="GENERAL",
        content="Note to resolve",
        created_by="edit_user",
    )

    resp = auth_client.patch(f"/api/book/notes/{note.id}/resolve/")
    assert resp.status_code == 200

    data = resp.json()
    assert data["is_resolved"] is True
    assert data["resolved_at"] is not None

    # Verify DB updated
    note.refresh_from_db()
    assert note.is_resolved is True


# ---------------------------------------------------------------------------
# REQ-BKEDIT-014: Resolving SHIPPING note → 400
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_resolve_shipping_note_returns_400(auth_client, db):
    """PATCH /api/book/notes/{note_id}/resolve/ on SHIPPING type must return 400."""
    inven = make_book("ISBN-RESOLVE-002")
    note = BookNote.objects.create(
        inven=inven,
        note_type="SHIPPING",
        content="Shipping note, not resolvable",
        created_by="edit_user",
    )

    resp = auth_client.patch(f"/api/book/notes/{note.id}/resolve/")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# REQ-BKEDIT-015: Resolving already-resolved note → 400
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_resolve_already_resolved_returns_400(auth_client, db):
    """PATCH /api/book/notes/{note_id}/resolve/ on already-resolved note must return 400."""
    inven = make_book("ISBN-RESOLVE-003")
    note = BookNote.objects.create(
        inven=inven,
        note_type="GENERAL",
        content="Already resolved note",
        created_by="edit_user",
        is_resolved=True,
        resolved_at=timezone.now(),
    )

    resp = auth_client.patch(f"/api/book/notes/{note.id}/resolve/")
    assert resp.status_code == 400
