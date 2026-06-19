import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from './ProtectedRoute'
import { PublicRoute } from './PublicRoute'
import { SuperAdminRoute } from './SuperAdminRoute'
import { useAuthStore } from '@/store/authStore'

vi.mock('@/store/authStore')

const mockUseAuthStore = vi.mocked(useAuthStore)

// Selector-aware mock: useAuthStore(selector) → selector(state)
const buildSelectorMock = (stateOverrides = {}) => {
  const state = {
    accessToken: null,
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    restoreSession: vi.fn(),
    ...stateOverrides,
  }
  return (selector?: (s: typeof state) => unknown) => {
    if (typeof selector === 'function') return selector(state)
    return state
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ProtectedRoute', () => {
  it('REQ-012: 미인증 사용자를 /login으로 리다이렉트한다', () => {
    mockUseAuthStore.mockImplementation(buildSelectorMock() as typeof useAuthStore)

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<div>Dashboard</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
  })

  it('REQ-030: isLoading=true일 때 스피너를 표시하고 리다이렉트하지 않는다', () => {
    mockUseAuthStore.mockImplementation(
      buildSelectorMock({ isLoading: true }) as typeof useAuthStore
    )

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<div>Dashboard</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })

  it('인증된 사용자는 보호된 경로에 접근할 수 있다', () => {
    mockUseAuthStore.mockImplementation(
      buildSelectorMock({
        isAuthenticated: true,
        accessToken: 'token',
        user: { id: 1, username: 'admin', role: 'super_admin', is_active: true },
      }) as typeof useAuthStore
    )

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<div>Dashboard</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })
})

describe('PublicRoute', () => {
  it('REQ-013: 인증된 사용자가 /login 접근 시 /로 리다이렉트한다', () => {
    mockUseAuthStore.mockImplementation(
      buildSelectorMock({
        isAuthenticated: true,
        accessToken: 'token',
        user: { id: 1, username: 'admin', role: 'super_admin', is_active: true },
      }) as typeof useAuthStore
    )

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<div>Login Page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })

  it('미인증 사용자는 공개 경로에 접근할 수 있다', () => {
    mockUseAuthStore.mockImplementation(buildSelectorMock() as typeof useAuthStore)

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<div>Login Page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })
})

describe('SuperAdminRoute', () => {
  it('REQ-015: admin 역할 사용자가 /admin-users 접근 시 /403으로 리다이렉트한다', () => {
    mockUseAuthStore.mockImplementation(
      buildSelectorMock({
        isAuthenticated: true,
        accessToken: 'token',
        user: { id: 2, username: 'admin', role: 'admin', is_active: true },
      }) as typeof useAuthStore
    )

    render(
      <MemoryRouter initialEntries={['/admin-users']}>
        <Routes>
          <Route path="/403" element={<div>403 Forbidden</div>} />
          <Route element={<SuperAdminRoute />}>
            <Route path="/admin-users" element={<div>Admin Users</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('403 Forbidden')).toBeInTheDocument()
    expect(screen.queryByText('Admin Users')).not.toBeInTheDocument()
  })

  it('super_admin 역할 사용자는 /admin-users에 접근할 수 있다', () => {
    mockUseAuthStore.mockImplementation(
      buildSelectorMock({
        isAuthenticated: true,
        accessToken: 'token',
        user: { id: 1, username: 'superadmin', role: 'super_admin', is_active: true },
      }) as typeof useAuthStore
    )

    render(
      <MemoryRouter initialEntries={['/admin-users']}>
        <Routes>
          <Route path="/403" element={<div>403 Forbidden</div>} />
          <Route element={<SuperAdminRoute />}>
            <Route path="/admin-users" element={<div>Admin Users</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('Admin Users')).toBeInTheDocument()
  })
})
