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
        db_table = "orders_customer"


class Order(models.Model):
    shopify_order_id = models.BigIntegerField()
    store_type = models.CharField(
        max_length=20,
        choices=[("gimssine", "Gimssine"), ("etoile", "Etoile")],
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
    note_resolved = models.BooleanField(default=False)
    tags = models.TextField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=100, null=True, blank=True)
    source_name = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=10, blank=True, default="")
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
        db_table = "orders_order"
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
        db_table = "orders_shipping_address"


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
        db_table = "orders_billing_address"


class LineItem(models.Model):
    # @MX:ANCHOR: [AUTO] Core sales line item model — linked to PurchaseOrder via M2M
    # @MX:REASON: Fan-in >= 3: UnorderedItemsView, ConfirmOrderView, PurchaseOrderListView all query LineItem

    PURCHASE_STATUS_CHOICES = [
        ("unordered", "미발주"),
        ("on_hold", "주문보류"),
        ("order_cancelled", "주문취소"),
        ("other_publisher", "타출판사"),
        ("cs_required", "CS필요"),
        ("in_stock", "재고"),
    ]

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
    location = models.CharField(max_length=10, blank=True, default="")
    purchase_status = models.CharField(
        max_length=20,
        choices=PURCHASE_STATUS_CHOICES,
        default="unordered",
    )
    confirmed_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    confirmed_distributor = models.CharField(max_length=50, null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "orders_line_item"
        unique_together = [("order", "shopify_line_item_id")]


class ShippingLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipping_lines")
    shopify_shipping_line_id = models.BigIntegerField()
    title = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=100, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "orders_shipping_line"
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
        db_table = "orders_refund"
        unique_together = [("order", "shopify_refund_id")]


class PurchaseOrder(models.Model):
    """Purchase order issued to a distributor for one or more SKUs."""

    DISTRIBUTOR_CHOICES = [
        ("bookseen", "북센"),
        ("kyobo", "교보"),
        ("choeumgoyuk", "처음교육"),
        ("agape", "아가페"),
        ("sungseoyunion", "성서유니온"),
    ]
    STATUS_CHOICES = [
        ("pending", "발주 대기"),
        ("confirmed", "발주 확정"),
        ("cancelled", "취소"),
    ]

    sku = models.CharField(max_length=255)
    title = models.CharField(max_length=500)
    distributor = models.CharField(max_length=20, choices=DISTRIBUTOR_CHOICES)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    # M2M to LineItem: links the purchase order to the sale line items that triggered it
    line_items = models.ManyToManyField("LineItem", related_name="purchase_orders", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_purchaseorder"
        indexes = [
            models.Index(fields=["distributor"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["sku"]),
        ]

    def __str__(self) -> str:
        return f"PurchaseOrder({self.sku}, {self.distributor}, qty={self.quantity})"


class BookseenData(models.Model):
    """Bookseen distributor vendor data, keyed by SKU."""

    sku = models.CharField(max_length=255, unique=True)
    available = models.BooleanField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(null=True, blank=True)
    returnable = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    arrival = models.CharField(max_length=100, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_booksendata"
        indexes = [models.Index(fields=["sku"])]

    def __str__(self) -> str:
        return f"BookseenData({self.sku})"


class KyoboData(models.Model):
    """Kyobo distributor vendor data, keyed by SKU."""

    sku = models.CharField(max_length=255, unique=True)
    available = models.BooleanField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField(null=True, blank=True)
    returnable = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    publisher = models.CharField(max_length=255, null=True, blank=True)
    ordered_qty = models.IntegerField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_kyobodata"
        indexes = [models.Index(fields=["sku"])]

    def __str__(self) -> str:
        return f"KyoboData({self.sku})"


class VendorComparison(models.Model):
    """Stores auto-selection results (selected distributor) for a SKU."""

    DISTRIBUTOR_CHOICES = [
        ("bookseen", "북센"),
        ("kyobo", "교보"),
        ("warehouse", "재고"),
        ("warehouse_west", "재고-서부확인"),
        ("check_required", "확인필요"),
        ("choeumgoyuk", "처음교육"),
        ("agape", "아가페"),
        ("sungseoyunion", "성서유니온"),
    ]

    sku = models.CharField(max_length=255)
    selected_distributor = models.CharField(
        max_length=20, choices=DISTRIBUTOR_CHOICES, null=True, blank=True
    )
    # Auto-selection metadata fields (SPEC-AUTO-DIST-001)
    candidate_basis = models.CharField(max_length=100, null=True, blank=True)
    price_diff = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_diff_alert = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_vendorcomparison"
        unique_together = [("sku",)]
        indexes = [models.Index(fields=["sku"])]

    def __str__(self) -> str:
        return f"VendorComparison({self.sku})"


class WarehouseStock(models.Model):
    """Warehouse inventory by ISBN and location."""

    LOCATION_CHOICES = [
        ("korea", "한국"),
        ("ca", "CA"),
        ("nj", "NJ"),
    ]

    isbn = models.CharField(max_length=20)
    quantity = models.IntegerField(default=0)
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_warehousestock"
        unique_together = [("isbn", "location")]
        indexes = [models.Index(fields=["isbn"])]

    def __str__(self) -> str:
        return f"WarehouseStock({self.isbn} @ {self.location}: {self.quantity})"


class ExchangeRate(models.Model):
    """
    Daily USD/KRW exchange rate for margin calculation.
    One record per day; effective_date is unique.
    """

    effective_date = models.DateField(unique=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=50, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_exchangerate"
        indexes = [models.Index(fields=["effective_date"])]

    def __str__(self) -> str:
        return f"{self.effective_date}: {self.rate} KRW/USD"


class DistributorVendorRule(models.Model):
    """Maps a publisher name to a secondary distributor (처음교육, 아가페, 성서유니온)."""

    SECONDARY_DISTRIBUTOR_CHOICES = [
        ("choeumgoyuk", "처음교육"),
        ("agape", "아가페"),
        ("sungseoyunion", "성서유니온"),
    ]

    publisher_name = models.CharField(max_length=255, unique=True)
    distributor = models.CharField(max_length=20, choices=SECONDARY_DISTRIBUTOR_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders_distributorvendorrule"
        indexes = [models.Index(fields=["publisher_name"])]

    def __str__(self) -> str:
        return f"DistributorVendorRule({self.publisher_name} -> {self.distributor})"
