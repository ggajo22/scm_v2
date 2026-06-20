---
id: SPEC-SHOPIFY-INFO-001
version: 1.0.0
status: Completed
created: 2026-06-20
updated: 2026-06-20
author: ggajo
priority: Medium
issue_number: ~
---

# SPEC-SHOPIFY-INFO-001: Shopify 상품 연동 정보 표시

## HISTORY

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0.0 | 2026-06-20 | ggajo | Initial SPEC creation |

---

## Overview

도서 상세 페이지에서 각 Shopify 스토어(Booksen, Etoile)의 상품 상태(Active / Draft / Archived)와 배송 무게를 실시간으로 조회하여 표시한다.

현재 DB에는 상품 상태와 무게 필드가 없으므로, 페이지 로드 시 백엔드가 Shopify Admin REST API를 호출하여 해당 정보를 반환한다.

---

## Scope

**In Scope:**
- 백엔드: 신규 엔드포인트 `GET /api/book/{inven_id}/shopify-live-info/` 구현
- 백엔드: Shopify Admin REST API 호출 (product status, variant weight)
- 프론트엔드: 도서 상세 페이지에 "Shopify 연동 정보" 섹션 추가
- 두 스토어(Booksen, Etoile) 모두 지원
- 스토어 미등록, 네트워크 오류 등 예외 상황 처리

**Out of Scope (미포함 항목):**
- DB에 status / weight 필드를 저장하거나 캐싱하는 기능
- Shopify 정보를 편집하거나 동기화하는 기능
- Shopify 웹훅을 통한 push 수신
- Booksen / Etoile 이외의 추가 스토어 확장 (현 SPEC 범위 외)
- Shopify 연동 정보를 검색 또는 필터링에 사용하는 기능

---

## Context & Assumptions

### 환경 변수 (사전 설정 필요)

| 변수명 | 설명 |
|--------|------|
| `SHOPIFY_BOOKSEN_TOKEN` | Booksen Admin API Access Token |
| `SHOPIFY_BOOKSEN_DOMAIN` | Booksen 스토어 도메인 (e.g., `booksen.myshopify.com`) |
| `SHOPIFY_ETOILE_TOKEN` | Etoile Admin API Access Token |
| `SHOPIFY_ETOILE_DOMAIN` | Etoile 스토어 도메인 |

### DB 관계

- Booksen: `Inven` → `Shopify_product` (FK, 1:N 구조이나 실질적으로 1:1)
- Etoile: `Inven` → `EtoileBookInven` (OneToOne) → `EtoileShopifyProduct` (FK)

### Shopify API 엔드포인트

- 상품 상태: `GET https://{domain}/admin/api/2024-01/products/{product_id}.json`
  - 반환 필드: `product.status` (`active` | `draft` | `archived`)
- 무게: `GET https://{domain}/admin/api/2024-01/variants/{variant_id}.json`
  - 반환 필드: `variant.weight`, `variant.weight_unit`

---

## EARS Requirements

### REQ-SHPINFO-001 (Ubiquitous)

The system **shall** provide a dedicated endpoint `GET /api/book/{inven_id}/shopify-live-info/` that returns real-time Shopify product information for both Booksen and Etoile stores.

### REQ-SHPINFO-002 (Event-Driven)

**When** the endpoint is called for a given `inven_id`, the system **shall** look up the associated `Shopify_product` record for Booksen and call the Shopify Admin API to retrieve `product.status` and `variant.weight` / `variant.weight_unit`.

### REQ-SHPINFO-003 (Event-Driven)

**When** the endpoint is called for a given `inven_id`, the system **shall** look up the associated `EtoileShopifyProduct` record (via `EtoileBookInven`) for Etoile and call the Shopify Admin API to retrieve `product.status` and `variant.weight` / `variant.weight_unit`.

### REQ-SHPINFO-004 (State-Driven — 스토어 미등록)

**While** a book has no `Shopify_product` record for Booksen, the system **shall** return `null` for all Booksen Shopify fields without calling the Shopify API.

### REQ-SHPINFO-005 (State-Driven — 스토어 미등록)

**While** a book has no `EtoileBookInven` or no `EtoileShopifyProduct` record for Etoile, the system **shall** return `null` for all Etoile Shopify fields without calling the Shopify API.

### REQ-SHPINFO-006 (Unwanted Behavior — API 오류)

**If** the Shopify Admin API call fails (network error, HTTP 4xx/5xx), **then** the system **shall** return `{"status": null, "weight": null, "weight_unit": null, "error": "<reason>"}` for the affected store and **shall not** raise an unhandled exception.

### REQ-SHPINFO-007 (Unwanted Behavior — 인증)

**If** the request does not include a valid JWT token, **then** the system **shall** return HTTP 401 and **shall not** call the Shopify API.

### REQ-SHPINFO-008 (Ubiquitous — 응답 구조)

The system **shall** return the following JSON structure for the endpoint:

```json
{
  "booksen": {
    "registered": true,
    "product_id": "string | null",
    "variant_id": "string | null",
    "status": "active | draft | archived | null",
    "weight": "number | null",
    "weight_unit": "g | kg | lb | oz | null",
    "error": "string | null"
  },
  "etoile": {
    "registered": true,
    "product_id": "string | null",
    "variant_id": "string | null",
    "status": "active | draft | archived | null",
    "weight": "number | null",
    "weight_unit": "g | kg | lb | oz | null",
    "error": "string | null"
  }
}
```

`registered: false`인 경우 나머지 필드는 모두 `null`.

### REQ-SHPINFO-009 (Event-Driven — 프론트엔드)

**When** the book detail page loads, the frontend **shall** call `GET /api/book/{inven_id}/shopify-live-info/` and display the returned information in a "Shopify 연동 정보" section.

### REQ-SHPINFO-010 (State-Driven — 로딩)

**While** the Shopify live info API call is in progress, the system **shall** display a skeleton loading indicator in the "Shopify 연동 정보" section.

### REQ-SHPINFO-011 (State-Driven — 상태 배지)

**While** displaying Shopify product status, the system **shall** render status badges with the following color coding:
- `active` → 녹색 (green)
- `draft` → 황색 (yellow/amber)
- `archived` → 회색 (gray)
- `null` / 미등록 → 회색 (gray), 텍스트 "미등록"

### REQ-SHPINFO-012 (Unwanted Behavior — 프론트엔드 오류)

**If** the `shopify-live-info` API call returns an error field for a store, **then** the frontend **shall** display an error message for that store and **shall not** crash the entire page.

### REQ-SHPINFO-013 (Ubiquitous — 무게 단위 표시)

The system **shall** display weight with its unit (e.g., `500 g`, `1.2 kg`) when `weight` and `weight_unit` are non-null.

### REQ-SHPINFO-014 (Ubiquitous — 병렬 API 호출)

The system **shall** call Booksen and Etoile Shopify APIs concurrently (not sequentially) to minimize response latency.

---

## Exclusions (What NOT to Build)

1. DB 스키마 변경 없음: `Shopify_product` 및 `EtoileShopifyProduct` 모델에 `status`, `weight`, `weight_unit` 필드를 추가하지 않는다.
2. 캐싱 없음: Redis, Django 캐시 프레임워크 등 서버 사이드 캐싱을 구현하지 않는다.
3. 편집 기능 없음: 이 SPEC은 읽기 전용 표시만 다루며, Shopify 데이터를 수정하는 기능은 포함하지 않는다.
4. 웹훅 없음: Shopify 웹훅을 통한 실시간 push 수신 구현은 포함하지 않는다.

---

## Non-Functional Requirements

- 응답 시간: 두 스토어 API 병렬 호출 기준 P95 < 3초 (Shopify API 응답 속도에 의존)
- 보안: Shopify API 토큰은 환경 변수로만 관리하며, 응답 payload에 노출하지 않는다.
- 인증: JWT 인증 필수 (기존 패턴 동일)
