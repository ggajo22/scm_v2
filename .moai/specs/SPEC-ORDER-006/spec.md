---
id: SPEC-ORDER-006
version: "1.0.0"
status: draft
created: 2026-06-22
updated: 2026-06-22
author: ggajo
priority: Medium
issue_number: ~
---

# 주문 위치(Location) 정보 저장 및 표시

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-22 | ggajo | 최초 작성 — 주문 위치 정보 저장 및 목록 표시 SPEC 초안 |

---

## 문제 정의

현재 `Order` 모델과 동기화 로직(`shopify_orders.py`)은 Shopify 주문 데이터에 포함된 `location_id` 필드를 수집하지 않는다. 그 결과:

- 물리 매장(POS)에서 발생한 주문과 온라인 웹 주문을 DB에서 구별할 수 없다
- 어느 창고/지역(CA, KR, NJ 등) 재고에서 처리된 주문인지 운영 화면에서 파악하기 어렵다
- 주문 목록 페이지(`/orders`)에 위치 정보 컬럼이 없어 관리자가 Shopify 어드민을 별도 조회해야 한다

Shopify Locations API를 통해 확인된 위치 정보는 다음과 같다:

| 스토어 | Location ID | Location Name | 추출 코드 |
|--------|-------------|---------------|-----------|
| GIMSSINE | 85951578417 | GIMSSINE_CA | CA |
| GIMSSINE | 111320793393 | GIMSSINE_KR | KR |
| GIMSSINE | 101550260529 | GIMSSINE_NJ | NJ |
| GIMSSINE | 98735030577 | GIMSSINE (비활성) | (없음) |
| ETOILE | 76370411705 | ETOILE_CA | CA |
| ETOILE | 79188459705 | ETOILE_NJ | NJ |

웹 주문은 `location_id: null`로 반환되며, 이 경우 위치 코드는 빈 문자열(`""`)로 저장한다.

---

## 솔루션 개요

1. `Order` 모델에 `location` 필드(`CharField(max_length=10, blank=True, default="")`)를 추가하고 Django 마이그레이션을 생성한다.
2. `shopify_orders.py`에 `_fetch_locations(domain, token)` 헬퍼를 추가한다. 이 함수는 `GET /admin/api/2024-10/locations.json`을 호출하여 `{location_id(int): code(str)}` 딕셔너리를 반환한다. 코드 추출 규칙: `name.rsplit("_", 1)[-1]` (단, `_`가 없으면 `""`).
3. `sync_store()`와 `sync_single_order_from_shopify()`에서 동기화 전 위치 정보를 한 번 조회(`_fetch_locations`)하여 `_sync_single_order()`에 `location_map` 인자로 전달한다.
4. `_sync_single_order(order_data, store_type, location_map=None)` 시그니처를 확장하여 `order_data.get("location_id")`를 조회하고 `location_map.get(location_id, "")`으로 `Order.location`을 설정한다.
5. `OrderListSerializer` 필드 목록에 `location`을 추가한다.
6. 프론트엔드 `OrderListItem` 타입에 `location?: string`을 추가하고, 주문 목록 테이블에 Location 컬럼을 추가한다.

---

## 요구사항 (EARS 형식)

### 모델 및 마이그레이션

**REQ-LOC-001** (Ubiquitous)
The `Order` 모델 **shall** `location` 필드(`CharField(max_length=10, blank=True, default="")`)를 가진다.

**REQ-LOC-002** (Ubiquitous)
The 시스템 **shall** `REQ-LOC-001`에 따른 스키마 변경을 적용하는 Django 마이그레이션 파일을 포함한다.

---

### 위치 정보 조회 헬퍼

**REQ-LOC-003** (Ubiquitous)
The `shopify_orders.py` 모듈 **shall** `_fetch_locations(domain, token)` 함수를 포함한다. 이 함수는 기존 `_get_with_headers(domain, token, "locations.json")`를 호출하여 `GET /admin/api/2024-10/locations.json`의 결과를 처리한다.

**REQ-LOC-004** (Event-Driven)
**When** `_fetch_locations(domain, token)`이 실행되면, the 시스템 **shall** 응답 JSON의 `locations` 리스트를 순회하여 다음 규칙으로 딕셔너리 `{location_id: code}`를 반환한다:
- `location_id` 키: Shopify `location.id` (정수형)
- `code` 값: `location["name"].rsplit("_", 1)[-1]` — 단, `"_"`가 `location["name"]`에 없으면 `""`

**REQ-LOC-005** (Unwanted Behavior)
**If** `_fetch_locations()` 호출 중 예외(네트워크 오류, HTTP 오류 등)가 발생하면, **then** the 시스템 **shall** 빈 딕셔너리 `{}`를 반환하고 예외를 전파하지 않는다. 이 경우 동기화는 `location=""`으로 계속 진행된다.

---

### 전체 동기화 (`sync_store`)

**REQ-LOC-006** (Event-Driven)
**When** `sync_store(store_type)`이 실행되면, the 시스템 **shall** 주문 수집 루프를 시작하기 전에 `_fetch_locations(domain, token)`을 정확히 한 번 호출하여 `location_map`을 구성한다.

**REQ-LOC-007** (Event-Driven)
**When** `sync_store()`가 각 주문에 대해 `_sync_single_order()`를 호출할 때, the 시스템 **shall** REQ-LOC-006에서 구성한 `location_map`을 `_sync_single_order(order_data, store_type, location_map=location_map)`으로 전달한다.

---

### 개별 재동기화 (`sync_single_order_from_shopify`)

**REQ-LOC-008** (Event-Driven)
**When** `sync_single_order_from_shopify(shopify_order_id, store_type)`이 실행되면, the 시스템 **shall** `_sync_single_order()` 호출 전에 `_fetch_locations(domain, token)`을 호출하여 `location_map`을 구성하고 이를 전달한다.

---

### 단일 주문 동기화 (`_sync_single_order`)

**REQ-LOC-009** (Ubiquitous)
The `_sync_single_order(order_data, store_type, location_map=None)` 함수 **shall** 다음 규칙으로 `Order.location`을 설정한다:
- `location_id = order_data.get("location_id")` — `None`이면 웹 주문
- `location = location_map.get(location_id, "") if location_map and location_id else ""`

**REQ-LOC-010** (Ubiquitous)
The `_sync_single_order()` 함수 **shall** 기존 `_sync_single_order(order_data, store_type)` 형태의 호출과 하위 호환성을 유지한다. `location_map` 인자가 없거나 `None`인 경우 `location=""`으로 설정한다.

---

### 직렬화 (Serializer)

**REQ-LOC-011** (Ubiquitous)
The `OrderListSerializer` **shall** `fields` 목록에 `"location"`을 포함하여 주문 목록 API 응답에 `location` 필드를 노출한다.

---

### 프론트엔드 타입

**REQ-LOC-012** (Ubiquitous)
The `frontend/src/types/order.ts`의 `OrderListItem` 인터페이스 **shall** `location?: string` 필드를 포함한다.

---

### 프론트엔드 UI

**REQ-LOC-013** (Ubiquitous)
The 주문 목록 테이블(`frontend/src/pages/OrdersPage.tsx`) **shall** "Location" 컬럼을 포함한다. 셀 값은 `order.location`이며, 빈 문자열인 경우 `"-"`를 표시한다.

**REQ-LOC-014** (Ubiquitous)
The Location 컬럼 **shall** 주문 번호 컬럼과 스토어 컬럼 사이 또는 스토어 컬럼 오른쪽에 배치된다. 정확한 위치는 구현 에이전트가 기존 컬럼 순서를 기반으로 결정한다.

---

## 제외 사항 (What NOT to Build)

- **위치 정보 기반 필터링 UI**: 이번 SPEC은 위치 정보를 저장하고 표시하는 것에 집중한다. 위치 코드로 주문 목록을 필터링하는 기능은 포함하지 않는다.
- **위치 정보 자동 갱신(웹훅)**: Shopify 위치 변경 웹훅 수신 및 자동 갱신 기능은 포함하지 않는다.
- **위치 정보 캐싱**: `_fetch_locations()` 결과를 Redis 등에 캐시하는 기능은 포함하지 않는다.
- **비활성 위치 처리 특수 로직**: `GIMSSINE (비활성)` 등 `_` 없는 위치 이름은 `""` 반환 규칙으로 처리하며 별도 표기나 상태 관리는 하지 않는다.
- **주문 상세 페이지 위치 표시**: 이번 SPEC은 목록 페이지에만 위치 컬럼을 추가한다. 주문 상세 페이지(`OrderDetailPage.tsx`) 변경은 포함하지 않는다.
- **Locations API 호출 실패 시 동기화 중단**: `_fetch_locations()` 오류 시 동기화를 중단하지 않는다 (REQ-LOC-005).

---

## 기술적 접근

### 의존성

- **SPEC-ORDER-001**: 기본 `Order` 모델 및 `shopify_orders.py` 구조 기반
- **SPEC-ORDER-004**: `_sync_single_order()` 함수 시그니처 (현재 `(order_data, store_type)`)

### 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/order/models.py` | 수정 | `Order` 모델에 `location = models.CharField(max_length=10, blank=True, default="")` 추가 |
| `backend/order/migrations/000X_add_order_location.py` | 신규 | `location` 필드 추가 마이그레이션 |
| `backend/order/shopify_orders.py` | 수정 | `_fetch_locations()` 헬퍼 추가, `_sync_single_order()` 시그니처 확장, `sync_store()` 및 `sync_single_order_from_shopify()` 업데이트 |
| `backend/order/serializers.py` | 수정 | `OrderListSerializer.fields`에 `"location"` 추가 |
| `frontend/src/types/order.ts` | 수정 | `OrderListItem`에 `location?: string` 추가 |
| `frontend/src/pages/OrdersPage.tsx` | 수정 | 주문 목록 테이블에 Location 컬럼 추가 |

### 핵심 구현 규칙

1. `_get_with_headers(domain, token, "locations.json")`는 이미 존재하는 헬퍼이다. `_fetch_locations()`는 이를 재사용해야 한다.
2. `_fetch_locations()`는 위치 조회 실패 시 `{}`를 반환하고 예외를 삼킨다(REQ-LOC-005). 로그는 기록해야 한다.
3. `sync_store()`에서 `_fetch_locations()` 호출은 루프 **밖**에서 한 번만 실행한다. 루프 안에서 반복 호출하지 않는다.
4. `_sync_single_order()` 함수 시그니처 변경 시 기존 호출부(현재 `sync_store`, `sync_single_order_from_shopify`)가 모두 업데이트되어야 한다.
5. 마이그레이션 파일 번호는 현재 `backend/order/migrations/` 디렉토리의 최대 번호 +1로 결정한다.
