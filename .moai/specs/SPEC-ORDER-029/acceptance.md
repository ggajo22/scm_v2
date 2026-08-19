# SPEC-ORDER-029 — 인수 기준 (Acceptance Criteria, v0.5.0)

대상 파일: `backend/order/tests/test_spec_029.py` `[NEW]`(공유 코어 함수, AC-CANC-001~012 + AC-CANC-024) + `backend/order/tests/test_sync_order_cancellations_command.py` `[NEW]`(감지 커맨드, AC-CANC-013~018 + AC-CANC-025) + `backend/order/tests/test_backfill_order_cancellations_command.py` `[NEW]`(백필 커맨드, AC-CANC-019~023)

> **v0.3.0**: plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-029-review-2.md`, **FAIL, 0.71**)가 blocking 5건을 지적했다 — (D1) 후보 집합의 생애주기 사각지대(종료 후 취소 영구 미감지), (D2) AC-CANC-005의 판별력이 청크 레벨 예외 삼킴으로 무력화됨, (D3) 파일 소속 배정이 4곳에서 서로 모순됨에도 "불일치 0건"이라 잘못 선언함, (D4) 가정 A1의 출처 오귀속, (D5) `fields=`/`limit=` 미커버(이전 회차 잔여). 이번 개정은 REQ/AC 체계를 확장 재작성했다 — 신규: 후보 집합 창(`closed_grace_days`) 검증, `missing_ids` 보고, 감지/백필 각각의 파라미터 전달 검증, `Refund`/`ShippingLine` 보존, `chunk_failures`의 실패 id 목록.
>
> **v0.4.0**: plan-auditor 3차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-029-review-3.md`, **FAIL, 0.80**, 4회차 감사 불필요 판정)가 blocking 4건을 지적했다 — 그중 둘이 이 문서에 있다: (D-N1) `IDS_CHUNK_SIZE=250` 기본값을 검출하는 AC 0개(기존 AC들이 전부 `chunk_size`를 명시적으로 넘겨 호출), (D-N2) 청크 레벨 실패가 커맨드 종료 코드에 반영되는지 검출하는 AC 0개(스토어 레벨 실패만 커버돼 있었다 — `failed.append(f"{store_type} (partial)")` 한 줄이 빠져도 23개 AC 전부가 통과했다). AC-CANC-007과 AC-CANC-017을 확장해 닫았다(AC 개수는 23개로 불변). 부수적으로 (D-N7) 패치 대상 규약의 분류 개수·구성원을 `plan.md` §1.6과 동기화하고("셋"→"넷"), (D-N8) AC-CANC-005의 실행 불가능한 형제 주문 id 표기를 정정했다.
>
> **v0.5.0**: 코디네이터 지시(신규 plan-auditor 감사 없이 적용) — 사용자가 제기한 동시성 문제(감지 커맨드와 기존 `sync_orders`의 겹침, `spec.md` §1.2 신설)를 다룬다. 신규 AC 2건을 추가한다: **AC-CANC-024**(공유 코어 — MySQL 잠금 대기 시간 초과 예외가 `chunk_failures`에 `lock_timeout=True`로, 다른 예외는 `False`로 구분 기록되는지 검증)와 **AC-CANC-025**(감지 커맨드 — 스토어의 모든 실패가 잠금 대기 시간 초과면 `CommandError`를 발생시키지 않되 기록은 유지되고, 하나라도 아니면 여전히 `CommandError`가 발생하는지 대조 시나리오로 검증). 두 AC 모두 기존 23개 AC의 번호·내용·판별력을 전혀 건드리지 않는 순수 추가다. AC 개수 23개 → **25개**.

## 0. 이 문서를 읽는 방법 — 판별력(mutation discrimination) 규약

[HARD] 통과하는 테스트가 곧 검증된 구현은 아니다. 이 SPEC의 모든 AC는 자신이 잡는 변이(mutation)를 명시하고, 그 변이를 픽스처에 직접 대입했을 때 결과값이 실제로 달라지는지 확인한 결과를 "판별력" 절에 적는다.

**[HARD] 기본값 함정 회피 규약** — `Order.cancelled_at`/`closed_at`은 둘 다 모델 기본값이 `NULL`이다. "필드가 그대로 `NULL`이다"라는 단정만 단독으로 쓰면, 코드가 아무것도 하지 않는 변이(no-op)에서도 트리비얼하게 통과한다. 이 문서는 그런 단정을 항상 다른 필드가 실제로 값을 얻었다는 양성 증거와 짝지어 배치한다.

**[HARD, v0.3.0 일반화 — 감사 D2 대응] 역방향 규약 — "무변경"·"예외 없음"·"빈 리스트" 등 모든 부정형 단정은 단독으로 쓰지 않는다.** v0.2.0은 이 규약을 "AC-CANC-011/017/019"(당시 번호)로 번호를 열거해 한정했는데, 그 열거 방식 자체가 신설되는 AC(당시 AC-CANC-005)를 규약 밖에 방치하는 구멍이었다(2차 감사 D2 — `existing[r["id"]]` 변이가 던지는 `KeyError`가 청크 레벨 `except Exception`에 삼켜져 "예외 없음"·"빈 리스트"·"미존재" 세 단정이 전부 트리비얼하게 통과했다). **v0.3.0부터 이 규약은 AC 번호가 아니라 "이 문서에 있는 모든 부정형 단정"에 무조건 적용된다** — 새 AC를 추가할 때도 예외 없이 적용해야 한다. 구체적으로: 어떤 AC의 Then이 "예외가 발생하지 않는다", "OO가 그대로다/비어 있다/포함되지 않는다" 같은 부정형만으로 구성돼 있다면, 그 AC는 이 규약을 위반한 것이다 — 반드시 "그리고 XX가 실제로 YY됐다"는 양성 증거 한 줄을 추가해야 한다.

**[HARD] 커서 전진을 성공의 증거로 쓰지 않는다** — 이 SPEC은 커서를 유지하지 않는다. "후보 집합에서 자동 제외됐다"는 별도의 관측 가능한 사실이며, `Order.cancelled_at`이 실제로 값을 얻었다는 선행 조건과 짝지어서만 검증한다(AC-CANC-010).

### 0.1 이 SPEC이 반드시 잡아야 하는 25개 변이

| ID | 범위 | 변이 | 판별 AC |
|----|------|------|---------|
| M1 | 공유 코어 | 후보 집합에 있는 신규 취소 주문의 `cancelled_at`이 기록되지 않는다 | **AC-CANC-001 (단독)** |
| M2 | 공유 코어 | 후보 집합에 있는 신규 종료 주문의 `closed_at`이 기록되지 않는다 | **AC-CANC-002 (단독)** |
| M3 | 공유 코어 | 종료-only 레코드의 `closed_at` 값이 로컬 `cancelled_at`에 잘못 기록된다 | **AC-CANC-003 (단독)** |
| M4 | 공유 코어 | 취소-only 레코드의 `cancelled_at` 값이 로컬 `closed_at`에 잘못 기록된다 | **AC-CANC-004 (단독)** |
| M5 | 공유 코어 | 로컬에 매칭되지 않는 레코드를 딕셔너리 직접 인덱싱(`existing[id]`)으로 처리해 `KeyError`가 발생한다 — 청크 레벨 예외 삼킴에 위장되지 않아야 한다 | **AC-CANC-005 (단독)** |
| M6 | 공유 코어 | 요청 URL의 `status=`/`ids=`/`fields=`/`limit=` 중 하나 이상이 틀리거나 누락된다 | **AC-CANC-006 (단독)** |
| M7 | 공유 코어 | 청킹 헬퍼가 250개 상한을 지키지 않거나 요소를 누락/중복시킨다. **[v0.4.0 확장, 3차 감사 D-N1]** `IDS_CHUNK_SIZE`/`chunk_size` 기본값이 250이 아닌 다른 값으로 바뀌는 것도 포함한다 | **AC-CANC-007 (단독)** |
| M8 | 공유 코어 | 후보 집합이 청크 크기를 초과할 때, 첫 청크만 처리되고 나머지가 조용히 누락된다 | **AC-CANC-008 (단독)** |
| M9 | 공유 코어 | 예상 밖 `Link` 헤더가 응답에 있어도 무시하고 첫 페이지만 처리한다 | **AC-CANC-009 (단독)** |
| M10 | 공유 코어 | 반영된 주문이 다음 후보 집합 조회에서도 계속 남아 있거나, 스토어 경계를 넘어 후보가 섞인다 | **AC-CANC-010 (단독)** |
| M11 | 공유 코어 | `closed_grace_days` 창 로직이 틀려 최근 종료 주문이 빠지거나 오래된 종료 주문이 계속 남는다 | **AC-CANC-011 (단독)** |
| M12 | 공유 코어 | Shopify가 반환하지 않은 요청 id가 `missing_ids`에 기록되지 않는다 | **AC-CANC-012 (단독)** |
| M13 | 감지 커맨드 | `StoreSyncWatermark`가 이 SPEC의 코드에 의해 잘못 기록된다 | **AC-CANC-013 (단독)** |
| M14 | 감지 커맨드 | 감지 커맨드가 `closed_grace_days=30`이 아닌 값(특히 무제한)을 전달한다 | **AC-CANC-014 (단독)** |
| M15 | 감지 커맨드 | 한 스토어의 실패가 다른 스토어의 처리를 막는다 | **AC-CANC-015 (단독)** |
| M16 | 감지 커맨드 | 한 청크의 실패가 같은 스토어의 나머지 청크 처리를 막거나, 실패 id가 기록되지 않는다 | **AC-CANC-016 (단독)** |
| M17 | 감지 커맨드 | **스토어 또는 청크** 레벨 실패가 있어도 종료 코드가 0이다(v0.4.0 확장, 3차 감사 D-N2 — v0.3.0까지는 스토어 레벨만 커버돼 청크 레벨 실패가 종료 코드에 반영되지 않는 변이가 전체 AC 세트를 통과했다) | **AC-CANC-017 (단독, 2개 시나리오)** |
| M18 | 감지 커맨드 | 매뉴얼 필드/`LineItem`/`ShippingLine`/`Refund`가 감지 잡에 의해 변경된다 | **AC-CANC-018 (단독)** |
| M19 | 백필 커맨드 | 백필 커맨드가 `closed_grace_days=None`이 아닌 값(창이 걸린 값)을 전달한다 | **AC-CANC-019 (단독)** |
| M20 | 백필 커맨드 | 기존에 미반영된 취소 주문(52건 유형)이 백필로도 반영되지 않는다 | **AC-CANC-020 (단독)** |
| M21 | 백필 커맨드 | `--dry-run`인데도 실제로 DB에 쓴다 | **AC-CANC-021 (단독)** |
| M22 | 백필 커맨드 | 매뉴얼 필드/`LineItem`/`ShippingLine`/`Refund`가 백필에 의해 변경된다 | **AC-CANC-022 (단독)** |
| M23 | 백필 커맨드 | 재실행이 중복 `Order` 행을 만들거나 첫 실행 자체가 반영에 실패한다 | **AC-CANC-023 (단독)** |
| M24 | 공유 코어, v0.5.0 | 청크 실패 예외가 MySQL 잠금 대기 시간 초과인지 여부와 무관하게 `chunk_failures`의 `lock_timeout`이 항상 같은 값(또는 키 자체가 없음)으로 기록된다 | **AC-CANC-024 (단독)** |
| M25 | 감지 커맨드, v0.5.0 | 스토어의 실패 종류(전부 잠금 대기 시간 초과 vs 하나라도 아님)와 무관하게 `CommandError` 발생 여부가 고정된다(항상 발생 또는 항상 미발생) | **AC-CANC-025 (단독, 2개 시나리오)** |

모든 변이가 정확히 1개의 AC로 잡히는 단독 판별자 구조다.

### 0.2 픽스처 규약 (v0.3.0 개정 — 감사 D8 대응 / v0.4.0 넷으로 동기화 — 감사 D-N7 대응)

패치 대상은 AC의 성격에 따라 **넷**으로 나뉜다(`plan.md` §1.6과 동일 규약, 여기서는 적용 대상만 나열한다) — **이 분류를 문자 그대로 따르지 않으면 쓰기 결과를 단정하는 AC들이 작성 자체가 불가능하다**(2차 감사 D8: `reconcile_order_status_for_ids`/`open_candidate_order_ids`를 패치하면 실제 쓰기가 일어나지 않는다). **[v0.4.0 정정, 3차 감사 D-N7]** v0.3.0은 이 문장이 "셋"이라 쓰면서 실제로는 4개를 나열했고, `plan.md` §1.6은 "3가지"라 쓰며 구성원도 서로 달랐다(그룹 4가 통째로 누락돼 있었다) — D8을 고치기 위해 신설한 바로 이 절에서 배정 드리프트가 재발했던 것이며, 이번 개정에서 두 문서의 그룹 번호·구성원을 동일하게 맞췄다:

1. **쓰기 결과를 단정하는 AC**(AC-CANC-013/018/020/021/022/023, 그리고 AC-CANC-015·017의 **정상 처리되는 쪽**) — `order.shopify_orders._get_with_headers`(HTTP 계층)만 패치한다.
2. **스토어 레벨에서 실패를 주입해야 하는 AC**(AC-CANC-015, AC-CANC-017 시나리오 1) — `order.management.commands.sync_order_cancellations.open_candidate_order_ids`에 스토어별 `side_effect`를 걸되, 정상 스토어 쪽은 1번 규약(HTTP 계층 패치)을 함께 적용해 실제 쓰기 경로를 살려둔다.
3. **청크 루프 자체를 검증하는 AC**(AC-CANC-005/008/012/016, AC-CANC-017 시나리오 2) — `order.shopify_orders.fetch_order_status_by_ids`를 패치한다.
4. **호출 인자만 캡처하면 되는 AC**(AC-CANC-014/019) — `open_candidate_order_ids`를 직접 패치해도 무방하다(쓰기 결과를 단정하지 않으므로).

Shopify 응답 모킹은 `id,cancelled_at,closed_at` 제한 스키마만 담는다. 로컬 `Order`/`LineItem` 픽스처는 매뉴얼 필드 보존을 검증하는 AC(018/022)에서 모델 기본값이 아닌 값을 명시적으로 설정한다. 날짜/시각 값은 `django.utils.timezone`을 통해 timezone-aware로 생성한다.

---

## 공유 코어 함수 AC (`test_spec_029.py`)

## AC-CANC-001 — [핵심] 신규 취소 주문의 cancelled_at 반영 `[CORE]`

Traces: REQ-CANC-001, REQ-CANC-004
잡는 변이: **M1 (단독)**

**Given** 로컬 `Order`(store_type="gimssine", shopify_order_id=90001, cancelled_at=None, closed_at=None). `_get_with_headers` 모킹 응답: `({"orders": [{"id": 90001, "cancelled_at": "2026-08-10T03:00:00Z", "closed_at": None}]}, {})`

**When** `reconcile_order_status_for_ids("gimssine", domain, token, [90001])` 호출

**Then** `Order.objects.get(shopify_order_id=90001).cancelled_at`이 `2026-08-10T03:00:00Z`와 같다.

**판별력**: `cancelled_at`을 기록하지 않는 변이(M1)는 값이 `None`으로 남아 즉시 실패한다.

---

## AC-CANC-002 — [핵심] 신규 종료 주문의 closed_at 반영 `[CORE]`

Traces: REQ-CANC-001, REQ-CANC-004
잡는 변이: **M2 (단독)**

**Given** 로컬 `Order`(shopify_order_id=90002, cancelled_at=None, closed_at=None). 모킹 응답: `{"id": 90002, "cancelled_at": None, "closed_at": "2026-08-09T12:00:00Z"}`

**When** `reconcile_order_status_for_ids("gimssine", domain, token, [90002])` 호출

**Then** `closed_at`이 `2026-08-09T12:00:00Z`와 같다.

**판별력**: `closed_at`을 기록하지 않는 변이(M2)는 값이 `None`으로 남아 잡힌다.

---

## AC-CANC-003 — [핵심, 필드 매핑] 종료-only 레코드: closed_at만 반영, cancelled_at은 그대로 NULL `[CORE]`

Traces: REQ-CANC-010
잡는 변이: **M3 (단독)**

**Given** 로컬 `Order`(shopify_order_id=90003, cancelled_at=None, closed_at=None). 모킹 응답: `{"id": 90003, "cancelled_at": None, "closed_at": "2026-08-05T00:00:00Z"}`

**When** `reconcile_order_status_for_ids(..., [90003])` 호출

**Then** `closed_at == 2026-08-05T00:00:00Z`(양성 증거) **그리고** `cancelled_at is None`(필드 교차 없음).

**판별력**: no-op 변이는 `closed_at`이 `None`으로 남아 첫 단정이 실패하고, 두 필드 대입을 뒤바꾸는 변이(M3)는 두 번째 단정이 실패한다.

---

## AC-CANC-004 — 취소-only 레코드: cancelled_at만 반영, closed_at은 그대로 NULL (대칭) `[CORE]`

Traces: REQ-CANC-010
잡는 변이: **M4 (단독)**

**Given** 로컬 `Order`(shopify_order_id=90004, cancelled_at=None, closed_at=None). 모킹 응답: `{"id": 90004, "cancelled_at": "2026-08-06T00:00:00Z", "closed_at": None}`

**When** `reconcile_order_status_for_ids(..., [90004])` 호출

**Then** `cancelled_at == 2026-08-06T00:00:00Z` **그리고** `closed_at is None`.

**판별력**: AC-CANC-003과 대칭 — 반대 방향 필드 교차(M4)도 잡힌다.

---

## AC-CANC-005 — [핵심, v0.3.0 판별력 복구] 로컬에 없는 주문은 예외 없이 스킵되고, 같은 청크의 나머지 처리는 계속된다 `[CORE]`

Traces: REQ-CANC-009
잡는 변이: **M5 (단독)**

**Given** 로컬 `Order` 테이블에 `shopify_order_id=90005`인 행이 없음. 같은 청크에 함께 들어가는 로컬 `Order`(shopify_order_id=**90006**, cancelled_at=None)가 **별도로 존재**. `fetch_order_status_by_ids`(§0.2 규약 3) 모킹 응답: `[{"id": 90005, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}, {"id": 90006, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]`(**[v0.4.0 정정, 3차 감사 D-N8]** v0.3.0의 `900005 + 1 (=90005b)` 표기는 산술도 표기도 실행 불가능했다 — 실제 정수 id로 정정했다).

**When** `reconcile_order_status_for_ids(..., [90005, 90006])` 호출(둘 다 기본 청크 크기 250 안에 포함되어 같은 청크)

**Then** 예외가 발생하지 않고, 반환된 `changed`에 90005가 포함되지 않으며, `Order.objects.filter(shopify_order_id=90005).exists()`는 여전히 `False` **그리고** 반환값의 `chunk_failures == []`(예외가 삼켜지지 않았다는 증거) **그리고** 90006의 `cancelled_at`이 실제로 갱신됐다(같은 청크의 나머지 레코드가 계속 처리됐다는 양성 증거).

**판별력**: `existing[r["id"]]`처럼 직접 인덱싱하는 변이(M5)는 `KeyError`를 던지지만, 그 예외는 청크 레벨 `except Exception`(`plan.md` §1.1)에 삼켜진다 — 이 경우 "예외 없음"·"90005 미포함"·"exists() False" 세 단정은 **전부 우연히 참**이 된다(감사 D2가 지적한 정확한 함정). `chunk_failures == []` 단정이 이 삼켜진 예외를 잡는다(변이 하에서 `chunk_failures`는 `[{"ids": [90005, 90006], "error": "'90005'"}]` 형태가 되어 빈 리스트가 아니게 된다) — **그리고** 예외로 청크 처리가 중단되면 90006도 처리되지 못하므로 그 양성 증거도 함께 잡는다. 두 겹의 방어선이다.

---

## AC-CANC-006 — 요청 URL이 올바른 status=any, ids=, fields=, limit= 를 모두 포함한다 `[CORE, v0.3.0 확장]`

Traces: REQ-CANC-001
잡는 변이: **M6 (단독)**

**Given** `_get_with_headers` 모킹, 호출 인자를 캡처.

**When** `fetch_order_status_by_ids(domain, token, [90006, 90007])` 호출

**Then** `_get_with_headers`에 전달된 요청 경로 문자열에 `status=any`, `ids=90006,90007`, `fields=id,cancelled_at,closed_at`, `limit=250`이 **전부** 포함된다.

**판별력**: `status=open`이 남는 복사-붙여넣기 실수(M6)나 `fields=`/`limit=` 누락은 각각 대응하는 단정에서 잡힌다 — `fields=` 누락은 프로덕션에서 매 요청이 전체 주문 페이로드를 끌어오는 성능 저하로 이어지지만 모킹 환경에서는 값 자체는 통과할 수 있으므로, 파라미터 존재를 직접 확인하는 이 AC가 유일한 방어선이다(2차 감사 D5, review-1 D6의 잔여분).

---

## AC-CANC-007 — [핵심, v0.4.0 확장] 청킹 헬퍼는 250개 상한을 지키고, 기본 청크 크기가 실제로 250이며, 실제 크기의 URL도 안전한 길이다 `[CORE, 순수 함수]`

Traces: REQ-CANC-002
잡는 변이: **M7 (단독)**

**Given** 정수 260개짜리 평범한 리스트(`list(range(1000000000000, 1000000000260))`, 13자리 — 실제 Shopify 주문 id 자릿수를 흉내낸다).

**When** `chunks = list(_chunked(ids, 250))` 호출

**Then** 첫 청크 길이 `== 250`, 둘째 청크 길이 `== 10`, 두 청크를 이어붙이면 원본과 완전히 동일 **그리고** 첫 청크를 `",".join(str(i) for i in chunks[0])`로 조인한 문자열 길이가 4,000자 미만이다(측정치 약 3,610자, `spec.md` A1 참고) **그리고** `shopify_orders.IDS_CHUNK_SIZE == 250`이고, `reconcile_order_status_for_ids`의 `chunk_size` 매개변수 기본값이 `IDS_CHUNK_SIZE`와 같다(`inspect.signature(reconcile_order_status_for_ids).parameters["chunk_size"].default`로 확인하거나, 상수를 직접 대조).

**판별력**: 250개 상한을 넘기거나 요소를 누락/중복하는 변이(M7)는 앞 세 단정에서 잡힌다. 길이 단정은 실제 프로덕션 규모(13자리 id 250개)로 URL을 조립해보는 유일한 AC다. **[v0.4.0 신설, 3차 감사 D-N1, blocking]** 마지막 단정은 `IDS_CHUNK_SIZE`가 250이 아닌 다른 값(예: 1000)으로 바뀌는 변이를 잡는다 — v0.3.0까지는 AC-CANC-007/008/016이 전부 `chunk_size`를 `_chunked(ids, 250)`처럼 **명시적으로 넘겨** 호출했으므로, `reconcile_order_status_for_ids`의 실제 기본값 자체를 단정하는 AC가 하나도 없었다(`spec.md`가 REQ-CANC-002 → AC-CANC-007로 커버를 선언했음에도, 그 REQ의 "최대 250개" 규범을 실제로 검출하지 못하는 상태였다). 이 변이는 프로덕션에서 매 요청이 약 14KB짜리 URL로 나타나며, 모킹 환경에서는 이 단정 없이는 통과했을 것이다.

---

## AC-CANC-008 — [핵심] 후보 집합이 청크 크기를 초과하면 모든 청크가 처리된다 `[CORE]`

Traces: REQ-CANC-011
잡는 변이: **M8 (단독)**

**Given** 로컬 `Order` 3건(A=90008a, B=90008b, C=90008c, 전부 `cancelled_at=None`). `fetch_order_status_by_ids`(§0.2 규약 3) 모킹, 호출 인자(청크)에 따라 다른 응답 반환: `chunk=[A,B]` → 두 레코드(`cancelled_at=T`), `chunk=[C]` → 한 레코드(`cancelled_at=T`).

**When** `reconcile_order_status_for_ids("gimssine", domain, token, [A,B,C], chunk_size=2)` 호출(청크 1=[A,B], 청크 2=[C])

**Then** A, B, **그리고 특히 마지막 청크에만 있던 C**의 `cancelled_at`이 모두 `T`로 갱신된다.

**판별력**: 첫 반복 후 종료하는 변이(M8)는 C가 반영되지 않아 잡힌다.

---

## AC-CANC-009 — 방어적: 예상 밖 Link 헤더도 끝까지 따라간다 `[CORE]`

Traces: REQ-CANC-003
잡는 변이: **M9 (단독)**

**Given** `_get_with_headers` 모킹 순차 응답: 1차 — 주문 1건(`id=90009a`) + `Link` 헤더(`rel="next"`, `page_info=xyz`); 2차(`page_info=xyz` 요청) — 주문 1건(`id=90009b`) + Link 헤더 없음.

**When** `fetch_order_status_by_ids(domain, token, [90009a, 90009b])` 호출

**Then** 반환된 레코드 목록에 두 주문이 모두 포함된다.

**판별력**: `while path:` 루프를 생략하는 변이(M9)는 `90009b`가 누락돼 잡힌다.

---

## AC-CANC-010 — [핵심, v0.3.0 확장] 반영된 주문은 자동으로 후보 집합에서 제외되고, 스토어 경계를 넘지 않는다 `[CORE]`

Traces: REQ-CANC-004, REQ-CANC-005
잡는 변이: **M10 (단독)**

**Given** 로컬 `Order`(store_type="gimssine", shopify_order_id=90010, cancelled_at=None, closed_at=None)와 로컬 `Order`(store_type="etoile", shopify_order_id=90010b, cancelled_at=None, closed_at=None). 조정 전 `open_candidate_order_ids("gimssine", closed_grace_days=None)`을 호출해 90010이 **포함됨**을 먼저 확인한다.

**When** 모킹 응답(`cancelled_at="2026-08-11T00:00:00Z"`)으로 `reconcile_order_status_for_ids("gimssine", domain, token, [90010])`을 실행한 뒤, `open_candidate_order_ids("gimssine", closed_grace_days=None)`을 다시 호출한다.

**Then** `Order.cancelled_at == 2026-08-11T00:00:00Z`(양성 증거) **그리고** 두 번째 `open_candidate_order_ids("gimssine", ...)` 결과에 90010이 포함되지 않는다 **그리고** `open_candidate_order_ids("etoile", closed_grace_days=None)`의 결과에 gimssine 주문 90010이 포함되지 않는다(스토어 스코핑, REQ-CANC-005, 2차 감사 D13).

**판별력**: 후보 집합 쿼리가 `closed_at` 조건만 걸고 `cancelled_at`을 놓치는 변이는 두 번째 단정에서 잡힌다. `store_type` 필터를 빠뜨리는 변이는 세 번째 단정에서 잡힌다.

---

## AC-CANC-011 — [핵심, v0.3.0 신설] closed_grace_days 창이 최근 종료 주문은 포함하고 오래된 종료 주문은 제외하며, 무제한 모드는 둘 다 포함한다 `[CORE]`

Traces: REQ-CANC-004
잡는 변이: **M11 (단독)**

**Given** 로컬 `Order` 3건(전부 `cancelled_at=None`): X(closed_at=None, 항상 후보), Y(closed_at=현재-10일, 30일 창 이내), Z(closed_at=현재-60일, 30일 창 밖).

**When** `open_candidate_order_ids("gimssine", closed_grace_days=30)`과 `open_candidate_order_ids("gimssine", closed_grace_days=None)`을 각각 호출.

**Then** `closed_grace_days=30` 결과에는 X, Y가 포함되고 Z는 **포함되지 않는다** **그리고** `closed_grace_days=None` 결과에는 X, Y, Z **전부** 포함된다.

**판별력**: 부등호가 반전되거나(`<=` 대신 `>=`) `closed_at IS NULL` 분기가 누락되는 변이(M11)는 첫 번째 단정에서 잡힌다. `closed_grace_days=None`일 때도 `closed_at` 조건을 걸어버리는 변이(무제한 모드가 실제로는 유계인 버그)는 두 번째 단정(Z 누락)에서 잡힌다.

---

## AC-CANC-012 — [핵심, v0.3.0 신설] Shopify가 반환하지 않은 요청 id는 missing_ids에 기록된다 `[CORE]`

Traces: REQ-CANC-006
잡는 변이: **M12 (단독)**

**Given** 로컬 `Order` 2건(A=90012a, B=90012b, `cancelled_at=None`). `fetch_order_status_by_ids`(§0.2 규약 3) 모킹 응답이 A의 레코드만 반환하고 B는 응답에서 **누락**(Shopify 삭제 시나리오 재현).

**When** `reconcile_order_status_for_ids("gimssine", domain, token, [A, B])` 호출

**Then** 반환값의 `missing_ids`에 B의 `shopify_order_id`가 포함된다 **그리고** A는 정상 반영된다(양성 증거 — 이 시나리오가 청크 전체를 실패시키지 않았음을 증명).

**판별력**: `missing_ids`를 계산하지 않거나 항상 빈 리스트로 두는 변이(M12)는 첫 단정에서 잡힌다.

---

## AC-CANC-024 — [v0.5.0 신설] 잠금 대기 시간 초과 예외는 chunk_failures에 lock_timeout=True로 구분 기록되고, 다른 예외는 False로 기록된다 `[CORE]`

Traces: REQ-CANC-025
잡는 변이: **M24 (단독)**

**Given** 로컬 `Order` 2건(A=90024a, B=90024b, 전부 `cancelled_at=None`). `fetch_order_status_by_ids`(§0.2 규약 3)를 모킹해 `chunk=[A]` 요청 시 `django.db.utils.OperationalError("(1205, 'Lock wait timeout exceeded; try restarting transaction')")`를 던지고, `chunk=[B]` 요청 시 일반 `ValueError("malformed response")`를 던지도록 설정.

**When** `reconcile_order_status_for_ids("gimssine", domain, token, [A, B], chunk_size=1)` 호출(청크 1=[A], 청크 2=[B])

**Then** 반환값의 `chunk_failures`에 정확히 2건이 있고, A를 포함하는 엔트리의 `"lock_timeout"`이 `True`, B를 포함하는 엔트리의 `"lock_timeout"`이 `False`다.

**판별력**: `lock_timeout` 키 자체를 기록하지 않는 변이나 항상 `False`(또는 항상 `True`)로 고정하는 변이(M24)는 두 엔트리 중 하나에서 값이 기대와 달라 잡힌다. 에러 메시지/코드 매칭 로직이 없거나 틀린 변이도 동일하게 잡힌다.

---

## 감지 커맨드 AC (`test_sync_order_cancellations_command.py`)

## AC-CANC-013 — [핵심] StoreSyncWatermark 무변경 + 실제 반영 확인 `[COMMAND]`

Traces: REQ-CANC-024
잡는 변이: **M13 (단독)**

**Given** `StoreSyncWatermark(store_type="gimssine", last_synced_updated_at=T_old, last_run_at=T_old2)` 존재. 로컬 `Order`(shopify_order_id=90013, cancelled_at=None). `_get_with_headers`(§0.2 규약 1) 모킹이 취소 처리됨을 반영하도록 구성.

**When** `call_command("sync_order_cancellations", "--store", "gimssine")` 실행

**Then** `StoreSyncWatermark.objects.get(store_type="gimssine")`의 두 필드가 실행 전과 완전히 동일하다 **그리고** `Order.objects.get(shopify_order_id=90013).cancelled_at`이 모킹 값으로 갱신됐다(양성 증거).

**판별력**: 이 SPEC의 코드가 실수로 `StoreSyncWatermark`를 참조·갱신하면(M13) 첫 단정이 실패한다. 커맨드가 아무 일도 하지 않는 변이는 두 번째 단정에서 잡힌다.

---

## AC-CANC-014 — [핵심, v0.3.0 신설] 감지 커맨드는 closed_grace_days=30을 전달한다 `[COMMAND]`

Traces: REQ-CANC-014
잡는 변이: **M14 (단독)**

**Given** `order.management.commands.sync_order_cancellations.open_candidate_order_ids`(§0.2 규약 4)를 모킹해 호출 인자를 캡처하고 빈 리스트를 반환하도록 설정.

**When** `call_command("sync_order_cancellations", "--store", "gimssine")` 실행

**Then** `open_candidate_order_ids`가 `closed_grace_days=30` 키워드 인자로 호출됐다.

**판별력**: 감지 커맨드가 `closed_grace_days`를 생략(함수 기본값 `None` 적용, 무제한)하거나 다른 값을 전달하는 변이(M14)는 이 단정에서 잡힌다 — 이 실수는 비용 유계화를 조용히 무너뜨리지만 정확성에는 영향이 없어 다른 어떤 AC도 대신 잡을 수 없다.

---

## AC-CANC-015 — 한 스토어의 실패가 다른 스토어의 처리를 막지 않는다 `[COMMAND]`

Traces: REQ-CANC-013, REQ-CANC-015
잡는 변이: **M15 (단독)**

**Given** `open_candidate_order_ids`(§0.2 규약 2)에 스토어별 `side_effect`: `store_type="gimssine"`이면 `RuntimeError` 발생, `store_type="etoile"`이면 실제 후보 id 목록 반환. `_get_with_headers`(§0.2 규약 1)는 etoile의 취소 처리를 정상 반영하도록 모킹. 로컬 `Order`(store_type="etoile", shopify_order_id=90015, closed_at=None) 존재.

**When** `call_command("sync_order_cancellations")`(기본값 `--store all`) 실행

**Then** etoile의 `Order.closed_at`이 실제로 갱신됐다.

**판별력**: 스토어 루프의 `try/except`를 루프 바깥에 두는 변이(M15)는 첫 예외에서 `handle()` 전체가 중단돼 etoile이 전혀 처리되지 않는다.

---

## AC-CANC-016 — 한 청크의 실패가 나머지 청크 처리를 막지 않고, 실패 id가 기록된다 `[COMMAND, v0.3.0 확장]`

Traces: REQ-CANC-012, REQ-CANC-016
잡는 변이: **M16 (단독)**

**Given** 로컬 `Order` 2건(A=90016a, B=90016b, `cancelled_at=None`). `fetch_order_status_by_ids`(§0.2 규약 3)를 모킹해 `chunk=[A]` 요청 시 예외를 던지고 `chunk=[B]` 요청 시 정상 응답(`cancelled_at=T`)을 반환하도록 설정.

**When** `reconcile_order_status_for_ids("gimssine", domain, token, [A, B], chunk_size=1)` 호출(청크 1=[A], 청크 2=[B])

**Then** B의 `cancelled_at == T`(청크 2가 처리됨) **그리고** 반환값의 `chunk_failures`가 정확히 1건이며 그 항목의 `"ids"`에 A의 `shopify_order_id`가 포함된다(오류 문자열뿐 아니라 대상 id가 기록됨, 2차 감사 D6).

**판별력**: 청크 루프의 `try/except`가 전체 함수를 감싸는 변이는 B 미처리로 첫 단정에서 잡힌다. `chunk_failures.append(str(exc))`처럼 오류 문자열만 남기고 id를 버리는 변이(M16)는 두 번째 단정에서 잡힌다.

---

## AC-CANC-017 — [핵심, v0.4.0 확장] 실패가 있으면 0이 아닌 종료 코드 — 스토어 레벨 실패와 청크 레벨 실패 둘 다 `[COMMAND]`

Traces: REQ-CANC-013, REQ-CANC-017
잡는 변이: **M17 (단독)**

**시나리오 1 — 스토어 레벨 실패**

**Given** AC-CANC-015와 동일한 설정(gimssine 실패, §0.2 규약 2).

**When** `call_command("sync_order_cancellations")` 실행

**Then** `CommandError`가 발생한다(`pytest.raises(CommandError, match="gimssine")`).

**시나리오 2 — [v0.4.0 신설, 3차 감사 D-N2, blocking] 청크 레벨 실패**

**Given** gimssine에 로컬 `Order` 1건(A=90017a, `cancelled_at=None`) — 후보 집합이 A 하나뿐이므로 그 유일한 청크가 실패하면 `reconcile_order_status_for_ids`는 예외를 밖으로 던지지 않고 `chunk_failures`가 비어 있지 않은 상태로 정상 반환한다(REQ-CANC-016/AC-CANC-016이 이미 보장하는 성질). etoile에 로컬 `Order` 1건(B=90017b, `cancelled_at=None`)도 존재. `fetch_order_status_by_ids`(§0.2 규약 3)에 `side_effect`를 걸어 A를 포함하는 요청(gimssine 쪽)은 예외를 던지고, B를 포함하는 요청(etoile 쪽)은 정상 응답(`cancelled_at=T`)을 반환하도록 설정한다.

**When** `call_command("sync_order_cancellations")`(기본값 `--store all`, 두 스토어 모두 처리) 실행

**Then** B의 `Order.cancelled_at == T`(etoile은 실제로 처리됐다는 양성 증거 — gimssine의 청크 실패가 전체 정지를 뜻하지 않는다) **그리고** `CommandError`가 발생한다(`pytest.raises(CommandError, match="partial")`).

**판별력**: 두 시나리오 모두에서 실패를 조용히 삼키는 변이(M17)는 예외가 발생하지 않아 잡힌다. **시나리오 2가 겨냥하는 구체적 변이**는 `plan.md`의 커맨드 구현에서 `if result["chunk_failures"]: ... failed.append(f"{store_type} (partial)")`의 **`failed.append(...)` 한 줄만 빠지는 것**이다 — `self.stderr.write(...)`로 로그는 남지만 `failed` 리스트에는 추가되지 않아, 함수 끝의 `if failed: raise CommandError(...)`가 트리거되지 않는다. v0.3.0까지는 AC-CANC-017의 유일한 시나리오가 스토어 레벨 실패(`open_candidate_order_ids`가 던지는 예외, §0.2 규약 2)였고, 그 실패는 애초에 커맨드의 바깥 `try/except`에서 잡혀 `failed`에 들어가므로 이 한 줄과 무관하게 통과한다 — 즉 이 변이는 23개 AC를 전부 통과했다(`spec.md` §8 C6이 스스로 "한 청크에 영구적 실패 원인이 있으면 같은 청크의 나머지가 매 사이클 함께 실패로 계상된다"고 예상하는 바로 그 시나리오이며, 그때 유일한 경보 경로가 이 한 줄이었다).

---

## AC-CANC-018 — [핵심, v0.3.0 확장] 매뉴얼 필드와 LineItem·ShippingLine·Refund 전체가 감지 잡에 의해 보존된다 `[COMMAND]`

Traces: REQ-CANC-007, REQ-CANC-008, REQ-CANC-022, REQ-CANC-023
잡는 변이: **M18 (단독)**

**Given** 로컬 `Order`(shopify_order_id=90018, status="shipped"[비기본값], note="고객 특별 요청 메모"[비어있지 않음], ready_to_ship=True, cancelled_at=None). 딸린 `LineItem` 1건(logistics_status="shipment_confirmed"[비기본값], rack_number="A-7"[비기본값], received_quantity=2[비기본값], purchase_status="in_stock"[비기본값], **original_sku="9788901234567"[비기본값, 2차 감사 D10]**), `PurchaseOrder` 1건과 M2M 연결. **`ShippingLine` 1건, `Refund` 1건**을 이 주문에 연결(2차 감사 D9 — 파괴 범위 회귀 방어선). `_get_with_headers`(§0.2 규약 1) 모킹 응답: `{"id": 90018, "cancelled_at": "2026-08-11T00:00:00Z", "closed_at": None}`(다른 필드는 애초에 응답에 없음).

**When** `call_command("sync_order_cancellations", "--store", "gimssine")` 실행

**Then** `Order.cancelled_at == 2026-08-11T00:00:00Z`(처리 증거) **그리고** `Order.status`/`note`/`ready_to_ship`이 전부 무변경 **그리고** 그 `LineItem`의 5개 필드(logistics_status/rack_number/received_quantity/purchase_status/original_sku)와 `PurchaseOrder` 연결이 무변경 **그리고** 그 주문의 `ShippingLine.objects.filter(order=order).count()`와 `Refund.objects.filter(order=order).count()`가 실행 전후 동일하다.

**판별력**: `_sync_single_order()`나 `update_or_create(defaults=...)` 같은 광역 쓰기 경로를 경유하는 변이(M18)는 `note`가 `None`으로 덮어써져 잡힌다. `line_items`/`shipping_lines`/`refunds` 키 부재로 인한 stale-삭제까지 경유하면 `LineItem`(PO 연결 없는 경우) 삭제, `ShippingLine` 전량 삭제(`shopify_orders.py:291`), `Refund` 전량 삭제(`:306`)가 발생해 각각의 카운트 단정에서 잡힌다 — 이 저장소의 환불 넷팅 회귀 이력(과거 SPEC-ORDER-023/026)을 고려한 저비용 방어선이다.

---

## AC-CANC-025 — [v0.5.0 신설] 스토어의 모든 실패가 잠금 대기 시간 초과면 CommandError를 발생시키지 않고(연성), 하나라도 아니면 발생시킨다(경성) — 두 경우 모두 실패는 기록·로그된다 `[COMMAND]`

Traces: REQ-CANC-026
잡는 변이: **M25 (단독, 2개 시나리오)**

**시나리오 1 — 전부 잠금 대기 시간 초과(연성)**

**Given** gimssine에 로컬 `Order` 1건(A=90025a, `cancelled_at=None`) — 후보 집합이 A 하나뿐이므로 유일한 청크가 실패한다. etoile에 로컬 `Order` 1건(B=90025b, `cancelled_at=None`)도 존재. `fetch_order_status_by_ids`(§0.2 규약 3)에 `side_effect`를 걸어 A를 포함하는 요청은 `django.db.utils.OperationalError("(1205, 'Lock wait timeout exceeded; try restarting transaction')")`를 던지고, B를 포함하는 요청은 정상 응답(`cancelled_at=T`)을 반환하도록 설정. stderr 캡처 가능한 형태로 호출.

**When** `call_command("sync_order_cancellations", stderr=<buffer>)`(기본값 `--store all`) 실행

**Then** `CommandError`가 발생하지 않는다(정상 종료) **그리고** B의 `Order.cancelled_at == T`(etoile 정상 처리, 양성 증거) **그리고** 캡처된 stderr에 gimssine의 실패와 A의 `shopify_order_id`가 여전히 기록·출력된다(정보 손실 없음, 양성 증거).

**시나리오 2 — [대조] 잠금 대기 시간 초과가 아닌 실패가 하나라도 섞이면(경성)**

**Given** 시나리오 1과 동일하되, A를 포함하는 요청이 대신 일반 `ValueError("malformed response")`(잠금 대기 시간 초과가 아님)를 던지도록 설정.

**When** `call_command("sync_order_cancellations")`(기본값 `--store all`) 실행

**Then** `CommandError`가 발생한다(`pytest.raises(CommandError, match="gimssine")`).

**판별력**: `lock_timeout` 여부를 무시하고 항상 `failed`에 추가하는 변이(연성 분류 자체가 없는 회귀)는 시나리오 1에서 `CommandError`가 발생해 잡힌다. 반대로 실패 종류와 무관하게 항상 `failed`에서 제외하는 변이(모든 실패를 연성으로 취급 — 진짜 실패까지 침묵시키는 위험한 회귀)는 시나리오 2에서 `CommandError`가 발생하지 않아 잡힌다. 두 시나리오가 REQ-CANC-026의 양방향(연성일 때 침묵, 경성일 때 경보)을 모두 검증하는 대조쌍이다.

---

## 백필 커맨드 AC (`test_backfill_order_cancellations_command.py`)

## AC-CANC-019 — [핵심, v0.3.0 신설] 백필 커맨드는 closed_grace_days=None(무제한)을 전달한다 `[COMMAND]`

Traces: REQ-CANC-019
잡는 변이: **M19 (단독)**

**Given** `order.management.commands.backfill_order_cancellations.open_candidate_order_ids`(§0.2 규약 4)를 모킹해 호출 인자를 캡처하고 빈 리스트를 반환하도록 설정.

**When** `call_command("backfill_order_cancellations", "--store", "gimssine")` 실행

**Then** `open_candidate_order_ids`가 `closed_grace_days=None` 키워드 인자로 호출됐다.

**판별력**: 백필이 실수로 창이 걸린 값(예: 30)을 전달하는 변이(M19)는 이 단정에서 잡힌다 — 이 실수는 30일 창을 넘긴 잔여 노출(`spec.md` §8 C5)을 흡수하는 유일한 경로를 조용히 없앤다.

---

## AC-CANC-020 — [핵심] 기존 미반영 취소 주문(52건 유형)을 정확히 반영한다 `[COMMAND]`

Traces: REQ-CANC-018
잡는 변이: **M20 (단독)**

**Given** 로컬 `Order`(shopify_order_id=90020, cancelled_at=None, closed_at=None). `_get_with_headers`(§0.2 규약 1) 모킹 응답: `{"id": 90020, "cancelled_at": "2026-07-01T00:00:00Z", "closed_at": None}`

**When** `call_command("backfill_order_cancellations", "--store", "gimssine")` 실행

**Then** `Order.cancelled_at == 2026-07-01T00:00:00Z`.

**판별력**: 백필이 조회를 수행하지 않거나 결과를 반영하지 않는 변이(M20)는 값이 `None`으로 남아 잡힌다.

---

## AC-CANC-021 — --dry-run은 아무것도 쓰지 않는다 + 진단은 실제로 보고된다 `[COMMAND]`

Traces: REQ-CANC-020
잡는 변이: **M21 (단독)**

**Given** 로컬 `Order`(shopify_order_id=90021, cancelled_at=None). `_get_with_headers`(§0.2 규약 1) 모킹 응답: `{"id": 90021, "cancelled_at": "2026-07-02T00:00:00Z", "closed_at": None}`. stdout 캡처 가능한 형태로 호출.

**When** `call_command("backfill_order_cancellations", "--store", "gimssine", "--dry-run", stdout=<buffer>)` 실행

**Then** `Order.objects.get(shopify_order_id=90021).cancelled_at is None`(무변경) **그리고** 캡처된 stdout에 `"90021"`과 `"would_change"`가 포함된다(양성 증거 — 조회·diff가 실제로 수행됐다는 증거).

**판별력**: `dry_run`이 쓰기를 막지 못하는 변이는 첫 단정에서, 진단 자체를 건너뛰는 변이는 두 번째 단정에서 잡힌다.

---

## AC-CANC-022 — [v0.3.0 확장] 매뉴얼 필드와 LineItem·ShippingLine·Refund 전체가 백필에 의해 보존된다 `[COMMAND]`

Traces: REQ-CANC-007, REQ-CANC-008, REQ-CANC-022, REQ-CANC-023
잡는 변이: **M22 (단독)**

**Given** AC-CANC-018과 동일한 픽스처 구성(매뉴얼 필드·`LineItem`·`ShippingLine`·`Refund` 전부 비기본값/존재)을 백필 대상으로 배치.

**When** `call_command("backfill_order_cancellations", "--store", "gimssine")` 실행

**Then** AC-CANC-018과 동일한 단정 — `cancelled_at`은 갱신되고, 나머지는 전부 무변경이다.

**판별력**: AC-CANC-018과 동일한 논리, 백필 커맨드 진입점에서 독립적으로 재확인한다.

---

## AC-CANC-023 — [핵심, v0.3.0 서술 축소] 백필을 두 번 연속 실행해도 값이 동일하고 예외/중복 행이 없다 `[COMMAND]`

Traces: REQ-CANC-018
잡는 변이: **M23 (단독)**

**Given** 로컬 `Order`(shopify_order_id=90023, cancelled_at=None, closed_at=None). `_get_with_headers`(§0.2 규약 1) 모킹이 **두 번의 커맨드 실행 모두에서 동일한 구체값**을 반환: `{"id": 90023, "cancelled_at": "2026-07-03T00:00:00Z", "closed_at": None}`.

**When** `call_command("backfill_order_cancellations", "--store", "gimssine")`을 연속으로 두 번 실행

**Then** **첫 번째** 실행 직후 `Order.cancelled_at == 2026-07-03T00:00:00Z`(양성 증거) **그리고** 두 번째 실행이 예외를 던지지 않으며 값이 여전히 동일하고 `Order.objects.filter(shopify_order_id=90023).count() == 1`.

**판별력**: 재실행마다 새 `Order` 행을 생성하는 변이(M23)는 `unique_together` 위반으로 `IntegrityError`가 나거나 `count()`가 2가 되어 잡힌다. 첫 실행 자체가 반영에 실패하는 변이는 첫 번째 단정에서 잡힌다. **[v0.3.0 정정, 2차 감사 D14]** "값이 흔들린다"는 변이는 이 아키텍처에서 재현 불가능하다 — 두 번째 실행 시 90023은 이미 `cancelled_at`이 채워져 후보 집합에서 자동 제외되므로(REQ-CANC-004) 그 주문에 대한 재조회 자체가 일어나지 않는다. 따라서 이 AC가 실제로 잡는 것은 (a) 중복 행 생성, (b) 첫 실행 무반영 두 가지뿐이며, 이 서술이 그 실제 판별력을 정확히 반영한다.

---

## 추적표 (AC → 변이)

| AC | 성격 | 잡는 변이 |
|----|------|-----------|
| AC-CANC-001 | 핵심 판별자 | **M1 (단독)** |
| AC-CANC-002 | 핵심 판별자 | **M2 (단독)** |
| AC-CANC-003 | 핵심 판별자(필드 매핑) | **M3 (단독)** |
| AC-CANC-004 | 대칭 케이스 | **M4 (단독)** |
| AC-CANC-005 | 핵심 판별자(예외 삼킴 방어) | **M5 (단독)** |
| AC-CANC-006 | 요청 형태 검증 | **M6 (단독)** |
| AC-CANC-007 | 순수 함수 단위 테스트 | **M7 (단독)** |
| AC-CANC-008 | 핵심 판별자 | **M8 (단독)** |
| AC-CANC-009 | 방어적 회귀 방지 | **M9 (단독)** |
| AC-CANC-010 | 핵심 판별자 | **M10 (단독)** |
| AC-CANC-011 | 핵심 판별자(창 로직) | **M11 (단독)** |
| AC-CANC-012 | 핵심 판별자(진단 보고) | **M12 (단독)** |
| AC-CANC-013 | 핵심 판별자(역방향 규약) | **M13 (단독)** |
| AC-CANC-014 | 핵심 판별자(파라미터 전달) | **M14 (단독)** |
| AC-CANC-015 | 핵심 판별자 | **M15 (단독)** |
| AC-CANC-016 | 핵심 판별자(진단 보고) | **M16 (단독)** |
| AC-CANC-017 | 핵심 판별자 | **M17 (단독)** |
| AC-CANC-018 | 핵심 판별자 | **M18 (단독)** |
| AC-CANC-019 | 핵심 판별자(파라미터 전달) | **M19 (단독)** |
| AC-CANC-020 | 핵심 판별자 | **M20 (단독)** |
| AC-CANC-021 | 핵심 판별자(역방향 규약) | **M21 (단독)** |
| AC-CANC-022 | 핵심 판별자 | **M22 (단독)** |
| AC-CANC-023 | 핵심 판별자(역방향 규약) | **M23 (단독)** |
| AC-CANC-024 | 핵심 판별자(잠금 대기 시간 초과 분류) | **M24 (단독)** |
| AC-CANC-025 | 핵심 판별자(연성/경성 대조쌍) | **M25 (단독, 2개 시나리오)** |

**변이 커버리지 확인**: M1~M25 전부 최소 1개 AC가 잡으며, 25개 전부 단독 판별자다.

**[HARD] 단독 판별자 보호 규칙**: 위 25개 AC 중 어느 것도 삭제·약화·픽스처 단순화되면 해당 변이가 즉시 미커버가 된다. 특히:
- AC-CANC-005의 `chunk_failures == []` + 형제 주문 양성 증거 — 이 둘을 제거하면 청크 레벨 예외 삼킴이 다시 이 AC를 무력화한다(v0.3.0의 핵심 수정 사항).
- AC-CANC-013/021/023의 양성 증거 단정 — 절대 제거하지 않는다.
- AC-CANC-011의 세 주문(X/Y/Z) 픽스처와 두 가지 `closed_grace_days` 값 호출 — 하나만 남으면 창 로직의 절반이 미검증된다.
- AC-CANC-014/019의 호출 인자 캡처 — 값이 다른 두 파라미터(30 vs None)를 명시적으로 대조한다.
- AC-CANC-025의 시나리오 2(대조) — 시나리오 1만 남기면 "모든 실패를 무조건 연성으로 취급"하는 위험한 회귀(진짜 실패까지 침묵)를 이 SPEC의 어떤 AC도 잡지 못하게 된다.

---

## 엣지 케이스 요약

| # | 케이스 | 대응 AC |
|---|--------|---------|
| 1 | 신규 취소/종료 감지 (기본 동작) | AC-CANC-001, AC-CANC-002 |
| 2 | 필드 매핑 정확성 | AC-CANC-003, AC-CANC-004 |
| 3 | 로컬 미존재 주문 + 예외 삼킴 방어 | AC-CANC-005 |
| 4 | 요청 파라미터 정확성 | AC-CANC-006 |
| 5 | 청킹 완전성(순수 함수 + 통합) | AC-CANC-007, AC-CANC-008 |
| 6 | 방어적 페이지네이션 | AC-CANC-009 |
| 7 | 후보 집합 자동 축소 + 스토어 스코핑 | AC-CANC-010 |
| 8 | 종료 후 취소 사각지대 (창 로직) | AC-CANC-011 |
| 9 | Shopify 삭제 주문 진단 | AC-CANC-012 |
| 10 | 워터마크 격리 | AC-CANC-013 |
| 11 | 감지/백필의 창 파라미터 전달 | AC-CANC-014, AC-CANC-019 |
| 12 | 스토어·청크별 실패 격리 + 진단 + 종료 코드 | AC-CANC-015, AC-CANC-016, AC-CANC-017 |
| 13 | 매뉴얼 필드/LineItem/ShippingLine/Refund 보존 | AC-CANC-018, AC-CANC-022 |
| 14 | 기존 미반영 취소 반영(52건 재현) | AC-CANC-020 |
| 15 | `--dry-run` | AC-CANC-021 |
| 16 | 백필 멱등성 | AC-CANC-023 |
| 17 | 잠금 대기 시간 초과 분류 + 연성/경성 실패 처리(동시성) | AC-CANC-024, AC-CANC-025 |

---

## Definition of Done

### 신규 검증
- [ ] AC-CANC-001 ~ AC-CANC-012, AC-CANC-024 전부 통과 (`backend/order/tests/test_spec_029.py`)
- [ ] AC-CANC-013 ~ AC-CANC-018, AC-CANC-025 전부 통과 (`backend/order/tests/test_sync_order_cancellations_command.py`)
- [ ] AC-CANC-019 ~ AC-CANC-023 전부 통과 (`backend/order/tests/test_backfill_order_cancellations_command.py`)
- [ ] **RED 성립 확인**: 25개 AC 전부 — 작성 직후 무수정 코드에서 실행해 `ImportError` 또는 `AssertionError`로 전부 실패함을 직접 확인한다.
- [ ] AC-CANC-005의 `chunk_failures == []` + 형제 양성 증거 단정을 유지한다(v0.3.0 핵심 수정).
- [ ] AC-CANC-013/021/023의 양성 증거 단정을 유지한다.
- [ ] AC-CANC-018/022의 비기본값 매뉴얼 필드 + `ShippingLine`/`Refund` 픽스처를 유지한다.
- [ ] **[v0.5.0 신설]** AC-CANC-025의 시나리오 1(연성)과 시나리오 2(경성) 둘 다 유지한다 — 시나리오 2가 없으면 "모든 실패를 연성으로 취급"하는 회귀를 잡을 AC가 없어진다.
- [ ] §0.2의 패치 대상 규약(4분류)을 그대로 따른다 — 특히 쓰기 결과를 단정하는 AC에서 `reconcile_order_status_for_ids`/`open_candidate_order_ids` 자체를 패치하지 않는다.

### 회귀 검증
- [ ] `backend/order/tests/test_shopify_orders.py` 전부 무수정 통과.
- [ ] `backend/order/tests/test_sync_orders_command.py`, `test_backfill_missing_orders_command.py`, `test_order_resync.py`, `test_store_sync_watermark.py` 전부 무수정 통과.
- [ ] `git diff --stat scripts/sync_orders.bat` 공집합.
- [ ] `git diff backend/order/shopify_orders.py` — 변경이 파일 끝에 추가된 신규 함수 4개와 모듈 레벨 `timedelta` import 1건에 국한된다.
- [ ] `git diff --stat backend/order/models.py` 공집합.

### 코드 범위 검증
- [ ] `backend/order/migrations/` 신규 파일 **0건**.
- [ ] `backend/order/management/commands/sync_order_cancellations.py`, `backfill_order_cancellations.py`가 `LineItem`/`ShippingLine`/`Refund`를 import/참조하지 않는다.
- [ ] 두 커맨드 모두 `StoreSyncWatermark`류의 어떤 커서 모델도 import/참조하지 않는다.

### 스케줄러 검증
- [ ] `scripts/sync_order_cancellations.bat`이 "새 인스턴스를 시작하지 않음" REM 2줄을 포함한다.
- [ ] Windows 작업 스케줄러에 `scm_v2 sync_order_cancellations` 작업이 등록되고, `-MultipleInstances IgnoreNew` 설정이 확인되며, 최소 1회 종료 코드 0으로 실행됨을 확인한다.
- [ ] **[v0.5.0 신설, REQ-CANC-027]** 등록된 `sync_order_cancellations` 작업의 **실제 트리거 시작 시각**(작업이 "존재한다"는 사실이 아니라 `Get-ScheduledTaskInfo`/작업 스케줄러 GUI에서 확인한 `-At` 값)이 `sync_orders` 작업의 트리거 시각(`:X4:05` 정렬)과 최소 2분 이상 어긋나 있음을 직접 확인한다 — 등록 스크립트를 기존 `sync_orders` 작업의 `-At (Get-Date)` 패턴을 그대로 복사해 만들면 이 검증이 실패한다(스태거링이 조용히 무효화되는 가장 흔한 실수, `spec.md` §1.2).
- [ ] **[v0.4.0 신설, 3차 감사 D-N5]** `backfill_order_cancellations --store all`을 저빈도(예: 월 1회) 작업으로 등록했거나, 등록하지 않기로 한 결정을 `.moai/project/scheduled-jobs.md`에 명시적으로 기록했다 — 30일 유예 창을 넘긴 잔여 노출(`spec.md` §8 C5)을 흡수하는 유일한 경로가 미등록 상태로 방치되지 않도록 한다(이 저장소에는 권고로만 남은 정기 작업이 실제로는 등록되지 않아 `ExchangeRate` 동기화가 멈췄던 선례가 있다).

### 문서
- [ ] `spec.md` HISTORY에 구현 결과(통과 테스트 수, 실제 백필 실행 결과, 배포 후 관측된 감지 커맨드 `candidates=N` 실수치, 스케줄러 등록 확인, mx_plan 실행 결과) 기록.
- [ ] `.moai/project/scheduled-jobs.md`에 3번째 작업(`sync_order_cancellations`) 추가는 `/moai sync` 단계에서 수행.
