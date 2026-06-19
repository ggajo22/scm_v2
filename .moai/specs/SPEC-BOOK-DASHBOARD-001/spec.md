---
id: SPEC-BOOK-DASHBOARD-001
version: 1.0.0
status: completed
created: 2026-06-19
updated: 2026-06-19
author: ggajo
priority: high
issue_number: 0
---

## HISTORY

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0.0 | 2026-06-19 | ggajo | 최초 작성 — 레거시 index() 함수 기반 대시보드 API 및 프론트엔드 구현 |

---

## Overview

레거시 SCM 시스템(book/views.py의 `index()` 함수)에서 제공하던 8개 지표를 신규 SCM v2 REST API로 이식하고, 현재 플레이스홀더 상태인 DashboardPage.tsx를 실제 동작하는 대시보드 UI로 교체한다.

---

## Requirements

### REQ-BD-001 (Ubiquitous)

The system **shall** provide a single REST API endpoint `GET /api/book/dashboard/metrics/` that returns all 8 dashboard metrics in a single response.

### REQ-BD-002 (State-Driven)

**While** a user is authenticated with a valid JWT access token, the system **shall** allow access to the dashboard metrics endpoint.

### REQ-BD-003 (Unwanted)

**If** a request to `GET /api/book/dashboard/metrics/` arrives without a valid JWT access token, **then** the system **shall** respond with HTTP 401 Unauthorized and **shall not** return any metric data.

### REQ-BD-004 (Ubiquitous)

The system **shall** return `status_counts` as a list of objects, each containing `status` (integer), `label` (string from STATUS_LABELS), and `count` (integer), covering all distinct `Inven.status_of_shopify` values present in the database.

### REQ-BD-005 (Ubiquitous)

The system **shall** return `shopify_created_24h` as an integer count of `Shopify_product` records whose `created_at` is within the last 24 hours.

### REQ-BD-006 (Ubiquitous)

The system **shall** return `error_total` as an integer count of `Inven` records whose `status_of_shopify` is in ERROR_STATUSES `[31, 32, 41, 42, 43, 44]`.

### REQ-BD-007 (Ubiquitous)

The system **shall** return `error_rows` as a filtered subset of `status_counts` containing only entries whose `status` is in ERROR_STATUSES.

### REQ-BD-008 (Ubiquitous)

The system **shall** return `waiting_total` as an integer count of `Inven` records whose `status_of_shopify` is in WAITING_STATUSES `[0, 1, 5, 6, 14, 15, 16]`.

### REQ-BD-009 (Ubiquitous)

The system **shall** return `unresolved_note_count` as an integer count of `BookNote` records where `note_type = 'GENERAL'` and `is_resolved = False`.

### REQ-BD-010 (Ubiquitous)

The system **shall** return `sale_zero_count` as an integer count of `Info` records where `price_sale = 0` and the associated `Inven.status_of_shopify` is in `[80, 81, 82]`.

### REQ-BD-011 (Ubiquitous)

The system **shall** return `cost_zero_count` as an integer count of `Info` records where `price = 0` AND `kyobo_supply_price = 0` and the associated `Inven.status_of_shopify` is in `[80, 81, 82]`.

### REQ-BD-012 (Ubiquitous)

The system **shall** define constants `STATUS_LABELS` (dict), `ERROR_STATUSES` (list), and `WAITING_STATUSES` (list) in `backend/book/constants.py`, replicating the values from the legacy `book/views.py`.

### REQ-BD-013 (Event-Driven)

**When** an authenticated user loads the DashboardPage, the frontend **shall** issue a single `GET /api/book/dashboard/metrics/` request using the React Query hook and display all returned metrics without requiring a page reload.

### REQ-BD-014 (State-Driven)

**While** the dashboard metrics request is in-flight, the system **shall** display a loading state to the user.

### REQ-BD-015 (Event-Driven)

**When** the dashboard metrics request fails, the system **shall** display a user-visible error message and **shall not** render stale or empty metric values silently.

### REQ-BD-016 (State-Driven)

**While** all metric counts are zero (empty database), the system **shall** display `0` values rather than null, undefined, or blank fields.

### REQ-BD-017 (Optional — Performance)

**Where** the `BookNote` table does not have a composite index on `(note_type, is_resolved)`, the system **shall** log a query performance warning to the application log when the query execution time exceeds 500ms.

### REQ-BD-018 (Ubiquitous)

The system **shall** use `JWTAuthentication` and `IsAuthenticated` permission class on `DashboardMetricsView`, consistent with the existing `accounts` app pattern.

---

## Constraints

- **데이터베이스**: 모든 쿼리는 인덱스된 필드만 사용해야 한다 (`Inven.status_of_shopify`는 `db_index=True` 확인).
- **단일 API 호출**: 프론트엔드는 대시보드 로딩 시 단 하나의 HTTP 요청만 발행해야 한다.
- **인증 패턴**: `accounts` 앱의 `APIView` 패턴을 그대로 따른다 (JWTAuthentication + IsAuthenticated).
- **마이그레이션 없음**: 새로운 모델을 생성하지 않으므로 DB 마이그레이션은 불필요하다.
- **React Query 5**: TanStack React Query 5 API를 사용해야 한다 (v4 API 금지).
- **shadcn/ui**: UI 컴포넌트는 shadcn/ui를 우선 사용하며 Tailwind 4와 함께 스타일링한다.
- **ProtectedRoute**: DashboardPage는 인증된 사용자만 접근 가능한 ProtectedRoute 하위에 위치한다.

---

## Exclusions (What NOT to Build)

1. **Etoile 지표 미포함**: Etoile 모델 관련 지표는 본 SPEC의 범위 밖이다.
2. **WebSocket 실시간 업데이트 없음**: 대시보드 지표는 온-디맨드 로딩으로 충분하며, 폴링 또는 WebSocket 구현은 본 SPEC에 포함하지 않는다.
3. **차트 시각화 없음**: MVP 단계에서는 카드/테이블 표시로 충분하다. 차트(Chart.js, Recharts 등) 구현은 별도 SPEC으로 분리한다.
4. **내보내기 기능 없음**: CSV/Excel 내보내기는 본 SPEC의 범위 밖이다.
5. **페이지네이션 없음**: `status_counts` 목록은 상태 코드 수가 제한적(28개)이므로 페이지네이션이 필요 없다.
6. **BookNote 인덱스 자동 생성 없음**: 인덱스 추가는 별도 마이그레이션 태스크로 분리한다. 본 SPEC은 성능 경고 로깅(REQ-BD-017)만 포함한다.
7. **사용자별 필터링 없음**: 모든 인증된 사용자는 동일한 전체 지표를 조회한다 (역할 기반 데이터 필터링 없음).
