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


def fetch_all_open_orders(domain, token):
    all_orders = []
    path = "orders.json?status=open&limit=250"
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


def _sync_single_order(order_data, store_type):
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


def sync_store(store_type):
    if store_type == "booksen":
        domain = settings.SHOPIFY_BOOKSEN_DOMAIN
        token = settings.SHOPIFY_BOOKSEN_TOKEN
    else:
        domain = settings.SHOPIFY_ETOILE_DOMAIN
        token = settings.SHOPIFY_ETOILE_TOKEN

    orders = fetch_all_open_orders(domain, token)
    synced_count = 0
    updated_count = 0
    for order_data in orders:
        result = _sync_single_order(order_data, store_type)
        if result == "created":
            synced_count += 1
        else:
            updated_count += 1
    return {"synced_count": synced_count, "updated_count": updated_count, "error": None}
