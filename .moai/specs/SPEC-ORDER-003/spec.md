---
id: SPEC-ORDER-003
version: "1.0.0"
status: Implemented
created: 2026-06-21
updated: 2026-06-21
author: ggajo
priority: High
issue_number: ~
---

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-21 | ggajo | 최초 작성 — 주문 상세 페이지 SPEC 초안 |

---

## 문제 정의

`SPEC-ORDER-001`에서 구현된 주문 목록 페이지(`/orders`)는 주문의 요약 정보(주문번호, 상태, 금액, 고객명)만 표시하며, **개별 주문의 상세 내역(주문 상품, 배송 정보, 결제 내역, 환불 내역)을 확인하는 수단이 없다**.

관리자가 특정 주문의 구체적인 내용을 확인하려면 Shopify 어드민으로 이탈해야 하며, 이는 다음과 같은 운영 비효율을 초래한다:

- 고객 문의(어떤 상품을 주문했는지, 배송지가 어디인지) 대응 시 SCM 시스템 이탈 필요
- 주문 상품 목록 및 ISBN 확인을 위해 별도 시스템 조회 필요
- 환불 내역 확인 시 Shopify 어드민 접근 필요
- 결제 방법 및 금액 내역 파악 불가

---

## 솔루션 개요

백엔드에 `GET /api/orders/{id}/` 상세 조회 엔드포인트를 추가하고, 프론트엔드에 `/orders/:id` 라우트와 `OrderDetailPage` 컴포넌트를 구현한다.

주문 목록의 각 행을 클릭하면 해당 주문의 상세 페이지로 이동하며, 상세 페이지에서는 다음 정보를 섹션별로 표시한다:

- **주문 정보**: 주문번호, 생성일시, 결제수단, 메모
- **상품 목록**: LineItem별 도서명, SKU(ISBN), 수량, 단가, 할인, 소계
- **결제 정보**: 소계, 할인, 배송비, 세금, 총계
- **배송 정보**: 수령인, 주소, 연락처
- **고객 정보**: 고객명, 이메일, 연락처
- **환불 내역**: 환불이 있는 경우에만 표시

---

## 요구사항 (EARS 형식)

### 백엔드 — OrderDetailSerializer

**REQ-OD-001** (Ubiquitous)
The 시스템 **shall** `OrderDetailSerializer`를 생성하며, 다음 필드를 포함한다:
- 기본 Order 필드 전체: `id`, `shopify_order_id`, `store_type`, `order_number`, `name`, `email`, `phone`, `financial_status`, `fulfillment_status`, `total_price`, `subtotal_price`, `total_tax`, `total_discounts`, `total_shipping_price_set`, `currency`, `gateway`, `note`, `tags`, `cancel_reason`, `source_name`, `shopify_created_at`, `shopify_updated_at`, `closed_at`, `cancelled_at`, `processed_at`, `has_refund`
- 중첩 `customer` (전체 필드: `shopify_customer_id`, `first_name`, `last_name`, `email`, `phone`)
- 중첩 `shipping_address` (전체 필드: `name`, `first_name`, `last_name`, `address1`, `address2`, `city`, `province`, `province_code`, `country`, `country_code`, `zip`, `phone`)
- 중첩 `line_items` (목록: `id`, `shopify_line_item_id`, `title`, `variant_title`, `sku`, `quantity`, `price`, `total_discount`, `fulfillment_status`, `vendor`, `grams`)
- 중첩 `shipping_lines` (목록: `title`, `code`, `price`, `source`)
- 중첩 `refunds` (목록: `shopify_refund_id`, `note`, `shopify_created_at`, `line_item_id`, `quantity`, `subtotal`, `total_tax`)

---

### 백엔드 — 상세 조회 엔드포인트

**REQ-OD-002** (Ubiquitous)
The 시스템 **shall** `GET /api/orders/{id}/` 엔드포인트를 `RetrieveAPIView`로 구현하며, 인증된 사용자에게만 허용한다(`IsAuthenticated`).

**REQ-OD-003** (Event-Driven)
**When** `GET /api/orders/{id}/`가 유효한 ID와 함께 호출되면, the 시스템 **shall** HTTP 200과 함께 `OrderDetailSerializer`로 직렬화된 주문 상세 데이터를 반환한다.

**REQ-OD-004** (Event-Driven)
**When** `GET /api/orders/{id}/`에서 해당 ID의 주문이 존재하지 않으면, the 시스템 **shall** HTTP 404를 반환한다.

**REQ-OD-005** (Ubiquitous)
The 시스템 **shall** `backend/order/urls.py`에 `orders/<int:pk>/` 패턴을 등록하여 상세 조회 엔드포인트에 접근할 수 있도록 한다.

---

### 프론트엔드 — TypeScript 타입

**REQ-OD-010** (Ubiquitous)
The 시스템 **shall** 다음 TypeScript 인터페이스를 정의한다:
- `LineItemDetail`: `id`, `shopify_line_item_id`, `title`, `variant_title`, `sku`, `quantity`, `price`, `total_discount`, `fulfillment_status`, `vendor`, `grams` 필드 포함
- `ShippingAddress`: `name`, `first_name`, `last_name`, `address1`, `address2`, `city`, `province`, `province_code`, `country`, `country_code`, `zip`, `phone` 필드 포함
- `ShippingLine`: `title`, `code`, `price`, `source` 필드 포함
- `Refund`: `shopify_refund_id`, `note`, `shopify_created_at`, `line_item_id`, `quantity`, `subtotal`, `total_tax` 필드 포함
- `OrderDetail`: 기존 `Order` 인터페이스를 확장하며 `customer` (전체 필드), `shipping_address`, `line_items: LineItemDetail[]`, `shipping_lines: ShippingLine[]`, `refunds: Refund[]`, `subtotal_price`, `total_tax`, `total_discounts`, `total_shipping_price_set`, `gateway`, `note`, `tags`, `cancel_reason`, `source_name` 추가

---

### 프론트엔드 — useOrderDetail 훅

**REQ-OD-011** (Ubiquitous)
The 시스템 **shall** `useOrderDetail(id: number)` 훅을 구현하며, `GET /api/orders/{id}/`를 호출하여 `OrderDetail` 데이터를 반환한다. 훅은 `useOrders` 훅과 동일한 패턴(TanStack Query v5)을 따른다.

---

### 프론트엔드 — 라우팅

**REQ-OD-012** (Ubiquitous)
The 시스템 **shall** TanStack Router에 `/orders/$id` 라우트를 추가하며, `OrderDetailPage` 컴포넌트를 lazy-load 방식으로 연결한다.

**REQ-OD-013** (Event-Driven)
**When** 사용자가 주문 목록(`/orders`) 페이지의 주문 행을 클릭하면, the 시스템 **shall** `/orders/{id}` 경로로 네비게이션한다. 주문 행에는 pointer 커서가 적용된다.

---

### 프론트엔드 — OrderDetailPage 레이아웃

**REQ-OD-014** (Ubiquitous)
The `OrderDetailPage` **shall** 다음 헤더를 포함한다:
- 주문명(`name`, 예: "#1234") 타이틀
- 스토어 구분 레이블 (`gimssine` / `etoile`)
- "← 주문 목록" 뒤로가기 버튼 (클릭 시 `/orders`로 이동)
- `financial_status`, `fulfillment_status` 상태 배지

**REQ-OD-015** (Ubiquitous)
The `OrderDetailPage` **shall** 다음 6개 섹션을 순서대로 표시한다:
- **섹션 1 — 주문 정보**: `order_number`, `shopify_created_at` (날짜 포맷), `gateway` (결제수단), `note` (메모, 값이 있는 경우만 표시)
- **섹션 2 — 상품 목록**: `line_items` 테이블 (컬럼: 도서명, SKU, 수량, 단가, 할인, 소계)
- **섹션 3 — 결제 정보**: `subtotal_price`, `total_discounts`, 배송비(`shipping_lines`의 합계), `total_tax`, `total_price` (강조 표시)
- **섹션 4 — 배송 정보**: `shipping_address`의 수령인명, `address1`, `address2`, `city`, `province`, `zip`, `phone`
- **섹션 5 — 고객 정보**: 고객 성명(`first_name` + `last_name`), `email`, `phone`
- **섹션 6 — 환불 내역**: `has_refund`가 `true`인 경우에만 렌더링하며, `refunds` 목록의 `note`, `shopify_created_at`, `subtotal`, `total_tax` 표시

---

### 프론트엔드 — 로딩 및 오류 처리

**REQ-OD-016** (State-Driven)
**While** 상세 데이터를 API에서 조회 중인 경우, the 시스템 **shall** 스켈레톤 로딩 UI를 표시한다.

**REQ-OD-017** (Event-Driven)
**If** API 호출이 네트워크 오류 또는 서버 오류(5xx)로 실패한 경우, **then** the 시스템 **shall** 에러 메시지와 "다시 시도" 버튼을 표시한다.

**REQ-OD-018** (Event-Driven)
**If** API가 HTTP 404를 반환한 경우, **then** the 시스템 **shall** "주문을 찾을 수 없습니다" 메시지와 "주문 목록으로 돌아가기" 링크를 표시한다.

---

## 제외 사항 (What NOT to Build)

- **주문 수정 및 상태 변경 기능**: 주문은 Shopify에서 관리되므로 SCM 시스템에서는 읽기 전용이다.
- **환불 처리 UI**: 환불 생성 및 처리는 Shopify 어드민에서 수행하며, 이 SPEC은 환불 내역 표시만 포함한다.
- **LineItem에서 발주서(PO) 연결 링크**: `line_items.purchase_orders` M2M 관계는 별도 발주 관리 모듈(SPEC-PURCHASE-ORDER-001)에서 처리한다.
- **청구 주소(Billing Address) 섹션**: 한국 SCM 운영 환경에서는 배송 주소와 청구 주소가 동일한 경우가 대부분이므로 청구 주소는 표시하지 않는다.
- **인쇄 및 내보내기 기능**: 주문 상세 PDF 출력, Excel 내보내기 등은 이 SPEC의 범위가 아니다.
- **주문 메모 수정**: 메모(`note`)는 읽기 전용으로 표시하며, 편집 기능은 포함하지 않는다.
- **실시간 상태 갱신(WebSocket)**: 주문 상태 변경 시 자동 갱신 기능은 포함하지 않는다. 수동 새로고침으로 충분하다.

---

## 기술적 접근 방식

### 백엔드

- `backend/order/serializers.py`에 `OrderDetailSerializer` 추가
- 중첩 Serializer는 기존 `CustomerSerializer` 패턴을 참조하여 `ShippingAddressSerializer`, `LineItemSerializer`, `ShippingLineSerializer`, `RefundSerializer` 구현
- `backend/order/views.py`에 `OrderDetailView(generics.RetrieveAPIView)` 추가
- `backend/order/urls.py`에 `path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail')` 등록
- 새 DB 마이그레이션 불필요 (모델 변경 없음)

### 프론트엔드

- 타입 정의: 기존 `src/types/order.ts` (또는 동등한 위치)에 새 인터페이스 추가
- 훅: `src/hooks/useOrderDetail.ts` 생성, `useOrders` 훅 패턴 준수
- 라우트: TanStack Router 파일 기반 라우팅에 `src/routes/orders/$id.tsx` 추가 (또는 동등한 라우트 등록 방식)
- 컴포넌트: `src/pages/OrderDetailPage.tsx` 생성
- 스타일: Tailwind CSS 유틸리티 클래스 사용, 기존 페이지 스타일 일관성 유지

---

## 의존성 (Dependencies)

- **SPEC-ORDER-001** (주문관리 백엔드/프론트엔드 구현) — 전제 조건. `Order` 모델, `OrderListSerializer`, `OrderListView`, 주문 목록 페이지(`/orders`)가 이미 구현되어 있어야 한다.
- **SPEC-ORDER-002** (주문 검색) — 동일 주문 목록 페이지를 공유하므로 UI 변경 시 충돌 주의. 클릭 이벤트 추가는 기존 행 렌더링 코드에 최소한의 변경만 필요하다.
