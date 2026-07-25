# Research: SPEC-SHOPIFY-SKU-SET-002 (Ingestion-time bundle expansion)

Date: 2026-07-25
Author: manager-spec (research pass, code read directly — not derived from brief summary)

Purpose: Verify every file/line reference and behavioral claim before writing spec.md,
per this SPEC's complexity (schema change, ingestion rewrite, refund semantics, data backfill).

---

## 1. Current state — SPEC-SHOPIFY-SKU-SET-001 (status: Implemented)

`.moai/specs/SPEC-SHOPIFY-SKU-SET-001/spec.md` confirmed read in full. Core decision
being superseded: **REQ-SKU-SET-003** — bundle expansion happens at DISPLAY TIME inside
`UnorderedItemsView.get()`. Confirmed exclusions in SPEC-001 that this new SPEC directly
touches:
- "Shopify 싱크 변경 없음: LineItem.sku는 Shopify 원본 값 그대로 저장" — **this SPEC reverses that decision.**
- "역방향 조회 없음: ISBN → bundle_sku 역방향 검색 기능은 제공하지 않는다" — a reverse lookup was
  added anyway as a bug patch (see §2); this SPEC removes it, restoring compliance with the
  original exclusion.
- "기존 PurchaseOrder 소급 전개 없음" — preserved verbatim by this SPEC's backfill scope.

## 2. The bug patch being reverted (commit `6d2dfc4`)

Verified via `git show 6d2dfc4`. Commit subject: "fix(order): SKU 세트 매핑 전개 항목 선택 시
'알 수 없는 SKU' 오류 수정". Changed only `backend/order/purchase_order_views.py` (+34/-6) and
added 3 tests to `backend/order/tests/test_purchase_orders.py` (+99). No model/migration
change in that commit — it is a pure view-layer patch, confirming the root cause was never
fixed at the source (ingestion).

The 3 added tests (in `TestGenerateOrderFileView`, currently at lines 499–591 of
`backend/order/tests/test_purchase_orders.py`) are:
- `test_bundle_member_sku_resolves_to_full_bundle_quantity`
- `test_two_bundle_members_each_get_own_row_with_full_quantity`
- `test_bundle_member_mixed_with_ordinary_sku`

Note: these tests carry a header comment "# SPEC-PURCHASE-ORDER-007: Bundle SKU
(ShopifySkuSetMapping) support" (line 496) — this is a mislabel in the original commit;
the actual current `SPEC-PURCHASE-ORDER-007` (`.moai/specs/SPEC-PURCHASE-ORDER-007/spec.md`,
status: planned) is an unrelated YES24 order-file-generation feature. This mislabel is noted
here only so the mismatch isn't mistaken for a real cross-SPEC dependency by a future reader.

## 3. `UnorderedItemsView.get()` — verified exact location

File: `backend/order/purchase_order_views.py`, class body lines 71–152.

- Base query + per-row dict build: lines 82–129 (unaffected by this SPEC; net-quantity/refund
  logic here already operates identically regardless of whether `sku` is a bundle SKU or a real
  ISBN — no change needed to this block).
- Bundle expansion block to be **removed**: lines 131–152.
  - Lines 133–136: build `bundle_map: dict[str, list[str]]` from `ShopifySkuSetMapping`
    (single extra query, matches SPEC-001's non-functional requirement of "최대 1회 추가 쿼리 허용").
  - Lines 138–150: `expanded` loop — for each result row, if `sku` is a bundle_sku, replace
    with N rows (`is_bundle_member=True`, `bundle_sku=<original>`); else pass through with
    `is_bundle_member=False, bundle_sku=None`.
  - Line 152: `return Response({"count": len(expanded), "results": expanded})`.
- Post-removal shape: `results` (built at line 111–129) becomes the direct return payload —
  `return Response({"count": len(results), "results": results})` — no `is_bundle_member`/
  `bundle_sku` keys at all (see §6 for why full removal, not always-`false`/`null`, is correct).

## 4. `GenerateOrderFileView.post()` — verified exact location and revert target

File: `backend/order/purchase_order_views.py`, class body lines 160–274.

Reverse-mapping block to be **removed** (added by commit `6d2dfc4`): lines 196–248.
- Lines 200–202: `member_to_bundle: dict[str, str]` built from
  `ShopifySkuSetMapping.objects.values_list("member_isbn", "bundle_sku")`.
- Line 205: `requested_underlying = {member_to_bundle.get(sku, sku) for sku in skus}`.
- Lines 215–234: `li_qs` filtered by `sku__in=requested_underlying`, aggregated into
  `underlying_found_map` (keyed by underlying/bundle sku).
  Note: this is functionally identical to the pattern in `UnorderedItemsView`'s refund
  subquery — reused verbatim, not affected by removal.
- Lines 236–248: maps `underlying_found_map` back to the originally-requested (member ISBN)
  keys into `found_map`.

**Verified pre-patch code** (from `git show 6d2dfc4` diff context, this is the exact revert
target):
```python
requested = set(skus)
refund_sum_sq = (...)  # unchanged
li_qs = (
    LineItem.objects.filter(sku__in=requested)
    .exclude(purchase_orders__isnull=False)
    .annotate(refunded_qty=Coalesce(Subquery(refund_sum_sq, output_field=IntegerField()), 0))
    .values("sku", "title", "quantity", "refunded_qty")
)
found_map: dict[str, dict] = {}
for row in li_qs:
    net = max((row["quantity"] or 0) - row["refunded_qty"], 0)
    if net == 0:
        continue
    sku = row["sku"]
    if sku not in found_map:
        found_map[sku] = {"sku": sku, "title": row["title"] or "", "total_quantity": 0}
    found_map[sku]["total_quantity"] += net
unknown_skus = [s for s in skus if s not in found_map]
```
This is what the view reverts to. With ingestion-time expansion, `LineItem.sku` for a bundle
member is already the real ISBN, so `sku__in=requested` (the raw requested SKUs, no
translation) matches directly.

## 5. `LineItem` model — schema constraint (verified)

File: `backend/order/models.py`, class body lines 109–147.
- Line 128: `sku = models.CharField(max_length=255, null=True, blank=True)` — **nullable**.
- Line 147: `unique_together = [("order", "shopify_line_item_id")]` — the constraint to change.

Proposed new constraint: `[("order", "shopify_line_item_id", "sku")]`.

**NULL-in-unique-together verified behavior**: Both MySQL 8.0 (production, confirmed in
`.claude/agent-memory/manager-spec/project-scm-v2.md` and `backend/config/settings/base.py`
default engine chain) and SQLite (`backend/pytest.ini` → `DJANGO_SETTINGS_MODULE =
config.settings.local` → `backend/config/settings/local.py` lines 9–18, `ENGINE` defaults to
`django.db.backends.sqlite3`) follow standard SQL semantics: **NULL is never equal to NULL**
in a unique index, so multiple rows with `sku=NULL` for the same `(order,
shopify_line_item_id)` would NOT be rejected by the DB-level constraint. This is a **pre-existing
class of non-enforcement**, not a new risk introduced by this change — today's 2-column
constraint already can't be violated by a null-sku duplicate in the same way. In practice this
is a non-issue because `_sync_single_order`'s `update_or_create` does a SELECT (translated by
Django to `sku IS NULL` when `sku=None`) before deciding INSERT vs UPDATE, so within a single
sequential sync run no duplicate is ever created — the risk only exists under true concurrent
writes to the exact same `(order, shopify_line_item_id, NULL)` tuple, which is already
out-of-scope for this codebase (no concurrent Shopify sync workers found in `shopify_orders.py`
or Celery task definitions searched). No sentinel value needed; documented as an accepted,
pre-existing characteristic, not a new gap. Confirmed no `null=True` needs to change.

## 6. Frontend — verified NO reference to `is_bundle_member`/`bundle_sku`

- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` (279 lines, read in full):
  no occurrence of `is_bundle_member` or `bundle_sku` anywhere in the file. Every row is
  rendered from `item.sku`, `item.title`, `item.vendor`, `item.quantity`,
  `item.auto_distributor`, `item.purchase_status`, `item.id`, `item.order_name` only.
- `frontend/src/services/purchaseOrderApi.ts` `UnorderedItem` interface (lines 5–14): does
  **not** declare `is_bundle_member` or `bundle_sku` fields — TypeScript never typed these
  fields even though the backend has been sending them since SPEC-001. They are dead weight
  today.
- Conclusion: full removal of `is_bundle_member`/`bundle_sku` from the API response (not
  "keep as always-false/null") is safe — zero frontend code, including tests, references
  them. `UnorderedItemsTab.test.tsx` also checked (grep) — no reference.
- `frontend/src/features/sku-sets/*` (`SkuSetsPage.tsx`, `api.ts`) reference `bundle_sku` only
  in the context of the SKU-set mapping CRUD page (`/settings/sku-sets`), which is explicitly
  out of scope and untouched by this SPEC.

## 7. Ingestion pipeline — `backend/order/shopify_orders.py` (verified line numbers)

- `_sync_single_order(order_data, store_type, location_code="", line_item_location_map=None)`:
  function body lines 82–218.
- LineItem loop to become bundle-aware: lines 159–180.
  ```python
  incoming_shopify_ids = set()
  for li in order_data.get("line_items", []):
      incoming_shopify_ids.add(li["id"])
      LineItem.objects.update_or_create(
          order=order_obj,
          shopify_line_item_id=li["id"],
          defaults={... "sku": li.get("sku"), "quantity": li.get("quantity"), ...},
      )
  ```
- Stale-line-item deletion: lines 181–184.
  ```python
  order_obj.line_items.filter(purchase_orders__isnull=True).exclude(
      shopify_line_item_id__in=incoming_shopify_ids
  ).delete()
  ```
  **Verified**: this filters by `shopify_line_item_id__in=incoming_shopify_ids` only (no `sku`
  in the filter/exclude at all). Since all N expanded rows for one bundle line item share the
  same `shopify_line_item_id`, this logic is unaffected by expansion — either all N rows are
  kept (id present in `incoming_shopify_ids`) or all N are candidates for deletion (id absent
  and not purchase-ordered) as a set. Confirmed no change needed here.

- `sync_store(store_type)`: function body lines 242–307.
  - `existing_line_item_locs` prefetch: lines 274–282, keyed by
    `(shopify_order_id, shopify_line_item_id) -> {shopify_line_item_id: location}`. Verified
    this is a `.values("order__shopify_order_id", "shopify_line_item_id", "location")` query —
    with N rows sharing one `shopify_line_item_id`, the dict comprehension
    (`.setdefault(...)[...] = row["location"]`) will simply overwrite the same key N times with
    the same location value (all split rows share the same `line_item_location_map.get(li["id"], "")`
    source at line 178 during the write side), so the read-side dict ends up with one entry per
    `shopify_line_item_id` regardless of N — **no change needed**, confirmed read-only
    optimization is unaffected by row-count multiplication.

- `Refund` model (`backend/order/models.py` lines 215–228): `line_item_id` is a plain
  `BigIntegerField` (not a FK) storing the raw Shopify `shopify_line_item_id`. A full grep of
  `purchase_order_views.py` for this subquery pattern found **6** call sites, not 4 as an
  earlier draft of this document undercounted — corrected here: `UnorderedItemsView` line
  84–92, `GenerateOrderFileView` line 206–214, `RunComparisonView` line 400–408,
  `DailyReviewExcelView` line 864–872, `_attach_net_quantity` line 1369–1381 (used by
  `PurchaseOrderListView` to compute `net_quantity` for display), and `PurchaseOrderListView.get()`
  line 1422–1430 (its own separate `unrefunded_li` subquery, used to exclude fully-refunded POs
  from the list — structurally distinct purpose from `_attach_net_quantity` but the identical
  `OuterRef` pattern). All 6 filter
  `Refund.objects.filter(order_id=OuterRef("order_id"), line_item_id=OuterRef("shopify_line_item_id"))`
  — i.e., keyed by `shopify_line_item_id`, NOT by `sku` or PK. **Verified**: with N LineItem rows
  sharing one `shopify_line_item_id`, this `OuterRef` subquery independently re-evaluates for
  each of the N outer rows and returns the SAME total refunded quantity every time (the
  subquery has no dependency on which specific split-row triggered it, nor on whether it's used
  for sku-grouped totals like `UnorderedItemsView`/`RunComparisonView`, per-LineItem net quantity
  like `_attach_net_quantity`, or a boolean fully-refunded filter like
  `PurchaseOrderListView.get()`'s own subquery — the safety argument is per-row-independent and
  therefore purpose-agnostic). Each row then does its own quantity/refunded_qty comparison
  independently using its own (full, undivided) `quantity` — so the full refunded quantity is
  subtracted from/compared against each split row's full quantity, automatically implementing
  the user's decision #1 (apply full refund to each member) with **zero code changes** to
  refund-subtraction logic anywhere in the file. Confirmed by reading all 6 call sites directly;
  the 4 quantity-arithmetic ones are structurally identical copy-pasted blocks, and the 2 newly
  identified ones (`RunComparisonView`, `PurchaseOrderListView`'s own filter) use the same
  `OuterRef` keying and are independently confirmed safe by the same per-row reasoning.
  - **Edge case found and not previously flagged in the brief**: this reasoning holds as long as
    each split row has the correct (full, non-divided) `quantity` value written by the
    ingestion loop — which REQ in this SPEC must guarantee explicitly (copy Shopify's line-item
    `quantity` verbatim into every member row, not divided). If a future implementer
    mistakenly divided quantity across members, the refund math would silently under- or
    over-subtract per row. This SPEC's requirements make this explicit rather than leaving it
    as an implicit emergent property.

## 8. Re-sync / mapping-change edge case (verified, no existing handling)

`OrderResyncView` (`backend/order/views.py` lines 188–219) calls
`sync_single_order_from_shopify` → `_sync_single_order` with the same code path as
`sync_store`. No special-casing exists anywhere for bundle SKUs today (confirmed via grep:
zero occurrences of `ShopifySkuSetMapping` in `views.py` or `shopify_orders.py`). Verified
`backend/order/tests/test_order_resync.py` (233 lines, read in full) has zero bundle-related
tests currently — 6 tests cover generic resync success/404/401/502/network-error, plus 3
"SPEC-ORDER-005" refund case tests (A/B/C: new refund created, stale refund cleared, no
duplication). None touch `ShopifySkuSetMapping`.

Confirmed edge case per the brief: if `ShopifySkuSetMapping` members change after an order
was already synced-and-expanded, and that order is later re-synced (webhook or
`OrderResyncView`), the ingestion loop re-runs expansion using the *current* (changed) mapping.
Since `update_or_create` is keyed by `(order, shopify_line_item_id, sku)`:
- Members still in the new mapping: matched and updated in place.
- Newly-added members: created as new rows.
- Removed members: **orphaned** — the stale-deletion logic (§7) only excludes by
  `shopify_line_item_id__in=incoming_shopify_ids`, and the incoming ids set still contains this
  line item's id (Shopify still reports it), so the orphaned old-member row is never deleted
  by that logic. It remains in the DB as an `unordered` LineItem with a real ISBN that is no
  longer part of the bundle mapping. This is a genuine, previously-unhandled edge case —
  confirmed no existing safety net catches it. Documented as an accepted Exclusion (consistent
  with SPEC-001's "no retroactive re-expansion" philosophy) rather than solved in this SPEC.

## 9. Tests requiring changes (verified via direct read, not guessed)

- `backend/order/tests/test_shopify_sku_set.py` (330 lines, read in full):
  - `TestUnorderedItemsBundleExpansion` (lines 289–330, 3 tests: `test_bundle_sku_expanded`,
    `test_non_bundle_sku_not_expanded`, `test_bundle_count_reflects_expansion`) directly
    assert on `is_bundle_member`/`bundle_sku` response fields and display-time expansion
    behavior — **entirely obsolete**, must be removed or rewritten once display-time expansion
    is removed. `order_with_bundle_lineitem` fixture (lines 55–72) creates a LineItem with
    `sku="GITANMATH-F SET"` directly — this fixture pattern itself models the OLD
    (pre-ingestion-expansion) DB state and needs reconsideration.
  - `bundle_mapping` fixture (lines 47–52) and `TestShopifySkuSetMappingModel`,
    `TestShopifySkuSetListCreateView`, `TestShopifySkuSetDetailView` classes (CRUD tests,
    lines ~76–283) are unaffected — they test the mapping CRUD API itself, not expansion
    timing.
- `backend/order/tests/test_purchase_orders.py` (1859 lines total):
  - `TestGenerateOrderFileView` bundle tests (lines 499–591, the 3 tests from commit
    `6d2dfc4`, see §2) must be rewritten to set up LineItems that are *already* per-ISBN
    (simulating post-ingestion-expansion state) instead of a single bundle-SKU LineItem, and
    assert the plain reverted query path handles them — per the user's explicit instruction.
  - `TestUnorderedItemsView` (lines 258–372, read in full) has **no** existing bundle-related
    assertions — confirmed clean, no change needed here directly (bundle expansion tests live
    exclusively in `test_shopify_sku_set.py`, not in this class).
- `backend/order/tests/test_shopify_orders.py` (224 lines, read in full): zero bundle-related
  tests currently exist. `_make_shopify_line_item()` helper (lines 48–62) and
  `_sync_single_order` test patterns (lines 65–155) are the templates to extend with new
  bundle-expansion-at-sync-time cases (mapping present vs absent, quantity-copied-verbatim,
  stale-removal-as-a-set).
- `backend/order/tests/test_order_resync.py` (233 lines, read in full): zero bundle-related
  tests; confirmed no existing coverage of the re-sync/mapping-change edge case (§8) — a new
  test documenting the *accepted* orphaning behavior is recommended but the edge case itself is
  NOT to be solved.

## 10. Migrations directory (verified)

`backend/order/migrations/` currently ends at `0024_yes24data.py`. Next migration number for
the schema-constraint change is `0025_...`. `0022_shopifyskusetmapping.py` (read in full) is
the template for `AlterUniqueTogether`-style migration authoring conventions used in this
project (plain `migrations.Migration` with explicit `dependencies`/`operations`, no
`RunPython` yet in this app's migration history — the backfill migration introduced by this
SPEC will be the first `RunPython` data migration in the `order` app; confirmed by scanning
all 24 existing migration filenames, none use a `data_migration` naming pattern or contain
`RunPython` — grep for "RunPython" across `backend/order/migrations/*.py` returned no matches
in the reviewed set).

## 11. Daily Review — confirmed beneficial side effect, not a new requirement

`DailyReviewExcelView.get()` (`backend/order/purchase_order_views.py` lines 852–978) and
`UploadDailyReviewView.post()` (lines 981–1152) both operate on `LineItem.sku` directly for
`BooxenData`/`KyoboData`/`WarehouseStock` joins (e.g. lines 892–893, 897–900). Today, for a
bundle LineItem, `li.sku` is the raw bundle SKU string (e.g. `"GITANMATH-F SET"`), which never
matches any real-ISBN-keyed vendor/warehouse row — so bundle rows in the Daily Review Excel
today silently show null price/stock/warehouse columns. After ingestion-time expansion,
`LineItem.sku` for these rows becomes the real ISBN, so these joins will start returning
correct vendor/warehouse data for what were previously bundle rows. Verified this requires
zero code change to either view — confirmed by reading both views in full. This is documented
in spec.md as a beneficial side effect, not a new build requirement (per the user's brief).

## 12. Additional risks/edge cases discovered during research (not in original brief)

1. **Refund-quantity correctness depends on ingestion writing full (undivided) quantity to
   every split row** — see §7 final paragraph. Must be an explicit REQ, not an implicit
   assumption, since the "zero code change" reasoning for refund semantics is contingent on
   this.
2. **Backfill migration must preserve `LineItemNote` FK integrity for at least one member row**
   — `LineItemNote.line_item` is `on_delete=CASCADE` (`backend/order/models.py` line 172).
   Deleting the original bundle LineItem row outright (rather than repurposing it into one of
   the N member rows) would cascade-delete any existing CS/발주/창고 notes attached to it. The
   brief left the exact backfill mechanism as "SPEC author's call" — this SPEC's design
   (§ REQ backfill) repurposes the original row into the first `sort_order` member (preserving
   PK, notes, and any other FK relations) and only creates new rows for the remaining N-1
   members. This is called out explicitly as a design decision with a documented limitation
   (notes are not duplicated to the other N-1 new rows).
3. **NULL-in-unique-together is a pre-existing non-issue, not a new risk** — see §5. No
   sentinel needed.
4. **`sort_order` should drive both ingestion-time expansion order and backfill order** — for
   consistency with the removed display-time expansion's iteration order
   (`ShopifySkuSetMapping.objects.order_by("bundle_sku", "sort_order")` at old line 135),
   ensuring member row creation order (and thus which member becomes "first"/repurposed in
   backfill) is deterministic.
5. **No Celery/async concurrent sync workers found** — confirmed via search, no competing
   process could race `update_or_create` on the same LineItem row during a single sync;
   simplifies the NULL-uniqueness discussion in §5 to a documented non-issue rather than a risk
   requiring mitigation.

---

## Summary of files requiring changes (verified against actual code, not the brief alone)

| File | Verified lines | Change |
|---|---|---|
| `backend/order/models.py` | 147 | `unique_together` → `[("order", "shopify_line_item_id", "sku")]` |
| `backend/order/migrations/0025_*.py` (new) | — | `AlterUniqueTogether` schema migration |
| `backend/order/migrations/0026_*.py` (new) | — | `RunPython` data migration (backfill) |
| `backend/order/shopify_orders.py` | 159–180 | Bundle-aware `update_or_create` loop in `_sync_single_order` |
| `backend/order/purchase_order_views.py` | 131–152 | Remove display-time expansion in `UnorderedItemsView.get()` |
| `backend/order/purchase_order_views.py` | 196–248 | Revert reverse-mapping in `GenerateOrderFileView.post()` |
| `backend/order/tests/test_shopify_sku_set.py` | 55–72, 289–330 | Remove/rewrite `TestUnorderedItemsBundleExpansion` + fixture |
| `backend/order/tests/test_purchase_orders.py` | 499–591 | Rewrite 3 bundle tests to pre-expanded-state setup |
| `backend/order/tests/test_shopify_orders.py` | new | Add ingestion-time bundle expansion tests |
| `backend/order/tests/test_order_resync.py` | new (optional) | Document re-sync/mapping-change edge case |

No changes required (verified, not assumed):
- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`
- `frontend/src/services/purchaseOrderApi.ts`
- `backend/order/shopify_sku_set_views.py`
- `frontend/src/features/sku-sets/*`
- `backend/order/purchase_order_views.py` `DailyReviewExcelView`/`UploadDailyReviewView` (beneficial side effect only)
- `sync_store()`'s `existing_line_item_locs` optimization
