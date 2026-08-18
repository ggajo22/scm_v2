# SPEC Review Report: SPEC-ORDER-027
Iteration: 2/3
Verdict: PASS
Overall Score: 0.75

> Reasoning context ignored per M1 Context Isolation. The two governing decisions supplied by the
> coordinator (received_quantity-based definition; per-line `Σ min(received_quantity, net_qty)` clamp)
> are treated as fixed inputs — this audit tests whether the SPEC implements them correctly and
> completely, not whether they are the right decisions.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**
  `REQ-RACKRECV-001` … `REQ-RACKRECV-018` at spec.md:52, 55, 58, 61, 64, 67, 72, 77, 80, 83, 86, 89, 94, 97, 100, 103, 106, 109 — 18 sequential, no gaps, no duplicates, consistent 3-digit padding. `AC-RACKRECV-001` … `011` likewise sequential (acceptance.md:40, 55, 70, 85, 106, 121, 138, 153, 168, 183, 198).

- **[PASS] MP-2 EARS format compliance**
  All 18 requirements verified individually against the five patterns. The iteration-1 D6 defect is genuinely repaired:
  - REQ-RACKRECV-003 (spec.md:58-59) is now a **real Unwanted**: *"**If** 어떤 라인아이템의 `received_quantity`가 그 `net_qty`를 초과하면 …, **then** the system **shall** 그 품목의 기여분을 `net_qty`로 클램프하고, **shall not** …"* — genuine `If … then` structure.
  - REQ-RACKRECV-005 (spec.md:64-65) relabeled `(State-Driven)` with a correct `While` keyword, replacing v0.1.0's `Where`-under-`Ubiquitous` mismatch.
  - The six unconditional `shall not` requirements (REQ-013…018, spec.md:94-110) are now correctly labeled `(Ubiquitous)` instead of `(Unwanted)`.
  - State-driven REQ-009 (`While … received_quantity가 0이면`) and REQ-011 verified.

- **[PASS] MP-3 YAML frontmatter validity**
  spec.md:1-11 — all six required fields present with correct types: `id: SPEC-ORDER-027`, `version: 0.2.0`, `status: draft`, **`created_at: 2026-08-18`** (renamed from `created`), `priority: Medium` (capitalized to match siblings), **`labels: [order, logistics, rack-number, summary, frontend, backend]`** (added). Iteration-1 D3/MP-3 failure is resolved.

- **[N/A] MP-4 Section 22 language neutrality**
  Single-project SPEC (Django backend + React/TypeScript frontend). No multi-language tooling surface.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements | Requirements are individually unambiguous; the clamp rule is stated as a cause-agnostic condition (spec.md:58) rather than tied to one scenario, which is correct drafting. Deduction: A2/A3 (spec.md:40-41) enumerate only the refund cause for `received_quantity > net_qty` and miss that `LineItem.quantity` is itself mutable via Shopify re-sync (N4). |
| Completeness | 0.75 | 0.75 — one non-critical item sparse | All sections present; frontmatter complete; 7 specific exclusions (spec.md:143-149); constraints C1/C2; DoD split into 신규/회귀/범위/문서. Deductions: REQ-006 restates a model fact rather than a behavior (N7); the MX gate at plan.md:168 is unactionable (N5). |
| Testability | 0.75 | 0.75 — one AC not precisely binary-testable | All 11 ACs have concrete fixtures. I recomputed every backend AC's expected values independently — **all six match the document exactly**. All 7 declared mutations verified genuinely detected. No AC passes under both correct and mutated implementations (the iteration-1 killer). Deduction: three discriminator-labeling errors (N1/N2/N3) and one uncovered mutation class (N9). |
| Traceability | 0.75 | 0.75 — one REQ uncovered / indirect mapping | Every AC traces to an existing REQ. REQ-001…012 (behavioral) all have ACs except 006 and 007; REQ-007 is legitimately compile-time-verified. REQ-013…018 are non-goals with diff-based DoD, now governed by an honest [HARD] disclosure rule (spec.md:137). 8 of 18 REQs are AC-less (N7). |

---

## Regression Check (iteration 1 defects)

| # | Iteration-1 defect | Status | Evidence |
|---|---|---|---|
| D1 | critical — unaware `LineItem.received_quantity` exists; partial receipts counted as 0 | **RESOLVED** | Architecture replaced. spec.md:32 cites `models.py:228` as an **existing** column; REQ-004 (spec.md:61-62) mandates status-independent aggregation and names the partial-receipt defect explicitly. AC-001 pins it with `received_quantity=3, logistics_status="shipment_confirmed"`. |
| D2 | critical — AC-004 could not distinguish correct from mutated (`0 + null === 0`) | **RESOLVED** | Frontend arithmetic eliminated entirely (REQ-008, spec.md:77-78; plan.md:64). The null-guard mutation class no longer exists. All replacement AC arithmetic independently recomputed and correct. |
| D3 | major — MP-3 frontmatter | **RESOLVED** | See MP-3 above. |
| D4 | major — false "sole discriminator" claims | **PARTIALLY RESOLVED — recurs** | M2/M3/M4/M6/M7 labels are now accurate and I verified them. But M1's "단독" claim is still false (see N1). Errs safe this time (over-coverage), unlike v0.1.0's under-coverage. |
| D5 | major — `입고` literal collision with `SummaryTab.test.tsx:103` | **RESOLVED** | REQ-012 (spec.md:89-90) mandates a single text node; AC-011 (acceptance.md:198-209) pins it with `getAllByText('입고', {exact:true})` length 1; plan.md:106 makes re-running `:103` a verification step, explicitly "가정이 아니라 검증 항목". Genuinely sound fix. |
| D6 | major — EARS labels wrong on 7 of 14 REQs | **RESOLVED** | All 18 re-verified. See MP-2. |
| D7/D8 | major/minor — "byte-identical" equivalence claim false for NULL and negative | **RESOLVED (obsolete)** | The client-side sum is gone. The negative-`quantity` hole is now structurally impossible: `net_qty = max(…, 0) ≥ 0` and `received_quantity ≥ 0`, so `min(rq, net) ≥ 0` and `Σ min(rq_i, n_i) ≤ Σ n_i` — `입고 ≤ 총` holds universally. |
| D9 | minor — `null`/`undefined` inconsistency | **RESOLVED** | Removed with the arithmetic. REQ-006 correctly notes `received_quantity` needs no null guard. |
| D10 | minor — AC-006 caught no mutation, violating the doc's own [HARD] rule | **RESOLVED** | acceptance.md:13 adds an explicit "회귀 확인" exemption category and forbids disguising such ACs as discriminators. (One classification is now slightly inaccurate — N2.) |
| D11 | minor — REQ-013 cited a sort-order test that does not exist | **RESOLVED** | REQ-016 (spec.md:103-104) now states "**[감사 D11 정정]** 이 규칙을 검증하는 기존 테스트는 `SummaryTab.test.tsx`에 없다" and switches to a diff-range check. Honest. |
| D12 | minor — `priority: low` | **RESOLVED** | `priority: Medium`. |

**11 of 12 resolved; D4 recurs in a milder, safe-direction form.** No stagnation pattern (no defect unchanged across iterations).

---

## Citation Verification (focus area 1)

Every citation re-resolved by reading the target. **All accurate**, including the range the author claims to have corrected.

| Citation | Claim | Result |
|---|---|---|
| `purchase_order_views.py:2392-2579` | `_process_warehouse_receipt_rows` | **VERIFIED EXACT** — `def _process_warehouse_receipt_rows` at 2392; closing `}` of the return dict at 2579; next symbol `class UploadWarehouseReceiptView` at 2582. The v0.1.0 range was indeed wrong; this one is right. |
| `purchase_order_views.py:2542` | `received_quantity += received_count` | correct |
| `purchase_order_views.py:2549-2550` | `if received_quantity >= effective_quantity: logistics_status = "received"` | correct |
| `purchase_order_views.py:2525` | `effective_quantity = line_item.quantity or 0` (A3's basis) | correct |
| `purchase_order_views.py:3446` | `net_qty = max((li.quantity or 0) - li.refunded_qty, 0)` | correct |
| `purchase_order_views.py:3442-3479` | aggregation loop | correct |
| `purchase_order_views.py:3397-3489` | `LineItemRackNumberSummaryView` | correct |
| `purchase_order_views.py:3481-3489` | "정렬 블록" | range is correct as a diff guard; 3481-3487 is the sort, 3489 is the `return Response(...)` — the label "정렬" is slightly broader than the content, harmless |
| `models.py:228` | `received_quantity = models.IntegerField(default=0)` | correct |
| `migrations/0037_lineitem_add_received_fields.py` | existing migration adding the column | **VERIFIED** — file exists; adds `received_quantity` (line 13) and `received_at` (line 18) |
| `rackNumberApi.ts:68-73` / `:59-66` / `:65` | group type / line-item type / `logistics_status: string` | correct |
| `purchaseOrderApi.ts:78` | `{ value: 'received', label: '입고' }` | correct |
| `test_spec_014.py:343-349` | `_refund(...)` helper | **VERIFIED EXACT** — `def _refund(self, order, line_item, quantity, shopify_refund_id=900001)` spans 343-349 |
| `test_spec_014.py:176-195` | `TestTotalQuantity` | **VERIFIED EXACT** — decorator 176, class 177, final assert 195 |
| `test_spec_014.py:333-432` | `TestRefundExclusion` | correct — decorator 333, class 334, next decorator 435 |
| `test_spec_014.py` helper signatures (plan.md:75-76) | `_make_order`, `_make_line_item` with `defaults = {"quantity": 1, "title": "Test Book"}`, `_find_group` | **VERIFIED EXACT** at :34, :38-45, :55. `**kwargs → defaults.update(kwargs) → LineItem.objects.create(**defaults)` confirms plan.md:76's claim that `received_quantity=3` passes through without helper changes |
| `SummaryTab.test.tsx:103`, `:12-56`, `:248-249`, `:178-271`, `:237-270`, `:152-165`, `:89-107` | various | all correct (`:178` = `describe('collapse/expand behavior…`, `:271` = its closing brace) |
| `SummaryTab.tsx:96`, `:65`, `:17-20`, `:122`, `:58-134` | header span, expanded state, `@MX:NOTE`, 수량 cell, component | correct |

**A1/A2's "only writer" claim independently verified.** Exhaustive grep of `received_quantity` across `backend/` excluding tests and migrations returns 13 hits: one field definition (`models.py:228`), four comments, and in `purchase_order_views.py` only `:2527` (read), `:2534`/`:2560` (response echo), `:2542` (the sole `+=` write), `:2549` (read), `:2568` (bulk_update field list). **No decrement, no reset, no sync path touches it.** A1 and A2 hold.

---

## Clamp Arithmetic Attack (focus area 2)

I tested each named shape plus two of my own. Verified invariant: since `net_qty = max(…, 0) ≥ 0` and `received_quantity ≥ 0`, every term `min(rq_i, n_i) ∈ [0, n_i]`, so **`입고 ≤ 총` holds universally** and `입고` can never be negative.

| Shape | Behavior under the clamp | Covered by the SPEC? |
|---|---|---|
| **Negative `quantity`** (unconstrained `IntegerField`, no `CheckConstraint`) | `net_qty = max(-2, 0) = 0`; `min(rq, 0) = 0`; total += 0 → `입고 0 / 총 0권` | **Yes, structurally.** This was iteration-1 D7; the clamp eliminates it. No misleading header possible. |
| **`received_quantity` > `quantity`, no refund** | Reachable: `:2527` blocks over-receiving, but `LineItem.quantity` is itself overwritten on Shopify re-sync (`shopify_orders.py:236` inside the `update_or_create` `defaults` at `:265`/`:281`). Receive 5/5, then re-sync lowers quantity to 3 → `rq=5 > net=3` with `refunded_qty=0`. Clamp → `min(5,3)=3` → `입고 3 / 총 3권` | **Behavior yes, rationale no.** REQ-003's condition is cause-agnostic ("`received_quantity`가 `net_qty`를 초과하면", refund given only as "예:"), so the requirement covers it. But A2/A3 present the refund as *the* cause and the SPEC's grep verification covered `received_quantity` writers only, not `quantity` writers → **N4**. |
| **Fully-refunded row dropped server-side with non-zero `received_quantity`** | `if li.refunded_qty and net_qty == 0: continue` → row contributes 0 to both fields. Had it not been dropped, `min(rq, 0) = 0` — identical. Drop and clamp agree; no divergence | **Yes.** REQ-002 (spec.md:56) explicitly scopes aggregation to rows "기존 필터를 통과하고 **전량 환불로 드롭되지 않은**". Not independently observable, and a mutation removing the `continue` would break `total_quantity` and fail `test_spec_014.py TestRefundExclusion` (in DoD, acceptance.md:266). |
| **`quantity` NULL with `received_quantity > 0`** | `net_qty = max(0-0,0) = 0`, `refunded_qty=0` is falsy so the row is **not** dropped; `min(4,0) = 0` → contributes 0 | **Yes** — REQ-005 (spec.md:64-65) states exactly this, and AC-003 pins it. But the shape is **unreachable via the only writer**: `:2525-2527` computes `effective_quantity = quantity or 0 = 0` and rejects any `received_count ≥ 1` as `quantity_exceeded` → **N6** (acceptance.md:27 presents it as a real-world cause). |
| **Mixed group** (row A: q=5, ref=2, rq=5 → 3; row B: q=4, ref=0, rq=1 → 1) | total 7, received 4. Physically 6 arrived, 2 refunded → 4 still sale-attached. Per-line clamp is correct here; a group-level clamp would also give 4 | Yes |
| **Refund recorded *before* receiving** (q=5, ref=2, net=3; warehouse then receives up to 5 because `:2527` uses original `quantity`) | `min(5,3) = 3` → `입고 3 / 총 3권`, while 5 books physically sit on the rack | **Yes, explicitly.** A2 (spec.md:40) and A3 (spec.md:41) document the divergence; C1 (spec.md:157) states the stored value hides it; Exclusion #7 (spec.md:149) defers "환불 시 `received_quantity`를 실제로 조정해야 하는가" as out of scope. This is honest disclosure, not a gap. |

**Conclusion:** the clamp is sound and no shape produces `입고 > 총` or a negative count. The SPEC's *requirements* cover every shape; its *assumptions* under-enumerate one cause (N4) and over-state the reachability of another (N6).

---

## Mutation Table Verification (focus area 3)

I re-derived the discrimination matrix computationally rather than reading the document's claims. Backend results — columns are the group's `received_quantity` under each implementation:

```
AC      total  correct | M1_gate  M2_noclamp  M4_skipUnassigned  || M1? M2? M4?
AC-001      5        3 |       0           3                  3  ||  True False False
AC-002      3        3 |       3           5                  3  || False  True False
AC-003      0        0 |       0           4                  0  || False  True False
AC-004      9        3 |       2           3                  3  ||  True False False
AC-005      3        0 |       0           0                  0  || False False False
AC-006      5        2 |       2           2                  0  || False False  True
```

Every `total`/`correct` pair matches the document's "Then" clause exactly (acceptance.md:49, 64, 79, 100, 115, 130). **All backend AC arithmetic is correct** — a real improvement over v0.1.0, where the equivalent claim was wrong.

**Sole-discriminator claims, tested individually:**

- **M4 → AC-006: TRULY SOLE ✓.** AC-001…005 all use named racks (P-1…P-5); only AC-006 exercises `rack_number=""`. Mutation yields 0 vs correct 2.
- **M6 → AC-008: TRULY SOLE ✓.** AC-008 is the only FE fixture with `received_quantity: 0` (others: 3, 1, 3, 3), so it is the only one that observes the `=== 0` branch. Mutation drops the `입고` segment entirely; `toHaveTextContent('입고 0 / 총 6권')` fails.
- **M7 → AC-011: TRULY SOLE ✓.** All other FE ACs assert via `toHaveTextContent` on the button, which is substring-based and unchanged by splitting the header into two spans. Only AC-011's `getAllByText('입고', {exact:true})` length assertion observes node structure. Verified the fixture actually produces a second `입고` node: the expanded table's 물류상태 cell renders `LOGISTICS_STATUS_LABELS['received']` = `입고` (purchaseOrderApi.ts:78, confirmed). Correct → 1 match; split → 2.
- **M1 → AC-001: NOT SOLE ✗** — see N1.

**Non-discriminator AC, honesty check (as requested):** AC-RACKRECV-010 is declared "잡는 변이: **없음(회귀 확인)**" (acceptance.md:186, :226). It asserts `입고 3 / 총 8권`. Under M5 (field swap) it would render `입고 8 / 총 3권` and **fail**. So AC-010 does catch M5. The table is **inaccurate but conservative** — it understates coverage, the opposite direction from v0.1.0's D4 → N2.

---

## Defects Found

### N1. acceptance.md:19, :217, :229, :231 — "M1 → AC-RACKRECV-001 (단독)" is false; the document contradicts itself — Severity: **major**

acceptance.md:11 makes a [HARD] commitment: *"이번 버전은 '단독/유일'이라는 표현을 **실제로 그 AC 하나만 해당 변이를 잡을 때만** 사용하고"*. It is violated in the very next table.

acceptance.md:19 reads: `**AC-RACKRECV-001 (단독)**, AC-RACKRECV-004(공동 보조)` — labelling AC-001 "sole" while listing a second AC that also catches M1, in the same cell. AC-004's own 판별력 text at :102 confirms it: *"M1(상태 게이트)이 있으면 행 2(`shipment_confirmed`)가 제외되어 `received_quantity == 2`를 낸다 — `2 ≠ 3`이므로 잡힌다."*

Verified computationally: M1 is caught by **AC-001 (0 vs 3) and AC-004 (2 vs 3)**.

Consequence: the [HARD] protection rule at acceptance.md:231 — *"AC-RACKRECV-001/006/008/011 중 하나라도 삭제·약화·픽스처 변경되면 해당 변이가 즉시 미커버가 된다"* — is false for AC-001. This is the same defect class as iteration-1 D4, in a document that explicitly claims to have remediated it. Coverage is not harmed (M1 is over-covered), but a normative [HARD] rule rests on a false premise.

### N2. acceptance.md:186, :194, :226 — AC-RACKRECV-010 is classified as catching no mutation, but it catches M5 — Severity: **minor**

Its assertion (`입고 3 / 총 8권`, acceptance.md:192) fails under the field-swap mutation (`입고 8 / 총 3권`). The claim at :194 that it "이 SPEC이 도입하는 신규 로직 … 에 대한 변이를 잡지 않는다" is false with respect to M5, which is precisely new field-rendering logic. Errs in the safe direction, but it is an inaccuracy in a table the author states was hand-verified.

### N3. acceptance.md:20, :27, :237, :263 — "AC-002와 AC-003 두 AC가 공동으로 **필요**" is not supported by the stated mutation — Severity: **minor**

M2 is defined as *"클램프 누락 — raw `received_quantity`를 그대로 합산"* (acceptance.md:20) — a single code change. Per the matrix, **AC-002 alone catches it (5 vs 3) and AC-003 alone catches it (4 vs 0)**; each is independently sufficient. Joint necessity would only hold for a finer-grained mutation such as a partial clamp (`min(rq, net) if refunded_qty else rq`), which is not in the 7-mutation table. Keeping both tests is right; asserting they are *jointly required* for M2 is an unsupported claim, and the DoD checkbox at :263 enforces it as if proven.

### N4. spec.md:40-41 (A2/A3), plan.md:47 — the assumptions enumerate only the refund cause of `received_quantity > net_qty`; `LineItem.quantity` is itself mutable — Severity: **minor**

A2 justifies the clamp by grep-verifying that nothing decrements `received_quantity` — which I confirmed. But the inequality `received_quantity > net_qty` has a second, independent cause: `net_qty` derives from `li.quantity`, and `quantity` is written on every Shopify re-sync via `"quantity": li.get("quantity")` (`backend/order/shopify_orders.py:236`) inside the `defaults` of `LineItem.objects.update_or_create` (`:265`, `:281`). Receiving 5/5 then re-syncing to `quantity=3` yields `rq=5 > net=3` with zero refunds — a shape A2's rationale does not predict.

REQ-003's condition is cause-agnostic so the **required behavior is correct**; only the stated justification is incomplete. Recommend extending A2 (or adding A5) to note that `quantity` is sync-mutable, so the clamp defends against divergence from either side.

### N5. plan.md:168 — the MX gate is already failed and the instruction is unactionable — Severity: **minor**

plan.md:154 proposes adding a new `@MX:NOTE` to `purchase_order_views.py`, and plan.md:168 instructs: *"작업 전 `purchase_order_views.py`의 기존 NOTE 개수를 확인해 `mx.yaml`의 `note_per_file` 한도(기본 10)를 넘지 않는지 확인한다."*

Measured: the file already contains **22** `@MX:NOTE` tags, against `note_per_file: 10` in `.moai/config/sections/mx.yaml:177`. The limit is exceeded more than twofold before this SPEC adds anything, so the check as written can never pass and gives the implementer no decision rule. Either state that the file is a known pre-existing exception, or drop the gate.

### N6. acceptance.md:27 — the NULL path is presented as a real-world cause, but it is unreachable via the only writer — Severity: **minor**

acceptance.md:27 justifies AC-003 as covering cause *"(b) `quantity`가 `NULL`이라 `net_qty`가 애초에 0인데 `received_quantity`는 이미 양수인 경우"*. For a NULL-quantity LineItem, `:2525` gives `effective_quantity = 0` and `:2527` rejects any `received_count ≥ 1` as `quantity_exceeded` **with no write** — so the sole writer can never produce this state. It is reachable only if `quantity` is nulled by a later re-sync.

AC-003 remains worth keeping as a defensive pin on the clamp, but it should be described as a defensive/unreachable-by-construction case rather than a naturally occurring one.

### N7. spec.md:118-135 — 8 of 18 requirements have no acceptance criterion — Severity: **minor**

REQ-006, 007, 013, 014, 015, 016, 017, 018 (44%, up from 36% in v0.1.0). Most are non-goals legitimately verified by diff, and the new [HARD] 추적표 무결성 규칙 (spec.md:137) makes the disclosure honest — a genuine improvement over D11. Two observations remain:
- **REQ-006** (spec.md:67-68) states a property of the model (`IntegerField(default=0)`, no null guard needed) rather than a required system behavior. It is a rationale note promoted to a [HARD]-adjacent requirement; it neither constrains the implementation nor can it be violated.
- **REQ-007**'s "컴파일 타임 검증" (spec.md:124) is sound — omitting the type field breaks every frontend AC at typecheck.

### N9. acceptance.md — no AC verifies per-group isolation of the new field — Severity: **minor**

Every backend fixture (AC-001…006) creates exactly **one** group, so each response contains a single group. A mutation that accumulates `received_quantity` into a shared/global counter rather than per-group (e.g., a variable hoisted outside the `groups.setdefault` scope) would produce an identical value for the single group in every fixture and pass all six ACs. The existing `test_spec_014.py TestCrossOrderGrouping` (:119-145) predates this field and asserts only grouping and `total_quantity`.

Cheap fix: one AC with two groups carrying different received values (e.g., P-1 → 3, P-2 → 1) asserted independently. Low probability given the `setdefault` structure, but it is the one mutation class the 7-mutation table does not reach.

### N10. plan.md:77 — `_refund` cannot be reused "그대로" — Severity: **very minor**

plan.md:77 says the helper is reused verbatim, but `test_spec_014.py:343` defines it as an instance method (`def _refund(self, order, line_item, quantity, shopify_refund_id=900001)`) on `TestRefundExclusion`, so it must be redefined in the new test class. acceptance.md:31 states this correctly ("그대로 재사용하거나 **동일 시그니처로 재정의한다**"); only plan.md is imprecise.

---

## Scope Assessment (focus area 4)

**The growth is forced by the architecture, not padding.** Judgment per unit:

**Files 2 → 5 — all five forced.** The chosen data source (`LineItem.received_quantity`) is absent from the summary response, so a backend aggregation is unavoidable; that in turn forces (1) the view, (2) a new backend test file, (3) the TypeScript type, (4) the component, (5) the frontend test. There is no smaller file set that implements decision #1. Notably the SPEC did **not** grow into the write path, migrations, row-level fields, or `SearchTab.tsx` — all explicitly fenced off (REQ-015/016/017/018, Exclusions 1-7).

**REQs 14 → 18.** Behavioral requirements went 9 → 12, all traceable to the new architecture (field existence, clamp, clamp-negation, status-independence, NULL, no-null-guard, API contract, plus the D5-mandated single-text-node rule). Non-goals went 5 → 6: `REQ-017` (write path untouched) and `REQ-018` (no migration) are newly *necessary* because the SPEC now edits the file containing `_process_warehouse_receipt_rows` and reads a model column — both are real new risks that did not exist in v0.1.0. Only **REQ-006 is padding** (N7).

**ACs 7 → 11.** Six backend ACs for six distinct behaviors (partial receipt, clamp-via-refund, clamp-via-NULL, multi-item sum, field existence, unassigned group) plus five frontend. AC-004 is the weakest — it catches only M1, which AC-001 already catches (N1) — but it does verify multi-item accumulation, which no other AC does, so it earns its place on a ground the table understates.

Verdict on scope: **justified.** One redundant requirement and one AC whose stated value is mislabeled; no drive-by expansion.

---

## Chain-of-Verification Pass

Second-look findings — three defects were added on the second pass:

1. **Did I read every REQ, or skim after the first few?** Re-read all 18 individually against the five EARS patterns rather than trusting the corrected labels. Confirmed REQ-003 is a genuine `If … then` and REQ-013…018 are correctly relabeled — D6 is truly fixed. Also noted REQ-006 states a model fact, not a behavior → **N7**.
2. **Did I check REQ sequencing end-to-end?** Enumerated all 18 REQ IDs and all 11 AC IDs against both §3/§4 and the acceptance doc. Clean.
3. **Did I verify traceability for every REQ, or sample?** Walked all 18 rows of spec.md:118-135. Counted 8 AC-less REQs and checked each stated verification method for adequacy — REQ-007's compile-time argument holds; REQ-006's does not constrain anything.
4. **Did I check Exclusions for specificity?** All 7 read individually. Exclusion #5 now correctly describes `received_quantity` as an **existing** column with its migration named — the exact wording that produced iteration-1's D1 is gone. Exclusion #7 (no retroactive decrement) is a genuinely new, well-scoped boundary.
5. **Did I look for contradictions *between* requirements?** REQ-004 (ignore `logistics_status`) vs REQ-002 (aggregate over filter-passing rows) — consistent, since the view-level `shipped`/`order_cancelled` filters are membership rules, not status gates on the new sum. REQ-008 (no client arithmetic) vs REQ-009 (render 0 verbatim) — consistent. No contradictions found.
6. **Did I accept the document's own mutation table?** No — recomputed it. This produced **N1** (M1 not sole, self-contradictory at :19 vs :102) and **N2** (AC-010 does catch M5), neither of which is visible from reading the claims.
7. **Did I test only the shapes I was handed?** Added two of my own — the mixed-group case and the refund-before-receiving case — and traced `quantity`'s own write path, which produced **N4** (sync-mutable `quantity` as a second cause) and confirmed **N6** (NULL path unreachable via `:2527`).
8. **Did I verify the environment claims, not just the code claims?** Counting `@MX:NOTE` in the target file against `mx.yaml` produced **N5** (22 vs a limit of 10).

---

## Recommendation

**PASS.** All four must-pass criteria are satisfied with cited evidence; both iteration-1 critical defects are genuinely resolved, not papered over. The verdict rests on independent verification rather than the document's self-assessment: I recomputed all six backend ACs' expected values (all match), confirmed all 7 declared mutations are actually detected, and confirmed that **no AC passes under both the correct and the mutated implementation** — the specific failure that made iteration 1 a FAIL. The clamp is arithmetically sound, guarantees `입고 ≤ 총` for every reachable data shape including the four named ones, and the residual real-world divergence (physically-received-but-refunded stock) is explicitly disclosed in A2/A3, C1 and Exclusion #7 rather than hidden.

The defects below do not block implementation but **must be corrected in the SPEC before it is treated as authoritative**, because three of them are false statements inside [HARD] rules:

1. **[N1, major] Fix the M1 "단독" claim.** Change acceptance.md:19 to `M1 → AC-RACKRECV-001 + AC-RACKRECV-004 (공동)`, update :217/:220/:229, and remove AC-001 from the [HARD] 단독 판별자 목록 at :231 — its weakening does **not** leave M1 uncovered. Keep AC-001 (it is the cleanest single-row proof), but stop asserting exclusivity that the fixtures contradict.
2. **[N2, minor] Reclassify AC-RACKRECV-010** as "잡는 변이: M5(공동 보조) — 그 외에는 회귀 확인" at :186/:194/:226, or change its fixture to `total_quantity == received_quantity` if a pure regression AC is genuinely wanted.
3. **[N3, minor] Restate the AC-002/003 relationship.** Either define the finer-grained mutation they jointly cover (a partial clamp applied only on the refund path) and add it to the table as M8, or downgrade the wording from "공동으로 필요" to "각각 독립적으로 M2를 잡으며, 서로 다른 원인 경로를 문서화한다" and soften the DoD checkbox at :263.
4. **[N4, minor] Extend A2/A3.** Note that `LineItem.quantity` is overwritten on Shopify re-sync (`shopify_orders.py:236` in the `update_or_create` defaults at `:265`/`:281`), so `received_quantity > net_qty` can arise with no refund at all. State that REQ-003's clamp is deliberately cause-agnostic.
5. **[N5, minor] Fix the MX gate at plan.md:168.** `purchase_order_views.py` already carries 22 `@MX:NOTE` against `mx.yaml:177`'s `note_per_file: 10`. Record the file as a known pre-existing exception or remove the check.
6. **[N6, minor] Re-describe AC-003's cause** at acceptance.md:27 as defensive/unreachable-by-construction (blocked by the `:2527` `quantity_exceeded` guard), reachable only if `quantity` is later nulled.
7. **[N9, minor] Add one two-group backend AC** (e.g., P-1 → `received_quantity` 3, P-2 → 1, asserted independently) to close the per-group-isolation mutation class.
8. **[N7/N10, minor] Housekeeping.** Consider folding REQ-006 into REQ-002's rationale rather than carrying it as a requirement; correct plan.md:77 to say `_refund` is redefined with the same signature (it is an instance method of `TestRefundExclusion`), matching acceptance.md:31.

Verdict: PASS
