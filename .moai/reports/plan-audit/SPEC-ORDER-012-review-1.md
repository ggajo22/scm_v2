# SPEC Review Report: SPEC-ORDER-012
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.62 (dimension average 0.875, capped by two Must-Pass firewall failures per M5)

Reasoning context ignored per M1 Context Isolation. Only `spec.md` was used as the primary audit input; `acceptance.md` was checked briefly for cross-reference (REQ/AC ID consistency) per the agent's optional cross-reference allowance. `plan.md` was not needed since no defect required it.

## Must-Pass Results

- [FAIL] MP-1 REQ number consistency: `spec.md:L108-153` lists REQ-RTS-001, 002, 003, **003a**, 004, 005, 006, 007, 008. `REQ-RTS-003a` (L127) breaks the strict "REQ-001, REQ-002, ... REQ-N" sequential pattern required by MP-1 ("Even one gap or duplicate = FAIL"). A lettered sub-ID inserted between REQ-RTS-003 and REQ-RTS-004 is neither a clean increment nor consistent zero-padding of a pure numeric sequence. The HISTORY note (L20) cites SPEC-ORDER-011's "REQ-LOGI-008/009/010" as precedent, but that precedent is a plain numeric sequence, not a lettered sub-ID — it does not justify this deviation.
- [FAIL] MP-2 EARS format compliance: `spec.md:L167-179` — AC-RTS-002a, AC-RTS-002b, AC-RTS-002c are each labeled "(Ubiquitous)" but are phrased as "For an Order with [condition], the system shall [response]". This textual form matches none of the five canonical EARS templates: it is not unconditional ("The system shall..." — Ubiquitous), not "When [trigger]..." (Event-driven), not "While [condition]..." (State-driven), not "Where [feature exists]..." (Optional), and not "If [condition], then..." (Unwanted). It is conditional business logic mislabeled as Ubiquitous, which per M3's rubric anchor and the MP-2 rule ("mixed informal/formal within a single criterion = FAIL") constitutes non-compliance.
- [PASS] MP-3 YAML frontmatter validity: `spec.md:L1-12` — all six required fields present with correct types: `id: SPEC-ORDER-012` (string, matches SPEC-{DOMAIN}-{NUM}), `version: 1.0.0` (string), `status: draft` (string, valid enum), `created_at: 2026-08-09` (ISO date string), `priority: High` (string), `labels: [order, logistics, purchase-order, ready-to-ship]` (array). No missing field, no type mismatch.
- [N/A] MP-4 Section 22 language neutrality: N/A — this SPEC is scoped to Order/LineItem business logic (a single Django backend domain), not multi-language LSP/tooling content. No language-specific tool names are hardcoded anywhere in the document.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements resolved consistently | `spec.md:L147-150` REQ-RTS-007 uses "visually and textually distinct" (vague standing alone), but `spec.md:L205-208` AC-RTS-007 resolves it into a concrete, unambiguous test ("no two badges' header text shares a word in common and no two badges share the same background color"). |
| Completeness | 1.0 | 1.0 — all required sections + frontmatter present, exclusions specific | HISTORY `L16-20`; WHY (문제 정의) `L24-31`; WHAT (솔루션 개요/범위) `L33-61`; HOW (설계 결정) `L63-100`; REQUIREMENTS `L104-153`; ACCEPTANCE CRITERIA `L157-211`; Exclusions `L215-223` with 5 specific, non-vague entries (e.g. "`ready_to_ship`을 수동으로 설정/override하는 PATCH 엔드포인트 — 항상 계산 전용 필드"). |
| Testability | 0.75 | 0.75 — one AC not precisely binary-testable but measurable with minor interpretation | No weasel words ("appropriate/adequate/reasonable/proper/should") found anywhere in `spec.md` (verified via full-document search). `spec.md:L192-195` AC-RTS-004 bundles two shall-statements (recompute all N orders' `ready_to_ship`, AND query count must not scale linearly with LineItems changed) — the second clause is objectively measurable but requires instrumented query-count assertions across multiple N values rather than a single direct check. |
| Traceability | 1.0 | 1.0 — every REQ has >=1 AC, every AC traces to an existing REQ, no orphans | Verified all 9 REQ-RTS ids (001,002,003,003a,004,005,006,007,008) each have >=1 corresponding AC (`L163-211`), and all 11 AC-RTS ids trace to an existing REQ-RTS id with no dangling references. Cross-checked against `acceptance.md:L9-232`, whose `Traces:` lines cite only REQ-RTS/AC-RTS ids that exist in `spec.md` — no mismatches found. |

## Defects Found

D1. spec.md:L127 — REQ-RTS-003a uses a lettered sub-ID, breaking MP-1's required strict sequential REQ-001...REQ-N numbering (sequence reads 001,002,003,003a,004,...008 instead of a clean 001-009 run) — Severity: critical

D2. spec.md:L167-179 — AC-RTS-002a, AC-RTS-002b, AC-RTS-002c are labeled "(Ubiquitous)" but written as "For an Order with [condition], the system shall [response]", which matches none of the five canonical EARS sentence templates — Severity: critical

D3. spec.md:L9 — YAML frontmatter `priority: High` uses capitalized casing; rubric-referenced enum values are lowercase (critical/high/medium/low). Does not trip MP-3 (still a string, field present) but is an inconsistency that should be normalized — Severity: minor

D4. spec.md:L147-150 — REQ-RTS-007's phrase "visually and textually distinct" is vague when read in isolation from its AC; the requirement itself is not independently testable without the AC's added specificity — Severity: minor

D5. spec.md:L132-135 (REQ-RTS-004) and L192-195 (AC-RTS-004) — a single REQ/AC pair bundles two distinct normative statements (per-Order recomputation completeness AND a query-scaling non-functional constraint) under one ID, reducing single-criterion clarity — Severity: minor

## Chain-of-Verification Pass

Second-look findings: Re-read every REQ-RTS entry (001 through 008 plus 003a) individually rather than sampling, re-read every AC-RTS entry (001 through 008 plus 002a/002b/002c/003a) individually, and re-walked the full REQ<->AC bidirectional mapping id-by-id (not spot-checked) — table shown under Traceability evidence above. Re-read the Exclusions section for specificity (5 entries, all concrete, none vague/generic). Re-scanned for contradictions between requirements: REQ-RTS-003 vs REQ-RTS-003a (no conflict — 003 covers pre-existing trigger paths, 003a covers newly-connected paths, mutually exclusive scope); REQ-RTS-005 (Shopify must not overwrite) vs REQ-RTS-006 (one-time backfill migration) — no conflict, migration runs once at deployment, sync exclusion is ongoing. Cross-checked Decision C's "recompute call once per request" design language (L82-88) against REQ-RTS-004's "O(1) queries, scaling by distinct Orders" requirement (L132-135) — initially flagged as a possible contradiction, but on closer reading Decision C's "1회" refers to invoking the batched recomputation function once per request (which itself can update multiple Orders in one SELECT+UPDATE pass per Decision B), not to limiting the scope to a single Order — no actual contradiction, this concern was resolved and is not listed as a defect.

New defect discovered during this pass: D5 (REQ-RTS-004/AC-RTS-004 bundling two normative statements) was not flagged in the initial pass and was added during Chain-of-Verification.

## Recommendation

1. Fix MP-1 (D1): Renumber `REQ-RTS-003a` to a plain sequential number (e.g., make it `REQ-RTS-004` and shift all subsequent REQs down by one: current 004->005, 005->006, 006->007, 007->008, 008->009), OR restructure REQ-RTS-003 and REQ-RTS-003a into a single REQ-RTS-003 that describes both trigger categories together, OR provide explicit written justification in HISTORY that lettered sub-IDs are an accepted project-wide convention with orchestrator sign-off (this SPEC's own citation of SPEC-ORDER-011 does not establish that precedent, since REQ-LOGI-008/009/010 was plain numeric). Apply the same fix to AC-RTS numbering (`AC-RTS-002a/b/c`, `AC-RTS-003a`) for full consistency, renumbering to `AC-RTS-002`, `AC-RTS-003`, `AC-RTS-004`, etc., matching the corrected REQ ids.

2. Fix MP-2 (D2): Rewrite AC-RTS-002a, AC-RTS-002b, AC-RTS-002c to match a canonical EARS template. Since these describe mutually exclusive computed states of `ready_to_ship`, the cleanest fix is to restructure each as a State-driven pattern, e.g.: "While an Order has zero non-excluded trackable LineItems, the system shall set `ready_to_ship` to `null`." / "While an Order has at least one non-excluded trackable LineItem with `purchase_status=\"cs_required\"`, the system shall set `ready_to_ship` to `False`." / "While an Order has at least one non-excluded trackable LineItem and none is `cs_required`, the system shall set `ready_to_ship` to `True` if and only if every non-excluded LineItem satisfies `logistics_status=\"received\"` OR `purchase_status=\"in_stock\"`, and to `False` otherwise." Re-label each with the correct EARS pattern tag ("State-Driven") instead of "(Ubiquitous)".

3. Address D3 (minor): Normalize `priority: High` to lowercase `high` in the YAML frontmatter to match the project's documented enum convention (critical/high/medium/low).

4. Address D4 (minor, optional): Consider tightening REQ-RTS-007's language to be self-contained and testable without relying on AC-RTS-007 for the operative definition, e.g. state the "no shared header word / no shared background color" rule directly in the REQ.

5. Address D5 (minor, optional): Consider splitting REQ-RTS-004 / AC-RTS-004 into two ids — one for "recompute all N affected Orders" and one for "query count does not scale linearly with LineItems changed" — for cleaner single-criterion traceability, though this is not blocking.

Once D1 and D2 are resolved, re-submit for iteration 2. All other findings (D3-D5) are minor and do not block progression but should be addressed for document quality.
