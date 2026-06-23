---
id: SPEC-PURCHASE-ORDER-001
version: 1.2.0
status: draft
created: 2026-06-21
updated: 2026-06-23
author: ggajo
priority: High
issue_number: ~
---

# 발주(Purchase Order) 관리 시스템

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-21 | ggajo | 최초 작성 — 발주 관리 시스템 SPEC 초안 |
| 1.1.0 | 2026-06-23 | ggajo | 업체 자료 업로드/비교 흐름 분리 — 업로드는 데이터 저장만, 비교는 별도 run-comparison 엔드포인트로 분리; 프론트엔드 distributor 값 매핑(북센↔bookseen, 교보↔kyobo) 명세 추가 |
| 1.2.0 | 2026-06-23 | ggajo | 확정 가격 이력 보존 — 비교 실행 시 LineItem에 confirmed_price/confirmed_distributor/confirmed_at 기록; 가격 재업로드 후에도 기존 LineItem 확정 가격 유지 |

---

## 문제 정의

현재 SCM v2는 Shopify 고객 주문(Order)을 수집하여 조회하는 기능(`SPEC-ORDER-001`)은 갖추고 있으나, 해당 주문에 포함된 도서 상품을 **유통사(발주처)에 실제로 발주**하는 흐름을 관리하는 수단이 없다.

관리자는 현재:
- 발주가 필요한 LineItem을 수동으로 파악해야 함
- 북센·교보 등 유통사에 제출할 발주 파일을 별도 엑셀로 수동 작성
- 유통사에서 받은 재고/단가 파일을 수작업으로 비교하여 발주처를 결정
- 발주 완료 여부를 별도 문서로 추적

이로 인해 발주 누락, 이중 발주, 처리 지연이 발생하며, 발주 이력이 시스템에 남지 않아 추적 불가능 상태이다.

---

## 솔루션 개요

기존 `order` 앱의 `LineItem` 모델을 기반으로 **발주 관리 워크플로우**를 구현한다.

1. **미발주 현황 파악** — `PurchaseOrder`와 연결되지 않은 `LineItem`을 SKU 단위로 집계하여 표시
2. **발주 파일 생성** — 북센·교보 제출용 Excel 파일 자동 생성
3. **업체 자료 업로드 및 비교** — 유통사가 회신한 재고/단가 Excel을 업로드하면 자동 비교·추천
4. **발주 확정** — 발주처 선택 후 `PurchaseOrder` 레코드 생성 및 `LineItem` 연결
5. **발주처 규칙 관리** — 출판사(vendor) → 발주처(처음교육/아가페) 자동 라우팅 규칙 설정

---

## 도메인 개념 정의

| 용어 | 정의 |
|------|------|
| 미발주 LineItem | `PurchaseOrder`와 M2M 관계가 없는 `LineItem`. 아직 유통사에 발주하지 않은 주문 상품. |
| 발주처 | 도서를 공급받는 유통사. 북센(Bookseen), 교보(Kyobo), 처음교육, 아가페 |
| 발주 파일 | 북센 또는 교보에 제출하기 위해 생성하는 Excel(.xlsx) 파일 (ISBN, 제목, 수량 포함) |
| 업체 자료 | 북센/교보가 회신하는 Excel 파일 (재고 여부, 단가 포함) |
| 발주 확정 | 발주처를 결정하고 `PurchaseOrder` 레코드를 생성하는 행위 |
| 발주처 규칙 | 출판사명(LineItem.vendor) → 발주처(처음교육/아가페)를 자동 매핑하는 규칙 |

---

## 요구사항

### 인증

**REQ-PO-001** (Ubiquitous)
The 발주 관련 모든 API endpoint **shall** JWT 인증(`JWTAuthentication + IsAuthenticated`)을 요구한다.

**REQ-PO-002** (Unwanted Behavior)
**If** 요청에 유효한 JWT 토큰이 없거나 만료된 경우, **then** the API **shall** HTTP 401 Unauthorized를 반환한다.

---

### 미발주 현황 조회

**REQ-PO-010** (Ubiquitous)
The 시스템 **shall** `GET /api/purchase-orders/unordered/` 엔드포인트를 제공하며, `PurchaseOrder`에 연결되지 않은 `LineItem`을 SKU 단위로 집계하여 반환한다.

**REQ-PO-011** (Ubiquitous)
The 미발주 현황 응답 **shall** SKU별로 `sku`, `title`, `vendor`(출판사), `total_quantity`(필요 수량 합계), `order_count`(관련 주문 수), `auto_distributor`(규칙 기반 자동 추천 발주처 또는 `null`) 필드를 포함한다.

**REQ-PO-012** (Ubiquitous)
The 시스템 **shall** `DistributorVendorRule`에 등록된 출판사명과 `LineItem.vendor`가 일치하는 경우 해당 발주처를 `auto_distributor`로 반환한다.

**REQ-PO-013** (Unwanted Behavior)
**If** 미발주 `LineItem`이 존재하지 않는 경우, **then** the API **shall** 빈 배열(`[]`)을 반환한다.

---

### 발주 파일 생성 (북센/교보)

**REQ-PO-020** (Event-Driven)
**When** 관리자가 `POST /api/purchase-orders/generate-order-file/`을 호출하면, the 시스템 **shall** 요청된 SKU 목록에 대해 Excel(.xlsx) 파일을 생성하여 반환한다.

**REQ-PO-021** (Ubiquitous)
The 생성된 발주 파일 **shall** 헤더(`ISBN`, `도서명`, `수량`) 행을 포함하며, 각 행에 SKU(ISBN), 도서명, 수량을 기재한다.

**REQ-PO-022** (Ubiquitous)
The `generate-order-file` 요청 **shall** `distributor`(bookseen 또는 kyobo)와 `skus`(SKU 목록 배열) 필드를 필수로 포함한다.

**REQ-PO-023** (Unwanted Behavior)
**If** `skus` 배열이 비어 있거나 `distributor`가 유효하지 않은 값인 경우, **then** the API **shall** HTTP 400 Bad Request를 반환한다.

**REQ-PO-024** (Unwanted Behavior)
**If** 요청된 SKU 중 미발주 `LineItem`에 존재하지 않는 SKU가 포함된 경우, **then** the 시스템 **shall** 해당 SKU를 응답의 `unknown_skus` 필드에 포함하여 경고하되 파일 생성은 계속 진행한다.

---

### 업체 자료 업로드 및 비교

**REQ-PO-030** (Event-Driven)
**When** 관리자가 `POST /api/purchase-orders/upload-vendor-file/`에 Excel 파일을 업로드하면, the 시스템 **shall** 파일을 파싱하여 SKU별 재고 여부와 단가를 `VendorComparison` 레코드에 저장한다.

**REQ-PO-031** (Ubiquitous)
The 업로드 요청 **shall** `distributor`(bookseen 또는 kyobo)와 `file`(Excel 파일) 필드를 포함하는 multipart/form-data 형식이어야 한다.

**REQ-PO-032** (Ubiquitous)
The 업체 자료 파싱 **shall** Excel 파일의 각 행에서 ISBN(SKU), 재고 여부(Boolean), 단가(숫자) 컬럼을 추출한다.

**REQ-PO-033** (Ubiquitous)
The `POST /api/purchase-orders/upload-vendor-file/` 응답 **shall** `parsed_count`(저장된 행 수)와 `distributor` 필드만 포함한다. 업로드 시점에는 발주처 자동 선택 로직을 실행하지 않는다.

**REQ-PO-034** (Event-Driven)
**When** 관리자가 `POST /api/purchase-orders/run-comparison/`을 호출하면, the 시스템 **shall** 현재 미발주 상태(`purchase_status="unordered"`)인 `LineItem`을 SKU별로 집계하고, 각 SKU의 `VendorComparison` 데이터와 매칭하여 `auto_select_distributor()`를 실행한 후 결과를 `VendorComparison`에 저장하고 반환한다.

**REQ-PO-034a** (Ubiquitous)
The `run-comparison` 응답 **shall** SKU별로 `sku`, `title`, `total_qty`(미발주 수량 합계), `line_items`(매칭된 주문 목록 — id, order_name, quantity), 북센/교보 재고·단가, `selected_distributor`, `candidate_basis`, `price_diff`, `price_diff_alert`, `confirmed_price`, `confirmed_distributor` 필드를 포함한다.

**REQ-PO-034c** (Event-Driven)
**When** `POST /api/purchase-orders/run-comparison/`이 실행되면, the 시스템 **shall** 해당 SKU의 미발주 `LineItem` 전체에 `confirmed_price`(선택된 배급사의 단가), `confirmed_distributor`(선택된 배급사 키), `confirmed_at`(실행 시각)을 저장한다. 이 값은 이후 업체 자료가 재업로드되더라도 변경되지 않으며, 비교를 다시 실행할 때만 갱신된다.

**REQ-PO-034d** (Ubiquitous)
The `업체 자료 업로드` 탭의 비교 결과 테이블 **shall** "확정 단가" 컬럼을 포함하여, 비교 실행 시점에 기록된 `confirmed_price`를 표시한다.

**REQ-PO-034b** (Ubiquitous)
The `GET /api/purchase-orders/comparison/` 엔드포인트 **shall** 현재 저장된 `VendorComparison` 레코드를 SKU별로 반환하며, 북센 재고/단가, 교보 재고/단가, 자동 선택된 발주처를 포함한다.

**REQ-PO-035** (Unwanted Behavior)
**If** 업로드된 파일이 Excel 형식(.xlsx, .xls)이 아닌 경우, **then** the API **shall** HTTP 400 Bad Request를 반환한다.

**REQ-PO-036** (Unwanted Behavior)
**If** 업로드된 Excel 파일에서 필수 컬럼(ISBN, 재고 여부, 단가)을 찾을 수 없는 경우, **then** the API **shall** HTTP 422 Unprocessable Entity를 반환하고 누락된 컬럼 정보를 응답에 포함한다.

**REQ-PO-037** (Ubiquitous)
The 프론트엔드 **shall** 유통사 선택 드롭다운 값(`'북센'`, `'교보'`)을 API 전송 시 각각 `'bookseen'`, `'kyobo'`로 변환한다. UI 표시와 API 값은 분리된다.

---

### 발주 확정

**REQ-PO-040** (Event-Driven)
**When** 관리자가 `POST /api/purchase-orders/confirm/`을 호출하면, the 시스템 **shall** 요청된 항목별로 `PurchaseOrder` 레코드를 생성하고, 해당 SKU의 미발주 `LineItem`과 M2M 관계로 연결한다.

**REQ-PO-041** (Ubiquitous)
The `confirm` 요청 **shall** `items` 배열을 포함하며, 각 항목은 `sku`, `distributor`, `quantity`, `unit_price`(선택) 필드를 가진다.

**REQ-PO-042** (Ubiquitous)
The 생성된 `PurchaseOrder` **shall** 초기 `status`를 `"pending"`으로 설정한다.

**REQ-PO-043** (Unwanted Behavior)
**If** `confirm` 요청의 `sku`에 해당하는 미발주 `LineItem`이 없는 경우, **then** the API **shall** HTTP 400 Bad Request를 반환하고 해당 SKU를 오류 메시지에 포함한다.

**REQ-PO-044** (Unwanted Behavior)
**If** 이미 `PurchaseOrder`에 연결된 `LineItem`을 다시 `confirm` 요청에 포함하는 경우, **then** the 시스템 **shall** HTTP 409 Conflict를 반환한다.

---

### 발주처 규칙 관리

**REQ-PO-050** (Ubiquitous)
The 시스템 **shall** `GET /api/purchase-orders/vendor-rules/` 엔드포인트를 제공하여 `DistributorVendorRule` 목록을 반환한다.

**REQ-PO-051** (Event-Driven)
**When** 관리자가 `POST /api/purchase-orders/vendor-rules/`를 호출하면, the 시스템 **shall** 새로운 `DistributorVendorRule`을 생성한다.

**REQ-PO-052** (Ubiquitous)
The `DistributorVendorRule` 생성 요청 **shall** `publisher_name`과 `distributor`(choeumgoyuk 또는 agape) 필드를 필수로 포함한다.

**REQ-PO-053** (Unwanted Behavior)
**If** 동일한 `publisher_name`의 규칙이 이미 존재하는 경우, **then** the API **shall** HTTP 409 Conflict를 반환한다.

**REQ-PO-054** (Event-Driven)
**When** 관리자가 `DELETE /api/purchase-orders/vendor-rules/{id}/`를 호출하면, the 시스템 **shall** 해당 규칙을 삭제한다.

---

### 발주 목록 조회

**REQ-PO-060** (Ubiquitous)
The `GET /api/purchase-orders/` 엔드포인트 **shall** 생성된 `PurchaseOrder` 목록을 `created_at` 내림차순으로 반환하며, `distributor`, `status`, `created_at` 기준 필터링을 지원한다.

**REQ-PO-061** (Ubiquitous)
The 발주 목록 응답 **shall** DRF 표준 페이지네이션 포맷(`count`, `next`, `previous`, `results`)을 따르며, 페이지당 50건을 반환한다.

---

### 프론트엔드 — 발주 관리 페이지

**REQ-PO-070** (Ubiquitous)
The 프론트엔드 **shall** `/purchase-orders` 경로에 발주 관리 페이지를 제공하며, 사이드바 네비게이션에 "발주 관리" 항목을 추가한다.

**REQ-PO-071** (Ubiquitous)
The 발주 관리 페이지 **shall** 다음 6개 탭을 제공한다: `미발주 현황`, `발주 파일 생성`, `업체 자료 업로드`, `발주 확정`, `발주 이력`, `발주처 규칙 설정`.

**REQ-PO-072** (Ubiquitous)
The `미발주 현황` 탭 **shall** SKU별로 집계된 미발주 항목 테이블을 표시하며, SKU, 도서명, 출판사, 필요 수량, 관련 주문 수, 자동 추천 발주처 컬럼을 포함한다.

**REQ-PO-073** (Ubiquitous)
The `미발주 현황` 탭 **shall** 항목 선택(체크박스) 기능을 제공하며, 선택된 항목에 대해 "북센 발주 파일 생성" 또는 "교보 발주 파일 생성" 버튼을 활성화한다.

**REQ-PO-074** (Event-Driven)
**When** 발주 파일 생성 버튼을 클릭하면, the 시스템 **shall** 선택된 SKU 목록과 유통사 정보로 `POST /api/purchase-orders/generate-order-file/`을 호출하고 응답으로 받은 Excel 파일을 브라우저에서 다운로드한다.

**REQ-PO-075** (Ubiquitous)
The `업체 자료 업로드` 탭 **shall** 파일 업로드 영역(drag-and-drop 또는 파일 선택), 유통사 선택 드롭다운(북센/교보), 업로드 완료 후 파싱 건수 표시, "비교 실행" 버튼을 제공한다.

**REQ-PO-076** (Event-Driven)
**When** 업체 자료 업로드가 완료되면, the 시스템 **shall** 파싱된 건수(`parsed_count`)를 화면에 표시한다. 비교 결과는 표시하지 않는다.

**REQ-PO-076a** (Event-Driven)
**When** 관리자가 "비교 실행" 버튼을 클릭하면, the 시스템 **shall** `POST /api/purchase-orders/run-comparison/`을 호출하고, 결과를 테이블로 표시한다. 테이블은 SKU별로 매칭된 미발주 주문 목록(order_name × quantity), 북센/교보 재고·단가, 자동 선택 발주처, 선택 근거(candidate_basis)를 포함한다.

**REQ-PO-077** (Event-Driven)
**When** "발주 확정 탭으로 이동" 버튼을 클릭하면, the 시스템 **shall** 비교 결과의 `selected_distributor`와 `total_qty`를 기반으로 발주 확정 탭의 항목 목록을 채운다.

**REQ-PO-078** (Event-Driven)
**When** `발주 확정` 탭에서 확정 버튼을 클릭하면, the 시스템 **shall** 선택된 항목에 대해 `POST /api/purchase-orders/confirm/`을 호출하고, 성공 시 토스트 메시지를 표시하며 미발주 현황 탭을 자동으로 새로고침한다.

**REQ-PO-079** (Ubiquitous)
The `발주 이력` 탭 **shall** 확정된 `PurchaseOrder` 목록을 테이블로 표시하며, 발주처, 도서명/SKU, 수량, 단가, 상태, 발주일시 컬럼을 포함한다.

**REQ-PO-080** (Ubiquitous)
The `발주처 규칙 설정` 탭 **shall** 현재 등록된 규칙 목록을 표시하고, 새 규칙 추가(출판사명 + 발주처 선택) 및 기존 규칙 삭제 기능을 제공한다.

**REQ-PO-081** (State-Driven)
**While** 데이터를 로딩 중인 경우, the 각 탭의 테이블 **shall** 로딩 스켈레톤 또는 스피너를 표시한다.

**REQ-PO-082** (Unwanted Behavior)
**If** API 호출 중 오류가 발생하면, **then** the 시스템 **shall** 오류 내용을 토스트 메시지 또는 인라인 에러 메시지로 사용자에게 표시한다.

---

## DB 스키마 설계

### 신규 모델 — PurchaseOrder

```python
class PurchaseOrder(models.Model):
    DISTRIBUTOR_CHOICES = [
        ("bookseen", "북센"),
        ("kyobo", "교보"),
        ("choeumgoyuk", "처음교육"),
        ("agape", "아가페"),
    ]
    STATUS_CHOICES = [
        ("pending", "발주 대기"),
        ("confirmed", "발주 확정"),
        ("cancelled", "취소"),
    ]

    sku = models.CharField(max_length=255)
    title = models.CharField(max_length=500)
    distributor = models.CharField(max_length=20, choices=DISTRIBUTOR_CHOICES)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    line_items = models.ManyToManyField("LineItem", related_name="purchase_orders", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_purchaseorder"
        indexes = [
            models.Index(fields=["distributor"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["sku"]),
        ]
```

### 신규 모델 — VendorComparison

```python
class VendorComparison(models.Model):
    DISTRIBUTOR_CHOICES = [
        ("bookseen", "북센"),
        ("kyobo", "교보"),
    ]

    sku = models.CharField(max_length=255)
    bookseen_available = models.BooleanField(null=True, blank=True)
    bookseen_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    kyobo_available = models.BooleanField(null=True, blank=True)
    kyobo_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    selected_distributor = models.CharField(max_length=20, choices=DISTRIBUTOR_CHOICES, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_vendorcomparison"
        unique_together = [("sku",)]
        indexes = [
            models.Index(fields=["sku"]),
        ]
```

### 신규 모델 — DistributorVendorRule

```python
class DistributorVendorRule(models.Model):
    SECONDARY_DISTRIBUTOR_CHOICES = [
        ("choeumgoyuk", "처음교육"),
        ("agape", "아가페"),
    ]

    publisher_name = models.CharField(max_length=255, unique=True)
    distributor = models.CharField(max_length=20, choices=SECONDARY_DISTRIBUTOR_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders_distributorvendorrule"
        indexes = [
            models.Index(fields=["publisher_name"]),
        ]
```

### 기존 모델 변경 없음

`LineItem` 모델에 직접 필드를 추가하지 않는다. `PurchaseOrder.line_items` M2M 관계를 통해 발주 여부를 판단한다.

---

## API 명세

### GET /api/purchase-orders/unordered/

**요청**
```
GET /api/purchase-orders/unordered/
Authorization: Bearer <access_token>
```

**성공 응답 (HTTP 200)**
```json
{
  "count": 15,
  "results": [
    {
      "sku": "9788901234567",
      "title": "그레이트 개츠비",
      "vendor": "처음교육",
      "total_quantity": 5,
      "order_count": 3,
      "auto_distributor": "choeumgoyuk"
    },
    {
      "sku": "9788901234568",
      "title": "어린 왕자",
      "vendor": "문학동네",
      "total_quantity": 2,
      "order_count": 1,
      "auto_distributor": null
    }
  ]
}
```

---

### POST /api/purchase-orders/generate-order-file/

**요청**
```
POST /api/purchase-orders/generate-order-file/
Authorization: Bearer <access_token>
Content-Type: application/json
```
```json
{
  "distributor": "bookseen",
  "skus": ["9788901234567", "9788901234568"]
}
```

**성공 응답 (HTTP 200)**
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: `attachment; filename="bookseen_order_20260621.xlsx"`
- 응답 바디: Excel 파일 바이너리

**경고 포함 응답 (HTTP 200 + unknown_skus)**
```json
{
  "warning": "일부 SKU가 미발주 목록에 없습니다.",
  "unknown_skus": ["9780000000000"],
  "file_url": "/api/purchase-orders/generate-order-file/download/abc123"
}
```

---

### POST /api/purchase-orders/upload-vendor-file/

**요청**
```
POST /api/purchase-orders/upload-vendor-file/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```
```
distributor=bookseen
file=<xlsx 파일>
```

**성공 응답 (HTTP 200)**
```json
{
  "parsed_count": 20,
  "distributor": "bookseen"
}
```

---

### POST /api/purchase-orders/run-comparison/

**요청**
```
POST /api/purchase-orders/run-comparison/
Authorization: Bearer <access_token>
```
(요청 바디 없음)

**성공 응답 (HTTP 200)**
```json
{
  "count": 2,
  "results": [
    {
      "sku": "9788901234567",
      "title": "그레이트 개츠비",
      "total_qty": 5,
      "line_items": [
        {"id": 101, "order_name": "#1001", "quantity": 3},
        {"id": 102, "order_name": "#1002", "quantity": 2}
      ],
      "bookseen_available": true,
      "bookseen_price": "12000.00",
      "bookseen_stock": 20,
      "kyobo_available": true,
      "kyobo_price": "11500.00",
      "kyobo_stock": 15,
      "selected_distributor": "kyobo",
      "candidate_basis": "양사재고/교보저가",
      "price_diff": "500.00",
      "price_diff_alert": false,
      "confirmed_price": "11500.00",
      "confirmed_distributor": "kyobo"
    }
  ]
}
```

**미발주 LineItem 없음 응답 (HTTP 200)**
```json
{ "count": 0, "results": [] }
```

---

### GET /api/purchase-orders/comparison/

**요청**
```
GET /api/purchase-orders/comparison/
Authorization: Bearer <access_token>
```

**성공 응답 (HTTP 200)**
```json
{
  "count": 5,
  "results": [
    {
      "sku": "9788901234567",
      "title": "그레이트 개츠비",
      "bookseen_available": true,
      "bookseen_price": "12000.00",
      "kyobo_available": true,
      "kyobo_price": "11500.00",
      "selected_distributor": "kyobo"
    }
  ]
}
```

---

### POST /api/purchase-orders/confirm/

**요청**
```
POST /api/purchase-orders/confirm/
Authorization: Bearer <access_token>
Content-Type: application/json
```
```json
{
  "items": [
    {
      "sku": "9788901234567",
      "distributor": "kyobo",
      "quantity": 5,
      "unit_price": "11500.00"
    },
    {
      "sku": "9788901234569",
      "distributor": "choeumgoyuk",
      "quantity": 2,
      "unit_price": null
    }
  ]
}
```

**성공 응답 (HTTP 201)**
```json
{
  "created_count": 2,
  "purchase_order_ids": [101, 102]
}
```

---

### GET /api/purchase-orders/vendor-rules/

**성공 응답 (HTTP 200)**
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "publisher_name": "처음교육",
      "distributor": "choeumgoyuk",
      "created_at": "2026-06-21T09:00:00+09:00"
    }
  ]
}
```

---

### POST /api/purchase-orders/vendor-rules/

**요청**
```json
{
  "publisher_name": "아가페출판사",
  "distributor": "agape"
}
```

**성공 응답 (HTTP 201)**
```json
{
  "id": 4,
  "publisher_name": "아가페출판사",
  "distributor": "agape",
  "created_at": "2026-06-21T10:00:00+09:00"
}
```

---

### DELETE /api/purchase-orders/vendor-rules/{id}/

**성공 응답 (HTTP 204)** — 응답 바디 없음

---

### GET /api/purchase-orders/

**쿼리 파라미터**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `distributor` | string | 선택 | `bookseen`, `kyobo`, `choeumgoyuk`, `agape` |
| `status` | string | 선택 | `pending`, `confirmed`, `cancelled` |
| `date_from` | string | 선택 | ISO 8601 날짜 — `created_at` 기준 |
| `date_to` | string | 선택 | ISO 8601 날짜 — `created_at` 기준 |
| `page` | integer | 선택 | 페이지 번호 (기본값: 1) |

**성공 응답 (HTTP 200)**
```json
{
  "count": 30,
  "next": "http://localhost:8000/api/purchase-orders/?page=2",
  "previous": null,
  "results": [
    {
      "id": 101,
      "sku": "9788901234567",
      "title": "그레이트 개츠비",
      "distributor": "kyobo",
      "quantity": 5,
      "unit_price": "11500.00",
      "status": "pending",
      "created_at": "2026-06-21T10:30:00+09:00"
    }
  ]
}
```

---

## 프론트엔드 UI 명세

### 라우팅

| 경로 | 컴포넌트 | 설명 |
|------|----------|------|
| `/purchase-orders` | `PurchaseOrderPage` | 발주 관리 메인 페이지 (탭 레이아웃) |

### 탭 구조

```
PurchaseOrderPage
├── Tab: 미발주 현황 (UnorderedItemsTab)
│   ├── 집계 테이블 (SKU, 도서명, 출판사, 수량, 주문수, 추천 발주처)
│   ├── 체크박스 다중 선택
│   └── 발주 파일 생성 버튼 (북센 / 교보)
├── Tab: 발주 파일 생성 (GenerateOrderFileTab)
│   ├── 유통사 선택 (북센 / 교보)
│   ├── SKU 목록 확인
│   └── Excel 다운로드 버튼
├── Tab: 업체 자료 업로드 (VendorFileUploadTab)
│   ├── 유통사 선택 드롭다운 (UI: 북센/교보 → API: bookseen/kyobo)
│   ├── 파일 업로드 (drag-and-drop) + 업로드 완료 시 parsed_count 표시
│   ├── "비교 실행" 버튼 → POST /api/purchase-orders/run-comparison/
│   └── 비교 결과 테이블 (SKU, 미발주 주문 목록, 재고, 단가, 자동 선택 발주처, 선택 근거)
├── Tab: 발주 확정 (ConfirmOrderTab)
│   ├── 확정 대상 항목 요약 테이블
│   └── 발주 확정 버튼
├── Tab: 발주 이력 (PurchaseOrderHistoryTab)
│   ├── 발주 이력 테이블 (발주처, 도서명, SKU, 수량, 단가, 상태, 발주일)
│   └── 필터 (발주처, 상태, 날짜)
└── Tab: 발주처 규칙 설정 (VendorRulesTab)
    ├── 규칙 목록 테이블 (출판사명, 발주처, 등록일)
    ├── 규칙 추가 폼 (출판사명 입력 + 발주처 선택)
    └── 삭제 버튼 (행별)
```

### 상태 관리

- TanStack Query를 사용하여 모든 서버 상태(미발주 목록, 비교 데이터, 발주 이력, 규칙 목록)를 관리한다.
- 발주 확정 후 `unordered` 및 `purchase-orders` 쿼리를 자동 무효화(invalidate)한다.
- 업체 파일 업로드는 서버 상태를 무효화하지 않는다. `useRunComparison` mutation 결과를 로컬 상태로 직접 관리한다.
- 탭 전환 시 현재 선택 상태(체크박스, 비교 선택)는 Zustand로 관리한다.

---

## 제외 사항 (What NOT to Build)

- **발주 상태 자동 업데이트**: 유통사로부터 배송 확인을 받아 `PurchaseOrder.status`를 자동으로 `confirmed`로 변경하는 기능은 이 SPEC의 범위가 아니다.
- **Shopify 연동 발주 취소**: Shopify 주문 취소 이벤트를 수신하여 관련 `PurchaseOrder`를 자동 취소하는 기능은 별도 SPEC으로 처리한다.
- **이메일/알림 발송**: 발주 확정 시 담당자에게 이메일 또는 슬랙 알림을 발송하는 기능은 구현하지 않는다.
- **Excel 파일 컬럼 매핑 커스터마이징**: 업체 자료 Excel의 컬럼명이 다를 경우를 위한 매핑 UI는 제공하지 않는다. 컬럼 순서/이름은 약속된 포맷을 따른다.
- **발주 단가 자동 히스토리 관리**: 과거 발주 단가 추이 분석 기능은 구현하지 않는다.
- **다중 발주 파일 동시 생성**: 북센과 교보 파일을 한 번에 생성하는 기능은 구현하지 않는다. 유통사별로 별도 요청한다.
- **기존 Order/LineItem 모델 필드 변경**: `SPEC-ORDER-001`에서 정의된 모델 필드는 변경하지 않는다.
- **처음교육/아가페 업체 자료 업로드**: 처음교육·아가페는 출판사명 기반 자동 라우팅만 지원하며, 재고/단가 비교 기능은 제공하지 않는다.
