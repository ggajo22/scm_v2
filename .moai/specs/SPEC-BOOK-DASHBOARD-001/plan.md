# SPEC-BOOK-DASHBOARD-001 Implementation Plan

## Overview

레거시 `index()` 함수의 8개 지표를 신규 REST API로 이식하고 프론트엔드 대시보드를 구현하는 브라운필드 작업이다. 총 9개 파일(4개 신규 생성, 5개 수정)을 대상으로 한다.

---

## File Delta (Brownfield Markers)

### Backend (5 files)

| 파일 | 상태 | 설명 |
|------|------|------|
| `backend/book/constants.py` | [NEW] | STATUS_LABELS, ERROR_STATUSES, WAITING_STATUSES 상수 정의 |
| `backend/book/serializers.py` | [NEW] | StatusCountSerializer, DashboardMetricsSerializer |
| `backend/book/views.py` | [NEW] | DashboardMetricsView (APIView) |
| `backend/book/urls.py` | [NEW] | book 앱 URL 라우팅 |
| `backend/config/urls.py` | [MODIFY] | book.urls include 추가 |

### Frontend (4 files)

| 파일 | 상태 | 설명 |
|------|------|------|
| `frontend/src/types/book.ts` | [NEW] | TypeScript 인터페이스 (StatusCount, DashboardMetrics) |
| `frontend/src/features/book/hooks/useDashboardMetrics.ts` | [NEW] | React Query hook |
| `frontend/src/pages/DashboardPage.tsx` | [MODIFY] | 플레이스홀더 → 실제 대시보드 UI |
| `frontend/src/pages/DashboardPage.test.tsx` | [MODIFY] | 테스트 업데이트 (loading/error/data 상태 커버) |

---

## Implementation Phases

### Phase 1 — Backend Constants (Priority: High)

**파일**: `backend/book/constants.py` [NEW]

**구현 내용**:
- `STATUS_LABELS`: 28개 상태 코드 → 한글 레이블 매핑 딕셔너리 (레거시 `book/views.py`에서 정확히 복사)
- `ERROR_STATUSES`: `[31, 32, 41, 42, 43, 44]`
- `WAITING_STATUSES`: `[0, 1, 5, 6, 14, 15, 16]`

**MX Tag**: `STATUS_LABELS` 딕셔너리에 `@MX:NOTE` — 비즈니스 컨텍스트(레거시 이식, 값 변경 시 레거시 확인 필요) 명시

**레퍼런스**: `backend/main/book/views.py` (레거시 시스템) 참조

---

### Phase 2 — Backend Serializer (Priority: High)

**파일**: `backend/book/serializers.py` [NEW]

**구현 내용**:
- `StatusCountSerializer`: `status` (int), `label` (str), `count` (int) 필드
- `DashboardMetricsSerializer`: 8개 필드를 직렬화하는 평탄형(flat) Serializer

**레퍼런스**: `backend/accounts/serializers.py` 패턴 참조

---

### Phase 3 — Backend View (Priority: High)

**파일**: `backend/book/views.py` [NEW]

**구현 내용**:
- `DashboardMetricsView(APIView)` — `GET` 메서드만 구현
- `authentication_classes = [JWTAuthentication]`
- `permission_classes = [IsAuthenticated]`
- 8개 지표를 각각 쿼리하여 단일 JSON 응답으로 반환

**쿼리 구현 전략**:
1. `status_counts`: `Inven.objects.values('status_of_shopify').annotate(count=Count('id'))` → STATUS_LABELS 매핑
2. `shopify_created_24h`: `Shopify_product.objects.filter(created_at__gte=now - 24h).count()`
3. `error_total`: `Inven.objects.filter(status_of_shopify__in=ERROR_STATUSES).count()`
4. `error_rows`: `status_counts`에서 ERROR_STATUSES 해당 항목 필터링 (추가 쿼리 없음)
5. `waiting_total`: `Inven.objects.filter(status_of_shopify__in=WAITING_STATUSES).count()`
6. `unresolved_note_count`: `BookNote.objects.filter(note_type='GENERAL', is_resolved=False).count()`
7. `sale_zero_count`: `Info.objects.filter(price_sale=0, inven__status_of_shopify__in=[80,81,82]).count()`
8. `cost_zero_count`: `Info.objects.filter(price=0, kyobo_supply_price=0, inven__status_of_shopify__in=[80,81,82]).count()`

**MX Tag**: `DashboardMetricsView.get()` 메서드에 `@MX:ANCHOR` — 모든 대시보드 지표의 단일 진입점(high fan_in)

**레퍼런스**: `backend/accounts/views.py` APIView 패턴 참조

---

### Phase 4 — Backend URL Registration (Priority: High)

**파일**: `backend/book/urls.py` [NEW]

**구현 내용**:
```python
path("book/dashboard/metrics/", DashboardMetricsView.as_view(), name="book-dashboard-metrics")
```

**파일**: `backend/config/urls.py` [MODIFY]

**변경 내용**: 기존 `path("api/", include("accounts.urls"))` 패턴에 book URL 추가
```python
path("api/", include("book.urls"))
```

**레퍼런스**: `backend/config/urls.py` 현재 패턴 참조

---

### Phase 5 — Frontend Types (Priority: High)

**파일**: `frontend/src/types/book.ts` [NEW]

**구현 내용**:
- `StatusCount` interface: `{ status: number; label: string; count: number }`
- `DashboardMetrics` interface: 8개 필드 (API 응답 스키마와 1:1 대응)

---

### Phase 6 — Frontend React Query Hook (Priority: High)

**파일**: `frontend/src/features/book/hooks/useDashboardMetrics.ts` [NEW]

**구현 내용**:
- `DASHBOARD_METRICS_QUERY_KEY`: `['dashboard', 'metrics']`
- `useDashboardMetrics()` hook: `useQuery`로 `GET /api/book/dashboard/metrics/` 호출
- `staleTime`, `retry` 옵션은 `useAdminUsers` 패턴과 동일하게 설정

**레퍼런스**: `frontend/src/features/admin-users/hooks/useAdminUsers.ts` 패턴 참조

---

### Phase 7 — Frontend DashboardPage Implementation (Priority: High)

**파일**: `frontend/src/pages/DashboardPage.tsx` [MODIFY]

**변경 내용**: 플레이스홀더(8 LOC) → 실제 대시보드 UI

**구현 내용**:
- `useDashboardMetrics()` hook 호출
- Loading 상태: shadcn/ui Skeleton 컴포넌트
- Error 상태: 사용자 가시 에러 메시지 (shadcn/ui Alert)
- Data 상태: 지표 카드 및 status_counts 테이블
  - 상단 요약 카드: `error_total`, `waiting_total`, `shopify_created_24h`, `unresolved_note_count`, `sale_zero_count`, `cost_zero_count`
  - 하단 테이블: `status_counts` 전체 목록
  - 에러 상세: `error_rows` (에러 상태 breakdown)

**레퍼런스**: `frontend/src/pages/AdminUsersPage.tsx` 컴포넌트 구조 참조

---

### Phase 8 — Frontend Tests Update (Priority: High)

**파일**: `frontend/src/pages/DashboardPage.test.tsx` [MODIFY]

**변경 내용**: 현재 플레이스홀더 테스트 → 실제 대시보드 테스트

**테스트 케이스**:
1. `useDashboardMetrics` mock 설정
2. loading 상태: Skeleton 렌더링 확인
3. error 상태: 에러 메시지 렌더링 확인
4. data 상태: 각 지표 값이 DOM에 렌더링되는지 확인
5. 빈 데이터(all zeros): 0 값이 null/undefined 없이 표시되는지 확인

---

## Reference Implementations

| 목적 | 파일 |
|------|------|
| Backend APIView 패턴 | `backend/accounts/views.py` |
| Backend Serializer 패턴 | `backend/accounts/serializers.py` |
| Backend URL 패턴 | `backend/accounts/urls.py`, `backend/config/urls.py` |
| Frontend hook 패턴 | `frontend/src/features/admin-users/hooks/useAdminUsers.ts` |
| Frontend 페이지 컴포넌트 패턴 | `frontend/src/pages/AdminUsersPage.tsx` |
| Frontend 타입 패턴 | `frontend/src/types/` 기존 파일 참조 |

---

## MX Tag Targets

| 대상 | Tag 종류 | 이유 |
|------|---------|------|
| `DashboardMetricsView.get()` | `@MX:ANCHOR` | 모든 대시보드 지표의 단일 진입점. 이 메서드가 변경되면 8개 지표 전체에 영향 (high fan_in) |
| `STATUS_LABELS` dict | `@MX:NOTE` | 레거시 이식 값. 레거시 `book/views.py`와 동기화 필요. 임의 변경 금지 |

---

## Risks

| 위험 | 심각도 | 완화 방안 |
|------|--------|----------|
| `BookNote` 테이블에 `(note_type, is_resolved)` 복합 인덱스 없음 | Medium | REQ-BD-017에 따라 500ms 초과 시 경고 로그 출력. 인덱스 추가는 별도 마이그레이션 태스크 |
| 레거시 `STATUS_LABELS` 값 불일치 | Low | 구현 시 레거시 파일을 직접 참조하여 정확히 복사 |
| Vite 개발 서버 프록시 설정 의존 | Low | `frontend/vite.config.ts`에 이미 `/api` → `localhost:8000` 프록시 설정 확인됨 |
| `config/urls.py` 수정 시 기존 URL 충돌 | Low | `book.urls` prefix를 `api/`로 설정하여 accounts URL과 분리 |

---

## Implementation Order

```
Phase 1 → Phase 2 → Phase 3 → Phase 4  (Backend, 순차)
                                    ↓
Phase 5 → Phase 6 → Phase 7 → Phase 8  (Frontend, 순차)
```

Backend Phase 1-4 완료 후 Frontend Phase 5-8을 진행한다. Backend API 없이도 Frontend mock을 작성할 수 있으나, 실제 API 응답 스키마 확정 후 타입을 정의하는 것이 안전하다.
