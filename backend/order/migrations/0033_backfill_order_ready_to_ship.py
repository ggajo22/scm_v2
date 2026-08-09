# SPEC-ORDER-012 REQ-RTS-006: one-time backfill computing Order.ready_to_ship
# for every existing Order that has at least one trackable (sku not null)
# LineItem, applied once at deployment time (mirrors 0031's scope, "decision
# E" — this is a computed-only field with the same trackable-LineItem
# aggregation shape as Order.status).
#
# Algorithm (historical-model reimplementation of REQ-RTS-002's rule —
# migrations must not import purchase_order_views, which is not frozen in
# time, same rationale as 0031_backfill_order_status.py):
#   1. Collect (order_id, purchase_status, logistics_status) triples for
#      every LineItem with a non-null sku, across ALL Orders in one query.
#   2. Group by order_id in Python, then apply REQ-RTS-002's three-step
#      rule per Order:
#        a. exclude LineItems with purchase_status == "order_cancelled";
#        b. if zero non-excluded LineItems remain -> ready_to_ship = None;
#        c. elif any non-excluded LineItem has purchase_status ==
#           "cs_required" -> ready_to_ship = False;
#        d. else -> ready_to_ship = True iff every non-excluded LineItem has
#           logistics_status == "received" OR purchase_status == "in_stock",
#           else False.
#   3. bulk_update() every affected Order's ready_to_ship in one batched
#      write.
#
# Scope: only Orders with >=1 trackable LineItem appear in the grouped
# result and get updated — Orders with zero trackable LineItems are left at
# the NULL value 0032's AddField already gave them, which is the correct
# REQ-RTS-002 value for that case (unlike 0031's Order.status gap, this is
# not an accepted shortfall — NULL is exactly right here, no update needed).
#
# reverse_code is RunPython.noop — mirrors 0031's documented irreversibility
# rationale: this is a brand-new field with no prior value to roll back to.

from django.db import migrations


def backfill_order_ready_to_ship(apps, schema_editor):
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
        elif any(purchase_status == "cs_required" for purchase_status, _ in non_cancelled):
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
        ("order", "0032_order_ready_to_ship"),
    ]

    operations = [
        migrations.RunPython(backfill_order_ready_to_ship, migrations.RunPython.noop),
    ]
