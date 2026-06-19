---
id: SPEC-AUTH-001
version: "1.1.0"
status: completed
created: "2026-06-18"
updated: "2026-06-18"
author: ggajo
priority: critical
issue_number: 0
---

## HISTORY

| 버전  | 날짜       | 작성자 | 변경 내용                              |
|-------|------------|--------|----------------------------------------|
| 1.0.0 | 2026-06-18 | ggajo  | 최초 작성 — 인터뷰 기반 요구사항 도출 |
| 1.0.1 | 2026-06-18 | ggajo  | 감사 결과 반영: REQ-AUTH-008 범위 수정(D4), REQ-AUTH-013 경로 확장(D7), REQ-AUTH-015 행동 중심 재작성(D6), Non-goals 비활성화 계정 토큰 동작 추가(D9) |

---

## 개요

### 목적

SCM v2는 내부 관리자 전용 웹 애플리케이션이다. 이 SPEC은 관리자 인증(로그인/로그아웃/토큰 갱신)과 역할 기반 접근 제어(RBAC) 시스템을 정의한다. 모든 API 엔드포인트는 인증된 관리자만 접근할 수 있으며, 역할(SuperAdmin / Admin)에 따라 접근 가능한 기능이 구분된다.

### 범위

- 관리자 로그인: username + password 방식
- JWT 기반 인증: Access Token (15분) + Refresh Token (24시간)
- 로그아웃: Refresh Token 서버 측 무효화
- 2단계 RBAC: SuperAdmin (전체 권한) / Admin (도서·주문 관리 한정)
- 관리자 계정 관리: SuperAdmin 전용 (생성·조회·수정·비활성화·비밀번호 초기화)

### 비목표 (Non-goals)

- 소셜 로그인 (Google, GitHub 등)
- 다중 인증 (MFA)
- 이메일 기반 계정 생성 인증 또는 비밀번호 재설정
- 감사 로그 (Audit Log)
- 로그인 실패 횟수 기반 계정 잠금 (v1 제외)
- 비밀번호 복잡도 규칙 고도화 (v1: 최소 길이만 적용)

---

## 요구사항

### 모듈 1: 인증 (Authentication)

#### REQ-AUTH-001 [NEW]
The 시스템 **shall** JWT 기반 인증을 사용하며, Access Token은 15분, Refresh Token은 24시간의 유효기간을 가진다.

#### REQ-AUTH-002 [NEW]
**When** 관리자가 유효한 username과 password로 로그인 요청을 전송하면, the 시스템 **shall** Access Token과 Refresh Token을 응답에 포함하여 반환한다.

#### REQ-AUTH-003 [NEW]
**When** 관리자가 존재하지 않는 username 또는 잘못된 password로 로그인 요청을 전송하면, the 시스템 **shall** HTTP 401 Unauthorized 응답을 반환하고 구체적인 인증 실패 사유를 노출하지 않는다.

#### REQ-AUTH-004 [NEW]
**When** 관리자가 유효한 Refresh Token으로 토큰 갱신 요청을 전송하면, the 시스템 **shall** 새로운 Access Token을 발급하여 반환한다.

#### REQ-AUTH-005 [NEW]
**When** 관리자가 만료되거나 무효화된 Refresh Token으로 토큰 갱신 요청을 전송하면, the 시스템 **shall** HTTP 401 Unauthorized 응답을 반환한다.

#### REQ-AUTH-006 [NEW]
**When** 관리자가 로그아웃 요청을 전송하면, the 시스템 **shall** 해당 Refresh Token을 서버 측에서 무효화하여 재사용을 방지한다.

#### REQ-AUTH-007 [NEW]
**If** 로그아웃 후 무효화된 Refresh Token으로 토큰 갱신을 시도하면, **then** the 시스템 **shall** HTTP 401 Unauthorized 응답을 반환한다.

#### REQ-AUTH-008 [NEW]
**While** 관리자 세션이 활성 상태인 동안, the 시스템 **shall** 모든 보호된 API 요청에서 Authorization 헤더의 Bearer Access Token을 검증한다. (로그인, 토큰 갱신 등 공개 엔드포인트는 제외)

#### REQ-AUTH-009 [NEW]
**If** 비활성화된(is_active=False) 계정으로 로그인을 시도하면, **then** the 시스템 **shall** HTTP 401 Unauthorized 응답을 반환한다.

---

### 모듈 2: 역할 기반 접근 제어 (RBAC)

#### REQ-AUTH-010 [NEW]
The 시스템 **shall** 관리자 계정에 SUPER_ADMIN 또는 ADMIN 두 가지 역할 중 하나를 할당한다.

#### REQ-AUTH-011 [NEW]
**While** 인증된 SUPER_ADMIN 역할의 관리자가 접근하는 동안, the 시스템 **shall** 도서 리스팅 관리, 주문 관리, 관리자 계정 관리를 포함한 모든 기능에 대한 접근을 허용한다.

#### REQ-AUTH-012 [NEW]
**While** 인증된 ADMIN 역할의 관리자가 접근하는 동안, the 시스템 **shall** 도서 리스팅 관리와 주문 관리 기능에만 접근을 허용한다.

#### REQ-AUTH-013 [NEW]
**If** ADMIN 역할의 관리자가 관리자 계정 관리 엔드포인트(`/api/admin/users/`, `/api/admin/users/{id}/`, `/api/admin/users/{id}/reset-password/`)에 접근 요청을 하면, **then** the 시스템 **shall** HTTP 403 Forbidden 응답을 반환한다.

#### REQ-AUTH-014 [NEW]
**If** 인증되지 않은 요청자가 임의의 보호된 API 엔드포인트에 접근을 시도하면, **then** the 시스템 **shall** HTTP 401 Unauthorized 응답을 반환한다.

#### REQ-AUTH-015 [NEW]
The 시스템 **shall** JWT 페이로드의 역할 정보가 변경되더라도 항상 서버 측 최신 역할 정보를 기준으로 접근을 결정한다. (JWT 페이로드의 역할 클레임은 접근 제어 판단에 사용하지 않는다)

---

### 모듈 3: 관리자 계정 관리 (User Management — SuperAdmin 전용)

#### REQ-AUTH-016 [NEW]
**Where** SUPER_ADMIN 역할의 관리자가 관리자 계정 관리 기능을 사용하는 경우, the 시스템 **shall** 새로운 관리자 계정을 username, 초기 비밀번호, 역할 정보를 포함하여 생성할 수 있도록 한다.

#### REQ-AUTH-017 [NEW]
**Where** SUPER_ADMIN 역할의 관리자가 관리자 계정 관리 기능을 사용하는 경우, the 시스템 **shall** 기존 관리자의 username, 역할, 활성화 상태를 수정할 수 있도록 한다.

#### REQ-AUTH-018 [NEW]
**Where** SUPER_ADMIN 역할의 관리자가 관리자 계정 관리 기능을 사용하는 경우, the 시스템 **shall** 특정 관리자의 비밀번호를 이메일 없이 직접 새 비밀번호로 초기화할 수 있도록 한다.

#### REQ-AUTH-019 [NEW]
**Where** SUPER_ADMIN 역할의 관리자가 관리자 계정 관리 기능을 사용하는 경우, the 시스템 **shall** 전체 관리자 계정 목록을 조회할 수 있도록 한다.

#### REQ-AUTH-020 [NEW]
**If** 새 관리자 계정 생성 시 이미 존재하는 username을 사용하면, **then** the 시스템 **shall** HTTP 400 Bad Request 응답과 함께 중복 username 오류 메시지를 반환한다.

#### REQ-AUTH-021 [NEW]
**If** 비밀번호가 최소 길이(8자) 미만으로 설정되면, **then** the 시스템 **shall** HTTP 400 Bad Request 응답과 함께 유효성 검사 오류 메시지를 반환한다.

#### REQ-AUTH-022 [NEW]
**When** SUPER_ADMIN이 관리자 계정을 비활성화(is_active=False)로 설정하면, the 시스템 **shall** 해당 계정의 기존 발급 Refresh Token을 즉시 무효화한다.

---

## 제외 항목 (What NOT to Build)

다음 항목은 이 SPEC의 구현 범위에 명시적으로 포함되지 않는다.

1. **소셜 로그인** — Google, GitHub, Kakao 등 OAuth 기반 외부 인증은 v1 범위 외이다.
2. **다중 인증 (MFA)** — TOTP, SMS 기반 2단계 인증은 v1 범위 외이다.
3. **이메일 기반 비밀번호 재설정 플로우** — 이메일 발송 또는 재설정 링크 메커니즘은 구현하지 않는다. 비밀번호 변경은 SuperAdmin의 직접 설정만 허용한다.
4. **감사 로그 (Audit Log)** — 관리자 행동 기록 및 추적 기능은 v2 이후 도입한다.
5. **로그인 실패 횟수 기반 계정 잠금** — 반복 실패 시 계정 잠금(Account Lockout) 정책은 v1에서 구현하지 않는다.
6. **일반 사용자 계정 시스템** — SCM v2는 내부 관리자 전용이다. Shopify 고객에 대한 별도 계정 시스템은 없다.
7. **권한 세분화 (Fine-grained Permission)** — 도서별·주문별 접근 제어 등의 세분화된 권한 관리는 v1 범위 외이다.
8. **Refresh Token 자동 로테이션** — 갱신 시 기존 토큰 자동 회전(Rotation) 전략은 구현하지 않는다. 단순 블랙리스트 방식으로 무효화한다.
9. **비활성화 계정의 기존 Access Token 즉시 무효화** — 계정 비활성화 시 기존 발급 Access Token은 만료 전까지 유효하다. 즉시 무효화는 v1에서 지원하지 않는다. (Refresh Token은 즉시 무효화됨, REQ-AUTH-022)

---

## 구현 노트 (Implementation Notes)

> 이 섹션은 sync 단계에서 자동 추가됨. 실제 구현과 계획의 차이를 기록함.

### 구현 완료일
2026-06-18

### 브랜치
`feature/SPEC-AUTH-001-admin-auth`

### 계획 대비 추가 구현

| 항목 | 사유 |
|------|------|
| `accounts/signals.py` | REQ-AUTH-022 — 계정 비활성화 시 Refresh Token 즉시 무효화를 Django Signal로 구현. 계획에 없었으나 기능 완성도를 위해 추가. |
| `accounts/tests/factories.py` | 테스트 데이터 생성 팩토리 (factory-boy). 중복 코드 제거를 위해 추가. |
| `accounts/tests/test_security_must_pass.py` | SEC-MUST-001~005 보안 필수 검증 테스트. 계획에 없었으나 보안 품질 강화를 위해 추가. |
| EDGE-013 예외 처리 | ADMIN 역할이 관리자 계정 관리 엔드포인트 접근 시 경로 확장 처리 |
| EDGE-015 예외 처리 | SuperAdmin의 자기 자신 비활성화 방지 로직 (`partial_update` 내 검증) |

### 품질 지표

| 지표 | 결과 |
|------|------|
| 테스트 수 | 91개 |
| 커버리지 | 99.78% |
| 린트 | ruff All checks passed |
| 보안 | SEC-MUST-001~005 모두 통과 |
