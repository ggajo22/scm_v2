# SPEC Review Report: SPEC-ORDER-020
Iteration: 2/3
Verdict: FAIL
Overall Score: 0.86

Reasoning context ignored per M1 Context Isolation. This audit used only the four documents in
`.moai/specs/SPEC-ORDER-020/` (v1.0.1) plus the repository source they cite, and the iteration-1 report
strictly as a regression checklist. Every `file:line` citation was re-opened independently; none was
accepted on the strength of the iteration-1 report's prior verification.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: `grep -o "^\*\*REQ-GROUP-[0-9]*\*\*" spec.md` yields exactly
  REQ-GROUP-001 … REQ-GROUP-014 in ascending order, once each, uniform 3-digit padding (spec.md:107, 110,
  113, 116, 121, 125, 131, 134, 140, 143, 146, 151, 156, 158). ACs likewise: AC-GROUP-001 … AC-GROUP-010,
  once each (spec.md:170, 179, 185, 190, 196, 205, 215, 224, 231, 238). A whole-corpus scan of all four
  files returns no identifier outside these 24 — no dangling REQ-GROUP-015, no orphan AC.

- **[PASS, with documented defects N5] MP-2 EARS format compliance**: All 14 REQs and all 10 ACs are
  single normative sentences with an explicit `the system shall` main clause. Verified pattern-by-pattern:
  REQ-GROUP-008 (spec.md:134-136) is genuine Unwanted (`If … then the system shall not …`);
  REQ-GROUP-010/011 (spec.md:143, 146) are genuine Event-Driven (`When …, the system shall …`);
  REQ-GROUP-013 (spec.md:156) is now correctly labeled Ubiquitous (`The system shall not provide …`),
  fixing iteration-1 D5. All seven mislabeled ACs from D12 now carry `(State-Driven)` and AC-GROUP-006
  correctly retains `(Event-Driven)` (spec.md:205). Residual defect N5: REQ-GROUP-005 (spec.md:121-123)
  and REQ-GROUP-006 (spec.md:125-127) are labeled `(Ubiquitous)` yet each carries a second normative
  clause with an explicit state precondition — "*where* two or more … share an identical `created_at`
  value, the system shall break the tie …". By the exact criterion the author applied to the ACs in this
  same revision (HISTORY, spec.md:20: "Ubiquitous·Unwanted 모두 'If/then' 형태의 전제조건 없이 성립해야
  하는데"), these two are compound Ubiquitous+State-Driven. Substance is sound; the label is imprecise.

- **[PASS] MP-3 YAML frontmatter validity**: spec.md:1-11 — `id: SPEC-ORDER-020` (string, matches
  SPEC-{DOMAIN}-{NUM}), `version: 1.0.1` (string), `status: draft` (string), `created_at: 2026-08-13`
  (ISO date), `priority: Medium` (string), `labels: [order, line-item-note, frontend, ux]` (array). All
  six required fields present with correct types. Companion frontmatter is internally consistent and
  synchronized at v1.0.1 / draft / updated 2026-08-13 (acceptance.md:1-7, plan.md:1-7, spec-compact.md:1-7).

- **[N/A] MP-4 Section 22 language neutrality**: single-project SPEC scoped to one React/TypeScript page
  (`frontend/src/pages/LineItemNotesPage.tsx`) with an explicit no-backend-change constraint
  (spec.md:158-159). No multi-language tooling claims. Auto-passes.

---

## Focus Area 1 — Citation Accuracy (every reference independently re-opened)

**Result: zero fabricated citations, zero drifted line numbers, including every citation added or changed
in the v1.0.1 revision.**

New or changed citations introduced by this revision — all verified:

| Citation | Claimed | Actual at that location | OK |
|---|---|---|---|
| `types/order.ts:93-101` (plan.md:83, :236; spec-compact.md:123) | `LineItemNote.id: number`, inherited by `LineItemNoteUnresolved` | `export interface LineItemNote {` at 93, `id: number` at 94, `}` at 101; `LineItemNoteUnresolved extends LineItemNote` at 103 | yes |
| `types/order.ts:99` (plan.md:89) | `created_at` is a string | `created_at: string` | yes (see N6 on the added "ISO 8601" inference) |
| `LineItemNotesPage.tsx:3` + `:5-11` (plan.md:66) | 6 imported exports from the mocked module | `:3` `LINE_ITEM_NOTES_QUERY_KEY`; `:5-11` `useUnresolvedLineItemNotes`, `useResolveLineItemNote`, `useCreateLineItemNote`, `useLineItemNotes`, `downloadLineItemNotesExcel` — exactly 6 | yes |
| `LineItemNotesPage.tsx:38-46` (acceptance.md:223, HISTORY spec.md:20) | LineItem-단위 최신 1건 Map 집계 | comment at 38, `latestByLineItem` loop, closing `}` at 46 | yes |
| `LineItemNotesPage.tsx:41` (acceptance.md:36) | `note_type === '타출판사'` skip | `if (note.note_type === '타출판사') continue` | yes |
| `purchase_order_views.py` `bulk_create` (plan.md:86, :237) | SPEC-ORDER-019 Daily Review 일괄 노트 생성 | `LineItemNote.objects.bulk_create(pending_notes)` at :1844, under comment `# REQ-PO9-005 … SPEC-ORDER-019 REQ-MEMO-009/010 added the third one` at :1839-1842 | yes — and prudently cited without a line number, so it cannot drift |
| SPEC-ORDER-019 `plan.md` "기술적 접근" (plan.md:86, :237) | discusses `bulk_create` | section header at `.moai/specs/SPEC-ORDER-019/plan.md:96`; `bulk_create 무변경` item at `:115` | yes |
| `frontend/package.json` has no date library (plan.md:91) | no date-fns/dayjs/moment/luxon | grep returns nothing | yes |
| `.claude/rules/moai/workflow/workflow-modes.md` Brownfield Enhancement (plan.md:19) | section exists | "### Brownfield Enhancement (for existing codebases)" present | yes |
| `NoteCard` props (plan.md:96) | `note, onResolve, isResolving, showAddForm, currentTabAssignee` | LineItemNotesPage.tsx:217-221, exactly those five | yes |

Carried-over citations re-verified from scratch (not trusted from iteration 1):
`LineItemNotesPage.tsx` is exactly 414 lines (matches plan.md:29) — `:35-49` `filterNotes`, `:36`,
`:48`, `:54-98` `NoteHistory`, `:103-211` `InlineNoteForm`, `:216-302` `NoteCard`, `:236-237` expand
toggle, `:240-245`/`:241`/`:244` order-number button, `:246-259` badges, `:260` truncated body,
`:266-272` resolve button, `:304-305` `@MX:ANCHOR`/`@MX:REASON`, `:306-414` page component, `:309`,
`:313`, `:325-341`, `:343`, `:344`, `:371-392`, `:394-398`, `:396`, `:400-411` — all exact.
`useLineItemNotes.ts` (file is 84 lines): `:7`, `:33-34`, `:35-59`, `:41-47`, `:61-69`, `:71-84` — all exact.
`serializers.py:79-97` / `:85` / `:86` / `:94-97`; `views.py:269-282` / `:275` / `:279`;
`urls.py:160`; `models.py:238-289` (class at 238, `ordering = ["-created_at"]` at 289);
`OrderDetailPage.test.tsx:15-18` (the `vi.mock` of the very module in question) and `:20-33`
(`renderPage()`); `quality.yaml:4`/`:43`/`:46` — all exact. Regression-gate files
`DashboardPage.test.tsx` and `ForbiddenPage.test.tsx` exist; `LineItemNotesPage.test.tsx` correctly does
not yet exist and is marked `[NEW]` (spec.md:72).

**Conclusion on Focus Area 1: PASS.** Roughly 75 distinct citations checked, all resolving to the claimed
symbol.

---

## Focus Area 2 — Acceptance Criteria Discriminating Power

### No-op survival test

**All 10 ACs fail on a no-op (revert to today's flat `tabNotes.map` at LineItemNotesPage.tsx:400-411).**
Every scenario's load-bearing assertion is performed through a group container that does not exist today.
AC-GROUP-007's empty-tab clause is the one exception, and it discloses that limitation explicitly at
acceptance.md:237-240 while its populated-tab clause carries revert-detection. No AC is a mere restatement
of its requirement.

### AC-GROUP-007 — did the fixture rewrite restore what D2 destroyed? YES

acceptance.md:220-228 now assigns `line_item_id: 9601` (id 81) and `line_item_id: 9602` (id 82) to the two
notes on order 1301, with distinct `created_at`, and states the reason inline with a verified citation to
`LineItemNotesPage.tsx:38-46`. Traced through the real code: `filterNotes` keys `latestByLineItem` on
`line_item_id` (`:42`), so with distinct keys both notes survive; `note_type` defaults to `""` per the new
fixture policy (acceptance.md:35-37) so `:41` does not drop them; both have `assignee: "CS"` so `:48`
retains both on the CS tab. Then(1차) at acceptance.md:230 — group container holds exactly 2 notes, header
"#I1301" and count "2" — is now achievable, and it is the sole revert-detector for this scenario.
Discriminating power restored. plan.md:136-137 mirrors the constraint for the test author.

### AC-GROUP-009 / AC-GROUP-010 — do the tie-break fixtures actually force a failure? YES for the
### stated mutation, NO for the specified tie-break *key*

The stable-sort question resolves in the SPEC's favor. `Array.prototype.sort` is stable per ES2019, so an
implementation sorting on `created_at` alone leaves equal-key elements in arrival order:

- **AC-GROUP-009** (acceptance.md:108-119): arrival `[id 91 → order 1601, id 92 → order 1602]`, both
  `created_at: "2026-08-12T09:00:00Z"`; expected render `#L1602 → #L1601`. Arrival is the exact reverse of
  the expectation, so a no-tie-break implementation renders `#L1601` first and fails. I also confirmed the
  fixture survives `filterNotes` (distinct `line_item_id` 9901/9902, `assignee: "발주"`), and that the
  common `Object.keys()`-on-a-numeric-keyed-object grouping path yields ascending numeric order
  `[1601, 1602]` — i.e. still arrival order, so the trap does not leak. Not incidentally satisfiable.
- **AC-GROUP-010** (acceptance.md:125-133): arrival `[id 101, id 102]` on order 1701, identical
  `created_at`; expected `메모 B (102)` above `메모 A (101)`. Same reasoning; a no-tie-break stable sort
  fails.

Cross-mutation check: sorting groups by `order_id` desc, or by `id` desc alone, or simply reversing the
array, each passes AC-GROUP-009 but is caught by AC-GROUP-002 (arrival `[601, 602, 603]`, expected
`[#B602, #B603, #B601]` — not the reverse, not `order_id`-ordered, not `id`-ordered). The suite is
mutually reinforcing there.

**However (N2):** in both new fixtures `id` order is perfectly correlated with `order_id` order and with
`line_item_id` order (91→1601/9901 vs 92→1602/9902; 101→10001 vs 102→10002). An implementation that breaks
the tie on `order_id` descending, or on `line_item_id` descending, passes AC-GROUP-009 and AC-GROUP-010
unchanged while violating the literal text of REQ-GROUP-005/006 ("break the tie by the `id`", spec.md:122-123,
:126-127). The ACs therefore verify *that a deterministic tie-break exists*, not *that the key is `id`*.

### AC-GROUP-005 — the D10 replacement mutation is not reliably caught by AC-GROUP-005 (N1, blocking)

spec.md:199-203 and acceptance.md:182-188 replace the old unrealizable mutation with a realizable one: a
group component that maps over the whole `tabNotes` array instead of its own notes. The mutation is indeed
realizable. The problem is the claimed detection mechanism:

> "…그룹1101 스코프 안에서도 그룹1102의 주문번호 컨트롤이 함께 발견되거나 그 반대가 되어 '그룹1102 컨테이너
> 안에서 컨트롤을 찾는다'는 전제 자체가 **둘 이상의 후보를 반환해** 이 단정이 실패한다" (acceptance.md:186-188)
>
> "…the click assertion would **resolve against the wrong target**" (spec.md:202)

I constructed the mutation concretely against the real component. Under it, group1102 renders both notes,
so it contains an order-number button reading `#G1101` **and** one reading `#G1102`. But the When clause
identifies the control by its own text — "주문번호 컨트롤(**"#G1102"**)" (acceptance.md:178-179) — and
`NoteCard:244` renders `{note.order_name ?? …}`, so `within(group1102).getByText('#G1102')` still matches
exactly one element, the click still fires `navigate('/orders/1102')` (`NoteCard:241`), and both assertions
pass. The stated mutation survives AC-GROUP-005.

Detection depends entirely on an unspecified query-construction choice by the test author: a name-regex
query (`getByRole('button', { name: /^#G/ })`) would throw on multiple matches and catch it; the exact-text
query the scenario literally prescribes would not. Note also that a bare `getByRole('button')` is not
available as a fallback — a collapsed `NoteCard` already contains two buttons (`:240` order-number, `:266`
resolve), so even the correct implementation forces a name filter. This is precisely the "the implementer
writes both the marker and the test" hazard raised as D11 in iteration 1.

The mutation *is* caught elsewhere — AC-GROUP-001 (d) would count 3 resolve controls in group801 instead of
2, and AC-GROUP-004 (a) would sum 8 note rows instead of 4 — so the suite as a whole is safe. But
spec.md:165-167 states a [HARD] contract that "각 항목은 자신을 깨뜨리는 mutation을 한 줄로 명시한다", and
AC-GROUP-005's line is false about itself. This is iteration-1 D10 recurring in a new form.

### AC-GROUP-001 (d) — the D7 fix works, with one residual gap (N3)

I verified the count assertion is mechanically sound against real markup: the resolve button's entire text
content is `해결` (LineItemNotesPage.tsx:266-272, text at `:271`), the order-number button's name is the
order display string (`:244`), the expand affordance is a `div` not a button (`:235-237`), and
`InlineNoteForm` is only mounted when `expanded` (`:276, :289-297`) which no scenario triggers. So
`within(group).getAllByRole('button', { name: /해결/ })` returns exactly one per collapsed note, and any
bulk control — "일괄 해결", "선택 해결", or icon-only with an accessible name containing 해결 — inflates the
count. Genuine improvement over the enumerated-label check.

Residual: the assertion is scoped *within* a group container (acceptance.md:64-67). REQ-GROUP-013
(spec.md:156) carries no scope qualifier — "The system shall not provide a control that resolves more than
one note in a single user action." A page-level or toolbar-level bulk-resolve control rendered outside every
group container satisfies every per-group count and still violates the requirement.

### Full mutation matrix

| AC | Mutation constructed | Caught by this AC? |
|---|---|---|
| 001 | flat list (revert) / one wrapper per note / single-note orders rendered bare / group-level bulk resolve | Yes — (a) containment, (b) count "2", (c) shared helper, (d) control count |
| 002 | no group sort / sort by `order_id` / sort by `id` / reverse array | Yes — arrival `[601,602,603]` differs from expected `[602,603,601]` under all four |
| 003 | no intra-group sort | Yes — arrival is old-first, expectation is new-first |
| 004 | `countByTab` from group count | Yes — label would read "(2)"; verified `:366` renders `({countByTab(tab)})` inside the tab button |
| 005 | group maps over full `tabNotes` | **No — see N1**; caught only by AC-001 (d) and AC-004 (a) |
| 006 | empty group shell left after last resolve | Yes — 2차 단정; first clause honestly disclosed as having no independent mutation (acceptance.md:206-212) |
| 007 | phantom empty group wrapper | Yes (2차); revert caught by 1차 |
| 008 | group before filtering | Yes — count would read 2 and "발주 노트" would appear on the CS tab |
| 009 | `created_at` only, stable sort | Yes; but `order_id`/`line_item_id` tie-break also passes — **N2** |
| 010 | `created_at` only, stable sort | Yes; but `line_item_id` tie-break also passes — **N2** |
| 013 | bulk control outside any group container | **No — see N3** |

---

## Focus Area 3 — Internal Consistency After Revision

Checked exhaustively, not sampled.

- **Fixture note counts vs. enumerations**: all ten scenarios agree. AC-001 "3건"/3 listed (acceptance.md:49-53);
  AC-002 "주문 3개"/3; AC-003 "2건"/2; AC-009 "2개"/2; AC-010 "2건"/2; AC-004 "4건"/4; AC-008 "2건"/2;
  AC-005 "2개"/2; AC-006 "2건"/2; AC-007 "2건"/2. The D1 contradiction is gone, and the downstream
  restatements now agree: spec-compact.md:77 "총 3건", plan.md:117 "총 3건", spec.md:171 "one order has two
  eligible notes and the other has one".
- **`id` / `created_at` / `line_item_id` values**: unique within every scenario; `order_id` values unique
  across all ten scenarios. One cross-scenario reuse: `line_item_id` 9601/9602 appears in both AC-GROUP-005
  (acceptance.md:176-177) and AC-GROUP-007 (:225-226). Harmless — the scenarios are independent renders —
  but it is the only break in an otherwise scenario-unique numbering convention (N7).
- **Traceability**: three tables plus ten per-AC `Traces:` lines compared entry-for-entry.
  spec.md:249-262 ↔ acceptance.md:248-257 (DoD, with T*n* ↔ AC-GROUP-00*n*) ↔ plan.md:214-223 agree
  completely; each AC's `Traces:` line in acceptance.md is identical to the same AC's `Traces:` in spec.md
  (AC-001 acc:47/spec:170; 002 acc:77/spec:179; 003 acc:93/spec:185; 004 acc:139/spec:190; 005 acc:173/spec:196;
  006 acc:192/spec:205; 007 acc:218/spec:215; 008 acc:157/spec:224; 009 acc:106/spec:231; 010 acc:123/spec:238).
  No orphan AC, no AC citing a non-existent REQ. Count statements agree: spec.md:264 and spec-compact.md:71
  both say 13 of 14 REQs directly covered by 10 ACs.
- **T-numbering**: plan.md:117-146 defines T1–T10 mapped to AC-GROUP-001–010; plan.md:36-38 and :190-195
  consistently carve out T7 and T6's first clause; acceptance.md:248-257 uses the same mapping;
  spec-compact.md:98 says "T1~T10(T9~T10은 `created_at` 동률 tie-break 검증)". Consistent.
- **HISTORY 1.0.1 accuracy** (spec.md:20): each claim was checked against the current file state, and every
  claimed fix is present. One factual error about the *prior* state — see N4.
- **Version/status sync**: 1.0.1 / draft / 2026-08-13 in all four frontmatters.

---

## Additional Checks Requested

- **Exclusions non-empty and meaningful**: PASS. spec.md:269-285 lists nine entries, each naming a concrete
  artifact or decision. I re-verified two of the embedded code claims rather than trusting them:
  `pagination_class = None` at views.py:275, and `downloadLineItemNotesExcel` at useLineItemNotes.ts:71-84
  (file ends at 84). Checked each exclusion against REQ-GROUP-001…014 — no conflict; each maps to a REQ or a
  확정된 사용자 결정.

- **Every REQ covered by at least one AC**: 13 of 14, with the gap disclosed and gated. REQ-GROUP-014 has no
  runtime AC (spec.md:262) and is verified by the `git diff --stat backend/` gate at plan.md:199, reinforced
  by three sibling diff gates (plan.md:196-201).

- **Scope boundary "frontend-only, no backend change" still holds**: PASS — and this needed re-verification,
  because v1.0.1 introduced a new data dependency. REQ-GROUP-005/006 now require `note.id` at render time.
  `id` is present in `LineItemNoteUnresolvedSerializer.Meta.fields` (serializers.py:94, first element of the
  list at :94-97) and in `LineItemNote` (types/order.ts:94), inherited by `LineItemNoteUnresolved`
  (types/order.ts:103). `LineItemNoteUnresolvedListView` returns the complete unresolved set
  (`pagination_class = None`, views.py:275; `filter(is_resolved=False)`, :279), so client-side grouping and
  tie-breaking need no new field, parameter, or endpoint. `order_id` remains non-null end to end
  (models.py:261-263 FK without `null=True` → serializers.py:86 without `default=None` → types/order.ts:108
  `number`). **The tie-break is implementable with zero backend change. The boundary holds.**

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.85 | between 0.75 and 1.0 — minor ambiguity in one or two requirements | D6 and D11 both closed: the weasel "correctly"/"올바르게" is replaced by a concrete assertion (spec.md:215-217, acceptance.md:230), and AC-001 (c) now binds the mechanism — "동일한 단일 조회 헬퍼(`order_id`만 인자로 받는 형태)" (acceptance.md:54-56, :61-63; mirrored plan.md:118-119). Deductions: REQ-GROUP-014 (spec.md:158-159) still reads as self-referential meta-language ("shall implement every requirement in this SPEC"); REQ-GROUP-005/006 compound labels (N5) |
| Completeness | 0.90 | between 0.75 and 1.0 | All required sections present: HISTORY (spec.md:15-20), 문제 정의 (:24-43), 솔루션 개요/범위 (:45-72), 확정된 사용자 결정 (:74-96), 요구사항 (:100-159), ACCEPTANCE CRITERIA (:163-265), Exclusions (:269-285), 후속 과제 (:287-295). Frontmatter complete. D9 closed — `note_type: ""` and `is_resolved: false` are now mandated safe defaults with the load-bearing reason cited to LineItemNotesPage.tsx:41 (acceptance.md:35-39). Deduction: no document names the strongest available justification for the tie-break (N6) |
| Testability | 0.75 | 0.75 — one AC is not precisely binary-testable but is measurable with minor interpretation | Ten ACs, all failing on a no-op revert; D7 closed with a mechanically verified count assertion; D8 closed with two new tie-break ACs whose fixtures genuinely defeat a stable sort. Deductions: AC-GROUP-005's own stated mutation is not reliably detected by it (N1); the tie-break key is not pinned (N2); REQ-GROUP-013 is only checked within group scope (N3) |
| Traceability | 1.00 | 1.0 — every REQ has an AC, every AC references a valid REQ | Three tables (spec.md:249-262, acceptance.md:248-257, plan.md:214-223) plus ten per-AC `Traces:` lines compared entry-for-entry; complete agreement. The single uncovered REQ (014) is disclosed in all three tables and gated at plan.md:199 |

---

## Defects Found

**N1. spec.md:199-203 / acceptance.md:182-188 (AC-GROUP-005) — the replacement mutation is not detected by
this AC. Severity: major. (Recurrence of iteration-1 D10.)**
The mutation is now realizable (a group rendering the full `tabNotes` instead of its own slice), which fixes
half of D10. But the claimed detection is false. The When clause identifies the control by its own order
text — 주문번호 컨트롤("#G1102") (acceptance.md:178-179) — and `NoteCard:244` renders exactly that text per
note, so `within(group1102).getByText('#G1102')` matches one element even when group1102 wrongly renders both
orders' rows; the click fires `navigate('/orders/1102')` (`NoteCard:241`) and both Then clauses pass. The
assertions "둘 이상의 후보를 반환해 이 단정이 실패한다" (acceptance.md:187-188) and "the click assertion would
resolve against the wrong target" (spec.md:202) are therefore untrue as written. Detection is possible only
if the test author independently chooses a name-regex query; a bare role query is unavailable because a
collapsed `NoteCard` already exposes two buttons (`:240`, `:266`). This violates the document's own [HARD]
contract at spec.md:165-167. The mutation is caught by AC-GROUP-001 (d) and AC-GROUP-004 (a), so the suite is
not unsafe — but AC-GROUP-005 claims a discriminating property it does not have, and a test author following
AC-GROUP-005 alone will write a non-discriminating T5.

**N2. acceptance.md:112-113 and :127-128 (AC-GROUP-009/010 fixtures) — the tie-break key is not pinned.
Severity: minor.**
In AC-GROUP-009 the higher `id` (92) also has the higher `order_id` (1602) and the higher `line_item_id`
(9902); in AC-GROUP-010 the higher `id` (102) also has the higher `line_item_id` (10002). A tie-break on
`order_id` desc or `line_item_id` desc passes both scenarios while violating REQ-GROUP-005/006, which name
`id` specifically (spec.md:122-123, :126-127). The fixtures prove *a* deterministic tie-break exists, not
that it is the specified one. Fix is a two-character edit: anti-correlate the keys (e.g. give order 1601 the
note with `id: 92` and order 1602 the note with `id: 91`, keeping the expected render `#L1601 → #L1602`).

**N3. spec.md:156 vs acceptance.md:64-67 — REQ-GROUP-013 is verified only within group scope. Severity: minor.**
The count assertion compares resolve controls *inside each group container* against that group's note count.
REQ-GROUP-013 forbids any control that resolves more than one note in a single action, with no scope
qualifier. A page-level or toolbar-level bulk-resolve control (rendered outside every group container)
satisfies every per-group count and still violates the requirement. Substantially better than the
enumerated-label check it replaced, but the hole is real. Adding a page-scope clause — the total number of
resolve controls on the page equals the tab's note count — would close it.

**N4. spec.md:20 (HISTORY 1.0.1) — misstates the prior EARS label of AC-GROUP-008. Severity: minor.**
The entry claims "AC-GROUP-008의 레이블을 **Unwanted** → State-Driven으로 … 정정". The iteration-1 report's
D12 recorded all seven mislabeled ACs — spec.md:166, 173, 179, 184, 190, 205, **214** — as carrying
`(Ubiquitous)`, and its recommendation 8 lists "AC-GROUP-001/002/003/004/005/007/008 are state-driven, not
Ubiquitous". AC-GROUP-008 was therefore Ubiquitous, not Unwanted. HISTORY is the audit trail for this
document; a wrong statement about the prior state degrades it. The same entry also says spec-compact.md was
"처음부터 … 일관되어 있었다" about the AC-001 note count, while spec-compact.md:77 was in fact edited from
"2주문(한쪽 2건)" to "2주문(한쪽 2건, 한쪽 1건, 총 3건)" — substantively consistent, textually changed.

**N5. spec.md:121-123, :125-127 (REQ-GROUP-005/006) — compound requirement under a Ubiquitous label.
Severity: minor.**
Each is labeled `(Ubiquitous)` but contains a second normative clause gated on a state precondition
("where two or more … share an identical `created_at` value, the system shall break the tie by `id` …"). By
the exact standard this revision applied to the ACs (HISTORY spec.md:20), that clause is State-Driven. Either
split into REQ-GROUP-005a/005b, or relabel as compound. Note this cannot be fixed by renumbering without
breaking MP-1 and three traceability tables — relabeling is the cheaper path.

**N6. spec.md:305-306, spec-compact.md:40 and :132-133, plan.md:86-88 / :164 / :237, acceptance.md:109-110 —
the cited justification for the tie-break is the weaker of the two available, and is unverified. Severity: minor.**
All four documents assert that SPEC-ORDER-019's `bulk_create` is the "현실적 원인" of identical `created_at`.
`LineItemNote.created_at` is `auto_now_add=True` (models.py:272), and Django assigns it through a separate
`timezone.now()` call per object during `bulk_create`, so identical microsecond values are *possible* but not
systematic — the claim is stated as possibility ("가질 수 있다"), which keeps it defensible, but no document
verifies it. Meanwhile the directly verifiable determinism gap is not cited anywhere:
`LineItemNoteUnresolvedListView.get_queryset()` orders by `-created_at` alone with no secondary key
(views.py:278-282), so equal timestamps yield DB-arbitrary arrival order regardless of how they were created.
Citing that would make the requirement's motivation airtight rather than probabilistic. Relatedly, plan.md:89
cites `types/order.ts:99` for "`created_at`은 ISO 8601 문자열" — that line declares only `created_at: string`;
the ISO-8601 property comes from DRF's serializer rendering, not from the type.

**N7. acceptance.md:176-177 vs :225-226 — cross-scenario `line_item_id` collision. Severity: minor (cosmetic).**
9601/9602 are used by both AC-GROUP-005 and AC-GROUP-007. Every other scenario uses a distinct band
(9101-9102, 9201-9203, 9301-9303, 9401-9404, 9501-9502, 9701-9702, 9901-9902, 10001-10002). Harmless — the
renders are independent — but it breaks the document's own convention and invites confusion when the two
fixtures are read side by side.

---

## Chain-of-Verification Pass

Second-look findings after re-reading the sections I moved through quickly on the first pass:

1. **Re-read all 14 REQs end-to-end rather than confirming only the ones the HISTORY said had changed.**
   This surfaced N5 (REQ-GROUP-005/006 compound labels) — the revision corrected eight AC labels using a
   stated principle, then left two REQs violating that same principle. I had initially checked only that the
   tie-break clause was present.
2. **Re-ran REQ/AC sequencing as a whole-corpus scan** (`grep -oh "REQ-GROUP-[0-9]*\|AC-GROUP-[0-9]*" *.md |
   sort -u`) instead of reading the tables. Confirmed exactly 14 REQs and 10 ACs with no dangling identifier
   anywhere in the four files.
3. **Re-verified all 14 REQ→AC mappings across three tables plus ten per-AC `Traces:` lines**, rather than
   spot-checking the two ACs added by the revision. No mismatch; the new AC-009/010 rows were inserted into
   all three tables correctly.
4. **Re-derived the AC-GROUP-005 mutation against the actual DOM rather than accepting the narrative.** This
   is where N1 surfaced. On my first pass I read spec.md:199-203, saw that the mutation was now realizable
   (which was D10's complaint), and moved on. Only when I constructed `within(group1102).getByText('#G1102')`
   against `NoteCard:240-245` did it become clear the assertion cannot see the extra rows. This was the single
   most valuable second-look item in this audit.
5. **Re-checked whether the newly added tie-break creates a hidden backend dependency.** REQ-GROUP-005/006 now
   need `note.id` at render time; I confirmed `id` is the first entry of
   `LineItemNoteUnresolvedSerializer.Meta.fields` (serializers.py:94) rather than assuming it, because a
   missing `id` would have silently broken the frontend-only scope claim in REQ-GROUP-014. It is present.
6. **Re-checked the resolve-control count assertion mechanically** rather than accepting that "개수 대조"
   is obviously stronger than label matching. Confirmed the resolve button's text is exactly `해결`
   (LineItemNotesPage.tsx:271), the expand affordance is a `div` (`:235`), and `InlineNoteForm` mounts only
   when expanded (`:276`) — so the count is stable at one per collapsed note. This also surfaced N3, the
   out-of-group scope hole.
7. **Re-read the Exclusions for specificity and re-verified two embedded code claims** (`pagination_class =
   None` at views.py:275; `downloadLineItemNotesExcel` at useLineItemNotes.ts:71-84). Both exact. Checked all
   nine exclusions against all fourteen REQs for conflict — none.
8. **Cross-requirement contradiction sweep including the new material.** REQ-GROUP-004 (single-note groups use
   the same container) vs REQ-GROUP-012 (no container when empty) — consistent. REQ-GROUP-005/006 tie-break vs
   REQ-GROUP-014 (no backend change) — consistent, per item 5. REQ-GROUP-002 vs REQ-GROUP-007 — mutually
   reinforcing. No contradictions.
9. **Re-checked the HISTORY entry line by line against the current documents** instead of accepting it as a
   summary. Every claimed fix is present in the files. One claim about the *prior* state is wrong — N4.
10. **Chased the `bulk_create` rationale to source** rather than treating it as background color, because it
    is cited in all four documents. The code exists (purchase_order_views.py:1844, attributed to SPEC-ORDER-019
    in the adjacent comment), but the mechanism by which it would produce identical timestamps is weaker than
    the documents imply, and the stronger untie-broken-queryset argument (views.py:281) is absent — N6.

---

## Regression Check (against iteration 1, `.moai/reports/plan-audit/SPEC-ORDER-020-review-1.md`)

| Prior defect | Status | Evidence |
|---|---|---|
| **D1** — acceptance.md:43 fixture said "4건", listed 3 (major) | **RESOLVED** | acceptance.md:49 now "다음 노트 3건", three notes at :50-52, parenthetical :53 "801에 2건, 802에 1건". Downstream restatements agree: spec-compact.md:77 "총 3건", plan.md:117 "총 3건", spec.md:171 |
| **D2** — AC-GROUP-007 fixture unsatisfiable, no distinct `line_item_id` (major) | **RESOLVED** | acceptance.md:220-228 states distinct `line_item_id` 9601/9602 with `id` and `created_at`, and the inline reason cited to LineItemNotesPage.tsx:38-46. Traced through real `filterNotes` — both notes survive; Then(1차) at :230 is now achievable. plan.md:136-137 mirrors it |
| **D3** — plan.md:62 wrong `vi.mock` rationale (major) | **RESOLVED** | plan.md:66 now states the module is replaced wholesale, names the exact error text, enumerates all six imported exports (verified against LineItemNotesPage.tsx:3 and :5-11), and conditions the safety on "이 SPEC의 테스트 범위가 그 코드 경로에 닿지 않기 때문" with an explicit instruction to future test authors. Corroborated by real precedent: OrderDetailPage.test.tsx:15-18 mocks only two of the module's exports |
| **D4** — REQ-GROUP-014 not a system-behavior requirement (minor) | **PARTIALLY RESOLVED** | spec.md:158-159 now makes the system the subject and is labeled Ubiquitous, but "shall implement every requirement in this SPEC" remains self-referential process language rather than observable behavior. Acceptable as a brownfield scope guard; noted, not re-raised |
| **D5** — REQ-GROUP-013 label mismatch (minor) | **RESOLVED** | spec.md:156 now `(Ubiquitous)` |
| **D6** — "correctly"/"올바르게" weasel word (minor) | **RESOLVED** | spec.md:215-217 now "render the populated tab's group container holding all of its notes"; acceptance.md:230 "정확히 노트 2건(id=81, id=82)을 포함하며, 그 헤더에 '#I1301'과 건수 '2'" |
| **D7** — enumerated-label absence check (minor) | **RESOLVED** | acceptance.md:64-67 and spec.md:173-174 replace it with a per-group control count. Mechanically verified against LineItemNotesPage.tsx:266-272. Residual scope hole raised separately as N3 |
| **D8** — no tie-break for equal `created_at` (minor) | **RESOLVED** | REQ-GROUP-005 (spec.md:121-123) and REQ-GROUP-006 (:125-127) add `id` descending; AC-GROUP-009/010 added; plan.md:81-85, :112-113, R7 :164; spec-compact.md:39-40. Verified implementable frontend-only (serializers.py:94). Key-pinning weakness raised as N2 |
| **D9** — fixture field policy omitted `note_type` (minor) | **RESOLVED** | acceptance.md:35-39 mandates `note_type: ""` and `is_resolved: false`, states the load-bearing reason with a verified citation to LineItemNotesPage.tsx:41, and explicitly withdraws `note_type` from the arbitrary-value list |
| **D10** — two unrealizable mutations (minor) | **PARTIALLY RESOLVED — recurs as N1** | AC-GROUP-006 half resolved: spec.md:209-213 keeps only the empty-shell mutation and openly states the first clause has no independent adversarial mutation. AC-GROUP-005 half **not** resolved: the replacement mutation is realizable but is not detected by AC-GROUP-005's own assertions. See N1 |
| **D11** — "예: 동일한 역할/테스트 훅 속성" non-binding (minor) | **RESOLVED** | acceptance.md:54-56 now binds the mechanism ("그룹801을 조회할 때 쓰는 것과 동일한 단일 조회 헬퍼 … 그룹마다 특화된 별도 셀렉터를 쓰지 않는다") and :61-63 spells out the failure mode; plan.md:118-119 mirrors it |
| **D12** — seven AC pattern labels wrong (minor) | **RESOLVED in substance** | All ten ACs now carry State-Driven or Event-Driven labels matching their form (spec.md:170, 179, 185, 190, 196, 205, 215, 224, 231, 238). Two new label issues: N4 (HISTORY misdescribes AC-008's prior label) and N5 (REQ-005/006 compound) |

**Stagnation check**: 9 of 12 prior defects fully resolved, including all three blocking ones. One defect
(D10, AC-GROUP-005 half) persists in altered form across both iterations. This is not stagnation — the author
implemented the iteration-1 recommendation literally, and the recommendation itself under-specified the
detection mechanism. Progress is real and substantial.

---

## Recommendation

FAIL — narrowly, on one major defect that is a recurrence of an unresolved iteration-1 finding. Everything
that blocked iteration 1 is genuinely fixed and independently verified: the fixture contradiction, the
unsatisfiable AC-GROUP-007 fixture, and the incorrect `vi.mock` rationale. Citation accuracy is again
flawless across ~75 references including every one added by this revision, traceability is perfect, the
frontend-only boundary survives the new `id` dependency, and the two new tie-break ACs do defeat a stable
sort. One targeted edit clears the FAIL.

**Required before RED:**

1. **acceptance.md:178-188 and spec.md:199-203 (AC-GROUP-005)** — make the mutation detectable by this AC.
   Add a Then clause that does not depend on the test author's query style, e.g.: "각 그룹 컨테이너 안에
   주문번호 컨트롤이 정확히 1개씩 존재한다 (그룹1101 안 1개, 그룹1102 안 1개)". Then correct the mutation
   narrative: the failure is the per-group control *count* becoming 2, not the click resolving against the
   wrong target — with the text-identified control it does not. Also state that under the current
   assertions alone the mutation is caught by AC-GROUP-001 (d) and AC-GROUP-004 (a), so a future editor does
   not weaken those without noticing.

**Strongly recommended (each closes a real hole; none requires re-planning):**

2. **acceptance.md:112-113 and :127-128** — anti-correlate `id` with `order_id` and `line_item_id` so the ACs
   pin the tie-break key named in REQ-GROUP-005/006 (N2). For AC-GROUP-009: put `id: 92` on order 1601 /
   `line_item_id` 9901 and `id: 91` on order 1602 / 9902, expected render `#L1601 → #L1602`, arrival order
   `[1602, 1601]`. For AC-GROUP-010: give the higher `id` the lower `line_item_id`. Update the Then and
   판별력 text accordingly.

3. **acceptance.md:64-67** — add a page-scope clause for REQ-GROUP-013 (N3): the total number of resolve
   controls rendered on the tab equals the tab's note count, so a bulk control placed outside every group
   container is also caught.

4. **spec.md:20 (HISTORY)** — correct "AC-GROUP-008의 레이블을 Unwanted → State-Driven" to "Ubiquitous →
   State-Driven", and soften the claim that spec-compact.md was unchanged (its AC-001 row was edited to
   "총 3건") (N4).

5. **spec.md:121-127** — relabel REQ-GROUP-005/006 to reflect their compound form, or split the tie-break
   clause out of the label's scope (N5). Do not renumber — that would break MP-1 and three traceability
   tables.

6. **plan.md:86-88 / :164 / :237, spec.md:305-306, spec-compact.md:40 / :132-133** — add the directly
   verifiable justification alongside the `bulk_create` one: `LineItemNoteUnresolvedListView.get_queryset()`
   orders by `-created_at` with no secondary key (views.py:278-282), so equal timestamps produce
   DB-arbitrary arrival order irrespective of how the rows were created. Also correct plan.md:89 — the ISO-8601
   property comes from DRF rendering, not from `types/order.ts:99`, which declares only `string` (N6).

7. **acceptance.md:225-226** — move AC-GROUP-007's `line_item_id` values out of AC-GROUP-005's 9601/9602 band
   (e.g. 9801/9802) to restore the document's scenario-unique convention (N7).

Verdict: FAIL
