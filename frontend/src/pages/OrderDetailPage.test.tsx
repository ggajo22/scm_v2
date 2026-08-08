import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { OrderDetailPage } from './OrderDetailPage'
import { useOrderDetail } from '@/features/order/hooks/useOrderDetail'
import { useCreateLineItemNote, useResolveLineItemNote } from '@/features/order/hooks/useLineItemNotes'
import type { OrderDetail } from '@/types/order'

vi.mock('@/features/order/hooks/useOrderDetail', () => ({
  useOrderDetail: vi.fn(),
  ORDER_DETAIL_QUERY_KEY: ['order-detail'],
}))

vi.mock('@/features/order/hooks/useLineItemNotes', () => ({
  useCreateLineItemNote: vi.fn(),
  useResolveLineItemNote: vi.fn(),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/orders/1']}>
        <Routes>
          <Route path="/orders/:id" element={<OrderDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function buildOrderDetail(overrides: Partial<OrderDetail> = {}): OrderDetail {
  return {
    id: 1,
    shopify_order_id: 5001,
    store_type: 'gimssine',
    order_number: 1001,
    name: '#1001',
    email: null,
    phone: null,
    financial_status: 'paid',
    fulfillment_status: 'fulfilled',
    total_price: '30000.00',
    subtotal_price: '30000.00',
    total_tax: '0.00',
    total_discounts: '0.00',
    total_shipping_price_set: null,
    currency: 'KRW',
    gateway: null,
    note: null,
    tags: null,
    cancel_reason: null,
    source_name: null,
    shopify_created_at: '2026-08-01T00:00:00Z',
    shopify_updated_at: null,
    closed_at: null,
    cancelled_at: null,
    processed_at: null,
    has_refund: false,
    margin_amount: null,
    margin_rate: null,
    customer: null,
    shipping_address: null,
    line_items: [
      {
        id: 11,
        shopify_line_item_id: 111,
        title: '테스트 상품',
        variant_title: null,
        sku: 'SKU-1',
        quantity: 1,
        price: '30000.00',
        total_discount: null,
        fulfillment_status: null,
        vendor: null,
        grams: null,
        location: '',
        confirmed_price: null,
        confirmed_distributor: null,
        confirmed_at: null,
        notes: [],
        logistics_status: 'shipment_confirmed',
      },
    ],
    shipping_lines: [],
    refunds: [],
    status: 'shipment_confirmed',
    ...overrides,
  }
}

describe('OrderDetailPage — SPEC-ORDER-011 logistics status badges (AC-LOGI-013)', () => {
  beforeEach(() => {
    vi.mocked(useCreateLineItemNote).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateLineItemNote>)
    vi.mocked(useResolveLineItemNote).mockReturnValue({
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useResolveLineItemNote>)
  })

  it('renders a 물류상태 column badge in the line item table showing the logistics_status label', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    expect(screen.getByText('물류상태')).toBeInTheDocument()
    // shipment_confirmed → 입고예정 (line item badge)
    expect(screen.getAllByText('입고예정').length).toBeGreaterThanOrEqual(1)
  })

  it('renders the Order.status aggregate badge near the fulfillment_status badge', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({ status: 'partial' }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    expect(screen.getByText(/부분입고/)).toBeInTheDocument()
    expect(screen.getByText(/출고완료/)).toBeInTheDocument()
  })

  it('does not render the Order.status badge when status is null', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({ status: null }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    expect(screen.queryByText(/부분입고/)).not.toBeInTheDocument()
  })

  it('AC-LOGI-013: fulfillment_status badge and Order.status badge share no header word and use different background colors', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({ status: 'partial', fulfillment_status: 'fulfilled' }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    const fulfillmentBadge = screen.getByText(/출고완료/)
    const logisticsBadge = screen.getByText(/부분입고/)

    const fulfillmentHeaderWords = new Set(
      (fulfillmentBadge.getAttribute('data-badge-header') ?? '').split(/\s+/).filter(Boolean)
    )
    const logisticsHeaderWords = new Set(
      (logisticsBadge.getAttribute('data-badge-header') ?? '').split(/\s+/).filter(Boolean)
    )

    expect(fulfillmentHeaderWords.size).toBeGreaterThan(0)
    expect(logisticsHeaderWords.size).toBeGreaterThan(0)
    for (const word of logisticsHeaderWords) {
      expect(fulfillmentHeaderWords.has(word)).toBe(false)
    }

    // Background color token must differ (e.g. bg-blue-50 vs bg-purple-50)
    const fulfillmentBg = [...fulfillmentBadge.classList].find((c) => c.startsWith('bg-'))
    const logisticsBg = [...logisticsBadge.classList].find((c) => c.startsWith('bg-'))
    expect(fulfillmentBg).toBeDefined()
    expect(logisticsBg).toBeDefined()
    expect(fulfillmentBg).not.toEqual(logisticsBg)
  })
})
