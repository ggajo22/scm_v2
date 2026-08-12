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
  // SPEC-PURCHASE-ORDER-010 REQ-DMG-001
  { value: 'damaged_exchange', label: '파손/교환' },
] as const

export type PurchaseStatusValue = (typeof PURCHASE_STATUS_OPTIONS)[number]['value']

// SPEC-ORDER-011 REQ-LOGI-001: 5-value logistics_status pipeline
// (Korea vendor -> US warehouse -> customer), fully independent of
// PURCHASE_STATUS_OPTIONS above and of fulfillment_status.
export const LOGISTICS_STATUS_OPTIONS = [
  { value: 'not_shipped', label: '미입고' },
  { value: 'shipment_confirmed', label: '입고예정' },
  { value: 'received', label: '입고' },
  { value: 'outbound_scheduled', label: '출고예정' },
  { value: 'shipped', label: '출고' },
] as const

export type LogisticsStatusValue = (typeof LOGISTICS_STATUS_OPTIONS)[number]['value']

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

export interface SkuQuantity {
  sku: string
  title: string
  quantity: number
}

export interface UploadDailyReviewResponse {
  message?: string
  confirmed_count?: number
  skipped_count?: number
  confirmed_by_distributor: Record<string, SkuQuantity[]>
}

export async function uploadDailyReview(formData: FormData): Promise<UploadDailyReviewResponse> {
  const res = await api.post('/api/purchase-orders/upload-daily-review/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

// ---------------------------------------------------------------------------
// SPEC-ORDER-011 T11: logistics_status endpoints
// ---------------------------------------------------------------------------

export interface LineItemLogisticsStatusResponse {
  id: number
  logistics_status: string
  sku: string | null
}

export interface BulkLogisticsStatusResponse {
  updated_count: number
  missing_ids: number[]
}

// Shared minimal shape for both logistics upload endpoints. The vendor
// shipment endpoint (uploadVendorShipment) returns exactly this — counts
// only, no per-row detail.
export interface UploadLogisticsResponse {
  matched_count: number
  skipped_count: number
}

// REQ-LOGI-017: failure reason codes returned by
// `_process_warehouse_receipt_rows` for the `unmatched` category. No
// quantity column exists on this upload (rows are counted, not summed), so
// there is no `invalid_total` analog here — unlike OutboundUnmatchedReason.
//
// Keep this union in sync with the reason strings in
// backend/order/purchase_order_views.py — an unlisted code falls through to
// the raw snake_case fallback in LogisticsStatusTab.
export type WarehouseReceiptUnmatchedReason =
  | 'order_not_found'
  | 'line_item_not_found'
  | 'multiple_line_items'
  // Blank order name or blank SKU, rejected before matching.
  | 'invalid_row'

export interface WarehouseReceiptMatchedItem {
  name: string
  sku: string
  // Number of rows counted for this (order, sku) key in THIS upload — not a
  // summed quantity column (there isn't one).
  received_count: number
  line_item_id: number
  // Post-update cumulative received quantity (REQ-LOGI-015).
  received_quantity: number
  // Nullable on the model — null is treated as capacity 0.
  quantity: number | null
  logistics_status: string
}

export interface WarehouseReceiptUnmatchedItem {
  name: string
  sku: string
  received_count: number
  reason: WarehouseReceiptUnmatchedReason
}

export interface WarehouseReceiptQuantityExceededItem {
  name: string
  sku: string
  received_count: number
  line_item_id: number
  // Pre-update values — nothing was written for this row (REQ-LOGI-015).
  received_quantity: number
  quantity: number | null
  reason: 'quantity_exceeded'
}

// REQ-LOGI-017: uploadWarehouseReceipt's response, extending the shared
// counts-only shape with the three per-row detail lists so the UI can show
// WHICH rows were skipped and why — same three-category payload
// OutboundProcessResponse carries (REQ-OUTBOUND-014).
export interface UploadWarehouseReceiptResponse extends UploadLogisticsResponse {
  matched: WarehouseReceiptMatchedItem[]
  unmatched: WarehouseReceiptUnmatchedItem[]
  unmatched_count: number
  quantity_exceeded: WarehouseReceiptQuantityExceededItem[]
  quantity_exceeded_count: number
}

// REQ-LOGI-007/007a: single LineItem logistics_status update.
export async function updateLineItemLogisticsStatus(
  id: number,
  logisticsStatus: string
): Promise<LineItemLogisticsStatusResponse> {
  const res = await api.patch(`/api/purchase-orders/line-items/${id}/logistics-status/`, {
    logistics_status: logisticsStatus,
  })
  return res.data
}

// REQ-LOGI-007/007a/010: batched LineItem logistics_status update.
export async function bulkUpdateLineItemLogisticsStatus(
  ids: number[],
  logisticsStatus: string
): Promise<BulkLogisticsStatusResponse> {
  const res = await api.patch('/api/purchase-orders/line-items/bulk-logistics-status/', {
    ids,
    logistics_status: logisticsStatus,
  })
  return res.data
}

// REQ-LOGI-003/004: vendor shipment confirmation upload → shipment_confirmed.
export async function uploadVendorShipment(formData: FormData): Promise<UploadLogisticsResponse> {
  const res = await api.post('/api/purchase-orders/upload-vendor-shipment/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

// REQ-LOGI-005/006/017: warehouse receiving results upload → received.
export async function uploadWarehouseReceipt(
  formData: FormData
): Promise<UploadWarehouseReceiptResponse> {
  const res = await api.post('/api/purchase-orders/upload-warehouse-receipt/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
