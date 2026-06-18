# 프로젝트 구조 설계

## 백엔드 (Django) 디렉토리 구조

```
scm_v2_backend/
├── manage.py
├── pyproject.toml
├── requirements.txt
├── README.md
│
├── config/                          # 프로젝트 설정
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── constants.py                 # 상수, enum 정의
│
├── accounts/                        # 관리자 인증/권한
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── permissions.py               # 커스텀 권한 클래스
│   ├── urls.py
│   └── tests/
│
├── sync/                            # Shopify API 동기화
│   ├── models.py                    # sync 상태 추적
│   ├── views.py
│   ├── serializers.py
│   ├── tasks.py                     # Celery 작업
│   ├── shopify_client.py            # Shopify API 래퍼
│   ├── webhooks.py                  # Shopify 웹훅 핸들러
│   ├── urls.py
│   └── tests/
│
├── listings/                        # 도서 리스팅 관리
│   ├── models.py                    # Book, Listing, Stock
│   ├── views.py
│   ├── serializers.py
│   ├── filters.py                   # 검색/필터 로직
│   ├── managers.py                  # 쿼리 최적화 (select_related, prefetch_related)
│   ├── urls.py
│   └── tests/
│
├── orders/                          # 주문 관리
│   ├── models.py                    # Order, OrderItem
│   ├── views.py
│   ├── serializers.py
│   ├── filters.py
│   ├── managers.py
│   ├── urls.py
│   └── tests/
│
├── common/                          # 공통 유틸리티
│   ├── pagination.py
│   ├── exceptions.py
│   ├── middleware.py
│   └── utils.py
│
└── tests/
    ├── fixtures/
    ├── factories/
    └── conftest.py
```

---

## 프론트엔드 (React + TypeScript) 디렉토리 구조

```
scm_v2_frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts (또는 next.config.js)
├── README.md
│
├── src/
│   ├── index.tsx
│   ├── App.tsx
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Navigation.tsx
│   │   │   └── Footer.tsx
│   │   │
│   │   ├── tables/
│   │   │   ├── ListingsTable.tsx    # TanStack Table 기반 도서 테이블
│   │   │   ├── OrdersTable.tsx
│   │   │   └── TableFilters.tsx
│   │   │
│   │   ├── forms/
│   │   │   ├── ListingForm.tsx
│   │   │   ├── OrderStatusForm.tsx
│   │   │   └── SearchBar.tsx
│   │   │
│   │   └── modals/
│   │       ├── ConfirmDialog.tsx
│   │       └── DetailModal.tsx
│   │
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── ListingsPage.tsx
│   │   ├── OrdersPage.tsx
│   │   ├── SyncStatusPage.tsx
│   │   └── NotFoundPage.tsx
│   │
│   ├── hooks/
│   │   ├── useListings.ts           # TanStack Query 쿼리
│   │   ├── useOrders.ts
│   │   ├── useAuth.ts
│   │   └── usePagination.ts
│   │
│   ├── services/
│   │   ├── api.ts                   # Axios 인스턴스
│   │   ├── listings.ts              # Listings API 호출
│   │   ├── orders.ts
│   │   ├── auth.ts
│   │   └── sync.ts
│   │
│   ├── store/
│   │   ├── authStore.ts             # Zustand 상태 관리
│   │   ├── filterStore.ts           # 필터 상태
│   │   └── notificationStore.ts
│   │
│   ├── types/
│   │   ├── api.ts                   # API 응답 타입
│   │   ├── models.ts                # 도메인 모델
│   │   └── forms.ts
│   │
│   ├── utils/
│   │   ├── format.ts
│   │   ├── validation.ts
│   │   └── helpers.ts
│   │
│   ├── styles/
│   │   ├── globals.css
│   │   ├── variables.css
│   │   └── tailwind.config.js (tailwindcss 사용 시)
│   │
│   └── constants/
│       ├── api.ts                   # API 엔드포인트
│       ├── messages.ts
│       └── enums.ts
│
├── public/
│   ├── favicon.ico
│   └── assets/
│
└── tests/
    ├── unit/
    ├── integration/
    └── mocks/
```

---

## 설정 파일 구조

### 백엔드 설정 파일

```
scm_v2_backend/

├── .env                             # 환경 변수 (git ignore)
├── .env.example                     # 환경 변수 템플릿
├── pyproject.toml                   # Poetry 의존성
│
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                  # 공통 설정
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   │
│   └── logging.py                   # 로깅 설정
│
└── celery_config.py                 # Celery + Celery Beat 설정
```

### 프론트엔드 설정 파일

```
scm_v2_frontend/

├── .env                             # 환경 변수
├── .env.example
│
├── vite.config.ts (또는 next.config.js)
├── tsconfig.json
├── jest.config.js                   # 테스트 설정
├── eslint.config.js
└── prettier.config.js
```

---

## 데이터베이스 (MySQL RDS)

### 스키마 구조

```
scm_v2_db/

├── migrations/
│   ├── 0001_initial.py              # 초기 스키마
│   ├── 0002_add_shopify_sync_models.py
│   └── ...
│
└── schema.sql                       # 스키마 문서 (선택)

주요 테이블:
  - accounts_admin (관리자 계정)
  - listings_book (도서 기본정보)
  - listings_listing (Shopify 리스팅)
  - listings_stock (재고 정보)
  - orders_order (주문)
  - orders_orderitem (주문 항목)
  - sync_shopifysync (동기화 상태/로그)
```

---

## Docker 컨테이너 구조 (선택)

```
docker-compose.yml

services:
  backend:
    build: ./scm_v2_backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [redis, mysql]
  
  frontend:
    build: ./scm_v2_frontend
    ports: ["3000:3000"]
  
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
    ports: ["3306:3306"]
    volumes: [mysql-data:/var/lib/mysql]
  
  celery:
    build: ./scm_v2_backend
    command: celery -A config worker -l info
    depends_on: [redis, mysql]

volumes:
  mysql-data:
```

---

## 배포 구조 (AWS)

```
AWS Infrastructure:

  ECS (Docker)
    ├── backend-service (Django + Gunicorn)
    ├── frontend-service (Nginx, React build)
    └── celery-worker (Celery + Redis)
  
  RDS (MySQL 8.0)
    └── scm_v2_prod (기존 인스턴스 재사용)
  
  ElastiCache (Redis)
    ├── celery-broker
    └── session-cache
  
  CloudFront (CDN)
    └── React Static Assets
  
  ALB (Application Load Balancer)
    ├── backend: /api/*
    └── frontend: /*
```

---

## 개발 워크플로우

### 로컬 개발 환경

```
scm_v2/                              # 최상위 프로젝트
├── backend/                         # Django
├── frontend/                        # React
├── docs/                            # 프로젝트 문서
├── docker-compose.dev.yml
├── .gitignore
└── README.md
```

---

**핵심 설계 원칙**:
- **관심사 분리** — 각 앱(sync, listings, orders)이 독립적인 도메인 관리
- **성능 최적화** — managers.py로 쿼리 최적화 (select_related, prefetch_related)
- **테스트 주도** — 각 앱에 tests/ 디렉토리 분리
- **타입 안정성** — TypeScript로 프론트엔드 타입 안정성 확보
- **확장성** — 새로운 기능(예: 대시보드)은 새로운 앱으로 추가 가능
