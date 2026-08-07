# SPEC Review Report: SPEC-PURCHASE-ORDER-010
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.63 (informational only — Must-Pass Firewall forces overall FAIL regardless of this average)

Reasoning context ignored per M1 Context Isolation. This audit is based solely on `spec.md` at `.moai/specs/SPEC-PURCHASE-ORDER-010/spec.md`. No `acceptance.md` or `plan.md` exists in the SPEC directory (verified via directory listing — only `spec.md` is present), so no cross-reference was possible.

## Pre-Read Failure Mode Checklist (M2)
Before reading, the following plausible failure modes were assumed present and checked: REQ number gaps/duplicates; informal-language ACs instead of EARS; missing/malformed YAML frontmatter fields; implementation detail (HOW) leaking into REQs; broken traceability (orphaned REQs/ACs); hardcoded language-specific tooling; vague/absent Exclusions; internal contradictions.

## Must-Pass Results
- [FAIL] MP-1 REQ number consistency: REQ-DMG-001 through REQ-DMG-007 (spec.md:L74,76,78,80,84,88,96) are sequential, non-duplicated, consistently zero-padded (3 digits). No gap or duplicate found. **This individual check passes**, but see MP-2/MP-3 below for firewall-triggering failures.
- [FAIL] MP-2 EARS format compliance: Every acceptance criterion in the document (AC-1, AC-1b, AC-2, AC-3, AC-3b, AC-4, AC-4b, AC-5, AC-6 — spec.md:L110-162) is written in **Given/When/Then BDD test-scenario format**, not any of the five EARS patterns (Ubiquitous/Event-driven/State-driven/Optional/Unwanted). Example quote from spec.md:L112-114: "**Given** 기존 PO에 연결된 LineItem을 `damaged_exchange`로 변경한다 / **When** `UnorderedItemsView`/`RunComparisonView`/`DailyReviewExcelView` 다운로드를 조회한다 / **Then** 해당 LineItem이 결과에 재노출된다." This is the exact "Given/When/Then test scenarios mislabeled as EARS" failure case cited in the rubric (M3, Score 0.25 band) and in M5 MP-2 definition. 0 of 9 ACs use an EARS pattern. **FAIL.**
- [FAIL] MP-3 YAML frontmatter validity: Frontmatter (spec.md:L1-10) is missing the required `labels` field entirely (no `labels:` key present anywhere in L1-10). It also does not contain a `created_at` field — the document uses `created: 2026-08-07` and `updated: 2026-08-07` instead, which are different field names than the required `created_at`. Per MP-3, "Any missing required field = FAIL." **FAIL.**
- [N/A] MP-4 Section 22 language neutrality: N/A — this SPEC is scoped to a single Python/Django backend feature (LineItem/PurchaseOrder status handling) with a TypeScript frontend dropdown touch-up; it is not multi-language tooling content. No language-specific LSP/tool enumeration issue applies.

**Must-Pass Firewall verdict: Any single MP failure forces overall FAIL. MP-2 and MP-3 both fail independently. Overall Verdict = FAIL.**

## Category Scores (0.0-1.0, rubric-anchored)
| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity a reasonable engineer would resolve consistently | REQ-DMG-005 (spec.md:L84) bundles two structurally distinct bypass behaviors (4-site pattern + separately-patterned ConfirmOrderView bypass) into one requirement, with the second "shall" clause lacking its own explicit trigger wording. Remaining REQs are precisely scoped with exact code references, minimizing ambiguity. |
| Completeness | 0.50 | 0.50 — frontmatter missing one or two fields | Document sections (HISTORY L14, WHY-equivalent "문제 정의" L24, WHAT "솔루션 개요"/"범위" L28/L36, HOW "설계 결정" L44, REQUIREMENTS L70, ACCEPTANCE CRITERIA L108, Exclusions L100) are all structurally present, but frontmatter (L1-10) is missing `labels` and lacks a correctly-named `created_at` field — two required fields absent per MP-3 definitions. |
| Testability | 0.75 | 0.75 — one AC not precisely binary-testable, measurable with minor interpretation | Most ACs are binary-testable (e.g., AC-3b spec.md:L136-138 has a clear pass/fail condition). However AC-6 (spec.md:L162) uses "정상적으로 포함된다" ("is properly/normally included") — a mild weasel-word qualifier — and AC-5 (spec.md:L156) uses "동일하게 동작한다" ("behaves identically") without enumerating which observable behaviors constitute "identical." |
| Traceability | 0.50 | 0.50 — multiple REQs lack ACs | REQ-DMG-001 (spec.md:L74), REQ-DMG-002 (L76), and REQ-DMG-007 (L96) have no dedicated acceptance criterion — REQ-DMG-001/002 appear only as an unstated precondition inside AC-1's Given clause, and REQ-DMG-007 (migration) is checked only via a Definition-of-Done checkbox (L168), not an AC. Additionally, AC-6 (spec.md:L158-163) does not trace to any REQ-DMG-XXX entry in the document — an orphaned AC. No AC header anywhere (L110-162) carries an explicit "Traces: REQ-DMG-XXX" tag; only two ACs (AC-1b at L120, AC-5 at L155) mention a REQ ID inline in prose. |

## Defects Found

D1. spec.md:L110-162 (all nine ACs: AC-1, AC-1b, AC-2, AC-3, AC-3b, AC-4, AC-4b, AC-5, AC-6) — Every acceptance criterion uses Given/When/Then BDD test-scenario format rather than an EARS pattern. This is a direct MP-2 firewall violation. — Severity: critical

D2. spec.md:L1-10 — YAML frontmatter is missing the required `labels` field entirely and does not contain a `created_at` field (uses `created`/`updated` instead). This is a direct MP-3 firewall violation. — Severity: critical

D3. spec.md:L4 — `status: planned` does not match any of the enumerated valid status values (draft, active, implemented, deprecated) used in the audit rubric for FC-3/SC status validation. `priority: High` (L8) is also capitalized rather than matching the rubric's lowercase enumeration (critical/high/medium/low) — minor casing inconsistency, noted for author awareness. — Severity: minor

D4. spec.md:L74, L76, L78, L84, L88, L96 — Multiple requirements embed transient implementation detail (exact file paths, line ranges, migration filenames, explicit code field lists) directly in normative REQ text: "models.py:113-120" (L74), "purchase_order_views.py:1305-1435" and ":744-782" (L88), "0011_lineitem_add_purchase_status.py" (L96), and an explicit `update_fields` bullet list with hardcoded field names (L89-90). This is HOW, not WHAT/WHY, and ties the SPEC's continued validity to exact code line positions that will drift as the codebase changes. — Severity: major

D5. spec.md:L74-96 combined with L108-171 — REQ-DMG-001, REQ-DMG-002, and REQ-DMG-007 have no dedicated acceptance criterion in the ACCEPTANCE CRITERIA section; REQ-DMG-007 (migration) is verified only via a Definition-of-Done checkbox (L168), not a testable AC. — Severity: major

D6. spec.md:L158-163 — AC-6 ("GenerateOrderFileView 자연 포함 확인") does not trace to any REQ-DMG-XXX requirement defined in the document; it is an orphaned acceptance criterion with no formal requirement backing it. — Severity: major

D7. spec.md:L110-162 — No AC header anywhere carries an explicit REQ-DMG-XXX trace tag; only AC-1b (L120) and AC-5 (L155) mention a REQ ID inline in prose text, and the rest (AC-1, AC-2, AC-3, AC-3b, AC-4, AC-4b, AC-6) have zero REQ reference of any kind. This makes REQ-to-AC traceability unreliable and unverifiable by inspection alone. — Severity: major

D8. spec.md:L84 (REQ-DMG-005) — The requirement bundles two structurally distinct bypass behaviors (the shared 4-site query pattern, and a separately-patterned ConfirmOrderView bypass introduced via "Additionally, ..." with no independent "When" trigger clause) into a single REQ entry, reducing single-responsibility clarity of the requirement. — Severity: minor

D9. spec.md:L156, L162 — AC-5 uses "동일하게 동작한다(회귀 없음)" ("behaves identically, no regression") without specifying which observable behaviors constitute "identical," and AC-6 uses "정상적으로 포함된다" ("properly/normally included") — both are mild weasel-word qualifiers requiring judgment calls rather than being strictly binary-testable as written. — Severity: minor

D10. spec.md:L65, L90 — "REQ-CON-022" is referenced as an existing requirement ID belonging to a different (unspecified) SPEC/system, without stating which document it originates from. This does not violate this document's own REQ-DMG numbering (MP-1 still passes on the REQ-DMG series), but the unqualified cross-document reference is a minor clarity gap for a reader without access to the external context. — Severity: minor

## Chain-of-Verification Pass

Second-look findings: Re-read every REQ-DMG entry (001–007) individually to confirm EARS labeling and content (confirmed all present, sequential, no duplicates — MP-1 holds). Re-read every AC entry (AC-1 through AC-6 plus the "b" variants) individually rather than sampling — confirmed all nine use Given/When/Then, not just a subset (initial impression from skimming might have missed AC-3b/AC-4b since they are sub-lettered; explicit re-check confirms both also use Given/When/Then, spec.md:L134-138 and L146-150). Verified REQ-to-AC traceability for all 7 REQs individually (not just samples) — confirmed REQ-DMG-001, 002, 007 are uncovered by any dedicated AC. Re-checked the Exclusions section (spec.md:L100-104) for specificity — all 3 entries are concrete and include rationale, no vague entries found (SC-6 passes). Re-scanned for contradictions between REQ-DMG-005/006 and the Exclusions list — none found; the read-side exposure (REQ-005) and write-side auto-reset (REQ-006) are logically consistent and the Exclusions do not conflict with any included requirement. No additional new defects were found beyond the ten listed above; the initial pass was thorough.

## Recommendation

This SPEC cannot proceed to Run phase in its current form. manager-spec must address the following before resubmission:

1. **Fix MP-2 (critical, blocking)**: Rewrite all nine acceptance criteria (spec.md:L110-162) from Given/When/Then format into EARS patterns (e.g., "When `UnorderedItemsView` is queried after a linked LineItem's `purchase_status` is set to `damaged_exchange`, the system shall include that LineItem in the results" instead of the current Given/When/Then AC-1). Do this for every AC — AC-1, AC-1b, AC-2, AC-3, AC-3b, AC-4, AC-4b, AC-5, AC-6.

2. **Fix MP-3 (critical, blocking)**: Add a `labels:` field to the YAML frontmatter (array or string, e.g., `labels: [purchase-order, backend]`). Rename `created` to `created_at` (or add `created_at` alongside, in ISO date format) so the required field name matches exactly.

3. **Fix traceability gaps (major)**: Add a dedicated AC for REQ-DMG-001 (manual PATCH-set of `damaged_exchange` is a valid choice), REQ-DMG-002 (endpoint accepts it with no code change), and REQ-DMG-007 (migration applies cleanly with no backfill needed — currently only a DoD checkbox). Either remove AC-6 or add a corresponding REQ-DMG entry that it traces to. Add explicit "Traces: REQ-DMG-XXX" tags to every AC header for unambiguous mapping.

4. **Reduce implementation detail in REQ text (major)**: Move exact file paths, line ranges, migration filenames, and explicit field-list values (spec.md:L74, L88-90, L96) out of the normative REQ-DMG-XXX statements and into the "설계 결정"/HOW section (which already exists and is the appropriate place for this level of detail) or into a research.md artifact. Keep REQ text focused on WHAT behavior is required.

5. **Minor cleanups**: Normalize `status` to one of draft/active/implemented/deprecated (or document the project's own valid enum if "planned" is intentional); consider splitting REQ-DMG-005 into two requirements (list-query bypass vs. ConfirmOrderView bypass) for single-responsibility clarity; replace "정상적으로"/"동일하게 동작한다" in AC-6/AC-5 with concrete, enumerable pass conditions; clarify which SPEC "REQ-CON-022" belongs to.
