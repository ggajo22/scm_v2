import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { OutboundPage } from './index'
import {
  useProcessOutboundManual,
  useUploadOutbound,
  useOutboundForceCandidates,
  useProcessOutboundForce,
} from '@/hooks/useOutboundQueries'
import type {
  OutboundProcessResponse,
  OutboundForceCandidateGroup,
  OutboundForceRowInput,
} from '@/services/outboundApi'

vi.mock('@/hooks/useOutboundQueries', () => ({
  useProcessOutboundManual: vi.fn(),
  useUploadOutbound: vi.fn(),
  useOutboundForceCandidates: vi.fn(),
  useProcessOutboundForce: vi.fn(),
}))

const mockUseProcess = vi.mocked(useProcessOutboundManual)
const mockUseUpload = vi.mocked(useUploadOutbound)
const mockUseForceCandidates = vi.mocked(useOutboundForceCandidates)
const mockUseProcessForce = vi.mocked(useProcessOutboundForce)

function buildResponse(
  overrides: Partial<OutboundProcessResponse> = {}
): OutboundProcessResponse {
  return {
    matched: [
      {
        name: '#37349',
        sku: 'ISBN001',
        total: 4,
        line_item_id: 11,
        shipped_quantity: 4,
        quantity: 10,
        logistics_status: 'received',
      },
    ],
    matched_count: 1,
    unmatched: [
      { name: '#99999', sku: 'ISBN001', total: 3, reason: 'order_not_found' },
      { name: '#37349', sku: 'ISBN999', total: 2, reason: 'line_item_not_found' },
      { name: '#37350', sku: 'ISBN003', total: 1, reason: 'multiple_line_items' },
      // Added by the backend fix cycle (per-row validation).
      { name: '#37351', sku: 'ISBN004', total: -5, reason: 'invalid_total' },
      { name: '', sku: '', total: 0, reason: 'invalid_row' },
    ],
    unmatched_count: 5,
    quantity_exceeded: [
      {
        name: '#37349',
        sku: 'ISBN002',
        total: 5,
        line_item_id: 12,
        shipped_quantity: 8,
        quantity: 10,
        reason: 'quantity_exceeded',
      },
    ],
    quantity_exceeded_count: 1,
    ...overrides,
  }
}

// The page drives both mutations with mutate(vars, { onSuccess }); these mocks
// invoke that callback synchronously so result rendering can be asserted.
//
// SPEC-ORDER-016: `forceOptions.candidates` seeds the mocked candidate query
// (keyed by whatever order names the page requests) and `forceOptions.forceResponse`
// seeds the force-execute mutation's onSuccess callback, mirroring how
// `response` seeds the two pre-existing mutations above.
function setupMutations(
  response: OutboundProcessResponse | null = null,
  forceOptions: {
    candidates?: OutboundForceCandidateGroup[]
    forceResponse?: OutboundProcessResponse
  } = {}
) {
  const processMutate = vi.fn((_vars: unknown, opts?: { onSuccess?: (r: OutboundProcessResponse) => void }) => {
    if (response) opts?.onSuccess?.(response)
  })
  const uploadMutate = vi.fn(
    (
      _vars: unknown,
      opts?: { onSuccess?: (r: OutboundProcessResponse) => void; onSettled?: () => void }
    ) => {
      if (response) opts?.onSuccess?.(response)
      opts?.onSettled?.()
    }
  )
  const forceMutate = vi.fn(
    (
      _vars: OutboundForceRowInput[],
      opts?: { onSuccess?: (r: OutboundProcessResponse) => void }
    ) => {
      if (forceOptions.forceResponse) opts?.onSuccess?.(forceOptions.forceResponse)
    }
  )
  mockUseProcess.mockReturnValue({ mutate: processMutate, isPending: false } as never)
  mockUseUpload.mockReturnValue({ mutate: uploadMutate, isPending: false } as never)
  mockUseProcessForce.mockReturnValue({ mutate: forceMutate, isPending: false } as never)
  mockUseForceCandidates.mockReturnValue({
    data: forceOptions.candidates ?? [],
    isLoading: false,
  } as never)
  return { processMutate, uploadMutate, forceMutate }
}

describe('OutboundPage — SPEC-ORDER-015', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('AC-OUTBOUND-018: 수동 입력 폼 + Excel 업로드 컨트롤 동시 노출', () => {
    it('renders both the manual entry textarea and the Excel upload control on first paint', () => {
      setupMutations()
      render(<OutboundPage />)

      expect(screen.getByRole('textbox', { name: '출고 처리 행 입력' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Excel 업로드' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '출고 처리 실행' })).toBeInTheDocument()
    })

    it('shows no result sections before any request has completed', () => {
      setupMutations()
      render(<OutboundPage />)

      expect(screen.queryByTestId('outbound-matched')).not.toBeInTheDocument()
      expect(screen.queryByTestId('outbound-unmatched')).not.toBeInTheDocument()
      expect(screen.queryByTestId('outbound-quantity-exceeded')).not.toBeInTheDocument()
    })
  })

  describe('AC-OUTBOUND-018 (manual submit): 수동 입력 제출', () => {
    it('submits the parsed rows through the manual-entry mutation', () => {
      const { processMutate } = setupMutations()
      render(<OutboundPage />)

      fireEvent.change(screen.getByRole('textbox', { name: '출고 처리 행 입력' }), {
        target: { value: '#37349\tISBN001\t4\n#37350\tISBN002\t1' },
      })
      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))

      expect(processMutate).toHaveBeenCalledTimes(1)
      expect(processMutate.mock.calls[0][0]).toEqual([
        { name: '#37349', sku: 'ISBN001', total: 4 },
        { name: '#37350', sku: 'ISBN002', total: 1 },
      ])
    })

    it('does not fire a request when the textarea has no parseable row', () => {
      const { processMutate } = setupMutations()
      render(<OutboundPage />)

      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))

      expect(processMutate).not.toHaveBeenCalled()
    })
  })

  describe('AC-OUTBOUND-018 (upload): Excel 업로드', () => {
    it('sends the chosen file as FormData through the upload mutation', () => {
      const { uploadMutate } = setupMutations()
      render(<OutboundPage />)

      const file = new File(['x'], 'outbound.xlsx')
      fireEvent.change(screen.getByLabelText('Excel 파일 선택'), {
        target: { files: [file] },
      })

      expect(uploadMutate).toHaveBeenCalledTimes(1)
      const formData = uploadMutate.mock.calls[0][0] as FormData
      expect(formData).toBeInstanceOf(FormData)
      expect(formData.get('file')).toBe(file)
    })

    it('does not fire a request when the file dialog is dismissed with no file', () => {
      const { uploadMutate } = setupMutations()
      render(<OutboundPage />)

      fireEvent.change(screen.getByLabelText('Excel 파일 선택'), { target: { files: [] } })

      expect(uploadMutate).not.toHaveBeenCalled()
    })
  })

  describe('AC-OUTBOUND-019: 결과 3섹션 시각화', () => {
    function renderWithResult() {
      setupMutations(buildResponse())
      render(<OutboundPage />)
      fireEvent.change(screen.getByRole('textbox', { name: '출고 처리 행 입력' }), {
        target: { value: '#37349\tISBN001\t4' },
      })
      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))
    }

    it('renders three distinct result sections after a completed request', () => {
      renderWithResult()

      expect(screen.getByTestId('outbound-matched')).toBeInTheDocument()
      expect(screen.getByTestId('outbound-unmatched')).toBeInTheDocument()
      expect(screen.getByTestId('outbound-quantity-exceeded')).toBeInTheDocument()
    })

    it('renders 매칭 실패 above 성공 so failures need no scrolling', () => {
      renderWithResult()

      const unmatched = screen.getByTestId('outbound-unmatched')
      const matched = screen.getByTestId('outbound-matched')

      expect(unmatched.compareDocumentPosition(matched)).toBe(
        Node.DOCUMENT_POSITION_FOLLOWING
      )
    })

    it('shows each section count from the response', () => {
      renderWithResult()

      expect(within(screen.getByTestId('outbound-matched')).getByText(/1건/)).toBeInTheDocument()
      expect(within(screen.getByTestId('outbound-unmatched')).getByText(/5건/)).toBeInTheDocument()
      expect(
        within(screen.getByTestId('outbound-quantity-exceeded')).getByText(/1건/)
      ).toBeInTheDocument()
    })

    it('lists the matched item with its order name and sku', () => {
      renderWithResult()

      const section = within(screen.getByTestId('outbound-matched'))
      expect(section.getByText('#37349')).toBeInTheDocument()
      expect(section.getByText('ISBN001')).toBeInTheDocument()
    })

    it('lists every unmatched item with a human-readable reason per item', () => {
      renderWithResult()

      const section = within(screen.getByTestId('outbound-unmatched'))
      expect(section.getByText('주문 없음')).toBeInTheDocument()
      expect(section.getByText('SKU 불일치')).toBeInTheDocument()
      expect(section.getByText('동일 SKU 복수 품목')).toBeInTheDocument()
    })

    // The backend fix cycle expanded the reason codes from 3 to 5. Without a
    // label entry the `?? item.reason` fallback leaks the raw snake_case code
    // into the UI, which the other three reasons never do.
    it('labels invalid_total in Korean rather than leaking the raw reason code', () => {
      renderWithResult()

      const section = within(screen.getByTestId('outbound-unmatched'))
      expect(section.getByText('수량 오류')).toBeInTheDocument()
      expect(section.queryByText('invalid_total')).not.toBeInTheDocument()
    })

    it('labels invalid_row in Korean rather than leaking the raw reason code', () => {
      renderWithResult()

      const section = within(screen.getByTestId('outbound-unmatched'))
      expect(section.getByText('행 형식 오류')).toBeInTheDocument()
      expect(section.queryByText('invalid_row')).not.toBeInTheDocument()
    })

    it('renders no raw snake_case reason code anywhere in the unmatched section', () => {
      renderWithResult()

      const section = screen.getByTestId('outbound-unmatched')
      expect(section.textContent).not.toMatch(/[a-z]+_[a-z_]+/)
    })

    it('lists the quantity-exceeded item with its current shipped/ordered quantities', () => {
      renderWithResult()

      const section = within(screen.getByTestId('outbound-quantity-exceeded'))
      expect(section.getByText('ISBN002')).toBeInTheDocument()
      expect(section.getByText(/8\s*\/\s*10/)).toBeInTheDocument()
    })

    it('renders a section even when its category is empty, so all three stay visible', () => {
      setupMutations(
        buildResponse({
          unmatched: [],
          unmatched_count: 0,
          quantity_exceeded: [],
          quantity_exceeded_count: 0,
        })
      )
      render(<OutboundPage />)
      fireEvent.change(screen.getByRole('textbox', { name: '출고 처리 행 입력' }), {
        target: { value: '#37349\tISBN001\t4' },
      })
      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))

      expect(screen.getByTestId('outbound-unmatched')).toBeInTheDocument()
      expect(screen.getByTestId('outbound-quantity-exceeded')).toBeInTheDocument()
      expect(
        within(screen.getByTestId('outbound-unmatched')).getByText(/0건/)
      ).toBeInTheDocument()
    })

    it('renders result sections after an Excel upload as well as a manual submit', () => {
      setupMutations(buildResponse())
      render(<OutboundPage />)

      fireEvent.change(screen.getByLabelText('Excel 파일 선택'), {
        target: { files: [new File(['x'], 'outbound.xlsx')] },
      })

      expect(screen.getByTestId('outbound-matched')).toBeInTheDocument()
      expect(screen.getByTestId('outbound-quantity-exceeded')).toBeInTheDocument()
    })
  })

  describe('AC-OUTBOUND-020: 리셋 컨트롤', () => {
    it('shows the reset control only once a result is present', () => {
      setupMutations(buildResponse())
      render(<OutboundPage />)

      expect(screen.queryByRole('button', { name: '다시 처리하기' })).not.toBeInTheDocument()

      fireEvent.change(screen.getByRole('textbox', { name: '출고 처리 행 입력' }), {
        target: { value: '#37349\tISBN001\t4' },
      })
      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))

      expect(screen.getByRole('button', { name: '다시 처리하기' })).toBeInTheDocument()
    })

    it('clears both the input form and the result sections without a reload', () => {
      setupMutations(buildResponse())
      render(<OutboundPage />)

      const textarea = screen.getByRole('textbox', { name: '출고 처리 행 입력' })
      fireEvent.change(textarea, { target: { value: '#37349\tISBN001\t4' } })
      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))
      fireEvent.click(screen.getByRole('button', { name: '다시 처리하기' }))

      expect(textarea).toHaveValue('')
      expect(screen.queryByTestId('outbound-matched')).not.toBeInTheDocument()
      expect(screen.queryByTestId('outbound-unmatched')).not.toBeInTheDocument()
      expect(screen.queryByTestId('outbound-quantity-exceeded')).not.toBeInTheDocument()
    })

    it('allows a second submission after a reset', () => {
      const { processMutate } = setupMutations(buildResponse())
      render(<OutboundPage />)

      const textarea = screen.getByRole('textbox', { name: '출고 처리 행 입력' })
      fireEvent.change(textarea, { target: { value: '#37349\tISBN001\t4' } })
      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))
      fireEvent.click(screen.getByRole('button', { name: '다시 처리하기' }))

      fireEvent.change(textarea, { target: { value: '#37350\tISBN002\t2' } })
      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))

      expect(processMutate).toHaveBeenCalledTimes(2)
      expect(processMutate.mock.calls[1][0]).toEqual([
        { name: '#37350', sku: 'ISBN002', total: 2 },
      ])
    })
  })

  describe('AC-OUTBOUND-017: 페이지 독립성', () => {
    it('renders its own "출고 처리" heading, sharing no RackNumberPage tab shell', () => {
      setupMutations()
      render(<OutboundPage />)

      expect(screen.getByRole('heading', { name: '출고 처리' })).toBeInTheDocument()
      expect(screen.queryAllByRole('tab')).toHaveLength(0)
    })
  })
})

describe('OutboundPage — SPEC-ORDER-016', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Two eligible rows on order #1, one eligible row on order #2, and one
  // ineligible row (order_not_found) on order #3 — used across the AC-FORCE
  // suites below.
  function buildForceUnmatched(): OutboundProcessResponse {
    return {
      matched: [],
      matched_count: 0,
      unmatched: [
        { name: '#1', sku: 'A', total: 4, reason: 'line_item_not_found' },
        { name: '#1', sku: 'B', total: 3, reason: 'line_item_not_found' },
        { name: '#2', sku: 'C', total: 2, reason: 'line_item_not_found' },
        { name: '#3', sku: 'D', total: 3, reason: 'order_not_found' },
      ],
      unmatched_count: 4,
      quantity_exceeded: [],
      quantity_exceeded_count: 0,
    }
  }

  function renderWithForceUnmatched(
    forceOptions: {
      candidates?: OutboundForceCandidateGroup[]
      forceResponse?: OutboundProcessResponse
    } = {}
  ) {
    const mutates = setupMutations(buildForceUnmatched(), forceOptions)
    render(<OutboundPage />)
    fireEvent.change(screen.getByRole('textbox', { name: '출고 처리 행 입력' }), {
      target: { value: '#1\tA\t4' },
    })
    fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))
    return mutates
  }

  describe('AC-FORCE-001: 자격 행에만 컨트롤이 렌더된다', () => {
    it('renders selection/target controls only on line_item_not_found rows with a positive quantity', () => {
      renderWithForceUnmatched()

      expect(screen.getByLabelText('#1 A 선택')).toBeInTheDocument()
      expect(screen.getByLabelText('#1 B 선택')).toBeInTheDocument()
      expect(screen.getByLabelText('#2 C 선택')).toBeInTheDocument()
      expect(screen.queryByLabelText('#3 D 선택')).not.toBeInTheDocument()

      expect(screen.getByLabelText('#1 A 대상 지정')).toBeInTheDocument()
      expect(screen.queryByLabelText('#3 D 대상 지정')).not.toBeInTheDocument()
    })

    it('selects only the eligible rows via "전체 선택"', () => {
      renderWithForceUnmatched()

      fireEvent.click(screen.getByLabelText('전체 선택'))

      expect(screen.getByLabelText('#1 A 선택')).toBeChecked()
      expect(screen.getByLabelText('#1 B 선택')).toBeChecked()
      expect(screen.getByLabelText('#2 C 선택')).toBeChecked()
    })
  })

  describe('REQ-FORCE-003: 후보 조회는 자격 행의 주문 식별자를 배치로 조회한다', () => {
    it('requests candidates with the deduplicated set of eligible order names, never a per-row subset', () => {
      renderWithForceUnmatched()

      // Renders before the result settles pass an empty order-name array
      // (no eligible rows yet) — only the post-settlement calls matter here.
      const settledCalls = mockUseForceCandidates.mock.calls
        .map((call) => call[0] as string[])
        .filter((args) => args.length > 0)

      expect(settledCalls.length).toBeGreaterThan(0)
      for (const args of settledCalls) {
        // Two distinct order names, each counted once — never a per-row
        // (e.g. length-1) subset, even though #1 has two eligible rows.
        expect(args).toEqual(['#1', '#2'])
      }
    })
  })

  describe('AC-FORCE-021: 대상 미지정 시 실행 컨트롤 비활성', () => {
    it('disables the execute control until a selected row also has a target, then enables it', () => {
      const candidates: OutboundForceCandidateGroup[] = [
        {
          order_name: '#1',
          candidates: [
            {
              line_item_id: 101,
              title: 'T',
              sku: 'TARGET-A',
              quantity: 10,
              shipped_quantity: 0,
              logistics_status: 'received',
              no_remaining_capacity: false,
            },
          ],
        },
      ]
      renderWithForceUnmatched({ candidates })

      fireEvent.click(screen.getByLabelText('#1 A 선택'))
      fireEvent.click(screen.getByLabelText('#1 B 선택'))

      expect(screen.getByRole('button', { name: '강제 출고 처리 실행' })).toBeDisabled()

      fireEvent.change(screen.getByLabelText('#1 A 대상 지정'), { target: { value: '101' } })

      expect(screen.getByRole('button', { name: '강제 출고 처리 실행' })).not.toBeDisabled()
    })
  })

  describe('AC-FORCE-015: 일괄 실행 요청 1회, 전송 대상은 지정된 행만 (REQ-FORCE-023)', () => {
    it('fires the force-execute mutation once with only the eligible+selected+target-assigned rows', () => {
      const candidates: OutboundForceCandidateGroup[] = [
        {
          order_name: '#1',
          candidates: [
            {
              line_item_id: 101,
              title: 'T',
              sku: 'TARGET-A',
              quantity: 10,
              shipped_quantity: 0,
              logistics_status: 'received',
              no_remaining_capacity: false,
            },
            {
              line_item_id: 102,
              title: 'T2',
              sku: 'TARGET-B',
              quantity: 10,
              shipped_quantity: 0,
              logistics_status: 'received',
              no_remaining_capacity: false,
            },
          ],
        },
      ]
      const { forceMutate } = renderWithForceUnmatched({ candidates })

      // Select and assign targets to #1/A and #1/B; select #2/C but leave it
      // unassigned — only the two target-assigned rows may be sent.
      fireEvent.click(screen.getByLabelText('#1 A 선택'))
      fireEvent.click(screen.getByLabelText('#1 B 선택'))
      fireEvent.click(screen.getByLabelText('#2 C 선택'))
      fireEvent.change(screen.getByLabelText('#1 A 대상 지정'), { target: { value: '101' } })
      fireEvent.change(screen.getByLabelText('#1 B 대상 지정'), { target: { value: '102' } })

      fireEvent.click(screen.getByRole('button', { name: '강제 출고 처리 실행' }))

      expect(forceMutate).toHaveBeenCalledTimes(1)
      expect(forceMutate.mock.calls[0][0]).toEqual([
        { name: '#1', sku: 'A', total: 4, line_item_id: 101 },
        { name: '#1', sku: 'B', total: 3, line_item_id: 102 },
      ])
    })
  })

  describe('AC-FORCE-022: 실행 성공 시 결과 병합, 미선택 행 잔존, 재제출 불가', () => {
    it('merges the force response into the result slot: submitted rows disappear, R3 stays selectable, matched/quantity_exceeded appear, counts recompute', () => {
      // Given: R1(#1/A), R2(#2/C), R3(#1/B) are the only unmatched rows, all
      // eligible — matches AC-FORCE-022's Given exactly (3 eligible rows,
      // R1/R2 get selected+assigned, R3 does not).
      const initialResult: OutboundProcessResponse = {
        matched: [],
        matched_count: 0,
        unmatched: [
          { name: '#1', sku: 'A', total: 4, reason: 'line_item_not_found' }, // R1
          { name: '#2', sku: 'C', total: 2, reason: 'line_item_not_found' }, // R2
          { name: '#1', sku: 'B', total: 3, reason: 'line_item_not_found' }, // R3
        ],
        unmatched_count: 3,
        quantity_exceeded: [],
        quantity_exceeded_count: 0,
      }
      const candidates: OutboundForceCandidateGroup[] = [
        {
          order_name: '#1',
          candidates: [
            {
              line_item_id: 101,
              title: 'T',
              sku: 'TARGET-A',
              quantity: 10,
              shipped_quantity: 0,
              logistics_status: 'received',
              no_remaining_capacity: false,
            },
          ],
        },
        {
          order_name: '#2',
          candidates: [
            {
              line_item_id: 102,
              title: 'T2',
              sku: 'TARGET-B',
              quantity: 10,
              shipped_quantity: 8,
              logistics_status: 'received',
              no_remaining_capacity: false,
            },
          ],
        },
      ]
      const forceResponse: OutboundProcessResponse = {
        matched: [
          {
            name: '#1',
            sku: 'TARGET-A',
            total: 4,
            line_item_id: 101,
            shipped_quantity: 4,
            quantity: 10,
            logistics_status: 'received',
          },
        ],
        matched_count: 1,
        unmatched: [],
        unmatched_count: 0,
        quantity_exceeded: [
          {
            name: '#2',
            sku: 'TARGET-B',
            total: 3,
            line_item_id: 102,
            shipped_quantity: 8,
            quantity: 10,
            reason: 'quantity_exceeded',
          },
        ],
        quantity_exceeded_count: 1,
      }
      const { forceMutate } = setupMutations(initialResult, { candidates, forceResponse })
      render(<OutboundPage />)
      fireEvent.change(screen.getByRole('textbox', { name: '출고 처리 행 입력' }), {
        target: { value: '#1\tA\t4' },
      })
      fireEvent.click(screen.getByRole('button', { name: '출고 처리 실행' }))

      // Select+assign R1 (#1/A) and R2 (#2/C); leave R3 (#1/B) unselected.
      fireEvent.click(screen.getByLabelText('#1 A 선택'))
      fireEvent.change(screen.getByLabelText('#1 A 대상 지정'), { target: { value: '101' } })
      fireEvent.click(screen.getByLabelText('#2 C 선택'))
      fireEvent.change(screen.getByLabelText('#2 C 대상 지정'), { target: { value: '102' } })

      fireEvent.click(screen.getByRole('button', { name: '강제 출고 처리 실행' }))

      expect(forceMutate).toHaveBeenCalledTimes(1)

      // (1) submitted rows are gone from the unmatched section — cannot be
      // reselected or resubmitted.
      expect(screen.queryByLabelText('#1 A 선택')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('#2 C 선택')).not.toBeInTheDocument()

      // (2) unselected R3 (#1/B) remains, still selectable and assignable.
      expect(screen.getByLabelText('#1 B 선택')).toBeInTheDocument()
      expect(screen.getByLabelText('#1 B 대상 지정')).toBeInTheDocument()
      expect(screen.getByLabelText('#1 B 선택')).not.toBeChecked()

      // (3) the force response's matched/quantity_exceeded items appear in
      // their respective sections — a reverted quantity-exceeded row is not
      // dropped from the screen.
      expect(
        within(screen.getByTestId('outbound-matched')).getByText('TARGET-A')
      ).toBeInTheDocument()
      expect(
        within(screen.getByTestId('outbound-quantity-exceeded')).getByText('TARGET-B')
      ).toBeInTheDocument()

      // (4) each section's count matches its displayed list length.
      expect(within(screen.getByTestId('outbound-matched')).getByText(/1건/)).toBeInTheDocument()
      expect(within(screen.getByTestId('outbound-unmatched')).getByText(/1건/)).toBeInTheDocument()
      expect(
        within(screen.getByTestId('outbound-quantity-exceeded')).getByText(/1건/)
      ).toBeInTheDocument()
    })
  })
})
