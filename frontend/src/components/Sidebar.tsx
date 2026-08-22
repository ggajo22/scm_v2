import { useEffect, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Users, LogOut, BookOpen, ChevronDown, ShoppingCart, Package, Warehouse } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

interface SubNavItem {
  label: string
  href: string
}

interface NavGroup {
  label: string
  icon: React.ComponentType<{ className?: string }>
  items: SubNavItem[]
}

interface FlatNavItem {
  label: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  roles?: Array<'super_admin' | 'admin'>
}

// Nav is grouped by the team that owns the work, matching the assignee axis
// already used by 품목 노트 (CS / 발주 / 한국창고 / 미국창고). Keeping the two
// vocabularies aligned means a new operator learns the sidebar for free.
const navGroups: NavGroup[] = [
  {
    label: '도서관리',
    icon: BookOpen,
    items: [
      { label: '대시보드', href: '/books' },
      { label: 'ISBN 추가', href: '/books/add-isbn' },
      { label: '빠른 리스팅', href: '/books/fast-listing' },
      { label: 'Etoile 현황', href: '/books/etoile' },
      // SPEC-ETOILE-INVEN-ADD-001
      { label: 'Etoile ISBN 추가', href: '/books/etoile-add-isbn' },
    ],
  },
  {
    label: '주문관리',
    icon: ShoppingCart,
    items: [
      { label: '주문 목록', href: '/orders' },
      // Renamed from "미해결 메모" — the page is the customer-facing note queue,
      // and "미해결" described a filter state rather than the subject matter.
      { label: '고객 메모', href: '/orders/notes' },
    ],
  },
  {
    label: '발주 & CS',
    icon: Package,
    items: [
      { label: '발주 관리', href: '/purchase-orders' },
      { label: '창고 재고', href: '/warehouse' },
      { label: 'SKU 세트 매핑', href: '/settings/sku-sets' },
      { label: '품목 노트', href: '/line-item-notes' },
    ],
  },
  {
    // Warehouse-floor flow reads in physical order: 렉번호 → 입고 → 출고 → 파손 교환.
    // 파손 교환 (SPEC-PURCHASE-ORDER-011 REQ-DEX-003) stays last because damage is
    // discovered during the outbound workflow that precedes it.
    label: '한국창고',
    icon: Warehouse,
    items: [
      { label: '렉번호 관리', href: '/rack-number' },
      { label: '입고 처리', href: '/inbound' },
      // SPEC-ORDER-015 REQ-OUTBOUND-015
      { label: '출고 처리', href: '/outbound' },
      { label: '파손 교환', href: '/damaged-exchange' },
    ],
  },
]

const flatNavItems: FlatNavItem[] = [
  {
    label: '관리자 계정 관리',
    href: '/admin-users',
    icon: Users,
    // REQ-014(SPEC-AUTH-001): Only visible to super_admin role
    roles: ['super_admin'],
  },
]

export function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const activeGroupLabel = navGroups.find((group) =>
    group.items.some((item) => item.href === location.pathname)
  )?.label

  // Only the group holding the current page starts open; the rest stay collapsed
  // so the sidebar shows 5 rows instead of 17 at rest.
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(navGroups.map((group) => [group.label, group.label === activeGroupLabel]))
  )

  // Navigating into a collapsed group re-opens it, so the active page is never
  // hidden behind a closed header. A manual collapse of the group you are
  // already in still sticks — the effect only fires when the active group changes.
  useEffect(() => {
    if (!activeGroupLabel) return
    setOpenGroups((prev) =>
      prev[activeGroupLabel] ? prev : { ...prev, [activeGroupLabel]: true }
    )
  }, [activeGroupLabel])

  const toggleGroup = (label: string) =>
    setOpenGroups((prev) => ({ ...prev, [label]: !prev[label] }))

  const visibleFlatItems = flatNavItems.filter((item) => {
    if (!item.roles) return true
    return item.roles.includes(user?.role as 'super_admin' | 'admin')
  })

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <aside
      className="w-64 h-full bg-card border-r flex flex-col"
      aria-label="사이드바 내비게이션"
    >
      <div className="p-4 border-b">
        <h2 className="font-semibold text-lg">SCM v2</h2>
        {user && (
          <p className="text-xs text-muted-foreground mt-1">
            {user.username} ({user.role === 'super_admin' ? '최고관리자' : '관리자'})
          </p>
        )}
      </div>

      <nav className="flex-1 p-4" aria-label="메인 내비게이션">
        <ul className="space-y-1" role="list">
          {/* REQ-001, REQ-010: 그룹 헤더 — 토글 가능, role=group + aria-label */}
          {navGroups.map((group) => {
            const isOpen = openGroups[group.label]
            return (
              <li key={group.label}>
                <div role="group" aria-label={group.label}>
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.label)}
                    aria-expanded={isOpen}
                    className={cn(
                      'w-full flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground',
                      'cursor-pointer hover:bg-gray-100 hover:text-gray-900 transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                    )}
                  >
                    <group.icon className="h-4 w-4" aria-hidden="true" />
                    <span className="flex-1 text-left">{group.label}</span>
                    <ChevronDown
                      className={cn('h-3.5 w-3.5 transition-transform duration-200', !isOpen && '-rotate-90')}
                      aria-hidden="true"
                    />
                  </button>
                  {/* REQ-002, REQ-003: sub-items; REQ-004, REQ-005, REQ-006: exact-match active state */}
                  {isOpen && (
                    <ul className="space-y-1 mt-0.5">
                      {group.items.map((subItem) => {
                        const isActive = location.pathname === subItem.href
                        return (
                          <li key={subItem.href}>
                            <Link
                              to={subItem.href}
                              aria-current={isActive ? 'page' : undefined}
                              className={cn(
                                // REQ-009: pl-9 indents sub-items relative to group header (pl-3)
                                'flex items-center rounded-md pl-9 pr-3 py-2 text-sm transition-colors',
                                'hover:bg-gray-100 hover:text-gray-900',
                                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                                isActive && 'bg-accent text-accent-foreground font-medium'
                              )}
                            >
                              {subItem.label}
                            </Link>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              </li>
            )
          })}

          {/* REQ-007, REQ-008: 관리자 계정 관리 — top-level flat item, super_admin only */}
          {visibleFlatItems.map((item) => (
            <li key={item.href}>
              <Link
                to={item.href}
                aria-current={location.pathname === item.href ? 'page' : undefined}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                  'hover:bg-gray-100 hover:text-gray-900',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  location.pathname === item.href && 'bg-accent text-accent-foreground font-medium'
                )}
              >
                <item.icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="p-4 border-t">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3"
          onClick={handleLogout}
          aria-label="로그아웃"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          로그아웃
        </Button>
      </div>
    </aside>
  )
}
