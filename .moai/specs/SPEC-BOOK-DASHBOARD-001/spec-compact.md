# SPEC-BOOK-DASHBOARD-001 Compact Reference

빠른 참조용 압축 문서. 전체 내용은 `spec.md`, `plan.md`, `acceptance.md` 참조.

---

## Requirements (EARS Format)

| ID | Pattern | Requirement |
|----|---------|-------------|
| REQ-BD-001 | Ubiquitous | The system **shall** provide `GET /api/book/dashboard/metrics/` returning all 8 metrics in a single response. |
| REQ-BD-002 | State-Driven | **While** authenticated with valid JWT, the system **shall** allow access to dashboard metrics. |
| REQ-BD-003 | Unwanted | **If** request arrives without valid JWT, **then** the system **shall** respond HTTP 401 and **shall not** return metric data. |
| REQ-BD-004 | Ubiquitous | The system **shall** return `status_counts` as `[{status, label, count}]` for all distinct `Inven.status_of_shopify` values. |
| REQ-BD-005 | Ubiquitous | The system **shall** return `shopify_created_24h` as count of `Shopify_product` with `created_at` within last 24 hours. |
| REQ-BD-006 | Ubiquitous | The system **shall** return `error_total` as count of `Inven` where `status_of_shopify in [31,32,41,42,43,44]`. |
| REQ-BD-007 | Ubiquitous | The system **shall** return `error_rows` as subset of `status_counts` filtered to ERROR_STATUSES. |
| REQ-BD-008 | Ubiquitous | The system **shall** return `waiting_total` as count of `Inven` where `status_of_shopify in [0,1,5,6,14,15,16]`. |
| REQ-BD-009 | Ubiquitous | The system **shall** return `unresolved_note_count` as count of `BookNote` where `note_type='GENERAL'` and `is_resolved=False`. |
| REQ-BD-010 | Ubiquitous | The system **shall** return `sale_zero_count` as count of `Info` where `price_sale=0` and `Inven.status_of_shopify in [80,81,82]`. |
| REQ-BD-011 | Ubiquitous | The system **shall** return `cost_zero_count` as count of `Info` where `price=0 AND kyobo_supply_price=0` and `Inven.status_of_shopify in [80,81,82]`. |
| REQ-BD-012 | Ubiquitous | The system **shall** define `STATUS_LABELS`, `ERROR_STATUSES`, `WAITING_STATUSES` in `backend/book/constants.py`. |
| REQ-BD-013 | Event-Driven | **When** authenticated user loads DashboardPage, frontend **shall** issue a single `GET /api/book/dashboard/metrics/` request and display all metrics. |
| REQ-BD-014 | State-Driven | **While** metrics request is in-flight, the system **shall** display a loading state. |
| REQ-BD-015 | Event-Driven | **When** metrics request fails, the system **shall** display a user-visible error message. |
| REQ-BD-016 | State-Driven | **While** all counts are zero, the system **shall** display `0` values (not null/undefined). |
| REQ-BD-017 | Optional | **Where** `BookNote` lacks `(note_type, is_resolved)` index, the system **shall** log performance warning when query exceeds 500ms. |
| REQ-BD-018 | Ubiquitous | The system **shall** use `JWTAuthentication` + `IsAuthenticated` on `DashboardMetricsView`. |

---

## Acceptance Criteria (Given-When-Then)

### SC-1: 정상 로드
- **Given**: 유효한 JWT 토큰을 가진 인증된 사용자, DB에 데이터 존재
- **When**: `GET /api/book/dashboard/metrics/` 호출
- **Then**: HTTP 200, 8개 필드 모두 포함, 숫자 필드는 모두 integer (not null)

### SC-2: 인증 거부
- **Given**: 유효하지 않거나 없는 JWT 토큰
- **When**: `GET /api/book/dashboard/metrics/` 호출
- **Then**: HTTP 401, 응답 본문에 지표 데이터 없음

### SC-3: 에러 지표 집계
- **Given**: `status_of_shopify=31` 레코드 3개, `status_of_shopify=44` 레코드 2개
- **When**: 인증 후 API 호출
- **Then**: `error_total=5`, `error_rows`에 status 31(count:3)과 44(count:2) 포함

### SC-4: 빈 데이터
- **Given**: 관련 레코드 없음
- **When**: 인증 후 API 호출
- **Then**: HTTP 200, 모든 숫자 필드 `0`, `status_counts`와 `error_rows`는 `[]`

### SC-5: 프론트엔드 로딩 상태
- **Given**: DashboardPage 마운트, API 응답 대기 중
- **When**: `useDashboardMetrics` hook 실행
- **Then**: Skeleton 표시, 단 1회 API 요청 발행

### SC-6: 프론트엔드 에러 상태
- **Given**: API 요청 실패 (네트워크 에러 또는 5xx)
- **When**: hook이 에러 수신
- **Then**: 사용자 가시 에러 메시지 표시, 앱 크래시 없음

---

## Files to Modify

### Backend

| 파일 | 상태 |
|------|------|
| `backend/book/constants.py` | [NEW] |
| `backend/book/serializers.py` | [NEW] |
| `backend/book/views.py` | [NEW] |
| `backend/book/urls.py` | [NEW] |
| `backend/config/urls.py` | [MODIFY] — book.urls include 추가 |

### Frontend

| 파일 | 상태 |
|------|------|
| `frontend/src/types/book.ts` | [NEW] |
| `frontend/src/features/book/hooks/useDashboardMetrics.ts` | [NEW] |
| `frontend/src/pages/DashboardPage.tsx` | [MODIFY] — 플레이스홀더 교체 |
| `frontend/src/pages/DashboardPage.test.tsx` | [MODIFY] — 테스트 업데이트 |

---

## Exclusions (What NOT to Build)

1. Etoile 관련 지표
2. WebSocket 실시간 업데이트 / 폴링
3. 차트 시각화 (Chart.js, Recharts 등)
4. CSV/Excel 내보내기
5. `status_counts` 페이지네이션
6. `BookNote` 인덱스 자동 생성 (별도 마이그레이션 태스크)
7. 역할 기반 지표 필터링
