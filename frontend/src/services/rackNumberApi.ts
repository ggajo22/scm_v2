import { api } from '@/lib/axios'

// ---------------------------------------------------------------------------
// SPEC-ORDER-013: rack_number management API service
// ---------------------------------------------------------------------------

export interface RackNumberResponse {
  id: number
  rack_number: string
  sku: string | null
}

export interface BulkRackNumberResponse {
  updated_count: number
  missing_ids: number[]
}

export interface UploadRackNumberResponse {
  matched_count: number
  skipped_count: number
}

// REQ-RACK-003/003a/003b: single LineItem rack_number update.
export async function updateLineItemRackNumber(
  id: number,
  rackNumber: string
): Promise<RackNumberResponse> {
  const res = await api.patch(`/api/purchase-orders/line-items/${id}/rack-number/`, {
    rack_number: rackNumber,
  })
  return res.data
}

// REQ-RACK-004/004a: batched LineItem rack_number update (explicit id list).
export async function bulkUpdateLineItemRackNumber(
  ids: number[],
  rackNumber: string
): Promise<BulkRackNumberResponse> {
  const res = await api.patch('/api/purchase-orders/line-items/bulk-rack-number/', {
    ids,
    rack_number: rackNumber,
  })
  return res.data
}

// REQ-RACK-005/006/006a/006b/007: 3-column (order number/SKU/rack number)
// Excel upload.
export async function uploadRackNumber(formData: FormData): Promise<UploadRackNumberResponse> {
  const res = await api.post('/api/purchase-orders/upload-rack-number/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

// ---------------------------------------------------------------------------
// SPEC-ORDER-014: cross-order rack_number summary API (read-only, Tab2)
// ---------------------------------------------------------------------------

export interface RackNumberSummaryLineItem {
  id: number
  order_name: string | null
  sku: string | null
  title: string | null
  quantity: number | null
  logistics_status: string
}

export interface RackNumberSummaryGroup {
  rack_number: string
  is_unassigned: boolean
  total_quantity: number
  line_items: RackNumberSummaryLineItem[]
}

export interface RackNumberSummaryResponse {
  groups: RackNumberSummaryGroup[]
}

// REQ-RACKSUM-001~008: cross-order read-only rack_number summary.
export async function getRackNumberSummary(): Promise<RackNumberSummaryResponse> {
  const res = await api.get('/api/purchase-orders/line-items/rack-number-summary/')
  return res.data
}
