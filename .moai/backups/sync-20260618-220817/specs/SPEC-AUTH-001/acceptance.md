# SPEC-AUTH-001 인수 기준

## 개요

이 문서는 SPEC-AUTH-001의 모든 요구사항에 대한 검증 가능한 인수 기준을 정의한다. 각 시나리오는 Given-When-Then 형식으로 작성되며, 자동화 테스트와 수동 검증 모두에 활용된다.

---

## 인수 시나리오

### AC-AUTH-001: 유효한 자격증명으로 로그인 성공
**관련 요구사항**: REQ-AUTH-001, REQ-AUTH-002

**Given** username이 `admin_user`이고 password가 `password123`인 활성화된 관리자 계정이 데이터베이스에 존재한다.

**When** `POST /api/auth/login/` 요청에 `{"username": "admin_user", "password": "password123"}` 본문을 전송한다.

**Then**
- HTTP 200 OK 응답을 반환한다.
- 응답 본문에 `access` 필드(JWT Access Token)가 포함된다.
- 응답 본문에 `refresh` 필드(JWT Refresh Token)가 포함된다.
- Access Token의 유효기간은 현재 시각으로부터 15분이다.
- Refresh Token의 유효기간은 현재 시각으로부터 24시간이다.

---

### AC-AUTH-002: 잘못된 자격증명으로 로그인 실패
**관련 요구사항**: REQ-AUTH-003

**Given** 데이터베이스에 `admin_user` 계정이 존재한다.

**When** `POST /api/auth/login/` 요청에 `{"username": "admin_user", "password": "wrong_password"}` 본문을 전송한다.

**Then**
- HTTP 401 Unauthorized 응답을 반환한다.
- 응답 본문에 `access` 또는 `refresh` 필드가 없다.
- 오류 메시지는 "username이 틀렸습니다" 또는 "password가 틀렸습니다"처럼 특정 필드의 오류를 노출하지 않는다. (어떤 필드가 틀렸는지 알 수 없어야 함)

---

### AC-AUTH-003: 비활성화된 계정으로 로그인 시도
**관련 요구사항**: REQ-AUTH-009

**Given** username이 `inactive_admin`이고 `is_active=False`인 관리자 계정이 데이터베이스에 존재한다.

**When** `POST /api/auth/login/` 요청에 올바른 username과 password를 전송한다.

**Then**
- HTTP 401 Unauthorized 응답을 반환한다.
- 응답 본문에 토큰이 포함되지 않는다.

---

### AC-AUTH-004: 유효한 Refresh Token으로 Access Token 갱신
**관련 요구사항**: REQ-AUTH-004

**Given** 관리자가 로그인하여 유효한 Refresh Token을 보유하고 있다.

**When** `POST /api/auth/token/refresh/` 요청에 `{"refresh": "<유효한_refresh_token>"}` 본문을 전송한다.

**Then**
- HTTP 200 OK 응답을 반환한다.
- 응답 본문에 새로운 `access` 필드(Access Token)가 포함된다.
- 새 Access Token의 유효기간은 현재 시각으로부터 15분이다.

---

### AC-AUTH-005: 만료된 Access Token → 갱신 성공 후 재접근
**관련 요구사항**: REQ-AUTH-004, REQ-AUTH-008

**Given** 관리자의 Access Token이 만료되었고(15분 경과), 유효한 Refresh Token이 있다.

**When** 만료된 Access Token으로 `GET /api/admin/users/` 요청을 전송한다.

**Then**
- HTTP 401 Unauthorized 응답을 반환한다.

**When** 이후 유효한 Refresh Token으로 `POST /api/auth/token/refresh/`를 호출한다.

**Then**
- HTTP 200 OK와 함께 새로운 Access Token이 발급된다.
- 새 Access Token으로 `GET /api/admin/users/` 재요청 시 정상 응답을 반환한다.

---

### AC-AUTH-006: 로그아웃 후 Refresh Token 재사용 불가
**관련 요구사항**: REQ-AUTH-006, REQ-AUTH-007

**Given** 관리자가 로그인하여 유효한 Refresh Token을 보유하고 있다.

**When** `POST /api/auth/logout/` 요청에 해당 Refresh Token을 전송한다.

**Then**
- HTTP 200 OK (또는 204 No Content) 응답을 반환한다.
- 서버 측 블랙리스트에 해당 토큰이 추가된다.

**When** 이후 동일한 Refresh Token으로 `POST /api/auth/token/refresh/`를 요청한다.

**Then**
- HTTP 401 Unauthorized 응답을 반환한다.
- 새 Access Token이 발급되지 않는다.

---

### AC-AUTH-007: Admin이 관리자 계정 관리 엔드포인트 접근 시 403
**관련 요구사항**: REQ-AUTH-012, REQ-AUTH-013

**Given** role이 `ADMIN`인 관리자가 인증된 상태이다.

**When** 유효한 Access Token으로 `GET /api/admin/users/` 요청을 전송한다.

**Then**
- HTTP 403 Forbidden 응답을 반환한다.
- 관리자 목록 데이터가 응답에 포함되지 않는다.

**When** 동일한 토큰으로 `POST /api/admin/users/`, `PUT /api/admin/users/{id}/`, `POST /api/admin/users/{id}/reset-password/`를 요청한다.

**Then**
- 모든 요청에서 HTTP 403 Forbidden 응답을 반환한다.

---

### AC-AUTH-008: SuperAdmin이 새 관리자 계정 생성
**관련 요구사항**: REQ-AUTH-011, REQ-AUTH-016, REQ-AUTH-020, REQ-AUTH-021

**Given** role이 `SUPER_ADMIN`인 관리자가 인증된 상태이다.

**When** `POST /api/admin/users/` 요청에 `{"username": "new_admin", "password": "securepass123", "role": "admin"}` 본문을 전송한다.

**Then**
- HTTP 201 Created 응답을 반환한다.
- 응답 본문에 생성된 계정 정보(`id`, `username`, `role`, `is_active`)가 포함된다.
- 비밀번호 필드는 응답에 포함되지 않는다.
- 데이터베이스에 해당 계정이 생성된다.

**When** 동일한 username `new_admin`으로 다시 `POST /api/admin/users/`를 요청한다.

**Then**
- HTTP 400 Bad Request 응답을 반환한다.
- 응답에 username 중복 오류 메시지가 포함된다.

---

### AC-AUTH-009: SuperAdmin이 다른 관리자 비밀번호 직접 초기화
**관련 요구사항**: REQ-AUTH-018

**Given** role이 `SUPER_ADMIN`인 관리자가 인증된 상태이다. 대상 관리자 계정 ID가 `5`이다.

**When** `POST /api/admin/users/5/reset-password/` 요청에 `{"new_password": "newpassword123"}` 본문을 전송한다.

**Then**
- HTTP 200 OK 응답을 반환한다.
- 이후 대상 관리자가 기존 비밀번호로 로그인 시도하면 실패한다.
- 이후 대상 관리자가 새 비밀번호 `newpassword123`으로 로그인 시도하면 성공한다.

**When** 비밀번호를 7자 미만(`short1`)으로 설정 시도한다.

**Then**
- HTTP 400 Bad Request 응답을 반환한다.
- 비밀번호 최소 길이 오류 메시지가 포함된다.

---

### AC-AUTH-010: SuperAdmin이 관리자 계정 비활성화 및 토큰 무효화
**관련 요구사항**: REQ-AUTH-017, REQ-AUTH-022

**Given** role이 `SUPER_ADMIN`인 관리자가 인증된 상태이다. 대상 관리자가 로그인하여 유효한 Refresh Token을 보유하고 있다.

**When** SuperAdmin이 `PATCH /api/admin/users/{id}/` 요청에 `{"is_active": false}`를 전송한다.

**Then**
- HTTP 200 OK 응답을 반환한다.
- 대상 관리자의 기존 Refresh Token이 서버 측에서 무효화된다.

**When** 대상 관리자가 기존 Refresh Token으로 `POST /api/auth/token/refresh/`를 시도한다.

**Then**
- HTTP 401 Unauthorized 응답을 반환한다.

**When** 대상 관리자가 비활성화 후 로그인을 시도한다.

**Then**
- HTTP 401 Unauthorized 응답을 반환한다.

---

### AC-AUTH-011: 인증 없이 보호된 API 접근
**관련 요구사항**: REQ-AUTH-014

**Given** 어떠한 Authorization 헤더도 없는 요청이다.

**When** `GET /api/admin/users/` 또는 임의의 보호된 엔드포인트로 요청을 전송한다.

**Then**
- HTTP 401 Unauthorized 응답을 반환한다.
- 요청이 처리되지 않는다.

---

### AC-AUTH-012: SuperAdmin 전체 관리자 목록 조회
**관련 요구사항**: REQ-AUTH-019

**Given** role이 `SUPER_ADMIN`인 관리자가 인증된 상태이고, 데이터베이스에 5개의 관리자 계정이 존재한다.

**When** `GET /api/admin/users/` 요청을 전송한다.

**Then**
- HTTP 200 OK 응답을 반환한다.
- 응답 본문에 5개 계정 목록이 포함된다.
- 각 계정 항목에는 `id`, `username`, `role`, `is_active` 필드가 포함된다.
- 각 계정 항목에 `password` 필드가 포함되지 않는다.

---

### AC-AUTH-013: 만료된 Refresh Token으로 갱신 시도 → 401
**관련 요구사항**: REQ-AUTH-005

**Given** 관리자가 로그인하여 발급받은 Refresh Token이 있다. 해당 토큰의 유효기간(24시간)이 경과하였다.

**When** `POST /api/auth/token/refresh/` 요청에 만료된 Refresh Token을 전송한다.

**Then**
- HTTP 401 Unauthorized 응답을 반환한다.
- 응답 본문에 새로운 `access` 토큰이 포함되지 않는다.
- 만료된 토큰으로는 재인증이 불가능하며, 관리자는 다시 로그인해야 한다.

---

## 품질 게이트 기준 (Quality Gate Criteria)

### 테스트 커버리지
- `accounts/` 앱 전체 테스트 커버리지: **90% 이상**
- 모든 인수 시나리오에 대한 자동화 테스트 존재

### 보안 검증
- 모든 보호된 엔드포인트에 인증 미적용 시 HTTP 401 반환 확인
- 역할 검증이 데이터베이스 조회를 통해 수행됨을 코드 리뷰로 확인
- JWT Secret Key가 코드에 하드코딩되지 않음 확인

### API 응답 형식
- 모든 오류 응답이 표준 DRF 오류 형식을 준수
- 인증 실패 응답에 민감한 정보(비밀번호 힌트 등) 미포함

### 정의 완료 기준 (Definition of Done)

- [ ] TASK-AUTH-001 ~ TASK-AUTH-010의 모든 태스크 완료
- [ ] `accounts/tests/` 디렉토리에 모든 인수 시나리오 자동화 테스트 포함
- [ ] `pytest --cov=accounts` 결과 90% 이상 커버리지
- [ ] `ruff check accounts/` 통과 (lint 오류 없음)
- [ ] 모든 API 엔드포인트 수동 검증 완료 (Postman 또는 curl)
- [ ] RBAC 역할 검증이 데이터베이스 쿼리 기반임을 코드 리뷰로 확인
- [ ] `.env.example`에 `SECRET_KEY`, `SIMPLE_JWT` 관련 필수 환경 변수 문서화
- [ ] Django 마이그레이션 파일 생성 및 정상 적용 확인
- [ ] simplejwt 블랙리스트 마이그레이션 적용 확인
