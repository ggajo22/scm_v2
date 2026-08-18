import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SummaryTab } from './SummaryTab'
import { useRackNumberSummary } from '@/hooks/useRackNumberQueries'
import type { RackNumberSummaryResponse } from '@/services/rackNumberApi'

vi.mock('@/hooks/useRackNumberQueries', () => ({
  useRackNumberSummary: vi.fn(),
}))

function buildResponse(overrides: Partial<RackNumberSummaryResponse> = {}): RackNumberSummaryResponse {
  return {
    groups: [
      {
        rack_number: 'A-1',
        is_unassigned: false,
        total_quantity: 8,
        received_quantity: 3,
        line_items: [
          {
            id: 42,
            order_name: '#1001',
            sku: 'SKU-001',
            title: '테스트 상품 A',
            quantity: 3,
            logistics_status: 'received',
          },
          {
            id: 43,
            order_name: '#1002',
            sku: 'SKU-002',
            title: '테스트 상품 B',
            quantity: 5,
            logistics_status: 'not_shipped',
          },
        ],
      },
      {
        rack_number: '',
        is_unassigned: true,
        total_quantity: 2,
        received_quantity: 1,
        line_items: [
          {
            id: 44,
            order_name: '#1003',
            sku: 'SKU-003',
            title: '테스트 상품 C',
            quantity: 2,
            logistics_status: 'outbound_scheduled',
          },
        ],
      },
    ],
    ...overrides,
  }
}

describe('SummaryTab — SPEC-ORDER-014', () => {
  beforeEach(() => {
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: undefined,
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)
  })

  it('AC-RACKSUM-011/004b: renders each group heading with rack_number and total_quantity, including cross-order groups', () => {
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: buildResponse(),
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)

    expect(screen.getByText('A-1')).toBeInTheDocument()
    expect(screen.getByText(/8/)).toBeInTheDocument()
  })

  it('AC-RACKSUM-011a: renders the unassigned group with the "미지정" label', () => {
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: buildResponse(),
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)

    expect(screen.getByText('미지정')).toBeInTheDocument()
  })

  it('AC-RACKSUM-012: renders order_name/sku/title/quantity/logistics_status for each member LineItem after expanding the group', async () => {
    const user = userEvent.setup()
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: buildResponse(),
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)
    await user.click(screen.getByRole('button', { name: /A-1/ }))

    expect(screen.getByText('#1001')).toBeInTheDocument()
    expect(screen.getByText('SKU-001')).toBeInTheDocument()
    expect(screen.getByText('테스트 상품 A')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('입고')).toBeInTheDocument() // received label

    // Cross-order group member from a different order_name (AC-RACKSUM-004b)
    expect(screen.getByText('#1002')).toBeInTheDocument()
  })

  it('renders "-" for a member LineItem with a null order_name after expanding the group', async () => {
    const user = userEvent.setup()
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: {
        groups: [
          {
            rack_number: 'B-2',
            is_unassigned: false,
            total_quantity: 1,
            line_items: [
              {
                id: 50,
                order_name: null,
                sku: 'SKU-050',
                title: '테스트 상품 D',
                quantity: 1,
                logistics_status: 'not_shipped',
              },
            ],
          },
        ],
      },
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)
    await user.click(screen.getByRole('button', { name: /B-2/ }))

    expect(screen.getByText('-')).toBeInTheDocument()
  })

  it('AC-RACKSUM-013: shows an empty-state message and no table when there are zero groups', () => {
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: { groups: [] },
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)

    expect(screen.getByText('미출고 품목이 없습니다.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('AC-RACKSUM-014/015: renders no checkbox, textbox, or apply button anywhere on the tab, even when expanded', async () => {
    const user = userEvent.setup()
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: buildResponse(),
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)
    await user.click(screen.getByRole('button', { name: /A-1/ }))

    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
    expect(screen.queryAllByRole('textbox')).toHaveLength(0)
    expect(screen.queryByRole('button', { name: '일괄 적용' })).not.toBeInTheDocument()
  })

  it('shows a loading skeleton while the summary request is pending', () => {
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: undefined,
      isPending: true,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)

    expect(screen.getByRole('status', { name: '로딩 중' })).toBeInTheDocument()
  })

  describe('collapse/expand behavior (SPEC-ORDER-014 UX improvement)', () => {
    it('does not render the LineItem table for a group before its header is clicked', () => {
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse(),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)

      expect(screen.queryByText('#1001')).not.toBeInTheDocument()
      expect(screen.queryByText('SKU-001')).not.toBeInTheDocument()
      expect(screen.queryAllByRole('table')).toHaveLength(0)
    })

    it('reveals the LineItem table for a group after clicking its header', async () => {
      const user = userEvent.setup()
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse(),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)
      await user.click(screen.getByRole('button', { name: /A-1/ }))

      expect(screen.getByText('#1001')).toBeInTheDocument()
      expect(screen.getAllByRole('table')).toHaveLength(1)
    })

    it('hides the LineItem table again after clicking the header a second time', async () => {
      const user = userEvent.setup()
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse(),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)
      const header = screen.getByRole('button', { name: /A-1/ })
      await user.click(header)
      expect(screen.getByText('#1001')).toBeInTheDocument()

      await user.click(header)
      expect(screen.queryByText('#1001')).not.toBeInTheDocument()
    })

    it('expanding one group does not expand a different group', async () => {
      const user = userEvent.setup()
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse(),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)
      await user.click(screen.getByRole('button', { name: /A-1/ }))

      expect(screen.getByText('#1001')).toBeInTheDocument()
      // The unassigned group ("미지정") remains collapsed.
      expect(screen.queryByText('#1003')).not.toBeInTheDocument()
    })

    it('always shows the rack_number/label and total_quantity in the header regardless of expand state', async () => {
      const user = userEvent.setup()
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse(),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)

      // Collapsed state: header text is present.
      const header = screen.getByRole('button', { name: /A-1/ })
      expect(header).toHaveTextContent('A-1')
      expect(header).toHaveTextContent('8')

      // Expanded state: header text remains present.
      await user.click(header)
      expect(header).toHaveTextContent('A-1')
      expect(header).toHaveTextContent('8')
    })

    it('group headers are keyboard-accessible buttons with aria-expanded state', async () => {
      const user = userEvent.setup()
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse(),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)
      const header = screen.getByRole('button', { name: /A-1/ })

      expect(header).toHaveAttribute('aria-expanded', 'false')
      await user.click(header)
      expect(header).toHaveAttribute('aria-expanded', 'true')
    })
  })

  describe('SPEC-ORDER-027: received_quantity in group header', () => {
    it('AC-RACKRECV-007: renders the header using received_quantity/total_quantity straight from the API', () => {
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse({
          groups: [
            {
              rack_number: 'A-1',
              is_unassigned: false,
              total_quantity: 5,
              received_quantity: 3,
              line_items: [],
            },
          ],
        }),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)

      const header = screen.getByRole('button', { name: /A-1/ })
      expect(header).toHaveTextContent('입고 3 / 총 5권')
    })

    it('AC-RACKRECV-008: renders "입고 0 / 총 N권" as-is when received_quantity is 0, not hidden', () => {
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse({
          groups: [
            {
              rack_number: 'C-3',
              is_unassigned: false,
              total_quantity: 6,
              received_quantity: 0,
              line_items: [],
            },
          ],
        }),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)

      const header = screen.getByRole('button', { name: /C-3/ })
      expect(header).toHaveTextContent('입고 0 / 총 6권')
    })

    it('AC-RACKRECV-009: renders the unassigned group with the same 입고/총 header format', () => {
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse({
          groups: [
            {
              rack_number: '',
              is_unassigned: true,
              total_quantity: 4,
              received_quantity: 1,
              line_items: [],
            },
          ],
        }),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)

      const header = screen.getByRole('button', { name: /미지정/ })
      expect(header).toHaveTextContent('입고 1 / 총 4권')
    })

    it('AC-RACKRECV-010: header keeps 입고/총 text across collapse/expand transitions', async () => {
      const user = userEvent.setup()
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse({
          groups: [
            {
              rack_number: 'A-1',
              is_unassigned: false,
              total_quantity: 8,
              received_quantity: 3,
              line_items: [],
            },
          ],
        }),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)
      const header = screen.getByRole('button', { name: /A-1/ })

      expect(header).toHaveAttribute('aria-expanded', 'false')
      expect(header).toHaveTextContent('입고 3 / 총 8권')

      await user.click(header)

      expect(header).toHaveAttribute('aria-expanded', 'true')
      expect(header).toHaveTextContent('입고 3 / 총 8권')
    })

    it('AC-RACKRECV-011: the header is a single text node — 입고 stays a single-match literal after expanding', async () => {
      const user = userEvent.setup()
      vi.mocked(useRackNumberSummary).mockReturnValue({
        data: buildResponse({
          groups: [
            {
              rack_number: 'A-1',
              is_unassigned: false,
              total_quantity: 8,
              received_quantity: 3,
              line_items: [
                {
                  id: 42,
                  order_name: '#1001',
                  sku: 'SKU-001',
                  title: '테스트 상품 A',
                  quantity: 3,
                  logistics_status: 'received',
                },
              ],
            },
          ],
        }),
        isPending: false,
      } as unknown as ReturnType<typeof useRackNumberSummary>)

      render(<SummaryTab />)
      await user.click(screen.getByRole('button', { name: /A-1/ }))

      expect(screen.getAllByText('입고', { exact: true })).toHaveLength(1)
    })
  })
})
