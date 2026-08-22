# SPEC-ORDER-027 — 인수 기준 (Acceptance Criteria)

대상 파일: `backend/order/tests/test_spec_027.py` `[NEW]`(AC-RACKRECV-001~006, 012) + `frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx` `[MODIFY]`(AC-RACKRECV-007~011)

## 0. 이 문서를 읽는 방법 — 판별력(mutation discrimination) 규약

[HARD] 통과하는 테스트가 곧 검증된 구현은 아니다. 이 SPEC의 모든 AC는 자신이 잡는 변이(mutation)를 명시한다.

**[감사 반영 — v0.1.0의 두 가지 실패 패턴을 다시 반복하지 않는다]**:
1. **D2(critical)**: v0.1.0의 AC-RACKRECV-004는 "`null + 3`이 `NaN`이 된다"는 잘못된 JS 지식을 근거로 판별력을 주장했으나 실제로는 `0 + null === 0`이라 아무것도 잡지 못했다. 이번 버전은 각 AC를 작성한 뒤 **변이 코드를 픽스처에 직접 대입해 결과값이 실제로 달라지는지 손으로 계산**했다 — 아래 각 AC의 "판별력" 절은 그 계산 결과다.
2. **D4(major)**: v0.1.0은 "AC-002가 M3의 유일 판별자"라고 주장했으나 실제로는 5개 AC가 공동으로 잡았다. 이번 버전은 "단독/유일"이라는 표현을 **실제로 그 AC 하나만 해당 변이를 잡을 때만** 사용하고, 여러 AC가 공동으로 잡는 경우 "공동 판별"로 정직하게 표기한다.

**[감사 D10 반영 — 회귀 확인 AC의 명시적 면제]**: 일부 AC(예: 접힘/펼침 상태 유지)는 이 SPEC이 도입하는 신규 로직에 대한 변이가 없다 — 순수하게 기존 동작이 새 헤더 형식에서도 깨지지 않는지 확인하는 회귀 테스트다. 이런 AC는 "잡는 변이: 없음(회귀 확인)"으로 명시적으로 분류하며, 이는 §0의 판별력 규약 위반이 아니라 별도로 인정된 카테고리다. 회귀 확인 AC를 마치 변이를 잡는 것처럼 위장하지 않는다.

이 SPEC이 반드시 잡아야 하는 **8개** 변이 (백엔드 5개, 프런트엔드 3개):

| ID | 범위 | 변이 | 판별 AC |
|----|------|------|---------|
| **M1** | BE | `logistics_status == "received"` 게이트를 남겨 부분 입고(다른 상태)를 놓침 | AC-RACKRECV-001 + AC-RACKRECV-004 (**공동** — v0.2.1 N1 정정: 이전 버전은 AC-001을 "단독"이라 주장하며 같은 셀에 AC-004를 공동 판별자로 나열하는 자기모순이 있었다. AC-001은 계속 유지한다 — 가장 단순한 단일 품목 증명) |
| **M2** | BE | 클램프(`min(received_quantity, net_qty)`) 누락 — raw `received_quantity`를 그대로 합산 | AC-RACKRECV-002(환불 경로), AC-RACKRECV-003(NULL 경로) — **두 AC가 공동으로 필요**(단독 아님, 서로 다른 원인 경로를 각각 증명) |
| **M3** | BE | 그룹 딕셔너리에 `received_quantity` 키 자체를 추가하지 않음 | 모든 백엔드 AC(001~006, 012)가 `KeyError`로 공통 검출. **AC-RACKRECV-005**가 "값이 0이어도 키가 존재"함을 증명하는 대표 케이스 |
| **M4** | BE | 미지정(`is_unassigned`) 그룹에서만 집계 로직이 빠지는 특수 케이스 | **AC-RACKRECV-006 (단독)** |
| **M8** | BE | `received_quantity` 누산기를 그룹별로 격리하지 않고 공유/전역 상태로 잘못 구현해 그룹 간에 값이 오염됨(v0.2.1 신규, 감사 N9) | **AC-RACKRECV-012 (단독)** — 기존 6개 BE AC는 전부 그룹 1개짜리 픽스처라 이 변이를 잡지 못했다 |
| **M5** | FE | API의 `received_quantity`/`total_quantity` 필드를 뒤바꾸거나 잘못 참조 | AC-RACKRECV-007, 008, 009, 010 — **네 AC 모두 공동으로 잡는다**(단독 아님, v0.2.1 N2: AC-010도 이 변이를 잡는다는 사실이 누락되어 있었다) |
| **M6** | FE | `receivedQuantity === 0`일 때 "입고" 세그먼트를 조건부로 숨김 | **AC-RACKRECV-008 (단독)** |
| **M7** | FE | 헤더 텍스트가 별도 요소로 쪼개져 `입고` 단독 리터럴과 충돌(D5) | **AC-RACKRECV-011 (단독)** |

> **M2가 두 AC를 필요로 하는 이유**: "클램프 누락"은 하나의 코드 결함이지만, 그 결함이 관측되려면 `received_quantity > net_qty`가 되는 상황이 필요하다. 그 상황은 두 개의 서로 다른 원인으로 발생할 수 있다 — (a) 환불이 나중에 기록되어 `net_qty`가 줄어든 경우(AC-002), (b) `quantity`가 `NULL`이라 `net_qty`가 애초에 0인데 `received_quantity`는 이미 양수인 경우(AC-003). 둘 중 하나만 테스트하면 다른 경로의 클램프 누락을 놓칠 수 있으므로 두 AC 모두 필요하다.
>
> **[v0.2.1 정정, 감사 N6] (b)는 실사용 시나리오가 아니라 방어적/도달 불가 케이스다.** 현재 유일한 쓰기 지점(`purchase_order_views.py:2525-2527`)은 `quantity IS NULL`이면 `effective_quantity = quantity or 0 = 0`이 되어 어떤 `received_count`든 `quantity_exceeded`로 거부하고 저장하지 않는다 — 즉 `quantity IS NULL` + `received_quantity > 0`은 이 쓰기 경로만으로는 만들어질 수 없다. `quantity`가 사후에(예: 가정 A2가 서술하는 Shopify 재동기화 경로, `shopify_orders.py:236/265/281`) `NULL`로 재기록되는 경우에만 간접적으로 도달 가능하다. AC-003은 클램프의 방어선으로서 계속 유지할 가치가 있으나, "자연 발생 시나리오"가 아니라 "방어적 핀(pin)"으로 읽어야 한다.

### 0.1 픽스처 규약

- 백엔드 테스트는 `backend/order/tests/test_spec_014.py`의 헬퍼 관례(`_make_order`, `_make_line_item`, `_find_group`, `_refund`)를 그대로 재사용하거나 동일 시그니처로 재정의한다 — 이 세션에서 그 파일 전체를 직접 읽고 확인했다.
- `received_quantity`는 `LineItem`의 실제 모델 필드이므로 `_make_line_item(order, ..., received_quantity=N)`으로 바로 전달 가능하다 — 헬퍼 확장이 필요 없다.
- 프런트엔드 테스트는 `SummaryTab.test.tsx:12-56`의 `buildResponse()` 패턴을 재사용하며, `RackNumberSummaryGroup` 픽스처에 `received_quantity` 필드를 추가한다.
- 모든 헤더 텍스트 단정은 그룹 헤더 `<button role="button">` 요소에 대해 `toHaveTextContent(...)`(부분 문자열 매칭, 기존 `SummaryTab.test.tsx:248-249`와 동일한 관례)로 확인한다 — 전체 텍스트 완전 일치가 아니라 부분 문자열 포함 여부를 확인한다(라벨과 개수 텍스트가 같은 버튼 안에 이어져 있으므로).

---

## 백엔드 AC (`test_spec_027.py`)

## AC-RACKRECV-001 — [핵심] 부분 입고: 상태가 아직 전환되지 않아도 `received_quantity`를 반영한다 `[BE]`

Traces: REQ-RACKRECV-002, REQ-RACKRECV-004
잡는 변이: **M1 (공동 — AC-004와 함께, v0.2.1 N1 정정)**

**Given** `rack_number="P-1"`, 라인아이템 1건: `quantity=5, received_quantity=3, logistics_status="shipment_confirmed"`, 환불 없음

**When** `GET /api/purchase-orders/line-items/rack-number-summary/`

**Then** 응답의 `P-1` 그룹: `total_quantity == 5`, `received_quantity == 3`

**판별력**: `net_qty = max(5-0,0) = 5`, 클램프 `min(3,5) = 3` → 정답은 `3`. `logistics_status == "received"` 게이트를 남겨둔 변이(M1)는 이 행의 상태가 `"shipment_confirmed"`이므로 게이트를 통과하지 못해 `received_quantity == 0`을 낸다 — `0 ≠ 3`이므로 즉시 잡힌다.

---

## AC-RACKRECV-002 — [핵심] 클램프: 입고 완료 후 환불로 `net_qty`가 줄어든 경우 `[BE]`

Traces: REQ-RACKRECV-002, REQ-RACKRECV-003
잡는 변이: **M2 (환불 경로, AC-003과 공동)**

**Given** `rack_number="P-2"`, 라인아이템 1건: `quantity=5, received_quantity=5, logistics_status="received"`, 환불 1건 `quantity=2`

**When** `GET /api/purchase-orders/line-items/rack-number-summary/`

**Then** 응답의 `P-2` 그룹: `total_quantity == 3`, `received_quantity == 3`

**판별력**: `refunded_qty=2`, `net_qty = max(5-2,0) = 3`. 클램프 적용 시 `min(5,3) = 3`(정답). 클램프를 생략한 변이(M2)는 raw `received_quantity=5`를 그대로 더해 `received_quantity == 5`를 낸다 — `5 ≠ 3`이며, 게다가 `5 > total_quantity(3)`이라는 논리적으로 불가능한 "입고 > 총" 상태가 되어 명백히 잡힌다.

---

## AC-RACKRECV-003 — [핵심] 클램프: `quantity`가 NULL이라 `net_qty`가 0인 경우 `[BE]`

Traces: REQ-RACKRECV-003, REQ-RACKRECV-005
잡는 변이: **M2 (NULL 경로, AC-002와 공동)**

**Given** `rack_number="P-3"`, 라인아이템 1건: `quantity=None, received_quantity=4, logistics_status="received"`, 환불 없음

**When** `GET /api/purchase-orders/line-items/rack-number-summary/`

**Then** 응답의 `P-3` 그룹: `total_quantity == 0`, `received_quantity == 0`

**판별력**: `net_qty = max((None or 0) - 0, 0) = 0`(기존/무변경 동작). `refunded_qty=0`(falsy)이므로 이 행은 `continue`로 드롭되지 않고 `net_qty=0`으로 포함된다. 클램프 적용 시 `min(4,0) = 0`(정답). 클램프를 생략한 변이는 raw `received_quantity=4`를 그대로 더해 `received_quantity == 4`를 낸다 — `4 ≠ 0`이며 `4 > total_quantity(0)`이므로 명백히 잡힌다.

**[v0.2.1 정정, 감사 N6] 이 픽스처의 현실성에 대한 정직한 고지**: 이 `quantity=None, received_quantity=4` 조합은 **현재 유일한 쓰기 지점으로는 도달할 수 없는 방어적 케이스**다. `purchase_order_views.py:2525-2527`은 `quantity IS NULL`이면 `effective_quantity=0`으로 계산해 어떤 `received_count ≥ 1`이든 `quantity_exceeded`로 거부하고 `received_quantity`를 갱신하지 않는다 — 즉 그 쓰기 경로만으로는 이 조합이 절대 만들어지지 않는다. 이 조합이 실제로 발생하려면 `quantity`가 **입고 이후에** `NULL`로 재기록되어야 한다(가정 A2/A3가 서술하는 Shopify 재동기화 경로, `shopify_orders.py:236/265/281` — `quantity`가 사후에 바뀔 수 있다는 것과 같은 메커니즘). 이 AC는 "실사용 시나리오 재현"이 아니라 "클램프가 이 극단값에서도 무너지지 않는지 확인하는 방어적 핀"으로 유지한다 — 그 가치 자체는 그대로다.

---

## AC-RACKRECV-004 — 다중 품목 그룹 합산 `[BE]`

Traces: REQ-RACKRECV-002, REQ-RACKRECV-004
잡는 변이: **M1 (공동 — AC-001과 함께, v0.2.1 N1 정정)**

**Given** `rack_number="P-4"`, 라인아이템 3건, 환불 없음:

| 라벨 | `quantity` | `received_quantity` | `logistics_status` |
|------|-----------|----------------------|---------------------|
| 1 | 2 | 2 | `received` |
| 2 | 4 | 1 | `shipment_confirmed` |
| 3 | 3 | 0 | `not_shipped` |

**When** `GET /api/purchase-orders/line-items/rack-number-summary/`

**Then** 응답의 `P-4` 그룹: `total_quantity == 9`(2+4+3), `received_quantity == 3`(2+1+0)

**판별력**: M1(상태 게이트)이 있으면 행 2(`shipment_confirmed`)가 제외되어 `received_quantity == 2`(2+0+0)를 낸다 — `2 ≠ 3`이므로 잡힌다. 단, 이 픽스처의 모든 행은 `received_quantity ≤ net_qty`이므로(2≤2, 1≤4, 0≤3) 클램프 유무는 결과에 영향을 주지 않는다 — **M2(클램프 누락)는 이 AC로 잡히지 않는다**(정직하게 명시, AC-002/003이 그 역할을 전담한다). 이 AC의 고유 가치는 단일 품목이 아닌 다중 품목 누적이 정확함을 확인하는 것이다.

---

## AC-RACKRECV-005 — 0건이어도 필드가 존재한다 `[BE]`

Traces: REQ-RACKRECV-001
잡는 변이: **M3 (대표 케이스)**

**Given** `rack_number="P-5"`, 라인아이템 1건: `quantity=3, received_quantity=0, logistics_status="not_shipped"`, 환불 없음

**When** `GET /api/purchase-orders/line-items/rack-number-summary/`

**Then** 응답의 `P-5` 그룹에 `"received_quantity"` 키가 **존재**하며(`"received_quantity" in group`) 그 값은 `0`이다. `total_quantity == 3`.

**판별력**: 그룹 딕셔너리에 `received_quantity` 키 자체를 추가하지 않는 변이(M3)는 `"received_quantity" in group`이 `False`가 되어 즉시 잡힌다. 값이 정답과 우연히 같은 `0`이라 하더라도 **키의 존재 자체**를 별도로 단정하므로, `.get("received_quantity", 0)` 같은 안이한 폴백으로 실제 결함(키 누락)을 가리는 상황도 검출한다.

---

## AC-RACKRECV-006 — 미지정(`is_unassigned`) 그룹도 동일하게 집계된다 `[BE]`

Traces: REQ-RACKRECV-002
잡는 변이: **M4 (단독)**

**Given** `rack_number=""`(미지정), 라인아이템 1건: `quantity=5, received_quantity=2, logistics_status="received"`(M1 게이트 변이와 얽히지 않도록 상태를 `"received"`로 고정), 환불 없음

**When** `GET /api/purchase-orders/line-items/rack-number-summary/`

**Then** 응답의 미지정 그룹(`rack_number == ""`, `is_unassigned == True`): `total_quantity == 5`, `received_quantity == 2`

**판별력**: 이 픽스처는 `logistics_status="received"`를 써서 M1(상태 게이트) 변이가 있어도 이 행은 게이트를 통과하므로 M1과 얽히지 않는다 — `received_quantity ≤ net_qty`(2≤5)이므로 M2(클램프)와도 얽히지 않는다. 미지정 그룹에서만 집계를 건너뛰는 특수 케이스 실수(M4, 예: 빈 문자열 키를 falsy로 취급해 `if key: ...` 형태의 조건 분기)만이 `received_quantity == 0`을 내어 `0 ≠ 2`로 잡힌다.

---

## 프런트엔드 AC (`SummaryTab.test.tsx`)

## AC-RACKRECV-007 — 헤더는 API가 준 `received_quantity`/`total_quantity`를 그대로 렌더링한다 `[FE]`

Traces: REQ-RACKRECV-008
잡는 변이: **M5 (공동 — AC-008/009와 함께)**

**Given** 그룹 `rack_number: 'A-1'`, `total_quantity: 5`, `received_quantity: 3`(API 응답 필드로 직접 설정, 클라이언트 계산 없음), `line_items`는 임의(헤더 값에 영향 없음)

**When** `<SummaryTab />`를 렌더링한다

**Then** `A-1` 그룹의 헤더 버튼 텍스트가 `입고 3 / 총 5권`을 포함한다.

**판별력**: `received_quantity`와 `total_quantity` 필드를 뒤바꿔 렌더링하는 변이(M5)는 `입고 5 / 총 3권`을 낸다 — `3`과 `5`가 서로 다른 값이므로 즉시 잡힌다.

---

## AC-RACKRECV-008 — [핵심] 입고 0건도 "입고 0 / 총 N권"을 그대로 표기한다 `[FE]`

Traces: REQ-RACKRECV-009
잡는 변이: **M6 (단독)**, M5(공동 보조)

**Given** 그룹 `rack_number: 'C-3'`, `total_quantity: 6`, `received_quantity: 0`

**When** `<SummaryTab />`를 렌더링한다

**Then** `C-3` 그룹의 헤더 버튼 텍스트가 정확히 `입고 0 / 총 6권`을 포함한다 — `입고` 세그먼트가 사라지거나 `총 6권`만 남지 않는다.

**판별력**: `receivedQuantity > 0`일 때만 `입고 ... /`를 붙이는 조건부 렌더링(M6)은 `총 6권`만 렌더해 "입고" 문자열이 아예 사라진다 — `toHaveTextContent('입고 0')` 단정이 즉시 실패한다. 이 픽스처는 필드 값이 `0`/`6`으로 다르므로 M5(필드 뒤바뀜, `입고 6 / 총 0권`)도 함께 잡는다.

---

## AC-RACKRECV-009 — 미지정(`is_unassigned`) 그룹도 동일한 형식으로 렌더링한다 `[FE]`

Traces: REQ-RACKRECV-010
잡는 변이: **M5 (공동 보조)**

**Given** 그룹 `rack_number: ''`, `is_unassigned: true`, `total_quantity: 4`, `received_quantity: 1`

**When** `<SummaryTab />`를 렌더링한다

**Then** 라벨 `미지정`을 표시하는 헤더 버튼의 텍스트가 `입고 1 / 총 4권`을 포함한다.

**판별력**: M5(필드 뒤바뀜)가 있으면 `입고 4 / 총 1권`을 낸다 — `1`과 `4`가 다르므로 잡힌다. 이 AC는 헤더 렌더 코드가 `is_unassigned` 그룹과 named 그룹 사이에 분기가 없음(공통 코드 경로)을 실증하는 것이 주 목적이며, M5에 대해서는 AC-007/008과 공동 판별이다.

---

## AC-RACKRECV-010 — 접힘/펼침 상태와 무관하게 헤더 표기가 유지된다 `[FE]`

Traces: REQ-RACKRECV-011
잡는 변이: **M5(공동 보조)** — 그 외에는 회귀 확인 (v0.2.1 N2 정정)

**Given** 그룹 `rack_number: 'A-1'`, `total_quantity: 8`, `received_quantity: 3`

**When** `<SummaryTab />`를 렌더링하고, 접힘 상태에서 헤더 텍스트를 확인한 뒤 헤더 버튼을 클릭해 펼치고 다시 확인한다

**Then** 두 상태 모두에서 헤더 버튼 텍스트가 `입고 3 / 총 8권`을 포함하며, `aria-expanded`가 각각 `false`→`true`로 정상 전환된다.

**목적 및 [v0.2.1 정정, 감사 N2]**: 이전 버전은 이 AC가 "잡는 변이: 없음"이라고 적었으나 이는 부정확했다 — 이 픽스처는 `received_quantity(3)`과 `total_quantity(8)`이 서로 다른 값이므로, M5(필드 뒤바뀜)가 있으면 `입고 8 / 총 3권`을 내어 `toHaveTextContent('입고 3 / 총 8권')` 단정이 실패한다. 따라서 이 AC는 M5의 (단독은 아닌) 공동 판별자다. 다만 이 AC의 주된 목적은 여전히 접힘/펼침 상태 전환(`aria-expanded`, 테이블 표시/숨김)이 새 헤더 형식에서도 기존 `SummaryTab.test.tsx:237-270` 동작대로 유지되는지 확인하는 회귀 테스트이며, 그 부분에 한해서는 이 SPEC이 도입하는 신규 로직에 대한 변이가 없다(§0의 면제 카테고리가 적용되는 부분).

---

## AC-RACKRECV-011 — [핵심, D5 대응] 헤더는 단일 텍스트 노드이며 `입고` 단독 리터럴과 충돌하지 않는다 `[FE]`

Traces: REQ-RACKRECV-012
잡는 변이: **M7 (단독)**

**Given** 그룹 `rack_number: 'A-1'`, `total_quantity: 8`, `received_quantity: 3`, `line_items`에 `logistics_status: 'received'`인 행 1건 포함(펼쳤을 때 그 행의 물류상태 셀이 라벨 `입고`를 렌더하도록, `purchaseOrderApi.ts:78`)

**When** `<SummaryTab />`를 렌더링하고 `A-1` 헤더 버튼을 클릭해 펼친다

**Then** `screen.getAllByText('입고', { exact: true })`가 정확히 **1개** 요소를 반환한다(펼쳐진 테이블의 물류상태 셀 하나뿐).

**판별력**: 헤더를 `<span>입고</span><span>{n} / 총 {t}권</span>`처럼 별도 요소로 쪼개는 변이(M7)는 헤더의 `입고` 텍스트도 정확히 일치하는 별도 노드가 되어, `getAllByText('입고', {exact:true})`가 헤더의 것 + 물류상태 셀의 것 총 **2개**를 반환한다 — 길이 단정(`toHaveLength(1)`)이 즉시 잡는다. 이 AC는 기존 `SummaryTab.test.tsx:103`의 `getByText('입고')` 단일 매치 단정을 영구적인 회귀 방어선으로 승격한 것이다(`plan.md` §2 M3에서 그 기존 단정을 헤더 변경 직후 직접 재실행해 확인하는 절차와 짝을 이룬다).

---

## AC-RACKRECV-012 — [v0.2.1 신규, 감사 N9] 그룹 간 입고 수량이 서로 오염되지 않는다 `[BE]`

> 번호가 011 다음이지만 성격은 백엔드(`test_spec_027.py`)다 — 기존 AC 번호(001~011)의 인용 안정성을 위해 끝에 추가했다.

Traces: REQ-RACKRECV-002
잡는 변이: **M8 (단독)**

**Given** 서로 다른 두 그룹, 환불 없음, 둘 다 `logistics_status="received"`(M1과 얽히지 않도록 고정):

| 그룹 | `quantity` | `received_quantity` |
|------|-----------|----------------------|
| `rack_number="Q-1"` | 5 | 3 |
| `rack_number="Q-2"` | 4 | 1 |

**When** `GET /api/purchase-orders/line-items/rack-number-summary/`

**Then** 두 그룹의 값이 각각 독립적으로 성립한다:
- `Q-1` 그룹: `total_quantity == 5`, `received_quantity == 3`
- `Q-2` 그룹: `total_quantity == 4`, `received_quantity == 1`

**판별력**: 기존 AC-RACKRECV-001~006은 전부 그룹이 **1개**뿐인 픽스처였다 — 응답에 그룹이 하나뿐이면, `received_quantity` 누산기를 그룹별 딕셔너리(`groups.setdefault(key, {...})`)가 아니라 함수 스코프의 공유 변수로 잘못 선언한 변이(예: `shared = 0`을 두고 매 반복마다 `group["received_quantity"] = shared`처럼 누적값을 현재 그룹에 계속 덮어쓰는 형태)도 유일한 그룹의 값과 공유 누산기의 값이 항상 같으므로 **6개 AC 전부를 통과한다**.

이 픽스처는 그룹이 2개이므로 그 결함이 드러난다. 조회는 `rack_number` 오름차순으로 정렬되므로(`purchase_order_views.py:3439`) `Q-1`이 먼저 처리된다. M8 아래에서: `Q-1` 처리 후 공유 누산기 = 3 → `group["received_quantity"] = 3`(정답과 우연히 일치). `Q-2` 처리 후 공유 누산기 = 3+1 = 4 → `group["received_quantity"] = 4`로 **덮어써진다** — 정답은 `1`인데 `4`가 나온다. `Q-2`의 단정(`received_quantity == 1`)이 `4 ≠ 1`로 즉시 잡는다. `Q-1`만 단정했다면 이 변이는 발견되지 않았을 것이다 — 두 그룹을 **모두** 독립적으로 단정하는 것이 이 AC의 핵심이다.

---

## 추적표 (AC → 변이)

| AC | 범위 | 성격 | 잡는 변이 |
|----|------|------|-----------|
| AC-RACKRECV-001 | BE | 핵심 판별자 | M1(001+004, **공동** — v0.2.1 N1 정정) |
| AC-RACKRECV-002 | BE | 핵심 판별자 | M2(환불 경로, 003과 공동) |
| AC-RACKRECV-003 | BE | 핵심 판별자(방어적 케이스, N6) | M2(NULL 경로, 002와 공동) |
| AC-RACKRECV-004 | BE | 다중 품목 합산 | M1(001+004, 공동) |
| AC-RACKRECV-005 | BE | 필드 존재 확인 | M3(대표 케이스, 전 BE AC 공통 안전망) |
| AC-RACKRECV-006 | BE | 핵심 판별자 | **M4 (단독)** |
| AC-RACKRECV-007 | FE | 기본 렌더링 | M5(007/008/009/010 공동) |
| AC-RACKRECV-008 | FE | 핵심 판별자 | **M6 (단독)**, M5(공동 보조) |
| AC-RACKRECV-009 | FE | 미지정 그룹 | M5(공동 보조) |
| AC-RACKRECV-010 | FE | 회귀 확인 + M5 공동 보조(v0.2.1 N2 정정) | M5(공동 보조), 그 외 없음(§0 면제) |
| AC-RACKRECV-011 | FE | 핵심 판별자(D5) | **M7 (단독)** |
| AC-RACKRECV-012 | BE | 그룹 간 격리(v0.2.1 신규, N9) | **M8 (단독)** |

**변이 커버리지 확인**: M1(001+004, 공동 — v0.2.1 N1 정정, 단독 아님) M2(002+003, 공동 필수) M3(005 대표, 전체 안전망) **M4(006 단독)** M5(007+008+009+010, 4중 공동 — v0.2.1 N2에서 010 추가) **M6(008 단독)** **M7(011 단독)** **M8(012 단독, v0.2.1 N9 신규)** — 8개 변이 전부 최소 1개 AC가 잡으며, M4/M6/M7/M8 네 건은 진짜 단독 판별자다.

**[HARD] 단독 판별자 보호 규칙**: AC-RACKRECV-006/008/011/012 중 하나라도 삭제·약화·픽스처 변경되면 해당 변이가 즉시 미커버가 된다(v0.2.1 N1 정정 — AC-001은 M1의 공동 판별자일 뿐 단독이 아니므로 이 목록에서 제외했다. AC-001 자체는 계속 유지한다 — 가장 단순한 단일 품목 증명이라는 가치는 그대로다). 특히:
- AC-RACKRECV-006의 "`rack_number=""`, `logistics_status="received"`" — 상태를 `"received"`로 고정해 M1과 얽히지 않게 격리한 설계를 유지해야 한다
- AC-RACKRECV-008의 "`received_quantity: 0`" — 0값 자체가 판별력이다
- AC-RACKRECV-011의 "펼쳤을 때 물류상태 `입고` 라벨이 존재하는 픽스처" + `getAllByText(..., {exact:true})`의 길이 단정 — 존재 단정(`toBeInTheDocument`)만으로는 개수 증가를 검출하지 못한다
- AC-RACKRECV-012의 "서로 다른 두 그룹, 각 그룹의 값이 서로 다르고 각자의 `total_quantity`와도 다름" — 그룹이 하나뿐이거나 두 그룹 값이 우연히 같으면 판별력을 잃는다

**AC-002/003(M2 공동 판별)에 대한 별도 보호**: 두 AC 중 하나만 남으면 다른 경로(환불 vs NULL)의 클램프 누락을 놓친다 — 둘 다 유지한다. AC-003은 v0.2.1부터 "방어적/도달 불가 케이스"로 재서술되었지만(N6) 판별력 자체는 무변경이다.

---

## 엣지 케이스 요약

| # | 케이스 | 대응 AC |
|---|--------|---------|
| 1 | 부분 입고 (상태 미전환) | AC-RACKRECV-001 |
| 2 | 클램프 — 환불로 `net_qty` 축소 | AC-RACKRECV-002 |
| 3 | 클램프 — `quantity` NULL로 `net_qty=0`(방어적/현재 쓰기 경로로는 도달 불가, N6) | AC-RACKRECV-003 |
| 4 | 다중 품목 그룹 합산 | AC-RACKRECV-004 |
| 5 | 입고 0건, 필드 존재 확인 | AC-RACKRECV-005, AC-RACKRECV-008 |
| 6 | 미지정(`is_unassigned`) 그룹 | AC-RACKRECV-006(BE), AC-RACKRECV-009(FE) |
| 7 | 접힘/펼침 상태 전환 시에도 헤더 값 유지 | AC-RACKRECV-010 |
| 8 | 헤더-행 라벨 텍스트 충돌 방지(D5) | AC-RACKRECV-011 |
| 9 | 그룹 간 입고 수량 격리(v0.2.1 신규, N9) | AC-RACKRECV-012 |

---

## Definition of Done

### 신규 검증
- [ ] AC-RACKRECV-001 ~ AC-RACKRECV-006, AC-RACKRECV-012 전부 통과 (`backend/order/tests/test_spec_027.py`)
- [ ] AC-RACKRECV-007 ~ AC-RACKRECV-011 전부 통과 (`SummaryTab.test.tsx`)
- [ ] **RED 성립 확인**: 백엔드 7개 AC 전부 — 작성 직후 무수정 코드에서 실행해 전부 실패(`KeyError` 또는 `AssertionError`)함을 직접 확인한다. 프런트엔드 5개 AC 전부 — 무수정 코드(`총 {n}권` 형식, `received_quantity` 필드 없음)에서 타입 에러 또는 텍스트 불일치로 실패함을 확인한다
- [ ] AC-RACKRECV-006/008/011/012의 단독 판별 픽스처를 §추적표의 규약대로 유지한다(단순화·약화 금지). AC-001은 M1의 공동 판별자이므로 이 목록에서 제외한다(v0.2.1 N1) — 그렇다고 AC-001을 삭제해도 되는 것은 아니다, AC-004와 함께 M1을 계속 커버해야 한다
- [ ] AC-RACKRECV-002/003 두 AC 모두 유지한다(하나만으로는 M2를 완전히 커버하지 못함)
- [ ] AC-RACKRECV-012의 두 그룹(`Q-1`, `Q-2`) 단정을 모두 유지한다 — 하나만 남으면 그룹 간 격리 결함(M8)을 놓친다

### 회귀 검증
- [ ] `backend/order/tests/test_spec_014.py` 전부 **무수정** 통과 — 특히 `TestTotalQuantity`(`:176-195`)와 `TestRefundExclusion`(`:333-432`)이 `total_quantity` 값을 그대로 재확인
- [ ] `SummaryTab.test.tsx`의 기존 테스트(`AC-RACKSUM-*` 라벨) 전부 통과 — 특히 `:103`의 `getByText('입고')` 단정을 헤더 변경 직후 **직접 재실행해 통과를 확인**(가정 금지, `plan.md` §2 M3)
- [ ] `git diff --stat frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx` 공집합
- [ ] `git diff` 로 `purchase_order_views.py:2392-2579`(`_process_warehouse_receipt_rows`) 및 `:3481-3489`(정렬 블록) 공집합 확인

### 코드 범위 검증
- [ ] `git diff backend/order/purchase_order_views.py` — 변경이 `:3442-3479` 집계 루프 내부(+신규 `@MX:NOTE`)에 국한된다
- [ ] `git diff frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx` — 변경이 헤더 span(`:96`) 하나에 국한되고 새 `<span>` 분리가 없다(D5)
- [ ] `SummaryTab.tsx:17-20`의 기존 `@MX:NOTE` 무삭제
- [ ] `backend/order/migrations/` 신규 파일 **0건**
- [ ] `RackNumberSummaryLineItem`(행 레벨 타입) 무변경

### 문서
- [ ] `spec.md` HISTORY에 구현 결과(통과 테스트 수, `:103` 재검증 결과, mx_plan 실행 결과) 기록
