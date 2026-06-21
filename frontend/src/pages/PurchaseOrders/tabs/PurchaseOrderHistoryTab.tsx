import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { usePurchaseOrders } from '@/hooks/usePurchaseOrderQueries'
import type { PurchaseOrderParams } from '@/services/purchaseOrderApi'

const STATUS_MAP: Record<string, string> = {
  pending: '대기',
  confirmed: '확정',
  shipped: '출고',
  cancelled: '취소',
}

const DISTRIBUTOR_OPTIONS = ['북센', '교보'] as const

export function PurchaseOrderHistoryTab() {
  const [params, setParams] = useState<PurchaseOrderParams>({ page: 1 })
  const { data, isPending, isError } = usePurchaseOrders(params)

  const setFilter = (key: keyof PurchaseOrderParams, value: string) => {
    setParams((prev) => ({ ...prev, [key]: value || undefined, page: 1 }))
  }

  const handlePageChange = (delta: number) => {
    setParams((prev) => ({ ...prev, page: (prev.page ?? 1) + delta }))
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          className="border rounded px-2 py-1 text-sm"
          value={params.distributor ?? ''}
          onChange={(e) => setFilter('distributor', e.target.value)}
          aria-label="발주처 필터"
        >
          <option value="">전체 발주처</option>
          {DISTRIBUTOR_OPTIONS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>

        <select
          className="border rounded px-2 py-1 text-sm"
          value={params.status ?? ''}
          onChange={(e) => setFilter('status', e.target.value)}
          aria-label="상태 필터"
        >
          <option value="">전체 상태</option>
          {Object.entries(STATUS_MAP).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-1">
          <input
            type="date"
            className="border rounded px-2 py-1 text-sm"
            value={params.date_from ?? ''}
            onChange={(e) => setFilter('date_from', e.target.value)}
            aria-label="시작일"
          />
          <span className="text-muted-foreground text-sm">~</span>
          <input
            type="date"
            className="border rounded px-2 py-1 text-sm"
            value={params.date_to ?? ''}
            onChange={(e) => setFilter('date_to', e.target.value)}
            aria-label="종료일"
          />
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

      {isError && (
        <p className="text-destructive">발주 이력을 불러오는데 실패했습니다.</p>
      )}

      {data && (
        <>
          <p className="text-sm text-muted-foreground">총 {data.count.toLocaleString()}건</p>
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-2 px-3 text-left font-medium">발주처</th>
                  <th className="py-2 px-3 text-left font-medium">SKU</th>
                  <th className="py-2 px-3 text-left font-medium">도서명</th>
                  <th className="py-2 px-3 text-right font-medium">수량</th>
                  <th className="py-2 px-3 text-right font-medium">단가</th>
                  <th className="py-2 px-3 text-left font-medium">상태</th>
                  <th className="py-2 px-3 text-left font-medium">발주일시</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-muted-foreground">
                      발주 이력이 없습니다.
                    </td>
                  </tr>
                )}
                {data.results.map((order) => (
                  <tr key={order.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="py-2 px-3">
                      <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                        {order.distributor}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-xs">{order.sku}</td>
                    <td className="py-2 px-3 max-w-xs truncate" title={order.title}>
                      {order.title}
                    </td>
                    <td className="py-2 px-3 text-right">{order.quantity}</td>
                    <td className="py-2 px-3 text-right">
                      {order.unit_price ? Number(order.unit_price).toLocaleString() : '-'}
                    </td>
                    <td className="py-2 px-3">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-muted">
                        {STATUS_MAP[order.status] ?? order.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-xs text-muted-foreground">
                      {new Date(order.created_at).toLocaleString('ko-KR')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {(data.previous || data.next) && (
            <div className="flex justify-center gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!data.previous}
                onClick={() => handlePageChange(-1)}
              >
                이전
              </Button>
              <span className="px-3 py-1 text-sm text-muted-foreground">
                {params.page ?? 1} 페이지
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={!data.next}
                onClick={() => handlePageChange(1)}
              >
                다음
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
