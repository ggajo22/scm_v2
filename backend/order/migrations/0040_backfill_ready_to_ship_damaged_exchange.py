# SPEC-PURCHASE-ORDER-011 REQ-DEX-013/013a (결정 F): one-time backfill that
# recomputes Order.ready_to_ship for every existing Order with at least one
# trackable (sku not null) LineItem, applying the REQ-DEX-009c
# damaged_exchange short-circuit added to
# purchase_order_views._recompute_order_aggregates(). Without this backfill,
# an Order that was already damaged_exchange before this SPEC shipped would
# keep displaying a stale ready_to_ship=True on the new search page until
# some unrelated write happened to touch it (결정 F).
#
# Direct precedent: 0033_backfill_order_ready_to_ship.py (SPEC-ORDER-012
# REQ-RTS-006) — same algorithm shape, same historical-model reimplementation
# rationale (migrations must not import purchase_order_views, which is not
# frozen in time), same batch design (1 SELECT + 1 bulk_update, regardless of
# Order count), same reverse_code=noop (no prior value to roll back to).
#
# Algorithm (REQ-RTS-002 rule extended by REQ-DEX-009c):
#   1. Collect (order_id, purchase_status, logistics_status) triples for
#      every LineItem with a non-null sku, across ALL Orders in one query.
#   2. Group by order_id in Python, then per Order:
#        a. exclude LineItems with purchase_status == "order_cancelled";
#        b. if zero non-excluded LineItems remain -> ready_to_ship = None;
#        c. elif any non-excluded LineItem has purchase_status in
#           ("cs_required", "damaged_exchange") -> ready_to_ship = False;
#        d. else -> ready_to_ship = True iff every non-excluded LineItem has
#           logistics_status == "received" OR purchase_status == "in_stock",
#           else False.
#   3. bulk_update() every affected Order's ready_to_ship in one batched
#      write.
#
# Scope (REQ-DEX-013a): Orders with no damaged_exchange LineItem are
# recomputed under the same, unchanged rule they already satisfied, so their
# stored value is left exactly as-is. Orders with zero trackable LineItems
# never appear in the grouped result and are not touched.

from django.db import migrations


def backfill_ready_to_ship_damaged_exchange(apps, schema_editor):
    Order = apps.get_model("order", "Order")
    LineItem = apps.get_model("order", "LineItem")

    triples = LineItem.objects.filter(sku__isnull=False).values_list(
        "order_id", "purchase_status", "logistics_status"
    )

    items_by_order: dict[int, list[tuple[str, str]]] = {}
    for order_id, purchase_status, logistics_status in triples:
        items_by_order.setdefault(order_id, []).append((purchase_status, logistics_status))

    if not items_by_order:
        return

    to_update = []
    for order_id, items in items_by_order.items():
        non_cancelled = [it for it in items if it[0] != "order_cancelled"]
        if not non_cancelled:
            ready_to_ship = None
        elif any(
            purchase_status in ("cs_required", "damaged_exchange")
            for purchase_status, _ in non_cancelled
        ):
            ready_to_ship = False
        else:
            ready_to_ship = all(
                logistics_status == "received" or purchase_status == "in_stock"
                for purchase_status, logistics_status in non_cancelled
            )
        to_update.append(Order(id=order_id, ready_to_ship=ready_to_ship))

    Order.objects.bulk_update(to_update, ["ready_to_ship"])


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0039_lineitem_damaged_quantity"),
    ]

    operations = [
        migrations.RunPython(backfill_ready_to_ship_damaged_exchange, migrations.RunPython.noop),
    ]
