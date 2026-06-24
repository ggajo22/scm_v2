---
id: SPEC-SHOPIFY-INFO-002
document: acceptance
version: 1.0.0
---

# SPEC-SHOPIFY-INFO-002: Acceptance Criteria

---

## Scenario 1: 두 스토어 모두 등록 — 가격 및 이미지 수 정상 반환

**Given** 특정 `inven_id`에 대해 Booksen(`Shopify_product`)과 Etoile(`EtoileShopifyProduct`) 레코드가 모두 존재하고,  
  Shopify API가 `product.variants[target].price = "25000.00"` 및 `product.images` 배열(2개)을 포함한 정상 응답을 반환하는 경우

**When** `GET /api/book/{inven_id}/shopify-live-info/` 를 JWT 인증 헤더와 함께 호출하면

**Then**
- HTTP 200 반환
- `booksen.price == "25000.00"` (또는 해당 variant의 price 문자열)
- `booksen.image_count` 는 응답에 포함됨 (값 유무 무관, 프론트에서 미표시)
- `etoile.price == "25000.00"` (또는 해당 variant의 price 문자열)
- `etoile.image_count == 2` (product.images 배열 길이)
- 기존 필드(`status`, `weight`, `weight_unit`, `error`)는 SPEC-SHOPIFY-INFO-001 동일하게 정상 반환

---

## Scenario 2: Booksen 미등록 도서 — price null

**Given** `Shopify_product` 레코드가 없어 Booksen이 미등록인 도서

**When** `GET /api/book/{inven_id}/shopify-live-info/` 호출 시

**Then**
- HTTP 200 반환
- `booksen.registered == false`
- `booksen.price == null`
- `booksen.image_count == null`
- Booksen Shopify API 미호출

---

## Scenario 3: Etoile 미등록 도서 — price 및 image_count null

**Given** `EtoileBookInven` 또는 `EtoileShopifyProduct` 레코드가 없어 Etoile이 미등록인 도서

**When** `GET /api/book/{inven_id}/shopify-live-info/` 호출 시

**Then**
- HTTP 200 반환
- `etoile.registered == false`
- `etoile.price == null`
- `etoile.image_count == null`
- Etoile Shopify API 미호출

---

## Scenario 4: Shopify API 오류 — price 및 image_count null

**Given** Etoile Shopify API 호출이 네트워크 오류 또는 5xx 응답을 반환하는 경우  
  (Booksen API는 정상)

**When** `GET /api/book/{inven_id}/shopify-live-info/` 호출 시

**Then**
- HTTP 200 반환 (전체 요청 실패 아님)
- `etoile.error` 가 non-null 문자열
- `etoile.price == null`
- `etoile.image_count == null`
- `booksen.price` 는 정상 값 반환
- `booksen.error == null`

---

## Scenario 5: 프론트엔드 — 두 스토어 가격 정상 표시

**Given** 두 스토어 모두 등록되고 API가 가격 및 이미지 수를 포함한 정상 응답을 반환하는 도서의 상세 페이지

**When** 사용자가 도서 상세 페이지(`/book/{id}`)에 접근하면

**Then**
- GIMSSINE 섹션에 가격이 무게 옆에 표시됨 (e.g., `25000.00` 또는 `25000`)
- ETOILE 섹션에 가격이 무게 옆에 표시됨
- ETOILE 섹션에 이미지 수가 표시됨 (e.g., `이미지 2개`)
- GIMSSINE 섹션에 이미지 수가 표시되지 않음 (REQ-SHPINFO2-008)

---

## Scenario 6: 프론트엔드 — price null 시 "-" 표시

**Given** Booksen이 미등록이거나 API 오류로 `booksen.price == null` 인 경우

**When** 사용자가 도서 상세 페이지에 접근하면

**Then**
- GIMSSINE 가격 필드에 "-" 또는 빈 표시
- GIMSSINE 섹션 전체가 크래시되지 않음
- ETOILE 섹션은 독립적으로 정상 렌더링

---

## Scenario 7: 프론트엔드 — image_count null 시 "-" 표시

**Given** Etoile이 미등록이거나 API 오류로 `etoile.image_count == null` 인 경우

**When** 사용자가 도서 상세 페이지에 접근하면

**Then**
- ETOILE 이미지 수 필드에 "-" 또는 빈 표시
- ETOILE 섹션 전체가 크래시되지 않음

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| `product.images` 배열이 빈 배열 (`[]`) | `image_count == 0` 반환; 프론트엔드에서 `0` 또는 `0개` 표시 |
| `product.variants`에 target variant 없음 | `price == null`, `error` 필드 설명 포함 |
| `price == "0.00"` | 유효한 값으로 처리 (`0.00` 표시) |
| `product.images` 키 자체가 응답에 없음 | `image_count == null` 반환, 예외 발생하지 않음 |
| `price` 문자열이 `"25000.00"` 형태 | 포맷팅 없이 그대로 표시 (`"25000.00"`) |
| Booksen API 정상, Etoile API 오류 | 각 스토어 독립적으로 처리; Booksen price 정상, Etoile price/image_count null |

---

## Definition of Done

- [ ] `_fetch_product_info()` 반환값에 `price` 필드 포함 (both stores)
- [ ] `_fetch_product_info()` 반환값에 `image_count` 필드 포함 (값은 두 스토어 모두 계산되나 표시는 ETOILE만)
- [ ] `GET /api/book/{inven_id}/shopify-live-info/` 응답에 `price`, `image_count` 포함 확인
- [ ] 추가 Shopify API 호출 없음 확인 (기존 products 엔드포인트 응답 재활용)
- [ ] 미등록 스토어의 `price == null`, `image_count == null` 확인
- [ ] API 오류 시 `price == null`, `image_count == null`, `error` 필드 설명 확인
- [ ] 프론트엔드 TypeScript 타입에 `price: string | null`, `image_count: number | null` 추가
- [ ] 프론트엔드 GIMSSINE 섹션에 가격 표시 확인
- [ ] 프론트엔드 ETOILE 섹션에 가격 표시 확인
- [ ] 프론트엔드 ETOILE 섹션에 이미지 수 표시 확인
- [ ] 프론트엔드 GIMSSINE 섹션에 이미지 수 미표시 확인
- [ ] `price == null` 시 프론트엔드 "-" 또는 빈 표시 확인
- [ ] `image_count == null` 시 프론트엔드 "-" 또는 빈 표시 확인
- [ ] 백엔드 테스트 (mock) 업데이트: 기존 `test_shopify_live_info.py`의 mock 응답에 `price`, `images` 필드 추가

---

## Quality Gate Criteria

- 백엔드: `ruff check` 통과
- 프론트엔드: `tsc --noEmit` 타입 오류 없음
- 백엔드: `_fetch_product_info()` 단위 테스트에서 `price`, `image_count` 추출 로직 검증
- API 응답 구조가 REQ-SHPINFO2-003 스키마와 일치 (두 스토어 모두 `price`, `image_count` 포함)
- GIMSSINE 섹션 UI에 `image_count` 관련 렌더링 코드 없음 (코드 리뷰로 확인)
