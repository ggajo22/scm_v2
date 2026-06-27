from django.core.management.base import BaseCommand
from django.conf import settings

from order.models import Order
from order.shopify_orders import _build_fulfillment_location_data


class Command(BaseCommand):
    help = "Backfill location field for orders and their line items via fulfillment_orders API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--store",
            choices=["gimssine", "etoile", "all"],
            default="all",
            help="Store to backfill (default: all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be updated without saving",
        )

    def handle(self, *args, **options):
        store = options["store"]
        dry_run = options["dry_run"]
        stores = ["gimssine", "etoile"] if store == "all" else [store]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved"))

        for store_type in stores:
            if store_type == "gimssine":
                domain = settings.SHOPIFY_GIMSSINE_DOMAIN
                token = settings.SHOPIFY_GIMSSINE_TOKEN
            else:
                domain = settings.SHOPIFY_ETOILE_DOMAIN
                token = settings.SHOPIFY_ETOILE_TOKEN

            orders = Order.objects.filter(store_type=store_type).prefetch_related("line_items").order_by("shopify_order_id")
            total = orders.count()
            self.stdout.write(f"\n[{store_type}] {total} orders to process")

            order_updated = 0
            line_item_updated = 0

            for i, order in enumerate(orders, 1):
                order_location, line_item_map = _build_fulfillment_location_data(
                    domain, token, order.shopify_order_id
                )

                if order.location != order_location:
                    self.stdout.write(
                        f"  [{i}/{total}] #{order.order_number} "
                        f"order: '{order.location or '(empty)'}' → '{order_location or '(empty)'}'"
                    )
                    if not dry_run:
                        order.location = order_location
                        order.save(update_fields=["location"])
                    order_updated += 1

                for line_item in order.line_items.all():
                    expected_loc = line_item_map.get(line_item.shopify_line_item_id, "")
                    if line_item.location != expected_loc:
                        self.stdout.write(
                            f"    line_item {line_item.shopify_line_item_id} "
                            f"'{line_item.location or '(empty)'}' → '{expected_loc or '(empty)'}'"
                        )
                        if not dry_run:
                            line_item.location = expected_loc
                            line_item.save(update_fields=["location"])
                        line_item_updated += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"[{store_type}] done — {order_updated} orders updated, {line_item_updated} line items updated"
                )
            )
