"""
Shopify API service layer for book inventory management.
SPEC-BOOK-EDIT-001: REQ-BKEDIT-020 through REQ-BKEDIT-025
"""
import json
import urllib.error
import urllib.request

from book.models import EtoileShopifyProduct, Shopify_product


# @MX:ANCHOR: [AUTO] fetch_shopify_product_for_inven — primary lookup for Inven → Shopify product
# @MX:REASON: Called by BookShopifyStatusView and BookRetrieveView; fan_in >= 3
def fetch_shopify_product_for_inven(inven_id: int):
    """Return the first Shopify_product for the given inven_id, or None."""
    return Shopify_product.objects.filter(inven_id=inven_id).first()


def fetch_shopify_product_by_etoile_inven_id(etoile_inven_id: int):
    """Return the first EtoileShopifyProduct for the given etoile_inven_id, or None."""
    return EtoileShopifyProduct.objects.filter(etoile_inven_id=etoile_inven_id).first()


# @MX:ANCHOR: [AUTO] set_shopify_product_status_for_inven — Shopify status update entry point
# @MX:REASON: Called by BookShopifyStatusView; controls live Shopify product visibility
def set_shopify_product_status_for_inven(inven_id: int, status: str) -> bool:
    """
    Call Shopify API to set the product status for the Shopify product linked to inven_id.
    PUT https://{domain}/admin/api/{version}/products/{product_id}.json
    Returns True on success, False on failure (missing config or API error).
    """
    from django.conf import settings

    from book.shopify_client import SHOPIFY_API_VERSION

    domain = settings.SHOPIFY_BOOXEN_DOMAIN
    token = settings.SHOPIFY_BOOXEN_TOKEN

    if not domain or not token:
        return False

    product = fetch_shopify_product_for_inven(inven_id)
    if product is None:
        return False

    try:
        url = f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}/products/{product.product_id}.json"
        body = json.dumps({"product": {"id": product.product_id, "status": status}}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def set_shopify_product_status_for_etoile_inven(etoile_inven_id: int, status: str) -> bool:
    """
    Call Shopify API to set the product status for the EtoileShopifyProduct.
    PUT https://{domain}/admin/api/{version}/products/{product_id}.json
    Returns True on success, False on failure (missing config or API error).
    """
    from django.conf import settings

    from book.shopify_client import SHOPIFY_API_VERSION

    domain = settings.SHOPIFY_ETOILE_DOMAIN
    token = settings.SHOPIFY_ETOILE_TOKEN

    if not domain or not token:
        return False

    product = fetch_shopify_product_by_etoile_inven_id(etoile_inven_id)
    if product is None:
        return False

    try:
        url = f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}/products/{product.product_id}.json"
        body = json.dumps({"product": {"id": product.product_id, "status": status}}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def set_shopify_product_tags_for_etoile_inven(etoile_inven_id: int, tags: list) -> bool:
    """
    Sync tags to Shopify for the EtoileShopifyProduct.
    PUT /admin/api/{version}/products/{product_id}.json
    Returns True on success, False on failure (missing config or API error).
    """
    from django.conf import settings

    from book.shopify_client import SHOPIFY_API_VERSION

    domain = settings.SHOPIFY_ETOILE_DOMAIN
    token = settings.SHOPIFY_ETOILE_TOKEN

    if not domain or not token:
        return False

    product = fetch_shopify_product_by_etoile_inven_id(etoile_inven_id)
    if product is None:
        return False

    try:
        url = f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}/products/{product.product_id}.json"
        body = json.dumps({"product": {"id": product.product_id, "tags": ",".join(tags)}}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False
