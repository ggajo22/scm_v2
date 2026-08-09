"""Tests for the SPEC-ORDER-012 backfill data migration
(0033_backfill_order_ready_to_ship).

Covers:
  AC-RTS-006  every pre-existing Order gets ready_to_ship consistent with
              REQ-RTS-002's rule.

The migration's RunPython operation is invoked directly (via MigrationLoader)
against the CURRENT (non-historical) app registry — safe here because 0033
is a pure data migration with no schema changes of its own, and by the time
this test runs, 0032 (schema: Order.ready_to_ship) has already been applied
to build the test database. Mirrors
test_backfill_order_status_migration.py's established pattern.
"""

import pytest
from django.apps import apps as global_apps
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from order.models import LineItem, Order


def _run_backfill_migration():
    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0033_backfill_order_ready_to_ship")
    operation = migration.operations[0]
    operation.code(global_apps, None)


def _make_order(shopify_order_id: int, **kwargs) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type="gimssine", **kwargs)


@pytest.mark.django_db
def test_backfill_sets_null_for_all_cancelled_lineitems():
    order = _make_order(72001)
    LineItem.objects.create(
        order=order, shopify_line_item_id=1, sku="ISBN-RTS-BF-1", quantity=1,
        purchase_status="order_cancelled",
    )

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.ready_to_ship is None


@pytest.mark.django_db
def test_backfill_sets_false_when_cs_required_present():
    order = _make_order(72002)
    LineItem.objects.create(
        order=order, shopify_line_item_id=1, sku="ISBN-RTS-BF-2", quantity=1,
        purchase_status="cs_required",
    )
    LineItem.objects.create(
        order=order, shopify_line_item_id=2, sku="ISBN-RTS-BF-3", quantity=1,
        logistics_status="received",
    )

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.ready_to_ship is False


@pytest.mark.django_db
def test_backfill_sets_true_when_all_satisfied():
    order = _make_order(72003)
    LineItem.objects.create(
        order=order, shopify_line_item_id=1, sku="ISBN-RTS-BF-4", quantity=1,
        purchase_status="in_stock", logistics_status="not_shipped",
    )
    LineItem.objects.create(
        order=order, shopify_line_item_id=2, sku="ISBN-RTS-BF-5", quantity=1,
        logistics_status="received",
    )

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.ready_to_ship is True


@pytest.mark.django_db
def test_backfill_sets_false_when_partially_satisfied():
    order = _make_order(72004)
    LineItem.objects.create(
        order=order, shopify_line_item_id=1, sku="ISBN-RTS-BF-6", quantity=1,
        logistics_status="received",
    )
    LineItem.objects.create(
        order=order, shopify_line_item_id=2, sku="ISBN-RTS-BF-7", quantity=1,
        purchase_status="on_hold", logistics_status="not_shipped",
    )

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.ready_to_ship is False


@pytest.mark.django_db
def test_backfill_leaves_orders_with_zero_trackable_lineitems_as_null():
    """Orders with 0 trackable LineItems are never touched by the backfill
    (unlike 0031's Order.status gap, NULL is already the correct
    REQ-RTS-002 value here, so no explicit update is needed)."""
    order = _make_order(72005)
    LineItem.objects.create(order=order, shopify_line_item_id=1, sku=None, quantity=1)

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.ready_to_ship is None


@pytest.mark.django_db
def test_backfill_noop_when_no_trackable_lineitems_exist_anywhere():
    order = _make_order(72006)

    _run_backfill_migration()

    order.refresh_from_db()
    assert order.ready_to_ship is None


@pytest.mark.django_db
def test_migration_reverse_code_is_noop():
    from django.db import migrations as dj_migrations

    loader = MigrationLoader(connection)
    migration = loader.get_migration("order", "0033_backfill_order_ready_to_ship")
    operation = migration.operations[0]
    assert operation.reverse_code is dj_migrations.RunPython.noop


@pytest.mark.django_db
def test_migration_dependency_chain():
    loader = MigrationLoader(connection)
    m0032 = loader.disk_migrations[("order", "0032_order_ready_to_ship")]
    m0033 = loader.disk_migrations[("order", "0033_backfill_order_ready_to_ship")]
    assert m0032.dependencies == [("order", "0031_backfill_order_status")]
    assert m0033.dependencies == [("order", "0032_order_ready_to_ship")]
