import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { OrderNote } from '@/types/order'

// @MX:ANCHOR: [AUTO] Query key for order notes — used by both useOrderNotes and useResolveNote
// @MX:REASON: Fan-in >= 3 — shared between query hook, mutation hook, and optimistic update rollback
export const ORDER_NOTES_QUERY_KEY = ['order-notes']

export function useOrderNotes() {
  return useQuery<OrderNote[]>({
    queryKey: ORDER_NOTES_QUERY_KEY,
    queryFn: async () => {
      const res = await api.get('/api/orders/notes/')
      return res.data
    },
  })
}

// @MX:WARN: [AUTO] Optimistic update with rollback — mutates query cache before server confirms
// @MX:REASON: onMutate cancels in-flight queries and modifies cache; rollback required in onError
export function useResolveNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (orderId: number) => {
      await api.patch(`/api/orders/${orderId}/resolve-note/`)
    },
    onMutate: async (orderId) => {
      // Optimistic update: remove from list immediately
      await queryClient.cancelQueries({ queryKey: ORDER_NOTES_QUERY_KEY })
      const previous = queryClient.getQueryData<OrderNote[]>(ORDER_NOTES_QUERY_KEY)
      queryClient.setQueryData<OrderNote[]>(
        ORDER_NOTES_QUERY_KEY,
        (old) => old?.filter((n) => n.id !== orderId) ?? [],
      )
      return { previous }
    },
    onError: (_err, _orderId, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(ORDER_NOTES_QUERY_KEY, context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ORDER_NOTES_QUERY_KEY })
    },
  })
}
