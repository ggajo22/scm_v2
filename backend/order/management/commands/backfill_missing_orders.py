"""Management command: backfill_missing_orders.

Recovery path for orders permanently skipped by the sync_store() watermark
bug (see order.models.StoreSyncWatermark and the sync_store() rewrite in
order.shopify_orders). Before that fix, a single-order resync could bump the
store-wide MAX(Order.shopify_updated_at) far ahead of what sync_store() had
actually swept, and orders created in the gap were never fetched again.

This command re-scans Shopify's open orders created since a given date,
diffs them against the local Order table in one query per store, and
creates ONLY the orders that are missing. It never touches an order that
already exists locally, and it never advances the sync watermark — running
it is not equivalent to running sync_store() again, on purpose.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from order.models import Order
from order.shopify_orders import (
    _build_fulfillment_location_data,
    _get_with_headers,
    _parse_next_page_info,
    _sync_single_order,
)


class Command(BaseCommand):
    help = (
        "Recover orders skipped by the sync_store() watermark bug: fetch open "
        "Shopify orders created since --created-since, diff against the local "
        "Order table, and create only the ones that are missing. Never "
        "modifies an existing order and never advances the sync watermark."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--store",
            choices=["gimssine", "etoile", "all"],
            default="all",
            help="Store to scan (default: all)",
        )
        parser.add_argument(
            "--created-since",
            type=str,
            default=None,
            help=(
                "ISO date/datetime; only orders created on/after this are "
                "scanned (default: 60 days ago)"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without writing anything",
        )

    def _credentials(self, store_type):
        if store_type == "gimssine":
            return settings.SHOPIFY_GIMSSINE_DOMAIN, settings.SHOPIFY_GIMSSINE_TOKEN
        return settings.SHOPIFY_ETOILE_DOMAIN, settings.SHOPIFY_ETOILE_TOKEN

    def _resolve_created_since(self, arg: str | None) -> str:
        if arg:
            return arg
        default_dt = timezone.now() - timedelta(days=60)
        return default_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _fetch_open_orders_created_since(self, domain, token, created_since):
        """Page through orders.json?status=open, mirroring
        fetch_all_open_orders's pagination contract: only `limit` and
        `page_info` are sent on subsequent pages (created_at_min is a
        first-page-only filter, per Shopify's cursor pagination rules)."""
        all_orders = []
        path = f"orders.json?status=open&limit=250&created_at_min={created_since}"
        while path:
            body, headers = _get_with_headers(domain, token, path)
            all_orders.extend(body.get("orders", []))
            link = headers.get("Link") or headers.get("link")
            page_info = _parse_next_page_info(link)
            path = f"orders.json?limit=250&page_info={page_info}" if page_info else None
        return all_orders

    def handle(self, *args, **options):
        store = options["store"]
        dry_run = options["dry_run"]
        created_since = self._resolve_created_since(options["created_since"])
        stores = ["gimssine", "etoile"] if store == "all" else [store]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved"))

        total_scanned = 0
        total_present = 0
        total_created = 0
        total_failed = 0
        failures = []

        for store_type in stores:
            domain, token = self._credentials(store_type)
            self.stdout.write(f"\n[{store_type}] scanning open orders created since {created_since}")

            orders = self._fetch_open_orders_created_since(domain, token, created_since)
            total_scanned += len(orders)

            # ONE query: diff the fetched Shopify ids against what already
            # exists locally for this store — never a per-order lookup.
            shopify_ids = [o["id"] for o in orders]
            existing_ids = set(
                Order.objects.filter(
                    store_type=store_type, shopify_order_id__in=shopify_ids
                ).values_list("shopify_order_id", flat=True)
            )
            missing = [o for o in orders if o["id"] not in existing_ids]
            total_present += len(orders) - len(missing)
            self.stdout.write(
                f"[{store_type}] {len(orders)} fetched, "
                f"{len(orders) - len(missing)} already present, {len(missing)} missing"
            )

            for order_data in missing:
                label = order_data.get("name") or f"#{order_data.get('order_number')}"
                if dry_run:
                    self.stdout.write(f"  would create {label} (id={order_data['id']})")
                    total_created += 1
                    continue
                try:
                    # Each missing order gets its own transaction so one bad
                    # order can never roll back the rest of the run.
                    with transaction.atomic():
                        order_location, line_item_map = _build_fulfillment_location_data(
                            domain, token, order_data["id"]
                        )
                        _sync_single_order(
                            order_data,
                            store_type,
                            location_code=order_location,
                            line_item_location_map=line_item_map,
                        )
                    self.stdout.write(self.style.SUCCESS(f"  created {label}"))
                    total_created += 1
                except Exception as exc:  # noqa: BLE001 — one bad order must not stop the run
                    self.stderr.write(self.style.ERROR(f"  FAILED {label}: {exc}"))
                    failures.append(label)
                    total_failed += 1

        created_label = "would_create" if dry_run else "created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\ndone - scanned={total_scanned}, already_present={total_present}, "
                f"{created_label}={total_created}, failed={total_failed}"
            )
        )
        if failures:
            self.stdout.write(self.style.ERROR(f"failed orders: {failures}"))
