from django.conf import settings
from django.db import models

# SPEC-ORDER-011 REQ-LOGI-001: module-level (not class-nested) so both
# LineItem.logistics_status and Order.status (aggregate — see Order.Meta
# below) can share the same 5-value choices list without cross-importing
# between the two model classes.
LOGISTICS_STATUS_CHOICES = [
    ("not_shipped", "미입고"),
    ("shipment_confirmed", "입고예정"),
    ("received", "입고"),
    ("outbound_scheduled", "출고예정"),
    ("shipped", "출고"),
]


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
    # SPEC-ORDER-011 REQ-LOGI-008: computed aggregate over trackable (sku not
    # null) child LineItems' logistics_status — see
    # purchase_order_views._recompute_order_aggregates() (renamed from
    # _recompute_order_status() by SPEC-ORDER-012). Column itself
    # (max_length=50, null=True, blank=True) is unchanged; only `choices` is
    # added for documentation/validation (decision D). No longer populated
    # from Shopify's financial_status (REQ-LOGI-011).
    status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=LOGISTICS_STATUS_CHOICES + [("partial", "부분입고")],
    )
    # SPEC-ORDER-012 REQ-RTS-001/002: computed aggregate over trackable (sku
    # not null) child LineItems' purchase_status/logistics_status — see
    # purchase_order_views._recompute_order_aggregates(). Fully independent
    # of Order.status (decision A). Three states: True (ready), False (not
    # ready), None (zero non-excluded trackable LineItems). Calculated only
    # — no manual PATCH endpoint exists for this field (decision E). Never
    # populated from Shopify-sourced fields (REQ-RTS-005).
    ready_to_ship = models.BooleanField(null=True, blank=True)
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
            # @MX:NOTE: [AUTO] SPEC-ORDER-013 (UploadRackNumberView,
            # LineItemBulkRackNumberUpdateView) and SPEC-ORDER-015
            # (_process_outbound_rows) both use Order.name as the sole
            # exact-match lookup key — SPEC-ORDER-015 as a single batched
            # `name__in` fetch covering every (order_name, sku) group in the
            # request. Without this index the lookup is a full table scan
            # (~140ms at 3,109 rows in dev; much worse at product.md's stated
            # 500k+ row production scale), and batching does not remove that
            # cost — it just stops paying it once per group.
            # See performance fixes following SPEC-ORDER-015.
            models.Index(fields=["name"]),
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
        # SPEC-PURCHASE-ORDER-010 REQ-DMG-001: re-enters the reorder queue
        # regardless of existing PurchaseOrder linkage (see purchase_order_views.py
        # read-side eligibility widening and write-side auto-reset).
        ("damaged_exchange", "파손/교환"),
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
    # SPEC-ORDER-013 REQ-RACK-001/002: physical rack/shelf code for locating
    # a book in the warehouse. Same CharField(max_length=10) shape as
    # `location` above, but semantically distinct (rack != warehouse
    # location code). Manual/upload-driven only (single PATCH, bulk PATCH,
    # or Excel upload) — never computed, and no Order-level aggregate or
    # rollup field exists for it (REQ-RACK-002).
    rack_number = models.CharField(max_length=10, blank=True, default="")
    purchase_status = models.CharField(
        max_length=20,
        choices=PURCHASE_STATUS_CHOICES,
        default="unordered",
    )
    confirmed_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    confirmed_distributor = models.CharField(max_length=50, null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    # SPEC-ORDER-011 REQ-LOGI-001: Korea-vendor -> US-warehouse -> customer
    # logistics pipeline status, fully independent of purchase_status
    # (why/whether a SKU needs purchasing) and fulfillment_status (Shopify-
    # synced "shipped to customer"). Manual/upload-driven only — never
    # written by Shopify sync (REQ-LOGI-002) and never derived from
    # PurchaseOrder.status (REQ-LOGI-014).
    logistics_status = models.CharField(
        max_length=20,
        choices=LOGISTICS_STATUS_CHOICES,
        default="not_shipped",
    )
    # @MX:NOTE: [AUTO] SPEC-ORDER-015 REQ-OUTBOUND-001/002/002a: cumulative
    # outbound quantity and last-processed timestamp. These fill the one
    # missing step of the LOGISTICS_STATUS_CHOICES pipeline above —
    # `outbound_scheduled` -> `shipped` (Korea warehouse -> US warehouse) —
    # which had no upload/entry path, unlike `shipment_confirmed`
    # (UploadVendorShipmentView) and `received` (UploadWarehouseReceiptView).
    # shipped_quantity accumulates across multiple partial outbound requests
    # and drives the automatic transition to logistics_status="shipped" once
    # it reaches `quantity`; shipped_at stays NULL until the first outbound
    # event actually touches the row (REQ-OUTBOUND-002a). Distinct from
    # `fulfillment_status` (Shopify "shipped to customer", never written here)
    # and from `book.Info.qty` / `WarehouseStock` (untouched by this SPEC).
    shipped_quantity = models.IntegerField(default=0)
    shipped_at = models.DateTimeField(null=True, blank=True)
    # SPEC-ORDER-011 REQ-LOGI-015: same quantity-accumulation model as
    # shipped_quantity/shipped_at above, applied one step earlier in the
    # pipeline — `UploadWarehouseReceiptView` accumulates uploaded receiving
    # quantities here and only advances logistics_status to "received" once
    # received_quantity reaches `quantity` (see _process_warehouse_receipt_rows).
    received_quantity = models.IntegerField(default=0)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders_line_item"
        # SPEC-SHOPIFY-SKU-SET-002 REQ-SKUSET2-001: widened to (order, shopify_line_item_id, sku)
        # so one Shopify line item can expand into N rows (one per bundle member ISBN).
        unique_together = [("order", "shopify_line_item_id", "sku")]


class LineItemNote(models.Model):
    # @MX:ANCHOR: [AUTO] LineItemNote model — 1:N relationship to LineItem
    # @MX:REASON: Fan-in >= 3: LineItemNoteListCreateView, LineItemNoteUnresolvedListView, LineItemNoteResolveView all query LineItemNote

    ASSIGNEE_CHOICES = [
        ("CS", "CS"),
        ("발주", "발주"),
        ("한국창고", "한국창고"),
        ("미국창고", "미국창고"),
    ]

    NOTE_TYPE_CHOICES = [
        ("주문취소", "주문취소"),
        ("주문보류", "주문보류"),
        ("CS필요", "CS필요"),
        ("타출판사", "타출판사"),
        ("CS요청", "CS요청"),
        ("발주요청", "발주요청"),
        ("발주제외", "발주제외"),
        # SPEC-PURCHASE-ORDER-010 REQ-DMG-004
        ("파손/교환", "파손/교환"),
    ]

    line_item = models.ForeignKey(
        LineItem, on_delete=models.CASCADE, related_name="notes"
    )
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="line_item_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    assignee = models.CharField(
        max_length=20,
        choices=ASSIGNEE_CHOICES,
        default="CS",
        blank=True,
    )
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES,
        blank=True,
        default="",
    )

    class Meta:
        db_table = "orders_line_item_note"
        ordering = ["-created_at"]


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
        ("booxen", "북센"),
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


class BooxenData(models.Model):
    """Booxen distributor vendor data, keyed by SKU."""

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
        return f"BooxenData({self.sku})"


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
    # SPEC-PURCHASE-ORDER-008 REQ-PO8-017: filled only via Daily Review upload
    # ('교보 정가' column), when present. Never touched by UploadVendorFileView.
    list_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_kyobodata"
        indexes = [models.Index(fields=["sku"])]

    def __str__(self) -> str:
        return f"KyoboData({self.sku})"


class Yes24Data(models.Model):
    """YES24 distributor vendor data (reference-only), keyed by SKU."""

    sku = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    list_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_yes24data"
        indexes = [models.Index(fields=["sku"])]

    def __str__(self) -> str:
        return f"Yes24Data({self.sku})"


class VendorComparison(models.Model):
    """Stores auto-selection results (selected distributor) for a SKU."""

    DISTRIBUTOR_CHOICES = [
        ("booxen", "북센"),
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


class ShopifySkuSetMapping(models.Model):
    # @MX:ANCHOR: [AUTO] ShopifySkuSetMapping — bundle SKU to member ISBN mapping table
    # @MX:REASON: Fan-in >= 3: ShopifySkuSetListCreateView, ShopifySkuSetDetailView,
    # shopify_orders._sync_single_order (SPEC-SHOPIFY-SKU-SET-002 sync-time expansion)

    bundle_sku = models.CharField(max_length=200, db_index=True)
    member_isbn = models.CharField(max_length=20)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_shopify_sku_set_mapping"
        ordering = ["bundle_sku", "sort_order"]
        unique_together = [("bundle_sku", "member_isbn")]
        indexes = [models.Index(fields=["bundle_sku"])]

    def __str__(self) -> str:
        return f"ShopifySkuSetMapping({self.bundle_sku} -> {self.member_isbn})"
