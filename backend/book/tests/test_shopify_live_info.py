"""
Tests for Shopify live info endpoint — SPEC-SHOPIFY-INFO-001
REQ-SHPINFO-001 through REQ-SHPINFO-014
"""

import json
from unittest.mock import MagicMock, patch

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

URL_TEMPLATE = "/api/book/{pk}/shopify-live-info/"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="live_info_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def make_full_book(sku: str = "ISBN-LIVE-001") -> tuple:
    """Create Inven + Info + Shopify_product + EtoileBookInven + EtoileBookInfo + EtoileShopifyProduct."""  # noqa: E501
    inven = Inven.objects.create(
        inven_SKU=sku,
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="Live Info Test Book",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    booksen_product = Shopify_product.objects.create(
        inven=inven,
        product_id="PROD001",
        variant_id="VAR001",
        inventory_item_id="INV001",
        shopify_price=10000.0,
    )
    etoile_inven = EtoileBookInven.objects.create(inven=inven)
    EtoileBookInfo.objects.create(
        etoile_inven=etoile_inven,
        name_en="",
        desc_en="",
        tags=[],
    )
    etoile_product = EtoileShopifyProduct.objects.create(
        etoile_inven=etoile_inven,
        product_id="EPROD001",
        variant_id="EVAR001",
        inventory_item_id="EINV001",
        shopify_price=10000.0,
    )
    return inven, booksen_product, etoile_inven, etoile_product


def _make_urlopen_mock(
    product_status: str = "active",
    weight: float = 500.0,
    weight_unit: str = "g",
):
    """Return a side_effect for urllib.request.urlopen that returns product data with variants.
    The products endpoint response includes variants so both status and weight come from one call.
    """

    def fake_urlopen(req, timeout=5):
        body = json.dumps({
            "product": {
                "status": product_status,
                "variants": [{"id": 1, "weight": weight, "weight_unit": weight_unit}],
            }
        }).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    return fake_urlopen


# ---------------------------------------------------------------------------
# REQ-SHPINFO-004: unauthenticated request returns 401
# ---------------------------------------------------------------------------

def test_unauthenticated_returns_401(db):
    client = APIClient()
    url = URL_TEMPLATE.format(pk=1)
    response = client.get(url)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# REQ-SHPINFO-005: non-existent pk returns 404
# ---------------------------------------------------------------------------

def test_inven_not_found_returns_404(auth_client):
    url = URL_TEMPLATE.format(pk=999999)
    response = auth_client.get(url)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# REQ-SHPINFO-001, REQ-SHPINFO-002: both stores registered, API returns normal data → HTTP 200
# ---------------------------------------------------------------------------

@patch("book.shopify_client.urllib.request.urlopen")
def test_both_stores_registered_normal_response(mock_urlopen, auth_client, db):
    inven, booksen_product, etoile_inven, etoile_product = make_full_book("ISBN-BOTH-001")
    mock_urlopen.side_effect = _make_urlopen_mock("active", 500.0, "g")

    url = URL_TEMPLATE.format(pk=inven.pk)
    with patch("django.conf.settings.SHOPIFY_BOOKSEN_DOMAIN", "booksen.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_TOKEN", "tok1"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_DOMAIN", "etoile.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_TOKEN", "tok2"):
        response = auth_client.get(url)

    assert response.status_code == 200
    data = response.json()

    # Booksen store
    assert "booksen" in data
    bs = data["booksen"]
    assert bs["registered"] is True
    assert bs["product_id"] == "PROD001"
    assert bs["variant_id"] == "VAR001"
    assert bs["status"] == "active"
    assert bs["weight"] == 500.0
    assert bs["weight_unit"] == "g"
    assert bs["error"] is None

    # Etoile store
    assert "etoile" in data
    et = data["etoile"]
    assert et["registered"] is True
    assert et["product_id"] == "EPROD001"
    assert et["variant_id"] == "EVAR001"
    assert et["status"] == "active"
    assert et["weight"] == 500.0
    assert et["weight_unit"] == "g"
    assert et["error"] is None


# ---------------------------------------------------------------------------
# REQ-SHPINFO-006: booksen not registered → registered=False, all fields null
# ---------------------------------------------------------------------------

def test_booksen_not_registered(auth_client, db):
    inven = Inven.objects.create(
        inven_SKU="ISBN-NOBS-001",
        vendor="v",
        store="s",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="No Booksen",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    # No Shopify_product for booksen, but etoile exists
    etoile_inven = EtoileBookInven.objects.create(inven=inven)
    EtoileBookInfo.objects.create(etoile_inven=etoile_inven, name_en="", desc_en="", tags=[])
    EtoileShopifyProduct.objects.create(
        etoile_inven=etoile_inven,
        product_id="EPROD999",
        variant_id="EVAR999",
        inventory_item_id="EINV999",
        shopify_price=5000.0,
    )

    url = URL_TEMPLATE.format(pk=inven.pk)
    with patch("book.shopify_client.urllib.request.urlopen") as mock_urlopen, \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_DOMAIN", "booksen.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_TOKEN", "tok1"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_DOMAIN", "etoile.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_TOKEN", "tok2"):
        mock_urlopen.side_effect = _make_urlopen_mock("active", 300.0, "g")
        response = auth_client.get(url)

    assert response.status_code == 200
    data = response.json()

    bs = data["booksen"]
    assert bs["registered"] is False
    assert bs["product_id"] is None
    assert bs["variant_id"] is None
    assert bs["status"] is None
    assert bs["weight"] is None
    assert bs["weight_unit"] is None
    assert bs["error"] is None


# ---------------------------------------------------------------------------
# REQ-SHPINFO-007: etoile not registered → registered=False, all fields null
# ---------------------------------------------------------------------------

@patch("book.shopify_client.urllib.request.urlopen")
def test_etoile_not_registered(mock_urlopen, auth_client, db):
    inven = Inven.objects.create(
        inven_SKU="ISBN-NOET-001",
        vendor="v",
        store="s",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="No Etoile",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    Shopify_product.objects.create(
        inven=inven,
        product_id="PROD777",
        variant_id="VAR777",
        inventory_item_id="INV777",
        shopify_price=8000.0,
    )
    # No EtoileBookInven / EtoileShopifyProduct

    mock_urlopen.side_effect = _make_urlopen_mock("draft", 250.0, "g")
    url = URL_TEMPLATE.format(pk=inven.pk)
    with patch("django.conf.settings.SHOPIFY_BOOKSEN_DOMAIN", "booksen.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_TOKEN", "tok1"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_DOMAIN", "etoile.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_TOKEN", "tok2"):
        response = auth_client.get(url)

    assert response.status_code == 200
    data = response.json()

    et = data["etoile"]
    assert et["registered"] is False
    assert et["product_id"] is None
    assert et["variant_id"] is None
    assert et["status"] is None
    assert et["weight"] is None
    assert et["weight_unit"] is None
    assert et["error"] is None


# ---------------------------------------------------------------------------
# REQ-SHPINFO-009: Booksen API error → booksen.error is non-null, etoile normal
# ---------------------------------------------------------------------------

def test_booksen_api_error(auth_client, db):
    import urllib.error

    inven, booksen_product, etoile_inven, etoile_product = make_full_book("ISBN-ERR-001")

    def selective_error(req, timeout=5):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        # All booksen calls fail, etoile calls succeed
        if "booksen" in url:
            raise urllib.error.URLError("Connection refused")
        # Etoile products call succeeds (variants included in product response)
        body = json.dumps({
            "product": {
                "status": "active",
                "variants": [{"id": 1, "weight": 400.0, "weight_unit": "g"}],
            }
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    url = URL_TEMPLATE.format(pk=inven.pk)
    with patch("book.shopify_client.urllib.request.urlopen", side_effect=selective_error), \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_DOMAIN", "booksen.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_TOKEN", "tok1"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_DOMAIN", "etoile.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_TOKEN", "tok2"):
        response = auth_client.get(url)

    assert response.status_code == 200
    data = response.json()
    # Booksen should have error
    assert data["booksen"]["error"] is not None
    assert data["booksen"]["registered"] is True
    # Etoile should be normal
    assert data["etoile"]["error"] is None
    assert data["etoile"]["status"] == "active"


# ---------------------------------------------------------------------------
# REQ-SHPINFO-010: variant_id="0" → falls back to first variant from product response
# ---------------------------------------------------------------------------

@patch("book.shopify_client.urllib.request.urlopen")
def test_variant_id_zero_uses_first_variant(mock_urlopen, auth_client, db):
    """variant_id="0" (DB default) should still return weight via products endpoint fallback."""
    inven = Inven.objects.create(
        inven_SKU="ISBN-VAR0-001",
        vendor="v",
        store="s",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="Zero Variant",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    Shopify_product.objects.create(
        inven=inven,
        product_id="PROD_REAL",
        variant_id="0",  # DB default — products endpoint fallback should provide weight
        inventory_item_id="INV_REAL",
        shopify_price=10000.0,
    )

    mock_urlopen.side_effect = _make_urlopen_mock("active", 300.0, "g")
    url = URL_TEMPLATE.format(pk=inven.pk)
    with patch("django.conf.settings.SHOPIFY_BOOKSEN_DOMAIN", "booksen.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_TOKEN", "tok1"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_DOMAIN", ""), \
         patch("django.conf.settings.SHOPIFY_ETOILE_TOKEN", ""):
        response = auth_client.get(url)

    assert response.status_code == 200
    data = response.json()
    bs = data["booksen"]
    assert bs["registered"] is True
    assert bs["status"] == "active"
    assert bs["weight"] == 300.0
    assert bs["weight_unit"] == "g"
    assert bs["error"] is None  # first variant used as fallback — no error


# ---------------------------------------------------------------------------
# REQ-SHPINFO-011: product_id="0" → error field set
# ---------------------------------------------------------------------------

@patch("book.shopify_client.urllib.request.urlopen")
def test_product_id_zero_returns_error(mock_urlopen, auth_client, db):
    inven = Inven.objects.create(
        inven_SKU="ISBN-PROD0-001",
        vendor="v",
        store="s",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="Zero Product",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    Shopify_product.objects.create(
        inven=inven,
        product_id="0",  # invalid — should trigger error
        variant_id="VAR_REAL",
        inventory_item_id="INV_REAL",
        shopify_price=10000.0,
    )

    mock_urlopen.side_effect = _make_urlopen_mock("active", 300.0, "g")
    url = URL_TEMPLATE.format(pk=inven.pk)
    with patch("django.conf.settings.SHOPIFY_BOOKSEN_DOMAIN", "booksen.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_TOKEN", "tok1"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_DOMAIN", ""), \
         patch("django.conf.settings.SHOPIFY_ETOILE_TOKEN", ""):
        response = auth_client.get(url)

    assert response.status_code == 200
    data = response.json()
    bs = data["booksen"]
    assert bs["registered"] is True
    # status fetch failed due to invalid product_id
    assert bs["error"] is not None


# ---------------------------------------------------------------------------
# REQ-SHPINFO-012: both stores unregistered → both registered=False
# ---------------------------------------------------------------------------

def test_both_stores_unregistered(auth_client, db):
    inven = Inven.objects.create(
        inven_SKU="ISBN-NONE-001",
        vendor="v",
        store="s",
        status_of_shopify=100,
    )
    Info.objects.create(
        inven=inven,
        name="No Shopify",
        price_sale=10000.0,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
        kyobo_category1="",
    )
    # No Shopify_product and no EtoileShopifyProduct

    url = URL_TEMPLATE.format(pk=inven.pk)
    response = auth_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["booksen"]["registered"] is False
    assert data["etoile"]["registered"] is False


# ---------------------------------------------------------------------------
# REQ-SHPINFO-013: Shopify tokens must not appear in response
# ---------------------------------------------------------------------------

@patch("book.shopify_client.urllib.request.urlopen")
def test_tokens_not_in_response(mock_urlopen, auth_client, db):
    inven, booksen_product, etoile_inven, etoile_product = make_full_book("ISBN-TOK-001")
    mock_urlopen.side_effect = _make_urlopen_mock("active", 500.0, "g")

    url = URL_TEMPLATE.format(pk=inven.pk)
    secret_token = "super-secret-token-value-12345"
    with patch("django.conf.settings.SHOPIFY_BOOKSEN_DOMAIN", "booksen.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_BOOKSEN_TOKEN", secret_token), \
         patch("django.conf.settings.SHOPIFY_ETOILE_DOMAIN", "etoile.myshopify.com"), \
         patch("django.conf.settings.SHOPIFY_ETOILE_TOKEN", "etoile-secret-999"):
        response = auth_client.get(url)

    assert response.status_code == 200
    response_text = response.content.decode()
    assert secret_token not in response_text
    assert "etoile-secret-999" not in response_text


# ---------------------------------------------------------------------------
# REQ-SHPINFO-014: HTTP 500 must not be returned even on API errors
# ---------------------------------------------------------------------------

def test_api_error_returns_200_not_500(auth_client, db):
    import urllib.error

    inven, _, _, _ = make_full_book("ISBN-500-001")

    url = URL_TEMPLATE.format(pk=inven.pk)
    url_error = urllib.error.URLError("timeout")
    with (
        patch("book.shopify_client.urllib.request.urlopen", side_effect=url_error),
        patch("django.conf.settings.SHOPIFY_BOOKSEN_DOMAIN", "booksen.myshopify.com"),
        patch("django.conf.settings.SHOPIFY_BOOKSEN_TOKEN", "tok"),
        patch("django.conf.settings.SHOPIFY_ETOILE_DOMAIN", "etoile.myshopify.com"),
        patch("django.conf.settings.SHOPIFY_ETOILE_TOKEN", "tok2"),
    ):
        response = auth_client.get(url)

    assert response.status_code == 200
    data = response.json()
    # errors captured in error field, not HTTP 500
    assert "booksen" in data
    assert "etoile" in data
