# SPEC-BOOK-DASHBOARD-001 Acceptance Criteria

---

## Scenario 1: 정상 로드 — 인증된 사용자가 8개 지표를 모두 수신

**Given** 유효한 JWT 액세스 토큰을 가진 인증된 사용자가 있고,
데이터베이스에 다양한 상태의 `Inven`, `Info`, `Shopify_product`, `BookNote` 레코드가 존재할 때

**When** `GET /api/book/dashboard/metrics/` 요청을 `Authorization: Bearer <token>` 헤더와 함께 보내면

**Then**
- HTTP 200 OK 응답이 반환된다
- 응답 JSON은 다음 8개 필드를 모두 포함한다: `status_counts`, `shopify_created_24h`, `error_total`, `error_rows`, `waiting_total`, `unresolved_note_count`, `sale_zero_count`, `cost_zero_count`
- `status_counts`는 `[{"status": <int>, "label": <str>, "count": <int>}]` 형태의 배열이다
- `error_rows`는 `status_counts` 중 `status`가 `[31, 32, 41, 42, 43, 44]`에 속하는 항목만 포함한다
- 모든 숫자 필드는 정수(integer)이며 null이 아니다

---

## Scenario 2: 인증 거부 — 미인증 요청은 401 반환

**Given** JWT 액세스 토큰이 없거나 만료된 요청이 있을 때

**When** `GET /api/book/dashboard/metrics/` 요청을 토큰 없이 또는 `Authorization: Bearer invalid_token` 헤더와 함께 보내면

**Then**
- HTTP 401 Unauthorized 응답이 반환된다
- 응답 본문에 지표 데이터가 포함되지 않는다
- `status_counts`, `error_total` 등 어떤 지표 필드도 노출되지 않는다

---

## Scenario 3: 에러 지표 — 에러 상태 항목 존재 시 집계

**Given** 데이터베이스에 `status_of_shopify = 31`인 `Inven` 레코드 3개, `status_of_shopify = 44`인 레코드 2개가 존재할 때

**When** 인증된 사용자가 `GET /api/book/dashboard/metrics/`를 호출하면

**Then**
- `error_total`은 `5`이다
- `error_rows`는 `status = 31`인 항목(`count: 3`)과 `status = 44`인 항목(`count: 2`)을 포함한다
- `error_rows`에서 status 31의 `label`은 STATUS_LABELS[31]과 일치한다
- `status_counts`에도 동일한 항목이 포함된다 (error_rows는 status_counts의 부분집합)

---

## Scenario 4: 빈 데이터 — 모든 카운트가 0으로 반환

**Given** 데이터베이스가 비어 있거나 모든 관련 조건에 해당하는 레코드가 없을 때

**When** 인증된 사용자가 `GET /api/book/dashboard/metrics/`를 호출하면

**Then**
- HTTP 200 OK 응답이 반환된다
- `shopify_created_24h`는 `0`이다 (null 또는 undefined 아님)
- `error_total`은 `0`이다
- `waiting_total`은 `0`이다
- `unresolved_note_count`는 `0`이다
- `sale_zero_count`는 `0`이다
- `cost_zero_count`는 `0`이다
- `status_counts`는 빈 배열 `[]`이다
- `error_rows`는 빈 배열 `[]`이다

---

## Scenario 5: 프론트엔드 로딩 상태

**Given** 인증된 사용자가 DashboardPage에 접근하고
API 응답이 아직 반환되지 않은 상태일 때

**When** DashboardPage가 마운트되어 `useDashboardMetrics` hook이 실행되면

**Then**
- 페이지에 로딩 인디케이터(Skeleton 또는 동등한 UI)가 표시된다
- 지표 값이 노출되지 않는다 (불완전한 데이터가 렌더링되지 않음)
- 단 하나의 `GET /api/book/dashboard/metrics/` 요청만 발행된다

---

## Scenario 6: 프론트엔드 에러 상태

**Given** 인증된 사용자가 DashboardPage에 접근하고
API 요청이 네트워크 에러 또는 5xx 응답으로 실패할 때

**When** `useDashboardMetrics` hook이 에러를 수신하면

**Then**
- 사용자 가시적인 에러 메시지가 표시된다
- 빈 카드 또는 0 값이 실데이터인 것처럼 표시되지 않는다
- 페이지가 크래시(unhandled error)하지 않는다

---

## Edge Cases

### EC-1: 대용량 데이터 성능

**조건**: `Inven` 테이블에 50,000개 이상의 레코드가 존재
**기대**: API 응답 시간이 1,000ms 미만
**근거**: `status_of_shopify`는 `db_index=True`로 인덱스 보유. 집계 쿼리는 인덱스 스캔으로 처리

### EC-2: 데이터베이스 접근 불가

**조건**: 데이터베이스 연결이 끊어진 상태에서 API 호출
**기대**: HTTP 503 Service Unavailable 응답 (500 Internal Server Error 아님)
**근거**: Django의 데이터베이스 예외를 뷰에서 캐치하여 503으로 변환

### EC-3: `shopify_created_24h` 경계 시간

**조건**: `Shopify_product.created_at`이 정확히 24시간 전인 레코드 존재
**기대**: 경계 레코드는 포함되지 않는다 (`created_at__gt=now - 24h` 사용)
**검증 방법**: 경계값 테스트(datetime mock)로 확인

### EC-4: STATUS_LABELS에 없는 상태 코드

**조건**: 데이터베이스에 STATUS_LABELS에 정의되지 않은 `status_of_shopify` 값 존재
**기대**: `status_counts`에 해당 항목 포함, `label`은 빈 문자열 또는 `"Unknown"`으로 대체 (에러 미발생)
**근거**: `.get(status, "Unknown")` 방어적 조회 사용

### EC-5: `cost_zero_count`와 `sale_zero_count` 중복

**조건**: 동일한 `Info` 레코드가 `price_sale=0`, `price=0`, `kyobo_supply_price=0`을 모두 만족
**기대**: `sale_zero_count`와 `cost_zero_count` 양쪽에 중복 집계됨 (이는 의도된 동작 — 레거시 동일)

---

## Quality Gate Criteria

| 항목 | 기준 |
|------|------|
| Backend 테스트 커버리지 | `book/views.py`, `book/serializers.py` 80% 이상 |
| Frontend 테스트 커버리지 | `DashboardPage.tsx`, `useDashboardMetrics.ts` 80% 이상 |
| API 응답 시간 | 50,000 레코드 기준 1,000ms 미만 |
| 타입 안전성 | TypeScript 컴파일 에러 0개 |
| Linting | ESLint 에러 0개, Python ruff 에러 0개 |
| 인증 검증 | 토큰 없는 요청에 대해 401 반환 확인 |

---

## Definition of Done

- [ ] `GET /api/book/dashboard/metrics/` 엔드포인트가 8개 지표를 모두 반환한다
- [ ] 미인증 요청에 대해 HTTP 401이 반환된다
- [ ] `DashboardPage.tsx`가 로딩/에러/데이터 상태를 모두 처리한다
- [ ] `DashboardPage.test.tsx`가 3가지 상태를 모두 커버한다
- [ ] `backend/book/constants.py`에 레거시 상수가 정확히 이식되어 있다
- [ ] `backend/config/urls.py`에 book URL이 등록되어 있다
- [ ] 모든 Backend 및 Frontend 테스트가 통과한다
- [ ] TypeScript 타입 에러가 없다
- [ ] SPEC-BOOK-DASHBOARD-001 관련 MX 태그(`@MX:ANCHOR`, `@MX:NOTE`)가 적용되어 있다
