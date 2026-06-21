# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### SPEC-AUTO-DIST-001: 발주처 자동 선택 로직 고도화

- `auto_select_distributor()` 5단계 의사결정 로직으로 교체
  - Step 0: DistributorVendorRule 우선 적용 (아가페 substring / 처음교육 exact match)
  - Step 1: 창고 재고 우선 — 한국(`warehouse`) / 서부CA·NJ(`warehouse_west`) 자동 분기
  - Step 2-A: 양사 재고 충분 — 가격·반품 8개 케이스 비교 (`candidate_basis` 레이블 포함)
  - Step 2-B/C: 단독 재고 — 북센 또는 교보 단독 선택
  - Step 2-D/E: 양사 재고 없음 — 북센 상태·가격 우위 기반 선택, 교보 반품 가능 시 오버라이드
- `VendorComparison` 모델 필드 3개 추가: `candidate_basis`, `price_diff`, `price_diff_alert`
- `VendorComparison.selected_distributor` choices 2개 → 7개 확장 (warehouse, warehouse_west, check_required, choeumgoyuk, agape 추가)
- `GET /api/purchase-orders/comparison/` 응답 확장: `candidate_basis`, `price_diff`, `price_diff_alert`, `bookseen_returnable`(가능/불가), `kyobo_returnable`(Y/N), `kyobo_status`, `kyobo_publisher`, `bookseen_arrival`
- 가격차이 알림: `abs(북센가 - 교보가) ≥ 3,000원` + 특정 조건 충족 시 `price_diff_alert = True`
- Django migration 0007 생성 (`orders_vendorcomparison` 컬럼 3개 추가)
- pytest 신규 38개 테스트 추가 (전체 125개 통과)

#### SPEC-ORDER-002: 주문 검색 기능

- `GET /api/orders/`에 `search` 쿼리 파라미터 추가
  - `name__icontains` 기본 포함
  - 숫자 입력 시 `order_number` exact match (OR)
  - 10~13자리 숫자 입력 시 `line_items__sku` ISBN 검색 (OR)
  - `distinct()` 적용으로 LineItem JOIN 중복 제거
  - 기존 필터(`store_type`, `financial_status` 등)와 AND 결합 유지
- `OrderListParams` 타입에 `search?: string` 추가
- `useOrders` 훅 `search` 파라미터 API 전달 구현
- 주문 목록 페이지 검색 입력 UI 추가
  - 검색어 없을 때 placeholder: "주문번호 또는 ISBN (Enter로 검색)"
  - Enter 키로 검색 실행
  - ✕ 버튼으로 검색 초기화
  - 결과 0건 시 "\"검색어\"에 해당하는 주문이 없습니다." 메시지 표시
- pytest 신규 7개 테스트 추가 (전체 161개 통과)

#### SPEC-ORDER-003: 주문 상세 페이지

- `GET /api/orders/{id}/` 단일 주문 상세 조회 엔드포인트 추가
  - `OrderDetailSerializer` — Customer·ShippingAddress·LineItem·ShippingLine·Refund 중첩 직렬화
  - `select_related("customer", "shipping_address")` + `prefetch_related("line_items", "shipping_lines", "refunds")` N+1 쿼리 방지
  - JWT 인증 필수 (`IsAuthenticated`)
- `/orders/:id` 라우트 추가 — 주문 목록 행 클릭 시 이동
- `OrderDetailPage` 6개 섹션: 주문정보·상품목록·결제정보·배송정보·고객정보·환불내역(조건부)
- `useOrderDetail(id)` 훅 (TanStack Query v5)
- 스켈레톤 로딩, 404 메시지, 에러 + 재시도 버튼 처리
- TDD 테스트 8개 추가

#### 주문 메모 해결 기능

- `Order.note_resolved` 필드 추가 (`BooleanField(default=False)`, 마이그레이션 0008)
- `GET /api/orders/notes/` — 미해결 메모 주문 목록 (note 있음 + note_resolved=False)
- `PATCH /api/orders/{id}/resolve-note/` — 메모 해결 처리
- `/orders/notes` 전용 페이지 — 낙관적 업데이트, 해결 버튼 (hover 시 녹색)
- 사이드바에 "미해결 메모" 메뉴 추가
- TDD 테스트 10개 추가

#### SPEC-ORDER-004: 주문 개별 재동기화

- `POST /api/orders/{id}/sync/` 단일 주문 재동기화 엔드포인트 추가
  - `sync_single_order_from_shopify()` 헬퍼 함수 — 개별 주문 Shopify API 조회 + DB 업서트
  - Shopify 404 응답 시 HTTP 404 반환 (삭제된 주문 처리)
  - 네트워크/서버 오류 시 HTTP 502 반환
  - 성공 시 `OrderDetailSerializer` 최신 데이터 HTTP 200 반환
- `OrderDetailPage` 헤더에 "다시 동기화" 버튼 추가
  - TanStack Query v5 `useMutation` 기반 — API 호출 상태(로딩/성공/오류) 관리
  - 성공 시 `queryClient.invalidateQueries({ queryKey: ['order-detail', id] })` 자동 리페치
  - 로딩 중 버튼 비활성화 + "동기화 중..." 텍스트 표시
  - 오류 시 API `error` 필드 또는 기본 메시지 표시
- URL 패턴 `orders/<int:pk>/sync/` — `orders/<int:pk>/` 보다 앞에 등록 (Django URL 매칭 순서 보장)
- TDD 테스트 6개 추가 (전체 185개 통과)

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

#### SPEC-PURCHASE-ORDER-001: 발주 관리 시스템

- 미발주 현황 조회 엔드포인트 (`GET /api/purchase-orders/unordered/`)
  - `PurchaseOrder`와 미연결 `LineItem`을 SKU별 집계, 주문시간 역순 정렬
  - 주문번호·SKU·수량·자동발주처 포함
- 발주 파일 생성 (`POST /api/purchase-orders/generate-order-file/`)
  - 북센: `ISBN/주문수량/도서명/출판사/저자/정가` 컬럼 Excel (.xlsx)
  - 교보: `ISBN/수량` 컬럼 Excel (.xlsx)
  - 파일명: `YYYYMMDD_{스토어명}_{주문N차}.xlsx` 형식
- 업체 자료 업로드 (`POST /api/purchase-orders/upload-vendor-file/`)
  - magic bytes (`0xD0CF11E0…`) 기반 `.xls`/`.xlsx` 자동 감지
  - 북센 파서 (xlrd): 고정 컬럼 위치 — ISBN(14), 출고가(6), 재고(7), 반품(10), 상태(11), 입고예정(15)
  - 교보 파서 (openpyxl): 출고가합(col14) ÷ 주문수량(col11) = 단가 자동 계산
- 발주처 비교 (`GET /api/purchase-orders/comparison/`)
  - 가용성·가격 기준 발주처 자동 추천 (동가이면 북센 우선)
  - 북센 상세: 재고량, 반품 가능 여부, 상태, 입고예정
  - 교보 상세: 재고량, 반품 가능 여부, 상태, 출판사, 주문수량, 출고가합
- 발주 확정 (`POST /api/purchase-orders/confirm/`) — `PurchaseOrder` 생성 및 `LineItem` M2M 연결
- 발주처 규칙 관리 (`GET/POST/DELETE /api/purchase-orders/vendor-rules/`)
  - 출판사명 → 처음교육/아가페 자동 라우팅 규칙 CRUD
- 발주 이력 조회 (`GET /api/purchase-orders/`) — 배포처·상태·날짜 필터, 페이지네이션
- `VendorComparison` 모델 북센/교보 상세 필드 확장 (migrations 0003~0005)
- `xlrd >= 2.0` 의존성 추가 (북센 .xls 파일 파싱)
- React 발주 관리 화면 (`/purchase-orders`) — 5탭 구조
  - 미발주 현황 탭: 전체/부분 선택, 발주처별 Excel 파일 생성
  - 업체 자료 업로드 탭: 파일 업로드, 발주처 선택
  - 발주 확정 탭: 비교 테이블, 발주처 수동 선택
  - 발주 이력 탭: 필터·페이지네이션
  - 발주처 규칙 설정 탭: 출판사→발주처 규칙 CRUD

#### SPEC-WAREHOUSE-001: 창고 재고 관리

- `WarehouseStock` 모델 신규 추가 — ISBN × 위치(한국/CA/NJ) 재고 관리 (migration 0006)
- 재고 목록 조회 (`GET /api/warehouse/stock/`) — ISBN별 피벗 응답 (한국·CA·NJ 컬럼, 셀 PK 포함)
  - **도서명 표시**: `book_info` 테이블 연동 (`Inven.inven_SKU` → `Info.name`) — 등록되지 않은 ISBN은 빈 칸 표시
- 단건 등록/수정 (`POST /api/warehouse/stock/upsert/`) — `update_or_create` 로직
- 일괄 등록 (`POST /api/warehouse/stock/bulk/`) — `[{isbn, location, quantity}]` 배열
- 단건 삭제 (`DELETE /api/warehouse/stock/<pk>/`)
- React 창고 재고 화면 (`/warehouse`)
  - ISBN × 위치 피벗 테이블, **도서명 컬럼** 추가, 셀별 삭제 버튼 (Trash2 아이콘)
  - **재고 합계 카드**: 테이블 상단에 한국/CA/NJ별 합계 및 총 합계 표시
  - 재고 추가 모달 (ISBN·위치 선택·수량)
  - 일괄 등록 모달 개선 — 위치 별칭 허용 (`한국`/`kor`/`kr` → `korea`), 파싱 실패 시 에러 토스트 표시
  - ISBN 검색 필터
- 사이드바 "창고 재고" 메뉴 추가 (Warehouse 아이콘)
- 11개 pytest 테스트

### Security

- 모든 도서 수정 API에 JWT 인증 적용 (`IsAuthenticated`)
- 노트 생성 시 작성자 자동 기록 (`created_by`)
- Shopify API 호출 실패 시 DB 상태 미변경 보장
- 발주 관리 및 창고 재고 전 엔드포인트 JWT `IsAuthenticated` 적용

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
