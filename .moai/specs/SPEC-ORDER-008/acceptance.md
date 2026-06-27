# SPEC-ORDER-008 인수 기준

## 시나리오 1: 확정 단가·발주처가 설정된 주문 상세 API 응답

**적용 REQ**: REQ-001, REQ-004, REQ-005

**Given** `confirmed_price = 15000`, `confirmed_distributor = "교보문고"`, `quantity = 2` 인 `LineItem`이 존재하는 주문이 있을 때

**When** `GET /api/orders/{id}/` 를 호출하면

**Then**
- 응답의 `line_items[0].confirmed_price` 는 `"15000.00"` 이어야 한다
- 응답의 `line_items[0].confirmed_distributor` 는 `"교보문고"` 이어야 한다
- 응답의 `margin_amount` 는 `total_price - (15000 * 2)` 를 소수점 2자리로 반올림한 값이어야 한다
- 응답의 `margin_rate` 는 `(margin_amount / total_price) * 100` 를 소수점 2자리로 반올림한 값이어야 한다

---

## 시나리오 2: confirmed_price 미설정 상품이 포함된 주문 상세 API 응답

**적용 REQ**: REQ-002, REQ-003, REQ-004, REQ-005, REQ-006

**Given** line_item A: `confirmed_price = null`, line_item B: `confirmed_price = 8000, quantity = 3` 인 주문이 있을 때

**When** `GET /api/orders/{id}/` 를 호출하면

**Then**
- 응답의 `line_items[0].confirmed_price` (item A) 는 `null` 이어야 한다
- 응답의 `line_items[1].confirmed_price` (item B) 는 `"8000.00"` 이어야 한다
- 응답의 `margin_amount` 는 `total_price - (8000 * 3)` 값으로 item A를 제외한 부분 합산이어야 한다
- 응답의 `margin_rate` 는 `null` 이 아니어야 한다 (부분 합산 결과가 존재하므로)

---

## 시나리오 3: 모든 line_item의 confirmed_price가 null인 주문

**적용 REQ**: REQ-004, REQ-005

**Given** 모든 `LineItem`의 `confirmed_price`가 `null`인 주문이 있을 때

**When** `GET /api/orders/{id}/` 를 호출하면

**Then**
- 응답의 `margin_amount` 는 `null` 이어야 한다
- 응답의 `margin_rate` 는 `null` 이어야 한다

---

## 시나리오 4: 주문 상세 페이지 — 확정 단가·발주처 컬럼 표시

**적용 REQ**: REQ-007, REQ-009

**Given** 사용자가 `confirmed_price = 12000`, `confirmed_distributor = "영풍문고"` 인 line_item이 있는 주문 상세 페이지(`/orders/{id}`)에 접속했을 때

**When** 상품 목록 테이블이 렌더링되면

**Then**
- 테이블 헤더에 `확정 단가` 컬럼이 표시되어야 한다
- 테이블 헤더에 `확정 발주처` 컬럼이 표시되어야 한다
- 해당 행의 `확정 단가` 셀에 `12,000` 이 표시되어야 한다
- 해당 행의 `확정 발주처` 셀에 `영풍문고` 가 표시되어야 한다

---

## 시나리오 5: 주문 상세 페이지 — null 필드 플레이스홀더 표시

**적용 REQ**: REQ-010, REQ-011

**Given** `confirmed_price = null`, `confirmed_distributor = null` 인 line_item이 있는 주문 상세 페이지에 접속했을 때

**When** 상품 목록 테이블이 렌더링되면

**Then**
- 해당 행의 `확정 단가` 셀에 `—` (em dash) 가 표시되어야 한다
- 해당 행의 `확정 발주처` 셀에 `—` 가 표시되어야 한다

---

## 시나리오 6: 주문 상세 페이지 — 마진 정보 표시

**적용 REQ**: REQ-008, REQ-012

**Given** API 응답에 `margin_amount = "5000.00"`, `margin_rate = "25.00"` 이 포함된 주문 상세 페이지에 접속했을 때

**When** 주문 요약 섹션이 렌더링되면

**Then**
- 마진 금액 행에 `5,000` 이 표시되어야 한다
- 마진율 행에 `25.00%` 가 표시되어야 한다

---

## 시나리오 7: 주문 상세 페이지 — 컨테이너 폭 확장 및 null 마진 표시

**적용 REQ**: REQ-013, REQ-014

**Given** 관리자가 주문 상세 페이지(`/orders/{id}`)에 접속했을 때

**When** 페이지가 렌더링되면

**Then**
- 컨테이너의 최대 너비 CSS 클래스가 `max-w-7xl` 이어야 한다 (DOM 검사 기준)
- `max-w-4xl` 클래스가 컨테이너에 존재하지 않아야 한다

**Given** `margin_amount = null` 인 주문 상세 페이지에 접속했을 때

**When** 주문 요약 섹션이 렌더링되면

**Then**
- 마진 금액 셀에 `—` 가 표시되어야 한다
- 마진율 셀에 `—` 가 표시되어야 한다

---

## 엣지 케이스

| 케이스 | 적용 REQ | 기대 동작 |
|--------|----------|-----------|
| `total_price = "0.00"` 이고 `confirmed_price`가 존재 | REQ-005 | `margin_rate = null` 반환 (0 나누기 방지) |
| `confirmed_price`가 음수 | REQ-004 | 계산에 그대로 반영 (비즈니스 규칙 외부에서 처리) |
| line_item이 0개인 주문 | REQ-004, REQ-005 | `margin_amount = null`, `margin_rate = null` |
| `quantity = 0` | REQ-004, REQ-006 | `0 * confirmed_price = 0` 으로 합산에 포함 |

---

## Definition of Done

- [ ] `GET /api/orders/{id}/` 응답의 line_items에 `confirmed_price`, `confirmed_distributor`, `confirmed_at` 포함 (REQ-001)
- [ ] 미확정 필드가 `null`로 직렬화됨 (REQ-002, REQ-003)
- [ ] `OrderDetailSerializer`에 `margin_amount`, `margin_rate` SerializerMethodField 추가 (REQ-004, REQ-005)
- [ ] `confirmed_price = null`인 항목이 마진 계산에서 제외됨 (REQ-006)
- [ ] 백엔드 단위 테스트: 마진 계산 시나리오 2개 이상 신규 추가 및 통과
- [ ] 기존 `SPEC-ORDER-003` 관련 테스트 전체 통과 (회귀 없음)
- [ ] 프론트엔드 타입에 신규 필드 반영 (REQ-007, REQ-008)
- [ ] 상품 테이블에 `확정 단가`, `확정 발주처` 컬럼 추가 (REQ-009)
- [ ] null 필드 시 `—` 플레이스홀더 올바르게 표시 (REQ-010, REQ-011)
- [ ] 요약 섹션에 마진 금액·마진율 행 추가 (REQ-012, REQ-013)
- [ ] 컨테이너 최대 폭 `max-w-7xl` 적용 (REQ-014)
- [ ] TypeScript 컴파일 오류 없음
