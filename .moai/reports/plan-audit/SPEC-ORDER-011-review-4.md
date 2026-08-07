# SPEC Review Report: SPEC-ORDER-011
Iteration: Supplemental verification pass (post-3/3, per review-3's own recommendation for a "supplemental one-off verification" outside the normal 3-iteration budget)
Verdict: FAIL
Overall Score: 0.75

Reasoning context ignored per M1 Context Isolation. This audit is based solely on `.moai/specs/SPEC-ORDER-011/spec.md` (185 lines, read in full), with `acceptance.md` and `SPEC-ORDER-011-review-3.md` consulted only for cross-reference as permitted by the Input Contract and the Retry Loop Contract's regression-check requirement.

## Scope of This Pass

The orchestrator applied exactly the 3 edits recommended in review-3's Escalation Report:
1. Split AC-LOGI-007 → AC-LOGI-007a (Ubiquitous) / AC-LOGI-007b (Unwanted)
2. Split AC-LOGI-014 → AC-LOGI-014a (Unwanted) / AC-LOGI-014b (Ubiquitous)
3. Relabel REQ-LOGI-014 from "(Unwanted)" to "(Ubiquitous)"

This audit does not merely check those 3 edits — per M2 (adversarial stance) and the plan-auditor's Input Contract, the full spec.md was independently re-scanned for every REQ and AC against the five EARS patterns, not limited to the previously-flagged locations.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: REQ-LOGI-001 through REQ-LOGI-014 present sequentially, no gaps/duplicates, consistent 3-digit padding (spec.md:L89,91,95,97,101,103,107,111,113,115,117,119,123,125). No regression from review-3.

- [FAIL] MP-2 EARS format compliance: The 3 targeted fixes are all confirmed correctly applied (see Regression Check). However, a full independent re-scan of the REQUIREMENTS section (which is explicitly titled "요구사항 (EARS)" at spec.md:L85 and carries the identical per-item "(Pattern)" labeling convention as the ACCEPTANCE CRITERIA section) surfaces three REQ-level instances of the exact same bundling defect class that was just fixed at the AC level:
  - **REQ-LOGI-003** (spec.md:L95) is labeled "(Event-Driven)" but contains three sentences spanning three distinct EARS patterns: a genuine Event-Driven main clause ("When an admin uploads..., the system shall identify... and shall transition..."), followed by an independently-triggered Unwanted clause ("If the uploaded file contains multiple rows for the same SKU, then the system shall apply only the last occurrence per SKU"), followed by a trigger-less Ubiquitous clause ("The system shall process the entire upload as a single all-or-nothing operation"). None of the latter two share the first clause's "When an admin uploads a file" trigger — they are independently conditioned/unconditioned statements fused under one label.
  - **REQ-LOGI-005** (spec.md:L101) is labeled "(Event-Driven)" but contains a genuine Event-Driven main clause plus a trigger-less Ubiquitous clause ("The system shall apply the same SKU-deduplication and all-or-nothing processing behavior described in REQ-LOGI-003") that does not share the main clause's trigger.
  - **REQ-LOGI-007** (spec.md:L107) is labeled "(Ubiquitous)" but is the direct REQ-level counterpart of the just-fixed AC-LOGI-007: it contains a genuine Ubiquitous main clause ("The system shall allow an admin to set... to any of the five valid values...") followed by an independently-triggered Unwanted clause ("If a requested value is not one of the five valid choices, then the system shall reject the request..."). This is the identical bundling pattern that was split into AC-LOGI-007a/007b one section below it — the fix was applied to the AC but never searched for and applied to the parent REQ that has the same problem.

  This is the same defect class the orchestrator itself was correcting in this very edit round (compound-pattern bundling under a single label), simply present in a section (REQUIREMENTS) that the 3-item fix list from review-3 did not enumerate. Per the HARD RULE "when in doubt, FAIL" and the Must-Pass Firewall's "even one gap... = FAIL" standard already applied by review-3 to this exact defect type, MP-2 remains FAIL.

- [PASS] MP-3 YAML frontmatter validity: spec.md:L1-12 — `id: SPEC-ORDER-011` (L2), `version: 1.3.0` (L3, string, correctly bumped from 1.2.0), `status: draft` (L4), `created_at: 2026-08-07` (L6, ISO date), `priority: High` (L9), `labels: [order, logistics, purchase-order]` (L11, array). All six required fields present with correct types. No regression.

- [N/A] MP-4 Section 22 language neutrality: N/A — SPEC-ORDER-011 remains scoped to a single Django/React business application, not multi-language LSP/tooling content.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | 0.50 — multiple requirements require interpretation; a reasonable engineer might implement them differently than intended | Three REQs (REQ-LOGI-003 L95, REQ-LOGI-005 L101, REQ-LOGI-007 L107) each carry a single pattern label that covers only part of their normative content; a reader deriving behavior from the label alone would miss the independently-triggered clauses. This exceeds the "one or two requirements" ceiling of the 0.75 band. |
| Completeness | 1.0 | 1.0 — all required sections present, frontmatter complete, exclusions present | HISTORY (L16-23, now includes the 1.3.0 entry documenting this edit round), WHY (L27-29), WHAT (L31-49), 설계 결정 (L51-81), REQUIREMENTS (L85-125), ACCEPTANCE CRITERIA (L129-165), Exclusions with 5 entries (L171-175), 확인이 필요한 가정 (L177-179) all present. No regression. |
| Testability | 1.0 | 1.0 — every AC is binary-testable, no weasel words | All 17 AC-LOGI entries (001, 002, 003, 004, 005a, 005b, 006, 007a, 007b, 008, 009, 010, 011, 012, 013, 014a, 014b — spec.md:L133-165) were individually re-checked; each now matches exactly one EARS pattern as a single unit (the 007/014 bundling that previously capped this dimension at 0.75 is resolved). Full-text scan for weasel words ("should", "may", "reasonable", "appropriate", "adequate", "proper") returns zero matches. Improved from 0.75 in review-3. |
| Traceability | 1.0 | 1.0 — every REQ has an AC, every AC references a valid REQ, no orphans | REQ-LOGI-007 now maps to both AC-LOGI-007a and AC-LOGI-007b (spec.md:L147,149); REQ-LOGI-014 now maps to both AC-LOGI-014a and AC-LOGI-014b (spec.md:L163,165), mirroring the pre-existing REQ-LOGI-005 → AC-LOGI-005a/005b pattern. All 14 REQs still covered, no orphaned ACs. No regression. |

## Defects Found

D1 (new, this pass). spec.md:L95 (REQ-LOGI-003) — Labeled "(Event-Driven)" but bundles three EARS pattern types: the Event-Driven main clause, an independently-triggered Unwanted clause ("If the uploaded file contains multiple rows for the same SKU, then..."), and a trigger-less Ubiquitous clause ("The system shall process the entire upload as a single all-or-nothing operation"). Same defect class as the now-fixed AC-LOGI-007 bundling — Severity: major

D2 (new, this pass). spec.md:L101 (REQ-LOGI-005) — Labeled "(Event-Driven)" but bundles the Event-Driven main clause with a trigger-less Ubiquitous clause ("The system shall apply the same SKU-deduplication and all-or-nothing processing behavior described in REQ-LOGI-003") that shares no trigger with the main clause — Severity: major

D3 (new, this pass). spec.md:L107 (REQ-LOGI-007) — Labeled "(Ubiquitous)" but bundles the Ubiquitous main clause with an independently-triggered Unwanted clause ("If a requested value is not one of the five valid choices, then the system shall reject the request..."). This is the direct REQ-level counterpart of the just-resolved AC-LOGI-007 bundling defect (D1 in review-3) — the fix was applied one section below at the AC level but never searched for and applied to the parent REQ exhibiting the identical problem — Severity: major

No other new defects found beyond D1-D3. All 3 defects from review-3 (D1: AC-LOGI-007 bundling, D2: AC-LOGI-014 bundling, D3: REQ-LOGI-014 mislabel) are confirmed resolved — see Regression Check.

## Chain-of-Verification Pass

Second-look findings: Yes — D1, D2, D3 above were found only after re-scanning the entire REQUIREMENTS section clause-by-clause, rather than limiting verification to the 3 locations named in review-3's fix list.

Re-verification performed:
- Did not assume the 3-item fix list from review-3 was exhaustive; independently re-read all 14 REQ-LOGI entries and all 17 AC-LOGI entries against their declared pattern label, asking "does every sentence in this item belong to the same EARS pattern as the label declares?" — this is the same stricter methodology review-3 itself used to find D1/D2, applied here to the REQUIREMENTS section which review-3's second pass did not extend to.
- Ran a full-text grep for `If |When |While |Where |Given |After ` across spec.md to enumerate every trigger-bearing sentence and check each REQ/AC for multiple independent triggers under one label (see Bash output above) — this directly surfaced REQ-LOGI-003 and REQ-LOGI-007 each containing two trigger sentences, and REQ-LOGI-005 containing one trigger sentence plus one un-triggered "shall" sentence, all under single labels.
- Verified REQ-LOGI-001, 002, 004, 006, 008, 009, 010, 011, 012, 013 do NOT exhibit this bundling: each has either a single trigger type or multiple "shall" clauses sharing the same trigger/no-trigger status (i.e., genuinely single-pattern compound statements, not multi-pattern bundling) — confirmed by individually re-reading each, not just counting sentences.
- Re-verified all 3 review-3 fixes are structurally correct (not just present): AC-LOGI-007a/007b, AC-LOGI-014a/014b each independently match exactly one EARS pattern; REQ-LOGI-014's new "(Ubiquitous)" label matches its trigger-less "shall NOT... and shall NOT..." structure.
- Re-verified REQ number sequencing end-to-end (001→014) and full REQ↔AC traceability (17 ACs × 14 REQs, including the two newly-split REQ→2×AC mappings) — no orphans, no regressions.
- Re-scanned for weasel words and re-confirmed zero matches.
- Re-checked the Exclusions section (spec.md:L171-175) — still 5 specific entries, no regression.

## Regression Check

Defects from previous iteration (SPEC-ORDER-011-review-3.md):

- D1 (AC-LOGI-007 bundles Ubiquitous + Unwanted under one label) — RESOLVED: spec.md:L147 now reads "**AC-LOGI-007a** (Ubiquitous) ... The system shall accept any of the five valid `logistics_status` values via single-item or batch manual change." and spec.md:L149 reads "**AC-LOGI-007b** (Unwanted) ... If an invalid value is submitted for a manual `logistics_status` change, then the system shall reject the request, leave all targeted LineItems' `logistics_status` unchanged, and return an error identifying the invalid value." Each is now independently single-pattern and correctly labeled.
- D2 (AC-LOGI-014 bundles Unwanted + Ubiquitous under one label) — RESOLVED: spec.md:L163 now reads "**AC-LOGI-014a** (Unwanted) ... If any `logistics_status` write occurs (manual or upload), then the system shall leave every LineItem's associated `PurchaseOrder.status` value(s) unchanged." and spec.md:L165 reads "**AC-LOGI-014b** (Ubiquitous) ... The system shall never compute a `logistics_status` value from `PurchaseOrder.status`." Each is now independently single-pattern and correctly labeled.
- D3 (REQ-LOGI-014 labeled Unwanted but structurally Ubiquitous) — RESOLVED: spec.md:L125 now reads "**REQ-LOGI-014** (Ubiquitous): The system shall NOT derive `logistics_status` from `PurchaseOrder.status`, and shall NOT write to `PurchaseOrder.status` as a side effect of any requirement in this SPEC (결정 A)." — label now matches the trigger-less structure.

Stagnation check: None of review-3's D1-D3 persist unchanged; all three show concrete, verifiable remediation. However, the newly-found D1-D3 in this pass (REQ-LOGI-003/005/007) are the same underlying defect class that review-3 itself was still resolving, and this is the second consecutive round in which fixing flagged instances of a defect class left other instances of the identical class unaddressed elsewhere in the document (iteration 2→3: AC-LOGI-005 split fixed but AC-LOGI-007/014 not found; iteration 3→this pass: AC-LOGI-007/014 split fixed but the parallel REQ-LOGI-003/005/007 bundling not found). This is a genuine pattern-recognition gap, not random regression — recommend the fix author run an explicit clause-by-clause single-trigger check across the ENTIRE spec.md (both REQUIREMENTS and ACCEPTANCE CRITERIA sections) in the next edit, rather than fixing only the specific line numbers cited in an audit report.

## Recommendation

Overall verdict is FAIL due to MP-2 (EARS format compliance). MP-1, MP-3, and MP-4 pass with cited evidence. The 3 fixes from review-3 were correctly and precisely applied — no defect remains at AC-LOGI-007, AC-LOGI-014, or REQ-LOGI-014. The failure is due to newly-surfaced instances of the identical bundling defect class in REQ-LOGI-003, REQ-LOGI-005, and REQ-LOGI-007, which were present in the document throughout iterations 1-3 but were not caught because prior audits' EARS-pattern scrutiny concentrated on the ACCEPTANCE CRITERIA section and only extended to REQUIREMENTS for the single already-flagged REQ-LOGI-014.

Actionable fix instructions:

1. Split REQ-LOGI-003 (spec.md:L95) into three single-pattern items (or fold the two trailing "shall" statements into REQ-LOGI-004, which already covers upload-response/error-reporting behavior, if judged redundant): REQ-LOGI-003 (Event-Driven, the SKU-matching + transition clause only), plus a new REQ (Unwanted) for "If the uploaded file contains multiple rows for the same SKU, then apply only the last occurrence," plus a new REQ (Ubiquitous) for "all-or-nothing processing" — or relabel as multiple REQ-LOGI-003a/b/c following the existing 005a/005b, 007a/007b, 014a/014b precedent.

2. Split REQ-LOGI-005 (spec.md:L101) similarly: keep the Event-Driven main clause under REQ-LOGI-005, and either fold "The system shall apply the same SKU-deduplication and all-or-nothing processing behavior described in REQ-LOGI-003" into REQ-LOGI-003's all-or-nothing REQ (cross-referenced, avoiding duplication) or split into REQ-LOGI-005a/005b.

3. Split REQ-LOGI-007 (spec.md:L107) into REQ-LOGI-007a (Ubiquitous: valid-value acceptance) and REQ-LOGI-007b (Unwanted: invalid-value rejection), mirroring the AC-LOGI-007a/007b split already present one section below — note this will require renumbering trailing REQs or adopting the same a/b suffix convention used elsewhere in this document.

4. After these edits, re-run the same trigger-keyword grep (`If |When |While |Where |Given |After `) across the ENTIRE spec.md — both REQUIREMENTS and ACCEPTANCE CRITERIA sections — and manually confirm every item's declared label matches 100% of its normative sentences before requesting the next audit pass. This full-document sweep, not a spot-fix of previously-cited line numbers, is what is needed to reach a genuine MP-2 PASS.

Given this SPEC has now completed its 3-iteration budget plus one supplemental pass, and the remaining defects are narrow (3 REQs, same class as prior fully-resolved defects, mechanical to fix), user intervention is recommended to decide between: (a) authorize one more supplemental fix-and-verify pass applying the full-document sweep in instruction 4, or (b) accept the SPEC with a documented exception for D1-D3 (REQ-LOGI-003/005/007) if the team judges this labeling/structure risk acceptable for Run-phase entry, given that the underlying acceptance-criteria (the actually-tested units) are all fully EARS-compliant and traceable.
