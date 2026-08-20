# SPEC Review Report: SPEC-ORDER-029

Iteration: 2/3
Verdict: **FAIL**
Overall Score: **0.71**
`/moai run` 진입: **불가. blocking 결함 5건 (D1~D5).**

> **M1 Context Isolation**: 프롬프트가 전달한 저자 측 배경 서술(v0.1.0 폐기 경위, "아키텍처가 교체됐다"는 프레이밍)은 감사 범위를 정하는 데만 썼다. 판정 근거는 `.moai/specs/SPEC-ORDER-029/{spec,plan,acceptance}.md`의 실제 텍스트와 이 세션에서 직접 연 저장소 소스(`shopify_orders.py`, `models.py`, `scripts/sync_orders.bat`, `backend/order/tests/`, `backend/order/migrations/`)다. 프롬프트가 "이 세션에서 프로덕션 직접 검증"으로 명시한 수치(776/25, 3,910, 3,109, 1,170/21, 58/6/52, 79/51, `ids=` 250/250 반환 + `Link` 헤더 없음)는 재검증하지 않고 기준값으로 채택했다 — 다만 **그 수치로부터 SPEC이 도출한 파생값**은 전부 재도출했고, 거기서 결함 1건이 나왔다(D7).
>
> 프롬프트 지시대로 v0.2.0을 **diff가 아니라 신규 문서로** 감사했다. 아키텍처(후보 집합 + `ids=`)는 이번이 최초 감사다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ 번호 일관성** — grep 전수 추출로 확인: `spec.md`의 `**REQ-CANC-` 헤더 20개, 추출된 고유 ID `REQ-CANC-001`~`REQ-CANC-020` 연속. 결번 0, 중복 0, 3자리 패딩 일관. `spec.md:242`의 자기 선언("001 ~ 020, 20개, 결번 없음")과 일치. AC도 동일하게 `## AC-CANC-001`~`019` 연속(`acceptance.md` 헤더 19개).
- **[PASS] MP-2 EARS 형식 준수** — 20개 REQ 전수 확인. 전부 `shall`/`shall not` 조동사 + 주어 명시된 완전한 규범문이다: `spec.md:112`(001 Ubiquitous), `:118`(003 `**When**…shall`), `:137`(008 `**While**…shall`), `:153`(012 `**If**…**then**…shall not`), `:159`(014 `**While**…**when**…shall`), `:167`(016 `WHERE…shall not`), `:177,180,183`(018/019/020 부정형 Ubiquitous — v0.1.0 D9에서 지적된 `(Unwanted)` 오라벨이 올바르게 정정됨). **라벨 오류 1건(D11)** — REQ-CANC-010(`:144-145`)은 `(Ubiquitous)`로 라벨됐으나 "후보 집합이 250건을 초과하면"이라는 조건절을 갖는 State-Driven 문장이다. 문장 자체는 EARS 정합이므로 MP-2 FAIL 사유가 아니다.
- **[PASS] MP-3 YAML frontmatter 유효성** — `spec.md:1-11`: `id: SPEC-ORDER-029` ✓(string), `version: 0.2.0` ✓(점 2개 → string), `status: planned` ✓, `created_at: 2026-08-19` ✓(ISO date), `priority: High` ✓, `labels: [order, shopify, sync, cancellation, closure, backend]` ✓(배열). 6개 필수 필드 전부 존재, 타입 정합.
- **[N/A] MP-4 언어 중립성** — 단일 언어(Python/Django) 프로젝트 SPEC. 자동 통과.

**must-pass firewall 미발동.** 아래 blocking 결함 5건은 must-pass와 독립적으로 `/moai run` 진입을 막는다.

---

## Category Scores

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.70 | 0.50–0.75 | §1.1/§4 D1~D6이 재설계 논거를 명확히 서술하고 각 결정이 REQ로 연결된다 ✓. `plan.md` §1.1 코드 스케치가 실제 코드 계약과 일치한다 ✓. 감점: **가정 A1의 출처가 사실과 다르다**(D4 — `spec.md:51,86`, `plan.md:7`), **`spec.md:214`의 "기계적 대조, 불일치 0건" 선언이 거짓**이며 같은 문장이 20행 표를 "25개 매핑 행"이라 부른다(D3), 비용 수치가 스토어별 청킹을 무시하고 합산 모집단에서 도출됐다(D7) |
| Completeness | 0.65 | 0.50–0.75 | HISTORY/문제정의/§1.1 메커니즘/Environment/Assumptions(A1~A5)/설계결정(D1~D6)/REQ 20/추적표/Exclusions 7건(전부 구체)/제약 C1~C4 전 섹션 존재 ✓. 감점: **후보 집합 생애주기의 최대 사각지대(종료 후 취소)가 어디에도 서술되지 않음**(D1), **영구 실패 청크·Shopify 미반환 id에 대한 제약 항목 부재**(D6 — v0.1.0의 C3에 해당하는 항목이 §8에서 사라졌다), `chunk_failures`가 실패한 id를 기록하지 않아 운영 진단 불가(D6) |
| Testability | 0.75 | 0.75 | 19개 AC 중 18개가 진짜 판별자다 — v0.1.0 D4의 공허 통과 4건이 전부 해소됐고(AC-011/017/019에 양성 증거 단정 추가, `acceptance.md:216,308,338`), 역방향 [HARD] 규약이 `:13`에 신설됐다 ✓. 감점: **AC-CANC-005가 자신이 잡는다고 선언한 M5를 실제로 잡지 못한다**(D2 — 청크 레벨 `except Exception`이 `KeyError`를 삼킨다), `fields=`·`limit=` 파라미터를 단정하는 AC가 여전히 0개(D5, v0.1.0 D6의 미해결 잔여분) |
| Traceability | 0.75 | 0.75 | **`spec.md` §6의 20행과 `acceptance.md`의 19개 `Traces:` 선언을 grep 추출 후 양방향 전건 대조 — 불일치 0건** ✓(아래 §독립 검증 참조). `plan.md` §4 위험표 R1~R14의 AC 참조도 14행 전건 대조 결과 전부 정확 ✓ (v0.1.0 D3의 +1 시프트 완전 해소). 감점: **AC-CANC-011의 소속 테스트 파일이 4곳에서 서로 모순**(D3), REQ-CANC-001의 `fields=` 규범 절반이 미커버인데 §6은 커버로 선언 — `spec.md:212`가 스스로 [HARD]로 금지한 형태(D5) |

---

## Defects Found

### BLOCKING

---

**D1. 후보 집합 정의가 "첫 상태 전이"에서 관측을 종료시킨다 — 종료(보관) 후에 취소된 주문은 영구히 감지되지 않는다. v0.1.0의 `status=cancelled` 스윕에는 없던 사각지대이며, SPEC 어디에도 서술이 없다.** — Severity: **major / blocking**

후보 집합은 `cancelled_at IS NULL AND closed_at IS NULL`이다(REQ-CANC-004, `spec.md:123`; `plan.md:78-82`). 생애주기를 끝까지 돌리면:

| 단계 | 로컬 상태 | 후보 집합 |
|---|---|---|
| 1. 신규 주문 생성(`sync_store`) | (NULL, NULL) | **포함** |
| 2. 계속 open → `ids=` 응답 (NULL, NULL) → 변경 없음 | (NULL, NULL) | 포함(매 사이클 재조회) |
| 3-a. Shopify에서 취소 | (T, T′) 둘 다 기록 | 이탈 ✓ |
| 3-b. Shopify에서 **보관(archive)** | (NULL, T) | **이탈** |
| 4. 3-b 이후 그 주문이 **취소됨** | (NULL, T) 그대로 | **영구 미감지** |

4단계가 사각지대다. 그 주문은 후보 집합에서 이미 빠졌으므로 이 SPEC의 조회 대상이 아니고, `status=open` 피드에도 없으므로 `sync_store()`(`shopify_orders.py:388`)도 가져오지 않는다. 기존 코드에서 그 주문을 다시 만질 수 있는 유일한 경로는 `OrderResyncView`(`views.py:408`) — **사람이 콕 집어 눌러야만** 동작하는 경로이며, 이는 `spec.md:26-30`이 이 SPEC을 만드는 이유로 든 바로 그 문제다.

**v0.1.0에는 이 사각지대가 없었다.** `status=cancelled` 목록 스윕은 로컬 상태와 무관하게 Shopify가 취소로 분류한 전체를 열거하므로 4단계를 반드시 잡는다. 즉 **아키텍처 교체가 감지 범위의 회귀를 도입했고, SPEC은 이 트레이드오프를 인지하지 못했다.** `spec.md:53`은 후보 집합을 "로컬에서 아직 취소·종료 여부를 모르는 주문"이라 정의하는데, 실제 의미는 "**아직 아무 상태 전이도 관측하지 못한** 주문"이다 — 이 미묘한 차이가 문제 정의를 조용히 축소시킨다.

부수적으로 같은 뿌리에서 나오는 두 케이스도 미서술이다:
- **Shopify에서 삭제된 주문**: `ids=` 응답이 그냥 누락한다(코드는 `records`를 순회하므로 예외는 없다 — `plan.md:129`). 그 주문은 두 필드가 영원히 NULL이라 **매 사이클 영구 재조회**된다. 후보 집합이 수렴하지 않는 유일한 실재 케이스다.
- `scanned`가 요청 id 수보다 작아도 그 차이를 보고·감지하는 요구가 없다(`plan.md:118` `scanned += len(records)`).

**어떤 AC도 이것을 다루지 않는다** — 19개 변이표(`acceptance.md:21-39`)에 상태 전이 순서에 관한 변이가 없다.

**수정** (셋 중 하나를 명시적으로 선택하고 근거를 기록할 것):
1. 후보 집합을 `cancelled_at IS NULL`만으로 정의한다 — 종료된 주문도 계속 조회되어 사각지대가 사라진다. 대가: 후보 집합이 로컬 전체 크기로 유지되어 사이클당 호출이 오늘 기준 17회로 고정되고 **로컬 테이블과 함께 선형 증가**한다(§1.1의 "4회" 주장 폐기 필요).
2. 현행 정의를 유지하되, **Exclusions에 "종료 후 취소는 감지하지 않는다"를 명시**하고 §8에 제약으로 올린다. 이 경우 `spec.md:53`의 후보 집합 서술을 "아직 어떤 상태 전이도 관측되지 않은 주문"으로 정정하라.
3. 절충: 감지 잡은 현행 정의(4회/사이클), 백필 커맨드에 `--include-closed` 인자를 두어 `cancelled_at IS NULL`만으로 주기적 전수 재확인을 가능하게 한다.
그리고 **Shopify 미반환 id**에 대해: `candidates`와 `scanned`의 차이를 stdout에 보고하는 요구를 REQ에 추가하고, §8에 "Shopify에서 삭제된 주문은 후보 집합에 영구 잔류한다"를 제약으로 신설하라.

---

**D2. AC-CANC-005는 자신이 "단독으로" 잡는다고 선언한 변이 M5를 실제로 잡지 못한다 — 청크 레벨 `except Exception`이 `KeyError`를 삼켜 세 단정이 전부 통과한다.** — Severity: **major / blocking**

`acceptance.md:124` Then:
> 예외가 발생하지 않고, 반환된 `changed`에 90005가 포함되지 않으며, `Order.objects.filter(shopify_order_id=90005).exists()`는 여전히 `False`.

`:126` 판별력 주장:
> `existing[r["id"]]`처럼 직접 인덱싱하는 변이(M5)는 `KeyError`로 잡힌다.

**틀렸다.** `plan.md:112-153`의 구조를 보면 `for r in records:` 루프는 `with transaction.atomic():` 안이고, 그 전체가 청크 루프의 `try:` 안이다:

```python
for chunk in _chunked(shopify_order_ids, chunk_size):
    try:
        ...
        for r in records:
            order = existing.get(r["id"])      # ← 변이: existing[r["id"]]
            ...
    except Exception as exc:                    # plan.md:151
        chunk_failures.append(str(exc))
        continue
```

변이를 대입하면 `KeyError`가 발생하지만 `:151`의 `except Exception`이 즉시 삼켜 `chunk_failures`에 문자열로 쌓고 `continue`한다. 함수는 정상 반환한다. 그 결과:

| AC-005 단정 | 변이 하에서 |
|---|---|
| 예외가 발생하지 않는다 | **참** (삼켜졌다) |
| `changed`에 90005 미포함 | **참** (`changed`는 빈 리스트) |
| `Order...exists() is False` | **참** (애초에 없다) |

→ **세 단정 전부 통과. M5는 영구 미커버다.** 변이표(`acceptance.md:25`)와 추적표(`:352`)가 M5를 "AC-CANC-005 (단독)"으로 선언했으므로, 이 AC가 판별력을 잃으면 대체 판별자가 없다.

같은 문제의 다른 얼굴: **AC-CANC-005는 19개 AC 중 유일하게 양성 증거가 하나도 없는 전면 부정형 AC다.** `acceptance.md:13`이 v0.2.0에서 신설한 [HARD] 역방향 규약("'아무것도 바뀌지 않아야 한다'를 검증하는 AC는 다른 무언가가 실제로 처리됐다는 양성 증거를 반드시 함께 요구한다")이 AC-011/017/019에만 적용되고 **AC-005에는 적용되지 않았다** — `:13`과 `:372`가 대상 AC를 "AC-CANC-011/017/019"로 열거하며 스스로 범위를 v0.1.0 지적 지점으로 한정했기 때문이다. 프롬프트가 "규약이 실제로 전부에 적용됐는지 확인하라"고 지목한 지점이 정확히 여기다.

**수정**: AC-CANC-005의 Then에 두 단정을 추가하라 —
- "**그리고** 반환값의 `chunk_failures`가 빈 리스트다(스킵이 예외 삼킴으로 위장되지 않았음을 증명)",
- "**그리고** 같은 청크에 넣은 로컬 존재 주문(예: 90005b)의 `cancelled_at`이 실제로 갱신됐다(청크가 끝까지 처리됐다는 양성 증거)".
아울러 `:13`·`:372`의 열거를 "이 문서의 모든 부정형 단정"으로 일반화하라 — 지금처럼 AC 번호를 열거하면 다음 개정에서 같은 누락이 반복된다.

---

**D3. `spec.md:214`가 선언한 "기계적 대조, 불일치 0건"은 거짓이다 — AC-CANC-011의 소속 테스트 파일이 4곳에서 서로 모순되며, 선언 문장 자체가 20행 표를 "25개 매핑 행"이라 부른다.** — Severity: **major / blocking**

`spec.md:214`:
> **[프로세스 확인, v0.2.0]** 위 표의 **25개 매핑 행**과 `acceptance.md`의 19개 AC 각각의 `Traces:` 선언을 기계적으로(grep 기반) 양방향 대조했다 — 불일치 0건. `plan.md`의 위험표(§4)·마일스톤(§2) AC 참조도 동일하게 대조했다 — **불일치 0건**.

두 가지가 틀렸다.

**(a) 표는 20행이다.** `spec.md:191-210`을 세면 REQ-CANC-001~020으로 정확히 20행이다. "25개"는 v0.1.0의 REQ 개수다 — 즉 이 문장은 grep 결과를 옮긴 것이 아니라 손으로 쓰였고, 그 과정에서 옛 숫자가 남았다.

**(b) 마일스톤 대조는 실제로 불일치를 갖고 있다.** AC-CANC-011이 어느 파일에 속하는지가 4곳에서 갈린다:

| 위치 | 주장 |
|---|---|
| `acceptance.md:3` | `test_spec_029.py` = AC-CANC-**001~011** |
| `plan.md:359,368` (M1) | `test_spec_029.py` = AC-CANC-**001~011** ("…필드 기록, **워터마크 무변경**") |
| `acceptance.md:205` 섹션 헤더 | "## 감지 커맨드 AC (`test_sync_order_cancellations_command.py`)" **바로 아래에 AC-CANC-011**(`:207`) |
| `acceptance.md:400-401` (DoD) | `test_spec_029.py` = AC-**001~010**, `test_sync_order_cancellations_command.py` = AC-**011~015** |

AC-CANC-011은 `[COMMAND]` 태그를 달고 있고(`:207`) When 절이 `call_command("sync_order_cancellations", ...)`(`:214`)이므로 **커맨드 테스트 파일이 맞다** — 즉 `acceptance.md:3`과 `plan.md` M1이 틀린 쪽이다. 이는 v0.1.0 D3의 후반부(§2 마일스톤 파일↔AC 배정 드리프트)와 **동일 부류의 재발**이며, 하필 그 재발을 "0건"이라 선언한 문장 바로 옆에서 일어났다.

프롬프트의 지시("주장된 자기 점검이 불일치를 못 잡았다면 그 자체가 결함이다")에 정확히 해당한다. 참고로 §6 추적표↔`Traces:` 대조는 **실제로 통과했다**(아래 §독립 검증) — 즉 선언의 절반은 참이고 절반은 거짓이며, 그래서 더 위험하다(다음 감사가 선언을 그대로 신뢰할 유인을 만든다).

**수정**:
1. `acceptance.md:3`과 `plan.md:359,368`(M1)의 범위를 **AC-CANC-001~010**으로, `plan.md:372,375`(M2)를 **AC-CANC-011~015**로 정정하라. M1의 설명에서 "워터마크 무변경"을 제거하라.
2. `spec.md:214`의 "25개 매핑 행"을 "20개"로 정정하라.
3. "불일치 0건" 선언을 유지하려면 **실행한 grep 명령과 그 출력**을 각주에 그대로 붙여라. 붙일 수 없으면 선언을 삭제하라 — 검증 불가능한 자기 인증은 감사 대상 문서에서 음의 가치를 갖는다.

---

**D4. 이 아키텍처 전체가 얹혀 있는 가정 A1의 출처가 사실과 다르다 — review-1은 `ids=`를 한 번도 언급하지 않는다.** — Severity: **major / blocking**

세 곳이 같은 주장을 한다:
- `spec.md:49` — "### 1.1 핵심 메커니즘 — `ids=` 파라미터 (v0.2.0, **plan-auditor D2 지시로 확인**)"
- `spec.md:51` — "**plan-auditor가 프로덕션에서 직접 확인했다**(이 세션에서 재검증하지 않고 채택, 가정 A1)"
- `spec.md:86` (A1 근거란) — "plan-auditor가 프로덕션에서 직접 확인(**review-1, D2 fix guidance**)"
- `plan.md:7` — "**감사가 프로덕션에서 직접 확인한** `ids=` 파라미터 메커니즘으로 아키텍처를 교체한다"

`.moai/reports/plan-audit/SPEC-ORDER-029-review-1.md` 전문을 다시 읽었다. **`ids=`라는 문자열이 한 번도 등장하지 않는다.** D2의 수정 지시(`:109-112`)는 정반대다 — "`status=closed&limit=1&fields=id`로 양쪽의 실제 페이지 수를 프로덕션에서 측정하고 그 값을 §1에 기록하라". review-1이 지시한 것은 **`status=closed` 규모 측정**이지 `ids=` 메커니즘 확인이 아니며, review-1은 `ids=` 프로덕션 조회를 수행한 적이 없다.

사실 자체는 참이다(사용자가 이 세션에서 프로덕션에서 직접 확인: 250개 요청 → 250개 반환, 두 타임스탬프 채워짐, `Link` 헤더 없음). 그러나 **문서에 기록된 출처가 틀렸고, A1은 동시에 "이 세션에서 재검증하지 않고 그대로 채택한다"고 선언한다**(`spec.md:86`). 두 문장을 합치면, 이 SPEC 전체의 토대가 되는 사실에 대해 **추적 가능한 검증 기록이 문서상 어디에도 존재하지 않는 상태**가 된다 — 존재하지 않는 문서를 가리키면서 재검증을 면제하고 있다.

이 저장소에는 이미 확립된 결함 부류다(auto-memory: "SPEC 문서의 file:line 인용 검증 필수 — manager-docs·manager-spec 모두 존재하지 않는 경로를 지어낸 사례 2건"). 이번엔 파일 경로가 아니라 **감사 보고서의 내용**을 지어냈고, 지어낸 대상이 하필 아키텍처 전체의 단일 근거다.

**수정**: `spec.md:49,51,86`과 `plan.md:7`의 귀속을 실제 출처로 정정하라 — "사용자가 2026-08-19 세션에서 프로덕션 직접 조회로 확인. 요청: `orders.json?ids=<250개 쉼표구분>&status=any&limit=250&fields=id,cancelled_at,closed_at`, 결과: 요청 250건 중 250건 반환, `cancelled_at`/`closed_at` 양쪽 채워짐, `Link` 헤더 없음." A1의 "재검증하지 않고 채택" 문구는 그대로 두어도 좋으나, 무엇을 근거로 면제하는지가 검증 가능해야 한다.

---

**D5. `fields=` 파라미터를 단정하는 AC가 여전히 0개인데 §6은 REQ-CANC-001을 커버로 선언한다 — `spec.md:212`가 스스로 [HARD]로 금지한 형태이며, review-1 D6의 미해결 잔여분이다.** — Severity: **major / blocking (carry-forward)**

REQ-CANC-001(`spec.md:112`)의 규범 내용은 세 조각이다: (a) `ids=<최대 250개>`, (b) `status=any`, (c) `fields=id,cancelled_at,closed_at`.

§6(`spec.md:191`)은 REQ-CANC-001 → AC-CANC-001, 002, 006으로 매핑한다. 실제 판별력을 대조하면:

| AC | 요청 문자열 단정 | (a) | (b) | (c) |
|---|---|---|---|---|
| AC-001(`:64`) | 없음(결과값만) | ✗ | ✗ | ✗ |
| AC-002(`:79`) | 없음(결과값만) | ✗ | ✗ | ✗ |
| AC-006(`:139`) | `status=any`와 `ids=90006,90007` | ✓ | ✓ | **✗** |

→ **`fields=`를 누락하거나 오타내는 변이를 잡는 AC가 0개다.** `limit=250`도 동일하게 미커버다. `_get_with_headers`가 모킹되므로 응답은 URL과 무관하게 픽스처가 정하며, 따라서 `fields=` 누락 변이는 19개 AC를 전부 통과한다(프로덕션에서는 3,904건 × 전체 페이로드를 끌어와 응답 크기가 수십 배가 되지만 기능은 통과한다).

`spec.md:212`가 바로 위에서 [HARD]로 규정한다:
> REQ가 그 위반을 실제로 검출할 수 없는 AC에 매핑되어 있으면 그 REQ는 미커버다.

자기 규약 위반이다. review-1 D6은 두 부분이었고 — "`status=`를 단정하는 AC가 0개" + "첫 페이지의 `fields=`를 단정하는 AC가 없다" — **앞부분만 해소됐다**(AC-006 신설 ✓). 이전 회차 미해결분이므로 retry contract상 자동 FAIL 사유다.

**수정**: AC-CANC-006의 Then에 한 줄 추가 — "**그리고** 같은 경로 문자열에 `fields=id,cancelled_at,closed_at`과 `limit=250`이 포함된다". 판별력 문단에도 대응 변이(필드 제한 누락)를 명시하라. 비용은 1줄이고, 미반영 시 이 변이는 영구 미커버로 남는다.

---

### MAJOR

**D6. 영구 실패 청크가 같은 249건을 무기한 볼모로 잡으며, `chunk_failures`가 실패한 id를 기록하지 않아 운영 진단이 불가능하다. Exclusions #5의 "자연히 수렴한다"는 주장은 일시적 실패에만 참이다.** — Severity: major

`plan.md:151-153`:
```python
except Exception as exc:
    chunk_failures.append(str(exc))
    continue
```
기록되는 것은 예외 문자열뿐이다. **어느 주문이 조정되지 못했는지가 어디에도 남지 않는다.** 커맨드 레벨 출력도 개수만 보고한다(`plan.md:220` `f"[{store_type}] {len(result['chunk_failures'])} chunk(s) failed"`).

`open_candidate_order_ids()`(`plan.md:78-82`)에는 `order_by()`가 없다 — MySQL/InnoDB에서 사실상 PK 순으로 안정적으로 나오므로, 청크 구성이 매 사이클 거의 동일하다. 따라서 한 id가 지속적으로 400/422를 유발하면 **그 청크의 나머지 최대 249건이 매 사이클 함께 실패**하고, 두 필드는 NULL로 남아 후보 집합에 영구 잔류하며, 커맨드는 5분마다 `CommandError`로 종료한다. 운영자가 보는 것은 "1 chunk(s) failed" 한 줄뿐이라 원인 id를 특정할 방법이 없다.

`spec.md:224`(Exclusions #5)는 이렇게 단정한다:
> 429가 실제로 발생해도 그 청크만 실패로 계상되고 다음 실행에서 그 주문은 여전히 후보 집합에 남아 있으므로 재시도된다 — 데이터 유실이나 무한 반복 없이 **자연히 수렴한다**.

429(일시적)에 대해서는 참이다. 영구적 실패에 대해서는 거짓이며, SPEC은 두 경우를 구분하지 않는다. v0.1.0에는 개별 레코드 poison을 다루는 제약(C3)이 있었으나 **v0.2.0 §8에서 사라졌고 대체 항목이 없다**.

**수정**: (a) `chunk_failures` 항목을 `{"ids": [...], "error": str(exc)}` 형태로 바꾸고 실패 청크의 id 목록을 stderr에 출력하도록 `plan.md:152,219-221`을 정정하라. (b) §8에 제약을 신설하라 — "한 청크에 영구 실패 원인이 있으면 같은 청크의 나머지 주문이 무기한 미조정 상태로 남는다. `chunk_failures`의 id 목록으로 격리·수동 처리한다." (c) Exclusions #5의 "자연히 수렴한다"를 "**일시적 실패는** 자연히 수렴한다"로 한정하라.

---

**D7. 호출 횟수 추정 2건이 스토어별 청킹을 무시하고 합산 모집단에서 도출됐다 — review-1 D2와 동일한 부류의 파생값 오류가 축소된 규모로 재발했다.** — Severity: major

`spec.md:55-56`:
> - 백필(현재 로컬 전체 3,910건 기준): `⌈3910/250⌉ = 16`회 — 결정론적
> - 상시 감지(…오늘 기준 최대 약 801건): `⌈801/250⌉ = 4`회/사이클

그러나 청킹은 **스토어별로** 일어난다. `plan.md:208-212`의 커맨드는 스토어를 순회하며 각 스토어마다 `open_candidate_order_ids(store_type)` → `reconcile_order_status_for_ids(...)`를 호출하고, 청킹은 그 안(`plan.md:112`)에서 수행된다. 스토어 경계를 넘는 청크는 만들어지지 않는다. §1의 실측치를 스토어별로 재도출하면:

| | gimssine | etoile | 실제 합 | SPEC 주장 |
|---|---|---|---|---|
| 백필 후보 | 3,828 − 6(반영됨) = 3,822 → **16청크** | 82 → **1청크** | **17회** | 16회 |
| 상시 감지 후보 | 776 → ⌈3.104⌉ = **4청크** | 25 → **1청크** | **5회/사이클** | 4회/사이클 |

절대 영향은 작다(각 +1회). 그러나 **오류의 메커니즘이 review-1 D2와 정확히 같다** — 실제 분할 단위가 아닌 모집단에 나눗셈을 적용했다. D2는 "로컬 건수를 Shopify 측 쿼리에 적용"이었고, 이번은 "합산 건수를 스토어별 청킹에 적용"이다. 프롬프트가 "비용 주장을 실측치에 대조해 검증하라"고 지목한 이유가 여기서 확인된다.

추가로, 미서술된 전제가 둘 있다:
- "후보 집합이 801로 수렴한다"는 **로컬 3,109건이 전부 `ids=` 조회에서 non-NULL 타임스탬프를 돌려준다**는 전제 위에 있다. D1의 삭제 주문 케이스가 있으면 그만큼 상시 잔류한다.
- "로컬 테이블이 커져도 4회가 유지된다"는 **주문이 계속 보관(archive)된다**는 전제 위에 있다. 보관이 멈추면 후보 집합 = open 주문 수가 선형 증가한다. §1.1은 이 조건부를 명시하지 않는다.

**수정**: `spec.md:55-56`의 두 수치를 **17회 / 5회**로 정정하고, 산식을 스토어별로 표기하라(`⌈3822/250⌉ + ⌈82/250⌉`, `⌈776/250⌉ + ⌈25/250⌉`). §4 D3(`:98`)의 "백필 16회, 사이클당 최대 4회"와 Exclusions #5(`:224`)의 동일 수치도 함께 정정하라(3곳). 위 두 전제를 §3 가정 또는 §8 제약으로 명시하라.

---

**D8. `acceptance.md:45`의 패치 대상 규약이 커맨드 AC 7건의 양성 증거 단정을 구조적으로 불가능하게 만든다 — v0.1.0 D4 수정의 작동 전제를 스스로 무너뜨린다.** — Severity: major

`acceptance.md:45`:
> 패치 대상은 항상 함수가 실제로 import된 네임스페이스를 기준으로 한다 — `shopify_orders.py` 내부 테스트는 `order.shopify_orders._get_with_headers`를, **커맨드 테스트는 `order.management.commands.<command_name>.reconcile_order_status_for_ids`(또는 `open_candidate_order_ids`)를 패치한다.**

`reconcile_order_status_for_ids`는 **DB에 실제로 쓰는 유일한 함수**다(`plan.md:150` `bulk_update`). 커맨드 테스트에서 이것을 패치하면 쓰기가 일어나지 않는다. 그런데 커맨드 AC 7건이 전부 **실제 쓰기 결과를 단정**한다:

| AC | 요구하는 양성 증거 | 규약대로 패치하면 |
|---|---|---|
| AC-011(`:216`) | `Order.cancelled_at`이 모킹 값으로 갱신 | 불가 |
| AC-012(`:231`) | etoile의 `Order.closed_at`이 실제 갱신 | 불가 |
| AC-015(`:276`) | `Order.cancelled_at` 갱신 + 매뉴얼 필드 보존 | 불가 |
| AC-016(`:293`) | `Order.cancelled_at == 2026-07-01…` | 불가 |
| AC-017(`:308`) | stdout에 `90017`·`would_change` | 불가 |
| AC-018(`:323`) | AC-015와 동일 | 불가 |
| AC-019(`:338`) | 첫 실행 직후 값 + 재실행 후 값 | 불가 |

특히 **AC-011/017/019의 양성 증거 단정은 v0.1.0 D4에 대한 수정 그 자체**다(`acceptance.md:13,218,310,340`). 규약을 문자 그대로 따르면 그 수정이 무력화된다.

저장소의 실제 관례도 이 규약과 다르다. 커맨드 테스트인 `test_backfill_missing_orders_command.py:17`은 **HTTP 계층**을 패치한다:
```python
_GET_HEADERS_TARGET = "order.management.commands.backfill_missing_orders._get_with_headers"
```
이 형태가 가능한 이유는 그 커맨드가 `_get_with_headers`를 **자기 네임스페이스로 import**하기 때문이다. 반면 SPEC-029의 두 커맨드는 `_get_with_headers`를 import하지 않는다(`plan.md:179,247`) — 따라서 올바른 패치 대상은 `order.shopify_orders._get_with_headers`(또는 `order.shopify_orders.fetch_order_status_by_ids`)이며, 이는 `:45`가 "`shopify_orders.py` 내부 테스트" 전용으로 못박은 대상이다.

추가로 AC-008(`:165`)과 AC-013(`:242`)이 패치하는 `fetch_order_status_by_ids`의 네임스페이스가 `:45`에 열거되어 있지 않다(정답은 `order.shopify_orders.fetch_order_status_by_ids` — 호출자가 같은 모듈의 전역으로 참조하므로).

**수정**: `acceptance.md:45`를 다음으로 교체하라 — "**쓰기 결과를 단정하는 AC**(011/012/015/016/017/018/019)는 실제 쓰기 경로가 살아 있어야 하므로 HTTP 계층인 `order.shopify_orders._get_with_headers`만 패치한다. **실패 주입이 필요한 AC**(012의 gimssine 측, 014)만 `order.management.commands.<name>.open_candidate_order_ids`에 `side_effect`를 건다 — 이 경우에도 정상 동작해야 하는 스토어는 실제 경로를 타야 하므로 스토어별 `side_effect` 분기를 쓴다. **청크 루프를 검증하는 AC**(008/013)는 `order.shopify_orders.fetch_order_status_by_ids`를 패치한다."

---

**D9. `_sync_single_order()` 경유 시의 파괴 범위를 SPEC이 여전히 과소 서술한다 — 라인아이템뿐 아니라 `ShippingLine` 전량과 `Refund` 전량이 삭제된다. 환불 행 보존을 단정하는 AC가 0개다.** — Severity: major

REQ-CANC-007(`spec.md:134`)과 가정 A4(`:89`)는 파괴 범위를 두 가지로 서술한다 — 다른 `Order` 필드가 `None`으로 덮어써짐 + `line_items` 키 부재로 `PurchaseOrder` 미연결 라인아이템 전량 삭제(`shopify_orders.py:287-289`). **소스를 직접 읽어 확인한 결과 그 두 가지는 정확하나, 같은 함수가 그 직후 두 가지를 더 한다**:

```python
# shopify_orders.py:287-289  (SPEC이 인용한 부분 — 확인 ✓)
order_obj.line_items.filter(purchase_orders__isnull=True).exclude(
    shopify_line_item_id__in=incoming_shopify_ids).delete()

# shopify_orders.py:291      (SPEC 미서술)
order_obj.shipping_lines.all().delete()

# shopify_orders.py:306      (SPEC 미서술)
order_obj.refunds.all().delete()
```

`:291`과 `:306`은 **무조건 삭제**다. `fields=` 제한 페이로드에는 `shipping_lines`/`refunds` 키가 없으므로(`:301`, `:307`) 삭제 후 아무것도 재생성되지 않는다. 즉 `_sync_single_order()`를 경유하는 변이는 **그 주문의 환불 행을 전부 소실시킨다.**

이 저장소에서 환불 넷팅은 이미 2건의 연속 프로덕션 결함을 낸 관례다(auto-memory: "수량 집계는 항상 환불 차감 — 8곳에 있는 규약인데 신규 경로가 계속 빠뜨려 SPEC-ORDER-023·026에서 연속 결함"). `Refund` 행이 사라지면 `purchase_order_views`의 6개 `OuterRef` 서브쿼리가 그 주문을 "환불 없음"으로 계산한다.

**AC-015/018은 `Refund`·`ShippingLine` 보존을 단정하지 않는다**(`acceptance.md:276,323` — `Order.status`/`note`/`ready_to_ship` + `LineItem` 4개 필드 + PO 연결만). 다만 광역 쓰기 변이는 `note` 단정에서 이미 잡히므로 **커버리지 손실은 전이적으로 방어된다** — 그래서 blocking이 아니라 major다. 문제는 SPEC이 자기 설계의 근거(왜 좁은 쓰기가 "더 좁은 선택"이 아니라 필수인가)를 실제보다 약하게 서술한다는 점이다. 정정하면 논거가 강해진다.

**수정**: 가정 A4(`spec.md:89`)와 REQ-CANC-007(`:134`)에 "`shopify_orders.py:291`·`:306`이 `ShippingLine`·`Refund` 행을 무조건 전량 삭제하며 제한 페이로드에는 재생성 소스가 없다 — 그 주문의 환불 이력이 소실되고 환불 넷팅 계산이 틀어진다"를 추가하라. AC-015 Then에 "**그리고** 그 주문의 `Refund` 행 수가 실행 전후 동일하다"를 추가할 것을 권한다(1줄, 환불 관례의 회귀 방어선).

---

### MINOR

**D10. AC-CANC-015/018의 매뉴얼 필드 픽스처에 `LineItem.original_sku`가 빠져 있다.** — Severity: minor
`acceptance.md:272`가 열거하는 비기본값 필드는 `logistics_status`/`rack_number`/`received_quantity`/`purchase_status` 4개다. `original_sku`(SPEC-ORDER-025가 도입한 수동 정정 보호 필드, `shopify_orders.py:209-224`·`:256-285`가 지키는 값)가 빠졌다. 이 SPEC의 쓰기 경로는 `LineItem`에 도달하지 않으므로 실질 위험은 낮고 광역 쓰기 변이는 다른 필드에서 잡히지만, 프롬프트가 명시한 불변식 목록에 포함된 항목이다.
**수정**: AC-015 Given의 `LineItem` 픽스처에 `original_sku="9788901234567"`(비기본값)을 추가하고 Then에 무변경 단정을 추가하라.

**D11. REQ-CANC-010의 EARS 라벨이 `(Ubiquitous)`이나 조건절을 갖는 State-Driven 문장이다.** — Severity: minor
`spec.md:144-145`: "**REQ-CANC-010** (Ubiquitous) … 후보 집합이 250건을 초과하면, THE 시스템은 모든 청크를 shall 처리한다". 같은 문서의 REQ-CANC-008(`:136-137`)이 `(State-Driven)` + `**While**` 구조를 올바르게 쓰고 있어 대조가 명확하다. v0.1.0 D9(`(Unwanted)` 오라벨 4건)는 정정됐으나 반대 방향의 오라벨이 1건 생겼다.
**수정**: `(State-Driven)` + "**While** 후보 집합이 250건을 초과하는 동안" 형태로 재작성하거나 라벨만 정정하라.

**D12. REQ-CANC-002·005의 주어가 시스템이 아니다.** — Severity: minor
`spec.md:115` "단일 조회 요청은 … shall 포함한다", `:126` "후보 집합은 스토어별로 shall 별도 산정된다"(수동태). EARS Ubiquitous는 "The [system] shall [response]"를 요구한다. 규범 내용은 명확하므로 기능 영향 없음.

**D13. REQ-CANC-005가 테스트 가능한데도 "AC 없음 — DoD 검증(코드 리뷰)"으로 처리됐다.** — Severity: minor
`spec.md:195`. 스토어 스코핑은 `open_candidate_order_ids("etoile")`을 gimssine 주문이 있는 상태에서 호출해 제외를 단정하면 3줄로 검증된다. [HARD] 요구를 코드 리뷰에만 맡기는 것은 회귀 방어선이 없다는 뜻이다. (실질 보호는 `plan.md:124`의 `filter(store_type=store_type, ...)`가 제공하므로 위험은 낮다.)
**수정**: AC-CANC-010에 "**그리고** `open_candidate_order_ids("etoile")` 결과에 gimssine 주문 id가 포함되지 않는다"를 1줄 추가하면 REQ-005가 커버된다.

**D14. AC-CANC-019가 잡는다고 선언한 M19(비멱등)는 이 아키텍처에서 구조적으로 발생 불가능하다.** — Severity: minor
두 번째 실행 시 90019는 이미 `cancelled_at`이 채워져 후보 집합에서 빠지므로(`plan.md:80`) **조회 자체가 일어나지 않는다.** 따라서 "값이 흔들린다"는 변이는 재현 경로가 없다. 남는 판별력은 (a) 첫 실행 양성 증거(AC-016과 중복), (b) `count() == 1`(중복 행 생성 변이) 두 가지뿐이다. 결함은 아니나 `acceptance.md:39`의 M19 서술("값이 흔들리거나")은 정확하지 않다.
**수정**: M19를 "재실행이 `update_or_create` 경유로 중복 `Order` 행을 만들거나, 후보 집합 재계산 대신 캐시된 목록을 재사용해 예외가 난다"로 좁혀 서술하라.

**D15. 250개 `ids=` URL의 길이(~3.6KB)가 어디에도 기록되지 않았고, 실제 크기의 URL을 만드는 AC가 없다.** — Severity: minor
`plan.md:52-53`이 만드는 최대 경로는 13자리 id 250개 + 쉼표 249개 ≈ 3,499자, 전체 URL ≈ 3,610자다. 프로덕션에서 동작이 확인됐으므로(가정 A1) 위험은 해소돼 있으나, AC-CANC-006은 id 2개(`:137`), AC-CANC-007은 조인하지 않는 순수 리스트(`:150`)만 다뤄 **실제 크기의 URL을 만들어보는 AC가 0개**다.
**수정**: §1.1 또는 A1에 측정된 URL 길이를 기록하라. AC-007의 Then에 "첫 청크를 `",".join(str(i) for i in chunk)`로 조인한 문자열 길이가 4,000자 미만이다"를 추가하는 것도 저비용 방어선이다.

**D16. `plan.md:104-106`이 `parse_datetime`을 함수 내부에서 재import한다.** — Severity: minor
`shopify_orders.py:8`이 이미 모듈 레벨에서 `from django.utils.dateparse import parse_datetime`을 import하고 있다(`sync_store()`가 `:442`에서 사용). 함수 내부 재import는 동작에 문제없으나 파일 기존 스타일과 불일치한다. (`from .models import Order`의 함수 내부 import는 순환 참조 회피 목적이므로 기존 관례와 일치한다 ✓ — `shopify_orders.py:105,356`이 같은 형태다.)

---

## 독립 검증 — 결함 없음 (근거와 함께 기록)

프롬프트가 지목한 load-bearing 주장 중 **검증을 통과한** 것들. 저자의 주장을 받아들인 것이 아니라 소스와 문서를 직접 대조한 결과다.

1. **D1(datetime → URL)의 구조적 해소 — 참.** 신규 코드 경로 전체를 추적했다: `open_candidate_order_ids()`(`plan.md:78-82`) → `values_list("shopify_order_id", flat=True)` → `Order.shopify_order_id = BigIntegerField()`(`models.py:31`, 실물 확인) → **int 리스트**. `_chunked()`(`:22-28`)는 슬라이싱만 한다. `fetch_order_status_by_ids()`(`:52`)의 `",".join(str(i) for i in shopify_order_ids)`가 int → str 명시 변환을 수행한다. **어떤 datetime도 URL에 도달하지 않으며, 도달할 수 있는 값의 타입이 int 하나뿐이다.** `_get_with_headers`(`shopify_orders.py:16-22`)에 들어가는 경로에 공백·`+`가 생길 여지가 없다. 구조적 재발 불가 주장은 참이다 ✓.
2. **빈 리스트 처리 — 안전.** 후보 집합이 비면 `_chunked([])`가 `range(0,0,250)`을 순회하지 않아 루프가 0회 실행되고, `ids=`(값 없음) URL은 **만들어지지 않는다**. `fetch_order_status_by_ids`의 `if not shopify_order_ids: return []`(`plan.md:50-51`)는 도달 불가한 방어층이다 ✓.
3. **재오픈 시 `sync_store()`가 되돌린다(A4/D5) — 참, 소스로 확인.** `shopify_orders.py:161-162`가 `closed_at`/`cancelled_at`을 `defaults`에 무조건 포함하며(제외 주석이 붙은 `status`/`ready_to_ship`(`:140-147`)과 대조적), `sync_store()`(`:430`)가 `status=open` 피드의 모든 주문에 대해 `_sync_single_order()`를 호출한다. 재오픈은 `updated_at`을 밀어 올리므로 `updated_at_min` 워터마크(`:386,451-453`) 이후 배치에 반드시 포함된다. → 두 필드가 NULL로 복원되고 그 주문이 후보 집합에 자동 재진입한다. **자기 치유 주장은 참이다** ✓.
4. **취소+종료 동시 기록 시 클로버링 없음 — 참.** 두 값이 **같은 레코드 하나**에서 나와 같은 `bulk_update` 호출로 함께 쓰인다(`plan.md:134-135,145-146,150`). v0.1.0의 2채널 설계가 가졌던 "종료 채널이 취소 채널의 쓰기를 NULL로 되돌린다"는 위험(review-1 D7)은 채널이 하나로 통합되며 **실제로** 소멸했다 — 문서의 주장(`spec.md:20` D7 항목)이 정확하다 ✓.
5. **응답이 요청보다 짧을 때 — 예외 없음.** `for r in records:`(`plan.md:129`)가 **응답**을 순회하고 요청 청크를 순회하지 않으므로, Shopify가 일부 id를 누락해도 KeyError/IndexError가 발생하지 않는다 ✓. (다만 그 사실을 감지·보고하지 않는 것이 D1의 일부다.)
6. **`_sync_single_order()` 경유가 파괴적이라는 판정 — 참이며 SPEC이 과소 서술.** `incoming_shopify_ids`가 `order_data.get("line_items", [])`(`shopify_orders.py:226-227`)에서만 채워지므로 제한 페이로드에서 빈 집합이 되고, `:287-289`가 `PurchaseOrder` 미연결 라인아이템을 전량 삭제한다 ✓. 추가 파괴 2건은 D9로 별도 계상.
7. **좁은 쓰기 경로의 범위 규율 — 위반 없음.** `bulk_update(to_update, ["cancelled_at","closed_at"])`(`plan.md:150`)는 `Order.status`(`models.py:47-53`), `ready_to_ship`(`:61`), `LineItem.purchase_status`/`logistics_status`(`shopify_orders.py:229-230` 주석이 명시적 제외), `original_sku`(`:209-224`), `received_quantity`, 환불 행(`:306-329`) 중 **어느 것에도 도달하지 않는다.** `.only("id","shopify_order_id","cancelled_at","closed_at")`(`plan.md:125`)에 pk가 포함돼 `bulk_update`가 정상 동작하며, deferred 필드는 건드려지지 않는다 ✓.
8. **`StoreSyncWatermark` 사고 부류 재현 불가 — 참.** 두 커맨드 어디에도 `StoreSyncWatermark` import가 없고(`plan.md:176-181, 244-249`), 이 SPEC은 커서 모델 자체를 만들지 않는다. `models.py:565-603`의 사고(단건 쓰기 경로가 스토어 전역 워터마크를 밀어 올림)를 재현할 코드 경로가 존재하지 않는다 ✓. AC-CANC-011이 양성 증거와 짝지어 회귀를 방어한다 ✓.
9. **신규 마이그레이션 0건 — 확인.** `backend/order/migrations/` 실물 확인 결과 최신은 `0044_lineitem_original_sku.py`이며 `0045`는 존재하지 않는다 ✓. `plan.md:169,410`·`acceptance.md:417`의 주장과 일치 ✓.
10. **`.bat` 미러링 5개 항목 — 전건 확인.** `scripts/sync_orders.bat` 실물(26줄)과 `plan.md:331-349`를 나란히 대조: (1) `cd /d C:\app\scm_v2\backend || exit /b 1` ✓(원본 `:9`), (2) `set PYTHONIOENCODING=utf-8` ✓(원본 `:14`), (3) 전용 로그 `sync_order_cancellations.log` ✓, (4) `set RC=%ERRORLEVEL%` + `exit /b %RC%` ✓(원본 `:20,25`), (5) **"do not run two copies at once / Do not start a new instance" REM 2줄 복원** ✓(원본 `:3-4` → `plan.md:334-335`). review-1 D5가 지적한 누락이 정확히 해소됐다 ✓. `-MultipleInstances IgnoreNew` 인용도 `.moai/project/scheduled-jobs.md` §3의 실제 등록 스크립트와 일치 ✓.
11. **트랜잭션 범위 축소 — review-1 D5 부차 권고가 반영됨.** `fetch_order_status_by_ids()` 호출이 `transaction.atomic()` **밖**에 있다(`plan.md:117` vs `:120`). Shopify 왕복 동안 DB 락을 쥐지 않는다 ✓. 원격 MySQL(~130ms/쿼리) 환경에서 의미 있는 개선이다.
12. **배치 쿼리 관례 준수.** `Order.objects.filter(store_type=..., shopify_order_id__in=chunk)`(`plan.md:123-124`)가 청크당 1쿼리이고 `__in`이 최대 250건으로 유계다 — review-1 D2의 부수 결함(무제한 `__in`)이 구조적으로 해소됐다 ✓. `unique_together=[("shopify_order_id","store_type")]`(`models.py:94`, 실물 확인)이 복합 인덱스를 제공하므로 이 조회는 인덱스를 탄다 ✓.
13. **`plan.md` §4 위험표 R1~R14의 AC 참조 — 14행 전건 대조, 오류 0건.** R1→AC-015/018 ✓, R2→003/004 ✓, R3→008 ✓, R4→006 ✓, R5→007 ✓, R6→009 ✓, R7→010 ✓, R8→011 ✓, R9→012 ✓, R10→013 ✓, R11→014 ✓, R12→016 ✓, R13→017 ✓, R14→019 ✓. 존재하지 않는 AC 참조 0건. **review-1 D3(10행 +1 시프트 + 유령 AC-021)이 완전히 해소됐다** ✓.
14. **§6 추적표 ↔ `Traces:` 양방향 대조 — 불일치 0건 (독립 재수행).** 저자의 선언을 신뢰하지 않고 grep으로 `Traces:` 19행을 추출해 `spec.md:191-210`의 20행과 양방향 대조했다. spec→acceptance 방향: 18개 REQ의 매핑이 대응 AC의 `Traces:`에 전부 존재(REQ-005/017은 "AC 없음" 명시) ✓. acceptance→spec 방향: 19개 AC의 모든 `Traces:` 항목이 §6의 해당 행에 존재 ✓. 고아 AC 0건, 미커버 REQ 0건. **review-1 D11(4건 불일치, 3회 연속 재발 부류)이 실제로 해소됐다** — 이 부분에 한해 저자의 주장은 참이다 ✓. (다만 파일↔AC 배정 층에서는 재발했다 — D3.)
15. **DoD가 인용한 회귀 테스트 파일 6개 전부 실재.** `backend/order/tests/` 실물 확인: `test_shopify_orders.py` ✓, `test_sync_orders_command.py` ✓, `test_backfill_missing_orders_command.py` ✓, `test_order_resync.py` ✓, `test_store_sync_watermark.py` ✓. `acceptance.md:410-411`·`plan.md:480-483`에 허위 경로 0건 ✓.
16. **범위 규율 — 위반 없음.** OUT 범위(UI/API 신설, 취소 주문의 라인아이템 결정, `:287-289` 편집 결함 수정)를 건드리는 요구사항이 20개 중 0건이다. REQ-CANC-018/019/020은 전부 보존(`shall not`) 요구이며, `plan.md:365-366`이 "`Order` 이외 모델 참조 금지"·"신규 마이그레이션/모델 추가 금지"를 마일스톤 금지사항으로 못박았다 ✓. Exclusions #3(`spec.md:222`)이 "79개 라인아이템과 PO 연결 51개는 이 SPEC 전후로 정확히 동일하게 유지된다"로 명시 ✓.
17. **v0.1.0 D4(공허 통과 4건) — 실제로 해소.** 각 대응 AC에 "커맨드가 아무 일도 하지 않는" 변이를 직접 대입했다: AC-011은 `cancelled_at` 갱신 단정(`:216`)에서 실패 ✓, AC-017은 stdout `90017`/`would_change` 단정(`:308`)에서 실패 ✓, AC-019는 첫 실행 직후 값 단정(`:338`)에서 실패 ✓. AC-003/004도 양성 증거를 먼저 두는 구조다(`:94,109`) ✓. **4건 중 4건 해소** — 단, 신규 AC-005에서 같은 부류가 1건 발생(D2).

---

## Chain-of-Verification Pass

1차 판정 후 재점검하여 **추가로 발견한 것**:

- **아키텍처를 "설계 문서"가 아니라 "상태 기계"로 다시 돌렸는가** → 1차에서는 `ids=`+후보 집합 조합이 D1/D2를 구조적으로 해소한다는 점을 확인하고 "설계는 옳다"로 넘어갔다. 2차에서 주문 하나의 생애를 1→2→3-a/3-b→4 단계로 표를 그려 돌린 결과 **3-b 이후 4단계가 어떤 코드 경로에도 걸리지 않는다**는 것을 발견했다(D1). 문서를 읽는 방식으로는 보이지 않는다 — `spec.md:53`의 "아직 취소·종료 여부를 모르는 주문"이라는 표현이 실제 술어(`두 필드가 모두 NULL`)와 미묘하게 다르다는 것을 알아채야만 나온다. **D1은 전적으로 2차 발견이다.**
- **판별력 문단을 믿지 않고 변이를 실제로 대입했는가** → 1차에서는 AC-005의 "판별력: `KeyError`로 잡힌다"를 그대로 수용했다. 2차에서 `plan.md:112-153`의 `try/except` 중첩 구조를 놓고 `existing[r["id"]]` 변이를 손으로 실행하여 **세 단정이 전부 통과함**을 확인했다(D2). 저자가 v0.1.0 D4를 고치면서 역방향 규약을 신설했는데, 그 규약을 자기가 열거한 3개 AC에만 적용하고 신규 AC-005에는 적용하지 않았다는 것도 이때 드러났다.
- **저자의 "기계적 대조" 선언을 독립적으로 재수행했는가** → 프롬프트 지시대로 grep으로 `Traces:` 19행과 `plan.md`의 AC 참조를 추출해 대조했다. **§6↔Traces는 실제로 깨끗했다**(항목 14) — 여기서 멈췄으면 선언을 그대로 통과시켰을 것이다. 2차에서 "마일스톤 참조도 0건"이라는 절반을 별도로 검증하다가 AC-011의 소속 파일이 4곳에서 갈리는 것을 발견했다(D3). **선언의 절반이 참이라는 사실이 나머지 절반을 검증하지 않을 유인을 만든다** — 이것이 이 부류 결함의 진짜 위험이다.
- **인용된 감사 보고서를 실제로 열었는가** → 1차에서는 "감사가 확인한 `ids=`"를 프롬프트의 ground truth와 일치하므로 통과 처리했다. 2차에서 review-1 전문을 `ids=`로 재검색해 **한 번도 등장하지 않으며 D2의 지시가 정반대(`status=closed` 규모 측정)임**을 확인했다(D4). 프롬프트가 "귀속이 틀렸다는 점은 지적하되 사실은 검증된 것으로 다루라"고 미리 알려준 항목이지만, 그 지시가 없었어도 review-1 재독으로 잡혔을 것이다.
- **파생 수치를 코드의 실제 분할 단위에 대조했는가** → 1차에서는 3910÷250=16, 801÷250=4 산술만 확인하고 통과시켰다. 2차에서 `plan.md:208-212`(스토어 루프) → `:112`(청크 루프)의 중첩 순서를 보고 **청킹이 스토어 내부에서 일어남**을 확인, 스토어별로 재도출하여 17회/5회를 얻었다(D7). review-1 D2와 완전히 같은 부류다.
- **테스트 관례 주장을 저장소 실물과 대조했는가** → `acceptance.md:45`가 "기존 모킹 관례를 재사용한다"고 적었기에 `test_backfill_missing_orders_command.py:17`을 열었더니 **커맨드 테스트인데 HTTP 계층을 패치**하고 있었고, 그 이유(커맨드가 `_get_with_headers`를 자기 네임스페이스로 import함)가 SPEC-029의 두 커맨드에는 성립하지 않는다는 것을 확인했다. 여기서 규약↔AC 7건의 구조적 모순이 드러났다(D8).
- **파괴 경로를 인용된 줄에서 멈추지 않고 그 아래까지 읽었는가** → SPEC이 `:287-289`를 정확히 인용했기에 통과시킬 뻔했다. 함수 끝까지 읽어 `:291`(ShippingLine 전량 삭제)과 `:306`(Refund 전량 삭제)을 발견했다(D9). **review-1이 "인용은 정확하나 인접 경로가 비었다"고 명명한 패턴이 같은 함수 안에서 두 줄 아래에 있었다.**
- **`chunk_failures`의 운영 가치를 따졌는가** → 1차에서는 "청크 격리가 구현됐다"로 통과. 2차에서 `str(exc)`만 담기고 id가 버려진다는 점과 `open_candidate_order_ids()`에 `order_by()`가 없어 청크 구성이 사실상 고정된다는 점을 결합해 영구 볼모 시나리오를 도출했다(D6).

1차에서 이미 잡았던 것: D4(부분), D5, D11, D12. **2차 신규: D1, D2, D3, D6, D7, D8, D9, D10, D13, D14, D15, D16** — blocking 5건 중 **4건이 2차 발견이다.**

---

## Regression Check — iteration 1 결함 13건

| # | iteration 1 결함 | 판정 | 근거 |
|---|---|---|---|
| D1 | `updated_at_min` datetime → URL(`InvalidURL`) | **RESOLVED** | 커서·`updated_at_min` 코드 경로 자체가 삭제됨. 신규 경로의 URL 삽입 값은 int 하나뿐임을 타입 추적으로 확인(독립 검증 1) |
| D2 | "~15회" 파생값 오류 + livelock | **RESOLVED (부류 재발)** | 무제한 Shopify 측 스윕 소멸, 호출량이 로컬 건수로 유계화 ✓. 단 **동일 부류의 파생값 오류가 축소 재발**(D7 — 스토어별 청킹 무시) |
| D3 | `plan.md` §4 위험표 10행 +1 시프트 + 유령 AC-021 | **RESOLVED (후반부 재발)** | 위험표 R1~R14 전건 정확 ✓(독립 검증 13). 단 **§2 마일스톤 파일↔AC 배정 드리프트는 재발**(D3 — AC-011) |
| D4 | 공허 통과 AC 4건 | **RESOLVED (1건 신규)** | AC-011/017/019에 양성 증거 추가, 역방향 [HARD] 규약 신설 ✓(독립 검증 17). 단 **신규 AC-005에 같은 부류 1건 발생**(D2) |
| D5 | `.bat` "새 인스턴스 시작 안 함" 2줄 누락 | **RESOLVED** | `plan.md:334-335` 복원 + REQ-CANC-017 5번째 항목 + DoD `:422-423` ✓. 부차 권고(트랜잭션 범위 축소)도 반영(`plan.md:114-120`) ✓ |
| D6 | `status=` 단정 AC 0개 | **PARTIALLY RESOLVED** | `status=any`·`ids=`는 AC-006이 단정 ✓. **`fields=`·`limit=`는 여전히 0개**(D5 blocking) |
| D7 | AC-005 대칭 픽스처가 반증 불가 | **RESOLVED** | 채널이 하나로 통합되어 대칭 클로버링 시나리오 자체가 소멸(독립 검증 4) ✓ |
| D8 | 내부 상호참조 오류 3건 | **RESOLVED (신규 1건)** | 단건 엔드포인트 명제가 가정 A3로 분리되고 "미검증"으로 정직히 명시 ✓(`spec.md:88`). 5분 주기 귀속도 정정 ✓(`:101`). **단 새 오귀속 1건 발생**(D4 — A1 → plan-auditor) |
| D9 | `(Unwanted)` 라벨 오용 4건 | **RESOLVED (반대 방향 1건)** | REQ-018/019/020이 `(Ubiquitous)`로 정정 ✓, REQ-012/013만 진짜 If/then ✓. **REQ-010이 반대 방향으로 오라벨**(D11 minor) |
| D10 | 스케줄러 실제 등록 DoD 부재 | **RESOLVED** | `acceptance.md:423`("등록되고 `-MultipleInstances IgnoreNew` 확인, 최소 1회 종료 코드 0"), `plan.md:388` ✓ |
| D11 | `Traces:` 불일치 4건 | **RESOLVED** | grep 기반 양방향 전건 재대조 결과 불일치 0건(독립 검증 14) ✓. 3회 연속 재발하던 부류가 실제로 끊겼다 |
| D12 | `auto_now`/`bulk_update` 근거 오류 | **RESOLVED** | 해당 서술이 v0.2.0에서 삭제됨(§4 위험표에 `auto_now` 언급 없음) ✓ |
| D13 | 반환 키 계약 이중 표기 | **RESOLVED** | `plan.md:98-102`가 `"changed"` 단일 키로 확정하고 라벨링을 호출자 책임으로 명시 ✓. 두 커맨드가 실제로 그렇게 사용(`:226,304-307`) ✓ |

**Stagnation 판정: 해당 없음.** 13건 중 11건 완전 해소, 2건 부분 해소. 어느 결함도 원문 그대로 남아 있지 않으며, 저자는 patch가 아니라 재설계로 대응했다. **blocking 판정의 근거는 정체가 아니라 새 아키텍처의 미감사 영역(D1)과 신규 문서에서 발생한 결함(D2/D3/D4)이다.**

다만 **부류 차원**에서는 4개가 재발했다 — 파생값 모집단 오류(D2→D7), 문서 간 배정 드리프트(D3→D3), 공허 통과 AC(D4→D2), 근거 오귀속(D8→D4). 개별 수정은 성실하게 이뤄지는데 **부류를 막는 절차가 정착하지 않았다**는 신호이며, 이 판정은 iteration 1의 결론과 동일하다.

---

## Recommendation

**FAIL. `/moai run` 진입 불가. v0.2.0은 구현 준비가 되지 않았다. blocking 결함 5건(D1, D2, D3, D4, D5).**

### 새 아키텍처에 대한 판정

**골격은 옳고, v0.1.0보다 명백히 낫다.** 커서 제거로 D1(직렬화)이 구조적으로 소멸했고, 조회 비용이 Shopify 측 미지수에서 로컬 건수로 옮겨가며 D2(livelock)의 발생 조건이 사라졌다. 호출부 계약 결함(D1을 낳은 부류)은 이번엔 없다 — 타입 경계를 전수 추적한 결과 URL에 닿는 값은 int뿐이고, 빈 리스트·짧은 응답·양 필드 동시 기록·재오픈 자기 치유가 전부 정상 동작한다(독립 검증 1~5). 좁은 쓰기 경로와 범위 규율도 소스로 확인했다(7, 16).

**그러나 후보 집합의 생애주기가 한 번도 끝까지 돌려지지 않았다.** "첫 상태 전이에서 관측을 종료한다"는 성질은 비용을 결정론적으로 만드는 바로 그 성질이면서, 동시에 종료 후 취소를 영구 사각지대로 만든다(D1). v0.1.0의 `status=cancelled` 스윕에는 없던 회귀이며, SPEC은 이 트레이드오프를 인지조차 하지 못하고 있다. 이것은 문언 수정으로 닫히지 않고 **설계 판단 1건**을 요구한다.

### 착수 전 필수 (blocking)

1. **D1 — 후보 집합 사각지대에 대한 명시적 결정.** 세 선택지(후보 집합을 `cancelled_at IS NULL`로 확대 / 현행 유지 + Exclusions 명시 / 백필에 `--include-closed`) 중 하나를 고르고 근거를 §4에 기록하라. 1번을 고르면 §1.1의 비용 수치를 전면 재도출해야 한다. 어느 것을 고르든 **Shopify 미반환 id의 영구 잔류**를 §8 제약으로 신설하고, `candidates` 대 `scanned` 차이를 보고하는 요구를 REQ에 추가하라. *이 결정 없이 착수하면, 이 SPEC은 스스로 정의한 문제("취소 감지")의 일부를 조용히 포기한 채 구현된다.*
2. **D2 — AC-CANC-005의 판별력 복구.** Then에 `chunk_failures == []`와 같은 청크의 다른 주문에 대한 양성 증거를 추가하라. 아울러 `acceptance.md:13,372`의 역방향 [HARD] 규약을 AC 번호 열거가 아니라 "모든 부정형 단정"으로 일반화하라 — 지금 형태는 다음 개정에서 같은 누락을 보장한다.
3. **D3 — AC-CANC-011 배정 정정 + 거짓 자기 인증 처리.** `acceptance.md:3`과 `plan.md` M1/M2를 DoD(`:400-401`) 기준으로 정정하고, `spec.md:214`의 "25개 매핑 행"을 20개로 고쳐라. "불일치 0건" 선언은 **실행한 grep 명령과 출력을 각주에 붙이거나, 삭제하라.**
4. **D4 — 가정 A1의 출처 정정.** `spec.md:49,51,86`과 `plan.md:7`의 "plan-auditor가 review-1에서 확인" 귀속을 실제 출처(사용자의 2026-08-19 프로덕션 직접 조회)와 조회 문자열·결과로 교체하라. 사실은 참이므로 설계는 그대로 두되, 아키텍처 전체의 단일 근거가 검증 가능한 상태여야 한다.
5. **D5 — `fields=`·`limit=` 단정 추가.** AC-CANC-006 Then에 1줄. 이전 회차 미해결분이므로 이번에 닫지 않으면 3회차로 이월된다.

### RED 작성 전 반영 (미반영 시 해당 변이 영구 미커버 또는 구현 1사이클 낭비)

6. **D8** — `acceptance.md:45`의 패치 대상 규약을 AC 성격별 3분류로 교체하라. 현행 규약을 문자 그대로 따르면 커맨드 AC 7건의 양성 증거 단정이 **작성 불가능**하며, 그 중 3건은 v0.1.0 D4 수정 그 자체다.
7. **D6** — `chunk_failures`에 실패 id를 담고 stderr에 출력하도록 `plan.md:152,219-221`을 정정, §8에 영구 실패 청크 제약 신설, Exclusions #5의 "자연히 수렴한다"를 일시적 실패로 한정.
8. **D9** — 가정 A4/REQ-CANC-007에 `ShippingLine`·`Refund` 전량 삭제를 추가하고, AC-CANC-015에 `Refund` 행 수 무변경 단정 1줄 추가(이 저장소의 환불 넷팅 회귀 이력을 고려한 저비용 방어선).
9. **D7** — 비용 수치 3곳(`spec.md:55-56`, `:98`, `:224`)을 스토어별 산식으로 재도출(17회 / 5회). 수렴 전제 2건을 가정 또는 제약으로 명시.

### 문서 정합 (코드 영향 없음)

10. **D10** — AC-015 픽스처에 `original_sku` 추가. **D13** — AC-010에 스토어 스코핑 단정 1줄로 REQ-005 커버. **D11/D12** — REQ-010 라벨, REQ-002/005 주어. **D14** — M19 서술 정밀화. **D15** — URL 길이 기록. **D16** — `parse_datetime` 재import.

### 재감사 시 중점 (iteration 3)

**D1의 결정 내용**을 먼저 본다 — 세 선택지 중 무엇을 골랐고 그 결과가 §1.1 비용 수치와 Exclusions에 일관되게 반영됐는지가 판정의 대부분을 좌우한다. 다음으로 **D3의 "불일치 0건" 선언 처리 방식**을 본다: grep 출력이 각주로 붙었는지, 아니면 선언이 삭제됐는지. 문언만 다듬은 채 선언이 그대로 남아 있으면 그 자체가 stagnation 신호로 간주한다. **D2/D5/D8은 각각 1~3줄 수정이므로, 미반영 시 정체로 판정한다.**
