---
id: SPEC-ORDER-021
version: 1.4.0
status: implemented
created_at: 2026-08-14
updated: 2026-08-15
author: ggajo
priority: High
issue_number: 0
labels: [order, margin, cost-breakdown, backend, frontend, exchange-rate]
---

# 마진 계산에 배송비·한국창고비 반영

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.4.0 | 2026-08-15 | ggajo | TDD 확장(manager-tdd, 동일 worktree `rate-display`, 브랜치 `feature/SPEC-ORDER-021-rate-display`). 적용 환율을 주문 상세 화면에 노출한다. `OrderDetailSerializer`에 `exchange_rate`(`ExchangeRate.rate`, 문자열)와 `exchange_rate_date`(적용된 레코드의 `effective_date`, ISO 문자열) 신규 `SerializerMethodField` 2개를 추가했다(REQ-COST-030/031, AC-COST-020~023). **이 두 필드는 기존 7개 비용 필드가 공유하는 `has_any_confirmed` 게이트(설계 결정 D)를 공유하지 않는다** — `_get_exchange_rate(obj)`가 레코드를 반환하기만 하면 `margin_amount`가 `null`이어도(확정 매입가 전무) 이 둘은 값을 반환한다(REQ-COST-033, AC-COST-022) — 그래야 "이 날짜에 환율 레코드가 없다"와 "환율은 있지만 아직 확정된 게 없다"를 구분할 수 있다. `null`은 오직 `_get_exchange_rate(obj)`가 `None`을 반환할 때(해당 주문일 이전 어떤 레코드도 없거나, `shopify_created_at` 자체가 없을 때)만 발생한다(REQ-COST-032, AC-COST-023). 신규 쿼리를 추가하지 않기 위해 `_get_exchange_rate`(기존에는 `_compute_cost_breakdown_uncached` 내부에서만 호출되던, 메모이제이션 없는 메서드)를 주문(`obj.pk`) 단위로 메모이즈했다(REQ-COST-034) — `_compute_cost_breakdown_uncached`도 이 메모이즈된 버전을 그대로 재사용하므로, 신규 게터 2개가 늘어나 DRF가 평가하는 `SerializerMethodField`가 7개에서 9개가 되었음에도 `orders_exchangerate` 참조 쿼리 수는 여전히 정확히 1이다(AC-COST-009 무수정 재통과로 실측 확인 — `ORDER_DETAIL_QUERY_COUNT=7`도 변화 없음, `orders_line_item` 참조 쿼리 수도 1로 불변). `margin_usd`/`get_margin_amount`/`get_margin_rate`/두 None 게이트(REQ-COST-009/010)는 **한 글자도 변경하지 않았다** — `git diff`로 확인(완료 조건). 프론트엔드는 `OrderDetail`(`frontend/src/types/order.ts`)에 두 필드를 추가하고, `OrderDetailPage.tsx`의 결제 정보 섹션 최하단(마진율 다음, `pl-3` 들여쓰기 그룹 **밖**)에 `적용 환율` 줄을 추가했다(REQ-COST-035/036, AC-COST-024) — 계산 결과가 아니라 계산에 쓰인 근거 값이므로 비용 하위 항목 그룹에 포함시키지 않는다. `null` 폴백은 기존 관례(`"—"`)를 따른다. `frontend/src/pages/OrderDetailPage.test.tsx`와 `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`(`:47`)의 두 `buildOrderDetail()` 픽스처 모두에 `exchange_rate: null, exchange_rate_date: null` 기본값을 추가했다(SPEC-ORDER-021 v1.3.0 D2 전례와 동일한 이유 — 신규 필수 필드 추가 시 두 번째 픽스처를 놓치기 쉽다). **발견한 베이스라인 불일치(이 SPEC이 만든 것이 아님, 수정하지 않음)**: `tsc -b`의 실제 베이스라인은 이 문서의 이전 버전들이 기록한 24건이 아니라 26건이다 — `frontend/src/hooks/usePurchaseOrderQueries.test.tsx`(`:65,78`)에 이 SPEC 이전부터 존재하던 신규 에러 2건이 추가로 있었다(원인 미상, 이 SPEC의 범위 밖). 이 SPEC이 수정한 4개 파일(`types/order.ts`, `OrderDetailPage.tsx`, `OrderDetailPage.test.tsx`, `SearchTab.test.tsx`)에는 신규 에러 0건이며, 전체 에러 수는 26건에서 26건으로 불변임을 실측 확인했다. |
| 1.3.0 | 2026-08-15 | ggajo | TDD 확장(manager-tdd, 동일 worktree `SPEC-ORDER-021`, 브랜치 `feature/SPEC-ORDER-021`). `OrderDetailSerializer`에 `confirmed_cost`(`confirmed_cost_usd`)와 `total_cost`(`confirmed_cost_usd+shipping_cost_usd+korea_warehouse_usd`, **반올림 전 정확값의 합을 한 번만 양자화**)를 신규 노출하고(REQ-COST-020~026, AC-COST-014~018), `OrderDetailPage.tsx`의 결제 정보 섹션을 `최종 결제 금액 → 비용 합계(total_cost) → [원가(confirmed_cost)/배송비(shipping_cost)/한국물류(korea_warehouse_cost), 들여쓰기+저채도로 시각적 하위 표시] → 마진 → 마진율` 순서로 재구성했다(REQ-COST-027/028, AC-COST-019). `한국창고비` 라벨을 `한국물류`로 변경했다(REQ-COST-029). `margin_usd`/`get_margin_amount`/`get_margin_rate`/두 None 게이트(REQ-COST-009/010)는 **한 글자도 변경하지 않았다** — 두 신규 필드는 기존 메모이즈된 `_compute_cost_breakdown` 헬퍼가 이미 계산해 두던 `confirmed_cost_usd`를 반환값 dict에 추가 노출하고, `total_cost_usd`는 그 dict 안에서 반올림 전 세 항(`confirmed_cost_usd`, `shipping_cost_usd`, `korea_warehouse_usd`)을 합산해 추가했을 뿐이다. AC-COST-009(쿼리 수 불변식)는 게터가 5개에서 7개로 늘었음에도 메모이제이션 덕분에 **무수정으로 통과**했다 — `ORDER_DETAIL_QUERY_COUNT=7`, `orders_line_item`/`orders_exchangerate` 참조 쿼리 수(각 1)가 확장 전후로 완전히 동일함을 실측 확인했다(변경 없음, 상수 갱신 불필요). **알려진 기존 불일치(수정하지 않음, 발견만 기록)**: `OrderDetailPage.tsx:168`(`netPaidAmount = total_price − totalRefunded`)이 최종 결제 금액 표시에 쓰는 기준과, 마진 계산(`total_price_usd`만 사용, 환불 미반영)의 기준이 다르다 — 환불이 있는 주문에서는 `최종 결제 금액 − 비용 합계 ≠ 마진`이 된다. 새 세로 레이아웃은 이 뺄셈이 성립하는 것처럼 보이게 만들어 이전보다 눈에 띄지만, 이 SPEC의 범위가 아니므로(사용자가 별도 결정) 그대로 둔다 — "알려진 제약사항" 절 참조. |
| 1.0.0 | 2026-08-14 | ggajo | 최초 작성. 현재 마진(`margin_usd = total_price_usd - confirmed_cost_usd`, `OrderDetailSerializer._compute_margin_usd`, `backend/order/serializers.py:189-204`)이 배송비·한국창고비를 반영하지 않아 실제 수익성보다 과대 표시되는 문제를 확정된 사용자 요구사항에 따라 해소한다. 모든 `file:line` 인용은 이 세션에서 직접 재검증했다 — 선행 SPEC의 인용을 재사용하지 않았다. |
| 1.2.0 | 2026-08-15 | ggajo | TDD 구현 완료(manager-tdd, worktree `SPEC-ORDER-021`). 계획 대비 발산 2건을 여기 기록한다 — (1) `plan.md`/`acceptance.md`가 인용하는 `backend/order/tests/test_spec_018.py`(쿼리 캡처·워밍업·`UNORDERED_ENDPOINT_QUERY_COUNT` 관례의 근거 파일)가 이 브랜치(master 556f1b5 기준)에는 존재하지 않는다 — 다른 SPEC 브랜치에서만 존재했던 것으로 보인다. `test_spec_021.py`는 대신 `test_spec_015.py:1118-1121`(`CaptureQueriesContext` 사용)과 `test_spec_011.py:24,267-269`(같은 패턴)를 실제 존재하는 선례로 삼아 동일한 관례(캡처 + 절대값 고정 + 워밍업 요청)를 독립 구현했다 — 동작과 판별력은 `plan.md`/`acceptance.md`가 의도한 것과 동일하다. `ORDER_DETAIL_QUERY_COUNT = 7`은 실측값이다(추측 아님, `test_spec_021.py` 상단 주석 참조). (2) `plan.md` 완료 조건의 "`npm run build`(`tsc -b`) 통과"는 이 브랜치의 현재 상태에서 문자 그대로는 거짓이다 — 이 SPEC 이전부터 `src/pages/PurchaseOrders/tabs/ConfirmOrderTab.tsx`(20건), `src/pages/BookDetailPage.tsx`(2건), `src/pages/DashboardPage.test.tsx`(1건), `src/services/purchaseOrderApi.ts`(1건), 총 24건의 `tsc -b` 에러가 이 SPEC과 무관하게 이미 존재했다(구현 시작 전 실측, 구현 완료 후에도 정확히 24건 동일 — `git diff` 대상 4개 파일에는 신규 에러 0건). 올바른 게이트는 "`tsc -b` 에러 수가 24건에서 변하지 않고, 이 SPEC이 수정한 4개 파일(`types/order.ts`, `OrderDetailPage.tsx`, `OrderDetailPage.test.tsx`, `SearchTab.test.tsx`)에 신규 에러가 0건"이다 — `plan.md`/`acceptance.md`의 "통과" 문구는 이 베이스라인 전제 없이 오해를 유발하므로 여기 정정을 남긴다. |
| 1.1.0 | 2026-08-14 | ggajo | plan-auditor 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-021-review-1.md`, iteration 1, FAIL/APPROVE WITH CHANGES, 0.75) 반영. 감사가 확인한 것(무변경): `file:line` 인용 약 45건 전부 정확, 손계산 22건 전부 재현, 백엔드 회귀 목록 완전, 범위 규율 통과. **차단 결함 6건 해소**: D1(critical) — AC-COST-009 (b)의 `"orders_line_item" in sql` 부분 문자열 매칭이 `LineItemNote.db_table = "orders_line_item_note"`(models.py:297)까지 잡아 정상 구현에서도 2를 반환하던 거짓 실패를 정규식 `orders_line_item(?!_)` 매칭으로 교체. D2(major) — `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx:47`의 별도 `buildOrderDetail()` 리터럴이 REQ-COST-017 신규 필드로 타입 체크가 깨지는 문제를 회귀 대상에 추가(`plan.md` M2/M4). D3(major) — AC-COST-011의 `shipping_cost="0.00"` 픽스처가 `Number("0.00").toLocaleString()==="0"`이라 "0 USD"로 렌더되어 실패하던 것을 `"8.18"`(AC-COST-003 재사용)로 교체. D4(major) — REQ-COST-007(환율 적용)이 전 AC가 `rate=1000.00`을 공유해 판별력이 없던 것("묵시적 커버" 주장 철회)을 신규 AC-COST-012(`rate=1250.00`)로 보강. D5(major) — REQ-COST-015의 "cost-breakdown 계산당"이 게터 5회 독립 호출(라인아이템 순회 5회 + `ExchangeRate` 쿼리 최대 5회)을 허용해 설계 결정 C와 충돌하고, 원격 RDS(`us-west-2`, `backend/.env`) 배포에서 설계 결정 F의 "실질적 영향 없음" 근거가 성립하지 않던 것을 "주문 직렬화당 최대 1회"로 강화 — 설계 결정 C/F, 제약사항, Exclusions, 후속 과제 2, `plan.md` R7을 함께 정정하고 AC-COST-009에 `orders_exchangerate` 참조 쿼리 수 단정을 추가. D6(major) — AC-COST-006/007이 관례상 `res.data.get(...)`(키 없어도 `None`)으로 작성되면 현재 코드에서 이미 통과해 RED가 성립하지 않던 것을 `"shipping_cost" in res.data` 키 존재 단정으로 명시. **부수 결함 8건 해소**: D7(추적표 REQ-COST-007/011/013 불일치 4곳 — AC-COST-001에 `shipping_cost`/`total_weight_grams` 단정과 Traces 추가), D8(acceptance.md "5건"→"3건"), D9(`plan.md`의 `serializers.py:141-232`→`141-225`), D10(`test_spec_018.py:490-492` 선례에 따라 AC-COST-009에 워밍업 요청 추가), D11(ROUND_HALF_UP·HALF_EVEN 미판별 — 신규 AC-COST-013, `grams=500,quantity=1`→`2.725`→`"2.73"`), D12(`total_weight_grams` 노출 근거를 "프론트엔드 소비" 대신 "이미 계산되는 값이라 노출 비용이 0에 가깝고 향후 백엔드 디버깅에 유용"으로 정정), D13(acceptance.md `tsc --noEmit`→`tsc -b`, `tsconfig.json`이 `"files": []` 솔루션 파일이라 실제 게이트가 아님), D14(REQ-COST-014/018 라벨 Unwanted→Ubiquitous, AC-COST-010 라벨 Unwanted→Event-Driven — 번호 재부여 없이 라벨만 교정). REQ 19개(무변경, REQ-COST-015 문구만 교정) + AC 11개→13개(AC-COST-012/013 신규). |

---

## 문제 정의

`OrderDetailSerializer`(`backend/order/serializers.py:141-225`)의 `get_margin_amount`/`get_margin_rate`(`:206-225`)는 `_compute_margin_usd`(`:189-204`)가 계산한 `margin_usd = total_price_usd - confirmed_cost_usd`만을 반영한다. 여기서 `confirmed_cost_usd`는 라인아이템별 `confirmed_price × quantity`의 합을 주문일 환율로 나눈 값(`:194-204`)이며, `total_price_usd`는 Shopify `total_price`를 그대로 USD로 취급한 값이다(`:202`). 이 공식에는 실제로 발생하는 두 가지 비용이 빠져 있다 — (1) 도서 무게 기반 국제 배송비, (2) 한국창고 처리 수수료(주문당 기본료 + 추가 권수 요금). 그 결과 `margin_amount`/`margin_rate`가 실제 마진보다 항상 더 높게 표시되어, 수익성 판단의 근거로 삼기에는 왜곡된 값이다.

`LineItem`에는 이미 이 두 비용을 계산하는 데 필요한 필드가 모두 존재한다 — `grams`(`backend/order/models.py:181`, Shopify 동기화 값, 개당 그램), `quantity`(`:176`) — 신규 모델 필드나 마이그레이션 없이 시리얼라이저 계산만으로 반영 가능하다.

## 목표

1. `margin_amount`/`margin_rate`(USD, `backend/order/serializers.py:206-225`)에 배송비와 한국창고비를 반영한다.
2. 반영된 두 비용을 `shipping_cost`/`korea_warehouse_cost` 필드로 `OrderDetailSerializer` 응답에 노출해, 프론트엔드가 마진 옆에 비용 내역을 보여줄 수 있게 한다.
3. 기존 None 게이트(환율 없음 → `null`, 확정 매입가 전무 → `null`, `backend/order/serializers.py:191-193,200-201`)는 그대로 유지한다.
4. 향후 미국창고비를 추가할 때 기존 5개 필드 게터의 제어 흐름을 재구성하지 않아도 되는 확장 지점을 남긴다(이 SPEC 자체는 미국창고비를 구현하지 않는다).

## 확정된 사용자 결정

1. **배송비 공식.** `shipping_cost_usd = 5.45 USD / 1000g × total_weight_grams`, 여기서 `total_weight_grams = Σ((grams or 0) × (quantity or 0))`(주문의 전체 라인아이템 대상, 확정 매입가 여부와 무관).
2. **한국창고비 공식.** `total_book_count = Σ(quantity or 0)`(전체 라인아이템 대상). `korea_warehouse_krw = 1250 + 500 × max(total_book_count − 1, 0)`(주문당 1250원에 1권 포함, 추가 1권마다 500원). `total_book_count == 0`이면 `korea_warehouse_krw = 0`(기본료를 적용하지 않는다). `confirmed_price` 환산과 동일한 주문일 환율로 USD 환산한다.
3. **신규 마진 공식.** `margin_usd = total_price_usd − confirmed_cost_usd − shipping_cost_usd − korea_warehouse_usd`. `margin_rate` 공식과 반올림 규칙(2자리 ROUND_HALF_UP, `total_price_usd == 0`이면 `null`)은 무변경이다. 기존 None 게이트(환율 없음, 확정 매입가 전무)도 무변경이다.
4. **비용 내역 노출.** `OrderDetailSerializer`가 `shipping_cost`, `korea_warehouse_cost`를 `margin_amount`와 동일한 관례(2자리 ROUND_HALF_UP, 문자열)로 추가 노출한다. `total_weight_grams`(원시 그램 정수)도 함께 노출한다 — 이 SPEC의 프론트엔드 화면(REQ-COST-016/017)은 `shipping_cost`/`korea_warehouse_cost` 두 필드만 표시하므로 `total_weight_grams`는 현재 소비자가 없지만, 이미 같은 순회에서 계산되는 값이라 API 응답에 포함하는 한계 비용이 사실상 0이고 백엔드 디버깅·향후 프론트엔드 확장(예: 배송비 수치의 근거 표시)에 유용하기 때문에 지금 노출한다(설계 결정 D).
5. **미국창고비는 이 SPEC의 범위 밖이다.** 자리표시자 필드나 0값 필드를 만들지 않는다. 비용 계산은 4번째 항을 나중에 추가할 수 있는 구조로 만든다(설계 결정 E).

## 명시적 가정

1. `total_book_count == 0`은 실제로 발생할 수 있다 — `LineItem.quantity`는 `null=True`(`backend/order/models.py:176`)이므로, `confirmed_price`는 채워졌지만 `quantity`가 아직 동기화되지 않은 라인아이템이 있는 주문이 존재할 수 있다. 이 경우 한국창고비 기본료(1250원)를 적용하지 않는 것이 "0권을 처리했는데 최소 1250원을 청구한다"는 모순을 피한다(REQ-COST-006).
2. 배송비·한국창고비 산정의 무게/권수 합산은 **확정 매입가 여부와 무관하게 전체 라인아이템**을 대상으로 한다 — 실제로 발송되는 물리적 물량(무게, 권수)은 매입가 확정 여부와 별개의 사실이기 때문이다. 반면 매입원가 합산(`confirmed_cost_krw`)은 기존과 동일하게 `confirmed_price`가 있는 라인아이템만 대상으로 한다(SPEC-ORDER-008 REQ-006 관례 유지).
3. `grams`가 `null` 또는 `0`인 라인아이템은 무게 합산에서 `0`으로 취급되며, 이 때문에 `margin_amount`가 `null`이 되지는 않는다 — 무게 데이터 결손이 마진 계산 가능 여부의 게이트가 아니다.
4. `korea_warehouse_usd` 환산에 사용하는 환율은 `confirmed_price` 환산과 **동일한** 주문일 환율(`_get_exchange_rate`, `backend/order/serializers.py:176-187`)이다 — 별도의 환율 조회 로직을 신설하지 않는다.

## 범위 — 델타

| 마커 | 대상 | 내용 |
|---|---|---|
| [MODIFY] | `OrderDetailSerializer._compute_margin_usd`(`backend/order/serializers.py:189-204`) 및 `get_margin_amount`/`get_margin_rate`(`:206-225`) | 비용 내역(배송비, 한국창고비)을 포함하도록 확장. 상세 설계는 `plan.md`. |
| [NEW] | `OrderDetailSerializer`의 `shipping_cost`/`korea_warehouse_cost`/`total_weight_grams` `SerializerMethodField` 3개 | 신규 필드 게터 + `Meta.fields`(`:164` 인근) 추가. |
| [EXISTING] | `OrderListSerializer`(`backend/order/serializers.py:14-36`) | 무수정 — 목록 API는 오늘도 마진 필드를 노출하지 않으며 이 SPEC도 노출하지 않는다(REQ-COST-014). |
| [EXISTING] | `LineItem`/`ExchangeRate` 모델(`backend/order/models.py:152-238,495-509`) | 무수정 — 신규 모델 필드·마이그레이션 없음. 필요한 필드(`grams`, `quantity`, `confirmed_price`, `ExchangeRate.rate`)가 이미 존재한다. |
| [MODIFY] | `frontend/src/types/order.ts`의 `OrderDetail`(`:168-`, `margin_amount`/`margin_rate` `:196-197`) | `shipping_cost`/`korea_warehouse_cost` 필드 추가. |
| [MODIFY] | `frontend/src/pages/OrderDetailPage.tsx`의 결제 정보 섹션(`:505-527`) | 배송비·한국창고비 표시 줄 추가. |

### v1.3.0 확장 — 델타

| 마커 | 대상 | 내용 |
|---|---|---|
| [MODIFY] | `_compute_cost_breakdown_uncached`(`backend/order/serializers.py`) | 이미 지역변수로 계산 중이던 `confirmed_cost_usd`를 반환 dict에 추가 노출하고, `total_cost_usd = confirmed_cost_usd + shipping_cost_usd + korea_warehouse_usd`(반올림 전 정확값의 합)를 신규 계산해 함께 반환. `margin_usd` 계산식과 두 None 게이트는 무변경. |
| [NEW] | `OrderDetailSerializer`의 `confirmed_cost`/`total_cost` `SerializerMethodField` 2개 | 기존 메모이즈된 `_compute_cost_breakdown` 헬퍼를 그대로 재사용(REQ-COST-022) — 신규 쿼리·신규 라인아이템 순회 없음. `Meta.fields`에 추가. |
| [MODIFY] | `frontend/src/types/order.ts`의 `OrderDetail` | `confirmed_cost: string \| null`, `total_cost: string \| null` 추가(REQ-COST-023). |
| [MODIFY] | `frontend/src/pages/OrderDetailPage.tsx`의 결제 정보 섹션 | `최종 결제 금액 → 비용 합계(total_cost) → [원가(confirmed_cost)/배송비/한국물류, 들여쓰기+저채도] → 마진 → 마진율` 순서로 재구성(REQ-COST-027/028). `한국창고비` 라벨을 `한국물류`로 변경(REQ-COST-029). |
| [EXISTING] | `margin_usd`, `get_margin_amount`, `get_margin_rate`, `_get_exchange_rate`, 두 None 게이트 | 한 글자도 변경하지 않는다 — `git diff`로 확인(완료 조건). |

### v1.4.0 확장 — 델타

| 마커 | 대상 | 내용 |
|---|---|---|
| [MODIFY] | `OrderDetailSerializer._get_exchange_rate`(`backend/order/serializers.py`) | 조회 로직(폴백 포함)은 무변경 — `obj.pk` 키의 인스턴스 딕셔너리로 결과를 메모이즈하도록 감싸기만 했다(REQ-COST-034). 반환값의 의미(어떤 레코드가 선택되는지)는 한 글자도 바뀌지 않는다. |
| [NEW] | `OrderDetailSerializer`의 `exchange_rate`/`exchange_rate_date` `SerializerMethodField` 2개 | 메모이즈된 `_get_exchange_rate`를 직접 호출(REQ-COST-030/031) — `_compute_cost_breakdown`(`has_any_confirmed` 게이트)을 거치지 않는다(설계 결정 H). `Meta.fields`에 추가. |
| [MODIFY] | `frontend/src/types/order.ts`의 `OrderDetail` | `exchange_rate: string \| null`, `exchange_rate_date: string \| null` 추가(REQ-COST-036). |
| [MODIFY] | `frontend/src/pages/OrderDetailPage.tsx`의 결제 정보 섹션 | `마진율` 다음, `pl-3` 그룹 밖에 `적용 환율` 표시 줄 추가(REQ-COST-035). |
| [MODIFY] | `frontend/src/pages/OrderDetailPage.test.tsx`, `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`의 `buildOrderDetail()` 2곳 | `exchange_rate: null, exchange_rate_date: null` 기본값 추가(v1.3.0 감사 D2와 동일한 이유). |
| [EXISTING] | `margin_usd`, `get_margin_amount`, `get_margin_rate`, 두 None 게이트, `_compute_cost_breakdown`/`_compute_cost_breakdown_uncached`의 계산 로직 | 한 글자도 변경하지 않는다 — `git diff`로 확인(완료 조건). |

## 관련 SPEC

- **SPEC-ORDER-008** — `margin_amount`/`margin_rate` 필드 최초 도입, 확정 매입가 부분 합산(`has_any_confirmed`) 관례 확립. 이 SPEC은 그 관례(확정 매입가만 원가 합산 대상)를 그대로 유지한다.
- **SPEC-ORDER-009** — `ExchangeRate` 모델 및 주문일 기준 환율 조회(`_get_exchange_rate`) 도입, USD 단위 통일. 이 SPEC은 그 환율 조회 로직을 무수정으로 재사용한다. `SPEC-ORDER-009/spec.md:204`의 NOTE(환율 조회가 필드마다 최대 1회씩 중복 호출되는 것을 "성능상 허용 범위"로 명시적으로 수용한 전례)를 설계 결정 F의 근거로 삼는다.

---

## 요구사항 (EARS)

### 모듈 1 — 상수

**REQ-COST-001** (Ubiquitous): The system shall define the shipping rate (5.45 USD per 1000g), the Korea-warehouse base fee (1250 KRW per order), and the Korea-warehouse per-additional-book fee (500 KRW) as named constants collocated with `OrderDetailSerializer` in `backend/order/serializers.py`.

### 모듈 2 — 배송비

**REQ-COST-002** (Ubiquitous): For every order, the system shall compute `total_weight_grams` as the sum, over all of that order's line items, of each line item's `grams` (treated as 0 when null) multiplied by its `quantity` (treated as 0 when null).

**REQ-COST-003** (Ubiquitous): The system shall compute `shipping_cost_usd` as the shipping rate constant multiplied by `total_weight_grams`, divided by 1000, retained as an exact (non-quantized) Decimal for use in the margin calculation.

### 모듈 3 — 한국창고비

**REQ-COST-004** (Ubiquitous): For every order, the system shall compute `total_book_count` as the sum, over all of that order's line items, of each line item's `quantity` (treated as 0 when null).

**REQ-COST-005** (State-Driven): While `total_book_count` is greater than zero, the system shall compute `korea_warehouse_krw` as the Korea-warehouse base fee plus the per-additional-book fee multiplied by (`total_book_count` minus 1).

**REQ-COST-006** (State-Driven): While `total_book_count` equals zero, the system shall compute `korea_warehouse_krw` as 0.

**REQ-COST-007** (Ubiquitous): The system shall compute `korea_warehouse_usd` as `korea_warehouse_krw` divided by the same exchange rate the order's `confirmed_price` conversion uses, retained as an exact (non-quantized) Decimal for use in the margin calculation.

### 모듈 4 — 마진 공식

**REQ-COST-008** (Ubiquitous) [MODIFY]: The system shall compute `margin_usd` as `total_price_usd` minus `confirmed_cost_usd` minus `shipping_cost_usd` minus `korea_warehouse_usd`.

**REQ-COST-009** (Unwanted): If no `ExchangeRate` record is found for the order via the existing fallback lookup, then the system shall return `null` for `margin_amount`, `margin_rate`, `shipping_cost`, `korea_warehouse_cost`, and `total_weight_grams`.

**REQ-COST-010** (Unwanted): If no line item of the order has a non-null `confirmed_price`, then the system shall return `null` for `margin_amount`, `margin_rate`, `shipping_cost`, `korea_warehouse_cost`, and `total_weight_grams`.

### 모듈 5 — 비용 내역 노출

**REQ-COST-011** (Ubiquitous): `OrderDetailSerializer` shall expose `shipping_cost` as `shipping_cost_usd` quantized to 2 decimal places with ROUND_HALF_UP, returned as a string, following the same convention `margin_amount` already uses.

**REQ-COST-012** (Ubiquitous): `OrderDetailSerializer` shall expose `korea_warehouse_cost` as `korea_warehouse_usd` quantized to 2 decimal places with ROUND_HALF_UP, returned as a string, following the same convention `margin_amount` already uses.

**REQ-COST-013** (Ubiquitous): `OrderDetailSerializer` shall expose `total_weight_grams` as the integer computed under REQ-COST-002, unquantized.

**REQ-COST-014** (Ubiquitous): `OrderListSerializer` shall not expose `shipping_cost`, `korea_warehouse_cost`, or `total_weight_grams`.

### 모듈 6 — 성능 불변식

**REQ-COST-015** (Ubiquitous): The system shall compute the full cost breakdown for an order — including the `total_weight_grams`/`total_book_count`/`confirmed_cost_krw` aggregation over `obj.line_items.all()` and the underlying `ExchangeRate` lookup — **at most once per serialized order**, regardless of how many of the five dependent fields (`margin_amount`, `margin_rate`, `shipping_cost`, `korea_warehouse_cost`, `total_weight_grams`) are requested for that order, and shall not issue a separate database query dedicated to line items beyond the queryset the view's existing `prefetch_related` already populates.

### 모듈 7 — 프론트엔드 표시

**REQ-COST-016** (Event-Driven): When `OrderDetailPage` renders an order, the system shall display `shipping_cost` and `korea_warehouse_cost` as two additional lines adjacent to the existing 마진/마진율 display, each formatted as `"{value} USD"` when non-null and `"—"` when null, matching the existing `margin_amount` display convention.

**REQ-COST-017** (Ubiquitous): The `OrderDetail` TypeScript interface shall declare `shipping_cost: string | null` and `korea_warehouse_cost: string | null`, matching the backend field names and null semantics.

### 모듈 8 — 범위 경계 및 확장 지점

**REQ-COST-018** (Ubiquitous): The system shall not compute, store, or expose a US-warehouse-fee value in this SPEC.

**REQ-COST-019** (Ubiquitous): The cost computation shall be structured as a single private helper that returns a named bundle of cost components (at minimum `total_price_usd`, `confirmed_cost_usd`, `shipping_cost_usd`, `korea_warehouse_usd`, `margin_usd`, `total_weight_grams`), so that a later SPEC can add a fourth cost term to that bundle without changing the five field-getter methods' control flow.

### 모듈 9 — confirmed_cost / total_cost 노출 (v1.3.0)

**REQ-COST-020** (Ubiquitous): `OrderDetailSerializer` shall expose `confirmed_cost` as `confirmed_cost_usd` quantized to 2 decimal places with ROUND_HALF_UP, returned as a string, following the same convention `shipping_cost` already uses.

**REQ-COST-021** (Ubiquitous) [HARD]: `OrderDetailSerializer` shall expose `total_cost` as `confirmed_cost_usd + shipping_cost_usd + korea_warehouse_usd`, computed from the three **unrounded** Decimal components and quantized exactly once to 2 decimal places with ROUND_HALF_UP, returned as a string. The system shall NOT derive `total_cost` by summing the already-quantized `confirmed_cost`, `shipping_cost`, and `korea_warehouse_cost` string values (design decision B, extended) — the two can differ by a cent (AC-COST-015 demonstrates this concretely).

**REQ-COST-022** (Ubiquitous): `confirmed_cost` and `total_cost` shall be computed through the same memoized `_compute_cost_breakdown` helper as the other five cost fields (REQ-COST-015), without adding a new `ExchangeRate` query or a new line-item iteration.

**REQ-COST-023** (Ubiquitous): The `OrderDetail` TypeScript interface shall declare `confirmed_cost: string | null` and `total_cost: string | null`, matching the backend field names and null semantics.

**REQ-COST-024** (Ubiquitous): `margin_usd` and `total_cost_usd` shall be computed from the same underlying unrounded Decimal components such that `margin_usd + total_cost_usd == total_price_usd` holds exactly before quantization (i.e. the existing margin formula, REQ-COST-008, is not altered by this module).

**REQ-COST-025** (Unwanted): If no `ExchangeRate` record is found for the order, then the system shall return `null` for `confirmed_cost` and `total_cost`, joining the existing null-gate field set (REQ-COST-009).

**REQ-COST-026** (Unwanted): If no line item of the order has a non-null `confirmed_price`, then the system shall return `null` for `confirmed_cost` and `total_cost`, joining the existing null-gate field set (REQ-COST-010).

### 모듈 10 — 결제 정보 화면 재구성 (v1.3.0)

**REQ-COST-027** (Event-Driven): When `OrderDetailPage` renders an order's 결제 정보 section, the system shall display the rows in this order: `최종 결제 금액`, `비용 합계` (`total_cost`), `원가 (확정 단가 합계)` (`confirmed_cost`), `배송비` (`shipping_cost`), `한국물류` (`korea_warehouse_cost`), `마진` (`margin_amount`), `마진율` (`margin_rate`). `total_cost`/`confirmed_cost` shall follow the same `"{value} USD"` / `"—"` convention as the other cost fields.

**REQ-COST-028** (Ubiquitous): The `원가`, `배송비`, and `한국물류` rows shall be rendered visually subordinate to (indented and lower-emphasis than) the `비용 합계` row, reusing the codebase's existing Tailwind utility conventions (indentation + opacity-modified `text-muted-foreground`) rather than introducing new CSS.

**REQ-COST-029** (Ubiquitous): The Korea-warehouse cost row label shall read `한국물류` (renamed from `한국창고비`).

### 모듈 11 — 적용 환율 노출 (v1.4.0)

**REQ-COST-030** (Ubiquitous): `OrderDetailSerializer` shall expose `exchange_rate` as the `ExchangeRate.rate` value applied by `_get_exchange_rate(obj)`, returned as a string.

**REQ-COST-031** (Ubiquitous): `OrderDetailSerializer` shall expose `exchange_rate_date` as the applied `ExchangeRate` record's `effective_date`, formatted as an ISO `YYYY-MM-DD` string.

**REQ-COST-032** (Unwanted): If `_get_exchange_rate(obj)` returns `None` (no `ExchangeRate` record found at or before the order date, or the order has no `shopify_created_at`), then the system shall return `null` for `exchange_rate` and `exchange_rate_date`.

**REQ-COST-033** (Ubiquitous) [HARD]: `exchange_rate` and `exchange_rate_date` shall be non-null whenever `_get_exchange_rate(obj)` returns a record, **independent of** whether any line item has a `confirmed_price` — these two fields shall NOT share the `has_any_confirmed` gate that `margin_amount`/`margin_rate`/`shipping_cost`/`korea_warehouse_cost`/`total_weight_grams`/`confirmed_cost`/`total_cost` share (design decision D applies only to those seven fields, not to these two). This lets a reader distinguish "no exchange rate exists for this date" (`exchange_rate` is `null`) from "rate exists but nothing is confirmed yet" (`exchange_rate` is non-null, `margin_amount` is `null`).

**REQ-COST-034** (Ubiquitous): The system shall not issue more than one `ExchangeRate` query per serialized order. `_get_exchange_rate` shall be memoized per order object so that `exchange_rate`/`exchange_rate_date` and the cost-breakdown helper (`_compute_cost_breakdown_uncached`) share a single lookup, preserving the invariant established by REQ-COST-015.

**REQ-COST-035** (Event-Driven): When `OrderDetailPage` renders an order's 결제 정보 section, the system shall display `적용 환율` as an additional row at the bottom of the section, after `마진율` and OUTSIDE the indented `원가`/`배송비`/`한국물류` sub-item group (it is calculation metadata, not a cost component). It shall render in the same de-emphasized style as the cost sub-items (`text-muted-foreground/70 text-xs`) but without their indentation, formatted as `"{rate} KRW/USD ({date})"` when both fields are non-null and `"—"` when either is `null`. The rate shall be formatted with `toLocaleString()`, matching the file's existing number-formatting convention.

**REQ-COST-036** (Ubiquitous): The `OrderDetail` TypeScript interface shall declare `exchange_rate: string | null` and `exchange_rate_date: string | null`, matching the backend field names and null semantics.

---

## 인수 기준

[HARD] 각 인수 기준은 손으로 계산한 정확한 숫자를 단정한다 — "마진이 계산된다"류의 판별력 없는 서술은 쓰지 않는다. 각 항목은 자신을 깨뜨리는 mutation을 명시한다. 실행 가능한 Given/When/Then 시나리오는 `acceptance.md`에 있으며 동일한 `Traces:` 목록을 인용한다.

**AC-COST-001** (State-Driven) — 단일 SKU 3권 주문의 한국창고비. Traces: REQ-COST-004, REQ-COST-005, REQ-COST-008, REQ-COST-011, REQ-COST-012, REQ-COST-013. **While** an order has `total_price=100.00 USD`, a valid `ExchangeRate(rate=1000.00)`, and one line item with `quantity=3, confirmed_price=10000.00`/unit, `grams=0`, the system **shall** report `margin_amount="67.75"`, `korea_warehouse_cost="2.25"`(`korea_warehouse_krw = 1250 + 500×2 = 2250`, `/1000 = 2.25`), `shipping_cost="0.00"`, and `total_weight_grams=0`.
*Mutation*: base fee 없이 권수당 정액(`500×total_book_count`)으로 잘못 구현하면 `korea_warehouse_krw=1500`이 되어 `korea_warehouse_cost="1.50"`으로 어긋난다. `-1`을 빠뜨리고 `1250+500×total_book_count`로 구현하면 `korea_warehouse_krw=2750`이 되어 `korea_warehouse_cost="2.75"`로 어긋난다. 둘 다 정답(`"2.25"`)과 다르다.

**AC-COST-002** (State-Driven) — 여러 라인아이템에 걸친 권수 합산은 단일 SKU와 동일한 결과를 낸다. Traces: REQ-COST-004, REQ-COST-005, REQ-COST-008. **While** an order has the same `total_price`/`rate` as AC-COST-001 but the line item is split into two — `quantity=2`+`quantity=1`, each `confirmed_price=10000.00`/unit, `grams=0` — the system **shall** report `margin_amount="67.75"`, AC-COST-001과 **정확히 동일**한 값.
*Mutation*: 한국창고 기본료(1250원)를 주문당이 아니라 **라인아이템당** 적용하면 `korea_warehouse_krw = (1250+500×1) + (1250+500×0) = 1750+1250 = 3000`이 되어 `korea_warehouse_cost="3.00"`, `margin_amount="67.00"`으로 AC-COST-001과 달라진다 — 이 mutation은 단일 라인아이템 픽스처만으로는 잡히지 않고 이 AC가 잡는다.

**AC-COST-003** (State-Driven) — 무게 가중 배송비와 노출 필드의 반올림 아티팩트. Traces: REQ-COST-002, REQ-COST-003, REQ-COST-008, REQ-COST-011, REQ-COST-012, REQ-COST-013. **While** an order has `total_price=200.00 USD`, `rate=1000.00`, and one line item with `quantity=3, grams=500, confirmed_price=10000.00`/unit, the system **shall** report `total_weight_grams=1500`, `shipping_cost="8.18"`(정확값 `8.175`를 ROUND_HALF_UP), `korea_warehouse_cost="2.25"`, `margin_amount="159.58"`, `margin_rate="79.79"`.
*알려진 반올림 아티팩트*: `total_price(200.00) − confirmed_cost(30.00) − shipping_cost(8.18) − korea_warehouse_cost(2.25) = 159.57`로, 노출된 `margin_amount`(`159.58`)와 **1센트 차이**가 난다 — `margin_usd`는 양자화되지 않은 정확값(`8.175`)으로 계산되고, `shipping_cost`는 그 값의 별도 양자화 사본이기 때문이다(설계 결정 B). 이 차이는 구현 결함이 아니라 의도된 설계다.
*Mutation*: `shipping_cost_usd` 계산에 `total_weight_grams`를 kg 단위로 변환하지 않고(`/1000` 누락) 그램 그대로 곱하면 `shipping_cost="8175.00"`이 되어 `margin_amount`가 음수에 가까운 값으로 크게 어긋난다.

**AC-COST-004** (State-Driven) — `grams=None`과 `grams=0`은 동일하게 0으로 처리되며 마진이 `null`이 되지 않는다. Traces: REQ-COST-002. **While** an order has `total_price=50.00 USD`, `rate=1000.00`, and two line items — A: `quantity=2, grams=None, confirmed_price=5000.00`/unit; B: `quantity=1, grams=0, confirmed_price=5000.00`/unit — the system **shall** respond with HTTP 200 and report `margin_amount="32.75"`(`null`이 아님), `total_weight_grams=0`, `shipping_cost="0.00"`.
*Mutation*: `grams`가 `None`일 때 `0`으로 치환하지 않고 그대로 곱셈에 사용하면 `TypeError`가 발생하거나(구현에 따라) 요청이 500 에러로 실패한다 — 이 AC의 200 응답 자체가 판별력을 갖는다.

**AC-COST-005** (State-Driven) — 미확정 라인아이템도 무게·권수 합산에는 포함되지만 매입원가 합산에는 제외된다. Traces: REQ-COST-002, REQ-COST-004, REQ-COST-008. **While** an order has `total_price=100.00 USD`, `rate=1000.00`, and two line items — A(확정): `quantity=2, confirmed_price=10000.00`/unit, `grams=300`; B(미확정): `quantity=1, confirmed_price=null`, `grams=600` — the system **shall** report `total_weight_grams=1200`(A의 600 + B의 600), `margin_amount="71.21"`(`confirmed_cost_usd=20.00`, B는 원가 합산에서 제외; `shipping_cost_usd=6.54`; `korea_warehouse_usd=2.25`, 권수 합산은 B의 1권을 포함해 `total_book_count=3`).
*Mutation*: 무게/권수 집계 루프를 `confirmed_price is not None` 조건 안으로 잘못 이동하면(원가 합산 루프와 게이트를 공유) B가 무게·권수에서도 빠져 `total_weight_grams=600`, `total_book_count=2`(→ `korea_warehouse_krw=1750`, `usd=1.75`), `margin_amount="74.98"`로 어긋난다(`100-20-3.27-1.75=74.98`).

**AC-COST-006** (Unwanted) — 환율 없음 → 5개 필드 전부 `null`(기존 동작 보존 + 확장). Traces: REQ-COST-009. **If** no `ExchangeRate` record exists for an order (AC-COST-001과 동일한 라인아이템 구성이지만 해당 주문일 이전 어떤 날짜에도 레코드가 없음), **then** the system **shall** include the keys `margin_amount`, `margin_rate`, `shipping_cost`, `korea_warehouse_cost`, `total_weight_grams` in the response **and** report `null` for every one of them — 단정은 반드시 키 존재(`"shipping_cost" in response`)와 값이 `null`이라는 것 둘 다를 확인해야 한다. `res.data.get(...)`처럼 키 부재와 `null` 값을 구분하지 못하는 조회는 이 AC의 판별력을 무효화한다(D6).
*Mutation*: `shipping_cost`/`total_weight_grams` 계산을 환율 게이트 밖으로 독립시키면(무게 계산은 환율이 필요 없으므로) 이 두 필드만 값을 반환해 이 AC가 실패한다 — 설계 결정 D(단일 게이트)의 판별 지점.

**AC-COST-007** (Unwanted) — 확정 매입가 전무 → 5개 필드 전부 `null`(기존 동작 보존 + 확장). Traces: REQ-COST-010. **If** no line item of an order has a non-null `confirmed_price`(유효한 `ExchangeRate`는 있지만 라인아이템 `quantity=3, grams=500, confirmed_price=null`로 무게 데이터는 존재), **then** the system **shall** include the keys for all five fields in the response **and** report `null` for every one of them — AC-COST-006과 동일한 키 존재 + `null` 값 이중 단정 요건이 적용된다(D6).
*Mutation*: AC-COST-006과 동일한 논리 — `shipping_cost`/`total_weight_grams`가 `has_any_confirmed` 게이트 밖에서 독립 계산되면 무게 데이터가 존재하므로 값을 반환해버려 이 AC가 실패한다. 별도로, 신규 필드를 아예 구현하지 않아도(`Meta.fields`에서 누락) `res.data.get("shipping_cost")`는 `None`을 반환하므로, 키 존재 단정이 없으면 이 미구현 상태가 정상 통과해버린다 — 키 존재 단정이 이 mutation의 유일한 판별 수단이다.

**AC-COST-008** (State-Driven) — `total_book_count == 0`일 때 한국창고비는 0원이다(기본료를 청구하지 않는다). Traces: REQ-COST-006. **While** an order has `total_price=50.00 USD`, `rate=1000.00`, and one line item with `quantity=null, confirmed_price=5000.00`/unit, `grams=null`, the system **shall** report `korea_warehouse_cost="0.00"` and `margin_amount="50.00"`(모든 비용 항이 0 — `quantity=null`이므로 `confirmed_cost_usd`도 0).
*Mutation*: REQ-COST-006의 0-분기 없이 공식을 그대로 적용하면(`1250 + 500×max(0-1,0) = 1250 + 500×0 = 1250`) `korea_warehouse_cost="1.25"`, `margin_amount="48.75"`로 어긋난다 — `max(-1,0)=0`이 base fee 자체를 상쇄하지 못한다는 점이 이 mutation의 핵심.

**AC-COST-009** (State-Driven) — 쿼리 수 불변식: 라인아이템 수와 무관하게 쿼리 수가 일정하고, 신규 필드가 라인아이템 재쿼리·환율 재조회를 추가하지 않는다. Traces: REQ-COST-015. **While** (워밍업으로 무관한 주문 1건을 먼저 조회해 첫 요청에서만 발생하는 쿼리를 측정 창 밖으로 뺀 뒤) 주문 X(라인아이템 1개, 확정+환율 유효)와 주문 Y(라인아이템 5개, 전부 확정+동일 환율)를 각각 `GET /api/orders/{pk}/`로 조회하며 쿼리를 캡처할 때, the system **shall** issue (a) X와 Y 양쪽에 대해 **동일하고, 구현 시점에 실측해 고정한 절대값과 일치하는** 총 쿼리 수, (b) `LineItem` 테이블(`db_table = "orders_line_item"`, `backend/order/models.py:240-241`)을 정확히 매칭하는(단순 부분 문자열이 아니라 `orders_line_item(?!_)` 정규식 또는 `connection.ops.quote_name("orders_line_item")` 완전 일치 — `LineItemNote.db_table = "orders_line_item_note"`(`models.py:297`)가 `orders_line_item`의 상위 문자열이므로 단순 `in` 검사는 이 테이블까지 잘못 세어 정상 구현에서도 2를 반환한다) 쿼리를 정확히 1개, (c) `ExchangeRate` 테이블(`db_table = "orders_exchangerate"`, `backend/order/models.py:507`)을 참조하는 쿼리를 정확히 1개 — 두 주문 모두에 대해.
*Mutation*: (a)는 무게/권수 집계를 라인아이템별 개별 쿼리로 구현하면(N+1) X와 Y의 쿼리 수가 달라져 잡힌다. (a)의 절대값 고정은 아이템 수와 무관한 상수 +1 쿼리(예: `obj.line_items.all()` 재사용 대신 신규 `LineItem.objects.filter(order=obj).aggregate(...)` 호출)도 잡는다 — X와 Y가 서로 같다는 상대 비교만으로는(둘 다 +1이 되어 여전히 같으므로) 이 mutation을 잡지 못하기 때문에 절대값 고정이 필수다. (b)는 위 상수 +1 mutation이 `orders_line_item` 정확 매칭 쿼리 수를 2로 만들어 별도로 잡는다. (c)는 REQ-COST-015의 "주문 직렬화당 최대 1회" 요건을 어기고 5개 게터가 헬퍼를 캐시 없이 독립 호출하면(설계 결정 F) `ExchangeRate` 쿼리가 최대 5개까지 늘어나는 것을 잡는다 — (a)의 절대값도 이 mutation에서 어긋나지만, (c)가 원인을 `ExchangeRate` 테이블로 직접 지목해 진단을 좁힌다.

**AC-COST-010** (Event-Driven) — 목록 API는 비용 내역을 노출하지 않는다(기존 마진 미노출 관례 확장). Traces: REQ-COST-014. **When** a client requests `GET /api/orders/`(목록), the system **shall not** include the keys `shipping_cost`, `korea_warehouse_cost`, `total_weight_grams` in any item of the response(기존 `margin_amount`/`margin_rate` 미노출과 동일).
*Mutation*: `OrderListSerializer.Meta.fields`에 신규 필드를 실수로 추가하면 응답에 해당 키가 나타나 이 AC가 실패한다.

**AC-COST-011** (Event-Driven) — 프론트엔드가 배송비·한국창고비를 마진 옆에 표시한다. Traces: REQ-COST-016, REQ-COST-017. **When** `OrderDetailPage` renders an order whose API response matches AC-COST-003's shape(`margin_amount="159.58"`, `shipping_cost="8.18"`, `korea_warehouse_cost="2.25"`), the system **shall** display "8.18 USD" and "2.25 USD" text inside the existing 마진/마진율 표시 영역. **While** `shipping_cost` is `null`, the system **shall** display "—"(기존 `margin_amount=null` 표시와 동일한 폴백).
*픽스처 참고(D3)*: 기존 표시 관례는 `` `${Number(data.margin_amount).toLocaleString()} USD` ``(`OrderDetailPage.tsx:515-517`)다. `Number("0.00").toLocaleString()`은 `"0"`이므로 `shipping_cost="0.00"` 픽스처를 쓰면 렌더 결과가 "0.00 USD"가 아니라 "0 USD"가 되어 이 AC가 정상 구현에서도 실패한다 — `"8.18"`은 `Number("8.18").toLocaleString() === "8.18"`이라 왕복이 보존되므로 이 값을 쓴다.
*Mutation*: 신규 필드를 `OrderDetail` 타입에 추가하지 않고 컴포넌트에서 `data.shipping_cost`에 접근하면 TypeScript 컴파일이 실패한다(회귀 게이트 — `tsc -b`, `npm run build`가 실행하는 실제 명령. `tsconfig.json`은 `"files": []`인 솔루션 파일이라 단독 `tsc --noEmit`은 아무것도 타입 체크하지 않는다). 표시 로직에서 `null` 폴백을 빠뜨리면 두 번째 절이 "null USD" 또는 빈 문자열을 렌더링해 실패한다.

**AC-COST-012** (State-Driven) — 한국창고비 환산은 실제 환율을 사용한다(하드코딩된 나눗셈 상수가 아니다). Traces: REQ-COST-007. **While** an order has `total_price=100.00 USD`, a valid `ExchangeRate(rate=1250.00)`(AC-COST-001~011과 다른 환율값), and one line item with `quantity=3, confirmed_price=12500.00`/unit, `grams=0`, the system **shall** report `korea_warehouse_cost="1.80"` and `margin_amount="68.20"`(`confirmed_cost_usd = 37500/1250 = 30.00`; `korea_warehouse_krw = 2250`, `/1250 = 1.80`; `margin_usd = 100-30-0-1.80 = 68.20`).
*이 AC가 필요한 이유(D4)*: AC-COST-001~011은 전부 `rate=1000.00`을 공유한다. `korea_warehouse_krw / Decimal("1000")`처럼 나눗셈 상수를 실제 `er.rate` 대신 하드코딩해도(한국창고비 공식 자체가 1000 단위 숫자들을 다루므로 그럴듯한 실수다) 그 값과 `1000.00`이 우연히 일치해 T1~T11 전부를 통과한다 — 이전 버전 spec.md가 "AC-COST-001이 묵시적으로 커버한다"고 주장했던 것은 거짓이었다(감사 결과 D4). `rate=1250.00`에서는 하드코딩된 `/1000` 구현이 `korea_warehouse_cost="2.25"`(오답, `2250/1000`)를 반환해 정답(`"1.80"`)과 명확히 갈린다.
*Mutation*: `korea_warehouse_usd = korea_warehouse_krw / Decimal("1000")`으로 하드코딩하면 `korea_warehouse_cost="2.25"`, `margin_amount="67.75"`가 되어 정답과 어긋난다.

**AC-COST-013** (State-Driven) — ROUND_HALF_UP은 ROUND_HALF_EVEN과 구별된다. Traces: REQ-COST-003, REQ-COST-011. **While** an order has `total_price=50.00 USD`, a valid `ExchangeRate(rate=1000.00)`, and one line item with `quantity=1, grams=500, confirmed_price=10000.00`/unit, the system **shall** report `shipping_cost="2.73"`(정확값 `5.45×500/1000 = 2.725`를 ROUND_HALF_UP).
*이 AC가 필요한 이유(D11)*: AC-COST-003의 반올림 경계값(`8.175→8.18`, `159.575→159.58`)은 반올림 자릿수 앞의 숫자가 홀수(7)라서 ROUND_HALF_UP과 ROUND_HALF_EVEN(은행가 반올림)이 우연히 같은 결과를 낸다 — HALF_EVEN 구현도 두 AC를 전부 통과한다. `2.725`는 앞자리가 짝수(2)라서 HALF_UP은 올림(`"2.73"`)하고 HALF_EVEN은 이미 짝수인 `"2.72"`를 유지한다 — 두 방식이 실제로 갈리는 유일한 케이스다.
*Mutation*: `ROUND_HALF_EVEN`으로 양자화하면 `shipping_cost="2.72"`가 되어 정답(`"2.73"`)과 어긋난다.

**AC-COST-014** (State-Driven) — `confirmed_cost`는 확정 매입원가(USD)를 정확히 반영한다. Traces: REQ-COST-020, REQ-COST-022. **While** an order has the same fixture as AC-COST-001(`total_price=100.00`, `rate=1000.00`, `quantity=3, confirmed_price=10000.00`/unit, `grams=0`), the system **shall** report `confirmed_cost="30.00"`(`confirmed_cost_usd = 10000×3/1000 = 30.00`, AC-COST-001이 이미 감사한 중간값).
*Mutation*: `confirmed_cost`를 노출하지 않거나 다른 값(`total_price_usd`, `margin_usd` 등)을 반환하면 어긋난다.

**AC-COST-015** (State-Driven) [HARD] — `total_cost`는 반올림 전 세 항의 정확한 합을 서버가 한 번만 양자화해 계산한다(프론트엔드가 반올림된 세 필드를 합산하지 않는다). Traces: REQ-COST-021, REQ-COST-023. **While** an order has `total_price=100.00 USD`, `rate=1000.00`, and one line item with `quantity=1, confirmed_price=10005.00`/unit, `grams=500`, the system **shall** report `confirmed_cost="10.01"`(정확값 `10.005`), `shipping_cost="2.73"`(정확값 `2.725`), `korea_warehouse_cost="1.25"`(정확값, 반올림 없음), and `total_cost="13.98"`(정확값 `10.005+2.725+1.25=13.980`을 **한 번만** 양자화).
*이 AC가 필요한 이유*: 세 노출 필드(반올림됨)를 그대로 합산하면 `"10.01"+"2.73"+"1.25"="13.99"`가 되어 정답(`"13.98"`)과 **1센트** 어긋난다 — `confirmed_cost_usd`(`.005`)와 `shipping_cost_usd`(`.725`)가 각각 개별 반올림에서 올림되어 `+0.005`가 두 번 누적되지만, 반올림 전 정확값의 합(`13.980`)은 이미 2자리 정밀도라 그 누적이 발생하지 않기 때문이다. 이 픽스처가 REQ-COST-021의 [HARD] 요건("반올림 전 값의 합을 한 번만 양자화")을 직접 판별하는 유일한 시나리오다.
*Mutation*: `total_cost`를 `Decimal(confirmed_cost)+Decimal(shipping_cost)+Decimal(korea_warehouse_cost)`(양자화된 값의 재합산)로 구현하면 `total_cost="13.99"`가 되어 정답과 어긋난다.

**AC-COST-016** (Ubiquitous) — `margin_amount == total_price − total_cost`(1센트 이내). Traces: REQ-COST-021, REQ-COST-024. **While** an order has AC-COST-015와 동일한 픽스처, the system **shall** report `margin_amount="86.02"`(`margin_usd = 100-10.005-2.725-1.25 = 86.020`), and `|(\text{total\_price} - \text{total\_cost}) - \text{margin\_amount}| \le 0.01`(이 픽스처에서는 `100.00-13.98=86.02`로 정확히 일치).
*Mutation*: `margin_usd` 공식이 변경되거나 `total_cost_usd`가 잘못 계산되면 이 차이가 1센트를 초과해 어긋난다.

**AC-COST-017** (Unwanted) — 환율 없음 → `confirmed_cost`/`total_cost`도 `null`(기존 5필드 게이트에 합류). Traces: REQ-COST-025. **If** no `ExchangeRate` record exists for an order(AC-COST-006과 동일 조건), **then** the system **shall** include the keys `confirmed_cost`, `total_cost` in the response **and** report `null` for both — 키 존재 + `null` 값 이중 단정(D6 계승).
*Mutation*: 두 필드를 구현하지 않으면 키 존재 단정이 실패한다. 게이트를 공유하지 않고 독립 계산하면 값이 반환되어 `null` 단정이 실패한다.

**AC-COST-018** (Unwanted) — 확정 매입가 전무 → `confirmed_cost`/`total_cost`도 `null`. Traces: REQ-COST-026. **If** no line item has a non-null `confirmed_price`(AC-COST-007과 동일 조건), **then** the system **shall** include the keys for both fields **and** report `null` for both.
*Mutation*: AC-COST-017과 대칭 — `has_any_confirmed` 게이트 밖에서 독립 계산되면 어긋난다.

**AC-COST-019** (Event-Driven) — 결제 정보 섹션이 새 순서·라벨로 재구성되고, 비용 세부항목은 시각적으로 하위 표시된다. Traces: REQ-COST-023, REQ-COST-027, REQ-COST-028, REQ-COST-029. **When** `OrderDetailPage` renders an order whose API response includes `margin_amount="159.58", margin_rate="79.79", shipping_cost="8.18", korea_warehouse_cost="2.25", confirmed_cost="30.00", total_cost="40.43"`(AC-COST-003 기반), the system **shall** render the rows in DOM order `최종 결제 금액 → 비용 합계 → 원가 (확정 단가 합계) → 배송비 → 한국물류 → 마진 → 마진율`, render `한국물류`(NOT `한국창고비`), and render `원가`/`배송비`/`한국물류`의 컨테이너를 `비용 합계`보다 시각적으로 옅고 들여쓴 스타일로 표시한다. `total_cost`/`confirmed_cost`가 `null`이면 각각 `"—"`를 표시한다.
*Mutation*: 순서를 바꾸거나 라벨을 갱신하지 않으면(`한국창고비` 잔존) 실패한다. 세 세부항목에 들여쓰기·저채도 스타일을 적용하지 않으면 시각적 판별력이 없어진다.

**AC-COST-020** (State-Driven) — 주문일 자체에 환율 레코드가 있는 경우 `exchange_rate`/`exchange_rate_date`가 정확한 값을 반환한다. Traces: REQ-COST-030, REQ-COST-031. **While** an order's `shopify_created_at` date has its own `ExchangeRate(effective_date=주문일, rate=1427.05)` record, the system **shall** report `exchange_rate="1427.05"` and `exchange_rate_date=` 주문일의 ISO 문자열.
*Mutation*: `exchange_rate`에 `margin_usd`나 다른 값을 반환하거나, `exchange_rate_date`를 주문일을 그대로 에코하는 방식으로(레코드의 `effective_date`를 실제로 조회하지 않고) 구현하면 이 AC 자체는 통과할 수 있다 — 이 mutation은 AC-COST-021이 전담해서 잡는다.

**AC-COST-021** (State-Driven) [HARD] — 폴백 발생 시 `exchange_rate_date`는 주문일이 아니라 실제 적용된 레코드의 `effective_date`를 반환한다(이 기능 전체의 판별 테스트). Traces: REQ-COST-030, REQ-COST-031, REQ-COST-034. **While** an order is dated `D`이고 `D` 당일에는 `ExchangeRate` 레코드가 없으며 `D-3`에만 레코드(`rate=1300.00`)가 존재할 때, the system **shall** report `exchange_rate="1300.00"`, `exchange_rate_date=(D-3)의 ISO 문자열`, **and** `exchange_rate_date != D의 ISO 문자열`.
*Mutation*: `exchange_rate_date`를 `obj.shopify_created_at.date()`(주문일)로 잘못 구현하면(폴백 레코드의 `effective_date`가 아니라 주문일을 그대로 반환) `exchange_rate_date == D`가 되어 정답(`D-3`)과 어긋난다 — 이 mutation이야말로 이 기능이 존재하는 이유(폴백을 눈에 보이게 만드는 것)를 직접 무효화하므로, 이 AC가 전체 기능의 핵심 판별 지점이다.

**AC-COST-022** (State-Driven) [HARD] — `margin_amount`가 `null`이어도(확정 매입가 전무) `exchange_rate`/`exchange_rate_date`는 `null`이 아니다(별도 게이트의 판별 테스트). Traces: REQ-COST-033. **While** an order has a valid `ExchangeRate`이지만 어떤 라인아이템도 `confirmed_price`가 없을 때(AC-COST-007과 동일 조건), the system **shall** report `margin_amount=null`이면서 동시에 `exchange_rate`/`exchange_rate_date`는 **non-null**.
*Mutation*: 이 두 필드를 `_compute_cost_breakdown`(`has_any_confirmed` 게이트를 가진 기존 헬퍼)을 거쳐 구현하면 `margin_amount`와 동일하게 `null`이 반환되어 이 AC가 실패한다 — 별도의, 더 좁은 게이트(`_get_exchange_rate(obj) is None`만)를 요구하는 REQ-COST-033의 직접 판별 지점.

**AC-COST-023** (Unwanted) — 환율 레코드 자체가 없을 때만 `exchange_rate`/`exchange_rate_date`가 `null`이다. Traces: REQ-COST-032. **If** no `ExchangeRate` record exists at or before the order date(AC-COST-006과 동일 조건), **then** the system **shall** include the keys `exchange_rate`, `exchange_rate_date` in the response **and** report `null` for both — 키 존재 + `null` 값 이중 단정(D6 계승, `.get(...)` 대신 `"exchange_rate" in res.data`).
*Mutation*: 두 필드를 구현하지 않으면(`Meta.fields` 누락) 키 존재 단정이 실패한다.

**AC-COST-024** (Event-Driven) — 프론트엔드가 적용 환율을 마진율 다음, 비용 세부항목 그룹 밖에 표시한다. Traces: REQ-COST-035, REQ-COST-036. **When** `OrderDetailPage` renders an order whose API response includes `exchange_rate="1427.05", exchange_rate_date="2026-08-03"`, the system **shall** display `"1,427.05 KRW/USD (2026-08-03)"` in a row labeled `적용 환율`, positioned in DOM order after `마진율`, with a container class that does NOT include a `pl-` indentation class. **While** `exchange_rate` or `exchange_rate_date` is `null`, the system **shall** display `"—"`.
*Mutation*: `OrderDetail` 타입에 두 필드를 추가하지 않고 컴포넌트에서 접근하면 TypeScript 컴파일이 실패한다(`tsc -b` 회귀 게이트). 표시 위치를 비용 세부항목의 `pl-3` 그룹 안에 넣으면(계산 근거가 아니라 비용 항목처럼 보이게 됨) 들여쓰기 부재 단정이 실패한다. `null` 폴백을 빠뜨리면 두 번째 절이 "null KRW/USD (null)" 같은 값을 렌더링해 실패한다.

### 기존 테스트 갱신 대상

이 변경으로 다음 기존 테스트의 기대값이 달라진다 — 새 공식(배송비 + 한국창고비 반영) 적용 결과다. 갱신 대상이 아닌 마진 관련 테스트(`test_margin_amount_is_null_when_all_confirmed_price_null`, `test_margin_null_when_no_exchange_rate`)는 애초에 `null`을 기대하므로 영향이 없다.

| 파일 | 테스트명 | 현재 기대값 | 신규 기대값 |
|---|---|---|---|
| `backend/order/tests/test_spec_008.py` | `test_margin_amount_calculation_with_partial_confirmed` (`:219-237`) | `margin_amount="49981.54"` | `margin_amount="49979.81"`(`total_book_count=3` → `korea_warehouse_usd=2250/1300≈1.7308`; `grams`는 픽스처에 없어 0 → `shipping_cost_usd=0`) |
| `backend/order/tests/test_spec_008.py` | `test_margin_rate_calculation_rounds_to_2_decimal_places` (`:264-286`) | `margin_amount="59963.08"`, `margin_rate="99.94"` | `margin_amount="59961.35"`(`korea_warehouse_usd=2250/1300≈1.7308`); `margin_rate="99.94"`는 **우연히 동일**(반올림 후 값이 같다 — 재검증 필요, 자동으로 통과한다고 가정하지 말 것) |
| `backend/order/tests/test_spec_008.py` | `test_confirmed_price_zero_is_valid_not_null` (`:293-319`) | `margin_amount="20000.00"`, `margin_rate="100.00"` | `margin_amount="19998.65"`, `margin_rate="99.99"`(`quantity=2` → `korea_warehouse_krw=1750` → `usd≈1.3462`) |
| `backend/order/tests/test_spec_009.py` | `test_margin_uses_exchange_rate_for_usd_conversion` (`:160-183`) | `margin_amount="23.08"`, `margin_rate="23.08"` | `margin_amount="21.35"`, `margin_rate="21.35"`(`total_book_count=3` → `korea_warehouse_usd=2250/1300≈1.7308`) |
| `backend/order/tests/test_spec_009.py` | `test_margin_fallback_to_prior_date_rate` (`:186-212`) | `margin_amount="26.56"`, `margin_rate="53.13"` | `margin_amount="25.59"`, `margin_rate="51.17"`(`total_book_count=1` → `korea_warehouse_krw=1250` → `usd=1250/1280=0.9765625`) |

### Traceability 검증표

각 행은 왼쪽 REQ가 오른쪽 AC들의 `Traces:` 목록에 실제로 나열되어 있는지를 그대로 반영한다(감사 D7 — 이전 버전은 AC-COST-008을 REQ-COST-004/008 아래 잘못 나열하고 REQ-COST-007을 "묵시적 커버"로 거짓 주장했다).

| REQ | 커버하는 AC |
|---|---|
| REQ-COST-001 | `plan.md` DoD (상수 존재 여부, 런타임 AC 없음) |
| REQ-COST-002 | AC-COST-003, AC-COST-004, AC-COST-005 |
| REQ-COST-003 | AC-COST-003, AC-COST-013 |
| REQ-COST-004 | AC-COST-001, AC-COST-002, AC-COST-005 |
| REQ-COST-005 | AC-COST-001, AC-COST-002 |
| REQ-COST-006 | AC-COST-008 |
| REQ-COST-007 | AC-COST-012 |
| REQ-COST-008 | AC-COST-001, AC-COST-002, AC-COST-003, AC-COST-005 |
| REQ-COST-009 | AC-COST-006 |
| REQ-COST-010 | AC-COST-007 |
| REQ-COST-011 | AC-COST-001, AC-COST-003, AC-COST-013 |
| REQ-COST-012 | AC-COST-001, AC-COST-003 |
| REQ-COST-013 | AC-COST-001, AC-COST-003 |
| REQ-COST-014 | AC-COST-010 |
| REQ-COST-015 | AC-COST-009 |
| REQ-COST-016 | AC-COST-011 |
| REQ-COST-017 | AC-COST-011 |
| REQ-COST-018 | `plan.md` DoD (git diff — 신규 필드 없음, 런타임 AC 없음) |
| REQ-COST-019 | `plan.md` DoD (코드 리뷰 — 단일 헬퍼 구조, 런타임 AC 없음) |
| REQ-COST-020 | AC-COST-014, AC-COST-015 |
| REQ-COST-021 | AC-COST-015, AC-COST-016 |
| REQ-COST-022 | AC-COST-014, AC-COST-015 |
| REQ-COST-023 | AC-COST-015, AC-COST-019 |
| REQ-COST-024 | AC-COST-016 |
| REQ-COST-025 | AC-COST-017 |
| REQ-COST-026 | AC-COST-018 |
| REQ-COST-027 | AC-COST-019 |
| REQ-COST-028 | AC-COST-019 |
| REQ-COST-029 | AC-COST-019 |
| REQ-COST-030 | AC-COST-020, AC-COST-021 |
| REQ-COST-031 | AC-COST-020, AC-COST-021 |
| REQ-COST-032 | AC-COST-023 |
| REQ-COST-033 | AC-COST-022 |
| REQ-COST-034 | AC-COST-021, `plan.md`/`test_spec_021.py::test_t9`(AC-COST-009) 무수정 재통과 (쿼리 수 불변식) |
| REQ-COST-035 | AC-COST-024 |
| REQ-COST-036 | AC-COST-024 |

19개 요구사항 중 16개가 13개 인수 기준으로 직접 커버된다. 나머지 3개(REQ-COST-001, 018, 019)는 구조/범위 제약이며 `plan.md`의 완료 조건으로 검증한다. **v1.3.0 확장**: REQ-COST-020~029(10개)가 AC-COST-014~019(6개)로 커버된다 — 전부 런타임 시나리오로 직접 검증된다(구조/범위 제약 없음). **v1.4.0 확장**: REQ-COST-030~036(7개)이 AC-COST-020~024(5개)로 커버된다 — 전부 런타임 시나리오로 직접 검증된다.

---

## 설계 결정

**A. 상수 위치.** `backend/order/serializers.py`에 `OrderDetailSerializer` 정의 바로 위 모듈 레벨 named constants로 선언한다. 검증: 이 파일에 오늘 모듈 레벨 `UPPER_CASE` 상수 패턴이 전혀 없음을 정규식 검색으로 확인했다(0건) — 기존 코드는 `Decimal("0.01")`, `Decimal("100")` 같은 리터럴을 인라인으로 쓴다(`:212,222-224`). `backend/order/` 앱 전체에도 별도 `constants.py`가 없다. 상수가 3개뿐이고 자주 바뀌지 않으므로, DB/설정 기반 가격 관리(관리자 API, 설정 테이블)는 이 SPEC 범위에서 과설계다.

**B. 반올림 순서.** 중간값(`shipping_cost_usd`, `korea_warehouse_usd`, `confirmed_cost_usd`)은 양자화 없는 정확한 `Decimal`로 유지하고 `margin_usd` 계산에 그대로 대입한다 — 기존 `_compute_margin_usd`(`:189-204`)가 이미 이 패턴이다. API로 노출하는 `shipping_cost`/`korea_warehouse_cost`는 **동일한 정확값의 별도 양자화 사본**이며 margin 계산에는 재사용되지 않는다. 알려진 부작용: 노출된 두 비용을 합산해 `total_price`에서 빼도 `margin_amount`와 센트 단위로 정확히 일치하지 않을 수 있다(AC-COST-003이 `159.58` vs `159.57`로 구체적으로 보여준다). 대안(부분합을 먼저 양자화한 뒤 합산)은 기각한다 — 그러면 이번에는 `margin_rate`가 정확한 `margin_usd`(양자화된 `margin_amount`가 아니라)에서 계산되는 기존 관례(`:214-225`)와 어긋나, 불일치가 다른 필드로 옮겨갈 뿐이다.

**C. 쿼리 비용.** `_compute_margin_usd`가 이미 `obj.line_items.all()`을 순회하는 단일 루프(`:196`)를 갖고 있으므로, 무게/권수 집계는 **같은 루프 안에서** 함께 계산해야 하며 별도 루프나 별도 쿼리를 추가하지 않는다(REQ-COST-015). 뷰가 이미 `line_items__notes__author`를 `prefetch_related`하므로(`backend/order/views.py:41-45`) `obj.line_items.all()`을 몇 번 호출해도 최초 1회 외 추가 쿼리가 없다.
**단, 헬퍼 자체가 라인아이템을 1회만 순회하는 것으로는 충분하지 않다(감사 D5).** 설계 결정 E가 공유하는 헬퍼를 5개 게터가 각각 캐시 없이 독립 호출하면, 헬퍼가 요청당 5회 실행되어 그 안의 라인아이템 순회도 5회, `_get_exchange_rate` 쿼리도 최대 5회가 된다 — 라인아이템 순회 자체는 여전히(각 호출마다) 1회이므로 "같은 루프 안에서 계산한다"는 원래 문장을 글자 그대로는 어기지 않지만, 요청 전체로 보면 새 필드마다 자체 순회를 두는 것과 동일한 결과가 된다. 따라서 REQ-COST-015를 "주문 직렬화당 최대 1회"로 강화해, 헬퍼의 계산 결과(무게/권수/비용 및 그 안에서 수행하는 환율 조회)를 **주문(객체) 단위로 메모이즈**해 5개 게터가 동일한 계산 결과를 공유하도록 요구한다 — 구현 방법(예: 시리얼라이저 인스턴스에 `obj.pk` 키의 캐시 딕셔너리, 또는 `obj`에 계산 결과를 직접 부착)은 `plan.md`가 정한다. AC-COST-009가 검증한다.

**D. 노출 필드의 null 시맨틱 — 단일 게이트.** `shipping_cost`, `korea_warehouse_cost`, `total_weight_grams` 세 필드 모두 `margin_amount`/`margin_rate`와 동일한 단일 게이트(환율 없음 OR 확정 매입가 전무)를 공유한다. 대안(무게·배송비는 확정 매입가와 무관하게 독립 계산해 노출)을 검토했으나 기각한다 — `korea_warehouse_cost`는 환율이 필요해 애초에 세 필드가 서로 다른 게이트를 가지면 "마진은 없는데 배송비만 있는" 상태를 프론트엔드가 다뤄야 해 혼란스럽다. 단일 게이트가 더 단순하고 기존 마진 필드 쌍의 "전부 계산되거나 전부 null" 관례와 정합한다. AC-COST-006/007이 검증한다.

**E. 미국창고비 확장 지점.** 5개 필드 게터(`get_margin_amount`, `get_margin_rate`, `get_shipping_cost`, `get_korea_warehouse_cost`, `get_total_weight_grams`)가 하나의 private 헬퍼(이름은 구현자 재량)를 공유한다 — 오늘의 `get_margin_amount`/`get_margin_rate`가 `_compute_margin_usd`를 공유하는 패턴(`:206-225`)을 3개 필드로 확장한 것이다(REQ-COST-019). 헬퍼가 반환하는 값 묶음에 비용 항목이 이름별로 분리되어 있으면, 이후 미국창고비 SPEC은 항 하나를 이 묶음과 `margin_usd` 계산식에 추가하는 것으로 끝나며 5개 게터의 제어 흐름(None 게이트, quantize 호출)은 건드릴 필요가 없다. 이 SPEC 자신은 4번째 항이나 자리표시자 필드를 만들지 않는다(REQ-COST-018).

**F. ExchangeRate 재조회는 주문당 1회로 제한한다(메모이제이션 필수, 감사 D5로 정정).** 최초 초안은 5개 게터가 헬퍼를 독립 호출해 환율 쿼리가 요청당 최대 5회까지 늘어나는 것을, SPEC-ORDER-009 전례(2회 허용, `SPEC-ORDER-009/spec.md:204`의 NOTE)의 자연스러운 연장으로 수용하려 했다. 이 판단을 두 가지 이유로 기각한다 — (1) 이 저장소의 `backend/.env`가 가리키는 DB는 원격 RDS(`us-west-2`)이므로 쿼리당 왕복 지연이 로컬 DB보다 훨씬 크고, 2회→5회는 SPEC-ORDER-009가 실제로 검증한 배수를 2.5배 초과하는 새로운 상황이지 그 전례의 자연스러운 연장이 아니다. (2) REQ-COST-015가 이미 강제하려던 "라인아이템 순회 1회" 의도(설계 결정 C)와 정면으로 충돌한다 — 헬퍼가 5회 호출되면 그 안의 라인아이템 순회도 사실상 5회가 되어 설계 결정 C 자체가 무의미해진다. 따라서 REQ-COST-015를 "주문 직렬화당 최대 1회"로 강화해, 헬퍼의 계산 결과(및 그 안에서 수행하는 환율 조회)를 주문 단위로 메모이즈하도록 요구한다 — 메모이제이션은 **단일 요청 내부**로 한정되며, 요청 간(cross-request) 영속 캐시(Django cache framework, Redis 등)는 이 SPEC의 범위가 아니다(Exclusions 참조). AC-COST-009 (c)가 검증한다.

**G. `total_cost`는 설계 결정 B를 확장한다 — 반올림 전 값의 합을 한 번만 양자화한다(v1.3.0).** `confirmed_cost`/`shipping_cost`/`korea_warehouse_cost`는 설계 결정 B가 이미 정한 대로 각자 독립적으로 양자화된 사본이다. `total_cost`는 이 세 개의 **양자화된 문자열을 다시 파싱해 합산**하지 않는다 — 대신 `_compute_cost_breakdown_uncached`가 갖고 있는 반올림 전 `confirmed_cost_usd + shipping_cost_usd + korea_warehouse_usd`를 그대로 합산한 뒤 `get_total_cost`에서 단 한 번 양자화한다. [HARD] 대안(프론트엔드 또는 백엔드가 이미 노출된 세 반올림 필드를 합산해 `total_cost`를 만드는 방식)은 명시적으로 기각한다 — 사용자 요구사항이 "compute on backend from unrounded values"를 [HARD]로 지정했고, AC-COST-015가 두 방식이 1센트 갈리는 구체적 픽스처(`10.005/2.725/1.25`)로 그 차이를 보여준다. 새 세로 레이아웃(REQ-COST-027)은 `비용 합계`가 `원가`+`배송비`+`한국물류`의 눈에 보이는 합처럼 보이는 위치에 배치되므로, 반올림 오차로 인한 "산술 오류처럼 보이는" 1센트 불일치를 서버가 흡수해야 한다는 것이 이 결정의 핵심 근거다.

**H. `exchange_rate`/`exchange_rate_date`는 설계 결정 D의 단일 게이트를 의도적으로 따르지 않는다(v1.4.0).** 설계 결정 D는 `shipping_cost`/`korea_warehouse_cost`/`total_weight_grams`가 `margin_amount`와 동일한 게이트(환율 없음 OR 확정 매입가 전무)를 공유해야 한다고 정했다 — 그 근거는 "마진은 없는데 배송비만 있는" 상태가 프론트엔드에 혼란을 준다는 것이었다. `exchange_rate`/`exchange_rate_date`는 다르다 — 이 두 필드의 존재 이유 자체가 "확정 매입가가 하나도 없어 마진을 계산할 수 없는 상황에서도, 이 날짜에 어떤 환율이 적용되고 있는지는 보여주고 싶다"는 것이다(문제 정의: `_get_exchange_rate`의 폴백이 지금까지 완전히 비가시적이었다). `has_any_confirmed` 게이트를 공유시키면 이 목적 자체가 무효화된다 — 확정 전 주문(가장 폴백이 궁금한 시점 중 하나)에서 환율이 통째로 사라져버리기 때문이다. 따라서 이 두 필드의 유일한 null 조건은 `_get_exchange_rate(obj) is None`(REQ-COST-032)이며, 설계 결정 D는 기존 7개 필드에만 적용된다. AC-COST-022가 이 분리를 직접 검증한다.

## 알려진 제약사항 — 순 결제액과 마진 기준의 불일치(수정하지 않음, v1.3.0에서 발견)

`frontend/src/pages/OrderDetailPage.tsx:168`은 `netPaidAmount = Number(data.total_price ?? 0) - totalRefunded`로 **환불을 반영한** 순 결제액을 `최종 결제 금액` 줄에 표시한다. 반면 마진(`margin_amount`, `margin_usd`)은 `total_price_usd`(환불 미반영, `backend/order/serializers.py:287`)만을 기준으로 계산한다 — 이 둘의 기준이 서로 다르다는 사실은 SPEC-ORDER-008/009 도입 시점부터 이미 존재했다.

환불이 없는 주문에서는 `netPaidAmount == total_price`이므로 문제가 드러나지 않는다. 환불이 있는 주문에서는 `최종 결제 금액(환불 반영) − 비용 합계(환불 미반영 total_price 기준) ≠ 마진`이 되어, 화면상 뺄셈이 성립하지 않는 것처럼 보인다.

이 SPEC(v1.3.0)이 결제 정보 섹션을 세로 레이아웃(`최종 결제 금액 → 비용 합계 → ... → 마진`)으로 재구성하면서, 이 불일치가 이전보다 훨씬 눈에 띄게 되었다 — 세로 배치는 위 세 줄이 뺄셈 관계라는 암묵적 기대를 만들기 때문이다. **이 SPEC은 이 불일치를 수정하지 않는다** — 마진 계산의 기준(환불 반영 여부)을 바꾸는 것은 이 SPEC의 범위를 벗어나며 사용자가 별도로 결정할 사안이다. 여기서는 결함으로 오인되지 않도록 정확한 `file:line`과 함께 기록만 남긴다.

---

## 제약사항

- 이 SPEC은 백엔드 시리얼라이저·프론트엔드 표시만 다루며 모델/마이그레이션 변경이 없다 — 비용은 런타임 계산이다(SPEC-ORDER-009가 확립한 관례 계승).
- `korea_warehouse_usd`/`shipping_cost_usd` 환산에 쓰는 환율은 `confirmed_price` 환산과 동일한 주문일 환율이며 별도 환율을 도입하지 않는다.
- 값의 통화 단위는 전량 USD로 통일한다(SPEC-ORDER-009 관례).
- `ExchangeRate` 조회는 주문 직렬화당 최대 1회로 제한된다(REQ-COST-015/034, 설계 결정 F) — `exchange_rate`/`exchange_rate_date`를 포함해 9개 필드 게터가 동일한 메모이즈된 조회를 공유한다(v1.4.0).
- `exchange_rate`/`exchange_rate_date`는 설계 결정 D의 단일 게이트를 공유하지 않는다(REQ-COST-033, 설계 결정 H) — 이 둘의 null 조건은 나머지 7개 필드보다 좁다.

## Exclusions (What NOT to Build)

- **미국창고비(US warehouse fee)는 구현하지 않는다.** 자리표시자 필드나 0값 필드도 만들지 않는다 — 사용자가 후속 SPEC에서 추가한다(설계 결정 E가 확장 지점만 마련한다).
- **배송비/한국창고비 상수를 DB나 설정 파일로 관리하는 기능은 만들지 않는다.** 모듈 레벨 상수로 고정한다(설계 결정 A).
- **`OrderListSerializer`(목록 API)에 비용/마진 필드를 노출하지 않는다.** 기존 관례 유지(REQ-COST-014).
- **비용 내역을 DB 컬럼으로 저장하지 않는다.** 런타임 계산으로 유지한다(SPEC-ORDER-009 제약사항 계승).
- **과거 주문에 대한 소급 배치 재계산은 만들지 않는다.** 런타임 계산이므로 조회 시점마다 새 공식이 자동 적용되며, 별도의 백필 마이그레이션이나 배치 작업이 필요 없다.
- **`ExchangeRate` 조회의 영속적(cross-request) 캐싱 계층은 만들지 않는다.** REQ-COST-015가 요구하는 것은 단일 요청 내 메모이제이션(주문 직렬화당 최대 1회)뿐이다 — Django cache framework, Redis 등 요청 간 캐시는 이 SPEC의 범위가 아니다(설계 결정 F).

## 후속 과제

1. **미국창고비 추가.** 설계 결정 E의 확장 지점(단일 비용 헬퍼)을 이용해 4번째 비용 항을 추가하는 별도 SPEC.
2. **`ExchangeRate` 조회의 요청 간(cross-request) 캐시.** REQ-COST-015가 이미 요청당 최대 1회로 제한하지만, 그 1회조차 고트래픽 환경(원격 RDS, `us-west-2`)에서 병목으로 판명되면 시리얼라이저 요청을 넘어서는 캐시(Django cache framework 등)를 도입하는 별도 SPEC.
