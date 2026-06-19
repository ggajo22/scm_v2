import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export function PublicRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  // REQ-013: Authenticated users accessing public routes get redirected to home
  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
