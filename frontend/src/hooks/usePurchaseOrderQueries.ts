import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  getUnorderedItems,
  generateOrderFile,
  uploadVendorFile,
  getComparison,
  confirmOrder,
  getVendorRules,
  createVendorRule,
  deleteVendorRule,
  getPurchaseOrders,
} from '@/services/purchaseOrderApi'
import type { PurchaseOrderParams } from '@/services/purchaseOrderApi'

// @MX:ANCHOR: [AUTO] Centralized query keys for purchase order domain
// @MX:REASON: Fan-in >= 3 — all tabs reference these keys for cache invalidation

export const QUERY_KEYS = {
  unordered: ['purchase-orders', 'unordered'] as const,
  comparison: ['purchase-orders', 'comparison'] as const,
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

export function useComparison() {
  return useQuery({
    queryKey: QUERY_KEYS.comparison,
    queryFn: getComparison,
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
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadVendorFile,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.comparison })
      toast.success('업체 자료가 업로드되었습니다.')
    },
    onError: () => {
      toast.error('파일 업로드에 실패했습니다.')
    },
  })
}

// @MX:WARN: [AUTO] confirmOrder mutates multiple query caches on success
// @MX:REASON: Invalidates both unordered and purchase-orders queries — ordering matters for UX consistency

export function useConfirmOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: confirmOrder,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.unordered })
      void queryClient.invalidateQueries({ queryKey: ['purchase-orders', 'list'] })
      toast.success('발주가 확정되었습니다.')
    },
    onError: () => {
      toast.error('발주 확정에 실패했습니다.')
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
