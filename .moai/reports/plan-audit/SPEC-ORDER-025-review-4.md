# SPEC Review Report: SPEC-ORDER-025

Iteration: 4
Overall Score: 0.90

> Reasoning context ignored per M1 Context Isolation. 본 감사는 `.moai/specs/SPEC-ORDER-025/`의 문서 5종(spec.md v1.3.0, acceptance.md, plan.md, research.md, spec-compact.md)과 실제 코드베이스만을 근거로 수행했다. iteration 1~3 보고서는 **회귀 검증 목적으로만** 읽었으며 그 판정을 승계하지 않았다 — iteration 3 보고서 자체도 검증 대상으로 취급했고, 실제로 그 안의 인용 1건(`:2556`)이 틀렸음을 이번에 확인했다(아래 참조).
>
> **감사 원칙(사용자 지시)**: HISTORY의 "해소했다"는 근거가 아니다. 문서 본문이 실제로 바뀌었는지, 바뀐 내용이 **틀린 구현에서 실제로 실패하는지**, 모든 `file:line`이 실제 코드로 해소되는지를 명령으로 검증했다.
>
> **범위 확장에 대하여**: iteration 3→4 사이의 두 확장(① REQ-LCONF-309 — `note_type=="타출판사"` 행은 메모/Status 공란이어도 항상 `LineItemNote` 생성, ② 레거시 행 소급 백필은 명시적 제외)은 사용자 승인 사항이므로 존재 자체는 감사 대상이 아니다. 아래는 그 **정확성**만 감사한 결과다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  `grep -n "^- \*\*REQ-LCONF-"` 전수 추출 = **정의 36건, 각 1회**: `spec.md:50-64` 001~015(15), `:72-79` 101~108(8), `:87-90` 201~204(4), `:98-106` 301~309(9). 블록 내 갭 0, 중복 0, 3자리 제로 패딩 전항 일관. 신규 1건(309)은 R4 블록 마지막 번호에 연속 부착되어 기존 번호를 밀어내지 않았다(iteration 3의 35건 → 36건, 델타 +1이 정확히 REQ-309 1건).

- **[PASS] MP-2 EARS format compliance**
  36개 전항의 패턴 라벨과 절 구조를 1:1 대조했다. iteration 3이 지목한 `spec.md:76` REQ-LCONF-107의 `(Unwanted)` 오표기는 **해소됐다** — 현재 `spec.md:78`은 `(Event-Driven) WHEN 담당자가 어느 행의 발주처리 버튼을 클릭하면, THE 시스템은 …`으로, 형제 요구사항 REQ-LCONF-102(`:73`)와 동일 형태다. 주어 누락 0건(전항 "THE 시스템은"/"THEN 시스템은").

  신규 REQ-LCONF-309(`spec.md:106`)는 `WHILE UploadDailyReviewView가 '선택'='타출판사'인 행을 처리하는 중 …, IF … note가 None이면, THEN 시스템은 …`으로 **State-driven + Unwanted의 EARS complex 형식**이며, 라벨 `(State-Driven)`이 선행 WHILE 절과 일치한다. IF 절의 "메모/Status 셀이 비어 있음"은 실제로 예외적·바람직하지 않은 입력 조건이므로 iteration 3 ND-C(정상 트리거를 Unwanted로 오표기)와 구조가 다르다. 오표기 아님.

- **[PASS] MP-3 YAML frontmatter validity**
  `spec.md:1-11` 6개 필수 필드 전항 존재·타입 적합: `id: SPEC-ORDER-025`(`:2`, 패턴 일치), `version: 1.3.0`(`:3`, 1.2.0에서 정상 증가 — 범위 확장을 minor bump로 반영), `status: draft`(`:4`), `created_at: 2026-08-17`(`:5`, ISO 8601), `priority: High`(`:8`), `labels: [order, purchase, purchase-status, distributor, frontend, backend]`(`:10`, array).

- **[N/A] MP-4 Section 22 language neutrality**
  단일 스택(Django + React/TypeScript) SPEC이며 다국어 툴체인·LSP를 다루지 않는다. 자동 통과.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.90 | 0.75~1.0 사이 | iteration 3의 두 거짓 명제가 모두 **참인 명제로 교체**됐다. `spec.md:32`(문제 정의 3번)·`:42`(D5)·`:113`("알려진 제약")은 이제 "무조건"이 아니라 "`:1799`는 무조건, `:1805`의 `if note is not None:`은 조건부"라는 코드 사실을 정확히 서술하고, REQ-309 적용 **후에** 무조건이 된다는 시제를 구분한다 — 내가 `purchase_order_views.py:1798-1815`를 직접 읽어 대조한 결과 완전 일치. `spec.md:102` REQ-LCONF-305의 근거도 자기모순(REQ-302가 제거하는 배지)과 허구(주문상세 화면)를 버리고 "damaged_exchange 패턴 일관성 + 방어적 조치"로 교체됐다. 감점: `spec-compact.md`의 "무엇을 만들지 않는가" 2개 항목이 v1.2.0 문구 그대로 남아 **같은 파일 5번 항목과 정면 충돌**(ND-F), 기본 안내 문구의 리터럴이 규범 문서에 없음(ND-G). |
| Completeness | 0.90 | 0.75~1.0 사이 | 필수 섹션 전항 존재. Exclusions 7개 유지 + 3번이 REQ-309 예외만큼 정밀하게 수정됨(`spec.md:122` — "그 분기의 나머지 로직(…), `ConfirmOrderView` 전체는 이 예외에 포함되지 않으며 무변경"), 6번은 두 레거시 통로를 모두 열거하도록 확장. "알려진 제약" 3개 항목 중 2번이 이제 고아화 경로를 ①수동 PATCH ②메모 공란 업로드 **둘 다** 기재한다(iteration 3의 ND-A(b) 정확히 해소). 품질 게이트에 신규 행(`test_spec_024.py`/`test_daily_review_upload.py` 회귀)과 ND-D 반전 지시(`:342`)가 추가됐고, `plan.md` 파일 목록에 `test_daily_review_upload.py`가 MODIFY 대상으로 신규 등재(`:159`). 프론트 픽스처 파급(`UnorderedItemsTab.test.tsx:170,328,356`의 `auto_distributor: null` 3곳)도 `plan.md:100,165`가 정확히 잡고 있다 — 내 독립 grep과 완전 일치. 감점: ND-F. |
| Testability | 0.90 | 0.75~1.0 사이 | **iteration 3의 유일한 Tier 1 결함이 실제로 실행 가능해졌다.** 구 AC-308(무수정 코드에서 실패)은 308a(메모 공란)/308b(메모 있음)/309c(대조군)로 재작성됐고, 세 AC의 판별 mutation을 코드에 대입해 실재를 확인했다 — 308a는 `_make_daily_review_excel`을 `"note"` 키 없이 호출(헬퍼 기본값 `row.get("note","")`, `test_daily_review_upload.py:106`)해 `_str_or_none`(`excel_utils.py:760-764`)이 `None`을 만드는 경로를 정확히 재현하며, REQ-309 미구현 시 노트 0건으로 **반드시 실패**한다. 309c는 반대 방향(범위를 넘어 4개 CS 유형 전부에 적용하는 과잉 구현)을 잡는다 — 이 대조군이 없으면 REQ-309의 범위 한정 문구가 코드 리뷰에만 의존하게 된다. 생성된 노트가 실제로 타출판사 탭에 뜨는지도 확인했다: `LineItemNote.is_resolved` 기본값 `False`(`models.py:282`) → `LineItemNoteUnresolvedListView.get_queryset()`(`views.py:497-502`)의 `filter(is_resolved=False)` 통과 → `LineItemNotesPage.tsx:36`의 `note_type === '타출판사'` 필터가 픽업. 즉 REQ-309는 의도한 가시성을 실제로 달성한다. 감점: ND-G(기본 문구 리터럴 미고정 — 다만 "빈 문자열이 아님"이라는 이진 판정 기준은 명시되어 있어 판별 가능), AC-308a의 Given이 "대상 LineItem이 미발주 후보로 존재한다"는 전제를 재진술하지 않음(nit). |
| Traceability | 0.90 | 0.75~1.0 사이 | **36개 REQ 전항이 대응 AC를 가진다.** 신규 REQ-309 → AC-308a(공란 케이스)/308b(비공란 회귀)/309c(범위 한정)로 3중 대응하며, `acceptance.md:349` Definition of Done도 `301~309`로 갱신됐다. 역방향 확인 — 근거 REQ 없는 AC는 0건. 감점 사유는 iteration 2부터 이월된 단 1건: REQ-LCONF-202의 타입 절(`UnorderedItem`에서 `auto_distributor` 제거)에 전용 AC가 없다(ND-I). 다만 이번에 새로 확인한 바로는 실무 위험이 iteration 3 평가보다 **더 낮다** — `purchaseOrderApi.ts:12`의 필드가 optional이 아니므로, `plan.md:100`이 지시하는 3개 픽스처 라인 제거와 타입 제거는 서로를 강제한다(한쪽만 하면 `tsc`가 깨진다). |

---

## Citation Verification (독립 재검증)

**v1.3.0에서 신규·변경된 인용을 전수 재대조했다. 조작되거나 존재하지 않는 인용은 0건이다.**

| 인용 | 문서 위치 | 검증 결과 |
|------|-----------|-----------|
| `purchase_order_views.py:1780-1817` CS 분기 | spec.md:106, plan.md:60, research.md:189 | **정확** — `:1780` `if note_type and not distributor_code:`, `:1817` `continue` |
| `:1792` `if note_type == "타출판사":` / `:1799` `li.purchase_status = new_status` | spec.md:42/:105, research.md:191/196 | **2건 정확 일치** |
| `:1805` `if note is not None:` (조건 가드) | spec.md:32/:42/:113, plan.md:60/:154, research.md:199 | **정확 일치** — ND-A의 핵심 근거가 실제 코드와 일치 |
| `:1714` `pending_notes: list = []` / `:1967` `LineItemNote.objects.bulk_create(pending_notes)` | research.md:204, plan.md:5 | **2건 정확 일치** — ND-E 정정 확인(구 `:1711-1714` 단일 인용이 3개 지점으로 분리됨) |
| `LineItemBulkStatusUpdateView` `:2540`(class) / `:2557`(`def patch`) | plan.md:58 | **정확** — **iteration 3 감사 원문의 `:2556`이 1줄 틀렸고, 작성자가 재검증해 `:2557`로 바로잡은 것이 맞다.** 감사 산출물을 무비판 승계하지 않은 사례 |
| `excel_utils.py:881-884` note_idx 분기 / `:944` `note = _str_or_none(...)` / `:760-764` `_str_or_none` | spec.md:42, research.md:208-210 | **3건 정확 일치**(`:881` `if is_new_template:`, `:882` Status, `:884` 메모) |
| `excel_utils.py:656-660` `_NOTE_TYPE_STATUS_MAP`, `:660` `"타출판사": "other_publisher"` | spec.md:105, research.md:189 | **정확 일치** |
| `_DAMAGED_EXCHANGE_BLOCKED_MESSAGE` 거부 분기 `:2516-2520` / `:2573-2577` | spec.md:41, plan.md:57-58 | **2건 정확 일치**, `valid_choices` 검사(`:2511`/`:2568`) **직후** 배치라는 REQ-306의 순서 주장도 코드와 일치 |
| `test_daily_review_upload.py:77-116` 헬퍼, `:106` `row.get("note", "")` | research.md:262, acceptance.md:308 | **정확 일치** — AC-308a의 "헬퍼 기본값이 정확히 이 상황을 재현한다"는 주장 성립 |
| `test_spec_024.py` 타출판사 행 `"status"` 10건 / `LineItemNote\|note_type` 0건 | plan.md:84, research.md:259-260 | **양쪽 다 `grep -c`로 재실측 일치**(10 / 0). 타출판사 행 8개(`:96,117,136,150,193,217,235,253`) 전부 Status 또는 note에 비공백 값 명시 확인 → "깨지는 기존 테스트 없음" 주장 **참** |
| `test_daily_review_upload.py:779/:869` 타출판사 = legend 목록뿐 | research.md:261 | **정확** — `"selected": "타출판사"` 실제 행 0건 확인. 참고로 `:1153`의 `assert not LineItemNote...exists()`는 **파손/교환** 행이라 REQ-309와 무관(내가 별도로 확인) |
| `models.py` `is_resolved` default False, `views.py:489-502`/`:497-502`, `views.py:39` | acceptance.md:257-259 | **3건 정확 일치** |
| `purchaseOrderApi.ts:58-65`(OPTIONS) / `:62`(other_publisher) / `:36-50`(LABELS) / `:40` / `:43-49`(damaged 선례) | spec.md:41/:102, plan.md:56 | **5건 모두 정확 일치** |
| `PURCHASE_STATUS_OPTIONS` 렌더 사이트 4곳 `:207,294,344,495`와 각 사이트의 정체 | research.md:160/168, plan.md:56 | **독립 grep + 코드 판독 결과 완전 일치** — `:207` 보류/제외 일괄(`setExcludedBulkStatus`), `:294` 보류/제외 행별, `:344` 미발주 일괄(`.filter(o=>o.value!=='unordered')`), `:495` 미발주 행별. ND-E의 `:472`→`:495` 정정 확인 |
| `UnorderedItemsTab.tsx:283` 제외 사유 배지 / `:426` 자동추천 `<th>` / `:433` `colSpan={8}` / `:442` 행 onClick / `:449` stopPropagation | spec.md:102, plan.md:80 | **5건 모두 정확 일치**. 미발주 테이블 `<th>` 실측 **8개**(`:412,421,422,423,424,425,426,427`) → REQ-204의 "−1+1=8 유지" 산술 정확 |
| `OrderDetailPage.tsx`의 `purchase_status` 참조 0건 | spec.md:102, acceptance.md:286 | **정확**(`grep -c` = 0) — ND-B 정정의 근거 성립 |
| `UnorderedItemsTab.test.tsx:170,328,356` `auto_distributor: null` | plan.md:100/:165 | **3건 정확 일치** |
| `purchaseOrderApi.test.ts:23-35` "preserves all six existing options"(`:28`에 other_publisher) | acceptance.md:342, plan.md:67 | **정확 일치** — ND-D 정정 확인 |
| `settings/base.py:102-108`, `local.py:11`, `pytest.ini:8`, `test_spec_016.py:1012/1013-1027`·`:1030-1064` | acceptance.md:95/107/120, research.md:225-232 | **전건 정확**. `test_spec_016.py`를 research는 `:1012`(데코레이터), acceptance는 `:1013`(class)로 적었으나 둘 다 실재 라인이며 실무 오차 없음 |

---

## Regression Check (iteration 3 결함 5건)

| ID | Sev | 판정 | 근거(문서 본문 + 코드 대조) |
|----|-----|------|------|
| ND-A | critical | **RESOLVED** | (a) 거짓 명제가 5개 문서 전부에서 제거·조건화됨: `spec.md:32`(문제 정의 3번이 두 구멍을 순차 서술), `:42`(D5 신설 — `:1799` 무조건 / `:1805` 조건부를 코드 라인까지 명기), `:113`("알려진 제약"이 ①수동 PATCH ②메모 공란 업로드 **둘 다** 열거), `research.md:206-213`(§5-4가 "주장 2는 거짓이었다"로 명시적 정정), `spec-compact.md` 5번·핵심 결정. (b) **AC-LCONF-308의 실행 불가 결함 해소** — 308a/308b로 분할되어 blank/filled 두 경로를 각각 직접 검증하며, 이제 REQ-309 구현 시 참, 미구현 시 거짓이 되는 판별력 있는 단정이다. (c) 사용자 승인 하에 근본 통로 차단(REQ-309) + 소급 백필은 Exclusions 6번으로 명시적 제외. (d) 회귀 안전성을 문서가 주장만 하지 않고 근거(`test_spec_024.py` 10/0, `test_daily_review_upload.py` 0건)를 제시했고 **내 독립 재실측과 일치**한다 |
| ND-B | major | **RESOLVED** | `spec.md:102`가 "보류/제외 배지 + 주문상세 화면" 근거를 버리고 "damaged_exchange 패턴 일관성 + 원시 열거형 노출 방지"로 교체. 자기모순(REQ-302가 그 배지에서 행을 제거함)과 허구(OrderDetailPage가 `purchase_status`를 렌더하지 않음)를 **문서가 스스로 명시적으로 인정**하고 기록했다. `acceptance.md:286`의 mutation 서술도 동일하게 정정. 요구사항 자체와 AC-305의 판별력(라벨 존재 직접 단정)은 무변경 — 올바른 처리 |
| ND-C | minor | **RESOLVED** | `spec.md:78`이 `(Event-Driven) WHEN … THE 시스템은 …`으로 재작성. MP-2 firewall 통과 |
| ND-D | minor | **RESOLVED** | `acceptance.md:342`가 "`purchaseOrderApi.test.ts`(`:23-35`의 기존 "6개 옵션 유지" 단정을 5개로 반전 + AC-304/305 신규 케이스)"로 보완 — `plan.md:67,139`와 정합 |
| ND-E | nit×3 | **RESOLVED** | 3건 전부 정정되었고 그중 1건은 **감사 원문보다 정확하다**(`:2557` vs 내가 적었던 `:2556`) |

**정체(stagnation) 판정: 없음.** iteration 1의 13건, 2의 7건, 3의 5건이 각각 전부 해소되었거나 사용자 승인 범위 확장으로 흡수되었다. 4회 연속 동일하게 남은 결함은 0건이다. 점수는 0.62 → 0.71 → 0.78 → **0.90**으로 단조 개선됐다.

---

## Defects Found

### ND-F. `spec-compact.md` "무엇을 만들지 않는가" 2개 항목이 v1.2.0 문구 그대로 남아 같은 파일 5번 항목과 충돌 — Severity: **minor**

같은 파일 안에서:

> **[MODIFY, v1.3.0 신규]** Daily Review 업로드의 타출판사 분기가 메모/Status 셀 공란이어도 항상 노트를 생성하도록 좁게 수정(REQ-LCONF-309)

라고 적어놓고, 아래 "무엇을 만들지 않는가" 절에서는

> - `ConfirmOrderView`/`UploadDailyReviewView` 로직 변경 (무변경)
> - 레거시(**이 SPEC 이전 수동 지정**) `other_publisher` 행의 소급 백필

라고 한다. 첫 항목은 정면 모순이고(`spec.md:122` Exclusions 3번은 이미 "REQ-LCONF-309가 규정하는 좁은 예외 하나가 있다"로 수정됐다), 둘째 항목은 `spec.md:125` Exclusions 6번이 "(수동 PATCH 지정 **또는 메모 공란 Daily Review 업로드**로)"로 확장한 범위를 반영하지 못했다.

**실무 위험은 낮다** — `spec-compact.md`는 스스로 "(요약, 전체는 spec.md Exclusions)"라고 선언하고, 규범 문서인 `spec.md:122`와 작업 지시인 `plan.md:60-73`/`:154`/`:159`가 REQ-309 구현을 명시적·구체적으로 요구하며, 같은 파일의 "무엇을 만드는가" 5번이 먼저 읽힌다. 구현자가 이 한 줄 때문에 M2b의 REQ-309 작업을 건너뛸 개연성은 실질적으로 없다. 다만 문서 내 자기모순은 그 자체로 결함이다.

권고: 두 항목을 각각 "`ConfirmOrderView` 로직 변경(무변경) / `UploadDailyReviewView`는 REQ-LCONF-309의 좁은 예외 외 무변경", "레거시(수동 PATCH 지정 또는 메모 공란 업로드로 생성된) `other_publisher` 행의 소급 백필"로 고쳐라.

### ND-G. 기본 안내 문구의 리터럴이 규범 문서에 없는데 AC-308a가 "REQ-LCONF-309가 규정하는 기본 안내 문구"를 단정한다 — Severity: **minor**

`spec.md:106` REQ-LCONF-309는 `content`에 "기본 안내 문구를 사용한다"고만 하고 문자열을 고정하지 않는다. `acceptance.md:308` AC-308a는 "그 `content`는 **REQ-LCONF-309가 규정하는** 기본 안내 문구다(빈 문자열이 아님)"라고 적어, 존재하지 않는 규정을 참조한다. 리터럴은 `plan.md:73`에만 예시로 있다(`_OTHER_PUBLISHER_DEFAULT_NOTE`, 예: `"타출판사 확정 처리 (Daily Review 업로드, 메모 없음)"`).

**판별력은 유지된다** — 괄호 안의 "빈 문자열이 아님"이 이진 판정 기준이고, `LineItemNote` 1건 생성 + `note_type="타출판사"` + `assignee="CS"`라는 나머지 단정이 REQ-309의 실질(가시성 확보)을 전부 고정한다. 구현자가 상수를 정의하고 테스트가 그 상수를 참조하면 통과하며, 미구현 시에는 0건이라 반드시 실패한다. 다만 "규정한다"는 문구는 사실이 아니다.

권고: `spec.md:106`에 문자열을 고정하거나(권장 — `plan.md:73`의 예시를 그대로 승격), AC-308a의 문구를 "구현이 정의한 기본 안내 문구 상수와 일치하며 빈 문자열이 아니다"로 고쳐라.

### ND-H. AC 번호 `AC-LCONF-309c`에 대응하는 309a/309b가 없다 — Severity: **minor (nit)**

REQ-309의 검증은 308a/308b/309c 3건에 분산되어 있는데, 309c만 존재하고 309a·309b는 없다. 읽는 사람이 누락된 AC 2건을 찾게 만든다. 의도(308a/b가 REQ-309의 긍정 케이스, 309c가 범위 한정 대조군)는 `acceptance.md:312-314`의 서술로 복원 가능하므로 실무 영향은 없다.

권고: `309c` → `308c`로 개명하거나, 309a/309b/309c로 재배치하라.

### ND-I. REQ-LCONF-202의 타입 절에 전용 AC가 없다(iteration 2부터 이월) — Severity: **minor (nit)**

`UnorderedItem` 타입에서 `auto_distributor`를 제거하는 요구는 여전히 `tsc -b` 게이트(`acceptance.md:343`)에만 의존한다. 다만 이번에 확인한 바로는 **이월 3회에도 실무 위험이 오히려 더 낮다** — `purchaseOrderApi.ts:12`의 `auto_distributor: string | null`이 optional이 아니므로, `plan.md:100`이 지시하는 픽스처 3곳(`UnorderedItemsTab.test.tsx:170,328,356`) 제거와 타입 제거는 서로를 강제한다(한쪽만 하면 타입 에러). 정체 결함으로 분류하지 않는다(iteration 2·3에서도 numbered defect가 아니라 점수 근거였다).

### ND-J. `spec.md:102`의 "`PURCHASE_STATUS_LABELS`를 import하는 프론트 파일은 `UnorderedItemsTab.tsx` 하나뿐" — Severity: **minor (nit)**

`grep -rln` 결과 정의 파일(`purchaseOrderApi.ts`) 외에 `purchaseOrderApi.test.ts`도 import한다(AC-305가 바로 그 파일에서 라벨 존재를 단정하므로 필연적이다). 의도(화면 소비처는 하나뿐)는 명백하나 문장은 부정확하다. 권고: "화면 컴포넌트 중에는 … 하나뿐(테스트 파일 제외)".

---

## Chain-of-Verification Pass

1차 감사 후 2차 자기비판을 수행했다.

**"iteration 3 결함 5건을 전부 문서 본문에서 확인했는가, HISTORY 문구만 읽고 넘어가지 않았는가?"**
5건 전부에 대해 (a) 문서 본문의 변경 위치를 특정하고 (b) 그 내용을 코드에 대조했다. `spec.md:22`의 방대한 v1.3.0 HISTORY 항목은 근거로 채택하지 않았다. ND-A는 특히 5개 문서(`spec.md` 3곳, `research.md` §5-4/§5-9, `spec-compact.md` 2곳, `acceptance.md` 3곳, `plan.md` 3곳)를 개별 확인했다.

**"범위 확장(REQ-309)이 실제로 목표를 달성하는가 — 문서 주장이 아니라 코드 경로로?"**
가시성 체인을 끝까지 추적했다: 노트 생성(`:1805` 가드 완화) → `is_resolved` 기본값 `False`(`models.py:282`) → `LineItemNoteUnresolvedListView.get_queryset()`의 `filter(is_resolved=False)`(`views.py:497-502`) → `LineItemNotesPage.tsx:36`의 `note_type === '타출판사'` 필터. **네 단계 전부 성립한다.** 아울러 `LineItemNotesPage.tsx:41`이 CS/발주 탭에서 타출판사 노트를 `continue`로 배제하므로, 신규 노트가 다른 탭을 오염시키지도 않는다 — 문서가 주장하지 않은 부작용까지 확인했다.

**"REQ-309가 기존 테스트를 깨뜨리지 않는다는 문서 주장을 표본이 아니라 전수로 재검증했는가?"**
문서와 무관하게 독립 재실측했다: `grep -rn "타출판사" backend/order/tests/*.py`(실제 행 픽스처는 `test_spec_024.py` 8건뿐, 전부 Status 또는 note에 비공백 값), `grep -c '"status"' test_spec_024.py` = 10(문서와 일치), `grep -c "LineItemNote\|note_type" test_spec_024.py` = 0(일치), `test_daily_review_upload.py`의 `:779/:869`는 legend 목록. **추가로 문서가 언급하지 않은 `test_daily_review_upload.py:1153` `assert not LineItemNote.objects.filter(line_item=li).exists()`를 발견해 직접 열어봤다** — 파손/교환(`"selected": "파손/교환"`) 행이라 REQ-309의 타출판사 한정 분기와 무관함을 확인했다. 즉 "깨지는 기존 테스트 0건" 주장은 참이며, 이는 내가 놓칠 뻔한 유일한 반례 후보였다.

**"신규·재작성 AC의 판별 mutation을 문서 문구로만 읽지 않고 실제 코드에 대입했는가?"**
AC-308a/308b/309c 3건에 대해 양방향으로 대입했다 — 과소 구현(가드 유지) → 308a 0건 실패, 과잉 구현(4개 CS 유형 전부 적용) → 309c 0건 단정 실패, 정상 구현 → 3건 모두 통과. 특히 iteration 3의 결함(무수정 코드에서 실패)이 재발하지 않는지 확인하기 위해 **308b가 REQ-309 없이도 통과하는지**를 되물었고, `test_spec_024.py:136`(`"note": "아가페"`, 레거시 헬퍼)이 현재 통과 중인 동일 경로임을 확인해 회귀 AC로서 정확함을 검증했다.

**"모든 REQ를 읽었는가, 신규 1건만 보고 기존 35건을 표본 처리하지 않았는가?"**
36개 정의를 전수 추출해 패턴 라벨·주어·절 구조를 개별 검토했다. REQ-309의 `WHILE … IF … THEN` 복합 형식을 iteration 1(REQ-203)·iteration 3(REQ-107)의 오표기 선례와 대조한 결과, 두 선례는 라벨과 절이 **불일치**했던 반면 REQ-309는 라벨(State-Driven)이 선행 WHILE 절과 **일치**하고 IF 절이 실제 예외 조건이므로 동일 기준으로 FAIL이 아니다. 감사 기준의 일관성을 위해 이 판단 근거를 명시적으로 남긴다.

**"요구사항 간·문서 간 모순을 찾았는가?"**
**2차 패스에서 ND-F를 발견했다** — 1차 패스에서는 `spec.md` Exclusions 3번이 수정된 것만 확인하고 넘어갔으나, "같은 예외가 4개 문서 전부에 전파됐는가"를 되물어 `spec-compact.md`의 요약 절 2개가 v1.2.0 문구 그대로임을 포착했다. 나머지 조합(spec↔acceptance, spec↔plan, plan↔acceptance)은 REQ-309 관련 전 항목에서 일치했다.

**"정량 주장을 표본이 아니라 전수로 대조했는가?"**
정량 주장 8건(REQ 36건, 렌더 사이트 4곳, `test_spec_024` status 10/note 0, `<th>` 8개, `colSpan` 8, `auto_distributor` 픽스처 3곳, LABELS import 파일 수, Exclusions 7개)을 명령으로 재측정했다. **전건 정확**하며, 유일한 부정확은 ND-J(import 파일 수를 "1개"라 한 것 — 테스트 파일 누락)뿐이다. iteration 1(2건 오기) → 2(2건) → 3(0건) → 4(nit 1건) 추세 유지.

**신규 발견 요약**: 2차 패스에서 ND-F(minor)를 추가 발견했다. 1차 패스만으로는 ND-G/H/I/J만 남기고 동일한 PASS 결론에 도달했을 것이다 — ND-F는 판정을 바꾸지 않지만 기록한다.

---

## Recommendation

**PASS.** 근거를 must-pass 기준별로 제시한다.

- **MP-1**: `spec.md:50-64/72-79/87-90/98-106`에서 36개 REQ 전수 추출 — 갭 0, 중복 0, 패딩 일관. 신규 REQ-309는 R4 블록 말미 연속 부착.
- **MP-2**: 36개 전항의 라벨·절 구조 1:1 대조 완료. iteration 3의 유일한 오표기(REQ-107)가 `spec.md:78`에서 `(Event-Driven) WHEN … THE 시스템은 …`으로 해소됐고, 신규 REQ-309(`spec.md:106`)는 라벨과 선행 절이 일치하는 적법한 EARS complex다.
- **MP-3**: `spec.md:1-11` 6개 필수 필드 전항 존재·타입 적합, `version: 1.3.0`으로 정상 증가.
- **MP-4**: N/A (단일 스택).

**두 범위 확장의 정확성 판정:**

1. **REQ-LCONF-309(메모 공란 시 노트 무조건 생성)는 정확하다.** 문제 진단(`:1799` 무조건 / `:1805` 조건부 / `note`는 별도 컬럼 / `_str_or_none`이 공백을 `None`으로 정규화)이 코드와 완전히 일치하고, 처방(타출판사 분기 한정, `note_type`/`assignee` 유지)이 가시성 체인 4단계를 실제로 복원하며, 범위 한정이 대조군 AC(309c)로 고정되어 있고, 기존 테스트 무파손 주장이 내 독립 전수 재실측과 일치한다. `plan.md:60-73`의 구현 스케치(`effective_note` 도입)는 기존 분기 구조를 최소 침습으로 확장하며 다른 3개 CS 유형을 자동 보존한다 — Scope Discipline 준수.
2. **레거시 행 소급 백필 제외는 정확하게 문서화됐다.** Exclusions 6번(`spec.md:125`)이 두 생성 통로를 모두 열거하고, "알려진 제약" 2번(`:113`)이 그 결과(주문상세에서만 조회 가능)를 정확히 기술하며, `project_daily_review_reupload_noop` 메모리의 "기존 95건 백필 안 하기로 확정" 선례와 동일한 결정 패턴임을 명시한다. 감춰진 사각지대가 아니라 **기록된 수용 위험**이다.

**남은 결함 5건(ND-F~ND-J)은 전부 문서 정리 수준이며, 유능한 구현자를 틀린 구현으로 이끌지 않는다.** 판정 근거를 명시한다: (a) ND-F의 모순은 같은 파일의 상위 항목과 규범 문서(`spec.md:122`)·작업 지시(`plan.md:60-73,154,159`) 3곳이 반대 방향으로 명확히 지시하므로 실행에 영향이 없다. (b) ND-G는 "빈 문자열이 아님"이라는 이진 기준이 병기되어 AC의 판별력이 유지된다. (c) ND-H/I/J는 순수 표기·정확성 nit이다. **어느 것도 잘못된 동작을 배포시키거나 판정 불가능한 AC를 만들지 않는다.**

권고 조치(차단 아님, 구현 세션 중 또는 sync 단계에서 처리 가능):
1. `spec-compact.md`의 "무엇을 만들지 않는가" 2개 항목을 v1.3.0 범위에 맞게 갱신(ND-F).
2. `spec.md:106`에 기본 안내 문구 리터럴을 고정하고 `acceptance.md:308`의 참조를 맞춰라(ND-G) — `plan.md:73`의 상수명·예시를 그대로 승격하면 된다.
3. `AC-LCONF-309c` → `308c` 개명(ND-H), `spec.md:102`의 "하나뿐" 문구에 테스트 파일 예외 부기(ND-J).

**최종 판단**: 4회 반복에 걸쳐 정체 결함 0건, 점수 0.62 → 0.71 → 0.78 → 0.90 단조 개선, 인용 조작 0건(4회 연속), 그리고 이번에는 작성자가 감사 원문의 오류(`:2556`)까지 코드로 검증해 바로잡았다. iteration 3이 지목한 유일한 Tier 1 결함(실행 불가능한 AC-308)은 실제로 실행 가능해졌고, 그 해소 방식이 근본 원인(조건부 노트 생성)까지 제거한다. 구현 착수 승인에 필요한 품질 기준을 충족한다.

---

Verdict: PASS
