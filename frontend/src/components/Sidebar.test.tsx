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

const renderSidebar = (role: 'super_admin' | 'admin' = 'super_admin', initialPath = '/books') => {
  mockUseAuthStore.mockImplementation(buildSelectorMock(role) as typeof useAuthStore)
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Sidebar />
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('REQ-001: 도서관리 그룹 헤더', () => {
    it('인증된 사용자에게 "도서관리" 그룹 헤더를 표시한다', () => {
      renderSidebar()
      expect(screen.getByText('도서관리')).toBeInTheDocument()
    })
  })

  describe('REQ-002: 대시보드 하위 항목', () => {
    it('"대시보드" 링크가 /books 경로로 렌더링된다', () => {
      renderSidebar()
      const link = screen.getByRole('link', { name: '대시보드' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/books')
    })
  })

  describe('REQ-003: ISBN 추가 하위 항목', () => {
    it('"ISBN 추가" 링크가 /books/add-isbn 경로로 렌더링된다', () => {
      renderSidebar()
      const link = screen.getByRole('link', { name: 'ISBN 추가' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/books/add-isbn')
    })
  })

  describe('REQ-004: /books 경로에서 대시보드 활성 상태', () => {
    it('/books 경로에서 "대시보드" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/books')
      expect(screen.getByRole('link', { name: '대시보드' })).toHaveAttribute('aria-current', 'page')
    })

    it('/books 경로에서 "ISBN 추가" 링크는 aria-current를 가지지 않는다', () => {
      renderSidebar('super_admin', '/books')
      expect(screen.getByRole('link', { name: 'ISBN 추가' })).not.toHaveAttribute('aria-current')
    })
  })

  describe('REQ-005: /books/add-isbn 경로에서 ISBN 추가 활성 상태', () => {
    it('/books/add-isbn 경로에서 "ISBN 추가" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/books/add-isbn')
      expect(screen.getByRole('link', { name: 'ISBN 추가' })).toHaveAttribute('aria-current', 'page')
    })

    it('/books/add-isbn 경로에서 "대시보드" 링크는 aria-current를 가지지 않는다', () => {
      renderSidebar('super_admin', '/books/add-isbn')
      expect(screen.getByRole('link', { name: '대시보드' })).not.toHaveAttribute('aria-current')
    })
  })

  describe('REQ-006: 기타 /books/* 경로에서 비활성 상태', () => {
    it('/books/123 경로에서 어떤 하위 항목도 aria-current를 가지지 않는다', () => {
      renderSidebar('super_admin', '/books/123')
      expect(screen.getByRole('link', { name: '대시보드' })).not.toHaveAttribute('aria-current')
      expect(screen.getByRole('link', { name: 'ISBN 추가' })).not.toHaveAttribute('aria-current')
    })
  })

  describe('REQ-007 & REQ-008: 관리자 계정 관리 역할 기반 표시', () => {
    it('REQ-007: super_admin은 관리자 계정 관리 메뉴를 볼 수 있다', () => {
      renderSidebar('super_admin')
      expect(screen.getByText(/관리자 계정 관리/i)).toBeInTheDocument()
    })

    it('REQ-008: admin 역할은 관리자 계정 관리 메뉴를 볼 수 없다', () => {
      renderSidebar('admin')
      expect(screen.queryByText(/관리자 계정 관리/i)).not.toBeInTheDocument()
    })
  })

  describe('REQ-009: 하위 항목 들여쓰기', () => {
    it('하위 항목 링크는 그룹 헤더보다 더 들여쓰기된 구조로 렌더링된다', () => {
      renderSidebar()
      const group = screen.getByRole('group', { name: '도서관리' })
      const dashboardLink = screen.getByRole('link', { name: '대시보드' })
      expect(group).toContainElement(dashboardLink)
    })
  })

  describe('REQ-010: 그룹 헤더 접근성', () => {
    it('"도서관리" 그룹에 role="group" 및 aria-label="도서관리"가 적용된다', () => {
      renderSidebar()
      const group = screen.getByRole('group', { name: '도서관리' })
      expect(group).toBeInTheDocument()
      expect(group).toHaveAttribute('aria-label', '도서관리')
    })
  })

  describe('토글 동작', () => {
    it('기본적으로 하위 항목이 펼쳐져 있다', () => {
      renderSidebar()
      expect(screen.getByRole('link', { name: '대시보드' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'ISBN 추가' })).toBeInTheDocument()
    })

    it('그룹 헤더 클릭 시 하위 항목이 접힌다', async () => {
      const user = userEvent.setup()
      renderSidebar()
      await user.click(screen.getByRole('button', { name: /도서관리/i }))
      expect(screen.queryByRole('link', { name: '대시보드' })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'ISBN 추가' })).not.toBeInTheDocument()
    })

    it('접힌 상태에서 다시 클릭 시 하위 항목이 펼쳐진다', async () => {
      const user = userEvent.setup()
      renderSidebar()
      const toggleButton = screen.getByRole('button', { name: /도서관리/i })
      await user.click(toggleButton)
      await user.click(toggleButton)
      expect(screen.getByRole('link', { name: '대시보드' })).toBeInTheDocument()
    })

    it('펼쳐진 상태에서 aria-expanded="true"를 가진다', () => {
      renderSidebar()
      expect(screen.getByRole('button', { name: /도서관리/i })).toHaveAttribute('aria-expanded', 'true')
    })

    it('접힌 상태에서 aria-expanded="false"를 가진다', async () => {
      const user = userEvent.setup()
      renderSidebar()
      await user.click(screen.getByRole('button', { name: /도서관리/i }))
      expect(screen.getByRole('button', { name: /도서관리/i })).toHaveAttribute('aria-expanded', 'false')
    })
  })

  describe('로그아웃', () => {
    it('로그아웃 버튼 클릭 시 logout을 호출한다', async () => {
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
})
