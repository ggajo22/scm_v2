import type { ComponentProps } from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import {
  UnmatchedForceSection,
  isForceEligible,
  buildForceSelectionKey,
} from './UnmatchedForceSection'
import type { OutboundForceCandidate, OutboundUnmatchedItem } from '@/services/outboundApi'

const REASON_LABELS: Record<string, string> = {
  order_not_found: '주문 없음',
  line_item_not_found: 'SKU 불일치',
  multiple_line_items: '동일 SKU 복수 품목',
  invalid_total: '수량 오류',
  invalid_row: '행 형식 오류',
}

function noop() {}

function renderSection(overrides: Partial<ComponentProps<typeof UnmatchedForceSection>> = {}) {
  return render(
    <UnmatchedForceSection
      items={[]}
      reasonLabels={REASON_LABELS}
      candidatesByOrder={new Map()}
      selectedKeys={new Set()}
      targetByKey={{}}
      onToggleSelect={noop}
      onToggleSelectAll={noop}
      onAssignTarget={noop}
      {...overrides}
    />
  )
}

describe('isForceEligible — SPEC-ORDER-016 REQ-FORCE-001', () => {
  it('is eligible for line_item_not_found with a positive quantity', () => {
    expect(
      isForceEligible({ name: '#1', sku: 'A', total: 4, reason: 'line_item_not_found' })
    ).toBe(true)
  })

  it('rejects line_item_not_found with a zero quantity', () => {
    expect(
      isForceEligible({ name: '#1', sku: 'A', total: 0, reason: 'line_item_not_found' })
    ).toBe(false)
  })

  it('rejects line_item_not_found with a negative quantity', () => {
    expect(
      isForceEligible({ name: '#1', sku: 'A', total: -3, reason: 'line_item_not_found' })
    ).toBe(false)
  })

  it('rejects every other reason code even with a positive quantity', () => {
    const reasons: OutboundUnmatchedItem['reason'][] = [
      'order_not_found',
      'multiple_line_items',
      'invalid_total',
      'invalid_row',
    ]
    for (const reason of reasons) {
      expect(isForceEligible({ name: '#1', sku: 'A', total: 3, reason })).toBe(false)
    }
  })
})

describe('UnmatchedForceSection — AC-FORCE-001: 자격 행에만 컨트롤이 렌더된다', () => {
  const items: OutboundUnmatchedItem[] = [
    { name: '#37349', sku: 'ISBN001', total: 4, reason: 'line_item_not_found' },
    { name: '#37349', sku: 'ISBN002', total: 0, reason: 'line_item_not_found' },
    { name: '#37350', sku: 'ISBN003', total: 3, reason: 'order_not_found' },
    { name: '#37351', sku: 'ISBN004', total: 3, reason: 'multiple_line_items' },
  ]

  it('renders a selection checkbox for the eligible row only', () => {
    renderSection({ items })

    expect(screen.getByLabelText('#37349 ISBN001 선택')).toBeInTheDocument()
    expect(screen.queryByLabelText('#37349 ISBN002 선택')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('#37350 ISBN003 선택')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('#37351 ISBN004 선택')).not.toBeInTheDocument()
  })

  it('renders a target-designation control for the eligible row only', () => {
    renderSection({ items })

    expect(screen.getByLabelText('#37349 ISBN001 대상 지정')).toBeInTheDocument()
    expect(screen.queryByLabelText('#37349 ISBN002 대상 지정')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('#37350 ISBN003 대상 지정')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('#37351 ISBN004 대상 지정')).not.toBeInTheDocument()
  })

  it('invokes onToggleSelectAll from the header "전체 선택" control', () => {
    const onToggleSelectAll = vi.fn()
    renderSection({ items, onToggleSelectAll })

    fireEvent.click(screen.getByLabelText('전체 선택'))

    expect(onToggleSelectAll).toHaveBeenCalledTimes(1)
  })

  it('checks the eligible row when its key is present in selectedKeys', () => {
    const key = buildForceSelectionKey('#37349', 'ISBN001')
    renderSection({ items, selectedKeys: new Set([key]) })

    expect(screen.getByLabelText('#37349 ISBN001 선택')).toBeChecked()
  })
})

describe('UnmatchedForceSection — AC-FORCE-019: 대상 선택 피커 표시 내용', () => {
  it('shows title/sku/ordered/shipped quantity/status for every candidate and marks the full one', () => {
    const items: OutboundUnmatchedItem[] = [
      { name: '#37349', sku: 'ISBN999', total: 2, reason: 'line_item_not_found' },
    ]
    const candidates: OutboundForceCandidate[] = [
      {
        line_item_id: 1,
        title: '도서A',
        sku: 'ISBN001',
        quantity: 10,
        shipped_quantity: 4,
        logistics_status: 'received',
        no_remaining_capacity: false,
      },
      {
        line_item_id: 2,
        title: '도서B',
        sku: 'ISBN002',
        quantity: 5,
        shipped_quantity: 5,
        logistics_status: 'shipped',
        no_remaining_capacity: true,
      },
      {
        line_item_id: 3,
        title: '도서C',
        sku: 'ISBN_003',
        quantity: null,
        shipped_quantity: 0,
        logistics_status: 'not_shipped',
        no_remaining_capacity: true,
      },
    ]

    renderSection({ items, candidatesByOrder: new Map([['#37349', candidates]]) })

    const picker = screen.getByLabelText('#37349 ISBN999 대상 지정')
    const options = within(picker).getAllByRole('option')
    // option[0] is the placeholder "대상 선택"; the remaining three mirror
    // the three candidates in order.
    expect(options).toHaveLength(4)

    expect(options[1].textContent).toContain('도서A')
    expect(options[1].textContent).toContain('ISBN001')
    expect(options[1].textContent).toContain('10')
    expect(options[1].textContent).toContain('4')
    expect(options[1].textContent).not.toContain('잔여 용량 없음')

    // Fully-shipped candidate carries the no-remaining-capacity indicator.
    expect(options[2].textContent).toContain('잔여 용량 없음')
    // NULL-quantity candidate (capacity 0) also carries the indicator.
    expect(options[3].textContent).toContain('잔여 용량 없음')
    expect(options[3].textContent).toContain('ISBN_003')
  })
})

describe('UnmatchedForceSection — AC-FORCE-020: 상태·사유 코드값 미노출, 데이터 값은 원본 유지', () => {
  it('never renders a raw snake_case logistics_status or reason code, but keeps sku/title verbatim', () => {
    const items: OutboundUnmatchedItem[] = [
      { name: '#37349', sku: 'ISBN999', total: 2, reason: 'line_item_not_found' },
    ]
    const candidates: OutboundForceCandidate[] = [
      {
        line_item_id: 1,
        title: '도서_A',
        sku: 'ISBN_WITH_UNDERSCORE',
        quantity: 10,
        shipped_quantity: 4,
        logistics_status: 'not_shipped',
        no_remaining_capacity: false,
      },
    ]

    const { container } = renderSection({
      items,
      candidatesByOrder: new Map([['#37349', candidates]]),
    })

    // Lowercase snake_case codes must never leak — same scan the page-level
    // regression test runs on the whole section (index.test.tsx).
    expect(container.textContent).not.toMatch(/[a-z]+_[a-z_]+/)
    // Data values (sku here) are rendered verbatim, underscore included —
    // it happens to be all-uppercase so it also proves the regex above is
    // scoped to lowercase codes, not data in general.
    expect(container.textContent).toContain('ISBN_WITH_UNDERSCORE')
  })

  it('labels a known logistics_status in Korean', () => {
    const items: OutboundUnmatchedItem[] = [
      { name: '#37349', sku: 'ISBN999', total: 2, reason: 'line_item_not_found' },
    ]
    const candidates: OutboundForceCandidate[] = [
      {
        line_item_id: 1,
        title: '도서',
        sku: 'ISBN001',
        quantity: 10,
        shipped_quantity: 4,
        logistics_status: 'received',
        no_remaining_capacity: false,
      },
    ]

    renderSection({ items, candidatesByOrder: new Map([['#37349', candidates]]) })

    const picker = screen.getByLabelText('#37349 ISBN999 대상 지정')
    expect(within(picker).getByText(/입고/)).toBeInTheDocument()
  })
})

describe('UnmatchedForceSection — 시각적 일관성 (설계 결정 M)', () => {
  it('keeps the outbound-unmatched test hook and renders the section title/count', () => {
    const items: OutboundUnmatchedItem[] = [
      { name: '#37349', sku: 'ISBN001', total: 4, reason: 'line_item_not_found' },
    ]
    renderSection({ items })

    const section = screen.getByTestId('outbound-unmatched')
    expect(within(section).getByText('매칭 실패')).toBeInTheDocument()
    expect(within(section).getByText('1건')).toBeInTheDocument()
  })

  it('shows the empty-state message when there are no unmatched items', () => {
    renderSection({ items: [] })

    expect(screen.getByText('해당 항목이 없습니다.')).toBeInTheDocument()
  })
})
