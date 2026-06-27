# SPEC-ORDER-008 구현 계획

## 개요

주문 상세 페이지 개선 3종을 최소한의 파일 수정으로 구현한다. DB 스키마 변경 없이 직렬화 레이어와 프론트엔드 레이어만 수정한다.

---

## 파일 변경 범위 (Delta 마커)

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `backend/order/serializers.py` | [MODIFY] | `LineItemDetailSerializer` 필드 추가 + `OrderDetailSerializer` 마진 computed fields |
| `frontend/src/types/order.ts` | [MODIFY] | `LineItemDetail` / `OrderDetail` 인터페이스 확장 |
| `frontend/src/pages/OrderDetailPage.tsx` | [MODIFY] | 테이블 컬럼 추가 + 마진 표시 + 컨테이너 폭 수정 |

총 수정 파일: 3개

---

## 구현 단계

### Phase 1 (Priority High): Backend 직렬화 수정

**대상 파일**: `backend/order/serializers.py`

**Task 1-1**: `LineItemDetailSerializer`에 필드 추가 [MODIFY] — 대응 REQ: REQ-001, REQ-002, REQ-003
- `confirmed_price`, `confirmed_distributor`, `confirmed_at` 3개 필드를 `fields` 튜플에 추가
- 추가 코드 없음 — `LineItem` 모델에 이미 존재하는 필드
- 구현 힌트: `LineItemDetailSerializer` 클래스 내 `fields` 선언 위치 (`backend/order/serializers.py` 약 lines 64–71)

**Task 1-2**: `OrderDetailSerializer`에 마진 computed fields 추가 [NEW] — 대응 REQ: REQ-004, REQ-005, REQ-006
- `margin_amount = SerializerMethodField()` 추가
- `margin_rate = SerializerMethodField()` 추가
- `get_margin_amount()`: `line_items`를 순회하여 `confirmed_price * quantity` 합산. `confirmed_price`가 전부 `None`이면 `None` 반환.
- `get_margin_rate()`: `margin_amount / total_price * 100`, 소수점 2자리 반올림. 예외 조건(0 나누기, `None`) 처리.
- 구현 힌트: `OrderDetailSerializer` 클래스 내 `SerializerMethodField` 패턴 사용. `Decimal` 타입 그대로 연산하여 float 변환 오류 방지.

**완료 기준**: 기존 테스트 통과 + 신규 단위 테스트 2개 이상 통과

---

### Phase 2 (Priority High): Frontend 타입 확장

**대상 파일**: `frontend/src/types/order.ts`

**Task 2-1**: `LineItemDetail` 인터페이스에 3개 필드 추가 [MODIFY] — 대응 REQ: REQ-007
- 구현 힌트: `frontend/src/types/order.ts` 내 `LineItemDetail` interface
```typescript
confirmed_price: string | null;
confirmed_distributor: string | null;
confirmed_at: string | null;
```

**Task 2-2**: `OrderDetail` 인터페이스에 2개 필드 추가 [MODIFY] — 대응 REQ: REQ-008
- 구현 힌트: `frontend/src/types/order.ts` 내 `OrderDetail` interface
```typescript
margin_amount: string | null;
margin_rate: string | null;
```

**완료 기준**: TypeScript 컴파일 오류 없음

---

### Phase 3 (Priority High): Frontend UI 수정

**대상 파일**: `frontend/src/pages/OrderDetailPage.tsx`

**Task 3-1**: 컨테이너 폭 수정 [MODIFY] — 대응 REQ: REQ-014
- `max-w-4xl` → `max-w-7xl`
- 구현 힌트: `frontend/src/pages/OrderDetailPage.tsx` 최상단 컨테이너 div의 className 속성 (약 line 146)

**Task 3-2**: 상품 테이블 헤더 컬럼 추가 [MODIFY] — 대응 REQ: REQ-009
- 기존 7컬럼(도서명/SKU/위치/수량/단가/할인/소계) 우측에 추가
- `확정 단가` 컬럼
- `확정 발주처` 컬럼

**Task 3-3**: 상품 테이블 데이터 셀 추가 [MODIFY] — 대응 REQ: REQ-010, REQ-011
- `confirmed_price`: `null`이면 `—` 표시, 값이 있으면 기존 price 포맷 방식 동일 적용 (천 단위 콤마, 소수점 제거)
- `confirmed_distributor`: `null`이면 `—` 표시

**Task 3-4**: 마진 정보 표시 영역 추가 [NEW] — 대응 REQ: REQ-012, REQ-013
- 주문 요약 섹션(금액 정보 카드) 하단에 마진 정보 행 추가
- `마진` 레이블 + `margin_amount` 값 (null이면 `—`)
- `마진율` 레이블 + `margin_rate` + `%` 단위 (null이면 `—`)

**완료 기준**: 화면에서 3가지 변경사항이 시각적으로 확인됨

---

## 위험 요소

| 위험 | 가능성 | 대응 |
|------|--------|------|
| `confirmed_price`가 `Decimal` 타입이므로 Python 연산 시 `float` 변환 오류 | 낮음 | `Decimal` 타입 그대로 연산, 최종 응답 시 `str` 직렬화 |
| `total_price`가 `"0.00"` 문자열로 직렬화되어 나눗셈 시 타입 오류 | 낮음 | `Decimal(self.total_price)` 변환 후 나눗셈 |
| `line_items` prefetch 없이 `get_margin_amount()` 호출 시 N+1 | 낮음 | 기존 `OrderDetailSerializer`가 `line_items`를 `nested serializer`로 이미 포함 — 추가 쿼리 없음 |
| 컬럼 추가로 테이블 수평 스크롤 필요 | 중간 | `max-w-7xl` 확장 + 기존 테이블에 `overflow-x-auto` 여부 확인 후 필요시 추가 |

---

## 의존성

- Phase 1 완료 후 Phase 2, 3 병렬 진행 가능
- Phase 2 완료 없이 Phase 3 TypeScript 타입 오류 발생 가능 → Phase 2 먼저 완료 권장
