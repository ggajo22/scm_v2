import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SearchTab } from './SearchTab'
import { useOrders } from '@/features/order/hooks/useOrders'
import { useOrderDetail } from '@/features/order/hooks/useOrderDetail'
import {
  useUpdateLineItemRackNumber,
  useBulkUpdateLineItemRackNumber,
  useUploadRackNumber,
} from '@/hooks/useRackNumberQueries'
import type { Order, OrderDetail } from '@/types/order'

vi.mock('@/features/order/hooks/useOrders', () => ({
  useOrders: vi.fn(),
}))

vi.mock('@/features/order/hooks/useOrderDetail', () => ({
  useOrderDetail: vi.fn(),
  ORDER_DETAIL_QUERY_KEY: ['order-detail'],
}))

vi.mock('@/hooks/useRackNumberQueries', () => ({
  useUpdateLineItemRackNumber: vi.fn(),
  useBulkUpdateLineItemRackNumber: vi.fn(),
  useUploadRackNumber: vi.fn(),
}))

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
    ...overrides,
  }
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
    confirmed_cost: null,
    total_cost: null,
    customer: null,
    shipping_address: null,
    line_items: [
      {
        id: 11,
        shopify_line_item_id: 111,
        title: '테스트 상품 A',
        variant_title: null,
        sku: 'SKU-A',
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
        logistics_status: 'not_shipped',
        rack_number: 'A-01',
      },
      {
        id: 12,
        shopify_line_item_id: 112,
        title: '테스트 상품 B',
        variant_title: null,
        sku: 'SKU-B',
        quantity: 1,
        price: '10000.00',
        total_discount: null,
        fulfillment_status: null,
        vendor: null,
        grams: null,
        location: '',
        confirmed_price: null,
        confirmed_distributor: null,
        confirmed_at: null,
        notes: [],
        logistics_status: 'not_shipped',
        rack_number: '',
      },
    ],
    shipping_lines: [],
    refunds: [],
    status: 'not_shipped',
    ready_to_ship: null,
    ...overrides,
  }
}

describe('SearchTab — SPEC-ORDER-013', () => {
  const updateMutate = vi.fn()
  const bulkMutate = vi.fn()
  const uploadMutate = vi.fn()

  beforeEach(() => {
    updateMutate.mockClear()
    bulkMutate.mockClear()
    uploadMutate.mockClear()

    vi.mocked(useUpdateLineItemRackNumber).mockReturnValue({
      mutate: updateMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateLineItemRackNumber>)
    vi.mocked(useBulkUpdateLineItemRackNumber).mockReturnValue({
      mutate: bulkMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useBulkUpdateLineItemRackNumber>)
    vi.mocked(useUploadRackNumber).mockReturnValue({
      mutate: uploadMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useUploadRackNumber>)

    // Default: no search submitted yet.
    vi.mocked(useOrders).mockReturnValue({
      data: undefined,
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: undefined,
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)
  })

  function search(value: string) {
    fireEvent.change(screen.getByLabelText('주문번호 검색'), { target: { value } })
    fireEvent.click(screen.getByRole('button', { name: '검색' }))
  }

  it('renders a search input and search button', () => {
    render(<SearchTab />)
    expect(screen.getByLabelText('주문번호 검색')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '검색' })).toBeInTheDocument()
  })

  it('AC-RACK-009: renders a LineItem table with SKU/title/rack_number when an exact order_number match is found', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    expect(screen.getByText('SKU-A')).toBeInTheDocument()
    expect(screen.getByText('테스트 상품 A')).toBeInTheDocument()
    expect(screen.getByDisplayValue('A-01')).toBeInTheDocument()
    expect(screen.getByText('SKU-B')).toBeInTheDocument()
  })

  it('AC-RACK-009a: shows a not-found state and no table when no order_number matches exactly', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 0, next: null, previous: null, results: [] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)

    render(<SearchTab />)
    search('9999')

    expect(screen.getByText('일치하는 주문을 찾을 수 없습니다.')).toBeInTheDocument()
    expect(screen.queryByText('SKU-A')).not.toBeInTheDocument()
  })

  it('결정 C: does not treat a partial name match (non-exact order_number) as a hit', () => {
    // Backend search may OR-match on name; only an exact order_number match counts.
    vi.mocked(useOrders).mockReturnValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [buildOrder({ order_number: 10012, name: '#10012' })],
      },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)

    render(<SearchTab />)
    search('1001')

    expect(screen.getByText('일치하는 주문을 찾을 수 없습니다.')).toBeInTheDocument()
  })

  it('BUGFIX: matches an order by name (no leading #) when order_number does not correlate with the typed search', () => {
    // Real production case: a manually-entered order has name="#EB10011778"
    // but order_number=1778. The backend already OR-matches on name, but the
    // frontend previously discarded this hit by filtering on order_number only.
    vi.mocked(useOrders).mockReturnValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [buildOrder({ order_number: 1778, name: '#EB10011778' })],
      },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('EB10011778')

    expect(screen.getByText('SKU-A')).toBeInTheDocument()
    expect(screen.queryByText('일치하는 주문을 찾을 수 없습니다.')).not.toBeInTheDocument()
  })

  it('BUGFIX: matches an order by name when the typed search includes a leading # (case-insensitive)', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [buildOrder({ order_number: 1778, name: '#EB10011778' })],
      },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('#eb10011778')

    expect(screen.getByText('SKU-A')).toBeInTheDocument()
    expect(screen.queryByText('일치하는 주문을 찾을 수 없습니다.')).not.toBeInTheDocument()
  })

  it('BUGFIX: a search matching neither name nor order_number still shows the not-found state', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [buildOrder({ order_number: 1778, name: '#EB10011778' })],
      },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)

    render(<SearchTab />)
    search('NOMATCH')

    expect(screen.getByText('일치하는 주문을 찾을 수 없습니다.')).toBeInTheDocument()
    expect(screen.queryByText('SKU-A')).not.toBeInTheDocument()
  })

  it('AC-RACK-010: renders one checkbox per row and one header select-all checkbox', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    expect(screen.getByLabelText('전체 선택')).toBeInTheDocument()
    expect(screen.getByLabelText('SKU-A 선택')).toBeInTheDocument()
    expect(screen.getByLabelText('SKU-B 선택')).toBeInTheDocument()
  })

  it('AC-RACK-010b: toggling "select all" checks/unchecks every row', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    const selectAll = screen.getByLabelText('전체 선택') as HTMLInputElement
    fireEvent.click(selectAll)
    expect((screen.getByLabelText('SKU-A 선택') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByLabelText('SKU-B 선택') as HTMLInputElement).checked).toBe(true)

    fireEvent.click(selectAll)
    expect((screen.getByLabelText('SKU-A 선택') as HTMLInputElement).checked).toBe(false)
    expect((screen.getByLabelText('SKU-B 선택') as HTMLInputElement).checked).toBe(false)
  })

  it('AC-RACK-010c: resets row selection when a fresh search is submitted', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    fireEvent.click(screen.getByLabelText('SKU-A 선택'))
    expect((screen.getByLabelText('SKU-A 선택') as HTMLInputElement).checked).toBe(true)

    search('1001')
    expect((screen.getByLabelText('SKU-A 선택') as HTMLInputElement).checked).toBe(false)
  })

  it('AC-RACK-010a: applying a bulk value to checked rows issues exactly one bulk-PATCH and clears selection on success', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)
    bulkMutate.mockImplementation((_payload, opts) => {
      opts?.onSuccess?.({ updated_count: 2, missing_ids: [] })
    })

    render(<SearchTab />)
    search('1001')

    fireEvent.click(screen.getByLabelText('전체 선택'))
    fireEvent.change(screen.getByLabelText('일괄 적용할 렉번호'), { target: { value: 'B-02' } })
    fireEvent.click(screen.getByRole('button', { name: '일괄 적용' }))

    expect(bulkMutate).toHaveBeenCalledTimes(1)
    const [payload] = bulkMutate.mock.calls[0]
    expect(payload).toEqual({ ids: [11, 12], rackNumber: 'B-02' })
    expect((screen.getByLabelText('SKU-A 선택') as HTMLInputElement).checked).toBe(false)
  })

  it('bulk-apply control is disabled unless at least one row is checked', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    expect(screen.queryByRole('button', { name: '일괄 적용' })).not.toBeInTheDocument()
  })

  it('REQ-RACK-011: editing a row inline and blurring submits a single-item PATCH and does not affect other rows', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    const input = screen.getByLabelText('SKU-A 렉번호') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'A-99' } })
    fireEvent.blur(input)

    expect(updateMutate).toHaveBeenCalledTimes(1)
    expect(updateMutate).toHaveBeenCalledWith({ id: 11, rackNumber: 'A-99' })
    expect((screen.getByLabelText('SKU-B 렉번호') as HTMLInputElement).value).toBe('')
  })

  it('REQ-RACK-011: the inline rack_number input enforces maxLength 10', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    expect(screen.getByLabelText('SKU-A 렉번호')).toHaveAttribute('maxLength', '10')
  })

  it('does not re-submit an unchanged inline value on blur', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    const input = screen.getByLabelText('SKU-A 렉번호')
    fireEvent.blur(input)

    expect(updateMutate).not.toHaveBeenCalled()
  })

  it('pressing Enter in the search input submits the search (same as clicking 검색)', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    fireEvent.change(screen.getByLabelText('주문번호 검색'), { target: { value: '1001' } })
    fireEvent.keyDown(screen.getByLabelText('주문번호 검색'), { key: 'Enter' })

    expect(screen.getByText('SKU-A')).toBeInTheDocument()
  })

  it('pressing Enter in an inline rack_number input commits the same as blur', () => {
    vi.mocked(useOrders).mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [buildOrder()] },
      isFetching: false,
    } as unknown as ReturnType<typeof useOrders>)
    vi.mocked(useOrderDetail).mockReturnValue({
      data: buildOrderDetail(),
      isFetching: false,
    } as unknown as ReturnType<typeof useOrderDetail>)

    render(<SearchTab />)
    search('1001')

    const input = screen.getByLabelText('SKU-A 렉번호')
    fireEvent.change(input, { target: { value: 'A-77' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(updateMutate).toHaveBeenCalledWith({ id: 11, rackNumber: 'A-77' })
  })

  it('Excel upload: selecting a file calls uploadRackNumber mutation with FormData', () => {
    const { container } = render(<SearchTab />)
    const file = new File(['dummy'], 'rack.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [file] } })

    expect(uploadMutate).toHaveBeenCalledTimes(1)
    const [formData] = uploadMutate.mock.calls[0]
    expect(formData instanceof FormData).toBe(true)
    expect((formData as FormData).get('file')).toBe(file)
  })
})
