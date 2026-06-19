import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act } from '@testing-library/react'
import { useAuthStore } from './authStore'
import { REFRESH_TOKEN_KEY } from '@/lib/axios'

// Mock axios module
vi.mock('@/lib/axios', async () => {
  const actual = await vi.importActual('@/lib/axios')
  return {
    ...actual,
    api: {
      post: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    },
    setupInterceptors: vi.fn(),
  }
})

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    })
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('REQ-004: 로그인 성공 시 accessToken을 메모리에, refreshToken을 localStorage에 저장한다', async () => {
      const { api } = await import('@/lib/axios')
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access: 'test-access-token',
          refresh: 'test-refresh-token',
          user: { id: 1, username: 'admin', role: 'super_admin', is_active: true },
        },
      })

      await act(async () => {
        await useAuthStore.getState().login({ username: 'admin', password: 'password' })
      })

      const state = useAuthStore.getState()
      expect(state.accessToken).toBe('test-access-token')
      expect(state.isAuthenticated).toBe(true)
      expect(state.user?.username).toBe('admin')
      expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('test-refresh-token')
    })

    it('REQ-004: accessToken은 절대 localStorage에 저장하지 않는다', async () => {
      const { api } = await import('@/lib/axios')
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          access: 'secret-token',
          refresh: 'refresh-token',
          user: { id: 1, username: 'admin', role: 'super_admin', is_active: true },
        },
      })

      await act(async () => {
        await useAuthStore.getState().login({ username: 'admin', password: 'password' })
      })

      // Access token must not be in localStorage
      expect(localStorage.getItem('secret-token')).toBeNull()
      const allKeys = Object.keys(localStorage)
      allKeys.forEach((key) => {
        expect(localStorage.getItem(key)).not.toBe('secret-token')
      })
    })

    it('REQ-005: 로그인 실패 시 에러를 throw한다', async () => {
      const { api } = await import('@/lib/axios')
      vi.mocked(api.post).mockRejectedValueOnce({
        response: { status: 401, data: { detail: 'Invalid credentials' } },
      })

      await expect(
        useAuthStore.getState().login({ username: 'wrong', password: 'wrong' })
      ).rejects.toBeTruthy()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.accessToken).toBeNull()
    })
  })

  describe('logout', () => {
    beforeEach(async () => {
      useAuthStore.setState({
        accessToken: 'test-token',
        user: { id: 1, username: 'admin', role: 'super_admin', is_active: true },
        isAuthenticated: true,
        isLoading: false,
      })
      localStorage.setItem(REFRESH_TOKEN_KEY, 'test-refresh-token')
    })

    it('REQ-006: 로그아웃 시 상태를 초기화하고 localStorage를 클리어한다', async () => {
      const { api } = await import('@/lib/axios')
      vi.mocked(api.post).mockResolvedValueOnce({ data: { detail: 'Logged out successfully.' } })

      await act(async () => {
        await useAuthStore.getState().logout()
      })

      const state = useAuthStore.getState()
      expect(state.accessToken).toBeNull()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull()
    })

    it('REQ-007: 로그아웃 API 실패해도 클라이언트 로그아웃은 성공한다', async () => {
      const { api } = await import('@/lib/axios')
      vi.mocked(api.post).mockRejectedValueOnce(new Error('Network error'))

      await act(async () => {
        await useAuthStore.getState().logout()
      })

      const state = useAuthStore.getState()
      expect(state.accessToken).toBeNull()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull()
    })
  })

  describe('refreshToken', () => {
    it('REQ-010: refresh 성공 시 새 accessToken을 업데이트하고 true 반환', async () => {
      localStorage.setItem(REFRESH_TOKEN_KEY, 'valid-refresh-token')
      const { api } = await import('@/lib/axios')
      vi.mocked(api.post).mockResolvedValueOnce({
        data: { access: 'new-access-token' },
      })

      let result: boolean
      await act(async () => {
        result = await useAuthStore.getState().refreshToken()
      })

      expect(result!).toBe(true)
      expect(useAuthStore.getState().accessToken).toBe('new-access-token')
    })

    it('REQ-009: refreshToken 없으면 false 반환', async () => {
      let result: boolean
      await act(async () => {
        result = await useAuthStore.getState().refreshToken()
      })

      expect(result!).toBe(false)
    })

    it('REQ-011: refresh API 401 실패 시 false 반환', async () => {
      localStorage.setItem(REFRESH_TOKEN_KEY, 'expired-refresh-token')
      const { api } = await import('@/lib/axios')
      vi.mocked(api.post).mockRejectedValueOnce({
        response: { status: 401 },
      })

      let result: boolean
      await act(async () => {
        result = await useAuthStore.getState().refreshToken()
      })

      expect(result!).toBe(false)
    })
  })

  describe('restoreSession', () => {
    it('REQ-008: localStorage에 refreshToken 있으면 세션을 복원한다', async () => {
      localStorage.setItem(REFRESH_TOKEN_KEY, 'valid-refresh-token')
      const { api } = await import('@/lib/axios')
      vi.mocked(api.post).mockResolvedValueOnce({
        data: { access: 'restored-access-token' },
      })

      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      const state = useAuthStore.getState()
      expect(state.accessToken).toBe('restored-access-token')
      expect(state.isAuthenticated).toBe(true)
      expect(state.isLoading).toBe(false)
    })

    it('REQ-009: localStorage에 refreshToken 없으면 비인증 상태로 설정', async () => {
      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
    })

    it('REQ-030: restoreSession 중에는 isLoading이 true이다', async () => {
      localStorage.setItem(REFRESH_TOKEN_KEY, 'valid-refresh-token')
      const { api } = await import('@/lib/axios')

      let loadingDuringRestore = false
      vi.mocked(api.post).mockImplementationOnce(() => {
        loadingDuringRestore = useAuthStore.getState().isLoading
        return Promise.resolve({ data: { access: 'token' } })
      })

      await act(async () => {
        await useAuthStore.getState().restoreSession()
      })

      expect(loadingDuringRestore).toBe(true)
      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })
})
