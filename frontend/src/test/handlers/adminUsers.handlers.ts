import { http, HttpResponse } from 'msw'

export const adminUsersHandlers = [
  http.get('http://localhost:8000/api/admin/users/', () =>
    HttpResponse.json([
      { id: 1, username: 'superadmin', role: 'super_admin', is_active: true, date_joined: '2024-01-01' },
      { id: 2, username: 'admin1', role: 'admin', is_active: true, date_joined: '2024-01-02' },
    ])
  ),
  http.post('http://localhost:8000/api/admin/users/', () =>
    HttpResponse.json(
      { id: 3, username: 'newadmin', role: 'admin', is_active: true, date_joined: '2024-01-03' },
      { status: 201 }
    )
  ),
  http.patch('http://localhost:8000/api/admin/users/:id/', ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      username: 'updated',
      role: 'admin',
      is_active: true,
      date_joined: '2024-01-01',
    })
  ),
  http.post('http://localhost:8000/api/admin/users/:id/reset-password/', () =>
    HttpResponse.json({ detail: 'Password reset successfully.' })
  ),
]
