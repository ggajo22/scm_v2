# SPEC Review Report: SPEC-PURCHASE-ORDER-011
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.52

Reasoning context ignored per M1 Context Isolation. This audit is based solely on the four
documents in `.moai/specs/SPEC-PURCHASE-ORDER-011/` (spec.md, plan.md, acceptance.md,
spec-compact.md) and on direct reading of the cited source files in `backend/` and `frontend/`.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  Base series `REQ-DEX-001`..`REQ-DEX-012` (spec.md:82, 86, 88, 92, 94, 98, 104, 108, 110, 114,
  116, 120) — no gaps, no duplicates, consistent 3-digit zero padding. Alphabetic suffixes
  (`005a`, `006a`, `006b`, `009a`, `012a`, `012b`) are declared and justified at spec.md:78 and
  match the SPEC-ORDER-015 / SPEC-PURCHASE-ORDER-010 project convention. AC IDs (spec.md:153-191)
  likewise contain no duplicates. Counts asserted in spec-compact.md:29 ("REQ 18개 / AC 20개")
  are arithmetically correct against the actual documents.

- **[FAIL] MP-2 EARS format compliance**
  Four requirements carry the `(Unwanted)` label but contain no `If [condition], then the [system]
  shall [response]` trigger, and two of them do not take "the system" as subject:
  - spec.md:100 `REQ-DEX-006a` (Unwanted): "The system shall NOT recompute, override, or
    redefine `Order.ready_to_ship`…" — negative ubiquitous, no If-trigger.
  - spec.md:116 `REQ-DEX-011` (Unwanted): "**A damage submission** … shall NOT modify…" — subject
    is an event, not the system; no If-trigger.
  - spec.md:122 `REQ-DEX-012a` (Unwanted): "**The base-quantity substitution** … shall NOT
    apply…" — subject is an implementation mechanism, not the system.
  - spec.md:124 `REQ-DEX-012b` (Unwanted): "**This SPEC** shall NOT modify the reorder-quantity
    computation at any of the other existing reorder-candidate call sites…" — the subject is the
    document itself. This is a scope/exclusion statement, not a statement of system behavior, and
    matches no EARS pattern. It duplicates the Exclusions entry at spec.md:137.

  Additionally, 13 of the 20 acceptance criteria are Given/When/Then test scenarios carrying EARS
  pattern labels (spec.md:159, 161, 163, 167, 169, 175, 177, 179, 181, 183, 185, 187, 189, 191),
  e.g. spec.md:175 "**(Event-Driven)** … **Given** a LineItem with `quantity=8` … **when** a damage
  submission of `3` is made, the system shall…". These duplicate acceptance.md's scenarios almost
  verbatim, and the duplication has already produced drift (see D4 below: AC-DEX-012b at
  spec.md:187 and 시나리오 12c at acceptance.md:125-129 do not state the same fixture).

- **[FAIL] MP-3 YAML frontmatter validity**
  `created_at` is absent. spec.md:5 declares `created: 2026-08-14` instead. Every sibling SPEC in
  this repository uses `created_at`:
  - `.moai/specs/SPEC-ORDER-020/spec.md:5` → `created_at: 2026-08-13`
  - `.moai/specs/SPEC-ORDER-015/spec.md:5` → `created_at: 2026-08-10`
  - `.moai/specs/SPEC-PURCHASE-ORDER-010/spec.md:5-6` → `created:` **and** `created_at:` both present
  A required field being present under a different key name is a missing required field.
  All other required fields are valid: `id` (spec.md:2), `version` (L3), `status` (L4),
  `priority` (L8), `labels` array (L10). Secondary: `issue_number: 0` (spec.md:9) is a placeholder;
  all sibling SPECs carry a real issue number at plan time (020→27, 015→13, 010→9).

- **[N/A] MP-4 Section 22 language neutrality**
  N/A: single-stack SPEC (Django/DRF backend + React/TS frontend). No multi-language tooling
  content, no language-server or per-language tool enumeration anywhere in the four documents.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | 0.50 — multiple requirements require interpretation; a reasonable engineer might implement them differently than intended | Repeat-submission semantics undefined (spec.md:96 makes it reachable, spec.md:108/110 never say overwrite vs accumulate — D5); "전체 출고 수량" label sums `quantity` while the codebase's actual 출고 수량 field is `LineItem.shipped_quantity` (models.py:221) (D7); AC-DEX-002 (spec.md:155) "sharing no component … with `/outbound`" is literally unachievable (D8); AC-DEX-006 (spec.md:169) cites "REQ-DEX-006a's rule" but REQ-DEX-006a (spec.md:100) defines no rule (D9) |
| Completeness | 0.50 | 0.50 — frontmatter missing a required field; a confirmed design decision has no requirement | `created_at` missing (spec.md:5, MP-3); 결정 D (spec.md:72-74, `author=request.user`) is implemented in plan.md:58 but has **no REQ and no AC** — REQ-DEX-010 (spec.md:114) cites "(결정 D)" while only requiring the note *content* (D6); null-`quantity` coercion to 0 asserted in 결정 B (spec.md:64) is verified by no AC. All required sections are present: HISTORY (L15-20), WHY (L24-28), WHAT (L30-45), REQUIREMENTS (L76-124), ACCEPTANCE CRITERIA (L149-191), Exclusions (L128-138, 8 specific entries) |
| Testability | 0.50 | 0.50 — several ACs require judgment or fail to discriminate | AC-DEX-009 / 시나리오 9 asserts an outcome a **correct** implementation cannot produce (D1, critical); AC-DEX-012b (spec.md:187) omits the one fixture value that gives it discriminating power (D4); AC-DEX-005a's Given is self-contradictory (D10); AC-DEX-008 (spec.md:173) "shall reject client-side **or** server-side" is satisfiable by client-only validation. Counterweight: AC-DEX-005/005b (spec.md:163,167), AC-DEX-012/012a/012c (L183,185,189), AC-DEX-003/004/010/011 are genuinely discriminating and explicitly enumerate the wrong answers |
| Traceability | 0.75 | 0.75 — coverage complete, but one internal cross-reference is broken and one exclusion is under-covered | All 18 REQs have ≥1 AC (001→AC-001; 002,003→AC-002; 004→AC-003; 005→AC-004; 005a→AC-004a; 006→AC-005,005a; 006a→AC-006; 006b→AC-005b; 007→AC-007; 008→AC-008; 009→AC-009; 009a→AC-009a; 010→AC-010; 011→AC-011; 012→AC-012,012a,012b; 012a→AC-012c; 012b→AC-012d). All 20 ACs trace to REQs that exist. acceptance.md scenario→AC mapping is consistent end-to-end (시나리오 12c→AC-DEX-012b, 12d→AC-DEX-012c, 12e→AC-DEX-012d). Deductions: AC-DEX-006 references a non-existent "REQ-DEX-006a's rule" (D9); AC-DEX-012d (spec.md:191) regression-checks only 2 of the 5 sites REQ-DEX-012b enumerates (D11) |

---

## Citation Verification (project failure mode 1)

Every `file:line` reference in the four documents was opened and read. **No fabricated file paths
and no wrong line numbers were found.** Confirmed correct:

| Citation | Verified |
|---|---|
| plan.md:30 `models.py` L156~194 | `PURCHASE_STATUS_CHOICES` L156-167, `purchase_status` field L190-194 — correct |
| plan.md:31 "최신 마이그레이션은 `0036_order_name_index.py`" | correct, it is the highest-numbered file in `backend/order/migrations/` |
| plan.md:32, 102 `UnorderedItemsView` L251-314, `net_qty` L292 | class L251, `return Response` L314, `net_qty = max((li.quantity or 0) - li.refunded_qty, 0)` at L292 — exact |
| plan.md:32, 103 `LineItemStatusUpdateView` L1863-1900 | exact |
| plan.md:33 `urls.py` L84-106 (SPEC-ORDER-013/014), L70-72 (SPEC-PURCHASE-ORDER-004) | exact |
| plan.md:49, 104 `LineItemRackNumberSummaryView` L2284-2341, unshipped filter | exact; L2301-2302 `.exclude(logistics_status="shipped").exclude(purchase_status="order_cancelled")` |
| plan.md:50, 79, 105 `_recompute_order_aggregates` L123-195, trackable query L154-158, `non_cancelled` L176 | exact; the claim that the search filter scope matches the aggregate's trackable+non-cancelled set is **correct** |
| plan.md:64 pseudocode vs L292 | consistent with actual code |
| plan.md:73, 106 `_reorder_candidate_filter` L93-110 (L86-110 incl. MX comment) | exact |
| plan.md:79 `_process_outbound_rows` "쿼리 수 3N→3" | corroborated by SPEC-ORDER-015/spec.md:24 and :596 |
| plan.md:83 `0035_lineitem_add_shipped_fields.py` precedent | exists |
| plan.md:95-96 mx.yaml `anchor_per_file: 3`, "이 파일은 이미 ANCHOR 4개 보유", `_recompute_order_aggregates` L113-122 demotion comment, fan_in 8 | all exact — mx.yaml:175, and ANCHOR tags at purchase_order_views.py:14, 860, 1176, 2915 (the other two `@MX:ANCHOR` string hits at L88/L118 are prose inside NOTE comments) |
| plan.md:42-43, 107 `router/index.tsx` L122-128, `Sidebar.tsx` L3 / L37-87 / L68-74 | exact |
| spec.md:19 HISTORY file list | all 7 files exist |
| spec.md:64 SPEC-ORDER-014 REQ-RACKSUM-005 precedent | exists at `.moai/specs/SPEC-ORDER-014/spec.md:151` |
| spec.md:114 `note_type="파손/교환"`, `assignee="발주"` | both are valid choices: models.py:251 and models.py:237 |
| acceptance.md:149 `test_purchase_order_models.py`, `test_purchase_orders.py` | both exist and both contain `damaged_exchange` tests |

**However, two claims *about* correctly-cited code are factually wrong** (D1 and D3 below). This is
the same failure class as fabricated citations: the path and line are real, but the document
asserts behavior the code does not have.

---

## Defects Found

**D1. acceptance.md:91 (and spec.md:175) — the "정상 접수" scenario asserts an outcome a CORRECT
implementation cannot produce. — Severity: critical**

시나리오 9 Given: an Order with a single LineItem, `quantity=8`, `purchase_status="unordered"`,
`logistics_status="received"`, therefore `ready_to_ship=True`.
시나리오 9 Then: "부모 Order의 `ready_to_ship`은 재계산되어 `False`로 바뀐다(damaged_exchange는
`logistics_status=="received"` 또는 `purchase_status=="in_stock"` 조건을 만족하지 않으므로)".

The parenthetical misreads `_recompute_order_aggregates`. The actual predicate is
`purchase_order_views.py:182-185`:

```python
ready_to_ship = all(
    logistics_status == "received" or purchase_status == "in_stock"
    for logistics_status, purchase_status in non_cancelled
)
```

The first disjunct tests `logistics_status`, which REQ-DEX-011 (spec.md:116) explicitly forbids the
damage submission from touching. After the submission the row is still
`logistics_status="received"`, so `all(...)` is still `True` and `ready_to_ship` stays `True`.
The scenario as written would fail against a correct implementation.

This is simultaneously a **non-discriminating criterion of the worst kind**: because
`ready_to_ship` does not change in this fixture, the single most plausible wrong implementation —
**omitting the `_recompute_order_aggregates([li.order_id])` call entirely** — produces byte-identical
observable state. REQ-DEX-009's recomputation clause (spec.md:110) therefore has **zero** verifying
coverage. spec.md:175's phrasing ("recompute … such that a previously-`True` `ready_to_ship`
changes to reflect the new state") is either equally wrong or unfalsifiable weasel wording.

Discriminating fixtures do exist and must be substituted, e.g.:
- Pre-state `purchase_status="in_stock"`, `logistics_status="not_shipped"` → `ready_to_ship=True`
  before; after the submission the row is `damaged_exchange`/`not_shipped`, so the predicate
  becomes `False`. Omitting the recompute leaves a stale `True` → caught.
- Or pre-state `purchase_status="cs_required"` → `ready_to_ship=False` before, `True` after
  (with `logistics_status="received"`) via the `any(cs_required)` branch at L179-180.

**D2. spec.md:110 + acceptance.md:87-91 — REQ-DEX-009's recompute obligation is untested. —
Severity: critical** (consequence of D1, listed separately because it survives even a cosmetic fix
to the wording; the fixture itself must change.)

**D3. plan.md:73 and spec.md:124 — false claim about the five excluded call sites. — Severity: major**

plan.md:73 states: "`RunComparisonView`(L544-590)·`DailyReviewExcelView`(L1048-)·
`UploadDailyReviewView`(L1229-)·`GenerateOrderFileView`(L322-)·`ConfirmOrderView`(L841-)는 동일한
`quantity - refunded_qty` 패턴을 각자 별도로 가지고 있으나". Verified against source:

| Site | Actual quantity computation | Matches claim? |
|---|---|---|
| `RunComparisonView` L580 | `max((li.quantity or 0) - li.refunded_qty, 0)` | yes |
| `GenerateOrderFileView` L398 | `max((row["quantity"] or 0) - row["refunded_qty"], 0)` | yes |
| `DailyReviewExcelView` L1084/L1099 | refund used only as an exclusion filter; the reported `qty_by_sku` sums raw `li.quantity` | partially |
| `UploadDailyReviewView` L1451 | `total_qty = sum(li.quantity or 0 for li in unordered_lis)` — **no refund term anywhere in the view** | **no** |
| `ConfirmOrderView` L884 | `qty = item.get("quantity")` — quantity comes from the **client request body**; `LineItem.quantity` is never read | **no** |

Consequently spec.md:124's normative claim that these sites "shall continue to use
`LineItem.quantity` unchanged, even for `damaged_exchange` rows" is false for `ConfirmOrderView`,
which does not use `LineItem.quantity` at all. A requirement built on a false premise about the
codebase cannot be validated.

**D4. spec.md:187 / acceptance.md:125-129 — AC-DEX-012b omits the fixture value that makes it
discriminating. — Severity: major**

AC-DEX-012b: "Given a LineItem with `purchase_status="damaged_exchange"`, `damaged_quantity=1`, and
a Refund totaling `1` against it, … the system shall exclude that LineItem from the results
entirely."

`quantity` is never specified. If a test author sets `quantity=1` (the most natural choice when the
value looks irrelevant), then the wrong implementation — the current L292 code, unmodified, using
`quantity` as the base — computes `max(1-1,0)=0` and *also* skips the row. The criterion passes
under both a correct and an incorrect implementation. acceptance.md:129 gestures at the intent
("`quantity`(원래 수량, 0보다 클 수 있음) 기준으로 계산했다면 포함되었을 상황에서도") but the Given
block at acceptance.md:127 still does not pin the value, and spec.md:187 omits the hint entirely.
Fix: state `quantity=10` explicitly in both documents.

Related fixture under-specification (same class, lower severity):
- 시나리오 6 (acceptance.md:69) adds a `cs_required` LineItem but does not say `sku` is non-null;
  a null-`sku` row is not trackable (`purchase_order_views.py:155-157`) and would leave a
  recomputation at `True`, destroying the criterion's discriminating power.
- 시나리오 12 / 12b / 12c (acceptance.md:113-129) never state `sku IS NOT NULL`, which
  `UnorderedItemsView` requires at L275 for the row to appear at all.

**D5. spec.md:96, 108, 110 — repeat-submission behavior on an already-`damaged_exchange` row is
unspecified. — Severity: major**

REQ-DEX-005a (spec.md:96) deliberately makes already-`damaged_exchange` rows re-appear in search
results, so re-submission is an explicitly reachable path. REQ-DEX-009 (spec.md:110) says "store the
submitted quantity in `damaged_quantity`" and REQ-DEX-008 (spec.md:108) bounds input by
`1..quantity` — neither says whether a second submission **overwrites** (3 → then 2 = 2, losing the
first report) or **accumulates** (3 → then 2 = 5). Both implementations satisfy every AC in the
document. Given that REQ-DEX-012 feeds `damaged_quantity` straight into the reorder queue, the two
choices produce materially different reorder quantities.

**D6. spec.md:72-74 vs spec.md:114 — 결정 D has no requirement and no acceptance criterion. —
Severity: major**

결정 D is a user-confirmed decision that deliberately departs from the existing `author=None`
precedent, justified by TRUST 5 Trackable. plan.md:58 implements it
(`author=request.user`). But REQ-DEX-010 (spec.md:114) only requires `note_type`, `assignee`, and
that content include the quantity — the "(결정 D)" tag at the end of that line points at a decision
whose actual content (the author field) the requirement never states. AC-DEX-010 (spec.md:179) and
시나리오 10 (acceptance.md:99-103) likewise never assert `author`. An implementation writing
`author=None`, matching the older precedent, passes every criterion. Either add the author clause to
REQ-DEX-010 + AC-DEX-010, or record 결정 D as explicitly out of scope.

**D7. spec.md:98 — the "전체 출고 수량" column label contradicts the field it sums. — Severity: minor**

REQ-DEX-006 labels the column 전체 출고 수량 (total outbound quantity) but defines it as the sum of
`quantity` (order quantity). This codebase already has a field that literally means 출고 수량:
`LineItem.shipped_quantity` (`backend/order/models.py:221`, SPEC-ORDER-015). AC-DEX-005 does catch a
`shipped_quantity`-based implementation (it would return 0, not 13), so this is a naming/clarity
defect rather than a coverage hole — but the label should be reconciled or the divergence noted
explicitly, since operators reading the screen will read it as "how much has shipped".

**D8. spec.md:155 — AC-DEX-002 is not satisfiable as written. — Severity: minor**

"sharing no component, state, or API module with the `/outbound` or `/rack-number` pages." Verified:
`frontend/src/pages/OutboundPage/index.tsx:2` imports `@/components/ui/button`, and both
`services/outboundApi.ts:1` and `services/rackNumberApi.ts:1` import `{ api } from '@/lib/axios'`.
Any new page will necessarily share both. The SPEC-ORDER-015 precedent phrased the same intent
precisely (`OutboundPage/index.tsx:20-22`: "no tab shell, no
RackNumberPage/rackNumberApi/useRackNumberQueries import"). acceptance.md:27 uses the narrower,
testable phrasing; spec.md:155 should be aligned to it.

**D9. spec.md:169 — AC-DEX-006 references a rule that REQ-DEX-006a does not define. —
Severity: minor**

"Given a parent Order whose stored `ready_to_ship` value would differ from what a fresh
recomputation of **REQ-DEX-006a's rule** would currently produce…" — REQ-DEX-006a (spec.md:100) is a
prohibition ("shall NOT recompute"); it contains no recomputation rule. The intended referent is
`_recompute_order_aggregates` (`purchase_order_views.py:175-186`) / SPEC-ORDER-012 REQ-RTS-002.

**D10. spec.md:165 / acceptance.md:57 — AC-DEX-005a's stated precondition is impossible. —
Severity: minor**

시나리오 5a Given: "부모 Order의 `ready_to_ship`이 `null`(**추적 가능한 LineItem이 하나도 없는
상태**)이다", While: "그 Order에 속한 LineItem이 검색 결과에 포함된다". A row can only be in the
search results if `sku` matched exactly — i.e. `sku IS NOT NULL` — which by definition makes it a
trackable LineItem (`purchase_order_views.py:155-157`). The stated cause and the scenario's own
When-clause are mutually exclusive. The scenario is only constructible with a deliberately stale
stored `null` (direct `Order.objects.filter(...).update(ready_to_ship=None)`), which is a legitimate
fixture but a different rationale. Fix the parenthetical.

**D11. spec.md:124, 137 / acceptance.md:137-141 — the enumerated "5 sites" list is incomplete, and
only 2 of the 5 are regression-covered. — Severity: minor**

- `VendorComparisonView` (`purchase_order_views.py:744-757`) sums `LineItem.quantity` per SKU
  (`total_qty_qs` … `Sum("quantity")`) and feeds it to `auto_select_distributor` — a reorder
  decision driven by quantity. It appears in neither REQ-DEX-012b's list nor the Exclusions entry.
  (`_attach_net_quantity` at L2903-2951 also computes `max(li_qty - refunded, 0)`, but for PO-list
  display rather than reorder candidacy, so its omission is defensible.)
- AC-DEX-012d / 시나리오 12e only exercise `RunComparisonView` and `DailyReviewExcelView`. An
  implementation that also modified `GenerateOrderFileView` (L398) would violate REQ-DEX-012b and
  still pass. Note also that `ConfirmOrderView` cannot be regression-tested this way at all, per D3.

**D12. acceptance.md:161 — Definition of Done omits 결정 D. — Severity: minor**

The `[x]` line records user confirmation of 결정 A and 결정 B only, while spec.md:20 (HISTORY
v1.1.0) and spec.md:72 state that 결정 D was confirmed on the same date. Stale text left by the
1.0.0 → 1.1.0 revision pass.

---

## Chain-of-Verification Pass

Second-look findings — the following were re-checked after the first pass, and three of the twelve
defects above (D3, D10, D11) were found only on re-read:

- **Re-read every REQ entry end-to-end (spec.md:82-124), not a sample.** First pass had accepted the
  `(Unwanted)` labels at face value; the second read showed that four of them carry no If/then
  trigger and that REQ-DEX-012b's subject is the SPEC document itself → MP-2 downgraded to FAIL.
- **Re-verified REQ→AC and AC→REQ mapping for all 18 REQs and all 20 ACs individually** (table in
  the Traceability row above), plus the acceptance.md 시나리오→AC mapping for all 18 scenarios. No
  orphans, no dangling IDs. First-pass conclusion held.
- **Opened all five "excluded" views rather than trusting plan.md's summary** → discovered D3
  (`ConfirmOrderView` takes quantity from the request body, `UploadDailyReviewView` has no refund
  term). This claim had been marked "plausible" in the first pass.
- **Re-read the Exclusions section for specificity, not just presence** (spec.md:128-138): 8 entries,
  all concrete, including a properly labelled "known, deliberate gap". Non-empty and specific — but
  cross-checking the enumeration against `grep`-derived call sites surfaced D11
  (`VendorComparisonView`).
- **Looked for contradictions *between* requirements, not only within them**: AC-DEX-009
  (spec.md:175, ready_to_ship changes) vs REQ-DEX-011 (spec.md:116, `logistics_status` untouched)
  vs `purchase_order_views.py:182-185` — this three-way check is what produced D1. A single-document
  read would not have caught it.
- **Re-checked the 1.0.0 → 1.1.0 revision for stale text**: spec.md 결정 B's "(초안 이력)" paragraph
  (L66) is intentionally labelled and is not stale; spec-compact.md:19/29 and acceptance.md 시나리오
  5/5b are correctly synchronized to 결정 B; the only stale artifact found is D12 (DoD omits 결정 D).
- **Re-verified frontmatter against three sibling SPECs** rather than against memory of the schema →
  confirmed `created_at` is the repository-wide convention, so MP-3's failure is a genuine deviation
  and not an audit-schema artifact.
- **Re-ran the "most plausible wrong implementation" construction against each of the 20 ACs.**
  Result: 14 discriminate cleanly (AC-001, 003, 004, 004a, 005, 005a, 005b, 006, 007, 009a-partial,
  010, 011, 012, 012a, 012c); AC-DEX-009 fails outright (D1); AC-DEX-012b fails conditionally on an
  unstated fixture value (D4); AC-DEX-002 and AC-DEX-008 are weakly worded (D8; "client-side **or**
  server-side" at spec.md:173 is satisfied by client-only validation); AC-DEX-012d is only 2/5
  covered (D11). AC-DEX-009a's "Order aggregate fields unchanged" clause is inherently
  non-discriminating (recomputation on a rejected write is idempotent), but its
  `purchase_status`/`damaged_quantity` clauses carry the criterion.

---

## Regression Check

N/A — iteration 1.

---

## Recommendation

The SPEC is well-researched and its citations are unusually accurate (no fabricated paths, no wrong
line numbers — a real improvement over the two prior SPECs in this repository). The failure is
concentrated in two places: one acceptance criterion asserts behavior the code cannot produce, and
the reorder-substitution criteria leave the most plausible wrong implementations uncaught. Fix the
following before approval.

**Blocking (must fix):**

1. **acceptance.md:87-91 and spec.md:175 — replace the 시나리오 9 fixture.** Read
   `backend/order/purchase_order_views.py:175-186` first. Because REQ-DEX-011 forbids touching
   `logistics_status`, a `received` row stays `ready_to_ship=True` after the damage submission.
   Use a fixture where the transition actually flips the aggregate, e.g. pre-state
   `purchase_status="in_stock"` + `logistics_status="not_shipped"` (True → False), or
   `purchase_status="cs_required"` + `logistics_status="received"` (False → True). Delete the
   incorrect parenthetical rationale at acceptance.md:91. The new criterion must fail when
   `_recompute_order_aggregates([li.order_id])` is omitted.

2. **spec.md:187 and acceptance.md:127 — add `quantity=10` to the AC-DEX-012b fixture** so the
   zero-skip criterion cannot be satisfied by the unmodified `quantity`-based computation at
   `purchase_order_views.py:292`. While there, add `sku` (non-null) to the 시나리오 12 / 12b / 12c
   fixtures and `sku` (non-null) to the added `cs_required` row in 시나리오 6.

3. **plan.md:73 and spec.md:124 — correct the claim about the five excluded sites.** Verified
   actual behavior: `RunComparisonView` L580 and `GenerateOrderFileView` L398 use
   `quantity - refunded_qty`; `DailyReviewExcelView` uses refunds only as an exclusion filter
   (L1084) and reports raw `quantity` (L1099); `UploadDailyReviewView` L1451 uses
   `sum(li.quantity or 0)` with no refund term; `ConfirmOrderView` L884 takes quantity from the
   request body and never reads `LineItem.quantity`. Restate REQ-DEX-012b so it does not assert a
   uniform pattern that does not exist, and note that `ConfirmOrderView` is unaffected by the
   `damaged_quantity` question for a different reason than the other four.

4. **spec.md:5 — rename `created:` to `created_at:`** to match `SPEC-ORDER-015`, `SPEC-ORDER-020`,
   and `SPEC-PURCHASE-ORDER-010`. Populate `issue_number` (spec.md:9) once the tracking issue exists.

5. **spec.md:124 — rewrite REQ-DEX-012b as an EARS statement or delete it.** "This SPEC shall NOT
   modify…" is a scope statement about a document, not system behavior, and it duplicates the
   Exclusions entry at spec.md:137. If a normative form is wanted, use the Unwanted pattern with a
   system subject, e.g. "If a LineItem with `purchase_status == "damaged_exchange"` is processed by
   the 업체 자료 비교 뷰 or the 발주 파일 생성 뷰, then the system shall use `quantity` (not
   `damaged_quantity`) as the base quantity." Apply the same treatment to REQ-DEX-006a (spec.md:100),
   REQ-DEX-011 (spec.md:116), and REQ-DEX-012a (spec.md:122): either give them a genuine If/then
   trigger with "the system" as subject, or relabel them `(Ubiquitous)` negative statements.

6. **spec.md:96/108/110 — specify repeat-submission semantics.** State explicitly whether a second
   damage submission on an already-`damaged_exchange` LineItem overwrites or accumulates
   `damaged_quantity`, and add an AC for the chosen behavior. This directly changes the reorder
   quantity produced by REQ-DEX-012.

7. **spec.md:114/179 — cover 결정 D or drop it.** Add `author` set to the authenticated requesting
   user to REQ-DEX-010, and assert it in AC-DEX-010 / 시나리오 10; otherwise remove the "(결정 D)"
   tag and record the decision as unimplemented.

**Non-blocking (should fix in the same pass):**

8. spec.md:169 — replace "REQ-DEX-006a's rule" with the actual referent
   (`_recompute_order_aggregates` / SPEC-ORDER-012 REQ-RTS-002).
9. spec.md:165 and acceptance.md:57 — remove the impossible "(추적 가능한 LineItem이 하나도 없는
   상태)" rationale; restate the precondition as a deliberately stale stored `null`.
10. spec.md:155 — narrow AC-DEX-002 to the SPEC-ORDER-015 phrasing already used at acceptance.md:27
    (no `OutboundPage`/`RackNumberPage`/`outboundApi`/`rackNumberApi`/`useOutboundQueries`/
    `useRackNumberQueries` import), since shared `ui/button` and `lib/axios` are unavoidable.
11. spec.md:173 — change "client-side **or** server-side" to require server-side rejection
    (client-side additionally).
12. spec.md:98 — reconcile the 전체 출고 수량 label with `LineItem.shipped_quantity`
    (`models.py:221`), or state explicitly why the order quantity carries that label.
13. spec.md:124/137 — add `VendorComparisonView` (`purchase_order_views.py:744-757`) to the
    known-gap enumeration, and extend AC-DEX-012d to cover `GenerateOrderFileView` and
    `UploadDailyReviewView`.
14. spec.md:64 — add an AC covering the null-`quantity` → 0 coercion in the 전체 출고 수량 sum
    (`Sum("quantity")` returns `None`, not `0`, when every row is null).
15. acceptance.md:161 — add 결정 D to the confirmed-decisions DoD line.
16. Consider deleting the ACCEPTANCE CRITERIA block in spec.md (L149-191) in favour of a pointer to
    acceptance.md. It is a near-verbatim duplicate that has already drifted (D4), and it is the main
    source of the Given/When/Then-labelled-as-EARS problem in MP-2.

Verdict: FAIL
