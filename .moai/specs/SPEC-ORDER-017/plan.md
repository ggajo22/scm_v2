---
id: SPEC-ORDER-017
document: plan
version: 1.0.4
status: completed
updated: 2026-08-13
---

# 구현 계획 — SPEC-ORDER-017 렉번호 엑셀 업로드 배치 처리

`spec.md`의 요구사항(REQ-RACKBATCH-001~015)을 구현하기 위한 작업 분해, 파일별 변경
계획, 기술적 접근, 리스크와 완화책, MX 태그 계획을 정리한다. 근거 자료는 `research.md`
(파일:라인 인용 포함)를 참조한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며,
요구사항을 재진술하지 않고 REQ ID로 참조한다.

v1.0.1 변경(plan-auditor iteration 1, FAIL, 0.69 후속): D2에 따라 쿼리 카운트 절대 상한을
"구현 후 실측해 결정"에서 참조 스위트 기반 구체적 수치(`<= 6`/`<= 4`/`<= 2`)로 확정하고
기술적 접근 7단계·리스크 R5·완료 조건을 갱신했다. D3/D4에 따라 REQ-RACKBATCH-005(빈 행
2건 이상 판별 테스트)와 REQ-RACKBATCH-007(빈 문자열 clear)을 M1/M4 신규 테스트 대상에
명시적으로 추가했다. D6/D7에 따라 REQ-RACKBATCH-015(500 경로)와 REQ-RACKBATCH-014 전용
필드 스냅샷 테스트를 M4에 추가했다. D8에 따라 mx_plan에 기존 `@MX:WARN`/`@MX:REASON`
(`:2218-2226`)의 이관 계획을 신설했다.

v1.0.2 변경(plan-auditor iteration 2, FAIL, 0.75 후속, iteration 3/3 최종): **사용자 결정**
— 렉번호 로직을 모듈 레벨 순수 함수 `_process_rack_number_rows(rows) -> dict`로 추출하도록
아키텍처를 변경(spec.md 설계 결정 H). 이 문서 전체(파일별 변경 계획, 마일스톤, 기술적 접근,
mx_plan, 리스크)를 그 함수 중심으로 재작성했다. **D2**: AC-001의 측정 스코프를 함수 직접
호출로 명시하고, 상한을 렉번호 함수 고유의 가드 구조에서 도출(`<= 6`/`<= 4`/`<= 2`, 참조
스위트와 같은 안전 여유 관례를 재사용하되 값을 그대로 베끼지 않고 도출 과정을 명시). **D2b**:
"전량 미매칭" 픽스처를 부재 `Order.name`으로 확정(LineItem 조회가 확실히 스킵됨). **D2c**:
`<= 2` 인용 범위를 `:1143-1153`에서 `:1155-1157`로 정정(4곳). **D4-R**: 빈 식별자 2행의
SKU를 "서로 다름"에서 "동일"로 정정 — 서로 다른 SKU는 판별력이 없었다. **D7-R**: 쓰기 범위
테스트에 SQL 컬럼 목록 assertion을 추가(스냅샷만으로는 `bulk_update` 필드 목록 확대를
감지할 수 없음), R6 완화책 설명을 정정. **D12**: 원자성(REQ-013) 전용 테스트를 신설 —
기존 테스트는 `bulk_update` 실행 **전**에 예외를 주입해 원자성을 증명하지 못했다(500 경로만
증명). 새 테스트는 `bulk_update` 실행 **후**, 트랜잭션 종료 전에 주입한다. **D13**:
응답 키 집합이 정확히 `{"matched_count", "skipped_count"}`임을 확인하는 신규 테스트를
추가(REQ-008, 기존 테스트는 개별 키 존재만 확인하고 추가 필드를 감지하지 못했다).

v1.0.3 변경(plan-auditor iteration 3/3, **PASS**, 0.88 후속 — 문서 정리, 블로킹 결함 없음):
**D17**: AC-011(a)의 SQL 레벨 검증을 "SET 절이 참조하는 컬럼"에서 "SET 절에서 대입되는
컬럼"으로 좁혀 Django `bulk_update`의 `CASE WHEN "id" = ...`가 오탐되지 않게 정정(기술적
접근 8단계, 리스크 R6). **D18**: AC-011/AC-012의 스코프를 뷰가 아닌 함수 직접 호출로 명확히
정렬(spec.md와 acceptance.md가 이미 함수 스코프였던 D2/D12 취지를 계획서 표현에도 반영).
**D20(b)**: 이관된 `@MX:WARN`/`@MX:REASON`의 위치 표현을 "새 함수 위" → "새 함수 본문 안,
판정 지점"으로 파일 전체(파일별 변경 계획, 기술적 접근 5단계, 리스크 R7, 참조 구현 목록)에서
통일. **D21**: 동명 Order tie-break 픽스처 기법의 인용을 정정 —
`test_spec_015.py:1166-1186`은 `pk` 오름차순 그대로 Order를 생성하므로 "동일한 기법"이
아니라, 이 SPEC이 강화한 별도 요구사항(낮은 `pk`를 나중에 생성)임을 명시. **기록(결함 아님)**:
`UploadRackNumberView.post()` MODIFY 행에 dedup 단계 예외가 이제 뷰의 `except Exception`
가드 안으로 들어온다는 동작 변화를 기록.

개발 방법론: TDD (RED-GREEN-REFACTOR), `.moai/config/sections/quality.yaml`
`development_mode: "tdd"`에 따름. 기존 코드 위에 얹는 브라운필드 변경이므로 RED 단계 전에
기존 `UploadRackNumberView.post()`, `_process_outbound_rows`, `_process_force_outbound_rows`를
먼저 읽고 이해하는 사전 단계를 거친다(workflow-modes.md의 Brownfield Enhancement 절).

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M1 (High) — 함수 추출 골격 + 쿼리 카운트 회귀 테스트 선작성 (RED)**: 먼저
  `_process_rack_number_rows(rows: list[dict]) -> dict`의 빈 골격(파라미터/반환 타입만,
  로직은 아직 기존 뷰에 남겨둔 채)을 `purchase_order_views.py`에 추가한다. `test_spec_017.py`
  신규 작성 — `_process_rack_number_rows(rows)`를 `CaptureQueriesContext`로 직접 감싸
  2-키 vs 10-키 쿼리 수 동등성 + 절대 상한 `<= 6`/`<= 4`/`<= 2` 테스트(REQ-RACKBATCH-001,
  002)와 동명 `Order.name` 최저 `pk` tie-break 테스트(REQ-RACKBATCH-004)를 작성한다 — 함수가
  아직 빈 골격이므로 이 테스트는 자연히 RED다.
- **M2 (High) — 로직 추출 및 배치 재작성 (GREEN)**: `UploadRackNumberView.post()`에 있던
  dedup·판정·쓰기 로직 전체를 `_process_rack_number_rows`로 이동하면서 동시에 배치 조회
  2회 + `bulk_update` 1회로 재작성한다(단순 이동이 아니라 이동과 재작성을 함께 수행 —
  이동만 하면 기존 3-쿼리/키 루프가 함수 안으로 옮겨질 뿐 GREEN이 되지 않는다). 뷰는 파일
  검증 → 파싱 → 함수 호출 → 응답 포장의 얇은 래퍼로 축소한다. 커버 REQ: 001, 002, 003, 004,
  005, 006, 007, 013, 014, 015.
- **M3 (High) — 기존 15개 특성화 테스트 무수정 통과 확인 (GREEN 유지)**:
  `test_spec_013.py::TestUploadRackNumberView` 전량 재실행 — 이 테스트들은 여전히 뷰를
  HTTP로 호출하므로 함수 추출이 뷰의 관측 가능한 동작(요청/응답 계약)을 바꾸지 않았음을
  검증한다. 결정 E 테스트(`test_upload_multiple_lineitems_matching_key_all_updated`, :748)와
  미호출 테스트(`test_upload_never_calls_recompute_order_aggregates`, :842)를 특히 주시한다.
  빈 식별자 테스트(`:809`)는 통과해야 하지만 REQ-RACKBATCH-005의 판별 근거로는 세지 않는다
  (D4-R, M4에서 판별 테스트를 별도로 작성).
- **M4 (Medium) — 나머지 신규 테스트 보강 (RED→GREEN)**: 다음 6개 시나리오를
  `test_spec_017.py`에 추가한다(함수를 직접 호출하는 것과 뷰를 HTTP로 호출하는 것을
  시나리오별로 구분 — 아래 기술적 접근/테스트 전략 참조) — (a) 빈 문자열 rack_number가
  명시적 clear로 반영됨(REQ-RACKBATCH-007, D3), (b) 빈 주문 식별자 행 **2건(동일 SKU)**이
  병합되지 않고 개별 skipped로 집계됨(REQ-RACKBATCH-005, D4-R), (c) 처리되지 않은 예외 →
  HTTP 500(REQ-RACKBATCH-015), (d) `bulk_update` 실행 **후** 예외 주입 → 원자성 확인
  (REQ-RACKBATCH-013, D12, (c)와는 별개의 주입 지점), (e) 성공한 업로드의 UPDATE 문 SET
  절이 `rack_number`만 참조함을 SQL 레벨로 확인 + 필드 스냅샷(REQ-RACKBATCH-014, D7-R),
  (f) 응답 본문 키 집합이 정확히 `{"matched_count", "skipped_count"}`임을 확인
  (REQ-RACKBATCH-008, D13).
- **M5 (Low) — 문서 동기화**: `spec.md`/`plan.md`/`acceptance.md` 완료 상태 갱신. M1에서
  실측한 쿼리 카운트가 `<= 6`/`<= 4`/`<= 2`와 다르면 근거와 함께 세 문서 모두 갱신한다(D2 —
  구현 시점에 처음 정하는 것이 아니라 사전에 정한 값의 검증·필요 시 정정).

의존 관계: M1 → M2 → M3, M2 → M4. M5는 M1~M4 완료 후.

## 파일별 변경 계획

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| NEW (모듈 레벨 함수, 같은 파일 안) | `backend/order/purchase_order_views.py` — `_process_rack_number_rows(rows: list[dict]) -> dict` | dedup·배치 Order 조회·배치 LineItem 조회·판정·`transaction.atomic()`·`bulk_update`를 전부 소유(spec.md 설계 결정 H). 참조 구현: `_process_outbound_rows`(`:2423-2714`)의 배치 Order/LineItem 조회 패턴(`:2532-2558`)과 `bulk_update` flush(`:2701-2704`) — 단 2+ 매칭 거부 분기(`:2582-2594`)는 이식하지 않는다(REQ-RACKBATCH-006, spec.md 설계 결정 A). 두 번째 선례: `_process_force_outbound_rows`(`:3021-`)도 동일하게 "모듈 레벨 순수 함수 + 얇은 뷰 래퍼" 구조를 쓴다. 동명 `Order.name` 해석은 기존 `_resolve_orders_by_name` 헬퍼(`:2812-2829`) 재사용을 우선 검토한다 — 재사용이 어려우면 `_process_outbound_rows`와 동일한 `order_by("pk")` + `setdefault` 인라인 패턴으로 재현한다. **이 함수 본문 안, 다중 매칭 판정 지점으로 기존 `@MX:WARN`/`@MX:REASON`(현재 `:2218-2226`, 결정 E 다중 매칭 경고)을 이관한다 — 삭제하지 않는다(mx_plan 참조, D8, D20(b)).** 호출부는 정확히 하나(`UploadRackNumberView.post()`)여야 한다. |
| MODIFY | `backend/order/purchase_order_views.py` — `UploadRackNumberView.post()`(현재 `:2180-2266`) | 파일 존재 확인(`:2181-2183`) → `.xlsx` 확장자 확인(`:2185-2190`) → `parse_rack_number_excel` 호출·`ValueError`→422(`:2193-2196`) → `_process_rack_number_rows(parsed_rows)` 호출 → 반환된 dict를 `Response(..., 200)`으로 포장하는 얇은 래퍼로 축소. 기존 `except Exception` → 500 가드(`:2257-2261`)는 `_process_rack_number_rows` 호출을 감싸는 형태로 그대로 유지한다(REQ-RACKBATCH-015의 구현). `dedup_map` 구축부(`:2198-2212`)는 이 메서드에서 **제거되어** 새 함수로 이동한다(단순 삭제가 아니라 이동). **알려진, 수용된 동작 변화(plan-auditor가 발견, 결함 아님)**: 현재는 `dedup_map` 구축(`:2198-2212`)이 `try` 블록(`:2216`에서 시작) **밖**에 있어 dedup 단계에서 예외가 나면 DRF로 그대로 전파된다. 추출 이후에는 dedup이 `_process_rack_number_rows` 호출 **안**으로 옮겨가므로 같은 예외가 뷰의 `except Exception` 가드에 잡혀 `{"detail": ...}` 500 JSON 본문으로 바뀐다. 두 경로 모두 500 계열이고 이를 pin하는 기존 테스트가 없어 15개 특성화 테스트에 대한 회귀는 아니지만, 구현 중 우연히 발견하기보다 여기서 미리 기록해 둔다. |
| NEW | `backend/order/tests/test_spec_017.py` | 모듈 docstring `"""SPEC-ORDER-017: rack-number upload batching (TDD)."""` + `Coverage targets:` T1~Tn과 REQ/AC 매핑(`test_spec_015.py:1-24` 관례). 두 계층의 테스트를 구분해서 담는다 — (1) `_process_rack_number_rows`를 **직접 호출**하는 함수 레벨 테스트(쿼리 카운트 REQ-001/002, tie-break REQ-004, 500 REQ-015, 원자성 REQ-013, 쓰기 범위 REQ-014), (2) `auth_client.post(...)`로 **뷰를 호출**하는 엔드포인트 레벨 테스트(빈 문자열 clear REQ-007, 빈 식별자 비병합 REQ-005, 응답 키 집합 REQ-008). `_seed_rack_rows(n, offset)` 픽스처 빌더와 `_count_queries(...)` 헬퍼는 `test_spec_015.py:1104-1121`의 기법을 그대로 재사용(같은 `CaptureQueriesContext` 임포트, `test_spec_015.py:34`), 단 대상 호출을 `_process_rack_number_rows`로 바꾼다. |
| EXISTING | `backend/order/tests/test_spec_013.py` | 변경하지 않는다. 15개 특성화 테스트 무수정 전량 통과가 M3의 완료 조건이다. |
| EXISTING | `backend/order/excel_utils.py` | 변경하지 않는다(spec.md Exclusions). |
| EXISTING | `backend/order/models.py` | 변경 없음. 신규 컬럼·마이그레이션·인덱스 없음(spec.md 설계 결정 E). `Order.name` 인덱스(`:100-110`)가 이미 존재해 배치 조회 성능 전제는 충족되어 있다. |
| EXISTING | 프론트엔드 전체 (`frontend/src/**`) | 변경하지 않는다. 응답 계약 불변, axios 타임아웃 미설정 확인 완료(`research.md` §8). |

## 기술적 접근

### 함수 추출과 배치 재작성 (M1-골격, M2-완성)

1. **함수 시그니처**: `def _process_rack_number_rows(rows: list[dict]) -> dict:` — `rows`는
   `parse_rack_number_excel`의 원본 반환값(파싱된 행 리스트, dedup 이전)이다. 뷰는 이
   함수에 파싱 결과를 그대로 넘기고, dedup은 함수 내부에서 수행한다(spec.md 설계 결정 H —
   "dedup은 뷰가 아니라 이 함수가 수행한다").
2. **`dedup_map` 구축**: 기존 로직(현재 `purchase_order_views.py:2198-2212`)을 그대로
   함수 안으로 옮긴다 — 순수 파이썬이며 DB 접근이 없다.
3. **Order 배치 조회**: `dedup_map.values()`에서 `order_name is not None`인 행들의
   `order_name` 집합을 모아 `Order.objects.filter(name__in={...}).order_by("pk")` 1회 조회
   후 `orders_by_name.setdefault(candidate.name, candidate)`로 최저 `pk` 선점
   (REQ-RACKBATCH-004). **이 조회는 반드시 `if order_names:`류 가드로 감싼다** —
   `_process_outbound_rows`의 `if grouped:` 가드(`:2533`)와 동일한 역할이며,
   AC-RACKBATCH-001의 전량-미매칭/빈-입력 상한이 이 가드의 존재를 전제한다.
   `_resolve_orders_by_name(names)`(`:2812-2829`) 재사용을 1순위로 검토 — 시그니처가 이미
   이 용도에 정확히 맞는다(빈 입력 시 쿼리 0회, 반환 타입 `dict[str, Order]`, 가드가 함수
   내부에 이미 있음). 재사용 시 함수 정의 순서(`_resolve_orders_by_name`이 현재
   `UploadRackNumberView`보다 파일 뒤쪽에 있음)를 확인하고, Python은 함수 호출 시점에
   이름을 해석하므로 같은 모듈 안에서는 정의 순서가 실행에 영향을 주지 않음을 확인한다.
4. **LineItem 배치 조회**: 채택된 Order id 집합과 dedup-키의 sku 집합으로
   `LineItem.objects.filter(order_id__in=[...], sku__in={...}).order_by("pk")` 1회 조회 후
   `(order_id, sku)` 키의 `list[LineItem]`으로 그룹핑(`_process_outbound_rows`의
   `line_items_by_key` 패턴, `:2549-2558`과 동일 구조). **이 조회는 반드시
   `if orders_by_name:`류 가드로 감싼다** — `_process_outbound_rows`의 `:2550` 가드와
   동일 — Order 조회 결과가 비면(전량 미매칭 케이스) LineItem 조회는 실행되지 않는다. 이
   가드가 없으면 AC-RACKBATCH-001의 전량-미매칭 상한(`<= 4`)이 성립하지 않는다.
5. **판정 및 반영 — 결정 A 비승계 지점**: `dedup_map`을 순회하며,
   - `order_name is None`이면 기존과 동일하게 `skipped_count += 1`.
   - 이름이 Order로 해석되지 않으면 `skipped_count += 1`.
   - `(order.id, sku)`로 후보 리스트를 조회 — **빈 리스트면 `skipped_count += 1`**,
     **1건 이상이면 각 LineItem의 `rack_number`를 설정하고 전부 `to_update`에 append,
     `matched_count += 1`**(REQ-RACKBATCH-006 — `_process_outbound_rows`의
     `if len(candidates) != 1: reject` 분기를 절대 복사하지 않는다). **기존
     `@MX:WARN`/`@MX:REASON`(현재 `:2218-2226`, 결정 E 다중 매칭 경고)을 이 판정 지점
     (신설 `_process_rack_number_rows` **함수 본문 안**, 바로 이 분기 바로 위)으로 이관한다
     — 이 로직이 바로 그 태그가 경고하는 "한 키가 LineItem 2건 이상과 매칭"되는 조건을
     처리하는 곳이기 때문이다(**v1.0.3 정정, D20(b)** — mx_plan 표(아래)의 배치와
     일치시켰다).**
   - 빈 문자열 rack_number도 다른 값과 동일하게 취급한다 — falsy 필터링 금지
     (REQ-RACKBATCH-007).
6. **단일 flush**: `if to_update: LineItem.objects.bulk_update(to_update,
   ["rack_number"])`. **이 가드는 필수다** — `_process_outbound_rows`의 `if to_update:`
   가드(`:2701`)와 동일 — 갱신 대상이 없으면 `bulk_update`가 아예 호출되지 않는다.
   `bulk_update`의 필드 목록은 `rack_number` 하나뿐이다(REQ-RACKBATCH-014) —
   `_process_outbound_rows`는 3필드를 쓰지만 이 함수는 1필드만 쓴다는 점이 다르다.
7. **원자성**: 함수 전체(dedup 이후 배치 조회부터 flush까지)를 `transaction.atomic()`으로
   감싼다(REQ-RACKBATCH-013). **이 블록은 dedup 결과가 비어 있어도(빈 `rows` → 빈
   `dedup_map`) 조건 없이 항상 진입한다** — `_process_outbound_rows`가 `grouped`가 비어도
   `with transaction.atomic():`을 그대로 실행하는 것과 동일(참조: `test_spec_015.py`
   `:1155-1157`의 빈 배치 상한 `<= 2`가 바로 이 무조건 진입을 전제로 성립한다). **v1.0.1의
   "빈 dedup_map이면 조회를 건너뛰고 즉시 반환" 문구는 이 무조건 진입 원칙과 모순되므로
   폐기한다** — atomic 블록 진입 자체는 조건 없이 일어나고, 블록 **내부의** 3개 가드(3~6단계)
   가 실제 쿼리 발생 여부를 결정한다.
8. **예외 처리**: `UploadRackNumberView.post()`의 기존 `try/except Exception -> 500`
   구조(현재 `:2216-2261`)를 그대로 유지하되, 감싸는 대상을 "dedup-키 순회 루프"에서
   "`_process_rack_number_rows` 호출"로 바꾼다. 이 구조 자체가 REQ-RACKBATCH-015(처리되지
   않은 예외 → HTTP 500 + 부분 미반영)의 구현이므로 신규 코드가 필요하지 않다.
9. **쿼리 예산과 상한 도출**: `_process_rack_number_rows(rows)`를 직접 호출해 측정할 때
   (`test_spec_015.py:1118-1121`과 동일한 측정 컨텍스트 — HTTP도, 인증 쿼리도 없음),
   - **10키 전량 매칭**: savepoint(1) + Order 조회(1) + LineItem 조회(1) + `bulk_update`(1)
     + release(1) = 실측 5. 안전 여유 +1 = **`<= 6`**(`test_spec_015.py:1143-1147`이 같은
     여유를 쓰는 것과 동일한 관례 — 렉번호 함수가 같은 가드 구조를 갖는다는 전제 위에서
     재사용이 정당화된다. 값을 그대로 베낀 것이 아니라 우리 함수의 가드 구조로부터 독립적으로
     도출한 결과가 우연히 같다).
   - **전량 미매칭(부재 `Order.name`으로 한정)**: Order 조회는 실행되지만(0건 반환) LineItem
     조회는 `if orders_by_name:` 가드에 걸려 스킵된다. savepoint(1) + Order(1) + release(1)
     = 실측 3. 안전 여유 +1 = **`<= 4`**(`test_spec_015.py:1149-1153`과 동일 관례). **주의**:
     "SKU가 없어서 미매칭"(Order는 찾지만 LineItem이 없는 경우)은 LineItem 조회가 실행되므로
     실측 4가 되어 이 상한과 다르다 — M1 테스트는 반드시 부재 `Order.name` 픽스처
     (`test_spec_015.py:1151`의 `#MISSING{i}` 패턴 참고)를 사용해야 한다.
   - **빈 입력**: `rows = []` → `dedup_map = {}` → 3개 가드 전부 거짓 → savepoint(1) +
     release(1) = 실측 2, 안전 여유 없음(다른 경로가 없으므로) = **`<= 2`**
     (`test_spec_015.py:1155-1157`과 동일).
   - 이 도출은 렉번호 함수가 3~6단계의 가드 구조를 정확히 갖췄다는 전제에 의존한다 — 가드
     중 하나라도 빠지면 해당 케이스의 실측치가 늘어나 RED가 GREEN으로 전환되지 않는다.

### 테스트 전략 (M1, M3, M4)

1. **쿼리 카운트 테스트 (M1, 함수 직접 호출)**: `test_spec_015.py:1104-1157`의
   `_seed_outbound_groups` / `_count_queries` /
   `TestOutboundQueryCountIsIndependentOfRowCount` 구조를 렉번호 도메인에 맞게 이식하되,
   측정 대상을 `_process_rack_number_rows`로 바꾼다 — `_seed_rack_rows(n, offset)`는 `n`개의
   서로 다른 Order + LineItem + 대응 업로드 행(dict)을 만든다. 다음을 기술적 접근 9단계와
   동일한 숫자로 코딩한다(D2):
   - 2-키 배치와 10-키 배치의 쿼리 수 동등성 (REQ-RACKBATCH-002, 판별력의 핵심 — 절대값이
     아니라 **동등성**이 O(1)의 증거, `test_spec_015.py:1128-1131`의 클래스 docstring이
     같은 논지를 편다).
   - 전량 매칭 10-키 배치의 절대 상한 `<= 6`(REQ-RACKBATCH-001).
   - 전량 미매칭(**부재 `Order.name`**) 배치의 절대 상한 `<= 4` — LineItem 조회와 write
     쿼리가 발생하지 않아야 한다(D2b).
   - 빈 입력의 절대 상한 `<= 2`.
2. **동명 Order tie-break (M1, 함수 직접 호출)**: **(v1.0.3 정정, D21)** 이전 버전은 이
   픽스처가 `test_spec_015.py:1166-1186`(`test_duplicate_order_names_resolve_to_the_lowest_pk_order`)
   와 "동일한 기법"이라고 서술했으나, 그 테스트를 다시 열어 보면 `first = _make_order(...)`
   다음 `second = _make_order(...)`(`:1175-1176`) 순서로 생성해 **`pk` 오름차순 = 생성 순서**
   그대로다 — `pk`와 생성 시각을 일부러 어긋나게 만들지 않는다. "낮은 `pk`가 나중에 생성되도록"
   하는 뒤집기는 이 SPEC(spec.md AC-RACKBATCH-003, acceptance.md AC-RACKBATCH-003)이 참조
   테스트보다 **강화한** 자체 요구사항이며, 참조 테스트는 이를 입증하지 않는다. 따라서 렉번호
   tie-break 테스트는
   참조 테스트의 "같은 `name`으로 Order 2건을 만들고 최저 `pk`가 선택되는지 확인"하는
   기법만 가져오고, `pk`를 생성 순서와 어긋나게 만드는 부분은 직접 구현해야 한다 — 예를 들어
   먼저 만든 Order를 삭제 후 재생성하거나, 두 번째로 생성한 Order에 더 낮은 `pk`가 배정되도록
   `pk`/`id`를 명시적으로 지정하는 방식으로, `_make_order`류 헬퍼가 자동 증가 `pk`만 쓰면
   이 뒤집기가 재현되지 않는다는 점을 픽스처 작성 시 명시적으로 처리한다. 같은 `name`의
   Order 2건을 만들되 낮은 `pk`를 가진 쪽이 나중에 생성되도록 하고, `_process_rack_number_rows`
   호출 결과가 낮은 `pk`의 LineItem에 반영됨을 확인한다(REQ-RACKBATCH-004).
3. **결정 E 회귀 (M3, 뷰 호출)**: `test_spec_013.py:748`가 이미 이를 검증하므로 신규 테스트는
   불필요하지만, 함수 추출 + 배치 재작성 직후 이 테스트를 **가장 먼저** 단독 실행해 결정 A
   비승계가 깨지지 않았음을 조기에 확인한다.
4. **빈 문자열 clear (M4, 뷰 호출)**: `rack_number="A-01"`인 LineItem에 빈 문자열 행을
   업로드해 `""`로 갱신됨을 확인한다(REQ-RACKBATCH-007, D3 — 기존 15개 테스트 중 이를 뷰
   레벨에서 검증하는 것이 없다; `test_spec_013.py:467`은 파서 레벨이라 뷰에 도달하지 않는다).
5. **빈 주문 식별자 2건(동일 SKU) 비병합 (M4, 뷰 또는 함수 호출)**: 빈 식별자 행 **2개, 같은
   SKU** + 유효 행 1개를 업로드해 `skipped_count == 2`, `matched_count == 1`을 확인한다
   (REQ-RACKBATCH-005, D4-R). **동일 SKU가 필수 조건이다** — 서로 다른 SKU면 오구현
   `(None, sku)`도 두 개의 별개 키를 만들어 `skipped_count == 2`를 반환하므로 판별력이
   없다(v1.0.1의 결함). 동일 SKU여야 오구현이 `(None, "동일SKU")` 하나로 병합되어 1을
   반환하고, 정상 구현 `(None, idx)`만 2를 반환한다. 기존 `test_spec_013.py:809`는 빈 행
   1건뿐이라 이 REQ의 판별 근거가 될 수 없다.
6. **500 경로 (M4, 함수 직접 호출)**: `_process_rack_number_rows`가 처리 중 어느 시점에서든
   처리되지 않은 예외를 일으키도록 주입하고, 뷰가 이를 HTTP 500으로 변환함을 확인한다
   (REQ-RACKBATCH-015). 이 테스트는 원자성을 증명하지 않는다(D12) — 예외가 쓰기 이전에
   발생해도 500은 관측되므로, 이 시나리오만으로는 `transaction.atomic()`의 유무를 구별할
   수 없다.
7. **원자성 전용 (M4, 함수 직접 호출, 신규)**: 두 키를 매칭하는 배치를 준비하고, 실제
   `bulk_update`가 DB에 UPDATE 문을 실행한 **직후**, `transaction.atomic()` 블록이 끝나기
   **전**에 예외를 주입한다(예: `LineItem.objects.bulk_update`를 실제 구현을 먼저 호출한
   뒤 예외를 던지는 side_effect로 패치). 함수 호출이 예외를 전파한 뒤, 별도의(성공한) 조회로
   두 LineItem의 `rack_number`가 요청 이전 값 그대로임을 확인한다(REQ-RACKBATCH-013). 이
   지점에 주입해야 판별력이 생긴다 — 쓰기 이전에 주입하면(v1.0.1의 방식) `transaction.atomic()`
   이 없어도 애초에 아무것도 쓰이지 않았으므로 결과가 똑같다.
8. **쓰기 범위 — SQL 대입 컬럼 + 필드 스냅샷 (M4, 함수 직접 호출, D7-R로 확장, D17로 정밀화)**:
   `title`/`quantity`/`price`/`purchase_status`/`logistics_status`/`shipped_quantity`/
   `shipped_at`에 비기본값을 심은 LineItem 1건을 매칭 업로드로 갱신시킨다. **(a) SQL 레벨**:
   `CaptureQueriesContext`로 감싸 캡처된 쿼리 중 `UPDATE` 문의 `SET` 절에서 **대입되는**
   컬럼(각 대입식의 좌변)이 `rack_number`뿐이고 다른 `LineItem` 컬럼이 대입 대상으로 없는지
   확인한다 — 이것이 `bulk_update`에 여분 필드를 넘기는 실수를 잡는 유일한 방법이다(값
   스냅샷은 읽은 값을 그대로 되쓰므로 diff가 비어 감지하지 못한다, D7-R). **주의(D17)**:
   "SET 절에 등장하는 모든 컬럼"으로 검사하면 정상 구현도 실패한다 — Django `bulk_update`는
   `SET "rack_number" = CASE WHEN "id" = %s THEN %s ... END`를 내므로 `id`가 `WHEN` 조건
   안에 등장한다(Django 5.1.6 `django/db/models/query.py:897` 주석으로 확인). 검사 대상은
   반드시 "대입식의 좌변"으로 한정한다. **(b) 값 레벨**: 업로드 전후 필드를 스냅샷 비교해
   `rack_number` 외 전 필드가 불변임을 확인한다(REQ-RACKBATCH-014) — 이 절반은 필드
   **값**을 바꾸는 구현(예: `_process_outbound_rows`의 `logistics_status` 전이를 잘못
   복사하는 경우)을 잡는다.
9. **응답 키 집합 (M4, 뷰 호출, 신규)**: 정상 매칭되는 업로드를 실행하고, `res.data.keys()`
   (또는 `set(res.data)`)가 정확히 `{"matched_count", "skipped_count"}`와 같은지 assert한다
   (REQ-RACKBATCH-008, D13 — 기존 `test_upload_matches_and_updates_lineitem`(`:664-678`)은
   개별 키의 존재만 확인하고 키 집합의 동등성은 확인하지 않아, 응답에 필드가 추가되어도
   통과했다).
10. **미호출 회귀 (M3, 뷰 호출)**: `test_spec_013.py:842`(`test_upload_never_calls_
    recompute_order_aggregates`)가 이미 존재하므로 재사용, 신규 작성 불필요.

## 리스크 분석 및 완화책

| # | 리스크 | 영향 | 완화책 |
|---|---|---|---|
| R1 | `_process_outbound_rows`의 "정확히 1건만 허용" 분기를 습관적으로 복사 | 결정 E 계약 붕괴 — `test_upload_multiple_lineitems_matching_key_all_updated`(:748) 즉시 실패 | 이 분기를 명시적으로 "복사 금지"로 계획에 명기(설계 결정 A, 기술적 접근 5단계). M3에서 이 테스트를 최우선 실행 |
| R2 | 빈 문자열 rack_number를 falsy로 걸러내는 관용구(`if row["rack_number"]:`)를 무심코 사용 | AC-RACKBATCH-004가 pin하려는 명시적 clear 시나리오가 조용히 깨짐 — 뷰 레벨에 이를 잡는 기존 테스트가 없다(D3) | 판정 로직에서 rack_number 값 자체로 분기하지 않고 오직 "후보 존재 여부"로만 분기하도록 구현(기술적 접근 5단계). M4에서 신설하는 빈 문자열 clear 테스트로 pin |
| R3 | `_resolve_orders_by_name` 재사용 시 함수 정의 순서 문제로 `NameError` | GREEN 단계 초반 런타임 오류 | Python은 모듈 레벨 함수 호출을 실행 시점에 이름 해석하므로 같은 모듈 내 순서는 무관함을 사전 확인(기술적 접근 3단계). 문제 발생 시 인라인 패턴으로 폴백 |
| R4 | `LineItem.sku`에 단독 인덱스가 없어 `sku__in`이 느릴 가능성 | 배치 조회 자체가 느려짐 | `order_id__in`이 먼저 인덱스로 좁혀지므로(`research.md` §6) 이 SPEC의 배치 규모에서는 문제 없음으로 판단. 신규 인덱스는 범위 밖(설계 결정 E) |
| R5 | M1에서 실제 측정한 쿼리 수가 사전에 확정한 `<= 6`/`<= 4`/`<= 2`(D2)와 다름, 또는 3~6단계의 가드 중 하나가 누락되어 상한이 성립하지 않음 | RED가 예상과 다른 이유로 실패해 원인 진단에 시간이 걸리거나, 상한이 너무 taut해 사소한 변경에도 깨짐 | 상한 도출이 렉번호 함수 자신의 가드 구조에 근거하므로(기술적 접근 9단계), 실측치가 다르면 먼저 가드 3종(3~6단계)이 전부 구현되었는지 확인한다. 구조적으로 불가피하다고 판단되면 M5에서 `spec.md` HISTORY에 근거를 남기고 세 문서를 함께 정정한다(값을 실측 후 처음 정하지 않는다) |
| R6 | `bulk_update` 필드 목록에 실수로 다른 필드를 포함 | REQ-RACKBATCH-014(쓰기 범위 제한) 위반 | `bulk_update(to_update, ["rack_number"])`로 단일 필드만 명시. **정정(D7-R)**: 값 스냅샷 테스트(AC-RACKBATCH-011 (b))만으로는 이 리스크를 pin하지 못한다 — `bulk_update`가 읽은 값을 그대로 되쓰므로 여분 필드가 있어도 diff가 비어 감지되지 않는다. 실제로 pin하는 것은 M4-8(a)의 SQL 컬럼 목록 assertion(AC-RACKBATCH-011 (a))이다 |
| R7 | 재작성 대상 루프 안의 기존 `@MX:WARN`/`@MX:REASON`(`:2218-2226`)이 재작성 중 실수로 삭제됨 | 결정 E의 위험 신호(다중 매칭)가 코드에서 사라져 이후 독자가 그 위험을 인지하지 못함 | mx_plan에 명시적 이관 행 추가(D8). 코드 리뷰 체크리스트에 "기존 WARN/REASON이 신설 함수 **본문 안** 판정 지점(mx_plan 행 참조)에 존재하는가"를 항목화 |
| R8 (신규) | 함수 추출 리팩터링 도중 `UploadRackNumberView.post()`의 기존 상태 코드 순서(400 → 422 → 500)나 파일 검증 로직이 실수로 바뀜 | `test_spec_013.py`의 400/422 관련 테스트가 회귀 | 뷰의 파일 검증·확장자 검증·파싱 단계(`:2181-2196`)는 위치와 순서를 그대로 두고, 오직 dedup-키 순회 루프(`:2198-2261`)만 함수 호출로 치환한다(파일별 변경 계획의 MODIFY 행 참조). M3에서 15개 테스트 전량 재실행으로 확인 |
| R9 (신규) | 원자성 전용 테스트(M4-7)의 `bulk_update` 패치가 실제 구현을 우회해 실제로는 아무것도 쓰지 않고 예외만 던짐 | 테스트가 항상 통과해 원자성을 전혀 검증하지 못하는 거짓 양성이 됨 | 패치의 side_effect는 반드시 원본(패치 이전) `bulk_update`를 먼저 호출해 실제 UPDATE를 실행한 뒤에 예외를 던져야 한다. 코드 리뷰에서 이 순서를 명시적으로 확인 |

## MX 태그 계획 (mx_plan)

| 대상 | 태그 | 내용 |
|---|---|---|
| `_process_rack_number_rows` 함수 정의부(신규) | `@MX:NOTE` | `_process_outbound_rows`의 `@MX:NOTE`(`:2403-2414`)를 미러링 — 모든 DB 접근이 dedup-키 개수와 무관하게 고정된 쿼리 수(Order 조회 1 + LineItem 조회 1 + bulk_update 최대 1)로 배치되어 있음을 기록하고, 원래 구현이 키당 3쿼리를 실행해 8키 업로드가 ~24왕복, 50키가 ~150왕복이었다는 비용 모델을 남긴다. `test_spec_017.py`의 쿼리 카운트 테스트(함수 직접 호출)가 2-키/10-키 동등성 + `<= 6`/`<= 4`/`<= 2` 절대 상한으로 이를 pin함을 명시 |
| `_process_rack_number_rows` 안, 판정 루프의 결정 E 다중 매칭 지점(기존 `@MX:WARN`/`@MX:REASON`, 원래 `:2218-2226`) | `@MX:WARN`(유지, 이관) + `@MX:REASON`(유지, 이관) | **D8**: 함수 추출로 원래 위치의 `for row in dedup_map.values():` 루프(원래 `:2227`) 자체가 새 함수 안으로 옮겨지므로, 이 태그도 함께 옮긴다 — 판정 로직(기술적 접근 5단계)이 바로 그 태그가 경고하는 "한 키가 LineItem 2건 이상과 매칭"되는 조건을 처리하는 지점이다. REQ-RACKBATCH-006이 이 WARN이 경고하는 조건을 그대로 보존하므로(위험이 해소되지 않음), mx-tag-protocol("WARN은 위험이 해소될 때만 제거")에 따라 **삭제하지 않는다.** 아래 결정-A-비승계 `@MX:NOTE`와 주제가 겹치지만(둘 다 "왜 2+ 매칭을 거부하지 않는가"를 다룸), 관점이 다르므로(WARN=위험 신호, NOTE=참조 구현과의 의도적 차이) 병합해 WARN을 삭제하지 않고 같은 지점에 나란히 유지한다 |
| `_process_rack_number_rows` 안, 판정 루프의 결정 A 비승계 지점 | `@MX:NOTE` | `_process_outbound_rows`와 달리 이 함수는 후보 2건 이상을 거부하지 않고 전부 갱신한다는 의도적 분기를 기록(SPEC-ORDER-013 결정 E). 이후 독자가 두 함수를 나란히 보고 불일치를 버그로 오인해 "정합"시키지 않도록 근거(`test_spec_013.py:748`)를 남긴다. 위 WARN/REASON과 같은 지점에 위치하되 별개 태그로 유지한다(D8) |
| 락-프리 갱신 구간(기존 `@MX:WARN`, `_process_outbound_rows` 소속) | 유지 | `purchase_order_views.py:2415-2422`의 기존 `@MX:WARN`/`@MX:REASON`은 그대로 둔다 — 이 SPEC은 `_process_outbound_rows`를 건드리지 않는다(설계 결정 D). REASON 문구가 이미 `UploadRackNumberView`를 원조로 지목하므로 갱신 불필요 |
| `UploadRackNumberView.post()`의 예외 처리 래퍼(`try/except Exception`, 현재 `:2216-2261`) | 태그 없음(유지) | 함수 추출 이후에도 REQ-RACKBATCH-015(예외 → 500 + 부분 미반영)를 구현하는 지점이지만, 기존 구조를 그대로 재사용하므로(감싸는 호출 대상만 바뀜) 신규 태그를 추가하지 않는다(설계 결정 G) |
| 신규 테스트 파일(`test_spec_017.py`) | 태그 없음 | 테스트 코드에는 MX 태그를 부여하지 않는다(기존 관례, `test_spec_015.py`/`test_spec_013.py`와 동일) |

구현(run) 단계에서 위 태그를 실제 코드에 부여하고, 실제 구조가 계획과 달라지면 이 표를
갱신한다.

## 완료 조건 (Definition of Ready → Done 게이트)

레이어별로 분리한다. 항목별 REQ/AC 배정은 `acceptance.md`의 품질 게이트 절이 단일 출처이며,
이 문서는 그것을 반복하지 않는다.

**백엔드**: `test_spec_017.py`가 `acceptance.md`가 열거한 REQ 15개 전량에 최소 1개의
**판별력 있는** 테스트를 매핑(D13 이후 acceptance.md의 per-REQ 표가 단일 출처). 함수 레벨
테스트가 `_process_rack_number_rows`를 직접 호출하고 HTTP를 거치지 않는지 코드 리뷰에서
확인(D2 스코프 위반 방지). `test_spec_013.py::TestUploadRackNumberView` 15개 전량 무수정
통과. `_process_rack_number_rows`의 호출부가 정확히 1개(`UploadRackNumberView.post()`)인지
Grep으로 확인. `makemigrations --check` 무변경. ruff 신규 에러 0.

**프론트엔드**: 변경 파일 없음 — 기존 프론트엔드 테스트 스위트가 이 SPEC과 무관하게 그대로
통과하는지만 확인한다(회귀 없음 확인).

**공통**: `spec.md` Exclusions 7개 항목(v1.0.2에서 1건 추가) 전수 확인 — 특히 응답 스키마
변경, `select_for_update` 도입, 프론트엔드 파일 diff, 신규 인덱스/마이그레이션,
`_process_rack_number_rows` 외 추가 추상화 계층이 diff에 존재하지 않을 것.

## 관련 참조 구현

- `backend/order/purchase_order_views.py:2423-2714` — `_process_outbound_rows`. 배치 조회
  구조와 "모듈 레벨 함수 + 얇은 뷰 래퍼" 아키텍처의 1차 원본. `:2582-2594`(2+ 매칭 거부)만
  이식 대상이 아니다.
- `backend/order/purchase_order_views.py:3021-` — `_process_force_outbound_rows`. 같은
  아키텍처의 2차 선례(SPEC-ORDER-016). 시그니처 `def _process_force_outbound_rows(rows:
  list[dict]) -> dict`, 호출부는 `OutboundForceProcessView.post()` 단 하나.
- `backend/order/purchase_order_views.py:2533` — `if grouped:` Order 조회 가드.
- `backend/order/purchase_order_views.py:2550` — `if orders_by_name:` LineItem 조회 가드.
- `backend/order/purchase_order_views.py:2701` — `if to_update:` bulk_update 가드.
- `backend/order/purchase_order_views.py:2532-2538` — `name__in` + `order_by("pk")` +
  `setdefault` 최저 `pk` tie-break 패턴.
- `backend/order/purchase_order_views.py:2549-2558` — `order_id__in` + `sku__in` 배치
  LineItem 조회 + 딕셔너리 그룹핑 패턴.
- `backend/order/purchase_order_views.py:2701-2704` — 단일 `bulk_update` flush 패턴.
- `backend/order/purchase_order_views.py:2812-2829` — `_resolve_orders_by_name` 공유 헬퍼
  (재사용 후보).
- `backend/order/purchase_order_views.py:2218-2226` — 재작성 대상 루프 안의 기존
  `@MX:WARN`/`@MX:REASON`(결정 E 다중 매칭 경고). 삭제하지 않고 신설
  `_process_rack_number_rows` 함수 **본문 안** 판정 지점으로 이관한다(D8, D20(b), mx_plan).
- `backend/order/purchase_order_views.py:2177` — `authentication_classes =
  [JWTAuthentication]`(임포트 `:47`). 뷰 레벨 쿼리 카운트 측정이 부정확했던 근본 원인(D2)
  — 함수 추출로 이 문제를 우회한다.
- `backend/order/purchase_order_views.py:2216-2261` — 기존 `try/except Exception -> 500`
  래퍼. REQ-RACKBATCH-015의 구현이며 감싸는 호출 대상만 바뀔 뿐 구조는 그대로 유지한다
  (설계 결정 G).
- `backend/order/tests/test_spec_015.py:1104-1121` — `_seed_outbound_groups` /
  `_count_queries` 기법(함수 직접 호출, HTTP 없음 — 이식 대상).
- `backend/order/tests/test_spec_015.py:1128-1131` — 클래스 docstring, "동등성이 1차 증거"
  논지.
- `backend/order/tests/test_spec_015.py:1143-1147` — `<= 6` (10그룹 전량 매칭).
- `backend/order/tests/test_spec_015.py:1149-1153` — `<= 4` (전량 미매칭, `#MISSING{i}`
  픽스처 패턴, `:1151`).
- `backend/order/tests/test_spec_015.py:1155-1157` — `<= 2` (빈 입력). **D2c 정정**: 이전
  버전에서 `:1143-1153`으로 잘못 인용되었다.
- `backend/order/tests/test_spec_015.py:1166-1186` — 동명 Order tie-break 테스트 기법
  (이식 대상).
- `backend/order/tests/test_spec_013.py:76-79` — `auth_client` 픽스처, 실제 JWT Bearer
  토큰 발급. 뷰 레벨 테스트가 인증 쿼리를 피할 수 없는 이유(D2 배경).
- `backend/order/tests/test_spec_013.py:467` — 빈 문자열 rack_number 파서 레벨 테스트.
  뷰에 도달하지 않으므로 REQ-RACKBATCH-007의 근거가 될 수 없다(D3) — `test_spec_017.py`가
  별도로 뷰 레벨 테스트를 추가해야 하는 이유.
- `backend/order/tests/test_spec_013.py:664-678` — 기존
  `test_upload_matches_and_updates_lineitem`. 개별 키 존재만 확인하고 키 집합 동등성은
  확인하지 않는다(D13) — REQ-RACKBATCH-008의 "추가 필드 없음" 절반이 미검증이었던 근거.
