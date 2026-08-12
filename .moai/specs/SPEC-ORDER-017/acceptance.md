---
id: SPEC-ORDER-017
document: acceptance
version: 1.0.3
status: draft
updated: 2026-08-12
---

# 인수 기준 — SPEC-ORDER-017 렉번호 엑셀 업로드 배치 처리

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의
AC-RACKBATCH-XXX / REQ-RACKBATCH-XXX ID를 인용해 상호 추적된다.

[HARD] 각 시나리오의 `Traces:` 목록은 `spec.md` ACCEPTANCE CRITERIA 절의 동일 AC 항목이
선언한 것과 완전히 일치한다. 어느 한쪽을 수정할 때 반드시 함께 갱신한다. **(v1.0.2 정정,
D15)**: `spec.md`의 AC 항목은 EARS 패턴 라벨만 붙어 있고 검증 레이어 마커(`[BE]` 등)를
따로 붙이지 않으므로, 이 동등성 요구는 `Traces:` 목록에만 적용된다 — 레이어 표기는
`spec.md`와 비교 대상이 아니다.

**검증 레이어와 호출 스코프**: 이 SPEC은 백엔드 전용 변경이므로 전 시나리오가 `[BE]`다.
단, 시나리오마다 호출 스코프가 다르다 — **[함수]** 표기는
`_process_rack_number_rows(rows)`를 직접 호출하는 시나리오(HTTP 없음, 인증 쿼리 없음),
**[뷰]** 표기는 `auth_client.post(...)`로 `/api/purchase-orders/upload-rack-number/`를
호출하는 시나리오다. AC-RACKBATCH-001/003/011/012는 `[함수]` 전용이다. AC-RACKBATCH-009는
주입은 함수 레벨에서 하되 관측(HTTP 500)은 뷰를 통해야 하므로 `[함수+뷰]`다.
AC-RACKBATCH-007은 두 레이어 모두에서 판별력이 성립하므로 `[뷰 또는 함수]`로 구현자가
선택한다(**v1.0.3 정정, D20** — 이전 버전은 이 문장에서 AC-007을 "나머지"에 포함시켜 암묵적으로
`[뷰]` 전용으로 읽혔으나, 아래 AC-RACKBATCH-007 자신의 표제와 품질 게이트 절의 DoD 표는
이미 `[뷰 또는 함수]`로 선언하고 있었다 — 세 서술을 여기서 일치시킨다). 그 외
나머지(AC-002/004/005/006/008/010)는 `[뷰]` 전용이다(spec.md 설계 결정 H, plan-auditor D2).

공통 전제(별도 명시가 없는 한, `[뷰]` 시나리오에 한함): 인증된 담당자가
`/api/purchase-orders/upload-rack-number/`에 `.xlsx` 파일을 업로드한다.

## 쿼리 배치 불변식

### AC-RACKBATCH-001 — 2-키 배치와 10-키 배치의 쿼리 수가 동일하다 `[BE][함수]`

Traces: REQ-RACKBATCH-001, REQ-RACKBATCH-002

**스코프**: 이 시나리오는 `_process_rack_number_rows(rows)`를 직접 호출한다 — HTTP 요청도,
`JWTAuthentication`이 발생시키는 사용자 조회 쿼리도 없다(`test_spec_015.py:1118-1121`이
`_process_outbound_rows`를 측정하는 것과 동일한 기법). v1.0.1에서는 이 AC가 엔드포인트
레벨로 서술되어 있어 인증 쿼리가 상한에 반영되지 않은 채 참조 스위트의 숫자만 옮겨온
결함이 있었다(plan-auditor D2) — 함수 추출(spec.md 설계 결정 H)로 이 문제 자체가 해소된다.

- **Given**: 서로 다른 2개 Order + LineItem 쌍을 대상으로 하는 2-키 배치와, 서로 다른 10개
  Order + LineItem 쌍을 대상으로 하는 10-키 배치를 각각 준비한다(각 키는 정확히 1개
  LineItem과 매칭). 별도로, 10개 키가 **전부 존재하지 않는 `Order.name`을 가리키는**
  전량 미매칭 배치(`test_spec_015.py:1151`의 `#MISSING{i}` 패턴과 동일 — SKU 미발견이
  아니라 주문 자체가 없는 경우로 한정한다, D2b)와, 빈 업로드(`rows == []`)도 준비한다.
- **When**: `CaptureQueriesContext`로 감싸 `_process_rack_number_rows(rows)`를 각 배치에
  대해 직접 호출한다.
- **Then**: (1차 증거, 필수) 2-키 배치와 10-키 배치가 발생시키는 쿼리 수가 **동일**하다 —
  5배 큰 입력이 쿼리를 하나도 더 쓰지 않는다. (2차 증거, 절대 상한, D2 도출) 그 동일한 수는
  **6을 넘지 않는다** — savepoint(1) + `Order` 조회(1) + `LineItem` 조회(1) + `bulk_update`
  (1) + release(1) = 실측 5, 안전 여유 +1(`test_spec_015.py:1143-1147`과 동일한 여유 관례).
  부재-`Order.name` 전량 미매칭 배치는 `LineItem` 조회와 쓰기 쿼리를 전혀 발생시키지 않으며
  총 쿼리 수는 **4를 넘지 않는다** — savepoint(1) + `Order` 조회(1) + release(1) = 실측 3,
  안전 여유 +1(`test_spec_015.py:1149-1153`과 동일). 빈 업로드는 `Order`/`LineItem` 조회를
  전혀 발생시키지 않으며 총 쿼리 수는 **2를 넘지 않는다** — savepoint(1) + release(1) =
  실측 2, 여유 없음(`test_spec_015.py:1155-1157`과 동일; `transaction.atomic()`은 빈
  입력에도 조건 없이 진입하므로 이 두 쿼리는 항상 발생한다). 이 세 상한이 성립하려면 구현이
  `Order` 조회를 `if grouped:`류로, `LineItem` 조회를 `if orders_by_name:`류로, `bulk_update`
  를 `if to_update:`류로 감싸야 한다(`purchase_order_views.py:2533`, `:2550`, `:2701`이
  `_process_outbound_rows`에서 쓰는 동일한 가드) — REQ-RACKBATCH-001이 이 가드 구조를
  요구한다.

## 반영 규칙 보존

### AC-RACKBATCH-002 — 결정 E: 한 키에 매칭되는 LineItem이 여럿이면 전부 갱신된다 `[BE][뷰]`

Traces: REQ-RACKBATCH-006

- **Given**: `Order.name="#40005"`인 Order 아래 동일 SKU `"SKU-MULTI"`를 가진 LineItem이
  2건(`li1`, `li2`) 존재한다.
- **When**: `("#40005", "SKU-MULTI", "SHELF-1")` 행 1개를 업로드한다.
- **Then**: `matched_count == 1`이며, `li1.rack_number`와 `li2.rack_number` **둘 다**
  `"SHELF-1"`이 된다. 배치 재작성이 이 키를 `multiple_line_items`류로 거부하지 **않는다**.

### AC-RACKBATCH-003 — 동명 `Order.name`은 최저 `pk`로 해소된다 `[BE][함수]`

Traces: REQ-RACKBATCH-004

- **Given**: `Order.name="#40020"`인 Order가 2건 존재한다. `pk`가 더 작은 O1을 **더 나중에**
  생성해 `pk` 순서와 생성 일시 순서를 어긋나게 만든다. O1과 O2는 서로 다른 LineItem 집합을
  갖는다.
- **When**: `("#40020", <O1의 SKU>, "B-01")` 행 하나로 `_process_rack_number_rows`를 직접
  호출한다.
- **Then**: 갱신은 O1(최저 `pk`)의 LineItem에만 반영된다 — 생성 일시 순서는 판정에 영향을
  주지 않는다. 배치 조회가 정렬 없이 진행되었다면 이 테스트는 MySQL의 반환 순서에 따라
  간헐적으로 실패했을 것이다.

### AC-RACKBATCH-004 — 빈 문자열 rack_number는 명시적 초기화로 반영된다 `[BE][뷰]`

Traces: REQ-RACKBATCH-007

- **Given**: `rack_number="A-01"`인 LineItem이 존재하는 Order/SKU 조합이 있다.
- **When**: 같은 `(order_name, sku)`를 가리키되 렉번호 셀이 빈 문자열인 행을 업로드한다.
- **Then**: `matched_count == 1`이며, 해당 LineItem의 `rack_number`가 `""`로 갱신된다 —
  건너뛰거나(skipped) 기존 값 `"A-01"`을 유지하지 않는다.

### AC-RACKBATCH-006 — 동일 키 중복 행은 마지막 행이 우선한다 `[BE][뷰]`

Traces: REQ-RACKBATCH-003

- **Given**: `Order.name="#40004"`, SKU `"SKU-DUP"`를 가진 LineItem 1건이 있다.
- **When**: `("#40004", "SKU-DUP", "FIRST")`와 `("#40004", "SKU-DUP", "LAST")` 두 행을 이
  순서로 업로드한다.
- **Then**: `matched_count == 1`이며 LineItem의 `rack_number`는 `"LAST"`가 된다(`"FIRST"`가
  아님).

### AC-RACKBATCH-007 — 빈 주문 식별자 행 2건(동일 SKU)은 병합 없이 개별적으로 skipped 처리된다 `[BE][뷰 또는 함수]`

Traces: REQ-RACKBATCH-005

[HARD] 이 시나리오의 빈 식별자 행 2건은 **동일한 SKU**를 가져야 한다. **(v1.0.2 정정,
D4-R)**: v1.0.1은 "서로 다른 SKU"로 서술했는데, 이는 판별력이 없다 — SKU가 다르면 잘못된
`(None, sku)` 병합 구현도 `(None, "SKU-X")`와 `(None, "SKU-Y")`라는 별개의 두 키를 만들어
`skipped_count == 2`를 반환하므로 올바른 `(None, idx)` 구현과 결과가 같아진다. 두 빈 행이
**같은** SKU를 가져야만 `(None, sku)` 구현이 `(None, "동일SKU")` 하나로 병합되어
`skipped_count == 1`을 반환하고, `(None, idx)` 구현만 2를 반환한다 — 이 차이가 판별력의
근원이다. 기존 `test_spec_013.py:809-834`도 빈 행 1건만 다루므로 이 REQ의 판별 근거가 될 수
없다.

- **Given**: 주문 식별자 셀이 빈 행 **2개**(**동일 SKU**, 예: 둘 다 `"SKU-BLANK"`)와, 유효한
  별개의 `(order_name, sku)`를 가리키는 정상 행 1개를 담은 업로드 파일이 있다.
- **When**: 파일을 업로드한다(또는 파싱된 행 리스트로 `_process_rack_number_rows`를 직접
  호출한다).
- **Then**: `matched_count == 1`(정상 행), `skipped_count == 2`(빈 식별자 행 2건 각각) —
  두 빈 식별자 행이 동일 SKU임에도 하나의 키로 병합되어 `skipped_count == 1`로 축소되지
  않는다. 이 값이 잘못된 `(None, sku)`류 병합 구현과 올바른 `(None, idx)` 구현을 구별하는
  지점이다.

## 오류 경로와 부수효과

### AC-RACKBATCH-005 — 손상된 xlsx는 422를 반환하고 아무것도 쓰지 않는다 `[BE][뷰]`

Traces: REQ-RACKBATCH-010

- **Given**: 손상된(파싱 불가능한) `.xlsx` 바이너리와, 알려진 `rack_number` 값을 가진 기존
  LineItem이 있다.
- **When**: 손상된 파일을 업로드한다.
- **Then**: 응답 상태 코드는 422이며, 해당 LineItem의 `rack_number`는 업로드 이전 값 그대로
  변경되지 않는다.

### AC-RACKBATCH-008 — 주문 집계 재계산은 절대 호출되지 않는다 `[BE][뷰]`

Traces: REQ-RACKBATCH-012

- **Given**: 정상적으로 매칭되어 `rack_number`가 갱신되는 업로드 요청이 있다.
- **When**: `order.purchase_order_views._recompute_order_aggregates`를 `patch()`로 감시하며
  요청을 처리한다.
- **Then**: 응답은 200이고 LineItem은 갱신되지만, `_recompute_order_aggregates`는 단 한 번도
  호출되지 않는다(`spy.assert_not_called()`).

### AC-RACKBATCH-009 — 처리되지 않은 예외는 500을 반환한다 `[BE][함수+뷰]`

Traces: REQ-RACKBATCH-015

**(v1.0.2 정정, D12)**: 이 AC는 v1.0.1에서 원자성(REQ-013)과 500 경로(REQ-015)를 함께
주장했으나, 예외를 `bulk_update` **이전**에 주입해 원자성을 실제로 증명하지 못했다 —
`transaction.atomic()`을 제거해도 같은 결과가 나오기 때문이다(아무것도 쓰이지 않은
상태에서 "아무것도 안 바뀌었다"는 항상 참). 이 AC는 이제 500 경로만 추적한다. 원자성은
AC-RACKBATCH-012가 별도의, 판별력 있는 픽스처로 검증한다.

- **Given**: `_process_rack_number_rows`가 처리를 진행하던 중 처리되지 않은 예외를 일으키도록
  주입 지점을 구성한다(예: `Order` 조회 직후 예외를 던지는 patch).
- **When**: 뷰가 이 함수를 호출한다.
- **Then**: 응답 상태 코드는 500이다.

### AC-RACKBATCH-012 — bulk_update 이후 실패해도 원자성에 의해 롤백된다 `[BE][함수]`

Traces: REQ-RACKBATCH-013

**(v1.0.2 신설, D12)**: 원자성(REQ-RACKBATCH-013)을 판별력 있게 검증하는 유일한 AC. 예외를
쓰기가 실제로 일어난 **뒤**에 주입해야, `transaction.atomic()`이 있고 없고에 따라 결과가
달라진다.

- **Given**: 서로 다른 두 키를 매칭하는 배치가 있다(둘 다 정상적으로 매칭됨).
- **When**: `LineItem.objects.bulk_update`가 (패치되지 않은) 실제 구현을 먼저 호출해 `UPDATE`
  문을 실제로 실행시킨 **직후**, `transaction.atomic()` 블록이 종료되기 **전**에 예외를
  던지도록 patch한 상태에서 `_process_rack_number_rows`를 호출한다.
- **Then**: 예외가 호출자에게 전파된다. 그 직후(같은 요청/호출과는 별개의) 새 조회로 두
  LineItem을 다시 읽으면 `rack_number`가 요청 이전 값 그대로다 — `bulk_update`가 실제로 DB에
  `UPDATE`를 실행했음에도 그 변경이 남아 있지 않다. 이것이 판별력의 근원이다:
  **(v1.0.3 정정, D19)** `pytest.mark.django_db`에서는 테스트 전체가 이미 하나의 래핑
  트랜잭션 안에서 실행되므로 "커밋"은 애초에 일어나지 않는다 — `transaction.atomic()`이
  있으면 그 안에서 세이브포인트가 생성되고, 나중에 발생한 예외가 그 세이브포인트까지만
  롤백해 이미 실행된 `UPDATE`를 되돌린다. `transaction.atomic()`이 없었다면 되돌릴
  세이브포인트 자체가 없으므로, 이미 실행된 `UPDATE`는 래핑 트랜잭션 안에 그대로 남아
  이후 조회(같은 커넥션·같은 트랜잭션 안의 읽기)에서 변경된 값이 그대로 관측되었을 것이다
  (패치가 실제 UPDATE를 실행시킨 뒤에 예외를 던지므로, 원자성이 없으면 되돌릴 세이브포인트가
  없다는 것이 요지다 — "오토커밋"이 아니다).

### AC-RACKBATCH-010 — 응답 스키마와 400/401 경로는 그대로 유지된다 `[BE][뷰]`

Traces: REQ-RACKBATCH-008, REQ-RACKBATCH-009, REQ-RACKBATCH-011

**(v1.0.2 정정, D13)**: (a)의 "정확히 두 필드만"이라는 절반은 기존 특성화 테스트로 검증되지
않는다 — `test_upload_matches_and_updates_lineitem`(`test_spec_013.py:664-678`)은
`res.data["matched_count"]`/`res.data["skipped_count"]`의 **값**만 확인하고 응답의 **키
집합**은 확인하지 않으므로, 세 번째 필드가 추가되어도 이 테스트는 그대로 통과한다. 신규
키-집합 assertion이 필요하다.

- **Given**: (a) 정상 처리되는 업로드 요청, (b) `.xlsx`가 아닌 파일, (c) 미인증 클라이언트의
  요청.
- **When**: 세 가지를 각각 실행한다.
- **Then**: (a) 응답 본문의 키 집합이 **정확히** `{"matched_count", "skipped_count"}`와
  같다 — 신규 assertion으로 검증(`set(res.data.keys()) == {"matched_count",
  "skipped_count"}`류). (b) 파일을 읽거나 파싱하기 전에 HTTP 400을 반환한다 — 기존
  `test_upload_wrong_extension_returns_400`이 무수정으로 계속 통과함으로써 검증된다. (c)
  HTTP 401을 반환하며 아무 LineItem도 변경되지 않는다 — 기존
  `test_upload_unauthenticated_returns_401`이 무수정으로 계속 통과함으로써 검증된다.

## 쓰기 범위 보존

### AC-RACKBATCH-011 — 성공한 업로드는 rack_number 컬럼만 쓴다 `[BE][함수]`

Traces: REQ-RACKBATCH-014

**(v1.0.2 확장, D7-R)**: v1.0.1은 값 스냅샷만으로 이 AC를 구성했는데, `bulk_update`가 읽은
값을 그대로 되쓰기 때문에 필드 목록에 여분 컬럼을 넣어도(예:
`bulk_update(to_update, ["rack_number", "shipped_quantity"])`) 스냅샷 diff가 비어 감지되지
않는다(`research.md` §7이 확인한 "`save()` 오버라이드도, `auto_now`도, 시그널도 없다"는
non-risk 사실이 여기서는 마지막 감지 수단마저 제거한다). 따라서 두 개의 독립적인 Then으로
구성한다.

**(v1.0.3 정정, D17)**: (a)의 원래 문구("SET 절이 참조하는 컬럼이 rack_number 하나뿐")는
정상 구현도 실패시킨다 — Django `bulk_update`는
`SET "rack_number" = CASE WHEN "id" = %s THEN %s ... END`를 내며, `id` 컬럼이 `CASE WHEN`
조건 안에 등장한다(Django 5.1.6 `django/db/models/query.py:897` 주석 "PK is used twice in
the resulting update query, once in the filter and once in the WHEN"으로 확인). `id`는 SET
**대입 대상**이 아니라 WHEN 조건절에 불과하므로, 검증 대상을 "SET 절에 등장하는 모든 컬럼"이
아니라 "SET 절에서 **대입되는(왼쪽에 오는)** 컬럼"으로 좁힌다.

- **Given**: `title`, `quantity`, `price`, `purchase_status`, `logistics_status`,
  `shipped_quantity`, `shipped_at`에 각각 기본값이 아닌 값을 심어 둔 LineItem 1건이, 업로드
  행 1개와 매칭되는 상태로 존재한다.
- **When**: 그 `(order_name, sku)`를 가리키는 행 1개로 `_process_rack_number_rows`를
  호출해 `rack_number`를 갱신시키되, 이 호출을 `CaptureQueriesContext`로 감싼다.
- **Then**:
  (a) *SQL 레벨(신규, 판별력의 핵심)*: 캡처된 쿼리 중 `UPDATE` 문의 `SET` 절에서 **대입되는**
  컬럼(각 대입식의 좌변)이 `rack_number` 하나뿐이며, `shipped_quantity`/`logistics_status`
  등 다른 `LineItem` 컬럼이 대입 대상으로 등장하지 않는다. `CASE WHEN "id" = ...` 형태로
  `id`가 조건절에 등장하는 것은 대입이 아니므로 이 검사에 걸리지 않는다 — `bulk_update`에
  두 번째 필드(예: `shipped_quantity`)가 실수로 추가되면 그 필드가 **대입 대상**으로
  나타나므로 그때만 실패한다.
  (b) *값 레벨*: 업로드 전후로 그 LineItem의 필드를 스냅샷 비교하면 `rack_number`만
  달라지고, `title`/`quantity`/`price`/`purchase_status`/`logistics_status`/
  `shipped_quantity`/`shipped_at` 7개 필드는 byte 단위로 동일하다 — 이 Then은 필드 **값**을
  바꾸는 구현(예: `_process_outbound_rows`의 `logistics_status` 전이를 잘못 복사)을 잡지만,
  (a) 없이는 여분 필드를 `bulk_update`에 넘기는 실수를 잡지 못한다.

## 품질 게이트 (Definition of Done)

**백엔드 게이트** — 아래 REQ 15개 전량에 최소 1개 테스트가 매핑되어야 한다. 표는 각 REQ의
**판별력 있는** 커버리지가 실제로 존재하는 파일과 호출 스코프를 명시한다 — plan-auditor
D3(REQ-007이 기존 테스트 어디에도 없이 "커버됨"으로 잘못 주장되었던 결함), D4-R(REQ-005의
기존 픽스처가 재작성 후에도 여전히 비판별적이었던 결함), D13(REQ-008의 "추가 필드 없음"
절반이 기존 테스트로 검증되지 않던 결함)의 재발을 막기 위해 프로즈 목록 대신 표로 고정한다.

| REQ | 커버 테스트 | 스코프 | 비고 |
|---|---|---|---|
| REQ-RACKBATCH-001 | `test_spec_017.py` (신규) | 함수 | 쿼리 카운트 절대 상한(AC-001) |
| REQ-RACKBATCH-002 | `test_spec_017.py` (신규) | 함수 | 2-키 vs 10-키 동등성(AC-001) |
| REQ-RACKBATCH-003 | `test_spec_013.py:729` (기존, 무수정) | 뷰 | dedup 마지막 행 우선(AC-006) |
| REQ-RACKBATCH-004 | `test_spec_017.py` (신규) | 함수 | 동명 Order 최저 `pk`(AC-003) — 기존 커버리지 없음 |
| REQ-RACKBATCH-005 | `test_spec_017.py` (신규, 빈 행 **2건, 동일 SKU**) | 뷰 또는 함수 | AC-007(D4-R) — `test_spec_013.py:809`(빈 행 1건)는 회귀용으로 무수정 유지되나 병합 구현을 판별하지 못하므로 이 REQ의 근거로 쓰지 않는다 |
| REQ-RACKBATCH-006 | `test_spec_013.py:748` (기존, 무수정) | 뷰 | 결정 E, 다중 LineItem 매칭(AC-002) |
| REQ-RACKBATCH-007 | `test_spec_017.py` (신규) | 뷰 | 빈 문자열 clear(AC-004) — 기존 15개 테스트 중 뷰 레벨에서 이를 검증하는 것은 없다(D3). `test_spec_013.py:467`의 파서 레벨 테스트는 뷰에 도달하지 않는다 |
| REQ-RACKBATCH-008 | `test_spec_017.py` (신규) | 뷰 | 응답 키 집합 정확히 일치(AC-010, D13) — `test_spec_013.py:664`는 개별 키 값만 확인하고 키 집합은 확인하지 않아 이 REQ의 "추가 필드 없음" 절반을 검증하지 못한다 |
| REQ-RACKBATCH-009 | `test_spec_013.py:615` (기존, 무수정) | 뷰 | 비-xlsx 400(AC-010) |
| REQ-RACKBATCH-010 | `test_spec_013.py:620, 637, 649` (기존, 무수정) | 뷰 | 파싱 실패 422(AC-005) |
| REQ-RACKBATCH-011 | `test_spec_013.py:836` (기존, 무수정) | 뷰 | 미인증 401(AC-010) |
| REQ-RACKBATCH-012 | `test_spec_013.py:842` (기존, 무수정) | 뷰 | 집계 미호출(AC-008) |
| REQ-RACKBATCH-013 | `test_spec_017.py` (신규) | 함수 | 원자성, bulk_update **이후** 고장 주입(AC-012, D12) |
| REQ-RACKBATCH-014 | `test_spec_017.py` (신규) | 함수 | SQL 대입 컬럼 + 필드 스냅샷(AC-011, D7-R/D17) |
| REQ-RACKBATCH-015 | `test_spec_017.py` (신규) | 함수+뷰 | 주입은 함수, 500 관측은 뷰(AC-009) |

- 신규 파일 `backend/order/tests/test_spec_017.py`가 커버하는 REQ: 001, 002, 004, 005(선택
  가능), 007, 008, 013, 014, 015 — 함수 직접 호출 테스트와 뷰 호출 테스트를 모두 담는다
  (plan.md 파일별 변경 계획 참조).
- 기존 `test_spec_013.py::TestUploadRackNumberView` 15개는 무수정 전량 통과가 조건이며,
  그중 003, 006, 009, 010, 011, 012에 대해서는 판별력 있는 커버리지로도 인정된다. 005는
  존재하되(`:809`) 판별력이 없어 이 표에서 REQ-005의 근거로 세지 않는다(위 비고 참조). 008은
  기존 테스트가 키 집합을 검증하지 않으므로(D13) 이 표에서 REQ-008의 근거로 세지 않는다.
- 이 표에 열거된 15개 REQ 전량이 판별력 있는 테스트를 갖는다 — 근거 없이 "커버됨"으로만
  표시된 REQ는 없다.

**프론트엔드 게이트** — 변경 파일 없음. 기존 프론트엔드 스위트가 이 SPEC과 무관하게 그대로
통과하는지만 확인(회귀 없음).

**공통 게이트** — `spec.md` Exclusions 7개 항목 전수 확인. `_process_rack_number_rows`의
호출부가 정확히 1개인지 확인(spec.md 설계 결정 H). `ruff` 신규 에러 0. `makemigrations
--check` 무변경(신규 인덱스/마이그레이션 없음 확인).

## Traceability 요약

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

12개 인수 기준이 15개 요구사항 전량을 커버한다(미커버 REQ 없음). REQ-RACKBATCH-013(원자성)
과 REQ-RACKBATCH-015(500 경로)는 v1.0.2에서 각각 AC-RACKBATCH-012와 AC-RACKBATCH-009로
분리되었다(plan-auditor D12) — 이전 버전은 두 REQ가 하나의, 원자성을 증명하지 못하는
AC-RACKBATCH-009를 공유했다.
