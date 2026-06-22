---
id: SPEC-ORDER-005
version: "1.0.0"
status: completed
created: 2026-06-22
updated: 2026-06-22
author: ggajo
priority: High
issue_number: 0
---

# 주문 재동기화 시 환불(Refund) 미반영 버그 수정

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-22 | ggajo | 최초 작성 — 재동기화 시 환불 데이터 미반영 버그 SPEC 초안 |

---

## 문제 정의

`SPEC-ORDER-004`에서 구현된 주문 개별 재동기화(`POST /api/orders/{id}/sync/`) 기능은 `_sync_single_order()` 함수를 재사용하여 Shopify에서 단일 주문 데이터를 가져와 DB를 갱신한다.

그런데 `_sync_single_order()` 내부에는 관련 데이터 처리 방식의 불일치가 존재한다:

- **line_items**: 기존 레코드를 `order_obj.line_items.all().delete()`로 전부 삭제한 뒤 새로 `bulk_create`한다 (Clean-Slate 방식)
- **shipping_lines**: 동일하게 `order_obj.shipping_lines.all().delete()` 후 새로 `bulk_create`한다 (Clean-Slate 방식)
- **refunds**: `delete()` 없이 곧바로 `Refund.objects.update_or_create()` 루프를 실행한다 (Upsert 방식)

이 불일치로 인해 Shopify에서 환불이 취소(환불 되돌림)된 경우, DB에 남아 있는 환불 레코드가 삭제되지 않고 잔류한다. 그 결과, 주문 상세 페이지에서 "다시 동기화" 버튼을 눌러도 취소 상태(`has_refund=true`, 취소 배지 표시)가 해제되지 않는다.

동일한 `_sync_single_order()` 함수를 사용하는 전체 동기화(`sync_store`)도 같은 결함을 가진다.

---

## 솔루션 개요

`backend/order/shopify_orders.py`의 `_sync_single_order()` 함수에서 refunds 처리 루프 직전에 `order_obj.refunds.all().delete()`를 추가하여, line_items·shipping_lines와 동일한 Clean-Slate 방식으로 통일한다.

신규 테스트(`backend/order/tests/test_order_resync.py`)에 "재동기화 시 기존 환불 레코드가 삭제되고, Shopify에서 돌아온 최신 환불만 반영된다"는 검증 케이스를 추가한다.

**변경 범위**: 백엔드 1개 파일 수정(`shopify_orders.py`) + 테스트 1개 케이스 추가(`test_order_resync.py`). 프론트엔드·DB 마이그레이션·API 인터페이스 변경 없음.

---

## 요구사항 (EARS 형식)

### 환불 Clean-Slate 동기화

**REQ-RF-001** (Ubiquitous)
The `_sync_single_order()` 함수 **shall** refunds 처리 루프 실행 직전에 `order_obj.refunds.all().delete()`를 호출하여 해당 주문의 기존 환불 레코드를 모두 삭제한다.

**REQ-RF-002** (Event-Driven)
**When** `_sync_single_order()`가 실행되면, the 시스템 **shall** 다음 순서로 환불 데이터를 처리한다:
1. `order_obj.refunds.all().delete()` — 기존 환불 레코드 전체 삭제
2. Shopify `order_data["refunds"]` 리스트를 순회하며 `Refund.objects.update_or_create()` 실행
3. Shopify가 빈 `refunds` 리스트(`[]`)를 반환하면 환불 레코드 없음 상태가 된다

**REQ-RF-003** (Event-Driven)
**When** Shopify가 `refunds: []`(빈 배열)를 반환하면, the 시스템 **shall** 해당 주문에 연결된 모든 `Refund` 레코드를 DB에서 삭제한다.

**REQ-RF-004** (Event-Driven)
**When** Shopify가 새로운 `refunds` 목록을 반환하면, the 시스템 **shall** 삭제 후 `update_or_create()`를 통해 최신 환불 레코드만 DB에 존재하도록 보장한다.

**REQ-RF-005** (Ubiquitous)
The `_sync_single_order()` 함수 **shall** refunds Clean-Slate 처리 방식이 line_items·shipping_lines의 기존 패턴과 일관성을 유지한다:
- `order_obj.line_items.all().delete()` → `bulk_create(line_items)` (기존 패턴)
- `order_obj.shipping_lines.all().delete()` → `bulk_create(shipping_lines)` (기존 패턴)
- `order_obj.refunds.all().delete()` → `update_or_create()` 루프 (이번 수정)

**REQ-RF-006** (Ubiquitous)
The 시스템 **shall** `_sync_single_order()` 수정 이후에도 기존 전체 동기화(`sync_store`) 및 개별 재동기화(`OrderResyncView`, `POST /api/orders/{id}/sync/`)가 동일하게 영향을 받아 환불 데이터가 정확히 반영된다.

---

### 테스트 커버리지

**REQ-RF-007** (Ubiquitous)
The `backend/order/tests/test_order_resync.py` **shall** 다음 케이스를 포함하는 테스트를 보유한다:
- **케이스 A**: 재동기화 전 DB에 환불이 없었고, Shopify가 새 환불을 반환하는 경우 → 새 환불 레코드가 생성된다
- **케이스 B**: 재동기화 전 DB에 환불이 있었고, Shopify가 빈 환불 목록을 반환하는 경우 → 기존 환불 레코드가 삭제된다
- **케이스 C**: 재동기화 전 DB에 환불이 있었고, Shopify가 동일한 환불을 반환하는 경우 → 환불 레코드가 중복 생성되지 않는다 (DB 상 1건 유지)

**REQ-RF-008** (If-Then)
**If** DB에 `shopify_refund_id`가 동일한 `Refund` 레코드가 존재했다가 삭제 후 재생성된 경우, **then** the 시스템 **shall** `Refund` 레코드가 2개가 되지 않고 1개만 존재하도록 보장한다.

---

## 제외 사항 (What NOT to Build)

- **프론트엔드 변경**: `OrderDetailPage.tsx`를 포함한 프론트엔드 코드는 수정하지 않는다. 백엔드 환불 데이터가 정확히 반영되면 기존 `has_refund` 필드 로직에 의해 UI가 자동으로 올바르게 표시된다.
- **DB 마이그레이션**: `Refund` 모델 구조를 변경하지 않으므로 마이그레이션 파일이 필요 없다.
- **API 인터페이스 변경**: `POST /api/orders/{id}/sync/` 엔드포인트의 요청/응답 형식은 변경하지 않는다.
- **환불 소프트 딜리트**: DB에서 완전히 삭제하지 않고 `is_deleted` 플래그로 처리하는 소프트 딜리트 방식은 이 SPEC의 범위가 아니다.
- **환불 이력 보존**: 삭제된 환불 레코드를 별도 이력 테이블에 보관하는 기능은 포함하지 않는다.
- **line_items·shipping_lines 처리 방식 변경**: 이미 Clean-Slate 방식으로 동작 중이므로 변경 대상이 아니다.

---

## 기술적 접근 방식

### 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `[MODIFY] backend/order/shopify_orders.py` | 수정 | `_sync_single_order()` 내 refunds 루프 직전에 `delete()` 1줄 추가 |
| `[NEW] backend/order/tests/test_order_resync.py` | 추가 | 환불 Clean-Slate 검증 테스트 케이스 (케이스 A·B·C) |

### 수정 위치 상세

**`backend/order/shopify_orders.py`** — `_sync_single_order()` 함수

기존 코드 (약 163~177번째 줄 근방):
```
# 수정 전 — delete() 없이 바로 update_or_create 루프 진입
for refund_data in order_data.get("refunds", []):
    Refund.objects.update_or_create(
        order=order_obj,
        shopify_refund_id=refund_data["id"],
        defaults={...}
    )
```

수정 후:
```
# 수정 후 — line_items/shipping_lines 패턴과 동일하게 Clean-Slate 적용
order_obj.refunds.all().delete()          # ← 이 줄만 추가
for refund_data in order_data.get("refunds", []):
    Refund.objects.update_or_create(
        order=order_obj,
        shopify_refund_id=refund_data["id"],
        defaults={...}
    )
```

### 참조 패턴 (기존 코드에서 검증된 Clean-Slate 방식)

`_sync_single_order()`에서 이미 사용 중인 동일한 패턴 (약 126~161번째 줄):
- `order_obj.line_items.all().delete()` → `LineItem.objects.bulk_create(line_items)` (약 126~146번째 줄)
- `order_obj.shipping_lines.all().delete()` → `ShippingLine.objects.bulk_create(shipping_lines)` (약 148~161번째 줄)

### 영향 범위 확인

이 수정은 `_sync_single_order()` 함수 내부만 변경한다. 이 함수를 호출하는 모든 경로가 동일하게 영향을 받는다:
- `sync_store()` (전체 동기화 배치)
- `OrderResyncView.post()` (개별 재동기화, SPEC-ORDER-004 구현체)

### 관련 코드 위치 참조

| 파일 | 줄 범위 | 설명 |
|------|---------|------|
| `backend/order/shopify_orders.py` | ~126-177 | `_sync_single_order()` — 수정 대상 함수 |
| `backend/order/models.py` | ~140-154 | `Refund` 모델 — `order` FK, `shopify_refund_id` 필드 확인 |
| `backend/order/serializers.py` | ~87-112 | `OrderDetailSerializer` — `refunds`, `has_refund` 필드 직렬화 |
| `backend/order/views.py` | ~162-194 | `OrderResyncView` — `prefetch_related("refunds")` 로 조회 |
| `frontend/src/pages/OrderDetailPage.tsx` | ~119-123 | `has_refund` 체크로 취소 배지 표시 (변경 없음) |
| `backend/order/tests/test_order_resync.py` | — | 환불 Clean-Slate 테스트 추가 대상 |

---

## 의존성 (Dependencies)

- **SPEC-ORDER-001** — `Order`, `Refund` 모델, `_sync_single_order()` 함수의 전제 조건
- **SPEC-ORDER-004** — `OrderResyncView`가 이미 구현되어 있어야 한다. 이 SPEC은 그 내부에서 사용하는 `_sync_single_order()`의 버그를 수정한다
