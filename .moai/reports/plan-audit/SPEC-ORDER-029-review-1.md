# SPEC Review Report: SPEC-ORDER-029

Iteration: 1/3
Verdict: **FAIL**
Overall Score: **0.66**
`/moai run` 진입: **불가. blocking 결함 4건.**

> **M1 Context Isolation**: 프롬프트가 전달한 저자 측 배경 서술(SPEC-028 폐기 경위 등)은 감사 범위를 정하는 데만 썼고, 판정 근거는 `.moai/specs/SPEC-ORDER-029/{spec,plan,acceptance}.md`의 실제 텍스트와 이 세션에서 직접 연 저장소 소스다. 프롬프트가 "검증된 실측치, 재도출 금지"로 명시한 프로덕션 수치(776/25, 3,910, 3,109, 1,170/21, 58/6/52, 79/51)는 재검증하지 않고 기준값으로 채택했다 — 다만 **그 수치들로부터 SPEC이 도출한 파생값**은 재도출 대상으로 삼았고, 거기서 blocking 결함 1건이 나왔다(D2).

---

## Must-Pass Results

- **[PASS] MP-1 REQ 번호 일관성** — 25개 전수 열거 확인: 모듈1 `spec.md:106,109,112`(001–003), 모듈2 `:117,120,123`(004–006), 모듈3 `:128,131,134,137`(007–010), 모듈4 `:142`(011), 모듈5 `:147,150,153,156,159,162`(012–017), 모듈6 `:167,170,173,176`(018–021), 모듈7 `:181`(022), 모듈8 `:186,189,192`(023–025). 결번 0, 중복 0, 3자리 패딩 일관. `spec.md:257`의 자기 선언("001~025, 25개, 결번 없음")과도 일치.
- **[PASS] MP-2 EARS 형식 준수** — 25개 REQ 전수 확인. 전부 `shall`/`shall not` 조동사를 갖고 주어(THE 시스템/THE 백필 커맨드/각 커서 행)가 명시되어 있다. `spec.md:121`(REQ-005, While…shall), `:151`(REQ-013, When…shall), `:157`(REQ-015, If…then…shall not), `:160`(REQ-016, If…then…shall not), `:163`(REQ-017, While…when…shall), `:171`(REQ-019, WHERE…shall not) 모두 해당 패턴에 정합. **다만 라벨링 오류 4건(D9)** — REQ-003(`:112`)/006(`:123`)/008(`:131`)/020(`:173`)은 `(Unwanted)`로 라벨되어 있으나 If/then 구조가 없는 **부정형 Ubiquitous** 문장이다. 문장 자체는 완전한 EARS 규범문이므로 MP-2 FAIL 사유는 아니며, MINOR 결함으로 분류한다.
- **[PASS] MP-3 YAML frontmatter 유효성** — `spec.md:1-11`: `id: SPEC-ORDER-029` ✓, `version: 0.1.0`(점 2개 → string) ✓, `status: planned` ✓(프로젝트 어휘 — `SPEC-ORDER-028/spec.md:4`가 `superseded`를 쓰는 것과 동일 계열), `created_at: 2026-08-19` ✓, `priority: High` ✓, `labels: [order, shopify, sync, cancellation, closure, backend]`(배열) ✓. 6개 필수 필드 전부 존재, 타입 정합.
- **[N/A] MP-4 언어 중립성** — 단일 언어(Python/Django) 프로젝트 SPEC. 자동 통과.

**must-pass firewall 미발동.** 그러나 아래 blocking 결함 4건은 must-pass와 독립적으로 `/moai run` 진입을 막는다.

---

## Category Scores

| Dimension | Score | Band | Evidence |
|-----------|-------|------|----------|
| Clarity | 0.70 | 0.50–0.75 | §4 D1~D7의 설계 논거가 명확하고 각 결정이 REQ로 연결된다 ✓. 감점: `plan.md` §4 위험표 12행 중 **10행이 AC 번호 +1 시프트**(D3), 내부 상호참조 오류 3건(D8 — `spec.md:29`가 A1에 없는 명제를 A1로 귀속, `:252` C5가 5분 주기를 §4 D6에 귀속하나 D6는 주기를 언급하지 않음) |
| Completeness | 0.70 | 0.50–0.75 | HISTORY/문제정의/Environment/Assumptions/설계결정/REQ/추적표/Exclusions(8건, 전부 구체)/제약 전 섹션 존재 ✓. 감점: `updated_at_min` **직렬화 포맷 미규정**(D1의 근인), 스케줄러 **자기중복 실행 방지 요구 부재**(D5), `status=closed` 규모 **미측정**(D2), 스케줄러 **실제 등록 요구 부재**(D10) |
| Testability | 0.60 | 0.50–0.75 | AC-003/004/010/014/017/020은 진짜 판별자다 ✓. 감점: 20개 중 **4개(AC-007/016/018/019)가 양성 대조군 없이 공허 통과 가능**하며 이는 `acceptance.md:9,11`이 스스로 [HARD]로 금지한 형태다(D4), `status=` 파라미터를 단정하는 AC가 **0개**(D6), AC-005 픽스처가 자기 주장을 반증 불가능하게 만든다(D7) |
| Traceability | 0.65 | 0.50–0.75 | 25개 REQ 중 23개가 AC 매핑, 2개(001/022)는 "DoD 검증"으로 명시 ✓. 감점: **AC 4건의 `Traces:` 선언이 `spec.md` §6과 불일치**하며 그 결과 REQ-CANC-011(페이지네이션 완전성)을 선언하는 AC가 `acceptance.md`에 **0개**(D11), REQ-CANC-004의 규범 내용 절반이 미커버(D6) |

---

## Defects Found

### BLOCKING

---

**D1. `plan.md`의 `updated_at_min` 전달이 datetime 객체를 URL에 그대로 보간해, 커서가 세팅된 **모든** 감지 사이클이 `InvalidURL`로 실패한다 — 이 SPEC의 주 산출물(상시 감지)이 첫 사이클 이후 영구히 동작하지 않는다.** — Severity: **critical / blocking**

경로를 끝까지 따라가면:

1. `plan.md:232` — 커맨드가 커서 값을 **datetime 객체 그대로** 넘긴다:
   ```python
   updated_at_min=cursor.last_synced_updated_at,
   ```
2. `plan.md:29-30` — `fetch_orders_by_status()`가 그것을 f-string에 raw 보간한다:
   ```python
   if updated_at_min:
       base += f"&updated_at_min={updated_at_min}"
   ```
3. `config/settings/base.py:92,94` — `TIME_ZONE = "UTC"`, `USE_TZ = True` → `cursor.last_synced_updated_at`은 **aware datetime**으로 읽힌다.
4. `str(aware_datetime)` = `"2026-08-10 07:00:00+00:00"` — **공백(0x20)** 과 `+`를 포함한다.
5. `shopify_orders.py:17-19` — 그 문자열이 `urllib.request.Request(url)` → `http.client`로 들어간다. `http.client`는 URL의 제어문자·공백(`\x00-\x20`)을 거부하고 `InvalidURL`을 던진다.

**대조 증거 — 기존 코드는 정확히 이 지점을 방어하고 있다.** `shopify_orders.py:386`:
```python
updated_at_min = last_updated.strftime("%Y-%m-%dT%H:%M:%SZ") if last_updated else None
```
`sync_store()`는 워터마크 datetime을 **호출 전에 ISO 문자열로 포맷**한 뒤 `fetch_all_open_orders()`에 넘긴다(`:388`). `plan.md`는 `fetch_all_open_orders`의 **함수 본문**(문자열을 받는 쪽)만 미러링하고, **호출부의 `strftime` 계약**(`:386`)을 미러링하지 않았다. 프롬프트가 지목한 "저자가 열지 않은 인접 코드 경로" 패턴이 정확히 재현됐다.

**귀결**: 백필(`updated_at_min=None`)과 감지 잡의 **첫** 사이클(커서 NULL)은 정상 동작한다. 첫 사이클이 커서를 세팅한 직후부터, 모든 `(store, list_status)` 조합이 매 사이클 예외 → `transaction.atomic()` 롤백 → 커서 무변경 → `CommandError`(REQ-CANC-017) → **5분마다 영구 반복**. REQ-CANC-005/012/013/014의 실질 기능이 전부 죽는다.

**어떤 AC도 이것을 잡지 못한다**: AC-CANC-008/009(`acceptance.md:161,177`)는 커서가 non-NULL인 유일한 시나리오지만, `_get_with_headers`가 모킹되므로 URL 문자열이 실제 `urllib`에 도달하지 않고, 두 AC 모두 URL 형태를 단정하지 않는다. AC-CANC-015(`:276`)만 URL을 검사하는데 그것은 백필 경로(`updated_at_min` **부재**)다 — 즉 검사 대상이 정확히 반대편이다.

**수정**:
- `spec.md` REQ-CANC-005(`:120-121`)에 직렬화 포맷을 규범으로 명시하라 — "그 값을 `%Y-%m-%dT%H:%M:%SZ` 형식의 ISO-8601 UTC 문자열로 변환해 `updated_at_min`으로 shall 포함한다(`shopify_orders.py:386`의 기존 계약과 동일)".
- `plan.md:232`를 `updated_at_min=cursor.last_synced_updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if cursor.last_synced_updated_at else None`로 정정하거나, `fetch_orders_by_status()` 내부에서 datetime을 받으면 포맷하도록 하라(단, 그 경우 `plan.md:18` 시그니처의 타입 계약을 docstring에 명시할 것).
- **AC를 1건 추가하라**(현재 20개 어느 것도 이 변이를 잡지 못한다): 커서가 non-NULL인 상태로 감지 커맨드를 실행하고, `_get_with_headers`에 전달된 **첫 번째 요청 경로 문자열**에 `updated_at_min=2026-08-10T03:00:00Z` 형태(공백 없음, `T`·`Z` 포함)가 들어있음을 직접 단정.

---

**D2. `~15회 호출` 추정이 SPEC 자신의 §1 표에 의해 반증된다 — 로컬 건수를 Shopify-측 쿼리에 잘못 적용한 파생값이며, 이 수치 위에 3개 결정(D7/Exclusions #6, Exclusions #7, C4)이 얹혀 있다.** — Severity: **critical / blocking**

`spec.md:52`:
> 전체 취소·종료 상태는 **주문 건수(3,109건)가 아니라 상태 목록 페이지 수(~15회 호출)** 로 재구성 가능하다

3,109 ÷ 250 = 12.4 → "~15". 즉 **로컬 DB의 non-open 건수(3,109)를 250으로 나눠서** 얻은 값이다. 그러나 페이지 수를 결정하는 것은 **Shopify가 반환하는 레코드 수**이지 로컬 건수가 아니다. SPEC 자신의 표(`spec.md:38-40`)가 이 오류를 직접 반증한다:

```
Shopify status=cancelled 전체       gimssine 1,170   etoile 21
  └ 로컬에 존재                     gimssine    58   etoile  0
```

→ **Shopify 취소 목록은 그 로컬 교집합(58)의 약 20배다.** 같은 표에서 종료 채널의 하한을 재도출하면:

```
로컬이지만 Shopify open에 없음        3,109   (spec.md:36)
그중 Shopify 취소 목록에 있는 것         58   (spec.md:39)
→ 로컬에 존재하는 "종료(보관)" 주문   3,051   ← 이들은 정의상 Shopify status=closed에 전부 포함된다
```

⇒ **Shopify `status=closed` ≥ 3,051 ⇒ 종료 채널만 ≥ ⌈3051/250⌉ = 13페이지**, 취소 채널 6페이지(1,170→5, 21→1)를 더하면 **총 ≥ 19회**. 그리고 3,051은 "로컬에 있는 것"만 센 **하한**이다 — 취소 채널에서 관측된 20배 비율이 종료 채널에도 적용되면 실제 규모는 수만 건·**100페이지 이상**이 된다.

가정 A6(`spec.md:84`)은 이를 "종료 건수는 미상이나 유사한 규모로 추정"이라고 적는다. **`status=closed`에 대한 프로덕션 카운트는 이 세션에서 한 번도 조회되지 않았다** — 프롬프트가 제공한 실측치에도 `status=cancelled` 카운트만 있다. 즉 A6은 미측정을 "유사 규모"로 단정한 뒤, 그 단정 위에 세 결정을 얹었다:

| 지점 | 의존 내용 | 규모가 10배면 |
|---|---|---|
| §4 D7(`:96`) / Exclusions #6(`:238`) | "`status=` 필터가 이미 충분히 좁히므로 날짜 상한 인자 불필요" | 무제한 백필이 수만 건을 1회 조회로 끌어온다 |
| Exclusions #7(`:239`) | "백필 시 총 ~15회 … 429 재시도/백오프 불필요" | **아래 참조 — livelock** |
| §8 C4(`:251`) | "백필 직후 첫 감지 사이클의 전체 재스윕은 무시 가능" | 매 배포·매 실패마다 반복되는 고비용 스윕 |

**Exclusions #7의 귀결이 D1과 결합하면 livelock이다.** Shopify REST는 버킷 40 / 초당 2 리필이다. 단일 스레드 순차 페이징은 왕복 250ms 기준 초당 ~4회 → 순 유출 2/s → 약 20초 후 버킷 고갈 → 429. 19페이지에서는 안 걸리지만 60페이지 이상에서는 확정적으로 걸린다. `_get_with_headers`(`shopify_orders.py:16-22`)에는 재시도·백오프가 **없고**, 429는 `HTTPError`로 올라와 `plan.md:229`의 `transaction.atomic()`을 롤백시키며, 커서는 NULL로 남는다 → **5분 뒤 다시 처음부터 전체 무제한 스윕**. 영구 재시도 루프이며, C3(`:250`)이 다루는 "개별 레코드 poison"과는 다른 부류라 SPEC 어디에도 서술이 없다.

부수 결함: `plan.md:66-71`이 `shopify_order_id__in=shopify_ids`를 **청킹 없이** 단일 쿼리로 던진다. 수만 건 규모에서 원격 MySQL(≈130ms/쿼리, RDS)에 대한 거대 `IN` 절이 되며, 이는 이 프로젝트가 명시적으로 확립한 배치 쿼리 관례에 어긋난다.

**수정**:
1. `status=closed&limit=1&fields=id`로 gimssine/etoile **양쪽의 실제 페이지 수를 프로덕션에서 측정**하고 그 값을 §1에 기록하라. A6을 측정치로 대체하라("미상이나 유사 규모로 추정"은 삭제).
2. §1:52 / §4 D4(`:93`) / Exclusions #7(`:239`) / C4(`:251`)의 "~15회"를 측정 기반 수치로 전부 재도출하라(로컬 3,109 ÷ 250 유래임을 명시적으로 폐기).
3. 측정 결과가 20페이지를 넘으면 **Exclusions #7(429 백오프 제외)과 Exclusions #6(날짜 상한 제외)을 재판정하라.** 최소한 C3에 "무제한 스윕 실패 시 커서가 NULL로 남아 다음 사이클이 전체 스윕을 반복한다"는 livelock 경로를 신설하고, 완화책(백필 전용 `--updated-at-min` 인자, 또는 감지 잡의 첫 사이클 시딩)을 명시하라.
4. `plan.md:66-71`에 `shopify_ids` 청킹(예: 1,000건 단위)을 명시하라.

---

**D3. `plan.md` §4 위험표 12행 중 10행의 AC 번호가 +1 시프트되어 있다 — 위험↔완화 매핑 전체가 잘못된 AC를 가리킨다.** — Severity: **major / blocking**

`plan.md:450-463`의 각 행을 `acceptance.md`의 실제 AC와 대조했다:

| 행 | plan.md 주장 | 실제 해당 AC | 판정 |
|---|---|---|---|
| R1(`:452`) | AC-015/018이 매뉴얼 필드·LineItem 보존을 단정 | AC-**014**/**017**(`:250,297`) | ✗ +1. **AC-015/018은 매뉴얼 필드를 전혀 단정하지 않는다** |
| R2(`:453`) | AC-003/004 | AC-003/004 | ✓ |
| R3(`:454`) | AC-011/**021**이 2페이지 응답을 모킹 | AC-**010**/**020** | ✗ +1. **AC-CANC-021은 존재하지 않는다**(AC는 001–020) |
| R4(`:455`) | AC-012가 2페이지 요청의 `fields=`를 단정 | AC-**011**(`:203`) | ✗ +1 |
| R5(`:456`) | AC-007이 `StoreSyncWatermark` 무변경 | AC-007 | ✓ |
| R6(`:457`) | AC-009(빈 배치) / AC-010(비지 않은 배치) | AC-**008**/**009** | ✗ +1 |
| R7(`:458`) | AC-010이 두 커서 독립성 | AC-**009**(`:171`) | ✗ +1 |
| R8(`:459`) | AC-013이 조합별 실패 격리 | AC-**012**(`:220`) | ✗ +1 |
| R9(`:460`) | AC-014가 `CommandError` 단정 | AC-**013**(`:235`) | ✗ +1 |
| R10(`:461`) | AC-019가 멱등성 | AC-**018**(`:312`) | ✗ +1 |
| R11(`:462`) | AC-020이 커서 무변경 | AC-**019**(`:327`) | ✗ +1 |
| R12(`:463`) | AC-017이 `--dry-run` 무변경 | AC-**016**(`:282`) | ✗ +1 |

R2/R5만 우연히 일치한다(시프트 이전 번호대와 겹치는 구간). 이 표는 구현자가 "각 위험이 어떤 테스트로 막히는가"를 확인하는 유일한 장치인데, 10행이 다른 AC를 가리키고 1행은 없는 AC를 가리킨다.

**같은 부류의 2차 드리프트** — `plan.md` §2 마일스톤의 테스트 파일↔AC 배정이 `acceptance.md`와 전면 불일치:

| 파일 | `acceptance.md:3` + DoD(`:415-417`) | `plan.md` §2 |
|---|---|---|
| `test_spec_029.py` | AC-001~011 | AC-001~006, 011, **012, 015, 018**(`:390,398`) |
| `test_sync_order_cancellations_command.py` | AC-012~014 | AC-007~**010**, 013, 014(`:402,405`) |
| `test_backfill_order_cancellations_command.py` | AC-015~020 | AC-016, 017, 019, 020(`:409,412`) — **015/018 누락** |

`plan.md:13`이 스스로 경계한다고 선언한 "SPEC-ORDER-028 감사가 반복 지적한 문서 간 정합 어긋남"이 같은 문서 안에서 재현됐다.

**수정**: `plan.md` §4 R1/R3/R4/R6/R7/R8/R9/R10/R11/R12의 AC 번호를 전부 -1 정정하고, R3의 `AC-CANC-021`을 `AC-CANC-020`으로 바꿔라. §2 M2/M3/M4의 AC 배정을 `acceptance.md:3`/DoD와 일치시켜라(M2→001–011, M3→012–014, M4→015–020).

---

**D4. AC 20개 중 4개(AC-007/016/018/019)가 양성 대조군 없이 공허 통과 가능하며, 이는 `acceptance.md`가 스스로 [HARD]로 금지한 바로 그 형태다.** — Severity: **major / blocking**

`acceptance.md:9`가 [HARD]로 규정한다:
> "필드가 그대로 `NULL`이다"라는 단정만 단독으로 쓰면, 코드가 **아무것도 하지 않는** 변이(no-op)에서도 트리비얼하게 통과한다. 이 문서는 그런 단정을 항상 "다른 필드가 실제로 값을 얻었다"는 **양성 증거**와 짝지어 배치한다.

이 규약을 지킨 AC(003/004/014/017)와 어긴 AC를 구분하면:

| AC | Then 단정(`acceptance.md`) | "커맨드가 아무것도 하지 않는" 변이 |
|---|---|---|
| **AC-007** (`:150`) | `StoreSyncWatermark`의 두 필드가 실행 전과 동일 | **통과.** Given(`:146`)은 "변경 있는 레코드 포함"을 모킹하지만, 그 레코드가 실제로 반영됐다는 단정이 **없다** |
| **AC-016** (`:291`) | `cancelled_at is None` | **통과.** 게다가 `None`은 **모델 기본값**(`models.py:80`) — `:9`가 명명한 "기본값 함정" 그 자체. 본문이 "stdout에 would_change 보고가 나타나지만"이라 적으면서도 그것을 **단정으로 만들지 않았다** |
| **AC-018** (`:321`) | 두 실행 후 값이 동일 + `count()==1` + 예외 없음 | **통과.** Given(`:317`)은 모킹 레코드의 `cancelled_at` **값을 지정조차 하지 않는다**. 첫 실행이 아무것도 안 써도 "두 실행 후 값 동일"(None==None)·`count()==1`·무예외가 전부 참 |
| **AC-019** (`:336`) | 커서 두 필드 + `count()` 무변경 | **통과.** 같은 구조 |

`acceptance.md:11`은 추가로 [HARD] "커서 전진을 성공의 증거로 쓰지 않는다"를 규정하지만, **그 역방향**(커서 무변경을 실패 없음의 증거로 쓰는 것)에 대한 방어가 없어 AC-007/019가 빠져나간다. `acceptance.md:382`는 "M1~M20 전부 최소 1개 AC가 잡으며, 20개 전부 단독 판별자다"라고 선언하는데, M7/M16/M18/M19는 **단독 판별자가 아니라 공허 통과 가능한 단측 단정**이다. 이는 SPEC-ORDER-028 review-4의 D4(AC-RSW-035b 단측)와 **동일 부류의 재발**이다.

**수정**(각 AC에 한 줄씩):
- AC-007 Then에 추가: "**그리고** 해당 `Order.cancelled_at`이 모킹 레코드 값으로 갱신됐다(감지 잡이 실제로 일을 했음을 증명)".
- AC-016 Then에 추가: "**그리고** stdout에 `order 90015` + `would_change` 보고가 포함된다(조회·diff는 실제로 수행됐음을 증명)".
- AC-018 Given에 모킹 `cancelled_at` 구체값을 명시하고, Then에 "**그리고** 첫 실행 직후 `cancelled_at == <그 값>`"을 추가.
- AC-019 Then에 추가: "**그리고** 해당 대상 주문의 `cancelled_at`이 갱신됐다".
- `acceptance.md:11` [HARD] 규약에 역방향 문장을 추가: "'커서/워터마크 무변경' 단정도 단독으로 쓰지 않는다 — 항상 같은 시나리오에서 `Order.cancelled_at`/`closed_at`이 실제로 갱신됐다는 양성 증거와 짝짓는다."

---

### MAJOR

**D5. 5분 트리거 + 무제한 첫 사이클 조합에 자기중복 실행 방지 요구가 없고, `plan.md` §1.5의 `.bat`이 원본의 중복 실행 경고를 누락했다.** — Severity: major

`scripts/sync_orders.bat`(실물 확인)의 3–4행:
```
REM Registered in Windows Task Scheduler; do not run two copies at once --
REM the task must be configured with "Do not start a new instance".
```
`plan.md:355-358`의 신규 `.bat`은 이 두 줄을 **가져오지 않았고**, `:374`의 등록 절차도 "트리거 5분 간격"만 지정할 뿐 "새 인스턴스를 시작하지 않음" 설정을 요구하지 않는다. REQ-CANC-022(`spec.md:181-182`)가 열거하는 미러링 항목은 "작업 디렉터리 고정, `PYTHONIOENCODING`, 전용 로그, 종료 코드 전파" 4개뿐 — **동시 실행 정책이 빠져 있다.**

D2와 결합하면 실질 위험이 된다: 커서 NULL 상태의 첫 사이클(또는 D2의 livelock 중 매 사이클)이 5분을 초과하면 두 번째 인스턴스가 겹쳐 뜨고, 두 인스턴스가 같은 `(store, list_status)` 커서 행에 `get_or_create` + `save`를 수행한다. `plan.md:229`의 `transaction.atomic()`은 **HTTP 페이징 전체를 감싸므로**(`:230-233`에서 `reconcile_order_status_batch`가 내부적으로 전 페이지를 가져온다) 락 보유 시간이 API 왕복 횟수에 비례한다.

**수정**: REQ-CANC-022의 미러링 항목에 "작업 스케줄러 '새 인스턴스를 시작하지 않음' 설정"을 추가하고, `plan.md:355-358`에 원본의 2줄 REM을 복원하라. 부수적으로, `transaction.atomic()` 범위를 HTTP 페이징 뒤(쓰기 직전)로 좁힐 것을 검토하라 — `plan.md:100-101`의 `bulk_update` + `:243`의 `cursor.save()`만 원자적이면 충분하며, 현재 설계는 필요 이상으로 넓다.

---

**D6. `status=` 파라미터가 올바른지 단정하는 AC가 0개다 — `status=open`으로 조회하는 변이나 cancelled/closed를 뒤바꾸는 변이가 20개 AC 전부를 통과한다.** — Severity: major

`fetch_orders_by_status()`(`plan.md:28`)가 만드는 `orders.json?status={status}&limit=250&fields={fields}`에서, `status` 값이 URL에 올바로 들어가는지를 검사하는 AC가 없다. `acceptance.md`에서 요청 문자열을 검사하는 AC는 정확히 2개인데:
- AC-011(`:212`) — **두 번째** 호출의 `fields=`만
- AC-015(`:276`) — `updated_at_min=` **부재**만

`_get_with_headers`가 모킹되므로 반환 레코드는 URL과 무관하게 픽스처가 정한 값이다. 따라서 `status=open`으로 조회하는 변이(기존 `fetch_all_open_orders`(`shopify_orders.py:34`)를 복사하며 `status=open`을 남기는, **가장 현실적인** 복사-붙여넣기 실수)는 **전 AC 통과**한다. 프로덕션에서는 취소 데이터를 한 건도 못 가져온다.

같은 구멍이 REQ-CANC-004(`spec.md:117-118`)의 규범 내용 절반을 미커버로 만든다 — "매 요청에 `fields=...`를 shall 포함"에서 **첫 페이지의 `fields=`를 단정하는 AC가 없다**(AC-011은 두 번째 호출만). `spec.md:204`는 REQ-004 → AC-001/002로 매핑하지만, AC-001/002(`:60,75`)는 결과 필드값만 단정하고 요청 형태를 전혀 보지 않는다.

추가로, AC-009/012는 "`status=cancelled` 조회는 X를, `status=closed` 조회는 Y를 반환"하도록 **채널별로 다른 모킹**을 요구하는데(`:177-178`, `:225`), 그 디스패치 키가 URL인지 호출 순서인지 명시되지 않았다. 호출 순서로 구현하면 채널 스왑 변이도 통과한다.

**수정**: AC-001에 "`_get_with_headers` **첫 번째** 호출 경로에 `status=cancelled`와 `fields=id,cancelled_at,closed_at,updated_at`이 **둘 다** 포함된다"를, AC-002에 `status=closed` 대응 단정을 추가하라. `acceptance.md:42`의 픽스처 규약에 "채널별 모킹은 반드시 **요청 경로 문자열의 `status=` 값**으로 디스패치한다(호출 순서로 디스패치하지 않는다)"를 [HARD]로 명시하라.

---

**D7. AC-CANC-005의 픽스처가 그 AC의 핵심 주장("어느 순서로 실행되어도 같은 최종값")을 반증 불가능하게 만든다.** — Severity: major

`acceptance.md:116`의 Given은 취소 채널과 종료 채널이 **완전히 동일한 dict**를 반환하도록 설정한다:
> `status=cancelled` 조회 모킹 응답과 `status=closed` 조회 모킹 응답 **둘 다** 동일 레코드를 반환: `{"id": 90005, "cancelled_at": "…T00:00:00Z", "closed_at": "…T00:05:00Z", …}`

두 응답이 동일하면 `plan.md:96-97`의 두 컬럼 대입은 두 번 다 같은 값을 쓰므로 **순서 독립성은 정의상 참**이 되고, `:120`의 "두 호출 중 어느 순서로 실행되어도 같은 최종값이다"는 단정은 어떤 구현으로도 실패할 수 없다.

이 AC가 실제로 겨눠야 하는 위험은 D2에서 나온다: **`status=closed` 응답이 실제로 `cancelled_at`을 채워서 돌려주는지가 미검증**이다. `spec.md:50`이 프로덕션 검증했다고 적은 쿼리는 `status=cancelled` **하나뿐**이며, 프롬프트가 제공한 실측치에도 `status=closed` + `fields=` 조합의 응답 샘플은 없다. 그런데 §4 D2(`spec.md:91`)는 "Shopify 자신이 이미 두 필드를 함께 반환한다"를 설계의 토대로 삼고, 가정 A1(`:79`)은 두 채널 모두 프로덕션 검증됐다고 **과잉 주장**한다.

만약 `status=closed` 응답이 취소된 주문에 대해 `cancelled_at: null`을 반환한다면, 취소 채널이 방금 쓴 `cancelled_at`을 종료 채널이 **NULL로 되돌린다** — 이 SPEC의 주 목적(52건 반영)이 조용히 무효화된다. 현재 픽스처는 이 시나리오를 구조적으로 재현할 수 없다.

**수정**: (a) `status=closed&limit=1&fields=id,cancelled_at,closed_at` 응답을 **취소된 주문 1건에 대해** 프로덕션에서 확인하고 결과를 §1과 A1에 기록하라(A1의 "두 채널 모두 검증" 주장을 실제와 일치시킬 것). (b) AC-005의 Given을 비대칭으로 바꿔라 — 종료 채널 응답의 `cancelled_at`을 취소 채널과 다른 값(또는 `None`)으로 두고, Then에서 어느 값이 최종 승자여야 하는지를 명시적으로 단정하라. 그래야 이 AC가 판별력을 갖는다.

---

**D8. `spec.md`의 내부 상호참조 오류 3건 — 근거가 없는 명제가 가정·설계결정에 귀속되어 있다.** — Severity: major

| 지점 | 주장 | 실제 |
|---|---|---|
| `spec.md:29` | "`orders/{id}.json` … 이 엔드포인트는 상태와 무관하게 항상 그 주문을 반환한다**(가정 A1)**" | A1(`:79`)은 **목록 엔드포인트의 `fields=` 파라미터**에 관한 것이다. "단건 엔드포인트가 취소된 주문도 반환한다"는 명제는 §3 가정표 A1–A6 **어디에도 없고 검증되지도 않았다**. 미검증 전제가 검증된 가정으로 위장돼 있다 |
| `spec.md:252` (C5) | "5분 주기를 권장하지만(**§4 D6**, `sync_orders`와 동일 주기)" | D6(`:95`)은 **별도 스케줄러 등록과 장애 격리**만 다루며 주기를 한 글자도 언급하지 않는다. 5분은 `plan.md:374`에만 있고 **어떤 REQ도 주기를 규정하지 않는다** |
| `spec.md:205` | 추적표: `REQ-CANC-005 \| AC-CANC-009` | AC-009(`acceptance.md:173`)의 `Traces:`에는 REQ-005가 있으나(✓), **동일 행에서 `spec.md:202`가 REQ-CANC-002 → AC-009도 주장**하는데 AC-009의 `Traces:`에 REQ-002가 **없다** |

`spec.md:29`가 특히 중요하다 — 이 명제는 §1이 "유일한 예외"로 제시하는 기존 경로의 근거이자, D5(재오픈 처리)의 배경 논리다.

**수정**: (a) `spec.md:29`의 `(가정 A1)`을 제거하고 §3에 가정 A7을 신설하라("`orders/{id}.json`은 취소·종료 상태와 무관하게 주문을 반환한다 — 이 세션 미검증, 틀리면 `OrderResyncView`의 취소 주문 재동기화가 실패한다"). (b) C5의 `§4 D6` 참조를 `plan.md §1.5`로 정정하거나, 권장 주기를 §4에 결정으로 신설하라. (c) 추적표 REQ-CANC-002 행을 AC-008 단독으로 정정하라(D11 참조).

---

### MINOR

**D9. `(Unwanted)` 라벨 오용 4건.** — Severity: minor
REQ-CANC-003(`spec.md:112`), 006(`:123`), 008(`:131`), 020(`:173`)은 `(Unwanted)`로 라벨되어 있으나 EARS Unwanted 패턴("**If** [바람직하지 않은 조건], **then** … shall")의 If/then 구조가 없는 **부정형 Ubiquitous** 문장이다. 같은 문서의 REQ-015(`:157`)·016(`:160`)이 올바른 Unwanted 형태를 보여주므로 대조가 명확하다. 문장 자체는 규범문으로 완전하므로 기능적 영향은 없다.
**수정**: 4건의 라벨을 `(Ubiquitous)`로 정정하거나, If/then 구조로 재작성하라.

**D10. 스케줄러 **실제 등록**을 요구하는 항목이 REQ에도 DoD에도 없다 — 이 프로젝트에서 이미 발생한 실패 모드다.** — Severity: minor(그러나 전례 있음)
REQ-CANC-022(`spec.md:181-182`)는 "등록 **가능한 형태로** shall 제공"만 요구하고, `acceptance.md:437`은 `.moai/project/scheduled-jobs.md` 갱신을 `/moai sync` 단계로 미룬다. DoD 어디에도 Windows 작업 스케줄러 항목이 실제로 등록되고 1회 이상 성공 실행됐음을 확인하는 체크가 없다. `.moai/project/scheduled-jobs.md`가 현재 2개 작업만 열거하고 있는 상태 그대로 구현이 "완료"될 수 있다.
**수정**: DoD에 "`scm_v2 sync_order_cancellations` 작업이 스케줄러에 등록되고 최소 1회 종료 코드 0으로 실행됨을 확인"을 추가하라.

**D11. AC의 `Traces:` 선언 4건이 `spec.md` §6 추적표와 불일치하며, 그 결과 REQ-CANC-011을 선언하는 AC가 0개다.** — Severity: minor(문서 한정, 실질 커버리지 손실 없음)
20개 AC의 `Traces:` 선언을 `spec.md:200-225`와 양방향 대조한 결과 불일치 4건:

| AC | `acceptance.md` 선언 | `spec.md` §6 주장 | 문제 |
|---|---|---|---|
| AC-009(`:173`) | REQ-005, REQ-014 | REQ-002·005·014·015가 AC-009 또는 AC-008 주장 | `spec.md:202`가 REQ-002 → AC-009를 주장하나 AC-009는 REQ-002를 선언하지 않음 |
| AC-010(`:190`) | **REQ-006** | `spec.md:211` REQ-**011** → AC-010 | AC-010은 페이지네이션 **완전성**(REQ-011) 테스트인데 `fields=` 재전송(REQ-006)을 선언 |
| AC-011(`:205`) | **REQ-016**(연계) | `spec.md:206` REQ-**006** → AC-011 | REQ-016은 **조합별 실패 격리**다 — 의미상 전혀 무관 |
| AC-020(`:344`) | **REQ-006**, REQ-018 | `spec.md:211,218` REQ-**011**·018 → AC-020 | 동일 오류 |

귀결: **REQ-CANC-011(페이지네이션 완전성 — 취소 목록만 5페이지, 절단 시 920건 조용히 누락)을 `Traces:`로 선언하는 AC가 하나도 없다.** 실질 검증은 AC-010/020이 수행하므로 커버리지 자체는 손실되지 않았으나, SPEC-ORDER-028 review-2 N7 / review-4 D1이 두 차례 지적한 "문서 간 추적 불일치"의 **3회째 재발**이다.
**수정**: AC-010 → `Traces: REQ-CANC-011`, AC-011 → `Traces: REQ-CANC-006`, AC-020 → `Traces: REQ-CANC-011, REQ-CANC-018`, AC-009 → `Traces: REQ-CANC-002, REQ-CANC-005, REQ-CANC-014`.

**D12. `plan.md` R10의 `bulk_update` ↔ `auto_now` 서술이 사실과 다르다.** — Severity: minor
`plan.md:461`:
> `Order`에는 `updated_at`이 `auto_now=True`라 실제로 매번 갱신된다

`Order.updated_at = models.DateTimeField(auto_now=True)`는 실재한다(`models.py:90`). 그러나 Django의 `QuerySet.bulk_update()`는 각 필드에 대해 `pre_save()`를 호출하지 않고 in-memory 값을 그대로 `CASE WHEN`으로 쓴다 — `auto_now`는 **발동하지 않으며**, `updated_at`은 `fields=["cancelled_at","closed_at"]`(`plan.md:101`)에 없으므로 아예 건드려지지 않는다. 결론(멱등성 판정)에는 영향이 없으나, 근거 문장이 틀렸다.
**수정**: R10의 괄호 서술을 "`bulk_update()`는 `pre_save()`를 호출하지 않으므로 `auto_now` 필드인 `Order.updated_at`조차 변경되지 않는다 — 두 컬럼 외에는 어떤 부수 변경도 없다"로 정정하라(정정하면 오히려 논거가 강해진다).

**D13. `plan.md:54` docstring의 반환 키 계약이 코드와 불일치.** — Severity: minor
docstring은 `Returns {"scanned": int, "would_change" | "changed": list[dict], …}`라 적지만, 코드(`:63,103`)는 **항상 `"changed"`**를 반환하고 `would_change`는 백필 커맨드의 **출력 라벨**일 뿐이다(`:328`). 구현자가 dry-run 분기에서 다른 키를 만들 오해 여지가 있다.
**수정**: docstring을 `"changed": list[dict]`로 단일화하고, "dry_run에서도 같은 키를 쓰며 라벨링은 호출자 책임"을 명시하라.

---

## 검증 완료 항목 (결함 없음 — 근거와 함께 기록)

프롬프트가 지목한 load-bearing 주장 중 **검증을 통과한 것**들:

1. **"`_sync_single_order()` 경유는 부재 필드를 NULL로 덮어쓴다" — 참이며, SPEC이 오히려 과소 서술했다.** `shopify_orders.py:133-166`의 `defaults`는 전 키가 `order_data.get(...)`이므로 `fields=` 제한 페이로드에서 `order_number`/`name`/`email`/`financial_status`/`total_price`/`note`/`tags`/`cancel_reason`/`shopify_created_at`/`shopify_updated_at`/`processed_at`이 **전부 None**이 된다. 더 나아가 `:287-289`의 stale-삭제가 `line_items` 부재(`order_data.get("line_items", [])` → `[]`)로 인해 **`PurchaseOrder` 미연결 라인아이템을 전량 삭제**한다. SPEC §4 D3(`:92`)/REQ-CANC-008(`:131-132`)의 판정은 정확하고, `plan.md:101`의 `bulk_update(to_update, ["cancelled_at","closed_at"])`은 요구를 만족하는 **진짜 최소 경로**다. AC-014(`acceptance.md:255-261`)가 이 파괴 경로의 최소 재현 픽스처(PO 연결 LineItem)를 정확히 갖췄다 ✓.
2. **불변식 보존 — 선택된 쓰기 경로가 이들 중 어느 것도 경유하지 않음을 소스로 확인.** 매뉴얼 필드 제외(`:140-147` Order.status/ready_to_ship, `:229-230` purchase_status/logistics_status), `original_sku` 보호(`:209-224`, `:256-285`), 입고 상태(`models.py:228` `received_quantity`), 환불 넷팅(`:306-329`) — `bulk_update` 2컬럼 경로는 이 코드들에 도달하지 않는다. **범위 규율 통과.**
3. **A4(재오픈 시 `sync_store()`가 되돌린다) — 우리 코드 측은 참.** `:161-162`가 `defaults`에 있어 무조건 쓰기이며 제외 목록에 없다 ✓. 커서 stranding 검토 결과도 통과: 재오픈은 `updated_at`을 밀어 올리고 `StoreSyncWatermark`는 배치 최댓값으로만 전진하므로(`:440-454`), 재오픈된 주문은 반드시 다음 `status=open` 배치에 들어온다. 결정적으로 `reconcile_order_status_batch()`가 `Order.shopify_updated_at`을 **쓰지 않으므로** `sync_store()`의 시딩 경로(`:376-381`)를 오염시킬 수 없다 — 이 부분은 설계가 정확하다. (다만 Shopify에서 **취소는 되돌릴 수 없으므로** D5/A4/Exclusions #5가 "취소·종료 → 재오픈"을 한 범주로 묶은 것은 취소 쪽에 대해 공허하다. 안전 방향의 과잉 서술이므로 결함으로 계상하지 않는다.)
4. **A5(신규 커서가 `StoreSyncWatermark` 사고를 재현할 수 없다) — 참.** `models.py:566-579` 독스트링의 사고 원인은 **단건 쓰기 경로가 스토어 전역 MAX를 밀어 올린 것**이다(주문 #37413, 28시간, 102건 `#38163`~`#38266` — SPEC A5의 인용 전부 정확). 신규 커서는 `plan.md:225-243` 배치 루프에서만 쓰이고, 백필은 이를 import조차 하지 않으며(`plan.md:347`), 실패 시 `transaction.atomic()` 롤백으로 커서가 남는다(`plan.md:261`) — `StoreSyncWatermark` 독스트링 `:593-595`가 명시한 것과 동일 규율. **이 부류의 재현 경로는 없다** ✓. (단, D2가 지적한 **NULL 커서 + 무제한 스윕 반복**은 다른 부류의 커서 결함이며 미대응 상태다.)
5. **페이지네이션 계약 서술 — 정확.** `_parse_next_page_info()`(`:25-29`), `fetch_all_open_orders`의 다음 페이지 경로(`:44`), `backfill_missing_orders.py:74-77`의 주석 원문("mirroring fetch_all_open_orders's pagination contract: only `limit` and `page_info` are sent on subsequent pages") 및 `:85` — SPEC `:56`/A3(`:81`)/REQ-CANC-006(`:124`)의 인용이 전부 일치하며, `fields=` 상속이 미검증임을 정직하게 명시한 뒤 매 페이지 재전송(`plan.md:38`)으로 회피한 판단은 옳다 ✓.
6. **마이그레이션 의존성 — 정확.** `backend/order/migrations/` 실물 확인 결과 최신은 `0044_lineitem_original_sku.py`. `0045` + 의존성 `0044_lineitem_original_sku`(`spec.md:107`, `plan.md:158-159`) ✓.
7. **`closed_at`/`cancelled_at` 소비처 0곳 — 전수 검색으로 확인.** 쓰기 `shopify_orders.py:161-162`, 선언 `models.py:79-80`, `migrations/0001_initial.py:57-58`, 시리얼라이저 필드 목록 `serializers.py:436`, 프런트 타입 `frontend/src/types/order.ts:224-225` — 그 외 집계·필터·렌더링 0건 ✓. Exclusions #2(`:234`)의 서술과 일치하며, **존재하지 않는 소비처를 가정한 요구사항은 없다** ✓.
8. **모든 인용 line 번호 전수 확인.** `models.py:49-62`(status/ready_to_ship) ✓, `:79-80` ✓, `:228` ✓, `:565-603`·`:586`·`:596` ✓; `shopify_orders.py:16-22`·`25-29`·`32-45`·`72-101`·`104-331`·`133-166`·`140-147`·`161-162`·`209-224`·`229-230`·`256-285`·`287-289`·`306-329`·`334-352`·`355-461`·`389-396`·`436-454` ✓; `sync_orders.py:58-71`·`82-86` ✓; `backfill_missing_orders.py:57-60`·`73-77`·`85`·`94-95` ✓; `views.py:99`·`408` ✓; `serializers.py:436` ✓. **드리프트·허위 인용 0건** — 프롬프트가 경고한 "인용은 정확하나 인접 경로가 비었다" 패턴이 여기서도 그대로 재현됐다(D1/D2/D5가 전부 인접 경로에서 나왔다).
9. **매뉴얼 필드 픽스처의 비기본값 주장 — 전부 검증.** `Order.status` 기본값 None(`models.py:49-54`, `default=` 없음 + `null=True`) vs 픽스처 `"shipped"` ✓; `ready_to_ship` 기본 None(`:62`) vs `True` ✓; `note` 기본 None(`:71`) vs 비어있지 않은 문자열 ✓; `logistics_status` 기본 `"not_shipped"`(`:204-208`) vs `"shipment_confirmed"` ✓; `rack_number` 기본 `""`(`:189`) vs `"A-7"` ✓; `received_quantity` 기본 0(`:228`) vs 2 ✓; `purchase_status` 기본 `"unordered"`(`:190-194`) vs `"in_stock"` ✓. `Order.unique_together = [("shopify_order_id","store_type")]`(`:94`)도 AC-018의 주장대로 실재 ✓. `Order.shopify_order_id`가 `BigIntegerField`(`:31`)이므로 `existing.get(r["id"])`(`plan.md:81`)의 int 키 조회도 성립 ✓.
10. **장애 격리 주장(D6) — 성립.** `scripts/sync_orders.bat` 실물이 `exit /b %RC%`로 종료 코드를 전파하고 `sync_orders.py:83-85`가 `CommandError`를 던지므로, 별도 `.bat` + 별도 작업 항목은 "마지막 실행 결과"를 실제로 분리한다 ✓. `scripts/run_hidden.vbs`도 실재 ✓.
11. **범위 규율 — 위반 없음.** OUT 범위(UI/API 신설, 취소 주문의 라인아이템 결정, `shopify_orders.py:287-289` 주문편집 결함)를 건드리는 요구사항이 25개 중 0개다. REQ-CANC-023/024는 보존 요구이지 변경 요구가 아니며, `plan.md:396`이 "`Order` 이외 모델 참조 금지"를 마일스톤 금지사항으로 못박았다 ✓.

---

## Chain-of-Verification Pass

1차 판정 후 재점검하여 **추가로 발견한 것**:

- **파생 수치를 "인용 정확"으로 끝내지 않고 재도출했는가** → 처음엔 §1의 실측 블록이 프롬프트의 ground truth와 일치하므로 통과 처리했다. 2차에서 **`~15회`가 어디서 나왔는지**를 되짚어 3,109÷250=12.4임을 발견하고, 같은 표의 1,170 대 58(20배) 비율과 3,109−58=3,051을 교차하여 **하한 19페이지**를 도출했다 — **D2는 전적으로 2차 발견이다.** 1차에서는 "종료 건수 미상"을 A6이 정직하게 인정했다고만 읽었다.
- **AC 번호를 표본이 아니라 전건 대조했는가** → 1차에서는 `plan.md` §4를 "위험 목록이 충실하다"로 넘겼다. 2차에서 12행 전부를 `acceptance.md`의 실제 AC와 1:1 대조하여 **10행 시프트 + 존재하지 않는 AC-021**을 발견했다(D3). R2/R5가 우연히 맞아서 표본 검사였다면 확실히 놓쳤을 구조다.
- **저자의 "판별력" 문단이 아니라 변이를 직접 대입했는가** → AC-007/016/018/019에 "커맨드가 아무것도 하지 않는다"를 대입해 네 개 모두 통과함을 확인했다(D4). `acceptance.md:382`의 "20개 전부 단독 판별자" 선언과 `:9,11`의 [HARD] 규약을 대조하지 않았다면 자기 선언을 그대로 수용했을 것이다.
- **모킹이 무엇을 무력화하는지 따졌는가** → `_get_with_headers`가 모킹된다는 사실로부터 "URL의 어느 부분도 자동으로는 검증되지 않는다"를 도출하고, 실제로 URL을 단정하는 AC가 2개뿐임을 확인해 D6과 D1의 "AC가 못 잡음" 근거를 얻었다.
- **타입이 함수 경계를 넘는 지점을 추적했는가** → `cursor.last_synced_updated_at`(datetime) → `plan.md:232` → `plan.md:30` f-string → `shopify_orders.py:17` urllib. `config/settings/base.py:94`의 `USE_TZ=True`를 확인하고 `str(aware_datetime)`에 공백이 들어감을 확정했다. **D1은 이 추적에서만 나온다** — 문서를 한 파일씩 읽는 방식으로는 보이지 않는다.
- **`.bat` 원본과 신규본을 나란히 놓았는가** → `scripts/sync_orders.bat` 실물을 읽고 `plan.md:355-372`와 대조해 "Do not start a new instance" 2줄 누락을 발견(D5). REQ-CANC-022가 미러링 항목을 4개로 열거한 것도 이때 드러났다.
- **`Traces:` 20건을 양방향 대조했는가** → 했다. spec.md §6의 25행과 acceptance의 20개 선언을 전건 대조하여 4건 불일치와 REQ-011 미선언을 확인(D11). SPEC-028 review-4 D1과 동일 부류의 3회째 재발이다.
- **Django 내부 동작을 가정하지 않고 확인했는가** → `bulk_update`의 `pre_save` 미호출을 근거로 `plan.md:461`의 `auto_now` 서술을 반증(D12). 1차에서는 R10을 "결론이 맞으니 통과"로 넘겼다.

1차에서 이미 잡았던 것: D3(부분), D9, D11. 2차 신규: **D1, D2, D4, D5, D6, D7, D8, D12, D13** — blocking 4건 중 **3건이 2차 발견**이다.

---

## Regression Check

Iteration 1이므로 이전 회차 없음. 다만 SPEC-ORDER-028의 4회 감사에서 확정된 결함 **부류**의 재발 여부를 점검했다:

| SPEC-028 결함 부류 | 최종 회차 상태 | SPEC-029에서 |
|---|---|---|
| 문서 간 추적 선언 불일치(review-2 N7 → review-4 D1) | 2회 지적, 1회 재발 | **3회째 재발** — D11(4건) |
| 단측 AC / 공허 통과(review-4 D4) | MINOR로 종결 | **악화 재발** — D4(4건), 게다가 이번엔 문서가 스스로 [HARD]로 금지한 형태 |
| 픽스처 기본값 함정(review-4 D5 계열) | 규약으로 대응 | **규약은 잘 작성되었으나 AC-016이 그 규약을 정면 위반** |
| 인용은 정확한데 인접 경로가 미검토 | 4회 전부 지속 | **재발** — D1(호출부 `strftime`), D2(Shopify vs 로컬 모집단), D5(`.bat` 원본 2줄) |
| 모의 패치 대상 네임스페이스 미명시(review-4 carry-forward) | UNRESOLVED로 이월 | **재발** — `acceptance.md:42`가 관례 재사용만 언급, 패치 네임스페이스 미명시 |

**Stagnation 판정**: 해당 없음(iteration 1). 다만 위 5개 부류 중 **4개가 새 SPEC에서 그대로 재발**했다는 사실은, 개별 결함 수정은 이뤄지되 **부류 차원의 절차가 정착되지 않았음**을 시사한다.

---

## Recommendation

**FAIL. `/moai run` 진입 불가. blocking 결함 4건(D1, D2, D3, D4).**

이 SPEC의 설계 골격 — 목록 엔드포인트 + `fields=` 제한 + 2컬럼 `bulk_update` + 전용 커서 — 은 **옳다**. 위 "검증 완료 항목" 11개가 그 근거이며, 특히 쓰기 경로가 요구를 만족하는 최소 경로라는 점(항목 1·2)과 `StoreSyncWatermark` 사고 부류를 구조적으로 배제한다는 점(항목 4)은 실물 소스로 확인했다. 문제는 골격이 아니라 **골격을 실행 가능한 코드로 옮기는 마지막 한 뼘**과 **그것을 검증한다고 주장하는 AC의 실제 판별력**이다.

### 착수 전 필수 (blocking)

1. **D1 — `updated_at_min` 직렬화.** REQ-CANC-005에 `%Y-%m-%dT%H:%M:%SZ` 포맷을 규범으로 명시하고, `plan.md:232`를 정정하며, **첫 요청 경로 문자열에 공백 없는 ISO 형태가 들어감을 단정하는 AC를 신설**하라. 현재 20개 AC 중 이 변이를 잡는 것이 0개이므로, AC 추가 없이 코드만 고치면 회귀 방어선이 남지 않는다. *이것을 고치지 않으면 상시 감지 잡은 첫 사이클 이후 영구히 동작하지 않는다.*
2. **D2 — `status=closed` 규모 측정.** `orders.json?status=closed&limit=1&fields=id`로 gimssine/etoile 실제 총량을 프로덕션에서 조회하고, A6·§1:52·§4 D4·Exclusions #7·C4의 "~15회"를 전부 재도출하라. 20페이지를 넘으면 Exclusions #6(날짜 상한)·#7(429 백오프)을 재판정하고, C3에 "무제한 스윕 실패 → 커서 NULL 유지 → 다음 사이클 전체 재스윕" livelock 경로를 신설하라. `plan.md:66-71`의 `__in` 청킹도 함께 명시하라.
3. **D3 — `plan.md` §4/§2 번호 정정.** R1/R3/R4/R6/R7/R8/R9/R10/R11/R12 전부 -1, `AC-CANC-021` → `AC-CANC-020`. §2 M2/M3/M4의 AC 배정을 `acceptance.md:3`/DoD와 일치시켜라.
4. **D4 — 공허 통과 4건 봉쇄.** AC-007/016/018/019 각각에 양성 대조군 단정을 1줄씩 추가하고, `acceptance.md:11` [HARD] 규약에 역방향 문장("무변경 단정도 단독으로 쓰지 않는다")을 추가하라. 이것을 미루면 M7/M16/M18/M19가 영구 미커버로 남는다.

### RED 작성 전 반영 (미반영 시 해당 변이 영구 미커버)

5. **D6** — AC-001/002에 첫 요청 경로의 `status=`·`fields=` 단정 추가, `acceptance.md:42`에 "채널별 모킹은 URL의 `status=` 값으로 디스패치" [HARD] 규약 추가. *현재 `status=open` 오타가 20개 AC를 전부 통과한다.*
6. **D7** — `status=closed` 응답의 `cancelled_at` 채움 여부를 프로덕션 1건으로 확인하고 A1의 과잉 주장을 정정한 뒤, AC-005의 Given을 비대칭 픽스처로 교체하라.
7. **D5** — REQ-CANC-022에 "새 인스턴스를 시작하지 않음" 설정을 추가하고 `plan.md:355-358`에 원본 REM 2줄을 복원하라. `transaction.atomic()` 범위 축소도 함께 검토.

### 문서 정합 (코드 영향 없음)

8. **D8** — `spec.md:29`의 `(가정 A1)` 제거 + 가정 A7 신설, C5의 `§4 D6` 참조 정정.
9. **D11** — AC-009/010/011/020의 `Traces:` 4건 정정. *동일 부류 3회째 재발이므로, 개정 시 양쪽 문서를 동시에 손대는 절차를 DoD에 넣는 것을 권한다.*
10. **D9** — `(Unwanted)` 라벨 4건 정정. **D12** — R10의 `auto_now` 서술 정정(정정하면 논거가 강해진다). **D13** — `plan.md:54` docstring 반환 키 단일화.

### 재감사 시 중점

iteration 2에서는 **D1의 AC 신설 여부**와 **D2의 실측 반영 여부**를 먼저 본다. 이 둘은 문서 수정만으로 닫히지 않고 각각 "새 AC 1건"과 "프로덕션 조회 1회"를 요구하므로, 문언만 손질된 채로 올라오면 그 자체가 stagnation 신호다.
