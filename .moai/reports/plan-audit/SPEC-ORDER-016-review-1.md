# SPEC Review Report: SPEC-ORDER-016
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.62

Reasoning context ignored per M1 Context Isolation. No author reasoning, prior drafts, or
conversation history was consulted. `interview.md` and `research.md` were read only as INPUT
artifacts to test the SPEC's fidelity to them, per the audit scope; their content is not
re-litigated. All verdicts below rest on `spec.md`, `plan.md`, `acceptance.md`,
`spec-compact.md`, and direct inspection of the cited source files.

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency** — Enumerated all REQ definitions mechanically
  (`grep -oE '\*\*REQ-FORCE-[0-9]+[a-z]?\*\*' spec.md | sort | uniq -c`): 33 IDs, each with
  count 1. Base series 001–025 complete with no gaps; 8 alphabetic suffixes (001a, 003a, 007a,
  010a, 010b, 013a, 019a, 020a) exactly matching the declared numbering rule at spec.md:L179-183.
  Zero-padding uniform (3 digits). No duplicates. AC series likewise: 34 IDs, count 1 each.
- **[PASS] MP-2 EARS format compliance** — Every one of the 33 REQ entries and 34 AC entries
  opens with a declared pattern label and uses the corresponding EARS keyword form
  (`While…shall`, `When…shall`, `If…then…shall`, `Where…shall`, bare `The system shall`). No
  informal "should"/"may" appears in normative text (grep for `should |may be|reasonable|
  appropriate|adequate|proper` across all four documents returned only three hits, all on the
  word "sufficient"). Given/When/Then scenarios are correctly quarantined in `acceptance.md`
  rather than mislabeled as EARS in `spec.md`. Purity deviations exist (see D10) but no criterion
  is informal or free-form, so the firewall does not trip.
- **[PASS] MP-3 YAML frontmatter validity** — spec.md:L1-11 carries `id: SPEC-ORDER-016`,
  `version: 1.0.0`, `status: draft`, **`created_at: 2026-08-12` (L5)**, `priority: High`,
  `labels: [order, logistics, outbound, force]`. **No regression on the parent SPEC's defect**:
  SPEC-ORDER-015-review-1.md:L43 recorded `created:` instead of `created_at:` as a critical MP-3
  failure; SPEC-ORDER-016 uses `created_at` and matches the field set of
  `SPEC-ORDER-015/spec.md:L5` and `SPEC-ORDER-014/spec.md:L5` exactly. Secondary documents
  (`plan.md`, `acceptance.md`, `spec-compact.md`) use the project's `id`/`document`/`version`/
  `status`/`updated` convention, identical to SPEC-ORDER-015's secondary documents.
- **[N/A] MP-4 Section 22 language neutrality** — Single-stack project SPEC (Django/Python
  backend + React/TypeScript frontend). No multi-language tooling content. Auto-passes.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | 0.50 — multiple requirements require interpretation; a reasonable engineer might implement them differently than intended | Four independently reachable behaviours are undefined or self-contradictory: `total == 0` (D1, spec.md:L242-246 vs L248-256), server-side enforcement of eligibility (D2, spec.md:L191-194 vs L242-246), target-LineItem ownership (D3, spec.md:L201-208), multi-row aggregation against one target (D4, spec.md:L286-294). REQ-FORCE-022 (L329-331) and REQ-FORCE-021 (L325-327) are mutually unsatisfiable for underscore-bearing SKUs (D7) |
| Completeness | 0.75 | 0.75 — one non-critical area sparse; frontmatter complete | All required sections present: HISTORY (L15-19), 문제 정의/WHY (L23-38), 솔루션 개요·범위 델타/WHAT (L40-73), 설계 결정/HOW (L75-175), 요구사항 (L177-345), ACCEPTANCE CRITERIA (L349-527), Exclusions (L531-565, 15 specific REQ-tied entries), 후속 과제 (L567-584). Docked for the force-response item schema being left undefined (REQ-FORCE-017, L296-299, "an item-level list sufficient to identify…") while the frontend is required to render it (REQ-FORCE-024, L337-339) |
| Testability | 0.60 | between 0.50 and 0.75 anchors — more than "one AC needing minor interpretation" (0.75), fewer than "several… judgment calls" dominating (0.50) | 29 of 34 ACs are binary-testable with concrete field-level outcomes (e.g. AC-FORCE-010a L416-418, AC-FORCE-011a L429-431, AC-FORCE-019 L467-469). Five are not: AC-FORCE-009 (L407-410) is circular ("For an input that… both accept"); AC-FORCE-015 (L450-451) specifies no way to induce mid-run failure; AC-FORCE-017 (L459-461) checks only count==length, leaving the item schema unverified; AC-FORCE-002 (L367-369) compares to an unrecorded "pre-SPEC presentation"; AC-FORCE-008 (L401-403) uses "byte-identical" of ORM rows |
| Traceability | 0.75 | 0.75 — coverage complete but one mapping is indirect | Recomputed end-to-end, not sampled: all 33 REQ IDs appear in at least one `Traces:` clause among the 34 ACs, and every `Traces:` reference resolves to a REQ that exists (spec.md:L505-523 table independently reproduced). Zero orphans, zero uncovered REQs. Docked because AC-FORCE-001 (L358-360) does not test REQ-FORCE-001 — it restates REQ-FORCE-020/AC-FORCE-020 verbatim (D12) — and four `Traces:` clauses disagree between spec.md and acceptance.md (D11) |

## Defects Found

**D1. spec.md:L242-246 (REQ-FORCE-009), L248-256 (REQ-FORCE-010/010a), L267-271 (REQ-FORCE-012) — `total == 0` behaviour is undefined and self-contradictory, and the case is reachable — Severity: critical**

REQ-FORCE-009 asserts that "non-positive amount rejection" is one of the existing outbound
path's rules and shall "apply to the force path identically". The existing path does **not**
reject non-positive amounts. Verified in source:

- `backend/order/purchase_order_views.py:2889-2898` rejects only `total < 0` pre-grouping; the
  comment at `:2885-2888` states explicitly "A total of exactly 0 is NOT rejected here".
- `:2999-3009` judges a zero total **after** matching: non-US-warehouse → `invalid_total`.
- `:3010-3037` for a US-warehouse-confirmed LineItem treats 0 as a completion signal:
  `shipped_quantity = max(shipped_quantity, effective_quantity)`, `shipped_at` stamped,
  `logistics_status = "shipped"`, reported as **matched**.

The case is force-eligible, not hypothetical: the candidate-count branch at `:2969-2980` (which
emits `line_item_not_found`) executes **before** the zero branch at `:2999`, so a row with
`total = 0` whose SKU has no LineItem in the order is reported as `line_item_not_found` and
therefore qualifies under REQ-FORCE-001 (L187-189).

Consequences as written:
- REQ-FORCE-012 (L267-271) covers only "negative, or… could not be genuinely read as a number" —
  it does not cover 0.
- REQ-FORCE-011 (L262-265) does not trigger (`0 + 0` does not exceed `quantity`).
- REQ-FORCE-010 (L248-252) therefore applies: increment by 0 and stamp `shipped_at`, reporting
  the row as matched — whereas the existing path would report `invalid_total` on a
  non-US-warehouse item, and would set `shipped_quantity = quantity` plus
  `logistics_status = "shipped"` on a US-warehouse item.

REQ-FORCE-009's own equivalence claim and AC-FORCE-009 (L407-410) are thus violated by the
SPEC's own other requirements. **Fix**: add an explicit requirement (and AC) defining the force
path's verdict for `total == 0`, and correct REQ-FORCE-009's phrase "non-positive amount
rejection" to match the actual inherited rule (negative and unreadable rejection, with the
post-match zero branch handled explicitly one way or the other).

**D2. spec.md:L191-194 (REQ-FORCE-001a) vs L242-246 (REQ-FORCE-009); acceptance.md:L33-36 — server-side rejection of ineligible rows is unimplementable as specified — Severity: major**

REQ-FORCE-001a requires that the system "shall NOT accept that row as a force outbound target"
for reasons `order_not_found`, `multiple_line_items`, `invalid_total`, `invalid_row`.
AC-FORCE-001a (spec.md:L362-365) and acceptance.md:L33-36 make this explicitly server-side
("서버에 직접 제출된 요청 역시 어떤 LineItem도 변경하지 않는다").

The force request payload (plan.md:L92-93: order identifier, sku, quantity, target LineItem id)
carries no record of the row's earlier classification. `order_not_found` and `invalid_row` are
re-derivable, and `invalid_total` is re-derivable from the amount — but `multiple_line_items`
means the `(order, sku)` pair matched exactly 2+ LineItems (`purchase_order_views.py:2969-2980`),
which the server can only determine by **re-running the `(order, sku)` match** — precisely the
step REQ-FORCE-009 declares bypassed. No requirement specifies this re-match, its query cost, or
its interaction with the "bypass exactly one rule" claim. **Fix**: either specify the
verification mechanism (re-match as a gate, with its own REQ/AC and query budget) or scope
REQ-FORCE-001a's second clause to the rows the server can actually discriminate, and say so.

**D3. spec.md:L201-208 (REQ-FORCE-003/003a), L248-252 (REQ-FORCE-010) — no requirement constrains the designated target to the row's own Order — Severity: major**

Nothing in the SPEC requires the designated LineItem to belong to the Order the row names. The
force path writes to an operator-supplied identifier with no ownership check specified; the
parent SPEC pins the opposite invariant for the normal path
(`test_spec_015.py` `test_a_sku_belonging_to_another_order_is_not_borrowed_across_groups`,
recorded at research.md:207). plan.md:L94-96 lists the validation order as
"(c) 대상 LineItem 존재 확인" — existence only, not ownership. No AC covers cross-order
designation. REQ-FORCE-013a (L277-280) constrains only the *affected* order's composition, which
a cross-order write does not violate.

Related and equally unspecified: the verdict when the designated `line_item_id` does not exist
at all. The Exclusions forbid new reason codes (spec.md:L560-561), and none of the existing five
means "target not designated / target invalid" — so REQ-FORCE-003a's "shall reject that row"
(L205-208) and acceptance.md:L64-66 ("반영되지 않은 것으로 보고된다") have no defined
representation in the three-category response REQ-FORCE-017 mandates. **Fix**: add a requirement
that the designated LineItem must belong to the row's resolved Order, and define which existing
reason code carries a missing/invalid/foreign target (or admit a new code and amend the
Exclusion).

**D4. spec.md:L286-288 (REQ-FORCE-015), L292-294 (REQ-FORCE-016), L242-246 (REQ-FORCE-009) — multi-row aggregation against a single target LineItem is unspecified, re-opening the capacity hole — Severity: major**

The existing path sums rows sharing a key **before** any capacity judgement
(`purchase_order_views.py:2900-2901`, REQ-OUTBOUND-007), which is what makes the limit at
`:3039` sound for a batch. REQ-FORCE-009's enumeration of inherited rules ("quantity limit,
non-positive amount rejection, non-decreasing shipped quantity, threshold status transition,
atomicity") omits grouping/summation, and the force path's natural key is a `line_item_id`, not
`(order, sku)`.

Two selected rows may designate the same target LineItem — reachable through the UI, since two
distinct `line_item_not_found` rows in one order (distinct SKUs, hence distinct selection keys
per 설계 결정 G, L160-168) can both be pointed at the same candidate. If each row is judged
against the pre-request `shipped_quantity`, both pass and jointly push past `quantity`,
defeating REQ-FORCE-011 and the "수량 한도 우회 없음" Exclusion (L533-535). **Fix**: state
whether force rows are aggregated per target LineItem before the capacity check, and add an AC
for two rows designating the same target.

**D5. plan.md:L54-67, spec-compact.md:L106-115 — the file-change plan omits `frontend/src/components/ResultSection.tsx`, the component that actually renders the unmatched section — Severity: major**

The `data-testid="outbound-unmatched"` element that REQ-FORCE-020/021/022 govern is not rendered
by `OutboundPage/index.tsx`; it is produced by the shared `ResultSection` component
(`OutboundPage/index.tsx:147-162` passes it `rows`). That component's row contract is
`export interface ResultRow { key: string; cells: string[] }`
(`frontend/src/components/ResultSection.tsx:8-11`) and it renders each cell as bare text
(`:53-59`). A checkbox and a target picker cannot be expressed through `string[]`.

Implementing REQ-FORCE-020 (L317-319) and REQ-FORCE-021 (L325-327) therefore requires either
changing that shared contract — which has four other call sites
(`frontend/src/pages/InboundPage/index.tsx:176`, `:194`, `:211`,
`frontend/src/pages/PurchaseOrders/tabs/DailyReviewTab.tsx:153`) — or bypassing the component
for the unmatched section, which changes the markup the existing tests assert on. Neither option,
nor the four-call-site regression surface, appears in plan.md, spec-compact.md, or spec.md
(`grep -rn ResultSection .moai/specs/SPEC-ORDER-016/` returns exactly one hit, research.md:447,
and only about the row key). plan.md's "완료 조건" (L166-167) claims the three existing frontend
test files are the regression scope; `InboundPage` and `DailyReviewTab` tests are not listed.
**Fix**: add `ResultSection.tsx` to the change table with an explicit MODIFY-vs-bypass decision
and list the affected consumers and their tests as regression targets.

**D6. acceptance.md:L338-339 and plan.md:L165 — the completion gate requires backend pytest to cover frontend-only requirements — Severity: major**

acceptance.md Quality Gate: "백엔드 pytest: REQ-FORCE-001~025 전 항목(하위 항목
001a/003a/007a/010a/010b/013a/019a 포함)에 대해 최소 1개 이상의 테스트 매핑". plan.md 완료 조건
L165: "`test_spec_016.py`가 REQ-FORCE-001~025 전량에 최소 1개 테스트를 매핑".

REQ-FORCE-020 through REQ-FORCE-025 (spec.md:L315-345) are React rendering, Korean labelling,
control-enablement, selection-reset and router/sidebar requirements. A Django pytest module
cannot exercise them, and plan.md:L30-35 (M5/M6) assigns them to frontend tests. The DoD gate
contradicts the milestone plan and is unsatisfiable as written. The same enumeration also omits
`020a` from its suffix list while claiming to be exhaustive. Related minor inconsistency:
plan.md:L27 assigns "AC-FORCE-003~019" to backend M3, which includes AC-FORCE-016
(spec.md:L455-457, "the system shall issue exactly one processing request") — a client-side
assertion the backend cannot make, also claimed by M6 (plan.md:L33-35). **Fix**: split the
quality gate by layer.

**D7. spec.md:L329-331 (REQ-FORCE-022) vs L226-229 (REQ-FORCE-007) and L325-327 (REQ-FORCE-021) — mutually unsatisfiable requirements, and the REQ is broader than its own AC — Severity: major**

REQ-FORCE-022: "no raw underscore-delimited **code value** shall appear in the rendered text of
that section." REQ-FORCE-021 and REQ-FORCE-007 require the picker (which lives inside that
section) to display each candidate's `sku` and book title. A SKU or title containing an
underscore makes the two requirements jointly unsatisfiable. AC-FORCE-022 (L488-489) narrows the
prohibition to "raw underscore-delimited **status** code", so the REQ and its own AC do not
agree on scope. The underlying test is scoped to the whole section's `textContent`
(`frontend/src/pages/OutboundPage/index.test.tsx:218-223`,
`expect(section.textContent).not.toMatch(/[a-z]+_[a-z_]+/)`), so this is a live implementation
conflict, not a wording nit; plan.md:L135 (R3) flags the risk but no requirement resolves it.
**Fix**: restate REQ-FORCE-022 to cover status/reason code values only, and add a requirement or
Exclusion covering data values that happen to contain underscores.

**D8. spec.md:L296-299 (REQ-FORCE-017) — the only weasel-worded normative statement; the force response item schema is undefined — Severity: minor**

"…each with a count and an item-level list **sufficient** to identify the affected order and
target." "Sufficient" is not measurable, and no requirement or AC pins the item fields.
AC-FORCE-017 (L459-461) verifies only `len(list) == count`. The existing path's items carry
`name`/`sku`/`total`/`line_item_id`/`shipped_quantity`/`quantity`/`logistics_status`
(`purchase_order_views.py:3026-3036`, `:3040-3050`, `:3071-3081`), and the frontend must render
the force result (REQ-FORCE-024, L337-339) — so the schema is an integration contract left
open. (The other two "sufficient" occurrences, L304 and L413, are precise in context and are not
defects.)

**D9. spec.md:L306-309 (REQ-FORCE-019) vs L311-313 (REQ-FORCE-019a) — requirements in tension over the same named contract — Severity: minor**

REQ-FORCE-019 requires the two existing endpoints' "request and response contracts" to be left
unchanged. REQ-FORCE-019a is conditioned on "a new attribute… introduced on the existing
unmatched result item contract" — the change REQ-FORCE-019 forbids. The intended split (backend
response contract vs the frontend `OutboundUnmatchedItem` TypeScript interface, verified at
`frontend/src/services/outboundApi.ts:79-93` and its literal fixtures at
`index.test.tsx:31-38`) is stated only in plan.md:L58, never in spec.md. As written the two
requirements read as contradictory. REQ-FORCE-019a is also HOW-level (a type-system modifier),
verifiable only by `tsc`.

**D10. Multiple locations — EARS single-pattern purity — Severity: minor**

- REQ-FORCE-002 (L196-199): Unwanted trigger followed, after an em dash, by an unconditional
  (Ubiquitous) obligation — two patterns in one criterion.
- REQ-FORCE-023 (L333-335) and AC-FORCE-023 (L491-493): State-Driven trigger followed by an
  unconditional invariant ("shall never include a selected row without a designated target").
- REQ-FORCE-013a (L277-280) and AC-FORCE-013a (L441-443): labelled Unwanted, but the trigger
  "If a force outbound row is processed" is a *desired* event — this is Event-Driven.
- Roughly ten ACs drop the system as grammatical subject: AC-FORCE-008 (L401, "A candidate
  lookup shall…"), AC-FORCE-013 (L437, "No sequence of force outbound requests shall…"),
  AC-FORCE-015 (L450), AC-FORCE-017 (L459), AC-FORCE-018 (L463), AC-FORCE-020a (L479),
  AC-FORCE-022 (L488), AC-FORCE-025 (L499). AC-FORCE-011a (L429-431) is grammatically incoherent
  in its response clause ("any positive requested amount shall… be reported under the
  quantity-exceeded category" — the *row* is reported, not the amount).

None of these is informal enough to trip MP-2, but they are the same authoring habit flagged as
D7 in SPEC-ORDER-015-review-2.md:L48.

**D11. spec.md:L505-523 vs acceptance.md — `Traces:` clauses disagree across documents — Severity: minor**

- AC-FORCE-001: spec.md:L358 traces REQ-FORCE-001; acceptance.md:L21 traces REQ-FORCE-001 **and
  REQ-FORCE-020**.
- AC-FORCE-001a: spec.md:L362 vs acceptance.md:L29 (adds REQ-FORCE-020a).
- AC-FORCE-003: spec.md:L371 vs acceptance.md:L48 (adds REQ-FORCE-010).
- AC-FORCE-012: spec.md:L433 vs acceptance.md:L187 (adds REQ-FORCE-013).
- acceptance.md:L282-289 merges AC-FORCE-020 and AC-FORCE-020a into a single scenario, while
  spec.md defines them as two separate ACs.

The spec.md traceability table is therefore not authoritative; a reader reconciling the two
documents gets different mappings.

**D12. spec.md:L187-189 (REQ-FORCE-001) and L358-360 (AC-FORCE-001) — the AC restates a different requirement instead of testing its own — Severity: minor**

REQ-FORCE-001 defines *eligibility* ("shall treat that row as eligible"). Its sole AC asserts
that the row is presented with a selection control and a target-designation control — which is
verbatim what REQ-FORCE-020 (L317-319) requires and AC-FORCE-020 (L476-477) already verifies.
REQ-FORCE-001 thus has no independent verification, and the backend half of eligibility (on
which D2's server-side clause depends) is untested. acceptance.md:L21 implicitly concedes this by
tracing the scenario to both REQs.

**D13. spec.md:L55-56 vs L82-175 and L341-345 — the document contradicts its own scope disclaimer — Severity: minor**

L55-56 states: "구체적인 참조 구현(기존 함수/뷰의 파일:라인, 테스트가 고정한 불변식, 재사용 대상
패턴)은 `plan.md`와 `research.md`를 참조 — 본 문서는 관찰 가능한 동작(WHAT)과 계약만 규정한다."
설계 결정 A~H (L82-175) then supplies roughly fifteen `file:line` citations, and REQ-FORCE-025
(L344-345) embeds one **inside a normative requirement**. This is the same defect category that
kept SPEC-ORDER-015 in FAIL (SPEC-ORDER-015-review-2.md:L42, iteration-1 D3). Mitigating: every
cited symbol is EXISTING code, so this is **not** the "invents names for code that does not exist
yet" defect — see the positive finding below.

**D14. spec.md:L450-451 (AC-FORCE-015), acceptance.md:L224-230 — no mechanism specified for inducing the mid-run failure — Severity: minor**

"A force outbound request that fails mid-run shall leave no LineItem modified" /
"처리 도중 실패가 발생한다" — neither states how the failure is produced, so the criterion is not
executable as written. A precedent exists (`test_spec_015.py:452`) but the SPEC does not point to
it.

**D15. spec.md:L385-388 (AC-FORCE-005) — tie-break stated as "creation order" where the behaviour to reproduce is lowest-pk — Severity: minor**

The AC says "the older record by creation order". The rule it must mirror is
`.order_by("pk")` + `setdefault` (`purchase_order_views.py:2919-2925`, comment at `:2912-2918`
naming it "oldest-wins"). spec.md:L99-101 correctly says "pk 오름차순"; the AC does not. For
backfilled or imported Orders, pk order and `shopify_created_at` order are not guaranteed to
agree, so the AC could be satisfied while REQ-FORCE-005 is violated.

## Positive findings (recorded with evidence, per M4)

These were checked because the audit brief named them; each passes.

- **spec.md invents no names for code that does not yet exist.** Every identifier in spec.md
  refers to existing symbols verified in source: `_recompute_order_aggregates`
  (`purchase_order_views.py:123`), `Order.name` / `Order.status` / `Order.ready_to_ship`,
  `LineItem.shipped_quantity` / `shipped_at` / `logistics_status` / `purchase_status` / `sku` /
  `quantity` (`models.py:152-235`), `line_item_id` (`purchase_order_views.py:3031`, `:3045`),
  and `frontend/src/pages/OutboundPage/index.tsx:24-28`. The two new view names appear only in
  plan.md:L47 and are explicitly marked "가칭" (tentative) — appropriate for an implementation
  plan.
- **Requirement module count is 5** (spec.md:L185, L210, L240, L290, L315) — within the limit.
- **Exclusions are present and specific**: 15 entries (spec.md:L531-565), each tied to a REQ or
  to a confirmed interview decision; `spec-compact.md:L117-133` reproduces all 15 consistently,
  and plan.md:L170 asserts the same count.
- **Cited `file:line` evidence is accurate.** Twenty-two citations were verified against the real
  files, not trusted: `test_spec_015.py:1147` (`<= 6`) and `:1153` (`<= 4`); `test_spec_015.py:746`
  (dict-equality assertion); `purchase_order_views.py:2919-2925` (order_by("pk") + setdefault);
  `:2689` and `:176` (order_cancelled exclusion); `:155-157` (`sku__isnull=False`);
  `:2985` (`quantity or 0`); `:3039-3051` (quantity_exceeded); `:2954-2980` (unmatched carries no
  `line_item_id`) vs `:3031`/`:3045`; `:2790-2801` (~130ms round-trip note);
  `:2137-2145`+`:2212` (sibling receipt path calls recompute); grep of
  `_recompute_order_aggregates(` confirms **no** call anywhere in `:2810-3101`, validating 설계
  결정 E; `serializers.py:110-123` (no `purchase_status`); `models.py:100-110` (name index) and
  `:235` (`unique_together` allows duplicate SKUs); `test_spec_013.py:390-399`
  (`spy.assert_not_called()` precedent); `urls.py:70`/`:73`/`:84` (bulk-before-pk ordering);
  `SearchTab.tsx:28`/`:64`; `InboundPage/index.tsx:30-32`; `useOutboundQueries.ts:14-16`/`:20-35`/
  `:28`; `outboundApi.test.ts:67` (five reason codes); `index.test.tsx:31-38` and `:218-223`;
  `router/index.tsx:129-135`. **Zero mis-citations found.**
- **Fidelity to `interview.md`** is faithful on all six confirmed decisions (Q1 매칭 실패 섹션
  한정 → REQ-FORCE-002; Q2 `line_item_not_found`만 → REQ-FORCE-001/001a; Q3 행별 체크박스 +
  일괄 실행 → REQ-FORCE-016/020; Q4 신규 컬럼·이력 없음 → Exclusions L541-544; Q5 사용자 명시
  지정 → REQ-FORCE-003/003a; Q6 수량 한도 유지 → REQ-FORCE-011).

## Chain-of-Verification Pass

Second-look findings: **four new defects surfaced on the second pass** (D1, D4, D5, D6), all of
them major or critical. Details of what the second pass changed:

1. **First pass accepted REQ-FORCE-009's rule enumeration at face value.** Re-reading
   `purchase_order_views.py:2865-3037` line by line — rather than trusting the SPEC's own summary
   of the inherited invariants — showed the phrase "non-positive amount rejection" is factually
   wrong about the code it claims to mirror, and that the zero-total branch is reachable through
   the `line_item_not_found` classification. This became D1 (critical). Lesson applied: the
   SPEC's characterisation of existing behaviour must be checked against the code, not just its
   `file:line` pointers (which were all individually correct).
2. **First pass treated the frontend plan as complete because every named file existed.**
   Re-reading `OutboundPage/index.tsx:129-179` showed the unmatched section is delegated to a
   shared component that is absent from every change table. This became D5.
3. **First pass read the acceptance criteria but not the completion gates.** Re-reading
   acceptance.md:L336-347 and plan.md:L162-171 against the module boundaries in spec.md:L315-345
   exposed the backend-covers-frontend contradiction. This became D6.
4. **First pass checked capacity per row.** Re-reading REQ-FORCE-015/016 against the existing
   path's grouping-then-summation step (`purchase_order_views.py:2900-2901`) exposed the
   duplicate-target aggregation gap. This became D4.

Re-verified end-to-end on this pass (not spot-checked):
- REQ numbering: all 33 IDs enumerated mechanically and counted; base 001–025 traversed
  individually for gaps; suffix list cross-checked against the declared rule at L179-183.
- AC numbering: all 34 IDs enumerated mechanically; the extra `011a` confirmed intentional
  (REQ-FORCE-011 is the only REQ with two ACs, spec.md:L522, L526-527).
- Traceability: every one of the 34 `Traces:` clauses read and resolved against the REQ list;
  reverse direction recomputed for all 33 REQs. Result 33/33 covered, 0 dangling — then
  cross-checked against acceptance.md, which surfaced D11.
- Exclusions: all 15 entries read individually for specificity, not merely counted; each names a
  concrete artefact (column, table, endpoint shape, permission class, reason code, route) rather
  than a vague prohibition.
- Contradiction sweep **between** requirements (not only within): 019 vs 019a (D9), 022 vs
  007/021 (D7), 009 vs 010/012 (D1), 001a vs 009 (D2) — four cross-requirement conflicts found,
  none of which a single-requirement read would have caught.
- Cross-document sweep: spec.md ↔ spec-compact.md verified consistent on REQ text, AC counts
  (34), module count (5) and Exclusions (15); the only spec-compact divergence is the inherited
  ResultSection omission (D5).

## Regression Check (Iteration 2+ only)

Not applicable — iteration 1. One targeted regression check was performed against the parent
SPEC's audit history as instructed:

- **SPEC-ORDER-015 D1 (`created` instead of `created_at`, MP-3 critical)** — **NOT regressed**.
  spec.md:L5 reads `created_at: 2026-08-12`.
- **SPEC-ORDER-015 D3 (spec.md carrying HOW-level implementation detail its own disclaimer
  assigns to plan.md)** — **partially regressed**, recorded as D13. The invented-name half of
  that defect did not recur.

## Recommendation

FAIL. All four must-pass criteria pass, but one critical and six major defects make the SPEC
unsafe to implement: three of them (D1, D3, D4) are behaviours an implementer would have to
invent, and each invention risks re-opening an invariant the parent SPEC explicitly closed.

Blocking fixes, in priority order:

1. **(D1, critical)** spec.md:L242-246 — correct REQ-FORCE-009's rule list: the existing path
   rejects *negative and unreadable* amounts, not "non-positive". Then add an explicit
   requirement plus AC for `total == 0` in the force path, covering both branches the existing
   path takes (`purchase_order_views.py:2999-3037`): non-US-warehouse → `invalid_total`;
   US-warehouse-confirmed target → completion. If the intent is to forbid zero-total force rows
   outright, say so in REQ-FORCE-012 and add it to the Exclusions.
2. **(D3, major)** spec.md:L201-208 — add a requirement that the designated LineItem must belong
   to the Order the row names, with a matching AC. Separately, define which of the five existing
   reason codes reports a missing, non-existent, or foreign target; if none fits, amend the
   Exclusion at L560-561 rather than leaving the verdict undefined.
3. **(D4, major)** spec.md:L286-294 — state whether force rows are aggregated per target LineItem
   before the capacity check, and add an AC for two selected rows designating the same target.
4. **(D2, major)** spec.md:L191-194 — specify the mechanism by which the server rejects
   ineligible rows, or scope REQ-FORCE-001a's server clause to the rows the payload permits the
   server to discriminate. Reconcile with REQ-FORCE-009's "bypass exactly one rule" claim.
5. **(D7, major)** spec.md:L329-331 — restrict REQ-FORCE-022 to status/reason code values so it
   stops contradicting REQ-FORCE-007/021, and align AC-FORCE-022 (L488-489) with it.
6. **(D5, major)** plan.md:L54-67 and spec-compact.md:L106-115 — add
   `frontend/src/components/ResultSection.tsx` to the change table with an explicit
   MODIFY-vs-bypass decision, and list `InboundPage/index.tsx` (three call sites),
   `DailyReviewTab.tsx` and their tests as regression targets.
7. **(D6, major)** acceptance.md:L338-339 and plan.md:L165 — split the coverage gate by layer:
   backend pytest for REQ-FORCE-001~019a, frontend tests for REQ-FORCE-019a~025. Add the missing
   `020a` to the suffix enumeration.
8. **(D8, D9, minor but cheap)** spec.md:L296-299 — replace "sufficient to identify" with the
   explicit item field list. spec.md:L306-313 — state in spec.md (not only plan.md) that
   REQ-FORCE-019 governs the backend endpoint contract while REQ-FORCE-019a governs the frontend
   result-item type.
9. **(D10–D15, minor)** Correct the pattern labels on REQ-FORCE-013a/AC-FORCE-013a
   (Unwanted → Event-Driven); split the grafted second clauses out of REQ-FORCE-002 and
   REQ-FORCE-023 into their own Ubiquitous entries; reconcile the four divergent `Traces:`
   clauses between spec.md and acceptance.md; give REQ-FORCE-001 an AC that tests eligibility
   rather than restating AC-FORCE-020; specify the fault-injection mechanism for AC-FORCE-015;
   change AC-FORCE-005's "creation order" to lowest-pk; and either relax the L55-56 disclaimer to
   permit evidence citations in 설계 결정 or move the `file:line` references out of
   REQ-FORCE-025's normative text.

Verdict: FAIL
