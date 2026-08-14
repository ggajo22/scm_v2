import type { ReactNode } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  searchDamagedExchangeCandidates,
  submitDamagedExchange,
} from '@/services/damagedExchangeApi'
import type { DamagedExchangeSearchResponse } from '@/services/damagedExchangeApi'
import { useSearchDamagedExchange, useSubmitDamagedExchange } from './useDamagedExchangeQueries'

vi.mock('@/services/damagedExchangeApi', () => ({
  searchDamagedExchangeCandidates: vi.fn(),
  submitDamagedExchange: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const mockSearch = vi.mocked(searchDamagedExchangeCandidates)
const mockSubmit = vi.mocked(submitDamagedExchange)

function buildSearchResponse(
  overrides: Partial<DamagedExchangeSearchResponse> = {}
): DamagedExchangeSearchResponse {
  return {
    count: 0,
    results: [],
    ...overrides,
  }
}

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useSearchDamagedExchange — SPEC-PURCHASE-ORDER-011 REQ-DEX-004', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not fetch when sku is null (no search submitted yet)', () => {
    const { result } = renderHook(() => useSearchDamagedExchange(null), { wrapper })

    expect(result.current.fetchStatus).toBe('idle')
    expect(mockSearch).not.toHaveBeenCalled()
  })

  it('does not fetch when sku is an empty string', () => {
    const { result } = renderHook(() => useSearchDamagedExchange(''), { wrapper })

    expect(result.current.fetchStatus).toBe('idle')
    expect(mockSearch).not.toHaveBeenCalled()
  })

  it('fetches once a non-empty sku is submitted', async () => {
    mockSearch.mockResolvedValueOnce(buildSearchResponse({ count: 1 }))
    const { result } = renderHook(() => useSearchDamagedExchange('9788956609959'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockSearch).toHaveBeenCalledTimes(1)
    expect(mockSearch).toHaveBeenCalledWith('9788956609959')
    expect(result.current.data?.count).toBe(1)
  })
})

describe('useSubmitDamagedExchange — SPEC-PURCHASE-ORDER-011 REQ-DEX-009', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls submitDamagedExchange with the id and damaged quantity', async () => {
    mockSubmit.mockResolvedValueOnce({ id: 5, purchase_status: 'damaged_exchange', damaged_quantity: 3 })
    const { result } = renderHook(() => useSubmitDamagedExchange(), { wrapper })

    result.current.mutate({ id: 5, damagedQuantity: 3 })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockSubmit).toHaveBeenCalledTimes(1)
    expect(mockSubmit).toHaveBeenCalledWith(5, 3)
  })

  it('shows a success toast on success', async () => {
    mockSubmit.mockResolvedValueOnce({ id: 5, purchase_status: 'damaged_exchange', damaged_quantity: 3 })
    const { result } = renderHook(() => useSubmitDamagedExchange(), { wrapper })

    result.current.mutate({ id: 5, damagedQuantity: 3 })

    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('shows an error toast and no success toast when the submission is rejected (e.g. HTTP 400 out-of-range)', async () => {
    mockSubmit.mockRejectedValueOnce(
      Object.assign(new Error('400'), { response: { status: 400 } })
    )
    const { result } = renderHook(() => useSubmitDamagedExchange(), { wrapper })

    result.current.mutate({ id: 5, damagedQuantity: 99 })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(toast.error).toHaveBeenCalledTimes(1)
    expect(toast.success).not.toHaveBeenCalled()
  })
})
