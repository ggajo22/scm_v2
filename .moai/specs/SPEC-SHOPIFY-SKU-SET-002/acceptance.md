# SPEC-SHOPIFY-SKU-SET-002 수락 기준 (Acceptance Criteria)

---

## REQ-SKUSET2-001 / REQ-SKUSET2-002: 스키마 변경

### AC-001-1: unique_together 제약 변경 확인

**Given** `LineItem.Meta.unique_together`가 `[("order", "shopify_line_item_id", "sku")]`로
변경되어 마이그레이션이 적용되었을 때
**When** 동일 `(order, shopify_line_item_id)`에 서로 다른 `sku` 값을 가진 두 개의 `LineItem`을
저장하면
**Then** 두 행 모두 정상 저장된다

### AC-001-2: 완전 동일 조합은 여전히 거부

**Given** `(order=O1, shopify_line_item_id=100, sku="ISBN-A")` 행이 이미 존재할 때
**When** 동일한 `(order, shopify_line_item_id, sku)` 조합으로 저장을 시도하면
**Then** `IntegrityError`가 발생한다

### AC-001-3: 마이그레이션 순서

**Given** `0025_*` 스키마 마이그레이션과 `0026_*` 백필 데이터 마이그레이션이 모두 존재할 때
**When** `python manage.py migrate`를 처음부터 순서대로 실행하면
**Then** `0025`가 `0026`보다 먼저 적용되고, `0026` 실행 중 제약 위반 오류가 발생하지 않는다

---

## REQ-SKUSET2-003 / REQ-SKUSET2-004 / REQ-SKUSET2-005: 싱크 시점 전개

### AC-003-1: 번들 SKU 싱크 시 구성 ISBN으로 전개

**Given** `"GITANMATH-F SET"` → ISBN 5종 매핑이 등록되어 있고
그리고 Shopify 주문 응답에 `sku="GITANMATH-F SET"`, `quantity=2`인 라인 아이템이 포함될 때
**When** `_sync_single_order()`가 해당 주문을 처리하면
**Then** DB에 동일 `order`, 동일 `shopify_line_item_id`를 공유하는 `LineItem` 행 5개가 생성된다
그리고 각 행의 `sku`는 서로 다른 `member_isbn` 값이다
그리고 각 행의 `quantity`는 `2`이다(나뉘지 않음)
그리고 각 행의 `title`/`price`/`vendor` 등 나머지 필드는 원본 Shopify 라인 아이템 값과 동일하다

### AC-003-2: 매핑 없는 일반 SKU는 기존과 동일

**Given** `"REGULAR-SKU-001"`에 대한 번들 매핑이 등록되어 있지 않을 때
**When** 해당 SKU를 가진 라인 아이템을 싱크하면
**Then** 기존과 동일하게 단일 `LineItem` 행이 `sku="REGULAR-SKU-001"`로 생성/갱신된다

### AC-003-3: N+1 쿼리 방지

**Given** 한 주문에 번들 SKU 라인 아이템이 3개 포함되어 있을 때
**When** `_sync_single_order()`가 해당 주문을 처리하면
**Then** `ShopifySkuSetMapping` 전체 조회 쿼리는 정확히 1회만 실행된다

### AC-004-1: 번들 라인 아이템 소멸 시 전개된 모든 행 삭제 (미발주)

**Given** 이전 싱크에서 번들 SKU가 5개 ISBN 행으로 전개되어 저장되어 있고, 모두
`purchase_status="unordered"`이며 `PurchaseOrder`에 연결되지 않았을 때
**When** 다음 싱크에서 Shopify가 해당 `shopify_line_item_id`를 더 이상 보고하지 않으면
**Then** 전개된 5개 행이 모두 삭제된다

### AC-004-2: 번들 라인 아이템 소멸 시에도 발주된 행은 보존

**Given** 전개된 5개 행 중 2개가 이미 `PurchaseOrder`에 연결되어 있을 때
**When** 다음 싱크에서 Shopify가 해당 `shopify_line_item_id`를 더 이상 보고하지 않으면
**Then** 발주 연결된 2개 행은 삭제되지 않고, 미발주 상태였던 나머지 3개만 삭제 후보가 된다
(기존 `purchase_orders__isnull=True` 필터 동작 재확인)

### AC-005-1: sync_store() 위치 캐시 정확성

**Given** 번들 SKU 라인 아이템이 포함된 주문이 이미 싱크되어 `location` 값이 저장되어 있을 때
**When** `sync_store()`가 같은 주문을 재싱크하면(위치 캐시 재사용 경로)
**Then** 전개된 N개 행 모두 동일하고 정확한 `location` 값을 유지한다

---

## REQ-SKUSET2-006: 환불 수량 자동 전체-적용 (회귀 검증)

### AC-006-1: 부분 환불이 각 구성원 행에 동일하게 적용

**Given** 번들 SKU가 2개 ISBN으로 전개되어 있고, 각 행의 `quantity=4`이며
그리고 원본 Shopify 라인 아이템에 대해 수량 1의 부분 환불(`Refund.quantity=1`,
`line_item_id=<공유 shopify_line_item_id>`)이 기록되어 있을 때
**When** `GET /api/purchase-orders/unordered/`를 호출하면
**Then** 두 구성원 행 모두 `quantity=3`(4-1)으로 응답된다(환불 수량이 각 행에 독립적으로,
분할 없이 전체 적용됨)

### AC-006-2: 완전 환불 시 두 구성원 행 모두 제외

**Given** 위와 동일한 전개 상태에서 원본 라인 아이템에 대해 수량 4 전체 환불이 기록되어 있을 때
**When** `GET /api/purchase-orders/unordered/`를 호출하면
**Then** 두 구성원 행 모두 미발주 목록에서 제외된다(net_qty=0)

---

## REQ-SKUSET2-007 / REQ-SKUSET2-008: UnorderedItemsView 정리

### AC-007-1: 화면 응답에 원본 SKU 그대로 노출(싱크 시점에 이미 ISBN)

**Given** 싱크 시점에 이미 구성 ISBN 단위로 전개되어 저장된 `LineItem`이 존재할 때
**When** `GET /api/purchase-orders/unordered/`를 호출하면
**Then** 응답의 각 행 `sku`가 그대로 실제 ISBN이며, 추가 전개 로직 없이 DB 값을 그대로 반환한다

### AC-008-1: is_bundle_member/bundle_sku 필드 완전 제거

**Given** `UnorderedItemsView` 응답을 받았을 때
**When** 응답 JSON의 각 결과 항목 키를 확인하면
**Then** `is_bundle_member` 키와 `bundle_sku` 키가 존재하지 않는다(항상 `false`/`null`이 아니라
키 자체가 없음)

---

## REQ-SKUSET2-009: GenerateOrderFileView 되돌리기

### AC-009-1: 직접 SKU 조회로 발주 파일 생성 성공

**Given** 싱크 시점에 이미 전개되어 `LineItem.sku="9788926025451"`(실제 ISBN)로 저장된 미발주
행이 존재할 때
**When** `POST /api/purchase-orders/generate-order-file/`에
`{"distributor": "booxen", "skus": ["9788926025451"]}`를 요청하면
**Then** HTTP 200과 함께 Excel 바이너리가 반환되고, 해당 행의 수량이 정확히 매칭된다
(역방향 매핑 없이 직접 `sku__in` 조회만으로 매칭)

### AC-009-2: 매핑 조회 코드 완전 제거 확인

**Given** `GenerateOrderFileView.post()` 소스 코드를 확인할 때
**When** `ShopifySkuSetMapping`에 대한 참조를 검색하면
**Then** 해당 뷰 내에 `ShopifySkuSetMapping` 참조가 존재하지 않는다

---

## REQ-SKUSET2-010: 재동기화/매핑 변경 엣지 케이스 (인정된 미해결 동작)

### AC-010-1: 매핑 변경 후 재동기화는 현재 매핑 기준으로 재전개

**Given** 주문이 최초 싱크되어 번들 SKU가 ISBN A, B 2개로 전개되어 저장되어 있고
그리고 이후 `ShopifySkuSetMapping`이 ISBN A, C(2개)로 변경되었을 때
**When** 해당 주문을 `OrderResyncView`로 재동기화하면
**Then** ISBN A 행은 갱신되고, ISBN C 행이 신규 생성된다
그리고 ISBN B 행은 자동으로 삭제되지 않고 DB에 남아있다(의도된 미해결 엣지 케이스)

---

## REQ-SKUSET2-011 / REQ-SKUSET2-012: 데이터 백필

### AC-011-1: 미발주 번들 LineItem 전개

**Given** 마이그레이션 적용 전, `purchase_status="unordered"`이고 `PurchaseOrder`에 연결되지
않은 `LineItem`(`sku="GITANMATH-F SET"`, `quantity=2`)이 존재하고, 해당 번들이 ISBN 3종에
매핑되어 있을 때
**When** 백필 데이터 마이그레이션이 적용되면
**Then** 해당 그룹에 정확히 3개의 `LineItem` 행이 존재한다(1개는 원본 PK 재사용, 2개는 신규)
그리고 3개 행 모두 `quantity=2`, 동일한 `order`/`shopify_line_item_id`를 갖는다
그리고 더 이상 `sku="GITANMATH-F SET"`인 `unordered` 행은 존재하지 않는다

### AC-011-2: 이미 발주된 LineItem은 백필 대상에서 제외

**Given** `sku="TEST-SET"`(번들 매핑 존재)이고 이미 `PurchaseOrder`에 연결된 `LineItem`이
존재할 때
**When** 백필 데이터 마이그레이션이 적용되면
**Then** 해당 행은 전개되지 않고 원본 그대로(`sku="TEST-SET"`, 단일 행) 유지된다

### AC-011-3: 재사용된 첫 행의 노트(LineItemNote) 보존

**Given** 백필 대상 `LineItem`에 `LineItemNote`가 1개 이상 연결되어 있을 때
**When** 백필 마이그레이션이 적용되면
**Then** 첫 번째(sort_order 최소) 구성 ISBN으로 재사용된 행에는 기존 노트가 그대로 남아있다
그리고 신규 생성된 나머지 구성원 행에는 노트가 복제되지 않는다(문서화된 설계상 한계)

### AC-012-1: 마이그레이션 역방향 실행이 오류 없이 완료

**Given** 백필 마이그레이션이 적용된 상태일 때
**When** `python manage.py migrate order 0025`로 백필 마이그레이션을 되돌리면
**Then** 오류 없이 완료된다(완전한 데이터 복원은 보장하지 않음이 마이그레이션 docstring에
명시되어 있음을 코드 리뷰로 확인)

---

## REQ-SKUSET2-013 / REQ-SKUSET2-014 / REQ-SKUSET2-015: 테스트 정리

### AC-013-1: 기존 화면 시점 전개 테스트 제거/재작성 확인

**Given** `test_shopify_sku_set.py`의 `TestUnorderedItemsBundleExpansion` 클래스를 확인할 때
**When** 테스트 스위트를 실행하면
**Then** 화면 시점 전개(`is_bundle_member`/`bundle_sku` 응답 필드)를 가정하는 옛 단언(assertion)이
남아있지 않다(제거되었거나 싱크 후 상태 검증으로 전환됨)

### AC-013-2: GenerateOrderFileView 번들 테스트 재작성 확인

**Given** `test_purchase_orders.py`의 `TestGenerateOrderFileView` 번들 테스트 3개를 확인할 때
**When** 테스트 스위트를 실행하면
**Then** 각 테스트가 "이미 구성 ISBN 단위로 나뉘어 저장된 LineItem"을 준비(setup)하고, 되돌려진
단순 직접 조회 경로로 검증한다(더 이상 단일 번들 SKU LineItem + 역방향 매핑을 가정하지 않음)

### AC-014-1: 신규 싱크 파이프라인 테스트 전체 통과

**Given** `test_shopify_orders.py`에 추가된 번들 전개 테스트를 확인할 때
**When** `pytest backend/order/tests/test_shopify_orders.py`를 실행하면
**Then** 모든 테스트가 통과한다

---

## 품질 게이트 (Quality Gate)

### Definition of Done

- [ ] `LineItem.Meta.unique_together` 변경 및 스키마 마이그레이션(`0025_*`) 생성 완료
- [ ] `_sync_single_order()` 번들-인식형 전개 구현 및 기존 동작(비번들 SKU) 회귀 없음
- [ ] `UnorderedItemsView` 화면 시점 전개 로직 완전 제거
- [ ] `GenerateOrderFileView` 역방향 매핑 완전 제거, 단순 직접 조회로 복원
- [ ] 데이터 백필 마이그레이션(`0026_*`) 생성 및 로컬 환경 적용 검증
- [ ] `backend/order/tests/` 전체 스위트 통과(회귀 방지)
- [ ] 신규/변경 코드 커버리지 85% 이상 (pytest)
- [ ] `ruff` 린트 오류 없음
- [ ] 프론트엔드 변경 없음(변경이 필요 없음을 재확인하는 것으로 충분 — research.md §6)
- [ ] SPEC-SHOPIFY-SKU-SET-001과의 관계(대체된 REQ-SKU-SET-003) 문서화 완료

### 엣지 케이스 검증 목록

| 케이스 | 예상 동작 |
|--------|-----------|
| 번들 SKU 매핑이 1개 ISBN만 가진 경우 | 1개 행으로 "전개"(사실상 무변화, 정상 동작) |
| 번들 SKU 라인 아이템 수량이 0인 경우 | 각 구성원 행도 `quantity=0`으로 저장(다운스트림에서 net_qty=0 처리는 기존 로직 재사용) |
| `LineItem.sku`가 NULL인 라인 아이템 | 번들 매핑 조회 대상이 아니므로(매핑은 문자열 키) 기존과 동일하게 단일 행 처리 |
| 백필 대상 번들의 `member_isbn` 목록이 이후(마이그레이션 실행 시점) 비어있는 경우 | 원본 행을 전개하지 않고 그대로 둠(방어적 처리, 데이터 손실 방지) |
| 재동기화 시 매핑이 완전히 삭제된(0개 member) 번들 SKU | 다음 싱크부터는 "매핑 없음"으로 취급되어 단일 행(원본 bundle_sku 그대로)으로 싱크됨 — 기존 전개 행들은 고아로 남음(REQ-SKUSET2-010과 동일한 인정된 엣지 케이스) |
| MySQL 프로덕션에서 대량 LineItem 백필 시 트랜잭션 크기 | 마이그레이션을 배치 단위로 커밋하거나 단일 트랜잭션 허용 여부를 Run 단계에서 실측 후 결정 |
