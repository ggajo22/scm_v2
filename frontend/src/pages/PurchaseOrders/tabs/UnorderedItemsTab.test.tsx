import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnorderedItemsTab } from './UnorderedItemsTab'
import {
  useUnorderedItems,
  useExcludedItems,
  useGenerateOrderFile,
  useUpdateLineItemStatus,
  useBulkUpdateLineItemStatus,
  useConfirmLineItem,
} from '@/hooks/usePurchaseOrderQueries'
import { usePurchaseOrderStore } from '@/stores/usePurchaseOrderStore'

// This factory replaces the whole module, so every hook the component calls
// MUST be listed here (and stubbed in beforeEach below) — omitting one makes
// it `undefined` at call time and breaks every test in this file.
vi.mock('@/hooks/usePurchaseOrderQueries', () => ({
  useUnorderedItems: vi.fn(),
  useExcludedItems: vi.fn(),
  useGenerateOrderFile: vi.fn(),
  useUpdateLineItemStatus: vi.fn(),
  useBulkUpdateLineItemStatus: vi.fn(),
  useConfirmLineItem: vi.fn(),
}))

vi.mock('@/stores/usePurchaseOrderStore', () => ({
  usePurchaseOrderStore: vi.fn(),
}))

describe('UnorderedItemsTab', () => {
  const mutateAsync = vi.fn()
  const bulkMutate = vi.fn()
  const toggleSku = vi.fn()
  const selectAllSkus = vi.fn()
  const clearSelections = vi.fn()
  const confirmMutate = vi.fn()

  beforeEach(() => {
    mutateAsync.mockClear()
    bulkMutate.mockClear()
    toggleSku.mockClear()
    selectAllSkus.mockClear()
    clearSelections.mockClear()
    confirmMutate.mockClear()
    mutateAsync.mockResolvedValue({ unknown_skus: [] })

    vi.mocked(useUnorderedItems).mockReturnValue({
      data: { count: 0, results: [] },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)

    vi.mocked(useExcludedItems).mockReturnValue({
      data: { count: 0, results: [] },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useExcludedItems>)

    vi.mocked(useGenerateOrderFile).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useGenerateOrderFile>)

    vi.mocked(useUpdateLineItemStatus).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateLineItemStatus>)

    vi.mocked(useBulkUpdateLineItemStatus).mockReturnValue({
      mutate: bulkMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useBulkUpdateLineItemStatus>)

    vi.mocked(useConfirmLineItem).mockReturnValue({
      mutate: confirmMutate,
      isPending: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useConfirmLineItem>)

    vi.mocked(usePurchaseOrderStore).mockReturnValue({
      selectedSkus: ['8809226729403'],
      toggleSku,
      selectAllSkus,
      clearSelections,
    } as unknown as ReturnType<typeof usePurchaseOrderStore>)
  })

  it('renders the YES24 order file button after 북센 and 교보 (AC-004)', () => {
    render(<UnorderedItemsTab />)
    const buttons = screen.getAllByRole('button').map((b) => b.textContent)
    const relevantButtons = buttons.filter((label) =>
      ['북센 발주 파일 생성', '교보 발주 파일 생성', 'YES24 발주 파일 생성'].includes(label ?? '')
    )
    expect(relevantButtons).toEqual([
      '북센 발주 파일 생성',
      '교보 발주 파일 생성',
      'YES24 발주 파일 생성',
    ])
  })

  it('calls handleGenerateFile with distributor=yes24 when the YES24 button is clicked (AC-004)', async () => {
    const user = userEvent.setup()
    render(<UnorderedItemsTab />)

    const button = screen.getByRole('button', { name: 'YES24 발주 파일 생성' })
    await user.click(button)

    expect(mutateAsync).toHaveBeenCalledTimes(1)
    expect(mutateAsync).toHaveBeenCalledWith({
      distributor: 'yes24',
      skus: ['8809226729403'],
    })
  })

  // -------------------------------------------------------------------------
  // SPEC-ORDER-018 — 보류/제외 품목 view
  // -------------------------------------------------------------------------

  function optionValues(select: HTMLElement): string[] {
    return Array.from(select.querySelectorAll('option')).map((o) => o.value)
  }

  async function switchToExcludedView(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByRole('button', { name: '보류/제외 품목' }))
  }

  it('T15: a failing unordered query still leaves the excluded view reachable', async () => {
    // plan-audit SPEC-ORDER-018-review-1: the `isError` guard used to sit
    // above the view switcher and early-returned the whole tab, so a failed
    // 미발주 request made the 보류/제외 list unreachable even when its own
    // query had succeeded — defeating the point of this SPEC. Pins the fix.
    const user = userEvent.setup()
    vi.mocked(useUnorderedItems).mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
    } as unknown as ReturnType<typeof useUnorderedItems>)
    vi.mocked(useExcludedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 9001,
            order_name: '#91001',
            sku: 'SKU-901',
            title: '도서 901',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'on_hold',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useExcludedItems>)

    render(<UnorderedItemsTab />)

    // The unordered error is still surfaced...
    expect(screen.getByText('미발주 현황을 불러오는데 실패했습니다.')).toBeInTheDocument()
    // ...but the switcher survives, and the excluded list is still reachable.
    await switchToExcludedView(user)
    expect(screen.getByText('도서 901')).toBeInTheDocument()
  })

  it('T12: switches to the excluded view, shows status labels, and offers unordered in both selects (AC-RESTORE-012)', async () => {
    const user = userEvent.setup()
    vi.mocked(useUnorderedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 1,
            order_name: '#1001',
            sku: '8809226729403',
            title: '미발주 도서',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'unordered',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)
    vi.mocked(useExcludedItems).mockReturnValue({
      data: {
        count: 2,
        results: [
          {
            id: 101,
            order_name: '#2001',
            sku: 'SKU-HOLD',
            title: '보류 도서',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'on_hold',
          },
          {
            id: 202,
            order_name: '#2002',
            sku: 'SKU-CANCEL',
            title: '취소 도서',
            vendor: '처음교육',
            quantity: 2,
            purchase_status: 'order_cancelled',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useExcludedItems>)

    render(<UnorderedItemsTab />)

    // (1) The unordered list is the default view, and its bulk select still
    // withholds `unordered` exactly as before this SPEC.
    expect(screen.getByText('미발주 도서')).toBeInTheDocument()
    expect(screen.queryByText('보류 도서')).not.toBeInTheDocument()
    expect(
      optionValues(screen.getByLabelText('일괄 변경할 발주 상태 선택'))
    ).not.toContain('unordered')

    // (2) After switching, both excluded rows render with their Korean
    // status labels, and `unordered` becomes selectable in both controls.
    await switchToExcludedView(user)

    expect(screen.getByText('보류 도서')).toBeInTheDocument()
    expect(screen.getByText('취소 도서')).toBeInTheDocument()

    // The status label is asserted on the dedicated 제외 사유 cell (index 6),
    // not by a bare text query — every status label also appears as an
    // <option> inside the row's own status select, so an unscoped query
    // would match regardless of whether the column renders.
    const holdRow = screen.getByRole('row', { name: /보류 도서/ })
    expect(within(holdRow).getAllByRole('cell')[6]).toHaveTextContent('주문보류')
    const cancelRow = screen.getByRole('row', { name: /취소 도서/ })
    expect(within(cancelRow).getAllByRole('cell')[6]).toHaveTextContent('주문취소')

    expect(
      optionValues(screen.getByLabelText('보류 도서 발주 상태 변경'))
    ).toContain('unordered')
    expect(
      optionValues(screen.getByLabelText('일괄 변경할 발주 상태 선택'))
    ).toContain('unordered')
  })

  it('T13: bulk restore addresses LineItem ids and never touches the shared SKU selection (AC-RESTORE-013)', async () => {
    const user = userEvent.setup()
    vi.mocked(useExcludedItems).mockReturnValue({
      data: {
        count: 3,
        results: [
          // Two rows share one SKU across different orders — a SKU-keyed
          // selection could not address them independently.
          {
            id: 101,
            order_name: '#3001',
            sku: 'SKU-DUP',
            title: '중복 도서 A',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'on_hold',
          },
          {
            id: 202,
            order_name: '#3002',
            sku: 'SKU-DUP',
            title: '중복 도서 B',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'on_hold',
          },
          {
            id: 303,
            order_name: '#3003',
            sku: 'SKU-OTHER',
            title: '다른 도서',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'cs_required',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useExcludedItems>)

    render(<UnorderedItemsTab />)
    await switchToExcludedView(user)

    await user.click(screen.getByLabelText('중복 도서 A 선택'))
    await user.click(screen.getByLabelText('중복 도서 B 선택'))

    const bulkSelect = screen.getByLabelText('일괄 변경할 발주 상태 선택')
    await user.selectOptions(bulkSelect, 'unordered')
    await user.click(screen.getByRole('button', { name: '일괄 상태 변경' }))

    expect(bulkMutate).toHaveBeenCalledTimes(1)
    const payload = bulkMutate.mock.calls[0][0] as { ids: number[]; purchaseStatus: string }
    expect([...payload.ids].sort((a, b) => a - b)).toEqual([101, 202])
    expect(payload.purchaseStatus).toBe('unordered')

    // The global SKU-keyed selection was never read or written (REQ-RESTORE-019).
    expect(toggleSku).not.toHaveBeenCalled()
    expect(selectAllSkus).not.toHaveBeenCalled()
    expect(clearSelections).not.toHaveBeenCalled()

    // Back on the unordered view, order-file generation still sees only the
    // pre-existing global selection — "SKU-DUP" never leaked in
    // (REQ-RESTORE-020).
    await user.click(screen.getByRole('button', { name: '미발주 품목' }))
    await user.click(screen.getByRole('button', { name: 'YES24 발주 파일 생성' }))
    expect(mutateAsync).toHaveBeenCalledWith({
      distributor: 'yes24',
      skus: ['8809226729403'],
    })
  })

  // -------------------------------------------------------------------------
  // SPEC-PURCHASE-ORDER-011 — damaged_exchange dropdown removal
  // -------------------------------------------------------------------------

  it('does not offer damaged_exchange as a selectable option in the bulk status select (미발주 품목)', () => {
    vi.mocked(useUnorderedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 1,
            order_name: '#1001',
            sku: '8809226729403',
            title: '미발주 도서',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'unordered',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)

    render(<UnorderedItemsTab />)

    expect(
      optionValues(screen.getByLabelText('일괄 변경할 발주 상태 선택'))
    ).not.toContain('damaged_exchange')
  })

  it('renders a row already at damaged_exchange with its Korean label, and the value is not reselectable elsewhere in the options list', async () => {
    vi.mocked(useUnorderedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 5,
            order_name: '#5001',
            sku: 'SKU-DEX',
            title: '파손 도서',
            vendor: '처음교육',
            quantity: 5,
            purchase_status: 'damaged_exchange',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)

    render(<UnorderedItemsTab />)

    const select = screen.getByLabelText('파손 도서 발주 상태 변경') as HTMLSelectElement
    // The row's actual status still renders correctly — not the raw enum
    // string, and not silently coerced to the first option ("미발주").
    expect(select.value).toBe('damaged_exchange')
    const damagedOption = within(select).getByRole('option', { name: '파손/교환' })
    expect(damagedOption).toBeDisabled()

    // Exactly one damaged_exchange <option> exists (the display-only one for
    // this row's current value) — it is not part of the regular selectable
    // list a user could pick after moving away from it.
    const damagedOptionValues = optionValues(select).filter((v) => v === 'damaged_exchange')
    expect(damagedOptionValues).toHaveLength(1)
  })

  it('excluded-view selects never offer damaged_exchange (backend rejects it on the shared status endpoints)', async () => {
    const user = userEvent.setup()
    vi.mocked(useExcludedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 101,
            order_name: '#2001',
            sku: 'SKU-HOLD',
            title: '보류 도서',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'on_hold',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useExcludedItems>)

    render(<UnorderedItemsTab />)
    await switchToExcludedView(user)

    expect(
      optionValues(screen.getByLabelText('보류 도서 발주 상태 변경'))
    ).not.toContain('damaged_exchange')
    expect(
      optionValues(screen.getByLabelText('일괄 변경할 발주 상태 선택'))
    ).not.toContain('damaged_exchange')
  })

  it('none of the four PURCHASE_STATUS_OPTIONS render sites offer other_publisher (REQ-LCONF-304)', async () => {
    const user = userEvent.setup()
    vi.mocked(useUnorderedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 1,
            order_name: '#1001',
            sku: '8809226729403',
            title: '미발주 도서',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'unordered',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)
    vi.mocked(useExcludedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 101,
            order_name: '#2001',
            sku: 'SKU-HOLD',
            title: '보류 도서',
            vendor: '처음교육',
            quantity: 1,
            purchase_status: 'on_hold',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useExcludedItems>)

    render(<UnorderedItemsTab />)

    expect(
      optionValues(screen.getByLabelText('미발주 도서 발주 상태 변경'))
    ).not.toContain('other_publisher')

    await switchToExcludedView(user)
    expect(
      optionValues(screen.getByLabelText('보류 도서 발주 상태 변경'))
    ).not.toContain('other_publisher')
    expect(
      optionValues(screen.getByLabelText('일괄 변경할 발주 상태 선택'))
    ).not.toContain('other_publisher')
  })
})

// -----------------------------------------------------------------------
// SPEC-ORDER-025 R2/M4 — 발주처리 모달 통합
// -----------------------------------------------------------------------

describe('UnorderedItemsTab — 발주처리 모달 (SPEC-ORDER-025)', () => {
  const confirmMutate = vi.fn()

  function mockOneUnorderedRow() {
    vi.mocked(useUnorderedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 42,
            order_name: '#4001',
            sku: 'ISBN-A',
            title: '테스트도서',
            vendor: '처음교육',
            quantity: 5,
            purchase_status: 'unordered',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)
  }

  beforeEach(() => {
    confirmMutate.mockClear()
    mockOneUnorderedRow()
    vi.mocked(useExcludedItems).mockReturnValue({
      data: { count: 0, results: [] },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useExcludedItems>)
    vi.mocked(useGenerateOrderFile).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useGenerateOrderFile>)
    vi.mocked(useUpdateLineItemStatus).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateLineItemStatus>)
    vi.mocked(useBulkUpdateLineItemStatus).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useBulkUpdateLineItemStatus>)
    vi.mocked(useConfirmLineItem).mockReturnValue({
      mutate: confirmMutate,
      isPending: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useConfirmLineItem>)
    vi.mocked(usePurchaseOrderStore).mockReturnValue({
      selectedSkus: [],
      toggleSku: vi.fn(),
      selectAllSkus: vi.fn(),
      clearSelections: vi.fn(),
    } as unknown as ReturnType<typeof usePurchaseOrderStore>)
  })

  // AC-LCONF-206: 8 columns before AND after this SPEC's column swap
  // ("자동 추천 발주처" removed, "발주처리" added).
  it('AC-LCONF-206: table has exactly 8 header columns and empty-state colSpan matches', () => {
    vi.mocked(useUnorderedItems).mockReturnValue({
      data: { count: 0, results: [] },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)

    render(<UnorderedItemsTab />)

    const headers = screen.getAllByRole('columnheader')
    expect(headers).toHaveLength(8)
    expect(screen.queryByText('자동 추천 발주처')).not.toBeInTheDocument()
    expect(screen.getByText('발주처리')).toBeInTheDocument()

    const emptyCell = screen.getByText('미발주 항목이 없습니다.')
    expect(emptyCell.closest('td')).toHaveAttribute('colspan', '8')
  })

  // AC-LCONF-101: clicking 발주처리 opens the modal with the row's info.
  it('AC-LCONF-101: opens the modal and shows title/SKU/quantity', async () => {
    const user = userEvent.setup()
    render(<UnorderedItemsTab />)

    await user.click(screen.getByRole('button', { name: '발주처리' }))

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByText('테스트도서')).toBeInTheDocument()
    expect(within(dialog).getByText('ISBN-A')).toBeInTheDocument()
    expect(within(dialog).getByText('5')).toBeInTheDocument()
  })

  // AC-LCONF-108: a damaged_exchange row's modal must show the same net
  // quantity the unordered list row displayed (backend already nets it to
  // damaged_quantity-based, so the frontend just passes item.quantity
  // through unchanged — see UnorderedItemsView.get() base_qty selection).
  it('AC-LCONF-108: damaged_exchange row modal shows the net (damaged_quantity-based) quantity, not the raw order quantity', async () => {
    vi.mocked(useUnorderedItems).mockReturnValue({
      data: {
        count: 1,
        results: [
          {
            id: 7,
            order_name: '#7001',
            sku: 'SKU-DEX',
            title: '파손 도서',
            vendor: '처음교육',
            // The backend already reports the damaged_quantity-based net
            // quantity (3) here, not the original order quantity (10).
            quantity: 3,
            purchase_status: 'damaged_exchange',
          },
        ],
      },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)

    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))

    const dialog = within(screen.getByRole('dialog'))
    expect(dialog.getByText('3')).toBeInTheDocument()
    expect(dialog.queryByText('10')).not.toBeInTheDocument()
  })

  // AC-LCONF-107: the row's own onClick (SKU selection toggle) must not fire.
  it('AC-LCONF-107: clicking 발주처리 does not toggle the row SKU selection', async () => {
    const toggleSku = vi.fn()
    vi.mocked(usePurchaseOrderStore).mockReturnValue({
      selectedSkus: [],
      toggleSku,
      selectAllSkus: vi.fn(),
      clearSelections: vi.fn(),
    } as unknown as ReturnType<typeof usePurchaseOrderStore>)

    const user = userEvent.setup()
    render(<UnorderedItemsTab />)

    await user.click(screen.getByRole('button', { name: '발주처리' }))

    expect(toggleSku).not.toHaveBeenCalled()
  })

  // AC-LCONF-102/103: whichever control (dropdown vs free text) was touched
  // last wins — both write into the same shared `distributor` value.
  it('AC-LCONF-102: submits the dropdown-selected value when nothing else is touched', async () => {
    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '교보')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(confirmMutate).toHaveBeenCalledTimes(1)
    const [payload] = confirmMutate.mock.calls[0] as [{ id: number; distributor: string; unitPrice: string | null }]
    expect(payload.distributor).toBe('kyobo')
  })

  it('AC-LCONF-103: free-text edits after a dropdown pick win over the dropdown value', async () => {
    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '교보')
    const freeText = dialog.getByLabelText('확정 발주처 직접 입력')
    await user.clear(freeText)
    await user.type(freeText, '특수출판사')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(confirmMutate).toHaveBeenCalledTimes(1)
    const [payload] = confirmMutate.mock.calls[0] as [{ id: number; distributor: string; unitPrice: string | null }]
    expect(payload.distributor).toBe('특수출판사')
  })

  // AC-LCONF-106: blank distributor keeps submit disabled.
  it('AC-LCONF-106: submit button is disabled while distributor is blank', async () => {
    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))

    const submitButton = within(screen.getByRole('dialog')).getByRole('button', { name: '발주처리' })
    expect(submitButton).toBeDisabled()
  })

  // AC-LCONF-105 (component-level): a failed mutation keeps the modal open
  // and renders the server's own error message. The invalidateQueries
  // call-count assertion for this AC lives in
  // usePurchaseOrderQueries.test.tsx, which owns the real hook.
  it('AC-LCONF-105: on failure the modal stays open and shows the server error message', async () => {
    vi.mocked(useConfirmLineItem).mockReturnValue({
      mutate: confirmMutate,
      isPending: false,
      isError: true,
      error: {
        response: { status: 409, data: { error: '이미 발주서에 연결되어 있습니다.' } },
      },
    } as unknown as ReturnType<typeof useConfirmLineItem>)

    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByText('이미 발주서에 연결되어 있습니다.')).toBeInTheDocument()
  })

  // AC-LCONF-104 (component-level): a successful submission closes the
  // modal. The three-key invalidation assertion for this AC lives in
  // usePurchaseOrderQueries.test.tsx (acceptance.md's specified technique).
  it('AC-LCONF-104: on success the modal closes', async () => {
    confirmMutate.mockImplementation((_payload, opts?: { onSuccess?: () => void }) => {
      opts?.onSuccess?.()
    })

    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))
    const dialog = within(screen.getByRole('dialog'))
    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '교보')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  // -------------------------------------------------------------------------
  // SPEC-ORDER-025 M2 — SKU correction at confirm time
  // -------------------------------------------------------------------------

  it('AC-LCONF-SKU: the modal opens with the SKU field prefilled from the row', async () => {
    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))

    const dialog = within(screen.getByRole('dialog'))
    expect(dialog.getByLabelText('SKU 정정 (선택)')).toHaveValue('ISBN-A')
  })

  it('AC-LCONF-SKU: an untouched modal submits a payload with no `sku` key', async () => {
    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '교보')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(confirmMutate).toHaveBeenCalledTimes(1)
    const [payload] = confirmMutate.mock.calls[0] as [Record<string, unknown>]
    expect('sku' in payload).toBe(false)
  })

  it('AC-LCONF-SKU: an edited SKU field submits the new value', async () => {
    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '교보')
    const skuInput = dialog.getByLabelText('SKU 정정 (선택)')
    await user.clear(skuInput)
    await user.type(skuInput, 'ISBN-NEW-EDITION')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(confirmMutate).toHaveBeenCalledTimes(1)
    const [payload] = confirmMutate.mock.calls[0] as [{ sku?: string }]
    expect(payload.sku).toBe('ISBN-NEW-EDITION')
  })

  // 409 collision: the server's SKU-collision-specific message renders (not
  // the generic fallback), and the modal stays open — same mechanism as
  // AC-LCONF-105 above, exercised with the SKU-collision error text.
  it('409 SKU collision: renders the collision-specific message and the modal stays open', async () => {
    vi.mocked(useConfirmLineItem).mockReturnValue({
      mutate: confirmMutate,
      isPending: false,
      isError: true,
      error: {
        response: {
          status: 409,
          data: {
            error:
              "sku 'ISBN-MEMBER-B' is already used by another item in this order — pick a different sku or correct the other item first.",
          },
        },
      },
    } as unknown as ReturnType<typeof useConfirmLineItem>)

    const user = userEvent.setup()
    render(<UnorderedItemsTab />)
    await user.click(screen.getByRole('button', { name: '발주처리' }))

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByRole('alert')).toHaveTextContent(
      "sku 'ISBN-MEMBER-B' is already used by another item in this order"
    )
  })
})
