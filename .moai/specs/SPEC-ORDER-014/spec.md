---
id: SPEC-ORDER-014
version: 1.0.2
status: completed
created_at: 2026-08-09
updated: 2026-08-10
completed_at: 2026-08-10
author: ggajo
priority: High
issue_number: 12
labels: [order, logistics, rack-number, summary]
---

# 렉번호(Rack Number) 요약 뷰 — 미출고 LineItem 렉별 교차 주문 집계 조회

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-09 | ggajo | 최초 작성 — 사용자 인터뷰로 확정된 요구사항(고정 미출고 필터, 전체 주문 교차 집계, 렉번호별 그룹핑 + 미지정 버킷, `/rack-number` 페이지 2번째 탭, 읽기 전용 백엔드 GET 엔드포인트)을 EARS 형식으로 formalize. SPEC-ORDER-013(완료, `rack_number` 필드 + 주문 검색 스코프 렉 관리 페이지)을 직접 확장 |
| 1.0.1 | 2026-08-09 | ggajo | plan-auditor 리뷰(iteration 1, PASS, 0.90) 후속 정리 — REQ-RACKSUM-008에서 구현 클래스명(`UnorderedItemsView`) 제거(D1), 설계 결정 B/D의 file:line·ORM 메서드 수준 상세를 WHAT 레벨 서술로 재작성하고 구체적 참조는 plan.md로 위임(D2), REQ/AC-RACKSUM-011a를 Ubiquitous에서 State-Driven으로 재분류해 내재된 조건절 제거(D4), 범위 섹션에서 "TanStack Query" 기술명을 라이브러리 미지정 서술로 교체(D5). D3(`status` enum 표기)는 프로젝트 전역의 기존 관례이므로 본 SPEC 범위에서 변경하지 않음 |
| 1.0.2 | 2026-08-10 | ggajo | Phase 3 (Sync) 완료 — 전체 구현 완료 및 테스트 통과. 백엔드 1개 신규 뷰 + 13개 테스트, 프론트엔드 RackNumberPage 탭 2개 구조(Tab1: SearchTab 기존 동작 무변경 확인, Tab2: SummaryTab 신규) + 26개 테스트. 전체 회귀 테스트 276개 통과(백엔드 149개, 프론트엔드 127개). |

---

## 문제 정의

SPEC-ORDER-013이 도입한 `LineItem.rack_number`는 특정 주문번호를 알고 있을 때만(Tab1: 주문
검색 → 체크박스/인라인 편집) 조회·수정할 수 있다. 그러나 물류 담당자가 실제로 필요로 하는
또 다른 작업은 "지금 한국에서 미국으로 아직 출고되지 않은(=`logistics_status != "shipped"`)
책들이, 렉번호를 기준으로 각각 몇 권씩 어디에 있는가"를 한 화면에서 파악하는 것이다. 이는
특정 주문 하나의 LineItem 목록이 아니라, 전체 주문을 가로지르는(cross-order) 렉번호 기준
집계 조회이며, SPEC-ORDER-013의 Exclusions는 이런 형태의 "역방향(렉번호 → 주문 목록) 조회"를
명시적으로 범위 밖으로 제외했었다. 이 SPEC은 그 제외 조항을 이 특정 읽기 전용 집계
유스케이스에 한해 대체(supersede)하여 해당 기능을 제공한다.

## 솔루션 개요

1. 신규 백엔드 GET 집계 엔드포인트 — 전체 Order를 가로질러 `logistics_status != "shipped"`인
   모든 LineItem을 조회하고, `rack_number` 값으로 그룹화한다. 빈 문자열 `rack_number`는
   버려지지 않고 별도의 "미지정" 그룹으로 묶인다. 그룹별로 총 수량(`LineItem.quantity` 합산)과
   구성 LineItem 목록(최소 주문번호/SKU/도서명/수량/현재 물류상태)을 반환한다.
2. 기존 `/rack-number` 페이지(SPEC-ORDER-013)에 탭 2개 구조를 도입한다 — Tab1 "주문 검색"은
   기존 검색 → 체크박스 일괄 적용 → 인라인 편집 흐름을 정확히 그대로 유지하며(회귀 없음),
   Tab2 "렉번호 요약"이 이 SPEC이 추가하는 신규 읽기 전용 집계 뷰다.
3. Tab2는 순수 조회 전용이다 — 체크박스, 일괄 적용, 인라인 편집 등 어떤 편집 기능도 제공하지
   않는다. `rack_number`를 수정하는 유일한 경로는 여전히 Tab1(SPEC-ORDER-013 흐름)뿐이다.
4. 미출고 필터(`logistics_status != "shipped"`)는 항상 고정 적용되며, 이를 끄거나 완화하는
   파라미터나 UI 토글은 제공하지 않는다.

구체적인 참조 구현(함수명, 파일:라인)은 `plan.md`를 참조 — 본 문서는 관찰 가능한 동작(WHAT)만
규정한다.

## 범위 — 포함

- 신규 백엔드 GET 엔드포인트 1개 — 전체 주문 교차 미출고 LineItem 렉번호별 집계.
- 기존 `RackNumberPage`를 탭 2개 구조로 재구성 — Tab1(기존 동작 무변경) + Tab2(신규 요약).
- 신규 프론트엔드 서비스 함수 + 읽기 전용 데이터 조회 훅(뮤테이션 아님).
- 렉번호 그룹 렌더링(그룹 헤더: 렉번호/미지정 라벨 + 총 수량, 그룹 내 LineItem 목록 표시).
- 미출고 LineItem이 시스템 전체에 0건일 때의 빈 상태 표시.

파일 단위 변경 대상과 [NEW]/[MODIFY]/[MOVE] 마커는 `plan.md`에 정리되어 있다.

## 설계 결정

### 결정 A — 미지정(빈 `rack_number`) 버킷은 드롭하지 않고 항상 별도 그룹으로 포함 (사용자 확정 요구사항 3)

`rack_number`가 아직 기록되지 않은 책도 "찾아야 하는 실물"이라는 점에서 유용한 정보이며,
사용자 인터뷰에서 이를 명시적으로 제외하라는 의사가 확인되지 않았으므로, 빈 문자열
`rack_number`를 가진 LineItem들은 조용히 누락시키지 않고 "미지정" 이라는 별도의 고정 그룹으로
묶어 항상 응답에 포함한다(REQ-RACKSUM-004a). 이는 사용자 인터뷰로 명시적으로 다뤄지지 않은
지점을 투명하게 문서화하는 것으로, 만약 반대 의도(미지정 항목 완전 배제)가 맞다면 후속 SPEC에서
쉽게 뒤집을 수 있다.

### 결정 B — 페이지네이션 미적용, v1 범위에서 명시적으로 보류 (사용자 확정 요구사항 6)

기존 교차 주문 집계 엔드포인트(아래 "관련 SPEC" 절의 SPEC-PURCHASE-ORDER-001 참조)도 전체
주문을 가로지르는 교차 집계 목록을 페이지네이션 없이 반환하는 선례가 있다 —
동일한 선례를 따라 이 엔드포인트도 페이지네이션을 적용하지 않는다. `logistics_status !=
"shipped"`인 LineItem은 시스템 전체 LineItem 중 일부(출고 완료 전 상태)로 자연스럽게 범위가
제한되므로, 무제한 응답의 실질적 위험은 낮다고 판단한다(REQ-RACKSUM-008). 데이터 규모가
실제로 문제가 될 정도로 커지면 후속 SPEC에서 페이지네이션 추가를 재검토한다 — 이번 SPEC에서는
구현하지 않는다. 구체적인 참조 구현 위치(파일:라인)는 `plan.md`를 참조.

### 결정 C — SPEC-ORDER-013 Exclusions의 "역방향 조회 범위 밖" 조항을 이 유스케이스에 한해 대체(supersede)

SPEC-ORDER-013의 Exclusions는 "`rack_number` 기준 전역 검색/필터... 역방향(렉번호 → 주문
목록) 조회는 범위 밖"이라고 명시했다. 이 SPEC은 정확히 그 역방향 조회를, 그러나 "검색/필터"
형태가 아니라 "고정 필터가 항상 적용되는 읽기 전용 집계 뷰" 형태로 제공함으로써 그 배제
조항을 이 특정 유스케이스에 한해 대체한다. SPEC-ORDER-013의 Tab1(주문번호 검색 → 체크박스
일괄 편집 → 인라인 편집) 흐름과 그 배제 규칙(REQ-RACK-002/012/013 등)은 이 SPEC으로 인해
전혀 변경되지 않는다(REQ-RACKSUM-009a).

### 결정 D — 그룹핑은 애플리케이션 레벨에서 수행

`rack_number`별 그룹을 구성할 때, 그룹별 `line_items` 상세 목록(주문번호/SKU/도서명/수량/
`logistics_status`)까지 함께 가져와야 하므로, 데이터베이스 레벨 집계만으로는 이를 한 번에
얻을 수 없다 — LineItem 목록을 조회한 뒤 애플리케이션 레벨에서 `rack_number` 기준으로
그룹핑한다. 총 수량은 그룹핑 도중 각 LineItem의 수량을 누적하며, null 수량은 0으로
취급한다(REQ-RACKSUM-005) — 이는 기존 교차 주문 집계 엔드포인트가 사용하는 동일한 null
처리 관례를 재사용한 것이다. 구체적인 쿼리 구성과 null 처리 코드는 `plan.md`를 참조.

### 결정 E — 미출고 필터는 하드코딩, 끄는 파라미터 제공하지 않음 (사용자 확정 요구사항 1)

"한국에서 미국으로 미출고"는 `logistics_status != "shipped"`로 고정되며, 요청 파라미터로
이를 끄거나 완화할 수 있는 방법을 제공하지 않는다. 요청에 그런 파라미터가 포함되더라도
무시한다(REQ-RACKSUM-002/002a).

### 결정 F — Tab2는 탭 활성화 시 자동 조회, 별도 검색 액션 불필요

Tab1과 달리 Tab2는 주문번호 검색이 필요 없는 전역 집계이므로, 탭이 처음 활성화될 때 자동으로
데이터를 가져온다. 사용자가 별도로 "조회" 버튼을 누를 필요가 없다(REQ-RACKSUM-010).

## 요구사항 (EARS)

**번호 규칙 참고**: 기본 번호 계열(REQ-RACKSUM-001~015)에는 결번·중복이 없다. 알파벳 접미사
(`002a`, `004a` 등)는 SPEC-ORDER-011/012/013에서 이미 확립된 프로젝트 관례를 따라, 기본
항목에서 파생된 서로 다른 트리거 또는 서로 다른 성격의 규범 진술(정상 경로 vs 예외/검증
경로)을 분리 표현하기 위한 것이다.

### 데이터 필터링

**REQ-RACKSUM-001** (Ubiquitous): The system shall define a LineItem as "not yet shipped
from Korea to the US" when that LineItem's `logistics_status` value is not equal to
`"shipped"` — that is, when its value is one of `not_shipped`, `shipment_confirmed`,
`received`, or `outbound_scheduled`.

**REQ-RACKSUM-002** (Ubiquitous): The system shall apply the not-shipped filter defined in
REQ-RACKSUM-001 to every rack-number summary computation, with no request parameter, toggle,
or configuration option capable of disabling it.

**REQ-RACKSUM-002a** (Unwanted): If a request to the rack-number summary endpoint carries any
parameter intended to disable, widen, or bypass the not-shipped filter, then the system shall
ignore that parameter, and the system shall still apply the filter defined in REQ-RACKSUM-001.

### 백엔드 API — 집계 엔드포인트

**REQ-RACKSUM-003** (Event-Driven): When a GET request is made to the rack-number summary
endpoint, the system shall evaluate every LineItem across every Order in the system against
the not-shipped filter (REQ-RACKSUM-001), without restricting the query to any single Order.

**REQ-RACKSUM-004** (Event-Driven): When computing the rack-number summary response, the
system shall group every LineItem that passes the not-shipped filter into one group per
distinct non-empty `rack_number` value.

**REQ-RACKSUM-004a** (State-Driven): While a LineItem that passes the not-shipped filter has
an empty-string `rack_number` value, the system shall place that LineItem into a single
distinct unassigned group, and the system shall NOT omit that LineItem from the response.

**REQ-RACKSUM-005** (Ubiquitous): The system shall compute, for every group produced by
REQ-RACKSUM-004/004a, a `total_quantity` value equal to the sum of each member LineItem's
`quantity` field, treating a null `quantity` as zero.

**REQ-RACKSUM-006** (Ubiquitous): The system shall include, for every group produced by
REQ-RACKSUM-004/004a, the full list of member LineItems, and the system shall report for each
member LineItem at minimum its parent Order's `order_number`, its `sku`, its `title`, its
`quantity`, and its current `logistics_status`.

**REQ-RACKSUM-007** (Unwanted): If a LineItem's `logistics_status` equals `"shipped"`, then
the system shall NOT include that LineItem in any group of the rack-number summary response,
regardless of whether other LineItems belonging to the same Order remain unshipped.

**REQ-RACKSUM-008** (Ubiquitous): The system shall return the rack-number summary response as
a single, non-paginated payload containing every group.

### 프론트엔드 — 탭 구조 및 기존 동작 보존

**REQ-RACKSUM-009** (Ubiquitous): The system shall present the rack-number management page
(`/rack-number`) with exactly two tabs: "주문 검색" and "렉번호 요약".

**REQ-RACKSUM-009a** (Ubiquitous): The system shall preserve, under the "주문 검색" tab, the
order-number search, checkbox multi-select, bulk-apply, and inline-edit behavior exactly as
specified by SPEC-ORDER-013 REQ-RACK-009 through REQ-RACK-011, without any change to that
behavior.

**REQ-RACKSUM-009b** (Ubiquitous): The system shall render "주문 검색" as the default active
tab when the rack-number management page first loads, before any tab is clicked.

**REQ-RACKSUM-010** (Event-Driven): When the user activates the "렉번호 요약" tab, the system
shall request the rack-number summary from the backend, and the system shall render the
returned groups without requiring any additional user input.

### 프론트엔드 — 요약 표시

**REQ-RACKSUM-011** (Ubiquitous): The system shall render, for every group in the rack-number
summary, a group heading showing that group's `rack_number` value (or the unassigned-group
label when `rack_number` is empty) and that group's `total_quantity`.

**REQ-RACKSUM-011a** (State-Driven): While the unassigned group contains one or more
LineItems, the system shall render that group using a label distinct from every named
`rack_number` group.

**REQ-RACKSUM-012** (Ubiquitous): The system shall render, within each group, one row per
member LineItem showing at minimum that LineItem's parent Order's `order_number`, `sku`,
`title`, `quantity`, and current `logistics_status`.

**REQ-RACKSUM-013** (State-Driven): While the rack-number summary response contains zero
groups, the system shall display an empty-state message on the "렉번호 요약" tab instead of
rendering an empty table or an empty group list.

### 제외 범위 강제 (읽기 전용)

**REQ-RACKSUM-014** (Unwanted): If the "렉번호 요약" tab is rendered, then the system shall
NOT render any checkbox, bulk-apply control, or inline-edit input for `rack_number` on that
tab.

**REQ-RACKSUM-015** (Unwanted): If the user interacts with any element rendered on the "렉번호
요약" tab, then the system shall NOT submit any PATCH or upload request capable of modifying a
LineItem's `rack_number` from that tab.

---

## ACCEPTANCE CRITERIA

EARS 형식의 인수 기준. 각 항목은 대응하는 REQ-RACKSUM-XXX 하나 이상에 1:1 이상으로 추적된다.
Given/When/Then 형태의 실행 가능한 테스트 시나리오는 `acceptance.md`에 별도로 존재하며, 각
시나리오는 아래 AC-RACKSUM-XXX ID를 인용해 상호 추적된다.

**AC-RACKSUM-001** (Ubiquitous) — Traces: REQ-RACKSUM-001. The system shall classify a
LineItem as matching the not-shipped filter when and only when its `logistics_status` is one
of `not_shipped`, `shipment_confirmed`, `received`, or `outbound_scheduled`.

**AC-RACKSUM-002** (Ubiquitous) — Traces: REQ-RACKSUM-002. The system shall apply the
not-shipped filter to every rack-number summary request without exposing any parameter capable
of disabling it.

**AC-RACKSUM-002a** (Unwanted) — Traces: REQ-RACKSUM-002a. If a GET request to the rack-number
summary endpoint includes an unrecognized query parameter (e.g. an attempt to disable the
filter), then the system shall ignore that parameter, and the system shall still return only
not-shipped LineItems.

**AC-RACKSUM-003** (Event-Driven) — Traces: REQ-RACKSUM-003. When the rack-number summary
endpoint is called, the system shall include matching LineItems from every Order that has at
least one not-shipped LineItem, not just a single Order.

**AC-RACKSUM-004** (Event-Driven) — Traces: REQ-RACKSUM-004. When two or more not-shipped
LineItems share the same non-empty `rack_number` value, the system shall place them in the
same group in the response.

**AC-RACKSUM-004a** (State-Driven) — Traces: REQ-RACKSUM-004a. While one or more not-shipped
LineItems have an empty-string `rack_number`, the system shall group all of them together into
a single unassigned group rather than omitting them.

**AC-RACKSUM-004b** (Event-Driven) — Traces: REQ-RACKSUM-004, REQ-RACKSUM-006. When a group's
member LineItems belong to two or more different Orders (i.e. the same `rack_number` value was
recorded for LineItems in different Orders), the system shall include every one of those
LineItems in that single group, each carrying its own parent Order's `order_number`.

**AC-RACKSUM-005** (Ubiquitous) — Traces: REQ-RACKSUM-005. The system shall report a group's
`total_quantity` as the arithmetic sum of its member LineItems' `quantity` values, counting any
null `quantity` as zero.

**AC-RACKSUM-006** (Ubiquitous) — Traces: REQ-RACKSUM-006. The system shall include
`order_number`, `sku`, `title`, `quantity`, and `logistics_status` for every LineItem listed
within every group.

**AC-RACKSUM-007** (Unwanted) — Traces: REQ-RACKSUM-007. If every LineItem belonging to a
given Order has `logistics_status` equal to `"shipped"`, then the system shall NOT include any
LineItem from that Order in any group of the response.

**AC-RACKSUM-007a** (Unwanted) — Traces: REQ-RACKSUM-007. If an Order has a mix of shipped and
not-shipped LineItems, then the system shall include only that Order's not-shipped LineItems in
the response, and the system shall NOT include that Order's shipped LineItems in the response.

**AC-RACKSUM-008** (Ubiquitous) — Traces: REQ-RACKSUM-008. The system shall return the
complete set of groups in a single response payload with no `page`, `next`, or `previous`
pagination fields.

**AC-RACKSUM-009** (Ubiquitous) — Traces: REQ-RACKSUM-009. The system shall render exactly two
tab controls labeled "주문 검색" and "렉번호 요약" on the `/rack-number` page.

**AC-RACKSUM-009a** (Ubiquitous) — Traces: REQ-RACKSUM-009a. The system shall render, when the
"주문 검색" tab is active, the same search input, checkbox column, bulk-apply control, and
inline-edit inputs that existed before this SPEC, with identical behavior on order-number
search, bulk PATCH, and single-item PATCH.

**AC-RACKSUM-009b** (Ubiquitous) — Traces: REQ-RACKSUM-009b. The system shall show the "주문
검색" tab's content immediately when the rack-number management page first loads, with no tab
click required to see it.

**AC-RACKSUM-010** (Event-Driven) — Traces: REQ-RACKSUM-010. When the user clicks the "렉번호
요약" tab, the system shall issue a request for the rack-number summary, and the system shall
render the resulting groups once the response arrives, without any search input or button
click from the user.

**AC-RACKSUM-011** (Ubiquitous) — Traces: REQ-RACKSUM-011. The system shall display each
group's `rack_number` (or the unassigned label) and `total_quantity` value adjacent to each
other in that group's heading.

**AC-RACKSUM-011a** (State-Driven) — Traces: REQ-RACKSUM-011a. While the response contains at
least one unassigned LineItem, the system shall render that group labeled "미지정".

**AC-RACKSUM-012** (Ubiquitous) — Traces: REQ-RACKSUM-012. The system shall display, for each
LineItem row within a group, its order number, SKU, title, quantity, and current
logistics-status label.

**AC-RACKSUM-013** (State-Driven) — Traces: REQ-RACKSUM-013. While the rack-number summary
response's group list is empty (zero not-shipped LineItems system-wide), the system shall
display an empty-state message on the "렉번호 요약" tab, and the system shall NOT render an
empty table structure.

**AC-RACKSUM-014** (Unwanted) — Traces: REQ-RACKSUM-014. If the "렉번호 요약" tab is
displayed, then the system shall NOT render any checkbox element, any bulk-apply input or
button, or any editable `rack_number` text input on that tab.

**AC-RACKSUM-015** (Unwanted) — Traces: REQ-RACKSUM-015. If a user clicks or interacts with any
element rendered on the "렉번호 요약" tab, then the system shall NOT trigger any PATCH or
upload request that modifies `rack_number`.

---

## Exclusions (What NOT to Build)

- Tab2("렉번호 요약")에 체크박스, 일괄 적용, 인라인 편집 등 어떤 편집 기능도 추가하지
  않는다 — 명시적으로 제외(REQ-RACKSUM-014/015). `rack_number` 수정은 여전히 Tab1(SPEC-ORDER-013
  흐름)에서만 가능하다.
- 미출고 필터(`logistics_status != "shipped"`)를 끄거나 완화하는 토글/파라미터/설정 —
  명시적으로 제외(REQ-RACKSUM-002/002a). 이 SPEC의 요약 뷰는 항상 고정된 단일 필터로만
  동작한다.
- 페이지네이션 — v1 범위에서 명시적으로 보류한다(REQ-RACKSUM-008, 결정 B). 데이터 규모가
  실제로 문제될 정도로 커지면 후속 SPEC에서 재검토한다.
- `rack_number` 기준 추가 검색/정렬/필터 UI(예: 특정 렉만 필터링하는 검색창, 정렬 옵션) —
  이 SPEC은 전체 목록을 렉번호로 그룹핑해 보여주는 것까지만 다루며, 사용자 인터뷰에서 요청되지
  않은 추가 필터/정렬 UI는 범위 밖이다.
- 요약 데이터의 Excel/CSV 내보내기(export) 기능 — 이 SPEC 범위 밖이다.
- SPEC-ORDER-013 Tab1(주문 검색 → 체크박스 일괄 편집 → 인라인 편집) 흐름 자체의 변경 —
  이 SPEC은 Tab1의 동작을 전혀 수정하지 않는다(REQ-RACKSUM-009a).

## 관련 SPEC

- SPEC-ORDER-013: `LineItem.rack_number` 필드 + 주문 검색 스코프 렉 관리 페이지(Tab1의
  직접적 기반). 이 SPEC은 SPEC-ORDER-013을 확장하며, 그 Tab1 흐름과 데이터 모델(`rack_number`
  필드 자체)을 전혀 변경하지 않는다. 다만 SPEC-ORDER-013 Exclusions의 "역방향(렉번호 → 주문
  목록) 조회는 범위 밖" 조항은 이 SPEC의 읽기 전용 집계 유스케이스에 한해 대체된다(결정 C).
- SPEC-ORDER-011: `LineItem.logistics_status` 도입 — 이 SPEC의 고정 필터(`!= "shipped"`)가
  참조하는 필드의 근원 SPEC.
- SPEC-ORDER-012: `Order.ready_to_ship` 집계 — Order 레벨 집계 패턴의 선례이나, 이 SPEC의
  집계는 Order가 아닌 `rack_number` 기준이며 Order 모델에 필드를 추가하지 않는다는 점에서
  성격이 다르다.
- SPEC-PURCHASE-ORDER-001 `UnorderedItemsView`: 이 SPEC이 페이지네이션 미적용 결정(결정 B)과
  애플리케이션 레벨 그룹핑(결정 D)의 직접적 선례로 참조하는 기존 교차 주문 집계 엔드포인트.

---

## Implementation Notes

### 백엔드 구현 (commit fb6b5d8)

- **신규 뷰 1개**: `GET /api/purchase-orders/line-items/rack-number-summary/` — 미출고 LineItem 렉번호별 집계 조회
  - 응답 구조: `groups` 배열 (각 그룹: `rack_number`, `is_unassigned`, `total_quantity`, `line_items` 배열)
  - 미지정 그룹(`rack_number=""`)은 항상 배열 마지막에 배치
  - `logistics_status != "shipped"` 고정 필터 적용, 파라미터로 불가 비활성화
- **13개 테스트**: 필터링(3개), 그룹핑(3개), null 처리(2개), 미지정 버킷(2개), 엣지 케이스(3개)
- **회귀 테스트**: 기존 149개 백엔드 테스트 모두 통과

### 프론트엔드 구현 (commit fb6b5d8)

- **RackNumberPage 구조 변경**: 탭 2개 쉘 도입
  - Tab1 "주문 검색": SearchTab — SPEC-ORDER-013 기존 동작 100% 유지 (체크박스, 일괄 적용, 인라인 편집)
  - Tab2 "렉번호 요약": SummaryTab — 신규 읽기 전용 집계 뷰 (그룹 렌더링, 렉번호/미지정 라벨, 총 수량, 빈 상태 메시지)
- **SearchTab 검증**: evaluator-active 의존도 분석 결과 SPEC-ORDER-013 코드와 바이트 정확 동일 (순수 추출, 회귀 없음)
- **26개 테스트**: 탭 구조(2개), 렉번호 렌더링(4개), 미지정 라벨(2개), 그룹 내 LineItem 표시(4개), 빈 상태(2개), 자동 조회(2개), UI 상호작용 제약(8개)
- **회귀 테스트**: 기존 127개 프론트엔드 테스트 모두 통과

### 응답 계약

- **엔드포인트 응답**: `GET /api/purchase-orders/line-items/rack-number-summary/`
  ```json
  {
    "groups": [
      {
        "rack_number": "A1",
        "is_unassigned": false,
        "total_quantity": 42,
        "line_items": [
          {
            "order_number": "ORD-001",
            "sku": "ISBN123",
            "title": "도서명",
            "quantity": 10,
            "logistics_status": "not_shipped"
          }
        ]
      },
      {
        "rack_number": "",
        "is_unassigned": true,
        "total_quantity": 5,
        "line_items": [...]
      }
    ]
  }
  ```

### 비차단 발견 사항

- **사전 존재 TypeScript 오류**: `npm run build` (`tsc -b`)에서 다음 파일의 unrelated 오류 발견
  - `BookDetailPage.tsx`, `DashboardPage.test.tsx`, `ConfirmOrderTab.tsx`, `purchaseOrderApi.ts`
  - 이 SPEC 이전부터 존재 (git stash 비교 확인됨)
  - 별도 정리 SPEC에서 대응 필요, 본 SPEC 범위 외
