---
id: SPEC-PURCHASE-ORDER-004
version: 1.0.0
status: completed
created: 2026-06-23
updated: 2026-06-23
author: ggajo
priority: High
issue_number: ~
---

# LineItem별 발주 상태 관리 (purchase_status 필드 추가)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-23 | ggajo | 최초 작성 |

---

## 문제 정의

현재 미발주 현황(UnorderedItemsTab)은 `LineItem`이 어떤 `PurchaseOrder`에도 연결되지 않은 것(M2M 관계 없음)을 기준으로 미발주 항목을 식별한다.

그러나 실무에서는 PO를 생성하지 않으면서도 해당 `LineItem`을 "발주 불필요" 상태로 구분해야 하는 다양한 케이스가 존재한다.

- **주문보류**: 고객 요청 또는 재고 확인 중인 항목
- **주문취소**: 고객이 취소하거나 판매 불가로 판단된 항목
- **타출판사**: 자사 취급 도서가 아니라 타 출판사가 처리해야 하는 항목
- **CS필요**: 고객 서비스 담당자가 별도 처리해야 하는 항목
- **재고**: 창고 재고로 충당 가능하여 추가 발주가 필요 없는 항목

이 항목들이 모두 "미발주" 상태로 노출되면 관리자는 실제로 발주가 필요한 항목을 식별하기 어렵다.

---

## 솔루션 개요

`LineItem` 모델에 `purchase_status` 필드(CharField, 6개 선택지)를 추가하여 각 `LineItem`에 발주 상태를 직접 부여한다.

- **스키마 변경 최소화**: 기존 M2M(`purchase_orders`) 관계는 그대로 유지하며, `purchase_status` 필드는 부가 분류 정보로 동작한다.
- **미발주 탭 필터 보강**: 기존 M2M 제외 조건에 더해 `purchase_status='unordered'`인 항목만 표시한다.
- **인라인 상태 변경**: 미발주 탭에서 각 행(또는 선택한 다수 행)의 상태를 드롭다운으로 즉시 변경한다.

---

## 범위

### 포함

- `LineItem` 모델에 `purchase_status` 필드 추가 및 Django 마이그레이션 생성
- `PATCH /api/purchase-orders/line-items/{id}/status/` — 단건 상태 변경 엔드포인트
- `PATCH /api/purchase-orders/line-items/bulk-status/` — 다건 상태 일괄 변경 엔드포인트
- `UnorderedItemsView` 필터 보강: `purchase_status='unordered'` 조건 추가
- `UnorderedItemsTab.tsx` — `purchase_status` 컬럼 추가 및 드롭다운 인라인 변경 UI
- URL 라우팅 및 `urls.py` 등록

### 제외 (What NOT to Build)

- 기존 `PurchaseOrder` ↔ `LineItem` M2M 관계 변경 또는 제거
- `purchase_status` 기반의 통계/집계 대시보드
- `purchase_status` 변경 이력(audit log) 기능
- 외부 시스템(Shopify 등) 연동 시 `purchase_status` 자동 갱신
- 발주현황 탭(`PurchaseOrderHistoryTab`) 변경
- 모바일 UI 또는 별도 알림 기능

---

## 요구사항 (EARS 형식)

### REQ-PO4-001 — purchase_status 필드 정의

**The `LineItem` model shall** `purchase_status` 필드를 가지며, 다음 6개 선택지(choices) 중 하나를 가진다.

| 코드 | 한국어 레이블 |
|------|--------------|
| `unordered` | 미발주 |
| `on_hold` | 주문보류 |
| `order_cancelled` | 주문취소 |
| `other_publisher` | 타출판사 |
| `cs_required` | CS필요 |
| `in_stock` | 재고 |

기본값(default)은 `unordered`이며, 기존 및 신규 `LineItem` 모두에 적용된다.

---

### REQ-PO4-002 — 마이그레이션 및 기존 데이터 백필

**When** Django 마이그레이션이 실행될 때, **the system shall** `orders_line_item` 테이블에 `purchase_status VARCHAR(20) NOT NULL DEFAULT 'unordered'` 컬럼을 추가하고, 기존 레코드의 `purchase_status`를 `'unordered'`로 설정한다.

> 제약: MySQL 8.0 (AWS RDS) — PostgreSQL 전용 문법 사용 금지.

---

### REQ-PO4-003 — 미발주 탭 필터 보강

**When** `GET /api/purchase-orders/unordered/` 요청이 들어올 때, **the system shall** 다음 두 조건을 모두 만족하는 `LineItem`만 반환한다.

1. `purchase_orders` M2M 관계가 없는 항목 (기존 조건, 유지)
2. `purchase_status = 'unordered'`인 항목 (신규 조건)

> 즉, PO에 연결되어 있지 않더라도 `purchase_status`가 `unordered`가 아닌 항목은 미발주 탭에 표시되지 않는다.

---

### REQ-PO4-004 — 미발주 탭 응답에 purchase_status 포함

**When** `GET /api/purchase-orders/unordered/` 요청이 성공할 때, **the system shall** 각 `LineItem` 응답 객체에 `purchase_status` 필드를 포함한다.

---

### REQ-PO4-005 — 단건 상태 변경 엔드포인트

**When** `PATCH /api/purchase-orders/line-items/{id}/status/` 요청이 유효한 `purchase_status` 값과 함께 들어올 때, **the system shall** 해당 `LineItem`의 `purchase_status`를 요청된 값으로 업데이트하고 HTTP 200과 업데이트된 `LineItem` 정보를 반환한다.

**If** `id`가 존재하지 않으면, **then the system shall** HTTP 404를 반환한다.

**If** `purchase_status` 값이 유효하지 않은 코드이면, **then the system shall** HTTP 400과 오류 메시지를 반환한다.

---

### REQ-PO4-006 — 다건 상태 일괄 변경 엔드포인트

**When** `PATCH /api/purchase-orders/line-items/bulk-status/` 요청이 `{"ids": [...], "purchase_status": "..."}` 형태로 들어올 때, **the system shall** 지정된 모든 `LineItem`의 `purchase_status`를 원자적으로 업데이트하고, 업데이트된 건수를 반환한다.

**If** `ids` 목록이 비어 있거나 `purchase_status`가 유효하지 않으면, **then the system shall** HTTP 400을 반환한다.

**If** `ids` 중 일부가 DB에 존재하지 않으면, **then the system shall** 존재하는 항목만 업데이트하고 누락된 `id` 목록을 응답에 포함한다.

---

### REQ-PO4-007 — 인증 요구

**The system shall** `PATCH /api/purchase-orders/line-items/{id}/status/` 및 `PATCH /api/purchase-orders/line-items/bulk-status/` 요청에 대해 JWT 인증을 요구하며, 미인증 요청에는 HTTP 401을 반환한다.

---

### REQ-PO4-008 — 프론트엔드 상태 컬럼 표시

**When** 미발주 현황 탭(UnorderedItemsTab)이 렌더링될 때, **the system shall** 각 행에 `purchase_status`를 한국어 레이블로 표시하는 컬럼을 추가한다.

---

### REQ-PO4-009 — 프론트엔드 인라인 상태 변경

**When** 사용자가 미발주 현황 탭의 특정 행에서 상태 드롭다운 값을 변경할 때, **the system shall** 즉시 `PATCH /api/purchase-orders/line-items/{id}/status/` 를 호출하고, 성공 시 해당 행을 목록에서 제거(상태가 `unordered`가 아닌 경우) 또는 유지(`unordered`로 변경한 경우)한다.

---

### REQ-PO4-010 — 프론트엔드 다건 상태 일괄 변경

**When** 사용자가 미발주 현황 탭에서 하나 이상의 행을 선택하고 일괄 상태 변경 액션을 실행할 때, **the system shall** `PATCH /api/purchase-orders/line-items/bulk-status/` 를 호출하고, 성공 시 선택된 행 중 `purchase_status`가 `unordered`가 아닌 항목을 목록에서 제거한다.

---

## 기술 설계

### 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `backend/order/models.py` | 수정 | `LineItem`에 `purchase_status` 필드 추가 |
| `backend/order/migrations/XXXX_add_purchase_status_to_lineitem.py` | 신규 생성 | Django 마이그레이션 |
| `backend/order/purchase_order_views.py` | 수정 | `UnorderedItemsView` 필터 보강, `LineItemStatusView`/`LineItemBulkStatusView` 신규 추가 |
| `backend/order/urls.py` | 수정 | 신규 엔드포인트 URL 등록 |
| `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` | 수정 | `purchase_status` 컬럼 + 드롭다운 인라인 변경 UI |
| `frontend/src/api/purchaseOrders.ts` (또는 동등 API 파일) | 수정 | 단건/다건 상태 변경 API 함수 추가 |

### 모델 변경 (backend/order/models.py)

```python
PURCHASE_STATUS_CHOICES = [
    ("unordered", "미발주"),
    ("on_hold", "주문보류"),
    ("order_cancelled", "주문취소"),
    ("other_publisher", "타출판사"),
    ("cs_required", "CS필요"),
    ("in_stock", "재고"),
]

class LineItem(models.Model):
    # ... 기존 필드 ...
    purchase_status = models.CharField(
        max_length=20,
        choices=PURCHASE_STATUS_CHOICES,
        default="unordered",
    )
```

### API 엔드포인트 설계

| 메서드 | URL | 설명 |
|--------|-----|------|
| `GET` | `/api/purchase-orders/unordered/` | 미발주 목록 (기존, 필터 보강) |
| `PATCH` | `/api/purchase-orders/line-items/{id}/status/` | 단건 상태 변경 |
| `PATCH` | `/api/purchase-orders/line-items/bulk-status/` | 다건 상태 일괄 변경 |

### 필터 변경 (UnorderedItemsView)

기존:
```python
LineItem.objects.filter(sku__isnull=False).exclude(purchase_orders__isnull=False)
```

변경 후:
```python
LineItem.objects.filter(sku__isnull=False, purchase_status="unordered").exclude(purchase_orders__isnull=False)
```

### 하위 호환성

- 기존 M2M(`line_items`) 관계는 변경 없음
- PO에 연결된 `LineItem`의 `purchase_status`는 별도로 변경되지 않음 (PO 연결이 "발주 완료"의 주요 기준)
- Shopify 동기화 로직(`sync_orders`)은 `purchase_status` 필드를 덮어쓰지 않음 (기본값 `unordered`는 신규 LineItem에만 적용)

---

## 구현 완료 노트

- **구현 일자**: 2026-06-23
- **커밋**: `1f65fe8`

### 백엔드 변경 사항

- `backend/order/models.py`: `PURCHASE_STATUS_CHOICES` 및 `purchase_status` CharField를 `LineItem` 모델에 추가 (6개 선택지, 기본값 `unordered`)
- `backend/order/migrations/0011_lineitem_add_purchase_status.py`: MySQL 호환 마이그레이션 생성 (`VARCHAR(20) NOT NULL DEFAULT 'unordered'`)
- `backend/order/purchase_order_views.py`:
  - `UnorderedItemsView.get()`: `purchase_status="unordered"` 필터 조건 추가 및 응답에 `purchase_status` 포함
  - `LineItemStatusUpdateView` 신규 추가: `PATCH /api/purchase-orders/line-items/{id}/status/`
  - `LineItemBulkStatusUpdateView` 신규 추가: `PATCH /api/purchase-orders/line-items/bulk-status/`
- `backend/order/urls.py`: 신규 엔드포인트 2개 URL 패턴 등록
- `backend/order/tests/test_purchase_order_models.py`: `TestLineItemPurchaseStatus` 클래스 (3개 테스트)
- `backend/order/tests/test_purchase_orders.py`: 신규 테스트 클래스 3개 (약 16개 테스트)

### 프론트엔드 변경 사항

- `frontend/src/services/purchaseOrderApi.ts`: `UnorderedItem`에 `purchase_status` 추가, `PURCHASE_STATUS_OPTIONS`, `updateLineItemStatus()`, `bulkUpdateLineItemStatus()` 추가
- `frontend/src/hooks/usePurchaseOrderQueries.ts`: `useUpdateLineItemStatus`, `useBulkUpdateLineItemStatus` mutation 훅 추가
- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`: 행별 상태 드롭다운 및 일괄 상태 변경 UI 추가

### 테스트 결과

- **23 / 23 테스트 통과**
