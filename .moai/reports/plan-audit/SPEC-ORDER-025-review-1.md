# SPEC Review Report: SPEC-ORDER-025

Iteration: 1/3
Overall Score: 0.62

> Reasoning context ignored per M1 Context Isolation. 본 감사는 `.moai/specs/SPEC-ORDER-025/`의 문서 5종(spec.md, acceptance.md, plan.md, research.md, spec-compact.md)과 실제 코드베이스만을 근거로 수행했다. 작성자의 추론 과정·이전 초안·대화 이력은 참조하지 않았다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  `spec.md`의 REQ는 총 27개이며 `grep -o "REQ-LCONF-[0-9]\+" | sort | uniq -c` 결과 **전부 출현 횟수 1** — 중복 0건. 블록별 연속성 확인: R1 `REQ-LCONF-001`~`015`(spec.md:45-59, 15개 연속), R2 `101`~`106`(spec.md:67-72, 6개 연속), R3 `201`~`203`(spec.md:80-82), R4 `301`~`303`(spec.md:90-92). 블록 경계(015→101, 106→201, 203→301)는 이 저장소의 확립된 블록 번호 규약이며 갭이 아니다. 제로 패딩은 3자리로 전항 일관.

- **[FAIL] MP-2 EARS format compliance**
  `spec.md:82` **REQ-LCONF-203은 `(Unwanted)`로 선언되었으나 IF/THEN 구조도, 바람직하지 않은 조건도 존재하지 않는다.** 실제 문장은 "`auto_select_distributor`/`resolve_publisher_distributor`... 와 ... `DistributorVendorRule` CRUD는 **이 SPEC에서 변경되지 않는다**" — 이는 범위 배제 진술(Ubiquitous 계열)이지 Unwanted 패턴이 아니다. 선언된 패턴과 실제 문장 구조가 불일치한다.
  추가로 4건이 EARS의 주어-응답(`THE {system} shall {response}`) 구조를 결여한다:
  - `spec.md:80` REQ-LCONF-201 `(Ubiquitous)` — "…응답의 각 결과 항목은 … 포함하지 않으며" (THE 시스템은 … 없음)
  - `spec.md:81` REQ-LCONF-202 `(Ubiquitous)` — "프론트엔드 `UnorderedItem` 타입은 … 갖지 않으며"
  - `spec.md:90` REQ-LCONF-301 `(Ubiquitous)` — "`EXCLUDED_PURCHASE_STATUSES`는 … 3개 값으로 구성된다" (시스템 행위가 아니라 소스 상수에 대한 서술)
  - `spec.md:91` REQ-LCONF-302 `(State-Driven)` — WHILE 절은 있으나 응답부 주어 누락
  27개 중 5개(18.5%)가 이탈하며 그중 1건은 명시적 패턴 오표기다. M5 기준("mislabeled as EARS = FAIL") 적용.

- **[PASS] MP-3 YAML frontmatter validity**
  `spec.md:1-11` 6개 필수 필드 전항 존재·타입 적합: `id: SPEC-ORDER-025`(:2, string, SPEC-{DOMAIN}-{NUM} 패턴 일치), `version: 1.0.0`(:3, string), `status: draft`(:4, string, 허용값), `created_at: 2026-08-17`(:5, ISO 8601 date), `priority: High`(:8, string), `labels: [order, purchase, purchase-status, distributor, frontend, backend]`(:10, array).
  Nit(비차단): `created_at`이 인용부호 없이 기술되어 YAML 파서가 `datetime.date` 객체로 역직렬화한다. 값 자체는 유효한 ISO 날짜이므로 PASS.

- **[N/A] MP-4 Section 22 language neutrality**
  단일 스택(Django 백엔드 + React/TypeScript 프론트엔드) 프로젝트에 한정된 SPEC이며, 다국어 툴체인·LSP·언어별 도구 선택을 다루지 않는다. 16개 언어 열거 요건 비적용 — 자동 통과.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 | `spec.md`의 규범 진술 자체는 대부분 단일 해석만 허용(예: :47 REQ-LCONF-003이 base_qty 산식을 명시적으로 정의). 감점 사유는 문서 간 모순(D6: plan.md:20 "간접 검증" vs acceptance.md:92-94 "mock.patch 스파이")과 미기재 제약(D13), `acceptance.md:148`의 비문("이 AC가 … 절대값은 … 검증한다"). |
| Completeness | 0.50 | 0.50 | 필수 섹션·프론트매터는 전항 존재하고 Exclusions는 5개 구체 항목으로 우수(`spec.md:98-102`). 그러나 SPEC이 의존하는 영향도 분석이 실질적으로 부정확 — "실측"이라 명시한 `research.md:90-95` §3에서 **3건의 독립적 누락**(D1/D2/D3)이 확인됨. `spec-compact.md:30`, `plan.md:26,87`까지 동일 오류가 전파되어 있다. |
| Testability | 0.65 | 0.50~0.75 사이 | 강점: 26개 AC 중 13개가 명시적 "판별 mutation"을 동반하며, 검증 결과 실제로 판별력이 있다(AC-001/002/003/005/007/011/012/102-103/104/105/201/202/301). 특히 `acceptance.md:172` AC-LCONF-301의 대조군 3개 상태 설계는 "빈 튜플 과잉 구현"까지 잡아내는 모범 사례다. 감점: D4(인증 가드 AC 부재), D5(REQ-006이 5개 상태를 규정하나 1개만 검증), D7(Edge Case 4건에 ID 미부여 — AC-203이 그중 하나에 의존). |
| Traceability | 0.65 | 0.50~0.75 사이 | 고아 AC 0건 — 26개 AC 전부 실재하는 REQ로 매핑된다. 그러나 `spec.md:45` **REQ-LCONF-001의 인증 절이 완전 미커버**이고, REQ-LCONF-006(5개 상태 중 1개), REQ-LCONF-203(excel_utils 2함수 미검증), REQ-LCONF-303(3개 경로 중 1개)이 부분 커버에 그친다. |

---

## Citation Verification (별도 검증)

`file:line` 인용은 **총 87건을 코드베이스에 대조**했다. 결론: **인용 정확도는 예외적으로 높다** — 아래 D8/D9를 제외한 전건이 실제 코드에 정확히 해소된다. 대표 표본:

| 인용 | 검증 결과 |
|------|-----------|
| `purchase_order_views.py:357-359` rule_map 빌드 | 정확 일치 (3줄 정확) |
| `purchase_order_views.py:387` `"auto_distributor": rule_map.get(...)` | 정확 일치 |
| `purchase_order_views.py:371-375` net_qty 계산 + zero-skip | 정확 일치 |
| `purchase_order_views.py:108-111` `_reorder_candidate_filter` 본체 | 정확 일치 |
| `purchase_order_views.py:1088-1089` distributor 공백 검사 | 정확 일치 |
| `purchase_order_views.py:1153` `status="pending"` | 정확 일치 |
| `purchase_order_views.py:2023/:2025-2029/:2030` | 3건 모두 정확 일치 |
| `purchase_order_views.py:4379` `li_qty = row["quantity"] or 0` | 정확 일치 (damaged_quantity 미반영 주장 입증) |
| `purchase_order_views.py:2507` `{"error": "Not found"}` | 정확 일치 |
| `models.py:339-345/:352/:354/:355/:356/:359` | 6건 모두 정확 일치 (max_length=20 확인) |
| `urls.py:88/:92-96/:103-107/:114-118` | 4건 모두 정확 일치 |
| `UnorderedItemsTab.tsx:426/:433/:442/:449/:463-471/:472` | 6건 모두 정확 일치 |
| `purchaseOrderApi.ts:5-14/:12/:16-20/:21-29/:36-50/:58-65/:130-133` | 7건 모두 정확 일치 |
| `usePurchaseOrderQueries.ts:27-35/:28/:31/:32-33/:116-132/:182` | 6건 모두 정확 일치 |
| MX 태그 인벤토리 ANCHOR 5개 / WARN 7개 | 정확 (주석 내 언급과 실제 태그를 올바르게 구분) |
| `mx.yaml` anchor_per_file:3 / warn_per_file:5 / note_per_file:10 | 정확 일치 (:175-177) |
| `acceptance.md:147` 테이블명 `orders_distributorvendorrule` | **정확** (models.py:528 `db_table` 확인 — 앱 라벨 `order`와 다른 접두사를 올바로 파악) |
| `test_spec_016.py` 동시성 테스트 구조 | 실재 확인 (:1030-1055, threading.Thread 2개) |
| `excel_utils.py` `auto_select_distributor`/`resolve_publisher_distributor` | 실재 확인 (:543, :505) |

주: 이는 프로젝트 메모리 `feedback_docs_sync_verification`("존재하지 않는 파일 경로 조작 사례 2건, plan-auditor가 잡지 못함")에 대한 실질적 개선이다. 인용 조작은 **1건도 발견되지 않았다.**

---

## Defects Found

### D1. `research.md:92` / `plan.md:26,87` / `spec-compact.md:30` — 기존 쿼리 수 핀(pin) 파손 미인지 — Severity: **critical**

REQ-LCONF-201(`spec.md:80`)이 `rule_map` 쿼리를 제거하면 `GET /api/purchase-orders/unordered/`의 쿼리 수가 1 감소한다(`research.md:24`가 직접 그렇게 단언). 그런데 **`backend/order/tests/test_spec_018.py:64`에 `UNORDERED_ENDPOINT_QUERY_COUNT = 3`이 절대값으로 고정되어 있고, `:542-543`에서 두 번 단정된다**:

```
assert queries_without_excluded == UNORDERED_ENDPOINT_QUERY_COUNT
assert queries_with_excluded == UNORDERED_ENDPOINT_QUERY_COUNT
```

해당 상수의 주석(`test_spec_018.py:59-63`)은 그 3이 "JWT 사용자 조회 1 + 이 뷰가 SPEC-ORDER-018 이전부터 발행하던 2"임을 명시하고, `:537-540`은 **"To re-derive after an intentional change, temporarily assert a wrong value and read the reported count"**라며 이번과 같은 의도적 변경을 정확히 예견해 두었다. 즉 이 테스트는 REQ-LCONF-201에 의해 **반드시 실패한다.**

그럼에도 `research.md:92`의 test_spec_018.py 영향 범위는 `:57, :183, :439, :474` 4곳으로만 열거되어 `:64`/`:542`/`:543`을 포함하지 않으며, `plan.md:26`의 M2 작업 지시와 `plan.md:87` 파일 목록, `spec-compact.md:30`도 동일하게 "4곳"으로 기술한다.

가중 요인: `plan.md:58` 리스크 R-C는 "정확한 절대값(베이스라인)은 이 Plan 단계에서 추정하지 않는다 … Run 단계에서 `CaptureQueriesContext`로 직접 재측정한 뒤 `test_spec_025.py`에 상수로 고정한다"라고 서술한다. **베이스라인은 이미 `test_spec_018.py:64`에 권위 있게 존재하며(3), `research.md:24`가 델타를 −1로 확정했으므로 신규 값 2는 지금 도출 가능하다.** Plan은 알려진 사실을 미지로 취급하면서, 동시에 그 사실이 기존 테스트를 깨뜨린다는 점을 놓쳤다.

### D2. `research.md:92` — `EXCLUDED_STATUSES` 참조 개수 오측 (4곳 주장 / 실제 7곳) — Severity: **major**

`research.md:92`는 "`other_publisher`/`EXCLUDED_STATUSES` 참조 **4곳**: `:57`, `:183`, `:439`, `:474`"라고 **실측이라 명시**한다. 실제 `grep -n "other_publisher\|EXCLUDED_STATUSES" backend/order/tests/test_spec_018.py` 결과는 **7곳**이다: `:57, :183, :320, :439, :474, :516, :550`.

누락된 3곳은 하필 가장 파손되기 쉬운 지점이다:

- `test_spec_018.py:320` — `purchase_status=EXCLUDED_STATUSES[line_no % 4]`
- `test_spec_018.py:516` — `purchase_status=EXCLUDED_STATUSES[idx % 4]`
- `test_spec_018.py:550` — `for status in EXCLUDED_STATUSES:` (SQL 문자열에 제외 상태가 나타나지 않음을 단정하는 루프)

`plan.md:26`의 지시대로 `:57`의 튜플을 3개로 축소하면 `:320`/`:516`의 `% 4` 모듈러 인덱싱은 `EXCLUDED_STATUSES[3]`을 요구하게 되어 **`IndexError`로 하드 크래시**한다. `:550`은 크래시 없이 조용히 `other_publisher` 절의 검증 커버리지를 상실한다. 어느 쪽 수정 방향을 택하든 4곳 열거는 불충분하다.

### D3. `research.md:90-95` / `plan.md:82-95` — `test_purchase_orders.py` 영향 완전 누락 — Severity: **major**

`research.md` §3의 제목은 "영향받는 테스트 (실측)"이나, REQ-LCONF-201에 의해 확실히 실패할 다음 두 테스트가 목록·`plan.md` 파일 목록 표·`spec-compact.md:30-31` 어디에도 없다:

- `backend/order/tests/test_purchase_orders.py:300-313` `test_auto_distributor_from_vendor_rule` → `assert result["auto_distributor"] == "choeumgoyuk"` (:313)
- `backend/order/tests/test_purchase_orders.py:315-325` `test_auto_distributor_null_when_no_rule` → `assert result["auto_distributor"] is None` (:325)

키 자체가 사라지므로(AC-LCONF-201이 `"auto_distributor" not in results[i]`를 요구) 두 단정은 `KeyError`로 실패한다. 파일 헤더 주석 `test_purchase_orders.py:5`("SC-PO-001 unordered aggregation + auto_distributor")도 무효화된다.

`acceptance.md:202`의 품질 게이트가 "전체 스위트 무손실"을 요구하므로 Run 단계에서 결국 드러나지만, **계획에 대응 작업이 없다는 점이 위험**하다 — 계획에 없는 실패에 직면한 구현 에이전트는 테스트를 삭제하는 방향으로 해소할 유인이 생긴다.

### D4. `spec.md:45` REQ-LCONF-001 — 인증 가드에 판별력 있는 AC 부재 — Severity: **major**

REQ-LCONF-001은 신규 엔드포인트가 "JWT 인증(`IsAuthenticated`)을 요구한다"고 규정하나, `acceptance.md`의 AC-LCONF-001~013 **전부가 인증된 클라이언트를 전제**하며 미인증 요청을 보내는 AC가 없다.

판별 mutation: `LineItemConfirmView`에서 `permission_classes = [IsAuthenticated]`(및/또는 `authentication_classes`)를 삭제한다 → **13개 R1 AC 전부가 그대로 통과한다.** 신규 *쓰기* 엔드포인트의 인증 통제가 판별력 0으로 남는다.

선례 부재로 인한 누락이 아니다: 자매 SPEC의 `test_spec_018.py:12`는 "T5 AC-RESTORE-005 REQ-RESTORE-008 unauthenticated -> 401, no leakage"를 명시하고, `:86` `anon_client` 픽스처와 `:408` `assert res.status_code == 401`을 이미 갖추고 있다. 읽기 전용 엔드포인트에 적용한 기준을 쓰기 엔드포인트에 적용하지 않았다.

### D5. `spec.md:50` REQ-LCONF-006 / `acceptance.md:30-35` AC-LCONF-004 — 부적격 상태 5종 중 1종만 검증 — Severity: **major**

REQ-LCONF-006은 부적격 상태를 `on_hold`/`order_cancelled`/`cs_required`/`other_publisher`/`in_stock` **5종으로 열거**하나, AC-LCONF-004는 `on_hold` 1종만 검증한다.

판별 mutation: 자격 검사를 단일값 블랙리스트로 구현한다 — `if li.purchase_status == "on_hold": raise ConflictError`. → AC-LCONF-004는 **통과**하지만 `order_cancelled`/`cs_required`/`other_publisher`/`in_stock` 행에 대해 `PurchaseOrder`가 잘못 생성된다. AC-LCONF-004의 "판별 mutation" 주석(`acceptance.md:35`)은 "미연결만 확인하는 구현"만 상정할 뿐 이 편향을 잡지 못한다.

특히 `other_publisher`가 위험하다 — R4(REQ-LCONF-302)가 해당 행을 보류/제외 뷰에서 감추므로, 이 가드는 잘못된 발주처리를 막는 유일한 방어선이 된다.

권고: AC-LCONF-301이 대조군 3종을 병렬 배치해 "빈 튜플 과잉 구현"을 잡아낸 것과 동일한 설계를 적용해, 5개 상태를 parametrize로 일괄 검증할 것.

### D6. `plan.md:20` vs `acceptance.md:92-94` — REQ-LCONF-015 검증 방법 상호 모순 — Severity: **major**

동일 요구사항에 대해 두 문서가 상충하는 검증 전략을 지시한다:

- `acceptance.md:92-94` AC-LCONF-013: "`order.purchase_order_views._recompute_order_aggregates`를 `unittest.mock.patch`로 스파이한 상태에서 … 스파이가 정확히 1회 호출되며"
- `plan.md:20` M1: "`_recompute_order_aggregates` 호출 확인(주문의 `status`/`ready_to_ship` 변화로 **간접 검증**)"

`plan.md` 쪽 방법은 판별력이 없다. `_recompute_order_aggregates`는 `logistics_status` 기반 집계를 계산하는데(`purchase_order_views.py:124-130` 독스트링), 발주처리 쓰기는 `logistics_status`를 변경하지 않는다 — 따라서 단일 LineItem 픽스처에서는 **호출 여부와 무관하게 집계값이 동일**하고, 호출을 누락한 구현도 통과한다.

`plan.md:7`은 "충돌하면 `spec.md`가 우선"이라 규정하나 이 충돌은 plan.md ↔ acceptance.md 간이라 해소 규칙이 적용되지 않는다. 구현 에이전트가 읽는 문서는 `plan.md`다.

### D7. `acceptance.md:188-193` — Edge Case 4건에 AC ID 미부여, 추적 불가 — Severity: **minor**

Edge Cases 섹션의 4개 항목이 번호 없는 산문으로만 존재한다: 열 수 8 불변, 발주처리 버튼 `stopPropagation`, damaged_exchange 모달 초기 표시 수량, distributor 20자 경계값.

`acceptance.md:210` Definition of Done 1항은 "REQ-LCONF-001~015(R1), 101~106(R2), 201~203(R3), 301~303(R4) 전항이 **대응하는 AC**를 통과한다"로만 정의되므로, ID 없는 Edge Case는 DoD 판정에서 누락될 수 있다.

실질적 영향 2건:
- **20자 경계값 누락 시**: mutation `if len(dist) >= 20: return 400`이 AC-LCONF-007(21자)을 통과하면서 정상 20자 입력을 오거부한다.
- **열 수 8 검증 누락 시**: `acceptance.md:155` AC-LCONF-203의 판별 mutation 주석이 "열 수(8) 검증 AC(아래 edge case)에서 잡힌다"라며 **ID 없는 항목에 명시적으로 의존**한다 — 그 항목이 구현되지 않으면 AC-203은 헤더 텍스트만 바꾼 구현을 잡지 못한다.

### D8. `research.md:69` — MX ANCHOR `:4005`의 귀속 대상 오기 — Severity: **minor**

`research.md:69`는 `purchase_order_views.py:4005`의 ANCHOR를 "`OutboundForceProcessView`의 불변 계약"으로 기술한다. 실제로 `:4005`의 태그는 그 아래 `_process_force_outbound_rows`(def `:4021`)에 부착되어 있으며, `OutboundForceProcessView` 클래스는 `:4199`에 있다. 줄 번호는 실재 ANCHOR로 정확히 해소되므로 인용 조작은 아니고 귀속 라벨만 틀렸다. ANCHOR 총계 5개와 "신규 ANCHOR 미추가" 결론에는 영향 없음.

### D9. `research.md:11,81,82` — 프론트엔드 3개 파일 총 줄 수 +1 일괄 오기 — Severity: **minor**

- `UnorderedItemsTab.tsx` 512줄 주장 → 실제 **511**줄
- `purchaseOrderApi.ts` 369줄 주장 → 실제 **368**줄
- `usePurchaseOrderQueries.ts` 257줄 주장 → 실제 **256**줄

3파일 모두 정확히 +1이며 세 파일 다 정상 개행(`0a`)으로 끝난다. 해당 파일들에 대한 **개별 줄 번호 인용은 전건 정확**하므로(:426, :433, :442, :449, :463-471, :472, :5-14, :12, :27-35, :116-132, :182 등 검증 완료) 실무 영향은 없으나, "실측" 주장의 신뢰도를 떨어뜨린다.

### D10. `spec.md` 전체 — 변경으로 무효화되는 독스트링이 변경 목록에 없음 — Severity: **minor**

- `purchase_order_views.py:327` — `UnorderedItemsView` 독스트링 "Each result includes auto_distributor derived from DistributorVendorRule." → REQ-LCONF-201 적용 시 거짓
- `purchase_order_views.py:417-418` — `ExcludedItemsView` 독스트링 "purchase_status is one of the **four** excluded states" → REQ-LCONF-301 적용 시 거짓

`plan.md:84` 파일 목록은 `purchase_order_views.py`를 MODIFY로 잡고 있으나 비고란("`LineItemConfirmView` 신설, `UnorderedItemsView.get()` 축소, `EXCLUDED_PURCHASE_STATUSES` 축소")에 독스트링 갱신이 없다.

### D11. `spec.md:82` REQ-LCONF-203 — 회귀 무변경 주장의 검증 범위 미달 — Severity: **minor**

REQ-LCONF-203은 `auto_select_distributor`/`resolve_publisher_distributor`(`excel_utils.py:543`/`:505`, 실재 확인)와 `DistributorVendorRule` CRUD가 무변경임을 규정하나, 대응 AC-LCONF-204(`acceptance.md:157-161`)는 `VendorRulesTab.tsx`/`DistributorVendorRuleListCreateView` 테스트 스위트만 재실행 대상으로 지정한다.

두 함수를 실제로 커버하는 전용 스위트 `backend/order/tests/test_auto_dist.py`(약 40개 호출 지점)와 `test_spec_024.py`가 회귀 대상으로 명시되지 않았다.

### D12. `spec.md:92` REQ-LCONF-303 — 3개 대체 경로 중 1개만 검증 — Severity: **minor**

REQ-LCONF-303은 `other_publisher` 행이 ① 주문상세 화면, ② 품목 노트 타출판사 탭, ③ Daily Review 업로드/다운로드 경로로 계속 조회 가능함을 규정한다. AC-LCONF-302(`acceptance.md:174-178`)는 ①(`OrderDetailView`, `backend/order/views.py:39` 실재 확인)만 검증한다. R4가 이 상태의 주요 노출 경로를 제거하는 변경이므로, 잔여 경로 검증은 "감춘 것이 사라진 것은 아니다"를 보증하는 핵심이다.

### D13. `research.md:48` / `plan.md:57` — spec.md 기재 약속 미이행 — Severity: **major**

`research.md:48`은 명시적으로 약속한다: "이 SPEC은 이 괴리를 고치지 않는다(범위 밖) — **spec.md에 알려진 제약으로 기록한다**." `plan.md:57` 리스크 R-B도 동일 취지를 반복한다.

**`spec.md`에는 해당 기재가 존재하지 않는다.** `grep -n "attach_net_quantity\|net_quantity\|제약\|괴리" .moai/specs/SPEC-ORDER-025/spec.md` → **매치 0건** (exit 1).

기재 대상이었던 제약은 사용자 가시적 데이터 불일치다: `damaged_exchange` 행에서 REQ-LCONF-003이 `PurchaseOrder.quantity`에 `damaged_quantity` 기반 순수량(예: 3)을 쓰는 반면, `_attach_net_quantity`(`purchase_order_views.py:4379` `li_qty = row["quantity"] or 0`으로 검증됨)는 발주서 목록의 `net_quantity`를 항상 원본 `LineItem.quantity`(예: 10)로 재계산한다. 담당자는 같은 발주서를 화면에 따라 3과 10으로 보게 된다.

`plan.md:74`의 mx_plan이 `@MX:NOTE` 항목 (c)로 코드 주석에 남기도록 계획하고 있어 부분 완화되나, `plan.md:7`이 "규범 진술의 단일 출처는 `spec.md`"라고 선언한 이상 규범 문서에 없는 제약은 승인 대상에서 제외된 것과 같다.

---

## Chain-of-Verification Pass

1차 감사 후 2차 자기비판을 수행했다. 재확인 항목과 결과:

**"모든 REQ를 실제로 읽었는가, 앞부분만 훑고 넘어가지 않았는가?"**
27개 REQ 전항을 개별 검토했다. 2차 패스에서 **D5(REQ-LCONF-006의 5개 상태 중 1개만 AC 존재)를 신규 발견** — 1차에서는 AC-LCONF-004의 존재만 확인하고 커버 완료로 처리했으나, REQ 본문의 괄호 열거를 다시 읽고 범위 불일치를 포착했다.

**"REQ 번호 연속성을 끝까지 확인했는가, 표본만 봤는가?"**
`grep -o | sort | uniq -c`로 27건 전수 검증(표본 아님). 중복 0, 블록 내 갭 0.

**"모든 REQ의 추적성을 확인했는가?"**
27개 REQ × AC 전수 매핑표를 작성했다. 2차 패스에서 **D4(REQ-LCONF-001 인증 절 미커버)를 신규 발견** — 1차에서는 AC-LCONF-001이 엔드포인트를 호출하므로 REQ-001이 커버된다고 처리했으나, REQ 본문이 엔드포인트 제공과 **인증 요구**라는 두 절을 담고 있고 후자에 대응 AC가 없음을 확인했다.

**"Exclusions를 존재 여부만 보지 않고 구체성까지 봤는가?"**
`spec.md:98-102` 5개 항목 전부 검토. 전항이 구체적 심볼명(`WarehouseStock`, `ConfirmOrderView`, `UploadDailyReviewView`, `DistributorVendorRule`)과 경계 근거를 포함 — 모호 항목 0건. 이 섹션은 **감사 통과이며 이 SPEC의 강점**이다.

**"요구사항 간 모순을 찾았는가, 개별 요구사항 내부만 봤는가?"**
문서 간 교차 대조에서 **D6(plan.md ↔ acceptance.md의 REQ-LCONF-015 검증 방법 상충)과 D13(research.md/plan.md가 약속한 spec.md 기재의 부재)을 신규 발견**. REQ-LCONF-005 vs 006의 409 중첩은 `plan.md:16`이 "메시지만 다르게, 상태 코드는 동일"로 의도적 설계임을 명시하므로 모순 아님으로 판정.

**"인용 검증을 표본으로 끝내지 않았는가?"**
87건 전수 대조. 2차 패스에서 `acceptance.md:147`의 테이블명을 별도 재검증했다 — 앱 라벨이 `order`(`apps.py`)이므로 Django 기본 규칙상 `order_distributorvendorrule`이 되어야 하나, `models.py:528`에 `db_table = "orders_distributorvendorrule"`이 명시되어 있어 **AC의 표기가 정확함**을 확인했다(1차에서는 오류로 의심했던 항목을 2차에서 무혐의 처리).

**신규 발견 요약**: 2차 패스에서 D4, D5, D6, D13 총 4건을 추가 발견했으며 이 중 3건이 major다. 1차 감사만으로는 불충분했다.

---

## Regression Check

해당 없음 — iteration 1. `.moai/reports/plan-audit/`에 SPEC-ORDER-025 선행 리뷰 보고서가 존재하지 않음을 확인했다.

---

## Recommendation

FAIL. 아래 순서로 수정 후 iteration 2를 요청할 것. 1~6번은 차단 항목이다.

1. **[D1 critical] `test_spec_018.py:64` 쿼리 핀을 영향 범위에 편입하라.**
   `research.md:92`와 `plan.md:26`·`plan.md:87`·`spec-compact.md:30`에 `test_spec_018.py:64`(`UNORDERED_ENDPOINT_QUERY_COUNT = 3`)와 `:542-543` 단정을 추가하고, 신규 값을 **2로 명시**하라(`research.md:24`가 델타를 −1로 확정했으므로 지금 도출 가능). `plan.md:58` R-C의 "Run 단계에서 재측정" 서술은 "기존 핀 3 → 2로 갱신하고 Run에서 실측 확인"으로 정정하라. 대응하는 AC(예: AC-LCONF-205 "GET /unordered/ 쿼리 수는 정확히 2다")를 `acceptance.md`에 추가할 것 — 판별 mutation: rule_map 조회를 남긴 구현은 3이 되어 실패.

2. **[D2 major] `EXCLUDED_STATUSES` 참조를 4곳에서 7곳으로 정정하라.**
   `research.md:92`를 `:57, :183, :320, :439, :474, :516, :550`으로 수정하고, `plan.md:26`·`plan.md:87`도 동일 갱신하라. `:320`/`:516`의 `% 4` 모듈러 인덱싱은 튜플 축소 시 `IndexError`를 일으키므로 `% len(EXCLUDED_STATUSES)`로 바꾸는 등의 구체적 조치를 M2 작업 항목에 명시할 것.

3. **[D3 major] `test_purchase_orders.py`를 영향 파일 목록에 추가하라.**
   `plan.md:82-95` 표에 `backend/order/tests/test_purchase_orders.py`(MODIFY, 비고: `:300-313`/`:315-325` auto_distributor 테스트 2건 제거 또는 재작성, `:5` 헤더 주석 갱신)를 추가하고, `research.md` §3과 `spec-compact.md:30`도 동기화하라.

4. **[D4 major] 인증 가드 AC를 신설하라.**
   AC-LCONF-014(신규): Given 미인증 클라이언트, When `POST /api/purchase-orders/line-items/<pk>/confirm/`, Then HTTP 401이며 `PurchaseOrder`가 생성되지 않는다. 판별 mutation: `permission_classes = [IsAuthenticated]` 제거 → 201이 되어 실패. `test_spec_018.py:86`의 `anon_client` 픽스처와 `:408` 단정 패턴을 재사용할 것.

5. **[D5 major] REQ-LCONF-006의 부적격 상태 5종을 전수 검증하도록 AC-LCONF-004를 확장하라.**
   `on_hold`/`order_cancelled`/`cs_required`/`other_publisher`/`in_stock` 5종 parametrize. 판별 mutation을 "단일값 블랙리스트 구현(`if purchase_status == "on_hold"`)"으로 명시할 것 — 현재 문구는 이 편향을 잡지 못한다.

6. **[D6 major] `plan.md:20`의 "간접 검증"을 삭제하고 `acceptance.md:92-94`의 스파이 방식으로 일원화하라.**
   간접 검증은 판별력이 없다(`_recompute_order_aggregates`는 `logistics_status` 집계를 다루며 발주처리 쓰기가 이를 변경하지 않으므로, 호출 누락 구현도 통과한다).

7. **[D13 major] `spec.md`에 "알려진 제약" 섹션을 신설하고 `_attach_net_quantity` 표시값 괴리를 기재하라.**
   `research.md:48`과 `plan.md:57`이 명시적으로 약속한 항목이다. `damaged_exchange` 행에서 `PurchaseOrder.quantity`(damaged_quantity 기반)와 발주서 목록 `net_quantity`(원본 quantity 기반, `purchase_order_views.py:4379`)가 다르게 표시된다는 사실을 규범 문서에 남길 것.

8. **[D7 minor] Edge Case 4건에 AC ID를 부여하라.**
   특히 20자 경계값(AC-LCONF-015 등)과 열 수 8 검증(AC-LCONF-205 등)은 필수 — `acceptance.md:155`가 후자에 명시적으로 의존한다.

9. **[D2 MP-2 연동 / minor] EARS 패턴 표기를 정정하라.**
   `spec.md:82` REQ-LCONF-203의 `(Unwanted)` → `(Ubiquitous)`로 변경하고 "THE 시스템은 … 변경하지 않는다" 형태로 재작성. `spec.md:80,81,90,91`(REQ-201/202/301/302)에 "THE 시스템은" 주어를 보완할 것.

10. **[D8/D9/D10/D11/D12 minor] 잔여 정정.**
    `research.md:69` ANCHOR `:4005` 귀속을 `_process_force_outbound_rows`로 수정. `research.md:11,81,82` 줄 수를 511/368/256으로 수정. `plan.md:84` 비고에 독스트링 2곳(`purchase_order_views.py:327`, `:417-418`) 갱신 추가. AC-LCONF-204 회귀 범위에 `test_auto_dist.py`·`test_spec_024.py` 추가. AC-LCONF-302에 품목 노트 타출판사 탭·Daily Review 경로 검증 추가.

**인정할 점**: 이 SPEC의 인용 정확도(87건 전수 대조에서 조작 0건)와 Exclusions 구체성, 그리고 AC에 판별 mutation을 병기하는 방식(특히 AC-LCONF-301의 대조군 설계, AC-LCONF-102/103의 양방향 판별)은 프로젝트 기준을 충족하는 모범 사례다. 본 FAIL은 문서 품질 전반이 아니라 **영향도 분석의 3건 누락(D1/D2/D3)과 판별력 공백 3건(D4/D5/D6)**에 기인한다.

---

Verdict: FAIL
