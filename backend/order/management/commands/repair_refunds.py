import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from order.models import Order, Refund
from order.shopify_orders import _decimal_or_none, _get_with_headers


class Command(BaseCommand):
    """Recover Refund rows dropped by the pre-0038 sync bug.

    Until migration 0038, `Refund` was unique on (order, shopify_refund_id) and
    `_sync_single_order` stored only `refund_line_items[0]`. A Shopify refund
    covering several line items therefore lost every item after the first, and
    those items kept counting as live stock in every refund-netting query.

    Rebuilds Refund rows from Shopify for orders that already have at least one
    refund. Touches ONLY the Refund table — deliberately not
    `sync_single_order_from_shopify`, which also rewrites line items, location
    and order aggregates.

    Run once per environment after applying migration 0038.
    """

    help = "Re-fetch refunds from Shopify and restore Refund rows lost to the refund_line_items[0] bug"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the missing rows (default: dry run)",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.3,
            help="Seconds to wait between Shopify calls (default: 0.3, respects the REST rate limit)",
        )

    def _credentials(self, store_type):
        if store_type == "gimssine":
            return settings.SHOPIFY_GIMSSINE_DOMAIN, settings.SHOPIFY_GIMSSINE_TOKEN
        return settings.SHOPIFY_ETOILE_DOMAIN, settings.SHOPIFY_ETOILE_TOKEN

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        pause = options["sleep"]

        if not apply_changes:
            # ASCII only in console output: the Windows console runs cp949 here
            # and raises UnicodeEncodeError on characters like an em dash.
            self.stdout.write(self.style.WARNING("DRY RUN - pass --apply to write"))

        order_ids = sorted(set(Refund.objects.values_list("order_id", flat=True)))
        self.stdout.write(f"orders with refunds: {len(order_ids)}")

        added = unchanged = errors = 0
        for order in Order.objects.filter(pk__in=order_ids).iterator():
            domain, token = self._credentials(order.store_type)
            try:
                body, _ = _get_with_headers(domain, token, f"orders/{order.shopify_order_id}.json")
            except Exception as exc:  # noqa: BLE001 — one bad order must not stop the run
                self.stderr.write(self.style.ERROR(f"  {order.name}: {exc}"))
                errors += 1
                continue

            # `or [{}]` keeps a refund with no line items (a pure money/shipping
            # refund) recorded as a header-only row, matching _sync_single_order.
            shopify_rows = [
                (refund, rli)
                for refund in body["order"].get("refunds", [])
                for rli in refund.get("refund_line_items", []) or [{}]
            ]
            existing = set(
                Refund.objects.filter(order=order).values_list("shopify_refund_id", "line_item_id")
            )
            missing = [
                (refund, rli)
                for refund, rli in shopify_rows
                if (refund["id"], rli.get("line_item_id")) not in existing
            ]

            if not missing:
                unchanged += 1
            else:
                self.stdout.write(f"  {order.name}: +{len(missing)} refund row(s)")
                for refund, rli in missing:
                    self.stdout.write(
                        f"      refund={refund['id']} line_item_id={rli.get('line_item_id')} "
                        f"qty={rli.get('quantity')}"
                    )
                if apply_changes:
                    with transaction.atomic():
                        for refund, rli in missing:
                            Refund.objects.update_or_create(
                                order=order,
                                shopify_refund_id=refund["id"],
                                line_item_id=rli.get("line_item_id"),
                                defaults={
                                    "note": refund.get("note"),
                                    "shopify_created_at": refund.get("created_at"),
                                    "quantity": rli.get("quantity"),
                                    "subtotal": _decimal_or_none(rli.get("subtotal")),
                                    "total_tax": _decimal_or_none(rli.get("total_tax")),
                                },
                            )
                added += len(missing)

            time.sleep(pause)

        verb = "added" if apply_changes else "to add"
        self.stdout.write(
            self.style.SUCCESS(
                f"done: rows {verb}={added}, orders unchanged={unchanged}, errors={errors}"
            )
        )
