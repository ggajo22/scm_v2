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
