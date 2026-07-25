import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VendorFileUploadTab } from './VendorFileUploadTab'
import { useUploadVendorFile } from '@/hooks/usePurchaseOrderQueries'

vi.mock('@/hooks/usePurchaseOrderQueries', () => ({
  useUploadVendorFile: vi.fn(),
}))

describe('VendorFileUploadTab', () => {
  const mutate = vi.fn()

  beforeEach(() => {
    mutate.mockClear()
    vi.mocked(useUploadVendorFile).mockReturnValue({
      mutate,
      isPending: false,
    } as unknown as ReturnType<typeof useUploadVendorFile>)
  })

  it('renders 북센, 교보, YES24 options in the distributor dropdown (AC-008)', () => {
    render(<VendorFileUploadTab />)
    const select = screen.getByLabelText('발주처 선택')
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.textContent)
    expect(options).toEqual(['북센', '교보', 'YES24'])
  })

  it('calls the upload mutation with distributor=yes24 when YES24 is selected and a file is uploaded (AC-008)', async () => {
    const user = userEvent.setup()
    const { container } = render(<VendorFileUploadTab />)

    const select = screen.getByLabelText('발주처 선택')
    await user.selectOptions(select, 'YES24')

    const file = new File(['dummy'], 'yes24.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [file] } })

    expect(mutate).toHaveBeenCalledTimes(1)
    const [formData] = mutate.mock.calls[0]
    expect(formData instanceof FormData).toBe(true)
    expect((formData as FormData).get('distributor')).toBe('yes24')
    expect((formData as FormData).get('file')).toBe(file)
  })
})
