import { useState, useEffect } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { BookSearchResult, PaginatedResponse } from '@/types/book'

// REQ-SEARCH-009: debounce 300ms for text, 0ms for ISBN (digits only)
const DEBOUNCE_TEXT_MS = 300
const DEBOUNCE_ISBN_MS = 0
// REQ-SEARCH-010: no API call for <2 chars
const MIN_SEARCH_LENGTH = 2

function isISBN(q: string) {
  return /^\d+$/.test(q)
}

export function useBookSearch(query: string, page: number = 1) {
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  // REQ-SEARCH-009/010: digits → immediate, text → 300ms debounce, <2 chars → skip
  useEffect(() => {
    if (query.length > 0 && query.length < MIN_SEARCH_LENGTH) {
      return
    }
    if (isISBN(query)) {
      setDebouncedQuery(query)
      return
    }
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, DEBOUNCE_TEXT_MS)
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
