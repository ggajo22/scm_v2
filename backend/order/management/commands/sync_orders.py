"""Management command: sync_orders.

CLI entry point for the incremental Shopify order sync, so a scheduler
(EventBridge / ECS scheduled task) can run it without going through
OrderSyncView's HTTP endpoint.

Mirrors OrderSyncView._sync_store_safe's isolation contract: each store runs
inside its own transaction, and one store's failure never rolls back or
aborts the other. Stores run sequentially rather than in the view's
ThreadPoolExecutor -- a scheduled run has no request latency budget to
optimise for, and sequential execution keeps one DB connection per process.

Exits non-zero when any store failed, so the scheduler can alarm on it.

Usage:
    python manage.py sync_orders
    python manage.py sync_orders --store gimssine

Note: this shares no lock with the manual sync button. If a scheduled run
overlaps a manual one on the same orders, one of the two fails on a lock
wait or a duplicate-key conflict and rolls back -- including its watermark
advance, so an overlap can never cause the skipped-order data loss that
StoreSyncWatermark exists to prevent. The failed side is picked up by the
next run.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from order.shopify_orders import sync_store

STORE_TYPES = ["gimssine", "etoile"]


class Command(BaseCommand):
    help = (
        "Run the incremental Shopify order sync from the CLI (scheduler entry "
        "point). Each store is synced in its own transaction; exits non-zero "
        "if any store failed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--store",
            choices=[*STORE_TYPES, "all"],
            default="all",
            help="Store to sync (default: all)",
        )

    def handle(self, *args, **options):
        store = options["store"]
        stores = STORE_TYPES if store == "all" else [store]

        total_synced = 0
        total_updated = 0
        failed = []

        for store_type in stores:
            try:
                with transaction.atomic():
                    result = sync_store(store_type)
            except Exception as exc:  # noqa: BLE001 - one store must not abort the other
                self.stderr.write(self.style.ERROR(f"[{store_type}] FAILED: {exc}"))
                failed.append(store_type)
                continue

            error = result.get("error")
            if error:
                self.stderr.write(self.style.ERROR(f"[{store_type}] FAILED: {error}"))
                failed.append(store_type)
                continue

            synced = result["synced_count"]
            updated = result["updated_count"]
            total_synced += synced
            total_updated += updated
            self.stdout.write(
                f"[{store_type}] created={synced} updated={updated} "
                f"since={result.get('updated_at_min')}"
            )

        summary = f"done - created={total_synced}, updated={total_updated}, failed={len(failed)}"
        if failed:
            self.stdout.write(self.style.ERROR(summary))
            raise CommandError(f"sync failed for: {', '.join(failed)}")
        self.stdout.write(self.style.SUCCESS(summary))
