# SPEC Review Report: SPEC-ORDER-023
Iteration: 1/3
Verdict: FAIL (= 재작업 필요 — 차단 결함 3건 + 고위험 결함 6건)
Overall Score: 0.61

Reasoning context ignored per M1 Context Isolation. 이 감사는 `.moai/specs/SPEC-ORDER-023/`의 세 문서(v1.0.0)와
저장소 소스만 사용했다. spec.md:19의 "모든 `file:line` 인용은 이 세션에서 직접 재검증했다"는 주장은 근거로
채택하지 않고 **모든 인용을 직접 다시 열어** 확인했다. 모든 손계산 값은 픽스처 원문에서 독립적으로 재유도했다.
mutation 분석은 문서의 서술을 신뢰하지 않고 실제 소스(`_compute_cost_breakdown_uncached`,
`_recompute_order_aggregates`, `_process_outbound_rows`)에 대해 직접 구성했다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: `grep -cE '^\*\*REQ-OLIST-[0-9]{3}\*\*' spec.md` = 34,
  `sort | uniq -d` 결과 없음, 최대값 REQ-OLIST-034 → 001~034 연속·중복 없음·3자리 패딩 일관.
  AC도 동일: 정의 27개, 중복 없음, 최대 AC-OLIST-027 → 001~027 연속. 3개 문서 전체 스캔 결과
  고유 식별자 61개(34+27)로, 정의되지 않은 REQ/AC 참조나 고아 AC가 없다.

- **[FAIL] MP-2 EARS format compliance**: 34개 REQ는 **전부 유효한 EARS 문장**이다 — 직접 확인:
  REQ-OLIST-008~015는 진짜 State-Driven(`While …, the system shall …`, spec.md:109, 111, 113, 115, 117,
  121, 123, 125), REQ-OLIST-006/017은 진짜 Unwanted(`If …, then the system shall …`, spec.md:103, 131),
  REQ-OLIST-004/005/023/027/030~032는 진짜 Event-Driven. **그러나 27개 인수 기준은 EARS 문장이 아니다.**
  전부 한국어 시나리오 서술문에 EARS 패턴 라벨만 붙어 있다. 예: spec.md:194
  "**AC-OLIST-006** (State-Driven) — … 단일 trackable 라인아이템(`logistics_status='shipped'`)만 있는
  주문의 `logistics_display == "shipped"`." — `While … the system shall …` 구조가 전혀 없다. 27개 전부
  같은 형태다. M5 MP-2는 "Given/When/Then test scenarios mislabeled as EARS = FAIL"을 명시하므로
  방화벽에 걸린다. 실무 영향은 형식적이지만(문장 자체는 구체적·검증 가능), **선행 SPEC-ORDER-021은
  AC를 EARS 문장으로 작성했으므로(`.moai/specs/SPEC-ORDER-021/spec.md:224` "**When** a client requests
  `GET /api/orders/`(목록), the system **shall not** include …") 이는 명백한 퇴행이다.**

- **[PASS] MP-3 YAML frontmatter validity**: spec.md:1-11 — `id: SPEC-ORDER-023`(string),
  `version: 1.0.0`(string), `status: draft`(string), `created_at: 2026-08-16`(ISO date),
  `priority: High`(string), `labels: [order, list, margin, logistics, purchase-status, frontend, backend]`(array).
  6개 필수 필드 전부 존재·타입 정확. 동반 문서 frontmatter도 동기화(plan.md:1-7, acceptance.md:1-7,
  모두 v1.0.0 / draft / updated 2026-08-16).

- **[N/A] MP-4 Section 22 language neutrality**: Django 백엔드 1개 + React 페이지 1개로 범위가 한정된
  단일 프로젝트 SPEC. 다국어 툴링 주장이 없다. 자동 통과.

---

## Focus Area 1 — 인용 무결성 (모든 `file:line`을 직접 재확인)

**결론: 날조된 인용 0건.** 약 55건의 개별 인용을 모두 열어 확인했고, 전부 주장한 구조를 가리킨다.
드리프트는 아래 표의 3건(전부 Low)뿐이다. 이 저장소의 과거 사고 2건(존재하지 않는 경로 날조)과 같은
유형의 결함은 **재발하지 않았다.**

### 백엔드 — 전부 정확

| 인용 | 주장 | 검증 결과 |
|---|---|---|
| `serializers.py:25-54` (spec.md:29,68) | `OrderListSerializer` | class 25, `get_line_items_count` 53-54, 다음 class 62 — 정확 |
| `serializers.py:152-443` (spec.md:29,71,314) | `OrderDetailSerializer` | class 152, `get_exchange_rate_date` 434, 다음 class 446 — 정확 |
| `serializers.py:222-254` (spec.md:29) | `_get_exchange_rate` | `def` 222, `return result` 253, 254는 공백 — +1 초과(무해) |
| `serializers.py:298-360` (spec.md:62, plan.md:39) | `_compute_cost_breakdown_uncached` | `def` 298, 반환 dict `}` 360 — **정확히 일치** |
| `serializers.py:49-51`, `:53-54` (spec.md:301) | `get_has_refund` / `get_line_items_count` | 정확 |
| `serializers.py:222-443` (plan.md:214) | 마진 계산 원본 블록 | 정확 |
| `views.py:161-218` (spec.md:69, plan.md:47) | `OrderListView.get_queryset` | `def` 161, `return qs` 218 — 정확 |
| `views.py:162` (spec.md:141, plan.md:41) | `prefetch_related("refunds", "line_items", "customer")` | 정확 |
| `views.py:171-173`, `:186-191` (spec.md:69,173,313) | `financial_status` / `fulfillment_status` 처리 | 정확 |
| `views.py:151-152` (plan.md:215) | `OrderPagination.page_size = 50` | class 151, `page_size = 50` 152 — 정확 |
| `views.py:38-52` (plan.md:24) | `OrderDetailView` | class 38, `get_queryset` 45, `)` 52 — 정확 |
| `views.py:155-218` (plan.md:88) | `OrderListView` | class 155 — 정확 |
| `models.py:49-54` (spec.md:31) | `Order.status` 필드 | `status = models.CharField(` 49, `)` 54 — **정확히 일치** |
| `models.py:8-14` (spec.md:323) | `LOGISTICS_STATUS_CHOICES` | 8~14 — **정확히 일치** |
| `models.py:156-167` (spec.md:323) | `PURCHASE_STATUS_CHOICES` | 156~167 — **정확히 일치** |
| `models.py:169-238`, `:175`, `:176`, `:190-194`, `:204-208`, `:221` (plan.md:219) | LineItem 필드 6건 | `order` FK 169, `sku` 175, `quantity` 176, `purchase_status` 190-194, `logistics_status` 204-208, `shipped_quantity` 221, `damaged_quantity` 238 — **6건 전부 정확** |
| `models.py:495-511` (plan.md:220), `:501` (spec.md:291), `:507` (acceptance.md:209) | `ExchangeRate`, `effective_date` unique, `db_table` | class 495, `effective_date = models.DateField(unique=True)` 501, `db_table = "orders_exchangerate"` 507 — 정확 |
| `purchase_order_views.py:123-209` (spec.md:31, plan.md:216) | `_recompute_order_aggregates` | `def` 123, 다음 `def` 212 — 정확 |
| `purchase_order_views.py:160-161` (spec.md:61,297, plan.md:216) | trackable 정의 `sku__isnull=False` | 160-161 — **정확히 일치** |
| `purchase_order_views.py:172-178` (spec.md:59) | `Order.status` 집계 로직 | 172 주석 → 178 `status_whens.append` — **정확히 일치** |
| `test_spec_015.py:332-345` (spec.md:31,85, plan.md:217) | `test_partial_shipment_stamps_time_but_leaves_status_unchanged` | `def` 332, 마지막 단정 `assert li.logistics_status == "outbound_scheduled"` 345 — **정확히 일치** |
| `test_spec_018.py:40`, `:64`, `:483-551` (plan.md:29,90) | `CaptureQueriesContext` import / `UNORDERED_ENDPOINT_QUERY_COUNT = 3` / 쿼리수 테스트 | 40, 64, 483~550(551 공백) — 정확 |
| **`test_spec_018.py:502-504` (워밍업, plan.md:29,218)** | 워밍업 요청 위치 | 502 `# Warm the auth/JWT machinery so first-request-only lookups do not`, 503 주석 계속, 504 `auth_client.get(UNORDERED_URL)` — **저자의 수정이 옳다. `:490-492`는 오류였고 `:502-504`가 정답이다.** |
| `test_spec_021.py:281-283` (plan.md:29,90) | `CaptureQueriesContext` 관례 | 279 워밍업 요청, 281 `with CaptureQueriesContext(connection) as ctx_x:` — 정확 |
| `.env` 원격 RDS (spec.md:29) | 쿼리당 ~130ms 근거 | `DB_HOST=gimssine.c96se8scy765.us-west-2.rds.amazonaws.com`, `DB_ENGINE=…mysql` — 확인 |
| `quality.yaml development_mode: "tdd"` (plan.md:15) | TDD 방법론 | `:4 development_mode: "tdd"` — 정확 |

### 프론트엔드 — 전부 정확

| 인용 | 검증 결과 |
|---|---|
| `OrdersPage.tsx:280-287` (spec.md:25) | `<th>`8개가 정확히 280~287 (주문번호/스토어/위치/고객/결제상태/출고상태/금액/주문일) — 정확 |
| `OrdersPage.tsx:81-94` `getDisplayStatus` | `function` 81, `}` 94 — 정확 |
| `OrdersPage.tsx:96-104` `getFulfillmentLabel` | `function` 96, `}` 104 — 정확 |
| `OrdersPage.tsx:284-285` (결제상태/출고상태 `<th>`) | 284/285 — 정확 |
| `OrdersPage.tsx:203-214` / `:229-239` (두 필터 `<select>`) | `aria-label="결제 상태 필터"` 207, `aria-label="출고 상태 필터"` 233, 블록 경계 정확 |
| `OrdersPage.tsx:293` `colSpan={8}` | 293 — 정확 |
| `OrdersPage.tsx:278-289` (헤더 블록, plan.md:65) | `<thead>` 278 … `</thead>` 289 — 정확 |
| `OrdersPage.tsx:300-348` (본문 셀, plan.md:67), `:306-308` (주문번호 셀) | map 300, `))}` 348; 주문번호 `<td>` 306-308 — **정확히 일치** |
| `types/order.ts:8-23` (`Order`), `:64-73` (`OrderListParams`) | 8 `export interface Order {` … 23 `}`; 64 … 73 — 정확 |
| `useOrders.ts:13-21` (파라미터 매핑), `:9-28` | 13 `const searchParams`, 21 `if (params.search)` — 정확 |
| `SearchTab.test.tsx:28-45` `buildOrder()` | `function buildOrder(overrides: Partial<Order> = {}): Order {` 28, `}` 45 — **정확히 일치** |
| `purchaseOrderApi.ts:76` (`outbound_scheduled` 수동 옵션) | `{ value: 'outbound_scheduled', label: '출고예정' },` 76 — **정확히 일치** |
| `OutboundPage/logisticsStatusLabels.ts` (plan.md:68) | 존재. `Record<string, string>`(:11), 5개 키만 있고 `partial`/`partial_shipped` 없음 → **"로컬 스프레드 확장 필요"라는 plan.md:68의 주장이 정확** |

### 드리프트 3건 (전부 Low)

1. **Django `query.py:609-620`** (spec.md:303) — 설치본에서 `def count(self):`는 **608행**이다.
   609-620은 docstring+본문(핵심 분기 `if self._result_cache is not None: return len(self._result_cache)`는
   616-617)만 덮는다. `def` 한 줄이 빠졌다.
2. **`test_spec_021.py` "전량(T1~T22)"** (plan.md:39,73,184, acceptance.md:270,315) — **T11이 존재하지 않는다.**
   `grep -c "^def test_"` = 21. 마커는 T1~T10, T12~T22.
3. **acceptance.md:317 "기존 sync-status 테스트(sync 관련 6개)"** — `OrdersPage.test.tsx`의 `it(` 개수는
   **7개**(:85, 94, 104, 118, 132, 145, 159)다.

### 반증 검증 (짐작 대신 직접 확인한 부정 주장들)

- **`orders_exchangerate` 부분문자열 함정 없음.** SPEC-ORDER-021 감사 D1(`orders_line_item` ⊂
  `orders_line_item_note`)과 같은 덫이 AC-OLIST-019 (b)에 있는지 확인하려고 `models.py`의 `db_table`
  18개를 전부 열거했다. `orders_exchangerate`를 접두사로 갖는 테이블은 없다. **이 AC는 안전하다.**
- **`outbound_scheduled`에 자동 기록 경로 없음 — 사실.** `grep -rn "outbound_scheduled" backend/ --include=*.py`
  결과 `models.py:12`(choices 정의)와 `:212`(주석)뿐. 프로덕션 코드에 쓰기 경로가 없다.
  프론트엔드는 `purchaseOrderApi.ts:76`의 수동 드롭다운뿐. **spec.md:60의 가정 2는 검증됨.**
- **부분출고가 `logistics_status`를 이동시키지 않음 — 사실.** `test_spec_015.py:332-345`가 직접 단정하며,
  구현측 `purchase_order_views.py:3411/3456/3972`가 `shipped_quantity >= effective_quantity`일 때만
  `shipped`로 전이한다. **spec.md:31의 핵심 동인은 정확하다.**
- **`order_cancelled`는 `ready_to_ship`에서만 제외되고 `status`에서는 제외되지 않음 — 사실.**
  `purchase_order_views.py:176-177`의 `status` 집계는 `items` 전체를 쓰고,
  `:188`의 `non_cancelled = [it for it in (items or []) if it[1] != "order_cancelled"]`는
  `ready_to_ship`에만 적용된다. (단, SPEC 본문은 `order_cancelled`를 한 번도 언급하지 않는다 — M9 참조.)
- **Django prefetch 캐시 재사용 주장 — 사실이지만 버전 근거가 어긋남.**
  `QuerySet.exists()`(`query.py:1283-1289`)와 역방향 FK 매니저 `get_queryset()`
  (`related_descriptors.py:752-766`, `_prefetched_objects_cache` 반환)은 **인용 행 범위가 정확히 일치**한다.
  `count()`는 위 드리프트 1. **그러나 spec.md:301이 근거로 삼은 "설치된 Django 5.1.6"은
  `backend/poetry.lock`이 고정한 버전이 아니다 — 락파일은 `version = "5.2.17"`(:168)이고
  `pyproject.toml:10`은 `django = "^5.0"`이다.** 결론(캐시 재사용) 자체는 두 버전 모두에서 유효하지만,
  근거 행번호는 프로젝트가 선언한 의존성이 아니라 로컬 인터프리터의 것이다.

**Focus Area 1 결론: PASS.** 인용 무결성은 이 SPEC의 강점이다.

---

## Focus Area 2 — 인수 기준 판별력 (27개 전수 mutation 분석)

각 AC에 대해 "그럴듯한 오구현"을 실제 소스에 대해 구성하고, AC가 그것을 잡는지 판정했다.

| AC | 대상 mutation | 판정 |
|---|---|---|
| 001 | `has_refund`만으로 배지 판별 | 잡음 (`has_refund=false` 픽스처) |
| 002 | — | 잡음 (단, 문자열 매칭 함정 M3) |
| 003 | `financial_status`만으로 판별 | 잡음 |
| 004 | **`getDisplayStatus`를 그대로 재사용(정상 주문에 "결제완료" 배지 렌더)** | **못 잡음 → H6** |
| 005 | `colSpan={8}` 유지 / 헤더 순서 오류 | 잡음 (`compareDocumentPosition` 사용 명시, 강력) |
| 006 | **규칙 2를 규칙 1보다 먼저 평가** | **못 잡음 → C2 (픽스처가 `shipped_quantity` 미지정)** |
| 007 | `shipped_quantity >= quantity` | 잡음 |
| 007 | `received_quantity > 0`(엉뚱한 필드) | 잡음 (기본값 0) |
| 008 | `shipped_quantity >= 0` / `is not None` | 잡음 — **단, 정상 구현에서도 실패 → C3** |
| 009 | 규칙 3을 규칙 2보다 먼저 평가 | **잡음.** `logistics_status='received'` + `shipped_quantity=3` 조합이 실제로 구성 가능함을 `test_spec_015.py:332-345`와 `purchase_order_views.py:3411`로 독립 확인했다. 두 순서의 기댓값이 `partial_shipped` vs `outbound_scheduled`로 실제 갈린다. **저자 주장 정확.** |
| 010 | 규칙 3 누락 | 잡음 |
| 011 | `sku__isnull=False` 누락(물류 경로) | 잡음 (`shipped_quantity=99` 극단값) |
| 012 | 필드 자체 미구현 | **못 잡음 → H1 (`.get()` → `None`)** |
| 013 | 규칙 4 passthrough 오류 | 잡음 — **단, 정상 구현에서도 실패 → C3** |
| 014 | `any` → `all` | 잡음 |
| 015 | — | 잡음 |
| 015 | **`sku__isnull=False` 누락(발주 경로)** | **못 잡음 → H4** |
| 016 | 필드 자체 미구현 | **못 잡음 → H1** |
| 017 | 배송비·창고비 누락(`70.00` vs `67.75`) | 잡음. 재유도: 37500/1000=30.00, books 3 → 1250+500×2=2250 → 2.25, 100−30−0−2.25=**67.75** ✓ |
| 017 | 상세 필드 집합 재사용 | 잡음 (금지 6키 부재 단정) |
| 017 | **양자화 순서 오류 / ROUND_HALF_EVEN** | **못 잡음 → M2 (구성요소가 전부 정확히 2자리)** |
| 018 | 필드 자체 미구현 | **못 잡음 → H1** |
| 018 | 원인 1(환율 없음)·원인 3(`total_price==0`) | **못 잡음 → H3 (원인 2만 커버)** |
| 019 | `_get_exchange_rate` 무수정 재사용 | **잡음.** 서로 다른 두 날짜 → pk 메모이즈 시 2회, 날짜 메모이즈 시에도 2회, 배치 시 1회. 2 vs 1로 판별 가능. 기대값 1은 REQ-OLIST-019에서 유도된 값이지 추측이 아니다. **페이지 크기 2로 충분하다.** |
| 019 | 페이지 최댓값 환율을 전원에게 적용 | 잡음. Y 재유도: 37500/1250=30.00, 2250/1250=1.80, 100−30−0−1.80=**68.20** ✓ (`test_spec_021.py:344-356` T12 픽스처와 일치 확인) |
| 020 | 정확일치 적재(폴백 없음) | 잡음 |
| 021 | `LineItem.objects.filter(order=obj)` N+1 | 잡음 |
| 021 | **REQ-OLIST-022("이전 대비 증가 없음") 위반** | **못 잡음 → C1 (절대상수를 구현 후 실측해 채우므로 어떤 구현이든 통과)** |
| 022 | 필터/표시 경로 우선순위 불일치 | **부분적.** `partial_shipped` 1개 값만 검증. `Q(all_shipped=False)` 누락 mutation도 못 잡음(비교 대상 출고완료 주문의 `shipped_quantity` 미지정) → **C2 / H2** |
| 023 | Python 사후 필터링 | 잡음 |
| 024 | — | 판정 불가 (M10, "이전과 동일" 서술) |
| 025 | 추출 리팩터링 회귀 | **부분적.** `git diff`는 pytest 단정이 아님 → M5. `test_spec_021.py` 재통과가 실질 게이트 |
| 026 | — | 잡음 (단, 라벨 충돌 M4) |
| 027 | null 폴백 누락 / 하드코딩 | 잡음 (2단 픽스처) |

**요약: 27개 중 3개가 오늘 코드에서 통과(H1), 2개가 정상 구현에서 실패(C3), 6개 mutation 계열이
전혀 커버되지 않는다(C1·C2·H2·H3·H4·M2).**

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.60 | 0.50–0.75 사이 | 34개 REQ는 대부분 단일 해석. 감점 3건: (1) spec.md:52의 등식 "trackable 라인아이템이 0개(`Order.status is None`)"는 **거짓** — `Order.status`는 집계가 한 번도 돌지 않은 주문에서도 NULL이다(C3). (2) REQ-OLIST-022(spec.md:143)와 REQ-OLIST-019(:137)+plan.md:41이 정면 충돌(C1). (3) spec.md:36/45의 "`getDisplayStatus`를 그대로 재사용"은 문자 그대로 따르면 REQ-OLIST-006을 위반한다(H6) |
| Completeness | 0.75 | 0.75 — 비핵심 항목 1건 누락/희박 | 전 섹션 존재: HISTORY(:15-19), 문제 정의(:23-31), 목표(:33-39), 확정된 사용자 결정(:41-55), 명시적 가정(:57-62), 범위 델타(:64-78), 관련 SPEC(:80-85), 요구사항(:89-173), 인수 기준(:177-285), 설계 결정(:289-297), 사전 검증(:299-306), 제약사항(:308-314), Exclusions(:316-324, **7건 전부 구체적**), 후속 과제(:326-330). frontmatter 완비. 감점: null/빈 상태 커버리지 부재(H3), `Order.status IS NULL` 미분석(C3), `order_cancelled` 미언급(M9), 설계 결정 A가 상한 설계를 plan.md에 위임했으나 plan.md가 정하지 않음(M6) |
| Testability | 0.45 | 0.25–0.50 사이 | 3개 AC가 오늘 코드에서 통과(H1), 2개가 정상 구현에서 실패(C3), 1개는 pytest로 표현 불가(M5), 1개는 이진 단정이 아님(M10). 가장 실제적인 프로덕션 오류(규칙 1↔2 순서)를 어떤 AC도 잡지 못한다(C2). 반면 AC-OLIST-009/011/014/019/020은 진짜로 강력하다 |
| Traceability | 0.65 | 0.50–0.75 사이 | spec.md:250-283 추적표는 형식적으로 완전하다 — REQ 34개 전부 ≥1 AC, AC 27개 전부 실재 REQ 참조, 고아 없음. 그러나 **매핑이 실제 커버리지를 과장한다**: REQ-OLIST-024(6개 값)→AC-OLIST-022는 1개 값만, REQ-OLIST-017(3개 원인)→AC-OLIST-018은 1개 원인만, REQ-OLIST-022→AC-OLIST-021은 아무것도, REQ-OLIST-006→AC-OLIST-004는 배지 부재 아닌 특정 문자열 부재만, REQ-OLIST-013/014의 trackable 조항은 어떤 AC도 검증하지 않는다. spec.md:285의 "34개 요구사항 전량이 27개 인수 기준으로 직접 커버된다"는 **과장된 주장**이다 |

---

## Defects Found

### Critical

**C1. spec.md:143 (REQ-OLIST-022) vs spec.md:137 (REQ-OLIST-019) + plan.md:41,129 — [HARD] 요구사항이
자기 설계로 충족 불가능하고, 이를 검출하는 AC가 없다.**

REQ-OLIST-022는 "총 SQL 쿼리 수가 **이 SPEC 이전 대비** 증가하지 않아야 한다"고 [HARD]로 규정한다.
그런데 오늘 `OrderListSerializer`(serializers.py:25-54)는 `ExchangeRate`를 **0회** 조회한다(직접 확인:
`has_refund`/`line_items_count` 두 게터뿐). REQ-OLIST-019는 "최대 1회"를 요구하고, plan.md:41/129는
`ExchangeRate.objects.filter(effective_date__lte=max_date)` 단일 쿼리를 `list()`에서 발급하도록
명시한다 → **총 쿼리 수는 정확히 +1이 된다.** REQ-OLIST-022는 문자 그대로 위반된다.
spec.md:39의 목표 5("신규 열 3개가 페이지당 쿼리 수를 늘리지 않도록")도 같은 오류를 반복한다.

더 심각한 것은 검출 불가능성이다. AC-OLIST-021(acceptance.md:221-228)은 (i) 1건 vs 5건 요청의
쿼리 수 동일성과 (ii) "구현 시점 실측 절대값" `ORDER_LIST_QUERY_COUNT` 고정만 단정한다.
(i)은 페이지 크기 무관성(O(1))을 볼 뿐 SPEC 전후 비교가 아니고, (ii)의 상수는 **구현 결과를 그대로
기록**하므로 어떤 구현이든 통과한다. plan.md:24/172가 M0에서 SPEC 이전 베이스라인을 측정하도록
지시하지만, **그 베이스라인과 비교하라는 단정은 어디에도 없다.** 즉 REQ-OLIST-022는
"하드코딩된 상수로 만족되는" 요구사항이다.

정정: REQ-OLIST-022를 실제 의도("페이지 크기·주문 수에 비례해 증가하지 않는다" = O(1))로 다시 쓰거나,
"`ExchangeRate` 배치 로드 1회를 제외하고 증가하지 않는다"로 예외를 명시하라. 그리고 AC-OLIST-021의
Then에 "M0에서 실측한 SPEC 이전 절대값 + 1과 정확히 같다"는 단정을 추가하라
(선례: `test_spec_018.py:539-545` "the count is pinned EXACTLY, not merely to itself").

**C2. spec.md:194/235, acceptance.md:75-81/234-241 (AC-OLIST-006, AC-OLIST-022) — 규칙 1과 규칙 2의
우선순위가 전혀 검증되지 않으며, 픽스처가 프로덕션에서 존재할 수 없는 상태를 쓴다.**

`purchase_order_views.py:3411`(`if line_item.shipped_quantity >= effective_quantity:` → `logistics_status`
= `"shipped"`), `:3456`, `:3972`를 직접 확인했다. **프로덕션에서 `logistics_status='shipped'`인 라인아이템은
반드시 `shipped_quantity >= quantity > 0`이다.** 즉 실제 데이터에서는 규칙 1과 규칙 2가 **항상 동시에
성립**하며, 순서가 뒤바뀌면 **모든 출고완료 주문이 "부분출고"로 표시된다** — 이 SPEC이 만들 수 있는
가장 흔하고 눈에 띄는 버그다.

그런데 AC-OLIST-006의 Given은 `logistics_status="shipped"`만 지정하고 `shipped_quantity`를 지정하지
않는다 → 기본값 0 → 규칙 2가 발화하지 않으므로 **순서를 뒤집어도 통과한다.** AC-OLIST-022의 비교 대상
주문(출고완료)도 동일한 결함을 갖는다 → 필터를 `Q(any_partial=True)`만으로 구현해
`Q(all_shipped=False)` 우선순위 조항을 통째로 빠뜨려도 통과한다.

spec.md:203/acceptance.md:108이 "규칙 2와 규칙 3이 실제로 동시에 성립 가능한 유일한 조합"이라고
단언한 것도 **틀렸다** — 규칙 1과 규칙 2가 동시에 성립하는 경우가 프로덕션의 정상 상태다.

정정: AC-OLIST-006의 Given을 `logistics_status="shipped", shipped_quantity=quantity(>0)`으로 바꾸고,
판별력 항목에 "규칙 2를 먼저 평가하면 `partial_shipped`가 되어 실패한다"를 명시하라.
AC-OLIST-022의 출고완료 주문에도 동일하게 `shipped_quantity=quantity`를 지정하라.

**C3. acceptance.md:92-99, :135-141 (AC-OLIST-008, AC-OLIST-013) — 정상 구현에서 실패한다.
spec.md:52의 등식이 거짓이기 때문이다.**

REQ-OLIST-011은 규칙 4에서 `Order.status`를 **그대로 통과**시킨다. 그런데 `Order.status`는
`_recompute_order_aggregates`만 쓰는 저장형 집계값이고, 이 함수의 호출자는
`purchase_order_views.py`의 9개 쓰기 뷰뿐이다(`grep -rn "_recompute_order_aggregates" backend/`로
확인 — Shopify 동기화 경로에 호출자 없음). `shopify_orders.py:137-147`은 `status`를 `defaults`에서
**의도적으로 제외**한다("SPEC-ORDER-011 REQ-LOGI-011: `status` intentionally excluded"). 모델 기본값도
없다(`models.py:49-54`, `null=True`, `default` 없음).

→ **물류 쓰기 작업을 한 번도 거치지 않은 주문은 trackable 라인아이템이 있어도 `Order.status IS NULL`이다.**

AC-OLIST-008과 AC-OLIST-013의 Given은 라인아이템의 `logistics_status`만 지정하고 `Order.status`를
지정하지 않는다. ORM으로 직접 만든 픽스처(`test_spec_021.py:65-73`의 `_make_order` 관례)에서는
`Order.status`가 None이므로, **정상 구현은 `None`을 반환하고 두 AC는 `"not_shipped"` / `"shipment_confirmed"`
단정에서 실패한다.** SPEC-ORDER-021 감사의 D1/D3와 정확히 같은 계열(정상 구현을 깨는 AC)이며,
RED/GREEN 사이클 하나를 통째로 소모하고 구현자를 잘못된 "수정"으로 유도한다.

부수 결함: spec.md:52는 "trackable 라인아이템이 0개(`Order.status is None`) → `-`"라며 두 조건을
**등치**시킨다. 위 분석대로 거짓이며, REQ-OLIST-012는 trackable 개수 기준, REQ-OLIST-011은 `status` 기준으로
서로 다른 조건을 쓴다.

정정(택1): (a) 두 AC의 Given에 `Order(status="not_shipped")` / `Order(status="shipment_confirmed")`를
명시하고, spec.md:52의 괄호 등식을 삭제하라. (b) 더 나은 선택 — REQ-OLIST-011을 "저장된 `Order.status`"가
아니라 "`_recompute_order_aggregates`와 동일한 규칙으로 trackable 라인아이템에서 그 자리에서 파생
(균일하면 그 값, 2개 이상이면 `partial`)"로 바꿔라. 그러면 C3·H5가 동시에 해소되고, 필터(SQL) 경로와
표시(Python) 경로의 정의 일치(설계 결정 B)도 `Order.status` 신선도에 의존하지 않게 된다.
**어느 쪽을 고르든 SPEC 본문에 "규칙 4는 저장형 집계값이며 최신이 아닐 수 있다"는 사실을 기록해야 한다.**

### High

**H1. acceptance.md:127-133, :164-170, :187-193 (AC-OLIST-012, 016, 018) — 오늘의 무수정 코드에서 통과한다.
SPEC-ORDER-021 감사 D6의 정확한 재발이다.**

세 AC의 Then은 각각 `logistics_display is None` / `purchase_display is None` / `margin_rate is None`이다.
이 저장소의 확립된 관례는 `res.data.get("margin_amount")`(`test_spec_008.py:235,254,282`,
`test_spec_009.py:177,224`)이고, 키가 없으면 `.get()`은 `None`을 돌려준다 → **신규 필드가 아예 없는
현재 코드에서 세 단정 모두 참이다.** plan.md:177의 "AC-OLIST-006~018이 신규 필드 부재 상태에서
실패함을 확인했다"와 plan.md:28의 RED 전제가 이 세 건에 대해 성립하지 않는다.

SPEC-ORDER-021 v1.1.0 HISTORY(:23)는 이 결함을 "D6(major) — … `"shipping_cost" in res.data` 키 존재
단정으로 명시"로 이미 해소했다. 같은 저자가 같은 함정에 다시 빠졌다.

정정: 세 AC의 Then을 2단 단정으로 명시하라 — `"logistics_display" in item` **그리고**
`item["logistics_display"] is None`.

**H2. spec.md:149,235 (REQ-OLIST-024, AC-OLIST-022) — 6개 필터 값 중 1개만 검증한다.
`partial_shipped`만 처리하고 나머지 5개를 무시하는 구현이 전 스위트를 통과한다.**

REQ-OLIST-024는 허용 값이 정확히 `{not_shipped, shipment_confirmed, outbound_scheduled, partial_shipped,
shipped, partial}` 6개라고 규정하고, 추적표(spec.md:273)는 이를 AC-OLIST-022/026이 커버한다고 주장한다.
그러나 AC-OLIST-022는 `?logistics_display=partial_shipped` 하나만, AC-OLIST-026은 드롭다운에서
"부분출고" 선택 하나만 검증한다. **가장 복잡한 `outbound_scheduled`(plan.md:52의
`Q(all_received=True) | Q(status="outbound_scheduled")` 이접)를 포함해 5개 값이 전혀 테스트되지 않는다.**
허용되지 않는 값이 들어왔을 때의 동작(무시? 400? 빈 결과?)도 REQ에 없고 AC에도 없다.

이것이 plan.md R4(:148)가 지목한 "필터(SQL)와 표시(Python)의 이중 구현" 리스크의 실체다.
**AC 1개로는 불충분하다.** 두 경로가 `outbound_scheduled`·`partial`·`not_shipped`에서 갈려도
전 스위트가 통과한다.

정정: 6개 값 각각에 대해 "필터 결과에 포함된 주문의 `logistics_display` 표시값이 요청한 값과 같다 +
제외된 주문은 그 값이 아니다"를 단정하는 파라미터화 AC(또는 6개 AC)로 확장하라. 허용 외 값의 동작을
REQ-OLIST-024에 규정하고 AC를 추가하라.

**H3. spec.md:131,224 (REQ-OLIST-017, AC-OLIST-018) — null 게이트 3개 원인 중 1개만 검증한다.**

REQ-OLIST-017은 (1) 환율 없음 (2) `confirmed_price` 전무 (3) `total_price == 0` 세 개의 독립 원인을
열거하고, 소스에서 셋 다 확인된다(`serializers.py:299-301`, `:318-319`, `:376-377`). AC-OLIST-018은
**(2)만** 검증한다. (1)과 (3)은 커버 0이다. 게다가 실제 코드에는 두 경로가 더 있다:
`obj.shopify_created_at`이 None이면 환율 조회가 None을 반환하고(`serializers.py:243-244`),
`total_price`가 NULL이면 `Decimal(str(obj.total_price or "0"))`로 0이 되어 (3)에 합류한다.
REQ-OLIST-017은 이 둘을 열거하지 않는다.

**특히 (1)은 배치 로드 구현에서 가장 깨지기 쉬운 지점이다** — 이력 리스트가 비었거나 주문일 이하
레코드가 하나도 없을 때 `IndexError`를 던지지 않고 `None`을 반환해야 한다.

정정: 원인 (1)·(3)에 대한 AC 2건을 추가하고, `shopify_created_at is None` 및 `total_price is None`을
REQ-OLIST-017에 명시하라.

**H4. spec.md:121,123,217 (REQ-OLIST-013/014, AC-OLIST-015) — 발주상태 경로의 trackable 필터가
전혀 검증되지 않는다. `purchase_status` 기본값이 `"unordered"`라 파급이 크다.**

`models.py:190-194`에서 `purchase_status`의 기본값은 `"unordered"`다. 따라서 `sku=None`인
non-trackable 라인아이템은 **기본적으로 미발주**다. 구현자가 발주상태 계산에서 `sku__isnull=False`
필터를 빠뜨리면 non-trackable 항목을 가진 모든 주문이 "미발주"로 잘못 표시된다.

AC-OLIST-011은 이 mutation을 **물류상태에 대해서만** 잡는다(`purchase_display`를 단정하지 않음).
AC-OLIST-014/015의 픽스처에는 non-trackable 항목이 없다. **커버리지 0.**

정정: AC-OLIST-011의 Then에 `purchase_display == "ordered"`를 추가하고, trackable 항목의
`purchase_status`를 `"in_stock"`으로, non-trackable 항목을 기본값 `"unordered"`로 두어라.
그러면 필터 누락 시 `"unordered"`(오답)가 나와 판별된다.

**H5. spec.md:59-60 (명시적 가정 1·2) — "규칙 4에 도달 가능한 값은 4가지뿐"이 거짓이며,
열거되지 않은 7번째 라벨이 화면에 나올 수 있다.**

가정 1은 "`received`는 규칙 3이 항상 먼저 가로채고 `shipped`는 규칙 1이 항상 먼저 가로챈다"고 주장한다.
이는 `Order.status`가 라인아이템과 **항상 동기화되어 있을 때만** 성립한다. 반례를 구성했다:

1. 주문의 trackable 항목이 전부 `received` → 물류 업로드가 `_recompute_order_aggregates`를 돌려
   `Order.status = "received"`.
2. Shopify 재동기화가 라인아이템을 하나 추가한다(`shopify_orders.py`는 `_recompute_order_aggregates`를
   호출하지 않는다 — 위 grep 확인). 신규 항목의 `logistics_status` 기본값은 `"not_shipped"`.
3. 이제 규칙 1(x), 규칙 2(x), 규칙 3(x — 전부 received가 아님) → **규칙 4가 `"received"`를 통과시킨다.**

`received`는 REQ-OLIST-024의 6개 허용 값에 없고, 결정 7의 필터 옵션에도 없다. 프론트엔드는
`LOGISTICS_STATUS_LABELS`(logisticsStatusLabels.ts:14)로 "입고"를 렌더하게 되어 **필터로 도달할 수 없는
7번째 라벨**이 생긴다. `shipped`도 같은 방식으로 도달 가능하다. REQ-OLIST-030의 "REQ-OLIST-011이
통과시킨 어떤 raw `status` 값이든 그에 대응하는 라벨"이라는 문구가 이 구멍을 무의식적으로 인정하고
있으나, REQ-OLIST-024·026과 모순된다.

정정: C3의 정정 (b)를 채택하면(규칙 4를 라인아이템에서 직접 파생) 이 결함이 함께 사라진다.
(a)를 택한다면 REQ-OLIST-024에 `received`를 추가하고 결정 7의 "6개"를 7개로 고치거나,
REQ-OLIST-011에 "`received`/`shipped`가 통과되면 각각 규칙 3·1의 결과로 정규화한다"를 명시하라.

**H6. spec.md:36,45,103 (목표 2, 결정 3, REQ-OLIST-006) vs acceptance.md:47-53 (AC-OLIST-004) —
SPEC이 지시하는 구현이 REQ-OLIST-006을 위반하는데 AC가 잡지 못한다.**

spec.md:36은 "기존 `getDisplayStatus` 판별식(`:81-94`)을 **그대로 재사용**한다", 결정 3(:45)은
"판별식은 기존 `getDisplayStatus`와 **완전히 동일**하다"고 한다. 그런데 실제
`getDisplayStatus`(OrdersPage.tsx:81-94)는 앞 3개 분기 이후에도 `paid → '결제완료'`,
`pending → '결제대기'` 등 **결제상태 라벨 맵(:86-93)을 반환**한다. 이 함수를 문자 그대로 배지에
재사용하면 정상 주문에 "결제완료" 배지가 붙어 REQ-OLIST-006("어떤 취소 배지도 렌더하지 않는다")을
위반한다.

AC-OLIST-004의 Then은 "'취소'/'부분취소' 텍스트가 렌더되지 않는다"뿐이므로 **"결제완료" 배지는
통과시킨다.** 즉 SPEC의 산문이 유도하는 오구현을 SPEC의 AC가 승인한다.

정정: 결정 3/목표 2의 문구를 "`getDisplayStatus`의 **앞 3개 분기와 동일한 판별식**을 쓰되, 그 외에는
배지를 렌더하지 않는다"로 바꾸고, AC-OLIST-004의 Then을 "주문번호 셀에 배지 요소 자체가 존재하지
않는다(`queryByTestId('cancel-badge')` 부재)"로 강화하라. 겸사겸사 `getDisplayStatus`의 잔여
맵(:86-93)이 사용처 없는 죽은 코드가 되는지도 plan.md에서 명시하라.

### Medium

**M1. spec.md:181-246 — 27개 AC 전부가 EARS 문장이 아니라 EARS 라벨이 붙은 한국어 시나리오다.**
MP-2 참조. SPEC-ORDER-021이 EARS 문장으로 작성했던 것에서의 퇴행이다. `acceptance.md`가 Given/When/Then을
담당하는 구조이므로 `spec.md`의 AC는 EARS 문장이어야 한다.

**M2. spec.md:129,221 / acceptance.md:180-185, :203-210 — 마진 양자화 순서와 반올림 모드를
어떤 AC도 판별하지 못한다.**
모든 마진 픽스처의 구성요소가 정확히 2자리로 떨어진다: AC-OLIST-017/020은 30.00 / 0.00 / 2.25,
AC-OLIST-019의 Y는 30.00 / 0.00 / 1.80. 따라서 (a) 양자화된 값을 합산하는 오구현과
(b) `ROUND_HALF_EVEN`이 전부 통과한다. SPEC-ORDER-021은 이 두 구멍을 각각 AC-COST-015(1센트 차이)와
AC-COST-013(`2.725 → "2.73"`)으로 닫았는데, SPEC-023이 **목록 경로에 대해 다시 열었다.**
설계 결정 C가 공용 헬퍼 추출을 요구하므로 `test_spec_021.py` T13/T15 재통과가 부분적 방어막이 되지만,
목록 전용 `get_margin_rate`가 독자적으로 재양자화하는 mutation은 잡히지 않는다.
정정: `grams=500, quantity=1`(→ `2.725`) 또는 1센트 차이 픽스처를 쓰는 AC 1건을 목록 엔드포인트에 추가하라.

**M3. acceptance.md:36 (AC-OLIST-002) — "'취소' 텍스트는 렌더되지 않는다"는 정상 구현에서 실패할 수 있다.**
`"부분취소"`는 `"취소"`를 부분문자열로 포함한다. `queryByText(/취소/)` 같은 자연스러운 관용구로
작성하면 정상 구현에서 매칭되어 실패한다. SPEC-ORDER-021 감사 D1(`orders_line_item` ⊂
`orders_line_item_note`)과 같은 계열. 정정: "정확 일치(`{ exact: true }`)로 `'취소'` 텍스트 노드가
없음을 단정한다"고 명시하라.

**M4. acceptance.md:281,291-293 (AC-OLIST-026, AC-OLIST-027) — "부분출고" 라벨이 필터 드롭다운 옵션과
셀에 동시에 존재해 `getByText`가 다중 매칭으로 실패한다.**
REQ-OLIST-026이 드롭다운에 "부분출고" 옵션을 요구하고, REQ-OLIST-030이 셀에 같은 문자열을 렌더한다.
정정: 두 AC에 "셀 범위로 스코프된 조회(`within(row).getByText(...)`)"를 명시하라.

**M5. acceptance.md:264-270, :310 (AC-OLIST-025) — pytest 단정으로 표현 불가능한데
`test_spec_023.py` 담당으로 매핑되어 있다.**
Then이 "이 SPEC 적용 전과 완전히 동일" + "`git diff`로 확인"이다. 이는 프로세스 게이트지 런타임
단정이 아니다. 반면 acceptance.md:310의 DoD 표는 이를 `test_spec_023.py`에 배정한다.
정정: AC-OLIST-025를 (a) 자동화 가능한 부분(`test_spec_021.py` 전량 무수정 재통과 + `GET /api/orders/{pk}/`
응답 키 집합 고정 단정)과 (b) 수동 게이트(`git diff`)로 분리하고, (b)는 plan.md의 Done 체크리스트로
옮겨라.

**M6. spec.md:291 (설계 결정 A) vs plan.md:129 — 상한 설계를 plan.md에 위임했으나 plan.md가 정하지 않았다.**
설계 결정 A는 "정확한 상한(전체 이력 대 페이지 최소일 기준 lookback 윈도) 설계는 `plan.md`가 정한다"고
위임한다. plan.md:129는 `ExchangeRate.objects.filter(effective_date__lte=max_date)` — **하한이 없다.**
즉 전체 이력을 매 리스트 요청마다 파이썬 메모리로 적재하며, 이 크기는 SPEC-ORDER-022의 일 단위
백필 때문에 단조 증가한다. "행 수가 작다(수백~수천 행 수준)"는 근거 없는 단언이다.
정정: plan.md에 하한(예: 페이지 최소 주문일 − N일, 또는 `values_list("effective_date","rate")` 사용)을
명시하고, 폴백이 하한 밖으로 나갈 때의 처리를 규정하라.

**M7. spec.md:301-306 — Django 버전 근거가 프로젝트 선언 의존성이 아니다.**
"설치된 Django 5.1.6의 소스로 확인했다"고 하나 `backend/poetry.lock:168`은 `version = "5.2.17"`,
`backend/pyproject.toml:10`은 `django = "^5.0"`이다. 결론(prefetch 캐시 재사용)은 두 버전 모두에서
유효함을 `query.py`/`related_descriptors.py`에서 확인했으나, 인용 행번호는 5.1.6 기준이며 5.2.17에서
달라질 수 있다. 정정: 근거 문장을 "`poetry.lock`이 고정한 Django 5.2.17 기준"으로 바꾸고 행번호를
그 버전에서 다시 확인하거나, 행번호 대신 함수명만 인용하라.

**M8. spec.md:82 (관련 SPEC) — SPEC-ORDER-021의 Exclusion을 뒤집으면서 그 사실을 기록하지 않았다.**
`.moai/specs/SPEC-ORDER-021/spec.md:373`은 "**`OrderListSerializer`(목록 API)에 비용/마진 필드를
노출하지 않는다.** 기존 관례 유지(REQ-COST-014)"를 Exclusion으로 못박았고, :61은 그 클래스를
"[EXISTING] 무수정"으로 표시했다. REQ-OLIST-016은 `margin_rate`를 노출해 이를 뒤집는다.
(확인: REQ-COST-014 자체와 `test_spec_021.py:322-334`의 T10은 `shipping_cost`/`korea_warehouse_cost`/
`total_weight_grams` 3키만 금지하므로 **테스트는 깨지지 않는다** — 계약 충돌은 아니고 문서 충돌이다.)
정정: 관련 SPEC 절에 "이 SPEC은 SPEC-ORDER-021의 Exclusion 중 마진 필드 부분을 supersede한다"를
명시하고, SPEC-ORDER-021 문서에도 상호 참조를 남기도록 후속 과제에 넣어라.

**M9. spec.md:53,121-125 — `order_cancelled` 라인아이템이 전혀 분석되지 않았다.**
`purchase_order_views.py:188`은 `ready_to_ship` 계산에서 `purchase_status="order_cancelled"` 항목을
**완전히 제외**하지만, `status` 집계(:176-177)에서는 제외하지 않는다. SPEC-023의 발주상태 규칙
(REQ-OLIST-013/014)은 `order_cancelled`를 "unordered가 아님" → **"발주완료"**로 분류한다. 즉
trackable 항목이 전부 주문취소인 주문이 "발주완료"로 표시된다. 이것이 의도된 동작인지 SPEC 어디에도
없고, `order_cancelled`라는 단어가 세 문서에 한 번도 등장하지 않는다. 관련 AC도 없다.
정정: 명시적 가정 절에 이 분류를 기록하거나(사용자 확인 필요), `ready_to_ship` 관례대로 제외하고
AC를 추가하라.

**M10. acceptance.md:256-262 (AC-OLIST-024) — 이진 단정이 아니다.**
Then이 "이 SPEC 이전과 동일하게 필터링된 결과가 반환된다"이다. 구체적 기대값(예: "`?financial_status=paid`는
`paid` 주문 1건만 반환한다")이 없어 PASS/FAIL 판정에 판단이 개입한다.

### Low

- **L1.** spec.md:303 — Django `query.py:609-620`의 `def count(self):`는 **608행**이다(609-620은 docstring+본문).
- **L2.** plan.md:39,73,184 / acceptance.md:270,315 — "`test_spec_021.py` 전량(T1~T22)"에서 **T11이 존재하지 않는다**(총 21개, T10 다음이 T12).
- **L3.** acceptance.md:317 — "sync 관련 **6개**" → 실제 **7개**(`OrdersPage.test.tsx:85,94,104,118,132,145,159`).
- **L4.** EARS 라벨 오류 — REQ-OLIST-033(spec.md:171)·034(:173)는 `(Unwanted)` 라벨이지만 `If … then` 조건이 없는 ubiquitous 부정문이다. AC-OLIST-004(:189)·024(:240)·025(:242)의 `(Unwanted)` 라벨도 문장 형태와 불일치. **번호는 재부여하지 말고 라벨만 교정**하라(추적표 3곳이 깨진다).
- **L5.** spec.md:197 / acceptance.md:90 — AC-OLIST-007의 mutation 서술 "규칙 4로 낙하해 `"outbound_scheduled"`(오답)를 반환한다"는 `Order.status='outbound_scheduled'`를 전제하는데 Given이 그것을 설정하지 않는다(C3과 동일 원인). mutation은 여전히 잡히지만 서술이 틀렸다.
- **L6.** spec.md:29 — `_get_exchange_rate`(`:222-254`)는 실제 222-253(254는 공백). +1 초과.
- **L7.** plan.md:128-130 — `max_date`는 `shopify_created_at`(DateTimeField)에서 오고 `effective_date`는 DateField다. `_get_exchange_rate`(serializers.py:245)는 `.date()`로 변환한다. REQ-OLIST-020이 "정확히 동일한 값"을 요구하므로 `.date()` 적용 시점과 타임존(`USE_TZ`) 처리를 plan.md에 명시해야 한다. 날짜 경계 케이스 AC도 없다.
- **L8.** acceptance.md:168 — AC-OLIST-016의 Given은 "모든 라인아이템이 `sku=None`"만 다루고, AC-OLIST-012(:131)가 포함한 "라인아이템 자체가 없음" 케이스를 빠뜨렸다.

---

## Chain-of-Verification Pass

1차 통과 후 빠르게 지나쳤던 구간을 다시 읽으며 찾아낸 것들:

1. **34개 REQ를 처음부터 끝까지 다시 읽었다** — 모듈 5(성능 불변식)를 처음에는 "O(1) 보장"으로 읽고
   넘어갔다. 재독 시 REQ-OLIST-022의 문언이 "**이 SPEC 이전 대비**"임을 확인했고, 이것이 REQ-OLIST-019
   및 plan.md:41의 배치 쿼리 1회 추가와 정면 충돌함을 발견했다(**C1 — 이번 감사 최대 수확 중 하나**).
   SPEC-ORDER-021 감사에서도 REQ-COST-015의 "cost-breakdown 계산당"이라는 한정어가 같은 방식으로
   1차 통과를 빠져나갔다 — 성능 REQ의 문언은 반드시 재독해야 한다.

2. **`Order.status`가 언제 NULL인지를 짐작하지 않고 쓰기 경로를 전수 추적했다.**
   `grep -rn "_recompute_order_aggregates" backend/`로 호출자가 `purchase_order_views.py`와 테스트뿐임을
   확인하고, `shopify_orders.py:137-147`에서 `status`가 `defaults`에서 의도적으로 제외됨을 직접 읽었다.
   여기서 C3(AC-OLIST-008/013이 정상 구현에서 실패)과 H5(7번째 라벨)가 동시에 드러났다.
   1차 통과에서는 spec.md:52의 "trackable 0개(`Order.status is None`)"를 정의로 받아들이고 지나쳤다.

3. **`shipped` 상태의 `shipped_quantity`가 실제로 무엇인지 확인했다.**
   1차 통과에서는 AC-OLIST-009(규칙 2↔3 역전)의 정교함에 만족하고 넘어갈 뻔했다.
   `grep -n "shipped_quantity" backend/order/purchase_order_views.py`로 3411/3456/3972의 전이 조건을
   읽고 나서야, **규칙 1↔2 순서가 프로덕션에서 훨씬 더 자주 문제되는 지점인데 아무 AC도 커버하지
   않는다**는 C2가 보였다. 이번 감사에서 가장 가치 있는 2차 확인이다.

4. **`purchase_status`의 기본값을 확인했다.** `models.py:193`의 `default="unordered"`를 보고서야
   H4(발주 경로의 trackable 필터 미검증)의 파급이 크다는 것을 알았다 — non-trackable 항목이 자동으로
   미발주로 계산된다.

5. **오늘 코드에서 통과하는 AC를 전수 점검했다.** SPEC-ORDER-021 감사 D6을 알고 있었으므로
   `is None` 단정을 전부 찾아 검사했고 3건(AC-OLIST-012/016/018)을 확인했다(H1).

6. **필터 값 6개 각각의 커버리지를 세었다.** AC-OLIST-022를 개별로 읽으면 "이중 단정"이 훌륭해 보인다.
   REQ-OLIST-024의 6개 값 집합과 대조하고 나서야 1/6 커버리지가 드러났다(H2).

7. **`test_spec_021.py` T10을 직접 읽었다** — SPEC-023이 `OrderListSerializer`에 `margin_rate`를 추가하면
   T10이 깨질 것이라고 의심했으나, T10은 `shipping_cost`/`korea_warehouse_cost`/`total_weight_grams`
   3키만 검사하므로 **깨지지 않는다.** 이 우려는 기각한다(SPEC-021의 Exclusion 문서 충돌 M8만 남는다).

8. **34개 REQ 상호 모순 스윕.** REQ-OLIST-008~012는 상호 배타적이고 trackable 개수 위에서 전수적이다 ✓.
   REQ-OLIST-013/014는 상호 배타·전수적 ✓. REQ-OLIST-016(노출)과 018(6키 금지)은 충돌 없음 ✓.
   REQ-OLIST-033(상세 무변경)과 설계 결정 C(공용 헬퍼 추출)는 "관측 가능한 출력 동일"이라는 단서로
   양립 ✓. **유일한 진짜 모순은 REQ-OLIST-019/022(C1)이다.**

9. **Exclusions 7건의 구체성을 개별 확인했다**(spec.md:318-324). 각각 구체적 산출물 또는 사용자 결정을
   지목하며, 포함된 요구사항과 충돌하지 않는다. 특히 `LOGISTICS_STATUS_CHOICES`에 `partial_shipped`를
   추가하지 않는다는 항목(:323)은 `models.py:8-14`와 `:156-167` 인용이 정확하고 REQ-OLIST-024와
   일관된다 ✓.

10. **범위 규율(비목표 재유입) 점검.** 마진 정렬/필터 — REQ 어디에도 없음 ✓(spec.md:310, :318과 일관).
    발주상태 필터 — REQ-OLIST-026은 물류상태 드롭다운만 규정 ✓. 부분출고 사유 분류 — 어떤 REQ도
    사유 필드를 만들지 않음 ✓. `OrderDetail` 변경 — REQ-OLIST-033 + [EXISTING] 표기 ✓,
    plan.md:87의 "순수 추출 리팩터링만 허용"도 일관. **범위 밀수 없음.**

11. **결함으로 올리지 않은 잔여 사항 1건**: plan.md:68은 `OutboundPage/logisticsStatusLabels.ts`를
    `OrdersPage.tsx`에서 import하도록 지시한다. 페이지 간 결합이 생기지만 파일 자체는 수정하지 않고
    `Record<string, string>` 타입이라 확장이 안전함을 직접 확인했다(:11). 구현자 판단에 맡길 수준.

---

## Regression Check

해당 없음 — iteration 1.

---

## Recommendation

**FAIL.** 이 SPEC의 강점은 분명하다: **인용 55건 전부가 주장한 구조를 가리키며 날조가 0건이다**
(이 저장소의 과거 사고 2건을 감안하면 유의미한 성과다). 저자가 SPEC-ORDER-021에서 물려받은 잘못된
인용(`test_spec_018.py:490-492`)을 스스로 찾아 `:502-504`로 고친 것도 **직접 확인한 결과 정확하다**.
AC-OLIST-009(규칙 2↔3 역전), AC-OLIST-011(non-trackable 극단값), AC-OLIST-019(배치 환율 2건/1쿼리),
AC-OLIST-020(폴백 보존)은 진짜로 판별력 있는 설계이며, `_get_exchange_rate`의 pk 단위 메모이제이션이
목록 API에 부적합하다는 핵심 통찰도 소스로 확인된다.

그러나 **정상 구현을 깨뜨리는 AC 2건, 오늘 코드에서 이미 통과하는 AC 3건, 자기 설계로 충족 불가능한
[HARD] 요구사항 1건, 그리고 가장 흔한 프로덕션 오류(규칙 1↔2 순서)를 잡는 AC 0건**이라는 상태로는
RED에 들어갈 수 없다.

### RED 진입 전 필수 (차단)

1. **spec.md:143 + acceptance.md:221-228 (C1)** — REQ-OLIST-022를 "페이지 크기·주문 수에 비례해
   증가하지 않는다(O(1))"로 다시 쓰고, `ExchangeRate` 배치 로드 1회 추가를 명시적 예외로 기록하라.
   AC-OLIST-021의 Then에 "M0 실측 베이스라인 + 1과 정확히 같다"는 절대 단정을 추가하라
   (선례: `test_spec_018.py:539-545`). 목표 5(spec.md:39)도 함께 정정하라.

2. **acceptance.md:75-81, :234-241 (C2)** — AC-OLIST-006과 AC-OLIST-022의 출고완료 주문 픽스처에
   `shipped_quantity = quantity(>0)`을 지정하라(`purchase_order_views.py:3411`이 강제하는 실제 상태).
   AC-OLIST-006의 판별력 항목에 "규칙 2를 규칙 1보다 먼저 평가하면 `partial_shipped`가 되어 실패한다"를
   추가하고, spec.md:203/acceptance.md:108의 "규칙 2와 3이 동시 성립 가능한 유일한 조합"이라는
   틀린 문장을 삭제하라.

3. **spec.md:52,115 + acceptance.md:92-99,:135-141 (C3)** — 규칙 4의 `Order.status`가 저장형·비동기
   집계값임을 SPEC에 기록하라. **권장 해법: REQ-OLIST-011을 "trackable 라인아이템에서 즉시 파생
   (균일하면 그 값, 2개 이상이면 `partial`)"로 바꾸면 C3와 H5가 동시에 해소되고 SQL/Python 두 경로의
   정의 일치도 `Order.status` 신선도에서 분리된다.** 현행 passthrough를 유지한다면 AC-OLIST-008/013의
   Given에 `Order(status=…)`를 명시하고 spec.md:52의 괄호 등식을 삭제하라.

4. **acceptance.md:127-133,:164-170,:187-193 (H1)** — 세 AC의 Then을 키 존재 단정과 값 단정의
   2단으로 명시하라(`"logistics_display" in item` **and** `item["logistics_display"] is None`).
   plan.md:28,177의 RED 전제 문장도 함께 정정하라. SPEC-ORDER-021 v1.1.0에서 이미 해소한 결함의 재발이다.

5. **spec.md:149,235 + acceptance.md:234-241 (H2)** — 6개 필터 값 각각에 대해 "필터 결과의 표시값이
   요청값과 일치 + 비매칭 주문 제외"를 단정하도록 AC-OLIST-022를 파라미터화하라. 특히
   `outbound_scheduled`(plan.md:52의 이접 조건)와 `partial`을 반드시 포함하라. 허용 외 값의 동작을
   REQ-OLIST-024에 규정하고 AC를 추가하라.

6. **spec.md:131 + acceptance.md:187-193 (H3)** — 원인 (1) 환율 없음, (3) `total_price == 0`에 대한
   AC 2건을 추가하라. `shopify_created_at is None`과 `total_price is None`을 REQ-OLIST-017에 열거하라.

7. **acceptance.md:118-125 (H4)** — AC-OLIST-011의 Then에 `purchase_display == "ordered"`를 추가하고,
   trackable 항목을 `purchase_status="in_stock"`, non-trackable 항목을 기본값 `"unordered"`로 두어
   발주 경로의 trackable 필터 누락을 판별하게 하라.

8. **spec.md:36,45,103 + acceptance.md:47-53 (H6)** — 결정 3/목표 2를 "`getDisplayStatus`의 앞 3개
   분기와 동일한 판별식"으로 한정하고, AC-OLIST-004를 "배지 요소 자체의 부재"로 강화하라.

### 강력 권장 (RED를 막지는 않으나 각각 실제 구멍을 닫는다)

9. **spec.md:181-246 (M1)** — 27개 AC를 EARS 문장으로 재작성하라(SPEC-ORDER-021 형식으로 복귀).
10. **AC 1건 추가 (M2)** — 목록 엔드포인트에 `grams=500, quantity=1`(→ `2.725` → `"2.73"`) 또는
    1센트 차이 픽스처를 넣어 양자화 순서·반올림 모드를 판별하게 하라.
11. **acceptance.md:36, :281,:291-293 (M3, M4)** — 문자열 정확 일치와 셀 스코프 조회를 명시하라.
12. **acceptance.md:264-270,:310 (M5)** — AC-OLIST-025를 자동화 단정과 수동 게이트로 분리하라.
13. **plan.md:129 (M6)** — 배치 로드에 하한(lookback 윈도)을 정하고 폴백 실패 시 동작을 규정하라.
14. **spec.md:301-306 (M7)** — 근거 버전을 `poetry.lock`의 5.2.17로 맞추고 행번호를 재확인하라.
15. **spec.md:82 (M8)** — SPEC-ORDER-021 Exclusion supersede 사실을 명기하라.
16. **spec.md:53 (M9)** — `order_cancelled` 항목의 발주상태 분류를 명시적 가정으로 기록하라(사용자 확인 필요).
17. **acceptance.md:256-262 (M10)** — AC-OLIST-024에 구체적 기대 결과를 넣어라.
18. **L1~L8** — 인용 3건 정정(Django `:608`, "T1~T22"→"T1~T10, T12~T22", "6개"→"7개"),
    EARS 라벨 5건 재부여 없이 교정, AC-OLIST-007 mutation 서술 정정, 타임존/`.date()` 규정 추가,
    AC-OLIST-016 Given 보강.

Verdict: FAIL
