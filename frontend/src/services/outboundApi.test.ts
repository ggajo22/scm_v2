import { describe, it, expect, vi, beforeEach } from 'vitest'

// The axios instance is mocked so these are pure contract tests — no network,
// no MSW handler needed (setup.ts runs MSW with onUnhandledRequest: 'error').
vi.mock('@/lib/axios', () => ({
  api: { post: vi.fn() },
}))

import { api } from '@/lib/axios'
import {
  processOutboundManual,
  uploadOutbound,
  fetchOutboundForceCandidates,
  processOutboundForce,
} from './outboundApi'
import type {
  OutboundProcessResponse,
  OutboundUnmatchedReason,
  OutboundForceCandidateGroup,
} from './outboundApi'

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

// ---------------------------------------------------------------------------
// SPEC-ORDER-016: force outbound processing (REQ-FORCE-003/004/005/006/015/016)
// ---------------------------------------------------------------------------

describe('fetchOutboundForceCandidates — SPEC-ORDER-016 REQ-FORCE-003/004/005/006', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the batched order_names to the force-candidates endpoint', async () => {
    mockPost.mockResolvedValueOnce({ data: { results: [] } })

    await fetchOutboundForceCandidates(['#37349', '#37350'])

    expect(mockPost).toHaveBeenCalledWith(
      '/api/purchase-orders/line-items/outbound-force-candidates/',
      { order_names: ['#37349', '#37350'] }
    )
  })

  it('returns the results array unwrapped from res.data.results, candidate fields included', async () => {
    const results: OutboundForceCandidateGroup[] = [
      {
        order_name: '#37349',
        candidates: [
          {
            line_item_id: 1,
            title: '도서',
            sku: 'ISBN001',
            quantity: 10,
            shipped_quantity: 4,
            logistics_status: 'received',
            no_remaining_capacity: false,
          },
        ],
      },
    ]
    mockPost.mockResolvedValueOnce({ data: { results } })

    const result = await fetchOutboundForceCandidates(['#37349'])

    expect(result).toEqual(results)
  })

  it('AC-FORCE-003: an empty order name list still round-trips to a single request', async () => {
    mockPost.mockResolvedValueOnce({ data: { results: [] } })

    const result = await fetchOutboundForceCandidates([])

    expect(mockPost).toHaveBeenCalledTimes(1)
    expect(result).toEqual([])
  })

  it('propagates a rejected candidate lookup to the caller', async () => {
    mockPost.mockRejectedValueOnce(new Error('boom'))

    await expect(fetchOutboundForceCandidates(['#37349'])).rejects.toThrow('boom')
  })
})

describe('processOutboundForce — SPEC-ORDER-016 REQ-FORCE-015/016', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the operator-designated rows to the force-process endpoint', async () => {
    mockPost.mockResolvedValueOnce({ data: buildResponse() })
    const rows = [{ name: '#37349', sku: 'ISBN001', total: 4, line_item_id: 11 }]

    await processOutboundForce(rows)

    expect(mockPost).toHaveBeenCalledWith(
      '/api/purchase-orders/line-items/outbound-force-process/',
      { rows }
    )
  })

  it('AC-FORCE-016 (client reuse): returns the existing 3-category response shape unwrapped from res.data', async () => {
    const payload = buildResponse()
    mockPost.mockResolvedValueOnce({ data: payload })

    const result = await processOutboundForce([
      { name: '#37349', sku: 'ISBN001', total: 4, line_item_id: 11 },
    ])

    expect(result).toEqual(payload)
    expect(result.matched_count).toBe(1)
    expect(result.unmatched_count).toBe(1)
    expect(result.quantity_exceeded_count).toBe(1)
  })

  it('surfaces an HTTP 400 gate violation (REQ-FORCE-002) as a rejection', async () => {
    const badRequest = Object.assign(new Error('Request failed with status code 400'), {
      response: {
        status: 400,
        data: { error: 'One or more rows failed target validation.' },
      },
    })
    mockPost.mockRejectedValueOnce(badRequest)

    await expect(
      processOutboundForce([{ name: '#37349', sku: 'ISBN001', total: 4, line_item_id: 11 }])
    ).rejects.toThrow('Request failed with status code 400')
  })
})
