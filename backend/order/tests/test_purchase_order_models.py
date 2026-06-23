import pytest
from django.db import IntegrityError

from order.models import (
    BookseenData,
    Customer,
    DistributorVendorRule,
    KyoboData,
    LineItem,
    Order,
    PurchaseOrder,
    VendorComparison,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_order(shopify_order_id: int = 10001, store_type: str = "gimssine") -> Order:
    """Create a minimal Order instance for use in tests."""
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type=store_type)


def _make_line_item(order: Order, shopify_line_item_id: int = 1) -> LineItem:
    """Create a minimal LineItem attached to the given order."""
    return LineItem.objects.create(
        order=order,
        shopify_line_item_id=shopify_line_item_id,
        sku="TEST-SKU-001",
        title="Test Book",
        quantity=1,
    )


# ---------------------------------------------------------------------------
# PurchaseOrder tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPurchaseOrder:
    def test_create_purchase_order(self):
        """Basic creation should persist the record and return a valid pk."""
        po = PurchaseOrder.objects.create(
            sku="SKU-001",
            title="Some Book",
            distributor="bookseen",
            quantity=10,
        )
        assert po.pk is not None
        assert PurchaseOrder.objects.filter(pk=po.pk).exists()

    def test_default_status_is_pending(self):
        """status should default to 'pending' when not explicitly set."""
        po = PurchaseOrder.objects.create(
            sku="SKU-002",
            title="Another Book",
            distributor="kyobo",
            quantity=5,
        )
        assert po.status == "pending"

    def test_m2m_link_to_line_items(self):
        """PurchaseOrder can be linked to one or more LineItem instances via M2M."""
        order = _make_order(shopify_order_id=20001)
        li1 = _make_line_item(order, shopify_line_item_id=1)
        li2 = _make_line_item(order, shopify_line_item_id=2)

        po = PurchaseOrder.objects.create(
            sku="SKU-003",
            title="Book A",
            distributor="bookseen",
            quantity=3,
        )
        po.line_items.add(li1, li2)

        assert po.line_items.count() == 2
        assert li1 in po.line_items.all()
        assert li2 in po.line_items.all()

    def test_m2m_reverse_relation(self):
        """LineItem.purchase_orders should return related PurchaseOrder instances."""
        order = _make_order(shopify_order_id=20002)
        li = _make_line_item(order, shopify_line_item_id=1)

        po = PurchaseOrder.objects.create(
            sku="SKU-004",
            title="Book B",
            distributor="choeumgoyuk",
            quantity=2,
        )
        po.line_items.add(li)

        assert po in li.purchase_orders.all()

    def test_distributor_choices(self):
        """All four distributor values should be accepted without error."""
        valid_distributors = ["bookseen", "kyobo", "choeumgoyuk", "agape"]
        for i, dist in enumerate(valid_distributors):
            po = PurchaseOrder.objects.create(
                sku=f"SKU-DIST-{i}",
                title=f"Book {dist}",
                distributor=dist,
                quantity=1,
            )
            assert po.distributor == dist

    def test_status_confirmed(self):
        """status can be set to 'confirmed'."""
        po = PurchaseOrder.objects.create(
            sku="SKU-005",
            title="Confirmed Book",
            distributor="kyobo",
            quantity=1,
            status="confirmed",
        )
        assert po.status == "confirmed"

    def test_unit_price_nullable(self):
        """unit_price is optional and should allow NULL."""
        po = PurchaseOrder.objects.create(
            sku="SKU-006",
            title="No Price Book",
            distributor="bookseen",
            quantity=1,
            unit_price=None,
        )
        assert po.unit_price is None

    def test_db_table_name(self):
        """The underlying DB table should follow the orders_ naming convention."""
        assert PurchaseOrder._meta.db_table == "orders_purchaseorder"

    def test_timestamps_auto_set(self):
        """created_at and updated_at should be populated automatically."""
        po = PurchaseOrder.objects.create(
            sku="SKU-007",
            title="Timestamp Book",
            distributor="agape",
            quantity=1,
        )
        assert po.created_at is not None
        assert po.updated_at is not None


# ---------------------------------------------------------------------------
# VendorComparison tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVendorComparison:
    def test_create_vendor_comparison(self):
        """Basic creation should persist the record with selection metadata."""
        vc = VendorComparison.objects.create(
            sku="ISBN-9780001",
            selected_distributor="bookseen",
        )
        assert vc.pk is not None
        assert vc.sku == "ISBN-9780001"

    def test_sku_uniqueness(self):
        """Duplicate SKU should raise IntegrityError due to unique_together constraint."""
        VendorComparison.objects.create(sku="ISBN-9780002")
        with pytest.raises(IntegrityError):
            VendorComparison.objects.create(sku="ISBN-9780002")

    def test_null_fields_allowed(self):
        """All optional fields should accept NULL without error."""
        vc = VendorComparison.objects.create(
            sku="ISBN-9780003",
            selected_distributor=None,
        )
        assert vc.selected_distributor is None

    def test_db_table_name(self):
        """The underlying DB table should follow the orders_ naming convention."""
        assert VendorComparison._meta.db_table == "orders_vendorcomparison"

    def test_timestamps_auto_set(self):
        """created_at and updated_at should be populated automatically."""
        vc = VendorComparison.objects.create(sku="ISBN-9780005")
        assert vc.created_at is not None
        assert vc.updated_at is not None


@pytest.mark.django_db
class TestBookseenData:
    def test_create_bookseen_data(self):
        """BookseenData stores bookseen vendor info independently."""
        from decimal import Decimal

        bd = BookseenData.objects.create(
            sku="ISBN-9780010",
            available=True,
            price=Decimal("15000.00"),
            stock=5,
        )
        bd.refresh_from_db()
        assert bd.available is True
        assert bd.price == Decimal("15000.00")
        assert bd.stock == 5

    def test_sku_uniqueness(self):
        """BookseenData SKU must be unique."""
        BookseenData.objects.create(sku="ISBN-9780011")
        with pytest.raises(IntegrityError):
            BookseenData.objects.create(sku="ISBN-9780011")

    def test_db_table_name(self):
        """Table name must match declared db_table."""
        assert BookseenData._meta.db_table == "orders_bookseendata"


@pytest.mark.django_db
class TestKyoboData:
    def test_create_kyobo_data(self):
        """KyoboData stores kyobo vendor info independently."""
        from decimal import Decimal

        kd = KyoboData.objects.create(
            sku="ISBN-9780020",
            available=True,
            price=Decimal("11500.00"),
            stock=10,
            publisher="테스트출판사",
        )
        kd.refresh_from_db()
        assert kd.available is True
        assert kd.price == Decimal("11500.00")
        assert kd.publisher == "테스트출판사"

    def test_sku_uniqueness(self):
        """KyoboData SKU must be unique."""
        KyoboData.objects.create(sku="ISBN-9780021")
        with pytest.raises(IntegrityError):
            KyoboData.objects.create(sku="ISBN-9780021")

    def test_db_table_name(self):
        """Table name must match declared db_table."""
        assert KyoboData._meta.db_table == "orders_kyobodata"


# ---------------------------------------------------------------------------
# DistributorVendorRule tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDistributorVendorRule:
    def test_create_rule(self):
        """Basic creation should persist the rule with correct field values."""
        rule = DistributorVendorRule.objects.create(
            publisher_name="처음교육출판사",
            distributor="choeumgoyuk",
        )
        assert rule.pk is not None
        assert rule.publisher_name == "처음교육출판사"
        assert rule.distributor == "choeumgoyuk"

    def test_publisher_name_unique(self):
        """Duplicate publisher_name should raise IntegrityError."""
        DistributorVendorRule.objects.create(
            publisher_name="아가페출판사",
            distributor="agape",
        )
        with pytest.raises(IntegrityError):
            DistributorVendorRule.objects.create(
                publisher_name="아가페출판사",
                distributor="choeumgoyuk",
            )

    def test_secondary_distributor_choices(self):
        """Both secondary distributor values should be accepted."""
        rule_choeumgoyuk = DistributorVendorRule.objects.create(
            publisher_name="Publisher A",
            distributor="choeumgoyuk",
        )
        rule_agape = DistributorVendorRule.objects.create(
            publisher_name="Publisher B",
            distributor="agape",
        )
        assert rule_choeumgoyuk.distributor == "choeumgoyuk"
        assert rule_agape.distributor == "agape"

    def test_db_table_name(self):
        """The underlying DB table should follow the orders_ naming convention."""
        assert DistributorVendorRule._meta.db_table == "orders_distributorvendorrule"

    def test_created_at_auto_set(self):
        """created_at should be populated automatically on creation."""
        rule = DistributorVendorRule.objects.create(
            publisher_name="Timestamp Publisher",
            distributor="agape",
        )
        assert rule.created_at is not None


# ---------------------------------------------------------------------------
# LineItem.purchase_status tests (SPEC-PURCHASE-ORDER-004)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemPurchaseStatus:
    def test_default_purchase_status_is_unordered(self):
        """REQ-PO4-001: LineItem.purchase_status defaults to 'unordered' when not specified."""
        order = _make_order(shopify_order_id=30001)
        li = _make_line_item(order, shopify_line_item_id=1)
        assert li.purchase_status == "unordered"

    def test_all_valid_choices_accepted(self):
        """REQ-PO4-002: All 6 purchase_status choices can be saved without error."""
        valid_choices = [
            "unordered",
            "on_hold",
            "order_cancelled",
            "other_publisher",
            "cs_required",
            "in_stock",
        ]
        order = _make_order(shopify_order_id=30002)
        for i, choice in enumerate(valid_choices):
            li = LineItem.objects.create(
                order=order,
                shopify_line_item_id=100 + i,
                sku=f"SKU-STATUS-{i}",
                quantity=1,
                purchase_status=choice,
            )
            li.refresh_from_db()
            assert li.purchase_status == choice

    def test_invalid_choice_rejected(self):
        """REQ-PO4-002: An invalid purchase_status value raises ValidationError on full_clean()."""
        from django.core.exceptions import ValidationError

        order = _make_order(shopify_order_id=30003)
        li = LineItem(
            order=order,
            shopify_line_item_id=200,
            sku="SKU-INVALID",
            quantity=1,
            purchase_status="invalid_status",
        )
        with pytest.raises(ValidationError):
            li.full_clean()
