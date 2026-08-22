import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import { useAuthStore } from '@/store/authStore'
import type { OrderSyncStatus } from '@/types/order'

export const ORDER_SYNC_STATUS_QUERY_KEY = ['order-sync-status']

// SPEC-ORDER-SYNC-HEALTH: the 5-minute scheduled Shopify sync has stopped
// silently before (102 orders lost). This surfaces when it last actually
// ran so a stopped sync is noticeable, not just decorative.
//
// Backend returns 403 for role 'admin' — `enabled` keeps the request from
// firing at all for non-super_admin so every orders page load doesn't
// generate a guaranteed 403. Refetches every 60s so an open page does not
// go stale while someone is looking at it.
export function useOrderSyncStatus() {
  const role = useAuthStore((state) => state.user?.role)

  return useQuery<OrderSyncStatus>({
    queryKey: ORDER_SYNC_STATUS_QUERY_KEY,
    queryFn: async () => {
      const res = await api.get('/api/orders/sync-status/')
      return res.data
    },
    enabled: role === 'super_admin',
    refetchInterval: 60_000,
  })
}
