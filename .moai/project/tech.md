# 기술 스택 및 구성

## 백엔드 스택 (Django + DRF)

### Python 및 핵심 프레임워크

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 런타임 |
| Django | 5.0+ | 웹 프레임워크 |
| Django REST Framework (DRF) | 3.14+ | RESTful API 구축 |
| django-cors-headers | 4.3+ | CORS 정책 관리 |

### 데이터베이스 및 ORM

| 기술 | 버전 | 용도 |
|------|------|------|
| MySQL | 8.0+ (AWS RDS) | 주요 데이터저장소 (기존 인스턴스 재사용) |
| mysqlclient | 2.2+ | MySQL 드라이버 |
| django-extensions | 3.2+ | Django 확장 유틸리티 |

### 비동기 작업 (Shopify API 동기화)

| 기술 | 버전 | 용도 |
|------|------|------|
| Celery | 5.3+ | 비동기 작업 큐 |
| django-celery-beat | 2.5+ | 정기 작업 스케줄링 (배치 동기화) |
| django-celery-results | 2.5+ | 작업 결과 저장소 |
| redis | 5.0+ | Celery broker + 캐시 (ElastiCache) |

### Shopify API 연동

| 기술 | 버전 | 용도 |
|------|------|------|
| shopify-python-api | 13.1+ | Shopify REST/GraphQL API 클라이언트 |
| requests | 2.31+ | HTTP 요청 (웹훅 검증, API 호출) |

### 인증 및 보안

| 기술 | 버전 | 용도 |
|------|------|------|
| djangorestframework-simplejwt | 5.3+ | JWT 토큰 인증 (관리자 로그인) |
| cryptography | 41.0+ | 암호화 (Shopify 웹훅 서명 검증) |
| python-dotenv | 1.0+ | 환경 변수 관리 |

### 성능 최적화

| 기술 | 버전 | 용도 |
|------|------|------|
| django-debug-toolbar | 4.1+ | 개발 환경 성능 디버깅 |
| dj-database-url | 2.1+ | 데이터베이스 URL 파싱 |
| django-filter | 23.3+ | 쿼리 필터링 및 검색 |
| rest-framework-filters | 1.0+ | DRF 필터백엔드 |

### 로깅 및 모니터링

| 기술 | 버전 | 용도 |
|------|------|------|
| python-json-logger | 2.0+ | JSON 로깅 |
| sentry-sdk | 1.36+ | 오류 추적 및 모니터링 |

### 테스트

| 기술 | 버전 | 용도 |
|------|------|------|
| pytest | 7.4+ | 테스트 프레임워크 |
| pytest-django | 4.7+ | Django 테스트 플러그인 |
| pytest-cov | 4.1+ | 커버리지 리포팅 |
| factory-boy | 3.3+ | 테스트 데이터 팩토리 |
| freezegun | 1.2+ | 시간 고정 테스트 |

---

## 프론트엔드 스택 (React + TypeScript)

### 핵심 프레임워크

| 기술 | 버전 | 용도 |
|------|------|------|
| React | 18.2+ | UI 라이브러리 |
| TypeScript | 5.2+ | 타입 안정성 |
| Vite | 5.0+ | 빌드 도구 (또는 Next.js 16+) |
| React Router | 6.16+ | 라우팅 |

### 상태 관리

| 기술 | 버전 | 용도 |
|------|------|------|
| Zustand | 4.4+ | 가벼운 상태 관리 (auth, filters, notifications) |
| TanStack Query (React Query) | 5.0+ | 서버 상태 관리 (API 캐싱, 동기화) |

### 데이터 테이블 및 UI

| 기술 | 버전 | 용도 |
|------|------|------|
| TanStack Table (React Table) | 8.10+ | 50만 건 대용량 테이블 렌더링 (가상 스크롤링) |
| Tailwind CSS | 3.3+ | 유틸리티 기반 스타일링 |
| shadcn/ui | 0.8+ | Tailwind 기반 컴포넌트 라이브러리 |
| date-fns | 2.30+ | 날짜 포맷팅 및 계산 |

### API 통신

| 기술 | 버전 | 용도 |
|------|------|------|
| axios | 1.6+ | HTTP 클라이언트 |
| zod 또는 yup | 3.22+ 또는 1.3+ | 스키마 검증 |

### 폼 관리

| 기술 | 버전 | 용도 |
|------|------|------|
| React Hook Form | 7.47+ | 폼 상태 관리 |
| @hookform/resolvers | 3.3+ | 폼 검증 리졸버 |

### 개발 도구

| 기술 | 버전 | 용도 |
|------|------|------|
| ESLint | 8.50+ | 코드 린팅 |
| Prettier | 3.0+ | 코드 포맷팅 |
| Jest | 29.7+ | 유닛 테스트 |
| @testing-library/react | 14.0+ | 컴포넌트 테스트 |
| Vitest | 0.34+ | 빠른 단위 테스트 (선택) |

---

## AWS 인프라

### 컴퓨팅

| 서비스 | 설정 | 용도 |
|--------|------|------|
| ECS (Elastic Container Service) | Fargate | Django + DRF 백엔드 배포 |
| EC2 (선택) | t3.medium+ | Celery 워커 실행 |
| Application Load Balancer (ALB) | HTTPS | API 및 프론트엔드 트래픽 분산 |

### 데이터베이스

| 서비스 | 설정 | 용도 |
|--------|------|------|
| RDS MySQL | db.r5.large+ (기존 재사용) | 도서/주문/동기화 데이터 저장 |
| ElastiCache Redis | cache.t3.micro+ | Celery broker, 세션 캐시, 결과 저장소 |

### 저장소

| 서비스 | 설정 | 용도 |
|--------|------|------|
| S3 | scm-v2-assets-prod | 업로드 파일, 정적 자산 (선택) |
| CloudFront | CDN | React 빌드 자산 분배 |

### 모니터링

| 서비스 | 설정 | 용도 |
|--------|------|------|
| CloudWatch | Logs, Metrics | 애플리케이션 로그 및 메트릭 |
| X-Ray (선택) | Tracing | 분산 추적 |

---

## 개발 환경 요구사항

### 로컬 개발 셋업

```bash
# 백엔드
Python 3.11+
MySQL 8.0 (또는 Docker)
Redis 7.0+ (또는 Docker)
PostgreSQL (테스트용, 선택)

# 프론트엔드
Node.js 18+ / npm 9+
또는 Bun 1.0+

# 인프라
Docker 24.0+
Docker Compose 2.20+
AWS CLI v2
```

### 필수 패키지 관리

```bash
백엔드: pyproject.toml (Poetry)
  - 의존성: Django, DRF, Celery, shopify-python-api, etc.
  - 개발 의존성: pytest, black, ruff, mypy

프론트엔드: package.json (npm/pnpm)
  - 의존성: React, TypeScript, TanStack Query/Table, Zustand, axios, etc.
  - 개발 의존성: Vite, ESLint, Prettier, Jest, Vitest
```

---

## Shopify 연동 아키텍처

### API 연동 방식

```
두 가지 경로:

1. 배치 동기화 (주기적)
   - django-celery-beat 스케줄러가 매 30분마다 작업 발생
   - shopify-python-api로 전체 주문/상품 조회
   - MySQL에 데이터 동기화
   - 대량 데이터 처리, 낮은 처리량 요청 (API 레이트 제한 회피)

2. 웹훅 기반 실시간 동기화
   - Shopify → Django /webhooks/ 엔드포인트로 POST
   - cryptography로 서명 검증 (보안)
   - Celery 태스크로 비동기 처리
   - 즉시 반영, 높은 품질 보증 (순서 보장)

병렬 처리:
  - Celery 워커 풀: 동시성 수준 조절 가능
  - Redis 브로커: 작업 큐 및 상태 저장소
  - Dead Letter Queue (DLQ): 실패한 작업 추적 및 재시도
```

---

## 성능 최적화 전략

### 데이터베이스 (MySQL RDS)

```
쿼리 최적화:
  - select_related(): 외래키 조인 쿼리 최소화
  - prefetch_related(): 역 관계 사전 로드
  - 적절한 인덱싱 (listing_id, order_status, created_at)
  - 페이지네이션 필수 (50만 건 전체 로드 금지)

커넥션 풀:
  - django-db-pool (선택): 커넥션 풀 관리
  - RDS 프록시 사용 (추후)
  - 타임아웃 설정 (idle: 30s, max: 300s)

Read Replica (추후):
  - RDS Read Replica로 읽기 쿼리 분산
  - 동기화는 Primary로 진행
```

### 캐싱 (Redis)

```
캐시 전략:
  - Celery 결과 캐시 (5분)
  - 자주 조회되는 도서 목록 캐시 (15분)
  - 관리자 세션 (30분)
  - API 응답 캐시 (5-10분)

캐시 무효화:
  - 쓰기 작업 후 즉시 무효화
  - TTL 기반 자동 만료
  - 명시적 캐시 플러시 (동기화 완료 후)
```

### 프론트엔드

```
렌더링 최적화:
  - TanStack Table 가상 스크롤링 (50만 건 테이블도 유연)
  - 청크 로딩 (첫 페이지만 즉시, 나머지 lazy)
  - 코드 분할 (각 페이지별 번들 최소화)

API 호출 최적화:
  - TanStack Query로 캐싱 및 배치 요청
  - GraphQL 사용 (선택): 필요한 필드만 조회
  - 요청 크기 최소화 (페이지네이션, 필터)
  - 검색 디바운싱 (300ms)

번들 최적화:
  - Vite로 빠른 빌드 및 HMR
  - Code splitting by route
  - Tree shaking 활성화
```

---

## 보안 고려사항

### 인증 및 권한

```
관리자 인증:
  - JWT (JSON Web Token) 사용
  - Refresh Token (24시간) + Access Token (15분)
  - djangorestframework-simplejwt 사용
  - HTTPS 필수 (모든 통신)

권한 검증:
  - view에서 permission_classes 검증
  - RBAC (Role-Based Access Control) 가능
  - 특정 도서/주문 접근 제한 (추후)
```

### Shopify 보안

```
웹훅 검증:
  - X-Shopify-Hmac-SHA256 헤더 검증
  - cryptography 라이브러리로 서명 확인
  - 검증 실패 시 즉시 거부 (HTTP 401)

API 키 관리:
  - .env 파일에 SHOPIFY_API_KEY, SHOPIFY_API_PASSWORD 저장
  - 프로덕션 환경: AWS Secrets Manager 사용
  - API 키 로테이션 (분기별)
```

### 데이터 보안

```
민감 정보:
  - 고객 개인정보 암호화 (추후)
  - 감사 로그 기록
  - 접근 제어 (관리자만)
```

---

## 배포 및 CI/CD

### CI/CD 파이프라인 (선택: GitHub Actions)

```yaml
프로세스:
  1. 코드 푸시 → GitHub
  2. 린트 검사 (ESLint, ruff)
  3. 테스트 실행 (pytest, Jest)
  4. 빌드 (Docker 이미지)
  5. ECR 푸시 (AWS)
  6. ECS 배포 (Fargate)
  7. 스모크 테스트
  8. 프로덕션 배포
```

### 배포 환경

```
개발 환경:
  - Docker Compose (로컬)
  - RDS (개발), ElastiCache (개발)

테스트 환경:
  - AWS ECS (Staging)
  - RDS (staging), ElastiCache (staging)

프로덕션:
  - AWS ECS (Fargate, Auto Scaling)
  - RDS MySQL (Multi-AZ 권장)
  - ElastiCache Redis (Multi-AZ 권장)
  - CloudFront CDN
```

---

## 외부 통합 및 API

### 제3자 서비스

| 서비스 | 용도 | API 버전 |
|--------|------|----------|
| Shopify | 주문/상품 조회, 웹훅 | REST v2024-01 + GraphQL |
| Sentry (선택) | 오류 추적 | v1 |
| Datadog (선택) | 모니터링 | v1 |

---

**최종 목표**: 50만 건 데이터를 빠르고 안정적으로 처리할 수 있는 엔터프라이즈급 스택 구축
