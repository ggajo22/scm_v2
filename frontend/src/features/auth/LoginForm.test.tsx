import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { LoginForm } from './LoginForm'
import { useAuthStore } from '@/store/authStore'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/store/authStore')

const mockLogin = vi.fn()
const mockUseAuthStore = vi.mocked(useAuthStore)

// Selector-aware mock
const buildSelectorMock = () => {
  const state = {
    accessToken: null,
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: mockLogin,
    logout: vi.fn(),
    refreshToken: vi.fn(),
    restoreSession: vi.fn(),
  }
  return (selector?: (s: typeof state) => unknown) => {
    if (typeof selector === 'function') return selector(state)
    return state
  }
}

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuthStore.mockImplementation(buildSelectorMock() as typeof useAuthStore)
  })

  const renderLoginForm = () =>
    render(
      <MemoryRouter>
        <LoginForm />
      </MemoryRouter>
    )

  it('REQ-001: 로그인 폼이 username, password, submit 버튼을 렌더링한다', () => {
    renderLoginForm()
    expect(screen.getByLabelText(/사용자명/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/비밀번호/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /로그인/i })).toBeInTheDocument()
  })

  it('REQ-002: 빈 필드로 제출 시 인라인 에러를 표시한다', async () => {
    const user = userEvent.setup()
    renderLoginForm()

    await user.click(screen.getByRole('button', { name: /로그인/i }))

    await waitFor(() => {
      expect(screen.getByText(/사용자명을 입력해주세요/i)).toBeInTheDocument()
      expect(screen.getByText(/비밀번호를 입력해주세요/i)).toBeInTheDocument()
    })
  })

  it('REQ-003: 제출 중 버튼이 disabled되고 로딩 인디케이터가 표시된다', async () => {
    const user = userEvent.setup()
    let resolveLogin: (v: void) => void
    mockLogin.mockReturnValueOnce(
      new Promise<void>((resolve) => {
        resolveLogin = resolve
      })
    )
    renderLoginForm()

    await user.type(screen.getByLabelText(/사용자명/i), 'admin')
    await user.type(screen.getByLabelText(/비밀번호/i), 'password123')
    await user.click(screen.getByRole('button', { name: /로그인/i }))

    await waitFor(() => {
      const button = screen.getByRole('button', { name: /로그인 중/i })
      expect(button).toBeDisabled()
    })

    resolveLogin!()
  })

  it('REQ-004: 로그인 성공 시 / 로 리다이렉트한다', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValueOnce(undefined)
    renderLoginForm()

    await user.type(screen.getByLabelText(/사용자명/i), 'admin')
    await user.type(screen.getByLabelText(/비밀번호/i), 'password123')
    await user.click(screen.getByRole('button', { name: /로그인/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
    })
  })

  it('REQ-005: 로그인 실패 시 에러 메시지를 표시한다', async () => {
    const user = userEvent.setup()
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))
    renderLoginForm()

    await user.type(screen.getByLabelText(/사용자명/i), 'wrong')
    await user.type(screen.getByLabelText(/비밀번호/i), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /로그인/i }))

    await waitFor(() => {
      expect(
        screen.getByText(/아이디 또는 비밀번호가 올바르지 않습니다/i)
      ).toBeInTheDocument()
    })
  })
})
