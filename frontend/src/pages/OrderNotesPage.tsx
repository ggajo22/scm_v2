import { useNavigate } from 'react-router-dom'
import { useOrderNotes, useResolveNote } from '@/features/order/hooks/useOrderNotes'

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

// @MX:ANCHOR: [AUTO] Order notes list page with optimistic resolve
// @MX:REASON: Fan-in >= 3 — routed from router, linked from Sidebar, and used via useOrderNotes hook
export function OrderNotesPage() {
  const navigate = useNavigate()
  const { data, isPending, isError } = useOrderNotes()
  const { mutate: resolveNote, isPending: isResolving } = useResolveNote()

  if (isPending) {
    return (
      <div className="p-6 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 bg-muted animate-pulse rounded" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6 text-center text-destructive">
        메모 목록을 불러오는데 실패했습니다.
      </div>
    )
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">미해결 메모</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data?.length ?? 0}건의 미해결 메모
          </p>
        </div>
      </div>

      {data?.length === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          미해결 메모가 없습니다.
        </div>
      )}

      <div className="space-y-2">
        {data?.map((order) => (
          <div
            key={order.id}
            className="border rounded-lg p-4 bg-background hover:bg-muted/30 transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate(`/orders/${order.id}`)}
                    className="font-mono text-sm font-medium hover:underline"
                  >
                    {order.name ?? `#${order.order_number}`}
                  </button>
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded text-white font-medium ${
                      order.store_type === 'gimssine' ? 'bg-blue-500' : 'bg-purple-500'
                    }`}
                  >
                    {order.store_type === 'gimssine' ? 'GIMSSINE' : 'Etoile'}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(order.shopify_created_at)}
                  </span>
                </div>
                {order.customer && (
                  <p className="text-xs text-muted-foreground">
                    {`${order.customer.last_name ?? ''}${order.customer.first_name ?? ''}`.trim() ||
                      order.customer.email ||
                      '-'}
                  </p>
                )}
                <p className="text-sm whitespace-pre-wrap text-foreground">{order.note}</p>
              </div>
              <button
                onClick={() => resolveNote(order.id)}
                disabled={isResolving}
                className="shrink-0 text-sm border rounded px-3 py-1.5 font-medium hover:bg-green-50 hover:border-green-400 hover:text-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                해결
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
