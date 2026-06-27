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

export interface OrderListParams {
  page?: number
  store_type?: 'gimssine' | 'etoile' | ''
  financial_status?: string
  fulfillment_status?: string
  location?: string
  date_from?: string
  date_to?: string
  search?: string
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
  발주: ['주문요청', '발주제외'],
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
  line_item_sku: string | null
  line_item_title: string | null
  order_name: string | null
  order_id: number
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
  customer: OrderCustomerDetail | null
  shipping_address: ShippingAddress | null
  line_items: LineItemDetail[]
  shipping_lines: ShippingLine[]
  refunds: Refund[]
}
