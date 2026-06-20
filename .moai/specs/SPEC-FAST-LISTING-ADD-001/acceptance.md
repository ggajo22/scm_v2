---
id: SPEC-FAST-LISTING-ADD-001
document: acceptance
version: 1.0.0
---

## 인수 조건 (Acceptance Criteria)

### 시나리오 1: 신규 SKU 일괄 생성

**Given** 인증된 운영자가 Inven 테이블에 존재하지 않는 SKU 목록을 입력하고
**When** `POST /api/book/fast-listing-skus/` 를 `{"skus": ["9791000000001", "9791000000002"]}` 로 호출하면
**Then**
- HTTP 200 응답이 반환된다
- Inven 테이블에 2개의 새 레코드가 생성된다
- 각 레코드는 `status_of_shopify=1`, `vendor="북센"`, `store="책방"`, `is_prepared=0`, `is_use=1` 을 가진다
- 응답 바디: `{"created": ["9791000000001", "9791000000002"], "updated": [], "skipped": [], "created_count": 2, "updated_count": 0, "skipped_count": 0}`

---

### 시나리오 2: 기존 SKU 상태 업데이트 (status NOT IN 80/81/82)

**Given** Inven 테이블에 `status_of_shopify=0` 인 SKU "9791000000003" 이 존재하고
**When** `POST /api/book/fast-listing-skus/` 를 `{"skus": ["9791000000003"]}` 로 호출하면
**Then**
- HTTP 200 응답이 반환된다
- "9791000000003" 레코드의 `status_of_shopify` 가 1로 변경된다
- 응답 바디: `{"created": [], "updated": ["9791000000003"], "skipped": [], "created_count": 0, "updated_count": 1, "skipped_count": 0}`

---

### 시나리오 3: 활성 SKU 건너뜀 (status IN 80/81/82)

**Given** Inven 테이블에 다음 레코드들이 존재한다:
- "9791000000080": `status_of_shopify=80`
- "9791000000081": `status_of_shopify=81`
- "9791000000082": `status_of_shopify=82`

**When** `POST /api/book/fast-listing-skus/` 를 세 SKU 모두 포함하여 호출하면
**Then**
- HTTP 200 응답이 반환된다
- 세 레코드의 `status_of_shopify` 값은 변경되지 않는다
- 응답 바디: `{"created": [], "updated": [], "skipped": ["9791000000080", "9791000000081", "9791000000082"], "created_count": 0, "updated_count": 0, "skipped_count": 3}`

---

### 시나리오 4: 혼합 입력 (신규 + 업데이트 + 건너뜀)

**Given** Inven 테이블에 다음이 존재한다:
- "EXIST_UPDATE": `status_of_shopify=12` (구판절판, 업데이트 대상)
- "EXIST_SKIP": `status_of_shopify=81` (활성, 건너뜀)
- "NEW_SKU": Inven 테이블에 없음 (신규 생성 대상)

**When** `POST /api/book/fast-listing-skus/` 를 세 SKU로 호출하면
**Then**
- HTTP 200 응답이 반환된다
- "NEW_SKU" 는 `created` 목록에 포함되고 Inven 레코드가 생성된다
- "EXIST_UPDATE" 는 `updated` 목록에 포함되고 `status_of_shopify=1` 로 변경된다
- "EXIST_SKIP" 는 `skipped` 목록에 포함되고 상태가 변경되지 않는다
- 응답: `{"created": ["NEW_SKU"], "updated": ["EXIST_UPDATE"], "skipped": ["EXIST_SKIP"], "created_count": 1, "updated_count": 1, "skipped_count": 1}`

---

### 시나리오 5: 입력 정규화 (공백 제거 및 중복 제거)

**Given** 운영자가 공백이 포함된 중복 SKU를 입력하고
**When** `{"skus": ["  9791000000001  ", "9791000000001", "", "  "]}` 로 호출하면
**Then**
- 공백이 제거된 단일 SKU "9791000000001" 만 처리된다
- 빈 문자열과 공백 전용 항목은 무시된다
- 중복은 하나만 처리된다

---

### 시나리오 6: 인증 실패

**Given** JWT 토큰 없이 요청을 보낼 때
**When** `POST /api/book/fast-listing-skus/` 를 Authorization 헤더 없이 호출하면
**Then**
- HTTP 401 Unauthorized 응답이 반환된다
- Inven 테이블에 변경이 없다

---

### 시나리오 7: 빈 SKU 목록 요청

**Given** 인증된 운영자가
**When** `{"skus": []}` 로 호출하면
**Then**
- HTTP 400 Bad Request 응답이 반환된다

---

### 시나리오 8: skus 필드 누락

**Given** 인증된 운영자가
**When** `{}` (skus 필드 없음) 로 호출하면
**Then**
- HTTP 400 Bad Request 응답이 반환된다

---

### 시나리오 9: 프론트엔드 - 사이드바 항목

**Given** 로그인된 사용자가 앱을 열면
**When** 사이드바의 "도서관리" 그룹을 확인하면
**Then**
- "대시보드", "ISBN 추가", "빠른 리스팅" 세 가지 서브 항목이 표시된다
- "빠른 리스팅" 클릭 시 `/books/fast-listing` 경로로 이동한다

---

### 시나리오 10: 프론트엔드 - 결과 표시

**Given** 운영자가 `/books/fast-listing` 페이지에서 SKU를 제출하고
**When** API 응답으로 `{"created": ["A"], "updated": ["B"], "skipped": ["C"], ...}` 를 받으면
**Then**
- "생성됨" 섹션(녹색)에 "A" 가 표시된다
- "업데이트됨" 섹션(파란색)에 "B" 가 표시된다
- "건너뜀" 섹션(회색/음소거)에 "C" 가 표시된다
- 제출 버튼이 다시 활성화된다

---

### 시나리오 11: 프론트엔드 - API 호출 중 버튼 비활성화

**Given** 운영자가 SKU를 입력하고 제출 버튼을 클릭했을 때
**When** API 응답이 아직 오지 않은 상태(pending)이면
**Then**
- 제출 버튼이 비활성화(disabled) 상태이다
- 중복 제출이 방지된다

---

### 시나리오 12: 프론트엔드 - API 오류 표시

**Given** 운영자가 SKU를 제출했을 때
**When** API가 오류 응답(4xx/5xx)을 반환하면
**Then**
- 오류 메시지가 사용자에게 표시된다
- 결과 섹션(생성됨/업데이트됨/건너뜀)은 표시되지 않는다

---

## Definition of Done

- [ ] `POST /api/book/fast-listing-skus/` 엔드포인트 구현 완료
- [ ] JWT 인증 동작 확인 (401 케이스 포함)
- [ ] 400 Bad Request: skus 누락/빈 배열 케이스 동작 확인
- [ ] 신규/업데이트/건너뜀 3-범주 분류 로직 동작 확인
- [ ] status 80/81/82 레코드 보호 로직 확인
- [ ] 공백 제거 및 중복 제거 로직 확인
- [ ] DB 오류 시 트랜잭션 롤백 확인
- [ ] `/books/fast-listing` 라우트 등록 확인
- [ ] 사이드바 "빠른 리스팅" 항목 추가 확인
- [ ] 결과 3-섹션 UI (녹색/파란색/회색) 렌더링 확인
- [ ] 제출 중 버튼 비활성화 확인
- [ ] 오류 메시지 표시 확인
- [ ] `/books` 돌아가기 링크 확인

## 품질 게이트

- Django REST framework `APITestCase` 를 사용한 백엔드 단위/통합 테스트 작성
- 위 인수 시나리오 1~8 모두 자동화 테스트로 커버
- 프론트엔드: TanStack Query `useMutation` 훅 단위 테스트
- LSP 오류 0건, 타입 오류 0건
