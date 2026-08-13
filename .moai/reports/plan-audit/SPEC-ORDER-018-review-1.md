# SPEC Review Report: SPEC-ORDER-018

Iteration: 1/3
Verdict: FAIL
Overall Score: 0.68

Reasoning context ignored per M1 Context Isolation. This audit is based solely on the five
documents in `.moai/specs/SPEC-ORDER-018/`, the committed implementation (`bd5a41c`), the
committed tests, and independent execution/mutation of those tests.

**Post-hoc audit note.** The implementation is already committed and under review as PR #23.
This SPEC skipped the plan-phase audit (the sync commit `5d1a1d5` records this itself under
"알려진 프로세스 갭"). The verdict below is a document-and-implementation audit, not a
pre-implementation gate. See the **Merge Decision** section for the separation between
merge-blocking findings and documentation debt.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency.** `REQ-RESTORE-001` … `REQ-RESTORE-023` appear exactly
  once each, sequentially, with consistent 3-digit zero-padding (spec.md:266–371, verified by
  enumeration — 23 definitions, 0 gaps, 0 duplicates). `AC-RESTORE-001` … `AC-RESTORE-014`
  likewise, 14 definitions in spec.md:381–465 and 14 matching `###` headings in acceptance.md.
  One cosmetic contradiction is recorded as D6 but does not affect numbering integrity.

- **[FAIL] MP-2 EARS format compliance.** Four of fourteen acceptance criteria carry the label
  `(Ubiquitous)` but are structurally `Given <precondition>, <subject> shall <response>` — which
  is not one of the five EARS patterns. A ubiquitous requirement by definition carries no
  precondition:
  - spec.md:398 `AC-RESTORE-004` (Ubiquitous) — *"Given 12 excluded LineItems spread across
    Orders with distinct creation timestamps, the response body shall carry…"*
  - spec.md:410 `AC-RESTORE-006` (Ubiquitous) — *"Given one `unordered` LineItem for SKU A
    and one LineItem in each of the four excluded states…"*
  - spec.md:416 `AC-RESTORE-007` (Ubiquitous) — *"With the same fixture in place, the number
    of database queries…"*
  - spec.md:435 `AC-RESTORE-010` (Ubiquitous) — *"Given an `on_hold` LineItem carrying a
    non-empty `rack_number`…"*

  Three requirements also mismatch their declared pattern:
  - spec.md:285–289 `REQ-RESTORE-005` is labelled `(State-Driven)` and opens correctly with
    *"While refunds are recorded against a returned LineItem…"*, then appends a second,
    ubiquitous sentence that describes the **negation** of that While-condition: *"A LineItem
    with no refunds shall be listed regardless of its ordered quantity, including when that
    quantity is absent or zero."* Two patterns in one requirement. This is not cosmetic — that
    trailing clause is the entire normative content of 설계 결정 D and is the only place the
    guarded-skip behaviour is required.
  - spec.md:357–358 `REQ-RESTORE-020` is labelled `(Unwanted)` but its condition
    *"If the excluded-items view is displayed"* is a persistent state, not an undesired
    event — it is State-Driven.
  - spec.md:370–371 `REQ-RESTORE-023` — *"If this SPEC is implemented, then no new model
    field, database migration, or audit-log table shall be introduced."* The antecedent is a
    process fact, not a runtime condition, and the consequent constrains the development
    process, not system behaviour. spec.md:495–496 concedes this ("부재를 요구하는 메타
    요구사항"). It is a build gate wearing EARS clothing.

- **[PASS] MP-3 YAML frontmatter validity.** spec.md:1–11 carries `id: SPEC-ORDER-018`
  (string, matches `SPEC-{DOMAIN}-{NUM}`), `version: 1.0.2` (string), `status: completed`
  (string), `created_at: 2026-08-13` (ISO date), `priority: High` (string), and
  `labels: [order, purchase-status, restore, read-path, frontend]` (array). All six required
  fields present with correct types, plus `updated`, `author`, `issue_number`.
  Informational: `status: completed` is outside the canonical `draft|active|implemented|
  deprecated` enum, but it is this repository's established convention across prior SPECs, so
  it is not scored as a type or presence failure.

- **[N/A] MP-4 Section 22 language neutrality.** This SPEC is scoped to one Django/Python
  backend and one React/TypeScript frontend within a single application. It makes no claim
  about multi-language tooling and enumerates no language servers or per-language toolchains.
  Criterion does not apply.

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements | Requirements are unusually precise and each design decision is evidence-backed (spec.md:109–256). Deductions: REQ-RESTORE-005 packs two patterns (spec.md:285–289); REQ-RESTORE-014 packs four independent sub-rules into one requirement (spec.md:325–331); REQ-RESTORE-023 is non-behavioural (spec.md:370). |
| Completeness | 0.75 | 0.75 — one non-critical section sparse; frontmatter complete | All required sections present: HISTORY (spec.md:15–21), 문제 정의 (:25), 솔루션 개요 (:61), 범위 (:89), 설계 결정 A–I (:107–256), 요구사항 (:260), ACCEPTANCE CRITERIA (:375), Exclusions (:524–546, 14 specific entries with file citations), 후속 과제 (:548). Deductions: the second clause of AC-RESTORE-007 ("the new read view shall not appear in the call graph of any pre-existing endpoint", spec.md:418–419) has **no** corresponding assertion anywhere in test_spec_018.py; and the acceptance.md DoD table is factually wrong about where T14 lives (D4). |
| Testability | 0.50 | 0.50 — several ACs require judgment calls / cannot discriminate | 12 of 14 criteria are genuinely binary-testable; **two are proven by mutation testing to be incapable of failing a wrong implementation** (D1, D2). AC-RESTORE-013's final clause is structurally unfalsifiable given the test's static store mock (D9). AC-RESTORE-009's `on_hold` half asserts equality against a self-recorded value with no premise assertion (D14). No weasel words found ("appropriate"/"reasonable"/"adequate" absent from all 14 criteria). |
| Traceability | 1.00 | 1.0 — every REQ has an AC; every AC traces to a valid REQ | Programmatically cross-checked: all 14 `Traces:` lists in spec.md are **byte-identical** to the corresponding lists in acceptance.md, honouring the `[HARD]` pledge at acceptance.md:14–15. Every AC references only REQ IDs that exist. The single uncovered requirement, REQ-RESTORE-023, is explicitly and correctly routed to a build gate (spec.md:493, acceptance.md:337–339, plan.md:263–265, plan.md:300). No orphaned ACs, no dangling REQ references. |

---

## Citation Verification (priority focus #2)

Every `file:line` citation across spec.md, plan.md, research.md, acceptance.md and
spec-compact.md was independently resolved by opening the cited file at the cited location, and
— where the current file did not match — by bisecting git history to find the revision the
citation was written against.

**Result: zero fabricated citations.** This is a materially better result than the
SPEC-ORDER-016 v1.0.5 incident that research.md:11–15 cites as its motivation.

Concretely:
- All 28 distinct cited paths exist. The only apparent miss, `LineItemNotesPage.tsx`
  (spec.md:50), is cited as a bare filename with no directory and resolves to
  `frontend/src/pages/LineItemNotesPage.tsx`.
- **Every** `purchase_order_views.py` citation resolves exactly at commit `9b23857` — the
  working-tree revision at research time. Verified spot checks at that revision:
  `:93` `_reorder_candidate_filter`, `:275`/`:567`/`:1071`/`:1410` the four call sites,
  `:1863` `LineItemStatusUpdateView`, `:1908` `LineItemBulkStatusUpdateView`,
  `:2365` `LineItemRackNumberSummaryView`, `:2399` `.exclude(purchase_status="order_cancelled")`,
  `:2415` `if li.refunded_qty and net_qty == 0:`, `:2416–2421` the Korean data-gap comment
  quoted verbatim at spec.md:167–169, `:2963` `OutboundForceCandidateView`, `:2973–2978` its
  docstring, `:3011` `.order_by("order_id", "pk")`, `:3428–3429` `PurchaseOrderPagination` /
  `page_size = 50`, `:3503` `PurchaseOrderListView`, `:2384–2386` the Refund-keying comment.
  All 19 checked, all exact.
- All frontend citations resolve exactly at the pre-implementation commit `88592d7`:
  `UnorderedItemsTab.tsx:126` (the `value !== 'unordered'` filter), `:262`, `:224`, `:230`,
  `:90`, `:69–72`, `:64–66`; `purchaseOrderApi.ts:16–25`, `:61–66`, `:90–93`, `:158–170`;
  `usePurchaseOrderQueries.ts:27`, `:103–115`, `:119–135`; `usePurchaseOrderStore.ts:4`, `:5`,
  `:12–13`, `:1–28` (file is exactly 28 lines).
- All test-file citations resolve exactly against the current tree:
  `test_purchase_orders.py:2152`, `:2197`, `:2217`, `:2234`, `:451`, `:50–59`, `:72`, `:77`,
  `:85`, `:89`, `:97`; `test_spec_015.py:34`.
- `models.py:156–167`, `:163–166`, `:204–208`; `serializers.py:79–97`;
  `excel_utils.py:614–622`; `views.py:269`, `:285`, `:313–317` — all exact against the current
  tree.

The citations are therefore **stale, not fabricated** — see D3 for the magnitude of the
staleness and why the sync commit should have fixed it.

---

## Acceptance-Criteria Discriminating Power (priority focus #1)

Method: for the criteria most at risk, I injected a mutation implementing the specific wrong
behaviour the criterion claims to forbid, ran only the corresponding test, then reverted. A
criterion that passes under its own mutant cannot protect anything.

| Criterion | Mutant injected | Test result | Discriminating? |
|---|---|---|---|
| AC-RESTORE-003 / REQ-005 (control) | `if li.refunded_qty and net_qty == 0` → `if net_qty == 0` (purchase_order_views.py:437) | **FAILED** — `assert {'SKU-PARTIAL'} == {'SKU-NULLQTY','SKU-PARTIAL'}` | **Yes** |
| AC-RESTORE-004 / REQ-007 | dropped `"pk"` from `.order_by("-order__shopify_created_at", "pk")` (purchase_order_views.py:424) | **PASSED** | **No** |
| AC-RESTORE-007 / REQ-011 | added an extra `LineItem.objects.filter(...).count()` inside the pre-existing `UnorderedItemsView.get()` | **PASSED** | **No** |
| AC-RESTORE-013 / REQ-019 | `toggleExcludedId` also calls `toggleSku(row.sku)` (leaks excluded selection into the shared store) | **FAILED** at `expect(toggleSku).not.toHaveBeenCalled()` | **Yes** |

The control mutant confirms the method works and that 설계 결정 D is genuinely pinned. The two
passing mutants are the SPEC-ORDER-017 class of defect recurring — see D1 and D2.

Baselines re-run and confirmed clean before and after every mutation:
`test_spec_018.py` 12 passed; `UnorderedItemsTab.test.tsx` 4 passed +
`usePurchaseOrderQueries.test.tsx` 3 passed. Working tree verified clean
(`git status --porcelain` empty for both mutated files) after revert.

---

## Implementation-vs-SPEC Conformance (priority focus #4)

Checked against the committed code, not the SPEC's own claims.

- **설계 결정 A — CONFORMS.** `ExcludedItemsView` (purchase_order_views.py:365) starts from
  `LineItem.objects.filter(purchase_status__in=EXCLUDED_PURCHASE_STATUSES)` at `:410`. `grep`
  for `_reorder_candidate_filter(` in the current file returns exactly four call sites — `:308`
  `UnorderedItemsView`, `:708` `RunComparisonView`, `:1212` `DailyReviewExcelView`, `:1586`
  `UploadDailyReviewView` — unchanged from the pre-implementation commit, plus one occurrence
  at `:382` which is inside the `@MX:NOTE` comment, not a call. The helper body (`:93–111`) is
  byte-identical to `f6d3fa3`. Fan-in remains 4. Requirement satisfied.
- **설계 결정 D — CONFORMS.** purchase_order_views.py:437 is
  `if li.refunded_qty and net_qty == 0:`, the guarded form, not `UnorderedItemsView`'s
  unconditional `if net_qty == 0:` at `:326`. Independently confirmed discriminating by the
  control mutant above.
- **REQ-RESTORE-012 — CONFORMS.** `bd5a41c --stat` shows no change to
  `LineItemStatusUpdateView` / `LineItemBulkStatusUpdateView`; the only backend edits are the
  +108-line block at `:350–457` and +7 lines in `urls.py`.
- **REQ-RESTORE-023 — CONFORMS.** `bd5a41c --stat` shows no `models.py` change and no new file
  under `backend/order/migrations/`.
- **REQ-RESTORE-020 — CONFORMS, and more strongly than required.** The excluded view returns
  early (UnorderedItemsTab.tsx:182) without rendering the order-file buttons at all, rather
  than disabling them. The inline comment states the reasoning.
- **REQ-RESTORE-016 — PARTIAL.** See D7: the view switcher is unreachable when the *unordered*
  query errors.
- **Behaviour with no covering requirement.** See D8 and D13.

---

## Defects Found

**D1. acceptance.md:86–105 / spec.md:398–404 / test_spec_018.py:355–357 — AC-RESTORE-004's
determinism check cannot fail a wrong implementation — Severity: major.**
The criterion is *"two consecutive identical requests shall return the rows in the identical
order."* The test implements it as
`assert [row["id"] for row in first...] == [row["id"] for row in second...]`. I removed the
`"pk"` tie-break from `purchase_order_views.py:424` — the exact defect the criterion exists to
catch, and the exact defect 설계 결정 H (spec.md:242–250) argues against — and **the test
passed**. Two identical queries against a stable table return a stable order regardless of
whether an ordering is deterministic *by construction*. acceptance.md:103–105 half-admits this
("(d)가 MySQL의 반환 순서에 따라 **간헐적으로** 실패한다"); a criterion that fails only
intermittently is not an acceptance criterion. The tie fixture built at test_spec_018.py:314–331
is therefore decorative: it creates the tie but nothing asserts what happens to it.
Fix: assert the concrete expected sequence, e.g. that the two rows sharing `tie_ts` appear in
ascending `pk` order, or compare the full id list against one computed by sorting the fixture by
`(-shopify_created_at, pk)` in Python.

**D2. acceptance.md:141–156 / spec.md:416–419 / test_spec_018.py:450–491 — AC-RESTORE-007 does
not test what REQ-RESTORE-011 requires — Severity: major.**
REQ-RESTORE-011 requires that "no existing endpoint issues a different number of database
queries … **as a result of this SPEC**". The test instead compares the unordered endpoint's
query count *with vs without excluded rows in the table* — a data-volume invariance check, which
is a different proposition. I injected an extra constant-cost query into `UnorderedItemsView.get()`
— precisely "this SPEC leaked a query into a pre-existing endpoint" — and **the test passed**,
because the extra query is present in both measurements and cancels out. The criterion is
therefore vacuous against its own stated failure mode. Separately, its second clause ("the new
read view shall not appear in the call graph of any pre-existing endpoint", spec.md:418–419)
has no assertion at all anywhere in the suite. The real protection for REQ-011 comes from T6 and
from plan.md:259–260's `git diff` gate, not from T7.
Fix: either assert an absolute query-count ceiling for `UnorderedItemsView` (pinning it as a
regression baseline), or restate the criterion as the diff gate it actually is and delete the
misleading equivalence assertion.

**D3. spec.md, acceptance.md, research.md, plan.md (all `file:line` citations) — citations are
systematically stale by up to +439 lines and were not refreshed by the sync commit —
Severity: major (documentation).**
The citations were correct against commit `9b23857`. Two independent drifts have since
accumulated: (a) concurrent work on `purchase_order_views.py` landed before implementation
(+33 lines before line 350, **+331** after it), and (b) this SPEC's own implementation added
108 more lines at `:350`, plus 7 in `urls.py`, 15+ in `purchaseOrderApi.ts`, 19 in
`usePurchaseOrderQueries.ts`, 215 in `UnorderedItemsTab.tsx`, 196 in `UnorderedItemsTab.test.tsx`.
Net effect today, sampled:

| Cited as | Actually now |
|---|---|
| `purchase_order_views.py:1863` `LineItemStatusUpdateView` (spec.md:70, :96, :528) | `:2302` |
| `purchase_order_views.py:1908` `LineItemBulkStatusUpdateView` (spec.md:70, :529) | `:2347` |
| `purchase_order_views.py:2415` guarded refund skip (spec.md:166, acceptance.md:81) | `:2854` |
| `purchase_order_views.py:2963`/`:2973–2978` `OutboundForceCandidateView` (spec.md:66, :117) | `:3402` / `:3412–3417` |
| `:567`, `:1071`, `:1410` filter call sites (spec.md:34, :95, :112, :527) | `:708`, `:1212`, `:1586` |
| `UnorderedItemsTab.tsx:126` bulk-select filter (spec.md:41, acceptance.md:270) | `:341` |
| `UnorderedItemsTab.tsx:224`/`:230` `toggleSku(item.sku)` (spec.md:214, acceptance.md:294) | `:439` / `:445` |
| `UnorderedItemsTab.tsx:90` order-file `mutateAsync` (spec.md:79, :219) | `:144` |
| `purchaseOrderApi.ts:16–25` `PURCHASE_STATUS_OPTIONS` (spec.md:39, :538; plan.md:275) | `:31–40` |
| `urls.py:154` note-resolve path (spec.md:194) | `:161` |
| `urls.py:72` path-order comment (spec.md:582) | `:75` (line 72 is now this SPEC's own comment) |

Version 1.0.2 was created by a sync commit whose stated purpose was documentation
synchronisation; it changed only the `version:` line in four of the five documents. Every one of
the above was already wrong at that moment. This matters more than usual here because
research.md:11–15 makes citation integrity this SPEC's explicit differentiator — the SPEC set
the bar and then did not clear it on the second pass.

**D4. acceptance.md:335 and acceptance.md:17–19 — the Definition-of-Done table names the wrong
test file for AC-RESTORE-014 — Severity: major (documentation).**
The quality-gate table states `AC-RESTORE-014 [FE] | UnorderedItemsTab.test.tsx | T14`, and
acceptance.md:18–19 states that "`[FE]`는 …`UnorderedItemsTab.test.tsx`의 vitest 시나리오다.
… AC-RESTORE-012~014가 `[FE]`다". T14 is not in that file. It is in
`frontend/src/hooks/usePurchaseOrderQueries.test.tsx:57–81`. spec.md:20 (HISTORY v1.0.1) and
spec.md:506 both record the relocation and its justification, and the justification is sound —
`UnorderedItemsTab.test.tsx:17–23` replaces the whole hook module with a `vi.mock` factory, so
the real `onSuccess` callbacks can never run there. But acceptance.md was never corrected. This
is not staleness; it is an active falsehood in the document a reviewer would consult to verify
completion. It is also the one divergence the sync commit explicitly re-examined
(spec.md:21) — and it still left the wrong pointer in place.

**D5. spec.md:398, :410, :416, :435, :285–289, :357–358, :370–371 — EARS label/structure
mismatches — Severity: major (documentation).** Detailed under MP-2 above.

**D6. spec.md:262 vs spec.md:495 — internal contradiction on requirement count —
Severity: minor.** Line 262: *"요구사항은 5개 모듈, REQ-RESTORE-001부터 REQ-RESTORE-022까지
연속 번호로 구성된다."* Line 495: *"23개 요구사항이 14개 인수 기준으로 커버된다."* There are
23 (001–023). The traceability table at spec.md:493 lists REQ-RESTORE-023. Line 262 is an
uncorrected off-by-one from an earlier draft.

**D7. UnorderedItemsTab.tsx:158–160 vs REQ-RESTORE-016 (spec.md:338–341) — the view switcher is
unreachable when the unordered query errors — Severity: minor (functional).**
`if (isError) { return <p>미발주 현황을 불러오는데 실패했습니다.</p> }` executes before
`viewSwitcher` is constructed at `:162` and before the `view === 'excluded'` branch at `:182`.
REQ-RESTORE-016 states unconditionally that the tab "shall offer a control that switches
between the existing unordered list and a excluded-items list". If `/unordered/` fails, it does
not. The symmetric case is handled correctly — `excludedQuery.isError` at `:183` still renders
the switcher. `isPending` is *not* an early return (it is inline at `:393`), so only the error
path is affected. No test covers this; AC-RESTORE-012 exercises only the happy path.

**D8. UnorderedItemsTab.tsx:216–232 — the excluded view's bulk control offers all seven
statuses, which no requirement covers — Severity: minor (uncovered behaviour).**
REQ-RESTORE-018 requires that `unordered` be *offered*; the implementation renders the entire
unfiltered `PURCHASE_STATUS_OPTIONS`, so an operator can bulk-move excluded items to
`in_stock`, `damaged_exchange`, or between excluded states. Nothing forbids this and it is
arguably useful, but it is a write capability introduced on a screen the SPEC describes
throughout as a *restore* path, and no requirement, AC, or exclusion mentions it. The same
applies to `excludedBulkStatus` defaulting to `'unordered'` (`:70`) — sensible, unspecified.
Also unspecified: clicking anywhere on a row toggles its selection (`:270`).

**D9. acceptance.md:297–299 / UnorderedItemsTab.test.tsx:265–270 — AC-RESTORE-013's final
clause is structurally unfalsifiable — Severity: minor.**
The criterion's last requirement is that after switching back, order-file generation behaves "as
if no excluded row had ever been selected", asserted as
`expect(mutateAsync).toHaveBeenCalledWith({ distributor: 'yes24', skus: ['8809226729403'] })`.
`usePurchaseOrderStore` is mocked (`:71–76`) to return a **constant** object, so `selectedSkus`
cannot change no matter what the component does — the assertion passes unconditionally. The real
protection is `expect(toggleSku).not.toHaveBeenCalled()` at `:258`, which I confirmed
discriminating by mutation. So the clause is redundant rather than dangerous, but it reads as
independent evidence when it is not.

**D10. spec.md:381–386 / test_spec_018.py:205–209 — AC-RESTORE-001 verifies less than
REQ-RESTORE-001 requires — Severity: minor.**
REQ-RESTORE-001 forbids any LineItem, Order, PurchaseOrder **or LineItemNote** row being
"created, modified, or deleted". The test takes a full-field snapshot for `LineItem`
(`:189`, `:206` — genuinely discriminating) but only row **counts** for `LineItemNote`,
`PurchaseOrder` and `Order` (`:190–192`, `:207–209`). A mutation to an existing note or order
row would not be detected. AC-RESTORE-001 (spec.md:385–386) is itself worded narrowly ("A
snapshot of every LineItem row"), so the test faithfully implements a criterion that is weaker
than its requirement.

**D11. spec.md:418–419 — AC-RESTORE-007's second clause has no verification at all —
Severity: minor.** "the new read view shall not appear in the call graph of any pre-existing
endpoint" — no assertion exists in test_spec_018.py, and neither acceptance.md:141–156 nor
plan.md:292 mentions how it would be checked beyond the general diff gate.

**D12. spec.md:20 (HISTORY v1.0.1) — the recorded drift magnitude is wrong —
Severity: minor.** The entry states the file was *"`research.md` 인용 대비 약 +33줄 밀려
있었다"*. +33 is correct only for citations before line ~350. Everything after it had shifted
+331, as the same sentence's own mappings show (`:1863`→`:2194`, `:1908`→`:2239` — both +331).
The "약 +33줄" summary understates the drift by an order of magnitude and would mislead anyone
using it to reconstruct citations.

**D13. purchase_order_views.py:411 vs REQ-RESTORE-004 (spec.md:282–283) — empty-string SKUs are
not excluded — Severity: minor.** `.exclude(sku__isnull=True)` drops NULL SKUs but admits
`sku=""`, which would render as a blank SKU cell and cannot be acted on meaningfully. This
mirrors `UnorderedItemsView`'s `filter(sku__isnull=False)` convention, so it is consistent
rather than novel, and REQ-RESTORE-004 says "no SKU" without defining whether `""` counts.
AC-RESTORE-002 tests only the NULL case.

**D14. spec.md:428–433 / test_spec_018.py:584–606 — AC-RESTORE-009's `on_hold` half asserts
against a self-recorded value with no premise — Severity: minor.**
For `order_cs` the test correctly asserts the premise (`assert order_cs.ready_to_ship is False`
at `:587`) before acting, then asserts the concrete post-state `is True`. For `order_hold` it
only records `hold_ready_before` / `hold_status_before` (`:584–585`) and asserts equality after.
If a regression made both values `None`, the assertion would still pass. AC-RESTORE-008
(spec.md:421–426) does this correctly with concrete `true`→`false` values; AC-RESTORE-009's
first half does not.

---

## Chain-of-Verification Pass

Second-look findings, after re-reading every section I had covered quickly on the first pass:

- **Re-read every REQ individually rather than sampling.** This surfaced D5's REQ-side
  components (REQ-005's two-pattern mix, REQ-020's Unwanted-vs-State label, REQ-023's
  non-behavioural form), which my first pass had skimmed past after checking that the AC labels
  looked plausible.
- **Re-checked REQ sequencing end-to-end by enumeration, not spot-check.** Confirmed 23 unique
  IDs; this is also what surfaced D6 (the "022" text at spec.md:262).
- **Re-verified traceability for all 23 REQs and all 14 ACs programmatically**, not by sampling.
  Result was clean in both directions — this is the one dimension that survived the second pass
  unchanged.
- **Re-read the Exclusions section for specificity, not mere presence.** All 14 entries at
  spec.md:526–546 name a concrete artefact; none are vague. However, this re-read is what
  surfaced that the section's citations (`:1863`, `:1908`, `:93-110`, `:275/:567/:1071/:1410`,
  `purchaseOrderApi.ts:16-25`, `usePurchaseOrderStore.ts:1-28`) are among the stale set in D3 —
  the exclusions are the most citation-dense section in the document and therefore the most
  degraded.
- **Looked for contradictions between requirements, not only within them.** Found none. I
  specifically checked REQ-018 (offer `unordered` in the bulk control) against the Exclusions
  entry "PURCHASE_STATUS_OPTIONS 수정 없음" (spec.md:538–539) — these are compatible, and the
  implementation resolves it exactly as the exclusion describes (filter at render time, constant
  untouched). I also checked REQ-009 against REQ-001 (visibility vs eligibility) — consistent,
  and 설계 결정 B (spec.md:126–132) states the distinction explicitly.
- **Did NOT stop at reading the tests.** The first pass concluded from inspection that
  AC-RESTORE-004 and AC-RESTORE-007 "looked weak". Inspection is not evidence, so I ran mutation
  tests with a control. Both suspicions were confirmed empirically, and the control passed —
  which is what upgraded D1 and D2 from "possible concern" to major findings and what
  moved Testability from 0.75 to 0.50.
- **New defects added on the second pass:** D5 (REQ-side), D6, D10, D11, D12, D13, D14.

---

## Regression Check

Not applicable — iteration 1. No prior review report exists for SPEC-ORDER-018
(`.moai/reports/plan-audit/` contains reports for SPEC-ORDER-008 through -017 but none for
-018), which is consistent with the process gap the sync commit `5d1a1d5` recorded.

---

## Merge Decision: what blocks, what follows

The audit verdict is FAIL on MP-2. That is a document-conformance failure, not a statement that
the code is wrong. Stated plainly:

**Nothing found blocks the merge on correctness grounds.** I verified independently that the
implementation satisfies 설계 결정 A (the view does not call `_reorder_candidate_filter`;
fan-in is still 4 and the helper body is byte-identical), 설계 결정 D (the refund skip is
guarded on `refunded_qty`), REQ-RESTORE-012 (no write-endpoint change) and REQ-RESTORE-023 (no
model or migration change). No requirement is unsatisfied by the code. The 979/237 passing
suites are real, and 12 of the 14 criteria do discriminate — two of them proven so by mutation.

**Worth fixing before merge (small, and they close real holes):**

1. **D1** — make AC-RESTORE-004's ordering assertion concrete. The tie fixture already exists at
   test_spec_018.py:314–331; add an assertion that the two tied rows come back in ascending `pk`
   order, or compare the whole id list against a Python-side sort by `(-shopify_created_at, pk)`.
   Roughly three lines. Without it, anyone can delete `"pk"` from
   purchase_order_views.py:424 and the suite stays green.
2. **D4** — correct acceptance.md:335 and acceptance.md:17–19 to name
   `frontend/src/hooks/usePurchaseOrderQueries.test.tsx`. This is a one-line fix to a document
   that currently tells a reviewer to look for a test in a file that does not contain it.

**Documentation debt that can follow the merge:**

3. **D3** — refresh all `file:line` citations, or (better, and as spec.md:508 itself
   recommends) stop citing absolute line numbers for anything outside the SPEC's own diff and
   cite symbol names instead: `purchase_order_views.py::ExcludedItemsView`,
   `::LineItemRackNumberSummaryView` refund guard. The current scheme is guaranteed to rot
   again on the next merge. This SPEC has now demonstrated that twice within its own lifetime.
4. **D2** — restate AC-RESTORE-007 as what it actually verifies, or replace the equivalence
   assertion with an absolute query-count baseline for `UnorderedItemsView`. Note that the
   protection REQ-011 really relies on is plan.md:259–260's diff gate, and that gate did hold.
5. **D5, D6, D12** — EARS labels, the "022" off-by-one at spec.md:262, and the "약 +33줄"
   drift figure at spec.md:20.
6. **D7** — move the `isError` early return at UnorderedItemsTab.tsx:158 below the
   `view === 'excluded'` branch so a failing unordered query does not hide the excluded view,
   and add the case to AC-RESTORE-012.
7. **D8** — decide whether the excluded view's bulk control should be restricted to
   `unordered`, and if it should stay open, say so in a requirement or an exclusion.
8. **D9, D10, D11, D13, D14** — criterion-strengthening items; batch them into a follow-up.

**Process note.** The most useful finding for the repository is not any individual defect: it is
that this SPEC's citation-integrity discipline worked (zero fabrications across five documents
and ~90 citations, independently confirmed by git bisection), while its *discriminating-power*
discipline did not — the same failure mode SPEC-ORDER-017 exhibited recurred here in two
criteria despite acceptance.md carrying explicit "판별력" (discriminating power) paragraphs for
both of the affected criteria. Writing a paragraph asserting that a test discriminates is not
the same as verifying that it does. A cheap mutation check on each criterion claiming
discriminating power would have caught both D1 and D2 in minutes.
