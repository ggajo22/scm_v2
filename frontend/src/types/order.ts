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
}
