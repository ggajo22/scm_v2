# SPEC Review Report: SPEC-PURCHASE-ORDER-011
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.69

Reasoning context ignored per M1 Context Isolation. This audit is based solely on the four
documents in `.moai/specs/SPEC-PURCHASE-ORDER-011/` (spec.md, plan.md, acceptance.md,
spec-compact.md) at v1.2.0, and on direct reading of every cited source file in `backend/` and
`frontend/`. The iteration-1 report was read only to run the regression check; no claim in it was
taken on trust — every "resolved" verdict below was re-derived from the current documents and the
current source.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  Base series `REQ-DEX-001`..`REQ-DEX-012` at spec.md:122, 126, 128, 132, 134, 138, 144, 148, 150,
  160, 162, 166 — 12 entries, no gaps, no duplicates, uniform 3-digit padding. Ten alphabetic
  suffixes (`005a` L136, `006a` L140, `006b` L142, `009a` L152, `009b` L154, `009c` L156, `009d`
  L158, `012a` L168, `012b` L170, `012c` L172) are declared and justified at spec.md:118. Total 22,
  matching the counts asserted at spec.md:21, spec-compact.md:31, plan.md:11 and acceptance.md:192.
  AC IDs (spec.md:201-249) total 25 with no duplicates, matching spec-compact.md:31 and
  acceptance.md:192. Arithmetic in HISTORY (spec.md:21, "18 → 22", "20 → 25") is correct.

- **[PASS] MP-2 EARS format compliance**
  The four iteration-1 violations are genuinely rewritten, not relabelled:
  - spec.md:140 REQ-DEX-006a — "**If** the system serves a search result row per REQ-DEX-006,
    **then the system shall NOT** recompute…" (was a negative ubiquitous with no trigger).
  - spec.md:162 REQ-DEX-011 — "**If** a damage submission (REQ-DEX-009) is processed for a LineItem,
    **then the system shall NOT** modify…" (subject was "A damage submission").
  - spec.md:168 REQ-DEX-012a — "**If** the reorder-queue view … computes …, **then the system
    shall** use `quantity`…" (subject was "The base-quantity substitution").
  - spec.md:170 REQ-DEX-012b — "**If** a LineItem with `purchase_status == "damaged_exchange"` is
    evaluated by … **then the system shall** continue to read/report…" (subject was "This SPEC").
  All 25 acceptance criteria (spec.md:201-249) were re-read individually; the
  "Given…when…the system shall" hybrid flagged in iteration 1 is gone from every one. Each now
  matches exactly one pattern — e.g. Event-Driven at L225 ("When a damage submission of `3` is made
  for a LineItem with `quantity=8` …, the system shall set…"), Unwanted at L241 ("If the
  reorder-queue view is queried for …, then the system shall exclude…"), State-Driven at L231
  ("While an Order's non-cancelled trackable LineItem set contains …, the system shall compute…").
  Residual (not MP-level, see D19): spec.md:118 claims every `(Unwanted)` item takes "the system"
  as subject, but REQ-DEX-006b (L142) reads "…then **that LineItem's `quantity`** shall NOT be
  included"; and AC-DEX-001's second clause (L201) reads "**applying the migration** shall NOT
  alter…". Both keep a valid If/then or ubiquitous structure, so MP-2 stands.

- **[PASS] MP-3 YAML frontmatter validity**
  `id: SPEC-PURCHASE-ORDER-011` (spec.md:2), `version: 1.2.0` (L3), `status: draft` (L4),
  `created_at: 2026-08-14` (L5 — the iteration-1 `created:` deviation is fixed and now matches
  `.moai/specs/SPEC-ORDER-020/spec.md:5` and `.moai/specs/SPEC-ORDER-015/spec.md:5`),
  `priority: High` (L8), `labels: [purchase-order, damaged-exchange, reorder-queue, frontend]`
  (L10, array). All six required fields present with correct types. `issue_number: 0` (L9) is not a
  required field and the rebuttal at spec.md:21 ("발급 전 플레이스홀더") is accepted — not re-raised
  per audit instruction 3.

- **[N/A] MP-4 Section 22 language neutrality**
  N/A: single-stack SPEC (Django/DRF + React/TS). No multi-language tooling content in any of the
  four documents.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements that a reasonable engineer would resolve consistently | REQ-DEX-009d (spec.md:158) says "the system shall NOT modify that Order's `status` field", but `_recompute_order_aggregates` writes `status` in the same UPDATE for every order (`purchase_order_views.py:188-195`) — the new 9th call site therefore does write `status` (D16). REQ-DEX-009c (spec.md:156) and REQ-DEX-012b/012c (L170-172) embed function names, file paths and line numbers inside REQUIREMENTS, contradicting the document's own rule at spec.md:42 ("이 문서는 관찰 가능한 동작(WHAT)만 규정한다") (D18). Counterweight: the D7/D8/D9/D10 clarity fixes at spec.md:138, 203, 213, 219 are all concrete and verified |
| Completeness | 0.50 | 0.50 — multiple sections substantively incomplete for the newly expanded scope | No requirement and no exclusion for backfilling `Order.ready_to_ship` after the rule change, despite the direct in-repo precedent `backend/order/migrations/0033_backfill_order_ready_to_ship.py` established by SPEC-ORDER-012 REQ-RTS-006 (D13, blocking). The "verified by full grep" downstream-consumer list at spec.md:106-110 omits `OrderResyncView` (`backend/order/views.py:188`, `POST /api/orders/<pk>/sync/`, serializes at views.py:229) (D15). The regression suite list at acceptance.md:182 omits `test_daily_review_upload.py`, the only existing suite where `damaged_exchange` rows actually flow through a `_recompute_order_aggregates` caller (D17). All required sections present: HISTORY (L15-21), 문제 정의 (L25-31), 솔루션 개요 (L33-42), 범위 (L44-50), REQUIREMENTS (L116-172), ACCEPTANCE CRITERIA (L197-249), Exclusions (L176-186, 8 specific entries) |
| Testability | 0.50 | 0.50 — several ACs fail to discriminate or assert an outcome a correct implementation may not produce | Three of the five newly added ACs fail the non-discriminating-criteria test: AC-DEX-009c (spec.md:231 / acceptance.md:113-117) yields `False` under both the modified and unmodified rule (D14); AC-DEX-005c (spec.md:217 / acceptance.md:69-73) passes against a bare `Sum("quantity")` because SQL `SUM` returns `9`, not `NULL`, for the stated fixture (D20); AC-DEX-012e (spec.md:247 / acceptance.md:163-167) does not pin PurchaseOrder linkage and fails against a correct implementation when the row is PO-linked (D21). Counterweight: AC-DEX-009 (spec.md:225) now discriminates cleanly against both wrong implementations — see the trace table below — and AC-DEX-012b (L241), AC-DEX-012d (L245), AC-DEX-009b (L229), AC-DEX-010 (L233), AC-DEX-008 (L223) are all binary and enumerate the wrong answers |
| Traceability | 1.00 | 1.0 — every REQ has at least one AC, every AC references an existing REQ, no orphans | All 22 REQs covered: 001→AC-001; 002,003→AC-002; 004→AC-003; 005→AC-004; 005a→AC-004a; 006→AC-005,005a,005c; 006a→AC-006; 006b→AC-005b; 007→AC-007; 008→AC-008; 009→AC-009; 009a→AC-009a; 009b→AC-009b; 009c→AC-009,AC-009c; 009d→AC-009c; 010→AC-010; 011→AC-011; 012→AC-012,012a,012b; 012a→AC-012c; 012b→AC-012d,012e; 012c→AC-012f. All 25 `Traces:` targets exist. acceptance.md maps 25 scenarios 1:1 onto the 25 ACs (시나리오 1,2,3,4,4b,5,5a,5b,5c,6,7,8,9,9a,9b,9c,10,11,12,12b,12c,12d,12e,12f,12g) with no orphan and no dangling ID |

---

## Priority 1 — Is D1 genuinely fixed?

**Yes.** Verified by re-deriving the outcome from source rather than from the SPEC's assertion.

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

AC-DEX-009 fixture (spec.md:225 / acceptance.md:97-99): one trackable LineItem, `quantity=8`,
`purchase_status="unordered"`, `logistics_status="received"`, pre-state `ready_to_ship=True`.
Submission of `3`; `logistics_status` stays `"received"` per REQ-DEX-011.

| Implementation | Post-state row | Computed `ready_to_ship` | AC-DEX-009 outcome |
|---|---|---|---|
| Correct (recompute called + REQ-DEX-009c short-circuit) | `("received","damaged_exchange")` | `any(cs_required or damaged_exchange)` → **False** | expects False → **passes** |
| (a) recompute never called | — | stored value untouched → **True** | **fails** |
| (b) recompute called, no new branch | `("received","damaged_exchange")` | `all("received"=="received")` → **True** | **fails** |

The criterion discriminates against both wrong implementations, exactly as instructed. The
factually-wrong parenthetical from v1.1.0 is deleted and replaced with the correct cause at
acceptance.md:99 ("**이 전환은 `logistics_status`가 바뀌어서가 아니다**"). D1 and D2 are resolved at
the requirement level, not by rewording the test.

---

## Priority 2 — Audit of the newly expanded scope

**Call sites — complete and accurate (PASS).** `grep -n "_recompute_order_aggregates" backend/`
returns exactly 8 invocation lines in production code; the enclosing class of each was resolved
mechanically:

| Line | Enclosing class | In spec.md:95-102 list? |
|---|---|---|
| 1014 | `ConfirmOrderView` (L841) | yes (#5) |
| 1640 | `UploadDailyReviewView` (L1229) | yes (#8) |
| 1773 | `UploadVendorShipmentView` (L1723) | yes (#1) |
| 1840 | `UploadWarehouseReceiptView` (L1788) | yes (#2) |
| 1892 | `LineItemStatusUpdateView` (L1863) | yes (#6) |
| 1950 | `LineItemBulkStatusUpdateView` (L1908) | yes (#7) |
| 1999 | `LineItemLogisticsStatusUpdateView` (L1966) | yes (#3) |
| 2057 | `LineItemLogisticsStatusBulkUpdateView` (L2010) | yes (#4) |

Exact 8-for-8 match, no omission, no phantom. The "fan-in 8→9" claim (spec.md:104, plan.md:35,
plan.md:140) is correct.

**Downstream consumers of `Order.ready_to_ship` — one omission (D15).** My own grep across
`backend/` and `frontend/`:

| Site | In spec.md:106-110? |
|---|---|
| `backend/order/serializers.py:170` (`OrderDetailSerializer`, class L141, Meta ends L171) | yes |
| `backend/order/views.py:31` `OrderDetailView` (`GET /api/orders/<pk>/`) | yes |
| `backend/order/views.py:188` **`OrderResyncView`** (`POST /api/orders/<pk>/sync/`, `urls.py:58`) — returns `OrderDetailSerializer(order).data` at views.py:229 | **no — D15** |
| `backend/order/serializers.py:14-36` `OrderListSerializer` — does NOT expose it (SPEC's negative claim verified correct) | yes |
| `frontend/src/pages/OrderDetailPage.tsx:247,256` (출고가능 / 출고불가 badges) | yes |
| `frontend/src/types/order.ts:208` (type declaration only) | not listed; immaterial |
| `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx` — consumes the same `useOrderDetail` payload but reads only `line_items`; `ready_to_ship` appears solely in its test fixture (`SearchTab.test.tsx:124`) | not a value consumer; correctly absent |
| `backend/order/shopify_orders.py:142` — comment asserting resync never writes the field; not a consumer | correctly absent |
| `backend/order/migrations/0033_backfill_order_ready_to_ship.py:55-63` — a **second implementation of the same rule** | **not mentioned anywhere — see D13** |

**`Order.status` is unaffected — the aggregate rule claim is TRUE, the requirement wording is
not (D16).** plan.md:85-97's diff touches only the `ready_to_ship` branch (L176-186); the `status`
branch (`purchase_order_views.py:167-173`) derives purely from `logistics_status`, which
REQ-DEX-011 forbids the submission from changing. So no `status` **value** changes as a result of
the new branch. However `_recompute_order_aggregates` writes `status` unconditionally in the same
`Case/When` UPDATE (L188-195), so the new 9th caller does write the column — and for an Order whose
stored `status` was stale, the persisted value will change. REQ-DEX-009d's literal "shall NOT modify
that Order's `status` field" is therefore not accurate as a runtime statement.

**Characterization-test requirement — present, but not specific enough and partly redundant
(D17/D22).** It is stated in four places: 결정 E (spec.md:114), plan.md M1.5 (L16), plan.md:122
(실행 제약사항), acceptance.md:179 (quality gate), acceptance.md:191 (DoD). It names the two
behaviors to freeze (`cs_required` short-circuit; `all(received/in_stock)`) and the code region
(`purchase_order_views.py:175-186`). Gaps:
- It omits the third existing branch — `if not non_cancelled: ready_to_ship = None` (L177-178) —
  which is the branch most at risk if an implementer restructures the `if/elif/else` chain.
- It does not acknowledge that `backend/order/tests/test_spec_012.py:169-285` (class T2) **already
  is** that characterization suite: `test_all_cancelled_sets_null`,
  `test_zero_trackable_lineitems_sets_null`, `test_cs_required_hard_blocks_to_false`,
  `test_cancelled_items_excluded_from_cs_check`, `test_in_stock_alone_satisfies_true`,
  `test_received_alone_satisfies_true`, `test_partial_satisfaction_sets_false`,
  `test_status_and_ready_to_ship_computed_together`, `test_recompute_overwrites_stale_ready_to_ship`.
  M1.5 as written asks for new tests duplicating all nine.
- Good news, independently verified: `grep -c damaged_exchange backend/order/tests/test_spec_012.py`
  = 0, so none of those nine assertions breaks under the new rule. acceptance.md:182's "전량 통과"
  demand is achievable.

---

## Defects Found

**D13. spec.md:156, 176-186 / plan.md:15, 35 / acceptance.md:183 — the `ready_to_ship` rule is
changed with no backfill requirement and no exclusion recording the omission. — Severity: major
(blocking)**

REQ-DEX-009c redefines how `Order.ready_to_ship` is computed. Every Order that already contains a
`damaged_exchange` LineItem — a status shipped by SPEC-PURCHASE-ORDER-010 and reachable today
through the Daily Review upload path (`test_daily_review_upload.py:1112`
`test_damaged_exchange_selection_sets_status_and_creates_note`) and through
`LineItemStatusUpdateView` — carries a stored `ready_to_ship` computed under the **old** rule. After
this SPEC ships, those rows stay stale until some unrelated write happens to trigger a recompute for
that Order, because:
- REQ-DEX-006a (spec.md:140) explicitly forbids the new search page from recomputing;
- `OrderDetailView` and `OrderResyncView` only read;
- nothing in the SPEC sweeps existing rows.

Net effect: the very symptom the SPEC exists to remove ("파손 접수 후에도 `ready_to_ship`이 `True`로
남는다", spec.md:31) persists indefinitely for all pre-existing damage records, and the new page will
display the stale `True` by design.

The precedent is in this repository and is directly on point: when SPEC-ORDER-012 introduced this
same field it shipped `backend/order/migrations/0033_backfill_order_ready_to_ship.py` (REQ-RTS-006)
plus `backend/order/tests/test_backfill_order_ready_to_ship_migration.py`. The word "backfill"
appears in this SPEC only at spec.md:46 and plan.md:33, and both occurrences are about
`damaged_quantity` ("데이터 백필 불필요"), not about `ready_to_ship`. Note also that
`0033_backfill_order_ready_to_ship.py:55-63` contains a **second copy** of the rule; after this
change the two copies intentionally diverge, and no document says so.

Required: either add a REQ + AC for a one-time `ready_to_ship` backfill migration mirroring
migration 0033, or add an explicit Exclusions entry stating that pre-existing damaged Orders keep a
stale aggregate until their next write, with the user's confirmation recorded as the other decisions
are.

**D14. spec.md:231 / acceptance.md:113-117 — AC-DEX-009c does not discriminate: the fixture yields
`ready_to_ship=False` under BOTH the modified and the unmodified rule. — Severity: major**

시나리오 9c fixture: (a) `purchase_status="damaged_exchange"`, `logistics_status="not_shipped"`;
(b) `purchase_status="unordered"`, `logistics_status="received"`.

- With the REQ-DEX-009c short-circuit: `any(cs_required or damaged_exchange)` → `False`.
- **Without** it: row (a) satisfies neither `logistics_status == "received"` nor
  `purchase_status == "in_stock"`, so `all(...)` at `purchase_order_views.py:182-185` is already
  `False`.

Identical observable output. This is the SPEC's only unit-level criterion for the new branch, and it
verifies nothing. The scenario's own parenthetical — "(b) … 단독이었다면 `all(...)` 판정을
만족시켰을 행" — describes discriminating power the fixture does not have, because `all()` requires
*every* row to satisfy the disjunct, not any one row.

Note spec.md:231 does not pin row (a)'s `logistics_status` at all, so the AC and the executable
scenario are not even equivalent: a test author reading spec.md alone might pick `"received"` (which
would discriminate) while acceptance.md mandates `"not_shipped"` (which does not).

Fix: set row (a) to `logistics_status="received"`, `purchase_status="damaged_exchange"` in **both**
documents. Then the unmodified rule yields `True` and the modified rule yields `False`.

**D15. spec.md:106-110 — the "backend/frontend 전체 grep으로 확인" consumer enumeration omits
`OrderResyncView`. — Severity: minor**

`backend/order/views.py:188` `class OrderResyncView(APIView)` (registered at
`backend/order/urls.py:58` as `orders/<int:pk>/sync/`) returns `OrderDetailSerializer(order).data`
at views.py:229 — a second endpoint exposing `ready_to_ship`. The claim of exhaustiveness makes the
omission a factual error rather than a stylistic one. Impact is low (same serializer, same field),
but `backend/order/tests/test_order_resync.py` and
`backend/order/tests/test_spec_012.py:609` (`test_resync_does_not_change_ready_to_ship`) belong in
the regression set for the same reason `test_spec_012.py` does.

**D16. spec.md:158 (REQ-DEX-009d), spec.md:184, acceptance.md:117 — "shall NOT modify `Order.status`"
is literally false for the new call site. — Severity: minor**

`_recompute_order_aggregates` writes both columns in one statement
(`purchase_order_views.py:188-195`), so the new damage-submission endpoint (the 9th caller) *does*
write `status`. The intended meaning — "the new short-circuit does not change how `status` is
computed; `status` continues to follow the unchanged `logistics_status` rule at L167-173" — is
correct and verified, but the current wording invites an implementer to avoid calling the shared
function or to add an `update_fields`-style carve-out, which would contradict plan.md:62. Restate as
"…the system shall continue to compute `Order.status` by the existing `logistics_status` aggregate
rule, unchanged by this SPEC". The Exclusions entry at spec.md:184 and the diff-level check at
acceptance.md:184 are fine as written; only the runtime-behavior wording needs correcting.

**D17. acceptance.md:182 — the regression suite enumeration omits `test_daily_review_upload.py`. —
Severity: minor**

The listed suites are `test_purchase_order_models.py`, `test_purchase_orders.py`, `test_spec_012.py`
and `OrderDetailPage.test.tsx`. But `backend/order/tests/test_daily_review_upload.py` contains 25
`damaged_exchange` occurrences and exercises `UploadDailyReviewView`, which is call site #8 at
`purchase_order_views.py:1640` — i.e. it is the single existing test file where a
`damaged_exchange` row actually passes through `_recompute_order_aggregates`. (Verified it contains
no `ready_to_ship` assertion, so nothing breaks — but it is precisely where an unexpected
interaction would first appear, and it is absent from the list.)

**D18. spec.md:156, 170, 172 vs spec.md:42 — REQUIREMENTS embed implementation detail, contradicting
the document's own stated rule. — Severity: minor**

spec.md:42 states "구체적인 코드 위치, 함수/클래스명, 엔드포인트 경로는 `plan.md`에 있다 — 이 문서는
관찰 가능한 동작(WHAT)만 규정한다." Yet REQ-DEX-009c (L156) names `_recompute_order_aggregates`,
prescribes "evaluated as a short-circuit before the existing `all(...)` disjunction" and cites
`purchase_order_views.py:179-180`; REQ-DEX-012b (L170) carries a full paragraph of L580/L398/L1084/
L1099/L1451/L744-757 findings; REQ-DEX-012c (L172) cites L884-886 and `item.get("quantity")`. The
evaluation-order clause in REQ-DEX-009c *is* observable (see D14's table) and should stay, but it can
be expressed behaviorally: "…shall set `ready_to_ship` to `False` regardless of any LineItem's
`logistics_status`". The file:line paragraphs belong in plan.md, which already carries them verbatim
at plan.md:115.

**D19. spec.md:118 vs spec.md:142 — self-contradicting claim about `(Unwanted)` subjects. —
Severity: minor**

spec.md:118 asserts "`(Unwanted)` 항목은 **전량** … 시스템을 주어로 삼는다", but REQ-DEX-006b (L142)
reads "…then **that LineItem's `quantity`** shall NOT be included…". Either fix the requirement
("…then the system shall NOT include that LineItem's `quantity` in…") or soften the claim.

**D20. spec.md:217 / acceptance.md:69-73 — AC-DEX-005c's fixture cannot expose the defect it was
added for. — Severity: major**

The criterion was added in response to iteration-1 Recommendation 14, whose stated rationale was
that "`Sum("quantity")` returns `None`, not `0`, when **every** row is null". The fixture chosen is
one `quantity=null` row plus one `quantity=9` row. SQL `SUM` ignores NULL inputs, so a naive
`Sum("quantity")` with no `Coalesce` returns `9` for this fixture and passes the criterion. The
implementation plan.md:53 prescribes (`Coalesce(Sum("quantity"), 0)`) is therefore unverified: the
most plausible wrong implementation — omitting `Coalesce` — is indistinguishable.

Fix: use a parent Order whose trackable non-cancelled LineItems **all** have `quantity=null`, and
require the reported 전체 출고 수량 to be `0` rather than `null`/`None`. Optionally keep the
mixed-null case as a second assertion.

**D21. spec.md:247 / acceptance.md:163-167 — AC-DEX-012e omits the fixture attribute that decides
whether a correct implementation can satisfy it. — Severity: major**

`VendorComparisonView`'s aggregate is
`LineItem.objects.filter(purchase_orders__isnull=True, sku__isnull=False).values("sku").annotate(total=Sum("quantity"))`
(`purchase_order_views.py:744-750`). Unlike `_reorder_candidate_filter` (L107-110) and
`GenerateOrderFileView` (L382-387), it has **no** `damaged_exchange` exception. Meanwhile
`purchase_order_views.py:373-381` records the project's own finding that "damaged_exchange SKUs are
realistically still linked to their ORIGINAL PurchaseOrder".

Neither AC-DEX-012e nor 시나리오 12f pins `purchase_orders` linkage, and 시나리오 12f inherits
시나리오 12e's fixture, which does not pin it either. Consequently:
- fixture unlinked → view reports `10`; criterion passes;
- fixture PO-linked (the realistic damaged case) → the SKU is excluded from `qty_by_sku` entirely and
  the view reports `0`; the criterion "the system shall report a quantity based on `quantity` (`10`)"
  **fails against a correct, unmodified implementation** — the same failure class as iteration-1 D1.

This also weakens REQ-DEX-012b's and spec.md:185's characterization of `VendorComparisonView` as
carrying "논리적으로는 동일한 결함": it only carries that latent defect for damaged rows that are
*not* PO-linked. Fix: pin `purchase_orders__isnull=True` in the fixture in both documents, and note
the linkage caveat in the Exclusions entry.

**D22. plan.md:16 (M1.5) / acceptance.md:179 — the characterization-test requirement is
under-specified and duplicates an existing suite. — Severity: minor**

It names only two of the three existing branches (the `if not non_cancelled → None` branch at
`purchase_order_views.py:177-178` is omitted), and it does not identify
`backend/order/tests/test_spec_012.py:169-285` (class T2, nine tests) as the pre-existing frozen
baseline — so M1.5 as written asks for tests that already exist. State which existing assertions
constitute the baseline and which (if any) must be extended.

---

## Chain-of-Verification Pass

Second-look findings. Three of the ten defects above (D20, D21, D22) were found only on re-read;
D13 was found by asking a question the SPEC never asks about itself.

- **Re-read all 22 REQ entries end-to-end (spec.md:122-172), not a sample.** First pass had accepted
  the MP-2 fixes; the second read surfaced the passive subject in REQ-DEX-006b (D19) and the
  WHAT/HOW leak that contradicts spec.md:42 (D18).
- **Re-verified REQ→AC and AC→REQ for all 22 REQs and all 25 ACs individually**, plus the
  25 acceptance.md 시나리오→AC mappings. No orphan, no dangling ID, no count drift across the four
  documents (22/25 asserted consistently at spec.md:21, spec-compact.md:31, plan.md:11,
  acceptance.md:177, acceptance.md:192). First-pass conclusion held.
- **Opened every `file:line` citation added or changed in v1.2.0 rather than trusting them.** All
  correct: `purchase_order_views.py:182-185` (the `all(...)` expression), `:179-180` (`cs_required`
  short-circuit), `:167-173` (`status`), `:113-122` (fan-in comment listing exactly the 8 classes),
  `:176` (`non_cancelled`), `:154-158` (trackable query), `:188-195` (the two-column UPDATE),
  `:580` (`RunComparisonView`, `max((li.quantity or 0) - li.refunded_qty, 0)`), `:398`
  (`GenerateOrderFileView`, same shape on a `values()` row), `:1084` (`DailyReviewExcelView` refund
  used only as an exclusion filter) and `:1099-1100` (raw `quantity` accumulation), `:1451`
  (`UploadDailyReviewView`, `sum(li.quantity or 0 …)`, no refund term), `:744-757`
  (`VendorComparisonView`, `Sum("quantity")` over `purchase_orders__isnull=True`), `:886`
  (`ConfirmOrderView`, `qty = item.get("quantity")`), `:251/292/314` (`UnorderedItemsView`),
  `:1863/1900` (`LineItemStatusUpdateView`), `:2284/2301-2302/2341`
  (`LineItemRackNumberSummaryView`), `:86-110` (`_reorder_candidate_filter`),
  `serializers.py:141-171` with `"ready_to_ship"` at L170, `serializers.py:14-36` (no exposure —
  negative claim verified), `models.py:156-167` + `:190-194` (choices + field), `models.py:221`
  (`shipped_quantity`), `mx.yaml:175` (`anchor_per_file: 3`),
  `OrderDetailPage.tsx:240-260` (the 3-state badge), `router/index.tsx:122-128`,
  `Sidebar.tsx:3` and `:68-74`, `urls.py:70-72` and `:84-106`, latest migration
  `0036_order_name_index.py`. **No fabricated path and no wrong line number in any of the four
  documents.** This is the third consecutive SPEC in this repository with clean citations.
- **Verified the two contested rebuttals rather than deferring to them.** (a) `issue_number: 0` is
  not an MP-3 required field — rebuttal accepted, not re-raised. (b) The claim at spec.md:199 /
  spec.md:21 that rewriting the spec.md AC block in place "SPEC-PURCHASE-ORDER-010 v1.2.0에서
  확립된 동일 수정 관례를 따름" is **true**: `.moai/specs/SPEC-PURCHASE-ORDER-010/spec.md:216-242`
  contains exactly such a block in pure EARS prose (e.g. L224 "**AC-DMG-001** (Ubiquitous) —
  Traces: REQ-DMG-001. The system shall accept…"). Precedent verified, rebuttal accepted, not
  re-raised.
- **Re-checked the Exclusions section for specificity, not just presence** (spec.md:176-186): 8
  entries, all concrete; the `Order.ready_to_ship` entry was correctly *removed* from the exclusion
  list and replaced by an accurate `Order.status`-only entry (L184), consistently mirrored at
  spec-compact.md:72. This re-read is what exposed that no entry covers pre-existing stale
  aggregates (D13).
- **Looked for contradictions between documents after two revision passes.** spec.md ACs and
  acceptance.md 시나리오 were compared pairwise for all 25: fixtures agree everywhere (4-row fixture
  spec.md:211 ↔ acceptance.md:53-55; `quantity=10`/`damaged_quantity=1`/refund 1 at spec.md:241 ↔
  acceptance.md:147; 3-then-2 overwrite at spec.md:229 ↔ acceptance.md:109-111; body `quantity=7`
  at spec.md:249 ↔ acceptance.md:171). The iteration-1 D4-class drift has not reappeared. The one
  residual mismatch is AC-DEX-009c, where spec.md under-specifies what acceptance.md over-commits
  (D14).
- **Re-ran the "most plausible wrong implementation" construction against every AC that is new or
  changed since iteration 1** (AC-DEX-002, 005a, 005c, 006, 008, 009, 009b, 009c, 010, 012b, 012d,
  012e, 012f). Result: 10 discriminate cleanly; AC-DEX-009c and AC-DEX-005c do not discriminate at
  all (D14, D20); AC-DEX-012e is unsatisfiable under a plausible fixture (D21).
- **Checked whether the expanded scope breaks existing tests, rather than assuming acceptance.md:182
  is achievable.** `grep -c damaged_exchange` returns 0 for `test_spec_012.py`, 0 for
  `test_purchase_orders.py`'s `ready_to_ship` assertions (that file has 49 `damaged_exchange` hits
  but no `ready_to_ship` assertion), and 25 for `test_daily_review_upload.py` (no `ready_to_ship`
  assertion). Conclusion: the "전량 통과" demand is achievable — but the enumeration is missing the
  one file where the interaction actually occurs (D17).

---

## Regression Check (defects from iteration 1)

| # | Description | Status | Evidence |
|---|---|---|---|
| D1 | 시나리오 9 asserts an outcome a correct implementation cannot produce | **RESOLVED** | Requirement changed, not the test: REQ-DEX-009c (spec.md:156) + AC-DEX-009 (spec.md:225) + acceptance.md:95-99. Discrimination re-derived from `purchase_order_views.py:176-185` — see the Priority 1 table; fails against both (a) no recompute and (b) recompute without the branch |
| D2 | REQ-DEX-009's recompute obligation had zero coverage | **RESOLVED** | Same fixture now flips `True→False`; omitting `_recompute_order_aggregates([li.order_id])` leaves a stale `True` (acceptance.md:99) |
| D3 | False claim that 5 sites share one `quantity - refunded_qty` pattern | **RESOLVED** | REQ-DEX-012b (spec.md:170) now states each site's actual computation; all five re-verified against source (L580, L398, L1084/L1099, L1451, L744-757). `ConfirmOrderView` split out into REQ-DEX-012c (L172) with the correct structural reason, verified at L886 |
| D4 | AC-DEX-012b omitted the discriminating fixture value | **RESOLVED** | `quantity=10` pinned at spec.md:241 and acceptance.md:147; `sku` not null added to 시나리오 6 (L77), 12 (L135), 12c (L147), inherited by 12b (L141) |
| D5 | Repeat-submission semantics undefined | **RESOLVED** | REQ-DEX-009b (spec.md:154, overwrite) + AC-DEX-009b (L229) + 시나리오 9b (acceptance.md:107-111), asserting `2` not `5` |
| D6 | 결정 D had no REQ and no AC | **RESOLVED** | `author` clause added to REQ-DEX-010 (spec.md:160); AC-DEX-010 (L233) asserts `author` equals the authenticated user "(not `null`)"; acceptance.md:123 explicitly fails an `author=None` implementation |
| D7 | 전체 출고 수량 label vs `shipped_quantity` | **RESOLVED** | spec.md:138 second sentence reconciles the two and cites `models.py:221`, verified to be `shipped_quantity = models.IntegerField(default=0)` |
| D8 | AC-DEX-002 unsatisfiable as written | **RESOLVED** | spec.md:203 narrowed to the import-exclusion list with shared primitives explicitly out of scope; acceptance.md:29 matches |
| D9 | AC-DEX-006 cited a non-existent "REQ-DEX-006a's rule" | **RESOLVED** | spec.md:219 now cites `_recompute_order_aggregates` / SPEC-ORDER-012 REQ-RTS-002; acceptance.md:79 matches |
| D10 | AC-DEX-005a's precondition was impossible | **RESOLVED** | spec.md:213 and acceptance.md:59 replace it with a deliberately stale stored `null` |
| D11 | `VendorComparisonView` missing; only 2 of 5 sites regression-covered | **RESOLVED**, but the fix introduced D21 | spec.md:170 and 185 now enumerate `VendorComparisonView`; AC-DEX-012d (L245) covers 4 sites and AC-DEX-012e (L247) the 5th. The new AC-DEX-012e fixture is defective (D21) |
| D12 | DoD omitted 결정 D | **RESOLVED** | acceptance.md:196 (결정 D) and :197 (결정 E) both added |
| MP-2 | EARS violations in 4 REQs + 13 hybrid ACs | **RESOLVED** | See MP-2 above |
| MP-3 | `created_at` missing | **RESOLVED** | spec.md:5 |
| Rec. 11 | "client-side or server-side" | **RESOLVED** | spec.md:223 makes server-side mandatory; acceptance.md:93 matches |
| Rec. 14 | null-`quantity` AC | **ADDRESSED BUT DEFECTIVE** | AC-DEX-005c added (spec.md:217) with a fixture that cannot expose the defect — D20 |
| Rec. 16 | delete spec.md AC block | **CONTESTED — rebuttal accepted** | SPEC-PURCHASE-ORDER-010 spec.md:216-242 precedent verified; not re-raised |
| — | `issue_number: 0` | **CONTESTED — rebuttal accepted** | Not an MP-3 required field; not re-raised |

No stagnation: every iteration-1 defect changed state. All twelve are resolved. **The failure in this
iteration is caused entirely by the newly expanded scope**, not by unfixed prior work.

---

## Recommendation

The revision is substantive and honest: D1 was fixed by changing the requirement rather than the
test, and the discrimination claim at acceptance.md:99 holds when re-derived from source. Citation
accuracy remains excellent — 30+ references re-opened, zero fabrications. The remaining failures are
all in the code the v1.2.0 expansion newly touches.

**Blocking (must fix):**

1. **Add a `ready_to_ship` backfill requirement, or an explicit exclusion (D13).** Read
   `backend/order/migrations/0033_backfill_order_ready_to_ship.py` first — SPEC-ORDER-012 shipped
   exactly this when it introduced the rule. Without it, every Order whose LineItem was set to
   `damaged_exchange` before this SPEC ships keeps a stale `ready_to_ship=True`, and REQ-DEX-006a
   guarantees the new page will show it. Either add REQ + AC for a one-time migration mirroring 0033,
   or add an Exclusions entry stating the stale-aggregate window and record the user's confirmation
   as 결정 F. Also note in 관련 SPEC (spec.md:191) that migration 0033 now contains a deliberately
   divergent copy of the rule.

2. **Repair AC-DEX-009c's fixture (D14).** In spec.md:231 and acceptance.md:115, set the
   `damaged_exchange` row to `logistics_status="received"`. As written both rows are non-satisfying
   under the old rule, so the expected `False` is produced with or without the new branch and the
   criterion verifies nothing. After the change: unmodified → `True`, modified → `False`.

3. **Repair AC-DEX-005c's fixture (D20).** In spec.md:217 and acceptance.md:71, make **all**
   trackable non-cancelled LineItems `quantity=null` and require `0`. SQL `SUM` returns `9` for the
   current mixed fixture, so a `Sum("quantity")` without the `Coalesce` prescribed at plan.md:53
   passes today.

4. **Pin `purchase_orders__isnull=True` in AC-DEX-012e / 시나리오 12f (D21).**
   `VendorComparisonView` (`purchase_order_views.py:744-750`) has no `damaged_exchange` linkage
   exception, and `purchase_order_views.py:373-381` records that damaged rows are realistically
   PO-linked. Unpinned, the criterion fails against a correct implementation. Qualify the
   "논리적으로 동일한 결함" claim at spec.md:170/185 accordingly.

**Non-blocking (should fix in the same pass):**

5. spec.md:158 — restate REQ-DEX-009d as "shall continue to compute `Order.status` by the existing
   `logistics_status` aggregate rule, unchanged by this SPEC"; the current wording is literally false
   for the new call site, which writes `status` at `purchase_order_views.py:188-195` (D16).
6. spec.md:107 — add `OrderResyncView` (`backend/order/views.py:188`, serializes at views.py:229,
   routed at `urls.py:58`) to the downstream-consumer list, and add `test_order_resync.py` /
   `test_spec_012.py:609` to acceptance.md:182 (D15).
7. acceptance.md:182 — add `backend/order/tests/test_daily_review_upload.py` to the regression set;
   it is the only existing suite where a `damaged_exchange` row passes through a
   `_recompute_order_aggregates` caller (`purchase_order_views.py:1640`) (D17).
8. plan.md:16 / acceptance.md:179 — name the third existing branch
   (`if not non_cancelled: ready_to_ship = None`, `purchase_order_views.py:177-178`) in the
   characterization-test requirement, and identify `test_spec_012.py:169-285` (class T2, nine tests)
   as the pre-existing baseline so M1.5 does not duplicate it (D22).
9. spec.md:156, 170, 172 — move the file:line paragraphs out of REQUIREMENTS into plan.md (which
   already carries them at plan.md:115), per spec.md:42's own rule; keep REQ-DEX-009c's
   evaluation-order clause but express it behaviorally ("regardless of any LineItem's
   `logistics_status`") (D18).
10. spec.md:142 — give REQ-DEX-006b "the system" as subject, or soften the "전량" claim at
    spec.md:118 (D19).
11. Cosmetic: the ACs and scenarios now carry inline review-history annotations ("D4 correction",
    "uncounted Recommendation #11 correction", "the auditor identified (D2)") at spec.md:203, 213,
    219, 223, 225, 241, 245, 247, 249 and acceptance.md:29, 59, 79, 99, 149, 161. Revision history
    belongs in HISTORY (spec.md:21), which already records all of it; normative criteria read
    cleaner without it. The *substantive* "an implementation that … fails this criterion" clauses
    should stay — they are what makes the criteria auditable.

Verdict: FAIL
