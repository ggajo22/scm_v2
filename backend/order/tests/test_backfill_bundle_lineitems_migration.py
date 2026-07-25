"""Tests for the SPEC-SHOPIFY-SKU-SET-002 backfill data migration
(0026_backfill_bundle_lineitems).

Covers:
  AC-011-1  Unordered bundle LineItem backfilled into per-ISBN rows
  AC-011-2  Already-purchase-ordered LineItem excluded from backfill
  AC-011-3  LineItemNote preserved on the reused first-member row only

The migration's RunPython operation is invoked directly (via
MigrationLoader), against the CURRENT (non-historical) app registry. This is
safe here because 0026 is a pure data migration with no schema changes of its
own — by the time this test runs, 0025 (schema) has already been applied to
build the test database, so the real LineItem/ShopifySkuSetMapping models
already match the historical state the migration expects.
"""

import pytest
from django.apps import apps as global_apps
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone

from order.models import LineItem, LineItemNote, Order, PurchaseOrder, ShopifySkuSetMapping


def _run_backfill_migration():
    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0026_backfill_bundle_lineitems")
    operation = migration.operations[0]
    operation.code(global_apps, None)


def _make_order(shopify_order_id: int) -> Order:
    return Order.objects.create(
        shopify_order_id=shopify_order_id,
        store_type="gimssine",
        order_number=shopify_order_id,
        name=f"#{shopify_order_id}",
        shopify_created_at=timezone.now(),
    )


@pytest.mark.django_db
def test_backfill_expands_unordered_bundle_lineitem_into_member_rows():
    """AC-011-1: an unordered, not-purchase-ordered bundle LineItem is
    expanded into exactly N rows (N = member ISBN count): the original PK is
    reused for the first (sort_order-min) member, and N-1 new rows are
    created for the rest — all sharing order/shopify_line_item_id and the
    original (undivided) quantity."""
    bundle_sku = "GITANMATH-F SET"
    for i, isbn in enumerate(["ISBN-A", "ISBN-B", "ISBN-C"]):
        ShopifySkuSetMapping.objects.create(bundle_sku=bundle_sku, member_isbn=isbn, sort_order=i)
    order = _make_order(70001)
    original = LineItem.objects.create(
        order=order,
        shopify_line_item_id=1001,
        sku="GITANMATH-F SET",
        title="기탄수학 F 세트",
        quantity=2,
        purchase_status="unordered",
    )
    original_pk = original.pk

    _run_backfill_migration()

    rows = LineItem.objects.filter(order=order, shopify_line_item_id=1001).order_by("sku")
    assert rows.count() == 3
    assert list(rows.values_list("sku", flat=True)) == ["ISBN-A", "ISBN-B", "ISBN-C"]
    for row in rows:
        assert row.quantity == 2
    assert rows.get(sku="ISBN-A").pk == original_pk  # first member reuses the original row
    assert not LineItem.objects.filter(
        order=order, shopify_line_item_id=1001, sku="GITANMATH-F SET"
    ).exists()


@pytest.mark.django_db
def test_backfill_excludes_already_purchase_ordered_lineitem():
    """AC-011-2: a bundle LineItem already linked to a PurchaseOrder is left
    untouched (still a single row, sku unchanged)."""
    ShopifySkuSetMapping.objects.create(bundle_sku="TEST-SET", member_isbn="ISBN-X", sort_order=0)
    ShopifySkuSetMapping.objects.create(bundle_sku="TEST-SET", member_isbn="ISBN-Y", sort_order=1)
    order = _make_order(70002)
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=1002,
        sku="TEST-SET",
        title="Test Set",
        quantity=1,
        purchase_status="in_stock",
    )
    po = PurchaseOrder.objects.create(
        sku="TEST-SET", title="Test Set", distributor="booxen", quantity=1
    )
    po.line_items.add(li)

    _run_backfill_migration()

    li.refresh_from_db()
    assert li.sku == "TEST-SET"
    assert LineItem.objects.filter(order=order, shopify_line_item_id=1002).count() == 1


@pytest.mark.django_db
def test_backfill_preserves_notes_on_reused_first_row_only():
    """AC-011-3: LineItemNote rows attached to the original LineItem stay on
    the reused first-member row; the newly created N-1 rows get no notes
    (documented, accepted design limitation)."""
    ShopifySkuSetMapping.objects.create(bundle_sku="NOTED-SET", member_isbn="ISBN-P", sort_order=0)
    ShopifySkuSetMapping.objects.create(bundle_sku="NOTED-SET", member_isbn="ISBN-Q", sort_order=1)
    order = _make_order(70003)
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=1003,
        sku="NOTED-SET",
        title="Noted Set",
        quantity=3,
        purchase_status="unordered",
    )
    note = LineItemNote.objects.create(line_item=li, content="CS 확인 필요", assignee="CS")

    _run_backfill_migration()

    first_row = LineItem.objects.get(order=order, shopify_line_item_id=1003, sku="ISBN-P")
    second_row = LineItem.objects.get(order=order, shopify_line_item_id=1003, sku="ISBN-Q")
    assert first_row.pk == li.pk
    assert list(first_row.notes.all()) == [note]
    assert second_row.notes.count() == 0


@pytest.mark.django_db
def test_backfill_is_idempotent_on_second_run():
    """Re-running the backfill (e.g. after a partial failure) does not
    re-expand rows that were already expanded in a prior run, since their sku
    is no longer a bundle_sku after the first pass."""
    ShopifySkuSetMapping.objects.create(bundle_sku="IDEMP-SET", member_isbn="ISBN-M", sort_order=0)
    ShopifySkuSetMapping.objects.create(bundle_sku="IDEMP-SET", member_isbn="ISBN-N", sort_order=1)
    order = _make_order(70004)
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=1004,
        sku="IDEMP-SET",
        title="Idempotent Set",
        quantity=1,
        purchase_status="unordered",
    )

    _run_backfill_migration()
    first_run_count = LineItem.objects.filter(order=order, shopify_line_item_id=1004).count()
    _run_backfill_migration()
    second_run_count = LineItem.objects.filter(order=order, shopify_line_item_id=1004).count()

    assert first_run_count == 2
    assert second_run_count == 2


@pytest.mark.django_db
def test_backfill_noop_when_no_bundle_mappings_exist():
    """When no ShopifySkuSetMapping rows exist at all, the migration is a
    no-op and does not touch any LineItem."""
    order = _make_order(70005)
    LineItem.objects.create(
        order=order,
        shopify_line_item_id=1005,
        sku="REGULAR-SKU",
        title="Regular Book",
        quantity=1,
        purchase_status="unordered",
    )

    _run_backfill_migration()

    assert LineItem.objects.filter(order=order, shopify_line_item_id=1005).count() == 1
    li = LineItem.objects.get(order=order, shopify_line_item_id=1005)
    assert li.sku == "REGULAR-SKU"


@pytest.mark.django_db
def test_migration_reverse_code_is_noop():
    """AC-012-1: reverse_code is RunPython.noop (rollback completes without
    error but does not undo the expansion — documented in the migration's
    module docstring)."""
    from django.db import migrations as dj_migrations

    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0026_backfill_bundle_lineitems")
    operation = migration.operations[0]
    assert operation.reverse_code is dj_migrations.RunPython.noop
