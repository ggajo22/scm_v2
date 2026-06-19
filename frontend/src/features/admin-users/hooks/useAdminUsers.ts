import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { AdminUser, CreateAdminUserPayload, UpdateAdminUserPayload, ResetPasswordPayload } from '@/types/auth'

export const ADMIN_USERS_QUERY_KEY = ['admin-users']

export function useAdminUsers() {
  return useQuery<AdminUser[]>({
    queryKey: ADMIN_USERS_QUERY_KEY,
    queryFn: async () => {
      const response = await api.get('/api/admin/users/')
      return response.data
    },
  })
}

export function useCreateAdminUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateAdminUserPayload) => {
      const response = await api.post('/api/admin/users/', payload)
      return response.data as AdminUser
    },
    onSuccess: () => {
      // REQ-021: Invalidate cache on success
      queryClient.invalidateQueries({ queryKey: ADMIN_USERS_QUERY_KEY })
    },
  })
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateAdminUserPayload }) => {
      const response = await api.patch(`/api/admin/users/${id}/`, payload)
      return response.data as AdminUser
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMIN_USERS_QUERY_KEY })
    },
  })
}

export function useResetPassword() {
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: ResetPasswordPayload }) => {
      const response = await api.post(`/api/admin/users/${id}/reset-password/`, payload)
      return response.data
    },
  })
}
