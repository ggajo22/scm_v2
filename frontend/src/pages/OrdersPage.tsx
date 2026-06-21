import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useOrders } from '@/features/order/hooks/useOrders'
import { useOrderSync } from '@/features/order/hooks/useOrderSync'
import type { Order, OrderListParams } from '@/types/order'

function getDisplayStatus(order: Order): string {
  // REQ-ORD-049: has_refund=true OR financial_status="refunded" → "취소"
  if (order.has_refund || order.financial_status === 'refunded') return '취소'
  const map: Record<string, string> = {
    paid: '결제완료',
    pending: '결제대기',
    partially_paid: '부분결제',
    partially_refunded: '부분취소',
    voided: '무효',
    authorized: '승인대기',
  }
  return map[order.financial_status ?? ''] ?? order.financial_status ?? '-'
}

function getFulfillmentLabel(status: string | null): string {
  if (!status) return '미출고'
  const map: Record<string, string> = {
    fulfilled: '출고완료',
    partial: '부분출고',
    restocked: '재입고',
  }
  return map[status] ?? status
}

function StoreLabel({ store }: { store: 'gimssine' | 'etoile' }) {
  return (
    <span
      className={
        store === 'gimssine'
          ? 'text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded'
          : 'text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded'
      }
    >
      {store === 'gimssine' ? 'GIMSSINE' : 'Etoile'}
    </span>
  )
}

export function OrdersPage() {
  const [params, setParams] = useState<OrderListParams>({ page: 1 })
  const [searchInput, setSearchInput] = useState('')
  const { data, isPending, isError } = useOrders(params)
  const syncMutation = useOrderSync()

  const handleSync = () => {
    syncMutation.mutate()
  }

  const setFilter = (key: keyof OrderListParams, value: string) => {
    setParams((prev) => ({ ...prev, [key]: value || undefined, page: 1 }))
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      setFilter('search', searchInput)
    }
  }

  const handleSearchClear = () => {
    setSearchInput('')
    setFilter('search', '')
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">주문관리</h1>
        <Button
          onClick={handleSync}
          disabled={syncMutation.isPending}
          variant="outline"
          size="sm"
          className="gap-2"
        >
          <RefreshCw
            className={`h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          {syncMutation.isPending ? '동기화 중...' : '동기화'}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder="주문번호 또는 ISBN (Enter로 검색)"
            className="border rounded px-3 py-1.5 text-sm w-64 pr-8"
            aria-label="주문 검색"
          />
          {searchInput && (
            <button
              onClick={handleSearchClear}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
              aria-label="검색 초기화"
            >
              ✕
            </button>
          )}
        </div>

        <select
          className="border rounded px-2 py-1 text-sm"
          value={params.store_type ?? ''}
          onChange={(e) => setFilter('store_type', e.target.value)}
          aria-label="스토어 필터"
        >
          <option value="">전체 스토어</option>
          <option value="gimssine">GIMSSINE</option>
          <option value="etoile">Etoile</option>
        </select>

        <select
          className="border rounded px-2 py-1 text-sm"
          value={params.financial_status ?? ''}
          onChange={(e) => setFilter('financial_status', e.target.value)}
          aria-label="결제 상태 필터"
        >
          <option value="">전체 결제상태</option>
          <option value="paid">결제완료</option>
          <option value="pending">결제대기</option>
          <option value="refunded">환불</option>
          <option value="partially_refunded">부분환불</option>
        </select>

        <select
          className="border rounded px-2 py-1 text-sm"
          value={params.fulfillment_status ?? ''}
          onChange={(e) => setFilter('fulfillment_status', e.target.value)}
          aria-label="출고 상태 필터"
        >
          <option value="">전체 출고상태</option>
          <option value="unfulfilled">미출고</option>
          <option value="fulfilled">출고완료</option>
          <option value="partial">부분출고</option>
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

      {/* Table */}
      {isPending && (
        <div role="status" aria-label="로딩 중" className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-muted animate-pulse rounded" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-destructive">주문 목록을 불러오는데 실패했습니다.</p>
      )}

      {data && (
        <>
          <p className="text-sm text-muted-foreground">총 {data.count.toLocaleString()}건</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-2 px-3 text-left font-medium">주문번호</th>
                  <th className="py-2 px-3 text-left font-medium">스토어</th>
                  <th className="py-2 px-3 text-left font-medium">고객</th>
                  <th className="py-2 px-3 text-left font-medium">결제상태</th>
                  <th className="py-2 px-3 text-left font-medium">출고상태</th>
                  <th className="py-2 px-3 text-right font-medium">금액</th>
                  <th className="py-2 px-3 text-left font-medium">주문일</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-muted-foreground">
                      {params.search
                        ? `"${params.search}"에 해당하는 주문이 없습니다.`
                        : '주문이 없습니다.'}
                    </td>
                  </tr>
                )}
                {data.results.map((order) => (
                  <tr key={order.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="py-2 px-3 font-mono text-xs">
                      {order.name ?? `#${order.order_number}`}
                    </td>
                    <td className="py-2 px-3">
                      <StoreLabel store={order.store_type} />
                    </td>
                    <td className="py-2 px-3">
                      {order.customer
                        ? `${order.customer.last_name ?? ''}${order.customer.first_name ?? ''}`.trim() ||
                          order.customer.email
                        : '-'}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={
                          order.has_refund || order.financial_status === 'refunded'
                            ? 'text-red-600 font-medium'
                            : ''
                        }
                      >
                        {getDisplayStatus(order)}
                      </span>
                    </td>
                    <td className="py-2 px-3">{getFulfillmentLabel(order.fulfillment_status)}</td>
                    <td className="py-2 px-3 text-right">
                      {order.total_price
                        ? `${Number(order.total_price).toLocaleString()} ${order.currency ?? ''}`
                        : '-'}
                    </td>
                    <td className="py-2 px-3 text-xs text-muted-foreground">
                      {order.shopify_created_at
                        ? new Date(order.shopify_created_at).toLocaleDateString('ko-KR')
                        : '-'}
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
                onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}
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
                onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}
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
