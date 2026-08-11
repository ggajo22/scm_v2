import pytest
from django.db import IntegrityError

from order.models import Customer, Order


@pytest.mark.django_db
def test_order_unique_together():
    Order.objects.create(shopify_order_id=1001, store_type="gimssine")
    with pytest.raises(IntegrityError):
        Order.objects.create(shopify_order_id=1001, store_type="gimssine")


@pytest.mark.django_db
def test_order_unique_together_different_store_allowed():
    Order.objects.create(shopify_order_id=1001, store_type="gimssine")
    # same shopify_order_id, different store_type is allowed
    order = Order.objects.create(shopify_order_id=1001, store_type="etoile")
    assert order.pk is not None


@pytest.mark.django_db
def test_customer_unique_shopify_id():
    Customer.objects.create(shopify_customer_id=9001)
    with pytest.raises(IntegrityError):
        Customer.objects.create(shopify_customer_id=9001)


@pytest.mark.django_db
def test_order_customer_fk_nullable():
    order = Order.objects.create(shopify_order_id=2001, store_type="gimssine", customer=None)
    assert order.customer is None


def test_order_name_field_has_db_index():
    """Order.name is used as the sole exact-match lookup key by
    UploadRackNumberView, LineItemBulkRackNumberUpdateView (SPEC-ORDER-013)
    and _process_outbound_rows (SPEC-ORDER-015). Without an index, every
    lookup performs a full table scan, which is measured to take ~140ms on
    a dev DB with only 3,109 rows and degrades further at production scale
    (500k+ rows per product.md). This test asserts a db-level index exists
    on Order.name so the query planner can use it, independent of any
    specific backend's EXPLAIN output (portable across SQLite/MySQL/CI).
    """
    indexed_field_sets = [tuple(index.fields) for index in Order._meta.indexes]
    assert ("name",) in indexed_field_sets, (
        "Order.name must be covered by a db index (models.Index(fields=['name'])) "
        "to avoid full table scans on the exact-match lookups performed by "
        "SPEC-ORDER-013 and SPEC-ORDER-015 views."
    )
