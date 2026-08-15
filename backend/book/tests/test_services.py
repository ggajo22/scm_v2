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

@pytest.fixture(autouse=True)
def shopify_settings(settings):
    """Give every test in this module known Shopify credentials.

    book/services.py reads django settings (SHOPIFY_BOOXEN_* for the inven
    functions, SHOPIFY_ETOILE_* for the etoile/tags ones), NOT os.environ.
    These tests previously monkeypatched SHOPIFY_STORE_URL and
    SHOPIFY_ACCESS_TOKEN — env vars nothing in the codebase reads — which had
    two consequences: the "configured" tests silently depended on whatever
    real credentials sat in the developer's .env (so they failed anywhere
    else, including CI), and the "no config" tests never actually removed the
    config, letting an unmocked request reach the real Shopify store on every
    local run. Setting the values the code truly consults fixes both.
    """
    settings.SHOPIFY_BOOXEN_DOMAIN = "booxen-test.myshopify.com"
    settings.SHOPIFY_BOOXEN_TOKEN = "booxen-test-token"
    settings.SHOPIFY_ETOILE_DOMAIN = "etoile-test.myshopify.com"
    settings.SHOPIFY_ETOILE_TOKEN = "etoile-test-token"


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
def test_set_shopify_status_for_inven_no_config_returns_false(inven_with_shopify, settings):
    """Returns False when the Shopify domain/token settings are blank."""
    settings.SHOPIFY_BOOXEN_DOMAIN = ""
    settings.SHOPIFY_BOOXEN_TOKEN = ""
    settings.SHOPIFY_ETOILE_DOMAIN = ""
    settings.SHOPIFY_ETOILE_TOKEN = ""
    inven, _ = inven_with_shopify
    result = set_shopify_product_status_for_inven(inven.id, "active")
    assert result is False


@pytest.mark.django_db
def test_set_shopify_status_for_inven_no_product_returns_false(db):
    """Returns False when no Shopify_product exists for the inven."""
    result = set_shopify_product_status_for_inven(99999, "active")
    assert result is False


@pytest.mark.django_db
def test_set_shopify_status_for_inven_api_success(inven_with_shopify):
    """Returns True when Shopify API returns 200."""
    inven, _ = inven_with_shopify

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = set_shopify_product_status_for_inven(inven.id, "active")
    assert result is True


@pytest.mark.django_db
def test_set_shopify_status_for_inven_api_error_returns_false(inven_with_shopify):
    """Returns False when urllib raises URLError."""
    import urllib.error
    inven, _ = inven_with_shopify

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection failed")):
        result = set_shopify_product_status_for_inven(inven.id, "active")
    assert result is False


# ---------------------------------------------------------------------------
# set_shopify_product_status_for_etoile_inven — no config → False
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_set_shopify_status_for_etoile_no_config_returns_false(etoile_with_shopify, settings):
    """Returns False when the Shopify domain/token settings are blank."""
    settings.SHOPIFY_BOOXEN_DOMAIN = ""
    settings.SHOPIFY_BOOXEN_TOKEN = ""
    settings.SHOPIFY_ETOILE_DOMAIN = ""
    settings.SHOPIFY_ETOILE_TOKEN = ""
    etoile_inven, _ = etoile_with_shopify
    result = set_shopify_product_status_for_etoile_inven(etoile_inven.id, "active")
    assert result is False


@pytest.mark.django_db
def test_set_shopify_status_for_etoile_api_success(etoile_with_shopify):
    """Returns True when Shopify API returns 200."""
    etoile_inven, _ = etoile_with_shopify

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = set_shopify_product_status_for_etoile_inven(etoile_inven.id, "active")
    assert result is True


@pytest.mark.django_db
def test_set_shopify_status_for_etoile_no_product_returns_false(db):
    """Returns False when no EtoileShopifyProduct exists."""
    result = set_shopify_product_status_for_etoile_inven(99999, "active")
    assert result is False


@pytest.mark.django_db
def test_set_shopify_status_for_etoile_api_error_returns_false(etoile_with_shopify):
    """Returns False when urllib raises URLError."""
    import urllib.error
    etoile_inven, _ = etoile_with_shopify

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection failed")):
        result = set_shopify_product_status_for_etoile_inven(etoile_inven.id, "active")
    assert result is False


# ---------------------------------------------------------------------------
# set_shopify_product_tags_for_etoile_inven
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_set_shopify_tags_no_config_returns_false(etoile_with_shopify, settings):
    """Returns False when the Shopify domain/token settings are blank."""
    settings.SHOPIFY_BOOXEN_DOMAIN = ""
    settings.SHOPIFY_BOOXEN_TOKEN = ""
    settings.SHOPIFY_ETOILE_DOMAIN = ""
    settings.SHOPIFY_ETOILE_TOKEN = ""
    etoile_inven, _ = etoile_with_shopify
    result = set_shopify_product_tags_for_etoile_inven(etoile_inven.id, ["tag1"])
    assert result is False


@pytest.mark.django_db
def test_set_shopify_tags_api_success(etoile_with_shopify):
    """Returns True when Shopify API returns 200."""
    etoile_inven, _ = etoile_with_shopify

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = set_shopify_product_tags_for_etoile_inven(etoile_inven.id, ["tag1", "tag2"])
    assert result is True


@pytest.mark.django_db
def test_set_shopify_tags_no_product_returns_false(db):
    """Returns False when no EtoileShopifyProduct exists."""
    result = set_shopify_product_tags_for_etoile_inven(99999, ["tag1"])
    assert result is False


@pytest.mark.django_db
def test_set_shopify_tags_api_error_returns_false(etoile_with_shopify):
    """Returns False when urllib raises URLError."""
    import urllib.error
    etoile_inven, _ = etoile_with_shopify

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection failed")):
        result = set_shopify_product_tags_for_etoile_inven(etoile_inven.id, ["tag1"])
    assert result is False
