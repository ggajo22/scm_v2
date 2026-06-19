import { create } from 'zustand'
import { api, REFRESH_TOKEN_KEY } from '@/lib/axios'
import type { User, LoginCredentials } from '@/types/auth'

// @MX:ANCHOR: [AUTO] Global auth state — all components read from this store
// @MX:REASON: Fan-in >= 3 — ProtectedRoute, PublicRoute, Sidebar, axios interceptors all read this state

interface AuthState {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean

  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<boolean>
  restoreSession: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,
  isLoading: true, // Start true — restoreSession runs before ProtectedRoute evaluates

  login: async (credentials: LoginCredentials) => {
    const response = await api.post('/api/auth/login/', credentials)
    const { access, refresh, user } = response.data

    // Store accessToken in memory only — never localStorage
    set({
      accessToken: access,
      user,
      isAuthenticated: true,
    })

    // Store refreshToken in localStorage
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },

  logout: async () => {
    const { accessToken } = get()

    // Attempt server logout — but always clear client state
    try {
      if (accessToken) {
        await api.post('/api/auth/logout/', null, {
          headers: { Authorization: `Bearer ${accessToken}` },
        })
      }
    } catch {
      // REQ-007: Ignore server logout failures — client logout must succeed
    } finally {
      set({
        accessToken: null,
        user: null,
        isAuthenticated: false,
      })
      localStorage.removeItem(REFRESH_TOKEN_KEY)
    }
  },

  refreshToken: async (): Promise<boolean> => {
    const storedRefresh = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (!storedRefresh) {
      return false
    }

    try {
      const response = await api.post('/api/auth/token/refresh/', {
        refresh: storedRefresh,
      })
      const { access } = response.data

      set({ accessToken: access, isAuthenticated: true })
      return true
    } catch {
      localStorage.removeItem(REFRESH_TOKEN_KEY)
      return false
    }
  },

  restoreSession: async () => {
    set({ isLoading: true })
    try {
      const storedRefresh = localStorage.getItem(REFRESH_TOKEN_KEY)
      if (!storedRefresh) {
        set({ isLoading: false, isAuthenticated: false })
        return
      }

      const success = await get().refreshToken()
      if (!success) {
        set({ isAuthenticated: false })
      }
    } finally {
      set({ isLoading: false })
    }
  },
}))
