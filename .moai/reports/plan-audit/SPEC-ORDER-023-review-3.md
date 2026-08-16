# SPEC Review Report: SPEC-ORDER-023

Iteration: 3/3
Verdict: **PASS** (구현 착수 가능 — 잔존 결함 8건은 전부 non-blocking, 그중 3건은 RED 작성 시 1~2줄로 닫힌다)
Overall Score: 0.87

Reasoning context ignored per M1 Context Isolation. 이 감사는 `.moai/specs/SPEC-ORDER-023/`의 세 문서(v1.2.0)와
저장소 소스만 사용했다. `review-1.md`와 `review-2.md`는 **재검증 대상 주장**으로만 취급했고 ground truth로
채택하지 않았다 — 실제로 review-1의 판정 2건은 review-2가 오류로 뒤집었고, 이번 감사에서 **review-2의 판정 1건
(L2-new)도 오류**로 확인되었다(아래 "판정 뒤집기"). 저자의 v1.2.0 HISTORY 주장(가드 추가, 표준 데이터셋 동일성,
`TIME_ZONE="UTC"`, 베이스라인 5/6 분기, fail-open 게이트 신설)은 **어느 것도 문서 서술을 근거로 채택하지 않고**
소스·Django 5.2.17 설치본·기계적 파싱으로 직접 재현했다. 물류상태 우선순위 사슬과 표준 데이터셋의 판별력은
저자의 재유도 문단(spec.md:127)을 읽기 전에 `LOGISTICS_STATUS_CHOICES` 실물 위에서 처음부터 다시 유도했다.

**사용자 전제 정정 2건(사실 확인)**:
- "37 REQs and 38 ACs" — 확인됨. 단 **v1.2.0이 추가한 REQ는 0개**다(v1.1.0도 37개였다, review-2 MP-1 참조).
  v1.2.0은 REQ-OLIST-010/011/011a/020/022a **5건을 수정**했을 뿐이며, 하위번호 011a/022a/024a는 모두 v1.1.0 산물이다.
- "Nine ACs were added or rewritten" — 실제로는 **10건**이다: 신규 2건(020a, 022f) + 재작성 6건(022, 022a~022e) +
  확장 2건(026, 027). AC 총수 36 → 38.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: 기계적 추출 결과 `^\*\*REQ-OLIST-\d{3}[a-z]?\*\*` = **37개**, 중복 0건.
  본번호 001~034 연속(결번 없음), 하위번호 3개(011a/022a/024a)만 접미사 사용, 3자리 패딩 일관.
  AC도 동일 방식으로 spec.md 38개 / acceptance.md 38개이며 **두 집합이 `diff` 결과 완전 일치**(중복 0건,
  001~027 연속 + 하위 013a/017a/018a/018b/020a/022a~f). spec.md:353의 "37개 요구사항 전량이 38개 인수 기준으로
  직접 커버된다"는 아래 Traceability 기계 검증에서 **산술·논리 모두 참**으로 확인되었다.

- **[PASS] MP-2 EARS format compliance**: 38개 AC 전량을 기계 파싱한 결과 **모두** 굵게 표시한 EARS 연결어
  (`**While**`/`**When**`/`**If**`)와 `**shall**`을 포함한 완전한 문장이다 — 예: spec.md:261
  "**While** `TIME_ZONE` is overridden to `"Asia/Seoul"` …, the system **shall** report `margin_rate == "67.75"`.",
  spec.md:297 "**While** the standard dataset … exists, and a client requests `?logistics_display=bogus_value`,
  the system **shall** respond HTTP 200 with all 7 orders." 37개 REQ도 전부 유효한 EARS 패턴 + `shall`.
  (라벨 불일치 9건은 아래 L1-new — 문장 패턴 자체는 5종 중 하나에 정확히 대응하므로 MP-2 위반이 아니다.)

- **[PASS] MP-3 YAML frontmatter validity**: spec.md:1-11 — `id: SPEC-ORDER-023`(string), `version: 1.2.0`(string),
  `status: draft`(string), `created_at: 2026-08-16`(ISO date), `priority: High`(string),
  `labels: [order, list, margin, logistics, purchase-status, frontend, backend]`(array). 6개 필수 필드 전부 존재·타입 정확.
  동반 문서 동기화 확인: plan.md:1-7 / acceptance.md:1-7 둘 다 `version: 1.2.0`, `status: draft`, `updated: 2026-08-16`.

- **[N/A] MP-4 Section 22 language neutrality**: Django 백엔드 + React 프론트엔드로 범위가 한정된 단일 프로젝트
  SPEC. 다국어 LSP/툴링 주장 없음. 자동 통과.

---

## Half 1 — 라운드 2 수정의 실제 해소 여부

각 항목은 **저자의 자기 주장이 아니라 소스·기계 검증**으로 판정했다.

| ID | 판정 | 독립 근거 |
|---|---|---|
| **C1-new** (010/011 빈 집합 가드 누락 ⊥ 012) | **해소(완전)** | spec.md:119/121/123에서 REQ-OLIST-010/011/011a 셋 다 `While an order has at least one trackable line item, …`로 시작한다. **아래 "우선순위 사슬 독립 재유도"에서 전수성·배타성을 처음부터 다시 증명**했고, `|T|=0`에서 발화하는 규칙이 REQ-OLIST-012 하나뿐임을 확인했다. 확정된 사용자 결정 5의 한글 서술(spec.md:51)도 "아래 1~5번 규칙은 모두 trackable 라인아이템이 1개 이상 존재함을 전제한다"로 정합화됨. plan.md:127(`if not trackable: return None, None`)·plan.md:56(`has_trackable &`)과 3문서 일관 ✓ |
| **H1-new** (022b/c/e 데이터셋 비특정) | **해소(부분적 잔존 1건 → N1)** | spec.md:270-278과 acceptance.md:280-288의 표준 데이터셋 표를 `diff`로 대조한 결과 **바이트 단위 동일**(Order A~G 7행 전부). 022~022e 전량이 "against the standard dataset(Order A~G 전량)"을 Given으로 명시 ✓. 6개 필터 값의 기대 결과를 데이터셋 위에서 직접 재유도해 `{A}/{B}/{C,D}/{E}/{F}/{G}`가 규칙 사슬과 정확히 일치함을 확인 ✓. **단 `outbound_scheduled` 분기의 any/all mutation만은 이 데이터셋으로 판별되지 않는다 → N1** |
| **H2-new** (규칙 4 경유 `outbound_scheduled` 표시값 미검증) | **해소** | AC-OLIST-022d(spec.md:291, acceptance.md:331)가 "return exactly {Order C, Order D} **and** both Order C's and Order D's `logistics_display` **shall equal** `"outbound_scheduled"`" 이중 단정. 같은 패턴이 022/022a/022b/022c/022e **전량에 전파**되었음을 개별 확인 ✓. 판별력 실검증: 규칙 4의 `outbound_scheduled` 분기를 빠뜨리는 mutation은 D의 표시값이 `partial`이 되어 두 번째 단정에서 실패한다 ✓ |
| **H3-new** (REQ-022a 등식 ⊥ 조건부 스킵) | **해소** | REQ-OLIST-022a(spec.md:155)가 "베이스라인 6(고객 ≥1) 또는 5(전원 customer=null) + **at most 1**(날짜 있으면 정확히 1, 전원 NULL이면 정확히 0)"로 일반화됨. plan.md:49/148의 조건부 스킵 서술과 문언 일치 ✓. AC-OLIST-021의 절대값 7과도 정합(고객 있음 → 6, 날짜 있음 → +1) ✓. **"5" 분기의 근거를 저자 주장이 아니라 Django 소스로 재확인**: `Order.customer`는 forward FK(`models.py:82`)이고, `prefetch_related`가 만드는 `pk__in={None}` 조건은 Django 5.2.17 `db/models/lookups.py:547`("Remove None from the list…") → `:555 raise EmptyResultSet`로 **쿼리가 아예 발급되지 않는다**. 즉 5는 단정이 아니라 유도 가능한 값이다 ✓ |
| **M1-new** (Traceability 표가 AC-011을 REQ-011로 계상) | **해소** | spec.md:325가 `REQ-OLIST-011 | AC-OLIST-008, AC-OLIST-013`으로 정정(AC-011 삭제). **대체 항목의 타당성도 검증**: AC-OLIST-008의 픽스처(단일 trackable, `not_shipped`, sq=0)는 규칙 1/2/3에 걸리지 않고 규칙 4(uniform passthrough)로 판정되므로 REQ-011을 실제로 경유한다 ✓. 아래 기계 검증에서 표 35행 전체를 AC의 `Traces:`와 대조했다 |
| **M2-new** (REQ-024a의 위임 게이트 부재) | **해소** | AC-OLIST-022f 신설(spec.md:297, acceptance.md:343), Traceability 표 `REQ-OLIST-024a | AC-OLIST-022f`(spec.md:341), acceptance.md DoD 매핑표 `AC-OLIST-022f | 024a`(:427), plan.md M1(:37)·M4(:69)·Done 체크리스트(:233) 4곳에 실행 게이트가 실재함을 확인 ✓ |
| **M3-new** (프론트엔드 라벨 1~2/6) | **해소** | AC-OLIST-026이 "exactly 7 `<option>` elements"(spec.md:307), AC-OLIST-027이 6개 값 파라미터화(spec.md:310) 단정. 판별력 근거 실검증: `frontend/src/pages/OutboundPage/logisticsStatusLabels.ts:11-17`은 **5개 키만** 정의하며 `partial_shipped`/`partial`이 실제로 없다 — 스프레드 확장 시 2개 키 누락 mutation이 실재 가능하고 6개 전량 파라미터화가 이를 잡는다 ✓ |
| **M4-new** (022a "그 외 5개 상태" 사실 오류) | **해소** | 해당 문구가 표준 데이터셋 참조로 대체되어 자동 소멸(spec.md:283) ✓ |
| **M5-new / round-1 L7** (`.date()` 시간대) | **해소** | REQ-OLIST-020(spec.md:149)에 "`.date()` 직접 호출, `timezone.localtime()` 금지, `TIME_ZONE` 설정과 무관" 규정 추가 + AC-OLIST-020a 신설. **인용·판별력 전부 독립 검증**(아래 전용 절) ✓ |

### 우선순위 사슬 독립 재유도 (저자의 spec.md:127을 읽기 전에 수행)

trackable 집합 T(`sku is not null`) 위에서 REQ-OLIST-008~012를 처음부터 대입했다.

| 규칙 | 형식화 | 결과 |
|---|---|---|
| 008 | `|T|≥1 ∧ ∀t∈T: ls(t)="shipped"` | `shipped` |
| 009 | `¬008 ∧ ∃t∈T: sq(t)>0` | `partial_shipped` |
| 010 | `|T|≥1 ∧ ¬008 ∧ ¬009 ∧ ∀t: ls(t)="received"` | `outbound_scheduled` |
| 011 | `|T|≥1 ∧ ¬008..¬010 ∧ |{ls(t)}|=1` | 그 값 |
| 011a | `|T|≥1 ∧ ¬008..¬010 ∧ |{ls(t)}|≥2` | `partial` |
| 012 | `|T|=0` | `null` |

- **배타성**: 009는 ¬008로, 010은 ¬008∧¬009로, 011/011a는 ¬008..¬010으로 가드된다. 011과 011a는 `|{ls}|=1`과 `|{ls}|≥2`로 상호 배타. 012는 `|T|=0`, 나머지는 전부 `|T|≥1`. **중첩 0** ✓
- **전수성(`|T|=0`)**: 008/010/011/011a는 명시적 가드로 거짓. **009는 명시적 가드가 없지만** `∃t∈T`가 공집합에서 거짓이므로 안전하다. 012만 발화 → `null` ✓
- **전수성(`|T|≥1`)**: ¬008∧¬009∧¬010이면 `{ls(t)}`는 비어 있지 않으므로 크기 1(011) 또는 ≥2(011a) 중 정확히 하나 ✓
- **치역 닫힘**: 011이 통과시키는 값 v는 `v≠"shipped"`(아니면 008 발화)이고 `v≠"received"`(아니면 010 발화)다. **`backend/order/models.py:8-14`의 `LOGISTICS_STATUS_CHOICES`를 직접 열어 확인한 결과 원시 값은 정확히 5개**(`not_shipped`/`shipment_confirmed`/`received`/`outbound_scheduled`/`shipped`)이므로 v ∈ {not_shipped, shipment_confirmed, outbound_scheduled}. 따라서 치역 =
  **{shipped, partial_shipped, outbound_scheduled, not_shipped, shipment_confirmed, partial, null}** — 저자가 주장한 7개 값과 **정확히 일치하며, 전수적·배타적이다.** ✓ (H5의 구조적 소멸도 재확인)
- **다만 저자의 재유도 문단에는 사실 오류가 하나 있다**: spec.md:127은 "008/009/010/011/011a는 이제 **전부** 'at least one trackable line item'으로 명시적으로 가드되어 있어"라고 쓰는데, **REQ-OLIST-009에는 그 문구가 없다**(존재 한정사로 안전할 뿐이다). 결론은 참이지만 근거 문장이 부정확하다 → N6.

### 표시(Python) ↔ 필터(SQL) 등가성 및 표준 데이터셋 판별력

plan.md:57-67의 `Exists` 조합을 데이터셋 A~G에 대입해 6개 값 전부의 반환 집합을 손으로 계산했다.
결과는 `shipped={A}`, `partial_shipped={B}`, `outbound_scheduled={C,D}`, `not_shipped={E}`,
`shipment_confirmed={F}`, `partial={G}` — **AC-OLIST-022~022e의 기대값과 전부 일치**하며,
데이터셋 자체가 내부 모순 없이 규칙 사슬과 정합한다 ✓.

`any` vs `all` mutation 판별력을 값별로 개별 구성했다(사용자 지정 확인 항목):

| mutation | 결과 | 판정 |
|---|---|---|
| `all_not_shipped` → `Exists(any not_shipped)` | Order G(항목1=`not_shipped`)가 추가되어 {E,G} | **잡힌다**(AC-022b) ✓ |
| `all_shipment_confirmed` → `any` | Order G(항목2=`shipment_confirmed`)가 추가되어 {F,G} | **잡힌다**(AC-022c) ✓ |
| `partial`에서 `¬all_outbound_scheduled` 누락 | Order D 추가 → {D,G} | **잡힌다**(AC-022e) ✓ |
| `partial_shipped`에서 `¬all_shipped` 누락 | Order A 추가 → {A,B} | **잡힌다**(AC-022) ✓ |
| `outbound_scheduled` 이접항 누락(`all_received`만) | Order D 누락 → {C} | **잡힌다**(AC-022d) ✓ |
| **`all_outbound_scheduled` → `Exists(any outbound_scheduled)`** | A(all_shipped 제외), B(any_partial 제외), C/D 그대로, E/F/G에 `outbound_scheduled` 항목 없음 → **{C,D} = 기대값** | **잡히지 않는다 → N1** |

즉 **데이터셋에 `outbound_scheduled`를 포함한 혼재(mixed) 주문이 없어**, 여섯 개 uniform 검사 중
`outbound_scheduled` 하나만 any/all 구분이 무방비다. 하필 이 값은 plan.md:64가 유일하게 이접 조건으로
특별 취급하는 값이며, `Exists(...filter(logistics_status=X))`라는 **양성 Exists를 자연스럽게 쓰게 되는
유일한 분기**여서 mutation 발생 확률이 가장 높은 지점이다.

### AC-OLIST-020a (시간대 경계) — 전량 독립 검증

- **배포 설정**: `backend/config/settings/base.py:92` = `TIME_ZONE = "UTC"`, `:94` = `USE_TZ = True`.
  저장소 전체에서 `TIME_ZONE`을 재정의하는 다른 설정 파일 없음(`grep -rn` 확인). **인용 정확** ✓
- **은폐 논거 성립**: `USE_TZ=True`이면 ORM이 반환하는 datetime은 UTC-aware이므로
  `shopify_created_at.date()`와 `timezone.localtime(...).date()`가 `TIME_ZONE="UTC"`에서 **항상 같은 값**이다.
  따라서 배포 설정 그대로는 이 mutation이 관측 불가능하며, `override_settings`가 판별력의 **필수 조건**이라는
  저자 주장은 옳다 ✓
- **판별력 손계산**(`_compute_cost_breakdown_uncached`, `serializers.py:298-360`에 직접 대입):
  정답 경로(rate=1000) → `confirmed=30000/1000=30.00`, `shipping=5.45×0/1000=0`,
  `korea=(1250+500×2)/1000=2.25`, `margin=100−30−0−2.25=67.75` → `"67.75"`.
  mutation 경로(KST 변환 → 2026-08-02 → rate=1200) → `25.00 / 0 / 1.875` → `margin=73.125` → `"73.13"`.
  **두 값이 명확히 갈린다 → 진짜 판별력** ✓
- **정상 구현에서 실패하지 않는가**: `override_settings(TIME_ZONE=...)`는 `USE_TZ=True`에서 DB 커넥션 타임존
  (UTC)을 바꾸지 않으므로, `.date()`를 쓰는 올바른 구현은 그대로 통과한다 ✓
- **인용 정확성**: REQ-OLIST-020이 근거로 든 `serializers.py:248`을 직접 열어
  `order_date = obj.shopify_created_at.date()`임을 확인 ✓ (`:245` = `if not obj.shopify_created_at:`도 정확)

### AC-OLIST-022f (fail-open 게이트) — 실재 및 검증 가능성

- 게이트 실재 확인 ✓(위 M2-new). 판별력: 화이트리스트 없이 값을 그대로 매핑해 0건을 반환하는 mutation은
  "7건 전부" 단정에서 실패한다 ✓
- **다만 이 AC는 오늘의 무수정 코드에서도 통과한다** — `OrderListView.get_queryset`(`views.py:161-218`)은
  현재 `logistics_display` 파라미터를 읽지 않으므로 `?logistics_display=bogus_value`는 이미 200 + 전체를 반환한다.
  즉 RED 신호가 없는 회귀형 AC다. SPEC이 이를 인지하고 plan.md:233에 **mutation 검증 항목**을 별도로 두고 있어
  결함으로 올리지는 않으나, 구현자는 "022f가 RED에서 초록이어도 정상"임을 알아야 한다 → N9(정보).

---

## Half 2 — 라운드 2가 새로 바꾼 것에 대한 신규 감사

### 신규/재작성 AC 10건 mutation 테스트

| AC | no-op / 상수 / 미작업 구현으로 통과 가능한가 | 판정 |
|---|---|---|
| AC-020a | 불가 — `margin_rate` 키 자체가 없으면 실패, 하드코딩 `"67.75"`는 AC-019(Y=68.20)·017a(86.02)·018a(null)와 동시에 만족 불가 | 강함 ✓ |
| AC-022 | 불가 — 필터 미구현이면 7건 반환, 표시값 단정도 필요 | 강함 ✓ |
| AC-022a | 불가 — 동일 | 강함 ✓ |
| AC-022b | 불가 — `any` mutation을 Order G가 잡는다 | 강함 ✓ |
| AC-022c | 불가 — `any` mutation을 Order G가 잡는다 | 강함 ✓ |
| AC-022d | 불가 — 필터 누락·표시값 누락 양쪽 판별 | 강함 ✓ (단 `any` 변형은 N1) |
| AC-022e | 불가 — Order D가 `¬all_outbound_scheduled` 누락을 잡는다 | 강함 ✓ |
| **AC-022f** | **가능 — 필터를 아예 구현하지 않으면 통과**(오늘 코드에서 이미 초록) | 회귀형, N9 |
| AC-026 | 불가 — 7개 옵션 전량 + 쿼리 파라미터 전달 이중 단정 | 강함 ✓ |
| AC-027 | 불가 — 6개 라벨 파라미터화 + null 폴백 + `tsc -b` | 강함 ✓ |

**정상 구현에서 실패하는 AC 0건**(10건 전부 손으로 정답 경로를 계산해 통과 확인).
**오늘 코드에서 통과하는 AC 1건**(022f, 설계상 불가피한 fail-open 회귀 AC).

### Traceability 기계 검증 (renumbering 이후)

파이썬 파서로 spec.md 38개 AC의 `Traces:` 목록, acceptance.md 38개 AC의 `Traces:` 목록, spec.md의
Traceability 검증표 35행을 전부 추출해 교차 대조했다.

- spec.md ↔ acceptance.md의 `Traces:` **38/38 완전 일치**(불일치 0건) ✓
- 실재하지 않는 REQ를 참조하는 AC **0건**(고아 AC 0건) ✓
- `Traces:`로 커버되지 않는 REQ **0건**(37/37 전부 ≥1 AC) ✓
- 검증표 35행 ↔ AC `Traces:` 역맵 대조: **불일치 1건**(REQ-OLIST-024 행이 AC-OLIST-026을 계상하지만
  AC-OLIST-026의 `Traces:`는 REQ-026/027만 적는다). AC-026은 실제로 REQ-024의 6개 값을 옵션으로 단정하므로
  **표가 과장한 것이 아니라 AC의 `Traces:`가 누락된 방향**이다 → N7(Low)
- **M1-new가 지적한 "표가 실제로 커버하지 않는 AC를 계상" 유형은 재발하지 않았다.** 다만 표의
  `REQ-OLIST-013 | AC-OLIST-011, AC-OLIST-014`에서 AC-011은 REQ-013을 **부정 방향으로만** 검증한다
  (그 픽스처는 REQ-014를 발화시킨다). AC-011이 REQ-013의 trackable 가드 누락 mutation을 실제로 판별하므로
  M1-new와 같은 공허한 계상은 아니다 — 결함으로 올리지 않는다.

### v1.1.0 이후 신규/변경 `file:line` 인용 전량 재검증

| 인용 | 위치 | 검증 결과 |
|---|---|---|
| `backend/config/settings/base.py:92` (`TIME_ZONE="UTC"`) | spec.md:149,261 / acceptance.md:260,263 / plan.md:147 | `TIME_ZONE = "UTC"` — **정확** ✓ |
| `serializers.py:248` (`.date()` 호출 지점) | spec.md:149 / plan.md:147 | `order_date = obj.shopify_created_at.date()` — **정확** ✓ |
| `serializers.py:245` (`shopify_created_at` 게이트) | spec.md:141 | `if not obj.shopify_created_at:` — **정확** ✓ |
| `serializers.py:322` (`total_price or "0"`) | spec.md:141 | `total_price_usd = Decimal(str(obj.total_price or "0"))` — **정확** ✓ |
| `models.py:77` (`shopify_created_at` nullable) | spec.md:155 | `shopify_created_at = models.DateTimeField(null=True, blank=True)` — **정확** ✓ |
| `views.py:163` (`-shopify_created_at` 정렬) | spec.md:155 | `.order_by(` 162행, `"-shopify_created_at"` 163행 — **정확** ✓ |
| `views.py:162` (prefetch 3종) | spec.md:151,155 | `prefetch_related("refunds", "line_items", "customer")` — **정확** ✓ |
| `views.py:171-173`, `:186-191` (무수정 파라미터) | spec.md:163,187 | 171~173 `financial_status`, 186~191 `fulfillment_status`(unfulfilled 분기 포함) — **정확** ✓ |
| `models.py:8-14` (`LOGISTICS_STATUS_CHOICES`) | spec.md:393 | 8~14, 정확히 5개 값 — **정확** ✓ |
| `models.py:193` / `:207` (기본값) | spec.md:223 / :33 | `default="unordered"` 193행, `default="not_shipped"` 207행 — **정확** ✓ |
| `models.py:501` / `:507` | spec.md:359 / acceptance.md:244 | `effective_date = models.DateField(unique=True)` 501행, `db_table = "orders_exchangerate"` 507행 — **정확** ✓ |
| `models.py:82` (`Order.customer` FK) | (감사가 직접 확인) | `customer = models.ForeignKey(` — forward FK 확인, 베이스라인 5/6 논거의 전제 ✓ |
| `shopify_orders.py:130-143` / `:140-143` | spec.md:33 | 130 `update_or_create(`, 140-143 "status intentionally excluded" 주석 — **정확**(plan.md:272는 같은 대상을 `:130-147`로 인용, 둘 다 유효 범위 — L6-new 잔존) |
| `logisticsStatusLabels.ts` 5키 | plan.md:84 | 11~17행, `Record<string, string>`, `partial_shipped`/`partial` **없음** — **정확** ✓ |
| `OrdersPage.tsx:81-94`, `:96-104`, `:293` | spec.md:81 / plan.md:78-82 | 81~94 `getDisplayStatus`(82 refunded / 83 partially_refunded / 85 has_refund / 86-93 라벨 맵), 96~104 `getFulfillmentLabel`, 293 `colSpan={8}` — **정확** ✓ |
| Django 5.2.17 (`poetry.lock:168`) | spec.md:369 / plan.md:278 | poetry 가상환경 `django/__init__.py` = `VERSION = (5, 2, 17, "final", 0)` — **정확** ✓ |

**날조 인용 0건. 3회 연속.** 이 저장소의 과거 사고(존재하지 않는 경로 날조 2건)와 같은 유형은 재발하지 않았다.

### 비목표 재유입 점검

- **마진 정렬/범위 필터**: 어떤 REQ에도 없음. 제약사항(spec.md:380)·Exclusion(:388)이 명시적으로 금지 ✓
- **발주상태 필터**: `grep` 결과 결정 8(spec.md:60)·Exclusion(:389)·후속 과제 2(:400) 세 곳 전부 "만들지 않는다"
  방향이며, REQ·AC·plan.md 어디에도 `purchase_display` 쿼리 파라미터가 없다 ✓
- **부분출고 사유 분류**: Exclusion(:390)·후속 과제 3(:401)뿐, 사유 필드를 만드는 REQ 없음 ✓
- **OrderDetail 동작 변경**: REQ-OLIST-033 + 범위 델타 `[EXISTING]`(:76) + Exclusion(:391) + plan.md:104
  "순수 추출 리팩터링만" ✓
- **밀수 없음.** v1.2.0이 추가한 것은 AC 2건과 REQ 5건의 한정어뿐이며, 전부 기존 범위를 **좁히는** 방향이다 ✓

### L1-new ~ L8-new 재검토 — 실제로 차단급인가

사용자가 이번 라운드 범위 밖으로 지정해 손대지 않은 항목들을 **연기 가능성 기준으로 다시 판정**했다.

| ID | 현재 상태 | 재판정 |
|---|---|---|
| L1-new (AC 라벨 불일치) | **잔존, 9건**(004/005/017/021/023/024/025/026이 `Ubiquitous`인데 `**While**`, 027이 `Event-Driven`인데 `**While**`) | 연기 가능. MP-2는 문장 패턴 기준이며 전부 통과. 구현에 영향 0 |
| L2-new (REQ-011 괄호 논거) | **잔존** | **결함이 아니다 — review-2의 판정을 뒤집는다.** REQ-011은 `¬010`으로 가드되고, `|T|≥1 ∧ ¬008 ∧ ¬009 ∧ ¬010`이면 정의상 `¬(∀t: received)`이므로 "REQ-010이 uniform-received 케이스를 소진한다"는 서술은 **참**이다. review-2가 지목한 009는 그 부분집합(sq>0)을 먼저 소진할 뿐이다 |
| L3-new (AC-021 mutation 서술 자기모순) | **잔존**(spec.md:266) | 연기 가능. acceptance.md:272의 정확한 서술(1건→7, 5건→11)이 병존하므로 구현자가 오도될 위험 낮음 |
| L4-new (`order_cancelled` AC 부재) | **잔존** | 연기 가능하나 **주의**: 명시적 가정 4(spec.md:67)가 "이것이 원하는 동작인지는 사용자 확인이 필요"라고 스스로 적는다. 미해결 제품 결정이 SPEC에 남아 있다는 뜻이며, `ready_to_ship` 관례(제외)로 구현하는 mutation은 표시값이 `null`로 갈리는데 어떤 AC도 잡지 못한다. 표시 전용·후속 과제 4로 문서화됨 → 차단 아님 |
| L5-new (AC-002 판별력 서술) | **잔존**(acceptance.md:41) | 연기 가능. 단정 문구 자체는 정확 |
| L6-new (`shopify_orders.py` 인용 범위 불일치) | **잔존** | 연기 가능. 둘 다 유효 범위 |
| L7-new (DoD 매핑표 REQ-013 누락) | **해소됨** | acceptance.md:418이 `007~010, 013(AC-011의 purchase_display 단정분)`으로 정정됨 — 저자가 "Low는 손대지 않았다"고 적었으나 이 1건은 실제로 고쳐졌다 |
| L8-new (REQ-024a "unfiltered result set" 모호) | **잔존** | **가장 실질적인 Low.** "ignore the filter and return the unfiltered result set"은 "다른 필터까지 무시"로도 읽힌다. `?financial_status=paid&logistics_display=bogus`에서 전체를 반환하는 구현이 문언상 허용되고 AC-022f(단일 파라미터)는 이를 판별하지 못한다. 다만 plan.md:69가 "이 annotation들 자체를 건너뛰고"로 명확히 해소하므로 → **연기 가능, 단 3단어 수정 권장** → N3 |

**결론: L1-new~L8-new 중 구현을 차단해야 할 만큼 심각한 항목은 없다.** L8-new만이 프로덕션 동작에
닿을 수 있는 유일한 항목이며, plan.md가 이미 disambiguate한다.

---

## Defects Found

### Major (차단은 아니나 RED 작성 시 반드시 반영 권장)

**N1. spec.md:270-278 / acceptance.md:280-288 (표준 데이터셋) — `outbound_scheduled` 분기의 any/all mutation이
데이터셋으로 판별되지 않는다. 데이터셋의 "6개 값 전량 포괄" 주장은 판별력 관점에서 과장이다.**

데이터셋의 유일한 혼재(mixed) 주문 G는 `{not_shipped, shipment_confirmed}`다. 따라서
`all_not_shipped`/`all_shipment_confirmed`를 `Exists(any …)`로 바꾸는 mutation은 잡히지만,
`all_outbound_scheduled` → `Exists(any outbound_scheduled)` mutation은 **A~G 어디에도 걸리지 않는다**
(상세 계산은 Half 1의 판별력 표 마지막 행). 그 결과 프로덕션에서 `{outbound_scheduled, not_shipped}`처럼
`outbound_scheduled`를 포함한 혼재 주문(표시값 `부분입고`)이 **"출고예정" 필터 결과에 잘못 섞여 나온다.**
필터와 표시가 갈리는 바로 그 결함(설계 결정 B가 막으려는 것)이며, 하필 이 값이 plan.md:64에서
유일하게 이접 조건으로 처리되어 양성 `Exists`를 쓰기 쉬운 분기다.

**정정(택1, 어느 쪽도 1행 수정)**: (a) Order G를 `{outbound_scheduled, not_shipped}`로 바꾸고
`shipment_confirmed` 판별용 Order H를 1건 추가, 또는 (b) 데이터셋에 Order H
= 항목1 `outbound_scheduled` + 항목2 `shipment_confirmed`(둘 다 sq=0, 표시값 `partial`)를 추가하고
AC-022c/022d/022e의 기대 집합을 그대로 유지(H는 어느 uniform 필터에도 속하지 않고 `partial`에만 속한다).
(b)를 권장한다 — 기존 6개 기대 집합 중 `partial`만 `{G, H}`로 바뀐다.

**N2. spec.md:165 (REQ-OLIST-025 [HARD]) / spec.md:300 (AC-OLIST-023) — "쿼리 레벨 필터" 요구를
어떤 AC도 실질적으로 판별하지 못한다. prefetch를 재사용한 Python 사후 필터링이 전 스위트를 통과한다.**

AC-OLIST-023은 "필터 요청과 동수의 미필터 요청의 총 쿼리 수가 같다"만 단정한다. 그런데 `list()`에서
페이지네이션 **이후** 이미 prefetch된 `obj.line_items.all()`로 Python 필터링을 하면 **추가 쿼리가 0개**이므로
AC-023이 통과한다. AC-022~022e도 7건짜리 단일 페이지 데이터셋에서는 `results` 집합이 동일하므로 통과한다.
즉 plan.md R7(:188)이 지목한 리스크가 실제로는 무방비다. 프로덕션 결과는 **페이지네이션 파손** —
`count`가 필터 전 전체 건수로 나오고, 50건 페이지에서 조건에 맞는 몇 건만 남아 페이지마다 결과 수가 요동친다.
사용자에게 바로 보이는 결함이다.

**정정(1줄)**: AC-OLIST-022~022e의 Then에 응답의 `count` 단정을 추가하라
(예: 022b → "`response.data["count"]`가 1이다"). Python 사후 필터링 구현은 `count`가 7로 남아 즉시 실패한다.
plan.md M4의 `Exists` 설계가 이미 올바른 방향을 지시하고 있으므로 **SPEC 재작성은 불필요하고 AC 보강으로 충분**하다.

### Medium

**N3. spec.md:163 (REQ-OLIST-024a) — fail-open 범위 문언이 여전히 모호하며(= L8-new 미해소),
AC-OLIST-022f가 그 모호성을 판별하지 못한다.**
"shall ignore the filter and return the unfiltered result set" — "the filter"가 `logistics_display`만인지
전체 필터인지 문언만으로 확정되지 않는다. AC-022f는 다른 파라미터를 함께 보내지 않으므로 두 해석을 구분하지 못한다.
plan.md:69가 "이 annotation들 자체를 건너뛰고"로 해소하므로 차단은 아니다.
**정정**: "ignore **this** filter and return the result set as if the `logistics_display` parameter had not
been supplied(다른 쿼리 파라미터의 필터링은 그대로 적용된다)"로 3단어 수정.

**N4. spec.md:264 / acceptance.md:269 (AC-OLIST-021) — Given이 `shopify_created_at` non-null을 명시하지 않는데,
H3-new 수정으로 절대값 7이 날짜 유무에 조건부가 되었다.**
REQ-OLIST-022a(spec.md:155)는 이제 "+1은 페이지에 non-null `shopify_created_at` 주문이 있을 때"로 한정된다.
그런데 AC-021의 Given은 "확정 매입가·유효 환율·고객이 연결된 주문"만 요구한다 — `shopify_created_at`이 null이면
배치 쿼리가 스킵되어 총계가 6이 되고 AC가 실패한다. "유효 환율"이 날짜를 함의한다고 읽을 수는 있으나
[HARD] 절대상수를 검증하는 유일한 AC의 Given으로는 느슨하다.
**정정**: Given에 "`shopify_created_at`이 not null인" 한정을 추가하라(1구절).

**N5. spec.md:155 (REQ-OLIST-022a [HARD]) — "exactly 0 additional queries" 분기에 대응하는 AC가 없다.**
전부-NULL 페이지에서 배치 쿼리를 스킵하지 않는 구현은 이 [HARD] 요구를 위반하지만 어떤 런타임 AC도 잡지 못한다
(plan.md R11:192가 이 사실을 스스로 기록한다). Traceability 표(spec.md:338)는 `REQ-OLIST-022a | AC-OLIST-021`로
완전 커버를 표기해 **커버리지를 과장**한다 — M3-new와 같은 계열이 좁은 형태로 남았다.
프로덕션 영향은 사실상 0(Shopify 주문은 항상 생성 시각을 동반)이므로 차단은 아니다.
**정정(택1)**: (a) REQ-OLIST-022a에서 "exactly 0" 절을 "and never more than 1 in any case"로 약화해
검증 불가능한 [HARD]를 제거하거나, (b) 전부-NULL 페이지 AC를 1건 추가하라. **(a)를 권장한다** —
조건부 스킵은 최적화일 뿐 요구사항일 필요가 없다.

### Low

- **N6.** spec.md:127 — 모듈 2 재검증 문단이 "008/009/010/011/011a는 이제 **전부** 'at least one trackable line item'
  으로 명시적으로 가드"라고 쓰지만 **REQ-OLIST-009에는 그 문구가 없다**(존재 한정사로 안전할 뿐).
  결론은 참이나 근거가 부정확하다. 감사가 저자 서술을 신뢰하지 않고 재유도해야 하는 이유의 실례다.
- **N7.** spec.md:340 — Traceability 표가 `REQ-OLIST-024`의 커버 AC에 AC-OLIST-026을 넣는데
  AC-OLIST-026의 `Traces:`(spec.md:307, acceptance.md:385)는 REQ-026/027만 적는다.
  실질 커버는 성립하므로 AC 쪽 `Traces:`에 REQ-OLIST-024를 추가하면 닫힌다.
- **N8.** L1-new(AC 라벨 9건), L3-new(spec.md:266 mutation 서술), L4-new(`order_cancelled` AC 부재),
  L5-new(acceptance.md:41), L6-new(`shopify_orders.py` 인용 범위 불일치) 잔존 — 전부 연기 가능.
- **N9(정보, 결함 아님).** AC-OLIST-022f는 오늘의 무수정 코드에서 초록이다(fail-open의 성질상 불가피).
  plan.md:233의 mutation 게이트가 유일한 실효 검증 수단임을 구현자가 인지해야 한다.
- **N10(정보).** 치역 닫힘(7개 값)은 `LOGISTICS_STATUS_CHOICES` 5개 값이 DB 레벨에서 강제되지 않는다는 전제 위에 있다
  (`CharField(choices=...)`는 애플리케이션 검증). 이 SPEC이 만든 위험은 아니며 SPEC-ORDER-011 소관이다.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.85 | 0.75–1.0 | 37개 REQ 전량 재독 결과 **상호 모순 0건**(C1-new 해소를 독립 재유도로 확인, spec.md:119/121/123). v1.0.0의 3대 모호성(C1/C3/H6)과 v1.1.0의 2대 모호성(C1-new/H3-new)이 전부 제거됨. REQ-OLIST-022a(spec.md:155)는 자기 설계(plan.md:49,148)와 이제 정합. 감점: REQ-OLIST-024a 범위 모호 잔존(N3, spec.md:163), 재검증 문단의 사실 오류(N6, spec.md:127), AC-021 mutation 서술 자기모순(L3-new, spec.md:266) |
| Completeness | 0.90 | 0.75–1.0 | 전 섹션 존재: HISTORY(:15-21), 문제 정의(:25-35), 목표(:37-43), 확정된 사용자 결정(:45-60), 명시적 가정(:62-67), 범위 델타(:69-84), 관련 SPEC(:86-91), 요구사항(:95-187), 인수 기준(:191-353), 설계 결정(:357-365), 사전 검증(:367-376), 제약사항(:378-384), **Exclusions 8건 전부 구체적**(:386-395), 후속 과제(:397-403). frontmatter 6필드 완비, 3문서 버전 동기(1.2.0). 감점: REQ-OLIST-022a의 "+0" 분기 미검증(N5), REQ-OLIST-025의 실효 검증 수단 부재(N2) |
| Testability | 0.80 | 0.75–1.0 | 38개 AC 중 신규/재작성 10건을 전수 mutation 구성: **정상 구현에서 실패하는 AC 0건**, **오늘 코드에서 통과하는 AC 1건**(022f, fail-open 성질상 불가피). 손계산 3건 독립 재유도(67.75 / 86.02 vs 86.01 / 73.13 vs 67.75) 전부 판별력 확인. 표준 데이터셋이 6개 any/all mutation 중 5개를 잡는다. 감점: `outbound_scheduled` any/all 무방비(N1), REQ-025의 Python 사후 필터 mutation 무방비(N2), `order_cancelled` 무검증(L4-new), REQ-022a "+0" 무검증(N5) |
| Traceability | 0.92 | 0.75–1.0 | 기계 검증: spec.md ↔ acceptance.md의 `Traces:` **38/38 완전 일치**, 고아 AC 0건, 커버되지 않는 REQ 0건, 검증표 35행 중 34행이 `Traces:` 역맵과 일치. spec.md:353의 "37개 REQ 전량이 38개 AC로 직접 커버"는 **참**. M1-new(표의 공허한 계상) 재발 없음. 감점: REQ-024 행 ↔ AC-026 `Traces:` 불일치 1건(N7), REQ-022a의 부분 커버를 완전 커버로 표기(N5) |

---

## Chain-of-Verification Pass

1차 통과 후 재독하며 확인·발견한 것들:

1. **저자의 재유도 문단(spec.md:127)을 읽기 전에 규칙 사슬을 처음부터 다시 유도했다.** review-1의
   "008~012는 전수적·배타적 ✓"이 오판이었고 review-2가 그것을 뒤집었으므로, 이번에는 `LOGISTICS_STATUS_CHOICES`
   실물(models.py:8-14, **정확히 5개 값**)부터 열어 치역 닫힘을 유도했다. 결론은 저자와 일치하지만
   **저자의 근거 문장에 사실 오류 1건**(REQ-009의 가드 문구)을 발견했다(N6).

2. **"데이터셋이 6개 값을 포괄한다"를 곧이곧대로 믿지 않고 여섯 개 uniform 검사 각각에 any/all mutation을
   대입했다.** 1차에는 "022b/c/e에 Order G가 들어갔으니 H1-new 완전 해소"로 넘어갈 뻔했다.
   값별로 세고 나서야 **혼재 주문이 `{not_shipped, shipment_confirmed}` 하나뿐이라 `outbound_scheduled`의
   any/all만 무방비**라는 것이 드러났다(**N1 — 이번 감사 최대 수확**). "6개 값에 AC가 각각 있다"와
   "6개 값의 mutation이 각각 잡힌다"는 다른 명제다.

3. **AC-OLIST-023이 REQ-OLIST-025([HARD] 쿼리 레벨 필터)를 실제로 판별하는지 mutation을 구성했다.**
   1차에는 "쿼리 수 불변식이면 SQL 필터의 증거"라는 plan.md R7의 서술을 그대로 받아들였다.
   재독에서 **prefetch 재사용 Python 사후 필터는 추가 쿼리가 0개**라는 것을 깨달았고, 그 구현이
   AC-022~023 전량을 통과하면서 페이지네이션만 조용히 깨뜨린다는 것을 확인했다(**N2**).

4. **REQ-OLIST-022a의 "5" 분기를 저자의 실측 주장이 아니라 Django 소스로 유도했다.**
   `Order.customer`가 forward FK(models.py:82)임을 확인하고, poetry 가상환경의 Django 5.2.17
   `db/models/lookups.py:547-555`에서 `In.process_rhs`가 None을 제거한 뒤 빈 목록에 대해 `EmptyResultSet`을
   던지는 것을 직접 읽었다. **5는 단정이 아니라 유도 가능한 값이다.**

5. **AC-OLIST-020a가 정상 구현을 깨뜨리지 않는지 역방향으로 검사했다.** `override_settings(TIME_ZONE=...)`가
   `USE_TZ=True`(base.py:94)에서 DB 커넥션 타임존을 바꾸지 않으므로 `.date()` 구현은 통과하고
   `localtime().date()` 구현만 실패한다 — SPEC-ORDER-021 감사가 지적했던 "정상 구현을 깨는 AC" 유형이
   아님을 확인했다.

6. **Traceability를 눈으로 세지 않고 파서로 세었다.** spec.md 38 × acceptance.md 38의 `Traces:`를 추출해
   집합 비교했고(불일치 0건), 검증표 35행을 역맵과 대조해 **불일치 1건**(N7)만 남음을 확인했다.
   M1-new 유형(공허한 계상)의 재발 여부를 각 행의 픽스처가 실제로 그 규칙을 경유하는지로 검사했다 —
   REQ-011 행의 대체 AC(AC-008)가 실제로 규칙 4를 경유함을 손으로 확인했다.

7. **Exclusions 8건을 개별 재확인했다**(spec.md:386-395). 전부 구체적 산출물 또는 사용자 결정을 지목하며
   포함된 요구사항과 충돌하지 않는다. `LOGISTICS_STATUS_CHOICES` 확장 금지 항목이 REQ-OLIST-024의 6개 값
   (그중 `partial_shipped`/`partial`은 파생 전용)과 정합함을 확인 ✓.

8. **비목표 재유입을 `grep`으로 재점검했다.** 마진 정렬/필터, 발주상태 필터, 부분출고 사유, OrderDetail 변경
   4종 모두 Exclusion/후속 과제 방향으로만 등장하며 REQ·AC·plan 어디에도 재유입 없음 ✓.

9. **review-2의 판정 1건을 뒤집었다**(L2-new — 아래 참조). 선행 감사의 Low 판정도 무비판 승계하지 않았다.

10. **결함으로 올리지 않은 잔여 사항 2건**: (a) 표준 데이터셋의 Order C/D/F/G는 `quantity`를 명시하지 않지만
    규칙 1~4a 중 어느 것도 `quantity`를 읽지 않으므로 판별력에 영향 없음. (b) Order D의 라인아이템 개수가
    명시되지 않았으나 1개든 2개든 규칙 4로 동일하게 판정된다.

---

## Regression Check (Iteration 2 → 3)

| review-2 결함 | 상태 | 근거 |
|---|---|---|
| **C1-new** REQ-010/011 빈 집합 가드 누락 | **RESOLVED** | spec.md:119/121/123 가드 3건 추가, 결정 5(:51) 정합화, 독립 재유도로 전수성·배타성 확인 |
| **H1-new** 022b/c/e 데이터셋 비특정 | **RESOLVED**(잔여 1건 → N1) | 표준 데이터셋 신설, spec ↔ acceptance `diff` 동일, 6개 mutation 중 5개 판별 확인 |
| **H2-new** 규칙 4 `outbound_scheduled` 표시값 미검증 | **RESOLVED** | AC-022d 이중 단정 + 022~022e 전량 전파 확인 |
| **H3-new** REQ-022a 등식 ⊥ 조건부 스킵 | **RESOLVED**(잔여 → N5) | "at most 1 / 6 또는 5 베이스라인"으로 일반화, plan.md:49,148 및 AC-021과 정합 |
| **M1-new** 표 ↔ Traces 불일치 | **RESOLVED** | AC-011 삭제 + 대체 AC의 실제 경유 확인, 기계 대조로 재발 0건 |
| **M2-new** REQ-024a 게이트 부재 | **RESOLVED** | AC-022f 신설, 4곳(spec 표 / acceptance DoD / plan M1·M4·Done) 실재 확인 |
| **M3-new** 프론트엔드 라벨 1~2/6 | **RESOLVED** | AC-026 7옵션 + AC-027 6라벨 파라미터화, `logisticsStatusLabels.ts:11-17` 5키 실물 확인 |
| **M4-new** 022a "그 외 5개 상태" 오류 | **RESOLVED** | 표준 데이터셋 참조로 대체 |
| **M5-new / round-1 L7** `.date()` 시간대 | **RESOLVED** | REQ-020 확장 + AC-020a, `base.py:92` 확인, 손계산으로 67.75 vs 73.13 판별력 확인 |
| L7-new (DoD 표 REQ-013 누락) | **RESOLVED** | acceptance.md:418 정정됨(저자가 "Low 미착수"라 적었으나 실제로는 수정됨) |
| L1/L3/L4/L5/L6/L8-new | **UNRESOLVED(의도적 연기)** | 전부 연기 가능으로 재판정(위 표) |
| L2-new | **판정 뒤집기 — 결함 아님** | 아래 참조 |

**판정 뒤집기(review-2가 틀린 항목):**

- **L2-new** — review-2는 "REQ-OLIST-011의 괄호 논거(008/010이 uniform-shipped/uniform-received를 소진)가
  부정확하며 실제로는 009가 소진한다"고 적었다. **이는 오판이다.** REQ-011은 `¬010`으로 가드되고,
  `|T|≥1 ∧ ¬008 ∧ ¬009 ∧ ¬010`은 정의상 `¬(∀t: ls=received)`를 함의하므로 "010이 uniform-received를 소진한다"는
  서술은 참이다. 009는 그 부분집합(`∃ sq>0`)을 먼저 소진할 뿐이며 두 진술은 배타적이지 않다.
  **저자가 이 항목을 고치지 않은 것이 옳다.**

**정체(stagnation) 판정: 없음.** 3회 반복 내내 변화 없이 남은 결함은 0건이다.
review-1이 지적한 20건 중 19건 해소(1건은 L7 → review-2 M5-new로 승계되어 v1.2.0에서 해소),
review-2가 지적한 신규 9건(C1-new, H1~H3-new, M1~M5-new) 중 **9건 전부 해소**,
Low 8건 중 1건 해소·1건 오판 철회·6건 의도적 연기. **manager-spec은 매 라운드 실질적으로 진전했다.**

---

## Recommendation

**PASS — 이 SPEC은 구현자에게 넘겨도 안전하다.**

판정 근거(각 must-pass에 대한 증거):

- **MP-1**: 37 REQ / 38 AC, 기계 추출로 결번·중복 0건, spec.md ↔ acceptance.md AC 집합 `diff` 완전 일치.
- **MP-2**: 38개 AC 전량이 굵은 EARS 연결어 + `**shall**` 포함 문장(파서로 전수 확인). 37 REQ 동일.
- **MP-3**: spec.md:1-11의 6개 필수 필드 전부 존재·타입 정확, 3문서 `version: 1.2.0` 동기.
- **MP-4**: 단일 프로젝트(Django + React) 범위, 다국어 툴링 주장 없음 → N/A.

세 라운드에 걸쳐 이 SPEC이 실제로 도달한 상태:
**요구사항 간 모순 0건**(독립 재유도로 확인), **정상 구현을 깨뜨리는 AC 0건**,
**오늘 코드에서 통과하는 AC 1건**(fail-open 회귀 AC로 성질상 불가피, plan.md:233에 mutation 게이트 존재),
**날조 `file:line` 인용 0건(3회 연속, 이번 라운드 16건 신규 재검증 포함)**,
**Traceability 100% 양방향**(기계 검증), **비목표 재유입 0건**.
손계산 3건(67.75 / 86.02 vs 86.01 / 73.13 vs 67.75)이 전부 독립적으로 재현되며,
절대 쿼리 상수 7과 베이스라인 5/6 분기가 추측이 아니라 Django 소스에서 유도 가능하다.

### 착수 전 필수 (차단)

**없음.** 잔존 결함 중 어느 것도 (a) 요구사항 자기모순, (b) 정상 구현을 깨는 AC, (c) 구현자를 잘못된
설계로 유도하는 서술에 해당하지 않는다. N1/N2/N3이 지목하는 세 mutation은 모두 **plan.md가 이미 올바른
구현을 명시적으로 지시**하고 있으므로(M4의 `all_X = has_trackable & ~Exists(exclude(X))` 정의,
"쿼리 레벨 `Exists` annotation", ":69 이 annotation들 자체를 건너뛰고") SPEC을 문자 그대로 따르는 구현자는
정답에 도달한다. 남은 것은 **테스트의 판별력**이며, 이는 RED 단계에서 닫는 것이 자연스럽다.

### RED(M1) 작성 시 반드시 반영 — 구현 중 처리 가능, 총 5줄

1. **N2 (권장도 최상, 1줄)** — AC-OLIST-022~022e의 Then에 응답 `count` 단정을 추가하라
   (예: 022b → "`count`가 1이다"). Python 사후 필터링 구현은 `count=7`로 남아 즉시 실패한다.
   REQ-OLIST-025([HARD])에 실효 검증 수단이 생긴다.
2. **N1 (1행)** — 표준 데이터셋에 Order H = 항목1 `outbound_scheduled` + 항목2 `shipment_confirmed`
   (둘 다 `shipped_quantity=0`, 표시값 `partial`)를 추가하고 AC-022e의 기대 집합을 `{G, H}`로 갱신하라.
   `all_outbound_scheduled → any` mutation이 AC-022d에서 판별된다.
3. **N4 (1구절)** — AC-OLIST-021의 Given에 "`shopify_created_at`이 not null인" 한정을 추가하라
   (REQ-OLIST-022a의 조건부 +1과 정합).

### 문서 정리 — sync 단계로 연기 가능

4. **N3 / L8-new** — REQ-OLIST-024a를 "ignore **this** filter …(다른 쿼리 파라미터는 그대로 적용)"로 한정.
5. **N5** — REQ-OLIST-022a의 "exactly 0" 절을 "never more than 1 in any case"로 약화(검증 불가능한 [HARD] 제거).
6. **N6** — spec.md:127의 "008/009/010/011/011a는 전부 명시적으로 가드"를 "009는 존재 한정사로 안전하다"로 정정.
7. **N7** — AC-OLIST-026의 `Traces:`에 REQ-OLIST-024를 추가.
8. **N8 (L1/L3/L4/L5/L6-new)** — AC 라벨 9건 교정(번호 유지), spec.md:266 mutation 서술 정리,
   `order_cancelled` 픽스처 1건 추가(명시적 가정 4의 사용자 확인 필요 사항은 후속 과제 4로 유지),
   acceptance.md:41 판별력 서술 정리, `shopify_orders.py` 인용 범위 통일.

### 구현자에게 전달할 주의 3건

- **AC-OLIST-022f는 RED에서 초록이다**(fail-open의 성질). 유일한 실효 검증은 plan.md:233의
  "화이트리스트 누락 mutation에서 실패" 확인이므로 건너뛰지 말 것.
- **plan.md M0의 베이스라인 재실측은 형식이 아니다** — 6(고객 있음)/5(전원 null) 분기와 절대값 7은
  이 감사에서 소스로 유도했으나 실행 측정은 하지 않았다(원격 공유 DB 제약). 불일치 시 plan.md:29의
  지시대로 spec.md를 실측값으로 갱신하고 HISTORY에 기록할 것(추측값으로 되돌리지 말 것).
- **명시적 가정 4**(trackable 전부 `order_cancelled` → "발주완료")는 **미해결 제품 결정**이다.
  구현은 문서대로 진행하되, sync 단계에서 사용자 확인을 받을 것(후속 과제 4).

Verdict: **PASS** (iteration 3/3)
