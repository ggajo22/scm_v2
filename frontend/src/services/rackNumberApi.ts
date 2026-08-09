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
