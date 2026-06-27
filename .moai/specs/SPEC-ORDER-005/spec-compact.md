# SPEC-ORDER-005 Compact — 환불 Clean-Slate 버그 수정

---

## 요구사항 (EARS 형식)

**REQ-RF-001** (Ubiquitous)
The `_sync_single_order()` 함수 **shall** refunds 처리 루프 실행 직전에 `order_obj.refunds.all().delete()`를 호출하여 기존 환불 레코드를 모두 삭제한다.

**REQ-RF-002** (Event-Driven)
**When** `_sync_single_order()`가 실행되면, the 시스템 **shall** (1) `order_obj.refunds.all().delete()`, (2) `refunds` 리스트 순회 `update_or_create()` 순으로 환불 데이터를 처리한다.

**REQ-RF-003** (Event-Driven)
**When** Shopify가 `refunds: []`(빈 배열)를 반환하면, the 시스템 **shall** 해당 주문의 모든 `Refund` 레코드를 DB에서 삭제한다.

**REQ-RF-004** (Event-Driven)
**When** Shopify가 새로운 `refunds` 목록을 반환하면, the 시스템 **shall** 삭제 후 재생성하여 최신 환불 레코드만 DB에 존재하도록 보장한다.

**REQ-RF-005** (Ubiquitous)
The `_sync_single_order()` 함수 **shall** refunds 처리를 line_items·shipping_lines와 동일한 Clean-Slate 방식으로 유지한다.

**REQ-RF-006** (Ubiquitous)
The 시스템 **shall** `_sync_single_order()` 수정 이후 전체 동기화(`sync_store`)와 개별 재동기화(`OrderResyncView`) 모두에서 환불 데이터가 정확히 반영된다.

**REQ-RF-007** (Ubiquitous)
The `backend/order/tests/test_order_resync.py` **shall** 다음 세 케이스를 보유한다: (A) 신규 환불 반영, (B) 기존 환불 삭제, (C) 중복 생성 방지.

**REQ-RF-008** (If-Then)
**If** DB에 기존 환불이 존재했다가 삭제 후 동일 `shopify_refund_id`로 재생성된 경우, **then** the 시스템 **shall** `Refund` 레코드가 1건만 존재하도록 보장한다.

---

## 인수 기준 (Given-When-Then)

**시나리오 1 — 신규 환불 반영 (케이스 A)**
- Given: DB 환불 없는 주문, Shopify가 `refunds: [{ "id": "ref_001" }]` 반환
- When: `_sync_single_order()` 호출
- Then: `Refund.objects.filter(order=order).count() == 1`, `has_refund=true`

**시나리오 2 — 기존 환불 삭제 (케이스 B, 핵심 버그)**
- Given: DB에 `shopify_refund_id="ref_001"` 환불 1건, Shopify가 `refunds: []` 반환
- When: `_sync_single_order()` 호출
- Then: `Refund.objects.filter(order=order).count() == 0`, `has_refund=false`

**시나리오 3 — 중복 생성 방지 (케이스 C)**
- Given: DB에 `shopify_refund_id="ref_001"` 환불 1건, Shopify가 동일 `{ "id": "ref_001" }` 반환
- When: `_sync_single_order()` 호출
- Then: `Refund.objects.filter(order=order).count() == 1` (2건 아님)

**시나리오 4 — 환불 목록 교체**
- Given: DB에 `shopify_refund_id="ref_old"` 환불 1건, Shopify가 `{ "id": "ref_new" }` 반환
- When: `_sync_single_order()` 호출
- Then: `ref_old` 레코드 없음, `ref_new` 레코드 1건 존재

---

## 수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/order/shopify_orders.py` | 수정 | `_sync_single_order()` refunds 루프 직전 `order_obj.refunds.all().delete()` 1줄 추가 |
| `backend/order/tests/test_order_resync.py` | 추가 | 환불 Clean-Slate 검증 케이스 A·B·C |

---

## 제외 사항

- 프론트엔드 코드 변경 없음 (`has_refund` 로직으로 자동 반영)
- DB 마이그레이션 없음 (모델 변경 없음)
- API 인터페이스 변경 없음
- 환불 소프트 딜리트 또는 이력 보존 없음
- line_items·shipping_lines 처리 방식 변경 없음 (이미 올바름)
