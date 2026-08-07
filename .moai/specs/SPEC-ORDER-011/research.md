# SPEC-ORDER-011 Research

Phase 0.5 Deep Research, produced by Explore subagent. DO NOT implement code from this document — planning input only.

Relocated from `.moai/specs/SPEC-LINEITEM-STATUS-001/research.md` (placeholder directory) during Phase 1.5/2 of planning — see spec.md HISTORY for the decision trail. This research also backs the reorder-queue query findings referenced by `SPEC-PURCHASE-ORDER-010`.

## Feature being planned

New LineItem-level status field tracking the Korea-vendor -> US-warehouse -> customer logistics pipeline, separate from:
- `LineItem.purchase_status`: why/whether a SKU still needs to be purchased from a vendor
- `LineItem.fulfillment_status` / `Order.fulfillment_status`: Shopify-synced "shipped to customer" status

New field: 5 states, ALL manually/upload-driven (no Shopify sync): 미입고(not yet shipped by vendor) -> 입고예정(vendor confirmed shipped, via Excel upload #1) -> 입고(received at US warehouse, via Excel upload #2) -> 출고예정 -> 출고 (both manual/upload too, NOT tied to Shopify fulfillment_status).

Also planned:
- New `purchase_status` value for damage/exchange (파손/교환) that re-enters the reorder queue.
- `Order.status` (currently unused, duplicates financial_status) redefined to hold a composite/aggregate value summarizing its LineItems' new status (e.g. "부분입고"). Exact aggregation/filtering behavior deliberately deferred — soft requirement only.

## 1. Existing bulk Excel upload endpoint patterns

**Daily Review flow** (`backend/order/purchase_order_views.py`):
- `DailyReviewExcelView.get` (line 816) generates the download.
- `UploadDailyReviewView.post` (line 998) is the reference upload endpoint:
  - Parses via `parse_daily_review_excel(file_bytes)` (`excel_utils.py:724`), returns `list[dict]`.
  - Dedup by SKU: `sku_map: dict[str, dict] = {row["sku"]: row for row in parsed_rows}` (lines 1040-1042) — last row wins.
  - Wrapped in one `transaction.atomic()` block (line 1064).
  - **Matching to LineItem rows is by SKU**: single `LineItem.objects.filter(sku__in=all_skus, purchase_status="unordered").exclude(purchase_orders__isnull=False).select_for_update()` (lines 1172-1178), grouped into `lineitems_by_sku: dict[str, list]` in Python — one query instead of N.
  - **Update pattern is `bulk_update`, not per-row `.save()`**: field updates accumulated into lists during the loop (`cs_status_updates`, `warehouse_li_updates`, `nonwarehouse_li_updates`, lines 1189-1191), flushed via `LineItem.objects.bulk_update(list, [fields])` once per distinct field-set (lines 1367-1376). Same for `LineItemNote.objects.bulk_create` (line 1363) and `PurchaseOrder.objects.bulk_create` (line 1414) followed by a re-query-by-timestamp trick to recover PKs for M2M linking (lines 1412-1435; MySQL doesn't return PKs from `bulk_create`).
  - Vendor-table upserts batched via `_batch_upsert_vendor_data()` (line 950) using `bulk_create(update_conflicts=True, update_fields=...)`, grouped by field-presence signature since MySQL requires uniform `update_fields` per call.
  - Warehouse stock deduction batched as a single `Case/When` `.update()` (lines 1339-1358).
  - Exceptions caught around the whole atomic block, returned as 500 with Korean message (lines 1437-1441).

**Vendor file upload flow** (`UploadVendorFileView`, line 246): older, simpler, non-batched — `parse_vendor_excel()` then per-row `Model.objects.update_or_create()` (lines 292-337) for `BooxenData`/`Yes24Data`/`KyoboData` only, no LineItem writes.

**Recommendation**: the two new upload endpoints (vendor-shipped Excel -> 입고예정, warehouse-received Excel -> 입고) should follow `UploadDailyReviewView`'s pattern (parse -> dedupe by SKU -> one `filter(sku__in=...).select_for_update()` -> accumulate `bulk_update` lists -> single `transaction.atomic()`), not the older `UploadVendorFileView` per-row style. This matches the direction SPEC-PURCHASE-ORDER-009 already optimized toward.

## 2. `_NOTE_TYPE_STATUS_MAP` pattern

Defined in `backend/order/excel_utils.py:614-619`:
```python
_NOTE_TYPE_STATUS_MAP: dict[str, str] = {
    "주문취소": "order_cancelled",
    "주문보류": "on_hold",
    "CS필요": "cs_required",
    "타출판사": "other_publisher",
}
```
Used in `purchase_order_views.py:1221`: when a Daily Review row's `선택` column isn't a recognized distributor but is a recognized CS-type label, `note_type` is captured during parsing (`excel_utils.py:848-849`), then at confirmation `new_status = _NOTE_TYPE_STATUS_MAP[note_type]` is applied to every unordered LineItem for that SKU (lines 1221-1224), and a `LineItemNote` created with the same `note_type` (lines 1226-1235). This is a **static dict lookup done inline in the upload view**, not a model-level signal/hook.

**Relevance to damage/exchange**: same pattern could apply — add `"파손/교환": "damaged_exchange"` to a similar map plus a new `NOTE_TYPE_CHOICES` entry on `LineItemNote` (`models.py:163-171`). Note this map is only consulted inside the Daily Review upload flow — if damage/exchange must also be triggerable from manual `LineItemNote` creation (`LineItemNoteListCreateView`), that trigger point isn't currently wired and needs new logic.

## 3. Migration conventions

- `0011_lineitem_add_purchase_status.py`: single `AddField` with inline `choices=[...]` and `default='unordered'`.
- `0012_lineitem_add_confirmed_fields.py`: three `AddField` ops in one migration, all `null=True, blank=True`.
- `0006_add_warehousestock.py`: `CreateModel` with `db_table`, `indexes`, `unique_together` in `options`.
- `0026_backfill_bundle_lineitems.py`: data-backfill convention — plain `RunPython(forward_func, migrations.RunPython.noop)` with thorough top-of-file comments explaining dependency ordering, why `reverse_code` is `noop` (irreversible, documented as accepted limitation), and the exact algorithm. Uses `apps.get_model(...)` historical model, not live import.

**Recommendation**: one `AddField` migration for the new LineItem status field (`default` = 미입고-equivalent, non-null, `choices=[...]`, mirroring 0011), one `AlterField` migration for `purchase_status` to add the damage/exchange choice (Django generates `AlterField` for a `choices` list change, not `AddField`). If backfill needed, follow 0026's `RunPython` + heavily-commented pattern with `noop` reverse.

## 4. WarehouseStock model and warehouse_views.py

`WarehouseStock` (`models.py:369-389`): `isbn` (CharField, not FK), `quantity` (IntegerField, default 0), `location` (choices: korea/ca/nj), `unique_together = [("isbn", "location")]`. **No status/state field — pure quantity ledger, not a receipt-event log.** No `received_at` timestamp, no reference to which PurchaseOrder/LineItem the stock came from.

`backend/order/warehouse_views.py`:
- `WarehouseStockListView.get` (line 15): pivots flat rows into one row per ISBN with korea/ca/nj columns.
- `WarehouseStockUpsertView.post` (line 49) / `WarehouseStockBulkView.post` (line 88): both `update_or_create(isbn=isbn, location=location, defaults={"quantity": quantity})` — **sets an absolute quantity, does not increment**. Also touched destructively by `UploadDailyReviewView`'s floor-at-0 deduction (lines 1339-1358) when warehouse-fulfilled sales are confirmed.

**No existing "입고예정"/"received into warehouse" event concept** on this model — confirmed via section 7 grep.

## 5. PurchaseOrder model and status field

`PurchaseOrder` (`models.py:233-270`): `STATUS_CHOICES = [("pending", "발주 대기"), ("confirmed", "발주 확정"), ("cancelled", "취소")]`, default `"pending"`. M2M to `LineItem` via `line_items`.

Current lifecycle: created with `status="pending"` in `ConfirmOrderView.post` (lines 744-751) and the Daily Review non-warehouse branch (lines 1305-1314). **Nothing in the codebase currently transitions `PurchaseOrder.status` to `"confirmed"` or `"cancelled"`** — no writes found beyond the choices declaration. It's a planned-but-unused state machine today. `LineItem.purchase_status` and `PurchaseOrder.status` are otherwise independent.

**Relevance**: the new field's "미입고"/"입고예정" states conceptually map to "PO exists but not vendor-confirmed" / "vendor confirmed shipment" — since `PurchaseOrder.status` already has an unused `confirmed` value, this SPEC could either (a) start actually driving `PurchaseOrder.status` transitions, or (b) keep the new field fully independent per the "manually/upload-driven" requirement. Given the SPEC explicitly says all 5 states are manual/upload-driven (not auto-derived from PO status), (b) is more consistent with stated intent, but flag as an explicit design decision since the unused "confirmed" value looks like it was meant for exactly this.

## 6. Frontend surfacing of purchase_status

- `frontend/src/services/purchaseOrderApi.ts:16-25`: `PURCHASE_STATUS_OPTIONS` — single source of truth mirroring `LineItem.PURCHASE_STATUS_CHOICES`, consumed by every tab (`@MX:ANCHOR` fan-in note lines 72-73).
- `UnorderedItemsTab.tsx`: per-row `<select>` bound to `item.purchase_status` (lines 254-268) via `useUpdateLineItemStatus` -> `PATCH /line-items/<id>/status/`; bulk toolbar (lines 118-141) via `useBulkUpdateLineItemStatus` -> `PATCH /line-items/bulk-status/`. Both hit `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView` (`purchase_order_views.py:1463`, `1504`).
- `ConfirmOrderTab.tsx`: another `<select>` for `purchase_status` per staged-item row (lines 161-175).
- `PurchaseOrderHistoryTab.tsx`: maps `PurchaseOrder.status` (not `LineItem.purchase_status`) via local `STATUS_MAP` (lines 6-11) — includes `shipped: '출고'` even though `PurchaseOrder.STATUS_CHOICES` has no `"shipped"` value (dead/forward-looking code, see section 7).

**Pattern for new status column/filter**: mirror `PURCHASE_STATUS_OPTIONS` with a new exported const array, add a `<select>` column following the existing per-row pattern, add matching single/bulk `PATCH` endpoints analogous to `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`.

## 7. No existing "입고예정"/"warehouse received" concept — confirmed, with adjacent-but-distinct terms found

Grepped `입고|출고|inbound|receiving|warehouse_received` across backend/ and frontend/src/:

- `excel_utils.py:26, 628, 822` — `"BOOXEN 입고예정"` is a Daily Review Excel column sourced from `BooxenData.arrival` (vendor's own restock-ETA free text) — unrelated to the new pipeline field, but the term "입고예정" is already user-visible in a different context, so new UI copy should disambiguate.
- `frontend/src/pages/OrderDetailPage.tsx:41-46`, `OrdersPage.tsx` — `FULFILLMENT_STATUS_LABELS` maps Shopify `fulfillment_status` (`fulfilled→출고완료`, `partial→부분출고`, `unfulfilled→미출고`, `restocked→재입고`) — this is the existing Shopify-synced concept the new field must stay distinct from; both will show "출고"-ish labels on the same Order/LineItem from different systems.
- `PurchaseOrderHistoryTab.tsx:9` — `STATUS_MAP` includes `shipped: '출고'` for `PurchaseOrder.status`, but `PurchaseOrder.STATUS_CHOICES` has no `"shipped"` value — dead/forward-looking frontend code, shows prior unrealized intent for a PO-level shipped state.
- `backend/book/models.py:121` — `BookNote.NOTE_TYPE_CHOICES` has `("SHIPPING", "출고 노트")`, but in the unrelated `book` app — no overlap.
- `WarehouseStock` — zero status/state fields, confirmed no existing "received" event tracking.

**Conclusion**: no existing model/endpoint implements the 미입고/입고예정/입고/출고예정/출고 pipeline. Adjacent concepts (`BooxenData.arrival`, `Order/LineItem.fulfillment_status`, `PurchaseOrder.status`) are vendor-external, Shopify-synced, or unused — safe to introduce without renaming/migrating existing data, but UI copy must avoid colliding with the two "입고예정"/"출고" terms already visible elsewhere.

## Recommendations for implementation approach

1. **Migrations**: `AddField` for the new LineItem status field (default = 미입고-equivalent, non-null, `choices=[...]`, mirroring `0011_lineitem_add_purchase_status.py`); `AlterField` for `purchase_status` adding the damage/exchange choice. Backfill (if needed) via `0026`'s `RunPython(forward, noop)` pattern with thorough comments.
2. **Upload endpoints**: model both new endpoints on `UploadDailyReviewView` (`purchase_order_views.py:998-1451`) — parse -> dedupe-by-SKU -> single `transaction.atomic()` -> one `filter(sku__in=..., <status filter>).select_for_update()` grouped in Python -> accumulate per-field-set lists -> flush with `bulk_update`/`bulk_create` once per group. Add `parse_*_excel()` functions to `excel_utils.py` alongside `parse_daily_review_excel` (line 724).
3. **Damage/exchange auto-transition**: extend `_NOTE_TYPE_STATUS_MAP` (`excel_utils.py:614-619`) if triggered via Daily Review upload's `선택` column, and/or add a new `LineItemNote.NOTE_TYPE_CHOICES` entry if triggered via manual note creation — the map is currently only consulted inside `UploadDailyReviewView`, so a manual-note trigger path needs new wiring.
4. **Shopify sync exclusion**: `shopify_orders.py:203` explicitly excludes `purchase_status` from `common_defaults` in `LineItem.objects.update_or_create(...)` to preserve manual state across re-syncs — the new field must follow the identical exclusion pattern since it's also manual/upload-driven.
5. **WarehouseStock overlap**: none currently — pure absolute-quantity ledger, `update_or_create` (set-absolute, not increment). Decide during design whether "입고" (received) should also increment `WarehouseStock.quantity` — today nothing links a LineItem-level event to a WarehouseStock write except the Daily Review upload's floor-at-0 deduction (opposite direction: consuming stock, not adding it).
6. **Frontend**: new exported const options array in `purchaseOrderApi.ts` (mirroring `PURCHASE_STATUS_OPTIONS`); single/bulk PATCH wrappers mirroring `updateLineItemStatus`/`bulkUpdateLineItemStatus`; `<select>` column in `UnorderedItemsTab.tsx`/`ConfirmOrderTab.tsx`; UI copy for "입고예정"/"출고" must be visually distinct from `FULFILLMENT_STATUS_LABELS` and `BooxenData.arrival`-sourced Excel column terms.
7. **`Order.status` aggregate (soft requirement, deferred)**: currently duplicates `financial_status`, set at `shopify_orders.py:138`. Redefining as an aggregate of LineItem states is flagged as a follow-up design decision — the sync code must stop overwriting `status` from Shopify once repurposed (same exclusion pattern as item 4).

## Additional verification performed during planning (Phase 1B/Decision Point rounds)

Beyond the initial Explore pass above, the following was verified directly against source during the planning conversation (all line numbers current as of 2026-08-07):

- `Order.status` write site confirmed at `backend/order/shopify_orders.py:138` (`"status": order_data.get("financial_status")` inside `_sync_single_order()`'s `Order.objects.update_or_create()` defaults dict).
- No frontend consumer of `Order.status` exists today (`frontend/src/types/order.ts` only types `financial_status`/`fulfillment_status`; `OrdersPage.tsx`/`OrderDetailPage.tsx` never read `.status`) — redefinition carries no frontend regression risk.
- Latest migration at planning time: `0028_kyobodata_list_price.py` — next available number is `0029`.
- Four (later corrected to five, see SPEC-PURCHASE-ORDER-010) reorder-candidate query sites identified with exact line numbers via direct `Read`, not just grep: `UnorderedItemsView` (:95), `RunComparisonView` (:375), `DailyReviewExcelView` (:839), `UploadDailyReviewView` (:1175) — all four share `filter(purchase_status="unordered").exclude(purchase_orders__isnull=False)`. `ConfirmOrderView.post()` (:713-717) has a *different* pattern — `filter(sku=sku).exclude(purchase_orders__isnull=False)` with no `purchase_status` filter at all — discovered only on a second, more careful read; this distinction matters for SPEC-PURCHASE-ORDER-010's query-fix scope.
