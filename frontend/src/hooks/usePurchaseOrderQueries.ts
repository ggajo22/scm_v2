import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  getUnorderedItems,
  getExcludedItems,
  generateOrderFile,
  uploadVendorFile,
  getVendorRules,
  createVendorRule,
  deleteVendorRule,
  getPurchaseOrders,
  updateLineItemStatus,
  bulkUpdateLineItemStatus,
  downloadDailyReview,
  uploadDailyReview,
  updateLineItemLogisticsStatus,
  bulkUpdateLineItemLogisticsStatus,
  uploadVendorShipment,
  uploadWarehouseReceipt,
} from '@/services/purchaseOrderApi'
import type { PurchaseOrderParams } from '@/services/purchaseOrderApi'
import { ORDER_DETAIL_QUERY_KEY } from '@/features/order/hooks/useOrderDetail'

// @MX:ANCHOR: [AUTO] Centralized query keys for purchase order domain
// @MX:REASON: Fan-in >= 3 — all tabs reference these keys for cache invalidation

export const QUERY_KEYS = {
  unordered: ['purchase-orders', 'unordered'] as const,
  // SPEC-ORDER-018: shares the 'purchase-orders' prefix with `unordered` but
  // is a distinct key, so the two lists invalidate independently.
  excludedItems: ['purchase-orders', 'excluded-items'] as const,
  purchaseOrders: (params?: PurchaseOrderParams) =>
    ['purchase-orders', 'list', params ?? {}] as const,
  vendorRules: ['purchase-orders', 'vendor-rules'] as const,
}

export function useUnorderedItems() {
  return useQuery({
    queryKey: QUERY_KEYS.unordered,
    queryFn: getUnorderedItems,
  })
}

// SPEC-ORDER-018 REQ-RESTORE-001: read-only list of the four excluded
// purchase statuses, backing the 보류/제외 품목 view in UnorderedItemsTab.
export function useExcludedItems() {
  return useQuery({
    queryKey: QUERY_KEYS.excludedItems,
    queryFn: getExcludedItems,
  })
}

export function usePurchaseOrders(params?: PurchaseOrderParams) {
  return useQuery({
    queryKey: QUERY_KEYS.purchaseOrders(params),
    queryFn: () => getPurchaseOrders(params),
  })
}

export function useVendorRules() {
  return useQuery({
    queryKey: QUERY_KEYS.vendorRules,
    queryFn: getVendorRules,
  })
}

export function useGenerateOrderFile() {
  return useMutation({
    mutationFn: generateOrderFile,
    onError: () => {
      toast.error('발주 파일 생성에 실패했습니다.')
    },
  })
}

export function useUploadVendorFile() {
  return useMutation({
    mutationFn: uploadVendorFile,
    onSuccess: () => {
      toast.success('업체 자료가 업로드되었습니다.')
    },
    onError: () => {
      toast.error('파일 업로드에 실패했습니다.')
    },
  })
}

export function useCreateVendorRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createVendorRule,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.vendorRules })
      toast.success('발주처 규칙이 추가되었습니다.')
    },
    onError: () => {
      toast.error('규칙 추가에 실패했습니다.')
    },
  })
}

export function useDeleteVendorRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteVendorRule,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.vendorRules })
      toast.success('발주처 규칙이 삭제되었습니다.')
    },
    onError: () => {
      toast.error('규칙 삭제에 실패했습니다.')
    },
  })
}

export function useUpdateLineItemStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, purchaseStatus }: { id: number; purchaseStatus: string }) =>
      updateLineItemStatus(id, purchaseStatus),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.unordered })
      // SPEC-ORDER-018 REQ-RESTORE-021: both directions need this — moving an
      // item to on_hold must make it appear in the excluded list, and
      // restoring it must make it leave.
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.excludedItems })
    },
    onError: () => {
      toast.error('상태 변경에 실패했습니다.')
    },
  })
}

// @MX:WARN: [AUTO] bulkUpdateLineItemStatus mutates multiple line items atomically
// @MX:REASON: Partial success (missing_ids) must be surfaced to the user to avoid silent data loss
export function useBulkUpdateLineItemStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ids, purchaseStatus }: { ids: number[]; purchaseStatus: string }) =>
      bulkUpdateLineItemStatus(ids, purchaseStatus),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.unordered })
      // SPEC-ORDER-018 REQ-RESTORE-021: see useUpdateLineItemStatus above.
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.excludedItems })
      if (result.missing_ids.length > 0) {
        toast.warning(`일부 항목(${result.missing_ids.length}건)이 업데이트되지 않았습니다.`)
      } else {
        toast.success(`${result.updated_count}건의 상태가 변경되었습니다.`)
      }
    },
    onError: () => {
      toast.error('일괄 상태 변경에 실패했습니다.')
    },
  })
}

export function useDownloadDailyReview() {
  return useMutation({
    mutationFn: downloadDailyReview,
    onSuccess: (blob) => {
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Daily_Order_Review_${today}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Daily Review 파일이 다운로드되었습니다.')
    },
    onError: () => {
      toast.error('다운로드에 실패했습니다.')
    },
  })
}

export function useUploadDailyReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadDailyReview,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.unordered })
      void queryClient.invalidateQueries({ queryKey: ['purchase-orders', 'list'] })
      toast.success(`발주 확정 완료: ${result.confirmed_count ?? 0}건 처리, ${result.skipped_count ?? 0}건 건너뜀`)
    },
    onError: () => {
      toast.error('파일 업로드에 실패했습니다.')
    },
  })
}

// ---------------------------------------------------------------------------
// SPEC-ORDER-011 T11: logistics_status hooks
// ---------------------------------------------------------------------------

export function useUpdateLineItemLogisticsStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, logisticsStatus }: { id: number; logisticsStatus: string }) =>
      updateLineItemLogisticsStatus(id, logisticsStatus),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })
    },
    onError: () => {
      toast.error('물류 상태 변경에 실패했습니다.')
    },
  })
}

// @MX:WARN: [AUTO] bulkUpdateLineItemLogisticsStatus mutates multiple line items atomically
// @MX:REASON: Partial success (missing_ids) must be surfaced to the user to avoid silent data loss
export function useBulkUpdateLineItemLogisticsStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ids, logisticsStatus }: { ids: number[]; logisticsStatus: string }) =>
      bulkUpdateLineItemLogisticsStatus(ids, logisticsStatus),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })
      if (result.missing_ids.length > 0) {
        toast.warning(`일부 항목(${result.missing_ids.length}건)이 업데이트되지 않았습니다.`)
      } else {
        toast.success(`${result.updated_count}건의 물류 상태가 변경되었습니다.`)
      }
    },
    onError: () => {
      toast.error('일괄 물류 상태 변경에 실패했습니다.')
    },
  })
}

export function useUploadVendorShipment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadVendorShipment,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })
      toast.success(`벤더 출고확인 처리 완료: ${result.matched_count}건 매칭, ${result.skipped_count}건 건너뜀`)
    },
    onError: () => {
      toast.error('벤더 출고확인 파일 업로드에 실패했습니다.')
    },
  })
}

export function useUploadWarehouseReceipt() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadWarehouseReceipt,
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })
      toast.success(`창고 입고결과 처리 완료: ${result.matched_count}건 매칭, ${result.skipped_count}건 건너뜀`)
    },
    onError: () => {
      toast.error('창고 입고결과 파일 업로드에 실패했습니다.')
    },
  })
}
