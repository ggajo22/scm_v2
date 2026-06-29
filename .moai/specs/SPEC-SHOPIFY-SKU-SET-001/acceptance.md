# SPEC-SHOPIFY-SKU-SET-001 수락 기준 (Acceptance Criteria)

---

## REQ-SKU-SET-001: ShopifySkuSetMapping 모델

### AC-001-1: 모델 생성 및 마이그레이션

**Given** Django `order` 앱에 `ShopifySkuSetMapping` 모델이 정의되어 있을 때  
**When** `python manage.py makemigrations` 및 `migrate`를 실행하면  
**Then** `order_shopify_sku_set_mapping` 테이블이 MySQL에 생성되어야 한다

검증 항목:
- [ ] 테이블명: `order_shopify_sku_set_mapping`
- [ ] 컬럼: `id`, `bundle_sku`, `member_isbn`, `sort_order`, `created_at`, `updated_at`
- [ ] `bundle_sku` 단일 인덱스 존재
- [ ] `(bundle_sku, member_isbn)` unique_together 제약 존재

### AC-001-2: 중복 저장 방지

**Given** `bundle_sku="GITANMATH-F SET"`, `member_isbn="9788926025451"` 행이 이미 존재할 때  
**When** 동일한 `(bundle_sku, member_isbn)` 조합으로 저장 시도하면  
**Then** `IntegrityError`(또는 DRF ValidationError)가 발생하여 저장되지 않아야 한다

### AC-001-3: 정렬 순서

**Given** 동일 `bundle_sku`에 `sort_order` 0, 1, 2 순으로 3개 ISBN이 저장되어 있을 때  
**When** `ShopifySkuSetMapping.objects.filter(bundle_sku=...).all()`을 조회하면  
**Then** `sort_order` 오름차순으로 반환되어야 한다

---

## REQ-SKU-SET-002: 번들 매핑 관리 REST API

### AC-002-1: 전체 목록 조회

**Given** 번들 SKU 2종이 각각 3개, 2개 ISBN으로 등록되어 있고, 첫 번째 번들의 ISBN 중 일부는 `Inven`에 존재하고 일부는 없는 상태일 때  
**When** `GET /api/shopify-sku-sets/`를 JWT 인증과 함께 호출하면  
**Then** HTTP 200과 함께 2개의 번들 객체를 반환한다  
그리고 각 번들 객체는 `bundle_sku`, `member_isbns` 배열을 포함한다  
그리고 `member_isbns` 배열은 `sort_order` 오름차순으로 정렬된다  
그리고 각 ISBN 항목은 `isbn`, `sort_order`, `book_title` 필드를 포함한다  
그리고 `Inven`에 존재하는 ISBN의 `book_title`은 `Info.name` 값이고, 존재하지 않는 ISBN의 `book_title`은 `null`이다  
그리고 전체 조회 시 추가 N+1 쿼리 없이 단일 쿼리로 제목을 함께 조회한다

### AC-002-2: 번들 신규 생성

**Given** `"TEST-SET"`이 아직 등록되지 않은 상태에서  
**When** `POST /api/shopify-sku-sets/`에 `{"bundle_sku": "TEST-SET", "member_isbns": ["1111111111", "2222222222"]}`를 전송하면  
**Then** HTTP 201과 함께 생성된 번들 정보를 반환한다  
그리고 `ShopifySkuSetMapping` 테이블에 2개 행이 삽입된다

### AC-002-3: 번들 신규 생성 — 유효성 실패

**Given** 인증된 사용자가  
**When** `POST /api/shopify-sku-sets/`에 `{"bundle_sku": "", "member_isbns": ["111"]}`를 전송하면  
**Then** HTTP 400을 반환한다

**When** `POST /api/shopify-sku-sets/`에 `{"bundle_sku": "A-SET", "member_isbns": []}`를 전송하면  
**Then** HTTP 400을 반환한다

### AC-002-4: 특정 번들 조회

**Given** `"GITANMATH-F SET"` 번들이 5개 ISBN으로 등록되어 있을 때  
**When** `GET /api/shopify-sku-sets/GITANMATH-F SET/`를 호출하면  
**Then** HTTP 200과 함께 해당 번들의 `bundle_sku`와 5개 `member_isbns` 배열을 반환한다

**When** `GET /api/shopify-sku-sets/NONEXISTENT-SET/`를 호출하면  
**Then** HTTP 404를 반환한다

### AC-002-5: 번들 구성 ISBN 교체 (PUT)

**Given** `"A-SET"`이 ISBN 3개로 등록되어 있을 때  
**When** `PUT /api/shopify-sku-sets/A-SET/`에 `{"member_isbns": ["NEWISBN1", "NEWISBN2"]}`를 전송하면  
**Then** HTTP 200을 반환한다  
그리고 기존 3개 행은 모두 삭제되고 새 2개 행으로 교체된다  
그리고 교체는 하나의 트랜잭션 내에서 원자적으로 처리된다

### AC-002-6: 번들 삭제

**Given** `"B-SET"` 번들이 존재할 때  
**When** `DELETE /api/shopify-sku-sets/B-SET/`를 호출하면  
**Then** HTTP 204를 반환한다  
그리고 `ShopifySkuSetMapping` 테이블에서 해당 `bundle_sku` 행이 모두 삭제된다

### AC-002-7: 미인증 접근 거부

**Given** JWT 토큰 없이  
**When** `/api/shopify-sku-sets/` 어느 엔드포인트에 요청하면  
**Then** HTTP 401을 반환한다

---

## REQ-SKU-SET-003: 발주 생성 시 세트 SKU 전개

### AC-003-1: 세트 SKU 전개 — 정상 동작

**Given** `"GITANMATH-F SET"` → 5개 ISBN 매핑이 등록되어 있고  
그리고 `LineItem`에 `sku="GITANMATH-F SET"`, `quantity=2`인 미발주 항목이 존재할 때  
**When** `GET /api/purchase-orders/unordered/`를 호출하면  
**Then** 응답의 `results` 배열에 `"GITANMATH-F SET"` 원본 행 대신 5개의 전개 행이 포함된다  
그리고 각 전개 행의 `quantity`는 `2`이다  
그리고 각 전개 행의 `is_bundle_member`는 `true`이다  
그리고 각 전개 행의 `bundle_sku`는 `"GITANMATH-F SET"`이다  
그리고 각 전개 행의 `sku`는 각 `member_isbn` 값이다

### AC-003-2: 매핑 미존재 시 기존 동작 유지

**Given** `"REGULAR-SKU-001"` SKU에 대한 번들 매핑이 등록되어 있지 않고  
그리고 해당 SKU의 `LineItem`이 존재할 때  
**When** `GET /api/purchase-orders/unordered/`를 호출하면  
**Then** 해당 항목은 `sku="REGULAR-SKU-001"`로 전개 없이 그대로 반환된다  
그리고 `is_bundle_member` 필드는 `false`이거나 존재하지 않는다

### AC-003-3: 복수 세트 SKU 혼합 시

**Given** `LineItem` 3개가 있고, 1개는 세트 SKU(3개 ISBN), 2개는 일반 SKU일 때  
**When** `GET /api/purchase-orders/unordered/`를 호출하면  
**Then** `results`에 일반 2개 + 전개된 3개 = 총 5개 행이 반환된다

### AC-003-4: 추가 쿼리 최소화

**Given** 미발주 `LineItem`이 N개 있을 때  
**When** `GET /api/purchase-orders/unordered/`를 호출하면  
**Then** `ShopifySkuSetMapping` 전체 조회 쿼리가 정확히 1번 실행된다 (N+1 쿼리 없음)

---

## REQ-SKU-SET-004: 프론트엔드 설정 페이지

### AC-004-1: 페이지 접근

**Given** 인증된 관리자가  
**When** `/settings/sku-sets` 경로에 접근하면  
**Then** 번들 매핑 목록 페이지가 렌더링된다

### AC-004-2: 목록 표시

**Given** 번들 매핑이 2종 등록된 상태에서 페이지를 로드하면  
**When** 페이지가 마운트될 때  
**Then** `GET /api/shopify-sku-sets/`가 호출된다  
그리고 테이블에 2개 행이 표시된다  
그리고 각 행에는 `bundle_sku`, 구성 ISBN 목록, 편집/삭제 버튼이 표시된다

### AC-004-3: 번들 추가

**Given** 사용자가 bundle_sku와 ISBN 목록을 입력 폼에 입력하고 저장 버튼을 클릭하면  
**When** `POST /api/shopify-sku-sets/`가 성공하면  
**Then** 목록이 자동 갱신되어 새 번들 행이 표시된다  
그리고 입력 폼이 초기화된다

### AC-004-4: 번들 삭제 확인

**Given** 사용자가 특정 번들의 삭제 버튼을 클릭하면  
**When** 확인 다이얼로그에서 삭제를 승인하면  
**Then** `DELETE /api/shopify-sku-sets/{bundle_sku}/`가 호출된다  
그리고 목록에서 해당 번들이 제거된다

### AC-004-5: API 오류 표시

**Given** API 호출이 실패하면 (네트워크 오류 또는 HTTP 4xx/5xx)  
**When** 오류 응답을 받으면  
**Then** 사용자에게 오류 메시지가 화면에 표시된다

---

## 품질 게이트 (Quality Gate)

### Definition of Done

- [ ] `ShopifySkuSetMapping` 모델 마이그레이션 파일 생성 완료
- [ ] API 엔드포인트 5종 모두 구현 및 JWT 인증 적용
- [ ] `UnorderedItemsView` 세트 전개 로직 구현 및 기존 동작 회귀 없음
- [ ] 프론트엔드 `/settings/sku-sets` 페이지 구현 완료
- [ ] 백엔드 단위 테스트 커버리지 85% 이상 (pytest)
- [ ] 프론트엔드 컴포넌트 테스트 작성 (React Testing Library)
- [ ] `ruff` 린트 오류 없음
- [ ] 기존 `UnorderedItemsView` 테스트 통과 (회귀 방지)

### 엣지 케이스 검증 목록

| 케이스 | 예상 동작 |
|--------|-----------|
| 세트 SKU가 환불 처리된 경우 | 전개 후 각 ISBN 행에도 net_qty 계산 적용 |
| 세트 SKU의 member_isbn이 1개뿐인 경우 | 1개 행으로 전개 (정상 동작) |
| bundle_sku에 공백/특수문자 포함 시 | URL 인코딩 처리 후 정상 조회 |
| PUT 시 member_isbns 중복 ISBN 포함 시 | 중복 제거 후 저장 또는 400 반환 |
| 동일 번들 SKU로 POST 재요청 시 | 이미 존재하는 경우 409 또는 400 반환 |
