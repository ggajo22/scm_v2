import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/axios'

interface FastListingRequest {
  skus: string[]
}

export interface FastListingResult {
  created: string[]
  updated: string[]
  skipped: string[]
  created_count: number
  updated_count: number
  skipped_count: number
}

export function useFastListingSku() {
  return useMutation<FastListingResult, Error, FastListingRequest>({
    mutationFn: async (payload) => {
      const res = await api.post('/api/book/fast-listing-skus/', payload)
      return res.data
    },
  })
}
