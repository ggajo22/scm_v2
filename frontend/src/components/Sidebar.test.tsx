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

// Groups collapse by default, so a test that asserts on a sub-item must open its
// group first. Renders, then expands the named group unless it is already open
// (the group holding initialPath starts expanded).
const renderAndExpand = async (
  groupLabel: string,
  role: 'super_admin' | 'admin' = 'super_admin',
  initialPath = '/books'
) => {
  const user = userEvent.setup()
  renderSidebar(role, initialPath)
  const header = screen.getByRole('button', { name: groupLabel })
  if (header.getAttribute('aria-expanded') === 'false') {
    await user.click(header)
  }
  return user
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
    it('/books/123 경로에서 어떤 하위 항목도 aria-current를 가지지 않는다', async () => {
      await renderAndExpand('도서관리', 'super_admin', '/books/123')
      expect(screen.getByRole('link', { name: '대시보드' })).not.toHaveAttribute('aria-current')
      expect(screen.getByRole('link', { name: 'ISBN 추가' })).not.toHaveAttribute('aria-current')
    })
  })

  describe('REQ-ETD-009: Etoile 현황 하위 항목 (SPEC-ETOILE-DASHBOARD-001)', () => {
    it('"Etoile 현황" 링크가 /books/etoile 경로로 렌더링된다', () => {
      renderSidebar()
      const link = screen.getByRole('link', { name: 'Etoile 현황' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/books/etoile')
    })

    it('/books/etoile 경로에서 "Etoile 현황" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/books/etoile')
      expect(screen.getByRole('link', { name: 'Etoile 현황' })).toHaveAttribute('aria-current', 'page')
    })

    it('/books/etoile 경로에서 "대시보드"는 aria-current를 가지지 않는다', () => {
      renderSidebar('super_admin', '/books/etoile')
      expect(screen.getByRole('link', { name: '대시보드' })).not.toHaveAttribute('aria-current')
    })
  })

  describe('REQ-EIA-018: Etoile ISBN 추가 하위 항목 (SPEC-ETOILE-INVEN-ADD-001)', () => {
    it('"Etoile ISBN 추가" 링크가 /books/etoile-add-isbn 경로로 렌더링된다', () => {
      renderSidebar()
      const link = screen.getByRole('link', { name: 'Etoile ISBN 추가' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/books/etoile-add-isbn')
    })

    it('/books/etoile-add-isbn 경로에서 "Etoile ISBN 추가" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/books/etoile-add-isbn')
      expect(screen.getByRole('link', { name: 'Etoile ISBN 추가' })).toHaveAttribute(
        'aria-current',
        'page'
      )
    })

    it('/books/etoile-add-isbn 경로에서 "Etoile 현황"은 aria-current를 가지지 않는다', () => {
      renderSidebar('super_admin', '/books/etoile-add-isbn')
      expect(screen.getByRole('link', { name: 'Etoile 현황' })).not.toHaveAttribute('aria-current')
    })
  })

  describe('REQ-FLA-012: 빠른 리스팅 하위 항목 (SPEC-FAST-LISTING-ADD-001)', () => {
    it('"빠른 리스팅" 링크가 /books/fast-listing 경로로 렌더링된다', () => {
      renderSidebar()
      const link = screen.getByRole('link', { name: '빠른 리스팅' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/books/fast-listing')
    })

    it('/books/fast-listing 경로에서 "빠른 리스팅" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/books/fast-listing')
      expect(screen.getByRole('link', { name: '빠른 리스팅' })).toHaveAttribute('aria-current', 'page')
    })

    it('/books/fast-listing 경로에서 "대시보드"는 aria-current를 가지지 않는다', () => {
      renderSidebar('super_admin', '/books/fast-listing')
      expect(screen.getByRole('link', { name: '대시보드' })).not.toHaveAttribute('aria-current')
    })
  })

  describe('SPEC-ORDER-013 REQ-RACK-008: 렉번호 관리 내비게이션 항목', () => {
    it('"렉번호 관리" 링크가 /rack-number 경로로 렌더링된다', async () => {
      await renderAndExpand('한국창고')
      const link = screen.getByRole('link', { name: '렉번호 관리' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/rack-number')
    })

    it('/rack-number 경로에서 "렉번호 관리" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/rack-number')
      expect(screen.getByRole('link', { name: '렉번호 관리' })).toHaveAttribute('aria-current', 'page')
    })
  })

  describe('입고 처리 내비게이션 항목 (PurchaseOrders 탭에서 승격)', () => {
    it('"입고 처리" 링크가 /inbound 경로로 렌더링된다', async () => {
      await renderAndExpand('한국창고')
      const link = screen.getByRole('link', { name: '입고 처리' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/inbound')
    })

    it('/inbound 경로에서 "입고 처리" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/inbound')
      expect(screen.getByRole('link', { name: '입고 처리' })).toHaveAttribute('aria-current', 'page')
    })

    it('admin 역할에게도 "입고 처리" 항목이 보인다 (역할 제한 없음)', async () => {
      await renderAndExpand('한국창고', 'admin')
      expect(screen.getByRole('link', { name: '입고 처리' })).toBeInTheDocument()
    })
  })

  describe('SPEC-ORDER-015 REQ-OUTBOUND-015: 출고 처리 내비게이션 항목', () => {
    it('AC-OUTBOUND-017: "출고 처리" 링크가 /outbound 경로로 렌더링된다', async () => {
      await renderAndExpand('한국창고')
      const link = screen.getByRole('link', { name: '출고 처리' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/outbound')
    })

    it('/outbound 경로에서 "출고 처리" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/outbound')
      expect(screen.getByRole('link', { name: '출고 처리' })).toHaveAttribute('aria-current', 'page')
    })

    it('/outbound 경로에서 "렉번호 관리" 링크는 aria-current를 가지지 않는다', () => {
      renderSidebar('super_admin', '/outbound')
      expect(screen.getByRole('link', { name: '렉번호 관리' })).not.toHaveAttribute('aria-current')
    })

    it('admin 역할에게도 "출고 처리" 항목이 보인다 (역할 제한 없음)', async () => {
      await renderAndExpand('한국창고', 'admin')
      expect(screen.getByRole('link', { name: '출고 처리' })).toBeInTheDocument()
    })
  })

  describe('SPEC-PURCHASE-ORDER-011 REQ-DEX-003: 파손 교환 내비게이션 항목', () => {
    it('"파손 교환" 링크가 /damaged-exchange 경로로 렌더링된다', async () => {
      await renderAndExpand('한국창고')
      const link = screen.getByRole('link', { name: '파손 교환' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', '/damaged-exchange')
    })

    it('/damaged-exchange 경로에서 "파손 교환" 링크가 aria-current="page"를 가진다', () => {
      renderSidebar('super_admin', '/damaged-exchange')
      expect(screen.getByRole('link', { name: '파손 교환' })).toHaveAttribute('aria-current', 'page')
    })

    it('admin 역할에게도 "파손 교환" 항목이 보인다 (역할 제한 없음)', async () => {
      await renderAndExpand('한국창고', 'admin')
      expect(screen.getByRole('link', { name: '파손 교환' })).toBeInTheDocument()
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
    it('현재 경로(/books)가 속한 도서관리 그룹은 펼쳐진 상태로 시작한다', () => {
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
      expect(screen.queryByRole('link', { name: '빠른 리스팅' })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Etoile 현황' })).not.toBeInTheDocument()
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

  describe('네비게이션 그룹 개편', () => {
    it('4개 그룹 헤더가 모두 렌더링된다', () => {
      renderSidebar()
      expect(screen.getByRole('group', { name: '도서관리' })).toBeInTheDocument()
      expect(screen.getByRole('group', { name: '주문관리' })).toBeInTheDocument()
      expect(screen.getByRole('group', { name: '발주 & CS' })).toBeInTheDocument()
      expect(screen.getByRole('group', { name: '한국창고' })).toBeInTheDocument()
    })

    it('"주문 목록"과 "고객 메모"가 주문관리 그룹에 속한다', async () => {
      await renderAndExpand('주문관리')
      const group = screen.getByRole('group', { name: '주문관리' })
      const orders = screen.getByRole('link', { name: '주문 목록' })
      const notes = screen.getByRole('link', { name: '고객 메모' })
      expect(orders).toHaveAttribute('href', '/orders')
      expect(notes).toHaveAttribute('href', '/orders/notes')
      expect(group).toContainElement(orders)
      expect(group).toContainElement(notes)
    })

    it('"미해결 메모" 라벨은 더 이상 존재하지 않는다', () => {
      renderSidebar()
      expect(screen.queryByText('미해결 메모')).not.toBeInTheDocument()
    })

    it('"품목 노트"가 발주 & CS 그룹에 속한다', async () => {
      await renderAndExpand('발주 & CS')
      const group = screen.getByRole('group', { name: '발주 & CS' })
      const link = screen.getByRole('link', { name: '품목 노트' })
      expect(link).toHaveAttribute('href', '/line-item-notes')
      expect(group).toContainElement(link)
    })

    it('"SKU 세트 매핑"이 발주 & CS 그룹에 속한다', async () => {
      await renderAndExpand('발주 & CS')
      const group = screen.getByRole('group', { name: '발주 & CS' })
      expect(group).toContainElement(screen.getByRole('link', { name: 'SKU 세트 매핑' }))
    })

    it('창고 현장 항목 4개가 한국창고 그룹에 속한다', async () => {
      await renderAndExpand('한국창고')
      const group = screen.getByRole('group', { name: '한국창고' })
      for (const label of ['렉번호 관리', '입고 처리', '출고 처리', '파손 교환']) {
        expect(group).toContainElement(screen.getByRole('link', { name: label }))
      }
    })

    it('"관리자 계정 관리"는 그룹에 속하지 않는 평면 항목이다', () => {
      renderSidebar('super_admin')
      const link = screen.getByRole('link', { name: '관리자 계정 관리' })
      expect(link).toHaveAttribute('href', '/admin-users')
      for (const groupLabel of ['도서관리', '주문관리', '발주 & CS', '한국창고']) {
        expect(screen.getByRole('group', { name: groupLabel })).not.toContainElement(link)
      }
    })
  })

  describe('그룹별 독립 접기', () => {
    it('현재 경로가 속하지 않은 그룹은 기본적으로 접혀 있다', () => {
      renderSidebar('super_admin', '/books')
      for (const label of ['주문관리', '발주 & CS', '한국창고']) {
        expect(screen.getByRole('button', { name: label })).toHaveAttribute('aria-expanded', 'false')
      }
      expect(screen.queryByRole('link', { name: '주문 목록' })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: '입고 처리' })).not.toBeInTheDocument()
    })

    it('어떤 그룹에도 속하지 않는 경로에서는 모든 그룹이 접혀 있다', () => {
      renderSidebar('super_admin', '/orders/123')
      for (const label of ['도서관리', '주문관리', '발주 & CS', '한국창고']) {
        expect(screen.getByRole('button', { name: label })).toHaveAttribute('aria-expanded', 'false')
      }
    })

    it('한 그룹을 펼쳐도 다른 그룹은 접힌 상태를 유지한다', async () => {
      const user = userEvent.setup()
      renderSidebar('super_admin', '/books')
      await user.click(screen.getByRole('button', { name: '한국창고' }))

      expect(screen.getByRole('link', { name: '입고 처리' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '발주 & CS' })).toHaveAttribute('aria-expanded', 'false')
      expect(screen.queryByRole('link', { name: '품목 노트' })).not.toBeInTheDocument()
      // 현재 경로가 속한 도서관리는 그대로 열려 있다
      expect(screen.getByRole('link', { name: '대시보드' })).toBeInTheDocument()
    })

    it('현재 경로가 속한 그룹만 펼쳐진 상태로 렌더링된다', () => {
      renderSidebar('super_admin', '/outbound')
      expect(screen.getByRole('button', { name: '한국창고' })).toHaveAttribute('aria-expanded', 'true')
      expect(screen.getByRole('link', { name: '출고 처리' })).toHaveAttribute('aria-current', 'page')
      expect(screen.getByRole('button', { name: '도서관리' })).toHaveAttribute('aria-expanded', 'false')
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
