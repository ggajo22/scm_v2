import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LogisticsStatusTab } from './LogisticsStatusTab'
import {
  useUploadVendorShipment,
  useUploadWarehouseReceipt,
} from '@/hooks/usePurchaseOrderQueries'

vi.mock('@/hooks/usePurchaseOrderQueries', () => ({
  useUploadVendorShipment: vi.fn(),
  useUploadWarehouseReceipt: vi.fn(),
}))

describe('LogisticsStatusTab — SPEC-ORDER-011 T11 upload cards', () => {
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

  it('renders two upload cards for vendor shipment confirmation and warehouse receiving results (REQ-LOGI-003/005)', () => {
    render(<LogisticsStatusTab />)
    expect(screen.getByText('벤더 출고확인 업로드')).toBeInTheDocument()
    expect(screen.getByText('창고 입고결과 업로드')).toBeInTheDocument()
  })

  it('calls uploadVendorShipment mutation with the selected file (REQ-LOGI-003)', () => {
    const { container } = render(<LogisticsStatusTab />)
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
    const { container } = render(<LogisticsStatusTab />)
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
    const { container } = render(<LogisticsStatusTab />)
    const file = new File(['dummy'], 'warehouse.xlsx', { type: 'application/xlsx' })
    const fileInputs = container.querySelectorAll('input[type="file"]')
    fireEvent.change(fileInputs[1], { target: { files: [file] } })

    expect(screen.getByText('창고 입고결과 파일 업로드에 실패했습니다.')).toBeInTheDocument()
  })

  it('shows matched/skipped counts on successful warehouse receipt upload (success state)', () => {
    warehouseMutate.mockImplementation((_formData, opts) => {
      opts.onSuccess({ matched_count: 3, skipped_count: 0 })
    })
    const { container } = render(<LogisticsStatusTab />)
    const file = new File(['dummy'], 'warehouse.xlsx', { type: 'application/xlsx' })
    const fileInputs = container.querySelectorAll('input[type="file"]')
    fireEvent.change(fileInputs[1], { target: { files: [file] } })

    expect(screen.getByText(/매칭: 3건/)).toBeInTheDocument()
    expect(screen.getByText(/건너뜀: 0건/)).toBeInTheDocument()
  })
})
