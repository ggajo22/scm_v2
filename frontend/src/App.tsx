import { RouterProvider } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useEffect } from 'react'
import { router } from './router'
import { queryClient } from './lib/queryClient'
import { useAuthStore } from './store/authStore'
import { setupInterceptors } from './lib/axios'

// Interceptors are registered once at module load — outside React lifecycle.
// Placing this inside useEffect causes duplicate registration in React StrictMode
// (double-invoke in dev) which corrupts the 401 refresh queue.
setupInterceptors(
  () => useAuthStore.getState().accessToken,
  () => useAuthStore.getState().refreshToken(),
  () => useAuthStore.getState().logout(),
)

function AppInner() {
  const restoreSession = useAuthStore((state) => state.restoreSession)

  useEffect(() => {
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
