# SPEC-ORDER-005 구현 계획

## 개요

`_sync_single_order()` 함수의 refunds 처리 누락된 `delete()` 호출 1줄을 추가하고, 해당 버그를 검증하는 테스트를 작성한다. 변경 규모는 최소(1줄 수정 + 테스트 3케이스)이나 영향 범위는 전체 동기화와 개별 재동기화 모두에 해당된다.

---

## 구현 범위

### 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/order/shopify_orders.py` | 수정 | `_sync_single_order()` refunds 루프 직전 `order_obj.refunds.all().delete()` 1줄 삽입 |
| `backend/order/tests/test_order_resync.py` | 추가/수정 | 환불 Clean-Slate 검증 케이스 A·B·C 추가 |

### 변경하지 않는 파일

- `backend/order/models.py` — `Refund` 모델 구조 변경 없음
- `backend/order/serializers.py` — `OrderDetailSerializer` 변경 없음
- `backend/order/views.py` — `OrderResyncView` 변경 없음
- `backend/order/urls.py` — URL 패턴 변경 없음
- `frontend/src/pages/OrderDetailPage.tsx` — 프론트엔드 변경 없음
- DB 마이그레이션 파일 — 모델 변경 없으므로 불필요

---

## 구현 마일스톤

### Priority High

**M1. 버그 수정 — `_sync_single_order()` 1줄 추가**

목표: REQ-RF-001, REQ-RF-002, REQ-RF-003, REQ-RF-004, REQ-RF-005, REQ-RF-006 충족

작업 내용:
1. `backend/order/shopify_orders.py` 열기
2. `_sync_single_order()` 함수 내 refunds 처리 시작 위치 확인 (기존 line_items `delete()` 패턴이 있는 줄 구조를 참고)
3. `for refund_data in order_data.get("refunds", []):` 직전에 `order_obj.refunds.all().delete()` 삽입
4. 수정 후 line_items · shipping_lines · refunds 세 블록 모두 Clean-Slate 방식임을 시각적으로 확인

수정 전후 비교:
```
# 수정 전
for refund_data in order_data.get("refunds", []):
    Refund.objects.update_or_create(...)

# 수정 후
order_obj.refunds.all().delete()   ← 이 줄만 추가
for refund_data in order_data.get("refunds", []):
    Refund.objects.update_or_create(...)
```

참조 패턴 (기존 코드, ~126~161번째 줄):
```
# line_items (기존 — 참고용)
order_obj.line_items.all().delete()
line_items = [LineItem(...) for li in order_data.get("line_items", [])]
if line_items:
    LineItem.objects.bulk_create(line_items)

# shipping_lines (기존 — 참고용)
order_obj.shipping_lines.all().delete()
shipping_lines = [ShippingLine(...) for sl in order_data.get("shipping_lines", [])]
if shipping_lines:
    ShippingLine.objects.bulk_create(shipping_lines)
```

**M2. 테스트 작성 — 환불 Clean-Slate 케이스 A·B·C**

목표: REQ-RF-007, REQ-RF-008 충족

작업 내용:
1. `backend/order/tests/test_order_resync.py` 확인 (이미 존재하는 경우 기존 클래스에 케이스 추가, 없으면 신규 파일 생성)
2. 케이스 A — 신규 환불 반영 확인:
   - DB에 환불 없는 주문 생성
   - Shopify 응답에 환불 1건 포함 모의(mock)
   - `_sync_single_order()` 호출
   - DB `Refund.objects.filter(order=order)` 카운트 == 1 검증
3. 케이스 B — 환불 삭제 확인 (핵심 버그 재현):
   - DB에 환불 1건 있는 주문 생성
   - Shopify 응답에 환불 빈 리스트(`[]`) 모의
   - `_sync_single_order()` 호출
   - DB `Refund.objects.filter(order=order)` 카운트 == 0 검증
4. 케이스 C — 중복 생성 방지 확인:
   - DB에 `shopify_refund_id="ref_001"` 환불 1건 있는 주문 생성
   - Shopify 응답에 동일 `id="ref_001"` 환불 1건 포함 모의
   - `_sync_single_order()` 호출
   - DB `Refund.objects.filter(order=order)` 카운트 == 1 검증 (2건 아님)

테스트 작성 시 유의 사항:
- `factory-boy`로 `Order`, `Refund` 픽스처 생성 (기존 테스트 패턴 참조)
- Shopify API 호출은 `unittest.mock.patch` 또는 `pytest-mock`으로 모의
- `_sync_single_order(order_data, store_type)` 함수를 직접 호출하는 단위 테스트 형태

---

## 기술적 위험 요소

| 위험 | 설명 | 완화 방안 |
|------|------|-----------|
| 트랜잭션 부재 | `delete()` 후 `update_or_create()` 중 오류 발생 시 환불 레코드가 삭제된 채로 남을 수 있음 | 현재 `_sync_single_order()`가 트랜잭션으로 묶여 있는지 확인. 없다면 `@transaction.atomic` 데코레이터 적용 권장 (별도 SPEC 범위이나 주의 필요) |
| `Refund` FK 제약 | `order_obj.refunds.all().delete()` 호출 시 `Refund`가 다른 테이블과 FK 관계가 있으면 `ProtectedError` 발생 가능 | 구현 전 `backend/order/models.py` `Refund` 모델의 FK 관계 확인 |
| 기존 테스트 파일 존재 여부 | `test_order_resync.py`가 이미 존재하면 기존 코드와 충돌 가능성 있음 | 파일 열어 기존 클래스 구조 확인 후 메서드만 추가 |
| `update_or_create` 시맨틱 유지 | Clean-Slate 적용 후에도 `update_or_create`를 유지하는 이유는 향후 Upsert 전환을 고려한 최소 변경 원칙 때문 | 수정 범위를 `delete()` 1줄 추가로 제한 |

---

## MX 태그 전략

| 위치 | 태그 유형 | 이유 |
|------|-----------|------|
| `_sync_single_order()` — refunds 블록 직전 | `@MX:NOTE` | Clean-Slate 방식 적용 이유 설명 (line_items, shipping_lines와 동일 패턴임을 명시) |
| `_sync_single_order()` 함수 전체 | `@MX:WARN` | 세 관련 데이터(line_items, shipping_lines, refunds)를 모두 삭제-재생성하므로, 이 함수를 수정할 때 세 블록 모두 일관성을 유지해야 함을 경고 |

---

## 구현 완료 조건

- [ ] `_sync_single_order()` 내 `order_obj.refunds.all().delete()` 줄이 refunds 루프 직전에 위치한다
- [ ] `test_order_resync.py`에 케이스 A·B·C가 모두 존재하고 통과한다
- [ ] 기존 재동기화 테스트(`OrderResyncView` 관련)가 깨지지 않는다
- [ ] DB 마이그레이션 파일이 생성되지 않았다

---

## 의존성 확인 체크리스트

구현 시작 전 다음 항목을 확인한다:

- [ ] `backend/order/shopify_orders.py`에서 `_sync_single_order()` 함수 내 refunds 처리 위치(정확한 줄 번호) 확인
- [ ] `backend/order/models.py`에서 `Refund` 모델의 FK 관계 및 `related_name` 확인 (`order_obj.refunds`가 올바른 역참조 이름인지 검증)
- [ ] `backend/order/tests/test_order_resync.py` 파일 존재 여부 및 기존 테스트 구조 확인
- [ ] 기존 테스트에서 사용 중인 Factory, Mock 패턴 확인 (일관성 유지)
