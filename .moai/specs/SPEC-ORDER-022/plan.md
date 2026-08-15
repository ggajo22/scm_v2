---
id: SPEC-ORDER-022
document: plan
version: 1.1.1
status: implemented
updated: 2026-08-15
---

> **구현 완료 메모 (v1.1.1, 2026-08-15)**: M0~M7 완료. 상세 발산 내역은 `spec.md` HISTORY v1.1.1 항목 참조. 요약: (1) 선례 파일 `test_spec_016.py`/`test_spec_018.py`/`repair_refunds.py`가 이 worktree에 없어 `test_spec_015.py`(`CaptureQueriesContext`/`freeze_time` 사용 스타일)와 `backfill_location.py`+`process_purchase_orders.py`(커맨드 스타일)로 대체. (2) AC-XRATE-008의 `freeze_time(..., tz_offset=9)` 픽스처가 이 저장소의 freezegun 1.5.5에서 `date.today()`/`timezone.localdate()`를 구별하지 못함을 실측 확인 — T8을 `timezone.localdate()` 직접 mock 방식으로 재작성(REQ-XRATE-009 자체는 원안대로 구현). (3) `SYNC_QUERY_COUNT = 4`(실측). (4) M8(라이브 백필)은 범위 밖, 별도 승인 대기.

# 구현 계획 — SPEC-ORDER-022 ExchangeRate 테이블 자동 갱신 및 공백 구간 백필

`spec.md`의 요구사항(REQ-XRATE-001~024, v1.1.0 — REQ-XRATE-024는 plan-auditor 감사 D3 반영으로 신설)을 구현하기 위한 작업 분해, 파일별 변경 계획, TDD 사이클, 리스크와 완화책, MX 태그 계획을 정리한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며, 요구사항을 재진술하지 않고 REQ ID로 참조한다.

**개발 방법론**: TDD (RED-GREEN-REFACTOR). `.moai/config/sections/quality.yaml`의 `development_mode: "tdd"`(`:4`), `test_first_required: true`(`:43`), `min_coverage_per_commit: 80`(`:46`)에 따른다. `backend/order/exchange_rates.py`와 `sync_exchange_rates` 커맨드는 이 저장소에 전례가 없는 신규 모듈이므로 그린필드에 가깝지만, 커맨드가 소비하는 `ExchangeRate` 모델과 그 유니크 제약(`models.py:501`)은 기존 코드이므로 M0에서 먼저 확인한다.

**이 SPEC의 특이점**: 이 저장소 최초의 management command 테스트다 — 기존 3개 커맨드(`backfill_location.py`, `process_purchase_orders.py`, `repair_refunds.py`)에는 `call_command`를 쓰는 테스트가 하나도 없다(`backend` 전체를 `call_command`로 검색한 결과 0건). 따라서 이 SPEC에서 확립하는 `call_command` + `io.StringIO`(stdout/stderr 캡처) 패턴이 향후 커맨드 테스트의 참조 선례가 된다.

---

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M0 (High) — 베이스라인 확인**: `backend/order/models.py:495-509`(`ExchangeRate`), `backend/order/serializers.py:176-225`(`_get_exchange_rate`, `_compute_margin_usd` — 무수정 대상이지만 회귀 확인을 위해 재확인), `backend/order/shopify_orders.py:1-40`(`_get_with_headers`, `REQUEST_TIMEOUT` 관례), `backend/order/management/commands/repair_refunds.py`, `backfill_location.py`, `process_purchase_orders.py`(커맨드 스타일 3종 전체), `backend/order/tests/test_shopify_orders.py:1-10,267-273,590-609`(모킹 관례), `backend/order/tests/test_spec_008.py:101-114`(UTC 날짜 계산 함정), `backend/order/tests/test_spec_016.py:578-586`(freeze_time + 이 프로젝트 특유의 상호작용 주의사항), `backend/config/settings/base.py:92,94`(`TIME_ZONE`, `USE_TZ`)를 다시 읽는다. 기존 백엔드 테스트 스위트(`pytest backend/order/tests/`)의 현재 통과 상태를 기록한다.

- **M1 (High) — 계약 함수 테스트 선작성 (RED)**:
  - `backend/order/tests/test_exchange_rates.py`를 신규 작성한다 — `fetch_usd_krw_rate`의 단위 테스트. **정정(D8, v1.1.0)**: `test_shopify_orders.py:269`(`patch("order.shopify_orders._get_with_headers")`, `mock_get.return_value`)와 `:604`(`side_effect` 콜러블)는 `patch(...)`/`side_effect` **사용 스타일**의 선례로만 참고한다 — 그 테스트는 `urlopen`이 아니라 모듈 레벨 헬퍼 `_get_with_headers`를 모킹하며(`grep -rn urlopen backend/order/tests/` 결과 0건, 이 저장소에 `urlopen` 모킹 전례가 없다), `fetch_usd_krw_rate`는 그런 헬퍼가 없으므로 `urlopen` 자체를 모킹해야 한다 — 이는 "기존 관례를 따르는" 것이 아니라 이 SPEC이 **새로 수립하는** 모킹 지점이다. `urlopen`은 컨텍스트 매니저이고 `.read()`가 `bytes`를 반환하므로, mock은 `mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"date": "...", "rates": {"KRW": ...}}'` 형태여야 한다 — 딕셔너리를 직접 `return_value`로 설정하면 `json.loads(dict)`가 `TypeError`를 낸다.
    - 정상 응답(`date`가 요청일과 같은 경우 / 다른 경우) → `(published_date, rate)` 튜플 반환, `rate`가 `Decimal`.
    - `urllib.error.URLError`, `urllib.error.HTTPError`, 잘못된 JSON, `KRW` 키 없음 — 네 경우 모두 `ExchangeRateFetchError` 발생.
  - 이 단계에서 `backend/order/exchange_rates.py`가 아직 없으므로 임포트 자체가 실패해 RED가 자연히 성립한다.

- **M2 (High) — 계약 함수 구현 (GREEN)**:
  - `backend/order/exchange_rates.py` 신규 작성: `ExchangeRateFetchError(Exception)`, `fetch_usd_krw_rate(request_date: date) -> tuple[date, Decimal]`(REQ-XRATE-001~004). `shopify_orders.py:10-11`의 `REQUEST_TIMEOUT = 30` 상수와 동일한 타임아웃 값을 재사용(같은 값을 이 파일에 독립적으로 선언 — `shopify_orders.py`를 임포트해 상수를 가져오지 않는다, 두 파일의 관심사가 분리되어 있어야 하므로).
    - Frankfurter 응답 파싱: `body["date"]` → `date.fromisoformat(...)`, `body["rates"]["KRW"]` → `Decimal(str(...))`(`serializers.py:202`의 `Decimal(str(obj.total_price or "0"))` 패턴과 동일한 이유 — float를 `Decimal`에 직접 넘기지 않는다).
    - `urllib.error.URLError`(`HTTPError`는 `URLError`의 서브클래스이므로 먼저 잡을 필요 없이 함께 캐치되지만, 메시지에 상태 코드를 포함시키려면 `HTTPError`를 개별적으로 먼저 캐치), `json.JSONDecodeError`, `KeyError`(`KRW` 키 부재) 네 가지를 모두 `ExchangeRateFetchError`로 다시 던진다(설계 결정 F) — 각 예외 메시지에 요청한 날짜를 포함해 stderr 출력(M3)에서 어떤 날짜가 실패했는지 알 수 있게 한다.
  - M1의 모든 테스트가 통과함을 확인한다.

- **M3 (High) — 커맨드 테스트 선작성 (RED)**:
  - `backend/order/tests/test_spec_022.py`를 신규 작성한다 — AC-XRATE-001~012(12개, v1.1.0 — AC-XRATE-012는 감사 D3 반영 신설)에 1:1 대응. `patch("order.management.commands.sync_exchange_rates.fetch_usd_krw_rate")`(커맨드 모듈에 임포트된 이름을 모킹 — `test_shopify_orders.py`가 `order.shopify_orders._get_with_headers`를 모킹하는 것과 동일하게, 호출부의 네임스페이스를 모킹 대상으로 삼는다)로 네트워크를 완전히 배제한다. **[HARD, D16 신설]** 이 patch target이 유효하려면 커맨드 모듈이 반드시 `from order.exchange_rates import fetch_usd_krw_rate`(이름을 커맨드 모듈 네임스페이스로 직접 가져오는 형태) 형태로 임포트해야 한다 — `from order import exchange_rates`로 임포트하고 `exchange_rates.fetch_usd_krw_rate(...)`로 호출하면 이 patch가 조용히 아무 효과가 없어(no-op) 모든 T-테스트가 실제 네트워크 호출을 시도한다(실패하거나, 최악의 경우 우연히 통과해버린다). M4에서 이 임포트 형태를 명시적으로 지킨다.
  - `django.core.management.call_command`(신규 도입 — 저장소 최초, M0에서 확인한 대로 전례 없음)로 커맨드를 실행하고, `io.StringIO`를 `stdout`/`stderr` 인자로 넘겨 출력 캡처, `CommandError`는 `pytest.raises(CommandError)`로 단정한다.
  - AC-XRATE-005(쿼리 수)는 `django.test.utils.CaptureQueriesContext`(`test_spec_018.py:40`의 기존 임포트 재사용)로 감싼다 — 절대값은 이 시점에 실제로 실행해 관측한 값으로 채운다(추측값 금지, `test_spec_018.py:64` 관례). **[D7 정정]** 캡처 범위는 `call_command` 호출 **전체**(범위 계산부터 배치 쓰기까지)이며, "쓰기 단계만"이 아니다 — `orders_exchangerate` 참조 쿼리 수는(savepoint 노이즈와 무관하게) X/Y 양쪽에서 정확히 2건이어야 한다.
  - AC-XRATE-006(실패 4종)은 mock이 `ExchangeRateFetchError`를 **직접** 발생시키도록 설정한다(raw `urllib`/`json` 예외가 아니다 — `except ExchangeRateFetchError`만 잡는 커맨드 구현에서는 raw 예외가 핸들러를 빠져나간다, D2 정정) — `io.StringIO` stderr 캡처 내용에 실패한 날짜와 오류 메시지가 포함되는지도 단정한다(D5 신설).
  - AC-XRATE-008은 `freezegun.freeze_time("2026-06-21 23:30:00", tz_offset=9)`(**D1 정정** — 자정 근처 UTC 시각 + `tz_offset=9` 조합이 반드시 필요하다. `freeze_time("2026-06-21 12:00:00")`처럼 `tz_offset` 없이(0으로 암묵 고정) 또는 자정에서 먼 시각으로 테스트하면 `date.today()`와 `timezone.localdate()`가 이 프로젝트의 `TIME_ZONE="UTC"` 설정 하에서 항상 같은 값을 반환해 "`date.today()` 대신 `timezone.localdate()`를 쓴다"는 mutation을 절대 잡지 못한다 — freezegun 1.5.5로 직접 실행해 확인함, `test_spec_016.py:583` 선례는 사용 스타일만 참고)로 "오늘"을 고정한다.
  - AC-XRATE-012(중복 echo 압축, D3 신설)는 `2026-06-19`(금)~`2026-06-21`(일) 범위에서 세 요청 전부가 같은 게시일(`2026-06-19`)을 echo하도록 모킹해, `bulk_create`가 `IntegrityError` 없이 정확히 1건만 생성함을 확인한다.
  - 이 단계에서 `sync_exchange_rates.py`가 아직 없으므로 전부 실패해 RED가 성립한다.

- **M4 (High) — 커맨드 구현 (GREEN)**:
  - `backend/order/management/commands/sync_exchange_rates.py` 신규 작성.
  - `add_arguments`: `--start`(`type=str`, `default=None`), `--end`(`type=str`, `default=None`) — `backfill_location.py:11-22`, `process_purchase_orders.py:23-47`의 `add_arguments` 스타일을 따른다.
  - `handle`: 아래 "기술적 접근" 절의 단계를 그대로 구현한다.
  - M3의 모든 테스트가 통과함을 확인한다.

- **M5 (Medium) — REFACTOR**: `fetch_usd_krw_rate`와 `sync_exchange_rates.handle`의 가독성을 다듬는다. 조회 루프와 쓰기 단계가 명확히 분리되어 있는지(설계 결정 E), 실패 시 개별 예외가 `ExchangeRateFetchError` 하나로 정규화되어 있는지(설계 결정 F) 재확인한다.

- **M6 (Medium) — 회귀 확인**: 백엔드 테스트 스위트 전량 재실행(`pytest backend/order/tests/`). `git diff --stat backend/order/serializers.py backend/order/urls.py backend/order/views.py`가 비어 있는지 확인(REQ-XRATE-018, 023). `git diff --stat backend/pyproject.toml`에 신규 HTTP 라이브러리 의존성이 없는지 확인(REQ-XRATE-002). `ruff check backend/order/exchange_rates.py backend/order/management/commands/sync_exchange_rates.py`.

- **M7 (Low) — MX 태그 적용 + 문서 동기화**: 아래 MX 태그 계획을 적용하고, `spec.md`/`plan.md`/`acceptance.md`의 `status`를 갱신하며 구현 중 발견한 발산을 `spec.md` HISTORY에 기록한다.

- **M8 (Low, 운영) — 최초 백필 실행 및 정기 실행 등록**: `python manage.py sync_exchange_rates --start 2026-06-19 --end <구현 완료 시점의 오늘 날짜>`를 실제 환경에서 1회 실행해 공백 구간을 채운다. 정기 실행은 외부 cron 또는 Windows Task Scheduler에 `python manage.py sync_exchange_rates`(인자 없음, 기본 범위 사용)를 하루 1회 등록한다 — 정확한 스케줄 시각(예: ECB 게시 시각 이후)은 운영 배포 환경에 따라 결정하며, 이 SPEC은 등록할 커맨드 자체만 규정한다(REQ-XRATE-022). 이 마일스톤은 **라이브 환경 실행**이므로 이 SPEC 문서 작성/구현 단계와 분리해 별도로 승인받은 뒤 수행한다.

의존 관계: M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8.

---

## 파일별 변경 계획

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| NEW | `backend/order/exchange_rates.py` | `ExchangeRateFetchError`, `fetch_usd_krw_rate(request_date) -> (date, Decimal)`(REQ-XRATE-001~004). |
| NEW | `backend/order/management/commands/sync_exchange_rates.py` | `--start`/`--end` 인자, 범위 계산, 조회 루프, 배치 쓰기, 실패 처리(REQ-XRATE-005~017). |
| NEW | `backend/order/tests/test_exchange_rates.py` | `fetch_usd_krw_rate` 단위 테스트 — 정상/echoed-date/4종 실패. |
| NEW | `backend/order/tests/test_spec_022.py` | AC-XRATE-001~012(12개, v1.1.0) 대응 테스트. |
| EXISTING (무수정) | `backend/order/serializers.py`(`_get_exchange_rate`, `_compute_margin_usd`) | REQ-XRATE-018. AC-XRATE-011이 이 무수정 상태에서의 동작을 회귀 확인한다. |
| EXISTING (무수정) | `backend/order/models.py`(`ExchangeRate`), `backend/order/migrations/` | 신규 필드/마이그레이션 없음. |
| EXISTING (무수정) | `backend/order/urls.py`, `backend/order/views.py`(`ExchangeRateListCreateView`, `ExchangeRateDetailView`) | REQ-XRATE-023 — 신규 API 엔드포인트 없음. |
| EXISTING (무수정) | `backend/order/shopify_orders.py` | 범위 분리 — 이 SPEC의 로직을 이 파일에 추가하지 않는다. |
| EXISTING (무수정) | `backend/pyproject.toml` | REQ-XRATE-002 — 신규 HTTP 의존성 추가 없음. |

---

## 기술적 접근

### 계약 함수 (M2)

```
def fetch_usd_krw_rate(request_date: date) -> tuple[date, Decimal]:
    url = f"https://api.frankfurter.dev/v1/{request_date.isoformat()}?base=USD&symbols=KRW"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise ExchangeRateFetchError(f"{request_date}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ExchangeRateFetchError(f"{request_date}: network error ({exc.reason})") from exc
    except json.JSONDecodeError as exc:
        raise ExchangeRateFetchError(f"{request_date}: malformed JSON response") from exc

    try:
        published_date = date.fromisoformat(body["date"])
        rate = Decimal(str(body["rates"]["KRW"]))
    except KeyError as exc:
        raise ExchangeRateFetchError(f"{request_date}: response missing expected key {exc}") from exc

    return published_date, rate
```

이름과 세부 구현(예: 헬퍼 함수 분리 여부)은 구현자 재량이나, 시그니처(`date -> (date, Decimal)`)와 예외 계약(`ExchangeRateFetchError` 하나로 정규화)은 강제된다(REQ-XRATE-001, 004, 설계 결정 F).

### 커맨드 (M4)

**[HARD, D16 신설] 임포트 형태**: `sync_exchange_rates.py`는 반드시 `from order.exchange_rates import fetch_usd_krw_rate`로 임포트해 커맨드 모듈 네임스페이스에 직접 이름을 들여온다. `from order import exchange_rates`로 임포트하고 `exchange_rates.fetch_usd_krw_rate(...)`로 호출하는 형태는 쓰지 않는다 — M3이 쓰는 `patch("order.management.commands.sync_exchange_rates.fetch_usd_krw_rate")`는 전자의 임포트 형태에서만 유효하며, 후자에서는 조용히 아무 효과가 없어(no-op) 모든 T-테스트가 실제 네트워크를 탄다.

1. **인자 파싱**: `--start`, `--end`(둘 다 `YYYY-MM-DD` 문자열, `date.fromisoformat`으로 파싱).
2. **범위 계산**:
   - `end`: 주어지지 않으면 `timezone.localdate()`(REQ-XRATE-009, `test_spec_008.py:101-114` 함정 회피).
   - `start`: 주어지지 않으면 `ExchangeRate.objects.order_by("-effective_date").values_list("effective_date", flat=True).first()`를 조회 — `None`이면 `CommandError`(REQ-XRATE-008), 아니면 그 다음 날(`+ timedelta(days=1)`, REQ-XRATE-007).
   - `start > end`이면 아무 것도 하지 않고 `return`(REQ-XRATE-010) — 이 지점 이후로는 fetch 호출도, DB 쓰기도 없다.
3. **조회 루프**(REQ-XRATE-011): `start`부터 `end`까지(포함) 하루씩 순회하며 `fetch_usd_krw_rate(d)`를 호출. 성공하면 `(published_date, rate)`를 `fetched: list[tuple[date, Decimal]]`에 추가, 실패(`ExchangeRateFetchError`)하면 그 예외를 `d`와 함께 `failures: list[tuple[date, ExchangeRateFetchError]]`에 추가하고 `self.stderr.write(...)`로 즉시 출력(`repair_refunds.py:65`의 `self.stderr.write(self.style.ERROR(f"  {order.name}: {exc}"))` 패턴과 동일) — 이 루프는 **DB에 접근하지 않는다**(설계 결정 E, 트랜잭션 경계는 다음 단계부터). **권고(강제 아님, D6 반영)**: `repair_refunds.py:35-40`의 `--sleep`(기본 0.3초) 페이싱 패턴을 참고해, Frankfurter(공용 무료 API, 인증 불필요)에 짧은 지연을 두고 순차 호출하는 것을 구현자 재량으로 고려한다 — 이 SPEC은 이를 REQ로 강제하지 않는다(초기 백필은 57회 일회성 배치이고, 정기 동기화는 보통 1~3건뿐이라 페이싱 필요성이 낮다).
4. **배치 쓰기**(REQ-XRATE-012~014, 024, 설계 결정 D/E/G):
   ```
   published: dict[date, Decimal] = {}
   for d, r in fetched:
       published[d] = r  # REQ-XRATE-024: 같은 게시일로 echo된 여러 요청은 dict 키로 자연히 압축된다
   with transaction.atomic():
       existing = set(
           ExchangeRate.objects.filter(effective_date__in=published.keys())
           .values_list("effective_date", flat=True)
       )
       to_create = [
           ExchangeRate(effective_date=d, rate=r)
           for d, r in published.items()
           if d not in existing
       ]
       ExchangeRate.objects.bulk_create(to_create, ignore_conflicts=True)  # 설계 결정 G — 동시 실행 경쟁 방어, 존재 확인 쿼리는 그대로 유지
   ```
   `fetched`를 `list`가 아니라 `dict`(게시일을 키로)로 압축하는 것이 REQ-XRATE-024를 만족시키는 핵심이다 — 요청한 서로 다른 날짜가 같은 게시일로 echo되는 경우(예: 토·일 이틀을 각각 요청하면 둘 다 금요일 게시일로 echo됨) `dict` 키가 자동으로 중복을 제거한다. `bulk_create`에 `ignore_conflicts=True`를 추가하는 것은 이 애플리케이션 레벨 압축을 대체하는 것이 **아니라** 보강하는 것이다(설계 결정 G) — 동시 실행 경쟁까지는 애플리케이션 레벨 압축만으로 막을 수 없기 때문이다.
5. **실패 보고**(REQ-XRATE-015~017): `failures`가 비어 있지 않으면, 성공분 쓰기(4단계)가 끝난 뒤 `raise CommandError(f"{len(failures)} date(s) failed to fetch: {[d for d, _ in failures]}")`.
6. **stdout 요약**: `process_purchase_orders.py:180-182`(**D10 정정** — v1.0.0은 이를 `:114-118`로 잘못 인용했다; 그 범위는 실제로는 `rule_map` 조회 블록이다), `backfill_location.py:74-78`의 `self.stdout.write(self.style.SUCCESS(...))` 요약 라인 관례를 따라 "N건 신규 저장, M건 이미 존재해 건너뜀, K건 실패" 형태로 출력.

**하지 말 것**:
- 조회 루프(3단계) 안에서 `ExchangeRate.objects.filter(...)`나 `.save()`를 호출 — REQ-XRATE-012 위반(배치가 아닌 개별 쿼리), AC-XRATE-005가 판별.
- `bulk_create` 대신 날짜별 `get_or_create`/`update_or_create` 루프 — REQ-XRATE-012 위반, AC-XRATE-005가 판별.
- 이미 존재하는 `effective_date`를 `update_or_create`나 `.save()`로 갱신 — REQ-XRATE-013 위반, AC-XRATE-004가 판별.
- 조회 루프 전체(3단계)를 `transaction.atomic()`으로 감싸기 — 설계 결정 E 위반, AC-XRATE-007이 판별.
- 실패를 `except Exception: pass`류로 무시하고 계속, 또는 stderr에 아무것도 쓰지 않고 요약 메시지만으로 `CommandError`를 발생 — REQ-XRATE-016/017 위반, AC-XRATE-006이 판별.
- `datetime.date.today()`를 기본 종료일 계산에 사용 — REQ-XRATE-009 위반, AC-XRATE-008이 판별.
- `fetched`를 `dict`로 압축하지 않고 `list`로 그대로 `bulk_create`에 전달(주말 중복 echo 시 `IntegrityError`) — REQ-XRATE-024 위반, AC-XRATE-012가 판별.
- 커맨드 모듈이 `from order import exchange_rates`처럼 임포트해 M3의 patch target을 무효화 — D16, 모든 T-테스트가 실제 네트워크를 시도하게 된다.

### 테스트 (M1, M3)

- **U1**(`fetch_usd_krw_rate` 정상, 요청일=echo일): mock 응답 `{"date": "2026-08-13", "rates": {"KRW": 1420.29}}`, 요청 `date(2026, 8, 13)`. 반환값 `(date(2026, 8, 13), Decimal("1420.29"))` 단정.
- **U2**(echoed date가 다름): mock 응답 `{"date": "2026-06-18", ...}`, 요청 `date(2026, 6, 20)`(토요일). 반환된 첫 번째 요소가 `date(2026, 6, 18)`임을 단정(요청일이 아님).
- **U3~U6**(4종 실패): `urlopen`이 각각 `urllib.error.URLError`, `urllib.error.HTTPError`, 파싱 불가 바이트열, `{"date": "...", "rates": {}}`(KRW 없음)를 내도록 모킹. 네 경우 모두 `pytest.raises(ExchangeRateFetchError)` 단정.
- **T1**(AC-XRATE-001): `--start 2026-07-01 --end 2026-07-03`, `fetch_usd_krw_rate`가 3개 날짜에 각각 `(그 날짜, Decimal("1500.00")/Decimal("1501.00")/Decimal("1502.00"))`을 반환하도록 `side_effect` 모킹(`test_shopify_orders.py:597-608`의 `side_effect` 콜러블 패턴 — **D14 정정**: mock 반환값은 REQ-XRATE-001의 `Decimal` 계약과 일치시켜야 하며 문자열이 아니다). 3건 생성, 각 `rate`가 대응 날짜 값과 일치함을 개별 단정.
- **T2**(AC-XRATE-002): 요청 `date(2026, 6, 20)`이 echo `date(2026, 6, 18)`을 반환하도록 모킹, `--start 2026-06-20 --end 2026-06-20`. `ExchangeRate.objects.filter(effective_date=date(2026,6,20)).exists()`가 `False`, `effective_date=date(2026,6,18)`가 `True`.
- **T3**(AC-XRATE-003): 동일 범위·동일 mock으로 커맨드를 두 번 `call_command`. 두 번째 실행 후 `ExchangeRate.objects.count()`가 첫 번째 실행 직후와 동일, 예외 없음.
- **T4**(AC-XRATE-004): 사전에 `ExchangeRate.objects.create(effective_date=D, rate=Decimal("1500.00"))`, mock이 D에 대해 `(D, Decimal("1420.29"))` 반환. 커맨드 실행 후 `ExchangeRate.objects.get(effective_date=D).rate == Decimal("1500.00")`.
- **T5**(AC-XRATE-005): N=3, N=10 각각(신규 날짜, 기존과 겹치지 않음) 명시적 `--start`/`--end`로 실행하며 `call_command` 호출 **전체**를 `CaptureQueriesContext`로 감싼다(D7 정정 — "쓰기 단계만"이 아니다). (a) 총 쿼리 수가 두 실행에서 서로 같고 실측 고정값과 일치함을 단정. (b) `orders_exchangerate`를 참조하는 쿼리 수가 두 실행 모두 정확히 2건(존재 확인 1 + `bulk_create` 1)임을 단정.
- **T6**(AC-XRATE-006): 단일 날짜, `fetch_usd_krw_rate`가 **`ExchangeRateFetchError`를 직접** 발생시키도록 모킹(D2 정정 — raw `urllib.error.URLError` 등이 아니다, 그런 raw 예외는 `except ExchangeRateFetchError`만 잡는 커맨드 구현에서 핸들러를 빠져나가 정상 구현에서도 `CommandError`가 발생하지 않는다). `io.StringIO`로 stderr를 캡처해 `pytest.raises(CommandError)` + `ExchangeRate.objects.count()` 실행 전후 불변(D15 정정 — 단일 날짜 `exists()`가 아니라 전체 카운트로, 다른 날짜에 쓰인 sentinel row까지 잡는다) + stderr에 실패한 날짜 문자열과 mock에 전달한 오류 메시지가 모두 나타남(D5 신설)을 단정.
- **T7**(AC-XRATE-007): 3일 중 가운데 1일만 실패, 나머지 2일은 서로 다른 값. 성공한 2일 레코드 존재 + 정확한 값, `pytest.raises(CommandError)`.
- **T8**(AC-XRATE-008): `ExchangeRate(effective_date=date(2026,6,18), ...)` 사전 생성, `freeze_time("2026-06-21 23:30:00", tz_offset=9)`(**D1 정정** — 자정 근처 UTC 시각 + `tz_offset=9`가 필수. freezegun은 호스트 타임존을 읽지 않고 `frozen instant + tz_offset`으로 `date.today()`를 대체하므로, `tz_offset=0`(v1.0.0의 `freeze_time("2026-06-21 12:00:00")`)이나 정오처럼 자정에서 먼 시각으로는 `date.today()`와 `timezone.localdate()`가 항상 같은 값을 내 mutation을 못 잡는다 — freezegun 1.5.5 실측 확인), `--start`/`--end` 없이 `call_command`. `fetch_usd_krw_rate` mock의 `call_args_list`에서 호출된 날짜 집합이 정확히 `{date(2026,6,19), date(2026,6,20), date(2026,6,21)}`임을 단정(구현이 `date.today()`를 쓰면 이 픽스처에서 `2026-06-22`가 추가로 호출되어 실패한다).
- **T9**(AC-XRATE-009): `--start 2026-07-05 --end 2026-07-01`(역순). `fetch_usd_krw_rate` mock의 `call_count == 0`, `ExchangeRate.objects.count()`가 실행 전후 동일, 예외 없이 정상 반환.
- **T10**(AC-XRATE-010): `ExchangeRate.objects.all().delete()`로 빈 테이블 확보, `--start` 없이(`--end`는 임의 값) 실행. `pytest.raises(CommandError)`, `fetch_usd_krw_rate` mock의 `call_count == 0`.
- **T11**(AC-XRATE-011): mock이 `date(2026,8,13)`에 대해 `(date(2026,8,13), Decimal("1420.29"))` 반환, 이 날짜를 포함하는 범위로 커맨드 실행. 이어서 `Order(shopify_created_at=timezone.now().replace(...) → 2026-08-13, ...)` 생성 후 `OrderDetailSerializer()._get_exchange_rate(order)`(직접 메서드 호출, 뷰를 거치지 않아도 됨 — REQ-XRATE-018이 이 메서드를 무수정으로 요구하므로 단위 테스트로 충분) 결과의 `.effective_date == date(2026,8,13)`, `.rate == Decimal("1420.29")` 단정.
- **T12**(AC-XRATE-012, D3 신설): `--start 2026-06-19 --end 2026-06-21`(금·토·일). `fetch_usd_krw_rate`가 세 요청 전부에 대해 `(date(2026,6,19), Decimal("1530.00"))`를 반환하도록 모킹(주말 이틀이 금요일 게시일로 echo되는 실제 동작 재현). 예외 없이 정상 종료, `ExchangeRate.objects.filter(effective_date=date(2026,6,19)).count() == 1`, `ExchangeRate.objects.filter(effective_date__in=[date(2026,6,20), date(2026,6,21)]).exists() is False` 단정.

---

## 리스크 분석 및 완화책

| ID | 리스크 | 완화책 |
|---|---|---|
| R1 | 조회 루프 안에서 DB에 개별 접근해 날짜 수에 비례한 쿼리가 발생한다(N+1) | 설계 결정 E가 조회/쓰기 단계를 명확히 분리. T5(AC-XRATE-005)가 절대값 고정으로 판별. |
| R2 | 이미 존재하는 레코드를 갱신해 수기 보정을 되돌린다 | REQ-XRATE-013이 명시적으로 금지. T4(AC-XRATE-004)가 "다른 값" 시나리오로 직접 판별(T3의 "동일 값" 재실행 시나리오만으로는 이 결함이 드러나지 않음을 `spec.md`에 명시). |
| R3 | 조회+쓰기를 하나의 트랜잭션으로 묶어 부분 실패 시 성공분까지 롤백된다 | 설계 결정 E가 트랜잭션 범위를 쓰기 단계로만 한정. T7(AC-XRATE-007)이 판별. |
| R4 | `datetime.date.today()`를 써서 서버가 KST 등 UTC+ 지역에 있을 때 자정 근처 9시간 동안 종료일이 하루 밀린다 | `test_spec_008.py:101-114`의 기존 함정을 REQ-XRATE-009로 명시, `timezone.localdate()` 강제. T8이 `freeze_time("2026-06-21 23:30:00", tz_offset=9)`(D1 정정 — 자정 근처 UTC + `tz_offset` 조합이 필수, freezegun 1.5.5로 실측 확인)로 판별. |
| R5 | echoed date가 요청일과 달라 요청일 밑에 잘못 저장되거나, 서로 다른 요청일이 같은 게시일로 echo되어 `bulk_create`가 `IntegrityError`를 낸다(백필 범위 57일 중 주말 16일 전부에서 발생, D3) | REQ-XRATE-003이 echoed date 키잉을 강제, REQ-XRATE-024(D3 신설)가 중복 게시일 압축을 강제. T2(AC-XRATE-002)가 저장 위치를 판별, T12(AC-XRATE-012, D3 신설)가 주말 포함 범위로 압축 자체를 직접 판별. 기술적 접근 4단계가 `fetched`를 `dict`로 압축하고 `bulk_create(..., ignore_conflicts=True)`(설계 결정 G)로 이중 방어한다. |
| R6 | 저장소 최초의 management command 테스트라 `call_command`/`CommandError` 단정 관례가 없어 시행착오가 생긴다 | M3에서 Django 공식 `call_command` 테스트 패턴(공식 문서 관례 — 이 저장소에 전례가 없으므로 Django 자체 문서를 참조)을 새로 확립하고, 이후 커맨드 테스트의 선례로 `plan.md`에 남긴다. `urlopen` 모킹(U1~U6)도 이 저장소에 전례가 없는 별도의 신규 관례다(D8). |
| R7 | `sync_exchange_rates`가 `shopify_orders.py`의 기존 상수(`REQUEST_TIMEOUT`)나 함수(`_get_with_headers`)를 재사용하려다 두 모듈 사이에 불필요한 결합이 생긴다 | `exchange_rates.py`는 `shopify_orders.py`를 임포트하지 않는다(범위 분리, `spec.md` 범위 델타 표) — 타임아웃 상수는 같은 값을 독립적으로 재선언. |
| R8 | 신규 API 엔드포인트를 "혹시 필요할까 봐" 추가로 만들어버린다 | REQ-XRATE-023, Exclusions가 명시적으로 금지. M6에서 `git diff --stat backend/order/urls.py`가 비어 있는지 확인. |
| R9 (D9 신설) | read-then-insert(존재 확인 → `bulk_create`)는 원자적이지 않아, 두 실행이 겹치면(cron 중복 실행, 운영자 수동 재실행 등) 둘 다 "미존재"를 관측해 삽입을 시도하고 나중 실행이 `unique=True` 위반 `IntegrityError`로 처리되지 않은 채 죽는다 | 설계 결정 G — `bulk_create(..., ignore_conflicts=True)` 채택(존재 확인 쿼리·쿼리 수·"건너뜀" 요약 로직은 무영향). |

---

## MX 태그 계획 (mx_plan)

| 태그 | 위치 | 내용 |
|---|---|---|
| `@MX:NOTE` (신규) | `fetch_usd_krw_rate` 정의부(`exchange_rates.py`) | echoed-date 키잉이 왜 필요한지(REQ-XRATE-003), 이 함수가 유일한 외부 데이터 소스 접점이며 교체 시 이 함수만 다시 쓰면 된다는 확장 계약(REQ-XRATE-004, 설계 결정 A). |
| `@MX:ANCHOR` (신규) | `fetch_usd_krw_rate`(`exchange_rates.py`) | fan_in 사유: `sync_exchange_rates` 커맨드가 유일한 호출자이지만, REQ-XRATE-004의 확장 계약(향후 Eximbank 구현체가 같은 시그니처로 교체될 수 있음)을 근거로 invariant 계약(시그니처, 예외 타입)을 명시하는 ANCHOR로 태깅 — 단순 fan_in 카운트가 아니라 "교체 가능한 계약의 경계"라는 사유. |
| `@MX:NOTE` (신규) | 배치 쓰기 지점(`sync_exchange_rates.py`의 `transaction.atomic()` 블록) | 이 트랜잭션이 왜 조회 루프를 포함하지 않는지(설계 결정 E), 원격 RDS 배포와의 연관(SPEC-ORDER-021 설계 결정 F 참조). |
| `@MX:NOTE` (신규) | 갱신하지 않는 정책 지점(`existing` 필터링 부분) | REQ-XRATE-013이 왜 존재하는지(수기 보정 보호) — 설계 결정 D 요약. |

`code_comments: en` 설정(`.moai/config/sections/language.yaml`)에 따라 모든 태그 본문은 영어로 작성한다.

---

## 완료 조건 (Definition of Ready → Done 게이트)

**Ready (구현 시작 전)**

- [ ] M0 확인 — `models.py:495-509`, `serializers.py:176-225`, `shopify_orders.py:1-40`, 기존 커맨드 3종, `test_shopify_orders.py`의 모킹 관례, `test_spec_008.py:101-114`, `test_spec_016.py:578-586`, `settings/base.py:92,94`를 재확인했다
- [ ] 기존 백엔드 테스트 스위트의 현재 통과 상태를 기록했다
- [ ] `call_command` 테스트에 이 저장소에 전례가 없음을 확인했다(R6)

**Done (구현)**

- [ ] `test_exchange_rates.py` U1~U6 전량 통과, `exchange_rates.py` 부재 상태에서 전량 실패했음을 확인했다
- [ ] `test_spec_022.py` T1~T12(AC-XRATE-001~012, v1.1.0) 전량 통과
- [ ] T1이 "날짜-값 매핑 뒤섞임" mutation에서 실패함을 확인했다
- [ ] T2가 "요청일 그대로 저장" mutation에서 실패함을 확인했다
- [ ] T3와 T4를 **둘 다** 확인했다 — T4가 "값이 다른 경우의 덮어쓰기 금지"를 T3(동일 값 재실행)와 독립적으로 판별함을 재확인했다(`spec.md` AC-XRATE-004의 "이 AC가 필요한 이유" 참조)
- [ ] T5의 절대값(쿼리 수)을 실측해 고정했다(추측값 아님), N=3/N=10 양쪽에서 (a) 총 쿼리 수 동일 (b) `orders_exchangerate` 참조 쿼리 정확히 2건을 확인했다(D7) — pytest-django의 savepoint 노이즈로 (a)가 "2"가 아닐 수 있음을 인지했다
- [ ] T6의 mock이 raw `urllib`/`json` 예외가 아니라 `ExchangeRateFetchError`를 직접 발생시키도록 작성됐음을 재확인했다(D2 — v1.0.0의 raw-예외 버전은 정상 구현에서도 실패했다), `CommandError` + DB 전체 카운트 불변(D15) + stderr에 날짜·메시지 포함(D5)을 단정함을 확인했다
- [ ] T7이 "조회+쓰기 단일 트랜잭션" mutation(성공분까지 롤백)에서 실패함을 확인했다
- [ ] T8이 `freeze_time("2026-06-21 23:30:00", tz_offset=9)`로 결정적으로 재현됨을 확인했고(D1 — `tz_offset` 없이는 이 mutation이 절대 잡히지 않는다), "오늘 계산에 `date.today()` 사용" mutation에서 실패함을 확인했다
- [ ] T9, T10이 각각 "빈 범위에서도 fetch 호출" / "빈 테이블에서 처리되지 않은 예외" mutation에서 실패함을 확인했다
- [ ] T11 통과 — `_get_exchange_rate`가 실제로 무수정임을 `git diff`로 재확인했다
- [ ] T12(D3 신설)가 통과하고, `fetched`를 `dict`로 압축하지 않는 mutation에서 `IntegrityError`로 실패함을 확인했다
- [ ] 커맨드 모듈이 `from order.exchange_rates import fetch_usd_krw_rate` 형태로 임포트했음을 코드 리뷰로 확인했다(D16 — 다른 형태는 M3의 patch target을 무효화한다)
- [ ] `bulk_create` 호출에 `ignore_conflicts=True`가 있음을 확인했다(설계 결정 G, D9)
- [ ] `git diff --stat backend/order/serializers.py backend/order/urls.py backend/order/views.py`가 비어 있다(REQ-XRATE-018, 023)
- [ ] `git diff --stat backend/pyproject.toml`에 신규 HTTP 의존성이 없다(REQ-XRATE-002)
- [ ] `ruff check`(백엔드) 신규 이슈 0
- [ ] 기존 백엔드 테스트 스위트 전량 무수정 통과(회귀 없음)

**Done (문서)**

- [ ] `spec.md`/`plan.md`/`acceptance.md`의 `status`가 갱신되었다
- [ ] 구현 중 발견한 계획 대비 발산이 `spec.md` HISTORY에 기록되었다

**Done (운영, M8 — 별도 승인 후)**

- [ ] 라이브 환경에서 `sync_exchange_rates --start 2026-06-19 --end <오늘>`을 1회 실행해 공백을 백필했다 — 이 범위는 주말 8쌍(REQ-XRATE-024가 다루는 중복 echo 케이스)을 포함하므로, T12/설계 결정 G가 구현되지 않은 상태로 이 실행을 하면 `IntegrityError`로 실패한다는 점을 명심한다
- [ ] 정기 실행이 외부 cron 또는 Windows Task Scheduler에 등록되었다

**REQ → 검증 수단 매핑**

| REQ | 검증 |
|---|---|
| 001 | 코드 리뷰 (계약 함수 시그니처) |
| 002 | 코드 리뷰, `git diff pyproject.toml` |
| 003 | T2(AC-XRATE-002), T11(AC-XRATE-011) |
| 004 | 코드 리뷰 (재시도/캐시/provider 설정 없음) |
| 005 | T1(AC-XRATE-001), `git diff` (커맨드 파일 1개) |
| 006 | T1(AC-XRATE-001)(**D18 정정** — v1.0.0은 T8도 나열했으나 T8은 REQ-007/009를 검증하는 것이지 "인자를 받는다"는 REQ-006 자체를 검증하지 않는다) |
| 007 | T8 |
| 008 | T10 |
| 009 | T8 |
| 010 | T9 |
| 011 | T1, T7 |
| 012 | T1, T3, T5, T11 |
| 013 | T4 |
| 014 | T7 |
| 015 | T6 |
| 016 | T6, T7 |
| 017 | T6 |
| 018 | T11, `git diff serializers.py` |
| 019 | 코드 리뷰 (날짜 필터링 코드 없음) |
| 020 | `git diff` (Eximbank 관련 코드 없음) |
| 021 | 코드 리뷰 (REQ-013과 동일 지점) |
| 022 | `git diff` (celery/APScheduler/django-q 미추가) |
| 023 | `git diff urls.py` |
| 024 | T12(AC-XRATE-012, v1.1.0 신설) |

---

## 관련 참조 구현

- **`ExchangeRate` 모델**: `backend/order/models.py:495-509`
- **기존 폴백 조회(무수정 대상)**: `backend/order/serializers.py:176-187`(`_get_exchange_rate`), `:189-204`(`_compute_margin_usd`가 이를 소비하는 방식)
- **기존 CRUD API(무수정, 참고용)**: `backend/order/views.py:233-248`(`ExchangeRateListCreateView`, `ExchangeRateDetailView`), `backend/order/urls.py:182-183`, `backend/order/serializers.py:228-232`(`ExchangeRateSerializer`)
- **HTTP 클라이언트 관례**: `backend/order/shopify_orders.py:1-20`(`_get_with_headers`, `REQUEST_TIMEOUT = 30`)
- **외부 API 모킹 관례(사용 스타일만 참고 — D8: `urlopen` 자체를 모킹하는 전례는 없다)**: `backend/order/tests/test_shopify_orders.py:2`(`from unittest.mock import patch`), `:267-273`(`patch(...).return_value`), `:590-608`(`patch(..., side_effect=콜러블)`)
- **management command 스타일 선례(3종, 테스트 없음)**: `backend/order/management/commands/backfill_location.py`, `process_purchase_orders.py`(`CommandError` 사용 예: `:100`, `:178`; stdout 요약 `:180-182`), `repair_refunds.py`(항목별 순차 외부 호출 + `--sleep` 페이싱: `:60-111`)
- **쿼리 카운트 관례 선례**: `backend/order/tests/test_spec_018.py:40`(`CaptureQueriesContext` 임포트), `:64`(절대값 고정 관례), `:483-551`(캡처·비교·SQL 텍스트 매칭 패턴)
- **UTC 날짜 계산 함정**: `backend/order/tests/test_spec_008.py:101-114`, `backend/config/settings/base.py:92,94`(`TIME_ZONE`, `USE_TZ`)
- **freeze_time 선례**: `backend/pyproject.toml:24`(freezegun dev dependency), `backend/order/tests/test_spec_016.py:583`(`with freeze_time("2026-08-12 09:00:00")`)
- **`db_table` 전체 목록(부분 문자열 충돌 확인 근거)**: `backend/order/models.py:27,93,130,149,241,297,310,326,364,389,414,431,464,487,507,528,547` — `orders_exchangerate`(`:507`)는 이 중 어느 것과도 부분 문자열 관계가 아니다.
- **`OrderSyncView` 사용처(REQ-XRATE-023 근거)**: `backend/order/urls.py:60`, `backend/order/views.py:48-81`, `frontend/src/features/order/hooks/useOrderSync.ts`, `frontend/src/pages/OrdersPage.tsx:89`(`동기화` 버튼)
- **Frankfurter API 응답 형태(이 세션에 WebFetch로 검증)**: 단일 날짜 `GET /v1/{date}?base=USD&symbols=KRW` → `{"amount":1.0,"base":"USD","date":"...","rates":{"KRW":...}}`; 범위 `GET /v1/{start}..{end}?base=USD&symbols=KRW` → `{"amount":1.0,"base":"USD","start_date":"...","end_date":"...","rates":{"YYYY-MM-DD":{"KRW":...}, ...}}`(미게시일은 키 없음) — 설계 결정 B의 근거.
