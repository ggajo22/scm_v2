import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import { toast } from 'sonner'
import type { OrderSyncResponse } from '@/types/order'
import { ORDERS_QUERY_KEY } from './useOrders'

export function useOrderSync() {
  const queryClient = useQueryClient()

  return useMutation<OrderSyncResponse>({
    mutationFn: async () => {
      const res = await api.post('/api/orders/sync/')
      return res.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ORDERS_QUERY_KEY })
      if (data.status === 'completed') {
        toast.success(
          `동기화 완료 — 신규 ${data.total_synced}건, 업데이트 ${data.total_updated}건`
        )
      } else {
        const errors = Object.entries(data.stores)
          .filter(([, r]) => r.error)
          .map(([store, r]) => `${store}: ${r.error}`)
          .join(', ')
        toast.warning(`일부 스토어 동기화 실패 — ${errors}`)
      }
    },
    onError: () => {
      toast.error('동기화 중 오류가 발생했습니다.')
    },
  })
}
