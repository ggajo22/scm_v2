# SPEC-WAREHOUSE-001 인수 기준

---

## Given-When-Then 시나리오

### 시나리오 1 — 피벗 재고 목록 전체 조회

**Given:** `WarehouseStock` 테이블에 다음 데이터가 존재
- `(isbn="9788901234567", location="korea", quantity=10, id=1)`
- `(isbn="9788901234567", location="ca", quantity=5, id=2)`
- `(isbn="9788901234568", location="nj", quantity=3, id=7)`

**When:** 인증된 사용자가 `GET /api/warehouse/stock/` 호출

**Then:**
- HTTP 200 반환
- 응답 배열에 2개 항목 존재
- 첫 번째 항목: `{ isbn: "9788901234567", korea_qty: 10, korea_id: 1, ca_qty: 5, ca_id: 2, nj_qty: null, nj_id: null }`
- 두 번째 항목: `{ isbn: "9788901234568", korea_qty: null, korea_id: null, ca_qty: null, ca_id: null, nj_qty: 3, nj_id: 7 }`

---

### 시나리오 2 — ISBN 검색 필터

**Given:** `9788901234567`과 `9780000000000` ISBN 재고가 모두 등록된 상태

**When:** 인증된 사용자가 `GET /api/warehouse/stock/?isbn=97889` 호출

**Then:**
- HTTP 200 반환
- `9788901234567` ISBN 항목만 포함됨
- `9780000000000` ISBN 항목은 포함되지 않음

---

### 시나리오 3 — 단건 Upsert (신규 생성)

**Given:** `isbn="9780000000001"`, `location="nj"` 레코드가 DB에 없음

**When:** 인증된 사용자가 `POST /api/warehouse/stock/upsert/` `{ "isbn": "9780000000001", "location": "nj", "quantity": 3 }` 호출

**Then:**
- HTTP 200 반환
- DB에 해당 레코드 생성됨 (`quantity=3`)
- 응답 바디에 `id`, `isbn`, `location`, `quantity`, `updated_at` 필드 포함

---

### 시나리오 4 — 단건 Upsert (수량 갱신)

**Given:** `(isbn="9780000000001", location="nj", quantity=3)` 레코드 존재

**When:** 인증된 사용자가 `POST /api/warehouse/stock/upsert/` `{ "isbn": "9780000000001", "location": "nj", "quantity": 7 }` 호출

**Then:**
- HTTP 200 반환
- 기존 레코드의 `quantity`가 7로 갱신됨
- DB 내 `(isbn="9780000000001", location="nj")` 레코드가 정확히 1개만 존재

---

### 시나리오 5 — 일괄 등록 (Bulk Upsert)

**Given:** 빈 `WarehouseStock` 테이블

**When:** 인증된 사용자가 `POST /api/warehouse/stock/bulk/`
```json
[
  { "isbn": "A001", "location": "korea", "quantity": 1 },
  { "isbn": "B002", "location": "ca", "quantity": 2 }
]
```
호출

**Then:**
- HTTP 200 반환
- 응답 바디: `{ "upserted": 2 }`
- DB에 2개의 레코드 생성됨

---

### 시나리오 6 — 단건 삭제

**Given:** `id=5`인 `WarehouseStock` 레코드 존재

**When:** 인증된 사용자가 `DELETE /api/warehouse/stock/5/` 호출

**Then:**
- HTTP 204 No Content 반환
- 응답 바디 없음
- DB에서 해당 레코드 삭제됨

---

### 시나리오 7 — 존재하지 않는 레코드 삭제

**Given:** `id=999`인 레코드가 DB에 없음

**When:** 인증된 사용자가 `DELETE /api/warehouse/stock/999/` 호출

**Then:** HTTP 404 Not Found 반환

---

### 시나리오 8 — 유효하지 않은 위치값 거부

**Given:** 유효한 JWT 토큰

**When:** `POST /api/warehouse/stock/upsert/` `{ "isbn": "X", "location": "tokyo", "quantity": 1 }` 호출

**Then:** HTTP 400 Bad Request 반환

---

### 시나리오 9 — 인증 없는 접근 거부

**Given:** Authorization 헤더가 없음

**When:** `GET /api/warehouse/stock/` 호출

**Then:** HTTP 401 Unauthorized 반환

---

### 시나리오 10 — 빈 배열로 일괄 등록 시도

**Given:** 유효한 JWT 토큰

**When:** `POST /api/warehouse/stock/bulk/` `[]` 호출

**Then:** HTTP 400 Bad Request 반환

---

## 엣지 케이스

| 케이스 | 기대 동작 |
|--------|-----------|
| `quantity=0`으로 Upsert | 허용. 재고 0으로 설정됨 |
| 동일 `(isbn, location)` 조합으로 bulk 내 중복 항목 | 마지막 항목의 값으로 덮어씀 (Upsert 순서 의존) |
| isbn 파라미터 빈 문자열 (`?isbn=`) | 전체 목록 반환 (필터 미적용) |
| 재고 없는 상태에서 목록 조회 | HTTP 200 + 빈 배열 `[]` 반환 |

---

## 완료 정의 (Definition of Done)

- [x] `WarehouseStock` 모델 생성 및 마이그레이션 적용
- [x] 4개 API 엔드포인트 (`GET /stock/`, `POST /upsert/`, `POST /bulk/`, `DELETE /<pk>/`) 구현
- [x] JWT 인증 적용
- [x] 백엔드 테스트 11개 전체 통과
- [x] 프론트엔드 API 클라이언트 및 TanStack Query 훅 구현
- [x] `WarehouseStockPage` 컴포넌트 구현 (피벗 테이블, 검색, 추가/일괄등록/삭제 모달)
- [x] 사이드바 네비게이션 "창고 재고" 항목 추가
- [x] `/warehouse` 라우터 등록 (lazy-loading)
