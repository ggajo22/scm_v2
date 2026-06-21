import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  bulkUpsertWarehouseStock,
  deleteWarehouseStockEntry,
  getWarehouseStock,
  upsertWarehouseStock,
} from '@/services/warehouseApi'
import type { WarehouseStockUpsertPayload } from '@/services/warehouseApi'

const QUERY_KEY = ['warehouse', 'stock'] as const

export function useWarehouseStock() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: getWarehouseStock,
  })
}

export function useUpsertWarehouseStock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: upsertWarehouseStock,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      toast.success('재고가 저장되었습니다.')
    },
    onError: () => {
      toast.error('재고 저장에 실패했습니다.')
    },
  })
}

export function useBulkUpsertWarehouseStock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (items: WarehouseStockUpsertPayload[]) => bulkUpsertWarehouseStock(items),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      toast.success(`${data.upserted_count}건 일괄 등록되었습니다.`)
    },
    onError: () => {
      toast.error('일괄 등록에 실패했습니다.')
    },
  })
}

export function useDeleteWarehouseStock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteWarehouseStockEntry,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      toast.success('재고가 삭제되었습니다.')
    },
    onError: () => {
      toast.error('재고 삭제에 실패했습니다.')
    },
  })
}
