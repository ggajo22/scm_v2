import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnorderedItemsTab } from './UnorderedItemsTab'
import {
  useUnorderedItems,
  useGenerateOrderFile,
  useUpdateLineItemStatus,
  useBulkUpdateLineItemStatus,
} from '@/hooks/usePurchaseOrderQueries'
import { usePurchaseOrderStore } from '@/stores/usePurchaseOrderStore'

vi.mock('@/hooks/usePurchaseOrderQueries', () => ({
  useUnorderedItems: vi.fn(),
  useGenerateOrderFile: vi.fn(),
  useUpdateLineItemStatus: vi.fn(),
  useBulkUpdateLineItemStatus: vi.fn(),
}))

vi.mock('@/stores/usePurchaseOrderStore', () => ({
  usePurchaseOrderStore: vi.fn(),
}))

describe('UnorderedItemsTab', () => {
  const mutateAsync = vi.fn()

  beforeEach(() => {
    mutateAsync.mockClear()
    mutateAsync.mockResolvedValue({ unknown_skus: [] })

    vi.mocked(useUnorderedItems).mockReturnValue({
      data: { count: 0, results: [] },
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useUnorderedItems>)

    vi.mocked(useGenerateOrderFile).mockReturnValue({
      mutateAsync,
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

    vi.mocked(usePurchaseOrderStore).mockReturnValue({
      selectedSkus: ['8809226729403'],
      toggleSku: vi.fn(),
      selectAllSkus: vi.fn(),
      clearSelections: vi.fn(),
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
})
