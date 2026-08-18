# SPEC Review Report: SPEC-ORDER-025

Iteration: 2/3
Overall Score: 0.71

> Reasoning context ignored per M1 Context Isolation. 본 감사는 `.moai/specs/SPEC-ORDER-025/`의 문서 5종(spec.md v1.1.0, acceptance.md, plan.md, research.md, spec-compact.md)과 실제 코드베이스만을 근거로 수행했다. 작성자의 추론 과정·이전 초안·대화 이력은 참조하지 않았다. iteration 1 보고서는 **회귀 검증 목적으로만** 읽었으며, 그 판정을 그대로 승계하지 않고 13개 결함 전부를 코드에 재대조했다.

**감사 원칙(사용자 지시)**: HISTORY에 "해소했다"고 적힌 것은 근거가 아니다. 문서 본문이 실제로 바뀌었는지, 그리고 바뀐 내용이 **틀린 구현에서 실제로 실패하는지**를 코드로 검증했다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  `grep -n "^- \*\*REQ-LCONF-" spec.md` 결과 **정의 27건, 각 1회**(`spec.md:46-60` 001~015, `:68-73` 101~106, `:81-83` 201~203, `:91-93` 301~303). 중복 정의 0, 블록 내 갭 0, 제로 패딩 3자리 전항 일관. `grep -o | sort | uniq -c`가 보고한 출현 횟수 2~3회 항목(001/003/006/015/201/203)은 전부 동일 문서 내 상호참조이며 정의 중복이 아님을 개별 확인했다. AC 번호도 001~015 / 101~108 / 201~206 / 301~303으로 연속이며 갭 0.

- **[FAIL] MP-2 EARS format compliance**
  iteration 1의 5건 중 4건은 실제로 해소됐다 — `spec.md:83` REQ-LCONF-203의 `(Unwanted)`→`(Ubiquitous)` 오표기 정정 및 "THE 시스템은 … 변경하지 않는다" 재작성 확인, `:81`/`:82`/`:91`/`:92`(201/202/301/302)에 "THE 시스템은" 주어 보완 확인.

  그러나 **`spec.md:93` REQ-LCONF-303은 `(Ubiquitous)`로 선언되었으나 시스템 주어가 없다**:

  > `purchase_status="other_publisher"`인 LineItem은 이 SPEC 이후에도 … 계속 조회 가능하다 — 이 SPEC은 그 경로들을 변경하지 않는다.

  첫 절의 주어는 `LineItem`(데이터 객체), 둘째 절의 주어는 "이 SPEC"(문서)이다. `THE {system} shall {response}` 구조가 아니다. 이는 iteration 1이 201/202/301/302에 대해 "주어 누락"으로 FAIL 판정한 것과 **동일한 구조적 결함**이며, `spec.md:20` HISTORY의 정정 대상 목록("REQ-LCONF-201/202/203/301/302")에서 303만 빠져 있다. 사용자 지시("iteration 1과 동일 기준 적용")에 따라 동일 판정을 적용한다.

  1/27(3.7%)이며 명시적 패턴 오표기는 0건이므로 iteration 1(5건, 오표기 1건)보다 크게 개선됐으나, MP-2는 비보상적(non-compensatory) 기준이므로 FAIL이다. 수정 비용은 1줄이다.

- **[PASS] MP-3 YAML frontmatter validity**
  `spec.md:1-11` 6개 필수 필드 전항 존재·타입 적합: `id: SPEC-ORDER-025`(:2, SPEC-{DOMAIN}-{NUM} 패턴 일치), `version: 1.1.0`(:3, 1.0.0에서 정상 증가), `status: draft`(:4, 허용값), `created_at: 2026-08-17`(:5, ISO 8601), `priority: High`(:8), `labels: [order, purchase, purchase-status, distributor, frontend, backend]`(:10, array). iteration 1 대비 `updated: 2026-08-17`(:6)이 추가되어 개정 이력이 프론트매터에도 반영됐다.

- **[N/A] MP-4 Section 22 language neutrality**
  단일 스택(Django + React/TypeScript) SPEC이며 다국어 툴체인·LSP를 다루지 않는다. 16개 언어 열거 요건 비적용 — 자동 통과.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 | 규범 진술 대부분이 단일 해석만 허용하고, `plan.md:9`가 신설한 "규범=spec.md / 검증방법=acceptance.md" 이원 우선순위 규칙은 D6 재발을 구조적으로 차단한다(개선). 감점: `spec.md:93` REQ-LCONF-303이 **거짓 사실**을 규범으로 진술(ND2), `acceptance.md:237` AC-302c의 Given("…이전 시점을 가정하지 않고, … 확인한다")이 문법적으로 성립하지 않는 비문, `acceptance.md:218` AC-206의 판별 mutation 문장이 괄호 중첩으로 자기모순적. |
| Completeness | 0.75 | 0.75 | 필수 섹션 전항 존재. `spec.md:97-99` "알려진 제약" 절 신설로 D13 해소(내용을 `purchase_order_views.py:4379`/`:4333`에 대조해 정확 확인). Exclusions 5개 항목 전부 구체적 심볼명 포함(강점, 무변경). **영향도 분석은 이번에 독립 검증 결과 완전하다** — `EXCLUDED_PURCHASE_STATUSES` 전역 참조는 `purchase_order_views.py:405`(정의)/`:458`(유일 소비처)뿐이고, `excluded-items` 엔드포인트를 테스트하는 파일은 `test_spec_018.py` 단독임을 확인했다. 감점: ND2가 드러낸 제약(수동 설정된 other_publisher 행의 고아화)이 "알려진 제약"에 없고, ND5의 테스트 인프라 제약(concurrency 마커)이 어디에도 없다. |
| Testability | 0.60 | 0.50~0.75 사이 | 신규 AC 중 **AC-004a~e / AC-015 / AC-205 / AC-206은 판별력을 코드로 검증해 실재 확인**했다(아래 회귀 검증 참조). 그러나 3개 AC가 판별력 0 또는 오기된 판별 mutation을 갖는다 — AC-014(ND1, 명시된 mutation이 DRF 기본값에 막혀 실패하지 않음), AC-302b(Given 조작으로 항상 통과), AC-302c(무관한 스위트 재실행일 뿐 주장 대상을 검증 못 함). 추가로 AC-012는 프로젝트 기본 DB 엔진(SQLite)에서 no-op이 되는 구조인데 결정론적 대조 테스트가 없다(ND5). |
| Traceability | 0.75 | 0.75 | 27개 REQ 전항이 대응 AC를 가진다(iteration 1의 REQ-001 인증 절 / REQ-006 5종 / REQ-203 excel_utils / REQ-303 3경로 부분커버가 전부 해소). 감점: **AC-LCONF-107/108/206 3건이 대응 REQ 없이 규범 행위를 단정**한다(ND4) — 특히 AC-108의 "모달 표시 수량 == 서버 기록값"은 `acceptance.md:167`에만 존재하고 `spec.md`에 없어 `plan.md:9`의 단일출처 규칙과 충돌. REQ-LCONF-202의 타입 절(`UnorderedItem`에서 필드 제거)은 전용 AC 없이 `tsc -b` 게이트에만 의존. |

---

## Citation Verification (독립 재검증)

이번 iteration에서 **신규·변경된 인용을 중심으로 62건을 코드에 재대조**했다. 결론: **조작된 인용은 1건도 없다.** 아래 표는 D1~D13 해소 주장의 핵심 근거 인용만 발췌한 것이다.

| 인용 | 문서 위치 | 검증 결과 |
|------|-----------|-----------|
| `test_spec_018.py:64` `UNORDERED_ENDPOINT_QUERY_COUNT = 3` | research.md:112, plan.md:40, acceptance.md:208 | **정확 일치** |
| `test_spec_018.py:59-63` 주석("JWT user lookup (1) + the two this view issued before SPEC-ORDER-018") | research.md:119 | **정확 일치**(원문 대조 완료) |
| `test_spec_018.py:542-543` 2회 단정 | research.md:112, plan.md:41 | **정확 일치** |
| `test_spec_018.py:537-540` "temporarily assert a wrong value" | research.md:119 | **정확 일치** |
| `EXCLUDED_STATUSES` 참조 7곳 `:57,:183,:320,:439,:474,:516,:550` | research.md:100-106 | **독립 grep 결과와 완전 일치**(7곳, 누락·과잉 0) |
| `:320` `EXCLUDED_STATUSES[line_no % 4]` / `:516` `[idx % 4]` | research.md:102,105 | **정확 일치** — `IndexError` 주장 타당 |
| `test_purchase_orders.py:5` / `:300-313` / `:315-325` | research.md:127-129, plan.md:44-46 | **3건 정확 일치**(`:313` `== "choeumgoyuk"`, `:325` `is None` 확인) |
| `test_spec_018.py:86` `anon_client` / `:408` `assert res.status_code == 401` | acceptance.md:108,110 | **정확 일치** |
| `test_spec_018.py:502-508` JWT 웜업 패턴 | acceptance.md:209 | **정확 일치** |
| `purchase_order_views.py:323-328` UnorderedItemsView 독스트링 | plan.md:34, :106 | **정확** — 문제 문장은 `:327` |
| `purchase_order_views.py:405-410` EXCLUDED_PURCHASE_STATUSES | spec.md:91 대상, plan.md:35 | **정확 일치** |
| `purchase_order_views.py:4005` ANCHOR 귀속 → `_process_force_outbound_rows`(def `:4021`), `OutboundForceProcessView`는 `:4199` | research.md:69, plan.md:90 | **정확 일치** — D8 정정 확인 |
| MX 인벤토리 ANCHOR 5(`:14,:1049,:1365,:4005,:4345`) / WARN 7(`:638,:1045,:1468,:3046,:3146,:3318,:3989`) | research.md:69-70 | **전건 정확**(주석 내 언급 `:89,:120,:370`을 태그와 올바로 구분) |
| 프론트 3파일 줄 수 511 / 368 / 256 | research.md:11,81,82 | **`wc -l` 3건 모두 정확** — D9 해소 확인 |
| `models.py:528` `db_table = "orders_distributorvendorrule"` | acceptance.md:185 | **정확 일치** |
| `views.py:39` OrderDetailView / `views.py:489-502` LineItemNoteUnresolvedListView | acceptance.md:235-236 | **2건 정확 일치**(:502가 `get_queryset` 종료 괄호까지 정확) |
| `LineItemNotesPage.tsx:36` `note_type === '타출판사'` | acceptance.md:236 | **정확 일치** |
| `UnorderedItemsTab.tsx:426/:433/:442/:449/:463-471/:472` | plan.md:56, research.md:13-16 | **6건 모두 정확 일치**(`<th>` 8개 실측 확인) |
| `usePurchaseOrderQueries.ts:181-182` 무효화 2줄 | plan.md:51 | **정확 일치** |
| `purchase_order_views.py:4379` `li_qty = row["quantity"] or 0` | spec.md:99 | **정확 일치** — "알려진 제약" 근거 성립 |
| `excel_utils.py:543`/`:505` | spec.md:83 | **정확 일치** |
| `test_auto_dist.py` 두 함수 참조 40건 | acceptance.md:199, plan.md:120 | **정확**(grep 40, 라인·출현 수 동일) |
| `test_spec_024.py` DistributorVendorRule 참조 **11건** | acceptance.md:200, plan.md:120 | **오기 — 실제 10건**(ND3) |
| `purchase_order_views.py:414-421` = ExcludedItemsView 독스트링 | plan.md:35, :106 | **범위 오기 — 실제 `:414-427`**(대상 문장 `:418`은 범위 안, ND7) |
| `OrderDetailPage.tsx:13-22` DISTRIBUTOR_LABELS "8개 값 — 6개 발주처 + 창고 3" | research.md:83 | **산술 오기 — 8 ≠ 6+3**(실제 발주처 5 + 창고 3, `yes24` 부재, ND6) |

---

## Regression Check (iteration 1 결함 13건)

| ID | Sev | 판정 | 근거 |
|----|-----|------|------|
| D1 | critical | **RESOLVED** | `research.md:110-121`에 §3-2 신설, `plan.md:40` M2-4가 `:64` 상수를 3→2로 갱신 지시, `plan.md:78` R-C가 "베이스라인 미지" 서술을 취소선으로 철회, `spec-compact.md:35` 반영, `acceptance.md:206-211` AC-LCONF-205 신설. **신규 값 2의 타당성을 독립 검증**: `UnorderedItemsView`가 `:344` `.select_related("order")`를 쓰므로 행별 추가 쿼리가 없고, refund는 `:335-343` 서브쿼리로 본 쿼리에 포함되며, `_reorder_candidate_filter`는 `:110`에서 `.exclude()` NOT EXISTS 단일 쿼리다 → JWT 1 + 본 쿼리 1 = **2가 맞다**. AC-205의 판별 mutation(직렬화에서만 키 숨김 → 3 유지)도 실제로 실패한다. |
| D2 | major | **RESOLVED** | `research.md:96-106` 표가 7곳 전부 열거. 내 독립 grep과 완전 일치. `plan.md:36-42`가 3개 그룹으로 재구성하고 `% len(EXCLUDED_STATUSES)` 수정을 "필수"로 명시. `plan.md:109` 파일 목록·`spec-compact.md:30` 동기화. |
| D3 | major | **RESOLVED** | `research.md:123-131` §3-3 신설, `plan.md:43-46` M2 작업 항목 + `plan.md:110` 파일 목록에 `test_purchase_orders.py` MODIFY 추가, `acceptance.md:254` 품질 게이트 행 추가, `spec-compact.md:30` 반영. |
| D4 | major | **PARTIAL** | AC-LCONF-014(`acceptance.md:106-111`) 신설은 확인. 그러나 명시된 판별 mutation이 실제로는 실패하지 않는다 → **ND1**. |
| D5 | major | **RESOLVED** | `acceptance.md:32-44` AC-004a~e 표로 5종 parametrize, `plan.md:25` M1 필수 케이스 명시, `plan.md:82` R-G 리스크 신설, `acceptance.md:252` 품질 게이트에 "004는 a~e 5개 케이스" 반영. **판별력 검증**: 단일값 블랙리스트 구현은 004b~e 4건이 201을 반환해 실패하고, 올바른 화이트리스트 구현(`not in ("unordered","damaged_exchange")`)은 5건 전부 통과 → 판별력 실재. |
| D6 | major | **RESOLVED** | `plan.md:28`이 간접 검증 서술을 취소선 처리하고 mock-spy로 일원화, `acceptance.md:104`에 "주의(D6 해소)" 절 추가. 추가로 `plan.md:9`가 "검증 방법은 acceptance.md가 규범"이라는 메타 규칙을 신설해 동종 모순의 재발 경로를 차단했다 — 요구된 것 이상의 조치. |
| D7 | minor | **RESOLVED (부분 부작용)** | Edge Case 4건이 AC-014/015/107/108/206으로 승격(`acceptance.md:106,113,156,163,213`), DoD `:263`이 명시적으로 포함. `acceptance.md:193`이 AC-203→AC-206 의존을 정식 ID로 대체. 다만 승격된 AC 중 3건이 대응 REQ 없이 남았다 → **ND4**. |
| D8 | minor | **RESOLVED** | `research.md:69`가 `:4005` ANCHOR를 `_process_force_outbound_rows`로 재귀속하고 `OutboundForceProcessView`가 `:4199`의 별개 클래스임을 명시. `plan.md:90`도 동일 정정. 코드 대조 완료(def `:4021`, class `:4199`). |
| D9 | minor | **RESOLVED** | 511 / 368 / 256 — `wc -l` 3건 모두 일치. |
| D10 | minor | **RESOLVED** | `plan.md:34`(UnorderedItemsView 독스트링 문장 제거), `plan.md:35`(ExcludedItemsView "four"→"three"), `plan.md:106` 파일 목록 비고 반영. 대상 문장 2곳(`:327`, `:418`) 실재 확인. 범위 라벨 1건만 부정확(ND7). |
| D11 | minor | **RESOLVED** | `acceptance.md:195-204` AC-204가 `test_auto_dist.py`·`test_spec_024.py`를 회귀 대상으로 명시, `plan.md:120`도 동일. 참조 수 1건 오기(ND3). |
| D12 | minor | **UNRESOLVED — 악화** | AC-302a/b/c로 3분할됐으나 302b/302c가 주장 대상을 검증하지 못하며, 그 과정에서 REQ-LCONF-303의 사실 오류가 규범으로 고착됐다 → **ND2 (critical)**. |
| D13 | major | **RESOLVED** | `spec.md:97-99` "알려진 제약" 절 신설. 내용을 `purchase_order_views.py:4379`(`li_qty = row["quantity"] or 0`)와 `:4333` 독스트링에 대조해 사실 정확 확인. `plan.md:77` R-B가 spec.md 기재 완료를 참조하고, `plan.md:96` mx_plan (c)가 코드 NOTE를 그 절 참조로 단순화. DoD `:268`이 임의 삭제를 금지하는 조항까지 추가. |

**요약**: 13건 중 10건 완전 해소, 1건 부분 해소(D4), 1건 미해소·악화(D12), 1건 해소하며 부작용(D7). **정체(stagnation) 결함은 없다** — 3회 연속 동일하게 남은 결함이 없으므로 manager-spec은 실질적으로 진전했다.

---

## Defects Found

### ND1. `acceptance.md:111` — AC-LCONF-014의 판별 mutation이 실패하지 않는다 — Severity: **major**

AC-LCONF-014는 판별 mutation을 이렇게 명시한다:

> `LineItemConfirmView`에서 `permission_classes = [IsAuthenticated]`(및/또는 `authentication_classes`)를 제거 → 200/201이 되어 상태 코드 단정 실패.

**이 주장은 거짓이다.** `backend/config/settings/base.py:100-107`:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
```

뷰에서 `permission_classes`를 제거하면 DRF는 프로젝트 기본값 `IsAuthenticated`로 폴백하므로 익명 요청은 **여전히 401**이다. `authentication_classes`를 제거해도 기본값 `JWTAuthentication`으로 폴백한다. 즉 **명시된 mutation을 주입해도 AC-014는 통과한다.**

실질적 결과: 가장 개연성 높은 잘못된 구현 — 신규 뷰가 `authentication_classes`/`permission_classes` 선언을 아예 빠뜨리는 것 — 이 **탐지되지 않는다**. AC-014가 실제로 검증하는 것은 REQ-LCONF-001의 "이 뷰가 `IsAuthenticated`를 요구한다"가 아니라 "프로젝트 기본 설정이 살아 있다"이다. AC-014를 실제로 깨뜨리려면 `permission_classes = [AllowAny]`를 명시적으로 넣어야 하는데, 이는 아무도 실수로 하지 않는 변경이다.

부수적으로 `acceptance.md:111`의 후속 문장("이 AC가 없으면 AC-LCONF-001~013 전부가 인증된 클라이언트를 전제하므로 인증 삭제 mutation이 무엇에도 걸리지 않는다")도 같은 이유로 성립하지 않는다.

참고: 같은 URL 패밀리에 대한 더 나은 선례가 이미 있다 — `test_purchase_orders.py:2300-2304` `test_patch_unauthenticated_returns_401`(`PATCH .../line-items/<pk>/status/`, `anon_client`, 401). `test_spec_018.py:86/:408`(GET 엔드포인트)보다 그레인이 일치한다.

권고: 판별 mutation을 `permission_classes = [AllowAny]` 명시로 정정하고, 뷰 수준 선언 존재를 직접 단정하는 케이스(예: `LineItemConfirmView.permission_classes`에 `IsAuthenticated`가 포함됨을 정적으로 확인)를 AC에 추가하라 — 후자가 없으면 REQ-LCONF-001의 인증 절은 여전히 코드 리뷰에만 의존한다.

### ND2. `spec.md:93` REQ-LCONF-303 / `spec.md:30` / `acceptance.md:231-238` — 대체 경로 주장이 사실과 다르고, 그것을 "검증"하는 AC가 실패할 수 없다 — Severity: **critical**

REQ-LCONF-303은 `other_publisher` 행이 R4 이후에도 **3개 경로**로 조회 가능하다고 규범적으로 진술한다: ① 주문상세 화면, ② 품목 노트 타출판사 탭, ③ **Daily Review 업로드/다운로드 경로**. `spec.md:30`의 문제 정의도 같은 주장을 R4의 정당화 근거로 사용한다("타출판사 건은 별도 경로 … 로 이미 처리되는 흐름이라").

**경로 ③은 존재하지 않는다.** 코드 검증:

- `DailyReviewExcelView`(다운로드, `purchase_order_views.py:1237`)는 `:1260`에서 `_reorder_candidate_filter(LineItem.objects.filter(sku__isnull=False))`로 후보를 뽑는다.
- `UploadDailyReviewView`(업로드, `:1443`)는 `:1704-1707`에서 `_reorder_candidate_filter(LineItem.objects.filter(sku__in=all_skus, order_id__in=order_ids)).select_for_update()`로 매칭 대상을 뽑는다.
- `_reorder_candidate_filter`(`:94`, 본체 `:108-111`)는 `purchase_status="unordered"`(미연결) **또는** `"damaged_exchange"`만 통과시킨다.

따라서 `purchase_status="other_publisher"`인 행은 Daily Review 다운로드 엑셀에 **나타나지 않고**, 업로드 매칭에도 **걸리지 않는다**. Daily Review 업로드는 `other_publisher`를 **쓰는**(`excel_utils.py:660` `"타출판사": "other_publisher"`, `purchase_order_views.py:1792`) 경로이지 **읽는** 경로가 아니다. 이는 프로젝트 메모리 `project_daily_review_reupload_noop`("이미 처리된 행은 `_reorder_candidate_filter`에서 빠져 갱신 안 됨")과 정확히 일치한다.

**경로 ②도 조건부다.** 품목 노트 타출판사 탭은 `LineItemNote(note_type='타출판사', is_resolved=False)`를 보여줄 뿐(`views.py:489-502`, `LineItemNotesPage.tsx:36`) `purchase_status`와 무관하다. 노트는 Daily Review 업로드가 bulk_create로 만든다(`purchase_order_views.py:1712-1713`). 그런데 담당자는 **이 SPEC이 수정하는 바로 그 화면에서** `other_publisher`를 수동 설정할 수 있다 — `PURCHASE_STATUS_OPTIONS`에 `other_publisher`가 포함되어 있고(`purchaseOrderApi.ts:62`) `UnorderedItemsTab.tsx:472` 이하의 행별 select가 이를 렌더링하며, 그 PATCH를 받는 `LineItemStatusUpdateView.patch`(`purchase_order_views.py:2503-2532`)는 `purchase_status`만 저장하고 **노트를 생성하지 않는다**.

결합하면 R4 적용 후 다음 시나리오가 성립한다:

> 담당자가 미발주 현황에서 어느 행의 발주 상태를 "타출판사"로 바꾼다 → 미발주 목록에서 사라짐(unordered 아님) → **보류/제외 품목에서도 사라짐(R4)** → 노트가 없으므로 품목 노트 타출판사 탭에도 없음 → Daily Review 다운로드/업로드에도 없음 → **주문번호를 이미 알고 있어야만 주문상세에서 찾을 수 있음.**

REQ-LCONF-303은 이 시나리오가 불가능하다고 규범적으로 단언하고 있다.

**그리고 이를 검증한다는 AC들은 실패할 수 없게 설계돼 있다:**

- `acceptance.md:236` **AC-302b**의 Given이 "`note_type="타출판사"`인 미해결 `LineItemNote`가 그 LineItem에 달려 있다"로 **노트 존재를 픽스처로 주입**한다. 노트가 없는 경우(=위 시나리오)가 검증 범위에서 구조적으로 배제된다. 명시된 판별 mutation("노트 쿼리셋에 `purchase_status__in=EXCLUDED_PURCHASE_STATUSES` 배제 필터를 잘못 추가")은 아무도 하지 않을 변경이다 — `LineItemNoteUnresolvedListView`는 `purchase_status`를 참조조차 하지 않는다(`views.py:497-502`).
- `acceptance.md:237` **AC-302c**는 Given이 비문이고("…이전 시점을 가정하지 않고, … 확인한다"), Then이 "기존 스위트(`test_daily_review_upload.py`, `test_spec_024.py`)를 재실행해 무수정 전량 통과"다. 그 스위트들은 `other_publisher` 행의 **가시성**을 애초에 테스트하지 않으므로, 경로 ③이 존재하든 존재하지 않든 통과한다. **판별력 0.**

즉 iteration 1의 D12("3개 경로 중 1개만 검증")에 대한 대응이, 검증되지 않은 2개 경로를 "검증됨"으로 표시하는 형태로 이루어졌다. 이는 프로젝트 메모리 `feedback_acceptance_criteria_mutation_check`("통과하는 테스트 ≠ 검증된 구현")가 경고하는 정확한 실패 양식이며, 문서 신뢰도 측면에서 iteration 1보다 나쁘다.

권고(3택 1, 어느 쪽이든 `spec.md:30`의 정당화 문구도 함께 정정할 것):
1. REQ-LCONF-303에서 경로 ③을 삭제하고, 경로 ②가 "타출판사 노트가 있는 행에 한한다"는 조건을 명시한 뒤, **노트 없는 other_publisher 행이 보류/제외 뷰에서도 사라진다는 사실을 "알려진 제약"에 기재**하라(D13과 동일한 조치).
2. 또는 R4의 범위를 좁혀라 — 예: `other_publisher` 중 타출판사 노트가 연결된 행만 숨긴다.
3. 또는 사용자에게 "수동으로 타출판사 설정한 행은 어디서 관리하는가"를 확인한 뒤 결정하라(오케스트레이터 경유).

AC 측면에서는 AC-302c를 삭제하거나, "`other_publisher` LineItem이 Daily Review 다운로드 엑셀에 포함되지 않는다"는 **사실에 맞는** 단정으로 교체하라.

### ND3. `acceptance.md:200` / `plan.md:120` — `test_spec_024.py` 참조 수 오기(11건 주장 / 실제 10건) — Severity: **minor**

두 문서 모두 "`test_spec_024.py`(타출판사 확정 발주처/단가 로직, `DistributorVendorRule` 관련 참조 **11건**)"이라 기재한다. 실측:

```
grep -c "DistributorVendorRule" backend/order/tests/test_spec_024.py  → 10
grep -o "DistributorVendorRule" ... | wc -l                          → 10
```

해당 10곳은 `:13, :30, :89, :108, :129, :162, :186, :210, :228, :246`이다. 같은 문장 안의 `test_auto_dist.py` 40건은 정확하므로 단순 오기로 보이나, iteration 1의 D2(4곳 주장/7곳 실제)·D9(줄 수 +1)와 **동일 계열의 "실측" 주장 부정확**이다. 회귀 대상 파일 자체는 실재하므로 실무 영향은 없다.

### ND4. `acceptance.md:156,163,213` — AC-LCONF-107/108/206이 대응 REQ 없이 규범 행위를 단정 — Severity: **minor**

D7 해소로 Edge Case에 AC ID가 부여됐으나, 그중 3건은 `spec.md`에 근거 REQ가 없다:

- **AC-107**(발주처리 버튼 클릭이 행 선택을 트리거하지 않음) — REQ-LCONF-101은 "각 행은 발주처리 액션(버튼)을 제공한다"까지만 규정.
- **AC-108**(damaged_exchange 행 모달 초기 표시 수량 = 3) — REQ-LCONF-102는 모달이 "필요 수량"을 표시한다고만 하고, 그 값이 순수량이어야 한다는 규범은 `acceptance.md:167`("REQ-LCONF-003이 서버에 실제로 기록하는 값과 담당자가 모달에서 보는 값이 일치해야 한다")에만 존재한다.
- **AC-206**(열 수 8 불변) — REQ-LCONF-202는 "자동 추천 발주처 열을 렌더링하지 않는다"까지만 규정하고 총 열 수는 규정하지 않는다.

`plan.md:9`가 "규범 진술의 단일 출처는 `spec.md`"라고 선언한 이상, `acceptance.md`에만 있는 규범은 승인 대상에서 벗어난다 — iteration 1의 D13과 동일한 구조다. AC 3건에 대응하는 REQ(예: REQ-LCONF-107/108, REQ-LCONF-204)를 `spec.md`에 추가하는 것이 일관된 처리다.

### ND5. `acceptance.md:91-96` AC-LCONF-012 — 동시성 AC가 프로젝트 테스트 규약과 기본 DB 엔진을 고려하지 않음 — Severity: **major**

AC-012는 `test_spec_016.py`의 "동시성 테스트 구조 재사용"만 지시한다. 그러나 그 선례는 **두 개의 테스트**로 구성돼 있고, AC-012는 그중 취약한 쪽만 가져온다:

- `test_spec_016.py:1012-1027` `TestForceProcessLockingDeterministic.test_target_select_uses_for_update` — `CaptureQueriesContext`로 SQL에 `FOR UPDATE`가 실제로 나타나는지 단정한다. 독스트링이 목적을 명시한다: *"Fast, deterministic companion to the threaded test below: if the lock is ever accidentally removed, this fails immediately instead of relying on a possibly-flaky concurrency test."*
- `test_spec_016.py:1030-1031` `@pytest.mark.concurrency` + `@pytest.mark.django_db(transaction=True)` — 스레드 2개 + Barrier.

두 가지 누락이 있다:

1. **`concurrency` 마커 미기재.** `backend/pytest.ini`의 markers 절이 이 마커를 정식 정의하며 그 설명이 곧 규약이다: *"uses transaction=True + real threads against the shared remote test DB — do not run concurrently with other pytest processes; select with `-m concurrency`, deselect with `-m "not concurrency"`."* 프로젝트 메모리 `feedback_pytest_remote_db_concurrency`도 같은 제약을 기록한다. `acceptance.md:252`(`pytest backend/order/tests/test_spec_025.py --no-cov`)와 `:255`(`pytest backend/order --no-cov`) 어디에도 마커 처리가 없어, 신규 스레드 테스트가 일반 스위트 실행에 섞여 공유 리모트 DB에서 가짜 실패를 유발할 수 있다.
2. **결정론적 대조 테스트 부재.** `backend/config/settings/local.py:11`의 `DB_ENGINE` 기본값은 `django.db.backends.sqlite3`이며, SQLite에서 Django의 `select_for_update()`는 **무시된다**. 기본 설정으로 실행하면 AC-012의 판별 mutation(`select_for_update()` 제거)이 아무 차이를 만들지 않아 **판별력이 0이 된다.** 선례가 결정론적 companion을 둔 이유가 정확히 이것인데 AC-012는 그것을 채택하지 않았다.

결과적으로 REQ-LCONF-014(락 + 원자적 트랜잭션)는 실행 환경에 따라 검증되지 않을 수 있다. `acceptance.md:258` "Mutation 실측" 행이 AC-012를 포함하고 있어 구현 세션에서 드러날 여지는 있으나, 그 시점에는 이미 AC 설계를 되돌리는 비용이 발생한다.

권고: AC-012를 (a) `FOR UPDATE`가 캡처된 SQL에 존재함을 단정하는 결정론적 AC와 (b) `@pytest.mark.concurrency`를 명시한 스레드 AC로 분할하고, `acceptance.md`의 품질 게이트 명령을 `-m "not concurrency"` / `-m concurrency` 2행으로 나눠라.

### ND6. `research.md:83` — `DISTRIBUTOR_LABELS` 구성 오기, 신규 드롭다운 값 `yes24`의 라벨 부재를 은폐 — Severity: **minor**

`research.md:83`은 "`DISTRIBUTOR_LABELS`(`:13-22`, **8개 값 — 6개 발주처 + `warehouse_korea/ca/nj`**)"라 기재한다. 6+3=9이므로 자체 모순이다. 실제(`OrderDetailPage.tsx:13-22`)는 발주처 **5개**(booxen/kyobo/choeumgoyuk/agape/sungseoyunion) + 창고 3개 = 8이며, **`yes24`가 없다.**

이 오기가 실질적 문제를 가린다: `spec.md:37`의 확정 결정 D2가 신규 모달 드롭다운을 **6개 값(booxen/kyobo/`yes24`/choeumgoyuk/agape/sungseoyunion)**으로 규정하고, REQ-LCONF-002가 그 값을 `LineItem.confirmed_distributor`에 기록한다. 그런데 `OrderDetailPage.tsx:374`는 `DISTRIBUTOR_LABELS[item.confirmed_distributor] ?? item.confirmed_distributor`로 렌더링하므로, `yes24`로 발주처리한 행은 주문상세에서 한글 라벨 없이 원시 문자열 `yes24`로 표시된다(`UnorderedItemsTab.tsx:132`의 로컬 맵은 `yes24: 'YES24'`를 갖고 있어 화면마다 표기가 갈린다).

"9개 값 — 6개 발주처 + 창고 3"이 맞는 대상은 `purchase_order_views.py:77-78`의 `VALID_DISTRIBUTORS`이며(`research.md:30`은 이를 정확히 기술한다), 그 문구가 `:83`에 잘못 재사용된 것으로 보인다. 표시 라벨 보완을 이 SPEC 범위에 넣을지 여부는 별론으로, 최소한 사실 기재는 정정해야 한다.

### ND7. `plan.md:35` / `plan.md:106` — `ExcludedItemsView` 독스트링 범위 오기 — Severity: **minor(nit)**

두 곳 모두 "`ExcludedItemsView` 독스트링(`:414-421`)"이라 기재하나, 실제 독스트링은 `purchase_order_views.py:414-427`이다(`:427`이 닫는 `"""`). 갱신 대상 문장 "purchase_status is one of the **four** excluded states"는 `:418`로 인용 범위 안에 있으므로 작업 지시 자체는 유효하다. `UnorderedItemsView` 쪽 `:323-328`은 정확하다.

---

## Chain-of-Verification Pass

1차 감사 후 2차 자기비판을 수행했다.

**"iteration 1 결함 13건을 전부 문서에서 확인했는가, HISTORY 문구만 읽고 넘어가지 않았는가?"**
13건 전부에 대해 (a) 문서 본문의 변경 위치를 특정하고 (b) 그 내용을 코드에 대조했다. HISTORY(`spec.md:20`)는 근거로 채택하지 않았다. **2차 패스에서 D12의 미해소를 발견** — 1차 패스에서는 AC-302가 302a/b/c로 3분할된 것을 확인하고 "해소"로 처리했으나, 각 AC의 Given/Then을 실제 코드에 대입해보는 단계에서 302b의 Given 조작과 302c의 판별력 0을 포착했고, 거기서 역추적해 REQ-LCONF-303 자체의 사실 오류(ND2)에 도달했다.

**"모든 REQ를 읽었는가, EARS 정정을 표본만 봤는가?"**
27개 REQ 정의를 `grep -n "^- \*\*REQ-LCONF-"`로 전수 추출해 개별 검토했다. **2차 패스에서 REQ-LCONF-303의 주어 누락을 발견** — 1차 패스에서는 `spec.md:20` HISTORY가 열거한 5건(201/202/203/301/302)만 대조하고 "MP-2 해소"로 처리할 뻔했다. HISTORY의 목록 자체가 불완전할 수 있다는 가정을 세우고 전수 재검토한 것이 발견의 계기다.

**"판별 mutation을 문서 문구로만 읽지 않고 실제 코드에 대입했는가?"**
신규·변경 AC 9건(004a~e, 014, 015, 205, 206, 302a/b/c, 013)에 대해 mutation을 코드 경로에 대입해 결과를 추론했다. **2차 패스에서 ND1(AC-014)을 발견** — 1차 패스에서는 "401 AC가 생겼으니 D4 해소"로 처리했으나, mutation을 실제로 적용하려고 DRF 설정을 찾아본 결과 `backend/config/settings/base.py:105-107`의 프로젝트 기본값이 mutation을 무력화함을 확인했다. **iteration 1 보고서의 D4 서술 자체가 같은 오류를 담고 있었으며, SPEC은 그것을 검증 없이 그대로 옮겨 적었다.**

**"영향도 분석(D1/D2/D3 계열)이 이번엔 정말 완전한가, 문서가 열거한 것만 확인하지 않았는가?"**
문서와 무관하게 독립적으로 재스캔했다: `EXCLUDED_PURCHASE_STATUSES` 전역 참조(`purchase_order_views.py:405` 정의, `:458` 유일 소비처), `excluded-items` 엔드포인트 테스트 파일(`test_spec_018.py` 단독), 전 테스트의 `auto_distributor` 참조(`test_purchase_orders.py` 3곳뿐), 전 테스트의 `other_publisher` 참조(나머지는 상태값 자체에 대한 테스트로 이 SPEC 무관함을 개별 확인), 프론트 `auto_distributor` 참조(`UnorderedItemsTab.test.tsx:170,328,356` + `purchaseOrderApi.ts:12` + `UnorderedItemsTab.tsx:463-471`). **추가 누락은 발견되지 않았다** — 영향도 분석은 이번 iteration에서 실제로 완전해졌다.

**"Exclusions를 존재 여부만 보지 않고 구체성까지 봤는가?"**
`spec.md:103-107` 5개 항목 전부 재검토. 구체적 심볼명(`WarehouseStock`, `ConfirmOrderView`, `UploadDailyReviewView`, `DistributorVendorRule`)과 경계 근거 포함, 모호 항목 0건. iteration 1과 동일하게 이 SPEC의 강점이다.

**"요구사항 간·문서 간 모순을 찾았는가?"**
D6(plan ↔ acceptance)이 해소됐고 `plan.md:9`가 재발 방지 규칙을 세운 것을 확인했다. 새로 발견한 모순은 **문서 ↔ 코드** 층위다(ND2: REQ-LCONF-303 vs `_reorder_candidate_filter`, ND1: AC-014 vs DRF 기본 설정, ND6: research.md vs `OrderDetailPage.tsx`). 문서 상호 간 모순은 이번에 발견되지 않았다.

**"수치 주장('실측', 'N건')을 표본이 아니라 전수로 대조했는가?"**
문서에 등장하는 정량 주장 12건(7곳/40건/11건/8열/511/368/256/66/4468/194/ANCHOR 5/WARN 7)을 전부 명령으로 재측정했다. **2차 패스에서 ND3(11→10)과 ND6(8≠6+3)을 발견.**

**신규 발견 요약**: 2차 패스에서 ND1, ND2, ND3, ND6 총 4건을 추가 발견했으며 그중 ND2는 critical, ND1은 major다. 1차 패스만으로는 "13건 중 12건 해소, 사소한 EARS 1건 남음"이라는 관대한 결론에 도달했을 것이다.

---

## Recommendation

**FAIL.** 다만 iteration 1과 성격이 다르다 — 영향도 분석(D1/D2/D3)과 규범 문서 기재(D13), 검증 방법 모순(D6), 상태 커버리지(D5)는 **실질적으로 해소됐고 코드로 검증했다**. 이번 FAIL은 (a) 남은 EARS 1건과 (b) **D12 대응 과정에서 검증되지 않은 사실이 규범으로 고착된 것**에 기인한다.

iteration 3 진입 전 아래 순서로 수정할 것. 1~3번이 차단 항목이다.

1. **[ND2 critical] REQ-LCONF-303의 사실 오류를 정정하고, R4의 실제 사각지대를 "알려진 제약"에 기재하라.**
   - `spec.md:93`에서 "Daily Review 업로드/다운로드 경로"를 삭제하라 — `DailyReviewExcelView`(`purchase_order_views.py:1260`)와 `UploadDailyReviewView`(`:1704-1707`)가 모두 `_reorder_candidate_filter`(`:108-111`)를 통과시키므로 `other_publisher` 행은 이 경로에 애초에 나타나지 않는다.
   - `spec.md:93`의 경로 ②에 조건을 명시하라: "타출판사 노트(`LineItemNote(note_type='타출판사')`)가 연결된 행에 한한다."
   - `spec.md:30`의 문제 정의 3번(R4 정당화 근거)도 같은 취지로 정정하라.
   - `spec.md`의 "알려진 제약"에 신규 항목을 추가하라: **`LineItemStatusUpdateView`(`purchase_order_views.py:2503-2532`)로 수동 설정된 `other_publisher` 행은 노트가 생성되지 않으므로, R4 적용 후 주문상세 화면 외에는 조회 경로가 없다.** `other_publisher`는 `PURCHASE_STATUS_OPTIONS`(`purchaseOrderApi.ts:62`)에 포함되어 이 SPEC이 수정하는 바로 그 화면(`UnorderedItemsTab.tsx:472` 이하)에서 선택 가능하므로 도달 가능한 시나리오다.
   - `acceptance.md:237` **AC-302c를 삭제하거나** 사실에 맞는 단정으로 교체하라(예: "`purchase_status="other_publisher"`인 LineItem은 `GET /api/purchase-orders/daily-review-excel/` 결과에 포함되지 않는다" — 판별 mutation: `_reorder_candidate_filter`를 넓힌 구현 → 포함되어 실패).
   - `acceptance.md:236` **AC-302b의 Given에서 노트 존재 전제를 제거하거나**, 노트가 없는 대조군을 추가해 "노트 없는 other_publisher 행은 이 탭에 나타나지 않는다"를 명시적으로 문서화하라 — 현재 형태는 Given 조작으로 항상 통과한다.
   - 위 정정이 R4의 범위 자체를 재검토해야 할 수준이라 판단되면, 오케스트레이터를 경유해 사용자에게 "수동으로 타출판사 설정한 행의 관리 경로"를 확인할 것.

2. **[ND1 major] AC-LCONF-014의 판별 mutation을 정정하고 뷰 수준 선언을 직접 검증하라.**
   `backend/config/settings/base.py:105-107`이 `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`를 전역 설정하므로 `acceptance.md:111`이 명시한 mutation(`permission_classes` 제거)은 실패하지 않는다. mutation을 `permission_classes = [AllowAny]` 명시로 바꾸고, 별도로 `LineItemConfirmView.permission_classes`에 `IsAuthenticated`가 선언되어 있음을 단정하는 정적 케이스를 추가하라. 401 단정 자체는 유지할 것(`AllowAny` 회귀 방어). 선례는 `test_purchase_orders.py:2300-2304`(동일 URL 패밀리, `anon_client`, 401)가 `test_spec_018.py:86/:408`(GET)보다 그레인이 맞다.

3. **[MP-2 / ND-EARS] `spec.md:93` REQ-LCONF-303에 시스템 주어를 보완하라.**
   현재 주어는 `LineItem`(데이터 객체)과 "이 SPEC"(문서)이다. 형제 요구사항 REQ-LCONF-203(`spec.md:83`)이 이미 채택한 "THE 시스템은 … 하지 않는다" 형태로 재작성하라. 예: "THE 시스템은 `purchase_status="other_publisher"`인 LineItem을 주문상세 화면(`OrderDetailView`/`OrderDetailPage.tsx`)과 타출판사 노트가 연결된 경우의 품목 노트 타출판사 탭에서 계속 조회 가능하게 유지한다." (1번 정정과 동시에 처리할 것.)

4. **[ND5 major] AC-LCONF-012를 결정론적 AC + 마커 명시 동시성 AC로 분할하라.**
   (a) `CaptureQueriesContext`로 대상 LineItem 조회 SQL에 `FOR UPDATE`가 존재함을 단정하는 결정론적 AC를 신설하라 — `test_spec_016.py:1013-1027`이 바로 이 목적으로 존재하며, 그 독스트링이 "possibly-flaky concurrency test에 의존하지 말라"고 명시한다. `backend/config/settings/local.py:11`의 기본 엔진(SQLite)에서 `select_for_update()`는 무시되므로 스레드 테스트만으로는 판별력이 0이 될 수 있다.
   (b) 스레드 AC에 `@pytest.mark.concurrency` + `@pytest.mark.django_db(transaction=True)`를 명시하라(`test_spec_016.py:1030-1031` 선례, `backend/pytest.ini` markers 절이 규약을 정의).
   (c) `acceptance.md:252,255`의 품질 게이트 명령을 `-m "not concurrency"`와 `-m concurrency` 2행으로 분리하라.

5. **[ND4 minor] AC-LCONF-107/108/206에 대응하는 REQ를 `spec.md`에 추가하라.**
   `plan.md:9`가 "규범 진술의 단일 출처는 `spec.md`"라 선언한 이상, `acceptance.md:167`에만 있는 "모달 표시 수량 == 서버 기록값" 같은 규범은 승인 범위 밖이다(iteration 1 D13과 동일 구조). REQ-LCONF-107(버튼 클릭이 행 선택을 유발하지 않음), REQ-LCONF-108(모달 초기 표시 수량 = REQ-LCONF-003의 순수량), REQ-LCONF-204(미발주 테이블 열 수 8 불변) 신설을 권고한다. **주의: 신설 시 R2/R3 블록의 번호 연속성을 유지할 것**(현재 101~106, 201~203).

6. **[ND3/ND6/ND7 minor] 수치·범위 정정.**
   - `acceptance.md:200`·`plan.md:120`: `test_spec_024.py` DistributorVendorRule 참조 **11건 → 10건**(`:13,:30,:89,:108,:129,:162,:186,:210,:228,:246`).
   - `research.md:83`: "8개 값 — 6개 발주처 + warehouse_korea/ca/nj" → "**8개 값 — 발주처 5개(booxen/kyobo/choeumgoyuk/agape/sungseoyunion) + warehouse_korea/ca/nj**". 아울러 **`yes24`가 `DISTRIBUTOR_LABELS`에 없어 `OrderDetailPage.tsx:374`에서 원시 문자열로 표시된다**는 사실을 기록하고, 신규 모달 드롭다운(`spec.md:37` D2)이 `yes24`를 포함하는 이상 라벨 보완을 이 SPEC 범위에 넣을지 명시적으로 결정하라(범위 밖으로 두더라도 "알려진 제약" 기재 권고).
   - `plan.md:35`·`:106`: `ExcludedItemsView` 독스트링 범위 `:414-421` → `:414-427`.

**인정할 점.** iteration 1이 지목한 영향도 분석 3건(D1/D2/D3)은 이번에 **내가 독립적으로 재스캔한 결과와 완전히 일치**할 만큼 정확하게 보강됐다 — `EXCLUDED_STATUSES` 7곳, `auto_distributor` 소비처, 쿼리 핀 3→2의 대수적 도출까지 검증했고 추가 누락은 없었다. D5의 5종 parametrize와 AC-015/205/206은 판별력을 코드에 대입해 실재 확인했다. `plan.md:9`가 신설한 "규범 vs 검증방법" 이원 우선순위 규칙, `plan.md:78`의 취소선 자기정정, DoD `:268`의 제약 절 삭제 금지 조항은 요구된 범위를 넘어선 구조적 개선이다. 인용 정확도도 62건 재대조에서 조작 0건으로 유지됐다.

**본 FAIL의 핵심 교훈**: 검증되지 않은 주장에 AC를 붙이면 결함이 사라지는 것이 아니라 **보이지 않게 된다.** ND2는 iteration 1의 minor 결함(D12)이 "해소" 과정에서 critical로 승격된 사례다 — AC를 추가할 때는 그 AC가 **틀린 세계에서 실제로 실패하는지**를 먼저 확인해야 한다(프로젝트 메모리 `feedback_acceptance_criteria_mutation_check`).

---

Verdict: FAIL
