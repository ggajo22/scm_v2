import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { OrderDetail } from '@/types/order'

export const ORDER_DETAIL_QUERY_KEY = ['order-detail']

// @MX:ANCHOR: [AUTO] useOrderDetail — called from OrderDetailPage (fan_in will grow with refund/edit pages)
// @MX:REASON: Single fetch point for order detail; cache key must stay stable for invalidation
export function useOrderDetail(id: number) {
  return useQuery<OrderDetail>({
    queryKey: [...ORDER_DETAIL_QUERY_KEY, id],
    queryFn: async () => {
      const res = await api.get(`/api/orders/${id}/`)
      return res.data
    },
  })
}
