---
id: SPEC-FE-AUTH-001
version: "1.0.1"
status: draft
created: "2026-06-18"
updated: "2026-06-18"
author: ggajo
priority: high
depends_on: SPEC-AUTH-001
issue_number: 0
---

## HISTORY

| 버전  | 날짜       | 작성자 | 변경 내용                              |
|-------|------------|--------|----------------------------------------|
| 1.0.0 | 2026-06-18 | ggajo  | 최초 작성 — 인터뷰 기반 요구사항 도출 (SPEC-AUTH-001 백엔드 완료 기준) |
| 1.0.1 | 2026-06-18 | ggajo  | plan-auditor D2 결함 수정: race condition(REQ-029), 세션 복원 로딩(REQ-030), 세션 만료 알림 명확화, 대시보드 리다이렉트 명확화, 자기 계정 비활성화 서버 오류 처리, 라우트/모달 불일치 해소 |

---

## 개요

### 목적

SCM v2 관리자 웹 애플리케이션의 프론트엔드 인증 UI를 정의한다. 이 SPEC은 SPEC-AUTH-001에서 구현된 Django 백엔드 인증 API를 소비하는 React 기반 UI 계층을 다루며, 로그인 화면부터 역할 기반 네비게이션, SuperAdmin 전용 관리자 계정 관리 UI까지 포함한다.

### 범위

- **로그인/로그아웃**: username + password 기반 로그인 폼, 로그아웃 플로우
- **토큰 관리**: Access Token 메모리 저장 + Refresh Token localStorage 저장, 자동 갱신
- **보호된 라우트**: 미인증 접근 시 로그인 페이지로 리다이렉트
- **역할 기반 UI**: Admin 역할은 관리자 계정 관리 메뉴 숨김 + URL 직접 접근 차단
- **관리자 계정 관리 UI**: SuperAdmin 전용 — 목록 조회, 생성, 수정, 비활성화, 비밀번호 초기화

### 비목표 (Non-goals)

- 도서 리스팅 관리 UI (별도 SPEC)
- 주문 목록 조회 및 관리 UI (별도 SPEC)
- 대시보드 화면 (별도 SPEC)
- 소셜 로그인 연동 UI
- 다중 인증(MFA) UI
- 이메일 기반 비밀번호 재설정 플로우

---

## 요구사항

### 모듈 1: 인증 (Authentication)

#### REQ-FE-AUTH-001 [NEW]
The 시스템 **shall** username 입력 필드, password 입력 필드, 로그인 버튼으로 구성된 로그인 폼을 제공한다.

#### REQ-FE-AUTH-002 [NEW]
**When** 사용자가 로그인 폼을 제출하면, the 시스템 **shall** 두 필드가 모두 입력되었는지 클라이언트 측에서 즉시 검증하고, 빈 필드가 있으면 인라인 에러 메시지를 표시한다.

#### REQ-FE-AUTH-003 [NEW]
**While** 로그인 API 요청이 진행 중인 동안, the 시스템 **shall** 로그인 버튼을 비활성화하고 로딩 인디케이터를 표시한다.

#### REQ-FE-AUTH-004 [NEW]
**When** 로그인 API가 성공 응답을 반환하면, the 시스템 **shall** Access Token을 Zustand 스토어 메모리에 저장하고, Refresh Token을 `localStorage`에 저장한 후, `/` 경로로 리다이렉트한다. (대시보드 컴포넌트 내용은 별도 SPEC이나, ProtectedRoute로서의 `/` 라우트 등록은 이 SPEC 범위에 포함된다.)

#### REQ-FE-AUTH-005 [NEW]
**When** 로그인 API가 실패 응답(401, 400 등)을 반환하면, the 시스템 **shall** "아이디 또는 비밀번호가 올바르지 않습니다." 라는 단일 에러 메시지를 표시한다. (username 또는 password 중 어느 것이 잘못되었는지 구분하지 않는다.)

#### REQ-FE-AUTH-006 [NEW]
**When** 관리자가 로그아웃 버튼을 클릭하면, the 시스템 **shall** `POST /api/auth/logout/` API를 호출하여 Refresh Token을 서버 측에서 무효화하고, Zustand 스토어의 Access Token과 사용자 정보를 초기화하고, `localStorage`의 Refresh Token을 삭제한 후, 로그인 페이지로 리다이렉트한다.

#### REQ-FE-AUTH-007 [NEW]
**If** 로그아웃 API 호출이 실패하더라도, **then** the 시스템 **shall** 클라이언트 측 토큰 및 상태를 초기화하고 로그인 페이지로 리다이렉트한다. (서버 API 실패가 클라이언트 로그아웃을 막지 않는다.)

---

### 모듈 2: 토큰 자동 갱신 및 세션 지속성

#### REQ-FE-AUTH-008 [NEW]
**When** 페이지가 새로고침(리로드)되면, the 시스템 **shall** `localStorage`에 Refresh Token이 존재하는 경우 `POST /api/auth/token/refresh/`를 자동 호출하여 새 Access Token을 발급받고 Zustand 스토어를 복원한다. (자동 재로그인)

#### REQ-FE-AUTH-009 [NEW]
**If** 페이지 새로고침 시 `localStorage`에 Refresh Token이 없거나, 토큰 갱신 API가 401을 반환하면, **then** the 시스템 **shall** 로그인 페이지로 리다이렉트한다.

#### REQ-FE-AUTH-010 [NEW]
**While** 인증된 세션이 활성 상태인 동안, the 시스템 **shall** API 요청 시 Access Token이 만료된 경우 axios 인터셉터를 통해 자동으로 `POST /api/auth/token/refresh/`를 호출하여 토큰을 갱신한 후 원래 요청을 재시도한다.

#### REQ-FE-AUTH-011 [NEW]
**If** 토큰 자동 갱신이 실패하면(Refresh Token 만료 또는 서버 오류), **then** the 시스템 **shall** "세션이 만료되었습니다. 다시 로그인해 주세요." 토스트 메시지를 3초간 표시하고, 클라이언트 인증 상태를 초기화한 후 로그인 페이지로 리다이렉트한다.

---

### 모듈 3: 보호된 라우트 및 역할 기반 접근 제어

#### REQ-FE-AUTH-012 [NEW]
**If** 인증되지 않은 사용자가 로그인 페이지(`/login`) 외의 모든 라우트에 접근을 시도하면, **then** the 시스템 **shall** 로그인 페이지로 리다이렉트한다.

#### REQ-FE-AUTH-013 [NEW]
**If** 인증된 사용자가 로그인 페이지(`/login`)에 접근을 시도하면, **then** the 시스템 **shall** 대시보드 페이지로 리다이렉트한다.

#### REQ-FE-AUTH-014 [NEW]
**While** `admin` 역할의 사용자가 로그인된 동안, the 시스템 **shall** 사이드바 또는 내비게이션 메뉴에서 관리자 계정 관리 항목을 숨긴다.

#### REQ-FE-AUTH-015 [NEW]
**If** `admin` 역할의 사용자가 관리자 계정 관리 라우트(`/admin-users`)에 URL을 직접 입력하여 접근을 시도하면, **then** the 시스템 **shall** 403 Forbidden 페이지로 리다이렉트한다. (관리자 생성/수정/비밀번호 초기화는 `/admin-users` 내 모달로 처리되므로 별도 URL 경로 없이 SuperAdminRoute 단일 가드로 보호된다.)

#### REQ-FE-AUTH-016 [NEW]
**Where** 403 Forbidden 페이지가 표시되는 경우, the 시스템 **shall** "접근 권한이 없습니다." 메시지와 함께 이전 페이지로 돌아가거나 대시보드로 이동할 수 있는 링크를 제공한다.

---

### 모듈 4: 관리자 계정 관리 UI (SuperAdmin 전용)

#### REQ-FE-AUTH-017 [NEW]
**Where** `super_admin` 역할의 사용자가 관리자 계정 관리 기능을 사용하는 경우, the 시스템 **shall** 관리자 목록을 username, 역할, 활성화 상태, 액션 버튼 컬럼이 포함된 테이블로 표시한다.

#### REQ-FE-AUTH-018 [NEW]
**When** 관리자 목록 API(`GET /api/admin/users/`)가 응답을 반환하면, the 시스템 **shall** TanStack Query를 통해 서버 상태를 캐싱하고 테이블에 렌더링한다.

#### REQ-FE-AUTH-019 [NEW]
**Where** `super_admin` 역할의 사용자가 관리자 생성 기능을 사용하는 경우, the 시스템 **shall** username, 비밀번호, 역할 선택(`super_admin` / `admin`) 필드를 가진 생성 폼을 제공한다.

#### REQ-FE-AUTH-020 [NEW]
**When** 관리자 생성 폼을 제출하면, the 시스템 **shall** 클라이언트 측에서 username(필수, 최소 1자), 비밀번호(필수, 최소 8자), 역할(필수) 유효성을 검사한 후 `POST /api/admin/users/` API를 호출한다.

#### REQ-FE-AUTH-021 [NEW]
**When** 관리자 생성 API가 성공 응답을 반환하면, the 시스템 **shall** 성공 토스트 메시지를 표시하고, 관리자 목록 쿼리를 무효화하여 목록을 갱신한다.

#### REQ-FE-AUTH-022 [NEW]
**If** 관리자 생성 API가 400(중복 username 등) 오류를 반환하면, **then** the 시스템 **shall** 해당 에러 메시지를 폼 내 인라인으로 표시한다.

#### REQ-FE-AUTH-023 [NEW]
**Where** `super_admin` 역할의 사용자가 관리자 수정 기능을 사용하는 경우, the 시스템 **shall** username, 역할 선택, is_active 토글 필드를 가진 수정 폼을 제공한다.

#### REQ-FE-AUTH-024 [NEW]
**When** 관리자 수정 폼을 제출하면, the 시스템 **shall** 변경된 필드만 포함하여 `PATCH /api/admin/users/{id}/` API를 호출한다.

#### REQ-FE-AUTH-025 [NEW]
**If** `super_admin` 역할의 사용자가 자기 자신의 계정을 비활성화(`is_active=false`)하려고 시도하면, **then** the 시스템 **shall** "자신의 계정은 비활성화할 수 없습니다." 라는 에러 메시지를 표시하고 API 호출을 차단한다. 만약 클라이언트 차단이 우회되어 서버에서 오류 응답(403 또는 400)이 반환된 경우에도 동일한 에러 메시지를 인라인으로 표시한다.

#### REQ-FE-AUTH-026 [NEW]
**Where** `super_admin` 역할의 사용자가 비밀번호 초기화 기능을 사용하는 경우, the 시스템 **shall** 새 비밀번호 입력 필드와 비밀번호 확인 입력 필드를 가진 다이얼로그(모달)를 제공한다.

#### REQ-FE-AUTH-027 [NEW]
**When** 비밀번호 초기화 다이얼로그를 제출하면, the 시스템 **shall** 클라이언트 측에서 두 필드의 일치 여부와 최소 8자 조건을 검사한 후 `POST /api/admin/users/{id}/reset-password/` API를 호출한다.

#### REQ-FE-AUTH-028 [NEW]
**When** 비밀번호 초기화 API가 성공 응답을 반환하면, the 시스템 **shall** 다이얼로그를 닫고 성공 토스트 메시지를 표시한다.

---

### 모듈 5: 토큰 관리 고급 패턴

#### REQ-FE-AUTH-029 [NEW]
**If** 다수의 API 요청이 동시에 401 Unauthorized 응답을 받으면, **then** the 시스템 **shall** Refresh Token 갱신 요청을 정확히 1회만 실행하고, 갱신이 완료될 때까지 대기 중인 모든 요청을 큐에 보류한 후, 새 Access Token으로 일괄 재시도한다.

#### REQ-FE-AUTH-030 [NEW]
**While** 페이지 새로고침 후 세션 복원(`restoreSession()`)이 진행 중인 동안(`isLoading: true`), the 시스템 **shall** 전체 화면 로딩 스피너를 표시하고 ProtectedRoute의 인증 상태 판단 및 리다이렉트를 보류한다.

---

## 제외 항목 (What NOT to Build)

다음 항목은 이 SPEC의 구현 범위에 명시적으로 포함되지 않는다.

1. **도서 리스팅 관리 UI** — 별도 SPEC에서 다룬다. 이 SPEC은 인증 및 관리자 계정 관리 UI에만 집중한다.
2. **주문 관리 UI** — 별도 SPEC에서 다룬다.
3. **대시보드/홈 화면 UI** — 로그인 성공 후 리다이렉트 대상으로만 참조되며, 실제 대시보드 컴포넌트는 이 SPEC의 범위 밖이다.
4. **소셜 로그인 UI** — Google, GitHub 등 OAuth 기반 UI는 구현하지 않는다.
5. **다중 인증(MFA) UI** — TOTP 앱 연동, SMS 인증 화면은 구현하지 않는다.
6. **이메일 기반 비밀번호 재설정 UI** — 이메일 발송 또는 재설정 링크 흐름은 구현하지 않는다.
7. **관리자 본인 프로필 수정** — 로그인한 관리자가 본인 계정의 username, 비밀번호를 자체 수정하는 UI는 이 SPEC에 포함되지 않는다.
8. **감사 로그 조회 UI** — 관리자 행동 기록 조회 화면은 v2 이후 도입한다.
9. **Access Token의 localStorage 저장** — 보안 정책에 따라 Access Token은 반드시 메모리(Zustand)에만 저장한다. localStorage 저장 방식은 허용하지 않는다.
10. **관리자 목록 페이지네이션** — v1에서는 전체 목록을 단일 페이지로 표시한다. 관리자 수가 적으므로 페이지네이션은 v2에서 고려한다.

---

## 기술 설계 (Technical Design)

### 컴포넌트 트리

```
App
├── AuthProvider (Zustand store 초기화 + restoreSession 호출)
│   └── Router
│       ├── PublicRoute (/login)  — 인증 시 / 로 리다이렉트
│       │   └── LoginPage
│       │       └── LoginForm (React Hook Form + shadcn/ui)
│       └── ProtectedRoute (미인증 시 /login 리다이렉트; isLoading=true 시 스피너)
│           ├── AppLayout
│           │   ├── Sidebar (역할 기반 메뉴 — admin은 관리자 계정 관리 항목 숨김)
│           │   └── Outlet
│           ├── DashboardPage (/) — 빈 셸, 내용은 별도 SPEC
│           ├── SuperAdminRoute (/admin-users — admin이면 /403으로 리다이렉트)
│           │   └── AdminUsersPage
│           │       ├── AdminUsersTable
│           │       ├── CreateAdminDialog (모달)
│           │       ├── EditAdminDialog (모달)
│           │       ├── ResetPasswordDialog (모달)
│           │       └── DeactivateConfirmDialog (모달)
│           └── ForbiddenPage (/403)
```

### 라우팅 구조

| 경로 | 컴포넌트 | 접근 조건 |
|------|----------|-----------|
| `/login` | LoginPage | 미인증 전용 (인증 시 `/`로 리다이렉트) |
| `/` | DashboardPage (빈 셸) | 인증 필수 |
| `/admin-users` | AdminUsersPage | 인증 필수 + `super_admin` 전용 (SuperAdminRoute 가드) |
| `/403` | ForbiddenPage | 모든 인증 사용자 접근 가능 |

> **모달 전략**: 관리자 생성/수정/비밀번호 초기화는 `/admin-users` 내 모달 다이얼로그로 처리한다. 별도 URL 경로(`/admin-users/new`, `/admin-users/:id/edit`)는 사용하지 않으며, SuperAdminRoute 단일 가드로 모든 접근을 보호한다.

### 인증 상태 형태 (Auth State Shape)

```typescript
// Zustand store
interface AuthState {
  accessToken: string | null;       // 메모리에만 저장 (절대 localStorage 금지)
  user: {
    id: number;
    username: string;
    role: 'super_admin' | 'admin';
    is_active: boolean;
  } | null;
  isAuthenticated: boolean;
  isLoading: boolean;               // 세션 복원 중 로딩 상태

  // Actions
  login: (credentials: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  restoreSession: () => Promise<void>; // 페이지 새로고침 시 호출
}

// localStorage 키
const REFRESH_TOKEN_KEY = 'scm_refresh_token';
```

### API 통합 패턴

```typescript
// axios 인스턴스 구성
// baseURL: http://localhost:8000/api/
// 요청 인터셉터: Authorization 헤더 자동 주입 (accessToken이 있을 때)
// 응답 인터셉터: 401 감지 → refreshToken() 호출 → 성공 시 재시도 → 실패 시 logout()

// TanStack Query 키 컨벤션
const adminUsersKeys = {
  all: ['admin-users'] as const,
  list: () => [...adminUsersKeys.all, 'list'] as const,
  detail: (id: number) => [...adminUsersKeys.all, 'detail', id] as const,
};
```

### 테스트 전략 (TDD)

- **단위 테스트**: Vitest + Testing Library
  - LoginForm: 유효성 검사, 에러 메시지, 로딩 상태
  - AuthStore: 로그인/로그아웃/세션 복원 로직
  - ProtectedRoute / SuperAdminRoute: 리다이렉트 동작
  - AdminUsersTable, CreateAdminDialog, EditAdminDialog, ResetPasswordDialog: 폼 검증 및 API 호출
- **API 모킹**: MSW (Mock Service Worker) — 실제 HTTP 요청 인터셉터 방식
- **커버리지 목표**: 인증 관련 로직 85% 이상
