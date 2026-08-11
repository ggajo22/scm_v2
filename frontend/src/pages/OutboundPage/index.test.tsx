import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { OutboundPage } from './index'
import { useProcessOutboundManual, useUploadOutbound } from '@/hooks/useOutboundQueries'
import type { OutboundProcessResponse } from '@/services/outboundApi'

vi.mock('@/hooks/useOutboundQueries', () => ({
  useProcessOutboundManual: vi.fn(),
  useUploadOutbound: vi.fn(),
}))

const mockUseProcess = vi.mocked(useProcessOutboundManual)
const mockUseUpload = vi.mocked(useUploadOutbound)

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
function setupMutations(response: OutboundProcessResponse | null = null) {
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
  mockUseProcess.mockReturnValue({ mutate: processMutate, isPending: false } as never)
  mockUseUpload.mockReturnValue({ mutate: uploadMutate, isPending: false } as never)
  return { processMutate, uploadMutate }
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
