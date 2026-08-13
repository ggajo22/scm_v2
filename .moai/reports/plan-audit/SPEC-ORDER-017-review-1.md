# SPEC Review Report: SPEC-ORDER-017
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.69

Reasoning context ignored per M1 Context Isolation. This audit used only the files in
`.moai/specs/SPEC-ORDER-017/` plus the source files they cite, read independently.

---

## Priority Focus Result — Independent `file:line` Citation Verification

Every `file:line` citation in `spec.md`, `plan.md`, `research.md`, `acceptance.md` and
`spec-compact.md` was opened at the cited location. **No fabricated citation was found.**
All cited constructs exist and say what the documents claim.

### Verified accurate (opened and matched)

`backend/order/purchase_order_views.py`
- `:841` `class ConfirmOrderView(APIView)` — MATCH
- `:918-929` per-item `LineItem.objects.filter(sku=sku).exclude(...).select_for_update()` — MATCH (see D10a)
- `:1229` `UploadDailyReviewView`, `:1723` `UploadVendorShipmentView`, `:1788` `UploadWarehouseReceiptView` — all MATCH
- `:2163` `class UploadRackNumberView`, `:2164-2175` docstring, `:2180-2266` `post()` — MATCH
- `:2185-2190` `.xlsx` guard → 400; `:2193-2194` `parse_rack_number_excel`; `:2195-2196` `ValueError` → 422 — MATCH
- `:2198-2212` / `:2205-2212` `dedup_map` construction with `(None, idx)` blank-row keying — MATCH (see D10b)
- `:2217` `transaction.atomic()`, `:2227` `for row in dedup_map.values()` — MATCH
- `:2243` `Order.objects.filter(name=order_name).first()`; `:2249-2250` `LineItem...exists()`; `:2255` `line_items.update(...)` — MATCH (3 queries/key confirmed)
- `:2257-2261` 500 path; `:2263-2266` `{matched_count, skipped_count}` 200 — MATCH
- `:2403-2414` `@MX:NOTE` batching/cost model (8 rows ≈ 24 round trips, 50 ≈ 150, ~130ms) — MATCH, quoted content accurate
- `:2415-2422` `@MX:WARN`/`@MX:REASON`; REASON literally says "carried over from UploadRackNumberView (which updates rack_number lock-free the same way)" — MATCH
- `:2423-2714` `_process_outbound_rows` — MATCH (def at 2423, return ends 2714)
- `:2518` atomic; `:2524-2531` tie-break rationale comment; `:2532-2538` `name__in` + `order_by("pk")` + `setdefault`; `:2540-2547` cross-product comment; `:2549-2558` `order_id__in` + `sku__in` grouping — all MATCH
- `:2582-2594` `if len(candidates) != 1:` → `multiple_line_items` rejection — MATCH (this is the non-inherited branch, correctly identified)
- `:2701-2704` `bulk_update(to_update, ["shipped_quantity","shipped_at","logistics_status"])` — MATCH
- `:2812-2829` `_resolve_orders_by_name` — MATCH; the code block quoted in research.md §2.1 is verbatim-correct

`backend/order/models.py`
- `:92-111` `Order.Meta`; `:100-109` `@MX:NOTE` naming UploadRackNumberView/SPEC-ORDER-015 as the reason for the index; `:110` `models.Index(fields=["name"])` — MATCH
- `:152-229` `LineItem`; `:169` `order = models.ForeignKey(Order, ...)`; `:169-222` field block; `:228` `unique_together = [("order","shopify_line_item_id","sku")]` — MATCH
- Negative claim "LineItem has no `save()` override and no `auto_now`/`auto_now_add`" — VERIFIED TRUE (`Order` has them at `:89-90`; `LineItem` has none)

`backend/order/excel_utils.py`
- `:994` `def parse_rack_number_excel`; `:1018-1026` empty-string-preserved rule — MATCH. The sentence quoted in research.md §4 is verbatim at `:1024-1026`

`backend/order/tests/test_spec_013.py`
- `:607-856` `TestUploadRackNumberView`; all 15 line numbers in research.md §4 table (615, 620, 637, 649, 664, 680, 703, 714, 729, 748, 766, 784, 809, 836, 842) — EVERY ONE MATCHES the named test
- Count is exactly 15 — VERIFIED
- `:748-764` `test_upload_multiple_lineitems_matching_key_all_updated`; the Python excerpt in research.md §3 is verbatim-accurate
- `:842-855` `test_upload_never_calls_recompute_order_aggregates` with `patch(...)` + `spy.assert_not_called()` — MATCH

`backend/order/tests/test_spec_015.py`
- `:1-24` module docstring with `Coverage targets:` T1–T8 — MATCH
- `:34` `from django.test.utils import CaptureQueriesContext` — MATCH
- `:452` `test_processing_is_atomic_so_a_mid_run_failure_rolls_everything_back` — MATCH
- "T8 — batched DB access" section label — MATCH at `:1093`
- `:1104-1115` `_seed_outbound_groups`; `:1118-1121` `_count_queries`; `:1124-1157` `TestOutboundQueryCountIsIndependentOfRowCount`; `:1133-1141` (2-vs-10 equality); `:1143-1147` (`<= 6`); `:1149-1153` (`<= 4`); `:1155-1157` (`<= 2`); `:1166-1186` `test_duplicate_order_names_resolve_to_the_lowest_pk_order` — ALL MATCH, including the exact numeric bounds
- `:1104-1199` range covers both techniques — MATCH

Frontend
- `SearchTab.tsx:93-103` `handleUploadChange` posting `FormData` — MATCH
- `SearchTab.tsx:130-138` button with `disabled={uploadMutation.isPending}` and `'업로드 중...' / 'Excel 업로드'` — MATCH
- `useRackNumberQueries.ts:53-67` `useUploadRackNumber` invalidating `ORDER_DETAIL_QUERY_KEY` + toast — MATCH
- `rackNumberApi.ts:48` `uploadRackNumber` — MATCH
- `lib/axios.ts` — VERIFIED: instance sets only `baseURL` + `Content-Type`; repo-wide grep for `timeout` under `frontend/src` returns zero matches

Other negative claims independently re-verified
- No `post_save`/`pre_save`/`receiver`/`signals` anywhere under `backend/order/` — TRUE (grep: no matches)
- `test_spec_013.py` has no query-count test — TRUE (`CaptureQueriesContext` appears in 6 test files; `test_spec_013.py` is not one)
- `backend/order/tests/test_spec_017.py` does not yet exist — TRUE (so the `[NEW]` marker is correct)
- `plan.md` claim `quality.yaml development_mode: "tdd"` — TRUE (`quality.yaml:4`)

**Conclusion on the priority focus: this SPEC set is citation-clean.** The failures below are
specification-quality failures, not citation fabrication.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: REQ-RACKBATCH-001 … 014, no gaps, no duplicates,
  uniform 3-digit zero-padding. Machine-counted: each of the 14 bold definitions occurs
  exactly once (spec.md:140–206). Module partition 001-002 / 003-005 / 006-007 / 008-012 /
  013-014 accounts for all 14. AC IDs likewise 001–010, each defined once (spec.md:216–266).

- **[FAIL] MP-2 EARS format compliance**: 7 of 10 acceptance criteria and 1 of 14 requirements
  carry a declared EARS pattern label that contradicts the sentence structure actually used.
  MP-2 explicitly lists "Given/When/Then test scenarios mislabeled as EARS" as a failure mode.
  Concrete evidence:
  - spec.md:167 `**REQ-RACKBATCH-006** (Ubiquitous): "When a dedup key's `(order_name, sku)` pair
    matches one or more LineItems …, the system shall …"` — a trigger-led Event-driven sentence
    declared Ubiquitous.
  - spec.md:216 `**AC-RACKBATCH-001** (Ubiquitous) … "When processing a 2-key batch and,
    separately, a 10-key batch …"` — Event-driven text, Ubiquitous label.
  - spec.md:222 `**AC-RACKBATCH-002** (Ubiquitous) … "Given an Order with two LineItems …, when a
    single upload row targets …"` — Given/When scenario, Ubiquitous label.
  - spec.md:232 `**AC-RACKBATCH-004** (Unwanted) … "Given a LineItem whose current `rack_number`
    is `"A-01"`, when an upload row targets it …"` — no `If … then` construct anywhere; Unwanted
    label is unsupported.
  - spec.md:237 `**AC-RACKBATCH-005** (Unwanted) … "Given a corrupted `.xlsx` file …, when the file
    is uploaded …"` — same defect.
  - spec.md:245 `**AC-RACKBATCH-007** (State-Driven) … "Given one row with a blank order-identifier
    cell …, when the file is processed …"` — State-driven requires `While [condition]`; the text
    contains no `While`.
  - spec.md:251 `**AC-RACKBATCH-008** (Ubiquitous) … "When a rack-number upload request transitions
    a LineItem's `rack_number` …"` — Event-driven text, Ubiquitous label.
  - spec.md:256 `**AC-RACKBATCH-009** (Unwanted) … "Given a batch with two matching keys, when the
    write step raises an exception …"` — Given/When scenario, Unwanted label.
  Correctly labelled for contrast: AC-RACKBATCH-003 (spec.md:227, Event-Driven ✔),
  AC-RACKBATCH-006 (spec.md:241, Event-Driven ✔), AC-RACKBATCH-010 (spec.md:262, Ubiquitous ✔),
  REQ-009/010/011 (spec.md:184–192, `If … then …` Unwanted ✔).
  The pattern label is a normative declaration in this SPEC's own format; a 70% mismatch rate on
  ACs is a systematic classification defect, not a typo.

- **[PASS] MP-3 YAML frontmatter validity**: all six required fields present with correct types —
  `id: SPEC-ORDER-017` (spec.md:2, matches `SPEC-{DOMAIN}-{NUM}`), `version: 1.0.0` (:3),
  `status: Planned` (:4), `created_at: 2026-08-12` (:5, ISO-8601), `priority: High` (:8),
  `labels: [order, rack-number, performance, batching]` (:10, array). Sibling documents
  (`plan.md:1-7`, `research.md:1-7`, `acceptance.md:1-7`, `spec-compact.md:1-7`) carry consistent
  `id`/`version`/`status`/`updated`. See D9 for a non-blocking note on the `status` vocabulary.

- **[N/A] MP-4 Section 22 language neutrality**: N/A — single-stack SPEC. Scope is one Django
  view (`backend/order/purchase_order_views.py`) plus pytest; spec.md:53-54 and Exclusions
  (spec.md:298-299) explicitly exclude all frontend change. No multi-language tooling claim is
  made anywhere, so no 16-language enumeration is owed.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in two-three requirements | Most REQs are single-interpretation (spec.md:140-148, 173-206). Ambiguity is localized: REQ-004 normatively defers to an ORM call chain (spec.md:158-159), AC-001 leaves its own threshold undefined (spec.md:218-220), AC-009's second clause has unbounded scope (spec.md:258-260). |
| Completeness | 0.75 | 0.75 — one non-critical gap; frontmatter complete | HISTORY (:15-19), WHY/문제 정의 (:23-35), WHAT/솔루션 개요+범위 (:37-72), 설계 결정 (:74-132), REQUIREMENTS (:134-206), ACCEPTANCE CRITERIA (:210-287), Exclusions with 6 specific entries (:291-303), 관련 SPEC (:305-315) all present. Gap: the 500 error path is declared preserved (spec.md:50-51) and asserted in acceptance.md:121 but has no REQ (D6). |
| Testability | 0.50 | 0.50 — several ACs require judgment calls / contain weasel words | AC-001 "a **small** fixed bound established at implementation time" (spec.md:218-220) is a self-certifying threshold; AC-007 cannot fail a merging implementation (spec.md:245-249, only one blank row in the Given); AC-009's universal clause is unbounded (spec.md:258-260); REQ-007's only claimed test bucket contains no such test (acceptance.md:144-145 vs test_spec_013.py:607-855). |
| Traceability | 0.75 | 0.75 — ID-level complete, verification-level broken in one place | ID-level is perfect and independently re-derived: all 14 REQs appear in the mapping table (spec.md:270-285), duplicated identically in acceptance.md:155-170; each AC's `Traces:` line agrees with the table; zero orphan ACs; zero uncovered REQs. Downgraded because the Definition-of-Done test allocation (acceptance.md:139-145) asserts coverage that does not exist for REQ-007 (D3) and is non-discriminating for REQ-005 (D4). |

---

## Defects Found

**D1. spec.md:167, 216, 222, 232, 237, 245, 251, 256 — EARS pattern labels contradict sentence
structure in 7/10 ACs and REQ-RACKBATCH-006 — Severity: critical (MP-2)**
Detailed per-item evidence is in the MP-2 block above. Three ACs use `Given …, when …, the system
shall …` while declaring `Unwanted`, whose canonical form is `If [undesired condition], then the
system shall [response]`; one declares `State-Driven` with no `While` clause; three declare
`Ubiquitous` while opening with a `When` trigger.

**D2. spec.md:216-220 / acceptance.md:33-37 — AC-RACKBATCH-001 lets the implementer set its own
pass bar — Severity: major**
"that number shall not exceed **a small fixed bound established at implementation time by direct
measurement**". "Small" is a weasel word (AC-3 violation) and the bound is unknowable at review
time, so the criterion is not binary-testable (AC-2 violation). The comparison SPEC did not do
this: `test_spec_015.py:1147/1153/1157` states concrete literals (`<= 6`, `<= 4`, `<= 2`) that
were reviewable before implementation. The 2-key/10-key equality half of the AC is sound and
should be kept; the deferred-absolute-bound half must be replaced with a number or deleted.

**D3. acceptance.md:144-145 — Definition-of-Done claims REQ-RACKBATCH-007 coverage that does not
exist — Severity: major**
acceptance.md:144-145 states the existing 15 tests in
`test_spec_013.py::TestUploadRackNumberView` cover "003, 005, 006, 007, 008, 009, 010, 011, 012".
I enumerated all 15 tests (test_spec_013.py:615, 620, 637, 649, 664, 680, 703, 714, 729, 748, 766,
784, 809, 836, 842) and grepped the class body: **none of them uploads an empty-string
`rack_number` against a LineItem that currently holds a value.** The only empty-string assertions
inside the class are `assert li.rack_number == ""` at `:727` and `:782`, both asserting an
*untouched default*, not a clear operation. The genuine empty-string test
(`test_empty_rack_number_value_preserved_as_empty_string`, `test_spec_013.py:467`) lives in
`TestParseRackNumberExcel` and is parser-level only — it never reaches the view. Meanwhile the
`test_spec_017.py` bucket (acceptance.md:142-143) lists only 001, 002, 004, 013, 014. Net effect:
**REQ-RACKBATCH-007 / AC-RACKBATCH-004 has no test assigned in either bucket**, even though
plan.md:125 (risk R2) identifies the falsy-filter regression as a live hazard and claims it is
"AC-RACKBATCH-004로 pin"-ned.

**D4. spec.md:245-249 / acceptance.md:82-90 — AC-RACKBATCH-007 cannot fail the implementation it
claims to guard — Severity: major**
REQ-RACKBATCH-005 (spec.md:161-164) requires that a blank-identifier row "shall not merge that row
with **any other blank-identifier row**". AC-RACKBATCH-007's Given supplies exactly **one** blank
row plus one valid row, then its Then asserts "빈 식별자 행이 다른 빈 식별자 행이나 정상 행과 병합되어
카운트가 누락되지 않는다" — an assertion the fixture makes unobservable. With a single blank row,
`skipped_count == 1` holds identically for a correct `(None, idx)` implementation and for a broken
`(None, sku)`-merging implementation. The existing test acceptance.md routes REQ-005 to
(`test_spec_013.py:809-834`) has the same shape: exactly one blank row at `:822`. Fix: the Given
must contain **two or more** blank-identifier rows and assert `skipped_count == 2`.

**D5. spec.md:158-159 — REQ-RACKBATCH-004 encodes implementation, not behaviour — Severity: major**
"…shall select the one with the lowest `pk`, **reproducing the tie-break the existing
`.filter(name=X).first()` call currently produces**." A normative requirement must not depend on a
Django ORM call chain; the call is precisely the code being deleted by this SPEC (verified live at
`purchase_order_views.py:2243`). The observable rule ("lowest `pk` wins on name collision") is
already stated in the same sentence and is sufficient. spec.md:56-57 asserts "요구사항 본문(EARS)은
관측 가능한 동작(WHAT)만 규정한다" — this REQ breaks the document's own stated rule. Same class,
lower severity: REQ-RACKBATCH-012 (spec.md:194-196) names the internal symbol
`_recompute_order_aggregates`.

**D6. spec.md:50-51, 256-260 vs acceptance.md:121 — the HTTP 500 path is asserted but never
required — Severity: major**
spec.md:50-51 lists 500 among the status codes to preserve, and acceptance.md:121 asserts
"응답은 500이다" as a Then. No REQ-RACKBATCH-XXX mandates it: REQ-009/010/011 cover 400/422/401
only, and REQ-013 mandates atomicity without prescribing a status. Additionally, **spec.md's own
AC-RACKBATCH-009 (:256-260) omits the 500 assertion that acceptance.md:121 adds** — the two
documents disagree on the content of the same AC ID, immediately under acceptance.md:14-15's
`[HARD]` claim of complete agreement with spec.md.

**D7. spec.md:256-260 — AC-RACKBATCH-009 is a compound criterion whose second half is
unverifiable as scoped — Severity: major**
The Given/When fixture describes a failure injection, but the trailing clause — "and no field
other than `rack_number` shall ever appear in the diff of **any successfully processed request**" —
is universally quantified over all requests and is not reachable from the stated fixture. This
dangling clause is the **only** coverage REQ-RACKBATCH-014 (write-scope limitation) receives
(spec.md:285, acceptance.md:169). Split it into its own AC with a concrete fixture (e.g. snapshot
all LineItem fields before/after one successful two-key upload).

**D8. purchase_order_views.py:2218-2226 not acknowledged anywhere in the SPEC set — Severity:
major**
An existing `@MX:WARN` + `@MX:REASON` block documenting 결정 E sits **inside** the exact
`transaction.atomic()` loop this SPEC rewrites (verified: `@MX:WARN` at `:2218`, `@MX:REASON` at
`:2223`, immediately above `for row in dedup_map.values():` at `:2227`). research.md §1 step 3
walks `:2217` straight to `:2227` and never mentions it; plan.md's MX plan (`:133-138`) addresses
only the *other* `@MX:WARN` at `:2415-2422`, which belongs to `_process_outbound_rows` and is not
being touched. A rewrite of `:2217-2261` will delete this tag by default. Per mx-tag-protocol,
WARN may be removed only when the danger is eliminated — the 2+-match condition it documents is
explicitly *preserved* by REQ-RACKBATCH-006, so the tag must survive. plan.md must state whether
it is retained in place or merged into the planned 결정-A-non-inheritance `@MX:NOTE`.

**D9. spec.md:4 — `status: Planned` is outside the canonical status vocabulary — Severity: minor**
FC-3 expects `draft | active | implemented | deprecated`. The project's own completed SPECs use
lowercase `completed` (`.moai/specs/SPEC-ORDER-016/spec.md:4`, `SPEC-ORDER-015/spec.md:4`), so
`Planned` is also inconsistent in casing with the project's convention. Not treated as an MP-3
failure since the field is present and correctly typed.

**D10. Citation pointer imprecision (4 items, all resolve within a few lines; none fabricated) —
Severity: minor**
- (a) research.md:216-219 cites `:918-929` for the locked per-item lookup; the
  `select_for_update()` query is `:918-925`, while `:927-929` is a *separate, unlocked*
  `.exists()` query. spec.md:116 repeats the range.
- (b) research.md:25 says "`:2198-2211`의 주석"; the comment block is `:2198-2204` and
  `:2205-2211` is executable code.
- (c) research.md:79 says "문서화 주석 `:2813-2823`"; the docstring runs `:2813-2824`.
- (d) spec.md:105 attributes the docstring to `excel_utils.py:994`; `:994` is the `def` line and
  the docstring is `:995-1030` (the specific claim cited, `:1018-1026`, is exact).

---

## Chain-of-Verification Pass

Second-look findings — **three defects were added on the second pass; the first pass was not
sufficient.**

- *Did I read every REQ entry or skim after the first few?* Re-read all 14 individually. The
  second pass is what caught **D5** (REQ-004's `.filter(name=X).first()` clause) and the
  REQ-006 mislabel that became part of **D1** — both are in the middle of the list, exactly where
  skimming would have missed them.
- *Did I check REQ sequencing end-to-end?* Yes, machine-verified rather than spot-checked: each of
  the 14 bold REQ tokens and 10 bold AC tokens occurs exactly once (`grep -o … | sort | uniq -c`).
  MP-1 stands.
- *Did I verify traceability for every REQ, not sample?* Yes. All 14 rows of spec.md:270-285 were
  cross-checked against each AC's own `Traces:` line and against the duplicate table at
  acceptance.md:155-170. ID-level traceability is genuinely complete. The second pass then asked
  the harder question — *does the test allocation behind those IDs exist?* — which produced **D3**
  (REQ-007 has no test in either bucket) and **D4** (AC-007 is non-discriminating). Neither is
  visible from the traceability table alone.
- *Did I check Exclusions for specificity, not just presence?* Yes. All six entries at
  spec.md:293-303 name concrete artefacts (response schema fields, `select_for_update`, progress
  UI / axios timeout, migrations, `parse_rack_number_excel`, `ConfirmOrderView`) and each is
  consistent with an included requirement or design decision. CN-2 passes.
- *Did I look for contradictions between requirements, not just within them?* Yes, pairwise across
  the five modules. REQ-001 ("at most one write operation") vs REQ-013 (atomicity) — compatible.
  REQ-005 (per-row skipped counting) vs REQ-003 (last-row-wins dedup) — compatible, and confirmed
  against the live `(None, idx)` keying at `purchase_order_views.py:2205-2212`. REQ-006 vs the
  non-inherited rejection at `:2582-2594` — correctly opposed and correctly flagged by the SPEC.
  The cross-document contradiction in **D6** (spec.md AC-009 vs acceptance.md AC-009) is the only
  one found, and it surfaced only because the second pass diffed the two AC bodies rather than
  just their `Traces:` lines.
- *Re-verified citations rather than trusting the first read*: the numeric bounds in
  `test_spec_015.py` (`<= 6` / `<= 4` / `<= 2`), the 15-test count, and the `lib/axios.ts`
  no-timeout claim were each re-opened. All held.

Sections re-read in full on pass 2: spec.md 요구사항 (134-206), spec.md ACCEPTANCE CRITERIA
(210-287), acceptance.md 품질 게이트 (137-151), plan.md MX 태그 계획 (131-141),
`test_spec_013.py:607-856`.

---

## Regression Check

Not applicable — iteration 1. No prior report exists for SPEC-ORDER-017 in
`.moai/reports/plan-audit/`.

---

## Recommendation

FAIL. MP-2 fails outright (D1), and five further major defects (D2, D3, D4, D6, D7) would each
survive into implementation as an untested or self-certifying contract. Required fixes for
manager-spec, in dependency order:

1. **Fix every EARS label (D1, blocks MP-2).** For each of spec.md:167, 216, 222, 232, 237, 245,
   251, 256 either relabel to the pattern the sentence actually uses, or rewrite the sentence to
   the declared pattern. Recommended: relabel REQ-006, AC-001, AC-002, AC-008 to `(Event-Driven)`;
   rewrite AC-004, AC-005, AC-009 as true `Unwanted` form (`If [condition], then the system shall
   [response]`) or relabel them `(Event-Driven)`; for AC-007 either rewrite with a leading
   `While a parsed row's order-identifier cell is blank …` or relabel `(Event-Driven)`. Apply the
   identical labels to acceptance.md so the two documents cannot drift.

2. **Give AC-RACKBATCH-001 a real bound (D2).** Replace "a small fixed bound established at
   implementation time by direct measurement" (spec.md:218-220, acceptance.md:33-37) with a
   literal ceiling in the style of `test_spec_015.py:1147` (`<= 6`), or delete the absolute-bound
   clause entirely and let the 2-key/10-key equality plus the skipped-only/empty-batch checks
   carry the AC. Do not leave the threshold for the implementer to choose after the fact.

3. **Assign REQ-RACKBATCH-007 a test (D3).** Correct acceptance.md:144-145 — remove `007` from the
   `test_spec_013.py` bucket, and add to the `test_spec_017.py` bucket at acceptance.md:142-143 a
   new upload-level scenario: LineItem with `rack_number="A-01"`, upload one row with an
   empty-string rack cell, assert `matched_count == 1` and `rack_number == ""`. This is exactly
   AC-RACKBATCH-004 (spec.md:232-235); it currently has no owner.

4. **Make AC-RACKBATCH-007 discriminating (D4).** Change the Given at spec.md:245-249 and
   acceptance.md:86-90 to at least **two** blank-identifier rows plus one valid row, and assert
   `skipped_count == 2`. Add this scenario to the `test_spec_017.py` bucket (the existing
   `test_spec_013.py:809-834` has only one blank row and cannot be relied on for REQ-005).

5. **Add a REQ for the 500 path, or drop the 500 assertion (D6).** Either add
   REQ-RACKBATCH-015 in Unwanted form ("If processing raises an unexpected error, then the system
   shall respond with HTTP 500 and shall persist no rack_number change") and trace it from
   AC-RACKBATCH-009, or remove "응답은 500이다" from acceptance.md:121. If a REQ is added,
   renumber nothing else — 015 extends the existing sequence and preserves MP-1.

6. **Split AC-RACKBATCH-009 (D7).** Keep the failure-injection scenario for REQ-013. Move the
   write-scope clause into a new AC dedicated to REQ-RACKBATCH-014 with a concrete fixture
   (snapshot every LineItem field before and after one successful two-key upload; assert only
   `rack_number` differs). Update both traceability tables (spec.md:270-285, acceptance.md:155-170).

7. **Account for the in-scope MX tag (D8).** Add a row to plan.md's MX 태그 계획 (:133-138) stating
   that the `@MX:WARN`/`@MX:REASON` at `purchase_order_views.py:2218-2226` is retained (in place or
   folded into the planned 결정-A `@MX:NOTE`), since REQ-RACKBATCH-006 preserves the condition it
   documents. Optionally note it in research.md §1 step 3, which currently jumps `:2217` → `:2227`.

8. **Minor, no re-audit needed (D9, D10).** Align `status:` with the project's lowercase
   vocabulary, and tighten the four line ranges in D10.

Citation integrity requires no action: every `file:line` reference in all five documents was
independently opened and matched. research.md:11-14's claim that all citations were re-verified in
this session is itself accurate.
