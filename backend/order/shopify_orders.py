import json
import re
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.db.utils import OperationalError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from book.models import Inven

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


def _build_title_map(isbn_list: list[str]) -> dict[str, str | None]:
    """Batch-query real book titles for member ISBNs (once per order sync).

    Mirrors the same Inven/Info join pattern as
    shopify_sku_set_views._build_title_map. Returns {isbn: title_or_None};
    ISBNs with no matching Inven/Info row are simply omitted (lookup via
    .get() then returns None).
    """
    if not isbn_list:
        return {}
    rows = (
        Inven.objects.filter(inven_SKU__in=isbn_list)
        .select_related("info")
        .values("inven_SKU", "info__name")
    )
    return {row["inven_SKU"]: row["info__name"] for row in rows}


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
        ShopifySkuSetMapping,
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
            # SPEC-ORDER-011 REQ-LOGI-011: "status" intentionally excluded —
            # it is now the logistics_status aggregate (REQ-LOGI-008),
            # recomputed only by purchase_order_views._recompute_order_aggregates().
            # Shopify sync must never overwrite it with financial_status.
            # SPEC-ORDER-012 REQ-RTS-005: "ready_to_ship" is likewise never
            # Shopify-sourced. It needs no explicit exclusion line here (it
            # was never added to this defaults dict in the first place) — it
            # is recomputed only by the same _recompute_order_aggregates().
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

    # SPEC-SHOPIFY-SKU-SET-002 REQ-SKUSET2-003: load the full bundle_sku -> member
    # ISBN mapping once per order sync (never per line item) to avoid N+1 queries.
    bundle_map: dict[str, list[str]] = {}
    bundle_mapping_rows = ShopifySkuSetMapping.objects.order_by("sort_order").values(
        "bundle_sku", "member_isbn"
    )
    for mapping in bundle_mapping_rows:
        bundle_map.setdefault(mapping["bundle_sku"], []).append(mapping["member_isbn"])

    # Title-data fix (follow-up to SPEC-SHOPIFY-SKU-SET-002): batch-load the
    # real book title for every member ISBN that will be split out below,
    # ONCE per order-sync call across ALL bundle line items — never per
    # line item, never per member — matching the bundle_map query discipline.
    relevant_member_isbns: set[str] = set()
    for li in order_data.get("line_items", []):
        member_isbns = bundle_map.get(li.get("sku"))
        if member_isbns:
            relevant_member_isbns.update(member_isbns)
    title_map = _build_title_map(list(relevant_member_isbns))

    # SPEC-ORDER-025 M2: rows whose sku was manually corrected at
    # 발주처리(confirm) time (LineItem.original_sku set) must never have that
    # correction silently reverted by the next Shopify sync. One query for
    # the whole order (never per line item — this project's remote DB costs
    # ~130ms/query), keyed by (shopify_line_item_id, original_sku) so the
    # bundle branch below can resolve a corrected member row by its ORIGINAL
    # isbn, and the non-bundle branch by the row's own single sku value.
    incoming_line_item_ids = [li["id"] for li in order_data.get("line_items", [])]
    protected_sku_by_key: dict[tuple[int, str], str] = {
        (row["shopify_line_item_id"], row["original_sku"]): row["sku"]
        for row in LineItem.objects.filter(
            order=order_obj,
            shopify_line_item_id__in=incoming_line_item_ids,
            original_sku__isnull=False,
        ).values("shopify_line_item_id", "original_sku", "sku")
    }

    incoming_shopify_ids = set()
    for li in order_data.get("line_items", []):
        incoming_shopify_ids.add(li["id"])
        # purchase_status and logistics_status (SPEC-ORDER-011 REQ-LOGI-002)
        # are intentionally excluded from defaults to preserve manual processing state
        common_defaults = {
            "product_id": li.get("product_id"),
            "variant_id": li.get("variant_id"),
            "title": li.get("title"),
            "variant_title": li.get("variant_title"),
            "quantity": li.get("quantity"),
            "price": _decimal_or_none(li.get("price")),
            "total_discount": _decimal_or_none(li.get("total_discount")),
            "fulfillment_status": li.get("fulfillment_status"),
            "vendor": li.get("vendor"),
            "grams": li.get("grams"),
            "location": line_item_location_map.get(li["id"], "") if line_item_location_map else "",
        }
        member_isbns = bundle_map.get(li.get("sku"))
        if member_isbns:
            # Bundle SKU: expand into one LineItem row per member ISBN, all
            # sharing shopify_line_item_id, each carrying the FULL (undivided)
            # quantity — required for refund math (REQ-SKUSET2-006) to stay
            # correct with zero changes to the 6 Refund OuterRef subquery sites.
            for member_isbn in member_isbns:
                # Each member row gets its OWN book title (or None if the
                # ISBN isn't in the catalog yet) — never the bundle's own
                # Shopify-reported title. LineItem.title is nullable and
                # downstream code already has title-or-fallback handling.
                member_defaults = {**common_defaults, "title": title_map.get(member_isbn)}
                # SPEC-ORDER-025 M2: `sku=member_isbn` is part of the LOOKUP
                # key here, not `defaults` — if this member row was
                # corrected, its actual current sku no longer equals
                # member_isbn, so looking it up by member_isbn would miss it
                # and create a stray duplicate, orphaning the corrected row.
                # Resolve to the corrected row's own sku when one exists for
                # this (shopify_line_item_id, original_sku=member_isbn) pair;
                # otherwise fall back to member_isbn exactly as before.
                lookup_sku = protected_sku_by_key.get((li["id"], member_isbn), member_isbn)
                LineItem.objects.update_or_create(
                    order=order_obj,
                    shopify_line_item_id=li["id"],
                    sku=lookup_sku,
                    defaults=member_defaults,
                )
        else:
            # No bundle mapping: single-row update_or_create.
            shopify_sku = li.get("sku")
            defaults = {**common_defaults, "sku": shopify_sku}
            # SPEC-ORDER-025 M2: unlike the bundle branch above, `sku` here
            # sits in `defaults` (the lookup is order+shopify_line_item_id
            # only), so an unconditional write silently reverts a manual
            # correction on every sync. Omit it when this row is protected.
            if (li["id"], shopify_sku) in protected_sku_by_key:
                defaults.pop("sku")
            LineItem.objects.update_or_create(
                order=order_obj,
                shopify_line_item_id=li["id"],
                defaults=defaults,
            )
    # Remove line items that Shopify no longer reports, but only if not purchase-ordered
    order_obj.line_items.filter(purchase_orders__isnull=True).exclude(
        shopify_line_item_id__in=incoming_shopify_ids
    ).delete()

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
        # One Refund row PER refund_line_item. A Shopify refund is a container
        # that can hold several refunded line items at once; storing only
        # `refund_line_items[0]` (the previous behaviour) dropped every
        # additional item, so the refund-netting subqueries in
        # purchase_order_views treated those items as never refunded.
        refund_line_items = refund_data.get("refund_line_items", [])
        for rli in refund_line_items or [{}]:
            # `or [{}]` keeps a refund with no line items (e.g. a pure
            # shipping refund) recorded as a header-only row, matching what
            # the previous code stored for that case.
            Refund.objects.update_or_create(
                order=order_obj,
                shopify_refund_id=refund_data["id"],
                line_item_id=rli.get("line_item_id"),
                defaults={
                    "note": refund_data.get("note"),
                    "shopify_created_at": refund_data.get("created_at"),
                    "quantity": rli.get("quantity"),
                    "subtotal": _decimal_or_none(rli.get("subtotal")),
                    "total_tax": _decimal_or_none(rli.get("total_tax")),
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
    from .models import LineItem, Order, StoreSyncWatermark

    if store_type == "gimssine":
        domain = settings.SHOPIFY_GIMSSINE_DOMAIN
        token = settings.SHOPIFY_GIMSSINE_TOKEN
    else:
        domain = settings.SHOPIFY_ETOILE_DOMAIN
        token = settings.SHOPIFY_ETOILE_TOKEN

    # Watermark lives in its own table, NOT derived from
    # Order.shopify_updated_at — that column is also written by the
    # single-order resync path (sync_single_order_from_shopify), which can
    # bump one old order's shopify_updated_at far ahead of the rest of the
    # store and silently skip everything in between on the next sync.
    watermark, _ = StoreSyncWatermark.objects.get_or_create(store_type=store_type)
    last_updated = watermark.last_synced_updated_at
    if last_updated is None:
        # First run after deploy (or a brand-new store): seed from the
        # current Order MAX so day-one behaviour is unchanged and we don't
        # re-pull the store's entire history.
        last_updated = (
            Order.objects.filter(store_type=store_type)
            .order_by("-shopify_updated_at")
            .values_list("shopify_updated_at", flat=True)
            .first()
        )
        if last_updated is not None:
            watermark.last_synced_updated_at = last_updated
            watermark.save(update_fields=["last_synced_updated_at"])

    updated_at_min = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ") if last_updated else None

    orders = fetch_all_open_orders(domain, token, updated_at_min=updated_at_min)
    if not orders:
        # Zero orders fetched: leave last_synced_updated_at (the fetch cursor)
        # untouched, but last_run_at MUST still advance — a quiet cycle with
        # no new Shopify activity is a healthy run, not a stopped one, and
        # this is the field the staleness indicator reads.
        watermark.last_run_at = timezone.now()
        watermark.save(update_fields=["last_run_at"])
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

    # Advance the watermark to MAX(updated_at) of the orders actually
    # returned in THIS batch — never a global MAX over the Order table
    # (that is exactly the bug this rewrite fixes). Monotonic: never move
    # the watermark backwards.
    batch_max = None
    for order_data in orders:
        parsed = parse_datetime(order_data["updated_at"]) if order_data.get("updated_at") else None
        if parsed is not None and (batch_max is None or parsed > batch_max):
            batch_max = parsed

    # last_run_at MUST advance here too even when the watermark itself does
    # not (batch_max <= last_updated) — a single save covers both fields so
    # neither update_fields list can silently drop the other.
    watermark.last_run_at = timezone.now()
    update_fields = ["last_run_at"]
    if batch_max is not None and (last_updated is None or batch_max > last_updated):
        watermark.last_synced_updated_at = batch_max
        update_fields.append("last_synced_updated_at")
    watermark.save(update_fields=update_fields)

    return {
        "synced_count": synced_count,
        "updated_count": updated_count,
        "error": None,
        "updated_at_min": updated_at_min,
    }


# ---------------------------------------------------------------------------
# SPEC-ORDER-029: order cancellation/closure detection & backfill
# ---------------------------------------------------------------------------

SHOPIFY_ORDER_STATUS_FIELDS = "id,cancelled_at,closed_at"
IDS_CHUNK_SIZE = 250


def _chunked(seq, size):
    """Pure helper: split seq into consecutive slices of at most `size`.
    No I/O, no Django imports — trivially unit-testable on a plain list.
    """
    seq = list(seq)
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def fetch_order_status_by_ids(domain, token, shopify_order_ids, fields=SHOPIFY_ORDER_STATUS_FIELDS):
    """Query orders.json?ids=<up to 250 comma-separated>&status=any&fields=...
    &limit=250 for an EXPLICIT list of Shopify order IDs (<=250), returning
    their CURRENT cancelled_at/closed_at values regardless of status.

    SPEC-ORDER-029 REQ-CANC-001/002: verified in production 2026-08-19 that a
    request for exactly 250 ids returns exactly 250 records, both timestamp
    fields populated, and NO Link header. This function still defensively
    follows a Link header if one unexpectedly appears (REQ-CANC-003), reusing
    the existing _parse_next_page_info() helper — but the expected path
    issues exactly one HTTP call.

    Caller MUST pass <=250 ids (REQ-CANC-002) — chunking is the caller's
    responsibility, see reconcile_order_status_for_ids() below.
    """
    if not shopify_order_ids:
        return []
    ids_param = ",".join(str(i) for i in shopify_order_ids)
    path = f"orders.json?ids={ids_param}&status=any&limit=250&fields={fields}"
    records = []
    while path:
        body, headers = _get_with_headers(domain, token, path)
        records.extend(body.get("orders", []))
        link = headers.get("Link") or headers.get("link")
        page_info = _parse_next_page_info(link)
        path = (
            f"orders.json?limit=250&page_info={page_info}&fields={fields}"
            if page_info
            else None
        )
    return records


def open_candidate_order_ids(store_type, closed_grace_days=None):
    """SPEC-ORDER-029 REQ-CANC-004/005: the reconciliation candidate set —
    local Order rows whose cancellation state is not yet known, scoped to
    one store.

    Asymmetric definition: cancellation is treated as terminal (Shopify has
    no public un-cancel API, spec.md Assumption A6) but closure is NOT — an
    order can be archived (closed_at set) and cancelled afterwards. So:

        cancelled_at IS NULL
        AND (closed_at IS NULL OR closed_at >= now - closed_grace_days)

    closed_grace_days=None (default) means the closed_at condition is not
    applied at all — every non-cancelled order is a candidate, regardless of
    how long ago it closed. This is what backfill_order_cancellations uses
    (REQ-CANC-019): unbounded, because it runs once/occasionally, not every
    5 minutes.

    closed_grace_days=30 is what sync_order_cancellations uses
    (REQ-CANC-014): bounds recurring cost while keeping recently-closed
    orders under observation for the realistic window where a
    closure-then-cancellation could still arrive.

    .order_by("shopify_order_id") makes chunk composition deterministic
    across repeated calls (REQ-CANC-012 / spec.md §8 C6).
    """
    from django.db.models import Q

    from .models import Order

    qs = Order.objects.filter(store_type=store_type, cancelled_at__isnull=True)
    if closed_grace_days is not None:
        threshold = timezone.now() - timedelta(days=closed_grace_days)
        qs = qs.filter(Q(closed_at__isnull=True) | Q(closed_at__gte=threshold))
    return list(qs.order_by("shopify_order_id").values_list("shopify_order_id", flat=True))


# @MX:NOTE: [AUTO] SPEC-ORDER-029 REQ-CANC-025: string-matches MySQL error
# 1205 ("Lock wait timeout exceeded") rather than a driver exception class
# because this failure originates entirely from sync_orders' long-held row
# locks (sync_orders.py sync_store(), transaction.atomic() wraps a Shopify
# HTTP round-trip) — this function's own lock hold is milliseconds
# (bulk_update on 2 columns). See spec.md §1.2 for the full analysis.
def _is_lock_wait_timeout(exc):
    """SPEC-ORDER-029 REQ-CANC-025: identify a MySQL "Lock wait timeout
    exceeded" failure (InnoDB error 1205) so the caller can classify it
    separately from other chunk failures.

    Gates on exception TYPE first (django.db.utils.OperationalError) —
    matching "1205" against str(exc) alone is type-blind and would
    misclassify any unrelated exception (KeyError, ValueError, ...) whose
    message happens to contain that digit sequence as a self-healing lock
    wait, silently suppressing a real failure from the caller's `failed`
    list (evaluator-active finding, 2026-08-19). Only once the type is
    confirmed do we check the error code: numerically against args[0] when
    it is an int (mysqlclient/PyMySQL both surface this as
    django.db.utils.OperationalError wrapping a DB-API error whose first arg
    is (1205, "Lock wait timeout exceeded; try restarting transaction")),
    falling back to a message substring match only within that type — never
    outside it.
    """
    if not isinstance(exc, OperationalError):
        return False
    args = getattr(exc, "args", ())
    if args and isinstance(args[0], int):
        return args[0] == 1205
    return "1205" in str(exc) or "Lock wait timeout exceeded" in str(exc)


# @MX:NOTE: [AUTO] SPEC-ORDER-029 REQ-CANC-007/008: writes ONLY
# cancelled_at/closed_at via bulk_update(), never via _sync_single_order()
# or update_or_create(defaults=...). The ids=/fields= payload this function
# consumes lacks every other Order field AND lacks "line_items"/
# "shipping_lines"/"refunds", so routing through _sync_single_order() would
# null those fields out AND unconditionally delete PurchaseOrder-unlinked
# LineItems, all ShippingLine rows, and all Refund rows on the order.
def reconcile_order_status_for_ids(
    store_type, domain, token, shopify_order_ids, dry_run=False, chunk_size=IDS_CHUNK_SIZE
):
    """Narrow-write Order.cancelled_at/closed_at for the given LOCAL
    shopify_order_ids, chunked at `chunk_size` (default 250, REQ-CANC-002).
    Every chunk is attempted even if an earlier one raises (REQ-CANC-011/
    016 — per-chunk isolation). Never routes through _sync_single_order()
    or a broad update_or_create(defaults=...) (REQ-CANC-007/008).

    Returns {
        "scanned": int,               # records actually returned by Shopify
        "changed": list[dict],        # {"shopify_order_id", "cancelled_at", "closed_at"}
        "chunk_failures": list[dict], # {"ids": list[int], "error": str, "lock_timeout": bool}
        "missing_ids": list[int],     # requested but not returned by Shopify
    }
    When dry_run=True, `changed` is still populated (diff computed) but no
    bulk_update() call happens — same "changed" key in both modes; the
    caller chooses its own display label ("would_change" vs "changed") for
    stdout only.
    """
    from django.db import transaction

    from .models import Order

    scanned = 0
    changed: list[dict] = []
    chunk_failures: list[dict] = []
    missing_ids: list[int] = []

    for chunk in _chunked(shopify_order_ids, chunk_size):
        try:
            # HTTP fetch happens OUTSIDE the DB transaction — a slow
            # Shopify round-trip must not hold a DB transaction/lock open.
            records = fetch_order_status_by_ids(domain, token, chunk)
            scanned += len(records)

            returned_ids = {r["id"] for r in records}
            missing_ids.extend(i for i in chunk if i not in returned_ids)

            with transaction.atomic():
                existing = {
                    o.shopify_order_id: o
                    for o in Order.objects.filter(
                        store_type=store_type, shopify_order_id__in=chunk
                    ).only("id", "shopify_order_id", "cancelled_at", "closed_at")
                }

                to_update = []
                for r in records:
                    order = existing.get(r["id"])
                    if order is None:
                        continue  # REQ-CANC-009: not locally matched — skip

                    new_cancelled = (
                        parse_datetime(r["cancelled_at"]) if r.get("cancelled_at") else None
                    )
                    new_closed = parse_datetime(r["closed_at"]) if r.get("closed_at") else None
                    if order.cancelled_at != new_cancelled or order.closed_at != new_closed:
                        changed.append(
                            {
                                "shopify_order_id": order.shopify_order_id,
                                "cancelled_at": new_cancelled,
                                "closed_at": new_closed,
                            }
                        )
                        if not dry_run:
                            order.cancelled_at = new_cancelled
                            order.closed_at = new_closed
                            to_update.append(order)

                if to_update:
                    Order.objects.bulk_update(to_update, ["cancelled_at", "closed_at"])
        except Exception as exc:  # noqa: BLE001 - one chunk must not abort the rest
            chunk_failures.append(
                {
                    "ids": list(chunk),
                    "error": str(exc),
                    "lock_timeout": _is_lock_wait_timeout(exc),
                }
            )
            continue

    return {
        "scanned": scanned,
        "changed": changed,
        "chunk_failures": chunk_failures,
        "missing_ids": missing_ids,
    }
