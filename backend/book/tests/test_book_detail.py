"""
Tests for GET /api/book/{id}/ — SPEC-BOOK-EDIT-001
REQ-BKEDIT-001 through REQ-BKEDIT-006
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from book.models import BookNote, EtoileBookInfo, EtoileBookInven, Info, Inven, Shopify_product

User = get_user_model()


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


def make_book(sku: str = "ISBN-001", title: str = "Test Book", price_sale: float = 10000.0,
              status_of_shopify: int = 100) -> Inven:
    """Helper: create Inven + Info pair."""
    inven = Inven.objects.create(
        inven_SKU=sku,
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=status_of_shopify,
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
# REQ-BKEDIT-001: GET /api/book/{id}/ returns full response
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_book_detail_returns_full_response(auth_client, db):
    """GET /api/book/{id}/ must return inven, info, notes, shopify_products, etoile fields."""
    inven = make_book("ISBN-DETAIL-001", "Detail Test Book")

    # Add a shopify product
    Shopify_product.objects.create(
        inven=inven,
        product_id="111222333",
        variant_id="444555666",
        inventory_item_id="777888999",
        shopify_price=15000.0,
    )

    # Add a note
    BookNote.objects.create(
        inven=inven,
        note_type="GENERAL",
        content="Test note content",
        created_by="detail_user",
    )

    resp = auth_client.get(f"/api/book/{inven.id}/")
    assert resp.status_code == 200

    data = resp.json()
    # Top-level fields (flat structure — REQ-BKEDIT-001)
    assert "id" in data
    assert "inven_SKU" in data
    assert "info" in data
    assert "notes" in data
    assert "shopify_products" in data
    assert "etoile" in data

    # Inven fields (flat, not nested under "inven")
    assert data["inven_SKU"] == "ISBN-DETAIL-001"
    assert data["status_of_shopify"] == 100

    # Info fields
    assert data["info"]["name"] == "Detail Test Book"
    assert data["info"]["price_sale"] == 10000.0

    # Shopify products
    assert len(data["shopify_products"]) == 1
    assert data["shopify_products"][0]["product_id"] == "111222333"

    # Notes
    assert len(data["notes"]) == 1
    assert data["notes"][0]["content"] == "Test note content"


# ---------------------------------------------------------------------------
# REQ-BKEDIT-002: Unauthenticated → 401
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_book_detail_unauthenticated_returns_401(db):
    """GET /api/book/{id}/ without JWT must return 401."""
    inven = make_book("ISBN-UNAUTH-001")
    client = APIClient()
    resp = client.get(f"/api/book/{inven.id}/")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# REQ-BKEDIT-003: Non-existent id → 404
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_book_detail_not_found_returns_404(auth_client, db):
    """GET /api/book/99999/ must return 404 when Inven does not exist."""
    resp = auth_client.get("/api/book/99999/")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# REQ-BKEDIT-004: No EtoileBookInven → etoile is null
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_book_detail_without_etoile_returns_null(auth_client, db):
    """GET /api/book/{id}/ must return etoile=null when no EtoileBookInven exists."""
    inven = make_book("ISBN-NO-ETOILE-001", "No Etoile Book")

    resp = auth_client.get(f"/api/book/{inven.id}/")
    assert resp.status_code == 200
    assert resp.json()["etoile"] is None


# ---------------------------------------------------------------------------
# REQ-BKEDIT-005: Notes filtering — unresolved (all) + resolved (max 10 recent)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_book_detail_with_etoile_returns_etoile_data(auth_client, db):
    """GET /api/book/{id}/ must return etoile data when EtoileBookInven and EtoileBookInfo exist."""
    from book.models import EtoileBookInfo, EtoileBookInven, EtoileShopifyProduct

    inven = make_book("ISBN-WITH-ETOILE-001", "Etoile Book")
    etoile_inven = EtoileBookInven.objects.create(inven=inven, status_of_shopify=100)
    EtoileBookInfo.objects.create(
        etoile_inven=etoile_inven,
        name_en="Etoile Book EN",
        desc_en="English description",
        tags=["tag1", "tag2"],
    )
    EtoileShopifyProduct.objects.create(
        etoile_inven=etoile_inven,
        product_id="ETL_P001",
        variant_id="ETL_V001",
        inventory_item_id="ETL_I001",
        shopify_price=15000.0,
    )

    resp = auth_client.get(f"/api/book/{inven.id}/")
    assert resp.status_code == 200

    data = resp.json()
    assert data["etoile"] is not None
    # etoile.inven is nested (not flat) — matches frontend BookDetail type
    assert data["etoile"]["inven"]["status_of_shopify"] == 100
    assert data["etoile"]["info"]["name_en"] == "Etoile Book EN"
    assert len(data["etoile"]["shopify_products"]) == 1


@pytest.mark.django_db
def test_get_book_detail_etoile_without_info_returns_info_null(auth_client, db):
    """GET /api/book/{id}/ must return etoile.info=null when EtoileBookInfo does not exist."""
    from book.models import EtoileBookInven

    inven = make_book("ISBN-ETOILE-NOINFO-001", "Etoile No Info Book")
    EtoileBookInven.objects.create(inven=inven)

    resp = auth_client.get(f"/api/book/{inven.id}/")
    assert resp.status_code == 200

    data = resp.json()
    assert data["etoile"] is not None
    assert data["etoile"]["info"] is None


@pytest.mark.django_db
def test_get_book_detail_notes_include_unresolved_and_recent_resolved(auth_client, db):
    """
    Notes endpoint must return all unresolved notes plus at most 10 most-recent resolved notes.
    """
    from django.utils import timezone

    inven = make_book("ISBN-NOTES-001", "Notes Filtering Book")

    # Create 3 unresolved notes
    for i in range(3):
        BookNote.objects.create(
            inven=inven,
            note_type="GENERAL",
            content=f"Unresolved note {i}",
            created_by="detail_user",
        )

    # Create 15 resolved notes (only 10 most recent should appear)
    for i in range(15):
        note = BookNote.objects.create(
            inven=inven,
            note_type="GENERAL",
            content=f"Resolved note {i}",
            created_by="detail_user",
        )
        note.is_resolved = True
        note.resolved_at = timezone.now()
        note.save(update_fields=["is_resolved", "resolved_at"])

    resp = auth_client.get(f"/api/book/{inven.id}/")
    assert resp.status_code == 200

    notes = resp.json()["notes"]
    unresolved = [n for n in notes if not n["is_resolved"]]
    resolved = [n for n in notes if n["is_resolved"]]

    # All 3 unresolved must be present
    assert len(unresolved) == 3
    # Only 10 most recent resolved must appear
    assert len(resolved) == 10
    # Total
    assert len(notes) == 13
