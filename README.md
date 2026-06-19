# SCM v2 — Shopify 도서 재고 및 주문 관리 시스템

Shopify 연동 도서 재고 및 주문 관리 관리자 애플리케이션. 관리자 전용 내부 웹 애플리케이션입니다.

---

## 현재 구현 상태

| 기능 | 상태 |
|------|------|
| 관리자 인증 (JWT) | ✅ 구현 완료 (SPEC-AUTH-001) |
| 역할 기반 접근 제어 (RBAC) | ✅ 구현 완료 (SPEC-AUTH-001) |
| 관리자 계정 관리 API | ✅ 구현 완료 (SPEC-AUTH-001) |
| Shopify 주문 동기화 | 🔜 예정 |
| 도서 리스팅 관리 | 🔜 예정 |

---

## 백엔드 설정

### 요구사항

- Python 3.11+
- MySQL 8.0+ (또는 SQLite — 개발 환경)

### 설치

```bash
cd backend

# 의존성 설치 (Poetry)
poetry install

# 또는 pip
pip install djangorestframework djangorestframework-simplejwt python-decouple django-cors-headers
```

### 환경 변수

`backend/.env.example`을 복사하여 `backend/.env`로 설정합니다.

```bash
cp .env.example .env
```

`.env` 파일 항목:

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here-change-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database (MySQL RDS — 개발 환경은 SQLite 자동 사용)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=scm_v2
DB_USER=scm_user
DB_PASSWORD=your-db-password

# JWT (선택 — 기본값 사용 가능)
# SIMPLE_JWT_ACCESS_TOKEN_LIFETIME=15   # minutes
# SIMPLE_JWT_REFRESH_TOKEN_LIFETIME=24  # hours
```

### 데이터베이스 마이그레이션

```bash
cd backend
python manage.py migrate
```

### 개발 서버 실행

```bash
cd backend
python manage.py runserver
```

---

## API 엔드포인트

기본 URL: `http://localhost:8000/api/`

### 인증 (Authentication)

| 메서드 | 경로 | 설명 | 인증 필요 |
|--------|------|------|-----------|
| POST | `/api/auth/login/` | 관리자 로그인 (Access + Refresh Token 발급) | ❌ |
| POST | `/api/auth/logout/` | 로그아웃 (Refresh Token 블랙리스트 처리) | ✅ |
| POST | `/api/auth/token/refresh/` | Access Token 갱신 | ❌ |

**로그인 요청:**
```json
POST /api/auth/login/
{
  "username": "admin",
  "password": "password123"
}
```

**로그인 응답:**
```json
{
  "access": "<JWT Access Token — 15분 유효>",
  "refresh": "<JWT Refresh Token — 24시간 유효>"
}
```

**인증 헤더:**
```
Authorization: Bearer <access_token>
```

### 관리자 계정 관리 (SuperAdmin 전용)

| 메서드 | 경로 | 설명 | 역할 |
|--------|------|------|------|
| GET | `/api/admin/users/` | 전체 관리자 목록 조회 | SUPER_ADMIN |
| POST | `/api/admin/users/` | 새 관리자 계정 생성 | SUPER_ADMIN |
| GET | `/api/admin/users/{id}/` | 특정 관리자 조회 | SUPER_ADMIN |
| PUT | `/api/admin/users/{id}/` | 관리자 정보 전체 수정 | SUPER_ADMIN |
| PATCH | `/api/admin/users/{id}/` | 관리자 정보 부분 수정 | SUPER_ADMIN |
| POST | `/api/admin/users/{id}/reset-password/` | 비밀번호 직접 초기화 | SUPER_ADMIN |

**계정 생성 요청:**
```json
POST /api/admin/users/
{
  "username": "new_admin",
  "password": "securepass123",
  "role": "admin"
}
```

### RBAC 역할 구조

| 역할 | 값 | 권한 |
|------|-----|------|
| SuperAdmin | `super_admin` | 모든 기능 접근 + 관리자 계정 관리 |
| Admin | `admin` | 도서 리스팅 관리, 주문 관리 |

> **보안 참고**: 역할 검증은 JWT 페이로드가 아닌 **데이터베이스 실시간 조회**로 처리됩니다 (REQ-AUTH-015).

---

## 테스트 실행

```bash
cd backend
pytest
```

커버리지 포함:
```bash
pytest --cov=accounts --cov-report=term-missing
```

**현재 커버리지**: 99.78% (91개 테스트)

### 테스트 파일 구성

| 파일 | 설명 |
|------|------|
| `test_login.py` | 로그인 성공/실패, 비활성화 계정 |
| `test_logout.py` | 로그아웃 및 토큰 블랙리스트 |
| `test_token_refresh.py` | Access Token 갱신, 만료 토큰 처리 |
| `test_permissions.py` | RBAC 역할별 접근 제어 |
| `test_admin_user_management.py` | 관리자 계정 CRUD |
| `test_account_deactivation.py` | 계정 비활성화 및 토큰 즉시 무효화 |
| `test_models.py` | AdminUser 모델 단위 테스트 |
| `test_security_must_pass.py` | 보안 필수 검증 5항목 (SEC-MUST-001~005) |

---

## 코드 품질

```bash
cd backend

# 린트 검사
ruff check .

# 포맷 적용
ruff format .
```

---

## 프로젝트 구조

```
scm_v2/
├── backend/                    # Django 백엔드
│   ├── accounts/               # 인증 및 RBAC 앱
│   │   ├── models.py           # AdminUser 모델
│   │   ├── views.py            # 인증/계정 관리 뷰
│   │   ├── serializers.py      # DRF 시리얼라이저
│   │   ├── permissions.py      # RBAC 권한 클래스
│   │   ├── signals.py          # 계정 비활성화 시 토큰 즉시 무효화
│   │   ├── urls.py             # API 라우팅
│   │   └── tests/              # 테스트 파일
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py         # 공통 설정 (JWT, DRF, CORS)
│   │   │   └── local.py        # 로컬 개발 설정 (SQLite)
│   │   └── urls.py             # 루트 URL 설정
│   ├── pyproject.toml          # 의존성 관리
│   └── pytest.ini              # 테스트 설정
├── .moai/                      # MoAI 프로젝트 메타데이터
│   └── specs/SPEC-AUTH-001/    # 인증 SPEC 문서
└── README.md
```

---

## 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 런타임 |
| Django | 5.0+ | 웹 프레임워크 |
| Django REST Framework | 3.14+ | RESTful API |
| djangorestframework-simplejwt | 5.3+ | JWT 인증 + 블랙리스트 |
| pytest / pytest-django | 7.4+ / 4.7+ | 테스트 |
| ruff | 0.1+ | 린트 및 포맷 |

---

## 라이선스

내부 사용 전용.
