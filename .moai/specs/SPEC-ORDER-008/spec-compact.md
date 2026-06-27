# SPEC-ORDER-008 Compact — 주문 상세 페이지 개선

## Requirements

### Backend

| ID | 요약 |
|----|------|
| REQ-001 | 주문 상세 API line item 응답에 `confirmed_price`, `confirmed_distributor`, `confirmed_at` 포함 [MODIFY] |
| REQ-002 | 미확정 `confirmed_price` → 직렬화 출력 `null` |
| REQ-003 | 미확정 `confirmed_distributor` → 직렬화 출력 `null` |
| REQ-004 | 주문 상세 API — `margin_amount` computed field 추가 [NEW]: `total_price - sum(confirmed_price * quantity)`, 전부 null이면 null |
| REQ-005 | 주문 상세 API — `margin_rate` computed field 추가 [NEW]: `(margin_amount / total_price) * 100` 소수점 2자리, total_price=0 또는 margin_amount=null이면 null |
| REQ-006 | `confirmed_price = null`인 line_item은 매입 원가 합산에서 제외 (부분 합산 허용) |

### Frontend Types

| ID | 요약 |
|----|------|
| REQ-007 | 프론트엔드 `LineItemDetail` 타입 — `confirmed_price`, `confirmed_distributor`, `confirmed_at` 추가 (`string \| null`) [MODIFY] |
| REQ-008 | 프론트엔드 `OrderDetail` 타입 — `margin_amount`, `margin_rate` 추가 (`string \| null`) [MODIFY] |

### Frontend UI

| ID | 요약 |
|----|------|
| REQ-009 | 상품 목록 테이블 — 기존 7컬럼 우측에 `확정 단가`, `확정 발주처` 컬럼 추가 [MODIFY] |
| REQ-010 | `confirmed_price = null` → 셀에 `—` 표시 |
| REQ-011 | `confirmed_distributor = null` → 셀에 `—` 표시 |
| REQ-012 | 주문 요약 섹션 — 마진 금액·마진율 표시 행 추가 [NEW] |
| REQ-013 | `margin_amount = null` → 마진 금액·마진율 셀에 `—` 표시 |
| REQ-014 | 주문 상세 페이지 컨테이너 — `max-w-4xl` → `max-w-7xl` [MODIFY] |

---

## Acceptance Criteria (요약)

| 시나리오 | 적용 REQ | 검증 대상 |
|----------|----------|-----------|
| 시나리오 1 | REQ-001, REQ-004, REQ-005 | 확정 단가·발주처 설정 시 API 응답 정확성 |
| 시나리오 2 | REQ-002, REQ-003, REQ-004, REQ-005, REQ-006 | 부분 null 포함 시 부분 합산 |
| 시나리오 3 | REQ-004, REQ-005 | 전체 null 시 margin = null |
| 시나리오 4 | REQ-007, REQ-009 | 확정 단가·발주처 컬럼 렌더링 |
| 시나리오 5 | REQ-010, REQ-011 | null 필드 `—` 플레이스홀더 |
| 시나리오 6 | REQ-008, REQ-012 | 마진 정보 표시 |
| 시나리오 7 | REQ-013, REQ-014 | 컨테이너 폭 확장 + null 마진 표시 |

---

## Exclusions

- 마진 데이터 DB 저장 금지
- 마진 기반 필터/정렬 금지
- `confirmed_price` 편집 UI 금지 (SPEC-ORDER-007 범위)
- `confirmed_at` 컬럼 UI 노출 금지
- 마진 임계치 경고 기능 금지

---

## Files Impacted

```
backend/order/serializers.py           [MODIFY]
frontend/src/types/order.ts            [MODIFY]
frontend/src/pages/OrderDetailPage.tsx [MODIFY]
```
