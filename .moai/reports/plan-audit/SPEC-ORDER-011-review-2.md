# SPEC Review Report: SPEC-ORDER-011
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.65

Reasoning context ignored per M1 Context Isolation. This audit is based solely on `.moai/specs/SPEC-ORDER-011/spec.md`, with `acceptance.md` and `plan.md` consulted only for cross-reference as permitted by the Input Contract.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: REQ-LOGI-001 through REQ-LOGI-014 appear sequentially with no gaps or duplicates (spec.md:L87,89,93,95,99,101,105,109,111,113,115,117,121,123). Zero-padding is consistent (3 digits) throughout.

- [FAIL] MP-2 EARS format compliance: Of the 14 items in the `## ACCEPTANCE CRITERIA` section (spec.md:L127-158), at least two fail to match any of the five canonical EARS patterns, and a third pattern-misuse recurs across both REQUIREMENTS and ACCEPTANCE CRITERIA:
  - **AC-LOGI-008** (spec.md:L145) is labeled "(Ubiquitous)" but is written as "**Given** a set of trackable LineItems belonging to one Order, the system shall set `Order.status` to..." — "Given" is a BDD/Gherkin keyword, not a valid EARS trigger. It cannot be Ubiquitous (Ubiquitous requires an unconditional statement with no precondition — this sentence has an explicit precondition), and it does not use "When"/"While"/"Where"/"If...then" either. This AC matches **zero** of the five EARS patterns.
  - **AC-LOGI-012** (spec.md:L153) is labeled "(Ubiquitous)" but is written as "**After** the one-time backfill migration runs, every pre-existing Order... shall have a status value consistent with..." — "After" is not a canonical EARS trigger word (Event-Driven requires "When"), and the sentence again has an explicit precondition that disqualifies it from the unconditional Ubiquitous pattern. Matches zero of the five patterns. Notably, REQ-LOGI-012 (spec.md:L117) itself is correctly phrased as pure Ubiquitous — the corresponding AC introduced a new pattern violation rather than inheriting the REQ's correct phrasing.
  - **"Where" misused for Unwanted conditions**: REQ-LOGI-003 (spec.md:L93, "Where the uploaded file contains multiple rows for the same SKU, the system shall apply only the last occurrence..."), REQ-LOGI-007 (spec.md:L105, "Where a requested value is not one of the five valid choices, the system shall reject the request...") and AC-LOGI-007 (spec.md:L143, "where an invalid value is submitted, the system shall reject the request...") all use the "Where" trigger — which EARS reserves exclusively for the **Optional** pattern ("Where [feature exists], the system shall [response]") describing optional-feature availability — to express what is actually an **Unwanted**-pattern scenario (duplicate/invalid input handling). The textbook-correct phrasing would be "If [duplicate SKU rows exist / an invalid value is submitted], then the system shall...".

  Per MP-2, every acceptance criterion must match one of the five EARS patterns; AC-LOGI-008 and AC-LOGI-012 match none, which alone is sufficient for FAIL. This is an improvement over iteration 1 (where the ACCEPTANCE CRITERIA section did not exist at all and 0/8 scenarios used EARS), but the criterion is not yet satisfied.

- [PASS] MP-3 YAML frontmatter validity: spec.md:L1-12 now contains all six required fields with correct types — `id: SPEC-ORDER-011` (L2, matches `SPEC-{DOMAIN}-{NUM}`), `version: 1.1.0` (L3, string), `status: draft` (L4, valid enum value), `created_at: 2026-08-07` (L6, ISO date string, newly added), `priority: High` (L9, string), `labels: [order, logistics, purchase-order]` (L11, array). Both D1 and D8 from iteration 1 are resolved.

- [N/A] MP-4 Section 22 language neutrality: N/A — SPEC-ORDER-011 remains scoped to a single Django/React business application (`backend/order/`, `frontend/src/`), not multi-language LSP/tooling content.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in a few requirements/ACs, resolvable consistently | The underlying business behavior is unambiguous throughout, but the "Where"-for-error-condition misuse (spec.md:L93,105,143) and the "Given"/"After" trigger substitutions (spec.md:L145,153) create pattern-label confusion — a reader relying on the EARS label to infer conditionality (optional vs. mandatory-error-handling) could be misled, even though the plain-English intent is clear. |
| Completeness | 1.0 | 1.0 — all required sections present, frontmatter complete, exclusions present | HISTORY (L16), 문제 정의/WHY (L25), 솔루션 개요·범위/WHAT (L29,39), REQUIREMENTS (L83-124), ACCEPTANCE CRITERIA (L127-158, newly added), Exclusions with 5 specific entries (L163-167) — all present. Frontmatter complete per MP-3. |
| Testability | 0.75 | 0.75 — one or two ACs not precisely binary-testable but measurable with minor interpretation | AC-LOGI-013 (spec.md:L155) requires the header/badge style to be "distinguishable... such that a user can tell them apart without reading tooltip text" — a soft, judgment-dependent criterion without an objective threshold (e.g., specific label text or a concrete visual rule). AC-LOGI-005 (spec.md:L139) bundles two distinct When-shall statements (direct not_shipped→received and shipment_confirmed→received transitions) under one AC ID, reducing per-criterion testing atomicity. No weasel words ("appropriate"/"adequate"/"reasonable") found elsewhere. |
| Traceability | 1.0 | 1.0 — every REQ has an AC, every AC references a valid REQ, no orphans | Verified all 14 REQ-LOGI-XXX (spec.md:L87-123) have exactly one corresponding AC-LOGI-XXX with matching number and an explicit "Traces: REQ-LOGI-XXX" annotation (spec.md:L131-157). Cross-checked all `acceptance.md` scenarios (0, 1, 1b, 2, 2b, 2c, 2d, 2e, 3, 4, 5, 6, 6b, 7, 8) — each carries an explicit `**Traces**: REQ-LOGI-XXX, AC-LOGI-XXX` header and collectively covers all 14 REQ-LOGI entries, resolving D3/D4/D5/D6 from iteration 1. |

## Defects Found

D1. spec.md:L145 (AC-LOGI-008) — Labeled "(Ubiquitous)" but phrased as "Given a set of trackable LineItems belonging to one Order, the system shall set Order.status to..." — "Given" is a BDD/Gherkin keyword, not an EARS trigger; the sentence has a precondition, disqualifying it from Ubiquitous, and it uses none of the other four valid trigger words. Matches zero EARS patterns — Severity: critical

D2. spec.md:L153 (AC-LOGI-012) — Labeled "(Ubiquitous)" but phrased as "After the one-time backfill migration runs, every pre-existing Order... shall have a status value consistent with..." — "After" is not a valid EARS trigger word (Event-Driven requires "When"); the sentence has a precondition, disqualifying it from Ubiquitous. Matches zero EARS patterns. Contrast with REQ-LOGI-012 (spec.md:L117), which is correctly phrased as pure Ubiquitous — the AC regressed relative to its own REQ — Severity: critical

D3. spec.md:L93 (REQ-LOGI-003), spec.md:L105 (REQ-LOGI-007), spec.md:L143 (AC-LOGI-007) — "Where" is used to introduce duplicate-row and invalid-value handling ("Where the uploaded file contains multiple rows for the same SKU...", "Where a requested value is not one of the five valid choices...", "where an invalid value is submitted..."). EARS reserves "Where" for the Optional pattern (optional feature availability), not for undesired/error conditions, which belong to the Unwanted pattern ("If X, then the system shall..."). This is a systematic trigger-word misapplication recurring in 3 places — Severity: major

D4. spec.md:L139 (AC-LOGI-005) — Combines two separate Event-Driven statements (not_shipped→received direct transition, and shipment_confirmed→received transition) under a single AC ID, reducing per-criterion test atomicity; a tester validating "AC-LOGI-005" must independently verify two distinct trigger/response pairs — Severity: minor

D5. spec.md:L155 (AC-LOGI-013) — "the system shall render them with distinguishable header text and visual style such that a user can tell them apart without reading tooltip text" lacks an objective, binary-testable threshold (e.g., specific label text, contrast ratio, or badge-shape rule), leaving PASS/FAIL determination partly to tester judgment — Severity: minor

## Chain-of-Verification Pass

Second-look findings: New defects were found on the second pass (D1-D5 above were not all apparent on a first skim, since 11 of 14 ACs are correctly EARS-formatted and create a strong first impression of compliance).

Re-verification performed:
- Re-read all 14 REQ-LOGI entries individually end-to-end (not sampled) to confirm MP-1 sequencing: confirmed 001→014, no gaps, consistent 3-digit zero-padding.
- Re-read all 14 AC-LOGI entries individually against their declared EARS-pattern label (not just checking "does it start with When/If/While") — this is what surfaced D1 and D2: both are labeled Ubiquitous but neither is unconditional, and neither uses a canonical trigger word. A first-pass skim that only checks "does each AC exist and look formal" would have missed this, since "Given X, the system shall Y" and "After X, ... shall Y" superficially resemble EARS prose.
- Cross-checked every REQ against its corresponding AC for pattern-label drift (not just checking that both exist) — this surfaced that REQ-LOGI-008 and REQ-LOGI-012 are themselves correctly phrased as pure Ubiquitous, but their ACs independently introduced new conditional trigger words not present in the REQ, meaning the drift was introduced during AC-writing rather than inherited.
- Re-checked all "Where" occurrences project-wide within spec.md (grep-equivalent manual scan of REQUIREMENTS + ACCEPTANCE CRITERIA sections) rather than relying on the single instance flagged implicitly by structure — this surfaced that the misuse recurs in 3 places (REQ-LOGI-003, REQ-LOGI-007, AC-LOGI-007), not just one, which changes this from an isolated typo to a systematic pattern-application error (D3).
- Re-verified full REQ↔AC traceability by building an explicit coverage map (all 14 REQs × all 14 ACs × all 15 acceptance.md scenarios) rather than spot-checking a few — confirmed 1:1 coverage with no orphans, resolving D3/D4/D5/D6 from iteration 1.
- Re-checked the Exclusions section (spec.md:L163-167) for specificity: still 5 specific entries with rationale — no regression, SC-6 remains a genuine PASS.
- Re-scanned for weasel words ("appropriate", "adequate", "reasonable", "good", "proper") across both REQUIREMENTS and ACCEPTANCE CRITERIA sections: none found, except the softer "distinguishable...such that a user can tell them apart" construction in AC-LOGI-013 (D5), which is a judgment-call phrasing rather than a literal weasel word.
- Re-scanned REQUIREMENTS for re-introduced implementation detail (function names, class names, file:line citations, migration filenames) that iteration 1's D7 flagged: confirmed none remain in spec.md's REQUIREMENTS section — all such detail is now correctly confined to plan.md (verified plan.md:L14-18, L23, L28, L39 retain the implementation specifics that were moved out of spec.md).

## Regression Check (Iteration 2+ only)

Defects from previous iteration (SPEC-ORDER-011-review-1.md):

- D1 (frontmatter missing `created_at`/`labels`) — RESOLVED: spec.md:L6 now has `created_at: 2026-08-07`; spec.md:L11 now has `labels: [order, logistics, purchase-order]`.
- D2 (no ACCEPTANCE CRITERIA section; acceptance.md scenarios were pure Given/When/Then with no EARS) — PARTIALLY RESOLVED: a `## ACCEPTANCE CRITERIA` section now exists in spec.md (L127-158) with 14 EARS-labeled entries, 12 of which correctly match their labeled pattern. However, the section still does not achieve full MP-2 compliance — see new defects D1/D2/D3 above, which replace the original "section doesn't exist" failure with a narrower "two ACs use invalid trigger words, three items misuse the Where/Optional pattern" failure. The original defect is resolved; the underlying must-pass criterion (MP-2) is not yet fully satisfied.
- D3 (no acceptance.md scenario cites a REQ-LOGI-XXX ID) — RESOLVED: all 15 acceptance.md scenarios now carry explicit `**Traces**: REQ-LOGI-XXX, AC-LOGI-XXX` headers (acceptance.md:L7,17,27,37,47,57,67,77,91,101,111,121,131,141,151).
- D4 (REQ-LOGI-006 uncovered by any acceptance scenario) — RESOLVED: acceptance.md 시나리오 2d (L65-72) traces REQ-LOGI-006/AC-LOGI-006.
- D5 (REQ-LOGI-014 uncovered) — RESOLVED: acceptance.md 시나리오 6b (L129-136) traces REQ-LOGI-014/AC-LOGI-014.
- D6 (REQ-LOGI-007 invalid-choice path uncovered) — RESOLVED: acceptance.md 시나리오 2e (L75-86) explicitly tests the invalid-value rejection path.
- D7 (implementation detail embedded in 6 REQs: function/class names, file:line citations, migration filenames) — RESOLVED: REQ-LOGI-003/004/005/007/011/012 (spec.md:L93-117) now contain no function names, class names, file:line citations, or migration filenames; all such detail was relocated to plan.md (verified: plan.md:L14-18 migration filenames, L23 file:line, L28/L39 class names).
- D8 (`status: planned` invalid enum value) — RESOLVED: spec.md:L4 now reads `status: draft`, a valid enum value.

Stagnation check: No defect from iteration 1 persists unchanged into iteration 2. All 8 prior defects show concrete remediation evidence. This is genuine progress, not stagnation — however, the remediation of D2 (adding an ACCEPTANCE CRITERIA section) introduced new, previously-nonexistent EARS pattern-compliance defects (D1/D2/D3 in this iteration) that must now be fixed before MP-2 can pass.

## Recommendation

1. Rewrite AC-LOGI-008 (spec.md:L145) to remove the "Given" opener. Since the underlying rule is unconditional ("the system always computes Order.status from its trackable LineItems' logistics_status per this rule"), phrase it as pure Ubiquitous matching REQ-LOGI-008's own correct phrasing: "The system shall set `Order.status` to the shared `logistics_status` value of a trackable LineItem set when all values are identical, to `partial` when two or more distinct values are present, and to unset when no trackable LineItems exist."

2. Rewrite AC-LOGI-012 (spec.md:L153) to remove the "After" opener. Either phrase it as pure Ubiquitous matching REQ-LOGI-012 ("The system shall ensure every pre-existing Order with at least one trackable LineItem has a `status` value consistent with REQ-LOGI-008's aggregation rule, following the one-time backfill migration.") or convert it to a proper Event-Driven statement using "When" if a trigger-based phrasing is preferred.

3. Replace "Where" with "If...then" in REQ-LOGI-003 (spec.md:L93), REQ-LOGI-007 (spec.md:L105), and AC-LOGI-007 (spec.md:L143), since all three describe undesired/error conditions (duplicate SKU rows, invalid value submission) that belong to the Unwanted pattern, not the Optional pattern. Example: "If the uploaded file contains multiple rows for the same SKU, then the system shall apply only the last occurrence per SKU."

4. Split AC-LOGI-005 (spec.md:L139) into two separate AC IDs (e.g., AC-LOGI-005a and AC-LOGI-005b) so each Event-Driven trigger/response pair is independently testable and traceable, or keep as one AC but restructure acceptance.md's 시나리오 2/2b to each cite a distinct sub-ID.

5. Add an objective test condition to AC-LOGI-013 (spec.md:L155) — e.g., "the header text for the two columns shall not share any word in common, and the badge background colors shall differ" — replacing the subjective "such that a user can tell them apart" phrasing.

After these five fixes, MP-2 should be re-evaluated; all other must-pass criteria (MP-1, MP-3, MP-4) currently pass with cited evidence and do not require further changes.
