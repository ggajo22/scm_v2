---
id: SPEC-ORDER-027
version: 0.2.1
status: draft
created_at: 2026-08-18
updated: 2026-08-18
author: ggajo
priority: Medium
issue_number: 0
labels: [order, logistics, rack-number, summary, frontend, backend]
---

# 렉번호 요약 탭 — 개수 표기를 "입고 / 총"으로 변경

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 0.1.0 | 2026-08-18 | ggajo | 최초 작성. `logistics_status === "received"`인 행의 `quantity` 합산으로 "입고"를 정의하는 프런트엔드 전용 SPEC. |
| 0.2.0 | 2026-08-18 | ggajo | plan-auditor 1차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-027-review-1.md`, iteration 1, **FAIL, 0.50**) 반영. **D1(critical)** — v0.1.0은 `LineItem.received_quantity`(`backend/order/models.py:228`, 기존 필드, `IntegerField(default=0)`)의 존재를 몰랐다. 이 필드는 `_process_warehouse_receipt_rows`(`purchase_order_views.py:2392-2579`)가 입고 업로드마다 누적하며, `logistics_status`는 `received_quantity >= quantity`가 될 때만 `"received"`로 전환된다(`:2549-2550`) — 즉 **부분 입고는 상태를 바꾸지 않는다**. v0.1.0의 "`received` 상태인 행만 카운트"라는 정의는 이 필드가 존재하는 한 부분 입고를 전부 0으로 표시하는 결함이었다. **사용자 재인터뷰로 입고 정의가 교체되었다**: `logistics_status` 기반 → `received_quantity` 기반(품목별 `min(li.received_quantity, net_qty)`의 그룹 합산, `net_qty`는 기존 환불 순액화 값 `purchase_order_views.py:3446`). 이 필드는 그룹 요약 응답에 없으므로 **더 이상 프런트엔드 전용이 아니다** — 백엔드가 그룹 레벨 `received_quantity`를 신규 집계해 응답에 추가해야 한다. **D2(critical)** — v0.1.0 AC-RACKRECV-004는 `null + 3`이 `NaN`이 된다는 잘못된 전제(`0 + null === 0`이 JS의 실제 동작)로 그 자신이 방어한다던 변이를 하나도 잡지 못했다. 새 설계는 프런트엔드에서 산술 자체를 제거해(REQ-RACKRECV-008) 이 결함 부류를 원천적으로 없앤다. **D3(major, MP-3 실패)** — frontmatter `created` → `created_at` 정정, `labels` 추가, `priority: low` → `Medium`(형제 SPEC 대문자 관례). **D4(major)** — 옛 acceptance.md가 "AC-002가 M3의 유일 판별자"라고 주장했으나 실제로는 5개 AC가 공동으로 잡았다 — 이번 버전은 모든 "단독/유일" 표시를 변이-AC 대조표로 직접 재검증했다. **D5(major)** — `SummaryTab.test.tsx:103`의 `getByText('입고')`(물류상태 `received` 라벨, `purchaseOrderApi.ts:78`과 동일 리터럴)와 신규 헤더 텍스트의 충돌 가능성을 REQ-RACKRECV-012(단일 텍스트 노드 요구) + AC-RACKRECV-011(전용 회귀 테스트)로 명문화했다. **D6(major)** — `(Unwanted)`로 잘못 라벨링된 무조건 `shall not` 문장 6개를 `(Ubiquitous)`로 정정하고, 진짜 조건부 클램프 요구(REQ-RACKRECV-003)만 올바른 `If … then` 형태의 `(Unwanted)`로 다시 썼다. **D7/D8(major/minor)** — v0.1.0의 "바이트 단위로 동일" 등가성 주장(클라이언트가 서버 순액화를 재현한다는 전제)은 새 아키텍처에서 통째로 폐기된다 — 클라이언트는 이제 어떤 산술도 하지 않고 API 값을 그대로 렌더링만 한다. **D9(minor)** — `null`/`undefined` 불일치 문구는 산술 제거로 무의미해져 삭제. **D10/D11(minor)** — 변이 없는 회귀 확인 AC는 acceptance.md §0에 명시적 면제 카테고리를 신설해 분류하고, 정렬 규칙(REQ-RACKRECV-016)은 존재하지 않는 테스트를 인용하는 대신 `git diff` 범위 확인으로 정직하게 재기술했다. **D12(minor)** — `priority: Medium`으로 정정. REQ 14개 → **18개**, AC 7개 → **11개**(백엔드 6 + 프런트엔드 5), 변이 7개(신규 체계). |
| 0.2.1 | 2026-08-18 | ggajo | plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-027-review-2.md`, iteration 2, **PASS, 0.75**) 반영. 5건 정정 + 1건 정리, 구조·요구사항 신설 없음(감사 지시 범위 준수). **N9(minor, 유일한 실질 공백)** — 기존 6개 백엔드 AC가 전부 그룹 1개짜리 픽스처라, `received_quantity` 집계를 그룹별로 격리하지 않고 공유 누산기에 쌓는 변이(예: `groups.setdefault` 스코프 밖으로 누산기를 끌어올리는 실수)가 6개 AC 전부를 통과할 수 있었다. **AC-RACKRECV-012**(그룹 2개, 서로 다른/각자의 합계와도 다른 `received_quantity`) 신설 + 변이 **M8** 등록으로 해소. **N1(major)** — acceptance.md:19가 "AC-001이 M1의 단독 판별자"라면서 같은 셀에 AC-004를 공동 판별자로 나열하는 자기모순이었다(§0의 [HARD] "단독은 진짜 단독일 때만" 규칙을 그 문서 스스로 위반). M1은 AC-001(0 vs 3)과 AC-004(2 vs 3) **공동** 판별로 정정하고, `:231`의 [HARD] 단독 판별자 목록에서 AC-001을 제거했다(AC-001은 유지 — 가장 단순한 단일 품목 증명이라는 가치는 그대로다). **N2(minor)** — AC-RACKRECV-010이 "잡는 변이: 없음(회귀 확인)"으로 분류되어 있었으나 실제로는 그 픽스처(`입고 3 / 총 8권`, 서로 다른 두 값)가 M5(필드 뒤바뀜, `입고 8 / 총 3권`)에서도 실패한다 — "M5(공동 보조) — 그 외에는 회귀 확인"으로 정정했다. **N4(minor)** — 가정 A2/A3가 `received_quantity > net_qty`의 원인으로 환불만 열거했으나, `LineItem.quantity` 자체가 Shopify 재동기화마다 덮어써진다(`backend/order/shopify_orders.py:236`, `common_defaults`의 `"quantity": li.get("quantity")`, `LineItem.objects.update_or_create`의 `defaults`로 사용되는 지점은 `:265`/`:281` — 이 세션에서 직접 확인). 전량 입고(5/5) 후 재동기화로 `quantity`가 3으로 하향 정정되면 환불 없이도 `received_quantity(5) > net_qty(3)`이 된다 — REQ-RACKRECV-003의 조건은 이미 원인 무관(cause-agnostic)이므로 요구사항 문구는 무변경이며, A2/A3에 이 두 번째 독립 원인을 추가해 클램프가 환불 단독 대응보다 더 무거운 방어선임을 명시했다. **N6(minor)** — acceptance.md의 AC-003(NULL quantity) 설명이 이 경로를 실사용 시나리오처럼 서술했으나, 현재 유일한 쓰기 지점(`purchase_order_views.py:2525-2527`)은 `quantity IS NULL`이면 `effective_quantity=0`이 되어 어떤 `received_count`든 `quantity_exceeded`로 거부하고 저장하지 않는다 — 즉 `quantity IS NULL` + `received_quantity > 0`은 그 쓰기 경로만으로는 도달 불가능하다. AC는 유지하되(클램프의 방어선으로서 여전히 가치 있음) 방어적/도달 불가 케이스로 정직하게 재서술했다(N4의 재동기화 경로를 통해서만 간접적으로 도달 가능). **REQ-RACKRECV-006 정리**(감사 N7 부수 지적) — `li.received_quantity`가 `IntegerField(default=0)`로 NULL이 될 수 없다는 것은 강제 가능한 시스템 행동이 아니라 모델 사실 서술이었고 이미 가정 A1과 중복이었다 — 별도 요구사항으로 유지하지 않고 가정 A1로 통합·폐기했다(번호는 결번으로 유지, 이하 REQ 번호 재부여 없음 — 인용 안정성을 위해 007~018은 그대로 둔다). REQ 18개(그 중 1개 폐기, 유효 17개), AC 11개 → **12개**, 변이 7개 → **8개**. |

---

## 1. Environment (환경)

| 항목 | 내용 |
|------|------|
| 대상 코드(백엔드) | `backend/order/purchase_order_views.py` `LineItemRackNumberSummaryView`(`:3397-3489`) — 그룹 집계 루프(`:3442-3479`)에 `received_quantity` 집계를 추가 |
| 대상 코드(프런트엔드) | `frontend/src/services/rackNumberApi.ts`(타입), `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx`(`RackNumberSummaryGroupSection`, `:58-134`) |
| 영향 화면 | `/rack-number` 페이지 "렉번호 요약" 탭(Tab2). Tab1("주문 검색", `SearchTab.tsx`)은 이 개수 표시를 렌더링하지 않는다 — 영향 없음 |
| 영향 API | `GET /api/purchase-orders/line-items/rack-number-summary/` — **응답 스키마가 바뀐다**: 각 그룹 객체에 `received_quantity: number` 필드가 추가된다. `RackNumberSummaryLineItem`(행 레벨 타입)은 무변경 — 행별 `received_quantity`는 노출하지 않는다 |
| 데이터 소재 | `LineItem.received_quantity`(`backend/order/models.py:228`, `IntegerField(default=0)`, **기존 컬럼**, 마이그레이션 `0037_lineitem_add_received_fields.py`로 이미 존재) — 이 SPEC은 이 값을 **읽기만** 한다 |
| 쓰기 경로(무변경) | `_process_warehouse_receipt_rows`(`purchase_order_views.py:2392-2579`)가 입고 업로드마다 `received_quantity`를 누적하고, 그 값이 `quantity`에 도달하면 `logistics_status`를 `"received"`로 전환한다(`:2549-2550`). 이 SPEC은 이 로직을 건드리지 않는다 |

## 2. Assumptions (명시적 가정)

| # | 가정 | 근거 / 틀렸을 때의 영향 |
|---|------|--------------------------|
| A1 | `li.received_quantity`는 항상 0 이상이며 NULL이 될 수 없다 | `IntegerField(default=0)`(`models.py:228`), 유일한 쓰기 지점은 `purchase_order_views.py:2542`의 `+=` 누적. 이 세션에서 `grep -r received_quantity backend/`로 다른 쓰기 경로가 없음을 확인했다 |
| A2 | `li.received_quantity`는 환불이 기록되어도 **소급 감산되지 않는다** — 환불 순액화(`net_qty`, `:3446`)와 입고 누적(`received_quantity`)은 서로 독립적인 값이다 | 이 세션에서 `backend/` 전체를 grep해 `received_quantity`를 쓰는 코드가 `:2542` 한 곳뿐임을 확인했다 — 환불(`Refund` 모델) 생성 경로 어디에도 `received_quantity`를 건드리는 코드가 없다. **이것이 REQ-RACKRECV-002/003의 클램프가 필요한 이유다**: 품목이 전량 입고된 뒤 환불되면 `received_quantity`(예: 5)가 그 시점의 `net_qty`(예: 3)보다 커질 수 있다 — 클램프 없이는 "입고 5 / 총 3"처럼 입고가 총을 초과하는 표시가 나온다. **[v0.2.1 추가, 감사 N4]** `received_quantity > net_qty`에는 **두 번째 독립 원인**이 있다 — 환불과 무관하게, `LineItem.quantity` 자체가 Shopify 재동기화마다 덮어써진다: `common_defaults`의 `"quantity": li.get("quantity")`(`backend/order/shopify_orders.py:236`)가 `LineItem.objects.update_or_create`의 `defaults`로 쓰인다(`:265`의 번들 분기, `:281`의 비번들 분기 — 이 세션에서 두 호출부 모두 직접 확인). 전량 입고(`received_quantity=5=quantity`) 후 재동기화가 `quantity`를 3으로 하향 정정하면, `Refund` 행이 **하나도 없어도** `net_qty`가 3으로 줄어 `received_quantity(5) > net_qty(3)`이 된다. REQ-RACKRECV-003의 조건("어떤 라인아이템의 `received_quantity`가 그 `net_qty`를 초과하면")은 원인을 명시하지 않는 cause-agnostic 서술이므로 이 두 번째 원인도 이미 요구사항 문구 그대로 커버된다 — **요구사항 텍스트는 변경하지 않는다.** 클램프는 "환불 대응"보다 더 무거운 방어선이다 |
| A3 | 입고 임계값 판정의 `effective_quantity`는 **원본** `li.quantity`이며 환불 순액이 아니다 | `effective_quantity = line_item.quantity or 0`(`:2525`) — A2의 괴리를 강화하는 근거. `received_quantity`는 원본 수량 기준으로 누적되므로 환불 후 순액과 어긋날 수 있다. **[v0.2.1 추가]** 이 `quantity`도 A2가 서술한 재동기화 경로(`shopify_orders.py:236/265/281`)로 사후에 바뀔 수 있으므로, "원본"이라는 표현은 "입고 임계값 판정 시점의 값"으로 읽어야 한다 — 그 값 자체가 이후 재동기화로 달라질 수 있다 |
| A4 | `logistics_status`의 타입은 `string`(리터럴 유니온 아님, `rackNumberApi.ts:65`)이지만, 이번 설계는 상태값을 전혀 비교하지 않으므로(REQ-RACKRECV-004) 상태 문자열 오타 위험은 이 SPEC의 범위에서 사실상 제거된다 | v0.1.0의 위험(C2)이었으나 재설계로 소멸 |

---

## 3. Requirements (EARS)

REQ 접두사는 `REQ-RACKRECV-`를 쓴다.

### 모듈 1 — 백엔드: 그룹별 입고 수량 집계 `[MODIFY]`

**REQ-RACKRECV-001** (Ubiquitous) [HARD]
`LineItemRackNumberSummaryView`(`purchase_order_views.py:3397-3489`)의 응답에서, 각 그룹 딕셔너리는 기존 `total_quantity`와 나란히 신규 필드 `received_quantity`(정수)를 **shall** 포함한다.

**REQ-RACKRECV-002** (Ubiquitous) [HARD]
그룹의 `received_quantity`는, 그 그룹에 기여하는(기존 필터를 통과하고 전량 환불로 드롭되지 않은) 모든 라인아이템에 대해 `min(li.received_quantity, net_qty)`를 누적한 값이어야 한다 — 여기서 `net_qty`는 `:3446`에서 이미 계산되는 값(`max((li.quantity or 0) - li.refunded_qty, 0)`)을 그대로 재사용하며, 중복 계산하지 않는다.

**REQ-RACKRECV-003** (Unwanted) [HARD]
**If** 어떤 라인아이템의 `received_quantity`가 그 `net_qty`를 초과하면(예: 입고 완료 후 환불이 기록되어 `net_qty`가 줄어든 경우), **then** the system **shall** 그 품목의 기여분을 `net_qty`로 클램프하고, **shall not** 클램프 없이 원본 `received_quantity`를 그대로 합산한다. `min(...)` 클램프(REQ-RACKRECV-002)를 raw 합산으로 단순화하는 것은 금지된다.

**REQ-RACKRECV-004** (Ubiquitous) [HARD]
REQ-RACKRECV-002의 집계는 `li.logistics_status` 값과 **무관하게** 균일하게 적용된다 — `logistics_status`가 아직 `"received"`로 전환되지 않은(예: `"shipment_confirmed"`) 품목도 `received_quantity`가 0보다 크면(부분 입고) 그 클램프된 값을 그룹 합계에 기여한다. **이것이 v0.1.0의 상태 기반 정의를 대체하는 핵심 변경이다** — 상태 기반 정의는 부분 입고를 전부 0으로 표시하는 결함이었다(`spec.md` HISTORY D1).

**REQ-RACKRECV-005** (State-Driven) [HARD]
**While** 어떤 기여 라인아이템의 `quantity`가 `NULL`이면, `net_qty`는 `0`으로 유지되고(기존/무변경 동작, `:3446`의 `(li.quantity or 0)`), 그 결과 그 품목이 `received_quantity` 그룹 합계에 기여하는 양도 `received_quantity`의 값과 무관하게 `0`이어야 한다 — REQ-RACKRECV-002/003의 클램프가 이를 강제한다.

**REQ-RACKRECV-006** — **[v0.2.1 폐기, 감사 N7]**
`li.received_quantity`가 `IntegerField(default=0)`로 NULL이 될 수 없다는 것은 강제 가능한 시스템 행동이 아니라 모델 스키마 사실 서술이었다(위반이 성립하지 않는 요구사항). 동일 내용은 이미 가정 A1(§2)에 있으므로 별도 요구사항으로 유지하지 않는다. 이 번호는 **의도적으로 결번 처리**한다 — 인용 안정성을 위해 REQ-RACKRECV-007~018의 번호는 재부여하지 않는다.

### 모듈 2 — API 계약 `[MODIFY]`

**REQ-RACKRECV-007** (Ubiquitous) [HARD]
`RackNumberSummaryGroup` 타입(`rackNumberApi.ts:68-73`)은 `received_quantity: number` 필드를 얻는다 — 그룹 레벨 필드만 추가하며, `RackNumberSummaryLineItem`(행 레벨 타입, `:59-66`)은 **shall not** 변경한다. 행별 `received_quantity`는 노출하지 않는다(§Exclusions).

### 모듈 3 — 프런트엔드 표기 `[MODIFY]`

**REQ-RACKRECV-008** (Ubiquitous) [HARD]
그룹 헤더(`RackNumberSummaryGroupSection`, `SummaryTab.tsx:96`)는 `입고 {group.received_quantity} / 총 {group.total_quantity}권`을 렌더링한다 — 두 값 모두 API 응답에서 그대로 읽으며, 클라이언트에서 어떤 산술(재계산, 가드, 재클램프)도 수행하지 않는다.

**REQ-RACKRECV-009** (State-Driven) [HARD]
**While** `group.received_quantity`가 `0`이면, 헤더는 `입고 0 / 총 {total}권`을 그대로 렌더링한다 — 숨기거나 생략하지 않는다.

**REQ-RACKRECV-010** (Ubiquitous)
미지정 그룹(`group.is_unassigned === true`)도 REQ-RACKRECV-008/009와 동일한 규칙을 따른다 — 특수 케이스 없음.

**REQ-RACKRECV-011** (State-Driven) [HARD]
**While** 그룹 섹션이 접히거나 펼쳐진 상태이든(`SummaryTab.tsx:65` `expanded`), 헤더의 `입고 {received} / 총 {total}권` 텍스트는 두 상태 모두에서 정확히 유지된다 — 기존 접힘/펼침 토글 동작은 변경하지 않는다.

**REQ-RACKRECV-012** (Ubiquitous) [HARD]
헤더의 개수 텍스트(`입고 {n} / 총 {t}권`)는 **단일 텍스트 노드/문자열**로 렌더링되어야 한다(하나의 요소 안에 결합된 문자열) — 어떤 요소의 정확한 텍스트도 `입고` 단독 리터럴과 일치해서는 안 된다. 이는 기존 `SummaryTab.test.tsx:103`의 `getByText('입고')` 단정(펼쳐진 라인아이템 테이블의 `received` 물류상태 라벨, `purchaseOrderApi.ts:78` `{ value: 'received', label: '입고' }`)과의 충돌을 방지한다.

### 모듈 4 — 비목표 불변식 (기존 동작 보존) `[EXISTING]`

**REQ-RACKRECV-013** (Ubiquitous) [HARD]
`SearchTab.tsx`(Tab1, "주문 검색")는 **shall not** 변경되며, 이 SPEC의 부수 효과로 어떤 개수 표시도 얻지 않는다.

**REQ-RACKRECV-014** (Ubiquitous) [HARD]
체크박스, 인라인 편집, 일괄 적용 컨트롤은 `SummaryTab.tsx` 어디에도 **shall not** 추가된다 — 기존 `@MX:NOTE`(`SummaryTab.tsx:17-20`, SPEC-ORDER-014 REQ-RACKSUM-014/015)가 주장하는 read-only 불변식은 계속 참이어야 하며, 그 태그는 삭제·수정되지 않는다.

**REQ-RACKRECV-015** (Ubiquitous) [HARD]
펼쳐진 라인아이템 테이블의 행별 `수량` 컬럼(`SummaryTab.tsx:122`, `item.quantity` 그대로 렌더)은 **shall not** 변경된다 — 새 헤더 집계와 별개다.

**REQ-RACKRECV-016** (Ubiquitous) [HARD]
그룹 정렬 규칙(이름별 알파벳, 미지정 버킷 항상 마지막, `purchase_order_views.py:3481-3487`)은 **shall not** 변경된다. **[감사 D11 정정]** 이 규칙을 검증하는 기존 테스트는 `SummaryTab.test.tsx`에 없다 — 존재하지 않는 테스트를 인용하지 않고, `git diff`로 `:3481-3489` 블록이 공집합인지 직접 확인하는 방식으로 검증한다(§DoD).

**REQ-RACKRECV-017** (Ubiquitous) [HARD]
`_process_warehouse_receipt_rows`(`purchase_order_views.py:2392-2579`, 입고 업로드 쓰기 경로)는 **shall not** 수정된다 — `received_quantity`를 쓰는 로직, 임계값 판정, `logistics_status` 전환 조건 전부 무변경.

**REQ-RACKRECV-018** (Ubiquitous) [HARD]
신규 DB 마이그레이션은 **shall not** 필요하다 — `received_quantity`는 이미 존재하는 컬럼(`models.py:228`, 마이그레이션 `0037_lineitem_add_received_fields.py`)이며 이 SPEC은 그 값을 읽기만 한다.

---

## 4. Traceability (REQ → AC)

| REQ | AC |
|-----|-----|
| REQ-RACKRECV-001 | AC-RACKRECV-005(대표: 0값이어도 필드 존재), 나머지 모든 백엔드 AC(001~006, 012)가 공통 안전망 |
| REQ-RACKRECV-002 | AC-RACKRECV-001, AC-RACKRECV-002, AC-RACKRECV-003, AC-RACKRECV-004, AC-RACKRECV-012 |
| REQ-RACKRECV-003 | AC-RACKRECV-002(환불로 인한 축소), AC-RACKRECV-003(NULL로 인한 축소, 방어적/현재 쓰기 경로로는 도달 불가 — §acceptance.md) |
| REQ-RACKRECV-004 | AC-RACKRECV-001 + AC-RACKRECV-004(공동, 단독 아님 — v0.2.1 N1 정정) |
| REQ-RACKRECV-005 | AC-RACKRECV-003 |
| REQ-RACKRECV-006 | **[v0.2.1 폐기]** 가정 A1로 통합, 별도 AC 없음 |
| REQ-RACKRECV-007 | AC 없음 — 컴파일 타임 검증(모든 프런트엔드 AC가 타입을 사용하므로 필드 누락 시 즉시 타입 에러) |
| REQ-RACKRECV-008 | AC-RACKRECV-007 |
| REQ-RACKRECV-009 | AC-RACKRECV-008 |
| REQ-RACKRECV-010 | AC-RACKRECV-009 |
| REQ-RACKRECV-011 | AC-RACKRECV-010 |
| REQ-RACKRECV-012 | AC-RACKRECV-011 |
| REQ-RACKRECV-013 | `git diff --stat SearchTab.tsx` 공집합 (AC 없음 — DoD 검증) |
| REQ-RACKRECV-014 | 기존 `AC-RACKSUM-014/015`(`SummaryTab.test.tsx:152-165`) 무수정 재통과 + `@MX:NOTE` 무삭제 (AC 없음 — DoD 검증) |
| REQ-RACKRECV-015 | 기존 `AC-RACKSUM-012`(`SummaryTab.test.tsx:89-107`) 무수정 재통과 (AC 없음 — DoD 검증) |
| REQ-RACKRECV-016 | `git diff` 로 `purchase_order_views.py:3481-3489` 공집합 확인 (AC 없음 — DoD 검증, 감사 D11: 대응 테스트 없음을 정직하게 기록) |
| REQ-RACKRECV-017 | `git diff` 로 `purchase_order_views.py:2392-2579` 공집합 확인 (AC 없음 — DoD 검증) |
| REQ-RACKRECV-018 | `backend/order/migrations/` 신규 파일 0건 확인 (AC 없음 — DoD 검증) |

> **[HARD] 추적표 무결성 규칙**: REQ가 그 위반을 실제로 검출할 수 없는 AC에 매핑되어 있으면 그 REQ는 미커버다. AC 없이 DoD 검사만으로 보증되는 REQ는 "(AC 없음 — DoD 검증)"으로 명시한다.

---

## 5. Exclusions (What NOT to Build)

1. **`SearchTab.tsx`(Tab1) 변경 — 하지 않는다.**
2. **행별 `received_quantity` 노출 — 하지 않는다.** `RackNumberSummaryLineItem`(행 레벨 타입)은 무변경이며, 펼쳐진 테이블의 `수량` 컬럼도 기존 `item.quantity` 그대로다. 그룹 레벨 집계만 추가한다(REQ-RACKRECV-007).
3. **Tab2의 read-only 성격 변경 — 하지 않는다.** 체크박스·인라인 편집·일괄 적용 등 어떤 입력 컨트롤도 추가하지 않는다.
4. **그룹 정렬 규칙 / 미지정 버킷 위치 — 변경하지 않는다.**
5. **신규 DB 마이그레이션 — 불필요하다.** `received_quantity`는 이미 존재하는 컬럼(`models.py:228`, 마이그레이션 `0037_lineitem_add_received_fields.py`)이며, 이 SPEC은 그 값을 읽기만 한다. (v0.1.0의 "API 스키마 무변경"이라던 옛 Exclusion #5는 D1로 인해 폐기됨 — 이번 버전은 API 스키마를 **의도적으로** 바꾼다.)
6. **입고 업로드 쓰기 경로 변경 — 하지 않는다.** `_process_warehouse_receipt_rows`(`purchase_order_views.py:2392-2579`)의 누적·임계값·상태 전환 로직은 전부 무변경이다.
7. **환불 시 `received_quantity`를 소급 감산하는 로직 신설 — 하지 않는다(범위 밖).** 클램프(REQ-RACKRECV-002/003)는 **표시 시점**에만 적용되며, 저장된 `LineItem.received_quantity` 값 자체는 이 SPEC으로 변경되지 않는다. "환불 시 입고수량을 실제로 조정해야 하는가"는 별도 판단이 필요한 후속 과제로 남긴다.

---

## 6. 알려진 제약 / 후속 과제

| # | 내용 |
|---|------|
| C1 | 가정 A2/A3의 결과, 어떤 라인아이템의 저장된 `received_quantity`가 그 시점의 `net_qty`를 초과하는 원본 데이터가 존재할 수 있다. 표시는 클램프로 항상 `입고 ≤ 총`을 유지하지만, 저장값 자체는 그 괴리를 드러내지 않는다. "환불 시 `received_quantity`를 조정해야 하는가"는 Exclusion #7이 명시한 대로 이 SPEC의 범위 밖이다 |
| C2 | `logistics_status`의 타입은 `string`(리터럴 유니온 아님, `rackNumberApi.ts:65`)이지만 이번 설계는 상태를 비교하지 않으므로(REQ-RACKRECV-004) 실질적 위험은 낮다 |

---

## 7. Definition of Done (요약, 전체는 `acceptance.md`)

- [ ] AC-RACKRECV-001 ~ AC-RACKRECV-006, AC-RACKRECV-012 전부 통과 (`backend/order/tests/test_spec_027.py` `[NEW]`)
- [ ] AC-RACKRECV-007 ~ AC-RACKRECV-011 전부 통과 (`frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx`)
- [ ] `git diff --stat` 로 `SearchTab.tsx`, `purchase_order_views.py:2392-2579`(쓰기 경로), `purchase_order_views.py:3481-3489`(정렬) 공집합 확인
- [ ] `backend/order/migrations/` 신규 파일 0건 (REQ-RACKRECV-018)
- [ ] 기존 `SummaryTab.test.tsx:103`의 `getByText('입고')` 단정이 무수정으로 통과함을 확인(REQ-RACKRECV-012, `plan.md` §검증 항목)
- [ ] `SummaryTab.tsx:17-20`의 기존 `@MX:NOTE` 무삭제 확인
- [ ] mx_plan 실행 결과 반영 (`plan.md` §MX 태그 계획)
