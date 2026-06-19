import { RouterProvider } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useEffect } from 'react'
import { router } from './router'
import { queryClient } from './lib/queryClient'
import { useAuthStore } from './store/authStore'
import { setupInterceptors } from './lib/axios'

function AppInner() {
  const restoreSession = useAuthStore((state) => state.restoreSession)

  useEffect(() => {
    // Setup interceptors at the root level so they are active before any route renders
    setupInterceptors(
      () => useAuthStore.getState().accessToken,
      () => useAuthStore.getState().refreshToken(),
      () => useAuthStore.getState().logout(),
    )
    // REQ-008/REQ-030: Restore session before ProtectedRoute evaluates auth state
    restoreSession()
  }, [restoreSession])

  return (
    <>
      <RouterProvider router={router} />
      <Toaster position="top-right" />
    </>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}

export default App
