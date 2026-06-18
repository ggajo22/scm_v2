import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

// @MX:ANCHOR: [AUTO] Root layout for all authenticated pages
// @MX:REASON: Fan-in >= 3 — wraps Dashboard, AdminUsersPage, and future authenticated pages
export function AppLayout() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" role="main">
        <Outlet />
      </main>
    </div>
  )
}
