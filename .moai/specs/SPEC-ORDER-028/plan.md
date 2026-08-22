# SPEC-ORDER-028 — 구현 계획

## 0. 범위 요약

이 SPEC은 6개의 독립적이지만 서로 연결된 작업으로 구성된다:

1. `Order.last_resynced_at` 필드 + 마이그레이션 `0045`
2. 대상 판정 쿼리(라운드로빈 큐잉 로직)
3. 신규 관리 커맨드 `resync_order_sweep`(오케스트레이션 + 페이싱 + per-order 트랜잭션 + 위치 조회 실패 처리)
4. `_sync_single_order()` 리팩터 — 배치 불변 컨텍스트(`bundle_map`/`title_map`) 파라미터화
5. `_sync_single_order()` 리팩터 — 환불/배송라인 delete-and-recreate를 MySQL 호환 차등 upsert로 대체
6. 스케줄러 등록 스크립트

CLAUDE.md Rule 2(3개 이상 파일 변경 시 분해)에 따라 §2의 M1~M9로 분해해 순차 진행한다.

**[v0.2.0, plan-audit 1차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-028-review-1.md`, FAIL 0.55) 반영]** 오케스트레이터의 위임 프롬프트가 DB를 PostgreSQL이라고 잘못 전달했다 — 실제로는 **MySQL**(RDS)이다. 이 정정이 §1.1(인덱스), §1.6(차등 갱신), §1.3(페이싱), §4(위험표)를 전면적으로 바꾼다. 또한 감사가 지적한 4개 CRITICAL 결함(D1 업서트 미지원, D2 header-only 환불 무한증식, D3 위치 조용한 소거, D4 번들 고아 행 증폭)에 대한 구체적 구현 설계를 신설했다.

**[v0.3.0, plan-audit 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-028-review-2.md`, FAIL 0.68) 반영]** 인용 정확도는 다시 41/41이었으나 결함은 다시 "인용하지 않은 인접 코드"에서 나왔다(migration `0026`, `test_order_location.py:62`). 두 곳을 고쳤다: **§1.3**(N2 — `_build_fulfillment_location_data()`가 예외 없이 정상적으로 빈 위치를 반환하는 경로가 있음을 놓쳐 `raise_on_error`가 그 경로를 전혀 막지 못했다. 대상 주문/라인아이템의 기존 저장 위치를 미리 조회해 빈 결과를 병합·보존하는 로직을 추가했다), **§1.6**(N3 — header-only 환불의 NULL 키에는 유니크 제약이 없어 선존 중복이 가능한데, 차등 갱신이 기존 `.all().delete()`의 자가치유 속성을 잃어 `MultipleObjectsReturned`로 영구 실패할 수 있었다. upsert 전 중복 정리 단계를 추가했다). 번들 명분 삭제(N1)에 따라 R14를 갱신하고, 신규 위험 R16(N2)·R17(N3)을 추가했다. `spec.md` HISTORY v0.3.0에 전체 대응표가 있다.

**[v0.4.0, 사용자 확정 결정 반영]** 대상 연령 상한 60일 → 30일(재론 아님, 구현). §1.2의 `NOT_SHIPPED_QUALIFYING_WINDOW_DAYS`를 30으로 변경하고 `_qualifying_orders_queryset()`에 `days` 파라미터를 추가했다. §1.3의 `resync_order_sweep`에 `--days` CLI 인자(기본값 30, `backfill_missing_orders.py`의 `--created-since` 관례 미러링)를 신설해 REQ-RSW-035를 구현했다. R14/R15의 파생 수치를 재도출했다(2.8시간→2.14시간, 약 8회·일→약 11회·일). `spec.md` HISTORY v0.4.0에 전체 대응표가 있다.

**[v0.5.0, plan-audit v0.4.0 델타 감사(`.moai/reports/plan-audit/SPEC-ORDER-028-review-4.md`, PASS 0.78) 반영]** 발견된 결함 8건(D1~D8)은 전부 `spec.md`/`acceptance.md`의 근거 서술·문서 정합 문제였고 구현 산출물(코드 스케치, 배선 경로, 마일스톤)을 바꾸는 결함은 없었다 — `plan.md`는 코드 레벨 변경 없음. `--days`의 배선 경로(argparse → `options["days"]` → `days=` 파라미터 → `cutoff`, §1.2/§1.3)가 감사에서 끊김 없이 확인되었다. `spec.md` HISTORY v0.5.0에 전체 대응표가 있다.

---

## 1. 접근 개요

### 1.1 모델 + 마이그레이션 (`backend/order/models.py`, 신규 `0045`)

```python
# models.py, Order 클래스 (기존 필드들 뒤, cancelled_at/processed_at 부근)
last_resynced_at = models.DateTimeField(null=True, blank=True)
```

```python
# Order.Meta.indexes 리스트에 추가 (기존 :95-111)
# [v0.2.0 정정, 감사 D6] 단일 컬럼 인덱스가 아니라 복합 인덱스 —
# 아래 근거 참조.
models.Index(fields=["last_resynced_at", "shopify_created_at"], name="order_last_resynced_at_idx"),
```

```python
# backend/order/migrations/0045_order_last_resynced_at.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("order", "0044_lineitem_original_sku"),
    ]
    operations = [
        migrations.AddField(
            model_name="order",
            name="last_resynced_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["last_resynced_at", "shopify_created_at"],
                name="order_last_resynced_at_idx",
            ),
        ),
    ]
```

**[v0.2.0 전면 재작성, 감사 D6] 왜 복합 인덱스이고 왜 MySQL 기준으로 다시 썼는가**:

대상 판정 쿼리(§1.2)는 `shopify_created_at__gte`(자체 인덱스 존재, `models.py:99`) + `EXISTS` 서브쿼리 + `ORDER BY last_resynced_at`을 동시에 요구한다. MySQL(InnoDB)은 한 테이블 접근에 원칙적으로 인덱스 하나만 사용하므로(인덱스 병합 최적화가 있지만 이런 조합에는 거의 적용되지 않는다), `shopify_created_at` 인덱스를 쓰면 `ORDER BY last_resynced_at`이 filesort가 되고, `last_resynced_at` 인덱스를 쓰면 `shopify_created_at` 조건은 인덱스 스캔 중 행마다 재확인해야 한다.

**복합 인덱스 `(last_resynced_at, shopify_created_at)`을 선택한 이유**: 옵티마이저가 이 인덱스를 오름차순으로 순회하면, 각 인덱스 엔트리 안에 `shopify_created_at` 값이 함께 있어 그 조건을 **별도 테이블(heap) 조회 없이** 인덱스만으로 확인할 수 있다(MySQL의 "index condition pushdown"과 유사한 이득 — 정확한 실행계획 채택 여부는 버전/통계에 따라 달라질 수 있어 보장하지 않는다). `EXISTS` 서브쿼리(LineItem 조회)는 인덱스 선택과 무관하게 후보 행마다 평가해야 하는 비용이며 이 설계로 없앨 수 없다 — 이 인덱스가 줄이는 것은 `orders_order` 자체에 대한 불필요한 정렬/재조회 비용이다.

**[HARD] 이것은 옵티마이저의 선택이지 보장이 아니다.** DoD는 "인덱스가 존재한다"가 아니라 **Run 단계에서 `EXPLAIN`을 실행해 `Extra` 컬럼에 `Using filesort`가 없고 `key`가 `order_last_resynced_at_idx`인지 직접 확인**하는 것으로 강화한다:

```sql
EXPLAIN SELECT o.id FROM orders_order o
WHERE o.shopify_created_at >= '2026-06-20'
  AND EXISTS (SELECT 1 FROM orders_line_item li WHERE li.order_id = o.id AND li.logistics_status = 'not_shipped')
ORDER BY o.last_resynced_at ASC
LIMIT 40;
```

만약 `EXPLAIN`이 filesort를 보이면(예: 통계상 `shopify_created_at` 필터의 선택도가 더 높다고 판단해 그 인덱스를 우선한 경우), 다음 대안을 순서대로 검토한다: (a) `USE INDEX (order_last_resynced_at_idx)` 힌트로 강제, (b) 정렬을 애플리케이션 레벨에서 수행(대상 건수가 수천 단위로 작으므로 허용 가능할 수 있음). 이 판단은 Run 단계의 `EXPLAIN` 실측 이후로 미룬다 — 지금 단정하지 않는다.

**LineItem 쪽 인덱스는 신설하지 않는다.** `EXISTS(LineItem.objects.filter(order=OuterRef("pk"), logistics_status="not_shipped"))`의 `order_id`는 이미 기존 `unique_together`(`order`, `shopify_line_item_id`, `sku`, `models.py:253`)가 만드는 인덱스의 선두 컬럼이라, 주문당 평균 3.96개 라인아이템 중 그 부분집합만 인덱스 스캔 후 인메모리 필터링하면 되는 낮은 비용이다. Run 단계 `EXPLAIN`에서 이 서브쿼리가 실제로 비싸다고 나오면 `(order, logistics_status)` 복합 인덱스를 후속으로 추가한다(과도한 사전 최적화 방지, Enforce Simplicity).

### 1.2 대상 판정 쿼리 (`backend/order/shopify_orders.py`에 신규 헬퍼 `_qualifying_orders_queryset`)

```python
from datetime import timedelta
from django.db.models import Exists, F, OuterRef
from django.utils import timezone

# [v0.4.0, SPEC-ORDER-028 REQ-RSW-003(b)] 60 -> 30. User-reconfirmed
# decision, not up for re-litigation (spec.md §4 D7). REQ-RSW-035's --days
# CLI arg overrides this default per-invocation via the days= parameter
# below; the module constant is only the fallback when no override is given.
NOT_SHIPPED_QUALIFYING_WINDOW_DAYS = 30


def _qualifying_orders_queryset(store_types=None, days=NOT_SHIPPED_QUALIFYING_WINDOW_DAYS):
    """REQ-RSW-003/004/005/035: orders with >=1 not_shipped LineItem AND
    shopify_created_at within the last `days` days (default 30, see
    NOT_SHIPPED_QUALIFYING_WINDOW_DAYS), ordered so the least-recently-swept
    order comes first (NULL = never swept = oldest).

    Uses Exists() rather than a join+distinct to avoid row fanout — mirrors
    the existing trackable_qs/Exists pattern in
    _apply_logistics_display_filter (backend/order/views.py:203-223).

    Ordering: MySQL's ASC natively sorts NULL first (order_by_nulls_first=True,
    supports_order_by_nulls_modifier=False — verified against the installed
    Django 5.1.6 source this session). explicit nulls_first=True below
    compiles to byte-identical SQL on this DB (see spec.md Assumption A4a) —
    it is kept for defensive readability/portability only, NOT as the
    mechanism that makes NULL-first ordering work on THIS database.
    """
    from .models import LineItem, Order

    cutoff = timezone.now() - timedelta(days=days)
    not_shipped_exists = LineItem.objects.filter(
        order=OuterRef("pk"), logistics_status="not_shipped"
    )
    qs = Order.objects.filter(shopify_created_at__gte=cutoff).annotate(
        has_not_shipped=Exists(not_shipped_exists)
    ).filter(has_not_shipped=True)
    if store_types:
        qs = qs.filter(store_type__in=store_types)
    return qs.order_by(F("last_resynced_at").asc(nulls_first=True))
```

호출부(신규 커맨드)는 `_qualifying_orders_queryset(store_types, days=days)[:count]`로 슬라이스한다 — REQ-RSW-006/008의 N 상한을 SQL `LIMIT`으로, REQ-RSW-003/035의 D를 `days=`로 적용한다.

### 1.3 신규 관리 커맨드 `resync_order_sweep`

```python
# backend/order/management/commands/resync_order_sweep.py
"""Management command: resync_order_sweep.

Round-robin resync sweep for orders sync_store()'s incremental sync
structurally cannot keep current: fulfillment location (sync_store() reuses
the stored value for existing orders), close/cancel (sync_store() only reads
the status=open list feed).

Targets: orders with >=1 LineItem.logistics_status == "not_shipped" AND
shopify_created_at within the last --days days (default 30, SPEC-ORDER-028
v0.4.0 REQ-RSW-003/035 -- see _qualifying_orders_queryset). Processes the
--count (default 40) least-recently-swept qualifying orders per invocation,
oldest-last_resynced_at-first (NULL first).

Contract, mirrored from sync_orders.py: each order is attempted; the run
never aborts early on a single order's failure; last_resynced_at advances
for EVERY attempted order regardless of outcome (SPEC-ORDER-028 D1 — an
order that keeps failing must not permanently block the round robin); the
command exits non-zero (CommandError) if any order failed, so a scheduler
can alarm on it.

[SPEC-ORDER-028 REQ-RSW-030]: _build_fulfillment_location_data() can return
an empty location in TWO distinct situations, and this command must not
silently overwrite Order.location/LineItem.location in either one:
  (a) the fetch call raises an exception -- this command treats the whole
      order as failed. Uses _build_fulfillment_location_data(...,
      raise_on_error=True), an opt-in parameter that does not change the
      function's default (silent "", {}) contract relied on by
      sync_store()/sync_single_order_from_shopify()/backfill_missing_orders.
  (b) the fetch call SUCCEEDS but legitimately returns an empty location
      (Shopify's assigned_location.name has no underscore, or
      fulfillment_orders is an empty list -- see
      test_order_location.py:62-76, this is NOT an error). raise_on_error
      does nothing here since no exception is raised. This command merges
      the freshly-fetched value with the order's/line items' CURRENTLY
      STORED location, preferring the fresh value only when it is
      non-empty -- so an order is still counted as SUCCEEDED in this case
      (unlike (a)), just without clobbering a previously-known routing
      value with "".

Never advances StoreSyncWatermark — this command is not a substitute for
sync_store(), same contract as backfill_missing_orders.

Note: shares no explicit application-level lock with sync_store()'s 5-minute
schedule or the manual sync button, but CAN lock-wait against sync_store()'s
whole-store transaction.atomic() at the DB engine level if they touch the
same rows concurrently — see .moai/specs/SPEC-ORDER-028/spec.md §8 C8.

Usage:
    python manage.py resync_order_sweep
    python manage.py resync_order_sweep --count 20 --store gimssine
    python manage.py resync_order_sweep --days 90  # [v0.4.0, REQ-RSW-035]
        # one-off wider catch-up sweep (see spec.md §8 C13) -- does not
        # change the default (30) for future invocations
"""

import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from order.models import LineItem, Order, ShopifySkuSetMapping
from order.shopify_orders import (
    NOT_SHIPPED_QUALIFYING_WINDOW_DAYS,
    _build_fulfillment_location_data,
    _build_title_map,
    _get_with_headers,
    _qualifying_orders_queryset,
    _sync_single_order,
)

STORE_TYPES = ["gimssine", "etoile"]
DEFAULT_COUNT = 40
# [v0.2.0 정정, 감사 D14] 0.5s (이론적 예산 소진, 여유 0) 대신 이 저장소의
# 기존 동작 선례를 채택한다: repair_refunds.py:36-39, --sleep 기본값 0.3s,
# "respects the REST rate limit". 이 값은 속도 제한 보장이 아니라 최선
# 노력 부하 경감이다 — 진짜 안전망은 REQ-RSW-030(실패 시 위치 보존)이다.
API_CALL_MIN_INTERVAL_SECONDS = 0.3


def _load_batch_invariant_context():
    """REQ-RSW-021/023: compute bundle_map + title_map ONCE per sweep cycle.

    bundle_map is trivially batch-invariant (same query regardless of which
    orders are in the batch). title_map is made batch-invariant too by
    eagerly covering every member ISBN in the WHOLE ShopifySkuSetMapping
    table (not just the ones relevant to this batch) -- the table is small
    and itself batch-invariant, so this costs the same as the existing
    per-order query but is now paid once per cycle instead of once per
    order.
    """
    bundle_map: dict[str, list[str]] = {}
    for mapping in ShopifySkuSetMapping.objects.order_by("sort_order").values(
        "bundle_sku", "member_isbn"
    ):
        bundle_map.setdefault(mapping["bundle_sku"], []).append(mapping["member_isbn"])
    all_member_isbns = {isbn for isbns in bundle_map.values() for isbn in isbns}
    title_map = _build_title_map(list(all_member_isbns))
    return bundle_map, title_map


class Command(BaseCommand):
    help = (
        "Round-robin resync sweep for open orders sync_store() cannot keep "
        "current (fulfillment location, close/cancel). Processes the "
        "--count least-recently-swept qualifying orders per run; never "
        "advances StoreSyncWatermark."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
        parser.add_argument("--store", choices=[*STORE_TYPES, "all"], default="all")
        # [v0.4.0, REQ-RSW-035] Style mirrors backfill_missing_orders.py's
        # --created-since (backend/order/management/commands/
        # backfill_missing_orders.py:47-55): explicit default stated in
        # help text, no separate "resolve" helper needed since --days is
        # already a plain day-count int (unlike --created-since's ISO
        # date/datetime string).
        parser.add_argument(
            "--days",
            type=int,
            default=NOT_SHIPPED_QUALIFYING_WINDOW_DAYS,
            help=(
                "Age cap in days for the not_shipped target window "
                f"(default: {NOT_SHIPPED_QUALIFYING_WINDOW_DAYS}). Use a "
                "wider value for a one-off catch-up sweep without a code "
                "change (SPEC-ORDER-028 REQ-RSW-035, spec.md §8 C13)."
            ),
        )

    def _credentials(self, store_type):
        # Mirrors backfill_missing_orders.Command._credentials
        # (backend/order/management/commands/backfill_missing_orders.py:62-65)
        from django.conf import settings

        if store_type == "gimssine":
            return settings.SHOPIFY_GIMSSINE_DOMAIN, settings.SHOPIFY_GIMSSINE_TOKEN
        return settings.SHOPIFY_ETOILE_DOMAIN, settings.SHOPIFY_ETOILE_TOKEN

    def handle(self, *args, **options):
        count = options["count"]
        store = options["store"]
        days = options["days"]  # [v0.4.0, REQ-RSW-035]
        store_types = STORE_TYPES if store == "all" else [store]

        targets = list(
            # [N2/REQ-RSW-030(b)] "location" is included so order.location
            # (the currently stored value) is available below without a
            # per-order deferred-field query.
            _qualifying_orders_queryset(store_types, days=days).only(
                "id", "shopify_order_id", "store_type", "location"
            )[:count]
        )
        if not targets:
            self.stdout.write(self.style.SUCCESS("done - no qualifying orders"))
            return

        bundle_map, title_map = _load_batch_invariant_context()

        succeeded = 0
        failed = []
        last_call_at = None

        def _pace():
            nonlocal last_call_at
            now = time.monotonic()
            if last_call_at is not None:
                elapsed = now - last_call_at
                if elapsed < API_CALL_MIN_INTERVAL_SECONDS:
                    time.sleep(API_CALL_MIN_INTERVAL_SECONDS - elapsed)
            last_call_at = time.monotonic()

        for order in targets:
            label = f"{order.store_type}#{order.shopify_order_id}"
            try:
                domain, token = self._credentials(order.store_type)

                _pace()
                body, _ = _get_with_headers(domain, token, f"orders/{order.shopify_order_id}.json")
                order_data = body["order"]

                # [REQ-RSW-030(a)] raise_on_error=True: unlike every other
                # existing caller of this function, a failure here must NOT
                # be silently swallowed into ("", {}) and written as an
                # empty location — it must abort this order's processing so
                # the except block below marks it failed and the stored
                # location is left untouched.
                _pace()
                fresh_location, fresh_line_item_map = _build_fulfillment_location_data(
                    domain, token, order.shopify_order_id, raise_on_error=True
                )

                # [N2/REQ-RSW-030(b)] The call above can succeed with NO
                # exception and still return an empty location (no
                # underscore in Shopify's assigned_location.name, or zero
                # fulfillment_orders — test_order_location.py:62-76 pins
                # this as intended, non-error behaviour). raise_on_error
                # does not help here since nothing raised. Without this
                # merge step, _sync_single_order()'s unconditional
                # "location": location_code default (shopify_orders.py:165,
                # :242) would silently wipe a previously-known NJ/CA routing
                # value with "" — this is the SAME incident D3 fixed for
                # the exception path, reproduced through the success path.
                # Fix: fall back to the CURRENTLY STORED value whenever the
                # freshly-fetched value is empty, at BOTH order and
                # line-item granularity. A brand-new line item Shopify has
                # never reported before has no "existing" value to fall
                # back to, so it correctly resolves to "" either way (not a
                # regression — matches first-sync behaviour elsewhere).
                order_location = fresh_location or order.location
                existing_line_item_locations = dict(
                    LineItem.objects.filter(order=order).values_list(
                        "shopify_line_item_id", "location"
                    )
                )
                all_line_item_ids = set(existing_line_item_locations) | set(
                    fresh_line_item_map or {}
                )
                line_item_map = {
                    shopify_line_item_id: (
                        (fresh_line_item_map or {}).get(shopify_line_item_id, "")
                        or existing_line_item_locations.get(shopify_line_item_id, "")
                    )
                    for shopify_line_item_id in all_line_item_ids
                }

                with transaction.atomic():
                    _sync_single_order(
                        order_data,
                        order.store_type,
                        location_code=order_location,
                        line_item_location_map=line_item_map,
                        bundle_map=bundle_map,
                        title_map=title_map,
                    )
                succeeded += 1
            except Exception as exc:  # noqa: BLE001 - one bad order must not stop the sweep
                self.stderr.write(self.style.ERROR(f"  FAILED {label}: {exc}"))
                failed.append(label)
            finally:
                # REQ-RSW-011 / D1: advance regardless of outcome so a
                # repeatedly-failing order cannot permanently block the
                # round robin.
                Order.objects.filter(pk=order.pk).update(last_resynced_at=timezone.now())

        summary = f"done - attempted={len(targets)}, succeeded={succeeded}, failed={len(failed)}"
        if failed:
            self.stdout.write(self.style.ERROR(summary))
            raise CommandError(f"resync_order_sweep failed for: {', '.join(failed)}")
        self.stdout.write(self.style.SUCCESS(summary))
```

**핵심 설계 판단**:

- **(A) `last_resynced_at` 갱신은 `finally` 블록.** 성공/실패/위치조회실패 세 경로 모두에서 정확히 한 번 실행된다(D1). 이 `update()`는 그 주문 자신의 `transaction.atomic()` 블록 **밖**에서 실행되므로, `_sync_single_order()`가 예외로 롤백되어도 `last_resynced_at` 갱신 자체는 별도의 (묵시적) 트랜잭션으로 커밋된다.
- **(B) `raise_on_error=True`가 REQ-RSW-030(a)를 해결하는 지점.** `_build_fulfillment_location_data()`가 예외로 실패하면, 그 예외는 바깥의 일반 `except Exception`에 걸려 `_sync_single_order()` 호출 자체에 도달하지 않는다 — 즉 예외 경로에서는 `location_code=""`가 절대 쓰이지 않는다. 별도의 "위치 실패 전용" 분기가 필요 없다(기존 per-order 실패 처리 메커니즘을 그대로 재사용).
- **(B') 값-병합이 REQ-RSW-030(b)를 해결하는 지점 `[v0.3.0 신규, 감사 N2]`.** (B)는 **예외** 경로만 막는다 — `_build_fulfillment_location_data()`가 예외 없이 정상적으로 빈 값을 반환하는 경로(언더스코어 없는 위치 이름, 빈 `fulfillment_orders`)는 `raise_on_error`가 전혀 개입하지 않는다. 그래서 `_sync_single_order()` 호출 **직전**에, 새로 조회한 값이 빈 경우에만 `order`/`LineItem`의 기존 저장값으로 대체하는 병합 단계를 추가했다 — `_sync_single_order()` 자신의 "받은 값을 무조건 쓴다"는 계약(`test_order_location.py:160`/`:187`이 다른 3개 호출부를 위해 고정)은 건드리지 않고, 스위프가 그 함수에 **무엇을 전달할지**만 스스로 결정한다. 이 경로는 실패가 아니므로 `except`에 걸리지 않고 `succeeded`에 정상 집계된다.
- **(C) 페이싱은 주문 조회 호출과 fulfillment 조회 호출 모두에 적용.** 사이클당 API 호출은 최대 2×N번 — N=40이면 최대 80번, 0.3초 간격이면 최소 약 24초의 API 시간이 걸린다(§4 위험 R6 재산정).
- **(D) `bundle_map`/`title_map`은 루프 진입 전 정확히 1회 계산.** 대상이 0건이면 그 계산조차 건너뛴다.
- **(E) Shopify 호출 2번은 트랜잭션 밖에서 수행한다.** DB 트랜잭션이 네트워크 왕복 시간만큼 열려 있는 것을 피한다 — §8 C8(락 경합)의 노출 시간을 최소화하는 효과도 있다.
- **(F) 병합에 필요한 `LineItem` 조회는 사이클마다가 아니라 주문마다 1회 추가된다 `[v0.3.0 신규]`.** `existing_line_item_locations`는 이번에 처리 중인 주문 하나의 라인아이템만 조회하므로(호이스팅 대상이 아님 — 배치 불변이 아니라 주문마다 다른 데이터다), 이 SPEC의 기존 "주문당 약 15쿼리" 예산에 쿼리 1개가 추가된다. 사소하지만 정직하게 기록한다(§4 R16).

### 1.4 `_build_fulfillment_location_data()` 확장 — 실패 명시적 전파 `[MODIFY, 신규]`

```python
# shopify_orders.py:72, 기존 시그니처
def _build_fulfillment_location_data(domain, token, order_id):
    """Return (order_location, line_item_location_map) from fulfillment_orders API.
    ...
    Returns ("", {}) on any error.
    """
    try:
        body, _ = _get_with_headers(domain, token, f"orders/{order_id}/fulfillment_orders.json")
        ...
        return "/".join(seen), line_item_map
    except Exception:
        return "", {}
```

를

```python
def _build_fulfillment_location_data(domain, token, order_id, raise_on_error=False):
    """Return (order_location, line_item_location_map) from fulfillment_orders API.
    ...
    Returns ("", {}) on any error, UNLESS raise_on_error=True (default False,
    preserves the exact existing contract for all 3 existing callers —
    SPEC-ORDER-028 REQ-RSW-030(a)), in which case the exception propagates
    instead of being swallowed.

    NOTE [v0.3.0, N2]: this flag ONLY affects the exception path. A
    successful call can ALSO legitimately return ("", {}) or a partial
    empty map when Shopify's own data has no usable location (see
    test_order_location.py:62-76) — raise_on_error does nothing for that
    case, it never raises there in the first place. Callers that need to
    avoid clobbering a previously-known location on THIS path must do so
    themselves by inspecting the returned value (see resync_order_sweep's
    merge step in §1.3) — this function's return contract for the success
    path is otherwise unchanged for all callers.
    """
    try:
        body, _ = _get_with_headers(domain, token, f"orders/{order_id}/fulfillment_orders.json")
        ...
        return "/".join(seen), line_item_map
    except Exception:
        if raise_on_error:
            raise
        return "", {}
```

**금지 사항**: 기존 3개 호출부(`sync_store()`, `sync_single_order_from_shopify()`, `backfill_missing_orders`)의 호출 지점을 수정하지 않는다 — 전부 `raise_on_error`를 생략하므로 기본값 `False`가 적용되어 `test_order_location.py:79-88`의 기존 계약이 그대로 유지된다(회귀 없음, REQ-RSW-030(a)). **정상-빈값 경로(REQ-RSW-030(b))의 처리는 이 함수 내부에 어떤 코드도 추가하지 않는다** — §1.3의 스위프 자신의 병합 로직만으로 해결한다(이 함수의 반환 계약은 성공 경로에서 완전히 무변경).

### 1.5 `_sync_single_order()` 리팩터 — 배치 불변 컨텍스트 파라미터화

```python
# shopify_orders.py:104, 기존 시그니처
def _sync_single_order(order_data, store_type, location_code="", line_item_location_map=None):
    ...
```

를

```python
def _sync_single_order(
    order_data,
    store_type,
    location_code="",
    line_item_location_map=None,
    bundle_map: dict[str, list[str]] | None = None,
    title_map: dict[str, str | None] | None = None,
):
    ...
    # 기존 :191-196 블록을 조건부로 감싼다
    if bundle_map is None:
        bundle_map = {}
        bundle_mapping_rows = ShopifySkuSetMapping.objects.order_by("sort_order").values(
            "bundle_sku", "member_isbn"
        )
        for mapping in bundle_mapping_rows:
            bundle_map.setdefault(mapping["bundle_sku"], []).append(mapping["member_isbn"])

    # 기존 :198-207 블록을 조건부로 감싼다
    if title_map is None:
        relevant_member_isbns: set[str] = set()
        for li in order_data.get("line_items", []):
            member_isbns = bundle_map.get(li.get("sku"))
            if member_isbns:
                relevant_member_isbns.update(member_isbns)
        title_map = _build_title_map(list(relevant_member_isbns))
    # 이하 :209~ 부터는 무변경 — title_map.get(member_isbn) 등 기존 참조 그대로
```

**금지 사항**:
- `is None` 체크를 `not bundle_map`/`not title_map`(falsy 체크)으로 바꾸지 않는다 — 호출부가 의도적으로 빈 `{}`를 전달한 경우와 "전달하지 않음"을 구분해야 한다.
- `sync_single_order_from_shopify()`(`:334-352`)와 `backfill_missing_orders.py`(`:138-143`의 `_sync_single_order(...)` 호출)는 **호출부를 수정하지 않는다** — 두 곳 모두 신규 파라미터를 전달하지 않으므로 자동으로 기존 동작(내부 계산)을 유지한다(REQ-RSW-022, 회귀 없음). **[v0.2.0 재확인, 감사 D7] 이 "무변경"은 배치 컨텍스트 파라미터에만 해당한다 — §1.6의 환불/배송라인 리팩터는 이 두 호출부에도 적용된다.**

### 1.6 `_sync_single_order()` 리팩터 — 환불/배송라인 MySQL 호환 차등 갱신 `[v0.2.0 전면 재작성]`

**[감사 D1] MySQL은 `supports_update_conflicts_with_target=False`다 — `bulk_create(update_conflicts=True, unique_fields=[...])`는 `unique_fields`를 넘기는 순간 `django.db.utils.NotSupportedError`를 던진다(이 세션에서 Django 5.1.6 소스 `django/db/models/query.py:727-728`을 직접 확인).** MySQL에서 유효한 형태는 `unique_fields`를 **생략**하는 것뿐이다 — `bulk_create(rows, update_conflicts=True, update_fields=[...])`는 MySQL의 `INSERT ... ON DUPLICATE KEY UPDATE`로 컴파일되며, 어떤 유니크 키가 위반되었는지는 DB가 알아서 판별한다(모델에 유니크 제약이 하나뿐이므로 모호하지 않다).

**[감사 D2] 그러나 이 형태만으로는 header-only 환불 행(`line_item_id IS NULL`)을 처리할 수 없다.** SQL 표준상 유니크 제약의 충돌 판정은 NULL을 다른 어떤 값과도(자기 자신과도) 같다고 보지 않는다 — MySQL도 예외가 아니다. 즉 `line_item_id=NULL`인 두 행은 `ON DUPLICATE KEY UPDATE` 관점에서 절대 "충돌"하지 않으므로, 매 스위프 사이클마다 새 행이 계속 INSERT된다. 이 문제는 **upsert 메커니즘 자체의 한계**이며 인자 조정으로 해결되지 않는다 — NULL `line_item_id` 행은 처음부터 이 경로에서 제외하고 별도로 처리해야 한다.

```python
# 기존 :291-304 (ShippingLine) 대체 — shopify_shipping_line_id는 NULL이 아니므로 문제 없음
incoming_shipping_lines = order_data.get("shipping_lines", [])
incoming_shipping_line_ids = {sl["id"] for sl in incoming_shipping_lines}
order_obj.shipping_lines.exclude(
    shopify_shipping_line_id__in=incoming_shipping_line_ids
).delete()
if incoming_shipping_lines:
    ShippingLine.objects.bulk_create(
        [
            ShippingLine(
                order=order_obj,
                shopify_shipping_line_id=sl["id"],
                title=sl.get("title"),
                code=sl.get("code"),
                price=_decimal_or_none(sl.get("price")),
                source=sl.get("source"),
            )
            for sl in incoming_shipping_lines
        ],
        update_conflicts=True,
        # [D1] unique_fields를 지정하지 않는다 — MySQL은
        # supports_update_conflicts_with_target=False라 지정하면 즉시
        # NotSupportedError. ON DUPLICATE KEY UPDATE가 (order,
        # shopify_shipping_line_id) 유니크 제약(models.py:320) 위반을
        # 알아서 판별한다.
        update_fields=["title", "code", "price", "source"],
    )
```

```python
# 기존 :306-329 (Refund) 대체 — line_item_id가 NULL일 수 있으므로 2개 경로로 분리
incoming_refund_keys = set()
non_null_refund_rows = []
null_line_item_refunds = []  # [D2] header-only rows — handled separately below
for refund_data in order_data.get("refunds", []):
    refund_line_items = refund_data.get("refund_line_items", []) or [{}]
    for rli in refund_line_items:
        line_item_id = rli.get("line_item_id")
        incoming_refund_keys.add((refund_data["id"], line_item_id))
        refund_kwargs = {
            "note": refund_data.get("note"),
            "shopify_created_at": refund_data.get("created_at"),
            "quantity": rli.get("quantity"),
            "subtotal": _decimal_or_none(rli.get("subtotal")),
            "total_tax": _decimal_or_none(rli.get("total_tax")),
        }
        if line_item_id is None:
            null_line_item_refunds.append((refund_data["id"], refund_kwargs))
        else:
            non_null_refund_rows.append(
                Refund(order=order_obj, shopify_refund_id=refund_data["id"],
                       line_item_id=line_item_id, **refund_kwargs)
            )

# 차등 삭제: 이번 페이로드에 없는 (shopify_refund_id, line_item_id) 조합만.
# Python 튜플 비교이므로 (refund_id, None) 키도 정확히 매치된다 — 삭제
# 판정 자체는 NULL 문제와 무관하다(문제는 upsert 매칭에만 있다).
stale_refund_pks = [
    row["id"]
    for row in order_obj.refunds.values("id", "shopify_refund_id", "line_item_id")
    if (row["shopify_refund_id"], row["line_item_id"]) not in incoming_refund_keys
]
if stale_refund_pks:
    Refund.objects.filter(pk__in=stale_refund_pks).delete()

if non_null_refund_rows:
    Refund.objects.bulk_create(
        non_null_refund_rows,
        update_conflicts=True,
        # [D1] unique_fields 없음 — (order, shopify_refund_id, line_item_id)
        # 위반은 이 행들 전부 line_item_id가 non-null이므로 정상적으로
        # 판별된다.
        update_fields=["note", "shopify_created_at", "quantity", "subtotal", "total_tax"],
    )

# [D2/REQ-RSW-029] header-only(line_item_id IS NULL) 행은 upsert 경로를
# 아예 타지 않는다 — Django의 update_or_create가 생성하는 조회는
# `line_item_id=None`을 IS NULL로 변환하므로(원래 코드도 이 방식이었다),
# 정확히 1행만 매치·갱신된다. 이 목록은 통상 0~1건이라 N+1 우려가 없다.
for shopify_refund_id, refund_kwargs in null_line_item_refunds:
    # [N3/REQ-RSW-029 자가치유] line_item_id에는 유니크 제약이 없으므로
    # (가정 A8) 이 조회 이전에 이미 (order, shopify_refund_id, NULL) 행이
    # 2건 이상 존재할 수 있다 — 이력 데이터, 또는 sync_store()/수동
    # 재동기화와의 동시 실행 경합(§8 C8)으로. 옛 코드는 이 사이클마다
    # .all().delete()로 이런 중복을 공짜로 정리했지만, 이 차등 설계는
    # 그 삭제를 하지 않으므로 upsert 전에 직접 정리해야 한다 — 정리하지
    # 않으면 update_or_create 내부의 .get()이 MultipleObjectsReturned를
    # 던져 이 주문이 매 랩마다 영구적으로 실패한다.
    duplicate_rows = list(
        Refund.objects.filter(
            order=order_obj, shopify_refund_id=shopify_refund_id, line_item_id__isnull=True
        ).order_by("pk")
    )
    if len(duplicate_rows) > 1:
        Refund.objects.filter(pk__in=[r.pk for r in duplicate_rows[1:]]).delete()
    Refund.objects.update_or_create(
        order=order_obj,
        shopify_refund_id=shopify_refund_id,
        line_item_id=None,
        defaults=refund_kwargs,
    )
```

**핵심 설계 판단**:

- **(A) `unique_fields`는 지정하지 않는다.** D1의 직접 해결책이다 — MySQL 기능 플래그(`supports_update_conflicts_with_target=False`)가 이 프로젝트의 유일하게 유효한 형태를 강제한다.
- **(B) header-only 환불은 애초에 bulk upsert 목록에 들어가지 않는다.** `line_item_id is None` 분기에서 별도 리스트로 빼내어 `update_or_create`(Django ORM이 `line_item_id=None`을 `IS NULL`로 정확히 변환)로 처리한다 — 원래 코드(`.all().delete()` 이전)가 쓰던 것과 동일한 조회 방식이라 동작이 검증되어 있다.
- **(B') upsert 직전 중복 정리로 자가치유를 복원한다 `[v0.3.0 신규, 감사 N3]`.** `line_item_id`에는 유니크 제약이 없어(가정 A8) 이미 중복된 (order, refund_id, NULL) 행이 존재할 수 있다 — 그 상태에서 `update_or_create`만 실행하면 내부 `.get()`이 `MultipleObjectsReturned`를 던져 그 주문이 영구 실패한다. `order_by("pk")`로 정렬해 첫 행만 남기고 나머지를 삭제한 뒤 upsert하면, 옛 `.all().delete()`가 매 동기화마다 공짜로 제공하던 자가치유 속성이 복원된다 — 중복이 없는 정상 상태에서는 이 조회가 항상 0~1건을 반환하므로 추가 비용은 무시할 만하다.
- **(C) 삭제는 여전히 필요하지만 범위가 좁다.** "이번 페이로드에 없는 행"만 삭제한다 — Python의 튜플 비교(`(refund_id, None) not in incoming_refund_keys`)는 NULL 문제와 무관하게 정확히 동작한다(SQL 유니크 제약의 NULL 비교 규칙은 upsert/충돌 판정에만 영향을 미치고, 애플리케이션 레벨 Python 집합 연산에는 영향을 주지 않는다).
- **(D) `ShippingLine`은 NULL 문제가 없다.** `shopify_shipping_line_id`는 `models.BigIntegerField()`(nullable 아님, `models.py:312`)이므로 단순 bulk upsert(unique_fields 없이)만으로 충분하다.

### 1.7 스케줄러 등록 (`scripts/resync_order_sweep.bat`)

`scripts/sync_orders.bat`을 그대로 미러링한다(작업 디렉터리 고정, `PYTHONIOENCODING=utf-8`, 로그 파일, 종료 코드 전파):

```bat
@echo off
REM Scheduled order resync sweep (see .moai/project/scheduled-jobs.md).
REM Registered in Windows Task Scheduler; do not run two copies at once --
REM the task must be configured with "Do not start a new instance".
setlocal

cd /d C:\app\scm_v2\backend || exit /b 1
set PYTHONIOENCODING=utf-8

if not exist "C:\app\scm_v2\logs" mkdir "C:\app\scm_v2\logs"

echo [%DATE% %TIME%] resync_order_sweep start >> "C:\app\scm_v2\logs\resync_order_sweep.log"
"C:\Users\ggajo\AppData\Local\Programs\Python\Python312\python.exe" manage.py resync_order_sweep >> "C:\app\scm_v2\logs\resync_order_sweep.log" 2>&1
set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] resync_order_sweep exit=%RC% >> "C:\app\scm_v2\logs\resync_order_sweep.log"

exit /b %RC%
```

작업 스케줄러 등록은 `sync_orders`와 동일한 5분 주기 반복 트리거를 사용하되(§4 위험 R6에서 재산정한 대로 사이클당 API 시간은 약 24초, DB 쓰기 시간은 약 80초 추가 — 합계 약 2~3분, 5분 창 안에서의 여유는 v0.1.0이 주장한 것보다 얇다), **별도의 태스크 이름**으로 등록한다(`scm_v2 resync_order_sweep`). `.moai/project/scheduled-jobs.md`에 이 신규 작업을 §1 표와 §3 등록 절차에 추가하는 것을 `/moai sync` 단계 작업으로 권고한다.

### 1.8 UI 고려사항 (권고, 결정하지 않음)

`OrderSyncStatusView`(`views.py:99-156`)는 현재 `StoreSyncWatermark.last_run_at`만 노출한다. 스위프 진행 상황을 같은 엔드포인트에 추가할지 여부는 이 SPEC에서 결정하지 않는다(`spec.md` §8 C6, 구 REQ-RSW-028) — 필요해지면 `Order.last_resynced_at`의 최솟값/최댓값과 대상 건수를 5분 주기로 캐싱해 노출하는 별도 후속 SPEC으로 다룬다.

---

## 2. 마일스톤 (우선순위 순, 시간 예측 없음)

### M1 (Priority High) — 모델 + 마이그레이션

1. `backend/order/models.py` `[MODIFY]` — `Order`에 `last_resynced_at` 필드 + `Meta.indexes`에 **복합** 인덱스 추가(§1.1).
2. `python manage.py makemigrations order` 실행 후 생성된 마이그레이션이 §1.1의 설계와 일치하는지 확인.
3. `python manage.py migrate` 로컬(MySQL RDS) 실행 확인.

완료 조건: 마이그레이션 적용 성공, `git status backend/order/migrations/`에 신규 파일 1건, `EXPLAIN`으로 이 인덱스가 후보로 존재함을 확인(M2에서 실제 쿼리로 재확인).

### M2 (Priority High) — 대상 판정 쿼리 + 단위 테스트: RED → GREEN

1. `backend/order/tests/test_spec_028.py` `[NEW]` 작성 — AC-RSW-001~006 대응.
2. `shopify_orders.py` `[MODIFY]` — `_qualifying_orders_queryset()` 신규 헬퍼(§1.2) 추가.
3. RED 확인 후 GREEN.
4. **[v0.2.0 신규]** `EXPLAIN`을 실제 쿼리에 실행해 filesort 여부 확인(§1.1 DoD).

금지 사항: `.distinct()`로 fanout을 우회하는 구현 금지(REQ-RSW-004) — 존재 서브쿼리만 사용.

완료 조건: AC-RSW-001 ~ AC-RSW-006 통과 + `EXPLAIN` 결과 기록.

### M3 (Priority High) — `_sync_single_order()` 리팩터: 배치 불변 컨텍스트

1. `shopify_orders.py` `[MODIFY]` — 시그니처 확장(§1.5).
2. 기존 회귀 스위트 재실행: `backend/order/tests/test_shopify_orders.py`, `test_order_resync.py`, `test_backfill_missing_orders_command.py`, `test_sync_orders_command.py` — 전부 무수정 통과 확인(REQ-RSW-022).
3. `test_spec_028.py`에 AC-RSW-024(호이스팅 쿼리 횟수), AC-RSW-025(단건 호출부 회귀) 추가.

금지 사항: `sync_single_order_from_shopify()`, `sync_store()`, `backfill_missing_orders.py`의 `_sync_single_order(...)` 호출부에 신규 배치 컨텍스트 파라미터 전달 금지(설계 결정 D2, Exclusions #8).

완료 조건: AC-RSW-024, AC-RSW-025 통과 + 기존 4개 테스트 파일 전부 무수정 통과.

### M4 (Priority High) — `_build_fulfillment_location_data()` 확장 + 위치 병합 (REQ-RSW-030)

1. `shopify_orders.py` `[MODIFY]` — `raise_on_error` 파라미터 추가(§1.4) — REQ-RSW-030(a), 예외 경로.
2. `resync_order_sweep.py` `[NEW/MODIFY]` — 위치 병합 로직 추가(§1.3 (B')) — REQ-RSW-030(b), 정상-빈값 경로. `.only()`에 `"location"` 포함, `LineItem.objects.filter(order=order).values_list(...)` 조회, 기존 값으로 폴백하는 병합 로직.
3. 기존 회귀: `test_order_location.py` 전부 무수정 통과 확인(기본값 `False`로 계약 무변경, 함수 자체는 성공 경로에서 완전히 무변경).
4. `test_spec_028.py`에 (a) `raise_on_error=True`일 때 예외가 실제로 전파되는지 확인하는 단위 테스트, (b) AC-RSW-014b(예외 경로), (c) AC-RSW-030(정상-빈값 경로, 신규) 추가.

금지 사항: `_build_fulfillment_location_data()` 또는 `_sync_single_order()`의 성공 경로 반환/쓰기 계약을 변경하지 않는다 — 병합은 오직 스위프 자신의 호출 지점에서만 이루어진다.

완료 조건: `test_order_location.py` 무수정 통과 + AC-RSW-014b, AC-RSW-030 통과.

### M5 (Priority High) — `_sync_single_order()` 리팩터: 환불/배송라인 MySQL 호환 차등 갱신

1. `shopify_orders.py` `[MODIFY]` — §1.6의 MySQL 호환 upsert(단, `unique_fields` 없음) + header-only 환불 분리 처리 + upsert 전 중복 정리(자가치유, §1.6 (B'))로 교체.
2. `test_spec_028.py`에 AC-RSW-021~023, AC-RSW-029(header-only 무한증식 방지), AC-RSW-029b(선존 중복 자가치유, 신규) 추가.
3. 기존 회귀: `test_shopify_orders.py`(특히 `:765` 헤더 전용 환불 테스트, `:665` 멱등성 테스트)와 `test_order_resync.py` 전부 무수정 통과 확인 — 최종 저장 상태가 delete-and-recreate 방식과 동일해야 한다(REQ-RSW-026).
4. MySQL RDS(로컬 pytest와 운영이 동일 인스턴스를 바라봄, `backend/.env`)에서 `bulk_create(update_conflicts=True)`(unique_fields 없이)가 실제로 `ON DUPLICATE KEY UPDATE`로 실행되는지 최소 1건 수동 검증.

금지 사항:
- `bulk_create(..., unique_fields=[...])` 형태를 다시 도입하지 않는다 — MySQL에서 `NotSupportedError`(D1).
- `line_item_id IS NULL`인 환불 행을 bulk upsert 목록에 섞지 않는다(D2) — 반드시 `update_or_create`로 분리.
- `.all().delete()`를 완전히 제거하지 말 것 — 차등 삭제(stale 행만)는 여전히 필요하다.
- header-only 환불의 upsert 전 중복 정리 단계를 생략하지 않는다(N3) — 생략하면 선존 중복이나 동시 실행 경합 상태에서 그 주문이 영구 실패한다.

완료 조건: AC-RSW-021 ~ AC-RSW-023, AC-RSW-029, AC-RSW-029b 통과 + 기존 refund/shipping_line 테스트 무수정 통과 + MySQL 수동 검증 기록.

### M6 (Priority High) — 신규 관리 커맨드 `resync_order_sweep`

1. `backend/order/management/commands/resync_order_sweep.py` `[NEW]` 작성(§1.3, 위치 병합 로직 포함).
2. `test_spec_028.py`에 AC-RSW-007~020, AC-RSW-026, AC-RSW-033, AC-RSW-034 추가 — `test_sync_orders_command.py`/`test_backfill_missing_orders_command.py`의 `call_command` + `unittest.mock.patch` 관례를 재사용한다. AC-RSW-007b(`--count` 생략 시 기본값 40)와 AC-RSW-035/AC-RSW-035b(`--days` 명시적 override / 생략 시 기본값 30, v0.4.0 신규, REQ-RSW-035)도 여기서 함께 작성한다.
3. Shopify API 호출은 `_get_with_headers`/`_build_fulfillment_location_data`를 모킹해 실제 네트워크 호출 없이 검증한다. `_build_fulfillment_location_data`를 `side_effect=Exception(...)`으로 모킹해 REQ-RSW-030(a)를 검증하는 AC-RSW-014b를, `return_value=("", {...})`(정상-빈값)으로 모킹해 REQ-RSW-030(b)를 검증하는 AC-RSW-030을 포함한다.

금지 사항: `StoreSyncWatermark`를 읽거나 쓰는 코드를 이 커맨드에 추가하지 않는다(REQ-RSW-016) — import조차 하지 않는 것으로 이 불변식을 코드 레벨에서 강제한다.

완료 조건: AC-RSW-007, AC-RSW-007b, AC-RSW-008 ~ AC-RSW-020, AC-RSW-026, AC-RSW-030, AC-RSW-033, AC-RSW-034 전부 통과.

### M7 (Priority Medium) — 스케줄러 스크립트

1. `scripts/resync_order_sweep.bat` `[NEW]`(§1.7).
2. 로컬에서 수동 실행해 로그 파일(`logs/resync_order_sweep.log`)이 정상 생성되는지 확인.

완료 조건: `.bat` 파일 존재 + 수동 실행 1회 성공(로그 확인).

### M8 (Priority Medium) — @MX 태그

§5 실행.

### M9 (Priority Low) — 문서 갱신 권고 (이 SPEC의 필수 산출물 아님)

`.moai/project/scheduled-jobs.md`에 `resync_order_sweep` 작업을 §1 표와 §3 등록 절차에 추가하는 것을 `/moai sync` 단계 작업으로 권고한다.

---

## 3. 영향 파일 ([DELTA] 마커)

| 마커 | 파일 | 변경 내용 |
|------|------|-----------|
| **[MODIFY]** | `backend/order/models.py` | `Order`에 `last_resynced_at` 필드 + 복합 인덱스 |
| **[NEW]** | `backend/order/migrations/0045_order_last_resynced_at.py` | 신규 마이그레이션 |
| **[MODIFY]** | `backend/order/shopify_orders.py` | `_qualifying_orders_queryset()` 신설, `_build_fulfillment_location_data()`에 `raise_on_error` 추가, `_sync_single_order()` 시그니처 확장 + refund/shipping_line MySQL 호환 차등 갱신(header-only 환불 분리 처리 포함) |
| **[NEW]** | `backend/order/management/commands/resync_order_sweep.py` | 신규 관리 커맨드 |
| **[NEW]** | `backend/order/tests/test_spec_028.py` | AC-RSW-001~035 범위 내 35개 대응 테스트(결번 안내는 `acceptance.md` §0 참고) |
| **[NEW]** | `scripts/resync_order_sweep.bat` | 스케줄러 등록용 래퍼 |
| **[EXISTING]** | `scripts/run_hidden.vbs` | **무변경** — 기존 창 숨김 스크립트 재사용 |
| **[EXISTING]** | `backend/order/shopify_orders.py`의 `sync_store()`(`:355-461`) | **소스 코드 무변경. 단, `_sync_single_order()`의 환불/배송라인 쓰기 방식 변경(§1.6)이 이 호출부의 런타임 동작에도 적용된다(감사 D7, spec.md §8 C7) — 회귀 스위트로 반드시 확인** |
| **[EXISTING]** | `backend/order/views.py`(`OrderSyncView`/`OrderResyncView`/`OrderSyncStatusView`) | **소스 코드 무변경.** `OrderResyncView` → `sync_single_order_from_shopify()`도 §1.6 변경의 영향을 받는다(같은 이유) |
| **[EXISTING]** | `backend/order/management/commands/backfill_missing_orders.py` | **소스 코드 무변경.** 같은 이유로 §1.6 변경의 영향을 받는다 — `test_backfill_missing_orders_command.py` 무수정 통과로 확인 |
| **[EXISTING]** | `backend/order/purchase_order_views.py`의 `_process_warehouse_receipt_rows`(`:2392-2579`) | **무변경** |

변경/신규 파일은 **6개**다(모델 1 + 마이그레이션 1 + 동기화 모듈 1 + 커맨드 1 + 테스트 1 + 스크립트 1). CLAUDE.md Rule 2에 따라 §2의 M1~M7로 분해해 순차 진행한다(M8/M9는 부가 작업).

---

## 4. 위험과 대응

| ID | 위험 | 대응 |
|----|------|------|
| R1 | 대상 판정 쿼리가 `.distinct()`에 의존해 JOIN fanout을 일으키고, `[:count]` 슬라이싱이 같은 주문을 중복 카운트한다 | AC-RSW-005가 3개 라인아이템(그중 1개 not_shipped)인 주문을 픽스처로 써서 결과 집합에 정확히 1개의 Order만 있는지 단정한다. §2 M2 "금지 사항"에 `.distinct()` 사용 금지 명시 |
| R2 `[v0.3.0 보강, 감사 N5]` | `last_resynced_at` 정렬이 실제로는 NULL을 뒤로 보낸다(방향 반전) — 또는 `order_by()` 절 자체가 통째로 삭제된다(정렬 제거) | AC-RSW-006이 **명령 실행 결과**(어떤 주문이 처리되었는가)로 직접 검증한다(감사 D5 반영 — SQL 파라미터 존재만으로는 이 DB에서 판별되지 않으므로 채택하지 않음). 픽스처 생성 순서를 기대 처리 순서(E→F→G의 역순, 즉 실제 생성은 E→F→G)와 의도적으로 불일치시켜, 정렬 제거 변이가 "우연히 생성 순서 = 기대 순서"로 위장 통과하지 못하게 한다(N5) |
| R3 | `resync_order_sweep`가 `sync_store()`의 위치 재사용 최적화(`:420-428`)를 실수로 복사해 온다 — "기존 주문이면 API 호출 생략" 분기를 넣는 것은 이 SPEC의 존재 이유(gap 1)를 무효화한다 | AC-RSW-014가 로컬에 NJ로 저장된 주문이 Shopify에서 CA로 바뀐 픽스처로 직접 검증한다. §1.3 커맨드 코드에는 그런 조건 분기 자체가 없다(항상 `_build_fulfillment_location_data` 호출) |
| R4 | 스위프가 `status=open` 목록 피드(`fetch_all_open_orders`)를 재사용해 종료/취소 주문을 놓친다 | AC-RSW-015/016이 `closed_at`/`cancelled_at`이 채워진 Shopify 응답 픽스처로 직접 검증한다. §1.3 코드는 `orders/{id}.json` 단건 엔드포인트만 사용한다 |
| R5 | `last_resynced_at` 갱신 코드가 성공 경로에만 있고 예외 경로(`except`)에는 없어, poison order가 라운드로빈을 영구 정체시킨다(D1 위반) | AC-RSW-009가 의도적으로 예외를 던지는 픽스처로 갱신 여부를 직접 확인한다. §1.3의 `finally` 블록 배치가 이를 구조적으로 강제한다 |
| R6 `[v0.2.0 재산정, 감사 D14/D15]` | Shopify API 호출 페이싱이 누락되어 짧은 시간에 80회(N=40 × 2)가 몰려 429를 유발한다. **또한 v0.1.0의 사이클 소요 산정은 페이싱(약 24초)만 세고 SPEC 자신이 지목한 지배항(주문당 약 2초의 DB 시간, 총 약 80초)을 빠뜨렸다** | AC-RSW-026이 `time.monotonic`을 고정 모킹해 매 페이싱 호출의 계산된 대기값이 정확히 0.3초인지 직접 단정한다. 재산정: N=40 → API 페이싱 약 24초(80회×0.3초) + DB 처리 약 80초(40×2초) + 네트워크 왕복 → **현실적 사이클은 약 2~3분**, 5분(300초) 주기 대비 여유는 v0.1.0이 주장한 것보다 얇지만 여전히 within budget. "Do not start a new instance" 설정이 실질적 안전장치임을 §1.7에 명시 |
| R7 | Shopify API 호출을 `transaction.atomic()` **안**에 넣어, 느린 네트워크 왕복 동안 DB 트랜잭션/락이 불필요하게 오래 열린다 | §1.3 설계에서 API 호출(주문 조회 + 위치 조회)을 트랜잭션 **밖**에 배치 — `_sync_single_order()`의 DB 쓰기만 `transaction.atomic()`으로 감싼다. 코드 리뷰로 확인(DoD, AC 없음). §8 C8(락 경합)의 노출 시간도 함께 줄인다 |
| R8 | 환불 차등 갱신에서 삭제 로직을 통째로 제거해(과도한 단순화) stale 행이 영원히 누적된다 | AC-RSW-022가 Shopify가 더 이상 보고하지 않는 환불 행이 실제로 삭제되는지 직접 검증한다. §2 M5 "금지 사항"에 명시 |
| R9 `[v0.2.0 전면 재작성, 감사 D1]` | **`bulk_create(update_conflicts=True, unique_fields=[...])`는 MySQL에서 `NotSupportedError`로 즉시 실패한다 — 이 코드가 `_sync_single_order()` 내부에 있어 `sync_store()`·수동 재동기화 버튼·`backfill_missing_orders`·신규 스위프 4개 호출부 전부를 무너뜨리는 최고 위험도 결함이었다** | §1.6에서 `unique_fields`를 완전히 제거했다(D1 직접 수정). M5 완료 조건에 "MySQL RDS에서 최소 1건 수동 검증"을 명시해 이론적 수정이 아니라 실제 실행 확인을 요구한다. `unique_fields`가 재도입되면 즉시 `NotSupportedError`로 전체 회귀 스위트가 실패하므로 재발은 CI 레벨에서 자동 검출된다 |
| R10 | `_sync_single_order()`의 `bundle_map`/`title_map` 파라미터에 `None` 대신 `{}`를 명시적으로 전달하는 경우와 "전달 안 함"을 혼동해 `is None` 대신 falsy 체크(`not bundle_map`)를 쓰면, 정말 0건인 매핑 테이블에서 매 주문마다 재계산이 일어나는 (성능만 저하되고 정합성은 깨지지 않는) 미묘한 버그가 생긴다 | AC-RSW-024가 사이클 안에서 대상 3건을 처리하며 `ShopifySkuSetMapping` 조회 쿼리가 정확히 1회만 실행되는지 쿼리 카운트로 직접 단정한다(HTTP 계층만 모킹, `_sync_single_order`는 실물 실행 — 감사 D16 반영) |
| R11 | 신규 커맨드가 실수로 `StoreSyncWatermark`를 import/갱신해 `sync_store()`의 워터마크 전진 로직과 충돌한다 | AC-RSW-013이 스위프 실행 전후 워터마크 두 필드가 불변인지 직접 단정한다. §2 M6 "금지 사항"에 import 자체를 금지 명시 |
| **R12** `[v0.2.0 신규, 감사 D2]` | header-only(line_item_id IS NULL) 환불 행이 upsert 경로에 섞여 매 사이클 새 행으로 INSERT되어 무한 증식한다 — 저장소에 이미 이 부류의 환불 손상 복구용 `repair_refunds.py` 커맨드가 존재할 만큼 위험도가 높은 영역이다 | §1.6에서 `line_item_id is None`인 행을 bulk upsert 목록에서 분리해 `update_or_create`(IS NULL 인식 조회)로 처리한다. AC-RSW-029가 동일 페이로드로 2회 연속 스위프한 뒤 `Refund.objects.filter(order=..., line_item_id__isnull=True).count() == 1`을 직접 단정한다 |
| **R13** `[감사 D3, 예외 경로 전용으로 범위 축소]` | fulfillment API 호출이 **예외로** 실패했을 때 조용히 삼켜져(`("", {})`) 위치가 지워지고 그 주문이 성공으로 기록된다 | REQ-RSW-030(a) + `raise_on_error=True`(§1.4)로 실패를 명시적으로 전파받아 기존 per-order 실패 처리에 편입시킨다(§1.3-B). AC-RSW-014b가 `_build_fulfillment_location_data`를 예외 발생으로 모킹해 `Order.location`이 무변경으로 유지되고 그 주문이 실패로 집계되는지 직접 단정한다. **이 위험은 예외 경로만 다룬다 — 예외 없이 정상적으로 빈 값이 나오는 경로는 R16이 별도로 다룬다(감사 N2, v0.1.0/v0.2.0이 두 경로를 혼동했던 지점)** |
| **R14** `[감사 D4/N1, 범위 확장]` | 번들 매핑이 존재하는 라인아이템을 재동기화하면(최초 전개·사후 변경 무관) 고아 `sku=bundle_sku` 행이 생기는 `_sync_single_order()`의 기존 한계가 스위프에 의해 수동/희귀에서 자동/약 11회·일(v0.4.0 재산정, 30일 상한 기준 랩 소요 2.14시간)로 증폭된다 | REQ-RSW-031로 이 로직을 수정하지 않음을 명문화하고 Exclusions #12로 배제했다(§8 C9). DoD에서 `git diff`로 `:287-289`가 무변경임을 확인하고, 기존 회귀 테스트 `test_order_resync.py::test_resync_after_mapping_change_reexpands_with_current_mapping_orphans_removed_member`가 무수정 통과하는지 확인한다. **[v0.3.0 정정, 감사 N1]** v0.2.0은 이 배제를 "사후 변경"으로만 한정해 남겨둔 명분("최초 1회 번들 확장")과 모순됐다 — v0.3.0은 문제 정의에서 번들 관련 명분을 완전히 제거했으므로(설계 결정 D6) 이 위험은 최초 전개까지 포함해 완화 없이 개방 위험으로 남는다(§8 C9가 "명시적 개방 위험"으로 정직하게 선언) |
| **R15** `[감사 D13]` | `sync_orders.py`의 스토어 전체 트랜잭션과 스위프가 같은 행에 동시 접근해 락 대기가 발생하고, D1 때문에 그 실패가 다음 랩(~2.14시간, v0.4.0 재산정)까지 재시도를 지연시킨다 | REQ-RSW-017을 사실에 맞게(명시적 애플리케이션 락 없음, DB 엔진 차원의 암묵적 락 경합 가능) 재서술했다. §1.3-E(API 호출을 트랜잭션 밖으로)로 락 보유 시간을 최소화한다. 겹침 빈도가 실운영에서 문제가 되면 후속 과제로 락 조정을 검토한다(spec.md §8 C8) |
| **R16** `[v0.3.0 신규, 감사 N2]` | fulfillment API 호출이 예외 **없이** 정상적으로 빈 위치를 반환하는 경로(언더스코어 없는 위치 이름, 빈 `fulfillment_orders`, `test_order_location.py:62-76`가 이 정상 동작을 고정)에서 `raise_on_error`가 전혀 개입하지 않아 위치가 조용히 지워질 수 있다 — R13과 같은 사고가 다른 트리거로 재현되는 경로이며, 이 SPEC이 새로 만드는 노출이다(`sync_store()`는 기존 주문에 이 경로 자체를 타지 않음, `:422-425`) | §1.3 (B')의 값-병합 로직(새 값이 비면 기존 저장값 유지, 주문/라인아이템 단위)으로 해결한다. AC-RSW-030이 `_build_fulfillment_location_data`를 예외 없이 빈 값으로 반환하도록 모킹해 `Order.location`이 무변경으로 유지되고 **그 주문은 성공으로 집계**되는지(R13/예외 경로와 달리 실패가 아님) 직접 단정한다 |
| **R17** `[v0.3.0 신규, 감사 N3]` | header-only(line_item_id IS NULL) 환불 키에는 유니크 제약이 없어(가정 A8) 이력 데이터나 `sync_store()`와의 동시 실행 경합(§8 C8)으로 이미 중복 행이 존재할 수 있는데, 기존 `.all().delete()`가 제공하던 자가치유가 차등 갱신 설계에서 사라져 `update_or_create`의 내부 `.get()`이 `MultipleObjectsReturned`를 던지고 그 주문이 영구 실패한다 | §1.6 (B')에서 upsert 시도 전에 동일 키의 기존 행이 2건 이상이면 1건만 남기고 나머지를 삭제하는 자가치유 단계를 추가했다. AC-RSW-029b가 Given에서 중복 행 2건을 미리 삽입하고 스위프 1회 후 `count()==1`이고 그 주문이 실패 목록에 없음을 직접 단정한다 |

---

## 5. MX 태그 계획

### 5.1 백엔드 — 신규 `@MX:NOTE`

- `shopify_orders.py`의 `_qualifying_orders_queryset()` 함수 선언부 위에 `@MX:NOTE` 1건 — 대상 연령 상한(기본값 30일, v0.4.0 — `--days`로 재정의 가능)·`not_shipped` 단일 조건의 근거(SPEC-ORDER-028 사용자 확정 결정) + MySQL에서 `nulls_first=True`가 사실상 no-op이라는 사실(감사 D5).
- `_sync_single_order()`의 `bundle_map is None`/`title_map is None` 분기 위에 `@MX:NOTE` 1건 — 왜 `is None`이어야 하고 falsy 체크가 아닌지(R10).
- `_sync_single_order()`의 환불 upsert 분기(§1.6) 위에 `@MX:NOTE` 1건 — MySQL의 `supports_update_conflicts_with_target=False` 제약과 header-only 환불의 NULL 매칭 한계(D1/D2, R9/R12).
- `_build_fulfillment_location_data()`의 `raise_on_error` 파라미터 위에 `@MX:NOTE` 1건 — 왜 기본값이 `False`이고 스위프만 `True`를 쓰는지, 그리고 이 파라미터가 예외 경로만 다루고 정상-빈값 경로는 다루지 않는다는 사실(D3, R13).
- `resync_order_sweep.py`의 `finally` 블록(D1) 위에 `@MX:NOTE` 1건 — "성공/실패 무관하게 항상 갱신"이라는 규칙의 의도(poison order 방지).
- **[v0.3.0 신규]** `resync_order_sweep.py`의 위치 병합 로직(§1.3 (B')) 위에 `@MX:NOTE` 1건 — 새로 조회한 값이 비어 있을 때 기존 저장값을 유지하는 이유(R16, `test_order_location.py:62`가 고정하는 "정상이지만 빈 값" 동작과의 상호작용).
- **[v0.3.0 신규]** `_sync_single_order()`의 header-only 환불 자가치유 단계(§1.6 (B')) 위에 `@MX:NOTE` 1건 — 왜 upsert 전에 중복 정리가 필요한지(R17, `MultipleObjectsReturned`로 인한 영구 실패 방지).

작업 전 `shopify_orders.py`의 기존 NOTE 개수를 확인해 `mx.yaml`의 `note_per_file` 한도(기본 10)를 넘지 않는지 확인한다 — v0.2.0+v0.3.0 누적으로 `shopify_orders.py` 신규 NOTE가 총 5건(위치 병합 로직은 `resync_order_sweep.py`에 위치하므로 제외), `resync_order_sweep.py` 신규 NOTE가 총 2건이다.

### 5.2 신규 `@MX:ANCHOR` 검토

`_sync_single_order()`는 이미 fan_in >= 3(`sync_store()`, `sync_single_order_from_shopify()`, `backfill_missing_orders`, 그리고 이 SPEC이 추가하는 `resync_order_sweep` — 4번째 호출부)이 된다. 기존에 이 함수에 `@MX:ANCHOR`가 없다면 이번 SPEC으로 신설을 검토한다. `_build_fulfillment_location_data()`도 같은 이유로(4번째 호출부 추가) 검토 대상이다.

파일 내 태그 수 변화: `shopify_orders.py` NOTE +5(대상 판정 헬퍼 1 + 배치 컨텍스트 분기 1 + 환불 upsert 분기 1 + `raise_on_error` 파라미터 1 + 환불 자가치유 단계 1). `resync_order_sweep.py` NOTE +2(신규 파일: `finally` 블록 1 + 위치 병합 로직 1).

---

## 6. 검증 명령 (참고)

```bash
# 마이그레이션
python manage.py makemigrations order --check  # M1 이후 0045가 이미 생성되어 있는지 확인
python manage.py migrate

# 백엔드 신규 테스트만 (동시 실행 금지, 서브셋에는 --no-cov 필수)
pytest backend/order/tests/test_spec_028.py --no-cov -v

# 회귀 (배치 불변 컨텍스트 + 환불/배송라인 리팩터가 건드리는 기존 스위트 — MySQL RDS 대상)
pytest backend/order/tests/test_shopify_orders.py --no-cov -v
pytest backend/order/tests/test_order_resync.py --no-cov -v
pytest backend/order/tests/test_backfill_missing_orders_command.py --no-cov -v
pytest backend/order/tests/test_sync_orders_command.py --no-cov -v
pytest backend/order/tests/test_order_location.py --no-cov -v

# [v0.2.0 신규] 쿼리 플랜 확인 — MySQL EXPLAIN (§1.1 DoD)
# EXPLAIN SELECT ... — key가 order_last_resynced_at_idx이고 Extra에
# "Using filesort"가 없는지 육안 확인. filesort가 나오면 §1.1의 대안 검토.

# [v0.2.0 신규] MySQL 차등 갱신 수동 검증 (§2 M5 완료 조건)
# 동일 주문을 2회 연속 동기화해 ShippingLine/Refund 행 수가 늘지 않는지,
# unique_fields 없는 bulk_create(update_conflicts=True)가 실제로
# ON DUPLICATE KEY UPDATE로 실행되는지 확인.

# [v0.3.0 신규] header-only 환불 선존 중복 자가치유 수동 검증 (§2 M5, N3/R17)
# (order, refund_id, NULL) 행 2건을 미리 INSERT한 뒤 스위프 1회 실행 —
# MultipleObjectsReturned 없이 count()==1로 수렴하는지 확인.

# [v0.3.0 신규] 위치 정상-빈값 병합 수동 검증 (§2 M4, N2/R16)
# Order.location="NJ" 상태에서 fulfillment_orders.json이 빈 배열을 반환하는
# 주문을 스위프 — Order.location이 "NJ"로 유지되고 실패로 집계되지 않는지 확인.

# 스케줄러 스크립트 수동 실행
scripts\resync_order_sweep.bat
type logs\resync_order_sweep.log

# 범위 규율 확인
git diff --stat backend/order/views.py                                    # 공집합
git diff --stat backend/order/purchase_order_views.py                     # 공집합(:2392-2579 무변경)
git diff backend/order/shopify_orders.py                                   # sync_store()/sync_single_order_from_shopify() 본문 무변경 확인(환불/배송라인 내부 로직 변경은 예외)
git status backend/order/migrations/                                       # 신규 파일 정확히 1건(0045)
```

---

## 7. 완료 후 기록

`spec.md` HISTORY에 다음을 추가한다:
- 통과 테스트 수(신규 AC-RSW 35개 + 기존 회귀 스위트 5개 무수정 통과)
- MySQL RDS에서의 `bulk_create(update_conflicts=True)`(unique_fields 없이) 수동 검증 결과
- header-only 환불 자가치유 수동 검증 결과(N3), 위치 정상-빈값 병합 수동 검증 결과(N2)
- `EXPLAIN` 결과 요약(대상 판정 쿼리가 복합 인덱스를 쓰는지, filesort 여부)
- mx_plan 실행 결과(신규 NOTE/ANCHOR 태그 개수)
- 계획 대 실제 파일 목록 대조(미예정 파일 변경 0건 확인)
