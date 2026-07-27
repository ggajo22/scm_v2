## SPEC-PURCHASE-ORDER-009 Progress

- Started: 2026-07-26
- Trigger: user-reported real-world performance issue after SPEC-008 deploy (1447s for ~400 SKU upload), root-caused and measured directly against real dev DB (rolled back, no data affected)
- Development mode: tdd (quality.yaml constitution.development_mode)
- Harness level: standard (single domain, single file: purchase_order_views.py, but touches core write-path logic)
- Plan approved by user
- Cycle 1 implementation: vendor-table upsert batching, LineItem batch lookup, LineItemNote bulk_create, WarehouseStock batched Case/When all correctly done (evaluator-active verified with concrete row-level tracing)
- Cycle 1 real-file measurement (orchestrator, rolled back): 1447s -> 120s (12x), 795 queries — big improvement but not "seconds" target
- evaluator-active cycle 1: FAIL — REQ-PO9-007 (PurchaseOrder creation) deliberately left un-batched, still O(N) ~2 queries/SKU; real file is 439/447 rows in this exact branch (booxen 217 + kyobo 216 + yes24 6), so it's the dominant real-world path, not an edge case
- New regression test's fixture artificially fixes PO-branch count at 3 regardless of total_rows -> blind to this gap
- User decision: proceed with full PurchaseOrder batching to close the gap (fix cycle 2)
- Cycle 2 (PurchaseOrder batching, REQ-PO9-007): implemented via bulk_create + created_at-window re-query correlation + M2M through-table bulk_create (MySQL bulk_create does not return PKs, verified empirically)
- Cycle 2 real-file re-measurement (orchestrator, independently verified, rolled back): 120s/795 queries -> 3.3s/14 queries (matches implementer's claimed 3.50s/14 queries)
- evaluator-active cycle 2: PASS on all dimensions; found correlation logic correct via direct tracing + DB introspection; flagged 2 low-severity out-of-scope items (process_purchase_orders.py missing select_for_update - pre-existing, and missing permanent M2M regression test)
- Orchestrator closed the M2M test coverage gap directly: added TestUploadPurchaseOrderLineItemsM2MCorrectness (120 SKUs, varying LineItem counts, asserts exact po.line_items membership per SKU) - passes
- Final full suite: 76/76 pass (906s). ruff clean on test file, 16 pre-existing errors on view file (baseline unchanged, zero new)
- SPEC-009 complete: 1447s -> 3.3s (~440x improvement) for real ~400-SKU production file
