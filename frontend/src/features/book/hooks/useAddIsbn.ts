import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/axios'

interface AddIsbnRequest {
  skus: string[]
}

export interface AddIsbnResult {
  created: string[]
  duplicates: string[]
  created_count: number
  duplicate_count: number
}

export function useAddIsbn() {
  return useMutation<AddIsbnResult, Error, AddIsbnRequest>({
    mutationFn: async (payload) => {
      const res = await api.post('/api/book/inven-skus/', payload)
      return res.data
    },
  })
}
