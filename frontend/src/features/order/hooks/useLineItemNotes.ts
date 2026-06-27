import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { LineItemNote, LineItemNoteUnresolved } from '@/types/order'

// @MX:ANCHOR: [AUTO] Query key for line item notes — shared between list, create, and resolve hooks
// @MX:REASON: Fan-in >= 3 — used by useLineItemNotes, useUnresolvedLineItemNotes, and useResolveLineItemNote rollback
export const LINE_ITEM_NOTES_QUERY_KEY = ['line-item-notes']

export function useLineItemNotes(lineItemId: number) {
  return useQuery<LineItemNote[]>({
    queryKey: [...LINE_ITEM_NOTES_QUERY_KEY, lineItemId],
    queryFn: async () => {
      const res = await api.get(`/api/orders/line-items/${lineItemId}/notes/`)
      return res.data
    },
  })
}

export function useCreateLineItemNote(lineItemId: number, orderId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { content: string; assignee: string; note_type?: string }) => {
      const res = await api.post(`/api/orders/line-items/${lineItemId}/notes/`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order-detail', orderId] })
      queryClient.invalidateQueries({ queryKey: LINE_ITEM_NOTES_QUERY_KEY })
    },
  })
}

// @MX:WARN: [AUTO] Optimistic update with rollback — mutates query cache before server confirms
// @MX:REASON: onMutate cancels in-flight queries and modifies cache; rollback required in onError
export function useResolveLineItemNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (noteId: number) => {
      await api.patch(`/api/orders/line-item-notes/${noteId}/resolve/`)
    },
    onMutate: async (noteId) => {
      await queryClient.cancelQueries({ queryKey: LINE_ITEM_NOTES_QUERY_KEY })
      const previous = queryClient.getQueryData<LineItemNoteUnresolved[]>(LINE_ITEM_NOTES_QUERY_KEY)
      queryClient.setQueryData<LineItemNoteUnresolved[]>(
        LINE_ITEM_NOTES_QUERY_KEY,
        (old) => old?.filter((n) => n.id !== noteId) ?? [],
      )
      return { previous }
    },
    onError: (_err, _noteId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(LINE_ITEM_NOTES_QUERY_KEY, context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: LINE_ITEM_NOTES_QUERY_KEY })
    },
  })
}

export function useUnresolvedLineItemNotes() {
  return useQuery<LineItemNoteUnresolved[]>({
    queryKey: LINE_ITEM_NOTES_QUERY_KEY,
    queryFn: async () => {
      const res = await api.get('/api/orders/line-item-notes/')
      return res.data
    },
  })
}
