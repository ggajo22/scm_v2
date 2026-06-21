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
        if not sku:
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


def auto_select_distributor(
    bookseen_available: bool | None,
    bookseen_price: Decimal | None,
    kyobo_available: bool | None,
    kyobo_price: Decimal | None,
) -> str | None:
    """
    Auto-select the best distributor based on availability and price.

    Priority:
      1. Availability: prefer any available distributor over an unavailable one.
      2. Price (tie-break): prefer the lower price when both are available.
      3. Default to bookseen when both available but prices are missing.

    Returns:
        "bookseen", "kyobo", or None when neither is available.
    """
    bs_ok = bool(bookseen_available)
    ky_ok = bool(kyobo_available)

    if bs_ok and ky_ok:
        if bookseen_price is not None and kyobo_price is not None:
            return "bookseen" if float(bookseen_price) <= float(kyobo_price) else "kyobo"
        return "bookseen"  # Default when prices are missing

    if bs_ok:
        return "bookseen"
    if ky_ok:
        return "kyobo"
    return None
