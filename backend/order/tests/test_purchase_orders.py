"""
TDD tests for SPEC-PURCHASE-ORDER-001 M2~M7 purchase order API endpoints.

Coverage targets:
  SC-PO-001  unordered aggregation + auto_distributor
  SC-PO-002  generate-order-file normal (Content-Type Excel)
  SC-PO-003  generate-order-file with unknown SKUs
  SC-PO-004  upload vendor file
  SC-PO-005  auto_select_distributor logic
  SC-PO-006  confirm order normal
  SC-PO-007  confirm order double-link prevention → 409
  SC-PO-008  vendor rules duplicate → 409
  SC-PO-009  vendor rules delete
  SC-PO-014  unauthenticated → 401
  SC-PO-015  invalid file format → 400
  EC-PO-001  empty skus → 400
  EC-PO-002  no unordered items → 200 empty
  EC-PO-003  only bookseen uploaded → kyobo fields null
  EC-PO-004  delete non-existent rule → 404
  EC-PO-005  invalid distributor → 400
  EC-PO-006  missing Excel columns → 422
"""

import io
from decimal import Decimal
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import (
    DistributorVendorRule,
    LineItem,
    Order,
    PurchaseOrder,
    VendorComparison,
)

User = get_user_model()

UNORDERED_URL = "/api/purchase-orders/unordered/"
GENERATE_URL = "/api/purchase-orders/generate-order-file/"
UPLOAD_URL = "/api/purchase-orders/upload-vendor-file/"
COMPARISON_URL = "/api/purchase-orders/comparison/"
CONFIRM_URL = "/api/purchase-orders/confirm/"
RULES_URL = "/api/purchase-orders/vendor-rules/"
PO_LIST_URL = "/api/purchase-orders/"

EXCEL_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="po_test_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()


def _make_order(
    shopify_order_id: int = 90001, store_type: str = "gimssine", name: str | None = None
) -> Order:
    return Order.objects.create(
        shopify_order_id=shopify_order_id, store_type=store_type, name=name
    )


def _make_line_item(
    order: Order,
    shopify_line_item_id: int = 1,
    sku: str = "9788901234567",
    title: str = "테스트 도서",
    vendor: str = "처음교육",
    quantity: int = 2,
) -> LineItem:
    return LineItem.objects.create(
        order=order,
        shopify_line_item_id=shopify_line_item_id,
        sku=sku,
        title=title,
        vendor=vendor,
        quantity=quantity,
    )


def _make_excel(rows: list[list], with_header: bool = True) -> bytes:
    """Build a generic .xlsx file (bookseen-generic format: header row + data)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    if with_header:
        ws.append(["ISBN", "재고여부", "단가"])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_kyobo_excel(rows: list[dict]) -> bytes:
    """Build a Kyobo-format .xlsx file.

    Format: row 0 = '엑셀주문' title, row 1 = headers, row 2+ = data.
    Each dict in rows must have: isbn, status, available ('Y'/'N'),
    returnable ('Y'/'N'), qty, total_price, stock.
    출고가 = total_price / qty
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["엑셀주문"] + [None] * 17)
    ws.append([
        "순서", "ISBN", "도서명", "분야", "상품\n상태", "출고\n여부",
        "반품\n가능여부", "저자", "출판사", "출판년월", "정가",
        "주문\n수량", "출고율", "정가합", "출고가합", "보유\n재고", None, None,
    ])
    # col: 0=순서 1=ISBN 2=도서명 3=분야 4=상품상태 5=출고여부 6=반품가능여부
    #      7=저자 8=출판사 9=출판년월 10=정가 11=주문수량 12=출고율 13=정가합
    #      14=출고가합 15=보유재고
    for i, r in enumerate(rows, start=1):
        qty = float(r.get("qty", 1))
        total_price = float(r.get("total_price", 0))
        ws.append([
            float(i),                  # 0: 순서
            r["isbn"],                 # 1: ISBN
            r.get("title", ""),        # 2: 도서명
            r.get("category", ""),     # 3: 분야
            r.get("status", "정상"),   # 4: 상품상태
            r.get("available", "Y"),   # 5: 출고여부
            r.get("returnable", "Y"),  # 6: 반품가능여부
            r.get("author", ""),       # 7: 저자
            r.get("publisher", ""),    # 8: 출판사
            r.get("pub_date", ""),     # 9: 출판년월
            r.get("list_price", 0),    # 10: 정가
            qty,                       # 11: 주문수량
            r.get("rate", "70%"),      # 12: 출고율
            r.get("list_total", 0),    # 13: 정가합
            total_price,               # 14: 출고가합
            float(r.get("stock", 0)),  # 15: 보유재고
            None, None,
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# SC-PO-014: Unauthenticated requests → 401
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUnauthorizedAccess:
    """SC-PO-014: All endpoints require JWT authentication."""

    def test_unordered_requires_auth(self, anon_client):
        res = anon_client.get(UNORDERED_URL)
        assert res.status_code == 401

    def test_generate_requires_auth(self, anon_client):
        res = anon_client.post(GENERATE_URL, data={"distributor": "bookseen", "skus": []}, format="json")
        assert res.status_code == 401

    def test_upload_requires_auth(self, anon_client):
        res = anon_client.post(UPLOAD_URL)
        assert res.status_code == 401

    def test_comparison_requires_auth(self, anon_client):
        res = anon_client.get(COMPARISON_URL)
        assert res.status_code == 401

    def test_confirm_requires_auth(self, anon_client):
        res = anon_client.post(CONFIRM_URL, data={"items": []}, format="json")
        assert res.status_code == 401

    def test_rules_list_requires_auth(self, anon_client):
        res = anon_client.get(RULES_URL)
        assert res.status_code == 401

    def test_po_list_requires_auth(self, anon_client):
        res = anon_client.get(PO_LIST_URL)
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# M2: GET /api/purchase-orders/unordered/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUnorderedItemsView:
    """SC-PO-001, EC-PO-002"""

    def test_returns_empty_when_no_line_items(self, auth_client):
        """EC-PO-002: No unordered items → 200 with empty results."""
        res = auth_client.get(UNORDERED_URL)
        assert res.status_code == 200
        assert res.data["count"] == 0
        assert res.data["results"] == []

    def test_returns_individual_line_items(self, auth_client):
        """SC-PO-001: Each LineItem is returned as a separate row (no SKU aggregation)."""
        order1 = _make_order(shopify_order_id=91001, name="#1001")
        order2 = _make_order(shopify_order_id=91002, name="#1002")
        _make_line_item(order1, shopify_line_item_id=1, sku="SKU-A", quantity=3)
        _make_line_item(order2, shopify_line_item_id=2, sku="SKU-A", quantity=2)

        res = auth_client.get(UNORDERED_URL)
        assert res.status_code == 200
        assert res.data["count"] == 2
        skus = [r["sku"] for r in res.data["results"]]
        assert skus.count("SKU-A") == 2
        quantities = {r["order_name"]: r["quantity"] for r in res.data["results"]}
        assert quantities["#1001"] == 3
        assert quantities["#1002"] == 2

    def test_excludes_line_items_linked_to_purchase_order(self, auth_client):
        """SC-PO-001: LineItems already linked to a PurchaseOrder are excluded."""
        order = _make_order(shopify_order_id=91003)
        li = _make_line_item(order, shopify_line_item_id=1, sku="SKU-B")
        po = PurchaseOrder.objects.create(
            sku="SKU-B", title="Book B", distributor="bookseen", quantity=2
        )
        po.line_items.add(li)

        res = auth_client.get(UNORDERED_URL)
        assert res.status_code == 200
        skus = [r["sku"] for r in res.data["results"]]
        assert "SKU-B" not in skus

    def test_auto_distributor_from_vendor_rule(self, auth_client):
        """SC-PO-001: auto_distributor comes from DistributorVendorRule.publisher_name = vendor."""
        DistributorVendorRule.objects.create(
            publisher_name="처음교육", distributor="choeumgoyuk"
        )
        order = _make_order(shopify_order_id=91004)
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-C", vendor="처음교육"
        )

        res = auth_client.get(UNORDERED_URL)
        assert res.status_code == 200
        result = next(r for r in res.data["results"] if r["sku"] == "SKU-C")
        assert result["auto_distributor"] == "choeumgoyuk"

    def test_auto_distributor_null_when_no_rule(self, auth_client):
        """SC-PO-001: auto_distributor is null when no DistributorVendorRule exists."""
        order = _make_order(shopify_order_id=91005)
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-D", vendor="알수없는출판사"
        )

        res = auth_client.get(UNORDERED_URL)
        assert res.status_code == 200
        result = next(r for r in res.data["results"] if r["sku"] == "SKU-D")
        assert result["auto_distributor"] is None

    def test_excludes_line_items_with_null_sku(self, auth_client):
        """LineItems with null SKU should be excluded from aggregation."""
        order = _make_order(shopify_order_id=91006)
        LineItem.objects.create(
            order=order,
            shopify_line_item_id=99,
            sku=None,
            title="No SKU Item",
            quantity=1,
        )
        res = auth_client.get(UNORDERED_URL)
        assert res.status_code == 200
        assert res.data["count"] == 0


# ---------------------------------------------------------------------------
# M3: POST /api/purchase-orders/generate-order-file/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateOrderFileView:
    """SC-PO-002, SC-PO-003, EC-PO-001, EC-PO-005"""

    def _setup_sku(self, sku: str = "9788901234567", title: str = "테스트 도서", quantity: int = 3):
        order = _make_order(shopify_order_id=92001)
        _make_line_item(
            order, shopify_line_item_id=1, sku=sku, title=title, quantity=quantity
        )

    def test_returns_excel_for_valid_skus(self, auth_client):
        """SC-PO-002: Valid SKUs → returns Excel binary with correct Content-Type."""
        self._setup_sku("9788901234567", "Great Gatsby", 3)
        payload = {"distributor": "bookseen", "skus": ["9788901234567"]}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 200
        assert EXCEL_CONTENT_TYPE in res["Content-Type"]
        # Verify content is a valid xlsx
        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0][0] == "ISBN"
        assert rows[1][0] == "9788901234567"

    def test_filename_contains_distributor_and_date(self, auth_client):
        """SC-PO-002: Content-Disposition includes distributor name and date."""
        self._setup_sku()
        payload = {"distributor": "kyobo", "skus": ["9788901234567"]}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 200
        disposition = res.get("Content-Disposition", "")
        assert "kyobo" in disposition
        assert ".xlsx" in disposition

    def test_empty_skus_returns_400(self, auth_client):
        """EC-PO-001: skus=[] → HTTP 400."""
        payload = {"distributor": "bookseen", "skus": []}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 400

    def test_all_unknown_skus_returns_warning_json(self, auth_client):
        """SC-PO-003: All SKUs unknown → JSON warning (no Excel)."""
        payload = {"distributor": "bookseen", "skus": ["0000000000000"]}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 200
        assert "unknown_skus" in res.data
        assert "0000000000000" in res.data["unknown_skus"]
        assert EXCEL_CONTENT_TYPE not in res.get("Content-Type", "")

    def test_mixed_skus_returns_warning_json(self, auth_client):
        """SC-PO-003: Some unknown SKUs → JSON warning with unknown_skus list."""
        self._setup_sku("9788901234567", "Valid Book", 2)
        payload = {
            "distributor": "bookseen",
            "skus": ["9788901234567", "0000000000000"],
        }
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 200
        assert "unknown_skus" in res.data
        assert "0000000000000" in res.data["unknown_skus"]

    def test_invalid_distributor_returns_400(self, auth_client):
        """EC-PO-005: Invalid distributor value → HTTP 400."""
        payload = {"distributor": "invalid_dist", "skus": ["9788901234567"]}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 400

    def test_missing_distributor_returns_400(self, auth_client):
        """distributor field required."""
        payload = {"skus": ["9788901234567"]}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# M4a: POST /api/purchase-orders/upload-vendor-file/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadVendorFileView:
    """SC-PO-004, SC-PO-015, EC-PO-003, EC-PO-006"""

    def test_upload_bookseen_file(self, auth_client):
        """SC-PO-004: Upload bookseen Excel → VendorComparison created/updated."""
        excel_bytes = _make_excel([
            ["9788901234567", True, 12000],
            ["9788901234568", False, 0],
        ])
        file_obj = io.BytesIO(excel_bytes)
        file_obj.name = "bookseen.xlsx"
        res = auth_client.post(
            UPLOAD_URL,
            data={"distributor": "bookseen", "file": file_obj},
            format="multipart",
        )
        assert res.status_code == 200
        assert res.data["parsed_count"] == 2
        assert res.data["distributor"] == "bookseen"
        assert len(res.data["comparisons"]) == 2

        vc = VendorComparison.objects.get(sku="9788901234567")
        assert vc.bookseen_available is True
        assert vc.bookseen_price == Decimal("12000")

    def test_upload_kyobo_file(self, auth_client):
        """SC-PO-004: Upload kyobo Excel (교보 format) → VendorComparison kyobo fields updated."""
        excel_bytes = _make_kyobo_excel([{
            "isbn": "9788901234567", "qty": 2, "total_price": 23000.0,
            "stock": 10, "available": "Y", "returnable": "Y", "status": "정상",
            "publisher": "테스트출판사",
        }])
        file_obj = io.BytesIO(excel_bytes)
        file_obj.name = "kyobo.xlsx"
        res = auth_client.post(
            UPLOAD_URL,
            data={"distributor": "kyobo", "file": file_obj},
            format="multipart",
        )
        assert res.status_code == 200
        vc = VendorComparison.objects.get(sku="9788901234567")
        assert vc.kyobo_available is True
        assert vc.kyobo_price == Decimal("11500")  # 23000 / 2
        assert vc.kyobo_stock == 10
        assert vc.kyobo_returnable is True
        assert vc.kyobo_status == "정상"
        assert vc.kyobo_publisher == "테스트출판사"
        assert vc.kyobo_ordered_qty == 2
        assert vc.kyobo_total_price == Decimal("23000")

    def test_only_bookseen_uploaded_kyobo_fields_null(self, auth_client):
        """EC-PO-003: Only bookseen uploaded → kyobo fields remain null."""
        excel_bytes = _make_excel([["9788901234569", True, 10000]])
        file_obj = io.BytesIO(excel_bytes)
        file_obj.name = "bookseen.xlsx"
        auth_client.post(
            UPLOAD_URL,
            data={"distributor": "bookseen", "file": file_obj},
            format="multipart",
        )
        vc = VendorComparison.objects.get(sku="9788901234569")
        assert vc.kyobo_available is None
        assert vc.kyobo_price is None

    def test_invalid_file_format_returns_400(self, auth_client):
        """SC-PO-015: Non-.xlsx/.xls file → HTTP 400."""
        fake_csv = io.BytesIO(b"isbn,available,price\n9788901234567,true,10000")
        fake_csv.name = "data.csv"
        res = auth_client.post(
            UPLOAD_URL,
            data={"distributor": "bookseen", "file": fake_csv},
            format="multipart",
        )
        assert res.status_code == 400

    def test_upsert_updates_existing_record(self, auth_client):
        """SC-PO-004: Re-upload updates existing VendorComparison record."""
        VendorComparison.objects.create(
            sku="9788901234567", bookseen_available=False, bookseen_price=Decimal("9000")
        )
        excel_bytes = _make_excel([["9788901234567", True, 12000]])
        file_obj = io.BytesIO(excel_bytes)
        file_obj.name = "bookseen.xlsx"
        auth_client.post(
            UPLOAD_URL,
            data={"distributor": "bookseen", "file": file_obj},
            format="multipart",
        )
        vc = VendorComparison.objects.get(sku="9788901234567")
        assert vc.bookseen_available is True
        assert vc.bookseen_price == Decimal("12000")
        assert VendorComparison.objects.filter(sku="9788901234567").count() == 1


# ---------------------------------------------------------------------------
# SC-PO-005: auto_select_distributor logic
# ---------------------------------------------------------------------------


class TestAutoSelectDistributor:
    """SC-PO-005: Three cases for distributor auto-selection."""

    def test_both_available_lower_price_wins(self):
        from order.excel_utils import auto_select_distributor

        result = auto_select_distributor(
            bookseen_available=True,
            bookseen_price=Decimal("10000"),
            kyobo_available=True,
            kyobo_price=Decimal("11000"),
        )
        assert result == "bookseen"

    def test_both_available_kyobo_cheaper(self):
        from order.excel_utils import auto_select_distributor

        result = auto_select_distributor(
            bookseen_available=True,
            bookseen_price=Decimal("12000"),
            kyobo_available=True,
            kyobo_price=Decimal("10000"),
        )
        assert result == "kyobo"

    def test_only_one_available(self):
        from order.excel_utils import auto_select_distributor

        result = auto_select_distributor(
            bookseen_available=False,
            bookseen_price=None,
            kyobo_available=True,
            kyobo_price=Decimal("11000"),
        )
        assert result == "kyobo"

    def test_neither_available_returns_none(self):
        from order.excel_utils import auto_select_distributor

        result = auto_select_distributor(
            bookseen_available=False,
            bookseen_price=None,
            kyobo_available=False,
            kyobo_price=None,
        )
        assert result is None


# ---------------------------------------------------------------------------
# M4b: GET /api/purchase-orders/comparison/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVendorComparisonView:
    """EC-PO-003: comparison list"""

    def test_returns_empty_list(self, auth_client):
        res = auth_client.get(COMPARISON_URL)
        assert res.status_code == 200
        assert res.data["count"] == 0

    def test_returns_comparison_records(self, auth_client):
        VendorComparison.objects.create(
            sku="9788901234567",
            bookseen_available=True,
            bookseen_price=Decimal("12000"),
        )
        res = auth_client.get(COMPARISON_URL)
        assert res.status_code == 200
        assert res.data["count"] == 1
        record = res.data["results"][0]
        assert record["sku"] == "9788901234567"
        assert record["bookseen_available"] is True


# ---------------------------------------------------------------------------
# M5: POST /api/purchase-orders/confirm/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConfirmOrderView:
    """SC-PO-006, SC-PO-007"""

    def test_confirm_creates_purchase_orders(self, auth_client):
        """SC-PO-006: Confirm creates PurchaseOrder and links LineItems."""
        order = _make_order(shopify_order_id=93001)
        _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-001", title="Book One", quantity=3
        )
        payload = {
            "items": [
                {
                    "sku": "ISBN-001",
                    "distributor": "bookseen",
                    "quantity": 3,
                    "unit_price": "10500.00",
                }
            ]
        }
        res = auth_client.post(CONFIRM_URL, data=payload, format="json")
        assert res.status_code == 201
        assert res.data["created_count"] == 1
        assert len(res.data["purchase_order_ids"]) == 1

        po = PurchaseOrder.objects.get(pk=res.data["purchase_order_ids"][0])
        assert po.sku == "ISBN-001"
        assert po.distributor == "bookseen"
        assert po.line_items.count() >= 1

    def test_confirm_multiple_skus(self, auth_client):
        """SC-PO-006: Confirm with multiple SKUs creates multiple PurchaseOrders."""
        order = _make_order(shopify_order_id=93002)
        _make_line_item(order, shopify_line_item_id=1, sku="ISBN-A", quantity=2)
        _make_line_item(order, shopify_line_item_id=2, sku="ISBN-B", quantity=1)
        payload = {
            "items": [
                {"sku": "ISBN-A", "distributor": "bookseen", "quantity": 2, "unit_price": "10000.00"},
                {"sku": "ISBN-B", "distributor": "kyobo", "quantity": 1, "unit_price": "8000.00"},
            ]
        }
        res = auth_client.post(CONFIRM_URL, data=payload, format="json")
        assert res.status_code == 201
        assert res.data["created_count"] == 2

    def test_double_confirm_returns_409(self, auth_client):
        """SC-PO-007: Confirming already-linked LineItems → HTTP 409."""
        order = _make_order(shopify_order_id=93003)
        li = _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-DUPE", quantity=2
        )
        # First confirmation
        po = PurchaseOrder.objects.create(
            sku="ISBN-DUPE", title="Dupe Book", distributor="bookseen", quantity=2
        )
        po.line_items.add(li)

        payload = {
            "items": [{"sku": "ISBN-DUPE", "distributor": "bookseen", "quantity": 2, "unit_price": "9000.00"}]
        }
        res = auth_client.post(CONFIRM_URL, data=payload, format="json")
        assert res.status_code == 409

    def test_sku_with_no_unordered_items_returns_400(self, auth_client):
        """EC-PO-002 variant: SKU has no unordered LineItem → HTTP 400."""
        payload = {
            "items": [{"sku": "NONEXISTENT-SKU", "distributor": "bookseen", "quantity": 1, "unit_price": "9000.00"}]
        }
        res = auth_client.post(CONFIRM_URL, data=payload, format="json")
        assert res.status_code == 400

    def test_confirm_empty_items_returns_400(self, auth_client):
        """Empty items list → HTTP 400."""
        res = auth_client.post(CONFIRM_URL, data={"items": []}, format="json")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# M6: /api/purchase-orders/vendor-rules/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDistributorVendorRuleViews:
    """SC-PO-008, SC-PO-009, EC-PO-004"""

    def test_list_rules_empty(self, auth_client):
        res = auth_client.get(RULES_URL)
        assert res.status_code == 200
        assert res.data["count"] == 0
        assert res.data["results"] == []

    def test_create_rule(self, auth_client):
        """POST creates a new DistributorVendorRule."""
        payload = {"publisher_name": "처음교육출판사", "distributor": "choeumgoyuk"}
        res = auth_client.post(RULES_URL, data=payload, format="json")
        assert res.status_code == 201
        assert DistributorVendorRule.objects.filter(publisher_name="처음교육출판사").exists()

    def test_duplicate_publisher_name_returns_409(self, auth_client):
        """SC-PO-008: Duplicate publisher_name → HTTP 409."""
        DistributorVendorRule.objects.create(
            publisher_name="아가페출판사", distributor="agape"
        )
        payload = {"publisher_name": "아가페출판사", "distributor": "choeumgoyuk"}
        res = auth_client.post(RULES_URL, data=payload, format="json")
        assert res.status_code == 409

    def test_delete_rule(self, auth_client):
        """SC-PO-009: DELETE removes the rule successfully."""
        rule = DistributorVendorRule.objects.create(
            publisher_name="삭제출판사", distributor="agape"
        )
        res = auth_client.delete(f"{RULES_URL}{rule.pk}/")
        assert res.status_code == 204
        assert not DistributorVendorRule.objects.filter(pk=rule.pk).exists()

    def test_delete_nonexistent_rule_returns_404(self, auth_client):
        """EC-PO-004: Deleting non-existent rule → HTTP 404."""
        res = auth_client.delete(f"{RULES_URL}99999/")
        assert res.status_code == 404

    def test_invalid_distributor_in_rule_returns_400(self, auth_client):
        """EC-PO-005: Invalid distributor in vendor rule → HTTP 400."""
        payload = {"publisher_name": "테스트출판사", "distributor": "invalid_dist"}
        res = auth_client.post(RULES_URL, data=payload, format="json")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# M7: GET /api/purchase-orders/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPurchaseOrderListView:
    """M7: List PurchaseOrders with filters and pagination."""

    def _create_po(self, sku: str, distributor: str = "bookseen", status: str = "pending") -> PurchaseOrder:
        return PurchaseOrder.objects.create(
            sku=sku, title=f"Book {sku}", distributor=distributor, quantity=1, status=status
        )

    def test_list_returns_paginated_results(self, auth_client):
        for i in range(3):
            self._create_po(f"SKU-LIST-{i}")
        res = auth_client.get(PO_LIST_URL)
        assert res.status_code == 200
        assert res.data["count"] == 3

    def test_filter_by_distributor(self, auth_client):
        self._create_po("SKU-BS", distributor="bookseen")
        self._create_po("SKU-KY", distributor="kyobo")
        res = auth_client.get(PO_LIST_URL, {"distributor": "bookseen"})
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["distributor"] == "bookseen"

    def test_filter_by_status(self, auth_client):
        self._create_po("SKU-PEND", status="pending")
        self._create_po("SKU-CONF", status="confirmed")
        res = auth_client.get(PO_LIST_URL, {"status": "confirmed"})
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["status"] == "confirmed"

    def test_ordered_by_created_at_desc(self, auth_client):
        po1 = self._create_po("SKU-FIRST")
        po2 = self._create_po("SKU-SECOND")
        res = auth_client.get(PO_LIST_URL)
        assert res.status_code == 200
        ids = [r["id"] for r in res.data["results"]]
        assert ids.index(po2.pk) < ids.index(po1.pk)

    def test_pagination_page_size_50(self, auth_client):
        for i in range(55):
            self._create_po(f"SKU-PAG-{i}")
        res = auth_client.get(PO_LIST_URL)
        assert res.status_code == 200
        assert res.data["count"] == 55
        assert len(res.data["results"]) == 50
        assert res.data["next"] is not None

    def test_filter_by_date_range(self, auth_client):
        """date_from and date_to filter on created_at."""
        self._create_po("SKU-DATE")
        res = auth_client.get(PO_LIST_URL, {"date_from": "2020-01-01", "date_to": "2099-12-31"})
        assert res.status_code == 200
        assert res.data["count"] >= 1


# ---------------------------------------------------------------------------
# excel_utils unit tests
# ---------------------------------------------------------------------------


class TestGenerateOrderExcel:
    """Unit tests for excel_utils.generate_order_excel."""

    def test_bookseen_column_format(self):
        from order.excel_utils import generate_order_excel

        data = [{"sku": "9780001", "title": "Test Book", "total_quantity": 5}]
        result = generate_order_excel(data, "bookseen")
        assert isinstance(result, bytes)
        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0] == ("ISBN", "주문수량", "도서명", "출판사", "저자", "정가")
        assert rows[1][0] == "9780001"
        assert rows[1][1] == 5

    def test_kyobo_column_format(self):
        from order.excel_utils import generate_order_excel

        data = [{"sku": "9780001", "title": "Test Book", "total_quantity": 3}]
        result = generate_order_excel(data, "kyobo")
        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0] == ("ISBN", "수량")
        assert rows[1][0] == "9780001"
        assert rows[1][1] == 3

    def test_empty_data_still_has_header(self):
        from order.excel_utils import generate_order_excel

        result = generate_order_excel([], "kyobo")
        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0] == ("ISBN", "수량")


class TestParseVendorExcel:
    """Unit tests for excel_utils.parse_vendor_excel."""

    def test_parses_standard_columns(self):
        from order.excel_utils import parse_vendor_excel

        excel_bytes = _make_excel([["9780001", True, 12000]])
        results = parse_vendor_excel(excel_bytes, "bookseen")
        assert len(results) == 1
        assert results[0]["sku"] == "9780001"
        assert results[0]["available"] is True
        assert results[0]["price"] == 12000.0

    def test_skips_empty_sku_rows(self):
        from order.excel_utils import parse_vendor_excel

        excel_bytes = _make_excel([["", True, 5000], ["9780002", False, 0]])
        results = parse_vendor_excel(excel_bytes, "bookseen")
        assert len(results) == 1
        assert results[0]["sku"] == "9780002"

    def test_handles_empty_file(self):
        from order.excel_utils import parse_vendor_excel

        wb = openpyxl.Workbook()
        buf = io.BytesIO()
        wb.save(buf)
        with pytest.raises(ValueError, match="Empty file"):
            parse_vendor_excel(buf.getvalue(), "bookseen")

    def test_parses_bookseen_xls_format(self):
        """Bookseen .xls: row 0 = timestamp, row 1 = headers, row 2+ = data.
        ISBN at col 14, 출고가 at col 6, 재고량 at col 7."""
        from order.excel_utils import _XLS_MAGIC, parse_vendor_excel

        rows = [[""] * 16, [""] * 16, [0.0] * 16]
        rows[0][0] = "조회기간 10건"
        rows[2][14] = 8809264180921.0  # ISBN as float (xlrd numeric cell)
        rows[2][6] = 15260.0           # 출고가
        rows[2][7] = 3.0               # 재고량 > 0 → available

        mock_sheet = MagicMock()
        mock_sheet.nrows = 3
        mock_sheet.row_values.side_effect = lambda n: rows[n]

        mock_wb = MagicMock()
        mock_wb.sheet_by_index.return_value = mock_sheet

        xls_magic_bytes = _XLS_MAGIC + b"\x00" * 100

        with patch("order.excel_utils.xlrd.open_workbook", return_value=mock_wb):
            results = parse_vendor_excel(xls_magic_bytes, "bookseen")

        assert len(results) == 1
        assert results[0]["sku"] == "8809264180921"
        assert results[0]["available"] is True
        assert results[0]["price"] == 15260.0

    def test_bookseen_xls_zero_stock_is_unavailable(self):
        """재고량 == 0 → available = False."""
        from order.excel_utils import _XLS_MAGIC, parse_vendor_excel

        rows = [[""] * 16, [""] * 16, [0.0] * 16]
        rows[2][14] = 9780000000000.0
        rows[2][6] = 12000.0
        rows[2][7] = 0.0

        mock_sheet = MagicMock()
        mock_sheet.nrows = 3
        mock_sheet.row_values.side_effect = lambda n: rows[n]

        mock_wb = MagicMock()
        mock_wb.sheet_by_index.return_value = mock_sheet

        with patch("order.excel_utils.xlrd.open_workbook", return_value=mock_wb):
            results = parse_vendor_excel(_XLS_MAGIC + b"\x00" * 100, "bookseen")

        assert results[0]["available"] is False
