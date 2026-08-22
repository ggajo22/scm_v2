---
id: SPEC-ORDER-022
version: 1.1.3
status: implemented
created_at: 2026-08-14
updated: 2026-08-15
author: ggajo
priority: High
issue_number: 0
labels: [order, exchange-rate, data-pipeline, backend]
---

# ExchangeRate 테이블 자동 갱신 및 공백 구간 백필

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-14 | ggajo | 최초 작성. `ExchangeRate` 테이블(`backend/order/models.py:495-509`)이 2026-06-18 이후 갱신되지 않아, 전체 주문의 90.1%(3,410건 중 3,072건)가 실제보다 최대 8.5% 과대평가된 환율로 마진을 계산하고 있는 문제를 해소한다. **인용 검증 범위**: 이 문서의 모든 `file:line` 인용과 Frankfurter API 응답 형태(단일 날짜 엔드포인트, range 엔드포인트 둘 다)는 이 세션에서 직접 파일을 읽거나 WebFetch로 재현해 검증했다 — 선행 SPEC의 인용을 재사용하지 않았다. 반면 라이브 DB 상태(레코드 117건, 요일 분포, 공백 구간, 주문 건수/비율)는 오케스트레이터가 이 세션에서 `python manage.py shell`로 직접 조회한 값을 그대로 인용한 것이며, 이 SPEC 작성 과정에서 `manage.py`를 라이브 DB에 대해 재실행하지 않았다(작업 제약사항에 따름) — 코드/API 관련 인용과 DB 상태 관련 인용의 검증 방식이 다르다는 점을 명시한다. **주의**: 아래 v1.1.0 D10 항목에서 밝히듯, "모든 `file:line` 인용을 직접 재검증했다"는 위 주장은 실제로는 40건 중 39건만 정확했다 — 이 v1.0.0 행 자체는 원문 그대로 보존하고, 정정은 v1.1.0 행에 기록한다. |
| 1.1.3 | 2026-08-15 | ggajo (manager-tdd) | 라이브 백필 1차 실행에서 58개 날짜 전부 `HTTP 403` 실패. 원인: Frankfurter가 stdlib 기본 User-Agent(`Python-urllib/3.x`)를 차단(이 세션에 라이브로 재현: 헤더 없는 `Request` → 403, `User-Agent` 헤더 포함 → 200). U1~U9 전부 `urlopen` 자체를 모킹해 실제 HTTP 계층을 타지 않으므로 구조적으로 테스트가 잡을 수 없던 결함(D8의 필연적 귀결) — 실제 호출 시점에야 드러났다. RED(`test_u9_...` 추가, 헤더 없는 상태에서 `sent_request.get_header("User-agent") is None`으로 실패 확인) → `exchange_rates.py`에 `USER_AGENT = "scm-v2/1.0"` 모듈 상수 추가 + `Request(url, headers={"User-Agent": USER_AGENT})`로 GREEN(9/9) → 헤더 제거 mutation으로 재실패 재확인 후 원복. `Request.headers`가 키를 `"User-agent"`로 정규화(`str.capitalize()`)한다는 점을 직접 확인(`req.get_header("User-agent")`가 유효, `"User-Agent"`는 무효)하고 테스트에 반영. `test_exchange_rates.py`+`test_spec_022.py` 24개 전량 통과(23+U9). **라이브 API 1건 직접 확인**(DB 미접촉 읽기 전용): `fetch_usd_krw_rate(date(2026,8,13))` → `(date(2026,8,13), Decimal('1420.29'))`, HTTP 403 재현 안 됨. REQ-XRATE-002에 User-Agent 요구와 함정 재발 가능성(데이터 소스 교체 시)을 명시. `sync_exchange_rates` 커맨드 자체는 이번 수정에서 실행하지 않았다(라이브 DB 쓰기는 오케스트레이터 직접 수행 예정) — `exchange_rates.py`/`test_exchange_rates.py`(둘 다 기존 신규 파일의 수정, 신규 파일 추가 없음) 외 무수정. 브랜치 `feature/SPEC-ORDER-022`(PR #31)에 추가 커밋으로 push. |
| 1.1.2 | 2026-08-15 | ggajo (manager-tdd) | evaluator-active mutation 검증(7건 중 2건 결함) 반영. F1(medium) — `exchange_rates.py`의 `except KeyError`가 필드 존재-값 손상 케이스(`date.fromisoformat`의 `ValueError`, `Decimal(str(None))`의 `decimal.InvalidOperation`)를 못 잡아 `_fetch_range`(`except ExchangeRateFetchError`만 캐치)를 빠져나가 커맨드가 트레이스백으로 죽고 그 시점까지 조회 성공한 날짜가 전부 유실되던 문제를, `except (ValueError, TypeError, decimal.InvalidOperation)` 추가로 해소(U7/U8 신규, RED 확인 후 GREEN). F2(medium) — T12가 REQ-XRATE-024(dict 압축)가 아니라 `ignore_conflicts=True`(설계 결정 G)의 DB 레벨 부수효과로만 통과하던 판별력 결여를, `ExchangeRate.objects.bulk_create`를 `wraps=`로 감싸 정확히 1개 객체로 호출됐는지 직접 단정하도록 보강 — dict→list mutation 적용 시 실패(`3 == 1` AssertionError, `bulk_create`가 중복 3건으로 호출됨을 직접 확인)함을 재검증 후 원복. 두 수정 후 `test_exchange_rates.py`+`test_spec_022.py` 23개 전량 통과(8+15, 기존 21개에 U7/U8 2개 추가). 기존 4개 신규 파일 외 무수정, 커밋 없음. |
| 1.1.1 | 2026-08-15 | ggajo (manager-tdd) | M0~M7 TDD 구현 완료(RED-GREEN-REFACTOR, worktree `~/.moai/worktrees/scm_v2/SPEC-ORDER-022`, 신규 파일 4개만 생성 — `backend/order/exchange_rates.py`, `backend/order/management/commands/sync_exchange_rates.py`, `backend/order/tests/test_exchange_rates.py`(U1~U6, 6개), `backend/order/tests/test_spec_022.py`(T1~T12, T6은 4-parametrize로 15개) — 기존 파일은 전부 무수정. M8(라이브 백필)은 이번 작업 범위에서 제외, 별도 승인 대기. **계획 대비 발산**: (1) `models.py`의 `ExchangeRate` 클래스 실제 위치는 `:473-489`로, spec.md/plan.md가 인용한 `:495-509`와 어긋난다(라인 드리프트 — 필드/제약은 인용대로 정확: `effective_date` unique, `db_table="orders_exchangerate"`). (2) plan.md가 선례로 지정한 `test_spec_016.py`/`test_spec_018.py`, 그리고 설계 결정 B/E가 인용하는 `repair_refunds.py`는 이 worktree(master 556f1b5 기준)에 존재하지 않는다 — 프롬프트가 사전에 경고한 대로였으며, `CaptureQueriesContext`/`freeze_time` 사용 스타일 선례는 대신 `test_spec_015.py`(`:34,1119,1459`)에서 확인했고, 커맨드 스타일 선례는 `backfill_location.py`+`process_purchase_orders.py` 두 개만 사용했다. (3) **AC-XRATE-008/T8 — acceptance.md 그대로는 검증 불가로 판명**: acceptance.md v1.1.0(D1 정정)가 "freezegun 1.5.5로 직접 실행해 확인함"이라며 제시한 `freeze_time("2026-06-21 23:30:00", tz_offset=9)` 픽스처를 이 저장소의 실제 고정 버전(freezegun 1.5.5, `pyproject.toml:24`)으로 직접 재현한 결과, `datetime.date.today()`와 `django.utils.timezone.localdate()`가 **동일한 값**(`2026-06-22`)을 반환해 두 구현을 전혀 구별하지 못했다 — freezegun 소스(`freezegun/api.py:338-341`의 `FakeDate.today()`, `:400-407`의 `FakeDatetime.now(tz=X)`)를 확인한 결과 두 메서드 모두 `tz` 인자 전달 여부와 무관하게 frozen instant에 `tz_offset`을 무조건 더하도록 구현되어 있어(`tz_offset=0,1,9,-5` 전부 대화형으로 재검증), 이 fixture로는 REQ-XRATE-009를 원리적으로 판별할 수 없다. 구현 자체는 REQ-XRATE-009대로 `timezone.localdate()`를 사용했으나(코드 리뷰로 확인 가능), 이 결함이 있는 fixture로는 이를 증명할 수 없어, T8을 `timezone.localdate()`를 직접 mock(`patch("order.management.commands.sync_exchange_rates.timezone.localdate")`)하고 `datetime.date.today()`는 실제 호스트 시각 그대로 두는 방식으로 재작성했다 — mock이 정확히 1회 호출되었는지와 반환값이 실제로 사용되었는지를 직접 단정하여, freeze_time 방식보다 더 강하게(그리고 환경에 의존하지 않고) `date.today()` mutation을 판별한다. REQ-XRATE-007(다음날 시작) 검증은 원안 그대로 유지했다. acceptance.md의 GWT 시나리오 자체는 수정하지 않았다(변경 권한 밖) — 이 사실만 정정 사항으로 기록한다. (4) **AC-XRATE-005 절대 쿼리 수 실측**: `SYNC_QUERY_COUNT = 4`(SAVEPOINT + 존재확인 SELECT + `bulk_create` INSERT + RELEASE SAVEPOINT, pytest-django의 트랜잭션 래핑으로 인한 savepoint 2건 포함 — D7이 예견한 그대로), N=3/N=10 양쪽 동일, `orders_exchangerate` 참조 쿼리는 양쪽 모두 정확히 2건으로 REQ-XRATE-012를 만족함을 확인. (5) D16(임포트 형태) 함정을 의도적 mutation으로 직접 재현: `from order import exchange_rates` + 모듈-한정 호출로 바꾸면, 이 SPEC이 채택한 patch 대상(`order.management.commands.sync_exchange_rates.fetch_usd_krw_rate`)이 해당 모듈에 그 이름 자체가 없어 patch 시점에 `AttributeError`로 즉시, 크게 실패한다(plan.md가 우려한 "조용한 no-op → 실제 네트워크 호출"보다 오히려 더 명확한 실패 신호) — 올바른 임포트 형태(`from order.exchange_rates import fetch_usd_krw_rate`)로 원복 후 재확인. **회귀**: M0 베이스라인(변경 전) `pytest order/tests/ --no-cov`는 799 passed, 3 failed(`test_spec_008.py`의 마진 테스트 3건 — `exchange_rate_today` 픽스처가 `dt_module.date.today()`를 쓰는 문서화된 KST 00:00~09:00 타임존 플레이키니스, 이 SPEC과 무관, `test_spec_008.py:101-114` 계열). M6 최종(변경 후) 전체 스위트는 **823 passed, 0 failed**(1663.44s) — 신규 21건(U1~U6 6개 + T1~T12 15개, T6은 4-case parametrize) 전부 통과, 위 3건도 이번 실행 시각(00:00~09:00 KST 창을 벗어남)에는 통과해 무관함을 재확인했다. `git diff --stat`로 `serializers.py`/`urls.py`/`views.py`/`models.py`/`pyproject.toml` 무수정 확인(REQ-XRATE-002/018/023), `ruff check` 신규 이슈 0. 라이브 DB 쓰기 및 git 커밋은 발생하지 않았다(M8은 별도 승인 대기). |
| 1.1.0 | 2026-08-14 | ggajo | plan-auditor 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-022-review-1.md`, iteration 1, FAIL/APPROVE WITH CHANGES, 0.66) 반영. 감사가 확인한 것(무변경): `file:line` 인용 약 40건 중 39건 정확, 손계산 전부 재현($32.45/$35.20/$2.75, 8.5%, 90.1%, 57일), 범위 규율 통과(밀반입 0건), AC-XRATE-005 (a)의 절대값 고정 방식 자체는 정확. **차단 결함 3건 해소**: D1(critical) — AC-XRATE-008이 `date.today()` mutation을 못 잡는 문제(freezegun 1.5.5 실행으로 실증됨 — freezegun은 호스트 OS 타임존을 읽지 않고 `frozen instant + tz_offset`(기본 0)으로 대체하므로 `freeze_time("2026-06-21 12:00:00")`에서는 `date.today()`와 `timezone.localdate()`가 우연히 같은 날짜를 반환했다)를 픽스처를 `freeze_time("2026-06-21 23:30:00", tz_offset=9)`(자정 근처 UTC 시각 + tz_offset=9가 필수 — `date.today()`→`2026-06-22`, `timezone.localdate()`→`2026-06-21`로 실제로 갈린다)로 교체해 해소. D2(critical) — spec.md의 AC-XRATE-006이 `fetch_usd_krw_rate`가 raw `urllib`/`json` 예외를 직접 발생시킨다고 서술해, 설계 결정 F/REQ-XRATE-015가 요구하는 `except ExchangeRateFetchError`만 잡는 커맨드 구현에서 그 예외들이 핸들러를 빠져나가 정상 구현이 이 AC에서 실패하던 문제(acceptance.md 버전과 서로 다른 두 테스트가 같은 AC ID 아래 존재)를 acceptance.md 버전(mock이 이미 `ExchangeRateFetchError`를 발생)에 맞춰 정정. D3(critical) — 백필 대상 범위(2026-06-19~2026-08-14, 57일 중 주말 16일)에서 필연적으로 발생하는 중복 echo 게시일(예: 2026-06-19(금) echo가 06-20(토)·06-21(일) 요청에서도 반환되어 `bulk_create`가 `unique=True` 위반으로 `IntegrityError`)에 대응하는 REQ/AC가 전무해 M8 첫 백필이 반드시 깨지던 문제를 REQ-XRATE-024(중복 echo 게시일 압축) + AC-XRATE-012(주말 포함 범위로 직접 판별) 신설로 해소. **주요 결함 6건 해소**: D4(major) — 기존 117개 레코드가 "한국 공휴일" 달력이 아니라 **미국 시장 휴장일 달력**(MLK 01-19, Presidents' 02-16, Memorial 05-25 — 전부 월요일, 설날 02-17·근로자의날 05-01은 존재)을 따른다는 사실관계 오류를 정정하고, REQ-XRATE-019의 근거를 "세 달력(미국/ECB/한국)이 서로 다르며 폴백이 흡수한다"로 재작성하며 TARGET 휴장일(성금요일 등) 값 소실이라는 순방향 결과를 명시. D5(major) — AC-XRATE-006이 stderr를 전혀 단정하지 않아 REQ-XRATE-016/017의 stderr 조항에 검증자가 없던 문제를 stderr 캡처 + 날짜/메시지 포함 단정 추가로 해소. D6(major) — 설계 결정 B의 range 엔드포인트 기각 근거 중 (1)이 순환논증(그 선택이 만든 REQ-XRATE-003으로 그 선택을 정당화), (2)가 오적용(Shopify는 벌크 엔드포인트가 없어 순차이고 Frankfurter는 있음)이던 것을 삭제하고, "날짜별 실패 격리는 날짜별 호출에서만 성립한다"는 진짜 근거로 재작성. 후속 과제 1에 range 엔드포인트가 후속 과제 4/D3도 함께 해소한다는 사실을 명시. D7(major) — AC-XRATE-005 clause (b)에 단정문이 없던 것("전제가 성립한다"는 서술뿐)을 "정확히 2건(존재확인 1 + `bulk_create` 1)"으로 구체화하고, 측정 창을 spec.md("쓰기 단계")·acceptance.md("커맨드 전체")로 서로 다르게 서술하던 것을 acceptance.md 쪽("커맨드 전체")으로 통일(명시적 `--start`/`--end`를 쓰므로 두 창이 실제로 일치함을 명시) — pytest-django의 트랜잭션 래핑으로 SAVEPOINT 쿼리가 섞여 (a)의 절대값이 2가 아닐 수 있다는 점도 명시. D9(major) — read-then-insert가 동시 실행 경쟁(cron 중복 실행 등)에 취약해 `unique=True` 위반이 `IntegrityError`로 노출되던 문제를 `bulk_create(..., ignore_conflicts=True)` 채택(설계 결정 G, 존재확인 쿼리·쓰기 단계 쿼리 수·"이미 존재해 건너뜀" 요약은 무영향)으로 해소 — 부수적으로 D3의 방어를 이중화하고 D17(배치 쓰기 실패 경로)의 실질적 발생 가능성도 낮춘다. **부수 결함(minor) 9건 해소**: D8 — `urlopen` 모킹이 이 저장소에 전례가 없다는 사실(전례는 `_get_with_headers` 헬퍼 모킹이지 `urlopen` 자체가 아님, `grep -rn urlopen backend/order/tests/` 0건)과 bytes+context-manager 반환 형태를 "관례를 따른다" 대신 "신규 관례를 수립한다"로 정정. D10 — `process_purchase_orders.py:114-118` 인용(`plan.md`)이 실제로는 `:180-182`였던 오류를 정정하고 위 v1.0.0 HISTORY의 "전수 재검증" 주장 수위를 낮춤. D11 — acceptance.md 공통 모킹 관례 문단의 자기모순 2건(U1~U6은 `urlopen`을 모킹하는데 "모든 시나리오"라 서술한 것, "항상 문자열로 비교"가 스스로의 괄호 설명과 모순되던 것)을 정정. D12 — spec.md의 "+0.03%"가 실제로는 "−0.03%"(DB가 Frankfurter보다 낮음)였던 부호 오기를 정정. D13 — EARS 라벨 8곳(REQ-XRATE-004/017/018~023의 Unwanted→Ubiquitous 재라벨, AC-XRATE-001/004/008/010/011의 라벨·`shall` 표현 정정)과 REQ-XRATE-018~023의 주어("This SPEC"→"The system")를 정정 — 번호는 변경하지 않았다(MP-1, 세 개의 traceability 표 보존). D14 — acceptance.md AC-XRATE-001의 mock 반환값이 문자열("1500.00" 등)이던 것을 REQ-XRATE-001의 `Decimal` 계약에 맞춰 `Decimal("1500.00")` 등으로 정정. D15 — AC-XRATE-006의 DB 미변경 단정이 단일 날짜만 확인해 다른 날짜에 쓰인 sentinel row를 못 잡던 것을 AC-XRATE-009와 동일하게 `ExchangeRate.objects.count()` 전체 불변 단정으로 강화. D16 — `plan.md`에 `from order.exchange_rates import fetch_usd_krw_rate` 임포트 형태 강제를 명시(다른 임포트 형태를 쓰면 모킹 대상이 조용히 빗나가 실제 네트워크를 탄다). D17 — REQ-XRATE-016이 배치 쓰기 자체가 실패하는 경로(그 경우 이미 보고된 조회 실패들이 요약되지 못함)를 다루지 않던 것을 설계 결정 E에 명시적으로 부기(D9의 `ignore_conflicts=True` 채택으로 이 경로의 실질 발생 가능성이 크게 줄었다는 점도 함께 기록). D18 — REQ-XRATE-005/006에 대한 traceability 표와 개별 AC의 `Traces:` 목록이 서로 어긋나던 것(REQ-005가 AC-001의 Traces에는 있지만 표에는 없음, REQ-006이 표에는 AC-008도 포함하지만 AC-008의 Traces에는 없음)과 acceptance.md 품질 게이트 표가 U1~U6에 REQ-002를 잘못 배정한 것을 정정. REQ 23개→24개(REQ-XRATE-024 신설) + AC 11개→12개(AC-XRATE-012 신설). |

---

## 문제 정의

`ExchangeRate` 모델(`backend/order/models.py:495-509`)은 `effective_date`(유니크), `rate`(`Decimal(10,2)`) 두 필드만 가진 단순 일별 환율 테이블이며, `OrderDetailSerializer._get_exchange_rate`(`backend/order/serializers.py:176-187`)가 `effective_date__lte=주문일` 조건으로 가장 최근 레코드를 폴백 조회해 마진 계산(SPEC-ORDER-009, SPEC-ORDER-021)에 사용한다. 이 테이블에 데이터를 채워 넣는 자동화 경로가 이 저장소 어디에도 없다 — 기존 API(`backend/order/urls.py:182-183`의 `ExchangeRateListCreateView`/`ExchangeRateDetailView`, SPEC-ORDER-009 REQ-004~009)는 수기 CRUD만 제공하며, `backend/order/management/commands/`에도 환율 갱신 커맨드가 없다.

그 결과 (오케스트레이터가 이 세션에 라이브 DB를 직접 조회해 확인한 값):

- `ExchangeRate` 레코드는 117건, 날짜 범위는 2026-01-02 ~ **2026-06-18**(최신 레코드, `rate=1540.64`)에서 멈춰 있다.
- 요일 분포는 월 21 / 화 24 / 수 24 / 목 24 / 금 24, 토 0 / 일 0 — 평일만 존재. **미국 시장 휴장일 달력(MLK Day/Presidents' Day/Memorial Day)을 따르는 피드로 보인다**(아래 근거).
- 3일 초과 공백 구간이 3곳 있다(2026-01-16→01-20, 2026-02-13→02-17, 2026-05-22→05-26). 세 구간에서 빠진 평일은 각각 **2026-01-19(월, MLK Day)**, **2026-02-16(월, Presidents' Day)**, **2026-05-25(월, Memorial Day)**로, 셋 다 미국 연방 공휴일이며 셋 다 월요일이다(요일 분포에서 월요일만 21건으로 다른 요일보다 3건 적은 이유이기도 하다) — 한국 공휴일이 아니다. 반증: 설날 2026-02-17(화)과 근로자의날 2026-05-01(금)은 둘 다 레코드가 존재한다(화=24건 전부, 금=24건 전부에 포함) — 한국 달력이었다면 둘 다 빠졌어야 한다. ECB/TARGET 달력도 아니다 — 성금요일 2026-04-03과 2026-05-01(둘 다 TARGET 휴장일)도 레코드가 존재한다(금=24건 전부에 포함). 이 SPEC 작성 세션이 재계산한 값(2026-01-02~2026-06-18 사이 평일 120일 − 결측 3일 = 117일, 월요일 24 − 3 = 21)이 오케스트레이터가 보고한 행 수·요일 분포와 정확히 일치해, 이 해석을 뒷받침한다. **이 SPEC 적용 이후의 순방향 결과**: 이 SPEC이 채우는 신규 레코드는 Frankfurter(ECB/TARGET 달력)를 따르므로, TARGET 휴장일(성금요일, 부활절 다음 월요일, 5월 1일, 12월 25/26일 등) 값이 앞으로는 채워지지 않는다 — 기존 117건이 갖고 있던 이 날짜들의 값과 다른 결측 패턴이 생긴다는 뜻이다. `_get_exchange_rate`의 `effective_date__lte` 폴백이 이 차이를 그대로 흡수하므로 동작에는 영향이 없지만, 데이터 형태가 바뀐다는 사실은 명시해 둔다.
- 가장 최근 주문(`Order.shopify_created_at`)은 2026-08-13이다. 전체 주문 3,410건 중 2026-06-18 이후 주문이 **3,072건(90.1%)**이며, 이들 전부가 `_get_exchange_rate`의 `effective_date__lte` 폴백 규칙에 의해 2026-06-18 레코드(`rate=1540.64`)로 마진을 계산하고 있다.

이 세션에 api.frankfurter.dev(ECB 기준 무료 환율 API, 키 불필요)로 직접 대조한 실제 값:

| 날짜 | DB 저장값 | Frankfurter 실측값 | 차이 |
|---|---|---|---|
| 2026-01-02 | 1444.45 | 1444.87 | −0.03%(DB가 더 낮음) |
| 2026-06-18 | 1540.64 | 1538.89 | +0.11% |
| 2026-08-13 | (레코드 없음, 폴백으로 1540.64 사용) | **1420.29** | **+8.5% 과대** |

`OrderDetailSerializer._compute_margin_usd`(`backend/order/serializers.py:189-204`, SPEC-ORDER-021이 배송비/한국창고비를 추가로 반영)는 `confirmed_cost_usd = confirmed_cost_krw / er.rate`로 KRW→USD를 환산한다. 환율이 실제보다 부풀려져 있으면(분모가 큼) `confirmed_cost_usd`가 실제보다 작게 계산되고, `margin_usd = total_price_usd - confirmed_cost_usd - ...`이므로 마진이 실제보다 **더 크게** 표시된다 — 확정원가 50,000원 라인아이템 기준으로 현재 환율(1540.64)은 $32.45, 실제 환율(1420.29)은 $35.20로, 주문당 약 $2.75의 마진 과대 계상이 발생한다. 이 왜곡이 전체 주문의 90.1%에 매일 누적되고 있다.

## 목표

1. 매일(또는 그와 유사한 주기로) `ExchangeRate` 테이블을 외부 소스로부터 자동 갱신하는 Django management command를 도입한다.
2. 2026-06-19부터 오늘까지의 공백 구간을 동일한 커맨드로 백필한다 — 별도의 일회성 백필 스크립트를 만들지 않는다.
3. 향후 데이터 소스를 한국수출입은행 공식 매매기준율로 교체할 수 있는 단일 함수 확장 지점을 남긴다(이 SPEC 자체는 그 연동을 구현하지 않는다).
4. `_get_exchange_rate`(`backend/order/serializers.py:176-187`)의 기존 폴백 로직과 SPEC-ORDER-021의 비용 계산 공식은 무수정으로 유지한다 — 이 SPEC은 순수하게 `ExchangeRate` 테이블을 채우는 데이터 파이프라인이다.

## 관련 SPEC

- **SPEC-ORDER-009** — `ExchangeRate` 모델, `_get_exchange_rate` 폴백 조회, CRUD API(`GET/POST /api/exchange-rates/`, `GET/PUT/DELETE /api/exchange-rates/{date}/`) 도입. 이 SPEC은 모델과 폴백 로직을 무수정으로 재사용하고, CRUD API는 수기 개별 보정 경로로 그대로 남긴다.
- **SPEC-ORDER-021** — 마진 계산에 배송비·한국창고비를 반영하며 `_get_exchange_rate`를 재사용. 이 SPEC이 채우는 환율 데이터가 정확해질수록 SPEC-ORDER-021의 마진 계산도 함께 정확해지지만, 이 SPEC은 SPEC-ORDER-021의 비용 계산 공식이나 필드를 전혀 변경하지 않는다.
- **원격 DB 지연 관례(SPEC-ORDER-021 설계 결정 F)** — `backend/.env`가 가리키는 DB가 원격 RDS(`us-west-2`)라는 사실을 이 SPEC의 트랜잭션 경계 설계 결정(설계 결정 E)에도 동일하게 적용한다.

## 범위 — 델타

| 마커 | 대상 | 내용 |
|---|---|---|
| [NEW] | `backend/order/exchange_rates.py` | 외부 환율 소스 조회 계약 함수(`fetch_usd_krw_rate`) + `ExchangeRateFetchError` 정의. `shopify_orders.py`와 나란한 위치의 신규 모듈. |
| [NEW] | `backend/order/management/commands/sync_exchange_rates.py` | 백필과 정기 동기화를 모두 처리하는 단일 management command. |
| [NEW] | `backend/order/tests/test_exchange_rates.py` | `fetch_usd_krw_rate`의 단위 테스트(`urllib.request.urlopen` 모킹). **주의(D8 정정)**: `test_shopify_orders.py`는 `urlopen`을 모킹하지 않는다 — `order.shopify_orders._get_with_headers`라는 모듈 레벨 헬퍼를 모킹한다(`grep -rn urlopen backend/order/tests/` 결과 0건). `fetch_usd_krw_rate`는 그런 헬퍼가 없으므로 `urlopen` 자체를 모킹해야 하며, 이는 이 저장소에 전례가 없는 **신규** 모킹 지점이다 — "기존 관례를 따른다"가 아니라 "새 관례를 수립한다"로 이해해야 한다. `urlopen`은 컨텍스트 매니저이자 `.read()`가 `bytes`를 반환하므로, mock은 `mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{...}'` 형태여야 한다(딕셔너리를 직접 반환하도록 모킹하면 `json.loads`가 `TypeError`를 낸다). |
| [NEW] | `backend/order/tests/test_spec_022.py` | `sync_exchange_rates` 커맨드의 통합 테스트(AC-XRATE-001~012, v1.1.0) — `fetch_usd_krw_rate`를 모킹해 네트워크를 타지 않는다. |
| [EXISTING] | `backend/order/models.py:495-509`(`ExchangeRate`) | 무수정 — 신규 필드나 마이그레이션 없음. |
| [EXISTING] | `backend/order/serializers.py:176-187`(`_get_exchange_rate`) | 무수정 — REQ-XRATE-019. |
| [EXISTING] | `backend/order/views.py:233-248`(`ExchangeRateListCreateView`, `ExchangeRateDetailView`), `backend/order/urls.py:182-183` | 무수정 — 기존 수기 CRUD API를 그대로 유지하고, 이 SPEC은 신규 API 엔드포인트를 추가하지 않는다(REQ-XRATE-023 — v1.0.0에서 이 셀이 잘못 "REQ-XRATE-024"를 가리키고 있었다; 이번 v1.1.0에서 정정). |
| [EXISTING] | `backend/order/shopify_orders.py` | 무수정 — 이 파일은 Shopify 전용이며, 이 SPEC의 환율 조회 로직을 이 파일에 추가하지 않는다(범위 분리). |

---

## 요구사항 (EARS)

### 모듈 1 — 외부 데이터 소스 계약

**REQ-XRATE-001** (Ubiquitous): The system shall access exchange rate data exclusively through a single contract function `fetch_usd_krw_rate(request_date: date) -> tuple[date, Decimal]` defined in `backend/order/exchange_rates.py`, which returns `(published_date, rate)` on success and raises `ExchangeRateFetchError` (defined in the same module) on any failure.

**REQ-XRATE-002** (Ubiquitous): The first implementation of this contract shall call the Frankfurter API (`GET https://api.frankfurter.dev/v1/{YYYY-MM-DD}?base=USD&symbols=KRW`, no API key required) using the stdlib `urllib.request` module, matching the existing HTTP-client convention in `backend/order/shopify_orders.py:14-20`(`_get_with_headers`) — no new HTTP dependency (`requests`, `httpx`, etc.) is added to `backend/pyproject.toml`. **정정(v1.1.3, 라이브 백필 인시던트 반영)**: 요청은 반드시 stdlib 기본 User-Agent(`Python-urllib/3.x`)가 아닌 명시적 `User-Agent` 헤더를 포함해야 한다 — Frankfurter는 기본 User-Agent를 `HTTP 403`으로 차단한다(이 세션에 라이브로 확인: `Request(url)` → 403, `Request(url, headers={"User-Agent": "scm-v2/1.0"})` → 200). `fetch_usd_krw_rate`는 `USER_AGENT = "scm-v2/1.0"` 모듈 상수를 `exchange_rates.py`에 정의하고 `Request(url, headers={"User-Agent": USER_AGENT})` 형태로 사용한다. **함정 — 데이터 소스 교체 시 재현 가능**: 이 요구는 U1~U8 어떤 단위 테스트로도 드러나지 않는다 — 전부 `urllib.request.urlopen` 자체를 모킹하므로(D8) 실제 HTTP 계층(그리고 그 계층이 주입하는 기본 User-Agent)을 전혀 타지 않는다. REQ-XRATE-004의 확장 지점으로 향후 데이터 소스(예: 한국수출입은행)를 교체할 때, 그 소스도 봇 트래픽을 유사하게 차단할 수 있으므로 실제 라이브 호출로 검증하기 전에는 이 함정이 재발할 수 있음을 명시해 둔다.

**REQ-XRATE-003** (Event-Driven): When determining the date under which to store a fetched rate, the system shall use the `date` field echoed in the API response body, not the date that was requested — because Frankfurter returns the rate for the nearest prior publication date (and echoes that actual date) when the requested date is not itself a publication day.

**REQ-XRATE-004** (Ubiquitous): The contract function shall not embed retry logic, response caching, or a provider-selection configuration mechanism — replacing the data source (e.g., with 한국수출입은행 매매기준율) shall require only rewriting this one function to the same signature and exception contract, not modifying the management command that calls it.

### 모듈 2 — 동기화 커맨드와 범위 계산

**REQ-XRATE-005** (Ubiquitous): The system shall provide exactly one Django management command, `sync_exchange_rates`, that handles both the initial gap backfill (2026-06-19 onward) and ongoing periodic synchronization — no separate one-off backfill command shall be created.

**REQ-XRATE-006** (Ubiquitous): `sync_exchange_rates` shall accept optional `--start YYYY-MM-DD` and `--end YYYY-MM-DD` arguments.

**REQ-XRATE-007** (State-Driven): While `--start` is not given, the system shall compute the start date as the day after the most recent `ExchangeRate.effective_date` currently stored.

**REQ-XRATE-008** (Unwanted): If `--start` is not given and no `ExchangeRate` record exists at all, then the system shall raise `django.core.management.base.CommandError` rather than computing an undefined default.

**REQ-XRATE-009** (State-Driven): While `--end` is not given, the system shall compute the end date as `django.utils.timezone.localdate()` — not Python's `datetime.date.today()` — because this project's settings use `TIME_ZONE = "UTC"` with `USE_TZ = True` (`backend/config/settings/base.py:92,94`), and `date.today()` reads the OS's local date, which drifts a day ahead of the UTC date the rest of the system uses for KST-zone machines during the first 9 hours of each local day (documented precedent: `backend/order/tests/test_spec_008.py:101-114`).

**REQ-XRATE-010** (Unwanted): If the resolved (or given) start date is later than the resolved (or given) end date, then the system shall perform no fetch and no database write, and shall exit with status code 0.

### 모듈 3 — 조회 및 배치 쓰기

**REQ-XRATE-011** (Ubiquitous): For each date in the resolved `[start, end]` range, the system shall call `fetch_usd_krw_rate` once, collecting successes as `(published_date, rate)` pairs and failures as `(requested_date, error)` pairs, and shall continue attempting the remaining dates after any single date's fetch fails.

**REQ-XRATE-012** (Ubiquitous): After all dates in the range have been attempted, the system shall perform the database write as exactly two queries regardless of how many dates were in the range: (a) one query using `effective_date__in=<published dates fetched this run>` to determine which of those dates already have a stored record, and (b) one `bulk_create` call writing only the `ExchangeRate` rows for published dates that do not already exist — a per-date `get_or_create`/`update_or_create` loop shall not be used.

**REQ-XRATE-013** (Unwanted): If a published date from this run's fetch results already has a stored `ExchangeRate` record, then the system shall not modify that record's `rate` — this applies even when the newly fetched rate differs from the stored value, so that a manually corrected record (via the existing `PUT /api/exchange-rates/{date}/` endpoint, SPEC-ORDER-009 REQ-007) is never silently reverted by an automated run.

**REQ-XRATE-014** (Ubiquitous): The database write described in REQ-XRATE-012 shall be wrapped in a single `django.db.transaction.atomic()` block scoped only to the two queries themselves — this transaction shall not span the per-date HTTP fetch loop (REQ-XRATE-011).

### 모듈 4 — 실패 처리 및 종료 코드

**REQ-XRATE-015** (Unwanted): If any date's fetch fails (network error, non-200 response, malformed JSON, or a response body missing the `KRW` key), then the system shall record that date as failed and shall not let the failure abort the fetch loop for the remaining dates.

**REQ-XRATE-016** (Unwanted): If one or more dates failed in a given run, then, after successfully writing every date that did succeed, the system shall raise `CommandError` so the process exits with a non-zero status code, and shall write each failed date and its error to stderr individually before raising.

**REQ-XRATE-017** (Ubiquitous): The system shall not swallow any fetch or database failure silently — every failure shall be visible on stderr and shall be reflected in the process's final exit code.

### 모듈 5 — 범위 경계

**REQ-XRATE-018** (Ubiquitous): The system shall not modify `OrderDetailSerializer._get_exchange_rate`(`backend/order/serializers.py:176-187`) or any margin/cost calculation logic (SPEC-ORDER-008, SPEC-ORDER-009, SPEC-ORDER-021) as part of this SPEC.

**REQ-XRATE-019** (Ubiquitous): The system shall not filter, skip, or otherwise omit dates published by the data source as part of this SPEC — every date the source publishes shall be stored as-is, regardless of which calendar it follows. (Rationale, corrected per audit D4: the existing 117 records follow a US market-holiday calendar, not a Korean one — see 문제 정의. Frankfurter follows the ECB/TARGET calendar. Neither reconciliation between the two, nor reconciliation with the Korean public-holiday calendar, is performed; the `effective_date__lte` fallback in `_get_exchange_rate` absorbs whatever gaps or overlaps result.)

**REQ-XRATE-020** (Ubiquitous): The system shall not implement 한국수출입은행 매매기준율 integration as part of this SPEC — only the extension point defined by REQ-XRATE-001/004 is in scope.

**REQ-XRATE-021** (Ubiquitous): The system shall not modify the `rate` value of any of the 117 pre-existing `ExchangeRate` records, or of any record this SPEC's own command has already written in a prior run (REQ-XRATE-013), as part of this SPEC — no retroactive correction of the small deviations between the existing records and Frankfurter's values is performed.

**REQ-XRATE-022** (Ubiquitous): The system shall not introduce an in-app scheduler (Celery, APScheduler, django-q, or similar) as part of this SPEC — periodic execution of `sync_exchange_rates` is an operations-layer responsibility (external cron, Windows Task Scheduler, etc.), external to this SPEC.

**REQ-XRATE-023** (Ubiquitous): The system shall not add a new API endpoint mirroring `POST /api/orders/sync/`(`OrderSyncView`, `backend/order/urls.py:60`) as part of this SPEC — `sync_exchange_rates` is exposed only as a management command.

### 모듈 6 — 중복 echo 게시일 압축 (감사 D3 반영, v1.1.0 신설)

**REQ-XRATE-024** (Unwanted): If two or more requested dates within a single run resolve (via REQ-XRATE-003's echoed-date keying) to the same published date, then the system shall write exactly one `ExchangeRate` row for that published date, not one row per requesting date.

이 요구사항이 필요한 이유: 2026-06-19(금)는 M8 백필 범위(spec.md 목표 2번, 2026-06-19~오늘)의 시작일이며, 2026-06-20(토)·2026-06-21(일) 요청은 둘 다 Frankfurter의 최근 발행일 규칙에 따라 `date=2026-06-19`를 echo한다 — 이 세 요청이 압축 없이 `to_create`에 담기면 동일 `effective_date=2026-06-19`를 가진 `ExchangeRate` 객체 3개가 `bulk_create`에 전달되어 `unique=True`(`models.py:501`) 위반으로 `IntegrityError`가 발생한다. 57일 백필 범위에는 이런 주말 쌍이 8개 있어(REQ-XRATE-024 없이는) M8의 첫 실행에서 반드시 발생하는 결함이다.

---

## 인수 기준

[HARD] 각 인수 기준은 손으로 계산했거나 실행해 관측한 정확한 값을 단정한다. 각 항목은 자신을 깨뜨리는 mutation을 명시한다. 외부 HTTP 호출은 전부 모킹하며 실제 네트워크를 타지 않는다 — U1~U6(`fetch_usd_krw_rate` 단위 테스트)은 `urllib.request.urlopen` 자체를 모킹하고(이 저장소에 전례가 없는 신규 모킹 지점, D8 정정 — `test_shopify_orders.py`는 `urlopen`이 아니라 `_get_with_headers` 헬퍼를 모킹한다), AC-XRATE-001~012(T1~T12)는 `fetch_usd_krw_rate` 자체를 모킹한다. 실행 가능한 Given/When/Then 시나리오는 `acceptance.md`에 있으며 동일한 `Traces:` 목록을 인용한다.

**AC-XRATE-001** (Event-Driven) — 정상 범위 동기화: N=3개 날짜 각각 고유한 값으로 저장된다. Traces: REQ-XRATE-005, REQ-XRATE-006, REQ-XRATE-011, REQ-XRATE-012. **When** `--start`/`--end`로 연속 3일을 지정하고 `fetch_usd_krw_rate`를 날짜별로 서로 다른 3개 rate 값을 반환하도록 모킹한 뒤 커맨드를 실행하면, the system **shall** 정확히 3건의 `ExchangeRate` 레코드를 생성하며 각 레코드의 `rate`가 그 레코드 자신의 `effective_date`에 대응하는 모킹된 값과 정확히 일치하도록 한다.
*Mutation*: 조회 결과를 취합하는 과정에서 날짜-값 매핑이 뒤섞이면(예: 공유 가변 누적 변수 재사용, `zip` 순서 오류) 일부 또는 전체 레코드가 다른 날짜의 값을 갖게 되어 이 AC가 실패한다 — 3개 값이 모두 다르므로 뒤섞임이 반드시 드러난다(값이 동일했다면 이 mutation은 관측 불가능했을 것이다).

**AC-XRATE-002** (Event-Driven) — echoed date 키잉. Traces: REQ-XRATE-003. **When** 요청한 날짜와 API 응답의 `date` 필드가 다른 경우(예: 요청일이 게시일이 아닌 날 — 응답이 더 이전의 실제 게시일을 echo), the system **shall** echo된 날짜로 레코드를 저장하고, 요청한 날짜로는 레코드를 저장하지 않는다.
*Mutation*: 요청일을 그대로 `effective_date`에 사용하면 요청일 레코드가 생기고 echo된 실제 게시일 레코드는 생기지 않아 이 AC가 실패한다.

**AC-XRATE-003** (State-Driven) — 재실행 멱등성(동일 값). Traces: REQ-XRATE-012. **While** 동일한 `--start`/`--end` 범위에 대해 `fetch_usd_krw_rate`가 두 번째 실행에서도 첫 번째와 동일한 값을 반환할 때, 같은 범위로 커맨드를 두 번 실행하면, the system **shall** 두 번째 실행 후에도 레코드 수와 각 레코드의 값이 첫 번째 실행 직후와 완전히 동일하게 유지한다(추가 레코드 없음, `IntegrityError` 없음).
*Mutation*: 존재 여부를 사전에 필터링하지 않고 두 번째 실행에서도 `bulk_create`를 그대로 시도하면 `effective_date`의 `unique=True` 제약(`models.py:501`)에 의해 `IntegrityError`가 발생해 커맨드 자체가 예외로 실패한다.

**AC-XRATE-004** (Complex) — 기존/수기 보정 레코드는 값이 달라도 덮어쓰지 않는다. Traces: REQ-XRATE-013. **While** 어떤 날짜 D에 대해 이미 `ExchangeRate(effective_date=D, rate=Decimal("1500.00"))`가 저장되어 있고, `fetch_usd_krw_rate`는 D를 요청하면 echo된 날짜가 D이면서 값은 `Decimal("1420.29")`(저장값과 다름)를 반환하도록 모킹되어 있을 때, **When** D를 포함하는 범위로 커맨드를 실행하면, **then** the system **shall** D의 `rate`를 `Decimal("1500.00")`으로 그대로 유지한다(`Decimal("1420.29")`로 갱신하지 않는다).
*이 AC가 AC-XRATE-003과 별도로 필요한 이유*: AC-XRATE-003은 재실행 시 동일한 값을 fetch하므로, 구현이 실제로는 `update_or_create`(값이 같으면 덮어써도 결과가 똑같이 보임)를 쓰더라도 통과해버려 "덮어쓰지 않는다"는 REQ-XRATE-013을 판별하지 못한다 — 이 AC만이 다른 값으로 덮어쓰기 시도를 직접 판별한다.
*Mutation*: 존재 여부 확인 없이 `update_or_create`로 구현하면 D의 `rate`가 `Decimal("1420.29")`로 바뀌어 실패한다.

**AC-XRATE-005** (State-Driven) — 커맨드 실행 전체의 쿼리 수 불변식. Traces: REQ-XRATE-012. **While** 명시적 `--start`/`--end`로 N=3개 날짜와 N=10개 날짜(모두 신규, 기존 레코드와 겹치지 않음)를 각각 별도 실행할 때, `django.test.utils.CaptureQueriesContext`로 `call_command` 호출 **전체**(D7 정정 — 범위 계산부터 배치 쓰기까지 전부, "쓰기 단계만"이 아니다. 명시적 `--start`/`--end`를 쓰므로 최신 저장일 조회 쿼리 자체가 애초에 발생하지 않아 두 정의가 이 시나리오에서는 정확히 같은 쿼리 집합을 가리킨다)를 각각 캡처하면, the system **shall** (a) N=3과 N=10 양쪽에서 동일하고, 구현 시점에 실제로 실행해 관측한 절대값과 일치하는 총 쿼리 수를 발급하고, (b) 그중 `orders_exchangerate`를 참조하는 쿼리는 N=3과 N=10 양쪽에서 **정확히 2건**(존재 확인 `filter(...__in=...)` 1건 + `bulk_create` 1건)이어야 한다(`orders_exchangerate` 참조 여부는 단순 부분 문자열 검사로 충분하다 — `backend/order/models.py` 전체의 `db_table` 선언 17개를 대조한 결과 `orders_exchangerate`는 다른 어떤 테이블명의 부분 문자열도 아니고, 다른 어떤 테이블명도 `orders_exchangerate`의 부분 문자열이 아니기 때문이다).
*측정상 주의*: pytest-django는 각 테스트를 트랜잭션으로 감싸므로, `sync_exchange_rates`의 `transaction.atomic()` 블록이 중첩 트랜잭션(savepoint)으로 실행되어 `SAVEPOINT`/`RELEASE SAVEPOINT` 문이 (a)의 캡처된 쿼리 목록에 섞여 들어간다 — 이 때문에 (a)의 절대값은 "2"가 아닐 것이다(이것이 정상이며, 절대값은 실측으로 고정하는 것이지 2로 "맞추려" 시도해서는 안 된다). savepoint 문은 `orders_exchangerate`를 참조하지 않으므로 (b)의 "정확히 2건" 단정에는 영향이 없다.
*판별력 요건*: 절대값은 이 테스트를 작성하는 시점에 실측해 고정한다(추측값 금지 — `test_spec_018.py:64`의 `UNORDERED_ENDPOINT_QUERY_COUNT = 3` 관례와 동일). N=3과 N=10이 서로 같다는 상대 비교만으로는, 날짜 수와 무관한 상수 추가 쿼리(예: 날짜마다 존재 여부를 개별 확인하지 않더라도 불필요한 카운트 쿼리를 추가로 발급하는 경우)를 잡지 못한다 — 양쪽에 똑같이 더해져 상쇄되기 때문이다(SPEC-ORDER-021 AC-COST-009, SPEC-ORDER-018 `test_unordered_endpoint_query_count_is_unaffected_by_excluded_items` 선례와 동일한 논리).
*Mutation*: 날짜별 `get_or_create` 루프로 구현하면 (a) N=3에서는 최대 6쿼리(존재확인+삽입 ×3), N=10에서는 최대 20쿼리로 서로 달라지고, (b) `orders_exchangerate` 참조 쿼리도 N에 비례해(최대 6/20건) 늘어나 "정확히 2건"과 어긋나 이 AC가 실패한다.

**AC-XRATE-006** (Unwanted) — 실패 처리: 종료 코드가 0이 아니고, DB가 전혀 변경되지 않으며, 실패 정보가 stderr에 나타난다. Traces: REQ-XRATE-015, REQ-XRATE-016, REQ-XRATE-017. **If** 단일 날짜(`2026-07-20`)만 포함하는 범위로 커맨드를 실행하며 그 날짜에 대해 `fetch_usd_krw_rate`가 `ExchangeRateFetchError("2026-07-20: network error (...)")`(또는 그에 준하는, 실패 원인을 담은 메시지 문자열)를 발생시키도록 모킹되어 있다면(**정정, D2**: mock은 raw `urllib.error.URLError`/`HTTPError`/`json.JSONDecodeError`가 아니라 계약 함수가 이미 정규화한 `ExchangeRateFetchError`를 직접 발생시킨다 — 설계 결정 F/REQ-XRATE-015에 따라 커맨드는 `except ExchangeRateFetchError`만 잡으므로, raw 예외를 모킹하면 그 예외가 핸들러를 빠져나가 정상 구현에서도 `CommandError`가 발생하지 않아 이 AC 자체가 실패해버린다 — raw 예외 네 종류가 실제로 `ExchangeRateFetchError`로 정규화되는지는 U3~U6이 계약 함수 레벨에서 이미 검증한다), **then** the system **shall** `CommandError`를 발생시켜(호출 측에서 `call_command`가 `CommandError`를 전파받음) 0이 아닌 종료를 유발하고, 그 날짜에 대한 `ExchangeRate` 레코드를 생성하지 않으며(`ExchangeRate.objects.count()`가 실행 전후 동일 — 단일 날짜 존재 여부만으로는 다른 날짜에 쓰인 sentinel row를 놓칠 수 있으므로 전체 카운트로 확인한다, D15), stderr에 `"2026-07-20"`(실패한 날짜)과 mock에 전달한 오류 메시지 문자열이 모두 나타난다(**신설, D5** — REQ-XRATE-016의 "각 실패 날짜와 오류를 stderr에 개별 기록"과 REQ-XRATE-017의 stderr 가시성 조항을 직접 판별).
*Mutation*: 실패를 무시(swallow)하고 계속 진행해 정상 종료(exit 0)로 끝나면 이 AC가 실패한다 — 종료 코드 판별이 1차 판별력이다. `CommandError`는 발생시키되 stderr에 아무것도 쓰지 않고 요약 메시지만 남기면(예: `CommandError(f"{len(failures)}건 실패")`만 쓰고 개별 날짜·메시지를 stderr에 쓰지 않으면), 종료 코드와 DB 상태는 정상이지만 stderr 단정이 실패한다 — 이것이 stderr 단정이 필요한 이유다(D5, 신설 전에는 이 mutation을 잡는 검증자가 없었다).

**AC-XRATE-007** (Event-Driven) — 부분 실패 시 성공분은 보존된다. Traces: REQ-XRATE-011, REQ-XRATE-014, REQ-XRATE-016. **When** 3일치 범위 중 가운데 1일만 실패하도록(나머지 2일은 서로 다른 값으로 성공) `fetch_usd_krw_rate`를 모킹한 뒤 커맨드를 실행하면, the system **shall** 성공한 2일에 대한 `ExchangeRate` 레코드를 정확한 값으로 생성하고, 실패한 1일에 대한 레코드는 생성하지 않으며, `CommandError`로 인해 0이 아닌 종료 코드를 반환한다.
*Mutation*: 조회(HTTP 루프)와 쓰기를 하나의 `transaction.atomic()`으로 묶어 조회 실패 시 이미 성공한 항목까지 롤백하면, 성공한 2일의 레코드도 생성되지 않아 이 AC가 실패한다 — REQ-XRATE-014("쓰기 단계에만 한정된 트랜잭션")의 직접 판별 지점.

**AC-XRATE-008** (Complex) — 기본 범위 계산: `--start` 생략 시 최신 저장일의 다음 날부터, `--end` 생략 시 오늘(UTC)까지. Traces: REQ-XRATE-007, REQ-XRATE-009. **While** 저장된 `ExchangeRate` 중 가장 최신 `effective_date`가 `2026-06-18`이고, `freeze_time("2026-06-21 23:30:00", tz_offset=9)`(freezegun, `backend/pyproject.toml:24` dev dependency, 선례 `backend/order/tests/test_spec_016.py:583`. **정정, D1**: 자정에 가까운 UTC 시각(`23:30`)과 `tz_offset=9`가 반드시 함께 있어야 한다 — 이유는 아래 판별력 참조)으로 고정되어 있을 때, **when** `--start`/`--end` 없이 커맨드를 실행하면, the system **shall** `fetch_usd_krw_rate`를 정확히 `2026-06-19`, `2026-06-20`, `2026-06-21` 세 날짜에 대해서만(순서 무관, 그 외 날짜는 호출하지 않음) 호출한다.
*Mutation*: 다음 날이 아니라 최신 저장일 자체(`2026-06-18`)부터 다시 조회하면(off-by-one) 호출 인자 목록에 `2026-06-18`이 포함되어 이 AC가 실패한다. `timezone.localdate()` 대신 `datetime.date.today()`를 쓰는 mutation은 **freezegun 1.5.5로 직접 실행해 확인한 결과**(D1), `freeze_time("2026-06-21 23:30:00", tz_offset=9)` 하에서 `date.today()`가 `2026-06-22`를 반환한다 — freezegun은 호스트 OS의 타임존을 전혀 참조하지 않고 `frozen instant(2026-06-21 23:30:00 UTC) + tz_offset(9시간) = 2026-06-22 08:30`을 기준으로 `date.today()`를 대체하기 때문이다. 이 경우 커맨드는 `2026-06-19`~`2026-06-22` 네 날짜를 호출해 세 날짜만 기대하는 이 AC의 단정이 실패한다. 반면 `timezone.localdate()`는 `TIME_ZONE="UTC"`(`backend/config/settings/base.py:92`) 설정 하에서 frozen UTC 시각을 그대로 사용해 `2026-06-21`을 반환하므로 세 날짜만 호출한다. **자정에 가까운 UTC 시각이 필수인 이유**: `freeze_time("2026-06-21 12:00:00", tz_offset=9)`처럼 정오 근처 시각을 쓰면 `+9시간`을 더해도 여전히 `2026-06-21` 안에 머물러(`21:00`) 두 계산 방식이 우연히 같은 날짜를 반환해 이 mutation을 잡지 못한다 — v1.0.0의 `freeze_time("2026-06-21 12:00:00")`(`tz_offset` 없음, 즉 0)가 정확히 이 실패 사례였다: `tz_offset=0`이면 애초에 `date.today()`와 `timezone.localdate()`가 항상 같은 값을 내므로 이 mutation이 어떤 시각을 골라도 걸리지 않는다.

**AC-XRATE-009** (Unwanted) — 시작일이 종료일보다 이후이면 아무 것도 하지 않고 성공 종료한다. Traces: REQ-XRATE-010. **If** `--start`가 `--end`보다 이후인 범위로 커맨드를 실행하면(또는 저장된 최신 날짜가 이미 오늘이라 기본 계산 결과 시작일이 종료일 다음날이 되면), **then** the system **shall** `fetch_usd_krw_rate`를 한 번도 호출하지 않고, DB에 아무 레코드도 쓰지 않으며, 종료 코드 0으로 정상 종료한다.
*Mutation*: 빈 범위에서도 최소 1회 반복이 일어나게 구현하면(예: `range(start, end+1)` 경계 계산 오류로 빈 range가 아닌 1-요소 range가 만들어짐) `fetch_usd_krw_rate`가 호출되어 mock의 호출 횟수 단정이 실패한다.

**AC-XRATE-010** (Unwanted) — 레코드가 전혀 없는 상태에서 `--start` 없이 실행하면 `CommandError`. Traces: REQ-XRATE-008. **If** `ExchangeRate` 테이블이 완전히 비어 있는 상태에서 `--start` 없이(`--end`는 있어도 없어도) 커맨드를 실행하면, **then** the system **shall** `CommandError`를 발생시키고 `fetch_usd_krw_rate`를 호출하지 않는다.
*Mutation*: 빈 테이블에서 "다음 날"을 계산하지 못하는 경우(`.first()`가 `None`을 반환) 이를 방어하지 않고 그대로 `None.effective_date`류의 `AttributeError`로 실패하면, 이 AC가 요구하는 "의도된 `CommandError`"가 아니라 처리되지 않은 예외 타입으로 실패해 이 AC를 만족하지 못한다 — 예외 타입 자체가 판별 지점이다.

**AC-XRATE-011** (Complex) — 회귀: 백필 후 `_get_exchange_rate`가 2026-08-13 주문에 대해 올바른 환율을 반환한다. Traces: REQ-XRATE-003, REQ-XRATE-012, REQ-XRATE-018. **While** `fetch_usd_krw_rate`가 `2026-08-13` 요청에 대해 echo된 날짜 `2026-08-13`, 값 `Decimal("1420.29")`를 반환하도록 모킹되어 있는 상태에서 이 날짜를 포함하는 범위로 `sync_exchange_rates`가 이미 성공적으로 실행되어 있을 때, **when** `shopify_created_at`이 `2026-08-13`인 `Order`에 대해 `OrderDetailSerializer()._get_exchange_rate(order)`를 호출하면(REQ-XRATE-018에 따라 이 메서드 자체는 무수정), the system **shall** `effective_date=2026-08-13`, `rate=Decimal("1420.29")`인 `ExchangeRate` 인스턴스를 반환한다.
*Mutation*: AC-XRATE-002가 잡는 echoed-date 키잉 결함이 여기서도 간접적으로 드러난다 — 요청일을 그대로 저장하는 구현이라면 이 시나리오에서는 요청일과 echo된 날짜가 우연히 같으므로 통과하지만, echo된 날짜가 다른 시나리오와 조합했을 때만 진짜 결함이 드러난다는 한계를 인지한 상태로, 이 AC 자체는 "백필이 끝난 뒤 기존 폴백 로직이 정말로 새 데이터를 집어 오는지"를 회귀 확인하는 것이 주 목적이다 — `_get_exchange_rate`를 실수로 함께 수정해버리는 mutation(REQ-XRATE-018 위반)은 이 AC가 직접 잡는다.

**AC-XRATE-012** (Event-Driven) — 주말을 포함하는 범위에서 중복 echo 게시일이 정확히 한 건으로 압축된다(신설, v1.1.0 — 감사 D3 반영). Traces: REQ-XRATE-024. **When** `2026-06-19`(금)~`2026-06-21`(일) 범위로 커맨드를 실행하며, `fetch_usd_krw_rate`가 세 요청(`2026-06-19`, `2026-06-20`, `2026-06-21`) 전부에 대해 동일한 `(date(2026, 6, 19), Decimal("1530.00"))`을 반환하도록(세 날짜 모두 금요일 게시일을 echo — 주말 이틀 뒤 다음 발행일까지 값이 없는 실제 Frankfurter 동작을 재현) 모킹했을 때, the system **shall** 예외 없이 정상 종료하고, `ExchangeRate.objects.filter(effective_date=date(2026, 6, 19)).count() == 1`이며, `ExchangeRate.objects.filter(effective_date__in=[date(2026,6,20), date(2026,6,21)]).exists() is False`이다.
*이 AC가 필요한 이유*: M8의 첫 백필(2026-06-19~오늘, 57일)에서 이런 주말 쌍이 8번 발생한다 — REQ-XRATE-024(중복 게시일 압축) 없이는 `to_create`에 `effective_date=2026-06-19`인 객체 3개가 담겨 `bulk_create`가 `unique=True`(`models.py:501`) 위반으로 `IntegrityError`를 낸다.
*Mutation*: `fetched` 리스트를 압축 없이 그대로 `to_create`에 매핑하면(`[ExchangeRate(effective_date=d, rate=r) for d, r in fetched]`, 중복 제거 없음) `bulk_create` 호출이 `IntegrityError`를 발생시켜 이 AC가 예외로 실패한다.

### Traceability 검증표

| REQ | 커버하는 AC |
|---|---|
| REQ-XRATE-001 | `plan.md` DoD (계약 함수 시그니처, 코드 리뷰) |
| REQ-XRATE-002 | `plan.md` DoD (코드 리뷰 — urllib 사용, 신규 의존성 없음) |
| REQ-XRATE-003 | AC-XRATE-002, AC-XRATE-011 |
| REQ-XRATE-004 | `plan.md` DoD (코드 리뷰 — 계약 함수에 재시도/캐시/provider 설정 없음) |
| REQ-XRATE-005 | AC-XRATE-001(**D18 정정** — v1.0.0에서 AC-001의 `Traces:`에는 있었으나 이 표에서 누락됨), `plan.md` DoD (git diff — 커맨드 파일 1개) |
| REQ-XRATE-006 | AC-XRATE-001(**D18 정정** — v1.0.0에서 이 표는 AC-008도 나열했으나 AC-008의 `Traces:`는 007/009만 선언한다; AC-008은 인자 생략 시의 기본값 계산을 검증하는 것이지 "인자를 받는다"는 REQ-006 자체를 검증하지 않으므로 제거) |
| REQ-XRATE-007 | AC-XRATE-008 |
| REQ-XRATE-008 | AC-XRATE-010 |
| REQ-XRATE-009 | AC-XRATE-008 |
| REQ-XRATE-010 | AC-XRATE-009 |
| REQ-XRATE-011 | AC-XRATE-001, AC-XRATE-007 |
| REQ-XRATE-012 | AC-XRATE-001, AC-XRATE-003, AC-XRATE-005, AC-XRATE-011 |
| REQ-XRATE-013 | AC-XRATE-004 |
| REQ-XRATE-014 | AC-XRATE-007 |
| REQ-XRATE-015 | AC-XRATE-006 |
| REQ-XRATE-016 | AC-XRATE-006, AC-XRATE-007 |
| REQ-XRATE-017 | AC-XRATE-006 |
| REQ-XRATE-018 | AC-XRATE-011, `plan.md` DoD (git diff — `serializers.py` 무변경) |
| REQ-XRATE-019 | `plan.md` DoD (코드 리뷰 — 날짜 필터링 코드 없음) |
| REQ-XRATE-020 | `plan.md` DoD (git diff — Eximbank 관련 코드 없음) |
| REQ-XRATE-021 | `plan.md` DoD (코드 리뷰 — 갱신 로직이 REQ-XRATE-013과 동일 지점) |
| REQ-XRATE-022 | `plan.md` DoD (git diff — celery/APScheduler/django-q 의존성 추가 없음) |
| REQ-XRATE-023 | `plan.md` DoD (git diff — `urls.py` 무변경) |
| REQ-XRATE-024 | AC-XRATE-012(v1.1.0 신설, 감사 D3 반영) |

24개 요구사항 중 16개(003, 005~018, 024)가 12개 인수 기준으로 직접 커버된다. 나머지 8개(001, 002, 004, 019~023)는 구조/범위 제약이며 `plan.md`의 완료 조건(코드 리뷰, `git diff`)으로 검증한다 — 이들이 여기 해당하는 이유는, "무엇을 하지 않는가/무엇이 하나로 통합되어 있는가"를 규정하는 구조적 제약이라 런타임 단정보다 정적 확인(코드 존재 여부, 파일 개수, 의존성 목록)이 더 직접적인 증거이기 때문이다(SPEC-ORDER-021의 REQ-COST-001/018/019와 동일한 판단 기준).

---

## 설계 결정

**A. 외부 페치 계약의 위치와 형태 — 단일 함수, 플러그인 레지스트리 없음.** `backend/order/exchange_rates.py`(신규)에 `fetch_usd_krw_rate` 함수 하나와 `ExchangeRateFetchError` 예외 클래스 하나만 정의한다. 대안(추상 베이스 클래스 + provider registry, 또는 `settings.py`에 provider 선택 키 추가)을 검토했으나 기각한다 — 현재 구현체가 Frankfurter 하나뿐이고, REQ-XRATE-004가 요구하는 확장 지점은 "같은 시그니처의 함수로 통째로 교체"만으로 충분하다. 구현체가 2개 이상이 되어 런타임에 선택해야 하는 요구가 실제로 생기기 전까지는 provider 추상화가 과설계다(SPEC-ORDER-021 설계 결정 A와 동일한 판단 기준).

**B. 단일-날짜 엔드포인트 채택, range 엔드포인트는 후속 과제로 보류(v1.1.0에서 근거 재작성, 감사 D6 반영).** Frankfurter는 `GET /v1/{start}..{end}?base=USD&symbols=KRW` 형태의 날짜 범위 조회도 지원한다는 것을 이 세션에 WebFetch로 직접 확인했다(`2026-06-19..2026-06-25` 요청 시 `{"rates": {"2026-06-19": {"KRW": ...}, "2026-06-22": {"KRW": ...}, ...}}` 형태로 게시되지 않은 날짜는 키 자체가 없이 반환되며, 단일-날짜 엔드포인트의 "요청일과 다른 날짜를 echo" 하는 모호성이 range 응답에는 없다). 그럼에도 이 SPEC은 계약 함수를 단일-날짜 형태로 채택한다.

**진짜 이유(v1.1.0)**: 날짜별 실패 격리(REQ-XRATE-011, REQ-XRATE-015~017, AC-XRATE-007이 검증)는 날짜별로 독립된 호출이 있어야만 성립한다. range 엔드포인트를 쓰면 한 번의 HTTP 요청이 요청 범위 전체를 대표하므로, 그 요청이 실패하면(네트워크 오류, 타임아웃, 서버 오류) 범위 전체가 all-or-nothing으로 실패한다 — "가운데 하루만 실패해도 나머지는 성공적으로 기록된다"는 이 SPEC의 핵심 견고성 속성(REQ-XRATE-011/016, AC-XRATE-007)을 range 엔드포인트로는 재현할 수 없다(청킹으로 흉내낼 수는 있지만, 그러면 사실상 날짜별 호출로 되돌아가는 것과 다를 게 없다). 초기 백필 대상이 57일 내외로 작아 순차 호출의 실질적 비용이 낮다는 점(오프라인 배치이지 사용자가 기다리는 요청-응답 경로가 아님)도 이 선택의 비용을 낮춘다.

**v1.0.0의 근거 (1)(2)는 재검토 결과 기각한다(감사 D6):** (1) "REQ-XRATE-003이 요구하는 echoed-date 키잉이 단일-날짜 엔드포인트를 정당화한다"는 순환논증이었다 — REQ-XRATE-003은 단일-날짜 엔드포인트를 먼저 선택했기 때문에 생긴 요구사항이지, 그 선택과 무관하게 존재하는 독립적 근거가 아니다. "발행일 기준으로 각 환율을 저장한다"는 실제 목표는 range 엔드포인트가 오히려 더 직접적으로 만족시킨다(응답이 이미 실제 발행일로 키가 매겨져 있고, 비게시일은 키 자체가 없다 — echoed-date 모호성도, D3의 중복 echo 문제도, 57일 중 16일의 낭비되는 주말 요청도 range 엔드포인트에서는 애초에 발생하지 않는다). (2) `repair_refunds.py`(`backend/order/management/commands/repair_refunds.py:60-111`) 선례를 오적용했다 — 그 커맨드가 Shopify를 주문별로 순차 호출하는 것은 **Shopify에 벌크 조회 엔드포인트가 없기 때문**(강제된 패턴)이며, Frankfurter는 벌크(range) 엔드포인트가 **있다**(선택 가능한 패턴). 강제된 선례를 근거로 선택 가능한 대안을 기각하는 것은 방향이 잘못됐다. 덧붙여 `repair_refunds.py`는 `--sleep`(기본 0.3초, `:35-40`)로 API 호출 속도를 조절하는데, 이 SPEC은 그 페이싱 절반만(순차 호출 패턴만) 차용하고 나머지 절반(속도 조절)은 반영하지 않았다 — 공용 무료 API에 57회 연속 요청을 페이싱 없이 보내는 것은 이 SPEC이 인용하는 선례 자체와 일관되지 않는다. **정정**: `plan.md`의 조회 루프 기술적 접근에 `repair_refunds.py`와 동일한 `--sleep` 스타일의 짧은 페이싱을 구현 시 고려하도록 권고 사항으로 추가한다(강제 REQ는 아님 — 57회 일회성 배치의 실패 시 영향이 크지 않고, 매일 실행되는 정기 동기화는 보통 1~3건뿐이라 페이싱 필요성이 낮다).

range 엔드포인트로의 전환은 후속 과제 1로 남긴다 — 채택 시 필요한 변경(REQ-XRATE-001 시그니처를 `fetch_usd_krw_rates(start, end) -> dict[date, Decimal]`로 변경, REQ-XRATE-003을 "소스가 반환한 날짜 키를 그대로 쓴다"로 대체, REQ-XRATE-011의 루프를 단일 호출로 대체, REQ-XRATE-024/AC-XRATE-012의 중복 압축 문제 자체가 사라짐, AC-XRATE-007의 부분 실패 시나리오는 청킹 없이는 재현 불가)은 후속 과제 1에 함께 기록한다.

**C. 백필과 정기 동기화를 하나의 커맨드로 통합.** `--start`/`--end` 인자와 그 기본값 계산(REQ-XRATE-007/009)만으로 최초 백필("57일치 명시적 범위")과 향후 정기 실행("인자 없이 실행 → 최신 저장일 다음날부터 오늘까지")을 모두 처리한다. 별도의 `backfill_exchange_rates` 커맨드를 따로 만드는 대안은 코드 중복과, 두 커맨드가 시간이 지나며 서로 다르게 동작하게 될 위험(예: 한쪽만 멱등성 로직이 갱신되는 등)을 낳으므로 기각한다.

**D. 갱신하지 않는 정책(덮어쓰기 금지).** 이미 저장된 `effective_date`는 새로 조회한 값이 다르더라도 절대 갱신하지 않는다(REQ-XRATE-013). 대안("항상 최신 조회값으로 덮어쓴다")은 두 가지 이유로 기각한다. 첫째, 기존 CRUD API(`PUT /api/exchange-rates/{date}/`, SPEC-ORDER-009 REQ-007)로 운영자가 수기 보정한 레코드를 자동 동기화가 다음 실행에서 조용히 되돌려버릴 수 있다 — 이는 REQ-XRATE-013이 명시적으로 방지하려는 상황이다. 둘째, "기존 117개 레코드에 대한 소급 재계산을 하지 않는다"(REQ-XRATE-021)는 결정과 논리적으로 동치다 — 소급 재계산을 안 하기로 했다면, 신규 자동 동기화도 재실행마다 과거 값을 덮어써서는 안 된다.

**E. 조회(HTTP)와 쓰기(DB)의 명확한 분리, 트랜잭션은 쓰기에만 한정.** 날짜별 조회는 순차적이고 실패를 허용하며(REQ-XRATE-011), 그 결과를 모은 뒤 쓰기만 단일 `transaction.atomic()`으로 묶는다(REQ-XRATE-012, 014). 대안(조회+쓰기 전체를 하나의 트랜잭션으로 묶어 인터리브)은 두 가지 이유로 기각한다. 첫째, 이 프로젝트가 원격 RDS(`us-west-2`, `backend/.env`, SPEC-ORDER-021 설계 결정 F가 이미 같은 배포 환경을 근거로 든 전례)를 쓰므로, 최대 57회의 순차 외부 HTTP 호출(각 최대 `REQUEST_TIMEOUT=30`초, `shopify_orders.py:11`과 동일한 상수를 재사용)에 걸쳐 DB 트랜잭션을 열어 두는 것은 커넥션/락을 불필요하게 오래 점유하는 안티패턴이다. 둘째, 부분 실패 시 이미 성공한 조회분까지 롤백되어 REQ-XRATE-011("실패해도 나머지 날짜는 계속")의 취지와 REQ-XRATE-016("성공분은 정상적으로 기록한 뒤 실패를 보고")이 무의미해진다 — AC-XRATE-007이 이 지점을 직접 판별한다.

**배치 쓰기 자체가 실패하는 경로에 대한 명시적 처리 범위(D17, v1.1.0 신설)**: REQ-XRATE-016은 "성공한 날짜를 정상적으로 기록한 뒤" `CommandError`를 발생시킬 것을 요구하는데, 만약 쓰기 단계 자체(`bulk_create` 호출)가 예외를 던지면(예: `IntegrityError`) 이 요구는 문자 그대로는 충족될 수 없다 — 그 시점까지 stderr에 이미 보고된 조회 실패들이 최종 요약 메시지 없이 그 예외가 그대로 전파된다. 이 SPEC은 이 경로를 다음과 같이 처리한다: DB는 일관 상태로 남는다(`atomic()`이 쓰기 단계를 원자적으로 되돌리므로 데이터 손상은 없다) — 다만 stderr 요약이 누락되는 것은 **보고 품질 저하**이지 데이터 무결성 문제가 아니므로, 이 SPEC은 이 경로를 우아하게 처리(예: `try/except`로 감싸 조회 실패까지 포함한 통합 오류 메시지 생성)하도록 요구하지 않는다 — 예외가 그대로 전파되어 프로세스가 처리되지 않은 트레이스백으로 종료되는 것을 **의도된 동작**으로 명시한다. 아래 설계 결정 G(`ignore_conflicts=True`)를 채택하면 이 경로의 가장 현실적인 원인(중복 키 충돌)이 애초에 예외를 일으키지 않게 되므로, 이 경로가 실제로 발동할 가능성은 크게 줄어든다(남는 원인은 DB 연결 끊김 등 진짜 인프라 장애뿐이며, 그런 경우 처리되지 않은 예외로 프로세스가 종료되는 것이 오히려 올바른 신호다).

**F. 실패를 단일 예외 타입으로 정규화.** 계약 함수(`fetch_usd_krw_rate`)는 네 가지 서로 다른 표준 예외(`urllib.error.URLError`, `urllib.error.HTTPError`, `json.JSONDecodeError`, `KRW` 키 부재 시의 `KeyError`)를 모두 `ExchangeRateFetchError` 하나로 정규화해 다시 던진다. 커맨드 쪽 코드는 이 예외 타입 하나만 처리하면 되므로, "실패해도 나머지 날짜는 계속 진행한다"(REQ-XRATE-011)는 요구를 `try/except ExchangeRateFetchError` 한 줄로 만족시킬 수 있다 — 호출부가 urllib/json 표준 예외 네 가지를 개별적으로 알아야 하는 대안보다 계약이 단순하고, REQ-XRATE-004의 "계약만 지키면 구현을 통째로 교체 가능"이라는 목표와도 정합한다(교체될 구현체가 무엇을 내부적으로 던지든 `ExchangeRateFetchError`로만 감싸면 커맨드는 무수정).

**G. 배치 쓰기는 `bulk_create(..., ignore_conflicts=True)`를 채택한다(v1.1.0 신설, 감사 D9 반영).** REQ-XRATE-012가 요구하는 read-then-insert(존재 확인 쿼리 → `bulk_create`)는 두 쿼리 사이에 원자성이 없다 — 같은 날짜 범위에 대해 두 실행이 겹치면(예: 외부 cron이 중복 실행되거나, 운영자가 예정된 정기 실행 시각 부근에 수동으로 `--start`/`--end` 재실행), 두 실행이 모두 같은 날짜를 "존재하지 않음"으로 관측하고 둘 다 삽입을 시도할 수 있다 — 나중에 커밋을 시도하는 쪽이 `unique=True`(`models.py:501`) 위반으로 처리되지 않은 `IntegrityError`를 내며 죽는다(REQ-XRATE-016이 약속하는 `CommandError`가 아니다). `bulk_create`에 `ignore_conflicts=True`를 추가하면(존재 확인 쿼리는 그대로 유지 — REQ-XRATE-012의 쿼리 수·AC-XRATE-005의 "정확히 2건" 단정·`plan.md`의 "M건 이미 존재해 건너뜀" 요약 로직은 전부 무영향) 이 경쟁을 DB 레벨에서 안전하게 흡수한다. 부수 효과로 REQ-XRATE-024(중복 echo 게시일 압축)가 애플리케이션 레벨에서 놓친 중복이 있더라도 DB 레벨에서 한 번 더 방어되고(D3의 이중 방어), 설계 결정 E가 다루는 "배치 쓰기 자체가 실패하는 경로"(D17)의 가장 흔한 발생 원인(중복 키 충돌)이 사라진다. 비용은 없다 — 이 SPEC은 애초에 `bulk_create`의 반환값(생성된 객체 목록)을 사용하지 않으므로 `ignore_conflicts=True`가 요구하는 "PK를 되돌려받지 않는다"는 제약이 문제되지 않는다.

---

## 제약사항

- 신규 HTTP 클라이언트 의존성을 추가하지 않는다 — stdlib `urllib.request`만 사용한다(REQ-XRATE-002).
- `ExchangeRate` 모델에 신규 필드나 마이그레이션을 추가하지 않는다.
- 이 SPEC이 채우는 데이터는 오직 `effective_date`/`rate` 두 필드이며, 데이터 소스나 조회 시각을 기록하는 감사(audit) 필드는 추가하지 않는다(범위 밖 — 필요해지면 별도 SPEC).
- `sync_exchange_rates`는 인증/권한 체크가 없다 — management command는 서버 운영자만 실행할 수 있는 실행 환경이 이미 그 경계를 제공하며, 이 SPEC이 API 엔드포인트를 만들지 않기로 한 결정(REQ-XRATE-023)과 일관된다.

## Exclusions (What NOT to Build)

- **`_get_exchange_rate` 폴백 로직을 변경하지 않는다.** `backend/order/serializers.py:176-187`은 이 SPEC에서 무수정이다(REQ-XRATE-018).
- **마진/비용 계산 공식을 변경하지 않는다.** SPEC-ORDER-008/009/021이 확립한 공식과 필드는 이 SPEC과 무관하다(REQ-XRATE-018).
- **기존 117개 레코드를 포함해 이미 저장된 어떤 레코드도 소급 수정하지 않는다.** Frankfurter 값과 기존 DB 값 사이의 0.03~0.11% 차이를 보정하는 배치 작업은 만들지 않는다 — 그 차이는 무시할 만큼 작고, 소급 수정은 "과거 시점에 실제로 계산에 쓰인 값"이라는 역사적 사실을 바꾸는 것이므로 별도의 명시적 의사결정 없이는 손대지 않는 것이 안전하다(REQ-XRATE-021).
- **한국수출입은행 매매기준율 연동을 구현하지 않는다.** REQ-XRATE-001/004가 정의하는 계약 함수 형태의 확장 지점만 남긴다 — placeholder 설정 키나 미사용 코드 경로를 만들지 않는다(REQ-XRATE-020).
- **인앱 스케줄러(Celery, APScheduler, django-q 등)를 도입하지 않는다.** 정기 실행 등록은 운영 계층(외부 cron, Windows Task Scheduler 등)의 책임이며, 이 SPEC은 실행할 정확한 커맨드(`python manage.py sync_exchange_rates`)만 제공한다(REQ-XRATE-022).
- **`POST /api/orders/sync/`(`OrderSyncView`)에 대응하는 신규 API 엔드포인트를 만들지 않는다.** `OrderSyncView`는 `frontend/src/features/order/hooks/useOrderSync.ts`를 통해 `OrdersPage.tsx`의 "동기화" 버튼(사용자가 즉시 신규 주문을 눈으로 확인하고 싶을 때 수동으로 누르는 버튼)에 연결되어 있다 — 이 SPEC이 다루는 환율 갱신에는 그런 사용자 워크플로 요구가 현재 존재하지 않으며(요구사항 어디에도 "환율 갱신 버튼"이 명시되지 않았다), 개별 값 수기 보정은 이미 기존 CRUD API(`PUT /api/exchange-rates/{date}/`)로 가능하다. 요청되지 않은 엔드포인트를 미리 만드는 것은 범위 확장이다(REQ-XRATE-023).
- **날짜 범위 조회(Frankfurter range 엔드포인트)로 전환하지 않는다.** 설계 결정 B가 이유를 설명한다 — 후속 과제로 남긴다.
- **재시도(retry) 로직을 만들지 않는다.** 실패한 날짜는 다음 실행(수동 재실행 또는 다음 정기 실행)에서 다시 시도되며, 이 SPEC은 같은 실행 내에서의 자동 재시도를 구현하지 않는다.

## 후속 과제

1. **Frankfurter range 엔드포인트로 전환.** 설계 결정 B가 보류한 최적화 — 백필 대상 기간이 크게 늘어나거나 순차 호출 수가 실제 병목으로 판명되면 검토. **범위(v1.1.0 추가, 감사 D6 반영)**: 이 전환은 후속 과제 4(실패한 특정 날짜가 자동으로 재시도되지 않는 문제)와 REQ-XRATE-024/AC-XRATE-012가 다루는 중복 echo 게시일 문제도 함께 해소한다 — range 엔드포인트의 응답은 이미 실제 발행일로 키가 매겨져 있어 이 SPEC이 단일-날짜 엔드포인트 때문에 떠안는 두 구조적 문제(주말 중복 echo, 특정 날짜 실패 시 영구 미추적)가 애초에 발생하지 않는다. 전환 시 REQ-XRATE-011/016의 날짜별 실패 격리 속성(설계 결정 B가 단일-날짜 엔드포인트를 유지하는 진짜 이유)은 청킹 없이는 재현되지 않으므로, 이 트레이드오프를 다시 평가해야 한다.
2. **한국수출입은행 매매기준율 연동.** REQ-XRATE-001/004의 확장 지점을 이용해 `fetch_usd_krw_rate`와 동일한 시그니처의 새 함수로 교체하는 별도 SPEC.
3. **실패 알림 강화.** 현재는 stderr 출력 + 0이 아닌 종료 코드만 제공한다 — 운영 계층 cron이 이 종료 코드를 감지해 알림(Slack, 이메일 등)을 보내는 것은 이 SPEC의 범위 밖이며, 필요해지면 별도 SPEC 또는 순수 운영 설정으로 처리한다.
4. **실패한 특정 날짜의 자동 재탐색.** 현재는 "최신 저장일 다음날부터 오늘까지"가 기본 범위이므로, 중간의 특정 날짜만 실패하고 그 이후 날짜들이 성공하면 그 특정 날짜는 다음 정기 실행에서도 자동으로 재시도되지 않는다(이미 그 이후 날짜가 "최신 저장일"이 되어 있으므로) — 운영자가 `--start`/`--end`로 수동 재실행해야 한다. 이 간극을 자동으로 메우는 기능(예: 범위 내 미저장 날짜 자동 탐지)은 이 SPEC의 범위 밖이다.
