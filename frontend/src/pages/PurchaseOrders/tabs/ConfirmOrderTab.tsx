import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useConfirmOrder } from '@/hooks/usePurchaseOrderQueries'
import { usePurchaseOrderStore } from '@/stores/usePurchaseOrderStore'

export function ConfirmOrderTab() {
  const { confirmItems, clearSelections, setConfirmItems } = usePurchaseOrderStore()
  const confirmMutation = useConfirmOrder()

  // Local editable quantities — mirrors confirmItems from store
  const [localItems, setLocalItems] = useState(() => confirmItems)

  // Sync from store if items change (e.g., user navigated away and back)
  const storeSkus = confirmItems.map((i) => i.sku).join(',')
  const localSkus = localItems.map((i) => i.sku).join(',')
  if (storeSkus !== localSkus) {
    setLocalItems(confirmItems)
  }

  const handleQuantityChange = (sku: string, value: string) => {
    const qty = parseInt(value, 10)
    if (isNaN(qty) || qty < 1) return
    setLocalItems((prev) =>
      prev.map((item) => (item.sku === sku ? { ...item, quantity: qty } : item))
    )
  }

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
        <p className="text-sm text-muted-foreground">총 {localItems.length}건</p>
        <Button
          size="sm"
          onClick={handleConfirm}
          disabled={confirmMutation.isPending}
        >
          {confirmMutation.isPending ? '확정 중...' : '발주 확정'}
        </Button>
      </div>

      <div className="overflow-x-auto rounded border">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="py-2 px-3 text-left font-medium">SKU</th>
              <th className="py-2 px-3 text-left font-medium">발주처</th>
              <th className="py-2 px-3 text-right font-medium">수량</th>
              <th className="py-2 px-3 text-right font-medium">단가</th>
            </tr>
          </thead>
          <tbody>
            {localItems.map((item) => (
              <tr key={item.sku} className="border-b last:border-0 hover:bg-muted/30">
                <td className="py-2 px-3 font-mono text-xs">{item.sku}</td>
                <td className="py-2 px-3">
                  <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                    {item.distributor}
                  </span>
                </td>
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
                <td className="py-2 px-3 text-right">
                  {item.unit_price ? Number(item.unit_price).toLocaleString() : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
