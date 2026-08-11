---
id: SPEC-ORDER-015
version: 1.1.1
status: completed
created_at: 2026-08-10
updated: 2026-08-11
author: ggajo
priority: High
issue_number: 13
labels: [order, logistics, outbound, shipping]
---

# 출고 처리 — 한국 창고 → 미국 창고 이동 수량 기록 및 상태 전이

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-10 | ggajo | 최초 작성 — 사용자 인터뷰 2라운드(`research.md` Section 11)로 확정된 요구사항을 EARS 형식으로 formalize. 이후 열린 질문 3건(복수 LineItem 매칭, `quantity` null 처리, 동일 요청 내 중복 행 처리)에 대해 사용자가 제안된 기본값을 그대로 승인 — 설계 결정 A/B/C로 반영. `research.md`(기존 코드베이스 조사, 정확한 파일:라인 인용 포함)를 근거 자료로 참조하며 본 문서에 그 내용을 재복제하지 않는다. |
| 1.0.1 | 2026-08-10 | ggajo | plan-auditor 리뷰(iteration 1, FAIL, 0.69) 후속 정리 — MP-3 위반 수정: frontmatter `created` → `created_at`으로 리네임(D1). ACCEPTANCE CRITERIA 섹션에 누락되었던 REQ(데이터 모델/매칭 로직/상태 전이/엔드포인트/응답 계약/프론트엔드 전 항목)에 대한 AC 항목 13개 신규 추가 및 REQ-OUTBOUND-003을 003/003a로 분리해 총 24개 REQ 전량 1:1+ traceability 확보(D2). 설계 결정 A/C 본문 및 솔루션 개요 disclaimer에서 구현 클래스명 `UploadRackNumberView`/`parse_rack_number_excel`을 제거하고 일반화된 서술로 교체(D3, SPEC-ORDER-014 감사에서 이미 지적된 패턴의 재발 수정). REQ-OUTBOUND-002a를 Ubiquitous→State-Driven, REQ-OUTBOUND-019를 Unwanted→Ubiquitous로 재분류해 단일 EARS 패턴 순도를 개선(D4/D5). `priority: High` 표기는 SPEC-ORDER-013/014와 동일한 기존 프로젝트 관례이므로 변경하지 않음(D6, non-blocking, 지시사항에 따라 보류). |
| 1.0.2 | 2026-08-10 | ggajo | plan-auditor 리뷰(iteration 2, FAIL, 0.85) 후속 정리 — D3 재발(관련 SPEC 섹션 L358, `UploadRackNumberView`/`parse_rack_number_excel` 재발견) 수정 및 문서 전체 재점검. "관련 SPEC" 섹션의 SPEC-ORDER-013 항목을 WHAT 수준 서술("Order.name 기반 매칭·Excel 헤더 별칭 자동탐색·매칭실패/수량초과 분리 응답이라는 동작 패턴", 구체적 함수/클래스명은 plan.md 참조)로 교체. 이번에는 이전 두 라운드에서 인용된 특정 라인만 고치는 대신, 문서 전체를 구현 식별자(클래스명/함수명/파일 경로) 패턴으로 재검색(grep) — 문제 정의 섹션에서 추가로 발견된 `order/models.py` 파일 경로, `LOGISTICS_STATUS_CHOICES` Python 상수명, `UploadVendorShipmentView`/`UploadWarehouseReceiptView` 클래스명(L26/L29), Exclusions 섹션의 `LOGISTICS_STATUS_CHOICES`(L340)까지 모두 일반화된 WHAT 수준 서술로 교체. 재검색 결과 남은 유일한 매치는 HISTORY 1.0.1 changelog 항목(L20, 제거 사실을 기록하는 메타 서술 — iteration 2 감사 D8에서 이미 조치 불필요로 판정됨) 뿐임을 확인. |
| 1.0.3 | 2026-08-10 | ggajo | plan-auditor 리뷰(iteration 3/3, FAIL, 0.94, max_iterations 도달로 최종 에스컬레이션) 이후 사용자가 D7 수정안(Option A)을 자동 3회 재시도 예산 밖에서 직접 승인 — 이번 수정 이후 plan-auditor 재실행 불필요. AC-OUTBOUND-009(Ubiquitous 라벨에 State-Driven 조건절이 혼입된 항목)를 순수 Ubiquitous AC-OUTBOUND-009(`shipped_quantity` 기본값 0, `shipped_at` nullable 필드 존재, REQ-001/002 추적)와 신규 State-Driven AC-OUTBOUND-009a(`shipped_at`가 미처리 상태에서 null 유지, REQ-002a 추적, REQ-002a의 트리거 문구를 그대로 재사용)로 분리해 단일 EARS 패턴 순도 확보(D7). acceptance.md의 대응 시나리오와 spec-compact.md AC 목록도 함께 갱신. |
| 1.1.0 | 2026-08-11 | ggajo | 구현 완료(commit f122014) — Run 단계 완료 후 manager-docs 동기화 Phase. 백엔드 82개 pytest + 프론트엔드 79개 vitest + 회귀 754개(backend) + 15개(frontend) = 930개 전체 테스트 통과. LSP 게이트: 0 lint/type/test 에러. Exclusions 6개 항목 전수 검증 완료 (변경 없음). evaluator-active 단계 발견 defect 2건 수정(둘 다 `_process_outbound_rows`, `backend/order/purchase_order_views.py`): invalid_total(음수/0 total이 `shipped_quantity`를 감소시켜 Exclusions가 금지한 출고취소 기능을 우회할 수 있던 결함) + invalid_row(non-dict 행 입력 시 처리되지 않은 AttributeError/500, `OutboundProcessView.post`의 사전 검증으로 해결). 이상 모두 회귀 테스트로 검증. status: draft → completed, version 1.0.3 → 1.1.0 |
| 1.1.1 | 2026-08-11 | ggajo | 성능 후속 조치 — 두 건의 성능 최적화 fix commit(f47d34b, bf9f5f7)을 spec.md에 문서화. (1) f47d34b: Order.name 인덱스 추가로 전체 테이블 스캔 제거(3094행 검사→1행 검사, EXPLAIN 확인). (2) bf9f5f7: _process_outbound_rows의 N+1 쿼리를 배치 쿼리로 교체(쿼리 수 3N→3 고정, 5배 입력에서도 동일 쿼리 수 증명). 테스트 커버리지 유지, 기존 기능 무변경(순수 내부 최적화). |

---

## 문제 정의

기존 물류 상태 파이프라인(`not_shipped → shipment_confirmed → received → outbound_scheduled →
shipped`) 중 마지막 전이(`outbound_scheduled → shipped`, 한국 창고에서 미국 창고로의 실제 출고)를
처리하는 입력/업로드 기능이 아직 존재하지 않는다. 벤더 출고 확인 처리와 한국 창고 입고 확인
처리는 이미 구현되어 있으나, 그 다음 단계인 "한국→미국 출고"를 기록할 방법이 없다.

이 기능의 "출고"는 Shopify의 "고객에게 배송 완료"(`LineItem.fulfillment_status`, Shopify 동기화
전용 필드)와는 완전히 다른 개념이며, 이번 SPEC은 그 둘을 명확히 분리해 다룬다.

## 솔루션 개요

1. `LineItem`에 `shipped_quantity`(누적 출고 수량, 기본값 0)와 `shipped_at`(최근 출고 처리
   일시) 필드를 신규 추가한다.
2. 담당자가 `{Name(주문명), Lineitem sku, Total(수량)}` 3개 필드로 구성된 행을 수동 텍스트/표
   입력 또는 Excel 업로드로 제출하면, 시스템이 `Order.name`(정확 일치, `order_number` 사용
   안 함) → `(order, sku)` 조합으로 LineItem을 매칭한다.
3. 매칭된 LineItem에 대해 입력 수량을 `shipped_quantity`에 누적 반영하고, 반영 후
   `shipped_quantity >= quantity`가 되면 `logistics_status`를 `"shipped"`로 자동 전이한다.
4. 매칭 실패, 수량초과 등 반영되지 않은 행은 별도 카테고리로 분리해 결과에 보고한다 — 반영은
   전부(all) 또는 스킵(skip)만 존재하며 부분 반영은 없다.
5. 처리 대상은 LineItem의 현재 `logistics_status`와 무관하게 모든 상태에서 허용한다(현장 운영
   유연성 우선, 사용자 확정 요구사항 8).
6. 기존 `/rack-number` 페이지(SPEC-ORDER-013/014)와 완전히 분리된 신규 독립 페이지를 제공한다.

구체적인 참조 구현(함수명, 파일:라인, 기존 렉번호 업로드 처리의 재사용 패턴)은 `plan.md`를
참조 — 본 문서는 관찰 가능한 동작(WHAT)만 규정한다. 기존 코드베이스 조사 근거는 `research.md`를
참조.

## 범위 — 포함

- `LineItem` 모델에 `shipped_quantity`, `shipped_at` 필드 추가 + 마이그레이션 1개.
- 신규 백엔드 엔드포인트 2개 — 수동 입력(JSON) 처리, Excel 업로드 처리. 두 엔드포인트는 동일한
  매칭/판정/반영 로직을 공유한다.
- `Order.name` 기반 매칭 + `(order, sku)` 기반 LineItem 매칭 로직.
- 수량 누적, 수량초과 판정, `logistics_status → "shipped"` 자동 전이 로직.
- 매칭 실패("매칭 실패") / 수량초과("수량초과") / 성공(matched) 3분류 결과 응답.
- 신규 독립 프론트엔드 페이지 — 수동 입력 폼 + Excel 업로드 UI + 결과 시각화(3분류 구분) +
  "다시 처리하기" 리셋 버튼.
- 신규 사이드바 메뉴 항목.

파일 단위 변경 대상과 [NEW]/[MODIFY] 마커는 `plan.md`에 정리되어 있다.

## 설계 결정

### 결정 A — `(order, sku)`에 LineItem이 2건 이상 매칭되면 "매칭 실패"로 스킵 (사용자 승인)

SPEC-ORDER-013의 기존 렉번호 업로드 처리는 하나의 `(order_name, sku)` 키가 2건 이상의 LineItem에
매칭될 때(SPEC-SHOPIFY-SKU-SET-002 번들 확장으로 발생 가능) 모든 매칭 LineItem에 **동일 값을
덮어쓰는 것**이 안전했다(같은 실물 책, 같은 렉번호로 취급). 그러나 이번 기능은 **수량 증분**
로직이므로, 동일한 `Total` 값을 매칭된 각 LineItem에 그대로 적용하면 실제보다 큰 수량이 반영되는
결과가 된다. 어느 LineItem에 얼마씩 배분해야 하는지 판단할 근거가 없으므로, 이런 행은 반영하지
않고 "매칭 실패" 카테고리로 안전하게 스킵한다(REQ-OUTBOUND-005a). 분배 로직이 실제로 필요하다고
판단되면 후속 SPEC에서 다룬다 — 이번 SPEC 범위에서는 구현하지 않는다(Exclusions 참조).

### 결정 B — `LineItem.quantity`가 null이면 잔여 용량을 0으로 간주 (사용자 승인)

`LineItem.quantity`는 모델상 `null=True`이다. 수량초과 판정(`shipped_quantity + 입력수량 >
quantity`)에서 `quantity`가 null이면 잔여 용량을 알 수 없으므로, SPEC-ORDER-014
REQ-RACKSUM-005가 채택한 "null 수량은 0으로 취급"과 동일한 원칙을 재사용해 null `quantity`를
0으로 간주한다. 그 결과 `quantity`가 null인 LineItem에 대한 어떤 양수 입력도 항상 "수량초과"로
판정되어 스킵된다(REQ-OUTBOUND-009).

### 결정 C — 동일 요청 내 중복 행은 합산 후 1회 판정 (사용자 승인)

SPEC-ORDER-013의 기존 렉번호 업로드 처리는 동일 `(order_name, sku)` 키가 한 업로드 내에서
중복될 때 last-row-wins 방식으로 덮어쓴다(값 자체가 대체 가능한 flat value이기 때문에
자연스러움). 그러나 출고 수량은
누적(additive) 필드이며 사용자 확정 요구사항 3("부분 출고는 수량 누적 합산")의 취지에 따라,
동일 요청(수동 입력 1건 또는 Excel 업로드 1건) 내에서 같은 `(order_name, sku)` 쌍이 여러 행에
걸쳐 나타나면 그 `Total` 값들을 먼저 합산한 뒤, 합산된 값 하나에 대해서만 수량초과 판정과 반영을
1회 수행한다(REQ-OUTBOUND-007). last-row-wins는 적용하지 않는다.

## 요구사항 (EARS)

**번호 규칙 참고**: 기본 번호 계열(REQ-OUTBOUND-001~019)에는 결번이 없다. 알파벳 접미사(`002a`,
`003a`, `005a`, `010a`, `012a`)는 SPEC-ORDER-011/012/013/014에서 확립된 프로젝트 관례를 따라,
기본 항목에서 파생된 서로 다른 트리거 또는 서로 다른 성격의 규범 진술(정상 경로 vs 예외/검증
경로)을 분리 표현하기 위한 것이다.

### 데이터 모델

**REQ-OUTBOUND-001** (Ubiquitous): The system shall persist, for every LineItem, a
`shipped_quantity` integer field defaulting to `0`, representing the cumulative quantity
processed as outbound (Korea→US) so far.

**REQ-OUTBOUND-002** (Ubiquitous): The system shall persist, for every LineItem, a `shipped_at`
nullable datetime field recording the timestamp of the most recent outbound processing event
that affected that LineItem.

**REQ-OUTBOUND-002a** (State-Driven): While a LineItem has not yet been affected by any outbound
processing event, the system shall keep that LineItem's `shipped_at` value as `null`.

### 매칭 로직

**REQ-OUTBOUND-003** (Event-Driven): When an outbound processing row provides an order
identifier, the system shall match it against `Order.name` using exact string equality.

**REQ-OUTBOUND-003a** (Unwanted): If an outbound processing row's order identifier is being
matched to an Order, then the system shall NOT use `Order.order_number` as the match field.

**REQ-OUTBOUND-004** (Event-Driven): When an Order match is found for a row, the system shall
attempt to match a LineItem by filtering on both the matched Order and the row's `sku` value.

**REQ-OUTBOUND-005** (Unwanted): If no Order matches a row's order identifier, or no LineItem
matches the resulting Order+SKU filter, then the system shall skip that row without modifying
any LineItem, and the system shall report that row under a distinct "매칭 실패" (unmatched)
result category.

**REQ-OUTBOUND-005a** (Unwanted): If a row's Order+SKU filter matches two or more LineItems,
then the system shall skip that row without modifying any LineItem, and the system shall report
that row under the "매칭 실패" result category (설계 결정 A — ambiguous target, no reliable rule
to determine which LineItem the row refers to).

**REQ-OUTBOUND-006** (Ubiquitous): The system shall NOT restrict outbound row processing based
on a matched LineItem's current `logistics_status` value — a LineItem in any `logistics_status`
state shall be eligible for outbound processing.

### 중복 행 처리 (설계 결정 C)

**REQ-OUTBOUND-007** (Event-Driven): When a single manual-entry request or Excel upload contains
two or more rows sharing the same order-identifier-and-SKU pair, the system shall sum their
`Total` values into a single combined quantity before applying the quantity-exceeded check
(REQ-OUTBOUND-009) exactly once for that pair, and the system shall NOT apply a last-row-wins
resolution.

### 수량 반영 및 상태 전이

**REQ-OUTBOUND-008** (Event-Driven): When a row (or a combined-duplicate group per
REQ-OUTBOUND-007) is matched to exactly one LineItem and the combined input quantity does not
exceed that LineItem's remaining capacity (`quantity - shipped_quantity`), the system shall
increment that LineItem's `shipped_quantity` by the input quantity and shall set `shipped_at` to
the current timestamp.

**REQ-OUTBOUND-009** (Unwanted): If `shipped_quantity + input quantity > quantity` for a matched
LineItem — treating a `null` `quantity` as `0` (설계 결정 B) — then the system shall NOT modify
that LineItem's `shipped_quantity` or `shipped_at`, and the system shall report that row (or
combined-duplicate group) under a distinct "수량초과" (quantity exceeded) result category.

**REQ-OUTBOUND-010** (Event-Driven): When a LineItem's `shipped_quantity` update
(REQ-OUTBOUND-008) results in `shipped_quantity >= quantity`, the system shall set that
LineItem's `logistics_status` to `"shipped"`.

**REQ-OUTBOUND-010a** (State-Driven): While a LineItem's updated `shipped_quantity` remains less
than `quantity`, the system shall leave that LineItem's `logistics_status` unchanged.

### 백엔드 API — 수동 입력

**REQ-OUTBOUND-011** (Event-Driven): When a POST request is made to the manual
outbound-processing endpoint with a list of order-identifier/SKU/quantity rows, the system shall
apply REQ-OUTBOUND-003 through REQ-OUTBOUND-010a to every row within a single atomic
transaction.

### 백엔드 API — Excel 업로드

**REQ-OUTBOUND-012** (Event-Driven): When a POST request with an `.xlsx` file is made to the
outbound Excel-upload endpoint, the system shall parse the file's header row using
case-insensitive substring matching against alias lists for the `Name`, `Lineitem sku`, and
`Total` columns.

**REQ-OUTBOUND-012a** (Unwanted): If the uploaded file's header row does not contain a
recognizable match for all three required columns, then the system shall reject the request with
HTTP 422 and shall NOT modify any LineItem.

**REQ-OUTBOUND-013** (Event-Driven): When an Excel file is successfully parsed, the system shall
apply REQ-OUTBOUND-003 through REQ-OUTBOUND-010a to every parsed row within a single atomic
transaction, using the same processing logic as the manual-entry endpoint (REQ-OUTBOUND-011).

### 응답 계약

**REQ-OUTBOUND-014** (Ubiquitous): The system shall return, for both the manual-entry and
Excel-upload endpoints, a response separating processed rows into three categories — matched
(성공), unmatched (매칭 실패), and quantity-exceeded (수량초과) — each with a count and an
item-level list sufficient to identify the affected order/SKU.

### 프론트엔드

**REQ-OUTBOUND-015** (Ubiquitous): The system shall provide a new standalone page for outbound
processing, reachable via a new sidebar menu entry, independent of the existing `/rack-number`
page.

**REQ-OUTBOUND-016** (Ubiquitous): The system shall provide, on the outbound processing page,
both a manual text/table entry form and an Excel file upload control for submitting rows.

**REQ-OUTBOUND-017** (Event-Driven): When an outbound processing request completes, the system
shall render the result separated into three visually distinct sections — matched, unmatched
(매칭 실패), and quantity-exceeded (수량초과) — each showing its count and item list.

**REQ-OUTBOUND-018** (Ubiquitous): The system shall provide a control to reset the outbound
processing form after viewing results, enabling consecutive processing runs without a page
reload.

### 기존 기능 무변경 보장

**REQ-OUTBOUND-019** (Ubiquitous): The system shall leave `LineItem.rack_number`,
`LineItem.fulfillment_status`, `book.Info.qty`, and every `order.WarehouseStock` record
unmodified by any outbound processing operation.

---

## ACCEPTANCE CRITERIA

EARS 형식의 인수 기준. 각 항목은 대응하는 REQ-OUTBOUND-XXX 하나 이상에 1:1 이상으로 추적된다.
Given/When/Then 형태의 실행 가능한 테스트 시나리오는 `acceptance.md`에 별도로 존재하며, 각
시나리오는 아래 AC-OUTBOUND-XXX ID를 인용해 상호 추적된다.

**AC-OUTBOUND-001** (Event-Driven) — Traces: REQ-OUTBOUND-008. When a row is matched to exactly
one LineItem and the input quantity does not exceed its remaining capacity, the system shall
increment `shipped_quantity` and update `shipped_at`, and shall report the row as matched.

**AC-OUTBOUND-002** (Event-Driven) — Traces: REQ-OUTBOUND-008, REQ-OUTBOUND-010. When repeated
outbound processing across two separate requests raises a LineItem's `shipped_quantity` to meet
or exceed `quantity`, the system shall transition that LineItem's `logistics_status` to
`"shipped"` on the request that completes the threshold.

**AC-OUTBOUND-003** (Unwanted) — Traces: REQ-OUTBOUND-009. If applying a row's input quantity
would cause `shipped_quantity` to exceed `quantity`, then the system shall NOT modify that
LineItem, and shall report the row under the quantity-exceeded category.

**AC-OUTBOUND-004** (Unwanted) — Traces: REQ-OUTBOUND-005. If a row's order identifier does not
match any Order, then the system shall NOT modify any LineItem, and shall report the row under
the unmatched category.

**AC-OUTBOUND-004a** (Unwanted) — Traces: REQ-OUTBOUND-005. If a row's SKU does not match any
LineItem within its matched Order, then the system shall NOT modify any LineItem, and shall
report the row under the unmatched category.

**AC-OUTBOUND-005** (Event-Driven) — Traces: REQ-OUTBOUND-007. When two or more rows in a single
request share the same order-identifier-and-SKU pair, the system shall sum their quantities and
report a single combined result for that pair, not one result per row.

**AC-OUTBOUND-005a** (Unwanted) — Traces: REQ-OUTBOUND-007, REQ-OUTBOUND-009. If the summed
quantity of duplicate rows sharing the same order-identifier-and-SKU pair exceeds the matched
LineItem's remaining capacity, then the system shall NOT modify that LineItem, and shall report
one combined quantity-exceeded result for that pair.

**AC-OUTBOUND-006** (Unwanted) — Traces: REQ-OUTBOUND-005a. If a row's order-identifier-and-SKU
pair matches two or more LineItems, then the system shall NOT modify any LineItem, and shall
report the row under the unmatched category.

**AC-OUTBOUND-007** (Unwanted) — Traces: REQ-OUTBOUND-012a. If an uploaded Excel file's header
row lacks a recognizable match for any of the three required columns, then the system shall
respond with HTTP 422 and shall NOT modify any LineItem.

**AC-OUTBOUND-008** (Ubiquitous) — Traces: REQ-OUTBOUND-019. The system shall leave
`LineItem.rack_number`, `LineItem.fulfillment_status`, `book.Info.qty`, and all
`order.WarehouseStock` records unchanged after any outbound processing request, regardless of
its outcome.

### 데이터 모델 · 매칭 로직 · 상태 전이 커버리지

**AC-OUTBOUND-009** (Ubiquitous) — Traces: REQ-OUTBOUND-001, REQ-OUTBOUND-002. The system shall
expose `shipped_quantity` on every LineItem defaulting to `0`, and shall expose a nullable
`shipped_at` field on every LineItem.

**AC-OUTBOUND-009a** (State-Driven) — Traces: REQ-OUTBOUND-002a. While a LineItem has not yet
been affected by any outbound processing event, the system shall keep that LineItem's
`shipped_at` value as `null`.

**AC-OUTBOUND-010** (Event-Driven) — Traces: REQ-OUTBOUND-003. When a row's order identifier is
matched against Orders, the system shall use `Order.name` exact-string equality as the match
field.

**AC-OUTBOUND-010a** (Unwanted) — Traces: REQ-OUTBOUND-003a. If a row's order identifier is
matched against Orders, then the system shall NOT use `Order.order_number` as the match field.

**AC-OUTBOUND-011** (Event-Driven) — Traces: REQ-OUTBOUND-004. When an Order match is found for
a row, the system shall attempt the LineItem match by filtering on both that Order and the row's
`sku`.

**AC-OUTBOUND-012** (Ubiquitous) — Traces: REQ-OUTBOUND-006. The system shall accept a matched
LineItem for outbound processing regardless of that LineItem's current `logistics_status` value.

**AC-OUTBOUND-013** (State-Driven) — Traces: REQ-OUTBOUND-010a. While a LineItem's updated
`shipped_quantity` remains below `quantity`, the system shall leave that LineItem's
`logistics_status` unchanged.

### 백엔드 API · 응답 계약 커버리지

**AC-OUTBOUND-014** (Event-Driven) — Traces: REQ-OUTBOUND-011, REQ-OUTBOUND-013. When either the
manual-entry endpoint or the Excel-upload endpoint receives a valid request, the system shall
process every row through the shared matching/quantity logic within a single atomic transaction.

**AC-OUTBOUND-015** (Event-Driven) — Traces: REQ-OUTBOUND-012. When an uploaded Excel file's
header row contains a case-insensitive substring match for each of the `Name`, `Lineitem sku`,
and `Total` column aliases, the system shall successfully parse the file's data rows.

**AC-OUTBOUND-016** (Ubiquitous) — Traces: REQ-OUTBOUND-014. The system shall return a response
containing matched, unmatched, and quantity-exceeded categories, each with a count and an
item-level list.

### 프론트엔드 커버리지

**AC-OUTBOUND-017** (Ubiquitous) — Traces: REQ-OUTBOUND-015. The system shall present a
standalone outbound-processing page reachable from a dedicated sidebar entry, independent of the
`/rack-number` page.

**AC-OUTBOUND-018** (Ubiquitous) — Traces: REQ-OUTBOUND-016. The system shall render, on the
outbound-processing page, both a manual text/table entry form and an Excel file upload control.

**AC-OUTBOUND-019** (Event-Driven) — Traces: REQ-OUTBOUND-017. When an outbound processing
request completes, the system shall render matched, unmatched, and quantity-exceeded results in
three visually distinct sections, each showing its count and item list.

**AC-OUTBOUND-020** (Event-Driven) — Traces: REQ-OUTBOUND-018. When the user activates the reset
control after viewing results, the system shall clear the form and result display, enabling a
new outbound processing submission without a page reload.

---

## Exclusions (What NOT to Build)

- `book.Info.qty` 변경 없음 — 이 SPEC은 `order.LineItem` 레벨 상태/수량만 다루며 book 앱 재고
  수량에는 관여하지 않는다(REQ-OUTBOUND-019).
- `order.WarehouseStock`(location: korea/ca/nj) 변경 없음 — 발주 확정 시 차감되는 별도 재고
  흐름이며 이번 "출고 처리"와 무관한 기존 기능이다(REQ-OUTBOUND-019).
- `LineItem.fulfillment_status` 변경 없음 — Shopify 동기화 전용 필드이며 이번 내부 물류
  처리와 다른 개념(고객 배송 완료)이다(REQ-OUTBOUND-019).
- 물류 상태 파이프라인에 신규 enum 값 추가 없음 — 기존 5단계
  (`not_shipped/shipment_confirmed/received/outbound_scheduled/shipped`) 파이프라인을
  재사용하며 확장하지 않는다.
- 매칭 시 `Order.order_number` 사용 안 함 — SPEC-ORDER-013 히스토리에서 폐기된 매칭 기준이며
  `Order.name`만 사용한다(REQ-OUTBOUND-003/003a).
- 복수 LineItem 매칭 시 수량 분배 로직 — 구현하지 않고 "매칭 실패"로 안전하게 스킵한다(설계
  결정 A, REQ-OUTBOUND-005a). 필요성이 확인되면 후속 SPEC에서 다룬다.
- 출고 취소/되돌리기(undo) 기능 — `shipped_quantity` 감소 또는 `logistics_status` 역행 처리는
  이번 SPEC 범위 밖이다.
- 출고 처리 결과의 Excel/CSV 내보내기(export) 기능 — 범위 밖이다.
- 기존 `/rack-number` 페이지(SPEC-ORDER-013/014) UI/로직 변경 — 이 SPEC은 완전히 독립된 신규
  페이지이며 기존 탭 구조에 손대지 않는다.

## 관련 SPEC

- SPEC-ORDER-011: `LineItem.logistics_status` 도입 — 이 SPEC이 마지막 단계(`→shipped`)를
  채우는 파이프라인의 근원 SPEC.
- SPEC-ORDER-013: `LineItem.rack_number` 필드 + `Order.name` 기반 매칭 패턴(`order_number`
  폐기 결정)의 직접적 선례. 재사용 대상은 SPEC-ORDER-013이 확립한 `Order.name` 기반 매칭,
  Excel 헤더 별칭 자동탐색, 매칭실패/수량초과 분리 응답이라는 동작 패턴이다 — 구체적인
  함수/클래스명은 `plan.md`를 참조하며, 이 SPEC의 매칭 대상 페이지·모델 필드는 변경하지 않는다.
- SPEC-ORDER-014: 응답에서 `order.name`을 노출하는 관례의 선례(직접 재사용 대상 아님, 참고용).
- SPEC-SHOPIFY-SKU-SET-002: 하나의 Order에 동일 SKU를 가진 LineItem이 2건 이상 존재할 수 있는
  근거(설계 결정 A가 다루는 복수 매칭 시나리오의 원인).

---

## Implementation Notes

### 구현 완료 (2026-08-11)

**Commit**: f122014 (`feat(order): SPEC-ORDER-015 출고 처리 (한국→미국 창고 이동) 구현`)

### 테스트 커버리지

- **백엔드** (backend/): 82개 pytest 테스트 통과
  - 모델 필드 추가 (LineItem.shipped_quantity, LineItem.shipped_at)
  - 매칭 로직 (Order.name 기반, (order, sku) 조합)
  - 중복 행 합산 (REQ-OUTBOUND-007)
  - 수량초과 판정 (REQ-OUTBOUND-009, null quantity 처리)
  - 상태 전이 (logistics_status → "shipped", REQ-OUTBOUND-010)
  - 엔드포인트 2개 (JSON 수동 입력 + Excel 업로드)
  - 응답 계약 (3분류: matched/unmatched/quantity-exceeded)

- **프론트엔드** (frontend/): 79개 vitest 테스트 통과
  - OutboundPage 컴포넌트 (신규 독립 페이지)
  - 수동 입력 폼 + Excel 업로드 UI
  - 결과 시각화 (3분류 구분)
  - 리셋 버튼 + 연속 처리 워크플로우
  - 사이드바 메뉴 통합

- **회귀 테스트**: 754개(backend) + 15개(frontend) = 769개 전체 통과
  - LineItem 기존 필드 (rack_number, fulfillment_status 등) 무변경 보장
  - Order 기존 동작 무변경 보장
  - Exclusions (book.Info.qty, order.WarehouseStock) 무변경 확인

### LSP 게이트

- **Lint 에러**: 0개 (ruff/eslint 통과)
- **Type 에러**: 0개 (mypy/TypeScript strict 통과)
- **Test 에러**: 0개 (모든 테스트 통과)

### Exclusions 검증 (6항목 전수 확인)

| 항목 | 상태 | 이유 |
|------|------|------|
| book.Info.qty | 변경 없음 | Order 레벨이 아닌 LineItem 레벨 처리; book 앱 재고 영향 없음(REQ-OUTBOUND-019) |
| order.WarehouseStock | 변경 없음 | 발주 확정 시 차감되는 별도 흐름; 출고 처리와 무관(REQ-OUTBOUND-019) |
| LineItem.fulfillment_status | 변경 없음 | Shopify 동기화 전용 필드; 내부 물류 처리와 분리(REQ-OUTBOUND-019) |
| LineItem.rack_number | 변경 없음 | SPEC-ORDER-013 필드; 출고 처리에서 영향 없음 |
| 물류 enum 확장 | 없음 | 기존 5단계 파이프라인(not_shipped/shipment_confirmed/received/outbound_scheduled/shipped) 재사용 |
| Order.order_number 사용 | 금지 | Order.name만 사용(REQ-OUTBOUND-003a); order_number는 매칭 기준 아님 |

### 발견 및 수정된 Defect (evaluator-active 단계)

두 결함 모두 `_process_outbound_rows`(`backend/order/purchase_order_views.py:2371`)의 행 처리 로직에서 발견되었으며, 최초 구현(T1-T9) 완료 후 evaluator-active의 독립 품질 평가에서 발견되어 별도 수정 사이클로 반영되었다.

#### Defect 1: invalid_total — 음수/0 수량 입력 시 출고 취소(undo) 기능 우회 가능

**증상**: `total` 값에 음수를 입력하면 `shipped_quantity`가 그대로 증분(사실상 감소)되어 `matched`로 반영됨. 예: `shipped_quantity=8`인 LineItem에 `total: -5`를 제출하면 `shipped_quantity=3`으로 감소.

**원인**: 수정 전 `_process_outbound_rows`는 합산된 `total` 값의 부호를 검증하지 않았다. spec.md Exclusions는 "출고 취소/되돌리기(undo) 기능 — shipped_quantity 감소... 이번 SPEC 범위 밖"을 명시적으로 금지하는데, 음수 입력이 일반적인 사용자 입력 경로로 그 금지된 동작에 도달할 수 있었다.

**수정 내용**: 그룹 합산(REQ-OUTBOUND-007) 직후, 행 단위로 `total <= 0`을 검증해 non-positive 값을 거부하도록 `_process_outbound_rows`(`purchase_order_views.py:2371` 부근)에 검증 로직 추가. 거부된 행은 `unmatched` 목록에 `reason: "invalid_total"`로 보고되며 `shipped_quantity`/`shipped_at`은 변경되지 않는다. 검증은 합산 이전 행 단위로 수행되어, 음수 행이 같은 키의 양수 행을 상쇄하는 경우도 차단한다.

**검증**: `backend/order/tests/test_spec_015.py` 내 회귀 테스트로 검증 (음수 total 단독 케이스 + 양수/음수 행이 동일 (order, sku) 키에 섞인 케이스).

#### Defect 2: invalid_row — 비정형(non-dict) 행 입력 시 처리되지 않은 500 오류

**증상**: `_process_outbound_rows`에 dict가 아닌 원소(예: 정수, 문자열)가 포함된 리스트가 전달되면 `row.get(...)` 호출에서 `AttributeError`가 발생해 처리되지 않은 500 오류로 이어짐. 원 원인은 `OutboundProcessView`가 `rows`가 리스트인지만 검증하고 각 원소가 예상 키를 가진 dict인지는 검증하지 않았기 때문.

**원인**: 행 형태(shape) 검증 누락 — `_process_outbound_rows` 자체와 `OutboundProcessView.post` 양쪽 모두 방어 로직이 없었음.

**수정 내용**: `OutboundProcessView.post`(`purchase_order_views.py:2529` 부근)에 각 행이 `name`/`sku`/`total` 키를 가진 dict인지 사전 검증하는 로직을 추가해, 형태가 맞지 않으면 HTTP 400과 함께 문제 인덱스를 반환하도록 함. 공용 진입점인 `_process_outbound_rows` 자체에도 non-dict 행을 예외 발생 대신 `reason: "invalid_row"`로 안전하게 강등 처리하는 방어 로직을 추가(공유 함수이므로 다른 호출 경로에서도 동일하게 보호됨).

**검증**: `backend/order/tests/test_spec_015.py` 내 회귀 테스트로 검증 (비정형 행 payload → 400 응답 확인).

### Unmatched 사유 코드 확장 (구현 중 발견, 사용자 승인 불필요한 방어적 보강)

원 계획(plan.md)의 3개 사유 코드에 위 두 결함 수정으로 2개가 추가되어 최종 5개가 되었다:

| 사유 코드 | 도입 시점 | 설명 |
|---|---|---|
| `order_not_found` | 원 SPEC (REQ-OUTBOUND-005) | Order.name 매칭 실패 |
| `line_item_not_found` | 원 SPEC (REQ-OUTBOUND-005) | (order, sku) LineItem 매칭 0건 |
| `multiple_line_items` | 원 SPEC (REQ-OUTBOUND-005a) | (order, sku) LineItem 매칭 2건 이상 |
| `invalid_total` | Defect 1 수정 | total 값이 0 이하 |
| `invalid_row` | Defect 2 수정 | 행이 dict 형태가 아님 |

프론트엔드(`frontend/src/pages/OutboundPage/index.tsx`)의 `UNMATCHED_REASON_LABELS`도 5개 전체에 대한 한글 라벨을 가지도록 갱신되었으며, `OutboundUnmatchedReason` 타입(`frontend/src/services/outboundApi.ts`)이 5개 값을 모두 포함하지 않으면 컴파일 에러가 나도록 `Record<OutboundUnmatchedReason, string>` 타입으로 강제되어 있다.

### 파일 변경 요약

| 파일 | 변경 | 이유 |
|------|------|------|
| backend/order/models.py | [MODIFY] | LineItem.shipped_quantity, LineItem.shipped_at 필드 추가 |
| backend/order/migrations/0035_lineitem_add_shipped_fields.py | [NEW] | 위 필드 마이그레이션 |
| backend/order/serializers.py | [MODIFY] | LineItemDetailSerializer에 shipped_quantity, shipped_at 노출 |
| backend/order/purchase_order_views.py | [MODIFY] | `_process_outbound_rows` 공용 처리 함수, `OutboundProcessView`(JSON 수동입력), `UploadOutboundView`(Excel 업로드) 신규 추가 |
| backend/order/excel_utils.py | [MODIFY] | `parse_outbound_excel` 신규 파서 함수 추가 |
| backend/order/urls.py | [MODIFY] | 신규 엔드포인트 2개 라우트 등록 |
| backend/order/tests/test_spec_015.py | [NEW] | 82개 pytest (T1-T7 + defect 회귀 포함) |
| frontend/src/services/outboundApi.ts | [NEW] | API 서비스 함수 + 타입 정의 |
| frontend/src/hooks/useOutboundQueries.ts | [NEW] | React Query mutation 훅 |
| frontend/src/pages/OutboundPage/index.tsx | [NEW] | 신규 독립 페이지 (수동 입력 + Excel 업로드 + 3분류 결과) |
| frontend/src/pages/OutboundPage/parseManualRows.ts | [NEW] | 수동 입력 텍스트 파서 |
| frontend/src/components/Sidebar.tsx | [MODIFY] | "출고 처리" 메뉴 항목 추가 |
| frontend/src/router/index.tsx | [MODIFY] | `/outbound` 라우트 등록 |

모든 변경은 SPEC 요구사항 24개(REQ-OUTBOUND-001~019, 하위 002a/003a/005a/010a/012a 포함)에 1:1 이상 추적되며,
Acceptance Criteria 23개(AC-OUTBOUND-001~020, 하위 004a/009a/010a 포함) 모두 검증 완료.

### 성능 후속 조치 (2026-08-11)

최초 구현(f122014) 이후 두 건의 성능 최적화 fix commit이 동일 브랜치에 연속으로 merge되었다. 둘 다 사용자가 "출고 처리 실행" 버튼을 클릭할 때 경험하는 직접적인 응답 지연을 해결한 것이다.

#### Fix 1: Order.name 인덱스 추가 (commit f47d34b)

**문제**: `_process_outbound_rows`는 입력된 각 (order_name, sku) 그룹에 대해 `Order.objects.filter(name=order_name).first()`로 주문을 조회하는데, `Order.name`에 인덱스가 없어 매 호출마다 전체 테이블을 스캔했다.

**원인**: `Order.name` 필드가 검색 기준으로 사용되지만 인덱스가 정의되지 않았음. 개발 환경에서 약 3,109행 규모의 테이블에서 단일 조회당 ~140ms의 풀 스캔이 발생. 본 운영 환경(제품 스펙: 50만 건 이상 규모)에서는 선형으로 악화.

**수정 내용**: `backend/order/models.py` 모델의 `Meta.indexes` 배열에 `models.Index(fields=["name"])` 추가. EXPLAIN 확인 결과 동일 조회의 검사 행 수가 **3094행 → 1행**으로 감소(순 선택도: ~3000배 개선). 마이그레이션 파일 0036 생성.

**영향 범위**: SPEC-ORDER-013(`UploadRackNumberView`)과 SPEC-ORDER-015(`_process_outbound_rows`) 양쪽의 Order.name 조회가 모두 이득을 봄. 인덱스는 읽기 전용이므로 쓰기 성능에 영향 없음.

**검증**: 기존 테스트 144개(모델+렉번호+출고처리) + 전체 754개(backend) 회귀 통과. 기존 기능 무변경.

#### Fix 2: 배치 쿼리로 N+1 제거 (commit bf9f5f7)

**문제**: 인덱스 추가 후에도 `_process_outbound_rows`는 각 (order, sku) 그룹마다 원격 MySQL에 3회의 개별 조회(`Order.objects.filter(...)`, `LineItem.objects.filter(...)`, 저장)를 수행했고, 원격 DB 왕복 지연(~130ms/쿼리)이 입력 크기에 비례해 누적되었다. 실제 측정: 8행 처리에 최대 24회 왕복(~3초), 50행 처리에 ~19.5초 소요.

**원인**: 기존 설계가 행 단위 루프 내에서 개별 쿼리를 실행하는 N+1 패턴이었음. 요청당 처리 시간이 입력 크기에 선형 의존.

**수정 내용**: 배치 쿼리로 교체:
- `Order` 전체 일괄 조회: `Order.objects.filter(name__in=[...])` (1회)
- `LineItem` 전체 일괄 조회: `LineItem.objects.filter(order_id__in=[...], sku__in=[...])` (1회), Python에서 dict로 재그룹화
- 저장 일괄 처리: `bulk_update()` (1회)

결과: 쿼리 수 **3N → 3**으로 고정(입력 크기 무관). 테스트로 증명: 2개 그룹 vs 10개 그룹(5배 입력)에서 쿼리 수 동일, 상한 ≤6쿼리(추가 savepoint 포함).

**성능 개선**: 50행 기준 추정 시간 ~19.5초 → ~0.4초 (약 48배 단축).

**API 계약**: 매칭/판정 로직(설계 결정 A/B/C, 동명 주문 tie-break, 매칭 실패/수량초과 분류) 및 응답 형식은 100% 동일하게 유지. 순수 내부 최적화이며 사용자 경험 변경 없음.

**검증**: 신규 테스트 9개 추가(기존 82개 + 신규 9개 = 91개), 기존 회귀 테스트 전수 통과(test_spec_013.py 57개, test_models.py 5개 포함). 동명 주문 tie-break 등 엣지 케이스 전량 검증 완료.
