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
- **렉번호 요약 탭** — `/rack-number` 페이지 2번째 탁 추가
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

### 10. 출고 처리 — 한국 창고 → 미국 창고 이동 (SPEC-ORDER-015 — 완료)
- **신규 LineItem 필드** — `shipped_quantity` (누적 출고 수량, 기본값 0) + `shipped_at` (최근 출고 처리 일시, nullable)
- **주문-SKU 기반 매칭** — Order.name 정확 일치 → (order, sku) 조합 기반 LineItem 매칭
  - 복수 LineItem 매칭 시 "매칭 실패" 안전 스킵 (분배 로직 불필요 — 설계 결정 A)
  - null quantity는 0으로 간주해 모든 양수 입력에서 "수량초과" 판정 (설계 결정 B)
  - 동일 요청 내 중복 행은 수량 합산 후 1회 판정 (설계 결정 C)
- **백엔드 엔드포인트** — 2개 (JSON 수동 입력 `/api/purchase-orders/line-items/outbound-process/` + Excel 업로드 `/api/purchase-orders/upload-outbound/`)
  - 3개 컬럼 자동 인식 (Name/Lineitem sku/Total, 대소문자 무시 substring 매칭)
  - 3분류 결과 응답 (성공/매칭 실패/수량초과)
  - 모든 행을 단일 atomic transaction으로 처리
- **상태 전이** — `shipped_quantity >= quantity` 시 자동으로 `logistics_status = "shipped"` 전이
- **신규 프론트엔드 페이지** — `/outbound` (독립 페이지, `/rack-number`와 분리)
  - 수동 텍스트/테이블 입력 폼 + Excel 파일 업로드 UI
  - 3분류 결과 시각화 + "다시 처리하기" 리셋 버튼
- **사이드바 메뉴** — "출고 처리" 항목 추가
- **기존 기능 무변경** — book.Info.qty / order.WarehouseStock / LineItem.fulfillment_status / order.order_number 유지
- **미국창고 완료 신호** — confirmed_distributor가 warehouse_ca/warehouse_nj인 품목에 대해 total=0을 "이미 완료됨" 신호로 해석해 shipped_quantity를 quantity까지 채우고 logistics_status를 shipped로 자동 전이 (기존 임계값 로직 재사용, 신규 enum 없음). 파싱 실패 0과 진짜 0 구분, 음수 거부, max() 갱신으로 불감소 보장.
- **성능 최적화** — Order.name 인덱스 추가로 테이블 스캔 제거 (EXPLAIN: 3094행 검사 → 1행 검사), 배치 쿼리로 N+1 제거 (쿼리 수 3N → 3 고정, 50행 처리 시 ~19.5초 → ~0.4초)
- 테스트 커버리지: 백엔드 124개 pytest(기존 91 + 신규 33), 프론트엔드 79개 vitest, 회귀 테스트 769개(754+15) 통과

### 11. 강제 출고 처리 — SKU 불일치 행의 대상 지정 출고 반영 (SPEC-ORDER-016 — 완료)
- **해결하는 문제** — SPEC-ORDER-015의 출고 처리에서 `(order, sku)` 매칭에 실패한 행(`line_item_not_found`)은 반영할 방법이 없었다. 담당자가 실물을 보고 어느 품목인지 알고 있어도 화면에서 처리할 수 없었다.
- **대상 지정 방식** — 자동 추론을 하지 않는다. 담당자가 매칭 실패 행마다 반영할 LineItem을 후보 목록에서 직접 고른다 (빈 SKU 자동 반영 · 순차 분배 · 단일 후보 자동 선택 모두 미구현)
- **자격 조건** — 매칭 실패 사유가 `line_item_not_found`이고 요청 수량이 양수인 행만 강제 대상. 그 밖의 행에는 선택 컨트롤 자체가 렌더되지 않는다
- **백엔드 엔드포인트** — 2개 신설
  - 후보 배치 조회 `/api/purchase-orders/line-items/outbound-force-candidates/` — 주문 식별자 집합을 1요청으로 조회, 동명 주문은 최저 `pk` 선점, 취소 품목·SKU 없는 품목 제외, 잔여 용량 없음 표시
  - 강제 반영 `/api/purchase-orders/line-items/outbound-force-process/` — 기존 3분류 응답 계약을 필드까지 그대로 반환해 기존 렌더링 경로가 수정 없이 소비
- **정상 경로와의 편차는 정확히 2가지** — `(order, sku)` 매칭 단계를 사용자 지정 대상으로 대체, 그리고 0 수량 미국창고 완료 신호를 승계하지 않음. 수량 한도·불감소·음수 거부·임계 전이·원자성은 동일하게 적용
- **입력 게이트** — 구조 오류 · 대상 미지정 · 존재하지 않는 대상 · 주문 미해석 · 타 주문 소속 대상 · 취소된 대상 · SKU 없는 대상 중 하나라도 있으면 요청 전체를 HTTP 400으로 거부(부분 반영 없음). 교차 주문 쓰기 차단
- **합산 규칙** — 음수 · 0 · 판독불가 행을 그룹화 이전에 제거한 뒤 대상 식별자 기준으로 합산해 대상당 1회 판정. 살아남은 행이 없는 대상은 그룹을 만들지 않아 `shipped_at` 각인이나 `0 >= 0` 완료 전이가 발생하지 않는다
- **동시성 안전** — 한도 판정 직전 대상 LineItem을 `select_for_update()`로 잠그고 잠금 이후 값으로 판정. 동시 강제 요청 2건이 같은 낡은 값으로 각자 한도를 통과하는 경로 차단. 정상 출고 경로는 무변경(락 미도입)
- **쓰기 범위** — 대상 LineItem의 `shipped_quantity` / `shipped_at` / `logistics_status` 3개 필드뿐. LineItem 생성·삭제 없음, Order 필드 무변경, 주문 집계 재계산 미호출(정상 경로 동작 답습)
- **신규 컬럼·마이그레이션·감사 로그 테이블 없음**
- **프론트엔드** — 매칭 실패 섹션 전용 컴포넌트 신설(성공·수량초과 섹션은 기존 컴포넌트 유지), 후보 피커, 일괄 실행 1요청, 물류 상태·매칭 실패 사유 코드값의 한국어 라벨링(SKU·도서명은 원본 유지)
- **결과 병합** — 실행 성공 시 제출한 행만 매칭 실패 목록에서 제거하고 미제출 행은 선택 가능 상태로 유지, 성공·수량초과 항목을 각 목록에 추가한 뒤 건수 재계산. 페이지 리로드 없이 이어서 처리 가능
- 테스트 커버리지: 백엔드 37개 pytest 신규(36 + 동시성 1), 프론트엔드 전체 221개 vitest 통과, SPEC-ORDER-015 기존 124개 무수정 통과

### 12. 보류/제외 품목 복구 — 발주 중단 상태의 품목을 재발주 대상으로 되돌림 (SPEC-ORDER-018 — 완료)
- **해결하는 문제** — 4개 제외 상태(`on_hold`, `order_cancelled`, `cs_required`, `other_publisher`)의 LineItem은 모든 발주 화면에서 사라져 복구할 방법이 없음. 담당자가 실물을 보고 재주문을 결정해도 DB 직접 수정 외에는 방법이 없었다.
- **조회 경로** — 신규 읽기 전용 엔드포인트 `GET /api/purchase-orders/excluded-items/` 추가 (선례: `OutboundForceCandidateView`)
  - 4개 제외 상태의 LineItem을 별도 목록으로 노출
  - 공유 필터 `_reorder_candidate_filter`를 넓히지 않아 Daily Review 업로드의 SKU 배치 매칭에 제외 품목이 재진입하지 않음
  - 환불 차감 적용 (전액 환불만 제외, 미환불 null/0 수량은 유지)
  - 결정성 정렬 (`-order__shopify_created_at`, `pk` tie-break)
- **복구 경로** — 신규 엔드포인트 없음, 기존 상태 변경 엔드포인트 재사용
  - 행별 상태 select (`LineItemStatusUpdateView`)
  - 일괄 상태 변경 (`LineItemBulkStatusUpdateView`)
  - 모두 `unordered` 상태 변경 지원
- **프론트엔드** — 미발주 탭 내 뷰 전환 컨트롤 추가
  - Tab 내 토글: "미발주 목록" ↔ "보류/제외 품목"
  - 제외 뷰에만 상태 라벨 열 표시
  - LineItem id 기반 로컬 선택 (전역 SKU 배열과 분리)
  - 일괄 복구 컨트롤
  - 발주 파일 생성 버튼은 제외 뷰에서 미표시
- **무효화 양방향** — 상태 변경 시 "미발주" / "보류/제외" 쿼리 모두 무효화해 두 뷰의 동기성 유지
- **신규 컬럼·마이그레이션·감사 로그 없음**
- 테스트 커버리지: 백엔드 12개 pytest, 프론트엔드 7개 vitest(훅 통합 3 + 컴포넌트 4), 회귀 테스트 979개 통과

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
