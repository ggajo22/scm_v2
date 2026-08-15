import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { OrdersPage } from './OrdersPage'
import { useOrders } from '@/features/order/hooks/useOrders'
import { useOrderSync } from '@/features/order/hooks/useOrderSync'
import { useOrderSyncStatus } from '@/features/order/hooks/useOrderSyncStatus'
import { useAuthStore } from '@/store/authStore'
import type { OrderListResponse, OrderSyncStatus } from '@/types/order'

vi.mock('@/features/order/hooks/useOrders', () => ({
  useOrders: vi.fn(),
}))

vi.mock('@/features/order/hooks/useOrderSync', () => ({
  useOrderSync: vi.fn(),
}))

vi.mock('@/features/order/hooks/useOrderSyncStatus', () => ({
  useOrderSyncStatus: vi.fn(),
}))

vi.mock('@/store/authStore')

const mockUseOrders = vi.mocked(useOrders)
const mockUseOrderSync = vi.mocked(useOrderSync)
const mockUseOrderSyncStatus = vi.mocked(useOrderSyncStatus)
const mockUseAuthStore = vi.mocked(useAuthStore)

// Selector-aware mock, same pattern as Sidebar.test.tsx.
function buildAuthMock(role: 'super_admin' | 'admin') {
  const state = {
    accessToken: 'token',
    user: { id: 1, username: 'tester', role, is_active: true },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    restoreSession: vi.fn(),
  }
  return (selector?: (s: typeof state) => unknown) => {
    if (typeof selector === 'function') return selector(state)
    return state
  }
}

function buildOrderList(overrides: Partial<OrderListResponse> = {}): OrderListResponse {
  return {
    count: 0,
    next: null,
    previous: null,
    results: [],
    ...overrides,
  }
}

function renderPage(role: 'super_admin' | 'admin') {
  mockUseAuthStore.mockImplementation(buildAuthMock(role) as typeof useAuthStore)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <OrdersPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('OrdersPage — SPEC-ORDER-SYNC-HEALTH sync status indicator', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOrders.mockReturnValue({
      data: buildOrderList(),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)
    mockUseOrderSync.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useOrderSync>)
  })

  it('admin 역할에게는 표시하지 않으며 상태 조회 훅 자체를 호출하지 않는다', () => {
    renderPage('admin')

    expect(screen.queryByTestId('sync-status-indicator')).not.toBeInTheDocument()
    // The hook must never be invoked for admin — SyncStatusIndicator, which
    // wraps the query, is not mounted at all for this role.
    expect(mockUseOrderSyncStatus).not.toHaveBeenCalled()
  })

  it('super_admin에게는 표시된다', () => {
    mockUseOrderSyncStatus.mockReturnValue({
      data: { last_run_at: new Date().toISOString(), stores: [] } as OrderSyncStatus,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)

    renderPage('super_admin')

    expect(screen.getByTestId('sync-status-indicator')).toBeInTheDocument()
  })

  it('15분 미만이면 평범한(muted) 스타일로 표시한다', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60_000).toISOString()
    mockUseOrderSyncStatus.mockReturnValue({
      data: { last_run_at: fiveMinAgo, stores: [] } as OrderSyncStatus,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)

    renderPage('super_admin')

    const indicator = screen.getByTestId('sync-status-indicator')
    expect(indicator.textContent).toContain('분 전')
    expect(indicator.textContent).not.toContain('중단')
    expect(indicator.className).toContain('text-muted-foreground')
  })

  it('15~60분 사이면 경고 스타일로 표시한다', () => {
    const thirtyMinAgo = new Date(Date.now() - 30 * 60_000).toISOString()
    mockUseOrderSyncStatus.mockReturnValue({
      data: { last_run_at: thirtyMinAgo, stores: [] } as OrderSyncStatus,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)

    renderPage('super_admin')

    const indicator = screen.getByTestId('sync-status-indicator')
    expect(indicator.textContent).toContain('분 전')
    expect(indicator.textContent).not.toContain('중단')
    expect(indicator.className).toContain('text-amber-700')
  })

  it('60분을 초과하면 동기화가 중단되었을 수 있다는 경고를 명시적으로 표시한다', () => {
    const twoHoursAgo = new Date(Date.now() - 125 * 60_000).toISOString()
    mockUseOrderSyncStatus.mockReturnValue({
      data: { last_run_at: twoHoursAgo, stores: [] } as OrderSyncStatus,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)

    renderPage('super_admin')

    const indicator = screen.getByTestId('sync-status-indicator')
    expect(indicator.textContent).toContain('중단되었을 수 있습니다')
    expect(indicator.className).toContain('text-red-700')
  })

  it('last_run_at이 null이면(한 번도 동기화된 적 없음) 알 수 없음/중단 상태로 표시하고 신선한 것으로 표시하지 않는다', () => {
    mockUseOrderSyncStatus.mockReturnValue({
      data: { last_run_at: null, stores: [] } as OrderSyncStatus,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)

    renderPage('super_admin')

    const indicator = screen.getByTestId('sync-status-indicator')
    expect(indicator.textContent).toContain('동기화 기록 없음')
    expect(indicator.textContent).toContain('중단되었을 수 있습니다')
    expect(indicator.className).toContain('text-red-700')
    expect(indicator.textContent).not.toContain('분 전')
  })

  it('데이터가 아직 없으면(로딩 중) 아무것도 렌더링하지 않는다', () => {
    mockUseOrderSyncStatus.mockReturnValue({
      data: undefined,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)

    renderPage('super_admin')

    expect(screen.queryByTestId('sync-status-indicator')).not.toBeInTheDocument()
  })
})
