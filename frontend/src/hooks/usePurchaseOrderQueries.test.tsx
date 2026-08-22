import type { ReactNode } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  updateLineItemStatus,
  bulkUpdateLineItemStatus,
  confirmLineItem,
} from '@/services/purchaseOrderApi'
import {
  QUERY_KEYS,
  useUpdateLineItemStatus,
  useBulkUpdateLineItemStatus,
  useConfirmLineItem,
} from './usePurchaseOrderQueries'

vi.mock('@/services/purchaseOrderApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/purchaseOrderApi')>()
  return {
    ...actual,
    updateLineItemStatus: vi.fn(),
    bulkUpdateLineItemStatus: vi.fn(),
    confirmLineItem: vi.fn(),
  }
})

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

const mockUpdate = vi.mocked(updateLineItemStatus)
const mockBulkUpdate = vi.mocked(bulkUpdateLineItemStatus)
const mockConfirm = vi.mocked(confirmLineItem)

/**
 * T14 (AC-RESTORE-014) — SPEC-ORDER-018 REQ-RESTORE-021.
 *
 * Verified as a hook unit test inside a real QueryClientProvider with
 * `invalidateQueries` spied, which plan.md's risk R4 lists as an accepted
 * verification route. It cannot live in UnorderedItemsTab.test.tsx: that file
 * replaces the whole `usePurchaseOrderQueries` module with a `vi.mock`
 * factory, so the real `onSuccess` callbacks under test here never run there.
 */
function makeHarness() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  })
  const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
  function wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
  return { wrapper, invalidateSpy }
}

function invalidatedKeys(spy: ReturnType<typeof makeHarness>['invalidateSpy']): unknown[] {
  return spy.mock.calls.map((call) => (call[0] as { queryKey: unknown }).queryKey)
}

describe('purchase status mutations invalidate both list queries (AC-RESTORE-014)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('useUpdateLineItemStatus invalidates the unordered AND excluded-items queries', async () => {
    mockUpdate.mockResolvedValueOnce(undefined)
    const { wrapper, invalidateSpy } = makeHarness()
    const { result } = renderHook(() => useUpdateLineItemStatus(), { wrapper })

    result.current.mutate({ id: 101, purchaseStatus: 'unordered' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const keys = invalidatedKeys(invalidateSpy)
    expect(keys).toContainEqual(QUERY_KEYS.unordered)
    expect(keys).toContainEqual(QUERY_KEYS.excludedItems)
  })

  it('useBulkUpdateLineItemStatus invalidates the unordered AND excluded-items queries', async () => {
    mockBulkUpdate.mockResolvedValueOnce({ updated_count: 2, missing_ids: [] })
    const { wrapper, invalidateSpy } = makeHarness()
    const { result } = renderHook(() => useBulkUpdateLineItemStatus(), { wrapper })

    result.current.mutate({ ids: [101, 202], purchaseStatus: 'unordered' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const keys = invalidatedKeys(invalidateSpy)
    expect(keys).toContainEqual(QUERY_KEYS.unordered)
    expect(keys).toContainEqual(QUERY_KEYS.excludedItems)
  })

  it('the two query keys are distinct but share the purchase-orders prefix', () => {
    expect(QUERY_KEYS.excludedItems).not.toEqual(QUERY_KEYS.unordered)
    expect(QUERY_KEYS.excludedItems[0]).toBe('purchase-orders')
  })
})

/**
 * SPEC-ORDER-025 AC-LCONF-104/105 — verification method fixed by
 * acceptance.md: a real QueryClientProvider with `invalidateQueries` spied,
 * reusing the exact harness above (SPEC-ORDER-018 precedent this file
 * already established).
 */
describe('useConfirmLineItem (AC-LCONF-104/105)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AC-LCONF-104: on success, invalidates unordered, excludedItems, and the purchase-orders list key', async () => {
    mockConfirm.mockResolvedValueOnce({
      line_item_id: 1,
      purchase_order_id: 99,
      distributor: 'kyobo',
      unit_price: null,
    })
    const { wrapper, invalidateSpy } = makeHarness()
    const { result } = renderHook(() => useConfirmLineItem(), { wrapper })

    result.current.mutate({ id: 1, distributor: 'kyobo', unitPrice: null })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const keys = invalidatedKeys(invalidateSpy)
    expect(keys).toContainEqual(QUERY_KEYS.unordered)
    expect(keys).toContainEqual(QUERY_KEYS.excludedItems)
    expect(keys).toContainEqual(['purchase-orders', 'list'])
  })

  it('AC-LCONF-105: on failure, invalidates nothing', async () => {
    mockConfirm.mockRejectedValueOnce({
      response: { status: 409, data: { error: '이미 발주서에 연결되어 있습니다.' } },
    })
    const { wrapper, invalidateSpy } = makeHarness()
    const { result } = renderHook(() => useConfirmLineItem(), { wrapper })

    result.current.mutate({ id: 1, distributor: 'kyobo', unitPrice: null })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(invalidateSpy).not.toHaveBeenCalled()
  })
})
