import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useConfirmOrder } from '@/hooks/usePurchaseOrderQueries'
import { usePurchaseOrderStore } from '@/stores/usePurchaseOrderStore'
import { PURCHASE_STATUS_OPTIONS } from '@/services/purchaseOrderApi'

export function ConfirmOrderTab() {
  const { confirmItems, clearSelections, setConfirmItems } = usePurchaseOrderStore()
  const confirmMutation = useConfirmOrder()

  // Local editable state — mirrors confirmItems from store
  const [localItems, setLocalItems] = useState(() => confirmItems)
  const [filterDistributor, setFilterDistributor] = useState<string>('')

  // Sync from store if items change (e.g., user navigated away and back)
  const storeSkus = confirmItems.map((i) => i.sku).join(',')
  const localSkus = localItems.map((i) => i.sku).join(',')
  if (storeSkus !== localSkus) {
    setLocalItems(confirmItems)
    setFilterDistributor('')
  }

  // Derive unique distributors for filter pills
  const uniqueDistributors = [...new Set(localItems.map((i) => i.distributor).filter(Boolean))]

  // Display-only filtered list — handleConfirm still uses localItems (all items)
  const displayItems = filterDistributor
    ? localItems.filter((item) => item.distributor === filterDistributor)
    : localItems

  // REQ-CON-010: distributor text input handler
  const handleDistributorChange = (sku: string, value: string) => {
    setLocalItems((prev) =>
      prev.map((item) => (item.sku === sku ? { ...item, distributor: value } : item))
    )
  }

  const handleQuantityChange = (sku: string, value: string) => {
    const qty = parseInt(value, 10)
    if (isNaN(qty) || qty < 1) return
    setLocalItems((prev) =>
      prev.map((item) => (item.sku === sku ? { ...item, quantity: qty } : item))
    )
  }

  // REQ-CON-020: purchase status dropdown handler
  const handlePurchaseStatusChange = (sku: string, value: string) => {
    setLocalItems((prev) =>
      prev.map((item) => (item.sku === sku ? { ...item, purchase_status: value } : item))
    )
  }

  // REQ-CON-030: memo text input handler
  const handleNoteChange = (sku: string, value: string) => {
    setLocalItems((prev) =>
      prev.map((item) => (item.sku === sku ? { ...item, note: value } : item))
    )
  }

  // REQ-CON-042: changes only saved on confirm button click
  const handleConfirm = () => {
    if (localItems.length === 0) return
    // Sync edits back to store before submitting
    setConfirmItems(localItems)
    confirmMutation.mutate(
      { items: localItems },
      {
        onSuccess: () => {
          clearSelections()
          setLocalItems([])
        },
      }
    )
  }

  if (localItems.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        <p>확정할 발주 항목이 없습니다.</p>
        <p className="text-xs mt-1">업체 자료 업로드 탭에서 항목을 가져오세요.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          총 {localItems.length}건{filterDistributor ? ` (${displayItems.length}건 표시)` : ''}
        </p>
        <Button
          size="sm"
          onClick={handleConfirm}
          disabled={confirmMutation.isPending}
        >
          {confirmMutation.isPending ? '확정 중...' : '발주 확정'}
        </Button>
      </div>

      {/* Distributor filter pills */}
      {uniqueDistributors.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setFilterDistributor('')}
            className={`px-3 py-1 rounded-full text-xs border transition-colors ${
              filterDistributor === ''
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background text-muted-foreground border-border hover:border-foreground'
            }`}
          >
            전체 ({localItems.length})
          </button>
          {uniqueDistributors.map((dist) => {
            const count = localItems.filter((i) => i.distributor === dist).length
            return (
              <button
                key={dist}
                onClick={() => setFilterDistributor(dist)}
                className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                  filterDistributor === dist
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background text-muted-foreground border-border hover:border-foreground'
                }`}
              >
                {dist} ({count})
              </button>
            )
          })}
        </div>
      )}

      {/* REQ-CON-040: column order — SKU | 발주처 | 발주상태 | 수량 | 단가 | 메모 */}
      <div className="overflow-x-auto rounded border">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="py-2 px-3 text-left font-medium">SKU</th>
              <th className="py-2 px-3 text-left font-medium">발주처</th>
              <th className="py-2 px-3 text-left font-medium">발주상태</th>
              <th className="py-2 px-3 text-right font-medium">수량</th>
              <th className="py-2 px-3 text-right font-medium">단가</th>
              <th className="py-2 px-3 text-left font-medium">메모</th>
            </tr>
          </thead>
          <tbody>
            {displayItems.map((item) => (
              <tr key={item.sku} className="border-b last:border-0 hover:bg-muted/30">
                <td className="py-2 px-3 font-mono text-xs">{item.sku}</td>

                {/* REQ-CON-010/011: distributor text input (replaces badge) */}
                <td className="py-2 px-3">
                  <input
                    type="text"
                    value={item.distributor}
                    onChange={(e) => handleDistributorChange(item.sku, e.target.value)}
                    className="border rounded px-2 py-0.5 text-sm w-24"
                    aria-label={`${item.sku} 발주처`}
                  />
                </td>

                {/* REQ-CON-020/021: purchase status select dropdown */}
                <td className="py-2 px-3">
                  <select
                    value={item.purchase_status ?? 'unordered'}
                    onChange={(e) => handlePurchaseStatusChange(item.sku, e.target.value)}
                    className="border rounded px-2 py-0.5 text-sm"
                    aria-label={`${item.sku} 발주상태`}
                  >
                    {PURCHASE_STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </td>

                {/* 수량: existing number input */}
                <td className="py-2 px-3 text-right">
                  <input
                    type="number"
                    min={1}
                    value={item.quantity}
                    onChange={(e) => handleQuantityChange(item.sku, e.target.value)}
                    className="border rounded px-2 py-0.5 text-sm text-right w-20"
                    aria-label={`${item.sku} 수량`}
                  />
                </td>

                {/* 단가: display only */}
                <td className="py-2 px-3 text-right">
                  {item.unit_price ? Number(item.unit_price).toLocaleString() : '-'}
                </td>

                {/* REQ-CON-030/031/041: memo text input, maxLength=500 */}
                <td className="py-2 px-3">
                  <input
                    type="text"
                    value={item.note ?? ''}
                    onChange={(e) => handleNoteChange(item.sku, e.target.value)}
                    placeholder="메모 입력..."
                    maxLength={500}
                    className="border rounded px-2 py-0.5 text-sm w-40"
                    aria-label={`${item.sku} 메모`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
