---
id: SPEC-ETOILE-DASHBOARD-001
version: 1.0.0
status: Completed
created: 2026-06-20
updated: 2026-06-20
author: ggajo
priority: Medium
issue_number: ~
---

# SPEC-ETOILE-DASHBOARD-001: 에투알 재고 현황 대시보드

## HISTORY

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-06-20 | 1.0.0 | 최초 작성 |

---

## 문제 정의

현재 scm_v2의 대시보드(`/books`)는 `Inven`(북센) 테이블 기준 지표만 표시한다.
에투알 재고(`etoile_book_inven`) 상태를 한눈에 파악할 수 있는 전용 화면이 없어,
운영자가 에투알 Shopify 리스팅 현황을 확인하려면 별도 DB 쿼리가 필요하다.

레거시 시스템의 `etoile_index()` 뷰는 `status_of_shopify` 기준 그룹별 건수를
HTML 페이지로 제공했다. 이 기능을 scm_v2 React SPA로 이식한다.

---

## 솔루션 개요

`/books/etoile` 경로에 에투알 전용 대시보드 페이지를 추가한다.

- **백엔드**: `GET /api/book/etoile/dashboard/` — `EtoileBookInven.status_of_shopify` 기준 상태별 건수 집계
- **프론트엔드**: 상태별 현황 테이블 + 전체 건수 요약 카드
- **사이드바**: "도서관리" 그룹에 "에투알 현황" 항목 추가

---

## 에투알 status_of_shopify 레이블

레거시 `ETOILE_STATUS_LABELS` 기준 (이식):

| 값 | 레이블 |
|----|--------|
| -1 | gimssine 등록 대기 |
| 0 | 리스팅 준비 |
| 12 | 리스팅 제외 - 컨셉 |
| 80 | 리스팅 완료 |
| (정의 외) | 정의되지 않은 상태 |
| null | 상태 없음 |

---

## 요구사항 (EARS 형식)

### 백엔드 API

**REQ-ETD-001** (Ubiquitous)
The system shall expose a `GET /api/book/etoile/dashboard/` endpoint.

**REQ-ETD-002** (Event-Driven)
When a `GET /api/book/etoile/dashboard/` request is received, the system shall require JWT Bearer token authentication via `JWTAuthentication` + `IsAuthenticated`.

**REQ-ETD-003** (Unwanted)
If no valid JWT token is present, then the system shall return HTTP 401 Unauthorized.

**REQ-ETD-004** (Event-Driven)
When the endpoint is called, the system shall aggregate `EtoileBookInven` records by `status_of_shopify`, returning one entry per distinct status value (including `null`) ordered by `status_of_shopify` ascending (nulls last).

**REQ-ETD-005** (Event-Driven)
When building the response, the system shall map each `status_of_shopify` value to a human-readable Korean label using `ETOILE_STATUS_LABELS`; unmapped values shall use `"정의되지 않은 상태"`, and `null` values shall use `"상태 없음"`.

**REQ-ETD-006** (Event-Driven)
When processing completes, the system shall return HTTP 200 with the following structure:
```json
{
  "status_counts": [
    { "status": -1, "label": "gimssine 등록 대기", "count": 5 },
    { "status": 0,  "label": "리스팅 준비",        "count": 120 },
    { "status": null, "label": "상태 없음",         "count": 3 }
  ],
  "total": 128
}
```

**REQ-ETD-007** (Ubiquitous)
The system shall add `ETOILE_STATUS_LABELS` to `backend/book/constants.py`, porting values from the legacy system: `{-1: "gimssine 등록 대기", 0: "리스팅 준비", 12: "리스팅 제외 - 컨셉", 80: "리스팅 완료"}`.

### 프론트엔드 UI

**REQ-ETD-008** (Ubiquitous)
The system shall register a `/books/etoile` route accessible to authenticated users.

**REQ-ETD-009** (Ubiquitous)
The system shall display an "에투알 현황" sub-item in the "도서관리" sidebar group, positioned after "빠른 리스팅".

**REQ-ETD-010** (Ubiquitous)
The system shall render a summary card showing the total `EtoileBookInven` record count on the `/books/etoile` page.

**REQ-ETD-011** (Ubiquitous)
The system shall render a status breakdown table with columns: 상태값 | 레이블 | 건수, sorted by status ascending (null row at the bottom).

**REQ-ETD-012** (State-Driven)
While the API call is in progress, the system shall display a loading skeleton in place of the table.

**REQ-ETD-013** (Unwanted)
If the API call returns an error, the system shall display an error message to the user.

**REQ-ETD-014** (Event-Driven)
When the current route is `/books/etoile`, the system shall apply the active visual style to the "에투알 현황" sidebar sub-item only.

---

## 제약사항

- 기존 `DashboardPage`(`/books`)는 변경하지 않는다.
- `ETOILE_STATUS_LABELS`는 `constants.py`에 추가 (레거시 동일 구조).
- `null` status 레코드가 존재할 경우 테이블 맨 아래에 표시한다.
- 프론트엔드 UI 패턴은 기존 `DashboardPage.tsx`와 동일한 구조를 따른다.
- 에투알 데이터는 읽기 전용 (수정 기능 없음).

---

## 제외 사항 (What NOT to Build)

- **개별 도서 링크 없음**: 상태별 건수 클릭 시 해당 도서 목록으로 이동하는 드릴다운 미포함.
- **실시간 Shopify 연동 없음**: `status_of_shopify`는 내부 상태 필드이며, 실시간 Shopify API 호출 없음.
- **필터/정렬 기능 없음**: 단순 집계 뷰만 제공.
- **에투알 북인포 데이터 없음**: `etoile_book_info` 테이블 데이터는 포함하지 않음.

---

## 변경 파일 목록

| 파일 | 변경 유형 |
|------|-----------|
| `backend/book/constants.py` | `ETOILE_STATUS_LABELS` 추가 |
| `backend/book/views.py` | `EtoileDashboardView` 추가 |
| `backend/book/urls.py` | `GET /api/book/etoile/dashboard/` 등록 |
| `frontend/src/features/book/hooks/useEtoileDashboard.ts` | 신규 생성 |
| `frontend/src/pages/EtoileDashboardPage.tsx` | 신규 생성 |
| `frontend/src/router/index.tsx` | `/books/etoile` 라우트 추가 |
| `frontend/src/components/Sidebar.tsx` | "에투알 현황" sub-item 추가 |
| `frontend/src/components/Sidebar.test.tsx` | 신규 항목 테스트 추가 |
