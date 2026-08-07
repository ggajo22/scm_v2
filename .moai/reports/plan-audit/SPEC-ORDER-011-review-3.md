# SPEC Review Report: SPEC-ORDER-011
Iteration: 3/3 (FINAL — escalation applies on FAIL)
Verdict: FAIL
Overall Score: 0.72

Reasoning context ignored per M1 Context Isolation. This audit is based solely on `.moai/specs/SPEC-ORDER-011/spec.md`, with `acceptance.md` consulted only for cross-reference as permitted by the Input Contract.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: REQ-LOGI-001 through REQ-LOGI-014 appear sequentially with no gaps or duplicates (spec.md:L88,90,94,96,99,102,106,110,112,114,116,118,122,124). Zero-padding is consistent (3 digits) throughout. Re-verified end-to-end, not spot-checked.

- [FAIL] MP-2 EARS format compliance: The three iteration-2 blocking defects (AC-LOGI-008 "Given"-opener, AC-LOGI-012 "After"-opener, and the "Where"-for-Unwanted misuse in REQ-LOGI-003/007/AC-LOGI-007) are all confirmed RESOLVED — see Regression Check below. However, deeper re-scrutiny surfaces two new, narrower EARS-compliance defects that still violate AC-1 ("Each AC matches one of the five EARS patterns"):
  - **AC-LOGI-007** (spec.md:L146) is labeled "(Ubiquitous)" but its text is two sentences implementing two different EARS patterns: "The system shall accept any of the five valid `logistics_status` values via single-item or batch manual change." (genuinely Ubiquitous) followed by "If an invalid value is submitted, then the system shall reject the request, leave all targeted LineItems' `logistics_status` unchanged, and return an error identifying the invalid value." (genuinely Unwanted — has its own "If...then" trigger). A single AC ID bearing a single pattern label cannot honestly claim to "match one of the five EARS patterns" when roughly half its normative content is a different, unlabeled pattern. A tester deriving one test case from "AC-LOGI-007 (Ubiquitous)" would miss the embedded Unwanted-pattern rejection requirement entirely, or would have to treat it as two criteria under one ID.
  - **AC-LOGI-014** (spec.md:L160) has the identical structural problem: labeled "(Unwanted)", it opens correctly with "If any `logistics_status` write occurs (manual or upload), then the system shall leave every LineItem's associated `PurchaseOrder.status` value(s) unchanged" (genuine Unwanted), then appends ", and `logistics_status` values shall never be computed from `PurchaseOrder.status`" — an unconditional negative statement with no trigger of its own, structurally Ubiquitous, fused onto the Unwanted clause via "and" under the single "(Unwanted)" label.
  - **REQ-LOGI-014** (spec.md:L124) itself is labeled "(Unwanted)" in the REQUIREMENTS ("EARS") section but contains no "If [undesired condition], then..." trigger at all: "The system shall NOT derive `logistics_status` from `PurchaseOrder.status`, and shall NOT write to `PurchaseOrder.status` as a side effect of any requirement in this SPEC." This sentence structurally matches the Ubiquitous pattern ("The system shall [response]", where the response happens to be a negation) — it is mislabeled, not malformed. Contrast with REQ-LOGI-002 (L90), REQ-LOGI-006 (L102), and REQ-LOGI-011 (L116), which are also labeled "(Unwanted)" and correctly use "If...then". REQ-LOGI-014 is the sole outlier among four Unwanted-labeled REQs in the document.

  This is a materially narrower defect than iterations 1 and 2 (13 of 15 ACs are cleanly single-pattern and correctly labeled; only 2 exhibit compound-pattern bundling, and 1 REQ carries a label/structure mismatch), but per M5's explicit instruction that "even one gap... = FAIL" (applied here by direct analogy: even one AC that does not cleanly match its declared single pattern is sufficient), and per the HARD RULE "when in doubt, FAIL," MP-2 does not yet pass.

- [PASS] MP-3 YAML frontmatter validity: spec.md:L1-12 contains all six required fields with correct types — `id: SPEC-ORDER-011` (L2, matches `SPEC-{DOMAIN}-{NUM}`), `version: 1.2.0` (L3, string), `status: draft` (L4, valid enum value), `created_at: 2026-08-07` (L6, ISO date string), `priority: High` (L9, string), `labels: [order, logistics, purchase-order]` (L11, array). No regression from iteration 2.

- [N/A] MP-4 Section 22 language neutrality: N/A — SPEC-ORDER-011 remains scoped to a single Django/React business application (`backend/order/`, `frontend/src/`), not multi-language LSP/tooling content.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements, resolvable consistently | The vast majority of REQ/AC text is unambiguous. REQ-LOGI-014's Unwanted-label-without-trigger (spec.md:L124) and the AC-LOGI-007/014 compound-pattern bundling (spec.md:L146,L160) each create a narrow interpretive gap between "what the label implies" and "what the sentence actually requires" — a careful engineer resolves it correctly by reading the full sentence, but the label itself is misleading. |
| Completeness | 1.0 | 1.0 — all required sections present, frontmatter complete, exclusions present | HISTORY (L16-22), 문제 정의/WHY (L26-28), 솔루션 개요·범위/WHAT (L30-48), 설계 결정 (L50-80), REQUIREMENTS (L84-124), ACCEPTANCE CRITERIA (L128-160), Exclusions with 5 specific entries (L164-170), and "확인이 필요한 가정" (L172-174) are all present. Frontmatter complete per MP-3. No regression. |
| Testability | 0.75 | 0.75 — one or two ACs not precisely binary-testable but measurable with minor interpretation | AC-LOGI-007 (spec.md:L146) and AC-LOGI-014 (spec.md:L160) each bundle two distinct trigger/response pairs under one AC ID — the same class of atomicity defect that AC-LOGI-005 exhibited in iteration 2 (D4) and was subsequently split into 005a/005b. AC-LOGI-013's previous weasel-word issue (D5, iteration 2) is fully resolved — it now has an objective, binary condition ("shares no word in common", "badge background colors differ", spec.md:L158). No weasel words found anywhere in spec.md (verified via full-text scan for "should", "may", "reasonable", "appropriate", "adequate", "proper" — zero matches). |
| Traceability | 1.0 | 1.0 — every REQ has an AC, every AC references a valid REQ, no orphans | Verified all 14 REQ-LOGI-XXX (spec.md:L88-124) map to at least one AC-LOGI-XXX with an explicit "Traces: REQ-LOGI-XXX" annotation (spec.md:L132-160); REQ-LOGI-005 correctly maps to both AC-LOGI-005a and AC-LOGI-005b. Cross-checked all 15 acceptance.md scenarios (0, 1, 1b, 2, 2b, 2c, 2d, 2e, 3, 4, 5, 6, 6b, 7, 8) — each carries an explicit `**Traces**` header citing both REQ-LOGI-XXX and AC-LOGI-XXX, and collectively covers all 14 REQs and all 15 ACs with no orphans in either direction. |

## Defects Found

D1 (new). spec.md:L146 (AC-LOGI-007) — Labeled "(Ubiquitous)" but the AC's second sentence ("If an invalid value is submitted, then the system shall reject the request...") is an independently-triggered Unwanted-pattern statement bundled under the same ID/label. The AC does not cleanly "match one of the five EARS patterns" as a single unit — it matches two, one of which is undisclosed by the label. Same defect class as the already-remediated AC-LOGI-005 (iteration 2, D4/split into 005a/005b) — Severity: major

D2 (new). spec.md:L160 (AC-LOGI-014) — Labeled "(Unwanted)"; the main clause ("If any `logistics_status` write occurs..., then the system shall leave... `PurchaseOrder.status`... unchanged") is correctly Unwanted, but the appended clause ("and `logistics_status` values shall never be computed from `PurchaseOrder.status`") is an unconditional, trigger-less statement structurally matching Ubiquitous, fused onto the Unwanted clause via "and" under a single label — Severity: major

D3 (new). spec.md:L124 (REQ-LOGI-014) — Labeled "(Unwanted)" but contains no "If [condition], then..." trigger; the sentence ("The system shall NOT derive... and shall NOT write...") structurally matches the Ubiquitous pattern instead. This is a label/structure mismatch, inconsistent with the document's other three Unwanted-labeled REQs (REQ-LOGI-002 L90, REQ-LOGI-006 L102, REQ-LOGI-011 L116), all of which correctly use "If...then" — Severity: minor (label/documentation defect; the underlying normative behavior itself is unambiguous and correctly matches Ubiquitous, just under the wrong tag)

No other new defects found. All five defects from the iteration-2 report (D1-D5) are confirmed resolved — see Regression Check.

## Chain-of-Verification Pass

Second-look findings: Yes — D1, D2, D3 above were found only on the second, line-by-line pass. The first pass confirmed the five prior defects (D1-D5 from iteration-2) were fixed and provisionally judged MP-2 as passing, since 12 of 15 ACs are cleanly single-pattern with correct labels and no "Where"/"Given"/"After" mis-triggers remain (confirmed via full-text grep — zero matches for `Where `, `Given `, `After ` and zero matches for weasel words/`should`/`may` anywhere in spec.md).

Re-verification performed on the second pass:
- Re-read all 14 REQ-LOGI entries individually against their declared pattern label (not just checking presence of a trigger word somewhere in the sentence) — this surfaced D3 (REQ-LOGI-014 labeled Unwanted but structurally Ubiquitous), which a first-pass skim (checking only "does the text look formal") would miss since the sentence is grammatically well-formed and confidently states "shall NOT."
- Re-read all 15 AC-LOGI entries and, for each, asked "does every sentence in this AC belong to the SAME EARS pattern as the one declared in the label?" rather than "does the AC contain at least one valid EARS-looking sentence?" — this stricter per-clause check is what surfaced D1 (AC-LOGI-007) and D2 (AC-LOGI-014), both of which read as plausible EARS prose on a shallow pass but contain a second, differently-patterned clause not reflected in the label.
- Explicitly compared AC-LOGI-007/014's structure against the already-fixed AC-LOGI-005 bundling issue (iteration 2, D4) to check whether the same remediation (splitting into sub-IDs) had been consistently applied everywhere it was needed, not just where it was previously flagged — it had not; D1/D2 are instances of the identical defect class the author fixed in one place (AC-LOGI-005) but not two others (AC-LOGI-007, AC-LOGI-014).
- Re-verified REQ number sequencing end-to-end (001→014, all 14 present, 3-digit padding) rather than spot-checking a few entries.
- Re-verified full REQ↔AC traceability by rebuilding the explicit coverage map (14 REQs × 15 ACs × 15 acceptance.md scenarios) rather than relying on the count matching from iteration 2 — confirmed still 1:1/no-orphan, including AC-LOGI-005a/005b both correctly tracing to REQ-LOGI-005.
- Re-checked the Exclusions section (spec.md:L164-170) for specificity: still 5 specific entries with rationale, no regression.
- Re-scanned for weasel words and informal normative language ("should", "may", "reasonable", "appropriate", "adequate", "proper", "good", "Where "/"Given "/"After " as sentence openers) across the entire spec.md via full-text search: zero matches — confirms D3 (Where-misuse) and D5 (AC-LOGI-013 subjective phrasing) from iteration 2 are genuinely and completely resolved, not just superficially reworded.
- Re-scanned REQUIREMENTS for re-introduced implementation detail (function names, class names, file:line citations, migration filenames): none found; still correctly confined to plan.md.

## Regression Check (Iteration 2+ only)

Defects from previous iteration (SPEC-ORDER-011-review-2.md):

- D1 (AC-LOGI-008 "Given"-opener, matches zero EARS patterns) — RESOLVED: spec.md:L148 now reads "The system shall set `Order.status` to the shared `logistics_status` value... when all values are identical, to `partial` when two or more distinct values are present, and to unset when no trackable LineItems exist." — pure Ubiquitous, no precondition opener.
- D2 (AC-LOGI-012 "After"-opener, matches zero EARS patterns) — RESOLVED: spec.md:L156 now reads "The system shall ensure every pre-existing Order with at least one trackable LineItem has a `status` value consistent with REQ-LOGI-008's aggregation rule, following the one-time backfill migration." — pure Ubiquitous, no precondition opener.
- D3 ("Where" misused for Unwanted conditions in REQ-LOGI-003, REQ-LOGI-007, AC-LOGI-007) — RESOLVED: REQ-LOGI-003 (spec.md:L94) now uses "If the uploaded file contains multiple rows for the same SKU, then the system shall apply only the last occurrence per SKU."; REQ-LOGI-007 (spec.md:L106) now uses "If a requested value is not one of the five valid choices, then the system shall reject the request..."; AC-LOGI-007 (spec.md:L146) now uses "If an invalid value is submitted, then the system shall reject the request...". Full-text scan confirms zero remaining `Where ` sentence-openers in spec.md. (Note: AC-LOGI-007's underlying "If...then" clause is now correctly worded, but see new defect D1 above — the AC still bundles this clause with a separate Ubiquitous sentence under one label.)
- D4 (AC-LOGI-005 bundles two Event-Driven trigger/response pairs under one ID) — RESOLVED: spec.md:L140,142 now split into AC-LOGI-005a (not_shipped→received direct transition) and AC-LOGI-005b (shipment_confirmed→received transition), each independently traceable and testable, and acceptance.md scenarios 2/2b (L35-51) each cite the correct sub-ID.
- D5 (AC-LOGI-013 subjective "distinguishable... such that a user can tell them apart" phrasing) — RESOLVED: spec.md:L158 now reads "...the header text for the two columns shares no word in common and the badge background colors differ" — objective, binary-testable condition with no judgment call required.

Stagnation check: No defect from iteration 2 persists unchanged into iteration 3. All 5 prior defects show concrete, verifiable remediation evidence — this is genuine progress. However, exactly as happened between iteration 1 and iteration 2 (fixing D2 introduced new EARS-compliance defects D1-D3), fixing D4 in isolation (splitting AC-LOGI-005) without applying the same fix pattern to structurally identical ACs (AC-LOGI-007, AC-LOGI-014) has left two new, narrower instances of the same underlying defect class. This is not stagnation on a specific defect ID, but it does indicate the author is fixing flagged instances individually rather than searching the document for all instances of a defect class — a pattern worth noting for user attention given this is the final iteration.

## Escalation Report (Final Iteration — FAIL)

Per the Retry Loop Contract, iteration 3 has concluded with a FAIL verdict. User intervention is recommended.

**Full defect history across all 3 iterations:**

| Iteration | Verdict | Score | Defects (count) | Outcome |
|-----------|---------|-------|------------------|---------|
| 1 | FAIL | 0.56 | D1-D8 (8 defects: missing frontmatter fields, no AC section, zero EARS-formatted acceptance scenarios, broken traceability, implementation detail in REQs, invalid `status` value) | All 8 resolved by iteration 2 |
| 2 | FAIL | 0.65 | D1-D5 (5 defects: 2 ACs matching zero EARS patterns, systematic "Where"-for-Unwanted misuse in 3 locations, 1 AC bundling issue, 1 AC subjective phrasing) | All 5 resolved by iteration 3 |
| 3 | FAIL | 0.72 | D1-D3 (3 defects: 2 ACs bundling two different EARS pattern types under one label, 1 REQ mislabeled Unwanted without trigger) | Unresolved — max iterations reached |

**Trend assessment**: Each iteration has resolved 100% of the previously identified defects and the overall score has monotonically improved (0.56 → 0.65 → 0.72). The SPEC is converging, not stagnating — no single defect identifier has survived across iterations. The remaining iteration-3 defects (D1-D3) are narrower in scope (2 ACs out of 15, 1 REQ out of 14) and lower average severity (2 major, 1 minor) than either prior iteration's defect set.

**Recommendation given max_iterations reached**: This SPEC does not require a full re-planning cycle. The remaining defects are mechanical, isolated, and follow a fix pattern already demonstrated correctly elsewhere in the same document (the AC-LOGI-005 split). Recommended path: apply the same three targeted edits below, then request a supplemental one-off verification (outside the normal 3-iteration budget) rather than treating this as a full plan-auditor restart.

1. Split AC-LOGI-007 (spec.md:L146) into AC-LOGI-007a (Ubiquitous: "The system shall accept any of the five valid `logistics_status` values via single-item or batch manual change.") and AC-LOGI-007b (Unwanted: "If an invalid value is submitted, then the system shall reject the request, leave all targeted LineItems' `logistics_status` unchanged, and return an error identifying the invalid value."), mirroring the AC-LOGI-005a/005b precedent already in the document.

2. Split AC-LOGI-014 (spec.md:L160) into AC-LOGI-014a (Unwanted: the existing "If any `logistics_status` write occurs..., then the system shall leave... `PurchaseOrder.status`... unchanged" clause) and AC-LOGI-014b (Ubiquitous: "`logistics_status` values shall never be computed from `PurchaseOrder.status`."), or alternatively fold 014b's content into REQ-LOGI-014/AC-LOGI-001's field-independence statement if it is judged redundant with AC-LOGI-001's existing "never be inferred from or synchronized with" language (spec.md:L132) — in which case remove the redundant clause from AC-LOGI-014 entirely rather than splitting it.

3. Relabel REQ-LOGI-014 (spec.md:L124) from "(Unwanted)" to "(Ubiquitous)" to match its actual unconditional structure — no rewording of the normative sentence itself is needed, only the parenthetical pattern tag.

After these three edits, re-scan spec.md once for "Where "/"Given "/"After " sentence-openers and for any AC/REQ whose label names one pattern but whose text spans two, to confirm no further instances remain before final approval.

## Recommendation

Overall verdict is FAIL due to MP-2 (EARS format compliance). MP-1, MP-3, and MP-4 all pass with cited evidence and require no further changes. The fix scope for MP-2 is now narrow (3 isolated edits, see Escalation Report above) and follows a pattern already successfully applied once in this same document. Given this is the final scheduled iteration (3/3), user intervention/decision is recommended: either (a) authorize a lightweight supplemental fix-and-verify pass covering only the 3 edits above, or (b) accept the SPEC with a documented exception for D1-D3 if the team judges the remaining risk acceptable for Run-phase entry.
