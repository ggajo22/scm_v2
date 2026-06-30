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
// Note: id field requires backend BookSearchSerializer to expose id (SPEC-BOOK-EDIT-001 dependency)
export interface BookSearchResult {
  id: number
  inven_SKU: string
  name: string
  price_sale: number
  status_of_shopify: number
}

// Book detail types (SPEC-BOOK-EDIT-001)
export interface BookInfo {
  id: number
  status: string
  price_sale: number
  name: string
  useruse1: string
  useruse2: string
  price: number
  opndate: string
  outrt2: number
  qty: number
  retyn: string
  booxen_cate_cd1: number
  booxen_cate_cd2: number
  booxen_cate_cd3: number
  page: number
  weight: number
  kyobo_weight: number
  kyobo_status: string
  kyobo_supply_price: number
  yes24_weight: number
  aladin_weight: number
  manual_weight: number | null
  dim1: number | null
  dim2: number | null
  dim3: number | null
  image_detail: string
  cover_image_url: string
  cover_image_url2: string | null
  desc_table: string
  desc_pub: string
  desc_author: string
  desc_desc: string
  kyobo_category1: string
  kyobo_category2: string
  kyobo_category3: string
  kyobo_category4: string
  kyobo_category5: string
  updated_at: string
}

export interface BookNote {
  id: number
  note_type: 'GENERAL' | 'SHIPPING'
  content: string
  is_resolved: boolean
  resolved_at: string | null
  created_by: string
  created_at: string
}

export interface ShopifyProduct {
  id: number
  product_id: string
  variant_id: string
  inventory_item_id: string
  shopify_price: number
  is_new_arrival: boolean
  image_url: string
}

export interface EtoileInfo {
  id: number
  name_en: string
  desc_en: string
  preview_urls: string[]
  tags: string[]
  updated_at: string
}

export interface EtoileInven {
  id: number
  status_of_shopify: number | null
  updated_at: string
}

export interface BookDetail {
  id: number
  inven_SKU: string
  vendor: string
  store: string
  status_of_shopify: number
  info: BookInfo
  notes: BookNote[]
  shopify_products: ShopifyProduct[]
  etoile: {
    inven: EtoileInven
    info: EtoileInfo | null
    shopify_products: ShopifyProduct[]
  } | null
}

// SPEC-ETOILE-DASHBOARD-001
export interface EtoileStatusCount {
  status: number | null
  label: string
  count: number
}

export interface EtoileDashboard {
  status_counts: EtoileStatusCount[]
  total: number
}

// REQ-SEARCH-007: DRF paginated response wrapper
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// SPEC-SHOPIFY-INFO-001: real-time Shopify product info types
export interface ShopifyStoreInfo {
  registered: boolean
  product_id: string | null
  variant_id: string | null
  status: 'active' | 'draft' | 'archived' | null
  weight: number | null
  weight_unit: 'g' | 'kg' | 'lb' | 'oz' | null
  error: string | null
}

export interface ShopifyLiveInfoResponse {
  booxen: ShopifyStoreInfo
  etoile: ShopifyStoreInfo
}
