---
id: SPEC-ORDER-012
version: 1.3.0
status: draft
created: 2026-08-09
created_at: 2026-08-09
updated: 2026-08-09
author: ggajo
priority: High
issue_number: 10
labels: [order, logistics, purchase-order, ready-to-ship]
---

# Order 출고 가능 여부(ready_to_ship) 판정

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-09 | ggajo | 최초 작성 — Phase 1B 계획안(필드 타입 3상태, `_recompute_order_status`→`_recompute_order_aggregates` 리네임, 마이그레이션 reverse `noop` 유지) 사용자 승인 반영한 최초 승인본. EARS 요구사항은 SPEC-ORDER-011의 REQ-LOGI-008/009/010 단일-정의/단일-트리거 선례를 따라 초안 단계에서부터 세분화 |
| 1.1.0 | 2026-08-09 | ggajo | Phase 2.3 plan-auditor 리뷰(iteration 1, FAIL — MP-1/MP-2 위반 2건 + minor 3건) 반영. MP-1: `REQ-RTS-003a`가 기본 번호 계열을 깬다는 지적에 대해, 기본 계열(001~008)에 결번·중복이 없고 알파벳 접미사는 SPEC-ORDER-011(`REQ-LOGI-003/003a/003b` 등)·SPEC-PURCHASE-ORDER-010(`REQ-DMG-005/005B`)에서 이미 확립된 프로젝트 전역 관례임을 REQUIREMENTS/ACCEPTANCE CRITERIA 양 섹션 상단에 "번호 규칙 참고" 설명으로 명문화(단순 선례 인용이 아니라 왜 분리가 단일-트리거 원칙상 옳은지 근거 추가) — 순차 재번호 대신 관례 문서화로 해결. MP-2: `AC-RTS-002a/002b/002c`를 "For an Order with..." 위장 조건문(Ubiquitous 오표기)에서 감사 보고서 권고안 그대로 순수 State-Driven("While...")으로 재작성. Minor 처리: `priority: High` 대문자 표기는 SPEC-PURCHASE-ORDER-010 v1.2.0 HISTORY가 이미 프로젝트 전역 관례로 명시적으로 확정한 사안이라 변경하지 않음(재검토 후 유지 결정). `REQ-RTS-007`에 "헤더 텍스트 단어 미공유 + 배경색 상이"라는 구체적 판정 메커니즘을 REQ 본문에 직접 명시(REQ-LOGI-013 최종 수정 패턴 재사용). `REQ-RTS-004`/`AC-RTS-004`를 완전성 진술(004)과 쿼리 비선형성 비기능 제약(004a)으로 분리 |
| 1.2.0 | 2026-08-09 | ggajo | Phase 2.3 plan-auditor 리뷰(iteration 2, PASS — 비차단 minor 4건). 사용자 승인 하에 오케스트레이터가 직접 마무리: AC-RTS-002a/b/c와 003a/004a의 접미사 분리 기준이 서로 다름(전자는 단일 REQ를 상태별로 나눈 것, 후자는 REQ 자체가 트리거별로 나뉜 것)을 명확히 구분해 "번호 규칙 참고" 재작성, AC-RTS-005의 Unwanted 절 주어를 필드명에서 "the system"으로 교정, AC-RTS-006을 "following the backfill migration"이라는 위장 트리거를 가진 Ubiquitous에서 순수 Event-Driven("When the ... migration is applied")으로 재작성, acceptance.md의 낡은 "AC-RTS-001~008"/"REQ-RTS-001~008" 범위 표기를 실제 12개 ID 전체 나열로 정정 |
| 1.3.0 | 2026-08-09 | ggajo | Phase 2.3 plan-auditor 검증 재감사(iteration 3/3, FAIL — 4건의 minor 결함, 감사관 자체 평가로도 "설계 문제 아닌 기계적 한 줄 수정") 반영. 사용자 승인 하에 오케스트레이터가 직접 마무리: AC-RTS-004a의 Event-Driven 절 주어를 "the number of SQL queries"(비-system 주어)에서 "the system shall ensure the number of..."로 교정(형제 REQ-RTS-004a는 이미 올바른 형태였음), AC-RTS-001의 둘째 절도 동일한 주어 문제를 "the system shall never infer or synchronize..."로 교정, acceptance.md Definition of Done의 REQ-RTS 범위 표기를 압축형에서 전체 ID 나열로 정정 |

---

## 문제 정의

`Order.status`(SPEC-ORDER-011)는 물류 파이프라인이 어디까지 왔는지(미입고/입고예정/입고/출고예정/출고/
부분입고)를 보여주지만, "지금 이 주문을 고객에게 출고해도 되는가"라는 별도의 운영 질문에는 답하지
못한다. 예를 들어 `status="received"`이면서 동시에 CS 처리 대기(`purchase_status="cs_required"`) 중인
LineItem이 섞여 있으면 물류 단계상으로는 "입고"이지만 실제로는 출고 불가능하다. 반대로 창고 재고를
사용한(`purchase_status="in_stock"`) LineItem은 `logistics_status`가 `received`로 전이된 적이 없어도
이미 출고 가능한 상태다. 두 판단축이 서로 독립적이므로 새 필드로 분리한다.

## 솔루션 개요

1. `Order`에 신규 필드 `ready_to_ship` 추가 — True/False/null(미설정) 3상태, `Order.status`와
   완전히 독립.
2. 추적 가능(`sku not null`) 자식 LineItem 집합에 대한 계산된 집계값으로 정의(수동 설정 불가,
   계산 전용).
3. 기존 `_recompute_order_status()`를 `_recompute_order_aggregates()`로 확장/리네임해 같은 SELECT
   결과에서 `Order.status`와 `ready_to_ship`을 함께 계산 — 추가 쿼리 없음.
4. 기존 4개 `logistics_status` write path(이미 재계산 호출 중)는 함수명만 교체되고, 지금까지
   Order 재계산을 전혀 트리거하지 않던 4개 `purchase_status` write path에도 동일한 재계산 호출을
   신규 연결(SPEC-ORDER-011/SPEC-PURCHASE-ORDER-010 양쪽의 기존 write path를 건드리는 의도된
   cross-cutting 변경).
5. Shopify 동기화가 새 필드를 덮어쓰지 않도록 문서화(코드 변경은 최소 — 원래도 대상이 아니었음).
6. 프론트엔드: Order 상세 화면에 세 번째 뱃지("출고가능") 추가.

구체적인 참조 구현(함수명, 파일:라인, 마이그레이션 파일 구성)은 `plan.md`를 참조 — 본 문서는
관찰 가능한 동작(WHAT)만 규정한다.

## 범위 — 포함

- `Order` 모델에 신규 계산 필드 추가(컬럼 자체는 새로 생성 — SPEC-ORDER-011의 `status`처럼 기존
  컬럼 재정의가 아님).
- 기존 Order 재계산 헬퍼 함수 확장 및 리네임.
- 8개 write path(기존 4개 + 신규 4개) 전체에 재계산 연결.
- Shopify 동기화 제외 문서화 및 회귀 테스트.
- 기존 Order 전체에 대한 1회성 백필 마이그레이션.
- 프론트엔드: Order 상세 화면 뱃지 1개 추가.

파일 단위 변경 대상과 [NEW]/[MODIFY] 마커는 `plan.md`에 정리되어 있다.

## 설계 결정

### 결정 A — 필드 타입: 3상태 nullable Boolean (사용자 승인)

`Order.ready_to_ship`은 `BooleanField(null=True, blank=True)`로 True/False/None 3상태를 표현한다.
같은 `Order` 모델에 두 가지 boolean 선례가 공존한다 — `note_resolved`(non-null, 수동 토글)와
`status`(같은 LineItem 집합에서 계산되는 aggregate, "대상 0개면 null"). `ready_to_ship`은 후자와
같은 카테고리(계산된 aggregate)이므로 `status`의 null 선례를 채택한다.

### 결정 B — 재계산 헬퍼 함수 확장 및 리네임 (사용자 승인, cross-SPEC 수정)

`_recompute_order_status()`(`purchase_order_views.py:117-158`)는 이미 단일 SELECT(그룹핑) + 단일
`Case/When` UPDATE 구조다. `ready_to_ship` 계산에는 같은 LineItem 집합의 `purchase_status`만 추가로
필요하므로, SELECT에 컬럼 하나를 추가하고 UPDATE에 절 하나를 추가하는 것으로 **쿼리 수 증가 없이**
확장한다. 함수가 이제 `Order.status`와 `Order.ready_to_ship` 둘 다 계산하므로
`_recompute_order_aggregates()`로 리네임한다 — 순수 기계적 리네임(동작 변경 없음)이지만
SPEC-ORDER-011이 만든 기존 코드(호출부 4곳 + docstring + `@MX:NOTE` 주석)를 건드리는 cross-SPEC
수정임을 명시한다.

### 결정 C — 8개 write path 전체 연결, "요청당 1회" N+1 방지 원칙

기존 4개(`logistics_status` 전용)에 신규 4개(`ConfirmOrderView`, 단건/일괄 `purchase_status` PATCH,
Daily Review 업로드의 3개 분기)를 추가한다. 신규 4개 중 `ConfirmOrderView`와 Daily Review 업로드는
한 요청 안에서 여러 SKU/여러 분기를 처리하므로, 재계산 호출은 **루프/분기 종료 후 요청당 1회만**
수행해 SKU 개수와 무관하게 O(1) 추가 쿼리쌍을 유지한다(SPEC-PURCHASE-ORDER-009 N+1 방지 선례,
REQ-LOGI-010 확장).

### 결정 D — 마이그레이션: `AddField` + `RunPython` 백필, `noop` reverse (사용자 승인)

`0030`/`0031` 분리 관례를 따라 스키마 변경(`AddField`)과 데이터 백필(`RunPython`)을 별도
마이그레이션으로 분리한다. 백필의 `reverse_code`는 `noop`으로 유지한다 — 이 필드는 신규라 이론상
"전부 NULL로 되돌리기"가 가능하지만, 프로젝트 전체의 `0026`/`0031` 관례 일관성을 우선한다.

### 결정 E — 계산 전용 필드, 수동 PATCH 엔드포인트 없음

`logistics_status`/`purchase_status`와 달리 `ready_to_ship`은 항상 재계산으로만 값이 정해지며,
별도 PATCH 엔드포인트를 두지 않는다. `OrderDetailView`가 `RetrieveAPIView`(GET 전용)임을 확인했으므로
우발적 쓰기 경로도 없다.

---

## 요구사항 (EARS)

**번호 규칙 참고**: 기본 번호 계열(REQ-RTS-001~008)에는 결번·중복이 없다. `REQ-RTS-003a`/
`REQ-RTS-004a`처럼 알파벳 접미사가 붙은 ID는 EARS의 단일 트리거·단일 응답 원칙에 따라 기본 항목에서
파생된, 서로 다른 트리거(또는 서로 다른 성격의 규범 진술)를 분리 표현하기 위한 것이다 — 이미
프로젝트 전역에서 확립된 관례다(SPEC-ORDER-011의 `REQ-LOGI-003/003a/003b`, `REQ-LOGI-005/005a`,
`REQ-LOGI-007/007a`; SPEC-PURCHASE-ORDER-010의 `REQ-DMG-005/005B`). `REQ-RTS-003`(기존 4개
`logistics_status` write path — 이미 재계산을 트리거하던 경로)과 `REQ-RTS-003a`(신규 4개
`purchase_status` write path — 지금까지 트리거하지 않던 경로)는 대상 필드와 write path 집합이 서로
다른 별개의 트리거이므로, 하나의 요구사항으로 합치면 오히려 단일-트리거 원칙을 위반한다.
`REQ-RTS-004`(N개 Order 재계산의 완전성)와 `REQ-RTS-004a`(쿼리 수 비선형성이라는 별도의 비기능
제약)도 같은 이유로 분리한다.

### 데이터 모델

**REQ-RTS-001** (Ubiquitous): The system shall provide `Order.ready_to_ship` as a field fully
independent of `Order.status`, capable of representing three states — ready (`True`), not ready
(`False`), and not applicable (`null`).

**REQ-RTS-002** (Ubiquitous): The system shall define `Order.ready_to_ship` as a computed
aggregate over the Order's trackable (`sku` not null) child LineItems, applying the following
rules in order: a LineItem whose `purchase_status` is `order_cancelled` shall be excluded from
consideration entirely; if zero non-excluded trackable LineItems remain, `ready_to_ship` shall be
`null`; otherwise, if one or more non-excluded LineItems has `purchase_status="cs_required"`,
`ready_to_ship` shall be `False`; otherwise, `ready_to_ship` shall be `True` if and only if every
non-excluded LineItem satisfies `logistics_status="received"` OR `purchase_status="in_stock"`,
and `False` otherwise.

### 재계산 연결

**REQ-RTS-003** (Event-Driven): When any LineItem's `logistics_status` is written by any of the
existing write paths that already trigger Order-level `status` recomputation, the system shall
recompute `ready_to_ship` per REQ-RTS-002 in the same recomputation pass.

**REQ-RTS-003a** (Event-Driven): When any LineItem's `purchase_status` is written by any existing
write path — including write paths that today trigger no Order-level recomputation at all — the
system shall trigger the same Order-level recomputation described in REQ-RTS-003, computing both
`Order.status` and `ready_to_ship` together.

**REQ-RTS-004** (Event-Driven): When a single request's write (triggered by REQ-RTS-003 or
REQ-RTS-003a) affects LineItems belonging to N distinct Orders, the system shall recompute all N
Orders' `ready_to_ship` together with `status` as part of that request's Order-level
recomputation.

**REQ-RTS-004a** (Event-Driven): When the recomputation described in REQ-RTS-004 executes, the
system shall ensure the number of additional database queries used does not scale with the number
of LineItems changed, but with the number of distinct Orders affected.

**REQ-RTS-005** (Unwanted): If Shopify order sync processes an Order or its LineItems, then the
system shall NOT set or overwrite `Order.ready_to_ship` from any Shopify-sourced field.

### 마이그레이션

**REQ-RTS-006** (Ubiquitous): The system shall provide a one-time data migration that computes
`Order.ready_to_ship` for every existing Order per REQ-RTS-002, applied once at deployment time.

### UI

**REQ-RTS-007** (State-Driven): While displaying `Order.ready_to_ship` alongside `Order.status`
and `fulfillment_status` on the Order detail screen, the system shall render `ready_to_ship` under
a badge whose header text shares no word with either of the other two badges' header text and
whose background color (or design token) differs from both.

**REQ-RTS-008** (State-Driven): While `Order.ready_to_ship` is `null`, the system shall NOT render
the ready-to-ship badge.

---

## ACCEPTANCE CRITERIA

EARS 형식의 인수 기준. 각 항목은 대응하는 REQ-RTS-XXX 하나 이상에 1:1 이상으로 추적된다.
Given/When/Then 형태의 실행 가능한 테스트 시나리오는 `acceptance.md`에 별도로 존재하며, 각 시나리오는
아래 AC-RTS-XXX ID를 인용해 상호 추적된다.

**번호 규칙 참고**: AC-RTS 접미사는 REQ-RTS 접미사와 문자를 공유하지만 분리 기준은 다르다.
`003a`/`004a`는 REQ-RTS-003a/004a와 동일하게 "다른 트리거(이벤트) 경로"를 나타내는 분리다
(REQUIREMENTS 섹션의 "번호 규칙 참고" 참조). 반면 `002a`/`002b`/`002c`는 REQ-RTS-002라는
단일 Ubiquitous 규칙을 세 가지 상태(0건/cs_required 존재/나머지) 각각에 대한 State-Driven
인수 기준으로 나눈 것으로, 대응하는 REQ 쪽에는 별도 접미사가 없다(REQ-RTS-002 하나가 세
AC 모두의 근거).

**AC-RTS-001** (Ubiquitous) — Traces: REQ-RTS-001. The system shall persist `Order.ready_to_ship`
as one of exactly three values (`True`/`False`/`null`) at all times, and the system shall never
infer or synchronize this value from `Order.status`.

**AC-RTS-002a** (State-Driven) — Traces: REQ-RTS-002. While an Order has zero non-excluded
trackable LineItems (either zero trackable LineItems at all, or every trackable LineItem has
`purchase_status="order_cancelled"`), the system shall set `ready_to_ship` to `null`.

**AC-RTS-002b** (State-Driven) — Traces: REQ-RTS-002. While an Order has at least one non-excluded
trackable LineItem with `purchase_status="cs_required"`, the system shall set `ready_to_ship` to
`False`, regardless of any other LineItem's `logistics_status` or `purchase_status`.

**AC-RTS-002c** (State-Driven) — Traces: REQ-RTS-002. While an Order has at least one non-excluded
trackable LineItem and none of them is `cs_required`, the system shall set `ready_to_ship` to
`True` if and only if every non-excluded LineItem satisfies `logistics_status="received"` OR
`purchase_status="in_stock"`, and to `False` otherwise.

**AC-RTS-003** (Event-Driven) — Traces: REQ-RTS-003. When any of the four existing
`logistics_status` write paths (two uploads, single/bulk PATCH) writes a LineItem's
`logistics_status`, the system shall recompute that LineItem's parent Order's `ready_to_ship`
before the write's response is returned.

**AC-RTS-003a** (Event-Driven) — Traces: REQ-RTS-003a. When the order-confirmation flow, the
single/bulk `purchase_status` PATCH endpoints, or any branch of the Daily Review upload writes a
LineItem's `purchase_status`, the system shall recompute that LineItem's parent Order's
`ready_to_ship` before the write's response is returned, even though these write paths did not
previously trigger any Order-level recomputation.

**AC-RTS-004** (Event-Driven) — Traces: REQ-RTS-004. When a single request's write affects
LineItems belonging to N distinct Orders, the system shall recompute all N Orders' `ready_to_ship`
together with `status`.

**AC-RTS-004a** (Event-Driven) — Traces: REQ-RTS-004a. When the recomputation in AC-RTS-004
executes, the system shall ensure the number of SQL queries issued for that recomputation does not
grow linearly with the number of LineItems updated, regardless of N.

**AC-RTS-005** (Unwanted) — Traces: REQ-RTS-005. If an Order or its LineItems are re-synced from
Shopify after `ready_to_ship` has been set by REQ-RTS-002's computation, then the system shall
leave `ready_to_ship` unchanged after the sync completes.

**AC-RTS-006** (Event-Driven) — Traces: REQ-RTS-006. When the one-time backfill migration is
applied, the system shall ensure every pre-existing Order has a `ready_to_ship` value consistent
with REQ-RTS-002's rules.

**AC-RTS-007** (State-Driven) — Traces: REQ-RTS-007. While the Order detail screen displays
`ready_to_ship`, `status`, and `fulfillment_status` badges together, the system shall render them
such that no two badges' header text shares a word in common and no two badges share the same
background color.

**AC-RTS-008** (State-Driven) — Traces: REQ-RTS-008. While `Order.ready_to_ship` is `null`, the
system shall omit the ready-to-ship badge from the rendered Order detail screen.

---

## Exclusions (What NOT to Build)

- `ready_to_ship` 기준 목록/필터 UI 또는 필터 API — SPEC-ORDER-011의 `Order.status` 필터링 유예와
  동일하게 명시적으로 제외, 별도 후속 SPEC 가능성으로 남겨둠.
- `ready_to_ship`을 수동으로 설정/override하는 PATCH 엔드포인트 — 항상 계산 전용 필드(결정 E).
- `WarehouseStock.quantity` 관련 변경 — `purchase_status="in_stock"`을 그대로 신뢰하며 실제 재고
  수량을 재검증하지 않음.
- `PurchaseOrder.status`와의 연동 — SPEC-ORDER-011 결정 A(완전 독립)를 그대로 유지.
- `ready_to_ship=True` 전이 시 알림/이메일 등 부수 효과.

## 관련 SPEC

- SPEC-ORDER-011: `Order.status` 집계 및 `_recompute_order_status()`(리네임 대상), 기존 4개
  `logistics_status` write path의 직접적인 선행 SPEC.
- SPEC-PURCHASE-ORDER-010: `damaged_exchange`/`cs_required` 등 `purchase_status` 값 체계의
  선행 SPEC. 이 SPEC이 처음으로 그 write path들에 Order 레벨 재계산을 연결한다(의도된 cross-cutting
  확장, 사용자 승인 완료).
