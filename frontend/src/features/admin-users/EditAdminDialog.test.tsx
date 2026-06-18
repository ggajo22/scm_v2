import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EditAdminDialog } from './EditAdminDialog'
import { useAuthStore } from '@/store/authStore'
import type { AdminUser } from '@/types/auth'

vi.mock('@/store/authStore')

const mockUseAuthStore = vi.mocked(useAuthStore)

const buildSelectorMock = (currentUserId = 1) => {
  const state = {
    accessToken: 'token',
    user: { id: currentUserId, username: 'superadmin', role: 'super_admin' as const, is_active: true },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    restoreSession: vi.fn(),
  }
  return (selector?: (s: typeof state) => unknown) => {
    if (typeof selector === 'function') return selector(state)
    return state
  }
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

const testUser: AdminUser = {
  id: 2,
  username: 'testadmin',
  role: 'admin',
  is_active: true,
  date_joined: '2024-01-01',
}

describe('EditAdminDialog', () => {
  const onOpenChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuthStore.mockImplementation(buildSelectorMock(1) as typeof useAuthStore)
  })

  it('열린 상태에서 사용자 정보를 폼에 채운다', () => {
    const Wrapper = createWrapper()
    render(
      <EditAdminDialog open={true} onOpenChange={onOpenChange} user={testUser} />,
      { wrapper: Wrapper }
    )

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByDisplayValue('testadmin')).toBeInTheDocument()
  })

  it('user가 null이면 렌더링하지 않는다', () => {
    const Wrapper = createWrapper()
    render(
      <EditAdminDialog open={true} onOpenChange={onOpenChange} user={null} />,
      { wrapper: Wrapper }
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('취소 버튼 클릭 시 onOpenChange(false)를 호출한다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(
      <EditAdminDialog open={true} onOpenChange={onOpenChange} user={testUser} />,
      { wrapper: Wrapper }
    )

    await user.click(screen.getByRole('button', { name: /취소/i }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('REQ-025: 자기 계정 수정 시 is_active 스위치가 disabled된다', () => {
    // Current user id=2 matches testUser id=2
    mockUseAuthStore.mockImplementation(buildSelectorMock(2) as typeof useAuthStore)
    const Wrapper = createWrapper()
    render(
      <EditAdminDialog open={true} onOpenChange={onOpenChange} user={testUser} />,
      { wrapper: Wrapper }
    )

    const switchEl = screen.getByRole('switch')
    expect(switchEl).toBeDisabled()
  })

  it('다른 사용자 수정 시 is_active 스위치가 활성화된다', () => {
    // Current user id=1, editing user id=2
    mockUseAuthStore.mockImplementation(buildSelectorMock(1) as typeof useAuthStore)
    const Wrapper = createWrapper()
    render(
      <EditAdminDialog open={true} onOpenChange={onOpenChange} user={testUser} />,
      { wrapper: Wrapper }
    )

    const switchEl = screen.getByRole('switch')
    expect(switchEl).not.toBeDisabled()
  })

  it('REQ-025: 자기 계정은 is_active 스위치가 disabled된다', () => {
    // Current user id=2 matches testUser id=2
    mockUseAuthStore.mockImplementation(buildSelectorMock(2) as typeof useAuthStore)
    const Wrapper = createWrapper()
    render(
      <EditAdminDialog
        open={true}
        onOpenChange={onOpenChange}
        user={{ ...testUser, id: 2 }}
      />,
      { wrapper: Wrapper }
    )

    // The switch is disabled, so clicking it does nothing
    const switchEl = screen.getByRole('switch')
    expect(switchEl).toBeDisabled()
  })

  it('변경 사항 없이 저장 클릭 시 다이얼로그가 닫힌다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(
      <EditAdminDialog open={true} onOpenChange={onOpenChange} user={testUser} />,
      { wrapper: Wrapper }
    )

    await user.click(screen.getByRole('button', { name: /저장/i }))

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
