import { useState, useEffect } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { BookSearchResult, PaginatedResponse } from '@/types/book'

// REQ-SEARCH-009: debounce 300ms
const DEBOUNCE_MS = 300
// REQ-SEARCH-010: no API call for <2 chars
const MIN_SEARCH_LENGTH = 2

export function useBookSearch(query: string, page: number = 1) {
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  // REQ-SEARCH-009/010: debounce — only update after 300ms, skip if <2 chars
  useEffect(() => {
    if (query.length > 0 && query.length < MIN_SEARCH_LENGTH) {
      // Too short — do not update debouncedQuery; no API call will fire
      return
    }
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [query])

  return useQuery<PaginatedResponse<BookSearchResult>>({
    queryKey: ['book', 'search', debouncedQuery, page],
    queryFn: async () => {
      const params: Record<string, string | number> = { page }
      if (debouncedQuery) params.search = debouncedQuery
      const response = await api.get('/api/book/search/', { params })
      return response.data
    },
    placeholderData: keepPreviousData,
    // Only fire when query is empty (show all) or has 2+ chars
    enabled: debouncedQuery.length === 0 || debouncedQuery.length >= MIN_SEARCH_LENGTH,
  })
}
