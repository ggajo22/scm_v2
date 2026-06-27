# SPEC-ORDER-004 인수 기준 (Acceptance Criteria)

---

## 시나리오 1: 정상 재동기화 — 백엔드

**Given** 로컬 DB에 `id=5`, `store_type="gimssine"`, `shopify_order_id=123456789`인 주문이 존재하고,
`settings.SHOPIFY_STORES["gimssine"]`에 유효한 `domain`과 `token`이 설정되어 있으며,
Shopify API가 해당 주문의 최신 데이터를 정상 반환하는 경우

**When** 인증된 관리자가 `POST /api/orders/5/sync/`를 호출하면

**Then**
- HTTP 200 응답이 반환된다
- 응답 바디는 `OrderDetailSerializer` 형식의 주문 상세 데이터를 포함한다 (order, customer, shipping_address, line_items, shipping_lines, refunds 필드 포함)
- `_sync_single_order`가 호출되어 DB가 Shopify 최신 데이터로 업서트된다

---

## 시나리오 2: 주문 없음 — 로컬 DB 404

**Given** 로컬 DB에 `id=9999`인 주문이 존재하지 않는 경우

**When** 인증된 관리자가 `POST /api/orders/9999/sync/`를 호출하면

**Then**
- HTTP 404 응답이 반환된다
- Shopify API는 호출되지 않는다

---

## 시나리오 3: Shopify API 오류 — HTTP 502

**Given** 로컬 DB에 주문이 존재하고, Shopify API 호출 시 `urllib.error.URLError`(네트워크 타임아웃 등)가 발생하는 경우

**When** 인증된 관리자가 `POST /api/orders/5/sync/`를 호출하면

**Then**
- HTTP 502 응답이 반환된다
- 응답 바디에 `{"error": "<에러 메시지>"}` JSON이 포함된다
- DB 상태는 변경되지 않는다

---

## 시나리오 4: Shopify에서 주문 삭제 — HTTP 404

**Given** 로컬 DB에 주문이 존재하지만, Shopify에서 해당 주문이 이미 삭제되어 Shopify API가 HTTP 404를 반환하는 경우

**When** 인증된 관리자가 `POST /api/orders/5/sync/`를 호출하면

**Then**
- HTTP 404 응답이 반환된다
- 응답 바디에 `{"error": "Shopify에서 주문을 찾을 수 없습니다."}` JSON이 포함된다
- 로컬 DB의 주문 레코드는 삭제되지 않는다

---

## 시나리오 5: 인증 없이 호출 — HTTP 401

**Given** JWT 토큰이 없는 상태인 경우

**When** `POST /api/orders/5/sync/`를 호출하면

**Then**
- HTTP 401 응답이 반환된다

---

## 시나리오 6: URL 패턴 충돌 없음

**Given** `backend/order/urls.py`에 `orders/<int:pk>/sync/` 패턴이 `orders/<int:pk>/` 패턴보다 앞에 등록된 경우

**When** `POST /api/orders/5/sync/`와 `GET /api/orders/5/` 각각을 호출하면

**Then**
- `POST /api/orders/5/sync/`는 `OrderResyncView`로 라우팅된다
- `GET /api/orders/5/`는 `OrderDetailView`로 라우팅된다 (기존 동작 유지)

---

## 시나리오 7: 재동기화 버튼 정상 표시 — 프론트엔드

**Given** 사용자가 `/orders/5` 주문 상세 페이지를 열어 데이터가 로드된 경우

**When** 페이지가 완전히 렌더링되면

**Then**
- 헤더 영역의 상태 배지 인근에 "다시 동기화" 버튼이 표시된다
- 버튼은 활성화(`enabled`) 상태이다

---

## 시나리오 8: 재동기화 진행 중 — 로딩 상태

**Given** 사용자가 "다시 동기화" 버튼을 클릭하여 API 호출이 진행 중인 경우

**When** API 응답을 대기하는 동안

**Then**
- 버튼은 비활성화(`disabled`) 상태로 전환된다
- 버튼 텍스트가 "동기화 중..."으로 변경된다
- 버튼을 다시 클릭해도 중복 요청이 발생하지 않는다

---

## 시나리오 9: 재동기화 성공 — 화면 갱신

**Given** 사용자가 "다시 동기화" 버튼을 클릭하여 `POST /api/orders/5/sync/`가 HTTP 200으로 응답한 경우

**When** API 성공 응답이 수신되면

**Then**
- `queryClient.invalidateQueries({ queryKey: ['order-detail', 5] })`가 호출된다
- TanStack Query가 자동으로 `GET /api/orders/5/`를 리페치한다
- 화면에 갱신된 주문 데이터가 표시된다
- 버튼은 "다시 동기화" 텍스트로 복귀하고 다시 활성화된다

---

## 시나리오 10: 재동기화 실패 — 에러 메시지

**Given** 사용자가 "다시 동기화" 버튼을 클릭하였으나 API가 HTTP 502를 반환하고 응답 바디에 `{"error": "Connection timeout"}` JSON이 포함된 경우

**When** API 오류 응답이 수신되면

**Then**
- 버튼 인근에 "Connection timeout" 에러 메시지가 표시된다
- 버튼은 활성화 상태로 복귀하여 재시도 가능하다
- 이전 주문 상세 데이터는 그대로 유지된다 (화면이 지워지거나 초기화되지 않음)

---

## Definition of Done

- [ ] `POST /api/orders/{id}/sync/` 엔드포인트가 정상 동작한다 (시나리오 1~6 통과)
- [ ] `backend/order/urls.py`에서 `sync/` 패턴이 `<int:pk>/` 패턴보다 앞에 위치한다
- [ ] `OrderDetailPage.tsx`에 "다시 동기화" 버튼이 추가되어 있다 (시나리오 7~10 통과)
- [ ] JWT 인증 없이 엔드포인트에 접근하면 HTTP 401을 반환한다 (시나리오 5 통과)
- [ ] 버튼 로딩 상태(비활성화 + "동기화 중...") 동작이 확인된다
- [ ] 성공 시 쿼리 무효화로 화면이 자동 갱신된다
- [ ] 실패 시 에러 메시지가 표시되고 이전 데이터가 유지된다
- [ ] 기존 `GET /api/orders/{id}/` 엔드포인트(SPEC-ORDER-003)의 동작에 영향이 없다
- [ ] DB 마이그레이션 파일이 생성되지 않았다 (모델 변경 없음)

---

## 품질 기준

- **백엔드**: `OrderResyncView`에 대한 단위 테스트 작성 (정상, 로컬 404, Shopify 502, Shopify 404, 인증 없음 케이스)
- **프론트엔드**: 버튼 렌더링 및 mutation 상태 전환에 대한 컴포넌트 테스트 작성 권장
- **회귀 방지**: `GET /api/orders/{id}/`(OrderDetailView) 기존 동작이 영향받지 않음을 기존 테스트로 검증
