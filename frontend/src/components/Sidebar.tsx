import { Link, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Users, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  roles?: Array<'super_admin' | 'admin'>
}

const navItems: NavItem[] = [
  {
    label: '대시보드',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    label: '관리자 계정 관리',
    href: '/admin-users',
    icon: Users,
    // REQ-014: Only visible to super_admin role
    roles: ['super_admin'],
  },
]

export function Sidebar() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const visibleItems = navItems.filter((item) => {
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
          {visibleItems.map((item) => (
            <li key={item.href}>
              <Link
                to={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
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
