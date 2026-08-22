---
id: SPEC-ETOILE-INVEN-ADD-001
type: acceptance
status: Planned
created: 2026-06-20
updated: 2026-06-20
---

## 수용 기준 (Acceptance Criteria)

### 시나리오 1 — 본관에 없는 SKU 일괄 등록 (신규 Inven + 신규 EtoileBookInven)

**Given** 본관(`Inven`)에도 Etoile(`EtoileBookInven`)에도 존재하지 않는 SKU `["A", "B"]`가 있고  
**When** 인증된 관리자가 `POST /api/book/etoile-inven-skus/`에 `{"skus": ["A", "B"]}`를 전송하면  
**Then**
- HTTP 200 응답이 반환된다
- `Inven` 테이블에 SKU `A`, `B`의 레코드가 생성된다 (`vendor="북센"`, `store="책방"`, `is_prepared=0`, `status_of_shopify=0`, `is_use=1`)
- `EtoileBookInven` 테이블에 SKU `A`, `B`의 레코드가 생성된다 (`status_of_shopify=-1`)
- 응답 본문: `book_created_skus=["A","B"]`, `etoile_created_new_book_skus=["A","B"]`, `etoile_created_existing_book_skus=[]`, `etoile_existing_skus=[]`
- `book_created_count=2`, `etoile_created_new_book_count=2`, `etoile_created_existing_book_count=0`, `etoile_existing_count=0`

---

### 시나리오 2 — 본관에 있는 SKU 일괄 등록 (EtoileBookInven만 신규 생성)

**Given** 본관(`Inven`)에는 존재하지만 Etoile(`EtoileBookInven`)에는 없는 SKU `["C", "D"]`가 있고  
**When** 인증된 관리자가 `POST /api/book/etoile-inven-skus/`에 `{"skus": ["C", "D"]}`를 전송하면  
**Then**
- HTTP 200 응답이 반환된다
- `Inven` 테이블에 신규 레코드가 생성되지 않는다
- `EtoileBookInven` 테이블에 SKU `C`, `D`의 레코드가 생성된다 (`status_of_shopify=0`)
- 응답 본문: `book_created_skus=[]`, `etoile_created_new_book_skus=[]`, `etoile_created_existing_book_skus=["C","D"]`, `etoile_existing_skus=[]`

---

### 시나리오 3 — Etoile에 이미 존재하는 SKU (중복 건너뜀)

**Given** `EtoileBookInven`에 이미 존재하는 SKU `["E"]`가 있고  
**When** 인증된 관리자가 `POST /api/book/etoile-inven-skus/`에 `{"skus": ["E"]}`를 전송하면  
**Then**
- HTTP 200 응답이 반환된다
- `Inven` 테이블 변경 없음
- `EtoileBookInven` 테이블 변경 없음
- 응답 본문: `etoile_existing_skus=["E"]`, 나머지 배열은 모두 빈 배열
- `etoile_existing_count=1`

---

### 시나리오 4 — 혼합 케이스 (3가지 상황 동시 처리)

**Given**
- SKU `"F"`: 본관에도 Etoile에도 없음
- SKU `"G"`: 본관에 있고 Etoile에 없음
- SKU `"H"`: Etoile에 이미 존재  
**When** 인증된 관리자가 `POST /api/book/etoile-inven-skus/`에 `{"skus": ["F", "G", "H"]}`를 전송하면  
**Then**
- HTTP 200 응답이 반환된다
- `book_created_skus=["F"]`
- `etoile_created_new_book_skus=["F"]` (status_of_shopify=-1)
- `etoile_created_existing_book_skus=["G"]` (status_of_shopify=0)
- `etoile_existing_skus=["H"]`
- 각 count 값이 정확히 1

---

### 시나리오 5 — 중복 입력 SKU 처리

**Given** 동일한 SKU `"I"`가 중복 포함된 입력이 있고  
**When** 인증된 관리자가 `POST /api/book/etoile-inven-skus/`에 `{"skus": ["I", "I", "I"]}`를 전송하면  
**Then**
- `"I"`에 대한 처리가 정확히 1회만 수행된다
- `Inven` 테이블에 `"I"` 레코드가 1개만 생성된다 (신규인 경우)
- 중복 처리 오류 없이 정상 응답이 반환된다

---

### 시나리오 6 — 공백 포함 SKU 처리

**Given** 공백이 포함된 SKU 입력이 있고  
**When** 인증된 관리자가 `{"skus": ["  J  ", "", "K"]}`를 전송하면  
**Then**
- `"J"` (strip 후), `"K"` 2개 SKU만 처리된다
- 빈 문자열 `""`은 처리 대상에서 제외된다

---

### 시나리오 7 — 인증 없이 요청

**Given** JWT 토큰이 없는 요청이 있고  
**When** `POST /api/book/etoile-inven-skus/`에 요청을 전송하면  
**Then** HTTP 401 Unauthorized 응답이 반환된다

---

### 시나리오 8 — 빈 배열 요청

**Given** 인증된 관리자가 있고  
**When** `POST /api/book/etoile-inven-skus/`에 `{"skus": []}`를 전송하면  
**Then** HTTP 400 Bad Request 응답이 반환된다

---

### 시나리오 9 — 트랜잭션 원자성 (DB 오류 시 롤백)

**Given** DB 오류가 발생하는 조건에서  
**When** `POST /api/book/etoile-inven-skus/`에 유효한 요청을 전송하면  
**Then**
- HTTP 500 Internal Server Error 응답이 반환된다
- `Inven` 테이블과 `EtoileBookInven` 테이블 모두 변경 없음 (트랜잭션 롤백)

---

## 엣지 케이스

| 케이스 | 예상 동작 |
|--------|-----------|
| `skus` 필드 자체 누락 | HTTP 400 |
| 모든 SKU가 공백 또는 빈 문자열 | strip 후 유효 SKU 없음 → HTTP 400 |
| 100개 이상 SKU 일괄 처리 | `bulk_create`로 단일 쿼리 처리, 정상 응답 |
| 동일 SKU가 Inven에 있고 `bulk_create` 중 race condition | `ignore_conflicts=True`로 처리, 재조회 후 EtoileBookInven 생성 |

---

## Definition of Done

- [ ] `POST /api/book/etoile-inven-skus/` 엔드포인트 응답 확인
- [ ] 시나리오 1~9 모두 통과
- [ ] `backend/book/tests/test_etoile_inven_add.py` 작성 및 전체 통과
- [ ] 신규 코드 테스트 커버리지 90% 이상
- [ ] `transaction.atomic()` 적용 확인
- [ ] 기존 `InvenSkuBulkAddView`, `FastListingSkuView` 동작 회귀 없음
- [ ] REQ-EIA-001 ~ REQ-EIA-015 전체 구현 확인
