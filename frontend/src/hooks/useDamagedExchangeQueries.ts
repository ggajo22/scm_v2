import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  searchDamagedExchangeCandidates,
  submitDamagedExchange,
} from '@/services/damagedExchangeApi'

// ---------------------------------------------------------------------------
// SPEC-PURCHASE-ORDER-011: damaged-exchange search + submission hooks
// ---------------------------------------------------------------------------

export const DAMAGED_EXCHANGE_SEARCH_QUERY_KEY = ['damaged-exchange-search']

// REQ-DEX-004: fetched only once a search has been submitted — `enabled`
// gate mirrors RackNumberPage/tabs/SearchTab.tsx's submittedSearch pattern,
// never firing on every keystroke.
export function useSearchDamagedExchange(sku: string | null) {
  return useQuery({
    queryKey: [...DAMAGED_EXCHANGE_SEARCH_QUERY_KEY, sku],
    queryFn: () => searchDamagedExchangeCandidates(sku ?? ''),
    enabled: sku !== null && sku !== '',
  })
}

// REQ-DEX-009/009b: a resubmission for a LineItem already at
// "damaged_exchange" overwrites damaged_quantity server-side — the client
// just re-fires the same mutation; the query invalidation below refreshes
// the row's badge/value from the server response.
export function useSubmitDamagedExchange() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, damagedQuantity }: { id: number; damagedQuantity: number }) =>
      submitDamagedExchange(id, damagedQuantity),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DAMAGED_EXCHANGE_SEARCH_QUERY_KEY })
      toast.success('파손 수량이 접수되었습니다.')
    },
    onError: () => {
      toast.error('파손 접수에 실패했습니다.')
    },
  })
}
