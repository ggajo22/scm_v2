# SPEC Review Report: SPEC-ORDER-016
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.76

Reasoning context ignored per M1 Context Isolation. No author reasoning, prior drafts, or
conversation history was consulted. `interview.md` and `research.md` were read only as INPUT
artifacts to test the SPEC's fidelity to them; their content is not re-litigated. All verdicts
rest on `spec.md` v1.0.1, `plan.md` v1.0.1, `acceptance.md` v1.0.1, `spec-compact.md` v1.0.1,
the iteration-1 report, and direct inspection of the cited source files.

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency** — Enumerated mechanically
  (`grep -oE '^\*\*REQ-FORCE-[0-9]+[a-z]?\*\*' spec.md | sort | uniq -c`): **39 IDs, each with
  count 1**. Base series 001–025 complete, no gaps. 14 alphabetic suffixes (001a, 001b, 002a,
  003a, 003b, 007a, 009a, 010a, 010b, 013a, 019a, 020a, 020b, 023a) exactly matching the declared
  numbering rule at spec.md:L291-295 — the rule text and the actual suffix set are now
  character-for-character identical, including the six added in v1.0.1. Zero-padding uniform
  (3 digits). AC series: **40 IDs, count 1 each**, base 001–025 plus 15 suffixes. Both counts
  match the document's own claims (spec.md:L711 "39 REQ → 40 AC", spec-compact.md:L83-85).
- **[PASS] MP-2 EARS format compliance** — All 39 REQ and 40 AC entries carry a declared pattern
  label and use the corresponding keyword form (`While…shall`, `When…shall`, `If…then…shall`,
  `Where…shall`, bare `The system shall`). No informal normative language: grep for
  `should |may be|reasonable|appropriate|adequate|proper` across all four documents returns no
  hit in normative text; the iteration-1 weasel word "sufficient" survives only at spec.md:L439
  ("an authenticated request is sufficient"), where it is a precise predicate, not a quality
  hedge. Given/When/Then remains quarantined in `acceptance.md`. Purity deviations exist (D10-R,
  N6, N7 below) but no criterion is free-form, so the firewall does not trip.
- **[PASS] MP-3 YAML frontmatter validity** — spec.md:L1-11 carries `id: SPEC-ORDER-016`
  (string), `version: 1.0.1` (string), `status: draft` (string), **`created_at: 2026-08-12`
  (L5, correct field name, ISO date)**, `priority: High` (string), `labels: [order, logistics,
  outbound, force]` (array). All six required fields present with correct types. No regression on
  the parent SPEC's `created` vs `created_at` defect. Secondary documents keep the project's
  `id`/`document`/`version`/`status`/`updated` convention and all four were bumped to 1.0.1
  together (spec.md:L3, plan.md:L4, acceptance.md:L4, spec-compact.md:L4) — no stale-version
  drift.
- **[N/A] MP-4 Section 22 language neutrality** — Single-stack SPEC (Django/Python backend +
  React/TypeScript frontend). No multi-language tooling content. Auto-passes.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.65 | between 0.50 and 0.75 — fewer requirements need interpretation than in iteration 1, but four independently reachable behaviours are still undefined or self-contradictory | Improved: the four iteration-1 ambiguities (`total==0`, server-side eligibility, target ownership, multi-row aggregation) are now pinned at spec.md:L190-213, L215-236, L254-270, L238-252. Remaining: AC-FORCE-001 contradicts 설계 결정 J (N1, L505-509 vs L233-235); matched-category granularity under summation undefined (N2, L374-377 vs L428-434); post-execution row state ambiguous (N4, L481-483); unresolvable order identifier undefined (N5, L329-332); "combined quantity" defined only for the 2+ case (N2, L374-377) |
| Completeness | 0.80 | above the 0.75 anchor — all sections present and frontmatter complete, one area still sparse | HISTORY (L15-20), 문제 정의 (L24-39), 솔루션 개요 (L41-60), 범위 델타 (L62-79), 설계 결정 A–M (L81-287), 요구사항 5 modules (L289-492), ACCEPTANCE CRITERIA + traceability table (L496-713), Exclusions **19 specific entries** (L717-768), 후속 과제 4 items (L770-790), 관련 SPEC (L792-806). D8 closed: REQ-FORCE-017 (L428-434) now enumerates the item schema field-by-field. Docked for the response contract still being under-determined (N2/N3) and for undefined edge inputs (N8 malformed row, N9 empty request) |
| Testability | 0.70 | between 0.50 and 0.75 | Genuine gains: AC-FORCE-015 (L619-621) now names the fault-injection mechanism; AC-FORCE-005 (L548-550) says "lower `pk`"; AC-FORCE-009 (L570-574) is a concrete differential test instead of the circular v1.0.0 text; AC-FORCE-017 (L629-633) checks the field set, not just `len == count`. Docked for AC-FORCE-001 (L505-509) being untestable at its declared `[BE]` layer (N1), AC-FORCE-022's unreachable `order_cancelled` example (N11, acceptance.md:L382), and ~13 ACs that restate their REQ verbatim with no added observable detail (N13) |
| Traceability | 0.95 | at the 1.0 anchor but for one content mismatch | Recomputed end-to-end, not sampled. All 40 `Traces:` clauses extracted from spec.md and all 40 from acceptance.md: **identical, 40/40**, closing iteration-1 D11. Every clause resolves to an existing REQ; all 39 REQs covered; REQ-FORCE-011 is the only REQ with two ACs (L690, L593-599), matching the document's claim at L712-713. AC-FORCE-020/020a are now two separate scenarios (acceptance.md:L338-353). The layer gates partition cleanly: backend 24 REQs + frontend 16 REQs − 1 overlap (004) = 39, and 25 + 16 − 1 = 40 ACs; plan.md:L214-225 and acceptance.md:L428-444 agree exactly. Docked 0.05 because AC-FORCE-001's *content* no longer verifies what REQ-FORCE-001 can be tested for at its declared layer (N1) |

## Regression Check — iteration 1 defects D1–D15

Every one of the 15 defects was addressed; **none is stagnant**. Four fixes, however, spawned new
defects, recorded in the next section.

- **D1 (critical, `total == 0` undefined and reachable) — RESOLVED, and the corrected description
  is factually accurate.** Verified against the real source rather than the document's claim:
  - spec.md:L192 "정상 경로는 `total < 0`만 그룹화 이전에 거부" + "주석이 '0은 여기서 거부되지
    않는다'고 명시" → `purchase_order_views.py:2885-2888` reads verbatim *"A total of exactly 0 is
    NOT rejected here"*, and the guard at `:2889` is `if total < 0`. Accurate.
  - spec.md:L193-194 "미국 창고가 아니면 `invalid_total`(`:2999-3009`)" → `:2999` `if total == 0:`,
    `:3000` `if line_item.confirmed_distributor not in _US_WAREHOUSE_DISTRIBUTORS:`, `:3006`
    `"reason": "invalid_total"`. Accurate.
  - spec.md:L195-196 "미국 창고이면 `shipped_quantity = max(...)` + `logistics_status="shipped"`
    (`:3010-3037`)" → `:3015-3017` `max(line_item.shipped_quantity, effective_quantity)`, `:3018`
    `shipped_at`, `:3022-3023` `"shipped"`, `:3026` appended to `matched`. Accurate.
  - spec.md:L200-201 "후보 판정 분기(`:2969-2980`)가 0 분기(`:2999`)보다 **먼저** 실행" → the
    `len(candidates) != 1` branch is at `:2970-2981` and `continue`s; the zero branch at `:2999` is
    below it. Accurate — the reachability claim that made D1 critical is correctly reproduced.
  - REQ-FORCE-009 (L366-372) now reads "per-row rejection of **negative and unreadable** amounts
    before summation", replacing the false "non-positive amount rejection". Correct.
  - Closure is complete on all three fronts: eligibility narrowed (REQ-FORCE-001 L299-301,
    REQ-FORCE-001b L308-311), server verdict fixed (REQ-FORCE-012 L399-403 → `invalid_total`),
    Exclusion added (L725-729), deferral recorded (후속 과제 4, L788-790), backend test mandated
    (plan.md:L31-32, R14 L185, acceptance.md:L238-245 case (d)).
  - Residual nit, not scored: L192's "`total < 0`**만**" (only) is imprecise — unreadable totals
    are also rejected pre-grouping at `:2865-2874`. REQ-FORCE-009 states it correctly, so no
    normative text is affected.
- **D2 (major, server-side rejection unimplementable) — RESOLVED in mechanism, but the fix
  collided with the D12 fix.** 설계 결정 J (L215-236) redefines eligibility as a UI
  responsibility with a correct account of why `multiple_line_items` is not re-derivable;
  REQ-FORCE-001a (L303-306) is rewritten as purely client-side; Exclusion added (L739-742);
  plan.md:L107 and L142-144 agree. → but see **N1**.
- **D3 (major, target ownership unconstrained) — RESOLVED.** REQ-FORCE-003b (L329-332) requires
  the target to exist, to belong to the Order resolved under REQ-FORCE-005, and to clear
  REQ-FORCE-006's exclusions, else HTTP 400 for the whole request. 설계 결정 L (L254-270),
  AC-FORCE-003b (L537-540), acceptance.md:L95-104 (four sub-cases), plan.md R16 (L187), Exclusion
  #14 (L755-757). The missing-target verdict is likewise defined (REQ-FORCE-003a L323-327). One
  residual gap → **N5**.
- **D4 (major, multi-row aggregation) — RESOLVED for the exceeded direction only.** 설계 결정 K
  (L238-252) and REQ-FORCE-009a (L374-377) key summation on the designated `line_item_id`;
  REQ-FORCE-010/011 (L379-397) both consume the combined quantity; AC-FORCE-009a (L576-579) and
  acceptance.md:L178-187 test the individually-fits/jointly-exceeds case. → the matched direction
  is still undefined, **N2**.
- **D5 (major, `ResultSection` omitted) — RESOLVED, and the underlying facts re-verified.**
  設計 결정 M (L272-287) is correct: `ResultSection.tsx:8-11` declares
  `ResultRow { key: string; cells: string[] }`, `:56-59` renders each cell as bare text, and the
  four external call sites exist exactly as cited (`InboundPage/index.tsx:176`, `:194`, `:211`;
  `DailyReviewTab.tsx:153`). Covered in plan.md:L70 (EXISTING row), L77, R13 (L184), M6 (L44-45),
  spec-compact.md:L129-130/L137-138, Exclusion #15 (L758-760), REQ-FORCE-020b (L462-465),
  AC-FORCE-020b (L658-661), acceptance.md:L355-364 and L452-454.
- **D6 (major, backend gate covering frontend REQs) — RESOLVED.** Gates split by layer
  (acceptance.md:L421-444, plan.md:L208-234) and the partition verified arithmetically: backend
  24 REQs, frontend 16 REQs, overlap only REQ-FORCE-004, union = 39 = the full set; AC union
  25 + 16 − 1 = 40. The missing `020a` from the iteration-1 suffix enumeration is gone (the lists
  are now explicit ID enumerations). AC-FORCE-016 is now `[FE]` only (acceptance.md:L287),
  removing the iteration-1 M3-vs-M6 conflict. One item is still mislabelled → **N1**.
- **D7 (major, REQ-FORCE-022 unsatisfiable) — RESOLVED.** REQ-FORCE-022 (L471-473) is scoped to
  `logistics_status` / `purchase_status` / unmatched-reason **values**; AC-FORCE-022 (L668-670)
  matches; Exclusion #16 (L761-764) covers data values containing underscores; R3 (plan.md:L174)
  rewritten. The factual basis is correct: `OutboundPage/index.tsx:157` already renders raw
  `item.sku` inside the `outbound-unmatched` section, so the SPEC's claim that it changes nothing
  is true.
- **D8 (minor, undefined item schema) — RESOLVED as to "sufficient", but the schema chosen
  introduces a new problem.** REQ-FORCE-017 (L428-434) now enumerates fields per category and
  AC-FORCE-017 (L629-633) checks them. → **N3**.
- **D9 (minor, 019 vs 019a) — RESOLVED.** REQ-FORCE-019 (L441-444) says "server-side"; REQ-FORCE-019a
  (L446-450) says "client-side … which REQ-FORCE-019 does not govern because it changes no server
  payload". The split is now stated in spec.md, not only plan.md. The second half of the
  iteration-1 finding stands: REQ-FORCE-019a remains a HOW-level type-system instruction
  verifiable only by `tsc`.
- **D10 (minor, EARS purity) — PARTIALLY RESOLVED.** Done: REQ-FORCE-002/002a and
  REQ-FORCE-023/023a split (L313-317, L475-479); REQ-FORCE-013a and AC-FORCE-013a reclassified
  Unwanted → Event-Driven (L409, L610); the system restored as grammatical subject on
  AC-FORCE-008/013/015/017/018/020a/022/025 (L564, L607, L619, L629, L635, L654, L668, L682);
  AC-FORCE-011a's incoherent response clause rewritten (L597-599). Not done → **N7**.
- **D11 (minor, `Traces:` divergence) — RESOLVED.** All 40 mappings now identical between spec.md
  and acceptance.md (extracted and compared mechanically, not sampled). AC-FORCE-020/020a
  de-merged. A [HARD] synchronisation rule was added at acceptance.md:L14-16.
- **D12 (minor, AC-FORCE-001 restated AC-FORCE-020) — RESOLVED in form; the replacement is
  defective.** → **N1**.
- **D13 (minor, disclaimer vs 설계 결정 citations) — RESOLVED.** The disclaimer at L57-60 now
  explicitly permits `file:line` in 설계 결정 as evidence, and REQ-FORCE-025's citation was moved
  out of the normative sentence into a non-normative blockquote at L490-492. No REQ or AC body
  now contains a `file:line`.
- **D14 (minor, no fault-injection mechanism) — RESOLVED.** AC-FORCE-015 (L619-621) "verified by
  injecting that exception the way the existing outbound atomicity test does";
  acceptance.md:L281-282; plan.md:L133-134 points at `test_spec_015.py:452`, verified to be
  `test_processing_is_atomic_so_a_mid_run_failure_rolls_everything_back`.
- **D15 (minor, "creation order" vs lowest-pk) — RESOLVED.** AC-FORCE-005 (L548-550) says "lower
  `pk`"; acceptance.md:L121-127 deliberately constructs creation order *opposite* to pk order so
  the test cannot pass by accident.

## Defects Found

**N1. spec.md:L505-509 (AC-FORCE-001) vs L233-235 (설계 결정 J) and acceptance.md:L27 — the new
AC-FORCE-001 asserts a behaviour the SPEC elsewhere declares impossible, and is filed under a test
layer that cannot execute it — Severity: major**

AC-FORCE-001 states: "While a row's reason is `line_item_not_found` and its requested quantity is
strictly positive, the system shall accept that row into a force execution and shall apply its
quantity to the designated target — **the same row shape submitted with any other reason code** or
a non-positive quantity **shall not reach that outcome**."

설계 결정 J says the opposite, explicitly: "`multiple_line_items` 행이 서버에 도달하더라도, 그
행이 지정한 대상은 해당 주문에 속하고 제외 조건에 걸리지 않으며 한도 안에 있는 LineItem이어야만
반영된다 — 이는 강제 경로가 원래 하는 일과 정확히 동일하며, 어떤 불변식도 깨지 않는다"
(L233-235). A `multiple_line_items` row with a valid designation *does* reach the applied outcome.

It is also unexecutable at its declared layer. The row's reason code is not in the payload
(plan.md:L106-107: "행마다 주문 식별자, sku, 요청 수량, **대상 LineItem 식별자**를 싣는다. 서버는
그 행의 원래 매칭 실패 사유를 재도출하지 않는다"), and Exclusion #8 (L739-742) forbids the server
from deriving it. `acceptance.md:L27` nevertheless marks AC-FORCE-001 `[BE]`, and both coverage
gates list REQ-FORCE-001 as backend-only (acceptance.md:L428-429, plan.md:L214-216) — so no test at
any layer verifies the reason-code half. `acceptance.md:L31-36` quietly drops that half, testing
only the quantity condition, which makes the two documents disagree on the criterion's content even
though their `Traces:` lines match.

The iteration-1 D12 fix (give REQ-FORCE-001 an AC that tests eligibility) and the D2 fix (move
eligibility to the client) were applied independently and are mutually inconsistent.

**What must change**: pick one. Either scope AC-FORCE-001 to the quantity condition alone and mark
it `[BE]` (matching acceptance.md's actual scenario), or split it into a `[FE]` criterion for the
reason-code half and a `[BE]` criterion for the quantity half — and delete the "any other reason
code … shall not reach that outcome" clause, which no layer can honour.

**N2. spec.md:L374-377 (REQ-FORCE-009a), L379-383 (REQ-FORCE-010), L428-434 (REQ-FORCE-017) — when
two rows are summed onto one target, the matched result's granularity and field values are
undefined — Severity: major**

REQ-FORCE-009a requires two rows designating the same target to be summed and judged "exactly once
for that target". REQ-FORCE-011 says the *exceeded* outcome is "one combined result for that
target". REQ-FORCE-010 says nothing about reporting at all, and REQ-FORCE-017 describes the response
as separating "processed **rows**" into three categories.

So for the success path an implementer must invent: is it one matched item per target or one per
row? If per target, REQ-FORCE-017 mandates `name`, `sku`, `total` on every matched item — but the
two merged rows have *different* SKUs (that is precisely the premise of 설계 결정 K, L244: "서로
다른 두 매칭 실패 행(서로 다른 SKU이므로 선택 키도 다름)") and different totals. Which `sku` and
which `total` the combined item carries is unspecified. The identical question applies to the
combined `quantity_exceeded` item that REQ-FORCE-011 explicitly mandates. No AC covers it:
AC-FORCE-009a (L576-579) tests only that the LineItem is unmodified and that there is one merged
item, never what that item contains; AC-FORCE-010 (L581-583) says "report **the row** as matched",
which presumes per-row reporting and therefore contradicts REQ-FORCE-011's per-target reporting.

Related, same root: REQ-FORCE-010 and REQ-FORCE-011 both trigger on "combined requested quantity
(per REQ-FORCE-009a)", but REQ-FORCE-009a defines that term only for "two or more rows". For a
single-row target the term is undefined, so the two central write requirements have an undefined
trigger in the ordinary case.

**What must change**: state whether the response is keyed per row or per target, define the `sku`
and `total` of a merged item in both categories, define "combined requested quantity" for the
one-row case, and add an AC covering a *successful* two-row merge (the mirror of AC-FORCE-009a).

**N3. spec.md:L428-434 (REQ-FORCE-017) vs plan.md:L135-138 and L69, and the real client types —
the specified item schema is narrower than the types the plan mandates reusing — Severity: major**

REQ-FORCE-017 requires every matched item to carry `name`, `sku`, `total`, `line_item_id` (four
fields) and every quantity-exceeded item those four plus `shipped_quantity`, `quantity` (six).

Verified against source, the existing contract is wider:
- `purchase_order_views.py:3026-3036` — matched items carry `name`, `sku`, `total`,
  `line_item_id`, `shipped_quantity`, `quantity`, `logistics_status` (seven).
- `:3040-3050` — quantity_exceeded items carry those seven with `reason` in place of
  `logistics_status`.
- `frontend/src/services/outboundApi.ts:37-47` — `OutboundMatchedItem` declares
  `shipped_quantity`, `quantity`, `logistics_status` as **required** (non-optional) fields; `:56-65`
  `OutboundQuantityExceededItem` declares `reason: 'quantity_exceeded'` as required.
- `frontend/src/pages/OutboundPage/index.tsx:141-142` and `:176` read
  `item.shipped_quantity`, `item.quantity`, `item.logistics_status` when rendering.

plan.md:L135-138 nevertheless asserts "정상 경로의 항목 구성(`:3026-3036`, `:3040-3050`,
`:2954-2980`)과 **동일한 필드명을 재사용**해 프론트가 결과 렌더링을 재사용할 수 있게 한다", and
plan.md:L69 mandates reusing the `useOutboundMutation` factory
(`useOutboundQueries.ts:20-35`, verified) whose signature is
`(vars: TVars) => Promise<OutboundProcessResponse>` and whose success handler calls
`buildOutboundSummary(result)` (`:14-16`, `:29`). Reusing that factory forces the force response to
type-check as `OutboundProcessResponse`, which a four-field matched item does not.

An implementer following REQ-FORCE-017 literally produces a response the reused client path cannot
consume; one following plan.md produces a response REQ-FORCE-017 under-specifies. REQ-FORCE-019a
guards only the *unmatched* item type, which is the one type that does not have this problem.

**What must change**: either widen REQ-FORCE-017's matched and quantity-exceeded field sets to
match `OutboundMatchedItem` / `OutboundQuantityExceededItem` exactly, or state in spec.md that the
force response is a distinct client type and remove plan.md's field-reuse and factory-reuse claims.

**N4. spec.md:L481-483 (REQ-FORCE-024) and L678-680 (AC-FORCE-024), acceptance.md:L403-410 — the
state of already-forced rows after execution is undefined, and one reading permits the same row to
be force-applied twice — Severity: major**

REQ-FORCE-024: "When a bulk force execution completes, the system shall present the resulting
three-category outcome and shall reset the row selection state, so that a new selection can be made
without reloading the page." AC-FORCE-024 adds "페이지 새로고침 없이 새 선택과 실행을 이어서
수행할 수 있다".

Two readings are equally supported and produce different data outcomes:
1. The force response *replaces* the displayed result. The successfully forced rows vanish from the
   unmatched section and cannot be re-submitted.
2. The force response is displayed *alongside/below* the original result, which still lists the
   rows just processed. Since only the selection is reset — not the rows and not their target
   designations — the operator can immediately re-select the same row, re-designate the same
   target, and apply the same quantity again.

Reading 2 is what "새 선택과 실행을 이어서 수행할 수 있다" most naturally describes, and it means a
10-unit LineItem can be driven to `shipped_quantity = 10` and `logistics_status = "shipped"` by
repeating one 4-unit and one 6-unit force of a row that was physically shipped once. The quantity
limit (REQ-FORCE-011) bounds the damage but does not prevent it, and no requirement marks a row as
already processed, invalidates the cached candidate list (whose `shipped_quantity` is now stale —
plan.md:L153-154 fetches candidates once when the result is finalised), or forbids re-submission.
Nothing in `interview.md` settles this.

**What must change**: state explicitly whether the force result replaces the displayed outbound
result; if it does not, add a requirement that successfully processed rows are removed or marked
non-eligible and that the candidate list is refreshed, with a matching AC.

**N5. spec.md:L329-332 (REQ-FORCE-003b) — behaviour undefined when the row's order identifier
resolves to no Order — Severity: minor**

The gate rejects a target that "does not belong to the Order its order identifier resolves to under
REQ-FORCE-005". If the identifier resolves to nothing, the predicate has no defined truth value.
The natural reading rejects, but an implementation that computes `resolved_order` first and skips
the ownership check when it is `None` would accept the row and write to an arbitrary
`line_item_id` — re-opening exactly the cross-order write D3 closed. 설계 결정 J (L220) notes
`order_not_found` is re-derivable but the server does not derive reason codes, leaving the case
in limbo. AC-FORCE-003b (L537-540) and acceptance.md:L95-104 cover four cases; this is not one of
them.

**What must change**: add "or whose order identifier resolves to no Order" to REQ-FORCE-003b's
condition list, and a fifth case to AC-FORCE-003b.

**N6. spec.md:L366-372 (REQ-FORCE-009) — "bypass exactly one rule" is contradicted by the carve-out
in the same requirement — Severity: minor**

The requirement reads "shall bypass **exactly one** rule … the `(order, sku)` matching step" and
"**Every other rule** of the existing path shall apply to the force path **identically**", then
closes with "The existing path's post-match handling of a zero amount is not inherited and is out
of scope". Zero-handling is a rule of the existing path, is not the matching step, and does not
apply identically — so the requirement's own absolute quantifier is false. 솔루션 개요 item 5
(L51-53) hedges this correctly ("동일하거나 그보다 좁게"), but the normative text does not.
Secondarily, "is out of scope" is a scoping note, not a `shall` clause, sitting inside an EARS
requirement.

**What must change**: replace "exactly one" with an enumeration of the two deviations (matching
step replaced; post-match zero handling not inherited), or move the carve-out sentence out of the
requirement into 설계 결정 I, which already states it.

**N7. spec.md:L399-403 (REQ-FORCE-012) and L360-362 (REQ-FORCE-008) — the D10 purity fix was applied
inconsistently — Severity: minor**

REQ-FORCE-012 is labelled Unwanted and grafts an unconditional obligation onto the conditional
trigger: "…then the system shall reject that row … **and the system shall NOT apply the existing
path's US-warehouse zero-completion behavior to any force outbound row**". The second clause is
Ubiquitous — it holds for every force row, not only for the rows the `If` selects. REQ-FORCE-008
does the same, packing read-only-ness and deterministic ordering into one Ubiquitous statement.
This is the identical construction that REQ-FORCE-002/002a and REQ-FORCE-023/023a were split apart
to remove, so the fix stops one requirement short. AC-FORCE-001 (L505-509) newly introduces the
pattern via its em-dash clause, and AC-FORCE-009 (L570-574) opens with "Given …" rather than any of
the five EARS openings while being labelled Ubiquitous.

**What must change**: split the second clause of REQ-FORCE-012 into its own Ubiquitous entry (as
was done for 002a/023a), split REQ-FORCE-008's ordering obligation out, and re-cast AC-FORCE-009's
precondition as a `While …` State-Driven opener.

**N8. spec.md:L399-403 (REQ-FORCE-012), L428-434 (REQ-FORCE-017), plan.md:L116-117 — no requirement
defines the verdict for a structurally malformed force row — Severity: minor**

plan.md's validation order lists "(a) 행 형태 검증" as the first per-row step, but no REQ or AC
assigns it an outcome. The only unmatched reason the force path can ever emit is `invalid_total`
(REQ-FORCE-012), and Exclusion #14 (L755-757) forbids new reason codes, so `invalid_row` — one of
the five existing codes, and the code the normal path uses for exactly this case — is never
produced by any force requirement. An implementer must choose between emitting `invalid_row`
(unstated), folding it into `invalid_total` (unstated), and adding it to the HTTP 400 gate
(unstated).

**What must change**: state which of the three the force path does, in REQ-FORCE-012 or in the
REQ-FORCE-003a/003b gate, with an AC.

**N9. plan.md:L87-89 and spec.md:L336-339 (REQ-FORCE-004), L424-426 (REQ-FORCE-016) — the empty
request case is left to the implementer's discretion — Severity: minor**

plan.md states the empty candidate-lookup list should be handled "거부하거나 빈 결과를 반환하되,
**어느 쪽이든** 쓰기는 발생하지 않는다" — an explicit either/or, i.e. an undecided observable API
behaviour recorded in a plan rather than settled in the SPEC. REQ-FORCE-004's "regardless of how
many order identifiers the set contains" does not cover zero. The same hole exists for a force
request with an empty row list; REQ-FORCE-023 makes it unreachable from the UI but not from the
API, which REQ-FORCE-001a and AC-FORCE-003a both treat as a directly reachable surface.

**What must change**: pick one behaviour for each endpoint and state it in spec.md.

**N10. spec.md:L779-784 (후속 과제 2) and plan.md:L179 (R8) — the stale-read risk analysis was not
updated for 설계 결정 L and now understates the failure mode — Severity: minor**

Both say a stale `shipped_quantity` "수량 한도 검증은 실행 시점 값 기준으로 수행되므로 데이터
파손이 아닌 `quantity_exceeded` 보고로 귀결된다 — 즉 안전 실패". That was true in v1.0.0. After
설계 결정 L, a target that became `order_cancelled` or lost its `sku` between candidate lookup and
execution no longer degrades to `quantity_exceeded`; it fails the pre-write gate and **rejects the
entire batch with HTTP 400** (L254-258), discarding every other valid row in the request. For the
일괄 실행 unit that Q3 of `interview.md` confirmed, that is a materially different operator
experience from "안전 실패".

**What must change**: update 후속 과제 2 and R8 to state both failure modes, and note the
batch-wide blast radius of a single staled target.

**N11. spec.md:L471-473 (REQ-FORCE-022) vs L347-353 (REQ-FORCE-006/007); acceptance.md:L382 —
REQ-FORCE-022 mandates labelling a value the SPEC guarantees never appears — Severity: minor**

REQ-FORCE-022 requires "every `logistics_status`, **`purchase_status`**, and unmatched-reason value
shown anywhere in the unmatched section" to be rendered as a Korean label. But REQ-FORCE-006
excludes `order_cancelled` items from the candidate list entirely and REQ-FORCE-007's returned
attribute set (identifier, title, `sku`, `quantity`, `shipped_quantity`, `logistics_status`) does
not include `purchase_status` — so no `purchase_status` value can reach the section. AC-FORCE-022's
example list (acceptance.md:L382) uses `order_cancelled` as a code that must not appear as text,
which is therefore an unreachable test condition. plan.md:L72 correspondingly instructs building a
`purchase_status` → Korean label map that nothing will consume.

**What must change**: drop `purchase_status` from REQ-FORCE-022, AC-FORCE-022's example, and
plan.md's label-map scope — or state where a `purchase_status` value is intended to surface.

**N12. Whole-document — the requirement set is over-specified: 39 REQs / 40 ACs for two endpoints
and one UI section, with substantial three-way restatement — Severity: major (structural)**

This was asked for explicitly, and the evidence supports it.

*Requirements that restate one another.* REQ-FORCE-020a (L458-460) already says an ineligible row
renders no selection control, no target-designation control, and is not included in a force
execution — where "eligible" is defined by REQ-FORCE-001. REQ-FORCE-001a (L303-306) is the same
rule restricted to four reason codes; REQ-FORCE-001b (L308-311) is the same rule restricted to
non-positive quantities. Both are strict subsets of 020a. Their three ACs (L511-518, L654-656) and
three acceptance.md scenarios (L38-54, L346-353) triple-test one behaviour. Likewise REQ-FORCE-003
(L319-321, "shall require every row … to carry an explicitly designated target") carries no
testable content beyond REQ-FORCE-003a (L323-327) — and its own AC-FORCE-003 (L528-530) tests a
*different* proposition ("apply the row against exactly that LineItem and no other"), which is what
REQ-FORCE-003 should have said.

*Requirements that restate Exclusions.* REQ-FORCE-002a (L316-317), REQ-FORCE-014 (L414-416),
REQ-FORCE-020b's test-hook clause (L462-465) and REQ-FORCE-025 (L485-488) are "nothing changes"
statements that duplicate Exclusions #9, #11, #15 and #17 (L743-744, L748-750, L758-760, L765).
AC-FORCE-002a's operative content is "the existing tests covering that section shall pass
unmodified" (L525-526) — a regression instruction, not an acceptance criterion.

*Requirements that belong in plan.md.* REQ-FORCE-019a (L446-450) is a TypeScript optionality
instruction, already stated verbatim at plan.md:L68 and as R4 (plan.md:L175). REQ-FORCE-020b's
"shall keep the existing test hook" mandates a `data-testid` attribute.

*ACs that restate their REQ with no added observable detail.* Comparing side by side:
AC-FORCE-020 (L650-652) vs REQ-FORCE-020 (L454-456); AC-FORCE-023 (L672-673) vs REQ-FORCE-023
(L475-476); AC-FORCE-023a (L675-676) vs REQ-FORCE-023a (L478-479); AC-FORCE-006 (L552-554) vs
REQ-FORCE-006 (L347-349); AC-FORCE-007 (L556-558) vs REQ-FORCE-007 (L351-353); AC-FORCE-010b
(L589-591) vs REQ-FORCE-010b (L389-391); AC-FORCE-022 (L668-670) vs REQ-FORCE-022 (L471-473);
AC-FORCE-002 (L520-522) vs REQ-FORCE-002 (L313-314); AC-FORCE-011 (L593-595) vs REQ-FORCE-011
(L393-397); AC-FORCE-013 (L607-608) vs REQ-FORCE-013 (L405-407); AC-FORCE-021 (L663-666) vs
REQ-FORCE-021 (L467-469); AC-FORCE-016 (L625-627) vs REQ-FORCE-016 (L424-426). Twelve of forty are
paraphrase-only. Because `acceptance.md` supplies the concrete Given/When/Then with real fixture
data for every one of them, the spec.md AC layer adds little beyond a second place to fall out of
sync.

The cost is not theoretical. Every rule now lives in up to four places (REQ, spec.md AC,
acceptance.md scenario, spec-compact.md summary), plus Exclusions and plan.md — and this iteration
found three cases where a v1.0.1 edit reached some copies but not others: N1 (spec.md AC vs
acceptance.md scenario), N10 (설계 결정 L vs 후속 과제 2 and R8), N2 (REQ-FORCE-011's per-target
reporting vs AC-FORCE-010's per-row reporting). The `[HARD]` synchronisation rule the authors added
at acceptance.md:L14-16 is an acknowledgement of this fragility rather than a fix for it.

**What must change**: fold REQ-FORCE-001a/001b into REQ-FORCE-020a; fold REQ-FORCE-003 into
REQ-FORCE-003a (and re-home AC-FORCE-003's proposition under it); move REQ-FORCE-019a and
REQ-FORCE-020b's test-hook clause to plan.md; and delete the spec.md ACs that only paraphrase their
REQ, letting the traceability table point at `acceptance.md` scenario IDs directly. A target near
28–30 REQs is achievable without dropping any confirmed behaviour.

**N13. plan.md:L69 — imprecise citation path — Severity: minor**

The sentence cites "`useRackNumberQueries.ts:76-81` / `useOrders.ts:11` 관례" in a row whose subject
is `frontend/src/hooks/useOutboundQueries.ts`, implying `frontend/src/hooks/useOrders.ts`. No such
file exists; the file is `frontend/src/features/order/hooks/useOrders.ts`, whose line 11 is indeed
`queryKey: [...ORDERS_QUERY_KEY, params]`, matching the claim. Also note the other cited example
(`useRackNumberQueries.ts:76-81`) uses `queryKey: ['rack-number-summary']` with **no** parameter,
so it does not illustrate the "문자열 리터럴 배열 + 파라미터" convention the sentence attributes to
it.

**N14. spec.md:L260-265 (설계 결정 L) — the all-or-nothing rejection is justified circularly and is
not traceable to a confirmed decision — Severity: minor**

The stated reason for rejecting a whole batch rather than degrading one row is "이 SPEC의
Exclusions는 신규 매칭 실패 사유 코드 도입을 금지하는데, 기존 5종 중 … 코드가 없다". The
Exclusion (L755-757) is authored by this SPEC, not imposed by `interview.md`, and it is amended in
the same breath to accommodate the choice. A self-imposed documentation constraint is being used to
justify a user-facing behaviour — an operator loses an entire 6-row batch because one target went
stale — that `interview.md` never contemplated (Q3 confirmed 일괄 실행, nothing about partial
failure). The second reason given (the picker only offers valid targets, so an invalid target
signals client/server desync) is sound on its own and should carry the decision; the first should
not.

## Chain-of-Verification Pass

Second-look findings: **five defects surfaced only on the second pass** (N1, N2, N3, N4, N12), four
of them major. What the second pass changed:

1. **First pass accepted the D2 and D12 fixes independently.** Reading 설계 결정 J and AC-FORCE-001
   in the same sitting — rather than checking each against its own iteration-1 defect — exposed that
   the two fixes assert opposite things about whether a non-`line_item_not_found` row can be
   applied. This became N1. Lesson: when several fixes land in one revision, cross-check the fixes
   against *each other*, not only against the defects they answer.
2. **First pass accepted "D8 resolved" because a field list now exists.** Opening
   `outboundApi.ts:37-65` and `OutboundPage/index.tsx:141-176` showed the specified list is a
   strict subset of the required client types, and that plan.md's factory-reuse instruction
   (`useOutboundQueries.ts:20-35`, verified) forces the wider type. This became N3 — a defect the
   D8 fix created.
3. **First pass checked the D4 fix only in the direction its AC tests.** AC-FORCE-009a covers the
   exceeded merge. Re-reading REQ-FORCE-010/011/017 against 설계 결정 K's premise (merged rows have
   different SKUs) exposed that the *successful* merge has no defined item shape. This became N2.
4. **First pass read REQ-FORCE-024 as a UI-reset requirement and moved on.** Re-reading it together
   with plan.md:L153-154's one-shot candidate fetch and AC-FORCE-024's "새 선택과 실행을 이어서"
   exposed the repeat-application reading. This became N4.
5. **First pass counted requirements without comparing them.** Reading REQ-FORCE-001a, 001b and
   020a consecutively — and the twelve paraphrase-only ACs side by side with their REQs — produced
   the bloat finding, N12, and explained the mechanism behind N1, N2 and N10.

Re-verified end-to-end on this pass, not spot-checked:
- REQ numbering: all 39 IDs enumerated mechanically and counted; base 001–025 traversed
  individually; the 14-suffix list at L291-295 compared element-by-element against the actual set.
- AC numbering: all 40 IDs enumerated mechanically; the single 2-AC REQ (011) confirmed.
- Traceability: all 40 `Traces:` clauses extracted from spec.md and all 40 from acceptance.md and
  compared pairwise — identical; reverse direction recomputed for all 39 REQs (0 uncovered, 0
  dangling); the L688-709 table independently reproduced; the layer-gate partition verified by
  arithmetic against both plan.md and acceptance.md.
- Exclusions: all 19 read individually for specificity (not counted); each names a concrete
  artefact — column, table, endpoint shape, permission class, reason code, component signature,
  route, data-value transform. Count cross-checked against plan.md:L233 ("19개") and
  spec-compact.md:L145-164 (19 bullets). Consistent.
- EARS pattern purity: every one of the 39 REQs and 40 ACs read for single-pattern compliance, not
  sampled — yielding N6, N7 and the AC-FORCE-009 opener.
- Cross-requirement contradiction sweep: 009 vs its own carve-out (N6), AC-001 vs 결정 J (N1),
  017 vs client types (N3), 011 vs AC-010 (N2), 022 vs 006/007 (N11), 후속 과제 2 vs 결정 L (N10).
- Invented-name check: every identifier in spec.md resolved to existing code —
  `_US_WAREHOUSE_DISTRIBUTORS` / `warehouse_ca` (`purchase_order_views.py:2765`), `LineItem.title`
  / `sku` / `quantity` / `confirmed_distributor` (`models.py:173`, `:175`, `:176`, `:196`),
  `line_item_id` (`:3031`, `:3045`), `_recompute_order_aggregates`, `data-testid="outbound-unmatched"`
  (`OutboundPage/index.tsx:148`), `export function OutboundPage` (`:29`). The two new view names
  appear only in plan.md:L57 and remain marked "가칭". **No invented names.**
- Citation sampling (concentrated on v1.0.1 additions, per the brief — 24 checked, all against the
  real files): `purchase_order_views.py:2885-2898`, `:2999-3009`, `:3010-3037`, `:2969-2980`,
  `:2900-2901`, `:2316-2319`, `:2416-2420`, `:2526-2530`, `:2671-2728`, `:247`, `:2802-2809`;
  `models.py:235`; `test_spec_013.py:383-399`, `:842-851`; `test_spec_015.py:452`, `:1166-1199`;
  `ResultSection.tsx:8-27`; `InboundPage/index.tsx:30-32`, `:176`/`:194`/`:211`;
  `DailyReviewTab.tsx:153`; `SearchTab.tsx:243-249`; `Sidebar.test.tsx:173-194`;
  `types/order.ts:112-136` (confirmed no `purchase_status`); `useRackNumberQueries.ts:76-81`;
  `outboundApi.test.ts:33-36`, `:67`; `index.test.tsx:31-38`, `:218-223`, `:76/81/154/268/317`;
  `router/index.tsx:129-135`; `OutboundPage/index.tsx:24-28`, `:154`. **All content claims accurate;
  one path imprecision (N13).**
- `interview.md` fidelity: all six confirmed decisions still faithfully mapped (Q1 → 002/002a,
  Q2 → 001/001a, Q3 → 016/020, Q4 → Exclusions #5/#6, Q5 → 003/003a, Q6 → 011). The v1.0.1
  additions narrow scope rather than widen it, which is the safe direction; the one behaviour the
  interview does not cover and that materially affects the operator (batch-wide 400) is recorded
  as N14.

## Recommendation

FAIL. Every iteration-1 defect was genuinely addressed — the critical D1 correction was verified
line-by-line against `purchase_order_views.py` and is factually accurate, not merely reworded, and
D5/D6/D7/D11/D14/D15 are cleanly and completely closed. Traceability is now essentially perfect.

But four of the fixes created new major defects (N1 from D2+D12, N2 from D4, N3 from D8, and the
untouched N4), and the SPEC remains a document an implementer cannot execute without inventing
behaviour: the shape of a merged result item, the field set of the force response, whether a
processed row can be forced again, and which of two contradictory statements about
non-`line_item_not_found` rows to honour.

Blocking fixes, in priority order:

1. **(N1, major)** spec.md:L505-509 — delete or re-layer AC-FORCE-001's "any other reason code …
   shall not reach that outcome" clause so it stops contradicting 설계 결정 J (L233-235), and
   correct its `[BE]` label at acceptance.md:L27 to match what the payload actually permits testing.
2. **(N3, major)** spec.md:L428-434 — reconcile REQ-FORCE-017's item schema with
   `OutboundMatchedItem` / `OutboundQuantityExceededItem` (`outboundApi.ts:37-65`), or declare the
   force response a distinct client type and strike plan.md:L69 and L135-138's reuse claims.
3. **(N2, major)** spec.md:L374-383 and L428-434 — state whether the response is keyed per row or
   per target, define the `sku` and `total` of a merged item in both the matched and the
   quantity-exceeded categories, define "combined requested quantity" for the single-row case, and
   add an AC for a successful two-row merge.
4. **(N4, major)** spec.md:L481-483 — state whether the force result replaces the displayed
   outbound result; if not, require successfully processed rows to become non-eligible and the
   candidate list to be refreshed, with a matching AC.
5. **(N12, major/structural)** Reduce the requirement set. Fold 001a/001b into 020a, fold 003 into
   003a, move 019a and 020b's test-hook clause to plan.md, and delete the twelve spec.md ACs that
   only paraphrase their REQ. This is the change most likely to prevent a fourth round of
   fix-induced defects.
6. **(N5, N8, N9, minor)** spec.md:L329-332 — add "resolves to no Order" to the gate condition and
   a fifth AC-FORCE-003b case; define the verdict for a structurally malformed force row; settle
   the empty-request behaviour that plan.md:L87-89 currently leaves to the implementer.
7. **(N6, N7, N11, minor)** spec.md:L366-372 — replace "exactly one rule" with the two actual
   deviations; split REQ-FORCE-012's and REQ-FORCE-008's grafted unconditional clauses out as
   Ubiquitous entries and re-cast AC-FORCE-009's "Given" opener; drop `purchase_status` from
   REQ-FORCE-022, AC-FORCE-022 and plan.md:L72.
8. **(N10, N13, N14, minor)** Update 후속 과제 2 and plan.md R8 for 결정 L's batch-wide rejection
   mode; fix the `useOrders.ts` path at plan.md:L69; and re-base 설계 결정 L's justification on the
   client-desync argument rather than on this SPEC's own Exclusion.

Verdict: FAIL
