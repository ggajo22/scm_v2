import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { FullScreenSpinner } from '@/components/FullScreenSpinner'

// @MX:ANCHOR: [AUTO] Guards all authenticated routes — critical access control boundary
// @MX:REASON: Fan-in >= 3 — wraps Dashboard, AdminUsers, and all future protected pages
export function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isLoading = useAuthStore((state) => state.isLoading)

  // REQ-030: Show spinner during session restore — do not redirect yet
  if (isLoading) {
    return <FullScreenSpinner />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
