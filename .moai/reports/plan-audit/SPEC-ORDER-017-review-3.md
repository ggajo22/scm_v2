# SPEC Review Report: SPEC-ORDER-017
Iteration: 3/3
Verdict: PASS
Overall Score: 0.88

Reasoning context ignored per M1 Context Isolation. The author's revision narrative
(spec.md HISTORY :21, plan.md :26-40, the `**(v1.0.2 정정, DXX)**` prose blocks in
acceptance.md) was read only as document content subject to audit, never as justification.
Every verdict below was re-derived from the documents as they now stand plus the source
files they cite, each opened independently this iteration.

---

## Must-Pass Results (re-run from scratch, nothing inherited from iterations 1-2)

- **[PASS] MP-1 REQ/AC number consistency**: Machine-verified, not spot-checked.
  `grep -o '\*\*REQ-RACKBATCH-[0-9]*\*\*' spec.md | sort | uniq -c` returns exactly one
  occurrence each of 001…015 — 15 definitions, no gap, no duplicate, uniform 3-digit
  padding. The same check on AC tokens returns exactly one each of 001…**012** — the new
  AC-RACKBATCH-012 extends the sequence without renumbering 001-011, as the iteration-2
  recommendation required. `acceptance.md` carries 12 `### AC-RACKBATCH-XXX` headings
  (`:32, 66, 76, 89, 98, 108, 132, 142, 152, 167, 186, 208`) — the same set. Both documents
  present ACs out of numeric order (012 sits between 009 and 010 in spec.md:366 and
  acceptance.md:167; 005 sits after 007 in acceptance.md:132), which is presentation, not a
  numbering defect. spec.md:206-208 and :423-425 correctly describe the resulting shape
  (15 REQ / 12 AC). No regression from the AC 11→12 growth.

- **[PASS] MP-2 EARS format compliance**: All 15 REQs and all 12 ACs re-classified
  independently against the five canonical patterns — every one read individually, not
  sampled. Every declared label matches the sentence structure actually used:
  - Unwanted, true `If … then …`: REQ-009 (:255), REQ-010 (:258), REQ-011 (:262),
    REQ-015 (:283), AC-005 (:336), AC-009 (:361), and the **new AC-012** (:366-367,
    `"Given a batch with two matching keys, if an exception is raised immediately after …,
    then the system shall respond with HTTP 500"`). AC-012's leading `Given` fixture clause
    before the `If` is the same construction iterations 1-2 accepted for AC-002/003/004/006,
    so the treatment stays internally consistent.
  - State-Driven, true `While`: REQ-005 (:232), AC-007 (:345).
  - Event-Driven, `When`-triggered: REQ-003 (:224), REQ-004 (:228), REQ-006 (:238),
    AC-001 (:300, after a `**Scope**:` metadata sentence), AC-002 (:321), AC-003 (:326),
    AC-004 (:331), AC-006 (:341), AC-008 (:356).
  - Ubiquitous, bare `The system shall …`: REQ-001 (:212), REQ-002 (:218), REQ-007 (:244),
    REQ-008 (:251), **REQ-012 (:265, rewritten this revision** — `"The system shall never
    invoke the order-aggregate recomputation routine"`, internal symbol removed, label
    unchanged and still correct**)**, REQ-013 (:270), REQ-014 (:274), AC-010 (:379),
    AC-011 (:387). None opens with a trigger.
  No label-vs-structure mismatch anywhere. MP-2 passes.

- **[PASS] MP-3 YAML frontmatter validity**: all six required fields present and correctly
  typed — `id: SPEC-ORDER-017` (spec.md:2, matches `SPEC-{DOMAIN}-{NUM}`), `version: 1.0.2`
  (:3, string), `status: draft` (:4, inside the FC-3 vocabulary), `created_at: 2026-08-12`
  (:5, ISO date), `priority: High` (:8, string), `labels: [order, rack-number, performance,
  batching]` (:10, array). All four sibling documents were re-checked and are synchronized at
  `version: 1.0.2` / `status: draft`: plan.md:1-7, acceptance.md:1-7, research.md:1-7,
  spec-compact.md:1-7. spec-compact.md is not stale — it already carries the 12-AC count
  (`:65`), AC-012 (`:81`), the extracted function (`:21, 87`), the split `:1143-1147` /
  `:1149-1153` / `:1155-1157` citations (`:123-124`) and the 7th exclusion (`:101`).

- **[N/A] MP-4 Section 22 language neutrality**: N/A — single-stack SPEC. Scope is one Django
  module plus pytest; spec.md:67-68 and Exclusions (:436-437) exclude all frontend change. No
  multi-language tooling claim anywhere, so no 16-language enumeration is owed.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in two-three items, resolvable consistently by a reasonable engineer | REQs are single-interpretation throughout (spec.md:212-286). Residual ambiguity is localized to three spots, all newly introduced by this revision: AC-001 attributes a guard-structure requirement to REQ-001 that REQ-001's text does not carry (D16); spec.md states AC-011/AC-012 at endpoint scope ("around a successful upload", "after the request completes", "respond with HTTP 500") while acceptance.md pins both to direct function calls (D18); acceptance.md:24 says AC-007 is `[뷰]` while acceptance.md:108 and :248 say `[뷰 또는 함수]` (D20). |
| Completeness | 1.00 | 1.0 — all required sections, frontmatter complete, exclusions specific | HISTORY (:15-21), WHY/문제 정의 (:25-37), WHAT/솔루션 개요 + 범위 델타 (:39-90), HOW/설계 결정 A–H (:92-202), REQUIREMENTS (:204-286), ACCEPTANCE CRITERIA (:290-425), Exclusions with **7** concrete entries (:429-445), 관련 SPEC (:447-458). The new 7th exclusion (:442-445, "`_process_rack_number_rows` 외 추가 계층·클래스 없음") is specific and correctly counted in both downstream gates (acceptance.md:273, plan.md:277). |
| Testability | 0.75 | 0.75 — one AC not precisely binary-testable as written but measurable with minor interpretation | Every AC that iteration 2 found non-discriminating now discriminates — verified case by case in the Regression Check below. The single residual: AC-011 (a)'s literal wording ("the emitted `UPDATE` statement's `SET` clause shall reference the `rack_number` column and no other `LineItem` column", spec.md:392-394) is unsatisfiable as written against a correct implementation, because Django 5.1.6's `bulk_update` emits `SET rack_number = CASE WHEN "id" = … THEN … END`, i.e. the `id` column is referenced inside the SET clause (D17). It fails closed and visibly, and the fix is a one-clause reword. |
| Traceability | 1.00 | 1.0 — every REQ has an AC, every AC references an existing REQ, no orphans | Re-derived exhaustively, not sampled. All 15 REQ rows in spec.md:407-421 match all 15 rows in acceptance.md:281-295. All 12 `Traces:` lines were diffed mechanically between spec.md (:296, 321, 326, 331, 336, 341, 345, 356, 361, 366, 379, 387) and acceptance.md (:34, 68, 78, 91, 100, 110, 134, 144, 154, 169, 188, 210) — **identical in all 12 cases**. Zero orphan ACs, zero uncovered REQs. The per-REQ DoD table (acceptance.md:242-258) was re-verified against source for every existing-test claim; all six survive (see Regression Check). |

---

## Regression Check — iteration-2 defects

Each was tested for genuine closure, not relabelling.

| # | Status | Evidence |
|---|--------|----------|
| **D2a** (query ceilings transplanted from a context with no auth query; `<= 2` unattainable, critical) | **RESOLVED** | The root cause is removed rather than papered over. The measurement scope is now the extracted function, stated in four places (spec.md:296-299 `"this AC measures _process_rack_number_rows(rows) directly under CaptureQueriesContext … No HTTP request is made and no authentication query is issued"`, acceptance.md:36-40, plan.md:154-155, spec-compact.md:70), and the derivation is spelled out per case instead of cited. I re-derived all three bounds independently against the guard structure the SPEC mandates: **10 matched** = savepoint + `Order` + `LineItem` + `bulk_update` + release = 5 ≤ 6 (margin 1); **all-unmatched** = savepoint + `Order` + release = 3 ≤ 4 (margin 1); **empty** = savepoint + release = 2 ≤ 2 (no margin, exactly attainable). All three are correct **for this function's own query shape**. The anchor is sound: the reference bounds are an already-passing committed test over a structurally identical function, and the three guards it depends on were opened at source — `purchase_order_views.py:2533` `if grouped:`, `:2550` `if orders_by_name:`, `:2701` `if to_update:` all exist exactly as cited. `bulk_update` adds no savepoint of its own (Django uses `atomic(savepoint=False)` internally), so the 1-query accounting is right. |
| **D2b** (all-unmatched fixture under-specified; two readings straddle `<= 4`) | **RESOLVED** | The fixture is now pinned to the absent-`Order.name` case, and the alternative is explicitly excluded, in all four documents: spec.md:306-308 (`"a non-existent Order.name (all-unmatched via absent order, not via an unmatched SKU on an existing order — the two flavors produce different counts)"`), acceptance.md:44-46, plan.md:161-166 (which additionally states the rejected reading's count: `"SKU가 없어서 미매칭 … 실측 4가 되어 이 상한과 다르다"`), spec-compact.md:70. **The LineItem fetch provably does not fire**: the mandated `if orders_by_name:` guard is false because the `Order` fetch returns zero rows for absent names. Verified against the reference fixture at `test_spec_015.py:1151` (`{"name": f"#MISSING{i}", …}`), which the SPEC cites and which matches. |
| **D2c** (`<= 2` cited to a range not containing it, minor) | **RESOLVED — all four sites re-opened** | Source: `:1143-1147` is `test_query_count_stays_within_a_small_fixed_bound` ending `assert … <= 6`; `:1149-1153` is `test_a_batch_that_writes_nothing_issues_no_write_query` ending `assert _count_queries(rows) <= 4`; `:1155-1157` is `test_an_empty_batch_touches_the_database_at_most_for_the_transaction` ending `assert _count_queries([]) <= 2`. All three ranges are now cited separately and correctly at spec.md:305/310/314, acceptance.md:52/55/57, plan.md:157/163/169 and plan.md:312-316, spec-compact.md:123-124. |
| **D4-R** (blank-order-identifier fixture used *different* SKUs, restoring non-discrimination, major) | **RESOLVED** | The two blank rows now share **one** SKU, and the constraint reached the normative document: spec.md:348-354 (`"two with a blank order-identifier cell that carry the **same SKU** as each other"`, plus an explicit statement of why sharing the SKU is what makes the AC discriminating), acceptance.md:112-128 (`[HARD]`-marked, with the full argument), plan.md:198-204, spec.md:89 (범위 델타 row). I re-derived the discrimination against the live keying at `purchase_order_views.py:2205-2212` (`key = (row["order_name"], row["sku"]) if row["order_name"] is not None else (None, idx)`): with three rows (blank/`SKU-BLANK`, blank/`SKU-BLANK`, valid) a correct `(None, idx)` implementation yields 3 dedup entries → `skipped_count == 2`; a `(None, sku)`-merging implementation yields 2 entries → `skipped_count == 1`, **failing** the assertion. The fixture now genuinely discriminates. Parser feasibility also checked: blank order-identifier rows survive parsing with `order_name=None` (`test_spec_013.py:475, 491`) while blank-**SKU** rows are dropped (`:505`), so a non-empty shared SKU is required and is what the fixture specifies. |
| **D7-R** (`bulk_update` field-list widening undetectable by a value snapshot, major) | **RESOLVED (with a wording defect, D17)** | AC-011 now carries two independent observations, with (a) SQL-level as the discriminating one: spec.md:387-401, acceptance.md:212-232, plan.md:217-225, and the R6 mitigation row (plan.md:243) was corrected to name M4-8(a) rather than the snapshot as the actual pin. **Does it fail if the implementation passes extra field names?** Yes: Django 5.1.6's `bulk_update` builds one `Case/When` expression per listed field, so `bulk_update(objs, ["rack_number", "shipped_quantity"])` emits `SET rack_number = CASE … END, shipped_quantity = CASE … END`. The extra column is textually present in the SET clause and the assertion fails. The residual issue is over-strictness, not under-strictness — see D17. |
| **D12** (AC-009's injection point before the write cannot fail an implementation missing `transaction.atomic()`, major) | **RESOLVED** | The two concerns were separated: AC-009 (spec.md:361-364, acceptance.md:152-165) is now scoped to REQ-015 only and says so explicitly (`"It does NOT prove atomicity — see AC-RACKBATCH-012"`), and the new AC-012 (spec.md:366-377, acceptance.md:167-184) owns REQ-013. **Is the fault injected after `bulk_update` has executed?** Yes, unambiguously and in three places: spec.md:367-369 (`"immediately after the single bulk_update call has actually executed against the database — so the UPDATE statement has run inside the still-open transaction.atomic() block — but before that block exits"`), acceptance.md:176-178, plan.md:210-216, plus a dedicated risk R9 (plan.md:246) requiring the patch's `side_effect` to call the real `bulk_update` first. **Does it fail without `transaction.atomic()`?** Yes: with the block present the exception unwinds the savepoint and the post-call read shows pre-request values; with the block absent the executed `UPDATE` is not unwound and the same read observes the change, failing the AC. Discriminating in both the function-level and view-level readings. Traceability moved correctly — spec.md:419 and acceptance.md:293 both map REQ-013 → AC-012. |
| **D13** (REQ-008's "no additional field" half untested; DoD table falsely promised coverage, major) | **RESOLVED** | AC-010 (a) now demands a new assertion with an exact key set — spec.md:380-383 (`"a response body whose key set is **exactly** {"matched_count", "skipped_count"} — verified by a new assertion, since no existing test asserts the key set"`), acceptance.md:199-201 (`set(res.data.keys()) == {"matched_count", "skipped_count"}`), plan.md:226-230 (M4 item (f)). The DoD table was corrected: acceptance.md:251 moves REQ-008 to the `test_spec_017.py` bucket and states why `test_spec_013.py:664` does not qualify, and acceptance.md:266 records the exclusion. I re-opened `test_spec_013.py:664-678` — it asserts only `status_code == 200`, `res.data["matched_count"] == 1`, `res.data["skipped_count"] == 0` and the persisted `rack_number`, confirming the SPEC's own diagnosis is accurate. |
| **D11** (AC-011 field scope: 7 enumerated fields vs "모든 필드", minor) | **RESOLVED** | acceptance.md:228-230 now enumerates the same seven fields spec.md:395-398 does; "모든 필드" is gone. All seven exist on the model (`backend/order/models.py`: `title`, `quantity`, `price`, `purchase_status`, `logistics_status`, `shipped_quantity`, `shipped_at`), so the fixture is implementable. |
| **D14** (REQ-012 named an internal symbol, minor) | **RESOLVED** | spec.md:265-266 now reads `"the order-aggregate recomputation routine"`. The symbol survives only in 결정 F (:147-150) and in AC-008 (:358) / acceptance.md:147, where it names the patch target — appropriate for a verification clause. |
| **D15** (`[HARD]` equality claim covered a field spec.md does not carry, minor) | **RESOLVED** | acceptance.md:14-18 narrows the claim to `Traces:` only and states the reason. I then verified the narrowed claim holds for all 12 ACs (see Traceability above). |

**Stagnation watch cleared.** D4 appeared in iterations 1 and 2 and was the flagged blocking-defect candidate; it is fixed at the level of the discrimination argument itself, in the normative document, not just in the derived one. No defect from any prior iteration survives.

---

## Audit of the newly introduced design decision (설계 결정 H)

Checked as normative content, independent of the fact that it was user-approved.

- **Does the SPEC state the helper owns the dedup pass (not the view)?** Yes, four times, and one of them pre-empts exactly the "move the loop but leave dedup behind" misread: spec.md:185-187 (`"dedup은 뷰가 아니라 이 함수가 수행한다"`), spec.md:47-48, plan.md:101-104, plan.md:90 (the MODIFY row: `"dedup_map 구축부(:2198-2212)는 이 메서드에서 제거되어 새 함수로 이동한다(단순 삭제가 아니라 이동)"`). Input type is pinned as `parse_rack_number_excel`'s raw return (pre-dedup) at spec.md:185 and plan.md:101-102. Consistent everywhere.
- **Is the single-caller constraint stated?** Yes, and it is enforceable: spec.md:46, :84, :189-191, plan.md:89, plan.md:271 (`"호출부가 정확히 1개(UploadRackNumberView.post())인지 Grep으로 확인"`), acceptance.md:274. The cited precedent is real — I grepped every reference to `_process_force_outbound_rows` in the repo: the only production call site is `purchase_order_views.py:3220`, inside `OutboundForceProcessView.post()` (class opens at `:3194`), exactly as spec.md:178-179 and plan.md:286-288 claim.
- **Does the `@MX:WARN`/`@MX:REASON` at `:2218-2226` have an explicit new home?** Yes. Re-verified live: `# @MX:WARN:` at `:2218`, `# @MX:REASON:` at `:2223`, block ends `:2226`, `for row in dedup_map.values():` at `:2227` — the range is exact. Its new home is named in spec.md:195-197, plan.md:89, plan.md:132-134, and mx_plan row plan.md:253 (which additionally records the mx-tag-protocol rationale for not deleting it and the reason it is kept alongside, not merged into, the 결정-A `@MX:NOTE`), plus risk R7 (plan.md:244). One inconsistency: spec.md:196 and plan.md:132 say the tag moves *onto* the function (`"새 함수 위로"`), while the mx_plan target column (plan.md:253) says *inside* it (`"_process_rack_number_rows 안, 판정 루프의 결정 E 다중 매칭 지점"`). Both name the same function; only the anchor line differs. Folded into D20.
- **Does the extraction silently change any of the 15 behaviours pinned by `test_spec_013.py`?** I enumerated all 15 tests (`:615, 620, 637, 649, 664, 680, 703, 714, 729, 748, 766, 784, 809, 836, 842` — the count of 15 the SPEC asserts at :83 is correct) and walked each against the target design. None is broken: the 400/422 ordering stays in the view (plan.md:90 keeps `:2181-2196` in place, guarded by risk R8 at plan.md:245); `.filter(name=X).first()` → `name__in` + `order_by("pk")` + `setdefault` is behaviour-preserving (Django orders an unordered queryset by pk for `.first()`, and the reference comment at `:2524-2531` documents the same reasoning); `line_items.update(...)` → in-memory mutate + `bulk_update` preserves the multi-LineItem contract at `:748` and the counting contract at `:784`; the recompute patch target at `:842` still resolves because the function stays in the same module. **One unpinned behaviour does change** and is not acknowledged anywhere: dedup construction currently sits *outside* the `try` (dedup at `:2198-2212`, `try` opens at `:2216`), so an exception during dedup escapes to DRF; after extraction it moves *inside* the extracted call and is caught by `except Exception` → the custom `{"detail": …}` 500 body. No test pins this, and both paths are 500-class, so it is not a regression against the 15 — recorded as an observation, not a defect.
- **Does the extraction actually buy what it claims?** Yes. The root cause it removes is real: `authentication_classes = [JWTAuthentication]` at `purchase_order_views.py:2177`, imported at `:47`, and the `auth_client` fixture at `test_spec_013.py:76-79` issuing a real Bearer token — both re-opened and exact. Measuring the function directly removes the auth `SELECT` from the count, which is what makes `<= 2` attainable.
- **Is the reuse candidate accurately described?** Yes. plan.md:113-117 claims `_resolve_orders_by_name` has an internal guard, zero queries on empty input, one batched query otherwise, and returns `dict[str, Order]`. Opened at `:2812-2829`: `if names:` guard present, `Order.objects.filter(name__in=set(names)).order_by("pk")` with `setdefault`, docstring states `"a no-op (zero queries) for an empty names"`. Every clause checks out.

---

## Defects Found

All are minor. None blocks implementation; each is a one-line-to-one-clause fix best made before M1 so no RED cycle is spent on it.

### D16. spec.md:315-319 vs spec.md:212-216 — AC-001 attributes a guard requirement to REQ-001 that REQ-001 does not state — Severity: minor

AC-001 closes with *"These bounds hold only if the implementation guards the `Order` fetch, the `LineItem` fetch, and the `bulk_update` exactly as `_process_outbound_rows` does … — REQ-RACKBATCH-001 requires the same guard structure in `_process_rack_number_rows`."* acceptance.md:61 repeats it (*"REQ-RACKBATCH-001이 이 가드 구조를 요구한다"*). REQ-001's actual text is *"at most one `Order` lookup, one `LineItem` lookup, and one write operation, regardless of how many dedup keys the request carries"* — **"at most one" is satisfied by exactly one**, so an unconditional `Order` fetch on an empty batch does not violate REQ-001, yet it breaks the `<= 2` bound. The normative requirement for "zero queries when there is nothing to look up" exists only in 솔루션 개요 step 3 (spec.md:52, :54-55, :60) and in the AC itself. Low consequence: the `<= 2` assertion is in AC-001 and will fail loudly, so the implementation is still held. Fix: add "and shall issue none of the three when the batch contains nothing to look up" to REQ-001, or reword the AC's attribution.

### D17. spec.md:392-394 / acceptance.md:225-227 / plan.md:220-221 — AC-011 (a)'s SET-clause assertion is over-strict as literally written and will fail a correct implementation — Severity: minor

The clause is *"the emitted `UPDATE` statement's `SET` clause shall reference the `rack_number` column and no other `LineItem` column"*; acceptance.md:225-227 is equivalent (*"SET 절이 참조하는 컬럼이 `rack_number` 하나뿐"*). Django 5.1.6's `bulk_update` renders `UPDATE … SET "rack_number" = CASE WHEN "id" = %s THEN %s … END WHERE "id" IN (…)` — the `id` column is referenced **inside** the SET clause by every `When`. A tester implementing the sentence literally (e.g. scanning the SET substring for `LineItem` column names) produces a test that fails against the intended implementation. The discrimination direction is preserved — it fails closed and is visible immediately in M4 — and the intended assertion is obvious, but as written the AC is not binary-testable without reinterpretation. Fix: scope the clause to the **assigned** columns (the left-hand sides of the SET assignments), e.g. *"the only column assigned in the SET clause shall be `rack_number`"*, and keep the concrete negative examples (`shipped_quantity`, `logistics_status`) that acceptance.md:226-227 already supplies.

### D18. spec.md:366-377 and :387-398 vs acceptance.md:24, :167-184, :208-232 — spec.md states AC-011 and AC-012 at endpoint scope while acceptance.md pins both to direct function calls — Severity: minor

acceptance.md:24 declares *"AC-RACKBATCH-001/003/009/011/012는 `[함수]`"*, and its bodies match: AC-012's Then is *"예외가 호출자에게 전파된다"* (:179, no HTTP), AC-011's When is *"`_process_rack_number_rows`를 호출해 … `CaptureQueriesContext`로 감싼다"* (:222-223). spec.md contradicts both: AC-012 says *"the system shall respond with HTTP 500 and a query issued after the request completes"* (:369-371) and AC-011 says *"around a successful upload"* / *"before and after a successful upload"* (:392, :397). A tester following spec.md writes view-level tests; one following acceptance.md writes function-level tests. Both readings remain discriminating for their REQs, so this is a documentation-consistency defect rather than a verification defect — but it is the same class as iteration-2 D11, which the revision otherwise closed. Fix: bring spec.md's AC-011/AC-012 wording to function scope (or add the scope marker to spec.md as acceptance.md:16-18 now presumes it does not have).

### D19. spec.md:372-373 — AC-012's stated mechanism is inaccurate for the environment the test runs in — Severity: minor

*"if `transaction.atomic()` were removed, the `bulk_update`'s write would not be rolled back by the later exception (Django auto-commits outside an explicit atomic block)"*. Under `pytest.mark.django_db` the whole test already runs inside a transaction, so nothing auto-commits; the write simply stays uncommitted-but-visible in the test's own transaction until teardown rolls it back. The **observable outcome the AC asserts is unaffected** — the post-call read still sees the change when the inner atomic is absent, so the AC discriminates exactly as claimed — but the parenthetical explains it by a mechanism that does not apply here, and acceptance.md:182-184 repeats the same framing. Fix: replace the parenthetical with "no savepoint is unwound, so the executed UPDATE remains visible to the subsequent read".

### D20. acceptance.md:24 vs :108 / :248, and plan.md:132 vs :253 — two internal scope/placement contradictions — Severity: minor

(a) acceptance.md:24 assigns `[함수]` to AC-001/003/009/011/012 and `[뷰]` to *"나머지"*, which puts AC-007 at `[뷰]`; but AC-007's own heading (:108) and the DoD row (:248) say `[뷰 또는 함수]`, and acceptance.md:260 lists REQ-005 as *"005(선택 가능)"*. Leaving the layer optional is defensible — the fixture discriminates at either level — but three statements about the same AC should not disagree.
(b) spec.md:196 and plan.md:132 place the migrated `@MX:WARN`/`@MX:REASON` *above* the new function (`"새 함수 위로"`); the mx_plan target column (plan.md:253) places it *inside*, at the judgement loop. Both name the correct function; only the anchor line differs. Pick one so the M2 reviewer's checklist item (plan.md:244) is unambiguous.

### D21. plan.md:188-191 — the tie-break test technique is attributed to a reference test that does not use it — Severity: minor

*"`test_spec_015.py:1166-1186`(`test_duplicate_order_names_resolve_to_the_lowest_pk_order`)와 동일한 기법 — 같은 `name`의 Order 2건을 만들되 **낮은 `pk`가 나중에 생성되도록** 하고"*. The cited test creates `first` then `second` (`:1177-1178`), i.e. in ascending pk order, and does **not** invert pk against creation order. The inversion is SPEC-ORDER-017's own strengthening — spec.md:326-328 and acceptance.md:80-82 require the lower-`pk` Order to be created later, which needs explicit `pk`/`id` assignment in the fixture. The requirement is implementable and strictly better than the reference; only the "동일한 기법" attribution is wrong, and the extra fixture work it implies is not flagged anywhere. Fix: say "the same technique, strengthened — the reference creates the orders in pk order, so this fixture must additionally assign pks explicitly to invert pk against creation order".

**Observation (not a defect)**: moving `dedup_map` construction inside the extracted function moves it inside the existing `try/except Exception` (dedup is currently at `:2198-2212`, the `try` opens at `:2216`). A dedup-stage exception changes from an unhandled propagation to a JSON 500 body. No test pins it and both are 500-class, so it is not a regression against the 15 characterization tests — but it is an unstated consequence of 설계 결정 H worth one sentence in plan.md's MODIFY row.

---

## Chain-of-Verification Pass

Second-look findings — the second pass produced D16, D17 and D21; the first pass had accepted all three areas.

- *Did I actually read every REQ and AC entry, or skim after the first few?* Re-read all 15 REQs and all 12 ACs individually for the MP-2 re-classification. The second pass is what produced **D16**: on the first pass AC-001 was accepted because its three derivations are arithmetically correct; only re-reading REQ-001's text *beside* the AC's closing attribution revealed that "at most one" does not entail "zero when empty".
- *Did I check REQ/AC sequencing end-to-end, not spot-check?* Machine-verified with `grep -o … | sort | uniq -c` over both ID families in spec.md, cross-checked against the 12 acceptance.md headings and against both traceability tables. The AC 11→12 growth introduced no renumbering and no gap.
- *Did I verify traceability for every REQ, not sample?* Yes — all 15 rows of spec.md:407-421 against all 15 rows of acceptance.md:281-295 against each of the 12 `Traces:` lines in both documents; the pairwise diff is empty. I then re-derived the DoD table's existing-test claims from source rather than trusting them: `test_spec_013.py:615` (wrong extension 400), `:620/:637/:649` (three 422 paths), `:729` (last-row-wins), `:748` (multi-LineItem), `:836` (401), `:842` (recompute not called) — all six say what acceptance.md:246-255 claims. The three REQs the SPEC *declines* to credit to existing tests (005 via `:809`, 007 via `:467`, 008 via `:664`) were also re-opened and the SPEC's reasoning for excluding each is correct.
- *Did I check Exclusions for specificity, not just presence?* Yes. All seven entries (spec.md:431-445) name concrete artefacts — response schema fields, `select_for_update`, progress UI / axios timeout, migrations, `parse_rack_number_excel`, `ConfirmOrderView`, and the new "no service class / manager / separate module" boundary on 설계 결정 H. CN-2 passes: the 7th exclusion constrains the new decision rather than conflicting with it (it explicitly permits the one extracted function while forbidding further layers), and the count 7 is consistent in acceptance.md:273 and plan.md:277.
- *Did I look for contradictions between requirements, not just within them?* Yes, pairwise across all five modules. REQ-001 (query bound) vs REQ-013 (atomicity) — compatible, the savepoint pair is inside the bound. REQ-005 (per-row skip counting) vs REQ-003 (last-row-wins dedup) — compatible, and consistent with the live `(None, idx)` keying at `:2205-2212`. REQ-006 (never reject on 2+ matches) vs the reference rejection at `:2582-2594` — correctly opposed and correctly excluded from inheritance. REQ-015 (unhandled → 500) vs REQ-009/010/011 — REQ-015 carves them out explicitly. REQ-014 (write scope) vs REQ-013 — compatible. REQ-012 (never recompute) vs REQ-006 (update every match) — compatible. No contradiction between requirements. The contradictions I did find are between *documents* and within *acceptance.md's own scope table* (D18, D20).
- *Did I re-verify only the revision's own claims, or actually re-derive?* Re-derived. The bounds were recomputed from the guard structure rather than compared to the cited reference; the D4-R and D12 discrimination arguments were re-run against the live keying and against Django's transaction semantics; the D7-R assertion was checked against Django 5.1.6's actual `bulk_update` SQL shape, which is what produced **D17**.

Sections re-read in full on pass 2: spec.md 요구사항 (:204-286), spec.md ACCEPTANCE CRITERIA (:290-425), spec.md 설계 결정 H (:162-202), acceptance.md 전체 (:11-300), plan.md 파일별 변경 계획 (:85-95), 기술적 접근 (:97-232), 리스크 (:234-246) and mx_plan (:248-260).

Citations verified at source this iteration (the added, moved and retightened set named in the audit scope, plus everything the new AC-012 / 설계 결정 H depend on): `purchase_order_views.py:47`, `:2177`, `:2180-2196`, `:2198-2212`, `:2205-2212`, `:2216-2261`, `:2218-2226`, `:2227`, `:2403`, `:2415-2422`, `:2423`, `:2524-2538`, `:2533`, `:2549-2558`, `:2550`, `:2582-2594`, `:2701-2704`, `:2812-2829`, `:3021`, `:3194`, `:3220`; `models.py` LineItem field block (all seven AC-011 (b) fields present); `test_spec_015.py:1104-1121`, `:1118-1121`, `:1128-1131`, `:1143-1147`, `:1149-1153`, `:1151`, `:1155-1157`, `:1166-1186`; `test_spec_013.py:76-79`, `:467`, `:475`, `:505`, `:607`, `:615`, `:620`, `:637`, `:649`, `:664-678`, `:729`, `:748`, `:766`, `:784-808`, `:809-834`, `:836`, `:842`. **All resolve and say what the documents claim**, with the single exception of the technique attribution in D21. No fabricated citation was found. The open-ended form `:3021-` (spec.md:178, :457, plan.md:286) is imprecise but resolves correctly.

---

## Recommendation

**PASS.** Rationale, with evidence per must-pass criterion:

1. **MP-1** — machine-verified: REQ 001…015 and AC 001…012 each appear exactly once in spec.md, matched by 12 headings and two identical 15-row traceability tables in acceptance.md. The AC 11→12 growth caused no renumbering.
2. **MP-2** — all 15 REQs and 12 ACs re-classified individually; every label matches its sentence structure, including the new AC-012 (`If … then`, spec.md:366-372) and the rewritten REQ-012 (Ubiquitous, spec.md:265).
3. **MP-3** — six required frontmatter fields present and correctly typed (spec.md:2-10), with all four sibling documents synchronized at v1.0.2 and spec-compact.md verified non-stale.
4. **MP-4** — N/A, single-stack SPEC (spec.md:67-68, Exclusions :436-437).

Every defect the prior two iterations raised is genuinely closed, not relabelled. The three that mattered most were each re-derived from first principles rather than accepted on the author's account: the query bounds are now correct **for this function's own query shape** and the all-unmatched fixture is pinned to the absent-`Order.name` case so the `LineItem` fetch provably cannot fire (D2/D2b); the blank-identifier rows now share a SKU, which is the only configuration under which a `(None, sku)` implementation diverges from a correct `(None, idx)` one (D4-R); the atomicity fault is injected after the `UPDATE` has executed inside the still-open block, which is the only injection point that can fail an implementation missing `transaction.atomic()` (D12). The newly introduced 설계 결정 H is well-formed as normative content — dedup ownership, the single-caller constraint, and the `@MX:WARN` migration all have explicit homes, the cited precedent (`_process_force_outbound_rows`, single caller at `:3220`) is real, and the extraction does not disturb any of the 15 behaviours pinned by `test_spec_013.py`.

**Blocking: none.** **Acceptable to carry into implementation, in this order of priority:**

1. **D17 first** — it is the only defect that will produce a confusing RED. One clause in spec.md:392-394 / acceptance.md:225-227 / plan.md:220-221: scope the SET-clause assertion to the columns **assigned**, not the columns referenced, so `CASE WHEN "id" = …` does not trip it.
2. **D18** — align spec.md's AC-011/AC-012 wording with acceptance.md's `[함수]` scope (or add scope markers to spec.md), so the implementer does not write both a view-level and a function-level version of the same test.
3. **D16** — one clause on REQ-001 ("and shall issue none of the three when there is nothing to look up"), so the `<= 2` bound rests on a requirement rather than only on the AC that measures it.
4. **D20, D21, D19** — pure documentation consistency; fix opportunistically during M5 doc sync. D20(b) should be settled before M2 so plan.md:244's review checklist item is unambiguous about where the migrated `@MX:WARN` belongs.

Citation integrity is the strongest it has been across the three iterations: every pointer opened this iteration resolves, the four D2c ranges were genuinely split and are individually correct, and the two new SPEC-ORDER-016 references (`:3021`, `:3220`) verify — including the single-caller claim attached to them.
