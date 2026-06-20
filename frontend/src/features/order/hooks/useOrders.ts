import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { OrderListParams, OrderListResponse } from '@/types/order'

export const ORDERS_QUERY_KEY = ['orders']

export function useOrders(params: OrderListParams = {}) {
  return useQuery<OrderListResponse>({
    queryKey: [...ORDERS_QUERY_KEY, params],
    queryFn: async () => {
      const searchParams: Record<string, string> = {}
      if (params.page && params.page > 1) searchParams.page = String(params.page)
      if (params.store_type) searchParams.store_type = params.store_type
      if (params.financial_status) searchParams.financial_status = params.financial_status
      if (params.fulfillment_status) searchParams.fulfillment_status = params.fulfillment_status
      if (params.date_from) searchParams.date_from = params.date_from
      if (params.date_to) searchParams.date_to = params.date_to

      const res = await api.get('/api/orders/', { params: searchParams })
      return res.data
    },
  })
}
