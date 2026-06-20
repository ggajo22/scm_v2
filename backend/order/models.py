from django.db import models


class Customer(models.Model):
    shopify_customer_id = models.BigIntegerField(unique=True)
    email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_customer"


class Order(models.Model):
    shopify_order_id = models.BigIntegerField()
    store_type = models.CharField(
        max_length=20,
        choices=[("booksen", "Booksen"), ("etoile", "Etoile")],
    )
    order_number = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    financial_status = models.CharField(max_length=50, null=True, blank=True)
    fulfillment_status = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    subtotal_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_discounts = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # TextField instead of JSONField for MySQL compatibility
    total_shipping_price_set = models.TextField(null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    gateway = models.CharField(max_length=100, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    tags = models.TextField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=100, null=True, blank=True)
    source_name = models.CharField(max_length=100, null=True, blank=True)
    shopify_created_at = models.DateTimeField(null=True, blank=True)
    shopify_updated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_order"
        unique_together = [("shopify_order_id", "store_type")]
        indexes = [
            models.Index(fields=["store_type"]),
            models.Index(fields=["financial_status"]),
            models.Index(fields=["fulfillment_status"]),
            models.Index(fields=["shopify_created_at"]),
        ]


class ShippingAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="shipping_address")
    name = models.CharField(max_length=200, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    province_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    zip = models.CharField(max_length=30, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "order_shipping_address"


class BillingAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="billing_address")
    name = models.CharField(max_length=200, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    province_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    zip = models.CharField(max_length=30, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "order_billing_address"


class LineItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="line_items")
    shopify_line_item_id = models.BigIntegerField()
    product_id = models.BigIntegerField(null=True, blank=True)
    variant_id = models.BigIntegerField(null=True, blank=True)
    title = models.CharField(max_length=500, null=True, blank=True)
    variant_title = models.CharField(max_length=255, null=True, blank=True)
    sku = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fulfillment_status = models.CharField(max_length=50, null=True, blank=True)
    vendor = models.CharField(max_length=255, null=True, blank=True)
    grams = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "order_line_item"
        unique_together = [("order", "shopify_line_item_id")]


class ShippingLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipping_lines")
    shopify_shipping_line_id = models.BigIntegerField()
    title = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=100, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "order_shipping_line"
        unique_together = [("order", "shopify_shipping_line_id")]


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refunds")
    shopify_refund_id = models.BigIntegerField()
    note = models.TextField(null=True, blank=True)
    shopify_created_at = models.DateTimeField(null=True, blank=True)
    line_item_id = models.BigIntegerField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_refund"
        unique_together = [("order", "shopify_refund_id")]
