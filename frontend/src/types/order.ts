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
  customer: OrderCustomerDetail | null
  shipping_address: ShippingAddress | null
  line_items: LineItemDetail[]
  shipping_lines: ShippingLine[]
  refunds: Refund[]
}
