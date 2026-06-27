# SPEC-ORDER-003 인수 기준

## 인수 시나리오 (Given-When-Then)

---

### 시나리오 1: 주문 상세 정상 조회 (백엔드)

**Given** 인증된 사용자가 있고, 데이터베이스에 ID=42인 주문이 존재하며, 해당 주문에 2개의 line_item, 1개의 shipping_line, shipping_address, customer가 연결되어 있음

**When** `GET /api/orders/42/` 요청을 전송

**Then**
- HTTP 200 응답 반환
- 응답 JSON에 `order_number`, `name`, `financial_status`, `fulfillment_status`, `total_price`, `currency` 포함
- `customer` 객체에 `first_name`, `last_name`, `email`, `phone` 포함
- `shipping_address` 객체에 `address1`, `city`, `zip`, `phone` 포함
- `line_items` 배열 길이가 2이며 각 항목에 `title`, `sku`, `quantity`, `price`, `total_discount` 포함
- `shipping_lines` 배열 길이가 1이며 `title`, `price` 포함

---

### 시나리오 2: 존재하지 않는 주문 조회 (백엔드)

**Given** 인증된 사용자, 데이터베이스에 ID=9999인 주문이 없음

**When** `GET /api/orders/9999/` 요청을 전송

**Then**
- HTTP 404 응답 반환

---

### 시나리오 3: 미인증 접근 차단 (백엔드)

**Given** 인증 토큰 없이 요청

**When** `GET /api/orders/42/` 요청을 전송

**Then**
- HTTP 401 또는 403 응답 반환

---

### 시나리오 4: 주문 목록에서 상세 페이지 이동 (프론트엔드)

**Given** 사용자가 `/orders` 주문 목록 페이지를 보고 있고, 목록에 최소 1개의 주문이 표시됨

**When** 사용자가 주문 행을 클릭

**Then**
- URL이 `/orders/{해당주문id}` 로 변경됨
- `OrderDetailPage`가 렌더링됨
- 페이지 로딩 중 스켈레톤 UI가 표시됨
- 데이터 로드 완료 후 주문명(예: "#1234")이 헤더에 표시됨

---

### 시나리오 5: 주문 상세 6개 섹션 렌더링 (프론트엔드)

**Given** `/orders/42`에 접근, ID=42 주문의 상세 데이터가 API에서 반환됨

**When** 페이지 로드 완료

**Then**
- 헤더에 주문명, 스토어 레이블, "← 주문 목록" 버튼, 상태 배지 2개(financial/fulfillment) 표시
- 섹션 1(주문 정보): order_number, 날짜, gateway 표시
- 섹션 2(상품 목록): line_items 테이블에 도서명, SKU, 수량, 단가, 할인, 소계 컬럼 표시
- 섹션 3(결제 정보): subtotal, 할인, 배송비, 세금, 총계 표시
- 섹션 4(배송 정보): 배송지 주소 정보 표시
- 섹션 5(고객 정보): 고객 성명, 이메일, 연락처 표시

---

### 시나리오 6: 환불 내역 조건부 렌더링 (프론트엔드)

**Given** 두 개의 주문 — 주문 A는 `has_refund: true`에 `refunds` 배열 포함, 주문 B는 `has_refund: false`

**When** 각 주문의 상세 페이지 로드

**Then**
- 주문 A: 섹션 6(환불 내역) 표시됨, `refunds` 항목별로 note, 날짜, 금액 표시
- 주문 B: 섹션 6(환불 내역) 렌더링되지 않음

---

### 시나리오 7: API 호출 실패 처리 (프론트엔드)

**Given** 사용자가 `/orders/42` 접근 시 네트워크 오류 또는 서버 오류(500) 발생

**When** `useOrderDetail(42)` 훅의 쿼리가 오류 상태로 전환

**Then**
- 에러 메시지 텍스트 표시
- "다시 시도" 버튼 표시
- "다시 시도" 버튼 클릭 시 API를 재호출

---

### 시나리오 8: 고객 정보 없는 주문 처리 (엣지 케이스)

**Given** guest checkout으로 생성된 주문, `customer` 필드가 `null`

**When** `/orders/{id}` 상세 페이지 로드

**Then**
- 페이지가 오류 없이 렌더링됨
- 섹션 5(고객 정보)에 "고객 정보 없음" 또는 빈 상태로 처리됨 (JS 에러 발생하지 않음)

---

### 시나리오 9: 뒤로가기 버튼 동작 (프론트엔드)

**Given** 사용자가 `/orders/42` 상세 페이지를 보고 있음

**When** "← 주문 목록" 버튼 클릭

**Then**
- URL이 `/orders`로 변경됨
- 주문 목록 페이지가 렌더링됨

---

## 품질 게이트 기준

### 백엔드 품질 게이트

- [ ] `OrderDetailSerializer` 단위 테스트: 중첩 필드 직렬화 검증
- [ ] `GET /api/orders/{id}/` 통합 테스트: 200, 404, 401 시나리오 전체 통과
- [ ] 기존 테스트 전체 통과 (회귀 없음)
- [ ] Django ORM N+1 쿼리 없음 (`select_related`, `prefetch_related` 사용)

### 프론트엔드 품질 게이트

- [ ] TypeScript 컴파일 오류 없음
- [ ] `OrderDetailPage`의 6개 섹션 모두 데이터 없을 때 crash 없음
- [ ] `null` customer, 빈 `line_items`, 빈 `refunds` 시나리오에서 렌더링 오류 없음
- [ ] Tailwind 클래스만 사용 (인라인 스타일 최소화)

---

## Definition of Done

- [ ] 백엔드: `GET /api/orders/{id}/` 엔드포인트 구현 완료 및 테스트 통과
- [ ] 프론트엔드: `/orders/:id` 라우트 및 `OrderDetailPage` 구현 완료
- [ ] 주문 목록 행 클릭 → 상세 페이지 이동 동작 확인
- [ ] 6개 섹션 정상 렌더링 확인
- [ ] 환불 섹션 조건부 렌더링 확인
- [ ] 로딩/에러/404 상태 처리 확인
- [ ] TypeScript 타입 오류 없음 확인
- [ ] 기존 주문 목록 기능(SPEC-ORDER-001, SPEC-ORDER-002) 회귀 없음 확인
