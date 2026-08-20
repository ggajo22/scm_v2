"""SPEC-ORDER-029: one-time (or periodically re-run) reconciliation.

For each store, runs the SAME reconciliation as sync_order_cancellations but
with NO closed_grace_days bound (REQ-CANC-019) — every non-cancelled local
order is re-checked regardless of how long ago it closed. This absorbs the
residual exposure of sync_order_cancellations' 30-day window (spec.md §8
C5). Supports --dry-run and verbose per-order reporting. Never touches
StoreSyncWatermark.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from order.shopify_orders import open_candidate_order_ids, reconcile_order_status_for_ids

STORE_TYPES = ["gimssine", "etoile"]


def _credentials(store_type):
    if store_type == "gimssine":
        return settings.SHOPIFY_GIMSSINE_DOMAIN, settings.SHOPIFY_GIMSSINE_TOKEN
    return settings.SHOPIFY_ETOILE_DOMAIN, settings.SHOPIFY_ETOILE_TOKEN


class Command(BaseCommand):
    help = (
        "One-time (or periodically re-run) reconciliation: for each store, "
        "run the SAME reconciliation as sync_order_cancellations but with "
        "NO closed_grace_days bound (REQ-CANC-019) — every non-cancelled "
        "local order is re-checked regardless of how long ago it closed. "
        "This absorbs the residual exposure of sync_order_cancellations' "
        "30-day window (spec.md §8 C5). Supports --dry-run and verbose "
        "per-order reporting. Never touches StoreSyncWatermark."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--store", choices=[*STORE_TYPES, "all"], default="all",
            help="Store to scan (default: all)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would change without writing anything",
        )

    def handle(self, *args, **options):
        stores = STORE_TYPES if options["store"] == "all" else [options["store"]]
        dry_run = options["dry_run"]
        failed = []

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved"))

        total_scanned = 0
        total_changed = 0

        for store_type in stores:
            try:
                domain, token = _credentials(store_type)
                candidate_ids = open_candidate_order_ids(store_type, closed_grace_days=None)
                result = reconcile_order_status_for_ids(
                    store_type, domain, token, candidate_ids, dry_run=dry_run
                )
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(self.style.ERROR(f"[{store_type}] FAILED: {exc}"))
                failed.append(store_type)
                continue

            if result["chunk_failures"]:
                for cf in result["chunk_failures"]:
                    self.stderr.write(self.style.ERROR(f"  ids={cf['ids']} error={cf['error']}"))
                failed.append(f"{store_type} (partial)")

            total_scanned += result["scanned"]
            total_changed += len(result["changed"])
            label = "would_change" if dry_run else "changed"
            self.stdout.write(
                f"[{store_type}] candidates={len(candidate_ids)} "
                f"scanned={result['scanned']} {label}={len(result['changed'])}"
            )
            for c in result["changed"]:
                self.stdout.write(
                    f"  order {c['shopify_order_id']}: "
                    f"cancelled_at={c['cancelled_at']} closed_at={c['closed_at']}"
                )

        self.stdout.write(
            self.style.SUCCESS(f"\ndone - scanned={total_scanned}, changed={total_changed}")
        )
        if failed:
            raise CommandError(f"backfill_order_cancellations failed for: {', '.join(failed)}")
