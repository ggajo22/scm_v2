// Coverage targets: T1~T10 (SPEC-ORDER-020 AC-GROUP-001~010)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { LineItemNotesPage } from './LineItemNotesPage'
import { useUnresolvedLineItemNotes, useResolveLineItemNote } from '@/features/order/hooks/useLineItemNotes'
import type { LineItemNoteUnresolved } from '@/types/order'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/features/order/hooks/useLineItemNotes', () => ({
  LINE_ITEM_NOTES_QUERY_KEY: ['line-item-notes'],
  useUnresolvedLineItemNotes: vi.fn(),
  useResolveLineItemNote: vi.fn(),
  useCreateLineItemNote: vi.fn(),
  useLineItemNotes: vi.fn(),
  downloadLineItemNotesExcel: vi.fn(),
}))

function buildNote(overrides: Partial<LineItemNoteUnresolved>): LineItemNoteUnresolved {
  return {
    id: 0,
    content: '',
    author_username: null,
    assignee: 'CS',
    note_type: '',
    created_at: '2026-08-12T00:00:00Z',
    is_resolved: false,
    line_item_id: 0,
    line_item_sku: null,
    line_item_title: null,
    order_name: null,
    order_id: 0,
    confirmed_distributor: null,
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  // NOTE: build a fresh element tree on each call (not a memoized `ui` reused across renders).
  // Reusing the identical element reference triggers React's referential-equality bailout
  // (oldProps === newProps at the fiber) and skips re-invoking the mocked hooks on rerender.
  const buildTree = () => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LineItemNotesPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
  const utils = render(buildTree())
  return { ...utils, rerenderPage: () => utils.rerender(buildTree()) }
}

function mockNotes(notes: LineItemNoteUnresolved[]) {
  vi.mocked(useUnresolvedLineItemNotes).mockReturnValue({
    data: notes,
    isPending: false,
    isError: false,
  } as ReturnType<typeof useUnresolvedLineItemNotes>)
}

function getGroupContainer(orderId: number) {
  return screen.getByTestId(`order-group-${orderId}`)
}

function queryGroupContainer(orderId: number) {
  return screen.queryByTestId(`order-group-${orderId}`)
}

function getAllGroupContainers() {
  return screen.getAllByTestId(/^order-group-\d+$/)
}

function switchTab(tab: 'CS' | '발주' | '타출판사') {
  fireEvent.click(screen.getByRole('button', { name: new RegExp(`^${tab}\\s*\\(`) }))
}

// Row div carries the fixed "cursor-pointer" class from NoteCard (LineItemNotesPage.tsx:236) — used
// only as a stable, unmodified DOM anchor to scope a resolve-button query to a specific note's row.
function getResolveButtonForContent(container: HTMLElement, content: string) {
  const contentEl = within(container).getByText(content)
  const row = contentEl.closest('.cursor-pointer') as HTMLElement
  return within(row).getByRole('button', { name: '해결' })
}

describe('LineItemNotesPage — SPEC-ORDER-020 order-number grouping', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useResolveLineItemNote).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useResolveLineItemNote>)
  })

  // T1 / AC-GROUP-001
  it('groups notes of the same order into one container with a header and resolve-control counts (AC-GROUP-001)', () => {
    mockNotes([
      buildNote({
        id: 1,
        order_id: 801,
        order_name: '#D801',
        line_item_id: 9201,
        content: '첫 메모',
        created_at: '2026-08-12T10:00:00Z',
        assignee: 'CS',
      }),
      buildNote({
        id: 2,
        order_id: 801,
        order_name: '#D801',
        line_item_id: 9202,
        content: '둘째 메모',
        created_at: '2026-08-12T11:00:00Z',
        assignee: 'CS',
      }),
      buildNote({
        id: 3,
        order_id: 802,
        order_name: '#D802',
        line_item_id: 9203,
        content: '단일 메모',
        created_at: '2026-08-11T09:00:00Z',
        assignee: 'CS',
      }),
    ])

    renderPage()

    const group801 = getGroupContainer(801)
    expect(within(group801).getByText('첫 메모')).toBeInTheDocument()
    expect(within(group801).getByText('둘째 메모')).toBeInTheDocument()
    const header801 = within(group801).getByTestId('order-group-header')
    expect(header801.textContent).toMatch(/#D801/)
    expect(header801.textContent).toMatch(/\(2\)/)

    const group802 = getGroupContainer(802)
    const header802 = within(group802).getByTestId('order-group-header')
    expect(header802.textContent).toMatch(/#D802/)
    expect(header802.textContent).toMatch(/\(1\)/)

    // (d) group-scoped resolve control counts
    expect(within(group801).getAllByRole('button', { name: /해결/ })).toHaveLength(2)
    expect(within(group802).getAllByRole('button', { name: /해결/ })).toHaveLength(1)

    // (e) page-scope resolve control total
    expect(screen.getAllByRole('button', { name: /해결/ })).toHaveLength(3)
  })

  // T2 / AC-GROUP-002
  it('orders groups by their newest note descending (AC-GROUP-002)', () => {
    mockNotes([
      buildNote({ id: 11, order_id: 601, order_name: '#B601', line_item_id: 9301, created_at: '2026-08-10T09:00:00Z', assignee: '발주' }),
      buildNote({ id: 12, order_id: 602, order_name: '#B602', line_item_id: 9302, created_at: '2026-08-12T09:00:00Z', assignee: '발주' }),
      buildNote({ id: 13, order_id: 603, order_name: '#B603', line_item_id: 9303, created_at: '2026-08-11T09:00:00Z', assignee: '발주' }),
    ])

    renderPage()
    switchTab('발주')

    const order = getAllGroupContainers().map((el) => el.getAttribute('data-testid'))
    expect(order).toEqual(['order-group-602', 'order-group-603', 'order-group-601'])
  })

  // T3 / AC-GROUP-003
  it('orders notes within a group with the newest note on top (AC-GROUP-003)', () => {
    mockNotes([
      buildNote({ id: 21, order_id: 701, order_name: '#C701', line_item_id: 9101, content: '먼저 남긴 메모', created_at: '2026-08-10T09:00:00Z', assignee: '발주' }),
      buildNote({ id: 22, order_id: 701, order_name: '#C701', line_item_id: 9102, content: '나중에 남긴 메모', created_at: '2026-08-11T09:00:00Z', assignee: '발주' }),
    ])

    renderPage()
    switchTab('발주')

    const group701 = getGroupContainer(701)
    const text = group701.textContent ?? ''
    expect(text.indexOf('나중에 남긴 메모')).toBeGreaterThanOrEqual(0)
    expect(text.indexOf('먼저 남긴 메모')).toBeGreaterThanOrEqual(0)
    expect(text.indexOf('나중에 남긴 메모')).toBeLessThan(text.indexOf('먼저 남긴 메모'))
  })

  // T4 / AC-GROUP-004
  it('keeps the tab count badge as note count, not group count (AC-GROUP-004)', () => {
    mockNotes([
      buildNote({ id: 61, order_id: 901, order_name: '#E901', line_item_id: 9401, created_at: '2026-08-12T09:00:00Z', assignee: 'CS' }),
      buildNote({ id: 62, order_id: 901, order_name: '#E901', line_item_id: 9402, created_at: '2026-08-12T10:00:00Z', assignee: 'CS' }),
      buildNote({ id: 63, order_id: 902, order_name: '#E902', line_item_id: 9403, created_at: '2026-08-11T09:00:00Z', assignee: 'CS' }),
      buildNote({ id: 64, order_id: 902, order_name: '#E902', line_item_id: 9404, created_at: '2026-08-11T10:00:00Z', assignee: 'CS' }),
    ])

    renderPage()

    const group901 = getGroupContainer(901)
    const group902 = getGroupContainer(902)
    const rowTotal =
      within(group901).getAllByRole('button', { name: /해결/ }).length +
      within(group902).getAllByRole('button', { name: /해결/ }).length
    expect(rowTotal).toBe(4)

    expect(screen.getByRole('button', { name: /^CS\s*\(4\)/ })).toBeInTheDocument()
  })

  // T5 / AC-GROUP-005
  it('navigates each group to its own order and keeps exactly one non-resolve control per group (AC-GROUP-005)', () => {
    mockNotes([
      buildNote({ id: 41, order_id: 1101, order_name: '#G1101', line_item_id: 9601, created_at: '2026-08-12T09:00:00Z', assignee: '발주' }),
      buildNote({ id: 42, order_id: 1102, order_name: '#G1102', line_item_id: 9602, created_at: '2026-08-12T10:00:00Z', assignee: '발주' }),
    ])

    renderPage()
    switchTab('발주')

    const group1101 = getGroupContainer(1101)
    const group1102 = getGroupContainer(1102)

    fireEvent.click(within(group1102).getByRole('button', { name: '#G1102' }))
    fireEvent.click(within(group1101).getByRole('button', { name: '#G1101' }))

    expect(mockNavigate).toHaveBeenNthCalledWith(1, '/orders/1102')
    expect(mockNavigate).toHaveBeenNthCalledWith(2, '/orders/1101')

    const nonResolveIn1101 = within(group1101)
      .getAllByRole('button')
      .filter((btn) => !/해결/.test(btn.textContent ?? ''))
    const nonResolveIn1102 = within(group1102)
      .getAllByRole('button')
      .filter((btn) => !/해결/.test(btn.textContent ?? ''))
    expect(nonResolveIn1101).toHaveLength(1)
    expect(nonResolveIn1102).toHaveLength(1)
  })

  // T6 / AC-GROUP-006
  it('removes only the resolved row, and removes the group when its last note is resolved (AC-GROUP-006)', () => {
    let currentNotes = [
      buildNote({ id: 51, order_id: 1201, order_name: '#H1201', line_item_id: 9701, content: '먼저 해결될 메모', created_at: '2026-08-12T09:00:00Z', assignee: 'CS' }),
      buildNote({ id: 52, order_id: 1201, order_name: '#H1201', line_item_id: 9702, content: '나중에 해결될 메모', created_at: '2026-08-12T10:00:00Z', assignee: 'CS' }),
    ]
    vi.mocked(useUnresolvedLineItemNotes).mockImplementation(
      () =>
        ({
          data: currentNotes,
          isPending: false,
          isError: false,
        }) as ReturnType<typeof useUnresolvedLineItemNotes>,
    )
    const mutate = vi.fn((noteId: number) => {
      currentNotes = currentNotes.filter((n) => n.id !== noteId)
    })
    vi.mocked(useResolveLineItemNote).mockReturnValue({
      mutate,
      isPending: false,
    } as unknown as ReturnType<typeof useResolveLineItemNote>)

    const { rerenderPage } = renderPage()

    // 1st resolve — id=51
    fireEvent.click(getResolveButtonForContent(getGroupContainer(1201), '먼저 해결될 메모'))
    rerenderPage()

    const group1201AfterFirst = getGroupContainer(1201)
    expect(within(group1201AfterFirst).getByText('나중에 해결될 메모')).toBeInTheDocument()
    expect(within(group1201AfterFirst).queryByText('먼저 해결될 메모')).not.toBeInTheDocument()

    // 2nd resolve — id=52 (last remaining note)
    fireEvent.click(getResolveButtonForContent(group1201AfterFirst, '나중에 해결될 메모'))
    rerenderPage()

    expect(queryGroupContainer(1201)).not.toBeInTheDocument()
  })

  // T7 / AC-GROUP-007
  it('renders the existing empty state with no phantom group when a tab has no notes (AC-GROUP-007)', () => {
    mockNotes([
      buildNote({ id: 81, order_id: 1301, order_name: '#I1301', line_item_id: 9801, assignee: 'CS', content: '먼저 남긴 CS 메모', created_at: '2026-08-12T09:00:00Z' }),
      buildNote({ id: 82, order_id: 1301, order_name: '#I1301', line_item_id: 9802, assignee: 'CS', content: '나중에 남긴 CS 메모', created_at: '2026-08-12T10:00:00Z' }),
    ])

    renderPage()

    const group1301 = getGroupContainer(1301)
    const header1301 = within(group1301).getByTestId('order-group-header')
    expect(header1301.textContent).toMatch(/#I1301/)
    expect(header1301.textContent).toMatch(/\(2\)/)

    switchTab('발주')

    expect(screen.getByText('미해결 품목 메모가 없습니다.')).toBeInTheDocument()
    expect(screen.queryAllByTestId(/^order-group-\d+$/)).toHaveLength(0)
  })

  // T8 / AC-GROUP-008
  it('does not pull other-assignee notes into a group on the active tab (AC-GROUP-008)', () => {
    mockNotes([
      buildNote({ id: 31, order_id: 1001, order_name: '#F1001', line_item_id: 9501, assignee: 'CS', content: 'CS 노트', created_at: '2026-08-12T09:00:00Z' }),
      buildNote({ id: 32, order_id: 1001, order_name: '#F1001', line_item_id: 9502, assignee: '발주', content: '발주 노트', created_at: '2026-08-12T10:00:00Z' }),
    ])

    renderPage()

    const group1001 = getGroupContainer(1001)
    const header1001 = within(group1001).getByTestId('order-group-header')
    expect(header1001.textContent).toMatch(/\(1\)/)
    expect(within(group1001).getByText('CS 노트')).toBeInTheDocument()
    expect(within(group1001).queryByText('발주 노트')).not.toBeInTheDocument()
  })

  // T9 / AC-GROUP-009
  it('breaks group-sort created_at ties by id descending (AC-GROUP-009)', () => {
    mockNotes([
      buildNote({ id: 91, order_id: 1602, order_name: '#L1602', line_item_id: 9902, created_at: '2026-08-12T09:00:00Z', assignee: '발주' }),
      buildNote({ id: 92, order_id: 1601, order_name: '#L1601', line_item_id: 9901, created_at: '2026-08-12T09:00:00Z', assignee: '발주' }),
    ])

    renderPage()
    switchTab('발주')

    const order = getAllGroupContainers().map((el) => el.getAttribute('data-testid'))
    expect(order).toEqual(['order-group-1601', 'order-group-1602'])
  })

  // T10 / AC-GROUP-010
  it('breaks intra-group sort created_at ties by id descending (AC-GROUP-010)', () => {
    mockNotes([
      buildNote({ id: 101, order_id: 1701, order_name: '#M1701', line_item_id: 10002, content: '메모 A', created_at: '2026-08-12T09:00:00Z', assignee: '발주' }),
      buildNote({ id: 102, order_id: 1701, order_name: '#M1701', line_item_id: 10001, content: '메모 B', created_at: '2026-08-12T09:00:00Z', assignee: '발주' }),
    ])

    renderPage()
    switchTab('발주')

    const group1701 = getGroupContainer(1701)
    const text = group1701.textContent ?? ''
    expect(text.indexOf('메모 B')).toBeGreaterThanOrEqual(0)
    expect(text.indexOf('메모 A')).toBeGreaterThanOrEqual(0)
    expect(text.indexOf('메모 B')).toBeLessThan(text.indexOf('메모 A'))
  })
})
