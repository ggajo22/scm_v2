# SPEC Review Report: SPEC-ORDER-027
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.50

> Reasoning context ignored per M1 Context Isolation. This audit is based solely on
> `.moai/specs/SPEC-ORDER-027/{spec.md,plan.md,acceptance.md}` cross-referenced against
> the actual source files cited therein.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  `REQ-RACKRECV-001` … `REQ-RACKRECV-014` appear at spec.md:48, 51, 54, 57, 60, 63, 68, 71, 74, 79, 82, 85, 88, 91 — 14 requirements, strictly sequential, no gaps, no duplicates, consistent 3-digit zero-padding. Traceability table (spec.md:99-113) lists exactly the same 14 IDs.

- **[PASS] MP-2 EARS format compliance**
  Every requirement is a well-formed normative statement with an explicit subject + `shall`/`shall not` + response. Example spec.md:68-69: *"**While** the computed received count for a group is `0` …, the header **shall** render `입고 0 / 총 {total}권` verbatim"* — valid State-driven. spec.md:48-49 and 51-52 are valid Ubiquitous. Acceptance criteria live in `acceptance.md` as Given/When/Then and are **not** labeled EARS, so the "GWT mislabeled as EARS" failure mode does not apply.
  *Caveat recorded as D6:* 7 of 14 requirements carry a pattern label that contradicts their own sentence structure. This does not break structural conformance but is a real defect (see Defects).

- **[FAIL] MP-3 YAML frontmatter validity**
  spec.md:1-10 contains: `id`, `version`, `status`, **`created`**, `updated`, `author`, `priority`, `issue_number`.
  1. Required field `created_at` is **absent**; the key is spelled `created` (spec.md:5).
  2. Required field `labels` is **entirely absent**.
  Verified against house convention — all four sibling SPECs use both keys:
  `SPEC-ORDER-023` → `created_at: 2026-08-16`, `labels: [order, list, margin, logistics, purchase-status, frontend, backend]`; `SPEC-ORDER-025` → `created_at: 2026-08-17`, `labels: [...]`; `SPEC-ORDER-026` → `created_at: 2026-08-17`, `labels: [...]`; `SPEC-ORDER-014` → `created_at: 2026-08-09`, `labels: [order, logistics, rack-number, summary]`.
  This deviates from both the audit schema and the project's own established convention. **Any missing required field = FAIL.**

- **[N/A] MP-4 Section 22 language neutrality**
  Single-project SPEC scoped to one Django backend + one React/TypeScript frontend. No multi-language tooling surface. Auto-passes.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | 0.50 — multiple requirements require interpretation | The central term "입고" is semantically ambiguous against the existing domain field `LineItem.received_quantity` (D1). REQ-RACKRECV-002 (spec.md:52) mandates handling `null`/`undefined` while REQ-RACKRECV-005 (spec.md:61) covers only `null` (D9). Assumption A2 (spec.md:37) states an equality that the cited code does not hold unconditionally (D7). |
| Completeness | 0.50 | 0.50 — frontmatter missing one or two fields | All narrative sections present (HISTORY spec.md:14-18, Environment :22-30, Assumptions :32-38, Requirements :42-92, Traceability :96-113, Exclusions :117-124 with 6 specific entries, Constraints :128-133, DoD :137-143). But frontmatter is missing `labels` and misnames `created_at` (MP-3), and the SPEC omits any analysis of the partial-receipt mechanism that governs its own subject matter (D1). |
| Testability | 0.50 | 0.50 — several ACs require judgment or fail to discriminate | ACs use exact expected strings (e.g. acceptance.md:45 `입고 3 / 총 8권`) — structurally strong. But AC-RACKRECV-004 has **zero** discriminating power against the mutation it is declared the sole defense for (D2, runtime-verified), and AC-RACKRECV-006 self-declares "잡는 변이: 없음" (acceptance.md:144), violating acceptance.md:7's own [HARD] rule (D10). |
| Traceability | 0.50 | 0.50 — multiple REQs lack ACs | REQ-001…009 each map to at least one AC and every AC traces to an existing REQ (spec.md:100-108) — clean. But 5 of 14 REQs (REQ-010…014, spec.md:109-113) have **no AC**, routed instead to `git diff --stat` "DoD 검증", which is a diff assertion, not a behavioral test. |

---

## Defects Found

### D1. spec.md:123 (+ :32-38, :52) — SPEC is unaware that `LineItem.received_quantity` already exists; partial receipts are silently counted as zero — Severity: **critical**

Exclusion #5 (spec.md:123) reads:

> "`received_quantity` 같은 **신규** 필드를 추가하지 않고"

`received_quantity` is **not a hypothetical new field**. It is an existing model field:

`backend/order/models.py:228`
```python
received_quantity = models.IntegerField(default=0)
```

with the governing comment at models.py:223-227:

> "`UploadWarehouseReceiptView` accumulates uploaded receiving quantities here and only advances logistics_status to "received" once received_quantity reaches `quantity`"

Confirmed in the write path, `backend/order/purchase_order_views.py:2542-2550`:
```python
line_item.received_quantity += received_count
line_item.received_at = timezone.now()
# Advance to "received" only once the cumulative quantity reaches
# `quantity`; below that threshold logistics_status is left
# exactly as it was ...
if line_item.received_quantity >= effective_quantity:
    line_item.logistics_status = "received"
```

**The divergent data shape** (this is the answer to "find a data shape where the client-side sum diverges"):

A LineItem with `quantity = 5`, `received_quantity = 3`, `logistics_status = "shipment_confirmed"`.
- It is **not** excluded by the summary view (purchase_order_views.py:3430 excludes only `"shipped"`).
- Server emits `{quantity: 5, logistics_status: "shipment_confirmed"}` and adds 5 to `total_quantity`.
- Under REQ-RACKRECV-002/003 the header renders **`입고 0 / 총 5권`** — while 3 physical books are sitting on that rack.

Assumptions A1/A2/A3 (spec.md:36-38) do not mention partial receipts at all; A3 only enumerates the four possible `logistics_status` values. **No stated invariant covers this shape.** No AC exercises it. HISTORY (spec.md:18) claims a user decision on "입고 정의" — but the user could not have made an informed choice about a mechanism the SPEC never surfaces, and the domain already stores the exact number the header claims to show.

### D2. acceptance.md:101-117 — AC-RACKRECV-004 passes under BOTH the correct implementation and the mutation it is the sole defense against; M4 is uncovered — Severity: **critical**

acceptance.md:16 and :104 declare AC-RACKRECV-004 the **sole** discriminator for mutation M4 ("`quantity`가 `null`일 때 `?? 0` 가드 누락"). acceptance.md:117 justifies it:

> "`?? 0` 가드 없이 `item.quantity`를 직접 더하는 구현은 `null + 3`이 되어 `NaN`이 헤더에 노출된다(`입고 NaN / 총 3권`)"

**This is factually wrong about JavaScript.** `null` numerically coerces to `0`; only `undefined` yields `NaN`. Runtime verification against the exact AC-004 fixture (acceptance.md:106-111):

```
AC-004 fixture [null, 3]
  correct   -> 3   header: 입고 3 / 총 3권
  M4 (no ??)-> 3   header: 입고 3 / 총 3권
  identical? true

0+null = 0 | Number(null) = 0 | 0+undefined = NaN
```

The declared type is `quantity: number | null` (`frontend/src/services/rackNumberApi.ts:64`) and the server emits JSON `null` verbatim (purchase_order_views.py:3476, models.py:176) — so `undefined` never occurs and `NaN` can never be produced by this fixture.

Full discrimination matrix across every AC fixture in the document:

| fixture | correct | M3 (count rows) | M4 (no `?? 0`) | M3 caught | M4 caught |
|---|---|---|---|---|---|
| AC-001 [recv3, outb5] | 3 | 1 | 3 | yes | **no** |
| AC-002 [recv2, nots1] | 2 | 1 | 2 | yes | **no** |
| AC-003 [nots4, outb2] | 0 | 0 | 0 | no | **no** |
| AC-004 [recvNULL, recv3] | 3 | 2 | 3 | yes | **no** |
| AC-005 [recv2, shipconf3] | 2 | 1 | 2 | yes | **no** |
| AC-007 [recv3] | 3 | 1 | 3 | yes | **no** |

**M4 is caught by zero ACs.** The `?? 0` guard mandated by REQ-RACKRECV-005 (spec.md:60-61) can be omitted entirely and the full suite still passes.

### D3. spec.md:1-10 — YAML frontmatter missing `labels`, misnames `created_at` as `created` — Severity: **major**

See MP-3 above. Fails the must-pass firewall independently of all other findings.

### D4. acceptance.md:15, :62, :180, :187, :189-190 — mutation-coverage table falsely claims AC-RACKRECV-002 is the sole discriminator for M3 — Severity: **major**

acceptance.md:15 marks M3's primary AC as "**AC-RACKRECV-002 (유일)**" and acceptance.md:189 elevates this into a [HARD] protection rule:

> "AC-RACKRECV-002/003/004/005/007 중 하나라도 삭제·약화·픽스처 변경되면 해당 변이가 즉시 미커버가 된다"

Per the matrix in D2, M3 (count-rows instead of sum-quantity) is caught by **AC-001, AC-002, AC-004, AC-005 and AC-007** — five ACs, not one. The [HARD] rule rests on a false premise. Coverage is better than claimed here, but the document's own discrimination analysis — the artifact its quality claim rests on — is demonstrably unreliable, which is what makes D2 dangerous: the same table also asserts a uniqueness that is a *zero*, not a five.

### D5. plan.md:51, acceptance.md:216 — existing-test regression analysis inspects the wrong assertions and misses the `입고` literal collision — Severity: **major**

The new header text introduces the literal `입고`. That exact string is already the rendered label for `logistics_status === "received"`:

`frontend/src/services/purchaseOrderApi.ts:78` → `{ value: 'received', label: '입고' }`

and is asserted with an **exact-match** query in the existing suite:

`frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx:103`
```js
expect(screen.getByText('입고')).toBeInTheDocument() // received label
```

`getByText` throws on multiple matches. Under the header shape specified at plan.md:37 (one span containing `입고 3 / 총 8권`) this survives, but any implementation that splits the label into its own element (`<span>입고</span><span>{n}</span>`) makes `getByText('입고')` match two nodes and throw.

The SPEC never analyzes this. plan.md:51 examines only the `/8/` matcher (test :75) and `:237-255`; acceptance.md:216 singles out `AC-RACKSUM-014/015` (:152-165) and `AC-RACKSUM-013` (:140-150) as "무수정 통과해야 한다" — both trivially unaffected — while the one genuinely collision-prone assertion, `AC-RACKSUM-012` at :103, goes unmentioned. plan.md:51's fallback ("값이 실제로 깨지는 매처가 있으면 … 최소 수정한다") is a catch-all, not analysis.

### D6. spec.md:54, 60, 79, 82, 85, 88, 91 — EARS pattern labels contradict sentence structure on 7 of 14 requirements — Severity: **major**

- REQ-003 (spec.md:54-55), REQ-010 (:79-80), REQ-011 (:82-83), REQ-012 (:85-86), REQ-013 (:88-89), REQ-014 (:91-92) are all labeled **(Unwanted)**. The EARS Unwanted pattern is *"If [undesired condition], then the [system] shall [response]"*. None contains an `If … then` clause; all six are unconditional `shall not` statements — i.e. Ubiquitous negatives.
- REQ-005 (spec.md:60-61) is labeled **(Ubiquitous)** but opens *"**Where** a qualifying line item's `quantity` is `null`…"*. `Where` is the EARS Optional-feature keyword ("Where [feature exists]"); a runtime data condition is State-driven (`While`) or Unwanted (`If … then`). Label and keyword are *both* wrong for the semantics.

Exactly half the requirement set is mislabeled in a document whose section header is literally "Requirements (EARS)" (spec.md:42).

### D7. spec.md:37 (Assumption A2), plan.md:14 — the "byte-identical" equivalence claim is false in two verifiable data shapes — Severity: **major**

plan.md:14 claims the client sum is *"서버의 환불 순액화 결과와 **바이트 단위로 동일**"*. A2 (spec.md:37) claims *"환불 없는 행은 원본 quantity가 그대로 들어가며 두 경우 모두 '순액'과 일치한다"*. The cited code does not support an unconditional equality — the two branches are asymmetric:

`purchase_order_views.py:3446` (total path, **clamped**):
```python
net_qty = max((li.quantity or 0) - li.refunded_qty, 0)
```
`purchase_order_views.py:3476` (line-item path, **verbatim passthrough**):
```python
"quantity": net_qty if li.refunded_qty else li.quantity,
```
with the server's own comment at :3473-3475 stating *"Unrefunded items pass `quantity` through verbatim (NULL stays NULL, per the original contract)"* — which directly contradicts A2's framing that `item.quantity` "이미 서버에서 환불 순액화된 값이다".

Two divergent shapes:
1. **NULL** — gross (`null`) ≠ net (`0`). The equality holds *only after* REQ-RACKRECV-005's `?? 0` is applied; A2 asserts it as a property of the server response, which it is not.
2. **Negative `quantity`** — `LineItem.quantity` is `models.IntegerField(null=True, blank=True)` (models.py:176). Grep for `CheckConstraint|PositiveIntegerField|MinValueValidator` in `backend/order/models.py` returns **no matches** — nothing prevents a negative. For `quantity = -2`, unrefunded, `logistics_status = "received"`: server contributes `max(-2, 0) = 0` to `total_quantity`, but emits `quantity: -2` verbatim, so the client renders **`입고 -2 / 총 0권`**.

A1 is verified correct (every non-`continue` row is appended at :3467 and added to the total at :3466 — identical membership). A2 is the assumption that does not hold as written.

### D8. acceptance.md:171 — asserted server invariant is false — Severity: **minor**

> "서버는 항상 `total_quantity == Σ line_items.quantity`"

Per D7 this is literally false whenever a member row carries `NULL` (or a negative) `quantity`. The AC-007 fixture itself remains valid — it is deliberately synthetic — but the parenthetical justification overstates a guarantee the backend does not make.

### D9. spec.md:52 vs spec.md:61 — `null`/`undefined` inconsistency — Severity: **minor**

REQ-RACKRECV-002 (spec.md:52) mandates *"treating `null`/`undefined` as `0`, per REQ-RACKRECV-005"*, but REQ-RACKRECV-005 (spec.md:61) covers only *"a qualifying line item's `quantity` is `null`"*. The declared type is `number | null` (rackNumberApi.ts:64) — `undefined` is not reachable. This is the drafting slip that most likely produced D2: the author reasoned about `undefined` (which yields `NaN`) while the fixture and the type use `null` (which yields `0`).

### D10. acceptance.md:141-152 — AC-RACKRECV-006 violates the document's own [HARD] rule — Severity: **minor**

acceptance.md:7 states [HARD]: *"이 SPEC의 모든 AC는 자신이 잡는 변이(mutation)를 명시한다 … 통과하는 AC는 가치가 0이다"*. AC-RACKRECV-006 then self-declares at :144: *"잡는 변이: 없음"*. Its stated purpose (:152) is to re-confirm `SummaryTab.test.tsx:237-270`, which already covers collapse/expand and keyboard access. This is duplicated coverage that the document's own rule prices at zero.

### D11. spec.md:109-113 — 5 of 14 requirements have no acceptance criterion — Severity: **minor**

REQ-010 … REQ-014 are routed to `git diff --stat` emptiness checks and "기존 테스트 무수정 재통과". A diff-emptiness assertion verifies that a file was not edited; it does not verify behavior. REQ-RACKRECV-013 (sort order) is mapped to "기존 정렬 관련 테스트" without naming a single test — and no sort-order test exists in `SummaryTab.test.tsx` (the suite has no ordering assertion; group order is only implicitly exercised via `getByText`).

### D12. spec.md:8 — `priority: low` inconsistent with house convention and with the SPEC's own framing — Severity: **minor**

Siblings use capitalized values (`priority: High` in SPEC-ORDER-023/025/026/014). More substantively, a user-requested change to a production header display is classified `low` while the SPEC devotes 14 requirements and 7 ACs to it.

---

## Scope Discipline Assessment (adversarial focus #4)

**Largely clean — this is a genuine strength.** The user asked for one header count change; the SPEC delivers exactly 2 modified files (plan.md:85-92), no backend change, no migration, no new API field, no new interaction control. Modules 2 and 3 (spec.md:66-92) are guardrails that *forbid* work rather than add it, and Exclusions (spec.md:117-124) are six specific, verifiable entries — not vague boilerplate.

Two items do exceed the minimal ask:
- **AC-RACKRECV-006** (D10) — duplicates existing regression coverage while admitting it catches no mutation.
- **REQ-010 … REQ-014** consume 5 of 14 requirement slots on pure non-goals with no ACs (D11). Defensible as scope discipline, but it inflates the requirement count and dilutes traceability.

No scope creep of consequence. This dimension does not contribute to the FAIL.

---

## Citation Verification (adversarial focus #1)

Every `file:line` citation in the SPEC was resolved by reading the target. **All 22 checked citations are accurate** — a notable improvement over the fabricated-citation pattern seen in prior audits.

| Citation | Claim | Result |
|---|---|---|
| `SummaryTab.tsx:96` | header span `총 {group.total_quantity}권` | correct |
| `SummaryTab.tsx:65` | `const [expanded, setExpanded] = useState(false)` | correct |
| `SummaryTab.tsx:17-20` | existing `@MX:NOTE` read-only block | correct |
| `SummaryTab.tsx:122` | `<td …>{item.quantity}</td>` | correct |
| `SummaryTab.tsx:58-134` | `RackNumberSummaryGroupSection` body | correct |
| `SummaryTab.tsx:49`, `:21` | component usage / `SummaryTab` export | correct |
| `rackNumberApi.ts:59-77` | the 3 summary interfaces | correct |
| `rackNumberApi.ts:65` | `logistics_status: string` (not a literal union) | correct — C2 valid |
| `purchaseOrderApi.ts:75-81` | `LOGISTICS_STATUS_OPTIONS` | correct |
| `purchase_order_views.py:3397` / `:3397-3489` | `LineItemRackNumberSummaryView` | correct |
| `purchase_order_views.py:3430` | `.exclude(logistics_status="shipped")` | correct |
| `purchase_order_views.py:3442-3479` | grouping loop | correct |
| `purchase_order_views.py:3446-3454` | `net_qty` + fully-refunded `continue` | correct |
| `purchase_order_views.py:3473-3476` | quantity passthrough | correct (but see D7) |
| `purchase_order_views.py:3481-3487` | named sort + unassigned last | correct |
| `SummaryTab.test.tsx:12-56` | `buildResponse()` | correct |
| `SummaryTab.test.tsx:75` | `getByText(/8/)` | correct |
| `SummaryTab.test.tsx:89-107` | AC-RACKSUM-012 | correct |
| `SummaryTab.test.tsx:140-150` | AC-RACKSUM-013 | correct |
| `SummaryTab.test.tsx:152-165` | AC-RACKSUM-014/015 | correct |
| `SummaryTab.test.tsx:237-270` / `:237-255` | collapse/expand + keyboard | correct |
| `SearchTab.tsx` "count display 0건" (spec.md:27) | grep confirms no count/total display | correct |
| `index.tsx` tab shell unrelated (plan.md:88) | confirmed — tab switcher only | correct |

---

## Chain-of-Verification Pass

Second-look findings — **three defects were missed on the first pass and are included above**:

1. **Re-read every REQ end-to-end (not just the first few).** First pass accepted the `(Unwanted)` labels at face value. Re-reading REQ-003 and REQ-010…014 word-by-word exposed that none contains an `If … then` clause, and REQ-005 uses the `Where` keyword under a `(Ubiquitous)` label → **D6**.
2. **Re-checked REQ sequencing end-to-end**, not spot-checked: all 14 IDs enumerated against both §3 and the §4 traceability table. Confirmed clean — MP-1 PASS stands.
3. **Re-verified traceability for every REQ**, not a sample. This surfaced that REQ-010…014 (5 of 14) have no AC at all and that REQ-013's cited "기존 정렬 관련 테스트" does not exist in the suite → **D11**.
4. **Re-read the Exclusions section for specificity, not just presence.** All six entries are concrete. But re-reading entry #5 word-by-word against `models.py` exposed the word "**신규** 필드" applied to `received_quantity` — a field that already exists → **D1**, the most serious defect in this audit. First pass had skimmed this as boilerplate.
5. **Looked for contradictions *between* requirements, not just within.** REQ-002's `null`/`undefined` vs REQ-005's `null`-only → **D9**; and that in turn prompted the runtime check that produced **D2**.
6. **Did not accept the SPEC's own mutation table as ground truth.** Executed the discrimination matrix independently rather than reading the claims — which is the only reason D2 and D4 were found. Every "유일/단독" claim in acceptance.md was re-derived from the fixtures.

---

## Regression Check

Not applicable — iteration 1. No prior `SPEC-ORDER-027-review-*.md` exists in `.moai/reports/plan-audit/`.

---

## Recommendation

**FAIL.** One must-pass criterion fails (MP-3) and two critical defects invalidate the SPEC's central design decision and its headline quality claim. Required fixes for manager-spec, in priority order:

1. **[D1, critical] Resolve `received_quantity` before anything else.** Read `backend/order/models.py:223-229` and `backend/order/purchase_order_views.py:2542-2550`. The domain already stores a per-line received quantity, and `logistics_status` only advances to `"received"` when it reaches `quantity`. Add a new Assumption (or amend A3) that explicitly states what happens to partially-received rows, and add a requirement + AC for the shape `{quantity: 5, received_quantity: 3, logistics_status: "shipment_confirmed"}`. Then re-surface the definition choice: "입고 = fully-received line quantity" (current SPEC) vs "입고 = `Σ received_quantity`" (matches the field's meaning and what an operator sees on the rack). If the former is kept, spec.md must state the tradeoff explicitly. Correct the false wording at spec.md:123 — `received_quantity` is **not** a 신규 field.

2. **[D2, critical] Repair AC-RACKRECV-004 or M4 stays uncovered.** The mutation `sum + item.quantity` (no `?? 0`) yields exactly `3` on the current fixture — identical to the correct implementation. Either:
   - change the assertion to detect the guard by a route `null` cannot fake — e.g. a group whose **only** `received` row has `quantity: null`, asserting `입고 0 / 총 0권`, still passes under both (`0 + null === 0`), so this does **not** work either; the honest fix is to
   - **drop the `NaN` justification at acceptance.md:117** and re-scope AC-004 to what it actually proves (that a `null` row does not crash rendering and contributes nothing), then state plainly in the mutation table that M4 is **not detectable at the UI layer for `null` input** — because `null` and `0` are arithmetically indistinguishable in JS `+`. If M4 coverage is genuinely required, it must move to a unit test over the extracted `computeReceivedQuantity` helper (plan.md:21-26) asserting the function's return type/value directly, not the rendered header.

3. **[D3, major] Fix the frontmatter (blocks MP-3).** Rename `created` → `created_at` at spec.md:5 and add a `labels` array, matching the sibling convention, e.g. `labels: [order, logistics, rack-number, summary, frontend]`. Consider `priority: Medium` for consistency with sibling capitalization (D12).

4. **[D4, major] Correct the mutation-coverage table.** acceptance.md:15/:62/:180/:187 must stop claiming AC-002 is M3's sole discriminator — M3 is caught by AC-001, 002, 004, 005 and 007. Re-derive every "유일/단독" marker in acceptance.md:177-192 from the fixtures rather than asserting it, and rewrite the [HARD] rule at :189-190 on the corrected basis.

5. **[D5, major] Redo the existing-test regression analysis.** Add explicit treatment of `SummaryTab.test.tsx:103` `getByText('입고')` — the `received` label is the literal string `입고` (purchaseOrderApi.ts:78), the same token the new header introduces. Add a constraint to plan.md §M2 that the header must render `입고 {n} / 총 {t}권` as **one** text node so no element's exact `textContent` equals `입고`, and state that assertion explicitly in the DoD at acceptance.md:216 in place of the currently-cited unaffected tests.

6. **[D6, major] Fix the EARS labels.** Relabel REQ-003 and REQ-010…014 from `(Unwanted)` to `(Ubiquitous)`, or rewrite them into genuine `If … then` form. Relabel REQ-005 and change its keyword from `Where` to `If` (`If a qualifying line item's quantity is null, then the system shall …`) or `While`.

7. **[D7/D8, major/minor] Correct Assumption A2 and the plan.md equivalence argument.** A2 (spec.md:37) must state that `item.quantity` is netted **only for refunded rows** and is passed through verbatim otherwise (quote purchase_order_views.py:3473-3476), so the client-side equality holds **only after** applying `?? 0`. Drop or qualify the "바이트 단위로 동일" claim at plan.md:14 and the "서버는 항상 `total_quantity == Σ line_items.quantity`" claim at acceptance.md:171, noting the unclamped-negative asymmetry between `:3446` (`max(…, 0)`) and `:3476` (verbatim).

8. **[D9, minor]** Align spec.md:52 and spec.md:61 on `null` only, matching the `number | null` type at rackNumberApi.ts:64.

9. **[D10/D11, minor]** Either give AC-RACKRECV-006 a mutation to catch or reclassify it explicitly as a regression guard exempt from acceptance.md:7's [HARD] rule. For REQ-013, either name the actual sort-order test or add one — no ordering assertion currently exists in `SummaryTab.test.tsx`.

Verdict: FAIL
