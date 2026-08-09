# SPEC Review Report: SPEC-ORDER-013
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.79 (informational only — Must-Pass Firewall forces overall FAIL regardless of this average)

Reasoning context ignored per M1 Context Isolation. This audit is based solely on `spec.md`, with `acceptance.md` consulted only for cross-reference traceability confirmation.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: Base REQ series runs `spec.md:L124` (REQ-RACK-001) through `spec.md:L230-232` (REQ-RACK-013), sequential 001–013 with no gaps or duplicates and consistent 3-digit zero-padding. Alphabetic suffixes (003a/003b/004a/005a/006a/006b/009a/010a) remain distinct sub-requirement IDs per the documented convention (`spec.md:L117-120`). Unchanged from iteration 1 — still PASS.

- [FAIL] MP-2 EARS format compliance: The bare-negative and mislabeled-pattern defects from iteration 1 (D2, D3, D4, D5, D6) are resolved (see Regression Check), but a **new instance of the same defect class** — a "shall" clause whose grammatical subject is not "the system" — was found in three ACs that iteration 1's audit did not catch:
  - `spec.md:L250-253` AC-RACK-003 (Event-Driven): "...the system shall update and persist that LineItem's `rack_number`, **and the response shall reflect the new value**." — second clause subject is "the response," not "the system."
  - `spec.md:L255-257` AC-RACK-003a (Unwanted): "...the system shall respond HTTP 404 **and no LineItem's `rack_number` shall change**." — second clause subject is "no LineItem's `rack_number`," not "the system."
  - `spec.md:L259-261` AC-RACK-003b (Unwanted): "...the system shall respond HTTP 400 **and the target LineItem's `rack_number` shall remain unchanged** from before the request." — second clause subject is "the target LineItem's `rack_number`," not "the system."
  These three ACs use the identical structural pattern that iteration 1 flagged as a critical MP-2 defect in AC-RACK-010 and AC-RACK-011 (D5/D6). Applying the same rubric consistently, AC-003/003a/003b fail EARS compliance for the same reason. Per MP-2 ("Every acceptance criterion must match one of the five EARS patterns... = FAIL"), this remains a FAIL.

- [PASS] MP-3 YAML frontmatter validity: `spec.md:L1-11` now contains all six required fields with correct types: `id: SPEC-ORDER-013` (string, `spec.md:L2`), `version: 1.0.0` (string, `spec.md:L3`), `status: draft` (string, `spec.md:L4`), `created_at: 2026-08-09` (ISO date string, `spec.md:L5`), `priority: High` (string, `spec.md:L8`), `labels: [order, logistics, rack-number]` (array, `spec.md:L10`). D1 from iteration 1 is resolved. MP-3 now PASSES.

- [N/A] MP-4 Section 22 language neutrality: N/A — single-stack (Django backend + React frontend) feature SPEC; no multi-language LSP/tooling content. Unchanged from iteration 1.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 band — "Minor ambiguity in one or two requirements that a reasonable engineer would resolve consistently" | Mislabeling/bare-negative ambiguity from iteration 1 is resolved. Remaining ambiguity: `spec.md:L250-253` AC-RACK-003, `spec.md:L255-257` AC-RACK-003a, `spec.md:L259-261` AC-RACK-003b shift grammatical subject mid-sentence, and `spec.md:L280-284` AC-RACK-006 / `spec.md:L313-317` AC-RACK-010 still bundle 2-3 distinct trigger/response behaviors under one AC ID — a reasonable engineer would still implement the intended behavior consistently, but the exact assertion count per AC requires interpretation. |
| Completeness | 1.0 | 1.0 band — "All required sections present. All YAML frontmatter fields present. At least one exclusion entry." | All narrative sections present (`spec.md:L15` HISTORY, `spec.md:L23` 문제 정의/WHY, `spec.md:L32,51` 솔루션 개요·범위/WHAT, `spec.md:L115` REQUIREMENTS, `spec.md:L236` ACCEPTANCE CRITERIA, `spec.md:L340` Exclusions with 6 entries). Frontmatter (`spec.md:L1-11`) now has all 6 required fields. D1 resolved. |
| Testability | 0.75 | 0.75 band — "One AC is not precisely binary-testable but is measurable with minor interpretation" | No weasel words ("appropriate", "reasonable", "adequate") found in REQ-RACK-* or AC-RACK-* text (`spec.md:L124-336` reviewed in full, second pass). However `spec.md:L280-284` AC-RACK-006 and `spec.md:L313-317` AC-RACK-010 still require a tester to decide how many sub-assertions each bundles before scoring binary pass/fail — unchanged from iteration 1 (D8 unresolved). |
| Traceability | 1.0 | 1.0 band — "Every REQ-XXX has at least one AC. Every AC references a valid REQ-XXX. No orphaned ACs. No uncovered REQs." | 21 REQ-RACK-* entries (`spec.md:L124-232`) and 21 AC-RACK-* entries (`spec.md:L242-336`) form an exact 1:1 ID-matched set (each AC line opens with "Traces: REQ-RACK-XXX" matching its own ID). Cross-referenced against `acceptance.md:L4-6,10,22,34,45` which cites the same AC-RACK-* IDs consistently. Unchanged from iteration 1 — still PASS. |

## Defects Found

D9. `spec.md:L250-253` (AC-RACK-003), `spec.md:L255-257` (AC-RACK-003a), `spec.md:L259-261` (AC-RACK-003b) — Second clause of each compound "shall" sentence uses a non-"system" grammatical subject ("the response shall reflect...", "no LineItem's `rack_number` shall change", "the target LineItem's `rack_number` shall remain unchanged"), breaking canonical EARS structure identically to the defect class iteration 1 flagged (and fixed) in AC-RACK-010/AC-RACK-011 — Severity: critical (MP-2 must-pass failure; this defect was present in iteration 1's spec.md too but was missed by the previous audit)

D10. `spec.md:L191-193` (REQ-RACK-008) and `spec.md:L299-302` (AC-RACK-008) — Both use the implementation-specific term "lazy-loaded route" / "code-split (lazy-loaded)", a React/bundler technique rather than an observable WHAT/WHY behavior — Severity: minor (RQ-4 implementation-detail leakage; same class of defect as iteration 1's D7, which was fixed for REQ-RACK-001 but a similar term was left unaddressed in REQ-RACK-008/AC-RACK-008)

D8 (carried over, unresolved). `spec.md:L280-284` (AC-RACK-006) and `spec.md:L313-317` (AC-RACK-010) — Each still bundles multiple distinct trigger/response scenarios under a single AC ID, reducing clean binary-testability — Severity: minor

## Chain-of-Verification Pass

Second-look findings: Re-read the full REQUIREMENTS section (`spec.md:L122-232`) and the full ACCEPTANCE CRITERIA section (`spec.md:L238-336`) a second time, checking every "shall" clause's grammatical subject individually rather than only re-checking the six lines flagged in iteration 1's report. This surfaced D9 — a defect class iteration 1 itself established as MP-2-blocking (via D5/D6) but did not apply exhaustively across all 21 ACs; AC-RACK-003/003a/003b exhibit the identical structural problem and were present in iteration 1's version of `spec.md` unchanged, meaning iteration 1's audit was not fully thorough despite its own Chain-of-Verification claim of a complete second pass. Also re-verified REQ number sequencing end-to-end (001–013 base series, no gaps/duplicates — confirmed). Re-verified traceability for all 21 REQ/AC pairs individually (confirmed 1:1, corroborated by `acceptance.md:L4-6,22,34,56`). Re-checked the Exclusions section (`spec.md:L340-351`) — all 6 entries remain specific and REQ-referenced. Re-checked YAML frontmatter types (`spec.md:L1-11`) — all 6 required fields present with correct types, confirmed PASS. Additionally scanned REQUIREMENTS and ACCEPTANCE CRITERIA text for implementation-detail leakage beyond the previously-fixed "CharField" term, which surfaced D10 ("lazy-loaded route" in REQ-RACK-008/AC-RACK-008) — also present unchanged since iteration 1 and not previously flagged.

New defects found in this pass: D9 (critical, MP-2-blocking) and D10 (minor). Both existed in the iteration-1 version of the document but were not caught by the iteration-1 audit.

## Regression Check

Defects from previous iteration:
- D1 (`spec.md:L1-10` frontmatter missing `created_at`/`labels`) — RESOLVED: `spec.md:L5` now has `created_at: 2026-08-09`; `spec.md:L10` now has `labels: [order, logistics, rack-number]`.
- D2 (REQ-RACK-002/012/013 bare "shall NOT" without If...then) — RESOLVED: `spec.md:L128-131`, `spec.md:L226-228`, `spec.md:L230-232` all now use "If [condition], then the system shall NOT..." structure.
- D3 (AC-RACK-002/012/013 same defect) — RESOLVED: `spec.md:L246-248`, `spec.md:L329-331`, `spec.md:L333-336` all now use correct If...then structure.
- D4 (AC-RACK-009a mislabeled Event-Driven phrasing) — RESOLVED: `spec.md:L309-311` now uses "If a user searches... then the system shall display..." matching REQ-RACK-009a's pattern.
- D5 (AC-RACK-010 subject-shift in compound clauses) — RESOLVED: `spec.md:L313-317` now repeats "the system shall" as the explicit subject for all three clauses (render / check-uncheck / reset).
- D6 (AC-RACK-011 subject-shift, "the table shall show...") — RESOLVED: `spec.md:L324-327` now reads "...the system shall issue... and the system shall show the updated value...", both clauses subject "the system."
- D7 (REQ-RACK-001 Django-specific "CharField-equivalent" term) — RESOLVED: `spec.md:L124-126` now reads "a short text code field (max length 10 characters, optional, default empty string)" with no ORM class name.
- D8 (AC-RACK-006 and AC-RACK-010 bundle multiple behaviors under one AC ID) — UNRESOLVED: `spec.md:L280-284` (AC-RACK-006) still combines a positive-set assertion and a negative-scope assertion in one AC; `spec.md:L313-317` (AC-RACK-010) still bundles three distinct behaviors (render checkboxes / toggle select-all / reset-on-navigation) in one AC, despite the grammar fix. This is a minor, non-must-pass defect; not yet at stagnation threshold (2 of 3 possible iterations observed).

Stagnation check: No defect has appeared unchanged across all three iterations yet (only 2 of 3 iterations have occurred). D8 has now appeared unresolved across iterations 1 and 2 — flag as "at risk of stagnation" if unresolved in iteration 3.

## Recommendation

1. Fix the newly-identified EARS subject-shift defect (D9) in `spec.md:L250-253` (AC-RACK-003), `spec.md:L255-257` (AC-RACK-003a), `spec.md:L259-261` (AC-RACK-003b) — the same fix pattern already applied to AC-RACK-010/AC-RACK-011 in this iteration:
   - AC-RACK-003: change "...and the response shall reflect the new value" to "...and the system shall return the new value in the response."
   - AC-RACK-003a: change "...and no LineItem's `rack_number` shall change" to "...and the system shall NOT change any LineItem's `rack_number`."
   - AC-RACK-003b: change "...and the target LineItem's `rack_number` shall remain unchanged from before the request" to "...and the system shall leave the target LineItem's `rack_number` unchanged."
2. Before resubmitting, grep every "shall" occurrence in the REQUIREMENTS and ACCEPTANCE CRITERIA sections and manually confirm each one's grammatical subject is "the system" (or a specifically named page/component acting as the system, per AC-RACK-008/REQ-RACK-008's usage) — do not rely on spot-checking only the lines flagged in the previous report, since this iteration's audit found MP-2 violations at lines the prior audit did not examine closely enough.
3. Optional (D10, minor): reword REQ-RACK-008 (`spec.md:L191-193`) and AC-RACK-008 (`spec.md:L299-302`) to remove the "lazy-loaded" implementation term, e.g., "registered as an independently-loaded route" or omit the loading-strategy detail entirely and describe only the observable routing/navigation behavior.
4. Optional (D8, minor, at risk of stagnation): split AC-RACK-006 (`spec.md:L280-284`) and AC-RACK-010 (`spec.md:L313-317`) into separate AC IDs per distinct testable behavior (e.g., AC-RACK-010, AC-RACK-010b, AC-RACK-010c) to improve binary-testability and avoid this becoming a stagnating defect in iteration 3.

Once item 1 (the MP-2 must-pass blocker) is addressed, re-submit for iteration 3. Traceability (1.0), Completeness (1.0), and YAML frontmatter (MP-3 PASS) are solid and should not need further changes.
