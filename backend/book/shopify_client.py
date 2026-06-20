"""
Shopify Admin REST API client for live product info retrieval.
SPEC-SHOPIFY-INFO-001: REQ-SHPINFO-002, REQ-SHPINFO-003, REQ-SHPINFO-014
"""
import json
import urllib.error
import urllib.request

# @MX:NOTE: [AUTO] API version pinned as a constant — change here to upgrade globally
SHOPIFY_API_VERSION = "2024-10"

# Timeout per individual Shopify API call (seconds)
REQUEST_TIMEOUT = 5


def _get(domain: str, token: str, path: str) -> dict:
    """
    Make a GET request to the Shopify Admin API. Returns parsed JSON or raises.
    REQ-SHPINFO-003: uses urllib.request (stdlib), no third-party HTTP client.
    """
    url = f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}/{path}"
    req = urllib.request.Request(
        url,
        headers={"X-Shopify-Access-Token": token},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read())


def _fetch_product_info(domain: str, token: str, product_id: str, variant_id: str) -> dict:
    """
    Single API call to GET /products/{product_id}.json — returns status and weight.
    The product response includes variants with weight, so no separate variant call needed.
    When variant_id is "0" or absent, falls back to the first variant in the response.
    REQ-SHPINFO-010: product_id="0" treated as invalid.
    """
    if not product_id or product_id == "0":
        return {"status": None, "weight": None, "weight_unit": None, "error": "Invalid product_id"}
    try:
        data = _get(domain, token, f"products/{product_id}.json")
        product = data.get("product", {})
        variants = product.get("variants", [])

        # Match by variant_id if valid; otherwise use first variant
        target = None
        if variant_id and variant_id != "0":
            target = next((v for v in variants if str(v.get("id")) == str(variant_id)), None)
        if target is None:
            target = variants[0] if variants else None

        return {
            "status": product.get("status"),
            "weight": target.get("weight") if target else None,
            "weight_unit": target.get("weight_unit") if target else None,
            "error": None,
        }
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError) as exc:
        return {"status": None, "weight": None, "weight_unit": None, "error": str(exc)}


# @MX:NOTE: [AUTO] Single products API call returns both status and variant weight.
# variant_id="0" (DB default) falls back to first variant — no separate variant endpoint needed.
def fetch_store_live_info(
    domain: str, token: str, product_id: str, variant_id: str
) -> dict:
    """
    Fetch product status and weight for one store via a single API call.
    Returns dict with keys: status, weight, weight_unit, error.
    REQ-SHPINFO-002: product and variant data from GET /products/{id}.json.
    REQ-SHPINFO-014: API errors surface as error field; caller always gets HTTP 200.
    """
    if not domain or not token:
        return {
            "status": None,
            "weight": None,
            "weight_unit": None,
            "error": "Store credentials not configured",
        }
    return _fetch_product_info(domain, token, product_id, variant_id)
