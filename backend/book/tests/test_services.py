"""
Unit tests for book/services.py — SPEC-BOOK-EDIT-001
Tests service layer functions with mocked external dependencies.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from book.models import EtoileBookInven, EtoileShopifyProduct, Inven, Shopify_product
from book.services import (
    fetch_shopify_product_by_etoile_inven_id,
    fetch_shopify_product_for_inven,
    set_shopify_product_status_for_etoile_inven,
    set_shopify_product_status_for_inven,
    set_shopify_product_tags_for_etoile_inven,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def inven_with_shopify(db):
    """Create an Inven with an associated Shopify_product."""
    from book.models import Info
    inven = Inven.objects.create(
        inven_SKU="ISBN-SVC-001",
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven, name="Service Test Book", price_sale=10000.0,
        status="active", useruse1="", useruse2="", retyn="N", kyobo_category1="",
    )
    product = Shopify_product.objects.create(
        inven=inven,
        product_id="SVC_PROD_001",
        variant_id="SVC_VAR_001",
        inventory_item_id="SVC_INV_001",
        shopify_price=10000.0,
    )
    return inven, product


@pytest.fixture
def etoile_with_shopify(db):
    """Create an EtoileBookInven with EtoileShopifyProduct."""
    from book.models import Info
    inven = Inven.objects.create(
        inven_SKU="ISBN-ETL-SVC-001",
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven, name="Etoile Service Book", price_sale=10000.0,
        status="active", useruse1="", useruse2="", retyn="N", kyobo_category1="",
    )
    etoile_inven = EtoileBookInven.objects.create(inven=inven)
    product = EtoileShopifyProduct.objects.create(
        etoile_inven=etoile_inven,
        product_id="ETL_PROD_001",
        variant_id="ETL_VAR_001",
        inventory_item_id="ETL_INV_001",
        shopify_price=10000.0,
    )
    return etoile_inven, product


# ---------------------------------------------------------------------------
# fetch_shopify_product_for_inven
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_fetch_shopify_product_for_inven_found(inven_with_shopify):
    """fetch_shopify_product_for_inven returns product when it exists."""
    inven, product = inven_with_shopify
    result = fetch_shopify_product_for_inven(inven.id)
    assert result is not None
    assert result.product_id == "SVC_PROD_001"


@pytest.mark.django_db
def test_fetch_shopify_product_for_inven_not_found(db):
    """fetch_shopify_product_for_inven returns None when no product exists."""
    result = fetch_shopify_product_for_inven(99999)
    assert result is None


# ---------------------------------------------------------------------------
# fetch_shopify_product_by_etoile_inven_id
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_fetch_shopify_product_by_etoile_inven_id_found(etoile_with_shopify):
    """fetch_shopify_product_by_etoile_inven_id returns product when it exists."""
    etoile_inven, product = etoile_with_shopify
    result = fetch_shopify_product_by_etoile_inven_id(etoile_inven.id)
    assert result is not None
    assert result.product_id == "ETL_PROD_001"


@pytest.mark.django_db
def test_fetch_shopify_product_by_etoile_inven_id_not_found(db):
    """fetch_shopify_product_by_etoile_inven_id returns None when no product exists."""
    result = fetch_shopify_product_by_etoile_inven_id(99999)
    assert result is None


# ---------------------------------------------------------------------------
# set_shopify_product_status_for_inven — no config → False
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_set_shopify_status_for_inven_no_config_returns_false(inven_with_shopify, monkeypatch):
    """Returns False when SHOPIFY_STORE_URL is not configured."""
    monkeypatch.delenv("SHOPIFY_STORE_URL", raising=False)
    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
    inven, _ = inven_with_shopify
    result = set_shopify_product_status_for_inven(inven.id, "active")
    assert result is False


@pytest.mark.django_db
def test_set_shopify_status_for_inven_no_product_returns_false(db, monkeypatch):
    """Returns False when no Shopify_product exists for the inven."""
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    result = set_shopify_product_status_for_inven(99999, "active")
    assert result is False


@pytest.mark.django_db
def test_set_shopify_status_for_inven_api_success(inven_with_shopify, monkeypatch):
    """Returns True when Shopify API returns 200."""
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    inven, _ = inven_with_shopify

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = set_shopify_product_status_for_inven(inven.id, "active")
    assert result is True


@pytest.mark.django_db
def test_set_shopify_status_for_inven_api_error_returns_false(inven_with_shopify, monkeypatch):
    """Returns False when urllib raises URLError."""
    import urllib.error
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    inven, _ = inven_with_shopify

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection failed")):
        result = set_shopify_product_status_for_inven(inven.id, "active")
    assert result is False


# ---------------------------------------------------------------------------
# set_shopify_product_status_for_etoile_inven — no config → False
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_set_shopify_status_for_etoile_no_config_returns_false(etoile_with_shopify, monkeypatch):
    """Returns False when SHOPIFY_STORE_URL is not configured."""
    monkeypatch.delenv("SHOPIFY_STORE_URL", raising=False)
    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
    etoile_inven, _ = etoile_with_shopify
    result = set_shopify_product_status_for_etoile_inven(etoile_inven.id, "active")
    assert result is False


@pytest.mark.django_db
def test_set_shopify_status_for_etoile_api_success(etoile_with_shopify, monkeypatch):
    """Returns True when Shopify API returns 200."""
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    etoile_inven, _ = etoile_with_shopify

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = set_shopify_product_status_for_etoile_inven(etoile_inven.id, "active")
    assert result is True


@pytest.mark.django_db
def test_set_shopify_status_for_etoile_no_product_returns_false(db, monkeypatch):
    """Returns False when no EtoileShopifyProduct exists."""
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    result = set_shopify_product_status_for_etoile_inven(99999, "active")
    assert result is False


@pytest.mark.django_db
def test_set_shopify_status_for_etoile_api_error_returns_false(etoile_with_shopify, monkeypatch):
    """Returns False when urllib raises URLError."""
    import urllib.error
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    etoile_inven, _ = etoile_with_shopify

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection failed")):
        result = set_shopify_product_status_for_etoile_inven(etoile_inven.id, "active")
    assert result is False


# ---------------------------------------------------------------------------
# set_shopify_product_tags_for_etoile_inven
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_set_shopify_tags_no_config_returns_false(etoile_with_shopify, monkeypatch):
    """Returns False when SHOPIFY_STORE_URL is not configured."""
    monkeypatch.delenv("SHOPIFY_STORE_URL", raising=False)
    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
    etoile_inven, _ = etoile_with_shopify
    result = set_shopify_product_tags_for_etoile_inven(etoile_inven.id, ["tag1"])
    assert result is False


@pytest.mark.django_db
def test_set_shopify_tags_api_success(etoile_with_shopify, monkeypatch):
    """Returns True when Shopify API returns 200."""
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    etoile_inven, _ = etoile_with_shopify

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = set_shopify_product_tags_for_etoile_inven(etoile_inven.id, ["tag1", "tag2"])
    assert result is True


@pytest.mark.django_db
def test_set_shopify_tags_no_product_returns_false(db, monkeypatch):
    """Returns False when no EtoileShopifyProduct exists."""
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    result = set_shopify_product_tags_for_etoile_inven(99999, ["tag1"])
    assert result is False


@pytest.mark.django_db
def test_set_shopify_tags_api_error_returns_false(etoile_with_shopify, monkeypatch):
    """Returns False when urllib raises URLError."""
    import urllib.error
    monkeypatch.setenv("SHOPIFY_STORE_URL", "https://test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test-token")
    etoile_inven, _ = etoile_with_shopify

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection failed")):
        result = set_shopify_product_tags_for_etoile_inven(etoile_inven.id, ["tag1"])
    assert result is False
