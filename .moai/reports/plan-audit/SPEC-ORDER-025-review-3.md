# SPEC Review Report: SPEC-ORDER-025

Iteration: 3/3 (최종)
Overall Score: 0.78

> Reasoning context ignored per M1 Context Isolation. 본 감사는 `.moai/specs/SPEC-ORDER-025/`의 문서 5종(spec.md v1.2.0, acceptance.md, plan.md, research.md, spec-compact.md)과 실제 코드베이스만을 근거로 수행했다. iteration 1/2 보고서는 **회귀 검증 목적으로만** 읽었으며, 그 판정을 승계하지 않고 코드에 재대조했다. 이전 감사 산출물 자체도 검증 대상으로 취급했다(iteration 1의 D4 서술이 틀렸던 선례가 있다).
>
> **감사 원칙(사용자 지시)**: HISTORY에 "해소했다"고 적힌 것은 근거가 아니다. 문서 본문이 실제로 바뀌었는지, 바뀐 내용이 **틀린 구현에서 실제로 실패하는지**, 모든 `file:line`이 실제 코드로 해소되는지를 명령으로 검증했다.
>
> **범위 확장에 대하여**: iteration 2→3 사이의 R4 확장(`other_publisher`를 `PURCHASE_STATUS_OPTIONS` + PATCH 2곳에서 제거)은 사용자 승인 사항이므로 존재 자체는 감사 대상이 아니다. 아래는 그 **정확성**만 감사한 결과다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  `grep -n "^- \*\*REQ-LCONF-"` 전수 추출 결과 정의 **35건, 각 1회**: `spec.md:48-62` 001~015, `:70-77` 101~108, `:85-88` 201~204, `:96-103` 301~308. 블록 내 갭 0, 중복 0, 제로 패딩 3자리 전항 일관. 신규 8건(107/108/204/304~308) 전부 각 블록의 마지막 번호에 연속 부착되어 기존 번호를 밀어내지 않았다. AC 번호도 001~015(+012a/012b 분할, +014b) / 101~108 / 201~206 / 301~308로 연속이며 갭 0.

- **[FAIL] MP-2 EARS format compliance**
  iteration 2가 지목한 `spec.md:93`(구 REQ-LCONF-303)의 주어 누락은 **해소됐다** — 현재 `spec.md:98`은 "THE 시스템은 `purchase_status="other_publisher"`인 LineItem을 … 유지한다"로 재작성되어 있다. 작성자가 감사 목록을 넘어 자체 재검토해 REQ-LCONF-101(`:70`)·103(`:72`)의 UI-요소-주어까지 "THE 시스템은"으로 고친 것도 확인했다(요구된 범위 이상의 조치).

  그러나 **신규 `spec.md:76` REQ-LCONF-107은 `(Unwanted)`로 선언되었으나 IF 절의 조건이 "바람직하지 않은 조건"이 아니다**:

  > (Unwanted) IF 담당자가 어느 행의 발주처리 버튼을 클릭하면, THEN 시스템은 그 클릭 이벤트가 행 자체의 클릭 핸들러(SKU 선택 토글)까지 전파되게 하지 않는다

  "담당자가 버튼을 클릭"은 정상적이고 의도된 트리거다. EARS Unwanted behaviour는 `IF <undesired condition>, THEN the <system> shall <response>` — 즉 트리거 자체가 원치 않는 사건이어야 한다. 이 요구사항의 트리거는 Event-driven(`WHEN 담당자가 … 클릭하면, THE 시스템은 …`)이며, 원치 않는 것은 트리거가 아니라 **응답 쪽에서 부정된 전파**다. 이는 iteration 1이 REQ-LCONF-203의 `(Unwanted)`→`(Ubiquitous)` 오표기를 MP-2 FAIL로 판정한 것과 **동일한 구조적 결함**이므로 동일 기준을 적용한다.

  1/35(2.9%)이며 주어 누락은 0건이므로 iteration 1(5건)·iteration 2(1건)와 같은 추세로 개선됐다. MP-2는 비보상적(non-compensatory) 기준이라 FAIL이지만, **실무 영향은 사실상 없다**(아래 결함 등급 참조). 수정 비용은 라벨 1개 + 접속사 1개.

- **[PASS] MP-3 YAML frontmatter validity**
  `spec.md:1-11` 6개 필수 필드 전항 존재·타입 적합: `id: SPEC-ORDER-025`(`:2`, 패턴 일치), `version: 1.2.0`(`:3`, 1.1.0에서 정상 증가 — 범위 확장을 minor bump로 반영), `status: draft`(`:4`), `created_at: 2026-08-17`(`:5`, ISO 8601), `priority: High`(`:8`), `labels: [order, purchase, purchase-status, distributor, frontend, backend]`(`:10`, array). `updated: 2026-08-17`(`:6`)도 유지.

- **[N/A] MP-4 Section 22 language neutrality**
  단일 스택(Django + React/TypeScript) SPEC이며 다국어 툴체인·LSP를 다루지 않는다. 자동 통과.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 | 규범 진술 대부분이 단일 해석만 허용한다. `spec.md:98` REQ-LCONF-303의 조건부 재작성("노트가 연결되어 있는 경우에 한해")은 iteration 2의 ND2 핵심을 정확히 해소했고, Daily Review 경로에 대한 부정 진술도 코드와 일치함을 재확인했다(`_reorder_candidate_filter`, `purchase_order_views.py:109-111`). 감점: `spec.md:31`/`:40`/`spec-compact.md:20`/`research.md:199`가 **거짓 전제**("Daily Review 업로드는 항상 타출판사 노트를 동반한다")를 규범 결정 D4의 근거로 사용(ND-A), `spec.md:100` REQ-LCONF-305의 근거가 같은 문서의 REQ-LCONF-302와 모순(ND-B), `spec.md:76` REQ-LCONF-107 패턴 오표기. |
| Completeness | 0.75 | 0.75 | 필수 섹션 전항 존재. Exclusions가 5→7개로 확장되며 신규 항목 2건(레거시 소급 백필, 모델 필드 `PURCHASE_STATUS_CHOICES` 미변경)이 전부 구체적 심볼명을 포함한다(강점 유지). "알려진 제약"이 2→3개로 확장되고 신규 `yes24` 라벨 항목은 코드 대조 결과 **정확**하다(`OrderDetailPage.tsx:13-22`에 발주처 5 + 창고 3 = 8개, `yes24` 부재 확인). 영향도 분석은 이번에도 독립 재스캔과 일치했다 — `PURCHASE_STATUS_OPTIONS` 소비처 4곳(`UnorderedItemsTab.tsx:207,294,344,495`)이 내 grep과 완전 일치, 모델 레벨 무영향 3파일도 확인. 감점: **"알려진 제약"이 잔여 사각지대를 과소 기술**(ND-A — 레거시 행만 고아화된다고 적었으나 향후 Daily Review 업로드 행도 조건부로 동일하게 고아화됨), `acceptance.md:332` 품질 게이트가 `purchaseOrderApi.test.ts:23-35` **기존 단정의 필수 수정**을 누락(ND-D, plan.md는 기재). |
| Testability | 0.75 | 0.75 | 이번 iteration의 최대 개선 영역이다. **신규·정정 AC 9건의 판별력을 코드에 대입해 실재 확인**했다 — AC-012a(`FOR UPDATE` SQL 텍스트 단정, `test_spec_016.py:1013-1027` 선례 실재), AC-012b(`@pytest.mark.concurrency` 명시, `pytest.ini:8` 규약 원문 일치), AC-014(mutation을 `AllowAny` 명시로 정정, `base.py:106-108` 대조 정확), AC-014b(클래스 속성 정적 단정 — 선언 누락을 프로젝트 기본값 폴백과 구분해내는 유일한 수단), AC-302b(노트 없음 대조군 추가), AC-302c(`daily-review-excel` 실측 + `unordered` 대조군 — `DailyReviewExcelView.get()`이 `_reorder_candidate_filter`를 쓰므로 실제로 판별력 있음), AC-304/306/307(전부 틀린 구현에서 실패 확인). 감점: **AC-LCONF-308의 노트 생성 단정은 올바른 무수정 구현에서 실패한다**(ND-A(a) — `purchase_order_views.py:1805` `if note is not None:` 가드 + 지정된 픽스처의 메모 기본값 `""`). |
| Traceability | 0.90 | 0.75~1.0 사이 | **35개 REQ 전항이 대응 AC를 가진다.** iteration 2의 ND4(AC-107/108/206이 근거 REQ 없이 규범을 단정)가 REQ-LCONF-107/108/204 신설로 완전 해소됐고, 신규 REQ-304~308도 AC-304~308과 1:1로 대응한다(`acceptance.md:269,278,287,296,303`). 역방향도 확인 — 근거 REQ 없는 AC는 0건. 감점 사유는 단 1건: REQ-LCONF-202의 타입 절(`UnorderedItem`에서 `auto_distributor` 필드 제거)이 여전히 전용 AC 없이 `tsc -b` 게이트(`acceptance.md:333`)에만 의존한다(iteration 2에서 이월, 실무 영향 낮음). |

---

## Citation Verification (독립 재검증)

**v1.2.0에서 신규·변경된 인용 34건을 코드에 재대조했다. 조작된 인용은 1건도 없다.** 아래는 범위 확장(M2b)과 ND 해소 주장의 핵심 근거만 발췌한 것이다.

| 인용 | 문서 위치 | 검증 결과 |
|------|-----------|-----------|
| `purchaseOrderApi.ts:62` `{ value: 'other_publisher', ... }` | spec.md:99, research.md:159 | **정확 일치** |
| `purchaseOrderApi.ts:43-49` damaged_exchange 라벨 유지 선례 주석 | spec.md:40, plan.md:55 | **정확**(`:43` 주석 시작, `:49` `damaged_exchange: '파손/교환',`) |
| `PURCHASE_STATUS_OPTIONS` 렌더 사이트 4곳 `:207,294,344,495` | plan.md:55, research.md:167 | **독립 grep 결과와 완전 일치**(누락·과잉 0). `:344`의 `.filter(o => o.value !== 'unordered')`도 확인 |
| `purchase_order_views.py:2516-2520` / `:2573-2577` damaged_exchange 거부 분기 | spec.md:40, plan.md:57-58 | **2건 모두 정확 일치**(각 5줄 블록의 첫/끝 라인까지 일치) |
| `_DAMAGED_EXCHANGE_BLOCKED_MESSAGE`(`:2475-2479`) 공유 상수 | research.md:184 | **정확 일치** |
| `LineItemStatusUpdateView.patch()`(`:2503-2532`), 독스트링(`:2496-2497`) | plan.md:57, :123 | **정확 일치** |
| `excel_utils.py:660` `"타출판사": "other_publisher"` | spec.md:103, research.md:188 | **정확 일치**(`_NOTE_TYPE_STATUS_MAP` `:656-660`) |
| `purchase_order_views.py:1792-1799` 타출판사 분기 | spec.md:103, plan.md:59 | **정확 일치**(`:1792` `if note_type == "타출판사":`, `:1799` `li.purchase_status = new_status`) |
| `purchase_order_views.py:1711-1714` "노트 bulk_create" | spec.md:40, research.md:199 | **범위 오기 + 결정적 누락** — `:1711-1713`은 주석, `:1714`는 `pending_notes: list = []` 선언이며 실제 `LineItemNote.objects.bulk_create()`는 `:1967`이다. 무엇보다 **`:1805`의 `if note is not None:` 가드가 인용 범위 밖에 있어, 이 인용이 뒷받침한다고 주장하는 명제를 반증한다**(ND-A) |
| `base.py:106-108` `DEFAULT_PERMISSION_CLASSES=[IsAuthenticated]` | acceptance.md:122, plan.md:22/31, research.md:203-213 | **정확 일치** — iteration 2 ND1의 근거와 완전 동일. 감사 원문의 오류를 코드로 정정한 것이 맞다 |
| `local.py:11` `DB_ENGINE default=sqlite3` | acceptance.md:94, research.md:221 | **정확 일치** |
| `pytest.ini:8` concurrency 마커 정의 | acceptance.md:106, research.md:222 | **원문 전문 일치** |
| `test_spec_016.py:1013-1027` / `:1030-1064` | acceptance.md:94/104, plan.md:32, research.md:223-224 | **2건 정확 일치**(독스트링 인용문까지 원문 대조 완료) |
| `test_purchase_orders.py:2300-2304`(401) / `:2306-2319`(6종) / `:2321-2335`(damaged 거부) | acceptance.md:119/289/330, plan.md:31/61-62 | **3건 모두 정확 일치** |
| `purchaseOrderApi.test.ts:15-21` / `:23-35` / `:43-45` | acceptance.md:271/280, plan.md:67-69, research.md:240 | **3건 모두 정확 일치**(`:28`에 `{ value: 'other_publisher', label: '타출판사' }` 실재 확인) |
| `views.py:39` OrderDetailView / `:489-502` LineItemNoteUnresolvedListView / `:497-502` get_queryset | acceptance.md:255/257/259 | **3건 정확 일치** |
| `purchase_order_views.py:108-111` `_reorder_candidate_filter` 본체 | acceptance.md:261 | **정확**(본체는 `:109-111`, `:108`은 독스트링 종료 — 실무상 오차 없음) |
| `GET /api/purchase-orders/daily-review-excel/` 라우트 | acceptance.md:260 | **실재**(`urls.py:72`), `DailyReviewExcelView.get()`(`:1249`)이 `_reorder_candidate_filter`(`:1260`) 사용 확인 → AC-302c의 판별 논리 성립 |
| `test_spec_024.py` DistributorVendorRule 참조 **10건** | acceptance.md:220, plan.md:148 | **정확**(`grep -c` = 10) — ND3 정정 확인 |
| `OrderDetailPage.tsx:13-22` "8개 값 — 발주처 5 + 창고 3", `yes24` 부재 | spec.md:111, research.md:85 | **정확** — ND6 정정 확인(실제 booxen/kyobo/choeumgoyuk/agape/sungseoyunion + warehouse_korea/ca/nj) |
| `OrderDetailPage.tsx:374` 폴백 렌더 / `UnorderedItemsTab.tsx:132` `yes24: 'YES24'` | spec.md:111 | **2건 정확 일치** |
| `ExcludedItemsView` 독스트링 `:414-427`, "four" 문장 `:418` | plan.md:37, :133 | **정확** — ND7 정정 확인(`:427`이 닫는 `"""`) |
| `UnorderedItemsView` 독스트링 `:323-328`, auto_distributor 문장 `:327` | plan.md:36, :133 | **정확 일치** |
| `UnorderedItemsTab.tsx:426`(자동추천 `<th>`) / `:433`(`colSpan={8}`) / `:442`(행 onClick) / `:449`(체크박스 stopPropagation) | plan.md:80 | **4건 모두 정확 일치**, 미발주 테이블 `<th>` 8개 실측 확인 → REQ-LCONF-204의 "8 유지"는 산술적으로 정확 |
| `LineItemBulkStatusUpdateView.patch()`(`:2540-2598`) | plan.md:58, research.md:184 | **경미한 오기** — `:2540`은 `class` 선언, `patch()`는 `:2556`(작업 지시에는 영향 없음) |
| `UnorderedItemsTab.tsx` 행별 select "`:472` 이하" | research.md:159 | **문서 내 불일치** — 같은 파일 `:167`과 `plan.md:55`는 `:495`라 기재. 실제 `PURCHASE_STATUS_OPTIONS` 호출은 `:495` |

---

## Regression Check (iteration 2 결함 7건 + MP-2)

| ID | Sev | 판정 | 근거 |
|----|-----|------|------|
| MP-2(REQ-303 주어) | — | **RESOLVED** | `spec.md:98`이 "THE 시스템은 … 유지한다"로 재작성. 추가로 감사가 지목하지 않은 REQ-101(`:70`)·103(`:72`)까지 자체 발견해 정정. **단 신규 REQ-107에서 새 오표기 발생(ND-C)** |
| ND1 | major | **RESOLVED** | `acceptance.md:122`가 mutation을 `permission_classes = [AllowAny]` 명시로 정정하고 그 근거(`base.py:106-108`)를 직접 인용 — 내가 `base.py`를 재확인한 결과 인용 정확. **AC-LCONF-014b 신설**(`:124-131`)로 "선언 누락"과 "기본값 폴백"을 구분하는 정적 단정 추가 — 이 AC의 판별 mutation(선언 자체 누락)은 AC-014를 통과시키지만 014b는 실패시킨다는 주장이 코드상 성립함을 확인. `plan.md:22`가 구현 지시(명시 선언 필수)까지 동기화. 요구된 것 이상의 조치 |
| ND2 | critical | **RESOLVED (본체) / 신규 파생 결함 발생** | (a) `spec.md:98` REQ-LCONF-303에서 "Daily Review 경로로 조회 가능" 거짓 주장이 삭제되고 정반대의 참 명제로 대체됨 — 코드 대조 완료. (b) `spec.md:31` 문제 정의 3번도 함께 정정. (c) `acceptance.md:260` AC-302c가 "무관한 스위트 재실행"에서 "`daily-review-excel` 결과에 other_publisher는 없고 unordered 대조군은 있다"로 교체 — **실제 판별력 확인**(`_reorder_candidate_filter`를 넓히는 mutation에서 실패). (d) `acceptance.md:258` AC-302b에 노트 없음 대조군(Given-2) 추가로 Given 조작 문제 완화. (e) 사용자 승인 하에 R4를 확장해 근본 통로 차단(REQ-304~308). **그러나 그 확장의 정당화 근거가 새로운 거짓 명제에 기대고 있다 → ND-A** |
| ND3 | minor | **RESOLVED** | `acceptance.md:220`·`plan.md:148` 모두 10건으로 정정, 라인 목록(`:13,:30,:89,:108,:129,:162,:186,:210,:228,:246`)까지 명시. `grep -c` 재실측 = 10 |
| ND4 | minor | **RESOLVED** | REQ-LCONF-107(`spec.md:76`)·108(`:77`)·204(`:88`) 신설로 `acceptance.md`에만 있던 규범이 `spec.md`로 승격. 번호 연속성도 유지(101~108, 201~204). `plan.md:9`의 단일출처 규칙과 정합 |
| ND5 | major | **RESOLVED** | AC-012가 012a(결정론적 `FOR UPDATE` SQL 단정)/012b(`@pytest.mark.concurrency` 명시 스레드)로 분할(`acceptance.md:92-107`). 선례(`test_spec_016.py:1013-1027`, `:1030-1064`)·마커 규약(`pytest.ini:8`)·SQLite 기본 엔진(`local.py:11`) 전부 재확인. `acceptance.md:327-328,331`의 품질 게이트 명령도 `-m "not concurrency"` / `-m concurrency` 2행으로 분리됨 — 권고 (a)(b)(c) 전부 반영 |
| ND6 | minor | **RESOLVED** | `research.md:85`가 "발주처 5개 + 창고 3개"로 정정되고 `VALID_DISTRIBUTORS`와 혼동했음을 명시. 추가로 `spec.md:111`에 `yes24` 라벨 부재를 "알려진 제약"으로 신규 기재(권고 초과 이행) |
| ND7 | minor(nit) | **RESOLVED** | `plan.md:37`·`:133` 모두 `:414-427`로 정정 |

**정체(stagnation) 판정**: 3회 연속 동일하게 남은 결함은 **없다**. iteration 1의 13건, iteration 2의 7건이 각각 전부 해소되었거나(문서 본문 기준, 코드 대조 완료) 사용자 승인 하에 범위 확장으로 흡수되었다. manager-spec은 매 iteration 실질적으로 진전했으며, 특히 "감사가 지목하지 않은 동종 결함을 자체 발견해 정정"하는 패턴(REQ-101/103, `yes24` 알려진 제약)이 iteration 2·3에서 반복 관찰된다.

---

## Defects Found

### ND-A. `spec.md:31`, `spec.md:40`, `spec.md:110`, `research.md:199`, `spec-compact.md:20`, `acceptance.md:309` — "Daily Review 업로드는 타출판사 행에 항상 노트를 동반한다"는 명제가 거짓이며, 이 명제가 범위 확장의 정당화·잔여 제약 기술·AC-308 단정을 동시에 지탱하고 있다 — Severity: **critical**

`spec.md:40` D4는 범위 확장의 결론부를 이렇게 진술한다:

> 이후 `other_publisher`는 Daily Review 업로드 경로로만 생성되며, 그 경로는 항상 타출판사 노트도 함께 만들어(`purchase_order_views.py:1711-1714` bulk_create) REQ-LCONF-303의 "타출판사 노트가 연결된 경우 품목 노트 탭에서 조회 가능" 조건이 **향후 생성되는 모든 행**에 대해 성립하게 만든다.

`research.md:199`가 같은 주장을 "이 세션에서 직접 코드를 추적해 확인했다"는 문구와 함께 반복하고, `spec.md:31`(문제 정의 3번)과 `spec-compact.md:20`도 동일 전제를 재사용한다.

**이 명제는 거짓이다.** 노트 생성은 무조건이 아니라 가드 안에 있다 — `backend/order/purchase_order_views.py:1804-1815`:

```python
cs_status_updates.extend(unordered_lis)      # :1804  ← purchase_status는 무조건 기록
if note is not None:                          # :1805  ← 노트는 조건부
    for li in unordered_lis:
        pending_notes.append(
            LineItemNote(line_item=li, content=note, ..., note_type=note_type, ...)
        )
```

`note`는 '선택' 컬럼(`note_type`)과 **별개 컬럼**에서 온다 — `excel_utils.py:944` `note = _str_or_none(_cell(row, note_idx))`, 그리고 `:881-884`:

```python
if is_new_template:
    note_idx = header.index("Status") if "Status" in header else None   # 신규 템플릿: Status 컬럼
else:
    note_idx = header.index("메모") if "메모" in header else None        # 레거시 템플릿: 메모 컬럼
```

`_str_or_none`(`excel_utils.py:760-764`)은 빈 문자열을 `None`으로 정규화한다. 따라서 **'선택'='타출판사'이면서 메모(레거시)/Status(신규) 셀이 비어 있는 행은 `purchase_status="other_publisher"`가 기록되지만 `LineItemNote`는 생성되지 않는다.**

기존 테스트가 이 경로를 이미 실행하고 있다 — `backend/order/tests/test_spec_024.py:87-103` `test_agape_publisher_sets_confirmed_distributor`는 '타출판사' 행을 업로드하고 `assert li.purchase_status == "other_publisher"`만 단정하며, 노트 존재는 단정하지 않는다.

**결과 (a) — AC-LCONF-308이 올바른 무수정 구현에서 실패한다.** `acceptance.md:307-309`는 픽스처와 단정을 이렇게 지정한다:

> **Given** … `test_daily_review_upload.py`의 `_make_daily_review_excel` 헬퍼 재사용.
> **Then** … 대응하는 `LineItemNote(note_type="타출판사")`가 함께 생성된다.

그런데 그 헬퍼(`test_daily_review_upload.py:77-114`)는 메모 셀을 `row.get("note", "")` — 즉 **기본값 빈 문자열**로 채운다. 지정된 대로 픽스처를 쓰면 `note`가 `None`이 되어 노트가 생성되지 않으므로, `UploadDailyReviewView`를 **한 줄도 건드리지 않은 상태에서** 이 회귀 AC가 실패한다. 구현 세션은 (i) 존재하지 않는 회귀를 추적하며 시간을 쓰거나, (ii) 픽스처에 `"note": "..."`를 슬쩍 추가해 통과시키게 된다 — 후자는 문제를 감출 뿐 거짓 명제를 그대로 남긴다. `plan.md:65`도 같은 지시("노트도 생성됨을 확인")를 반복한다.

**결과 (b) — "알려진 제약"이 잔여 사각지대를 과소 기술한다.** `spec.md:110`은 고아화 대상을 "이 SPEC 이전에 수동 지정된" **레거시 행으로 한정**하고, REQ-LCONF-304~307이 "**향후** 발생을 방지"한다고 단언한다. 실제로는 R4 적용 후에도 다음이 성립한다:

> 담당자가 Daily Review에서 '선택'='타출판사'로만 표시하고 메모/Status 셀을 비워 업로드 → `purchase_status="other_publisher"` 기록, 노트 없음 → 보류/제외 뷰에서 제외(REQ-302) → 품목 노트 타출판사 탭에 없음(노트 없음) → Daily Review 재조회에도 없음(`_reorder_candidate_filter`가 배제, `:109-111`) → **주문번호를 이미 알아야만 주문상세에서 찾을 수 있음.**

즉 iteration 2의 ND2가 드러낸 사각지대는 **수동 지정 통로에 한정된 것이 아니었고**, 범위 확장은 그중 한 갈래만 막는다. 사용자가 승인한 것은 "가시성 공백을 닫는다"였는데, SPEC은 닫히지 않은 잔여분을 닫혔다고 기술한다.

이는 프로젝트 메모리 `feedback_acceptance_criteria_mutation_check`("통과하는 테스트 ≠ 검증된 구현")와 `project_daily_review_reupload_noop`이 경고하는 실패 양식의 재발이며, iteration 2 ND2와 **동일한 결함 패턴이 인접 명제로 이동한 형태**다.

**권고(3택 1, 어느 쪽이든 5개 문서를 함께 정정할 것 — `spec.md:31`, `spec.md:40`, `spec.md:110`, `research.md:199`, `spec-compact.md:20`)**:
1. **(최소 비용, 권장)** "항상/모든 행" 주장을 **"메모(레거시 템플릿) 또는 Status(신규 템플릿) 셀이 비어 있지 않은 경우에 한해"**로 조건화하고, `spec.md:110` "알려진 제약"을 확장하라 — 레거시 행뿐 아니라 **향후 업로드되는 메모 공란 타출판사 행도 동일하게 고아화됨**을 명시. 동시에 `acceptance.md:307-309` AC-LCONF-308의 Given에 `"note": "<임의 문자열>"`을 **명시하고**, Then의 노트 단정이 그 조건부임을 적어라(또는 노트 단정을 삭제하고 `purchase_status` 반영만 회귀로 남겨라 — 이 AC의 목적은 "PATCH 400 게이트가 업로드 경로를 막지 않음"의 증명이므로 노트 단정은 본래 불필요하다).
2. 또는 `UploadDailyReviewView`의 타출판사 분기가 메모 공란일 때도 노트를 생성하도록 범위를 넓혀라(신규 REQ 필요 — `Exclusions 3번`이 `UploadDailyReviewView` 로직 변경을 금지하므로 Exclusion도 함께 수정해야 한다).
3. 또는 오케스트레이터를 경유해 사용자에게 "메모 공란 타출판사 행을 어떻게 다룰지"를 확인하라.

### ND-B. `spec.md:100` REQ-LCONF-305 / `acceptance.md:285` — 라벨 유지의 근거로 제시된 소비처가 이 SPEC이 스스로 제거하거나 애초에 존재하지 않는다 (문서 내 모순) — Severity: **major(문서 정확성) / 낮음(구현 위험)**

REQ-LCONF-305는 `PURCHASE_STATUS_LABELS`에 `other_publisher`를 유지하는 이유를 이렇게 설명한다:

> … 보류/제외 품목 표의 제외 사유 배지, 주문상세 화면 등에서 원시 문자열이 아닌 한글 라벨로 계속 표시되도록 한다

두 소비처 모두 성립하지 않는다:

- **"보류/제외 품목 표의 제외 사유 배지"** = `UnorderedItemsTab.tsx:283` `{PURCHASE_STATUS_LABELS[item.purchase_status] ?? item.purchase_status}`(REQ-RESTORE-017). 그러나 같은 SPEC의 **REQ-LCONF-302가 `other_publisher` 행을 이 표에서 제거**하므로, 이 배지는 R4 적용 후 `other_publisher`를 받을 수 없다. 같은 문서 안의 두 요구사항이 서로를 무효화한다.
- **"주문상세 화면"** — `grep -rn "PURCHASE_STATUS_LABELS" frontend/src` 결과 이 상수를 import하는 파일은 `UnorderedItemsTab.tsx` **단 하나**다. `OrderDetailPage.tsx`는 `purchase_status`를 렌더링조차 하지 않는다(`grep -n "purchase_status" frontend/src/pages/OrderDetailPage.tsx` → 0건).

`acceptance.md:285` AC-LCONF-305의 mutation 서술("기존 `other_publisher` 행이 보류/제외 뷰의 제외 사유 배지나 주문상세 화면에서 … 원시 문자열로 표시되고")도 같은 이유로 성립하지 않는다.

**요구사항 자체는 유지해도 무방하다** — 라벨 삭제는 `UnorderedItemsTab.tsx:495` select에서 `other_publisher` 행(예: R4 적용 직후 잔존 레거시 데이터가 어떤 경로로든 이 표에 유입되는 경우)의 표시 회귀를 부를 수 있고, AC-305 자체는 `PURCHASE_STATUS_LABELS.other_publisher === '타출판사'`를 직접 단정하므로 판별력이 있다. 문제는 **근거가 거짓**이라는 점이다. 승인자는 "다른 화면에서 계속 보인다"는 (틀린) 전제로 이 요구사항을 승인하게 된다.

권고: REQ-LCONF-305의 근거를 사실에 맞게 교체하라 — 예: "`PURCHASE_STATUS_OPTIONS`에서만 제거하고 라벨 맵은 유지하는 것이 `damaged_exchange`(`purchaseOrderApi.ts:43-49`)가 확립한 프로젝트 패턴이며, 향후 어떤 표시 경로가 추가되더라도 원시 열거형 문자열 노출을 막는 방어적 조치다." 아울러 `spec.md:100`이 언급하는 "주문상세 화면"은 삭제하라.

### ND-C. `spec.md:76` REQ-LCONF-107 — EARS 패턴 오표기 `(Unwanted)` — Severity: **minor**

MP-2 항에서 상술. `IF 담당자가 … 클릭하면`은 정상 트리거이므로 Unwanted가 아니라 Event-driven이다. 형제 요구사항 REQ-LCONF-102(`spec.md:71`)가 이미 동일한 트리거를 `(Event-Driven) WHEN 담당자가 어느 행의 발주처리 버튼을 클릭하면, THE 시스템은 …`으로 올바르게 쓰고 있으므로, 그 형태를 그대로 따르면 된다.

권고: `(Event-Driven) WHEN 담당자가 어느 행의 발주처리 버튼을 클릭하면, THE 시스템은 그 클릭 이벤트를 행 자체의 클릭 핸들러(SKU 선택 토글)로 전파하지 않는다 — 모달은 열리되 …`

### ND-D. `acceptance.md:332` — 품질 게이트가 `purchaseOrderApi.test.ts:23-35` 기존 단정의 필수 수정을 누락 — Severity: **minor**

`purchaseOrderApi.test.ts:23-35` `it('preserves all six existing options unmodified')`는 `:28`에서 `{ value: 'other_publisher', label: '타출판사' }`가 `PURCHASE_STATUS_OPTIONS`에 **존재함을 단정**한다. REQ-LCONF-304가 이 단정을 반드시 깨뜨린다.

`plan.md:67`(`:23-35` → 5개로 갱신)과 `plan.md:139`(파일 목록 MODIFY)가 이를 정확히 지시하고 있으므로 **구현 세션이 놓칠 위험은 낮다**. 다만 `acceptance.md:332` 품질 게이트 행은 "`purchaseOrderApi.test.ts`(AC-304/305 **신규 케이스**) 전량 통과"라고만 적어, 기존 케이스 반전이 필요하다는 사실이 검증 규범 문서에서 빠져 있다 — `plan.md:10`이 "검증 방법은 `acceptance.md`가 규범"이라 선언한 이상 정합성 결함이다.

권고: `acceptance.md:332`를 "…`purchaseOrderApi.test.ts`(`:23-35` 기존 6개 옵션 단정을 5개로 반전 + AC-304/305 신규 케이스)…"로 보완하라.

### ND-E. 경미한 인용 오차 3건 — Severity: **minor(nit)**

- `spec.md:40` / `research.md:199`: `purchase_order_views.py:1711-1714`를 "bulk_create"라 지칭하나 `:1711-1713`은 주석, `:1714`는 `pending_notes` 선언이며 실제 `LineItemNote.objects.bulk_create()`는 `:1967`이다. (ND-A와 함께 정정할 것 — 인용 범위가 `:1805` 가드를 배제한 것이 거짓 명제의 직접 원인이다.)
- `plan.md:58` / `research.md:184`: `LineItemBulkStatusUpdateView.patch()`(`:2540-2598`) — `:2540`은 `class` 선언, `patch()`는 `:2556`.
- `research.md:159`: 미발주 행별 select를 "`:472` 이하"라 적었으나 같은 문서 `:167`과 `plan.md:55`는 `:495`. 실제 `PURCHASE_STATUS_OPTIONS` 호출은 `:495`(`:472`는 이전 개정판의 위치로 보인다).

---

## Chain-of-Verification Pass

1차 감사 후 2차 자기비판을 수행했다.

**"iteration 2 결함 7건 + MP-2를 전부 문서 본문에서 확인했는가, HISTORY 문구만 읽고 넘어가지 않았는가?"**
8건 전부에 대해 (a) 문서 본문의 변경 위치를 특정하고 (b) 그 내용을 코드에 대조했다. `spec.md:21`의 방대한 v1.2.0 HISTORY 항목은 근거로 채택하지 않았다. 특히 ND5는 "분할했다"는 서술만 보지 않고 AC-012a/012b 각각의 Given/When/Then과 선례 테스트 원문·`pytest.ini` 마커 정의·SQLite 기본 엔진을 모두 재확인했다.

**"모든 REQ를 읽었는가, 신규 8건만 보고 기존을 표본 처리하지 않았는가?"**
35개 REQ 정의를 전수 추출해 개별 검토했다. **2차 패스에서 ND-C(REQ-107 패턴 오표기)를 발견** — 1차 패스에서는 신규 REQ에 "THE 시스템은" 주어가 있는지만 확인하고 넘어갔으나, 패턴 라벨과 IF 절의 의미론을 대조하는 단계에서 포착했다. iteration 1이 라벨 오표기를 MP-2 FAIL로 판정한 선례를 적용했다.

**"판별 mutation을 문서 문구로만 읽지 않고 실제 코드에 대입했는가?"**
신규·변경 AC 9건(012a, 012b, 014, 014b, 302a/b/c, 304, 305, 306, 307, 308)의 mutation을 코드 경로에 대입해 결과를 추론했다. **2차 패스에서 ND-A(a)를 발견** — 1차 패스에서는 AC-308을 "회귀 AC이므로 무수정 통과가 당연"으로 처리했으나, "그럼 실제로 무수정 상태에서 통과하는가"를 되물어 `_make_daily_review_excel`의 메모 기본값 → `_str_or_none` → `if note is not None:` 경로를 추적한 결과 **올바른 구현에서 실패한다**는 것을 확인했다. 거기서 역추적해 D4·문제 정의·research §5-4의 공통 전제(ND-A(b))에 도달했다.

**"범위 확장(M2b)의 영향도 분석이 완전한가, 문서가 열거한 것만 확인하지 않았는가?"**
문서와 무관하게 독립 재스캔했다: `grep -rn "PURCHASE_STATUS_OPTIONS|PURCHASE_STATUS_LABELS" frontend/src`(소비처 4곳 + 테스트 + 정의, 문서와 완전 일치), `grep -rn "other_publisher" backend/order/tests/*.py`(6개 파일 — `test_purchase_orders.py:2238/2310`, `test_spec_018.py`, `test_spec_024.py`, `test_purchase_order_models.py:321/455`, `test_spec_012.py:257`, 전부 문서가 분류한 대로 PATCH 경유 여부를 개별 확인), `grep -rn "PurchaseStatusValue"`(소비처 0건 — 타입 축소의 파급 없음), bulk 엔드포인트 테스트 전수(`:2356-2431`, `other_publisher` 사용 0건). **문서가 놓친 영향은 `purchaseOrderApi.test.ts:23-35` 1건뿐이며 그것도 `plan.md`는 잡고 있었다**(ND-D는 `acceptance.md` 누락에 한정). 범위 확장의 영향도 분석은 실질적으로 완전하다.

**"Exclusions를 존재 여부만 보지 않고 구체성까지 봤는가?"**
`spec.md:117-123` 7개 항목 전부 재검토. 신규 2건(6번 레거시 소급 백필, 7번 모델 필드 미제거)도 구체적 심볼명(`LineItem.PURCHASE_STATUS_CHOICES`)과 경계 근거를 포함하며 모호 항목 0건. 특히 7번은 REQ-LCONF-306의 "멤버십 검사 통과 값에만 추가 적용" 서술과 정합하고, 코드(`purchase_order_views.py:2509-2520`의 검사 순서)와도 일치함을 확인했다.

**"요구사항 간·문서 간 모순을 찾았는가?"**
**2차 패스에서 ND-B를 발견** — 1차 패스에서는 REQ-304/305를 "damaged_exchange 선례의 정확한 복제"로 보고 통과시켰으나, 305의 *근거절*이 지목하는 소비처를 실제로 열어본 결과 하나는 REQ-302가 제거하고 하나는 존재하지 않았다. 문서 간 모순(`plan.md` ↔ `acceptance.md`)은 ND-D 1건이며, 문서 ↔ 코드 모순이 ND-A/ND-B다.

**"수치 주장을 표본이 아니라 전수로 대조했는가?"**
정량 주장 9건(렌더 사이트 4곳, `test_spec_024` 10건, `test_auto_dist` 40건, `DISTRIBUTOR_LABELS` 8개, `<th>` 8개, `colSpan` 8, `EXCLUDED_STATUSES` 7곳, 쿼리 핀 3→2, ANCHOR 5/WARN 7)을 명령으로 재측정했다. **전건 정확** — iteration 1(D2/D9)·iteration 2(ND3/ND6)에서 반복됐던 "실측 주장 부정확" 계열 결함이 이번에는 0건이다. 이 문서군의 인용 신뢰도는 iteration을 거치며 실질적으로 개선됐다.

**신규 발견 요약**: 2차 패스에서 ND-A(critical), ND-B(major), ND-C(minor)를 추가 발견했다. 1차 패스만으로는 "iteration 2 결함 7건 전부 해소, 사소한 인용 오차만 남음 → PASS"라는 결론에 도달했을 것이다.

---

## Recommendation

**FAIL.** 다만 이번 FAIL의 성격은 iteration 1·2와 명확히 다르다 — 영향도 분석, 인용 정확도, 판별력 설계, 추적성은 **이번 iteration에서 사실상 완성됐다**(전수 재검증에서 각각 누락 1건 이하). 남은 것은 **범위 확장의 정당화 근거에 검증되지 않은 명제가 들어간 것**과 그로부터 파생된 AC 1건의 오작동이다.

최종 iteration이므로 판정을 실행 가능하게 서열화한다.

### Tier 1 — 이대로 진행하면 잘못된 결과가 실제로 배포되거나 구현 세션을 오도하는 항목 (차단)

1. **[ND-A critical] "Daily Review는 항상 타출판사 노트를 만든다"는 거짓 명제를 5개 문서에서 정정하고, AC-LCONF-308을 실행 가능하게 고쳐라.**
   - 근거: `purchase_order_views.py:1805` `if note is not None:` 가드 + `excel_utils.py:881-884`(note는 메모/Status 별도 컬럼) + `excel_utils.py:760-764`(빈 문자열 → None) + `test_spec_024.py:87-103`(노트 없이 `other_publisher`가 기록되는 기존 테스트).
   - 최소 조치: (i) `spec.md:40`·`:31`, `research.md:199`, `spec-compact.md:20`의 "항상/모든 행"을 "메모(또는 Status) 셀이 비어 있지 않은 경우에 한해"로 조건화. (ii) `spec.md:110` "알려진 제약"에 **향후 업로드되는 메모 공란 타출판사 행도 동일하게 고아화됨**을 추가(현재는 레거시 행만 기재). (iii) `acceptance.md:307-309` AC-LCONF-308의 Given에 `"note"` 값을 명시하거나, 노트 단정을 삭제하고 "HTTP 201 + `purchase_status == 'other_publisher'`"만 회귀 대상으로 남길 것 — 이 AC의 목적(REQ-306/307의 400 게이트가 업로드 경로를 막지 않음)에는 노트 단정이 불필요하다. `plan.md:65`도 함께 동기화.
   - **이것이 유일한 "구현이 잘못 나갈 수 있는" 항목이다.** (iii)를 고치지 않으면 무수정 상태에서 회귀 AC가 실패하며, 가장 개연성 높은 대응(픽스처에 메모 추가)은 (ii)의 사각지대를 영구히 가린다.

### Tier 2 — 문서 정확성 결함. 유능한 구현자가 이 때문에 틀린 코드를 쓰지는 않으나, 승인자가 틀린 전제로 승인하게 됨

2. **[ND-B major] REQ-LCONF-305(`spec.md:100`)의 근거를 사실로 교체하라.** 요구사항(라벨 유지)은 그대로 두되, 근거에서 "주문상세 화면"을 삭제하고(그 화면은 `purchase_status`를 렌더링하지 않는다), "보류/제외 품목 표의 제외 사유 배지"는 REQ-LCONF-302가 그 표에서 `other_publisher`를 제거한다는 사실과 모순되므로 `damaged_exchange` 패턴 일관성 + 방어적 조치로 근거를 바꿔라. `acceptance.md:285`의 mutation 서술도 동일하게 정정. **구현 코드에는 영향 없다.**

3. **[ND-C minor / MP-2] `spec.md:76` REQ-LCONF-107의 패턴 라벨을 `(Event-Driven)`으로 고치고 `WHEN … THE 시스템은` 형태로 재작성하라.** 형제 REQ-LCONF-102(`:71`)가 동일 트리거에 대해 이미 올바른 형태를 쓰고 있다. **의미는 이미 명확하므로 구현 위험은 0이다** — 순수 형식 준수 항목이며, MP-2 firewall 때문에 판정에 반영됐을 뿐이다. 수정 비용 1줄.

4. **[ND-D minor] `acceptance.md:332`에 `purchaseOrderApi.test.ts:23-35` 기존 단정 반전을 명시하라.** `plan.md:67,139`가 이미 지시하고 있어 실무 위험은 낮다.

5. **[ND-E nit] 인용 3건 정정** — `:1711-1714`→노트 수집 지점(`:1714` 선언 / `:1805` 가드 / `:1967` bulk_create를 분리 기재), `LineItemBulkStatusUpdateView.patch()` `:2540`→`:2556`, `research.md:159`의 `:472`→`:495`.

### 인정할 점

- **범위 확장 자체의 설계는 정확하다.** REQ-LCONF-304의 "소스 배열 1곳 수정으로 4개 렌더 사이트에 자동 전파" 주장은 내 독립 grep(`UnorderedItemsTab.tsx:207,294,344,495`)과 완전 일치하며, REQ-306/307이 복제하는 `damaged_exchange` 거부 분기(`:2516-2520`/`:2573-2577`)도 인용 범위까지 정확하다. REQ-LCONF-308의 "Daily Review는 두 PATCH 뷰를 거치지 않는다"는 핵심 주장도 코드 추적 결과 **참**이다(ND-A는 이 주장이 아니라 그 옆의 노트 관련 부가 주장에 관한 것이다). Exclusions 7번(모델 필드 미제거)과 REQ-306의 검사 순서 서술도 코드와 정합한다.
- **iteration 2가 요구한 판별력 보강이 전부 실현됐다.** AC-014b(정적 선언 단정)는 "프로젝트 기본값 폴백에 가려지는 선언 누락"을 잡는 유일한 수단이고, AC-012a/012b 쌍은 SQLite/실DB 양쪽에서 각각 판별력을 갖도록 선례를 정확히 재사용했으며, AC-302c는 판별력 0이던 진술을 실제로 실패 가능한 사실 검증으로 교체했다. 이들 모두 mutation을 코드에 대입해 실재를 확인했다.
- **인용 신뢰도가 3 iteration에 걸쳐 단조 개선됐다.** 이번 34건 재대조에서 조작 0건, 정량 주장 9건 전건 정확(iteration 1: 2건 오기, iteration 2: 2건 오기 → iteration 3: 0건).
- **자기정정 습관이 정착했다.** 감사가 지목하지 않은 REQ-101/103의 주어 문제, `yes24` 라벨 부재의 "알려진 제약" 승격, iteration 1 감사 원문 자체의 오류(ND1) 반박 — 모두 지시받지 않은 자체 검증의 산물이다.

### 최종 iteration 판단

3회 반복에도 **정체 결함은 0건**이며, 남은 결함은 전부 v1.2.0에서 새로 유입된 것이다. Tier 1 1건은 문서 5곳 문구 정정 + AC 1건 수정으로 해소 가능하며 설계 재검토를 요구하지 않는다. 따라서 **사용자 개입이 필요한 escalation 사안은 아니다** — 다만 ND-A(ii)의 "메모 공란 타출판사 행을 어떻게 다룰 것인가"는 제품 결정이므로, 작성자가 조치 1(제약으로 기록)이 아니라 조치 2(업로드 로직 변경)를 택하려 할 경우에만 오케스트레이터를 경유해 사용자 확인을 받을 것.

---

Verdict: FAIL
