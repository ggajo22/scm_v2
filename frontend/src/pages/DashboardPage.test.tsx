import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DashboardPage } from './DashboardPage'

vi.mock('@/features/book/hooks/useDashboardMetrics')

import { useDashboardMetrics } from '@/features/book/hooks/useDashboardMetrics'

const mockUseDashboardMetrics = vi.mocked(useDashboardMetrics)

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

const fullMetrics = {
  status_counts: [
    { status: 1, label: '대기', count: 10 },
    { status: 2, label: '처리중', count: 5 },
  ],
  shopify_created_24h: 3,
  error_total: 5,
  error_rows: [{ status: 99, label: '오류', count: 5 }],
  waiting_total: 10,
  unresolved_note_count: 2,
  sale_zero_count: 7,
  cost_zero_count: 4,
}

const zeroMetrics = {
  status_counts: [],
  shopify_created_24h: 0,
  error_total: 0,
  error_rows: [],
  waiting_total: 0,
  unresolved_note_count: 0,
  sale_zero_count: 0,
  cost_zero_count: 0,
}

describe('DashboardPage', () => {
  it('로딩 중일 때 스켈레톤을 렌더링한다', () => {
    mockUseDashboardMetrics.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useDashboardMetrics>)

    render(<DashboardPage />, { wrapper: createWrapper() })

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('5')).not.toBeInTheDocument()
  })

  it('에러 발생 시 에러 메시지를 표시한다', () => {
    mockUseDashboardMetrics.mockReturnValue({
      isPending: false,
      isError: true,
      data: undefined,
    } as ReturnType<typeof useDashboardMetrics>)

    render(<DashboardPage />, { wrapper: createWrapper() })

    expect(screen.getByText(/불러오는데 실패/)).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('데이터가 있을 때 주요 지표 값을 표시한다', () => {
    mockUseDashboardMetrics.mockReturnValue({
      isPending: false,
      isError: false,
      data: fullMetrics,
    } as ReturnType<typeof useDashboardMetrics>)

    render(<DashboardPage />, { wrapper: createWrapper() })

    // error_total = 5 (여러 곳에 표시될 수 있으므로 getAllByText 사용)
    expect(screen.getAllByText('5').length).toBeGreaterThanOrEqual(1)
    // waiting_total = 10
    expect(screen.getAllByText('10').length).toBeGreaterThanOrEqual(1)
    // shopify_created_24h = 3
    expect(screen.getByText('3')).toBeInTheDocument()
    // status_counts 테이블 레이블
    expect(screen.getByText('대기')).toBeInTheDocument()
    expect(screen.getByText('처리중')).toBeInTheDocument()
  })

  it('모든 값이 0일 때 0을 표시한다 (null/undefined 아님)', () => {
    mockUseDashboardMetrics.mockReturnValue({
      isPending: false,
      isError: false,
      data: zeroMetrics,
    } as ReturnType<typeof useDashboardMetrics>)

    render(<DashboardPage />, { wrapper: createWrapper() })

    // 0 값이 여러 개 표시되어야 함
    const zeros = screen.getAllByText('0')
    expect(zeros.length).toBeGreaterThanOrEqual(6)
  })
})
