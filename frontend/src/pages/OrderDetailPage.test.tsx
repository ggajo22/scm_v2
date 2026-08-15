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
    shipping_cost: null,
    korea_warehouse_cost: null,
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
        rack_number: '',
      },
    ],
    shipping_lines: [],
    refunds: [],
    status: 'shipment_confirmed',
    ready_to_ship: null,
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

describe('OrderDetailPage — SPEC-ORDER-012 ready_to_ship badge (AC-RTS-007/008)', () => {
  beforeEach(() => {
    vi.mocked(useCreateLineItemNote).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateLineItemNote>)
    vi.mocked(useResolveLineItemNote).mockReturnValue({
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useResolveLineItemNote>)
  })

  it('renders the 출고가능 badge when ready_to_ship is true', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({ ready_to_ship: true }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    const badge = screen.getByText('출고가능')
    expect(badge).toBeInTheDocument()
    expect(badge.getAttribute('data-badge-header')).toBe('출고가능')
    expect([...badge.classList]).toContain('bg-emerald-50')
    expect(screen.queryByText('출고불가')).not.toBeInTheDocument()
  })

  it('renders a distinct 출고불가 badge when ready_to_ship is false (결정 F)', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({ ready_to_ship: false }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    const badge = screen.getByText('출고불가')
    expect(badge).toBeInTheDocument()
    expect(badge.getAttribute('data-badge-header')).toBe('출고불가')
    expect([...badge.classList]).toContain('bg-red-50')
    expect(screen.queryByText('출고가능')).not.toBeInTheDocument()
  })

  it('renders neither ready_to_ship badge when ready_to_ship is null', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({ ready_to_ship: null }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    expect(screen.queryByText('출고가능')).not.toBeInTheDocument()
    expect(screen.queryByText('출고불가')).not.toBeInTheDocument()
  })

  it('AC-RTS-007: all four badges (true/false ready_to_ship variants included) share no header word and use distinct background colors', () => {
    const headerWords = (el: HTMLElement) =>
      new Set((el.getAttribute('data-badge-header') ?? '').split(/\s+/).filter(Boolean))
    const bgClass = (el: HTMLElement) => [...el.classList].find((c) => c.startsWith('bg-'))

    // true-state pass: 출고가능 vs fulfillment_status vs status
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({
        ready_to_ship: true,
        status: 'partial',
        fulfillment_status: 'fulfilled',
      }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    const { unmount } = renderPage()

    let fulfillmentBadge = screen.getByText(/출고완료/)
    let statusBadge = screen.getByText(/부분입고/)
    const readyBadge = screen.getByText('출고가능')

    let fulfillmentWords = headerWords(fulfillmentBadge)
    let statusWords = headerWords(statusBadge)
    const readyWords = headerWords(readyBadge)

    expect(readyWords.size).toBeGreaterThan(0)
    for (const word of readyWords) {
      expect(fulfillmentWords.has(word)).toBe(false)
      expect(statusWords.has(word)).toBe(false)
    }

    let fulfillmentBg = bgClass(fulfillmentBadge)
    let statusBg = bgClass(statusBadge)
    const readyBg = bgClass(readyBadge)

    expect(readyBg).toBeDefined()
    expect(readyBg).not.toEqual(fulfillmentBg)
    expect(readyBg).not.toEqual(statusBg)

    unmount()

    // false-state pass: 출고불가 vs fulfillment_status vs status
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({
        ready_to_ship: false,
        status: 'partial',
        fulfillment_status: 'fulfilled',
      }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    fulfillmentBadge = screen.getByText(/출고완료/)
    statusBadge = screen.getByText(/부분입고/)
    const notReadyBadge = screen.getByText('출고불가')

    fulfillmentWords = headerWords(fulfillmentBadge)
    statusWords = headerWords(statusBadge)
    const notReadyWords = headerWords(notReadyBadge)

    expect(notReadyWords.size).toBeGreaterThan(0)
    for (const word of notReadyWords) {
      expect(fulfillmentWords.has(word)).toBe(false)
      expect(statusWords.has(word)).toBe(false)
    }

    fulfillmentBg = bgClass(fulfillmentBadge)
    statusBg = bgClass(statusBadge)
    const notReadyBg = bgClass(notReadyBadge)

    expect(notReadyBg).toBeDefined()
    expect(notReadyBg).not.toEqual(fulfillmentBg)
    expect(notReadyBg).not.toEqual(statusBg)
    // true-state and false-state ready_to_ship badges must also differ from
    // each other in both header word and background color.
    expect(notReadyWords.has('출고가능')).toBe(false)
    expect(notReadyBg).not.toEqual(readyBg)
  })
})

// SPEC-ORDER-013 REQ-RACK-012/AC-RACK-012: rack_number is exposed on the
// shared LineItemDetail API response (consumed by RackNumberPage), but
// OrderDetailPage must never render or allow editing it.
describe('OrderDetailPage — SPEC-ORDER-013 rack_number exclusion (REQ-RACK-012)', () => {
  beforeEach(() => {
    vi.mocked(useCreateLineItemNote).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateLineItemNote>)
    vi.mocked(useResolveLineItemNote).mockReturnValue({
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useResolveLineItemNote>)
  })

  it('does not render any rack_number field, label, input, or badge even when the API response includes a non-empty value', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({
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
            rack_number: 'RACK-Z9',
          },
        ],
      }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    expect(screen.queryByText('RACK-Z9')).not.toBeInTheDocument()
    expect(screen.queryByText(/렉번호/)).not.toBeInTheDocument()
    expect(screen.queryByDisplayValue('RACK-Z9')).not.toBeInTheDocument()
  })
})

describe('OrderDetailPage — SPEC-ORDER-021 shipping/Korea-warehouse cost display (AC-COST-011)', () => {
  beforeEach(() => {
    vi.mocked(useCreateLineItemNote).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateLineItemNote>)
    vi.mocked(useResolveLineItemNote).mockReturnValue({
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useResolveLineItemNote>)
  })

  it('displays shipping_cost and korea_warehouse_cost next to margin_amount/margin_rate', () => {
    // Values match AC-COST-003's fixture shape. shipping_cost intentionally
    // uses "8.18" (not "0.00") — Number("0.00").toLocaleString() === "0",
    // which would render "0 USD" and make this assertion fail even against a
    // correct implementation (audit D3).
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({
        margin_amount: '159.58',
        margin_rate: '79.79',
        shipping_cost: '8.18',
        korea_warehouse_cost: '2.25',
      }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    expect(screen.getByText(/8\.18 USD/)).toBeInTheDocument()
    expect(screen.getByText(/2\.25 USD/)).toBeInTheDocument()
  })

  it('falls back to "—" when shipping_cost and korea_warehouse_cost are null', () => {
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail({
        shipping_cost: null,
        korea_warehouse_cost: null,
      }),
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useOrderDetail>)

    renderPage()

    // Scope to each label's own row so this does not coincidentally pass
    // against pre-existing unrelated "—" fallbacks (e.g. confirmed_price).
    const shippingRow = screen.getByText('배송비').closest('div')
    const warehouseRow = screen.getByText('한국창고비').closest('div')
    expect(shippingRow?.textContent).toContain('—')
    expect(warehouseRow?.textContent).toContain('—')
  })
})
