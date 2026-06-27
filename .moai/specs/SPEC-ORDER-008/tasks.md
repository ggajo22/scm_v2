---
spec_id: SPEC-ORDER-008
version: "1.0.0"
created: 2026-06-24
methodology: TDD (RED-GREEN-REFACTOR)
status: ready
---

# SPEC-ORDER-008 Task Decomposition

## TDD Cycle Order (Implementation Sequence)

```
TASK-001 (RED)   → TASK-002 (GREEN/REFACTOR)   Backend 완료
       ↓
TASK-003 (Types) → TASK-004 (UI RED) → TASK-005 (UI GREEN) → TASK-006 (UI REFACTOR)
```

Phase 1 (Backend)은 반드시 먼저 완료해야 한다. Phase 2 (Types)는 Phase 1 직후 진행하고,
Phase 3 (UI)는 Phase 2 완료 이후 시작한다 (TypeScript 타입 오류 방지).

---

## TASK-001 — Backend: 실패 테스트 작성 (RED)

**REQ 매핑**: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006

**의존성**: 없음 (최초 시작점)

**파일**:
- `backend/order/tests/test_order_detail.py` [MODIFY] — 신규 테스트 케이스 추가

**작업 내용**:

기존 `test_order_detail.py`에 다음 4개의 신규 테스트 케이스를 추가한다.
기존 fixture(`order_with_line_items`)를 확장하거나 별도 fixture를 생성한다.

### 추가할 fixture

```python
@pytest.fixture
def order_with_confirmed_items(db) -> Order:
    """confirmed_price가 설정된 line item을 가진 주문."""
    order = Order.objects.create(
        shopify_order_id=99010,
        store_type="gimssine",
        financial_status="paid",
        total_price="60000.00",
        shopify_created_at=timezone.now(),
    )
    # item A: confirmed_price 있음
    LineItem.objects.create(
        order=order, shopify_line_item_id=11010,
        title="상품 A", quantity=2, price="15000.00",
        confirmed_price="14000.00", confirmed_distributor="bookseen",
    )
    # item B: confirmed_price 없음 (null)
    LineItem.objects.create(
        order=order, shopify_line_item_id=11011,
        title="상품 B", quantity=1, price="30000.00",
        confirmed_price=None, confirmed_distributor=None,
    )
    return order

@pytest.fixture
def order_all_null_confirmed(db) -> Order:
    """모든 line item의 confirmed_price가 null인 주문."""
    order = Order.objects.create(
        shopify_order_id=99011,
        store_type="gimssine",
        total_price="45000.00",
        shopify_created_at=timezone.now(),
    )
    LineItem.objects.create(
        order=order, shopify_line_item_id=11020,
        quantity=1, price="45000.00", confirmed_price=None,
    )
    return order
```

### 추가할 테스트 케이스

```
test_line_item_includes_confirmed_fields          # REQ-001, 002, 003
test_margin_amount_partial_null_excluded          # REQ-004, REQ-006
test_margin_rate_computed_correctly               # REQ-005
test_margin_amount_null_when_all_confirmed_null   # REQ-004 (전체 null 케이스)
```

**완료 기준**: `pytest backend/order/tests/test_order_detail.py -k "confirmed or margin"` 실행 시 4개 테스트가 모두 FAIL 상태

---

## TASK-002 — Backend: 직렬화 구현 (GREEN + REFACTOR)

**REQ 매핑**: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006

**의존성**: TASK-001 완료 (RED 상태 테스트 존재)

**파일**:
- `backend/order/serializers.py` [MODIFY]

**작업 내용**:

### 2-A: LineItemDetailSerializer 필드 추가 (GREEN for REQ-001~003)

`LineItemDetailSerializer.Meta.fields` 리스트에 3개 필드 추가:
```python
# 기존 fields 리스트 끝에 추가
"confirmed_price", "confirmed_distributor", "confirmed_at",
```
추가 코드 불필요 — `LineItem` 모델에 이미 존재하는 필드 (models.py lines 140-142).

### 2-B: OrderDetailSerializer 마진 필드 추가 (GREEN for REQ-004~006)

```python
from decimal import Decimal, ROUND_HALF_UP

class OrderDetailSerializer(serializers.ModelSerializer):
    # 기존 SerializerMethodField 선언부에 추가
    margin_amount = serializers.SerializerMethodField()
    margin_rate = serializers.SerializerMethodField()

    class Meta:
        # fields 리스트에 "margin_amount", "margin_rate" 추가
        ...

    def get_margin_amount(self, obj: Order):
        """
        REQ-004, REQ-006:
        - confirmed_price IS NOT NULL인 line item만 합산
        - 전부 null이면 None 반환
        """
        items_with_price = [
            li for li in obj.line_items.all()
            if li.confirmed_price is not None
        ]
        if not items_with_price:
            return None
        cost = sum(li.confirmed_price * li.quantity for li in items_with_price)
        total = Decimal(obj.total_price or "0")
        return str(total - cost)

    def get_margin_rate(self, obj: Order):
        """
        REQ-005:
        - margin_amount가 None이면 None 반환
        - total_price == 0이면 None 반환
        """
        margin = self.get_margin_amount(obj)
        if margin is None:
            return None
        total = Decimal(obj.total_price or "0")
        if total == 0:
            return None
        rate = (Decimal(margin) / total * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return str(rate)
```

### REFACTOR 체크리스트
- `get_margin_amount`와 `get_margin_rate` 간 중복 계산 제거 방안 검토
  - `get_margin_rate`가 `get_margin_amount`를 내부 호출하는 현재 설계는 수용 가능 (API 호출당 1회)
- `obj.line_items.all()` 중복 호출 없음 (Django ORM prefetch_related가 캐시)
- 타입 일관성: 반환값은 항상 `str` 또는 `None` (DRF의 DecimalField 직렬화 방식과 일치)

**완료 기준**:
```
pytest backend/order/tests/test_order_detail.py -v → 전체 통과
pytest backend/order/tests/ -v → 기존 테스트 회귀 없음
```

---

## TASK-003 — Frontend: TypeScript 타입 확장

**REQ 매핑**: REQ-007, REQ-008

**의존성**: TASK-002 완료 (백엔드 응답 스키마 확정)

**파일**:
- `frontend/src/types/order.ts` [MODIFY]

**작업 내용**:

### 3-A: LineItemDetail 인터페이스 확장 (REQ-007)

`LineItemDetail` 인터페이스 (현재 lines 83-96)에 3개 필드 추가:
```typescript
// 기존 필드 이후에 추가
confirmed_price: string | null
confirmed_distributor: string | null
confirmed_at: string | null
```

### 3-B: OrderDetail 인터페이스 확장 (REQ-008)

`OrderDetail` 인터페이스 (현재 lines 127-160)에 2개 필드 추가:
```typescript
// refunds 필드 이후에 추가
margin_amount: string | null
margin_rate: string | null
```

**설계 근거**:
- `confirmed_price`, `margin_amount`가 `string | null`인 이유: DRF `DecimalField`는 문자열로 직렬화. `SerializerMethodField`도 `str()`로 반환하도록 구현.
- `confirmed_at`이 `string | null`인 이유: Django `DateTimeField` → ISO 8601 문자열 직렬화.

**완료 기준**: `npx tsc --noEmit` 오류 없음

---

## TASK-004 — Frontend: UI 테스트 작성 (RED) — 선택적

**REQ 매핑**: REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014

**의존성**: TASK-003 완료

**파일**:
- `frontend/src/pages/OrderDetailPage.test.tsx` [CREATE 또는 MODIFY]

**작업 내용**:

프론트엔드 테스트 환경이 구성되어 있는 경우 다음 테스트를 작성한다:
- `renders confirmed_price column header` (REQ-009)
- `renders em dash for null confirmed_price` (REQ-010, 011)
- `renders margin_amount in summary section` (REQ-012)
- `renders em dash for null margin_amount` (REQ-013)
- `container has max-w-7xl class` (REQ-014)

> Note: 프론트엔드 단위 테스트 환경(Vitest + RTL)이 없는 경우 이 태스크는 건너뛰고 시각적 검증(TASK-005)으로 대체한다.

**완료 기준**: 테스트 5개 모두 FAIL (RED 상태)

---

## TASK-005 — Frontend: UI 구현 (GREEN)

**REQ 매핑**: REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014

**의존성**: TASK-003 완료 (TASK-004는 선택적)

**파일**:
- `frontend/src/pages/OrderDetailPage.tsx` [MODIFY]

**작업 내용**:

### 5-A: 컨테이너 폭 수정 (REQ-014)

Line 146:
```tsx
// BEFORE
<div className="p-6 max-w-4xl mx-auto space-y-6">
// AFTER
<div className="p-6 max-w-7xl mx-auto space-y-6">
```

### 5-B: 상품 테이블 헤더 컬럼 추가 (REQ-009)

Line 225 이후 (기존 `<th>소계</th>` 다음):
```tsx
<th className="py-2 px-3 text-right font-medium">확정 단가</th>
<th className="py-2 px-3 text-left font-medium">확정 발주처</th>
```

### 5-C: 상품 테이블 데이터 셀 추가 (REQ-010, REQ-011)

Line 264 이후 (기존 소계 `<td>` 다음 — `normalItems.map()` 내부):
```tsx
<td className="py-2 px-3 text-right">
  {item.confirmed_price
    ? Number(item.confirmed_price).toLocaleString()
    : '—'}
</td>
<td className="py-2 px-3">
  {item.confirmed_distributor ?? '—'}
</td>
```

`colSpan={7}` (line 231) → `colSpan={9}`로 변경 (컬럼 수 증가 반영).

### 5-D: 마진 정보 표시 (REQ-012, REQ-013)

Section 3 "결제 정보" (lines 335-344) 내 `max-w-xs ml-auto` div에 추가:
```tsx
{/* 마진 정보 — margin_amount가 null이면 표시하지 않거나 — 표시 */}
<div className="flex justify-between text-muted-foreground border-t pt-1 mt-1">
  <span>마진</span>
  <span>
    {data.margin_amount != null
      ? Number(data.margin_amount).toLocaleString()
      : '—'}
  </span>
</div>
<div className="flex justify-between text-muted-foreground">
  <span>마진율</span>
  <span>
    {data.margin_rate != null
      ? `${data.margin_rate}%`
      : '—'}
  </span>
</div>
```

**완료 기준**:
- TypeScript 컴파일 오류 없음
- TASK-004 테스트가 있는 경우 전체 통과
- 브라우저에서 시각적 확인 가능

---

## TASK-006 — Frontend: REFACTOR 및 최종 검증

**REQ 매핑**: 전체

**의존성**: TASK-005 완료

**파일**:
- `frontend/src/pages/OrderDetailPage.tsx` (검토만)
- `backend/order/serializers.py` (검토만)

**작업 내용**:

### 검토 체크리스트

1. `colSpan` 값이 실제 컬럼 수와 일치하는지 확인 (7 → 9)
2. 환불 테이블 섹션의 `colSpan`도 동일 변경 여부 확인 (환불 테이블은 별도 컬럼 구성이므로 변경 불필요)
3. `normalItems`만 새 컬럼을 추가하고 `refundedItems` 테이블은 별도 섹션이므로 영향 없음 확인
4. `margin_amount`가 음수인 경우 표시 형식 검토 (마진 손실 케이스 — `Number().toLocaleString()`은 음수 처리 정상)
5. `confirmed_price`가 `"0.00"`인 경우 `'—'` 대신 `"0"` 표시 여부 확인 (0은 falsy → `'—'` 처리됨 — 명시적 null 체크로 수정 고려)

> **주의**: `item.confirmed_price`가 `"0.00"`이면 `Number("0.00")` → `0` → falsy → `'—'` 표시.
> 이는 의도와 다를 수 있음. `item.confirmed_price != null` 조건으로 수정 권장.

### 수정 권장

```tsx
// BEFORE (falsy 체크 — "0.00" 케이스 오동작)
{item.confirmed_price
  ? Number(item.confirmed_price).toLocaleString()
  : '—'}

// AFTER (null 체크 — 명시적)
{item.confirmed_price != null
  ? Number(item.confirmed_price).toLocaleString()
  : '—'}
```

**완료 기준**:
```
pytest backend/order/tests/ -v           # 전체 통과, 회귀 없음
npx tsc --noEmit                         # 오류 없음
```

---

## 위험 매트릭스

| 위험 | 발생 시나리오 | 대응 전략 |
|------|-------------|----------|
| Decimal 연산 정밀도 | `confirmed_price * quantity` 부동소수점 오류 | `Decimal` 타입 유지 — `float()` 변환 금지. `str(Decimal * int)` 정상 동작 확인 |
| `total_price` 문자열 타입 | `obj.total_price`가 `"60000.00"` 문자열 → 나눗셈 오류 | `Decimal(obj.total_price or "0")` 변환 후 연산 |
| N+1 쿼리 | `get_margin_amount`에서 `obj.line_items.all()` 반복 호출 | `OrderDetailView`의 `prefetch_related("line_items")` 이미 존재 — 추가 쿼리 없음 |
| `colSpan` 불일치 | 컬럼 추가 후 `colSpan={7}` 미수정 시 테이블 레이아웃 깨짐 | TASK-005에서 `colSpan={9}`로 명시적 수정 |
| `"0.00"` falsy 오동작 | `confirmed_price = "0.00"` 케이스에서 `'—'` 잘못 표시 | TASK-006에서 `!= null` 조건으로 수정 |

---

## 레퍼런스 구현 (기존 코드 패턴)

| 패턴 | 위치 | 적용 태스크 |
|------|------|------------|
| `SerializerMethodField` 패턴 | `serializers.py` line 97 (`get_has_refund`) | TASK-002 |
| `Decimal` 직렬화 | `models.py` line 140 (`confirmed_price`) | TASK-002 |
| null → `'-'` 표시 | `OrderDetailPage.tsx` line 243 (`item.title ?? '-'`) | TASK-005 |
| `formatPrice()` 헬퍼 | `OrderDetailPage.tsx` lines 36-40 | TASK-005 (단, confirmed_price는 직접 포맷 — currency 불필요) |
| `colSpan` 패턴 | `OrderDetailPage.tsx` line 231 | TASK-005 |
| DRF 테스트 fixture 패턴 | `test_order_detail.py` lines 33-105 | TASK-001 |
