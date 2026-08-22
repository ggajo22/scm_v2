# SPEC-ORDER-028 — 인수 기준 (Acceptance Criteria)

대상 파일: `backend/order/tests/test_spec_028.py` `[NEW]`(AC-RSW-001~035 범위 내 실재 35개, 결번 안내는 §0 참고) + 기존 회귀 스위트 5개(`test_shopify_orders.py`, `test_order_resync.py`, `test_backfill_missing_orders_command.py`, `test_sync_orders_command.py`, `test_order_location.py`, 무수정 통과 확인만)

**[v0.3.0, plan-audit 2차 리뷰(FAIL 0.68) 반영]** 이 문서는 다음을 신규/재설계했다: AC-RSW-030(N2 — 정상-빈값 위치 보존), AC-RSW-029b(N3 — header-only 환불 선존 중복 자가치유), AC-RSW-007b(N10 — `--count` 기본값 40), AC-RSW-006(N5 — 픽스처 생성 순서를 기대 처리 순서와 의도적으로 불일치), 그리고 §0.1의 [HARD] "처리됨" 규약을 "성공" 증거로 강화하고 그 규약을 실제로 지키지 않던 8개 AC(013/014/021/022/023/024/026/029)와 보존 계열 4개(017~020)에 증거를 추가했다(N4/N4b). 문서 간 추적 불일치 3건(N7)도 정정했다. 상세 대응은 `spec.md` HISTORY v0.3.0 참조.

**[v0.4.0, 사용자 확정 결정 반영]** 대상 연령 상한 60일 → 30일(재론 아님, 구현). AC-RSW-003/004의 경계 픽스처를 61일/59일 → 31일/29일로 갱신했다(REQ-RSW-003(b)). AC-RSW-035(`--days` 명시적 override)와 AC-RSW-035b(`--days` 생략 시 커맨드 경로 전체에 기본값 30 적용)를 신설했다(REQ-RSW-035, M26/M27). **carry-forward(2차 감사가 RED-test-time·non-blocking으로 유예한 항목, 이번 개정에서도 손대지 않음)**: AC-RSW-018의 `logistics_status="not_shipped"` 픽스처가 모델 기본값과 동일한 문제, AC-RSW-030이 전체-빈값 `("", {})` 형태만 모킹하는 문제, 모의 패치 대상이 명시되지 않은 문제. 상세 대응은 `spec.md` HISTORY v0.4.0 참조.

**[v0.5.0, plan-audit v0.4.0 델타 감사(PASS 0.78) 반영]** **감사 D1**(N7 재발) — AC-RSW-035b의 `Traces:`가 `REQ-RSW-003`만 선언해 `spec.md` §6(REQ-RSW-035 → AC-035/AC-035b)과 불일치했다 — `REQ-RSW-003, REQ-RSW-035`로 정정했다. 재발 방지로 35개 AC의 `Traces:` 전체를 §6과 기계적으로 재대조했다(이 건 외 불일치 0건). **감사 D4** — AC-RSW-035b가 35일 주문 1건의 순수 음성 단정뿐이라 기본값이 30→20으로 어긋나는 변이와 전면 실패 시나리오를 놓쳤다 — Given에 29일 양성 대조군(주문 O)을 추가하고 Then에 O의 성공 증거를 추가했다(M27). §0.1 규약 재확인 목록에 035/035b를 편입했다. **감사 D6** — DoD 신규 검증 열거가 34개를 나열하고 35개라 표기했다(`AC-RSW-014b` 누락) — 열거를 정정했다. 상세 대응은 `spec.md` HISTORY v0.5.0 참조. **수용된 개방 위험(조치 불요, 이번 개정에서 손대지 않음)**: 감사 D5(AC-035/035b의 Given이 `_make_qualifying_order()` 오버라이드 스타일 대신 처음부터 서술) — RED 작성 시점 반영으로 유예.

## 0. 이 문서를 읽는 방법 — 판별력(mutation discrimination) 규약

[HARD] 통과하는 테스트가 곧 검증된 구현은 아니다. 이 SPEC의 모든 AC는 자신이 잡는 변이(mutation)를 명시한다. 각 AC는 실제로 그 변이 코드를 픽스처에 대입했을 때 결과값이 달라지는지 확인한 결과다.

**MySQL에서 판별 불가능한 변이는 "판별 불가"로 정직하게 명시한다.** `nulls_first=True` 파라미터의 유무는 이 DB에서 컴파일되는 SQL이 바이트 단위로 동일하므로(spec.md 가정 A4a), 그 파라미터 자체를 겨냥한 판별은 설계하지 않는다 — 대신 REQ-RSW-005가 요구하는 **결과**(처리 순서)를 직접 검증한다.

**[v0.3.0, 감사 N4/N4b 반영] "처리됨"과 "성공했다"는 다르다.** `last_resynced_at`은 성공·실패·위치조회실패 세 경로 모두에서 `finally`(D1)로 전진하므로, 그 필드가 `None`이 아니라는 사실만으로는 그 주문이 **성공**했는지 증명하지 못한다 — 어떤 변이가 모든 주문을 예외로 실패시켜도 이 필드는 여전히 전진하고, 그 결과 "무변경"류 보존 단정은 공허하게 통과할 수 있다. 이 문서에서 `resync_order_sweep`을 실행하고 데이터 보존/반영을 주장하는 모든 AC는 다음 중 하나의 명시적 **성공** 증거를 Then에 포함해야 한다(둘 다 포함하면 더 좋다): **(a)** 그 사이클이 `CommandError` 없이 종료했다(실패 0건), **(b)** 그 실행에서 Shopify가 실제로 바꾼 다른 값(예: `title`)이 반영되었다. 이 규약은 §추적표 직전의 Definition of Done에서 실제 준수 여부를 AC별로 재확인한다.

이 SPEC이 반드시 잡아야 하는 **27개** 변이:

| ID | 범위 | 변이 | 판별 AC |
|----|------|------|---------|
| **M1** | BE | 연령 상한(기본값 30일, v0.4.0) 필터가 없거나 경계값이 틀림 | AC-RSW-003(음성), AC-RSW-004(경계 양성) |
| **M2** | BE | `not_shipped` 조건 자체가 잘못됨(다른 상태로 대체되거나 전체 상태 허용) | AC-RSW-001(양성), AC-RSW-002(음성) |
| **M3** | BE | 대상 판정이 JOIN+fanout으로 구현되어 다중 라인아이템 주문이 중복 반환된다 | **AC-RSW-005 (단독)** |
| **M4** | BE | 정렬 결과가 "한 번도 스윕되지 않은/오래 전 스윕된 주문 우선"이 아니다(방향 반전 또는 `order_by` 자체 삭제) | **AC-RSW-006 (단독)** — 처리 결과로 검증, 픽스처 생성 순서를 기대 처리 순서와 의도적으로 불일치시켜 두 변이 모두 커버(v0.3.0, 감사 N5) |
| **M5** | BE | `--count`(N) 파라미터가 무시되어 전체 대상이 처리된다 | **AC-RSW-007 (단독)** |
| **M6** | BE | "변경 없음" 성공 케이스에서 `last_resynced_at` 갱신이 누락된다 | AC-RSW-008 |
| **M7** | BE | 예외 발생 케이스에서 `last_resynced_at` 갱신이 누락된다(poison order) | **AC-RSW-009 (단독)** |
| **M8** | BE | 주문 1건의 예외가 전체 사이클을 중단시킨다(나머지 주문 미처리) | **AC-RSW-010 (단독)** |
| **M9** | BE | 실패가 있어도 커맨드가 항상 종료코드 0을 반환한다(CommandError 미발생) | AC-RSW-011(양성), AC-RSW-012(음성) |
| **M10** | BE | `StoreSyncWatermark`가 스위프에 의해 갱신된다 | **AC-RSW-013 (단독)** |
| **M11** | BE | fulfillment location 갱신이 생략된다(`sync_store()`의 재사용 단축 로직이 유입됨) | **AC-RSW-014 (단독)** |
| **M12** | BE | close/cancel 감지 실패(`status=open` 목록 피드를 오용) | AC-RSW-015(closed), AC-RSW-016(cancelled) |
| **M13** | BE | 매뉴얼 필드(`purchase_status`/`logistics_status`)가 스위프에 의해 되돌려진다 | AC-RSW-017, AC-RSW-018 |
| **M14** | BE | `original_sku` 보정이 스위프에 의해 되돌려진다(번들/비번들 각각) | AC-RSW-019, AC-RSW-020 |
| **M15** | BE | 환불 데이터가 유실된다(non-null line_item_id) | **AC-RSW-021 (단독)** |
| **M16** | BE | 환불/배송라인 stale 행이 삭제되지 않고 누적된다 | AC-RSW-022(환불), AC-RSW-023(배송라인) |
| **M17** | BE | `bundle_map`/`title_map`이 사이클당 1회가 아니라 주문마다 재계산된다 | **AC-RSW-024 (단독)** |
| **M18** | BE | 리팩터 이후 기존 단건 호출부(`sync_single_order_from_shopify`)가 회귀한다 | **AC-RSW-025 (단독)** |
| **M19** | BE | API 호출 사이 페이싱 간격이 요구된 상수(0.3초)보다 짧다(호출률 증가) | **AC-RSW-026 (단독)** — 계산된 대기값 자체를 단정 |
| **M20** | BE | header-only(line_item_id NULL) 환불 행이 반복 스위프마다(정상 상태에서 시작) 중복 INSERT된다 | **AC-RSW-029 (단독)** |
| **M21** | BE | fulfillment 조회가 **예외로** 실패했을 때 `Order.location`이 빈 값으로 덮어써지고 그 주문이 성공으로 기록된다 | **AC-RSW-014b (단독)** |
| **M22** | BE | 스위프가 갱신하는 LineItem에서 `received_quantity` 등 비-Shopify 필드가 덮어써진다 | **AC-RSW-034 (단독)** |
| **M23** | BE | header-only 환불 키에 **선존 중복**(2건 이상)이 있을 때 upsert가 `MultipleObjectsReturned`로 그 주문을 영구 실패시킨다 `[v0.3.0 신규, 감사 N3]` | **AC-RSW-029b (단독)** |
| **M24** | BE | fulfillment 조회가 **예외 없이 정상적으로** 빈 값을 반환했을 때 `Order.location`이 빈 값으로 덮어써진다(M21과 트리거가 다름) `[v0.3.0 신규, 감사 N2]` | **AC-RSW-030 (단독)** |
| **M25** | BE | `--count`를 생략했을 때 기본값 40이 적용되지 않는다(무제한 처리 등) `[v0.3.0 신규, 감사 N10]` | **AC-RSW-007b (단독)** |
| **M26** | BE | `--days`로 지정한 값이 무시되고 대상 판정에 반영되지 않는다(CLI 인자가 큐잉 쿼리까지 전달되지 않음) `[v0.4.0 신규]` | **AC-RSW-035 (단독)** |
| **M27** | BE | `--days`를 생략했을 때 커맨드 경로에서 기본값 30이 적용되지 않는다(옛 상수 60이 되살아나는 등) `[v0.4.0 신규]` | **AC-RSW-035b (단독)** |

**[HARD] 단독 판별자 보호 규칙**: AC-RSW-005/006/007/007b/009/010/013/014/014b/021/024/025/026/029/029b/030/034/035/035b 중 하나라도 삭제·약화·픽스처 변경되면 해당 변이가 즉시 미커버가 된다.

### 0.1 픽스처 규약

- 백엔드 테스트는 `test_spec_014.py`/`test_spec_027.py`의 헬퍼 관례(`_make_order`, `_make_line_item`)를 재사용하거나 동일 시그니처로 재정의한다.
- 관리 커맨드 테스트는 `test_sync_orders_command.py`/`test_backfill_missing_orders_command.py`의 `call_command` + `unittest.mock.patch` 관례를 재사용한다 — Shopify API 호출(`_get_with_headers`, `_build_fulfillment_location_data`)은 별도로 명시하지 않는 한 실제 네트워크 호출 없이 모킹한다.
- **대상 조건 충족 헬퍼.** `resync_order_sweep`를 실행하는 모든 AC는 `_make_qualifying_order(**overrides)` 헬퍼(신규, `test_spec_028.py`에 정의)로 기준 픽스처를 만든다 — 이 헬퍼는 기본으로 REQ-RSW-003을 만족하는 주문(라인아이템 1건, `logistics_status="not_shipped"`, `quantity=1`, `Order.shopify_created_at=timezone.now() - timedelta(days=10)`)을 생성한다. 각 AC의 Given은 이 기준으로부터의 **차이만** 기술한다. 이 헬퍼를 우회해 대상 조건을 만족하지 않는 픽스처로 "무변경/보존" 계열 AC를 작성하는 것은 금지한다.
- **[HARD, v0.3.0 강화, 감사 N4/N4b] "성공" 단정.** `resync_order_sweep`를 실행하고 데이터 보존/반영을 주장하는 모든 AC의 Then은 최소한 다음 중 하나를 명시적으로 포함한다 — **(a)** 그 사이클이 `CommandError` 없이 종료했다(실패 0건), **(b)** 그 실행에서 Shopify가 실제로 바꾼 값(예: `title`)이 반영되었다. `last_resynced_at`이 `None`이 아니라는 사실만으로는(그것만으로는 "선택되어 처리 시도됨"의 증거일 뿐 "성공"의 증거가 아니므로) 이 요구를 충족하지 못한다 — 여전히 함께 단정하되(처리 대상으로 선택되었다는 사실 자체도 유용한 정보이므로), 그것이 유일한 증거여서는 안 된다.
- 시간 관련 단정(`last_resynced_at`, 연령 상한 경계(기본값 30일, v0.4.0))은 `django.utils.timezone.now()`를 고정하거나 직접 계산한 `timedelta` 오프셋으로 결정론적으로 만든다.
- 쿼리 횟수 단정(AC-RSW-024)은 `django.test.utils.CaptureQueriesContext`를 사용하고, `order_shopify_sku_set_mapping` 테이블(`ShopifySkuSetMapping.Meta.db_table`, `models.py:556`)을 포함하는 쿼리만 필터링해서 센다 — `_sync_single_order`가 실행하는 다른 다수의 쿼리(LineItem 조회, 환불/배송라인 쓰기 등)와 섞이지 않도록 한다. **HTTP 계층만 모킹하고 `_sync_single_order`는 모킹하지 않는다** — 실물 함수가 실제로 실행되어야 이 AC가 M17을 판별할 수 있다.
- 페이싱 단정(AC-RSW-026)은 `time.monotonic`을 고정값(항상 동일 값 반환)으로 모킹해 "경과 시간 0"을 시뮬레이션하고, `time.sleep` 호출 인자가 정확히 상수(0.3)인지 직접 단정한다.

### 0.2 AC 번호 결번 안내 `[v0.3.0 신규, 감사 N9]`

실재하는 AC는 **35개**다: 001–026(26개) + 029 + 030 + 033 + 034 + 035(5개) + 007b + 014b + 029b + 035b(4개, `b` 접미사). "AC-RSW-001~035"라는 범위 표기는 번호 상한을 가리킬 뿐 35개 연속을 뜻하지 않는다 — 아래 4개 번호는 결번이며 각각 이유가 있다(**주의: 030은 결번이 아니다** — `AC-RSW-030`은 REQ-RSW-030(b) 대응으로 실재하는 v0.3.0 신규 AC다. 숫자가 연속돼 보이는 027~032 구간에서 030만 실재하고 나머지 4개가 결번이라는 사실이 오해를 부르기 쉬워 명시한다):

| 결번 | 사유 |
|------|------|
| 027 | REQ-RSW-027(스케줄러 등록)은 AC 없이 DoD로만 검증된다(`.bat` 파일 존재 확인) — `spec.md` §6 참조 |
| 028 | REQ-RSW-028 자체가 결번이다(비규범 권고로 §8 C6 이동, iteration 1 D12) |
| 031 | REQ-RSW-031(번들 stale-삭제 무수정)은 AC 없이 DoD로만 검증된다(`git diff` + 기존 회귀 테스트 무수정 통과) — `spec.md` §6 참조 |
| 032 | REQ-RSW-032 자체가 결번이다(비규범 범위 면책 선언이라 삭제, iteration 2 N6/MP-2) |

번호 체계 참고: 새 AC는 대응 REQ 번호를 미러링하는 것이 원칙(029/033/034/035)이나, `AC-RSW-014b`/`AC-RSW-029b`/`AC-RSW-035b`는 "형제 AC의 두 번째 시나리오"를 뜻하는 `b` 접미사 관례를 따른다(각각 AC-014/AC-029/AC-035의 실패·중복·기본값 변형).

---

## 대상 판정 쿼리 (`_qualifying_orders_queryset`)

## AC-RSW-001 — [핵심] not_shipped 라인아이템 1건이 있는 주문(연령 상한 이내, 기본값 30일)이 대상에 포함된다

Traces: REQ-RSW-003
잡는 변이: **M2 (양성, AC-002와 공동)**

**Given** 주문 A(`shopify_created_at`=현재-10일), 라인아이템 2건: 1건은 `logistics_status="shipped"`, 1건은 `logistics_status="not_shipped"`

**When** `_qualifying_orders_queryset()`을 평가한다

**Then** 결과 집합에 주문 A가 포함된다

**판별력**: `not_shipped` 조건을 삭제하거나 `shipped`로 잘못 바꾼 변이(M2)는 이 주문을 대상에서 빠뜨리거나 최소 1건 존재 여부를 놓친다.

---

## AC-RSW-002 — 모든 라인아이템이 shipped인 주문은 대상에서 제외된다

Traces: REQ-RSW-003
잡는 변이: **M2 (음성, AC-001과 공동)**

**Given** 주문 B(`shopify_created_at`=현재-10일), 라인아이템 전부 `logistics_status="shipped"`

**When** `_qualifying_orders_queryset()`을 평가한다

**Then** 결과 집합에 주문 B가 포함되지 않는다

**판별력**: `not_shipped` 조건을 제거해 모든 주문을 대상으로 삼는 변이는 이 음성 케이스에서 즉시 잡힌다.

---

## AC-RSW-003 — shopify_created_at이 31일 전인 주문은 not_shipped 라인아이템이 있어도 제외된다 `[v0.4.0, 30일 상한으로 경계 갱신]`

Traces: REQ-RSW-003
잡는 변이: **M1 (음성)**

**Given** 주문 C(`shopify_created_at`=현재-31일), 라인아이템 1건 `logistics_status="not_shipped"`

**When** `_qualifying_orders_queryset()`을 평가한다(인자 없이 — 기본값 30 사용)

**Then** 결과 집합에 주문 C가 포함되지 않는다

**판별력**: 연령 상한 필터를 제거하거나 기본값을 30보다 크게 잘못 둔 변이(M1)는 이 주문을 대상에 포함시켜 즉시 잡힌다.

---

## AC-RSW-004 — shopify_created_at이 정확히 29일 전인 주문은 포함된다(경계) `[v0.4.0, 30일 상한으로 경계 갱신]`

Traces: REQ-RSW-003
잡는 변이: **M1 (경계 양성)**

**Given** 주문 D(`shopify_created_at`=현재-29일), 라인아이템 1건 `logistics_status="not_shipped"`

**When** `_qualifying_orders_queryset()`을 평가한다(인자 없이 — 기본값 30 사용)

**Then** 결과 집합에 주문 D가 포함된다

**판별력**: 경계 조건을 잘못 구현하거나 30일을 29일/31일로 오프바이원 실수한 변이는 AC-003(31일, 제외)과 AC-004(29일, 포함) 양쪽을 함께 봐야 잡힌다.

---

## AC-RSW-005 — [핵심] 다중 라인아이템 주문이 중복 없이 정확히 1건으로 반환된다

Traces: REQ-RSW-004
잡는 변이: **M3 (단독)**

**Given** 주문 E, 라인아이템 3건(2건 `not_shipped`, 1건 `shipped`)

**When** `_qualifying_orders_queryset()`을 평가하고 그 안에서 주문 E의 pk 등장 횟수를 센다

**Then** 정확히 1회만 등장한다

**판별력**: JOIN + `filter(logistics_status="not_shipped")` 방식(fanout)으로 구현한 변이는, `not_shipped` 라인아이템이 2건이므로 정확히 2회 등장해 잡힌다.

---

## AC-RSW-006 — [핵심, v0.3.0 재보강, 감사 N5] 한 번도 스윕되지 않은/오래 전 스윕된 주문이 먼저 처리된다(명령 실행 결과로 검증, 생성 순서와 기대 순서를 의도적으로 불일치)

Traces: REQ-RSW-005
잡는 변이: **M4 (단독)**

**[재설계 사유]** MySQL은 `order_by_nulls_first=True`이면서 `supports_order_by_nulls_modifier=False`라, `.asc(nulls_first=True)`와 `.asc()`가 바이트 단위로 동일한 SQL을 생성한다(가정 A4a) — `nulls_first` 파라미터 자체를 겨냥한 판별은 이 DB에서 성립하지 않는다. 대신 **명령 실행 결과**(어떤 주문이 처리되었는가)로 검증한다. **[v0.3.0 추가, 감사 N5]** 픽스처를 기대 처리 순서와 **같은** 순서로 생성하면, `order_by()` 절 자체를 삭제하는 변이가 (MySQL이 흔히 반환하는 삽입/PK 순서와 우연히 일치해) 위장 통과할 수 있다 — 이를 막기 위해 생성 순서를 기대 처리 순서와 **의도적으로 뒤집는다**.

**Given** 대상 조건을 만족하는 주문 3건을 다음 순서로 **생성**한다 — 먼저 E(`last_resynced_at`=현재-10분), 다음 F(`last_resynced_at`=현재-2시간), 마지막 G(`last_resynced_at=None`). (생성 순서 E→F→G는 기대 처리 순서 G→F→E와 정반대다 — 우연한 일치를 방지하기 위한 의도적 설계)

**When** `python manage.py resync_order_sweep --count 2`를 실행한다(Shopify 호출은 성공 모킹)

**Then** 처리된 주문(= `last_resynced_at`이 갱신된 주문)은 정확히 {G, F}이며 E는 포함되지 않는다

**판별력**: 정렬 방향이 반전된 변이(DESC)는 "가장 최근에 스윕된" 순서로 처리해 {E, F}를 처리하고 G(NULL)는 제외한다 — `{G, F} ≠ {E, F}`로 즉시 잡힌다. `order_by()` 절 자체를 삭제하는 변이는 MySQL이 어떤 순서로든(흔히 삽입 순서 E→F→G) 반환할 수 있어 상위 2건이 {E, F}가 되기 쉽다 — 이 픽스처는 생성 순서를 기대 순서와 반대로 고정했으므로, "삽입 순서 그대로 반환"이 발생해도 {E, F} ≠ {G, F}로 잡힌다.

---

## 신규 관리 커맨드 `resync_order_sweep`

## AC-RSW-007 — [핵심] --count로 지정한 건수만 처리된다

Traces: REQ-RSW-006, REQ-RSW-007, REQ-RSW-008
잡는 변이: **M5 (단독)**

**Given** `_make_qualifying_order()`로 만든 대상 주문 5건

**When** `resync_order_sweep --count 2`를 실행한다(Shopify 호출은 모킹)

**Then** `_sync_single_order`(모킹 대상)가 정확히 2회만 호출되고, 그 2건의 `last_resynced_at`만 갱신된다

**판별력**: `[:count]` 슬라이싱을 빠뜨리거나 무시하는 변이(M5)는 5회 호출을 발생시켜 `2 ≠ 5`로 즉시 잡힌다.

---

## AC-RSW-007b — [핵심, v0.3.0 신규, 감사 N10] --count를 생략하면 기본값 40이 적용된다

Traces: REQ-RSW-006
잡는 변이: **M25 (단독)**

**Given** `_make_qualifying_order()`로 만든 대상 주문 45건(모두 성공 모킹)

**When** `--count` 인자 없이 `resync_order_sweep`을 실행한다

**Then** `_sync_single_order`가 정확히 40회만 호출되고, 나머지 5건의 `last_resynced_at`은 갱신되지 않는다

**판별력**: `DEFAULT_COUNT` 상수 값을 다른 값으로 바꾸거나, 인자 생략 시 상한을 적용하지 않는 변이(M25)는 호출 횟수가 40이 아니게 되어 즉시 잡힌다. AC-RSW-007은 `--count`를 **명시적으로 전달**하므로 기본값 경로 자체를 판별하지 못한다 — 이 AC가 그 공백을 메운다.

---

## AC-RSW-035 — [핵심, v0.4.0 신규] --days로 지정한 값이 대상 판정에 사용된다

Traces: REQ-RSW-035
잡는 변이: **M26 (단독)**

**Given** 주문 M(`shopify_created_at`=현재-45일), 라인아이템 1건 `logistics_status="not_shipped"`(기본값 30일 창으로는 제외되어야 할 주문)

**When** `python manage.py resync_order_sweep --days 60`을 실행한다(Shopify 호출은 성공 모킹)

**Then** 주문 M이 처리 대상에 포함된다(`last_resynced_at` 갱신 + 이 실행이 `CommandError` 없이 종료했다 — 성공 증거)

**판별력**: `--days` 인자가 파싱만 되고 `_qualifying_orders_queryset()`의 `days` 파라미터로 전달되지 않는 변이(M26)는 주문 M이 기본 30일 창에 의해 계속 제외되어 `last_resynced_at`이 갱신되지 않으므로 즉시 잡힌다.

---

## AC-RSW-035b — [핵심, v0.4.0 신규, v0.5.0 양성 대조군 추가] --days를 생략하면 커맨드 경로 전체에 기본값 30이 적용된다

Traces: REQ-RSW-003, REQ-RSW-035
잡는 변이: **M27 (단독)**

**Given** 주문 N(`shopify_created_at`=현재-35일), 라인아이템 1건 `logistics_status="not_shipped"`(30일 창 밖, 옛 60일 상한 안 — 옛 기본값이 실수로 되살아나면 포함되어 버리는 값). **[v0.5.0 추가, 감사 D4]** 함께 주문 O(`shopify_created_at`=현재-29일), 라인아이템 1건 `logistics_status="not_shipped"`(30일 창 안 — 기본값이 30보다 작은 값으로 어긋나면 제외되어 버리는 양성 대조군)

**When** `--days` 인자 없이 `resync_order_sweep`을 실행한다(Shopify 호출은 성공 모킹)

**Then** 주문 N은 처리 대상에 포함되지 않는다(`last_resynced_at` 미갱신). **[v0.5.0 추가, 감사 D4]** 주문 O는 처리 대상에 포함된다(`last_resynced_at` 갱신) + 이 실행이 `CommandError` 없이 종료했다(실패 0건 — 성공 증거)

**판별력**: 커맨드의 `add_arguments` 기본값이나 `_qualifying_orders_queryset()`의 `days` 파라미터 기본값이 30이 아닌 다른 값(예: 옛 상수 60)으로 **위쪽으로** 어긋나는 변이(M27)는 주문 N을 대상에 포함시켜 즉시 잡힌다. AC-RSW-003/004는 `_qualifying_orders_queryset()`을 **직접 호출**해 함수 레벨의 기본값만 검증하므로, 커맨드의 `add_arguments` 기본값이 별도로 어긋나는 경로는 판별하지 못한다 — 이 AC가 그 공백을 메운다. **[v0.5.0, 감사 D4]** 주문 O가 없던 v0.4.0판은 순수 음성 단정뿐이라 세 가지를 놓쳤다 — (1) 기본값이 30보다 **작은** 값(예: 20)으로 어긋나는 변이는 N이 여전히 제외되어 통과했다, (2) 스위프가 전면 실패해 아무것도 처리하지 못하는 변이도 "N이 포함되지 않는다"를 공허하게 만족시켜 통과했다, (3) §0.1 [HARD] 성공 증거 규약을 이 AC만 충족하지 못했다. 주문 O의 포함 단정(하한 고정) + 성공 증거가 세 가지를 한 번에 닫는다.

---

## AC-RSW-008 — 변경 없는 주문도 last_resynced_at이 갱신된다

Traces: REQ-RSW-011
잡는 변이: **M6**

**Given** `_make_qualifying_order()`로 만든 대상 주문 H, Shopify 응답이 로컬 상태와 동일(순수 리프레시), 실행 전 `last_resynced_at`이 NULL

**When** `resync_order_sweep`을 실행한다

**Then** 주문 H의 `last_resynced_at`이 NULL이 아닌 현재 시각 근방 값으로 갱신되어 있다

**판별력**: "변경 없음"일 때만 갱신을 건너뛰는 변이(M6)는 `last_resynced_at`이 여전히 NULL이라 즉시 잡힌다.

---

## AC-RSW-009 — [핵심] 예외가 발생한 주문도 last_resynced_at이 갱신된다(poison order 방지)

Traces: REQ-RSW-011
잡는 변이: **M7 (단독)**

**Given** `_make_qualifying_order()`로 만든 대상 주문 I, `_sync_single_order`가 예외(예: `urllib.error.HTTPError`)를 던지도록 모킹, 실행 전 `last_resynced_at`이 NULL

**When** `resync_order_sweep`을 실행한다(전체 사이클은 실패로 끝나도 무방 — 이 AC는 의도적으로 실패 시나리오를 검증하므로 §0.1의 "성공 증거" 규약 예외다)

**Then** 주문 I의 `last_resynced_at`이 NULL이 아닌 현재 시각 근방 값으로 갱신되어 있다

**판별력**: 갱신 코드를 `try` 블록의 성공 경로에만 두고 `finally`(또는 `except`)에 두지 않은 변이(M7)는 주문 I의 `last_resynced_at`이 여전히 NULL이라 즉시 잡힌다.

---

## AC-RSW-010 — [핵심] 주문 1건의 실패가 나머지 주문 처리를 막지 않는다

Traces: REQ-RSW-010
잡는 변이: **M8 (단독)**

**Given** `_make_qualifying_order()`로 만든 대상 주문 3건(J, K, L), K만 `_sync_single_order`에서 예외를 던지도록 모킹

**When** `resync_order_sweep`을 실행한다

**Then** J와 L은 정상 처리되고(각각의 `last_resynced_at` 갱신 + 성공 카운트 반영), K는 실패로 기록된다 — 3건 모두 처리 시도가 있었다(`_sync_single_order` 또는 그 앞 단계가 3건 전부에 대해 호출됨). (이 AC는 의도적으로 부분 실패 시나리오를 검증하므로 §0.1의 "0건 실패" 증거는 적용되지 않는다 — 대신 "실패 목록이 정확히 {K}"임을 직접 단정하는 것이 이 AC 고유의 성공/실패 구분 증거다)

**판별력**: K의 예외가 루프 전체를 중단시키는 변이는 L이 아예 처리되지 않아(호출 자체가 없음) 즉시 잡힌다.

---

## AC-RSW-011 — 실패한 주문이 있으면 커맨드가 0이 아닌 종료코드로 끝난다

Traces: REQ-RSW-007, REQ-RSW-012
잡는 변이: **M9 (양성, AC-012와 공동)**

**Given** `_make_qualifying_order()`로 만든 대상 주문 2건, 그중 1건이 실패하도록 모킹

**When** `call_command("resync_order_sweep")`을 실행한다

**Then** `CommandError`가 발생한다(`pytest.raises(CommandError)`)

**판별력**: 실패를 집계만 하고 마지막에 `raise CommandError`를 하지 않는 변이(M9)는 예외 없이 정상 반환되어 잡힌다.

---

## AC-RSW-012 — 실패가 전혀 없으면 커맨드가 정상 종료(예외 없음)한다

Traces: REQ-RSW-007, REQ-RSW-012
잡는 변이: **M9 (음성, AC-011과 공동)**

**Given** `_make_qualifying_order()`로 만든 대상 주문 2건, 둘 다 성공하도록 모킹

**When** `call_command("resync_order_sweep")`을 실행한다

**Then** 예외 없이 정상 반환되고(= 실패 0건, 성공 증거), 두 주문 모두 `last_resynced_at`이 갱신되어 있다

**판별력**: 모든 경우에 무조건 `CommandError`를 던지는 변이는 이 AC에서 예상치 못한 예외로 잡힌다.

---

## Fulfillment Location 갱신 (gap 1)

## AC-RSW-013 — [핵심, v0.3.0 성공 증거 추가, 감사 N4] 스위프 실행 전후 StoreSyncWatermark가 불변이다

Traces: REQ-RSW-016
잡는 변이: **M10 (단독)**

**Given** `StoreSyncWatermark(store_type="gimssine", last_synced_updated_at=T1, last_run_at=T2)`, `_make_qualifying_order()`로 만든 대상 주문 1건(성공 모킹)

**When** `resync_order_sweep`을 실행한다

**Then** `StoreSyncWatermark`를 다시 조회했을 때 `last_synced_updated_at == T1`이고 `last_run_at == T2`(둘 다 무변경), **그리고 이 실행이 `CommandError` 없이 종료했다(실패 0건 — 성공 증거, N4)**

**판별력**: 스위프 코드가 실수로 `sync_store()`의 워터마크 전진 로직을 복사해 오는 변이(M10)는 T1/T2 중 하나 이상이 달라져 즉시 잡힌다.

---

## AC-RSW-014 — [핵심, v0.3.0 성공 증거 추가, 감사 N4] 기존 주문의 위치가 스위프로 갱신된다(단축 경로 미적용, 정상 경로)

Traces: REQ-RSW-013
잡는 변이: **M11 (단독)**

**Given** `_make_qualifying_order()`로 만든 대상 주문, 로컬 `Order.location="NJ"`. Shopify `fulfillment_orders.json` 응답을 모킹해 위치가 `"CA"`로 바뀌어 있음을 반환(정상 성공 경로)

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후 `Order.location == "CA"`(및 해당 LineItem들의 `location`도 갱신), **그리고 이 실행이 `CommandError` 없이 종료했다(실패 0건 — 성공 증거, N4: `Order.location`이 실제로 `"CA"`로 바뀌었다는 사실 자체가 이미 성공 없이는 불가능하므로 이중 증거)**

**판별력**: `sync_store()`의 "기존 주문이면 저장된 위치 재사용, API 호출 생략" 최적화(`shopify_orders.py:420-428`)를 스위프 코드에 실수로 이식한 변이(M11)는 `Order.location`이 여전히 `"NJ"`로 남아 즉시 잡힌다.

---

## AC-RSW-014b — [핵심] fulfillment 조회가 예외로 실패하면 위치가 지워지지 않고 그 주문은 실패로 기록된다

Traces: REQ-RSW-030
잡는 변이: **M21 (단독)**

**Given** `_make_qualifying_order()`로 만든 대상 주문, 로컬 `Order.location="NJ"`, 로컬 `LineItem.location="NJ"`. `_build_fulfillment_location_data`(또는 그 하위의 `_get_with_headers`)가 예외(예: `urllib.error.URLError`)를 던지도록 모킹

**When** `resync_order_sweep`을 실행한다(전체 사이클은 실패로 끝나도 무방 — 이 AC는 실패 경로 자체를 검증하므로 §0.1 예외)

**Then** 스위프 후에도 `Order.location == "NJ"`(무변경, 빈 문자열로 지워지지 않음)이고 `LineItem.location == "NJ"`(무변경)이며, 그 주문은 실패 목록에 포함된다(`CommandError` 발생 또는 실패 카운트 1) — 단, `last_resynced_at`은 그래도 전진한다(D1과의 상호작용, AC-RSW-009와 동일 메커니즘)

**판별력**: `_build_fulfillment_location_data`의 기존 계약(모든 예외를 삼키고 `("", {})` 반환)을 스위프가 그대로 사용하는 변이(`raise_on_error=True`를 전달하지 않거나 그 파라미터 자체를 구현하지 않음, M21)는 `location_code=""`가 `_sync_single_order()`에 전달되어 `Order.location`이 `""`로 덮어써지고, 예외가 밖으로 나오지 않으므로 그 주문이 성공으로 기록된다 — `"" ≠ "NJ"` 및 "실패 목록에 없음"이 이 변이를 즉시 잡는다.

---

## AC-RSW-030 — [핵심, v0.3.0 신규, 감사 N2] fulfillment 조회가 예외 없이 정상적으로 빈 값을 반환하면 위치가 보존되고 그 주문은 성공으로 집계된다

Traces: REQ-RSW-030
잡는 변이: **M24 (단독)**

**[신설 사유]** AC-RSW-014b는 `_build_fulfillment_location_data()`의 **예외** 경로만 검증한다. 그러나 이 함수는 예외 없이도 정상적으로 빈 값을 반환한다 — Shopify가 반환한 `assigned_location.name`에 언더스코어가 없거나(`shopify_orders.py:88-89`) `fulfillment_orders`가 빈 배열인 경우이며, `test_order_location.py:62-76`이 이 정상 동작을 고정한다. `raise_on_error`는 예외가 없으므로 이 경로에서 아무것도 하지 않는다 — 별도 검증이 필요하다.

**Given** `_make_qualifying_order()`로 만든 대상 주문, 로컬 `Order.location="NJ"`, 로컬 `LineItem.location="NJ"`. `_build_fulfillment_location_data`가 예외 없이 `("", {})`를 반환하도록 모킹(정상 응답이지만 위치 정보를 낼 수 없는 경우를 흉내 — 예외가 아님)

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후에도 `Order.location == "NJ"`(무변경, 빈 문자열로 지워지지 않음)이고 `LineItem.location == "NJ"`(무변경)이며, 그 주문은 실패 목록에 **없다**(`CommandError` 미발생 — 성공 증거, AC-RSW-014b와 반대) — `last_resynced_at`도 갱신되어 있다

**판별력**: 새로 조회한 값이 비어도 무조건 `_sync_single_order()`에 그대로 전달하는 변이(값-병합 로직 누락, M24)는 `Order.location`이 `""`로 덮어써져 `"" ≠ "NJ"`로 즉시 잡힌다. 이 AC는 AC-RSW-014b와 짝을 이루며 서로 다른 방향에서 서로 다른 트리거(예외 vs 정상-빈값)를 잡는다 — 두 AC 모두 없으면 REQ-RSW-030의 두 하위 절 중 하나가 미커버로 남는다.

---

## Close/Cancel 감지 (gap 2)

## AC-RSW-015 — Shopify에서 closed_at이 채워진 주문을 스위프하면 로컬도 반영된다

Traces: REQ-RSW-015
잡는 변이: **M12 (closed, AC-016과 공동)**

**Given** `_make_qualifying_order()`로 만든 대상 주문, 로컬 `Order.closed_at=None`, Shopify `orders/{id}.json` 응답 모킹에 `"closed_at": "2026-08-01T00:00:00Z"` 포함

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후 `Order.closed_at`이 그 값으로 채워져 있고(이 사실 자체가 성공 없이는 불가능하므로 성공 증거), `last_resynced_at`도 갱신되어 있다

**판별력**: 스위프가 `status=open` 목록 피드를 재사용하는 변이(M12)는 이 주문의 최신 페이로드를 가져오지 못해 `closed_at`이 계속 `None`으로 남아 잡힌다.

---

## AC-RSW-016 — Shopify에서 cancelled_at이 채워진 주문을 스위프하면 로컬도 반영된다

Traces: REQ-RSW-015
잡는 변이: **M12 (cancelled, AC-015와 공동)**

**Given** `_make_qualifying_order()`로 만든 대상 주문, 로컬 `Order.cancelled_at=None`, Shopify 응답 모킹에 `"cancelled_at": "2026-08-05T00:00:00Z"` 포함

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후 `Order.cancelled_at`이 그 값으로 채워져 있고(성공 증거), `last_resynced_at`도 갱신되어 있다

**판별력**: AC-015와 동일한 메커니즘, 별도 필드로 독립 검증.

---

## 매뉴얼 상태/보정 불변식 보존

## AC-RSW-017 — [v0.3.0 성공 증거 추가, 감사 N4] 수동 지정된 purchase_status가 스위프로 되돌아가지 않는다

Traces: REQ-RSW-018
잡는 변이: **M13**

**Given** `_make_qualifying_order(purchase_status="cs_required")`로 만든 주문(REQ-RSW-003을 만족하도록 `logistics_status="not_shipped"`는 그대로 유지 — `purchase_status`와 `logistics_status`는 독립 필드다), Shopify 응답은 `title`을 새 값(`"Updated Title"`)으로 변경해 포함(이 필드와 무관한 실제 변경 — 성공 증거로 쓰기 위해 구체화)

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후에도 `purchase_status == "cs_required"`(무변경)이고, `LineItem.title == "Updated Title"`(Shopify가 실제로 바꾼 값이 반영됨 — **성공 증거**, N4), 그리고 이 실행이 `CommandError` 없이 종료했다(실패 0건)

**판별력**: 스위프 전용 쓰기 경로를 새로 만들면서 `purchase_status`를 실수로 `defaults`에 포함시킨 변이(M13)는 Shopify 기본값(`unordered`)으로 되돌려 즉시 잡힌다. **[v0.3.0 정정, N4]** 이전 버전은 `last_resynced_at` 전진만으로 "처리됨"을 증명했으나, 그 필드는 실패 시에도 전진하므로(D1) 이 주문 전체를 실패시키는 변이 앞에서 "무변경" 단정이 공허하게 통과할 수 있었다 — `title`이 실제로 갱신되었다는 단정과 `CommandError` 부재 단정을 추가해 이 결함을 막는다.

---

## AC-RSW-018 — [v0.3.0 성공 증거 추가 + 판별력 재작성, 감사 N4/N4b] 수동 지정된 logistics_status가 스위프로 되돌아가지 않는다

Traces: REQ-RSW-018
잡는 변이: **M13**

**Given** `_make_qualifying_order(logistics_status="not_shipped")`로 만든 주문에 대해, Shopify 응답이 `title`을 새 값(`"Updated Title"`)으로 변경해 포함하도록 모킹

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후에도 `logistics_status == "not_shipped"`(무변경)이고, `LineItem.title == "Updated Title"`(성공 증거), 그리고 이 실행이 `CommandError` 없이 종료했다(실패 0건)

**판별력**: **[v0.3.0 전면 재작성, 감사 N4b — 이전 버전의 판별력 문단은 자기모순이었다]** 이전 버전은 "`update_or_create`가 기존 값을 그대로 두는지"를 판별력으로 주장했으나, `logistics_status`가 실수로 `defaults`에 포함되는 변이에서 `li.get("logistics_status")`가 Shopify 응답에 없어 `None`이 되고, `LineItem.logistics_status`는 `CharField(choices=..., default="not_shipped")`로 non-nullable이므로(`models.py:204-208`, `null=True` 없음) 이 쓰기는 `IntegrityError`를 던진다 — per-order 트랜잭션이 롤백되어 `logistics_status`는 원래 값을 유지한 채(변경이 아예 커밋되지 않았으므로), "무변경" 단정만으로는 **오히려 통과**했다(자기모순). 이번 버전은 `CommandError` 부재(= 실패 0건) 단정을 추가했다 — `IntegrityError`로 롤백된 주문은 `except`에 걸려 실패로 집계되므로 `CommandError`가 발생하고, 이 AC의 "실패 0건" 단정이 실패해 변이가 잡힌다. `title` 반영 단정도 같은 이유로 유효하다(롤백되면 `title`도 갱신되지 않는다).

---

## AC-RSW-019 — [v0.3.0 성공 증거 추가, 감사 N4] original_sku 보정(비번들)이 스위프로 되돌아가지 않는다

Traces: REQ-RSW-019
잡는 변이: **M14 (비번들)**

**Given** `_make_qualifying_order()`로 만든 주문의 LineItem이 발주처리 시점에 수동 보정되어 `sku`가 `"ISBN-A-NEW-EDITION"`, `original_sku`가 `"ISBN-A"`로 채워진 상태(SPEC-ORDER-025 패턴), `logistics_status="not_shipped"`는 유지, Shopify가 여전히 원래(보정 전) sku `"ISBN-A"`를 보고하되 `title`은 새 값(`"Updated Title"`)으로 변경해 포함

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후에도 `sku == "ISBN-A-NEW-EDITION"`(원래 값으로 되돌아가지 않음)이고, `title == "Updated Title"`(성공 증거), 그리고 이 실행이 `CommandError` 없이 종료했다(실패 0건)

**판별력**: 스위프가 `protected_sku_by_key` 조회(`shopify_orders.py:209-224`)를 생략한 별도 경로를 쓰는 변이(M14)는 `sku`가 Shopify 원본 값 `"ISBN-A"`로 되돌아가 즉시 잡힌다.

---

## AC-RSW-020 — [v0.3.0 성공 증거 추가, 감사 N4] original_sku 보정(번들)이 스위프로 되돌아가지 않는다

Traces: REQ-RSW-019
잡는 변이: **M14 (번들)**

**Given** `_make_qualifying_order()`로 만든 주문의 번들 SKU 라인아이템 멤버 행 중 하나(`logistics_status="not_shipped"`)가 수동 보정된 상태, Shopify가 여전히 원래 member_isbn을 보고하되 그 라인아이템의 `price`는 새 값으로 변경해 포함

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후에도 그 멤버 행의 보정된 `sku`가 유지되고, `price`는 새 값으로 갱신되어 있으며(성공 증거), 이 실행이 `CommandError` 없이 종료했다(실패 0건)

**판별력**: AC-019와 동일한 메커니즘, 번들 분기(`:256-270`)를 독립적으로 검증.

---

## 환불/배송라인 MySQL 호환 차등 갱신

## AC-RSW-021 — [핵심, v0.3.0 성공 증거 추가, 감사 N4] 기존 환불 행(line_item_id 존재)이 다음 페이로드에도 존재하면 데이터가 유실되지 않는다

Traces: REQ-RSW-025, REQ-RSW-026
잡는 변이: **M15 (단독)**

**Given** `_make_qualifying_order()`로 만든 주문의 LineItem에 이미 저장된 `Refund(shopify_refund_id=900001, line_item_id=X, quantity=2, subtotal=10.00)`(`line_item_id`는 non-null), 다음 스위프의 Shopify 응답에도 동일한 환불이 동일한 값으로 포함되고 `LineItem.title`이 새 값으로 변경되어 포함됨

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후 그 `Refund` 행이 여전히 존재하며 `quantity==2`, `subtotal==10.00`(유실되지 않음), `Refund.objects.filter(...).count()`가 여전히 1(중복 생성 없음), `LineItem.title`이 새 값으로 갱신되어 있으며(성공 증거), 이 실행이 `CommandError` 없이 종료했다(실패 0건)

**판별력**: `bulk_create(update_conflicts=True, unique_fields=[...])` 형태를 그대로 쓰는 변이(M15, D1)는 MySQL에서 `NotSupportedError`를 던져 커맨드 자체가 예외로 실패한다 — `CommandError` 부재 단정이 즉시 이를 잡는다. **[v0.3.0, N4]** 이 AC는 순수 보존형("환불 행이 여전히 존재")이라 실패 시에도 데이터가 손상되지 않은 채 남아 공허하게 통과할 수 있었다 — `title` 갱신과 `CommandError` 부재 단정이 이를 막는다.

---

## AC-RSW-022 — [v0.3.0 성공 증거 추가, 감사 N4] Shopify가 더 이상 보고하지 않는 환불 행(non-null)은 차등 삭제된다

Traces: REQ-RSW-025
잡는 변이: **M16 (환불)**

**Given** `_make_qualifying_order()`로 만든 주문의 LineItem에 저장된 `Refund(shopify_refund_id=900002, line_item_id=Y, ...)`(non-null), 다음 스위프의 Shopify 응답에는 이 환불이 더 이상 포함되지 않음

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후 그 `Refund` 행이 삭제되어 있고(이 사실 자체가 성공 없이는 불가능하므로 성공 증거), 이 실행이 `CommandError` 없이 종료했다(실패 0건)

**판별력**: 삭제 로직 자체를 제거하는 변이(M16)는 그 행이 그대로 남아 있어 즉시 잡힌다.

---

## AC-RSW-023 — [v0.3.0 성공 증거 추가, 감사 N4] 배송라인도 동일한 차등 갱신 규약을 따른다(기존 행 갱신, 중복 없음)

Traces: REQ-RSW-024, REQ-RSW-026
잡는 변이: **M16 (배송라인)**

**Given** `_make_qualifying_order()`로 만든 주문에 저장된 `ShippingLine(shopify_shipping_line_id=500001, price=5.00)`, 다음 스위프의 Shopify 응답에 동일 ID의 가격이 `7.50`으로 변경되어 포함됨

**When** `resync_order_sweep`을 실행한다(**2회 연속** 실행해 멱등성도 함께 확인)

**Then** 스위프 후 그 `ShippingLine`의 `price==7.50`(갱신됨, 성공 증거)이고, `ShippingLine.objects.filter(shopify_shipping_line_id=500001).count()==1`(중복 행 없음, 2회 실행 후에도 동일), 두 실행 모두 `CommandError` 없이 종료했다(실패 0건)

**판별력**: `unique_fields`를 지정한 변이는 MySQL에서 `NotSupportedError`로 실패한다 — `CommandError` 부재 단정이 즉시 잡는다. `update_conflicts`를 아예 빠뜨린 변이는 두 번째 실행에서 `IntegrityError`(unique 위반)나 중복 행(`count()==2`)으로 잡힌다.

---

## AC-RSW-024 — [핵심, v0.3.0 성공 증거 추가, 감사 N4/N16] 대상 3건 처리 시 ShopifySkuSetMapping 조회가 정확히 1회만 실행된다

Traces: REQ-RSW-021, REQ-RSW-023
잡는 변이: **M17 (단독)**

**Given** `_make_qualifying_order()`로 만든 대상 주문 3건. **HTTP 계층(`_get_with_headers`, `_build_fulfillment_location_data`)만 모킹하고, `_sync_single_order`는 모킹하지 않는다 — 실물 함수가 실제로 실행되어야 이 AC가 M17을 판별할 수 있다**(`_sync_single_order` 자체를 모킹하면 그 함수 내부의 `ShopifySkuSetMapping` 조회가 아예 실행되지 않아, 호이스팅 누락 변이가 "0회 대 0회"로 위장 통과한다). `django.test.utils.CaptureQueriesContext`로 `order_shopify_sku_set_mapping` 테이블(`models.py:556`)을 포함하는 쿼리만 카운트한다

**When** `resync_order_sweep`을 실행한다

**Then** `ShopifySkuSetMapping`에 대한 SELECT 쿼리가 정확히 1회만 실행되고(3회가 아님), 이 실행이 `CommandError` 없이 종료했다(3건 모두 성공 — 성공 증거)

**판별력**: `_load_batch_invariant_context()`를 루프 밖에서 호출하지 않고 `_sync_single_order()` 호출마다 `bundle_map=None`으로 넘기는 변이(M17)는 주문마다 내부에서 재계산해 쿼리가 3회 실행되어 `1 ≠ 3`으로 즉시 잡힌다.

---

## AC-RSW-025 — [핵심] 기존 단건 재동기화(sync_single_order_from_shopify)가 리팩터 이후에도 회귀 없이 동작한다

Traces: REQ-RSW-021, REQ-RSW-022
잡는 변이: **M18 (단독)**

**Given** `test_order_resync.py`의 기존 테스트 스위트(무수정)

**When** `_sync_single_order()`의 시그니처가 확장되고 환불/배송라인 쓰기 방식이 변경된 이후 그 스위트를 재실행한다

**Then** 기존 테스트 전부가 무수정으로 통과한다

**판별력**: 시그니처 확장 시 `bundle_map`/`title_map`의 기본값을 `None`이 아닌 다른 값으로 잘못 설정한 변이(M18)는 `sync_single_order_from_shopify()` 호출 시 항상 빈 컨텍스트를 쓰게 되어 번들 SKU가 포함된 기존 테스트 픽스처에서 회귀가 발생한다. 환불/배송라인 리팩터가 header-only 처리를 빠뜨리는 변이는 `test_shopify_orders.py:765`에서도 함께 잡힌다(별도 회귀 확인). (이 AC는 `resync_order_sweep`을 실행하지 않으므로 §0.1의 "성공 증거" 규약이 적용되지 않는다 — 기존 테스트 스위트의 통과 자체가 이미 명확한 증거다.)

---

## API 호출 페이싱

## AC-RSW-026 — [핵심, v0.3.0 성공 증거 추가, 감사 N4] Shopify API 호출 사이에 정확히 0.3초 페이싱이 계산·적용된다

Traces: REQ-RSW-014
잡는 변이: **M19 (단독)**

**[재설계 사유]** 이전 버전은 "훅이 최소 2회 이상 호출됨"만 확인해, 호출률을 2배로 늘리거나(주문당 1회만 페이싱) 간격 상수를 줄이는 변이(예: 0.05초)가 훅 호출 횟수 자체는 그대로라 통과했다. 이 버전은 **계산된 대기값**을 직접 단정한다.

**Given** 대상 주문 3건(모두 성공 모킹), `time.monotonic`을 고정값(항상 동일한 값 반환 — "경과 시간 0" 시뮬레이션)으로 모킹, `time.sleep` 호출을 기록하는 스파이

**When** `resync_order_sweep`을 실행한다

**Then** `time.sleep`이 정확히 **5회** 호출되고(주문 3건 × Shopify 호출 2회 = 6회의 페이싱 지점 중, 맨 처음 호출은 `last_call_at`이 없어 sleep하지 않으므로 5회), 매 호출의 인자가 정확히 **0.3**이며(경과 시간을 0으로 고정했으므로 `0.3 - 0 = 0.3`), 이 실행이 `CommandError` 없이 종료했다(3건 모두 성공 모킹이므로 성공 증거)

**판별력**: 페이싱 로직을 통째로 제거한 변이는 `time.sleep`이 전혀 호출되지 않아 잡힌다. 주문당 1회만 페이싱하는 변이(호출률 2배)는 `time.sleep` 호출 횟수가 5가 아닌 2가 되어 잡힌다. 간격 상수를 0.05초로 줄인 변이는 인자값이 0.3이 아닌 0.05가 되어 잡힌다.

---

## AC-RSW-029 — [핵심] header-only(line_item_id NULL) 환불 행은 반복 스위프에도 중복 생성되지 않는다(깨끗한 초기 상태)

Traces: REQ-RSW-025, REQ-RSW-026, REQ-RSW-029
잡는 변이: **M20 (단독)**

**Given** `_make_qualifying_order()`로 만든 주문의 Shopify 응답에 `line_item_id`가 없는 순수 배송/금액 환불(header-only, `refund_line_items: []`) 1건 포함(초기 로컬 상태에는 아직 이 환불 행이 없음 — "깨끗한" 시작)

**When** `resync_order_sweep`을 **동일 페이로드로 2회 연속** 실행한다

**Then** 두 번의 실행 후에도 `Refund.objects.filter(order=..., shopify_refund_id=<그 값>, line_item_id__isnull=True).count() == 1`(1회 실행 후에도, 2회 실행 후에도 정확히 1)이고, 두 실행 모두 `CommandError` 없이 종료했다(실패 0건 — 성공 증거)

**판별력**: header-only 행을 `unique_fields` 없는 bulk upsert 경로에 그대로 섞는 변이(M20, D2)는 SQL 표준의 NULL≠NULL 유니크 판별 규칙 때문에 매 실행마다 새 행을 INSERT한다 — 2회 실행 후 `count() == 2`가 되어 `1 ≠ 2`로 즉시 잡힌다. **이 AC는 "깨끗한 초기 상태"만 다룬다 — 선존 중복 상태는 AC-RSW-029b가 별도로 다룬다(v0.3.0, N3).**

---

## AC-RSW-029b — [핵심, v0.3.0 신규, 감사 N3] 선존 중복 header-only 환불 행은 자가치유되어 그 주문이 영구 실패하지 않는다

Traces: REQ-RSW-029
잡는 변이: **M23 (단독)**

**[신설 사유]** `Refund.line_item_id`는 유니크 제약이 사실상 걸리지 않으므로(가정 A8, NULL≠NULL) 이력 데이터나 `sync_store()`와의 동시 실행 경합(§8 C8)으로 동일 (주문, `shopify_refund_id`, NULL) 조합의 행이 **이미** 2건 이상 존재하는 상태가 가능하다. AC-RSW-029는 "깨끗한" 시작만 다뤄 이 시나리오를 놓친다.

**Given** `_make_qualifying_order()`로 만든 주문의 LineItem에 **이미** `(order, shopify_refund_id=900003, line_item_id=NULL)` 조합의 `Refund` 행이 **2건** 존재(선존 중복 — 이력 데이터 또는 동시 실행 경합을 흉내낸 픽스처). Shopify 응답에도 동일 `shopify_refund_id=900003`의 header-only 환불이 포함됨

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후 `Refund.objects.filter(order=..., shopify_refund_id=900003, line_item_id__isnull=True).count() == 1`(2건에서 1건으로 자가치유됨)이고, 그 주문은 실패 목록에 **없으며**(`CommandError` 미발생 — 성공 증거), `last_resynced_at`이 갱신되어 있다

**판별력**: upsert 전 중복 정리 단계를 생략한 변이(M23)는 `update_or_create` 내부의 `.get()`이 2건과 매치되어 `django.core.exceptions.MultipleObjectsReturned`를 던진다 — 그 주문이 예외로 실패하고 `CommandError`가 발생해 "실패 목록에 없음" 단정이 즉시 실패한다. 이 변이는 이 SPEC이 놓치면 프로덕션에서 특정 주문을 **영구적으로** 재동기화 불가능하게 만드는 심각한 결함이므로, 이 AC는 다른 단독 판별자들과 동급으로 보호된다.

---

## 부분 입고 대상 포함 및 보존

## AC-RSW-033 — 부분 입고된 라인아이템을 가진 주문도 대상에 포함된다

Traces: REQ-RSW-033
잡는 변이: 없음(정보성 확정 — 회귀 방지 목적)

**Given** `_make_qualifying_order()`로 만든 주문의 LineItem이 `quantity=5`, `received_quantity=2`(부분 입고, 0보다 크지만 quantity 미달), `logistics_status="not_shipped"`(부분 입고는 상태를 전환하지 않음, `purchase_order_views.py:2549-2550`)

**When** `_qualifying_orders_queryset()`을 평가한다

**Then** 결과 집합에 이 주문이 포함된다

**목적**: 이 AC는 부분 입고 주문이 대상 판정에서 실수로 배제되지 않는다는 사실을 영구적인 회귀 방지 테스트로 고정한다. 누군가 향후 "부분 입고는 스위프 대상에서 빼야 하지 않나"라는 직관으로 `logistics_status="not_shipped"` 조건에 `received_quantity=0`을 추가하는 변경을 시도하면 이 AC가 실패해 즉시 드러난다. (이 AC는 `_qualifying_orders_queryset()`만 평가하고 `resync_order_sweep`을 실행하지 않으므로 §0.1의 "성공 증거" 규약이 적용되지 않는다.)

---

## AC-RSW-034 — [핵심, v0.3.0 성공 증거 추가, 감사 N4] 스위프가 갱신하는 LineItem의 비-Shopify 소스 필드가 보존된다

Traces: REQ-RSW-034
잡는 변이: **M22 (단독)**

**Given** `_make_qualifying_order()`로 만든 주문의 LineItem이 `received_quantity=2`, `received_at`=특정 시각, `shipped_quantity=1`, `rack_number="A-3"`, `damaged_quantity=0`, `confirmed_price=Decimal("9.99")`, `confirmed_distributor="booxen"`을 가짐(모두 Shopify 동기화 `defaults`에 없는 필드). Shopify 응답은 이 라인아이템을 여전히 보고하되(그래서 stale-삭제 대상이 아님), `title`을 새 값(`"Updated Title"`)으로 변경해 포함

**When** `resync_order_sweep`을 실행한다

**Then** 스위프 후 위 필드 전부(`received_quantity`, `received_at`, `shipped_quantity`, `rack_number`, `damaged_quantity`, `confirmed_price`, `confirmed_distributor`)가 정확히 이전 값으로 유지되고, `title == "Updated Title"`(성공 증거), 이 실행이 `CommandError` 없이 종료했다(실패 0건), `last_resynced_at`은 갱신되어 있다

**판별력**: `_sync_single_order()`의 `common_defaults` 딕셔너리(`shopify_orders.py:231-243`)에 이 필드 중 하나라도 실수로 추가되는 변이(M22)는 Shopify가 그 필드를 아예 보고하지 않으므로(Shopify API 응답에 없는 개념) `update_or_create`가 그 값을 `None`/기본값으로 덮어써 즉시 잡힌다. **[v0.3.0, N4]** 이 AC도 순수 보존형이라 전면 실패 시나리오에서 공허하게 통과할 수 있었다 — `title` 갱신 및 `CommandError` 부재 단정을 추가했다.

---

## 추적표 (AC → 변이)

| AC | 범위 | 성격 | 잡는 변이 |
|----|------|------|-----------|
| AC-RSW-001 | BE | 대상 판정 양성 | M2(001+002, 공동) |
| AC-RSW-002 | BE | 대상 판정 음성 | M2(001+002, 공동) |
| AC-RSW-003 | BE | 연령 상한 음성(30일, v0.4.0) | M1(003+004, 경계 쌍) |
| AC-RSW-004 | BE | 연령 상한 경계 양성(30일, v0.4.0) | M1(003+004, 경계 쌍) |
| AC-RSW-005 | BE | fanout 방지 | **M3 (단독)** |
| AC-RSW-006 | BE | 라운드로빈 순서(v0.3.0 재보강) | **M4 (단독)** |
| AC-RSW-007 | BE | N 상한 적용(명시적 `--count`) | **M5 (단독)** |
| AC-RSW-007b | BE | N 기본값 40(v0.3.0 신규) | **M25 (단독)** |
| AC-RSW-035 | BE | 연령 상한 적용(명시적 `--days`, v0.4.0 신규) | **M26 (단독)** |
| AC-RSW-035b | BE | 연령 상한 기본값 30(커맨드 경로, v0.4.0 신규) | **M27 (단독)** |
| AC-RSW-008 | BE | last_resynced_at 갱신(성공) | M6 |
| AC-RSW-009 | BE | last_resynced_at 갱신(실패) | **M7 (단독)** |
| AC-RSW-010 | BE | per-order 격리 | **M8 (단독)** |
| AC-RSW-011 | BE | 종료코드(실패 있음) | M9(011+012, 공동) |
| AC-RSW-012 | BE | 종료코드(실패 없음) | M9(011+012, 공동) |
| AC-RSW-013 | BE | 워터마크 불변(v0.3.0 성공 증거) | **M10 (단독)** |
| AC-RSW-014 | BE | 위치 갱신(정상 경로, v0.3.0 성공 증거) | **M11 (단독)** |
| AC-RSW-014b | BE | 위치 갱신(예외 경로) | **M21 (단독)** |
| AC-RSW-030 | BE | 위치 갱신(정상-빈값 경로, v0.3.0 신규) | **M24 (단독)** |
| AC-RSW-015 | BE | closed_at 반영 | M12(015+016, 공동) |
| AC-RSW-016 | BE | cancelled_at 반영 | M12(015+016, 공동) |
| AC-RSW-017 | BE | purchase_status 보호(v0.3.0 성공 증거) | M13 |
| AC-RSW-018 | BE | logistics_status 보호(v0.3.0 성공 증거+판별력 재작성) | M13 |
| AC-RSW-019 | BE | original_sku 보호(비번들, v0.3.0 성공 증거) | M14 |
| AC-RSW-020 | BE | original_sku 보호(번들, v0.3.0 성공 증거) | M14 |
| AC-RSW-021 | BE | 환불 데이터 무유실(non-null, v0.3.0 성공 증거) | **M15 (단독)** |
| AC-RSW-022 | BE | 환불 stale 삭제(non-null, v0.3.0 성공 증거) | M16 |
| AC-RSW-023 | BE | 배송라인 차등 갱신(v0.3.0 성공 증거) | M16 |
| AC-RSW-024 | BE | 배치 불변 컨텍스트(v0.3.0 성공 증거) | **M17 (단독)** |
| AC-RSW-025 | BE | 단건 호출부 회귀 없음 | **M18 (단독)** |
| AC-RSW-026 | BE | API 페이싱(v0.3.0 성공 증거) | **M19 (단독)** |
| AC-RSW-029 | BE | header-only 환불 무한증식 방지(깨끗한 초기 상태) | **M20 (단독)** |
| AC-RSW-029b | BE | header-only 환불 선존 중복 자가치유(v0.3.0 신규) | **M23 (단독)** |
| AC-RSW-033 | BE | 부분 입고 대상 포함(정보성) | 없음(회귀 확인) |
| AC-RSW-034 | BE | 비-Shopify 필드 보존(v0.3.0 성공 증거) | **M22 (단독)** |

**변이 커버리지 확인**: M1(003+004) M2(001+002) **M3(005 단독)** **M4(006 단독)** **M5(007 단독)** M6(008) **M7(009 단독)** **M8(010 단독)** M9(011+012) **M10(013 단독)** **M11(014 단독)** **M21(014b 단독)** **M24(030 단독, v0.3.0)** M12(015+016) M13(017+018) M14(019+020) **M15(021 단독)** M16(022+023) **M17(024 단독)** **M18(025 단독)** **M19(026 단독)** **M20(029 단독)** **M23(029b 단독, v0.3.0)** **M22(034 단독)** **M25(007b 단독, v0.3.0)** **M26(035 단독, v0.4.0)** **M27(035b 단독, v0.4.0)** — 27개 변이 전부 최소 1개 AC가 잡으며, 그중 19건은 진짜 단독 판별자다.

---

## 엣지 케이스 요약

| # | 케이스 | 대응 AC |
|---|--------|---------|
| 1 | 다중 상태 라인아이템 혼재 주문(1개 not_shipped + 나머지 shipped)의 포함 여부 | AC-RSW-001 |
| 2 | 전량 shipped 주문의 제외 | AC-RSW-002 |
| 3 | 연령 상한 경계(31일 제외 / 29일 포함, 기본값 30일, v0.4.0) | AC-RSW-003, AC-RSW-004 |
| 4 | 다중 not_shipped 라인아이템 주문의 중복 방지 | AC-RSW-005 |
| 5 | 라운드로빈 순서(NULL/오래된 것 우선, 생성 순서와 기대 순서 불일치) | AC-RSW-006 |
| 6 | N(--count) 상한, 명시적 지정 | AC-RSW-007 |
| 7 | N(--count) 기본값 40, 생략 시 | AC-RSW-007b |
| 7b | D(--days) 명시적 지정이 대상 판정에 반영됨(v0.4.0 신규) | AC-RSW-035 |
| 7c | D(--days) 기본값 30, 생략 시 커맨드 경로 전체 적용(v0.4.0 신규) | AC-RSW-035b |
| 8 | 무변경 성공 시 갱신 | AC-RSW-008 |
| 9 | 실패 시에도 갱신(poison order) | AC-RSW-009 |
| 10 | per-order 격리(1건 실패, 나머지 계속) | AC-RSW-010 |
| 11 | 종료코드(실패 있음/없음) | AC-RSW-011, AC-RSW-012 |
| 12 | 워터마크 불변 | AC-RSW-013 |
| 13 | 위치 갱신(정상 경로) | AC-RSW-014 |
| 14 | 위치 갱신(예외 경로, 조용한 소거 방지) | AC-RSW-014b |
| 15 | 위치 갱신(정상-빈값 경로, 조용한 소거 방지) | AC-RSW-030 |
| 16 | closed_at/cancelled_at 반영 | AC-RSW-015, AC-RSW-016 |
| 17 | 매뉴얼 상태 보호(대상 조건 충족 + 성공 증거 픽스처) | AC-RSW-017, AC-RSW-018 |
| 18 | SKU 보정 보호(번들/비번들, 대상 조건 충족 + 성공 증거 픽스처) | AC-RSW-019, AC-RSW-020 |
| 19 | 환불 데이터 무유실(non-null) + stale 삭제 | AC-RSW-021, AC-RSW-022 |
| 20 | 배송라인 차등 갱신 | AC-RSW-023 |
| 21 | header-only 환불 무한증식 방지(깨끗한 초기 상태) | AC-RSW-029 |
| 22 | header-only 환불 선존 중복 자가치유 | AC-RSW-029b |
| 23 | 배치 불변 컨텍스트(실물 실행, 쿼리 1회) | AC-RSW-024 |
| 24 | 기존 단건 호출부 회귀 없음 | AC-RSW-025 |
| 25 | API 페이싱(계산값 단정) | AC-RSW-026 |
| 26 | 부분 입고 대상 포함 | AC-RSW-033 |
| 27 | 비-Shopify 필드(입고/랙/파손/확정) 보존 | AC-RSW-034 |

---

## Definition of Done

### 신규 검증
- [ ] AC-RSW-001 ~ AC-RSW-026, AC-RSW-007b, AC-RSW-014b, AC-RSW-029, AC-RSW-029b, AC-RSW-030, AC-RSW-033, AC-RSW-034, AC-RSW-035, AC-RSW-035b 전부 통과(35개, `backend/order/tests/test_spec_028.py`) — §0.2의 결번 4개(027/028/031/032)는 의도된 것임을 재확인. **[v0.5.0 정정, 감사 D6]** 이 열거는 원래 `AC-RSW-014b`가 빠진 채 34개를 나열하고 35개라 표기했다(review-3 D5(iii) 2회 연속 미해결) — 추가했다
- [ ] **RED 성립 확인**: 각 AC를 작성한 직후 무수정 코드에서 실행해 전부 실패함을 직접 확인한다
- [ ] 단독 판별 AC(005/006/007/007b/009/010/013/014/014b/021/024/025/026/029/029b/030/034/035/035b) 19건의 픽스처를 §추적표의 규약대로 유지한다(단순화·약화 금지)
- [ ] AC-001/002(M2), AC-003/004(M1), AC-011/012(M9), AC-015/016(M12), AC-022/023(M16) 각 쌍 모두 유지한다
- [ ] **[v0.3.0 신규, N4]** §0.1의 "성공 증거" [HARD] 규약이 실제로 지켜지는지 재확인한다 — 특히 AC-013/014/017~024/026/029/029b/030/034/035/035b가 `CommandError` 부재(또는 실제 반영된 값) 단정을 포함하는지 직접 대조(**[v0.5.0 추가, 감사 D4]** 035/035b를 이 목록에 편입 — 035는 신설 시점부터 포함, 035b는 v0.5.0에서 양성 대조군 주문 O에 성공 증거를 추가하며 이 규약을 충족)
- [ ] AC-RSW-006의 Given이 생성 순서(E→F→G)와 기대 처리 순서(G→F→E)를 의도적으로 불일치시키는 픽스처를 유지한다(N5 재발 방지)
- [ ] AC-RSW-029(header-only 환불, 깨끗한 상태)와 AC-RSW-029b(선존 중복)를 둘 다 유지한다 — 하나만으로는 header-only 환불의 두 시나리오(정상 반복 vs 선존 중복)를 모두 커버하지 못한다
- [ ] AC-RSW-014b(예외 경로)와 AC-RSW-030(정상-빈값 경로)을 둘 다 유지한다 — 하나만으로는 REQ-RSW-030의 두 하위 절을 모두 커버하지 못한다

### 회귀 검증
- [ ] `backend/order/tests/test_shopify_orders.py` 전부 **무수정** 통과 — 특히 `:765`(header-only 환불)와 `:665`(멱등성)를 주의 깊게 확인
- [ ] `backend/order/tests/test_order_resync.py` 전부 **무수정** 통과 — `:255-292`(번들 매핑 변경 후 고아 행 accepted-edge-case 테스트)가 이 SPEC 적용 후에도 정확히 동일한 결과를 내는지 특히 확인(REQ-RSW-031, 최초 전개·사후 변경 구분 없이 무변경이어야 함)
- [ ] `backend/order/tests/test_backfill_missing_orders_command.py` 전부 **무수정** 통과
- [ ] `backend/order/tests/test_sync_orders_command.py` 전부 **무수정** 통과
- [ ] `backend/order/tests/test_order_location.py` 전부 **무수정** 통과 — 예외 경로(`:79-88`)와 정상-빈값 경로(`:62-76`) 양쪽 모두 무변경 확인(N2)
- [ ] `git diff --stat backend/order/views.py` 공집합
- [ ] `git diff --stat backend/order/purchase_order_views.py` 공집합(`_process_warehouse_receipt_rows` 무변경)

### 코드 범위 검증
- [ ] `git diff backend/order/shopify_orders.py` — 변경이 `_sync_single_order()`의 시그니처/bundle_map·title_map 분기/refund·shipping_line MySQL 호환 차등 갱신 블록(header-only 자가치유 포함)/`_build_fulfillment_location_data()`의 `raise_on_error` 파라미터/신규 `_qualifying_orders_queryset()`에 국한된다. `sync_store()`, `fetch_all_open_orders()`의 본문, 번들 stale-삭제 로직(`:287-289`)은 무변경
- [ ] `git diff backend/order/management/commands/resync_order_sweep.py` — 위치 병합 로직(N2)이 이 파일에만 있고 `_sync_single_order()`/`_build_fulfillment_location_data()`의 시그니처를 추가로 변경하지 않았는지 확인
- [ ] `backend/order/migrations/` 신규 파일 정확히 **1건**(`0045_*.py`)
- [ ] `resync_order_sweep.py`에 `StoreSyncWatermark` import가 없다(REQ-RSW-016 코드 레벨 강제)
- [ ] `_sync_single_order()`의 refund/shipping-line 쓰기 블록에 `unique_fields=` 인자가 **없다**(D1 재발 방지, grep으로 확인)
- [ ] header-only 환불 upsert 직전에 중복 정리(`filter(...).order_by("pk")` + 초과분 삭제) 단계가 존재한다(N3 재발 방지, grep으로 확인)

### MySQL 특정 검증
- [ ] 로컬 pytest와 운영이 동일 MySQL RDS를 바라본다는 사실을 재확인(`backend/.env`)
- [ ] `EXPLAIN`으로 대상 판정 쿼리가 `order_last_resynced_at_idx`(복합 인덱스)를 사용하고 `Extra`에 `Using filesort`가 없는지 확인 — filesort가 나오면 `plan.md` §1.1의 대안을 검토하고 그 결과를 기록
- [ ] MySQL RDS에서 `bulk_create(update_conflicts=True)`(unique_fields 없이)가 최소 1건 실제로 `ON DUPLICATE KEY UPDATE`로 실행됨을 수동 확인
- [ ] MySQL RDS에서 header-only 환불 선존 중복(2건) → 스위프 1회 → 1건으로 수렴을 수동 확인(N3)

### 문서
- [ ] `spec.md` HISTORY에 구현 결과(통과 테스트 수, MySQL 수동 검증 결과, `EXPLAIN` 결과, mx_plan 실행 결과) 기록
- [ ] `.moai/project/scheduled-jobs.md` 갱신 여부(권고 사항) 기록
