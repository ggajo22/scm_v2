# SPEC-ORDER-010 인수 테스트

## 시나리오 1: 노트 생성 및 조회

**Given** 인증된 사용자가 있고, `orders_line_item.id = 1`인 line_item이 존재한다  
**When** `POST /api/orders/line-items/1/notes/` 요청을 `{"content": "배송 지연 확인 요망", "assignee": "한국창고"}`으로 보낸다  
**Then** HTTP 201이 반환되고, DB에 `LineItemNote(content="배송 지연 확인 요망", assignee="한국창고", is_resolved=False, author=request.user)`가 생성된다

**Given** 위 노트가 생성된 상태  
**When** `GET /api/orders/line-items/1/notes/` 요청을 보낸다  
**Then** HTTP 200과 함께 노트 목록이 반환되고, `is_resolved=false`인 노트가 포함된다

---

## 시나리오 2: 노트 해결 처리

**Given** `LineItemNote.id = 5`, `is_resolved=False`인 노트가 존재한다  
**When** `PATCH /api/orders/line-item-notes/5/resolve/` 요청을 보낸다  
**Then** HTTP 200과 `{"is_resolved": true}`가 반환되고, DB에서 `is_resolved=True`로 저장된다

**Given** 위 해결 처리 후  
**When** `GET /api/orders/line-item-notes/` (전체 미해결 목록) 요청을 보낸다  
**Then** 해결된 노트(id=5)는 목록에 포함되지 않는다

---

## 시나리오 3: 전체 미해결 노트 목록

**Given** 여러 line_item에 걸쳐 미해결 노트 3개, 해결된 노트 2개가 존재한다  
**When** `GET /api/orders/line-item-notes/` 요청을 보낸다  
**Then** HTTP 200과 함께 미해결 3개만 반환된다. 각 항목에 line_item, order, assignee 정보가 포함된다

---

## 시나리오 4: OrderDetail API에 노트 포함

**Given** `order.id = 100`, 해당 주문에 line_item 2개가 있고 각각 노트가 존재한다  
**When** `GET /api/orders/100/` 요청을 보낸다  
**Then** 응답 JSON의 `line_items[0].notes`에 노트 배열이 포함된다. DB 쿼리가 N+1 없이 처리된다 (prefetch)

---

## 시나리오 5: 데이터 마이그레이션

**Given** `orders_line_item.note = "긴급 처리 필요"`인 line_item 레코드가 존재한다  
**When** 마이그레이션 3단계(생성, 데이터 이전, 컬럼 제거)가 실행된다  
**Then** `orders_line_item_note` 테이블에 `content="긴급 처리 필요"`, `is_resolved=False`, `author=NULL`인 레코드가 생성되고, `orders_line_item.note` 컬럼은 제거된다

---

## 시나리오 6: 인증 미제공 시 거부

**Given** 인증 토큰 없이 요청한다  
**When** `GET /api/orders/line-item-notes/` 또는 `POST /api/orders/line-items/1/notes/` 요청을 보낸다  
**Then** HTTP 401이 반환된다

---

## 시나리오 7: UI - OrderDetailPage 인라인 노트

**Given** 사용자가 OrderDetailPage(`/orders/100`)에 접근한다  
**When** line_item 행의 노트 배지를 클릭한다  
**Then** 해당 행 아래에 노트 목록 패널이 펼쳐지고, 새 노트 입력 폼이 표시된다

**When** 폼에 content와 assignee를 입력하고 "추가" 버튼을 누른다  
**Then** 새 노트가 목록 맨 위에 추가되고 OrderDetail 쿼리가 갱신된다

---

## 시나리오 8: UI - LineItemNotesPage

**Given** `/line-item-notes` 페이지에 접근한다  
**When** 미해결 노트가 3개 존재한다  
**Then** 3개의 카드가 표시된다. 각 카드에 line_item 제목, assignee, 내용, 해결 버튼이 있다

**When** 카드의 "해결" 버튼을 클릭한다  
**Then** 해당 카드가 즉시(optimistic) 목록에서 제거된다

---

## 품질 게이트

- [ ] `backend/order/tests/test_line_item_notes.py` 전체 통과
- [ ] `GET /api/orders/<pk>/` 쿼리 수 기존 대비 증가 없음 (prefetch 확인)
- [ ] TypeScript `tsc --noEmit` 오류 없음
- [ ] assignee 필드에 허용되지 않은 값 입력 시 HTTP 400 반환
