# SPEC Review Report: SPEC-ORDER-013
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.69 (informational only — Must-Pass Firewall forces overall FAIL regardless of this average)

Reasoning context ignored per M1 Context Isolation. This audit is based solely on `spec.md`, with `acceptance.md` consulted only for cross-reference traceability confirmation.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: Base REQ series is `spec.md:L123` (REQ-RACK-001) through `spec.md:L227` (REQ-RACK-013), fully sequential 001–013 with no gaps or duplicates and consistent 3-digit zero-padding. Alphabetic suffixes (003a/003b/004a/005a/006a/006b/009a/010a) are distinct sub-requirement IDs, not duplicates, and the document explicitly documents this as an established project convention (`spec.md:L116-119`).

- [FAIL] MP-2 EARS format compliance: Multiple entries labeled "(Unwanted)" do not follow the required "If [condition], then the [system] shall [response]" structure. Evidence:
  - `spec.md:L127-129` REQ-RACK-002: "The system shall NOT compute, derive, or expose any Order-level aggregate..." — bare negative statement, no "If...then" trigger.
  - `spec.md:L224-225` REQ-RACK-012: "The system shall NOT render or allow editing of `rack_number`..." — same defect.
  - `spec.md:L227-228` REQ-RACK-013: "The system shall NOT introduce any rack-location capacity validation..." — same defect.
  - `spec.md:L242-244` AC-RACK-002 mirrors REQ-RACK-002's non-conforming structure.
  - `spec.md:L324-326` AC-RACK-012: "The system shall render `OrderDetailPage` with no `rack_number` field..." — positively-phrased Ubiquitous sentence mislabeled "(Unwanted)"; no "If...then" structure.
  - `spec.md:L328-330` AC-RACK-013 mirrors REQ-RACK-013's non-conforming structure.
  - `spec.md:L305-307` AC-RACK-009a: labeled "(Unwanted)" but written as "When a user searches by an order number that matches no existing Order, the system shall display..." — this is Event-Driven ("When...shall") phrasing, not the Unwanted "If...then" pattern used correctly by its own source requirement REQ-RACK-009a (`spec.md:L199-201`, which correctly uses "If...then"). The AC diverged from its REQ's correct EARS pattern.
  - `spec.md:L309-312` AC-RACK-010: compound sentence where the second and third clauses drop "the system" as subject — "toggling 'select all' **shall** check or uncheck..." and "navigating away from the page and returning... **shall** reset..." — subject of "shall" is a gerund phrase, not "the system", breaking the canonical template.
  - `spec.md:L319-322` AC-RACK-011: similar subject-shift — "...the system shall issue a single-item PATCH request... and **the table shall** show the updated value..." — second clause's subject is "the table", not "the system".
  Six of 21 ACs (AC-002, AC-009a, AC-010, AC-011, AC-012, AC-013 ≈ 29%) and three of 21 REQs deviate from the five canonical EARS templates. Per the M3 rubric and MP-2 hard rule, this is a FAIL.

- [FAIL] MP-3 YAML frontmatter validity: `spec.md:L1-10` frontmatter contains `id`, `version`, `status`, `created`, `updated`, `author`, `priority`, `issue_number` — but:
  - Required field `created_at` is absent; the document uses `created` (`spec.md:L5`) instead, which is a different field name, not merely a formatting variant.
  - Required field `labels` is entirely absent — no `labels`, `tags`, or equivalent array/string field exists anywhere in the frontmatter block (`spec.md:L1-10`).
  Two of six required fields are missing under their required names. This is a FAIL per MP-3 ("Any missing required field = FAIL").

- [N/A] MP-4 Section 22 language neutrality: N/A — this SPEC is scoped to a single-stack (Django backend + React frontend) feature (rack-number tracking on `LineItem`); it does not cover multi-language LSP/tooling content. No language-specific tool names are hardcoded in a template-bound, multi-language context.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | 0.50 band — "Multiple requirements require interpretation; a reasonable engineer might implement them differently" | `spec.md:L275-280` AC-RACK-006 bundles two distinct trigger/response scenarios ("When X... the system shall set...; when Y... the system shall update only...") under a single AC ID, leaving ambiguous whether the second clause is an independently-testable requirement or illustrative commentary. `spec.md:L309-312` AC-RACK-010 similarly bundles three distinct behaviors (render checkboxes / toggle select-all / reset-on-navigation) under one ID with shifting grammatical subjects, so a reviewer must guess how many discrete test cases the single AC represents. |
| Completeness | 0.50 | 0.50 band — "frontmatter missing one or two fields" | All narrative sections (HISTORY, 문제 정의/WHY, 솔루션 개요·범위/WHAT, 요구사항/REQUIREMENTS, ACCEPTANCE CRITERIA, Exclusions) are present (`spec.md:L14,22,31,50,114,232,334`), but frontmatter (`spec.md:L1-10`) is missing `created_at` (present only as `created`) and `labels` entirely — 2 of 6 required fields missing. |
| Testability | 0.75 | 0.75 band — "One AC is not precisely binary-testable but is measurable with minor interpretation" | No weasel words ("appropriate", "reasonable", "adequate") found anywhere in REQ-RACK-* or AC-RACK-* text (`spec.md:L121-330` reviewed in full). However `spec.md:L275-280` AC-RACK-006 and `spec.md:L309-312` AC-RACK-010 require a tester to decide how many sub-assertions each compound AC entails before it can be scored binary pass/fail. |
| Traceability | 1.0 | 1.0 band — "Every REQ-XXX has at least one AC. Every AC references a valid REQ-XXX. No orphaned ACs. No uncovered REQs." | 21 REQ-RACK-* entries (`spec.md:L123-228`) and 21 AC-RACK-* entries (`spec.md:L238-330`) form an exact 1:1 ID-matched set (e.g., `spec.md:L238` "AC-RACK-001 ... Traces: REQ-RACK-001" through `spec.md:L328` "AC-RACK-013 ... Traces: REQ-RACK-013"); every REQ ID has a corresponding "Traces:" AC and no AC references a non-existent REQ. Cross-referenced against `acceptance.md:L4-6,10,22,34,45,56` which cites the same AC-RACK-* IDs consistently. |

## Defects Found

D1. `spec.md:L1-10` — YAML frontmatter uses `created` instead of the required `created_at` field name, and omits the required `labels` field entirely — Severity: critical (MP-3 must-pass failure)

D2. `spec.md:L127-129` (REQ-RACK-002), `spec.md:L224-225` (REQ-RACK-012), `spec.md:L227-228` (REQ-RACK-013) — Requirements labeled "(Unwanted)" use bare "The system shall NOT..." phrasing without the required "If [condition], then the [system] shall [response]" structure — Severity: critical (MP-2 must-pass failure)

D3. `spec.md:L242-244` (AC-RACK-002), `spec.md:L324-326` (AC-RACK-012), `spec.md:L328-330` (AC-RACK-013) — Same EARS-Unwanted structural defect propagated into the corresponding Acceptance Criteria — Severity: critical (MP-2 must-pass failure)

D4. `spec.md:L305-307` — AC-RACK-009a is labeled "(Unwanted)" but is phrased as an Event-Driven "When X, the system shall Y" sentence, diverging from its own source requirement REQ-RACK-009a (`spec.md:L199-201`), which correctly uses "If...then" — internal inconsistency between REQ and AC EARS pattern usage for the same requirement — Severity: major

D5. `spec.md:L309-312` — AC-RACK-010 is a compound sentence whose second and third clauses use "toggling 'select all' shall..." and "navigating away... shall..." — the grammatical subject of "shall" is not "the system" in either clause, breaking canonical EARS structure — Severity: major

D6. `spec.md:L319-322` — AC-RACK-011's second clause ("the table shall show the updated value...") shifts subject from "the system" to "the table," breaking canonical EARS structure — Severity: minor

D7. `spec.md:L123-125` — REQ-RACK-001 embeds a Django-specific implementation term ("CharField-equivalent") inside a requirement statement rather than describing pure observable behavior — Severity: minor (RQ-4 implementation-detail leakage)

D8. `spec.md:L275-280` and `spec.md:L309-312` — AC-RACK-006 and AC-RACK-010 each bundle multiple distinct trigger/response scenarios under a single AC ID, reducing clean binary-testability and making it unclear how many discrete assertions the AC represents — Severity: minor

## Chain-of-Verification Pass

Second-look findings: Re-read the full REQUIREMENTS section (`spec.md:L114-228`) line-by-line a second time (all 21 REQ entries, not just the first few) and the full ACCEPTANCE CRITERIA section (`spec.md:L232-330`, all 21 AC entries) a second time, explicitly checking EARS pattern-label-vs-sentence-structure agreement for every entry rather than sampling. This second pass is what surfaced D4 (AC-RACK-009a pattern mismatch with its own REQ) and D5/D6 (subject-shift within compound "shall" clauses in AC-RACK-010 and AC-RACK-011), which were not caught in an initial skim that only checked for the presence of the word "shall." Also re-verified REQ number sequencing end-to-end by listing every REQ-RACK-* ID in document order (not spot-checking) — confirmed 001–013 base series complete with no gaps/duplicates. Re-verified traceability for all 21 REQ/AC pairs individually (not a sample) — confirmed complete 1:1 mapping, corroborated by `acceptance.md:L4-6`. Re-checked the Exclusions section (`spec.md:L334-345`) for specificity — all 6 entries are specific and REQ-referenced, no vague entries found. Re-checked for contradictions between Decision E (`spec.md:L96-104`, apply to all matching LineItems) and REQ-RACK-006 (`spec.md:L168-171`) — consistent, no contradiction found.

No additional new defects beyond D1–D8 were found in the second pass.

## Recommendation

1. Fix YAML frontmatter (`spec.md:L1-10`): rename `created` to `created_at`, and add a `labels` field (array or string) reflecting the SPEC's domain/scope (e.g., `labels: [order, logistics, rack-number]`).
2. Rewrite REQ-RACK-002, REQ-RACK-012, REQ-RACK-013 (`spec.md:L127-129, L224-225, L227-228`) using proper Unwanted EARS structure: "If [undesired condition/attempt], then the system shall NOT [action]." For example, REQ-RACK-002 could become: "If any process attempts to compute, derive, or expose an Order-level aggregate for `rack_number`, then the system shall reject or omit that computation." Propagate the same fix to AC-RACK-002, AC-RACK-012, AC-RACK-013 (`spec.md:L242-244, L324-326, L328-330`).
3. Fix AC-RACK-009a (`spec.md:L305-307`) to use the same "If [condition], then the system shall [response]" structure as its source REQ-RACK-009a (`spec.md:L199-201`), rather than "When...shall" phrasing.
4. Rewrite AC-RACK-010 (`spec.md:L309-312`) and AC-RACK-011 (`spec.md:L319-322`) so every "shall" clause has "the system" as its explicit subject; split compound behaviors into separate AC IDs (e.g., AC-RACK-010, AC-RACK-010b) if more than one discrete testable behavior is being specified.
5. Consider splitting AC-RACK-006 (`spec.md:L275-280`) into two ACs (one per distinct trigger scenario) to improve binary-testability and Clarity scoring.
6. Optional: reword REQ-RACK-001 (`spec.md:L123-125`) to remove the Django-specific "CharField-equivalent" term, describing the field purely by observable constraints (short text code, max 10 characters, optional, defaults empty) without naming an ORM class.

Once these are addressed, re-submit for iteration 2. Note that traceability (1.0) and document structure (all sections present) are already solid and should not need further changes.
