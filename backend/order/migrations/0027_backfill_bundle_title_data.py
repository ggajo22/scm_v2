# Follow-up fix for SPEC-SHOPIFY-SKU-SET-002 (title-data bug, commit e9a6f42).
#
# 0026_backfill_bundle_lineitems correctly split existing bundle Shopify line
# items into per-member-ISBN LineItem rows, but the sync pipeline at that
# time (and 0026 itself, which copies fields "verbatim" from the original
# row) reused the bundle's own Shopify-reported title (e.g. "GITANMATH-F
# SET") for every split row instead of looking up each member ISBN's own
# book title. shopify_orders._sync_single_order() has since been fixed at
# the source; this migration backfills the leftover wrong title data in two
# places:
#
#   1. LineItem.title  — nullable; wrong rows are identified precisely via
#      the (sku=member_isbn, title=bundle_sku) signature, since that state
#      can ONLY be reached by the bug (a member ISBN literally titled with
#      its own bundle's SKU string). Rows already correct, or manually
#      edited since, are left untouched.
#
#   2. PurchaseOrder.title — a title SNAPSHOT copied from LineItem.title at
#      PO-confirmation time (purchase_order_views.py). Because it is a
#      snapshot, fixing the sync pipeline alone does NOT correct
#      already-created POs — they carry the same wrong-title signature and
#      need their own backfill. Unlike LineItem.title, PurchaseOrder.title
#      is a NON-nullable CharField, so rows with no catalog match fall back
#      to the sku (ISBN) itself — the same `title = unordered_lis[0].title
#      or sku` convention already used at PO-confirmation time.
#
# Depends on 0026_backfill_bundle_lineitems: that migration is what produced
# (or left in place, for pre-existing rows) the exact wrong-title state this
# migration corrects — it must have already run.
#
# reverse_code is RunPython.noop for both operations: this migration
# corrects title *data*, not schema, and there is no reliable way to
# distinguish "still in the original wrong state" from "manually re-titled
# to something else since" once this migration has run. Unlike 0026 (which
# risks losing which-row-was-original PK/relation information), no
# structural information is at risk here either way — reversal is simply
# not a meaningful operation for a plain data correction.

from django.db import migrations


def _build_title_map(apps, isbn_list):
    """Batch-query real book titles for a list of ISBNs (historical models).

    Mirrors the same Inven/Info join pattern used elsewhere in this codebase
    (shopify_sku_set_views._build_title_map, shopify_orders._build_title_map).
    """
    if not isbn_list:
        return {}
    Inven = apps.get_model("book", "Inven")
    rows = (
        Inven.objects.filter(inven_SKU__in=isbn_list)
        .select_related("info")
        .values("inven_SKU", "info__name")
    )
    return {row["inven_SKU"]: row["info__name"] for row in rows}


def backfill_lineitem_titles(apps, schema_editor):
    LineItem = apps.get_model("order", "LineItem")
    ShopifySkuSetMapping = apps.get_model("order", "ShopifySkuSetMapping")

    pairs = list(ShopifySkuSetMapping.objects.values_list("bundle_sku", "member_isbn"))
    if not pairs:
        return

    member_isbns = {member_isbn for _, member_isbn in pairs}
    title_map = _build_title_map(apps, list(member_isbns))

    for bundle_sku, member_isbn in pairs:
        # Precise wrong-state signature: sku is already the member ISBN, but
        # title still literally equals the bundle SKU string.
        LineItem.objects.filter(sku=member_isbn, title=bundle_sku).update(
            title=title_map.get(member_isbn)
        )


def backfill_purchase_order_titles(apps, schema_editor):
    PurchaseOrder = apps.get_model("order", "PurchaseOrder")
    ShopifySkuSetMapping = apps.get_model("order", "ShopifySkuSetMapping")

    pairs = list(ShopifySkuSetMapping.objects.values_list("bundle_sku", "member_isbn"))
    if not pairs:
        return

    member_isbns = {member_isbn for _, member_isbn in pairs}
    title_map = _build_title_map(apps, list(member_isbns))

    for bundle_sku, member_isbn in pairs:
        # PurchaseOrder.title is NON-nullable: fall back to the sku (ISBN)
        # itself when no catalog title is found, matching the
        # `title = unordered_lis[0].title or sku` convention used at
        # PO-confirmation time.
        real_title = title_map.get(member_isbn) or member_isbn
        PurchaseOrder.objects.filter(sku=member_isbn, title=bundle_sku).update(title=real_title)


class Migration(migrations.Migration):
    dependencies = [
        ("order", "0026_backfill_bundle_lineitems"),
    ]

    operations = [
        migrations.RunPython(backfill_lineitem_titles, migrations.RunPython.noop),
        migrations.RunPython(backfill_purchase_order_titles, migrations.RunPython.noop),
    ]
