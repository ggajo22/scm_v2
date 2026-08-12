import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  processOutboundManual,
  uploadOutbound,
  fetchOutboundForceCandidates,
  processOutboundForce,
} from '@/services/outboundApi'
import type { OutboundProcessResponse, OutboundForceCandidateGroup } from '@/services/outboundApi'
import { ORDER_DETAIL_QUERY_KEY } from '@/features/order/hooks/useOrderDetail'

// ---------------------------------------------------------------------------
// SPEC-ORDER-015: outbound processing mutation hooks (REQ-OUTBOUND-016)
// ---------------------------------------------------------------------------

// REQ-OUTBOUND-014/017: a single toast line covering all three response
// categories — the page renders the per-item detail, the toast only has to
// tell the user at a glance whether anything needs attention.
export function buildOutboundSummary(result: OutboundProcessResponse): string {
  return `출고 처리 완료: 성공 ${result.matched_count}건, 매칭 실패 ${result.unmatched_count}건, 수량초과 ${result.quantity_exceeded_count}건`
}

// Outbound writes shipped_quantity/shipped_at/logistics_status on LineItems,
// so any order-detail view already in cache is stale afterwards.
function useOutboundMutation<TVars>(
  mutationFn: (vars: TVars) => Promise<OutboundProcessResponse>,
  errorMessage: string
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })
      toast.success(buildOutboundSummary(result))
    },
    onError: () => {
      toast.error(errorMessage)
    },
  })
}

// REQ-OUTBOUND-011/016: manual bulk entry submit.
export function useProcessOutboundManual() {
  return useOutboundMutation(processOutboundManual, '출고 처리에 실패했습니다.')
}

// REQ-OUTBOUND-013/016: Excel upload submit. A header the backend parser
// cannot resolve comes back as HTTP 422 and lands in onError.
export function useUploadOutbound() {
  return useOutboundMutation(uploadOutbound, '출고 파일 업로드에 실패했습니다.')
}

// ---------------------------------------------------------------------------
// SPEC-ORDER-016: force outbound processing (REQ-FORCE-003/015/016)
// ---------------------------------------------------------------------------

export const OUTBOUND_FORCE_CANDIDATES_QUERY_KEY = ['outbound-force-candidates']

// REQ-FORCE-003: fetches candidates once for the full batch of eligible
// rows' order names — the caller (OutboundPage) recomputes `orderNames`
// only when the settled unmatched result changes, never per row and never
// on picker open. Disabled while the set is empty so an empty page (or a
// page with zero eligible rows) issues no request. Parameterised query key
// style (frontend/src/features/order/hooks/useOrders.ts), not the
// parameterless style in useRackNumberQueries.ts.
export function useOutboundForceCandidates(orderNames: string[]) {
  return useQuery<OutboundForceCandidateGroup[]>({
    queryKey: [...OUTBOUND_FORCE_CANDIDATES_QUERY_KEY, orderNames],
    queryFn: () => fetchOutboundForceCandidates(orderNames),
    enabled: orderNames.length > 0,
  })
}

// REQ-FORCE-015/016: bulk force-execute mutation. Reuses the shared
// `useOutboundMutation` factory — it requires `Promise<OutboundProcessResponse>`,
// which matches REQ-FORCE-016's "reuse the existing 3-category contract
// verbatim" — so cache invalidation, the fixed Korean error toast and the
// success-summary toast all follow the same convention as the two existing
// submit paths above.
export function useProcessOutboundForce() {
  return useOutboundMutation(processOutboundForce, '강제 출고 처리에 실패했습니다.')
}
