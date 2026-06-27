import { useNavigate } from 'react-router-dom'
import { useUnresolvedLineItemNotes, useResolveLineItemNote } from '@/features/order/hooks/useLineItemNotes'
import type { LineItemNoteAssignee } from '@/types/order'

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

const ASSIGNEE_COLORS: Record<LineItemNoteAssignee, string> = {
  CS: 'bg-blue-100 text-blue-700 border-blue-200',
  발주: 'bg-orange-100 text-orange-700 border-orange-200',
  한국창고: 'bg-green-100 text-green-700 border-green-200',
  미국창고: 'bg-purple-100 text-purple-700 border-purple-200',
}

// @MX:ANCHOR: [AUTO] LineItem notes page — mirrors OrderNotesPage structure for unresolved note management
// @MX:REASON: Fan-in >= 3 — routed from router, linked from Sidebar, and used via useUnresolvedLineItemNotes hook
export function LineItemNotesPage() {
  const navigate = useNavigate()
  const { data, isPending, isError } = useUnresolvedLineItemNotes()
  const { mutate: resolveNote, isPending: isResolving } = useResolveLineItemNote()

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
        품목 메모 목록을 불러오는데 실패했습니다.
      </div>
    )
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">미해결 품목 메모</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data?.length ?? 0}건의 미해결 품목 메모
          </p>
        </div>
      </div>

      {data?.length === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          미해결 품목 메모가 없습니다.
        </div>
      )}

      <div className="space-y-2">
        {data?.map((note) => (
          <div
            key={note.id}
            className="border rounded-lg p-4 bg-background hover:bg-muted/30 transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={() => navigate(`/orders/${note.order_id}`)}
                    className="font-mono text-sm font-medium hover:underline"
                  >
                    {note.order_name ?? `주문 #${note.order_id}`}
                  </button>
                  {note.assignee && (
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded border font-medium ${
                        ASSIGNEE_COLORS[note.assignee as LineItemNoteAssignee] ?? 'bg-gray-100 text-gray-700 border-gray-200'
                      }`}
                    >
                      {note.assignee}
                    </span>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {formatDate(note.created_at)}
                  </span>
                </div>
                {(note.line_item_title || note.line_item_sku) && (
                  <p className="text-xs text-muted-foreground">
                    {note.line_item_title ?? '-'}
                    {note.line_item_sku && (
                      <span className="ml-2 font-mono">{note.line_item_sku}</span>
                    )}
                  </p>
                )}
                {note.author_username && (
                  <p className="text-xs text-muted-foreground">작성자: {note.author_username}</p>
                )}
                <p className="text-sm whitespace-pre-wrap text-foreground">{note.content}</p>
              </div>
              <button
                onClick={() => resolveNote(note.id)}
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
