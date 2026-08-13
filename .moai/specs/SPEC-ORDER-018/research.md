---
id: SPEC-ORDER-018
document: research
version: 1.0.5
status: completed
updated: 2026-08-13
---

# 조사 근거 — SPEC-ORDER-018 보류/제외 품목 발주 대상 복구

이 문서는 `spec.md` / `plan.md` / `acceptance.md`가 인용하는 모든 `file:line` 근거를 모은다.
**모든 인용은 이 세션에서 Read/Grep으로 직접 재확인했다.** SPEC-ORDER-016 `spec.md` v1.0.5
HISTORY 항목이 기록하듯 이 저장소에는 존재하지 않는 파일 경로를 지어낸 SPEC 문서 사례가
있었고 plan-auditor 3회 감사가 그것을 잡지 못했다 — 인용 파일의 실재 여부는 그 에이전트의
점검 항목이 아니다. 따라서 이 SPEC은 선행 SPEC 문서의 인용을 재사용하지 않고 전량 새로
검증했다. 또한 `purchase_order_views.py`의 줄 번호는 SPEC-ORDER-017 구현
(`_process_rack_number_rows` 신설)으로 2100번대 이후가 이동했으므로, SPEC-ORDER-013~017
문서의 줄 번호를 그대로 옮겨 쓰면 안 된다.

---

## 1. 문제의 실체 — 4개 상태는 어떤 화면에서도 보이지 않는다

### 1.1 `LineItem.purchase_status`의 7개 값

`backend/order/models.py:156-167`이 유효한 7개 코드와 한글 라벨을 정의한다.

| 코드 | 라벨 | 재발주 큐 진입 |
|---|---|---|
| `unordered` | 미발주 | O (PurchaseOrder 미연결 시) |
| `on_hold` | 주문보류 | **X** |
| `order_cancelled` | 주문취소 | **X** |
| `other_publisher` | 타출판사 | **X** |
| `cs_required` | CS필요 | **X** |
| `in_stock` | 재고 | X (의도된 종착 상태) |
| `damaged_exchange` | 파손/교환 | O (SPEC-PURCHASE-ORDER-010) |

기본값은 `unordered`다(`models.py:190-194`). `damaged_exchange`는
`models.py:163-166` 주석이 명시하듯 "PurchaseOrder 연결 여부와 무관하게 재발주 큐에
재진입"하기 위해 SPEC-PURCHASE-ORDER-010이 신설한 값이다 — **이미 한 번 "제외 상태에서
큐로 되돌리는" 문제가 별도 상태값 도입으로 해결된 선례가 있다**(§7 참조).

### 1.2 공유 필터 `_reorder_candidate_filter`가 4개 상태를 배제한다

`backend/order/purchase_order_views.py:93`에 정의된 `_reorder_candidate_filter(queryset)`의
본체(`:107-110`)는 다음과 같다.

```python
return (
    queryset.filter(Q(purchase_status="unordered") | Q(purchase_status="damaged_exchange"))
    .exclude(purchase_status="unordered", purchase_orders__isnull=False)
)
```

즉 통과 조건은 **`unordered`(단, 어떤 PurchaseOrder에도 미연결)** 또는 **`damaged_exchange`**
뿐이다. `on_hold`/`order_cancelled`/`cs_required`/`other_publisher`는 첫 `.filter()`에서
탈락한다. docstring(`:94-106`)은 단일 `.exclude()`로 구현한 이유를 설명한다 — 다중값
`purchase_orders` 관계가 JOIN이 아니라 NOT EXISTS 서브쿼리로 평가되어 2개 이상 PurchaseOrder에
연결된 LineItem의 행 중복이 생기지 않으므로 `.distinct()`가 불필요하다는 것이다(경험적 검증
테스트명까지 `:105`에 기록되어 있다).

### 1.3 호출부는 정확히 4곳이다

`Grep`으로 전수 확인한 호출부(주석 언급은 제외):

| 파일:라인 | 호출자 | 성격 |
|---|---|---|
| `purchase_order_views.py:308` | `UnorderedItemsView.get()` | 미발주 현황 목록(읽기) |
| `purchase_order_views.py:567` | `RunComparisonView.post()` | 발주처 자동 비교 실행 |
| `purchase_order_views.py:1071` | `DailyReviewExcelView.get()` | Daily Review 엑셀 생성 |
| `purchase_order_views.py:1410` | `UploadDailyReviewView.post()` | Daily Review 업로드 SKU 배치 매칭 |

`:86-92`의 `@MX:NOTE`도 "Fan-in == 4"로 같은 수를 기록하며, ANCHOR 승격 대신 NOTE로 강등한
이유(파일당 anchor 한도 3, 기존 ANCHOR 4개)를 명시한다. 이 태그의 fan-in 서술은 현재 코드와
일치하므로 이 SPEC에서 갱신할 필요가 없다.

주석에만 등장하고 실제 호출은 아닌 지점: `:377-378`(`ConfirmOrderView` 안의 인라인
`.exclude()`가 같은 예외를 쓰지만 헬퍼를 호출하지 않는다는 설명), `:121`, `:916`,
`backend/order/tests/test_purchase_orders.py:823`.

### 1.4 프론트엔드에서 이 4개 상태는 "쓸 수는 있고 읽을 수는 없다"

`frontend/src/services/purchaseOrderApi.ts:31-40`의 `PURCHASE_STATUS_OPTIONS`는 7개 값을
전부 나열한다. `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx:486`는 이
목록을 **그대로** 행별 select에 렌더링하므로 담당자는 미발주 항목을 `on_hold` 등으로 바꿀 수
있다. 그러나 `:255-257`의 select는 `data.results`의 각 행 위에 있고, `data`는
`useUnorderedItems()`(`:48`)가 부르는 `/api/purchase-orders/unordered/`의 결과다 — 상태를
바꾸는 순간 그 행은 `_reorder_candidate_filter`에서 탈락해 목록에서 사라지고, 되돌릴 UI가
없다.

일괄 변경 select(`:120-131`)는 한술 더 떠 `:126`에서
`PURCHASE_STATUS_OPTIONS.filter((o) => o.value !== 'unordered')`로 **`unordered`를 선택지에서
제거**한다. 미발주 목록에서는 모든 행이 이미 `unordered`이므로 합리적이지만, 보류/제외
목록에서는 이 필터가 정확히 필요한 복구 동작을 막는다.

`purchase_status`를 참조하는 프론트엔드 파일은 전수 조사 결과 5개뿐이다:
`services/purchaseOrderApi.ts`, `types/order.ts`,
`pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`,
`pages/PurchaseOrders/tabs/ConfirmOrderTab.tsx`,
`pages/OutboundPage/logisticsStatusLabels.ts`. 이 중 서버에 단일 항목 상태 변경을 보내는
곳은 `UnorderedItemsTab.tsx:118-120`(`handleStatusChange`) 하나다. `ConfirmOrderTab.tsx:47-51`의
`handlePurchaseStatusChange`는 로컬 state만 갱신하고 발주 확정 요청 본문에 실어 보낸다.

### 1.5 다른 화면에서도 보이지 않는다

- `LineItemRackNumberSummaryView`(`purchase_order_views.py:2804`)는
  `:2399`에서 `.exclude(purchase_status="order_cancelled")` 한다. docstring `:2373-2374`가
  이를 명시한다.
- `OutboundForceCandidateView`(`:2963`)도 `:3009`에서 같은 제외를 한다.
- 품목 노트 페이지(`frontend/src/pages/LineItemNotesPage.tsx`)는 노트 중심이며
  `purchase_status`를 **표시하지도 쓰지도 않는다**(전수 grep에서 미검출). 서버측
  `LineItemNoteUnresolvedSerializer`(`backend/order/serializers.py:79-97`)의 필드 목록에도
  `purchase_status`가 없다. 따라서 이 페이지는 대안이 될 수 없다.

### 1.6 운영 데이터로 확인한 규모 (2026-08-13 측정)

원격 MySQL에 대해 읽기 전용 집계를 1회 실행한 결과:

| purchase_status | 건수 |
|---|---|
| `other_publisher` | 80 |
| `order_cancelled` | 79 |
| `cs_required` | 49 |
| `on_hold` | 17 |
| **합계** | **225** |

사용자가 지목한 구체 사례도 그대로 확인했다 — `LineItem` id=15083, `Order.name`=`#37636`,
`sku`=`9791199783218`, `purchase_status`=`order_cancelled`, `rack_number`=`M4`,
`logistics_status`=`not_shipped`, 대응 `Refund` 행 0건. 이 품목은 렉번호 M4를 달고 물리적으로
창고에 있으면서도 §1.5의 제외 규칙 때문에 렉번호 요약에서 사라졌고, §1.2 때문에 미발주
목록에도 없다.

이 225라는 규모는 §5의 페이지네이션 결정과 §6의 성능 판단의 전제다.

---

## 2. 상태가 붙는 경로 — 어디서 4개 상태로 들어가는가

### 2.1 수동 변경 (단일)

`LineItemStatusUpdateView`(`purchase_order_views.py:2302`), PATCH
`/api/purchase-orders/line-items/<pk>/status/`(docstring `:1865`, URL 등록
`backend/order/urls.py:81`).

- `:1876-1880` — `LineItem.objects.get(pk=pk)`, 없으면 404. **pk로 직접 조회하므로 대상
  LineItem의 현재 `purchase_status`에 아무 제약이 없다** — 4개 제외 상태의 품목도 그대로
  받는다.
- `:1882-1888` — 값이 `PURCHASE_STATUS_CHOICES`의 코드 중 하나인지 검사, 아니면 400.
  `unordered`도 당연히 유효한 선택지다.
- `:1890-1891` — `li.save(update_fields=["purchase_status"])`. **쓰기 필드는 하나뿐이다.**
- `:1892` — `_recompute_order_aggregates([li.order_id])`.
- `:1893-1900` — 200 + `{"id", "purchase_status", "sku"}`.

즉 **복구에 필요한 백엔드 쓰기 능력은 이미 전부 존재한다.** 없는 것은 이 엔드포인트에
도달할 UI 경로뿐이다.

### 2.2 수동 변경 (일괄)

`LineItemBulkStatusUpdateView`(`:1908`), PATCH
`/api/purchase-orders/line-items/bulk-status/`(docstring `:1910-1913`, URL 등록
`urls.py:80` — `<int:pk>/status/`보다 **먼저** 등록되어야 한다는 주석이 `urls.py:79`에 있다).

- 본문은 `{"ids": [int, ...], "purchase_status": str}` — **SKU가 아니라 LineItem id 목록**을
  받는다(`:1923`).
- `:1928-1937` — 빈 `ids` → 400, 유효하지 않은 상태 → 400.
- `:1939-1946` — `filter(pk__in=ids)`로 실재 id 집합과 `missing_ids`를 계산하고,
  `affected_order_ids`를 `.update()` **이전에** 수집한다(주석 `:1943-1945`가
  `QuerySet.update()`가 인스턴스를 반환하지 않는 제약을 근거로 든다).
- `:1948` — `existing.update(purchase_status=purchase_status_value)` (단일 UPDATE).
- `:1950` — `_recompute_order_aggregates(affected_order_ids)` (배치 1회).
- `:1952-1958` — 200 + `{"updated_count", "missing_ids"}`.

여기에도 현재 상태에 대한 제약이 없다. 프론트엔드 래퍼는
`services/purchaseOrderApi.ts:170-179`(`bulkUpdateLineItemStatus`)이며, 훅은
`hooks/usePurchaseOrderQueries.ts:119-135`(`useBulkUpdateLineItemStatus`)다. 그 위
`:134-135`에 `@MX:WARN`/`@MX:REASON`이 붙어 있다 — 부분 성공(`missing_ids`)을 사용자에게
노출하지 않으면 조용한 데이터 손실이 된다는 경고이며, `:126-130`이 실제로 toast로 이를
노출한다.

### 2.3 Daily Review 업로드 (자동, 노트 동반)

`UploadDailyReviewView`(`:1229`)는 업로드 행의 '선택' 열이 발주처가 아니라 CS 계열 라벨일 때
상태를 바꾼다. `backend/order/excel_utils.py:614-622`의 `_NOTE_TYPE_STATUS_MAP`:

```python
_NOTE_TYPE_STATUS_MAP: dict[str, str] = {
    "주문취소": "order_cancelled",
    "주문보류": "on_hold",
    "CS필요": "cs_required",
    "타출판사": "other_publisher",
    "파손/교환": "damaged_exchange",
}
```

(`:613`의 주석이 "'선택' 열의 CS 계열 값을 purchase_status 코드로 매핑"이라고 설명한다.
라벨 감지는 `excel_utils.py:876-877`.)

뷰 쪽에서는 `purchase_order_views.py:1633`가 `note_type`을 읽고, `:1644-1649`이
`_NOTE_TYPE_STATUS_MAP[note_type]`으로 상태를 세팅하며, `:1459-1466`이 **같은 트랜잭션에서
`LineItemNote`를 생성**한다. `_NOTE_TYPE_STATUS_MAP`은 `:50`에서 임포트된다.

**이것이 §1.6의 225건을 만든 지배적 경로일 가능성이 높다** — 그리고 4개 제외 상태의 품목
상당수가 미해결 `LineItemNote`를 동반한다는 뜻이기도 하다. 복구 시 노트를 어떻게 할지(§4)가
실질적 설계 쟁점인 이유다.

주의: `:1410`이 이 뷰의 SKU 배치 조회이며 `_reorder_candidate_filter`를 통과시킨다(주석
`:1404-1406`이 REQ-PO9-004의 N+1 제거 근거를 설명). 즉 **이미 제외 상태인 품목은 이 업로드의
매칭 대상이 아니다** — 한 번 제외되면 Daily Review 업로드로도 되돌릴 수 없다.

---

## 3. 복구가 Order 집계에 미치는 영향

`_recompute_order_aggregates(order_ids)`(`purchase_order_views.py:123`, `@MX:NOTE`는
`:113-122`에 있고 fan-in 8을 기록)는 §2.1/§2.2 두 경로가 쓰기 직후 반드시 호출한다.

- `:150-152` — `order_ids`가 비면 쿼리 0건으로 즉시 반환.
- `:155-158` — `order_id__in` + `sku__isnull=False`인 LineItem의
  `(order_id, logistics_status, purchase_status)` 3튜플을 **1회 SELECT**로 읽어 파이썬에서
  그룹핑.
- `:188-195` — Order 집계 2개를 `Case/When`으로 **1회 UPDATE**.

두 필드의 계산 규칙은 다음과 같다.

### 3.1 `Order.status` — `purchase_status`와 무관하다

`:167-173`:

```python
if not items:
    new_status = None
else:
    statuses = {logistics_status for logistics_status, _ in items}
    new_status = next(iter(statuses)) if len(statuses) == 1 else "partial"
```

집합에 들어가는 것은 `logistics_status`뿐이다. **따라서 `purchase_status`를 무엇으로 바꾸든
`Order.status`는 변하지 않는다.** (해당 LineItem의 `sku`가 NULL이 아닌 한 그 LineItem은
변경 전에도 후에도 동일하게 집계에 포함된다.)

### 3.2 `Order.ready_to_ship` — 4개 상태 중 2개가 영향을 준다

`:176-185`:

```python
non_cancelled = [it for it in (items or []) if it[1] != "order_cancelled"]
if not non_cancelled:
    ready_to_ship = None
elif any(purchase_status == "cs_required" for _, purchase_status in non_cancelled):
    ready_to_ship = False
else:
    ready_to_ship = all(
        logistics_status == "received" or purchase_status == "in_stock"
        for logistics_status, purchase_status in non_cancelled
    )
```

docstring `:130-136`이 같은 규칙을 SPEC-ORDER-012 REQ-RTS-002/003/003a/004로 명시한다.

복구 방향별 귀결:

| 복구 전 상태 | `ready_to_ship`에 대한 효과 |
|---|---|
| `order_cancelled` → `unordered` | `:176`의 제외에서 **빠져나와 집계에 재진입**한다. 그 Order의 유일한 품목이었다면 `None` → `True`/`False`로 바뀐다. 재진입한 품목은 `logistics_status`가 보통 `not_shipped`(모델 기본값, `models.py:204-208`)이고 `purchase_status`도 `in_stock`이 아니므로 `:182-185`의 `all(...)`이 거짓이 되어 **`True`였던 Order가 `False`로 뒤집힐 수 있다**. |
| `cs_required` → `unordered` | `:179-180`의 `any(cs_required)` 강제 `False` 조건이 사라진다. 다른 품목이 조건을 만족하면 `False` → `True`로 **올라갈 수 있다**. |
| `on_hold` → `unordered` | 두 규칙 어디에도 등장하지 않는다. 재계산은 실행되지만 **결과값은 동일**하다. |
| `other_publisher` → `unordered` | 위와 동일. **결과값 동일.** |

이는 이 SPEC이 새로 만드는 동작이 아니라 기존 쓰기 엔드포인트가 이미 하는 동작이다. 다만
"보이지 않던 품목을 되살린다"는 이 SPEC의 성격상 `True` → `False` 뒤집힘이 담당자에게는
놀라운 결과일 수 있으므로 `spec.md`가 이를 명시적 요구사항과 인수 기준으로 고정한다.

---

## 4. `LineItemNote`와의 관계

`LineItemNote`(`backend/order/models.py:238`)는 `line_item` FK(`:261-263`,
`related_name="notes"`), `is_resolved`(`:273`, 기본 `False`), `note_type`(`:280-285`) 필드를
갖는다. `NOTE_TYPE_CHOICES`(`:249-259`)는 `주문취소`/`주문보류`/`CS필요`/`타출판사` 등 §2.3의
매핑 키와 같은 한글 라벨을 포함한다.

노트 해결은 **전용 엔드포인트**가 담당한다:

- `LineItemNoteListCreateView` — `backend/order/views.py:251`
- `LineItemNoteUnresolvedListView` — `views.py:269` (미해결 목록)
- `LineItemNoteResolveView` — `views.py:285`, PATCH
  `/api/orders/line-item-notes/{pk}/resolve/`(`urls.py:161`), 응답은 `views.py:295`의
  `{"is_resolved": True}`
- `LineItemNoteExportView` — `views.py:298`, `:313-317`이 `is_resolved=False` +
  `note_type="타출판사"` 미해결 노트를 엑셀로 내보낸다

**핵심 관찰**: 상태 → 노트 방향의 결합은 존재하지만(§2.3의 `:1453-1466`, 상태 변경과 노트
생성을 함께 수행) **역방향은 존재하지 않는다**. `LineItemStatusUpdateView`(`:1876-1900`)와
`LineItemBulkStatusUpdateView`(`:1922-1958`) 어느 쪽도 `LineItemNote`를 조회·생성·수정하지
않는다. 복구 시 노트를 자동 해결하려면 이 두 엔드포인트의 동작을 바꿔야 하고, 그 두
엔드포인트는 기존 미발주 탭 흐름(`UnorderedItemsTab.tsx:118-120`, `:132-139`)이 공유한다 —
`spec.md` 설계 결정 E가 이를 근거로 자동 해결을 범위 밖으로 둔다.

---

## 5. 응답 형태·페이지네이션 관례

### 5.1 `UnorderedItemsView`는 페이지네이션하지 않는다

`purchase_order_views.py:284`의 `UnorderedItemsView`:

- `:259-260` — `authentication_classes = [JWTAuthentication]`,
  `permission_classes = [IsAuthenticated]`.
- `:263-272` — `Refund`를 `(order_id, line_item_id)`로 묶어 `total`을 뽑는 상관 서브쿼리.
  주석은 없지만 `LineItemRackNumberSummaryView`의 같은 서브쿼리에 달린 주석(`:2384-2386`)이
  "Refund 행은 로컬 LineItem pk가 아니라 Shopify의 `line_item_id`를 들고 있어 두 키가 모두
  필요하다"고 설명한다.
- `:274-284` — `_reorder_candidate_filter(LineItem.objects.filter(sku__isnull=False))`에
  `refunded_qty` annotate, `.select_related("order")`,
  `.order_by("-order__shopify_created_at")`.
- `:291-294` — 파이썬 루프에서 `net_qty = max((li.quantity or 0) - li.refunded_qty, 0)`,
  `net_qty == 0`이면 `continue`(주석: "Fully refunded — exclude from unordered list").
- `:296` — `order_name = order.name or (f"#{order.order_number}" if order.order_number else None)`.
- `:297-308` — 결과 dict 필드: `id`, `order_name`, `sku`, `title`, `vendor`, `quantity`(순
  수량), `purchase_status`, `auto_distributor`.
- `:314` — `return Response({"count": len(results), "results": results})`.

**`:314`가 결정적이다** — DRF 페이지네이션을 거치지 않고 `count`/`results` 봉투를 직접
만든다. `next`/`previous` 키가 없다.

`PageNumberPagination`은 `:43`에서 임포트되지만 파일 전체에서 이를 상속하는 클래스는
`PurchaseOrderPagination`(`:3428-3429`, `page_size = 50`) 하나이고, 그것은
`PurchaseOrderListView`(`:3503`)의 PurchaseOrder 목록 전용이다. 프론트엔드에서도
`PaginatedResponse<T>`(`services/purchaseOrderApi.ts:76-81`)는
`getPurchaseOrders`(`:181-193`)에만 쓰이고, `getUnorderedItems`(`:105-108`)의 반환 타입은
`{ count: number; results: UnorderedItem[] }`다.

**결론**: LineItem 목록 계열 읽기 엔드포인트의 이 저장소 관례는 **비페이지네이션**이다.
§1.6의 실측 225건은 미발주 목록이 이미 감당하는 규모와 같은 자릿수다.

### 5.2 환불 넷팅에는 두 가지 관례가 있다

| 관례 | 위치 | 동작 |
|---|---|---|
| 무조건 스킵 | `UnorderedItemsView:293-294` | `net_qty == 0`이면 무조건 제외 — **환불이 0건이고 `quantity`가 NULL/0인 품목도 사라진다** |
| 가드된 스킵 | `LineItemRackNumberSummaryView:2415` | `if li.refunded_qty and net_qty == 0:`일 때만 제외 |

후자에는 `:2416-2421`에 그 이유를 적은 긴 주석이 붙어 있다: "`refunded_qty`에 가드를 걸어
환불이 없는데 `quantity`가 NULL/0인 LineItem은 기존 동작(목록에 표시, 0으로 집계)을 유지하게
했다 — 그 경우는 취소가 아니라 데이터 결손이다." 이쪽이 더 나중에 쓰인, 더 신중한 관례다.

### 5.3 결정적 정렬 관례

`OutboundForceCandidateView:3011`의 `.order_by("order_id", "pk")`에는 `:3003-3006`에 근거
주석이 있다 — "결정적이고 반복 가능한 순서를 주며(REQ-FORCE-006) MySQL의 무정렬 스캔 반환
순서에 의존하지 않는다." `LineItemRackNumberSummaryView:2407`도
`.order_by("rack_number", "order__order_number")`로 명시 정렬한다.
`UnorderedItemsView:283`의 `.order_by("-order__shopify_created_at")`은 단일 키라
`shopify_created_at` 동률 시 순서가 비결정적이다.

---

## 6. 아키텍처 선례 — "기존 경로를 넓히지 않고 별도 읽기 경로를 만든다"

`OutboundForceCandidateView`(`purchase_order_views.py:3402`)가 **정확히 같은 구조적 문제를
이미 이 방식으로 풀었다.** docstring `:3412-3417`:

> Modelled on `LineItemRackNumberSummaryView` above as the cross-order read-only structural
> precedent and on `_process_outbound_rows`'s `name__in` batched order lookup + Python
> grouping as the batching precedent — **but this view is fully separate code, so it adds
> zero queries to the two existing outbound endpoints** (REQ-FORCE-018, 설계 결정 A).

구현 특징:

- `:2981-2982` — 표준 인증 관례(`JWTAuthentication` + `IsAuthenticated`).
- `:2991-2996` — 빈 입력은 오류가 아니라 빈 결과이며 **쿼리를 하나도 쓰지 않는다**.
- `:3002` — `if order_ids:` 가드로 대상이 없으면 후속 조회를 건너뛴다.
- `:3007-3012` — `.exclude(purchase_status="order_cancelled")`,
  `.exclude(sku__isnull=True)`, `.order_by("order_id", "pk")`.
- `:3032-3043` — 요청 순서를 그대로 보존하는 `results` 조립.
- URL은 `urls.py:128-132`에 등록되어 있고 `:130-134`의 주석이 정적 세그먼트라
  `<int:pk>` 패턴에 가려지지 않는 이유를 설명한다.

`urls.py:157`의 `path("purchase-orders/", PurchaseOrderListView.as_view(), ...)`가 가장 마지막에
오고 `:64`에 "more specific paths must come before the generic list"라는 주석이 있다.
`purchase-orders/` 아래에 `<int:pk>` 패턴은 존재하지 않으므로 새 정적 경로를 `:67`
(`purchase-orders/unordered/`) 옆에 두면 충돌이 없다.

---

## 7. "제외 상태에서 큐로 되돌리기"의 기존 선례 2건

### 7.1 `damaged_exchange` — 새 상태값으로 우회 (SPEC-PURCHASE-ORDER-010)

`models.py:163-166`이 기록하듯 `damaged_exchange`는 PurchaseOrder 연결 여부와 무관하게 큐에
재진입하도록 `_reorder_candidate_filter`의 두 번째 OR 항으로 들어갔다(`:108`). 이 SPEC은 이
접근을 **채택하지 않는다** — 4개 상태의 배제는 의도된 계약이고(§8의 테스트가 이를 고정),
필터를 넓히면 4개 호출부 전부의 동작이 바뀐다.

### 7.2 발주 확정 시 자동 리셋 (REQ-DMG-006)

`ConfirmOrderView`(`:841`) 안 `:975-984`:

```python
# REQ-DMG-006: auto-reset damaged_exchange -> unordered for this
# confirmation batch, applied before the explicit purchase_status
# override below so a client-supplied value always wins (REQ-CON-022).
damaged_exchange_reset = False
for li in unordered_lis:
    if li.purchase_status == "damaged_exchange":
        li.purchase_status = "unordered"
        damaged_exchange_reset = True
if damaged_exchange_reset:
    update_fields.append("purchase_status")
```

이어 `:986-991`이 클라이언트가 명시한 `purchase_status`로 덮어쓴다. 같은 리셋이
`UploadDailyReviewView`(`:1568-1569`)에도 있다.

**시사점**: "특정 상태를 `unordered`로 되돌린다"는 동작 자체는 이 코드베이스에 이미 두 번
구현되어 있고, 둘 다 `purchase_status` 한 필드만 건드리며 감사 로그를 남기지 않는다. 이
SPEC의 복구도 같은 관례를 따르면 된다.

---

## 8. 회귀 방지 — 반드시 통과 상태를 유지해야 할 기존 테스트

`backend/order/tests/test_purchase_orders.py`:

- `:2152-2153` `TestUnorderedItemsViewPurchaseStatusFilter` — REQ-PO4-003/004.
  - `:2155-2169` `test_on_hold_item_excluded_from_unordered` — `on_hold` 품목이 미발주
    목록에 없음.
  - `:2171-2185` `test_unordered_item_included`.
  - `:2187-2195` `test_response_includes_purchase_status_field`.
  - `:2197-2215` `test_po_linked_unordered_item_excluded` — **`unordered`이지만
    PurchaseOrder에 연결된 품목은 제외됨.** §9의 알려진 한계의 근거다.
  - `:2217-2234` `test_all_non_unordered_statuses_excluded` — `on_hold`,
    `order_cancelled`, `other_publisher`, `cs_required`, `in_stock` 5개가 전부 제외됨을
    한 번에 고정한다. **이 SPEC이 절대 깨뜨려서는 안 되는 테스트다.**
- `:451` `TestUnorderedItemsViewDamagedExchange` — `damaged_exchange` 계열.
  - `:487` `test_other_non_unordered_non_damaged_statuses_still_excluded`.
- `:1189` `test_unordered_unlinked_still_included_regression`.

`backend/order/tests/test_spec_011.py:423` `test_unordered_purchase_status_excluded`도
같은 계열이다.

테스트 인프라 관례:

- URL 상수: `test_purchase_orders.py:50` `UNORDERED_URL = "/api/purchase-orders/unordered/"`,
  `:59` `LINE_ITEM_STATUS_URL`, `:59` `BULK_STATUS_URL`.
- 픽스처: `test_purchase_orders.py:72`(`user`), `:77`(`auth_client`), `:85`(`anon_client`),
  헬퍼 `:90`(`_make_order`), `:97`(`_make_line_item`).
- SPEC 전용 스위트 관례: `test_spec_015.py:1-24`가 모듈 docstring에 `Coverage targets:` T1~Tn과
  REQ/AC 매핑을 적는다. `test_spec_016.py:1-40`도 동일. 같은 파일의
  `:34`(`from django.test.utils import CaptureQueriesContext`), `:46`(`_make_order`),
  `:50`(`_make_line_item`), `:611-625`(`user`/`auth_client`/`anon_client` 픽스처)가 재사용
  가능한 기법이다.
- 공용 conftest: `backend/conftest.py`는 `api_client` 픽스처 하나만 제공하므로, 인증 픽스처는
  스위트마다 자체 정의하는 것이 관례다.

프론트엔드:

- `UnorderedItemsTab.test.tsx:17-27` — `usePurchaseOrderQueries`의 훅 4개와
  `usePurchaseOrderStore`를 통째로 `vi.mock`한다.
- `:31-57` — `beforeEach`에서 각 훅의 반환값을 세팅. 새 훅을 추가하면 **이 mock 팩토리에도
  추가해야 하며, 그렇지 않으면 기존 2개 테스트(`:79`, `:92`)가 깨진다.**

---

## 9. 프론트엔드 선택 상태 — 가장 큰 함정

`frontend/src/stores/usePurchaseOrderStore.ts`:

- `:4-5` — `// SKUs selected (checked) in UnorderedItemsTab` / `selectedSkus: string[]`.
- `:12-13` — `@MX:ANCHOR` / `@MX:REASON`: "Fan-in >= 3 — UnorderedItemsTab and
  VendorFileUploadTab use this store".
- `:18-27` — `toggleSku`, `selectAllSkus`, `clearSelections`.

`UnorderedItemsTab.tsx`에서의 사용:

- `:45` — 스토어에서 4개를 구조 분해.
- `:49-54` — `allSkus`는 `new Set(...map(item => item.sku))`, `checkedRowCount`와
  `selectedQuantityTotal`은 `selectedSkus.includes(item.sku)`로 계산.
- `:220-225` / `:227-234` — 행 클릭과 체크박스가 **`toggleSku(item.sku)`** 를 호출한다.
- `:69-72` — 일괄 상태 변경은 선택된 SKU를 **LineItem id로 다시 매핑**한다:
  `data?.results.filter(item => selectedSkus.includes(item.sku)).map(item => item.id)`.
- `:86-102` — 발주 파일 생성은 `selectedSkus`를 **그대로** 서버로 보낸다(`:90`).

두 가지 결론:

1. **선택 키가 SKU다.** 같은 SKU가 서로 다른 주문에 서로 다른 제외 상태로 존재하면(§1.6의
   225건에서 충분히 있을 수 있다) SKU 하나를 체크하는 것으로 의도치 않은 행까지 선택된다.
   보류/제외 뷰는 선택 키를 LineItem id로 잡아야 한다.
2. **스토어가 전역이고 탭 간 공유된다.** 보류/제외 뷰의 선택이 `selectedSkus`에 들어가면
   `:90`의 발주 파일 생성이 그 SKU를 넘겨받는다. 즉 보류 품목을 선택한 채 뷰를 전환하면
   제외된 품목의 SKU로 발주 파일이 생성될 수 있다. 뷰 로컬 state로 분리해야 한다.

`hooks/usePurchaseOrderQueries.ts`의 캐시 무효화:

- `:26-31` — `QUERY_KEYS.unordered = ['purchase-orders', 'unordered']`.
- `:33-38` — `useUnorderedItems`.
- `:109`(단일) / `:125`(일괄) — 성공 시 `QUERY_KEYS.unordered`만 무효화한다. **새 목록의
  쿼리 키를 추가하면 두 훅 모두에 무효화를 추가해야 한다** — 그렇지 않으면 복구 후 원본
  목록에서 항목이 사라지지 않는다.

---

## 10. 알려진 한계의 근거 — PurchaseOrder에 연결된 품목

`_reorder_candidate_filter`(`:107-110`)의 `.exclude(purchase_status="unordered",
purchase_orders__isnull=False)`는 `unordered`인 품목 중 **어떤 PurchaseOrder에라도 연결된
것**을 배제한다. `test_po_linked_unordered_item_excluded`
(`test_purchase_orders.py:2197-2215`)가 이를 고정한다.

따라서: 어떤 품목이 발주 확정(→ PurchaseOrder 연결)된 뒤 `order_cancelled`로 바뀌었다면, 이
SPEC의 복구로 `unordered`가 되어도 **미발주 목록에 나타나지 않는다.** 복구는 성공했지만
결과가 보이지 않는, 담당자 입장에서 가장 혼란스러운 시나리오다.

우회 수단이 코드베이스에 이미 있다 — `damaged_exchange`(§7.1)는 연결 여부와 무관하게
통과한다. 그러나 그 값의 의미는 "파손/교환"이라 보류 복구에 전용하면 의미가 왜곡된다.
`spec.md`는 이를 해결하지 않고 **관측 가능한 한계로 고정**하며(REQ-RESTORE-021,
AC-RESTORE-011) 후속 과제로 넘긴다.

---

## 11. 이 SPEC이 손대지 않는 것들 (확인 완료)

| 대상 | 확인 근거 |
|---|---|
| `_reorder_candidate_filter` 본체 | `:93-110` — 변경 없음, 4개 호출부(§1.3) 전부 무영향 |
| `UploadDailyReviewView`의 SKU 배치 매칭 | `:1410` — 이 필터를 그대로 통과, 변경 없음 |
| `LineItemStatusUpdateView` / `LineItemBulkStatusUpdateView` | `:1863-1900` / `:1908-1958` — 그대로 재사용, 코드 변경 없음 |
| `LineItem` / `LineItemNote` / `Order` 모델 | `models.py` — 신규 필드·마이그레이션 없음 |
| `LineItemNote` 해결 경로 | `views.py:285` — 이 SPEC에서 호출하지 않음 |
| `excel_utils.py` | 파서·매핑 변경 없음 |
| `PURCHASE_STATUS_OPTIONS` | `purchaseOrderApi.ts:31-40` — 7개 값 그대로, 신규 값 없음 |
| `usePurchaseOrderStore` | `usePurchaseOrderStore.ts:1-28` — 변경 없음(§9의 이유로 새 선택은 뷰 로컬 state) |
| `ConfirmOrderTab` / `LineItemNotesPage` | 변경 없음 |

---

## 12. 미해결 질문 (구현 시 판단)

1. 신규 엔드포인트 경로명 — `plan.md`는 `purchase-orders/excluded-items/`를 권고하지만
   `urls.py:64`의 "구체적 경로 먼저" 규칙만 지키면 명칭은 구현 재량이다.
2. 뷰 전환 UI의 형태(토글 버튼 / 세그먼트 컨트롤 / 서브탭) — `spec.md`는 관측 가능한
   요구(전환 가능, 기본은 미발주)만 규정한다.
3. 제외 상태별 클라이언트 필터 제공 여부 — 서버는 4개 상태를 전부 반환하므로 필요하면
   클라이언트에서 필터링할 수 있다. `spec.md` Exclusions에 서버측 필터 파라미터를 범위 밖으로
   둔다.
