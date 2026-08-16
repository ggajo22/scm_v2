from bisect import bisect_right
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from .models import Customer, ExchangeRate, LineItem, LineItemNote, Order, Refund, ShippingAddress, ShippingLine

# @MX:NOTE: [AUTO] SPEC-ORDER-021 REQ-COST-001: shipping/Korea-warehouse fee
# constants, used by OrderDetailSerializer._compute_cost_breakdown() below.
# Collocated with the serializer rather than a shared constants.py — this
# app has no such module today and these three values change rarely (design
# decision A). Changing any of these values also changes the fixed-value
# assertions in backend/order/tests/test_spec_021.py (AC-COST-001, 002, 003,
# 005, 008, 012, 013).
SHIPPING_COST_USD_PER_KG = Decimal("5.45")
KOREA_WAREHOUSE_BASE_KRW = Decimal("1250")
KOREA_WAREHOUSE_PER_BOOK_KRW = Decimal("500")


# @MX:NOTE: [AUTO] SPEC-ORDER-023 REQ-OLIST-016/033: cost-breakdown formula
# extracted from OrderDetailSerializer._compute_cost_breakdown_uncached
# (design decision C) so OrderListSerializer.get_margin_rate can reuse the
# identical calculation. Takes `rate` (a Decimal, e.g. ExchangeRate.rate) as
# a parameter instead of looking it up itself -- this lets the detail
# serializer keep its per-instance memoized _get_exchange_rate() lookup
# while the list serializer resolves its rate from OrderListView's
# page-level batch load (REQ-OLIST-019). OrderDetailSerializer's own
# observable output is unchanged by this extraction (REQ-OLIST-033) --
# _compute_cost_breakdown_uncached below now just resolves `er` and
# delegates here.
def _compute_cost_breakdown_for_rate(obj: "Order", rate: Decimal):
    confirmed_cost_krw = Decimal("0")
    has_any_confirmed = False
    total_weight_grams = 0
    total_book_count = 0
    for item in obj.line_items.all():
        quantity = item.quantity or 0
        grams = item.grams or 0
        total_weight_grams += grams * quantity
        total_book_count += quantity
        if item.confirmed_price is not None:
            has_any_confirmed = True
            confirmed_cost_krw += item.confirmed_price * quantity

    if not has_any_confirmed:
        return None

    total_price_usd = Decimal(str(obj.total_price or "0"))
    confirmed_cost_usd = confirmed_cost_krw / rate
    shipping_cost_usd = (
        SHIPPING_COST_USD_PER_KG * Decimal(total_weight_grams) / Decimal("1000")
    )

    if total_book_count == 0:
        korea_warehouse_krw = Decimal("0")
    else:
        korea_warehouse_krw = KOREA_WAREHOUSE_BASE_KRW + KOREA_WAREHOUSE_PER_BOOK_KRW * max(
            total_book_count - 1, 0
        )
    korea_warehouse_usd = korea_warehouse_krw / rate

    margin_usd = total_price_usd - confirmed_cost_usd - shipping_cost_usd - korea_warehouse_usd
    total_cost_usd = confirmed_cost_usd + shipping_cost_usd + korea_warehouse_usd

    return {
        "margin_usd": margin_usd,
        "total_price_usd": total_price_usd,
        "confirmed_cost_usd": confirmed_cost_usd,
        "shipping_cost_usd": shipping_cost_usd,
        "korea_warehouse_usd": korea_warehouse_usd,
        "total_cost_usd": total_cost_usd,
        "total_weight_grams": total_weight_grams,
    }


def _resolve_exchange_rate(history, order_date):
    """SPEC-ORDER-023 REQ-OLIST-020: binary search `history` (a list of
    (effective_date, rate) tuples sorted ascending by effective_date, as
    loaded by OrderListView._load_exchange_rate_history) for the most
    recent rate whose effective_date <= order_date -- the same fallback
    semantics as OrderDetailSerializer._get_exchange_rate. Returns None
    (never raises) when history is empty or no entry qualifies
    (AC-OLIST-018a)."""
    if not history:
        return None
    dates = [effective_date for effective_date, _ in history]
    idx = bisect_right(dates, order_date) - 1
    if idx < 0:
        return None
    return history[idx][1]


class CustomerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["shopify_customer_id", "first_name", "last_name", "email"]


class OrderListSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    has_refund = serializers.SerializerMethodField()
    line_items_count = serializers.SerializerMethodField()
    # SPEC-ORDER-023 REQ-OLIST-016/007/013: margin_rate reuses the
    # OrderDetailSerializer formula (via _compute_cost_breakdown_for_rate);
    # logistics_display/purchase_display derive from `LineItem` rows only —
    # neither reads the stored `Order.status` aggregate column (design
    # decision B, C3 in spec.md).
    margin_rate = serializers.SerializerMethodField()
    logistics_display = serializers.SerializerMethodField()
    purchase_display = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "shopify_order_id",
            "store_type",
            "order_number",
            "name",
            "financial_status",
            "fulfillment_status",
            "total_price",
            "currency",
            "shopify_created_at",
            "customer",
            "has_refund",
            "line_items_count",
            "location",
            "margin_rate",
            "logistics_display",
            "purchase_display",
        ]

    def get_has_refund(self, obj):
        # relies on prefetch_related("refunds") in the view queryset
        return obj.refunds.exists()

    def get_line_items_count(self, obj):
        return obj.line_items.count()

    # @MX:NOTE: [AUTO] SPEC-ORDER-023 REQ-OLIST-007~011a: priority order is
    # (1) all trackable shipped -> "shipped", (2) any trackable
    # shipped_quantity>0 -> "partial_shipped", (3) all trackable received ->
    # "outbound_scheduled", (4) remaining trackable logistics_status uniform
    # -> that value, (4a) not uniform -> "partial". This exact order matters:
    # in production every fully-shipped line item also satisfies
    # shipped_quantity >= quantity > 0 (purchase_order_views.py:3411/3456/
    # 3972), so rules (1) and (2) co-occur on every completed order —
    # swapping them mislabels every completed order as partial_shipped
    # (SPEC-ORDER-023 problem definition, AC-OLIST-006). Deliberately never
    # reads obj.status: that stored aggregate is NULL for orders that have
    # never gone through a logistics write path even though their trackable
    # line items already carry a real (default "not_shipped") status
    # (spec.md C3). Iterates obj.line_items.all() exactly once, relying on
    # OrderListView's prefetch_related("line_items") cache — REQ-OLIST-021
    # forbids any additional query here.
    def _derive_line_item_states(self, obj):
        cache = getattr(self, "_line_item_states_cache", None)
        if cache is None:
            cache = {}
            self._line_item_states_cache = cache
        if obj.pk in cache:
            return cache[obj.pk]

        trackable = [li for li in obj.line_items.all() if li.sku is not None]
        if not trackable:
            result = (None, None)
        else:
            if all(li.logistics_status == "shipped" for li in trackable):
                logistics = "shipped"
            elif any(li.shipped_quantity > 0 for li in trackable):
                logistics = "partial_shipped"
            elif all(li.logistics_status == "received" for li in trackable):
                logistics = "outbound_scheduled"
            else:
                statuses = {li.logistics_status for li in trackable}
                logistics = next(iter(statuses)) if len(statuses) == 1 else "partial"

            purchase = (
                "unordered"
                if any(li.purchase_status == "unordered" for li in trackable)
                else "ordered"
            )
            result = (logistics, purchase)

        cache[obj.pk] = result
        return result

    def get_logistics_display(self, obj):
        logistics, _purchase = self._derive_line_item_states(obj)
        return logistics

    def get_purchase_display(self, obj):
        _logistics, purchase = self._derive_line_item_states(obj)
        return purchase

    def get_margin_rate(self, obj):
        """REQ-OLIST-016: identical formula to
        OrderDetailSerializer.get_margin_rate, but resolves its ExchangeRate
        from the page-level batch history OrderListView.list() loads into
        `self.context['exchange_rate_history']` (REQ-OLIST-019) instead of
        the per-instance memoized _get_exchange_rate lookup that would issue
        up to 50 queries per page if reused here unmodified."""
        if not obj.shopify_created_at:
            return None
        history = self.context.get("exchange_rate_history") or []
        rate = _resolve_exchange_rate(history, obj.shopify_created_at.date())
        if rate is None:
            return None
        breakdown = _compute_cost_breakdown_for_rate(obj, rate)
        if breakdown is None:
            return None
        total_price_usd = breakdown["total_price_usd"]
        if total_price_usd == Decimal("0"):
            return None
        result = (breakdown["margin_usd"] / total_price_usd * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return str(result)


# ---------------------------------------------------------------------------
# SPEC-ORDER-003: Order Detail serializers
# ---------------------------------------------------------------------------


class CustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["shopify_customer_id", "first_name", "last_name", "email", "phone"]


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = [
            "name", "first_name", "last_name", "address1", "address2",
            "city", "province", "province_code", "country", "country_code", "zip", "phone",
        ]


class LineItemNoteSerializer(serializers.ModelSerializer):
    # @MX:NOTE: [AUTO] Serializer for LineItemNote — used in list/create and order detail
    author_username = serializers.SerializerMethodField()

    def get_author_username(self, obj):
        return obj.author.username if obj.author else None

    class Meta:
        model = LineItemNote
        fields = ["id", "content", "author_username", "assignee", "note_type", "created_at", "is_resolved"]
        read_only_fields = ["id", "author_username", "created_at", "is_resolved"]


class LineItemNoteUnresolvedSerializer(serializers.ModelSerializer):
    # @MX:NOTE: [AUTO] Serializer for unresolved notes page — includes order and line_item context
    author_username = serializers.SerializerMethodField()
    line_item_id = serializers.IntegerField()
    line_item_sku = serializers.CharField(source="line_item.sku", default=None)
    line_item_title = serializers.CharField(source="line_item.title", default=None)
    order_name = serializers.CharField(source="line_item.order.name", default=None)
    order_id = serializers.IntegerField(source="line_item.order.id")
    confirmed_distributor = serializers.CharField(source="line_item.confirmed_distributor", default=None)

    def get_author_username(self, obj):
        return obj.author.username if obj.author else None

    class Meta:
        model = LineItemNote
        fields = [
            "id", "content", "author_username", "assignee", "note_type", "created_at", "is_resolved",
            "line_item_id", "line_item_sku", "line_item_title", "order_name", "order_id", "confirmed_distributor",
        ]


class LineItemDetailSerializer(serializers.ModelSerializer):
    # @MX:ANCHOR: [AUTO] LineItemDetailSerializer — serializes confirmed purchase fields
    # @MX:REASON: Extended by SPEC-ORDER-008 and SPEC-ORDER-010; notes replaces note field
    confirmed_price = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, read_only=True)
    confirmed_distributor = serializers.CharField(allow_null=True, read_only=True)
    confirmed_at = serializers.DateTimeField(allow_null=True, read_only=True)
    notes = LineItemNoteSerializer(many=True, read_only=True)

    class Meta:
        model = LineItem
        fields = [
            "id", "shopify_line_item_id", "title", "variant_title", "sku",
            "quantity", "price", "total_discount", "fulfillment_status", "vendor", "grams",
            "location", "rack_number", "notes",
            "confirmed_price", "confirmed_distributor", "confirmed_at",
            # SPEC-ORDER-011 T11: expose logistics_status so the frontend has
            # a data source for the LineItem-level logistics badge column.
            "logistics_status",
            # SPEC-ORDER-015 T7: cumulative outbound quantity and last
            # outbound timestamp, so an order-detail view can show partial
            # shipment progress alongside logistics_status.
            "shipped_quantity",
            "shipped_at",
        ]


class ShippingLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingLine
        fields = ["title", "code", "price", "source"]


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            "shopify_refund_id", "note", "shopify_created_at",
            "line_item_id", "quantity", "subtotal", "total_tax",
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    # @MX:ANCHOR: [AUTO] Fan-in >= 3: called by OrderDetailView, test suite, frontend client
    # @MX:REASON: Central serializer for order detail; all nested domain data flows through here
    customer = CustomerDetailSerializer(read_only=True)
    shipping_address = ShippingAddressSerializer(read_only=True)
    line_items = LineItemDetailSerializer(many=True, read_only=True)
    shipping_lines = ShippingLineSerializer(many=True, read_only=True)
    refunds = RefundSerializer(many=True, read_only=True)
    has_refund = serializers.SerializerMethodField()
    margin_amount = serializers.SerializerMethodField()
    margin_rate = serializers.SerializerMethodField()
    # SPEC-ORDER-021 REQ-COST-011/012/013: cost breakdown backing the margin
    # fields above. Same null gate as margin_amount/margin_rate (design
    # decision D) and same underlying memoized helper (design decision C/E).
    shipping_cost = serializers.SerializerMethodField()
    korea_warehouse_cost = serializers.SerializerMethodField()
    total_weight_grams = serializers.SerializerMethodField()
    # SPEC-ORDER-021 extension: confirmed_cost (confirmed_cost_usd, already
    # computed internally by _compute_cost_breakdown_uncached) and total_cost
    # (confirmed_cost_usd + shipping_cost_usd + korea_warehouse_usd, summed
    # from the UNROUNDED Decimals and quantized once -- see design decision B
    # and _compute_cost_breakdown_uncached below). Same null gate + memoized
    # helper as the other cost fields above.
    confirmed_cost = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    # SPEC-ORDER-021 extension (v1.4.0): the ExchangeRate record actually
    # applied by _get_exchange_rate() -- exposed so the order detail screen
    # can show the applied rate and, crucially, the fallback effective_date
    # when it differs from the order date (previously invisible).
    # DELIBERATELY NOT gated by has_any_confirmed like the 7 cost fields
    # above (design decision D does not extend to these two) -- these two
    # are non-null whenever an ExchangeRate record was found at all, even if
    # margin_amount is null because no line item has a confirmed_price yet.
    exchange_rate = serializers.SerializerMethodField()
    exchange_rate_date = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "shopify_order_id", "store_type", "order_number", "name",
            "email", "phone", "financial_status", "fulfillment_status",
            "total_price", "subtotal_price", "total_tax", "total_discounts",
            "total_shipping_price_set", "currency", "gateway", "note", "note_resolved", "tags",
            "cancel_reason", "source_name", "shopify_created_at",
            "shopify_updated_at", "closed_at", "cancelled_at", "processed_at",
            "has_refund", "customer", "shipping_address",
            "line_items", "shipping_lines", "refunds",
            "margin_amount", "margin_rate",
            # SPEC-ORDER-021 REQ-COST-011/012/013: shipping/Korea-warehouse
            # cost breakdown backing the margin fields.
            "shipping_cost", "korea_warehouse_cost", "total_weight_grams",
            # SPEC-ORDER-021 extension: confirmed_cost (confirmed purchase
            # cost only) and total_cost (all three cost components summed
            # server-side from unrounded values).
            "confirmed_cost", "total_cost",
            # SPEC-ORDER-021 extension (v1.4.0): applied exchange rate + the
            # record's effective_date (may be earlier than the order date
            # due to the fallback lookup in _get_exchange_rate).
            "exchange_rate", "exchange_rate_date",
            # SPEC-ORDER-011 T11: expose the logistics_status aggregate so the
            # frontend has a data source for the Order-level aggregate badge.
            "status",
            # SPEC-ORDER-012 REQ-RTS-007: expose the ready_to_ship aggregate
            # for the Order detail screen's third badge.
            "ready_to_ship",
        ]

    def get_has_refund(self, obj: Order) -> bool:
        return obj.refunds.exists()

    def _get_exchange_rate(self, obj: Order):
        """
        Look up exchange rate for order date with fallback to prior date.
        Returns ExchangeRate instance or None.
        REQ-003, REQ-013

        Memoized per `obj` for the lifetime of this serializer instance
        (SPEC-ORDER-021 REQ-COST-034, same pattern as
        _compute_cost_breakdown below). `get_exchange_rate`/
        `get_exchange_rate_date` call this directly (they are NOT gated by
        `_compute_cost_breakdown`'s has_any_confirmed check -- REQ-COST-033),
        while `_compute_cost_breakdown_uncached` also calls it. Without this
        cache, the two call sites would each issue their own ExchangeRate
        query, defeating the "at most 1 query per serialized order" guarantee
        AC-COST-009 (c) pins.
        """
        cache = getattr(self, "_exchange_rate_cache", None)
        if cache is None:
            cache = {}
            self._exchange_rate_cache = cache
        if obj.pk in cache:
            return cache[obj.pk]

        if not obj.shopify_created_at:
            result = None
        else:
            order_date = obj.shopify_created_at.date()
            result = ExchangeRate.objects.filter(
                effective_date__lte=order_date
            ).order_by("-effective_date").first()

        cache[obj.pk] = result
        return result

    # @MX:NOTE: [AUTO] SPEC-ORDER-021 REQ-COST-002~008/019: single helper
    # backing all 7 cost-related SerializerMethodFields (margin_amount,
    # margin_rate, shipping_cost, korea_warehouse_cost, total_weight_grams,
    # confirmed_cost, total_cost).
    # Weight/book-count aggregation runs unconditionally over every line item
    # in the SAME loop as the confirmed-cost aggregation (REQ-COST-002/004 —
    # deliberately outside the `confirmed_price is not None` gate, so
    # unconfirmed line items still count toward shipping/Korea-warehouse
    # fees). The zero-book-count branch (REQ-COST-006) is checked before the
    # general formula so a 0-book order is never charged the base fee.
    # Extending with a 4th cost term (e.g. US-warehouse fee) later only
    # requires adding a key to the returned dict and a term to margin_usd —
    # no getter's control flow needs to change (design decision E).
    def _compute_cost_breakdown(self, obj: Order):
        """Returns a dict of unquantized Decimal/int cost components, or None
        when margin cannot be computed (no exchange rate, or no line item has
        a non-null confirmed_price).

        Memoized per `obj` for the lifetime of this serializer instance
        (REQ-COST-015, design decisions C/F): each of the 7
        SerializerMethodFields above is evaluated independently by DRF, so
        without this cache the line-item loop and the ExchangeRate lookup
        would each run up to 7x per request against a remote RDS instance.
        """
        # @MX:NOTE: [AUTO] SPEC-ORDER-021 REQ-COST-015: all 7 cost getters
        # (get_margin_amount, get_margin_rate, get_shipping_cost,
        # get_korea_warehouse_cost, get_total_weight_grams, get_confirmed_cost,
        # get_total_cost) MUST go through this cache. Bypassing it (calling
        # _compute_cost_breakdown_uncached directly, or adding a getter that
        # skips this method) reopens the up-to-7x ExchangeRate query
        # multiplication AC-COST-009 (c) guards against.
        cache = getattr(self, "_cost_breakdown_cache", None)
        if cache is None:
            cache = {}
            self._cost_breakdown_cache = cache
        if obj.pk in cache:
            return cache[obj.pk]

        result = self._compute_cost_breakdown_uncached(obj)
        cache[obj.pk] = result
        return result

    def _compute_cost_breakdown_uncached(self, obj: Order):
        """SPEC-ORDER-023 REQ-OLIST-033: the calculation itself now lives in
        module-level `_compute_cost_breakdown_for_rate` (design decision C),
        shared with OrderListSerializer.get_margin_rate. This method's own
        job is unchanged -- resolve `obj`'s memoized ExchangeRate and hand
        its `.rate` to the shared function. Observable output is identical
        to the pre-extraction implementation (verified by
        test_spec_021.py's T1-T10, T12-T22 passing unmodified)."""
        er = self._get_exchange_rate(obj)
        if er is None:
            return None
        return _compute_cost_breakdown_for_rate(obj, er.rate)

    def get_margin_amount(self, obj: Order):
        """USD 단위 마진: total_price_usd - confirmed_cost_usd - shipping_cost_usd
        - korea_warehouse_usd. 환율/확정매입가 없으면 None."""
        result = self._compute_cost_breakdown(obj)
        if result is None:
            return None
        return str(result["margin_usd"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def get_margin_rate(self, obj: Order):
        """마진율: (margin_usd / total_price_usd) × 100, 소수점 2자리 ROUND_HALF_UP."""
        result = self._compute_cost_breakdown(obj)
        if result is None:
            return None
        margin_usd = result["margin_usd"]
        total_price_usd = result["total_price_usd"]
        if total_price_usd == Decimal("0"):
            return None
        rate = (margin_usd / total_price_usd * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return str(rate)

    def get_shipping_cost(self, obj: Order):
        """REQ-COST-011: shipping_cost_usd, 소수점 2자리 ROUND_HALF_UP, 문자열."""
        result = self._compute_cost_breakdown(obj)
        if result is None:
            return None
        return str(result["shipping_cost_usd"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def get_korea_warehouse_cost(self, obj: Order):
        """REQ-COST-012: korea_warehouse_usd, 소수점 2자리 ROUND_HALF_UP, 문자열."""
        result = self._compute_cost_breakdown(obj)
        if result is None:
            return None
        return str(result["korea_warehouse_usd"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def get_total_weight_grams(self, obj: Order):
        """REQ-COST-013: 원시 그램 정수, 양자화하지 않음."""
        result = self._compute_cost_breakdown(obj)
        if result is None:
            return None
        return result["total_weight_grams"]

    def get_confirmed_cost(self, obj: Order):
        """SPEC-ORDER-021 extension: confirmed_cost_usd, 소수점 2자리
        ROUND_HALF_UP, 문자열. Same convention/null-gate as shipping_cost."""
        result = self._compute_cost_breakdown(obj)
        if result is None:
            return None
        return str(result["confirmed_cost_usd"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def get_total_cost(self, obj: Order):
        """SPEC-ORDER-021 extension: confirmed_cost_usd + shipping_cost_usd +
        korea_warehouse_usd, summed from the unrounded Decimals in
        _compute_cost_breakdown_uncached and quantized here exactly once --
        NOT summed from the already-quantized confirmed_cost/shipping_cost/
        korea_warehouse_cost fields (design decision B)."""
        result = self._compute_cost_breakdown(obj)
        if result is None:
            return None
        return str(result["total_cost_usd"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def get_exchange_rate(self, obj: Order):
        """SPEC-ORDER-021 v1.4.0 REQ-COST-030: the ExchangeRate.rate actually
        applied by _get_exchange_rate(), as a string. Null gate is
        `_get_exchange_rate(obj) is None` ONLY -- independent of
        has_any_confirmed, unlike the 7 cost fields above (REQ-COST-033)."""
        er = self._get_exchange_rate(obj)
        if er is None:
            return None
        return str(er.rate)

    def get_exchange_rate_date(self, obj: Order):
        """SPEC-ORDER-021 v1.4.0 REQ-COST-031: effective_date of the applied
        ExchangeRate record (ISO YYYY-MM-DD), which may be earlier than the
        order date due to the fallback lookup in _get_exchange_rate -- that
        fallback was previously invisible to readers of the order detail
        screen. Same null gate as get_exchange_rate."""
        er = self._get_exchange_rate(obj)
        if er is None:
            return None
        return er.effective_date.isoformat()


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ["effective_date", "rate", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class OrderNoteSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "shopify_order_id", "store_type", "order_number", "name",
            "note", "note_resolved", "shopify_created_at", "customer",
        ]
