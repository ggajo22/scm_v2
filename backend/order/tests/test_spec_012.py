"""SPEC-ORDER-012: Order.ready_to_ship 출고 가능 여부 판정 (TDD).

Coverage targets:
  T1   Order.ready_to_ship field (three-state, independent of Order.status)
  T2   _recompute_order_aggregates() rename + ready_to_ship computation
       (REQ-RTS-002/AC-RTS-002a/002b/002c)
  T3   Existing 4 logistics_status write paths also recompute ready_to_ship
       (REQ-RTS-003/AC-RTS-003)
  T4   New 4 purchase_status write paths now trigger recomputation
       (REQ-RTS-003a/AC-RTS-003a)
  T5   Shopify sync exclusion (REQ-RTS-005/AC-RTS-005)
  T6   OrderDetailSerializer exposes ready_to_ship (REQ-RTS-007)
  T7   N+1 regression: recompute call count / query count does not scale
       with LineItem count (REQ-RTS-004/004a/AC-RTS-004/004a)

Backfill migration (0033_backfill_order_ready_to_ship) tests live in
test_backfill_order_ready_to_ship_migration.py.
Frontend badge tests live in OrderDetailPage.test.tsx.
"""

import io
from unittest.mock import patch

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, Order, WarehouseStock
from order.purchase_order_views import _recompute_order_aggregates

User = get_user_model()

CONFIRM_URL = "/api/purchase-orders/confirm/"
LINE_ITEM_STATUS_URL = "/api/purchase-orders/line-items/{pk}/status/"
BULK_STATUS_URL = "/api/purchase-orders/line-items/bulk-status/"
LOGISTICS_STATUS_URL = "/api/purchase-orders/line-items/{pk}/logistics-status/"
BULK_LOGISTICS_STATUS_URL = "/api/purchase-orders/line-items/bulk-logistics-status/"
UPLOAD_VENDOR_SHIPMENT_URL = "/api/purchase-orders/upload-vendor-shipment/"
UPLOAD_WAREHOUSE_RECEIPT_URL = "/api/purchase-orders/upload-warehouse-receipt/"
UPLOAD_DAILY_URL = "/api/purchase-orders/upload-daily-review/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec012_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def _make_order(shopify_order_id: int = 200001, store_type: str = "gimssine", **kwargs) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type=store_type, **kwargs)


def _make_line_item(
    order: Order, shopify_line_item_id: int = 1, sku: str = "SKU-RTS-001", **kwargs
) -> LineItem:
    defaults = {"quantity": 1, "title": "Test Book"}
    defaults.update(kwargs)
    return LineItem.objects.create(
        order=order, shopify_line_item_id=shopify_line_item_id, sku=sku, **defaults
    )


def _make_sku_only_excel(skus: list, header=("SKU", "기타컬럼")) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(header))
    for sku in skus:
        ws.append([sku, "ignored"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_daily_review_excel(rows: list[dict]) -> bytes:
    """Mirrors test_daily_review_upload.py's `_make_daily_review_excel`."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "주문번호", "ISBN", "제목", "수량", "주문위치", "메모",
        "재고(한국)", "재고(CA)", "재고(NJ)",
        "북센 공급가", "교보 공급가",
        "북센 재고수량", "북센 재고상태",
        "교보 재고수량", "교보 재고상태",
        "공급가차이", "북센 입고예정", "북센 반품가능여부",
        "교보 출고여부", "교보 반품가능여부",
        "가격차이알림", "출판사", "선택근거", "선택",
    ])
    for row in rows:
        ws.append([
            row.get("order_name", ""),
            row.get("isbn", ""),
            row.get("title", ""),
            row.get("quantity", 1),
            "",
            row.get("note", ""),
            row.get("korea_stock", 0),
            row.get("ca_stock", 0),
            row.get("nj_stock", 0),
            row.get("bs_price", ""),
            "", "", "", "", "", "", "", "", "", "", "", "", "",
            row.get("selected", ""),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _file_obj(file_bytes: bytes, name: str = "upload.xlsx"):
    f = io.BytesIO(file_bytes)
    f.name = name
    return f


# ---------------------------------------------------------------------------
# T1: Order.ready_to_ship field
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOrderReadyToShipField:
    def test_defaults_to_null(self):
        """AC-RTS-001/시나리오0: new Order defaults to ready_to_ship=None."""
        order = _make_order(shopify_order_id=200101)
        assert order.ready_to_ship is None

    def test_accepts_true(self):
        order = _make_order(shopify_order_id=200102, ready_to_ship=True)
        order.refresh_from_db()
        assert order.ready_to_ship is True

    def test_accepts_false(self):
        order = _make_order(shopify_order_id=200103, ready_to_ship=False)
        order.refresh_from_db()
        assert order.ready_to_ship is False

    def test_independent_of_order_status(self):
        """AC-RTS-001: never inferred or synced from Order.status."""
        order = _make_order(shopify_order_id=200104, status="received", ready_to_ship=False)
        order.status = "partial"
        order.save(update_fields=["status"])
        order.refresh_from_db()
        assert order.ready_to_ship is False
        assert order.status == "partial"


# ---------------------------------------------------------------------------
# T2: _recompute_order_aggregates() ready_to_ship computation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRecomputeOrderAggregatesReadyToShip:
    def test_all_cancelled_sets_null(self):
        """시나리오1/AC-RTS-002a: every trackable LineItem order_cancelled -> null."""
        order = _make_order(shopify_order_id=200201)
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-RTS-1", purchase_status="order_cancelled"
        )
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.ready_to_ship is None

    def test_zero_trackable_lineitems_sets_null(self):
        """시나리오1b/AC-RTS-002a: sku IS NULL on every child -> null."""
        order = _make_order(shopify_order_id=200202)
        LineItem.objects.create(order=order, shopify_line_item_id=1, sku=None, quantity=1)
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.ready_to_ship is None

    def test_cs_required_hard_blocks_to_false(self):
        """시나리오2/AC-RTS-002b: cs_required forces False regardless of others."""
        order = _make_order(shopify_order_id=200203)
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-RTS-2a", purchase_status="cs_required"
        )
        _make_line_item(
            order, shopify_line_item_id=2, sku="SKU-RTS-2b", logistics_status="received"
        )
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.ready_to_ship is False

    def test_cancelled_items_excluded_from_cs_check(self):
        """시나리오2b/AC-RTS-002a/002c: cancelled items ignored entirely."""
        order = _make_order(shopify_order_id=200204)
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-RTS-2c", purchase_status="order_cancelled"
        )
        _make_line_item(
            order, shopify_line_item_id=2, sku="SKU-RTS-2d", purchase_status="in_stock"
        )
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.ready_to_ship is True

    def test_in_stock_alone_satisfies_true(self):
        """시나리오3/AC-RTS-002c: in_stock suffices regardless of logistics_status."""
        order = _make_order(shopify_order_id=200205)
        _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-RTS-3",
            purchase_status="in_stock",
            logistics_status="not_shipped",
        )
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.ready_to_ship is True

    def test_received_alone_satisfies_true(self):
        """시나리오3b/AC-RTS-002c: received suffices regardless of purchase_status."""
        order = _make_order(shopify_order_id=200206)
        _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-RTS-3b",
            purchase_status="other_publisher",
            logistics_status="received",
        )
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.ready_to_ship is True

    def test_partial_satisfaction_sets_false(self):
        """시나리오4/AC-RTS-002c: one unmet LineItem -> False."""
        order = _make_order(shopify_order_id=200207)
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-RTS-4a", logistics_status="received"
        )
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-RTS-4b",
            purchase_status="on_hold",
            logistics_status="not_shipped",
        )
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.ready_to_ship is False

    def test_status_and_ready_to_ship_computed_together(self):
        """Both aggregates computed in the same call/pass."""
        order = _make_order(shopify_order_id=200208)
        _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-RTS-5",
            logistics_status="received",
            purchase_status="in_stock",
        )
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.status == "received"
        assert order.ready_to_ship is True

    def test_noop_on_empty_order_ids_issues_zero_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            _recompute_order_aggregates([])
        assert len(ctx.captured_queries) == 0

    def test_recompute_overwrites_stale_ready_to_ship(self):
        order = _make_order(shopify_order_id=200209, ready_to_ship=True)
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-RTS-6", purchase_status="cs_required"
        )
        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        assert order.ready_to_ship is False


# ---------------------------------------------------------------------------
# T3: existing 4 logistics_status write paths also recompute ready_to_ship
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExistingWritePathsRecomputeReadyToShip:
    """AC-RTS-003 — 시나리오5."""

    def test_upload_vendor_shipment_recomputes_ready_to_ship(self, auth_client):
        order = _make_order(shopify_order_id=200301)
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-RTS-UV", purchase_status="in_stock"
        )
        file_bytes = _make_sku_only_excel(["SKU-RTS-UV"])
        res = auth_client.post(
            UPLOAD_VENDOR_SHIPMENT_URL, data={"file": _file_obj(file_bytes)}, format="multipart"
        )
        assert res.status_code == 200
        order.refresh_from_db()
        assert order.ready_to_ship is True

    def test_upload_warehouse_receipt_recomputes_ready_to_ship(self, auth_client):
        order = _make_order(shopify_order_id=200302)
        _make_line_item(order, shopify_line_item_id=1, sku="SKU-RTS-UW")
        file_bytes = _make_sku_only_excel(["SKU-RTS-UW"])
        res = auth_client.post(
            UPLOAD_WAREHOUSE_RECEIPT_URL, data={"file": _file_obj(file_bytes)}, format="multipart"
        )
        assert res.status_code == 200
        order.refresh_from_db()
        assert order.ready_to_ship is True

    def test_single_logistics_status_patch_recomputes_ready_to_ship(self, auth_client):
        order = _make_order(shopify_order_id=200303)
        li = _make_line_item(order, shopify_line_item_id=1, sku="SKU-RTS-SL")
        url = LOGISTICS_STATUS_URL.format(pk=li.pk)
        res = auth_client.patch(url, data={"logistics_status": "received"}, format="json")
        assert res.status_code == 200
        order.refresh_from_db()
        assert order.ready_to_ship is True

    def test_bulk_logistics_status_patch_recomputes_ready_to_ship(self, auth_client):
        order = _make_order(shopify_order_id=200304)
        li = _make_line_item(order, shopify_line_item_id=1, sku="SKU-RTS-BL")
        res = auth_client.patch(
            BULK_LOGISTICS_STATUS_URL,
            data={"ids": [li.pk], "logistics_status": "received"},
            format="json",
        )
        assert res.status_code == 200
        order.refresh_from_db()
        assert order.ready_to_ship is True


# ---------------------------------------------------------------------------
# T4: 4 new purchase_status write paths now trigger recomputation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConfirmOrderViewRecomputesReadyToShip:
    """AC-RTS-003a — 시나리오6."""

    def test_out_of_batch_order_unchanged(self, auth_client):
        """Control: an Order whose SKU is NOT in this confirm request is
        untouched by this request's recomputation."""
        order_a = _make_order(shopify_order_id=200401)
        _make_line_item(
            order_a, shopify_line_item_id=1, sku="SKU-RTS-CS-A", purchase_status="cs_required"
        )
        order_b = _make_order(shopify_order_id=200402)
        _make_line_item(order_b, shopify_line_item_id=1, sku="SKU-RTS-CONFIRM-B", quantity=1)

        payload = {
            "items": [
                {
                    "sku": "SKU-RTS-CONFIRM-B",
                    "distributor": "booxen",
                    "quantity": 1,
                    "unit_price": "1000",
                }
            ]
        }
        res = auth_client.post(CONFIRM_URL, data=payload, format="json")
        assert res.status_code == 201

        order_a.refresh_from_db()
        assert order_a.ready_to_ship is None  # untouched: no recompute ever ran for it

    def test_confirm_triggers_recompute_previously_never_triggered(self, auth_client):
        """Regression: before this SPEC, ConfirmOrderView triggered NO
        Order-level recomputation at all."""
        order = _make_order(shopify_order_id=200403)
        _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-RTS-CONFIRM-C",
            quantity=1,
            logistics_status="received",
        )
        payload = {
            "items": [
                {
                    "sku": "SKU-RTS-CONFIRM-C",
                    "distributor": "booxen",
                    "quantity": 1,
                    "unit_price": "1000",
                }
            ]
        }
        res = auth_client.post(CONFIRM_URL, data=payload, format="json")
        assert res.status_code == 201
        order.refresh_from_db()
        # confirming does not itself set purchase_status; the LineItem's
        # logistics_status="received" already satisfies REQ-RTS-002.
        assert order.ready_to_ship is True

    def test_confirm_with_explicit_purchase_status_recomputes(self, auth_client):
        order = _make_order(shopify_order_id=200404)
        _make_line_item(order, shopify_line_item_id=1, sku="SKU-RTS-CONFIRM-D", quantity=1)
        payload = {
            "items": [
                {
                    "sku": "SKU-RTS-CONFIRM-D",
                    "distributor": "booxen",
                    "quantity": 1,
                    "unit_price": "1000",
                    "purchase_status": "in_stock",
                }
            ]
        }
        res = auth_client.post(CONFIRM_URL, data=payload, format="json")
        assert res.status_code == 201
        order.refresh_from_db()
        assert order.ready_to_ship is True

    def test_confirm_recomputes_once_per_request_not_per_item(self, auth_client):
        """REQ-RTS-004/004a: one recompute call per request, not per SKU."""
        order_a = _make_order(shopify_order_id=200405)
        _make_line_item(order_a, shopify_line_item_id=1, sku="SKU-RTS-CONFIRM-E1", quantity=1)
        order_b = _make_order(shopify_order_id=200406)
        _make_line_item(order_b, shopify_line_item_id=1, sku="SKU-RTS-CONFIRM-E2", quantity=1)

        payload = {
            "items": [
                {
                    "sku": "SKU-RTS-CONFIRM-E1",
                    "distributor": "booxen",
                    "quantity": 1,
                    "unit_price": "1000",
                },
                {
                    "sku": "SKU-RTS-CONFIRM-E2",
                    "distributor": "kyobo",
                    "quantity": 1,
                    "unit_price": "2000",
                },
            ]
        }
        with patch(
            "order.purchase_order_views._recompute_order_aggregates",
            wraps=__import__(
                "order.purchase_order_views", fromlist=["_recompute_order_aggregates"]
            )._recompute_order_aggregates,
        ) as mocked:
            res = auth_client.post(CONFIRM_URL, data=payload, format="json")
        assert res.status_code == 201
        assert mocked.call_count == 1
        called_ids = set(mocked.call_args[0][0])
        assert called_ids == {order_a.id, order_b.id}


@pytest.mark.django_db
class TestLineItemStatusUpdateViewRecomputesReadyToShip:
    """AC-RTS-003a — 시나리오6b (single)."""

    def test_single_purchase_status_patch_recomputes(self, auth_client):
        order = _make_order(shopify_order_id=200501)
        li = _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-RTS-SPS",
            purchase_status="on_hold",
            logistics_status="not_shipped",
        )
        url = LINE_ITEM_STATUS_URL.format(pk=li.pk)
        res = auth_client.patch(url, data={"purchase_status": "in_stock"}, format="json")
        assert res.status_code == 200
        order.refresh_from_db()
        assert order.ready_to_ship is True


@pytest.mark.django_db
class TestLineItemBulkStatusUpdateViewRecomputesReadyToShip:
    """AC-RTS-003a — 시나리오6b (bulk)."""

    def test_bulk_purchase_status_patch_recomputes_multiple_orders(self, auth_client):
        order_a = _make_order(shopify_order_id=200601)
        li_a = _make_line_item(
            order_a, shopify_line_item_id=1, sku="SKU-RTS-BPS-A", logistics_status="received"
        )
        order_b = _make_order(shopify_order_id=200602)
        li_b = _make_line_item(
            order_b, shopify_line_item_id=1, sku="SKU-RTS-BPS-B", logistics_status="not_shipped"
        )

        res = auth_client.patch(
            BULK_STATUS_URL,
            data={"ids": [li_a.pk, li_b.pk], "purchase_status": "cs_required"},
            format="json",
        )
        assert res.status_code == 200

        order_a.refresh_from_db()
        order_b.refresh_from_db()
        # cs_required hard-blocks both, regardless of logistics_status.
        assert order_a.ready_to_ship is False
        assert order_b.ready_to_ship is False

    def test_bulk_captures_order_ids_before_update(self, auth_client):
        """.update() does not return affected instances — order_ids must be
        captured beforehand (same constraint as the logistics bulk view)."""
        order = _make_order(shopify_order_id=200603)
        li = _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-RTS-BPS-C", logistics_status="received"
        )
        res = auth_client.patch(
            BULK_STATUS_URL,
            data={"ids": [li.pk], "purchase_status": "in_stock"},
            format="json",
        )
        assert res.status_code == 200
        order.refresh_from_db()
        assert order.ready_to_ship is True


@pytest.mark.django_db
class TestUploadDailyReviewRecomputesReadyToShip:
    """AC-RTS-003a — 시나리오6c: 3 branches, 1 recompute call per request."""

    def test_three_branches_each_recompute_their_own_order(self, auth_client):
        cs_sku = "9788901400001"
        warehouse_sku = "9788901400002"
        nonwarehouse_sku = "9788901400003"

        order_cs = _make_order(shopify_order_id=200701)
        _make_line_item(order_cs, shopify_line_item_id=1, sku=cs_sku, quantity=1)

        order_wh = _make_order(shopify_order_id=200702)
        _make_line_item(order_wh, shopify_line_item_id=1, sku=warehouse_sku, quantity=1)
        WarehouseStock.objects.create(isbn=warehouse_sku, location="korea", quantity=10)

        order_nw = _make_order(shopify_order_id=200703)
        _make_line_item(order_nw, shopify_line_item_id=1, sku=nonwarehouse_sku, quantity=1)

        file_bytes = _make_daily_review_excel([
            {"isbn": cs_sku, "selected": "주문취소", "note": "고객 요청"},
            {"isbn": warehouse_sku, "selected": "재고(한국)"},
            {"isbn": nonwarehouse_sku, "selected": "북센"},
        ])
        res = auth_client.post(
            UPLOAD_DAILY_URL, data={"file": _file_obj(file_bytes)}, format="multipart"
        )
        assert res.status_code == 201

        order_cs.refresh_from_db()
        order_wh.refresh_from_db()
        order_nw.refresh_from_db()

        # CS branch -> purchase_status="order_cancelled" -> zero non-excluded -> null
        assert order_cs.ready_to_ship is None
        # warehouse branch -> purchase_status="in_stock" -> True
        assert order_wh.ready_to_ship is True
        # non-warehouse branch -> purchase_status stays "unordered" -> False
        assert order_nw.ready_to_ship is False

    def test_recompute_called_once_per_upload_not_per_branch(self, auth_client):
        cs_sku = "9788901400011"
        warehouse_sku = "9788901400012"
        nonwarehouse_sku = "9788901400013"

        order_cs = _make_order(shopify_order_id=200711)
        _make_line_item(order_cs, shopify_line_item_id=1, sku=cs_sku, quantity=1)

        order_wh = _make_order(shopify_order_id=200712)
        _make_line_item(order_wh, shopify_line_item_id=1, sku=warehouse_sku, quantity=1)
        WarehouseStock.objects.create(isbn=warehouse_sku, location="korea", quantity=10)

        order_nw = _make_order(shopify_order_id=200713)
        _make_line_item(order_nw, shopify_line_item_id=1, sku=nonwarehouse_sku, quantity=1)

        file_bytes = _make_daily_review_excel([
            {"isbn": cs_sku, "selected": "주문취소", "note": "고객 요청"},
            {"isbn": warehouse_sku, "selected": "재고(한국)"},
            {"isbn": nonwarehouse_sku, "selected": "북센"},
        ])
        with patch(
            "order.purchase_order_views._recompute_order_aggregates",
            wraps=__import__(
                "order.purchase_order_views", fromlist=["_recompute_order_aggregates"]
            )._recompute_order_aggregates,
        ) as mocked:
            res = auth_client.post(
                UPLOAD_DAILY_URL, data={"file": _file_obj(file_bytes)}, format="multipart"
            )
        assert res.status_code == 201
        assert mocked.call_count == 1
        called_ids = set(mocked.call_args[0][0])
        assert called_ids == {order_cs.id, order_wh.id, order_nw.id}


# ---------------------------------------------------------------------------
# T5: Shopify sync exclusion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestShopifySyncExcludesReadyToShip:
    """AC-RTS-005 — 시나리오8."""

    def test_resync_does_not_change_ready_to_ship(self):
        from order.shopify_orders import _sync_single_order

        order = _make_order(shopify_order_id=200801)
        _make_line_item(order, shopify_line_item_id=1, sku="SKU-RTS-SHOPIFY")
        order.ready_to_ship = True
        order.save(update_fields=["ready_to_ship"])

        order_data = {
            "id": 200801,
            "order_number": 1,
            "name": "#1",
            "financial_status": "paid",
            "fulfillment_status": None,
            "total_price": "10000.00",
            "subtotal_price": "10000.00",
            "total_tax": "0.00",
            "total_discounts": "0.00",
            "total_shipping_price_set": None,
            "currency": "KRW",
            "gateway": "manual",
            "note": None,
            "tags": "",
            "cancel_reason": None,
            "source_name": "web",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T01:00:00Z",
            "closed_at": None,
            "cancelled_at": None,
            "processed_at": "2026-01-01T00:00:00Z",
            "customer": None,
            "shipping_address": None,
            "line_items": [],
            "shipping_lines": [],
            "refunds": [],
            "email": None,
            "phone": None,
        }
        _sync_single_order(order_data, "gimssine")

        order.refresh_from_db()
        assert order.ready_to_ship is True


# ---------------------------------------------------------------------------
# T6: OrderDetailSerializer exposes ready_to_ship
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOrderDetailSerializerExposesReadyToShip:
    def test_serializer_includes_ready_to_ship_field(self):
        from order.serializers import OrderDetailSerializer

        order = _make_order(shopify_order_id=200901, ready_to_ship=True)
        data = OrderDetailSerializer(order).data
        assert data["ready_to_ship"] is True

    def test_serializer_returns_null_when_unset(self):
        from order.serializers import OrderDetailSerializer

        order = _make_order(shopify_order_id=200902)
        data = OrderDetailSerializer(order).data
        assert data["ready_to_ship"] is None


# ---------------------------------------------------------------------------
# T7: N+1 regression — query count does not scale with LineItem count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRecomputeOrderAggregatesQueryCountWithReadyToShip:
    """AC-RTS-004/004a — 시나리오7: query count for the extended
    (status + ready_to_ship) recomputation still scales with distinct Order
    count, not LineItem count, via the newly-wired bulk purchase_status
    PATCH endpoint (previously untested for this dimension)."""

    def _bulk_patch_and_capture(
        self, auth_client, order_count: int, items_per_order: int, id_seed: int
    ) -> int:
        ids = []
        for o in range(order_count):
            order = _make_order(shopify_order_id=id_seed + o)
            for i in range(items_per_order):
                li = _make_line_item(
                    order, shopify_line_item_id=i + 1, sku=f"SKU-RTS-QC-{id_seed}-{o}-{i}"
                )
                ids.append(li.pk)

        with CaptureQueriesContext(connection) as ctx:
            res = auth_client.patch(
                BULK_STATUS_URL,
                data={"ids": ids, "purchase_status": "in_stock"},
                format="json",
            )
        assert res.status_code == 200
        return len(ctx.captured_queries)

    def test_query_count_does_not_scale_with_lineitem_count(self, auth_client):
        small_count = self._bulk_patch_and_capture(
            auth_client, order_count=5, items_per_order=3, id_seed=201000
        )
        large_count = self._bulk_patch_and_capture(
            auth_client, order_count=5, items_per_order=30, id_seed=201100
        )
        assert small_count == large_count, (
            f"query count scaled with LineItem count: {small_count} vs {large_count}"
        )
        assert small_count < 15, f"expected a small constant query count, got {small_count}"
