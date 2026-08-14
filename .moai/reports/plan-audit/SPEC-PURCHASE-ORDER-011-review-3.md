# SPEC Review Report: SPEC-PURCHASE-ORDER-011
Iteration: 3/3 (final)
Verdict: FAIL
Overall Score: 0.78

Reasoning context ignored per M1 Context Isolation. This audit is based solely on the four documents
in `.moai/specs/SPEC-PURCHASE-ORDER-011/` at v1.3.0 (spec.md, plan.md, acceptance.md,
spec-compact.md) and on direct reading of every cited source file in `backend/` and `frontend/`. The
iteration-1 and iteration-2 reports were opened only to run the regression check; no "RESOLVED"
claim below is taken from them or from the SPEC's own HISTORY — every one was re-derived from the
current documents and the current source.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  Base series `REQ-DEX-001`..`REQ-DEX-013` at spec.md:131, 135, 137, 141, 143, 147, 153, 157, 159,
  169, 171, 179, 173 — 13 entries, no gaps, no duplicates, uniform 3-digit padding. Eleven alphabetic
  suffixes (`005a` L145, `006a` L149, `006b` L151, `009a` L161, `009b` L163, `009c` L165, `009d`
  L167, `012a` L181, `012b` L183, `012c` L185, `013a` L175) are declared and justified at
  spec.md:127. Total 24, matching spec.md:22, spec-compact.md:32, plan.md:11 and acceptance.md:210.
  AC IDs at spec.md:215-267 total 27 with no duplicates, matching spec-compact.md:32 and
  acceptance.md:210. HISTORY arithmetic at spec.md:22 ("22 → 24", "25 → 27") is correct.
  Presentation note (not an MP-1 failure): REQ-DEX-013/013a are printed *before* REQ-DEX-012
  (L173/175 vs L179) because they were folded into the "파손 신고 제출 및 Order 집계 영향" section to
  hold the module count at ≤5, a choice explicitly recorded at spec.md:22. Numbering is complete and
  consistent; only the reading order is non-monotonic. Same for 시나리오 13/13a at acceptance.md:135-145,
  placed before 시나리오 12.

- **[PASS] MP-2 EARS format compliance**
  All 24 REQs (spec.md:131-185) and all 27 ACs (spec.md:215-267) were read individually, not sampled.
  Every one matches exactly one of the five patterns; the "Given…when…the system shall" hybrid is
  absent throughout. The four items rewritten this round hold up:
  - REQ-DEX-006b (L151) now reads "If a LineItem … has `sku IS NULL` … **then the system shall NOT
    include** that LineItem's `quantity`…" — D19's passive subject is genuinely fixed.
  - REQ-DEX-009d (L167) "If the REQ-DEX-009c short-circuit evaluates for an Order, then the system
    shall continue to compute that Order's `status` field using the existing, unmodified
    `logistics_status` aggregate rule" — valid Unwanted.
  - REQ-DEX-013 (L173) "When the backfill migration is applied, the system shall recompute…" — valid
    Event-Driven.
  - REQ-DEX-013a (L175) "If an Order in the backfill's scope does not contain any `damaged_exchange`
    LineItem, then **the backfill** shall leave…" — valid If/then structure, so MP-2 stands, but the
    subject is "the backfill", not "the system", which contradicts the document's own claim at
    spec.md:127 (see D26). Same for AC-DEX-013a (L267).

- **[PASS] MP-3 YAML frontmatter validity**
  `id: SPEC-PURCHASE-ORDER-011` (spec.md:2), `version: 1.3.0` (L3), `status: draft` (L4),
  `created_at: 2026-08-14` (L5), `priority: High` (L8), `labels: [purchase-order, damaged-exchange,
  reorder-queue, frontend]` (L10, array). All six required fields present with correct types.
  `issue_number: 0` (L9) is not an MP-3 required field; rebuttal accepted in iteration 2, not
  re-raised.

- **[N/A] MP-4 Section 22 language neutrality**
  N/A: single-stack SPEC (Django/DRF + React/TS). No multi-language tooling content in any document.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements a reasonable engineer would resolve consistently | REQ-DEX-013a (spec.md:175) "shall leave that Order's `ready_to_ship` value exactly as already computed by the pre-existing REQ-RTS-002 rule" admits two readings — "don't write the row" vs "recompute with the old rule and get the same answer". The planned migration (plan.md:109-133) writes *every* in-scope Order, so only the second reading is satisfiable; the AC's fixture ("already correct under the existing rule", spec.md:267) makes the two coincide, so nothing fails, but the requirement text does not say which is meant (D28). The D16 correction is applied at spec.md:115, :167 and :197 but **not** at spec.md:41 ("`Order.status`(물류 집계)는 건드리지 않는다") or spec.md:50 ("`Order.status`는 무변경") — the two prose summaries still carry the literally-false wording D16 was raised about (D27). Counterweight: REQ-DEX-009d (L167), 결정 E (L115) and the Exclusions entry (L197) now state the rule/column distinction precisely and correctly |
| Completeness | 0.90 | 1.0 band, one step down for residual factual imprecision | All required sections present: HISTORY (L17-22), 문제 정의 (L26-32), 솔루션 개요 (L34-43), 범위 (L45-51), 가정 (L53-58), 설계 결정 A-F (L60-123), REQUIREMENTS (L125-185), Exclusions (L189-200, 10 entries, all concrete), 관련 SPEC (L202-207), ACCEPTANCE CRITERIA (L211-267). The D13 hole is genuinely filled (REQ-DEX-013/013a + AC-DEX-013/013a + 결정 F + plan.md M4.6 + plan.md:104-136 + acceptance.md:133-145/197/200/209/216). The downstream-consumer enumeration at spec.md:107-113 is now complete — `OrderResyncView` added and verified at `backend/order/views.py:188`, route `backend/order/urls.py:58`, serializer reuse at `views.py:229`. Deductions: "`TestRecomputeOrderAggregatesReadyToShip`(9개 테스트)" is wrong — the class has 10 (D25); acceptance.md:197's "0033 선례와 동일하게 … 쿼리 수 테스트" implies a precedent that does not exist (D29) |
| Testability | 0.65 | between 0.50 and 0.75 — 25 of 27 ACs are binary and discriminating; two are not | AC-DEX-012e (spec.md:261 / acceptance.md:179-183) asserts an output `VendorComparisonView` does not produce: the response dict at `purchase_order_views.py:808-831` contains no LineItem quantity field at all, and with the AC's own fixture the only quantity-dependent outputs (`selected_distributor`/`candidate_basis`, via `auto_select_distributor`, `excel_utils.py:553-569`) are identical whether the aggregate reads `10` or `3`. Not executable, not discriminating (D23, blocking). AC-DEX-013 (spec.md:265 / acceptance.md:137) does not pin the `damaged_exchange` row's `logistics_status`, so a backfill that copies 0033 verbatim without the new short-circuit survives under a `not_shipped` fixture (D24). Counterweight: AC-DEX-009c and AC-DEX-005c are now genuinely discriminating — traces below — and AC-DEX-009, 012b, 012d, 010, 008 each enumerate the wrong answer explicitly |
| Traceability | 1.00 | 1.0 — every REQ has ≥1 AC, every AC references an existing REQ, no orphans | All 24 REQs covered: 001→AC-001; 002,003→AC-002; 004→AC-003; 005→AC-004; 005a→AC-004a; 006→AC-005,005a,005c; 006a→AC-006; 006b→AC-005b; 007→AC-007; 008→AC-008; 009→AC-009; 009a→AC-009a; 009b→AC-009b; 009c→AC-009,AC-009c; 009d→AC-009c; 010→AC-010; 011→AC-011; 012→AC-012,012a,012b; 012a→AC-012c; 012b→AC-012d,012e; 012c→AC-012f; 013→AC-013; 013a→AC-013a. All 27 `Traces:` targets exist. acceptance.md maps 27 시나리오 1:1 onto the 27 ACs (1,2,3,4,4b,5,5a,5b,5c,6,7,8,9,9a,9b,9c,10,11,13,13a,12,12b,12c,12d,12e,12f,12g) with no orphan and no dangling ID; the 12x→012(x-1) offset is preserved exactly |

---

## Priority 1 — Are the four iteration-2 blockers genuinely resolved?

### D13 (backfill migration) — **RESOLVED at requirement level; its acceptance criterion is under-pinned (D24)**

*Requirement present and correctly shaped.* REQ-DEX-013 (spec.md:173) + REQ-DEX-013a (L175) + 결정 F
(L119-123) + Exclusions/관련 SPEC updates (L113, L205) + plan.md M4.6 (L21), file plan (L38),
algorithm (L104-136), execution constraint (L161), risk entry (L177) + acceptance.md 시나리오 13/13a
(L135-145), quality gate (L197, L200), DoD (L209, L216).

*Does AC-DEX-013 fail if the migration is omitted?* **Yes.** The fixture pins a stored
`ready_to_ship=True` on an Order that owns a `damaged_exchange` LineItem and asserts `False` after
the migration runs. With no migration the stored value cannot change — nothing else in this SPEC
touches that Order (REQ-DEX-006a, spec.md:149, explicitly forbids the search page from recomputing).
Mutant "migration absent" is caught.

*Is the migration's shape consistent with the 0033 precedent?* **Yes — verified line by line against
`backend/order/migrations/0033_backfill_order_ready_to_ship.py`.*

| 0033 (actual) | plan.md:109-133 (planned) | Match |
|---|---|---|
| `LineItem.objects.filter(sku__isnull=False).values_list("order_id","purchase_status","logistics_status")` (L40-42) | identical (L113-115) | yes |
| group into `items_by_order` as `(purchase_status, logistics_status)` (L44-46) | identical (L116-118) | yes |
| `non_cancelled = [it for it in items if it[0] != "order_cancelled"]` (L53) | identical (L122) | yes |
| `if not non_cancelled: None` (L54-55) | identical (L123-124) | yes |
| `elif any(ps == "cs_required" …)` (L56-57) | `elif any(ps in ("cs_required","damaged_exchange") …)` (L125-126) | intended divergence — the whole point |
| `all(ls == "received" or ps == "in_stock" for ps, ls in non_cancelled)` (L59-62) | identical, same tuple order (L128-130) | yes |
| `Order.objects.bulk_update(to_update, ["ready_to_ship"])` (L65) | identical (L133) | yes |
| `RunPython(fn, RunPython.noop)` (L75), does not import `purchase_order_views` | stated verbatim at plan.md:136 | yes |
| scope = Orders with ≥1 trackable LineItem (0033 header L24-28) | stated at plan.md:38 | yes |

Tuple-unpacking order is correct in the planned pseudocode (`for ps, ls in non_cancelled` against
tuples appended as `(purchase_status, logistics_status)`) — I checked this specifically because it is
the easiest silent error to make when copying 0033. Only deviation: 0033's `if not items_by_order:
return` early exit (L48-49) is absent from the pseudocode; `bulk_update([])` is a no-op in Django, so
this is harmless. The test harness precedent
(`backend/order/tests/test_backfill_order_ready_to_ship_migration.py:24-29`, `MigrationLoader` +
`operation.code(global_apps, None)`) makes AC-DEX-013/013a mechanically implementable.

*Deployment-ordering check the SPEC does not make but I did:* the migration re-implements the rule
itself, so it is correct regardless of whether it runs before or after the new runtime code is live.
No gap.

### D14 (AC-DEX-009c discrimination) — **RESOLVED**

Actual predicate, `backend/order/purchase_order_views.py:176-185`:

```python
non_cancelled = [it for it in (items or []) if it[1] != "order_cancelled"]
if not non_cancelled:
    ready_to_ship = None
elif any(purchase_status == "cs_required" for _, purchase_status in non_cancelled):
    ready_to_ship = False
else:
    ready_to_ship = all(
        logistics_status == "received" or purchase_status == "in_stock"
        for logistics_status, purchase_status in non_cancelled
    )
```

New fixture (spec.md:245 **and** acceptance.md:117, now identical): row (a)
`purchase_status="damaged_exchange"`, `logistics_status="received"`; row (b)
`purchase_status="unordered"`, `logistics_status="received"`.

| Implementation | `all(...)` result | AC-DEX-009c outcome |
|---|---|---|
| recompute **without** the new branch | (a) received ✓, (b) received ✓ → **True** | expects False → **fails** ✓ |
| recompute **with** the REQ-DEX-009c short-circuit | intercepted before `all(...)` → **False** | **passes** ✓ |

So yes — AC-DEX-009c now fails against an implementation that calls the recompute without the
`damaged_exchange` branch. That was the exact question, and the answer is affirmative. The v1.2.0
`not_shipped` fixture that made the criterion vacuous is gone from both documents. The added `status`
clause is also satisfiable: with both rows `received`, `status` = `"received"` via
`purchase_order_views.py:171-172`.

### D20 (AC-DEX-005c discrimination) — **RESOLVED**

New fixture (spec.md:231 and acceptance.md:73, identical): the parent Order's trackable non-cancelled
LineItems are **all** `quantity=null`, expected 전체 출고 수량 = `0`, explicitly "not `null`/`None`".
`LineItem.quantity` is `models.IntegerField(null=True, blank=True)` (`backend/order/models.py:174`),
so the fixture is constructible. A bare `Sum("quantity")` over a group whose every row is NULL
returns SQL NULL → Django yields `None` → the criterion's "not `null`/`None`" clause fails.
`Coalesce(Sum("quantity"), 0)` (plan.md:55) yields `0` → passes. Yes: AC-DEX-005c now fails against a
bare `Sum("quantity")` with no `Coalesce`. The non-discriminating mixed-null assertion was removed,
not merely supplemented.

### D21 (AC-DEX-012e) — **PARTIALLY RESOLVED — the fixture is fixed, the assertion is not (D23)**

The linkage half is genuinely fixed: `purchase_orders__isnull=True` is now pinned in spec.md:261 and
acceptance.md:181, the `VendorComparison` record precondition is stated (correct —
`purchase_order_views.py:725` and :753 iterate over `VendorComparison.objects.all()`, so an
unreferenced SKU never appears), REQ-DEX-012b's coverage claim is qualified at spec.md:183, and the
PO-linked case is recorded as a known gap at spec.md:199 and plan.md:153/179. Against
`purchase_order_views.py:744-750` (`filter(purchase_orders__isnull=True, sku__isnull=False)
.values("sku").annotate(total=Sum("quantity"))`) and the `qty_by_sku.get(isbn, 0)` fallback at L757,
all of that is accurate.

**But the criterion is still not satisfiable by a correct implementation, for a different reason
neither prior iteration caught.** `VendorComparisonView` never returns the quantity. `total_qty` is
consumed only at L773 as an argument to `auto_select_distributor`; the response rows built at
L808-831 contain `sku`, the Booxen/Kyobo columns, `selected_distributor`, `candidate_basis`,
`price_diff`, `price_diff_alert` — and nothing else. There is no field in which "a quantity based on
`quantity` (`10`)" can be observed. See D23.

---

## Defects Found

**D23. spec.md:261 / acceptance.md:179-183 — AC-DEX-012e asserts an output `VendorComparisonView`
does not produce, and its fixture cannot discriminate `10` from `3` indirectly either. — Severity:
major (blocking as an acceptance criterion)**

The criterion reads "…then the system shall report a quantity based on `quantity` (`10`) via its
`Sum("quantity")` aggregation, not `damaged_quantity` (`3`)". Verified against source:

- `purchase_order_views.py:744-750` computes `qty_by_sku`; L757 reads `total_qty = qty_by_sku.get(isbn, 0)`.
- L771-778 passes it into `auto_select_distributor` only.
- L808-831 builds the response row — **no quantity key of any kind**; L833 returns
  `{"count": len(results), "results": results}`.

So no black-box assertion of "10" is possible. The only indirect channel is
`selected_distributor`/`candidate_basis`, and `excel_utils.py:553-569` uses `total_qty` solely in
threshold comparisons (`korea_stock >= total_qty`, `bs_stock >= total_qty`, `ky_stock >= total_qty`).
With the fixture the AC actually specifies — one LineItem plus a bare `VendorComparison` record, no
`BooxenData`/`KyoboData`/`WarehouseStock`/`DistributorVendorRule` — every stock is `0`, so both
`10` and `3` fall through to `_no_stock_logic` and produce the identical result. The criterion is
simultaneously unassertable and non-discriminating.

Fix (either is acceptable): (a) restate it as a white-box criterion on the aggregation itself — "the
`sku`→quantity map the view builds shall total `10`" — matching how it is actually verifiable; or
(b) keep it black-box and pin a `WarehouseStock` row with `korea=5` for that SKU, so `total_qty=3`
would yield `candidate_basis="재고우선"`/`selected_distributor="warehouse"` while `total_qty=10`
would not, and assert the latter; or (c) delete AC-DEX-012e and rely on the diff-level Exclusions
check already stated at acceptance.md:201, recording the reduction explicitly. Note this AC covers a
view this SPEC does not modify, so option (c) carries little real risk — but leaving the criterion as
written guarantees an implementer writes either a fabricated or a vacuous test.

**D24. spec.md:265 / acceptance.md:137 — AC-DEX-013 does not pin the `damaged_exchange` row's
`logistics_status`, so a backfill that copies 0033 without the new short-circuit can survive. —
Severity: major**

Mutation test against the criterion as written ("a fixture Order with a `damaged_exchange` LineItem
(trackable, non-cancelled) whose stored `ready_to_ship=True` was computed under the pre-migration
rule"):

| Migration implementation | fixture `logistics_status="received"` | fixture `logistics_status="not_shipped"` |
|---|---|---|
| absent | stays `True` → **fails** ✓ | stays `True` → **fails** ✓ |
| present, 0033 rule copied verbatim (no `damaged_exchange` branch) | `all(...)` → `True` → **fails** ✓ | `all(...)` → `False` → **passes** ✗ |
| present, new rule | `False` → passes ✓ | `False` → passes ✓ |

The stored value must be set by hand in the test (the pre-migration rule no longer exists in code by
the time M4.6 runs, per plan.md:21), so nothing forces the author's fixture to be consistent with the
stated provenance. Strictly, "computed under the pre-migration rule" *implies* `received` — for a
`damaged_exchange` row the old rule yields `True` only via the `logistics_status == "received"`
disjunct — so a careful author derives it. But this is precisely the implicit-derivation trap D14 was
raised for one round ago, and v1.3.0 fixed D14 by making the pin explicit while leaving the new AC
implicit. Fix: add `logistics_status="received"` to the damaged row in spec.md:265 and
acceptance.md:137, exactly as was done for AC-DEX-009c.

Related, minor: AC-DEX-013a (spec.md:267 / acceptance.md:143) does not pin `sku` not null on the
second Order's `in_stock` LineItem. With `sku=null` that Order falls outside
`filter(sku__isnull=False)` entirely and is never written, so the criterion passes vacuously instead
of demonstrating the intended "processing one Order does not disturb another". REQ-DEX-013a's
"in the backfill's scope" (spec.md:175) implies it; the AC should say it.

**D25. spec.md:117, plan.md:16, acceptance.md:195, spec-compact.md:64 — "9개 테스트" is wrong; the
class has 10. — Severity: minor**

`backend/order/tests/test_spec_012.py` `TestRecomputeOrderAggregatesReadyToShip` (class at L168,
ends L285) contains ten test methods: L169 `test_all_cancelled_sets_null`, L179
`test_zero_trackable_lineitems_sets_null`, L187 `test_cs_required_hard_blocks_to_false`, L200
`test_cancelled_items_excluded_from_cs_check`, L213 `test_in_stock_alone_satisfies_true`, L227
`test_received_alone_satisfies_true`, L241 `test_partial_satisfaction_sets_false`, L258
`test_status_and_ready_to_ship_computed_together`, L273
`test_noop_on_empty_order_ids_issues_zero_queries`, L278
`test_recompute_overwrites_stale_ready_to_ship`. The iteration-2 report enumerated nine (it omitted
L273) and the SPEC adopted that number as verified fact in four places. The substantive claim — that
all three pre-existing branches are frozen by this suite — is **true** (null: L169/L179;
`cs_required`: L187; `all(received/in_stock)`: L213/L227/L241), and the "damaged_exchange appears
nowhere in this file" claim is **true** (`grep -c damaged_exchange` = 0). Only the count is wrong.

**D26. spec.md:127 vs spec.md:175 and spec.md:267 — the "(Unwanted) 항목은 전량 시스템을 주어로
삼는다" claim is contradicted by the two requirements added in the same revision. — Severity: minor**

spec.md:127 asserts every `(Unwanted)` item takes "the system" as subject and cites the v1.3.0
REQ-DEX-006b fix as proof. REQ-DEX-013a (L175) reads "then **the backfill** shall leave…" and
AC-DEX-013a (L267) "then **the backfill** shall NOT change…". This is D19 re-introduced in the same
pass that closed it. Structurally still valid EARS, so not MP-2; but the self-referential claim is
now false. Fix either the two new items or the claim.

**D27. spec.md:41 and spec.md:50 vs spec.md:115/167/197 — the D16 correction was applied to the
normative text but not to the two prose summaries. — Severity: minor**

`_recompute_order_aggregates` writes `status` and `ready_to_ship` in one UPDATE
(`purchase_order_views.py:188-195`), so the new 9th caller does write `status` every time. v1.3.0
correctly restates this at 결정 E (spec.md:115), REQ-DEX-009d (L167) and the Exclusions entry (L197).
But 솔루션 개요 #6 (L41) still says "`Order.status`(물류 집계)는 건드리지 않는다" and 범위 (L50) still
says "`Order.status`는 무변경" — the exact wording D16 was raised against. An implementer reading the
summary first may still reach for an `update_fields` carve-out, which plan.md:102 forbids.

**D28. spec.md:175 (REQ-DEX-013a) — ambiguous between "does not write the row" and "writes the same
value". — Severity: minor**

"the backfill shall leave that Order's `ready_to_ship` value exactly as already computed by the
pre-existing REQ-RTS-002 rule" is satisfiable only under the second reading, because the planned
migration (plan.md:120-133, mirroring 0033) appends *every* in-scope Order to `to_update` and
bulk-updates all of them. A consequence nothing in the SPEC states: the backfill will also silently
overwrite stale `ready_to_ship` values on Orders that have no `damaged_exchange` LineItem at all
(0033 behaves identically, so this is precedent-consistent — but it is an undocumented side effect of
a data migration). AC-DEX-013a's fixture pins "already correct under the existing rule", so no
correct implementation fails; this is a wording/documentation gap, not a testability failure.

**D29. acceptance.md:197 — "0033 선례와 동일하게 … 고정된 쿼리 수 … 테스트 최소 1건 포함" implies a
precedent test that does not exist. — Severity: minor**

`backend/order/tests/test_backfill_order_ready_to_ship_migration.py` contains eight tests (L36, 50,
68, 86, 104, 118, 128, 138) and **no** query-count test. The batch *design* is the precedent; the
test is new. Also, strictly, `bulk_update` batches by `batch_size`, so "Order 수와 무관하게 고정된
쿼리 수" holds only within one batch — the same imprecision 0033 carries, harmless at test-fixture
scale, but the criterion should say "does not grow per Order" rather than "fixed".

**D30. acceptance.md:199 / plan.md:24 — the regression additions for `OrderResyncView` do not
actually exercise `ready_to_ship`. — Severity: minor**

Verified: `grep -c ready_to_ship backend/order/tests/test_order_resync.py` = **0**, and
`test_spec_012.py:609 test_resync_does_not_change_ready_to_ship` tests
`order.shopify_orders._sync_single_order` directly, not the `OrderResyncView` endpoint (the endpoint
calls `sync_single_order_from_shopify`, `backend/order/views.py:212`). Both suites are legitimate
"must still pass" regressions, but neither confirms the `ready_to_ship` consumption path the D15
remedy claims they confirm. Low impact — the view reuses `OrderDetailSerializer` verbatim
(`views.py:229`), which `test_order_detail.py`-class coverage already exercises.

**D31. spec.md:127 vs spec.md:147 — "REQUIREMENTS는 … 파일:라인 인용을 담지 않는다" is not quite
true. — Severity: minor**

The D18 remedy did move the file:line paragraphs out of REQ-DEX-009c/012b/012c (verified: L165, L183,
L185 now defer to plan.md, and plan.md:151/153/195/197 carry the citations). But REQ-DEX-006 (L147)
still cites "`models.py:221`" inline, and REQ-DEX-012a/012b/012c still name concrete classes
(`RunComparisonView`, `VendorComparisonView`, `ConfirmOrderView`, `UnorderedItemsView`), which
spec.md:42 assigns to plan.md. Substantially resolved; the absolute claim at L127 overstates it.

**D32. Cosmetic (carried from iteration-2 recommendation 11, now regressed) — inline audit history
inside normative text has increased, not decreased.** Review annotations now appear inside
requirement and criterion bodies at spec.md:151, 167, 183, 231, 245, 261, 265, 267 and
acceptance.md:71-75, 115-119, 179-183. HISTORY (spec.md:22) already records all of it. The
*substantive* "an implementation that … fails this criterion" clauses should stay — they are what
makes the criteria auditable — but "(v1.3.0 D19 — subject corrected to 'the system')" inside a
requirement is provenance, not requirement.

---

## Chain-of-Verification Pass

Second-look findings. D23 was found only on the second pass, by asking a question neither of my two
prior reports asked: *what does this endpoint actually return?* Iteration 2 asserted "fixture unlinked
→ view reports `10`; criterion passes" — that assertion was wrong, and I carried it forward into
iteration 3's first pass before checking it. D25 was found by counting the test methods instead of
trusting my own iteration-2 enumeration.

- **Re-read all 24 REQ entries end-to-end** (spec.md:131-185), not a sample. This surfaced D26
  (the `(Unwanted)` subject claim broken by the two brand-new requirements) and D31.
- **Ran the mutation ("most plausible wrong implementation") test on every AC that is new or changed
  since iteration 2** — AC-DEX-005c, 009c, 012e, 013, 013a, plus the ACs touched by the REQ rewrites
  (AC-DEX-006, 009, 012d, 012f). Results: 005c discriminates (bare `Sum` → `None`); 009c
  discriminates (unmodified rule → `True`); 013 discriminates against omission but not against a
  0033-verbatim copy under one fixture choice (D24); 013a discriminates against a "set everything
  False" mutant but is vacuous if `sku` is null; 012e discriminates against nothing (D23).
- **Checked observability at every one of the six no-change sites in AC-DEX-012d/012e/012f, not just
  the one I suspected.** `RunComparisonView` exposes `total_qty` and per-row `quantity`
  (`purchase_order_views.py:585-591`, response at :671/:690) ✓; `DailyReviewExcelView` emits
  `"quantity": li.quantity or 0` (:1143) ✓; `UploadDailyReviewView` writes `quantity=total_qty` to
  the PurchaseOrder (:1555) and echoes it in the response (:1574) ✓; `GenerateOrderFileView`
  accumulates into `found_map[sku]["total_quantity"]` (:398-404) ✓; `ConfirmOrderView` reads
  `item.get("quantity")` from the body (:886) ✓; `VendorComparisonView` — **not exposed** (D23).
  AC-DEX-012d and AC-DEX-012f are therefore sound; only AC-DEX-012e is not.
- **Re-verified REQ→AC and AC→REQ for all 24 REQs and all 27 ACs individually**, plus all 27
  acceptance.md 시나리오→AC mappings and the four count assertions (spec.md:22, spec-compact.md:32,
  plan.md:11, acceptance.md:193/210). No orphan, no dangling ID, no count drift. The 12x→012(x-1)
  offset introduced in v1.1.0 is still consistent after inserting 13/13a.
- **Re-read the Exclusions section for specificity, not presence** (spec.md:189-200): 10 entries, all
  concrete; the new D21 entry (L199) accurately describes `purchase_orders__isnull=True` with no
  `damaged_exchange` exception and correctly contrasts it with `_reorder_candidate_filter`. Verified
  against `purchase_order_views.py:107-110` (the filter, which *does* admit damaged rows) and
  :372-381 (the REQ-DMG-008 comment). Checked for the converse hole — an exclusion that contradicts an
  included requirement — and found none: the `Order.status` exclusion (L197) is now rule-scoped and
  agrees with REQ-DEX-009d.
- **Looked for contradictions introduced by the insertion of 013/013a**, not just within single
  requirements: REQ-DEX-013 (migration recomputes) vs REQ-DEX-006a (page must not recompute) — no
  conflict, different actors; REQ-DEX-013 vs the Exclusions `Order.status` entry — no conflict, the
  migration's `bulk_update` touches only `ready_to_ship`; 결정 F vs 결정 E — consistent. The only
  contradictions found are D26, D27, D31.
- **Re-opened every file:line citation, including all v1.3.0 additions**, rather than trusting the
  prior reports: `purchase_order_views.py` :86-110/:93-110, :113-122 (fan-in comment naming exactly
  the 8 callers), :123-195, :154-158, :167-173, :175-186, :176, :179-180, :182-185, :188-195, :251,
  :292, :372-381, :398, :580, :744-750, :744-757, :808-833, :884-886, :1084, :1099-1100, :1451,
  :1555/:1574, :1863-1900/:1892; `models.py` :150-165 (choices incl. `damaged_exchange`), :174
  (`quantity` nullable), :221 (`shipped_quantity`); `serializers.py` :141 + `"ready_to_ship"` at
  :170, :14-36 (no exposure — negative claim correct); `views.py` :188 (`OrderResyncView`), :229
  (`serializer = OrderDetailSerializer(order)`); `urls.py` :58 (`orders/<int:pk>/sync/`);
  `test_spec_012.py` :168-285 and :609; `test_backfill_order_ready_to_ship_migration.py` :24-29;
  `migrations/0033_backfill_order_ready_to_ship.py` :36-65 (rule at :53-63); latest migration is
  `0036_order_name_index.py` ✓; `OrderDetailPage.tsx` :240-260 (the 3-state badge); `router/index.tsx`
  :122-128 (`/outbound` lazy route); `Sidebar.tsx` :3 (lucide import), :37 (`flatNavItems`), :71
  ('출고 처리', block :68-74). **Zero fabricated paths and zero wrong line numbers across all four
  documents, including every citation added this round.** Fourth consecutive clean citation audit —
  the only factual errors this round are counts and claims about content (D25, D29, D30), not paths.
- **Independently re-checked the greps the SPEC asserts:** `test_spec_012.py` `damaged_exchange` = 0
  (spec.md:117 correct); `test_daily_review_upload.py` `damaged_exchange` = 25, `ready_to_ship` = 0
  (acceptance.md:199 correct); `test_order_resync.py` `ready_to_ship` = 0 (contradicts the D15 claim
  — D30); 8 `_recompute_order_aggregates` invocation lines in production code (:1014, :1640, :1773,
  :1840, :1892, :1950, :1999, :2057), matching the "fan-in 8→9" claim at spec.md:95-105.

---

## Regression Check (defects from iteration 2)

| # | Description | Status | Evidence |
|---|---|---|---|
| D13 | No `ready_to_ship` backfill requirement and no exclusion | **RESOLVED** (its AC is weak — D24) | REQ-DEX-013/013a (spec.md:173-175), 결정 F (L119-123), AC-DEX-013/013a (L265-267), 시나리오 13/13a (acceptance.md:135-145), plan.md M4.6 (L21) + algorithm (L104-136) + file plan (L38). Shape re-derived against 0033 line by line — table above. Migration-0033 divergence now documented at spec.md:113 and :205 |
| D14 | AC-DEX-009c non-discriminating (`not_shipped` fixture) | **RESOLVED** | `logistics_status="received"` pinned in both spec.md:245 and acceptance.md:117; discrimination re-derived from `purchase_order_views.py:176-185` — unmodified rule yields `True`, modified yields `False` |
| D15 | `OrderResyncView` missing from consumer list | **RESOLVED** | spec.md:109, plan.md:199, plan.md:24/175, acceptance.md:199/212. All three citations (`views.py:188`, `views.py:229`, `urls.py:58`) verified exact. Residual: the added regression tests don't assert `ready_to_ship` (D30) |
| D16 | "shall NOT modify `Order.status`" literally false | **RESOLVED** in normative text | spec.md:167 restates it as a rule-level statement; 결정 E (L115) and Exclusions (L197) match; plan.md:20/102 and acceptance.md:119/201 carry the same correction. Residual: spec.md:41 and :50 not updated (D27) |
| D17 | `test_daily_review_upload.py` missing from regression set | **RESOLVED** | acceptance.md:199, plan.md:24, DoD acceptance.md:212. Counts (25 `damaged_exchange`, 0 `ready_to_ship`) independently verified |
| D18 | file:line paragraphs inside REQUIREMENTS | **RESOLVED** substantially | REQ-DEX-009c (L165), 012b (L183), 012c (L185) now defer to plan.md; citations landed at plan.md:151/153/195/197. Residual: `models.py:221` at spec.md:147, class names still in 012a/012b/012c (D31) |
| D19 | REQ-DEX-006b passive subject | **RESOLVED**, but re-introduced elsewhere | spec.md:151 fixed; REQ-DEX-013a (L175) and AC-DEX-013a (L267) added in the same pass with "the backfill" as subject (D26) |
| D20 | AC-DEX-005c non-discriminating (mixed-null) | **RESOLVED** | All-null fixture with expected `0` in spec.md:231 and acceptance.md:73; `quantity` verified nullable at `models.py:174`; SQL `SUM` over an all-NULL group returns NULL, so a `Coalesce`-less implementation now fails |
| D21 | AC-DEX-012e unpinned PO linkage | **PARTIALLY RESOLVED** | Linkage pinned (spec.md:261, acceptance.md:181), `VendorComparison` precondition correct, gap recorded in Exclusions (L199) and plan.md:153/179. But the assertion targets an output the view does not emit (D23) |
| D22 | Characterization-test requirement under-specified / duplicative | **RESOLVED** | spec.md:117, plan.md:16, acceptance.md:195, spec-compact.md:64 all name the existing `TestRecomputeOrderAggregatesReadyToShip` suite, state all three branches, and say "확인, 신규 작성 아님". Residual: test count off by one (D25) |

No stagnation: all ten iteration-2 defects changed state, eight fully resolved, two partially. No
defect has now appeared unchanged in three consecutive iterations. Consistent with the pattern the
requester flagged: **each fix round resolves its predecessors cleanly and introduces new defects in
what it touched** — this round, D23 (in the AC it rewrote for D21), D24 (in the AC it created for
D13), D26 (in the requirement it created for D13, breaking the claim it repaired for D19), D25/D29
(in the claims it added for D22/D13).

---

## Recommendation — go/no-go input for a human

### Genuinely blocking (do not start Run without fixing — but both are document-only edits)

1. **D24 — one word.** Add `logistics_status="received"` to the `damaged_exchange` LineItem in
   AC-DEX-013 (spec.md:265) and 시나리오 13 (acceptance.md:137). Without it, a backfill that copies
   `0033_backfill_order_ready_to_ship.py` verbatim — omitting the `damaged_exchange` short-circuit,
   the single most likely implementation error given plan.md tells the implementer to copy 0033 —
   passes the only criterion that exists to catch it. This is the criterion that carries D13, the
   blocking defect this whole revision was built around. Also add `sku` not null to AC-DEX-013a's
   second Order (spec.md:267 / acceptance.md:143) so it is not vacuous.

2. **D23 — two lines.** AC-DEX-012e (spec.md:261) / 시나리오 12f (acceptance.md:179-183) assert
   "shall report a quantity", but `VendorComparisonView` returns no quantity field
   (`purchase_order_views.py:808-833`), and with the stated fixture the auto-selection outputs are
   identical for `10` and `3` (`excel_utils.py:553-569`, all stocks `0`). Choose one: restate as a
   white-box assertion on the view's internal `sku`→quantity map; or add a `WarehouseStock` row with
   `korea=5` so `candidate_basis` discriminates; or delete the AC and rely on the diff-level
   Exclusions gate at acceptance.md:201, recording the reduction. Any of the three is acceptable;
   leaving it as written is not, because it cannot be executed honestly.

### Acceptable to carry into implementation as documented risks

- **D25** (test count 9 vs 10) — corrects a number, changes no behavior. The substantive claim (three
  branches frozen, zero `damaged_exchange` in that file) is verified true.
- **D26** ("the backfill" as subject in two Unwanted items) — valid EARS either way; only the
  self-referential claim at spec.md:127 is inaccurate.
- **D27** (spec.md:41/:50 still say `status` "무변경") — the normative requirement (L167) and plan
  (L102) are correct; risk is an implementer reading only the summary and adding an `update_fields`
  carve-out. Low, and plan.md:102 explicitly warns against it.
- **D28** (REQ-DEX-013a's two readings; the backfill also silently corrects stale non-damaged Orders)
  — precedent-consistent with 0033, no correct implementation fails any AC. Worth one sentence in
  the requirement, but safe to carry.
- **D29** (0033 has no query-count test), **D30** (`test_order_resync.py` asserts nothing about
  `ready_to_ship`), **D31** (`models.py:221` still cited inside a requirement), **D32** (audit
  provenance inside normative text) — all documentation-accuracy items with no implementation risk.

### Assessment

Substantively this is the strongest revision of the three. All four iteration-2 blockers were
addressed at the requirement level rather than by rewording tests; the backfill design was verified
line-by-line against its in-repo precedent and is correct; traceability is perfect at 24/27; and the
file:line citation record remains clean across roughly 45 references, including every one added this
round. The two blocking findings are both defects in *acceptance criteria*, not in the design: D24 is
a one-word hardening, D23 is a mis-specified observable on a view this SPEC does not modify.

A human may reasonably decide to proceed to Run without a fourth audit round, **provided the two
edits above are applied to spec.md and acceptance.md first** — they take minutes and require no
further investigation, since the exact replacement text is given. What is not acceptable is starting
implementation with AC-DEX-013 as written, because the criterion that guards the SPEC's central new
requirement can be satisfied by the wrong migration.

Verdict: FAIL
