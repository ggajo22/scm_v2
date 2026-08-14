---
id: SPEC-PURCHASE-ORDER-011
document: plan
version: 1.3.1
status: draft
updated: 2026-08-14
---

# 구현 계획 — SPEC-PURCHASE-ORDER-011 파손 교환 신청 페이지

`spec.md`의 요구사항(REQ-DEX-001~013, 하위 항목 포함, v1.3.0 기준 총 24개 REQ 항목)을 구현하기 위한 파일별 변경 계획, 기술적 접근, 마일스톤, 리스크, 실행 제약사항을 정리한다.

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M1 (High) — 데이터 모델**: `LineItem.damaged_quantity` 필드 추가 + 마이그레이션 작성. 이후 모든 마일스톤의 선행 조건.
- **M1.5 (High, v1.3.0에서 D22 반영 재정정) — `_recompute_order_aggregates` 기존 특성화 테스트 확인(신규 작성 아님)**: `backend/order/tests/test_spec_012.py`의 `TestRecomputeOrderAggregatesReadyToShip` 클래스(L168-285, 9개 테스트)가 이미 `ready_to_ship`의 세 가지 기존 분기 — (1) 추적 가능 LineItem 0건→`None`, (2) `cs_required` 단락, (3) `all(received/in_stock)` 판정(`purchase_order_views.py:175-186`) — 전부를 특성화하고 있다. 이 마일스톤은 새 스위트를 작성하지 않고, `damaged_exchange` 단락 분기 추가 전후로 이 9개 테스트가 그대로 통과하는지만 확인한다(사전 확인: 이 파일에 `damaged_exchange` 문자열이 전혀 없어 영향 없음이 예상됨). M4.5의 선행 조건.
- **M2 (High) — 백엔드: 검색 엔드포인트**: ISBN 정확 일치 검색 뷰 — 미출고 필터 재사용, 부모 Order 집계(전체 출고 수량) 배치 조회.
- **M3 (High) — 백엔드: 파손 접수 엔드포인트**: 상태 전환(재접수 시 덮어쓰기) + `damaged_quantity` 저장 + `LineItemNote` 자동 생성(`author`=접수자) + `_recompute_order_aggregates` 호출을 단일 트랜잭션으로 처리.
- **M4 (High) — 백엔드: 재발주 큐 수량 보정**: `UnorderedItemsView.get()`의 `net_qty` 계산 분기 수정(REQ-DEX-012/012a).
- **M4.5 (High, v1.2.0 신규) — `_recompute_order_aggregates`의 `ready_to_ship` 단락 확장**: M1.5의 기존 특성화 테스트가 통과하는 상태에서, `damaged_exchange`를 `cs_required`와 동일한 자리에서 단락 처리하는 분기를 추가(REQ-DEX-009c). `status` 계산 규칙이 변경되지 않음을 검증하되, `status`/`ready_to_ship` 두 컬럼이 같은 UPDATE로 함께 쓰인다는 사실 자체는 회귀 대상이 아님에 유의(REQ-DEX-009d, D16). fan-in 8→9(신규 파손 접수 뷰) 반영 — 함수 상단 주석(L113-122) 갱신.
- **M4.6 (High, v1.3.0 신규, D13) — `ready_to_ship` 백필 마이그레이션**: M4.5로 확정된 새 규칙을 기존 Order 전체에 소급 적용하는 1회성 데이터 마이그레이션 작성(REQ-DEX-013/013a) — `0033_backfill_order_ready_to_ship.py`(SPEC-ORDER-012 REQ-RTS-006)를 선례로 그 형태를 그대로 따른다: 마이그레이션 파일은 `purchase_order_views`를 import하지 않고 규칙을 역사적 모델(historical model)로 재구현하며(0031/0033과 동일한 관례), 단일 SELECT로 모든 추적 가능 LineItem의 `(order_id, purchase_status, logistics_status)`를 가져와 Python에서 Order별로 그룹화한 뒤 `bulk_update()` 1회로 반영한다. M4.5 완료 후 착수(새 규칙이 확정되어야 백필 로직을 작성할 수 있음).
- **M5 (High) — 백엔드 테스트**: 검색/접수/재발주 수량 보정/`ready_to_ship` 단락/백필 마이그레이션 전 REQ에 대한 pytest 작성 — 원격 MySQL 테스트 DB 동시 실행 금지 준수(아래 실행 제약사항 참조).
- **M6 (Medium) — 프론트엔드**: 서비스 함수 + 훅 + 신규 페이지(ISBN 검색 폼 + 결과 테이블 + 행별 파손 접수 컨트롤) + 사이드바/라우터 등록.
- **M7 (Medium) — 프론트엔드 테스트 + 회귀 확인**: 신규 페이지 테스트 작성 + `UnorderedItemsView` 소비 화면(발주 관리 페이지), `OrderDetailPage.tsx`(`ready_to_ship` 배지), `OrderResyncView` 소비 경로(v1.3.0 신규, D15) 기존 테스트 재실행으로 무영향/의도된 변경 확인. `test_daily_review_upload.py`(v1.3.0 신규, D17 — `damaged_exchange` 행이 `_recompute_order_aggregates`를 실제로 경유하는 유일한 기존 스위트)도 함께 실행.
- **M8 (Low) — 문서 동기화**: `product.md` 기능 목록 갱신, SPEC 상태를 `completed`로 전이.

## 파일별 변경 계획

### 백엔드

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| MODIFY | `backend/order/models.py` (`LineItem` 클래스, `PURCHASE_STATUS_CHOICES` 및 `purchase_status` 필드 인근, L156~194) | `damaged_quantity = models.IntegerField(default=0)` 추가. SPEC-PURCHASE-ORDER-011 참조 주석 포함, 결정 A(환불 차감 적용)·REQ-DEX-012a(non-damaged_exchange 행에서는 의미 없음) 요지를 주석으로 남긴다. |
| NEW | `backend/order/migrations/0037_lineitem_damaged_quantity.py` (파일명·번호는 Run 단계에서 최신 상태 재확인 필요 — 2026-08-14 기준 최신 마이그레이션은 `0036_order_name_index.py`) | 위 필드 추가 마이그레이션. 데이터 백필 불필요(기본값 0, 기존 행은 신규 컬럼에 기본값 적용). |
| MODIFY | `backend/order/purchase_order_views.py` | 신규 뷰 2개 추가: (1) ISBN 검색 뷰(GET, `sku` 쿼리 파라미터, REQ-DEX-004~007) — 부모 Order 집계는 배치 쿼리로 처리(아래 "기술적 접근" 참조), (2) 파손 접수 뷰(POST, `<int:pk>`, REQ-DEX-008~011) — `LineItemStatusUpdateView`(L1863-1900) 구조를 참조하되 `damaged_quantity` 저장(재접수 시 덮어쓰기, REQ-DEX-009b) + `LineItemNote.objects.create(...)`(`author`=요청 사용자, REQ-DEX-010) + `_recompute_order_aggregates([li.order_id])`를 하나의 뷰 안에서 원자적으로 수행. `UnorderedItemsView.get()`(L251-314)의 `net_qty` 계산(L292) 수정 — `damaged_exchange` 행은 `damaged_quantity`를 기준으로, 그 외는 기존대로 `quantity`를 기준으로 사용(REQ-DEX-012/012a). `RunComparisonView`/`DailyReviewExcelView`/`UploadDailyReviewView`/`GenerateOrderFileView`/`VendorComparisonView`는 변경하지 않는다(REQ-DEX-012b, v1.2.0에서 5개 지점으로 정정 — 아래 "재발주 큐 수량 보정" 절 참조). `ConfirmOrderView`도 변경하지 않되 구조적으로 다른 이유(REQ-DEX-012c)다. |
| **[MODIFY] DELTA** | `backend/order/purchase_order_views.py` — `_recompute_order_aggregates`(L113-195, fan-in 8→9) | **v1.2.0 신규, 범위 확장(결정 E)**: `ready_to_ship` 계산부(L175-186)에 `damaged_exchange` 단락 분기 추가 — 기존 `cs_required` 단락(L179-180) 직후, `all(...)` 판정(L182-185) 이전에 "trackable 비취소 집합에 `damaged_exchange`가 하나라도 있으면 `ready_to_ship=False`"를 삽입(REQ-DEX-009c). `status` 계산부(L167-173)는 손대지 않는다(REQ-DEX-009d). 함수 상단 주석(L113-122, 현재 fan-in 8 호출자 8곳 나열)과 docstring(L124-136, `ready_to_ship` 규칙 서술)을 갱신해 신규 9번째 호출자(파손 접수 뷰)와 새 단락 규칙을 반영한다. **선행 조건**: M1.5 특성화 테스트. |
| MODIFY | `backend/order/urls.py` (SPEC-ORDER-013/014 블록, L84-106 인근 및 SPEC-PURCHASE-ORDER-004 블록 L70-72 인근) | 검색 엔드포인트(정적 경로, `<int:pk>` 충돌 없음)와 접수 엔드포인트(`<int:pk>/damaged-exchange/` 형태, 기존 `<int:pk>/status/`·`<int:pk>/logistics-status/`·`<int:pk>/rack-number/` 패턴과 동일한 그룹)를 등록. |
| **NEW (v1.3.0, D13)** | `backend/order/migrations/00XX_backfill_ready_to_ship_damaged_exchange.py`(파일명·번호는 M4.5 완료 후 Run 단계에서 최신 상태 재확인) | REQ-DEX-013/013a 구현. `0033_backfill_order_ready_to_ship.py`를 그대로 선례로 삼는다 — `purchase_order_views`를 import하지 않고 새 규칙(`cs_required` 또는 `damaged_exchange` 중 하나라도 있으면 `False`)을 역사적 모델로 재구현. 스코프는 0033과 동일하게 "추적 가능 LineItem 1건 이상인 Order만" — 0건인 Order는 이미 `null`이므로 갱신 불필요. |

### 프론트엔드

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| NEW | `frontend/src/pages/DamagedExchangePage/index.tsx` | 독립 페이지 — ISBN 검색 폼 + 결과 테이블(주문번호/주문 수량/오늘 출고 가능 여부/전체 출고 수량 컬럼, 이미 접수된 행은 배지 표시) + 행별 파손 수량 입력(기본값 1) + 접수 버튼. `OutboundPage`/`RackNumberPage`와 완전히 분리, import 없음(REQ-DEX-002). |
| NEW | `frontend/src/services/damagedExchangeApi.ts` | `searchDamagedExchangeCandidates(sku)`, `submitDamagedExchange(id, damagedQuantity)` — `rackNumberApi.ts`/`outboundApi.ts` 패턴(타입 정의 + `api.get`/`api.post` 호출) 재사용. |
| NEW | `frontend/src/hooks/useDamagedExchangeQueries.ts` | `useSearchDamagedExchange()`, `useSubmitDamagedExchange()` — `useRackNumberQueries.ts`/`useOutboundQueries.ts`의 `useQuery`/`useMutation` + `toast` 패턴 재사용. |
| MODIFY | `frontend/src/router/index.tsx` (`/outbound` 등록 L122-128 인근) | `/damaged-exchange` lazy route 추가(동일 패턴). |
| MODIFY | `frontend/src/components/Sidebar.tsx` (L3 import, L37-87 `flatNavItems`) | 신규 lucide 아이콘 import 추가(예: `PackageX`), `{ label: '파손 교환', href: '/damaged-exchange', icon: PackageX }` 항목을 '출고 처리'(L68-74) 인근에 배치. |

## 기술적 접근

### 검색 엔드포인트 — 배치 쿼리 설계 (REQ-DEX-004~007, 결정 B)

1. `LineItem.objects.filter(sku=sku).exclude(logistics_status="shipped").exclude(purchase_status="order_cancelled").select_related("order")` — `LineItemRackNumberSummaryView`(L2284-2341)의 미출고 필터를 그대로 재사용(정확 일치이므로 `sku=sku`, `icontains` 사용 안 함, REQ-DEX-004).
2. **전체 출고 수량(N+1 위험 지점, 결정 B 확정 반영)**: 위 쿼리 결과에서 `order_id` 목록을 추출한 뒤, `LineItem.objects.filter(order_id__in=order_ids, sku__isnull=False).exclude(purchase_status="order_cancelled").values("order_id").annotate(order_total_quantity=Sum("quantity"))`로 **단일 쿼리**를 실행해 `{order_id: 합계}` 딕셔너리를 만든다(REQ-DEX-006/006b — 취소·미추적 행 제외, null `quantity`는 `Sum()`이 자동으로 0 취급하지 않으므로 `Coalesce(Sum("quantity"), 0)`로 감싸 AC-DEX-005c의 null→0 요구를 보장한다). 그 뒤 Python에서 각 결과 행에 딕셔너리 조회로 매핑한다. 검색 결과 행 수와 무관하게 쿼리 수는 고정(검색 쿼리 1회 + 집계 쿼리 1회 + 필요 시 `DistributorVendorRule` 등 부가 조회)이며, 절대 행마다 별도 조회를 하지 않는다 — `_recompute_order_aggregates`(L123-195)가 확립한 "Order 수만큼만 쿼리, LineItem 수와 무관"이라는 배치 원칙을 그대로 적용한다. 이 필터 범위(`sku__isnull=False` AND `purchase_status != "order_cancelled"`)는 `_recompute_order_aggregates`의 `ready_to_ship` 계산이 내부적으로 사용하는 "추적 가능 + 비취소" 집합(L154-158 트랙어블 조회, L176 `non_cancelled` 필터)과 정확히 일치한다.
3. 응답에는 각 행의 `is_damaged_exchange`(또는 동등한 플래그, `purchase_status == "damaged_exchange"` 여부)를 포함해 프론트엔드가 배지를 렌더링할 수 있게 한다(REQ-DEX-005a).

### 파손 접수 엔드포인트 (REQ-DEX-008~011, REQ-DEX-009b/009c/009d)

1. `pk`로 LineItem을 조회(404 처리는 `LineItemStatusUpdateView` 패턴 재사용).
2. 요청 바디의 `damaged_quantity`가 정수이고 `1 <= damaged_quantity <= (li.quantity or 0)` 범위인지 검증 — `li.quantity`가 `null`이거나 `0`이면 범위가 공집합이 되어 항상 거부(REQ-DEX-009a). 이 검증은 `li.purchase_status`가 이미 `damaged_exchange`인 재접수 요청에도 동일하게 적용된다.
3. 통과 시 `li.purchase_status = "damaged_exchange"`, `li.damaged_quantity = damaged_quantity`를 같은 `save(update_fields=[...])` 호출로 반영 — 기존 `damaged_quantity` 값은 단순 대입으로 덮어써진다(REQ-DEX-009b, 누적 아님).
4. `LineItemNote.objects.create(line_item=li, content=f"파손 수량 {damaged_quantity}건 접수", author=request.user, note_type="파손/교환", assignee="발주")` — `author=request.user`는 결정 D의 직접 구현이다(REQ-DEX-010). 문구 정확한 표현은 Run 단계에서 확정하되, 반드시 접수 수량 값을 포함해야 한다(AC-DEX-010이 `content`에 수량 문자열 포함을 검증).
5. `_recompute_order_aggregates([li.order_id])` 호출 — 기존 모든 `purchase_status` 쓰기 경로와 동일한 관례(REQ-DEX-009). M4.5에서 이 함수 자체에 `damaged_exchange` 단락이 추가되므로, 이 호출 하나로 REQ-DEX-009(재계산 트리거)와 REQ-DEX-009c(새 단락 규칙)가 함께 검증된다.
6. `logistics_status`/`shipped_quantity` 필드는 어떤 단계에서도 참조·수정하지 않는다(REQ-DEX-011).

### `_recompute_order_aggregates`의 `ready_to_ship` 단락 확장 (REQ-DEX-009c/009d, 결정 E — [MODIFY] DELTA)

기존 코드(`purchase_order_views.py:175-186`):

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

변경 후(의사코드, 정확한 구현은 Run 단계 — `cs_required`와 `damaged_exchange` 중 하나라도 있으면 `False`, 두 조건 모두 없을 때만 기존 `all(...)` 판정 수행):

```python
non_cancelled = [it for it in (items or []) if it[1] != "order_cancelled"]
if not non_cancelled:
    ready_to_ship = None
elif any(
    purchase_status in ("cs_required", "damaged_exchange")
    for _, purchase_status in non_cancelled
):
    ready_to_ship = False
else:
    ready_to_ship = all(
        logistics_status == "received" or purchase_status == "in_stock"
        for logistics_status, purchase_status in non_cancelled
    )
```

`status`(물류 집계, L167-173)를 도출하는 **규칙**은 이 변경에서 완전히 분리되어 있으므로 무수정(REQ-DEX-009d) — 위 diff는 `ready_to_ship` 분기(L175-186)에만 있고 `status` 분기(L167-173)는 건드리지 않는다. 다만 L188-195의 `Order.objects.filter(...).update(status=Case(...), ready_to_ship=Case(...))`는 두 컬럼을 항상 함께 쓰므로(D16), 신규 9번째 호출자도 매번 `status`를 다시 쓰지만 그 값은 L167-173 규칙 그대로다 — "컬럼이 안 쓰인다"가 아니라 "값을 결정하는 규칙이 그대로다"라는 의미로 코드 리뷰 시 확인할 것. M1.5의 기존 특성화 테스트가 이 변경 전 `cs_required`/`received`/`in_stock`/`None` 조합에 대한 기존 동작을 고정해 두므로, 이 diff가 그 9개 테스트를 깨지 않는지 먼저 확인한 뒤 신규 `damaged_exchange` 케이스 테스트를 추가한다.

### `ready_to_ship` 백필 마이그레이션 (REQ-DEX-013/013a, 결정 F — [NEW], D13)

`0033_backfill_order_ready_to_ship.py`(SPEC-ORDER-012 REQ-RTS-006)를 그대로 선례로 따른다 — 알고리즘 형태(단일 SELECT로 모든 추적 가능 LineItem의 `(order_id, purchase_status, logistics_status)` 조회 → Python에서 order_id별 그룹화 → 규칙 적용 → `bulk_update()` 1회)를 그대로 재사용하고, 규칙 판정부에만 M4.5에서 확정한 `damaged_exchange` 단락을 반영한다(의사코드):

```python
def backfill_ready_to_ship_damaged_exchange(apps, schema_editor):
    Order = apps.get_model("order", "Order")
    LineItem = apps.get_model("order", "LineItem")

    triples = LineItem.objects.filter(sku__isnull=False).values_list(
        "order_id", "purchase_status", "logistics_status"
    )
    items_by_order: dict[int, list[tuple[str, str]]] = {}
    for order_id, purchase_status, logistics_status in triples:
        items_by_order.setdefault(order_id, []).append((purchase_status, logistics_status))

    to_update = []
    for order_id, items in items_by_order.items():
        non_cancelled = [it for it in items if it[0] != "order_cancelled"]
        if not non_cancelled:
            ready_to_ship = None
        elif any(ps in ("cs_required", "damaged_exchange") for ps, _ in non_cancelled):
            ready_to_ship = False
        else:
            ready_to_ship = all(
                ls == "received" or ps == "in_stock" for ps, ls in non_cancelled
            )
        to_update.append(Order(id=order_id, ready_to_ship=ready_to_ship))

    Order.objects.bulk_update(to_update, ["ready_to_ship"])
```

0033과 마찬가지로 이 마이그레이션 함수는 `purchase_order_views`를 import하지 않는다 — Django 마이그레이션은 특정 시점의 역사적 모델을 다루므로, 런타임 모듈을 참조하면 향후 그 모듈이 바뀔 때 과거 마이그레이션의 동작까지 조용히 바뀌는 위험이 생긴다(0031/0033이 확립한 관례). `reverse_code`는 0033과 동일하게 `RunPython.noop`(신규 규칙 적용 이전 값으로 되돌릴 근거 데이터가 없음). **원격 DB 실행 제약**: 0033처럼 배치 조회(1 SELECT) + 배치 갱신(1 `bulk_update`)로 설계해 Order 수와 무관하게 고정된 쿼리 수를 유지한다 — 절대 Order별 개별 UPDATE로 구현하지 않는다("실행 제약사항" 절 참조).

### 재발주 큐 수량 보정 (REQ-DEX-012/012a/012b/012c, 결정 A)

`UnorderedItemsView.get()`의 L292 `net_qty = max((li.quantity or 0) - li.refunded_qty, 0)`를 다음과 같이 분기한다(의사코드, 정확한 구현은 Run 단계):

```
base = li.damaged_quantity if li.purchase_status == "damaged_exchange" else li.quantity
net_qty = max((base or 0) - li.refunded_qty, 0)
if net_qty == 0:
    continue
```

`_reorder_candidate_filter`(L93-110)는 변경하지 않는다 — 이 SPEC은 재발주 큐에 "무엇이 노출되는가"가 아니라 "노출된 행의 수량이 얼마로 보고되는가"만 다룬다.

**v1.2.0 정정(D3/D11)**: 직접 재확인한 결과, 다음 5개 지점은 `quantity - refunded_qty` 균일 패턴을 공유하지 **않는다**(REQ-DEX-012b) — `RunComparisonView`(L580)와 `GenerateOrderFileView`(L398)만 `max(quantity - refunded_qty, 0)`를 쓰고, `DailyReviewExcelView`(L1084/L1099)는 환불을 제외 필터로만 쓰며 raw `quantity`를 보고하고, `UploadDailyReviewView`(L1451)는 환불 항 자체가 없이 raw `quantity`를 합산하며, `VendorComparisonView`(L744-757, v1.2.0에서 D11로 신규 추가)는 `purchase_orders__isnull=True` 필터(= `_reorder_candidate_filter`와 다른 자격 기준)로 `Sum("quantity")`를 집계한다. 다섯 곳의 공통점은 "quantity를 어떻게 계산하든 `damaged_quantity`는 읽지 않는다"는 것뿐이다. `ConfirmOrderView`(L884-886)는 이 5곳과 별도다(REQ-DEX-012c) — `qty = item.get("quantity")`(L886)로 **요청 바디**에서 수량을 받으며 `LineItem.quantity`를 전혀 읽지 않으므로, "quantity 대신 damaged_quantity를 썼는가" 질문 자체가 성립하지 않는다.

**v1.3.0 정정(D21) — `VendorComparisonView`의 PO-연결 제약**: `VendorComparisonView`의 `total_qty_qs`(L744-750)는 `purchase_orders__isnull=True`(PurchaseOrder에 전혀 연결되지 않은 LineItem)만 대상으로 하며, `GenerateOrderFileView`(L373-381)가 갖는 것과 같은 `damaged_exchange` 링크 예외가 **없다**. `purchase_order_views.py:372-381`의 기존 주석은 "damaged_exchange SKU는 현실적으로 원래 PurchaseOrder에 이미 연결되어 있다"고 명시적으로 기록하고 있으므로, 실무에서 흔할 PO-연결된 `damaged_exchange` 행은 이 뷰의 `qty_by_sku`에서 완전히 빠져 `0`으로 보고된다(`10`도 `damaged_quantity`인 `3`도 아님). AC-DEX-012e는 PO-**미연결** 픽스처(`purchase_orders__isnull=True`)로만 검증한다 — PO-연결 경우는 spec.md Exclusions에 알려진 미검증 공백으로 기록되어 있다.

## 실행 제약사항 (Execution Constraints)

- **원격 공유 MySQL 테스트 DB — pytest 동시 실행 금지**: 이 프로젝트의 테스트는 원격 공유 MySQL 인스턴스를 사용한다. Run 단계에서 pytest를 실행할 때 다른 세션/에이전트와 동시에 실행하면 무관한 테스트가 가짜로 실패할 수 있다 — 반드시 순차 실행한다.
- **원격 DB 왕복 지연(~130ms/쿼리) — 배치 쿼리 필수**: 검색 엔드포인트는 결과 행 수와 무관하게 고정된 쿼리 수(검색 1회 + 전체 출고 수량 집계 1회)로 설계해야 한다. 절대 Order별로 반복 조회(N+1)하지 않는다 — "기술적 접근 > 검색 엔드포인트" 절의 배치 설계를 그대로 따른다.
- **기존 배치 선례 준수**: `_recompute_order_aggregates`(L123-195, "Order 수만큼만 쿼리")와 SPEC-ORDER-015 후속 성능 수정(`_process_outbound_rows`, 쿼리 수 3N→3 고정)이 이 프로젝트의 확립된 배치 쿼리 관례다. 신규 코드는 이 관례를 따른다.
- **공유 함수 수정 시 특성화 테스트 선행(v1.2.0 신규, 결정 E)**: `_recompute_order_aggregates`는 fan-in 8(9로 증가)의 브라운필드 공유 함수다. M4.5(단락 추가) 착수 전 M1.5(기존 특성화 테스트 확인)를 반드시 먼저 완료해, 기존 8개 호출자 경로의 `ready_to_ship`/`status` 산출값이 회귀하지 않았음을 자동 검증한다.
- **백필 마이그레이션도 배치 쿼리 필수(v1.3.0 신규, D13)**: REQ-DEX-013의 백필은 0033 선례와 동일하게 고정 쿼리 수(1 SELECT + 1 `bulk_update`)로 설계한다 — Order 수만큼 반복 조회/갱신하는 구현은 원격 DB 지연(~130ms/쿼리) 하에서 허용되지 않는다.

## 리스크 및 제약사항

**MySQL 마이그레이션 안전성**: `damaged_quantity`(default=0, NOT NULL)는 기존 행에 안전한 기본값을 가지는 additive 컬럼 추가로, 데이터 백필이나 다운타임이 필요하지 않다 — `0035_lineitem_add_shipped_fields.py`가 이미 동일 패턴의 선례.

**환불 차감 설계 결정(결정 A)**: `damaged_quantity` 기준값에도 기존 환불 차감(`refunded_qty`)을 그대로 적용하기로 한 SPEC 작성자의 판단을 사용자가 2026-08-14에 확정했다(`spec.md` 결정 A 참조). 추가 검증 불필요.

**"전체 출고 수량" 범위(결정 B)**: 취소(`order_cancelled`)·미추적(`sku IS NULL`) LineItem을 제외하고 합산하는 것으로 사용자가 2026-08-14에 확정했다(`spec.md` 결정 B 참조, `_recompute_order_aggregates`의 "추적 가능" 관례와 정합). 위 "기술적 접근 > 검색 엔드포인트" 절의 쿼리 설계에 반영 완료.

**동시성**: 파손 접수 엔드포인트는 `LineItemStatusUpdateView`와 동일하게 `select_for_update()` 없이 처리한다 — 두 사용자가 동시에 같은 LineItem을 접수하는 race condition은 기존 관례와 동일하게 이번 SPEC에서 다루지 않는다.

**REQ-DEX-012b/012c가 남기는 잠재적 결함**: `RunComparisonView`/`DailyReviewExcelView`/`UploadDailyReviewView`/`GenerateOrderFileView`/`VendorComparisonView` 5곳(v1.2.0에서 `VendorComparisonView` 추가, `ConfirmOrderView` 제외 — D3/D11)도 논리적으로 동일한 "damaged_exchange 행에 quantity 전체를 사용" 결함을 잠재적으로 가지고 있으나, 사용자가 이번 SPEC의 범위를 `UnorderedItemsView` 한 곳으로 명시적으로 확정했다(2026-08-14). `spec.md`의 `Exclusions` 섹션에 "알려진 의도적 공백(known, deliberate gap)"으로 명시 기록되어 있으며, 후속 SPEC 후보다.

**공유 함수 범위 확장 리스크(v1.2.0 신규, 결정 E; v1.3.0에서 D15 보강)**: `_recompute_order_aggregates`의 `ready_to_ship` 단락 변경은 이번 신규 페이지와 무관한 기존 8개 호출자·`OrderDetailPage.tsx`의 3-state 배지·`OrderResyncView`(재동기화 응답)에도 영향을 준다 — `damaged_exchange` LineItem을 포함한 Order라면 이 SPEC 적용 이후 이 화면들 밖에서도 배지/응답값이 "출고가능"에서 "출고불가"로 바뀔 수 있다. 이는 의도된 동작(D1 대응)이지만, Run 단계에서 `OrderDetailPage.test.tsx`/`test_spec_012.py`/`test_order_resync.py`(SPEC-ORDER-012·리싱크 기존 테스트)에 회귀가 아니라 "의도된 변경"으로 반영해야 한다 — 세 테스트 스위트 모두 실행해 예상치 못한 부작용이 없는지 확인.

**백필 이후 데이터 정합성 리스크(v1.3.0 신규, D13)**: 백필 마이그레이션(REQ-DEX-013)은 배포 시점의 스냅샷을 1회 반영할 뿐이다 — 배포 이후 새로 `damaged_exchange`로 접수되는 LineItem은 REQ-DEX-009의 실시간 재계산 경로로 이미 정확히 반영되므로 별도 조치가 필요 없다. 배포 "이전"에 이미 `damaged_exchange`였던 Order만 백필 대상이며, 마이그레이션은 배포 파이프라인에서 정확히 한 번만 실행된다(Django 마이그레이션의 기본 보장) — 재실행 시에도 멱등(같은 입력에 같은 규칙을 다시 적용할 뿐이므로 결과가 달라지지 않음).

**`VendorComparisonView`의 PO-연결 공백은 이번 SPEC이 닫지 않는다(v1.3.0 신규, D21)**: `_reorder_candidate_filter`류의 링크 예외를 이 뷰에 추가하는 것은 REQ-DEX-012b의 "5곳 무변경" 확정 범위를 벗어난다 — PO-연결된 `damaged_exchange` SKU가 이 뷰에서 `0`으로 보고되는 문제는 후속 SPEC 후보로 남긴다(spec.md Exclusions).

## MX 태그 계획 (mx_plan)

- **`backend/order/purchase_order_views.py`의 `_recompute_order_aggregates`(L113-195, v1.2.0 [MODIFY])**: 함수 상단의 fan-in 강등 주석(L113-122, 현재 "Fan-in == 8"과 8개 호출자 나열)을 "Fan-in == 9"로 갱신하고 신규 파손 접수 뷰를 호출자 목록에 추가한다. `@MX:NOTE` 갱신 대상 — 기존 강등 사유(이 파일이 이미 `anchor_per_file` 한도 3에 도달, ANCHOR 4개 보유)는 그대로 유효하므로 `@MX:ANCHOR`로 승격하지 않는다. docstring(L124-136)의 `ready_to_ship` 규칙 서술에 `damaged_exchange` 단락을 추가 반영.
- **`UnorderedItemsView.get()` 내 `net_qty` 계산 분기(REQ-DEX-012)**: 비자명한 비즈니스 규칙(damaged_exchange 행만 기준값이 달라짐 + 환불 차감은 공통 적용)이므로 `@MX:NOTE`로 그 근거(REQ-DEX-012/012a, 결정 A)를 명시한다. 이 분기 자체는 `UnorderedItemsView.get()` 내부에서만 사용되어 fan_in=1이므로 `@MX:ANCHOR` 대상은 아니다.
- **신규 검색 뷰 / 접수 뷰**: 둘 다 URL 라우팅을 통해서만 호출되는 최상위 APIView이며 다른 Python 코드에서 임포트되어 호출되지 않으므로 fan_in 기준으로 `@MX:ANCHOR` 대상이 아니다. 새로운 fan_in≥3 지점이 이번 SPEC으로 발생하면, 이 파일이 이미 anchor_per_file 한도(3)에 도달해 있다는 사유로 `@MX:ANCHOR` 대신 `@MX:NOTE` + 강등 사유를 기록한다(L86-92, L113-122의 선례를 그대로 따름).
- **`LineItem.damaged_quantity` 필드(models.py)**: `@MX:NOTE`로 SPEC-PURCHASE-ORDER-011 도입 배경(파손 수량과 원 주문 수량을 분리 기록해 재발주 큐 정확도를 보장하기 위함)과, `purchase_status != "damaged_exchange"`인 행에서는 이 값이 의미를 가지지 않는다는 점, 재접수 시 덮어쓰기(REQ-DEX-009b)임을 남긴다.
- **백필 마이그레이션(v1.3.0 신규)**: `0033_backfill_order_ready_to_ship.py`에 MX 태그가 없는 것과 동일하게, 신규 백필 마이그레이션에도 MX 태그를 부여하지 않는다 — Django 마이그레이션 파일은 이 프로젝트에서 MX 태깅 대상으로 다뤄진 전례가 없으며, 대신 파일 상단에 0033처럼 알고리즘·스코프·비가역성(reverse_code)을 설명하는 상세 주석을 남긴다(코드가 아니라 문서 주석 관례).
- 구현(run) 단계에서 위 태그를 실제 코드에 부여하고, 필요 시 이 목록을 갱신한다.

## 관련 참조 구현

- `backend/order/purchase_order_views.py:251-314` `UnorderedItemsView` — 수정 대상 뷰, 환불 차감/0-스킵 패턴의 원본.
- `backend/order/purchase_order_views.py:1863-1900` `LineItemStatusUpdateView` — 단건 상태 변경 + `_recompute_order_aggregates` 호출 구조의 직접적 선례.
- `backend/order/purchase_order_views.py:2284-2341` `LineItemRackNumberSummaryView` — 미출고(unshipped) 필터 정의의 출처(`.exclude(logistics_status="shipped").exclude(purchase_status="order_cancelled")`).
- `backend/order/purchase_order_views.py:113-195` `_recompute_order_aggregates` — Order 집계 재계산 관례, 배치 쿼리(Order 수만큼만) 설계 선례. `ready_to_ship` 판정은 L175-186(`cs_required` 단락 L179-180, `damaged_exchange` 신규 단락 삽입 지점), `status` 판정은 L167-173(무수정 대상).
- `backend/order/purchase_order_views.py:86-110` `_reorder_candidate_filter` — SPEC-PURCHASE-ORDER-010이 확립한 `damaged_exchange` 읽기측 예외 처리(이번 SPEC은 이 필터를 변경하지 않음).
- `backend/order/purchase_order_views.py:544-590` `RunComparisonView`, `:322-420`(정확히는 L398) `GenerateOrderFileView`, `:1048-` `DailyReviewExcelView`(L1084/L1099), `:1229-` `UploadDailyReviewView`(L1451), `:714-` `VendorComparisonView`(L744-757, PO-연결 예외 없음 — L744-750), `:841-` `ConfirmOrderView`(L884-886) — REQ-DEX-012b/012c가 "변경하지 않는다"고 명시하는 6개 지점의 정확한 위치(v1.2.0/v1.3.0에서 전량 재검증). `:373-381`(`GenerateOrderFileView` 내부의 `damaged_exchange` 링크 예외 주석) — `VendorComparisonView`에는 없는 예외의 대조 사례(D21).
- `backend/order/serializers.py:141-171` `OrderDetailSerializer`(`ready_to_ship` 노출 L170), `backend/order/serializers.py:14-36` `OrderListSerializer`(노출 안 함, 확인됨) — REQ-DEX-009c의 다운스트림 소비자 조사 결과.
- `backend/order/views.py:188` `OrderResyncView`(`POST /api/orders/<pk>/sync/`, `urls.py:58`, `OrderDetailSerializer` 재사용은 `views.py:229`) — v1.3.0에서 D15로 추가된 두 번째 `ready_to_ship` 소비 엔드포인트.
- `backend/order/migrations/0033_backfill_order_ready_to_ship.py` — REQ-DEX-013 백필 마이그레이션의 직접적 선례(알고리즘·배치 설계·`reverse_code=noop` 관례 전부 재사용). `backend/order/tests/test_backfill_order_ready_to_ship_migration.py` — 그 마이그레이션의 기존 테스트 스위트, 신규 백필 테스트 작성 시 구조 참고.
- `backend/order/tests/test_spec_012.py:168-285` `TestRecomputeOrderAggregatesReadyToShip`(9개 테스트) — REQ-DEX-009c 착수 전 확인해야 할 기존 특성화 스위트(M1.5, D22). `test_spec_012.py:609` `test_resync_does_not_change_ready_to_ship` — `OrderResyncView` 회귀 확인용 기존 테스트.
- `frontend/src/pages/OrderDetailPage.tsx:240-260` — `Order.ready_to_ship` 3-state 배지(SPEC-ORDER-012 결정 F), REQ-DEX-009c의 프론트엔드 소비자.
- `frontend/src/pages/OutboundPage/index.tsx`, `frontend/src/router/index.tsx:122-128`, `frontend/src/components/Sidebar.tsx` — 독립 페이지 + 라우트 + 사이드바 등록 패턴의 직접적 선례(SPEC-ORDER-015).
