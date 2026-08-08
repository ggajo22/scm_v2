"""Tests for the SPEC-ORDER-011 backfill data migration
(0031_backfill_order_status).

Covers:
  AC-LOGI-012  (a) Orders with >=1 trackable LineItem recomputed per REQ-LOGI-008
  T10          (b) Orders with 0 trackable LineItems left untouched (accepted gap)

The migration's RunPython operation is invoked directly (via MigrationLoader)
against the CURRENT (non-historical) app registry — safe here because 0031 is
a pure data migration with no schema changes of its own, and by the time this
test runs, 0030 (schema: LineItem.logistics_status + Order.status choices)
has already been applied to build the test database. Mirrors
test_backfill_bundle_lineitems_migration.py's established pattern.
"""

import pytest
from django.apps import apps as global_apps
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from order.models import LineItem, Order


def _run_backfill_migration():
    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0031_backfill_order_status")
    operation = migration.operations[0]
    operation.code(global_apps, None)


def _make_order(shopify_order_id: int, **kwargs) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type="gimssine", **kwargs)


@pytest.mark.django_db
def test_backfill_recomputes_order_with_uniform_trackable_lineitems():
    """(a) Orders with >=1 trackable LineItem get correctly recomputed —
    uniform logistics_status case."""
    order = _make_order(71001, status="paid")
    LineItem.objects.create(
        order=order, shopify_line_item_id=1, sku="ISBN-BF-1", quantity=1,
        logistics_status="received",
    )
    LineItem.objects.create(
        order=order, shopify_line_item_id=2, sku="ISBN-BF-2", quantity=1,
        logistics_status="received",
    )

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.status == "received"


@pytest.mark.django_db
def test_backfill_recomputes_order_with_mixed_trackable_lineitems_as_partial():
    """(a) Orders with >=1 trackable LineItem get correctly recomputed —
    mixed logistics_status case -> 'partial'."""
    order = _make_order(71002, status="paid")
    LineItem.objects.create(
        order=order, shopify_line_item_id=1, sku="ISBN-BF-3", quantity=1,
        logistics_status="not_shipped",
    )
    LineItem.objects.create(
        order=order, shopify_line_item_id=2, sku="ISBN-BF-4", quantity=1,
        logistics_status="shipped",
    )

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.status == "partial"


@pytest.mark.django_db
def test_backfill_leaves_orders_with_zero_trackable_lineitems_untouched():
    """(b) Orders with 0 trackable LineItems (sku IS NULL on every child)
    keep their stale pre-backfill status value untouched — this is a known,
    accepted gap per REQ-LOGI-012's exact scope, not a defect."""
    order = _make_order(71003, status="paid")
    LineItem.objects.create(order=order, shopify_line_item_id=1, sku=None, quantity=1)

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.status == "paid"


@pytest.mark.django_db
def test_backfill_noop_when_no_trackable_lineitems_exist_anywhere():
    """No trackable LineItem in the whole DB -> migration is a no-op."""
    order = _make_order(71004, status="paid")

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.status == "paid"


@pytest.mark.django_db
def test_backfill_ignores_orders_with_no_lineitems_at_all():
    order = _make_order(71005, status=None)

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.status is None


@pytest.mark.django_db
def test_migration_reverse_code_is_noop():
    """reverse_code is RunPython.noop — rollback completes without error but
    does not undo the recomputation (documented in the migration's module
    docstring)."""
    from django.db import migrations as dj_migrations

    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0031_backfill_order_status")
    operation = migration.operations[0]
    assert operation.reverse_code is dj_migrations.RunPython.noop


@pytest.mark.django_db
def test_migration_dependency_chain():
    """0030 depends on 0029 (SPEC-PURCHASE-ORDER-010's migration, which
    claimed the 0029 slot first); 0031 depends on 0030."""
    loader = MigrationLoader(connection)
    m0030 = loader.disk_migrations[
        ("order", "0030_lineitem_logistics_status_alter_order_status")
    ]
    m0031 = loader.disk_migrations[("order", "0031_backfill_order_status")]
    assert m0030.dependencies == [("order", "0029_lineitem_damaged_exchange_status")]
    assert m0031.dependencies == [
        ("order", "0030_lineitem_logistics_status_alter_order_status")
    ]
