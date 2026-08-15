import { api } from '@/lib/axios'

// ---------------------------------------------------------------------------
// SPEC-PURCHASE-ORDER-011: damaged-exchange search + submission API service
// ---------------------------------------------------------------------------

// REQ-DEX-006/006a/006b: order_ready_to_ship is the parent Order's stored
// value, read exactly as-is (never recomputed here) — 3-state
// (true/false/null). AC-DEX-005a: null must render as null, never coerced
// to false.
export interface DamagedExchangeSearchResultRow {
  id: number
  order_name: string | null
  sku: string
  title: string
  // SPEC-ORDER-013 REQ-RACK-001: physical shelf code, read-only here.
  // Empty string means unassigned — rendered as '미지정', matching the
  // SPEC-ORDER-014 summary convention. Editing stays exclusive to
  // /rack-number Tab1; this page never writes it.
  rack_number: string
  quantity: number | null
  purchase_status: string
  is_damaged_exchange: boolean
  order_ready_to_ship: boolean | null
  order_total_quantity: number
}

export interface DamagedExchangeSearchResponse {
  count: number
  results: DamagedExchangeSearchResultRow[]
}

// REQ-DEX-004/005/005a/007: exact-match `sku` search within the unshipped,
// non-cancelled scope (backend-side) — an empty/missing `sku` returns
// { count: 0, results: [] } rather than an error, so this is always safe to
// call once the operator has typed something.
export async function searchDamagedExchangeCandidates(
  sku: string
): Promise<DamagedExchangeSearchResponse> {
  const res = await api.get('/api/purchase-orders/line-items/damaged-exchange-search/', {
    params: { sku },
  })
  return res.data
}

export interface DamagedExchangeSubmitResponse {
  id: number
  purchase_status: string
  damaged_quantity: number
}

// REQ-DEX-008/009/009a/009b: row-level damage submission. The server is the
// authoritative validator of the 1..quantity inclusive range (AC-DEX-008) —
// the page only pre-fills the default and disables submission client-side as
// an early UX guard, never as the sole line of defense.
export async function submitDamagedExchange(
  id: number,
  damagedQuantity: number
): Promise<DamagedExchangeSubmitResponse> {
  const res = await api.post(`/api/purchase-orders/line-items/${id}/damaged-exchange/`, {
    damaged_quantity: damagedQuantity,
  })
  return res.data
}
