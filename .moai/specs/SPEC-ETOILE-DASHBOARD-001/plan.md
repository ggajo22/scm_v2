# Implementation Plan — SPEC-ETOILE-DASHBOARD-001

## M1: 백엔드

### 1-1. constants.py
- `ETOILE_STATUS_LABELS` 딕셔너리 추가

### 1-2. views.py
- `EtoileDashboardView(APIView)` 추가
  - `GET /api/book/etoile/dashboard/`
  - `EtoileBookInven.objects.values("status_of_shopify").annotate(count=Count("id")).order_by(...)`
  - null status 처리: `status_of_shopify__isnull` 별도 처리
  - `total` = 전체 합산

### 1-3. urls.py
- `path("book/etoile/dashboard/", EtoileDashboardView.as_view(), name="book-etoile-dashboard")`

## M2: 프론트엔드

### 2-1. useEtoileDashboard.ts
- `GET /api/book/etoile/dashboard/` TanStack Query hook
- 타입: `EtoileDashboard { status_counts: EtoileStatusCount[], total: number }`

### 2-2. EtoileDashboardPage.tsx
- 전체 건수 요약 카드 (`MetricCard` 패턴)
- 상태별 현황 테이블 (상태값 | 레이블 | 건수)
- 로딩/에러 상태 처리

### 2-3. router/index.tsx
- `path: 'etoile'` lazy route 추가

### 2-4. Sidebar.tsx
- `bookGroup.items`에 `{ label: 'Etoile 현황', href: '/books/etoile' }` 추가

## M3: 테스트

### 백엔드
- `test_etoile_dashboard.py`: 인증, 집계 정확성, 레이블, null 처리, 정렬

### 프론트엔드
- `Sidebar.test.tsx`: Etoile 항목 렌더링 + active state 테스트 추가
