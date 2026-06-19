# 인수 기준 — SPEC-BOOK-SEARCH-001

## 인수 시나리오

### 시나리오 1: ISBN 정확 검색

- **Given**: 인증된 관리자이고, `inven_SKU="978-89-954321-0-5"`인 도서가 DB에 존재한다.
- **When**: `GET /api/book/search/?search=978-89-954321-0-5` 요청을 보낸다.
- **Then**:
  - HTTP 200 OK가 반환된다.
  - `results` 배열에 해당 도서가 포함된다.
  - `results[0].inven_SKU == "978-89-954321-0-5"`이다.
  - 응답에 `count`, `next`, `previous`, `results` 필드가 존재한다.

---

### 시나리오 2: 도서 제목 부분 검색

- **Given**: 인증된 관리자이고, `info.name="파이썬 프로그래밍 입문"`인 도서가 DB에 존재한다.
- **When**: `GET /api/book/search/?search=파이썬` 요청을 보낸다.
- **Then**:
  - HTTP 200 OK가 반환된다.
  - `results` 배열에 해당 도서가 포함된다.
  - `results[0].info.name`에 "파이썬"이 포함된다.

---

### 시나리오 3: OR 조건 복합 검색

- **Given**: 도서 A는 `inven_SKU`에 "123"이 포함되고, 도서 B는 `info.name`에 "123"이 포함된다.
- **When**: `GET /api/book/search/?search=123` 요청을 보낸다.
- **Then**:
  - HTTP 200 OK가 반환된다.
  - 도서 A와 도서 B 모두 `results`에 포함된다.
  - 두 도서가 단일 요청으로 반환된다 (별도 요청 불필요).

---

### 시나리오 4: 미인증 요청 차단

- **Given**: JWT 토큰이 없거나 유효하지 않다.
- **When**: `GET /api/book/search/?search=test` 요청을 보낸다.
- **Then**:
  - HTTP 401 Unauthorized가 반환된다.
  - 응답 바디에 인증 오류 메시지가 포함된다.

---

### 시나리오 5: 검색 결과 없음 처리

- **Given**: 인증된 관리자이고, 검색어에 매칭되는 도서가 DB에 없다.
- **When**: `GET /api/book/search/?search=ZZZNOMATCH99999` 요청을 보낸다.
- **Then**:
  - HTTP 200 OK가 반환된다 (404 아님).
  - `results`는 빈 배열 `[]`이다.
  - `count`는 `0`이다.

---

### 시나리오 6: 페이지네이션 동작 확인

- **Given**: 인증된 관리자이고, DB에 100건 이상의 도서가 존재한다.
- **When**: `GET /api/book/search/` (search 파라미터 없음) 요청을 보낸다.
- **Then**:
  - HTTP 200 OK가 반환된다.
  - `results`는 최대 50건이다.
  - `count`는 전체 도서 수를 반영한다.
  - `next`는 2페이지 URL을 포함한다 (100건 초과 시).
  - `previous`는 `null`이다 (1페이지이므로).

---

### 시나리오 7: 프론트엔드 — 2자 미만 입력 시 API 미호출

- **Given**: 사용자가 `/books/search` 페이지에 있다.
- **When**: 검색 입력란에 1자("파")를 입력한다.
- **Then**:
  - API 호출이 발생하지 않는다.
  - 결과 테이블이 표시되지 않는다 (또는 빈 상태 메시지).
  - 로딩 스피너가 표시되지 않는다.

---

### 시나리오 8: 프론트엔드 — 검색 디바운스 동작

- **Given**: 사용자가 `/books/search` 페이지에 있다.
- **When**: 검색 입력란에 "파이썬"을 300ms 이내에 빠르게 입력한다.
- **Then**:
  - 중간 입력 상태("파", "파이", "파이썬")에 대해 개별 API 호출이 발생하지 않는다.
  - 마지막 입력("파이썬") 이후 300ms가 경과하면 단 1회의 API 호출이 발생한다.

---

### 시나리오 9: 프론트엔드 — 결과 테이블 열 확인

- **Given**: 인증된 관리자이고, 검색 결과가 1건 이상 존재한다.
- **When**: 검색어 2자 이상 입력 후 결과가 표시된다.
- **Then**:
  - 테이블에 "ISBN", "도서 제목", "판매가", "Shopify 상태" 열이 존재한다.
  - 각 행에 `inven_SKU`, `info.name`, `info.price_sale`, `status_of_shopify` 값이 올바르게 표시된다.

---

### 시나리오 10: 프론트엔드 — 에러 상태 처리

- **Given**: 사용자가 `/books/search` 페이지에 있고, 검색어를 입력한다.
- **When**: 백엔드 API가 5xx 오류를 반환한다.
- **Then**:
  - 로딩 스피너가 사라진다.
  - 사용자에게 에러 메시지가 표시된다.
  - 페이지가 500 에러로 크래시되지 않는다.

---

## 엣지 케이스

| 케이스 | 입력 | 기대 결과 |
|--------|------|-----------|
| 빈 search 파라미터 | `?search=` | 전체 목록 반환 (필터 없음) |
| 대소문자 무관 검색 | `?search=python` (제목: "Python 입문") | 대소문자 관계없이 매칭 |
| 특수문자 포함 검색 | `?search=978-89` | 500 오류 없이 정상 처리 |
| 공백 포함 검색 | `?search=파이썬 입문` | 공백 포함 문자열로 icontains 처리 |
| 2페이지 요청 | `?page=2` | 51번째~100번째 항목 반환 |
| 검색 + 페이지 조합 | `?search=파이썬&page=2` | 검색 결과의 2페이지 반환 |
| 매우 긴 검색어 | 200자 이상 입력 | 500 오류 없이 빈 결과 또는 정상 처리 |

---

## Definition of Done (완료 기준)

### 백엔드

- [ ] `Info.name` 인덱스 마이그레이션 작성 및 적용 가능 상태
- [ ] `BookDetailSerializer`가 `inven_SKU`, `info.name`, `info.price_sale`, `status_of_shopify` 필드를 반환
- [ ] `GET /api/book/search/` 엔드포인트가 ISBN 및 제목 OR 검색을 지원
- [ ] 미인증 요청 시 401 반환 확인
- [ ] `select_related('info')` 사용으로 N+1 쿼리 없음 (`assertNumQueries` 확인)
- [ ] 페이지네이션 응답 구조 (`count`, `next`, `previous`, `results`) 올바름
- [ ] 모든 테스트 시나리오 (`test_book_search.py`) 통과
- [ ] 기존 `DashboardMetricsView` 응답 구조 회귀 없음

### 프론트엔드

- [ ] `useBookSearch` 훅이 `enabled: query.length >= 2` 조건 준수
- [ ] 300ms 디바운스 동작 확인 (수동 또는 단위 테스트)
- [ ] 결과 테이블에 4개 열(ISBN, 제목, 판매가, Shopify 상태) 표시
- [ ] 로딩/에러/빈 상태 UI 모두 렌더링 확인
- [ ] 페이지네이션 컨트롤(이전/다음) 동작
- [ ] `/books/search` 라우트 등록 및 접근 가능
- [ ] TypeScript 타입 오류 없음 (`tsc --noEmit` 통과)

### 품질 게이트

- [ ] 백엔드 테스트 커버리지 85% 이상 (신규 코드 기준)
- [ ] ESLint 오류 없음
- [ ] ruff 린트 통과
- [ ] 기존 API 엔드포인트 회귀 없음
