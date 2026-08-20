# SPEC-PURCHASE-ORDER-011 REQ-DEX-011/013b (개정 v1.7.0, 사용자 지시): one-time
# backfill for LineItems that reached purchase_status="damaged_exchange"
# BEFORE the damage submission started resetting logistics_status. Those rows
# still sit at their pre-damage logistics_status (typically "received") with
# the damaged units still counted in received_quantity, so they display as 입고
# and their parent Order can still read ready_to_ship=True.
#
# Direct precedent: 0040_backfill_ready_to_ship_damaged_exchange.py (결정 F) —
# same one-shot shape, same historical-model reimplementation rationale
# (migrations must not import purchase_order_views, which is not frozen in
# time), same reverse_code=noop (the pre-backfill value is not recoverable).
#
# Algorithm:
#   1. For every damaged_exchange LineItem: logistics_status -> "not_shipped"
#      and received_quantity -> max(0, received_quantity - damaged_quantity),
#      matching DamagedExchangeSubmitView's live rule for a first submission.
#   2. Recompute Order.status / Order.ready_to_ship for exactly those parent
#      Orders, mirroring the CURRENT _recompute_order_aggregates rule — refund
#      netting included, and WITHOUT the cs_required/damaged_exchange
#      short-circuits, both of which were removed in v1.6.0 (SPEC-ORDER-012
#      v1.5.0 REQ-RTS-002). Migration 0040 predates that removal, which is why
#      its rule is not reused here.
#
# Scope: Orders with no damaged_exchange LineItem are never selected and are
# left untouched.

from django.db import migrations


def backfill_damaged_exchange_logistics(apps, schema_editor):
    Order = apps.get_model("order", "Order")
    LineItem = apps.get_model("order", "LineItem")
    Refund = apps.get_model("order", "Refund")

    damaged = list(LineItem.objects.filter(purchase_status="damaged_exchange"))
    if not damaged:
        return

    for li in damaged:
        li.received_quantity = max(0, li.received_quantity - li.damaged_quantity)
        li.logistics_status = "not_shipped"
    LineItem.objects.bulk_update(damaged, ["logistics_status", "received_quantity"])

    order_ids = {li.order_id for li in damaged}

    # 환불(취소) 수량 차감: same net-quantity exclusion _recompute_order_aggregates
    # applies — a fully refunded LineItem takes part in neither aggregate.
    refunded: dict[tuple[int, int], int] = {}
    for order_id, line_item_id, quantity in Refund.objects.filter(
        order_id__in=order_ids
    ).values_list("order_id", "line_item_id", "quantity"):
        key = (order_id, line_item_id)
        refunded[key] = refunded.get(key, 0) + (quantity or 0)

    items_by_order: dict[int, list[tuple[str, str]]] = {}
    for (
        order_id,
        shopify_line_item_id,
        logistics_status,
        purchase_status,
        quantity,
    ) in LineItem.objects.filter(order_id__in=order_ids, sku__isnull=False).values_list(
        "order_id", "shopify_line_item_id", "logistics_status", "purchase_status", "quantity"
    ):
        if (quantity or 0) - refunded.get((order_id, shopify_line_item_id), 0) <= 0:
            continue
        items_by_order.setdefault(order_id, []).append((logistics_status, purchase_status))

    orders_to_update = []
    for order_id in order_ids:
        items = items_by_order.get(order_id)

        if not items:
            new_status = None
        else:
            statuses = {logistics_status for logistics_status, _ in items}
            new_status = next(iter(statuses)) if len(statuses) == 1 else "partial"

        non_cancelled = [it for it in (items or []) if it[1] != "order_cancelled"]
        if not non_cancelled:
            ready_to_ship = None
        else:
            ready_to_ship = all(
                logistics_status == "received" or purchase_status == "in_stock"
                for logistics_status, purchase_status in non_cancelled
            )

        orders_to_update.append(
            Order(id=order_id, status=new_status, ready_to_ship=ready_to_ship)
        )

    Order.objects.bulk_update(orders_to_update, ["status", "ready_to_ship"])


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0044_lineitem_original_sku"),
    ]

    operations = [
        migrations.RunPython(backfill_damaged_exchange_logistics, migrations.RunPython.noop),
    ]
