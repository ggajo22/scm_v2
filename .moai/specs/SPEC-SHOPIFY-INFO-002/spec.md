---
id: SPEC-SHOPIFY-INFO-002
version: 1.0.0
status: Completed
created: 2026-06-20
updated: 2026-06-20
completed: 2026-06-20
author: ggajo
priority: Medium
issue_number: ~
---

# SPEC-SHOPIFY-INFO-002: Shopify 가격 및 이미지 수 표시

## HISTORY

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0.0 | 2026-06-20 | ggajo | Initial SPEC creation — extends SPEC-SHOPIFY-INFO-001 |

---

## Overview

SPEC-SHOPIFY-INFO-001에서 구현된 Shopify 연동 정보 표시 기능을 확장하여, GIMSSINE(Booksen)과 ETOILE 두 스토어 모두에 **가격(price)** 을 표시하고, ETOILE 스토어에는 **Shopify 상품 이미지 수(image_count)** 를 추가로 표시한다.

기술적으로, Shopify Admin REST API의 `GET /products/{product_id}.json` 응답에는 이미 `product.variants[].price` 와 `product.images` 배열이 포함되어 있다. SPEC-SHOPIFY-INFO-001의 `_fetch_product_info()`가 동일한 엔드포인트를 이미 호출하므로, **추가 API 호출 없이** 기존 응답에서 해당 필드를 추출하는 것으로 구현한다.

---

## Scope

**In Scope:**
- 백엔드: `_fetch_product_info()` 반환값에 `price`와 `image_count` 필드 추가
- 백엔드: `GET /api/book/{inven_id}/shopify-live-info/` 응답 스키마에 두 필드 포함
- 프론트엔드: `ShopifyStoreInfo` 타입에 `price` 및 `image_count` 필드 추가
- 프론트엔드: 두 스토어 UI에 가격 표시
- 프론트엔드: ETOILE UI에만 이미지 수 표시

**Out of Scope (미포함 항목):**
- GIMSSINE(Booksen) 이미지 수 표시 (REQ-SHPINFO2-008)
- 가격의 통화 기호 또는 천 단위 구분 포맷팅 (내부 관리 도구이므로 불필요)
- Shopify 추가 API 호출 — 이미 수신된 응답 데이터를 재활용
- DB에 가격이나 이미지 수를 저장하거나 캐싱하는 기능
- 가격 또는 이미지 수를 기준으로 검색/필터링하는 기능

---

## Context & Assumptions

### 선행 SPEC

이 SPEC은 **SPEC-SHOPIFY-INFO-001**의 확장이다. 아래 요소가 이미 구현되어 있다고 가정한다:

- `GET /api/book/{pk}/shopify-live-info/` 엔드포인트 존재
- `backend/book/shopify_client.py` — `_fetch_product_info(product_id, variant_id, ...)` 함수 존재
- `_fetch_product_info()`는 `GET /products/{product_id}.json`을 호출하며, `product` 객체 전체를 수신함
- 프론트엔드 `ShopifyStoreInfo` 타입 및 `ShopifyLiveInfoSection` UI 컴포넌트 존재

### Shopify API 응답 구조 (기존 호출)

`GET https://{domain}/admin/api/2024-01/products/{product_id}.json` 응답:

```json
{
  "product": {
    "id": 123456,
    "status": "active",
    "images": [
      { "id": 1, "src": "..." },
      { "id": 2, "src": "..." }
    ],
    "variants": [
      {
        "id": 789,
        "weight": 500.0,
        "weight_unit": "g",
        "price": "25000.00"
      }
    ]
  }
}
```

- `price`: 매칭된 `variant`(target)의 `price` 필드 (문자열, e.g., `"25000.00"`)
- `image_count`: `len(product["images"])` — 상품에 등록된 이미지 전체 수

### image_count 데이터 소스 결정

`EtoileInfo.preview_urls` (DB)와 Shopify `product.images` (실시간 API) 두 가지 소스가 존재한다.
이 SPEC은 **Shopify API의 `product.images`** 를 사용한다. 이유:
- 이미 수신한 API 응답에서 추출하므로 추가 비용 없음
- 실시간 정확도 보장 (DB 동기화 지연 없음)
- "Shopify 연동 정보" 섹션의 목적과 일치

---

## EARS Requirements

### REQ-SHPINFO2-001 (Ubiquitous — 백엔드 price 반환)

The system **shall** extract `price` from the matched variant (`product.variants[target_index].price`) in the Shopify API response and include it in the `_fetch_product_info()` return value for both Booksen and Etoile stores.

### REQ-SHPINFO2-002 (Ubiquitous — 백엔드 image_count 반환)

The system **shall** compute `image_count` as `len(product["images"])` from the Shopify API response and include it in the `_fetch_product_info()` return value for the Etoile store.

### REQ-SHPINFO2-003 (Ubiquitous — 응답 스키마 확장)

The system **shall** include `price` (string or null) and `image_count` (integer or null) in the `shopify-live-info` endpoint response for both `booksen` and `etoile` objects.

### REQ-SHPINFO2-004 (Event-Driven — 프론트엔드 가격 표시)

**When** the `shopify-live-info` API response is received, the frontend **shall** display `price` next to the weight field for both GIMSSINE and ETOILE store sections.

### REQ-SHPINFO2-005 (Event-Driven — 프론트엔드 이미지 수 표시)

**When** the `shopify-live-info` API response is received, the frontend **shall** display `image_count` in the ETOILE store section only.

### REQ-SHPINFO2-006 (State-Driven — price null 처리)

**While** `price` is null (store not registered or API error), the frontend **shall** display "-" or nothing in place of the price value.

### REQ-SHPINFO2-007 (State-Driven — image_count null 처리)

**While** `image_count` is null (ETOILE not registered or API error), the frontend **shall** display "-" or nothing in place of the image count value.

### REQ-SHPINFO2-008 (Unwanted — GIMSSINE 이미지 수 표시 금지)

The system **shall not** display `image_count` in the GIMSSINE (Booksen) store section, even if the `image_count` value is present in the API response.

### REQ-SHPINFO2-009 (Ubiquitous — 가격 포맷)

The system **shall** display `price` as a plain numeric string (e.g., `"25000"` or `"25000.00"`) without currency symbol or thousand-separator formatting.

### REQ-SHPINFO2-010 (Unwanted — 추가 API 호출 금지)

The system **shall not** make additional Shopify API calls to retrieve `price` or `image_count`; both values **shall** be extracted from the existing `GET /products/{product_id}.json` response already fetched in `_fetch_product_info()`.

---

## Exclusions (What NOT to Build)

1. **GIMSSINE 이미지 수 표시 없음**: `booksen.image_count` 필드는 응답에 포함될 수 있으나, 프론트엔드에서 절대 렌더링하지 않는다.
2. **가격 포맷팅 없음**: 통화 기호(`₩`), 천 단위 구분자(`,`), 소수점 처리 등 포맷팅 로직을 추가하지 않는다. 내부 관리 도구이므로 raw 문자열 표시로 충분하다.
3. **캐싱 없음**: 가격 또는 이미지 수를 DB나 Redis에 저장하지 않는다.
4. **DB 저장 없음**: 신규 모델 필드 또는 마이그레이션을 생성하지 않는다.
5. **편집 기능 없음**: 가격 또는 이미지 수를 수정하는 UI나 API를 추가하지 않는다.

---

## Non-Functional Requirements

- 성능: `_fetch_product_info()`에 추가 연산(필드 추출)만 수행하므로 응답 시간 변화 없음
- 보안: 가격 정보는 이미 인증된 엔드포인트를 통해서만 반환되며, JWT 인증 요건은 SPEC-SHOPIFY-INFO-001과 동일
- 타입 안전성: 프론트엔드 TypeScript 타입 변경 시 `tsc --noEmit` 통과 필수
