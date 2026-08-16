---
id: SPEC-ORDER-023
document: plan
version: 1.4.0
status: completed
updated: 2026-08-16
---

# 구현 계획 — SPEC-ORDER-023 주문목록 표시 컬럼 개편

`spec.md`의 요구사항(REQ-OLIST-001~034 및 하위 011a/022a/024a)을 구현하기 위한 작업 분해, 파일별 변경 계획, TDD 사이클, 리스크와 완화책, MX 태그 계획을 정리한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며, 요구사항을 재진술하지 않고 REQ ID로 참조한다.

**개발 방법론**: TDD (RED-GREEN-REFACTOR). `.moai/config/sections/quality.yaml`의 `development_mode: "tdd"`에 따른다. 브라운필드 변경이므로 각 RED 단계 전에 대상 코드를 먼저 읽는다.

**v1.1.0 변경 요약(plan-audit iteration 1 반영)**: 물류상태 파생을 `Order.status` 패스스루에서 `LineItem` 직접 파생(우선순위 규칙 4/4a)으로 재설계(C3). `ExchangeRate` 배치 로드의 상한을 "lookback 윈도"가 아니라 "슬림 프로젝션(`values_list`)"으로 정정(M6, 정확성 우선). AC-OLIST-021의 절대상수를 이 세션에서 실측한 베이스라인(6) + 배치 쿼리(1) = **7**로 SPEC 자체에 못박음(C1). 물류상태 필터를 6개 값 전량 커버하도록 확장(H2). 마진 null 게이트 3원인 전량 커버(H3). 발주상태 trackable 필터 판별 추가(H4). 취소 배지 판별을 `getDisplayStatus`의 앞 3개 분기로 한정(H6).

**v1.2.0 변경 요약(plan-audit iteration 2 반영, FAIL→0.76)**: 이 문서(plan.md)의 의사코드(`if not trackable: return None, None`)와 SQL 설계(`has_trackable &`)는 **처음부터 trackable 0개를 올바르게 가드하고 있었다** — 감사가 지적한 C1-new는 spec.md의 REQ-OLIST-010/011에 그 가드가 빠져 있어 spec.md 단독으로는 REQ-OLIST-012와 모순되는 상태였다는 것이었다(plan.md:13의 "단일 출처는 spec.md" 원칙 위반). spec.md의 REQ 문언을 plan.md의 기존 로직과 일치하도록 수정했으므로, **이 문서의 기술적 접근(M2 의사코드, M4 SQL)은 내용 변경이 필요 없다** — 다만 REQ-OLIST-020(H3-new 대응, `.date()` 시간대 규정)과 REQ-OLIST-022a(H3-new 대응, 조건부 스킵과의 정합)에 맞춰 M3의 서술을 보강했다. AC-OLIST-022f(REQ-OLIST-024a 허용 외 값 fail-open) 신규 테스트 대응 항목을 M1/M4/Done 체크리스트에 추가.

**v1.2.1 변경 요약(plan-audit iteration 3 반영, PASS 0.87 — 착수 가능)**: spec.md/acceptance.md가 표준 데이터셋에 Order H를 추가(감사 N1)하고 AC-OLIST-022~022e에 `count` 단정을 추가(N2)한 것에 맞춰, 이 문서의 3곳(M1 데이터셋 언급, R4, Done 체크리스트)에 있던 "Order A~G" 표기만 "Order A~H"로 갱신했다 — plan.md의 기술적 접근(M2/M4 설계) 자체는 v1.2.0에서 이미 올바른 방향을 지시하고 있었으므로 내용 변경이 필요 없다(감사도 이를 확인했다: "plan.md가 이미 올바른 구현을 명시적으로 지시하고 있으므로 SPEC 재작성은 불필요하고 AC 보강으로 충분하다").

**v1.3.0 변경 요약(구현 완료)**: M0~M9 전 마일스톤 완료. 독립 평가(evaluator-active, PASS — Functionality 93 / Security 96 / Craft 88 / Consistency 88) 확인 후 `status`를 draft→completed로 전환한다. 이 문서가 지시한 기술적 접근(M2/M3/M4)은 구현 단계에서 변경 없이 그대로 채택되었다 — 계획 대비 발산 1건(`get_margin_rate`의 명시적 `shopify_created_at` 조기 반환, 동작 동일)은 `spec.md` HISTORY(v1.3.0)에 기록했다. Done 체크리스트 전 항목 충족 확인(`test_spec_023.py` 31개, 백엔드 스위트 1204개, `test_spec_021.py` T1~T10/T12~T22 21개 무수정 재통과, 프론트엔드 304개, `tsc -b` 클린). REQ-OLIST-022a의 "+0" 분기(전부-NULL 페이지)는 계획대로 런타임 AC 없이 코드 검사로만 검증된 채 남았다(R11, 저확률 프로덕션 상태).

**pytest 실행 규칙(이 프로젝트 고유 제약, 반드시 준수)**:
- 테스트 DB가 공유 원격 인스턴스이므로 **테스트 실행은 동시에 두 세션에서 진행하지 않는다.**
- 서브셋 실행 시 `--no-cov`를 반드시 붙인다 — 붙이지 않으면 전부 통과해도 프로세스 종료 코드가 비정상(1)이 되어 CI/자동화가 실패로 오인한다.
- 신규 테스트 파일: `backend/order/tests/test_spec_023.py`.
- **측정 목적의 임시 스크립트/테스트 파일은 실행 직후 반드시 삭제한다** — `test_zzz_*` 접두사 관례(이 SPEC의 M0 베이스라인 실측에 사용한 방식)를 따르고, 영구 스위트에 남기지 않는다.

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M0 (High) — 베이스라인 확인**: `backend/order/serializers.py:25-54,152-443`, `backend/order/views.py:38-52,151-218`, `backend/order/models.py:1-244,495-511`, `backend/order/purchase_order_views.py:113-209,3400-3420,3448-3460,3960-3980`, `frontend/src/pages/OrdersPage.tsx` 전체, `frontend/src/types/order.ts`, `frontend/src/features/order/hooks/useOrders.ts`, `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx:1-75`를 다시 읽는다. **`GET /api/orders/`의 현재(이 SPEC 이전) 쿼리 수를 재실측하고 AC-OLIST-021이 유도한 값 6과 일치하는지 확인한다** — 불일치 시 spec.md REQ-OLIST-022a와 AC-OLIST-021을 실측값으로 갱신하고 그 사실을 HISTORY에 기록한다(추측값으로 되돌리지 않는다).

- **M1 (High) — 백엔드 계약 테스트 선작성 (RED)**:
  - `backend/order/tests/test_spec_023.py` 신규 작성. AC-OLIST-006~025(백엔드 대상, 하위 013a/017a/018a/018b/020a/022a~f 포함)에 1:1 대응하는 테스트를 담는다.
  - **표준 물류상태 데이터셋(Order A~H, spec.md 참조)을 이 파일의 공용 fixture/헬퍼로 1회 정의하고, AC-OLIST-022~022f 전량이 이를 재사용한다** — 각 AC가 개별적으로 부분집합을 고르면 판별력이 테스트 작성자의 선택에 좌우된다는 것이 v1.1.0 감사(H1-new)의 핵심 지적이었다(v1.2.1: Order H 추가, 감사 N1 — `outbound_scheduled` uniform 검사의 any/all mutation 판별용).
  - AC-OLIST-017/017a/018/018a/018b(마진율 값·필드 범위·null 게이트 3원인), AC-OLIST-006~013a(물류상태 파생, 우선순위 역전·trackable 제외·혼재 상태 포함), AC-OLIST-014~016(발주상태 파생)은 신규 필드가 없는 현재 코드에서 반드시 실패해야 한다(`KeyError` 또는 값 불일치) — 단, AC-OLIST-012/016/018/018a/018b는 **키 존재 단정을 반드시 포함**해야 RED가 성립한다(`"logistics_display" in item`류, H1 — `.get(...)`만 쓰면 미구현 코드에서도 통과해버린다).
  - AC-OLIST-019(배치 로드 정확성+쿼리 수), AC-OLIST-021(전체 쿼리 수 = 정확히 8, v1.4.0에서 7→8), AC-OLIST-023(필터 쿼리 수 불변식)은 `test_spec_021.py:281-283`/`test_spec_018.py:483-551`(워밍업 `:502-504`)의 `CaptureQueriesContext` + 워밍업 관례를 따른다. **AC-OLIST-021의 절대값 `8`(v1.4.0 이전 `7`)은 spec.md REQ-OLIST-022a가 이미 유도했으므로 추측하거나 구현 후 되채우지 않는다** — M0에서 재실측해 일치를 확인하는 것이 유일한 목적이다.
  - AC-OLIST-020(폴백 보존)은 D-3에만 레코드가 있는 픽스처를 쓴다. AC-OLIST-020a(신규, 시간대 경계)는 `django.test.utils.override_settings(TIME_ZONE="Asia/Seoul")`로 배포 설정(`"UTC"`)과 다른 시간대를 강제해 `.date()` 시간대 일치 요건을 판별한다.
  - AC-OLIST-022~022e(6개 필터 값 전량, 표준 데이터셋 공유), AC-OLIST-022f(신규, `?logistics_display=bogus_value` fail-open), AC-OLIST-024(구체적 기대값), AC-OLIST-025(`OrderDetailSerializer` 응답 키 집합 회귀 — `test_spec_021.py`의 T1~T10, T12~T22 무수정 재통과 확인 포함)도 포함한다.
  - AC-OLIST-001~005(취소 배지, 열 구성), AC-OLIST-026(6개 옵션 전량 존재 단정 포함), AC-OLIST-027(6개 라벨 파라미터화)은 `frontend/src/pages/OrdersPage.test.tsx`에서 다룬다(M6).

- **M2 (High) — 물류상태/발주상태 파생 구현 (GREEN) — `Order.status`를 읽지 않는다**:
  - `OrderListSerializer`에 `get_logistics_display`/`get_purchase_display` 추가. 공용 헬퍼(예: `_derive_line_item_states(obj)`)가 `obj.line_items.all()`을 **1회** 순회하며 trackable(`sku is not None`) 필터를 적용해 두 파생값을 함께 계산 — REQ-OLIST-021(추가 쿼리 없음)을 만족하려면 반드시 이미 prefetch된 `obj.line_items.all()`을 재사용해야 하며, `LineItem.objects.filter(order=obj)`류의 신규 쿼리를 발급하면 안 되고, **`obj.status`를 참조해서도 안 된다**(REQ-OLIST-007, C3 재설계).
  - 우선순위 구현 순서 준수: (1) 전부 `shipped` 체크 → (2) 하나라도 `shipped_quantity > 0` 체크 → (3) 전부 `received` 체크 → (4) 남은 trackable의 `logistics_status`가 uniform하면 그 값 → (4a) uniform하지 않으면(2개 이상의 distinct 값) `"partial"`. **순서를 바꾸면 AC-OLIST-006(규칙 1↔2)/AC-OLIST-009(규칙 2↔3)가 실패한다.** uniform 판정은 `{li.logistics_status for li in trackable}`의 길이가 1인지로 구현(집합 크기 비교) — `_recompute_order_aggregates`(`purchase_order_views.py:176-177`)의 `len(statuses) == 1` 패턴과 동일한 방식.
  - 발주상태 [REWRITTEN v1.4.0]: trackable 라인아이템에 대해 `any(_awaiting_purchase(li) for li in trackable)`이며, `_awaiting_purchase`는 미발주 목록 탭의 `_reorder_candidate_filter`(`purchase_order_views.py:107-110`)와 동일하게 (a) `purchase_status == "unordered"`이면서 연결된 `PurchaseOrder`가 없거나 (b) `purchase_status == "damaged_exchange"`인 경우 참이다. `all()`로 잘못 구현하면 AC-OLIST-014가, `purchase_status`만 검사하면 AC-OLIST-014/014a가, `damaged_exchange`에도 링크 예외를 적용하면 AC-OLIST-014b가 실패한다. `order_cancelled` 항목은 배제하지 않는다(명시적 가정 4 — 새 기준에서도 `unordered`가 아니므로 미발주를 유발하지 않는다). 링크 조회는 반드시 `li.purchase_orders.all()`(prefetch 캐시)로 해야 하며 `.exists()`는 캐시를 우회해 라인아이템당 1쿼리를 발급하므로 AC-OLIST-021이 실패한다.

- **M3 (High) — 마진율 노출 + 배치 환율 로드 구현 (GREEN)**:
  - `OrderDetailSerializer._compute_cost_breakdown_uncached`(`serializers.py:298-360`)가 이미 구현한 마진 계산 로직(confirmed_cost_usd/shipping_cost_usd/korea_warehouse_usd → margin_usd → margin_rate 양자화)을 **재사용 가능한 형태로 추출**한다 — 정확한 방법(모듈 함수로 분리해 두 시리얼라이저가 호출, 또는 mixin)은 구현자 재량이나, 추출 후 `OrderDetailSerializer`가 호출하는 코드 경로가 리팩터링 전후 동일한 값을 반환하는지 `test_spec_021.py`의 T1~T10, T12~T22(21개, T11 결번) 무수정 재통과로 확인한다(REQ-OLIST-033, AC-OLIST-025의 전제 조건). **금지: 목록 전용 코드가 이미 양자화된 `confirmed_cost`/`shipping_cost`/`korea_warehouse_cost` 문자열을 재파싱해 `margin_rate`를 재계산 — AC-OLIST-017a가 이 mutation을 판별한다.**
  - 추출된 계산 함수는 `ExchangeRate` 인스턴스(또는 `rate` 값)를 **매개변수로 받아야 한다** — 내부에서 `_get_exchange_rate(obj)`를 직접 호출하지 않는다. 이래야 리스트 시리얼라이저가 배치 로드한 환율을 주입할 수 있다.
  - `OrderListView`(`views.py:155-218`)에 배치 환율 로드를 추가한다 — `list()`를 오버라이드해 페이지네이션 이후의 `page` 객체 목록에서 주문일 최댓값을 구하고, **`ExchangeRate.objects.filter(effective_date__lte=max_date).order_by("effective_date").values_list("effective_date", "rate")`**(모델 인스턴스가 아니라 2개 컬럼만 — 설계 결정 A, M6 정정: lookback 윈도 대신 슬림 프로젝션을 채택했다) 단일 쿼리로 이력을 적재한 뒤, 시리얼라이저 컨텍스트(`context={"exchange_rate_history": [...], ...}`)로 전달한다. 각 주문의 적용 환율은 Python에서 "적재된 이력 중 해당 주문일 이하 최신 레코드"(이진 탐색 또는 정렬된 리스트 역순회)로 해석해 `_get_exchange_rate`와 동일한 폴백 의미를 재현한다(REQ-OLIST-020) — **하한을 두지 않는다**: `shopify_created_at`이 임의로 오래된 주문을 포함할 수 있으므로, 상한(`max_date`)만 두고 하한은 열어 둔 전체 이력을 적재해야 REQ-OLIST-020의 "동일한 값" 요건을 만족한다.
  - **REQ-OLIST-019/022a 검증의 핵심**: 이 배치 쿼리가 페이지당 정확히 1회만 실행되어야 하고, `list()` 오버라이드 시점에 한 번만 계산해 컨텍스트에 담아야 한다. 페이지에 유효한 주문(`shopify_created_at` not null)이 하나도 없으면 이 쿼리 자체를 건너뛴다.
  - `get_margin_rate`(리스트용)는 이 컨텍스트에서 주문에 맞는 환율을 조회한 뒤 M3에서 추출한 공용 계산 함수를 호출한다. 환율을 찾지 못하면(이력에 해당 날짜 이하 레코드가 전혀 없음, 또는 `shopify_created_at`이 없음) `None`을 반환한다(REQ-OLIST-017 원인 1) — **`IndexError`를 던지지 않는다**(AC-OLIST-018a가 이 경계를 직접 판별한다, H3).
  - `OrderListSerializer.Meta.fields`에 `margin_rate`만 추가한다(REQ-OLIST-018 — 나머지 6개 비용 필드는 추가하지 않는다).

- **M4 (High) — 물류상태 필터 구현 (GREEN) — `LineItem`에서만 파생, `Order.status`를 필터 조건에 쓰지 않는다**:
  - `OrderListView.get_queryset`(`views.py:161-218`)에 `logistics_display` 쿼리 파라미터 처리를 추가한다. 값이 REQ-OLIST-024의 6개 중 하나가 아니면 REQ-OLIST-024a에 따라 필터를 적용하지 않는다(무시, 400 아님).
  - `Exists`/`~Exists` 서브쿼리로 다음 annotation들을 정의한다(모두 `sku__isnull=False`로 스코프된 `trackable_qs = LineItem.objects.filter(order=OuterRef("pk"), sku__isnull=False)`를 기반):
    - `has_trackable = Exists(trackable_qs)`
    - `not_all_shipped = Exists(trackable_qs.exclude(logistics_status="shipped"))` → `all_shipped = has_trackable & ~not_all_shipped`
    - `any_partial = Exists(trackable_qs.filter(shipped_quantity__gt=0))`
    - `not_all_received = Exists(trackable_qs.exclude(logistics_status="received"))` → `all_received = has_trackable & ~not_all_received`
    - 규칙 4/4a 판별용, 남은 3개 raw 값 각각에 대해: `not_all_X = Exists(trackable_qs.exclude(logistics_status=X))` (X ∈ {`not_shipped`, `shipment_confirmed`, `outbound_scheduled`}) → `all_X = has_trackable & ~not_all_X`. **이 3개 annotation은 규칙 4(uniform passthrough) 전용이며, 규칙 4a("partial")는 `all_shipped`/`any_partial`/`all_received`/`all_not_shipped`/`all_shipment_confirmed`/`all_outbound_scheduled` 여섯 개가 전부 거짓이면서 `has_trackable`이 참인 경우로 정의한다(별도 Exists 불필요, 나머지 6개의 부정 조합으로 유도).**
  - `logistics_display` 파라미터 값에 따라 REQ-OLIST-008~011a와 동일한 우선순위로 위 annotation들을 조합한 `Q` 필터를 적용한다:
    - `shipped` → `Q(all_shipped=True)`
    - `partial_shipped` → `Q(all_shipped=False) & Q(any_partial=True)`
    - `outbound_scheduled` → `Q(all_shipped=False) & Q(any_partial=False) & (Q(all_received=True) | Q(all_outbound_scheduled=True))`(이접 조건, AC-OLIST-022d)
    - `not_shipped` → `Q(all_shipped=False) & Q(any_partial=False) & Q(all_received=False) & Q(all_not_shipped=True)`
    - `shipment_confirmed` → 위와 동일한 앞 3개 부정 + `Q(all_shipment_confirmed=True)`
    - `partial` → 앞 3개 부정 + `Q(all_not_shipped=False) & Q(all_shipment_confirmed=False) & Q(all_outbound_scheduled=False) & Q(has_trackable=True)`
  - 표시 로직(M2)과 필터 로직(M4)이 반드시 동일한 우선순위를 구현해야 한다 — 어긋나면 AC-OLIST-022~022e가 실패한다(각 AC가 "필터 결과 ∧ 반환된 주문의 표시값" 이중 단정을 쓰므로, 필터만 옳고 표시값이 틀린 경우와 그 반대 모두 v1.2.0부터 판별 가능하다, H2-new).
  - 필터가 없으면(또는 REQ-OLIST-024의 6개 값에 속하지 않으면) 이 annotation들 자체를 건너뛰고 전체 결과를 반환한다(REQ-OLIST-024a, AC-OLIST-022f가 판별) — 불필요한 쿼리 플랜 복잡도를 늘리지 않으면서 fail-open 동작을 보장한다.

- **M5 (High) — 프론트엔드 타입/훅 갱신 (RED→GREEN)**:
  - `frontend/src/types/order.ts`의 `Order`(`:8-23`)에 `margin_rate`/`logistics_display`/`purchase_display` 3개 필드 추가. `OrderListParams`(`:64-73`)에 `logistics_display?: string` 추가.
  - `frontend/src/features/order/hooks/useOrders.ts`(`:13-21`)에 `logistics_display` 파라미터 매핑 추가.
  - `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`의 `buildOrder()`(`:28-45`)에 `margin_rate: null, logistics_display: null, purchase_display: null` 기본값 추가 — **`types/order.ts` 변경과 같은 단계에서 처리**해 `tsc -b`가 깨지는 중간 상태를 만들지 않는다(SPEC-ORDER-021 v1.4.0 감사 D2와 동일한 이유).

- **M6 (High) — 프론트엔드 렌더링 구현 (RED→GREEN)**:
  - `frontend/src/pages/OrdersPage.tsx`:
    - `getFulfillmentLabel`(`:96-104`) 삭제.
    - `getDisplayStatus`(`:81-94`)의 **앞 3개 분기만** 배지 판별에 재사용한다 — 정확히는, 배지 전용 헬퍼(예: `getCancelBadge(order): '취소' | '부분취소' | null`)를 새로 만들어 `refunded`/`partially_refunded`/`has_refund` 3개 분기만 복제하고, 뒤따르는 결제상태 라벨 맵(`:86-93`)은 배지 헬퍼에 포함하지 않는다(REQ-OLIST-006, H6). `getDisplayStatus` 자체는 남은 호출부가 없다면(그렙으로 확인) 죽은 코드가 되므로 **삭제한다** — 결제상태 열 자체가 사라지므로 다른 소비자가 없을 가능성이 높다. 배지 요소에 `data-testid="cancel-badge"`를 부여한다.
    - 결제상태 필터(`:203-214`)와 출고상태 필터(`:229-239`) 제거, 물류상태 필터 드롭다운 추가(옵션: 전체 + REQ-OLIST-024의 6개 값, 값이 REQ-OLIST-024a 처리와 일관되도록 서버가 이해하는 문자열 그대로 전송).
    - 테이블 헤더(`:278-289`)를 9열로 재구성: 주문번호/스토어/위치/고객/물류상태/발주상태/마진율/금액/주문일.
    - `colSpan={8}`(`:293`) → `colSpan={9}`.
    - 본문 셀(`:300-348`)에서 결제상태/출고상태 셀을 물류상태/발주상태/마진율 셀로 교체하고, 주문번호 셀(`:306-308`)에 취소 배지를 추가.
    - 물류상태 한글 라벨은 `frontend/src/pages/OutboundPage/logisticsStatusLabels.ts`의 `LOGISTICS_STATUS_LABELS`를 **import해 재사용**하고, `partial_shipped`/`partial` 2개 키는 `OrdersPage.tsx` 로컬에서 스프레드로 확장한다(공유 파일 자체는 수정하지 않는다 — 그 파일은 SPEC-ORDER-016 소유이며 `Record<string, string>`이라 로컬 확장이 타입 충돌 없이 가능함을 plan-audit가 확인했다).
    - 테스트에서 필터 옵션(`<option>`)과 테이블 셀의 동일 텍스트("부분출고" 등)가 혼동되지 않도록, 필터는 `<select aria-label="물류상태 필터">` 스코프로, 셀은 행(`<tr>`) 스코프로 조회 가능하게 마크업한다(M4 대응 — 특별한 DOM 구조 변경 없이 기존 `<select>`/`<tr>` 구조로 이미 스코프 가능하다).
  - `frontend/src/pages/OrdersPage.test.tsx`에 AC-OLIST-001~005, 026, 027 대응 신규 `describe` 블록 추가.

- **M7 (Medium) — REFACTOR**: M2~M4에서 추출한 헬퍼들의 가독성을 다듬는다. 물류상태 표시 로직(M2)과 필터 로직(M4)이 동일한 우선순위 문서(REQ-OLIST-008~011a)를 주석으로 공유하는지 확인한다.

- **M8 (Medium) — 회귀 확인**: 백엔드 전체 테스트 스위트, `test_spec_021.py`의 T1~T10, T12~T22(21개) 무수정 재통과(마진 공식 무수정 확인), 프론트엔드 전체 테스트 스위트(`SearchTab.test.tsx` 포함), `npm run build`(`tsc -b`) 통과. `git diff`로 `OrderDetailSerializer` 블록(`serializers.py:152-443`)이 값/필드 변경 없이(순수 추출 리팩터링만) 남아 있는지 확인 — 이것이 AC-OLIST-025의 수동 게이트 부분이다.

- **M9 (Low) — MX 태그 적용 + 문서 동기화**: 아래 MX 태그 계획을 적용하고, `spec.md`/`plan.md`/`acceptance.md`의 `status`를 갱신하며 구현 중 발견한 발산을 `spec.md` HISTORY에 기록한다. SPEC-ORDER-021 문서에 이 SPEC이 그 Exclusion을 supersede했다는 상호 참조를 남긴다(후속 과제 5, 감사 M8).

의존 관계: M0 → M1 → {M2, M3, M4 (병렬 가능, 서로 다른 헬퍼)} → M5 → M6 → M7 → M8 → M9.

---

## 파일별 변경 계획

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| MODIFY | `backend/order/serializers.py`(`OrderListSerializer`, `:25-54`) | `margin_rate`/`logistics_display`/`purchase_display` 3개 `SerializerMethodField` + `Meta.fields` 추가. `logistics_display`/`purchase_display`는 `obj.line_items.all()`만 순회 — `obj.status` 참조 금지. |
| MODIFY | `backend/order/serializers.py`(마진 계산 헬퍼 추출) | `_compute_cost_breakdown_uncached`의 계산 로직 중 재사용 가능한 부분을 환율을 매개변수로 받는 공용 함수/메서드로 추출. `OrderDetailSerializer`의 관측 가능한 출력은 무변경. |
| EXISTING (무수정) | `backend/order/serializers.py`(`OrderDetailSerializer`, `:152-443`) | REQ-OLIST-033. 순수 추출 리팩터링만 허용, 값/필드 변경 없음. |
| MODIFY | `backend/order/views.py`(`OrderListView`, `:155-218`) | `logistics_display` 필터(`Exists` annotation, `LineItem` 전용) 추가. `list()` 오버라이드로 페이지 단위 `ExchangeRate` 배치 로드(슬림 프로젝션) 후 시리얼라이저 컨텍스트 주입. |
| EXISTING (무수정) | `backend/order/views.py`의 `financial_status`/`fulfillment_status` 파라미터 처리(`:171-173`, `:186-191`) | REQ-OLIST-034. |
| EXISTING (무수정) | `backend/order/models.py`의 `Order.status`/`Order.ready_to_ship`, `backend/order/purchase_order_views.py`의 `_recompute_order_aggregates` | v1.1.0 재설계로 이 SPEC의 어떤 코드 경로도 이들을 읽거나 쓰지 않는다. |
| NEW | `backend/order/tests/test_spec_023.py` | AC-OLIST-006~025(백엔드 대상, 하위 항목 포함) 대응 테스트. 쿼리 캡처는 `test_spec_021.py:281-283`, `test_spec_018.py:40,483-551`(워밍업 `:502-504`) 관례를 따른다. |
| MODIFY | `frontend/src/types/order.ts` | `Order`(`:8-23`)에 3개 필드 추가, `OrderListParams`(`:64-73`)에 `logistics_display?` 추가. |
| MODIFY | `frontend/src/features/order/hooks/useOrders.ts`(`:9-28`) | `logistics_display` 파라미터 매핑 추가. |
| MODIFY | `frontend/src/pages/OrdersPage.tsx` | 열/필터 재구성(본문 참조), `getFulfillmentLabel`/`getDisplayStatus` 삭제, `getCancelBadge` 신설(앞 3분기만). |
| MODIFY | `frontend/src/pages/OrdersPage.test.tsx` | 배지·신규 열·필터 테스트 추가. |
| MODIFY | `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`(`:28-45`) | `buildOrder()`에 3개 신규 필드 기본값(`null`) 추가. |
| EXISTING (무수정) | `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx` | 이 SPEC과 무관 — 별도 컴포넌트. |
| EXISTING (무수정) | `frontend/src/pages/OutboundPage/logisticsStatusLabels.ts` | import해 재사용만 한다 — 파일 자체는 수정하지 않는다(SPEC-ORDER-016 소유 파일에 대한 범위 규율). |

---

## 기술적 접근

### 물류상태/발주상태 파생 (M2) — `Order.status`를 읽지 않는다

```
def _derive_line_item_states(obj):
    trackable = [li for li in obj.line_items.all() if li.sku is not None]
    if not trackable:
        return None, None  # logistics_display, purchase_display

    if all(li.logistics_status == "shipped" for li in trackable):
        logistics = "shipped"
    elif any(li.shipped_quantity > 0 for li in trackable):
        logistics = "partial_shipped"
    elif all(li.logistics_status == "received" for li in trackable):
        logistics = "outbound_scheduled"
    else:
        statuses = {li.logistics_status for li in trackable}
        logistics = next(iter(statuses)) if len(statuses) == 1 else "partial"

    # v1.4.0: 미발주 목록 탭(_reorder_candidate_filter)과 동일 기준.
    # li.purchase_orders.all()은 prefetch_related("line_items__purchase_orders")
    # 캐시를 읽는다 — .exists()는 캐시를 우회해 라인아이템마다 쿼리를 발급하므로 금지.
    def _awaiting_purchase(li):
        if li.purchase_status == "damaged_exchange":
            return True
        return li.purchase_status == "unordered" and not li.purchase_orders.all()

    purchase = "unordered" if any(_awaiting_purchase(li) for li in trackable) else "ordered"
    return logistics, purchase
```

위는 의도를 보이기 위한 의사코드다 — 정확한 함수 시그니처·캐싱 방식은 구현자 재량이나, **순서(전부 shipped → 부분출고 → 전부 received → uniform passthrough → partial)는 REQ-OLIST-008~011a의 순서와 정확히 일치해야 하고, `obj.status`를 어디에서도 참조하면 안 된다.** uniform 판정(`len(statuses) == 1`)은 `_recompute_order_aggregates`(`purchase_order_views.py:176-177`)와 동일한 집합-크기 비교 패턴을 재사용한다(정의는 재사용, 저장값은 재사용하지 않음 — 설계 결정 D).

### 배치 환율 로드 (M3) — 슬림 프로젝션, 하한 없음

1. `OrderListView.list()`를 오버라이드해 `page = self.paginate_queryset(queryset)` 직후, `page`(현재 페이지의 `Order` 인스턴스 목록)에서 `shopify_created_at`이 not null인 것들의 최댓값 `max_date`를 구한다. **`.date()`는 각 `order.shopify_created_at` 속성에 직접 호출한다** — `django.utils.timezone.localtime()`이나 다른 시간대 변환 호출을 거치지 않는다. `_get_exchange_rate`(`serializers.py:248`, `order_date = obj.shopify_created_at.date()`)가 쓰는 것과 정확히 동일한 방식이어야, 배포 `TIME_ZONE` 설정(현재 `"UTC"`, `config/settings/base.py:92`)과 무관하게 REQ-OLIST-020이 요구하는 "동일한 값"이 보장된다(v1.2.0, H3-new/M5-new — AC-OLIST-020a가 `override_settings(TIME_ZONE="Asia/Seoul")`로 이 요건을 직접 판별한다).
2. `ExchangeRate.objects.filter(effective_date__lte=max_date).order_by("effective_date").values_list("effective_date", "rate")`로 단일 쿼리 적재(모델 인스턴스가 아니라 2개 컬럼만, 설계 결정 A) — 페이지에 유효한 주문이 없으면(모두 `shopify_created_at is None`) 이 쿼리 자체를 건너뛴다(REQ-OLIST-022a가 이 스킵을 "post-SPEC 총계 = 베이스라인 + 0"으로 명시적으로 허용한다, v1.2.0 H3-new). **하한을 두지 않는다** — `effective_date__gte=...`류의 조건을 추가하면 REQ-OLIST-020("동일한 값")을 위반할 위험이 있다(설계 결정 A, M6).
3. 정렬된 `(date, rate)` 튜플 리스트를 시리얼라이저 컨텍스트에 담아 전달한다. 각 주문의 적용 환율은 "이 리스트에서 `effective_date <= order_date`인 마지막 원소"(리스트가 이미 오름차순 정렬되어 있으므로 이진 탐색 또는 뒤에서부터 순회)로 찾는다 — `_get_exchange_rate`의 "가장 최근의 `effective_date <= order_date`" 의미와 정확히 같아야 한다(REQ-OLIST-020). 이 단계의 `order_date` 산출도 1번과 동일하게 `order.shopify_created_at.date()`를 직접 호출한다(타임존 변환 없음). 리스트가 비어 있거나 일치하는 원소가 없으면 `None`을 반환한다(`IndexError` 금지, AC-OLIST-018a).
4. 페이지네이션이 없는 호출 경로(`page is None`)에서도 동일한 배치 로드를 적용한다.

**하지 말 것**: 각 주문마다 별도로 `ExchangeRate.objects.filter(...).first()`를 호출 — REQ-OLIST-019 위반, AC-OLIST-019가 판별. `_get_exchange_rate`를 무수정으로 재사용 — 인스턴스 단위 메모이제이션이 서로 다른 주문(`obj.pk`)마다 새로 캐시를 채워 페이지당 최대 50회 쿼리가 된다. 배치 쿼리에 `effective_date__gte`류의 하한을 추가 — REQ-OLIST-020 위반 위험(M6). `max_date`나 `order_date` 계산에 `timezone.localtime()`/`timezone.now()`를 섞어 쓰기 — REQ-OLIST-020의 시간대 일치 요건 위반, AC-OLIST-020a가 판별(v1.2.0).

### 물류상태 필터 (M4) — `LineItem` 전용, `Order.status` 미사용

`Exists`/`~Exists` 서브쿼리로 annotate 후 `Q` 조합 — 기술적 접근 절 M4 항목 참조. 필터 파라미터가 없거나 REQ-OLIST-024의 6개 값에 속하지 않으면(REQ-OLIST-024a) 이 annotation들 자체를 건너뛰어(조건부 적용) 불필요한 쿼리 플랜 복잡도를 늘리지 않는다.

### 쿼리 수 계산 근거 (REQ-OLIST-022a, AC-OLIST-021)

이 SPEC 착수 시점(v1.1.0 작성 중)에 이 세션에서 직접 실측한 베이스라인(고객 연결 주문 포함 페이지):

| # | 쿼리 | 발급 주체 |
|---|---|---|
| 1 | `SELECT ... FROM accounts_adminuser WHERE id=...` | `JWTAuthentication.get_user`(JWT 인증, 요청당 1회) |
| 2 | `SELECT COUNT(*) FROM orders_order` | `PageNumberPagination` → `django.core.paginator.Paginator.count`(`@cached_property`, 요청당 1회) |
| 3 | `SELECT ... FROM orders_order ...` | 본문 쿼리셋 평가(`OrderListView.get_queryset`) |
| 4 | `SELECT ... FROM orders_refund WHERE order_id IN (...)` | `prefetch_related("refunds")` |
| 5 | `SELECT ... FROM orders_line_item WHERE order_id IN (...)` | `prefetch_related("line_items")` |
| 6 | `SELECT ... FROM orders_customer WHERE id IN (...)` | `prefetch_related("customer")` |
| **7** | `SELECT effective_date, rate FROM orders_exchangerate WHERE effective_date <= ... ORDER BY effective_date` | **이 SPEC이 추가하는 배치 쿼리(REQ-OLIST-019)** |
| **8** | `SELECT ... FROM orders_purchaseorder INNER JOIN orders_purchaseorder_line_items WHERE lineitem_id IN (...)` | **v1.4.0이 추가하는 `prefetch_related("line_items__purchase_orders")`(REQ-OLIST-013의 링크 조건, REQ-OLIST-021)** |

1~6은 페이지 크기(주문 수)와 무관하게 항상 정확히 1개씩만 발급된다(`prefetch_related`는 `id IN (...)` 단일 쿼리, `COUNT(*)`/본문 SELECT도 페이지당 1개) — 이것이 REQ-OLIST-022의 O(1) 근거다. 7도 페이지의 날짜 범위와 무관하게 항상 1개다(REQ-OLIST-019). 8도 중첩 prefetch이지만 페이지 전체의 라인아이템 ID를 한 번에 `IN (...)`으로 묶으므로 라인아이템 수와 무관하게 1개다. 합계 **8**이 AC-OLIST-021의 절대상수다(v1.4.0에서 7→8).

**주의(엣지 케이스, 테스트 설계 시 회피)**: 페이지의 모든 주문이 `customer=None`이면 Django가 6번 쿼리 자체를 생략해 합계가 6이 된다(빈 ID 목록에 대한 프리페치는 쿼리를 발급하지 않음, 이 세션에서 직접 확인). AC-OLIST-021의 픽스처는 고객이 연결된 주문만 사용해 이 엣지 케이스를 피한다.

---

## 리스크 분석 및 완화책

| ID | 리스크 | 완화책 |
|---|---|---|
| R1 | `_get_exchange_rate`를 리스트 시리얼라이저에 그대로 재사용해 페이지당 최대 50개의 `ExchangeRate` 쿼리가 발생한다(문제 정의의 핵심 리스크) | M3에서 페이지 단위 배치 로드를 명시적으로 설계. AC-OLIST-019, AC-OLIST-021(절대값 7)이 판별. |
| R2 | 물류상태 우선순위(전부 shipped → 부분출고 → 전부 received → uniform → partial)가 잘못된 순서로 구현되면, 프로덕션에서 항상 동시 성립하는 규칙 1/2(문제 정의, `purchase_order_views.py:3411/3456/3972`)에서 완전출고 주문이 전부 "부분출고"로 잘못 표시된다 — **가장 흔하고 눈에 띄는 잠재 결함** | AC-OLIST-006(현실적 `shipped_quantity=quantity` 픽스처)이 규칙 1↔2 역전을, AC-OLIST-009가 규칙 2↔3 역전을 직접 판별. |
| R3 | 물류상태/발주상태 계산이 non-trackable(`sku=None`) 라인아이템을 실수로 포함한다 | AC-OLIST-011이 non-trackable 항목에 극단값(`shipped_quantity=99`, `purchase_status` 기본값 `unordered`)을 심어 물류·발주 양쪽에서 판별. |
| R4 | 필터(SQL)와 표시(Python)가 서로 다른 우선순위 로직을 구현해 필터 결과와 화면 라벨이 불일치한다 | 설계 결정 B, AC-OLIST-022~022e가 표준 데이터셋(Order A~H) 위에서 "필터 결과 ∧ 표시값" 이중 단정으로 이 일치를 직접 검증(v1.2.0, H2-new; Order H는 v1.2.1, N1). |
| R5 | 공용 마진 계산 함수 추출 과정에서 `OrderDetailSerializer`의 반환값이 미세하게 달라진다(반올림 순서, None 게이트 등) | `test_spec_021.py`의 T1~T10, T12~T22(21개) 무수정 재통과를 M8 회귀 확인의 필수 조건으로 명시. AC-OLIST-025가 응답 키 집합 동일성을 판별, `git diff`가 계산 로직 무변경을 수동 확인. |
| R6 | `Order` 타입에 3개 필수 필드가 추가되면서 `SearchTab.test.tsx:28-45`의 `buildOrder()`가 타입 에러로 `tsc -b`를 깨뜨린다 | M5에서 `types/order.ts` 변경과 같은 단계로 `buildOrder()` 기본값 추가. |
| R7 | 물류상태 필터의 `Exists` 서브쿼리가 페이지네이션 이전(전체 쿼리셋)에 적용되지 않고 실수로 페이지 이후에 Python 필터링되면 페이지 크기가 요청한 것과 달라진다 | REQ-OLIST-025를 "쿼리 레벨" 필터로 명시. AC-OLIST-023이 쿼리 수로 간접 판별(N+1이 없다는 것은 SQL 레벨 필터링의 증거). |
| R8 | 목록 전용 `get_margin_rate`가 이미 양자화된 하위 필드 문자열을 재파싱해 마진을 재계산하면 SPEC-ORDER-021 AC-COST-015가 이미 경고한 1센트 오차가 재발한다 | AC-OLIST-017a(`grams=500, confirmed_price=10005.00` 픽스처)가 직접 판별. |
| R9 | `ExchangeRate` 배치 쿼리에 실수로 하한(`effective_date__gte`)을 추가하면 오래된 주문의 폴백이 깨진다 | AC-OLIST-020(D-3 폴백)과 AC-OLIST-018a(레코드 전무 → `null`)가 함께 판별 — 하한이 있으면 D-3보다 더 오래된 유일 레코드를 가진 주문에서 전자가, 이력 자체가 없는 주문에서 후자가 각각 실패한다. |
| R10 | (v1.2.0, C1-new) REQ-OLIST-010/011에 "at least one trackable line item" 가드 없이 구현하면(spec.md v1.1.0의 원래 문언을 그대로 따르면), trackable 0개 주문에서 `all([])==True`가 되어 규칙 3(REQ-010)이 공허하게 발화해 `logistics_display`가 `null` 대신 `"outbound_scheduled"`가 된다 | REQ-OLIST-010/011/011a 전부에 가드를 명시(spec.md). AC-OLIST-012가 trackable 0개 픽스처에서 `null`을 직접 단정해 판별. |
| R11 | (v1.2.0, H3-new) 배치 쿼리 스킵 최적화(모든 주문의 `shopify_created_at`이 NULL인 페이지)를 구현하지 않거나, 반대로 항상 배치 쿼리를 발급하도록 "단순화"하면 REQ-OLIST-022a("베이스라인 + 0 또는 정확히 1")의 두 분기 중 하나가 검증 불가능해진다 | REQ-OLIST-022a가 두 분기를 모두 명시. AC-OLIST-021은 canonical 분기(날짜 있음, +1=7)만 실측 단정하며, 전부-NULL 분기는 REQ 문언과 M3의 조건부 스킵 설계로 문서화되어 있으나 별도 런타임 AC는 없다(저확률 프로덕션 상태 — Shopify 주문은 항상 생성 시각을 동반). |
| R12 | (v1.2.0, M5-new/H3-new) 배치 로더가 `.date()` 대신 `timezone.localtime().date()`를 쓰면, 이 프로젝트의 실제 배포 `TIME_ZONE="UTC"`에서는 관측 가능한 차이가 없어(현지화해도 UTC이므로) 결함이 눈에 띄지 않다가, 향후 `TIME_ZONE` 설정이 바뀌면(예: `Asia/Seoul`) 자정 경계 주문에서 잘못된 환율이 적용된다 | AC-OLIST-020a가 `override_settings(TIME_ZONE="Asia/Seoul")`로 배포 설정과 무관하게 이 요건을 강제 판별. |

---

## MX 태그 계획 (mx_plan)

| 태그 | 위치 | 내용 |
|---|---|---|
| `@MX:NOTE` (신규) | `_derive_line_item_states`(또는 동등 헬퍼) 정의부 | 우선순위 5단계(전부 shipped → 부분출고 → 전부 received → uniform passthrough → partial)와 그 근거(SPEC-ORDER-015가 확인한 "부분출고가 logistics_status를 이동시키지 않는다"는 동작, `purchase_order_views.py:3411/3456/3972`), **그리고 `Order.status`를 의도적으로 읽지 않는 이유(C3 — 저장형 집계값이 물류 미작업 주문에서 NULL이기 때문)**를 명시. |
| `@MX:NOTE` (신규) | 배치 환율 로드 지점(`OrderListView.list()` 또는 동등 위치) | 페이지당 최대 1회 쿼리로 제한되는 이유(원격 DB 쿼리당 ~130ms, 50개 주문이면 최대 6.5초)와, `_get_exchange_rate`를 그대로 재사용하면 안 되는 이유, 하한을 두지 않는 이유(정확성)를 명시. |
| `@MX:WARN` (신규, `@MX:REASON` 필수) | 물류상태 필터의 `Exists` annotation 조합부 | 표시 로직(M2)과 우선순위가 반드시 일치해야 하며, 한쪽만 수정하면 AC-OLIST-022~022e가 깨진다는 경고. |

`code_comments: en` 설정(`.moai/config/sections/language.yaml`)에 따라 모든 태그 본문은 영어로 작성한다.

---

## 완료 조건 (Definition of Ready → Done 게이트)

**Ready (구현 시작 전)**

- [ ] M0 확인 — 대상 파일 전체를 재확인했다
- [ ] 현재(이 SPEC 이전) `GET /api/orders/` 쿼리 수를 재실측해 6과 일치함을 확인했다(불일치 시 spec.md 갱신)

**Done (구현)**

- [ ] `test_spec_023.py`의 AC-OLIST-006~025(백엔드, 하위 항목 포함) 전량 통과
- [ ] AC-OLIST-006~018b가 신규 필드 부재 상태(되돌린 코드)에서 실패함을 확인했다
- [ ] AC-OLIST-006이 "규칙 2를 규칙 1보다 먼저 평가" mutation에서 실패함을 확인했다(가장 흔한 프로덕션 오류 — C2)
- [ ] AC-OLIST-009가 "규칙 3을 규칙 2보다 먼저 평가" mutation에서 실패함을 확인했다
- [ ] AC-OLIST-011이 "trackable 필터 누락"(물류·발주 양쪽) mutation에서 실패함을 확인했다
- [ ] AC-OLIST-012가 "trackable 0개 주문에서 규칙 10(모든 trackable이 received)이 공허하게 발화" mutation(REQ-OLIST-010에 "at least one trackable line item" 가드를 빠뜨린 구현)에서 실패함을 확인했다 — `logistics_display`가 `"outbound_scheduled"`로 잘못 나오면 안 되고 반드시 `null`이어야 한다(v1.2.0, C1-new)
- [ ] AC-OLIST-013a가 "uniform 판정 생략" mutation에서 실패함을 확인했다
- [ ] AC-OLIST-014가 "any 대신 all" mutation에서 실패함을 확인했다
- [ ] AC-OLIST-017a가 "양자화된 하위 필드 재합산" mutation에서 실패함을 확인했다(R8)
- [ ] AC-OLIST-012/016/018/018a/018b가 `"key" in item` 키 존재 단정을 실제로 포함하며, 되돌린 코드에서 실패함을 확인했다(H1)
- [ ] AC-OLIST-019의 (b) 쿼리 수 단정이 "`_get_exchange_rate` 무수정 재사용" mutation에서 실패함을 확인했다
- [ ] AC-OLIST-018a가 "이력 전무 시 `IndexError`" mutation에서 실패(예외로 500이 되어 200 단정이 실패)함을 확인했다
- [ ] AC-OLIST-020a가 "`.date()` 대신 `timezone.localtime().date()` 사용" mutation에서 `override_settings(TIME_ZONE="Asia/Seoul")` 하에 실패함을 확인했다(v1.2.0, H3-new/M5-new)
- [ ] AC-OLIST-021의 절대값(7)이 M0 재실측과 REQ-OLIST-022a의 유도값 모두와 일치함을 확인했다(추측값 아님)
- [ ] AC-OLIST-022~022e(표준 데이터셋 Order A~H 공유) 통과 — 특히 022b/022c/022e가 Order G(또는 D/H)를 포함한 상태에서 `any` 대신 `all` mutation을 잡아냄을, 022d가 (a)/(b) 두 원인 모두에서 필터 결과와 표시값을 동시에 단정함을, 022~022e의 `count` 단정이 Python 사후 필터링 mutation에서 실패함을 확인했다(v1.2.0 H1-new/H2-new, v1.2.1 N1/N2)
- [ ] AC-OLIST-022f가 `?logistics_display=bogus_value`에서 200 + 전체 결과(0건이 아님)를 단정하며, 화이트리스트 누락 mutation에서 실패함을 확인했다(v1.2.0, M2-new)
- [ ] AC-OLIST-026이 7개 옵션 전량 존재를, AC-OLIST-027이 6개 라벨 전량 렌더링을 파라미터화로 확인한다(v1.2.0, M3-new — 이전 버전은 1~2개만 확인해 프론트/백엔드 파리티가 깨져 있었다)
- [ ] `test_spec_021.py`의 T1~T10, T12~T22(21개) 무수정 재통과 — 마진 공식 추출 리팩터링이 `OrderDetailSerializer` 출력을 바꾸지 않았다
- [ ] `git diff`로 `financial_status`/`fulfillment_status` 백엔드 파라미터 처리 블록(`views.py:171-173`, `:186-191`) 무변경 확인
- [ ] `git diff`로 `Order.status`/`Order.ready_to_ship`/`_recompute_order_aggregates` 무변경 확인
- [ ] 프론트엔드: `OrdersPage.test.tsx`의 AC-OLIST-001~005, 026, 027 대응 테스트 전량 통과
- [ ] AC-OLIST-004가 "`getDisplayStatus` 통째 재사용" mutation(정상 주문에 결제상태 라벨이 `data-testid="cancel-badge"`로 렌더)에서 실패함을 확인했다(H6)
- [ ] `SearchTab.test.tsx`가 `buildOrder()` 기본값 추가 후에도 통과한다
- [ ] `npm run build`(`tsc -b`) 통과, 기존 프론트엔드 테스트 스위트 무수정 통과
- [ ] ESLint/TypeScript 신규 에러 0, 백엔드 `ruff`/`black` 신규 이슈 0

**Done (문서)**

- [ ] `spec.md`/`plan.md`/`acceptance.md`의 `status`가 갱신되었다
- [ ] 구현 중 발견한 계획 대비 발산이 `spec.md` HISTORY에 기록되었다
- [ ] SPEC-ORDER-021 문서에 이 SPEC의 supersede 사실을 상호 참조로 남겼다(감사 M8)

**REQ → 검증 수단 매핑**

| REQ | 검증 |
|---|---|
| 001~006 | AC-OLIST-001~005 |
| 007~011a | AC-OLIST-006~013a |
| 013~015 | AC-OLIST-011, 014~016 |
| 016~018 | AC-OLIST-017, 017a, 018, 018a, 018b |
| 019~022a | AC-OLIST-019, 020, 020a, 021 |
| 023~025 | AC-OLIST-022~022e, 023 |
| 024a | AC-OLIST-022f |
| 026~032 | AC-OLIST-005, 026, 027 |
| 033 | AC-OLIST-025, `test_spec_021.py` 무수정 재통과, `git diff` |
| 034 | AC-OLIST-024 |

---

## 관련 참조 구현

- **마진 계산 원본**: `backend/order/serializers.py:222-443`(`_get_exchange_rate`, `_compute_cost_breakdown`, `_compute_cost_breakdown_uncached`, `get_margin_amount`, `get_margin_rate`)
- **뷰 레벨 prefetch 근거**: `backend/order/views.py:161-164`(`OrderListView.get_queryset`), `:151-152`(`OrderPagination.page_size = 50`)
- **`shipped_quantity >= quantity` 전이 조건 3곳(C2 근거)**: `purchase_order_views.py:3411`, `:3456`, `:3972`
- **`Order.status`가 NULL일 수 있는 근거(C3)**: `shopify_orders.py:130-147`(`status`가 `defaults`에서 의도적 제외), `models.py:49-54`(기본값 없음), `_recompute_order_aggregates` 호출자가 `purchase_order_views.py` 내부뿐임(grep 확인)
- **Order.status 집계 로직(정의·규칙 재사용 대상, 컬럼 자체는 미사용)**: `backend/order/purchase_order_views.py:123-209`(`_recompute_order_aggregates`), 특히 `:160-161`(trackable 정의 `sku__isnull=False`), `:172-178`(uniform-then-partial 집계 로직)
- **부분출고가 logistics_status를 이동시키지 않는다는 증거**: `backend/order/tests/test_spec_015.py:332-345`(`test_partial_shipment_stamps_time_but_leaves_status_unchanged`)
- **쿼리 카운트 관례 선례**: `backend/order/tests/test_spec_021.py:281-283`, `backend/order/tests/test_spec_018.py:40,64,483-551`(워밍업 `:502-504`)
- **LineItem 필드 원본**: `backend/order/models.py:169-238`(`sku` `:175`, `quantity` `:176`, `logistics_status` `:204-208`, `shipped_quantity` `:221`, `purchase_status` `:190-194`)
- **ExchangeRate 모델**: `backend/order/models.py:495-511`
- **Django 5.2.17(`poetry.lock:168`) 소스 근거(prefetch 캐시 재사용)**: `django/db/models/query.py:595-606`(`count`), `:1293-1299`(`exists`), `django/db/models/fields/related_descriptors.py:755-770`(역방향 FK 매니저 `get_queryset`) — poetry 가상환경(`C:\Users\ggajo\AppData\Local\pypoetry\Cache\virtualenvs\scm-v2-backend-*\`)에서 직접 확인.
- **프론트엔드 취소 배지 판별식 원본**: `frontend/src/pages/OrdersPage.tsx:81-94`(`getDisplayStatus`, 앞 3분기만 재사용 — `:86-93`은 재사용하지 않음)
- **프론트엔드 재사용 대상 라벨 맵**: `frontend/src/pages/OutboundPage/logisticsStatusLabels.ts`
- **프론트엔드 파라미터 매핑 원본**: `frontend/src/features/order/hooks/useOrders.ts:13-21`
- **두 번째 `Order` 구성 지점(회귀 대상)**: `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx:28-45`(`buildOrder()`)
