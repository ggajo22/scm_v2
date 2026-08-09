---
id: SPEC-ORDER-013
version: 1.1.1
status: draft
created_at: 2026-08-09
updated: 2026-08-09
author: ggajo
priority: High
issue_number: 11
labels: [order, logistics, rack-number]
---

# 렉번호(Rack Number) 관리 — LineItem 도서 보관 위치 추적

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-09 | ggajo | 최초 작성 — 사용자 인터뷰로 확정된 요구사항(데이터 모델, 신규 독립 페이지, 검색→체크박스 일괄 적용, 개별 인라인 편집, Excel 3컬럼 업로드, 3개 백엔드 엔드포인트, OrderDetailPage 노출 제외)을 EARS 형식으로 formalize |
| 1.1.0 | 2026-08-09 | ggajo | Phase 2.3 plan-auditor 리뷰(iteration 2, FAIL — MP-2 잔존) 반영, iteration 3 제출본. (D9, critical/MP-2) AC-RACK-003/003a/003b의 후행 "shall" 절 주어를 "the response"/"no LineItem's rack_number"/"the target LineItem's rack_number"에서 모두 "the system"으로 통일. REQ-RACK-002에서도 동일 결함 유형("rack_number shall be set only by...")을 자체 재검토로 추가 발견해 "the system shall set..."으로 정정. (D8) AC-RACK-006을 006(양성 매칭)/006c(음성 범위 제한, 신설)로, AC-RACK-010을 010(렌더링)/010b(전체선택 토글, 신설)/010c(재검색 시 선택 초기화, 신설)로 분리해 AC 1개당 단일 테스트 가능 동작 원칙 준수. (D10) REQ-RACK-008/AC-RACK-008에서 구현 세부사항 "lazy-loaded route"/"code-split" 문구 제거, 관찰 가능한 라우팅/메뉴 동작만 기술 |
| 1.1.1 | 2026-08-09 | ggajo | Phase 2.3 iteration 3 리뷰(FAIL, D11 critical/MP-2 단독 잔존) 이후 사용자 승인 하에 경량 수정 적용 — 3회 감사 반복 소진, 감사관 권고에 따라 전체 4차 감사 사이클 생략. AC-RACK-008의 "shall" 절 주어를 "The rack-number management page"에서 "The system"으로 정정(EARS 주어 일관성 원칙 준수). |

---

## 문제 정의

물류 담당자가 특정 주문의 특정 품목(LineItem)이 현재 어느 렉(선반/구역)에 보관되어 있는지 빠르게
조회·기록할 방법이 없다. 기존 `LineItem.location`(SPEC-ORDER-011 이전부터 존재, 미국 창고
구역 등 광의의 위치 코드로 추정)과는 별개로, "지금 이 책이 정확히 어느 렉에 있는가"를 나타내는
운영용 짧은 코드를 개별/일괄/엑셀 업로드 세 가지 경로로 기록할 수 있어야 한다. 이 값은 물류
파이프라인 상태(`logistics_status`, SPEC-ORDER-011)나 발주 상태(`purchase_status`)와 달리
Order 단위 집계나 자동 계산이 필요 없는 순수 수동/업로드 기입 값이다.

## 솔루션 개요

1. `LineItem`에 신규 필드 `rack_number` 추가 — 기존 `location` 필드와 동일한 패턴
   (`CharField(max_length=10, blank=True, default="")`), 계산/집계 없음, Order 레벨 롤업 없음.
2. 신규 독립 페이지(기존 발주 관리 페이지의 탭이 아님) — 주문번호로 검색 → 해당 주문의
   LineItem 목록을 테이블로 표시 → 체크박스로 다중 선택 후 렉번호 값을 일괄 적용, 동시에
   테이블 내에서 개별 LineItem의 렉번호를 인라인으로 직접 수정 가능.
3. 백엔드 API 3종 — 단건 PATCH, 명시적 id 목록 기반 일괄 PATCH, 3컬럼(주문번호/SKU/렉번호)
   Excel 업로드. 검색 자체는 기존 `GET /api/orders/?search=`(주문번호 정확 매칭 지원,
   SPEC-ORDER-003/007 계열 기존 구현)와 기존 `GET /api/orders/{id}/`(`OrderDetailView`)를
   재사용하며, 검색 전용 신규 엔드포인트는 만들지 않는다.
4. `LineItemDetailSerializer`에 `rack_number` 읽기 노출을 추가하되, 기존 Order 상세 화면
   (`OrderDetailPage`)의 UI에는 렉번호를 절대 렌더링/편집하지 않는다 — API 응답에는 필드가
   포함되지만(다른 신규 페이지가 동일 엔드포인트를 재사용하므로) 화면 소비 여부는 페이지별로
   분리된다.

구체적인 참조 구현(함수명, 파일:라인, 마이그레이션 파일 구성)은 `plan.md`를 참조 — 본 문서는
관찰 가능한 동작(WHAT)만 규정한다.

## 범위 — 포함

- `LineItem` 모델에 신규 컬럼 추가(단일 `AddField` 마이그레이션, 백필 없음 — 신규 컬럼은
  전 행 빈 문자열로 시작).
- 단건 PATCH / 일괄 PATCH(명시적 id 목록) / Excel 업로드 백엔드 엔드포인트 3종.
- `LineItemDetailSerializer`에 `rack_number` 읽기 필드 추가.
- 신규 독립 라우트 + 사이드바 메뉴 항목 1개.
- 신규 페이지: 주문번호 검색, LineItem 테이블(체크박스 다중 선택 + 렉번호 인라인 개별 편집),
  일괄 적용 컨트롤, Excel 업로드 UI.
- 신규 프론트엔드 서비스/타입 정의 + TanStack Query 훅.

파일 단위 변경 대상과 [NEW]/[MODIFY] 마커는 `plan.md`에 정리되어 있다.

## 설계 결정

### 결정 A — 데이터 모델: `location` 필드 패턴 채택, Order 집계 없음 (사용자 승인)

`LineItem.rack_number`는 `location`(171행)과 동일하게 `CharField(max_length=10, blank=True,
default="")`로 선언한다. `status`/`ready_to_ship`(SPEC-ORDER-011/012)처럼 계산된 집계
필드가 아니라, 수동 또는 업로드로만 값이 채워지는 단순 코드 필드이며, `Order` 레벨의 롤업/집계
필드는 만들지 않는다(사용자 확정 요구사항 1).

### 결정 B — 마이그레이션: `AddField` 단독, 백필 없음 (사용자 승인)

신규 컬럼이므로 기존 행은 모두 `default=""`로 채워지며 별도 데이터 백필 마이그레이션이
필요 없다. `0010_lineitem_add_location.py`와 동일하게 단일 `AddField` 마이그레이션 하나로
충분하다.

### 결정 C — 검색 흐름: 기존 주문 검색/상세 엔드포인트 재사용, 신규 검색 API 없음

`GET /api/orders/?search=<주문번호>`(`OrderListView`, `views.py:88-151`)는 이미 숫자
검색어를 `order_number` 정확 일치로 처리하는 로직을 포함한다. 프론트엔드는 이 엔드포인트로
주문을 찾은 뒤, 정확히 `order_number`가 일치하는 결과를 선택하고(이름 부분 일치로 인한
오탐 방지), 그 주문의 `id`로 `GET /api/orders/{id}/`(`OrderDetailView`, 이미
`line_items`를 `LineItemDetailSerializer`로 직렬화)를 호출해 LineItem 전체 목록을
가져온다. 렉번호 전용 검색 엔드포인트는 신설하지 않는다(사용자 확정 요구사항 6은 "3개
엔드포인트"만 명시).

### 결정 D — Excel 매칭: 주문번호+SKU 조합, 이름 기반 대소문자 무시 부분일치 헤더 탐색

3개 컬럼(주문번호/SKU/렉번호) 모두 헤더 이름의 대소문자 무시 부분일치로 탐색한다
(`excel_utils._parse_sku_only_xlsx`의 `"sku" in h or "isbn" in h` 스타일을 3개 컬럼으로
확장). 동일 (주문번호, SKU) 조합이 여러 행에 나타나면 마지막 행이 우선한다
(`UploadVendorShipmentView`의 `sku_map[row["sku"]] = row` 마지막-행-우선 관례,
REQ-LOGI-003a 선례 재사용).

### 결정 E — Excel 매칭 시 (주문번호, SKU) 조합이 LineItem 2개 이상과 매칭되는 경우 전부 적용

`(order, shopify_line_item_id, sku)`가 unique_together(SPEC-SHOPIFY-SKU-SET-002)이므로
이론상 같은 주문 안에 같은 SKU를 가진 LineItem이 2개 이상 존재할 수 있다(같은 책을 서로
다른 Shopify line item으로 중복 주문한 경우, 번들 세트 확장 등). 이 경우 어느 특정
LineItem을 지목할 추가 정보가 엑셀에 없으므로, 매칭되는 LineItem 전부에 동일한 렉번호 값을
적용한다(부분 매칭이 아닌 전체 매칭 처리) — 물리적으로 같은 책은 같은 렉에 있다고 가정하는
것이 합리적이라는 판단에 따른 기본 동작이며, 사용자 인터뷰에서 명시적으로 다뤄지지 않은
엣지 케이스이므로 여기서 투명하게 문서화한다.

### 결정 F — 프론트엔드 상태 스코프: 로컬 컴포넌트 상태, 전역 스토어 미사용 (사용자 승인)

체크박스 다중 선택 상태는 `UnorderedItemsTab.tsx`의 UX 패턴(체크박스 컬럼 + 전체선택 +
일괄값 선택 + 적용 버튼)을 재사용하되, 전역 `usePurchaseOrderStore`(SKU 배열 기반, 발주
관리 페이지 전역 스코프)는 사용하지 않는다. 이 페이지는 항상 "현재 검색된 단일 주문"
범위로만 동작하므로 로컬 `useState<number[]>`(LineItem id 배열)로 충분하며, 페이지를
벗어나면 선택 상태가 자동으로 소멸하는 것이 올바른 동작이다(사용자 확정 요구사항 3).

## 요구사항 (EARS)

**번호 규칙 참고**: 기본 번호 계열(REQ-RACK-001~013)에는 결번·중복이 없다. 알파벳 접미사
(`003a`, `005a` 등)는 SPEC-ORDER-011/012에서 이미 확립된 프로젝트 관례를 따라, 기본
항목에서 파생된 서로 다른 트리거 또는 서로 다른 성격의 규범 진술(정상 경로 vs 예외/검증
경로)을 분리 표현하기 위한 것이다.

### 데이터 모델

**REQ-RACK-001** (Ubiquitous): The system shall provide `LineItem.rack_number` as a short text
code field (max length 10 characters, optional, default empty string), matching the existing
`LineItem.location` field's pattern.

**REQ-RACK-002** (Unwanted): If any process attempts to compute, derive, or expose an
Order-level aggregate or rollup value for `rack_number`, then the system shall NOT provide
that aggregate or rollup value, and the system shall set `rack_number` only via direct manual
edit, bulk apply, or Excel upload, never via automatic calculation.

### 백엔드 API — 단건 PATCH

**REQ-RACK-003** (Event-Driven): When a PATCH request targeting an existing LineItem's
rack-number endpoint carries a `rack_number` value of at most 10 characters, the system shall
update that LineItem's `rack_number` to the submitted value and persist it.

**REQ-RACK-003a** (Unwanted): If a PATCH request to the single rack-number endpoint targets a
LineItem id that does not exist, then the system shall respond with HTTP 404 and shall NOT
modify any LineItem.

**REQ-RACK-003b** (Unwanted): If a PATCH request to the single rack-number endpoint carries a
`rack_number` value longer than 10 characters, then the system shall reject the request with
HTTP 400 and shall leave the target LineItem's `rack_number` unchanged.

### 백엔드 API — 일괄 PATCH

**REQ-RACK-004** (Event-Driven): When a PATCH request to the bulk rack-number endpoint
supplies a non-empty list of LineItem ids and a `rack_number` value of at most 10 characters,
the system shall update `rack_number` on every LineItem matching a supplied id, and shall
report which of the supplied ids did not match any existing LineItem.

**REQ-RACK-004a** (Unwanted): If a PATCH request to the bulk rack-number endpoint supplies an
empty id list, then the system shall reject the request with HTTP 400 and shall NOT modify any
LineItem.

### 백엔드 API — Excel 업로드

**REQ-RACK-005** (Event-Driven): When an `.xlsx` file is uploaded to the rack-number upload
endpoint, the system shall locate its three required columns — order number, SKU, and rack
number — by scanning the header row for a case-insensitive substring match against each
column's expected name variants, independent of the columns' left-to-right position in the
sheet.

**REQ-RACK-005a** (Unwanted): If the uploaded file's header row does not contain a column
matching all three required column types, then the system shall reject the upload with HTTP
422 and shall NOT modify any LineItem.

**REQ-RACK-006** (Event-Driven): When a parsed row's order-number value matches an existing
Order's `order_number` and that Order has one or more LineItems whose `sku` equals the row's
SKU value, the system shall set `rack_number` to the row's rack-number value on every such
matching LineItem.

**REQ-RACK-006a** (State-Driven): While a parsed row's order-number value does not match any
existing Order's `order_number`, or the matched Order has no LineItem whose `sku` equals the
row's SKU value, the system shall count that row as skipped and shall NOT modify any LineItem
for that row.

**REQ-RACK-006b** (Event-Driven): When the uploaded file contains two or more rows sharing the
same (order number, SKU) pair, the system shall apply only the last such row's rack-number
value to the matching LineItem(s), consistent with the last-row-wins rule already used by the
existing logistics-status upload endpoints.

**REQ-RACK-007** (Ubiquitous): The system shall respond to a completed rack-number upload with
`matched_count` and `skipped_count`, each counted per distinct (order number, SKU) row after
REQ-RACK-006b's deduplication — not per LineItem row affected.

### 프론트엔드 — 신규 페이지 및 내비게이션

**REQ-RACK-008** (Ubiquitous): The system shall provide a rack-number management page as an
independently routed page (not a tab within the existing purchase-order management page), with
a corresponding sidebar navigation entry.

### 프론트엔드 — 주문번호 검색

**REQ-RACK-009** (Event-Driven): When the user submits an order-number search on the
rack-number management page, the system shall locate the Order whose `order_number` exactly
matches the submitted value and shall display that Order's LineItems in a table.

**REQ-RACK-009a** (Unwanted): If no Order's `order_number` exactly matches the submitted
search value, then the system shall display a not-found state and shall NOT render any
LineItem table.

### 프론트엔드 — 체크박스 다중 선택 및 일괄 적용

**REQ-RACK-010** (State-Driven): While the LineItem table for a searched Order is displayed,
the system shall render a checkbox for each row and a "select all" checkbox in the table
header, with selection state scoped to that page's local component state (not any
cross-page/global store).

**REQ-RACK-010a** (Event-Driven): When the user enters a rack-number value and applies it to
the currently checked rows, the system shall submit a single bulk-PATCH request containing all
checked LineItem ids and the entered value, and shall clear the row selection after a
successful response.

### 프론트엔드 — 개별 인라인 편집

**REQ-RACK-011** (Event-Driven): When the user edits a single LineItem's `rack_number` value
directly within the table and confirms the change, the system shall submit a single-item
PATCH request for that LineItem and shall reflect the updated value in the table without
requiring a full page reload.

### 제외 범위 강제

**REQ-RACK-012** (Unwanted): If the existing Order detail screen (`OrderDetailPage`) is
rendered, then the system shall NOT render or allow editing of `rack_number` anywhere on that
screen.

**REQ-RACK-013** (Unwanted): If a `rack_number` value is submitted via PATCH or Excel upload,
then the system shall NOT apply any rack-location capacity validation or any uniqueness
constraint to that value.

---

## ACCEPTANCE CRITERIA

EARS 형식의 인수 기준. 각 항목은 대응하는 REQ-RACK-XXX 하나 이상에 1:1 이상으로 추적된다.
Given/When/Then 형태의 실행 가능한 테스트 시나리오는 `acceptance.md`에 별도로 존재하며, 각
시나리오는 아래 AC-RACK-XXX ID를 인용해 상호 추적된다.

**AC-RACK-001** (Ubiquitous) — Traces: REQ-RACK-001. The system shall persist `rack_number` as
a string field on `LineItem` with max length 10, default empty string, independent of
`location`, `logistics_status`, and `purchase_status`.

**AC-RACK-002** (Unwanted) — Traces: REQ-RACK-002. If any code path attempts to add a
`rack_number`-derived field, column, or computed property on `Order`, then the system shall
NOT expose that field, column, or property on the `Order` model or its serializers.

**AC-RACK-003** (Event-Driven) — Traces: REQ-RACK-003. When a valid single-item PATCH request
is sent for an existing LineItem with a rack_number value of 10 characters or fewer, the
system shall update and persist that LineItem's `rack_number`, and the system shall return the
new value in the response.

**AC-RACK-003a** (Unwanted) — Traces: REQ-RACK-003a. If the single-item PATCH endpoint is
called with a non-existent LineItem id, then the system shall respond HTTP 404 and the system
shall NOT change any LineItem's `rack_number`.

**AC-RACK-003b** (Unwanted) — Traces: REQ-RACK-003b. If the single-item PATCH endpoint is
called with a rack_number value longer than 10 characters, then the system shall respond HTTP
400 and the system shall leave the target LineItem's `rack_number` unchanged.

**AC-RACK-004** (Event-Driven) — Traces: REQ-RACK-004. When the bulk PATCH endpoint is called
with a non-empty list of LineItem ids (a mix of existing and non-existent ids) and a valid
rack_number value, the system shall update `rack_number` on every existing LineItem in the
list and shall return the subset of ids that did not match any LineItem.

**AC-RACK-004a** (Unwanted) — Traces: REQ-RACK-004a. If the bulk PATCH endpoint is called with
an empty id list, then the system shall respond HTTP 400 and shall NOT modify any LineItem.

**AC-RACK-005** (Event-Driven) — Traces: REQ-RACK-005. When an uploaded `.xlsx` file's header
row contains the three required columns in any left-to-right order and in any letter case
(e.g. "SKU", "sku", "Lineitem SKU"), the system shall correctly locate all three columns and
proceed to parse data rows.

**AC-RACK-005a** (Unwanted) — Traces: REQ-RACK-005a. If an uploaded file's header row is
missing any one of the three required columns, then the system shall respond HTTP 422 with an
error message and shall NOT modify any LineItem.

**AC-RACK-006** (Event-Driven) — Traces: REQ-RACK-006. When a parsed row's order number and
SKU together match exactly one Order and one or more LineItems within that Order, the system
shall set `rack_number` to the row's value on every matching LineItem within that Order.

**AC-RACK-006a** (State-Driven) — Traces: REQ-RACK-006a. While a parsed row's order number
does not match any existing Order, or matches an Order that has no LineItem with the row's
SKU, the system shall increment `skipped_count` for that row and shall NOT modify any
LineItem.

**AC-RACK-006b** (Event-Driven) — Traces: REQ-RACK-006b. When an uploaded file contains two
rows with identical (order number, SKU) but different rack-number values, the system shall
apply only the value from the row that appears later in the file.

**AC-RACK-006c** (Unwanted) — Traces: REQ-RACK-006. If a LineItem belongs to an Order other
than the one matched by a parsed row's order number, then the system shall NOT modify that
LineItem's `rack_number` when processing that row, even when the LineItem's `sku` equals the
row's SKU value.

**AC-RACK-007** (Ubiquitous) — Traces: REQ-RACK-007. The system shall ensure
`matched_count + skipped_count` equals the number of distinct (order number, SKU) row-keys
present in the uploaded file after deduplication, for every upload response.

**AC-RACK-008** (Ubiquitous) — Traces: REQ-RACK-008. The system shall make the rack-number
management page reachable via its own route distinct from `/purchase-orders` and its tabs, and
shall provide a corresponding entry in the sidebar navigation list.

**AC-RACK-009** (Event-Driven) — Traces: REQ-RACK-009. When a user searches by an order number
that exactly matches an existing Order, the system shall render a table containing every
LineItem belonging to that Order, each row showing at least SKU, title, and the current
`rack_number` value.

**AC-RACK-009a** (Unwanted) — Traces: REQ-RACK-009a. If a user searches by an order number
that matches no existing Order, then the system shall display a not-found message and shall
NOT render a LineItem table.

**AC-RACK-010** (State-Driven) — Traces: REQ-RACK-010. While a LineItem table is displayed,
the system shall render one checkbox per row and one "select all" checkbox in the table
header.

**AC-RACK-010a** (Event-Driven) — Traces: REQ-RACK-010a. When one or more rows are checked, a
rack-number value is entered, and the apply action is triggered, the system shall issue
exactly one bulk-PATCH request covering all checked LineItem ids, and upon success shall clear
all checkbox selections and reflect the new value for the updated rows in the table.

**AC-RACK-010b** (Event-Driven) — Traces: REQ-RACK-010. When the user toggles the "select
all" checkbox, the system shall check or uncheck every row's checkbox to match the toggled
state.

**AC-RACK-010c** (Event-Driven) — Traces: REQ-RACK-010. When the user navigates away from the
page and returns with a fresh search, the system shall reset all checkbox selections.

**AC-RACK-011** (Event-Driven) — Traces: REQ-RACK-011. When a user edits an individual row's
`rack_number` input and confirms the change (independent of any checkbox selection state), the
system shall issue a single-item PATCH request for that LineItem only, and the system shall
show the updated value in the table without a full page reload or navigation.

**AC-RACK-012** (Unwanted) — Traces: REQ-RACK-012. If `OrderDetailPage` is rendered, then the
system shall NOT display any `rack_number` field, label, input, or badge anywhere on the page,
and shall NOT provide any interaction on that page capable of modifying `rack_number`.

**AC-RACK-013** (Unwanted) — Traces: REQ-RACK-013. If a `rack_number` PATCH or upload request
contains a value that duplicates another LineItem's `rack_number`, then the system shall NOT
reject or flag that request for the duplication, and shall NOT enforce any maximum-occupancy
or capacity rule tied to a rack code.

---

## Exclusions (What NOT to Build)

- `OrderDetailPage`에 `rack_number` 노출/편집 UI 추가 — 명시적으로 제외(REQ-RACK-012).
- `Order` 레벨 렉번호 집계/롤업 필드 또는 필터 UI/API — 명시적으로 제외(REQ-RACK-002).
- 렉 위치 용량(capacity) 검증 또는 `rack_number` 고유성(uniqueness) 제약 — 명시적으로
  제외(REQ-RACK-013).
- `rack_number` 값 변경 이력(audit trail) 저장 — 현재 값만 유지, 변경 로그 없음.
- `rack_number` 기준 전역 검색/필터(예: "이 렉에 있는 책 전부 보여줘") — 이 SPEC은
  주문번호 검색 → 해당 주문의 LineItem 목록에만 적용되며, 역방향(렉번호 → 주문 목록) 조회는
  범위 밖.
- `WarehouseStock` 수량/위치 로직과의 연동 — `rack_number`는 `WarehouseStock`과 독립적인
  LineItem 단위 값이며 재고 수량 계산에 관여하지 않는다.

## 관련 SPEC

- SPEC-ORDER-011: `LineItem.logistics_status` 도입 — `location`/`logistics_status`처럼
  물류 관련 LineItem 필드를 추가한 선행 SPEC. 필드 독립성(계산 없는 수동/업로드 전용 필드
  패턴)에 대한 직접적 선례.
- SPEC-ORDER-012: `Order.ready_to_ship` 집계 — 이 SPEC이 명시적으로 채택하지 않는
  "Order 레벨 집계 패턴"의 대조군(counter-example) 성격의 선행 SPEC.
- SPEC-PURCHASE-ORDER-004: 단건/일괄 `purchase_status` PATCH 엔드포인트 — 이 SPEC의 단건/
  일괄 PATCH 엔드포인트 구조(`ids`+값, `missing_ids` 응답)의 직접적 선례.
- SPEC-SHOPIFY-SKU-SET-002: `(order, shopify_line_item_id, sku)` unique_together — 동일
  주문 내 동일 SKU가 2개 이상의 LineItem으로 존재할 수 있는 근거(결정 E의 배경).
