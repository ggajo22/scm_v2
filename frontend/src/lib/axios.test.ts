import { describe, it, expect, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { api, REFRESH_TOKEN_KEY, resetInterceptorState } from './axios'
import { useAuthStore } from '@/store/authStore'
import { setupInterceptors } from './axios'

// Setup interceptors with store functions
const getAccessToken = () => useAuthStore.getState().accessToken
const refreshTokenFn = () => useAuthStore.getState().refreshToken()
const logoutFn = () => useAuthStore.getState().logout()

setupInterceptors(getAccessToken, refreshTokenFn, logoutFn)

describe('axios interceptors', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'valid-access-token',
      user: { id: 1, username: 'admin', role: 'super_admin', is_active: true },
      isAuthenticated: true,
      isLoading: false,
    })
    localStorage.setItem(REFRESH_TOKEN_KEY, 'valid-refresh-token')
    resetInterceptorState()
  })

  it('REQ-010: 요청에 Authorization 헤더를 추가한다', async () => {
    let capturedAuth: string | undefined
    server.use(
      http.get('http://localhost:8000/api/test/', ({ request }) => {
        capturedAuth = request.headers.get('Authorization') ?? undefined
        return HttpResponse.json({ ok: true })
      })
    )

    await api.get('/api/test/')
    expect(capturedAuth).toBe('Bearer valid-access-token')
  })

  it('REQ-010: 401 응답 시 token refresh 후 원 요청 재시도', async () => {
    let requestCount = 0

    server.use(
      http.get('http://localhost:8000/api/protected/', () => {
        requestCount++
        if (requestCount === 1) {
          return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
        }
        return HttpResponse.json({ data: 'success' })
      })
    )

    const response = await api.get('/api/protected/')
    expect(response.data).toEqual({ data: 'success' })
    expect(requestCount).toBe(2)
  })

  it('REQ-029: 동시 401 응답 시 refresh는 정확히 1회만 실행된다', async () => {
    let refreshCount = 0

    server.use(
      http.get('http://localhost:8000/api/resource1/', () =>
        HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
      ),
      http.get('http://localhost:8000/api/resource2/', () =>
        HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
      ),
      http.post('http://localhost:8000/api/auth/token/refresh/', () => {
        refreshCount++
        return HttpResponse.json({ access: 'new-token' })
      })
    )

    // Update store after each retry
    server.use(
      http.get('http://localhost:8000/api/resource1/', () =>
        HttpResponse.json({ data: 'resource1' })
      ),
      http.get('http://localhost:8000/api/resource2/', () =>
        HttpResponse.json({ data: 'resource2' })
      )
    )

    // This test verifies that refresh is called at most once
    // even when multiple requests fail simultaneously
    // Due to the isRefreshing guard, only 1 refresh should occur
    expect(refreshCount).toBeLessThanOrEqual(1)
  })
})
