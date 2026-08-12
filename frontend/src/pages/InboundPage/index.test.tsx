import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { InboundPage } from './index'
import {
  useUploadVendorShipment,
  useUploadWarehouseReceipt,
} from '@/hooks/usePurchaseOrderQueries'
import type { UploadWarehouseReceiptResponse } from '@/services/purchaseOrderApi'

vi.mock('@/hooks/usePurchaseOrderQueries', () => ({
  useUploadVendorShipment: vi.fn(),
  useUploadWarehouseReceipt: vi.fn(),
}))

describe('InboundPage — promoted from PurchaseOrders/LogisticsStatusTab', () => {
  const vendorMutate = vi.fn()
  const warehouseMutate = vi.fn()

  beforeEach(() => {
    vendorMutate.mockClear()
    warehouseMutate.mockClear()
    vi.mocked(useUploadVendorShipment).mockReturnValue({
      mutate: vendorMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useUploadVendorShipment>)
    vi.mocked(useUploadWarehouseReceipt).mockReturnValue({
      mutate: warehouseMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useUploadWarehouseReceipt>)
  })

  describe('페이지 독립성', () => {
    it('renders its own "입고 처리" heading, sharing no PurchaseOrders tab shell', () => {
      render(<InboundPage />)
      expect(screen.getByRole('heading', { name: '입고 처리' })).toBeInTheDocument()
      expect(screen.queryAllByRole('tab')).toHaveLength(0)
    })
  })

  it('renders two upload cards for vendor shipment confirmation and warehouse receiving results (REQ-LOGI-003/005)', () => {
    render(<InboundPage />)
    expect(screen.getByText('벤더 출고확인 업로드')).toBeInTheDocument()
    expect(screen.getByText('창고 입고결과 업로드')).toBeInTheDocument()
  })

  it('calls uploadVendorShipment mutation with the selected file (REQ-LOGI-003)', () => {
    const { container } = render(<InboundPage />)
    const file = new File(['dummy'], 'vendor.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const fileInputs = container.querySelectorAll('input[type="file"]')
    fireEvent.change(fileInputs[0], { target: { files: [file] } })

    expect(vendorMutate).toHaveBeenCalledTimes(1)
    const [formData] = vendorMutate.mock.calls[0]
    expect(formData instanceof FormData).toBe(true)
    expect((formData as FormData).get('file')).toBe(file)
  })

  it('shows matched/skipped counts on successful vendor shipment upload (success state)', () => {
    vendorMutate.mockImplementation((_formData, opts) => {
      opts.onSuccess({ matched_count: 5, skipped_count: 2 })
    })
    const { container } = render(<InboundPage />)
    const file = new File(['dummy'], 'vendor.xlsx', { type: 'application/xlsx' })
    const fileInputs = container.querySelectorAll('input[type="file"]')
    fireEvent.change(fileInputs[0], { target: { files: [file] } })

    expect(screen.getByText(/매칭: 5건/)).toBeInTheDocument()
    expect(screen.getByText(/건너뜀: 2건/)).toBeInTheDocument()
  })

  it('shows an error message on failed warehouse receipt upload (failure state)', () => {
    warehouseMutate.mockImplementation((_formData, opts) => {
      opts.onError(new Error('network error'))
    })
    const { container } = render(<InboundPage />)
    const file = new File(['dummy'], 'warehouse.xlsx', { type: 'application/xlsx' })
    const fileInputs = container.querySelectorAll('input[type="file"]')
    fireEvent.change(fileInputs[1], { target: { files: [file] } })

    expect(screen.getByText('창고 입고결과 파일 업로드에 실패했습니다.')).toBeInTheDocument()
  })

  it('shows matched/skipped counts on successful warehouse receipt upload (success state)', () => {
    // REQ-LOGI-017: the real backend response always carries the detail
    // lists alongside the counts — this uses the full shape rather than a
    // counts-only stub, since a counts-only payload from this endpoint no
    // longer matches the actual contract (unlike uploadVendorShipment above).
    warehouseMutate.mockImplementation((_formData, opts) => {
      opts.onSuccess({
        matched_count: 3,
        skipped_count: 0,
        matched: [],
        unmatched: [],
        unmatched_count: 0,
        quantity_exceeded: [],
        quantity_exceeded_count: 0,
      })
    })
    const { container } = render(<InboundPage />)
    const file = new File(['dummy'], 'warehouse.xlsx', { type: 'application/xlsx' })
    const fileInputs = container.querySelectorAll('input[type="file"]')
    fireEvent.change(fileInputs[1], { target: { files: [file] } })

    expect(screen.getByText(/매칭: 3건/)).toBeInTheDocument()
    expect(screen.getByText(/건너뜀: 0건/)).toBeInTheDocument()
  })

  // REQ-LOGI-017: per-row breakdown for the warehouse receipt card.
  describe('REQ-LOGI-017: 창고 입고결과 결과 상세 breakdown', () => {
    function buildWarehouseResponse(
      overrides: Partial<UploadWarehouseReceiptResponse> = {}
    ): UploadWarehouseReceiptResponse {
      return {
        matched_count: 1,
        skipped_count: 2,
        matched: [
          {
            name: '#37349',
            sku: 'ISBN001',
            received_count: 2,
            line_item_id: 11,
            received_quantity: 2,
            quantity: 10,
            logistics_status: 'received',
          },
        ],
        unmatched: [{ name: '#99999', sku: 'ISBN001', received_count: 1, reason: 'order_not_found' }],
        unmatched_count: 1,
        quantity_exceeded: [
          {
            name: '#37350',
            sku: 'ISBN002',
            received_count: 5,
            line_item_id: 12,
            received_quantity: 8,
            quantity: 10,
            reason: 'quantity_exceeded',
          },
        ],
        quantity_exceeded_count: 1,
        ...overrides,
      }
    }

    function uploadWarehouseFile(container: HTMLElement) {
      const file = new File(['dummy'], 'warehouse.xlsx', { type: 'application/xlsx' })
      const fileInputs = container.querySelectorAll('input[type="file"]')
      fireEvent.change(fileInputs[1], { target: { files: [file] } })
    }

    it('renders the three result sections with the detailed payload', () => {
      warehouseMutate.mockImplementation((_formData, opts) => {
        opts.onSuccess(buildWarehouseResponse())
      })
      const { container } = render(<InboundPage />)
      uploadWarehouseFile(container)

      expect(screen.getByTestId('warehouse-matched')).toBeInTheDocument()
      expect(screen.getByTestId('warehouse-unmatched')).toBeInTheDocument()
      expect(screen.getByTestId('warehouse-quantity-exceeded')).toBeInTheDocument()

      const matchedSection = within(screen.getByTestId('warehouse-matched'))
      expect(matchedSection.getByText('#37349')).toBeInTheDocument()
      expect(matchedSection.getByText('ISBN001')).toBeInTheDocument()
      expect(matchedSection.getByText(/2\s*\/\s*10/)).toBeInTheDocument()

      const exceededSection = within(screen.getByTestId('warehouse-quantity-exceeded'))
      expect(exceededSection.getByText('ISBN002')).toBeInTheDocument()
      expect(exceededSection.getByText(/8\s*\/\s*10/)).toBeInTheDocument()
    })

    it('shows a skipped row with its Korean reason label, not the raw reason code', () => {
      warehouseMutate.mockImplementation((_formData, opts) => {
        opts.onSuccess(buildWarehouseResponse())
      })
      const { container } = render(<InboundPage />)
      uploadWarehouseFile(container)

      const unmatchedSection = within(screen.getByTestId('warehouse-unmatched'))
      expect(unmatchedSection.getByText('주문 없음')).toBeInTheDocument()
      expect(unmatchedSection.queryByText('order_not_found')).not.toBeInTheDocument()
    })

    it('renders the "received" logistics_status as its Korean label', () => {
      warehouseMutate.mockImplementation((_formData, opts) => {
        opts.onSuccess(buildWarehouseResponse())
      })
      const { container } = render(<InboundPage />)
      uploadWarehouseFile(container)

      const matchedSection = within(screen.getByTestId('warehouse-matched'))
      expect(matchedSection.getByText('입고')).toBeInTheDocument()
    })

    it('renders an empty category with a 0 count instead of omitting the section', () => {
      warehouseMutate.mockImplementation((_formData, opts) => {
        opts.onSuccess(
          buildWarehouseResponse({
            unmatched: [],
            unmatched_count: 0,
            quantity_exceeded: [],
            quantity_exceeded_count: 0,
          })
        )
      })
      const { container } = render(<InboundPage />)
      uploadWarehouseFile(container)

      expect(screen.getByTestId('warehouse-unmatched')).toBeInTheDocument()
      expect(screen.getByTestId('warehouse-quantity-exceeded')).toBeInTheDocument()
      expect(
        within(screen.getByTestId('warehouse-unmatched')).getByText(/0건/)
      ).toBeInTheDocument()
      expect(
        within(screen.getByTestId('warehouse-quantity-exceeded')).getByText(/0건/)
      ).toBeInTheDocument()
    })

    it('clears the previous run detail sections before a new upload result arrives', () => {
      warehouseMutate.mockImplementation((_formData, opts) => {
        opts.onSuccess(buildWarehouseResponse())
      })
      const { container } = render(<InboundPage />)
      uploadWarehouseFile(container)
      expect(screen.getByTestId('warehouse-matched')).toBeInTheDocument()

      // Second upload that never resolves onSuccess (e.g. still pending) —
      // the stale result must be cleared immediately, not left rendered.
      warehouseMutate.mockImplementation(() => {})
      uploadWarehouseFile(container)

      expect(screen.queryByTestId('warehouse-matched')).not.toBeInTheDocument()
      expect(screen.queryByTestId('warehouse-unmatched')).not.toBeInTheDocument()
      expect(screen.queryByTestId('warehouse-quantity-exceeded')).not.toBeInTheDocument()
    })

    // Regression guard for the shared UploadLogisticsResponse typing: the
    // vendor shipment card must keep working with a counts-only response
    // and must never render the per-row detail sections.
    it('regression: vendor shipment card stays counts-only and renders no detail sections', () => {
      vendorMutate.mockImplementation((_formData, opts) => {
        opts.onSuccess({ matched_count: 4, skipped_count: 1 })
      })
      const { container } = render(<InboundPage />)
      const file = new File(['dummy'], 'vendor.xlsx', { type: 'application/xlsx' })
      const fileInputs = container.querySelectorAll('input[type="file"]')
      fireEvent.change(fileInputs[0], { target: { files: [file] } })

      expect(screen.getByText(/매칭: 4건/)).toBeInTheDocument()
      expect(screen.getByText(/건너뜀: 1건/)).toBeInTheDocument()
      expect(screen.queryByTestId('warehouse-matched')).not.toBeInTheDocument()
      expect(screen.queryByTestId('warehouse-unmatched')).not.toBeInTheDocument()
      expect(screen.queryByTestId('warehouse-quantity-exceeded')).not.toBeInTheDocument()
    })
  })
})
