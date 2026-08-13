# SPEC Review Report: SPEC-ORDER-017
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.75

Reasoning context ignored per M1 Context Isolation. The author's revision narrative in
`spec.md` HISTORY (:20), `research.md` (:16-19), `plan.md` (:18-24) was read only as document
content subject to audit, never as justification. Every claim below was re-derived from the
documents as they now stand plus the source files they cite, opened independently.

---

## Must-Pass Results (re-run from scratch, nothing inherited from iteration 1)

- **[PASS] MP-1 REQ number consistency**: Machine-verified, not spot-checked.
  `grep -o '\*\*REQ-RACKBATCH-[0-9]*\*\*' spec.md | sort | uniq -c` returns exactly one
  occurrence each of 001…015 — 15 definitions, no gap, no duplicate, uniform 3-digit padding.
  Same check on AC tokens returns exactly one each of 001…011. `acceptance.md` carries 11
  `### AC-RACKBATCH-XXX` headings (`:25, 45, 55, 67, 76, 86, 104, 114, 124, 139, 154`) — the
  same set, presented out of numeric order (005 sits at `:104`, after 007) but complete.
  The new REQ-015 (spec.md:228) and AC-011 (spec.md:301) extend the sequence without
  renumbering, exactly as the iteration-1 recommendation required. No regression.

- **[PASS] MP-2 EARS format compliance**: All 15 REQs and all 11 ACs re-classified
  independently against the five canonical patterns. Every declared label now matches the
  sentence structure actually used:
  - Unwanted, true `If … then …` form: REQ-009 (:199), REQ-010 (:202), REQ-011 (:206),
    REQ-015 (:228 `"If processing … raises an exception …, then the system shall respond with
    HTTP 500"`), AC-005 (:268 `"If an uploaded .xlsx file is corrupted …, then the system
    shall respond with HTTP 422"`), AC-009 (:289 `"If, given a batch with two matching keys,
    the write step raises an exception …, then the system shall respond with HTTP 500"`).
    The three ACs iteration 1 flagged for a `Given …, when …` body under an `Unwanted` label
    were genuinely rewritten into `If … then` form, not merely relabelled.
  - State-Driven, true `While` clause: REQ-005 (:176 `"While a parsed row's order-identifier
    cell is blank"`), AC-007 (:277 `"While two or more parsed rows … carry a blank
    order-identifier cell"`). AC-007's `While` sentence leads; the Given/When fixture follows
    as elaboration.
  - Event-Driven, `When`-triggered: REQ-003 (:168), REQ-004 (:172), REQ-006 (:182),
    AC-001 (:241), AC-002 (:253), AC-003 (:258), AC-004 (:263), AC-006 (:273), AC-008 (:284).
    AC-002/003/004/006 open with a `Given` fixture clause before the `When` trigger; this is
    the same construction iteration 1 explicitly accepted as Event-Driven for AC-003 and
    AC-006, so the treatment is now internally consistent across all six.
  - Ubiquitous, bare `The system shall …`: REQ-001 (:156), REQ-002 (:162), REQ-007 (:188),
    REQ-008 (:195), REQ-012 (:209), REQ-013 (:215), REQ-014 (:219), AC-010 (:295),
    AC-011 (:301). None opens with a trigger.
  D1 is closed. MP-2 passes.

- **[PASS] MP-3 YAML frontmatter validity**: all six required fields present, correctly typed —
  `id: SPEC-ORDER-017` (spec.md:2, matches `SPEC-{DOMAIN}-{NUM}`), `version: 1.0.1` (:3),
  `status: draft` (:4, now inside the FC-3 vocabulary — D9 closed), `created_at: 2026-08-12`
  (:5, ISO-8601), `priority: High` (:8), `labels: [order, rack-number, performance, batching]`
  (:10, array). Sibling documents carry consistent `id`/`version: 1.0.1`/`status: draft`
  (`plan.md:1-7`, `research.md:1-7`, `acceptance.md:1-7`, `spec-compact.md:1-7`). No regression.

- **[N/A] MP-4 Section 22 language neutrality**: N/A — single-stack SPEC. Scope is one Django
  view plus pytest; spec.md:54-55 and Exclusions (:340-341) exclude all frontend change. No
  multi-language tooling claim anywhere, so no 16-language enumeration is owed.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in two-three requirements | REQs are single-interpretation throughout (spec.md:156-231). Residual ambiguity is localized and all inside AC-001: acceptance.md:31 says "전량 미매칭(0건 매칭) 10-키 배치" without saying *how* the keys miss (absent Order vs absent SKU), and the two cases produce different query counts (D2b); acceptance.md:32's "CaptureQueriesContext로 감싸 각 배치를 처리한다" does not say whether "처리" is the HTTP request or an internal call, and the two differ by one query (D2a). AC-011's scope differs between spec.md:301-306 (7 enumerated fields) and acceptance.md:167-169 ("모든 필드") (D11). |
| Completeness | 1.00 | 1.0 — all required sections present, frontmatter complete, exclusions specific | HISTORY (:15-20), WHY/문제 정의 (:24-36), WHAT/솔루션 개요 + 범위 델타 (:38-76), HOW/설계 결정 A–G (:78-146), REQUIREMENTS (:148-231), ACCEPTANCE CRITERIA (:235-329), Exclusions with 6 concrete entries (:333-345), 관련 SPEC (:347-357). The iteration-1 completeness gap (500 path asserted but never required) is closed: 설계 결정 G (:138-146) + REQ-RACKBATCH-015 (:228-231) + AC-009 Traces (:289) now form a complete chain, and spec.md AC-009 (:291-292) and acceptance.md:131 finally state the same 500 assertion. |
| Testability | 0.50 | 0.50 — several ACs require judgment calls or cannot fail a non-compliant implementation | Weasel words are gone (the "small fixed bound established at implementation time" clause is deleted; concrete `<= 6`/`<= 4`/`<= 2` now appear at spec.md:245-247). But five criteria are still not binary-discriminating: AC-001's `<= 2` ceiling is unattainable as scoped (D2a), AC-007's fixture passes identically for the broken implementation it names (D4-R), AC-009 cannot fail an implementation that drops `transaction.atomic()` (D12), AC-011 cannot fail the `bulk_update` field-list widening that plan.md:169 claims it pins (D7-R), AC-010's exact-schema clause cannot fail an added field (D13). |
| Traceability | 0.75 | 0.75 — ID-level complete, verification-level broken in four places | ID-level is perfect and independently re-derived: all 15 REQs appear in the spec.md table (:312-326) and identically in acceptance.md (:212-226); each AC's `Traces:` line was compared one by one against both tables and against the acceptance.md scenario headers — zero orphan ACs, zero uncovered REQs, and the spec.md↔acceptance.md `Traces:` lists agree for all 11 ACs. Downgraded because the per-REQ test table (acceptance.md:178-194) — which now explicitly promises "**판별력 있는** 커버리지가 실제로 존재하는 파일" (:173-176) — makes that promise falsely for REQ-005, REQ-008, REQ-013 and REQ-014. |

---

## Regression Check — iteration 1 defects D1-D10

| # | Status | Evidence |
|---|--------|----------|
| D1 (EARS labels, critical) | **RESOLVED** | See MP-2 above. All 8 flagged items fixed; 4 relabelled, 4 rewritten. Verified item by item. |
| D2 (self-certifying bound, major) | **UNRESOLVED** | Weasel clause removed, but the replacement numbers are transplanted from a measurement context that is not the target's. See D2a/D2b/D2c below. |
| D3 (REQ-007 has no test, major) | **RESOLVED** | acceptance.md:186 moves REQ-007 to the `test_spec_017.py` bucket and states the reason. Independently re-verified: `test_spec_013.py:467 test_empty_rack_number_value_preserved_as_empty_string` sits inside `class TestParseRackNumberExcel` (`:407`), i.e. parser-level and unreachable from the view — the SPEC's claim is correct. plan.md:141-144 and spec.md:74 carry the same allocation. |
| D4 (AC-007 non-discriminating, major) | **UNRESOLVED — same failure mode, new fixture** | Row count raised 1→2, but acceptance.md:95 specifies the two blank rows have *different* SKUs, which restores non-discrimination. See D4-R below. |
| D5 (REQ-004 encodes implementation, major) | **RESOLVED (main clause)** | spec.md:172-174 now reads "shall use exact `Order.name` string equality and, when two or more Orders share that name, shall select the Order with the lowest `pk` among them" — the `.filter(name=X).first()` clause is gone. Sub-item unresolved: REQ-012 (:209-211) still names the internal symbol `_recompute_order_aggregates`; see D14 (minor). |
| D6 (500 asserted but not required, major) | **RESOLVED** | REQ-015 added (spec.md:228-231); spec.md AC-009 (:291-292) now carries the 500 assertion that previously existed only in acceptance.md:131; both trace REQ-013 + REQ-015 identically (spec.md:289, acceptance.md:126). Cross-document disagreement on AC-009 is gone. |
| D7 (AC-009 compound / REQ-014 unverifiable, major) | **PARTIALLY RESOLVED** | The split happened — AC-011 exists (spec.md:301-306, acceptance.md:154-169) and is the sole tracer of REQ-014 in both tables. But the new fixture cannot fail the specific write-scope violation plan.md:169 assigns to it. See D7-R below. |
| D8 (in-scope `@MX:WARN` unacknowledged, major) | **RESOLVED** | Tag re-verified live: `# @MX:WARN:` at `purchase_order_views.py:2218`, `# @MX:REASON:` at `:2223`, block ends `:2226`, `for row in dedup_map.values():` at `:2227` — the SPEC's range `:2218-2226` is exact. It is now acknowledged in research.md §1 step 3 (:32-41), plan.md file table (:65), plan.md mx_plan row (:177, "삭제하지 않는다" with the mx-tag-protocol rationale), plan.md risk R7 (:170), and spec-compact.md:100-101. |
| D9 (`status: Planned`, minor) | **RESOLVED** | spec.md:4 `status: draft`. |
| D10 (4 citation ranges, minor) | **RESOLVED — all four re-opened** | (a) `:918-925` is the `select_for_update()` block (918 `unordered_lis = list(` → 925 `)`), `:927-929` is the separate unlocked `.exists()` inside `if not unordered_lis:` — research.md:240-242 and spec.md:120 now say exactly this. (b) `:2198-2204` is comment, `:2205` is `dedup_map: dict[tuple, dict] = {}`, `:2212` is `dedup_map[key] = row` — research.md:28-30 exact. (c) `_resolve_orders_by_name` docstring opens `"""` at `:2813` and closes at `:2824` — research.md:94 exact. (d) `excel_utils.py:994` is the `def` line, docstring runs `:995-1030`, the quoted "empty string is preserved as an explicit clear" sentence is at `:1024-1026` inside the cited `:1018-1026` — research.md:152-157 exact. |

**Stagnation watch**: D4 has now appeared in two consecutive iterations. It was *touched* (fixture
changed) but not *fixed* — the change addresses the symptom iteration 1 described (one blank row)
while re-introducing the same non-discrimination through a different attribute (distinct SKUs).
If it survives iteration 3 unchanged this is a blocking defect indicating the discrimination
argument itself was not understood.

---

## Defects Found

### D2a. spec.md:241-251 / acceptance.md:33-41 — the three query ceilings are transplanted from a measurement that has no authentication query; the `<= 2` ceiling is unattainable as scoped — Severity: critical

The SPEC justifies its numbers by asserting structural identity with the outbound suite:
spec.md:247-251 — *"These ceilings mirror `test_spec_015.py:1143-1153`'s `<= 6` / `<= 4` / `<= 2`
bounds for the structurally identical reference implementation — one `transaction.atomic()` block
wrapping at most one `Order` fetch, one `LineItem` fetch, and one `bulk_update`, plus the savepoint
statements that block emits inside the test's own wrapping transaction."*
acceptance.md:37-39 repeats it as "구조가 동일한 참조 구현의 실측 상한".

That enumeration is incomplete, and the omitted item is exactly the structural difference.

The reference numbers were measured on a **direct function call**:
```
test_spec_015.py:1118-1121
def _count_queries(rows: list[dict]) -> int:
    with CaptureQueriesContext(connection) as ctx:
        _process_outbound_rows(rows)
    return len(ctx.captured_queries)
```
No HTTP layer, therefore no authentication. The observed decomposition of `_process_outbound_rows`
(`purchase_order_views.py:2518` atomic, `:2533-2536` Order fetch guarded by `if grouped:`,
`:2550-2554` LineItem fetch guarded by `if orders_by_name:`, `:2701-2704` `bulk_update` guarded by
`if to_update:`) gives: empty = savepoint + release = 2; all-unmatched = savepoint + Order +
release = 3 (the LineItem fetch is skipped because `orders_by_name` is empty); 10 matched =
savepoint + Order + LineItem + bulk_update + release = 5. The ceilings 2/4/6 follow.

The rack-number criterion is scoped to the **endpoint**, not to a function. acceptance.md:20-21
states the common precondition — "인증된 담당자가 `/api/purchase-orders/upload-rack-number/`에
`.xlsx` 파일을 업로드한다" — and there is no extracted rack-number function to call directly: the
logic is inline in `UploadRackNumberView.post()` (`purchase_order_views.py:2180-2266`), and
plan.md:65 plans to rewrite that method in place, not to extract a helper. Every existing test of
this endpoint necessarily goes through `auth_client.post(...)` (e.g. `test_spec_013.py:672, 799,
828, 852`), where `auth_client` attaches a real JWT (`test_spec_013.py:76-79`,
`client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")`) against
`authentication_classes = [JWTAuthentication]` (`purchase_order_views.py:2177`, imported from
`rest_framework_simplejwt.authentication` at `:47`).

`JWTAuthentication.get_user()` in the installed package
(`…/site-packages/rest_framework_simplejwt/authentication.py`) executes
`user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})` — **one unavoidable
SELECT per authenticated request**. `ATOMIC_REQUESTS` is not set anywhere under
`backend/config/settings/`, so no additional request-level savepoint offsets this.

Recomputing at the endpoint level:

| AC-001 clause | Stated ceiling | Actual at view level | Verdict |
|---|---|---|---|
| 10 keys, all matched | `<= 6` (spec.md:244) | auth 1 + savepoint 1 + Order 1 + LineItem 1 + bulk_update 1 + release 1 = **6** | attainable with **zero** headroom |
| all keys unmatched | `<= 4` (spec.md:246) | auth 1 + savepoint 1 + Order 1 + release 1 = **4**, or **5** if the LineItem fetch is not skipped | attainable only under an unstated implementation guard, zero headroom |
| empty upload | `<= 2` (spec.md:247) | auth 1 + savepoint 1 + release 1 = **3** | **unattainable** |

The empty-upload case is reachable and does enter the transaction: a header-only workbook is not
a parse error — `parse_rack_number_excel` raises `ValueError` only on unreadable bytes
(`excel_utils.py:1031-1034`), a zero-row sheet (`:1038-1039`) or a missing header column
(`:1054-1057`); a valid header with no data rows falls through `for row in rows[1:]`
(`:1060`) and returns `[]`. plan.md:108-109 then mandates keeping the wrapper — "전체를 감싸는
`transaction.atomic()`은 이미 존재하므로 그대로 유지한다" — so the savepoint pair is emitted even
for an empty `dedup_map`, and 3 > 2.

This is the same failure D2 identified, one level down: the SPEC still does not carry a bound the
implementation can be held to. The difference is that it now fails *closed* — the M1 RED test will
be un-GREEN-able and the team will be pushed back to the amendment escape hatch at
acceptance.md:40-41 / plan.md:116-120, which is precisely the "값을 구현 시점에 처음 정하지
않는다" outcome the revision claims to have prevented.

### D2b. acceptance.md:31 — the all-unmatched fixture is under-specified, and the two readings straddle the ceiling — Severity: major

"전량 미매칭(0건 매칭) 10-키 배치" does not say how the keys fail to match. The reference fixture
uses non-existent order names (`test_spec_015.py:1151`, `{"name": f"#MISSING{i}", …}`), which
short-circuits the LineItem fetch. If the rack-number fixture instead uses existing Orders with
non-existent SKUs — an equally faithful reading of "전량 미매칭" — the LineItem fetch fires and the
count becomes 5, breaking the `<= 4` ceiling regardless of D2a. spec.md:245-246 is equally silent.

### D2c. spec.md:248 / acceptance.md:38 / plan.md:114-115, :168 — the citation `test_spec_015.py:1143-1153` does not contain the `<= 2` bound it is cited for — Severity: minor

Opened at source: `:1147` is `assert … <= 6`, `:1153` is `assert … <= 4`, and `assert
_count_queries([]) <= 2` is at **`:1157`**, outside the cited range. All four places cite
`:1143-1153` as the origin of all three numbers. `research.md:172-177` cites the three tests
separately and correctly (`:1143-1147`, `:1149-1153`, `:1155-1157`), so the three derived
documents are less precise than the research artefact they draw from. This is the same
citation-precision class the revision claims to have closed under D10.

### D4-R. acceptance.md:95 / plan.md:145 / spec.md:279-282 — the rewritten AC-007 fixture still cannot fail the merging implementation it names — Severity: major

acceptance.md:90-93 states the discrimination argument correctly: a `(None, idx)` implementation
and a `(None, sku)`-merging implementation must produce different `skipped_count`. The live
keying it must guard is `purchase_order_views.py:2205-2212`:
```
key = (row["order_name"], row["sku"]) if row["order_name"] is not None else (None, idx)
```
The Given then specifies: **"주문 식별자 셀이 빈 행 2개(서로 다른 SKU를 가짐)"** (acceptance.md:95),
repeated at plan.md:145 ("빈 식별자 행 2개(서로 다른 SKU)").

With *different* SKUs the broken implementation produces `(None, "SKU-X")` and `(None, "SKU-Y")` —
two distinct keys, `skipped_count == 2`, identical to the correct implementation. The fixture
therefore passes for both, and acceptance.md:99-100's claim — "이 값이 잘못된 `(None, sku)`류
병합 구현과 올바른 `(None, idx)` 구현을 구별하는 지점이다" — is false as written. The two blank
rows must share the **same** SKU for the collision to occur at all; the revision specified the one
attribute that guarantees it cannot. spec.md:279-280 ("Given three rows — two with a blank
order-identifier cell and one valid, distinct row") is silent on SKU, so the normative document
under-specifies the only detail that matters.

For reference, the existing test the SPEC correctly declines to rely on
(`test_spec_013.py:809-834`) uses one blank row with SKU `"SKU-BAD-ORDER"` at `:822` — the
iteration-1 diagnosis was right, and the replacement inherits the same blind spot by another route.

### D7-R. spec.md:301-306 / acceptance.md:162-169 vs plan.md:169 — AC-011 cannot fail the write-scope violation it is assigned to pin — Severity: major

plan.md risk R6 (:169) names the failure mode: "`bulk_update` 필드 목록에 실수로 다른 필드를
포함" → "REQ-RACKBATCH-014(쓰기 범위 제한) 위반", mitigated by "M4의 필드 스냅샷 테스트
(AC-RACKBATCH-011)로 pin". The snapshot test cannot detect that.

`bulk_update(objs, fields)` writes each object's **in-memory** value for every listed field. In
the target flow the objects are fetched inside the same transaction and only `rack_number` is
mutated (plan.md:96-98), so `bulk_update(to_update, ["rack_number", "shipped_quantity"])` writes
`shipped_quantity` back at the value it was just read at. A before/after snapshot is byte-identical
and the test passes. `research.md:210-215` independently confirms there is no `auto_now`, no
`save()` override and no signal on `LineItem` that could perturb the value — verified there as a
"non-risk", which here removes the last mechanism by which the snapshot could notice.

AC-011 does discriminate a narrower class — an implementation that *changes* another field's value
(e.g. copying `_process_outbound_rows`' `logistics_status` transition at `:2596-2704`) — and that
is worth keeping. But REQ-014's normative text is "The system shall **write** only the
`rack_number` field" (spec.md:219), and the AC only observes "shall remain byte-identical"
(spec.md:306). The gap between "written" and "changed" is the entire R6 risk. A test that inspects
the emitted UPDATE (e.g. `CaptureQueriesContext` on the successful upload, asserting the UPDATE
statement's column list) would close it; the snapshot alone does not.

### D11. spec.md:301-306 vs acceptance.md:167-169 — the two documents state AC-011 at different strengths — Severity: minor

spec.md scopes the assertion to seven enumerated fields: "For a LineItem seeded with non-default
values in `title`, `quantity`, `price`, `purchase_status`, `logistics_status`,
`shipped_quantity`, and `shipped_at`, **every one of those fields** … shall remain
byte-identical." acceptance.md:167-169 scopes it to the whole model: "그 LineItem의 **모든
필드**를 스냅샷 비교하면 `rack_number`만 달라지고 … **나머지 전 필드**는 byte 단위로 동일하다."
A tester following spec.md writes a strictly weaker test than one following acceptance.md. Same
defect class as iteration-1 D6 (two documents disagreeing on the body of one AC ID), one severity
lower because the `Traces:` lines agree and the enumerated set covers the realistic cases.

### D12. spec.md:289-293 / acceptance.md:128-132 — AC-009 cannot fail an implementation that drops the transaction — Severity: major

AC-009 is the sole tracer of REQ-013 (atomicity) in both tables (spec.md:324, acceptance.md:224).
Its When is: "첫 번째 키의 변경이 **메모리에 준비된 뒤**, 트랜잭션이 커밋되기 전인 쓰기 단계
(`bulk_update` 직전 또는 그 경로)에서 예외를 주입" (acceptance.md:129-130); spec.md:290-291 is
identical ("after the first key's change has been staged in memory but before the transaction
commits").

In the target design there is exactly one write — `if to_update: LineItem.objects.bulk_update(…)`
(plan.md:105). If the exception fires before or at that call, **nothing has been written to the
database at all**, so the Then ("두 키에 대응하는 LineItem `rack_number` 모두 어떤 값도 변경되지
않은 채로 남는다") holds trivially — it holds identically for an implementation with
`transaction.atomic()` removed entirely. The batched rewrite makes partial application
structurally impossible at this injection point, which is good engineering and bad verification:
AC-009 proves REQ-015 (the 500 response is genuinely observable) but proves nothing about REQ-013.
To discriminate, the injection must land *inside* the write (e.g. patch `bulk_update` to persist
the first object then raise, or force a multi-chunk `bulk_update` via `batch_size`).

### D13. acceptance.md:146-150, :187 — the exact-response-schema claim is not discriminating, yet the table now promises it is — Severity: major

acceptance.md:173-176 recasts the DoD table as an explicit guarantee: "표는 각 REQ의 **판별력
있는** 커버리지가 실제로 존재하는 파일을 명시한다 … D3 … 의 재발을 막기 위해". Row `:187` maps
REQ-RACKBATCH-008 to "`test_spec_013.py:664` 등 (기존, 무수정)", and AC-010's Then (a)
(`:146-150`) asserts "응답 본문은 정확히 `{"matched_count": <int>, "skipped_count": <int>}` 두
필드만 갖는다 … 기존 특성화 테스트가 무수정으로 계속 통과함으로써 검증된다."

`test_upload_matches_and_updates_lineitem` (`test_spec_013.py:664-678`) asserts only
`res.status_code == 200`, `res.data["matched_count"] == 1`, `res.data["skipped_count"] == 0` and
the persisted `rack_number`. A repo-wide grep for a key-set assertion on this endpoint
(`res.data.keys` / `set(res.data` / `sorted(res.data` / `== {"matched_count"`) returns exactly one
hit in the whole file — `:330`, `sorted(res.data["missing_ids"])`, an unrelated endpoint. No
existing test would fail if the rewrite added a third response field. REQ-008's normative text is
"and **no additional** or renamed field" (spec.md:197): the renamed half is covered (a rename
raises `KeyError`), the additional half is not covered by anything in either bucket. This is the
D3 defect pattern surviving on a different REQ, under a table that now explicitly forbids it.

### D14. spec.md:209-211 — REQ-012 still names an internal symbol — Severity: minor

"The system shall never invoke the order-aggregate recomputation routine
(`_recompute_order_aggregates`)". Iteration 1 filed this as the low-severity half of D5; D5's main
clause was fixed and this was not. Mitigating: the symbol is the only unambiguous way to name the
invariant, and AC-008 patches that exact path (`test_spec_013.py:851`). Recorded, not blocking.

### D15. acceptance.md:14-15 — the `[HARD]` equality claim asserts agreement on a field spec.md does not carry — Severity: minor

"[HARD] 각 시나리오의 `Traces:` 목록과 **검증 레이어 표기**는 `spec.md` ACCEPTANCE CRITERIA 절의
동일 AC 항목이 선언한 것과 완전히 일치한다." The `Traces:` half is true and was verified for all
11 ACs. The verification-layer half is not checkable: every acceptance.md heading carries `[BE]`
(`:25, 45, 55, 67, 76, 86, 104, 114, 124, 139, 154`) while spec.md's AC entries (:241-306) declare
EARS pattern labels and no layer marker at all. Either add the marker to spec.md or narrow the
`[HARD]` claim to `Traces:`.

---

## Chain-of-Verification Pass

Second-look findings — **four defects were added on the second pass; the first pass was not
sufficient.**

- *Did I actually read every REQ and AC entry, or skim after the first few?* Re-read all 15 REQs
  and all 11 ACs individually for the MP-2 re-classification rather than sampling. The second pass
  is what produced **D12** — on the first pass AC-009 was accepted because it now carries a
  well-formed `If … then` structure and a 500 assertion (i.e. D6/D1 are closed); only re-reading it
  *against the target design in plan.md:105* revealed that its Then is vacuous for REQ-013.
- *Did I check REQ sequencing end-to-end, not spot-check?* Machine-verified with
  `grep -o … | sort | uniq -c` over both ID families; also cross-checked the acceptance.md heading
  list. MP-1 stands, no renumbering regression from REQ-015/AC-011.
- *Did I verify traceability for every REQ, not sample?* Yes — all 15 rows of spec.md:312-326
  against all 15 rows of acceptance.md:212-226 against each AC's own `Traces:` line, in both
  documents. ID-level agreement is exact. The second pass then asked the harder question the
  revision itself invited (acceptance.md:173-176 promises *discriminating* coverage) and re-derived
  each existing-test mapping from source: that produced **D13** (REQ-008's exact-schema clause has
  no test that could fail) and confirmed **D4-R**/**D7-R**.
- *Did I check the Exclusions for specificity, not just presence?* Yes. All six entries
  (spec.md:335-345) name concrete artefacts — response schema fields, `select_for_update`,
  progress UI / axios timeout, migrations, `parse_rack_number_excel`, `ConfirmOrderView` — and each
  is consistent with an included requirement or design decision. CN-2 passes. The new REQ-015 does
  not collide with any exclusion.
- *Did I look for contradictions between requirements, not just within them?* Yes, pairwise across
  all six groupings. REQ-001 (at most one write) vs REQ-013 (atomicity) — compatible. REQ-005
  (per-row skip counting) vs REQ-003 (last-row-wins dedup) — compatible, and consistent with the
  live `(None, idx)` keying at `purchase_order_views.py:2205-2212`. REQ-006 (never reject on 2+
  matches) vs the reference rejection at `:2582-2594` — correctly opposed and correctly flagged as
  non-inherited. REQ-015 (unhandled exception → 500) vs REQ-010 (parse failure → 422) — REQ-015
  explicitly carves out the handled failures of REQ-009…011, no overlap. REQ-014 (write scope) vs
  REQ-013 — compatible. No contradiction found.
- *Did I re-verify only what the revision touched, per the audit scope?* Yes, and the first pass
  stopped at "the ranges resolve correctly". The second pass re-derived what the cited code
  *implies for the new numbers*, which is what produced **D2a** (the missing authentication query),
  **D2b** (fixture ambiguity straddling the `<= 4` ceiling) and **D2c** (`<= 2` sits at `:1157`,
  outside the cited `:1143-1153`).

Sections re-read in full on pass 2: spec.md 요구사항 (:148-231), spec.md ACCEPTANCE CRITERIA
(:235-329), acceptance.md 전체 (:23-206), plan.md 기술적 접근 (:72-158) and mx_plan (:172-184),
`purchase_order_views.py:2180-2266` and `:2505-2600`, `test_spec_015.py:1092-1200`,
`test_spec_013.py:595-856`.

Citations verified at source this iteration (only those added, moved, retightened, or attached to
REQ-015/AC-011, per the audit scope): `purchase_order_views.py:918-925`, `:927-929`,
`:2198-2204`, `:2205-2212`, `:2216-2261` (`try` at 2216, `except` at 2257, response ends 2261 —
exact), `:2218-2226`, `:2227`, `:2812-2829`, `:2813-2824`; `excel_utils.py:994`, `:995-1030`,
`:1018-1026`, `:1031-1057`; `test_spec_015.py:1118-1121`, `:1143-1157`; `test_spec_013.py:76-79`,
`:407`, `:467`, `:664-678`, `:729`, `:748`, `:766`, `:784`, `:809-834`, `:836`, `:842-855`.
**All resolve and say what the documents claim, with the single exception of D2c.** No fabricated
citation was found this iteration either. AC-011 carries no source citation (nothing to verify).

---

## Recommendation

FAIL. Two iteration-1 majors are unresolved (D2, D4), one is partially resolved (D7), and three
new majors surfaced from the revision itself (D12, D13, and D2b). No must-pass criterion fails —
D1/D9 are genuinely fixed and MP-1/MP-2/MP-3 all pass cleanly — so the remaining work is narrow and
mechanical. Fixes for manager-spec, in dependency order:

1. **Fix the query ceilings or the measurement scope (D2a/D2b, blocks the SPEC's primary AC).**
   Pick one and state it explicitly in spec.md:241-251 and acceptance.md:29-41:
   - *Option A (recommended, keeps the endpoint contract)* — keep the AC at the endpoint and add
     the authentication query to the model: `<= 7` / `<= 5` / `<= 3`, with the derivation spelled
     out ("1 JWT user fetch + savepoint/release pair + at most one Order fetch + one LineItem fetch
     + one `bulk_update`"). Cite `purchase_order_views.py:2177` and the `auth_client` fixture at
     `test_spec_013.py:76-79` as the reason the reference numbers do not transfer verbatim.
   - *Option B* — drop the absolute ceilings entirely and let the 2-key/10-key **equality** carry
     AC-001. acceptance.md:33-34 already calls the equality the "1차 증거, 필수", and it alone
     proves O(1) regardless of the constant; this is also what `test_spec_015.py:1128-1131`'s own
     class docstring argues.
   - Whichever is chosen, also pin the all-unmatched fixture (D2b): state that the 10 keys miss on
     **absent order names** (mirroring `test_spec_015.py:1151`), so the LineItem fetch is
     provably skipped, and say whether the empty-batch early return happens **before** entering
     `transaction.atomic()` — plan.md:76-79 and plan.md:108-109 currently imply opposite answers.
2. **Make AC-007 discriminating (D4-R).** Change "서로 다른 SKU를 가짐" at acceptance.md:95 and
   plan.md:145 to **the same SKU**, and add the same constraint to spec.md:279-280 so the normative
   document carries it. Only a shared SKU makes a `(None, sku)` implementation collapse the two
   rows to `skipped_count == 1`. Keep the `skipped_count == 2` / `matched_count == 1` assertions.
3. **Give REQ-014 a write-scope observation, not just a value observation (D7-R).** Either widen
   AC-011 with a second Then that inspects the emitted UPDATE column list (wrap the successful
   upload in `CaptureQueriesContext` and assert the write statement touches only `rack_number`), or
   correct plan.md:169 to stop claiming AC-011 pins R6 and name what does. Keep the existing
   snapshot clause — it covers the value-mutation class.
4. **Make AC-009 discriminating for REQ-013 (D12).** Change the injection point in spec.md:290-291
   and acceptance.md:129-130 from "before the write / staged in memory" to *inside* the write —
   e.g. a `bulk_update` patched to persist the first object and then raise, or a forced
   multi-statement `bulk_update`. Otherwise reassign REQ-013's tracer, since AC-009 as written only
   proves REQ-015.
5. **Fix the REQ-008 coverage claim (D13).** Add to the `test_spec_017.py` bucket a one-line
   assertion that the 200 body's key set is exactly `{"matched_count", "skipped_count"}`, and
   update acceptance.md:187 and :146-150 accordingly. No existing test can fail on an added field.
6. **Minor, no re-audit needed (D2c, D11, D14, D15).** Split the `test_spec_015.py:1143-1153`
   citation into `:1143-1147` / `:1149-1153` / `:1155-1157` in spec.md:248, acceptance.md:38 and
   plan.md:114-115, :168 (research.md:172-177 is already correct). Align AC-011's field scope
   between spec.md:301-306 and acceptance.md:167-169. Either add `[BE]` markers to spec.md's ACs or
   narrow acceptance.md:14-15's `[HARD]` claim to `Traces:` only.

Citation integrity remains strong: every reference opened this iteration resolves, and the four
D10 pointers were genuinely tightened. The failures above are specification-quality failures —
specifically, four acceptance criteria that cannot fail the implementation they are assigned to
guard — not citation fabrication.
