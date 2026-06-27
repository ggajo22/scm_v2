# SPEC-ORDER-002 리서치 — 영향 파일 분석

## 분석 대상

SPEC-ORDER-002(주문번호·ISBN 통합 검색) 구현에 영향받는 기존 파일을 분석한다.

---

## 1. 백엔드

### `backend/order/views.py`

**현재 상태**

`OrderListView.get_queryset()`은 5개 필터 파라미터(`store_type`, `financial_status`, `fulfillment_status`, `date_from`, `date_to`)를 순차적으로 `qs`에 적용한다.

```python
# 현재 import — Q 객체 없음
from django.db import transaction
from rest_framework.exceptions import ValidationError
...
from .models import Order
```

**필요한 변경**

- `from django.db.models import Q` import 추가 (1줄)
- `get_queryset()` 말미에 `search` 파라미터 처리 블록 추가 (약 11줄)
- `date_to` 필터 처리 이후, `return qs` 이전에 삽입

**주의사항**

- `distinct()`를 호출하면 `order_by("-shopify_created_at")`와 함께 사용된다. MySQL 8.0에서는 `DISTINCT`와 `ORDER BY`를 함께 사용할 때 `ORDER BY` 컬럼이 `SELECT` 절에 포함되어야 하나, Django ORM이 이를 자동 처리한다.
- `order_number` 필드는 `IntegerField(null=True, blank=True)` 이므로, `int(numeric)` 변환 후 쿼리에 사용한다. null 레코드는 자동으로 제외된다.
- `line_items__sku` 조건 추가 시 `LineItem` 테이블과 JOIN이 발생한다. `distinct()`가 필수이다.

---

### `backend/order/models.py`

**참조 필드 확인**

| 필드 | 모델 | 타입 | 비고 |
|------|------|------|------|
| `order_number` | `Order` | `IntegerField(null=True)` | 숫자 입력 시 exact match |
| `name` | `Order` | `CharField(null=True)` | e.g. "#1234", icontains |
| `sku` | `LineItem` | `CharField(null=True)` | FK: `order` (related_name="line_items") |

`LineItem.order`는 `ForeignKey(Order, related_name="line_items")`이므로 `Order.objects.filter(line_items__sku=...)` 역참조가 가능하다.

**변경 없음** — 모델 수정 및 마이그레이션 불필요.

---

## 2. 프론트엔드

### `frontend/src/types/order.ts`

**현재 `OrderListParams`**

```typescript
export interface OrderListParams {
  page?: number
  store_type?: 'gimssine' | 'etoile' | ''
  financial_status?: string
  fulfillment_status?: string
  date_from?: string
  date_to?: string
}
```

**필요한 변경**: `search?: string` 필드 1개 추가.

---

### `frontend/src/features/order/hooks/useOrders.ts`

**현재 `queryFn` 내 파라미터 조립**

```typescript
if (params.page && params.page > 1) searchParams.page = String(params.page)
if (params.store_type) searchParams.store_type = params.store_type
// ... 기타 파라미터
```

**필요한 변경**: `if (params.search) searchParams.search = params.search` 조건문 1개 추가.

React Query의 `queryKey`에 `params` 객체 전체가 포함되어 있으므로(`[...ORDERS_QUERY_KEY, params]`), `params.search` 값 변경 시 자동으로 재요청이 트리거된다. 별도 무효화 로직 불필요.

---

### `frontend/src/pages/OrdersPage.tsx`

**현재 필터 영역 구조**

```tsx
<div className="flex flex-wrap gap-3">
  <select ...>  {/* 스토어 */}
  <select ...>  {/* 결제상태 */}
  <select ...>  {/* 출고상태 */}
  <div className="flex items-center gap-1">  {/* 날짜 범위 */}
</div>
```

`setFilter(key, value)` 유틸리티 함수가 이미 `keyof OrderListParams`를 받아 `params` 상태를 갱신하므로, 검색 input의 `onChange`에서 `setFilter('search', value)`를 호출하는 패턴과 완전히 호환된다.

**필요한 변경**

1. `useRef<ReturnType<typeof setTimeout>>` 또는 `useCallback` 기반의 debounce 타이머 상태 추가
2. `<div className="flex flex-wrap gap-3">` 내에 `<input>` 추가
3. `results`가 0건일 때 "검색 결과가 없습니다" 분기 처리 (현재 빈 테이블만 렌더링됨)

**현재 빈 결과 처리**

현재 코드에는 빈 `results`에 대한 명시적 메시지가 없다. 기존 테이블 렌더링 로직 내 `data.results.length === 0` 분기에 메시지를 추가한다.

---

## 3. 의존성 정리

```
OrderListParams (types/order.ts)
    ↓ 사용
useOrders (hooks/useOrders.ts) → GET /api/orders/?search=...
    ↓ 사용
OrdersPage (pages/OrdersPage.tsx)
```

```
OrderListView.get_queryset() (views.py)
    ↓ 참조
Order.order_number, Order.name (models.py)
LineItem.sku via line_items FK (models.py)
```

---

## 4. 테스트 파일 현황

| 테스트 파일 | 현재 커버리지 |
|-------------|---------------|
| `backend/order/tests/test_list_view.py` | 기존 필터 파라미터 테스트 포함 |
| `frontend/src/features/order/` | 훅 테스트 파일 미확인 (구현 시 확인 필요) |

백엔드 구현 후 `test_list_view.py`에 `search` 파라미터 관련 테스트 케이스를 추가해야 한다.

---

## 5. 구현 순서 권장

1. `backend/order/views.py` — `search` 필터 추가 및 테스트
2. `frontend/src/types/order.ts` — `OrderListParams.search` 추가
3. `frontend/src/features/order/hooks/useOrders.ts` — search 전달 추가
4. `frontend/src/pages/OrdersPage.tsx` — UI 및 debounce 추가

백엔드 변경이 단독으로 검증 가능하고(curl/pytest), 프론트엔드는 타입 변경 → 훅 변경 → UI 변경 순서의 의존성이 존재한다.
