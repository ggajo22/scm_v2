import { createBrowserRouter } from 'react-router-dom'
import { ProtectedRoute } from './ProtectedRoute'
import { PublicRoute } from './PublicRoute'
import { SuperAdminRoute } from './SuperAdminRoute'
import { LoginPage } from '@/features/auth/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ForbiddenPage } from '@/pages/ForbiddenPage'
import { AppLayout } from '@/components/AppLayout'

export const router = createBrowserRouter([
  {
    // Public routes — redirect to / if already authenticated
    element: <PublicRoute />,
    children: [
      {
        path: '/login',
        element: <LoginPage />,
      },
    ],
  },
  {
    // Protected routes — redirect to /login if not authenticated
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: '/',
            element: <DashboardPage />,
          },
          {
            // Super admin only routes
            element: <SuperAdminRoute />,
            children: [
              {
                path: '/admin-users',
                lazy: async () => {
                  const { AdminUsersPage } = await import('@/features/admin-users/AdminUsersPage')
                  return { Component: AdminUsersPage }
                },
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: '/403',
    element: <ForbiddenPage />,
  },
  {
    path: '*',
    element: <div className="p-6 text-center">페이지를 찾을 수 없습니다 (404)</div>,
  },
])
