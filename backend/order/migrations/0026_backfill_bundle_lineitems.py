# SPEC-SHOPIFY-SKU-SET-002 REQ-SKUSET2-011/012: one-time backfill of existing
# unordered bundle-SKU LineItem rows into per-member-ISBN rows.
#
# This migration MUST be applied after 0025_lineitem_unique_together_with_sku
# (the unique_together widened to include sku) — applying it before 0025 would
# raise an IntegrityError the moment two split rows share
# (order, shopify_line_item_id) with the old 2-column constraint still active.
#
# For each unordered, not-yet-purchase-ordered LineItem whose sku matches a
# ShopifySkuSetMapping.bundle_sku:
#   - the first (min sort_order) member ISBN reuses the ORIGINAL row (UPDATE
#     sku in place) — this preserves the PK and any LineItemNote FK relations.
#   - the remaining member ISBNs get NEW LineItem rows copying the other
#     fields verbatim (quantity is NOT divided — REQ-SKUSET2-006 depends on
#     every split row carrying the full, undivided quantity).
#
# Known, accepted limitation (documented, not a bug — see REQ-SKUSET2-011):
# LineItemNote rows attached to the original LineItem stay only on the reused
# first-member row; they are NOT duplicated to the newly created N-1 rows.
#
# reverse_code is RunPython.noop: a full reverse backfill (merging N rows back
# into 1) is NOT possible without information loss — once split, there is no
# reliable way to tell which row was "the original" if e.g. purchase_status or
# notes have since diverged between the split rows. Rolling back this
# migration leaves the already-expanded rows in place; it does not undo the
# expansion.

from django.db import migrations


def backfill_bundle_lineitems(apps, schema_editor):
    LineItem = apps.get_model("order", "LineItem")
    ShopifySkuSetMapping = apps.get_model("order", "ShopifySkuSetMapping")

    bundle_skus = list(
        ShopifySkuSetMapping.objects.values_list("bundle_sku", flat=True).distinct()
    )
    if not bundle_skus:
        return

    targets = list(
        LineItem.objects.filter(
            purchase_status="unordered",
            purchase_orders__isnull=True,
            sku__in=bundle_skus,
        )
    )

    for li in targets:
        member_isbns = list(
            ShopifySkuSetMapping.objects.filter(bundle_sku=li.sku)
            .order_by("sort_order")
            .values_list("member_isbn", flat=True)
        )
        if not member_isbns:
            # Defensive: mapping members were removed between the bundle_skus
            # snapshot above and this row's processing. Leave the row as-is
            # rather than risk silent data loss.
            continue

        first_isbn, *rest_isbns = member_isbns

        li.sku = first_isbn
        li.save(update_fields=["sku"])

        for member_isbn in rest_isbns:
            LineItem.objects.create(
                order_id=li.order_id,
                shopify_line_item_id=li.shopify_line_item_id,
                product_id=li.product_id,
                variant_id=li.variant_id,
                title=li.title,
                variant_title=li.variant_title,
                sku=member_isbn,
                quantity=li.quantity,
                price=li.price,
                total_discount=li.total_discount,
                fulfillment_status=li.fulfillment_status,
                vendor=li.vendor,
                grams=li.grams,
                location=li.location,
                purchase_status=li.purchase_status,
                confirmed_price=li.confirmed_price,
                confirmed_distributor=li.confirmed_distributor,
                confirmed_at=li.confirmed_at,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0025_lineitem_unique_together_with_sku'),
    ]

    operations = [
        migrations.RunPython(backfill_bundle_lineitems, migrations.RunPython.noop),
    ]
