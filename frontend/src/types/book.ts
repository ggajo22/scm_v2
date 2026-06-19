export interface StatusCount {
  status: number
  label: string
  count: number
}

export interface DashboardMetrics {
  status_counts: StatusCount[]
  shopify_created_24h: number
  error_total: number
  error_rows: StatusCount[]
  waiting_total: number
  unresolved_note_count: number
  sale_zero_count: number
  cost_zero_count: number
}

// REQ-SEARCH-011: book search result fields
export interface BookSearchResult {
  inven_SKU: string
  name: string
  price_sale: number
  status_of_shopify: number
}

// REQ-SEARCH-007: DRF paginated response wrapper
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
