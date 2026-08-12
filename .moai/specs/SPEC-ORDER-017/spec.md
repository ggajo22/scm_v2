---
id: SPEC-ORDER-017
version: 1.0.5
status: completed
created_at: 2026-08-12
updated: 2026-08-13
author: ggajo
priority: High
issue_number: 0
labels: [order, rack-number, performance, batching]
---

# 렉번호 엑셀 업로드 배치 처리 — 행 단위 쿼리 루프를 O(1) 쿼리로 전환

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-12 | ggajo | 최초 작성 — 사용자 보고("렉번호 관리 페이지에서 렉번호 엑셀 업로드 배치처리로 바꿔줘, 지금은 너무 느리다")에 따라 `UploadRackNumberView`의 dedup-키 단위 3-쿼리 루프를 SPEC-ORDER-015가 확립한 배치 패턴(`_process_outbound_rows`)으로 전환하는 순수 성능 개선 SPEC. 관측 가능한 응답 계약·매칭 규칙·상태 코드는 전혀 변경하지 않는다. 유일한 의도적 비승계 지점은 참조 구현의 결정 A(2+ LineItem 매칭 시 거부)를 복제하지 않는다는 것이다 — 렉번호 엔드포인트는 SPEC-ORDER-013 결정 E에 따라 여러 LineItem이 매칭되면 전부 갱신해야 한다(REQ-RACKBATCH-006). 설계 결정의 근거는 `research.md`가 file:line 인용과 함께 확정했으며 본 문서에 재복제하지 않는다. |
| 1.0.1 | 2026-08-12 | ggajo | plan-auditor 리뷰(iteration 1, FAIL, 0.69) 후속 정리 — critical 1건(D1) + major 7건(D2~D8) 수정. **D1**: REQ-006과 AC-001/002/004/005/007/008/009 총 8건의 EARS 라벨이 문장 구조와 불일치하던 것을 수정 — REQ-006/AC-001/002/004/008은 Event-Driven으로 재라벨링, AC-005/009는 `If … then` Unwanted 구조로, AC-007은 `While` State-Driven 구조로 재작성. **D2**: AC-001의 "구현 시점에 실측해 정하는 작은 고정 상한"을 참조 스위트(`test_spec_015.py` T8, 동일한 `transaction.atomic()` 1회 + 배치 조회 구조)의 실측 근거를 그대로 적용한 구체적 수치(10키 전량 매칭 `<= 6`, 전량 skip `<= 4`, 빈 입력 `<= 2`)로 대체. **D3**: REQ-007(빈 문자열 clear)이 기존 15개 테스트 중 어디에도 뷰 레벨로 커버되지 않음을 인정하고 `test_spec_017.py` 신규 버킷으로 이전(acceptance.md). **D4**: AC-007의 Given을 빈 식별자 행 1개에서 2개 이상으로 확장해 병합 구현을 실제로 판별하도록 재작성(`skipped_count == 2`). **D5**: REQ-004에서 `.filter(name=X).first()` 구현 세부를 제거하고 관측 가능한 결과("동명 충돌 시 최저 `pk`의 Order 선택")만 남김. **D6**: REQ-RACKBATCH-015(신규, Unwanted)를 추가해 예외 발생 시 HTTP 500 + 부분 미반영을 규범화하고 AC-009에서 추적하도록 정정 — 이전에는 acceptance.md만 500을 주장하고 spec.md AC-009는 이를 누락해 두 문서가 불일치했다. **D7**: AC-009를 원자성/500(REQ-013/015)과 쓰기 범위(REQ-014, 신규 AC-011)로 분리 — 이전 AC-009의 후행 전칭 절이 REQ-014의 유일한 근거였고 그 픽스처로는 검증 불가능했다. **D8**: 배치 재작성 대상 루프 내부에 있는 기존 `@MX:WARN`/`@MX:REASON`(`purchase_order_views.py:2218-2226`, 결정 E 다중 매칭 경고)이 research.md/plan.md 어디에도 언급되지 않아 재작성 시 묵시적으로 삭제될 위험이 있던 것을 반영. **D9(minor)**: `status`를 `Planned`에서 프로젝트 관례(FC-3 어휘)에 맞는 `draft`로 정정. **D10(minor)**: 인용 포인터 4건을 정밀화 — `:918-929`를 `:918-925`(락 조회)와 `:927-929`(별도 무락 `.exists()` 조회)로 분리, `:2198-2211`을 `:2198-2204`(주석)와 `:2205-2212`(코드)로 분리, `:2813-2823`을 `:2813-2824`로 정정, `excel_utils.py:994`(def 줄)와 docstring 본문(`:995-1030`, 인용한 `:1018-1026`은 그대로 정확)을 구분. 순 결과: REQ 14→15(REQ-RACKBATCH-015 신설, 기존 001~014는 재번호하지 않음), AC 10→11(AC-RACKBATCH-011 신설, 기존 001~010은 재번호하지 않음). |
| 1.0.2 | 2026-08-12 | ggajo | plan-auditor 리뷰(iteration 2, FAIL, 0.75) 후속 정리 — iteration 3/3(최종). MP-1/MP-2/MP-3 전부 PASS 유지, D1/D3/D5/D6/D8/D9/D10 종결 확인. **사용자 결정(선행)**: 렉번호 로직을 순수 함수 `_process_rack_number_rows(rows) -> dict`로 추출하도록 구현 계획을 변경(신설 결정 H) — dedup·배치 조회·판정·`transaction.atomic()`·`bulk_update`를 전부 이 함수가 소유하고, `UploadRackNumberView.post()`는 파일 검증 → 파싱 → 호출 → 응답 포장만 하는 얇은 래퍼가 된다. 이 추출이 D2/D7/D12의 근본 원인(뷰 레벨 측정 시 `JWTAuthentication`의 사용자 조회 쿼리가 섞여 순수 함수가 없어 매 AC가 엔드포인트 단위로 밀려남)을 해소한다. **D2(critical)**: AC-001을 함수 직접 호출 스코프로 재정의(`CaptureQueriesContext`가 `_process_rack_number_rows(rows)`만 감쌈, HTTP·인증 쿼리 없음 — `test_spec_015.py:1118-1121`과 동일 측정 컨텍스트). 상한을 참조 스위트에서 그대로 베끼지 않고 렉번호 함수의 가드 구조(`if grouped:`류, `if orders_by_name:`류, `if to_update:`류)로부터 직접 도출 — 10키 전량 매칭 5(savepoint+Order+LineItem+bulk_update+release) + 안전 여유 1 = `<= 6`, 전량 미매칭(**부재 `Order.name`**으로 한정, LineItem 조회가 확실히 스킵됨) 3(savepoint+Order+release) + 안전 여유 1 = `<= 4`, 빈 입력(빈 `rows` → 빈 dedup_map, 단 `transaction.atomic()` 자체는 그대로 진입) 2(savepoint+release, 여유 없음) = `<= 2`. plan.md에 동일 가드를 구현 요구사항으로 명시(D2b 겸용). **D2c**: `<= 2` 근거가 `test_spec_015.py:1143-1153` 밖(`:1157`)에 있던 인용을 spec.md/acceptance.md/plan.md(2곳) 4곳에서 `:1143-1147`/`:1149-1153`/`:1155-1157`로 분리(research.md는 기존에 정확했음). **D4-R**: AC-007의 두 빈 식별자 행이 서로 다른 SKU를 가져 `(None, sku)` 오구현도 `skipped_count == 2`를 반환해 판별력이 없던 결함을 수정 — 두 행이 **동일 SKU**를 갖도록 변경(오구현은 `(None, "SKU-X")`로 병합되어 1을 반환, 정상 구현은 `(None, idx)`로 2를 반환). **D7-R**: AC-011의 스냅샷 단독 assertion이 `bulk_update`가 필드 목록에 여분 필드를 포함해도(읽은 값을 그대로 되쓰므로 diff가 비어) 감지하지 못하던 결함을 수정 — `CaptureQueriesContext`로 UPDATE 문의 SET 절이 `rack_number`만 참조하는지 확인하는 SQL 레벨 Then을 추가. plan.md의 R6 완화책 설명도 정정. **D11**: AC-011의 필드 범위를 spec.md의 7개 열거 필드로 acceptance.md와 일치시킴("모든 필드" 표현 제거). **D12(major)**: AC-009(원자성+500 결합)가 `bulk_update` 실행 전에 예외를 주입해 REQ-013(원자성)을 사실상 증명하지 못하던 결함을 수정 — AC-009는 REQ-015(500 경로)만 추적하도록 축소하고, `bulk_update`가 실제로 DB에 반영된 뒤 `transaction.atomic()` 블록이 끝나기 전에 예외를 주입하는 신규 AC-RACKBATCH-012(원자성 전용, REQ-013 추적)를 신설. **D13(major)**: REQ-008(응답 스키마 불변)의 "추가 필드 없음" 절반이 기존 테스트로 검증되지 않던 결함을 수정 — `test_spec_017.py`에 응답 키 집합이 정확히 `{"matched_count", "skipped_count"}`임을 확인하는 신규 시나리오를 추가하고 DoD 매핑표를 정정. **D14(minor)**: REQ-012에서 `_recompute_order_aggregates` 내부 심볼명을 제거하고 관측 가능한 서술("주문 집계 재계산 루틴")만 남김 — 심볼명은 결정 F에서 검증 근거로만 유지. **D15(minor)**: acceptance.md의 `[HARD]` 동등성 주장을 검증 레이어 표기가 아닌 `Traces:` 목록에만 적용되도록 좁힘(spec.md AC 항목에는 레이어 마커가 없으므로). 순 결과: AC 11→12(AC-RACKBATCH-012 신설, 기존 001~011은 재번호하지 않음), REQ 15개 유지. |
| 1.0.3 | 2026-08-12 | ggajo | plan-auditor 리뷰(iteration 3/3, **PASS**, 0.88) 후속 — 블로킹 결함 없음, 문서 정리 6건 + 미표기 결과 1건 기록. **D17(가장 먼저 수정)**: AC-RACKBATCH-011(a)의 "SET 절이 `rack_number`를 참조하고 다른 컬럼은 참조하지 않는다"는 서술이 정상 구현도 실패시켰다 — Django `bulk_update`는 `SET rack_number = CASE WHEN "id" = ... THEN ... END`를 내어 `id`가 `WHEN` 조건 안에 등장한다(Django 5.1.6 `django/db/models/query.py:897` 확인). 검증 대상을 "SET 절에 등장하는 모든 컬럼"에서 "SET 절에서 **대입되는**(좌변) 컬럼"으로 좁혔다 — 판별력(여분 필드 추가 시 실패)은 그대로 유지. spec.md/acceptance.md/plan.md 3곳 모두 수정. **D18**: spec.md의 AC-RACKBATCH-011/012가 "HTTP 500으로 응답한다", "성공적인 업로드 전후"처럼 엔드포인트 스코프로 서술되어 acceptance.md의 `[함수]` 스코프(설계 결정 H)와 불일치하던 것을 spec.md 쪽을 함수 직접 호출 스코프로 재작성해 일치시켰다(AC-012의 Then도 "HTTP 500" → "예외가 호출자에게 전파" 로 정정). **D16**: REQ-RACKBATCH-001의 "at most one"이 "빈 배치에서 쿼리 0건"을 함의하지 않아 AC-001의 가드-구조 요구가 REQ 본문에 근거가 없던 것을 REQ-001에 "조회할 대상이 없으면 그 쿼리를 발행하지 않는다"는 절을 추가해 해소. **D19**: AC-RACKBATCH-012의 근거 서술이 "Django가 atomic 블록 밖에서는 자동 커밋한다"는 부정확한 메커니즘을 들었는데, `pytest.mark.django_db`에서는 테스트 전체가 이미 래핑 트랜잭션 안이라 애초에 커밋이 일어나지 않는다 — "되돌릴 세이브포인트가 없어 이미 실행된 UPDATE가 그대로 보인다"는 정확한 설명으로 spec.md/acceptance.md 둘 다 정정. **D20**: (a) acceptance.md의 스코프 선언 문장이 AC-RACKBATCH-007을 암묵적으로 `[뷰]` 전용처럼 읽히게 했는데 AC-007 자신의 표제와 DoD 표는 이미 `[뷰 또는 함수]`였다 — 스코프 선언 문장을 AC-007(`[뷰 또는 함수]`)과 AC-009(`[함수+뷰]`, 주입은 함수·관측은 뷰)를 명시하도록 재작성. (b) 이관된 `@MX:WARN`/`@MX:REASON`의 위치를 spec.md/plan.md 여러 곳이 "새 함수 위"(함수 정의 바깥)로, mx_plan 표는 "함수 안, 판정 지점"으로 서로 다르게 서술했던 것을 "함수 본문 안, 판정 지점"으로 전체 통일. **D21**: plan.md가 렉번호 tie-break 픽스처 기법을 `test_spec_015.py:1166-1186`과 "동일한 기법"이라 서술했으나, 그 테스트를 재확인한 결과 `first`를 만든 뒤 `second`를 만들어(`:1175-1176`) `pk` 오름차순 = 생성 순서 그대로였다 — `pk`를 생성 순서와 어긋나게 만드는 것은 이 SPEC이 참조 테스트보다 **강화**한 자체 요구사항임을 명시하고, 구현 시 `pk`를 명시적으로 다루어야 한다는 점을 추가했다. **기록(결함 아님)**: `dedup_map` 구축이 함수 추출로 기존 `try` 블록(뷰의 `:2216`) 밖에서 안으로 이동해, dedup 단계 예외가 "DRF로의 무가공 전파"에서 "`{"detail": ...}` 500 JSON 본문"으로 바뀐다 — 둘 다 500 계열이고 이를 pin하는 기존 테스트가 없어 특성화 테스트 회귀는 아니지만, plan.md MODIFY 행에 알려진 동작 변화로 기록했다. 이번 버전은 REQ/AC 개수·번호에 변경이 없다(15 REQ / 12 AC 유지). |
| 1.0.4 | 2026-08-13 | ggajo | 구현 완료 — `_process_rack_number_rows()` 함수 신설(모듈 단위, 설계 결정 H), `UploadRackNumberView.post()` 얇은 래퍼로 축소, `@MX:WARN`/`@MX:REASON`을 신설 함수의 판정 지점으로 이관, `@MX:NOTE` 2건 추가(배치 비용 모델, 결정 A 비승계 근거). `test_spec_017.py` 11개 신규(쿼리 수 불변식, 최저 pk tie-break, 빈 식별자 행 비병합, 원자성 전용, 쓰기 범위 SQL/필드, 응답 키 집합, 500 경로) 전량 통과. `test_spec_013.py`는 무수정 상태로 57개(그중 `TestUploadRackNumberView` 15개) 전량 통과 — 회귀 없음. 계획 대비 발산 없음. 별건: 동기화 시점에 `test_spec_008.py` margin-calculation 3건이 실패했다 — 본 SPEC의 diff 범위 밖이다(원인은 v1.0.5 참조). REQ/AC 개수 불변(15/12). |
| 1.0.5 | 2026-08-13 | ggajo | **오귀인 정정** — v1.0.4가 `test_spec_008.py` margin-calculation 3건 실패를 "다른 세션의 `Refund` 모델 변경" 탓으로 적었으나 틀렸다. 실제 원인은 master 자체의 잠복 버그로, 같은 파일의 두 픽스처가 서로 다른 시간대 기준을 썼다 — 주문 픽스처는 `timezone.now()`(UTC), 환율 픽스처는 `date.today()`(OS 로컬 KST). `OrderSerializer._get_exchange_rate`가 `effective_date__lte=<UTC 주문 날짜>`로 조회하므로 로컬 날짜가 UTC보다 앞서는 매일 KST 00:00~09:00 구간에만 환율을 못 찾아 `margin_amount`가 `None`이 됐다. 3중 확인: 환불 커밋이 전혀 없는 SPEC-016 브랜치에서도 동일 3건 실패(852 passed), master 단독에서도 3 failed, master+픽스처 수정으로 6 passed. 수정은 PR #21로 master에 별도 병합됐고 본 SPEC의 코드 변경과 무관하다. REQ/AC 개수 불변(15/12). |

---

## 문제 정의

`/api/purchase-orders/upload-rack-number/`(`UploadRackNumberView`)는 업로드된 3열(주문
식별자/SKU/렉번호) Excel의 각 행을 `(order_name, sku)` 키로 dedup한 뒤, **키마다** 3개의 DB
쿼리(`Order` 조회 → `LineItem` 조회/존재 확인 → `update()`)를 순차 실행한다. 이 프로젝트가 쓰는
원격 MySQL 인스턴스는 쿼리 왕복당 약 130ms가 걸리므로, 응답 시간은 업로드 행(정확히는 dedup 후
고유 키) 개수에 선형 비례해 늘어난다. 사용자는 이 엔드포인트가 "너무 느리다"고 보고했다.

같은 파일 안에 이미 동일한 문제를 해결한 참조 구현이 있다 — SPEC-ORDER-015의
`_process_outbound_rows`는 배치 크기와 무관하게 Order 조회 1회 + LineItem 조회 1회 +
`bulk_update` 1회로 고정된 쿼리 수를 달성했다(근거: `research.md` §2). 이 SPEC은 그 패턴을
렉번호 엔드포인트에 적용하되, 두 엔드포인트의 매칭-이후 반영 규칙이 정반대인 지점(§ "설계
결정" A)만 의도적으로 다르게 구현한다.

## 솔루션 개요

1. **(v1.0.2, 설계 결정 H)** dedup·배치 조회·판정·`transaction.atomic()`·`bulk_update`를
   전부 소유하는 모듈 레벨 순수 함수 `_process_rack_number_rows(rows: list[dict]) -> dict`를
   신설한다 — `_process_outbound_rows`와 동일한 아키텍처. `UploadRackNumberView.post()`는
   파일 존재 확인 → `.xlsx` 확장자 확인 → 파싱(`ValueError` → 422) → 이 함수 호출 → 반환된
   dict를 `Response(..., 200)`으로 포장하는 얇은 래퍼가 된다. 기존 `except Exception` → 500
   가드는 그대로 유지한다. 이 함수는 호출부가 정확히 하나여야 한다(뷰 하나뿐).
2. dedup 로직(주문 식별자 빈 셀 처리 포함)은 순수 파이썬이며 DB 접근이 없다 — 위치만
   `_process_rack_number_rows` 내부로 옮겨진다.
3. `transaction.atomic()` 내부(함수 안)의 처리는 다음으로 구성된다:
   - Order를 `name__in`으로 한 번에 조회하고 최저 `pk` 선점으로 동명 충돌을 해소한다(기존
     `.filter(name=X).first()`가 암묵적으로 하던 tie-break를 명시적으로 재현). 이 조회는
     `_process_outbound_rows`의 `if grouped:` 가드(`:2533`)와 동일한 가드로 감싼다.
   - LineItem을 `order_id__in` + `sku__in`으로 한 번에 조회해 `(order_id, sku)` 키로
     그룹핑한다. 이 조회는 `_process_outbound_rows`의 `if orders_by_name:` 가드(`:2550`)와
     동일한 가드로 감싼다 — Order 조회 결과가 비면 LineItem 조회는 아예 실행되지 않는다.
   - dedup-키를 순회하며 그룹핑 결과에서 후보를 찾는다 — 후보가 0건이면 skip, **1건
     이상이면 전부** `rack_number`를 갱신 대상으로 표시한다(SPEC-ORDER-013 결정 E 승계,
     `_process_outbound_rows`의 2+ 매칭 거부 규칙은 승계하지 않음).
   - 수집된 대상 전체를 `bulk_update()` 1회로 flush한다 — 이 쓰기는
     `_process_outbound_rows`의 `if to_update:` 가드(`:2701`)와 동일한 가드로 감싼다.
   - `transaction.atomic()`은 dedup 결과가 비어 있어도 **항상 진입한다**(참조 구현과 동일
     — 조회 3종의 가드가 전부 거짓이 되어 내부 쿼리가 0건이 될 뿐, atomic 블록 자체를
     건너뛰는 조기 반환은 없다). 이는 AC-RACKBATCH-001의 빈 입력 상한 도출 전제다.
4. 응답 스키마 `{matched_count, skipped_count}`, 상태 코드(400/401/422/500), dedup 규칙(마지막
   행 우선), 빈 문자열 렉번호 보존 규칙, `_recompute_order_aggregates` 미호출은 전부 그대로
   유지한다.
5. 프론트엔드는 수정하지 않는다 — 응답 계약이 바뀌지 않고 클라이언트에 타임아웃 설정이 없어
   느림의 원인이 아니었다(`research.md` §8).

요구사항 본문(EARS)은 관측 가능한 동작(WHAT)만 규정한다. 아래 "설계 결정" 절은 각 판단의
근거가 된 기존 코드·테스트를 `file:line`으로 인용한다 — 구현 지시가 아니라 결정을 검증
가능하게 만드는 증거다. 구현 순서와 파일별 변경 계획은 `plan.md`를, 조사 전문은 `research.md`를
참조한다.

## 범위 — 델타

이 SPEC은 기존 엔드포인트 위에 얹는 브라운필드 성능 개선이다.

| 마커 | 대상 동작 | 내용 |
|---|---|---|
| [EXISTING] | `dedup_map` 구축 로직, 응답 스키마, 상태 코드 400/401/422/500 | 변경 없음(위치는 신설 함수 내부로 이동). |
| [EXISTING] | `parse_rack_number_excel` 파서 | 변경 없음. |
| [EXISTING] | 15개 특성화 테스트(`test_spec_013.py::TestUploadRackNumberView`) | 무수정 전량 통과가 완료 조건이다. |
| [NEW] | `_process_rack_number_rows(rows) -> dict` (모듈 레벨 순수 함수) | dedup·배치 조회·판정·`transaction.atomic()`·`bulk_update`를 전부 소유(REQ-RACKBATCH-001~007, 013, 014, 015). 호출부는 `UploadRackNumberView.post()` 단 하나(설계 결정 H, 사용자 결정 v1.0.2). |
| [MODIFY] | `UploadRackNumberView.post()` | 파일 검증 → 파싱 → `_process_rack_number_rows` 호출 → 응답 포장만 하는 얇은 래퍼로 축소. |
| [NEW] | 쿼리 카운트 테스트(함수 직접 호출) | `_process_rack_number_rows(rows)`를 `CaptureQueriesContext`로 직접 감싸 2-키/10-키 동등성 + 절대 상한을 검증(REQ-RACKBATCH-001, 002). HTTP·인증 쿼리가 섞이지 않는다(plan-auditor D2). 현재 이 함수 자체가 없으므로 커버리지 없음. |
| [NEW] | 동명 `Order.name` 최저 `pk` tie-break 테스트 | 현재 커버리지가 없다(REQ-RACKBATCH-004). |
| [NEW] | 빈 문자열 rack_number 초기화 테스트 | 뷰 레벨에서 이를 검증하는 기존 테스트가 없다(REQ-RACKBATCH-007, plan-auditor D3). |
| [NEW] | 빈 주문 식별자 2건(동일 SKU) 비병합 테스트 | 기존 테스트(`test_spec_013.py:809`)는 빈 행 1건만 다뤄 병합 구현을 판별하지 못한다(REQ-RACKBATCH-005, plan-auditor D4/D4-R). |
| [NEW] | 쓰기 범위 SQL 컬럼 목록 테스트, 원자성 전용 고장 주입 테스트, 500 고장 주입 테스트, 응답 키 집합 테스트 | 각각 REQ-RACKBATCH-014, REQ-RACKBATCH-013, REQ-RACKBATCH-015, REQ-RACKBATCH-008의 판별력 있는 커버리지(plan-auditor D7-R/D12/D13). |

## 설계 결정

### 결정 A — 참조 구현의 판정 규칙은 승계하지 않는다 (핵심 구현 함정)

`_process_outbound_rows`는 하나의 `(order, sku)` 키가 LineItem 2건 이상과 매칭되면
`multiple_line_items`로 **거부**한다(`purchase_order_views.py:2582-2594`, SPEC-ORDER-015
설계 결정 A). 렉번호 엔드포인트의 계약은 정반대다 — SPEC-ORDER-013 결정 E에 따라 여러
LineItem이 매칭되면 **전부** 같은 `rack_number`를 받고, `matched_count`는 여전히 그 키를
1로 센다. 이는 `test_upload_multiple_lineitems_matching_key_all_updated`
(`backend/order/tests/test_spec_013.py:748-764`)로 이미 pin되어 있다.

따라서 배치 재작성은 `(order_id, sku)` 그룹핑 결과에서 후보 리스트가 **1건 이상이면 전부**
갱신 대상에 포함해야 한다 — `_process_outbound_rows`의 "정확히 1건만 허용" 분기를 그대로
복사하면 이 SPEC의 핵심 계약이 깨진다(REQ-RACKBATCH-006).

### 결정 B — 동명 `Order.name` 해석은 기존 최저 `pk` 관례를 재현한다

`Order.name`은 유일 제약이 없다(`Order.Meta.unique_together`는
`(shopify_order_id, store_type)`). 현재 `.filter(name=order_name).first()`는 정렬 없는
쿼리셋에 대한 Django의 암묵적 `ORDER BY pk` 폴백으로 사실상 "최저 pk 선점"을 얻고 있다.
배치 조회로 전환하면서 이 암묵적 동작을 유지하려면 `order_by("pk")` + `setdefault`
조합이 필요하다 — `_process_outbound_rows`(`purchase_order_views.py:2532-2538`)가 이미
같은 패턴을 쓰며, 그 근거는 같은 파일의 주석(`:2524-2531`)에 명시되어 있다.

같은 파일에는 이미 이 tie-break를 추출한 공유 헬퍼 `_resolve_orders_by_name`
(`purchase_order_views.py:2812-2829`)이 존재한다(SPEC-ORDER-016이 추출). 구현 시 이 헬퍼를
재사용하면 tie-break 로직을 세 번째로 복제하지 않을 수 있다(`plan.md` 참조) — 다만 재사용
여부는 구현 계획 사항이며 이 REQ의 규범적 요구는 "최저 pk 선점"이라는 관측 가능한 동작이다.

### 결정 C — 빈 문자열 `rack_number`는 명시적 초기화 값으로 계속 보존한다

`parse_rack_number_excel`의 docstring(`backend/order/excel_utils.py:994`, 본문
`:1018-1026`)은 빈 문자열 `rack_number`가 "이 렉번호를 지운다"는 명시적 신호이며 falsy로
걸러져서는 안 된다고 규정한다. 배치 재작성이 `if row["rack_number"]:` 같은 조건으로 걸러내면
이 계약이 깨진다 — 갱신 대상 판단은 오직 "후보 LineItem이 존재하는가"에만 의존해야 한다.

### 결정 D — 행 단위 락(`select_for_update`)은 도입하지 않는다

렉번호 엔드포인트는 현재도 락 없이 갱신하며, 이는 `@MX:WARN`/`@MX:REASON`
(`purchase_order_views.py:2415-2422`)에 문서화된 기존에 수용된 격차다 — 그 REASON은
`UploadRackNumberView`를 이 패턴의 원조로 명시적으로 지목한다. 배치 전환은 쿼리 수만
바꿀 뿐 동시성 특성을 악화시키지 않으므로, 이 SPEC에서 락을 새로 도입할 근거가 없다. 락
도입이 필요한 `ConfirmOrderView`(`:841`, 항목별 `select_for_update()` 조회가 `:918-925`에
있음)는 구조가 근본적으로 다르며 범위 밖이다.

### 결정 E — 신규 인덱스·마이그레이션을 추가하지 않는다

`Order.name`은 이미 인덱스가 있다(`backend/order/models.py` `Order.Meta.indexes`의
`models.Index(fields=["name"])`, `:110`) — 그 위 주석(`:100-109`)이 정확히 이 엔드포인트류의
배치 조회를 근거로 추가되었다고 기록한다. `LineItem.sku`는 단독 인덱스가 없지만, 배치 조회는
인덱스가 있는 `order_id__in`으로 먼저 좁혀지므로(`LineItem.order`는 `ForeignKey`) 이 SPEC의
배치 규모에서 충분하다(`research.md` §6). 신규 인덱스는 범위 밖이다.

### 결정 F — `_recompute_order_aggregates` 미호출은 배치 전환 후에도 유지한다

`test_upload_never_calls_recompute_order_aggregates`
(`backend/order/tests/test_spec_013.py:842-855`)가 이미 `patch(...) + assert_not_called()`로
이를 pin하고 있다. 배치 재작성이 `bulk_update()`로 전환되더라도 이 호출을 도입해서는 안 된다
(REQ-RACKBATCH-012).

### 결정 G — 처리되지 않은 예외의 500 응답을 REQ로 승격한다

기존 `UploadRackNumberView.post()`는 `dedup-키` 순회 전체를 `try/except Exception`으로
감싸 처리되지 않은 예외를 HTTP 500으로 변환한다(`purchase_order_views.py:2216-2261`, 전체
`try`는 `:2216`에서 시작해 `except` 블록이 `:2261`에서 끝난다). 이 관측 가능한 동작 —
"예외가 발생하면 500을 반환하고 부분 반영을 남기지 않는다" — 은 v1.0.0에서는 문제 정의·
솔루션 개요에만 서술되고 REQ로 승격되지 않아, `acceptance.md`가 이를 주장하는데도 대응하는
REQ가 없는 상태였다(plan-auditor D6). 배치 재작성도 이 경로를 그대로 유지해야 하므로
REQ-RACKBATCH-015로 승격한다(모듈 4 보충 절 참조).

### 결정 H — 로직을 모듈 레벨 순수 함수로 추출한다 (v1.0.2, 사용자 결정)

v1.0.1까지의 계획은 배치 조회 로직을 `UploadRackNumberView.post()` 안에서 직접 재작성하는
것이었다. 이 구조에서는 쿼리 카운트를 측정할 수 있는 지점이 HTTP 엔드포인트뿐이고, 엔드포인트는
`authentication_classes = [JWTAuthentication]`(`purchase_order_views.py:2177`, 클래스 임포트는
`:47`)를 거친다 — 인증된 모든 요청은 `JWTAuthentication.get_user()`가 사용자 조회 쿼리 1건을
추가로 발생시키며, 프로젝트 어디에도 `ATOMIC_REQUESTS`가 설정되어 있지 않아 이를 상쇄할 요청
단위 세이브포인트도 없다. 기존 테스트는 전부 `auth_client`(`test_spec_013.py:76-79`, 실제 JWT
Bearer 토큰을 발급해 세팅)를 통해 이 엔드포인트를 호출한다.

이 구조적 제약이 plan-auditor D2(쿼리 카운트 AC가 참조 구현과 다른 측정 맥락에서 숫자만
가져와 검증 불가), D7-R(쓰기 범위 검증이 값 스냅샷 수준에 머물러 SQL 자체를 관측할 수단이
없음), D12(원자성 주입 지점을 함수 경계 밖인 뷰에서 흉내 내려다 보니 판별력을 잃음) 세 결함의
공통 원인이었다.

따라서 SPEC-ORDER-015의 `_process_outbound_rows`(`:2423-2714`)와 SPEC-ORDER-016의
`_process_force_outbound_rows`(`:3021-`, 시그니처 `def _process_force_outbound_rows(rows:
list[dict]) -> dict`, 호출부는 `OutboundForceProcessView.post()` 단 하나)가 이미 확립한
"모듈 레벨 순수 함수 하나가 로직 전체를 소유하고 뷰는 얇은 래퍼"라는 이 파일의 기존 아키텍처
관례를 그대로 따라, dedup·배치 조회·판정·`transaction.atomic()`·`bulk_update`를 전부
소유하는 모듈 레벨 순수 함수 `_process_rack_number_rows(rows: list[dict]) -> dict`를
추출한다:

- **입력**: `parse_rack_number_excel`이 반환하는 원본 dict 리스트 그대로 — dedup은 뷰가 아니라
  이 함수가 수행한다(`_process_outbound_rows`도 자신의 그룹핑 패스를 스스로 소유하는 것과
  동일한 원칙).
- **출력**: `{"matched_count": int, "skipped_count": int}`.
- **호출부는 정확히 하나** — `UploadRackNumberView.post()`뿐이다. 이것은 새로운 추상화
  계층이 아니라 테스트 가능성 확보와 `_process_outbound_rows`/`_process_force_outbound_rows`
  와의 아키텍처 정합을 위한 리팩터링이다.
- `UploadRackNumberView.post()`는 파일 존재 확인 → `.xlsx` 확장자 확인 → 파싱(`ValueError`
  → 422) → 이 함수 호출 → 반환된 dict를 `Response(..., 200)`으로 포장하는 얇은 래퍼가 되며,
  기존 `except Exception` → 500 가드는 그대로 유지한다.
- 재작성 대상 루프 안에 있던 기존 `@MX:WARN`/`@MX:REASON`(`:2218-2226`, 결정 E 다중 매칭
  경고, plan-auditor D8이 이관을 요구)은 이 새 함수의 **본문 안**, 다중 매칭 판정이 실제로
  일어나는 지점으로 옮긴다(`plan.md` mx_plan 참조) — 함수가 결정 E의 다중 매칭 조건을
  판정하는 새로운 자리이기 때문이다.

이 추출로 AC-RACKBATCH-001은 `_process_rack_number_rows(rows)`를 `CaptureQueriesContext`로
직접 감싸 측정할 수 있게 되어(`test_spec_015.py:1118-1121`이 `_process_outbound_rows`를
측정하는 것과 동일한 기법), HTTP·인증 쿼리가 섞이지 않는다. AC-RACKBATCH-011/012도 이제
함수를 직접 호출해 SQL 레벨/실패-주입 시나리오를 판별력 있게 구성할 수 있다.

## 요구사항 (EARS)

요구사항은 5개 모듈, REQ-RACKBATCH-001부터 REQ-RACKBATCH-014까지 연속 번호로 구성되며,
예외 처리 경로를 규범화하는 REQ-RACKBATCH-015(모듈 4 소속)가 번호 보존을 위해 문서 뒷부분에
추가되었다(설계 결정 G).

### 모듈 1 — 쿼리 배치 불변식

**REQ-RACKBATCH-001** (Ubiquitous): The system shall issue a number of database queries for a
rack-number upload request that does not grow with the number of distinct
`(order_name, sku)` dedup keys in the uploaded file — specifically at most one `Order`
lookup, one `LineItem` lookup, and one write operation, regardless of how many dedup keys
the request carries. The system shall issue none of the three when there is nothing for that
lookup or write to act on — specifically, the `Order` lookup shall not be issued when the
batch resolves to zero dedup keys, the `LineItem` lookup shall not be issued when the `Order`
lookup finds no matching Order, and the write shall not be issued when no LineItem is staged
for update. (D16: this "issue none when there is nothing to look up" clause is what makes
"at most one" strict enough to entail zero-on-empty; without it, an unconditional `Order`
lookup on every batch would satisfy the "at most one" wording while still breaking the empty
and all-unmatched query-count ceilings AC-RACKBATCH-001 requires.)

**REQ-RACKBATCH-002** (Ubiquitous): The system shall issue an identical number of database
queries when processing a 2-key batch and a 10-key batch, so that a batch five times larger
does not incur any additional query.

### 모듈 2 — 매칭·중복 제거 시맨틱 보존

**REQ-RACKBATCH-003** (Event-Driven): When two or more parsed rows share the same
`(order_name, sku)` key, the system shall apply only the rack_number value of the
last such row among them, exactly as the existing per-row implementation does.

**REQ-RACKBATCH-004** (Event-Driven): When the system resolves an order identifier to an
`Order` for matching, the system shall use exact `Order.name` string equality and, when two
or more Orders share that name, shall select the Order with the lowest `pk` among them.

**REQ-RACKBATCH-005** (State-Driven): While a parsed row's order-identifier cell is blank,
the system shall not merge that row with any other blank-identifier row under a shared key,
and shall count each such row individually toward `skipped_count`.

### 모듈 3 — 반영 규칙 보존 (결정 E 승계, 결정 A 비승계)

**REQ-RACKBATCH-006** (Event-Driven): When a dedup key's `(order_name, sku)` pair matches one
or more LineItems belonging to the resolved Order, the system shall apply that key's
rack_number value to every matching LineItem, and shall count that key exactly once toward
`matched_count` regardless of how many LineItems it updates — the system shall NOT reject a
key on the grounds that it matches more than one LineItem.

**REQ-RACKBATCH-007** (Ubiquitous): The system shall treat an empty string rack_number value
as an explicit instruction to clear the field and shall apply it to matching LineItems the
same way it applies any non-empty value — the system shall NOT skip or filter out a row on
account of its rack_number value being empty.

### 모듈 4 — 응답 계약·오류 처리·부수효과 보존

**REQ-RACKBATCH-008** (Ubiquitous): The system shall return the same response schema the
existing endpoint returns — a JSON object with exactly `matched_count` and `skipped_count`
integer fields — and no additional or renamed field.

**REQ-RACKBATCH-009** (Unwanted): If the uploaded file does not have a `.xlsx` extension,
then the system shall respond with HTTP 400 without attempting to read or parse the file.

**REQ-RACKBATCH-010** (Unwanted): If the uploaded file cannot be parsed — because it is
corrupted, empty, or missing a required header column — then the system shall respond with
HTTP 422 and shall modify no LineItem.

**REQ-RACKBATCH-011** (Unwanted): If the request is unauthenticated, then the system shall
respond with HTTP 401 without modifying any LineItem.

**REQ-RACKBATCH-012** (Ubiquitous): The system shall never invoke the order-aggregate
recomputation routine while processing a rack-number upload request.

### 모듈 5 — 원자성과 쓰기 범위

**REQ-RACKBATCH-013** (Ubiquitous): The system shall apply a single rack-number upload
request within one atomic transaction, so that if processing fails partway through, no
partially-applied rack_number change persists.

**REQ-RACKBATCH-014** (Ubiquitous): The system shall write only the `rack_number` field of
the LineItems it updates while processing a rack-number upload request — no other LineItem
field, and no Order field, shall change as a result of this operation.

### 모듈 4 보충 — 예외 처리 경로

REQ-RACKBATCH-015는 성격상 모듈 4(응답 계약·오류 처리·부수효과 보존)에 속하지만, 기존
001~014 번호를 재번호하지 않기 위해 문서 뒷부분에 배치한다(설계 결정 G).

**REQ-RACKBATCH-015** (Unwanted): If processing a rack-number upload request raises an
exception that is not one of the handled parse/authentication/extension failures covered by
REQ-RACKBATCH-009 through REQ-RACKBATCH-011, then the system shall respond with HTTP 500 and
shall persist no partially-applied rack_number change.

---

## ACCEPTANCE CRITERIA

각 인수 기준은 대응 요구사항이 이미 말한 내용을 되풀이하지 않고 구체적 픽스처·경계값으로
관측 가능한 결과를 제시한다. 실행 가능한 Given/When/Then 시나리오는 `acceptance.md`에 있으며,
동일한 `Traces:` 목록을 인용한다.

**AC-RACKBATCH-001** (Event-Driven) — Traces: REQ-RACKBATCH-001, REQ-RACKBATCH-002. **Scope**:
this AC measures `_process_rack_number_rows(rows)` directly under `CaptureQueriesContext` —
the same measurement context `test_spec_015.py:1118-1121` uses for `_process_outbound_rows`.
No HTTP request is made and no authentication query is issued. When processing a 2-key batch
and, separately, a 10-key batch of otherwise-matching rows, the system shall issue the same
number of database queries for both — the primary proof of O(1) behavior — and that shared
number shall not exceed 6 (derivation: 1 `Order` fetch + 1 `LineItem` fetch + 1 `bulk_update`
+ the savepoint/release pair `transaction.atomic()` emits inside the test's own wrapping
transaction = 5 actual queries, `+1` safety margin = 6, mirroring the identical margin
`test_spec_015.py:1143-1147` applies to the structurally identical case). When processing a
batch whose 10 keys each target a non-existent `Order.name` (all-unmatched via absent order,
not via an unmatched SKU on an existing order — the two flavors produce different counts),
the system shall issue no `LineItem` lookup and no write query, and the total shall not
exceed 4 (derivation: 1 `Order` fetch + savepoint/release pair = 3 actual, `+1` margin = 4,
mirroring `test_spec_015.py:1149-1153`). When processing an empty upload (zero rows, hence an
empty dedup map), the system shall issue no `Order` or `LineItem` lookup and no write query,
and the total shall not exceed 2 (derivation: the function still enters
`transaction.atomic()` unconditionally — see spec.md 솔루션 개요 step 3 — so exactly the
savepoint/release pair is emitted, with no margin, mirroring
`test_spec_015.py:1155-1157`). These bounds hold only if the implementation guards the
`Order` fetch, the `LineItem` fetch, and the `bulk_update` exactly as
`_process_outbound_rows` does (`purchase_order_views.py:2533` `if grouped:`, `:2550`
`if orders_by_name:`, `:2701` `if to_update:`) — REQ-RACKBATCH-001 requires the same guard
structure in `_process_rack_number_rows`.

**AC-RACKBATCH-002** (Event-Driven) — Traces: REQ-RACKBATCH-006. Given an Order with two
LineItems sharing the same SKU, when a single upload row targets that `(order_name, sku)`
key, the system shall set the same rack_number on both LineItems and shall report
`matched_count == 1`.

**AC-RACKBATCH-003** (Event-Driven) — Traces: REQ-RACKBATCH-004. Given two Orders sharing the
same `name`, where the Order with the lower `pk` was created later, when an upload row
targets that name, the system shall apply the rack_number to the lower-`pk` Order's matching
LineItem.

**AC-RACKBATCH-004** (Event-Driven) — Traces: REQ-RACKBATCH-007. Given a LineItem whose current
`rack_number` is `"A-01"`, when an upload row targets it with an empty-string rack_number,
the system shall clear the field to `""` rather than leaving it unchanged or skipping the
row.

**AC-RACKBATCH-005** (Unwanted) — Traces: REQ-RACKBATCH-010. If an uploaded `.xlsx` file is
corrupted, empty, or missing a required header column, then the system shall respond with
HTTP 422 and shall leave an existing LineItem's `rack_number` unchanged from its
pre-upload value.

**AC-RACKBATCH-006** (Event-Driven) — Traces: REQ-RACKBATCH-003. Given two rows in the
uploaded file that share the same `(order_name, sku)` key with different rack_number values,
when the file is processed, the system shall apply only the value from the later row.

**AC-RACKBATCH-007** (State-Driven) — Traces: REQ-RACKBATCH-005. While two or more parsed rows
in the same upload carry a blank order-identifier cell, the system shall treat each one
individually rather than merging any of them together under a shared key. Given three rows —
two with a blank order-identifier cell that carry the **same SKU** as each other, and one
valid, distinct row — when the file is processed, the system shall report `skipped_count == 2`
(one per blank row, not one for both combined) alongside `matched_count == 1` for the valid
row. The two blank rows must share one SKU: a `(None, sku)`-keyed implementation would collapse
them into a single key and report `skipped_count == 1`, identical to a correct `(None, idx)`
implementation only when the SKUs differ — sharing the SKU is what makes the two
implementations diverge and therefore what makes this AC discriminating.

**AC-RACKBATCH-008** (Event-Driven) — Traces: REQ-RACKBATCH-012. When a rack-number upload
request transitions a LineItem's `rack_number`, the system shall never invoke
`_recompute_order_aggregates`, verified the same way the existing
`test_upload_never_calls_recompute_order_aggregates` test does (patch + assert not called).

**AC-RACKBATCH-009** (Unwanted) — Traces: REQ-RACKBATCH-015. If processing raises an
unhandled exception at any point before `_process_rack_number_rows` returns, then the system
shall respond with HTTP 500. (This AC proves the 500 response is genuinely observable. It
does NOT prove atomicity — see AC-RACKBATCH-012 for the discriminating atomicity test.)

**AC-RACKBATCH-012** (Unwanted) — Traces: REQ-RACKBATCH-013. **Scope**: like AC-RACKBATCH-001
and AC-RACKBATCH-011, this AC calls `_process_rack_number_rows(rows)` directly — no HTTP
request, no view. Given a batch with two matching keys, if an exception is raised immediately
after the single `bulk_update` call has actually executed against the database — so the
`UPDATE` statement has run inside the still-open `transaction.atomic()` block — but before
that block exits, then the exception shall propagate to the caller, and a query issued after
the call returns (a fresh read, on the same or a new connection, outside the now-rolled-back
transaction) shall show both LineItems' `rack_number` unchanged from their pre-call values.
This is discriminating: if `transaction.atomic()` were removed, no savepoint would exist for
the later exception to unwind, so the `bulk_update`'s already-executed write would remain
visible to that subsequent read — failing this AC. An injection point before the write (as in
an earlier draft of this SPEC) cannot distinguish these two cases, because nothing has been
written yet either way; this AC's injection point is deliberately placed after the write
completes for exactly that reason.

**AC-RACKBATCH-010** (Ubiquitous) — Traces: REQ-RACKBATCH-008, REQ-RACKBATCH-009,
REQ-RACKBATCH-011. The system shall continue to return, on success, a response body whose key
set is **exactly** `{"matched_count", "skipped_count"}` — verified by a new assertion, since
no existing test asserts the key set (an added third field would pass every existing
characterization test unnoticed). HTTP 400 for a non-`.xlsx` upload before any file read, and
HTTP 401 for an unauthenticated request, remain verified by the existing characterization
tests passing unmodified.

**AC-RACKBATCH-011** (Ubiquitous) — Traces: REQ-RACKBATCH-014. **Scope**: like AC-RACKBATCH-001,
this AC calls `_process_rack_number_rows(rows)` directly — no HTTP request. The system shall
write only the `rack_number` column when persisting a rack-number upload's matched LineItems.
This has two independent observations, because a value-snapshot alone cannot detect an
over-broad `bulk_update` field list (writing back a field's just-read value produces an empty
diff even when that field should never have been listed):
(a) *SQL-level*: capturing queries with `CaptureQueriesContext` around a call to
`_process_rack_number_rows` that matches and updates a LineItem, the only column **assigned**
in the emitted `UPDATE` statement's `SET` clause shall be `rack_number` — i.e. the left-hand
side of every `SET` assignment, not every column referenced anywhere in the clause. (Django's
`bulk_update` renders `SET rack_number = CASE WHEN "id" = … THEN … END`; the `id` column
appears inside the `CASE WHEN` condition, not as a `SET` assignment target, and must not trip
this check — only a second assigned column such as `shipped_quantity` should.)
(b) *Value-level*: for a LineItem seeded with non-default values in `title`, `quantity`,
`price`, `purchase_status`, `logistics_status`, `shipped_quantity`, and `shipped_at`, every
one of those seven fields — snapshotted immediately before and after a call to
`_process_rack_number_rows` that updates that LineItem's `rack_number` — shall remain
byte-identical. This clause alone catches an implementation that *changes* another field's
value (e.g. copying `_process_outbound_rows`' `logistics_status` transition); it does not by
itself catch an over-broad field list, which is why (a) is required.

### Traceability 검증표

| REQ | AC |
|---|---|
| REQ-RACKBATCH-001 | AC-RACKBATCH-001 |
| REQ-RACKBATCH-002 | AC-RACKBATCH-001 |
| REQ-RACKBATCH-003 | AC-RACKBATCH-006 |
| REQ-RACKBATCH-004 | AC-RACKBATCH-003 |
| REQ-RACKBATCH-005 | AC-RACKBATCH-007 |
| REQ-RACKBATCH-006 | AC-RACKBATCH-002 |
| REQ-RACKBATCH-007 | AC-RACKBATCH-004 |
| REQ-RACKBATCH-008 | AC-RACKBATCH-010 |
| REQ-RACKBATCH-009 | AC-RACKBATCH-010 |
| REQ-RACKBATCH-010 | AC-RACKBATCH-005 |
| REQ-RACKBATCH-011 | AC-RACKBATCH-010 |
| REQ-RACKBATCH-012 | AC-RACKBATCH-008 |
| REQ-RACKBATCH-013 | AC-RACKBATCH-012 |
| REQ-RACKBATCH-014 | AC-RACKBATCH-011 |
| REQ-RACKBATCH-015 | AC-RACKBATCH-009 |

요구사항 15개 전량이 최소 1개의 인수 기준에 대응한다(미커버 REQ 없음). AC는 12개로,
REQ-RACKBATCH-013(원자성)과 REQ-RACKBATCH-015(500 경로)가 각각 별도의 판별력 있는 AC
(AC-RACKBATCH-012, AC-RACKBATCH-009)로 분리되어 있다(plan-auditor D12).

---

## Exclusions (What NOT to Build)

- **응답 스키마 변경 없음** — `{matched_count, skipped_count}` 두 필드만 유지한다. 출고
  엔드포인트의 `unmatched` 사유별 상세(`reason` 필드 등)는 렉번호 엔드포인트로 이식하지
  않는다.
- **행 단위 락(`select_for_update`) 도입 없음** — 기존에 수용된, 이 SPEC이 악화시키지 않는
  격차다(설계 결정 D).
- **프론트엔드 변경 없음** — 진행률 바, 퍼센트 UI, axios 타임아웃 설정 어느 것도 추가하지
  않는다. 응답 계약이 바뀌지 않으므로 프론트엔드 코드는 수정하지 않는다.
- **신규 DB 인덱스·마이그레이션 없음**(설계 결정 E).
- **`parse_rack_number_excel` 변경 없음** — 파서는 그대로 유지한다.
- **`ConfirmOrderView` 또는 다른 엔드포인트의 배치화 작업 없음** — 구조가 다르거나(락 보유)
  이미 배치화되어 있다. 범위는 오직 `UploadRackNumberView`다.
- **`_process_rack_number_rows` 외 추가 계층·클래스 없음** — 설계 결정 H의 추출은
  `_process_outbound_rows`/`_process_force_outbound_rows`가 이미 확립한 관례를 따르는
  리팩터링이며, 서비스 클래스·매니저·별도 모듈 분리 같은 새로운 추상화 계층을 도입하지
  않는다. 함수는 `purchase_order_views.py` 안에 그대로 둔다.

## 관련 SPEC

- **SPEC-ORDER-013**: `rack_number` 필드와 `UploadRackNumberView`의 원 SPEC. 결정 E(2+
  LineItem 매칭 시 전부 갱신)의 근원이며, 이 SPEC은 그 규칙을 그대로 승계한다.
- **SPEC-ORDER-014**: `Order.name` 기반 매칭 관례의 후속 정정(same-day follow-up)이 이
  엔드포인트에 반영되어 있다. 이 SPEC은 매칭 기준을 변경하지 않는다.
- **SPEC-ORDER-015**: `_process_outbound_rows`의 배치 조회 패턴(Order `name__in` + LineItem
  `order_id__in`/`sku__in` + `bulk_update`)이 이 SPEC이 재사용하는 참조 구현이다. 단, 2+
  매칭 거부 규칙(결정 A)은 승계하지 않는다(본 문서 설계 결정 A).
- **SPEC-ORDER-016**: `_resolve_orders_by_name` 공유 헬퍼와 `_process_force_outbound_rows`
  (`:3021-`)를 확립한 SPEC. 전자는 tie-break 재사용 후보(설계 결정 B), 후자는 "모듈 레벨
  순수 함수 + 얇은 뷰 래퍼" 아키텍처의 두 번째 선례로 설계 결정 H가 인용한다.
