import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { DashboardMetrics } from '@/types/book'

export const DASHBOARD_METRICS_QUERY_KEY = ['dashboard', 'metrics']

export function useDashboardMetrics() {
  return useQuery<DashboardMetrics>({
    queryKey: DASHBOARD_METRICS_QUERY_KEY,
    queryFn: async () => {
      const response = await api.get('/api/book/dashboard/metrics/')
      return response.data
    },
  })
}
