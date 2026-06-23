import { api } from '@/lib/axios'

// --- Type Definitions ---

export interface UnorderedItem {
  id: number
  order_name: string | null
  sku: string
  title: string
  vendor: string
  quantity: number
  auto_distributor: string | null
  purchase_status: string
}

export const PURCHASE_STATUS_OPTIONS = [
  { value: 'unordered', label: '미발주' },
  { value: 'on_hold', label: '주문보류' },
  { value: 'order_cancelled', label: '주문취소' },
  { value: 'other_publisher', label: '타출판사' },
  { value: 'cs_required', label: 'CS필요' },
  { value: 'in_stock', label: '재고' },
] as const

export type PurchaseStatusValue = (typeof PURCHASE_STATUS_OPTIONS)[number]['value']

export interface VendorRule {
  id: number
  publisher_name: string
  distributor: string
  created_at: string
}

export interface PurchaseOrder {
  id: number
  sku: string
  title: string
  distributor: string
  quantity: number
  net_quantity: number
  unit_price: string | null
  status: string
  created_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface WarningResponse {
  unknown_skus: string[]
}

export interface UploadVendorResponse {
  parsed_count: number
  distributor: string
}

export interface PurchaseOrderParams {
  distributor?: string
  status?: string
  date_from?: string
  date_to?: string
  page?: number
}

// --- API Functions ---

// @MX:ANCHOR: [AUTO] Central purchase order API module used by all purchase order hooks
// @MX:REASON: Fan-in >= 3 — usePurchaseOrderQueries hooks consume all exported functions

export async function getUnorderedItems(): Promise<{ count: number; results: UnorderedItem[] }> {
  const res = await api.get('/api/purchase-orders/unordered/')
  return res.data
}

export async function generateOrderFile(data: {
  distributor: string
  skus: string[]
}): Promise<Blob | WarningResponse> {
  const res = await api.post('/api/purchase-orders/generate-order-file/', data, {
    responseType: 'blob',
    validateStatus: (status) => status < 500,
  })

  // If backend returns warning JSON (non-blob content type), parse it
  const contentType = res.headers['content-type'] ?? ''
  if (contentType.includes('application/json')) {
    const text = await (res.data as Blob).text()
    return JSON.parse(text) as WarningResponse
  }

  return res.data as Blob
}

export async function uploadVendorFile(formData: FormData): Promise<UploadVendorResponse> {
  const res = await api.post('/api/purchase-orders/upload-vendor-file/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function getVendorRules(): Promise<{ count: number; results: VendorRule[] }> {
  const res = await api.get('/api/purchase-orders/vendor-rules/')
  return res.data
}

export async function createVendorRule(data: {
  publisher_name: string
  distributor: string
}): Promise<VendorRule> {
  const res = await api.post('/api/purchase-orders/vendor-rules/', data)
  return res.data
}

export async function deleteVendorRule(id: number): Promise<void> {
  await api.delete(`/api/purchase-orders/vendor-rules/${id}/`)
}

export async function updateLineItemStatus(
  id: number,
  purchaseStatus: string
): Promise<void> {
  await api.patch(`/api/purchase-orders/line-items/${id}/status/`, {
    purchase_status: purchaseStatus,
  })
}

export async function bulkUpdateLineItemStatus(
  ids: number[],
  purchaseStatus: string
): Promise<{ updated_count: number; missing_ids: number[] }> {
  const res = await api.patch('/api/purchase-orders/line-items/bulk-status/', {
    ids,
    purchase_status: purchaseStatus,
  })
  return res.data
}

export async function getPurchaseOrders(
  params?: PurchaseOrderParams
): Promise<PaginatedResponse<PurchaseOrder>> {
  const searchParams: Record<string, string> = {}
  if (params?.distributor) searchParams.distributor = params.distributor
  if (params?.status) searchParams.status = params.status
  if (params?.date_from) searchParams.date_from = params.date_from
  if (params?.date_to) searchParams.date_to = params.date_to
  if (params?.page && params.page > 1) searchParams.page = String(params.page)

  const res = await api.get('/api/purchase-orders/', { params: searchParams })
  return res.data
}

export async function downloadDailyReview(): Promise<Blob> {
  const res = await api.get('/api/purchase-orders/daily-review-excel/', {
    responseType: 'blob',
  })
  return res.data as Blob
}

export async function uploadDailyReview(formData: FormData): Promise<{
  confirmed_count: number
  skipped_count: number
  errors: Array<{ sku: string; error: string }>
}> {
  const res = await api.post('/api/purchase-orders/upload-daily-review/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
