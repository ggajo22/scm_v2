"""
Management command to create PurchaseOrders for unordered LineItems
belonging to specified order numbers.

Usage:
    python manage.py process_purchase_orders --orders 1001 1002 1003
    python manage.py process_purchase_orders --orders 1001 --distributor booxen
    python manage.py process_purchase_orders --orders 1001 1002 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum

from order.models import DistributorVendorRule, LineItem, Order, PurchaseOrder

VALID_DISTRIBUTORS = {"booxen", "kyobo", "choeumgoyuk", "agape"}


class Command(BaseCommand):
    help = "Create PurchaseOrders for unordered line items in the given order numbers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--orders",
            nargs="+",
            type=str,
            required=True,
            help="Order numbers to process (e.g. --orders 1001 1002 1003 or #1001 #1002)",
        )
        parser.add_argument(
            "--store",
            choices=["gimssine", "etoile", "all"],
            default="all",
            help="Limit to a specific store (default: all)",
        )
        parser.add_argument(
            "--distributor",
            choices=sorted(VALID_DISTRIBUTORS),
            default=None,
            help="Fallback distributor when no DistributorVendorRule matches the vendor",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without saving anything",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        fallback_distributor: str | None = options["distributor"]
        store: str = options["store"]
        raw_orders: list[str] = options["orders"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved\n"))

        # Normalize inputs — split into numeric order_numbers and name strings (e.g. EB10011705)
        numeric_ids: list[int] = []
        name_keys: list[str] = []
        for raw in raw_orders:
            clean = raw.lstrip("#").strip()
            if clean.isdigit():
                numeric_ids.append(int(clean))
            else:
                # Store both bare (EB10011705) and prefixed (#EB10011705) for name lookup
                name_keys.append(clean)
                name_keys.append(f"#{clean}")

        # Fetch matching orders (numeric order_number OR name field)
        from django.db.models import Q
        q = Q()
        if numeric_ids:
            q |= Q(order_number__in=numeric_ids)
        if name_keys:
            q |= Q(name__in=name_keys)

        order_qs = Order.objects.filter(q)
        if store != "all":
            order_qs = order_qs.filter(store_type=store)

        found_numbers = set(order_qs.values_list("order_number", flat=True))
        found_names = set(order_qs.values_list("name", flat=True))

        missing = []
        for raw in raw_orders:
            clean = raw.lstrip("#").strip()
            if clean.isdigit():
                if int(clean) not in found_numbers:
                    missing.append(raw)
            else:
                if clean not in found_names and f"#{clean}" not in found_names:
                    missing.append(raw)
        if missing:
            self.stdout.write(
                self.style.WARNING(f"Orders not found in DB: {missing}")
            )

        if not order_qs.exists():
            raise CommandError("No matching orders found.")

        # Find unordered LineItems for these orders
        line_items = (
            LineItem.objects
            .filter(order__in=order_qs, sku__isnull=False)
            .exclude(purchase_orders__isnull=False)
            .select_related("order")
        )

        if not line_items.exists():
            self.stdout.write(self.style.SUCCESS("No unordered line items found — nothing to do."))
            return

        # Load vendor rules: publisher_name → distributor
        rule_map: dict[str, str] = dict(
            DistributorVendorRule.objects.values_list("publisher_name", "distributor")
        )

        # Group line items by SKU
        sku_map: dict[str, dict] = {}
        for li in line_items:
            sku = li.sku
            if sku not in sku_map:
                sku_map[sku] = {
                    "title": li.title or sku,
                    "vendor": li.vendor or "",
                    "total_quantity": 0,
                    "line_items": [],
                }
            sku_map[sku]["total_quantity"] += li.quantity or 0
            sku_map[sku]["line_items"].append(li)

        # Resolve distributor per SKU — fallback to booxen if no rule and no --distributor
        DEFAULT_DISTRIBUTOR = "booxen"
        skus_to_create: list[dict] = []

        for sku, info in sku_map.items():
            vendor = info["vendor"]
            distributor = rule_map.get(vendor) or fallback_distributor or DEFAULT_DISTRIBUTOR
            info["distributor"] = distributor
            skus_to_create.append({"sku": sku, **info})

        # Print summary
        self.stdout.write(f"\nOrders to process : {sorted(found_numbers)}")
        self.stdout.write(f"Unordered SKUs    : {len(sku_map)}")
        self.stdout.write(f"Will create POs   : {len(skus_to_create)}\n")

        for item in skus_to_create:
            self.stdout.write(
                f"  SKU={item['sku']}  qty={item['total_quantity']}"
                f"  dist={item['distributor']}  title={item['title'][:40]}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete — no records written."))
            return

        # Create PurchaseOrders atomically
        created_count = 0
        try:
            with transaction.atomic():
                for item in skus_to_create:
                    po = PurchaseOrder.objects.create(
                        sku=item["sku"],
                        title=item["title"],
                        distributor=item["distributor"],
                        quantity=item["total_quantity"],
                        status="pending",
                    )
                    po.line_items.add(*item["line_items"])
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Created PO #{po.pk}: {item['sku']} × {item['total_quantity']} → {item['distributor']}"
                        )
                    )
        except Exception as exc:
            raise CommandError(f"Transaction rolled back: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(f"\nDone — {created_count} PurchaseOrder(s) created.")
        )
