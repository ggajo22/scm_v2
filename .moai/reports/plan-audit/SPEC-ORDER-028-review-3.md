# SPEC Review Report: SPEC-ORDER-028

Iteration: 3/3 (final)
Verdict: **PASS**
Overall Score: **0.80** (iteration 1: 0.55 → iteration 2: 0.68 → iteration 3: 0.80)

> **M1 Context Isolation**: 프롬프트가 전달한 저자 측 변경 요약(N1~N13 대응 내역)은 **탐색 순서를 정하는 데만** 썼고, 종결 판정의 근거로는 채택하지 않았다. 모든 판정은 `.moai/specs/SPEC-ORDER-028/{spec,plan,acceptance}.md`의 실제 텍스트와 이 세션에서 직접 연 저장소 소스만을 근거로 한다. HISTORY 산문(`spec.md:21`)은 근거로 채택하지 않았다 — 이번 회차에는 그 판단이 실제로 결정적이었다(D3 참조: HISTORY가 §8 C11과 모순되는 수치를 적고 있다). 프롬프트가 제공한 DB 기능 플래그 4건과 `shopify_orders.py:88-89`/`:287-289`/`migration 0026:55-64`는 재도출하지 않고 기준값으로 사용했다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ 번호 일관성** — 활성 REQ **32개**(001–027, 029–031, 033–034), 결번 2개(028, 032). 중복 0, 3자리 zero-padding 일관. 두 결번 모두 3곳 이상에 명시: 028 → `spec.md:98`(§5 도입부) / `:258`(추적표) / `:297`(§8 C6). 032 → `spec.md:98` / `:262`(추적표) / `:302`(§8 C11) + `acceptance.md:66`. 삭제된 REQ-RSW-032 본문을 참조하는 **댕글링 인용 0건**(세 문서 전수 확인) — 남은 5건은 전부 "결번이다/삭제되었다"는 이력 서술이다.
- **[PASS] MP-2 EARS 형식 준수** — 활성 32개 REQ 전건을 개별 확인했다. `shall`/`shall not` 부재 REQ **0건**. 패턴 라벨과 문장 구조 정합: Ubiquitous(001–007, 013–028 계열), Optional(008 `WHERE --count`, 009 `WHERE --store`), Unwanted(010, 029, 030), Event-Driven(011 `When … shall`), Complex(012 `While … when … shall` — EARS 표준의 복합형). **iteration 2의 FAIL 원인이던 REQ-RSW-032(비규범 범위 면책 선언)는 완전히 삭제**되었고(`spec.md:98`), 그 자리를 대체하는 비규범 문장이 §5 안에 새로 들어오지 않았음을 전수 확인했다 — D12 → N6로 이어진 **stagnation 사슬이 이번 회차에서 끊겼다**. 부수 지적이던 REQ-RSW-033의 `[HARD]` 누락도 보완됨(`spec.md:214`).
- **[PASS] MP-3 YAML frontmatter 유효성** — `spec.md:1-11`: `id: SPEC-ORDER-028`, `version: 0.3.0`(점 2개 → string), `status: draft`, `created_at: 2026-08-19`(ISO date), `priority: High`, `labels: [order, shopify, sync, resync, performance, backend]`(array). 전 필드 존재·타입 정합.
- **[N/A] MP-4 언어 중립성** — 단일 언어(Python/Django) 프로젝트 SPEC. 자동 통과.

**must-pass 4항목 전부 통과 → firewall 미발동.**

---

## Category Scores (rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.85 | 0.75–1.0 | iteration 2의 최대 결함(§1 명분 ↔ Exclusions #12 자기모순)이 해소됨 — `spec.md:31`이 "번들 매핑 전파(최초 전개·사후 변경 구분 없이)는 이 SPEC의 명분에서 완전히 제외한다"로 단정하고, REQ-RSW-031(`:210`)·Exclusions #12(`:283`)·§8 C9(`:300`)가 전부 같은 범위로 확장되어 세 지점이 서로를 부정하지 않는다. 채택하지 않은 대안(migration 0026 방식)과 그 이유도 D6(`:92`)에 기록. 감점: **HISTORY(`:21`)의 정정 수치가 §8 C11(`:302`)과 정반대**(D3) |
| Completeness | 0.80 | 0.75–1.0 | 전 섹션 존재(HISTORY/문제정의/Environment/Assumptions 9건/설계결정 6건/REQ/추적표/Exclusions 13건/알려진제약 12건). Exclusions는 전부 구체적("~하지 않는다" + 근거 + 대안 비용). 감점: **종료/취소 감지의 소비자 부재**(D1)가 §8 어디에도 없다 — 이 SPEC에 남은 3개 명분 중 하나의 실효성이 문서화되지 않은 채 남는다 |
| Testability | 0.72 | 0.50–0.75 | AC 33개 + 변이 25개 + 단독 판별자 17개 + §0.1의 강화된 "성공 증거" [HARD] 규약(15개 AC에 실제 적용, 전수 대조 확인). AC-018의 판별력 문단 재작성은 실효적이다(`IntegrityError` → 실패 집계 → `CommandError`, MySQL strict/non-strict 양쪽에서 성립). 감점: **AC-018 픽스처가 모델 기본값과 동일해 되돌림 변이에 퇴화**(D2), **AC-030이 부분-빈값 경로를 판별하지 못함**(D4), 모킹 대상 네임스페이스 미지정(D6) |
| Traceability | 0.90 | 0.75–1.0 | `spec.md:229-264` 추적표 34행 전건을 `acceptance.md`의 실제 `Traces:` 선언과 **양방향** 대조 — 불일치 **0건**(iteration 2의 N7 3건 전부 종결). AC 없는 REQ 7건(001/002/009/017/020/027/031)은 전부 "(AC 없음 — DoD 검증)"으로 명시되어 `spec.md:266`의 [HARD] 규칙을 준수. 감점: 결번 안내(`acceptance.md:59`, `:670`)의 개수 표기 오류 3건(D5) |

---

## Part 1 — iteration 2 지적사항 개별 종결 판정

| # | 판정 | 근거(실제 변경 텍스트) |
|---|------|------------------------|
| **N1** (번들 명분 ↔ 배제 모순) | **CLOSED** | ① 명분 삭제 확인: `spec.md:31`이 헤드라인을 "**도서 제목 전파만이 이 SPEC의 명분이다**"로 바꾸고 번들 관련 이득 주장을 제거. ② 배제 확장 확인: REQ-RSW-031(`:210`) "최초 전개든 사후 변경이든 무관하게", Exclusions #12(`:283`) "최초 전개·사후 변경 구분 없이", §8 C9(`:300`) "최초 전개와 사후 변경을 구분하지 않고 둘 다 적용된다", 가정 A9 신설(`:79`), plan.md R14(`:732`) 갱신 — **5개 지점이 동일 범위로 정렬**. ③ 잔여 이득 주장 전수 검색: 세 문서에서 번들 전파에 의존하는 이득 문장 **0건**. ④ 위치: 잔여 위험이 HISTORY가 아니라 §1 본문 마지막 문장(`:31`) + Exclusions #12 + §8 C9에 있어 **독자가 실제로 마주치는 자리**에 있다. ⑤ 채택하지 않은 대안(b)의 비용도 D6(`:92`)에 기록 |
| **N1 — 결과 서술의 정확성 검증** | **정확(경미한 프레이밍 과장 있음)** | §8 C9의 "수량 집계 규약에 오염 위험"을 **집계 지점을 직접 열어** 검증했다. 고아 `sku=bundle_sku` 행은 `sku__isnull=False`이므로 (a) `UnorderedItemsView`(`purchase_order_views.py:344-368`, `_reorder_candidate_filter` `:94-111`)에서 **팬텀 재주문 후보 1행**으로 노출되고, (b) `:2891-2894`의 `order_total_quantity = Sum("quantity")`를 전량만큼 부풀리며, (c) `_recompute_order_aggregates`(`:180-191`)의 trackable 집합에 들어가 `Order.status`가 영구 "partial", `ready_to_ship`이 영구 False가 된다. 환불 넷팅(`:170-178`)은 `line_item_id=OuterRef("shopify_line_item_id")`로 매칭하므로 고아 행도 멤버 행과 **동일한 환불량을 차감받아** 배제되지 않는다. → **"오염 위험"은 사실이며 오히려 과소 표현**이다(위험이 아니라 해당 주문에서는 확정적). 반면 "약 8회·일"은 **경로 진입 빈도**이지 손상 발생 빈도가 아니다 — 고아 생성은 "번들 매핑이 새로 추가된 순간 그 주문 1회"의 전이 이벤트이고 이후 스위프는 멱등이다(`update_or_create(sku=member_isbn)`가 기존 멤버 행에 매치). 즉 실제 프로필은 "주문당 1회, 영구 잔존"이며 "8회·일 반복 손상"이 아니다. 결함은 아니나 문구가 오해를 부른다 → **D7(MINOR)** |
| **N2** (정상-빈값 위치 소거) | **PARTIAL** | REQ-RSW-030이 (a) 예외 / (b) 정상-빈값 두 하위 절로 분리됨(`spec.md:202-205`), 가정 A7 재작성(`:77`), Exclusions #13 단서 추가(`:284`), plan.md §1.3 (B')에 **주문 단위 + 라인아이템 단위 양쪽 폴백**이 실제로 구현됨(`plan.md:314-329`) — 프롬프트가 우려한 "주문 레벨만 처리했는가"는 **기우였다**: `line_item_map`이 `set(existing) | set(fresh)` 합집합 위에서 키별로 `fresh.get(id,"") or existing.get(id,"")`를 계산하므로 부분 케이스가 코드상 커버된다. 위험 R16 신설(`plan.md:734`), M4 마일스톤 갱신(`:642-651`), 수동 검증 절차 추가(`:791-793`). **그러나 AC가 그 부분 케이스를 판별하지 못한다 → D4** |
| **N3** (header-only 환불 자가치유) | **CLOSED** | REQ-RSW-029에 자가치유 절 추가(`spec.md:197`), D3 설계결정 갱신(`:89`), plan.md §1.6 (B')에 실제 코드(`:556-568`) — `order_by("pk")` 후 `[1:]` 삭제이므로 **생존자는 결정적(최소 pk)**이다. **데이터 유실 검증**: 삭제되는 중복 행이 들고 있는 값 중 소비되는 것이 있는지 확인하려고 `Refund`의 전 소비 지점을 열었다 — `purchase_order_views.py:171/335/444/549/742/1335/1450/3420/3716/4166/4192/4617/4669`, `views.py:195`는 전부 `line_item_id=OuterRef("shopify_line_item_id")`로 매칭하므로 `line_item_id IS NULL` 행은 **어느 합계에도 들어가지 않는다**. `serializers.py:180`은 `if refund.line_item_id is not None:`로 명시 배제. `Refund`를 가리키는 FK도 없다(cascade 없음). → **중복 정리는 금액·수량 집계에 대해 무해**하다. AC-RSW-029b(`acceptance.md:542-555`)가 Given 2건 → Then `count()==1` + 실패 목록 부재를 단정 |
| **N4/N4b** (성공 증거) | **CLOSED** | §0.1 [HARD] 규약이 "실패 0건(`CommandError` 미발생)" 또는 "실제 반영된 변경값"으로 강화됨(`acceptance.md:52`) + §0 서두 재서술(`:13`) + D1에 [HARD 주의] 삽입(`spec.md:87`) + REQ-RSW-011 본문에 명시(`:137`). **실제 준수 전수 대조**: 013(`:284`), 014(`:299`), 017(`:380`), 018(`:395`), 019(`:410`), 020(`:425`), 021(`:442`), 022(`:457`), 023(`:472`), 024(`:487`), 026(`:521`), 029(`:536`), 029b(`:553`), 030(`:331`), 034(`:585`) — **15개 전부 포함**. 예외 선언 4건(009 `:220`, 010 `:237`, 014b `:312`, 025 `:504`, 033 `:572`)은 각각 고유 증거를 대신 제시. AC-018 판별력 문단 전면 재작성(`:397`)의 논리도 검증: `_sync_single_order`가 `with transaction.atomic()` 안에 있고 `except Exception`이 밖에 있으므로(`plan.md:331-343`) `IntegrityError` → savepoint 롤백 → `failed` 적재 → `CommandError` 성립. non-strict sql_mode에서도 `""`가 써져 "무변경" 단정이 깨지므로 양쪽에서 판별된다 |
| **N5** (AC-006 정렬 제거 변이) | **CLOSED** | `acceptance.md:156`이 생성 순서를 **E→F→G**로 뒤집고 기대 순서 G→F→E와 정반대임을 명시, 판별력 문단(`:162`)이 "삽입 순서 그대로 반환이 발생해도 {E,F} ≠ {G,F}로 잡힌다"를 설명, plan.md R2(`:720`) 갱신, DoD 보호 항목 추가(`acceptance.md:675`) |
| **N6/MP-2** (REQ-032 비규범) | **CLOSED** | REQ-RSW-032 **완전 삭제**, 결번 3-place 명시. "15→13"은 §8 C11(`:302`)에 **비규범 참고치**로 이동하고 `_build_title_map` 조기 반환(`shopify_orders.py:62-63`)을 반영해 재산정. 추적표의 "(대표 — 쿼리 수 감소분 검증)" 표기도 제거됨(`:262`는 결번 행) |
| **N7** (문서 간 추적 불일치) | **CLOSED** | 32개 활성 REQ 전건 양방향 대조 결과 불일치 0건. 구체적으로: AC-RSW-001(`:76`)에서 REQ-RSW-007 제거됨 ✓, AC-RSW-029(`:529`)에 REQ-RSW-025/026 추가됨 ✓, AC-RSW-007(`:170`)/AC-RSW-011(`:245`)/AC-RSW-012(`:260`)/AC-RSW-024(`:480`)/AC-RSW-025(`:495`) 전부 spec.md와 정합 |
| **N8** (REQ-034 근거 오류) | **CLOSED** | `spec.md:218`이 "이 보존의 실제 근거는 REQ-RSW-018/019가 **아니다** … 진짜 근거는 이 필드들이 `common_defaults`(`shopify_orders.py:231-243`)에 애초에 포함되어 있지 않다는 사실"로 정정. 소스 대조 결과 `common_defaults`(`:231-243`)에 해당 10개 필드 전부 부재 확인 |
| **N9** (AC 결번 무설명) | **CLOSED(신규 계수 오류 발생)** | §0.2 신설(`acceptance.md:57-68`)로 결번 4개(027/028/031/032)와 사유, "030은 결번이 아니다"라는 오해 방지 문구까지 명시. `acceptance.md:3`·`plan.md:703`도 "범위 내 33개"로 정정. **그러나 열거 자체에 오류 3건 → D5** |
| **N10** (기본값 40 미검증) | **CLOSED** | AC-RSW-007b 신설(`acceptance.md:183-194`), 변이 M25 등록(`:43`), 단독 판별자 보호 목록 편입(`:45`), 추적표 REQ-RSW-006 → `AC-007, AC-007b`(`spec.md:236`) |
| **N11** (REQ-033 `[HARD]` 누락) | **CLOSED** | `spec.md:214` `**REQ-RSW-033** (Ubiquitous) [HARD]` |
| **N12** (요구사항 층의 구현 기법) | **수용(미조치) — 타당** | §8 C12(`:303`)에 "의도적으로 조치하지 않는다"와 그 이유를 명시. **감사도 동의한다**: REQ-RSW-024/025/029가 인용하는 `models.py:320`/`:342` 유니크 제약은 이 세션에서 직접 확인해 전부 정확하고, 이 시점의 전면 재작성은 N7 부류의 신규 불일치를 만들 위험이 이득보다 크다. 정직하게 선언된 잔여 항목으로 **수용** |
| **N13** | 조치 불요(기록용) | — |

**요약: CLOSED 11 / PARTIAL 1(N2) / 수용 1(N12).** iteration 2의 CRITICAL 2건 중 N1은 완전 종결, N2는 설계는 종결·검증만 부분 종결. MAJOR 4건 전건 종결. **NOT CLOSED 0건. Stagnation 0건.**

---

## Part 2 — 신규 3개 메커니즘 정밀 감사(미감사 신규 작업으로 취급)

### (A) REQ-RSW-030(b) 위치 값-병합 — `plan.md:314-329`

검증 결과:

| 시나리오 | 병합 결과 | 판정 |
|---|---|---|
| 주문 코드 빈값 + 전 라인아이템 빈값 | `order.location` 유지 + 각 행 기존값 유지 | 정상, **AC-030이 판별** |
| 주문 코드 빈값 + 라인아이템 맵 자체가 `{}` | `all_line_item_ids`가 기존 행 키집합 → 각 행 기존값 유지 | 정상, AC-030이 판별(`_sync_single_order:242`의 `if line_item_location_map else ""` 우회 확인) |
| **주문 코드 있음("NJ") + 일부 라인아이템만 빈값** | 키별 폴백으로 그 행만 기존값 유지 | **코드는 정상. AC 없음 → D4** |
| 주문 코드 빈값 + 라인아이템 일부 값 있음 | 발생 불가 — `seen`은 truthy 코드만 모으므로 라인 코드가 하나라도 non-empty면 주문 코드도 non-empty(`shopify_orders.py:91-97`) | 논리적으로 닫힘 |
| Shopify가 처음 보고하는 신규 라인아이템 | 기존값 없음 → `""` (첫 동기화와 동일) | plan.md:311-313이 명시, 회귀 아님 |
| Shopify가 더 이상 보고하지 않는 라인아이템 | 맵에는 들어가나 `_sync_single_order`가 조회하지 않음 | 무해 |

키 타입 정합도 확인: `li["id"]`(Shopify JSON int) ↔ `LineItem.shopify_line_item_id`(BigIntegerField) ↔ `fresh_line_item_map` 키(Shopify int) — 3자 일치. 쿼리 예산 +1/주문도 `plan.md:365` (F)에 정직하게 기록됨.

**잔여 결함 2건: D4(부분 케이스 미판별), D7b(번들 확장 주문에서 `dict(values_list(...))`가 동일 `shopify_line_item_id`의 N행을 조용히 1건으로 축약, 생존자 비결정적).**

### (B) REQ-RSW-029 중복 정리 — `plan.md:556-568`

- **결정적 생존자**: `order_by("pk")` 후 `[1:]` 삭제 → 최소 pk 생존. ✓ (`spec.md:197`은 "1건만 남기고"로만 규정 — HOW를 plan에 위임한 것이라 적절)
- **데이터 유실 가능성**: 없음. 삭제되는 행의 컬럼 중 `id`/`created_at`(auto_now_add) 외 전부 직후 upsert의 `defaults`로 덮어써진다. 그리고 위 Part 1 N3행에서 확인한 대로 `line_item_id IS NULL` 행은 **저장소의 어떤 환불 합계·표시 로직에도 들어가지 않는다**(14개 소비 지점 전수 확인 + `serializers.py:180`의 명시 배제 + FK 부재). → **금액/수량 왜곡 없음.**
- **경합 재발**: 정리와 upsert 사이에 `sync_store()`가 끼어들면 다시 중복이 생길 수 있으나, 다음 사이클이 다시 자가치유하므로 영구 고착은 해소된다 — 이것이 정확히 옛 `.all().delete()`가 제공하던 속성이다. ✓
- `ShippingLine` 쪽에는 같은 정리가 없는데, `shopify_shipping_line_id`가 non-nullable(`models.py:312`)이라 유니크 제약이 실효하므로 **선존 중복이 물리적으로 불가능**하다. 비대칭이 정당함을 확인. ✓

**결함 없음.**

### (C) §0.1 성공 증거 규약의 전면 적용 여부

`resync_order_sweep`를 실행하는 AC 20개를 전수 분류:

- **규약 준수 15건**: 013/014/017/018/019/020/021/022/023/024/026/029/029b/030/034 — 전부 `CommandError` 부재 또는 실제 반영값(또는 둘 다).
- **명시적 예외 선언 4건**: 009(`:220`), 010(`:237`, 대체 증거 "실패 목록이 정확히 {K}"), 014b(`:312`), 011(실패를 기대하는 양성 케이스).
- **규약 범위 밖 4건**: 006/007/007b — 각각 처리 순서·호출 횟수를 단정하므로 "데이터 보존/반영 주장"이 아니다.
- **회색지대 1건**: **AC-RSW-008**(`:198-209`)의 Then은 `last_resynced_at`이 NULL이 아님 **하나뿐**이다 — §0.1이 경고한 바로 그 형태다. 규약 문구("데이터 보존/반영을 주장하는 모든 AC")의 문리상 범위 밖이고, 선언 변이 M6("성공 케이스에서만 갱신 누락")은 여전히 판별되므로 커버리지 구멍은 아니다. 그러나 DoD 재확인 목록(`:674`)에도 008이 빠져 있어 규약과 실제의 경계가 흐리다 → **D8(MINOR)**.

**판정: 실질적으로 일관 적용됨. 회색지대 1건은 커버리지 손실 없음.**

---

## Part 3 — 신규 결함(제3의 "인용하지 않은 인접 코드" 탐색 결과)

프롬프트의 요청대로 세 번째 사례를 겨냥해 탐색했다. **찾았다 — D1이다.**

### MAJOR

**D1. 종료/취소 감지(문제 정의 2번)가 채우는 `closed_at`/`cancelled_at`을 백엔드에서 읽는 코드가 하나도 없다 — 이 SPEC에 남은 3개 명분 중 하나의 실효성이 미검증이다.**

`backend/` 전체(테스트 제외)에서 두 필드의 출현 지점은 **정확히 4곳**이며 전부 쓰기 또는 선언이다:
- `shopify_orders.py:161-162` — `_sync_single_order`의 defaults 쓰기(이 SPEC이 활용하려는 지점)
- `models.py:79-80` — 필드 선언
- `migrations/0001_initial.py:57-58` — 최초 마이그레이션
- `serializers.py:436` — `OrderDetailSerializer`의 `fields` 목록(직렬화만)

**읽는 코드는 0건이다.** 특히 이 SPEC의 이웃 경로들을 직접 열어 확인했다:
- `_reorder_candidate_filter`(`purchase_order_views.py:94-111`) — 취소/종료 조건 **없음**. 취소된 주문의 `purchase_status="unordered"` 라인아이템은 여전히 재주문 후보로 노출된다.
- `_apply_logistics_display_filter`(`views.py:188-229`) — 두 필드 미참조.
- `_recompute_order_aggregates`(`purchase_order_views.py:124-206`) — 미참조(취소 신호는 `Refund` 행으로만 들어온다고 `serializers.py:177`이 명시).
- 이 SPEC 자신의 대상 판정 쿼리 `_qualifying_orders_queryset`(`plan.md:92-119`) — `cancelled_at`/`closed_at`을 **배제하지 않는다**.

프런트엔드도 `frontend/src/types/order.ts:224-225`의 타입 선언과 두 테스트 픽스처가 전부다 — **렌더링하는 컴포넌트가 없다.**

귀결:
1. `spec.md:30`은 프로덕션 실측(3,883건 중 `closed_at` 12 / `cancelled_at` 6)을 근거로 이를 "구조적으로 닫을 수 없는 결함"으로 제시한다. 독자는 스위프 도입 후 취소 주문이 라이브 취급에서 빠질 것으로 읽는다. **빠지지 않는다** — 아무도 그 필드를 보지 않는다.
2. 대상 판정이 두 필드를 배제하지 않으므로, 취소된 주문에 `not_shipped` 라인아이템이 하나라도 남아 있으면 그 주문은 60일 내내 라운드로빈 슬롯을 점유하며 매 랩 동일 값을 재기록한다. 최초 감지 이후의 반복 처리는 순비용이다(현 실측 규모로는 무시 가능하나, 문서화되지 않은 설계 귀결이다).

이것은 iteration 2의 N1과 **정확히 같은 결함 부류**다(코드가 뒷받침하지 않는 명분). 다만 N1은 명분이 **적극적 손상**을 유발했던 반면 여기서는 **효용이 0에 가까울 뿐 손상은 없다** — 데이터 자체는 정확해지고 상세 API로 노출되므로, 후속 SPEC이 소비할 수 있는 기반이 만들어지는 것은 사실이다. 그래서 CRITICAL이 아니라 MAJOR다.

**종결 조건**: §8에 항목 하나를 추가하라 — "`closed_at`/`cancelled_at`은 현재 어떤 조회·집계·필터도 읽지 않으며(`_reorder_candidate_filter`·`_apply_logistics_display_filter`·`_recompute_order_aggregates` 전부 미참조), 이 SPEC은 데이터 정확성만 확보하고 그 값을 소비하는 로직은 후속 과제로 남긴다. 대상 판정도 취소/종료 주문을 배제하지 않으므로 그 주문들은 60일 창이 닫힐 때까지 슬롯을 계속 점유한다." AC 추가는 불필요하다(AC-015/016이 데이터 반영 자체는 이미 검증한다).

**D2. AC-RSW-018의 픽스처 값이 모델 기본값과 동일해, 가장 개연성 높은 되돌림 변이에 대해 퇴화한다.**

`acceptance.md:391`의 Given은 `_make_qualifying_order(logistics_status="not_shipped")`이다. 그런데 `LineItem.logistics_status`의 모델 기본값이 정확히 `"not_shipped"`다(`models.py:204-208`, `default="not_shipped"`). 따라서:
- 스위프가 이 필드를 **기본값으로 리셋**하는 변이(예: 조회 키 오류로 기존 행 대신 새 행을 만드는 변이, 또는 `common_defaults`에 `li.get("logistics_status", "not_shipped")` 형태로 넣는 변이)는 결과값이 `"not_shipped"`로 동일해 **"무변경" 단정을 통과**한다. `title`도 갱신되고 `CommandError`도 나지 않으므로 v0.3.0이 추가한 성공 증거 2종도 이 변이를 잡지 못한다.
- 잡히는 것은 `None`/`""`이 써지는 변이뿐이다(재작성된 판별력 문단이 다루는 케이스).

REQ-RSW-003이 대상 조건으로 `not_shipped`를 강제하므로 **단일 라인아이템 픽스처로는 이 퇴화를 피할 수 없다**. 대조군: AC-RSW-017은 `purchase_status="cs_required"`(기본값 `unordered`와 다름)이라 퇴화하지 않는다(`models.py:190-194`). 변이 M13은 017+018 공동 커버로 선언되어 있으므로 `purchase_status` 쪽은 살아 있으나, `logistics_status` 전용 리셋 변이는 **SPEC 전체에서 미커버**다.

**종결 조건**: AC-RSW-018의 Given을 라인아이템 2건으로 바꿔라 — 1건은 대상 자격용 `logistics_status="not_shipped"`, 다른 1건은 보호 대상으로 `logistics_status="received"`(기본값과 다름). Then은 후자가 `"received"`로 유지되는지 단정한다. 한 줄 변경으로 퇴화가 해소된다.

**D4. AC-RSW-030이 위치 병합의 "부분" 케이스를 판별하지 못한다 — 실제 프로덕션에서 가장 자주 발생하는 형태가 그쪽이다.**

`acceptance.md:327`의 Given은 `_build_fulfillment_location_data`가 **`("", {})`(전면 빈값)**를 반환하도록 모킹한다. 이 모킹은 다음 두 구현을 구분하지 못한다:
- (정답) 키 단위 폴백: `fresh.get(id,"") or existing.get(id,"")`
- (변이) 전부-아니면-전무 폴백: `line_item_map = fresh_map if fresh_map else existing_map`

두 구현 모두 `("", {})` 입력에서 동일하게 `"NJ"`를 보존한다. 그러나 실제 Shopify 응답에서는 **부분 케이스가 자연스럽게 발생**한다 — `assigned_location.name`이 `GIMSSINE_NJ`인 fulfillment order와 `GIMSSINE`(언더스코어 없음)인 것이 한 주문에 섞이면 `seen=["NJ"]`이므로 `loc="NJ"`이고 `line_map={1001:"NJ", 1002:""}`가 된다(`shopify_orders.py:86-97`의 로직으로 직접 도출; `test_order_location.py:62-76`이 언더스코어 없음 → `""` 동작을 고정, `:44-59`가 다중 fulfillment order → 다중 코드 동작을 고정). 이 입력에서 변이는 라인아이템 1002의 저장된 `"NJ"`를 `""`로 지운다 — **N2가 지적한 사고가 그대로 재현**되는데 AC는 통과한다.

plan.md의 코드 자체는 정답이므로 실제 위험은 낮지만, `acceptance.md` §0의 [HARD] 판별력 규약("각 AC는 실제로 그 변이 코드를 픽스처에 대입했을 때 결과값이 달라지는지 확인한 결과다") 기준으로는 미충족이며, AC-RSW-030은 M24의 **단독** 판별자다.

**종결 조건**: AC-RSW-030의 Given에 두 번째 시나리오를 추가하거나 별도 AC를 두어라 — 로컬에 `LineItem(1001).location="NJ"`, `LineItem(1002).location="NJ"`, 모킹 반환값 `("CA", {1001: "CA", 1002: ""})` → Then `1001.location=="CA"`(신선값 반영) **그리고** `1002.location=="NJ"`(빈값이 기존값을 지우지 않음) **그리고** `Order.location=="CA"`.

### MINOR

**D3. HISTORY(`spec.md:21`)의 "정정된 수치"가 §8 C11(`spec.md:302`)과 정반대다 — N6를 고치면서 새 사실 오류를 만들었다.**
- HISTORY: "정정된 수치(**번들 SKU가 없는 주문에서는 15→14, 있는 주문에서는 절감 없음**)를 §8 C11에 남겼다"
- §8 C11 실제 본문: "번들 SKU가 전혀 없는 주문에서는 … 절감은 약 15 → 약 14이고, **번들 SKU가 있는 주문에서만 도서 제목 쿼리까지 절감되어 약 15 → 약 13에 가까워진다**"

**C11이 옳고 HISTORY가 틀렸다.** 호이스팅이 제거하는 쿼리는 (i) 모든 주문에서 `ShopifySkuSetMapping` 1개, (ii) 번들 SKU가 있는 주문에서만 `_build_title_map` 1개 — 번들 없는 주문은 `if not isbn_list: return {}`(`shopify_orders.py:62-63`)로 애초에 쿼리를 내지 않기 때문이다. 즉 번들 주문이 **더 많이** 절감한다. §1(`spec.md:33`)은 C11로 위임만 하므로 규범 텍스트에는 오염이 없다. 그러나 이번 감사가 HISTORY를 근거로 채택했다면 그대로 오판했을 항목이며, **HISTORY 서술이 본문의 신뢰할 만한 요약이 아니라는 증거**로 기록한다.

**D5. 결번 안내(`acceptance.md`)의 개수 표기 오류 3건 — N9를 고치면서 새 계수 오류가 들어왔다.**
- `:59` "001–026(26개) + 007b + 014b + 029b + 030 + 033 + 034(**7개**)" — 열거는 **6개**이고 `AC-RSW-029`가 빠졌다. 총계 33은 7개일 때만 맞으므로 **누락된 항목이 029**임이 확정된다. 하필 029는 [핵심] 단독 판별자(M20)다.
- `:670` DoD "…결번 **5개**(027/028/031/032, …)" — 열거는 4개다(v0.2.0 시점 030 포함 5개였던 잔재).
- `:670` DoD의 열거 "AC-RSW-001 ~ AC-RSW-026, AC-RSW-007b, …"에는 `AC-RSW-014b`가 빠져 있다 — §0.2가 014b를 "001–026" 범위 밖으로 따로 세는 규약을 세웠으므로 자기 규약과 불일치.

실질 총계 33은 §추적표(`:595-627`) 33행 전수 계수로 **정확함을 확인**했고 REQ 커버리지에도 영향이 없다. 순수 표기 오류.

**D6. 모킹 대상 네임스페이스가 미지정이라, 저장소 기존 관례를 그대로 따르면 AC 다수가 실패한다.**
`plan.md:186-192`가 커맨드 모듈에서 `from order.shopify_orders import _build_fulfillment_location_data, _get_with_headers, _sync_single_order`로 **이름을 커맨드 모듈에 바인딩**한다. 저장소의 기존 관례는 `patch("order.shopify_orders._get_with_headers", ...)`(`test_order_location.py:55/72/82/101`, `test_order_resync.py:281`)인데, 이 대상으로는 커맨드 모듈의 바인딩이 교체되지 않아 실제 네트워크 호출이 발생한다. `acceptance.md:50`은 "`_get_with_headers`, `_build_fulfillment_location_data`는 … 모킹한다"고만 적고 경로를 지정하지 않으며, §0.1이 "관례를 재사용한다"고 지시하므로 잘못된 경로가 선택될 확률이 높다. AC-007/007b/009/010의 `_sync_single_order` 모킹도 동일하다.
**종결 조건**: §0.1에 한 줄 — "패치 대상은 `order.management.commands.resync_order_sweep.<name>`이다(커맨드가 `from … import`로 이름을 바인딩하므로 `order.shopify_orders.<name>` 패치는 효과가 없다)". 또는 plan.md §1.3에서 `from order import shopify_orders` 후 `shopify_orders.<name>()` 호출 형태로 바꿔라.

**D7. §8 C9의 빈도 서술이 손상 발생 빈도로 오독된다.** Part 1에서 검증한 대로 "약 8회·일"은 경로 진입 빈도이며 고아 행 생성은 "번들 매핑 추가 시점, 해당 주문당 1회, 이후 영구 잔존"이다. 한 문장 보강 권고(결함 아님, 정확도 개선).
**D7b. `plan.md:315-319`의 `dict(LineItem.objects.filter(order=order).values_list("shopify_line_item_id","location"))`은 번들 확장 주문에서 동일 `shopify_line_item_id`의 N행을 조용히 1건으로 축약하며 생존자가 비결정적이다.** 정상 상태에서는 멤버 행들이 같은 `common_defaults["location"]`을 공유하므로 무해하지만, 고아 `sku=bundle_sku` 행이 과거 동기화의 다른 위치값을 들고 있으면 폴백 값이 그 쪽으로 결정될 수 있다. 폴백은 어차피 "빈값으로 지우지 않는다"가 목적이므로 피해는 없다. 기록용.

**D8. §0.1 성공 증거 규약의 회색지대 1건(AC-RSW-008).** Part 2 (C) 참조. 커버리지 손실 없음.

**D9. plan.md의 iteration 2 잔여 미조치 2건.** ① `plan.md:671`이 AC-RSW-033을 M6(커맨드 마일스톤)에 계속 배정하나, 이 AC는 `_qualifying_orders_queryset()`만 평가하므로 M2가 맞다(iteration 2 N9 부수 지적, 미조치). ② `plan.md:720` R2의 괄호 문구 "기대 처리 순서(E→F→G의 역순, 즉 실제 생성은 E→F→G)"가 자체로 뒤엉켜 읽힌다 — `acceptance.md:156`의 서술은 명확하므로 실행에 지장은 없다.

---

## Part 4 — 판별력 최종 선언(감사 우선순위 5)

| 위험 영역 | 진짜 판별력 있는 AC 존재? | 근거 |
|---|---|---|
| 위치가 갱신되지 않는다 | **예** | AC-RSW-014(`acceptance.md:290-301`) — NJ→CA + `CommandError` 부재. `sync_store():420-428`의 단축 경로 이식 변이를 직접 잡는다 |
| 위치가 조용히 지워진다 — **예외 경로** | **예** | AC-RSW-014b(`:305-316`) — `raise_on_error` 미전달 변이를 `"" ≠ "NJ"` + "실패 목록에 없음"으로 이중 판별 |
| 위치가 조용히 지워진다 — **정상-빈값 경로** | **부분** | AC-RSW-030(`:320-333`)이 **전면 빈값**은 판별하나 **부분 빈값**은 판별하지 못한다(D4). 병합 자체의 존재는 확인되고, 전부-아니면-전무 구현만 빠져나간다 |
| `last_resynced_at`이 전진하지 않는다 | **예** | AC-RSW-008(성공 경로) + AC-RSW-009(예외 경로, 단독). `finally` 배치를 구조적으로 강제 |
| 워터마크가 스위프에 의해 전진한다 | **예** | AC-RSW-013(`:275-286`) T1/T2 불변 + `CommandError` 부재. DoD의 "`StoreSyncWatermark` import 부재"(`:692`)로 코드 레벨 이중 강제 |
| 수동 값이 되돌려진다 | **부분** | `purchase_status`: AC-RSW-017 **예**(기본값 `unordered`와 다른 `cs_required` 픽스처). `original_sku`: AC-RSW-019/020 **예**. `logistics_status`: AC-RSW-018 **아니오 — 픽스처가 모델 기본값과 동일해 리셋 변이에 퇴화(D2)** |
| 환불 행이 유실되거나 중복된다 | **예(전 시나리오)** | 유실 AC-RSW-021(단독) / stale 삭제 AC-RSW-022 / 반복 중복 AC-RSW-029(2회 실행, 단독) / **선존 중복 자가치유 AC-RSW-029b(단독, 신규)**. `unique_fields` 재도입 변이는 `NotSupportedError` → `CommandError` 부재 단정이 잡는다. 미커버 잔여: `line_item_id`가 NULL↔non-NULL로 전이하는 케이스(튜플 비교로 정상 동작함은 iteration 2가 확인, AC로는 고정되지 않음) |
| 부분 입고 필드가 보존되지 않는다 | **예** | AC-RSW-034(단독) — 픽스처 값이 전부 모델 기본값과 다르다(`received_quantity=2` vs 0, `rack_number="A-3"` vs `""`, `confirmed_price=9.99` vs None). D2와 같은 퇴화 없음. 대상 포함 여부는 AC-RSW-033. 선언된 미커버: stale-삭제로 행 자체가 사라지는 경로(§8 C10, 의도적) |

---

## Part 5 — 정량 주장 재검증(감사 우선순위 6)

| 주장 | 검증 |
|---|---|
| 주문당 약 15쿼리 | `_sync_single_order` 본문(`:104-331`)으로 재구성: Order upsert 2 + ShopifySkuSetMapping 1 + protected_sku 1 + 라인아이템 upsert 2/건 + stale delete ~2 + shipping_lines delete ~2 + bulk_create 1 + refunds delete ~2 + refund upsert 2/건 (+ Customer/주소 upsert 각 2). 주문당 평균 3.96 라인아이템 기준 **~15는 타당한 자릿수**. 정확한 값이 아니라 "약"으로 표기한 것도 적절 |
| 호이스팅 절감 "번들 없는 주문 15→14 / 번들 주문 15→13" | **§8 C11 기준으로 정확.** `_build_title_map`의 조기 반환(`shopify_orders.py:62-63`)을 정확히 반영했다. **HISTORY의 반대 서술만 오류(D3)** |
| 1차 성능 해법은 라운드로빈이지 호이스팅이 아니다 | **세 문서 일관.** `spec.md:33`("실제로 해소하는 것은 라운드로빈 아키텍처 그 자체다 — 호이스팅은 부차적"), `spec.md:302`("이 SPEC이 검증하는 것은 REQ-RSW-023뿐"), Exclusions #1, `plan.md:0`/R6. 모순 0건 |
| 랩 약 2.8시간 / 약 8회·일 | 1,328 ÷ 40 = 33.2 사이클 × 5분 = 166분 = 2.77시간 ✓, 24 ÷ 2.77 = 8.7회·일 ✓ |
| 전체 재동기화 2시간 초과 | 3,883 × 2초 = 7,766초 = 2.16시간 ✓ |
| 페이싱 sleep 5회 × 0.3(AC-026) | `plan.md:268-275`의 `_pace()`와 대조 — 3주문 × 2호출 = 6개 페이싱 지점, 첫 호출만 `last_call_at is None` → sleep 5회, `time.monotonic` 고정 시 `0.3 - 0 = 0.3` ✓ |

---

## Chain-of-Verification Pass

1차 판정 후 재점검한 항목과 결과:

- **"CLOSED"를 문구 존재만으로 판정하지 않았는가** → N1은 명분 삭제 문장을 읽는 데 그치지 않고, ① 세 문서에서 번들 의존 이득 주장을 전수 검색해 0건임을 확인하고 ② §8 C9가 주장하는 "수량 집계 오염"이 사실인지 **집계 지점을 직접 열어** 검증했다(`purchase_order_views.py:94-111`, `:170-191`, `:344-368`, `:2891-2894`). 그 과정에서 오염이 오히려 과소 표현되었다는 점과, "8회·일"이 손상 빈도가 아니라는 점(D7)을 함께 확인했다.
- **저자 요약(및 프롬프트 요약)을 근거로 쓰지 않았는가** → 쓰지 않았다. 결정적 사례: 프롬프트와 HISTORY가 공통으로 전한 "번들 주문은 절감 없음"이 §8 C11 본문과 정반대였다(D3). 본문을 직접 열지 않았다면 그대로 통과시켰을 항목이다.
- **REQ를 전건 읽었는가** → 32개 활성 REQ 전건에서 `shall`/`shall not`의 실재와 패턴 라벨 정합을 개별 확인했다. 표본 검사였다면 REQ-RSW-012의 `(Complex)` 라벨과 REQ-RSW-030의 하위 절 구조를 검증하지 못했을 것이다.
- **추적성을 표본이 아니라 전건으로 봤는가** → `spec.md:229-264` 34행 전부를 `acceptance.md`의 실제 `Traces:` 선언과 양방향 대조했다(불일치 0). 이 과정의 부산물로 `acceptance.md:59`의 열거 누락(029)을 발견했다(D5) — REQ 커버리지에는 영향 없음을 §추적표 33행 재계수로 확인했다.
- **Exclusions를 존재 여부가 아니라 구체성으로 봤는가** → 13개 전부 "무엇을 하지 않는가 + 왜 + 대신 무엇을 하는가" 구조다. 특히 #8과 #12는 iteration 2 지적 이후 단서 절이 추가되어 오독 여지가 줄었다. 막연한 항목 0건.
- **신규 3개 메커니즘을 저자의 설명이 아니라 코드로 검증했는가** → 위치 병합은 6개 시나리오로 진리표를 직접 만들었고(부분 케이스가 코드상 커버됨을 확인 — 프롬프트의 우려는 기우였고, 대신 **AC 쪽에 구멍**이 있었다: D4). 중복 정리는 "삭제되는 행의 값이 어디서 읽히는가"를 물어 `Refund` 소비 지점 14곳 + serializer + FK 유무를 전수 확인한 뒤 무해 판정했다.
- **요구사항 간 모순을 문장 내부가 아니라 문장 사이에서 찾았는가** → 찾았다. HISTORY ↔ §8 C11(D3). 그리고 REQ-RSW-022 ↔ Exclusions #8 ↔ §8 C7의 삼각 관계는 이번에도 정합함을 재확인했다.
- **"제3의 인접 코드"를 실제로 찾았는가** → **찾았다(D1).** 접근 방식은 이전 두 회차와 같았다: SPEC이 **인용한** 코드가 아니라 SPEC이 **약속한 효과가 실현되려면 반드시 존재해야 하는** 코드를 찾아 나섰다. "close/cancel을 채운다"는 명분이 성립하려면 그 값을 읽는 소비자가 있어야 하는데, `backend/` 전수 검색 결과 쓰기 4곳·읽기 0곳이었고 `_reorder_candidate_filter`에도 취소 조건이 없었다. iteration 1의 migration `0026`, iteration 2의 `test_order_location.py:62`와 같은 계열이다.
- **AC 픽스처의 값이 모델 기본값과 겹치지 않는지 확인했는가** → 이번에 처음 수행했고 D2를 발견했다. AC-018만 퇴화하고 017/019/020/034는 건전함을 개별 확인했다.
- **인용 정확도** → 이번 회차에 검증한 인용: `models.py:79-80/170/182/189/190-194/195-197/204-208/221-229/238/247/253/312/320/328/342`, `shopify_orders.py:62-63/72-101/86-99/104/159-166/231-243/242/244-270/287-289/291-329`, `purchase_order_views.py:94-111/124-206/170-178/180-191/344-368/2891-2894`, `views.py:188-229`, `serializers.py:177-183/436`, `test_order_location.py:44-59/62-76/79-88/148-194`, `test_order_resync.py:255-292`, `frontend/src/types/order.ts:224-225`. **전건 정확했다.** 세 회차 연속으로 인용 정확도 자체는 결함이 아니었다.

신규 발견: D1, D2, D3, D4, D5, D6, D7/D7b, D8, D9. 전부 위에 반영했다.

---

## Regression Check (iteration 2 → 3)

| 이전 결함 | 상태 |
|---|---|
| **MP-2** (REQ-032 비규범) | **RESOLVED** — REQ 삭제 + 결번 3-place 명시, §5에 비규범 문장 신규 유입 0건 |
| N1 (번들 명분 모순) | **RESOLVED** — 명분 삭제 + 5개 지점 범위 정렬, 결과 서술의 정확성도 집계 지점 대조로 확인 |
| N2 (정상-빈값 위치) | **PARTIALLY RESOLVED** — REQ/plan 설계는 완전 종결(부분 케이스 포함), AC 판별력만 미완(D4) |
| N3 (환불 자가치유) | **RESOLVED** — 결정적 생존자 + 데이터 유실 없음(소비 지점 전수 확인) + AC-029b |
| N4/N4b (성공 증거) | **RESOLVED** — 15개 AC 전수 대조, AC-018 판별력 논리도 재검증 |
| N5 (AC-006 정렬 제거) | **RESOLVED** |
| N6 (REQ-032 미검증 수치) | **RESOLVED** — HISTORY 서술만 오류(D3, MINOR) |
| N7 (문서 간 추적 불일치) | **RESOLVED** — 32건 양방향 전수 대조, 불일치 0 |
| N8 (REQ-034 근거) | **RESOLVED** |
| N9 (AC 결번) | **RESOLVED** — 신규 표기 오류 3건(D5, MINOR) |
| N10 (기본값 40) | **RESOLVED** — AC-RSW-007b |
| N11 (`[HARD]` 누락) | **RESOLVED** |
| N12 (구현 기법 잔재) | **ACCEPTED** — §8 C12에 명시적 수용, 감사도 동의 |
| N13 | 기록용, 조치 불요 |

**Stagnation 판정: 없음.** iteration 2가 경고한 D12→N6 사슬("요구사항 절에 `shall` 없는 범위 면책 선언")은 v0.3.0에서 재발하지 않았다 — REQ-RSW-032를 삭제하면서 그 내용을 §8 C11의 **비규범 참고치**로 정확히 재배치했고, 새로 추가된 REQ 절(030의 (a)/(b), 029의 자가치유 절)은 전부 `shall`을 갖춘 시스템 행동이다. blocking 격상 사유 없음.

3회차 결함 누계 추이: iteration 1 CRITICAL 4 / iteration 2 CRITICAL 2 / **iteration 3 CRITICAL 0, MAJOR 3, MINOR 6.**

---

## Recommendation

**PASS 근거(must-pass 4항목)**:
- MP-1: 활성 32 + 결번 2, 중복·패딩 결함 0, 결번 3-place 명시(`spec.md:98/258/262/297/302`), 댕글링 참조 0.
- MP-2: 32개 REQ 전건에서 `shall`/`shall not` 실재 및 패턴 정합 확인, iteration 2의 유일한 FAIL 원인(REQ-RSW-032) 완전 제거, 동종 재발 0.
- MP-3: `spec.md:1-11` 6개 필수 필드 전부 존재·타입 정합.
- MP-4: 단일 언어 SPEC, N/A.

**`/moai run` 진입을 막을 blocking 결함은 없다.** 아래는 잔여 항목의 처분 지정이다.

### 구현 착수 전에 처리할 것(문서 1줄~1블록, 코드 영향 없음)

1. **D1 — §8에 C13을 추가하라(권장, 그러나 blocking 아님).** "`closed_at`/`cancelled_at`은 현재 백엔드의 어떤 조회·필터·집계도 읽지 않는다(`_reorder_candidate_filter`·`_apply_logistics_display_filter`·`_recompute_order_aggregates` 전부 미참조, 프런트엔드도 타입 선언만 존재). 이 SPEC은 데이터 정확성만 확보하며 소비 로직은 후속 과제다. 대상 판정도 취소/종료 주문을 배제하지 않으므로 그 주문들은 60일 창이 닫힐 때까지 라운드로빈 슬롯을 계속 점유한다." — **이 한 항목이 추가되면 D1은 '수용된 문서화 개방 위험'이 된다. 추가되지 않으면 명분 과장이 문서에 남는다.**
2. **D3 — `spec.md:21` HISTORY의 "있는 주문에서는 절감 없음"을 §8 C11 본문과 일치시켜라**("있는 주문에서는 도서 제목 쿼리까지 절감되어 약 15→13").
3. **D5 — `acceptance.md:59`의 열거에 `AC-RSW-029`를 추가하고, `:670`의 "결번 5개"를 "4개"로, DoD 열거에 `AC-RSW-014b`를 명시하라.**

### RED 작성 시점(M4/M6)에 반드시 반영할 것 — 반영하지 않으면 해당 변이가 영구 미커버

4. **D2 — AC-RSW-018의 Given을 라인아이템 2건으로 바꿔라.** 1건은 자격용 `logistics_status="not_shipped"`, 1건은 보호 대상 `logistics_status="received"`. Then에 후자가 `"received"`로 유지되는지 단정. (현재 픽스처는 모델 기본값과 같아 리셋 변이에 퇴화한다 — `models.py:207`.)
5. **D4 — AC-RSW-030에 부분-빈값 시나리오를 추가하라.** 모킹 반환 `("CA", {1001: "CA", 1002: ""})`, 로컬 두 행 모두 `"NJ"` → Then `1001=="CA"`, `1002=="NJ"`, `Order.location=="CA"`. (현재 전면 빈값 모킹만으로는 전부-아니면-전무 병합 변이가 빠져나간다.)
6. **D6 — `acceptance.md` §0.1에 패치 대상 경로를 명시하라**: `order.management.commands.resync_order_sweep.<name>`. 저장소 기존 관례(`order.shopify_orders.<name>`)를 그대로 따르면 커맨드 모듈 바인딩이 교체되지 않아 실제 네트워크 호출이 발생한다(`plan.md:186-192`의 `from … import` 형태 때문).

### 수용된 개방 위험(조치 불요, `/moai run` 진행 가능)

- **N12 / §8 C12** — 요구사항 층의 구현 기법 잔재. 인용은 전부 정확하며, 이 시점의 재작성이 새 불일치를 만들 위험이 더 크다는 저자의 판단에 동의한다.
- **§8 C9** — 번들 고아 행. 명분에서 제거되고 3개 지점에서 배제가 선언되었으며 결과 상태도 정확히 서술되었다. D7의 빈도 프레이밍은 정확도 개선 권고일 뿐이다.
- **§8 C10** — stale-삭제로 인한 입고 필드 손실. 정직하게 선언됨.
- **REQ-RSW-002 / plan.md §1.1** — `EXPLAIN`이 filesort를 보일 경우의 대안 선택이 Run 단계로 유예되어 있다. 실측 없이 단정하지 않겠다는 판단이 옳으며, 대안 2안이 미리 제시되어 있다.
- **D7b / D8 / D9** — 기록용. 실행에 지장 없음.
