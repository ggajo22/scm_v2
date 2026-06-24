---
id: SPEC-SHOPIFY-INFO-002
document: plan
version: 1.0.0
---

# SPEC-SHOPIFY-INFO-002: Implementation Plan

## Overview

SPEC-SHOPIFY-INFO-001에서 구현된 `_fetch_product_info()`의 반환값을 최소한으로 확장하여 `price`와 `image_count`를 추가한다. 수정 범위는 4개 파일에 한정되며, 추가 API 호출이나 DB 변경은 없다.

---

## Technical Approach

### 데이터 플로우

```
Shopify Admin REST API
GET /products/{product_id}.json
        │
        ▼
  product 객체 수신 (기존 동일)
        │
        ├── product["status"]          → status (기존)
        ├── target["weight"]           → weight (기존)
        ├── target["weight_unit"]      → weight_unit (기존)
        ├── target["price"]            → price (신규)
        └── len(product["images"])     → image_count (신규)
        │
        ▼
_fetch_product_info() 반환값
{
  "status": ...,
  "weight": ...,
  "weight_unit": ...,
  "error": null,
  "price": "25000.00",      ← 추가
  "image_count": 2           ← 추가
}
        │
        ▼
ShopifyLiveInfoView 응답 조합
{
  "booksen": { ..., "price": "25000.00", "image_count": null },
  "etoile":  { ..., "price": "25000.00", "image_count": 2 }
}
        │
        ▼
Frontend ShopifyLiveInfoSection
├── GIMSSINE: status + weight + price 표시
│             image_count 미표시 (REQ-SHPINFO2-008)
└── ETOILE:   status + weight + price + image_count 표시
```

---

### Backend

#### 1. `backend/book/shopify_client.py` — `_fetch_product_info()` 확장

현재 반환 구조:
```python
return {
    "status": product.get("status"),
    "weight": target.get("weight") if target else None,
    "weight_unit": target.get("weight_unit") if target else None,
    "error": None,
}
```

변경 후:
```python
return {
    "status": product.get("status"),
    "weight": target.get("weight") if target else None,
    "weight_unit": target.get("weight_unit") if target else None,
    "price": target.get("price") if target else None,
    "image_count": len(product.get("images", [])),
    "error": None,
}
```

오류 발생 시 반환 구조도 동일하게 `price: null`, `image_count: null` 포함:
```python
return {
    "status": None, "weight": None, "weight_unit": None,
    "price": None, "image_count": None,
    "error": str(e),
}
```

#### 2. 응답 스키마 변경 (자동 반영)

`ShopifyLiveInfoView`는 `_fetch_product_info()`의 반환값을 그대로 직렬화하므로, 별도 View 수정 없이 응답에 자동 포함된다. 단, 응답 구조 주석 또는 docstring이 있다면 업데이트 필요.

---

### Frontend

#### 1. `frontend/src/types/book.ts` — `ShopifyStoreInfo` 타입 확장

현재:
```typescript
export interface ShopifyStoreInfo {
  registered: boolean
  product_id: string | null
  variant_id: string | null
  status: 'active' | 'draft' | 'archived' | null
  weight: number | null
  weight_unit: 'g' | 'kg' | 'lb' | 'oz' | null
  error: string | null
}
```

변경 후:
```typescript
export interface ShopifyStoreInfo {
  registered: boolean
  product_id: string | null
  variant_id: string | null
  status: 'active' | 'draft' | 'archived' | null
  weight: number | null
  weight_unit: 'g' | 'kg' | 'lb' | 'oz' | null
  price: string | null        // 추가
  image_count: number | null  // 추가
  error: string | null
}
```

#### 2. `frontend/src/pages/BookDetailPage.tsx` — `ShopifyLiveInfoSection` UI 업데이트

**GIMSSINE 스토어 렌더링 수정:**
- 기존 weight 표시 옆에 `price` 추가
- `price`가 null이면 "-" 표시
- `image_count`는 렌더링하지 않음

**ETOILE 스토어 렌더링 수정:**
- 기존 weight 표시 옆에 `price` 추가
- `price`가 null이면 "-" 표시
- `image_count` 표시 추가 (null이면 "-")

표시 예시:
```
GIMSSINE
  상태: [active]   무게: 500 g   가격: 25000.00

ETOILE
  상태: [active]   무게: 500 g   가격: 25000.00   이미지: 2개
```

---

### Test

#### `backend/book/tests/test_shopify_live_info.py` 업데이트

기존 mock 응답에 `price`와 `images` 필드 추가:

```python
# 기존 mock에 추가
mock_product = {
    "status": "active",
    "images": [{"id": 1}, {"id": 2}],  # 추가
    "variants": [
        {
            "id": "789",
            "weight": 500.0,
            "weight_unit": "g",
            "price": "25000.00",  # 추가
        }
    ],
}
```

신규 테스트 케이스:
- `price` 및 `image_count` 정상 추출 검증
- `product.images` 빈 배열 → `image_count == 0` 검증
- `product.images` 키 없음 → `image_count == 0` 또는 `null` 검증
- API 오류 시 `price == null`, `image_count == null` 검증

---

## Implementation Milestones

### Priority High

1. `backend/book/shopify_client.py` — `_fetch_product_info()` 반환값에 `price`, `image_count` 추가 (정상/오류 경로 모두)
2. `backend/book/tests/test_shopify_live_info.py` — mock 업데이트 및 신규 검증 추가
3. API 응답 수동 확인 (`curl` 또는 DRF Browsable API)

### Priority Medium

4. `frontend/src/types/book.ts` — `ShopifyStoreInfo` 타입 확장
5. `frontend/src/pages/BookDetailPage.tsx` — GIMSSINE 가격 표시 추가
6. `frontend/src/pages/BookDetailPage.tsx` — ETOILE 가격 및 이미지 수 표시 추가

### Priority Low

7. TypeScript 타입 검사 (`tsc --noEmit`) 통과 확인
8. 각 null 케이스 브라우저 UI 확인

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `product.images` 키가 일부 상품에서 누락 | Low | Low | `product.get("images", [])` 로 기본값 처리 |
| `target["price"]` 가 소수점 포함 문자열 (`"25000.00"`) | None | None | 포맷팅 없이 그대로 반환; 요구사항상 raw 문자열 허용 |
| 기존 테스트 mock에 `price`/`images` 누락으로 테스트 실패 | Medium | Low | 테스트 파일 mock 동시 업데이트 (Priority High에 포함) |
| 프론트엔드 타입 변경으로 기존 컴포넌트 타입 오류 | Low | Low | `price?`, `image_count?` optional 또는 null 유니온으로 안전하게 처리 |

---

## Files to Modify

### Modify (수정) — 4개 파일

- `backend/book/shopify_client.py` — `_fetch_product_info()` 반환 딕셔너리에 `price`, `image_count` 추가
- `frontend/src/types/book.ts` — `ShopifyStoreInfo` 인터페이스에 두 필드 추가
- `frontend/src/pages/BookDetailPage.tsx` — `ShopifyLiveInfoSection` UI 업데이트
- `backend/book/tests/test_shopify_live_info.py` — mock 및 assertion 업데이트

### Create (신규) — 없음

이 SPEC은 기존 파일 수정만으로 구현 완료된다. 신규 파일 생성은 불필요하다.
