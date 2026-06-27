# SPEC-ORDER-002 구현 계획

## 개요

기존 주문 목록 기능(`SPEC-ORDER-001`)에 검색 파라미터를 추가하는 작업이다. 신규 엔드포인트나 마이그레이션 없이 기존 코드 2~3곳에 소규모 변경으로 완료된다.

---

## 마일스톤

### 우선순위 High — 백엔드 검색 로직

**M1. `backend/order/views.py` 수정**

`OrderListView.get_queryset()` 내에 `search` 파라미터 처리 블록을 추가한다.

- `from django.db.models import Q` import 추가
- `search = params.get("search", "").strip()` 처리
- `numeric = search.lstrip("#")`로 선행 "#" 제거
- `Q(name__icontains=search)` 기본 조건 설정
- `numeric.isdigit()` 이면 `Q(order_number=int(numeric))` OR 결합
- `len(numeric) in (10, 13) and numeric.isdigit()` 이면 `Q(line_items__sku=numeric)` OR 결합
- `qs.filter(q).distinct()` 적용

**변경 범위**: `views.py` 약 12줄 추가 (import 1줄 포함)

---

### 우선순위 High — 프론트엔드 타입 및 훅

**M2. `frontend/src/types/order.ts` 수정**

`OrderListParams` 인터페이스에 `search?: string` 필드 추가.

**M3. `frontend/src/features/order/hooks/useOrders.ts` 수정**

`params.search`가 존재할 경우 `searchParams.search` 에 할당하는 조건문 추가.

---

### 우선순위 High — 프론트엔드 UI

**M4. `frontend/src/pages/OrdersPage.tsx` 수정**

- `filter.search` 상태 관리 (`OrderListParams`에 이미 포함됨)
- `useDebounce` 훅(또는 `setTimeout` 기반 로컬 구현) 300ms debounce 적용
- `<input>` 요소 추가: `placeholder="주문번호 또는 ISBN"`, `onKeyDown` Enter 즉시 검색, `onChange` debounce 검색
- 검색 결과 0건 시 "검색 결과가 없습니다" 빈 상태 메시지 표시

---

## 기술 접근 방법

### 백엔드 Q 객체 조합 패턴

```
search = params.get("search", "").strip()
if search:
    numeric = search.lstrip("#")
    q = Q(name__icontains=search)
    if numeric.isdigit():
        q |= Q(order_number=int(numeric))
    if len(numeric) in (10, 13) and numeric.isdigit():
        q |= Q(line_items__sku=numeric)
    qs = qs.filter(q).distinct()
```

`distinct()`는 `line_items` JOIN 시 동일 Order 행이 여러 LineItem 수만큼 복제되는 현상을 방지한다. `order_number`와 `name`만 검색하는 경우에도 `distinct()`를 항상 적용하여 일관성을 유지한다.

### 프론트엔드 debounce 전략

`useOrders` 훅의 `queryKey`는 `params` 객체 전체를 포함하므로, debounce된 `search` 값이 `params`에 반영된 시점에 자동으로 React Query가 재요청을 트리거한다. 별도 `refetch()` 호출이 필요 없다.

Enter 키 입력 시에는 debounce를 우회하여 즉시 `search` 파라미터를 업데이트한다.

---

## 위험 요소

| 위험 | 영향 | 대응 |
|------|------|------|
| `distinct()` 와 `order_by("-shopify_created_at")` 조합 시 PostgreSQL/MySQL 호환성 | 쿼리 오류 가능 | MySQL 8.0 기준 `ORDER BY` 컬럼이 `SELECT` 절에 포함되므로 문제 없음. `DISTINCT` + `ORDER BY` 조합 테스트 필수 |
| 검색 입력이 매우 긴 문자열인 경우 | 예상치 못한 쿼리 결과 | `search` 파라미터 길이 제한은 별도 SPEC으로 처리 (현재 범위 외) |
| `order_number`가 `null`인 주문 | `int(numeric)` 변환 후 조회 시 null 레코드 미포함 | 정상 동작 — null인 주문은 order_number 검색 대상에서 제외됨 |

---

## 영향받는 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `backend/order/views.py` | 수정 | `search` 파라미터 처리 블록 추가 (12줄) |
| `frontend/src/types/order.ts` | 수정 | `OrderListParams.search` 필드 추가 |
| `frontend/src/features/order/hooks/useOrders.ts` | 수정 | `search` 파라미터 전달 조건문 추가 |
| `frontend/src/pages/OrdersPage.tsx` | 수정 | 검색 input UI, debounce 로직, 빈 결과 메시지 |

신규 파일, 마이그레이션, 새 엔드포인트: 없음.
