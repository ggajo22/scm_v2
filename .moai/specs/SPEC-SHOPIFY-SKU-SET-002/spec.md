---
id: SPEC-SHOPIFY-SKU-SET-002
version: "1.0"
status: Planned
created: 2026-07-25
updated: 2026-07-25
author: ggajo
priority: High
issue_number: ~
---

# HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0 | 2026-07-25 | 최초 작성 — SPEC-SHOPIFY-SKU-SET-001 REQ-SKU-SET-003 대체 |

---

# SPEC-SHOPIFY-SKU-SET-002: 세트 SKU 전개 시점을 Shopify 싱크로 이동

## 개요

SPEC-SHOPIFY-SKU-SET-001은 세트(번들) SKU 전개를 **화면 표시 시점**(`UnorderedItemsView.get()`)에
수행하도록 설계했다(REQ-SKU-SET-003). `LineItem.sku`는 Shopify 원본 값(번들 SKU)을 그대로
유지하고, 화면에 보여줄 때만 구성 ISBN으로 "펼쳐서" 응답했다.

이 설계는 실제 버그를 낳았다. 발주 파일 생성(`POST /api/purchase-orders/generate-order-file/`,
`GenerateOrderFileView`)은 프론트엔드가 화면에 표시된 구성 ISBN을 그대로 요청 SKU로 보내지만,
`LineItem.objects.filter(sku__in=requested)`로 DB의 원본(`LineItem.sku` = 번들 SKU)을 직접
조회하기 때문에 매칭에 실패하여 "알 수 없는 SKU" 오류로 발주 파일 생성이 완전히 막혔다. 이 문제는
커밋 `6d2dfc4`에서 `GenerateOrderFileView`에 역방향 매핑(구성 ISBN → 번들 SKU) 조회를 추가하는
방식으로 **땜질(reactive patch)** 되었으며, 이는 SPEC-001이 명시적으로 제외했던
"역방향 조회 없음" 원칙을 어기는 결과를 낳았다.

**본 SPEC은 이 반응적 패치 접근을 폐기하고, 근본 설계를 변경한다.** 세트 SKU 전개를
**Shopify 싱크(주문 수집) 시점**으로 이동시켜, `LineItem`이 DB에 저장되는 순간부터 이미
구성 ISBN 단위로 존재하도록 한다. 이렇게 하면 발주 파일 생성, 미발주 현황 조회, Daily Review
다운로드/업로드, 환불 계산 등 모든 하위 소비자가 읽기/쓰기 시점 변환 계층 없이 실제 ISBN을
자연스럽게 다루게 된다.

**본 SPEC은 SPEC-SHOPIFY-SKU-SET-001의 REQ-SKU-SET-003(발주 생성 시 세트 SKU 전개)을
대체(supersede)한다.** SPEC-001의 나머지 요구사항(REQ-SKU-SET-001 모델, REQ-SKU-SET-002 CRUD API,
REQ-SKU-SET-004 프론트엔드 관리 페이지)은 변경 없이 그대로 유지된다. SPEC-001의 상태(`status`)를
"Implemented"에서 갱신할지 여부는 이 SPEC의 Sync 단계에서 별도로 판단한다(이 SPEC 문서 자체는
SPEC-001 파일을 수정하지 않는다).

---

## 배경 조사

이 SPEC 작성 전 `research.md`에 코드베이스 직접 확인 결과를 기록했다. 아래 요구사항의 파일/줄
번호는 모두 `research.md`에서 실제 코드를 읽고 검증한 값이다.

---

## 범위 (Scope)

### 확정된 사용자 결정 사항 (재논의 대상 아님)

1. **환불 수량 정책**: 번들 라인 아이템이 부분 환불되면, Shopify가 보고한 환불 수량 전체를
   전개된 각 구성 ISBN `LineItem` 행에 **동일하게(분할하지 않고)** 적용한다 — 이는 기본 수량에
   대한 기존 정책("번들 전체 수량을 각 구성원에 그대로 적용, 나누지 않음")과 동일한 원칙이다.
2. **기존 데이터 백필**: `purchase_status="unordered"`이고 `sku`가 `ShopifySkuSetMapping.bundle_sku`와
   일치하는 기존 `LineItem` 행을 찾아 구성 ISBN 수만큼 전개하는 1회성 데이터 마이그레이션을
   수행한다. 이미 `PurchaseOrder`에 연결된(`purchase_orders__isnull=False`) `LineItem`은 건드리지
   않는다(SPEC-001의 "기존 PurchaseOrder 소급 전개 없음" 원칙 유지).
3. **불필요해진 코드 정리**: 싱크 시점 전개가 적용되면 `UnorderedItemsView`의 화면 표시 시점
   전개 로직과 `GenerateOrderFileView`의 역방향 매핑 패치(커밋 `6d2dfc4`)를 모두 제거한다.

### 대상

- Django 백엔드: `order` 앱의 모델, 마이그레이션, Shopify 싱크 파이프라인, 발주 관련 뷰
- 데이터 백필: Django 데이터 마이그레이션(`RunPython`)
- 테스트: 백엔드 pytest 스위트 (프론트엔드 변경 없음 — 아래 Exclusions 참조)

---

## 요구사항 (EARS Format)

### 스키마 변경

#### REQ-SKUSET2-001: LineItem unique_together 제약 변경

**The system shall** `LineItem.Meta.unique_together`를 `[("order", "shopify_line_item_id")]`에서
`[("order", "shopify_line_item_id", "sku")]`로 변경한다.

- 대상 파일: `backend/order/models.py` (`LineItem.Meta`, 현재 147번째 줄)
- 목적: 하나의 Shopify 라인 아이템(`shopify_line_item_id`)에 대해 구성 ISBN 수만큼의 `LineItem`
  행을 저장할 수 있도록 허용한다.
- `sku`는 nullable(`null=True`) 필드이며, MySQL 8.0과 SQLite(테스트 환경) 모두 표준 SQL 의미상
  NULL을 서로 다른 값으로 취급하므로(NULL ≠ NULL) `sku=NULL`인 행 간에는 DB 레벨 유일성이
  보장되지 않는다. 이는 이 변경으로 새로 생기는 위험이 아니라 기존에도 존재하던 특성이며,
  `update_or_create`가 매 싱크마다 SELECT 후 INSERT/UPDATE를 결정하는 순차 실행 흐름에서는
  실질적 중복 생성 위험이 없다(코드베이스에 동시 실행되는 Celery 워커나 병렬 싱크 경로가 확인되지
  않음). 별도의 sentinel 값 도입은 하지 않는다.

#### REQ-SKUSET2-002: 스키마 마이그레이션 생성

**The system shall** REQ-SKUSET2-001의 제약 변경을 위한 Django 스키마 마이그레이션
(`AlterUniqueTogether`)을 `backend/order/migrations/`에 생성한다.

- 마이그레이션 번호: 기존 마지막 마이그레이션(`0024_yes24data.py`) 다음인 `0025_*.py`
- 이 마이그레이션은 REQ-SKUSET2-005(백필 데이터 마이그레이션)보다 **먼저** 적용되어야 한다 —
  구 제약(`order`, `shopify_line_item_id`)이 남아있는 상태에서 백필이 동일
  `shopify_line_item_id`를 공유하는 N개의 행을 생성하려 하면 제약 위반으로 실패한다.

---

### Shopify 싱크 파이프라인 (전개 시점 이동)

#### REQ-SKUSET2-003: 싱크 시점 세트 SKU 전개

**When** `_sync_single_order()`가 Shopify 주문의 라인 아이템(`li`)을 처리할 때, **the system shall**
`li.get("sku")`가 `ShopifySkuSetMapping.bundle_sku`와 일치하는지 확인한다.

- 대상 파일: `backend/order/shopify_orders.py` (`_sync_single_order()` 함수, 현재 159-180번째 줄의
  `LineItem.objects.update_or_create()` 루프)
- 매핑 조회는 주문 1건당 1회, `ShopifySkuSetMapping` 전체를 메모리 내 딕셔너리로 로드하여
  N+1 쿼리를 방지한다(SPEC-001의 REQ-SKU-SET-003 비기능 요구사항과 동일한 성능 원칙 계승).

**When** `li.get("sku")`가 `bundle_sku`에 매핑되어 있을 때, **the system shall** 해당 `bundle_sku`의
`member_isbn` 목록을 `sort_order` 순서로 순회하며, 각 `member_isbn`에 대해
`LineItem.objects.update_or_create(order=order_obj, shopify_line_item_id=li["id"], sku=member_isbn,
defaults={...})`를 호출한다. `defaults`에 포함되는 나머지 필드(`quantity`, `price`, `title`,
`variant_title`, `total_discount`, `fulfillment_status`, `vendor`, `grams`, `location` 등)는
Shopify 라인 아이템 원본 값을 그대로 복사한다("전체 수량을 각 구성원에 그대로 적용" 정책, 나누지
않음).

**While** `li.get("sku")`에 대한 `ShopifySkuSetMapping`이 존재하지 않을 때, **the system shall**
기존과 동일하게 `sku=li.get("sku")`인 단일 `LineItem` 행을 `update_or_create`한다(오늘날의 동작을
100% 보존).

#### REQ-SKUSET2-004: 소멸 LineItem 정리 로직 무변경 검증

**The system shall** 기존 stale-LineItem 삭제 로직(`order_obj.line_items.filter(purchase_orders__isnull=True).exclude(shopify_line_item_id__in=incoming_shopify_ids).delete()`,
현재 181-184번째 줄)을 **수정하지 않는다.**

- 근거(research.md §7에서 검증): 이 로직은 `shopify_line_item_id`만으로 필터링하며 `sku`는 전혀
  참조하지 않는다. 하나의 번들 라인 아이템에서 전개된 N개의 행은 모두 동일한
  `shopify_line_item_id`를 공유하므로, Shopify가 여전히 해당 라인 아이템을 보고하면 N개 모두
  유지되고, 더 이상 보고하지 않으면(미발주 상태인 한) N개 모두 삭제 후보가 된다 — 항상 "세트
  단위"로 일관되게 동작한다.
- 이 요구사항은 회귀 테스트(REQ-SKUSET2-013)로 명시적으로 검증되어야 한다.

#### REQ-SKUSET2-005: sync_store() 위치 캐시 최적화 무영향 검증

**The system shall** `sync_store()`의 `existing_line_item_locs` 사전 로드 최적화(현재
274-282번째 줄)를 **수정하지 않는다.**

- 근거(research.md §7): 이 딕셔너리는 `(shopify_order_id, shopify_line_item_id) → location`
  읽기 전용 조회 최적화이며, N개의 분할 행이 모두 동일한 `location` 값을 쓰기 때문에(같은
  `line_item_location_map.get(li["id"], "")` 소스 사용) 딕셔너리 키가 중복 갱신될 뿐 결과값은
  항상 동일하다. 정확성에 영향 없음.

---

### 환불 시맨틱 (코드 변경 없음, 근거 문서화)

#### REQ-SKUSET2-006: 환불 수량 자동 전체-적용 (기존 로직 재사용)

**The system shall** `Refund` 기반 순수 수량 차감 로직(`UnorderedItemsView`, `GenerateOrderFileView`,
`RunComparisonView`, `DailyReviewExcelView`, `_attach_net_quantity`, `PurchaseOrderListView.get()`
자체 필터까지 총 6개의 `Refund.objects.filter(order_id=OuterRef("order_id"),
line_item_id=OuterRef("shopify_line_item_id"))` 서브쿼리 — 최초 초안에서 4개로 과소 집계되었던 것을
research.md 재검증으로 바로잡음)을 **일절 수정하지 않는다.**

- 근거(research.md §7): `Refund.line_item_id`는 `shopify_line_item_id`(PK 아님, 원본 Shopify 값)를
  저장하는 일반 필드다. N개의 분할 `LineItem` 행이 동일한 `shopify_line_item_id`를 공유하므로,
  이 서브쿼리는 N개 행 각각에 대해 독립적으로 재평가되지만 항상 **동일한 총 환불 수량**을
  반환한다. 각 행은 자신의 (전체, 미분할) `quantity`에서 이 동일한 환불 수량을 독립적으로
  차감하므로, "구성 ISBN 각각에 전체 환불 수량을 동일하게 적용"이라는 사용자 결정 사항이
  **코드 변경 없이 자동으로 성립**한다.
- **전제 조건(반드시 REQ-SKUSET2-003이 보장해야 함)**: 이 자동 성립은 싱크 시점에 각 분할 행이
  정확히 Shopify 원본의 (미분할) `quantity` 값을 그대로 받는다는 전제에 의존한다. 만약 향후
  구현에서 수량을 구성원 수로 나누어 저장한다면 환불 차감 결과가 조용히 틀어진다 — 이 SPEC은
  이 전제를 REQ-SKUSET2-003에 명시적으로 못 박아 암묵적 가정으로 남기지 않는다.

---

### 화면 표시 로직 정리 (SPEC-001 REQ-SKU-SET-003 되돌리기)

#### REQ-SKUSET2-007: UnorderedItemsView 화면 시점 전개 로직 제거

**The system shall** `UnorderedItemsView.get()`의 화면 표시 시점 세트 전개 블록(`bundle_map`
구축 및 `expanded` 루프, 현재 131-152번째 줄)을 **완전히 제거**하고, 149-129번째 줄에서 이미
구성된 `results` 리스트를 그대로 응답한다: `return Response({"count": len(results), "results":
results})`.

- 대상 파일: `backend/order/purchase_order_views.py`
- 싱크 시점에 이미 `LineItem.sku`가 실제 ISBN이므로, 이 시점의 추가 전개는 불필요하다.

#### REQ-SKUSET2-008: 응답 계약에서 is_bundle_member/bundle_sku 필드 완전 제거

**The system shall** `UnorderedItemsView`의 응답에서 `is_bundle_member`, `bundle_sku` 필드를
완전히 제거한다(항상 `false`/`null`로 유지하는 방식이 아니라 필드 자체를 없앤다).

- 근거(research.md §6에서 검증): `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`와
  `frontend/src/services/purchaseOrderApi.ts`의 `UnorderedItem` TypeScript 인터페이스 모두
  이 두 필드를 전혀 참조하지 않는다(SPEC-001 도입 이후 한 번도 프론트엔드에서 소비된 적 없음).
  필드 제거는 프론트엔드에 어떠한 영향도 주지 않으며, 필드를 유지하는 것은 불필요한 응답 계약
  복잡도만 남긴다.

#### REQ-SKUSET2-009: GenerateOrderFileView 역방향 매핑 되돌리기

**The system shall** `GenerateOrderFileView.post()`에서 커밋 `6d2dfc4`가 추가한 역방향 매핑
로직(`member_to_bundle` 딕셔너리 구축, `requested_underlying` 변환, `underlying_found_map`→
`found_map` 역매핑, 현재 196-248번째 줄)을 **완전히 제거**하고, 다음의 단순한 직접 조회로
되돌린다:

```python
requested = set(skus)
li_qs = (
    LineItem.objects.filter(sku__in=requested)
    .exclude(purchase_orders__isnull=False)
    .annotate(refunded_qty=Coalesce(Subquery(refund_sum_sq, output_field=IntegerField()), 0))
    .values("sku", "title", "quantity", "refunded_qty")
)
found_map: dict[str, dict] = {}
for row in li_qs:
    net = max((row["quantity"] or 0) - row["refunded_qty"], 0)
    if net == 0:
        continue
    sku = row["sku"]
    if sku not in found_map:
        found_map[sku] = {"sku": sku, "title": row["title"] or "", "total_quantity": 0}
    found_map[sku]["total_quantity"] += net
unknown_skus = [s for s in skus if s not in found_map]
```

- 싱크 시점에 `LineItem.sku`가 이미 실제 ISBN이므로, 요청받은 SKU를 그대로 직접 조회하면
  매칭된다 — 역방향 변환이 더 이상 필요 없다.
- 이 되돌림은 SPEC-SHOPIFY-SKU-SET-001의 명시적 제외 사항("역방향 조회 없음: ISBN → bundle_sku
  역방향 검색 기능은 제공하지 않는다")을 다시 준수하는 결과이기도 하다.

---

### 재동기화(re-sync) 시 매핑 변경 — 인정된 엣지 케이스 (해결하지 않음)

#### REQ-SKUSET2-010: 매핑 변경 후 재동기화 시 동작 (While/Unwanted 명시)

**While** 이미 싱크되어 전개된 주문의 `ShopifySkuSetMapping`이 이후 수정(구성원 추가/삭제)된
상태에서, **when** 해당 주문이 `OrderResyncView` 또는 향후 webhook을 통해 재동기화될 때,
**the system shall** 재동기화 시점의 **현재** 매핑을 기준으로 다시 전개를 수행한다(과거 전개
결과를 기억하거나 강제로 일치시키지 않는다).

**If** 재동기화로 인해 이전에 존재하던 구성 ISBN이 새 매핑에서 제거되었다면, **then the system
shall NOT** 자동으로 해당 과거 구성 ISBN의 `LineItem` 행을 정리(삭제)한다 — 이 행은
`purchase_status`에 따라 미발주 목록에 "고아(orphan)" 상태로 남는다. 이는 SPEC-001의 "소급
재전개 없음" 철학과 일관된, **의도적으로 해결하지 않는** 엣지 케이스다(아래 Exclusions 참조).

---

### 데이터 백필

#### REQ-SKUSET2-011: 기존 미발주 번들 LineItem 백필 데이터 마이그레이션

**The system shall** Django 데이터 마이그레이션(`RunPython`, `backend/order/migrations/0026_*.py`,
REQ-SKUSET2-002 스키마 마이그레이션 이후 적용)을 생성하여, `purchase_status="unordered"`이고
`purchase_orders__isnull=True`(미발주)이며 `sku`가 `ShopifySkuSetMapping.bundle_sku`와 일치하는
모든 기존 `LineItem` 행을 찾는다.

**When** 백필 대상 `LineItem` 행이 발견될 때, **the system shall** 해당 `bundle_sku`의
`member_isbn` 목록을 `sort_order` 순서로 조회하여:
1. **첫 번째**(`sort_order` 최소) `member_isbn`에 대해서는 **기존 `LineItem` 행의 `sku` 필드를
   해당 ISBN으로 직접 갱신(UPDATE in place)**한다 — 기존 PK, `LineItemNote` 등 관련 FK 관계를
   보존한다.
2. **나머지** `member_isbn`들에 대해서는 원본 행의 `quantity`/`price`/`title`/`variant_title`/
   `vendor`/`grams`/`location`/`fulfillment_status`/`total_discount` 값을 복사한 **신규**
   `LineItem` 행을 생성한다(`order`, `shopify_line_item_id`는 원본과 동일, `sku`만 해당
   `member_isbn`).

**If** 백필 대상 `LineItem`이 이미 하나 이상의 `PurchaseOrder`에 연결되어 있다면(`purchase_orders__isnull=False`),
**then the system shall NOT** 해당 행을 백필 대상에 포함하지 않는다(SPEC-001의 "기존 PurchaseOrder
소급 전개 없음" 원칙 유지).

- **알려진 한계(문서화, 별도 요구사항 아님)**: 원본 행에 연결된 `LineItemNote`(CS/발주/창고 노트)는
  1번 방식(재사용된 첫 번째 구성원 행)에만 남고, 신규 생성된 나머지 N-1개 구성원 행에는
  복제되지 않는다. 이는 노트가 원래 "번들 단위"로 작성되었을 뿐 특정 구성원에 종속되지 않았기
  때문에 발생하는 자연스러운 결과이며, 이 SPEC은 노트를 복제하지 않는 쪽을 명시적으로 선택한다.

#### REQ-SKUSET2-012: 백필 마이그레이션의 역방향(reverse) 동작

**The system shall** 백필 마이그레이션에 대응하는 `reverse_code`(또는 `RunPython.noop`)를
정의하여, 마이그레이션 롤백 시 최소한 오류 없이 되돌릴 수 있도록 한다. 완전한 역백필(N개
행을 다시 1개로 병합)은 정보 손실(어느 행이 원본이었는지)로 인해 100% 재현 불가능함을
마이그레이션 docstring에 명시한다.

---

### 테스트 업데이트

#### REQ-SKUSET2-013: 기존 테스트 정리 및 재작성

**The system shall** 아래 기존 테스트를 이 SPEC의 변경사항에 맞춰 갱신한다:

- `backend/order/tests/test_shopify_sku_set.py`의 `TestUnorderedItemsBundleExpansion` 클래스
  (현재 289-330번째 줄, 3개 테스트: `test_bundle_sku_expanded`, `test_non_bundle_sku_not_expanded`,
  `test_bundle_count_reflects_expansion`)와 `order_with_bundle_lineitem` 픽스처(55-72번째 줄)는
  화면 표시 시점 전개가 제거되므로 **제거하거나, 싱크 시점 전개 이후 상태를 검증하는 테스트로
  재작성**한다.
- `backend/order/tests/test_purchase_orders.py`의 `TestGenerateOrderFileView` 내 3개 번들 테스트
  (현재 499-591번째 줄, 커밋 `6d2dfc4`에서 추가됨)는 **이미 구성 ISBN 단위로 나뉘어 있는
  LineItem**(싱크 후 상태를 시뮬레이션)을 준비한 뒤, 되돌려진 단순 조회 경로가 이를 올바르게
  처리하는지 검증하도록 재작성한다.

#### REQ-SKUSET2-014: 신규 싱크 파이프라인 테스트

**The system shall** `backend/order/tests/test_shopify_orders.py`에 아래를 검증하는 신규 테스트를
추가한다:
- 매핑이 존재하는 번들 SKU 라인 아이템을 싱크하면 구성 ISBN 수만큼의 `LineItem` 행이 생성되고,
  각 행의 `quantity`가 Shopify 원본 수량과 동일함(나뉘지 않음).
- 매핑이 없는 일반 SKU는 기존과 동일하게 단일 행으로 싱크됨(회귀).
- 번들 라인 아이템이 Shopify에서 사라지고 미발주 상태이면, 전개된 N개 행이 모두 삭제됨
  (REQ-SKUSET2-004 검증).
- 번들 라인 아이템이 Shopify에서 사라졌지만 일부 구성원 행이 이미 발주(`PurchaseOrder` 연결)된
  경우, 해당 행은 삭제되지 않음.

#### REQ-SKUSET2-015: 재동기화 엣지 케이스 문서화 테스트 (권장)

**Where** `backend/order/tests/test_order_resync.py`에 기존 테스트 구조가 존재할 때, **the
system shall** REQ-SKUSET2-010에서 인정한 엣지 케이스(매핑 변경 후 재동기화 시 고아 행 발생)를
문서화하는 최소 1개의 회귀 테스트를 추가하는 것을 권장한다(필수는 아님 — 엣지 케이스 자체를
해결하는 것이 아니라 현재 동작을 명시적으로 고정하기 위함).

---

## 비기능 요구사항

**The system shall** 싱크 시점 세트 전개를 위한 `ShopifySkuSetMapping` 조회를 주문 처리당 1회로
제한하여(N+1 쿼리 방지), 기존 싱크 성능 특성을 유지한다.

**The system shall** 스키마 마이그레이션과 데이터 백필 마이그레이션을 분리된 별도 마이그레이션
파일로 작성하여, 스키마 변경과 데이터 변경의 롤백/추적을 독립적으로 관리할 수 있게 한다.

**참고(오케스트레이터를 위한 하니스 레벨 권고)**: 이 SPEC은 스키마 제약 변경, 프로덕션 데이터
백필(1회성 되돌리기 어려운 변경), 환불(재무 인접) 계산 로직의 암묵적 의존성 문서화를 모두
포함하는 복합 변경이다. Run 단계 진입 시 `harness` 레벨을 `thorough`로 지정하여
evaluator-active + TRUST 5 전체 검증을 거칠 것을 강력히 권고한다.

---

## Exclusions (What NOT to Build)

- **DailyReviewExcelView/UploadDailyReviewView 코드 변경 없음**: 두 뷰는 오늘도 `LineItem.sku`를
  직접 사용하며, 싱크 시점 전개 이후 자연스럽게 더 정확한 데이터(실제 ISBN 기준 벤더가격/재고
  조인)를 반환하게 되는 **부수 효과**일 뿐, 이 SPEC이 요구하는 신규 빌드 대상이 아니다(research.md §11).
- **프론트엔드 변경 없음**: `UnorderedItemsTab.tsx`와 `purchaseOrderApi.ts`의 `UnorderedItem`
  인터페이스는 `is_bundle_member`/`bundle_sku` 필드를 참조한 적이 없으므로(research.md §6),
  REQ-SKUSET2-008로 인한 프론트엔드 코드 변경은 없다.
- **SKU 세트 매핑 관리 페이지(`/settings/sku-sets`) 무변경**: `SkuSetsPage.tsx`,
  `shopify_sku_set_views.py`, `ShopifySkuSetListCreateView`/`ShopifySkuSetDetailView`는 매핑
  자체를 관리하는 CRUD이며 이 SPEC의 대상이 아니다.
- **재동기화 시 매핑 변경 엣지 케이스 해결 없음**: REQ-SKUSET2-010에서 인정한 "고아 구성원 행"
  케이스는 자동 정리 로직을 구축하지 않는다(SPEC-001의 "소급 재전개 없음" 철학 계승).
- **기존 PurchaseOrder 소급 전개 없음**: 이미 `PurchaseOrder`에 연결된 `LineItem`은 백필 대상에서
  제외하며, 어떤 경우에도 사후적으로 전개하지 않는다(SPEC-001 원칙 유지).
- **환불/수량의 구성원 간 분할 없음**: 번들 수량과 환불 수량 모두 각 구성 ISBN에 전체 값을 그대로
  적용하며, 구성원 수로 나누지 않는다(SPEC-001부터 이어지는 기존 정책, 변경 없음).
- **ISBN → bundle_sku 역방향 조회 기능 재도입 없음**: 커밋 `6d2dfc4`의 역방향 매핑은 이 SPEC이
  제거하는 대상이며, 어떤 형태로든 다시 추가하지 않는다(SPEC-001 원칙 복원).
- **`sku` NULL sentinel 값 도입 없음**: NULL-in-unique-together는 기존에도 존재하던 특성이며
  이 SPEC에서 별도의 sentinel 값이나 `null=False` 강제를 도입하지 않는다(research.md §5).
- **자동 Shopify SKU 감지 없음**: 세트 여부 판정은 여전히 수동 매핑 테이블 등록에 의존하며,
  Shopify API로부터 자동 판별하지 않는다(SPEC-001 원칙 유지).
- **백필 후 신규 구성원 행에 노트(LineItemNote) 복제 없음**: 원본 행에 있던 노트는 재사용된 첫
  번째 구성원 행에만 남고, 신규 생성되는 나머지 구성원 행에는 복제하지 않는다(REQ-SKUSET2-011
  참조, 의도적 설계 선택).

---

## 관련 SPEC

- **SPEC-SHOPIFY-SKU-SET-001** — 이 SPEC이 REQ-SKU-SET-003(발주 생성 시 세트 SKU 전개)을
  대체한다. SPEC-001의 REQ-SKU-SET-001(모델), REQ-SKU-SET-002(CRUD API), REQ-SKU-SET-004(관리
  페이지)는 그대로 유지된다. SPEC-001의 `status` 필드 갱신은 이 SPEC의 Sync 단계에서 별도 검토.
- **커밋 `6d2dfc4`** — "SKU 세트 매핑 전개 항목 선택 시 '알 수 없는 SKU' 오류 수정": 이 SPEC이
  되돌리는 반응적 패치. 해당 커밋의 테스트 3개는 REQ-SKUSET2-013에 따라 재작성된다.
