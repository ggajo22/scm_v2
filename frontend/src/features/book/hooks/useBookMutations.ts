import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/axios'
import type { BookInfo, BookNote } from '@/types/book'

// @MX:ANCHOR: [AUTO] All book mutation hooks share this invalidation target
// @MX:REASON: Every mutation must invalidate ['book', 'detail', bookId] to keep BookDetailPage in sync

type InfoPatch = Partial<Omit<BookInfo, 'id' | 'updated_at'>>

export function useUpdateBookInfo(bookId: number) {
  const queryClient = useQueryClient()
  return useMutation<BookInfo, Error, InfoPatch>({
    mutationFn: async (payload) => {
      const res = await api.patch(`/api/book/${bookId}/info/`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book', 'detail', bookId] })
      toast.success('저장되었습니다.')
    },
    onError: () => {
      toast.error('저장에 실패했습니다.')
    },
  })
}

export function useAddNote(bookId: number) {
  const queryClient = useQueryClient()
  return useMutation<BookNote, Error, { note_type: 'GENERAL' | 'SHIPPING'; content: string }>({
    mutationFn: async (payload) => {
      const res = await api.post(`/api/book/${bookId}/notes/`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book', 'detail', bookId] })
      toast.success('노트가 추가되었습니다.')
    },
    onError: () => {
      toast.error('노트 추가에 실패했습니다.')
    },
  })
}

export function useResolveNote(bookId: number) {
  const queryClient = useQueryClient()
  return useMutation<{ id: number; is_resolved: boolean; resolved_at: string }, Error, number>({
    mutationFn: async (noteId) => {
      const res = await api.patch(`/api/book/notes/${noteId}/resolve/`)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book', 'detail', bookId] })
      toast.success('노트가 해결되었습니다.')
    },
    onError: () => {
      toast.error('노트 해결에 실패했습니다.')
    },
  })
}

export function useUpdateShopifyStatus(bookId: number) {
  const queryClient = useQueryClient()
  return useMutation<{ status_of_shopify: number; action: string }, Error, 'active' | 'draft'>({
    mutationFn: async (action) => {
      const res = await api.patch(`/api/book/${bookId}/shopify-status/`, { action })
      return res.data
    },
    onSuccess: (_data, action) => {
      queryClient.invalidateQueries({ queryKey: ['book', 'detail', bookId] })
      toast.success(`Shopify 상태가 ${action === 'active' ? '활성' : '드래프트'}로 변경되었습니다.`)
    },
    onError: () => {
      toast.error('Shopify 상태 변경에 실패했습니다.')
    },
  })
}

export function useUpdateEtoileShopifyStatus(bookId: number) {
  const queryClient = useQueryClient()
  return useMutation<{ status_of_shopify: number; action: string }, Error, 'active' | 'draft'>({
    mutationFn: async (action) => {
      const res = await api.patch(`/api/book/${bookId}/etoile-shopify-status/`, { action })
      return res.data
    },
    onSuccess: (_data, action) => {
      queryClient.invalidateQueries({ queryKey: ['book', 'detail', bookId] })
      toast.success(`에투알 Shopify 상태가 ${action === 'active' ? '활성' : '드래프트'}로 변경되었습니다.`)
    },
    onError: () => {
      toast.error('에투알 Shopify 상태 변경에 실패했습니다.')
    },
  })
}

export function useUpdateEtoileTags(bookId: number) {
  const queryClient = useQueryClient()
  return useMutation<{ tags: string[]; shopify_sync: 'success' | 'failed' }, Error, string[]>({
    mutationFn: async (tags) => {
      const res = await api.patch(`/api/book/${bookId}/etoile-tags/`, { tags })
      return res.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['book', 'detail', bookId] })
      if (data.shopify_sync === 'failed') {
        toast.warning('태그는 저장되었으나 Shopify 동기화에 실패했습니다.')
      } else {
        toast.success('태그가 저장되었습니다.')
      }
    },
    onError: () => {
      toast.error('태그 저장에 실패했습니다.')
    },
  })
}
