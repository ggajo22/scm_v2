# SCM v2 — 프로젝트 개요

## 프로젝트명 및 한줄 설명

**SCM v2** (Supply Chain Management v2)  
Shopify 연동 도서 재고 및 주문 관리 관리자 애플리케이션

---

## 타겟 사용자

- **관리자 전용** — 인증된 관리자만 접근 가능
- 일반 고객 사용자 없음
- 내부 팀 전용 웹 애플리케이션

---

## 구현 완료 기능

### 0. 관리자 인증 및 RBAC (SPEC-AUTH-001 — 완료)
- **JWT 기반 인증** — Access Token (15분) + Refresh Token (24시간)
- **2단계 RBAC** — SuperAdmin (전체 권한) / Admin (도서·주문 관리 한정)
- **서버 측 토큰 블랙리스트** — 로그아웃 및 계정 비활성화 시 즉시 무효화
- **관리자 계정 관리** — SuperAdmin 전용 CRUD + 비밀번호 초기화
- 테스트 커버리지 99.78% (91개 테스트)

### 0-1. 도서 검색 (SPEC-BOOK-SEARCH-001 — 완료)
- **ISBN 검색** — `inven_SKU` 부분 일치 검색 (icontains)
- **제목 검색** — `info.name` 부분 일치 검색 (icontains)
- **OR 조건 검색** — 단일 검색어로 ISBN/제목 동시 검색
- **페이지네이션** — 50건/페이지, 이전/다음 네비게이션
- **성능** — `select_related('info')` N+1 방지, `Info.name` 인덱스 추가
- 테스트 커버리지 18/18 (신규 13개)

### 0-2. 도서 정보 수정 화면 (SPEC-BOOK-EDIT-001 — 완료)
- **도서 상세 조회** — Inven/Info 모델 통합 조회 + 노트, Shopify, Etoile 데이터 연동 (`GET /api/book/{id}/`)
- **기본 정보 수정** — Info 필드 선택적 편집 (name, price, cover_image_url, 카테고리 등) (`PATCH /api/book/{id}/info/`)
- **메모(노트) 관리** — 일반/출고 노트 생성, 완료 처리, 미해결 + 최근 10건 조회
- **Shopify 상태 변경** — 본관/Etoile 별도 상태 제어 (active/draft)
- **Etoile 태그 관리** — 태그 편집 및 Shopify 동기화
- **React UI** — 탭 기반 섹션 구분, 실시간 검증 및 인라인 피드백
- 테스트 커버리지: 백엔드 8개 엔드포인트 단위 테스트, E2E 검색-상세-저장 흐름

### 0-4. 사이드바 계층형 네비게이션 (SPEC-NAV-SIDEBAR-001 — 완료)
- **그룹형 사이드바** — "도서관리" 그룹 헤더 아래 "대시보드", "ISBN 추가", "빠른 리스팅", "Etoile 현황" 하위 항목 배치
- **토글(접기/펼치기)** — ChevronDown 아이콘과 함께 클릭으로 하위 항목 토글, 기본 상태 펼침
- **활성 상태 표시** — 현재 경로 정확 일치 시에만 하위 항목 강조(`aria-current="page"`)
- **접근성** — `role="group"`, `aria-label`, `aria-expanded` 속성 적용
- **"관리자 계정 관리"** — super_admin 전용 최상위 항목 유지

### 0-5. 빠른 리스팅 추가 (SPEC-FAST-LISTING-ADD-001 — 완료)
- **일괄 리스팅 지정** — ISBN을 한 줄에 하나씩 입력해 `status_of_shopify=1` 일괄 처리 (`POST /api/book/fast-listing-skus/`)
- **3분기 처리 로직** — 신규 SKU 생성 / 기존 SKU 업데이트 / 활성 도서(80·81·82) 건너뜀
- **활성 도서 보호** — `status_of_shopify IN (80, 81, 82)` 레코드는 무조건 skip, 덮어쓰기 없음
- **결과 시각화** — 생성됨(녹색) / 업데이트됨(파란색) / 건너뜀(회색) 3섹션 표시
- **다시 등록하기** — 결과 확인 후 폼 초기화 버튼으로 연속 작업 지원
- 신규 생성 고정값: `vendor="북센"`, `store="책방"`, `is_use=1`

### 0-6. Etoile 재고 현황 대시보드 (SPEC-ETOILE-DASHBOARD-001 — 완료)
- **상태별 집계 API** — `GET /api/book/etoile/dashboard/` — `EtoileBookInven.status_of_shopify` 기준 그룹별 건수 반환
- **레이블 매핑** — `-1: gimssine 등록 대기 / 0: 리스팅 준비 / 12: 리스팅 제외 - 컨셉 / 80: 리스팅 완료 / 미정의: 정의되지 않은 상태 / null: 상태 없음`
- **null 정렬** — `status_of_shopify IS NULL` 레코드는 테이블 맨 아래 배치 (`nulls_last`)
- **상태별 현황 테이블** — 상태값 / 레이블 / 건수 3컬럼 테이블
- **로딩/에러 상태** — 스켈레톤 애니메이션 + 에러 메시지 처리
- 9개 pytest 테스트 (인증, 집계 정확성, 레이블 매핑, null 처리 등)

### 0-3. ISBN 일괄 추가 (SPEC-INVEN-ADD-001 — 완료)
- **ISBN 일괄 등록** — 한 줄에 하나씩 입력 후 신규 Inven 레코드 일괄 생성 (`POST /api/book/inven-skus/`)
- **중복 자동 감지** — 기존 DB 조회로 중복 SKU를 건너뛰고 생성됨/중복으로 분리 반환
- **결과 시각화** — 생성됨(녹색)/중복(회색) 구분 표시 및 상세 목록 제공
- **다시 등록하기** — 결과 확인 후 폼 초기화 버튼으로 연속 작업 지원
- 초기 등록 필드: `vendor="북센"`, `store="책방"`, `status_of_shopify=0`, `is_use=1`

### 0-7. Shopify 주문 동기화 및 목록 조회 (SPEC-ORDER-001 — 완료)
- **주문 동기화 API** — Booksen·Etoile 두 스토어에서 `status=open` 주문 수동 동기화 (`POST /api/orders/sync/`)
  - Shopify Admin REST API v2024-10, cursor pagination (250건/페이지)
  - per-store `transaction.atomic()` 격리 — 한 스토어 실패가 타 스토어 롤백 없음
  - `update_or_create` upsert — 중복 동기화 안전, 신규/업데이트 건수 분리 응답
- **주문 목록 조회** — 50건/페이지, `shopify_created_at` 최신순 (`GET /api/orders/`)
  - 필터: `store_type`, `financial_status`, `fulfillment_status`, `date_from`/`date_to`
  - `has_refund` 실시간 계산 — `prefetch_related("refunds")` N+1 없이 환불 여부 판별
- **환불 "취소" 표기** — `has_refund=true` OR `financial_status="refunded"` → 빨간색 "취소" 표시
- **7개 신규 DB 모델** — Order, Customer, LineItem, ShippingLine, Refund, ShippingAddress, BillingAddress
- **React 주문관리 페이지** (`/orders`) — 필터 UI + 테이블 + 페이지네이션 + 동기화 버튼
- **사이드바** — "주문관리" 내비게이션 항목 추가 (ShoppingCart 아이콘)
- 29개 pytest 테스트 (모델 4 + Shopify 클라이언트 10 + 동기화 뷰 4 + 목록 뷰 11)

### 8. LineItem 렉번호(Rack Number) 관리 (SPEC-ORDER-013 — 완료)
- **렉번호 필드** — `LineItem.rack_number` 추가 (CharField, max_length=10, blank=True, default="")
  - 기존 `location` 필드와 독립적, 계산/집계 없음
  - Order 레벨 롤업 필드 없음 — 순수 수동/업로드 전용 필드
- **단건 PATCH 엔드포인트** — `PATCH /api/purchase-orders/line-items/{id}/rack-number/`
  - 10자 초과 값 거부 (HTTP 400), 미존재 LineItem 404 응답
- **일괄 PATCH 엔드포인트** — `PATCH /api/purchase-orders/line-items/bulk-rack-number/`
  - LineItem id 목록 + 렉번호 값 입력, 미존재 id 목록 응답
- **Excel 업로드** — `POST /api/purchase-orders/upload-rack-number/`
  - 3컬럼(주문번호/SKU/렉번호) 헤더 자동 탐색 (대소문자 무시 substring 매칭)
  - `(order_number, sku)` 조합 기반 매칭, 중복 행은 마지막 행 우선
  - 매칭 건수/스킵 건수 분리 응답
- **신규 독립 페이지** — `/rack-number` 라우트
  - 주문번호 검색 (정확 일치)
  - LineItem 테이블 (SKU/도서명/렉번호)
  - 체크박스 다중 선택 + "전체선택" 토글
  - 인라인 편집 (개별 렉번호 수정)
  - 일괄 적용 컨트롤
  - Excel 파일 업로드 UI
- **사이드바** — "렉번호 관리" 메뉴 항목 추가 (MapPin 아이콘)
- **API 노출** — `LineItemDetailSerializer`에 `rack_number` 필드 추가
  - OrderDetailPage에는 UI 노출 금지 (데이터만 응답에 포함)
- 테스트 커버리지: 백엔드 51개 pytest (T1~T7), 프론트엔드 15개 테스트

### 9. 렉번호 요약 뷰 — 미출고 LineItem 렉별 교차 주문 집계 (SPEC-ORDER-014 — 완료)
- **렉번호 요약 탭** — `/rack-number` 페이지 2번째 탭 추가
  - Tab1 "주문 검색" — 기존 SPEC-ORDER-013 동작 무변경 (검색 → 체크박스 일괄 선택 → 인라인 편집)
  - Tab2 "렉번호 요약" — 신규 읽기 전용 집계 뷰 (항상 고정 미출고 필터 적용)
- **렉번호별 그룹핑** — 전체 주문을 가로지르는 미출고 LineItem을 렉번호별로 자동 그룹화
  - 각 그룹: 렉번호, 총 수량, 그룹 내 LineItem 목록 (주문번호/SKU/도서명/수량/물류상태)
  - 미지정 그룹 — `rack_number` 미기록 LineItem은 별도 "미지정" 그룹으로 자동 포함 (항상 마지막)
- **백엔드 신규 엔드포인트** — `GET /api/purchase-orders/line-items/rack-number-summary/` (읽기 전용, 비페이지네이션)
- **사용자 인터페이스** — 탭 활성화 시 자동 조회, 별도 검색 버튼 불필요
- **읽기 전용 강제** — Tab2에 체크박스, 일괄 적용, 인라인 편집 등 편집 기능 제공 금지
  - 렉번호 수정은 여전히 Tab1(SPEC-ORDER-013)에서만 가능
- 테스트 커버리지: 백엔드 13개 pytest (필터/그룹핑/null 처리), 프론트엔드 26개 테스트, 회귀 테스트 276개 통과

---

## 핵심 기능 (3가지 — 예정)

### 1. Shopify API 주문 동기화
- **배치 기반 동기화** — 정기적 데이터 동기화
- **웹훅 기반 실시간 동기화** — Shopify 이벤트 즉시 반영
- 주문 생성, 상태 변경, 결제 정보 실시간 연동

### 2. 도서 리스팅 관리
- **재고 상태 관리** — 수량 추가/감소
- **가격 관리** — 도서별 판매 가격 변경
- **노출 여부 관리** — 도서 공개/비공개 상태 제어

### 3. 주문 목록 조회 및 관리
- **대용량 주문 검색** — 50만 건 이상 데이터 빠른 검색
- **주문 필터링** — 상태, 날짜, 고객 기준 조회
- **주문 상태 업데이트** — 배송, 완료, 취소 상태 관리

---

## 1차 범위 외 (우선순위 낮음)

- 통계 대시보드 및 분석 기능
- 재고 발주 자동화 시스템
- 예측 분석 및 매출 리포팅

---

## 핵심 제약사항

### 성능 (가장 중요)
- 50만 건 이상의 도서 및 주문 데이터 처리
- 주문 검색 및 필터링 응답시간 < 1초 목표
- 동시 관리자 접속 시 안정성 필수

### 기술 인프라 (변경 불가)
- **MySQL RDS 유지** — 기존 AWS RDS 인스턴스 재사용 (비용 절감)
- MySQL 스키마 마이그레이션 최소화
- 데이터 마이그레이션 리스크 회피

### 개발 효율
- Django 기존 경험 활용
- 레거시 코드 호환성 고려
- 팀 내 기술 스택 숙련도 고려

---

## 사업 컨텍스트

- Shopify 스토어를 통한 도서 판매
- 안정적이고 빠른 주문 처리가 수익에 직결
- 관리자 UX 개선 = 운영 효율 증대
- 데이터 양이 많아질수록 성능 최적화의 ROI 증가

---

**최종 목표**: 관리자가 50만 건의 도서와 주문을 빠르고 안정적으로 관리할 수 있는 고성능 웹 애플리케이션 구축
