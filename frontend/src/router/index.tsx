import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './ProtectedRoute'
import { PublicRoute } from './PublicRoute'
import { SuperAdminRoute } from './SuperAdminRoute'
import { LoginPage } from '@/features/auth/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ForbiddenPage } from '@/pages/ForbiddenPage'
import { AppLayout } from '@/components/AppLayout'
import { BookLayout } from '@/features/book/BookLayout'

export const router = createBrowserRouter([
  {
    element: <PublicRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: '/',
            element: <Navigate to="/books" replace />,
          },
          {
            path: '/books',
            element: <BookLayout />,
            children: [
              {
                index: true,
                element: <DashboardPage />,
              },
              {
                path: 'search',
                lazy: async () => {
                  const { BookSearchPage } = await import('@/pages/BookSearchPage')
                  return { Component: BookSearchPage }
                },
              },
              {
                path: 'add-isbn',
                lazy: async () => {
                  const { AddIsbnPage } = await import('@/pages/AddIsbnPage')
                  return { Component: AddIsbnPage }
                },
              },
              {
                path: 'fast-listing',
                lazy: async () => {
                  const { FastListingPage } = await import('@/pages/FastListingPage')
                  return { Component: FastListingPage }
                },
              },
              {
                path: 'etoile',
                lazy: async () => {
                  const { EtoileDashboardPage } = await import('@/pages/EtoileDashboardPage')
                  return { Component: EtoileDashboardPage }
                },
              },
              {
                path: ':id',
                lazy: async () => {
                  const { BookDetailPage } = await import('@/pages/BookDetailPage')
                  return { Component: BookDetailPage }
                },
              },
            ],
          },
          {
            path: '/orders',
            lazy: async () => {
              const { OrdersPage } = await import('@/pages/OrdersPage')
              return { Component: OrdersPage }
            },
          },
          {
            path: '/orders/notes',
            lazy: async () => {
              const { OrderNotesPage } = await import('@/pages/OrderNotesPage')
              return { Component: OrderNotesPage }
            },
          },
          {
            path: '/orders/:id',
            lazy: async () => {
              const { OrderDetailPage } = await import('@/pages/OrderDetailPage')
              return { Component: OrderDetailPage }
            },
          },
          {
            path: '/purchase-orders',
            lazy: async () => {
              const { PurchaseOrdersPage } = await import('@/pages/PurchaseOrders')
              return { Component: PurchaseOrdersPage }
            },
          },
          {
            path: '/warehouse',
            lazy: async () => {
              const { WarehouseStockPage } = await import('@/pages/WarehouseStockPage')
              return { Component: WarehouseStockPage }
            },
          },
          {
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
  { path: '/403', element: <ForbiddenPage /> },
  { path: '*', element: <div className="p-6 text-center">페이지를 찾을 수 없습니다 (404)</div> },
])
