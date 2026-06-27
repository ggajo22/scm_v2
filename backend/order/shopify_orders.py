import json
import re
import urllib.request
import urllib.error

from django.conf import settings

SHOPIFY_API_VERSION = "2024-10"
REQUEST_TIMEOUT = 30


def _get_with_headers(domain, token, path):
    url = f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}/{path}"
    req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": token})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        body = json.loads(resp.read())
        headers = dict(resp.headers)
        return body, headers


def _parse_next_page_info(link_header):
    if not link_header:
        return None
    match = re.search(r'<[^>]+[?&]page_info=([^&>]+)[^>]*>;\s*rel="next"', link_header)
    return match.group(1) if match else None


def fetch_all_open_orders(domain, token, updated_at_min=None):
    all_orders = []
    base = "orders.json?status=open&limit=250"
    if updated_at_min:
        base += f"&updated_at_min={updated_at_min}"
    path = base
    while path:
        body, headers = _get_with_headers(domain, token, path)
        orders = body.get("orders", [])
        all_orders.extend(orders)
        link = headers.get("Link") or headers.get("link")
        page_info = _parse_next_page_info(link)
        path = f"orders.json?limit=250&page_info={page_info}" if page_info else None
    return all_orders


def _decimal_or_none(value):
    if value is None or value == "":
        return None
    return value


def _build_fulfillment_location_data(domain, token, order_id):
    """Return (order_location, line_item_location_map) from fulfillment_orders API.

    order_location: unique location codes joined with "/" (e.g. "NJ" or "NJ/CA")
    line_item_location_map: {shopify_line_item_id: location_code}
    Returns ("", {}) on any error.
    """
    try:
        body, _ = _get_with_headers(domain, token, f"orders/{order_id}/fulfillment_orders.json")
        fulfillment_orders = body.get("fulfillment_orders", [])

        line_item_map = {}
        seen = []

        for fo in fulfillment_orders:
            name = fo.get("assigned_location", {}).get("name", "")
            parts = name.split("_")
            loc_code = parts[1] if len(parts) > 1 else ""

            if loc_code and loc_code not in seen:
                seen.append(loc_code)

            for fo_li in fo.get("line_items", []):
                line_item_id = fo_li.get("line_item_id")
                if line_item_id:
                    line_item_map[line_item_id] = loc_code

        return "/".join(seen), line_item_map
    except Exception:
        return "", {}


def _sync_single_order(order_data, store_type, location_code="", line_item_location_map=None):
    from .models import (
        BillingAddress,
        Customer,
        LineItem,
        Order,
        Refund,
        ShippingAddress,
        ShippingLine,
    )

    customer_obj = None
    customer_data = order_data.get("customer")
    if customer_data and customer_data.get("id"):
        customer_obj, _ = Customer.objects.update_or_create(
            shopify_customer_id=customer_data["id"],
            defaults={
                "email": customer_data.get("email"),
                "first_name": customer_data.get("first_name"),
                "last_name": customer_data.get("last_name"),
                "phone": customer_data.get("phone"),
            },
        )

    shipping_set = order_data.get("total_shipping_price_set")
    order_obj, created = Order.objects.update_or_create(
        shopify_order_id=order_data["id"],
        store_type=store_type,
        defaults={
            "order_number": order_data.get("order_number"),
            "name": order_data.get("name"),
            "email": order_data.get("email"),
            "phone": order_data.get("phone"),
            "financial_status": order_data.get("financial_status"),
            "fulfillment_status": order_data.get("fulfillment_status"),
            "status": order_data.get("financial_status"),
            "total_price": _decimal_or_none(order_data.get("total_price")),
            "subtotal_price": _decimal_or_none(order_data.get("subtotal_price")),
            "total_tax": _decimal_or_none(order_data.get("total_tax")),
            "total_discounts": _decimal_or_none(order_data.get("total_discounts")),
            "total_shipping_price_set": json.dumps(shipping_set) if shipping_set else None,
            "currency": order_data.get("currency"),
            "gateway": order_data.get("gateway"),
            "note": order_data.get("note"),
            "tags": order_data.get("tags"),
            "cancel_reason": order_data.get("cancel_reason"),
            "source_name": order_data.get("source_name"),
            "shopify_created_at": order_data.get("created_at"),
            "shopify_updated_at": order_data.get("updated_at"),
            "closed_at": order_data.get("closed_at"),
            "cancelled_at": order_data.get("cancelled_at"),
            "processed_at": order_data.get("processed_at"),
            "customer": customer_obj,
            "location": location_code,
        },
    )

    shipping_addr = order_data.get("shipping_address")
    if shipping_addr:
        ShippingAddress.objects.update_or_create(
            order=order_obj,
            defaults={k: shipping_addr.get(k) for k in [
                "name", "first_name", "last_name", "address1", "address2",
                "city", "province", "province_code", "country", "country_code", "zip", "phone",
            ]},
        )

    billing_addr = order_data.get("billing_address")
    if billing_addr:
        BillingAddress.objects.update_or_create(
            order=order_obj,
            defaults={k: billing_addr.get(k) for k in [
                "name", "first_name", "last_name", "address1", "address2",
                "city", "province", "province_code", "country", "country_code", "zip", "phone",
            ]},
        )

    order_obj.line_items.all().delete()
    line_items = [
        LineItem(
            order=order_obj,
            shopify_line_item_id=li["id"],
            product_id=li.get("product_id"),
            variant_id=li.get("variant_id"),
            title=li.get("title"),
            variant_title=li.get("variant_title"),
            sku=li.get("sku"),
            quantity=li.get("quantity"),
            price=_decimal_or_none(li.get("price")),
            total_discount=_decimal_or_none(li.get("total_discount")),
            fulfillment_status=li.get("fulfillment_status"),
            vendor=li.get("vendor"),
            grams=li.get("grams"),
            location=line_item_location_map.get(li["id"], "") if line_item_location_map else "",
        )
        for li in order_data.get("line_items", [])
    ]
    if line_items:
        LineItem.objects.bulk_create(line_items)

    order_obj.shipping_lines.all().delete()
    shipping_lines = [
        ShippingLine(
            order=order_obj,
            shopify_shipping_line_id=sl["id"],
            title=sl.get("title"),
            code=sl.get("code"),
            price=_decimal_or_none(sl.get("price")),
            source=sl.get("source"),
        )
        for sl in order_data.get("shipping_lines", [])
    ]
    if shipping_lines:
        ShippingLine.objects.bulk_create(shipping_lines)

    order_obj.refunds.all().delete()
    for refund_data in order_data.get("refunds", []):
        refund_line_items = refund_data.get("refund_line_items", [])
        first_rli = refund_line_items[0] if refund_line_items else {}
        Refund.objects.update_or_create(
            order=order_obj,
            shopify_refund_id=refund_data["id"],
            defaults={
                "note": refund_data.get("note"),
                "shopify_created_at": refund_data.get("created_at"),
                "line_item_id": first_rli.get("line_item_id"),
                "quantity": first_rli.get("quantity"),
                "subtotal": _decimal_or_none(first_rli.get("subtotal")),
                "total_tax": _decimal_or_none(first_rli.get("total_tax")),
            },
        )

    return "created" if created else "updated"


def sync_single_order_from_shopify(shopify_order_id: int, store_type: str) -> dict:
    """Fetch a single order from Shopify and sync it to the DB. Returns the raw order dict.

    Raises urllib.error.HTTPError or urllib.error.URLError on failure — callers handle exceptions.
    """
    # @MX:ANCHOR: [AUTO] sync_single_order_from_shopify — called by OrderResyncView and future webhooks
    # @MX:REASON: public API boundary; fan_in >= 3 expected (view, tests, future webhook handler)
    if store_type == "gimssine":
        domain = settings.SHOPIFY_GIMSSINE_DOMAIN
        token = settings.SHOPIFY_GIMSSINE_TOKEN
    else:
        domain = settings.SHOPIFY_ETOILE_DOMAIN
        token = settings.SHOPIFY_ETOILE_TOKEN

    body, _ = _get_with_headers(domain, token, f"orders/{shopify_order_id}.json")
    order_data = body["order"]
    order_location, line_item_map = _build_fulfillment_location_data(domain, token, shopify_order_id)
    _sync_single_order(order_data, store_type, location_code=order_location, line_item_location_map=line_item_map)
    return order_data


def sync_store(store_type):
    from .models import LineItem, Order

    if store_type == "gimssine":
        domain = settings.SHOPIFY_GIMSSINE_DOMAIN
        token = settings.SHOPIFY_GIMSSINE_TOKEN
    else:
        domain = settings.SHOPIFY_ETOILE_DOMAIN
        token = settings.SHOPIFY_ETOILE_TOKEN

    last_updated = (
        Order.objects.filter(store_type=store_type)
        .order_by("-shopify_updated_at")
        .values_list("shopify_updated_at", flat=True)
        .first()
    )
    updated_at_min = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ") if last_updated else None

    orders = fetch_all_open_orders(domain, token, updated_at_min=updated_at_min)
    if not orders:
        return {"synced_count": 0, "updated_count": 0, "error": None, "updated_at_min": updated_at_min}

    shopify_ids = [o["id"] for o in orders]

    # One DB query: existing order-level locations
    existing_order_locations = {
        row["shopify_order_id"]: row["location"]
        for row in Order.objects.filter(
            shopify_order_id__in=shopify_ids, store_type=store_type
        ).values("shopify_order_id", "location")
    }

    # One DB query: existing line-item-level locations
    existing_line_item_locs: dict = {}
    for li in LineItem.objects.filter(
        order__shopify_order_id__in=shopify_ids,
        order__store_type=store_type,
    ).values("order__shopify_order_id", "shopify_line_item_id", "location"):
        existing_line_item_locs.setdefault(li["order__shopify_order_id"], {})[
            li["shopify_line_item_id"]
        ] = li["location"]

    synced_count = 0
    updated_count = 0
    for order_data in orders:
        shopify_id = order_data["id"]
        if shopify_id in existing_order_locations:
            # Existing order: reuse stored locations, skip Shopify fulfillment API call
            order_location = existing_order_locations[shopify_id] or ""
            line_item_map = existing_line_item_locs.get(shopify_id) or {}
        else:
            # New order: fetch fulfillment location from Shopify
            order_location, line_item_map = _build_fulfillment_location_data(domain, token, shopify_id)

        result = _sync_single_order(order_data, store_type, location_code=order_location, line_item_location_map=line_item_map)
        if result == "created":
            synced_count += 1
        else:
            updated_count += 1
    return {
        "synced_count": synced_count,
        "updated_count": updated_count,
        "error": None,
        "updated_at_min": updated_at_min,
    }
