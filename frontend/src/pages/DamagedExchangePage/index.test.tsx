import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DamagedExchangePage } from './index'
import {
  useSearchDamagedExchange,
  useSubmitDamagedExchange,
} from '@/hooks/useDamagedExchangeQueries'
import type { DamagedExchangeSearchResultRow } from '@/services/damagedExchangeApi'

// SPEC-PURCHASE-ORDER-011 AC-DEX-002: this page module must not import
// OutboundPage/RackNumberPage or outboundApi/rackNumberApi/
// useOutboundQueries/useRackNumberQueries — enforced here by only mocking
// its own hook module. If DamagedExchangePage's source ever imported one of
// those modules, this test file's mock setup below would not cover it and
// the suite would fail at collection time with a missing-module/real-network
// error rather than silently passing.
vi.mock('@/hooks/useDamagedExchangeQueries', () => ({
  useSearchDamagedExchange: vi.fn(),
  useSubmitDamagedExchange: vi.fn(),
}))

const mockUseSearch = vi.mocked(useSearchDamagedExchange)
const mockUseSubmit = vi.mocked(useSubmitDamagedExchange)

function buildRow(
  overrides: Partial<DamagedExchangeSearchResultRow> = {}
): DamagedExchangeSearchResultRow {
  return {
    id: 1,
    order_name: '#1001',
    sku: '9788956609959',
    title: '테스트 도서',
    rack_number: 'A-01',
    quantity: 4,
    purchase_status: 'unordered',
    is_damaged_exchange: false,
    order_ready_to_ship: true,
    order_total_quantity: 13,
    ...overrides,
  }
}

async function search(user: ReturnType<typeof userEvent.setup>, sku: string) {
  await user.type(screen.getByLabelText('ISBN 검색'), sku)
  await user.click(screen.getByRole('button', { name: '검색' }))
}

describe('DamagedExchangePage — SPEC-PURCHASE-ORDER-011', () => {
  const submitMutate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseSubmit.mockReturnValue({
      mutate: submitMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useSubmitDamagedExchange>)
    mockUseSearch.mockReturnValue({
      data: undefined,
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)
  })

  it('렉번호 컬럼: renders the stored rack_number for a matched row', async () => {
    const user = userEvent.setup()
    mockUseSearch.mockReturnValue({
      data: { count: 1, results: [buildRow({ rack_number: 'B-12' })] },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)

    render(<DamagedExchangePage />)
    await search(user, '9788956609959')

    expect(screen.getByRole('columnheader', { name: '렉번호' })).toBeInTheDocument()
    // Asserts the stored value, not the fallback — an implementation that
    // always rendered '미지정' would pass a mere "column exists" check.
    expect(screen.getByRole('row', { name: /테스트 도서/ })).toHaveTextContent('B-12')
    expect(screen.queryByText('미지정')).not.toBeInTheDocument()
  })

  it('렉번호 컬럼: renders 미지정 when rack_number is the empty unassigned value', async () => {
    const user = userEvent.setup()
    mockUseSearch.mockReturnValue({
      data: { count: 1, results: [buildRow({ rack_number: '' })] },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)

    render(<DamagedExchangePage />)
    await search(user, '9788956609959')

    // Empty string is the unassigned bucket — must show '미지정', not blank
    // and not the '-' used by other nullable columns on this page.
    expect(screen.getByRole('row', { name: /테스트 도서/ })).toHaveTextContent('미지정')
  })

  it('시나리오 2: renders the ISBN search form with no result table before any search', () => {
    render(<DamagedExchangePage />)

    expect(screen.getByLabelText('ISBN 검색')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '검색' })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('AC-DEX-006/REQ-DEX-006: renders 주문번호/주문 수량/전체 출고 수량 for a matched row', async () => {
    const user = userEvent.setup()
    mockUseSearch.mockReturnValue({
      data: { count: 1, results: [buildRow({ quantity: 4, order_total_quantity: 13 })] },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)

    render(<DamagedExchangePage />)
    await search(user, '9788956609959')

    const row = screen.getByRole('row', { name: /테스트 도서/ })
    expect(row).toHaveTextContent('#1001')
    expect(row).toHaveTextContent('4')
    expect(row).toHaveTextContent('13')
  })

  it('시나리오 4b/AC-DEX-004a: rows already at damaged_exchange render a distinguishing badge, other rows do not', async () => {
    const user = userEvent.setup()
    mockUseSearch.mockReturnValue({
      data: {
        count: 2,
        results: [
          buildRow({ id: 1, title: '일반 품목', is_damaged_exchange: false }),
          buildRow({ id: 2, title: '접수된 품목', is_damaged_exchange: true }),
        ],
      },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)

    render(<DamagedExchangePage />)
    await search(user, '9788956609959')

    const normalRow = screen.getByRole('row', { name: /일반 품목/ })
    const damagedRow = screen.getByRole('row', { name: /접수된 품목/ })
    expect(normalRow).not.toHaveTextContent('파손/교환 접수됨')
    expect(damagedRow).toHaveTextContent('파손/교환 접수됨')
  })

  it('시나리오 5a/AC-DEX-005a: renders true/false/null 오늘 출고 가능 여부 distinctly — null is never coerced to false', async () => {
    const user = userEvent.setup()
    mockUseSearch.mockReturnValue({
      data: {
        count: 3,
        results: [
          buildRow({ id: 1, title: '가능 품목', order_ready_to_ship: true }),
          buildRow({ id: 2, title: '불가 품목', order_ready_to_ship: false }),
          buildRow({ id: 3, title: '미확정 품목', order_ready_to_ship: null }),
        ],
      },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)

    render(<DamagedExchangePage />)
    await search(user, '9788956609959')

    expect(screen.getByRole('row', { name: /가능 품목/ })).toHaveTextContent('출고가능')
    expect(screen.getByRole('row', { name: /불가 품목/ })).toHaveTextContent('출고불가')
    const nullRow = screen.getByRole('row', { name: /미확정 품목/ })
    expect(nullRow).toHaveTextContent('미확정')
    // The null row must not also render the false-case label.
    expect(nullRow).not.toHaveTextContent('출고불가')
  })

  it('AC-DEX-007: an empty result set shows a not-found message rather than a table', async () => {
    const user = userEvent.setup()
    mockUseSearch.mockReturnValue({
      data: { count: 0, results: [] },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)

    render(<DamagedExchangePage />)
    await search(user, '0000000000000')

    expect(screen.getByText('일치하는 품목을 찾을 수 없습니다.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('시나리오 8/AC-DEX-008: damage quantity input defaults to 1 and disables submit outside 1..quantity', async () => {
    const user = userEvent.setup()
    mockUseSearch.mockReturnValue({
      data: { count: 1, results: [buildRow({ id: 7, sku: 'SKU-7', quantity: 5 })] },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)

    render(<DamagedExchangePage />)
    await search(user, 'SKU-7')

    const qtyInput = screen.getByLabelText('SKU-7 파손 수량') as HTMLInputElement
    const submitButton = screen.getByRole('button', { name: '접수' })

    expect(qtyInput.value).toBe('1')
    expect(submitButton).toBeEnabled()

    await user.clear(qtyInput)
    await user.type(qtyInput, '6')
    expect(submitButton).toBeDisabled()

    await user.clear(qtyInput)
    await user.type(qtyInput, '3')
    expect(submitButton).toBeEnabled()

    await user.click(submitButton)
    expect(submitMutate).toHaveBeenCalledTimes(1)
    expect(submitMutate).toHaveBeenCalledWith({ id: 7, damagedQuantity: 3 })
  })

  it('시나리오 9b: resubmitting for an already-damaged row still submits (server overwrites, not accumulates)', async () => {
    const user = userEvent.setup()
    mockUseSearch.mockReturnValue({
      data: {
        count: 1,
        results: [
          buildRow({
            id: 9,
            sku: 'SKU-9',
            quantity: 8,
            purchase_status: 'damaged_exchange',
            is_damaged_exchange: true,
          }),
        ],
      },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof useSearchDamagedExchange>)

    render(<DamagedExchangePage />)
    await search(user, 'SKU-9')

    const qtyInput = screen.getByLabelText('SKU-9 파손 수량') as HTMLInputElement
    await user.clear(qtyInput)
    await user.type(qtyInput, '2')
    await user.click(screen.getByRole('button', { name: '접수' }))

    expect(submitMutate).toHaveBeenCalledWith({ id: 9, damagedQuantity: 2 })
  })
})
