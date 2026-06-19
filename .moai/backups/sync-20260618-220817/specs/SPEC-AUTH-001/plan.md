# SPEC-AUTH-001 구현 계획

## 개요

이 계획서는 SPEC-AUTH-001(관리자 인증 및 역할 기반 접근 제어)의 구현 순서와 기술적 접근 방식을 정의한다. 모든 구현은 신규(Greenfield) 프로젝트이므로 기존 코드와의 충돌 없이 진행된다.

---

## 구현 태스크 목록

### 우선순위: High (핵심 인증 기반)

#### TASK-AUTH-001: Django 커스텀 유저 모델 설계
- `accounts/models.py`에 `AdminUser` 모델 정의
- Django `AbstractBaseUser` 또는 `AbstractUser` 확장
- `username` 필드를 로그인 식별자로 사용 (email 미사용)
- `role` 필드: `SUPER_ADMIN`, `ADMIN` 선택지를 가진 CharField
- `is_active` 필드: 계정 활성화 상태 제어
- `AUTH_USER_MODEL = 'accounts.AdminUser'` 설정

**설계 결정**: `AbstractUser` 확장이 권장됨. `username` 필드가 이미 존재하고, `is_active`, `is_staff`, `password` 관리 기능을 상속받을 수 있음. email 필드는 blank=True, null=True로 유지하되 로그인에 사용하지 않음.

```
Role 선택지:
  SUPER_ADMIN = 'super_admin'
  ADMIN = 'admin'
```

#### TASK-AUTH-002: simplejwt 설정 및 Refresh Token 블랙리스트
- `pyproject.toml`에 `djangorestframework-simplejwt[crypto]` 추가
- `config/settings/base.py`에 `SIMPLE_JWT` 설정 정의:
  - `ACCESS_TOKEN_LIFETIME`: timedelta(minutes=15)
  - `REFRESH_TOKEN_LIFETIME`: timedelta(hours=24)
  - `ROTATE_REFRESH_TOKENS`: False (단순 블랙리스트 방식)
  - `BLACKLIST_AFTER_ROTATION`: False
  - `AUTH_TOKEN_CLASSES`: simplejwt access token
  - `TOKEN_USER_CLASS`: `accounts.AdminUser`
- `INSTALLED_APPS`에 `'rest_framework_simplejwt.token_blacklist'` 추가
- 블랙리스트 마이그레이션 실행

#### TASK-AUTH-003: 로그인·로그아웃·토큰 갱신 뷰 구현
- `accounts/views.py`에 다음 뷰 구현:
  - `AdminLoginView`: simplejwt `TokenObtainPairView` 커스텀 확장. `is_active=False` 계정 로그인 거부.
  - `AdminLogoutView`: Refresh Token을 블랙리스트에 추가 후 HTTP 200 반환.
  - `AdminTokenRefreshView`: simplejwt `TokenRefreshView` 커스텀 확장. 블랙리스트 검증 포함.
- `accounts/serializers.py`에 로그인 요청/응답 시리얼라이저 정의
- `accounts/urls.py` 구성

#### TASK-AUTH-004: RBAC 권한 클래스 구현
- `accounts/permissions.py`에 커스텀 DRF permission 클래스 정의:
  - `IsSuperAdmin`: `request.user.role == 'super_admin'` 검증
  - `IsAdminOrSuperAdmin`: `request.user.role in ['super_admin', 'admin']` 검증
- 역할 검증은 JWT 토큰 페이로드가 아닌 데이터베이스에서 실시간 조회 (REQ-AUTH-015 준수)
- `IsAuthenticated`와 함께 조합하여 사용

### 우선순위: High (관리자 계정 관리)

#### TASK-AUTH-005: 관리자 계정 관리 API 구현
- `accounts/views.py`에 다음 ViewSet 구현:
  - `AdminUserViewSet`: ModelViewSet 기반
    - `list`: 전체 관리자 목록 조회
    - `create`: 새 관리자 계정 생성 (username, password, role)
    - `retrieve`: 특정 관리자 정보 조회
    - `update`/`partial_update`: username, role, is_active 수정
    - `reset_password`: POST `/api/admin/users/{id}/reset-password/` 커스텀 액션
  - 모든 뷰에 `permission_classes = [IsAuthenticated, IsSuperAdmin]` 적용
- `accounts/serializers.py`에 다음 시리얼라이저 정의:
  - `AdminUserListSerializer`: 목록 조회용 (password 필드 제외)
  - `AdminUserCreateSerializer`: 생성용 (password 포함, 최소 8자 검증)
  - `AdminUserUpdateSerializer`: 수정용 (username, role, is_active)
  - `PasswordResetSerializer`: 비밀번호 초기화용 (new_password 최소 8자 검증)

#### TASK-AUTH-006: 계정 비활성화 시 Refresh Token 무효화
- `accounts/views.py` 또는 `accounts/signals.py`에서:
  - 관리자 `is_active=False` 설정 시 해당 유저의 블랙리스트에 기존 토큰 추가
  - simplejwt 블랙리스트 모델(`OutstandingToken`) 활용

### 우선순위: Medium (프론트엔드)

#### TASK-AUTH-007: URL 라우팅 통합
- `config/urls.py`에 accounts URL 포함:
  - `POST /api/auth/login/`
  - `POST /api/auth/logout/`
  - `POST /api/auth/token/refresh/`
  - `GET /api/admin/users/`
  - `POST /api/admin/users/`
  - `GET /api/admin/users/{id}/`
  - `PUT /api/admin/users/{id}/`
  - `PATCH /api/admin/users/{id}/`
  - `POST /api/admin/users/{id}/reset-password/`

#### TASK-AUTH-008: 로그인 페이지 구현 (프론트엔드)
- `src/pages/LoginPage.tsx`: username + password 폼
- `src/services/auth.ts`: 로그인/로그아웃/토큰 갱신 API 호출 함수
- `src/store/authStore.ts` (Zustand): Access Token, 역할 정보 저장
- `src/hooks/useAuth.ts`: 인증 상태 관리 훅
- React Router Protected Route 구현: 미인증 시 `/login`으로 리다이렉트
- Axios 인터셉터: 401 응답 시 자동 토큰 갱신 시도, 실패 시 로그인 페이지로 이동

#### TASK-AUTH-009: 관리자 계정 관리 페이지 구현 (프론트엔드)
- `src/pages/AdminUsersPage.tsx`: 관리자 목록 테이블 + 생성/수정 모달
- SuperAdmin 역할일 때만 사이드바 메뉴에 노출
- shadcn/ui 컴포넌트 기반 폼 구성
- React Hook Form + zod 스키마 검증

### 우선순위: Low (테스트)

#### TASK-AUTH-010: 백엔드 테스트 작성
- `accounts/tests/` 디렉토리 구성:
  - `test_login.py`: 로그인 성공/실패 시나리오
  - `test_logout.py`: 로그아웃 및 토큰 무효화
  - `test_token_refresh.py`: 토큰 갱신 플로우
  - `test_permissions.py`: RBAC 접근 제어 시나리오
  - `test_admin_user_management.py`: 계정 관리 CRUD
- factory_boy로 `AdminUserFactory` 정의
- freezegun으로 토큰 만료 시나리오 테스트

---

## Django 모델 설계

```
accounts/models.py:

class AdminUser(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'SuperAdmin'
        ADMIN = 'admin', 'Admin'

    role = CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)
    # AbstractUser에서 상속: username, password, is_active, is_staff, date_joined
    # email 필드는 blank=True, null=True (로그인에 미사용)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['role']
```

---

## API 엔드포인트 목록

| 메서드 | 경로 | 설명 | 접근 권한 |
|--------|------|------|-----------|
| POST | `/api/auth/login/` | 로그인 (username+password → JWT 발급) | 미인증 |
| POST | `/api/auth/logout/` | 로그아웃 (Refresh Token 무효화) | 인증됨 |
| POST | `/api/auth/token/refresh/` | Access Token 갱신 | 인증됨 (유효한 Refresh Token) |
| GET | `/api/admin/users/` | 관리자 목록 조회 | SuperAdmin |
| POST | `/api/admin/users/` | 관리자 계정 생성 | SuperAdmin |
| GET | `/api/admin/users/{id}/` | 관리자 상세 조회 | SuperAdmin |
| PUT | `/api/admin/users/{id}/` | 관리자 정보 전체 수정 | SuperAdmin |
| PATCH | `/api/admin/users/{id}/` | 관리자 정보 부분 수정 | SuperAdmin |
| POST | `/api/admin/users/{id}/reset-password/` | 비밀번호 직접 초기화 | SuperAdmin |

---

## 권한 클래스 설계

```
accounts/permissions.py:

IsSuperAdmin:
  - has_permission: request.user.is_authenticated AND 데이터베이스에서 조회한 role == 'super_admin'

IsAdminOrSuperAdmin:
  - has_permission: request.user.is_authenticated AND 데이터베이스에서 조회한 role in ['super_admin', 'admin']
```

**중요**: 역할 검증은 반드시 데이터베이스 쿼리를 통해 수행한다 (REQ-AUTH-015). JWT 토큰 페이로드의 role 클레임은 사용하지 않는다.

---

## 리스크 분석

### 리스크 1: JWT Secret Key 노출
- 위험도: High
- 설명: `SECRET_KEY` 또는 `SIMPLE_JWT.SIGNING_KEY`가 버전 관리에 포함될 경우 전체 토큰 시스템이 위협받음
- 완화: `python-dotenv`로 환경 변수 관리, `.env`를 `.gitignore`에 포함, AWS 환경에서는 Secrets Manager 사용

### 리스크 2: 역할 우회 (Token Tampering)
- 위험도: High
- 설명: JWT 페이로드에 role을 포함시킬 경우 토큰 위변조로 권한 상승 가능
- 완화: REQ-AUTH-015에 명시된 대로 역할 검증을 항상 데이터베이스 조회로 수행. 토큰 페이로드에 role 클레임 미포함.

### 리스크 3: Refresh Token 블랙리스트 성능
- 위험도: Medium
- 설명: 블랙리스트 테이블이 커질수록 조회 성능 저하 가능
- 완화: `outstanding_token` 테이블에 `user_id`, `jti` 인덱스 확보. 만료된 토큰 주기적 정리 (Django management command 또는 Celery Beat 활용)

### 리스크 4: 계정 비활성화 후 기존 Access Token 유효
- 위험도: Medium
- 설명: `is_active=False` 처리 후에도 만료되지 않은 Access Token(최대 15분)이 유효하게 작동할 수 있음
- 완화: Access Token 유효기간 15분은 보안과 UX 간 허용 가능한 트레이드오프로 수용. 즉각적 무효화가 필요한 경우 Access Token 유효기간 단축(5분) 검토.

### 리스크 5: 프론트엔드 토큰 저장 방식
- 위험도: Medium
- 설명: localStorage에 JWT 저장 시 XSS 공격에 취약
- 완화: `httpOnly` 쿠키 방식 또는 메모리 저장 + Refresh Token은 httpOnly 쿠키 방식 권장. 프론트엔드 구현 시 expert-security 검토 권장.
