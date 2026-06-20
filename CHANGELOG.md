# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### SPEC-BOOK-EDIT-001: 도서 정보 수정 화면
- 도서 상세 정보 조회 엔드포인트 (`GET /api/book/{id}/`)
  - Inven, Info, BookNote, Shopify 상품, Etoile 정보 통합 조회
  - 미해결 노트 전체 + 최근 해결 노트 10건 포함
- 도서 기본 정보 수정 엔드포인트 (`PATCH /api/book/{id}/info/`)
  - 선택적 필드 업데이트 (partial update)
  - 기본, 부클, 교보, 중량, 장문 텍스트 필드 지원
- 노트 관리 엔드포인트
  - 노트 생성 (`POST /api/book/{id}/notes/`)
  - 노트 완료 처리 (`PATCH /api/book/notes/{note_id}/resolve/`)
- Shopify 상태 변경 엔드포인트
  - 본관 상태 변경 (`PATCH /api/book/{id}/shopify-status/`)
  - Etoile 상태 변경 (`PATCH /api/book/{id}/etoile-shopify-status/`)
- Etoile 태그 관리 엔드포인트 (`PATCH /api/book/{id}/etoile-tags/`)
- React 기반 도서 수정 화면 (`BookDetailPage`)
  - 탭 기반 섹션 구분 (기본 정보, 노트, Shopify, Etoile)
  - 실시간 필드 검증
  - 인라인 성공/오류 피드백 (토스트)
  - Etoile 섹션 조건부 표시
- 데이터베이스 마이그레이션
  - Info.name 전문 검색 인덱스 추가 (FULLTEXT NGRAM)

#### SPEC-NAV-SIDEBAR-001: 사이드바 계층형 내비게이션
- "도서관리" 그룹 헤더 — 클릭으로 접기/펼치기, 기본 펼침 상태
- 하위 항목: 대시보드 / ISBN 추가 / 빠른 리스팅 / Etoile 현황
- 현재 경로 정확 일치 시 `aria-current="page"` 활성 표시
- 접근성: `role="group"`, `aria-label`, `aria-expanded` 적용

#### SPEC-INVEN-ADD-001: ISBN 일괄 추가
- ISBN 일괄 등록 엔드포인트 (`POST /api/book/inven-skus/`)
- 중복 자동 감지 — 신규/중복 분리 반환
- React UI: 결과 시각화 (생성됨 녹색 / 중복 회색), 다시 등록하기 버튼

#### SPEC-FAST-LISTING-ADD-001: 빠른 리스팅 추가
- 빠른 리스팅 일괄 지정 엔드포인트 (`POST /api/book/fast-listing-skus/`)
- 3분기 처리 로직: 신규 생성 / 기존 업데이트 / 활성 도서(80·81·82) skip
- 활성 도서 보호 — status_of_shopify IN (80, 81, 82) 레코드 덮어쓰기 금지
- React UI: 결과 3섹션 (생성됨 녹색 / 업데이트됨 파란색 / 건너뜀 회색), 다시 등록하기 버튼

#### SPEC-ETOILE-DASHBOARD-001: Etoile 재고 현황 대시보드
- Etoile 현황 집계 엔드포인트 (`GET /api/book/etoile/dashboard/`)
- status_of_shopify 기준 그룹별 건수 + 레이블 매핑 + null 처리
- React 페이지 `/books/etoile`: 상태별 현황 테이블
- null status nulls_last 정렬, 로딩 스켈레톤, 에러 처리
- 9개 pytest 테스트

#### SPEC-ORDER-001: Shopify 주문 동기화 및 목록 조회
- 주문 동기화 엔드포인트 (`POST /api/orders/sync/`)
  - Booksen·Etoile 두 스토어에서 status=open 주문 일괄 동기화
  - Shopify Admin REST API v2024-10 cursor pagination (250건/페이지)
  - per-store `transaction.atomic()` 격리 — 한 스토어 실패가 타 스토어에 무영향
  - `update_or_create` upsert — 중복 동기화 안전, 신규/업데이트 건수 분리 응답
- 주문 목록 엔드포인트 (`GET /api/orders/`)
  - 50건/페이지 페이지네이션, shopify_created_at 최신순 정렬
  - 필터: store_type, financial_status, fulfillment_status, date_from/date_to
  - `has_refund` 실시간 계산 필드 (`prefetch_related("refunds")`, DB 컬럼 비정규화 없음)
- 환불 "취소" 표기: `has_refund=true` OR `financial_status="refunded"` → 빨간색 "취소"
- 7개 신규 DB 모델: Order, Customer, LineItem, ShippingLine, Refund, ShippingAddress, BillingAddress
- React 주문관리 페이지 (`/orders`) — 필터 + 테이블 + 페이지네이션 + 동기화 버튼
- 사이드바 "주문관리" 내비게이션 항목 추가
- 29개 pytest 테스트 (모델 4 + Shopify 클라이언트 10 + 동기화 뷰 4 + 목록 뷰 11)

### Security

- 모든 도서 수정 API에 JWT 인증 적용 (`IsAuthenticated`)
- 노트 생성 시 작성자 자동 기록 (`created_by`)
- Shopify API 호출 실패 시 DB 상태 미변경 보장

### Fixed

- 한국어 도서명 검색 정확도 개선 (FULLTEXT NGRAM 인덱스)

## [0.1.0] - 2026-06-20

### Added

#### SPEC-AUTH-001: 관리자 인증 및 RBAC
- JWT 기반 인증 (Access Token 15분 + Refresh Token 24시간)
- 2단계 RBAC (SuperAdmin, Admin)
- 토큰 블랙리스트 (로그아웃 및 계정 비활성화)
- 관리자 계정 관리 API
- 테스트: 91개, 커버리지 99.78%

#### SPEC-BOOK-SEARCH-001: 도서 검색 기능
- ISBN(inven_SKU) 및 제목(info.name) OR 검색 엔드포인트 (`GET /api/book/search/`)
- 페이지네이션 (50건/페이지)
- 한국어 전문 검색 지원 (FULLTEXT NGRAM 인덱스)
- 테스트: 18개

### Performance

- N+1 쿼리 최적화 (`select_related`)
- 도서 검색 인덱스 추가

### Infrastructure

- Django 5.2 LTS 기반 백엔드
- React 19 기반 프론트엔드
- MySQL RDS 데이터베이스
- JWT 기반 인증 시스템
