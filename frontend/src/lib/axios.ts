import axios from 'axios'
import { toast } from 'sonner'

export const REFRESH_TOKEN_KEY = 'scm_refresh_token'
export const BASE_URL = 'http://localhost:8000'

// @MX:ANCHOR: [AUTO] Central axios instance used by all API calls in the app
// @MX:REASON: Fan-in >= 3 — authStore, admin-users hooks, and all feature modules use this instance
export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Queue management for concurrent 401 responses
let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token!)
    }
  })
  failedQueue = []
}

// @MX:WARN: [AUTO] Interceptor mutates module-level state (isRefreshing, failedQueue)
// @MX:REASON: Concurrent 401 handling requires shared refresh state; guard with isRefreshing flag
export const setupInterceptors = (
  getAccessToken: () => string | null,
  refreshTokenFn: () => Promise<boolean>,
  logoutFn: () => Promise<void>
) => {
  // Request interceptor: attach access token
  const requestInterceptor = api.interceptors.request.use(
    (config) => {
      const token = getAccessToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // Response interceptor: handle 401 with token refresh
  const responseInterceptor = api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config

      if (error.response?.status !== 401 || originalRequest._retry) {
        return Promise.reject(error)
      }

      // Skip refresh for auth endpoints themselves
      if (
        originalRequest.url?.includes('/api/auth/login/') ||
        originalRequest.url?.includes('/api/auth/token/refresh/')
      ) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              resolve(api(originalRequest))
            },
            reject,
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const success = await refreshTokenFn()
        if (!success) {
          processQueue(new Error('Refresh failed'))
          await logoutFn()
          toast.error('세션이 만료되었습니다. 다시 로그인해 주세요.', { duration: 3000 })
          return Promise.reject(error)
        }

        // Get fresh token from store
        const { useAuthStore } = await import('@/store/authStore')
        const newToken = useAuthStore.getState().accessToken
        processQueue(null, newToken)

        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError)
        await logoutFn()
        toast.error('세션이 만료되었습니다. 다시 로그인해 주세요.', { duration: 3000 })
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
  )

  return { requestInterceptor, responseInterceptor }
}

// Export for testing
export const getIsRefreshing = () => isRefreshing
export const getFailedQueueLength = () => failedQueue.length
export const resetInterceptorState = () => {
  isRefreshing = false
  failedQueue = []
}
