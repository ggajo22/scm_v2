import type { ReactNode } from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import { useBookSearch } from './useBookSearch'

vi.mock('@/lib/axios', () => ({ api: { get: vi.fn() } }))

const mockGet = vi.mocked(api.get)

const emptyPage = { data: { count: 0, next: null, previous: null, results: [] } }

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

// A 13-digit ISBN typed by hand, one keystroke at a time.
const ISBN_KEYSTROKES = [
  '97', '978', '9788', '97889', '978893', '9788937', '97889374',
  '978893746', '9788937460', '97889374601', '978893746012', '9788937460123',
]

beforeEach(() => {
  mockGet.mockReset()
  mockGet.mockResolvedValue(emptyPage)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useBookSearch — request volume', () => {
  it('collapses a hand-typed ISBN into a single request', async () => {
    vi.useFakeTimers()
    const { rerender } = renderHook(({ q }) => useBookSearch(q), {
      wrapper,
      initialProps: { q: '' },
    })
    // Drain the mount request ("show all") so only typing is measured
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400)
    })
    mockGet.mockClear()

    // 50 ms per keystroke — faster than the debounce, as real typing is
    for (const q of ISBN_KEYSTROKES) {
      rerender({ q })
      await act(async () => {
        await vi.advanceTimersByTimeAsync(50)
      })
    }
    // Before the fix this was 12 requests, one per keystroke
    expect(mockGet).not.toHaveBeenCalled()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300)
    })
    expect(mockGet).toHaveBeenCalledTimes(1)
    expect(mockGet.mock.calls[0][1]?.params).toMatchObject({
      search: '9788937460123',
    })
  })

  it('still debounces text search at 300 ms', async () => {
    vi.useFakeTimers()
    const { rerender } = renderHook(({ q }) => useBookSearch(q), {
      wrapper,
      initialProps: { q: '' },
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400)
    })
    mockGet.mockClear()

    rerender({ q: '토지' })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250)
    })
    expect(mockGet).not.toHaveBeenCalled()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100)
    })
    expect(mockGet).toHaveBeenCalledTimes(1)
  })

  it('searches immediately when the query arrives already complete (paste, scanner, direct URL)', async () => {
    renderHook(() => useBookSearch('9788937460123'), { wrapper })

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1))
    expect(mockGet.mock.calls[0][1]?.params).toMatchObject({
      search: '9788937460123',
    })
  })
})

describe('useBookSearch — request cancellation', () => {
  it('passes an AbortSignal so a superseded request releases its connection', async () => {
    renderHook(() => useBookSearch('9788937460123'), { wrapper })

    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(mockGet.mock.calls[0][1]?.signal).toBeInstanceOf(AbortSignal)
  })

  it('aborts the in-flight request when the query key changes', async () => {
    // Keep the first request pending — there is nothing to abort once it settles
    mockGet.mockImplementationOnce(() => new Promise(() => {}))
    const { rerender } = renderHook(({ q }) => useBookSearch(q), {
      wrapper,
      initialProps: { q: '9788937460123' },
    })
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    const firstSignal = mockGet.mock.calls[0][1]?.signal as AbortSignal
    expect(firstSignal.aborted).toBe(false)

    rerender({ q: '9791162540123' })
    await waitFor(() => expect(firstSignal.aborted).toBe(true))
  })
})
