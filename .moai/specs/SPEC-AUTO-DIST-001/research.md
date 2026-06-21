# SPEC-AUTO-DIST-001 연구 노트 — 기존 코드 분석

## 대상 함수: `auto_select_distributor()` (excel_utils.py:311)

### 현재 구현 요약

```python
def auto_select_distributor(
    bookseen_available, bookseen_price, kyobo_available, kyobo_price
) -> str | None:
```

현재 로직은 4개 파라미터만 받는 단순 스텁:
1. 양사 모두 재고 있으면 → 가격 낮은 쪽 선택 (동가면 bookseen 기본)
2. 단독 재고 → 해당 업체 선택
3. 양사 모두 없으면 → None 반환

**문제점**:
- `bookseen_available` (bool)을 사용하지만 실제로는 `bookseen_stock >= total_qty` 비교가 필요
- DistributorVendorRule 우선 적용 없음
- WarehouseStock 재고 확인 없음
- `bookseen_price_comparison` 컬럼 미활용
- `candidate_basis` 레이블 없음
- `price_diff_alert` 없음

---

## VendorComparison 모델 현황 (models.py:194)

### 기존 필드

| 필드 | 타입 | 비고 |
|------|------|------|
| `sku` | CharField | unique |
| `bookseen_available` | BooleanField | null |
| `bookseen_price` | DecimalField | null |
| `bookseen_stock` | IntegerField | null |
| `bookseen_returnable` | BooleanField | null |
| `bookseen_status` | CharField | null |
| `bookseen_arrival` | CharField | null |
| `kyobo_available` | BooleanField | null |
| `kyobo_price` | DecimalField | null |
| `kyobo_stock` | IntegerField | null |
| `kyobo_returnable` | BooleanField | null |
| `kyobo_status` | CharField | null |
| `kyobo_publisher` | CharField | null |
| `kyobo_ordered_qty` | IntegerField | null |
| `kyobo_total_price` | DecimalField | null |
| `selected_distributor` | CharField | choices: bookseen/kyobo |

### 누락 필드 (이 SPEC에서 추가)

- `bookseen_price_comparison` — 북센 파일의 "가격비교" 컬럼 (TBD 인덱스)
- `candidate_basis` — 자동 선택 근거 레이블
- `price_diff` — 북센가 - 교보가
- `price_diff_alert` — 가격차이 임계값 초과 알림

### selected_distributor choices 문제

현재 choices는 `("bookseen", "북센")`, `("kyobo", "교보")` 두 가지뿐.
신규 로직이 반환하는 `"BOOXEN"`, `"재고"`, `"재고-서부확인"`, `"확인필요"`, `"agape"`, `"choeumgoyuk"` 값이 추가 필요.

---

## 호출 경로 분석 (purchase_order_views.py:262)

`UploadVendorFileView.post()` 내부에서 업로드 후 루프마다 호출:
```python
selected = auto_select_distributor(
    bookseen_available=vc.bookseen_available,
    bookseen_price=vc.bookseen_price,
    kyobo_available=vc.kyobo_available,
    kyobo_price=vc.kyobo_price,
)
if selected != vc.selected_distributor:
    vc.selected_distributor = selected
    vc.save(update_fields=["selected_distributor"])
```

신규 구현에서는 이 호출부가 다음을 추가로 전달해야 함:
- `total_qty` (LineItem 집계)
- `warehouse` (WarehouseStock 조회 결과)
- `vendor_rules` (DistributorVendorRule pre-fetch)
- 저장 시 `candidate_basis`, `price_diff`, `price_diff_alert` 추가

---

## 북센 파서 현황 (_parse_bookseen_xls, excel_utils.py:93)

현재 읽는 컬럼:
```
_BOOKSEEN_COL_TITLE = 1
_BOOKSEEN_COL_PRICE = 6
_BOOKSEEN_COL_STOCK = 7
_BOOKSEEN_COL_RETURNABLE = 10
_BOOKSEEN_COL_STATUS = 11
_BOOKSEEN_COL_ISBN = 14
_BOOKSEEN_COL_ARRIVAL = 15
```

"가격비교" 컬럼 인덱스가 불명확. 컬럼 8, 9, 12, 13 중 하나일 가능성이 높으나
실제 파일 확인 전에는 TBD 처리.

파서 반환 dict에 현재 없는 키:
- `price_comparison` → 신규 추가 필요

---

## DistributorVendorRule 모델 현황 (models.py:257)

```python
publisher_name = CharField(unique=True)
distributor = CharField(choices=[("choeumgoyuk", ...), ("agape", ...)])
```

아가페 매칭: `publisher_name`이 정확히 "아가페출판사" 등으로 저장되어 있을 수 있으므로
substring 매칭(`"아가페" in publisher_name`)이 안전. 단, DB 조회 방식과 Python 방식 중 구현 시 결정.

---

## 영향 범위 요약

| 파일 | 변경 유형 |
|------|-----------|
| `backend/order/excel_utils.py` | `auto_select_distributor()` 전면 교체, `_parse_bookseen_xls()` 수정, `_BOOKSEEN_COL_PRICE_COMPARISON` 상수 추가 |
| `backend/order/models.py` | `VendorComparison` 필드 4개 추가, `selected_distributor` choices 확장 |
| `backend/order/purchase_order_views.py` | `UploadVendorFileView` 호출 인터페이스 수정, `VendorComparisonView` 응답 필드 추가 |
| `backend/order/migrations/` | 신규 migration 파일 생성 |
| `backend/order/tests/` | 신규 단위 테스트 추가 |
