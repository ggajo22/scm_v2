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

// ---------------------------------------------------------------------------
// SPEC-ORDER-016: force outbound processing (REQ-FORCE-001~025)
// ---------------------------------------------------------------------------

// REQ-FORCE-006: one force-eligible candidate LineItem for a given order, as
// returned by the batch candidate lookup. `no_remaining_capacity` is true
// when `quantity` is null (capacity 0, 설계 결정 B) or `shipped_quantity`
// has already reached `quantity`.
export interface OutboundForceCandidate {
  line_item_id: number
  title: string | null
  sku: string
  quantity: number | null
  shipped_quantity: number
  logistics_status: string
  no_remaining_capacity: boolean
}

// REQ-FORCE-006: one order's candidate list within a batch response.
export interface OutboundForceCandidateGroup {
  order_name: string
  candidates: OutboundForceCandidate[]
}

// One force-outbound row as submitted by the operator: the original
// order/sku (carried through for gate validation and response reporting
// only, per backend contract) plus the operator-designated target
// LineItem id, which replaces `(order, sku)` matching (REQ-FORCE-002/007).
export interface OutboundForceRowInput {
  name: string
  sku: string
  total: number
  line_item_id: number
}

// REQ-FORCE-003: batch candidate lookup for every order identifier the
// caller passes, in a single round trip. An empty list still round-trips
// (the server returns an empty `results` array rather than an error).
export async function fetchOutboundForceCandidates(
  orderNames: string[]
): Promise<OutboundForceCandidateGroup[]> {
  const res = await api.post('/api/purchase-orders/line-items/outbound-force-candidates/', {
    order_names: orderNames,
  })
  return res.data.results
}

// REQ-FORCE-015/016: force-execute a batch of operator-designated rows.
// Reuses `OutboundProcessResponse` verbatim — the server returns the same
// matched/unmatched/quantity_exceeded/*_count contract the two existing
// outbound endpoints return, so no new response type is introduced here.
// A gate violation (REQ-FORCE-002) surfaces as an HTTP 400 rejection, same
// as every other outbound submit path.
export async function processOutboundForce(
  rows: OutboundForceRowInput[]
): Promise<OutboundProcessResponse> {
  const res = await api.post('/api/purchase-orders/line-items/outbound-force-process/', { rows })
  return res.data
}
