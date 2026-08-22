import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { OrdersPage } from './OrdersPage'
import { useOrders } from '@/features/order/hooks/useOrders'
import { useOrderSync } from '@/features/order/hooks/useOrderSync'
import { useOrderSyncStatus } from '@/features/order/hooks/useOrderSyncStatus'
import { useAuthStore } from '@/store/authStore'
import type { Order, OrderListResponse, OrderSyncStatus } from '@/types/order'

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

// SPEC-ORDER-023: fixture for the M6 rendering tests below (cancel badge,
// 9-column layout, logistics/purchase/margin cells).
function buildOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: 1,
    shopify_order_id: 5001,
    store_type: 'gimssine',
    order_number: 1001,
    name: '#1001',
    financial_status: 'paid',
    fulfillment_status: 'fulfilled',
    total_price: '30000.00',
    currency: 'KRW',
    shopify_created_at: '2026-08-01T00:00:00Z',
    customer: null,
    has_refund: false,
    line_items_count: 2,
    margin_rate: null,
    logistics_display: null,
    purchase_display: null,
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

describe('OrdersPage — SPEC-ORDER-023 취소 배지', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOrderSync.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useOrderSync>)
    mockUseOrderSyncStatus.mockReturnValue({
      data: undefined,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)
  })

  // AC-OLIST-001
  it('financial_status=refunded 주문에 취소 배지("취소")가 렌더된다', () => {
    const order = buildOrder({ financial_status: 'refunded', has_refund: false })
    mockUseOrders.mockReturnValue({
      data: buildOrderList({ count: 1, results: [order] }),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)

    renderPage('admin')

    const badge = screen.getByTestId('cancel-badge')
    expect(badge).toBeInTheDocument()
    expect(badge.textContent).toBe('취소')
  })

  // AC-OLIST-002
  it('financial_status=partially_refunded 주문에 정확히 "부분취소" 배지가 렌더된다', () => {
    const order = buildOrder({ financial_status: 'partially_refunded', has_refund: true })
    mockUseOrders.mockReturnValue({
      data: buildOrderList({ count: 1, results: [order] }),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)

    renderPage('admin')

    expect(screen.getByTestId('cancel-badge').textContent).toBe('부분취소')
  })

  // AC-OLIST-003
  it('financial_status=paid, has_refund=true ($0 취소) 주문에 "부분취소" 배지가 렌더된다', () => {
    const order = buildOrder({ financial_status: 'paid', has_refund: true })
    mockUseOrders.mockReturnValue({
      data: buildOrderList({ count: 1, results: [order] }),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)

    renderPage('admin')

    expect(screen.getByTestId('cancel-badge').textContent).toBe('부분취소')
  })

  // AC-OLIST-004 (H6): asserting element absence, not just text absence —
  // reusing getDisplayStatus wholesale would render a "결제완료" badge here.
  it('정상 주문(paid, has_refund=false)에는 취소 배지 요소 자체가 없다', () => {
    const order = buildOrder({ financial_status: 'paid', has_refund: false })
    mockUseOrders.mockReturnValue({
      data: buildOrderList({ count: 1, results: [order] }),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)

    renderPage('admin')

    expect(screen.queryByTestId('cancel-badge')).not.toBeInTheDocument()
  })
})

describe('OrdersPage — SPEC-ORDER-023 열 구성 (AC-OLIST-005)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOrderSync.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useOrderSync>)
    mockUseOrderSyncStatus.mockReturnValue({
      data: undefined,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)
    mockUseOrders.mockReturnValue({
      data: buildOrderList(),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)
  })

  it('결제상태/출고상태 열·필터가 제거되고, 9열이 지정된 순서로 렌더되며, 빈 상태 colSpan이 9다', () => {
    renderPage('admin')

    // (a) removed filters and headers
    expect(screen.queryByLabelText('결제 상태 필터')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('출고 상태 필터')).not.toBeInTheDocument()
    expect(screen.queryByText('결제상태')).not.toBeInTheDocument()
    expect(screen.queryByText('출고상태')).not.toBeInTheDocument()

    // (b) header order — getAllByRole returns elements in DOM order, so
    // asserting the text array equals the expected order verifies DOM order.
    const headers = screen.getAllByRole('columnheader')
    expect(headers.map((h) => h.textContent)).toEqual([
      '주문번호',
      '스토어',
      '위치',
      '고객',
      '물류상태',
      '발주상태',
      '마진율',
      '금액',
      '주문일',
    ])

    // (c) empty-state colSpan
    const emptyCell = screen.getByText('주문이 없습니다.').closest('td')
    expect(emptyCell).toHaveAttribute('colspan', '9')
  })
})

describe('OrdersPage — SPEC-ORDER-023 물류상태 필터 (AC-OLIST-026)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOrderSync.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useOrderSync>)
    mockUseOrderSyncStatus.mockReturnValue({
      data: undefined,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)
    mockUseOrders.mockReturnValue({
      data: buildOrderList(),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)
  })

  it('전체 + 6개 값 정확히 7개 옵션이 존재한다', () => {
    renderPage('admin')

    const select = screen.getByLabelText('물류상태 필터')
    const options = within(select).getAllByRole('option')
    expect(options).toHaveLength(7)
    expect(options.map((o) => o.textContent)).toEqual([
      '전체',
      '미입고',
      '입고예정',
      '출고예정',
      '부분출고',
      '출고',
      '부분입고',
    ])
  })

  it('"부분출고" 옵션을 선택하면 다음 요청 파라미터에 logistics_display=partial_shipped가 포함된다', () => {
    renderPage('admin')

    const select = screen.getByLabelText('물류상태 필터')
    fireEvent.change(select, { target: { value: 'partial_shipped' } })

    const lastCallParams = mockUseOrders.mock.calls.at(-1)?.[0]
    expect(lastCallParams).toMatchObject({ logistics_display: 'partial_shipped' })
  })
})

describe('OrdersPage — SPEC-ORDER-023 라벨 렌더링 (AC-OLIST-027)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOrderSync.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useOrderSync>)
    mockUseOrderSyncStatus.mockReturnValue({
      data: undefined,
    } as unknown as ReturnType<typeof useOrderSyncStatus>)
  })

  it('null 값들(logistics_display/purchase_display/margin_rate)은 모두 "-"로 렌더된다', () => {
    const order = buildOrder({
      name: '#NULLROW',
      logistics_display: null,
      purchase_display: null,
      margin_rate: null,
    })
    mockUseOrders.mockReturnValue({
      data: buildOrderList({ count: 1, results: [order] }),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)

    renderPage('admin')

    const row = screen.getByRole('row', { name: /NULLROW/ })
    const cells = within(row).getAllByRole('cell')
    // column order: 주문번호(0)/스토어(1)/위치(2)/고객(3)/물류상태(4)/발주상태(5)/마진율(6)/금액(7)/주문일(8)
    expect(cells[4].textContent).toBe('-')
    expect(cells[5].textContent).toBe('-')
    expect(cells[6].textContent).toBe('-')
  })

  it.each([
    ['not_shipped', '미입고'],
    ['shipment_confirmed', '입고예정'],
    ['outbound_scheduled', '출고예정'],
    ['partial_shipped', '부분출고'],
    ['shipped', '출고'],
    ['partial', '부분입고'],
  ])('logistics_display=%s -> 물류상태 셀에 "%s"가 렌더된다', (value, label) => {
    const order = buildOrder({ name: `#ROW-${value}`, logistics_display: value })
    mockUseOrders.mockReturnValue({
      data: buildOrderList({ count: 1, results: [order] }),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)

    renderPage('admin')

    const row = screen.getByRole('row', { name: new RegExp(`ROW-${value}`) })
    const cells = within(row).getAllByRole('cell')
    expect(cells[4].textContent).toBe(label)
  })

  it('purchase_display=unordered -> "미발주", margin_rate="67.75" -> "67.75%"가 렌더된다', () => {
    const order = buildOrder({
      name: '#PURCHASEROW',
      purchase_display: 'unordered',
      margin_rate: '67.75',
    })
    mockUseOrders.mockReturnValue({
      data: buildOrderList({ count: 1, results: [order] }),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useOrders>)

    renderPage('admin')

    const row = screen.getByRole('row', { name: /PURCHASEROW/ })
    const cells = within(row).getAllByRole('cell')
    expect(cells[5].textContent).toBe('미발주')
    expect(cells[6].textContent).toBe('67.75%')
  })
})
