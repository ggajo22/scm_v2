// SPEC-SHOPIFY-INFO-001: TanStack Query hook for real-time Shopify product info
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { ShopifyLiveInfoResponse } from '@/types/book'

export function useShopifyLiveInfo(id: number | undefined) {
  return useQuery<ShopifyLiveInfoResponse>({
    queryKey: ['book', 'shopify-live-info', id],
    queryFn: async () => {
      const res = await api.get<ShopifyLiveInfoResponse>(`/api/book/${id}/shopify-live-info/`)
      return res.data
    },
    enabled: id !== undefined,
    retry: 1,
  })
}
