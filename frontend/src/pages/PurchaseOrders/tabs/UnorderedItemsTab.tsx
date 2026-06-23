import { useState } from 'react'
import { toast } from 'sonner'
import { Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  useUnorderedItems,
  useGenerateOrderFile,
  useUpdateLineItemStatus,
  useBulkUpdateLineItemStatus,
} from '@/hooks/usePurchaseOrderQueries'
import { usePurchaseOrderStore } from '@/stores/usePurchaseOrderStore'
import { PURCHASE_STATUS_OPTIONS } from '@/services/purchaseOrderApi'
import type { WarningResponse } from '@/services/purchaseOrderApi'

// Helper: format Date as YYYYMMDD string
function formatDateCompact(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}${m}${d}`
}

// Helper: trigger browser file download from a Blob
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Helper: check if response is a warning (JSON) vs a Blob (file)
function isWarningResponse(value: Blob | WarningResponse): value is WarningResponse {
  return !!(value as WarningResponse).unknown_skus
}

export function UnorderedItemsTab() {
  const { data, isPending, isError } = useUnorderedItems()
  const generateMutation = useGenerateOrderFile()
  const statusMutation = useUpdateLineItemStatus()
  const bulkStatusMutation = useBulkUpdateLineItemStatus()
  const { selectedSkus, toggleSku, selectAllSkus, clearSelections } = usePurchaseOrderStore()
  const [loadingDistributor, setLoadingDistributor] = useState<string | null>(null)
  const [bulkStatus, setBulkStatus] = useState('on_hold')

  const allSkus = [...new Set(data?.results.map((item) => item.sku) ?? [])]
  const allSelected = allSkus.length > 0 && allSkus.every((s) => selectedSkus.includes(s))
  const checkedRowCount = data?.results.filter((item) => selectedSkus.includes(item.sku)).length ?? 0
  const selectedQuantityTotal = data?.results
    .filter((item) => selectedSkus.includes(item.sku))
    .reduce((sum, item) => sum + item.quantity, 0) ?? 0

  const handleSelectAll = () => {
    if (allSelected) {
      clearSelections()
    } else {
      selectAllSkus(allSkus)
    }
  }

  const handleStatusChange = (itemId: number, newStatus: string) => {
    statusMutation.mutate({ id: itemId, purchaseStatus: newStatus })
  }

  const handleBulkStatusChange = () => {
    const selectedIds =
      data?.results
        .filter((item) => selectedSkus.includes(item.sku))
        .map((item) => item.id) ?? []
    if (selectedIds.length === 0) return
    bulkStatusMutation.mutate(
      { ids: selectedIds, purchaseStatus: bulkStatus },
      {
        onSuccess: () => {
          clearSelections()
        },
      }
    )
  }

  const distributorLabel: Record<string, string> = { bookseen: '북센', kyobo: '교보' }

  const handleGenerateFile = async (distributor: string) => {
    if (selectedSkus.length === 0) return
    setLoadingDistributor(distributor)
    try {
      const result = await generateMutation.mutateAsync({ distributor, skus: selectedSkus })
      if (isWarningResponse(result)) {
        toast.warning(`알 수 없는 SKU: ${result.unknown_skus.join(', ')}`)
      } else {
        const label = distributorLabel[distributor] ?? distributor
        const filename = `${formatDateCompact(new Date())}_${label}_주문1차.xlsx`
        downloadBlob(result, filename)
        toast.success(`${label} 발주 파일이 다운로드되었습니다.`)
      }
    } finally {
      setLoadingDistributor(null)
    }
  }

  if (isError) {
    return <p className="text-destructive py-4">미발주 현황을 불러오는데 실패했습니다.</p>
  }

  return (
    <div className="space-y-4">
      {/* Action buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <p className="text-sm text-muted-foreground">
            {checkedRowCount > 0
              ? `${checkedRowCount}건 / 수량 ${selectedQuantityTotal}개`
              : '항목을 선택하세요'}
          </p>
          {selectedSkus.length > 0 && (
            <div className="flex items-center gap-2">
              <select
                value={bulkStatus}
                onChange={(e) => setBulkStatus(e.target.value)}
                className="text-sm border rounded px-2 py-1"
                aria-label="일괄 변경할 발주 상태 선택"
              >
                {PURCHASE_STATUS_OPTIONS.filter((o) => o.value !== 'unordered').map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                onClick={handleBulkStatusChange}
                disabled={bulkStatusMutation.isPending}
                className="bg-orange-500 text-white hover:bg-orange-600"
              >
                {bulkStatusMutation.isPending ? '변경 중...' : '일괄 상태 변경'}
              </Button>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={selectedSkus.length === 0 || loadingDistributor === 'bookseen'}
            onClick={() => handleGenerateFile('bookseen')}
            className="gap-2"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            {loadingDistributor === 'bookseen' ? '생성 중...' : '북센 발주 파일 생성'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={selectedSkus.length === 0 || loadingDistributor === 'kyobo'}
            onClick={() => handleGenerateFile('kyobo')}
            className="gap-2"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            {loadingDistributor === 'kyobo' ? '생성 중...' : '교보 발주 파일 생성'}
          </Button>
        </div>
      </div>

      {/* Loading skeleton */}
      {isPending && (
        <div role="status" aria-label="로딩 중" className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-muted animate-pulse rounded" />
          ))}
        </div>
      )}

      {/* Table */}
      {data && (
        <>
          <p className="text-sm text-muted-foreground">총 {data.count}건</p>
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-2 px-3 text-left w-10">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={handleSelectAll}
                      aria-label="전체 선택"
                      className="cursor-pointer"
                    />
                  </th>
                  <th className="py-2 px-3 text-left font-medium">주문번호</th>
                  <th className="py-2 px-3 text-left font-medium">SKU</th>
                  <th className="py-2 px-3 text-left font-medium">도서명</th>
                  <th className="py-2 px-3 text-left font-medium">출판사</th>
                  <th className="py-2 px-3 text-right font-medium">필요 수량</th>
                  <th className="py-2 px-3 text-left font-medium">자동 추천 발주처</th>
                  <th className="py-2 px-3 text-left font-medium">발주 상태</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-muted-foreground">
                      미발주 항목이 없습니다.
                    </td>
                  </tr>
                )}
                {data.results.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b last:border-0 hover:bg-muted/30 cursor-pointer"
                    onClick={() => toggleSku(item.sku)}
                  >
                    <td className="py-2 px-3">
                      <input
                        type="checkbox"
                        checked={selectedSkus.includes(item.sku)}
                        onChange={() => toggleSku(item.sku)}
                        onClick={(e) => e.stopPropagation()}
                        aria-label={`${item.title} 선택`}
                        className="cursor-pointer"
                      />
                    </td>
                    <td className="py-2 px-3 font-mono text-xs">
                      {item.order_name ?? '-'}
                    </td>
                    <td className="py-2 px-3 font-mono text-xs">{item.sku}</td>
                    <td className="py-2 px-3 max-w-xs truncate" title={item.title}>
                      {item.title}
                    </td>
                    <td className="py-2 px-3">{item.vendor}</td>
                    <td className="py-2 px-3 text-right font-medium">{item.quantity}</td>
                    <td className="py-2 px-3">
                      {item.auto_distributor ? (
                        <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                          {item.auto_distributor}
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-xs">-</span>
                      )}
                    </td>
                    <td className="py-2 px-3" onClick={(e) => e.stopPropagation()}>
                      <select
                        value={item.purchase_status}
                        onChange={(e) => handleStatusChange(item.id, e.target.value)}
                        disabled={statusMutation.isPending}
                        className="text-sm border rounded px-2 py-1"
                        aria-label={`${item.title} 발주 상태 변경`}
                      >
                        {PURCHASE_STATUS_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
