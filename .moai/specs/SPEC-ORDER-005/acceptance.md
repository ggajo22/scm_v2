# SPEC-ORDER-005 인수 기준 (Acceptance Criteria)

---

## 시나리오 1: 재동기화 — 신규 환불 반영 (케이스 A)

**Given** 로컬 DB에 환불 레코드가 없는 주문(`order_id=10`)이 존재하고,
Shopify API가 해당 주문에 대해 `refunds: [{ "id": "ref_001", ... }]` 1건을 반환하는 경우

**When** `_sync_single_order(order_data, store_type)`이 호출되면

**Then**
- `Refund.objects.filter(order=order)` 카운트가 1이다
- `shopify_refund_id="ref_001"` 레코드가 DB에 존재한다
- `has_refund=true`가 `OrderDetailSerializer`에 의해 직렬화된다

---

## 시나리오 2: 재동기화 — 기존 환불 삭제 (케이스 B, 핵심 버그 재현)

**Given** 로컬 DB에 `shopify_refund_id="ref_001"` 환불 레코드가 1건 있는 주문(`order_id=10`)이 존재하고,
Shopify API가 해당 주문에 대해 `refunds: []`(빈 배열)를 반환하는 경우

**When** `_sync_single_order(order_data, store_type)`이 호출되면

**Then**
- `Refund.objects.filter(order=order)` 카운트가 0이다
- DB에 `shopify_refund_id="ref_001"` 레코드가 더 이상 존재하지 않는다
- `has_refund=false`가 `OrderDetailSerializer`에 의해 직렬화된다
- 주문 상세 페이지에서 취소 배지가 표시되지 않는다 (프론트엔드 `has_refund` 체크 기준)

---

## 시나리오 3: 재동기화 — 동일 환불 중복 생성 없음 (케이스 C)

**Given** 로컬 DB에 `shopify_refund_id="ref_001"` 환불 레코드가 1건 있는 주문(`order_id=10`)이 존재하고,
Shopify API가 동일한 `{ "id": "ref_001", ... }` 환불 1건을 반환하는 경우

**When** `_sync_single_order(order_data, store_type)`이 호출되면

**Then**
- `Refund.objects.filter(order=order)` 카운트가 정확히 1이다 (2건이 되지 않는다)
- `shopify_refund_id="ref_001"` 레코드가 DB에 1건만 존재한다

---

## 시나리오 4: 재동기화 — 환불 목록 교체

**Given** 로컬 DB에 `shopify_refund_id="ref_old"` 환불 레코드가 1건 있는 주문(`order_id=10`)이 존재하고,
Shopify API가 다른 `{ "id": "ref_new", ... }` 환불 1건을 반환하는 경우

**When** `_sync_single_order(order_data, store_type)`이 호출되면

**Then**
- `Refund.objects.filter(order=order)` 카운트가 정확히 1이다
- DB에 `shopify_refund_id="ref_old"` 레코드가 존재하지 않는다
- DB에 `shopify_refund_id="ref_new"` 레코드가 존재한다

---

## 시나리오 5: Clean-Slate 일관성 — line_items, shipping_lines와 동일한 순서

**Given** `backend/order/shopify_orders.py`의 `_sync_single_order()` 함수를 읽었을 때

**When** line_items, shipping_lines, refunds 세 블록의 처리 순서를 확인하면

**Then**
- 각 블록은 `<related_manager>.all().delete()` 호출로 시작한다
- line_items: `order_obj.line_items.all().delete()` 존재
- shipping_lines: `order_obj.shipping_lines.all().delete()` 존재
- refunds: `order_obj.refunds.all().delete()` 존재 (이번 수정으로 추가)

---

## 시나리오 6: 전체 동기화(sync_store)에도 동일하게 적용

**Given** `sync_store()` 함수가 내부적으로 `_sync_single_order()`를 호출하고,
DB에 특정 주문에 대한 환불 레코드가 있으나 Shopify에서는 해당 환불이 없는 경우

**When** `sync_store()`가 실행되면

**Then**
- 해당 주문의 환불 레코드가 DB에서 삭제된다
- 개별 재동기화(`POST /api/orders/{id}/sync/`)와 동일한 결과가 보장된다

---

## 시나리오 7: 기존 재동기화 기능 회귀 없음

**Given** SPEC-ORDER-004에서 구현된 `POST /api/orders/{id}/sync/` 엔드포인트가 동작 중이고,
Shopify가 정상적인 환불 데이터를 반환하는 경우

**When** 인증된 관리자가 `POST /api/orders/5/sync/`를 호출하면

**Then**
- HTTP 200 응답이 반환된다
- `OrderDetailSerializer` 형식의 주문 상세 데이터가 반환된다 (SPEC-ORDER-004 시나리오 1과 동일)
- 환불 데이터가 올바르게 `refunds` 필드에 포함된다

---

## Definition of Done

- [ ] `backend/order/shopify_orders.py`의 `_sync_single_order()`에 `order_obj.refunds.all().delete()` 줄이 refunds 루프 직전에 추가되었다
- [ ] 테스트 케이스 A (신규 환불 반영) — 통과한다
- [ ] 테스트 케이스 B (기존 환불 삭제) — 통과한다 (핵심 버그 검증)
- [ ] 테스트 케이스 C (중복 생성 방지) — 통과한다
- [ ] 기존 `OrderResyncView` 관련 테스트가 깨지지 않는다 (회귀 없음)
- [ ] DB 마이그레이션 파일이 생성되지 않았다
- [ ] 프론트엔드 코드가 변경되지 않았다

---

## 품질 기준

- **단위 테스트**: `_sync_single_order()`를 직접 호출하는 형태로 작성하여 API 레이어와 분리
- **모킹 전략**: Shopify API 호출을 `unittest.mock.patch` 또는 `pytest-mock`으로 모의하여 외부 의존성 제거
- **회귀 방지**: SPEC-ORDER-004에서 작성된 `OrderResyncView` 관련 테스트를 모두 실행하여 통과 확인
- **커버리지**: `_sync_single_order()` 함수 내 refunds 블록 100% 커버리지
