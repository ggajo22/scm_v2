# Progress Log — SPEC-PURCHASE-ORDER-006

## Phase 1 — Data layer (T-001, REQ-PO6-001)

- RED: added `TestYes24DataModel` in `backend/order/tests/test_purchase_orders.py`
  (create/query by sku, unique constraint). Confirmed failure: `ImportError: cannot
  import name 'Yes24Data' from 'order.models'`.
- GREEN: added `Yes24Data` model in `backend/order/models.py` (sku unique, price,
  list_price, status, updated_at). Generated migration via
  `python manage.py makemigrations order` → `backend/order/migrations/0024_yes24data.py`
  (depends on `0023_rename_bookseen_to_booxen`, CreateModel + index, matches
  `0013_split_vendor_data.py` KyoboData pattern).
- Verified: `pytest order/tests/test_purchase_orders.py::TestYes24DataModel` → 2 passed.
- Task status: T-001 done.

## Phase 2 — Parser layer (T-002/T-003, REQ-PO6-002/003/008)

- RED: added `_make_yes24_excel` fixture helper (1 header row, 15 real YES24
  columns) and 8 test cases in `TestParseVendorExcel` (column mapping, 1-row
  header skip, 6 유통상태 values via parametrize, invalid ISBN exclusion, empty
  file ValueError). Confirmed failure: dispatch fell through to
  `_parse_generic_xlsx` (yes24 branch not wired) → mis-mapped columns / no
  ValueError on empty data.
- GREEN: added `_YES24_COL_*` constants and `_parse_yes24_xlsx()` in
  `backend/order/excel_utils.py` (skips only `rows[0]`, `sku.isdigit()`
  validity check, returns `sku`/`available` (always None)/`price`/
  `list_price`/`status`). Wired `distributor == "yes24"` into
  `parse_vendor_excel()` dispatch, preserving order (booxen .xls magic bytes →
  kyobo → yes24 → generic fallback).
- Verified: `pytest order/tests/test_purchase_orders.py -k yes24` → 12 passed
  (2 model + 10 parser, including 6 parametrized status cases).
- Task status: T-002, T-003 done.

## Phase 3 — API view layer (T-004/T-005, REQ-PO6-004/005/009)

- RED: added 4 tests to `TestUploadVendorFileView` (create via YES24 upload,
  upsert on re-upload, `unknown_vendor` → 400 with "yes24" in message, empty
  YES24 file → 422). Confirmed failure: `distributor="yes24"` still rejected
  with 400 (`VENDOR_FILE_DISTRIBUTORS` not yet updated); upsert test failed
  because price wasn't updated (branch not implemented).
- GREEN: added `Yes24Data` to the models import and `"yes24"` to
  `VENDOR_FILE_DISTRIBUTORS` in `backend/order/purchase_order_views.py`.
  Changed `UploadVendorFileView.post()` from a 2-branch
  (`if booxen / else kyobo`) to 3-branch structure
  (`if booxen / elif yes24 / else kyobo`). The yes24 branch passes only
  `price`, `list_price`, `status` into `Yes24Data.objects.update_or_create()`
  defaults (does not reuse booxen/kyobo-only local vars stock/returnable/
  arrival/publisher/ordered_qty/total_price). `list_price` is extracted
  locally from `row.get("list_price")` and converted via
  `Decimal(str(...))`, mirroring the existing `price`/`total_price` pattern.
  booxen/kyobo branches left untouched.
- Verified: `pytest order/tests/test_purchase_orders.py::TestUploadVendorFileView`
  → 9 passed (5 existing booxen/kyobo + 4 new yes24), no regressions.
- Task status: T-004, T-005 done.

## Phase 4 — Frontend (T-006/T-007, REQ-PO6-006/007, AC-008)

- RED: created `frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.test.tsx`
  (no prior frontend test files existed in the repo — confirmed Vitest +
  React Testing Library + happy-dom via `vitest.config.ts`/`package.json`).
  2 tests: dropdown renders 북센/교보/YES24; selecting YES24 + uploading a
  file calls the mocked `useUploadVendorFile().mutate` with
  `distributor=yes24` in the FormData. Confirmed failure: option list only
  had 북센/교보; `selectOptions(select, 'YES24')` threw
  `Value "YES24" not found in options`.
- GREEN: updated `DISTRIBUTOR_OPTIONS` to
  `['북센', '교보', 'YES24'] as const`, added `'YES24': 'yes24'` to
  `DISTRIBUTOR_API_KEY`, and updated the helper text to
  "북센·교보·YES24 파일 업로드 후 ..." in
  `frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.tsx`. The
  `uploadedCounts` display loop already iterates `DISTRIBUTOR_OPTIONS`
  generically — no change needed there.
- Note (test-environment-only issue, not a production bug): initial version
  of the file-upload test used `@testing-library/user-event`'s
  `user.upload()`, which triggered a `RangeError: Maximum call stack size
  exceeded` inside React's event-dispatch reporting under happy-dom
  (confirmed via a temporary `console.error` spy). Reproduced the same
  assertions with `fireEvent.change()` instead — zero errors, same pass
  result — confirming this was a `userEvent.upload` + happy-dom interaction
  artifact, not a bug in `handleFileInput`'s `e.target.value = ''` reset.
  Finalized the test using `fireEvent.change()`.
- Verified: `npx vitest run --config vitest.config.ts
  src/pages/PurchaseOrders/tabs/VendorFileUploadTab.test.tsx` → 2 passed, no
  console errors.
- Task status: T-006, T-007 done.

## Phase 5 — Regression gate (T-008, REQ-PO6-010)

- `order/tests/test_auto_dist.py`: 38 passed, unchanged (auto_select_distributor
  3-step decision tree, price-diff alert logic — no yes24 integration, as
  required by the exclusion scope).
- `order/tests/test_purchase_orders.py`: 111 passed (full file, including all
  pre-existing booxen/kyobo/PO-list/refund/line-item-status tests plus the
  new 14 YES24 tests: 2 model + 10 parser + wait — see below for exact
  breakdown). Confirmed via a clean sequential run (`pytest
  order/tests/test_purchase_orders.py --no-cov`) → `111 passed in 229.58s`.
  (An earlier attempt that ran this file concurrently with a second
  module-scoped coverage process against the same MySQL test database
  produced spurious ERRORs/1 FAILED from DB contention between the two
  parallel pytest processes — not a code defect. Re-ran sequentially and
  confirmed 111/111 pass cleanly, reproduced twice.)
- Combined run `test_purchase_orders.py + test_auto_dist.py` with
  `--cov=order.models --cov=order.excel_utils --cov=order.purchase_order_views`:
  **149 passed**, 0 failed. Coverage of the 3 changed modules:
  - `order/models.py`: 96% (only pre-existing `__str__` dunder methods
    uncovered across all vendor-data models, including `Yes24Data.__str__`
    at line 327 — consistent with existing BooxenData/KyoboData pattern)
  - `order/excel_utils.py`: 69% (new `_parse_yes24_xlsx` fully covered
    except defensive `except` fallback branches for malformed workbook /
    non-numeric price cells — same untested-fallback pattern as the
    pre-existing `_parse_kyobo_xlsx`/`_parse_booxen_xls`)
  - `order/purchase_order_views.py`: 65% (new `elif distributor == "yes24"`
    upsert branch, lines 330-338, fully covered — not present in the
    coverage tool's "Missing" line list)
  - The project's global `--cov-fail-under=90` (pytest.ini) only passes when
    the *entire* test suite runs (covering `accounts/` and all `order/`
    test modules together); running a subset of test files against that
    global threshold fails as expected and is not indicative of a
    regression in the YES24 changes themselves.
- `generate_order_excel()` / `VALID_DISTRIBUTORS` (PO generation,
  `GenerateOrderFileView`): untouched — verified via `git diff` scope (no
  edits to these symbols) and no failures in
  `TestPurchaseOrderListView`/generate-order-file related tests.
- `DailyReviewTab.tsx` and Daily Review upload/download logic: untouched
  (out of SPEC scope, not modified).
- Task status: T-008 done. All SPEC-PURCHASE-ORDER-006 tasks (T-001–T-008)
  complete.

## Lint / Format

- `ruff check` on the 4 modified backend files: 48 pre-existing errors
  remain (E501 long lines, F821 forward-ref, F401 unused import — all in
  code untouched by this SPEC, e.g. `generate_daily_review_excel`,
  `auto_select_distributor`, other PO-list test methods). Confirmed via
  line-range grep that zero ruff errors fall within any newly added code
  (Yes24Data model, `_parse_yes24_xlsx`, the yes24 upsert branch, or any new
  test method). One line I directly edited (the `.models` import in
  `purchase_order_views.py`, extended to add `Yes24Data`) was reformatted to
  a multi-line import to stay under the 100-char limit.
- `ruff format --check`: pre-existing formatting drift across all 4 files
  (unrelated to this SPEC, e.g. `generate_daily_review_excel`,
  `LineItemNote.line_item` FK). New YES24 code matches surrounding
  booxen/kyobo style intentionally and is not flagged in the format diff
  for `purchase_order_views.py`'s new branch or `VENDOR_FILE_DISTRIBUTORS`
  line. Did not run whole-file `ruff format` (would touch large amounts of
  unrelated pre-existing code — out of scope per Rule 5).
- Frontend `tsc -b --noEmit`: pre-existing type errors in unrelated files
  (`BookDetailPage.tsx`, `DashboardPage.test.tsx`, `ConfirmOrderTab.tsx`,
  `purchaseOrderApi.ts`) — zero errors in `VendorFileUploadTab.tsx` or
  `VendorFileUploadTab.test.tsx`.
- Frontend `eslint` on both modified/created files: clean, no errors.
- Frontend full `vitest run`: 11 test files, 80 tests, all passing
  (including the 2 new YES24 tests).
