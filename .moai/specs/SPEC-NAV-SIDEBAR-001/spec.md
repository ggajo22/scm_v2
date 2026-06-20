---
id: SPEC-NAV-SIDEBAR-001
version: 1.0.0
status: Completed
created: 2026-06-20
updated: 2026-06-20
author: ggajo
priority: Medium
issue_number: ~
---

# SPEC-NAV-SIDEBAR-001: 사이드바 계층형 네비게이션

## HISTORY

| 버전  | 날짜       | 변경 내용                |
|-------|------------|--------------------------|
| 1.0.0 | 2026-06-20 | 최초 작성                |

---

## 개요

현재 단일 수준의 플랫(flat) 리스트로 구성된 사이드바 네비게이션을 **그룹 헤더 + 하위 항목** 구조의 계층형 네비게이션으로 전환한다.

- "도서 관리" → 그룹 헤더로 변경, 하위에 "대시보드"와 "ISBN 추가" 배치
- "관리자 계정 관리" → 기존 플랫 항목 유지 (super_admin 전용)

### 변경 대상 파일

| 파일 | 변경 유형 |
|------|-----------|
| `frontend/src/components/Sidebar.tsx` | 주요 리팩터 (flat list → grouped nav) |
| `frontend/src/components/Sidebar.test.tsx` | 기존 테스트 업데이트 + 신규 테스트 추가 |

### 백엔드 변경 없음

라우팅 및 API는 변경되지 않는다.

---

## 요구사항 (EARS 형식)

### REQ-001: 그룹 헤더 표시

The **Sidebar** shall render a non-clickable group header labeled "도서관리" with a `BookOpen` icon when the user is authenticated.

> 사이드바는 인증된 사용자에게 `BookOpen` 아이콘이 포함된 클릭 불가능한 "도서관리" 그룹 헤더를 표시해야 한다.

### REQ-002: 대시보드 하위 항목 렌더링

The **Sidebar** shall render a sub-item labeled "대시보드" under the "도서관리" group, linking to `/books`.

> 사이드바는 "도서관리" 그룹 아래 `/books` 경로로 연결되는 "대시보드" 하위 항목을 렌더링해야 한다.

### REQ-003: ISBN 추가 하위 항목 렌더링

The **Sidebar** shall render a sub-item labeled "ISBN 추가" under the "도서관리" group, linking to `/books/add-isbn`.

> 사이드바는 "도서관리" 그룹 아래 `/books/add-isbn` 경로로 연결되는 "ISBN 추가" 하위 항목을 렌더링해야 한다.

### REQ-004: 대시보드 활성 상태

**When** the current route is exactly `/books`, the **Sidebar** shall apply the active visual style to the "대시보드" sub-item only.

> 현재 경로가 정확히 `/books`일 때, 사이드바는 "대시보드" 하위 항목에만 활성 스타일을 적용해야 한다.

### REQ-005: ISBN 추가 활성 상태

**When** the current route is `/books/add-isbn`, the **Sidebar** shall apply the active visual style to the "ISBN 추가" sub-item only.

> 현재 경로가 `/books/add-isbn`일 때, 사이드바는 "ISBN 추가" 하위 항목에만 활성 스타일을 적용해야 한다.

### REQ-006: 기타 도서 관련 경로의 비활성 상태

**When** the current route matches `/books/*` but is neither `/books` nor `/books/add-isbn`, the **Sidebar** shall not apply the active visual style to any sub-item under "도서관리".

> 현재 경로가 `/books/*`에 해당하지만 `/books`도 `/books/add-isbn`도 아닐 때 (예: `/books/:id`), 사이드바는 "도서관리" 그룹의 어떤 하위 항목에도 활성 스타일을 적용하지 않아야 한다.

### REQ-007: 관리자 계정 관리 항목 유지

**Where** the authenticated user has `super_admin` role, the **Sidebar** shall render "관리자 계정 관리" as a top-level flat item linking to `/admin-users`, unchanged from the current behavior.

> 인증된 사용자가 `super_admin` 역할을 가진 경우, 사이드바는 "관리자 계정 관리"를 기존과 동일하게 `/admin-users`로 연결되는 최상위 플랫 항목으로 렌더링해야 한다.

### REQ-008: 관리자 계정 관리 항목 숨김

**When** the authenticated user has `admin` role (not `super_admin`), the **Sidebar** shall not render the "관리자 계정 관리" item.

> 인증된 사용자가 `admin` 역할(super_admin 아님)일 때, 사이드바는 "관리자 계정 관리" 항목을 렌더링하지 않아야 한다.

### REQ-009: 하위 항목 들여쓰기

The **Sidebar** shall visually indent sub-items relative to the "도서관리" group header using consistent padding.

> 사이드바는 하위 항목을 "도서관리" 그룹 헤더보다 일관된 패딩으로 들여쓰기하여 시각적 계층 구조를 표현해야 한다.

### REQ-010: 그룹 헤더 접근성

The **Sidebar** shall mark the "도서관리" group header with `role="group"` and `aria-label="도서관리"` (or equivalent semantic HTML) so that screen readers announce the grouping.

> 사이드바는 "도서관리" 그룹 헤더에 `role="group"` 및 `aria-label="도서관리"` (또는 동등한 시맨틱 HTML)를 적용하여 스크린 리더가 그룹 구조를 인식할 수 있도록 해야 한다.

---

## 제약 사항

- 기존 `NavItem` 인터페이스의 역할(roles) 필터링 로직을 재사용한다.
- React Router의 `useLocation` 또는 동등한 훅을 사용하여 현재 경로를 판별한다.
- 활성 상태 판별은 **완전 일치(exact match)** 를 기준으로 한다 (`/books`와 `/books/search`는 서로 다른 항목).
- Tailwind CSS 유틸리티 클래스를 사용하여 스타일링한다 (기존 패턴 유지).
- 백엔드 API 변경 없음.

---

## Exclusions (What NOT to Build)

- **도서 검색 페이지(`/books/search`) 링크 추가 안 함**: 현재 요청 범위에 포함되지 않음.
- **그룹 접기/펼치기(Accordion) 기능 제외**: 정적 그룹 헤더만 구현. 토글 동작 없음.
- **아이콘 변경 없음**: `BookOpen`, `Users` 등 기존 아이콘 그대로 사용.
- **모바일 반응형 사이드바 재구성 제외**: 레이아웃 반응성 변경 없음.
- **새 라우트(`/books/search` 등) 추가 안 함**: 라우팅 파일 변경 없음.

---

## 구현 노트 (Implementation Notes)

**구현 완료일**: 2026-06-20
**커밋 범위**: `26f725f` → `a475674` (master)

### 계획 대비 변경사항

- **Exclusion 번복 — 토글 기능 추가**: 최초 SPEC에서 "그룹 접기/펼치기 기능 제외"로 명시했으나, 구현 후 사용자 요청으로 토글(접기/펼치기) 기능을 추가함. `useState(true)`로 기본 펼침, `aria-expanded` 속성 포함.
- **추가 파일 변경 — `BookLayout.tsx`**: SPEC 범위 외 파일이지만, topbar의 "ISBN 추가" 버튼이 사이드바 하위 항목과 기능 중복되어 제거함.
- **hover 색상 수정**: Tailwind CSS 변수 기반 클래스(`hover:bg-muted`) 대신 구체적 색상(`hover:bg-gray-100 hover:text-gray-900`) 사용 — 프로젝트 button.tsx 커스터마이징과의 일관성 유지.

### 구현 완료 항목

- REQ-001 ~ REQ-010 전체 구현 완료
- 테스트: 18개 (기존 3개 + 신규 15개) 전체 통과
