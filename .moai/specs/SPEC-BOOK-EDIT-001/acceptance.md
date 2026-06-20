---
id: SPEC-BOOK-EDIT-001
version: "0.1.0"
status: draft
created: "2026-06-20"
updated: "2026-06-20"
author: ggajo
---

## 수락 기준 (Acceptance Criteria)

### 시나리오 1: 도서 상세 정보 전체 조회

**Given** 인증된 관리자가 유효한 JWT 토큰을 보유하고, `Inven.id=1` 도서가 Info, BookNote(미해결 1건), Shopify_product, EtoileBookInven, EtoileBookInfo를 모두 가진 상태  
**When** `GET /api/book/1/` 요청을 전송  
**Then**
- HTTP 200 OK 반환
- 응답 바디에 `info`, `notes`, `shopify_products`, `etoile` 키가 모두 존재
- `notes` 배열에 `is_resolved: false` 노트가 포함됨
- `etoile.info.tags` 필드가 배열 형태로 반환됨

---

### 시나리오 2: Etoile 없는 도서 조회

**Given** 인증된 관리자, `Inven.id=2` 도서가 `EtoileBookInven`을 보유하지 않는 상태  
**When** `GET /api/book/2/` 요청을 전송  
**Then**
- HTTP 200 OK 반환
- 응답 바디의 `etoile` 필드가 `null`

---

### 시나리오 3: 존재하지 않는 도서 조회

**Given** 인증된 관리자  
**When** `GET /api/book/99999/` 요청을 전송 (해당 ID 없음)  
**Then**
- HTTP 404 Not Found 반환

---

### 시나리오 4: 미인증 요청

**Given** JWT 토큰 없이 도서 상세 엔드포인트에 접근  
**When** `GET /api/book/1/` 요청을 전송  
**Then**
- HTTP 401 Unauthorized 반환

---

### 시나리오 5: 도서 기본 정보 부분 수정

**Given** 인증된 관리자, `Inven.id=1` 도서의 `Info.name`이 현재 "기존 제목"인 상태  
**When** `PATCH /api/book/1/info/` 요청을 `{"name": "수정된 제목", "price": "20000.00"}`으로 전송  
**Then**
- HTTP 200 OK 반환
- 응답 바디의 `name`이 "수정된 제목", `price`가 "20000.00"으로 반영
- DB `Info.updated_at`이 현재 시각으로 갱신됨
- 요청에 포함하지 않은 다른 필드는 변경되지 않음

---

### 시나리오 6: 잘못된 필드 값으로 수정 요청

**Given** 인증된 관리자  
**When** `PATCH /api/book/1/info/` 요청을 `{"price": "무효한값"}` (숫자가 아닌 문자열)으로 전송  
**Then**
- HTTP 400 Bad Request 반환
- 응답에 `price` 필드 오류 메시지 포함

---

### 시나리오 7: GENERAL 노트 생성

**Given** 인증된 관리자, `Inven.id=1` 도서  
**When** `POST /api/book/1/notes/` 요청을 `{"note_type": "GENERAL", "content": "재고 확인 필요"}`로 전송  
**Then**
- HTTP 201 Created 반환
- 응답에 `id`, `note_type: "GENERAL"`, `content: "재고 확인 필요"`, `is_resolved: false`, `created_by` 필드 포함
- DB에 `BookNote` 레코드 생성 확인

---

### 시나리오 8: GENERAL 노트 해결 처리

**Given** 인증된 관리자, `BookNote.id=1` (note_type: GENERAL, is_resolved: false)  
**When** `PATCH /api/book/notes/1/resolve/` 요청을 전송  
**Then**
- HTTP 200 OK 반환
- 응답의 `is_resolved`가 `true`, `resolved_at`이 현재 시각

---

### 시나리오 9: SHIPPING 노트 해결 시도 차단

**Given** 인증된 관리자, `BookNote.id=2` (note_type: SHIPPING)  
**When** `PATCH /api/book/notes/2/resolve/` 요청을 전송  
**Then**
- HTTP 400 Bad Request 반환

---

### 시나리오 10: 이미 해결된 노트 재해결 시도 차단

**Given** 인증된 관리자, `BookNote.id=3` (is_resolved: true)  
**When** `PATCH /api/book/notes/3/resolve/` 요청을 전송  
**Then**
- HTTP 400 Bad Request 반환

---

### 시나리오 11: Shopify 상태 active로 변경 (성공)

**Given** 인증된 관리자, `Inven.id=1` 도서, Shopify API mock이 성공 응답 반환하도록 설정  
**When** `PATCH /api/book/1/shopify-status/` 요청을 `{"action": "active"}`로 전송  
**Then**
- HTTP 200 OK 반환
- `Inven.status_of_shopify`가 DB에서 갱신됨
- 응답에 `action: "active"` 포함

---

### 시나리오 12: Shopify API 실패 시 DB 불변

**Given** 인증된 관리자, Shopify API mock이 500 오류 반환하도록 설정  
**When** `PATCH /api/book/1/shopify-status/` 요청을 전송  
**Then**
- HTTP 502 Bad Gateway 반환
- DB `Inven.status_of_shopify` 값 변경 없음

---

### 시나리오 13: Etoile 태그 업데이트

**Given** 인증된 관리자, `Inven.id=1` 도서에 EtoileBookInfo 존재, Shopify API mock 성공 설정  
**When** `PATCH /api/book/1/etoile-tags/` 요청을 `{"tags": ["신간", "추천"]}`로 전송  
**Then**
- HTTP 200 OK 반환
- `EtoileBookInfo.tags`가 `["신간", "추천"]`으로 DB 저장
- 응답의 `shopify_sync`가 `"success"`

---

### 시나리오 14: Etoile 없는 도서 Shopify 상태 변경 시도

**Given** 인증된 관리자, `Inven.id=2` 도서에 EtoileBookInven 없음  
**When** `PATCH /api/book/2/etoile-shopify-status/` 요청을 전송  
**Then**
- HTTP 404 Not Found 반환

---

### 시나리오 15: 프론트엔드 — 검색 → 수정 화면 이동

**Given** 관리자가 도서 검색 화면(`/book`)에서 검색 결과를 조회한 상태  
**When** 결과 테이블에서 특정 도서 행을 클릭  
**Then**
- 브라우저 URL이 `/book/{id}/edit`으로 변경
- `BookDetailPage`가 렌더링되며 해당 도서의 상세 정보가 표시됨
- 로딩 중 로딩 인디케이터 표시

---

### 시나리오 16: 프론트엔드 — 저장 성공 피드백

**Given** 관리자가 `BookDetailPage`에서 `name` 필드를 수정한 상태  
**When** 저장 버튼 클릭  
**Then**
- 성공 시 toast 또는 인라인 배너로 성공 메시지 표시
- 폼의 값이 저장된 값으로 유지됨

---

## 엣지 케이스

| 케이스 | 기대 동작 |
|--------|-----------|
| `BookNote` 없는 도서 조회 | `notes: []` 빈 배열 반환 |
| `Shopify_product` 없는 도서 조회 | `shopify_products: []` 빈 배열 반환 |
| PATCH 요청 바디가 빈 객체 `{}` | HTTP 200 OK, 아무 필드도 변경되지 않음 |
| `note_type`에 허용되지 않는 값 전달 | HTTP 400, 유효성 검사 오류 반환 |
| Etoile 태그 Shopify 동기화 실패 | HTTP 207, DB 저장은 완료, `shopify_sync: "failed"` 반환 |
| 동시에 여러 필드 수정 (전체 Info 필드) | 모든 필드 정상 저장, `updated_at` 갱신 |

---

## Definition of Done

- [ ] 모든 백엔드 API 엔드포인트가 `pytest`로 테스트되고 통과
- [ ] `GET /api/book/{id}/` N+1 쿼리 없이 `select_related`/`prefetch_related` 적용 확인
- [ ] 프론트엔드 `BookDetailPage` 빌드 오류 없음 (`npm run build` 통과)
- [ ] 도서 검색 → 수정 화면 이동 흐름 수동 확인
- [ ] JWT 미인증 시 401 반환 확인 (모든 엔드포인트)
- [ ] Shopify API 실패 시 DB 롤백 동작 확인
- [ ] `EtoileBookInven` 없는 도서에서 Etoile 섹션이 null-safe 처리됨 확인
- [ ] `SPEC-AUTH-001` 인증 플로우와 연동 확인
