---
id: SPEC-ORDER-001
title: Shopify 주문 동기화 및 목록 조회
status: Approved
created: 2026-06-20
updated: 2026-06-20
author: ggajo
priority: High
issue_number: ~
---

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-20 | ggajo | 최초 작성 — Shopify 주문 동기화 및 목록 조회 SPEC 초안 |

---

## 문제 정의

현재 SCM v2는 도서 재고 및 상품 정보 관리 기능은 제공하지만, Shopify 스토어(Booksen, Etoile)에서 발생하는 주문 데이터를 내부 관리자 시스템에서 조회·관리하는 수단이 없다.

관리자는 주문 현황 파악을 위해 Shopify 어드민 화면을 직접 접속해야 하며, 두 스토어 간 통합 조회가 불가능하다. 이로 인해:

- 두 스토어의 주문을 단일 화면에서 비교·조회하지 못함
- 결제 상태 및 배송 상태 기반 필터링이 운영 도구 내에서 불가
- 주문 데이터가 SCM v2 DB에 없어 향후 재고 연동 자동화의 기반이 없음

---

## 솔루션 개요

신규 Django `order` 앱을 생성하여 다음을 구현한다:

1. **수동 동기화 API** — 관리자가 버튼을 클릭하면 두 Shopify 스토어의 `status=open` 주문 전체를 DB에 upsert한다.
2. **주문 목록 조회 API** — 저장된 주문을 페이지네이션·필터링하여 반환하는 REST API를 제공한다.
3. **프론트엔드 주문 목록 페이지** — `/orders` 경로에 주문 목록 테이블, 필터 바, 동기화 버튼을 제공한다.

Shopify API 버전 `2024-10`의 `GET /admin/api/2024-10/orders.json?status=open&limit=250`을 사용하며, 커서 페이지네이션(`page_info`)으로 250건 단위로 전체 주문을 수집한다.

기존 `book` 앱의 모델(`Inven`, `Info`, `EtoileBookInven`)과 DB 테이블은 변경하지 않는다.

---

## 요구사항

### 인증

**REQ-ORD-001** (Ubiquitous)
The 주문 관련 모든 API endpoint **shall** require JWT 인증(`JWTAuthentication + IsAuthenticated`)을 적용한다.

**REQ-ORD-002** (Unwanted Behavior)
**If** 요청에 유효한 JWT 토큰이 없거나 만료된 경우, **then** the API **shall** HTTP 401 Unauthorized를 반환하고 주문 데이터에 대한 접근을 거부한다.

---

### 동기화 API (POST /api/orders/sync/)

**REQ-ORD-010** (Event-Driven)
**When** 관리자가 `POST /api/orders/sync/`를 호출하면, the 시스템 **shall** Booksen 스토어와 Etoile 스토어 양쪽에서 `status=open`인 주문 전체를 수집하여 DB에 반영한다.

**REQ-ORD-011** (Ubiquitous)
The 시스템 **shall** Shopify API의 커서 페이지네이션(`page_info` 파라미터)을 사용하여 한 스토어당 250건 단위로 모든 open 주문을 순차적으로 수집한다.

**REQ-ORD-012** (Ubiquitous)
The 시스템 **shall** 수집한 주문 데이터를 `shopify_order_id` + `store_type` 복합 키 기준으로 upsert(존재하면 update, 없으면 insert)한다.

**REQ-ORD-013** (Ubiquitous)
The 동기화 **shall** 스토어별로 독립적으로 수행하며, 하나의 스토어 동기화가 실패해도 나머지 스토어의 동기화 결과는 DB에 커밋된다.

**REQ-ORD-014** (Unwanted Behavior)
**If** Shopify API 호출 중 오류(HTTP 4xx/5xx, 네트워크 타임아웃)가 발생하면, **then** the 시스템 **shall** 해당 스토어의 동기화를 중단하고 오류 내역을 응답의 `errors` 필드에 포함하여 반환한다.

**REQ-ORD-015** (Ubiquitous)
The 동기화 완료 응답 **shall** 각 스토어별 `synced_count`(새로 추가된 수), `updated_count`(갱신된 수), `error`(오류 메시지 또는 null) 정보를 포함한다.

**REQ-ORD-016** (Ubiquitous)
The 시스템 **shall** 기존 `backend/book/shopify_client.py`의 `_get(domain, token, path)` 함수를 재사용하여 Shopify API를 호출한다.

---

### 주문 데이터 저장

**REQ-ORD-020** (Ubiquitous)
The 시스템 **shall** 각 주문에 대해 `Order`, `Customer`, `ShippingAddress`, `BillingAddress`, `LineItem`, `ShippingLine` 모델에 관련 필드를 모두 저장한다.

**REQ-ORD-021** (Ubiquitous)
The `Order` 모델 **shall** 다음 필드를 포함한다: `shopify_order_id`, `order_number`, `name`, `email`, `phone`, `financial_status`, `fulfillment_status`, `status`, `created_at`, `updated_at`, `closed_at`, `cancelled_at`, `processed_at`, `total_price`, `subtotal_price`, `total_tax`, `total_discounts`, `total_shipping_price_set`, `currency`, `gateway`, `note`, `tags`, `cancel_reason`, `source_name`, `store_type`.

**REQ-ORD-022** (Ubiquitous)
The `Customer` 모델 **shall** 다음 필드를 포함한다: `shopify_customer_id`, `email`, `first_name`, `last_name`, `phone`.

**REQ-ORD-023** (Ubiquitous)
The `ShippingAddress` 및 `BillingAddress` 모델 **shall** 각각 `name`, `first_name`, `last_name`, `address1`, `address2`, `city`, `province`, `province_code`, `country`, `country_code`, `zip`, `phone` 필드를 포함한다.

**REQ-ORD-024** (Ubiquitous)
The `LineItem` 모델 **shall** 다음 필드를 포함한다: `shopify_line_item_id`, `product_id`, `variant_id`, `title`, `variant_title`, `sku`, `quantity`, `price`, `total_discount`, `fulfillment_status`, `vendor`, `grams`.

**REQ-ORD-025** (Ubiquitous)
The `ShippingLine` 모델 **shall** 다음 필드를 포함한다: `shopify_shipping_line_id`, `title`, `code`, `price`, `source`.

**REQ-ORD-026** (Ubiquitous)
The `store_type` 필드 **shall** `"booksen"` 또는 `"etoile"` 값만 허용하며, 어느 스토어에서 수집한 주문인지를 식별한다.

---

### 주문 목록 조회 API (GET /api/orders/)

**REQ-ORD-030** (Ubiquitous)
The `GET /api/orders/` API **shall** 주문 목록을 `created_at` 내림차순으로 정렬하여 페이지당 50건씩 반환한다.

**REQ-ORD-031** (Ubiquitous)
The API **shall** 다음 필터 파라미터를 지원한다: `store_type`(booksen/etoile), `financial_status`, `fulfillment_status`, `date_from`(ISO 8601), `date_to`(ISO 8601).

**REQ-ORD-032** (Ubiquitous)
The API 응답 **shall** `count`(전체 건수), `next`(다음 페이지 URL), `previous`(이전 페이지 URL), `results`(주문 목록 배열)를 포함하는 DRF 표준 페이지네이션 포맷을 따른다.

**REQ-ORD-033** (Unwanted Behavior)
**If** `date_from`이 `date_to`보다 늦은 날짜이면, **then** the API **shall** HTTP 400 Bad Request를 반환한다.

---

### 프론트엔드 — 주문 목록 페이지

**REQ-ORD-040** (Ubiquitous)
The 프론트엔드 **shall** `/orders` 경로에 주문 목록 페이지를 제공하며, 사이드바 네비게이션에 "주문관리" 항목을 추가한다.

**REQ-ORD-041** (Ubiquitous)
The 주문 목록 테이블 **shall** 다음 컬럼을 표시한다: 주문번호, 스토어, 고객명, 상품수, 결제금액, 결제상태, 배송상태, 주문일시.

**REQ-ORD-042** (Ubiquitous)
The 필터 바 **shall** 스토어 선택(전체/Booksen/Etoile), 결제상태, 배송상태, 날짜 범위(시작일~종료일) 필터를 제공한다.

**REQ-ORD-043** (Ubiquitous)
The 페이지 상단 **shall** 동기화 버튼을 제공하며, 클릭 시 `POST /api/orders/sync/`를 호출한다.

**REQ-ORD-044** (Event-Driven)
**When** 동기화 버튼을 클릭하면, the 버튼 **shall** 로딩 상태(스피너)로 전환되고 API 응답 수신 전까지 재클릭이 비활성화된다.

**REQ-ORD-045** (Event-Driven)
**When** 동기화 API가 성공적으로 완료되면, the 시스템 **shall** 동기화 결과(스토어별 추가/갱신 건수)를 토스트 메시지 또는 알림으로 표시하고 주문 목록을 자동으로 새로고침한다.

**REQ-ORD-046** (Unwanted Behavior)
**If** 동기화 API 호출 중 오류가 발생하면, **then** the 시스템 **shall** 오류 메시지를 사용자에게 표시하고 버튼을 다시 활성화 상태로 복원한다.

**REQ-ORD-047** (Ubiquitous)
The 주문 목록 **shall** 페이지네이션 컨트롤을 제공하며, 현재 페이지와 전체 페이지 수를 표시한다.

**REQ-ORD-048** (State-Driven)
**While** 주문 목록 데이터를 로딩 중인 경우, the 테이블 **shall** 로딩 스켈레톤 또는 스피너를 표시한다.

---

## DB 스키마 설계

### Order 모델

```python
class Order(models.Model):
    # Shopify 식별자
    shopify_order_id = models.BigIntegerField()
    store_type = models.CharField(max_length=20, choices=[("booksen", "Booksen"), ("etoile", "Etoile")])

    # 주문 기본 정보
    order_number = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)  # e.g. "#1001"
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    # 상태
    financial_status = models.CharField(max_length=50, null=True, blank=True)
    fulfillment_status = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)

    # 금액
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    subtotal_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_discounts = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_shipping_price_set = models.JSONField(null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)

    # 결제 정보
    gateway = models.CharField(max_length=100, null=True, blank=True)

    # 메타 정보
    note = models.TextField(null=True, blank=True)
    tags = models.TextField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=100, null=True, blank=True)
    source_name = models.CharField(max_length=100, null=True, blank=True)

    # 날짜
    shopify_created_at = models.DateTimeField(null=True, blank=True)
    shopify_updated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # 관계
    customer = models.ForeignKey("Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")

    # 시스템 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("shopify_order_id", "store_type")]
        indexes = [
            models.Index(fields=["store_type"]),
            models.Index(fields=["financial_status"]),
            models.Index(fields=["fulfillment_status"]),
            models.Index(fields=["shopify_created_at"]),
        ]
```

### Customer 모델

```python
class Customer(models.Model):
    shopify_customer_id = models.BigIntegerField(unique=True)
    email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### ShippingAddress 모델

```python
class ShippingAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="shipping_address")
    name = models.CharField(max_length=200, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    province_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    zip = models.CharField(max_length=30, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
```

### BillingAddress 모델

```python
class BillingAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="billing_address")
    name = models.CharField(max_length=200, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    province_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    zip = models.CharField(max_length=30, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
```

### LineItem 모델

```python
class LineItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="line_items")
    shopify_line_item_id = models.BigIntegerField()
    product_id = models.BigIntegerField(null=True, blank=True)
    variant_id = models.BigIntegerField(null=True, blank=True)
    title = models.CharField(max_length=500, null=True, blank=True)
    variant_title = models.CharField(max_length=255, null=True, blank=True)
    sku = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fulfillment_status = models.CharField(max_length=50, null=True, blank=True)
    vendor = models.CharField(max_length=255, null=True, blank=True)
    grams = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = [("order", "shopify_line_item_id")]
```

### ShippingLine 모델

```python
class ShippingLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipping_lines")
    shopify_shipping_line_id = models.BigIntegerField()
    title = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=100, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = [("order", "shopify_shipping_line_id")]
```

---

## API 명세

### POST /api/orders/sync/

**요청**

```
POST /api/orders/sync/
Authorization: Bearer <access_token>
Content-Type: application/json
```

요청 바디 없음.

**성공 응답 (HTTP 200)**

```json
{
  "status": "completed",
  "stores": {
    "booksen": {
      "synced_count": 12,
      "updated_count": 45,
      "error": null
    },
    "etoile": {
      "synced_count": 3,
      "updated_count": 8,
      "error": null
    }
  },
  "total_synced": 15,
  "total_updated": 53
}
```

**부분 오류 응답 (HTTP 200, 한 스토어 실패)**

```json
{
  "status": "partial",
  "stores": {
    "booksen": {
      "synced_count": 12,
      "updated_count": 45,
      "error": null
    },
    "etoile": {
      "synced_count": 0,
      "updated_count": 0,
      "error": "Shopify API 호출 실패: HTTP 401"
    }
  },
  "total_synced": 12,
  "total_updated": 45
}
```

**인증 오류 응답 (HTTP 401)**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

### GET /api/orders/

**요청**

```
GET /api/orders/?store_type=booksen&financial_status=paid&page=1
Authorization: Bearer <access_token>
```

**쿼리 파라미터**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `store_type` | string | 선택 | `booksen` 또는 `etoile` |
| `financial_status` | string | 선택 | `paid`, `pending`, `refunded`, `voided` 등 |
| `fulfillment_status` | string | 선택 | `fulfilled`, `partial`, `unfulfilled` 등 |
| `date_from` | string | 선택 | ISO 8601 날짜 (예: `2026-01-01`) — `shopify_created_at` 기준 |
| `date_to` | string | 선택 | ISO 8601 날짜 (예: `2026-06-30`) |
| `page` | integer | 선택 | 페이지 번호 (기본값: 1) |

**성공 응답 (HTTP 200)**

```json
{
  "count": 120,
  "next": "http://localhost:8000/api/orders/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "shopify_order_id": 5678901234567,
      "store_type": "booksen",
      "order_number": 1001,
      "name": "#1001",
      "financial_status": "paid",
      "fulfillment_status": "fulfilled",
      "total_price": "35000.00",
      "currency": "KRW",
      "shopify_created_at": "2026-06-15T10:30:00+09:00",
      "customer": {
        "shopify_customer_id": 9876543210,
        "first_name": "길동",
        "last_name": "홍",
        "email": "hong@example.com"
      },
      "line_items_count": 2
    }
  ]
}
```

---

## 제외 사항 (What NOT to Build)

- **자동 주기적 동기화**: 이 SPEC은 수동 동기화만 구현한다. Celery Beat 기반 자동 스케줄링은 별도 SPEC으로 처리한다.
- **주문 상세 페이지**: 이 SPEC은 목록 조회만 구현한다. 주문 상세 보기는 별도 SPEC으로 분리한다.
- **주문 상태 변경 API**: Shopify 주문 상태를 SCM에서 변경하는 기능은 이 SPEC의 범위가 아니다.
- **웹훅 기반 실시간 동기화**: Shopify 웹훅 수신 및 실시간 반영은 별도 SPEC으로 처리한다.
- **기존 book 앱 테이블 변경**: `Inven`, `Info`, `EtoileBookInven` 모델 및 마이그레이션은 건드리지 않는다.
- **주문 삭제 기능**: DB에 저장된 주문 데이터를 삭제하는 기능은 구현하지 않는다.
- **고객 상세 조회 API**: `Customer` 모델에 대한 별도 API endpoint는 제공하지 않는다.

---

## 인수 조건

### 동기화 API

- [ ] `POST /api/orders/sync/`에 유효한 JWT 없이 요청 시 HTTP 401 반환
- [ ] `POST /api/orders/sync/` 호출 시 Booksen의 모든 open 주문이 DB에 저장됨
- [ ] `POST /api/orders/sync/` 호출 시 Etoile의 모든 open 주문이 DB에 저장됨
- [ ] 이미 존재하는 주문(`shopify_order_id` + `store_type` 중복)은 삭제되지 않고 갱신됨
- [ ] 250건을 초과하는 스토어에서 커서 페이지네이션으로 전체 주문이 수집됨
- [ ] 응답에 스토어별 `synced_count`, `updated_count`, `error` 포함
- [ ] 한 스토어 실패 시에도 다른 스토어 결과는 커밋되고 응답에 반영됨

### 주문 목록 API

- [ ] `GET /api/orders/`가 `created_at` 내림차순으로 50건씩 반환함
- [ ] `store_type` 필터로 특정 스토어 주문만 조회 가능
- [ ] `financial_status` 필터가 정상 동작함
- [ ] `fulfillment_status` 필터가 정상 동작함
- [ ] `date_from`, `date_to` 필터가 `shopify_created_at` 기준으로 동작함
- [ ] `date_from`이 `date_to`보다 늦으면 HTTP 400 반환
- [ ] 응답에 `count`, `next`, `previous`, `results` 포함

### 데이터 완전성

- [ ] `Order`, `Customer`, `ShippingAddress`, `BillingAddress`, `LineItem`, `ShippingLine` 6개 모델이 마이그레이션으로 생성됨
- [ ] Shopify API 응답의 `customer`, `shipping_address`, `billing_address`, `line_items`, `shipping_lines` 중첩 데이터가 각 관련 테이블에 저장됨
- [ ] `store_type` 필드가 `"booksen"` 또는 `"etoile"` 값으로 올바르게 설정됨

### 프론트엔드

- [ ] `/orders` 경로 접속 시 주문 목록 페이지가 렌더링됨
- [ ] 사이드바 네비게이션에 "주문관리" 항목이 표시됨
- [ ] 테이블에 주문번호, 스토어, 고객명, 상품수, 결제금액, 결제상태, 배송상태, 주문일시 컬럼이 표시됨
- [ ] 동기화 버튼 클릭 시 로딩 스피너가 표시되고 버튼이 비활성화됨
- [ ] 동기화 성공 시 결과 알림(토스트)이 표시되고 목록이 자동 갱신됨
- [ ] 동기화 실패 시 오류 메시지가 표시되고 버튼이 재활성화됨
- [ ] 스토어, 결제상태, 배송상태, 날짜 범위 필터가 동작함
- [ ] 페이지네이션 컨트롤로 페이지 이동이 가능함
- [ ] 데이터 로딩 중 스켈레톤 또는 스피너가 표시됨
- [ ] JWT 미인증 상태에서 `/orders` 접근 시 로그인 페이지로 리디렉션됨
