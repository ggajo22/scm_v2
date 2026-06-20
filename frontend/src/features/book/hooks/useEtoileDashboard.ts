import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { EtoileDashboard } from '@/types/book'

export const ETOILE_DASHBOARD_QUERY_KEY = ['etoile', 'dashboard']

export function useEtoileDashboard() {
  return useQuery<EtoileDashboard>({
    queryKey: ETOILE_DASHBOARD_QUERY_KEY,
    queryFn: async () => {
      const res = await api.get('/api/book/etoile/dashboard/')
      return res.data
    },
  })
}
