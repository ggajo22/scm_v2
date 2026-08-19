# SPEC-ORDER-029 — 구현 계획 (v0.5.0)

## 0. 재설계·수정 배경

**v0.3.0**: plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-029-review-2.md`, **FAIL, 0.71**)의 D1(major, blocking)이 v0.2.0의 후보 집합 정의(`cancelled_at IS NULL AND closed_at IS NULL`)가 "첫 상태 전이"에서 관측을 멈춘다는 사각지대를 지적했다 — 종료가 먼저 일어난 주문은 후보 집합을 영구 이탈하고, 그 뒤의 취소를 어떤 자동 경로도 감지하지 못한다(실측 1,170건 중 1건, 0.09%지만 영구 미감지). review-2 D1이 제기한 이 문제에 대해, 저자가 "취소는 종결, 종료는 아니다"라는 비대칭을 반영한 유예 창(`closed_grace_days`) 방식을 독자적으로 설계했다(`spec.md` §1.1이 review-2의 실제 세 선택지와 이 설계의 관계를 정확히 서술한다 — v0.4.0 D-N3 정정) — 후보 집합에 `closed_grace_days` 파라미터를 추가해 감지는 30일 창으로 반복 비용을 유계화하고, 백필은 무제한으로 잔여 노출을 흡수한다.

같은 리뷰의 D2(AC-CANC-005 판별력 상실)·D6(청크 영구 실패 시 진단 불가)·D8(테스트 패치 규약이 쓰기 결과 단정을 불가능하게 만듦)·D9(파괴 범위 과소 서술)도 함께 반영했다.

**v0.4.0**: plan-auditor 3차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-029-review-3.md`, **FAIL, 0.80**, 4회차 감사 불필요 판정)의 blocking 4건을 반영한다 — D-N1(REQ-CANC-002의 "최대 250개"를 검출하는 AC 부재, AC-CANC-007 확장), D-N2(REQ-CANC-017의 "청크 실패" 절반을 검출하는 AC 부재, AC-CANC-017에 청크 레벨 실패 시나리오 추가), D-N3(후보 집합 생애주기 실측치의 출처 오귀속, `spec.md` 정정), D-N4(REQ-CANC-011 EARS 라벨이 HISTORY에서만 정정 단정되고 본문은 미수정, `spec.md` 정정). 권고 사항(D-N5 백필 스케줄러 DoD화, D-N6 단조 증가·429 노출 개방 위험 기록, D-N7 패치 규약 4분류 동기화, D-N11 중복 import 제거)도 함께 반영했다. 감사가 "설계는 옳고 남은 것은 판별력 격자의 구멍 2개와 출처 문장 2개"라고 명시한 종결 회차다.

**v0.5.0**: 코디네이터 지시(신규 plan-auditor 감사 없이 적용) — 사용자가 제기한 동시성 문제(감지 커맨드와 기존 `sync_orders`의 겹침, `spec.md` §1.2/D10/REQ-CANC-025~027)를 구현 계획에 반영한다. `reconcile_order_status_for_ids()`의 예외 핸들러가 MySQL 잠금 대기 시간 초과(에러 1205)를 별도 식별하는 `_is_lock_wait_timeout(exc)` 헬퍼와 `chunk_failures`의 `lock_timeout` 키를 추가하고(§1.1), 감지 커맨드가 "스토어의 모든 실패가 잠금 대기 시간 초과인가"를 기준으로 `failed` 목록 추가 여부를 가르도록 확장한다(§1.3). 스케줄러 등록 절차에 `sync_orders`와 최소 2~3분 어긋난 트리거 오프셋 지정을 명시한다(§1.5). 기존 4개 파일 중 3개(`shopify_orders.py`, `sync_order_cancellations.py`, 스케줄러 등록 절차)만 확장하며, 신규 파일은 추가하지 않는다 — 영향 파일 개수는 7개로 불변이다(§3).

---

## 1. 접근 개요 — 공유 코어 함수 4개(파라미터 확장) + 커맨드 2개 (신규 모델 없음)

### 1.1 공유 코어 — `shopify_orders.py`에 함수 4개 추가

```python
# shopify_orders.py 파일 상단 기존 import 블록에 추가 (v0.3.0, 감사 D16 대응 —
# 함수 내부 재import 대신 모듈 레벨에 둔다. parse_datetime은 이미 :8에서
# 모듈 레벨로 import돼 sync_store()가 사용 중이므로(:442), 그 관례를 따른다)
from datetime import timedelta
# (django.utils.dateparse.parse_datetime, django.utils.timezone은 이미 모듈
#  상단에 import돼 있다 — 신규 import는 timedelta 하나뿐)

SHOPIFY_ORDER_STATUS_FIELDS = "id,cancelled_at,closed_at"
IDS_CHUNK_SIZE = 250


def _chunked(seq, size):
    """Pure helper: split seq into consecutive slices of at most `size`.
    No I/O, no Django imports — trivially unit-testable on a plain list.
    """
    seq = list(seq)
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def fetch_order_status_by_ids(domain, token, shopify_order_ids, fields=SHOPIFY_ORDER_STATUS_FIELDS):
    """Query orders.json?ids=<up to 250 comma-separated>&status=any&fields=...
    &limit=250 for an EXPLICIT list of Shopify order IDs (<=250), returning
    their CURRENT cancelled_at/closed_at values regardless of status.

    SPEC-ORDER-029 REQ-CANC-001/002: verified in production 2026-08-19
    (this session, NOT review-1 — see spec.md Assumption A1 for the
    corrected attribution) that a request for exactly 250 ids returns
    exactly 250 records, both timestamp fields populated, and NO Link
    header. This function still defensively follows a Link header if one
    unexpectedly appears (REQ-CANC-003), reusing the existing
    _parse_next_page_info() helper — but the expected path issues exactly
    one HTTP call.

    Caller MUST pass <=250 ids (REQ-CANC-002) — chunking is the caller's
    responsibility, see reconcile_order_status_for_ids() below.
    """
    if not shopify_order_ids:
        return []
    ids_param = ",".join(str(i) for i in shopify_order_ids)
    path = f"orders.json?ids={ids_param}&status=any&limit=250&fields={fields}"
    records = []
    while path:
        body, headers = _get_with_headers(domain, token, path)
        records.extend(body.get("orders", []))
        link = headers.get("Link") or headers.get("link")
        page_info = _parse_next_page_info(link)
        path = (
            f"orders.json?limit=250&page_info={page_info}&fields={fields}"
            if page_info
            else None
        )
    return records


def open_candidate_order_ids(store_type, closed_grace_days=None):
    """SPEC-ORDER-029 REQ-CANC-004/005 (v0.3.0 — plan-auditor review-2 D1
    fix): the reconciliation candidate set — local Order rows whose
    cancellation state is not yet known, scoped to one store.

    Asymmetric definition: cancellation is treated as terminal (Shopify has
    no public un-cancel API, spec.md Assumption A6) but closure is NOT —
    an order can be archived (closed_at set) and cancelled afterwards
    (measured 1/1,170 in production this session). So:

        cancelled_at IS NULL
        AND (closed_at IS NULL OR closed_at >= now - closed_grace_days)

    closed_grace_days=None (default) means the closed_at condition is not
    applied at all — every non-cancelled order is a candidate, regardless
    of how long ago it closed. This is what backfill_order_cancellations
    uses (REQ-CANC-019): unbounded, because it runs once/occasionally, not
    every 5 minutes.

    closed_grace_days=30 is what sync_order_cancellations uses
    (REQ-CANC-014): bounds recurring cost while keeping recently-closed
    orders under observation for the realistic window where a
    closure-then-cancellation could still arrive.

    .order_by("shopify_order_id") makes chunk composition deterministic
    across repeated calls (MySQL/InnoDB already returns rows in
    approximately PK order without it, but explicit ordering means a
    chunk_failures report for "chunk N" correlates to the same order-id
    subset on the next cycle — see REQ-CANC-012 / spec.md §8 C6).
    """
    from django.db.models import Q
    from .models import Order
    # NOTE (v0.4.0, 3차 감사 D-N11a): `timezone` is NOT re-imported here —
    # it is already a module-level import (see :20-21's own comment and
    # shopify_orders.py:7, sync_store() already uses timezone.now() at
    # :430). Re-importing it locally would repeat exactly the anti-pattern
    # D16 removed for parse_datetime, on a different symbol.

    qs = Order.objects.filter(store_type=store_type, cancelled_at__isnull=True)
    if closed_grace_days is not None:
        threshold = timezone.now() - timedelta(days=closed_grace_days)
        qs = qs.filter(Q(closed_at__isnull=True) | Q(closed_at__gte=threshold))
    return list(qs.order_by("shopify_order_id").values_list("shopify_order_id", flat=True))


def _is_lock_wait_timeout(exc):
    """SPEC-ORDER-029 REQ-CANC-025 (v0.5.0): identify a MySQL "Lock wait
    timeout exceeded" failure (InnoDB error 1205) so the caller can
    classify it separately from other chunk failures. This is the
    concurrency exposure spec.md §1.2 documents: sync_orders(:60) holds
    row locks on Order for its full ~18-24s runtime inside a single
    transaction.atomic() (measured this session, spec.md A7/A8) and our
    innodb_lock_wait_timeout=50s means an abnormally long sync_orders run
    can make a chunk's bulk_update() time out.

    Deliberately string-matches rather than importing a specific driver
    exception class — mysqlclient/PyMySQL both surface this as
    django.db.utils.OperationalError wrapping a DB-API error whose first
    arg is (1205, "Lock wait timeout exceeded; try restarting
    transaction"). Matching on "1205" is more robust across driver
    versions than matching the full message text.
    """
    return "1205" in str(exc) or "Lock wait timeout exceeded" in str(exc)


def reconcile_order_status_for_ids(store_type, domain, token, shopify_order_ids, dry_run=False, chunk_size=IDS_CHUNK_SIZE):
    """Narrow-write Order.cancelled_at/closed_at for the given LOCAL
    shopify_order_ids, chunked at `chunk_size` (default 250, REQ-CANC-002).
    Every chunk is attempted even if an earlier one raises (REQ-CANC-011/
    016 — per-chunk isolation). Never routes through _sync_single_order()
    or a broad update_or_create(defaults=...) (REQ-CANC-007/008) — that
    path nulls out every other Order field AND unconditionally deletes
    PurchaseOrder-unlinked LineItems (:287-289), ALL ShippingLine rows
    (:291), and ALL Refund rows (:306) with no regeneration source in a
    fields=-limited payload (spec.md Assumption A4).

    Returns {
        "scanned": int,               # records actually returned by Shopify
        "changed": list[dict],        # {"shopify_order_id", "cancelled_at", "closed_at"}
        "chunk_failures": list[dict], # {"ids": list[int], "error": str,
                                       #  "lock_timeout": bool} — v0.3.0,
                                       # review-2 D6: carries the AFFECTED ids, not
                                       # just the error string, so an operator can
                                       # identify which orders are stuck.
                                       # "lock_timeout" added v0.5.0, REQ-CANC-025:
                                       # True when _is_lock_wait_timeout(exc) — lets
                                       # the caller (sync_order_cancellations)
                                       # distinguish a self-healing MySQL lock
                                       # contention failure from a genuine one
                                       # (REQ-CANC-026, spec.md D10).
        "missing_ids": list[int],     # requested but not returned by Shopify —
                                       # v0.3.0, review-2 D1: usually means the
                                       # order was deleted on Shopify's side.
    }
    When dry_run=True, `changed` is still populated (diff computed) but no
    bulk_update() call happens — same "changed" key in both modes; the
    caller chooses its own display label ("would_change" vs "changed") for
    stdout only.
    """
    from django.db import transaction
    from .models import Order

    scanned = 0
    changed: list[dict] = []
    chunk_failures: list[dict] = []
    missing_ids: list[int] = []

    for chunk in _chunked(shopify_order_ids, chunk_size):
        try:
            # HTTP fetch happens OUTSIDE the DB transaction — a slow
            # Shopify round-trip must not hold a DB transaction/lock open.
            records = fetch_order_status_by_ids(domain, token, chunk)
            scanned += len(records)

            returned_ids = {r["id"] for r in records}
            missing_ids.extend(i for i in chunk if i not in returned_ids)

            with transaction.atomic():
                existing = {
                    o.shopify_order_id: o
                    for o in Order.objects.filter(
                        store_type=store_type, shopify_order_id__in=chunk
                    ).only("id", "shopify_order_id", "cancelled_at", "closed_at")
                }

                to_update = []
                for r in records:
                    order = existing.get(r["id"])
                    if order is None:
                        continue  # REQ-CANC-009: not locally matched — skip

                    new_cancelled = parse_datetime(r["cancelled_at"]) if r.get("cancelled_at") else None
                    new_closed = parse_datetime(r["closed_at"]) if r.get("closed_at") else None
                    if order.cancelled_at != new_cancelled or order.closed_at != new_closed:
                        changed.append(
                            {
                                "shopify_order_id": order.shopify_order_id,
                                "cancelled_at": new_cancelled,
                                "closed_at": new_closed,
                            }
                        )
                        if not dry_run:
                            order.cancelled_at = new_cancelled
                            order.closed_at = new_closed
                            to_update.append(order)

                if to_update:
                    Order.objects.bulk_update(to_update, ["cancelled_at", "closed_at"])
        except Exception as exc:  # noqa: BLE001 - one chunk must not abort the rest
            chunk_failures.append(
                {
                    "ids": list(chunk),
                    "error": str(exc),
                    "lock_timeout": _is_lock_wait_timeout(exc),  # v0.5.0, REQ-CANC-025
                }
            )
            continue

    return {
        "scanned": scanned,
        "changed": changed,
        "chunk_failures": chunk_failures,
        "missing_ids": missing_ids,
    }
```

**핵심 설계 판단**:

- **(A) 비대칭 후보 집합.** `open_candidate_order_ids()`가 `closed_grace_days` 파라미터로 두 커맨드의 서로 다른 요구(감지=유계 반복 비용, 백필=무제한 1회성 재확인)를 하나의 함수로 표현한다 — 각자 다른 쿼리를 재구현하지 않는다.
- **(B) `.order_by("shopify_order_id")`.** 청크 구성을 사이클 간에 결정론적으로 만든다 — 영구 실패가 있을 때 `chunk_failures`의 id 목록이 매 사이클 같은 부분집합을 가리켜, 운영자가 그 대상을 정확히 특정할 수 있다(spec.md §8 C6).
- **(C) `chunk_failures`가 실패 id 목록을 담는다.** `{"ids": list(chunk), "error": str(exc)}` — 오류 문자열만으로는 어느 주문이 조정되지 못했는지 알 수 없었다(v0.2.0의 결함, 감사 D6).
- **(D) `missing_ids`가 요청-응답 차이를 추적한다.** `returned_ids = {r["id"] for r in records}`로 응답에 실제로 있는 id 집합을 구하고, 청크에는 있었지만 응답에 없는 id를 `missing_ids`에 담는다 — Shopify에서 삭제된 주문의 신호다(감사 D1의 부수 지적).
- **(E) HTTP 호출은 트랜잭션 밖.** `fetch_order_status_by_ids()` 호출이 `transaction.atomic()` 밖에서 실행돼 Shopify 왕복 시간 동안 DB 락을 쥐지 않는다.
- **(F) 좁은 쓰기.** `bulk_update(to_update, ["cancelled_at", "closed_at"])`가 정확히 그 두 컬럼만 쓴다.
- **(G) `chunk_size` 파라미터로 테스트 용이성 확보.** 프로덕션은 기본값 250, 테스트는 작은 값을 넘겨 다중 청크 경로를 검증한다.
- **(H) `dry_run`은 진단만 하고 쓰기를 건너뛴다.** `to_update.append()`가 `if not dry_run:` 블록 안에 있다.
- **(I) `_is_lock_wait_timeout()`이 잠금 대기 시간 초과를 문자열 매칭으로 식별한다(v0.5.0, REQ-CANC-025).** 특정 드라이버 예외 클래스를 import하지 않고 `"1205" in str(exc)`로 판정한다 — mysqlclient/PyMySQL 모두 이 실패를 `django.db.utils.OperationalError`로 감싸되 내부 DB-API 예외 형태는 드라이버마다 다를 수 있어, 에러 코드 문자열 매칭이 클래스 매칭보다 강건하다. 이 분류가 `chunk_failures`에 남아야만 감지 커맨드(§1.3)가 REQ-CANC-026의 연성/경성 구분을 할 수 있다 — 이 함수 자체는 `failed` 여부를 판단하지 않는다(그 판단은 호출자의 책임, 관심사 분리).

### 1.2 신규 모델 — **없음**

`backend/order/migrations/`에 이 SPEC이 추가하는 파일은 0건이다.

### 1.3 신규 커맨드 1 — `sync_order_cancellations` (상시 감지, 5분 주기)

```python
# backend/order/management/commands/sync_order_cancellations.py

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from order.shopify_orders import open_candidate_order_ids, reconcile_order_status_for_ids

STORE_TYPES = ["gimssine", "etoile"]
CLOSED_GRACE_DAYS = 30  # REQ-CANC-014


def _credentials(store_type):
    if store_type == "gimssine":
        return settings.SHOPIFY_GIMSSINE_DOMAIN, settings.SHOPIFY_GIMSSINE_TOKEN
    return settings.SHOPIFY_ETOILE_DOMAIN, settings.SHOPIFY_ETOILE_TOKEN


class Command(BaseCommand):
    help = (
        "Detect newly cancelled/closed Shopify orders and reflect "
        "cancelled_at/closed_at locally. Candidate set is derived fresh "
        "from the local Order table each run (cancelled_at IS NULL, "
        f"closed_at within the last {CLOSED_GRACE_DAYS} days or never "
        "closed) — no cursor. Never touches StoreSyncWatermark. A store "
        "whose chunk failures are ALL MySQL lock-wait timeouts (expected "
        "under overlap with sync_orders, spec.md §1.2) is logged but does "
        "NOT raise CommandError (REQ-CANC-026) — any other failure still "
        "does."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--store", choices=[*STORE_TYPES, "all"], default="all",
            help="Store to scan (default: all)",
        )

    def handle(self, *args, **options):
        stores = STORE_TYPES if options["store"] == "all" else [options["store"]]
        failed = []

        for store_type in stores:
            try:
                domain, token = _credentials(store_type)
                candidate_ids = open_candidate_order_ids(store_type, closed_grace_days=CLOSED_GRACE_DAYS)
                result = reconcile_order_status_for_ids(store_type, domain, token, candidate_ids)
            except Exception as exc:  # noqa: BLE001 - one store must not abort the other
                self.stderr.write(self.style.ERROR(f"[{store_type}] FAILED: {exc}"))
                failed.append(store_type)
                continue

            if result["chunk_failures"]:
                self.stderr.write(self.style.ERROR(f"[{store_type}] {len(result['chunk_failures'])} chunk(s) failed"))
                for cf in result["chunk_failures"]:
                    tag = "lock_timeout" if cf.get("lock_timeout") else "error"
                    self.stderr.write(self.style.ERROR(f"  ids={cf['ids']} {tag}={cf['error']}"))
                # REQ-CANC-026 (v0.5.0, spec.md D10): a store whose chunk
                # failures are ALL lock-wait timeouts is a soft failure —
                # self-healing next cycle via candidate-set re-entry
                # (REQ-CANC-004) — do not raise CommandError for it. The
                # failure is still logged above (no information loss). Any
                # non-lock-timeout failure mixed in is still a hard failure.
                if not all(cf.get("lock_timeout") for cf in result["chunk_failures"]):
                    failed.append(f"{store_type} (partial)")

            if result["missing_ids"]:
                self.stdout.write(
                    self.style.WARNING(f"[{store_type}] missing from Shopify response: {result['missing_ids']}")
                )

            self.stdout.write(
                f"[{store_type}] candidates={len(candidate_ids)} "
                f"scanned={result['scanned']} changed={len(result['changed'])}"
            )

        if failed:
            raise CommandError(f"sync_order_cancellations failed for: {', '.join(failed)}")
        self.stdout.write(self.style.SUCCESS("done"))
```

**핵심 설계 판단**:

- **`CLOSED_GRACE_DAYS = 30`이 모듈 레벨 상수**로 명시돼 있어, `open_candidate_order_ids(store_type, closed_grace_days=CLOSED_GRACE_DAYS)` 호출 인자를 테스트에서 캡처해 직접 단정할 수 있다(REQ-CANC-014).
- **스토어 루프의 `try/except`**가 REQ-CANC-015(스토어 격리)를 구현한다.
- **`result["chunk_failures"]`**가 REQ-CANC-016(청크 격리)의 결과를 이 레벨로 끌어올리고, 실패 id 목록을 stderr에 출력한다(REQ-CANC-012).
- **`result["missing_ids"]`**가 REQ-CANC-006(요청-응답 차이 보고)을 stdout 경고로 표현한다.

### 1.4 신규 커맨드 2 — `backfill_order_cancellations` (1회성/정기 재실행, 수동)

```python
# backend/order/management/commands/backfill_order_cancellations.py

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from order.shopify_orders import open_candidate_order_ids, reconcile_order_status_for_ids

STORE_TYPES = ["gimssine", "etoile"]


def _credentials(store_type):
    if store_type == "gimssine":
        return settings.SHOPIFY_GIMSSINE_DOMAIN, settings.SHOPIFY_GIMSSINE_TOKEN
    return settings.SHOPIFY_ETOILE_DOMAIN, settings.SHOPIFY_ETOILE_TOKEN


class Command(BaseCommand):
    help = (
        "One-time (or periodically re-run) reconciliation: for each store, "
        "run the SAME reconciliation as sync_order_cancellations but with "
        "NO closed_grace_days bound (REQ-CANC-019) — every non-cancelled "
        "local order is re-checked regardless of how long ago it closed. "
        "This absorbs the residual exposure of sync_order_cancellations' "
        "30-day window (spec.md §8 C5). Supports --dry-run and verbose "
        "per-order reporting. Never touches StoreSyncWatermark."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--store", choices=[*STORE_TYPES, "all"], default="all",
            help="Store to scan (default: all)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would change without writing anything",
        )

    def handle(self, *args, **options):
        stores = STORE_TYPES if options["store"] == "all" else [options["store"]]
        dry_run = options["dry_run"]
        failed = []

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved"))

        total_scanned = 0
        total_changed = 0

        for store_type in stores:
            try:
                domain, token = _credentials(store_type)
                candidate_ids = open_candidate_order_ids(store_type, closed_grace_days=None)
                result = reconcile_order_status_for_ids(
                    store_type, domain, token, candidate_ids, dry_run=dry_run
                )
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(self.style.ERROR(f"[{store_type}] FAILED: {exc}"))
                failed.append(store_type)
                continue

            if result["chunk_failures"]:
                for cf in result["chunk_failures"]:
                    self.stderr.write(self.style.ERROR(f"  ids={cf['ids']} error={cf['error']}"))
                failed.append(f"{store_type} (partial)")

            total_scanned += result["scanned"]
            total_changed += len(result["changed"])
            label = "would_change" if dry_run else "changed"
            self.stdout.write(
                f"[{store_type}] candidates={len(candidate_ids)} "
                f"scanned={result['scanned']} {label}={len(result['changed'])}"
            )
            for c in result["changed"]:
                self.stdout.write(
                    f"  order {c['shopify_order_id']}: "
                    f"cancelled_at={c['cancelled_at']} closed_at={c['closed_at']}"
                )

        self.stdout.write(
            self.style.SUCCESS(f"\ndone - scanned={total_scanned}, changed={total_changed}")
        )
        if failed:
            raise CommandError(f"backfill_order_cancellations failed for: {', '.join(failed)}")
```

**핵심 설계 판단**:

- **`closed_grace_days=None`을 명시적으로 전달**한다(REQ-CANC-019) — 함수 기본값에 암묵적으로 기대지 않고, 테스트가 실제 호출 인자를 캡처해 단정할 수 있게 한다.
- **`OrderStatusSyncCursor`류의 어떤 모델도 import하지 않는다** — 그런 모델이 존재하지 않으므로 REQ-CANC-024를 위반할 코드 경로 자체가 없다.

### 1.5 스케줄러 등록 — `scripts/sync_order_cancellations.bat`

`scripts/sync_orders.bat`을 그대로 미러링하되 별도 로그 파일을 쓴다. **"새 인스턴스를 시작하지 않음" 경고 2줄을 포함한다**:

```batch
@echo off
REM Scheduled order cancellation/closure detection (SPEC-ORDER-029).
REM Registered in Windows Task Scheduler; do not run two copies at once --
REM the task must be configured with "Do not start a new instance".
setlocal

cd /d C:\app\scm_v2\backend || exit /b 1
set PYTHONIOENCODING=utf-8

if not exist "C:\app\scm_v2\logs" mkdir "C:\app\scm_v2\logs"

echo [%DATE% %TIME%] sync_order_cancellations start >> "C:\app\scm_v2\logs\sync_order_cancellations.log"
"C:\Users\ggajo\AppData\Local\Programs\Python\Python312\python.exe" manage.py sync_order_cancellations >> "C:\app\scm_v2\logs\sync_order_cancellations.log" 2>&1
set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] sync_order_cancellations exit=%RC% >> "C:\app\scm_v2\logs\sync_order_cancellations.log"

exit /b %RC%
```

작업 스케줄러 등록은 `.moai/project/scheduled-jobs.md` §3의 PowerShell 절차를 그대로 따르되 `-TaskName "scm_v2 sync_order_cancellations"`, 트리거 5분 간격, `-MultipleInstances IgnoreNew`로 별도 등록한다. `spec.md` §8 C5의 운영 권고(백필 정기 재실행)를 채택하는 경우, `backfill_order_cancellations --store all`을 저빈도(예: 월 1회)로 도는 별도 스케줄러 항목도 같은 패턴(`.bat` + `run_hidden.vbs`)으로 추가할 수 있다 — 이는 이 SPEC의 REQ가 아니라 선택적 운영 관행이다.

**트리거 오프셋 — REQ-CANC-027 (v0.5.0 신설, spec.md §1.2/D10)**: 기존 `sync_orders` 작업은 `:X4:05`(분%5==4, 초==05, 예: `:39:05`, `:44:05`)에 정렬돼 있다(실측, spec.md A7). 신규 작업의 `-At`을 **그대로 복사하면 두 잡이 매 사이클 거의 동시에 시작**해 §1.2의 잠금 대기 상호작용을 정상 상태에서도 유발한다 — 이는 이 개정이 막으려는 정확히 그 실수다. `New-ScheduledTaskTrigger`의 `-At`을 `sync_orders`보다 최소 2~3분 앞선 시각으로 명시적으로 지정한다:

```powershell
# WRONG — copies sync_orders' own -At pattern verbatim, reintroducing the
# overlap this SPEC exists to avoid (spec.md §1.2):
#   $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
#       -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)

# CORRECT — offset so this task's :X1:30 mark never coincides with
# sync_orders' measured :X4:05 mark, even if sync_orders runs several times
# longer than its measured 18-24s (spec.md A7/§1.2). Gaps in BOTH directions
# clear REQ-CANC-027's 2-minute floor:
#   :X1:30 -> next :X4:05  = 2m35s
#   :X4:05 -> next :X1:30  = 2m25s
# [정정, run 단계 전략 검증] 이전 판(`+ 2`, :X2:30)은 앞 방향 간격이 1m35s로
# REQ-CANC-027이 스스로 정한 "최소 2분" 하한에 미달했다 — 주석이 주장하던
# 2m35s는 `+ 1`(:X1:30)에서만 성립한다.
$staggeredStart = (Get-Date).Date.AddHours((Get-Date).Hour).AddMinutes((Get-Date).Minute - ((Get-Date).Minute % 5) + 1).AddSeconds(30)
$trigger = New-ScheduledTaskTrigger -Once -At $staggeredStart `
    -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)
```

등록 후 `Get-ScheduledTaskInfo`(또는 GUI)로 **실제 트리거 시각**이 `sync_orders`와 최소 2분 이상 어긋나 있는지 직접 확인한다(DoD, `acceptance.md` 스케줄러 검증 절) — "작업이 등록됐다"는 사실만으로는 오프셋이 실제로 적용됐는지 증명하지 못한다.

---

## 2. 마일스톤 (우선순위 순, 시간 예측 없음)

### M1 (Priority High) — 공유 코어 함수: RED → GREEN

1. `backend/order/tests/test_spec_029.py` `[NEW]` — AC-CANC-001~012, **AC-CANC-024(v0.5.0)** 대응(청킹 헬퍼, `ids=`+`status=any`+`fields=`+`limit=` 조회, 비대칭 후보 집합 산정과 창 검증, `missing_ids` 보고, 필드 기록, 잠금 대기 시간 초과 분류).
2. `shopify_orders.py` `[MODIFY]` — `_chunked()`, `fetch_order_status_by_ids()`, `open_candidate_order_ids()`, `reconcile_order_status_for_ids()`, **`_is_lock_wait_timeout()`(v0.5.0)** 추가(§1.1).

금지 사항:
- `_sync_single_order()` 호출 금지(REQ-CANC-008)
- `update_or_create(defaults=...)` 형태의 광역 쓰기 금지
- `Order` 이외의 모델(특히 `LineItem`/`ShippingLine`/`Refund`) 참조 금지
- 신규 마이그레이션/모델 추가 금지(§1.2)

완료 조건: AC-CANC-001~012, AC-CANC-024 전부 통과.

### M2 (Priority High) — 감지 커맨드: RED → GREEN

1. `backend/order/tests/test_sync_order_cancellations_command.py` `[NEW]` — AC-CANC-013~018, **AC-CANC-025(v0.5.0)** 대응(워터마크 무변경, `closed_grace_days=30` 전달, 스토어·청크 격리, 종료 코드, 매뉴얼 필드/`LineItem`/`ShippingLine`/`Refund` 보존, 잠금 대기 시간 초과의 연성/경성 분기). 쓰기 결과를 단정하는 AC는 `order.shopify_orders._get_with_headers`(HTTP 계층)를 패치한다 — `reconcile_order_status_for_ids`/`open_candidate_order_ids` 자체를 패치하지 않는다(§1.6 패치 규약 참조, 감사 D8).
2. `backend/order/management/commands/sync_order_cancellations.py` `[NEW]`(§1.3) — **v0.5.0**: `chunk_failures`의 `lock_timeout` 여부에 따라 `failed` 목록 추가를 분기한다(REQ-CANC-026).

완료 조건: AC-CANC-013~018, AC-CANC-025 전부 통과.

### M3 (Priority High) — 백필 커맨드: RED → GREEN

1. `backend/order/tests/test_backfill_order_cancellations_command.py` `[NEW]` — AC-CANC-019~023 대응(`closed_grace_days=None` 전달, 기존 미반영 취소 반영, `--dry-run`, 매뉴얼 필드 보존, 멱등성).
2. `backend/order/management/commands/backfill_order_cancellations.py` `[NEW]`(§1.4).

완료 조건: AC-CANC-019~023 전부 통과.

### M4 (Priority Medium) — 스케줄러 스크립트

1. `scripts/sync_order_cancellations.bat` `[NEW]`(§1.5, "새 인스턴스 시작 안 함" 경고 포함).
2. `scripts/sync_orders.bat` `[EXISTING]` — 무변경 확인.
3. Windows 작업 스케줄러에 `sync_orders`와 최소 2~3분 어긋난 `-At` 오프셋으로 실제 등록하고(§1.5, REQ-CANC-027, v0.5.0) 1회 이상 종료 코드 0으로 실행됨을 확인.

완료 조건: 신규 `.bat`이 원본 구조 5개 항목 전부를 미러링하며, 스케줄러 등록·실행이 확인되고, **등록된 작업의 실제 트리거 시각이 `sync_orders`와 최소 2분 이상 어긋나 있음을 `Get-ScheduledTaskInfo`로 확인함**(v0.5.0).

### M5 (Priority Medium) — @MX 태그 + 문서

§6 실행.

---

## 1.6 테스트 패치 대상 규약 (v0.3.0 신설, 감사 D8 대응 / v0.4.0 4분류로 동기화, 감사 D-N7 대응)

`acceptance.md` §0.2가 이 규약을 그대로 참조한다 — **4가지** AC 성격별로 패치 대상이 갈린다. (v0.3.0은 이 절과 `acceptance.md` §0.2의 분류 개수·구성원이 서로 달랐다 — "셋"이라 쓰고 4개를 나열하거나, 그룹 4를 이 절에서만 누락하는 등 D8을 고치기 위해 신설한 바로 이 절에서 배정 드리프트가 재발했었다. v0.4.0은 두 문서의 그룹 번호·구성원을 동일하게 맞춘다.)

1. **쓰기 결과를 단정하는 AC**(AC-CANC-013/018/020/021/022/023, 그리고 AC-CANC-015·017의 **정상 처리되는 쪽**): 실제 쓰기 경로가 살아 있어야 하므로 **HTTP 계층인 `order.shopify_orders._get_with_headers`만 패치**한다. 이 저장소의 기존 관례(`test_backfill_missing_orders_command.py:17`, `_GET_HEADERS_TARGET = "order.management.commands.backfill_missing_orders._get_with_headers"`)와 동일한 원리이나, SPEC-029의 두 커맨드는 `_get_with_headers`를 자기 네임스페이스로 import하지 않으므로(§1.3/1.4의 import 블록 참조) 패치 대상은 **정의된 모듈**(`order.shopify_orders._get_with_headers`)이다.
2. **스토어 레벨에서 실패를 주입해야 하는 AC**(AC-CANC-015, AC-CANC-017 시나리오 1): `order.management.commands.sync_order_cancellations.open_candidate_order_ids`에 스토어별로 분기하는 `side_effect`를 건다 — 실패시킬 스토어는 예외, 정상 스토어는 실제 후보 집합을 반환하도록 해, 정상 스토어 쪽은 1번 규약(HTTP 계층 패치)을 통해 실제 쓰기 경로를 탄다.
3. **청크 루프 자체를 검증하는 AC**(AC-CANC-005, AC-CANC-008, AC-CANC-012, AC-CANC-016, AC-CANC-017 시나리오 2, **AC-CANC-024, AC-CANC-025 — v0.5.0 신설**): `order.shopify_orders.fetch_order_status_by_ids`를 패치한다 — 청크별로 다른 응답/예외를 주입해야 하므로 이 레벨이 가장 직접적이다. AC-CANC-017 시나리오 2와 AC-CANC-025(양쪽 시나리오)는 이 그룹에 속하는 **커맨드 레벨** 테스트다 — `call_command()`로 실행하되 청크 실패(잠금 대기 시간 초과 예외 포함)는 이 함수 레벨에서 주입한다. AC-CANC-024는 **공유 코어 레벨**(`reconcile_order_status_for_ids()` 직접 호출)에서 동일한 패치 대상을 쓴다.
4. **호출 인자만 캡처하면 되는 AC**(AC-CANC-014, AC-CANC-019): `open_candidate_order_ids`를 직접 패치해 빈 리스트를 반환하도록 하고 호출 인자(`closed_grace_days`)를 캡처한다 — 쓰기 결과를 단정하지 않으므로 실제 쓰기 경로를 살려둘 필요가 없다.

---

## 3. 영향 파일 ([DELTA] 마커)

| 마커 | 파일 | 변경 내용 |
|------|------|-----------|
| **[MODIFY]** | `backend/order/shopify_orders.py` | `_chunked()`, `fetch_order_status_by_ids()`, `open_candidate_order_ids()`, `reconcile_order_status_for_ids()` 함수 추가 (기존 함수 무수정, `timedelta` 모듈 레벨 import 1건 추가) |
| **[NEW]** | `backend/order/management/commands/sync_order_cancellations.py` | 상시 감지 커맨드 |
| **[NEW]** | `backend/order/management/commands/backfill_order_cancellations.py` | 1회성 백필 커맨드 |
| **[NEW]** | `scripts/sync_order_cancellations.bat` | 스케줄러 진입점 |
| **[NEW]** | `backend/order/tests/test_spec_029.py` | 공유 코어 함수 테스트 |
| **[NEW]** | `backend/order/tests/test_sync_order_cancellations_command.py` | 감지 커맨드 테스트 |
| **[NEW]** | `backend/order/tests/test_backfill_order_cancellations_command.py` | 백필 커맨드 테스트 |
| **[EXISTING]** | `backend/order/models.py` | **무변경** — 신규 모델 없음 |
| **[EXISTING]** | `backend/order/migrations/` | **무변경** — 신규 마이그레이션 없음 |
| **[EXISTING]** | `backend/order/shopify_orders.py`의 `sync_store()`/`fetch_all_open_orders()`/`_sync_single_order()`/`_build_fulfillment_location_data()` | **무변경** |
| **[EXISTING]** | `backend/order/models.py`의 `StoreSyncWatermark` | **무변경**(REQ-CANC-024) |
| **[EXISTING]** | `scripts/sync_orders.bat` | **무변경**(REQ-CANC-021) |

신규/변경 파일은 **7개**다. CLAUDE.md Rule 2(3개 이상 파일 분해)에 따라 §2의 M1(공유 코어)/M2(감지)/M3(백필)/M4(스케줄러)로 분해해 순차 진행한다.

---

## 4. 위험과 대응

| ID | 위험 | 대응 |
|----|------|------|
| R1 | `reconcile_order_status_for_ids()`가 `_sync_single_order()`를 호출하거나 광역 `defaults` 딕셔너리를 쓰도록 잘못 구현되어, 다른 `Order` 필드가 `None`으로 덮어써지거나 `PurchaseOrder` 미연결 라인아이템·`ShippingLine`·`Refund`가 삭제된다 | AC-CANC-018/022가 매뉴얼 필드와 `LineItem`·`ShippingLine`·`Refund` 행 수가 정확히 보존되는지 직접 단정한다(v0.3.0 확장, 감사 D9) |
| R2 | 응답 레코드의 필드값이 로컬 `cancelled_at`/`closed_at`에 뒤바뀌어 쓰인다 | AC-CANC-003/004가 각각 한쪽 필드만 값을 가진 레코드로 매핑 정확성을 검증한다 |
| R3 | 청킹 루프가 첫 청크만 처리하고 종료한다 | AC-CANC-008이 `chunk_size` 오버라이드로 다중 청크 시나리오를 구성해 마지막 청크의 반영을 단정한다 |
| R4 | `ids=`/`status=any`/`fields=`/`limit=` 파라미터가 잘못 구성된다 | AC-CANC-006이 요청 경로 문자열에 네 파라미터가 전부 포함되는지 직접 단정한다(v0.3.0 확장, 감사 D5) |
| R5 | 요청 하나에 250개를 초과하는 id가 들어가거나, `IDS_CHUNK_SIZE`/`chunk_size` 기본값이 250이 아닌 다른 값으로 바뀐다(v0.4.0 확장, 3차 감사 D-N1 — 기존 AC들이 전부 `chunk_size`를 명시적으로 넘겨 호출해 기본값 자체를 단정하지 못했다) | AC-CANC-007이 `_chunked()`를 순수 함수로 직접 테스트하고, `IDS_CHUNK_SIZE == 250`과 `reconcile_order_status_for_ids`의 `chunk_size` 기본 인자가 그 상수와 같음을 직접 단정한다 |
| R6 | 예상 밖 `Link` 헤더가 와도 무시하고 첫 페이지만 처리한다 | AC-CANC-009가 단일 청크 요청에 예상 밖 `Link` 헤더가 포함된 모킹 응답을 구성해 단정한다 |
| R7 | 반영된 주문이 다음 조회에서도 계속 후보 집합에 남거나, 스토어 경계를 넘어 후보가 섞인다 | AC-CANC-010이 반영 전후 자동 축소와 스토어 스코핑을 함께 단정한다(v0.3.0 확장, 감사 D13) |
| R8 | **[v0.3.0 신규, 감사 D1]** `closed_grace_days` 창 로직이 잘못 구현돼(예: 부등호 반전, `closed_at IS NULL` 분기 누락) 최근 종료 주문이 감지에서 빠지거나, 반대로 오래된 종료 주문이 계속 후보로 남는다 | AC-CANC-011이 `closed_grace_days=30`으로 최근/오래된 종료 주문 각각의 포함 여부를 단정하고, `closed_grace_days=None`으로 무제한 동작도 함께 단정한다 |
| R9 | **[v0.3.0 신규, 감사 D1]** Shopify가 요청한 id를 반환하지 않아도(삭제된 주문) 그 사실이 어디에도 기록되지 않는다 | AC-CANC-012가 `missing_ids`에 그 id가 담기는지 직접 단정한다 |
| R10 | **[v0.3.0 신규, 감사 D2]** `existing[r["id"]]`처럼 직접 인덱싱하는 변이가 청크 레벨 `except Exception`에 삼켜져 AC-CANC-005의 세 단정이 전부 통과한다 | AC-CANC-005가 `chunk_failures == []`와 같은 청크의 다른 주문에 대한 양성 증거를 함께 단정한다 — 예외가 삼켜지면 `chunk_failures`가 비지 않게 되고, 같은 청크의 나머지 처리가 중단되면 양성 증거가 사라진다 |
| R11 | 이 SPEC의 코드가 실수로 `StoreSyncWatermark`를 참조·갱신한다 | AC-CANC-013이 무변경 단정을 해당 `Order.cancelled_at` 갱신이라는 양성 증거와 짝짓는다 |
| R12 | 감지 커맨드가 `closed_grace_days=30`이 아니라 다른 값(특히 `None`, 무제한)을 실수로 전달해 비용 유계화가 깨진다 | AC-CANC-014가 `open_candidate_order_ids` 호출 인자를 캡처해 `closed_grace_days == 30`을 직접 단정한다 |
| R13 | 백필 커맨드가 `closed_grace_days=None`이 아니라 다른 값을 전달해 무제한 재확인이 깨진다(30일 창을 넘긴 사각지대를 흡수하지 못함) | AC-CANC-019가 동일한 방식으로 `closed_grace_days is None`을 직접 단정한다 |
| R14 | 한 스토어의 실패가 다른 스토어 처리를 막는다 | AC-CANC-015가 한 스토어를 실패시키고 다른 스토어가 계속 처리됐는지 단정한다 |
| R15 | 한 청크의 실패가 같은 스토어의 나머지 청크 처리를 막거나, 실패 id가 기록되지 않는다 | AC-CANC-016이 청크 격리와 `chunk_failures`의 id 목록을 함께 단정한다(v0.3.0 확장, 감사 D6) |
| R16 | 스토어 레벨 실패에서는 종료 코드가 정상적으로 0이 아니지만, **청크 레벨 실패**(`result["chunk_failures"]`가 비어 있지 않은 경우)에서 `failed.append(f"{store_type} (partial)")` 한 줄이 누락돼 종료 코드가 0으로 끝난다 — §8 C6이 스스로 예상하는 시나리오이며, v0.3.0까지는 이 경로를 검증하는 AC가 없어 이 한 줄이 빠져도 23개 AC 전부가 통과했다(3차 감사 D-N2, blocking) | AC-CANC-017이 두 시나리오를 모두 단정한다 — 시나리오 1(스토어 레벨, 기존)은 `open_candidate_order_ids`가 예외를 던지는 경우, **시나리오 2(청크 레벨, v0.4.0 신설)는 `fetch_order_status_by_ids`가 특정 청크에서만 예외를 던지는 경우** — 두 경우 모두 `call_command()`를 거쳐 `CommandError`가 발생함을 직접 단정한다 |
| R17 | 백필이 기존 미반영 취소 주문(52건 유형)을 반영하지 않는다 | AC-CANC-020이 실제 반영 값을 직접 단정한다 |
| R18 | `--dry-run`인데 실제로 `bulk_update`가 호출된다 | AC-CANC-021이 DB 무변경을 stdout 진단 보고 양성 증거와 짝짓는다 |
| R19 | 백필을 두 번 실행하면 중복 행이 생기거나 예외가 난다 | AC-CANC-023이 구체적 모킹 값과 `count() == 1`을 단정한다(v0.3.0 축소 서술, 감사 D14 — "값이 흔들린다"는 이 아키텍처에서 재현 불가능한 변이이므로 서술에서 제외) |
| R20 | **[v0.5.0 신설]** `_is_lock_wait_timeout()`이 잠금 대기 시간 초과와 다른 예외를 구분하지 못해(예: 항상 `True`/`False` 고정, 에러 코드 매칭 누락) 감지 커맨드가 진짜 실패를 조용히 삼키거나(위험한 방향), 반대로 매 사이클 자기 치유형 실패에 경보를 계속 울린다(경보 피로 재발) | AC-CANC-024가 잠금 대기 시간 초과와 일반 예외를 같은 호출에서 함께 주입해 `lock_timeout` 필드 값이 각각 다름을 직접 단정한다 |
| R21 | **[v0.5.0 신설]** 스케줄러 등록 시 신규 작업의 `-At`을 `sync_orders`의 `-At (Get-Date)` 패턴을 그대로 복사해, 스태거링이 명목상으로만 존재하고 실제로는 두 잡이 매 사이클 거의 동시에 시작한다 — 이 실수는 어떤 pytest AC로도 잡을 수 없다(스케줄러 등록은 코드 밖의 운영 단계다) | `acceptance.md` DoD의 스케줄러 검증 절이 "작업이 등록됨"이 아니라 "등록된 작업의 실제 트리거 시각이 `sync_orders`와 최소 2분 이상 어긋남"을 `Get-ScheduledTaskInfo`로 직접 확인하도록 요구한다(v0.5.0, §1.5) |

---

## 5. 테스트 대상 함수 검토 — 예외 경계 전수 확인 (v0.3.0 신설, 프로세스 지시 대응)

`reconcile_order_status_for_ids()`의 청크 루프는 `try/except Exception`으로 감싸여 있다(§1.1). 이 절은 AC-CANC-001~025 각각의 변이가 이 경계(또는 다른 함수의 경계) 안에서 발생하는지, 발생한다면 예외로 삼켜져도 여전히 관측 가능한지 확인한 결과다.

- **예외를 던지는 변이이며 삼켜짐 위험이 있었던 것**: AC-CANC-005(`existing[r["id"]]` → `KeyError`) 1건뿐이었다 — R10/D2로 이미 수정.
- **논리 오류(값이 틀리거나 루프가 조기 종료)이며 예외를 던지지 않는 변이**: AC-CANC-001~004, 006, 008~012 — 이들은 예외가 아니라 잘못된 값/누락된 처리로 나타나므로, `try/except`의 존재와 무관하게 값 단정으로 직접 관측된다.
- **의도적으로 예외 삼킴 자체를 검증하는 AC**: AC-CANC-015(스토어 격리, `open_candidate_order_ids`가 던지는 예외가 스토어 루프 레벨에서 잡힘)와 AC-CANC-016(청크 격리, `fetch_order_status_by_ids`가 던지는 예외가 청크 레벨에서 잡힘) — 이 둘은 예외가 잡히는 것 자체가 올바른 동작이므로 문제가 아니다. 다만 각각 "다른 스토어/청크는 계속 처리됐다"는 양성 증거를 반드시 함께 요구한다(이미 그렇게 설계됨).
- **순수 함수라 예외 경계가 아예 없는 것**: AC-CANC-007(`_chunked()`, DB/네트워크 호출 없음).
- **[v0.5.0 신설] 예외가 청크 레벨 경계에 삼켜지는 것은 정상 동작이고, 검증 대상은 삼켜진 예외의 "분류"인 것**: AC-CANC-024는 `except Exception`이 예외를 잡는 것 자체를 문제 삼지 않는다 — 잡힌 뒤 `_is_lock_wait_timeout(exc)`가 그 예외를 올바르게 분류해 `chunk_failures`에 `lock_timeout` 필드로 남기는지만 검증한다. AC-CANC-025는 그 분류값이 감지 커맨드의 `failed` 판단(REQ-CANC-026)에 실제로 반영되는지를 스토어 레벨에서 재확인한다 — 두 AC 모두 "예외가 관측 가능한가"가 아니라 "관측된 예외가 올바르게 구분되는가"를 검증하는, 이전 22개 AC와는 다른 성격의 판별력이다.

---

## 6. MX 태그 계획

### 6.1 백엔드 — 신규 `@MX:NOTE`

`shopify_orders.py`의 `open_candidate_order_ids()` 함수 정의부 위(또는 함수 독스트링 자체)에 비대칭 후보 집합 설계 근거가 이미 문서화돼 있다(§1.1) — 별도 `@MX:NOTE`가 필요할 만큼 코드만 봐서 드러나지 않는 지점은 `reconcile_order_status_for_ids()`의 "왜 `_sync_single_order()`를 쓰지 않는가"이므로 그 함수 위에 1건:

```python
# @MX:NOTE: [AUTO] SPEC-ORDER-029 REQ-CANC-007/008: writes ONLY
# cancelled_at/closed_at via bulk_update(), never via _sync_single_order()
# or update_or_create(defaults=...). The ids=/fields= payload this function
# consumes lacks every other Order field AND lacks "line_items"/
# "shipping_lines"/"refunds", so routing through _sync_single_order() would
# null those fields out AND unconditionally delete PurchaseOrder-unlinked
# LineItems, all ShippingLine rows, and all Refund rows on the order.
```

fan_in 관찰: `reconcile_order_status_for_ids()`/`open_candidate_order_ids()`는 감지 커맨드 + 백필 커맨드 2곳에서 호출된다(fan_in=2) — `@MX:ANCHOR` 임계값(fan_in>=3)에는 못 미친다.

**[v0.5.0 신설]** `_is_lock_wait_timeout()` 위에 `@MX:NOTE` 1건 추가 — 왜 예외 클래스가 아니라 에러 코드 문자열을 매칭하는지, 그리고 이 판정이 `sync_orders`의 긴 트랜잭션(코드상 드러나지 않는 외부 사실)에서 비롯된 동시성 노출과 어떻게 연결되는지가 코드만 봐서는 드러나지 않기 때문이다:

```python
# @MX:NOTE: [AUTO] SPEC-ORDER-029 REQ-CANC-025: string-matches MySQL error
# 1205 ("Lock wait timeout exceeded") rather than a driver exception class
# because this failure originates entirely from sync_orders' long-held row
# locks (sync_orders.py:60, transaction.atomic() wraps a Shopify HTTP
# round-trip) — this function's own lock hold is milliseconds
# (bulk_update on 2 columns). See spec.md §1.2 for the full analysis.
```

### 6.2 프런트엔드 — 해당 없음

---

## 7. 검증 명령 (참고)

```bash
git status backend/order/migrations/

pytest backend/order/tests/test_spec_029.py --no-cov -v
pytest backend/order/tests/test_sync_order_cancellations_command.py --no-cov -v
pytest backend/order/tests/test_backfill_order_cancellations_command.py --no-cov -v

pytest backend/order/tests/test_shopify_orders.py backend/order/tests/test_sync_orders_command.py \
       backend/order/tests/test_backfill_missing_orders_command.py \
       backend/order/tests/test_order_resync.py backend/order/tests/test_store_sync_watermark.py \
       --no-cov -v

git diff --stat backend/order/shopify_orders.py
git diff --stat scripts/sync_orders.bat
git status backend/order/migrations/
git diff --stat backend/order/models.py
```

---

## 8. 완료 후 기록

`spec.md` HISTORY에 다음을 추가한다:
- 통과 테스트 수
- 실제 백필 실행 결과(52건 중 실제 반영 건수, 발주 연결 51건 라인아이템·환불 행 무변경 확인)
- 배포 후 관측된 감지 커맨드 실제 `candidates=N` 수치(§1.1의 사전 추정과 대조)
- 작업 스케줄러 등록·1회 이상 성공 실행 확인 결과
- **[v0.5.0 신설]** 등록된 `sync_order_cancellations` 작업의 실제 트리거 시각과 `sync_orders`와의 실측 오프셋(분 단위)
- **[v0.5.0 신설]** 배포 후 일정 기간 관측된 `chunk_failures`의 `lock_timeout=True` 발생 빈도(있다면) — D10의 연성 분류 판단이 실제 운영에서도 타당한지 재검토할 근거 자료로 남긴다
- mx_plan 실행 결과
