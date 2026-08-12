# SPEC Review Report: SPEC-ORDER-016
Iteration: 3/3 (final escalation)
Verdict: FAIL
Overall Score: 0.80

Reasoning context ignored per M1 Context Isolation. No author reasoning, prior drafts, or
conversation history was consulted. `interview.md` and `research.md` were read only as INPUT
artifacts to test the SPEC's fidelity to them; their content is not re-litigated. All verdicts rest
on `spec.md` v1.0.2, `plan.md` v1.0.2, `acceptance.md` v1.0.2, `spec-compact.md` v1.0.2, the
iteration-1 and iteration-2 reports, and direct inspection of the cited source files. The document
was treated as largely new, per the brief.

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency** — Enumerated mechanically
  (`grep -oE '^\*\*REQ-FORCE-[0-9]+[a-z]?\*\*' spec.md | sort | uniq -c`): **24 IDs, each with
  count 1**, base series 001–024 complete, **zero alphabetic suffixes**, uniform 3-digit padding.
  The declared numbering rule at spec.md:L295-297 ("`REQ-FORCE-001`부터 `REQ-FORCE-024`까지 연속
  번호이며 결번·중복·알파벳 접미사가 없다") is now literally true, where in v1.0.1 it required a
  14-element suffix list. AC series: **22 IDs, count 1 each**, 001–022, no gaps. Both counts match
  the document's own claims (spec.md:L571, spec-compact.md:L14/L77).
- **[PASS] MP-2 EARS format compliance** — All 24 REQ and 22 AC entries carry a declared pattern
  label (mechanical count: 19 Ubiquitous + 14 Event-Driven + 8 Unwanted + 5 State-Driven = 46 =
  24+22) and every one uses `shall`. A grep across all four documents for
  `appropriate|adequate|reasonable|proper|sufficient|should|may be` returns **zero hits** — the
  iteration-2 residual "sufficient" is gone. Given/When/Then remains quarantined in
  `acceptance.md`. **This is a PASS under the same standard applied in iterations 1 and 2**
  (declared label + `shall` + a recognisable keyword form); I am deliberately not tightening the
  firewall in the final round on an unchanged construct. The single-pattern purity deviations are
  real and are recorded as **F4**, which is stagnant across all three iterations.
- **[PASS] MP-3 YAML frontmatter validity** — spec.md:L1-11 carries `id: SPEC-ORDER-016` (string),
  `version: 1.0.2` (string), `status: draft` (string), **`created_at: 2026-08-12` (L5 — correct
  field name, ISO date)**, `priority: High` (string), `labels: [order, logistics, outbound, force]`
  (array). All six required fields present with correct types. No regression on the parent SPEC's
  `created` vs `created_at` defect. All four documents were bumped to 1.0.2 together (spec.md:L3,
  plan.md:L4, acceptance.md:L4, spec-compact.md:L4) — no stale-version drift.
- **[N/A] MP-4 Section 22 language neutrality** — Single-stack SPEC (Django/Python backend +
  React/TypeScript frontend). No multi-language tooling content. Auto-passes.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.65 | between 0.50 and 0.75 — fewer requirements need interpretation than in iteration 2, but one central write rule is self-contradictory | Improved: N1/N2/N3/N4/N5/N10/N11/N13/N14 are all genuinely closed (see regression section), and the four iteration-2 undefined behaviours are pinned. Remaining: REQ-FORCE-009's trigger is satisfied by a zero combined quantity and mandates a write that AC-FORCE-006 and AC-FORCE-011 forbid (**F1**, L352-357 vs L472-477/L499-503); REQ-FORCE-007's "exactly two respects" is false (**F3**, L339-345 vs L306-313 and L613-615); REQ-FORCE-015's "entire set" contradicts REQ-FORCE-023 (**F7**, L383-385 vs L426-427); "structurally malformed" is undefined and its boundary with REQ-FORCE-011 decides 400-vs-`invalid_total` (**F8**, L306 vs L364-365) |
| Completeness | 0.85 | above the 0.75 anchor — all sections present, frontmatter complete, one area sparse | HISTORY (L15-21) + consolidation table (L23-38), 문제 정의 (L42-57), 솔루션 개요 (L59-80), 범위 델타 (L82-98), 설계 결정 A–N (L100-291), 요구사항 5 modules (L293-432), ACCEPTANCE CRITERIA + traceability table (L436-574), Exclusions **21 specific entries** (L578-627, counted individually and cross-checked against plan.md:L196 "21개" and spec-compact.md:L133-156), 후속 과제 4 items (L629-649), 관련 SPEC (L651-664). Docked for **F2** (설계 결정 N mandates a behaviour whose operational cost is neither recorded nor tested, where 설계 결정 L does record its "수용된 대가" at L263-265) and **F9** (three behaviours removed by the v1.0.2 consolidation survive with no AC and no layer-gate assignment) |
| Testability | 0.80 | above the 0.75 anchor — one AC is not precisely binary-testable and two behaviours lost their only assertion | Genuine gains over iteration 2: every retained AC now carries concrete fixture values or boundary cases (AC-FORCE-002's seven enumerated violations L450-455; AC-FORCE-007's 6+5-against-10 L479-482; AC-FORCE-008's 4+6-exactly-10 with the `sku` derivation L484-489; AC-FORCE-011's four rejection rows plus the offset case L499-503; AC-FORCE-004's deliberately inverted pk-vs-creation order L462-464). Docked for **F6** (AC-FORCE-005 traces REQ-FORCE-006 but does not assert its attribute set), **F9(a)(b)** (candidate-lookup read-only-ness and section visual reproduction have no criterion), and AC-FORCE-016's trailing clause "so that the existing client result-rendering path consumes it without modification" (L526-527), which is not verifiable at its declared `[BE]` layer |
| Traceability | 0.90 | at the 1.0 anchor but for one listed-not-asserted mapping | Recomputed end-to-end, not sampled. All 22 `Traces:` clauses extracted from spec.md and all 22 from acceptance.md and compared pairwise — **identical, 22/22**. Every clause resolves to an existing REQ; **all 24 REQs covered, 0 orphaned ACs, 0 dangling references**; the L556-569 table independently reproduced. The document's own arithmetic at L571-574 verified true: exactly 5 multi-REQ ACs (001, 005, 007, 008, 015) and exactly 4 two-AC REQs (008, 009, 010, 016). The layer gates partition cleanly: backend 16 REQs + frontend 9 REQs − 1 overlap (003) = 24; backend 16 ACs + frontend 7 ACs − 1 = 22 (acceptance.md:L275-288). Docked 0.10 solely for **F6** |

## Regression Check — iteration 2 defects N1–N14

Every one of the 14 was addressed. Three are incompletely closed (N6, N7, N9) and one fix spawned a
new major defect (N4 → F2). None of the resolutions is merely cosmetic except where noted.

- **N1 (major, AC-FORCE-001 contradicted 설계 결정 J and was unexecutable at `[BE]`) — RESOLVED,
  genuinely.** AC-FORCE-001 (spec.md:L444-448) is now a pure display-layer assertion over a
  five-row fixture and is labelled `[FE]` in both documents (acceptance.md:L26). The clause "the
  same row shape submitted with any other reason code … shall not reach that outcome" is **gone**;
  a grep of spec.md for any server-side reason gate returns nothing, and Exclusion L597-599
  affirmatively states the opposite ("사유를 근거로 행을 거부하지 않는다"). 설계 결정 J (L206-224)
  now closes with an explicit prohibition on such a requirement existing. The coverage gates list
  REQ-FORCE-001 as frontend-only (acceptance.md:L286, plan.md:L35) — consistent with the payload,
  which per plan.md:L89-90 carries no reason code. **No residue.**
- **N2 (major, merged matched item granularity and field values undefined) — RESOLVED, and the
  derivation argument checks out.** 설계 결정 K (L226-247) now fixes the response as per-designated-
  target and derives each field: `line_item_id` = the target; `sku` = **the target LineItem's own
  `sku`**; `total` = the combined quantity; `name` = the order name, justified by the claim that
  the gate validates every target against the Order its row's identifier resolves to, so merged
  rows necessarily share a `name`. **I checked that justification rather than accepting it**: the
  gate (REQ-FORCE-002, L308-309) requires the target to belong to "the Order its order identifier
  resolves to under REQ-FORCE-004", and REQ-FORCE-004 (L323-326) resolves by exact `Order.name`
  equality — so two rows designating one target must both carry that Order's exact `name`. The
  argument is sound. REQ-FORCE-016 (L394-397) carries the rule normatively, not only in the design
  decision. "Combined quantity" is now defined for the one-row case ("a group of one row yielding
  that row's quantity", L349-350), closing the second half of N2. AC-FORCE-008 (L484-489) is the
  successful-merge AC that iteration 2 demanded and it asserts the `sku` derivation explicitly.
- **N3 (major, item schema narrower than the client types) — RESOLVED. Verified against the real
  type declarations, not the document.** `frontend/src/services/outboundApi.ts:37-47` declares
  `OutboundMatchedItem { name, sku, total, line_item_id, shipped_quantity, quantity: number|null,
  logistics_status }` — seven required fields; `:49-54` `OutboundUnmatchedItem { name, sku, total,
  reason }`; `:56-65` `OutboundQuantityExceededItem { name, sku, total, line_item_id,
  shipped_quantity, quantity, reason: 'quantity_exceeded' }`. REQ-FORCE-016 (L390-393) now
  enumerates **exactly** those sets: "`name`, `sku`, `total`, `line_item_id`, `shipped_quantity`,
  `quantity` and `logistics_status` for a matched item; the same with `reason` in place of
  `logistics_status` for a quantity-exceeded item; `name`, `sku`, `total` and `reason` for an
  unmatched item". Field-for-field identical, in both directions. The server side matches too
  (`purchase_order_views.py:3026-3036`, `:3040-3050`, `:2954-2980` — all read and confirmed).
  plan.md:L59 now mandates returning the existing `OutboundProcessResponse` type unchanged, and
  plan.md:L60 keeps the `useOutboundMutation` factory reuse, which is now type-consistent
  (`useOutboundQueries.ts:20-21` requires `(vars) => Promise<OutboundProcessResponse>`, verified).
  AC-FORCE-016 (L523-527) and acceptance.md:L202-207 assert "좁히거나 넓히지 않아". **Fully closed.**
- **N4 (major, post-execution row state ambiguous, repeat-application possible) — RESOLVED as to
  the ambiguity; the chosen resolution has an unrecorded cost (→ F2).** 설계 결정 N (L280-291) and
  REQ-FORCE-024 (L429-432) fix replacement of the single result slot, and the factual basis is
  correct: `OutboundPage/index.tsx:31-33` declares one `result` slot, `:42` and `:52` both
  `onSuccess: setResult` — verified in source. AC-FORCE-022 (L550-552) and acceptance.md:L258-266
  assert the processed rows are no longer displayed. plan.md R18 (L163) records the reasoning. The
  repeat-application hole is structurally closed. → **F2**.
- **N5 (minor, unresolvable order identifier) — RESOLVED.** REQ-FORCE-002 (L308) now lists "whose
  order identifier resolves to no Order" among the gate violations; AC-FORCE-002 case (d) (L452)
  and acceptance.md:L46-47 (d) cover it; plan.md:L98-99 explicitly forbids the skip-when-`None`
  implementation.
- **N6 (minor, "exactly one rule" false) — PARTIALLY RESOLVED → F3.** "Exactly one" became
  "exactly two respects" with both deviations enumerated (L339-342), and the carve-out sentence
  was folded into that enumeration rather than left as a scoping note. But a **third** deviation
  now exists and is not counted: the existing path degrades a malformed row to `invalid_row`
  per-row, while REQ-FORCE-002 rejects the whole request with HTTP 400 — a deviation the SPEC
  itself acknowledges at Exclusions L613-615 ("구조 오류는 행 단위 보고가 아니라 요청 전체
  HTTP 400"). The absolute quantifier is still false.
- **N7 (minor, EARS purity applied inconsistently) — NOT RESOLVED → F4, and stagnant across all
  three iterations.** Iteration 2 gave a concrete instruction: "re-cast AC-FORCE-009's 'Given'
  opener as a `While …` State-Driven opener" and "split the grafted unconditional clauses out". The
  "Given" opener was **moved, not fixed** — it is now AC-FORCE-006 (L472). New grafted clauses were
  introduced in REQ-FORCE-001 and REQ-FORCE-002. Details in F4.
- **N8 (minor, malformed-row verdict undefined) — RESOLVED in verdict, not in definition → F8.**
  REQ-FORCE-002 (L306) now assigns "structurally malformed" to the 400 gate, and plan.md:L93-94
  makes it the gate's first step. The term itself is undefined in spec.md.
- **N9 (minor, empty request left to implementer discretion) — RESOLVED for the candidate lookup,
  implicit for the force request.** REQ-FORCE-003 (L320-321) now states "for an empty set the
  system shall return an empty result rather than an error"; AC-FORCE-003 (L459-460) and
  acceptance.md:L58-62 (b) test it; plan.md:L75 no longer offers the either/or. The empty
  force-execution row list is covered only by REQ-FORCE-015's "regardless of how many rows"
  (L384-385), which is a weak but defensible reading. Accepted.
- **N10 (minor, stale-read failure modes understated) — RESOLVED.** 후속 과제 2 (L637-645) now
  splits (a) `shipped_quantity`-only staleness → safe `quantity_exceeded` with other targets still
  applied, and (b) target cancelled or `sku` lost → **whole request HTTP 400**, explicitly noting
  the batch-wide blast radius. plan.md R8 (L153) matches, and adds an operator-communication
  instruction. Verified consistent with 설계 결정 L.
- **N11 (minor, `purchase_status` labelling unreachable) — RESOLVED.** REQ-FORCE-021 (L419-421) now
  covers "every `logistics_status` value and every unmatched-reason value" only; `purchase_status`
  is gone. AC-FORCE-020 / acceptance.md:L247 use `not_shipped` and `line_item_not_found` — both
  reachable. plan.md:L63 explicitly instructs **not** to build a `purchase_status` label map and
  gives the reason. 설계 결정 D (L150-152) records why the value never leaves the server.
- **N12 (major/structural, over-specification) — RESOLVED as to volume; two consolidation losses
  → F6, F9.** 39 REQ → 24, 40 AC → 22, alphabetic suffixes abolished, and every merge is recorded
  in the L23-38 table. I traced all twelve table rows; ten preserve their content in a remaining
  requirement, an Exclusion or a design decision. The exceptions are recorded as F9.
- **N13 (minor, imprecise path) — RESOLVED.** plan.md:L60 now cites
  `frontend/src/features/order/hooks/useOrders.ts:11` (verified: `queryKey: [...ORDERS_QUERY_KEY,
  params]`) and explicitly notes that `useRackNumberQueries.ts:76-81` is the *parameterless* example
  and therefore not the one to follow — the exact correction requested.
- **N14 (minor, 설계 결정 L justified circularly) — RESOLVED.** L249-261 now leads with the
  client-desync argument and demotes the no-new-reason-code policy to a consequence in so many
  words: "다만 그 방침은 이 결정의 **결과**이지 근거가 아니다" (L260-261). The accepted cost is
  stated at L263-265.

## Consolidation Audit — did the v1.0.2 merge lose normative content?

Each row of the L23-38 table was traced to its claimed destination and the destination text read.

| Removed v1.0.1 item | Claimed destination | Survives? |
|---|---|---|
| REQ-FORCE-001a, 001b | REQ-FORCE-019 | **Yes.** REQ-FORCE-019 (L411-413) renders controls "on exactly the rows that are eligible per REQ-FORCE-001"; REQ-FORCE-023 (L426-427) includes in the request "exactly those displayed rows that are eligible, selected and carrying a designated target". "Exactly" carries both directions. AC-FORCE-001's four ineligible rows test it |
| REQ-FORCE-003 | REQ-FORCE-002 | **Yes.** "carries no designated target LineItem identifier" (L307) → HTTP 400; AC-FORCE-002 case (b) (L451) plus the no-auto-selection assertion (L454-455) |
| REQ-FORCE-002a, 025 | Exclusions | **Yes, but no AC.** Exclusions L600-601 (`quantity_exceeded` 섹션 무변경) and L624-625 (라우팅·사이드바, named export, 폴더+index 해석). Verification survives only as an acceptance.md regression/Exclusion-sweep item (L294-298, L303-305), not as a criterion |
| REQ-FORCE-010b | REQ-FORCE-009 조건절 + AC | **Weakly — see F9(c).** The table's justification is a non-sequitur; the behaviour survives only in AC-FORCE-009 (L493) |
| REQ-FORCE-013a, 014 | REQ-FORCE-013 | **Yes, and strengthened.** L372-376 is a closed-world write restriction covering creation/deletion, other LineItem fields, and every `Order` field; AC-FORCE-013 (L509-513) verifies by field-level diff plus a recompute spy |
| REQ-FORCE-008 정렬 결정성 | REQ-FORCE-006 | **Yes.** "in a deterministic order" (L332-333); AC-FORCE-005 asserts identical ordering on repeat (L470) |
| REQ-FORCE-008 읽기 전용성 | Exclusions | **Partially — F9(a).** Exclusion L607-608 is normative, but no AC and no gate item assert it for a non-empty lookup |
| REQ-FORCE-019a | plan.md | **Yes**, plan.md:L59 (optional-only field additions) and R4 (L149). Correctly re-homed — it is a type-system instruction |
| REQ-FORCE-020b 테스트 훅 | plan.md | **Yes**, plan.md:L62 (b) pins `data-testid="outbound-unmatched"` and names the test that depends on it |
| REQ-FORCE-020b 시각적 일관성 | 설계 결정 M + plan.md | **Partially — F9(b).** 설계 결정 M:L276-278 and plan.md:L62 (a) state it; no AC and no gate item |
| REQ-FORCE-012 미국창고 조항 | REQ-FORCE-007 편차 열거 | **Yes.** L342 ("the existing path's post-match handling of a zero amount is not inherited"); AC-FORCE-006 (b) (L475-477) and acceptance.md:L96-99 test it differentially against the normal path |
| 순수 재진술 AC 12건 | 삭제 | **Yes.** I mapped every deleted v1.0.1 AC to a surviving criterion (candidate exclusion → AC-005; candidate attributes → AC-005/AC-019; below-threshold → AC-009; quantity limit → AC-007/AC-010; write scope → AC-013; single request → AC-015; controls → AC-001; picker → AC-019; Korean labels → AC-020; control availability → AC-021; target gate cases → AC-002, which is *stronger* than the v1.0.1 pair). **No deleted AC removed the only coverage of a real behaviour**, with the two exceptions already recorded as F9(a) and F9(b) |

## Defects Found

**F1. spec.md:L352-357 (REQ-FORCE-009) vs L347-350 (REQ-FORCE-008), L364-367 (REQ-FORCE-011),
L472-477 (AC-FORCE-006) and L499-503 (AC-FORCE-011) — a target whose rows are all rejected has a
combined quantity of zero, which satisfies REQ-FORCE-009's trigger and mandates a write the SPEC's
own acceptance criteria forbid — Severity: major**

REQ-FORCE-008 groups rows by designated target and sums them "into that target's combined
quantity", then evaluates "each target exactly once". REQ-FORCE-011 excludes a negative, zero or
unreadable row "from its target's combined quantity". If **every** row designating a target is
excluded, that target's combined quantity is 0 and the target is still in the grouping, so it is
still evaluated.

REQ-FORCE-009 then fires: "When the sum of a target LineItem's current `shipped_quantity` and its
combined quantity does not exceed that LineItem's ordered `quantity` … the system shall increase
that LineItem's `shipped_quantity` by the combined quantity, **shall set `shipped_at` to the
processing timestamp**, and **shall set `logistics_status` to `"shipped"` at the moment the
resulting `shipped_quantity` reaches or exceeds the ordered `quantity`**."

Worked consequences, all reachable through fixtures the SPEC itself constructs:

- acceptance.md:L145-151 case (b): target LA has `quantity=10`, `shipped_quantity=8`, and its only
  row is quantity `0` → excluded → combined 0 → `8 + 0 ≤ 10` → REQ-FORCE-009 requires stamping
  `shipped_at`. AC-FORCE-011 requires "LA와 LB는 무변경" (L151). Direct contradiction.
- acceptance.md:L146 / L96-99: target LB / L3 is `warehouse_ca`-confirmed with `quantity=10`,
  `shipped_quantity=0`, single row `0` → combined 0 → `0 + 0 ≤ 10` → `shipped_at` stamped.
  AC-FORCE-006 requires "강제 경로는 L3를 전혀 변경하지 않는다" (L98-99) and spec.md:L476-477 says
  "the force path shall leave it unmodified". Direct contradiction.
- Worst case: a target with `quantity` `null` (capacity 0 per L353-354, L360) whose only row is
  rejected → combined 0 → `0 + 0` does not exceed `0` → REQ-FORCE-009 fires **and** the threshold
  clause fires because `0 ≥ 0` → `logistics_status = "shipped"`. A LineItem is marked shipped on
  the strength of an `invalid_total` row. The same holds for any already-complete target
  (`shipped_quantity >= quantity`).

This is precisely the zero-amount completion behaviour REQ-FORCE-007 (L342) declares "not
inherited", re-entering through a different door, and it defeats the Exclusion at L584-587.

The only text arguing against this reading is REQ-FORCE-011's "shall modify no LineItem **on
account of it**" (L366) — but that is a guard on the rejected row, not a statement that a
zero-combined target is skipped, and it says nothing about whether such a target is *reported*
(as a `matched` item with `total: 0`, per REQ-FORCE-008's "report each target exactly once" and
REQ-FORCE-016's list-length-equals-count contract at L523-527). An implementer has to invent the
rule.

**What must change**: require a strictly positive combined quantity in REQ-FORCE-009's trigger, or
state in REQ-FORCE-008 that a target whose combined quantity is zero after REQ-FORCE-011 exclusions
is neither evaluated nor reported. Add an AC for the all-rows-rejected target, including the
`quantity`-`null` and already-complete variants.

**F2. spec.md:L429-432 (REQ-FORCE-024), L280-291 (설계 결정 N), L550-552 (AC-FORCE-022),
acceptance.md:L258-266 — replacing the result slot silently discards unmatched rows the operator did
not select, and neither the design decision nor any criterion records or tests it — Severity: major**

REQ-FORCE-024 requires the system to "replace the displayed outbound result with the force
response". That fully determines the outcome — but the consequence extends past the rows just
processed:

- Eligible `line_item_not_found` rows the operator did **not** select disappear from the screen.
  With N eligible rows and a partial batch, the remaining N−k rows are lost from the work list.
- Rows the force run itself reports as `quantity_exceeded` (REQ-FORCE-010) move out of the unmatched
  section, so the operator cannot re-designate and retry them.
- The operator's only recovery is to re-run the original outbound processing, which the SPEC does
  not mention.

The SPEC's own convention is to record such costs: 설계 결정 L (L263-265) explicitly heads a
paragraph "**수용된 대가**", quantifies it ("6행짜리 배치에서 대상 하나가 낡으면 나머지 5행도
반영되지 않는다"), and routes it to 후속 과제 2. 설계 결정 N (L280-291) contains no equivalent — it
argues only the re-submission-prevention benefit. `interview.md` Q3 confirmed 일괄 실행 as the
execution unit and is silent on what happens to unselected rows.

No criterion pins it either. AC-FORCE-022's fixture has three displayed rows of which two are
processed (acceptance.md:L262), and the Then clause speaks only of "직전에 처리한 매칭 실패 행들"
(L264) — the third row's fate is not asserted in either document. A reviewer reading only the ACs
would not learn that it vanishes.

**What must change**: add an accepted-cost paragraph to 설계 결정 N stating that unselected and
newly-quantity-exceeded rows are also cleared and that recovery requires re-running outbound
processing; extend AC-FORCE-022 (and acceptance.md's Then) to assert the third row's fate
explicitly, so the behaviour is chosen rather than inherited.

**F3. spec.md:L339-345 (REQ-FORCE-007) vs L306-313 (REQ-FORCE-002) and L613-615 (Exclusions);
spec-compact.md:L37-39 — the "exactly two deviations" claim is still false — Severity: minor**

REQ-FORCE-007 asserts the force path "shall deviate from the existing outbound processing path in
**exactly two** respects" and that "**Every other rule** of the existing path shall apply
identically". A third deviation exists and the SPEC states it elsewhere: the existing path degrades
a structurally malformed row to the per-row reason `invalid_row` (confirmed in the client union at
`outboundApi.ts:32-35`, "Malformed row shape reaching the shared processing path"), whereas
REQ-FORCE-002 rejects the entire request with HTTP 400, and Exclusion L613-615 says so in as many
words: "구조 오류는 행 단위 보고가 아니라 요청 전체 HTTP 400으로 처리한다".

This is the same class of defect as iteration-2 N6 ("exactly one rule" contradicted by a carve-out
in the same requirement), relocated rather than eliminated. `spec-compact.md:L37-39` propagates the
false quantifier.

**What must change**: enumerate three deviations, or scope the claim to the judgement/write rules it
actually lists ("the rules governing amount validation, summation, capacity and status transition
apply identically") rather than to every rule.

**F4. Multiple locations — EARS single-pattern purity; present in iteration 1 (D10), iteration 2
(N7) and unchanged here — Severity: minor (stagnant)**

Grafted second patterns (a conditional trigger followed by an unconditional obligation) — the exact
construction that REQ-FORCE-002/002a and REQ-FORCE-023/023a were split apart to remove in v1.0.1:

- REQ-FORCE-001 (L301-304), State-Driven: "While … the system shall treat that row as eligible;
  **every other displayed row shall be ineligible**." The second clause is Ubiquitous.
- REQ-FORCE-002 (L306-313), Unwanted: "… then the system shall reject the entire request …, **and
  the system shall NOT substitute or infer a target by any fallback rule**." The prohibition holds
  for every request, not only those the `If` selects.
- AC-FORCE-021 (L546-548), State-Driven: "While two eligible rows are selected and neither carries a
  designated target, the system shall keep the control unavailable, **and shall make it available as
  soon as one of them is designated**" — the second clause fires precisely when the `While`
  condition is falsified.
- REQ-FORCE-003 (L317-321), Event-Driven: a second trigger ("for an empty set …") appended after a
  semicolon.

Non-EARS openers:

- AC-FORCE-006 (L472): "**Given** two LineItems in identical initial state, the system shall …".
  Iteration 2 (N7) named this construct and gave the fix ("re-cast … as a `While …` State-Driven
  opener"); it was carried to a new ID unchanged.
- AC-FORCE-005 (L466): "**For** an order holding one ordinary LineItem, …".

Pattern-label mismatches:

- AC-FORCE-013 (L509), labelled Ubiquitous: "**After** a force request that transitions a target to
  `"shipped"`, …" — Event-Driven.
- AC-FORCE-014 (L515), labelled Ubiquitous: "… **when** the force write step raises an exception
  partway through …" — Event-Driven.
- AC-FORCE-020 (L542), labelled Ubiquitous: "**With** the picker open and a row's failure reason
  displayed, …" — State-Driven.
- REQ-FORCE-009 (L352), labelled Event-Driven: "When the sum … **does not exceed** …" is a state
  condition, not an event, and it embeds a second trigger ("at the moment the resulting
  `shipped_quantity` reaches or exceeds …").

**Stagnation assessment**: this defect appears in all three iterations. Each revision fixed the
specific instances cited and reintroduced the construction elsewhere, which indicates the authoring
habit — not the individual sentences — is the problem. Flagged as a **stagnant defect**.

**F5. spec.md:L444-448 (AC-FORCE-001) vs acceptance.md:L30-32 — the criterion miscounts its own
fixture — Severity: minor**

AC-FORCE-001 opens "While the unmatched section displays **five** rows" and then lists four
unmatched rows plus "**one row from the quantity-exceeded section**", which by definition is not
displayed in the unmatched section. acceptance.md states it correctly: "매칭 실패 섹션에 다음 **4개**
행이 있다 … 수량초과 섹션에도 1건이 있다" (L30-32). The two documents disagree on the fixture even
though their `Traces:` lines match.

**What must change**: "displays four rows … and one row is present in the quantity-exceeded
section".

**F6. spec.md:L466-470 (AC-FORCE-005) vs L332-335 (REQ-FORCE-006) and acceptance.md:L82-84 — a REQ
listed in a multi-REQ `Traces:` line is only partially asserted — Severity: minor**

AC-FORCE-005 traces REQ-FORCE-005 and REQ-FORCE-006. It asserts the exclusion rule (REQ-FORCE-005),
the no-remaining-capacity indicator and the deterministic ordering (REQ-FORCE-006, partial) — but it
does **not** assert REQ-FORCE-006's per-candidate attribute set: "a stable identifier, book title,
`sku`, ordered `quantity`, current `shipped_quantity`, current `logistics_status`". acceptance.md's
scenario does ("각 후보는 안정적 식별자, 도서명, `sku`, 주문 수량, 기출고 수량, 물류 상태를 갖고",
L82-83), so the two documents state different criteria under the same ID.

REQ-FORCE-006 has no second AC. The only other place the attributes are checked is AC-FORCE-019
(L537-540), which is `[FE]` and traces REQ-FORCE-020 — it verifies what the *picker renders*, not
what the *endpoint returns*. So at the backend layer the candidate response contract has no spec.md
criterion. This is the one case among the five multi-REQ ACs where a traced requirement is listed
but not genuinely asserted; the other four (001, 007, 008, 015) assert every REQ they claim —
checked individually.

**What must change**: add the attribute assertion to AC-FORCE-005, matching acceptance.md.

**F7. spec.md:L383-385 (REQ-FORCE-015) vs L426-427 (REQ-FORCE-023) and L519-521 (AC-FORCE-015) —
two requirements disagree on what the request contains — Severity: minor**

REQ-FORCE-015: "When the operator executes force processing for a set of selected rows, the system
shall transmit and process **the entire set** in a single request". REQ-FORCE-023: "The system shall
include in a force execution request **exactly those** displayed rows that are eligible, selected
and carrying a designated target." AC-FORCE-015 (which traces both) resolves it against
REQ-FORCE-015: six selected rows, two without targets, "exactly one request containing exactly the
**four** designated rows".

REQ-FORCE-015's intent is clearly "one request, not N" — but as written "the entire set" is false.

**What must change**: "shall transmit and process in a single request the entire set of rows it
includes per REQ-FORCE-023, regardless of how many rows or how many distinct orders they span".

**F8. spec.md:L306 (REQ-FORCE-002) vs L364-365 (REQ-FORCE-011); acceptance.md:L45-46 — the term
"structurally malformed" is undefined, and its boundary decides between HTTP 400 and a per-row
report — Severity: minor**

REQ-FORCE-002 sends a "structurally malformed" row to a whole-request HTTP 400. REQ-FORCE-011 sends
a row whose quantity "could not be genuinely read as a number" to a per-row `invalid_total`. A row
such as `{order, sku, quantity: "네 개", line_item_id: 5}` satisfies both descriptions on a plain
reading, and the two outcomes are maximally different (nothing applied vs everything else applied).

The boundary is settled only by a parenthetical inside an acceptance.md fixture — "(a) 구조가 깨진
행(dict 아님 또는 필수 키 누락)" (L45-46) — which is a fixture description, not a definition, and
does not appear in spec.md at all. plan.md:L93-94 orders the gate first without defining its scope.

**What must change**: define "structurally malformed" in REQ-FORCE-002 (not a dict, or a required
key absent) and state in REQ-FORCE-011 that a present-but-unreadable quantity value is *not*
structural malformation.

**F9. Consolidation losses — three behaviours removed by v1.0.2 survive without verification —
Severity: minor**

(a) **Candidate-lookup read-only-ness.** The v1.0.2 table (L33) moves it from REQ-FORCE-008 to an
Exclusion (L607-608). It survives normatively, but AC-FORCE-003 asserts "write nothing" only for the
**empty**-set call (L459-460, acceptance.md:L61-62), and neither layer gate (acceptance.md:L275-288)
carries a read-only test. A non-empty candidate lookup that wrote to a LineItem would pass every
listed criterion.

(b) **Dedicated section component's visual reproduction of the existing section.** Moved to 설계
결정 M (L276-278) and plan.md:L62 (a). No AC, no gate item. The v1.0.1 AC-FORCE-020b that covered it
was deleted.

(c) **Below-threshold status invariance.** The table (L30) justifies deleting v1.0.1 REQ-FORCE-010b
with "'임계 도달 시 전이한다'가 미달 시 변경을 허용하지 않는다" — a non-sequitur. REQ-FORCE-009's
positive obligation ("shall set `logistics_status` … at the moment … reaches or exceeds") does not
prohibit setting it below the threshold; REQ-FORCE-013 restricts *which* fields may be written, not
their values. The behaviour survives only in AC-FORCE-009's "shall leave `logistics_status` at its
previous value" (L493) — no requirement states it.

**What must change**: add "and shall leave `logistics_status` unchanged below that threshold" to
REQ-FORCE-009; add a read-only assertion to AC-FORCE-005 or a gate item for (a); accept (b) as a
plan-level concern or give it a criterion.

**F10. plan.md:L60; spec.md:L132 — off-by-one citation starts — Severity: minor (trivial)**

plan.md:L60 cites "`ORDER_DETAIL_QUERY_KEY` prefix 무효화(`:28`)"; the invalidation call is at
`useOutboundQueries.ts:29` (`:28` is the `onSuccess` opener). The same line cites "고정 한국어 에러
문구(`:31-33`)"; `:31-33` is the generic `onError` handler and the fixed Korean strings are at `:38`
and `:43`. spec.md:L132 cites `test_spec_015.py:932-1021` and `:1524-1637`; the classes begin at
`:933` (`TestOutboundRejectsNonPositiveTotals`) and `:1523`
(`TestZeroTotalRequiresAGenuineParsedZero`). Every substantive claim is correct; only the range
starts are imprecise.

## Citation Verification (fresh sample, concentrated on this revision)

Thirty-five citations were checked against the real files, not trusted. **Zero substantive
mis-citations**; the only findings are the three off-by-one range starts in F10.

New or moved in v1.0.2 (설계 결정 N, REQ-FORCE-016, R17, R18, N13 fix):
`OutboundPage/index.tsx:31-33` (single `result` slot with the REQ-OUTBOUND-018 comment), `:42`
(`processMutation.mutate(rows, { onSuccess: setResult })`), `:52` (`onSuccess: setResult`),
`:141-142` and `:176` (reads `shipped_quantity`/`quantity`/`logistics_status`), `:148`
(`testId="outbound-unmatched"`), `:154` (`key={name}-{sku}-{index}`), `:24-28` (@MX:ANCHOR + named
export); `outboundApi.ts:37-47`, `:49-54`, `:56-65`, `:69-76` (all four response types, field by
field); `useOutboundQueries.ts:14-16` (`buildOutboundSummary`), `:20-35` (mutation factory with
`Promise<OutboundProcessResponse>`); `features/order/hooks/useOrders.ts:11`
(`queryKey: [...ORDERS_QUERY_KEY, params]` — the N13 correction is accurate, and the caveat about
`useRackNumberQueries.ts:76-81` being parameterless is also accurate);
`purchase_order_views.py:123-195` (the `_recompute_order_aggregates` body ends at `:196`).

Re-verified from earlier iterations because this revision's normative text depends on them:
`purchase_order_views.py:2885-2898` (comment "A total of exactly 0 is NOT rejected here", guard
`if total < 0`), `:2865-2874` (`if not total_ok` → `invalid_total`), `:2900-2901` (grouped
summation), `:2912-2925` (`order_by("pk")` + `setdefault`, comment naming it oldest-wins),
`:2969-2980` (`len(candidates) != 1` → `line_item_not_found`/`multiple_line_items`, executing before
`:2999`), `:2984-2985` (`line_item.quantity or 0`), `:2999-3009` (non-US-warehouse zero →
`invalid_total`), `:3010-3037` (`max()` + `shipped_at` + `"shipped"` completion), `:3026-3036` and
`:3040-3050` (the seven-field matched and quantity-exceeded payloads that REQ-FORCE-016 now
mirrors), `:2954-2980` (unmatched carries no `line_item_id`), `:155-157` (`sku__isnull=False`),
`:176` (`!= "order_cancelled"`), `:2689` (`.exclude(purchase_status="order_cancelled")`),
`:2765` (`_US_WAREHOUSE_DISTRIBUTORS = {"warehouse_ca", "warehouse_nj"}` — `warehouse_ca` used in
AC-FORCE-006/011 is a real value), `:2790-2801` (~130ms round-trip note), `:2802-2809`
(@MX:WARN lock-free + @MX:REASON), `:247` (`.select_for_update()` coexisting path);
`serializers.py:110-123` (field list, confirmed **no** `purchase_status`);
`models.py:49` (`Order.status`), `:62` (`Order.ready_to_ship`), `:110` (`Index(fields=["name"])`),
`:173` (`LineItem.title`), `:190` (`purchase_status`), `:196` (`confirmed_distributor`), `:222`
(`shipped_at`), `:235` (`unique_together` permitting duplicate SKUs);
`test_spec_015.py:1143-1153` (`<= 6` at `:1147`, `<= 4` at `:1153`), `:746` (dict-equality across
endpoints), `:452` (`test_processing_is_atomic_so_a_mid_run_failure_rolls_everything_back`),
`:1166` (`test_duplicate_order_names_resolve_to_the_lowest_pk_order`);
`test_spec_013.py:383` (`test_bulk_never_calls_recompute_order_aggregates`);
`ResultSection.tsx:8-27` (`ResultRow { key: string; cells: string[] }` + props);
`InboundPage/index.tsx:30-32` (label `Record`), `:176`/`:194`/`:211` (three `ResultSection` call
sites); `DailyReviewTab.tsx:153` (fourth call site);
`index.test.tsx:218-223` (`expect(section.textContent).not.toMatch(/[a-z]+_[a-z_]+/)`);
`router/index.tsx:129-135` (`const { OutboundPage } = await import('@/pages/OutboundPage')`);
`urls.py:70`/`:73`/`:84` (three bulk-before-`<int:pk>` ordering comments).

**No invented names.** Every identifier in spec.md resolves to existing code (verified above). The
two new view names remain confined to plan.md:L48 and are still marked "가칭". spec.md contains no
`file:line` inside any REQ or AC body (mechanically checked) — the iteration-1 D13 fix holds.

**Fidelity to `interview.md`**: all six confirmed decisions still faithfully mapped — Q1 매칭 실패
섹션 한정 → REQ-FORCE-001/019 + Exclusion L600-601; Q2 `line_item_not_found`만 → REQ-FORCE-001 +
Exclusion L594-596; Q3 행별 체크박스 + 일괄 실행 → REQ-FORCE-015/019/022/023; Q4 신규 컬럼·이력 없음
→ Exclusions L590-593; Q5 사용자 명시 지정 → REQ-FORCE-002 + Exclusion L582-583; Q6 수량 한도 유지 →
REQ-FORCE-010 + Exclusion L580-581. F2 is the one operator-facing behaviour the interview does not
cover and the SPEC does not flag.

## Chain-of-Verification Pass

Second-look findings: **three defects surfaced only on the second pass** (F1, F2, F6), two of them
major. What the second pass changed:

1. **First pass read REQ-FORCE-008/009/010/011 as a clean pipeline and moved on**, because each
   requirement is individually coherent and AC-FORCE-007/008/009/010/011 each test a sensible case.
   Re-reading them as a *composition* — specifically, asking what the combined quantity is when
   REQ-FORCE-011 removes every row for a target, and then feeding that value back into
   REQ-FORCE-009's trigger — exposed F1, and exposed that acceptance.md's own LA and LB fixtures
   (L145-151) instantiate the failing case. Lesson applied: the iteration-2 report found N2 by
   composing requirements; the same technique on the *rejection* path rather than the *merge* path
   is what produced F1.
2. **First pass recorded N4 as cleanly resolved** because 설계 결정 N is well argued and its factual
   basis checks out in `OutboundPage/index.tsx`. Re-reading it against AC-FORCE-022's three-row
   fixture — asking what happens to the *third* row rather than the two that were processed —
   exposed F2, and exposed the asymmetry with 설계 결정 L, which does record its accepted cost.
3. **First pass verified traceability arithmetically and stopped there** (24/24 covered, 22/22 used,
   both documents identical). Re-reading each of the five multi-REQ ACs sentence-by-sentence against
   *both* of the REQs it claims — as the brief required — exposed that AC-FORCE-005 asserts
   REQ-FORCE-006 only partially, while acceptance.md asserts it fully. That is F6, and it is
   invisible to any count-based traceability check.

Re-verified end-to-end on this pass, not spot-checked:
- REQ numbering: all 24 IDs enumerated mechanically and counted; base 001–024 traversed
  individually; the "no suffixes" claim at L295-297 verified against the actual ID set.
- AC numbering: all 22 IDs enumerated mechanically; the four two-AC REQs identified independently
  and matched against the document's claim at L571-574.
- Traceability: all 22 `Traces:` clauses extracted from spec.md and all 22 from acceptance.md and
  compared pairwise — identical; reverse direction recomputed for all 24 REQs; the L556-569 table
  independently reproduced; the layer-gate partition verified by arithmetic against both plan.md and
  acceptance.md (16+9−1=24 REQs, 16+7−1=22 ACs).
- Consolidation: all twelve rows of the L23-38 table traced to their claimed destination and the
  destination text read — results tabulated above. Every one of the twelve deleted ACs mapped to a
  surviving criterion.
- Exclusions: all 21 read individually for specificity, not counted; each names a concrete artefact
  (column, table, endpoint shape, permission class, reason code, component signature, route, data
  transform, function name). Count cross-checked against plan.md:L196 and spec-compact.md:L133-156.
- EARS purity: every one of the 24 REQs and 22 ACs read for single-pattern compliance — yielding F4.
- Cross-requirement contradiction sweep: 009 vs 008/011 and vs AC-006/AC-011 (F1); 007 vs 002 and
  the Exclusions (F3); 015 vs 023 (F7); 002 vs 011 (F8); 024 vs its own AC's fixture (F2);
  AC-001's row count vs acceptance.md (F5).
- Cross-document sweep: spec-compact.md verified against spec.md on REQ text, AC summaries, module
  count (5), REQ count (24), AC count (22), the five multi-REQ ACs, and Exclusions (21) — consistent
  throughout, including the propagated F3 quantifier. One trivial divergence not scored: module 4's
  heading includes "인증" in spec-compact.md:L53 but not in spec.md:L381.
- Module count: 5 (spec.md:L299, L315, L337, L381, L409) — within the limit of 5.

## Escalation Report (iteration 3 of 3)

The retry loop is exhausted. Defect history across all three iterations:

| Iteration | Verdict | Score | Critical | Major | Minor | Outcome |
|---|---|---|---|---|---|---|
| 1 | FAIL | 0.62 | 1 (D1) | 6 | 8 | All 15 addressed in v1.0.1 |
| 2 | FAIL | 0.76 | 0 | 5 (N1–N4, N12) | 9 | 13 of 14 addressed in v1.0.2; N7 not |
| 3 | FAIL | 0.80 | 0 | 2 (F1, F2) | 8 | — |

Trajectory: monotonic improvement (0.62 → 0.76 → 0.80), with genuine, source-verified closure of the
iteration-1 critical defect and of the four iteration-2 majors. This is **not** a stagnant SPEC
overall. The residual major count fell from 5 to 2, and F1 is a newly-surfaced composition defect
rather than an unfixed one.

**Stagnant defect (blocking pattern)**: EARS single-pattern purity — D10 (iter 1) → N7 (iter 2) →
F4 (iter 3). Each revision corrected the specific sentences cited and reintroduced the same
construction elsewhere. This is a systematic authoring habit, not a missed fix, and a fourth
correction of individual sentences is unlikely to eliminate it. It is minor in severity and does not
by itself block implementation.

**Fix-induced defect rate**: iteration 1 → 4 new majors; iteration 2 → 1 new major (F2, from the N4
fix) plus 1 composition defect exposed by the consolidation (F1). The rate is falling, but every
revision so far has introduced at least one new major defect, which is the argument for user
intervention rather than a fourth automated round.

**Recommended user intervention**: F1 and F2 are narrow and mechanical — F1 needs one clause added
to REQ-FORCE-009's trigger plus one AC; F2 needs one paragraph in 설계 결정 N plus one clause in
AC-FORCE-022. A human review of those two specific edits, rather than another full re-authoring
pass, is the lowest-risk path. F3–F10 are minor and can be batched into the same edit.

## Recommendation

FAIL. All four must-pass criteria pass, the requirement set is now well-sized (24 REQ / 22 AC / 5
modules / 21 Exclusions), traceability is bidirectionally complete and consistent across both
documents, and the citation evidence is accurate — 35 citations checked against source with zero
substantive errors. The three iteration-2 defects the brief singled out for scrutiny (N1, N2, N3)
are **genuinely and completely fixed, not reworded**, and N3 was confirmed field-for-field against
the real declarations in `outboundApi.ts:37-65` rather than against the document's claim about them.

The SPEC nonetheless cannot be implemented as written. REQ-FORCE-009 mandates a write that two of
the SPEC's own acceptance criteria forbid, on an input the SPEC's own fixtures construct (F1); and
REQ-FORCE-024 mandates a behaviour whose principal operator-facing cost is neither acknowledged nor
tested (F2).

Blocking fixes, in priority order:

1. **(F1, major)** spec.md:L352-357 — require a strictly positive combined quantity in
   REQ-FORCE-009's trigger, or state in REQ-FORCE-008 (L347-350) that a target whose combined
   quantity is zero after REQ-FORCE-011 exclusions is neither evaluated nor reported. Add an AC for
   the all-rows-rejected target covering the `quantity`-`null` and already-complete variants, so the
   `logistics_status = "shipped"` path at `0 ≥ 0` is closed by test.
2. **(F2, major)** spec.md:L280-291 — add an accepted-cost paragraph to 설계 결정 N covering
   unselected eligible rows and force-run `quantity_exceeded` rows, and the recovery path. Extend
   AC-FORCE-022 (L550-552) and acceptance.md:L262-266 to assert the third row's fate.
3. **(F3, F7, F8, minor)** spec.md:L339-345 — enumerate three deviations or scope the claim to the
   judgement rules listed; L383-385 — reconcile REQ-FORCE-015's "entire set" with REQ-FORCE-023;
   L306 — define "structurally malformed" and its boundary with REQ-FORCE-011.
4. **(F6, F9, minor)** spec.md:L466-470 — add REQ-FORCE-006's attribute set to AC-FORCE-005, matching
   acceptance.md:L82-83; L352-357 — add "and shall leave `logistics_status` unchanged below that
   threshold" so F9(c) has a requirement, not only an AC; add a read-only assertion for the
   non-empty candidate lookup.
5. **(F4, minor but stagnant)** Split the grafted unconditional clauses out of REQ-FORCE-001 and
   REQ-FORCE-002 and out of AC-FORCE-021; re-cast AC-FORCE-006's "Given" and AC-FORCE-005's "For"
   openers as `While`; correct the pattern labels on AC-FORCE-013, AC-FORCE-014, AC-FORCE-020 and
   REQ-FORCE-009. Because this defect has survived three rounds of sentence-level correction, a
   one-time pass over **all 46 entries** against the five patterns is more likely to close it than
   fixing the listed instances.
6. **(F5, F10, trivial)** spec.md:L444-448 — "four rows"; plan.md:L60 and spec.md:L132 — correct the
   three off-by-one citation range starts.

Verdict: FAIL
