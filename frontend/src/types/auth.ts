export interface User {
  id: number
  username: string
  role: 'super_admin' | 'admin'
  is_active: boolean
  date_joined?: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface LoginResponse {
  access: string
  refresh: string
  user: User
}

export interface AdminUser {
  id: number
  username: string
  role: 'super_admin' | 'admin'
  is_active: boolean
  date_joined?: string
}

export interface CreateAdminUserPayload {
  username: string
  password: string
  role: 'super_admin' | 'admin'
}

export interface UpdateAdminUserPayload {
  username?: string
  role?: 'super_admin' | 'admin'
  is_active?: boolean
}

export interface ResetPasswordPayload {
  new_password: string
}
