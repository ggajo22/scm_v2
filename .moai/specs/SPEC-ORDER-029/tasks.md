## Task Decomposition
SPEC: SPEC-ORDER-029 (v0.5.0)

## Plan-Implementability Validation (pre-task-decomposition)

Performed against the current state of `backend/order/` (not re-derived from plan.md). Full findings are
in the manager-strategy session report. Summary:

- Name collisions: none. `_chunked`, `fetch_order_status_by_ids`, `open_candidate_order_ids`,
  `reconcile_order_status_for_ids`, `_is_lock_wait_timeout`, `IDS_CHUNK_SIZE`, `SHOPIFY_ORDER_STATUS_FIELDS`
  do not exist anywhere in `backend/`. `sync_order_cancellations.py`, `backfill_order_cancellations.py`,
  and the three planned test files do not exist yet.
- `[MODIFY]` surface on `shopify_orders.py` is genuinely additive — the 4 new functions are appended after
  the current EOF (line 461, end of `sync_store()`); `sync_store()`, `_sync_single_order()`,
  `sync_single_order_from_shopify()`, `fetch_all_open_orders()` are untouched by the plan.
- Patch-target convention (plan.md §1.6 / acceptance.md §0.2): verified consistent with this repo's actual
  precedent (`test_backfill_missing_orders_command.py:17`, `test_sync_orders_command.py:16`) — both patch
  the *consuming* module's own imported name. The new commands only import `open_candidate_order_ids` /
  `reconcile_order_status_for_ids` into their own namespace (not `_get_with_headers`), so
  `order.shopify_orders._get_with_headers` / `order.shopify_orders.fetch_order_status_by_ids` are the
  correct patch targets for HTTP/chunk-level tests — same principle as the existing convention, applied
  correctly to a different import shape. No divergence in principle, only in target path, and the plan
  explains this correctly (plan.md §1.6 item 1).
- Imports/helpers the plan assumes exist: `_get_with_headers` (shopify_orders.py:16), `_parse_next_page_info`
  (shopify_orders.py:25), `parse_datetime`/`timezone` already module-level imports (shopify_orders.py:7-8),
  `Order.cancelled_at`/`closed_at`/`shopify_order_id`/`store_type` (models.py:79-80,31-35),
  `StoreSyncWatermark.last_synced_updated_at`/`last_run_at` (models.py:586,596) — all confirmed present with
  matching field names. MySQL driver confirmed as `mysqlclient` (pyproject.toml:13,
  `DB_ENGINE=django.db.backends.mysql`), consistent with `_is_lock_wait_timeout()`'s
  `django.db.utils.OperationalError` string-matching design.
- Command conventions: the two planned commands mirror `sync_orders.py`'s `try/except` + `failed.append()` +
  `raise CommandError` pattern and `backfill_missing_orders.py`'s `--dry-run` pattern correctly.
- `.bat` script: mirrors all 5 structural items of `scripts/sync_orders.bat` (cd to `backend/`,
  `PYTHONIOENCODING=utf-8`, dedicated log file, exit-code propagation, "do not start new instance" REM
  comment — actual enforcement is a Task Scheduler setting in both cases, not `.bat` content).
- AC implementability: all 25 ACs in acceptance.md are expressible with existing fixtures/patch points
  (Order/LineItem/ShippingLine/Refund/PurchaseOrder models and their FKs/related_names all confirmed to
  exist with the exact field names the ACs reference; `call_command(..., stdout=<buf>, stderr=<buf>)` is
  standard Django test API).

**PROBLEM found (blocks M4, not M1-M3):** plan.md §1.5 / spec.md §1.2 D10's recommended stagger offset
`:X2:30` does not satisfy REQ-CANC-027's own "최소 2분 이상" requirement, and does not match its own
"2 minutes 35 seconds ahead of `sync_orders`" description. `sync_orders` fires at `minute%5==4, second=05`
(measured, spec.md A7). The PowerShell one-liner in plan.md line ~476
(`.AddMinutes((Get-Date).Minute - ((Get-Date).Minute % 5) + 2).AddSeconds(30)`) always resolves to
`minute%5==2, second=30` regardless of when it is run. The forward gap from `:X2:30` to the next
`:X4:05` is only **1 minute 35 seconds** (95s), not the claimed 2m35s, and it is **below** the "최소 2분"
(120s) floor REQ-CANC-027 itself sets. The backward gap (previous `:X4:05` to `:X2:30`) is 3m25s, which
does satisfy the floor — so the requirement is met in one direction only. A true "2 minutes 35 seconds
before `:X4:05`" target is `:X1:30` (`minute%5==1, second=30`), not `:X2:30` — the plan's formula has an
off-by-one-minute error (`+2` should be `+1`). This must be corrected before M4's scheduler registration
step, or the DoD's `Get-ScheduledTaskInfo` verification will measure a gap that does not meet the SPEC's
own stated floor. Flagged as a task note under T-007 below; not a blocker for M1-M3 (pytest-covered,
unaffected).

---

## HARD Environment Constraints (apply to every task below with pytest commands)

- Always append `--no-cov` to any `pytest backend/order/...` subset command. `pytest.ini` sets
  `addopts = --cov=accounts --cov-report=term-missing --cov-fail-under=90` — without `--no-cov`, a
  subset run measures the wrong app's coverage and **exits 1 even when every test in the subset passes**.
- The test database is a shared remote MySQL instance (RDS, ~130ms/query). **Never run two pytest
  processes concurrently** — it produces false failures from cross-session interference.
- **Never run `python manage.py sync_order_cancellations` or `backfill_order_cancellations` against the
  real database at any point in this SPEC's implementation.** Both write to production `Order` rows and
  call the live Shopify API. All verification in T-001 through T-006 and T-009 is via mocked pytest only.
  The only place a real, unmocked run is appropriate is T-007's scheduler DoD check, and only after all
  of M1-M3's tests pass.
- `USE_TZ=True` (settings/base.py:94) — all datetime fixtures must be timezone-aware
  (`django.utils.timezone.now()`/`make_aware`), never naive.

---

## Task Table

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|---------------|---------------|--------|
| T-001 | RED (M1): Write `test_spec_029.py` covering AC-CANC-001~012 and AC-CANC-024 (13 cases; AC-CANC-005 sibling-order fixture uses real ids 90005/90006 per v0.4.0 D-N8 correction). Run against unmodified `shopify_orders.py` and confirm every case fails with `ImportError`/`AttributeError` (functions don't exist yet) — record the failure output as RED evidence. Patch targets per acceptance.md §0.2 groups 1/3/4 (`order.shopify_orders._get_with_headers` and `order.shopify_orders.fetch_order_status_by_ids`). | REQ-CANC-001~012, REQ-CANC-025 | - | `backend/order/tests/test_spec_029.py` [NEW] | pending |
| T-002 | GREEN (M1): Append `_chunked()`, `SHOPIFY_ORDER_STATUS_FIELDS`, `IDS_CHUNK_SIZE`, `fetch_order_status_by_ids()`, `open_candidate_order_ids()`, `_is_lock_wait_timeout()`, `reconcile_order_status_for_ids()` to `shopify_orders.py` after the current EOF (line 461), plus one module-level `from datetime import timedelta` import. Do not modify `sync_store()`, `_sync_single_order()`, `sync_single_order_from_shopify()`, `fetch_all_open_orders()`, `_build_fulfillment_location_data()`, `_get_with_headers()`, `_parse_next_page_info()`. Make all 13 T-001 cases pass (`pytest backend/order/tests/test_spec_029.py --no-cov -v`). Then run the regression set (`test_shopify_orders.py`, `test_sync_orders_command.py`, `test_backfill_missing_orders_command.py`, `test_order_resync.py`, `test_store_sync_watermark.py`, all `--no-cov`) and confirm zero regressions. Verify `git diff --stat backend/order/shopify_orders.py` shows only additions at EOF plus the one import line. | REQ-CANC-001~012, REQ-CANC-025 | T-001 | `backend/order/shopify_orders.py` [MODIFY] | pending |
| T-003 | RED (M2): Write `test_sync_order_cancellations_command.py` covering AC-CANC-013~018 and AC-CANC-025 (7 cases, AC-CANC-017/025 each contain 2 scenarios). Patch targets per acceptance.md §0.2: group 1 (`order.shopify_orders._get_with_headers`) for write-result assertions, group 2 (`order.management.commands.sync_order_cancellations.open_candidate_order_ids` with a store-keyed `side_effect`) for store-level failure injection, group 3 (`order.shopify_orders.fetch_order_status_by_ids`) for chunk-level failure injection including AC-CANC-025's lock-timeout vs. non-lock-timeout contrast, group 4 for AC-CANC-014's call-argument capture. Confirm RED (`ImportError`/`CommandError: Unknown command` — the command module does not exist yet). | REQ-CANC-013~017, REQ-CANC-024, REQ-CANC-026 | T-002 | `backend/order/tests/test_sync_order_cancellations_command.py` [NEW] | pending |
| T-004 | GREEN (M2): Create `sync_order_cancellations.py` per plan.md §1.3 — `--store` argument (choices gimssine/etoile/all, default all), `CLOSED_GRACE_DAYS = 30` module constant passed explicitly as `closed_grace_days=CLOSED_GRACE_DAYS`, store-loop `try/except` isolation, chunk-failure stderr reporting with `lock_timeout` tag, `missing_ids` stdout warning, and the `all(cf.get("lock_timeout") ...)` soft/hard failure split per REQ-CANC-026 before appending to `failed`. Never import `LineItem`/`ShippingLine`/`Refund`/`StoreSyncWatermark`. Make all 7 T-003 cases pass. | REQ-CANC-013~017, REQ-CANC-024, REQ-CANC-026 | T-003 | `backend/order/management/commands/sync_order_cancellations.py` [NEW] | pending |
| T-005 | RED (M3): Write `test_backfill_order_cancellations_command.py` covering AC-CANC-019~023 (5 cases). Patch targets per acceptance.md §0.2 groups 1 and 4. AC-CANC-023 (idempotency) uses the same mocked value across both `call_command` invocations and asserts `count() == 1`, per v0.3.0's narrowed claim (D14) that "value drifts on rerun" is not a reachable mutation in this architecture. Confirm RED. | REQ-CANC-018~020 | T-004 | `backend/order/tests/test_backfill_order_cancellations_command.py` [NEW] | pending |
| T-006 | GREEN (M3): Create `backfill_order_cancellations.py` per plan.md §1.4 — `--store` and `--dry-run` arguments, `open_candidate_order_ids(store_type, closed_grace_days=None)` passed explicitly (no reliance on the function's own default), `dry_run` forwarded to `reconcile_order_status_for_ids`, per-order stdout diagnostic lines including the literal `"would_change"` label required by AC-CANC-021. Never import `LineItem`/`ShippingLine`/`Refund`/`StoreSyncWatermark`. Make all 5 T-005 cases pass. | REQ-CANC-018~020 | T-005 | `backend/order/management/commands/backfill_order_cancellations.py` [NEW] | pending |
| T-007 | M4: Create `scripts/sync_order_cancellations.bat` mirroring all 5 structural items of `scripts/sync_orders.bat` (cd to `backend/`, `PYTHONIOENCODING=utf-8`, dedicated `logs/sync_order_cancellations.log`, exit-code propagation via `set RC=%ERRORLEVEL%` / `exit /b %RC%`, "do not start new instance" REM comment). **Before registering the scheduler task, correct the stagger-offset math from plan.md §1.5** — the plan's PowerShell formula (`+2` minutes, landing on `:X2:30`) produces only a 1m35s forward gap to `sync_orders`' measured `:X4:05` phase, which is below REQ-CANC-027's own "최소 2분 이상" floor; use `+1` minute (`:X1:30`) or otherwise verify the actual computed offset satisfies >=2 minutes in both directions before registering. Register via `Register-ScheduledTask` with `-MultipleInstances IgnoreNew`, confirm >=1 successful run (`LastTaskResult == 0`), and confirm via `Get-ScheduledTaskInfo` that the actual registered trigger time differs from `sync_orders`' trigger time by >=2 minutes (do not accept "task exists" as sufficient evidence). Record whether a low-frequency `backfill_order_cancellations` scheduler entry was also registered, or record the explicit decision not to in `.moai/project/scheduled-jobs.md` (spec.md §8 C5/D-N5). | REQ-CANC-021, REQ-CANC-027 | T-004, T-006 | `scripts/sync_order_cancellations.bat` [NEW] | pending |
| T-008 | M5: Add the two planned `@MX:NOTE` annotations in `shopify_orders.py` per plan.md §6.1 — one above `reconcile_order_status_for_ids()` explaining why it never routes through `_sync_single_order()`/`update_or_create(defaults=...)`, one above `_is_lock_wait_timeout()` explaining the error-code string-match rationale and its link to `sync_orders`' long-held transaction. No `@MX:ANCHOR` needed (fan_in=2, below the >=3 threshold). | (MX tag quality gate, no REQ) | T-002 | `backend/order/shopify_orders.py` [MODIFY] | pending |
| T-009 | Final regression + DoD closure: run the full new-test set and the full regression set together (`test_spec_029.py`, `test_sync_order_cancellations_command.py`, `test_backfill_order_cancellations_command.py`, `test_shopify_orders.py`, `test_sync_orders_command.py`, `test_backfill_missing_orders_command.py`, `test_order_resync.py`, `test_store_sync_watermark.py`, all in one `--no-cov` invocation, one process at a time). Verify `backend/order/migrations/` has 0 new files, `git diff --stat backend/order/models.py` is empty, `git diff --stat scripts/sync_orders.bat` is empty, and grep both new command files for `LineItem`/`ShippingLine`/`Refund`/`StoreSyncWatermark` (expect 0 matches). Update `spec.md` HISTORY with pass count, actual backfill results (of the 52 known-unreflected cancellations), post-deploy `candidates=N` figures, scheduler confirmation, and mx_plan results, per acceptance.md DoD "문서" section. | (DoD closure, all REQs) | T-007, T-008 | `.moai/specs/SPEC-ORDER-029/spec.md` [MODIFY, HISTORY only] | pending |

---

## Milestone -> Task Mapping (traceability to plan.md)

- M1 (공유 코어 함수): T-001, T-002
- M2 (감지 커맨드): T-003, T-004
- M3 (백필 커맨드): T-005, T-006
- M4 (스케줄러 스크립트): T-007
- M5 (@MX 태그 + 문서): T-008, T-009
