import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
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
        line_items: [
          {
            id: 42,
            order_number: 1001,
            sku: 'SKU-001',
            title: '테스트 상품 A',
            quantity: 3,
            logistics_status: 'received',
          },
          {
            id: 43,
            order_number: 1002,
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
        line_items: [
          {
            id: 44,
            order_number: 1003,
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

  it('AC-RACKSUM-012: renders order_number/sku/title/quantity/logistics_status for each member LineItem', () => {
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: buildResponse(),
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)

    expect(screen.getByText('1001')).toBeInTheDocument()
    expect(screen.getByText('SKU-001')).toBeInTheDocument()
    expect(screen.getByText('테스트 상품 A')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('입고')).toBeInTheDocument() // received label

    // Cross-order group member from a different order_number (AC-RACKSUM-004b)
    expect(screen.getByText('1002')).toBeInTheDocument()
  })

  it('renders "-" for a member LineItem with a null order_number', () => {
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
                order_number: null,
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

  it('AC-RACKSUM-014/015: renders no checkbox, textbox, or apply button anywhere on the tab', () => {
    vi.mocked(useRackNumberSummary).mockReturnValue({
      data: buildResponse(),
      isPending: false,
    } as unknown as ReturnType<typeof useRackNumberSummary>)

    render(<SummaryTab />)

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
})
