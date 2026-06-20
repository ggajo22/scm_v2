import pytest
from django.db import IntegrityError

from order.models import Customer, Order


@pytest.mark.django_db
def test_order_unique_together():
    Order.objects.create(shopify_order_id=1001, store_type="booksen")
    with pytest.raises(IntegrityError):
        Order.objects.create(shopify_order_id=1001, store_type="booksen")


@pytest.mark.django_db
def test_order_unique_together_different_store_allowed():
    Order.objects.create(shopify_order_id=1001, store_type="booksen")
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
    order = Order.objects.create(shopify_order_id=2001, store_type="booksen", customer=None)
    assert order.customer is None
