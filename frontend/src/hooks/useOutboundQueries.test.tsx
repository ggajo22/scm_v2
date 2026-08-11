import type { ReactNode } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { toast } from 'sonner'
import { processOutboundManual, uploadOutbound } from '@/services/outboundApi'
import type { OutboundProcessResponse } from '@/services/outboundApi'
import { useProcessOutboundManual, useUploadOutbound } from './useOutboundQueries'

vi.mock('@/services/outboundApi', () => ({
  processOutboundManual: vi.fn(),
  uploadOutbound: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

const mockProcess = vi.mocked(processOutboundManual)
const mockUpload = vi.mocked(uploadOutbound)

function buildResponse(
  overrides: Partial<OutboundProcessResponse> = {}
): OutboundProcessResponse {
  return {
    matched: [],
    matched_count: 2,
    unmatched: [],
    unmatched_count: 1,
    quantity_exceeded: [],
    quantity_exceeded_count: 3,
    ...overrides,
  }
}

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useProcessOutboundManual — SPEC-ORDER-015 REQ-OUTBOUND-016', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls processOutboundManual with the submitted rows', async () => {
    mockProcess.mockResolvedValueOnce(buildResponse())
    const { result } = renderHook(() => useProcessOutboundManual(), { wrapper })

    const rows = [{ name: '#37349', sku: 'ISBN001', total: 4 }]
    result.current.mutate(rows)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    // react-query v5 appends a mutation-context arg, so assert on arg 0 only.
    expect(mockProcess).toHaveBeenCalledTimes(1)
    expect(mockProcess.mock.calls[0][0]).toEqual(rows)
  })

  it('exposes the 3-category response as mutation data', async () => {
    const payload = buildResponse()
    mockProcess.mockResolvedValueOnce(payload)
    const { result } = renderHook(() => useProcessOutboundManual(), { wrapper })

    result.current.mutate([{ name: '#37349', sku: 'ISBN001', total: 4 }])

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(payload)
  })

  it('shows a success toast summarizing matched/unmatched/quantity_exceeded counts', async () => {
    mockProcess.mockResolvedValueOnce(buildResponse())
    const { result } = renderHook(() => useProcessOutboundManual(), { wrapper })

    result.current.mutate([{ name: '#37349', sku: 'ISBN001', total: 4 }])

    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    const message = vi.mocked(toast.success).mock.calls[0][0] as string
    expect(message).toContain('2')
    expect(message).toContain('1')
    expect(message).toContain('3')
  })

  it('shows an error toast and no success toast when the request fails', async () => {
    mockProcess.mockRejectedValueOnce(new Error('network down'))
    const { result } = renderHook(() => useProcessOutboundManual(), { wrapper })

    result.current.mutate([{ name: '#37349', sku: 'ISBN001', total: 4 }])

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(toast.error).toHaveBeenCalledTimes(1)
    expect(toast.success).not.toHaveBeenCalled()
  })

  // OutboundProcessView now pre-validates row shape and returns HTTP 400
  // before reaching _process_outbound_rows. Confirm that path surfaces a
  // failure toast rather than being silently swallowed or reported as success.
  it('surfaces an HTTP 400 malformed-row rejection as a failure toast, not a success', async () => {
    const badRequest = Object.assign(new Error('Request failed with status code 400'), {
      response: {
        status: 400,
        data: { detail: 'rows[0] is missing required key(s): total.' },
      },
    })
    mockProcess.mockRejectedValueOnce(badRequest)
    const { result } = renderHook(() => useProcessOutboundManual(), { wrapper })

    result.current.mutate([{ name: '#37349', sku: 'ISBN001', total: 4 }])

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(toast.success).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledTimes(1)

    // The generic message must still name the failed operation — a 400 that
    // produced a blank or misattributed toast would be a mislabel.
    const message = vi.mocked(toast.error).mock.calls[0][0] as string
    expect(message).toContain('출고 처리')
    expect(message.length).toBeGreaterThan(0)
  })

  it('leaves mutation data undefined on a 400 so the page renders no result sections', async () => {
    mockProcess.mockRejectedValueOnce(
      Object.assign(new Error('400'), { response: { status: 400 } })
    )
    const { result } = renderHook(() => useProcessOutboundManual(), { wrapper })

    result.current.mutate([{ name: '#37349', sku: 'ISBN001', total: 4 }])

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.data).toBeUndefined()
  })
})

describe('useUploadOutbound — SPEC-ORDER-015 REQ-OUTBOUND-013/016', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls uploadOutbound with the supplied FormData', async () => {
    mockUpload.mockResolvedValueOnce(buildResponse())
    const { result } = renderHook(() => useUploadOutbound(), { wrapper })

    const formData = new FormData()
    formData.append('file', new File(['x'], 'outbound.xlsx'))
    result.current.mutate(formData)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockUpload).toHaveBeenCalledTimes(1)
    expect(mockUpload.mock.calls[0][0]).toBe(formData)
  })

  it('shows a success toast summarizing the three counts', async () => {
    mockUpload.mockResolvedValueOnce(buildResponse())
    const { result } = renderHook(() => useUploadOutbound(), { wrapper })

    result.current.mutate(new FormData())

    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    const message = vi.mocked(toast.success).mock.calls[0][0] as string
    expect(message).toContain('2')
    expect(message).toContain('1')
    expect(message).toContain('3')
  })

  it('shows an error toast when the upload is rejected (e.g. HTTP 422)', async () => {
    mockUpload.mockRejectedValueOnce(new Error('422'))
    const { result } = renderHook(() => useUploadOutbound(), { wrapper })

    result.current.mutate(new FormData())

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(toast.error).toHaveBeenCalledTimes(1)
    expect(toast.success).not.toHaveBeenCalled()
  })
})
