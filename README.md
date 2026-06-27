# SCM v2 — Shopify 도서 재고 및 주문 관리 시스템

Shopify 연동 도서 재고 및 주문 관리 관리자 애플리케이션. 관리자 전용 내부 웹 애플리케이션입니다.

---

## 현재 구현 상태

| 기능 | 상태 |
|------|------|
| 관리자 인증 (JWT) | ✅ 구현 완료 (SPEC-AUTH-001) |
| 역할 기반 접근 제어 (RBAC) | ✅ 구현 완료 (SPEC-AUTH-001) |
| 관리자 계정 관리 API | ✅ 구현 완료 (SPEC-AUTH-001) |
| 도서 검색 (ISBN + 제목) | ✅ 구현 완료 (SPEC-BOOK-SEARCH-001) |
| 도서 정보 수정 | ✅ 구현 완료 (SPEC-BOOK-EDIT-001) |
| 사이드바 내비게이션 | ✅ 구현 완료 (SPEC-NAV-SIDEBAR-001) |
| ISBN 일괄 추가 | ✅ 구현 완료 (SPEC-INVEN-ADD-001) |
| 빠른 리스팅 추가 | ✅ 구현 완료 (SPEC-FAST-LISTING-ADD-001) |
| Etoile 재고 현황 대시보드 | ✅ 구현 완료 (SPEC-ETOILE-DASHBOARD-001) |
| Shopify 주문 동기화 | ✅ 구현 완료 (SPEC-ORDER-001) |
| 주문 목록 조회 | ✅ 구현 완료 (SPEC-ORDER-001) |
| 주문 상세 페이지 | ✅ 구현 완료 (SPEC-ORDER-003) |
| 주문 메모 해결 기능 | ✅ 구현 완료 |
| 발주 관리 시스템 | ✅ 구현 완료 (SPEC-PURCHASE-ORDER-001) |
| 창고 재고 관리 | ✅ 구현 완료 (SPEC-WAREHOUSE-001) |

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

## 프론트엔드 설정

### 설치

```bash
cd frontend
npm install
```

### 개발 서버 실행

```bash
cd frontend
npm run dev
```

개발 서버가 `http://localhost:5173`에서 실행됩니다.

### 빌드

```bash
cd frontend
npm run build
```

### 테스트

```bash
cd frontend
npx vitest run
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

### 도서 관리 (Book Management)

| 메서드 | 경로 | 설명 | 인증 필요 |
|--------|------|------|-----------|
| GET | `/api/book/search/` | 도서 검색 (ISBN 또는 제목) | ✅ |
| GET | `/api/book/{id}/` | 도서 상세 조회 (통합 정보) | ✅ |
| PATCH | `/api/book/{id}/info/` | 도서 기본 정보 수정 | ✅ |
| POST | `/api/book/{id}/notes/` | 노트 생성 | ✅ |
| PATCH | `/api/book/notes/{note_id}/resolve/` | 노트 완료 처리 | ✅ |
| PATCH | `/api/book/{id}/shopify-status/` | 본관 Shopify 상태 변경 | ✅ |
| PATCH | `/api/book/{id}/etoile-shopify-status/` | Etoile Shopify 상태 변경 | ✅ |
| PATCH | `/api/book/{id}/etoile-tags/` | Etoile 태그 관리 | ✅ |
| POST | `/api/book/inven-skus/` | ISBN 일괄 추가 | ✅ |
| POST | `/api/book/fast-listing-skus/` | 빠른 리스팅 추가 | ✅ |
| GET | `/api/book/etoile/dashboard/` | Etoile 재고 현황 조회 | ✅ |

### 주문 관리 (Order Management)

| 메서드 | 경로 | 설명 | 인증 필요 |
|--------|------|------|-----------|
| POST | `/api/orders/sync/` | Shopify 주문 동기화 (Booksen·Etoile) | ✅ |
| GET | `/api/orders/` | 주문 목록 조회 (필터·페이지네이션) | ✅ |

**동기화 응답:**
```json
{
  "status": "completed",
  "stores": {
    "booksen": { "synced_count": 5, "updated_count": 2, "error": null },
    "etoile":  { "synced_count": 3, "updated_count": 1, "error": null }
  },
  "total_synced": 8,
  "total_updated": 3
}
```

**목록 쿼리 파라미터:**

| 파라미터 | 설명 | 예시 |
|----------|------|------|
| `store_type` | 스토어 필터 | `booksen` \| `etoile` |
| `financial_status` | 결제 상태 필터 | `paid`, `pending`, `refunded` |
| `fulfillment_status` | 출고 상태 필터 | `unfulfilled`, `fulfilled` |
| `date_from` | 시작일 (YYYY-MM-DD) | `2025-01-01` |
| `date_to` | 종료일 (YYYY-MM-DD) | `2025-12-31` |
| `page` | 페이지 번호 (50건/페이지) | `2` |

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

### 백엔드 테스트

```bash
cd backend
pytest
```

커버리지 포함:
```bash
pytest --cov=accounts --cov=book --cov-report=term-missing
```

**현재 커버리지**: 99.78% (accounts), 18+ (book)

### 프론트엔드 테스트

```bash
cd frontend
npx vitest run
```

실시간 모드:
```bash
cd frontend
npx vitest
```

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
│   ├── book/                   # 도서 관리 앱
│   │   ├── models.py           # Book, BookNote, Shopify, Etoile 모델
│   │   ├── views.py            # 도서 검색, CRUD, 대시보드 뷰
│   │   ├── serializers.py      # 도서 정보 시리얼라이저
│   │   ├── permissions.py      # 도서 접근 권한
│   │   ├── urls.py             # 도서 API 라우팅
│   │   ├── migrations/         # DB 마이그레이션
│   │   └── tests/              # 테스트 파일
│   ├── order/                  # 주문 관리 앱 (SPEC-ORDER-001)
│   │   ├── models.py           # Order, Customer, LineItem, Refund 등 7개 모델
│   │   ├── views.py            # 주문 동기화·목록 뷰
│   │   ├── serializers.py      # 주문 시리얼라이저 (has_refund 계산 필드)
│   │   ├── shopify_orders.py   # Shopify API 클라이언트 (cursor pagination)
│   │   ├── urls.py             # 주문 API 라우팅
│   │   ├── migrations/         # DB 마이그레이션
│   │   └── tests/              # 29개 pytest 테스트
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py         # 공통 설정 (JWT, DRF, CORS)
│   │   │   └── local.py        # 로컬 개발 설정 (SQLite)
│   │   └── urls.py             # 루트 URL 설정
│   ├── pyproject.toml          # 의존성 관리
│   └── pytest.ini              # 테스트 설정
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── components/         # React 컴포넌트
│   │   │   └── ui/             # UI 컴포넌트 (Button, Select, etc.)
│   │   ├── features/           # 기능별 컴포넌트
│   │   │   ├── book/           # 도서 관리 기능
│   │   │   └── order/          # 주문 관리 기능 (useOrders, useOrderSync)
│   │   ├── pages/              # 페이지 컴포넌트
│   │   │   ├── OrdersPage.tsx  # 주문관리 페이지
│   │   │   └── BookDetailPage.tsx
│   │   ├── hooks/              # 커스텀 훅 (TanStack Query)
│   │   ├── services/           # API 호출 서비스
│   │   └── App.tsx             # 메인 앱 컴포넌트
│   ├── package.json            # 의존성 관리 (npm)
│   ├── vite.config.ts          # Vite 설정
│   ├── vitest.config.ts        # Vitest 설정
│   └── tsconfig.json           # TypeScript 설정
├── .moai/                      # MoAI 프로젝트 메타데이터
│   └── specs/                  # SPEC 문서
│       ├── SPEC-AUTH-001/      # 인증 SPEC
│       ├── SPEC-BOOK-SEARCH-001/
│       ├── SPEC-BOOK-EDIT-001/
│       ├── SPEC-NAV-SIDEBAR-001/
│       ├── SPEC-INVEN-ADD-001/
│       ├── SPEC-FAST-LISTING-ADD-001/
│       └── SPEC-ETOILE-DASHBOARD-001/
└── README.md
```

---

## 기술 스택

### 백엔드

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 런타임 |
| Django | 5.2+ | 웹 프레임워크 |
| Django REST Framework | 3.14+ | RESTful API |
| djangorestframework-simplejwt | 5.3+ | JWT 인증 + 블랙리스트 |
| pytest / pytest-django | 7.4+ / 4.7+ | 테스트 |
| ruff | 0.1+ | 린트 및 포맷 |
| MySQL | 8.0+ | 데이터베이스 |

### 프론트엔드

| 기술 | 버전 | 용도 |
|------|------|------|
| React | 19+ | UI 라이브러리 |
| TypeScript | 5.0+ | 타입 안정성 |
| Vite | 5.0+ | 번들러 |
| TanStack Query | 5.0+ | 상태 관리 (서버 상태) |
| React Router | 6.0+ | 라우팅 |
| Tailwind CSS | 3.0+ | CSS 프레임워크 |
| Vitest | 1.0+ | 단위 테스트 |
| React Testing Library | 14.0+ | 컴포넌트 테스트 |

---

## 라이선스

내부 사용 전용.
