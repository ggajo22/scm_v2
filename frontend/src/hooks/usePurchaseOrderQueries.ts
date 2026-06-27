import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  getUnorderedItems,
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
} from '@/services/purchaseOrderApi'
import type { PurchaseOrderParams } from '@/services/purchaseOrderApi'

// @MX:ANCHOR: [AUTO] Centralized query keys for purchase order domain
// @MX:REASON: Fan-in >= 3 — all tabs reference these keys for cache invalidation

export const QUERY_KEYS = {
  unordered: ['purchase-orders', 'unordered'] as const,
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
