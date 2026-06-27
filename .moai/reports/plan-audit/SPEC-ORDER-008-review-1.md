# SPEC Review Report: SPEC-ORDER-008
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.38

---

## Must-Pass Results

- [FAIL] MP-1 REQ number consistency: REQ numbers follow a domain-partitioned scheme (`REQ-008-B-01` ... `REQ-008-B-06`, `REQ-008-F-01` ... `REQ-008-F-08`) rather than the required flat sequential format `REQ-001, REQ-002, ... REQ-N`. The required format mandates no domain-suffix infix. The actual scheme embeds SPEC ID and domain character between hyphens, producing identifiers that cannot satisfy "sequential REQ-001 through REQ-N with consistent zero-padding." Even within each partition the sequencing is internally consistent, but the overall numbering scheme is structurally non-conformant.

- [FAIL] MP-2 EARS format compliance: Every acceptance criterion in acceptance.md uses Given/When/Then (GWT) test scenario format, not EARS. Per M3 rubric: "Given/When/Then test scenarios mislabeled as EARS = FAIL." Zero ACs conform to any of the five EARS patterns. Examples: acceptance.md:L5 ("Given ... confirmed_price = 15000 ..."), acceptance.md:L19 ("Given line_item A: confirmed_price = null ..."), acceptance.md:L44 ("Given 사용자가 ... 접속했을 때"). None use the "When [trigger], the [system] shall [response]" or other EARS structures. The spec.md itself contains no Acceptance Criteria section at all — ACs live only in a separate acceptance.md file.

- [FAIL] MP-3 YAML frontmatter validity: Two required fields are defective.
  (a) `created_at` is absent. The frontmatter uses `created: 2026-06-24` (spec.md:L5) — the field name is wrong. The required field name is `created_at`.
  (b) `labels` field is entirely absent from the frontmatter (spec.md:L1-10). Fields present: id, version, status, created, updated, author, priority, issue_number. `labels` is missing.

- [N/A] MP-4 Section 22 language neutrality: N/A — this SPEC is scoped to a single application (Python/Django backend + TypeScript/React frontend). It does not cover multi-language tooling. Auto-passes.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements | Most requirements are clear and precise. spec.md:L46 (REQ-008-B-01) conflates behavior with implementation (class name + line numbers). spec.md:L58 formula is unambiguous. Main clarity degradation: implementation details embedded in normative requirement text make behavioral intent harder to isolate. |
| Completeness | 0.50 | 0.50 — multiple sections missing | HISTORY present (spec.md:L12), WHY ("문제 정의" spec.md:L20), WHAT ("목표" spec.md:L26), REQUIREMENTS present (spec.md:L42), Exclusions present (spec.md:L127). MISSING: Acceptance Criteria section within spec.md — ACs are in a separate acceptance.md file, not integrated. YAML frontmatter is missing `labels` and has wrong field name `created` instead of `created_at`. |
| Testability | 0.50 | 0.50 — several ACs contain weasel words or require judgment calls | acceptance.md:L12 "또는 동등한 숫자 문자열" (or equivalent numeric string), acceptance.md:L52 "또는 동등한 포맷" (or equivalent format), acceptance.md:L76 "또는 동등한 포맷". These require tester judgment. acceptance.md:L88-89 (CSS class check) is fully binary-testable. acceptance.md:L37-39 (margin_amount = null, margin_rate = null) is binary-testable. Approximately half have weasel qualifiers. |
| Traceability | 0.25 | 0.25 — traceability largely absent | acceptance.md contains 7 scenarios (Scenarios 1-7). spec.md contains 14 REQs (REQ-008-B-01 through REQ-008-F-08). No AC references any REQ-XXX identifier. No REQ references any AC. There are no forward or backward traceability links anywhere in either document. REQs with no mapped AC: REQ-008-B-02, REQ-008-B-03, REQ-008-F-01, REQ-008-F-02 are not individually addressed by any labeled scenario. |

---

## Defects Found

D1. spec.md:L5 — YAML field `created` must be named `created_at` per required frontmatter schema. Current: `created: 2026-06-24`. Required: `created_at: "2026-06-24"`. — Severity: critical (MP-3 failure)

D2. spec.md:L1-10 — `labels` field entirely absent from YAML frontmatter. Required field with array or string type. — Severity: critical (MP-3 failure)

D3. spec.md:L46, L50, L52, L58, L66, L74, L81, L88, L99, L101, L103, L109, L111, L113 — REQ numbering scheme `REQ-008-B-NN` / `REQ-008-F-NN` does not conform to required flat sequential format `REQ-001, REQ-002, ... REQ-N`. The domain-infix characters (B, F) and the SPEC-ID prefix embedded in the REQ identifier violate MP-1. — Severity: critical (MP-1 failure)

D4. acceptance.md (all scenarios) — All 7 acceptance criteria scenarios use Given/When/Then format, not EARS patterns. This violates MP-2. The five valid EARS patterns are: Ubiquitous, Event-driven, State-driven, Optional, Unwanted. None of the 7 scenarios in acceptance.md use any of these patterns. — Severity: critical (MP-2 failure)

D5. spec.md — No Acceptance Criteria section exists within spec.md. The document structure is incomplete: REQUIREMENTS section is present but the mandatory paired ACCEPTANCE CRITERIA section is absent. ACs are placed in a separate file (acceptance.md) rather than inside spec.md. — Severity: major (SC-5 failure)

D6. spec.md:L46 — REQ-008-B-01 contains implementation details: `LineItemDetailSerializer` (class name), `backend/order/serializers.py lines 64–71` (exact file path and line numbers). Requirements must specify WHAT the system shall do, not HOW or WHERE in the code. — Severity: major (RQ-3, RQ-4 violation)

D7. spec.md:L81-86 — REQ-008-F-01 specifies exact TypeScript interface name (`LineItemDetail`) and exact file path (`frontend/src/types/order.ts`). This is implementation-level detail embedded in a behavioral requirement. — Severity: major (RQ-4 violation)

D8. spec.md:L113 — REQ-008-F-08 specifies exact CSS class names (`max-w-7xl`, `max-w-4xl`) and references a specific HTML element type (`div`) and exact component name (`OrderDetailPage`). Behavioral requirements should describe observable behavior (e.g., "the page container shall expand to accommodate wider tables"), not prescribe CSS class implementation. — Severity: minor (RQ-4 violation — lower severity as CSS class is an observable attribute, but class name is still an implementation detail)

D9. acceptance.md:L12, L52, L76 — Weasel phrase "또는 동등한 포맷" (or equivalent format) / "또는 동등한 숫자 문자열" (or equivalent numeric string) renders these ACs not binary-testable. A tester must exercise judgment to determine what qualifies as "equivalent." — Severity: major (AC-2, AC-3 violation)

D10. acceptance.md (all scenarios) — No AC references any REQ-XXX identifier. spec.md REQs do not reference any acceptance scenario. Forward and backward traceability are both completely absent. REQ-008-B-02 (null confirmed_price returns null), REQ-008-B-03 (null confirmed_distributor returns null), REQ-008-F-01 (TypeScript LineItemDetail interface), REQ-008-F-02 (TypeScript OrderDetail interface) have no corresponding AC scenario. — Severity: major (AC-4, AC-5 violation)

---

## Chain-of-Verification Pass

Second-look findings: Confirmed all four must-pass failures on re-read. Additional verification:

- Re-read spec.md:L1-10 line by line: `id`, `version`, `status`, `created`, `updated`, `author`, `priority`, `issue_number`. `created_at` and `labels` definitively absent.
- Re-read all 14 REQ identifiers: B-01 through B-06, F-01 through F-08. Non-conformant numbering confirmed on every entry.
- Re-read all 7 acceptance.md scenarios: Given/When/Then format confirmed on every scenario. Not one uses a "shall" EARS pattern.
- Re-read traceability: Confirmed zero cross-references between spec.md REQs and acceptance.md scenarios in either direction.
- Consistency check (CN-1): REQ-008-B-06 (partial sum when some confirmed_price are null) and REQ-008-B-04 (return null when ALL are null) are consistent with each other and with acceptance.md Scenario 2 (partial sum case) and Scenario 3 (all null case). No contradiction found.
- Checked REQ-008-B-05 (margin_rate formula) against acceptance.md Scenario 1 (Then block). The formula is: `margin_rate = (margin_amount / total_price) * 100`. Scenario 1 confirms: `margin_rate = (margin_amount / total_price) * 100` rounded to 2 decimal places. Consistent. No defect.

No new defects found beyond those already listed in first pass. The first pass was thorough. Sections re-verified: YAML frontmatter, all REQ identifiers, all AC scenarios, traceability linkage, exclusions, consistency between REQ-008-B-04/B-05/B-06.

---

## Recommendation

The SPEC has 3 critical must-pass failures (MP-1, MP-2, MP-3) and 1 major structural failure (SC-5). manager-spec must address all of the following before re-audit:

1. **Fix YAML frontmatter (MP-3):** Rename `created` to `created_at` at spec.md:L5. Add a `labels` field (e.g., `labels: ["order", "frontend", "backend", "enhancement"]`). The field is required and must be present.

2. **Renumber all REQs to flat sequential format (MP-1):** Replace the domain-partitioned scheme with `REQ-001` through `REQ-014`. Map the current 14 requirements to REQ-001...REQ-014 in document order. For example: REQ-008-B-01 → REQ-001, REQ-008-B-02 → REQ-002, ..., REQ-008-F-08 → REQ-014. Update all internal cross-references.

3. **Rewrite acceptance criteria to EARS format (MP-2):** All 7 scenarios in acceptance.md (and any ACs that should be in spec.md) must be rewritten using one of the five EARS patterns. For example, Scenario 1's backend assertions should become:
   - "When `GET /api/orders/{id}/` is called for an order with a confirmed line item, the system shall return `confirmed_price` as a non-null numeric string in the line item."
   - "When `GET /api/orders/{id}/` is called, the system shall return `margin_amount` calculated as `total_price - sum(confirmed_price * quantity)` for all line items with non-null `confirmed_price`."

4. **Add Acceptance Criteria section to spec.md (SC-5):** The EARS-format ACs must appear inside spec.md under a `## Acceptance Criteria` section, not only in a separate file. Each AC must reference a REQ-XXX identifier.

5. **Add REQ-XXX references to all ACs (AC-4, AC-5):** Every AC must cite the REQ it covers. Every REQ must have at least one AC citing it. REQs currently without any AC coverage: REQ-008-B-02, REQ-008-B-03, REQ-008-F-01, REQ-008-F-02.

6. **Remove implementation details from requirements (RQ-4):** REQ-001 (formerly B-01) should not cite `backend/order/serializers.py lines 64-71` or class name `LineItemDetailSerializer`. Express the requirement as observable system behavior: "The system shall include confirmed_price, confirmed_distributor, and confirmed_at in the order line item API response." Similarly for REQ-007 (F-01) and REQ-014 (F-08).

7. **Eliminate weasel phrases from ACs (AC-2, AC-3):** Remove "또는 동등한 포맷" and "또는 동등한 숫자 문자열" from all ACs. Specify the exact format expected (e.g., "formatted as a comma-separated integer without decimal places") or remove the qualifier entirely and accept the precise value.
