import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { BookDetail } from '@/types/book'

// @MX:ANCHOR: [AUTO] Central query hook for book detail — used by BookDetailPage and all mutation hooks
// @MX:REASON: queryKey ['book', 'detail', id] is the cache key invalidated by every mutation in useBookMutations
export function useBookDetail(id: number | undefined) {
  return useQuery<BookDetail>({
    queryKey: ['book', 'detail', id],
    queryFn: async () => {
      const res = await api.get(`/api/book/${id}/`)
      return res.data
    },
    enabled: id !== undefined,
  })
}
