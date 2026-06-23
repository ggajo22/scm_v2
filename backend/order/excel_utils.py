"""
Excel generation and parsing utilities for purchase order workflows.

# @MX:ANCHOR: [AUTO] Public API for Excel I/O; called by generate-order-file and upload-vendor-file views
# @MX:REASON: High fan-in (2+ view callers) and external data format boundary
"""

import io
from decimal import Decimal

import openpyxl
import xlrd
from openpyxl import Workbook

# OLE2 Compound Document magic bytes — identifies legacy .xls (BIFF) format
_XLS_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"

# Bookseen result file (.xls): row 0 = timestamp, row 1 = headers (encoding-unreliable).
# Column positions confirmed from sample file analysis.
_BOOKSEEN_COL_TITLE = 1      # 도서명
_BOOKSEEN_COL_PRICE = 6      # 출고가 (단가)
_BOOKSEEN_COL_STOCK = 7      # 재고량
_BOOKSEEN_COL_RETURNABLE = 10  # 반품 ('가능'/'불가')
_BOOKSEEN_COL_STATUS = 11    # 상태 ('정상', '품절' 등)
_BOOKSEEN_COL_ISBN = 14      # ISBN
_BOOKSEEN_COL_ARRIVAL = 15   # 입고예정

# Kyobo result file (.xlsx): row 0 = "엑셀주문" (skip), row 1 = headers, row 2+ = data.
_KYOBO_COL_ISBN = 1          # ISBN
_KYOBO_COL_STATUS = 4        # 상품상태 ('정상', '품절' 등)
_KYOBO_COL_AVAILABLE = 5     # 출고여부 ('Y'/'N')
_KYOBO_COL_RETURNABLE = 6    # 반품가능여부 ('Y'/'N')
_KYOBO_COL_PUBLISHER = 8     # 출판사
_KYOBO_COL_QTY = 11          # 주문수량 (출고가 계산에 사용)
_KYOBO_COL_TOTAL_PRICE = 14  # 출고가합 (÷ 주문수량 = 단가)
_KYOBO_COL_STOCK = 15        # 보유재고


def generate_order_excel(skus_data: list[dict], distributor: str) -> bytes:
    """
    Generate an Excel (.xlsx) file for purchase order submission to a distributor.

    Args:
        skus_data: List of dicts with keys: sku (str), title (str), total_quantity (int).
        distributor: Distributor name (used only for context; not written to file).

    Returns:
        Raw bytes of the generated .xlsx file.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "발주서"

    if distributor == "bookseen":
        ws.append(["ISBN", "주문수량", "도서명", "출판사", "저자", "정가"])
        for row in skus_data:
            ws.append([row["sku"], row["total_quantity"], "", "", "", ""])
    elif distributor == "kyobo":
        ws.append(["ISBN", "수량"])
        for row in skus_data:
            ws.append([row["sku"], row["total_quantity"]])
    else:
        ws.append(["ISBN", "도서명", "수량"])
        for row in skus_data:
            ws.append([row["sku"], row["title"], row["total_quantity"]])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def parse_vendor_excel(file_bytes: bytes, distributor: str) -> list[dict]:
    """
    Parse a vendor-supplied Excel file into comparison records.

    Supports .xls (xlrd, bookseen) and .xlsx (openpyxl, kyobo), detected via magic bytes.

    Returns:
        List of dicts with keys:
          sku, available, price,
          stock, returnable, status,
          arrival (bookseen only)

    Raises:
        ValueError: If the file is empty or unreadable.
    """
    if file_bytes[:8] == _XLS_MAGIC:
        return _parse_bookseen_xls(file_bytes)
    if distributor == "kyobo":
        return _parse_kyobo_xlsx(file_bytes)
    return _parse_generic_xlsx(file_bytes)


def _parse_bookseen_xls(file_bytes: bytes) -> list[dict]:
    """
    Parse a Bookseen result .xls file.

    Structure: row 0 = timestamp/title, row 1 = headers (encoding unreliable),
    row 2+ = data. Column positions are fixed (confirmed from sample file).
    """
    try:
        wb = xlrd.open_workbook(file_contents=file_bytes)
    except Exception as exc:
        raise ValueError(f"Cannot read .xls file: {exc}") from exc

    ws = wb.sheet_by_index(0)
    if ws.nrows < 3:
        raise ValueError("Empty file")

    required_max_col = max(
        _BOOKSEEN_COL_ISBN,
        _BOOKSEEN_COL_PRICE,
        _BOOKSEEN_COL_STOCK,
        _BOOKSEEN_COL_RETURNABLE,
        _BOOKSEEN_COL_STATUS,
        _BOOKSEEN_COL_ARRIVAL,
    )

    results = []
    for row_num in range(2, ws.nrows):  # skip row 0 (timestamp) and row 1 (headers)
        row = ws.row_values(row_num)
        if len(row) <= required_max_col:
            continue

        raw_sku = row[_BOOKSEEN_COL_ISBN]
        if raw_sku is None or raw_sku == "":
            continue
        # xlrd reads numeric ISBN cells as float
        sku = str(int(raw_sku)) if isinstance(raw_sku, float) else str(raw_sku).strip()
        if not sku:
            continue

        raw_stock = row[_BOOKSEEN_COL_STOCK]
        stock: int | None = None
        try:
            stock = int(float(raw_stock)) if raw_stock not in (None, "") else None
        except (TypeError, ValueError):
            stock = None
        available = (stock is not None and stock > 0)

        raw_price = row[_BOOKSEEN_COL_PRICE]
        price: float | None = None
        try:
            price = float(raw_price) if raw_price not in (None, "") else None
        except (TypeError, ValueError):
            price = None

        # 반품: '가능' → True, anything else → False
        raw_returnable = row[_BOOKSEEN_COL_RETURNABLE]
        returnable = str(raw_returnable).strip() == "가능" if raw_returnable not in (None, "") else None

        raw_status = row[_BOOKSEEN_COL_STATUS]
        status = str(raw_status).strip() if raw_status not in (None, "") else None

        raw_arrival = row[_BOOKSEEN_COL_ARRIVAL]
        arrival = str(raw_arrival).strip() if raw_arrival not in (None, "") else None

        results.append({
            "sku": sku,
            "available": available,
            "price": price,
            "stock": stock,
            "returnable": returnable,
            "status": status,
            "publisher": None,
            "ordered_qty": None,
            "total_price": None,
            "arrival": arrival,
        })

    return results


def _parse_kyobo_xlsx(file_bytes: bytes) -> list[dict]:
    """
    Parse a Kyobo result .xlsx file.

    Structure: row 0 = "엑셀주문" (title, skip), row 1 = headers, row 2+ = data.
    Column positions are fixed (confirmed from sample file analysis).
    출고가 = 출고가합 (col 14) ÷ 주문수량 (col 11)
    """
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as exc:
        raise ValueError(f"Cannot read .xlsx file: {exc}") from exc

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 3:
        raise ValueError("Empty file")

    required_max_col = max(
        _KYOBO_COL_ISBN,
        _KYOBO_COL_STATUS,
        _KYOBO_COL_AVAILABLE,
        _KYOBO_COL_RETURNABLE,
        _KYOBO_COL_PUBLISHER,
        _KYOBO_COL_QTY,
        _KYOBO_COL_TOTAL_PRICE,
        _KYOBO_COL_STOCK,
    )

    results = []
    for row in rows[2:]:  # skip row 0 (title) and row 1 (headers)
        if len(row) <= required_max_col:
            continue

        raw_sku = row[_KYOBO_COL_ISBN]
        sku = str(raw_sku).strip() if raw_sku is not None else None
        if not sku or not sku.isdigit():
            continue

        # 출고여부 'Y' → available
        raw_available = row[_KYOBO_COL_AVAILABLE]
        available = str(raw_available).strip().upper() == "Y" if raw_available is not None else False

        # 출고가합 저장 + 출고가(단가) = 출고가합 / 주문수량
        raw_total = row[_KYOBO_COL_TOTAL_PRICE]
        raw_qty = row[_KYOBO_COL_QTY]
        total_price: float | None = None
        ordered_qty: int | None = None
        price: float | None = None
        try:
            total_price = float(raw_total) if raw_total not in (None, "") else None
            qty_f = float(raw_qty) if raw_qty not in (None, "") else None
            if qty_f is not None:
                ordered_qty = int(qty_f)
            if total_price is not None and qty_f and qty_f > 0:
                price = total_price / qty_f
        except (TypeError, ValueError):
            pass

        raw_stock = row[_KYOBO_COL_STOCK]
        stock: int | None = None
        try:
            stock = int(float(raw_stock)) if raw_stock not in (None, "") else None
        except (TypeError, ValueError):
            stock = None

        raw_returnable = row[_KYOBO_COL_RETURNABLE]
        returnable = str(raw_returnable).strip().upper() == "Y" if raw_returnable is not None else None

        raw_status = row[_KYOBO_COL_STATUS]
        status = str(raw_status).strip() if raw_status not in (None, "") else None

        raw_publisher = row[_KYOBO_COL_PUBLISHER]
        publisher = str(raw_publisher).strip() if raw_publisher not in (None, "") else None

        results.append({
            "sku": sku,
            "available": available,
            "price": price,
            "stock": stock,
            "returnable": returnable,
            "status": status,
            "publisher": publisher,
            "ordered_qty": ordered_qty,
            "total_price": total_price,
            "arrival": None,
        })

    return results


def _parse_generic_xlsx(file_bytes: bytes) -> list[dict]:
    """Fallback parser for unknown .xlsx distributors. Uses header-name detection."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as exc:
        raise ValueError(f"Cannot read .xlsx file: {exc}") from exc

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Empty file")

    header = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
    isbn_idx = next((i for i, h in enumerate(header) if "isbn" in h or "sku" in h), 0)
    avail_idx = next((i for i, h in enumerate(header) if "재고" in h or "available" in h), 1)
    price_idx = next((i for i, h in enumerate(header) if "단가" in h or "price" in h), 2)

    results = []
    for row in rows[1:]:
        max_idx = max(isbn_idx, avail_idx, price_idx)
        if len(row) <= max_idx:
            continue

        raw_sku = row[isbn_idx]
        sku = str(raw_sku).strip() if raw_sku is not None else None
        if not sku:
            continue

        raw_avail = row[avail_idx]
        available = bool(raw_avail) if raw_avail is not None else False

        raw_price = row[price_idx]
        price: float | None = None
        try:
            price = float(raw_price) if raw_price is not None else None
        except (TypeError, ValueError):
            price = None

        results.append({
            "sku": sku, "available": available, "price": price,
            "stock": None, "returnable": None, "status": None,
            "publisher": None, "ordered_qty": None, "total_price": None, "arrival": None,
        })

    return results


def _result(
    selected: str | None,
    basis: str,
    price_diff: Decimal | None,
    price_diff_alert: bool,
) -> dict:
    """Return a standardized auto_select_distributor result dict."""
    return {
        "selected_distributor": selected,
        "candidate_basis": basis,
        "price_diff": price_diff,
        "price_diff_alert": price_diff_alert,
    }


def _compare_both(
    bs_price: Decimal | None,
    ky_price: Decimal | None,
    bs_ret: bool | None,
    ky_ret: bool | None,
) -> tuple[str, str]:
    """
    Select distributor when both vendors have sufficient stock (Step 2-A).

    Returns (selected_distributor, candidate_basis).
    """
    if bs_price is not None and ky_price is not None:
        if bs_price < ky_price:
            return "bookseen", "양사재고/북센저가"
        if ky_price < bs_price:
            return "kyobo", "양사재고/교보저가"
        # Same price → check returnability
        if bs_ret is True and ky_ret is not True:
            return "bookseen", "양사재고/동가/북센반품"
        if ky_ret is True and bs_ret is not True:
            return "kyobo", "양사재고/동가/교보반품"
        return "bookseen", "양사재고/동가/반품동일"

    if bs_price is None and ky_price is not None:
        return "kyobo", "양사재고/교보가격만확인"
    if ky_price is None and bs_price is not None:
        return "bookseen", "양사재고/북센가격만확인"
    return "bookseen", "양사재고/가격없음"


def _no_stock_logic(
    bs_status: str,
    ky_status: str,
    bs_price: Decimal | None,
    ky_price: Decimal | None,
    bs_ret: bool | None,
    ky_ret: bool | None,
) -> tuple[str, str]:
    """
    Select distributor when neither vendor has sufficient stock (Step 2-D then 2-E).

    Returns (selected_distributor, candidate_basis).
    """
    basis = "양사재고없음"
    bs_cheaper = (
        bs_price is not None
        and ky_price is not None
        and bs_price <= ky_price
    )

    # Step 2-D: status/price heuristics
    if bs_status == "정상":
        if bs_cheaper:
            selected = "bookseen"
        else:
            selected = "kyobo" if ky_status == "정상" else "check_required"
    elif ky_status in ("정상", "주문판매"):
        selected = "kyobo"
    else:
        selected = "check_required"

    # Step 2-E: kyobo-returnable override
    if ky_ret is True and bs_ret is not True:
        if ky_status == "정상":
            selected = "kyobo"
        else:
            selected = "check_required"

    return selected, basis


def auto_select_distributor(
    vc: "VendorComparison",
    total_qty: int,
    korea_stock: int = 0,
    ca_stock: int = 0,
    nj_stock: int = 0,
    vendor_rules: list[tuple[str, str]] | None = None,
) -> dict:
    """
    Determine the best distributor for a VendorComparison record.

    Implements a 5-step decision tree:
      Step 0: DistributorVendorRule override (agape / choeumgoyuk)
      Step 1: Warehouse stock priority (korea / west)
      Step 2: Vendor comparison (stock, price, returnability, status)
      Step 3: Price diff alert calculation

    Args:
        vc: VendorComparison instance (unsaved OK — only reads field values).
        total_qty: Total quantity needed for this SKU.
        korea_stock: Korea warehouse stock quantity.
        ca_stock: CA warehouse stock quantity.
        nj_stock: NJ warehouse stock quantity.
        vendor_rules: Pre-fetched list of (publisher_name, distributor_code) tuples.

    Returns:
        dict with keys:
            selected_distributor: str code or None
            candidate_basis: str label describing the selection reason
            price_diff: Decimal (bookseen_price - kyobo_price) or None
            price_diff_alert: bool
    """
    # Lazy import to avoid circular dependency at module level
    # (VendorComparison is in models.py which imports nothing from excel_utils)
    bs_price: Decimal | None = vc.bookseen_price
    ky_price: Decimal | None = vc.kyobo_price
    price_diff: Decimal | None = (
        (bs_price - ky_price)
        if (bs_price is not None and ky_price is not None)
        else None
    )

    # ------------------------------------------------------------------
    # Step 0: DistributorVendorRule override
    # ------------------------------------------------------------------
    if vendor_rules and vc.kyobo_publisher:
        for pub_name, dist_code in vendor_rules:
            if dist_code == "agape" and "아가페" in vc.kyobo_publisher:
                return _result("agape", "아가페규칙", price_diff, False)
            if dist_code == "choeumgoyuk" and vc.kyobo_publisher == pub_name:
                return _result("choeumgoyuk", "처음교육규칙", price_diff, False)
            if dist_code == "sungseoyunion" and vc.kyobo_publisher == pub_name:
                return _result("sungseoyunion", "성서유니온규칙", price_diff, False)

    # ------------------------------------------------------------------
    # Step 1: Warehouse stock priority
    # ------------------------------------------------------------------
    if korea_stock >= total_qty:
        return _result("warehouse", "재고우선", price_diff, False)
    if ca_stock >= total_qty or nj_stock >= total_qty:
        return _result("warehouse_west", "서부창고확인", price_diff, False)

    # ------------------------------------------------------------------
    # Step 2: Vendor comparison
    # ------------------------------------------------------------------
    bs_stock: int = vc.bookseen_stock or 0
    ky_stock: int = vc.kyobo_stock or 0
    bs_ret: bool | None = vc.bookseen_returnable
    ky_ret: bool | None = vc.kyobo_returnable
    bs_status: str = vc.bookseen_status or ""
    ky_status: str = vc.kyobo_status or ""

    bs_enough = bs_stock >= total_qty
    ky_enough = ky_stock >= total_qty

    if bs_enough and ky_enough:
        selected, basis = _compare_both(bs_price, ky_price, bs_ret, ky_ret)
    elif bs_enough and not ky_enough:
        selected, basis = "bookseen", "북센재고우선"
    elif ky_enough and not bs_enough:
        selected, basis = "kyobo", "교보재고우선"
    else:
        selected, basis = _no_stock_logic(
            bs_status, ky_status, bs_price, ky_price, bs_ret, ky_ret
        )

    # ------------------------------------------------------------------
    # Step 3: Price diff alert
    # ------------------------------------------------------------------
    price_diff_alert = False
    if price_diff is not None and abs(price_diff) >= 3000:
        if (
            selected == "check_required"
            or (selected == "bookseen" and bs_price is not None and ky_price is not None and bs_price > ky_price)
            or (selected == "kyobo" and ky_price is not None and bs_price is not None and ky_price > bs_price)
        ):
            price_diff_alert = True

    return _result(selected, basis, price_diff, price_diff_alert)


# Distributor display name ↔ internal code mappings
_DISTRIBUTOR_LABEL_MAP: dict[str, str] = {
    "북센": "bookseen",
    "교보": "kyobo",
    "처음교육": "choeumgoyuk",
    "아가페": "agape",
    "성서유니온": "sungseoyunion",
}

_DAILY_REVIEW_HEADERS = [
    "주문번호", "ISBN", "제목", "수량", "주문위치", "메모",
    "창고재고수량", "창고재고위치",
    "북센 공급가", "교보 공급가",
    "북센 재고수량", "북센 재고상태",
    "교보 재고수량", "교보 재고상태",
    "공급가차이",
    "북센 입고예정", "북센 반품가능여부",
    "교보 출고여부", "교보 반품가능여부",
    "가격차이알림",
    "출판사", "선택근거", "선택",
]


def generate_daily_review_excel(rows: list[dict]) -> bytes:
    """
    Generate Daily Order Review Excel with 22 columns.

    Each dict in `rows` should have:
        order_name, sku, title, quantity, location, note,
        warehouse_qty (int|None), warehouse_locations (str),
        bs_price (float|None), ky_price (float|None),
        bs_status (str|None), ky_stock (int|None), ky_status (str|None),
        price_diff (float|None), bs_arrival (str|None),
        bs_returnable (bool|None), ky_available (bool|None), ky_returnable (bool|None),
        price_diff_alert (bool), candidate_basis (str|None), selected (str)
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Order Review"
    ws.append(_DAILY_REVIEW_HEADERS)

    for row in rows:
        bs_returnable = "Y" if row.get("bs_returnable") is True else ("N" if row.get("bs_returnable") is False else "")
        ky_returnable = "Y" if row.get("ky_returnable") is True else ("N" if row.get("ky_returnable") is False else "")
        ky_available = "Y" if row.get("ky_available") is True else ("N" if row.get("ky_available") is False else "")
        price_diff_alert = "Y" if row.get("price_diff_alert") else "N"
        wh_qty = row.get("warehouse_qty")

        ws.append([
            row.get("order_name") or "",
            row.get("sku") or "",
            row.get("title") or "",
            row.get("quantity") or 0,
            row.get("location") or "",
            row.get("note") or "",
            wh_qty if wh_qty is not None else "",
            row.get("warehouse_locations") or "",
            row.get("bs_price") if row.get("bs_price") is not None else "",
            row.get("ky_price") if row.get("ky_price") is not None else "",
            "",  # 북센 재고수량 — no reliable data
            row.get("bs_status") or "",
            row.get("ky_stock") if row.get("ky_stock") is not None else "",
            row.get("ky_status") or "",
            row.get("price_diff") if row.get("price_diff") is not None else "",
            row.get("bs_arrival") or "",
            bs_returnable,
            ky_available,
            ky_returnable,
            price_diff_alert,
            row.get("publisher") or "",
            row.get("candidate_basis") or "",
            row.get("selected") or "",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def parse_daily_review_excel(file_bytes: bytes) -> list[dict]:
    """
    Parse an uploaded Daily Review Excel file.

    Reads the '선택' column (Korean display name) and 'ISBN' column.
    Skips rows where '선택' is empty or maps to an unknown distributor.

    Returns:
        List of dicts: {sku: str, distributor: str, note: str|None}
        distributor is the internal code (bookseen, kyobo, choeumgoyuk, agape).

    Raises:
        ValueError: If file is unreadable or missing required columns.
    """
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as exc:
        raise ValueError(f"Cannot read Excel file: {exc}") from exc

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise ValueError("파일이 비어 있습니다.")

    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    if "ISBN" not in header or "선택" not in header:
        raise ValueError("올바른 Daily Review 형식의 파일이 아닙니다 (ISBN, 선택 컬럼 필요).")

    sku_idx = header.index("ISBN")
    selected_idx = header.index("선택")
    note_idx = header.index("메모") if "메모" in header else None

    results = []
    for row in rows[1:]:
        if len(row) <= max(sku_idx, selected_idx):
            continue

        raw_sku = row[sku_idx]
        sku = str(raw_sku).strip() if raw_sku is not None else ""
        if not sku:
            continue

        raw_selected = row[selected_idx]
        selected_label = str(raw_selected).strip() if raw_selected is not None else ""
        if not selected_label:
            continue

        distributor_code = _DISTRIBUTOR_LABEL_MAP.get(selected_label)
        if not distributor_code:
            continue  # Unknown label — skip silently

        note: str | None = None
        if note_idx is not None and len(row) > note_idx:
            raw_note = row[note_idx]
            if raw_note is not None:
                note = str(raw_note).strip() or None

        results.append({"sku": sku, "distributor": distributor_code, "note": note})

    return results
