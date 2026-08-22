import { useState, useEffect } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { api } from '@/lib/axios'
import type { BookSearchResult, PaginatedResponse } from '@/types/book'

// REQ-SEARCH-009: debounce before hitting the API.
// ISBN used to be 0 ms on the theory that a SKU prefix scan is cheap. It is not:
// the paginator runs a COUNT next to every page query, and a 2-3 digit prefix
// matches ~620k of 631k rows. Hand-typing a 13-digit ISBN fired 12 requests
// (24 queries) and the only one that mattered — the full ISBN — queued behind
// the browser's 6-connection-per-host limit.
const DEBOUNCE_TEXT_MS = 300
const DEBOUNCE_ISBN_MS = 250
// REQ-SEARCH-010: no API call for <2 chars
const MIN_SEARCH_LENGTH = 2

function isISBN(q: string) {
  return /^\d+$/.test(q)
}

export function useBookSearch(query: string, page: number = 1) {
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  // REQ-SEARCH-009/010: both paths debounce, <2 chars → skip.
  // ISBN waits less than text because a scanner or paste arrives as one keystroke
  // and should not sit through the full text delay.
  useEffect(() => {
    if (query.length > 0 && query.length < MIN_SEARCH_LENGTH) {
      return
    }
    const delay = isISBN(query) ? DEBOUNCE_ISBN_MS : DEBOUNCE_TEXT_MS
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, delay)
    return () => clearTimeout(timer)
  }, [query])

  return useQuery<PaginatedResponse<BookSearchResult>>({
    queryKey: ['book', 'search', debouncedQuery, page],
    // signal aborts the previous request when the query key changes, so a
    // superseded prefix stops holding one of the six per-host connections
    queryFn: async ({ signal }) => {
      const params: Record<string, string | number> = { page }
      if (debouncedQuery) params.search = debouncedQuery
      const response = await api.get('/api/book/search/', { params, signal })
      return response.data
    },
    placeholderData: keepPreviousData,
    // Only fire when query is empty (show all) or has 2+ chars
    enabled: debouncedQuery.length === 0 || debouncedQuery.length >= MIN_SEARCH_LENGTH,
  })
}
