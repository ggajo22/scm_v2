import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/axios'

interface EtoileAddIsbnRequest {
  skus: string[]
}

export interface EtoileAddIsbnResult {
  book_created_skus: string[]
  etoile_created_new_book_skus: string[]
  etoile_created_existing_book_skus: string[]
  etoile_existing_skus: string[]
  book_created_count: number
  etoile_created_new_book_count: number
  etoile_created_existing_book_count: number
  etoile_existing_count: number
}

export function useEtoileAddIsbn() {
  return useMutation<EtoileAddIsbnResult, Error, EtoileAddIsbnRequest>({
    mutationFn: async (payload) => {
      const res = await api.post('/api/book/etoile-inven-skus/', payload)
      return res.data
    },
  })
}
