"""
Tests for Shopify status endpoints — SPEC-BOOK-EDIT-001
REQ-BKEDIT-016 through REQ-BKEDIT-034
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from book.models import (
    EtoileBookInfo,
    EtoileBookInven,
    EtoileShopifyProduct,
    Info,
    Inven,
    Shopify_product,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="shopify_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def make_book_with_shopify(sku: str = "ISBN-SHOPIFY-001") -> tuple:
    """Helper: create Inven + Info + Shopify_product."""
    inven = Inven.objects.create(
        inven_SKU=sku,
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="Shopify Test Book",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    shopify_product = Shopify_product.objects.create(
        inven=inven,
        product_id="PROD001",
        variant_id="VAR001",
        inventory_item_id="INV001",
        shopify_price=10000.0,
    )
    return inven, shopify_product


def make_book_with_etoile(sku: str = "ISBN-ETOILE-001") -> tuple:
    """Helper: create Inven + Info + EtoileBookInven + EtoileBookInfo + EtoileShopifyProduct."""
    inven = Inven.objects.create(
        inven_SKU=sku,
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="Etoile Test Book",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    etoile_inven = EtoileBookInven.objects.create(inven=inven)
    etoile_info = EtoileBookInfo.objects.create(
        etoile_inven=etoile_inven,
        name_en="Etoile Test Book EN",
        desc_en="Description EN",
        tags=["tag1", "tag2"],
    )
    etoile_shopify = EtoileShopifyProduct.objects.create(
        etoile_inven=etoile_inven,
        product_id="EPROD001",
        variant_id="EVAR001",
        inventory_item_id="EINV001",
        shopify_price=10000.0,
    )
    return inven, etoile_inven, etoile_info, etoile_shopify


# ---------------------------------------------------------------------------
# REQ-BKEDIT-016: PATCH /api/book/{id}/shopify-status/ — active success
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_shopify_status_to_active_success(auth_client, db):
    """PATCH shopify-status/ with action=active when service returns True must return 200."""
    inven, _ = make_book_with_shopify("ISBN-SHOPIFY-ACT-001")

    with patch("book.services.set_shopify_product_status_for_inven", return_value=True):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/shopify-status/",
            {"action": "active"},
            format="json",
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# REQ-BKEDIT-017: PATCH shopify-status/ — draft success
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_shopify_status_to_draft_success(auth_client, db):
    """PATCH shopify-status/ with action=draft when service returns True must return 200."""
    inven, _ = make_book_with_shopify("ISBN-SHOPIFY-DRF-001")

    with patch("book.services.set_shopify_product_status_for_inven", return_value=True):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/shopify-status/",
            {"action": "draft"},
            format="json",
        )
    assert resp.status_code == 200

    # On draft: status_of_shopify must be set to 12
    inven.refresh_from_db()
    assert inven.status_of_shopify == 12


# ---------------------------------------------------------------------------
# REQ-BKEDIT-018: PATCH shopify-status/ — API failure → 502
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_shopify_status_api_failure_returns_502(auth_client, db):
    """PATCH shopify-status/ when service returns False must return 502."""
    inven, _ = make_book_with_shopify("ISBN-SHOPIFY-ERR-001")

    with patch("book.services.set_shopify_product_status_for_inven", return_value=False):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/shopify-status/",
            {"action": "active"},
            format="json",
        )
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# REQ-BKEDIT-019: PATCH shopify-status/ — invalid action → 400
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_shopify_status_invalid_action_returns_400(auth_client, db):
    """PATCH shopify-status/ with invalid action must return 400."""
    inven, _ = make_book_with_shopify("ISBN-SHOPIFY-INV-001")

    resp = auth_client.patch(
        f"/api/book/{inven.id}/shopify-status/",
        {"action": "invalid"},
        format="json",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# REQ-BKEDIT-020: PATCH /api/book/{id}/etoile-shopify-status/ — active success
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_etoile_shopify_status_success(auth_client, db):
    """PATCH etoile-shopify-status/ with action=active when service returns True → 200."""
    inven, etoile_inven, _, _ = make_book_with_etoile("ISBN-ETL-ACT-001")

    with patch("book.services.set_shopify_product_status_for_etoile_inven", return_value=True):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/etoile-shopify-status/",
            {"action": "active"},
            format="json",
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# REQ-BKEDIT-021: PATCH etoile-shopify-status/ — no EtoileBookInven → 404
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_etoile_shopify_status_no_etoile_returns_404(auth_client, db):
    """PATCH etoile-shopify-status/ when no EtoileBookInven exists must return 404."""
    inven = Inven.objects.create(
        inven_SKU="ISBN-ETL-NOETOILE-001",
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="No Etoile Book",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )

    resp = auth_client.patch(
        f"/api/book/{inven.id}/etoile-shopify-status/",
        {"action": "active"},
        format="json",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# REQ-BKEDIT-022: PATCH /api/book/{id}/etoile-tags/ — success
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_etoile_tags_success(auth_client, db):
    """PATCH etoile-tags/ with valid tags when service returns True must return 200."""
    inven, etoile_inven, etoile_info, _ = make_book_with_etoile("ISBN-ETL-TAG-001")

    with patch("book.services.set_shopify_product_tags_for_etoile_inven", return_value=True):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/etoile-tags/",
            {"tags": ["tag-a", "tag-b"]},
            format="json",
        )
    assert resp.status_code == 200

    # Verify tags saved to DB
    etoile_info.refresh_from_db()
    assert "tag-a" in etoile_info.tags
    assert "tag-b" in etoile_info.tags


# ---------------------------------------------------------------------------
# REQ-BKEDIT-023: PATCH etoile-tags/ — Shopify sync fails → 207
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_etoile_tags_shopify_sync_fail_returns_207(auth_client, db):
    """PATCH etoile-tags/ when Shopify sync fails but DB saved must return 207."""
    inven, etoile_inven, etoile_info, _ = make_book_with_etoile("ISBN-ETL-TAG-002")

    with patch("book.services.set_shopify_product_tags_for_etoile_inven", return_value=False):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/etoile-tags/",
            {"tags": ["tag-x"]},
            format="json",
        )
    assert resp.status_code == 207

    # DB should still be updated despite Shopify sync failure
    etoile_info.refresh_from_db()
    assert "tag-x" in etoile_info.tags


# ---------------------------------------------------------------------------
# REQ-BKEDIT-024: PATCH etoile-tags/ — no EtoileBookInfo → 404
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_shopify_status_active_with_kyobo_category_sets_81(auth_client, db):
    """PATCH shopify-status/ active with kyobo_category1 set must set status_of_shopify=81."""
    inven = Inven.objects.create(
        inven_SKU="ISBN-KYOBO-001",
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="Kyobo Book",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="국내도서",  # kyobo_category1 is set
    )
    Shopify_product.objects.create(
        inven=inven,
        product_id="KYOBO_PROD_001",
        variant_id="KYOBO_VAR_001",
        inventory_item_id="KYOBO_INV_001",
        shopify_price=10000.0,
    )

    with patch("book.services.set_shopify_product_status_for_inven", return_value=True):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/shopify-status/",
            {"action": "active"},
            format="json",
        )
    assert resp.status_code == 200

    inven.refresh_from_db()
    assert inven.status_of_shopify == 81


@pytest.mark.django_db
def test_shopify_status_active_without_kyobo_category_sets_80(auth_client, db):
    """PATCH shopify-status/ active without kyobo_category1 must set status_of_shopify=80."""
    inven, _ = make_book_with_shopify("ISBN-SHOPIFY-ACT-002")

    with patch("book.services.set_shopify_product_status_for_inven", return_value=True):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/shopify-status/",
            {"action": "active"},
            format="json",
        )
    assert resp.status_code == 200

    inven.refresh_from_db()
    assert inven.status_of_shopify == 80


@pytest.mark.django_db
def test_etoile_shopify_status_invalid_action_returns_400(auth_client, db):
    """PATCH etoile-shopify-status/ with invalid action must return 400."""
    inven, etoile_inven, _, _ = make_book_with_etoile("ISBN-ETL-INV-001")

    resp = auth_client.patch(
        f"/api/book/{inven.id}/etoile-shopify-status/",
        {"action": "invalid"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_etoile_shopify_status_api_failure_returns_502(auth_client, db):
    """PATCH etoile-shopify-status/ when service returns False must return 502."""
    inven, etoile_inven, _, _ = make_book_with_etoile("ISBN-ETL-ERR-001")

    with patch("book.services.set_shopify_product_status_for_etoile_inven", return_value=False):
        resp = auth_client.patch(
            f"/api/book/{inven.id}/etoile-shopify-status/",
            {"action": "active"},
            format="json",
        )
    assert resp.status_code == 502


@pytest.mark.django_db
def test_etoile_tags_no_etoile_inven_returns_404(auth_client, db):
    """PATCH etoile-tags/ when no EtoileBookInven returns 404."""
    inven = Inven.objects.create(
        inven_SKU="ISBN-TAGS-NOINVEN-001",
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="No Etoile Inven Book",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )

    resp = auth_client.patch(
        f"/api/book/{inven.id}/etoile-tags/",
        {"tags": ["tag-x"]},
        format="json",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_etoile_tags_invalid_tags_type_returns_400(auth_client, db):
    """PATCH etoile-tags/ with non-list tags must return 400."""
    inven, etoile_inven, _, _ = make_book_with_etoile("ISBN-ETL-TAG-003")

    resp = auth_client.patch(
        f"/api/book/{inven.id}/etoile-tags/",
        {"tags": "not-a-list"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_etoile_tags_no_etoile_info_returns_404(auth_client, db):
    """PATCH etoile-tags/ when no EtoileBookInfo exists must return 404."""
    inven = Inven.objects.create(
        inven_SKU="ISBN-ETL-NOINFO-001",
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="No EtoileInfo Book",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    # EtoileBookInven exists but no EtoileBookInfo
    EtoileBookInven.objects.create(inven=inven)

    resp = auth_client.patch(
        f"/api/book/{inven.id}/etoile-tags/",
        {"tags": ["tag-x"]},
        format="json",
    )
    assert resp.status_code == 404
