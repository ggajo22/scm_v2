---
id: SPEC-PURCHASE-ORDER-006
version: 1.0.0
status: draft
created: 2026-07-25
updated: 2026-07-25
author: ggajo
priority: Medium
issue_number: ~
---

# YES24 벤더 결과파일 업로드 지원 (참고용, 3번째 벤더)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-07-25 | ggajo | 최초 작성 |

---

## 문제 정의

현재 `UploadVendorFileView`(`POST /api/purchase-orders/upload-vendor-file/`)는 북센(booxen)과 교보(kyobo) 2개 벤더의 결과 Excel 파일만 업로드·파싱·저장할 수 있다. `VENDOR_FILE_DISTRIBUTORS = {"booxen", "kyobo"}`로 하드코딩되어 있어 YES24 결과파일은 업로드할 수 없다.

YES24는 도서 발주 프로세스에서 사용하는 세 번째 벤더이며, 발주 후 `20260725_YES24_결과.xlsx`와 같은 결과 파일을 제공한다. 이 파일은 booxen/kyobo와 달리 정상적인 헤더 행(row 0)을 가지고 있고, ISBN·정가·공급가·유통상태 컬럼을 포함하지만 재고수량·반품가능여부 컬럼은 없다.

관리자가 YES24 결과 데이터를 시스템에 참고용으로 저장할 방법이 없어, 북센/교보와 동일한 업로드 UX로 YES24 데이터를 조회·보관할 수 있어야 한다.

---

## 솔루션 개요

- `backend/order/models.py`에 `Yes24Data` 모델 신규 추가 (sku 유니크 키, `price`/`list_price`/`status`/`updated_at` 필드) + 마이그레이션 파일 생성
- `backend/order/excel_utils.py`에 `_parse_yes24_xlsx` 파서 신규 추가 (헤더 기반 컬럼 매핑, row 0 헤더만 스킵 — booxen/kyobo와 달리 타이틀 행 없음)
- `parse_vendor_excel()` dispatch에 `distributor == "yes24"` 분기 추가
- `backend/order/purchase_order_views.py`의 `VENDOR_FILE_DISTRIBUTORS`에 `"yes24"` 추가
- `UploadVendorFileView.post()`에 `Yes24Data` 업서트 3번째 분기 추가 (기존 booxen/else-kyobo 2분기 → booxen/yes24/kyobo 3분기)
- `frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.tsx`의 `DISTRIBUTOR_OPTIONS`/`DISTRIBUTOR_API_KEY`에 YES24 추가, 안내 문구 업데이트
- 파서 단위 테스트 + 업로드 API 통합 테스트 추가 (`backend/order/tests/test_purchase_orders.py` 기존 클래스 확장)

---

## 범위

### 포함

- `backend/order/models.py`: `Yes24Data` 모델 정의
- `backend/order/migrations/`: `Yes24Data` 테이블 생성 마이그레이션 (`orders_yes24data`)
- `backend/order/excel_utils.py`: `_parse_yes24_xlsx` 함수 추가, `parse_vendor_excel()` dispatch 갱신
- `backend/order/purchase_order_views.py`: `VENDOR_FILE_DISTRIBUTORS` 확장, `UploadVendorFileView.post()` 3번째 업서트 분기
- `frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.tsx`: 발주처 옵션 및 안내 문구 갱신
- `backend/order/tests/test_purchase_orders.py`: 파서 단위 테스트(`TestParseVendorExcel` 확장) + API 통합 테스트(`TestUploadVendorFileView` 확장)

### 제외

- `auto_select_distributor()` 및 `VendorComparison` 모델/`DISTRIBUTOR_CHOICES`에 YES24 통합 — booxen/kyobo 2자 비교 로직은 변경하지 않는다 (`backend/order/tests/test_auto_dist.py` 무변경)
- `generate_order_excel()`에 YES24 발주서(발주 파일) 생성 브랜치 추가 — 이 SPEC은 업로드/파싱/저장 전용이며 `GenerateOrderFileView`/`VALID_DISTRIBUTORS`는 건드리지 않는다
- `DailyReviewTab.tsx` 및 Daily Review 업로드/다운로드 로직 변경
- YES24 원본 컬럼 중 도서명, 출판사, 저자, 출간일, 주문수량, 부가코드, 분야명, 중복여부, 공급률의 DB 영속화 — ISBN(sku), 정가(list_price), 공급가(price), 유통상태(status) 4개 필드만 저장한다
- `available`, `stock`, `returnable`, `arrival`, `publisher`, `ordered_qty`, `total_price` 필드를 `Yes24Data` 모델에 추가하는 것 — YES24 원본 파일에 대응 데이터가 없다

---

## 요구사항

### REQ-PO6-001 — Yes24Data 모델 및 마이그레이션 추가

The system shall provide a `Yes24Data` model in `backend/order/models.py`, keyed by unique `sku`, with fields `price` (공급가, `DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)`), `list_price` (정가, `DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)`), `status` (유통상태, `CharField(max_length=50, null=True, blank=True)`), and `updated_at` (`DateTimeField(auto_now=True)`).

- 대상 파일: `backend/order/models.py`
- `Meta.db_table = "orders_yes24data"`, `indexes = [models.Index(fields=["sku"])]` — `BooxenData`/`KyoboData`와 동일 패턴(`orders_{vendor}data`)
- 신규 마이그레이션 파일 필요 (기존 마이그레이션 마지막 번호 `0023_rename_bookseen_to_booxen.py` 이후 순번, 예: `0024_add_yes24data.py`), `CreateModel` + `AddIndex` 오퍼레이션으로 `0013_split_vendor_data.py`의 `KyoboData` 생성 패턴을 따른다
- `available`, `stock`, `returnable`, `arrival`, `publisher`, `ordered_qty`, `total_price` 필드는 추가하지 않는다 (제외 범위 참조)

---

### REQ-PO6-002 — YES24 결과파일 파서 구현

When `_parse_yes24_xlsx(file_bytes)`가 호출될 때, the system shall openpyxl로 `.xlsx` 파일을 읽어 row 0을 헤더로 인식하고 row 1부터 데이터로 파싱해야 한다 (booxen/kyobo와 달리 타이틀 행이 없으므로 스킵 행은 1개뿐).

- 대상 파일: `backend/order/excel_utils.py`
- 컬럼 인덱스(0-based, 샘플 파일 헤더로 확인됨): ISBN=8, 정가=6, 공급가=13, 유통상태=11
- 파싱 규칙:
  - `sku`: ISBN 컬럼 값을 문자열로 변환·strip. 값이 없거나 숫자로만 구성되지 않은 행은 건너뛴다 (kyobo 파서의 `sku.isdigit()` 검증과 동일 원칙)
  - `list_price`: 정가 컬럼 값 (int/float → 그대로 반환, 파싱 실패 시 `None`)
  - `price`: 공급가 컬럼 값 (int/float → 그대로 반환, 파싱 실패 시 `None`)
  - `status`: 유통상태 컬럼 값을 문자열로 변환 (값이 `None`이면 `None` 유지) — 관측된 값: `판매중`, `절판`, `품절`, `일시품절`, `예약판매`, `None`
- 반환하는 각 dict는 기존 `parse_vendor_excel` 공용 계약과 호환되어야 한다: `UploadVendorFileView.post()`의 공통 루프가 `row["sku"]`, `row["available"]`, `row["price"]`를 필수 키로 접근하므로, YES24 파서는 최소 `sku`, `available`, `price` 키를 포함해야 한다. YES24 원본에는 가용 여부(재고 Y/N) 데이터가 없으므로 `available`은 `None`으로 채운다
- 파일이 비어있거나(헤더만 있고 데이터 행 없음) 읽기 실패 시 `ValueError` 발생 (booxen/kyobo 파서와 동일한 에러 처리 패턴)

---

### REQ-PO6-003 — parse_vendor_excel dispatch에 YES24 분기 추가

When `parse_vendor_excel(file_bytes, distributor)`가 `distributor="yes24"`로 호출될 때, the system shall `_parse_yes24_xlsx(file_bytes)`를 호출하여 결과를 반환해야 한다.

- 대상 파일: `backend/order/excel_utils.py`
- 기존 dispatch 순서 유지: `.xls` magic byte 감지(booxen) → `distributor == "kyobo"` → `distributor == "yes24"`(신규) → `_parse_generic_xlsx` fallback
- 기존 booxen/kyobo 분기 동작은 변경하지 않는다

---

### REQ-PO6-004 — VENDOR_FILE_DISTRIBUTORS에 yes24 추가

The system shall `VENDOR_FILE_DISTRIBUTORS` 집합에 `"yes24"`를 포함해야 한다 (`{"booxen", "kyobo", "yes24"}`).

- 대상 파일: `backend/order/purchase_order_views.py`
- `UploadVendorFileView.post()`의 유효성 검사(`distributor not in VENDOR_FILE_DISTRIBUTORS` → 400)가 `"yes24"`를 유효한 값으로 허용해야 한다
- `VENDOR_RULE_DISTRIBUTORS`(`choeumgoyuk`, `agape`, `sungseoyunion`)는 이 SPEC과 무관하며 변경하지 않는다

---

### REQ-PO6-005 — UploadVendorFileView에 Yes24Data 업서트 분기 추가

When `UploadVendorFileView.post()`가 `distributor="yes24"`이고 파싱이 성공했을 때, the system shall 파싱된 각 행에 대해 `Yes24Data.objects.update_or_create(sku=sku, defaults={...})`를 실행하여 `price`, `list_price`, `status` 필드를 갱신해야 한다.

- 대상 파일: `backend/order/purchase_order_views.py`
- 기존 `if distributor == "booxen": ... else: # kyobo ...` 2분기 구조를 `if distributor == "booxen": ... elif distributor == "yes24": ... else: # kyobo ...` 3분기 구조로 변경
- `list_price`는 파싱 결과 dict의 `list_price` 키에서 가져오며, `Decimal(str(row["list_price"]))` 형태로 변환 (값이 `None`이면 `None` 유지) — 기존 `price`/`total_price` 변환 패턴과 동일
- 응답 JSON 구조(`parsed_count`, `distributor`)는 기존과 동일하게 유지
- booxen/kyobo 분기의 기존 동작은 변경하지 않는다

---

### REQ-PO6-006 — 프론트엔드 발주처 옵션에 YES24 추가

The system shall `VendorFileUploadTab.tsx`의 `DISTRIBUTOR_OPTIONS`에 `'YES24'`를 추가하고 `DISTRIBUTOR_API_KEY`에 `'YES24': 'yes24'` 매핑을 추가해야 한다.

- 대상 파일: `frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.tsx`
- `DISTRIBUTOR_OPTIONS = ['북센', '교보', 'YES24'] as const`
- 발주처 `<select>` 드롭다운에 "YES24" 옵션이 표시되고 선택 가능해야 함
- 업로드 상태 표시(`uploadedCounts`) 영역은 `DISTRIBUTOR_OPTIONS`를 순회하는 기존 로직을 그대로 사용하므로 별도 수정 불필요 (자동으로 YES24 건수 표시)

---

### REQ-PO6-007 — 프론트엔드 안내 문구 업데이트

The system shall `VendorFileUploadTab` 하단 안내 문구를 "북센·교보 파일 업로드 후..."에서 "북센·교보·YES24 파일 업로드 후..."로 갱신해야 한다.

- 대상 파일: `frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.tsx`
- 변경 후 문구: `"북센·교보·YES24 파일 업로드 후 Daily Review 탭에서 발주처를 확인하고 확정하세요."`

---

### REQ-PO6-008 — YES24 파서 단위 테스트

The system shall `backend/order/tests/test_purchase_orders.py`의 `TestParseVendorExcel` 클래스에 YES24 파서 단위 테스트를 추가해야 한다.

- 헤더 행 + 데이터 행으로 구성된 `.xlsx` 픽스처(`_make_yes24_excel` 유사 헬퍼)를 사용
- 정상 케이스: ISBN/정가/공급가/유통상태가 올바르게 매핑되는지 검증
- 유통상태 값별 파싱: `판매중`, `절판`, `품절`, `일시품절`, `예약판매`, `None`이 모두 오류 없이 처리되는지 검증
- ISBN이 비어있거나 숫자가 아닌 행은 결과에서 제외되는지 검증
- 데이터 행이 없는(헤더만 있는) 빈 파일 업로드 시 `ValueError` 발생 검증

---

### REQ-PO6-009 — YES24 업로드 API 통합 테스트

The system shall `backend/order/tests/test_purchase_orders.py`의 `TestUploadVendorFileView` 클래스에 YES24 업로드 API 통합 테스트를 추가해야 한다.

- `POST /api/purchase-orders/upload-vendor-file/`에 `distributor="yes24"` + YES24 형식 `.xlsx` 파일을 전송했을 때 200 응답과 올바른 `parsed_count`를 반환하는지 검증
- 업로드 후 `Yes24Data` 레코드가 `sku`, `price`, `list_price`, `status`로 정확히 생성되는지 검증
- 동일 SKU를 재업로드했을 때 신규 레코드가 아닌 기존 레코드가 업데이트(upsert)되는지 검증

---

### REQ-PO6-010 — 기존 auto-select/발주서 생성 로직 무변경 보장 (Unwanted Behavior)

If YES24 업로드/파싱 기능이 구현되면, then the system shall NOT `auto_select_distributor()`, `VendorComparison` 모델/`DISTRIBUTOR_CHOICES`, 또는 `generate_order_excel()`을 수정해야 한다.

- `backend/order/tests/test_auto_dist.py`의 기존 테스트는 변경 없이 그대로 통과해야 한다
- `GenerateOrderFileView`의 `VALID_DISTRIBUTORS`에 `"yes24"`를 추가하지 않는다
- `DailyReviewTab.tsx` 및 관련 다운로드/업로드 로직은 이 SPEC의 범위에 포함되지 않는다

---

## 구현 범위 (수정·생성 대상 파일)

| 파일 | 변경 유형 | 변경 내용 요약 |
|------|-----------|----------------|
| `backend/order/models.py` | 수정 | `Yes24Data` 모델 추가 (`price`, `list_price`, `status`, `updated_at`) |
| `backend/order/migrations/00XX_add_yes24data.py` | 생성 | `Yes24Data` 테이블(`orders_yes24data`) 생성 마이그레이션 |
| `backend/order/excel_utils.py` | 수정 | `_parse_yes24_xlsx` 함수 추가, `parse_vendor_excel()` dispatch에 yes24 분기 추가 |
| `backend/order/purchase_order_views.py` | 수정 | `VENDOR_FILE_DISTRIBUTORS`에 yes24 추가, `UploadVendorFileView.post()` 3번째 업서트 분기 추가 |
| `frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.tsx` | 수정 | `DISTRIBUTOR_OPTIONS`/`DISTRIBUTOR_API_KEY`에 YES24 추가, 안내 문구 갱신 |
| `backend/order/tests/test_purchase_orders.py` | 수정 | `TestParseVendorExcel`/`TestUploadVendorFileView`에 YES24 테스트 케이스 추가 |

---

## 제외 범위 (What NOT to Build)

- `auto_select_distributor()` 3자 비교 통합 (booxen/kyobo/yes24) — 이 SPEC은 참고용 업로드만 다루며 자동 선택 결정 트리는 변경하지 않는다
- `VendorComparison` 모델에 yes24 관련 필드나 `DISTRIBUTOR_CHOICES` 항목 추가
- `generate_order_excel()`에 YES24 발주서(발주 요청 파일) 생성 브랜치 추가 — YES24는 발주서 생성 대상이 아니다
- `DailyReviewTab.tsx` 화면 표시 변경 (YES24 데이터를 Daily Review 탭에 노출하는 기능 없음)
- YES24 원본 파일의 도서명, 출판사, 저자, 출간일, 주문수량, 부가코드, 분야명, 중복여부, 공급률 컬럼의 DB 영속화
- YES24 업로드 이력 추적 또는 감사 로그 테이블
- YES24 재고수량/반품가능여부 데이터 — 원본 파일에 해당 컬럼이 존재하지 않음

---

## 인수 조건

### AC-001 — YES24 헤더 기반 컬럼 매핑 정확성

**Given** row 0이 `번호, 상품번호, 도서명, 출판사, 저자, 출간일, 정가, 주문수량, ISBN, 부가코드, 분야명, 유통상태, 중복여부, 공급가, 공급률` 헤더이고 row 1에 `ISBN="8809226729403"`, `정가=15000`, `공급가=9750`, `유통상태="판매중"`인 데이터 행이 있는 `.xlsx` 파일일 때
**When** `_parse_yes24_xlsx(file_bytes)`를 호출하면
**Then** 반환된 리스트에 `{"sku": "8809226729403", "list_price": 15000, "price": 9750, "status": "판매중", ...}`에 해당하는 항목이 포함되어야 한다

---

### AC-002 — 헤더 1행만 스킵 (booxen/kyobo와 달리 타이틀 행 없음)

**Given** row 0이 헤더이고 row 1부터 데이터인 YES24 형식 파일일 때
**When** `_parse_yes24_xlsx(file_bytes)`를 호출하면
**Then** row 1의 데이터가 파싱 결과에 포함되어야 한다 (row 2부터 데이터로 취급하는 booxen/kyobo 방식과 달리 스킵 행이 1개뿐임을 검증)

---

### AC-003 — 유통상태 값별 정상 파싱

**Given** 유통상태 컬럼 값이 각각 `판매중`, `절판`, `품절`, `일시품절`, `예약판매`, `None`인 6개 데이터 행이 있을 때
**When** `_parse_yes24_xlsx(file_bytes)`를 호출하면
**Then** 6개 행 모두 오류 없이 파싱되어야 하며 각 `status` 필드 값이 원본과 일치해야 한다

---

### AC-004 — 유효하지 않은 ISBN 행 제외

**Given** ISBN 컬럼이 비어있거나(`None`) 숫자가 아닌 문자열("N/A")인 행이 포함된 파일일 때
**When** `_parse_yes24_xlsx(file_bytes)`를 호출하면
**Then** 해당 행은 반환 리스트에서 제외되어야 한다

---

### AC-005 — 업로드 API로 Yes24Data 신규 생성

**Given** 인증된 관리자가 `distributor="yes24"`와 유효한 YES24 형식 `.xlsx` 파일을 `POST /api/purchase-orders/upload-vendor-file/`에 전송할 때
**When** 요청이 처리되면
**Then** 200 응답과 함께 `{"parsed_count": N, "distributor": "yes24"}`가 반환되어야 하고, 파싱된 각 SKU에 대해 `Yes24Data` 레코드가 `price`/`list_price`/`status` 값과 함께 생성되어야 한다

---

### AC-006 — 동일 SKU 재업로드 시 upsert

**Given** `Yes24Data(sku="8809226729403", price=9750, list_price=15000, status="판매중")`가 이미 존재할 때
**When** 동일 SKU에 대해 `price=9500`, `status="품절"`인 새 파일을 업로드하면
**Then** 신규 레코드가 생성되지 않고 기존 레코드의 `price`가 9500, `status`가 "품절"로 갱신되어야 한다

---

### AC-007 — 잘못된 distributor 값은 여전히 400 반환

**Given** `distributor="unknown_vendor"`로 업로드 요청을 보낼 때
**When** `UploadVendorFileView.post()`가 처리되면
**Then** 400 응답과 함께 `VENDOR_FILE_DISTRIBUTORS`에 `"yes24"`를 포함한 유효 값 목록이 에러 메시지에 나타나야 한다

---

### AC-008 — 프론트엔드 YES24 옵션 표시 및 선택

**Given** `VendorFileUploadTab`이 렌더링될 때
**When** 발주처 드롭다운을 열면
**Then** "북센", "교보", "YES24" 3개 옵션이 표시되어야 하며, "YES24" 선택 후 파일 업로드 시 `distributor=yes24`로 API가 호출되어야 한다

---

### AC-009 — auto-select 및 발주서 생성 로직 무영향 (회귀 검증)

**Given** YES24 업로드/파싱 기능이 구현된 상태일 때
**When** `backend/order/tests/test_auto_dist.py`의 기존 테스트 스위트와 `generate_order_excel()` 관련 기존 테스트를 실행하면
**Then** 모두 기존과 동일하게 통과해야 하며 YES24 관련 코드 변경으로 인한 회귀가 없어야 한다

---

### AC-010 — 빈 데이터 파일 업로드 시 오류 처리

**Given** 헤더 행만 있고 데이터 행이 없는 YES24 형식 `.xlsx` 파일일 때
**When** `distributor="yes24"`로 업로드 요청을 보내면
**Then** `_parse_yes24_xlsx`가 `ValueError`를 발생시키고, API는 422 응답을 반환해야 한다 (기존 booxen/kyobo 파서의 빈 파일 처리와 동일)
