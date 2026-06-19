import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

// @MX:ANCHOR: [AUTO] Guards super_admin-only routes
// @MX:REASON: Fan-in >= 3 — wraps AdminUsersPage and any future super_admin routes
export function SuperAdminRoute() {
  const user = useAuthStore((state) => state.user)

  // REQ-015: admin role trying to access super_admin routes → /403
  if (!user || user.role !== 'super_admin') {
    return <Navigate to="/403" replace />
  }

  return <Outlet />
}
