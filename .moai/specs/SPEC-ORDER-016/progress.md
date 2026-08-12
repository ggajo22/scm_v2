---
id: SPEC-ORDER-016
document: progress
updated: 2026-08-12
---

# SPEC-ORDER-016 Progress

- Started: 2026-08-12
- Development mode: TDD (RED-GREEN-REFACTOR)
- Harness level: standard (feature + multi_domain)
- Scale mode: Full Pipeline (files ~13, domains 2)
- Execution order: backend → frontend (sequential, user-confirmed)

## Phase Log

- Phase 0.9 complete: Python/Django (backend/pytest.ini, manage.py) + TypeScript/React (frontend/package.json)
- Phase 0.95 complete: Full Pipeline selected
- Phase 1 complete: plan.md v1.0.4 (plan-auditor 3-iteration audited) adopted as execution plan; no re-planning needed
- Decision Point 1: user approved — sequential, backend first
- Phase 1.5 complete: 5 stage tasks registered (A backend impl, B backend regression, C frontend impl, D frontend tests, E quality gate)

- Stage A complete (manager-tdd): `purchase_order_views.py` +425 (pure insertion), `urls.py` +18, `test_spec_016.py` NEW 963 lines / 33 tests / T1-T19, `pytest.ini` +2 (concurrency marker).
  - test_spec_016: 32 passed + 1 concurrency-marked passed
  - test_spec_015: 124 passed, file unmodified
  - `makemigrations --check`: No changes detected
  - ruff: baseline 31 errors before and after in touched files, 0 inside inserted ranges
  - Drift: planned 3 backend files, actual 4 (pytest.ini marker registration, required by plan.md 동시성 테스트 기법 §3) → 33% of planned-new but 1 unplanned file, informational
- Stage B complete: `_process_outbound_rows` and both existing outbound endpoints have zero diff (445 insertions, 0 deletions across backend)
- Orchestrator correction: `urls.py` SPEC-016 comment claimed the routes were registered ahead of the `<int:pk>` patterns; they are registered after (harmless — static 3-segment paths cannot be shadowed by 4-segment `<int:pk>` patterns). Comment rewritten to state the real reason.

- Stage C+D complete (expert-frontend): `outboundApi.ts` +60, `useOutboundQueries.ts` +42, `OutboundPage/index.tsx` +193/-31, `UnmatchedForceSection.tsx` NEW 151, `UnmatchedForceSection.test.tsx` NEW 240, `logisticsStatusLabels.ts` NEW 17, 3 existing test files extended (+546)
  - `npx vitest run`: 23 files / 221 tests passed (independently re-run by orchestrator)
  - `npx tsc -b`: errors only in BookDetailPage.tsx, DashboardPage.test.tsx, ConfirmOrderTab.tsx, purchaseOrderApi.ts — all pre-existing, none in touched files (independently re-run)
  - `git diff --stat frontend/`: only the 6 intended files; `router/index.tsx`, `Sidebar.tsx`, `types/order.ts` zero diff
  - Deviation from plan: plan.md prescribed a `useEffect` selection reset; eslint rule `react-hooks/set-state-in-effect` forbids it, so the render-time "adjust state when a prop changes" pattern was used instead. Behaviourally identical, one fewer render.
- Phase 2.8a complete (evaluator-active, standard harness): **PASS** — Functionality 0.92, Security 0.90, Craft 0.82, Consistency 0.78. Verified the lock is load-bearing by removing `select_for_update()`, observing the concurrency test fail (`shipped_quantity` reached 12 > `quantity` 10), then reverting. All 21 Exclusions compliant. No critical findings.
- Post-evaluation fixes complete: 3 test gaps closed in `test_spec_016.py` only, implementation untouched (T20 force-process tie-break write-side, T21 `string_target`/`bool_target` gate cases incl. the `True`-as-int-subclass path, T22 non-list `rows` 400 branch). `pytest order/tests/test_spec_016.py --no-cov -m "not concurrency"` → **36 passed** (independently re-run by orchestrator); concurrency test 1 passed separately. `git diff --stat backend/` unchanged at 444 insertions / 0 deletions.
- Stage E complete: all 21 Exclusions verified compliant; 8 MX tag declarations added (6 NOTE, 1 WARN+REASON, 1 ANCHOR+REASON) backend + 1 NOTE frontend, all carrying required REASON sub-lines; run phase quality gate PASS.

## Run phase outcome

Implementation complete and verified. NOT committed — awaiting user decision. Remaining work belongs to `/moai sync`: correct the fabricated citations (below), update `product.md`, transition `spec.md` `draft → completed`, update HISTORY.

## Documentation defect — SPEC citations are fabricated [BLOCKS status: completed]

`spec.md`, `spec-compact.md`, `plan.md` and `research.md` all cite `frontend/src/components/ResultSection.tsx` as a shared component with 4 external call sites at `frontend/src/pages/InboundPage/index.tsx:176/:194/:211` and `PurchaseOrders/tabs/DailyReviewTab.tsx:153`. Verified independently: **none of these exist.** `ResultSection` is a private, non-exported function inside `frontend/src/pages/OutboundPage/index.tsx:345`, called twice from that same file. There is no `InboundPage` anywhere in the repo, and `DailyReviewTab.tsx` never references `ResultSection`.

Impact: no REQ or AC is invalidated — the architectural decision to build a separate `UnmatchedForceSection` still stands on its own local merits (the `cells: string[]` contract genuinely cannot carry a checkbox or picker). But 설계 결정 M's stated evidentiary basis is fictional, and the DoD item "공유 결과 섹션 컴포넌트의 4개 외부 호출부 및 그 테스트 무변경 통과" plus the corresponding acceptance.md 회귀 clause are unverifiable as written — there is no such regression surface. Three plan-auditor iterations did not catch this.

Required in sync phase: correct these citations in all four documents before `spec.md` transitions `draft → completed`. The label-mapping convention reference `InboundPage/index.tsx:30-32` in plan.md is fabricated too.

## Stale line references

`plan.md` / `research.md` cite `purchase_order_views.py:2810-3101` for `_process_outbound_rows`; the function is actually at line 2423 in the current file. Line citations in the SPEC documents drifted and should not be trusted verbatim.

## Constraints carried into implementation

- `backend/pytest.ini` addopts includes `--cov=accounts --cov-fail-under=90`; running only order tests requires `--no-cov`
- Shared remote MySQL test DB: NEVER run two pytest processes concurrently
- AC-FORCE-023 concurrency test uses `transaction=True` (TRUNCATE side effect) — isolate behind a dedicated pytest marker
- T8 query budget has only 1 query of headroom — no query may be added to the normal outbound path
