---
id: SPEC-ORDER-018
document: acceptance
version: 1.0.5
status: completed
updated: 2026-08-13
---

# 인수 기준 — SPEC-ORDER-018 보류/제외 품목 발주 대상 복구

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의
AC-RESTORE-XXX / REQ-RESTORE-XXX ID를 인용해 상호 추적된다.

[HARD] 각 시나리오의 `Traces:` 목록은 `spec.md` ACCEPTANCE CRITERIA 절의 동일 AC 항목이
선언한 것과 완전히 일치한다. 어느 한쪽을 수정할 때 반드시 함께 갱신한다.

**검증 레이어**: `[BE]`는 `backend/order/tests/test_spec_018.py`의 pytest 시나리오,
`[FE]`는 vitest 시나리오다. AC-RESTORE-001~011이 `[BE]`, AC-RESTORE-012~014가
`[FE]`다. `[FE]` 중 AC-RESTORE-012/013은
`frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx`에 있고,
**AC-RESTORE-014만 `frontend/src/hooks/usePurchaseOrderQueries.test.tsx`에 있다** —
탭 테스트는 `usePurchaseOrderQueries` 모듈 전체를 `vi.mock`으로 대체하므로 검증
대상인 실제 `onSuccess` 콜백이 그 안에서 실행되지 않는다(spec.md v1.0.1 발산 기록).

**호출 스코프**: 백엔드 시나리오는 전부 `auth_client`(또는 `anon_client`)로 HTTP
엔드포인트를 호출한다 — 이 SPEC이 추출하는 순수 함수가 없으므로 함수 직접 호출 스코프는
존재하지 않는다. 쿼리 수를 다루는 유일한 시나리오(AC-RESTORE-007)는 **동등성과 절대값을
모두** 주장한다. `JWTAuthentication`의 사용자 조회가 측정에 포함되지만 요청당 정확히
1건으로 결정적이므로 절대값 고정이 가능하며, 그 1건은 상수
`UNORDERED_ENDPOINT_QUERY_COUNT`에 명시적으로 포함돼 있다. 동등성만 주장하면 기존 뷰에
추가된 쿼리가 양쪽 측정에서 상쇄되어 판별력이 사라진다(v1.0.4 참조).

**공통 픽스처 관례**: `user` / `auth_client` / `anon_client` 픽스처와
`_make_order` / `_make_line_item` 헬퍼는 `backend/order/tests/test_purchase_orders.py:72`,
`:77`, `:85`, `:89`, `:97` 형태를 복제한다. URL 상수는 같은 파일 `:50-59`의 관례에 따라
스위트 상단에 정의한다.

---

## 조회 경로 — 선별과 무쓰기

### AC-RESTORE-001 — 7개 상태 중 정확히 4개만 반환되며 아무것도 쓰지 않는다 `[BE]`

Traces: REQ-RESTORE-001, REQ-RESTORE-002

- **Given**: Order 1개(`_make_order`) 아래에 `LineItem` 7건을 만든다 — 각각
  `purchase_status`가 `unordered`, `on_hold`, `order_cancelled`, `other_publisher`,
  `cs_required`, `in_stock`, `damaged_exchange`이며 SKU는 `SKU-UNORDERED`,
  `SKU-HOLD`, `SKU-CANCEL`, `SKU-OTHERPUB`, `SKU-CS`, `SKU-STOCK`, `SKU-DMG`로 서로 다르다.
  모든 행은 `quantity=1`이고 `Refund`는 없다.
  요청 직전에 7건 전부의 전 필드 스냅샷(`LineItem.objects.values()` 결과)을 뜬다.
- **When**: `auth_client`로 제외 품목 목록 URL을 GET 한다.
- **Then**: HTTP 200이며 응답 `results`의 SKU 집합이 정확히
  `{"SKU-HOLD", "SKU-CANCEL", "SKU-OTHERPUB", "SKU-CS"}`다 — 4건이며 그 이상도 이하도 아니다.
  `SKU-UNORDERED`, `SKU-STOCK`, `SKU-DMG`는 포함되지 않는다. 요청 후 다시 뜬 7건의 전 필드
  스냅샷이 요청 전 스냅샷과 **완전히 동일**하다(무쓰기). `LineItemNote`, `PurchaseOrder`,
  `Order` 행 수도 요청 전후로 동일하다.

### AC-RESTORE-002 — SKU 없는 품목은 제외된다 `[BE]`

Traces: REQ-RESTORE-004

- **Given**: Order 1개 아래에 `purchase_status="on_hold"`인 LineItem 2건을 만든다 —
  li_nosku는 `sku=None`, li_sku는 `sku="SKU-HAS"`. 둘 다 `quantity=1`.
- **When**: `auth_client`로 제외 품목 목록 URL을 GET 한다.
- **Then**: `results`의 길이가 1이고 그 항목의 `sku`가 `"SKU-HAS"`다. li_nosku의 id는
  응답 어디에도 없다. **주의**: 두 행이 모두 같은 상태이므로, 구현이 SKU 가드를 빠뜨리면
  길이가 2가 되어 판별된다.

### AC-RESTORE-003 — 환불 넷팅은 전량 환불만 제외하고 미환불 0수량은 남긴다 `[BE]`

Traces: REQ-RESTORE-005

- **Given**: Order 1개 아래에 `purchase_status="order_cancelled"`인 LineItem 3건:
  - `li_partial` — `sku="SKU-PARTIAL"`, `quantity=5`,
    대응 `Refund` 행들의 `quantity` 합계 2
  - `li_full` — `sku="SKU-FULL"`, `quantity=3`, 대응 `Refund` 합계 3
  - `li_nullqty` — `sku="SKU-NULLQTY"`, `quantity=None`, `Refund` **없음**

  `Refund` 행은 `order_id`와 `line_item_id`(= 대상 LineItem의 `shopify_line_item_id`) 두 키로
  매칭된다 — 로컬 pk가 아니다(근거: `purchase_order_views.py:2384-2386`의 주석).
- **When**: `auth_client`로 제외 품목 목록 URL을 GET 한다.
- **Then**: `results`의 SKU 집합이 정확히 `{"SKU-PARTIAL", "SKU-NULLQTY"}`다.
  `SKU-PARTIAL` 항목의 `quantity`가 **3**(5 - 2)이다. `SKU-FULL`은 포함되지 않는다.
  `SKU-NULLQTY`는 포함되며 그 `quantity`는 0이다.
  **판별력**: 구현이 `UnorderedItemsView:293-294`의 무조건 `if net_qty == 0: continue`를
  복사하면 `SKU-NULLQTY`(`max((None or 0) - 0, 0) == 0`)까지 사라져 이 시나리오가 실패한다.
  올바른 구현은 `LineItemRackNumberSummaryView:2415`의
  `if li.refunded_qty and net_qty == 0:` 가드다(`spec.md` 설계 결정 D).

## 조회 경로 — 응답 계약

### AC-RESTORE-004 — 봉투·필드 집합·결정적 정렬 `[BE]`

Traces: REQ-RESTORE-003, REQ-RESTORE-006, REQ-RESTORE-007

- **Given**: 서로 다른 `shopify_created_at`을 갖는 Order 여러 개에 걸쳐 4개 제외 상태의
  LineItem 12건을 만든다. 그중 **2건은 서로 다른 Order에 속하되 두 Order의
  `shopify_created_at`이 정확히 같도록** 설정한다(정렬 tie 유발). 모든 행에
  `title`, `vendor`, `sku`, `quantity`를 채운다.
- **When**: `auth_client`로 제외 품목 목록 URL을 **연속 2회** GET 한다.
- **Then**:
  - (a) 두 응답 모두 HTTP 200이며 최상위 키 집합이 정확히 `{"count", "results"}`다 —
    `"next"`도 `"previous"`도 없다(REQ-RESTORE-006, `spec.md` 설계 결정 G).
  - (b) `count == len(results) == 12`다.
  - (c) 모든 항목이 `id`, `order_name`, `sku`, `title`, `vendor`, `quantity`,
    `purchase_status` 키를 갖는다(REQ-RESTORE-003).
  - (d) 두 응답의 `[item["id"] for item in results]` 리스트가 **완전히 동일**하다 —
    `shopify_created_at`이 같은 2건의 상대 순서까지 같다(REQ-RESTORE-007).
  - **판별력**: 정렬이 `-order__shopify_created_at` 단일 키뿐이면 (d)가 MySQL의 반환 순서에
    따라 간헐적으로 실패한다. `pk` tie-break가 이를 고정한다(`spec.md` 설계 결정 H,
    선례 `purchase_order_views.py:3450` + 주석 `:3442-3445`).

### AC-RESTORE-005 — 미인증 요청은 401이며 품목 데이터를 노출하지 않는다 `[BE]`

Traces: REQ-RESTORE-008

- **Given**: `purchase_status="on_hold"`, `sku="SKU-SECRET"`, `title="Secret Book"`인
  LineItem 1건이 존재한다.
- **When**: `anon_client`(자격 증명 미설정)로 제외 품목 목록 URL을 GET 한다.
- **Then**: HTTP 401이다. 응답 본문 문자열에 `"SKU-SECRET"`도 `"Secret Book"`도 그 LineItem의
  `id` 값도 등장하지 않는다.

## 기존 재발주 경로 불변 (회귀 방지)

### AC-RESTORE-006 — 미발주 목록과 Daily Review 업로드 매칭이 그대로다 `[BE]`

Traces: REQ-RESTORE-009, REQ-RESTORE-010

- **Given**: Order 1개 아래에 LineItem 5건 —
  `SKU-A`(`unordered`, PurchaseOrder 미연결), `SKU-B`(`on_hold`),
  `SKU-C`(`order_cancelled`), `SKU-D`(`cs_required`), `SKU-E`(`other_publisher`).
  모두 `quantity=1`.
- **When**: (1) `auth_client`로 `UNORDERED_URL`을 GET 한다. (2) `SKU-B`~`SKU-E` 4개 SKU를
  담은 Daily Review 엑셀을 만들어 업로드 엔드포인트에 POST 한다(엑셀 구성 기법은
  `backend/order/tests/test_daily_review_upload.py`의 기존 시나리오를 따른다).
- **Then**:
  - (1)의 `results` SKU 집합이 정확히 `{"SKU-A"}`다 — `SKU-B`~`SKU-E`는 하나도 없다.
  - (2)의 응답이 4개 SKU를 전부 **미매칭/skip**으로 보고한다(매칭 0건).
  - (2) 이후 `SKU-B`~`SKU-E` LineItem 4건의 `purchase_status`가 각각
    `on_hold`/`order_cancelled`/`cs_required`/`other_publisher` 그대로다 —
    `confirmed_distributor`, `confirmed_price`도 여전히 `None`이며 새 `PurchaseOrder`가
    이 4건에 연결되지 않았다.
  - **근거**: 두 경로 모두 `_reorder_candidate_filter`를 통과한다
    (`purchase_order_views.py:308`, `:1410`). 구현이 그 필터를 넓혔다면 이 시나리오가
    실패한다.

### AC-RESTORE-007 — 신규 뷰의 존재가 기존 엔드포인트의 쿼리 수를 바꾸지 않는다 `[BE]`

Traces: REQ-RESTORE-011

- **Given**: `unordered` LineItem 3건만 존재하는 상태(A)와, 거기에 4개 제외 상태의 LineItem
  8건을 추가한 상태(B)를 각각 준비한다.
- **When**: 각 상태에서 `CaptureQueriesContext`
  (`from django.test.utils import CaptureQueriesContext`,
  `backend/order/tests/test_spec_015.py:34`)로 감싸 `auth_client`로 `UNORDERED_URL`을
  GET 한다.
- **Then**:
  - (a) 상태 A와 상태 B에서 발생한 쿼리 수가 **동일**하다. 두 응답의 `results` 길이도 둘 다
    3으로 동일하다.
  - (b) 그 쿼리 수가 **정확히 `UNORDERED_ENDPOINT_QUERY_COUNT`(=3)**다 — 자기 자신과의
    비교가 아니라 고정된 절대값이다.
  - (c) 상태 B에서 발행된 어떤 쿼리의 SQL에도 4개 제외 상태 문자열이 등장하지 않는다.
  - (d) `UNORDERED_URL` 요청 동안 신규 뷰의 `get`이 **한 번도 호출되지 않는다**
    (`unittest.mock.patch.object` spy).

  **판별력**: (a)만으로는 REQ-RESTORE-011이 금지하는 것을 잡지 못한다. 기존 뷰에 쿼리가
  하나 추가되면 그 비용이 **두 측정 모두에 들어가 상쇄**되므로 (a)는 그대로 통과한다 —
  plan-audit SPEC-ORDER-018-review-1(D2)이 실제로 `UnorderedItemsView.get()`에 쿼리를
  누출시켜 통과함을 확인했다. (b)가 이를 잡는다(mutation 재확인: `assert 4 == 3`으로 실패).
  (d)는 "신규 뷰가 기존 엔드포인트의 호출 그래프에 나타나지 않는다"는 이 AC의 두 번째 절을
  검증한다 — 이전에는 어떤 테스트도 이 절을 다루지 않았다(mutation 재확인: 기존 뷰에서 신규
  뷰를 호출하면 실패). (c)는 공유 필터가 넓어지는 경우를 SQL 수준에서 추가로 잡는다
  (mutation 재확인: 기존 뷰 쿼리셋에 제외 상태 리터럴이 등장하면 실패).

  **상수 재도출**: `UNORDERED_ENDPOINT_QUERY_COUNT`는 JWT 사용자 조회 1건 + 이 뷰가
  SPEC-ORDER-018 이전부터 발행하던 2건이다. 의도적으로 바뀌었다면 틀린 값을 임시로 단정해
  실제 값을 읽어 갱신한다.

## 복구 부수효과 — Order 집계

### AC-RESTORE-008 — `order_cancelled` 복구가 `ready_to_ship`을 뒤집고 `status`는 건드리지 않는다 `[BE]`

Traces: REQ-RESTORE-014

- **Given**: Order 1개 아래에 LineItem 2건 —
  - `li_ready`: `sku="SKU-READY"`, `logistics_status="received"`,
    `purchase_status="unordered"`
  - `li_cancel`: `sku="SKU-CANCEL"`, `logistics_status="not_shipped"`,
    `purchase_status="order_cancelled"`

  `_recompute_order_aggregates([order.id])`를 호출해 집계를 초기화한 뒤 Order를 refresh
  한다. 이 시점에 `order.ready_to_ship is True`(`li_cancel`이
  `purchase_order_views.py:176`의 `non_cancelled` 필터에서 빠지고 남은 `li_ready`가
  `received`라 `:182-185`의 `all(...)`이 참)이고
  `order.status == "partial"`(`received`와 `not_shipped` 2종이 섞여 `:171-172`)임을
  **Given 단계에서 먼저 assert** 한다 — 전제가 성립하지 않으면 When/Then은 의미가 없다.
- **When**: `auth_client`로 `LINE_ITEM_STATUS_URL.format(pk=li_cancel.pk)`에
  `{"purchase_status": "unordered"}`를 PATCH 한다.
- **Then**: HTTP 200이며, `order.refresh_from_db()` 후
  - `order.ready_to_ship is False` — `li_cancel`이 집계에 재진입했고 그 항목은
    `logistics_status="not_shipped"`이며 `purchase_status`도 `in_stock`이 아니므로
    `:182-185`의 `all(...)`이 거짓이 된다.
  - `order.status == "partial"` — 복구 전과 **동일**하다. `purchase_status`는
    `:167-173`의 계산에 전혀 들어가지 않는다.

### AC-RESTORE-009 — `on_hold` 복구는 무변화, `cs_required` 복구는 false→true `[BE]`

Traces: REQ-RESTORE-014

- **Given**: Order 두 개.
  - `order_hold`: LineItem 1건 — `logistics_status="received"`,
    `purchase_status="on_hold"`. `_recompute_order_aggregates` 후 `ready_to_ship`과
    `status` 값을 기록한다.
  - `order_cs`: LineItem 2건 — 둘 다 `logistics_status="received"`,
    하나는 `purchase_status="cs_required"`, 다른 하나는 `purchase_status="unordered"`.
    `_recompute_order_aggregates` 후 `ready_to_ship is False`임을 Given 단계에서 assert
    한다(`:179-180`의 `any(cs_required)` 강제 `False`).
- **When**: 두 Order의 제외 상태 LineItem을 각각 `LINE_ITEM_STATUS_URL`로 `unordered`로
  복구한다.
- **Then**:
  - `order_hold`: `ready_to_ship`과 `status` 모두 복구 전에 기록한 값과 **동일**하다.
    `on_hold`는 `:176-185`의 어느 규칙에도 등장하지 않는다.
  - `order_cs`: `ready_to_ship is True`가 된다 — 강제 `False` 조건이 사라졌고 남은 두
    항목이 모두 `received`라 `:182-185`가 참이 된다. `status`는 복구 전과 동일하다.

## 복구 부수효과 — 쓰기 범위와 노트

### AC-RESTORE-010 — 복구는 `purchase_status`만 쓰고 노트를 건드리지 않는다 `[BE]`

Traces: REQ-RESTORE-012, REQ-RESTORE-013, REQ-RESTORE-015

- **Given**: `purchase_status="on_hold"`인 LineItem 2건(`li_single`, `li_bulk`)을 만든다.
  두 건 모두 `rack_number="A-01"`, `confirmed_distributor="booxen"`,
  `confirmed_price`가 설정되어 있고, `logistics_status="received"`(모델 기본값
  `not_shipped`와 다른 값, `models.py:204-208`), `location`이 비어 있지 않으며,
  각각 `is_resolved=False`인 `LineItemNote` 1건을 갖는다.
  두 건의 전 필드 스냅샷을 `LineItem.objects.filter(pk__in=[...]).values()`로 뜬다.
- **When**: (a) `li_single`을 `LINE_ITEM_STATUS_URL`(단일)로,
  (b) `li_bulk`를 `BULK_STATUS_URL`에 `{"ids": [li_bulk.pk], "purchase_status": "unordered"}`
  로 각각 `unordered`로 복구한다.
- **Then**: 두 경로 모두에 대해
  - `purchase_status`가 `"unordered"`로 바뀌었다.
  - 스냅샷의 **다른 모든 키**가 복구 전 값과 동일하다 — 특히 `rack_number`,
    `confirmed_distributor`, `confirmed_price`, `confirmed_at`, `logistics_status`,
    `location`, `shipped_quantity`, `shipped_at`.
  - `li.notes.count()`가 여전히 1이고, 그 노트의 `is_resolved`가 여전히 `False`이며
    `content`와 `note_type`도 불변이다. 새 `LineItemNote`가 생성되지 않았다
    (전역 `LineItemNote.objects.count()`도 불변).
  - **근거**: 단일 경로는 `purchase_order_views.py:2330`의
    `save(update_fields=["purchase_status"])`, 일괄 경로는 `:2387`의
    `existing.update(purchase_status=purchase_status_value)`. 두 뷰 어디에도
    `LineItemNote` 접근이 없다(`:1876-1900`, `:1922-1958`).

## 알려진 한계 고정

### AC-RESTORE-011 — PurchaseOrder 연결 품목은 복구해도 재발주 큐에 들어가지 않는다 `[BE]`

Traces: REQ-RESTORE-022

- **Given**: `purchase_status="order_cancelled"`, `sku="SKU-POLINKED"`인 LineItem 1건을
  만들고, `PurchaseOrder`를 하나 생성해 `po.line_items.add(li)`로 연결한다.
  대조군으로 PurchaseOrder에 연결되지 **않은** `order_cancelled` LineItem
  `sku="SKU-FREE"` 1건도 만든다.
- **When**: 두 건을 각각 `LINE_ITEM_STATUS_URL`로 `unordered`로 복구한 뒤,
  `UNORDERED_URL`과 제외 품목 목록 URL을 모두 GET 한다.
- **Then**:
  - `UNORDERED_URL`의 `results`에 `"SKU-FREE"`가 있고 `"SKU-POLINKED"`는 **없다** —
    `_reorder_candidate_filter:109`의
    `.exclude(purchase_status="unordered", purchase_orders__isnull=False)` 때문이며,
    `test_po_linked_unordered_item_excluded`
    (`backend/order/tests/test_purchase_orders.py:2197-2215`)가 같은 규칙을 이미 고정한다.
  - 제외 품목 목록의 `results`에도 `"SKU-POLINKED"`가 **없다** — 복구로
    `purchase_status`가 4개 상태를 벗어났기 때문이다.
  - **이 시나리오의 목적**: 이 결과를 "버그"로 보고 누군가 공유 필터를 넓히는 것을 막는
    잠금장치다. 해소는 후속 과제 2다.

## 프론트엔드 — 보류/제외 뷰

### AC-RESTORE-012 — 뷰 전환·상태 라벨·`unordered` 옵션 노출 `[FE]`

Traces: REQ-RESTORE-016, REQ-RESTORE-017, REQ-RESTORE-018

- **Given**: `UnorderedItemsTab.test.tsx:17-27`의 `vi.mock` 팩토리에 신규 조회 훅을
  추가하고 `beforeEach`(`:46-72`)에서 반환값을 세팅한다. 미발주 훅은 `unordered` 항목 1건을,
  제외 조회 훅은 `purchase_status`가 각각 `on_hold`와 `order_cancelled`인 항목 2건을
  반환하도록 mock 한다. 스토어 mock은 `selectedSkus`에 값이 하나 들어 있는 기존
  형태(`:52-57`)를 유지해 일괄 컨트롤이 렌더링되게 한다.
- **When**: (1) 컴포넌트를 렌더링만 한다. (2) 보류/제외 뷰 전환 컨트롤을 클릭한다.
- **Then**:
  - (1) 직후 미발주 목록이 렌더링되어 있고, 이 상태의 일괄 상태 select의 option 값 집합에
    `"unordered"`가 **없다**(기존 `UnorderedItemsTab.tsx:350`의 필터가 그대로 적용된다).
  - (2) 이후 제외 품목 2건이 렌더링되며, 각 행에 그 항목의 상태 한글 라벨(`주문보류`,
    `주문취소` — `purchaseOrderApi.ts:31-40`의 `label` 값)이 보인다.
  - (2) 이후 행별 상태 select의 option 값 집합에 `"unordered"`가 **있다**.
  - (2) 이후 일괄 상태 select의 option 값 집합에도 `"unordered"`가 **있다**.
  - 기존 테스트 2건(`:60` YES24 버튼 순서, `:88` 클릭 시 mutateAsync 인자)이 여전히
    통과한다.

### AC-RESTORE-013 — 선택은 LineItem id 기반이며 전역 SKU 선택과 격리된다 `[FE]`

Traces: REQ-RESTORE-019, REQ-RESTORE-020

- **Given**: 제외 조회 훅이 **같은 SKU `"SKU-DUP"`을 갖되 서로 다른 `order_name`과 서로
  다른 `id`(예: 101, 202)를 가진 항목 2건**과, 다른 SKU를 가진 항목 1건(`id: 303`)을
  반환하도록 mock 한다. 스토어 mock의 `toggleSku` / `selectAllSkus` / `clearSelections`는
  각각 `vi.fn()`이다. 일괄 변경 mutation의 `mutate`도 `vi.fn()`이다.
- **When**: 제외 뷰로 전환한 뒤 `id: 101`과 `id: 202` 두 행의 체크박스를 클릭하고,
  일괄 상태를 `unordered`로 두고 일괄 복구 버튼을 클릭한다. 그 다음 미발주 뷰로 되돌아간다.
- **Then**:
  - 일괄 mutation이 정확히 1회 호출되며 인자의 `ids`가 정확히 `[101, 202]`다
    (순서 무관, 집합 동등). `303`은 포함되지 않는다.
  - **스토어의 `toggleSku`가 한 번도 호출되지 않았다**
    (`expect(toggleSku).not.toHaveBeenCalled()`), `selectAllSkus`와 `clearSelections`도
    마찬가지다. 전역 `selectedSkus` 값은 처음과 동일하다.
  - **판별력**: 구현이 기존 `toggleSku(item.sku)` 경로(`UnorderedItemsTab.tsx:448`, `:454`)를
    재사용하면 두 행이 같은 SKU라 하나만 토글되고 `ids`가 `[101, 202]`가 되지 않으며,
    `toggleSku` assertion도 즉시 실패한다.
  - 미발주 뷰로 되돌아온 뒤 발주 파일 생성 버튼을 클릭하면 `mutateAsync`의 인자 `skus`가
    Given에서 세팅한 전역 `selectedSkus`와 동일하다 — 제외 뷰에서 선택한 `"SKU-DUP"`이
    섞이지 않았다(REQ-RESTORE-020).

### AC-RESTORE-014 — 복구 성공 시 두 목록이 모두 무효화된다 `[FE]`

Traces: REQ-RESTORE-021

- **Given**: `useUpdateLineItemStatus`와 `useBulkUpdateLineItemStatus`의 `onSuccess`가
  호출하는 `queryClient.invalidateQueries`를 관찰할 수 있도록 `useQueryClient`를 mock 하거나,
  두 훅을 실제 `QueryClientProvider` 안에서 렌더링하고 `invalidateQueries`를 spy 한다.
- **When**: 단일 복구와 일괄 복구의 `onSuccess`를 각각 발동시킨다.
- **Then**: 두 경우 모두 `invalidateQueries`가 `QUERY_KEYS.unordered`
  (`usePurchaseOrderQueries.ts:28`의 `['purchase-orders', 'unordered']`)와 **신규 제외 목록
  쿼리 키** 양쪽에 대해 호출된다.
  **판별력**: 현재 구현은 `:109`(단일)와 `:125`(일괄)에서 `QUERY_KEYS.unordered`만
  무효화한다. 신규 키 무효화를 추가하지 않으면 이 시나리오가 실패하고, 실사용에서는 복구한
  항목이 제외 목록에 그대로 남는다.

---

## 품질 게이트 — Definition of Done 매핑

| AC | 테스트 파일 | 테스트 번호 | 검증 대상 REQ |
|---|---|---|---|
| AC-RESTORE-001 `[BE]` | `test_spec_018.py` | T1 | 001, 002 |
| AC-RESTORE-002 `[BE]` | `test_spec_018.py` | T2 | 004 |
| AC-RESTORE-003 `[BE]` | `test_spec_018.py` | T3 | 005 |
| AC-RESTORE-004 `[BE]` | `test_spec_018.py` | T4 | 003, 006, 007 |
| AC-RESTORE-005 `[BE]` | `test_spec_018.py` | T5 | 008 |
| AC-RESTORE-006 `[BE]` | `test_spec_018.py` | T6 | 009, 010 |
| AC-RESTORE-007 `[BE]` | `test_spec_018.py` | T7 | 011 |
| AC-RESTORE-008 `[BE]` | `test_spec_018.py` | T8 | 014 |
| AC-RESTORE-009 `[BE]` | `test_spec_018.py` | T9 | 014 |
| AC-RESTORE-010 `[BE]` | `test_spec_018.py` | T10 | 012, 013, 015 |
| AC-RESTORE-011 `[BE]` | `test_spec_018.py` | T11 | 022 |
| AC-RESTORE-012 `[FE]` | `UnorderedItemsTab.test.tsx` | T12 | 016, 017, 018 |
| AC-RESTORE-013 `[FE]` | `UnorderedItemsTab.test.tsx` | T13 | 019, 020 |
| AC-RESTORE-014 `[FE]` | `usePurchaseOrderQueries.test.tsx` | T14 | 021 |

시나리오로 검증하지 않는 요구사항: **REQ-RESTORE-023**(신규 모델 필드·마이그레이션·감사
로그 부재). 부재를 요구하는 메타 요구사항이라 `plan.md` 완료 조건의
`makemigrations --check --dry-run` + `models.py` diff 게이트로 검증한다.

**추가 회귀 게이트**(신규 테스트가 아니라 기존 스위트의 무수정 통과):

- `backend/order/tests/test_purchase_orders.py::TestUnorderedItemsViewPurchaseStatusFilter`
  (`:2152`) 5건 — 특히 `test_all_non_unordered_statuses_excluded`(`:2217-2234`)
- `backend/order/tests/test_purchase_orders.py::TestUnorderedItemsViewDamagedExchange`
  (`:451`)
- `backend/order/tests/test_daily_review_upload.py` 전량
- `backend/order/tests/test_spec_011.py`, `test_spec_012.py` 전량
  (`Order.status` / `Order.ready_to_ship` 집계 회귀)
- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx`의 기존 2건
  (`:60`, `:73`)
