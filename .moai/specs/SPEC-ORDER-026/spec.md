---
id: SPEC-ORDER-026
version: 1.2.0
status: draft
created_at: 2026-08-17
updated: 2026-08-18
author: ggajo
priority: High
issue_number: 0
labels: [order, cost, margin, refund, netting, backend]
---

# 주문 원가·마진 계산의 환불 순액화 — 수량과 매출 양쪽

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-17 | ggajo | 최초 작성. 프로덕션 결함(확정) 정정 SPEC. `_compute_cost_breakdown_for_rate`(`backend/order/serializers.py:31-73`)가 7개 비용 필드 전부를 원시 `item.quantity`와 gross `obj.total_price`로 계산해, `Refund` 행이 있는 주문 **96건**(2026-08-17 스냅샷, 구현 시점 재실측 권고)의 마진을 과대 계상하고 있다. 이 코드베이스는 8곳 이상에서 환불 순액화 관례를 적용하며(`purchase_order_views.py:332-342,366-370`, `serializers.py:179-191` 등) 비용 경로만 이 관례를 건너뛴다 — 설계 선택이 아니라 결함이다. 사용자 확정 결정 3건(양쪽 순액화 / 매출 항은 프론트엔드 공식과 동일 / `purchase_status="order_cancelled"`는 범위 밖)을 반영해 EARS 5개 모듈로 formalize. **모든 `file:line` 인용은 이 세션에서 직접 재확인했다**(`research.md` §13) — 선행 SPEC 인용 중 파일 변경으로 어긋난 4건을 발견해 정정했다(`research.md` §7). |
| 1.1.0 | 2026-08-17 | ggajo | plan-auditor 1차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-026-review-1.md`, iteration 1, **FAIL, 0.72**) 반영. 감사가 무변경으로 확인한 것: 인용 약 48건 전수 대조에서 **어긋난 인용 0건**, 산술 약 90개 값 중 1개 행만 불일치, fan_in=2 임계 미달의 정직한 기록, AC-NET-003/007의 무판별 자진 공개. **차단 결함 4건 해소**: **D2(critical)** — REQ-NET-002의 "합산" 축(`spec.md` 가정 A3)을 15개 AC가 하나도 고정하지 못해 `refunded_qty[id] = (refund.quantity or 0)`(누적 대신 **덮어쓰기**) 변이가 전부 통과했다. 같은 `shopify_line_item_id`에 환불 2행을 붙인 **AC-NET-015** 신설 + 변이 **M10** 등록으로 해소(감사가 제시한 기대 `margin_amount="66.02"`는 재검산 결과 오류 — 66.025는 ROUND_HALF_UP으로 **`"66.03"`**이다). **D1(critical)** — `acceptance.md` AC-NET-009의 "메모이제이션 우회 변이가 `orders_refund` 쿼리를 7까지 늘린다"는 판별력 주장이 **거짓**이었다(순액화는 prefetch 캐시를 읽으므로 반복해도 쿼리 1건이고, `_get_exchange_rate`는 `serializers.py:466-498`에서 **독립 메모이즈**되어 있어 환율 쿼리도 1건 그대로다 — 이 세션에서 해당 코드를 직접 읽어 확인했다). SPEC-ORDER-021 시절 유효했던 주장을 검증 없이 승계한 것이다. 거짓 주장을 삭제하고, 메모이제이션 호출 횟수를 직접 관측하는 **AC-NET-016** 신설 + 변이 **M11** 등록 + 추적표의 REQ-NET-033 매핑을 AC-NET-009 → AC-NET-016으로 정정해 해소. **D3(major)** — `plan.md` M1의 RED 완료 조건이 "13개 실패"였으나 실제로는 11개(현 17개 기준 12개)이며, AC-NET-009/010은 불변식 보존 AC이므로 무수정 코드에서 **통과하는 것이 정상**이다. 문자대로 따르는 구현자가 정상 통과 중인 MUST-PASS 성능 AC 2개의 픽스처를 "고장난 것"으로 고쳐 R3(주문당 +50 쿼리)의 유일한 방어선을 훼손할 수 있었다. **D9/MP-3(major)** — frontmatter에 `created_at`/`labels` 누락 + `priority` 대소문자 불일치를 형제 SPEC(`SPEC-ORDER-025/spec.md:1-10`) 기준으로 정정. **부수 결함 8건 해소**: D4(AC-NET-002의 M8 행이 M1 값 복사 — 매출 측은 조인 키를 쓰지 않으므로 실제 M8은 M3와 동일한 `"39.58"`/`"49.47"`), D5(AC-NET-003 판별 변이 표기 3곳 자기모순 — 본문이 옳으므로 헤더/요약표를 M2로 통일), D6("6개 변이" → 11개), D7(`DETAIL_SERIALIZER_FIELDS` "41개" → **45개**, 프로그램 카운트로 확정, 5개 문서 정정), D8(AC-NET-014의 T1 인용 과장 — T1은 4개만 단정하고 `confirmed_cost`는 T14 `test_spec_021.py:395`가, `total_cost`/`margin_rate`는 어디서도 단정하지 않는다), D10(EARS 패턴 라벨 3건: REQ-NET-004 Unwanted→Ubiquitous, REQ-NET-023/040 Ubiquitous→State-Driven), D11(REQ-NET-031이 8로 결정한 값을 AC-NET-009(a)가 구현자 재량으로 되돌리던 구조 — 결정 쪽으로 일원화), D12(커버리지 공백 4건 — 목록 경로 매출 0 게이트를 AC-NET-004(b)로, `quantity IS NULL`+환불을 AC-NET-006a(b)로, `total_price IS NULL`+환불을 AC-NET-006b(b)로 파라미터화, REQ-NET-043의 `0.01` 상한을 AC-NET-005에서 잔차 정확 일치로 검증). D13은 감사 권고대로 **UNVERIFIED 표시를 유지**하고 스냅샷 일자를 병기했다. REQ 25개(무변경, 라벨 3건·문구 2건만 교정) + AC 15개 → **17개**(AC-NET-015/016 신설, 기존 번호 무변경). |
| 1.2.0 | 2026-08-18 | ggajo | plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-026-review-2.md`, iteration 2, **FAIL, 0.86** — 0.72에서 상승) 반영. 2차 감사가 **Must-Pass 4개 전부 통과**로 전환하고, 약 110개 수치를 독립 재계산해 **불일치 0건**, 인용 어긋남 0건, 1차 critical 2건(D1/D2)의 **실질 해소**를 확인했다. 특히 1차 감사가 제시한 `margin_amount="66.02"`를 틀렸다고 반박한 것에 대해 2차 감사가 `Decimal("66.025")` + `ROUND_HALF_UP`을 독립 재계산해 **`"66.03"`이 맞다고 확정**했다 — 값 유지. **차단 결함 1건 해소**: **N1(major)** — 1차 D3의 실패 부류가 신설 AC-NET-016에서 재발했다. (a) 단정이 **AC-NET-001의 순액화된 기대값**을 참조하고 있었으므로 무수정 코드에서 반드시 실패하는데도 6곳에서 "무수정 코드에서 통과가 정상"으로 분류되어 있었다. 감사 권고 ①을 채택해 **(a)를 "스파이 밖 baseline 요청과의 7필드 바이트 동일성"으로 재작성**했다 — 이러면 (a)가 순액화 여부에 무관해져 AC-NET-016이 진짜 불변식 보존 AC가 되고(REQ-NET-033이 이 SPEC이 바꾸지 않는 `[EXISTING]` 불변식이라는 사실과 정합), 6곳의 분류 문구가 참이 되며, `wraps` 누락 검출력은 하드코딩 값 대신 살아있는 기준과 비교하므로 오히려 강화된다. 맨 `MagicMock`이 `is None`/`__getitem__`/`.quantize()`/`== Decimal("0")`을 전부 지원해 non-None 단정으로는 검출 불가함을 이 세션에서 직접 실행해 확인했다(그래서 (a) 약화가 아니라 형태 변경이 정답이다). 위험 R16으로 등록. **부수 결함 9건 해소**: N2(AC-NET-005의 M7 판별력 주장 삭제 — 그 픽스처의 순확정 금액이 0이라 선반올림이 관측되지 않는다. M7은 AC-NET-012 **단독** 판별자가 되었고 헤더/요약표/커버리지 3곳을 정합화), N3(AC-NET-016의 "M6 2차 방어선" 주장 삭제 — M6은 캐시를 경유하므로 `call_count`가 1로 유지된다), N4(무수정 코드 집계 "12 실패 / 9 통과"가 산술 불가 → AC 단위 12/5, 테스트 단위 16/5 표로 명시), N5("잔차 0.01인 유일한 픽스처" 정정 + AC-NET-015에 동일 잔차 단정 신설로 REQ-NET-043 상한 검증 2중화), N6(`:163`의 "그 AC에서는 화해를 단정하지 않는다" stale 문구 갱신), N7(`spec-compact.md` 위험 12건 → 17건), N8(parametrize 열거에 003 추가), N9(**`_make_order`(`test_spec_021.py:74`)가 `Decimal(total_price)`를 무조건 호출해 `total_price=None`을 받을 수 없다** — AC-NET-006b(b)가 그것을 요구하므로 원본 헬퍼로는 구현 불가능. 이 세션에서 `Decimal(None)` → `TypeError`를 직접 확인하고 헬퍼 3개 전부의 확장 필요성을 [HARD]로 명시, 위험 R17로 등록), N10(잔차 단정의 설명을 "REQ-NET-043 상한 검증"에서 "이 픽스처의 잔차가 정확히 `0.01`임을 고정하는 특성화 단정, 상한 준수는 그 귀결"로 축소), N11(frontmatter `updated`와 HISTORY 최신 행 날짜 일치). REQ 25개·AC 17개·변이 11개 **전부 번호 무변경** — 단독 판별자가 M4/M10/M11 3건에서 **M4/M7/M10/M11 4건**으로 정정되었다(M7이 005 커버리지를 잃어 012 단독이 됨). 위험 15건 → **17건**. |

---

## 1. Environment (환경)

| 항목 | 내용 |
|------|------|
| 대상 코드 | `backend/order/serializers.py` (Django 5.x + DRF 3.14, `backend/pyproject.toml:10-11`) |
| 영향 화면 | 주문 상세 `결제 정보` 패널 (`frontend/src/pages/OrderDetailPage.tsx:511-513`), 주문 목록 `마진율` 컬럼 |
| 영향 API | `GET /api/orders/{pk}/` (`OrderDetailSerializer`), `GET /api/orders/` (`OrderListSerializer`) |
| 데이터 소재 | `Refund` 모델 (`backend/order/models.py:323-342`), 주문 단위 `related_name="refunds"` |
| DB | 원격 공유 MySQL (`us-west-2`) — 쿼리 1건당 약 130ms |
| 저장 컬럼 | 없음. 7개 필드 전부 `SerializerMethodField` (읽기 시점 계산) |

## 2. Assumptions (명시적 가정)

| # | 가정 | 근거 / 틀렸을 때의 영향 |
|---|------|--------------------------|
| A1 | `Refund` 행이 이 시스템에서 취소·환불의 유일한 신뢰 신호다 | `serializers.py:165-178`이 명시("the cancellation signal lives in the Refund rows, NOT `order_cancelled`"). 틀리면 순액화 기준 자체가 바뀐다 |
| A2 | `Refund.line_item_id`는 `LineItem.shopify_line_item_id`와 조인된다 (PK가 아님) | `purchase_order_views.py:337`, `serializers.py:190` 두 곳이 동일 키를 쓴다 |
| A3 | 한 주문에 같은 `line_item_id`를 가진 `Refund` 행이 여러 개 존재할 수 있다 | `unique_together = ("order", "shopify_refund_id", "line_item_id")` (`models.py:342`) + `models.py:336-341` 주석. 따라서 순액화는 **합산**이어야 한다 |
| A4 | `refunds`는 두 소비처 모두에서 이미 prefetch되어 있다 | `views.py:59`, `views.py:269`. 틀리면 성능 불변식(모듈 4)이 성립하지 않는다 |
| A5 | 환불 행이 없는 주문에서는 gross == net이다 | 산술적 자명. `test_spec_021.py`가 `Refund`를 전혀 만들지 않으므로(매치 0건) 기존 고정값 단정 전부가 유지된다 |
| A6 | `total_price`는 배송비·세금을 포함한 주문 총액이며, `Refund.subtotal + Refund.total_tax`가 그 총액에서 환불된 부분이다 | 프론트엔드가 이미 이 공식으로 `최종 결제 금액`을 표시한다(`OrderDetailPage.tsx:159-163`). 이 SPEC은 그 공식을 백엔드로 복제하는 것이며 새로운 회계 모델을 도입하지 않는다 |

---

## 3. Requirements (EARS)

REQ 접두사는 `REQ-NET-`을 쓴다 — 선행 SPEC-ORDER-021의 `REQ-COST-` 번호 공간과 충돌하지 않게 하기 위함이다.

### 모듈 1 — 라인아이템 수량의 참 순액 산술 `[MODIFY]`

**REQ-NET-001** (Ubiquitous) [HARD]
The order cost calculation (`_compute_cost_breakdown_for_rate`, `backend/order/serializers.py:31-73`) **shall** derive every per-line-item aggregate — `total_weight_grams`, `total_book_count`, `confirmed_cost_krw` — from the **net quantity** of each line item, defined as `max((item.quantity or 0) - refunded_qty.get(item.shopify_line_item_id, 0), 0)`, never from the raw `item.quantity`.

**REQ-NET-002** (Ubiquitous) [HARD]
The system **shall** build the `refunded_qty` mapping by summing `refund.quantity` per `refund.line_item_id` across `obj.refunds.all()`, skipping rows whose `line_item_id` is `None` and treating a `None` `quantity` as `0` — the same construction as `LineItemStateDerivationMixin._derive_line_item_states` (`serializers.py:179-184`).

**REQ-NET-003** (Event-Driven) [HARD]
**When** a line item is partially refunded (net quantity greater than 0 but less than `item.quantity`), the system **shall** reduce that line item's contribution to weight, book count, and confirmed cost **proportionally to the net quantity** — and **shall not** treat the partial refund as a boolean include/exclude decision that preserves the full quantity.

> **[구현 함정 — 명시적 경고]** `serializers.py:186-191`의 `trackable` 리스트 컴프리헨션은 순액을 **boolean 필터로만** 쓴다(순액 > 0이면 원래 수량 전량 유지). 이는 출고/발주 판정에는 맞지만 비용 계산에는 **틀렸다**. 그 코드를 복사하면 REQ-NET-003을 위반한다.

**REQ-NET-004** (Ubiquitous — 금지형) [HARD]
The system **shall not** read `LineItem.purchase_status` as a cancellation signal in the cost path — the only quantity-reducing signal is a `Refund` row.

**REQ-NET-005** (State-Driven) [HARD]
**While** the net book count is `0`, the system **shall** return `0` for `korea_warehouse_krw` via the existing zero-book branch (`serializers.py:54-55`) — the base fee **shall not** be charged to an order with no net goods.

### 모듈 2 — 매출 기준의 순액화 `[MODIFY]`

**REQ-NET-010** (Ubiquitous) [HARD]
The revenue term of the margin formula (`total_price_usd`, `serializers.py:48`) **shall** be the net paid amount, defined as `max(Decimal(str(obj.total_price or "0")) - Σ((refund.subtotal or 0) + (refund.total_tax or 0)) over obj.refunds.all(), Decimal("0"))`.

**REQ-NET-011** (Ubiquitous) [HARD]
The revenue-side sum **shall** include **every** `Refund` row of the order regardless of whether its `line_item_id` matches an existing `LineItem` or is `None` — byte-for-byte the same population the frontend already sums at `frontend/src/pages/OrderDetailPage.tsx:159-162`.

**REQ-NET-012** (Ubiquitous) [HARD]
The revenue-side sum **shall** tolerate `NULL` `subtotal` and `NULL` `total_tax` independently, treating each as `0` (schema: `models.py:330-331`).

**REQ-NET-013** (Ubiquitous) [HARD]
The quantity-side netting (모듈 1) and the revenue-side netting (모듈 2) **shall** ship together as one atomic change. Splitting them across milestones, commits, or feature flags is prohibited: netting costs alone moves order `#37454`'s margin from 37.22 to 60.80, which is **further** from the truth (23.52) than the current defect — the error grows from +13.70 to +37.28 (`research.md` §5.4).

### 모듈 3 — 경계 조건의 결정된 동작 `[MODIFY]`

**REQ-NET-020** (Unwanted) [HARD]
**If** the summed refunded quantity for a line item exceeds `item.quantity`, **then** the system **shall** clamp that line item's net quantity to `0` and never produce a negative weight, book count, or confirmed cost — the `max(..., 0)` convention of `purchase_order_views.py:368`.

**REQ-NET-021** (Unwanted) [HARD]
**If** the summed refunded amount exceeds `obj.total_price`, **then** the system **shall** clamp the net revenue to `Decimal("0")`. Without this clamp a negative revenue divided into a negative margin yields a **positive-looking** `margin_rate` (e.g. `-5 / -5 × 100 = +100.00`), which is strictly worse than reporting nothing.

**REQ-NET-022** (State-Driven) [HARD]
**While** the net revenue is `Decimal("0")`, the system **shall** return `null` for `margin_rate` through the **existing, unmodified** zero-revenue gates (`serializers.py:570-571` for detail, `serializers.py:283-284` for list).

**REQ-NET-023** (State-Driven) [HARD]
**While** an order is fully refunded (every line item's net quantity is `0` **and** the net revenue is `0`), the seven fields **shall** return `confirmed_cost = "0.00"`, `shipping_cost = "0.00"`, `korea_warehouse_cost = "0.00"`, `total_cost = "0.00"`, `total_weight_grams = 0`, `margin_amount = "0.00"`, `margin_rate = null`. This is not an "implementation detail" — it is the pinned contract.

**REQ-NET-024** (Ubiquitous) [HARD]
**Decided behavior for the `has_any_confirmed` gate** (`serializers.py:41-46`): the flag **shall** continue to be evaluated **pre-netting** — `item.confirmed_price is not None` sets it regardless of net quantity. Consequently an order whose only confirmed line item is fully refunded still returns non-null cost fields (all `"0.00"` per REQ-NET-023) rather than flipping all seven to `null`.

> **결정 근거**: (a) 기존 null 게이트 의미(REQ-COST-009/010, SPEC-ORDER-021)를 한 글자도 바꾸지 않아 변경 범위가 산술로만 국한된다. (b) 순액 재화가 0인 주문의 산술적 정답은 실제로 `0.00`이다. (c) `margin_rate`가 REQ-NET-022의 기존 게이트로 이미 `null`이 되므로 "의미 있는 비율이 없다"는 신호는 그 채널로 전달된다. (d) 화면 패널이 `최종 결제 금액 0.00 − 비용 합계 0.00 = 마진 0.00`으로 **자기정합**을 유지한다 — 사후 평가로 바꾸면 7필드가 모두 `—`가 되어 "환율 없음"·"확정매입가 없음"과 구별할 수 없게 된다.

**REQ-NET-025** (Ubiquitous) [HARD]
The system **shall not** introduce any intermediate rounding into the netting. Net quantities are integer arithmetic; net revenue and net confirmed cost are unrounded `Decimal` values. Quantization **shall** remain exactly once per exposed field, in the getters (`serializers.py:555-615`), per design decision B (`get_total_cost` docstring, `serializers.py:606-615`).

**REQ-NET-026** (Ubiquitous)
`total_weight_grams` **shall** remain a raw integer (no quantization), as today (`serializers.py:591-596`), computed from net quantities.

### 모듈 4 — 성능·구조 불변식 `[EXISTING]` (유지 대상)

**REQ-NET-030** (Ubiquitous) [HARD]
The netting **shall** be performed in Python from the `obj.refunds.all()` prefetch cache (`views.py:59` for detail, `views.py:269` for list), and **shall not** issue any per-order or per-line-item database query. The `Subquery`/`OuterRef` ORM pattern of `purchase_order_views.py:334-342` is **forbidden inside the serializers** — it would issue one query per serialized order, i.e. up to 50 per list page (`OrderPagination.page_size = 50`, `views.py:159-160`).

**REQ-NET-031** (Ubiquitous) [HARD]
`GET /api/orders/{pk}/`의 총 쿼리 수 **shall** remain exactly `8` — the value already pinned as `ORDER_DETAIL_QUERY_COUNT` at `test_spec_021.py:48` — and the count of queries referencing `orders_refund` (`models.py:335`) **shall** be exactly `1`, including for orders that have `Refund` rows. This preserves SPEC-ORDER-021 AC-COST-009(c) (`.moai/specs/SPEC-ORDER-021/spec.md:222`).

> **[HARD] 이 값은 SPEC이 결정한다 — 구현자가 실측값으로 재핀하지 않는다** (감사 D11). `8`은 추측이 아니라 `test_spec_021.py:48`이 이미 절대값으로 고정하고 있고 그 스위트의 무수정 통과가 DoD인 값이다. 구현 후 실측이 `8`이 아니라면 그것은 "새 기준선"이 아니라 **REQ-NET-031 위반**이다 — 상수를 갱신하지 말고 작업을 멈추고 원인(추가된 쿼리)을 보고한다. 환불 보유 주문에서만 조건부로 발급되는 상수 1쿼리도 이 규칙에 걸린다.

**REQ-NET-032** (Ubiquitous) [HARD]
`GET /api/orders/`의 총 쿼리 수 **shall** remain `TOTAL_QUERY_COUNT` (현재 `8`, `test_spec_023.py:34`) and **shall** be identical for a 1-order page and a 5-order page where every order carries `Refund` rows. This preserves SPEC-ORDER-023 REQ-OLIST-021 (`.moai/specs/SPEC-ORDER-023/spec.md:162`).

**REQ-NET-033** (Ubiquitous) [HARD]
All seven cost getters **shall** continue to route through `OrderDetailSerializer._compute_cost_breakdown` (`serializers.py:513-540`); the memoization contract documented at `serializers.py:524-530` **shall not** be bypassed, weakened, or duplicated. Observable evidence: `_compute_cost_breakdown_for_rate` **shall** be invoked **exactly once** per serialized order (AC-NET-016).

> **[감사 D1 정정] 이 요구사항의 위반은 쿼리 수로 관측되지 않는다.** 최초 버전은 REQ-NET-033을 AC-NET-009(쿼리 수)에 매핑했으나 그 판별력 주장은 거짓이었다: (i) 순액화는 `obj.refunds.all()` prefetch 캐시를 읽으므로 7번 반복해도 `orders_refund` 쿼리는 1건이고(REQ-NET-030의 전제 그 자체), (ii) `_get_exchange_rate`는 `serializers.py:466-498`에서 **독립적으로 주문 단위 메모이즈**되어 있어(SPEC-ORDER-021 REQ-COST-034, 독스트링 `:472-480`) `_compute_cost_breakdown_uncached`를 7번 호출해도 `orders_exchangerate` 쿼리도 1건이다. 따라서 메모이제이션 우회는 쿼리 수를 전혀 바꾸지 않는다 — 함수 호출 횟수를 직접 관측해야만 잡힌다(AC-NET-016).

### 모듈 5 — 회귀 불변식 및 관측 가능한 화해 `[EXISTING]` / `[NEW]`

**REQ-NET-040** (State-Driven) [HARD]
**While** an order has no `Refund` rows, all seven fields **shall** return byte-identical values to the pre-change implementation. Concretely: every fixed-value assertion in `backend/order/tests/test_spec_021.py` (T1–T22) and `test_spec_023.py:839-852` **shall** pass **unmodified**.

> **[구현자 신호]** `test_spec_021.py`의 고정값(`"2.25"` at `:113`/`:151`, `"1.80"` at `:358`, `"1.25"` at `:429`, `"13.98"` at `:433` 등)을 편집해야 할 것 같다면, 그것은 수정이 틀렸다는 신호다. 환불이 없는 주문의 값은 정의상 불변이다.

**REQ-NET-041** (Ubiquitous) [HARD]
The detail serializer field set **shall not** change — no field added or removed. `test_spec_023.py:848`의 `set(res.data.keys()) == DETAIL_SERIALIZER_FIELDS` (`:39-58`, **45개 필드** — 프로그램 카운트로 확정, 중복 0) 단정은 무수정으로 통과해야 한다.

**REQ-NET-042** (Ubiquitous) [HARD]
`OrderListSerializer.get_margin_rate` (`serializers.py:266-288`) and `OrderDetailSerializer.get_margin_rate` (`serializers.py:563-575`) **shall** return the identical string for the same order — the shared-formula guarantee of SPEC-ORDER-023 REQ-OLIST-016 survives this change because both continue to call the single netted `_compute_cost_breakdown_for_rate`.

**REQ-NET-043** (Ubiquitous)
The backend's net revenue basis **shall** reconcile with the frontend's `netPaidAmount` (`OrderDetailPage.tsx:163`) by construction: `margin_amount + total_cost` **shall** equal the net revenue within `0.01` USD, the residual being the unavoidable consequence of quantizing each field once (REQ-NET-025 / design decision B).

**REQ-NET-044** (Optional) — 프론트엔드
**Where** the frontend already computes `netPaidAmount` locally (`OrderDetailPage.tsx:159-163`), the system **shall** keep that local calculation unchanged `[EXISTING]`. No new backend field is exposed and no frontend file is modified.

> **결정 근거**: 목표는 "백엔드 마진이 화면의 최종 결제 금액과 화해하는 것"이며 그것은 백엔드가 동일 공식을 채택하는 것만으로 달성된다. 필드를 신설하면 `DETAIL_SERIALIZER_FIELDS` 계약(`test_spec_023.py:39-58`)이 바뀌고, 프론트 타입 + 픽스처 2곳(`OrderDetailPage.test.tsx`, `SearchTab.test.tsx` — SPEC-ORDER-021 v1.4.0이 기록한 "두 번째 픽스처 누락" 함정)을 건드려야 한다. 목표에 기여하지 않는 비용이다. 중복 공식의 위험은 REQ-NET-043의 백엔드 단위 화해 단정으로 코드에 고정한다. 상세 근거: `research.md` §11.

---

## 4. Traceability (REQ → AC)

| REQ | AC |
|-----|-----|
| REQ-NET-001 | AC-NET-001, AC-NET-002, AC-NET-015 |
| REQ-NET-002 | AC-NET-002, AC-NET-007, **AC-NET-015** (합산 축의 유일한 판별자, 감사 D2) |
| REQ-NET-003 | **AC-NET-002** (비례 축의 유일한 판별자) |
| REQ-NET-004 | AC-NET-013 |
| REQ-NET-005 | AC-NET-004 |
| REQ-NET-010 | AC-NET-001, AC-NET-003 |
| REQ-NET-011 | AC-NET-008, AC-NET-007 |
| REQ-NET-012 | AC-NET-007 |
| REQ-NET-013 | AC-NET-001, AC-NET-003 (두 축을 한 픽스처에서 동시 단정) |
| REQ-NET-020 | AC-NET-006a (a) `quantity=1`+초과환불, (b) `quantity IS NULL`+환불 |
| REQ-NET-021 | AC-NET-006b (a) `total_price` 초과환불, (b) `total_price IS NULL`+환불 |
| REQ-NET-022 | AC-NET-004 (a) 상세, **(b) 목록**(`serializers.py:283-284` 게이트), AC-NET-006b |
| REQ-NET-023 | AC-NET-004 |
| REQ-NET-024 | AC-NET-005 |
| REQ-NET-025 | AC-NET-012 |
| REQ-NET-026 | AC-NET-001, AC-NET-002, AC-NET-015 |
| REQ-NET-030 | AC-NET-009, AC-NET-010 |
| REQ-NET-031 | AC-NET-009 (a) — 절대값 `8`은 SPEC이 결정, 구현자 재핀 금지 |
| REQ-NET-032 | AC-NET-010 |
| REQ-NET-033 | **AC-NET-016** (함수 호출 횟수 관측) — AC-NET-009는 이 위반을 검출할 수 없다(감사 D1) |
| REQ-NET-040 | AC-NET-014, `test_spec_021.py` 무수정 재통과 |
| REQ-NET-041 | `test_spec_023.py:848` 무수정 재통과 (AC 없음 — DoD 검증) |
| REQ-NET-042 | AC-NET-011 |
| REQ-NET-043 | AC-NET-003 (오차 0 픽스처 2건 정확 일치) + **AC-NET-005** (잔차 `0.01` 정확 일치 — 상한 자체를 검증, 감사 D12) |
| REQ-NET-044 | 프론트엔드 `git diff` 공집합 (AC 없음 — DoD 검증) |

> **[HARD] 추적표 무결성 규칙** (감사 D1의 재발 방지): REQ가 **그 위반을 실제로 검출할 수 없는** AC에 매핑되어 있으면 그 REQ는 미커버다. AC 없이 DoD 검사만으로 보증되는 REQ는 위 표에 "(AC 없음 — DoD 검증)"으로 명시한다 — AC로 위장하지 않는다. 현재 그런 REQ는 REQ-NET-041, REQ-NET-044 두 건이다.

---

## 5. Exclusions (What NOT to Build)

1. **`purchase_status == "order_cancelled"` 처리 — 명시적 비목표, 누락이 아니다.**
   그런 라인아이템은 `Refund` 행이 없다 → 매출이 내려가지 않는다. 비용만 제외하면 마진이 **반대 방향으로** 과대 계상된다. `Refund` 행은 수량과 매출 양쪽을 **대칭으로** 움직이는 유일한 신호이므로 이 SPEC은 오직 `Refund`만 본다. 프로덕션에서 그런 품목을 가진 주문은 **61건**이며(**2026-08-17 원격 DB 스냅샷, UNVERIFIED** — 조사 세션에서만 실측했고 이후 재조회하지 않았다, 구현 시점 재실측 권고, `research.md` §8/§13), 별도 판단이 필요한 후속 과제로 남긴다. SPEC-ORDER-023의 명시적 가정 4(`order_cancelled` 미제외)와 정합한다.
2. **데이터 백필 / 마이그레이션 / 저장 컬럼 신설 — 전부 범위 밖.**
   7개 필드 전부 `SerializerMethodField`로 읽기 시점 계산이다(`research.md` §10). 저장 컬럼이 없으므로 마이그레이션도, 백필 스크립트도 없다. 영향받는 96건은 **다음 조회 시 자동으로 정정된다**. (이 프로젝트는 과거에 "고쳤는데 기존 데이터가 안 바뀐다"는 혼선을 겪은 적이 있어 명시한다.)
3. **비용 상수 3개 변경 — 무변경.**
   `SHIPPING_COST_USD_PER_KG = 5.45`, `KOREA_WAREHOUSE_BASE_KRW = 1250`, `KOREA_WAREHOUSE_PER_BOOK_KRW = 500` (`serializers.py:15-17`)의 값과 한국물류비 공식 형태(`serializers.py:54-59`)는 한 글자도 바꾸지 않는다. 바꾸면 `test_spec_021.py`의 고정값 다수가 깨지며 이는 REQ-NET-040 위반이다.
4. **환율 해석 로직 무변경.**
   `_get_exchange_rate`(상세, 메모이즈), `_resolve_exchange_rate`(목록, `serializers.py:76-90`), 배치 히스토리 로딩(`OrderListView`) 전부 무변경.
5. **`has_any_confirmed` 게이트의 의미 변경 — 하지 않는다** (REQ-NET-024). null 게이트 2개(REQ-COST-009/010, SPEC-ORDER-021)의 조건식은 무변경이다.
6. **프론트엔드 변경 — 없음** (REQ-NET-044). 새 응답 필드 없음, 타입 변경 없음, 픽스처 변경 없음.
7. **`_derive_line_item_states`(`serializers.py:157-213`) 변경 — 없음.** 그 경로의 boolean 필터 의미(부분 환불은 제외 사유가 아니다, `serializers.py:165-171`)는 출고/발주 판정에 대해 **의도된 정답**이며 이 SPEC은 건드리지 않는다. 두 경로가 순액을 다르게 쓰는 것은 모순이 아니라 목적 차이다.
8. **`purchase_order_views.py`의 ORM 순액화 패턴 변경 — 없음.** 참조만 하고 옮겨오지 않는다(REQ-NET-030).
9. **`has_refund` / `refunds` 직렬화 출력 변경 — 없음.**
10. **환불 반영 여부를 켜고 끄는 설정·플래그 — 만들지 않는다.** 순액화는 항상 켜져 있다(REQ-NET-013).

---

## 6. 알려진 제약 / 후속 과제

| # | 내용 |
|---|------|
| C1 | `margin_amount + total_cost`가 순매출과 최대 `0.01` USD 어긋날 수 있다 — 필드별 1회 양자화(설계 결정 B)의 필연적 결과다. AC-NET-003은 이를 허용 오차로 명시하며, 지정된 두 픽스처에서는 오차 0으로 정확히 일치한다 |
| C2 | 프론트엔드와 백엔드가 순매출 공식을 **중복** 보유한다(REQ-NET-044 결정). 두 경로가 동일 공식이므로 결과는 구조적으로 일치하지만, 한쪽만 변경되면 화면에서 즉시 드러난다 — 의도된 상호 검산이다 |
| C3 | `order_cancelled` 품목을 가진 61건은 이 SPEC 이후에도 비용이 계상된다(Exclusions 1) |
| C4 | `Refund.subtotal`이 배송비 환불을 포함하는지 여부는 Shopify 페이로드에 의존한다. 이 SPEC은 프론트엔드가 이미 채택한 해석(`subtotal + total_tax`)을 그대로 따르며 재해석하지 않는다 — 두 화면 값의 화해가 목표이기 때문이다 |
| C5 | 과다 환불(REQ-NET-020/021)은 데이터 이상 상황에 대한 방어이며, 프로덕션에서 발생 사례가 확인된 것은 아니다. 하한이 없으면 음수 비용이 흘러 들어가므로 방어를 둔다 |

---

## 7. Definition of Done (요약, 전체는 `acceptance.md`)

- [ ] AC-NET-001 ~ AC-NET-016 전부 통과 (`backend/order/tests/test_spec_026.py`, 총 **21개 테스트** — 006a/006b 분리 + **003**/004/006a/006b의 parametrize 분리)
- [ ] 무수정 코드에서 **AC 단위 12개 실패 / 5개 통과**(테스트 단위 16 실패 / 5 통과)임을 확인 (RED 성립). AC-NET-009/010/013/014/016은 불변식·비목표·하위호환 AC이므로 **현재도 통과하는 것이 정상**이다 — 이들을 "고장난 테스트"로 취급해 픽스처를 고치면 안 된다 (감사 D3)
- [ ] **[HARD] AC-NET-016의 (a)는 스파이 밖 baseline 요청과의 바이트 동일성으로 구현한다** — AC-NET-001의 순액화된 기대값을 참조하면 이 AC가 무수정 코드에서 실패해 위 분류가 거짓이 되고, 그 충돌을 (a) 삭제로 해소하면 M11의 단독 판별자가 무력화된다 (감사 N1)
- [ ] `test_spec_021.py` 21개 **무수정** 통과 (고정값 편집 0건)
- [ ] `test_spec_023.py` 전량 **무수정** 통과 (특히 `:848` 필드셋, `:638-681` 쿼리 수)
- [ ] `backend/order/tests/` 전체 스위트 통과
- [ ] `git diff --stat frontend/` 가 공집합 (REQ-NET-044)
- [ ] `git diff`로 확인: `serializers.py`의 변경이 `_compute_cost_breakdown_for_rate`(`:31-73`) 내부와 그 위 `@MX` 주석 블록에 국한된다. 7개 게터(`:555-615`)·메모이제이션(`:513-540`)·null 게이트 2곳의 조건식은 무변경
- [ ] mx_plan 실행 및 ANCHOR 강등 보고 (`plan.md` §mx_plan)
