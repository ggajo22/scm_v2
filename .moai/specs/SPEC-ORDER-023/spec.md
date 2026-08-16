---
id: SPEC-ORDER-023
version: 1.4.0
status: completed
created_at: 2026-08-16
updated: 2026-08-16
author: ggajo
priority: High
issue_number: 0
labels: [order, list, margin, logistics, purchase-status, frontend, backend]
---

# 주문목록 표시 컬럼 개편 (마진율 / 물류상태 / 발주상태)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-16 | ggajo | 최초 작성. 사용자가 확정한 범위(주문목록 결제상태/출고상태 열 제거, 마진율/물류상태/발주상태 열 추가, 물류상태 필터 추가)를 EARS 형식으로 formalize. |
| 1.1.0 | 2026-08-16 | ggajo | plan-auditor 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-023-review-1.md`, iteration 1, FAIL, 0.61) 반영. **차단 결함 3건 해소**: C1(REQ-OLIST-022가 REQ-OLIST-019/plan.md의 배치 쿼리 +1과 정면 모순 — "이전 대비 증가 없음"을 "페이지 크기·주문 수에 비례해 증가하지 않는다(O(1))"로 재정의하고, REQ-OLIST-022a를 신설해 "베이스라인 + 정확히 1"을 명시적으로 못박음. 베이스라인은 이 세션에서 직접 실측 — 아래 참조), C2(규칙 1↔2 우선순위를 검증하는 AC가 없고 프로덕션에서 항상 동시 성립 — `purchase_order_views.py:3411/3456/3972` 확인 후 AC-OLIST-006/022 계열의 "출고완료" 픽스처에 `shipped_quantity=quantity`를 명시), C3(`Order.status`가 물류 쓰기 작업을 한 번도 거치지 않은 주문에서는 trackable 항목이 있어도 `NULL`이라는 사실 확인 — `shopify_orders.py:140-143`이 `status`를 `defaults`에서 의도적으로 제외하고 `_recompute_order_aggregates`의 호출자는 `purchase_order_views.py`뿐임을 grep으로 확인. **REQ-OLIST-011을 `Order.status` 패스스루에서 trackable 라인아이템으로부터 즉시 파생(uniform이면 그 값, 2개 이상이면 `partial`)하는 방식으로 재설계** — 저장된 집계값에 대한 의존을 완전히 제거해 C3와 H5(7번째 라벨 누출)를 동시에 해소). **고위험 결함 6건 해소**: H1(AC-OLIST-012/016/018의 `is None` 단정이 미구현 코드에서도 통과 — 키 존재 단정 추가, SPEC-ORDER-021 D6 재발), H2(6개 필터 값 중 1개만 검증 — AC-OLIST-022를 6개 값 전량 커버하는 계열로 확장, REQ-OLIST-024a로 미허용 값 동작 명시), H3(`margin_rate` null 원인 3개 중 1개만 검증 — AC-OLIST-018a/018b 신설), H4(발주상태 경로의 trackable 필터 누락이 검증되지 않음 — AC-OLIST-011에 `purchase_display` 단정과 non-trackable 극단값 추가), H5(C3 재설계로 해소 — `received`가 더 이상 규칙 4에 도달할 수 없음을 재검증), H6(`getDisplayStatus` "완전 재사용" 지시가 REQ-OLIST-006을 위반 — 배지 판별을 "앞 3개 분기만"으로 한정하고 `data-testid="cancel-badge"` 부재로 AC-OLIST-004를 강화). **마진 반올림(감사 M2) 해소**: 목록 엔드포인트 전용 AC-OLIST-017a 신설(`grams=500,quantity=1` 반올림 경계 픽스처). **MP-2(EARS 형식 퇴행) 해소**: 기존 27개 AC 전량을 SPEC-ORDER-021 형식(굵게 표시한 EARS 연결어 포함 문장)으로 재작성하고, 신규 추가된 9개(013a/017a/018a/018b/022a~e)도 동일 형식으로 작성 — 최종 36개 AC 전량이 EARS 문장이다. **Medium 결함 7건도 함께 해소**: M3(부분문자열 함정 — "취소"/"부분취소" 배지를 `data-testid` 기반 정확 대조로 전환), M4(라벨 중복 매칭 — 필터 옵션과 셀 텍스트를 스코프 조회로 분리 명시), M6(배치 로드 상한 미설계 — lookback 윈도 대신 `values_list("effective_date","rate")` 슬림 프로젝션으로 정정, 근거는 설계 결정 A 참조 — 감사가 제안한 lookback 윈도 축소안은 REQ-OLIST-020의 정확성 요건과 충돌할 위험이 있어 채택하지 않았다), M8(SPEC-ORDER-021 Exclusion supersede 사실 명기), M9(`order_cancelled` 라인아이템의 발주상태 분류를 명시적 가정으로 기록), M10(AC-OLIST-024에 구체적 기대값 추가), L4(REQ-OLIST-033/034의 EARS 라벨을 Unwanted→Ubiquitous로 교정, 번호는 유지). **Low 결함(인용 드리프트) 3건 정정**: Django `count()`/`exists()`/prefetch 캐시 근거를 "설치된 5.1.6"에서 **`backend/poetry.lock:168`이 고정한 5.2.17**(실제 poetry 가상환경 `C:\Users\ggajo\AppData\Local\pypoetry\Cache\virtualenvs\scm-v2-backend-*\`에서 직접 재확인)로 교체 — `count()`는 5.1.6에서 609행, **5.2.17에서는 595행**(두 버전 모두 재확인, 감사가 제시한 "608행"은 이 세션에서 5.1.6/5.2.17 어느 쪽으로도 재현되지 않아 채택하지 않았다 — `def count` 앞뒤 한 줄씩도 확인함); "`test_spec_021.py` 전량(T1~T22)"을 "T1~T10, T12~T22(21개, T11 결번)"으로 정정; "sync 관련 6개"를 "7개"(`OrdersPage.test.tsx:85,94,104,118,132,145,159`)로 정정. **베이스라인 실측(C1 근거)**: 고객 정보가 있는 주문 2건으로 구성된 페이지에 대해 `GET /api/orders/`를 이 세션에서 직접 측정한 결과 쿼리 6개(JWT 인증 사용자 조회 1 + 페이지네이션 COUNT 1 + 본문 SELECT 1 + `prefetch_related` 3개(`refunds`/`line_items`/`customer`))로 확인했다(측정에 사용한 임시 테스트 파일은 검증 직후 삭제). 이 값이 REQ-OLIST-022a와 AC-OLIST-021의 근거 상수다. |
| 1.2.0 | 2026-08-16 | ggajo | plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-023-review-2.md`, iteration 2, FAIL, 0.76 — v1.1.0 대비 상승) 반영. v1.1.0의 C1/C2/C3, H1~H6은 감사가 소스 대조로 전부 실질 해소를 확인했다(문구 땜질이 아니라 설계 수준 해소 확인 — 재설계가 새로 만든 표면에서만 신규 결함 발견). **차단 결함 1건 해소**: C1-new(REQ-OLIST-010/011이 REQ-OLIST-008과 달리 "at least one trackable line item" 가드가 없어, trackable 0개 주문에서 `all([])==True`로 REQ-OLIST-010이 공허하게 발화해 REQ-OLIST-012/AC-OLIST-012와 정면 모순 — plan.md의 의사코드/SQL은 우연히 안전했지만 이는 plan.md:13("규범 진술 단일 출처는 spec.md")을 위반하는 상태였다. REQ-OLIST-010/011/011a 전부에 동일 가드 추가, 확정된 사용자 결정 5의 한글 서술도 함께 정합화). **고위험 결함 3건 해소**: H1-new(AC-OLIST-022b/022c/022e의 Given이 "그 외 상태의 주문 1건 이상"으로 비특정이라 `all` 대신 `any`로 잘못 구현해도 통과 — 6개 상태를 망라하는 명명된 "표준 물류상태 데이터셋"(Order A~G)을 신설해 022~022e 전량이 동일 데이터셋을 공유하도록 재작성), H2-new(규칙 4 경유 `outbound_scheduled`의 **표시값**을 단정하는 AC가 전무 — AC-OLIST-022d에 "(a)/(b) 두 원인 모두의 `logistics_display`가 `outbound_scheduled`"인 이중 단정을 추가하고, 같은 "필터 결과 ∧ 표시값" 패턴을 022a~e 전체로 일괄 전파), H3-new(REQ-OLIST-022a의 "plus exactly 1"이 plan.md의 "페이지 전체가 `shopify_created_at IS NULL`이면 배치 쿼리를 건너뛴다"는 조건부 최적화와 충돌 — `shopify_created_at`이 nullable이고 목록이 `-shopify_created_at` 정렬이므로 전부 NULL인 마지막 페이지가 도달 가능함을 확인. REQ-OLIST-022a를 "고객 유무에 따른 베이스라인(6 또는 5) + 날짜 유무에 따른 추가분(정확히 1 또는 정확히 0), 그 이상은 없음"으로 일반화). **Medium 결함 5건 해소**(감사가 제시한 M1-new~M5-new 전부, 사용자가 명시적으로 지정): M1-new(Traceability 표에서 REQ-OLIST-011의 커버 AC 목록에서 AC-OLIST-011 삭제 — 그 픽스처는 규칙 3으로 판정되어 규칙 4를 경유하지 않는다), M2-new(REQ-OLIST-024a가 위임하던 "plan.md DoD" 게이트가 실재하지 않았음 — 신규 AC-OLIST-022f 추가로 실제 런타임 검증을 확보), M3-new(프론트엔드 물류상태 라벨이 6개 중 1~2개만 검증되던 것을 백엔드와 동일하게 6/6 파리티로 확장 — AC-OLIST-026에 7개 옵션 전량 존재 단정, AC-OLIST-027에 6개 라벨 파라미터화 단정 추가), M4-new(AC-OLIST-022a의 "그 외 5개 상태" 서술이 사실과 다름(AC-007/AC-009가 둘 다 `partial_shipped`로 수렴해 실제로는 4개 상태뿐이고 `not_shipped`가 누락) — 표준 데이터셋 도입으로 자동 해소), M5-new(=round-1 L7 미해소 — 배치 로더의 `.date()` 적용 시점·시간대가 `_get_exchange_rate`와 동일해야 한다는 규정이 없었음 — REQ-OLIST-020에 명시 추가, `override_settings(TIME_ZONE=...)` 기반 경계 AC-OLIST-020a 신설). Low 항목(L1-new~L8-new)은 사용자가 이번 라운드에서 범위 밖으로 지정해 손대지 않았다 — 다음 라운드로 이월. |
| 1.2.1 | 2026-08-16 | ggajo | plan-auditor 3차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-023-review-3.md`, iteration 3, **PASS, 0.87, 차단 결함 0건**) 반영. v1.2.0의 C1-new/H1-new/H2-new/H3-new/M1-new~M5-new 9건 전량이 독립 재유도로 해소 확인됨(review-2의 L2-new 오판도 이번 감사가 뒤집었다 — REQ-OLIST-011의 괄호 논거는 원래 옳았다). 이번 라운드는 PASS 상태에서 사용자가 선택한 4건만 좁게 반영한다: **N1**(표준 데이터셋의 유일한 혼재 주문 G가 `{not_shipped, shipment_confirmed}`뿐이라 `outbound_scheduled` uniform 검사의 any/all mutation을 판별하지 못함 — Order H(`{outbound_scheduled, shipment_confirmed}` 혼재, 표시값 `partial`)를 데이터셋에 추가하고 AC-OLIST-022e의 기대 집합을 `{G,H}`로, AC-OLIST-022d에 이 mutation 전용 판별 노트를 추가. spec.md/acceptance.md 두 데이터셋 표는 바이트 단위로 동일하게 유지), **N2**(REQ-OLIST-025 [HARD] "쿼리 레벨 필터"를 어떤 AC도 실질 판별하지 못함 — 페이지네이션 이후 Python 사후 필터링은 추가 쿼리 0개라 AC-OLIST-023을 통과하고, 7~8건짜리 단일 페이지 데이터셋에서는 `results`도 우연히 맞아 AC-OLIST-022~022e도 통과하지만 프로덕션에서 페이지네이션이 조용히 깨진다 — AC-OLIST-022~022e의 Then에 `count` 필드 단정을 추가해 Python 사후 필터링 mutation을 `count`가 필터 전 전체 건수로 남는 것으로 판별. Traces에 REQ-OLIST-025 추가), **L8-new**(REQ-OLIST-024a의 "return the unfiltered result set" 문언이 "다른 필터까지 무시"로 오독 가능 — "ignore **this** filter … other query parameters' filtering still applies"로 3단어 수정), **spec.md:127의 사실 오류**(N6 — 재검증 문단이 "008/009/010/011/011a 전부 명시적으로 가드"라고 썼으나 REQ-OLIST-009는 명시적 가드가 아니라 존재 한정사(`∃`)로 안전한 것이며 근거가 달랐다 — 문장 정정, 결론은 원래도 참이었다). 감사가 deferred로 재확인한 나머지 항목(N3/N4/N5/N7/N8/N9/N10, L1/L3/L4/L5/L6-new)은 사용자가 이번에도 명시적으로 범위 밖으로 지정해 손대지 않았다. |
| 1.3.0 | 2026-08-16 | ggajo | 구현 완료(브랜치 `feature/SPEC-ORDER-023`) — 백엔드는 manager-tdd(M0~M4, M8 백엔드분), 프론트엔드는 expert-frontend(M5~M6)가 담당했다. 독립 평가(evaluator-active, PASS — Functionality 93 / Security 96 / Craft 88 / Consistency 88) 완료 후 `status`를 draft→completed로 전환한다. **M0 베이스라인 재실측**: 이 세션에서 `GET /api/orders/`의 SPEC 이전 쿼리 수를 다시 측정해 **6**을 확인했다 — REQ-OLIST-022a의 유도값과 일치. 구현 후 쿼리 수는 **7**이며 페이지 크기에 관계없이 불변임을 확인했다. **테스트 결과**: `test_spec_023.py` 31개 전량 통과. 백엔드 스위트 1204개 통과. `test_spec_021.py`의 T1~T10, T12~T22(21개, T11 결번) 전량 무수정 재통과 — 마진 공식 추출 리팩터링이 `OrderDetailSerializer`의 출력을 바꾸지 않았음을 확인. 프론트엔드 304개 테스트 통과, `tsc -b` 클린. **계획 대비 유일한 발산**: `OrderListSerializer.get_margin_rate`(`serializers.py:197-207`)가 `obj.shopify_created_at`이 falsy일 때 명시적 조기 반환(`if not obj.shopify_created_at: return None`)을 추가했다 — plan.md는 이를 `_resolve_exchange_rate`가 `None`을 반환하는 경로로 간접적으로만 암시했을 뿐, 명시적 조기 반환을 지시하지 않았다. 두 방식은 동작상 완전히 동일하며, 이 조기 반환은 가독성을 위해 추가한 것이다. **mutation 검증을 분석에 그치지 않고 실제 코드에서 가드를 제거해 라이브로 재현했다**: 규칙 1/2 순서 교체(AC-006), trackable 가드 제거(AC-012), `any`→`all` 교체(AC-014), 반올림 순서 교체(AC-017a), 주문별 개별 `ExchangeRate` 조회(AC-019/021), 페이지네이션 이후 Python 사후 필터링(AC-022~022e의 `count` 단정) — 설계된 대로 전부 실패했다. 특히 `count` 단정은 `results`는 정답과 같아 보여도 `count`가 필터 전 전체 건수로 남는 사후 필터링 결함을 잡아냈다 — 이것이 감사 3라운드(N2)가 방지하려 했던 정확히 그 결함이다. **알려진 잔여 격차(수용)**: REQ-OLIST-022a의 "+0" 분기(페이지의 모든 주문이 `shopify_created_at IS NULL`)는 런타임 AC가 없다 — 코드는 검사로 정확함이 확인되었고, Shopify 주문은 항상 생성 시각을 동반하므로 프로덕션 리스크는 사실상 0이다. 이는 감사 3라운드가 N5로 기록한 항목과 동일하다. |
| 1.4.0 | 2026-08-16 | ggajo | **프로덕션 결함 정정 — 발주상태 판정 기준(모듈 3)이 근본적으로 틀렸다.** 사용자가 주문 `#38360`(order.pk=4163)이 발주 완료인데 "미발주"로 표시된다고 보고했고, 원격 DB 실측으로 해당 주문의 trackable 라인아이템 8건 전부가 `status='confirmed'`인 `PurchaseOrder`(#12197, #12534~#12540)에 연결돼 있으면서도 `purchase_status`는 `'unordered'`임을 확인했다. **근본 원인**: `LineItem.PURCHASE_STATUS_CHOICES`(`backend/order/models.py:156-167`)에는 "발주완료"에 해당하는 값이 아예 없고, 발주 생성 경로(`purchase_order_views.py:1131` `po.line_items.add(*unordered_lis)`, `management/commands/process_purchase_orders.py:170`)는 M2M 링크만 걸 뿐 `purchase_status`를 바꾸지 않는다. 즉 이 시스템에서 "발주됨"의 실제 판정 기준은 `purchase_status`가 아니라 **`PurchaseOrder` 연결 여부**이며, 미발주 목록 탭(`_reorder_candidate_filter`, `purchase_order_views.py:107-110`)이 이미 그 기준을 쓰고 있었다. v1.0.0~v1.3.0의 REQ-OLIST-013/014는 이 링크 조건을 누락한 채 `purchase_status == 'unordered'`만 검사했다. **영향 범위 실측(원격 DB 전수 조사)**: trackable 라인아이템 14,281건 중 `purchase_status='unordered'`가 13,917건이고 그중 **13,904건이 이미 발주서에 연결된 오탐**(진짜 미발주는 13건뿐), 주문 단위로는 trackable 주문 3,613건 중 **3,524건(97.5%)이 발주 완료인데 "미발주"로 표시**되고 있었다 — 단발 데이터 문제가 아니라 발주상태 열이 사실상 항상 "미발주"를 표시하는 상태였다. 기존 AC-OLIST-014/015가 이를 잡지 못한 이유는 두 AC의 픽스처가 `PurchaseOrder`를 전혀 만들지 않아 `purchase_status`만으로도 정답이 나오는, **판별력 없는 픽스처**였기 때문이다(감사 3라운드가 이 축을 검사하지 않았다). **정정 내용**: (1) 확정된 사용자 결정 6과 REQ-OLIST-013/014를 미발주 목록 탭과 **동일한 기준**(`_reorder_candidate_filter`)으로 재정의 — `purchase_status='unordered'`이면서 연결된 `PurchaseOrder`가 없는 항목, 또는 `purchase_status='damaged_exchange'`인 항목이 하나라도 있으면 미발주(사용자 확정 결정 9 신설). (2) REQ-OLIST-021을 `line_items__purchase_orders` prefetch 재사용 허용으로 개정하고, REQ-OLIST-022a의 델타를 "+최대 1"에서 "+최대 2"로, AC-OLIST-021의 절대상수를 7에서 8로 갱신 — 추가 1건은 M2M prefetch 1회이며 페이지 크기와 무관한 상수다. (3) AC-OLIST-014/015에 `PurchaseOrder` 연결 픽스처를 필수화하고, AC-OLIST-014a(발주서 연결 항목은 미발주가 아니다 — 이번 결함의 직접 재현), AC-OLIST-014b(`damaged_exchange`는 발주서 연결과 무관하게 미발주)를 신설했다. 명시적 가정 4(`order_cancelled` 미제외)는 그대로 유지된다 — 새 기준에서도 `order_cancelled`는 `unordered`가 아니므로 미발주를 유발하지 않는다. |

---

## 문제 정의

`frontend/src/pages/OrdersPage.tsx`의 주문목록 테이블은 현재 8개 열(`:280-287`) — 주문번호/스토어/위치/고객/**결제상태**/**출고상태**/금액/주문일 — 을 표시한다. 이 중 결제상태(`getDisplayStatus`, `:81-94`)와 출고상태(`getFulfillmentLabel`, `:96-104`)는 Shopify가 동기화한 원시 필드(`financial_status`/`fulfillment_status`)를 그대로 라벨링한 것으로, 담당자가 실제 운영에 쓰는 정보(마진율, 한국창고 기준 물류 진행 상태, 발주 필요 여부)를 담지 못한다.

취소/부분취소 정보 자체는 여전히 필요하다 — 다만 전용 열이 아니라 주문번호 옆의 작은 배지로 축소해 유지한다.

`OrderListSerializer`(`backend/order/serializers.py:25-54`)는 오늘 마진·물류·발주 관련 필드를 전혀 노출하지 않는다. `OrderDetailSerializer`(`:152-443`)는 `margin_rate` 등을 이미 계산하지만, 그 계산의 핵심 의존성인 `_get_exchange_rate`(`:222-254`)가 **주문(`obj.pk`) 단위로 메모이즈**되어 있어 — 목록 API처럼 자식 시리얼라이저 인스턴스 하나가 페이지의 50개 주문을 순차 처리하는 구조에 그대로 재사용하면, 서로 다른 50개의 `obj.pk`가 캐시에 각각 새 키로 쌓여 **페이지당 최대 50회**의 `ExchangeRate` 조회가 발생한다. 이 저장소는 원격 DB(`backend/.env`, 쿼리당 약 130ms)를 쓰므로 이는 페이지 로드에 최대 ~6.5초를 추가하는, 이 SPEC에서 가장 중요한 비기능 제약이다(REQ-OLIST-019).

**`Order.status`(`backend/order/models.py:49-54`)에 의존해서는 안 된다 — 이는 저장형 집계 컬럼이며, 물류 관련 쓰기 작업을 한 번도 거치지 않은 주문에서는 trackable 라인아이템이 있어도 `NULL`이다.** `status`를 갱신하는 유일한 함수는 `_recompute_order_aggregates`(`backend/order/purchase_order_views.py:123-209`)이며, 그 호출자는 같은 파일 안의 9개 쓰기 뷰뿐이다(`grep -rn "_recompute_order_aggregates" backend/`로 이 세션에서 확인 — Shopify 동기화 경로에는 호출자가 없다). `shopify_orders.py:130-143`의 `Order.objects.update_or_create(..., defaults={...})`는 `status`를 `defaults` 딕셔너리에서 **의도적으로 제외**한다(주석: "`status` intentionally excluded — it is now the logistics_status aggregate ... recomputed only by `purchase_order_views._recompute_order_aggregates()`. Shopify sync must never overwrite it"). 모델에도 기본값이 없다(`models.py:49-54`, `null=True`, `default` 미지정). 따라서 Shopify 동기화로 갓 생성되었고 아직 어떤 물류 업로드도 거치지 않은 주문은 라인아이템이 모두 기본값 `logistics_status='not_shipped'`(`models.py:207`)를 갖고 있음에도 `Order.status IS NULL`이다 — 이 SPEC의 물류상태 열은 이런 주문에서도 정확히 "미입고"를 표시해야 하므로(trackable 라인아이템이 실제로 존재하기 때문), **`Order.status`를 읽는 방식으로는 이 요구를 충족할 수 없다.** 이 SPEC은 물류상태 파생을 전적으로 이미 prefetch된 `LineItem` 행에서 그 자리에서 계산하는 방식으로 설계한다(REQ-OLIST-011/011a) — 저장된 `Order.status`는 읽지도 쓰지도 않는다.

또한 `LineItem.logistics_status == 'shipped'`로 쓰는 유일한 세 코드 경로(`purchase_order_views.py:3411,3456,3972`, 전부 `if line_item.shipped_quantity >= effective_quantity: line_item.logistics_status = "shipped"` 형태)를 이 세션에서 직접 확인한 결과, **프로덕션에서 `logistics_status='shipped'`인 라인아이템은 항상 `shipped_quantity >= quantity > 0`을 동시에 만족한다.** 즉 "전부 출고완료"(규칙 1)와 "하나 이상 부분출고"(규칙 2)는 완전출고 주문에서 **항상 동시에 성립**하며, 두 규칙의 평가 순서가 뒤바뀌면 모든 완전출고 주문이 "부분출고"로 잘못 표시된다 — 이 SPEC이 만들 수 있는 가장 흔하고 눈에 띄는 버그다. 인수 기준의 픽스처는 이 사실을 반드시 반영해야 한다(AC-OLIST-006/022 계열).

## 목표

1. 주문목록에서 결제상태/출고상태 열과 그 필터 드롭다운을 제거한다.
2. 취소/부분취소 가시성은 주문번호 옆 배지로 보존한다 — 기존 `getDisplayStatus`의 **취소 판별 분기만**(결제상태 라벨 분기는 재사용하지 않는다) 재사용한다.
3. 마진율(표시 전용), 물류상태(한국창고 기준 파생값, `LineItem`에서 직접 파생), 발주상태(미발주/발주완료) 3개 열을 추가한다.
4. 물류상태 필터 드롭다운을 추가한다 — 필터 옵션은 화면에 실제로 보이는 라벨과 정확히 일치해야 하며, 필터(SQL)와 표시(Python) 양쪽 모두 `LineItem` 행에서 동일한 우선순위로 파생해야 한다.
5. `ExchangeRate` 조회를 리스트 요청당 최대 1회로 제한해, 신규 열 3개가 페이지 크기·주문 수에 비례해 쿼리 수를 늘리지 않도록 한다(O(1)) — `ExchangeRate` 배치 쿼리 1회의 추가는 이 목표가 금지하는 대상이 아니라 이 SPEC이 의도적으로 도입하는 대가다.

## 확정된 사용자 결정

1. **최종 열 구성(9열, 좌→우)**: 주문번호(취소 배지 포함) / 스토어 / 위치 / 고객 / 물류상태 / 발주상태 / 마진율 / 금액 / 주문일.
2. **결제상태 열과 출고상태 열은 완전히 제거한다** — 라벨 헬퍼(`getFulfillmentLabel`)를 포함해 삭제한다.
3. **취소 배지 판별식은 기존 `getDisplayStatus`(`OrdersPage.tsx:81-94`)의 앞 3개 분기(`:82-85`, `refunded`/`partially_refunded`/`has_refund` 판정)와 완전히 동일하다 — 그 뒤에 이어지는 결제상태 라벨 맵(`:86-93`, `paid→결제완료` 등)은 배지에 재사용하지 않는다.** `financial_status === 'refunded'` → `취소`; (`refunded`가 아니면서) `financial_status === 'partially_refunded'` 이거나 `has_refund === true` → `부분취소`; 그 외 → 배지 없음(배지 요소 자체가 DOM에 존재하지 않는다).
4. **마진율은 표시 전용이다** — DB 컬럼으로 역정규화하지 않고, `OrderDetailSerializer`와 동일한 계산을 재사용하되 목록 요청 특유의 성능 제약(배치 환율 로드)을 만족해야 한다.
5. **물류상태는 한국창고 기준이며, 오직 trackable 라인아이템(`sku` not null)에서 그 자리에서 파생한다 — `Order.status` 컬럼은 읽지 않는다.** 아래 1~5번 규칙은 모두 **trackable 라인아이템이 1개 이상 존재함을 전제**한다(v1.2.0 명시 — C1-new: 이 전제 없이 "모든 trackable 라인아이템이 X" 같은 규칙을 그대로 구현하면, trackable이 0개인 주문에서 공집합에 대한 전칭 명제가 공허하게 참이 된다. **[v1.3.0 정정]** 다만 이때 실제로 잘못 발화하는 것은 규칙 3(REQ-OLIST-010, `outbound_scheduled`)이 아니라 규칙 1(REQ-OLIST-008, `all(li.logistics_status == "shipped")`)이다 — 규칙 1도 공집합에서 동일하게 공허하게 참이고, 규칙 3보다 먼저 평가되므로 규칙 3에는 도달조차 하지 않는다. 가드를 실제로 제거하고 관찰한 결과는 `"outbound_scheduled"`가 아니라 `"shipped"`였다 — 구현 에이전트와 독립 평가자(evaluator-active) 양쪽이 각자 가드를 제거해 재현·확인했다. 이 정정은 결론에 영향을 주지 않는다 — 가드는 여전히 필수이며 AC-OLIST-012는 어느 값이 잘못 나오든 그 제거를 그대로 잡아낸다). 우선순위:
   1. 모든 trackable 라인아이템의 `logistics_status == 'shipped'` → **출고**
   2. (1이 아니고) 하나 이상의 trackable 라인아이템이 `shipped_quantity > 0` → **부분출고**
   3. (1, 2가 아니고) 모든 trackable 라인아이템의 `logistics_status == 'received'` → **출고예정**
   4. (1~3이 아니고) 남은 trackable 라인아이템들의 `logistics_status`가 전부 동일한 값 하나로 uniform함 → 그 값(반드시 `not_shipped`/`shipment_confirmed`/`outbound_scheduled` 중 하나 — 규칙 1~3이 이미 `shipped`/`received`-전체-일치를 소진했으므로 이 시점의 uniform 값은 이 셋으로 한정된다)
   5. (1~4가 아니고, 즉 남은 trackable 라인아이템의 `logistics_status`가 2개 이상의 값으로 섞여 있음) → **부분입고**(`Order.status`의 기존 `"partial"` 라벨과 동일한 의미론, 단 저장값이 아니라 즉시 계산)
   6. trackable 라인아이템이 0개 → `-`
6. **발주상태는 미발주/발주완료 2값뿐이다** [REWRITTEN v1.4.0]: trackable 라인아이템 중 하나라도 **발주 대기 상태**이면 → **미발주**; 그 외(trackable이 1개 이상 존재) → **발주완료**; trackable 0개 → `-`. "발주 대기 상태"의 정의는 아래 결정 9가 정한다. Order 레벨 집계 컬럼은 신설하지 않는다(표시 전용, 매 요청 시 이미 prefetch된 라인아이템에서 계산).
7. **물류상태 필터를 추가한다** — 필터 옵션은 물류상태 열에 실제로 표시되는 6개 상태(미입고/입고예정/출고예정/부분출고/출고/부분입고)와 정확히 일치하며, SQL 측도 `LineItem` 술어에서만 파생한다(`Order.status`를 필터 조건에 쓰지 않는다).
8. **발주상태 필터는 만들지 않는다.**
9. **"발주 대기 상태"의 정의는 미발주 목록 탭과 동일하다** [NEW v1.4.0]: 판정 기준은 `_reorder_candidate_filter`(`backend/order/purchase_order_views.py:107-110`)와 **한 글자도 다르지 않게** 일치해야 한다 — 즉 (a) `purchase_status == 'unordered'`이면서 연결된 `PurchaseOrder`가 **하나도 없는** 라인아이템, 또는 (b) `purchase_status == 'damaged_exchange'`인 라인아이템(발주서 연결 여부와 무관, SPEC-PURCHASE-ORDER-010 REQ-DMG-001이 재발주 큐 재진입을 규정한다). `purchase_status` 단독 검사는 금지한다 — `PURCHASE_STATUS_CHOICES`(`models.py:156-167`)에 "발주완료" 값이 존재하지 않고 발주 생성 경로(`purchase_order_views.py:1131`)가 M2M 링크만 걸기 때문에, `purchase_status`만 보면 발주가 나간 항목도 영구히 `'unordered'`로 남는다(v1.4.0 결함의 근본 원인). **이 일치는 선택이 아니라 요구사항이다**: 주문목록의 발주상태와 미발주 목록 탭에 실제로 뜨는 항목이 어긋나면 운영자가 두 화면 중 어느 쪽을 믿어야 할지 알 수 없다.

## 명시적 가정

1. **`outbound_scheduled`(출고예정) 원시 상태와 규칙 3이 파생하는 "전부 입고완료"도 동일 라벨 "출고예정"으로 수렴한다.** `outbound_scheduled`는 실제 운영 코드에 자동 기록 경로가 없고(수신/입고 업로드는 `received`에서 멈추고, 출고 업로드는 `received`를 건너뛰어 바로 `shipped`로 감 — `grep -rn "outbound_scheduled" backend/ --include=*.py`로 이 세션에서 재확인, `models.py`의 choices 정의와 주석 외에 프로덕션 코드에 쓰기 경로 없음), `frontend/src/services/purchaseOrderApi.ts:76`의 수동 드롭다운으로만 도달 가능하므로 두 의미가 같은 라벨로 합쳐져도 실무 충돌이 없다고 가정한다. 물류상태 필터(`logistics_display=outbound_scheduled`)도 이 두 원인을 구분하지 않고 하나의 값으로 다룬다(REQ-OLIST-023의 이접 조건).
2. **`sku`가 null인 라인아이템("non-trackable")은 물류상태·발주상태 계산에서 완전히 제외한다** — `_recompute_order_aggregates`가 (과거) `Order.status`/`ready_to_ship`을 계산할 때 쓰던 것과 동일한 정의(`sku__isnull=False`, `backend/order/purchase_order_views.py:160-161`)를 그대로 재사용한다. **단, 이 SPEC의 물류상태 파생 자체는 `_recompute_order_aggregates`를 호출하거나 그 저장된 결과(`Order.status`)를 읽지 않는다 — 동일한 trackable 정의와 동일한 uniform/partial 집계 규칙을 재사용할 뿐, 계산은 매 요청 시 독립적으로 수행한다(v1.1.0 설계 변경, C3 참조).**
3. **마진율 계산은 `sku` 유무와 무관하게 전체 라인아이템을 대상으로 한다** — `OrderDetailSerializer._compute_cost_breakdown_uncached`(`backend/order/serializers.py:298-360`)가 `obj.line_items.all()` 전체를 순회하며 `sku` 필터를 적용하지 않는 것과 동일한 관례를 유지한다. "trackable"은 물류/발주 상태 파생에만 적용되는 개념이며 마진 계산에는 적용되지 않는다 — 구현자가 혼동하지 않도록 명시한다.
4. **`purchase_status == 'order_cancelled'`인 trackable 라인아이템은 발주상태 "unordered가 아님" 판정에 그대로 포함된다(제외하지 않는다).** `_recompute_order_aggregates`의 `status` 집계(`purchase_order_views.py:172-178`)는 `order_cancelled` 항목을 제외하지 않지만, `ready_to_ship` 집계(`:187-199`)는 제외한다 — 이 SPEC의 발주상태 규칙(REQ-OLIST-013/014)은 `status` 집계와 동일하게 **제외하지 않는 쪽**을 채택한다. 그 결과 trackable 라인아이템이 전부 `order_cancelled`인 주문은 "발주완료"로 표시된다 — 사용자가 확정한 발주상태 규칙이 "미발주/발주완료 2값뿐"으로 제한되어 있어 별도의 "취소" 상태를 도입하지 않았기 때문에 나오는 결과다. 이것이 원하는 동작인지는 사용자 확인이 필요하며, 필요시 후속 SPEC에서 `ready_to_ship` 관례(제외)로 전환할 수 있다(후속 과제 4).

## 범위 — 델타

| 마커 | 대상 | 내용 |
|---|---|---|
| [MODIFY] | `OrderListSerializer`(`backend/order/serializers.py:25-54`) | `margin_rate`, `logistics_display`, `purchase_display` 3개 `SerializerMethodField` 신규 추가. 기존 5개 필드(`has_refund`, `line_items_count` 포함)는 무수정. |
| [MODIFY] | `OrderListView.get_queryset`(`backend/order/views.py:161-218`) | `logistics_display` 쿼리 파라미터 처리(`LineItem` 대상 `Exists` 기반 필터, `Order.status`는 조건에 쓰지 않음) 추가. `financial_status`(`:171-173`)/`fulfillment_status`(`:186-191`) 파라미터 처리는 무수정. |
| [MODIFY] | `OrderListView`(`list()` 오버라이드 또는 동등 위치) | 페이지 단위 `ExchangeRate` 배치 조회를 1회만 수행해 시리얼라이저 컨텍스트로 전달. |
| [EXISTING] | `OrderDetailSerializer`(`backend/order/serializers.py:152-443`) | 무수정 — 필드 집합·계산 로직·`_get_exchange_rate`/`_compute_cost_breakdown` 어느 것도 건드리지 않는다. 공용 헬퍼를 추출하더라도 detail의 관측 가능한 출력은 리팩터링 전후 바이트 단위로 동일해야 한다. |
| [EXISTING] | `Order.status`/`Order.ready_to_ship`, `_recompute_order_aggregates` | 완전히 무수정 — 이 SPEC은 이 컬럼들을 읽지도 쓰지도 않는다(v1.1.0 설계 변경). |
| [MODIFY] | `frontend/src/types/order.ts`의 `Order`(`:8-23`) | `margin_rate: string \| null`, `logistics_display: string \| null`, `purchase_display: string \| null` 3개 필드 추가. |
| [MODIFY] | `frontend/src/types/order.ts`의 `OrderListParams`(`:64-73`) | `logistics_display?: string` 추가. |
| [MODIFY] | `frontend/src/features/order/hooks/useOrders.ts`(`:13-21`) | `logistics_display` 파라미터를 기존 매핑 패턴대로 전달. |
| [MODIFY] | `frontend/src/pages/OrdersPage.tsx` | 결제상태/출고상태 열(`:284-285`) 및 두 필터 드롭다운(`:203-214`, `:229-239`) 제거. `getFulfillmentLabel`(`:96-104`) 삭제. `getDisplayStatus`(`:81-94`)의 앞 3개 분기만 배지 판별식으로 재사용(뒤의 결제상태 라벨 맵은 배지에 쓰지 않음 — 남은 사용처가 없다면 죽은 코드가 되므로 plan.md가 처리 방침을 정한다). 물류상태/발주상태/마진율 열 추가, 물류상태 필터 드롭다운 추가, `colSpan={8}`(`:293`) → `9`로 갱신. 배지에 `data-testid="cancel-badge"` 부여. |
| [MODIFY] | `frontend/src/pages/OrdersPage.test.tsx` | 배지·신규 3열·필터 드롭다운에 대한 신규 테스트 추가. |
| [MODIFY] | `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`의 `buildOrder()`(`:28-45`) | `Order` 타입에 3개 필수 필드가 추가되므로 이 리터럴도 기본값(`margin_rate: null, logistics_display: null, purchase_display: null`)을 갖추지 않으면 `tsc -b`가 깨진다(감사 발견 — SPEC-ORDER-021 v1.4.0의 `SearchTab.test.tsx:47` `buildOrderDetail()` 사례와 동일한 패턴). |
| [EXISTING] | `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx` | 무수정 — 이 SPEC이 건드리는 것은 위 테스트 픽스처의 타입 정합성뿐이며, `SearchTab`의 렌더링 로직 자체는 `OrdersPage`의 테이블과 완전히 분리된 별도 컴포넌트다. |

## 관련 SPEC

- **SPEC-ORDER-021** — `margin_amount`/`margin_rate` 계산 공식과 `_get_exchange_rate` 폴백 조회(`effective_date <= order_date` 중 최신)의 원 SPEC. 이 SPEC은 그 공식을 그대로 재사용하며, `_get_exchange_rate`의 "주문 단위 메모이제이션"이 리스트 요청에는 부적합하다는 사실(문제 정의 참조)이 이 SPEC의 핵심 동인이다. **이 SPEC은 SPEC-ORDER-021의 Exclusion 한 항목을 명시적으로 supersede한다**: SPEC-ORDER-021 `spec.md:373`은 "`OrderListSerializer`(목록 API)에 비용/마진 필드를 노출하지 않는다. 기존 관례 유지(REQ-COST-014)"를 Exclusion으로 명시했고 `:61`은 `OrderListSerializer`를 `[EXISTING] 무수정`으로 표시했다 — REQ-OLIST-016(`margin_rate` 노출)은 이 문서적 결정을 뒤집는다. 계약 충돌은 아니다 — REQ-COST-014 자체와 `test_spec_021.py`의 T10(`test_t10_list_endpoint_does_not_expose_cost_breakdown`, `:321-334`)은 `shipping_cost`/`korea_warehouse_cost`/`total_weight_grams` 3키만 금지하며 `margin_rate`는 언급하지 않으므로 T10은 이 SPEC 이후에도 그대로 통과한다. SPEC-ORDER-021 문서에 상호 참조를 남기는 것은 후속 과제로 둔다.
- **SPEC-ORDER-022** — `ExchangeRate` 테이블 자동 갱신·백필. 이 SPEC은 그 테이블이 일 단위로 촘촘하다는 전제 위에서 배치 로드를 설계한다(설계 결정 A).
- **SPEC-ORDER-011** — `LineItem.logistics_status`/`Order.status` 집계 파이프라인, `_recompute_order_aggregates`의 "trackable(=`sku` not null)" 정의 및 uniform/partial 집계 규칙의 원 SPEC. 이 SPEC은 그 **정의와 집계 규칙**을 재사용하지만(가정 2), `Order.status` **컬럼 자체는 읽지 않는다**(v1.1.0 설계 변경, C3 참조) — 저장된 집계값이 아니라 매 요청 시 동일 규칙으로 독립 재계산한다.
- **SPEC-ORDER-015** — `LineItem.shipped_quantity`/`shipped_at` 필드 도입. `purchase_order_views.py:3411,3456,3972`가 `shipped_quantity >= quantity`일 때만 `logistics_status`를 `"shipped"`로 쓴다는 사실(문제 정의 참조)이 규칙 1/2의 프로덕션 동시 성립과 AC-OLIST-006/022 픽스처 설계의 근거다.

---

## 요구사항 (EARS)

### 모듈 1 — 결제상태/출고상태 열 제거 및 취소 배지 (프론트엔드)

**REQ-OLIST-001** (Ubiquitous): The `OrdersPage` results table shall NOT render a 결제상태 (payment status) column.

**REQ-OLIST-002** (Ubiquitous): The `OrdersPage` results table shall NOT render a 출고상태 (fulfillment status) column.

**REQ-OLIST-003** (Ubiquitous): The `OrdersPage` filter row shall NOT render a 결제상태 filter dropdown or a 출고상태 filter dropdown.

**REQ-OLIST-004** (Event-Driven): When a row's order has `financial_status === 'refunded'`, the system shall render an element with `data-testid="cancel-badge"` containing the text "취소", adjacent to that row's order-number cell.

**REQ-OLIST-005** (Event-Driven): When a row's order does not satisfy REQ-OLIST-004 and (`financial_status === 'partially_refunded'` OR `has_refund === true`), the system shall render an element with `data-testid="cancel-badge"` containing the text "부분취소", adjacent to that row's order-number cell.

**REQ-OLIST-006** (Unwanted): If neither REQ-OLIST-004 nor REQ-OLIST-005 applies to a row, then the system shall NOT render any element with `data-testid="cancel-badge"` for that row — including any element derived from `getDisplayStatus`'s payment-status label branches (`OrdersPage.tsx:86-93`).

### 모듈 2 — 물류상태 파생 (백엔드, `LineItem`에서 직접 파생 — `Order.status`는 읽지 않는다)

**REQ-OLIST-007** (Ubiquitous): For every order, the system shall evaluate only that order's trackable line items — `LineItem` rows where `sku` is not null — when computing `logistics_display`, and shall NOT read the stored `Order.status` column at any point in that computation.

**REQ-OLIST-008** (State-Driven): While an order has at least one trackable line item and every trackable line item's `logistics_status` equals `"shipped"`, the system shall set that order's `logistics_display` to `"shipped"`.

**REQ-OLIST-009** (State-Driven): While REQ-OLIST-008 does not hold for an order and at least one of its trackable line items has `shipped_quantity` greater than `0`, the system shall set `logistics_display` to `"partial_shipped"`.

**REQ-OLIST-010** (State-Driven) [GUARD ADDED v1.2.0, C1-new]: While an order has at least one trackable line item, neither REQ-OLIST-008 nor REQ-OLIST-009 holds for it, and every one of its trackable line items has `logistics_status` equal to `"received"`, the system shall set `logistics_display` to `"outbound_scheduled"`.

**REQ-OLIST-011** (State-Driven) [GUARD ADDED v1.2.0, C1-new]: While an order has at least one trackable line item, none of REQ-OLIST-008 through REQ-OLIST-010 holds for it, and the order's trackable line items share a single identical `logistics_status` value, the system shall set `logistics_display` to that shared value, computed directly from the trackable line items at request time (this value is necessarily one of `not_shipped`/`shipment_confirmed`/`outbound_scheduled`, since REQ-OLIST-008/010 already exhaust the uniform-`shipped`/uniform-`received` cases).

**REQ-OLIST-011a** (State-Driven) [GUARD ADDED v1.2.0, symmetry with 010/011]: While an order has at least one trackable line item, none of REQ-OLIST-008 through REQ-OLIST-010 holds for it, and its trackable line items' `logistics_status` values are NOT all identical (two or more distinct values present — which is only possible when at least one trackable line item exists), the system shall set `logistics_display` to `"partial"`.

**REQ-OLIST-012** (State-Driven): While an order has zero trackable line items, the system shall set `logistics_display` to `null`.

**모듈 2 완전성·배타성 재검증 (v1.2.0, C1-new 대응; v1.2.1에서 근거 문장 정정, 감사 N6).** REQ-OLIST-008~012를 trackable 집합 T 위에서 다시 대입한다: (a) `|T|=0` → REQ-OLIST-012만 발화 → 결과 `null`, 유일. `008`/`010`/`011`/`011a`는 "at least one trackable line item"으로 명시적으로 가드되어 있어 이 경우 발화하지 않는다. **`009`에는 그 문구가 없지만, "at least one of its trackable line items has `shipped_quantity` greater than `0`"이라는 존재 한정사(`∃`)가 공집합에서 자동으로 거짓이 되므로 별도의 명시적 가드 없이도 안전하다** — 008/010/011/011a와 009는 "안전한 이유"가 다를 뿐, 결과(빈 집합에서 발화하지 않음)는 동일하다. (b) `|T|≥1`이면 008/009/010/011/011a 다섯 규칙이 서로의 부정으로 순차 가드되어 있어("REQ-OLIST-008 does not hold", "none of REQ-OLIST-008 through REQ-OLIST-010 holds" 등) 각 주문은 정확히 하나의 규칙에서만 발화한다 — 정확히 하나가 참인 이유는, "모든 trackable이 uniform"(011) 아니면 "2개 이상의 distinct 값"(011a) 둘 중 정확히 하나가 항상 성립하기 때문이다(합이 전체를 덮고 서로 배타적). 따라서 치역은 `{shipped, partial_shipped, outbound_scheduled, not_shipped, shipment_confirmed, partial, null}`이며 이 7개 값 중 정확히 하나로 항상 귀결된다.

### 모듈 3 — 발주상태 파생 (백엔드)

**REQ-OLIST-013** (State-Driven) [REWRITTEN v1.4.0 — the previous wording tested `purchase_status` alone, which mislabelled 3,524 of 3,613 trackable orders as 미발주 in production; see HISTORY v1.4.0]: While an order has at least one trackable line item and at least one of its trackable line items is *awaiting purchase* — defined identically to `_reorder_candidate_filter` (`backend/order/purchase_order_views.py:107-110`) as either (a) `purchase_status == "unordered"` **and** the line item is linked to zero `PurchaseOrder` rows, or (b) `purchase_status == "damaged_exchange"` regardless of `PurchaseOrder` linkage — the system shall set that order's `purchase_display` to `"unordered"`.

**REQ-OLIST-014** (State-Driven) [REWRITTEN v1.4.0]: While an order has at least one trackable line item and none of its trackable line items is *awaiting purchase* as defined in REQ-OLIST-013, the system shall set `purchase_display` to `"ordered"` — this includes (1) orders whose trackable line items all carry `purchase_status == "unordered"` but are each linked to at least one `PurchaseOrder` (the dominant production case, ~97% of orders), and (2) orders whose trackable line items are all `purchase_status == "order_cancelled"` (명시적 가정 4, unchanged by v1.4.0 — `order_cancelled` is not `unordered`, so it never triggers 미발주 under the new rule either).

**REQ-OLIST-014a** (Ubiquitous) [HARD] [NEW v1.4.0]: The *awaiting purchase* predicate of REQ-OLIST-013 shall stay in lockstep with `_reorder_candidate_filter` — an order's `purchase_display` shall equal `"unordered"` if and only if at least one of its trackable line items would be returned by `UnorderedItemsView` for that same database state. The system shall NOT reintroduce a `purchase_status`-only derivation on any code path.

**REQ-OLIST-015** (State-Driven): While an order has zero trackable line items, the system shall set `purchase_display` to `null`.

### 모듈 4 — 마진율 노출 (백엔드)

**REQ-OLIST-016** (Ubiquitous): `OrderListSerializer` shall expose `margin_rate` computed by the identical formula `OrderDetailSerializer.get_margin_rate` uses — `margin_usd / total_price_usd × 100`, quantized to 2 decimal places with ROUND_HALF_UP exactly once from the unrounded Decimal components, where `margin_usd` includes the confirmed-cost, shipping-cost, and Korea-warehouse-cost terms.

**REQ-OLIST-017** (Unwanted) [EXPANDED v1.1.0]: If any of the following holds for an order — (1) no `ExchangeRate` resolves for the order's date (including the case where `shopify_created_at` is `null`, `serializers.py:245`), OR (2) no line item of the order has a non-null `confirmed_price`, OR (3) `total_price` is `0` or `null` (a `null` `total_price` is treated as `0`, `serializers.py:322`) — then the system shall return `null` for `margin_rate`.

**REQ-OLIST-018** (Ubiquitous) [HARD]: `OrderListSerializer` shall NOT expose `margin_amount`, `shipping_cost`, `korea_warehouse_cost`, `confirmed_cost`, `total_cost`, or `total_weight_grams`.

### 모듈 5 — 성능 불변식 (배치 환율 로드)

**REQ-OLIST-019** (Ubiquitous) [HARD]: The system shall resolve every order's applicable `ExchangeRate` for a single `GET /api/orders/` request via at most one query against the `ExchangeRate` table, regardless of page size (up to 50) or the number of distinct order dates present in that page.

**REQ-OLIST-020** (Ubiquitous) [EXPANDED v1.2.0, M5-new/L7]: The exchange rate resolved for a given order date under REQ-OLIST-019 shall equal the value `_get_exchange_rate` would resolve for that same date — the most recent `ExchangeRate` whose `effective_date` is less than or equal to that order's date, with no lower bound on how far back that search may reach. The order's date shall be derived by calling `.date()` directly on the order's `shopify_created_at` attribute — the identical method `_get_exchange_rate` uses (`serializers.py:248`) — and NOT via `django.utils.timezone.localtime()` or any other timezone-converting call, so that the resolved date is identical regardless of the deployment's configured `TIME_ZONE` setting (`backend/config/settings/base.py:92` currently pins `TIME_ZONE = "UTC"`, but this requirement must hold independent of that value).

**REQ-OLIST-021** (Ubiquitous) [HARD] [AMENDED v1.4.0 — the `PurchaseOrder` linkage REQ-OLIST-013 now requires cannot be read from the `line_items` prefetch alone]: `logistics_display` and `purchase_display` shall be computed only from data already available in `OrderListView`'s `prefetch_related` caches — `line_items` for both derivations, plus `line_items__purchase_orders` for the linkage half of REQ-OLIST-013 — without issuing any per-order or per-line-item database query. Reading the linkage via `li.purchase_orders.exists()` or `LineItem.objects.filter(...)` inside the serializer is forbidden: both bypass the prefetch cache and issue one query per line item.

**REQ-OLIST-022** (Ubiquitous) [HARD] [REWRITTEN v1.1.0 — was "no increase vs. before this SPEC", which literally contradicted REQ-OLIST-019's intentional +1 batch query]: The total number of SQL queries issued to serve a `GET /api/orders/` request shall be constant with respect to page size and the number of distinct order dates in the page (O(1)) — it shall NOT grow as more orders or more distinct dates are added to a page.

**REQ-OLIST-022a** (Ubiquitous) [HARD] [REWRITTEN v1.2.0, H3-new — "plus exactly 1" contradicted `plan.md`'s conditional skip optimization for an all-null-date page, which is a reachable state since `shopify_created_at` is nullable (`models.py:77`) and the list is ordered by `-shopify_created_at` (`views.py:163`), so an all-NULL final page is reachable]: The pre-SPEC-023 baseline query count for `GET /api/orders/` on a given page is 6 when the page contains at least one order with a non-null `customer`, or 5 when every order in the page has `customer == null` (1 JWT-authentication user lookup + 1 pagination `COUNT(*)` + 1 main `Order` `SELECT` + `prefetch_related` queries for `refunds`/`line_items` always, plus `customer` only when at least one non-null value exists to fetch, `backend/order/views.py:162`). Relative to that baseline, the post-SPEC-023 total shall equal the baseline plus **at most 2** [AMENDED v1.4.0 — was "at most 1"; the `line_items__purchase_orders` prefetch REQ-OLIST-021 now mandates adds exactly one further constant query] — 1 additional query for the batched `ExchangeRate` load (REQ-OLIST-019) when the page contains at least one order with a non-null `shopify_created_at` (and exactly 0 when every order in the page has `shopify_created_at == null`, the batch query being skipped entirely per the conditional-skip design `plan.md` specifies), plus exactly 1 additional query for the `line_items__purchase_orders` M2M prefetch — and never more than that in any case. The customer-presence and date-presence conditions are independent of each other; the delta applies identically whether the page's baseline is 5 or 6. Crucially, the M2M prefetch query count does not depend on page size or on the number of line items in the page — Django issues exactly one `orders_purchaseorder_line_items` join query for the whole page regardless.

### 모듈 6 — 물류상태 필터 (백엔드 + 프론트엔드, `LineItem`에서 직접 파생)

**REQ-OLIST-023** (Event-Driven): When a client supplies a `logistics_display` query parameter on `GET /api/orders/` with one of the six values in REQ-OLIST-024, the system shall return only orders whose derived `logistics_display` (REQ-OLIST-007 through REQ-OLIST-011a) equals the supplied value, computed via query-level predicates over `LineItem` rows only (never over `Order.status`).

**REQ-OLIST-024** (Ubiquitous): The accepted values for the `logistics_display` query parameter shall be exactly `{not_shipped, shipment_confirmed, outbound_scheduled, partial_shipped, shipped, partial}`.

**REQ-OLIST-024a** (Unwanted) [NEW v1.1.0] [WORDING CLARIFIED v1.2.1, L8-new]: If the `logistics_display` query parameter is supplied with a value outside the set in REQ-OLIST-024, then the system shall ignore **this filter** and return the result set as if the `logistics_display` parameter had not been supplied (other query parameters' filtering, e.g. `financial_status`/`fulfillment_status`, still applies as normal — fail-open, consistent with this endpoint's existing unvalidated `financial_status`/`fulfillment_status` parameters, `views.py:171-173`, `:186-191`) — it shall NOT raise an error and shall NOT silently return zero results.

**REQ-OLIST-025** (Ubiquitous) [HARD]: The `logistics_display` filter shall be implemented at the query level (annotations/`Exists` subqueries evaluated inside the single list query) and shall NOT add a per-row query.

**REQ-OLIST-026** (Ubiquitous): The `OrdersPage` filter row shall include a 물류상태 dropdown offering "전체" plus the six values in REQ-OLIST-024, labeled 미입고/입고예정/출고예정/부분출고/출고/부분입고 respectively.

**REQ-OLIST-027** (Event-Driven): When the user selects a value from the 물류상태 dropdown, the system shall include it as the `logistics_display` query parameter on the subsequent `GET /api/orders/` request.

### 모듈 7 — 프론트엔드 렌더링

**REQ-OLIST-028** (Ubiquitous): The `OrdersPage` results table shall render exactly 9 columns in this order: 주문번호(취소 배지 포함) / 스토어 / 위치 / 고객 / 물류상태 / 발주상태 / 마진율 / 금액 / 주문일.

**REQ-OLIST-029** (Ubiquitous): The empty-results row's `colSpan` shall equal `9`.

**REQ-OLIST-030** (Event-Driven): When an order's `logistics_display` is `null`, the system shall render `"-"` in that row's 물류상태 cell; otherwise it shall render the Korean label corresponding to the value (REQ-OLIST-024's six values).

**REQ-OLIST-031** (Event-Driven): When an order's `purchase_display` equals `"unordered"`, the system shall render "미발주"; when it equals `"ordered"`, it shall render "발주완료"; when it is `null`, it shall render `"-"`.

**REQ-OLIST-032** (Event-Driven): When an order's `margin_rate` is non-null, the system shall render it as `"{value}%"`; when it is `null`, it shall render `"-"`.

### 모듈 8 — 회귀 방지

**REQ-OLIST-033** (Ubiquitous) [라벨 교정 v1.1.0: Unwanted → Ubiquitous — "If...then" 트리거 조건 없는 순수 부정문이므로, SPEC-ORDER-021 REQ-COST-014와 동일한 관례]: The system shall NOT modify `OrderDetailSerializer`'s field set or any of its computed values as a result of this SPEC.

**REQ-OLIST-034** (Ubiquitous) [라벨 교정 v1.1.0: Unwanted → Ubiquitous, 사유는 REQ-OLIST-033과 동일]: The system shall NOT remove or alter the `financial_status`/`fulfillment_status` query-param filters in `OrderListView.get_queryset` (`backend/order/views.py:171`, `:186`).

---

## 인수 기준

[HARD] 각 인수 기준은 굵게 표시한 EARS 연결어(**While**/**When**/**If**/**then**/**shall**)를 포함한 완전한 문장이다(v1.1.0, MP-2 대응 — SPEC-ORDER-021 형식으로 복귀). 각 항목은 자신을 깨뜨리는 mutation을 명시한다. 실행 가능한 Given/When/Then 시나리오는 `acceptance.md`에 있으며 동일한 `Traces:` 목록을 인용한다.

**AC-OLIST-001** (Event-Driven) — 취소 배지. Traces: REQ-OLIST-004, REQ-OLIST-006. **When** a row's order has `financial_status === 'refunded'`, the system **shall** render `data-testid="cancel-badge"` containing "취소" adjacent to the order-number cell.
*Mutation*: 배지 판별을 `has_refund`만으로 구현하면(`financial_status` 무시) `refunded`가 아닌데 `has_refund=true`인 주문에서 "취소"와 "부분취소"를 구분하지 못한다.

**AC-OLIST-002** (Event-Driven) — 부분취소 배지(명시적 부분환불). Traces: REQ-OLIST-005, REQ-OLIST-006. **When** a row's order has `financial_status === 'partially_refunded'`(NOT `refunded`), the system **shall** render `data-testid="cancel-badge"` whose text is **exactly** "부분취소"(NOT "취소" — `{ exact: true }` 또는 정확 문자열 비교, "부분취소"가 "취소"를 부분문자열로 포함하므로 느슨한 매칭은 오탐을 낸다, 감사 M3).

**AC-OLIST-003** (Event-Driven) — 부분취소 배지($0 취소, `getDisplayStatus` 주석의 엣지케이스). Traces: REQ-OLIST-005. **When** a row's order has `financial_status === 'paid'` and `has_refund === true`, the system **shall** render `data-testid="cancel-badge"` containing "부분취소".
*Mutation*: 배지 판별을 `financial_status`만으로 구현하면(`has_refund` 무시) 이 케이스가 배지 없음으로 잘못 렌더된다.

**AC-OLIST-004** (Ubiquitous) [강화 v1.1.0, H6] — 정상 주문에는 배지 요소 자체가 없다. Traces: REQ-OLIST-006. **While** an order has `financial_status === 'paid'` and `has_refund === false`, the system **shall NOT** render any element with `data-testid="cancel-badge"` for that row.
*Mutation*: `getDisplayStatus`를 문자 그대로(결제상태 라벨 맵까지) 재사용해 "결제완료" 같은 라벨을 `data-testid="cancel-badge"` 요소에 담아 렌더하면, 텍스트만 확인하는 단정(구버전)은 통과하지만 이 AC(요소 자체의 부재)는 실패한다 — 이것이 H6가 지목한 정확한 결함이다.

**AC-OLIST-005** (Ubiquitous) — 9열 구성 및 결제/출고상태 열·필터 제거. Traces: REQ-OLIST-001, REQ-OLIST-002, REQ-OLIST-003, REQ-OLIST-028, REQ-OLIST-029. **While** `OrdersPage` renders with normal data, the system **shall** omit "결제상태"/"출고상태" text from both the table headers and the filter row, **shall** render 9 headers in DOM order 주문번호/스토어/위치/고객/물류상태/발주상태/마진율/금액/주문일(`compareDocumentPosition`으로 단정), and **shall** set the empty-results row's `colSpan` to `9`.
*Mutation*: 열은 추가했지만 `colSpan`을 8로 남겨두면 빈 상태에서 레이아웃이 깨진다(테스트가 정확한 값 9를 단정).

**AC-OLIST-006** (State-Driven) [C2 수정 — 프로덕션 불가능 상태 픽스처 교체] — 물류상태: 전 trackable 항목 출고 완료(현실적 픽스처). Traces: REQ-OLIST-008. **While** an order has a single trackable line item with `logistics_status='shipped'` **and** `shipped_quantity == quantity`(양수, 예: `quantity=5, shipped_quantity=5` — `purchase_order_views.py:3411/3456/3972`가 강제하는 실제 프로덕션 상태. `shipped_quantity`를 기본값 `0`으로 방치하면 규칙 2가 발화하지 않아 순서 역전 mutation을 잡지 못한다), the system **shall** set `logistics_display` to `"shipped"`.
*Mutation*: 규칙 2("하나 이상 `shipped_quantity>0`")를 규칙 1보다 먼저 평가하면, 이 픽스처는 `shipped_quantity=5>0`이므로 규칙 2가 먼저 발화해 `"partial_shipped"`(오답)를 반환한다 — 프로덕션에서 실제로 발생 가능한 가장 흔한 순서 오류다(문제 정의 참조).

**AC-OLIST-007** (State-Driven) — 부분출고 판별(`>= quantity` 대 `> 0` mutation). Traces: REQ-OLIST-009. **While** an order has two trackable line items — A(`logistics_status='outbound_scheduled', shipped_quantity=4, quantity=10`), B(`logistics_status='outbound_scheduled', shipped_quantity=0, quantity=5`) — the system **shall** set `logistics_display` to `"partial_shipped"`.
*Mutation*: 조건을 `shipped_quantity >= quantity`로 구현하면 A(4≥10 거짓), B(0≥5 거짓) 모두 거짓이 되어 규칙 2가 트리거되지 않고, 두 아이템의 `logistics_status`가 균일(`outbound_scheduled`)하므로 규칙 4로 낙하해 `"outbound_scheduled"`(오답)를 반환한다.

**AC-OLIST-008** (State-Driven) — `shipped_quantity=0` 경계(부분출고 아님). Traces: REQ-OLIST-009, REQ-OLIST-011. **While** an order has a single trackable line item with `logistics_status='not_shipped', shipped_quantity=0, quantity=5`, the system **shall** set `logistics_display` to `"not_shipped"`(NOT `"partial_shipped"`).
*Mutation*: 조건을 `shipped_quantity >= 0`(또는 `is not None`)으로 구현하면 이 케이스도 `"partial_shipped"`로 잘못 판정된다.

**AC-OLIST-009** (State-Driven) [HARD] — 우선순위 역전 판별(규칙 3을 규칙 2보다 먼저 평가하는 mutation). Traces: REQ-OLIST-009, REQ-OLIST-010. **While** an order has a single trackable line item with `logistics_status='received', shipped_quantity=3, quantity=10`, the system **shall** set `logistics_display` to `"partial_shipped"`(NOT `"outbound_scheduled"`).
*Mutation*: 규칙 3("모두 received → 출고예정")을 규칙 2보다 먼저 평가하면, 이 단일 아이템이 `received` 하나뿐이므로 "모두 received"가 참이 되어 `"outbound_scheduled"`(오답)를 반환한다 — SPEC-ORDER-015(`purchase_order_views.py:3411,3456,3972`)가 확인한 "부분출고가 `logistics_status`를 이동시키지 않는다"는 동작 때문에 이 조합(received + shipped_quantity>0)이 실제로 발생 가능하다.

**AC-OLIST-010** (State-Driven) — 전부 입고완료 → 출고예정. Traces: REQ-OLIST-010. **While** an order has two trackable line items both with `logistics_status='received', shipped_quantity=0`, the system **shall** set `logistics_display` to `"outbound_scheduled"`.

**AC-OLIST-011** (State-Driven) [HARD] [확장 v1.1.0, H4 — `purchase_display` 단정 추가] — non-trackable 항목 제외 판별(물류·발주 양쪽). Traces: REQ-OLIST-007, REQ-OLIST-013. **While** an order has one trackable line item(`sku="ISBN001", logistics_status='received', shipped_quantity=0, quantity=5, purchase_status='in_stock'`) and one non-trackable line item(`sku=None, shipped_quantity=99, purchase_status='unordered'`(모델 기본값, `models.py:193`) — 값을 명시하지 않아도 기본값으로 자동 성립), the system **shall** set `logistics_display` to `"outbound_scheduled"`(NOT `"partial_shipped"`) **and shall** set `purchase_display` to `"ordered"`(NOT `"unordered"`).
*Mutation(물류)*: `sku__isnull=False` 필터를 물류 경로에서 빠뜨리고 전체 라인아이템을 평가하면 non-trackable 항목의 `shipped_quantity=99>0`이 규칙 2를 트리거해 `logistics_display == "partial_shipped"`(오답)를 반환한다.
*Mutation(발주, H4)*: `sku__isnull=False` 필터를 발주 경로에서 빠뜨리면, non-trackable 항목의 `purchase_status`가 모델 기본값 `"unordered"`이므로 `purchase_display == "unordered"`(오답)를 반환한다 — trackable 항목은 `"in_stock"`이므로 필터가 올바르면 "unordered" 조건에 해당하는 trackable 항목이 없어 `"ordered"`가 나와야 한다.

**AC-OLIST-012** (Unwanted) [강화 v1.1.0, H1 — 키 존재 단정 추가] — trackable 없음 → `logistics_display` 키는 존재하되 값이 `null`. Traces: REQ-OLIST-012. **If** an order has zero trackable line items(모든 라인아이템 `sku=None`, 또는 라인아이템 자체가 없음), **then** the response item **shall** contain the key `"logistics_display"` **and** its value **shall** be `null`(`"logistics_display" in item` **그리고** `item["logistics_display"] is None` 이중 단정 — `.get(...)`만 쓰면 필드 미구현 상태에서도 통과해버린다, SPEC-ORDER-021 감사 D6 재발 방지).
*Mutation*: 필드를 아예 구현하지 않으면(`Meta.fields` 누락) 키 존재 단정이 실패한다 — 이중 단정이 없으면 이 mutation은 (필드 없음 → `.get()` → `None`) 경로로 정상 통과해버린다.

**AC-OLIST-013** (State-Driven) — 규칙 4 통과값 정확성(uniform, 단일 값). Traces: REQ-OLIST-011. **While** an order has a single trackable line item with `logistics_status='shipment_confirmed', shipped_quantity=0`, the system **shall** set `logistics_display` to `"shipment_confirmed"`.

**AC-OLIST-013a** (State-Driven) [신규 v1.1.0, 규칙 4a] — 규칙 4a: 혼재 상태 → 부분입고. Traces: REQ-OLIST-011a. **While** an order has two trackable line items with distinct `logistics_status` values that satisfy none of REQ-OLIST-008~010(예: A는 `not_shipped`, B는 `shipment_confirmed`, 둘 다 `shipped_quantity=0`), the system **shall** set `logistics_display` to `"partial"`.
*Mutation*: uniform 판정을 생략하고 그냥 첫 번째 라인아이템의 값을 반환하면(정렬 순서에 따라 `"not_shipped"` 또는 `"shipment_confirmed"`) `"partial"`과 어긋난다.

**AC-OLIST-014** (State-Driven) [HARD] [강화 v1.4.0 — 기존 픽스처는 `PurchaseOrder`를 하나도 만들지 않아 링크 조건 누락을 판별하지 못했다] — 미발주 판별(`any` 대 `all` mutation + 링크 조건 동시 판별). Traces: REQ-OLIST-013. **While** an order has two trackable line items — A(`purchase_status='unordered'`, 연결된 `PurchaseOrder` 없음), B(`purchase_status='unordered'`이면서 `status='confirmed'`인 `PurchaseOrder` 1건에 연결) — the system **shall** set `purchase_display` to `"unordered"`(A 때문에), **and** removing A from the same fixture **shall** flip the value to `"ordered"`(B 단독으로는 미발주가 아님을 같은 테스트 안에서 확인).

**AC-OLIST-014a** (State-Driven) [HARD] [NEW v1.4.0 — 프로덕션 결함 `#38360`의 직접 재현] — 발주서에 연결된 `unordered` 항목은 미발주가 아니다. Traces: REQ-OLIST-013, REQ-OLIST-014, REQ-OLIST-014a. **While** an order reproduces `#38360`'s exact shape — 8 trackable line items, every one with `purchase_status='unordered'` and each linked to its own `status='confirmed'` `PurchaseOrder` — the system **shall** set `purchase_display` to `"ordered"`. **Mutation 근거**: v1.3.0 구현(`purchase_status` 단독 검사)에서 이 AC는 `"unordered"`를 반환해 반드시 실패한다.

**AC-OLIST-014b** (State-Driven) [HARD] [NEW v1.4.0] — `damaged_exchange`는 발주서 연결과 무관하게 미발주다. Traces: REQ-OLIST-013(b), REQ-OLIST-014a. **While** an order has two trackable line items — A(`purchase_status='damaged_exchange'`, `status='confirmed'`인 `PurchaseOrder` 1건에 **연결됨**), B(`purchase_status='in_stock'`) — the system **shall** set `purchase_display` to `"unordered"`. **Mutation 근거**: 링크 조건을 `purchase_status`와 무관하게 일괄 적용하면(즉 `damaged_exchange`에도 링크 예외를 적용하면) 이 AC는 `"ordered"`를 반환해 실패하며, 그 구현은 미발주 목록 탭과 어긋난다(REQ-OLIST-014a 위반).
*Mutation*: 조건을 "모든 trackable 항목이 unordered"로 구현하면(all) A/B가 섞여 있으므로 거짓이 되어 `"ordered"`(오답)를 반환한다.

**AC-OLIST-015** (State-Driven) — 발주완료 판별. Traces: REQ-OLIST-014. **While** an order has two trackable line items, neither *awaiting purchase*(예: `in_stock`, `cs_required` — 둘 다 `PurchaseOrder` 연결 없음), the system **shall** set `purchase_display` to `"ordered"`.

**AC-OLIST-016** (Unwanted) [강화 v1.1.0, H1 — 키 존재 단정 추가; L8 — "라인아이템 자체 없음" 케이스도 포함] — trackable 없음 → 키 존재 + `null`. Traces: REQ-OLIST-015. **If** an order has zero trackable line items — 두 하위 케이스 모두: (a) 모든 라인아이템 `sku=None`, (b) 라인아이템 자체가 0개 — **then** the response item **shall** contain the key `"purchase_display"` **and** its value **shall** be `null`.

**AC-OLIST-017** (Ubiquitous) — `margin_rate` 값 및 필드 노출 범위. Traces: REQ-OLIST-016, REQ-OLIST-018. **While** an order has `total_price="100.00"`, a valid `ExchangeRate(rate="1000.00")`, and a line item `quantity=3, confirmed_price="10000.00", grams=0`(SPEC-ORDER-021 AC-COST-001과 동일 픽스처), the system **shall** report `margin_rate == "67.75"` **and shall NOT** include the keys `margin_amount`/`shipping_cost`/`korea_warehouse_cost`/`confirmed_cost`/`total_cost`/`total_weight_grams` in the response item.
*Mutation*: `margin_rate`를 배송비·한국창고비를 뺀 `confirmed_cost_usd`만으로 계산하면(`100-30=70` → `"70.00"`) 정답(`"67.75"`)과 어긋난다. 상세 시리얼라이저의 필드 집합을 그대로 재사용하면 금지된 6개 키 중 하나 이상이 응답에 나타난다.

**AC-OLIST-017a** (State-Driven) [신규 v1.1.0, 감사 M2 — 반올림 순서 판별] — 마진율은 반올림 전 정확값의 합에서 한 번만 양자화한다. Traces: REQ-OLIST-016. **While** an order has `total_price="100.00"`, `ExchangeRate(rate="1000.00")`, and a line item `quantity=1, grams=500, confirmed_price="10005.00"`(SPEC-ORDER-021 AC-COST-015/016과 동일 픽스처 — `confirmed_cost_usd=10.005`, `shipping_cost_usd=2.725`가 개별 반올림 시 각각 올림되도록 의도적으로 고른 값), the system **shall** report `margin_rate == "86.02"`(계산: `margin_usd = 100 - 10.005 - 2.725 - 1.25 = 86.020`, 반올림 전 정확값의 합에서 한 번만 양자화).
*Mutation*: 이미 개별 양자화된 `confirmed_cost="10.01"`(`.005`가 올림), `shipping_cost="2.73"`(`.725`가 올림), `korea_warehouse_cost="1.25"` 문자열을 목록 전용 코드가 재파싱해 `100-10.01-2.73-1.25=86.01`로 구하면 정답(`"86.02"`)과 **1센트** 어긋난다 — SPEC-ORDER-021 AC-COST-015가 `total_cost`에서 이미 검증한 것과 동일한 반올림-순서 함정을, 목록 엔드포인트의 `margin_rate` 하나의 관측 가능한 필드로 재현한다.

**AC-OLIST-018** (Unwanted) [강화 v1.1.0, H1 — 키 존재 단정 추가] — `margin_rate` null 게이트(원인 2: 확정 매입가 전무). Traces: REQ-OLIST-017. **If** an order has a valid `ExchangeRate` but no line item with a non-null `confirmed_price`, **then** the response item **shall** contain the key `"margin_rate"` **and** its value **shall** be `null`.

**AC-OLIST-018a** (Unwanted) [신규 v1.1.0, H3 — 원인 1] — `margin_rate` null 게이트(원인 1: 환율 없음). Traces: REQ-OLIST-017. **If** no `ExchangeRate` record exists at or before an order's date(확정 매입가는 있음), **then** the response item **shall** contain the key `"margin_rate"` **and** its value **shall** be `null`.
*Mutation*: 배치 로더가 "이력이 비어 있음"을 예외로 처리하거나(`IndexError`) 잘못된 폴백 값을 반환하면 이 AC가 실패한다 — 이 원인이 배치 로드 구현에서 가장 깨지기 쉬운 지점이다(감사 H3).

**AC-OLIST-018b** (Unwanted) [신규 v1.1.0, H3 — 원인 3] — `margin_rate` null 게이트(원인 3: `total_price == 0`). Traces: REQ-OLIST-017. **If** an order has `total_price="0.00"`, a valid `ExchangeRate`, and a line item with a non-null `confirmed_price`, **then** the response item **shall** contain the key `"margin_rate"` **and** its value **shall** be `null`.

**AC-OLIST-019** (State-Driven) [HARD] — 배치 환율 로드 정확성 + 쿼리 수. Traces: REQ-OLIST-019, REQ-OLIST-020. **While** a page contains two orders on different dates — X(`rate="1000.00"`, SPEC-ORDER-021 AC-COST-001 픽스처, 정답 `margin_rate="67.75"`), Y(`rate="1250.00"`, AC-COST-012 픽스처, 정답 `margin_rate="68.20"`) — the system **shall** report each order's `margin_rate` computed with its own date's rate **and shall** issue exactly 1 query referencing the `orders_exchangerate` table for the whole request.
*Mutation*: `_get_exchange_rate`를 무수정 재사용하면(주문 `pk` 단위 메모이제이션) 서로 다른 두 주문에 대해 캐시가 각각 새로 채워져 `orders_exchangerate` 참조 쿼리가 2개가 된다.

**AC-OLIST-020** (State-Driven) — 배치 로드의 폴백 보존. Traces: REQ-OLIST-020. **While** an order is dated `D` with no `ExchangeRate` record at `D` but one at `D-3`(SPEC-ORDER-021 AC-COST-001과 동일한 라인아이템 픽스처, `rate="1000.00"`), the system **shall** report `margin_rate == "67.75"`(NOT `null`).
*Mutation*: 배치 로더가 페이지의 주문일과 **정확히 일치**하는 `ExchangeRate` 행만 적재하면(폴백 없이) `D`에 해당하는 레코드가 없어 `margin_rate`가 잘못 `null`이 된다.

**AC-OLIST-020a** (State-Driven) [HARD] [신규 v1.2.0, M5-new/L7(round-1 미해소분) — 시간대 경계] — 배치 로더의 날짜 산출은 배포 `TIME_ZONE` 설정과 무관하게 `_get_exchange_rate`와 동일한 값을 낸다. Traces: REQ-OLIST-020. **While** `TIME_ZONE` is overridden to `"Asia/Seoul"`(`override_settings` — 이 프로젝트의 실제 배포값은 `backend/config/settings/base.py:92`의 `"UTC"`이지만, 이 AC는 배치 로더가 어떤 `TIME_ZONE` 값에서도 `_get_exchange_rate`와 동일하게 동작함을 증명하기 위해 의도적으로 다른 값을 쓴다), an order has `shopify_created_at="2026-08-01T23:30:00Z"`, `ExchangeRate(effective_date="2026-08-01", rate="1000.00")`, `ExchangeRate(effective_date="2026-08-02", rate="1200.00")`, and a line item `quantity=3, confirmed_price="10000.00", grams=0` with `total_price="100.00"`, the system **shall** report `margin_rate == "67.75"`(UTC 달력 날짜 `2026-08-01`의 환율 `1000.00` 사용 — `confirmed_cost_usd=30.00`, `korea_warehouse_usd=2.25`, `margin_usd=100-30-0-2.25=67.75`).
*Mutation*: 배치 로더가 `order.shopify_created_at.date()` 대신 `django.utils.timezone.localtime(order.shopify_created_at).date()`를 쓰면(KST 변환), `23:30 UTC`가 `08:30 KST` 다음날(`2026-08-02`)이 되어 `rate="1200.00"`이 잘못 적용된다 — `confirmed_cost_usd=25.00`, `korea_warehouse_usd=2250/1200=1.875`, `margin_usd=100-25-0-1.875=73.125`→`margin_rate=="73.13"`(정답 `"67.75"`와 명확히 어긋난다). 이 프로젝트의 실제 `TIME_ZONE="UTC"`에서는 이 mutation이 관측 가능한 차이를 만들지 않으므로(현지화해도 UTC이므로 무연산), `override_settings`로 다른 시간대를 강제해야만 판별 가능하다.

**AC-OLIST-021** (Ubiquitous) [HARD] [C1 재설계 — 절대상수를 SPEC 자체가 유도한다] — 전체 쿼리 수는 SPEC이 유도한 값과 정확히 같다. Traces: REQ-OLIST-021, REQ-OLIST-022, REQ-OLIST-022a. **While** a page contains 1 order versus 5 orders(둘 다 확정 매입가·유효 환율·고객 있는 trackable 라인아이템), the system **shall** issue the same total query count for both requests, **and** that count **shall equal exactly 8**[AMENDED v1.4.0 — was 7](REQ-OLIST-022a가 유도한 값: 이 SPEC 시작 시점에 이 세션에서 직접 측정한 베이스라인 6 + `ExchangeRate` 배치 쿼리 1 + `line_items__purchase_orders` M2M prefetch 1 — 아래 계산 근거 참조). 5건 페이지에서도 8이어야 한다는 점이 핵심이다 — M2M prefetch를 빠뜨리고 `li.purchase_orders.exists()`로 구현하면 1건 페이지에서는 라인아이템 수만큼, 5건 페이지에서는 그보다 훨씬 많이 늘어나 두 요청의 쿼리 수가 달라진다.
*계산 근거(구현 시점에 재실측해 이 값과 일치해야 함)*: 1(JWT 인증 사용자 조회) + 1(페이지네이션 `COUNT(*)`) + 1(본문 `Order` `SELECT`) + 3(`prefetch_related`: `refunds`/`line_items`/`customer`) + 1(배치 `ExchangeRate`) = **7**.
*Mutation*: `logistics_display`/`purchase_display` 계산이 `obj.line_items.all()` 재사용 대신 `LineItem.objects.filter(order=obj)`류의 신규 쿼리를 발급하면 주문 수에 비례해 쿼리 수가 늘어 1건 vs 5건의 값이 달라지고, 절대값도 8을 초과한다. `_get_exchange_rate`를 무수정 재사용하는 mutation은 페이지 크기 불변성(1건=5건)은 우연히 지킬 수 있어도(둘 다 주문 수만큼 늘어나므로 여전히 서로 다름 — 실제로는 불변성 자체도 깨진다) 절대값 7과 어긋난다.

**표준 물류상태 데이터셋 (Order A~H, 8건)** [신규 v1.2.0, H1-new/H2-new/M4-new 대응; v1.2.1에서 Order H 추가, 감사 N1]. AC-OLIST-022~022e는 이 데이터셋 전량을 Given으로 공유한다 — 각 AC가 서로 다른 임의의 부분집합을 고르면 판별력이 테스트 작성자의 선택에 좌우되므로, 6개 필터 값(REQ-OLIST-024) + `outbound_scheduled`의 두 번째 원인을 모두 포괄하는 고정 데이터셋 하나로 통일한다.

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

**Order H가 필요한 이유(N1)**: G는 `{not_shipped, shipment_confirmed}`만 섞여 있어 `all_not_shipped`/`all_shipment_confirmed`의 `any` mutation은 잡지만, `outbound_scheduled` uniform 검사(`all_outbound_scheduled`)를 `Exists(...filter(logistics_status="outbound_scheduled"))`(any)로 잘못 구현하는 mutation은 A~G 중 어디에도 걸리지 않는다 — `outbound_scheduled` 필터는 `¬any_partial ∧ ¬all_shipped` 가드를 먼저 통과해야 하므로 B(부분출고)는 이 가드에서 이미 걸러지고, C/D는 정상적으로 포함되어 mutation 여부와 무관하게 결과가 같다. H는 `outbound_scheduled` 항목을 포함하면서도 uniform하지 않으므로(표시값 `partial`), `any` mutation이 적용되면 H가 `outbound_scheduled` 필터 결과에 잘못 추가되어(AC-OLIST-022d의 "정확히 {C, D}" 단정을 깨뜨림) 비로소 판별된다.

**AC-OLIST-022** (Event-Driven) [H2 확장, v1.2.0에서 표준 데이터셋으로 재정렬; v1.2.1 `count` 단정 추가, 감사 N2] — 물류상태 필터: 부분출고. Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025. **When** a client requests `GET /api/orders/?logistics_display=partial_shipped` against the standard dataset(Order A~H 전량), the system **shall** return a response whose `count` field equals `1` and whose `results` contains exactly Order B, **and** Order B's `logistics_display` **shall equal** `"partial_shipped"`.
*Mutation*: 필터를 `Q(any_partial=True)`만으로 구현해 "전부 출고되지 않음(`Q(all_shipped=False)`)" 조건을 빠뜨리면, Order A(`shipped_quantity=quantity>0`이므로 `any_partial=True`이기도 함)가 잘못 포함되어 반환 집합이 {A, B}가 된다 — C2가 지목한 것과 동일한 우선순위 결함이 필터 경로에도 있다.
*Mutation(N2, REQ-OLIST-025 판별)*: `OrderListView`가 SQL 쿼리셋에 필터를 적용하는 대신, 이미 페이지네이션된 `page`(전체 8건)를 표시값 계산에 쓰는 것과 동일한 Python 헬퍼(`_derive_line_item_states`)로 사후 필터링하면 — `results`만 보면 우연히 정답과 같아 보일 수 있으나, `paginator.count`는 필터 이전의 쿼리셋 크기(8)에서 계산되므로 `count == 8`(오답, 정답은 `1`)이 되어 실패한다. 프로덕션에서는 이 결함이 페이지네이션 자체를 조용히 깨뜨린다(예: 50건 페이지에서 조건에 맞는 몇 건만 남아 `count`와 실제 표시 건수가 어긋난다).

**AC-OLIST-022a** (Event-Driven) [v1.2.0, H1-new/M4-new 재작성 — 표준 데이터셋으로 고정; v1.2.1 `count` 단정 추가] — 물류상태 필터: 출고. Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025. **When** a client requests `?logistics_display=shipped` against the standard dataset(Order A~H 전량), the system **shall** return a response whose `count` field equals `1` and whose `results` contains exactly Order A, **and** Order A's `logistics_display` **shall equal** `"shipped"`.
*Mutation(N2)*: AC-OLIST-022와 동일한 원리 — Python 사후 필터링 구현은 `results`가 우연히 맞아도 `count`가 8로 남아 실패한다.

**AC-OLIST-022b** (Event-Driven) [v1.2.0, H1-new 재작성 — 표준 데이터셋으로 고정; v1.2.1 `count` 단정 추가] — 물류상태 필터: 미입고. Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025. **When** a client requests `?logistics_display=not_shipped` against the standard dataset(Order A~H 전량, **특히 Order G를 반드시 포함**), the system **shall** return a response whose `count` field equals `1` and whose `results` contains exactly Order E, **and** Order E's `logistics_display` **shall equal** `"not_shipped"`.
*Mutation*: 필터를 `Exists(trackable_qs.filter(logistics_status="not_shipped"))`(any, uniform 아님)로 구현하면, Order G(`not_shipped` 항목을 하나 포함하지만 표시값은 `partial`)가 결과 집합에 잘못 추가되어 `count == 2`(오답, 정답은 `1`)가 된다 — 데이터셋에 Order G가 없으면 이 mutation이 발견되지 않는다(H1-new의 핵심 지적).
*Mutation(N2)*: Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

**AC-OLIST-022c** (Event-Driven) [v1.2.0, H1-new 재작성 — 표준 데이터셋으로 고정; v1.2.1 `count` 단정 추가] — 물류상태 필터: 입고예정. Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025. **When** a client requests `?logistics_display=shipment_confirmed` against the standard dataset(Order A~H 전량, **특히 Order G를 반드시 포함**), the system **shall** return a response whose `count` field equals `1` and whose `results` contains exactly Order F, **and** Order F's `logistics_display` **shall equal** `"shipment_confirmed"`.
*Mutation*: `any`(uniform 아님) 기반 구현은 Order G(`shipment_confirmed` 항목을 하나 포함)를 잘못 포함시켜 `count == 2`가 된다 — AC-OLIST-022b와 대칭인 판별 지점.
*Mutation(N2)*: Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

**AC-OLIST-022d** (Event-Driven) [v1.2.0, H2-new 강화 — 필터 ∧ 표시값 이중 단정 추가; v1.2.1 `count` 단정 추가, Order H로 any/all 판별력 확보(N1)] — 물류상태 필터: 출고예정(두 원인 모두, 필터 결과와 표시값 모두 검증). Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025. **When** a client requests `?logistics_display=outbound_scheduled` against the standard dataset(Order A~H 전량), the system **shall** return a response whose `count` field equals `2` and whose `results` contains exactly {Order C, Order D}, **and** both Order C's and Order D's `logistics_display` **shall equal** `"outbound_scheduled"`.
*Mutation*: 규칙 4를 3개 값에 대한 명시적 if-체인으로 구현하면서 `outbound_scheduled` 분기를 빠뜨리면(→ Order D가 `partial`로 잘못 계산됨), Order D가 필터 결과에서 빠질 뿐 아니라 **Order D 자신의 `logistics_display` 표시값도 `"outbound_scheduled"`가 아니게 된다** — 이전 버전은 필터 결과(Then)만 확인해 표시값 쪽 mutation을 놓쳤다(H2-new). 필터를 `Q(all_received=True)`만으로(규칙 4 경유 원인을 빠뜨리고) 구현해도 Order D가 반환 집합에서 누락되어 `count == 1`이 된다.
*Mutation(N1)*: `all_outbound_scheduled`(uniform 검사)를 `Exists(trackable_qs.filter(logistics_status="outbound_scheduled"))`(any)로 잘못 구현하면, Order H(`outbound_scheduled`+`shipment_confirmed` 혼재, 표시값은 `partial`)가 "적어도 하나는 outbound_scheduled"를 만족해 잘못 포함되어 `count == 3`(집합 {C, D, H})이 된다 — 데이터셋에 Order H가 없으면(v1.2.0처럼 A~G뿐이면) 이 mutation은 어디에도 걸리지 않는다. Order B도 `outbound_scheduled` 항목을 갖지만 `any_partial=True`이므로 이 필터의 앞단 가드(`¬any_partial`)에서 이미 제외되어 이 mutation의 신호로 쓸 수 없다 — Order H가 반드시 필요한 이유다.
*Mutation(N2)*: Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

**AC-OLIST-022e** (Event-Driven) [v1.2.0, H1-new 재작성 — 표준 데이터셋으로 고정; v1.2.1 Order H 반영해 기대 집합을 {G,H}로 갱신 + `count` 단정 추가(N1/N2)] — 물류상태 필터: 부분입고. Traces: REQ-OLIST-023, REQ-OLIST-024, REQ-OLIST-025. **When** a client requests `?logistics_display=partial` against the standard dataset(Order A~H 전량, **특히 Order D를 반드시 포함**), the system **shall** return a response whose `count` field equals `2` and whose `results` contains exactly {Order G, Order H}(둘 다 표시값 `partial` — G는 `{not_shipped, shipment_confirmed}` 혼재, H는 `{outbound_scheduled, shipment_confirmed}` 혼재), **and** both Order G's and Order H's `logistics_display` **shall equal** `"partial"`.
*Mutation*: `partial` 필터 조건에서 `¬all_outbound_scheduled`(Order D를 배제하는 조건) 절을 빠뜨리면, Order D(uniform `outbound_scheduled`)가 "3개 uniform 검사 중 어느 것도 해당 안 됨"으로 오판되어 잘못 포함되어 `count == 3`이 된다 — 데이터셋에 Order D가 없으면 이 mutation이 발견되지 않는다.
*Mutation(N2)*: Python 사후 필터링 구현은 `count`가 8로 남아 실패한다.

**AC-OLIST-022f** (State-Driven) [신규 v1.2.0, M2-new] — 허용 외 필터 값은 무시된다(fail-open). Traces: REQ-OLIST-024a. **While** the standard dataset(Order A~H 전량, 8건)가 존재하고, a client requests `?logistics_display=bogus_value`(REQ-OLIST-024의 6개 값에 속하지 않음), the system **shall** respond HTTP 200 with all 8 orders(필터를 적용하지 않은 것과 동일한 전체 결과).
*Mutation*: 화이트리스트 검사 없이 값을 그대로 SQL 조건에 매핑하려는 구현은(예: 매칭되는 분기가 없어 "일치하는 것 없음"을 의미하는 기본 필터로 떨어짐) 0건을 반환해 REQ-OLIST-024a가 명시적으로 금지하는 "silently return zero results" 상태가 되어 이 AC가 실패한다.

**AC-OLIST-023** (Ubiquitous) [HARD] — 필터의 쿼리 수 불변식. Traces: REQ-OLIST-025. **While** 5 orders match a `logistics_display` filter, the system **shall** issue the same total query count for the filtered request as for an equivalent unfiltered request returning the same 5 orders.
*Mutation*: 필터를 "먼저 전체 조회 후 Python에서 각 주문의 라인아이템을 별도 쿼리로 다시 조회해 판정"하는 방식으로 구현하면 주문 수만큼 쿼리가 추가된다.

**AC-OLIST-024** (Ubiquitous) [M10 강화 — 구체적 기대값] — 백엔드 파라미터 회귀 없음. Traces: REQ-OLIST-034. **While** exactly one order has `financial_status="paid"` among a set that also includes `financial_status="refunded"` and `financial_status="pending"` orders, `GET /api/orders/?financial_status=paid` **shall** return exactly that one order. **While** exactly one order has `fulfillment_status=null` among a set that also includes `fulfillment_status="fulfilled"` orders, `GET /api/orders/?fulfillment_status=unfulfilled` **shall** return exactly that one order.

**AC-OLIST-025** (Ubiquitous) [M5 분리 — 자동화 가능 부분만 pytest 단정] — `OrderDetailSerializer` 응답 키 집합 회귀 없음. Traces: REQ-OLIST-033. **While** an order matches SPEC-ORDER-021 AC-COST-001's fixture, `GET /api/orders/{pk}/` **shall** return a response whose key set is identical to the set `test_spec_021.py`'s T1(`test_t1_single_sku_korea_warehouse_fee`) already asserts on(`margin_amount`, `korea_warehouse_cost`, `shipping_cost`, `total_weight_grams` 등), **and** `test_spec_021.py`의 T1~T10, T12~T22(21개, T11은 결번)이 무수정 재통과해야 한다. (수동 게이트: 계산 로직 자체가 리팩터링 전후 동일한지는 `git diff`로 별도 확인 — `plan.md`의 완료 조건으로 이동, pytest 단정 대상이 아니다.)

**AC-OLIST-026** (Ubiquitous) [M4 — 스코프 조회 명시; v1.2.0 M3-new 확장 — 6개 옵션 전량 존재 단정 추가] — 물류상태 필터 드롭다운: 옵션 전량 존재 + 선택 상호작용. Traces: REQ-OLIST-026, REQ-OLIST-027. **While** `OrdersPage` is rendered, the `aria-label="물류상태 필터"` dropdown(다른 곳의 동일 텍스트와 혼동하지 않도록 이 속성으로 스코프) **shall** contain exactly 7 `<option>` elements — "전체" plus the 6 values in REQ-OLIST-024, each paired with its Korean label(미입고/입고예정/출고예정/부분출고/출고/부분입고). **When** the user selects the "부분출고" option, the system **shall** include `logistics_display=partial_shipped` as a query parameter on the subsequent `GET /api/orders/` request.
*Mutation(M3-new)*: 옵션을 2개(전체 + 부분출고)만 구현해도 "부분출고 선택 시 쿼리 파라미터 반영" 단정 하나만으로는 통과했다 — 7개 옵션 전량 존재 단정이 이 mutation을 잡는다.

**AC-OLIST-027** (Event-Driven) [M4 — 셀 스코프 조회 명시; v1.2.0 M3-new 확장 — 6개 라벨 파라미터화] — 프론트엔드 라벨 렌더링(6개 값 전량 파리티). Traces: REQ-OLIST-030, REQ-OLIST-031, REQ-OLIST-032. **While** an order has `logistics_display: null, purchase_display: null, margin_rate: null`, the system **shall** render `"-"` in all three cells(행으로 스코프된 조회, 예: `within(row)`). **While** an order's `logistics_display` is, in turn, each of the 6 values in REQ-OLIST-024 — `not_shipped`→"미입고", `shipment_confirmed`→"입고예정", `outbound_scheduled`→"출고예정", `partial_shipped`→"부분출고", `shipped`→"출고", `partial`→"부분입고" — the system **shall** render the corresponding Korean label in that row's 물류상태 cell(각 케이스 행 스코프 조회, 파라미터화 테스트로 6개 값 전량을 순회한다). **While** an order has `purchase_display: "unordered", margin_rate: "67.75"`, the system **shall** render "미발주"/"67.75%" in the respective cells, scoped to that row.
*Mutation(M3-new)*: `logisticsStatusLabels.ts`를 로컬에서 스프레드로 확장하며 `partial_shipped`/`partial` 2개 키를 빠뜨리면(raw snake_case 값이 그대로 노출), 이전 버전은 `partial_shipped` 1개만 확인해 `partial` 키 누락을 발견하지 못했다 — 6개 전량 파라미터화가 이를 잡는다. `Order` 타입에 3개 필드를 추가하지 않고 컴포넌트가 접근하면 `tsc -b` 컴파일 오류로 실패한다(회귀 게이트). null 폴백을 빠뜨리면 1차 단정이 "null" 또는 빈 문자열 렌더링으로 실패한다.

### Traceability 검증표

| REQ | 커버하는 AC |
|---|---|
| REQ-OLIST-001~003 | AC-OLIST-005 |
| REQ-OLIST-004 | AC-OLIST-001 |
| REQ-OLIST-005 | AC-OLIST-002, AC-OLIST-003 |
| REQ-OLIST-006 | AC-OLIST-001, AC-OLIST-002, AC-OLIST-004 |
| REQ-OLIST-007 | AC-OLIST-011 |
| REQ-OLIST-008 | AC-OLIST-006 |
| REQ-OLIST-009 | AC-OLIST-007, AC-OLIST-008, AC-OLIST-009 |
| REQ-OLIST-010 | AC-OLIST-009, AC-OLIST-010 |
| REQ-OLIST-011 | AC-OLIST-008, AC-OLIST-013 |
| REQ-OLIST-011a | AC-OLIST-013a |
| REQ-OLIST-012 | AC-OLIST-012 |
| REQ-OLIST-013 | AC-OLIST-011, AC-OLIST-014, AC-OLIST-014a, AC-OLIST-014b |
| REQ-OLIST-014 | AC-OLIST-014, AC-OLIST-014a, AC-OLIST-015 |
| REQ-OLIST-014a | AC-OLIST-014a, AC-OLIST-014b |
| REQ-OLIST-015 | AC-OLIST-016 |
| REQ-OLIST-016 | AC-OLIST-017, AC-OLIST-017a |
| REQ-OLIST-017 | AC-OLIST-018, AC-OLIST-018a, AC-OLIST-018b |
| REQ-OLIST-018 | AC-OLIST-017 |
| REQ-OLIST-019 | AC-OLIST-019 |
| REQ-OLIST-020 | AC-OLIST-019, AC-OLIST-020, AC-OLIST-020a |
| REQ-OLIST-021 | AC-OLIST-021 |
| REQ-OLIST-022 | AC-OLIST-021 |
| REQ-OLIST-022a | AC-OLIST-021 |
| REQ-OLIST-023 | AC-OLIST-022, AC-OLIST-022a~e |
| REQ-OLIST-024 | AC-OLIST-022, AC-OLIST-022a~e, AC-OLIST-026 |
| REQ-OLIST-024a | AC-OLIST-022f |
| REQ-OLIST-025 | AC-OLIST-022, AC-OLIST-022a~e, AC-OLIST-023 |
| REQ-OLIST-026 | AC-OLIST-026 |
| REQ-OLIST-027 | AC-OLIST-026 |
| REQ-OLIST-028 | AC-OLIST-005 |
| REQ-OLIST-029 | AC-OLIST-005 |
| REQ-OLIST-030 | AC-OLIST-027 |
| REQ-OLIST-031 | AC-OLIST-027 |
| REQ-OLIST-032 | AC-OLIST-027 |
| REQ-OLIST-033 | AC-OLIST-025 |
| REQ-OLIST-034 | AC-OLIST-024 |

37개 요구사항 전량이 38개 인수 기준(v1.2.0: 36개 + 신규 AC-OLIST-020a/022f 2개)으로 직접 커버된다 — 런타임 AC 없이 문서 게이트에만 위임된 요구사항은 더 이상 없다(v1.1.0의 REQ-OLIST-024a는 AC-OLIST-022f 신설로 해소됨, 감사 M2-new).

---

## 설계 결정

**A. `ExchangeRate` 배치 로드는 페이지 단위, 하한 없는 이력 범위를, 슬림 프로젝션으로 적재한다(v1.1.0 정정, 감사 M6).** 페이지의 각 주문마다 정확히 일치하는 날짜의 레코드만 적재하면 폴백(REQ-OLIST-020)이 깨진다(AC-OLIST-020). 감사는 대안으로 "lookback 윈도(하한)"를 제안했으나 **채택하지 않는다** — `shopify_created_at`이 임의로 오래된 주문(예: 마이그레이션된 과거 데이터)을 포함할 수 있고, 윈도 밖에 유일한 적용 가능 레코드가 있으면 `_get_exchange_rate`가 찾아냈을 값을 배치 로더가 놓쳐 REQ-OLIST-020("동일한 값")을 위반하게 된다 — 정확성이 메모리 절약보다 우선한다. 대신 감사가 함께 제시한 두 번째 대안을 채택한다: `ExchangeRate.objects.filter(effective_date__lte=max_date).order_by("effective_date").values_list("effective_date", "rate")`로 **전체 이력을, 모델 인스턴스가 아니라 2개 컬럼만** 적재한다 — `ExchangeRate`는 하루 1행(`effective_date` unique, `models.py:501`)이고 SPEC-ORDER-022가 자동 갱신·백필을 보장하므로, 수년치 이력이라도 수천 행 × 2개의 좁은 컬럼(`DateField`, `DecimalField`)에 불과해 메모리 부담이 사실상 없다.

**B. `logistics_display`/`purchase_display`는 Python에서, 필터는 SQL에서 — 양쪽 모두 오직 `LineItem`에서만 파생하며, `Order.status`는 어느 쪽도 읽지 않는다(v1.1.0, C3/H5 재설계).** 표시값은 이미 prefetch된 `obj.line_items.all()`을 순회해 계산하고(REQ-OLIST-021), 필터는 별도의 `Exists` 기반 annotation으로 구현한다(REQ-OLIST-025, N+1 방지를 위해 Python 루프로 필터링할 수 없다). 두 경로가 반드시 같은 결과를 내야 하므로, AC-OLIST-022~022e(6개 값 전량)가 이 일치를 직접 판별한다. `Order.status`를 완전히 배제함으로써 이전 설계가 가졌던 문제(저장된 집계값이 최신이 아닐 수 있음, C3)가 원천적으로 사라진다 — 필터와 표시 양쪽이 항상 같은 라이브 데이터를 본다.

**C. 마진 공식은 단일 출처를 공유해야 한다.** `OrderListSerializer.get_margin_rate`가 `OrderDetailSerializer`의 계산 로직과 별개로 재구현되면 두 값이 갈릴 위험이 생긴다 — 공용 헬퍼로 추출하는 정확한 방법(모듈 함수, mixin, 정적 메서드 등)은 `plan.md`가 정하되, `OrderDetailSerializer`의 관측 가능한 출력은 리팩터링 전후 바이트 단위로 동일해야 한다(REQ-OLIST-033, AC-OLIST-025).

**D. "trackable"의 정의는 새로 만들지 않고 기존 정의를 재사용하되, 저장된 집계값 자체는 재사용하지 않는다.** `_recompute_order_aggregates`(`backend/order/purchase_order_views.py:160-161`)가 이미 `sku__isnull=False`를 "집계 대상" 라인아이템의 정의로, uniform-then-partial을 집계 규칙으로 쓰고 있다 — 이 SPEC은 그 **정의와 규칙**을 물류상태 파생에 재사용하지만, `Order.status` **컬럼**은 결코 읽지 않는다(설계 결정 B).

## 사전 검증 — 기존 게터의 N+1 위험 (조치 불필요, 확인만 기록)

`OrderListSerializer.get_line_items_count`(`backend/order/serializers.py:53-54`, `obj.line_items.count()`)와 `get_has_refund`(`:49-51`, `obj.refunds.exists()`)가 `views.py:162`의 `prefetch_related("line_items", "refunds", ...)` 캐시를 실제로 재사용하는지 이 세션에서 직접 검증했다 — **`backend/poetry.lock:168`이 고정한 Django 5.2.17**(`pyproject.toml:10`의 `^5.0` 제약을 만족하는 버전, 실제 poetry 가상환경 `C:\Users\ggajo\AppData\Local\pypoetry\Cache\virtualenvs\scm-v2-backend-*\Lib\site-packages\django\`에서 직접 소스를 읽어 확인 — 시스템 전역 인터프리터가 아니다):

- `QuerySet.count()`(`django/db/models/query.py:595-606`)와 `QuerySet.exists()`(`:1293-1299`)는 둘 다 `self._result_cache is not None`이면 새 쿼리 없이 캐시된 결과 길이/존재 여부를 반환한다.
- 역방향 FK 매니저의 `get_queryset()`(`django/db/models/fields/related_descriptors.py:755-770`, `Order.line_items`/`Order.refunds` 둘 다 이 종류)는 `self.instance._prefetched_objects_cache`에 해당 필드가 있으면 **그 캐시된(이미 평가된) 쿼리셋을 그대로 반환**한다.

두 사실을 합치면 `obj.line_items.count()`/`obj.refunds.exists()`는 prefetch 캐시를 정확히 재사용하며 추가 쿼리를 발급하지 않는다 — 이 SPEC 이전부터 N+1 문제가 없었다. 별도 수정은 필요 없다(범위 규율).

**베이스라인 실측(REQ-OLIST-022a의 근거).** 고객이 연결된 주문 2건으로 구성된 페이지에 대해 이 세션에서 `GET /api/orders/`를 직접 측정한 결과(임시 테스트 파일, 검증 직후 삭제) 총 쿼리 6개: JWT 인증 사용자 조회(`accounts_adminuser`) 1 + 페이지네이션 `COUNT(*)`(`orders_order`) 1 + 본문 `SELECT`(`orders_order`) 1 + `prefetch_related` 3개(`orders_refund`, `orders_line_item`, `orders_customer`) — 이 순서·구성 그대로 재현했다. 고객이 전혀 연결되지 않은 페이지(모든 주문 `customer=None`)에서는 `orders_customer` 쿼리 자체가 발급되지 않아 5개로 줄어드는 것도 별도로 확인했다(Django의 `prefetch_related`가 빈 ID 목록에 대해 쿼리를 완전히 생략하기 때문) — 프로덕션 데이터는 Shopify 주문이 거의 항상 고객 정보를 동반하므로 6을 표준 베이스라인으로 채택한다.

## 제약사항

- 마진율은 표시 전용이다 — DB 컬럼으로 역정규화하지 않으며, 정렬/범위 필터를 지원하지 않는다.
- 물류상태·발주상태 파생은 매 요청 시 이미 prefetch된 라인아이템에서 계산하는 런타임 값이며, Order 레벨 집계 컬럼을 신설하지 않고 `Order.status`/`ready_to_ship`도 읽지 않는다.
- `ExchangeRate` 조회는 리스트 요청당 최대 1회로 제한된다(REQ-OLIST-019).
- `financial_status`/`fulfillment_status` 백엔드 쿼리 파라미터(`backend/order/views.py:171`, `:186`)는 무수정 — 프론트엔드 드롭다운만 제거한다.
- `OrderDetailSerializer`(`backend/order/serializers.py:152-443`)와 `OrderDetailPage`는 이 SPEC의 범위 밖이며 관측 가능한 동작이 변경되지 않아야 한다.

## Exclusions (What NOT to Build)

- **`margin_rate`를 `Order` DB 컬럼으로 역정규화하지 않는다.** 표시 전용이며, 정렬·범위 필터 기능은 만들지 않는다 — 계산 로직은 후속 SPEC이 컬럼화할 수 있도록 재사용 가능한 형태로 유지한다(설계 결정 C).
- **발주상태 필터 드롭다운은 만들지 않는다.** 물류상태 필터만 추가한다(사용자 확정 결정 8).
- **부분출고의 사유(반품, 파손, 분할배송 등) 분류 기능은 만들지 않는다.** 사용자가 명시적으로 보류했다 — "부분출고" 단일 라벨만 표시한다.
- **`OrderDetailPage`/`OrderDetailSerializer`의 어떤 동작도 변경하지 않는다.** 공유 코드를 추출하더라도 detail의 출력은 바이트 단위로 동일해야 한다(REQ-OLIST-033).
- **`financial_status`/`fulfillment_status` 백엔드 쿼리 파라미터 필터를 제거하거나 변경하지 않는다.** API 호환성을 위해 유지한다 — 제거되는 것은 프론트엔드 드롭다운뿐이다(REQ-OLIST-034).
- **`LOGISTICS_STATUS_CHOICES`/`PURCHASE_STATUS_CHOICES`(`backend/order/models.py:8-14`, `:156-167`)에 신규 enum 값을 추가하지 않는다.** `partial_shipped`/`partial`은 `logistics_display`라는 파생 필드 전용 값이며, `LineItem.logistics_status`나 `Order.status` 컬럼 자체의 선택지에는 추가되지 않는다.
- **`ExchangeRate` 조회의 요청 간(cross-request) 캐시는 만들지 않는다.** REQ-OLIST-019가 요구하는 것은 단일 리스트 요청 내 배치 로드(최대 1회 쿼리)뿐이다.
- **`Order.status`/`Order.ready_to_ship` 컬럼을 이 SPEC의 물류상태·발주상태 계산에 읽거나 쓰지 않는다(v1.1.0).** 이 두 컬럼과 `_recompute_order_aggregates`는 완전히 무수정으로 남는다 — 이 SPEC의 파생값은 매 요청 독립 계산이다.

## 후속 과제

1. **마진율 컬럼화 및 정렬/범위 필터.** 이 SPEC은 표시 전용으로 남겨둔다 — 설계 결정 C의 공유 헬퍼를 그대로 재사용해 별도 SPEC에서 DB 컬럼 + 배치 갱신 잡을 추가할 수 있다.
2. **발주상태 필터.** 사용자가 이번 범위에서 명시적으로 제외했다 — 수요가 확인되면 물류상태 필터와 동일한 `Exists` 기반 패턴을 재사용할 수 있다.
3. **부분출고 사유 분류.** 사용자가 명시적으로 보류했다 — `LineItem` 레벨에 사유 필드를 추가하는 별도 SPEC이 필요하다.
4. **`order_cancelled` trackable 항목의 발주상태 분류 재검토(명시적 가정 4).** 현재는 `status` 집계 관례(포함)를 따르지만, `ready_to_ship` 관례(제외)가 더 적절하다고 판단되면 별도 SPEC에서 전환한다 — 사용자 확인 필요.
5. **SPEC-ORDER-021 문서 상호 참조.** SPEC-ORDER-021의 Exclusion(`spec.md:373`)이 이 SPEC에 의해 supersede되었다는 사실을 SPEC-ORDER-021 문서에도 기록한다(감사 M8).
