---
id: SPEC-ORDER-023
document: acceptance
version: 1.4.0
status: completed
updated: 2026-08-16
---

# 인수 기준 — SPEC-ORDER-023 주문목록 표시 컬럼 개편

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의 AC-OLIST-XXX/REQ-OLIST-XXX ID를 인용해 상호 추적된다.

[HARD] **판별력 요건.** 각 시나리오는 손으로 계산/추적 가능한 정확한 값을 단정한다. 각 항목은 자신을 깨뜨리는 mutation을 명시한다.

**v1.1.0 변경**: plan-audit iteration 1(FAIL, 0.61) 반영. AC-OLIST-006/022 계열의 픽스처를 프로덕션 실제 상태(`shipped_quantity=quantity`)로 교체(C2). AC-OLIST-008/013이 더 이상 `Order.status`에 의존하지 않는다(C3 — 물류상태 파생 자체가 `LineItem`에서만 계산되도록 재설계되었으므로 이 두 AC는 애초에 `Order.status`를 언급할 필요가 없어졌다). AC-OLIST-012/016/018/018a/018b에 키 존재 단정 추가(H1). AC-OLIST-022를 6개 값 전량 커버하도록 확장(H2, 022a~e 신설). AC-OLIST-018a/018b 신설로 null 원인 3개 전량 커버(H3). AC-OLIST-011에 발주상태 단정 추가(H4). AC-OLIST-004를 배지 요소 부재로 강화(H6). AC-OLIST-017a 신설(마진 반올림 순서, 감사 M2). AC-OLIST-013a 신설(규칙 4a, 혼재 상태).

**v1.2.0 변경**: plan-audit iteration 2(FAIL, 0.76) 반영. AC-OLIST-022~022e가 **표준 물류상태 데이터셋(Order A~G)**을 공유하도록 전면 재작성 — 이전 버전의 022b/022c/022e는 "그 외 상태 1건 이상"으로 비특정이라 `any` 대신 `all` mutation을 놓칠 수 있었다(H1-new). AC-OLIST-022d에 "필터 결과 ∧ 표시값" 이중 단정을 추가 — 규칙 4 경유 `outbound_scheduled`의 표시값을 단정하는 AC가 전무했다(H2-new). AC-OLIST-022f 신설(REQ-OLIST-024a 허용 외 값 fail-open, M2-new). AC-OLIST-020a 신설(`.date()` 시간대 일치, M5-new/round-1 L7). AC-OLIST-026/027을 6개 라벨 전량 파리티로 확장(M3-new — 이전에는 백엔드만 6/6이고 프론트엔드는 1~2/6였다).

**v1.2.1 변경**: plan-audit iteration 3(**PASS, 0.87, 차단 결함 0건**) 반영. PASS 상태에서 사용자가 선택한 3건만 반영: **N1**(표준 데이터셋에 Order H = `{outbound_scheduled, shipment_confirmed}` 혼재, 표시값 `partial` 추가 — G만으로는 `outbound_scheduled` uniform 검사의 any/all mutation을 판별하지 못했다. AC-OLIST-022e의 기대 집합을 `{G,H}`로 갱신), **N2**(AC-OLIST-022~022e의 Then에 응답 `count` 필드 단정 추가 — 페이지네이션 이후 Python 사후 필터링은 추가 쿼리 0개라 기존 AC를 전부 통과하면서 프로덕션에서 페이지네이션을 조용히 깨뜨릴 수 있었다. REQ-OLIST-025([HARD] 쿼리 레벨 필터)에 실효 검증 수단이 생겼다), **L8-new**(spec.md REQ-OLIST-024a 문언 정정, 이 문서에는 직접적인 텍스트 변경 없음 — AC-OLIST-022f는 무수정).

**v1.3.0 변경(구현 완료)**: 독립 평가(evaluator-active, PASS — Functionality 93 / Security 96 / Craft 88 / Consistency 88) 확인 후 `status`를 draft→completed로 전환한다. 이 문서의 시나리오 자체는 무수정이다 — 전 AC가 `test_spec_023.py`(31개, 백엔드) 및 `OrdersPage.test.tsx`(프론트엔드, 전체 스위트 304개 중 일부)에서 설계된 mutation을 실제로 재현해 판별력을 확인했다(자세한 내용은 `spec.md` HISTORY v1.3.0 참조).

**v1.4.0 변경(프로덕션 결함 정정)**: 발주상태 AC 계열이 `PurchaseOrder` 링크 조건을 전혀 검사하지 않아, `purchase_status` 단독 검사라는 잘못된 구현을 그대로 통과시켰다(주문 `#38360` 사용자 보고, 프로덕션 trackable 주문의 97.5%가 오표시). AC-OLIST-014를 링크 픽스처 포함으로 강화하고, AC-OLIST-014a(`#38360` 직접 재현)·AC-OLIST-014b(`damaged_exchange`는 링크와 무관하게 미발주)를 신설했다. AC-OLIST-021의 절대 쿼리 수를 7→8로 갱신(`line_items__purchase_orders` M2M prefetch 1회 추가). 자세한 근본 원인은 `spec.md` HISTORY v1.4.0 참조.

**검증 레이어**: `[BE]` = `backend/order/tests/test_spec_023.py`(pytest + DRF `APIClient`), `[FE]` = `frontend/src/pages/OrdersPage.test.tsx`(vitest + React Testing Library).

---

## 취소 배지

### AC-OLIST-001 — 취소 배지 (`financial_status='refunded'`) `[FE]`

Traces: REQ-OLIST-004, REQ-OLIST-006

- **Given**: 주문 목록 응답에 `financial_status: 'refunded', has_refund: false`인 주문이 포함되어 있다.
- **When**: `OrdersPage`를 렌더링한다.
- **Then**: 해당 행에 `data-testid="cancel-badge"` 요소가 존재하고, 그 텍스트가 "취소"다.
- **판별력**: 배지 판별을 `has_refund`만으로 구현하면(`financial_status` 무시) `has_refund=false`인 이 픽스처에서 배지가 아예 렌더되지 않아 실패한다.

### AC-OLIST-002 — 부분취소 배지 (명시적 부분환불, 정확 일치) `[FE]`

Traces: REQ-OLIST-005, REQ-OLIST-006

- **Given**: `financial_status: 'partially_refunded', has_refund: true`인 주문(refunded 아님).
- **When**: `OrdersPage`를 렌더링한다.
- **Then**: 해당 행의 `data-testid="cancel-badge"` 요소의 텍스트가 **정확히** "부분취소"다(`toHaveTextContent`의 정확 문자열 비교, 또는 `{ exact: true }` 매처 사용).
- **판별력(감사 M3)**: "부분취소"는 "취소"를 부분문자열로 포함한다 — `data-testid` 스코프 없이 `queryByText(/취소/)`류의 느슨한 매칭으로 작성하면 이 텍스트 노드 자체가 매칭되어 통과하는 것은 맞지만, 만약 구현이 실수로 배지를 2개("취소"와 "부분취소") 렌더하는 등의 mutation이 있어도 느슨한 매칭은 구분하지 못한다 — 정확 일치 단정이 이를 방지한다.

### AC-OLIST-003 — 부분취소 배지 ($0 취소, `has_refund`만 true) `[FE]`

Traces: REQ-OLIST-005

- **Given**: `financial_status: 'paid', has_refund: true`인 주문.
- **When**: `OrdersPage`를 렌더링한다.
- **Then**: 해당 행의 `data-testid="cancel-badge"` 요소의 텍스트가 "부분취소"다.
- **판별력**: 배지 판별을 `financial_status`만으로 구현하면(`has_refund` 무시) 이 픽스처는 `paid`이므로 배지가 렌더되지 않아 실패한다.

### AC-OLIST-004 — 정상 주문에는 배지 요소 자체가 없다 (감사 H6 강화) `[FE]`

Traces: REQ-OLIST-006

- **Given**: `financial_status: 'paid', has_refund: false`인 주문.
- **When**: `OrdersPage`를 렌더링한다.
- **Then**: 해당 행에 `data-testid="cancel-badge"` 요소 자체가 **존재하지 않는다**(`queryByTestId` 부재 단정 — 특정 텍스트("취소"/"부분취소")의 부재가 아니라 요소 자체의 부재).
- **판별력(H6)**: `getDisplayStatus`(`OrdersPage.tsx:81-94`)를 문자 그대로(뒤따르는 결제상태 라벨 맵 `:86-93`까지) 재사용해 그 반환값을 그대로 `data-testid="cancel-badge"` 요소에 렌더하면, 이 픽스처(`financial_status='paid'`)에서 "결제완료" 텍스트를 담은 배지 요소가 렌더된다 — 텍스트만 확인하는 이전 버전의 단정은 이를 놓치지만, "요소 자체의 부재"를 요구하는 이 단정은 실패한다.

## 열 구성

### AC-OLIST-005 — 9열 구성 및 결제/출고상태 열·필터 제거 `[FE]`

Traces: REQ-OLIST-001, REQ-OLIST-002, REQ-OLIST-003, REQ-OLIST-028, REQ-OLIST-029

- **Given**: `OrdersPage`를 정상 데이터로 렌더링한다.
- **When**: 테이블 헤더와 필터 영역을 조회한다.
- **Then**:
  - (a) "결제상태"/"출고상태" 텍스트가 헤더에도, `aria-label="결제 상태 필터"`/`aria-label="출고 상태 필터"` 셀렉트에도 존재하지 않는다.
  - (b) 헤더 9개가 DOM 순서상 주문번호/스토어/위치/고객/물류상태/발주상태/마진율/금액/주문일 순으로 렌더된다(`compareDocumentPosition`으로 단정).
  - (c) `data.results`가 빈 배열일 때 렌더되는 빈 상태 행의 `<td>` `colSpan` 속성이 `9`다.
- **판별력**: 열은 추가했지만 `colSpan={8}`을 그대로 두면 (c)가 실패한다. 헤더 순서를 다르게 구현하면 (b)가 실패한다.

## 물류상태 파생 (`LineItem`에서만 계산 — `Order.status`는 관여하지 않는다)

### AC-OLIST-006 — 전 trackable 항목 출고 완료 (현실적 픽스처, 감사 C2) `[BE]`

Traces: REQ-OLIST-008

- **Given**: `Order`에 trackable 라인아이템(`sku="ISBN001"`) 1개, `logistics_status="shipped", quantity=5, shipped_quantity=5`(양수 — `purchase_order_views.py:3411/3456/3972`가 강제하는 실제 프로덕션 상태. 이전 버전은 `shipped_quantity`를 지정하지 않아 기본값 `0`이 되었고, 그 결과 규칙 2가 발화하지 않아 우선순위 역전 mutation을 놓쳤다).
- **When**: `GET /api/orders/`.
- **Then**: 응답의 해당 주문 `logistics_display == "shipped"`.
- **판별력**: 규칙 2("하나 이상 `shipped_quantity>0`")를 규칙 1보다 먼저 평가하면, 이 픽스처는 `shipped_quantity=5>0`이므로 규칙 2가 먼저 발화해 `"partial_shipped"`(오답)를 반환한다 — 이것이 프로덕션에서 실제로 발생 가능한 가장 흔한 순서 오류다.

### AC-OLIST-007 — 부분출고 판별 (`>= quantity` 대 `> 0`) `[BE]`

Traces: REQ-OLIST-009

- **Given**: `Order`에 trackable 라인아이템 2개 — A(`logistics_status="outbound_scheduled", shipped_quantity=4, quantity=10`), B(`logistics_status="outbound_scheduled", shipped_quantity=0, quantity=5`).
- **When**: `GET /api/orders/`.
- **Then**: `logistics_display == "partial_shipped"`.
- **판별력**: `shipped_quantity >= quantity`로 구현하면 A(4≥10 거짓)·B(0≥5 거짓) 모두 거짓이 되어 규칙 2가 트리거되지 않고, 두 아이템의 `logistics_status`가 균일(`outbound_scheduled`)하므로 규칙 4로 낙하해 `"outbound_scheduled"`(오답)가 된다.

### AC-OLIST-008 — `shipped_quantity=0` 경계 (부분출고 아님) `[BE]`

Traces: REQ-OLIST-009, REQ-OLIST-011

- **Given**: trackable 라인아이템 1개, `logistics_status="not_shipped", shipped_quantity=0, quantity=5`(이 라인아이템의 `logistics_status`가 유일한 입력이다 — v1.1.0부터 이 계산은 `Order.status`를 전혀 참조하지 않으므로, `Order` 픽스처는 이 값을 별도로 설정할 필요가 없다).
- **When**: `GET /api/orders/`.
- **Then**: `logistics_display == "not_shipped"`.
- **판별력**: 조건을 `shipped_quantity >= 0`(또는 `is not None`)으로 구현하면 이 케이스가 `"partial_shipped"`로 잘못 판정된다.

### AC-OLIST-009 — 우선순위 역전 판별 (핵심 시나리오) `[BE]`

Traces: REQ-OLIST-009, REQ-OLIST-010

- **Given**: trackable 라인아이템 1개, `logistics_status="received", shipped_quantity=3, quantity=10`(SPEC-ORDER-015가 확인한 대로, 출고 처리는 현재 `logistics_status`와 무관하게 허용되므로 `received` 상태에서도 부분출고가 발생할 수 있다).
- **When**: `GET /api/orders/`.
- **Then**: `logistics_display == "partial_shipped"`(NOT `"outbound_scheduled"`).
- **판별력**: 규칙 3("모두 received → 출고예정")을 규칙 2보다 먼저 평가하면, 이 단일 아이템이 `received` 하나뿐이므로 "모두 received"가 참이 되어 `"outbound_scheduled"`(오답)를 반환한다. 이 시나리오가 규칙 1↔2(AC-OLIST-006) 다음으로 이 SPEC에서 중요한 판별 지점이다.

### AC-OLIST-010 — 전부 입고완료 → 출고예정 `[BE]`

Traces: REQ-OLIST-010

- **Given**: trackable 라인아이템 2개, 둘 다 `logistics_status="received", shipped_quantity=0`.
- **When**: `GET /api/orders/`.
- **Then**: `logistics_display == "outbound_scheduled"`.

### AC-OLIST-011 — non-trackable 항목 제외 판별 (물류·발주 양쪽, 감사 H4 확장) `[BE]`

Traces: REQ-OLIST-007, REQ-OLIST-013

- **Given**: `Order`에 trackable 라인아이템 1개(`sku="ISBN001", logistics_status="received", shipped_quantity=0, quantity=5, purchase_status="in_stock"`)와 non-trackable 라인아이템 1개(`sku=None, shipped_quantity=99, quantity=1` — `purchase_status`는 명시하지 않아 모델 기본값 `"unordered"`가 그대로 적용된다, `models.py:193`).
- **When**: `GET /api/orders/`.
- **Then**: `logistics_display == "outbound_scheduled"`(NOT `"partial_shipped"`) **그리고** `purchase_display == "ordered"`(NOT `"unordered"`).
- **판별력(물류)**: `sku__isnull=False` 필터를 물류 경로에서 빠뜨리고 전체 라인아이템을 평가하면 non-trackable 항목의 `shipped_quantity=99>0`이 규칙 2를 트리거해 `logistics_display == "partial_shipped"`(오답)가 된다.
- **판별력(발주, H4)**: `sku__isnull=False` 필터를 발주 경로에서 빠뜨리면, non-trackable 항목의 `purchase_status`가 모델 기본값 `"unordered"`이므로 `purchase_display == "unordered"`(오답)가 된다 — trackable 항목은 `"in_stock"`뿐이므로, 필터가 올바르면 "unordered"에 해당하는 trackable 항목이 없어 `"ordered"`가 나와야 한다. 이전 버전은 이 mutation을 물류 경로에 대해서만 판별했다(`purchase_display`를 단정하지 않았다) — 커버리지 0이었던 것을 이 버전이 메운다.

### AC-OLIST-012 — trackable 없음 → 키 존재 + null (감사 H1 강화) `[BE]`

Traces: REQ-OLIST-012

- **Given**: `Order`의 모든 라인아이템이 `sku=None`(또는 라인아이템 자체가 없음).
- **When**: `GET /api/orders/`.
- **Then**: 응답 항목에 `"logistics_display"` 키가 **존재**하며(`"logistics_display" in item`), 그 값이 `None`이다.
- **판별력(H1)**: 이 필드를 아예 구현하지 않으면(`Meta.fields` 누락) `item.get("logistics_display")`류의 조회는 키 부재를 `None`으로 착각해 통과해버린다 — 키 존재 단정이 이 mutation을 잡는 유일한 수단이다(SPEC-ORDER-021 감사 D6 재발 방지).

### AC-OLIST-013 — 규칙 4 통과값 정확성 (uniform, 단일 값) `[BE]`

Traces: REQ-OLIST-011

- **Given**: trackable 라인아이템 1개, `logistics_status="shipment_confirmed", shipped_quantity=0`(v1.1.0: `Order.status`는 이 계산에 관여하지 않으므로 별도로 지정하지 않는다).
- **When**: `GET /api/orders/`.
- **Then**: `logistics_display == "shipment_confirmed"`.

### AC-OLIST-013a — 규칙 4a: 혼재 상태 → 부분입고 (신규, 규칙 4a) `[BE]`

Traces: REQ-OLIST-011a

- **Given**: trackable 라인아이템 2개 — A(`logistics_status="not_shipped", shipped_quantity=0`), B(`logistics_status="shipment_confirmed", shipped_quantity=0`) — 둘 다 규칙 1~3에 해당하지 않고 서로 다른 `logistics_status`를 가진다.
- **When**: `GET /api/orders/`.
- **Then**: `logistics_display == "partial"`.
- **판별력**: uniform 판정을 생략하고 정렬/조회 순서상 첫 번째 라인아이템의 값을 그대로 반환하면(예: `"not_shipped"` 또는 `"shipment_confirmed"`) `"partial"`과 어긋난다.

## 발주상태 파생

### AC-OLIST-014 — 미발주 판별 (`any` 대 `all` + 발주서 링크 조건) `[BE]` (강화 v1.4.0)

Traces: REQ-OLIST-013

- **Given**: trackable 라인아이템 2개 — A(`purchase_status="unordered"`, 연결된 `PurchaseOrder` **없음**), B(`purchase_status="unordered"`이면서 `status="confirmed"`인 `PurchaseOrder` 1건에 **연결됨**).
- **When**: `GET /api/orders/`.
- **Then**: `purchase_display == "unordered"`. 이어서 같은 테스트에서 A를 삭제하고 재요청하면 `purchase_display == "ordered"`.
- **판별력**: "모든 trackable 항목이 대기 상태"(all)로 구현하면 A/B가 섞여 있어 거짓이 되어 `"ordered"`(오답)가 된다. 후반부 단정(A 삭제 후 `"ordered"`)은 v1.3.0의 `purchase_status` 단독 검사를 직접 잡아낸다 — 그 구현에서는 B만 남아도 `"unordered"`가 나온다.

### AC-OLIST-014a — 발주서에 연결된 `unordered` 항목은 미발주가 아니다 (`#38360` 재현) `[BE]` (신규 v1.4.0)

Traces: REQ-OLIST-013, REQ-OLIST-014, REQ-OLIST-014a

- **Given**: 프로덕션 주문 `#38360`(order.pk=4163)의 실제 형태 — trackable 라인아이템 8개 전부 `purchase_status="unordered"`이고, 각각 `status="confirmed"`인 서로 다른 `PurchaseOrder`에 연결됨.
- **When**: `GET /api/orders/`.
- **Then**: `purchase_display == "ordered"`.
- **판별력**: 이것이 v1.4.0이 고치는 결함의 직접 재현이다. v1.3.0 구현(`any(li.purchase_status == "unordered")`)에서는 `"unordered"`가 나와 반드시 실패한다. 프로덕션에서 trackable 주문 3,613건 중 3,524건(97.5%)이 이 형태였다.

### AC-OLIST-014b — `damaged_exchange`는 발주서 연결과 무관하게 미발주 `[BE]` (신규 v1.4.0)

Traces: REQ-OLIST-013(b), REQ-OLIST-014a

- **Given**: trackable 라인아이템 2개 — A(`purchase_status="damaged_exchange"`, `status="confirmed"`인 `PurchaseOrder` 1건에 **연결됨**), B(`purchase_status="in_stock"`).
- **When**: `GET /api/orders/`.
- **Then**: `purchase_display == "unordered"`.
- **판별력**: 링크 예외를 `purchase_status`와 무관하게 일괄 적용하면(즉 `damaged_exchange`에도 "발주서 있으면 발주완료"를 적용하면) `"ordered"`(오답)가 되고, 그 구현은 미발주 목록 탭(`_reorder_candidate_filter`가 `damaged_exchange`를 링크 여부와 무관하게 포함한다)과 어긋나 REQ-OLIST-014a를 위반한다.

### AC-OLIST-015 — 발주완료 판별 `[BE]`

Traces: REQ-OLIST-014

- **Given**: trackable 라인아이템 2개, 둘 다 발주 대기 상태가 아님(`in_stock`, `cs_required` — 둘 다 `PurchaseOrder` 연결 없음).
- **When**: `GET /api/orders/`.
- **Then**: `purchase_display == "ordered"`.

### AC-OLIST-016 — trackable 없음 → 키 존재 + null (감사 H1 강화, L8: 두 하위 케이스) `[BE]`

Traces: REQ-OLIST-015

- **Given (a)**: `Order`의 모든 라인아이템이 `sku=None`.
- **Given (b)**: `Order`에 라인아이템 자체가 0개다.
- **When**: (a), (b) 각각에 대해 `GET /api/orders/`.
- **Then**: 두 경우 모두 응답 항목에 `"purchase_display"` 키가 존재하며 값이 `None`이다.

## 마진율

### AC-OLIST-017 — `margin_rate` 값 및 필드 노출 범위 `[BE]`

Traces: REQ-OLIST-016, REQ-OLIST-018

- **Given**: `Order(total_price="100.00")`, `ExchangeRate(rate="1000.00")`, 라인아이템 1개 `LineItem(quantity=3, confirmed_price="10000.00", grams=0)`(SPEC-ORDER-021 AC-COST-001과 동일 픽스처).
- **When**: `GET /api/orders/`.
- **Then**:
  - (a) `margin_rate == "67.75"`(계산 근거: `confirmed_cost_usd=30.00`, `shipping_cost_usd=0`, `korea_warehouse_usd=2.25`, `margin_usd=100-30-0-2.25=67.75`, `margin_rate=67.75/100×100=67.75`).
  - (b) 응답 항목에 `margin_amount`/`shipping_cost`/`korea_warehouse_cost`/`confirmed_cost`/`total_cost`/`total_weight_grams` 키가 없다.
- **판별력**: `margin_rate`를 배송비·한국창고비를 뺀 `confirmed_cost_usd`만으로 계산하면 `100-30=70` → `"70.00"`이 되어 (a)가 실패한다. 상세 시리얼라이저의 필드 집합을 그대로 재사용하면 (b)의 금지 키 중 하나 이상이 나타난다.

### AC-OLIST-017a — 마진율은 반올림 전 정확값의 합에서 한 번만 양자화한다 (신규, 감사 M2) `[BE]`

Traces: REQ-OLIST-016

- **Given**: `Order(total_price="100.00")`, `ExchangeRate(rate="1000.00")`, 라인아이템 1개 `LineItem(quantity=1, confirmed_price="10005.00", grams=500)`(SPEC-ORDER-021 AC-COST-015/016과 동일 픽스처 — `confirmed_cost_usd=10.005`, `shipping_cost_usd=2.725`가 개별 반올림 시 각각 올림되도록 의도적으로 고른 값).
- **When**: `GET /api/orders/`.
- **Then**: `margin_rate == "86.02"`(계산: `margin_usd = 100 - 10.005 - 2.725 - 1.25 = 86.020`, 반올림 전 정확값의 합에서 한 번만 양자화).
- **판별력**: 목록 전용 코드가 개별 양자화된 `confirmed_cost="10.01"`(`.005`가 올림), `shipping_cost="2.73"`(`.725`가 올림), `korea_warehouse_cost="1.25"` 문자열을 재파싱해 `100-10.01-2.73-1.25=86.01`로 구하면 정답(`"86.02"`)과 **1센트** 어긋난다 — SPEC-ORDER-021 AC-COST-015가 `total_cost`에서 이미 검증한 반올림-순서 함정을, 목록 엔드포인트의 `margin_rate` 하나의 관측 가능한 필드로 재현한다.

### AC-OLIST-018 — `margin_rate` null 게이트 (원인 2: 확정 매입가 전무, 감사 H1 강화) `[BE]`

Traces: REQ-OLIST-017

- **Given**: 유효한 `ExchangeRate`는 있으나 어떤 라인아이템도 `confirmed_price`가 없는 주문.
- **When**: `GET /api/orders/`.
- **Then**: 응답 항목에 `"margin_rate"` 키가 존재하며 값이 `None`이다.

### AC-OLIST-018a — `margin_rate` null 게이트 (원인 1: 환율 없음, 신규, 감사 H3) `[BE]`

Traces: REQ-OLIST-017

- **Given**: 확정 매입가는 있으나, 해당 주문일 이전 어떤 날짜에도 `ExchangeRate` 레코드가 없는 주문.
- **When**: `GET /api/orders/`.
- **Then**: HTTP 200이며(500이 아님), 응답 항목에 `"margin_rate"` 키가 존재하고 값이 `None`이다.
- **판별력**: 배치 로더가 "이력 리스트가 비어 있음" 또는 "일치하는 원소 없음"을 `IndexError`로 처리하면 이 요청이 500으로 실패한다 — 이 AC의 HTTP 200 자체가 1차 판별력이며(배치 로드 구현에서 가장 깨지기 쉬운 지점, 감사 H3), `null` 값이 2차 판별력이다.

### AC-OLIST-018b — `margin_rate` null 게이트 (원인 3: `total_price == 0`, 신규, 감사 H3) `[BE]`

Traces: REQ-OLIST-017

- **Given**: `Order(total_price="0.00")`, 유효한 `ExchangeRate`, 확정 매입가가 있는 라인아이템 1개.
- **When**: `GET /api/orders/`.
- **Then**: 응답 항목에 `"margin_rate"` 키가 존재하며 값이 `None`이다.

## 성능 불변식

### AC-OLIST-019 — 배치 환율 로드 정확성 + 쿼리 수 `[BE]`

Traces: REQ-OLIST-019, REQ-OLIST-020

- **Given**: 서로 다른 날짜의 주문 2건 —
  - X: `shopify_created_at=D1`, `ExchangeRate(effective_date=D1, rate="1000.00")`, 라인아이템 `quantity=3, confirmed_price="10000.00", grams=0`, `total_price="100.00"`(SPEC-ORDER-021 AC-COST-001 픽스처).
  - Y: `shopify_created_at=D2`(`D2 != D1`), `ExchangeRate(effective_date=D2, rate="1250.00")`, 라인아이템 `quantity=3, confirmed_price="12500.00", grams=0`, `total_price="100.00"`(SPEC-ORDER-021 AC-COST-012 픽스처).
- **When**: (워밍업 요청 1회 후) `CaptureQueriesContext`로 감싸 `GET /api/orders/`를 조회한다.
- **Then**:
  - (a) X의 `margin_rate == "67.75"`, Y의 `margin_rate == "68.20"` — 각자 자신의 날짜/환율로 정확히 계산된다.
  - (b) `orders_exchangerate` 테이블(`backend/order/models.py:507`)을 참조하는 쿼리가 정확히 1개다.
- **판별력**: `_get_exchange_rate`를 무수정 재사용하면(주문 `pk` 단위 메모이제이션) 서로 다른 두 주문에 대해 캐시가 각각 새로 채워져 (b)가 2가 되어 실패한다. 배치 로더가 두 주문에 같은(잘못된) 환율을 적용하면(예: 페이지 내 최댓값 날짜의 환율을 모두에게 적용) (a)에서 X 또는 Y 중 하나의 값이 어긋난다.

### AC-OLIST-020 — 배치 로드의 폴백 보존 `[BE]`

Traces: REQ-OLIST-020

- **Given**: `Order(shopify_created_at=D)`, `D` 당일에는 `ExchangeRate` 레코드가 없고 `D-3`에만 `ExchangeRate(effective_date=D-3, rate="1000.00")`가 존재. 라인아이템 `quantity=3, confirmed_price="10000.00", grams=0`, `total_price="100.00"`.
- **When**: `GET /api/orders/`.
- **Then**: `margin_rate == "67.75"`(NOT `null`).
- **판별력**: 배치 로더가 페이지의 주문일과 정확히 일치하는 `ExchangeRate` 행만 적재하면(폴백 없이) `D`에 해당하는 레코드가 없어 `margin_rate`가 잘못 `null`이 된다. 배치 쿼리에 실수로 하한(`effective_date__gte`)을 추가해 `D-3`이 하한 밖으로 밀려나도 같은 방식으로 실패한다.

### AC-OLIST-020a — 배치 로더의 날짜 산출은 `TIME_ZONE` 설정과 무관하다 (신규 v1.2.0, M5-new/round-1 L7) `[BE]`

Traces: REQ-OLIST-020

- **Given**: `django.test.utils.override_settings(TIME_ZONE="Asia/Seoul")`(KST, UTC+9 — 이 프로젝트의 실제 배포값은 `backend/config/settings/base.py:92`의 `"UTC"`이지만, 이 AC는 배치 로더가 어떤 `TIME_ZONE`에서도 `_get_exchange_rate`와 동일하게 동작함을 증명하기 위해 의도적으로 다른 값을 강제한다) 적용 상태에서, `Order(shopify_created_at="2026-08-01T23:30:00Z")`, `ExchangeRate(effective_date="2026-08-01", rate="1000.00")`, `ExchangeRate(effective_date="2026-08-02", rate="1200.00")`, 라인아이템 `quantity=3, confirmed_price="10000.00", grams=0`, `total_price="100.00"`.
- **When**: `GET /api/orders/`.
- **Then**: `margin_rate == "67.75"`(UTC 달력 날짜 `2026-08-01`의 환율 `1000.00`을 사용 — `confirmed_cost_usd=30.00`, `korea_warehouse_usd=2.25`, `margin_usd=100-30-0-2.25=67.75`).
- **판별력**: 배치 로더가 `order.shopify_created_at.date()` 대신 `django.utils.timezone.localtime(order.shopify_created_at).date()`를 쓰면(KST로 변환), `23:30 UTC`가 `08:30 KST` 다음날(`2026-08-02`)이 되어 `rate="1200.00"`이 잘못 적용된다 — `confirmed_cost_usd=25.00`, `korea_warehouse_usd=2250/1200=1.875`, `margin_usd=100-25-0-1.875=73.125`→`margin_rate=="73.13"`(정답 `"67.75"`와 명확히 어긋난다). 이 프로젝트의 실제 `TIME_ZONE="UTC"`에서는 이 mutation이 관측 가능한 차이를 만들지 않으므로(현지화해도 UTC이므로 무연산), `override_settings`가 이 AC의 판별력에 필수적이다.

### AC-OLIST-021 — 전체 쿼리 수는 SPEC이 유도한 절대값과 정확히 같다 (감사 C1 재설계) `[BE]`

Traces: REQ-OLIST-021, REQ-OLIST-022, REQ-OLIST-022a

- **Given**: 확정 매입가·유효 환율·**고객이 연결된**(`customer` not null — 그렇지 않으면 `orders_customer` 프리페치 쿼리 자체가 생략되어 절대값이 6이 아니라 5가 되는 엣지 케이스와 섞인다) trackable 라인아이템을 각각 가진 주문들.
- **When**: (워밍업 요청 후) 주문 1건을 반환하는 요청과 5건을 반환하는 요청 각각을 `CaptureQueriesContext`로 캡처한다.
- **Then**: 두 요청의 총 쿼리 수가 서로 같고, **그 값이 정확히 8이다**(v1.4.0에서 7→8; `spec.md` REQ-OLIST-022a가 유도한 값 — 이 세션에서 실측한 베이스라인 6: JWT 인증 사용자 조회 1 + 페이지네이션 `COUNT(*)` 1 + 본문 `SELECT` 1 + `prefetch_related` 3개(`refunds`/`line_items`/`customer`) + 배치 `ExchangeRate` 쿼리 1 + `line_items__purchase_orders` M2M prefetch 1).
- **판별력**: `logistics_display`/`purchase_display` 계산이 `obj.line_items.all()` 재사용 대신 `LineItem.objects.filter(order=obj)`류의 신규 쿼리를 발급하면 주문 수에 비례해 쿼리 수가 늘어 1건 vs 5건의 값이 달라지고, 절대값도 8을 초과한다. `_get_exchange_rate`를 무수정 재사용하는 mutation은 주문마다 캐시가 새로 채워지므로 1건 요청은 8(7+1), 5건 요청은 12(7+5)이 되어 **페이지 크기 불변성 자체가 깨지고**, 절대값도 어긋난다 — 이 mutation은 상대 비교(1건==5건)만으로도 걸리지만, 절대값 8 고정이 "우연히 둘 다 늘어나 같아지는" 다른 mutation(예: 항상 +1 상수 쿼리를 추가하는 버그)까지 추가로 잡는다.

## 물류상태 필터 (`LineItem`에서만 파생 — `Order.status`는 필터 조건에 쓰지 않는다)

### 표준 물류상태 데이터셋 (Order A~H, 8건) — 신규 v1.2.0, H1-new/H2-new/M4-new 대응; v1.2.1에서 Order H 추가(감사 N1)

AC-OLIST-022~022f는 이 데이터셋 전량을 Given으로 공유한다. 각 AC가 서로 다른 임의의 부분집합을 고르면 판별력이 테스트 작성자의 선택에 좌우된다는 것이 v1.1.0 감사(H1-new)의 핵심 지적이었다 — 예컨대 "미입고" 필터를 `any`(우연히 일치하는 항목이 하나라도 있으면 포함) 방식으로 잘못 구현해도, 비교 대상 주문이 "출고" 하나뿐이면 그 mutation은 드러나지 않는다. 아래 8건을 표준 fixture 헬퍼(`backend/order/tests/test_spec_023.py`)로 1회 정의해 재사용한다. **이 표는 `spec.md`의 동일 표와 바이트 단위로 동일해야 한다** — 감사가 v1.2.0에서 `diff`로 이 동일성을 직접 확인했다.

| 주문 | trackable 라인아이템 구성 | `logistics_display` |
|---|---|---|
| A | `logistics_status="shipped", quantity=5, shipped_quantity=5`(AC-OLIST-006과 동일 — 규칙 1) | `shipped` |
| B | P(`outbound_scheduled, shipped_quantity=4, quantity=10`) + Q(`outbound_scheduled, shipped_quantity=0, quantity=5`)(AC-OLIST-007과 동일 — 규칙 2) | `partial_shipped` |
| C | 2개 모두 `received, shipped_quantity=0`(AC-OLIST-010과 동일 — 규칙 3 경유) | `outbound_scheduled` |
| D | uniform `outbound_scheduled, shipped_quantity=0`(신규 — 규칙 4 경유, `outbound_scheduled`의 두 번째 원인) | `outbound_scheduled` |
| E | `not_shipped, shipped_quantity=0, quantity=5`(AC-OLIST-008과 동일 — 규칙 4) | `not_shipped` |
| F | `shipment_confirmed, shipped_quantity=0`(AC-OLIST-013과 동일 — 규칙 4) | `shipment_confirmed` |
| G | 항목1=`not_shipped` + 항목2=`shipment_confirmed`, 둘 다 `shipped_quantity=0`(AC-OLIST-013a와 동일 — 규칙 4a) | `partial` |
| H | 항목1=`outbound_scheduled` + 항목2=`shipment_confirmed`, 둘 다 `shipped_quantity=0`(신규, 감사 N1 — 혼재 상태이지만 `outbound_scheduled`를 포함한다) | `partial` |

**Order H가 필요한 이유(N1)**: G는 `{not_shipped, shipment_confirmed}`만 섞여 있어 `all_not_shipped`/`all_shipment_confirmed`의 `any` mutation은 잡지만, `outbound_scheduled` uniform 검사(`all_outbound_scheduled`)를 `any`로 잘못 구현하는 mutation은 A~G 중 어디에도 걸리지 않는다 — Order B도 `outbound_scheduled` 항목을 갖지만 `any_partial=True`이므로 필터의 앞단 가드에서 이미 제외된다. H는 `outbound_scheduled` 항목을 포함하면서도 uniform하지 않으므로(표시값 `partial`), `any` mutation이 적용되면 H가 `outbound_scheduled` 필터 결과에 잘못 추가되어 비로소 판별된다(AC-OLIST-022d 참조).

### AC-OLIST-022 — 필터: 부분출고 `[BE]`

Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025

- **Given**: 표준 데이터셋(Order A~H 전량).
- **When**: `GET /api/orders/?logistics_display=partial_shipped`.
- **Then**: 응답의 `count`가 `1`이고 `results`에는 Order B만 포함되며, Order B의 `logistics_display == "partial_shipped"`다(필터 결과와 표시값이 일치함을 함께 확인).
- **판별력**: 필터를 `Q(any_partial=True)`만으로 구현해 "전부 출고되지 않음"(`Q(all_shipped=False)`) 조건을 빠뜨리면, Order A(`shipped_quantity=quantity>0`이므로 `any_partial=True`이기도 함)가 잘못 포함되어 반환 집합이 {A, B}(`count == 2`)가 된다 — C2가 지목한 것과 동일한 우선순위 결함이 필터 경로에도 있을 수 있음을 이 AC가 직접 판별한다.
- **판별력(N2, REQ-OLIST-025)**: `OrderListView`가 SQL 쿼리셋에 필터를 적용하는 대신, 이미 페이지네이션된 `page`(전체 8건)를 표시값 계산과 동일한 Python 헬퍼로 사후 필터링하면 `results`는 우연히 맞아 보여도 `paginator.count`는 필터 이전 쿼리셋 크기(8)에서 계산되므로 `count == 8`(오답)이 되어 실패한다 — 프로덕션에서는 이 결함이 페이지네이션 자체를 조용히 깨뜨린다.

### AC-OLIST-022a — 필터: 출고 `[BE]`

Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025

- **Given**: 표준 데이터셋(Order A~H 전량).
- **When**: `GET /api/orders/?logistics_display=shipped`.
- **Then**: 응답의 `count`가 `1`이고 `results`에는 Order A만 포함되며, Order A의 `logistics_display == "shipped"`다.
- **판별력(N2)**: AC-OLIST-022와 동일한 원리 — Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

### AC-OLIST-022b — 필터: 미입고 (v1.2.0 재작성 — 표준 데이터셋으로 고정, H1-new) `[BE]`

Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025

- **Given**: 표준 데이터셋(Order A~H 전량 — **특히 Order G가 반드시 포함**).
- **When**: `GET /api/orders/?logistics_display=not_shipped`.
- **Then**: 응답의 `count`가 `1`이고 `results`에는 Order E만 포함되며, Order E의 `logistics_display == "not_shipped"`다.
- **판별력**: 필터를 `Exists(trackable_qs.filter(logistics_status="not_shipped"))`(any, uniform 아님)로 구현하면, Order G(`not_shipped` 항목을 하나 포함하지만 표시값은 `partial`)가 결과 집합에 잘못 추가되어 `count == 2`(집합 {E, G})가 된다 — 데이터셋에 Order G가 없으면(v1.1.0처럼 "그 외 상태 1건"만 넣으면) 이 mutation이 발견되지 않는다(H1-new의 핵심 지적).
- **판별력(N2)**: Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

### AC-OLIST-022c — 필터: 입고예정 (v1.2.0 재작성 — 표준 데이터셋으로 고정, H1-new) `[BE]`

Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025

- **Given**: 표준 데이터셋(Order A~H 전량 — **특히 Order G가 반드시 포함**).
- **When**: `GET /api/orders/?logistics_display=shipment_confirmed`.
- **Then**: 응답의 `count`가 `1`이고 `results`에는 Order F만 포함되며, Order F의 `logistics_display == "shipment_confirmed"`다.
- **판별력**: `any`(uniform 아님) 기반 구현은 Order G(`shipment_confirmed` 항목을 하나 포함)를 잘못 포함시켜 `count == 2`(집합 {F, G})가 된다 — AC-OLIST-022b와 대칭인 판별 지점.
- **판별력(N2)**: Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

### AC-OLIST-022d — 필터: 출고예정, 두 원인 모두 (v1.2.0 강화 — 필터 ∧ 표시값 이중 단정, H2-new; v1.2.1 Order H로 any/all 판별력 확보, N1) `[BE]`

Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025

- **Given**: 표준 데이터셋(Order A~H 전량 — Order C(규칙 3 경유)와 Order D(규칙 4 경유)를 모두 포함).
- **When**: `GET /api/orders/?logistics_display=outbound_scheduled`.
- **Then**: 응답의 `count`가 `2`이고 `results`에는 정확히 {Order C, Order D}가 포함되며, **Order C와 Order D 둘 다**의 `logistics_display == "outbound_scheduled"`다.
- **판별력**: 규칙 4를 3개 값에 대한 명시적 if-체인으로 구현하면서 `outbound_scheduled` 분기를 빠뜨리면(→ Order D가 `partial`로 잘못 계산됨), Order D가 필터 결과에서 빠질 뿐 아니라 **Order D 자신의 `logistics_display` 표시값도 `"outbound_scheduled"`가 아니게 된다** — v1.1.0은 필터 결과(Then)만 확인해 표시값 쪽 mutation을 놓쳤다(H2-new). 필터를 `Q(all_received=True)`만으로(규칙 4 경유 원인을 빠뜨리고) 구현해도 Order D가 반환 집합에서 누락되어 `count == 1`이 된다.
- **판별력(N1)**: `all_outbound_scheduled`(uniform 검사)를 `Exists(trackable_qs.filter(logistics_status="outbound_scheduled"))`(any)로 잘못 구현하면, Order H(`outbound_scheduled`+`shipment_confirmed` 혼재, 표시값은 `partial`)가 "적어도 하나는 outbound_scheduled"를 만족해 잘못 포함되어 `count == 3`(집합 {C, D, H})이 된다 — 데이터셋에 Order H가 없으면(v1.2.0처럼 A~G뿐이면) 이 mutation은 어디에도 걸리지 않는다.
- **판별력(N2)**: Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

### AC-OLIST-022e — 필터: 부분입고 (v1.2.0 재작성 — 표준 데이터셋으로 고정, H1-new; v1.2.1 Order H 반영해 기대 집합을 {G,H}로 갱신, N1) `[BE]`

Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025

- **Given**: 표준 데이터셋(Order A~H 전량 — **특히 Order D가 반드시 포함**).
- **When**: `GET /api/orders/?logistics_display=partial`.
- **Then**: 응답의 `count`가 `2`이고 `results`에는 정확히 {Order G, Order H}가 포함되며(둘 다 표시값 `partial` — G는 `{not_shipped, shipment_confirmed}` 혼재, H는 `{outbound_scheduled, shipment_confirmed}` 혼재), **Order G와 Order H 둘 다**의 `logistics_display == "partial"`다.
- **판별력**: `partial` 필터 조건에서 `¬all_outbound_scheduled`(Order D를 배제하는 조건) 절을 빠뜨리면, Order D(uniform `outbound_scheduled`)가 "3개 uniform 검사 중 어느 것도 해당 안 됨"으로 오판되어 잘못 포함되어 `count == 3`(집합 {D, G, H})이 된다 — 데이터셋에 Order D가 없으면 이 mutation이 발견되지 않는다.
- **판별력(N2)**: Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

### AC-OLIST-022f — 허용 외 필터 값은 무시된다 (fail-open, 신규 v1.2.0, M2-new) `[BE]`

Traces: REQ-OLIST-024a

- **Given**: 표준 데이터셋(Order A~H 전량, 8건).
- **When**: `GET /api/orders/?logistics_display=bogus_value`(REQ-OLIST-024의 6개 값에 속하지 않음).
- **Then**: HTTP 200, 응답에 8건 전부(필터를 적용하지 않은 것과 동일한 전체 결과)가 포함된다.
- **판별력**: 화이트리스트 검사 없이 값을 그대로 SQL 조건에 매핑하려는 구현은(예: 매칭되는 분기가 없어 "일치하는 것 없음"을 의미하는 기본 필터로 떨어짐) 0건을 반환한다 — REQ-OLIST-024a가 명시적으로 금지하는 "silently return zero results" 상태이며, 이 AC가 직접 판별한다. v1.1.0에서는 이 요구사항이 `plan.md`의 존재하지 않는 DoD 게이트로만 위임되어 어떤 런타임 테스트도 이를 검증하지 않았다(M2-new).

### AC-OLIST-023 — 필터의 쿼리 수 불변식 `[BE]`

Traces: REQ-OLIST-025

- **Given**: `logistics_display` 필터 조건에 매칭되는 주문 5건(고객 연결 포함).
- **When**: (워밍업 요청 후) 필터 없이 5건을 반환하는 요청과 `?logistics_display=partial_shipped`로 5건을 반환하는 요청 각각을 캡처한다.
- **Then**: 두 요청의 총 쿼리 수가 동일하다.
- **판별력**: 필터를 "먼저 전체 조회 후 Python에서 각 주문의 라인아이템을 별도 쿼리로 다시 조회해 판정"하는 방식으로 구현하면 주문 수만큼 쿼리가 추가되어 필터 요청의 쿼리 수가 더 커진다.

## 회귀

### AC-OLIST-024 — 백엔드 파라미터 회귀 없음 (감사 M10 — 구체적 기대값) `[BE]`

Traces: REQ-OLIST-034

- **Given**: `financial_status="paid"`인 주문 1건, `financial_status="refunded"`인 주문 1건, `financial_status="pending"`인 주문 1건. 별도로, `fulfillment_status=null`인 주문 1건과 `fulfillment_status="fulfilled"`인 주문 1건.
- **When**: `GET /api/orders/?financial_status=paid`와 `GET /api/orders/?fulfillment_status=unfulfilled`를 각각 요청한다.
- **Then**: 전자는 정확히 `financial_status="paid"`인 주문 1건만 반환하고, 후자는 정확히 `fulfillment_status=null`인 주문 1건만 반환한다(각 파라미터 처리 블록이 무수정임을 `git diff`로도 확인).
- **판별력(M10)**: 이전 버전의 "이 SPEC 이전과 동일하게 필터링된다"는 서술은 구체적 기대값이 없어 판정에 주관이 개입했다 — 이 버전은 정확한 카운트와 대상을 단정한다.

### AC-OLIST-025 — `OrderDetailSerializer` 응답 키 집합 회귀 없음 (감사 M5 — 자동화 가능 부분만 분리) `[BE]`

Traces: REQ-OLIST-033

- **Given**: SPEC-ORDER-021 AC-COST-001 픽스처와 동일한 주문 1건.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: 응답의 키 집합이 `test_spec_021.py`의 T1(`test_t1_single_sku_korea_warehouse_fee`)이 이미 단정하는 키 집합(`margin_amount`, `korea_warehouse_cost`, `shipping_cost`, `total_weight_grams` 등)과 동일하다. **그리고** `test_spec_021.py`의 T1~T10, T12~T22(21개, T11은 결번)이 무수정 재통과한다.
- **수동 게이트(pytest 단정 아님, `plan.md` Done 체크리스트로 이동)**: 계산 로직 자체가 리팩터링 전후 동일한지는 `git diff`로 `OrderDetailSerializer` 블록의 값 변경 여부를 확인한다 — "이 SPEC 적용 전과 완전히 동일하다"는 서술 자체는 자동화된 단정으로 표현할 수 없다(감사 M5).

## 프론트엔드 필터·렌더링

### AC-OLIST-026 — 물류상태 필터 드롭다운: 옵션 전량 존재 + 선택 상호작용 (감사 M4 스코프 조회 + v1.2.0 M3-new 확장) `[FE]`

Traces: REQ-OLIST-026, REQ-OLIST-027

- **Given**: `OrdersPage`가 렌더되어 있다.
- **When (1차)**: `aria-label="물류상태 필터"` 셀렉트(드롭다운 요소로 스코프 — 테이블 셀의 동일 텍스트와 혼동하지 않는다)의 `<option>` 목록을 조회한다.
- **Then (1차)**: 정확히 7개 옵션이 존재한다 — "전체" + REQ-OLIST-024의 6개 값, 각각 정확한 한글 라벨(미입고/입고예정/출고예정/부분출고/출고/부분입고)과 짝을 이룬다.
- **When (2차)**: "부분출고" `<option>`을 선택한다.
- **Then (2차)**: 다음 `GET /api/orders/` 요청의 쿼리 파라미터에 `logistics_display=partial_shipped`가 포함된다(`useOrders` 모킹의 호출 인자로 단정).
- **판별력(M3-new)**: 옵션을 2개(전체 + 부분출고)만 구현해도 v1.1.0의 단일 선택 상호작용 단정(2차에 해당)은 통과했다 — 1차의 "7개 옵션 전량 존재" 단정이 이 mutation을 잡는다.

### AC-OLIST-027 — 프론트엔드 라벨 렌더링: 6개 값 전량 파리티 (감사 M4 행 스코프 조회 + v1.2.0 M3-new 확장) `[FE]`

Traces: REQ-OLIST-030, REQ-OLIST-031, REQ-OLIST-032

- **Given (1차)**: `logistics_display: null, purchase_display: null, margin_rate: null`인 주문.
- **When (1차)**: `OrdersPage`를 렌더링한다.
- **Then (1차)**: 해당 행(`within(row)`으로 스코프)에서 물류상태/발주상태/마진율 세 셀 모두 "-"가 렌더된다.
- **Given (2차, 파라미터화 — 6개 값 각각에 대해 반복)**: `logistics_display`가 각각 `not_shipped`/`shipment_confirmed`/`outbound_scheduled`/`partial_shipped`/`shipped`/`partial`인 주문 6건(주문마다 1개 값).
- **When (2차)**: `OrdersPage`를 렌더링한다.
- **Then (2차)**: 각 주문의 행(스코프 조회)에서 물류상태 셀에 각각 "미입고"/"입고예정"/"출고예정"/"부분출고"/"출고"/"부분입고"가 렌더된다.
- **Given (3차)**: `purchase_display: "unordered", margin_rate: "67.75"`인 주문.
- **When (3차)**: `OrdersPage`를 렌더링한다.
- **Then (3차)**: 해당 행으로 스코프된 조회에서 발주상태 셀에 "미발주", 마진율 셀에 "67.75%"가 렌더된다.
- **행 스코프 조회를 쓰는 이유**: 물류상태 필터 드롭다운에도 "부분출고" 등 동일 텍스트 옵션이 존재해 문서 전체 대상 `getByText`는 다중 매칭으로 실패하기 때문이다(감사 M4).
- **판별력(M3-new)**: `logisticsStatusLabels.ts`를 로컬에서 스프레드로 확장하며 `partial_shipped`/`partial` 2개 키를 빠뜨리면(raw snake_case 값이 그대로 노출), v1.1.0은 `partial_shipped` 1개만 확인해 `partial` 키 누락을 발견하지 못했다 — 6개 전량 파라미터화가 이를 잡는다. `Order` 타입에 3개 필드를 추가하지 않고 컴포넌트가 접근하면 `tsc -b` 컴파일 오류로 실패한다(회귀 게이트). null 폴백을 빠뜨리면 1차 단정이 "null" 또는 빈 문자열 렌더링으로 실패한다.

---

## 품질 게이트 — Definition of Done 매핑

| AC | 테스트 파일 | 검증 대상 REQ |
|---|---|---|
| AC-OLIST-001~004 `[FE]` | `OrdersPage.test.tsx` | 004, 005, 006 |
| AC-OLIST-005 `[FE]` | `OrdersPage.test.tsx` | 001, 002, 003, 028, 029 |
| AC-OLIST-006~011 `[BE]` | `test_spec_023.py` | 007~010, 013(AC-011의 `purchase_display` 단정분) |
| AC-OLIST-012 `[BE]` | `test_spec_023.py` | 012 |
| AC-OLIST-013, 013a `[BE]` | `test_spec_023.py` | 011, 011a |
| AC-OLIST-014, 014a, 014b, 015, 016 `[BE]` | `test_spec_023.py` | 013~015 (014a/014b는 v1.4.0 신규) |
| AC-OLIST-017, 017a `[BE]` | `test_spec_023.py` | 016 |
| AC-OLIST-018, 018a, 018b `[BE]` | `test_spec_023.py` | 017 |
| AC-OLIST-019~021 `[BE]` | `test_spec_023.py` | 019~022a |
| AC-OLIST-020a `[BE]` | `test_spec_023.py` | 020 |
| AC-OLIST-022~022e `[BE]` | `test_spec_023.py` | 023, 024, 025 |
| AC-OLIST-022f `[BE]` | `test_spec_023.py` | 024a |
| AC-OLIST-023 `[BE]` | `test_spec_023.py` | 025 |
| AC-OLIST-024 `[BE]` | `test_spec_023.py` | 034 |
| AC-OLIST-025 `[BE]` | `test_spec_023.py` + `test_spec_021.py`(무수정 재통과) | 033 |
| AC-OLIST-026~027 `[FE]` | `OrdersPage.test.tsx` | 026, 027, 030~032 |

**추가 회귀 게이트** (신규 테스트가 아니라 기존 스위트의 무수정 통과):

- `backend/order/tests/test_spec_021.py`의 T1~T10, T12~T22(21개, T11 결번) — 마진 공식 추출 리팩터링 후에도 무수정 통과.
- `backend/order/tests/` 전체 스위트.
- `frontend/src/pages/OrdersPage.test.tsx`의 기존 sync-status 테스트 7개(`:85, 94, 104, 118, 132, 145, 159`) 무수정 통과.
- `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx` 전량 — `buildOrder()` 기본값 추가 후에도 통과.
- `npm run build`(`tsc -b`) 통과.

## Definition of Done

- [ ] `OrderListSerializer`에 `margin_rate`/`logistics_display`/`purchase_display` 3개 필드 추가 완료 — 셋 다 `Order.status`를 읽지 않는다.
- [ ] `OrderListView`에 배치 환율 로드(슬림 프로젝션, 하한 없음, `.date()`를 `_get_exchange_rate`와 동일한 방식으로 적용) + `logistics_display` 필터(`LineItem` 전용, 허용 외 값은 fail-open) 구현 완료.
- [ ] REQ-OLIST-001~034(하위 011a/022a/024a 포함) 전 항목 및 AC-OLIST-001~027(하위 013a/017a/018a/018b/020a/022a~f 포함) 전량 테스트 통과.
- [ ] REQ-OLIST-010/011/011a의 "at least one trackable line item" 가드가 실제로 구현에 반영되어, trackable 0개 주문에서 `logistics_display`가 `null`임을 확인했다(v1.2.0, C1-new).
- [ ] `frontend/src/pages/OrdersPage.tsx`의 9열 재구성 및 취소 배지(`getDisplayStatus` 앞 3분기만 재사용) 구현 완료, 물류상태 드롭다운·셀 라벨이 6개 값 전량에서 파리티를 이룬다(v1.2.0, M3-new).
- [ ] `test_spec_021.py`(T1~T10, T12~T22), 기존 백엔드/프론트엔드 테스트 스위트 회귀 없이 전량 통과.
- [ ] `git diff`로 `Order.status`/`Order.ready_to_ship`/`_recompute_order_aggregates` 무변경 확인.
- [ ] `product.md` 기능 목록에 SPEC-ORDER-023 항목 추가(sync 단계).
- [ ] `spec.md`/`plan.md`/`acceptance.md` `status: draft → completed` 전이 및 HISTORY 갱신.
