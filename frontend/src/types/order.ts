export interface OrderCustomer {
  shopify_customer_id: number
  first_name: string | null
  last_name: string | null
  email: string | null
}

export interface Order {
  id: number
  shopify_order_id: number
  store_type: 'gimssine' | 'etoile'
  order_number: number | null
  name: string | null
  financial_status: string | null
  fulfillment_status: string | null
  total_price: string | null
  currency: string | null
  shopify_created_at: string | null
  customer: OrderCustomer | null
  has_refund: boolean
  line_items_count: number
  location?: string
  // SPEC-ORDER-023 REQ-OLIST-016~018: list-endpoint margin rate, derived
  // server-side from the same cost breakdown as OrderDetail.margin_rate.
  // Null when exchange rate is unavailable, no confirmed purchase cost
  // exists, or total_price is zero (REQ-OLIST-017).
  margin_rate: string | null
  // SPEC-ORDER-023 REQ-OLIST-007~011a: one of 'shipped' | 'partial_shipped'
  // | 'outbound_scheduled' | 'not_shipped' | 'shipment_confirmed' |
  // 'partial', or null when the order has no trackable line items. Note:
  // 'received' is never emitted as a display value.
  logistics_display: string | null
  // SPEC-ORDER-023 REQ-OLIST-013~015: 'unordered' | 'ordered', or null when
  // the order has no trackable line items.
  purchase_display: string | null
}

export interface OrderListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Order[]
}

export interface OrderSyncStoreResult {
  synced_count: number
  updated_count: number
  error: string | null
}

export interface OrderSyncResponse {
  status: 'completed' | 'partial'
  stores: {
    gimssine: OrderSyncStoreResult
    etoile: OrderSyncStoreResult
  }
  total_synced: number
  total_updated: number
}

// SPEC-ORDER-SYNC-HEALTH: super_admin-only sync health indicator (GET
// /api/orders/sync-status/, 403 for admin). `last_run_at` is the MIN across
// stores and null when any store has never run — treat null as
// unknown/stopped, never as fresh. `last_synced_updated_at` is a Shopify
// cursor, not a run time — do not present it as "last sync".
export interface OrderSyncStatusStore {
  store_type: 'gimssine' | 'etoile'
  last_run_at: string | null
  last_synced_updated_at: string | null
}

export interface OrderSyncStatus {
  last_run_at: string | null
  stores: OrderSyncStatusStore[]
}

export interface OrderListParams {
  page?: number
  store_type?: 'gimssine' | 'etoile' | ''
  financial_status?: string
  fulfillment_status?: string
  location?: string
  date_from?: string
  date_to?: string
  search?: string
  // SPEC-ORDER-023 REQ-OLIST-023~025: one of the 6 accepted
  // logistics_display values (see Order.logistics_display). Unrecognized
  // values are ignored server-side (fail-open, REQ-OLIST-024a).
  logistics_display?: string
}

// SPEC-ORDER-003: Order Detail types
export interface OrderCustomerDetail {
  shopify_customer_id: number
  first_name: string | null
  last_name: string | null
  email: string | null
  phone: string | null
}

export interface ShippingAddress {
  name: string | null
  first_name: string | null
  last_name: string | null
  address1: string | null
  address2: string | null
  city: string | null
  province: string | null
  province_code: string | null
  country: string | null
  country_code: string | null
  zip: string | null
  phone: string | null
}

// SPEC-ORDER-010: LineItemNote types
export type LineItemNoteAssignee = 'CS' | '발주' | '한국창고' | '미국창고'

export const ASSIGNEE_NOTE_TYPES: Record<LineItemNoteAssignee, string[]> = {
  CS: ['주문취소', '주문보류', 'CS필요', '타출판사', 'CS요청'],
  발주: ['발주요청', '발주제외'],
  한국창고: [],
  미국창고: [],
}

export interface LineItemNote {
  id: number
  content: string
  author_username: string | null
  assignee: LineItemNoteAssignee | ''
  note_type: string
  created_at: string
  is_resolved: boolean
}

export interface LineItemNoteUnresolved extends LineItemNote {
  line_item_id: number
  line_item_sku: string | null
  line_item_title: string | null
  order_name: string | null
  order_id: number
  confirmed_distributor: string | null
}

export interface LineItemDetail {
  id: number
  shopify_line_item_id: number
  title: string | null
  variant_title: string | null
  sku: string | null
  quantity: number | null
  price: string | null
  total_discount: string | null
  fulfillment_status: string | null
  vendor: string | null
  grams: number | null
  location: string
  confirmed_price: string | null
  confirmed_distributor: string | null
  confirmed_at: string | null
  notes: LineItemNote[]
  // SPEC-ORDER-011 REQ-LOGI-001: Korea-vendor -> US-warehouse -> customer
  // logistics pipeline status, independent of purchase_status/fulfillment_status.
  logistics_status: string
  // SPEC-ORDER-013 REQ-RACK-001: short operational storage-rack code, manual/
  // upload-only, independent of `location`/`logistics_status`/`purchase_status`.
  // Exposed here for reuse by RackNumberPage; OrderDetailPage must not render it
  // (REQ-RACK-012).
  rack_number: string
}

export interface ShippingLine {
  title: string | null
  code: string | null
  price: string | null
  source: string | null
}

export interface Refund {
  shopify_refund_id: number
  note: string | null
  shopify_created_at: string | null
  line_item_id: number | null
  quantity: number | null
  subtotal: string | null
  total_tax: string | null
}

export interface OrderNote {
  id: number
  shopify_order_id: number
  store_type: 'gimssine' | 'etoile'
  order_number: number | null
  name: string | null
  note: string
  note_resolved: boolean
  shopify_created_at: string | null
  customer: OrderCustomer | null
}

export interface OrderDetail {
  id: number
  shopify_order_id: number
  store_type: 'gimssine' | 'etoile'
  order_number: number | null
  name: string | null
  email: string | null
  phone: string | null
  financial_status: string | null
  fulfillment_status: string | null
  total_price: string | null
  subtotal_price: string | null
  total_tax: string | null
  total_discounts: string | null
  total_shipping_price_set: string | null
  currency: string | null
  gateway: string | null
  note: string | null
  tags: string | null
  cancel_reason: string | null
  source_name: string | null
  shopify_created_at: string | null
  shopify_updated_at: string | null
  closed_at: string | null
  cancelled_at: string | null
  processed_at: string | null
  note_resolved?: boolean
  has_refund: boolean
  margin_amount: string | null
  margin_rate: string | null
  // SPEC-ORDER-021 REQ-COST-017: cost breakdown backing the margin fields
  // above — shipping cost (weight-based) and Korea-warehouse handling fee,
  // both USD, same null gate as margin_amount/margin_rate.
  shipping_cost: string | null
  korea_warehouse_cost: string | null
  // SPEC-ORDER-021 extension: confirmed purchase cost (confirmed_cost_usd)
  // and total_cost (confirmed_cost + shipping_cost + korea_warehouse_cost,
  // summed server-side from unrounded values — do not re-derive this by
  // summing the three fields above on the frontend). Same null gate.
  confirmed_cost: string | null
  total_cost: string | null
  // SPEC-ORDER-021 extension (v1.4.0): the ExchangeRate record actually
  // applied by the backend's _get_exchange_rate() fallback lookup — surfaces
  // the applied rate and its effective_date (which may be earlier than the
  // order date when the fallback kicked in). NOT gated by has_any_confirmed
  // like the fields above — non-null whenever a rate record was found, even
  // if margin_amount is null because nothing is confirmed yet.
  exchange_rate: string | null
  exchange_rate_date: string | null
  customer: OrderCustomerDetail | null
  shipping_address: ShippingAddress | null
  line_items: LineItemDetail[]
  shipping_lines: ShippingLine[]
  refunds: Refund[]
  // SPEC-ORDER-011 REQ-LOGI-008: computed aggregate over trackable child
  // LineItems' logistics_status. Null when no trackable LineItems exist.
  status: string | null
  // SPEC-ORDER-012 REQ-RTS-001/002: computed "ready to ship" aggregate,
  // fully independent of `status` above. True/False/null.
  ready_to_ship: boolean | null
  // 주문상세/주문목록 표시 일원화: derived live from LineItem rows by the
  // backend (LineItemStateDerivationMixin), identical to the 주문목록 field
  // of the same name. The 입고출고 현황 badge reads this, not `status`.
  logistics_display: string | null
  purchase_display: string | null
}
