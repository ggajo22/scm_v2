---
id: SPEC-PURCHASE-ORDER-003
version: 1.1.0
status: draft
created: 2026-06-22
updated: 2026-06-22
author: ggajo
priority: Medium
issue_number: ~
---

# 발주현황 — 환불 반영 (전체 환불 제외 / 부분 환불 수량 차감)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-22 | ggajo | 최초 작성 |
| 1.1.0 | 2026-06-22 | ggajo | 부분 환불 PO 수량 차감 요구사항 추가 (REQ-PO3-004, REQ-PO3-006, REQ-PO3-007) |

---

## 문제 정의

`GET /api/purchase-orders/` (발주현황 목록)에서 환불이 전혀 반영되지 않는다.

1. **전량 환불된 PO**가 목록에 그대로 노출 — 처리할 필요가 없는 항목이 노이즈로 쌓인다.
2. **부분 환불된 PO**의 `quantity`가 원래 수량 그대로 표시 — 실제 발주 필요 수량(원래 수량 - 환불 수량)이 아닌 잘못된 값이 보인다.

관리자는 "지금 실제로 발주해야 할 수량"을 발주현황에서 즉시 파악해야 하므로, 환불 수량이 정확히 반영되어야 한다.

---

## 솔루션 개요

두 가지 동작을 동시에 구현한다.

1. **전량 환불 제외**: 모든 연결된 `LineItem`이 전량 환불된 PO는 API 응답에서 제거
2. **부분 환불 수량 차감**: 부분 환불된 PO는 `net_quantity = 원래수량 - 총환불수량`을 API 응답에 추가 노출

- 백엔드: `backend/order/purchase_order_views.py` — `PurchaseOrderListView` + `PurchaseOrderSerializer`
- 프론트엔드: `PurchaseOrderHistoryTab.tsx` — `quantity` 대신 `net_quantity` 표시
- DB 마이그레이션 없음 (스키마 변경 없음)

---

## 범위

- **포함**:
  - `backend/order/purchase_order_views.py` — `PurchaseOrderListView` queryset 필터링 + `PurchaseOrderSerializer` `net_quantity` 필드 추가
  - `frontend/src/pages/PurchaseOrders/tabs/PurchaseOrderHistoryTab.tsx` — `net_quantity` 표시
- **제외**: DB 마이그레이션, 다른 API 엔드포인트, 환불 관련 모델 필드 추가

---

## 요구사항 (EARS 형식)

### REQ-PO3-001 — 전체 환불 건 기본 제외

**The system shall** `GET /api/purchase-orders/` 응답에서, 연결된 모든 `LineItem`이 전량 환불된 `PurchaseOrder`를 제외한다.

### REQ-PO3-002 — LineItem 전량 환불 판단 기준

**The system shall** 개별 `LineItem`의 전량 환불 여부를 다음 조건으로 판단한다:  
`SUM(Refund.quantity WHERE Refund.line_item_id == LineItem.shopify_line_item_id AND Refund.order_id == LineItem.order_id) >= LineItem.quantity`

### REQ-PO3-003 — 연결된 LineItem이 없는 PO는 표시 유지

**Where** `PurchaseOrder`에 연결된 `LineItem`이 없는 경우,  
**the system shall** 해당 `PurchaseOrder`를 발주현황 목록에 계속 표시한다.

### REQ-PO3-004 — 부분 환불 PO 수량 차감 표시

**If** 연결된 `LineItem` 중 하나라도 전량 환불되지 않은 항목이 있는 경우,  
**then the system shall** 해당 `PurchaseOrder`를 목록에 표시하되, API 응답에 `net_quantity` 필드를 포함한다.  
`net_quantity = PurchaseOrder의 모든 LineItem.quantity 합계 - 해당 LineItem들의 Refund.quantity 합계`

### REQ-PO3-006 — API 응답에 net_quantity 필드 추가

**The system shall** `GET /api/purchase-orders/` 응답의 각 PurchaseOrder 항목에 `net_quantity` 필드를 포함한다.  
- 환불 없음: `net_quantity == PurchaseOrder.quantity`  
- 부분 환불: `net_quantity = PurchaseOrder.quantity - 총환불수량`  
- 전량 환불: 목록에서 제외되므로 해당 없음

### REQ-PO3-007 — 프론트엔드 수량 표시를 net_quantity로 변경

**The system shall** `PurchaseOrderHistoryTab`의 수량 컬럼에서 `quantity` 대신 `net_quantity` 값을 표시한다.

### REQ-PO3-008 — 기존 필터 파라미터 정상 동작 유지

**While** 환불 제외 필터가 적용된 상태에서,  
**the system shall** 기존 쿼리 파라미터(`distributor`, `status`, `date_from`, `date_to`, `page`)가 환불 제외 필터와 함께 올바르게 동작한다.

---

## 인수 조건

| # | 시나리오 | 조건 | 기대 결과 |
|---|---------|------|-----------|
| AC-01 | 전량 환불 PO 제외 | PO에 LineItem 1개(qty=5), Refund qty 합계=5 | 해당 PO가 목록에 미표시 |
| AC-02 | 부분 환불 — 수량 차감 | PO에 LineItem 1개(qty=5), Refund qty 합계=3 | 목록에 표시, `net_quantity=2` |
| AC-03 | LineItem 없는 PO | PO에 연결된 LineItem 없음 | 목록에 표시, `net_quantity=PurchaseOrder.quantity` |
| AC-04 | 복수 LineItem — 모두 전량 환불 | PO에 LineItem 2개(qty=3, qty=2), Refund 합계 3, 2 | 해당 PO 미표시 |
| AC-05 | 복수 LineItem — 일부만 환불 | PO에 LineItem 2개(qty=3, qty=2), Refund 합계 3, 1 | 목록에 표시, `net_quantity=1` (미환불 수량 합산) |
| AC-06 | 환불 초과(qty 초과 refund) | LineItem qty=5, Refund qty 합계=6 | 전량 환불로 간주, PO 미표시 |
| AC-07 | 기존 필터 병행 동작 | `distributor=bookseen` 필터 + 전량 환불 PO 혼재 | bookseen이면서 전량 환불되지 않은 PO만 반환 |
| AC-08 | Refund 없는 PO | PO에 LineItem 있으나 Refund 레코드 없음 | 목록에 표시, `net_quantity=LineItem.quantity 합산` |
| AC-09 | net_quantity 프론트 표시 | 부분 환불 PO (net_quantity=2) | 수량 컬럼에 2 표시 (원래 수량이 아닌 net_quantity) |

---

## 기술 설계

### 변경 파일

- `backend/order/purchase_order_views.py` — `PurchaseOrderSerializer` + `PurchaseOrderListView`
- `frontend/src/pages/PurchaseOrders/tabs/PurchaseOrderHistoryTab.tsx` — `net_quantity` 표시

### 모델 관계

```
PurchaseOrder
  └─ line_items (M2M) ──► LineItem
                              ├─ shopify_line_item_id (BigIntegerField)
                              ├─ quantity (IntegerField)
                              └─ order_id (FK → Order)

Refund
  ├─ line_item_id (BigIntegerField)  ← LineItem.shopify_line_item_id와 매칭
  ├─ order_id (FK → Order)           ← LineItem.order_id와 동일해야 유효
  └─ quantity (IntegerField)
```

`Refund`와 `LineItem` 간에는 직접적인 ForeignKey가 없으므로 비-FK join(`line_item_id == shopify_line_item_id AND order_id == order_id`)이 필요하다.

### ORM 접근 방식

`Refund` → `LineItem` 간 직접 FK가 없으므로 `OuterRef`를 사용한 Subquery로 각 `LineItem`의 환불 수량 합계를 계산하고, 이를 Annotation으로 집계하여 제외 조건을 구성한다.

```python
from django.db.models import OuterRef, Subquery, Sum, IntegerField
from django.db.models.functions import Coalesce

# 각 LineItem의 환불 수량 합계 Subquery
refund_qty_subquery = Subquery(
    Refund.objects.filter(
        line_item_id=OuterRef("shopify_line_item_id"),
        order_id=OuterRef("order_id"),
    ).values("line_item_id").annotate(
        total=Sum("quantity")
    ).values("total")[:1],
    output_field=IntegerField(),
)

# 전량 환불된 LineItem: 환불 수량 합계 >= 원래 수량
# 전량 환불된 PO: 모든 LineItem이 전량 환불됨
#   → 연결된 LineItem 수 == 전량 환불된 LineItem 수인 PO를 제외
```

구체적 제외 조건은 구현 단계에서 `Subquery` + `annotate` + `exclude`/`filter` 조합으로 확정한다. 대안으로 raw SQL 기반 `RawSQL` 또는 `extra(where=[...])` 접근도 허용하며, 가독성과 유지보수성을 기준으로 선택한다.

### Serializer 변경 (`PurchaseOrderSerializer`)

```python
class PurchaseOrderSerializer(serializers.ModelSerializer):
    net_quantity = serializers.IntegerField(read_only=True)  # annotate로 주입

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "sku", "title", "distributor", "quantity",
            "net_quantity",  # 추가
            "unit_price", "status", "created_at", "updated_at",
        ]
```

`net_quantity`는 `PurchaseOrderListView`의 queryset에서 `annotate`로 계산하여 주입한다.

### 프론트엔드 (`PurchaseOrderHistoryTab.tsx`)

- 수량 컬럼에서 `item.quantity` 대신 `item.net_quantity ?? item.quantity` 표시
- TypeScript 타입 정의(`PurchaseOrderParams` 또는 관련 인터페이스)에 `net_quantity?: number` 추가

### DB 마이그레이션

불필요 — 기존 모델 스키마 변경 없음.

---

## 테스트 계획

- **파일**: `backend/order/tests/test_purchase_orders.py`
- **테스트 클래스**: `PurchaseOrderListViewRefundExclusionTest`
- **필수 테스트 케이스**: AC-01 ~ AC-09 시나리오 각각 단위 테스트로 작성
- **픽스처**: `PurchaseOrder`, `LineItem`, `Order`, `Refund` 모델 인스턴스를 `setUp`에서 생성
- **검증 방법**: API 응답 `results` 리스트의 PO id 포함 여부로 확인

---

## 제외 사항 (What NOT to Build)

- **전량 환불 건 별도 탭/화면 표시**: 제외된 전량 환불 PO를 별도로 조회하는 UI 또는 API는 이 SPEC의 범위 밖이다.
- **환불 상태 필드 추가**: `PurchaseOrder` 모델에 환불 관련 필드를 추가하는 스키마 변경은 하지 않는다.
- **실시간 환불 webhook 연동**: Shopify 환불 이벤트를 수신하여 즉시 처리하는 기능은 별도 SPEC으로 처리한다.
- **프론트엔드 필터 UI**: 전량 환불 건을 다시 포함하여 볼 수 있는 토글 필터는 구현하지 않는다.
