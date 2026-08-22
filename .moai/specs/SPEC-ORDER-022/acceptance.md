---
id: SPEC-ORDER-022
document: acceptance
version: 1.1.1
status: implemented
updated: 2026-08-15
---

> **구현 완료 메모 (v1.1.1, 2026-08-15)**: U1~U6, T1~T12(T6은 4-case parametrize, 총 21개 테스트) 전부 통과. AC-XRATE-005의 `SYNC_QUERY_COUNT`는 4로 실측 고정(SAVEPOINT + 존재확인 SELECT + `bulk_create` INSERT + RELEASE SAVEPOINT; `orders_exchangerate` 참조 쿼리는 N=3/N=10 양쪽 정확히 2건). AC-XRATE-008: 이 문서가 명시한 `freeze_time("2026-06-21 23:30:00", tz_offset=9)` 픽스처는 이 저장소의 freezegun 1.5.5에서 `date.today()`와 `timezone.localdate()`를 구별하지 못함(둘 다 `2026-06-22` 반환, freezegun의 `tz_offset`이 `tz` 인자 전달 여부와 무관하게 항상 적용되는 구현 방식 때문 — `freezegun/api.py:338-341`, `:400-407`). 구현 코드는 REQ-XRATE-009대로 `timezone.localdate()`를 사용하지만, 이 AC를 문자 그대로는 만족(판별)시킬 수 없어 `backend/order/tests/test_spec_022.py`의 T8은 `timezone.localdate()`를 직접 mock하는 방식으로 대체 구현했다 — 상세는 `spec.md` HISTORY v1.1.1 및 해당 테스트 코드 주석 참조.

# 인수 기준 — SPEC-ORDER-022 ExchangeRate 테이블 자동 갱신 및 공백 구간 백필

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의 AC-XRATE-XXX / REQ-XRATE-XXX ID를 인용해 상호 추적된다.

[HARD] 각 시나리오의 `Traces:` 목록은 `spec.md` 인수 기준 절의 동일 AC 항목이 선언한 것과 완전히 일치한다. 어느 한쪽을 수정할 때 반드시 함께 갱신한다.

[HARD] **판별력 요건.** 모든 단정은 손으로 계산했거나 실제로 실행해 관측한 정확한 값이다 — "동기화가 된다"류의 약한 단정은 쓰지 않는다. 이 프로젝트는 판별력 없는 인수 기준으로 이미 손해를 본 전례가 있다(`SPEC-ORDER-018` v1.0.3/v1.0.4, `SPEC-ORDER-020` v1.0.2 N1, `SPEC-ORDER-021` 감사 D4/D6/D11).

**검증 레이어**: 전부 `[BE]`다. `test_exchange_rates.py`(pytest, `fetch_usd_krw_rate` 단위 테스트, U1~U6)와 `test_spec_022.py`(pytest, `django.core.management.call_command`로 `sync_exchange_rates` 커맨드를 구동, T1~T12, v1.1.0 — T12는 감사 D3 반영 신설)로 나뉜다. 이 SPEC은 프론트엔드 변경이 없다.

**공통 모킹 관례(D11 정정, v1.1.0)**: T1~T12(`sync_exchange_rates` 커맨드 통합 테스트)는 `patch("order.management.commands.sync_exchange_rates.fetch_usd_krw_rate")`로 외부 HTTP 호출을 대체한다(`patch(...).return_value`/`side_effect` **사용 스타일**은 `backend/order/tests/test_shopify_orders.py:269`/`:604`를 참고하되, 그 테스트는 `urlopen`이 아니라 `_get_with_headers` 헬퍼를 모킹하므로 그대로 전이되는 관례는 아니다). U1~U6(`fetch_usd_krw_rate` 단위 테스트)는 이와 달리 `urllib.request.urlopen` 자체를 모킹한다(아래 U1~U6 절 참조) — 두 계층 모두 실제 네트워크를 타지 않는다. `ExchangeRate.rate` 비교는 항상 `Decimal(...)` 값끼리 한다(`Decimal("1500.00") == "1500.00"`은 `False`이므로 문자열과 직접 비교하지 않는다 — v1.0.0의 "항상 문자열로 비교한다"는 문장은 스스로의 괄호 설명과 모순되는 오기였다).

---

## 계약 함수 단위 테스트

### U1 — 정상 응답, 요청일과 echo일이 같음 `[BE]`

Traces: (spec.md 인수 기준 절의 런타임 AC 없음 — REQ-XRATE-001/002의 코드 리뷰 보조 근거로 `plan.md` M1에 포함)

- **Given**(**D8 정정, v1.1.0** — `urlopen`은 컨텍스트 매니저이고 `.read()`는 `bytes`를 반환한다; 딕셔너리를 직접 반환하도록 모킹하면 `json.loads`가 `TypeError`를 낸다): `urllib.request.urlopen`을 `mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"amount":1.0,"base":"USD","date":"2026-08-13","rates":{"KRW":1420.29}}'`로 모킹.
- **When**: `fetch_usd_krw_rate(date(2026, 8, 13))` 호출.
- **Then**: 반환값이 `(date(2026, 8, 13), Decimal("1420.29"))`와 정확히 일치.

### U2 — echoed date가 요청일과 다름 `[BE]`

Traces: REQ-XRATE-003 (계약 함수 레벨 확인 — AC-XRATE-002는 커맨드 레벨에서 이 동작이 저장 위치에 반영되는지까지 확인한다)

- **Given**(D8 정정 — U1과 동일한 bytes+컨텍스트매니저 형태): `urllib.request.urlopen`을 `mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"date":"2026-06-18","rates":{"KRW":1538.89}}'`로 모킹.
- **When**: `fetch_usd_krw_rate(date(2026, 6, 20))` 호출(토요일 — 비게시일이라고 가정).
- **Then**: 반환값의 첫 번째 요소(게시일)가 `date(2026, 6, 18)`이며, 요청에 사용한 `date(2026, 6, 20)`이 아니다.

### U3~U6 — 4종 실패 `[BE]`

Traces: (REQ-XRATE-001의 예외 계약 확인 — AC-XRATE-006이 커맨드 레벨에서 이 예외들이 어떻게 처리되는지 확인한다)

| # | Given(모킹) | When | Then |
|---|---|---|---|
| U3 | `mock_urlopen.side_effect = urllib.error.URLError("...")` | `fetch_usd_krw_rate(임의 날짜)` | `ExchangeRateFetchError` 발생 |
| U4 | `mock_urlopen.side_effect = urllib.error.HTTPError(url, 500, "...", {}, None)` | 〃 | `ExchangeRateFetchError` 발생 |
| U5 | `mock_urlopen.return_value.__enter__.return_value.read.return_value = b"not json"`(파싱 불가) | 〃 | `ExchangeRateFetchError` 발생 |
| U6 | `mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"date":"...","rates":{}}'`(KRW 키 없음, **D8 정정** — bytes 형태) | 〃 | `ExchangeRateFetchError` 발생 |

---

## 정상 범위 동기화

### AC-XRATE-001 — N=3개 날짜, 각각 고유한 값으로 저장 `[BE]`

Traces: REQ-XRATE-005, REQ-XRATE-006, REQ-XRATE-011, REQ-XRATE-012

- **Given**: `ExchangeRate` 테이블이 `2026-07-01`~`2026-07-03` 범위와 겹치지 않는 기존 레코드만 갖고 있다(또는 비어 있다). `fetch_usd_krw_rate`를 `side_effect` 콜러블로 모킹해, 요청 날짜별로 서로 다른 값을 반환하도록 한다(**D14 정정** — 반환값은 REQ-XRATE-001의 `Decimal` 계약과 일치시킨다, 문자열이 아니다): `2026-07-01 → (date(2026,7,1), Decimal("1500.00"))`, `2026-07-02 → (date(2026,7,2), Decimal("1501.00"))`, `2026-07-03 → (date(2026,7,3), Decimal("1502.00"))`.
- **When**: `call_command("sync_exchange_rates", "--start", "2026-07-01", "--end", "2026-07-03")`.
- **Then**: `ExchangeRate.objects.filter(effective_date__in=[date(2026,7,1), date(2026,7,2), date(2026,7,3)]).count() == 3`이고, 각 레코드의 `rate`가 자신의 `effective_date`에 대응하는 모킹된 값과 정확히 일치한다(`date(2026,7,1)` → `Decimal("1500.00")` 등, 세 값 모두 개별 단정).
- **판별력**: 세 값이 모두 다르므로, 취합 과정에서 날짜-값 매핑이 뒤섞이면(예: 마지막으로 조회한 값을 모든 레코드에 재사용) 최소 두 레코드의 값이 어긋나 이 단정이 실패한다.

### AC-XRATE-002 — echoed date로 저장, 요청일로는 저장되지 않음 `[BE]`

Traces: REQ-XRATE-003

- **Given**: `fetch_usd_krw_rate`가 `date(2026, 6, 20)` 요청에 대해 `(date(2026, 6, 18), Decimal("1538.89"))`를 반환하도록 모킹(echo가 다른 날짜).
- **When**: `call_command("sync_exchange_rates", "--start", "2026-06-20", "--end", "2026-06-20")`.
- **Then**: `ExchangeRate.objects.filter(effective_date=date(2026, 6, 20)).exists() is False`이고, `ExchangeRate.objects.filter(effective_date=date(2026, 6, 18)).exists() is True`이며 그 `rate == Decimal("1538.89")`.
- **판별력**: 요청일을 그대로 `effective_date`에 쓰면 `2026-06-20`이 존재하고 `2026-06-18`이 존재하지 않아 두 단정 모두 반대로 실패한다.

### AC-XRATE-003 — 재실행 멱등성(fetch가 동일 값을 반환하는 경우) `[BE]`

Traces: REQ-XRATE-012

- **Given**: `fetch_usd_krw_rate`가 `2026-07-10`에 대해 항상 `(date(2026,7,10), Decimal("1510.00"))`을 반환하도록 모킹(고정 반환값 — `side_effect` 아님).
- **When**: `call_command("sync_exchange_rates", "--start", "2026-07-10", "--end", "2026-07-10")`를 **두 번 연속** 호출.
- **Then**: 두 번째 호출이 예외 없이 완료되고, `ExchangeRate.objects.filter(effective_date=date(2026,7,10)).count() == 1`(첫 번째 호출 직후와 동일), `rate == Decimal("1510.00")`(불변).
- **판별력**: 존재 여부를 사전에 필터링하지 않고 두 번째 호출에서도 `bulk_create([ExchangeRate(effective_date=date(2026,7,10), ...)])`를 그대로 시도하면, `effective_date`의 `unique=True` 제약(`backend/order/models.py:501`)에 의해 두 번째 `call_command`가 `IntegrityError`로 실패한다.

### AC-XRATE-004 — 기존/수기 보정 레코드는 다른 값이 조회되어도 덮어쓰지 않는다 `[BE]`

Traces: REQ-XRATE-013

- **Given**: `ExchangeRate.objects.create(effective_date=date(2026, 6, 25), rate=Decimal("1500.00"))`(수기 보정을 흉내낸 사전 레코드). `fetch_usd_krw_rate`가 `date(2026, 6, 25)` 요청에 대해 `(date(2026, 6, 25), Decimal("1420.29"))`(저장값과 다름)를 반환하도록 모킹.
- **When**: `call_command("sync_exchange_rates", "--start", "2026-06-25", "--end", "2026-06-25")`.
- **Then**: `ExchangeRate.objects.get(effective_date=date(2026, 6, 25)).rate == Decimal("1500.00")`(`Decimal("1420.29")`로 바뀌지 않음).
- **이 AC가 AC-XRATE-003과 별도로 필요한 이유**: AC-XRATE-003의 재실행 시나리오는 두 번 모두 **같은** 값을 fetch하므로, 구현이 실제로는 `update_or_create`를 쓰더라도(값이 같으므로 결과가 똑같아 보여) 그 AC를 통과해버린다 — "덮어쓰지 않는다"는 REQ-XRATE-013을 직접 판별하는 것은 이 AC(값이 다른 시나리오)뿐이다.
- **판별력**: 존재 여부 확인 없이 `update_or_create`로 구현하면 `rate`가 `Decimal("1420.29")`로 바뀌어 이 단정이 실패한다.

## 성능 불변식

### AC-XRATE-005 — 커맨드 실행 전체의 DB 쿼리 수 불변식 `[BE]`

Traces: REQ-XRATE-012

- **Given**: 아무 기존 레코드와도 겹치지 않는 두 그룹의 날짜 — 그룹 X(N=3일), 그룹 Y(N=10일). 각 그룹에 대해 `fetch_usd_krw_rate`가 전부 성공(서로 다른 값)하도록 모킹.
- **When**: 그룹 X, Y 각각에 대해 명시적 `--start`/`--end`로 `call_command`를 별도 실행하며, `django.test.utils.CaptureQueriesContext(connection)`(`backend/order/tests/test_spec_018.py:40`의 기존 임포트 재사용)로 커맨드 실행 전체를 감싼다(명시적 `--start`/`--end`를 쓰므로 최신 저장일 조회 쿼리 자체가 발생하지 않는다).
- **Then**: (a) `len(ctx_x.captured_queries) == len(ctx_y.captured_queries) == SYNC_QUERY_COUNT` — `SYNC_QUERY_COUNT`는 이 테스트를 작성하는 시점에 올바른(배치) 구현으로 실제 실행해 관측한 값을 상수로 고정한다(`test_spec_018.py:64`의 `UNORDERED_ENDPOINT_QUERY_COUNT = 3`와 동일한 관례 — 추측값을 넣지 않는다). 날짜 수가 3배 이상 늘어도 총 쿼리 수는 이 절대값과 동일해야 한다. **주의(D7)**: pytest-django가 각 테스트를 트랜잭션으로 감싸므로 `sync_exchange_rates`의 `transaction.atomic()`이 중첩(savepoint)으로 실행되어 `SAVEPOINT`/`RELEASE SAVEPOINT` 문이 캡처된 쿼리에 섞여 들어간다 — 이 때문에 `SYNC_QUERY_COUNT`는 "2"가 아닐 수 있다(이것이 정상이며, 절대값은 실측으로 고정하는 것이지 2로 "맞추려" 시도해서는 안 된다). (b) **[HARD, D7 정정 — 이전 버전은 여기에 단정 없이 전제 서술만 있었다]** `ctx_x`, `ctx_y` 각각에서 `orders_exchangerate`(`backend/order/models.py:507`)를 참조하는 쿼리 개수가 **정확히 2건**(존재 확인 `filter(...__in=...)` 1건 + `bulk_create` 1건)이어야 한다. 참조 여부는 부분 문자열(`in`) 검사로 충분하다 — 이 테이블명이 `backend/order/models.py`에 선언된 다른 어떤 `db_table`(`:27,93,130,149,241,297,310,326,364,389,414,431,464,487,528,547` — 총 16개)의 부분 문자열도 아니고 그 반대도 아니기 때문이다(savepoint 문은 `orders_exchangerate`를 참조하지 않으므로 이 카운트에 섞이지 않는다).
- **판별력**: (a)는 날짜별 `get_or_create`/`update_or_create` 루프로 구현하면(N+1) X와 Y의 쿼리 수가 서로 달라져(대략 X는 최대 6, Y는 최대 20) 실패한다. 절대값 고정은 날짜 수와 무관한 상수 추가 쿼리(예: 불필요한 카운트 쿼리 하나를 더 발급)도 잡는다 — X와 Y가 서로 같다는 상대 비교만으로는(둘 다 똑같이 늘어나 여전히 같으므로) 이런 mutation을 잡지 못하기 때문에 절대값 고정이 필수다(`SPEC-ORDER-021` AC-COST-009, `SPEC-ORDER-018` `test_unordered_endpoint_query_count_is_unaffected_by_excluded_items`와 동일한 논리). (b)는 (a)와 별도로, `orders_exchangerate` 참조 쿼리 자체가 N에 비례해 늘어나는 mutation(예: 날짜별 개별 존재 확인)을 원인 테이블 단위로 직접 지목한다.

## 실패 처리

### AC-XRATE-006 — 실패 4종: 종료 코드, DB 미변경, stderr 내용 `[BE]`

Traces: REQ-XRATE-015, REQ-XRATE-016, REQ-XRATE-017

- **Given**: 단일 날짜(`date(2026, 7, 20)`)만 포함하는 범위. `ExchangeRate.objects.count()`를 실행 전에 기록해 둔다. `fetch_usd_krw_rate`가 아래 4가지 방식 중 하나로 각각 독립적인 테스트 케이스에서 `ExchangeRateFetchError`를 발생시키도록 모킹(계약 함수 자체의 4종 실패는 U3~U6이 개별 검증했으므로, 여기서는 커맨드가 이 예외를 받았을 때의 처리만 검증한다):
  - (a) 네트워크 오류를 흉내낸 `ExchangeRateFetchError("2026-07-20: network error (Name or service not known)")`
  - (b) HTTP 500을 흉내낸 `ExchangeRateFetchError("2026-07-20: HTTP 500")`
  - (c) JSON 파싱 실패를 흉내낸 `ExchangeRateFetchError("2026-07-20: malformed JSON response")`
  - (d) KRW 키 부재를 흉내낸 `ExchangeRateFetchError("2026-07-20: response missing expected key 'KRW'")`
- **When**: 4개 케이스 각각에서 `io.StringIO()`를 `stderr` 인자로 넘겨 `call_command("sync_exchange_rates", "--start", "2026-07-20", "--end", "2026-07-20", stderr=captured_stderr)`.
- **Then**: 4개 케이스 각각에서 (1) `pytest.raises(CommandError)`가 발생하고, (2) `ExchangeRate.objects.count()`가 실행 전과 동일하다(**D15 정정** — 단일 날짜 `exists()`가 아니라 전체 카운트로 확인한다. `filter(effective_date=date(2026,7,20)).exists() is False`만으로는 구현이 실패 시 **다른** 날짜에 sentinel row를 잘못 쓰는 경우를 놓친다), (3) **[신설, D5]** `captured_stderr.getvalue()`에 `"2026-07-20"`(실패한 날짜)과 그 케이스의 mock 메시지 문자열(예: 케이스 (a)라면 `"network error"`)이 모두 포함되어 있다.
- **판별력**: 실패를 무시하고 계속 진행해 정상 종료(예외 없이 반환)하면 `pytest.raises(CommandError)` 단정이 실패한다 — 이것이 1차 판별력이다. DB 카운트 불변 단정이 2차 판별력이다. `CommandError`는 정확히 발생시키되 stderr에 개별 날짜·메시지를 쓰지 않고 요약 문구만 남기면(예: `CommandError("1건 실패")`만 쓰고 `self.stderr.write(...)`를 호출하지 않으면), (1)(2)는 통과하지만 (3)이 실패한다 — REQ-XRATE-016의 "각 실패 날짜와 오류를 stderr에 개별 기록"과 REQ-XRATE-017의 stderr 가시성 조항을 이 단정이 없으면 아무것도 판별하지 못했다(v1.0.0의 결함, D5).

### AC-XRATE-007 — 부분 실패 시 성공분은 보존된다 `[BE]`

Traces: REQ-XRATE-011, REQ-XRATE-014, REQ-XRATE-016

- **Given**: 3일 범위(`2026-07-21`~`2026-07-23`). `fetch_usd_krw_rate`를 `side_effect`로 모킹 — `2026-07-21 → (date(2026,7,21), Decimal("1600.00"))`, `2026-07-22 → ExchangeRateFetchError("...")`(실패), `2026-07-23 → (date(2026,7,23), Decimal("1602.00"))`.
- **When**: `call_command("sync_exchange_rates", "--start", "2026-07-21", "--end", "2026-07-23")`.
- **Then**: `pytest.raises(CommandError)`가 발생하되, `ExchangeRate.objects.get(effective_date=date(2026,7,21)).rate == Decimal("1600.00")`, `ExchangeRate.objects.get(effective_date=date(2026,7,23)).rate == Decimal("1602.00")`(둘 다 존재), `ExchangeRate.objects.filter(effective_date=date(2026,7,22)).exists() is False`.
- **판별력**: 조회(HTTP 루프)와 쓰기를 하나의 `transaction.atomic()`으로 묶으면, `2026-07-22`의 실패가 예외로 전파되는 순간 이미 성공한 `2026-07-21`/`2026-07-23`의 DB 쓰기까지 롤백되어(트랜잭션 전체가 커밋되지 않음) 두 날짜의 `exists()` 단정이 `False`로 뒤바뀌어 실패한다 — REQ-XRATE-014("쓰기 단계에만 한정된 트랜잭션")의 직접 판별 지점.

## 범위 계산

### AC-XRATE-008 — 기본 범위: `--start` 생략 시 다음날부터, `--end` 생략 시 오늘(UTC)까지 `[BE]`

Traces: REQ-XRATE-007, REQ-XRATE-009

- **Given**(**D1 정정, v1.1.0 — 블로킹 결함**): `ExchangeRate.objects.create(effective_date=date(2026, 6, 18), rate=Decimal("1540.64"))`(최신 저장 레코드를 흉내냄, 그 이전 날짜의 레코드도 함께 존재해도 무방). `freezegun.freeze_time("2026-06-21 23:30:00", tz_offset=9)`로 "오늘"을 고정 — 자정 근처 UTC 시각(`23:30`)과 `tz_offset=9`의 조합이 반드시 필요하다(이유는 아래 판별력 참조). `fetch_usd_krw_rate`를 모든 호출에 대해 성공하도록 모킹(값은 임의).
- **When**: `call_command("sync_exchange_rates")`(`--start`/`--end` 모두 생략).
- **Then**: `fetch_usd_krw_rate` mock의 `call_args_list`에서 추출한 호출 인자(요청 날짜) 집합이 정확히 `{date(2026,6,19), date(2026,6,20), date(2026,6,21)}`과 일치한다(그 외 날짜에 대한 호출 없음, 이 세 날짜 모두 호출됨).
- **판별력**: "다음 날"이 아니라 최신 저장일 자체(`2026-06-18`)부터 다시 조회하면(off-by-one) 호출 인자 집합에 `date(2026,6,18)`이 추가로 포함되어 이 단정이 실패한다. `timezone.localdate()` 대신 `datetime.date.today()`를 쓰는 mutation은, **freezegun 1.5.5를 이 픽스처로 직접 실행해 확인한 결과**, `date.today()`가 `2026-06-22`를 반환한다 — freezegun은 호스트 OS의 타임존을 전혀 참조하지 않고 `frozen instant(2026-06-21 23:30:00 UTC) + tz_offset(9시간) = 2026-06-22 08:30`을 기준으로 `date.today()`를 대체하기 때문이다(호스트 머신의 실제 로컬 타임존과는 무관 — v1.0.0의 "테스트 실행 머신의 로컬 타임존이 UTC가 아닐 경우"라는 설명은 freezegun의 실제 동작 방식에 대한 오해였다). 이 mutation 하에서는 커맨드가 `2026-06-19`~`2026-06-22` 네 날짜를 호출해 세 날짜만 기대하는 이 단정이 실패한다. 반면 `timezone.localdate()`는 `TIME_ZONE="UTC"`(`backend/config/settings/base.py:92`) 설정 하에서 frozen UTC 시각을 그대로 사용해 `2026-06-21`을 반환하므로 세 날짜만 호출한다. **자정 근처 시각이 필수인 이유**: `freeze_time("2026-06-21 12:00:00", tz_offset=9)`처럼 정오 근처 시각을 쓰면 `+9시간`을 더해도(`21:00`) 여전히 `2026-06-21` 안에 머물러 두 계산 방식이 우연히 같은 날짜를 반환해 이 mutation을 잡지 못한다 — v1.0.0의 `freeze_time("2026-06-21 12:00:00")`(`tz_offset` 생략, 즉 0)가 정확히 이 실패 사례였다: `tz_offset=0`이면 `date.today()`와 `timezone.localdate()`가 이 프로젝트의 `TIME_ZONE="UTC"` 설정 하에서 **항상** 같은 값을 반환하므로, 어떤 시각을 골라도 이 mutation이 걸리지 않았다.

### AC-XRATE-009 — 시작일이 종료일보다 이후이면 조회/기록 없이 성공 종료 `[BE]`

Traces: REQ-XRATE-010

- **Given**: `fetch_usd_krw_rate`를 모킹(호출 여부만 확인하면 되므로 반환값은 무관). 사전 `ExchangeRate` 레코드 상태를 기록해 둔다.
- **When**: `call_command("sync_exchange_rates", "--start", "2026-07-05", "--end", "2026-07-01")`(시작일이 종료일보다 이후).
- **Then**: 예외 없이 정상 반환, `fetch_usd_krw_rate` mock의 `call_count == 0`, `ExchangeRate.objects.count()`가 실행 전후 동일.
- **판별력**: 빈 범위에서도 최소 1회 반복이 일어나게 구현하면(예: 날짜 순회 경계 계산에서 `range`류 구조가 빈 시퀀스를 만들지 못하는 오프바이원 오류) `fetch_usd_krw_rate`가 최소 1회 호출되어 `call_count == 0` 단정이 실패한다.

### AC-XRATE-010 — 레코드가 전혀 없는 상태에서 `--start` 없이 실행하면 `CommandError` `[BE]`

Traces: REQ-XRATE-008

- **Given**: `ExchangeRate.objects.all().delete()`로 테이블을 완전히 비운다. `fetch_usd_krw_rate`를 모킹.
- **When**: `call_command("sync_exchange_rates", "--end", "2026-07-01")`(`--start`만 생략).
- **Then**: `pytest.raises(CommandError)`, `fetch_usd_krw_rate` mock의 `call_count == 0`.
- **판별력**: 빈 테이블에서 최신 레코드 조회(`.order_by("-effective_date").first()`)가 `None`을 반환하는 경우를 방어하지 않고 그대로 `None`에 날짜 연산(`+ timedelta(...)`)을 시도하면 `AttributeError`/`TypeError`가 발생한다 — 이는 `CommandError`가 아니므로(예외 타입이 다르므로) `pytest.raises(CommandError)`가 그 예외를 잡지 못해 테스트가 실패한다. 이 AC는 "의도적으로 처리된 실패"와 "처리되지 않은 예외로 인한 우연한 실패"를 예외 타입으로 구분한다.

## 회귀 확인

### AC-XRATE-011 — 백필 후 `_get_exchange_rate`가 2026-08-13 주문에 대해 올바른 환율을 반환한다 `[BE]`

Traces: REQ-XRATE-003, REQ-XRATE-012, REQ-XRATE-018

- **Given**: `fetch_usd_krw_rate`가 `date(2026, 8, 13)` 요청에 대해 `(date(2026, 8, 13), Decimal("1420.29"))`(echo일=요청일, 이 세션에 WebFetch로 확인한 실제 Frankfurter 값)를 반환하도록 모킹. 이 날짜를 포함하는 범위(예: `--start 2026-08-13 --end 2026-08-13`)로 `call_command("sync_exchange_rates", ...)`를 실행해 성공적으로 저장한다.
- **When**: `shopify_created_at`이 `2026-08-13`인(UTC 인식 `datetime`, `timezone.now()` 기반 — `test_spec_008.py:101-114`의 UTC 함정을 재사용해 회피) `Order` 인스턴스에 대해 `OrderDetailSerializer()._get_exchange_rate(order)`를 직접 호출한다(REQ-XRATE-018에 따라 이 메서드는 이 SPEC에서 무수정이므로, 뷰 전체를 거치지 않고 메서드를 직접 호출하는 것으로 회귀 확인에 충분하다).
- **Then**: 반환된 `ExchangeRate` 인스턴스의 `.effective_date == date(2026, 8, 13)`이고 `.rate == Decimal("1420.29")`.
- **판별력**: `_get_exchange_rate` 자체를 이 SPEC 구현 과정에서 실수로 함께 수정해버리면(REQ-XRATE-018 위반) 이 회귀 확인이 예상과 다른 값이나 예외로 실패한다. echoed-date 키잉이 깨져 있으면(AC-XRATE-002가 직접 잡는 결함이지만, 이 시나리오는 요청일=echo일이라 그 결함 자체는 여기서 드러나지 않는다) 이 AC는 통과할 수 있다 — 이 AC의 주목적은 "echoed-date 키잉이 옳다"는 것의 재확인이 아니라 "백필이 끝난 뒤 기존 폴백 로직이 실제로 새 데이터를 집어 오는지"에 대한 종단 간(end-to-end) 회귀 확인이다.

## 중복 echo 게시일 압축 (신설, v1.1.0 — 감사 D3 반영)

### AC-XRATE-012 — 주말을 포함하는 범위에서 중복 echo 게시일이 정확히 한 건으로 압축된다 `[BE]`

Traces: REQ-XRATE-024

- **Given**: `fetch_usd_krw_rate`를 `side_effect` 콜러블로 모킹해, `date(2026,6,19)`(금), `date(2026,6,20)`(토), `date(2026,6,21)`(일) 세 요청 **전부**에 대해 동일한 `(date(2026, 6, 19), Decimal("1530.00"))`을 반환하도록 한다(주말 이틀이 직전 금요일 게시일로 echo되는 실제 Frankfurter 동작을 재현 — 이 세션에 WebFetch로 확인한 non-publication-day 스누핑 동작과 동일한 패턴).
- **When**: `call_command("sync_exchange_rates", "--start", "2026-06-19", "--end", "2026-06-21")`.
- **Then**: 예외 없이 정상 종료하고, `ExchangeRate.objects.filter(effective_date=date(2026, 6, 19)).count() == 1`이며, `rate == Decimal("1530.00")`이고, `ExchangeRate.objects.filter(effective_date__in=[date(2026,6,20), date(2026,6,21)]).exists() is False`.
- **이 AC가 필요한 이유**: M8의 첫 백필 범위(`2026-06-19`~오늘, 57일)에는 이런 주말 쌍이 8개 있다 — 압축 없이는 `2026-06-19`에 대해 `ExchangeRate` 객체 3개(요청 3건 각각에서 하나씩)가 `bulk_create`에 담겨 `unique=True`(`backend/order/models.py:501`) 위반으로 `IntegrityError`가 발생하고, M8의 첫 실행 자체가 실패한다.
- **판별력**: `fetched` 결과를 게시일 기준으로 압축하지 않고(예: `dict`가 아니라 `list`로 모아 그대로 `bulk_create`에 전달) 그대로 쓰면, 동일 `effective_date=2026-06-19`를 가진 객체 3개가 `bulk_create` 호출 하나에 함께 전달된다. 이 SPEC은 그 결과가 `IntegrityError`로 나타나는지, 아니면 다중 행 내부 중복에 대한 특정 백엔드의 `IGNORE`/`ON CONFLICT` 처리로 조용히 흡수되는지를 판단의 근거로 삼지 않는다 — 이 프로젝트는 로컬/테스트 환경 기본값이 SQLite(`backend/config/settings/local.py:11`)이고 운영 환경은 MySQL(`mysqlclient`, `pyproject.toml`)이라 배치 내부 중복에 대한 두 백엔드의 정확한 동작을 이 SPEC 작성 시점에 독립적으로 검증하지 않았기 때문이다. REQ-XRATE-024가 애플리케이션 레벨(`dict`) 압축을 명시적으로 요구하는 이유가 바로 이것이다 — 백엔드별 `IGNORE` 의미에 기대지 않고, "정확히 1건만 `bulk_create`에 전달된다"는 것을 애플리케이션 코드 스스로 보장한다. `pytest.raises(...)` 없이 이 AC를 작성한 이유도 같다 — 압축이 생략된 구현이 특정 백엔드에서 예외 없이 우연히 `count() == 1`을 만들어낼 가능성을 배제할 수 없으므로, 예외 발생 여부가 아니라 `count() == 1` **그 자체**(및 `rate` 값 일치)를 1차 판별 기준으로 삼는다 — 이 AC가 CI에서 사용하는 백엔드에서 압축 생략 구현이 예외로 실패하는지, 조용히 통과하는지는 구현자가 M1/M3 단계에서 직접 실행해 확인해야 한다(`plan.md` DoD).

---

## 품질 게이트 — Definition of Done 매핑

| AC | 테스트 파일 | 테스트 번호 | 검증 대상 REQ |
|---|---|---|---|
| U1~U6 | `test_exchange_rates.py` | U1~U6 | 001, 003(**D18 정정** — v1.0.0은 002도 나열했으나 002(Frankfurter 엔드포인트 URL·urllib 사용·신규 의존성 없음)는 spec.md·acceptance.md 양쪽에서 코드 리뷰 전용으로 배정되어 있어 제거) |
| AC-XRATE-001 | `test_spec_022.py` | T1 | 005, 006, 011, 012 |
| AC-XRATE-002 | `test_spec_022.py` | T2 | 003 |
| AC-XRATE-003 | `test_spec_022.py` | T3 | 012 |
| AC-XRATE-004 | `test_spec_022.py` | T4 | 013 |
| AC-XRATE-005 | `test_spec_022.py` | T5 | 012 |
| AC-XRATE-006 | `test_spec_022.py` | T6 | 015, 016, 017 |
| AC-XRATE-007 | `test_spec_022.py` | T7 | 011, 014, 016 |
| AC-XRATE-008 | `test_spec_022.py` | T8 | 007, 009 |
| AC-XRATE-009 | `test_spec_022.py` | T9 | 010 |
| AC-XRATE-010 | `test_spec_022.py` | T10 | 008 |
| AC-XRATE-011 | `test_spec_022.py` | T11 | 003, 012, 018 |
| AC-XRATE-012 | `test_spec_022.py` | T12 | 024(v1.1.0 신설, 감사 D3 반영) |

이 표는 각 AC 섹션 상단의 `Traces:` 목록과 완전히 일치한다(v1.1.0 — D18 정정 이후 재검증됨).

시나리오로 직접 검증하지 않는 요구사항: REQ-XRATE-001, 002, 004(계약 함수의 구조적 성질 — U1~U6이 보조적으로 뒷받침하지만 최종 확인은 코드 리뷰), REQ-XRATE-019~023(범위 경계) — 전부 `plan.md` 완료 조건의 코드 리뷰/`git diff` 게이트로 확인한다. **D18 정정**: v1.0.0은 REQ-XRATE-005도 이 목록에 넣었으나, AC-XRATE-001의 `Traces:`가 REQ-005를 선언하므로 실제로는 간접 검증되지 않고 직접 검증된다 — 목록에서 제거.

**추가 회귀 게이트**(신규 테스트가 아니라 기존 스위트의 무수정 통과):

- `backend/order/tests/test_spec_008.py`, `test_spec_009.py`, `test_spec_021.py`(존재한다면) 전량 — `_get_exchange_rate`/`_compute_margin_usd`가 이 SPEC에서 무수정임을 확인하는 회귀 게이트(REQ-XRATE-018).
- `backend/order/tests/test_shopify_orders.py` 전량 — `shopify_orders.py`가 무수정임을 확인하는 회귀 게이트.
- 백엔드 전체 `pytest backend/order/tests/`.
