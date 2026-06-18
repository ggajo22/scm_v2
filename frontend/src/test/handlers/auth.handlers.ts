import { http, HttpResponse } from 'msw'

export const authHandlers = [
  http.post('http://localhost:8000/api/auth/login/', () =>
    HttpResponse.json({
      access: 'test-access-token',
      refresh: 'test-refresh-token',
      user: {
        id: 1,
        username: 'superadmin',
        role: 'super_admin',
        is_active: true,
        date_joined: '2024-01-01',
      },
    })
  ),
  http.post('http://localhost:8000/api/auth/logout/', () =>
    HttpResponse.json({ detail: 'Logged out successfully.' })
  ),
  http.post('http://localhost:8000/api/auth/token/refresh/', () =>
    HttpResponse.json({ access: 'new-access-token' })
  ),
]
