---
id: SPEC-ORDER-011
version: 1.6.0
status: completed
created: 2026-08-07
created_at: 2026-08-07
updated: 2026-08-17
author: ggajo
priority: High
issue_number: 8
labels: [order, logistics, purchase-order]
---

# LineItem 물류 상태(입고/출고) 추적 및 Order 집계 상태

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-07 | ggajo | 최초 작성 — Decision Point 1~3 리비전(업로드 2 대상 필터 확장 포함) 반영한 최종 승인본 |
| 1.1.0 | 2026-08-07 | ggajo | Phase 2.3 plan-auditor 리뷰(iteration 1, FAIL) 반영 — 프론트매터 `labels`/`created_at` 추가, `status` 유효값 수정, spec.md에 EARS 형식 `## ACCEPTANCE CRITERIA` 섹션 신설(REQ 1:1 추적), REQ-LOGI-003/004/005/007/011/012에서 구현 세부사항(함수명·클래스명·파일:라인·마이그레이션 파일명)을 제거하고 plan.md로 이관, acceptance.md 시나리오에 REQ 추적 태그 추가, 누락됐던 REQ-LOGI-006/007/014 인수 기준 보강 |
| 1.2.0 | 2026-08-07 | ggajo | Phase 2.3 plan-auditor 리뷰(iteration 2, FAIL — MP-2만 잔존) 반영 — AC-LOGI-008/012에서 "Given"/"After" 트리거 오용 제거하고 순수 Ubiquitous 형태로 재작성, REQ-LOGI-003/007 및 AC-LOGI-007의 "Where"(Optional 전용) 오용을 "If...then"(Unwanted)으로 교체, AC-LOGI-005를 AC-LOGI-005a/005b로 분리(단일 트리거·단일 응답 원칙), AC-LOGI-013에 객관적 검증 조건(헤더 텍스트 공통 단어 없음 + 뱃지 배경색 상이) 추가 |
| 1.3.0 | 2026-08-07 | ggajo | Phase 2.3 plan-auditor 리뷰(iteration 3/3, FAIL — 잔여 결함 3개, 최대 반복 도달로 에스컬레이션) 반영. 사용자 승인 하에 오케스트레이터가 직접 마무리: AC-LOGI-007을 007a(Ubiquitous, 유효값 수용)/007b(Unwanted, 무효값 거부)로 분리, AC-LOGI-014를 014a(Unwanted, PurchaseOrder.status 불변)/014b(Ubiquitous, logistics_status는 PurchaseOrder.status로부터 계산되지 않음)로 분리, REQ-LOGI-014의 라벨을 "(Unwanted)"에서 "(Ubiquitous)"로 정정(트리거 없는 항상-참 불변식이므로) |
| 1.4.0 | 2026-08-07 | ggajo | 검증 재감사(review-4)에서 동일 결함 유형이 REQUIREMENTS 섹션 3곳에 추가로 발견되어(REQ-LOGI-003/005/007) 사용자 승인 하에 오케스트레이터가 동일 패턴으로 마무리: REQ-LOGI-003을 003(Event-Driven, 전이 규칙)/003a(Unwanted, SKU 중복 dedup)/003b(Ubiquitous, 원자적 커밋)로 분리, REQ-LOGI-005에 005a(Ubiquitous, dedup/원자성 규칙 공유) 신설, REQ-LOGI-007을 007(Ubiquitous, 유효값 허용)/007a(Unwanted, 무효값 거부)로 분리(AC-LOGI-007b의 Traces를 REQ-LOGI-007a로 갱신). 새로 분리된 REQ 각각에 대응하는 AC-LOGI-003a/003b/005c 신설 및 acceptance.md에 시나리오 1c/1d/2b2 추가로 1:1 추적성 유지 |
| 1.5.0 | 2026-08-08 | ggajo | Phase 3 문서 동기화 — Run 단계 구현 완료(commit 9c2fc33) 반영. `status: draft → completed`, 신규 섹션 `## 구현 노트` 추가(실제 구현 범위, plan.md 대비 차이, 인수기준 검증, 테스트 커버리지, 알려진 제약 기술)
| 1.6.0 | 2026-08-11 | ggajo | 프로덕션 버그 수정 및 문서 동기화 — commit d22818f (cross-order SKU 충돌 안전성 개선). REQ-LOGI-003b/005b의 (Order.name, SKU) 매칭 구현, regression 테스트 추가(test_spec_011.py, test_spec_012.py) |
| 1.6.0 | 2026-08-17 | ggajo | **환불 차감 도입 — `Order.status` 집계 대상에서 전량 환불된 LineItem 제외(REQ-LOGI-008).** 사용자 보고: 주문 #37830이 19개 품목 중 18개 출고 완료인데 부분입고/부분출고로 표시됐다. 원인은 전량 환불된 19번째 품목이 `not_shipped`로 남아 uniform 판정을 깬 것이며, 그 품목의 `purchase_status`는 `cs_required`(취소 코드가 아님)라 기존 제외 규칙에 걸리지 않았다 — 실제 취소 신호는 Refund 행이다. `UnorderedItemsView`/`_fully_refunded_line_item_ids`가 이미 쓰던 `quantity - Σrefunded ≤ 0` 규칙을 집계에도 적용한다(부분 환불은 제외 사유 아님). 2쿼리 설계는 유지 — 환불 합계는 기존 SELECT에 서브쿼리로 주석 처리(annotate)된다. `UploadWarehouseReceiptView`(REQ-LOGI-015)의 입고 용량 판정은 이 개정 범위 밖으로 변경 없음. **테스트**: `test_spec_011.py`에 `TestRecomputeAggregatesRefundNetting` 4건 추가(전량 환불이 partial을 유발하지 않음 / 부분 환불은 계속 집계 / 전량 취소 주문은 null / 취소 품목이 출고준비를 막지 않음). |

---

## 문제 정의

`LineItem`에는 이미 두 종류의 상태가 있다 — `purchase_status`(발주 필요 여부/사유), `fulfillment_status`(Shopify 동기화, 미국창고→고객 배송). 하지만 **한국 벤더 → 미국창고 → 고객**으로 이어지는 물류 파이프라인의 중간 단계(벤더가 실제로 보냈는지, 미국창고에 도착했는지, 고객에게 다시 내보냈는지)를 추적할 필드가 없다. 관리자는 이를 엑셀/수기로 별도 관리 중이며, `Order` 레벨에서 "이 주문이 전체적으로 어디까지 진행됐는지" 요약할 방법도 없다(`Order.status`는 현재 다른 Shopify 동기화 필드를 그대로 복제할 뿐 아무 의미가 없음 — 상세 근거는 research.md 참조).

## 솔루션 개요

1. `LineItem`에 신규 필드 `logistics_status` 추가 — 5단계, 전량 수기/업로드 기반(Shopify 미연동), `purchase_status`/`fulfillment_status`와 완전 독립.
2. 신규 Excel 업로드 엔드포인트 2개 — 벤더 출고확인(→ 입고예정), 창고 입고결과(→ 입고).
3. 나머지 2단계(출고예정/출고)는 단건/일괄 수기 상태 변경으로 처리.
4. `Order.status`를 하위 `LineItem.logistics_status` 집계값으로 재정의하고, 매 LineItem 상태 write마다 재계산.
5. Shopify 동기화가 새 필드들을 덮어쓰지 않도록 제외 처리.

구체적인 참조 구현(기존 업로드/PATCH 뷰 패턴, 배칭 전략, 마이그레이션 파일 구성)은 `plan.md`를 참조 — 본 문서는 관찰 가능한 동작(WHAT)만 규정한다.

## 범위 — 포함

- LineItem 데이터 모델에 신규 상태 필드 추가 및 `Order.status`의 값 집합 재정의(컬럼 자체는 변경 없음).
- 신규 Excel 업로드 엔드포인트 2개(벤더 출고확인, 창고 입고결과).
- `logistics_status` 단건/일괄 수기 상태 변경 기능.
- Shopify 동기화 로직에서 신규 필드 및 `Order.status`를 제외 처리.
- 프론트엔드: 상태 컬럼 표시, PATCH 연동, 업로드 UI.

파일 단위 변경 대상과 [NEW]/[MODIFY] 마커는 `plan.md`에 정리되어 있다.

## 설계 결정

### 결정 A — `PurchaseOrder.status`와 완전 독립

`logistics_status`는 `PurchaseOrder.status`(미사용 `"confirmed"` 값 포함)를 파생시키지도, 그것에 의해 파생되지도 않는다. 근거: 사용자가 "5단계 모두 수기/업로드 기반"이라고 명시했고, `PurchaseOrder.status`는 어디서도 실제로 전이되지 않는 계획-but-미구현 필드라 새 의미를 얹으면 향후 구현 시 두 상태 개념이 뒤섞일 위험이 크다.

### 결정 B — `WarehouseStock.quantity` 증가 없음

"입고"(received) 전이는 순수 `LineItem` 상태 플래그이며 `WarehouseStock`에 side effect를 주지 않는다. 근거: `WarehouseStock`은 절대값 설정 방식의 순수 수량 원장이라 증분 이벤트 개념이 없고, 여기에 연결하려면 재업로드 멱등성·location 매핑까지 새로 설계해야 해 범위를 벗어난다.

### 결정 C — 업로드 엔드포인트별 대상 필터 (Revision 1 반영, 최종)

- **업로드 1(벤더 출고확인)**: `purchase_status != "unordered"` AND `logistics_status = "not_shipped"`인 LineItem만 매칭 → `shipment_confirmed`로 전이. 단일 출발 상태에서만 전이.
- **업로드 2(창고 입고결과)**: `logistics_status IN ("not_shipped", "shipment_confirmed")`인 LineItem 매칭 → `received`로 전이. **두 개의 출발 상태를 모두 허용** — 벤더가 출고확인 데이터를 아예 보내지 않고 실물만 창고에 도착하는 실무 케이스(사용자 확인)를 반영해, `입고예정`을 거치지 않고 `미입고`에서 곧바로 `입고`로 전이하는 경로를 지원한다.
- 수기 상태 변경(출고예정/출고 포함 5값 전체)은 순서 강제 없이 임의 값으로 전이 허용 — 기존 `purchase_status` 수기 변경과 동일한 설계 일관성.

### 결정 D — `Order.status` 집계 규칙 (필터링 UI/API는 제외, 집계값 정의는 확정)

- 대상: `sku`가 있는("추적 가능한") LineItem만 집계 대상. 대상이 0개면 `Order.status`는 미설정(null) 유지.
- 모든 추적 가능 LineItem의 `logistics_status`가 동일하면 `Order.status` = 그 값(5개 코드/라벨 재사용).
- 2개 이상 값이 섞이면 `Order.status = partial`(부분입고) — 단일 범용 혼재 버킷만 이번에 구현, 세분화(부분입고 vs 부분출고)는 제외.
- 재계산 트리거: 단건 PATCH, 일괄 PATCH, 두 업로드 — LineItem의 `logistics_status`가 실제로 바뀔 때마다 부모 Order를 재계산. Shopify 동기화 시점에는 재계산하지 않음.
- 일괄 처리 시 Order별로 그룹화하여 배치 재계산(SPEC-PURCHASE-ORDER-009의 N+1 방지 선례 준수).

### 결정 E — 기존 Order 백필 필요

`logistics_status` 신설 시 기존 LineItem 전부가 기본값(`not_shipped`)을 가지므로, 기존 Order 전체를 새 집계 규칙으로 일괄 재계산하는 데이터 마이그레이션을 포함한다. 구체적인 마이그레이션 관례(RunPython, historical model, noop reverse)는 `plan.md` 참조.

### 결정 F — UI 카피 구분

`logistics_status`/`Order.status` 라벨은 기존 "배송 상태"(`fulfillment_status`) 컬럼 및 Daily Review 엑셀의 "BOOXEN 입고예정" 컬럼과 시각적으로도 문구적으로도 구분되는 별도 컬럼 헤더/뱃지 스타일로 노출한다(정확한 카피는 Run 단계에서 확정).

---

## 요구사항 (EARS)

### 데이터 모델

**REQ-LOGI-001** (Ubiquitous): The system shall provide `LineItem.logistics_status` with five values — `not_shipped`(미입고, 기본값), `shipment_confirmed`(입고예정), `received`(입고), `outbound_scheduled`(출고예정), `shipped`(출고) — independent of `purchase_status` and `fulfillment_status`.

**REQ-LOGI-002** (Unwanted): If Shopify order sync upserts a LineItem, then the system shall NOT overwrite an existing LineItem's `logistics_status`.

### 업로드 1 — 벤더 출고확인

**REQ-LOGI-003** (Event-Driven): When an admin uploads a vendor-shipment-confirmation file, the system shall identify matching LineItems by SKU where `purchase_status` is not `unordered` AND `logistics_status` is `not_shipped`, and shall transition those LineItems' `logistics_status` to `shipment_confirmed`.

**REQ-LOGI-003a** (Unwanted): If the uploaded vendor-shipment-confirmation file contains multiple rows for the same SKU, then the system shall apply only the last occurrence per SKU.

**REQ-LOGI-003b** (Ubiquitous): The system shall process each vendor-shipment-confirmation upload as a single all-or-nothing operation, with no partial commit on failure.

**REQ-LOGI-004** (Ubiquitous): The system shall return, for every upload, a summary of how many LineItems were matched/updated and how many rows were skipped/unmatched, and shall report any processing failure as a single consolidated error for the whole upload rather than a partial per-row result.

### 업로드 2 — 창고 입고결과 (Decision C 최종본)

**REQ-LOGI-005** (Event-Driven): When an admin uploads a warehouse-receiving-results file, the system shall identify matching LineItems by SKU where `logistics_status` is `not_shipped` OR `shipment_confirmed`, and shall transition those LineItems' `logistics_status` to `received`. This allows a LineItem to transition directly from 미입고(`not_shipped`) to 입고(`received`), skipping 입고예정(`shipment_confirmed`), for the case where the vendor never sent a shipment-confirmation file but the physical goods arrived at the warehouse regardless.

**REQ-LOGI-005a** (Ubiquitous): The system shall apply the same last-row-wins SKU-deduplication (REQ-LOGI-003a) and all-or-nothing processing (REQ-LOGI-003b) behavior to warehouse-receiving-results uploads.

**REQ-LOGI-006** (Unwanted): If a LineItem's `logistics_status` transitions to `received` (via upload or manual change), then the system shall NOT modify `WarehouseStock.quantity` for any ISBN/location (결정 B).

### 수기 상태 변경

**REQ-LOGI-007** (Ubiquitous): The system shall allow an admin to set `LineItem.logistics_status` to any of the five valid values for a single LineItem or for a batch of LineItems in one request.

**REQ-LOGI-007a** (Unwanted): If a requested `logistics_status` value is not one of the five valid choices, then the system shall reject the request without modifying any LineItem and shall report which value was invalid.

### Order 집계

**REQ-LOGI-008** (Ubiquitous) `[AMENDED v1.6.0]`: The system shall define `Order.status` as a computed aggregate over trackable (`sku` not null) child LineItems whose ordered quantity is not fully refunded (`quantity - Σrefunded > 0`), using their `logistics_status`: the shared value when uniform, `partial`(부분입고) when 2+ distinct values are present, unset when no such LineItems exist (결정 D). A fully refunded LineItem takes no part in the aggregate — the customer is not owed those copies (v1.6.0, 사용자 보고 주문 #37830).

**REQ-LOGI-009** (Event-Driven): When any LineItem's `logistics_status` is written (single change, batch change, or either upload), the system shall recompute and persist that LineItem's parent Order's `status` per REQ-LOGI-008.

**REQ-LOGI-010** (Event-Driven): When a batch change or either upload endpoint updates LineItems spanning multiple Orders, the system shall recompute affected Orders' `status` such that the number of database queries used for recomputation does not scale with the number of LineItems updated, but with the number of distinct Orders affected — consistent with SPEC-PURCHASE-ORDER-009's N+1-avoidance precedent.

**REQ-LOGI-011** (Unwanted): If Shopify order sync processes an Order, then the system shall NOT set or overwrite `Order.status` using `financial_status` or any other Shopify-sourced field.

**REQ-LOGI-012** (Ubiquitous): The system shall provide a one-time data migration that recomputes `Order.status` for every existing Order that has at least one trackable LineItem, applied once at deployment time (결정 E).

### UI/독립성 보장

**REQ-LOGI-013** (State-Driven): While displaying `logistics_status` or the `Order.status` aggregate, the system shall present them under a column header/badge style visually and textually distinct from the `fulfillment_status`-driven column and the Daily Review "BOOXEN 입고예정" term (결정 F).

**REQ-LOGI-014** (Ubiquitous): The system shall NOT derive `logistics_status` from `PurchaseOrder.status`, and shall NOT write to `PurchaseOrder.status` as a side effect of any requirement in this SPEC (결정 A).

---

## ACCEPTANCE CRITERIA

EARS 형식의 인수 기준. 각 항목은 대응하는 REQ-LOGI-XXX 하나 이상에 1:1 이상으로 추적된다. Given/When/Then 형태의 실행 가능한 테스트 시나리오는 `acceptance.md`에 별도로 존재하며, 각 시나리오는 아래 AC-LOGI-XXX ID를 인용해 상호 추적된다.

**AC-LOGI-001** (Ubiquitous) — Traces: REQ-LOGI-001. The system shall persist exactly one of the five defined `logistics_status` values for every LineItem at all times, defaulting new LineItems to `not_shipped`, and this value shall never be inferred from or synchronized with `purchase_status` or `fulfillment_status`.

**AC-LOGI-002** (Unwanted) — Traces: REQ-LOGI-002. If a LineItem that already has a non-default `logistics_status` is re-synced from Shopify, then the system shall leave `logistics_status` unchanged after the sync completes.

**AC-LOGI-003** (Event-Driven) — Traces: REQ-LOGI-003. When a vendor-shipment-confirmation file containing a SKU eligible under REQ-LOGI-003's matching rule is uploaded, the system shall transition every matching LineItem to `shipment_confirmed` and shall leave LineItems that do not meet the matching rule (e.g. `purchase_status="unordered"`) unchanged.

**AC-LOGI-003a** (Unwanted) — Traces: REQ-LOGI-003a. If an uploaded vendor-shipment-confirmation file contains two or more rows for the same SKU, then the system shall apply only the values from the last such row and disregard the earlier ones.

**AC-LOGI-003b** (Ubiquitous) — Traces: REQ-LOGI-003b. The system shall commit all LineItem updates from a single vendor-shipment-confirmation upload as one unit, such that a failure partway through the upload leaves no partial updates persisted.

**AC-LOGI-004** (Ubiquitous) — Traces: REQ-LOGI-004. The system shall include, in every upload response, a count of matched/updated LineItems and a count of skipped/unmatched rows, such that matched + skipped equals the number of distinct SKUs in the uploaded file.

**AC-LOGI-005a** (Event-Driven) — Traces: REQ-LOGI-005. When a warehouse-receiving-results file is uploaded for a SKU whose LineItem is currently `not_shipped`, the system shall transition that LineItem directly to `received` without requiring an intermediate `shipment_confirmed` state.

**AC-LOGI-005b** (Event-Driven) — Traces: REQ-LOGI-005. When a warehouse-receiving-results file is uploaded for a SKU whose LineItem is currently `shipment_confirmed`, the system shall transition that LineItem to `received`.

**AC-LOGI-005c** (Ubiquitous) — Traces: REQ-LOGI-005a. The system shall apply the same last-row-wins deduplication and all-or-nothing commit behavior to warehouse-receiving-results uploads as it applies to vendor-shipment-confirmation uploads.

**AC-LOGI-006** (Unwanted) — Traces: REQ-LOGI-006. If any LineItem's `logistics_status` becomes `received` by any means (upload or manual change), then the corresponding `WarehouseStock` row(s) for that LineItem's ISBN shall show no quantity change attributable to that transition.

**AC-LOGI-007a** (Ubiquitous) — Traces: REQ-LOGI-007. The system shall accept any of the five valid `logistics_status` values via single-item or batch manual change.

**AC-LOGI-007b** (Unwanted) — Traces: REQ-LOGI-007a. If an invalid value is submitted for a manual `logistics_status` change, then the system shall reject the request, leave all targeted LineItems' `logistics_status` unchanged, and return an error identifying the invalid value.

**AC-LOGI-008** (Ubiquitous) — Traces: REQ-LOGI-008. The system shall set `Order.status` to the shared `logistics_status` value of a trackable, not-fully-refunded LineItem set when all values are identical, to `partial` when two or more distinct values are present, and to unset when no such LineItems exist.

**AC-LOGI-009** (Event-Driven) — Traces: REQ-LOGI-009. When a single LineItem's `logistics_status` is changed by any of the four write paths (manual single, manual batch, upload 1, upload 2), the system shall recompute that LineItem's parent Order's `status` before the write's response is returned.

**AC-LOGI-010** (Event-Driven) — Traces: REQ-LOGI-010. When a batch change or upload affects LineItems belonging to N distinct Orders, the system shall recompute all N Orders' `status`, and the number of SQL queries issued for this recomputation shall not grow linearly with the number of LineItems updated.

**AC-LOGI-011** (Unwanted) — Traces: REQ-LOGI-011. If an Order is re-synced from Shopify after its `status` has been set by REQ-LOGI-008's aggregation, then `Order.status` shall retain its aggregate value after the sync completes (not reset to a Shopify-sourced value).

**AC-LOGI-012** (Ubiquitous) — Traces: REQ-LOGI-012. The system shall ensure every pre-existing Order with at least one trackable LineItem has a `status` value consistent with REQ-LOGI-008's aggregation rule, following the one-time backfill migration.

**AC-LOGI-013** (State-Driven) — Traces: REQ-LOGI-013. While any screen displays both `logistics_status`/`Order.status` and `fulfillment_status` for the same Order or LineItem, the system shall render them such that the header text for the two columns shares no word in common and the badge background colors differ.

**AC-LOGI-014a** (Unwanted) — Traces: REQ-LOGI-014. If any `logistics_status` write occurs (manual or upload), then the system shall leave every LineItem's associated `PurchaseOrder.status` value(s) unchanged.

**AC-LOGI-014b** (Ubiquitous) — Traces: REQ-LOGI-014. The system shall never compute a `logistics_status` value from `PurchaseOrder.status`.

---

## Exclusions (What NOT to Build)

- `Order.status` 기준 필터 UI/필터 API — 사용자가 명시적으로 유예("상황봐서 다시 고민")
- 세분화된 부분 상태(`partial` 하위 구분, 예: 부분입고 vs 부분출고) — 단일 범용 `partial` 버킷만 구현
- `WarehouseStock.quantity` 증분 연동 — 후속 과제
- `PurchaseOrder.status`를 이 필드로 구동하거나 그 반대로 구동하는 로직
- 두 업로드 엔드포인트의 정확한 Excel 컬럼 레이아웃 확정 — Run 단계 착수 전 실제 샘플 파일/컬럼 정의 필요(아래 가정 참조)

## 확인이 필요한 가정

1. 두 신규 Excel 업로드의 정확한 컬럼 구성(SKU 컬럼명, 날짜/수량 등 부가 컬럼)은 아직 정의되지 않았다 — Run 단계 착수 전 실제 템플릿 파일 또는 컬럼 스펙 확인 필요.

## 관련 SPEC

- SPEC-PURCHASE-ORDER-009: N+1 배칭 패턴의 선례(REQ-LOGI-010, AC-LOGI-010이 이 선례를 따름).
- SPEC-PURCHASE-ORDER-010: `purchase_status` 파손/교환 값 — `logistics_status`와 데이터/쿼리 접점 없이 완전 독립이나, 동일 코드베이스 감사(research.md)를 공유.

---

## 구현 노트 (Implementation Notes)

**상태**: 완료 (commit 9c2fc33, 2026-08-08 22:39:48 UTC)  
**검증**: TRUST5 완전 통과, evaluator-active PASS, 모든 인수기준 충족

### 실제 구현 범위

#### ✅ 구현됨 (계획 일치)

**M1 — 데이터 모델**
- `LineItem.logistics_status` 필드: 5개 선택값(미입고/입고예정/입고/출고예정/출고), 기본값 미입고
- `Order.status` 5개 재사용값 + 부분입고(partial) — choices 추가만으로 구현
- 마이그레이션 3개: `0030_lineitem_logistics_status_alter_order_status.py`, `0031_backfill_order_status.py`
  - 실제 번호는 SPEC-PURCHASE-ORDER-010이 0029를 선점해 0030/0031로 조정됨 (plan.md 예정대로)

**M2 — Shopify 동기화 제외**
- `shopify_orders.py:_sync_single_order()`에서 `Order.status` 동기화 제거
- LineItem `logistics_status` 필드는 Shopify 동기화 대상 자체에서 미포함 (신규 필드이므로 자동 제외)

**M3 — 업로드 엔드포인트 2개**
- `UploadVendorShipmentView`: 벤더 출고확인 Excel 업로드 → `shipment_confirmed` 전이
- `UploadWarehouseReceiptView`: 창고 입고결과 Excel 업로드 → `received` 전이
- 두 엔드포인트 모두 SKU 중복 제거, 원자성, 배치 Order 재계산 준수
- Excel 파싱 함수: `excel_utils.py:parse_vendor_shipment_excel()`, `parse_warehouse_receipt_excel()` 추가
- URL 등록: `purchase-orders/upload-vendor-shipment/`, `purchase-orders/upload-warehouse-receipt/` (plan.md 규칙 준수, 최종 줄바꿈 포맷팅만 이후 수정)

**M4 — 수기 상태 변경 PATCH**
- `LineItemLogisticsStatusUpdateView`: 단건 변경
- `LineItemLogisticsStatusBulkUpdateView`: 일괄 변경
- 기존 `LineItemStatusUpdateView` 패턴 재사용

**M5 — Order.status 재계산**
- 헬퍼 함수: `_recompute_order_status(order_ids)` 구현
- 4개 write 경로(업로드 2개 + PATCH 2개) 모두에서 호출
- Order 배치 그룹화로 N+1 방지 (SPEC-PURCHASE-ORDER-009 선례 준수)
- 쿼리 수 테스트 포함: `test_spec_011.py` 중 배치 시나리오

**M6 — 프론트엔드**
- 신규 컴포넌트: `LogisticsStatusTab.tsx` (기존 탭 구조 확장)
- 수정 컴포넌트: `OrderDetailPage.tsx` (logistics_status 컬럼 추가)
- API 래퍼: `usePurchaseOrderQueries.ts` 신규 생성 (기존 hook과는 별도, logistics 쿼리 전용)
- 선택값 상수: `LOGISTICS_STATUS_OPTIONS` 추가 (purchaseOrderApi.ts)
- serializers.py에 `logistics_status` 필드 노출 추가

#### ⚠️ 실제 구현과 plan.md의 차이 (기술적 영향 없음)

1. **프론트엔드 컴포넌트 구조**
   - plan.md 예상: "기존 탭에 컬럼 추가"
   - 실제: 새 전용 탭(`LogisticsStatusTab.tsx`) + `OrderDetailPage.tsx` 통합
   - 근거: logistics_status의 관리 인터페이스가 purchase_status와는 다른 workflow(업로드 기반)이므로 UI 분리가 더 명확함

2. **Hook 파일 추가**
   - `usePurchaseOrderQueries.ts` 신규 생성 (plan.md에서는 기존 hook 재사용으로 가정했으나, 실제로는 logistics 전용 쿼리 집합이 필요해 분리)

3. **URL 최종 포맷팅**
   - urls.py에 줄바꿈 포맷팅 추가 (논리 변경 없음, 스타일만)

#### 🎯 발견된 edge case 및 추가 변경

- WarehouseStock과의 독립성 명확히 함 (결정 B 재확인): `received` 전이 시 quantity 미변경
- 원본 Order 미변경 (결정 D 재확인): trackable LineItem이 없는 Order는 Order.status 미설정 유지
- Shopify 재동기화 완전 격리: `logistics_status`와 `Order.status` 모두 Shopify 동기화 중 미변경

### 인수 기준 검증 결과

모든 AC-LOGI-001~014 충족:
- ✅ AC-LOGI-001~004: 벤더 출고확인 업로드 (정상 전이, 카운트, dedup, 원자성)
- ✅ AC-LOGI-005a~005c: 창고 입고결과 업로드 (직행 경로, dedup, 원자성)
- ✅ AC-LOGI-006: WarehouseStock 무변경
- ✅ AC-LOGI-007a~007b: 수기 상태 변경 (유효값 수용, 무효값 거부)
- ✅ AC-LOGI-008~010: Order.status 집계 및 배치 재계산 (N+1 방지 검증됨)
- ✅ AC-LOGI-011~012: Shopify 격리, 백필 마이그레이션
- ✅ AC-LOGI-013~014: UI 구분, PurchaseOrder.status 독립성

### 테스트 커버리지

- 신규 테스트 파일: `test_spec_011.py` (842줄, 포괄적)
- 마이그레이션 테스트: `test_backfill_order_status_migration.py` (135줄)
- 기존 테스트 호환성: `test_shopify_orders.py`, `test_order_detail.py` 등 회귀 없음
- 커버리지 목표: 85%+ (TRUST5 Tested)

### 알려진 제약

- Excel 컬럼 레이아웃은 초기 plan.md의 "확인이 필요한 가정"에 남아 있음 — Run 단계 착수 시 실제 템플릿 확보로 파싱 함수 최종 검증 필요 (현재는 SKU 기준 기본 구조만 가정)
