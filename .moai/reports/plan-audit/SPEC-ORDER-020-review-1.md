# SPEC Review Report: SPEC-ORDER-020
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.78

Reasoning context ignored per M1 Context Isolation. This audit used only the four files in
`.moai/specs/SPEC-ORDER-020/` plus the repository source they cite. No author reasoning, prior draft,
or conversation history was consulted.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: REQ-GROUP-001 through REQ-GROUP-014 are defined exactly once
  each, in ascending order, at spec.md:106, 109, 112, 115, 120, 123, 127, 130, 136, 139, 142, 147, 152,
  154. No gaps, no duplicates, consistent 3-digit zero-padding. AC-GROUP-001..008 likewise unique
  (acceptance.md:39, 63, 79, 94, 107, 123, 138, 160 — presented in thematic rather than numeric order,
  which is cosmetic only; the DoD table at acceptance.md:185-192 lists them in numeric order).

- **[PASS, with documented defect D12] MP-2 EARS format compliance**: All 14 REQs and all 8 ACs are
  single normative sentences with an explicit `the system shall` main clause — not free-form prose and
  not multi-step Given/When/Then scenarios (those correctly live in acceptance.md, separate from the
  normative source). Verified examples: spec.md:106-107 (Ubiquitous), spec.md:130-132 (Unwanted, `If …
  then … shall not`), spec.md:139-140 (Event-driven, `When a user resolves a note, the system shall`).
  Defect: 7 of 8 AC entries are labeled `(Ubiquitous)` while carrying a state precondition (`Given two
  orders in the active tab …`, spec.md:166-169) — a Ubiquitous requirement by definition has no
  precondition; these are state-driven (`While …`) in EARS terms. REQ-GROUP-013 (spec.md:152) is
  labeled `(Unwanted)` but written in Ubiquitous form. REQ-GROUP-014 (spec.md:154-155) is labeled
  `(Unwanted)` but its subject is not the system and `If this SPEC is implemented` is not an undesired
  condition — it is a process/scope constraint wearing EARS clothing. Substance is sound; labels are wrong.

- **[PASS] MP-3 YAML frontmatter validity**: spec.md:1-11 contains `id: SPEC-ORDER-020` (string,
  matches SPEC-{DOMAIN}-{NUM}), `version: 1.0.0` (string), `status: draft` (string), `created_at:
  2026-08-13` (ISO date), `priority: Medium` (string), `labels: [order, line-item-note, frontend, ux]`
  (array). All six required fields present with correct types. Companion documents carry consistent
  `id`/`version`/`status` (acceptance.md:1-7, plan.md:1-7, spec-compact.md:1-7).

- **[N/A] MP-4 Section 22 language neutrality**: single-project SPEC scoped to one React/TypeScript
  page (`frontend/src/pages/LineItemNotesPage.tsx`) with an explicit no-backend-change constraint
  (spec.md:154-155). No multi-language tooling claims. Auto-passes.

---

## Focus Area 1 — Citation Accuracy (independently re-opened, every reference)

This was audited line-by-line against the repository, not against prior SPEC documents. **Result: zero
fabricated citations, zero drifted line numbers.** This is a material improvement over the incidents
recorded in SPEC-ORDER-016 v1.0.5 (fabricated `frontend/src/components/ResultSection.tsx`) and
SPEC-ORDER-018 v1.0.3 (+439-line citation drift), both of which I confirmed are accurately
characterized in spec.md:19.

Verified — `frontend/src/pages/LineItemNotesPage.tsx` (file is exactly 414 lines, matching plan.md:29):

| Citation | Claimed | Actual at that location | OK |
|---|---|---|---|
| `:306-414` | `LineItemNotesPage` | `export function LineItemNotesPage()` at 306, closing `}` at 414 | yes |
| `:309` | `useUnresolvedLineItemNotes()` | `const { data, isPending, isError } = useUnresolvedLineItemNotes()` | yes |
| `:313` | `tabNotes` | `const tabNotes = data ? filterNotes(data, activeTab) : []` | yes |
| `:35-49` | `filterNotes` | `function filterNotes(...)` at 35, `}` at 49 | yes |
| `:36` | 타출판사 filter | `if (tab === '타출판사') return notes.filter((n) => n.note_type === '타출판사')` | yes |
| `:38-46` | per-line_item Map aggregation | comment at 38, `latestByLineItem` loop closing at 46 | yes |
| `:48` | `assignee === tab` | `return Array.from(...).filter((n) => n.assignee === tab)` | yes |
| `:54-98` | `NoteHistory` | `function NoteHistory(...)` 54 → `}` 98 | yes |
| `:103-211` | `InlineNoteForm` | `function InlineNoteForm({` 103 → `}` 211 | yes |
| `:216-302` | `NoteCard` | `function NoteCard({` 216 → `}` 302 | yes |
| `:236-237` | expand toggle | `cursor-pointer select-none` / `onClick={() => setExpanded(...)}` | yes |
| `:240-245` / `:241` / `:244` | order-number button, `stopPropagation`+`navigate`, fallback | `<button>` 240-245; `navigate(\`/orders/${note.order_id}\`)` 241; `{note.order_name ?? \`주문 #${note.order_id}\`}` 244 | yes |
| `:246-259` / `:260` / `:266-272` | badges / truncated body / resolve button | assignee+note_type badges 246-259; `truncate max-w-[200px]` 260; resolve `<button>` 266-272 | yes |
| `:304-305` | `@MX:ANCHOR` + `@MX:REASON` | exactly those two comment lines | yes |
| `:325-341` | loading/error states | `if (isPending) {` 325 → error block `}` 341 | yes |
| `:343` / `:344` | `tabs` / `countByTab` | `const tabs: Tab[] = [...]` / `const countByTab = (tab) => (data ? filterNotes(data, tab).length : 0)` | yes |
| `:371-392` | 타출판사 Excel block | comment 371 → `)}` 392 | yes |
| `:394-398` / `:396` | empty-state branch / message | `{tabNotes.length === 0 && (` 394 → `)}` 398; `미해결 품목 메모가 없습니다.` at 396 | yes |
| `:400` / `:401-410` / `:400-411` | flat render target | `<div className="space-y-2">` 400; `tabNotes.map` 401-410; block closes 411 | yes |

Verified — other files:

- `frontend/src/features/order/hooks/useLineItemNotes.ts`: `:7` `LINE_ITEM_NOTES_QUERY_KEY`; `:33-34`
  `@MX:WARN`/`@MX:REASON`; `:35-59` `useResolveLineItemNote`; `:41-47` `onMutate` optimistic removal;
  `:61-69` `useUnresolvedLineItemNotes`; `:71-84` `downloadLineItemNotesExcel`. All exact.
- `frontend/src/types/order.ts`: `:103-110` `export interface LineItemNoteUnresolved extends
  LineItemNote { … }`; `:108` `order_id: number` — the non-null claim in spec.md:88 and plan.md:76 is
  correct. Cross-checked against the DB: `backend/order/models.py:169` `order = models.ForeignKey(Order,
  on_delete=models.CASCADE, …)` with no `null=True`, so the grouping key can never be null. Good.
- `backend/order/serializers.py`: `:79-97` `LineItemNoteUnresolvedSerializer`; `:85`
  `order_name = serializers.CharField(source="line_item.order.name", default=None)`; `:86`
  `order_id = serializers.IntegerField(source="line_item.order.id")`; `:94-97` `Meta.fields` including
  both. All exact.
- `backend/order/views.py`: `:269-282` `LineItemNoteUnresolvedListView`; `:275` `pagination_class = None`;
  `:279` `LineItemNote.objects.filter(is_resolved=False)`; `:251-296` the SPEC-ORDER-010 note API block.
  All exact.
- `backend/order/urls.py:160` → `path("orders/line-item-notes/", LineItemNoteUnresolvedListView.as_view(), …)`. Exact.
- `backend/order/models.py:238-289` → `class LineItemNote(models.Model)` at 238, class ends at 289
  (`ordering = ["-created_at"]` inside `Meta`). Exact.
- `frontend/src/pages/OrderDetailPage.test.tsx`: `:15-18` `vi.mock('@/features/order/hooks/useLineItemNotes', …)`;
  `:20-33` `renderPage()` with `QueryClient({defaultOptions:{queries:{retry:false}}})` + `QueryClientProvider`
  + `MemoryRouter`; `:1-33` conventions; `:35-95` `buildOrderDetail` fixture builder. All exact.
- `.moai/config/sections/quality.yaml`: `:4` `development_mode: "tdd"`, `:43` `test_first_required: true`,
  `:46` `min_coverage_per_commit: 80`. All exact.
- Regression-gate files named in acceptance.md:199-201 all exist (`OrderDetailPage.test.tsx`,
  `DashboardPage.test.tsx`, `ForbiddenPage.test.tsx`). `LineItemNotesPage.test.tsx` correctly does not
  exist yet and is marked `[NEW]` (spec.md:71).
- Cross-SPEC claims: commit `7b9f494` exists and is SPEC-ORDER-019; SPEC-ORDER-019 후속 과제 2 exists
  at `.moai/specs/SPEC-ORDER-019/spec.md:490-493` and does concern the `filterNotes` "LineItem당 최신
  1건" rule; SPEC-ORDER-016 v1.0.5 and SPEC-ORDER-018 v1.0.3/v1.0.4 histories match spec.md:19 and
  acceptance.md:21 verbatim in substance.

**Conclusion on Focus Area 1: PASS.** The HISTORY claim at spec.md:19 ("모든 `file:line` 인용은 이
세션에서 직접 재검증했다") is substantiated. Approximately 60 distinct citations checked; all resolve
to the claimed symbol.

---

## Focus Area 2 — Acceptance Criteria Discriminating Power

For each AC I constructed the concrete mutation and the no-op (revert-to-today's-code) case.

**No-op survival test — all 8 fail on current code.** Every scenario except AC-GROUP-007's second
clause performs its lookup *through* a group container (`within(그룹NNN)`), which does not exist in
today's flat `tabNotes.map` at LineItemNotesPage.tsx:400-411. AC-GROUP-007 discloses its own limitation
explicitly and honestly at acceptance.md:174-177 and spec.md:210-212, and carries revert-detection via
its first clause. **No AC survives a no-op implementation.** This is the correct answer to the
question the checklist asks, and it is a genuine improvement over the SPEC-ORDER-018 incidents.

Mutation-by-mutation adversarial check:

| AC | Wrong implementation I constructed | Caught? |
|---|---|---|
| 001 | Group only multi-note orders, render single notes bare | Yes — (c) requires order 802's single note in the same container structure |
| 001 | One wrapper per note (no actual merging) | Yes — header count would read "1", contradicting (b)'s "2" |
| 002 | Group with no sort / sort by `order_id` / sort ascending | Yes — arrival order [601,602,603] deliberately differs from expected [602,603,601] |
| 003 | No intra-group sort | Yes — arrival [21,22] (old first) vs required [22,21] |
| 004 | `countByTab` computed from group count | Yes — label would read "(2)" not "(4)"; line 366 renders `({countByTab(tab)})` as one text node, so the query is well-formed |
| 005 | Shared closed-over `order_id` across notes | **Not realizable** — see D10 |
| 006 | Remove entire group when one note resolves | **Not realizable** — see D10 |
| 006 | Leave empty group shell after last note resolves | Yes, and this one *is* realizable if the implementer groups raw `data` and filters inside groups |
| 007 | Phantom empty group wrapper on empty tab | Yes — and this is the same realizable mutation as above; the two ACs reinforce each other |
| 008 | Group before filtering instead of after | Yes — group count would read 2 and "발주 노트" would appear on the CS tab |
| 013 | Add a group-level bulk-resolve control | **Only partially** — see D7 |

**Conclusion on Focus Area 2: PASS with reservations.** No AC is a mere restatement of its requirement.
The suite catches every plausible mis-implementation I could construct except the bulk-resolve
prohibition (D7). Two ACs overstate their mutation stories (D10) but still fail on revert. Two fixtures
are defective as written (D1, D2), which is what drives the FAIL verdict — not weak discriminating power.

---

## Additional Checks Requested

- **Exclusions non-empty and meaningful**: PASS. spec.md:245-261 lists nine entries, each naming a
  specific artifact or decision rather than a vague sentiment — e.g. pagination/virtualization excluded
  with the reason cited to real code (`pagination_class = None`, views.py:275, verified); the Excel
  export flow excluded by naming `downloadLineItemNotesExcel` (useLineItemNotes.ts:71-84, verified) and
  the button block (`:371-392`, verified); the `filterNotes` "latest-per-LineItem" rule explicitly
  deferred to SPEC-ORDER-019 후속 과제 2 (verified to exist). Exclusions do not contradict any included
  requirement (checked each against REQ-GROUP-001..014).

- **Every REQ covered by at least one AC**: 13 of 14. REQ-GROUP-014 has no runtime AC; spec.md:238-241
  discloses this openly and maps it to the `git diff --stat backend/` gate at plan.md:170. The three
  traceability tables (spec.md:223-238, acceptance.md:183-192, plan.md:183-194) were compared entry by
  entry and agree with each other and with the per-AC `Traces:` lines in acceptance.md. No orphan ACs,
  no AC referencing a non-existent REQ.

- **Scope boundary "frontend-only, no backend change" is actually correct**: PASS, verified against the
  real response shape, not against the SPEC's assertion. `LineItemNoteUnresolvedSerializer.Meta.fields`
  (serializers.py:94-97) already emits both `order_id` and `order_name`; `LineItemNoteUnresolvedListView`
  returns the full unresolved set with `pagination_class = None` (views.py:275) ordered
  `-created_at` (views.py:281), so client-side grouping over the complete set is possible with no new
  query parameter and no cross-page grouping hazard; `LineItemNoteUnresolved` (types/order.ts:103-110)
  already types both fields; `order_id` is non-null all the way down (serializers.py:86 has no
  `default=None`, models.py:169 FK is non-nullable, types/order.ts:108 is `number`). The backend's
  `-created_at` ordering also substantiates the SPEC's rationale at spec.md:50-51 and 85 that
  newest-first is what users see today — I checked this rather than taking it on trust. **No backend
  change is required. The scope boundary is sound.**

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 — minor ambiguity in one or two requirements | Core requirements unambiguous (spec.md:106-155). Deductions: "correctly" at spec.md:207 / "올바르게" at acceptance.md:168 (D6); "동일한 구조 — 예: 동일한 역할/테스트 훅 속성" leaves the structural-equivalence assertion to the implementer (acceptance.md:53-54, D11); REQ-GROUP-008 is written in terms of "assignee scope" (spec.md:130-132) but the 타출판사 tab filters on `note_type` (LineItemNotesPage.tsx:36), so that tab is covered only indirectly via REQ-GROUP-002 |
| Completeness | 0.80 | between 0.75 and 1.0 | All required sections present: HISTORY (spec.md:15-19), 문제 정의 (WHY, :23-42), 솔루션 개요/범위 (WHAT, :44-71), 요구사항 (:99-155), ACCEPTANCE CRITERIA (:159-241), Exclusions (:245-261), plus 명시적 가정 and 후속 과제. Frontmatter complete. Deductions: acceptance.md fixtures are incomplete in two load-bearing ways (D2, D9) |
| Testability | 0.70 | between 0.50 and 0.75 | Eight ACs, all failing on a no-op, each stating its own breaking mutation (spec.md:170-219). Deductions: one fixture is internally contradictory (D1), one is unsatisfiable as literally written (D2), the bulk-resolve prohibition is verified by an enumerated-label absence check that a differently-labeled control would pass (D7), no tie-break is specified for equal `created_at` (D8), and two stated mutations are unrealizable under the SPEC's own constraints (D10) |
| Traceability | 0.90 | between 0.75 and 1.0 | Three independent traceability tables agree entry-for-entry (spec.md:223-238, acceptance.md:183-192, plan.md:183-194); per-AC `Traces:` lines match the tables exactly. One REQ (014) has no runtime AC, disclosed and gated (spec.md:238-241, plan.md:170) |

---

## Defects Found

**D1. acceptance.md:43 — fixture count contradicts its own enumeration. Severity: major.**
`useUnresolvedLineItemNotes`가 다음 노트 **4건**을 반환하도록 모킹한다" is followed by exactly three
notes (acceptance.md:44-46: ids 1, 2, 3) and by a parenthetical that itself says "order_id 801에 2건,
order_id 802에 1건" — i.e. three. spec.md:166-167 ("one order has two eligible notes and the other has
one") and spec-compact.md:76 ("2주문(한쪽 2건)") both confirm three is correct. The literal "4건" is
wrong. This is the same class of doc/test mismatch recorded as D4 in SPEC-ORDER-018 v1.0.3.

**D2. acceptance.md:164-168 (AC-GROUP-007) — fixture is unsatisfiable as literally written. Severity: major.**
The Given places "노트 2건" on a single order (1301) but, uniquely among the multi-note fixtures in this
document, does not state that the two notes have different `line_item_id`. `filterNotes`
(LineItemNotesPage.tsx:38-46) collapses notes to one per `line_item_id` on the CS tab, so a literal
implementation with a shared `line_item_id` yields a one-note group and makes Then(1차) — "그룹
컨테이너가 올바르게 렌더링되고 **노트 2건을 포함한다**" (acceptance.md:168) — unachievable. Every other
multi-note fixture is explicit about this: AC-001 (acceptance.md:47), AC-003 (9101/9102, :85-86),
AC-004 (9401-9404, :98-99), AC-006 (9701/9702, :143-144), AC-008 (9501/9502, :112-113). AC-007 is the
sole omission, so this is an oversight rather than a convention. Since T7's first clause is the *only*
thing giving that scenario revert-detection (acceptance.md:174-177 states this explicitly), a broken
first clause would silently strip AC-GROUP-007 of all discriminating power.

**D3. plan.md:62 — factually incorrect claim about Vitest module mocking. Severity: major.**
The text states that `useCreateLineItemNote`/`useLineItemNotes` need not be mocked because "해당
컴포넌트들은 **실제 훅을 호출**하지만 렌더되지 않는 조건부 분기 안에 있다". Under
`vi.mock(path, factory)` the entire module is replaced, so the real hooks are never reachable — the
components would resolve to the mock's (absent) exports, and Vitest throws
`No "useLineItemNotes" export is defined on the mock` on access. The conclusion (they need not appear
in the factory, given no scenario expands a `NoteCard`) happens to hold, but the stated reason is
wrong. The same sentence also omits `LINE_ITEM_NOTES_QUERY_KEY` and `downloadLineItemNotesExcel`, which
`LineItemNotesPage.tsx:3` and `:10` import from the very module being mocked — safe only because no
T1-T8 scenario reaches the 타출판사 export path. Since plan.md:22 flags that this SPEC *establishes*
the mocking convention for this page (R5, plan.md:137), a wrong rationale here propagates.

**D4. spec.md:154-155 (REQ-GROUP-014) — not a system-behavior requirement. Severity: minor.**
"If this SPEC is implemented, then no backend endpoint, serializer field, database model, or migration
shall be added or changed." The subject is not the system, and "if this SPEC is implemented" is not an
undesired condition — this is a process/scope constraint formatted as EARS Unwanted. It is also the
only REQ without a runtime AC (spec.md:238). The constraint itself is correct and worth keeping; the
EARS framing is not.

**D5. spec.md:152 (REQ-GROUP-013) — pattern label mismatch. Severity: minor.**
Labeled `(Unwanted)` but written as "The system shall not provide a control that…" — Ubiquitous form.
No `If [undesired condition], then` structure.

**D6. spec.md:205-207 / acceptance.md:168 — weasel word in an acceptance criterion. Severity: minor.**
"the system shall render the populated tab's group container(s) **correctly**" / "그룹 컨테이너가
**올바르게** 렌더링되고". "Correctly" is not binary-testable on its own. The accompanying clause
("노트 2건을 포함한다") saves it — but see D2, which breaks exactly that clause.

**D7. spec.md:169 / acceptance.md:55-56 — REQ-GROUP-013 is verified by an enumerated-label absence check. Severity: minor.**
The only verification of "no bulk resolve control" is: "그룹 헤더 스코프에서 '**전체 해결**'·'**모두
해결**' 등의 라벨을 가진 요소를 찾으면 발견되지 않는다". A bulk control labeled "일괄 해결",
"선택 해결", or an icon-only button passes this check unchanged. React Testing Library's default text
matcher is full-string normalized, so a `getAllByText('해결')` count assertion would not catch
"일괄 해결" either. A count-based assertion (number of resolve controls within a group === note count,
using a role+accessible-name query robust to substrings) would be discriminating; the enumerated-label
form is not.

**D8. spec.md:120-123 (REQ-GROUP-005, REQ-GROUP-006) — no tie-break for equal `created_at`. Severity: minor.**
Both ordering requirements key solely on `created_at` with no secondary key. All ordering fixtures use
distinct timestamps (acceptance.md:69-71, :85-86), so a non-deterministic sort would pass every AC. This
is structurally the same defect SPEC-ORDER-018 v1.0.3 D1 had to remediate (ordering assertion that
survived removal of the `"pk"` tie-break). Relevant here because SPEC-ORDER-019 introduced bulk
creation of `assignee="발주"` notes from Daily Review uploads, which is the realistic source of
near-simultaneous timestamps on one order.

**D9. acceptance.md:31-33 — fixture field policy omits a load-bearing field. Severity: minor.**
The notation lists nine fields including `note_type`, then permits arbitrary values only for
`author_username`, `line_item_sku`, `line_item_title`, `confirmed_distributor`. But `note_type` is
never given a value in AC-002/003/004/005/006/008 and is load-bearing: LineItemNotesPage.tsx:41 skips
any note whose `note_type === '타출판사'` on the CS/발주 tabs. An author filling it "arbitrarily" per
line 33 can zero out the fixture. `created_at` is likewise unspecified in AC-004's fixture
(acceptance.md:98-99) — harmless there since its assertions are order-independent, but inconsistent
with the rest of the document.

**D10. spec.md:193-195 and :201-203 — two "mutation that breaks it" claims are not realizable under this SPEC's own constraints. Severity: minor.**
AC-GROUP-005 claims a loop-closure bug sharing one `order_id` across notes would break it. That bug
cannot occur: `NoteCard` is unmodified (spec.md:66, plan.md:41-42) and reads `note.order_id` from its
own prop at LineItemNotesPage.tsx:241. AC-GROUP-006 claims "removing the whole group when any one of
its notes is resolved" would break it; groups are re-derived from `tabNotes` on every render
(plan.md:64), so no code path produces that behavior either. Both ACs still fail on revert (their
lookups go through a group container), so discriminating power is preserved — but the stated mutations
are fiction, and this document's own [HARD] contract at spec.md:161-164 is that each item "명시한다"
the mutation that breaks it. AC-GROUP-006's *second* mutation (empty group shell left behind) is real
and worth keeping.

**D11. acceptance.md:53-54 — assertion mechanism deferred to the implementer with "예:". Severity: minor.**
"(c) order_id 802의 노트도 그룹 컨테이너로 렌더링되며(그룹801과 동일한 구조 — **예**: 동일한
역할/테스트 훅 속성)". "Same structure" is not operationalized; the illustrative "예:" makes even the
suggested mechanism optional. Since the implementer both defines the group container marker and writes
the test, this is the one place where the suite's revert-detection could be weakened without violating
the letter of the document. plan.md:165-166 partially compensates by requiring explicit confirmation
that T1-T6/T8 fail on reverted code.

**D12. spec.md:166, 173, 179, 184, 190, 205, 214 — seven of eight AC pattern labels are wrong. Severity: minor.**
Each is labeled `(Ubiquitous)` while opening with a state precondition ("Given two orders in the active
tab where…", "Given three single-note orders whose…"). A Ubiquitous EARS requirement has no
precondition; these are state-driven and would be written "While …, the system shall …". AC-GROUP-006
(spec.md:197) is correctly labeled `(Event-Driven)` and does contain a `when … the system shall` core.

---

## Chain-of-Verification Pass

Second-look findings after re-reading sections I had moved through quickly on the first pass:

1. **Re-read every REQ end-to-end (not just the first four).** REQ-GROUP-009 through 014 were only
   skimmed initially. On re-read I found D4 (REQ-GROUP-014's non-system subject) and D5 (REQ-GROUP-013's
   label mismatch), neither of which I had flagged in pass 1.
2. **Re-checked REQ sequencing exhaustively** via `grep -o "REQ-GROUP-[0-9]*" | sort -u` rather than
   spot-checking the first and last. Confirmed 001-014 complete with no duplicates; also confirmed
   every REQ ID that appears anywhere in the three documents is one of those 14 (no dangling
   REQ-GROUP-015 etc.).
3. **Re-verified traceability for all 14 REQs, not a sample**, comparing all three tables plus the
   per-AC `Traces:` lines. No mismatch. I had initially planned to sample; the full check changed
   nothing but is now evidence-backed.
4. **Re-read the Exclusions section for specificity, not just presence.** All nine entries name concrete
   artifacts; I then verified two of the code claims inside them (`pagination_class = None` at
   views.py:275 and `downloadLineItemNotesExcel` at useLineItemNotes.ts:71-84) rather than trusting them.
5. **Cross-requirement contradiction sweep.** Checked REQ-GROUP-004 (single-note groups use the same
   container) against REQ-GROUP-011 (remove container when empty) — consistent. Checked REQ-GROUP-002
   (build from filter output) against REQ-GROUP-007 (tab counts from filter output) — consistent and
   mutually reinforcing. Checked Exclusions against every REQ — no conflict. Noted that REQ-GROUP-002's
   clause "shall not modify or bypass that filter" is an implementation constraint rather than a pure
   behavioral statement (RQ-3), as is REQ-GROUP-014; both are defensible for a brownfield SPEC whose
   central risk is scope creep, so I am not raising them as separate defects.
6. **Re-examined the fixtures I had accepted on first read.** This is where D1 and D2 surfaced — the
   "4건" contradiction at acceptance.md:43 and the missing `line_item_id` distinctness in AC-GROUP-007.
   I had read both paragraphs in pass 1 and not caught either. D9 came from the same re-read.
7. **Re-derived the current tab-ordering behavior from source rather than from the SPEC's description.**
   `filterNotes` inserts into a `Map` keyed by `line_item_id` in arrival order and only replaces values
   (never re-inserts keys), so output order follows the backend's `-created_at` ordering
   (views.py:281). The SPEC's claim at spec.md:50-51 that grouping by each group's newest note preserves
   today's perceived order is therefore correct. No defect — recording it because I would otherwise have
   accepted an unverified rationale.

---

## Regression Check

Not applicable — iteration 1.

---

## Recommendation

FAIL. Three major defects must be corrected before the RED phase begins. All are cheap to fix; none
require rethinking the design. The SPEC's core engineering — citation accuracy, no-op-detecting
acceptance criteria, and the frontend-only scope boundary — is sound and verified.

Required fixes:

1. **acceptance.md:43** — change "다음 노트 4건을 반환하도록" to "다음 노트 3건을 반환하도록"
   (D1). Cross-check that spec.md:166-167 and spec-compact.md:76 remain consistent after the edit.

2. **acceptance.md:164-166** — make the AC-GROUP-007 fixture explicit and complete, matching the
   precision of every other multi-note fixture in the document (D2). It must state distinct
   `line_item_id` values, and should state `id` and `created_at` values, for the two notes on order
   1301. Without distinct `line_item_id`s, `filterNotes` (LineItemNotesPage.tsx:38-46) collapses them
   and Then(1차) at acceptance.md:168 cannot be satisfied — which would also destroy the only
   revert-detection this scenario has.

3. **plan.md:62** — correct the mocking rationale (D3). Replace "해당 컴포넌트들은 실제 훅을
   호출하지만 렌더되지 않는 조건부 분기 안에 있다" with an accurate statement: `vi.mock` with a factory
   replaces the whole module, so any export omitted from the factory throws on access; omitting
   `useCreateLineItemNote`/`useLineItemNotes`/`LINE_ITEM_NOTES_QUERY_KEY`/`downloadLineItemNotesExcel`
   is safe only because no T1-T8 scenario expands a `NoteCard` or clicks the 타출판사 export buttons.
   State that constraint explicitly so a future test author who adds an expand scenario knows to extend
   the factory.

Recommended (not blocking, but each closes a real hole):

4. **spec.md:169 and acceptance.md:55-56** — replace the enumerated-label absence check for
   REQ-GROUP-013 with a count-based assertion: the number of resolve controls within a group container
   equals the number of note rows in that group (D7). The current form passes if a bulk control is
   labeled anything other than "전체 해결" or "모두 해결".

5. **spec.md:120-123** — add a deterministic tie-break to REQ-GROUP-005 and REQ-GROUP-006 for equal
   `created_at` (e.g. `order_id` and `id` descending), and give one ordering fixture a duplicate
   timestamp so the tie-break is actually exercised (D8). This is the SPEC-ORDER-018 v1.0.3 D1 lesson
   applied preventively, and it is directly relevant given SPEC-ORDER-019's bulk note creation.

6. **spec.md:193-195 and :201-203** — replace the two unrealizable mutations (D10) with realizable
   ones. For AC-GROUP-005, the realizable failure is a grouping implementation that renders the wrong
   notes under a group header (e.g. mapping over `tabNotes` inside each group instead of over that
   group's own notes). For AC-GROUP-006, the realizable failure is already stated as its second
   mutation — keep that and drop the first.

7. **acceptance.md:31-33** — add `note_type` (and `is_resolved`) to the explicitly-defaulted field list
   with a stated safe default, noting that `note_type === '타출판사'` is load-bearing at
   LineItemNotesPage.tsx:41 and must not be chosen arbitrarily (D9).

8. **spec.md:152, 154-155, and the eight AC pattern labels** — correct the EARS labels (D4, D5, D12).
   AC-GROUP-001/002/003/004/005/007/008 are state-driven, not Ubiquitous; REQ-GROUP-013 is Ubiquitous,
   not Unwanted; REQ-GROUP-014 should either be restated with the system as subject or moved out of the
   EARS requirement list into the Exclusions/scope section where a process constraint belongs (its
   substance is correct and its `git diff --stat backend/` gate at plan.md:170 should be retained
   either way).

9. **spec.md:207 / acceptance.md:168** — remove "correctly" / "올바르게" and let the concrete clause
   carry the assertion (D6). **acceptance.md:53-54** — replace "예: 동일한 역할/테스트 훅 속성" with a
   binding statement of how structural equivalence is asserted (D11), since the same person writes both
   the marker and the test.

Verdict: FAIL
