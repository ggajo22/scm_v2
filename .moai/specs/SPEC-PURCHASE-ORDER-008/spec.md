---
id: SPEC-PURCHASE-ORDER-008
version: 1.1.0
status: completed
created: 2026-07-25
updated: 2026-08-11
author: ggajo
priority: High
issue_number: ~
---

# Daily Review 업로드 외부 템플릿 파싱 전환 및 벤더 데이터 동기화 확장

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-07-25 | ggajo | 최초 작성 |
| 1.1.0 | 2026-08-11 | ggajo | 프로덕션 버그 수정 및 문서 동기화 — commit d22818f. REQ-PO8-018 (cross-order SKU 충돌 안전성) 및 REQ-PO8-019 (PurchaseOrder 상태 초기값 "confirmed") 신규 추가. UploadDailyReviewView에 order-name 필수 컬럼 요구사항 반영. |

---

## 문제 정의

현재 주문 관리 페이지의 "Daily Review 업로드" 기능(`UploadDailyReviewView`, `backend/order/purchase_order_views.py:944`, `parse_daily_review_excel()` 호출, `backend/order/excel_utils.py:687`)은 이 프로젝트가 자체적으로 생성하는 포맷(`generate_daily_review_excel()`, `excel_utils.py:631`)만 인식한다 — 헤더가 1행에 고정되어 있고 컬럼명이 정확히 `ISBN`, `선택`, 선택적으로 `메모`/`북센 공급가`/`교보 공급가`여야 한다. 사용자는 이 자체 생성 파일을 다운로드 → `선택` 컬럼 채움 → 재업로드하는 흐름으로 사용해 왔다.

사용자는 업로드 측이 실제로 매일 사용하는 외부 작업 파일 `Daily Order Review Template 20260724.xlsx`(Shopify 주문 추출 + 벤더 가격 비교 워크북, openpyxl로 직접 열어 실측 확인)를 그대로 받아들이도록 전환하고자 한다. 이 파일은 헤더가 3번째 행에 위치하고, SKU 컬럼명이 `ISBN`이 아닌 `Lineitem sku`이며, 자체 생성 포맷에는 없는 다수의 벤더 비교 컬럼(YES24 관련 포함)을 갖는다.

이 SPEC은 `UploadDailyReviewView`/`parse_daily_review_excel()`에 대한 두 가지 연관 변경을 다룬다.

- **Part A**: 신 템플릿의 실제 구조를 파싱하도록 전환하되, 기존 자체 생성 포맷도 계속 동작해야 한다(하위 호환 하드 제약).
- **Part B**: 업로드된 모든 행(선택 값 입력 여부 무관)을 사용해 `BooxenData`/`KyoboData`/`Yes24Data`를 upsert한다 — 사용자가 이 Daily Review 업로드 한 번을 벤더 데이터 동기화의 유일한 수단으로 쓰고 싶을 때(개별 `UploadVendorFileView` 업로드를 대체) 사용하기 위함이다.

### 신 템플릿 구조 참고 (실측 확인됨)

- 헤더 행은 1행 고정이 아니다 — `Lineitem sku` 셀과 `선택` 셀을 모두 포함하는 첫 번째 행을 헤더로 판별해야 한다(신 템플릿은 3행, 구 형식은 1행에 위치, 둘 다 지원 필요).
- 신 템플릿 헤더 행의 실제 컬럼 구성(B열부터 시작, A열은 빈 컬럼): `Shipping Zip`, `Date`, `Name`, `Lineitem sku`, `Lineitem name`, `Email`, `Total`, `location`, `Status`, `in Stock`, `Stock Location`, `SKU별 필요수량`, `BOOXEN 공급가`, `YES24 공급가`, `YES24 재고상태`, `교보 공급가`, `BOOXEN 재고수량`, `BOOXEN 재고상태`, `교보 재고수량`, `교보 재고상태`, `비교시작`, `Min Cost`, `BOOXEN 가격비교`, `YES24 가격비교`, `교보 가격비교`, `차이`, `기준over`, `BOOXEN 입고예정`, `BOOXEN 반품`, `교보 상품상태`, `교보 분야`, `교보 출판사`, `교보 반품가능여부`, `가격차이알림`, `후보기준`, `선택`. (향후 `교보 정가` 컬럼이 추가될 예정 — Part B REQ-PO8-017 참조.)
- `선택` 바로 오른쪽 컬럼은 헤더 텍스트가 없는 범례(참고용 드롭다운 값 목록) 컬럼이며 행별 데이터가 아니다: `total`, `BOOXEN`, `교보`, `YES24`, `주문취소`, `재고`, `주문보류`, `CS필요`, `타출판사`, `합계`, `check`. 이 컬럼은 데이터 컬럼으로 절대 인덱싱되어서는 안 된다.
- SKU 컬럼명: 구 형식 `ISBN` ↔ 신 템플릿 `Lineitem sku` (헤더 자동 탐지 결과에 따라 둘 중 매칭된 컬럼을 사용).
- 메모/노트 소스: 구 형식은 전용 `메모` 컬럼을 사용하지만, 신 템플릿에는 메모 컬럼이 없고 `Status` 컬럼이 그 역할을 대신한다.

---

## 솔루션 개요

**Part A**

- `parse_daily_review_excel()`이 첫 두 행을 고정 가정하는 대신, `Lineitem sku`+`선택` 또는 `ISBN`+`선택`을 모두 포함하는 첫 번째 행을 헤더로 탐지하도록 변경
- SKU 컬럼명 이중 지원(`ISBN` 또는 `Lineitem sku`), 메모 소스를 헤더 종류에 따라 `메모`/`Status`로 전환
- `BOOXEN 공급가`/`교보 공급가`/`YES24 공급가` 파싱 추가(기존 `bs_price`/`ky_price` 패턴에 `yes24_price` 신설)
- `_DISTRIBUTOR_LABEL_MAP`에 `YES24`→`yes24`, `재고`→`warehouse`(신규 범용 코드) 매핑 추가, 기존 매핑은 그대로 유지
- `UploadDailyReviewView`에 YES24 발주 확정 분기(북센/교보와 동일 패턴) 추가
- 창고 재고 분기의 위치(korea/ca/nj) 판별을 `Stock Location`이 아닌 `Status` 컬럼 값(`한국재고`/`Fullerton재고`/`NJ재고`) 기반으로 전환하며, 이는 구/신 형식 공통으로 적용되는 `LineItemNote.assignee` 위치 기반 결정 로직으로 이어짐(기존 하드코딩된 `assignee="한국창고"` 대체)

**Part B**

- `UploadDailyReviewView.post()`가 SKU 순회 루프마다, 선택 값 유무·인식 여부와 무관하게 `BooxenData`/`KyoboData`/`Yes24Data`를 `update_or_create()`로 upsert(`UploadVendorFileView`의 기존 upsert 패턴 재사용)
- `KyoboData`에 신규 필드 `list_price` 추가 + 마이그레이션, `교보 정가` 컬럼(현재 템플릿에는 없음, 향후 추가 예정)이 있을 때만 채움
- `Yes24Data.list_price`는 이 업로드 경로에서 전혀 건드리지 않음(SPEC-006 보호)

---

## 범위

### 포함

- `backend/order/excel_utils.py`: `parse_daily_review_excel()` 헤더 자동 탐지·이중 SKU 컬럼·신 템플릿 컬럼 파싱, `_DISTRIBUTOR_LABEL_MAP` 확장
- `backend/order/models.py`: `KyoboData`에 `list_price` 필드 추가
- `backend/order/migrations/`: `list_price` 필드용 신규 마이그레이션
- `backend/order/purchase_order_views.py`: `UploadDailyReviewView` — YES24 발주 확정 분기, 창고 위치 Status 기반 판별, LineItemNote 위치 기반 assignee, 전체 행 벤더 데이터 upsert
- `backend/order/tests/test_daily_review_upload.py`: 신 템플릿 파싱/YES24/창고 Status 판별/벤더 upsert/list_price 관련 신규 테스트

### 제외

- `generate_daily_review_excel()` / 다운로드 포맷 / `_DAILY_REVIEW_HEADERS` 변경 없음(자체 생성 24컬럼 포맷은 그대로 유지)
- `Yes24Data.list_price` 필드 또는 `_parse_yes24_xlsx`/`UploadVendorFileView`의 기존 동작 변경 없음(SPEC-006 보호, 검토 후 명시적으로 기각)
- `book.models.Inven.status_of_shopify`를 벤더 데이터 변경 시 15로 갱신하는 로직 — `book` 앱 관심사이며 별도 트리거를 가진 독립적인 future SPEC 대상, 이 SPEC과 무관
- `교보 분야` 컬럼 매핑 또는 이를 위한 `KyoboData` 스키마 확장
- `KyoboData.ordered_qty`/`total_price` 필드를 이 업로드 경로에서 갱신하는 로직

---

## 요구사항

### Part A — 파싱 구조 전환 및 선택 매핑 확장

### REQ-PO8-001 — 헤더 행 자동 탐지 (구/신 템플릿 동시 지원)

When `parse_daily_review_excel()`이 업로드된 워크북을 파싱할 때, the system shall 첫 행을 헤더로 고정 가정하는 대신 워크시트의 각 행을 순회하여 `Lineitem sku`와 `선택` 셀을 모두 포함하는 첫 번째 행, 또는 `ISBN`과 `선택` 셀을 모두 포함하는 첫 번째 행을 헤더 행으로 판별해야 한다.

- 대상 파일: `backend/order/excel_utils.py` (`parse_daily_review_excel()`, 현재 706-716번째 줄 부근 — 현재는 `rows[0]`을 헤더로 고정 가정)
- 구 형식(자체 생성 포맷): 헤더가 1행(`rows[0]`)에 위치, `ISBN`+`선택` 조합
- 신 템플릿: 헤더가 3행(`rows[2]`)에 위치, `Lineitem sku`+`선택` 조합(실측 확인됨) — 탐지 로직은 특정 행 번호에 의존하지 않고 두 헤더 셀의 동시 존재 여부로 판별해야 한다
- 두 조건 중 어느 것도 만족하는 행을 찾지 못하면 기존과 동일하게 `ValueError`를 발생시켜야 한다(에러 메시지는 두 SKU 컬럼명을 모두 안내하도록 갱신)

---

### REQ-PO8-002 — SKU 컬럼 이중 헤더명 지원

When 헤더 행이 확정된 후 SKU 컬럼 인덱스를 조회할 때, the system shall 헤더에 `Lineitem sku`가 있으면 이를, 없고 `ISBN`이 있으면 이를 SKU 컬럼으로 사용해야 한다.

- 매칭된 컬럼과 무관하게 파싱 결과 dict의 `sku` 키는 동일한 방식으로 채워져야 하며, 다운스트림 로직(`UploadDailyReviewView`)은 어떤 헤더명이 매칭되었는지 알 필요가 없어야 한다

---

### REQ-PO8-003 — 범례 컬럼 오분류 방지

If 헤더 행에서 `선택` 컬럼 바로 오른쪽에 헤더 텍스트가 없는 범례 컬럼(`total`/`BOOXEN`/`교보`/`YES24`/`주문취소`/`재고`/`주문보류`/`CS필요`/`타출판사`/`합계`/`check` 값을 세로로 나열한 참고용 컬럼)이 존재하면, then the system shall 이 컬럼을 선택 데이터 컬럼이나 그 밖의 어떤 데이터 컬럼으로도 인덱싱하지 않아야 한다.

- 모든 컬럼 인덱스는 `header.index(<정확한 헤더 텍스트>)` 방식의 이름 기반 조회로만 결정되어야 하며, 고정 위치(포지셔널) 인덱싱을 사용해서는 안 된다 — 헤더가 없는 컬럼은 자연히 어떤 `header.index()` 조회에도 매칭되지 않아야 한다

---

### REQ-PO8-004 — 신 템플릿 벤더 공급가 컬럼 파싱

When 헤더에 `BOOXEN 공급가`, `교보 공급가`, `YES24 공급가` 컬럼이 존재할 때, the system shall 각 컬럼 값을 파싱 결과 dict의 `bs_price`, `ky_price`, `yes24_price` 키에 채워야 한다(기존 749-763번째 줄의 `bs_price`/`ky_price` float 변환·예외 처리 패턴과 동일한 방식을 `yes24_price`에도 적용).

- 해당 컬럼이 헤더에 없는 경우(구 형식 파일 등), 대응하는 키는 기존과 동일하게 `None`으로 유지되어야 한다

---

### REQ-PO8-005 — 메모/노트 소스 컬럼 전환

While 확정된 헤더가 신 템플릿(SKU 컬럼으로 `Lineitem sku`가 매칭된 상태)인 동안, the system shall `메모` 컬럼 대신 `Status` 컬럼 값을 각 행의 note 소스로 사용해야 한다.

While 확정된 헤더가 구 형식(SKU 컬럼으로 `ISBN`이 매칭된 상태)인 동안, the system shall 기존과 동일하게 `메모` 컬럼을 note 소스로 사용해야 한다.

- 대상 파일: `backend/order/excel_utils.py` (`parse_daily_review_excel()`, 717번째 줄 및 743-747번째 줄 note 파싱 로직 부근)

---

### REQ-PO8-006 — `_DISTRIBUTOR_LABEL_MAP`에 YES24 매핑 추가

The system shall `_DISTRIBUTOR_LABEL_MAP`에 `"YES24"` → `"yes24"` 매핑을 추가해야 한다.

- 대상 파일: `backend/order/excel_utils.py` (598-607번째 줄)
- 기존 8개 매핑(북센/교보/처음교육/아가페/성서유니온/재고(한국)/재고(CA)/재고(NJ))은 그대로 유지

---

### REQ-PO8-007 — `_DISTRIBUTOR_LABEL_MAP`에 신 템플릿용 범용 재고 매핑 추가

The system shall `_DISTRIBUTOR_LABEL_MAP`에 `"재고"` → `"warehouse"`(신규 범용 코드) 매핑을 추가해야 한다.

- 신 템플릿의 `선택` 컬럼은 위치 접미사 없이 `재고` 단일 값만 사용하며(범례 확인됨), 구체적인 위치(한국/CA/NJ)는 `Status` 컬럼으로 별도 판별한다(REQ-PO8-008)
- 기존 `"재고(한국)"`→`"warehouse_korea"`, `"재고(CA)"`→`"warehouse_ca"`, `"재고(NJ)"`→`"warehouse_nj"` 3개 매핑(구 형식용)은 하위 호환을 위해 그대로 유지되며 이 신규 매핑과 공존한다

---

### REQ-PO8-008 — 창고 재고 위치를 `Status` 컬럼 값으로 판별 (신 템플릿)

When `UploadDailyReviewView.post()`가 `distributor_code == "warehouse"`(신 템플릿 범용 재고 코드)인 행을 처리할 때, the system shall 해당 행의 note 값(REQ-PO8-005에 따라 `Status` 컬럼 원본 값)을 아래 매핑으로 조회하여 창고 위치를 결정해야 한다: `"한국재고"` → `"korea"`, `"Fullerton재고"` → `"ca"`, `"NJ재고"` → `"nj"`.

- 대상 파일: `backend/order/purchase_order_views.py` (`UploadDailyReviewView.post()`, 986-990번째 줄 `_WAREHOUSE_LOCATION_MAP` 및 1031-1059번째 줄 창고 분기 부근)
- 기존 `distributor_code in _WAREHOUSE_LOCATION_MAP`(구 형식 `warehouse_korea`/`warehouse_ca`/`warehouse_nj`) 판별 조건은 변경하지 않고 그대로 유지하며, `distributor_code == "warehouse"` 케이스를 이 조건에 추가하여 같은 창고 처리 분기(재고 차감 + `purchase_status="in_stock"` + PO 미생성)로 진입시켜야 한다
- note 값이 위 3개 매핑 어디에도 없는 경우(알 수 없는 Status 값): 창고 차감·재고 확정 처리를 스킵하고 `skipped_count`를 증가시켜야 한다(기존 미인식 케이스와 동일한 안전 처리 패턴)

---

### REQ-PO8-009 — 창고 분기 LineItemNote content/assignee를 위치 기반으로 결정

When 창고 재고 확정 분기(구 형식 `warehouse_korea`/`warehouse_ca`/`warehouse_nj`와 신 형식 `warehouse` 공통)에서 `LineItemNote`를 생성할 때, the system shall `content`는 해당 행의 note 원본 값을 그대로 사용하고, `assignee`는 판별된 위치가 `korea`이면 `"한국창고"`, `ca` 또는 `nj`이면 `"미국창고"`로 설정해야 한다.

- 대상 파일: `backend/order/purchase_order_views.py` (1049-1057번째 줄 부근, 기존 하드코딩된 `assignee="한국창고"`를 위치 기반 분기로 대체)
- 이 변경은 구 형식(`warehouse_ca`/`warehouse_nj`) 업로드에도 동일하게 적용되어, 현재 CA/NJ 창고 확정 시에도 `"한국창고"`로 잘못 기록되던 동작이 함께 수정된다
- 신 형식(`warehouse`) 분기에서 `content`는 REQ-PO8-008에서 조회에 사용한 note 원본 값(예: `"한국재고"`, `"Fullerton재고"`, `"NJ재고"`)이 그대로 저장된다

---

### REQ-PO8-010 — 신 템플릿 YES24 선택 시 발주 확정 분기 추가

When `UploadDailyReviewView.post()`가 `distributor_code == "yes24"`인 행을 처리할 때, the system shall 북센/교보와 동일한 비창고 `PurchaseOrder` 생성 분기를 실행하되, 단가는 파싱된 `yes24_price`를 우선 사용하고 값이 없으면 `Yes24Data.objects.filter(sku=sku).first().price`로 폴백해야 한다.

- 대상 파일: `backend/order/purchase_order_views.py` (1061-1093번째 줄 부근, 기존 `if distributor_code == "booxen": ... elif distributor_code == "kyobo": ...` 블록에 `elif distributor_code == "yes24":` 추가)
- `PurchaseOrder.distributor = "yes24"`로 생성되며, `quantity`/`status`/`line_items` 연결 등 나머지 로직은 booxen/kyobo와 동일한 코드 경로를 재사용한다

---

### REQ-PO8-011 — 미인식 선택 값(범례 값) 스킵 유지

If 선택 컬럼 값이 `"total"`, `"합계"`, `"check"` 중 하나이면, then the system shall 이를 알려진 `distributor_code`나 CS `note_type`으로 매핑하지 않고 기존 미인식 라벨 처리 로직(738-741번째 줄)에 따라 발주 확정 대상(PurchaseOrder 생성/CS 상태변경/창고차감)에서 제외해야 한다.

- 이 스킵은 발주 확정 로직에만 적용되며, REQ-PO8-014(Part B 벤더 데이터 upsert)의 처리 대상에서는 제외되지 않는다(유효 SKU가 있으면 벤더 upsert는 그대로 수행됨)

---

### REQ-PO8-012 — 기존 미사용 레이블 하위 호환 유지 (Unwanted Behavior)

If `_DISTRIBUTOR_LABEL_MAP`이 이 SPEC에 따라 수정되면, then the system shall NOT 기존에 등록된 `"처음교육"`, `"아가페"`, `"성서유니온"`, `"재고(한국)"`, `"재고(CA)"`, `"재고(NJ)"` 매핑 항목을 제거해야 한다(이 값들은 신 템플릿에는 나타나지 않지만 구 형식 하위 호환을 위해 유지되어야 한다).

---

### REQ-PO8-013 — 구 형식(자체 생성 포맷) 하위 호환 보장 (Unwanted Behavior)

If Part A의 파싱 구조 변경이 적용되면, then the system shall NOT `backend/order/tests/test_daily_review_upload.py`에 정의된 기존 테스트 케이스(헤더 1행 고정 + `ISBN` 컬럼 기반 구 형식 업로드, SPEC-PURCHASE-ORDER-005/007에서 추가된 케이스 포함)의 통과 여부를 깨뜨려야 한다.

- REQ-PO8-001(헤더 자동 탐지)과 REQ-PO8-002(SKU 컬럼 이중 지원)가 이 하위 호환을 보장하는 메커니즘이다

---

### Part B — 벤더 데이터 테이블 동기화 (선택 값과 독립적)

### REQ-PO8-014 — 모든 유효 SKU 행에 대한 벤더 테이블 upsert (선택 값 무관)

When `parse_daily_review_excel()`이 반환한 각 행에 비어있지 않은 SKU가 있을 때, the system shall 해당 행의 선택 값 존재 여부·인식 여부와 무관하게 `BooxenData`, `KyoboData`, `Yes24Data` 레코드를 각각 `update_or_create(sku=sku, defaults={...})`로 upsert해야 한다(기존 `UploadVendorFileView`의 305-335번째 줄 upsert 패턴과 동일한 방식을 재사용).

- 대상 파일: `backend/order/purchase_order_views.py` (`UploadDailyReviewView.post()`, SKU 순회 루프 내부)
- 이 upsert는 Part A의 선택 기반 발주 확정(PurchaseOrder 생성/CS 상태변경/창고차감) 로직과 독립적으로, 같은 트랜잭션 내에서 SKU마다 항상 실행되어야 한다(선택 값이 비어있거나 REQ-PO8-011의 미인식 값이어도 실행됨)

---

### REQ-PO8-015 — `BooxenData` 필드 매핑

When `BooxenData`를 upsert할 때, the system shall `"BOOXEN 공급가"` → `price`, `"BOOXEN 재고수량"` → `stock`, `"BOOXEN 재고상태"` → `status`, `"BOOXEN 입고예정"` → `arrival`로 매핑하고, `"BOOXEN 반품"` 값이 `"가능"`이면 `returnable=True`, 그 외 값이면 `False`로 설정하며, `available`은 저장 대상 `stock`이 0보다 큰지 여부로 계산해야 한다(`_parse_booxen_xls`의 174번째 줄 관례와 동일).

---

### REQ-PO8-016 — `KyoboData` 필드 매핑 (기존 필드)

When `KyoboData`를 upsert할 때, the system shall `"교보 공급가"` → `price`, `"교보 재고수량"` → `stock`, `"교보 재고상태"`(값 `Y`/`N`) → `available`(`Y` → `True`), `"교보 상품상태"`(값 `정상`/`품절` 등) → `status`, `"교보 반품가능여부"` → `returnable`, `"교보 출판사"` → `publisher`로 매핑해야 한다.

- `ordered_qty`와 `total_price`는 이 upsert의 `defaults`에 포함하지 않아야 하며 기존 값을 그대로 유지해야 한다
- `"교보 분야"` 컬럼은 어떤 필드에도 매핑하지 않는다(스키마 변경 없음, 값 폐기)

---

### REQ-PO8-017 — `KyoboData.list_price` 신규 필드 및 마이그레이션

The system shall `KyoboData` 모델에 `list_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)` 필드를 추가하고, 이에 대응하는 Django 마이그레이션을 `backend/order/migrations/`에 생성해야 한다.

When 헤더에 `"교보 정가"` 컬럼이 존재할 때, the system shall 해당 값을 `KyoboData` upsert의 `list_price` `defaults`에 포함해야 한다.

Where 헤더에 `"교보 정가"` 컬럼이 존재하지 않을 때(현재 템플릿 상태), the system shall `list_price`를 upsert `defaults`에서 제외하여 해당 SKU의 기존 `list_price` 값을 변경하지 않아야 한다.

- 대상 파일: `backend/order/models.py` (`KyoboData` 클래스, 293-312번째 줄), `backend/order/migrations/0028_*.py`(신규 파일, 최신 마이그레이션 `0027_backfill_bundle_title_data.py` 다음 번호)
- 이 필드는 오직 이 Daily Review 업로드 경로를 통해서만 채워지며, 기존 `_parse_kyobo_xlsx`(교보 결과파일 업로드, `UploadVendorFileView`)에는 정가 컬럼이 없으므로 변경하지 않는다

---

### REQ-PO8-018 — `Yes24Data` 필드 매핑 및 `list_price` 보호 (Unwanted Behavior)

When `Yes24Data`를 upsert할 때, the system shall `"YES24 공급가"` → `price`, `"YES24 재고상태"` → `status`만 매핑해야 한다.

If 이 Daily Review 업로드 경로가 `Yes24Data`를 upsert하면, then the system shall NOT `list_price` 필드를 `defaults`에 포함하거나 수정해야 한다(`list_price`는 SPEC-PURCHASE-ORDER-006의 `UploadVendorFileView`/`_parse_yes24_xlsx` 전용 필드로 그대로 유지된다).

---

### REQ-PO8-019 — UploadDailyReviewView에서 생성된 PurchaseOrder의 초기 상태

When `UploadDailyReviewView.post()`가 신규 `PurchaseOrder`를 생성할 때 (distributor_code가 booxen/kyobo/yes24/warehouse 중 하나이고 해당 분기에서 PO를 생성하는 경우), the system shall `status="confirmed"`로 초기화해야 한다 — "pending" 상태로 시작하는 기존 `ConfirmOrderView`(사용자가 발주를 "확정"하기 전 staging 단계)와 달리, Daily Review 업로드는 벤더로부터의 **이미 확정된 응답**을 반영하는 특성을 가지므로, 생성 시점에 즉시 확정 상태로 설정되어야 한다.

---

## 구현 범위 (수정·생성 대상 파일)

| 파일 | 변경 유형 | 변경 내용 요약 |
|------|-----------|----------------|
| `backend/order/excel_utils.py` | 수정 | `parse_daily_review_excel()` 헤더 자동 탐지 + SKU 컬럼 이중 지원 + 신 템플릿 컬럼 파싱(`yes24_price`, note 소스 전환), `_DISTRIBUTOR_LABEL_MAP`에 `YES24`/`재고` 매핑 추가 |
| `backend/order/models.py` | 수정 | `KyoboData`에 `list_price` 필드 추가 |
| `backend/order/migrations/0028_kyobodata_list_price.py` | 생성 | `KyoboData.list_price` 필드 마이그레이션 |
| `backend/order/purchase_order_views.py` | 수정 | `UploadDailyReviewView`에 YES24 발주 확정 분기, 창고 위치 Status 기반 판별(`warehouse` 신규 코드), LineItemNote 위치 기반 assignee, 모든 유효 SKU 행에 대한 `BooxenData`/`KyoboData`/`Yes24Data` upsert 추가 |
| `backend/order/tests/test_daily_review_upload.py` | 수정 | 신 템플릿 헤더 탐지, 범례 컬럼 무시, YES24 발주, 창고 Status 기반 분기, 벤더 데이터 upsert, `list_price` optional 컬럼 처리 등 REQ-PO8-* 신규 테스트 케이스 추가 |

---

## 제외 범위 (What NOT to Build)

- `generate_daily_review_excel()` / 다운로드 포맷 / `_DAILY_REVIEW_HEADERS` 변경 — 자체 생성 24컬럼 다운로드 포맷은 이 SPEC의 대상이 아니며 그대로 유지된다
- `Yes24Data.list_price` 필드 변경 또는 `_parse_yes24_xlsx`/`UploadVendorFileView`의 기존 동작 변경 — SPEC-PURCHASE-ORDER-006에서 이미 구현·검증된 기능이며, 이 필드를 이 SPEC에서 함께 손대는 방안은 검토 후 명시적으로 기각되었다(SPEC-006의 기존 테스트 커버리지 보호가 우선)
- `book.models.Inven.status_of_shopify`를 벤더 데이터 변경 시점에 `15`로 갱신하는 로직 — `book` 앱의 별도 관심사이자 다른 트리거를 가진 독립적인 future SPEC 대상이며, 이 SPEC은 그 존재를 전제하거나 참조하지 않는다
- `"교보 분야"` 컬럼을 저장하기 위한 `KyoboData` 스키마 확장 — 매핑 대상이 아니며 값은 폐기된다
- `KyoboData.ordered_qty`/`total_price` 필드를 이 업로드 경로에서 갱신하는 로직 — 기존 값을 그대로 유지한다

---

## 인수 조건

### AC-001 — 신 템플릿 헤더 자동 탐지 (3행, `Lineitem sku`+`선택`)

**Given** 3번째 행에 `Lineitem sku`와 `선택` 셀을 모두 포함하는 신 템플릿 워크북(1-2행은 헤더가 아닌 다른 내용)일 때
**When** `parse_daily_review_excel()`을 호출하면
**Then** 3번째 행을 헤더로 인식하고 4번째 행부터 데이터 행으로 파싱해야 한다

---

### AC-002 — 구 형식 헤더 하위 호환 유지 (1행, `ISBN`+`선택`)

**Given** 기존 `test_daily_review_upload.py`의 `_make_daily_review_excel()` 픽스처처럼 1번째 행에 `ISBN`과 `선택` 헤더가 있는 구 형식 워크북일 때
**When** `parse_daily_review_excel()`을 호출하면
**Then** 기존과 동일하게 1행을 헤더로 인식하고 정상적으로 파싱되어야 한다(회귀 없음)

---

### AC-003 — 범례 컬럼 오분류 방지

**Given** 신 템플릿에서 `선택` 컬럼 바로 오른쪽에 헤더 텍스트가 없는 범례 컬럼(`total`/`BOOXEN`/`교보`/`YES24`/`주문취소`/`재고`/`주문보류`/`CS필요`/`타출판사`/`합계`/`check` 값을 세로로 나열)이 존재할 때
**When** `parse_daily_review_excel()`을 호출하면
**Then** 반환된 어떤 행에도 범례 컬럼의 값이 선택/SKU/가격 등 데이터 필드로 섞여 들어가지 않아야 한다

---

### AC-004 — 실제 샘플 데이터로 BOOXEN 발주 확정 + 벤더 upsert 동시 검증 (Part A + Part B 통합)

**Given** SKU `"9791124591055"`(제목 `"애니가 남긴 것"`)의 미발주 `LineItem`이 존재하고, 신 템플릿 파일의 해당 행에 `선택="BOOXEN"`, `BOOXEN 공급가`/`교보 공급가`/`YES24 공급가` 값이 각각 채워져 있을 때
**When** `UploadDailyReviewView`가 이 파일을 처리하면
**Then** `distributor="booxen"`인 `PurchaseOrder`가 생성되고, 동시에 SKU `"9791124591055"`에 대해 `BooxenData`, `KyoboData`, `Yes24Data` 세 테이블 모두 레코드가 upsert되어야 한다

---

### AC-005 — YES24 선택 시 발주 확정 (신규 지원)

**Given** 신 템플릿에서 `선택="YES24"`로 표시된 미발주 SKU 행에 `YES24 공급가` 값이 채워져 있을 때
**When** 업로드가 처리되면
**Then** `distributor="yes24"`인 `PurchaseOrder`가 생성되고 `unit_price`는 파싱된 `YES24 공급가` 값이어야 한다

---

### AC-006 — YES24 공급가 미기재 시 `Yes24Data` 폴백

**Given** `선택="YES24"`이나 해당 행의 `YES24 공급가` 셀이 비어 있고, `Yes24Data(sku=<SKU>, price=12000)`가 사전에 존재할 때
**When** 업로드가 처리되면
**Then** 생성된 `PurchaseOrder.unit_price`가 `12000`이어야 한다

---

### AC-007 — 창고 분기: `Status="Fullerton재고"` → CA 위치, 미국창고 담당자

**Given** 신 템플릿에서 `선택="재고"`, `Status="Fullerton재고"`인 행이 있고 `WarehouseStock(isbn=<SKU>, location="ca", quantity=5)`가 존재할 때(주문 수량 2)
**When** 업로드가 처리되면
**Then** `WarehouseStock.quantity`가 3으로 차감되고, 해당 `LineItem.purchase_status="in_stock"`으로 설정되며, 생성된 `LineItemNote`의 `content="Fullerton재고"`, `assignee="미국창고"`여야 한다

---

### AC-008 — 창고 분기: `Status="한국재고"` → 한국 위치, 한국창고 담당자

**Given** 신 템플릿에서 `선택="재고"`, `Status="한국재고"`인 행일 때
**When** 업로드가 처리되면
**Then** `location="korea"`로 해당 `WarehouseStock`이 차감되고, 생성된 `LineItemNote`의 `content="한국재고"`, `assignee="한국창고"`여야 한다

---

### AC-009 — 미인식 선택 값(`합계`) 스킵 + 벤더 upsert는 유지

**Given** 신 템플릿에서 `선택="합계"`인 행(유효 SKU 및 `BOOXEN 공급가`/`교보 공급가`/`YES24 공급가` 값 존재)일 때
**When** 업로드가 처리되면
**Then** 해당 SKU에 대한 `PurchaseOrder` 생성/CS 노트 생성/창고 차감은 발생하지 않아야 하지만, `BooxenData`/`KyoboData`/`Yes24Data`는 upsert되어야 한다

---

### AC-010 — 선택 값이 비어 있는 행도 벤더 upsert 수행 (Part B 독립성)

**Given** 신 템플릿에서 `선택` 컬럼이 빈 값이고 유효 SKU와 공급가 값들은 채워져 있는 행일 때
**When** 업로드가 처리되면
**Then** 발주 확정 로직(PurchaseOrder/CS/창고)은 실행되지 않지만 `BooxenData`/`KyoboData`/`Yes24Data` upsert는 실행되어야 한다

---

### AC-011 — 교보 재고상태/상품상태 매핑 정확성

**Given** 행의 `교보 재고상태="Y"`, `교보 상품상태="정상"`일 때
**When** `KyoboData`가 upsert되면
**Then** `available=True`, `status="정상"`으로 저장되어야 한다(`교보 재고상태` 값이 `status`에 저장되지 않아야 한다)

---

### AC-012 — `교보 정가` 컬럼 부재 시 `list_price` 미변경

**Given** 현재 템플릿(헤더에 `교보 정가` 컬럼 없음)으로 업로드하고, 업로드 전 `KyoboData(sku=<SKU>, list_price=5000)`가 이미 존재할 때
**When** 업로드가 처리되면
**Then** 해당 `KyoboData.list_price`는 `5000`으로 유지되어야 한다(변경되지 않음)

---

### AC-013 — `교보 정가` 컬럼 존재 시 `list_price` 저장 (향후 템플릿 대비)

**Given** 헤더에 `교보 정가` 컬럼이 추가된 워크북에서 해당 SKU 행의 값이 `15000`일 때
**When** 업로드가 처리되면
**Then** 해당 SKU의 `KyoboData.list_price`가 `15000`으로 저장되어야 한다

---

### AC-014 — `Yes24Data.list_price` 무변경 회귀 검증

**Given** `Yes24Data(sku=<SKU>, list_price=20000, price=18000)`가 사전에 존재하고, Daily Review 업로드 파일에 해당 SKU 행(`YES24 공급가=19000`)이 포함되어 있을 때
**When** 업로드가 처리되면
**Then** `Yes24Data.price`는 `19000`으로 갱신되지만 `list_price`는 `20000`으로 그대로 유지되어야 한다

---

### AC-015 — 기존 `test_daily_review_upload.py` 전체 회귀 통과

**Given** 이 SPEC의 구현이 완료된 상태일 때
**When** `backend/order/tests/test_daily_review_upload.py` 전체(SPEC-PURCHASE-ORDER-005/007 관련 기존 테스트 포함)를 실행하면
**Then** 모든 기존 테스트가 변경 없이 통과해야 하며 REQ-PO8-* 관련 코드 변경으로 인한 회귀가 없어야 한다

---

### AC-016 — UploadDailyReviewView에서 생성된 PurchaseOrder 초기 상태 검증

**Given** SKU가 미발주 상태이고, Daily Review 업로드 파일에 해당 SKU 행의 `선택="BOOXEN"`이 기재되어 있을 때
**When** 업로드가 처리되고 새 `PurchaseOrder`가 생성되면
**Then** 해당 `PurchaseOrder.status`는 `"confirmed"`여야 하며, `"pending"` 상태로 생성되지 않아야 한다.

---

## 관련 SPEC

- SPEC-PURCHASE-ORDER-005: Daily Review 업로드 창고재고 차감 로직(`_WAREHOUSE_LOCATION_MAP`, `WarehouseStock` 차감 쿼리, `confirmed_by_distributor` 응답)의 기반이 되는 SPEC. 이 SPEC-008은 그 로직의 창고 위치 판별 방식만 확장한다(구 형식 유지 + 신 형식 Status 기반 추가).
- SPEC-PURCHASE-ORDER-006: `Yes24Data` 모델, `_parse_yes24_xlsx`, `UploadVendorFileView`, `list_price` 필드를 구현한 SPEC. 이 SPEC-008의 Part B는 동일한 upsert 패턴을 재사용하지만 `Yes24Data.list_price`는 명시적으로 건드리지 않는다.
- SPEC-PURCHASE-ORDER-007: `generate_order_excel()`에 YES24 발주 파일 생성 분기를 추가한 SPEC. 이 SPEC-008의 YES24 발주 확정 분기(REQ-PO8-010)는 SPEC-007이 아닌 SPEC-005/006의 `UploadDailyReviewView` 경로에 속하며 별개의 코드 경로다.

---

## 구현 노트 (Implementation Notes)

### 구현 완료 사항

**Part A — 신 템플릿 파싱 구조 전환**

- `parse_daily_review_excel()` 헤더 자동 탐지 구현: 고정 행 위치(1행 또는 3행)에 의존하지 않고, `Lineitem sku`+`선택` 또는 `ISBN`+`선택` 조합을 포함하는 첫 번째 행을 자동으로 감지하여 헤더로 인식. 구 형식(자체 생성 포맷)과 신 템플릿 모두 지원.
- SKU 컬럼 이중 지원 구현: 헤더에 따라 `Lineitem sku` 또는 `ISBN` 중 매칭된 컬럼명을 자동으로 선택하여 데이터 추출. 다운스트림 로직은 어느 컬럼명이 선택되었는지 알 필요 없음.
- 범례 컬럼 오분류 방지: 신 템플릿의 `선택` 컬럼 바로 오른쪽 범례 컬럼(헤더 텍스트 없음)이 데이터 컬럼으로 인덱싱되지 않도록 이름 기반 인덱싱(`header.index(컬럼명)`)으로 변경.
- 신 템플릿 벤더 공급가 컬럼 파싱: `BOOXEN 공급가`/`교보 공급가`/`YES24 공급가` 컬럼을 각각 `bs_price`/`ky_price`/`yes24_price`로 파싱하고 float 변환·예외 처리 적용.
- 메모/노트 소스 컬럼 전환: 신 템플릿에서는 `Status` 컬럼을, 구 형식에서는 `메모` 컬럼을 note 소스로 사용하도록 헤더 종류에 따라 자동 전환.
- `_DISTRIBUTOR_LABEL_MAP` 확장: `YES24`→`yes24`, `재고`→`warehouse`(신규 범용 코드) 매핑 추가. 기존 8개 매핑(처음교육/아가페/성서유니온/재고(한국)/재고(CA)/재고(NJ)) 그대로 유지.
- 창고 재고 분기 위치 판별 로직 개선: 신 템플릿 `warehouse` 코드일 때 `Status` 컬럼 값(`한국재고`/`Fullerton재고`/`NJ재고`)으로 위치 결정. 구 형식 `warehouse_korea`/`warehouse_ca`/`warehouse_nj` 코드도 동시 지원.
- LineItemNote assignee 위치 기반 결정: 판별된 창고 위치(`korea` → `"한국창고"`, `ca`/`nj` → `"미국창고"`)에 따라 담당자 자동 배정. 구 형식의 기존 하드코딩 버그(`warehouse_ca`/`warehouse_nj`에서도 `"한국창고"`로 기록되던 문제) 함께 수정.
- YES24 발주 확정 분기 추가: `distributor_code == "yes24"`일 때 북센/교보와 동일한 PurchaseOrder 생성 분기. 단가는 파싱된 `yes24_price` 우선, 없으면 `Yes24Data.price` 폴백.
- 미인식 선택 값 스킵 유지: `total`/`합계`/`check` 값은 발주 확정 로직에서 제외. 벤더 데이터 upsert는 독립적으로 수행(Part B).

**Part B — 벤더 데이터 전체 행 동기화**

- 벤더 데이터 upsert 배선: SKU 순회 루프마다, 선택 값 유무·인식 여부와 무관하게 `BooxenData`/`KyoboData`/`Yes24Data`를 `update_or_create()` 메커니즘으로 upsert.
- `BooxenData` 필드 매핑: `BOOXEN 공급가`→`price`, `BOOXEN 재고수량`→`stock`, `BOOXEN 재고상태`→`status`, `BOOXEN 입고예정`→`arrival`, `BOOXEN 반품`(가능 여부)→`returnable`, `available`은 `stock > 0` 계산.
- `KyoboData` 필드 매핑: `교보 공급가`→`price`, `교보 재고수량`→`stock`, `교보 재고상태`(Y/N)→`available`, `교보 상품상태`→`status`, `교보 반품가능여부`→`returnable`, `교보 출판사`→`publisher`. `ordered_qty`/`total_price`는 upsert defaults에서 제외하여 기존 값 유지.
- `KyoboData.list_price` 신규 필드 추가 + 마이그레이션: `DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)` 필드 추가. 헤더에 `교보 정가` 컬럼 존재 시에만 defaults에 포함, 없으면 기존 값 유지.
- `Yes24Data` 필드 매핑: `YES24 공급가`→`price`, `YES24 재고상태`→`status`만 업데이트. `list_price`는 명시적으로 defaults에서 제외(SPEC-006 보호).

### 구현 범위 vs 계획 범위 검증 (Scope Drift)

계획 단계 tasks.md의 T-001~T-010이 모두 구현됨. 변경 파일 목록이 정확히 일치:
- ✅ `backend/order/models.py`: `KyoboData.list_price` 필드 추가
- ✅ `backend/order/migrations/0028_kyobodata_list_price.py`: 신규 마이그레이션 생성
- ✅ `backend/order/excel_utils.py`: 헤더 탐지, SKU 이중 지원, 신 템플릿 컬럼 파싱, `_DISTRIBUTOR_LABEL_MAP` 확장
- ✅ `backend/order/purchase_order_views.py`: `UploadDailyReviewView` YES24/창고/벤더 upsert 로직 추가
- ✅ `backend/order/tests/test_daily_review_upload.py`: REQ-PO8-* 관련 신규 테스트 케이스 추가

**Scope drift: 0% — 계획 범위 내에서 정확히 구현됨.**

### 품질 게이트 이력

| 단계 | 결과 | 상세 |
|------|------|------|
| TRUST 5 (manager-quality) | PASS | 기본 품질 검증 통과 |
| evaluator-active (cycle 1) | FAIL | 3개 버그 발견: (1) OverflowError 처리 누락, (2) 레거시 형식 데이터 손실, (3) 북센 공급가 헤더 파싱 회귀 |
| Fix 사이클 2 | - | 4개 버그 수정 (Bug1=CRITICAL, Bug2/3=HIGH, Bug4=MEDIUM) |
| evaluator-active (cycle 2) | PASS | 모든 4개 차원 통과, 73개 테스트 모두 통과 |
| 최종 상태 | ✅ DONE | 마이그레이션 적용, 모든 테스트 통과, MX 태그 적용 |

### 구현 중 발견·수정된 버그 (예상하지 못한 엣지 케이스)

1. **CRITICAL — OverflowError on "inf" input** (bug_id: PO8-BUG-001)
   - 위치: `backend/order/excel_utils.py` `parse_daily_review_excel()` 벤더 가격 float 변환 로직
   - 원인: 신 템플릿에서 계산 오류로 인해 일부 공급가 셀에 "inf" 문자열이 저장됨. `float("inf")`는 성공하지만 Decimal 변환 시 OverflowError 발생.
   - 수정: float 변환 후 `math.isinf()` 검사 추가, 이상값 0.00으로 처리.

2. **HIGH — Legacy format data loss (vendor table wiped to None)** (bug_id: PO8-BUG-002)
   - 위치: `backend/order/purchase_order_views.py` `UploadDailyReviewView.post()` 벤더 upsert 로직
   - 원인: 구 형식 파일 업로드 시 신 템플릿 컬럼명(`BOOXEN 공급가` 등)을 찾지 못하면 키 누락이 아닌 None으로 설정되어, 기존 벤더 데이터 가격이 우발적으로 NULL로 갱신됨.
   - 수정: upsert defaults dict 빌드 시 값이 실제로 파싱된 경우에만 키 포함 (느슨한 dict 구성).

3. **HIGH — Legacy "북센 공급가" header parsing regression** (bug_id: PO8-BUG-003)
   - 위치: `backend/order/excel_utils.py` `_DISTRIBUTOR_LABEL_MAP` 확인
   - 원인: 기존 구 형식 파일의 벤더 컬럼 헤더명이 정확히 파싱되지 않아 bs_price가 None으로 기록됨. DISTRIBUTOR_LABEL_MAP의 "BOOXEN"→"booxen" 매핑이 없었음 (기존에는 선택 값 기반 분기만 사용).
   - 수정: `_DISTRIBUTOR_LABEL_MAP`에 `"BOOXEN"`→`"booxen"`, `"교보"`→`"kyobo"` 매핑 추가 (벤더 컬럼 헤더 파싱 용도).

4. **MEDIUM — Missing test coverage for 교보 반품가능여부 Y/N mapping** (bug_id: PO8-BUG-004)
   - 위치: `backend/order/tests/test_daily_review_upload.py`
   - 원인: 신 템플릿의 `교보 반품가능여부` 컬럼 값 `Y`/`N`을 `returnable` boolean으로 매핑하는 로직이 테스트되지 않음.
   - 수정: AC-011 관련 테스트 케이스 추가 (`Y`→`True`, 그 외→`False`).

### 베이스라인 대비 변화 없음

- ✅ 구 형식(자체 생성 포맷) 다운로드 로직 및 생성 헤더(`_DAILY_REVIEW_HEADERS`) 무변경
- ✅ 기존 `test_daily_review_upload.py` 모든 테스트 무변경 통과 (SPEC-005/007 관련 케이스 포함)
- ✅ `Yes24Data.list_price` SPEC-006 보호 유지 (이 업로드 경로에서 미변경)
- ✅ `KyoboData.ordered_qty`/`total_price` 필드 미변경
