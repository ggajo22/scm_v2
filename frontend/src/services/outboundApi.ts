import { api } from '@/lib/axios'

// ---------------------------------------------------------------------------
// SPEC-ORDER-015: outbound processing API service (REQ-OUTBOUND-011/013/014/016)
// ---------------------------------------------------------------------------

// One outbound row as submitted by the user: Shopify order name + line item
// SKU + the quantity being shipped out.
export interface OutboundRowInput {
  name: string
  sku: string
  total: number
}

// REQ-OUTBOUND-005a: failure modes reported by `_process_outbound_rows`; each
// is rendered with its own Korean label on the page.
//
// `invalid_total` / `invalid_row` were added by the backend fix for the
// negative-total defect: a negative total decremented shipped_quantity, which
// re-implemented the "출고 취소/되돌리기(undo)" capability spec.md explicitly
// excludes. Rows are now validated per-row before summation.
//
// Keep this union in sync with the reason strings in
// backend/order/purchase_order_views.py — an unlisted code falls through to
// the raw snake_case fallback in OutboundPage.
export type OutboundUnmatchedReason =
  | 'order_not_found'
  | 'line_item_not_found'
  | 'multiple_line_items'
  // Non-positive total, rejected per-row before summation.
  | 'invalid_total'
  // Malformed row shape reaching the shared processing path. The manual
  // endpoint pre-validates and returns HTTP 400, so this normally arrives
  // only via the Excel path.
  | 'invalid_row'

export interface OutboundMatchedItem {
  name: string
  sku: string
  total: number
  line_item_id: number
  // Post-update cumulative shipped quantity (REQ-OUTBOUND-008).
  shipped_quantity: number
  // Nullable on the model — REQ-OUTBOUND-009 treats null as capacity 0.
  quantity: number | null
  logistics_status: string
}

export interface OutboundUnmatchedItem {
  name: string
  sku: string
  total: number
  reason: OutboundUnmatchedReason
}

export interface OutboundQuantityExceededItem {
  name: string
  sku: string
  total: number
  line_item_id: number
  // Pre-update values — nothing was written for this row (REQ-OUTBOUND-009).
  shipped_quantity: number
  quantity: number | null
  reason: 'quantity_exceeded'
}

// REQ-OUTBOUND-014: identical payload from both endpoints — three categories,
// each with its item list and count.
export interface OutboundProcessResponse {
  matched: OutboundMatchedItem[]
  matched_count: number
  unmatched: OutboundUnmatchedItem[]
  unmatched_count: number
  quantity_exceeded: OutboundQuantityExceededItem[]
  quantity_exceeded_count: number
}

// REQ-OUTBOUND-011: manual-entry outbound processing.
export async function processOutboundManual(
  rows: OutboundRowInput[]
): Promise<OutboundProcessResponse> {
  const res = await api.post('/api/purchase-orders/line-items/outbound-process/', { rows })
  return res.data
}

// REQ-OUTBOUND-012/013: Excel-driven outbound processing. An unresolvable
// header surfaces as HTTP 422 and is surfaced to the caller as a rejection.
export async function uploadOutbound(formData: FormData): Promise<OutboundProcessResponse> {
  const res = await api.post('/api/purchase-orders/upload-outbound/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
