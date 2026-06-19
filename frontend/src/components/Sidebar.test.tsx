import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '@/store/authStore'

vi.mock('@/store/authStore')

const mockUseAuthStore = vi.mocked(useAuthStore)
const mockLogout = vi.fn()

// Selector-aware mock
const buildSelectorMock = (role: 'super_admin' | 'admin' = 'super_admin') => {
  const state = {
    accessToken: 'token',
    user: { id: 1, username: 'testuser', role, is_active: true },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: mockLogout,
    refreshToken: vi.fn(),
    restoreSession: vi.fn(),
  }
  return (selector?: (s: typeof state) => unknown) => {
    if (typeof selector === 'function') return selector(state)
    return state
  }
}

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('REQ-014: super_admin은 관리자 계정 관리 메뉴를 볼 수 있다', () => {
    mockUseAuthStore.mockImplementation(buildSelectorMock('super_admin') as typeof useAuthStore)

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText(/관리자 계정 관리/i)).toBeInTheDocument()
  })

  it('REQ-014: admin 역할은 관리자 계정 관리 메뉴를 볼 수 없다', () => {
    mockUseAuthStore.mockImplementation(buildSelectorMock('admin') as typeof useAuthStore)

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.queryByText(/관리자 계정 관리/i)).not.toBeInTheDocument()
  })

  it('REQ-006: 로그아웃 버튼 클릭 시 logout을 호출한다', async () => {
    const user = userEvent.setup()
    mockUseAuthStore.mockImplementation(buildSelectorMock('super_admin') as typeof useAuthStore)
    mockLogout.mockResolvedValueOnce(undefined)

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    await user.click(screen.getByRole('button', { name: /로그아웃/i }))

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledOnce()
    })
  })
})
