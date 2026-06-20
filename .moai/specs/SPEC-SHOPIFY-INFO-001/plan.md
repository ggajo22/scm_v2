---
id: SPEC-SHOPIFY-INFO-001
document: plan
version: 1.0.0
---

# SPEC-SHOPIFY-INFO-001: Implementation Plan

## Overview

Backend에 Shopify Admin REST API를 호출하는 신규 엔드포인트를 추가하고, Frontend 도서 상세 페이지에 "Shopify 연동 정보" 섹션을 추가한다.

---

## Technical Approach

### Backend

#### 1. Shopify API 클라이언트 모듈

`backend/book/shopify_client.py` (신규 파일)

- `fetch_product_status(domain, token, product_id) -> dict | None`
  - `GET https://{domain}/admin/api/2024-01/products/{product_id}.json`
  - 반환: `{"status": "active" | "draft" | "archived"}` 또는 오류 시 `{"error": "..."}`
- `fetch_variant_weight(domain, token, variant_id) -> dict | None`
  - `GET https://{domain}/admin/api/2024-01/variants/{variant_id}.json`
  - 반환: `{"weight": float, "weight_unit": str}` 또는 오류 시 `{"error": "..."}`
- `fetch_shopify_live_info(domain, token, product_id, variant_id) -> dict`
  - 두 API 결과를 병합하여 단일 스토어 결과 반환
  - `asyncio` 또는 `concurrent.futures.ThreadPoolExecutor`로 두 API 병렬 호출

#### 2. 신규 View

`backend/book/views.py` 에 `ShopifyLiveInfoView` 추가

```python
GET /api/book/{pk}/shopify-live-info/
```

- `pk` → `Inven` 조회
- Booksen: `Shopify_product.objects.filter(inven=inven).first()`
- Etoile: `inven.etoile_inven.shopify_product.first()` (DoesNotExist 처리)
- Booksen, Etoile API 호출을 `ThreadPoolExecutor`로 병렬 실행 (REQ-SHPINFO-014)
- 결과 조합 후 REQ-SHPINFO-008 구조로 Response 반환

#### 3. URL 등록

`backend/book/urls.py` 에 추가:

```python
path("book/<int:pk>/shopify-live-info/", ShopifyLiveInfoView.as_view(), name="book-shopify-live-info"),
```

#### 4. 환경 변수 접근

`django.conf.settings`에서 읽기:

```python
settings.SHOPIFY_BOOKSEN_TOKEN
settings.SHOPIFY_BOOKSEN_DOMAIN
settings.SHOPIFY_ETOILE_TOKEN
settings.SHOPIFY_ETOILE_DOMAIN
```

`backend/config/settings.py` (또는 `base.py`)에서 `os.environ.get()` 로 로드.

---

### Frontend

#### 1. API 훅

`frontend/src/features/book/hooks/useShopifyLiveInfo.ts` (신규)

```typescript
export function useShopifyLiveInfo(id: number | undefined) {
  return useQuery<ShopifyLiveInfoResponse>({
    queryKey: ['book', 'shopify-live-info', id],
    queryFn: async () => {
      const res = await api.get(`/api/book/${id}/shopify-live-info/`)
      return res.data
    },
    enabled: id !== undefined,
  })
}
```

#### 2. 타입 정의

`frontend/src/types/book.ts` 에 추가:

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

export interface ShopifyLiveInfoResponse {
  booksen: ShopifyStoreInfo
  etoile: ShopifyStoreInfo
}
```

#### 3. UI 컴포넌트

`frontend/src/pages/BookDetailPage.tsx` 에 `ShopifyLiveInfoSection` 컴포넌트 추가

- `useShopifyLiveInfo(id)` 호출
- 로딩 중: 스켈레톤 카드
- 두 스토어 각각에 대해:
  - 스토어 이름 배지
  - 상품 상태 배지 (색상 구분)
  - 무게 + 단위 텍스트
  - API 오류 메시지 (오류 시)
  - "미등록" 표시 (`registered: false` 시)

---

## Implementation Milestones

### Priority High

1. `shopify_client.py` — Shopify API 클라이언트 구현 및 오류 처리
2. `ShopifyLiveInfoView` — 백엔드 뷰 구현 (병렬 호출 포함)
3. URL 등록 및 수동 테스트

### Priority Medium

4. Frontend 타입 정의 (`ShopifyLiveInfoResponse`)
5. `useShopifyLiveInfo` 훅 구현
6. `ShopifyLiveInfoSection` UI 컴포넌트 구현 (상태 배지 색상 포함)
7. `BookDetailPage.tsx` 에 섹션 통합

### Priority Low

8. 환경 변수 미설정 시 fallback 메시지 처리
9. 단위 테스트 작성 (shopify_client 오류 시나리오 mocking)

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Shopify API rate limit (40 req/min) | Low | Medium | 에러 응답 캐치 후 `error` 필드로 반환. 필요 시 429 재시도 로직 추가 |
| 환경 변수 미설정 | Medium | High | `settings.py`에서 누락 시 명확한 오류 메시지 출력; view에서 검증 |
| Shopify API 스펙 변경 (2024-01) | Low | Medium | API 버전 상수화하여 일괄 교체 용이하게 구성 |
| 양 스토어 API 동시 타임아웃 | Low | Low | 각 API 호출에 timeout 설정 (e.g., 5초); 개별 오류 필드로 반환 |

---

## Files to Modify / Create

### Create (신규)
- `backend/book/shopify_client.py`
- `frontend/src/features/book/hooks/useShopifyLiveInfo.ts`

### Modify (수정)
- `backend/book/views.py` — `ShopifyLiveInfoView` 추가
- `backend/book/urls.py` — URL 패턴 추가
- `frontend/src/pages/BookDetailPage.tsx` — `ShopifyLiveInfoSection` 추가
- `frontend/src/types/book.ts` — 신규 타입 추가
- `backend/config/settings.py` (또는 동등한 설정 파일) — 환경 변수 로드
