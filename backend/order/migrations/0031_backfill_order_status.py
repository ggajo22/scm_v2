# SPEC-ORDER-011 REQ-LOGI-012: one-time backfill recomputing Order.status for
# every existing Order that has at least one trackable (sku not null)
# LineItem, applied once at deployment time (decision E).
#
# Algorithm (mirrors purchase_order_views._recompute_order_status()'s
# two-query design, reimplemented inline here since migrations must use
# apps.get_model() historical models rather than importing view-layer code
# that is not frozen in time):
#   1. Collect (order_id, logistics_status) pairs for every LineItem with a
#      non-null sku, across ALL Orders in one query.
#   2. Group by order_id in Python: if every trackable LineItem under an
#      Order shares the same logistics_status, that Order's status becomes
#      that value; if 2+ distinct values are present, status becomes
#      "partial" (REQ-LOGI-008).
#   3. bulk_update() every affected Order's status in one batched write.
#
# Scope, exactly as REQ-LOGI-012 states: only Orders with >=1 trackable
# LineItem are touched. Orders with zero trackable LineItems (sku IS NULL on
# every child LineItem) are left with whatever stale financial_status-derived
# value they already had — this is a known, accepted gap per spec wording,
# not a defect to "fix" beyond scope (see spec.md 결정 D / REQ-LOGI-008).
#
# In practice, since this migration runs immediately after
# 0030_lineitem_logistics_status_alter_order_status (which defaults every
# existing LineItem's new logistics_status column to "not_shipped" via the
# AddField default), every trackable LineItem is uniformly "not_shipped" at
# the moment this backfill runs — so every recomputed Order.status is
# expected to converge on "not_shipped" (see acceptance.md 시나리오 8). The
# general aggregation algorithm above is still implemented in full (not
# hardcoded to "not_shipped") so it stays correct for any future re-run
# against a database where logistics_status values have since diverged.
#
# reverse_code is RunPython.noop: reversing this backfill would require
# knowing each Order's PRE-backfill status value, which this migration does
# not retain — rolling back leaves the recomputed values in place rather
# than attempting (and failing) to restore stale Shopify-derived values that
# REQ-LOGI-011 has already deemed meaningless. This mirrors
# 0026_backfill_bundle_lineitems.py's documented irreversibility.

from django.db import migrations


def backfill_order_status(apps, schema_editor):
    Order = apps.get_model("order", "Order")
    LineItem = apps.get_model("order", "LineItem")

    pairs = LineItem.objects.filter(sku__isnull=False).values_list(
        "order_id", "logistics_status"
    )

    statuses_by_order: dict[int, set[str]] = {}
    for order_id, logistics_status in pairs:
        statuses_by_order.setdefault(order_id, set()).add(logistics_status)

    if not statuses_by_order:
        return

    to_update = []
    for order_id, statuses in statuses_by_order.items():
        new_status = next(iter(statuses)) if len(statuses) == 1 else "partial"
        to_update.append(Order(id=order_id, status=new_status))

    Order.objects.bulk_update(to_update, ["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0030_lineitem_logistics_status_alter_order_status"),
    ]

    operations = [
        migrations.RunPython(backfill_order_status, migrations.RunPython.noop),
    ]
