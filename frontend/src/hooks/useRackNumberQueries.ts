import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  updateLineItemRackNumber,
  bulkUpdateLineItemRackNumber,
  uploadRackNumber,
  getRackNumberSummary,
} from '@/services/rackNumberApi'
import { ORDER_DETAIL_QUERY_KEY } from '@/features/order/hooks/useOrderDetail'

// ---------------------------------------------------------------------------
// SPEC-ORDER-013: rack_number management mutation hooks
// ---------------------------------------------------------------------------

// REQ-RACK-011: single-item PATCH, reflected via order-detail cache invalidation.
export function useUpdateLineItemRackNumber() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, rackNumber }: { id: number; rackNumber: string }) =>
      updateLineItemRackNumber(id, rackNumber),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })
    },
    onError: () => {
      toast.error('렉번호 변경에 실패했습니다.')
    },
  })
}

// @MX:WARN: [AUTO] bulkUpdateLineItemRackNumber mutates multiple line items atomically
// @MX:REASON: Partial success (missing_ids) must be surfaced to the user to avoid silent data loss
// REQ-RACK-010a: single bulk-PATCH request for all checked LineItem ids.
export function useBulkUpdateLineItemRackNumber() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ids, rackNumber }: { ids: number[]; rackNumber: string }) =>
      bulkUpdateLineItemRackNumber(ids, rackNumber),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })
      if (result.missing_ids.length > 0) {
        toast.warning(`일부 항목(${result.missing_ids.length}건)이 업데이트되지 않았습니다.`)
      } else {
        toast.success(`${result.updated_count}건의 렉번호가 변경되었습니다.`)
      }
    },
    onError: () => {
      toast.error('일괄 렉번호 변경에 실패했습니다.')
    },
  })
}

// REQ-RACK-006/007: 3-column Excel upload trigger.
export function useUploadRackNumber() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadRackNumber,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })
      toast.success(
        `렉번호 업로드 완료: ${result.matched_count}건 매칭, ${result.skipped_count}건 건너뜀`
      )
    },
    onError: () => {
      toast.error('렉번호 파일 업로드에 실패했습니다.')
    },
  })
}

// ---------------------------------------------------------------------------
// SPEC-ORDER-014: cross-order rack_number summary query hook (Tab2, read-only)
// ---------------------------------------------------------------------------

// REQ-RACKSUM-010: fetched once when the "렉번호 요약" tab mounts — no
// `enabled` flag needed since the tab-switcher only mounts SummaryTab when
// that tab is active (결정 F).
export function useRackNumberSummary() {
  return useQuery({
    queryKey: ['rack-number-summary'],
    queryFn: getRackNumberSummary,
  })
}
