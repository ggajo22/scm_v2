"""Tests for the title-data-bug follow-up backfill migration
(0027_backfill_bundle_title_data), fixing a bug introduced by
SPEC-SHOPIFY-SKU-SET-002 (commit e9a6f42).

Covers:
  LineItem.title backfill  — rows in the exact wrong state
                              (sku=member_isbn, title=bundle_sku) get
                              corrected to the real book title, or None
                              when the ISBN isn't in the catalog.
  Precision/idempotency     — rows already correct, or unrelated to any
                              bundle mapping, are left untouched.
  PurchaseOrder.title backfill — same wrong-state signature, corrected to
                              the real book title, or the ISBN itself as a
                              fallback (title is NON-nullable).

The migration's two RunPython operations are invoked directly (via
MigrationLoader), against the CURRENT (non-historical) app registry — same
approach as test_backfill_bundle_lineitems_migration.py, valid here because
0027 is a pure data migration with no schema changes of its own.
"""

import pytest
from django.apps import apps as global_apps
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone

from book.models import Info, Inven
from order.models import LineItem, Order, PurchaseOrder, ShopifySkuSetMapping


def _run_lineitem_backfill():
    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0027_backfill_bundle_title_data")
    operation = migration.operations[0]
    operation.code(global_apps, None)


def _run_purchase_order_backfill():
    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0027_backfill_bundle_title_data")
    operation = migration.operations[1]
    operation.code(global_apps, None)


def _make_order(shopify_order_id: int) -> Order:
    return Order.objects.create(
        shopify_order_id=shopify_order_id,
        store_type="gimssine",
        order_number=shopify_order_id,
        name=f"#{shopify_order_id}",
        shopify_created_at=timezone.now(),
    )


# ---------------------------------------------------------------------------
# LineItem.title backfill
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_backfill_corrects_lineitem_title_to_real_book_title():
    """A LineItem in the exact wrong state (sku=member_isbn,
    title=bundle_sku) gets title corrected to the real catalog title."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-A", sort_order=0
    )
    inven = Inven.objects.create(inven_SKU="ISBN-A")
    Info.objects.create(inven=inven, name="기탄수학 F1")

    order = _make_order(80001)
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=2001,
        sku="ISBN-A",
        title="GITANMATH-F SET",  # wrong: bundle's own title
        quantity=2,
        purchase_status="unordered",
    )

    _run_lineitem_backfill()

    li.refresh_from_db()
    assert li.title == "기탄수학 F1"


@pytest.mark.django_db
def test_backfill_sets_lineitem_title_to_none_when_isbn_not_in_catalog():
    """A wrong-state LineItem whose ISBN has no Inven/Info match gets
    title=None — not left as the bundle title, not an empty string."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-UNCATALOGED", sort_order=0
    )
    order = _make_order(80002)
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=2002,
        sku="ISBN-UNCATALOGED",
        title="GITANMATH-F SET",
        quantity=1,
        purchase_status="unordered",
    )

    _run_lineitem_backfill()

    li.refresh_from_db()
    assert li.title is None


@pytest.mark.django_db
def test_backfill_does_not_touch_already_correct_lineitem_title():
    """A LineItem whose title already matches its own real book title (not
    the bundle title) is left untouched — precision check."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-A", sort_order=0
    )
    inven = Inven.objects.create(inven_SKU="ISBN-A")
    Info.objects.create(inven=inven, name="기탄수학 F1")

    order = _make_order(80003)
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=2003,
        sku="ISBN-A",
        title="기탄수학 F1",  # already correct
        quantity=1,
        purchase_status="unordered",
    )

    _run_lineitem_backfill()

    li.refresh_from_db()
    assert li.title == "기탄수학 F1"


@pytest.mark.django_db
def test_backfill_does_not_touch_unrelated_lineitem():
    """A LineItem whose sku has no bundle mapping at all is left completely
    untouched, regardless of its title value."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-A", sort_order=0
    )
    order = _make_order(80004)
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=2004,
        sku="REGULAR-SKU",
        title="Some Regular Title",
        quantity=1,
        purchase_status="unordered",
    )

    _run_lineitem_backfill()

    li.refresh_from_db()
    assert li.title == "Some Regular Title"


@pytest.mark.django_db
def test_backfill_does_not_touch_lineitem_with_different_title_manually_edited():
    """A LineItem whose sku matches a member_isbn but whose title does NOT
    equal the bundle_sku (e.g. manually corrected already) is left
    untouched — the precise (sku, title) signature must both match."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-A", sort_order=0
    )
    order = _make_order(80005)
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=2005,
        sku="ISBN-A",
        title="Manually Fixed Title",
        quantity=1,
        purchase_status="unordered",
    )

    _run_lineitem_backfill()

    li.refresh_from_db()
    assert li.title == "Manually Fixed Title"


# ---------------------------------------------------------------------------
# PurchaseOrder.title backfill
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_backfill_corrects_purchase_order_title_to_real_book_title():
    """A PurchaseOrder in the wrong-state signature (sku=member_isbn,
    title=bundle_sku) gets title corrected to the real catalog title."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-A", sort_order=0
    )
    inven = Inven.objects.create(inven_SKU="ISBN-A")
    Info.objects.create(inven=inven, name="기탄수학 F1")

    po = PurchaseOrder.objects.create(
        sku="ISBN-A",
        title="GITANMATH-F SET",  # wrong: bundle's own title
        distributor="booxen",
        quantity=2,
        status="confirmed",
    )

    _run_purchase_order_backfill()

    po.refresh_from_db()
    assert po.title == "기탄수학 F1"


@pytest.mark.django_db
def test_backfill_falls_back_to_isbn_for_purchase_order_title_when_uncataloged():
    """PurchaseOrder.title is non-nullable: when no catalog title is found,
    the fallback is the sku (ISBN) itself, matching the
    `title = unordered_lis[0].title or sku` convention used elsewhere."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-UNCATALOGED", sort_order=0
    )
    po = PurchaseOrder.objects.create(
        sku="ISBN-UNCATALOGED",
        title="GITANMATH-F SET",
        distributor="booxen",
        quantity=1,
        status="confirmed",
    )

    _run_purchase_order_backfill()

    po.refresh_from_db()
    assert po.title == "ISBN-UNCATALOGED"
    assert po.title is not None  # never None: field is non-nullable


@pytest.mark.django_db
def test_backfill_does_not_touch_unrelated_purchase_order():
    """A PurchaseOrder whose sku has no bundle mapping is left untouched."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-A", sort_order=0
    )
    po = PurchaseOrder.objects.create(
        sku="REGULAR-SKU",
        title="Some Regular Title",
        distributor="booxen",
        quantity=1,
        status="confirmed",
    )

    _run_purchase_order_backfill()

    po.refresh_from_db()
    assert po.title == "Some Regular Title"


@pytest.mark.django_db
def test_backfill_does_not_touch_purchase_order_already_correct():
    """A PurchaseOrder whose title already matches its own real book title
    is left untouched — precision check, and idempotency across re-runs."""
    ShopifySkuSetMapping.objects.create(
        bundle_sku="GITANMATH-F SET", member_isbn="ISBN-A", sort_order=0
    )
    inven = Inven.objects.create(inven_SKU="ISBN-A")
    Info.objects.create(inven=inven, name="기탄수학 F1")
    po = PurchaseOrder.objects.create(
        sku="ISBN-A",
        title="기탄수학 F1",
        distributor="booxen",
        quantity=1,
        status="confirmed",
    )

    _run_purchase_order_backfill()
    _run_purchase_order_backfill()  # idempotency: second run is a no-op

    po.refresh_from_db()
    assert po.title == "기탄수학 F1"


@pytest.mark.django_db
def test_migration_reverse_code_is_noop_for_both_operations():
    """Both RunPython operations use reverse_code=migrations.RunPython.noop
    (rollback completes without error but does not undo the correction —
    documented in the migration's module docstring)."""
    from django.db import migrations as dj_migrations

    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0027_backfill_bundle_title_data")
    for operation in migration.operations:
        assert operation.reverse_code is dj_migrations.RunPython.noop


@pytest.mark.django_db
def test_backfill_noop_when_no_bundle_mappings_exist():
    """When no ShopifySkuSetMapping rows exist, both operations are no-ops
    and do not touch any LineItem or PurchaseOrder."""
    order = _make_order(80006)
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=2006,
        sku="REGULAR-SKU",
        title="Regular Book",
        quantity=1,
        purchase_status="unordered",
    )
    po = PurchaseOrder.objects.create(
        sku="REGULAR-SKU", title="Regular Book", distributor="booxen", quantity=1
    )

    _run_lineitem_backfill()
    _run_purchase_order_backfill()

    li.refresh_from_db()
    po.refresh_from_db()
    assert li.title == "Regular Book"
    assert po.title == "Regular Book"
