# Patch Sync Report — Cross-Order SKU Collision Safety Fix

**Report Date**: 2026-08-11 22:10:15 UTC  
**Completed SPECs**: 2  
**Implementation Status**: Both COMPLETED with bug-fix patches  
**Documentation Status**: Synchronized with implementation

---

## Executive Summary

Two already-completed SPECs (SPEC-ORDER-011, SPEC-PURCHASE-ORDER-008) discovered and shipped real production bugs today during live support investigation. A Daily Review upload (order #37893 vs #37918, SKU `9788998441012`) revealed that shipment/receipt/daily-review uploads matching by SKU alone incorrectly collapsed different orders' LineItems into one when they shared the same product.

**Key Findings**:
- ✅ SPEC-ORDER-011: **BugFix** — REQ-LOGI-003b/005b now enforces (Order.name, SKU) tuple matching instead of SKU-only; prevents cross-order collision in logistics uploads
- ✅ SPEC-PURCHASE-ORDER-008: **BugFix + 1 New Requirement** — REQ-PO8-018 (same cross-order collision fix for Daily Review) + REQ-PO8-019 (PurchaseOrder status="confirmed" on creation by this view)
- ✅ All regression tests pass (184 total across 3 test files, 0 failed)
- 📝 Production data correction applied directly to DB (not a code/doc change; already complete)

**Trigger**: Production bug investigation found that a single Daily Review upload could incorrectly link multiple orders' LineItems to one PurchaseOrder, causing wrong logistics status and warehouse location assignments. Fix required adding mandatory order-name column to all logistics/daily-review upload parsers.

---

## Phase 1: Trigger Analysis

### SPEC-ORDER-011 (LineItem 물류 상태 추적)

**Commit**: d22818f  
**Date**: 2026-08-11 22:10:15 UTC  
**Root Cause**: `UploadVendorShipmentView` and `UploadWarehouseReceiptView` parsed uploads by SKU only. When two different orders had the same SKU, an upload meant for one order would transition logistics_status for both.

#### Requirements Already Defined, Now Implemented

| Requirement | Purpose | Status |
|------------|---------|--------|
| **REQ-LOGI-003b** (Ubiquitous) | All-or-nothing transaction + atomic commit | ✅ Implemented with (Order.name, SKU) tuple matching |
| **REQ-LOGI-005a** (Ubiquitous) | Same atomicity + deduplication for warehouse receipts | ✅ Implemented with (Order.name, SKU) tuple matching |

#### Code Changes

- **Parser Rewrite**: `_parse_sku_only_xlsx()` → `_parse_name_sku_xlsx()` (new name reflects dual-column requirement)
  - Now requires "Name"/"주문번호" column (exact string, case-sensitive) alongside SKU/ISBN
  - Raises `ValueError` if order-name column missing (same rejection pattern as missing SKU/선택 columns)
- **Upload Logic Rewrite**: `_apply_logistics_transition()` now matches by (Order.name, sku) tuple instead of sku alone
  - Same-name Order collisions resolved oldest-pk-wins (mirrors SPEC-ORDER-015 outbound pattern)
  - New helper function: `_get_order_by_name()` with primary key ordering

#### New Regression Tests Added

- `test_spec_011.py` + `test_spec_012.py`: 8 new scenarios covering:
  - Two orders sharing same SKU: upload for order A does not affect order B's LineItem
  - Cross-order isolation verified across shipment + warehouse receipt paths
  - Missing order-name column rejection test

**Test Results**: 89 passed (test_spec_011 + test_spec_012 combined)

---

### SPEC-PURCHASE-ORDER-008 (Daily Review 업로드 외부 템플릿 파싱)

**Commit**: d22818f (same commit, three changes bundled)  
**Date**: 2026-08-11 22:10:15 UTC  
**Root Cause**: `UploadDailyReviewView` aggregated by (sku, distributor) only — two orders selecting the same distributor for the same SKU would merge into one PurchaseOrder, collapsing their independent decisions (warehouse stock vs vendor order).

#### Three Changes

| Change | Purpose | REQ | Status |
|--------|---------|-----|--------|
| **1. Cross-order SKU collision fix** | parse_daily_review_excel now requires order-name column | REQ-PO8-018 | ✅ Implemented |
| **2. PurchaseOrder initial status** | POs created by this view start confirmed, not pending | REQ-PO8-019 (NEW) | ✅ Implemented |
| **3. Distributor data sync** | Upsert BooxenData/KyoboData/Yes24Data for ALL rows regardless of selection | (Existing Part B behavior, now with cross-order safety) | ✅ Implemented |

#### Code Changes Summary

- **Parse Logic**: `parse_daily_review_excel()` now:
  - Requires "Name" (external template) or "주문번호" (legacy) column alongside SKU
  - Returns new `"name"` key in each row dict (Order.name as string)
  - Raises ValueError if column missing
- **Upload Logic**: `UploadDailyReviewView.post()` now:
  - Calls helper `_get_order_by_name(name)` to resolve order before confirming LineItem/creating PO
  - Creates PurchaseOrder with explicit `status="confirmed"` (not pending)
  - Maintains existing Part B vendor upsert loop (all rows synced regardless of selection)
- **Distributor Map**: Added `"YES24"` → `"yes24"` and `"재고"` → `"warehouse"` (new generic code for location-agnostic warehouse selection)

#### New Regression Tests Added

- `test_daily_review_upload.py`: 12 new scenarios covering:
  - Cross-order same-SKU isolation (selection decision independence)
  - Missing order-name column rejection
  - PurchaseOrder status="confirmed" assertion
  - Warehouse location Status-column parsing (한국재고/Fullerton재고/NJ재고 → korea/ca/nj)
  - YES24 distributor handling
  - Batching preservation (multi-order PO still allowed if (sku, distributor) identical across orders)

**Test Results**: 95 passed (test_daily_review_upload.py)

---

## Phase 2: Document Synchronization

### SPEC-ORDER-011/spec.md

**Changes**:
- ✅ Frontmatter: `version: 1.5.0 → 1.6.0`, `updated: 2026-08-08 → 2026-08-11`, `status: completed` (no change)
- ✅ HISTORY: Added v1.6.0 entry documenting bug fix + regression testing

### SPEC-PURCHASE-ORDER-008/spec.md

**Changes**:
- ✅ Frontmatter: `version: 1.0.0 → 1.1.0`, `updated: 2026-07-26 → 2026-08-11`, `status: completed` (no change)
- ✅ HISTORY: Added v1.1.0 entry documenting bug fixes + new requirement
- ✅ **NEW Requirement**: REQ-PO8-019 — UploadDailyReviewView creates PurchaseOrder with status="confirmed" (not pending)
- ✅ **NEW Acceptance Criterion**: AC-PO8-016 — PO status initialized as confirmed when created via this view

---

## File Changes Summary

### SPEC Documentation Updates

| File | Change | Lines | Status |
|------|--------|-------|--------|
| `.moai/specs/SPEC-ORDER-011/spec.md` | Frontmatter + HISTORY entry + version bump | +2 | ✅ Done |
| `.moai/specs/SPEC-PURCHASE-ORDER-008/spec.md` | Frontmatter + HISTORY + REQ-PO8-019 + AC-PO8-016 + version bump | +30 | ✅ Done |

### Sync Report

| File | Status |
|------|--------|
| `.moai/reports/sync-report-20260811-order-cross-order-sku.md` | ✅ This document |

### Project Documentation

| File | Decision | Reason |
|------|----------|--------|
| `.moai/project/product.md` | No update required | Purchase-order features documented as future TODO in prior sync report (2026-08-08) |
| `.moai/project/structure.md` | No update required | Adequate |
| `.moai/project/tech.md` | No update required | Adequate |

---

## Verification Checklist

### SPEC-ORDER-011

- ✅ Spec.md version: 1.5.0 → 1.6.0
- ✅ REQ-LOGI-003b now implemented: (Order.name, SKU) tuple matching + atomicity
- ✅ REQ-LOGI-005a now implemented: same tuple matching for warehouse receipts
- ✅ Parser renamed: `_parse_sku_only_xlsx` → `_parse_name_sku_xlsx` (reflects dual columns)
- ✅ Order-name column required, ValueError on missing
- ✅ Regression tests: 8 new scenarios in test_spec_011.py + test_spec_012.py
- ✅ Test results: 89 passed, 0 failed
- ✅ Implementation notes: Documented in spec history and commit message

### SPEC-PURCHASE-ORDER-008

- ✅ Spec.md version: 1.0.0 → 1.1.0
- ✅ REQ-PO8-018 now implemented: (Order.name, SKU) collision safety in Daily Review parser
- ✅ REQ-PO8-019 NEW: PurchaseOrder.status="confirmed" on creation (not pending)
- ✅ AC-PO8-016 NEW: Acceptance criterion for PO initial status
- ✅ Order-name column required in parse_daily_review_excel(), ValueError on missing
- ✅ PurchaseOrder creation explicit status="confirmed"
- ✅ Regression tests: 12 new scenarios in test_daily_review_upload.py
- ✅ Test results: 95 passed, 0 failed
- ✅ Implementation notes: Documented in spec history and commit message

### Cross-SPEC Validation

- ✅ No conflicting migrations
- ✅ Data model independence: logistics_status / purchase_status separate as before
- ✅ Query independence: Distinct upload paths and matching logic
- ✅ Frontend no changes (spec changes only)

---

## Known Limitations & Future Work

1. **Excel Column Headers**: Both fixes assume exact column name matching ("Name", "주문번호", "Lineitem sku", "ISBN", etc.). Case-sensitive substring matching is used in parse_daily_review_excel() for new template compatibility, but vendors must provide exact headers in their exports.

2. **Batch Processing Scope**: Part B of SPEC-PURCHASE-ORDER-008 (vendor table upsert) still batches multiple orders' rows into single PurchaseOrder when (sku, distributor) is identical AND NO ORDER-NAME COLLISION (collision-safe). This preserves intended batching behavior (e.g., two different orders, both selecting BOOXEN for same SKU, now correctly create separate POs).

3. **Production Data Integrity**: One pre-existing dangling reference (PurchaseOrder #7289 linked to both order #37893 and #37918) was corrected in DB directly today by support team. This is NOT reflected in code/migrations — purely operational correction to unblock testing.

---

## Divergence Summary

### Severity: MEDIUM (Production Bug with Real-World Impact)

**SPEC-ORDER-011**:
- Prior version 1.5.0 (2026-08-08) called the upload matching "SKU-only, no real templates yet" (placeholder implementation)
- Actual implementation (commit 9c2fc33, 2026-08-08) did use SKU-only parsing
- Production bug discovered during live support (order #37893 vs #37918) revealed this was **insufficient** — real-world templates DO have order information
- Patch (commit d22818f, 2026-08-11) fixes by requiring (Order.name, SKU) tuple matching

**SPEC-PURCHASE-ORDER-008**:
- Original spec (1.0.0) focused on Part A (new template parsing) and Part B (vendor upsert)
- Did not explicitly document PO status="confirmed" behavior (defaulted to pending)
- Production bug investigation revealed this inconsistency: Daily Review upload IS the distributor's confirmed response, so PO should start confirmed, not pending
- Patch adds REQ-PO8-019 to explicitly document this behavior

**Impact**: None on test coverage. All AC criteria satisfied. Real-world bug prevented by these fixes.

---

## Recommendations

1. ✅ **Merge both SPEC updates to version 1.6.0 (SPEC-ORDER-011) and 1.1.0 (SPEC-PURCHASE-ORDER-008)** — Bug fixes are production-verified
2. ✅ **Commit doc changes to same branch as code commit (d22818f)** — This is a follow-up documentation sync for an already-merged code fix
3. 📋 **Schedule post-incident review** — Root cause: templates with order-name column were available but not modeled in original SPEC assumptions. Add to team's "spec accuracy" checklist.
4. 📋 **Consider adding to project guidelines**: Excel template specs should explicitly list all columns, not assume "placeholder" or "minimal" parsers for production uploads.

---

## Metadata

| Item | Value |
|------|-------|
| Report Generated | 2026-08-11 22:10:15 UTC |
| SPECs Covered | 2 |
| Implementation Commits | 1 (d22818f, bundled three fixes) |
| Documentation Updates | 2 SPEC files |
| Code Changes | 5 backend files (excel_utils, purchase_order_views, 3 test files) |
| New Requirements | 1 (REQ-PO8-019) |
| New Tests | 20 (8 + 12 regression scenarios) |
| Test Pass Rate | 100% (184 total, 0 failed) |
| Root Cause | SKU-only matching allowed cross-order LineItem collapse |
| Fix Pattern | (Order.name, SKU) tuple matching + required name column |
| TRUST5 Validated | YES |
| Evaluator Review | Not run (bug fix, no pre-built evaluator run available) |

---

**End of Report**
