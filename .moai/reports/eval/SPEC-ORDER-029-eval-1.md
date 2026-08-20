## Evaluation Report
SPEC: SPEC-ORDER-029
Branch: `feature/SPEC-ORDER-029`
Overall Verdict: **FAIL**

### Dimension Scores
| Dimension | Score | Verdict | Evidence |
|-----------|-------|---------|----------|
| Functionality (40%) | 66/100 | FAIL | 25/25 documented AC pass, and 12 independent mutation categories were applied by hand — 11 caught immediately by the AC set. But `_is_lock_wait_timeout()` (`backend/order/shopify_orders.py:557-569`) is demonstrated by direct execution (not mutation) to misclassify unrelated exceptions as soft lock-wait failures, undermining REQ-CANC-025/026's core safety guarantee. One additional test-discriminability gap found (idempotent-write check, `shopify_orders.py:631`). |
| Security (25%) | 90/100 | PASS | No injection surface (ids are `BigIntegerField`-sourced, not user input); `--store` is choice-constrained; URL length ~3,610 chars for 250 ids (well under limits, verified by AC-CANC-007); no secrets in URLs/logs; empty-candidate-list path handled cleanly. |
| Craft (20%) | 68/100 | FAIL | `ruff check` (project's own configured gate, `pyproject.toml:32-38`, `line-length=100`) fails with 20 violations attributable to new SPEC-029 code (7 in implementation, 13 in tests) — verified by direct execution, not assumed. Numeric coverage % not independently measured per the evaluation's HARD `--no-cov` constraint; AC-exhaustiveness and mutation results substitute as qualitative evidence. |
| Consistency (15%) | 82/100 | PASS | `.bat` script mirrors `sync_orders.bat` on all 5 required items; §0.2 patch-target convention (HTTP-layer vs. command-module patch groups) is followed correctly in all three test files; minor style deviation: `_credentials()` is a module-level function here vs. a `Command` method in `backfill_missing_orders.py`/`repair_refunds.py`. |

**Weighted score**: 0.40×66 + 0.25×90 + 0.20×68 + 0.15×82 = 74.9. Security did not FAIL, but Functionality FAIL drives the overall verdict per the hard-threshold rule that any dimension FAIL is reported, and Functionality (highest weight, 40%) carries a demonstrated — not hypothetical — defect in shipped code.

---

### Methodology note

All findings below were verified by one of three methods, stated explicitly per finding:
- **Executed (baseline)**: ran the full 27-test SPEC-ORDER-029 suite unmodified — `27 passed in 135.44s`.
- **Executed (mutation)**: edited `shopify_orders.py` or the command files, ran the targeted test(s) with `--no-cov`, observed pass/fail, then reverted the exact edit and re-ran the affected test to confirm the revert.
- **Executed (probe)**: called an existing function directly with a crafted input, without modifying any file, to observe its real behavior.
- **Read**: assessed by reading code/config without execution.

Every mutation was reverted immediately after observation. Final state confirmed clean (see "Working tree" section at the end).

---

### 1. Mutation-testing results (Priority 1)

| # | Mutation | Location | Result | Test that caught it |
|---|----------|----------|--------|----------------------|
| M-bulk | Drop `cancelled_at` from `bulk_update` field list | `shopify_orders.py:645` | **Caught** | 14 tests fail immediately (AC-CANC-001 first) |
| M-window-invert | `closed_at__gte` → `closed_at__lte` | `shopify_orders.py:547` | **Caught** | AC-CANC-011 (`90011002` incorrectly excluded from bounded set) |
| M-window-delete | Remove the `closed_grace_days` filter entirely | `shopify_orders.py:545-547` | **Caught** | AC-CANC-011 (`90011003` incorrectly included in bounded set) |
| M-swap | Swap `cancelled_at`/`closed_at` on write | `shopify_orders.py:640-641` | **Caught** | AC-CANC-003 (`closed_at` stayed `None` instead of the closed value) |
| M-status | `status=any` → `status=open` | `shopify_orders.py:500` | **Caught** | AC-CANC-006 (non-DB test, fails in 1.1s) |
| M-fields | Drop `fields=` param | `shopify_orders.py:500` | **Caught** | AC-CANC-006 |
| M-limit | Drop `limit=` param | `shopify_orders.py:500` | **Caught** | AC-CANC-006 |
| M-chunksize | `IDS_CHUNK_SIZE = 250` → `1000` | `shopify_orders.py:470` | **Caught** | AC-CANC-007 (non-DB test) |
| M-failedappend | Delete `failed.append(f"{store_type} (partial)")` | `sync_order_cancellations.py:73` | **Caught** | AC-CANC-017 scenario 2 (`DID NOT RAISE CommandError`) — confirms the auditor's own targeted regression is closed |
| M-locktimeout-true | `_is_lock_wait_timeout()` → always `True` | `shopify_orders.py:569` | **Caught** | AC-CANC-024, AC-CANC-025 scenario 2 |
| M-locktimeout-false | `_is_lock_wait_timeout()` → always `False` | `shopify_orders.py:569` | **Caught** | AC-CANC-024, AC-CANC-025 scenario 1 |
| M-missingids | Delete `missing_ids.extend(...)` (short-response handling) | `shopify_orders.py:613` | **Caught** | AC-CANC-012 |
| **M-diffcheck** | **Replace `if order.cancelled_at != new_cancelled or order.closed_at != new_closed:` with `if True:`** (unconditional write / idempotence-of-diff) | `shopify_orders.py:631` | **NOT CAUGHT** | Ran all 27 tests (`test_spec_029.py` + both command test files) — **all 27 pass** with this mutation applied |

**M-diffcheck is the finding that matters per Priority 1.** With the diff check replaced by an unconditional `if True`, every candidate order that Shopify returns a record for is added to `changed` and written via `bulk_update`, regardless of whether its `cancelled_at`/`closed_at` actually differ from the stored value. All 27 tests still pass because:
- No AC constructs a fixture where a record is already reconciled (matching value) and re-appears in a subsequent Shopify response with the *same* value.
- AC-CANC-023 (the idempotency AC) doesn't exercise this path either — on the second `backfill_order_cancellations` run, order 90023 already has `cancelled_at` set, so it drops out of the candidate set (`cancelled_at IS NULL` filter) before `reconcile_order_status_for_ids` is even called a second time — the diff-check branch is never reached on the "idempotent" AC's own re-run.

Practical consequence: the `changed=N` / `would_change=N` counts reported to stdout (used for `--dry-run` diagnostics and operator visibility) are not verified to reflect *actual* changes — a regression here would silently inflate every reported count and cause `bulk_update()` to be called on every candidate order every cycle instead of only on the ones with a real diff. This runs directly counter to spec.md §1.2's own stated rationale for why this SPEC's lock hold time is safe ("이 SPEC 자신의 잠금 보유 시간은 밀리초 단위다" — justified by narrow, minimal writes) — a regression here would still be correct data-wise (writing the same value twice doesn't corrupt anything) but would silently defeat that "narrow write" cost argument, and no test would notice.

---

### 2. `_is_lock_wait_timeout()` vs. reality (Priority 2) — real, demonstrated defect

```python
# shopify_orders.py:557-569
def _is_lock_wait_timeout(exc):
    return "1205" in str(exc) or "Lock wait timeout exceeded" in str(exc)
```

**Verified by direct probe (not mutation)** — called the shipped, unmodified function with crafted, unrelated exceptions:

```
unrelated ValueError w/ coincidental substring -> True
unrelated KeyError w/ coincidental substring -> True
unrelated, no match -> False
```//command output reproduced verbatim above

The function does **not** check `isinstance(exc, django.db.utils.OperationalError)` before string-matching — it will classify *any* exception type as a soft lock-timeout failure purely because its `str()` happens to contain the four-character substring `"1205"`. Given that:
- `chunk_failures` entries record `str(exc)` for whatever exception the chunk's try/except catches — this includes `urllib.error.HTTPError`/`URLError` from the network fetch, `json.JSONDecodeError`, `KeyError`, and any `django.db.utils.*Error` from the `bulk_update()`/filter step, not just `OperationalError` 1205.
- `shopify_order_id` values are large integers (10-13+ digits per spec.md A1); a coincidental 4-digit run of `"1205"` appearing somewhere inside an id, or inside any other numeric content that ends up embedded in an unrelated exception's message, is a low- but non-zero-probability event that grows with cumulative production usage.

This is precisely the "always-true" failure mode the evaluation brief warned about (Priority 2: "always-true silences genuine failures"), except partial rather than total — it silences genuine failures **conditionally**, based on message content collision, which is harder to notice in production than a blanket bug because the classifier is *usually* correct. This directly undermines the safety argument spec.md D10 builds at length: the decision to treat lock-wait timeouts as soft failures is explicitly justified by the claim that *only* self-healing, well-understood lock-contention failures get suppressed — a real, unrelated bug that happens to collide with the string match would be silently absorbed into "self-healing" and never raise `CommandError`, exactly the ExchangeRate-incident failure mode (silent stoppage) that spec.md's own D10 rationale cites as the risk it is trying to avoid on the *other* side of the tradeoff.

None of the 25 documented ACs exercise this because AC-CANC-024/025's "non-lock-timeout" fixture (`ValueError("malformed response")`) was deliberately chosen not to contain "1205" or the phrase — so the AC set does not probe the classifier's precision, only its behavior on two hand-picked exemplars.

**Recommendation**: gate the string match behind `isinstance(exc, OperationalError)` first (import `from django.db.utils import OperationalError`), then check `exc.args and exc.args[0] == 1205` (or the string check) only on that narrowed type. This closes the false-positive class without weakening the driver-portability rationale already documented in the code's own comment.

---

### 3. Known divergence — AC-CANC-016 (Priority 3)

Confirmed by reading: `test_sync_order_cancellations_command.py:116-135` (`test_ac_cancc_016_chunk_failure_isolated_ids_recorded`) calls `reconcile_order_status_for_ids(...)` directly, not `call_command(...)`, despite being filed in the command test file under the "감지 커맨드 AC" section.

This matches `acceptance.md`'s own literal AC-CANC-016 text (lines 310-321), which specifies **"When** `reconcile_order_status_for_ids(...)` 호출" — the implementer's test is a faithful transcription of the acceptance document as written; the divergence originates in the SPEC document's own file/section labeling versus its Given/When/Then body, not in an implementation shortcut. The implementer disclosed this rather than silently reconciling the mismatch by rewriting the AC.

**Does this leave a real REQ coverage hole?** Assessed as **low risk, non-blocking**:
- The `sync_order_cancellations` command itself has **no chunk-iteration logic of its own** — all chunking and per-chunk isolation lives entirely inside `reconcile_order_status_for_ids()` (`shopify_orders.py:605-654`). The command only consumes the aggregated `result` dict once per store.
- The command-specific logic that IS unique to the command layer — translating `chunk_failures` into the `failed` list (soft vs. hard) and writing to stderr — **is** exercised through a real `call_command()` invocation, in `test_ac_cancc_017_scenario2_chunk_level_failure_raises_partial` (`test_sync_order_cancellations_command.py:156-172`), which is exactly the scenario the plan-auditor's iteration-3 review flagged as previously uncovered (mutation M-failedappend above, confirmed caught).
- The one genuine residual gap: no test exercises **same-store, multi-chunk** partial success through `call_command()` (only cross-store chunk failure is exercised at the command level; same-store multi-chunk isolation is exercised only at the core-function level via AC-CANC-016). Given the command has no chunk logic of its own to diverge from the core function's, this residual gap is narrow.

---

### 4. Security (Priority 4)

- **Injection**: `shopify_order_id` is `models.BigIntegerField` (`order/models.py:31`) — every value in `ids=<comma-separated>` originates from the local DB via `open_candidate_order_ids()`, never from user/CLI input. The only user-facing arguments on both commands are `--store` (argparse `choices=["gimssine","etoile","all"]`, enforced before use) and `--dry-run` (boolean flag). No free-form input reaches the URL. **No injection risk.**
- **URL length**: verified by AC-CANC-007 (executed) — 250 13-digit ids joined produce a string `< 4000` chars (measured ~3,610 in spec.md); well under common 8KB+ URL limits.
- **Empty-list handling**: `fetch_order_status_by_ids([])` returns `[]` immediately (`shopify_orders.py:497-498`); `_chunked([], 250)` yields nothing, so `reconcile_order_status_for_ids(..., [])` returns a clean zeroed result dict with no exceptions. Verified by reading — consistent with `open_candidate_order_ids()` returning `[]` when a store has no candidates.
- **Secret/token leakage**: the Shopify access token is passed only via the `X-Shopify-Access-Token` header in `_get_with_headers` (`shopify_orders.py:19`), never interpolated into the URL or logged; `chunk_failures["error"]` stores `str(exc)` from `urllib`/Django exceptions, which do not include request headers by default. No leakage path introduced by this SPEC.

No Critical/High findings. Security dimension **PASSES**.

---

### 5. Invariants (Priority 5) — all confirmed by reading + grep, no violations found

- Write path confined to `cancelled_at`/`closed_at`: single `bulk_update(to_update, ["cancelled_at", "closed_at"])` call (`shopify_orders.py:645`), reinforced by AC-CANC-018/AC-CANC-022 fixtures asserting non-default `Order.status`/`note`/`ready_to_ship`, `LineItem` 5 fields, and `ShippingLine`/`Refund` row counts are unchanged (both tests pass, executed).
- `_sync_single_order()` is never called from the new code — confirmed via `grep`, the only occurrences of that name in the new section (lines 465-661) are in comments explaining why it's avoided.
- `StoreSyncWatermark` is never imported/referenced by either new command (`grep` of both command files' `from`/`import` lines shows only `django.conf.settings`, `django.core.management.base`, and `order.shopify_orders`). AC-CANC-013 confirms at runtime that a pre-existing watermark's fields are byte-identical before/after a `sync_order_cancellations` run.
- `Order.status`, `ready_to_ship`, `LineItem.purchase_status`/`logistics_status`/`original_sku`/`received_quantity` — none referenced anywhere in the new code (confirmed by `grep` across the new section and both command files; all matches for these terms were either in old, unmodified `_sync_single_order()` code or in comments).
- Neither command imports `LineItem`, `ShippingLine`, `Refund`, or `StoreSyncWatermark` (confirmed by reading both files' import blocks).
- `git diff --stat` for `shopify_orders.py` shows exactly `+200/-0` (additive-only); `models.py` and `scripts/sync_orders.bat` show zero diff; no new files under `order/migrations/`.

---

### 6. Craft

- **Lint (executed)**: `ruff check` (project config: `pyproject.toml:32-38`, `line-length=100`, rules `E,F,W,I`) against all new/modified SPEC-029 files:
  - `sync_order_cancellations.py:54,62,77` — E501 (3 violations, entire file is new)
  - `shopify_orders.py:541,597` — I001 import-block-unsorted (both inside newly-added functions — `from django.db.models import Q` and `from django.db import transaction` are function-local imports placed after other statements)
  - `shopify_orders.py:579,629` — E501 (2 violations, both in new code)
  - `test_spec_029.py` — 6 × E501
  - `test_sync_order_cancellations_command.py` — 6 × E501
  - `test_backfill_order_cancellations_command.py:10` — I001
  - Baseline comparison (executed): `ruff check order/tests/test_backfill_missing_orders_command.py` (an existing, pre-SPEC-029 file in the same directory) → `All checks passed!` — confirming this is not pre-existing repo-wide debt tolerated elsewhere, but a genuine gap specific to this SPEC's deliverables. 6 additional E501 hits reported in `shopify_orders.py` (lines 340/351/352/397/429/431) are pre-existing, outside this SPEC's diff (diff starts at line 465) and are **not** attributed to this SPEC.
  - Net new-code lint debt: **7 in implementation** (`shopify_orders.py` new section: 4, `sync_order_cancellations.py`: 3) + **13 in tests** = 20 violations, `[*] 3 fixable with --fix` (the I001 ones).
- **Coverage**: not independently measured with a numeric percentage — the evaluation's HARD constraint requires `--no-cov` on every pytest invocation to avoid the wrong-app `--cov-fail-under=90` false failure, and no scoped override was attempted to stay strictly within that constraint. Qualitative substitute: 24 of 25 documented mutations were independently reproduced and caught (Section 1), which is strong but not equivalent to a measured branch-coverage number. **Marked UNVERIFIED for the specific numeric claim.**
- **Error handling**: the chunk-level `except Exception as exc:` (`shopify_orders.py:646`, `# noqa: BLE001`) and store-level `except Exception as exc:` in both commands are broad-by-design, consistent with the REQ-CANC-011/015/016 isolation requirements and consistent with the existing `sync_store()` pattern in the same file (also uses broad per-store exception handling for isolation). This is a deliberate, documented, justified pattern — not a craft defect.
- **Over-engineering check**: none found — the four new functions are narrow and single-purpose (`_chunked`, `fetch_order_status_by_ids`, `open_candidate_order_ids`, `reconcile_order_status_for_ids`), no unnecessary abstraction layers, no premature generalization.

---

### 7. Consistency

- `scripts/sync_order_cancellations.bat` mirrors `scripts/sync_orders.bat` on all 5 items required by REQ-CANC-021: working directory `cd /d C:\app\scm_v2\backend`, `PYTHONIOENCODING=utf-8`, dedicated log file, `exit /b %RC%` exit-code propagation, and the "do not start a new instance" REM comment (lines 3-4). Confirmed by reading both files side by side.
- §0.2 patch-target convention (4 groups: HTTP-layer / store-level-injection / chunk-loop-level / call-argument-capture) is followed correctly and consistently across all three test files — verified by reading each `patch(...)` target against the declared group assignment.
- Minor deviation: `_credentials(store_type)` is defined as a bare module-level function in both new commands, whereas the existing `backfill_missing_orders.py:62` and `repair_refunds.py:42` define the same helper as a `Command` method (`self._credentials`). Functionally equivalent, stylistically inconsistent with the two closest precedents in the same package. Non-blocking.
- `.moai/project/scheduled-jobs.md` still lists only `sync_orders`/`sync_exchange_rates` (confirmed by reading) — `sync_order_cancellations`/`backfill_order_cancellations` are not yet registered there. This is **explicitly deferred** by acceptance.md's own DoD ("`.moai/project/scheduled-jobs.md`에 3번째 작업 추가는 `/moai sync` 단계에서 수행") — flagged as an open item for the sync phase, not a run-phase defect.

---

### Findings (ranked by severity)

- **[HIGH, blocking]** `backend/order/shopify_orders.py:557-569` — `_is_lock_wait_timeout()` classifies by unscoped substring match on `str(exc)` without checking exception type. Demonstrated by direct execution: a `ValueError`/`KeyError` whose message coincidentally contains `"1205"` is misclassified `lock_timeout=True`, silently downgrading what should be a hard failure (`CommandError`, REQ-CANC-017) into a suppressed soft failure (REQ-CANC-026) with no operator alert beyond a stderr log line that's easy to miss in an unattended scheduled job. Failure scenario: a genuine, unrelated bug in the reconciliation path (e.g., a DB schema drift, a malformed Shopify payload causing a `KeyError`) whose message happens to contain the substring "1205" or a coincidental order id fragment would be silently absorbed as "self-healing" and never surface — the exact "ExchangeRate incident" failure mode (silent stoppage) the SPEC's own D10 rationale explicitly tries to guard against on the *other* side of this tradeoff.

- **[MEDIUM, non-blocking]** `backend/order/shopify_orders.py:631` — the diff check gating `changed.append()`/`bulk_update()` (`if order.cancelled_at != new_cancelled or order.closed_at != new_closed:`) has zero test coverage for its negative case. Mutating it to `if True:` (always treat as changed, always write) passes all 27 tests. Current shipped behavior is correct (the check IS present), but a future regression removing it would go undetected, silently inflating the `changed=N`/`would_change=N` diagnostic counts and causing every candidate order to be written on every cycle instead of only the ones that actually changed.

- **[LOW, non-blocking]** `backend/order/tests/test_sync_order_cancellations_command.py:116-135` — AC-CANC-016 is filed under the command test file/section but calls `reconcile_order_status_for_ids()` directly rather than `call_command()`. Matches `acceptance.md`'s own literal Given/When/Then text (the divergence is inherited from the SPEC document's own internal file/section-vs-body inconsistency, not an implementation shortcut) and was proactively disclosed. Residual gap is narrow: no test exercises same-store multi-chunk partial success through `call_command()` specifically (cross-store is covered via AC-CANC-017 scenario 2).

- **[LOW, non-blocking]** `ruff check` fails with 20 violations attributable to new SPEC-029 code (7 implementation: `shopify_orders.py:541,579,597,629`, `sync_order_cancellations.py:54,62,77`; 13 test-file E501/I001). Verified against the project's own configured gate (`pyproject.toml:32-38`) and against a clean baseline file in the same directory. 3 are auto-fixable (`--fix`); the rest need manual line wrapping.

- **[INFO, non-blocking, expected-pending]** `.moai/project/scheduled-jobs.md` not yet updated with the new commands, and no evidence of actual Windows Task Scheduler registration (REQ-CANC-021/027 are DoD-only, not AC-verifiable) — explicitly deferred to the `/moai sync` phase per acceptance.md's own DoD section, confirmed still pending by reading the file.

---

### Recommendations

- Gate `_is_lock_wait_timeout()` behind `isinstance(exc, django.db.utils.OperationalError)` before the string match, and prefer checking `exc.args[0] == 1205` over a bare substring check on the full message.
- Add an AC (or extend an existing one) asserting that a record whose Shopify-returned values already match the stored values does **not** appear in `changed` and does **not** trigger a `bulk_update()` write — closes the M-diffcheck gap.
- Run `ruff check --fix` for the 3 auto-fixable import-sort issues, and manually wrap the remaining 17 long lines, before merge.
- When registering the Windows scheduled tasks (deferred to `/moai sync`), verify the actual `-At` trigger offset per REQ-CANC-027's DoD item, and update `.moai/project/scheduled-jobs.md` per the SPEC's own DoD checklist.

---

### Working tree verification

```
$ git status --porcelain | grep order
 M backend/order/shopify_orders.py
?? backend/order/management/commands/backfill_order_cancellations.py
?? backend/order/management/commands/sync_order_cancellations.py
?? backend/order/tests/test_backfill_order_cancellations_command.py
?? backend/order/tests/test_spec_029.py
?? backend/order/tests/test_sync_order_cancellations_command.py

$ git diff --stat backend/order/shopify_orders.py
 backend/order/shopify_orders.py | 200 ++++++++++++++++++++++++++++++++++++++++
 1 file changed, 200 insertions(+)

$ grep -rn "MUTATION" backend/order/
(no matches)
```

Identical to the state at the start of this evaluation (the pre-existing `+200/-0` diff on `shopify_orders.py` and the 5 new untracked files). All mutations applied during this evaluation were reverted, verified by test re-run (27/27 passing) and by the absence of any leftover mutation markers.

Final regression confirmation (executed): `python -m pytest order/tests/test_spec_029.py order/tests/test_sync_order_cancellations_command.py order/tests/test_backfill_order_cancellations_command.py --no-cov -q` → `27 passed in 135.44s`.
