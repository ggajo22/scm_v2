import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CreateAdminDialog } from './CreateAdminDialog'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('CreateAdminDialog', () => {
  const onOpenChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('열린 상태에서 폼 필드를 렌더링한다', () => {
    const Wrapper = createWrapper()
    render(<CreateAdminDialog open={true} onOpenChange={onOpenChange} />, { wrapper: Wrapper })

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/사용자명/i)).toBeInTheDocument()
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument()
  })

  it('닫힌 상태에서 다이얼로그가 없다', () => {
    const Wrapper = createWrapper()
    render(<CreateAdminDialog open={false} onOpenChange={onOpenChange} />, { wrapper: Wrapper })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('취소 버튼 클릭 시 onOpenChange(false)를 호출한다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<CreateAdminDialog open={true} onOpenChange={onOpenChange} />, { wrapper: Wrapper })

    await user.click(screen.getByRole('button', { name: /취소/i }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('REQ-020: username 빈 값으로 제출 시 에러를 표시한다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<CreateAdminDialog open={true} onOpenChange={onOpenChange} />, { wrapper: Wrapper })

    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /^생성$/i }))

    await waitFor(() => {
      expect(within(dialog).getByText(/사용자명을 입력해주세요/i)).toBeInTheDocument()
    })
  })

  it('REQ-020: password 8자 미만 시 에러를 표시한다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<CreateAdminDialog open={true} onOpenChange={onOpenChange} />, { wrapper: Wrapper })

    const dialog = screen.getByRole('dialog')
    await user.type(within(dialog).getByLabelText(/사용자명/i), 'testuser')
    await user.type(within(dialog).getByLabelText('비밀번호'), 'short')
    await user.click(within(dialog).getByRole('button', { name: /^생성$/i }))

    await waitFor(() => {
      expect(within(dialog).getByText(/최소 8자/i)).toBeInTheDocument()
    })
  })
})
