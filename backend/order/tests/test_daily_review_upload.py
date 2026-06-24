"""
TDD tests for SPEC-PURCHASE-ORDER-005.

Covers:
  REQ-PO5-001  _DISTRIBUTOR_LABEL_MAP includes warehouse codes
  REQ-PO5-002  _DAILY_REVIEW_HEADERS uses location columns (재고(한국)/재고(CA)/재고(NJ))
  REQ-PO5-003  generate_daily_review_excel uses korea_stock/ca_stock/nj_stock keys
  REQ-PO5-004  UploadDailyReviewView deducts WarehouseStock
  REQ-PO5-005  UploadDailyReviewView sets LineItem.purchase_status = "in_stock"
  REQ-PO5-006  UploadDailyReviewView does NOT create PurchaseOrder for warehouse rows
  REQ-PO5-007  Upload response includes confirmed_by_distributor
  REQ-PO5-008  VALID_DISTRIBUTORS includes warehouse codes
"""

import io

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, Order, PurchaseOrder, WarehouseStock

User = get_user_model()

UPLOAD_DAILY_URL = "/api/purchase-orders/upload-daily-review/"
GENERATE_URL = "/api/purchase-orders/generate-order-file/"
DAILY_REVIEW_EXCEL_URL = "/api/purchase-orders/daily-review-excel/"

EXCEL_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="dr_test_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def _make_order(shopify_order_id: int = 80001, name: str = "#8001") -> Order:
    return Order.objects.create(
        shopify_order_id=shopify_order_id, store_type="gimssine", name=name
    )


def _make_line_item(
    order: Order,
    sku: str = "9788901234567",
    title: str = "테스트 도서",
    quantity: int = 2,
    shopify_line_item_id: int = 1,
) -> LineItem:
    return LineItem.objects.create(
        order=order,
        shopify_line_item_id=shopify_line_item_id,
        sku=sku,
        title=title,
        quantity=quantity,
    )


def _make_daily_review_excel(rows: list[dict]) -> bytes:
    """
    Build a Daily Review .xlsx file with standard headers.

    Each dict in rows must have: isbn, selected (Korean label), and optionally note.
    """
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
            "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            row.get("selected", ""),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_legacy_daily_review_excel(rows: list[dict]) -> bytes:
    """Build a Daily Review .xlsx file with the OLD headers (창고재고수량/창고재고위치)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "주문번호", "ISBN", "제목", "수량", "주문위치", "메모",
        "창고재고수량", "창고재고위치",
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
            row.get("warehouse_qty", 0),
            row.get("warehouse_locations", ""),
            "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            row.get("selected", ""),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# REQ-PO5-001: _DISTRIBUTOR_LABEL_MAP includes warehouse codes
# ---------------------------------------------------------------------------


class TestDistributorLabelMapWarehouseCodes:
    """REQ-PO5-001: Warehouse display names are mapped to internal codes."""

    def test_label_map_includes_warehouse_korea(self):
        from order.excel_utils import _DISTRIBUTOR_LABEL_MAP

        assert "재고(한국)" in _DISTRIBUTOR_LABEL_MAP
        assert _DISTRIBUTOR_LABEL_MAP["재고(한국)"] == "warehouse_korea"

    def test_label_map_includes_warehouse_ca(self):
        from order.excel_utils import _DISTRIBUTOR_LABEL_MAP

        assert "재고(CA)" in _DISTRIBUTOR_LABEL_MAP
        assert _DISTRIBUTOR_LABEL_MAP["재고(CA)"] == "warehouse_ca"

    def test_label_map_includes_warehouse_nj(self):
        from order.excel_utils import _DISTRIBUTOR_LABEL_MAP

        assert "재고(NJ)" in _DISTRIBUTOR_LABEL_MAP
        assert _DISTRIBUTOR_LABEL_MAP["재고(NJ)"] == "warehouse_nj"


# ---------------------------------------------------------------------------
# REQ-PO5-002: parse_daily_review_excel recognizes warehouse labels
# ---------------------------------------------------------------------------


class TestParseDailyReviewExcelWarehouseCodes:
    """REQ-PO5-002: Parser correctly maps Korean warehouse labels to internal codes."""

    def test_parses_warehouse_korea_label(self):
        from order.excel_utils import parse_daily_review_excel

        file_bytes = _make_daily_review_excel([
            {"isbn": "9788901234567", "selected": "재고(한국)"},
        ])
        results = parse_daily_review_excel(file_bytes)
        assert len(results) == 1
        assert results[0]["sku"] == "9788901234567"
        assert results[0]["distributor"] == "warehouse_korea"

    def test_parses_warehouse_ca_label(self):
        from order.excel_utils import parse_daily_review_excel

        file_bytes = _make_daily_review_excel([
            {"isbn": "9788901234568", "selected": "재고(CA)"},
        ])
        results = parse_daily_review_excel(file_bytes)
        assert len(results) == 1
        assert results[0]["distributor"] == "warehouse_ca"

    def test_parses_warehouse_nj_label(self):
        from order.excel_utils import parse_daily_review_excel

        file_bytes = _make_daily_review_excel([
            {"isbn": "9788901234569", "selected": "재고(NJ)"},
        ])
        results = parse_daily_review_excel(file_bytes)
        assert len(results) == 1
        assert results[0]["distributor"] == "warehouse_nj"


# ---------------------------------------------------------------------------
# REQ-PO5-002/REQ-PO5-003: generate_daily_review_excel uses new column headers
# ---------------------------------------------------------------------------


class TestDailyReviewExcelHeaders:
    """REQ-PO5-002: Generated Excel has location columns instead of old warehouse columns."""

    def test_headers_contain_location_columns(self):
        from order.excel_utils import generate_daily_review_excel

        file_bytes = generate_daily_review_excel([])
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        assert "재고(한국)" in headers
        assert "재고(CA)" in headers
        assert "재고(NJ)" in headers

    def test_headers_do_not_contain_old_columns(self):
        from order.excel_utils import generate_daily_review_excel

        file_bytes = generate_daily_review_excel([])
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        assert "창고재고수량" not in headers
        assert "창고재고위치" not in headers

    def test_data_row_uses_new_stock_keys(self):
        from order.excel_utils import generate_daily_review_excel

        rows = [{
            "order_name": "#001", "sku": "9788901234567", "title": "Test", "quantity": 2,
            "location": "", "note": "",
            "korea_stock": 5, "ca_stock": 3, "nj_stock": 1,
            "bs_price": None, "ky_price": None, "bs_status": None,
            "ky_stock": None, "ky_status": None, "price_diff": None,
            "bs_arrival": None, "bs_returnable": None, "ky_available": None,
            "ky_returnable": None, "price_diff_alert": False,
            "publisher": None, "candidate_basis": None, "selected": "북센",
        }]
        file_bytes = generate_daily_review_excel(rows)
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        korea_col_idx = headers.index("재고(한국)")
        ca_col_idx = headers.index("재고(CA)")
        nj_col_idx = headers.index("재고(NJ)")

        data_row = list(ws.iter_rows(values_only=True))[1]
        assert data_row[korea_col_idx] == 5
        assert data_row[ca_col_idx] == 3
        assert data_row[nj_col_idx] == 1


# ---------------------------------------------------------------------------
# REQ-PO5-008: VALID_DISTRIBUTORS includes warehouse codes
# ---------------------------------------------------------------------------


class TestValidDistributors:
    """REQ-PO5-008: VALID_DISTRIBUTORS set includes warehouse codes."""

    def test_valid_distributors_includes_warehouse_korea(self):
        from order.purchase_order_views import VALID_DISTRIBUTORS

        assert "warehouse_korea" in VALID_DISTRIBUTORS

    def test_valid_distributors_includes_warehouse_ca(self):
        from order.purchase_order_views import VALID_DISTRIBUTORS

        assert "warehouse_ca" in VALID_DISTRIBUTORS

    def test_valid_distributors_includes_warehouse_nj(self):
        from order.purchase_order_views import VALID_DISTRIBUTORS

        assert "warehouse_nj" in VALID_DISTRIBUTORS


# ---------------------------------------------------------------------------
# REQ-PO5-008: GenerateOrderFileView accepts warehouse distributor codes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateOrderFileAcceptsWarehouseCodes:
    """REQ-PO5-008: generate-order-file accepts warehouse distributor codes (200, not 400)."""

    def _setup_sku(self, sku: str = "9788901234567", quantity: int = 2):
        order = _make_order(shopify_order_id=82001)
        _make_line_item(order, sku=sku, quantity=quantity, shopify_line_item_id=10)

    def test_warehouse_korea_returns_excel_or_warning(self, auth_client):
        """warehouse_korea is a valid distributor — not 400."""
        self._setup_sku()
        payload = {"distributor": "warehouse_korea", "skus": ["9788901234567"]}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        # Either Excel (200) or warning JSON (200) — both are OK; what matters is NOT 400
        assert res.status_code == 200

    def test_warehouse_ca_returns_200(self, auth_client):
        self._setup_sku("9788901234568")
        payload = {"distributor": "warehouse_ca", "skus": ["9788901234568"]}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 200

    def test_warehouse_nj_returns_200(self, auth_client):
        self._setup_sku("9788901234569")
        payload = {"distributor": "warehouse_nj", "skus": ["9788901234569"]}
        res = auth_client.post(GENERATE_URL, data=payload, format="json")
        assert res.status_code == 200


# ---------------------------------------------------------------------------
# REQ-PO5-004: UploadDailyReviewView deducts WarehouseStock
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadWarehouseDeductsStock:
    """REQ-PO5-004: Warehouse upload deducts LineItem quantities from WarehouseStock."""

    def test_upload_warehouse_deducts_stock(self, auth_client):
        """CA warehouse stock is decremented by sum of unordered LineItem quantities."""
        sku = "9788901234567"
        order = _make_order(shopify_order_id=83001)
        _make_line_item(order, sku=sku, quantity=2, shopify_line_item_id=1)
        WarehouseStock.objects.create(isbn=sku, location="ca", quantity=10)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(CA)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(
            UPLOAD_DAILY_URL,
            data={"file": file_obj},
            format="multipart",
        )
        assert res.status_code == 201

        stock = WarehouseStock.objects.get(isbn=sku, location="ca")
        assert stock.quantity == 8  # 10 - 2

    def test_upload_warehouse_deducts_korea_stock(self, auth_client):
        """Korea warehouse stock is decremented correctly."""
        sku = "9788901234570"
        order = _make_order(shopify_order_id=83002)
        _make_line_item(order, sku=sku, quantity=3, shopify_line_item_id=2)
        WarehouseStock.objects.create(isbn=sku, location="korea", quantity=20)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(한국)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")

        stock = WarehouseStock.objects.get(isbn=sku, location="korea")
        assert stock.quantity == 17  # 20 - 3

    def test_upload_warehouse_deducts_nj_stock(self, auth_client):
        """NJ warehouse stock is decremented correctly."""
        sku = "9788901234571"
        order = _make_order(shopify_order_id=83003)
        _make_line_item(order, sku=sku, quantity=1, shopify_line_item_id=3)
        WarehouseStock.objects.create(isbn=sku, location="nj", quantity=5)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(NJ)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")

        stock = WarehouseStock.objects.get(isbn=sku, location="nj")
        assert stock.quantity == 4  # 5 - 1


# ---------------------------------------------------------------------------
# REQ-PO5-004: Floor at zero
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadWarehouseFloorAtZero:
    """REQ-PO5-004: Quantity never goes negative; floored at 0."""

    def test_floor_at_zero_when_stock_insufficient(self, auth_client):
        """If LineItem quantity > current stock, result is 0 (not negative)."""
        sku = "9788901299001"
        order = _make_order(shopify_order_id=84001)
        _make_line_item(order, sku=sku, quantity=10, shopify_line_item_id=1)
        WarehouseStock.objects.create(isbn=sku, location="ca", quantity=3)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(CA)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")

        stock = WarehouseStock.objects.get(isbn=sku, location="ca")
        assert stock.quantity == 0  # Cannot go below 0

    def test_zero_initial_stock_stays_zero(self, auth_client):
        """Zero stock stays at zero after deduction."""
        sku = "9788901299002"
        order = _make_order(shopify_order_id=84002)
        _make_line_item(order, sku=sku, quantity=5, shopify_line_item_id=1)
        WarehouseStock.objects.create(isbn=sku, location="korea", quantity=0)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(한국)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")

        stock = WarehouseStock.objects.get(isbn=sku, location="korea")
        assert stock.quantity == 0


# ---------------------------------------------------------------------------
# REQ-PO5-005: LineItem.purchase_status set to "in_stock"
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadWarehouseSetsInStockStatus:
    """REQ-PO5-005: After warehouse upload, LineItems get purchase_status="in_stock"."""

    def test_sets_in_stock_status(self, auth_client):
        sku = "9788901299003"
        order = _make_order(shopify_order_id=85001)
        li = _make_line_item(order, sku=sku, quantity=2, shopify_line_item_id=1)
        WarehouseStock.objects.create(isbn=sku, location="ca", quantity=10)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(CA)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.purchase_status == "in_stock"

    def test_sets_in_stock_with_note(self, auth_client):
        """When note is provided, LineItem.note is also updated."""
        sku = "9788901299004"
        order = _make_order(shopify_order_id=85002)
        li = _make_line_item(order, sku=sku, quantity=1, shopify_line_item_id=2)
        WarehouseStock.objects.create(isbn=sku, location="korea", quantity=5)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(한국)", "note": "한국 창고에서 발송"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")

        li.refresh_from_db()
        assert li.purchase_status == "in_stock"
        assert li.note == "한국 창고에서 발송"


# ---------------------------------------------------------------------------
# REQ-PO5-006: No PurchaseOrder created for warehouse selection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadWarehouseNoPurchaseOrder:
    """REQ-PO5-006: Warehouse uploads do NOT create PurchaseOrder records."""

    def test_no_purchase_order_created(self, auth_client):
        sku = "9788901299005"
        order = _make_order(shopify_order_id=86001)
        _make_line_item(order, sku=sku, quantity=2, shopify_line_item_id=1)
        WarehouseStock.objects.create(isbn=sku, location="nj", quantity=10)

        po_count_before = PurchaseOrder.objects.count()

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(NJ)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        assert res.status_code == 201

        po_count_after = PurchaseOrder.objects.count()
        assert po_count_after == po_count_before  # No new PurchaseOrder

    def test_confirmed_count_incremented_for_warehouse(self, auth_client):
        """Warehouse entries increment confirmed_count."""
        sku = "9788901299006"
        order = _make_order(shopify_order_id=86002)
        _make_line_item(order, sku=sku, quantity=2, shopify_line_item_id=1)
        WarehouseStock.objects.create(isbn=sku, location="ca", quantity=10)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(CA)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        assert res.status_code == 201
        assert res.data["confirmed_count"] == 1


# ---------------------------------------------------------------------------
# REQ-PO5-007: Response includes confirmed_by_distributor
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadResponseConfirmedByDistributor:
    """REQ-PO5-007: Upload response includes confirmed_by_distributor breakdown."""

    def test_response_contains_confirmed_by_distributor_key(self, auth_client):
        """confirmed_by_distributor key must be present in response."""
        sku = "9788901299007"
        order = _make_order(shopify_order_id=87001)
        _make_line_item(order, sku=sku, quantity=2, shopify_line_item_id=1)
        WarehouseStock.objects.create(isbn=sku, location="ca", quantity=10)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(CA)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        assert res.status_code == 201
        assert "confirmed_by_distributor" in res.data

    def test_warehouse_entry_appears_in_confirmed_by_distributor(self, auth_client):
        """Warehouse SKU appears under its warehouse_* key."""
        sku = "9788901299008"
        order = _make_order(shopify_order_id=87002)
        _make_line_item(order, sku=sku, quantity=3, title="창고 도서", shopify_line_item_id=1)
        WarehouseStock.objects.create(isbn=sku, location="korea", quantity=10)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(한국)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        assert res.status_code == 201

        cbd = res.data["confirmed_by_distributor"]
        assert "warehouse_korea" in cbd
        entries = cbd["warehouse_korea"]
        assert len(entries) == 1
        assert entries[0]["sku"] == sku
        assert entries[0]["quantity"] == 3

    def test_non_warehouse_entry_appears_in_confirmed_by_distributor(self, auth_client):
        """Non-warehouse SKU (bookseen) appears under bookseen key."""
        sku = "9788901299009"
        order = _make_order(shopify_order_id=87003)
        _make_line_item(order, sku=sku, quantity=2, title="북센 도서", shopify_line_item_id=1)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "북센"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        assert res.status_code == 201

        cbd = res.data["confirmed_by_distributor"]
        assert "bookseen" in cbd
        assert len(cbd["bookseen"]) == 1
        assert cbd["bookseen"][0]["sku"] == sku

    def test_mixed_upload_groups_correctly(self, auth_client):
        """Mixed warehouse + regular upload groups all SKUs correctly."""
        sku_wh = "9788901299010"
        sku_bs = "9788901299011"

        order = _make_order(shopify_order_id=87004)
        _make_line_item(order, sku=sku_wh, quantity=2, shopify_line_item_id=1)
        _make_line_item(order, sku=sku_bs, quantity=1, shopify_line_item_id=2)
        WarehouseStock.objects.create(isbn=sku_wh, location="nj", quantity=10)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku_wh, "selected": "재고(NJ)"},
            {"isbn": sku_bs, "selected": "북센"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        assert res.status_code == 201

        cbd = res.data["confirmed_by_distributor"]
        assert "warehouse_nj" in cbd
        assert "bookseen" in cbd
        assert res.data["confirmed_count"] == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadWarehouseEdgeCases:
    """Edge cases for warehouse upload logic."""

    def test_warehouse_upload_no_existing_stock_record(self, auth_client):
        """If no WarehouseStock record exists, upload still processes LineItems (no error)."""
        sku = "9788901299020"
        order = _make_order(shopify_order_id=88001)
        li = _make_line_item(order, sku=sku, quantity=2, shopify_line_item_id=1)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(CA)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        # Should not error — no WarehouseStock means no update but LineItem still processed
        assert res.status_code == 201
        li.refresh_from_db()
        assert li.purchase_status == "in_stock"

    def test_warehouse_skipped_if_no_unordered_line_items(self, auth_client):
        """If no unordered LineItems for the SKU, warehouse entry is skipped."""
        sku = "9788901299021"
        WarehouseStock.objects.create(isbn=sku, location="ca", quantity=10)

        file_bytes = _make_daily_review_excel([
            {"isbn": sku, "selected": "재고(CA)"},
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res = auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")
        assert res.status_code == 201
        assert res.data["skipped_count"] == 1

        # Stock should not be touched
        stock = WarehouseStock.objects.get(isbn=sku, location="ca")
        assert stock.quantity == 10
