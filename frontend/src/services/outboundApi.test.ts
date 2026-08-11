import { describe, it, expect, vi, beforeEach } from 'vitest'

// The axios instance is mocked so these are pure contract tests — no network,
// no MSW handler needed (setup.ts runs MSW with onUnhandledRequest: 'error').
vi.mock('@/lib/axios', () => ({
  api: { post: vi.fn() },
}))

import { api } from '@/lib/axios'
import { processOutboundManual, uploadOutbound } from './outboundApi'
import type { OutboundProcessResponse, OutboundUnmatchedReason } from './outboundApi'

const mockPost = vi.mocked(api.post)

// Mirrors the exact serialized shape built by `_process_outbound_rows`
// (backend/order/purchase_order_views.py) — SPEC-ORDER-015 REQ-OUTBOUND-014.
function buildResponse(
  overrides: Partial<OutboundProcessResponse> = {}
): OutboundProcessResponse {
  return {
    matched: [
      {
        name: '#37349',
        sku: 'ISBN001',
        total: 4,
        line_item_id: 11,
        shipped_quantity: 4,
        quantity: 10,
        logistics_status: 'received',
      },
    ],
    matched_count: 1,
    unmatched: [
      { name: '#99999', sku: 'ISBN001', total: 3, reason: 'order_not_found' },
    ],
    unmatched_count: 1,
    quantity_exceeded: [
      {
        name: '#37349',
        sku: 'ISBN002',
        total: 5,
        line_item_id: 12,
        shipped_quantity: 8,
        quantity: 10,
        reason: 'quantity_exceeded',
      },
    ],
    quantity_exceeded_count: 1,
    ...overrides,
  }
}

// The backend fix cycle (negative-total defect: a negative total decremented
// shipped_quantity, re-implementing the excluded "undo" capability) added
// per-row validation, expanding the reason codes from 3 to 5. This list is a
// compile-time assertion: a stale union makes `tsc` reject the extra members.
const ALL_UNMATCHED_REASONS: OutboundUnmatchedReason[] = [
  'order_not_found',
  'line_item_not_found',
  'multiple_line_items',
  'invalid_total',
  'invalid_row',
]

describe('OutboundUnmatchedReason — backend reason-code contract', () => {
  it('covers all five reason codes emitted by _process_outbound_rows', () => {
    expect(ALL_UNMATCHED_REASONS).toHaveLength(5)
  })

  it('includes invalid_total, emitted for a non-positive total rejected per-row', () => {
    expect(ALL_UNMATCHED_REASONS).toContain('invalid_total')
  })

  it('includes invalid_row, emitted for a malformed row reaching the shared processing path', () => {
    expect(ALL_UNMATCHED_REASONS).toContain('invalid_row')
  })
})

describe('processOutboundManual — SPEC-ORDER-015 REQ-OUTBOUND-011/016', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the rows to the manual outbound-process endpoint', async () => {
    mockPost.mockResolvedValueOnce({ data: buildResponse() })

    await processOutboundManual([{ name: '#37349', sku: 'ISBN001', total: 4 }])

    expect(mockPost).toHaveBeenCalledWith(
      '/api/purchase-orders/line-items/outbound-process/',
      { rows: [{ name: '#37349', sku: 'ISBN001', total: 4 }] }
    )
  })

  it('wraps multiple rows in a single { rows: [...] } body', async () => {
    mockPost.mockResolvedValueOnce({ data: buildResponse() })

    const rows = [
      { name: '#37349', sku: 'ISBN001', total: 3 },
      { name: '#37350', sku: 'ISBN002', total: 1 },
    ]
    await processOutboundManual(rows)

    expect(mockPost).toHaveBeenCalledWith(
      '/api/purchase-orders/line-items/outbound-process/',
      { rows }
    )
  })

  it('AC-OUTBOUND-016: returns the 3-category response payload unwrapped from res.data', async () => {
    const payload = buildResponse()
    mockPost.mockResolvedValueOnce({ data: payload })

    const result = await processOutboundManual([{ name: '#37349', sku: 'ISBN001', total: 4 }])

    expect(result).toEqual(payload)
    expect(result.matched_count).toBe(1)
    expect(result.unmatched_count).toBe(1)
    expect(result.quantity_exceeded_count).toBe(1)
  })

  it('propagates a rejected request to the caller', async () => {
    mockPost.mockRejectedValueOnce(new Error('boom'))

    await expect(
      processOutboundManual([{ name: '#37349', sku: 'ISBN001', total: 4 }])
    ).rejects.toThrow('boom')
  })
})

describe('uploadOutbound — SPEC-ORDER-015 REQ-OUTBOUND-013/016', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the FormData to the Excel upload endpoint as multipart/form-data', async () => {
    mockPost.mockResolvedValueOnce({ data: buildResponse() })
    const formData = new FormData()
    formData.append('file', new File(['x'], 'outbound.xlsx'))

    await uploadOutbound(formData)

    expect(mockPost).toHaveBeenCalledWith(
      '/api/purchase-orders/upload-outbound/',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  })

  it('AC-OUTBOUND-014: returns the same 3-category response shape as the manual endpoint', async () => {
    const payload = buildResponse()
    mockPost.mockResolvedValueOnce({ data: payload })

    const result = await uploadOutbound(new FormData())

    expect(result).toEqual(payload)
  })

  it('propagates a rejected upload (e.g. HTTP 422 header parse failure) to the caller', async () => {
    mockPost.mockRejectedValueOnce(new Error('422'))

    await expect(uploadOutbound(new FormData())).rejects.toThrow('422')
  })
})
