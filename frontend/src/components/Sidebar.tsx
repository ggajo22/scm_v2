import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Users, LogOut, BookOpen } from 'lucide-react'
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

const bookGroup: NavGroup = {
  label: '도서관리',
  icon: BookOpen,
  items: [
    { label: '대시보드', href: '/books' },
    { label: 'ISBN 추가', href: '/books/add-isbn' },
  ],
}

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
          {/* REQ-001: 도서관리 그룹 헤더 (non-clickable, REQ-010: role=group + aria-label) */}
          <li>
            <div role="group" aria-label={bookGroup.label}>
              <div className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-muted-foreground select-none">
                <bookGroup.icon className="h-4 w-4" aria-hidden="true" />
                {bookGroup.label}
              </div>
              {/* REQ-002, REQ-003: sub-items; REQ-004, REQ-005, REQ-006: exact-match active state */}
              <ul className="space-y-1">
                {bookGroup.items.map((subItem) => {
                  const isActive = location.pathname === subItem.href
                  return (
                    <li key={subItem.href}>
                      <Link
                        to={subItem.href}
                        aria-current={isActive ? 'page' : undefined}
                        className={cn(
                          // REQ-009: pl-9 indents sub-items relative to group header (pl-3)
                          'flex items-center rounded-md pl-9 pr-3 py-2 text-sm transition-colors',
                          'hover:bg-accent hover:text-accent-foreground',
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
            </div>
          </li>

          {/* REQ-007, REQ-008: 관리자 계정 관리 — top-level flat item, super_admin only */}
          {visibleFlatItems.map((item) => (
            <li key={item.href}>
              <Link
                to={item.href}
                aria-current={location.pathname === item.href ? 'page' : undefined}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
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
