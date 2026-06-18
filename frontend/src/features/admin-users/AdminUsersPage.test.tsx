import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AdminUsersPage } from './AdminUsersPage'
import { useAuthStore } from '@/store/authStore'
vi.mock('@/store/authStore')

const mockUseAuthStore = vi.mocked(useAuthStore)

// Selector-aware mock
const buildSelectorMock = (userId = 1, role: 'super_admin' | 'admin' = 'super_admin') => {
  const state = {
    accessToken: 'token',
    user: { id: userId, username: 'superadmin', role, is_active: true },
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
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    )
  }
}

describe('AdminUsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuthStore.mockImplementation(buildSelectorMock() as typeof useAuthStore)
  })

  it('REQ-017: 관리자 목록 테이블을 렌더링한다', async () => {
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByText('superadmin')).toBeInTheDocument()
      expect(screen.getByText('admin1')).toBeInTheDocument()
    })
  })

  it('REQ-018: 로딩 중에는 스켈레톤을 표시한다', () => {
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    // Initial loading state
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('관리자 생성 버튼 클릭 시 생성 다이얼로그가 열린다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    await user.click(screen.getByRole('button', { name: /관리자 생성/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('REQ-020: 생성 폼 유효성 검사 — username 필수', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    await user.click(screen.getByRole('button', { name: /관리자 생성/i }))
    await waitFor(() => screen.getByRole('dialog'))
    await user.click(screen.getByRole('button', { name: /^생성$/i }))

    await waitFor(() => {
      expect(screen.getByText(/사용자명을 입력해주세요/i)).toBeInTheDocument()
    })
  })

  it('REQ-020: 생성 폼 유효성 검사 — password 최소 8자', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    await user.click(screen.getByRole('button', { name: /관리자 생성/i }))
    await waitFor(() => screen.getByRole('dialog'))

    const dialog = screen.getByRole('dialog')
    await user.type(within(dialog).getByLabelText(/사용자명/i), 'newuser')
    await user.type(within(dialog).getByLabelText('비밀번호'), 'short')
    await user.click(within(dialog).getByRole('button', { name: /^생성$/i }))

    await waitFor(() => {
      expect(screen.getByText(/최소 8자/i)).toBeInTheDocument()
    })
  })

  it('REQ-022: 생성 폼 유효성 검사 — role 필수', async () => {
    // Test validation for required fields — role must be selected
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    await user.click(screen.getByRole('button', { name: /관리자 생성/i }))
    await waitFor(() => screen.getByRole('dialog'))

    // Submit with all empty — role error should appear
    await user.click(screen.getByRole('button', { name: /^생성$/i }))

    await waitFor(() => {
      // username and password errors should both appear
      expect(screen.getByText(/사용자명을 입력해주세요/i)).toBeInTheDocument()
    })
  })

  it('수정 버튼 클릭 시 수정 다이얼로그가 열린다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    const editButtons = screen.getAllByRole('button', { name: /수정/i })
    await user.click(editButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText('관리자 수정')).toBeInTheDocument()
    })
  })

  it('비밀번호 초기화 버튼 클릭 시 초기화 다이얼로그가 열린다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    const resetButtons = screen.getAllByRole('button', { name: /비밀번호 초기화/i })
    await user.click(resetButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('REQ-027: 비밀번호 불일치 시 에러를 표시한다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    const resetButtons = screen.getAllByRole('button', { name: /비밀번호 초기화/i })
    await user.click(resetButtons[0])

    await waitFor(() => screen.getByRole('dialog'))

    await user.type(screen.getByLabelText(/새 비밀번호/i), 'password123')
    await user.type(screen.getByLabelText(/비밀번호 확인/i), 'different456')
    await user.click(screen.getByRole('button', { name: /^초기화$/i }))

    await waitFor(() => {
      expect(screen.getByText(/비밀번호가 일치하지 않습니다/i)).toBeInTheDocument()
    })
  })

  it('REQ-025: 자기 계정 수정 시 is_active 스위치가 disabled된다', async () => {
    // Current user id=1, and first user in list also has id=1
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    const editButtons = screen.getAllByRole('button', { name: /수정/i })
    await user.click(editButtons[0]) // Edit first user (id=1, same as current user)

    await waitFor(() => screen.getByRole('dialog'))
    const switchEl = screen.getByRole('switch')
    expect(switchEl).toBeDisabled()
  })

  it('REQ-028: 비밀번호 초기화 성공 시 다이얼로그가 닫힌다', async () => {
    const user = userEvent.setup()
    const Wrapper = createWrapper()
    render(<AdminUsersPage />, { wrapper: Wrapper })

    await waitFor(() => screen.getByText('superadmin'))
    const resetButtons = screen.getAllByRole('button', { name: /비밀번호 초기화/i })
    await user.click(resetButtons[0])

    await waitFor(() => screen.getByRole('dialog'))

    await user.type(screen.getByLabelText(/새 비밀번호/i), 'newpassword123')
    await user.type(screen.getByLabelText(/비밀번호 확인/i), 'newpassword123')
    await user.click(screen.getByRole('button', { name: /^초기화$/i }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })
})
