import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { DailyReviewTab } from './DailyReviewTab'
import {
  useDownloadDailyReview,
  useUploadDailyReview,
  useGenerateOrderFile,
} from '@/hooks/usePurchaseOrderQueries'
import type { UploadDailyReviewResponse } from '@/services/purchaseOrderApi'

vi.mock('@/hooks/usePurchaseOrderQueries', () => ({
  useDownloadDailyReview: vi.fn(),
  useUploadDailyReview: vi.fn(),
  useGenerateOrderFile: vi.fn(),
}))

// REQ-PO8-020: the upload result now reports WHICH rows were skipped and why,
// not just a tally — these cover the rendering of that list.
describe('DailyReviewTab — 건너뜀 상세 목록 (REQ-PO8-020)', () => {
  const uploadMutate = vi.fn()

  const uploadFile = () => {
    const { container } = render(<DailyReviewTab />)
    const file = new File(['dummy'], 'daily_review.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const fileInput = container.querySelector('input[type="file"]')!
    fireEvent.change(fileInput, { target: { files: [file] } })
  }

  const respondWith = (data: UploadDailyReviewResponse) => {
    uploadMutate.mockImplementation((_formData, opts) => {
      opts.onSuccess(data)
    })
  }

  beforeEach(() => {
    uploadMutate.mockClear()
    vi.mocked(useDownloadDailyReview).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useDownloadDailyReview>)
    vi.mocked(useGenerateOrderFile).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useGenerateOrderFile>)
    vi.mocked(useUploadDailyReview).mockReturnValue({
      mutate: uploadMutate,
      isPending: false,
      isSuccess: true,
    } as unknown as ReturnType<typeof useUploadDailyReview>)
  })

  it('renders one row per skipped item with its Korean reason label', () => {
    respondWith({
      confirmed_count: 1,
      skipped_count: 2,
      skipped: [
        {
          name: '#8001',
          sku: '9788901234567',
          title: '',
          selection: '북센',
          reason: 'line_item_not_found',
        },
        {
          name: '#8002',
          sku: '9788901234568',
          title: '오타 도서',
          selection: '북셴',
          reason: 'selection_unrecognized',
        },
      ],
      confirmed_by_distributor: {},
    })
    uploadFile()

    const section = screen.getByTestId('daily-review-skipped')
    expect(within(section).getByText('건너뜀')).toBeInTheDocument()
    expect(within(section).getByText('2건')).toBeInTheDocument()
    expect(within(section).getByText('발주 대상 품목 없음')).toBeInTheDocument()
    expect(within(section).getByText('선택값 인식 불가')).toBeInTheDocument()
    // The unrecognized '선택' value is shown verbatim so the typo is visible.
    expect(within(section).getByText('북셴')).toBeInTheDocument()
    expect(within(section).getByText('오타 도서')).toBeInTheDocument()
  })

  it('substitutes placeholders for a blank 주문번호 and a blank 선택값', () => {
    respondWith({
      confirmed_count: 0,
      skipped_count: 1,
      skipped: [
        { name: '', sku: '9788901234569', title: '', selection: '', reason: 'order_not_found' },
      ],
      confirmed_by_distributor: {},
    })
    uploadFile()

    const section = screen.getByTestId('daily-review-skipped')
    expect(within(section).getByText('(없음)')).toBeInTheDocument()
    expect(within(section).getByText('(비어 있음)')).toBeInTheDocument()
    expect(within(section).getByText('주문번호 없음')).toBeInTheDocument()
  })

  it('renders the section as visibly empty when nothing was skipped', () => {
    respondWith({
      confirmed_count: 3,
      skipped_count: 0,
      skipped: [],
      confirmed_by_distributor: {},
    })
    uploadFile()

    const section = screen.getByTestId('daily-review-skipped')
    expect(within(section).getByText('0건')).toBeInTheDocument()
    expect(within(section).getByText('해당 항목이 없습니다.')).toBeInTheDocument()
  })

  it('omits the section entirely when the response carries no skipped list', () => {
    respondWith({
      confirmed_count: 1,
      skipped_count: 0,
      confirmed_by_distributor: {},
    })
    uploadFile()

    expect(screen.queryByTestId('daily-review-skipped')).not.toBeInTheDocument()
    // The pre-existing count summary is unaffected.
    expect(screen.getByText(/확정: 1건/)).toBeInTheDocument()
  })
})
