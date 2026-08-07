# SPEC Review Report: SPEC-ORDER-011
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.56

Reasoning context ignored per M1 Context Isolation. This audit is based solely on `.moai/specs/SPEC-ORDER-011/spec.md`, with `acceptance.md` and `plan.md` consulted only for cross-reference as permitted by the Input Contract.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: REQ-LOGI-001 through REQ-LOGI-014 appear sequentially with no gaps or duplicates (spec.md:L81,83,87,89,93,95,99,103,105,107,109,111,115,117). Zero-padding is consistent (3 digits).

- [FAIL] MP-2 EARS format compliance: `spec.md` contains no "ACCEPTANCE CRITERIA" section at all (see SC-5 below). The de-facto acceptance criteria live in `acceptance.md`, and all 8 scenarios there ("시나리오 1" through "시나리오 8", acceptance.md:L3-79) are written exclusively as Given/When/Then BDD test scenarios — none use any of the five EARS patterns (Ubiquitous/Event-Driven/State-Driven/Optional/Unwanted). Example: acceptance.md:L3-7 "**Given** ... **When** ... **Then** ..." — this is a Given/When/Then test scenario mislabeled/used as acceptance criteria, which M3's rubric explicitly calls out as a 0.25–0.50 band failure pattern. 0 of 8 acceptance entries match an EARS pattern.

- [FAIL] MP-3 YAML frontmatter validity: spec.md:L1-10 frontmatter is missing two required fields. The document has `created: 2026-08-07` (spec.md:L5) but no `created_at` field — the required field name is absent, not merely differently formatted. The `labels` field (required: array or string) is entirely absent from the frontmatter block (spec.md:L1-10). Two required fields missing = FAIL per MP-3 ("Any missing required field = FAIL").

- [N/A] MP-4 Section 22 language neutrality: N/A — SPEC-ORDER-011 is scoped to a single Django/React business application (`backend/order/`, `frontend/src/`), not multi-language LSP/tooling content. No language-specific tool enumeration issue applies.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity/over-specification in a few requirements | Most REQs are precise (e.g., spec.md:L81 lists exact 5 values; L103 defines the aggregation rule precisely). However REQ-LOGI-011 (spec.md:L109) is phrased as a literal code-removal instruction (`order_data.get("financial_status")` at `shopify_orders.py:138`) rather than a behavioral statement, blurring what the actual required behavior is versus the implementation patch — a reasonable engineer reading only "the system shall NOT write to Order.status from financial_status" would be clear, but the appended code fragment invites confusion about whether the citation itself is normative. |
| Completeness | 0.50 | 0.50 — required section missing + frontmatter missing 1-2 fields | spec.md has HISTORY (L14), WHY-equivalent "문제 정의" (L22), WHAT/Scope-equivalent "솔루션 개요"/"범위" (L26, L34), REQUIREMENTS (L77-118), and Exclusions (L121-127) — but has **no ACCEPTANCE CRITERIA section whatsoever**. Combined with frontmatter missing `created_at` and `labels` (spec.md:L1-10), this matches the 0.50 band exactly. |
| Testability | 0.75 | 0.75 — one dimension not precisely binary-testable but measurable | Most REQs define binary-testable outcomes (spec.md:L87 exact filter/target-status; acceptance.md:L51-55 Scenario 5 specifies query-count verification via `CaptureQueriesContext`). However REQ-LOGI-007's invalid-choice 400 response (spec.md:L99) has no corresponding test scenario anywhere in acceptance.md, leaving that testability claim unverified in practice. |
| Traceability | 0.25 | 0.25 — traceability largely absent | Zero acceptance.md scenarios cite a REQ-LOGI-XXX identifier anywhere in the document (acceptance.md:L1-103 scanned in full — no "REQ-LOGI" string present). At least three REQs have no corresponding acceptance scenario at all: REQ-LOGI-006 (WarehouseStock.quantity untouched, spec.md:L95), REQ-LOGI-007's invalid-choice 400 path (spec.md:L99), and REQ-LOGI-014 (PurchaseOrder.status independence, spec.md:L117). |

## Defects Found

D1. spec.md:L1-10 — YAML frontmatter is missing the required `created_at` field (only `created: 2026-08-07` is present, a differently-named field) and is missing the required `labels` field entirely — Severity: critical

D2. spec.md (entire document) — No "ACCEPTANCE CRITERIA" section exists anywhere in spec.md. Acceptance criteria are relegated entirely to a separate `acceptance.md` file, and none of that file's 8 scenarios use EARS pattern language — all are Given/When/Then BDD scenarios — Severity: critical

D3. acceptance.md:L1-103 — No acceptance scenario references a REQ-LOGI-XXX identifier anywhere in the document. Traceability from requirement to acceptance criterion is entirely implicit and left to reader inference — Severity: major

D4. spec.md:L95 (REQ-LOGI-006) — "the system shall NOT modify `WarehouseStock.quantity`" has no corresponding acceptance scenario verifying this non-modification; acceptance.md's 8 scenarios do not test WarehouseStock state at all — Severity: major

D5. spec.md:L117 (REQ-LOGI-014) — "shall NOT derive `logistics_status` from `PurchaseOrder.status`, and shall NOT write to `PurchaseOrder.status`" has no corresponding acceptance scenario verifying `PurchaseOrder.status` remains untouched — Severity: major

D6. spec.md:L99 (REQ-LOGI-007) — "the same invalid-choice 400 response pattern" has no corresponding acceptance scenario testing the invalid-choice rejection path — Severity: minor

D7. spec.md:L87,89,93,99,109,111 — Seven of fourteen REQs (REQ-LOGI-003, 004, 005, 007, 011, 012, and partially 010) embed implementation-level detail rather than behavior/outcome: specific function calls (`transaction.atomic()`, `bulk_update()`, `.save()` at L87/93), specific class names (`UploadDailyReviewView` at L87/89/93, `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView` at L99), a literal code fragment and file:line citation (`order_data.get("financial_status")` at `shopify_orders.py:138`, L109), and a specific migration filename/mechanism (`0026_backfill_bundle_lineitems.py`, RunPython, historical models at L111). This is a WHAT/HOW boundary violation (RQ-3/RQ-4) affecting exactly half of the requirements set — Severity: major

D8. spec.md:L4 — `status: planned` does not match any of the four rubric-enumerated valid status values (draft, active, implemented, deprecated) — Severity: minor

## Chain-of-Verification Pass

Second-look findings: New defects were found on the second pass.

Re-verification performed:
- Re-read all 14 REQ-LOGI entries individually (not just the first few) to confirm MP-1 sequencing end-to-end: confirmed 001→014 with no gaps, matching numbering, and to specifically re-check each for embedded implementation detail (this surfaced D7, which was not fully quantified on the first pass — initial pass noted REQ-LOGI-011 only; second pass found the pattern repeats across 6 additional REQs).
- Re-read all 8 acceptance.md scenarios individually against all 14 REQ-LOGI entries to build an explicit REQ→AC coverage map, rather than sampling a few. This surfaced three uncovered REQs (D4, D5, D6) that a partial sample would have missed, since scenarios 1-5 and 8 do map reasonably well to REQ-LOGI-001/003/004/005/008/009/010/012, creating an initial impression of adequate coverage that only breaks down once REQ-LOGI-002, 006, 007, 011, 013, 014 are checked individually.
- Re-checked the Exclusions section (spec.md:L121-127) for specificity, not just presence: confirmed all 5 entries are specific and include rationale (e.g., "사용자가 명시적으로 유예" for the filter-UI exclusion) — no defect found here, SC-6 is a genuine PASS.
- Re-scanned for contradictions between requirements (not just within a single requirement): none found. Decision C's upload-1/upload-2 filters (spec.md:L55-56, REQ-LOGI-003/005) are mutually consistent, and the Exclusions section does not conflict with any included requirement.
- Re-checked frontmatter field-by-field against the MP-3 required list rather than assuming presence from a glance: this is what surfaced D1's precise nature — `created` is present but is not `created_at`, and `labels` was completely absent, not just malformed.

## Regression Check (Iteration 2+ only)

N/A — this is iteration 1. No prior review report exists.

## Recommendation

1. Add an explicit `## ACCEPTANCE CRITERIA` section to spec.md itself (or, at minimum, rewrite the scenarios in `acceptance.md` using EARS patterns) so that MP-2 can pass. Each acceptance criterion must be phrased as one of: Ubiquitous ("The system shall..."), Event-Driven ("When X, the system shall..."), State-Driven ("While X, the system shall..."), Optional ("Where X, the system shall..."), or Unwanted ("If X, then the system shall..."). Convert all 8 Given/When/Then scenarios in acceptance.md:L3-79 into this format, or add a parallel EARS-formatted AC list inside spec.md that references the scenarios.

2. Fix YAML frontmatter (spec.md:L1-10): rename `created` to `created_at` (or add `created_at` alongside it), and add a `labels` field (array or string) reflecting the SPEC's domain tags (e.g., `[order, logistics, purchase-order]`).

3. Add explicit `REQ-LOGI-XXX` references to every acceptance scenario in acceptance.md so traceability is verifiable rather than inferred (addresses D3).

4. Add acceptance scenarios covering the three currently-uncovered REQs: REQ-LOGI-006 (WarehouseStock.quantity untouched after `received` transition), REQ-LOGI-007 (invalid-choice PATCH returns 400), and REQ-LOGI-014 (PurchaseOrder.status remains untouched by any logistics_status write).

5. Rewrite REQ-LOGI-003, 004, 005, 007, 011, and 012 to state WHAT the system must do (behavior/outcome) without naming specific functions, classes, or file:line locations. Implementation guidance referencing `UploadDailyReviewView`, `transaction.atomic()`, `bulk_update()`, `shopify_orders.py:138`, and `0026_backfill_bundle_lineitems.py` belongs in `plan.md` (where it already correctly appears, e.g., plan.md:L28, L22-24) — not duplicated as normative requirement text in spec.md.

6. Change `status: planned` (spec.md:L4) to one of the four canonical values (draft, active, implemented, deprecated), or confirm with the SPEC owner whether "planned" should be added as a project-wide valid status value in the frontmatter schema documentation.
