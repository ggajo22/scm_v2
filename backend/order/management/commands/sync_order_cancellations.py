"""SPEC-ORDER-029: detect newly cancelled/closed Shopify orders and reflect
cancelled_at/closed_at locally.

Candidate set is derived fresh from the local Order table each run
(cancelled_at IS NULL, closed_at within the last CLOSED_GRACE_DAYS days or
never closed) — no cursor. Never touches StoreSyncWatermark.

A store whose chunk failures are ALL MySQL lock-wait timeouts (expected
under overlap with sync_orders, spec.md §1.2) is logged but does NOT raise
CommandError (REQ-CANC-026) — any other failure still does.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from order.shopify_orders import open_candidate_order_ids, reconcile_order_status_for_ids

STORE_TYPES = ["gimssine", "etoile"]
CLOSED_GRACE_DAYS = 30  # REQ-CANC-014


def _credentials(store_type):
    if store_type == "gimssine":
        return settings.SHOPIFY_GIMSSINE_DOMAIN, settings.SHOPIFY_GIMSSINE_TOKEN
    return settings.SHOPIFY_ETOILE_DOMAIN, settings.SHOPIFY_ETOILE_TOKEN


class Command(BaseCommand):
    help = (
        "Detect newly cancelled/closed Shopify orders and reflect "
        "cancelled_at/closed_at locally. Candidate set is derived fresh "
        "from the local Order table each run (cancelled_at IS NULL, "
        f"closed_at within the last {CLOSED_GRACE_DAYS} days or never "
        "closed) — no cursor. Never touches StoreSyncWatermark. A store "
        "whose chunk failures are ALL MySQL lock-wait timeouts (expected "
        "under overlap with sync_orders, spec.md §1.2) is logged but does "
        "NOT raise CommandError (REQ-CANC-026) — any other failure still "
        "does."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--store", choices=[*STORE_TYPES, "all"], default="all",
            help="Store to scan (default: all)",
        )

    def handle(self, *args, **options):
        stores = STORE_TYPES if options["store"] == "all" else [options["store"]]
        failed = []

        for store_type in stores:
            try:
                domain, token = _credentials(store_type)
                candidate_ids = open_candidate_order_ids(
                    store_type, closed_grace_days=CLOSED_GRACE_DAYS
                )
                result = reconcile_order_status_for_ids(store_type, domain, token, candidate_ids)
            except Exception as exc:  # noqa: BLE001 - one store must not abort the other
                self.stderr.write(self.style.ERROR(f"[{store_type}] FAILED: {exc}"))
                failed.append(store_type)
                continue

            if result["chunk_failures"]:
                self.stderr.write(
                    self.style.ERROR(
                        f"[{store_type}] {len(result['chunk_failures'])} chunk(s) failed"
                    )
                )
                for cf in result["chunk_failures"]:
                    tag = "lock_timeout" if cf.get("lock_timeout") else "error"
                    self.stderr.write(self.style.ERROR(f"  ids={cf['ids']} {tag}={cf['error']}"))
                # REQ-CANC-026 (spec.md D10): a store whose chunk failures
                # are ALL lock-wait timeouts is a soft failure — self-healing
                # next cycle via candidate-set re-entry (REQ-CANC-004) — do
                # not raise CommandError for it. The failure is still logged
                # above (no information loss). Any non-lock-timeout failure
                # mixed in is still a hard failure.
                if not all(cf.get("lock_timeout") for cf in result["chunk_failures"]):
                    failed.append(f"{store_type} (partial)")

            if result["missing_ids"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"[{store_type}] missing from Shopify response: "
                        f"{result['missing_ids']}"
                    )
                )

            self.stdout.write(
                f"[{store_type}] candidates={len(candidate_ids)} "
                f"scanned={result['scanned']} changed={len(result['changed'])}"
            )

        if failed:
            raise CommandError(f"sync_order_cancellations failed for: {', '.join(failed)}")
        self.stdout.write(self.style.SUCCESS("done"))
