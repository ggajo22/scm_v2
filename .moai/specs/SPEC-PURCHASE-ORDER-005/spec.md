---
id: SPEC-PURCHASE-ORDER-005
version: 1.0.0
status: draft
created: 2026-06-24
updated: 2026-06-24
author: ggajo
priority: High
issue_number: ~
---

# Daily Review 업로드 확장 — 창고재고 차감 및 공급사별 주문파일 다운로드

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-24 | ggajo | 최초 작성 |

---

## 문제 정의

현재 Daily Review 업로드(`UploadDailyReviewView`)는 `선택` 컬럼과 `메모` 컬럼만 읽어 공급사 PurchaseOrder를 생성한다. 아래 두 가지 기능이 누락되어 있다.

1. **창고 재고 선택 미지원**: `선택` 컬럼에 "재고(한국)", "재고(CA)", "재고(NJ)"를 입력해도 이를 인식하지 못한다. 창고 재고로 충당 가능한 주문을 업로드 시점에 처리하고 `WarehouseStock`에서 해당 수량을 즉시 차감해야 한다.

2. **공급사별 최종 주문파일 생성 불가**: 업로드 확정 후 어느 공급사에 얼마나 발주해야 하는지 알 수 있지만, 공급사별 Excel 주문파일을 Daily Review 탭에서 바로 다운로드할 수 없다. 현재 `GenerateOrderFileView`는 이미 존재하나, 업로드 응답이 공급사별 SKU 데이터를 반환하지 않아 프론트엔드에서 연결할 수 없다.

---

## 솔루션 개요

- `_DISTRIBUTOR_LABEL_MAP`에 창고 코드 3종 추가 (`"warehouse_korea"`, `"warehouse_ca"`, `"warehouse_nj"`)
- `UploadDailyReviewView`에서 창고 코드 감지 시 `WarehouseStock` 수량 차감 + `LineItem.purchase_status="in_stock"` 설정 (PO 생성 없음)
- 업로드 응답에 `confirmed_by_distributor` 필드 추가 (공급사 코드 → SKU/수량 목록)
- `generate_daily_review_excel()`에서 "창고재고수량"/"창고재고위치" 컬럼을 "재고(한국)"/"재고(CA)"/"재고(NJ)" 3개 컬럼으로 분리
- 기존 `GenerateOrderFileView`에 창고 코드를 허용하는 `VALID_DISTRIBUTORS` 확장
- 프론트엔드 `DailyReviewTab`에서 업로드 완료 후 공급사별 다운로드 버튼 표시

---

## 범위

### 포함

- `excel_utils.py`: `_DISTRIBUTOR_LABEL_MAP` 확장, Daily Review 헤더 컬럼 재정의, 행 데이터 생성 로직 수정
- `purchase_order_views.py`: `UploadDailyReviewView` 창고 처리 로직, `GenerateOrderFileView` VALID_DISTRIBUTORS 확장, 업로드 응답 구조 변경
- `DailyReviewTab.tsx`: 업로드 완료 후 공급사별 다운로드 버튼 렌더링
- `purchaseOrderApi.ts`: 업로드 응답 타입 업데이트

### 제외

- 새로운 Django 모델 추가 없음
- DB 마이그레이션 없음 (기존 `WarehouseStock` 모델 재사용)
- 창고 재고 초과 차감에 대한 별도 알림 UI (경고는 콘솔 로그로만 기록)
- 업로드 이력 추적 기능
- 주문파일 이메일 발송 기능

---

## 요구사항

### REQ-PO5-001 — 창고 배급사 레이블 매핑 추가

When `_DISTRIBUTOR_LABEL_MAP`이 참조될 때,
the system shall "재고(한국)" → `"warehouse_korea"`, "재고(CA)" → `"warehouse_ca"`, "재고(NJ)" → `"warehouse_nj"` 매핑을 포함해야 한다.

- 대상 파일: `backend/order/excel_utils.py`
- 기존 5개 매핑 유지

---

### REQ-PO5-002 — Daily Review Excel 헤더 컬럼 재정의

When `generate_daily_review_excel()`이 호출될 때,
the system shall 기존 "창고재고수량"과 "창고재고위치" 2개 컬럼 대신 "재고(한국)", "재고(CA)", "재고(NJ)" 3개 컬럼을 생성해야 한다.

- 컬럼 순서: ... "메모", "재고(한국)", "재고(CA)", "재고(NJ)", "북센 공급가", ...
- 각 셀 값: 해당 location의 `WarehouseStock.quantity` (레코드 없으면 0)
- `_DAILY_REVIEW_HEADERS` 상수를 새 컬럼 목록으로 업데이트

---

### REQ-PO5-003 — Daily Review 행 데이터 생성 로직 수정

When `generate_daily_review_excel()`이 행을 생성할 때,
the system shall 각 ISBN별 `WarehouseStock`을 location별로 조회하여 "재고(한국)", "재고(CA)", "재고(NJ)" 셀에 각각 채워야 한다.

- MySQL 8.0 호환 쿼리 사용
- `WarehouseStock.objects.filter(isbn__in=sku_list)` 로 사전 로딩 후 매핑 (N+1 쿼리 방지)

---

### REQ-PO5-004 — 업로드 시 창고 선택 항목 감지

When `UploadDailyReviewView.post()`가 `선택` 컬럼을 파싱할 때,
the system shall 매핑 결과가 `"warehouse_korea"`, `"warehouse_ca"`, `"warehouse_nj"` 중 하나인 경우 이를 창고 처리 경로로 분기해야 한다.

- 분기 조건: `distributor_code.startswith("warehouse_")`
- 기존 공급사 경로(bookseen, kyobo 등)와 독립적으로 동작

---

### REQ-PO5-005 — 창고 재고 수량 차감

When 업로드 처리 중 창고 코드가 감지될 때,
the system shall 해당 `WarehouseStock` 레코드에서 `total_qty`만큼 차감해야 한다.

- location 매핑: `"warehouse_korea"` → `"korea"`, `"warehouse_ca"` → `"ca"`, `"warehouse_nj"` → `"nj"`
- 차감 쿼리:
  ```python
  from django.db.models import F
  WarehouseStock.objects.filter(isbn=sku, location=loc).update(
      quantity=Case(
          When(quantity__gte=qty, then=F('quantity') - qty),
          default=Value(0),
          output_field=IntegerField()
      )
  )
  ```
- 레코드가 존재하지 않을 경우: 차감 없이 처리 진행 (경고 로그 기록)
- 재고가 주문 수량보다 적을 경우: 0으로 설정 (floor at 0)

---

### REQ-PO5-006 — 창고 처리 LineItem 상태 설정

When 창고 선택 항목을 처리할 때,
the system shall 해당 `LineItem.purchase_status`를 `"in_stock"`으로 설정하고 공급사 `PurchaseOrder`를 생성하지 않아야 한다.

- `LineItem.purchase_status = "in_stock"` (SPEC-PURCHASE-ORDER-004에서 정의된 필드)
- `PurchaseOrder` 생성 없음
- `LineItem.note` 필드에 선택 배급사 코드 기록 (선택사항, 가능한 경우)

---

### REQ-PO5-007 — 업로드 응답에 confirmed_by_distributor 포함

When `UploadDailyReviewView.post()`가 성공적으로 완료될 때,
the system shall 응답 JSON에 `confirmed_by_distributor` 필드를 포함해야 한다.

- 타입: `dict[str, list[dict]]`
- 구조:
  ```json
  {
    "confirmed_by_distributor": {
      "bookseen": [
        {"sku": "9791234567890", "title": "도서명", "quantity": 3}
      ],
      "warehouse_korea": [
        {"sku": "9799876543210", "title": "도서명2", "quantity": 1}
      ]
    }
  }
  ```
- 업로드 세션에서 처리된 모든 공급사(창고 포함) 항목 포함
- 기존 응답 필드(`message`, `created_count` 등) 유지

---

### REQ-PO5-008 — GenerateOrderFileView에 창고 코드 허용

When `GenerateOrderFileView`가 `distributor` 파라미터를 검증할 때,
the system shall `"warehouse_korea"`, `"warehouse_ca"`, `"warehouse_nj"`를 유효한 배급사 코드로 허용해야 한다.

- `VALID_DISTRIBUTORS` 집합에 3개 창고 코드 추가
- 창고 코드에 대한 출력 형식: `["ISBN", "제목", "수량"]` (기타 공급사와 동일)
- bookseen/kyobo 기존 형식은 변경 없음

---

### REQ-PO5-009 — 프론트엔드 업로드 응답 타입 업데이트

When `purchaseOrderApi.ts`가 업로드 응답을 파싱할 때,
the system shall `confirmed_by_distributor` 필드를 올바르게 타입 선언해야 한다.

- 타입 정의:
  ```typescript
  interface SkuQuantity {
    sku: string;
    title: string;
    quantity: number;
  }

  interface UploadDailyReviewResponse {
    message: string;
    confirmed_by_distributor: Record<string, SkuQuantity[]>;
    // 기존 필드 유지
  }
  ```

---

### REQ-PO5-010 — 프론트엔드 공급사별 다운로드 버튼 표시

When 업로드가 성공적으로 완료된 후 `confirmed_by_distributor`가 비어있지 않을 때,
the system shall 각 공급사별 다운로드 버튼을 `DailyReviewTab`에 렌더링해야 한다.

- 버튼 레이블: 배급사 표시명 + "주문파일 다운로드" (예: "북센 주문파일 다운로드")
- 버튼 클릭 시: 기존 `useGenerateOrderFile` 훅을 사용하여 해당 공급사의 SKU 목록으로 파일 다운로드 요청
- 배급사 표시명 매핑:
  - `bookseen` → "북센"
  - `kyobo` → "교보"
  - `warehouse_korea` → "창고(한국)"
  - `warehouse_ca` → "창고(CA)"
  - `warehouse_nj` → "창고(NJ)"
  - `choeumgoyuk` → "처음교육"
  - `agape` → "아가페"
  - `sungseoyunion` → "성서유니온"
- 버튼은 업로드 완료 상태가 초기화될 때까지 유지

---

## 구현 범위 (수정·생성 대상 파일)

| 파일 | 변경 유형 | 변경 내용 요약 |
|------|-----------|----------------|
| `backend/order/excel_utils.py` | 수정 | `_DISTRIBUTOR_LABEL_MAP` 확장, `_DAILY_REVIEW_HEADERS` 재정의, 행 생성 로직 수정 (창고재고 3컬럼 분리) |
| `backend/order/purchase_order_views.py` | 수정 | `UploadDailyReviewView.post()` 창고 처리 분기 추가, `confirmed_by_distributor` 응답 반환, `VALID_DISTRIBUTORS` 확장 |
| `frontend/src/pages/PurchaseOrders/tabs/DailyReviewTab.tsx` | 수정 | 업로드 완료 후 공급사별 다운로드 버튼 렌더링 |
| `frontend/src/services/purchaseOrderApi.ts` | 수정 | 업로드 응답 타입 업데이트 (`confirmed_by_distributor` 필드 추가) |

---

## 제외 범위 (What NOT to Build)

- 새로운 Django 모델 또는 DB 마이그레이션 (WarehouseStock 기존 모델 그대로 사용)
- 창고별 재고 초과 경보 UI (백엔드 로그로만 처리)
- 업로드 이력 또는 감사 로그 테이블
- 공급사 주문파일 이메일 자동 발송
- Daily Review 다운로드 시 "재고(한국/CA/NJ)" 컬럼 값이 선택 컬럼에 자동 반영되는 로직

---

## 인수 조건

### AC-001 — 창고 레이블 매핑 인식

**Given** Daily Review Excel 파일의 `선택` 컬럼에 "재고(한국)"이 입력되어 있을 때  
**When** `UploadDailyReviewView`가 파일을 처리하면  
**Then** 해당 항목이 창고 처리 경로로 분기되어야 하며, 공급사 PurchaseOrder가 생성되지 않아야 한다

---

### AC-002 — 창고 재고 차감

**Given** "재고(CA)"가 선택된 ISBN=`9791234567890`, 주문수량=2인 항목이 있고, `WarehouseStock(isbn="9791234567890", location="ca", quantity=5)`가 존재할 때  
**When** 업로드를 실행하면  
**Then** `WarehouseStock.quantity`가 3(`5 - 2`)으로 업데이트되어야 한다

---

### AC-003 — 창고 재고 부족 시 floor at 0

**Given** "재고(NJ)"가 선택된 ISBN=`9799876543210`, 주문수량=5인 항목이 있고, `WarehouseStock(isbn="9799876543210", location="nj", quantity=2)`가 존재할 때  
**When** 업로드를 실행하면  
**Then** `WarehouseStock.quantity`가 0으로 설정되어야 하며 오류 없이 처리되어야 한다

---

### AC-004 — LineItem 상태 in_stock 설정

**Given** "재고(한국)"이 선택된 항목이 포함된 Daily Review 파일이 업로드될 때  
**When** 업로드가 완료되면  
**Then** 해당 `LineItem.purchase_status`가 `"in_stock"`이어야 한다

---

### AC-005 — 업로드 응답에 confirmed_by_distributor 포함

**Given** Daily Review 파일에 북센 2건, 창고(한국) 1건이 선택된 상태로 업로드될 때  
**When** 업로드 API가 응답하면  
**Then** 응답 JSON에 `confirmed_by_distributor` 키가 있어야 하고, `"bookseen"` 키 아래 2개 항목, `"warehouse_korea"` 키 아래 1개 항목이 포함되어야 한다

---

### AC-006 — Daily Review 다운로드 헤더 확인

**Given** 여러 ISBN의 창고재고 데이터가 존재할 때  
**When** `DailyReviewExcelView`로 Daily Review Excel을 다운로드하면  
**Then** Excel 헤더에 "창고재고수량"과 "창고재고위치" 컬럼이 없고, "재고(한국)", "재고(CA)", "재고(NJ)" 컬럼이 각각 존재해야 한다

---

### AC-007 — Daily Review 다운로드 재고값 정확성

**Given** `WarehouseStock(isbn="9791234567890", location="korea", quantity=10)`, `WarehouseStock(isbn="9791234567890", location="ca", quantity=3)`, NJ 레코드 없음일 때  
**When** Daily Review Excel을 다운로드하면  
**Then** 해당 ISBN 행의 "재고(한국)"=10, "재고(CA)"=3, "재고(NJ)"=0이어야 한다

---

### AC-008 — 창고 코드로 GenerateOrderFileView 호출 성공

**Given** `distributor="warehouse_korea"`와 SKU 목록이 요청 바디에 포함될 때  
**When** `POST /api/purchase-orders/generate-order-file/`를 호출하면  
**Then** 400 에러 없이 Excel 파일이 반환되어야 하며, 헤더가 `["ISBN", "제목", "수량"]`이어야 한다

---

### AC-009 — 프론트엔드 다운로드 버튼 렌더링

**Given** 업로드가 성공하고 응답에 `confirmed_by_distributor: {"bookseen": [...], "kyobo": [...]}`가 포함될 때  
**When** DailyReviewTab이 렌더링되면  
**Then** "북센 주문파일 다운로드" 버튼과 "교보 주문파일 다운로드" 버튼이 화면에 표시되어야 한다

---

### AC-010 — 프론트엔드 다운로드 버튼 동작

**Given** AC-009 조건에서 "북센 주문파일 다운로드" 버튼을 클릭할 때  
**When** 버튼이 클릭되면  
**Then** `useGenerateOrderFile` 훅이 `distributor="bookseen"`과 해당 SKU 목록으로 호출되어 Excel 파일 다운로드가 시작되어야 한다
