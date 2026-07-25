---
id: SPEC-PURCHASE-ORDER-007
version: 1.0.0
status: planned
created: 2026-07-25
updated: 2026-07-25
author: ggajo
priority: Medium
issue_number: ~
---

# YES24 발주 파일 생성 지원 (미발주 현황 탭, 4번째 발주처)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-07-25 | ggajo | 최초 작성 |

---

## 문제 정의

현재 미발주 현황(`UnorderedItemsTab`) 탭은 `GenerateOrderFileView`(`POST /api/purchase-orders/generate-order-file/`)를 통해 북센(booxen)·교보(kyobo) 2개 발주처의 발주 요청 Excel 파일을 생성할 수 있다. `generate_order_excel()`은 `distributor` 값에 따라 컬럼 구성이 다른 분기를 갖고 있으며, `VALID_DISTRIBUTORS` 집합에 booxen/kyobo를 포함한 8개 값이 등록되어 있으나 yes24는 포함되어 있지 않다.

YES24는 SPEC-PURCHASE-ORDER-006에서 벤더 "결과파일" 업로드(참고용 조회) 기능은 이미 지원되지만, 그 SPEC은 명시적으로 "발주서 생성" 기능을 제외 범위로 두었다. 관리자가 YES24향 발주를 넣을 때도 북센과 동일하게 미발주 현황 탭에서 선택한 SKU들의 발주 요청 파일을 바로 생성·다운로드할 수 있어야 하며, YES24가 요구하는 `번호, 도서명, ISBN, 출판사, 정가, 수량` 컬럼 구성과 ISBN·수량만 채우는 입력 규칙을 따라야 한다.

이 SPEC은 SPEC-PURCHASE-ORDER-006(YES24 결과파일 업로드/파싱/저장)과는 별개의, SPEC-006이 명시적으로 제외했던 "YES24 발주서 생성" 기능을 다루는 독립적인 SPEC이다. `Yes24Data` 모델, `_parse_yes24_xlsx` 파서, `VENDOR_FILE_DISTRIBUTORS`, `UploadVendorFileView`는 이 SPEC의 대상이 아니다.

---

## 솔루션 개요

- `backend/order/excel_utils.py`의 `generate_order_excel()`에 `elif distributor == "yes24":` 분기 추가 — 헤더 `번호, 도서명, ISBN, 출판사, 정가, 수량`, 각 데이터 행은 ISBN(`row["sku"]`)과 수량(`row["total_quantity"]`)만 채우고 번호/도서명/출판사/정가는 빈 문자열로 둔다 (북센 분기와 동일한 "일부 컬럼만 채움" 패턴)
- `backend/order/purchase_order_views.py`의 `VALID_DISTRIBUTORS`에 `"yes24"` 추가 — `GenerateOrderFileView`가 이미 `distributor`를 이 집합으로 검증하고 `generate_order_excel(skus_data, distributor)`를 범용 호출하므로, 이 한 줄 추가만으로 뷰가 yes24를 수용한다
- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`의 `distributorLabel`에 `yes24: 'YES24'` 추가, 북센/교보 버튼과 동일한 구조의 "YES24 발주 파일 생성" 버튼 신규 추가
- 백엔드 테스트: `TestGenerateOrderExcel`에 `test_yes24_column_format` 추가, `TestGenerateOrderFileView`에 yes24 발주처 수용 테스트 추가
- 프론트엔드 테스트: 버튼 자체는 표시/래핑 로직만 있는 저복잡도 변경이므로 신규 최소 테스트 파일 작성 여부는 구현 시점에 판단 (아래 REQ-PO7-006 참조)

---

## 범위

### 포함

- `backend/order/excel_utils.py`: `generate_order_excel()`에 `distributor == "yes24"` 분기 추가
- `backend/order/purchase_order_views.py`: `VALID_DISTRIBUTORS`에 `"yes24"` 추가
- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`: `distributorLabel`에 yes24 추가, "YES24 발주 파일 생성" 버튼 추가
- `backend/order/tests/test_purchase_orders.py`: `TestGenerateOrderExcel`/`TestGenerateOrderFileView`에 YES24 테스트 케이스 추가
- 프론트엔드 테스트 커버리지 여부 판단 및 문서화 (필요 시 신규 테스트 파일 작성)

### 제외

- `backend/order/models.py`의 `Yes24Data` 모델, `backend/order/excel_utils.py`의 `_parse_yes24_xlsx` 파서, `VENDOR_FILE_DISTRIBUTORS`, `UploadVendorFileView` — 이들은 SPEC-PURCHASE-ORDER-006에서 이미 구현·완료된 "결과파일 업로드" 기능이며 이 SPEC과 무관하다
- `generate_order_excel()`의 일반/fallback `else` 분기(choeumgoyuk, agape, sungseoyunion, warehouse_* 등 다른 발주처가 사용) 변경
- `auto_select_distributor()`, `VendorComparison` 모델, `DISTRIBUTOR_CHOICES`에 yes24 통합
- `DailyReviewTab.tsx` 및 Daily Review 업로드/다운로드 로직 변경
- 번호/도서명/출판사/정가 컬럼에 실제 값을 채우는 로직 — 북센 패턴과 동일하게 ISBN과 수량만 채우고 나머지는 빈칸으로 둔다 (사용자가 명시적으로 확인한 요구사항)

---

## 요구사항

### REQ-PO7-001 — generate_order_excel()에 YES24 분기 추가

When `generate_order_excel(skus_data, distributor)`가 `distributor="yes24"`로 호출될 때, the system shall 헤더 행 `["번호", "도서명", "ISBN", "출판사", "정가", "수량"]`을 작성하고, `skus_data`의 각 항목에 대해 `["", "", row["sku"], "", "", row["total_quantity"]]` 형태의 데이터 행을 추가해야 한다.

- 대상 파일: `backend/order/excel_utils.py` (`generate_order_excel()` 함수, 기존 61-72번째 줄 부근)
- 분기 추가 위치: 기존 `elif distributor == "kyobo":` 분기(65-68번째 줄) 다음, 범용 `else` fallback(69-72번째 줄) 이전
- 컬럼 순서는 정확히 `번호, 도서명, ISBN, 출판사, 정가, 수량`이어야 하며 임의로 순서를 바꾸지 않는다
- ISBN(3번째 컬럼, index 2)에는 `row["sku"]`, 수량(6번째 컬럼, index 5)에는 `row["total_quantity"]`만 채우고 번호/도서명/출판사/정가(index 0, 1, 3, 4)는 빈 문자열(`""`)로 둔다
- 기존 booxen/kyobo/일반 fallback 분기의 동작은 변경하지 않는다

---

### REQ-PO7-002 — VALID_DISTRIBUTORS에 yes24 추가

The system shall `backend/order/purchase_order_views.py`의 `VALID_DISTRIBUTORS` 집합에 `"yes24"`를 포함해야 한다.

- 대상 파일: `backend/order/purchase_order_views.py` (56번째 줄 부근, 기존 `{"booxen", "kyobo", "choeumgoyuk", "agape", "sungseoyunion", "warehouse_korea", "warehouse_ca", "warehouse_nj"}`)
- `GenerateOrderFileView.post()`의 유효성 검사(185번째 줄 부근, `distributor not in VALID_DISTRIBUTORS` → 400)가 `"yes24"`를 유효한 값으로 허용해야 한다
- `VENDOR_FILE_DISTRIBUTORS`(SPEC-006, 업로드용)는 이 SPEC과 무관하며 변경하지 않는다
- `GenerateOrderFileView.post()`의 나머지 로직(SKU 집계, 미발주 LineItem 필터링, `generate_order_excel()` 호출, 파일명 생성)은 이미 `distributor` 문자열에 대해 범용적으로 동작하므로 추가 수정이 필요 없다

---

### REQ-PO7-003 — 프론트엔드 distributorLabel에 yes24 추가

The system shall `UnorderedItemsTab.tsx`의 `distributorLabel` 맵에 `yes24: 'YES24'`를 추가해야 한다.

- 대상 파일: `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` (84번째 줄 부근, 기존 `{ booxen: '북센', kyobo: '교보' }`)
- 변경 후: `{ booxen: '북센', kyobo: '교보', yes24: 'YES24' }`
- `handleGenerateFile()`(86-102번째 줄)은 이미 `distributor` 문자열과 `distributorLabel` 조회로 범용 동작하므로 추가 수정이 필요 없다 (다운로드 파일명, 성공/경고 토스트 문구 모두 자동으로 "YES24"를 사용)

---

### REQ-PO7-004 — 프론트엔드 YES24 발주 파일 생성 버튼 추가

The system shall 미발주 현황 탭의 액션 버튼 영역에 "YES24 발주 파일 생성" 버튼을 북센·교보 버튼과 동일한 구조로 추가해야 한다.

- 대상 파일: `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` (144-164번째 줄 부근, 기존 북센/교보 `<Button>` 두 개 다음)
- 버튼 속성: `size="sm" variant="outline" disabled={selectedSkus.length === 0 || loadingDistributor === 'yes24'} onClick={() => handleGenerateFile('yes24')} className="gap-2"`
- 버튼 내용: `<Download className="h-4 w-4" aria-hidden="true" />` + `{loadingDistributor === 'yes24' ? '생성 중...' : 'YES24 발주 파일 생성'}`
- 버튼 위치: 교보 버튼 바로 다음 (북센 → 교보 → YES24 순서)

---

### REQ-PO7-005 — YES24 컬럼 포맷 단위 테스트

The system shall `backend/order/tests/test_purchase_orders.py`의 `TestGenerateOrderExcel` 클래스에 `test_yes24_column_format` 테스트를 추가해야 한다 (기존 `test_booxen_column_format`/`test_kyobo_column_format`과 동일한 패턴).

- SKU 데이터 dict(`{"sku": ..., "title": ..., "total_quantity": ...}`)로 `generate_order_excel(data, "yes24")`를 호출
- openpyxl로 반환된 바이트를 로드하여 `rows[0] == ("번호", "도서명", "ISBN", "출판사", "정가", "수량")` 검증
- `rows[1]`에서 index 2(ISBN)가 SKU 값과, index 5(수량)가 `total_quantity` 값과 일치함을 검증
- `rows[1]`의 index 0, 1, 3, 4(번호/도서명/출판사/정가)가 모두 빈 문자열임을 검증

---

### REQ-PO7-006 — GenerateOrderFileView의 YES24 수용 통합 테스트

The system shall `backend/order/tests/test_purchase_orders.py`의 `TestGenerateOrderFileView` 클래스에 yes24 발주처 수용 테스트를 추가해야 한다 (기존 `test_returns_excel_for_valid_skus`/`test_filename_contains_distributor_and_date` 패턴을 따름).

- 미발주 LineItem SKU를 준비한 뒤 `{"distributor": "yes24", "skus": [sku]}`로 `POST /api/purchase-orders/generate-order-file/` 요청
- 200 응답과 `EXCEL_CONTENT_TYPE` Content-Type을 검증
- 반환된 Excel의 `rows[0]`이 YES24 헤더(`("번호", "도서명", "ISBN", "출판사", "정가", "수량")`)와 일치하고, `rows[1]`의 ISBN/수량 컬럼이 올바른 값을 갖는지 검증
- `Content-Disposition` 헤더에 `"yes24"`가 포함되는지 검증 (기존 `test_filename_contains_distributor_and_date` 패턴)

---

### REQ-PO7-007 — 프론트엔드 버튼 테스트 커버리지 판단 (Optional)

Where 프론트엔드에서 `UnorderedItemsTab.tsx`에 대한 기존 테스트 파일이 존재하지 않는 경우, the system shall 구현 시점에 신규 최소 테스트 파일(`UnorderedItemsTab.test.tsx`) 작성 여부를 판단하고 그 근거를 커밋 메시지 또는 PR 설명에 문서화해야 한다.

- 판단 기준: 이 변경은 표시/배선(wiring) 전용이며 `handleGenerateFile()`은 이미 북센/교보로 검증된 범용 함수이므로, 신규 로직 없이 라벨/버튼 추가만 이루어짐 — SPEC-006의 업로드 플로우(`VendorFileUploadTab.test.tsx`)처럼 새로운 상태 전이나 API 분기 로직이 없다는 점에서 상대적으로 낮은 복잡도
- 테스트를 작성하지 않기로 결정할 경우, 수동 QA로 검증(드롭다운이 아닌 버튼 클릭 시 `distributor=yes24`로 API가 호출되는지)했음을 남긴다
- 테스트를 작성하기로 결정할 경우, 최소 1개 케이스(버튼 렌더링 + 클릭 시 `handleGenerateFile('yes24')` 호출 검증)로 충분하다

---

### REQ-PO7-008 — 기존 발주처 및 SPEC-006 기능 무변경 보장 (Unwanted Behavior)

If YES24 발주 파일 생성 기능이 구현되면, then the system shall NOT `_parse_yes24_xlsx`, `Yes24Data` 모델, `VENDOR_FILE_DISTRIBUTORS`, `UploadVendorFileView`, `generate_order_excel()`의 일반 fallback `else` 분기(choeumgoyuk/agape/sungseoyunion/warehouse_* 등), `auto_select_distributor()`, `VendorComparison` 모델, `DailyReviewTab.tsx`를 수정해야 한다.

- 기존 booxen/kyobo 컬럼 포맷 테스트(`test_booxen_column_format`, `test_kyobo_column_format`)는 변경 없이 그대로 통과해야 한다
- SPEC-PURCHASE-ORDER-006의 YES24 업로드 관련 테스트(`TestParseVendorExcel`, `TestUploadVendorFileView`의 yes24 케이스)는 변경 없이 그대로 통과해야 한다
- `test_auto_dist.py`의 기존 테스트는 변경 없이 그대로 통과해야 한다

---

## 구현 범위 (수정·생성 대상 파일)

| 파일 | 변경 유형 | 변경 내용 요약 |
|------|-----------|----------------|
| `backend/order/excel_utils.py` | 수정 | `generate_order_excel()`에 `distributor == "yes24"` 분기 추가 (헤더 6컬럼 + ISBN/수량만 채움) |
| `backend/order/purchase_order_views.py` | 수정 | `VALID_DISTRIBUTORS`에 `"yes24"` 추가 |
| `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` | 수정 | `distributorLabel`에 yes24 추가, "YES24 발주 파일 생성" 버튼 추가 |
| `backend/order/tests/test_purchase_orders.py` | 수정 | `TestGenerateOrderExcel`에 `test_yes24_column_format` 추가, `TestGenerateOrderFileView`에 yes24 수용 테스트 추가 |
| `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx` | 생성 (조건부) | REQ-PO7-007 판단 결과에 따라 신규 작성 여부 결정 |

---

## 제외 범위 (What NOT to Build)

- `backend/order/models.py`의 `Yes24Data` 모델 변경 — SPEC-PURCHASE-ORDER-006에서 이미 구현 완료, 이 SPEC과 무관
- `backend/order/excel_utils.py`의 `_parse_yes24_xlsx` 파서 및 `parse_vendor_excel()` dispatch 변경 — SPEC-006 영역, 결과파일 업로드용이며 발주서 생성과 무관
- `VENDOR_FILE_DISTRIBUTORS`, `UploadVendorFileView` 변경 — SPEC-006에서 이미 구현 완료
- `generate_order_excel()`의 일반 fallback `else` 분기(choeumgoyuk/agape/sungseoyunion/warehouse_* 등 다른 발주처) 컬럼 구성 변경
- `auto_select_distributor()`, `VendorComparison` 모델, `DISTRIBUTOR_CHOICES`에 yes24 통합
- `DailyReviewTab.tsx` 및 Daily Review 업로드/다운로드 로직 변경
- 번호/도서명/출판사/정가 컬럼에 실제 데이터를 채우는 로직 — 북센과 동일하게 ISBN·수량만 채우고 나머지는 빈칸으로 유지 (사용자 명시 요구사항)

---

## 인수 조건

### AC-001 — YES24 헤더 및 컬럼 순서 정확성

**Given** `skus_data = [{"sku": "8809226729403", "title": "테스트 도서", "total_quantity": 5}]`일 때
**When** `generate_order_excel(skus_data, "yes24")`를 호출하면
**Then** 반환된 Excel의 첫 번째 행(헤더)이 정확히 `("번호", "도서명", "ISBN", "출판사", "정가", "수량")`이어야 한다

---

### AC-002 — ISBN과 수량만 채워지고 나머지 컬럼은 빈칸

**Given** AC-001과 동일한 `skus_data`일 때
**When** `generate_order_excel(skus_data, "yes24")`를 호출하면
**Then** 두 번째 행(데이터 행)에서 ISBN 컬럼(index 2)이 `"8809226729403"`, 수량 컬럼(index 5)이 `5`이어야 하고, 번호/도서명/출판사/정가 컬럼(index 0, 1, 3, 4)은 모두 빈 문자열이어야 한다

---

### AC-003 — GenerateOrderFileView가 yes24 발주처를 유효한 값으로 수용

**Given** 미발주 상태의 LineItem(SKU `"8809226729403"`, 수량 5)이 존재할 때
**When** 인증된 관리자가 `POST /api/purchase-orders/generate-order-file/`에 `{"distributor": "yes24", "skus": ["8809226729403"]}`를 전송하면
**Then** 200 응답과 함께 YES24 컬럼 포맷의 Excel 바이너리가 반환되어야 하고, `Content-Disposition` 헤더에 `"yes24"`가 포함되어야 한다

---

### AC-004 — 프론트엔드 YES24 버튼 표시 및 클릭 동작

**Given** `UnorderedItemsTab`이 렌더링되고 SKU가 1개 이상 선택된 상태일 때
**When** 화면을 확인하면
**Then** "북센 발주 파일 생성", "교보 발주 파일 생성" 버튼 다음에 "YES24 발주 파일 생성" 버튼이 표시되어야 하며, 클릭 시 `handleGenerateFile('yes24')`가 호출되어 `distributor=yes24`로 API가 요청되어야 한다

---

### AC-005 — 기존 북센/교보/기타 발주처 회귀 검증

**Given** YES24 발주 파일 생성 기능이 구현된 상태일 때
**When** `backend/order/tests/test_purchase_orders.py`의 기존 `test_booxen_column_format`, `test_kyobo_column_format`, `TestGenerateOrderFileView`의 기존 테스트 및 `test_auto_dist.py` 전체를 실행하면
**Then** 모두 기존과 동일하게 통과해야 하며 YES24 관련 코드 변경으로 인한 회귀가 없어야 한다

---

### AC-006 — SPEC-006 YES24 업로드 기능 무영향 회귀 검증

**Given** YES24 발주 파일 생성 기능이 구현된 상태일 때
**When** SPEC-PURCHASE-ORDER-006에서 추가된 `TestParseVendorExcel`, `TestUploadVendorFileView`의 yes24 관련 테스트를 실행하면
**Then** 모두 기존과 동일하게 통과해야 하며 `Yes24Data`/`_parse_yes24_xlsx`/`UploadVendorFileView`에 대한 코드 변경이 없어야 한다

---

### AC-007 — 잘못된 distributor 값은 여전히 400 반환

**Given** `distributor="invalid_dist"`로 발주 파일 생성 요청을 보낼 때
**When** `GenerateOrderFileView.post()`가 처리되면
**Then** 기존과 동일하게 400 응답이 반환되어야 한다 (yes24 추가가 다른 유효성 검사에 영향을 주지 않음을 검증)

---

## 관련 SPEC

- SPEC-PURCHASE-ORDER-006: YES24 벤더 결과파일 업로드 지원 — 이 SPEC이 사용하는 `distributor="yes24"` 문자열 값과 동일한 발주처를 가리키지만, 코드 경로(업로드/파싱/저장 vs 발주서 생성)는 완전히 분리되어 있다. SPEC-006이 명시적으로 제외했던 "발주서 생성" 범위를 이 SPEC-007이 다룬다.
