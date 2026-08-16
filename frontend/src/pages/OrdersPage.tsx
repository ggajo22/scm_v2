import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useOrders } from '@/features/order/hooks/useOrders'
import { useOrderSync } from '@/features/order/hooks/useOrderSync'
import { useOrderSyncStatus } from '@/features/order/hooks/useOrderSyncStatus'
import { useAuthStore } from '@/store/authStore'
import { LOGISTICS_STATUS_LABELS } from '@/pages/OutboundPage/logisticsStatusLabels'
import type { Order, OrderListParams } from '@/types/order'

// SPEC-ORDER-023 REQ-OLIST-030~032: extends the SPEC-ORDER-016-owned
// LOGISTICS_STATUS_LABELS (imported, not modified — that file belongs to a
// different SPEC) with the 2 additional display values this SPEC introduces.
// `received` from the shared map is intentionally unused here — it is never
// emitted as a logistics_display value (see Order.logistics_display).
const ORDER_LOGISTICS_DISPLAY_LABELS: Record<string, string> = {
  ...LOGISTICS_STATUS_LABELS,
  partial_shipped: '부분출고',
  partial: '부분입고',
}

// SPEC-ORDER-023 REQ-OLIST-024: the 6 accepted logistics_display values, in
// display order, mirrored from backend/order/views.py's
// LOGISTICS_DISPLAY_FILTER_VALUES whitelist.
const LOGISTICS_DISPLAY_FILTER_OPTIONS: readonly string[] = [
  'not_shipped',
  'shipment_confirmed',
  'outbound_scheduled',
  'partial_shipped',
  'shipped',
  'partial',
]

// SPEC-ORDER-SYNC-HEALTH: thresholds for the sync-health indicator below.
// The point is not decoration — a stopped 5-minute scheduled sync has cost
// 102 lost orders before, so a stale value must visually intrude while a
// fresh one stays quiet.
const SYNC_WARN_THRESHOLD_MIN = 15
const SYNC_ALERT_THRESHOLD_MIN = 60

type SyncLevel = 'fresh' | 'warn' | 'alert'

function getSyncLevel(minutesAgo: number | null): SyncLevel {
  if (minutesAgo === null || minutesAgo >= SYNC_ALERT_THRESHOLD_MIN) return 'alert'
  if (minutesAgo >= SYNC_WARN_THRESHOLD_MIN) return 'warn'
  return 'fresh'
}

const SYNC_LEVEL_STYLES: Record<SyncLevel, string> = {
  fresh: 'text-xs text-muted-foreground',
  warn: 'text-xs font-medium text-amber-700 bg-amber-100 px-2 py-1 rounded',
  alert: 'text-xs font-bold text-red-700 bg-red-100 px-2 py-1 rounded animate-pulse',
}

function formatMinutesAgo(minutes: number): string {
  if (minutes < 1) return '방금 전'
  if (minutes < 60) return `${minutes}분 전`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`
  return `${Math.floor(hours / 24)}일 전`
}

// react-hooks/purity: Date.now() is impure and must not be called directly
// in a render body — track it as state, ticked on an interval, so the
// "n분 전" label also keeps advancing while the page sits open between the
// hook's own 60s refetches.
function useNow(intervalMs: number): number {
  const [now, setNow] = useState<number>(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
  return now
}

// REQ-SYNC-HEALTH: only ever mounted for super_admin (see role gate in
// OrdersPage below) — mounting is what keeps useOrderSyncStatus from firing
// a request at all for admin, not a client-side no-render check.
function SyncStatusIndicator() {
  const { data } = useOrderSyncStatus()
  const now = useNow(30_000)
  if (!data) return null

  const lastRunAt = data.last_run_at
  const minutesAgo = lastRunAt ? Math.floor((now - new Date(lastRunAt).getTime()) / 60000) : null
  const level = getSyncLevel(minutesAgo)

  const title = lastRunAt ? new Date(lastRunAt).toLocaleString('ko-KR') : '동기화 기록 없음'

  const text =
    level === 'alert'
      ? minutesAgo === null
        ? '동기화 기록 없음 — 자동 동기화가 중단되었을 수 있습니다'
        : `마지막 동기화 ${formatMinutesAgo(minutesAgo)} — 자동 동기화가 중단되었을 수 있습니다`
      : `마지막 동기화 ${formatMinutesAgo(minutesAgo ?? 0)}`

  return (
    <span className={SYNC_LEVEL_STYLES[level]} title={title} data-testid="sync-status-indicator">
      {text}
    </span>
  )
}

// SPEC-ORDER-023 REQ-OLIST-004~006 (H6): copies only the 3 refund branches
// from the removed getDisplayStatus — never the trailing financial_status
// label map, since a normal 'paid' order must render no badge at all, not a
// "결제완료" badge (AC-OLIST-004).
function getCancelBadge(order: Order): '취소' | '부분취소' | null {
  if (order.financial_status === 'refunded') return '취소'
  if (order.financial_status === 'partially_refunded') return '부분취소'
  // paid + has_refund: $0 cancellation — Shopify keeps status 'paid' but refund record exists
  if (order.has_refund) return '부분취소'
  return null
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
  const navigate = useNavigate()
  const { data, isPending, isError } = useOrders(params)
  const syncMutation = useOrderSync()
  const role = useAuthStore((state) => state.user?.role)

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
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">주문관리</h1>
          {role === 'super_admin' && <SyncStatusIndicator />}
        </div>
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
          value={params.location ?? ''}
          onChange={(e) => setFilter('location', e.target.value)}
          aria-label="위치 필터"
        >
          <option value="">전체 위치</option>
          <option value="CA">CA</option>
          <option value="NJ">NJ</option>
          <option value="KR">KR</option>
          <option value="CA/NJ">CA/NJ</option>
        </select>

        <select
          className="border rounded px-2 py-1 text-sm"
          value={params.logistics_display ?? ''}
          onChange={(e) => setFilter('logistics_display', e.target.value)}
          aria-label="물류상태 필터"
        >
          <option value="">전체</option>
          {LOGISTICS_DISPLAY_FILTER_OPTIONS.map((value) => (
            <option key={value} value={value}>
              {ORDER_LOGISTICS_DISPLAY_LABELS[value] ?? value}
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
                  <th className="py-2 px-3 text-left font-medium">위치</th>
                  <th className="py-2 px-3 text-left font-medium">고객</th>
                  <th className="py-2 px-3 text-left font-medium">물류상태</th>
                  <th className="py-2 px-3 text-left font-medium">발주상태</th>
                  <th className="py-2 px-3 text-left font-medium">마진율</th>
                  <th className="py-2 px-3 text-right font-medium">금액</th>
                  <th className="py-2 px-3 text-left font-medium">주문일</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-muted-foreground">
                      {params.search
                        ? `"${params.search}"에 해당하는 주문이 없습니다.`
                        : '주문이 없습니다.'}
                    </td>
                  </tr>
                )}
                {data.results.map((order) => (
                  <tr
                    key={order.id}
                    className="border-b last:border-0 hover:bg-muted/30 cursor-pointer"
                    onClick={() => navigate(`/orders/${order.id}`)}
                  >
                    <td className="py-2 px-3 font-mono text-xs">
                      {order.name ?? `#${order.order_number}`}
                      {getCancelBadge(order) && (
                        <span
                          data-testid="cancel-badge"
                          className="ml-1.5 text-[10px] font-sans font-medium text-red-600 bg-red-100 px-1.5 py-0.5 rounded"
                        >
                          {getCancelBadge(order)}
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      <StoreLabel store={order.store_type} />
                    </td>
                    <td className="py-2 px-3">
                      {order.location ? (
                        <span className="text-xs font-mono">{order.location}</span>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      {order.customer
                        ? `${order.customer.last_name ?? ''}${order.customer.first_name ?? ''}`.trim() ||
                          order.customer.email
                        : '-'}
                    </td>
                    <td className="py-2 px-3">
                      {order.logistics_display
                        ? ORDER_LOGISTICS_DISPLAY_LABELS[order.logistics_display] ?? order.logistics_display
                        : '-'}
                    </td>
                    <td className="py-2 px-3">
                      {order.purchase_display === 'unordered'
                        ? '미발주'
                        : order.purchase_display === 'ordered'
                          ? '발주완료'
                          : '-'}
                    </td>
                    <td className="py-2 px-3">
                      {order.margin_rate !== null ? `${order.margin_rate}%` : '-'}
                    </td>
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
