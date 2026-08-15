# Data migration: seed StoreSyncWatermark.last_synced_updated_at for every
# store_type that already has Order rows, from the current
# MAX(Order.shopify_updated_at) for that store.
#
# Without this, the first post-deploy sync_store() run would see a NULL
# watermark and (per sync_store()'s own seed-on-NULL fallback) compute the
# same MAX(Order.shopify_updated_at) at request time anyway — so this
# migration is not strictly required for correctness, but it makes the cutover
# explicit and auditable (a StoreSyncWatermark row exists with the correct
# value from the moment this migration runs, rather than being created lazily
# on the next sync call), and keeps the seeding logic in one place instead of
# relying on every future StoreSyncWatermark row to always pass through
# sync_store()'s NULL-seed branch first.
#
# reverse_code deletes the rows this migration creates, mirroring the
# "reversible where reasonable" convention used elsewhere in this app
# (contrast with 0033/0040's RunPython.noop, which is correct there only
# because the field being backfilled has no other origin to roll back to —
# here the origin is "no StoreSyncWatermark row", which IS trivially
# restorable by deleting the row again).

from django.db import migrations


def backfill_store_sync_watermark(apps, schema_editor):
    Order = apps.get_model("order", "Order")
    StoreSyncWatermark = apps.get_model("order", "StoreSyncWatermark")

    store_types = Order.objects.values_list("store_type", flat=True).distinct()
    for store_type in store_types:
        max_updated_at = (
            Order.objects.filter(store_type=store_type)
            .order_by("-shopify_updated_at")
            .values_list("shopify_updated_at", flat=True)
            .first()
        )
        StoreSyncWatermark.objects.update_or_create(
            store_type=store_type,
            defaults={"last_synced_updated_at": max_updated_at},
        )


def remove_store_sync_watermark(apps, schema_editor):
    StoreSyncWatermark = apps.get_model("order", "StoreSyncWatermark")
    StoreSyncWatermark.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0041_storesyncwatermark"),
    ]

    operations = [
        migrations.RunPython(backfill_store_sync_watermark, remove_store_sync_watermark),
    ]
