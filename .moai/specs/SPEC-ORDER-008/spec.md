---
id: SPEC-ORDER-008
version: "1.0.0"
status: draft
created: 2026-06-24
updated: 2026-06-24
author: ggajo
priority: medium
issue_number: 7
---

## HISTORY

| 버전  | 날짜       | 작성자 | 변경 내용                          |
|-------|------------|--------|------------------------------------|
| 1.0.0 | 2026-06-24 | ggajo  | 최초 작성 — 주문 상세 페이지 개선 3종 |

---

## 문제 정의

`SPEC-ORDER-003`에서 구현된 주문 상세 페이지(`/orders/:id`)는 상품 목록 테이블에서 발주 확정 후 갱신되는 `confirmed_price` 및 `confirmed_distributor` 정보를 표시하지 않는다. 또한 주문 매출과 매입원가를 비교하는 마진 정보가 부재하여 운영 수익성 파악이 불가하다. 컨테이너 폭이 `max-w-4xl`(896px)로 제한되어 다수 컬럼을 표시하는 테이블이 좁게 렌더링된다.

---

## 목표

1. 상품 목록 테이블에 `confirmed_price`(확정 단가) 및 `confirmed_distributor`(확정 발주처) 컬럼을 추가한다.
2. 주문 총액 대비 매입 원가를 기반으로 마진 및 마진율을 계산·표시한다.
3. 컨테이너 최대 폭을 `max-w-4xl` → `max-w-7xl`로 확장한다.

---

## 관련 SPEC

- `SPEC-ORDER-003` v1.0.0 — 주문 상세 엔드포인트 (`GET /api/orders/:id/`) 및 상세 페이지 구현
- `SPEC-PURCHASE-ORDER-001` v1.2.0 — `confirmed_price` / `confirmed_distributor` 필드 보존 규칙
- `SPEC-ORDER-007` — 발주 확정 화면 (ConfirmOrderTab) — `confirmed_price` 저장 주체

---

## 요구사항 (EARS 형식)

### Module 1: 확정 단가·발주처 직렬화 (Backend)

**REQ-001 [MODIFY]** 주문 상세 API가 line item 목록을 반환할 때, 시스템은 각 line item의 `confirmed_price`, `confirmed_distributor`, `confirmed_at` 필드를 응답에 포함하여야 한다.

**REQ-002** When the API serializes a line item with no confirmed price set, the system **shall** return `confirmed_price` as `null`.

**REQ-003** When the API serializes a line item with no confirmed distributor set, the system **shall** return `confirmed_distributor` as `null`.

---

### Module 2: 마진 계산 직렬화 (Backend)

**REQ-004 [NEW]** The order detail API **shall** expose a computed field `margin_amount` defined as:

```
margin_amount = total_price - sum(confirmed_price * quantity for all line items where confirmed_price IS NOT NULL)
```

`confirmed_price`가 하나도 없을 때는 `null`을 반환한다.

**REQ-005 [NEW]** The order detail API **shall** expose a computed field `margin_rate` defined as:

```
margin_rate = (margin_amount / total_price) * 100  [소수점 2자리 반올림]
```

`total_price`가 0이거나 `margin_amount`가 `null`일 때는 `null`을 반환한다.

**REQ-006** While computing `margin_amount`, **when** a line item has `confirmed_price = null`, the system **shall** exclude that line item from the purchase cost sum (부분 합산 허용, 전체 null 처리 금지).

---

### Module 3: 프론트엔드 타입 확장 (Frontend Types)

**REQ-007 [MODIFY]** The frontend `LineItemDetail` type **shall** include `confirmed_price`, `confirmed_distributor`, `confirmed_at` as nullable fields to reflect the API response schema.

**REQ-008 [MODIFY]** The frontend `OrderDetail` type **shall** include `margin_amount` and `margin_rate` as nullable fields to reflect the API response schema.

---

### Module 4: 상품 테이블 UI 확장 (Frontend UI)

**REQ-009 [MODIFY]** When the order detail page renders the product list table, the system **shall** display `confirmed_price` and `confirmed_distributor` as additional columns to the right of the existing 7 columns.

**REQ-010** When `confirmed_price` is `null`, the system **shall** display a `—` (em dash) placeholder in the confirmed price cell.

**REQ-011** When `confirmed_distributor` is `null`, the system **shall** display a `—` placeholder in the confirmed distributor cell.

---

### Module 5: 마진 정보 표시 및 컨테이너 확장 (Frontend UI)

**REQ-012 [NEW]** When the order detail page renders the summary section, the system **shall** display `margin_amount` (마진 금액) and `margin_rate` (마진율 %) in a dedicated margin information row.

**REQ-013** When `margin_amount` is `null`, the system **shall** display `—` in the margin amount and margin rate cells.

**REQ-014 [MODIFY]** The order detail page container **shall** apply `max-w-7xl` as the maximum width constraint instead of the current `max-w-4xl`.

---

## 인수 기준 (Acceptance Criteria)

각 REQ에 대한 검증 가능한 기준을 정의한다. 상세 시나리오는 `acceptance.md` 참조.

| REQ | 인수 기준 요약 | acceptance.md 시나리오 |
|-----|---------------|------------------------|
| REQ-001 | `GET /api/orders/{id}/` 응답의 `line_items[*]`에 `confirmed_price`, `confirmed_distributor`, `confirmed_at` 키가 존재한다 | 시나리오 1, 2, 3 |
| REQ-002 | 미확정 line item의 `confirmed_price` 응답값이 `null`이다 | 시나리오 2 (item A) |
| REQ-003 | 미확정 line item의 `confirmed_distributor` 응답값이 `null`이다 | 시나리오 2 |
| REQ-004 | 응답에 `margin_amount` 키가 존재하며 계산값이 정확하다 | 시나리오 1, 2, 3 |
| REQ-005 | 응답에 `margin_rate` 키가 존재하며 소수점 2자리 값이다. `total_price = 0` 또는 전체 null이면 `null`이다 | 시나리오 1, 2, 3 |
| REQ-006 | `confirmed_price = null`인 line item은 `margin_amount` 계산에서 제외된다 | 시나리오 2 |
| REQ-007 | 프론트엔드가 `confirmed_price`, `confirmed_distributor`, `confirmed_at` 필드를 타입 오류 없이 소비한다 | 시나리오 4, 5 |
| REQ-008 | 프론트엔드가 `margin_amount`, `margin_rate` 필드를 타입 오류 없이 소비한다 | 시나리오 6 |
| REQ-009 | 상품 목록 테이블에 `확정 단가`, `확정 발주처` 헤더 컬럼이 렌더링된다 | 시나리오 4 |
| REQ-010 | `confirmed_price = null`인 행의 확정 단가 셀이 `—`을 표시한다 | 시나리오 5 |
| REQ-011 | `confirmed_distributor = null`인 행의 확정 발주처 셀이 `—`을 표시한다 | 시나리오 5 |
| REQ-012 | 주문 요약 섹션에 마진 금액 행과 마진율 행이 존재한다 | 시나리오 6 |
| REQ-013 | `margin_amount = null`이면 마진 금액 셀과 마진율 셀이 `—`을 표시한다 | 시나리오 7 (엣지 케이스) |
| REQ-014 | 페이지 컨테이너의 최대 너비 CSS 클래스가 `max-w-7xl`이며 `max-w-4xl`이 존재하지 않는다 | 시나리오 7 |

---

## 제약사항

- DB 스키마 변경 없음 — `confirmed_price`, `confirmed_distributor`, `confirmed_at` 필드는 이미 `LineItem` 모델에 존재한다.
- `margin_amount`·`margin_rate`는 DB 저장 없이 `SerializerMethodField`로 런타임 계산한다.
- 마진 계산에 사용하는 매입 단가는 `confirmed_price`만 사용한다 (`price` 필드 사용 금지).
- 기존 7개 컬럼의 순서·내용·스타일은 변경하지 않는다.
- `max-w-7xl` 이외 레이아웃 구조(padding, spacing, card 구성)는 변경하지 않는다.

---

## Exclusions (What NOT to Build)

- **마진 데이터 저장**: `margin_amount` / `margin_rate`를 DB 컬럼 또는 별도 모델로 영속화하지 않는다.
- **마진 기반 필터/정렬**: 주문 목록 페이지에 마진 기준 필터 또는 정렬 기능을 추가하지 않는다.
- **confirmed_price 편집 UI**: 이 SPEC은 조회·표시만 다루며, 확정 단가 입력·수정은 `SPEC-ORDER-007` 범위다.
- **confirmed_at 컬럼 표시**: `confirmed_at` 타임스탬프는 직렬화에는 포함하지만 테이블 컬럼으로 노출하지 않는다.
- **마진 알림·경고**: 마진율이 특정 임계치 이하일 때 경고를 표시하는 기능은 포함하지 않는다.
