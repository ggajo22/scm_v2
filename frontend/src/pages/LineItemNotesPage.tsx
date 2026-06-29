import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { LINE_ITEM_NOTES_QUERY_KEY } from '@/features/order/hooks/useLineItemNotes'
import { useNavigate } from 'react-router-dom'
import {
  useUnresolvedLineItemNotes,
  useResolveLineItemNote,
  useCreateLineItemNote,
  useLineItemNotes,
  downloadLineItemNotesExcel,
} from '@/features/order/hooks/useLineItemNotes'
import type { LineItemNote, LineItemNoteAssignee, LineItemNoteUnresolved } from '@/types/order'
import { ASSIGNEE_NOTE_TYPES } from '@/types/order'

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

const ASSIGNEE_CHOICES: LineItemNoteAssignee[] = ['CS', '발주', '한국창고', '미국창고']

type Tab = 'CS' | '발주' | '타출판사'

function filterNotes(notes: LineItemNoteUnresolved[], tab: Tab): LineItemNoteUnresolved[] {
  if (tab === '타출판사') return notes.filter((n) => n.note_type === '타출판사')

  // Group by line_item_id; pick latest note (highest id) per line item
  const latestByLineItem = new Map<number, LineItemNoteUnresolved>()
  for (const note of notes) {
    if (note.note_type === '타출판사') continue
    const existing = latestByLineItem.get(note.line_item_id)
    if (!existing || note.id > existing.id) {
      latestByLineItem.set(note.line_item_id, note)
    }
  }

  return Array.from(latestByLineItem.values()).filter((n) => n.assignee === tab)
}

// ---------------------------------------------------------------------------
// NoteHistory — unresolved note thread for a line item, always expanded
// ---------------------------------------------------------------------------
function NoteHistory({ lineItemId, excludeNoteId }: { lineItemId: number; excludeNoteId: number }) {
  const { data: allNotes } = useLineItemNotes(lineItemId)

  const others = allNotes?.filter((n: LineItemNote) => n.id !== excludeNoteId) ?? []

  if (others.length === 0) return null

  return (
    <div className="mt-2 border-t pt-2">
      <p className="text-xs text-muted-foreground mb-1.5">이력 {others.length}건</p>
      <div className="space-y-1.5">
        {[...others].reverse().map((note: LineItemNote) => (
            <div key={note.id} className={`text-xs rounded px-2 py-1.5 bg-muted/40 ${note.is_resolved ? 'opacity-60' : ''}`}>
              <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
                {note.assignee && (
                  <span
                    className={`px-1.5 py-0.5 rounded border font-medium ${
                      ASSIGNEE_COLORS[note.assignee as LineItemNoteAssignee] ?? 'bg-gray-100 text-gray-700 border-gray-200'
                    }`}
                  >
                    {note.assignee}
                  </span>
                )}
                {note.note_type && (
                  <span className="px-1.5 py-0.5 rounded border font-medium bg-gray-100 text-gray-700 border-gray-200">
                    {note.note_type}
                  </span>
                )}
                {note.is_resolved && (
                  <span className="px-1.5 py-0.5 rounded border font-medium bg-green-50 text-green-600 border-green-200">
                    해결됨
                  </span>
                )}
                {note.author_username && (
                  <span className="text-muted-foreground">{note.author_username}</span>
                )}
                <span className="text-muted-foreground">{formatDate(note.created_at)}</span>
              </div>
              <p className="whitespace-pre-wrap text-foreground">{note.content}</p>
            </div>
          ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// InlineNoteForm — add note; auto-resolves current note when cross-tab assignee
// ---------------------------------------------------------------------------
function InlineNoteForm({
  lineItemId,
  orderId,
  currentNoteId,
  currentTabAssignee,
  onResolve,
}: {
  lineItemId: number
  orderId: number
  currentNoteId: number
  currentTabAssignee: LineItemNoteAssignee
  onResolve: (id: number) => void
}) {
  const [open, setOpen] = useState(false)
  const [content, setContent] = useState('')
  const [assignee, setAssignee] = useState<LineItemNoteAssignee>(
    currentTabAssignee === 'CS' ? '발주' : 'CS'
  )
  const [noteType, setNoteType] = useState('')
  const { mutate: createNote, isPending } = useCreateLineItemNote(lineItemId, orderId)

  const availableTypes = ASSIGNEE_NOTE_TYPES[assignee] ?? []

  function handleSubmit() {
    if (!content.trim()) return
    createNote(
      { content: content.trim(), assignee, note_type: noteType || undefined },
      {
        onSuccess: () => {
          // 다른 담당자에게 넘길 때 현재 노트 자동 해결
          if (assignee !== currentTabAssignee) {
            onResolve(currentNoteId)
          }
          setContent('')
          setNoteType('')
          setOpen(false)
        },
      },
    )
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="mt-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        + 노트 추가
      </button>
    )
  }

  return (
    <div className="mt-3 pt-3 border-t space-y-2">
      <div className="flex gap-2 flex-wrap">
        <select
          value={assignee}
          onChange={(e) => {
            setAssignee(e.target.value as LineItemNoteAssignee)
            setNoteType('')
          }}
          className="text-xs border rounded px-2 py-1.5 bg-background"
        >
          {ASSIGNEE_CHOICES.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        {availableTypes.length > 0 && (
          <select
            value={noteType}
            onChange={(e) => setNoteType(e.target.value)}
            className="text-xs border rounded px-2 py-1.5 bg-background"
          >
            <option value="">유형 선택</option>
            {availableTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        )}
      </div>
      <div className="flex gap-2">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="노트 추가..."
          rows={2}
          autoFocus
          className="flex-1 text-sm border rounded px-2 py-1.5 resize-none bg-background focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <div className="flex flex-col gap-1">
          <button
            onClick={handleSubmit}
            disabled={isPending || !content.trim()}
            className="text-sm border rounded px-3 py-1.5 font-medium hover:bg-blue-50 hover:border-blue-400 hover:text-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            추가
          </button>
          <button
            onClick={() => { setOpen(false); setContent(''); setNoteType('') }}
            className="text-sm border rounded px-3 py-1.5 text-muted-foreground hover:bg-muted transition-colors"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// NoteCard
// ---------------------------------------------------------------------------
function NoteCard({
  note,
  onResolve,
  isResolving,
  showAddForm,
  currentTabAssignee,
}: {
  note: LineItemNoteUnresolved
  onResolve: (id: number) => void
  isResolving: boolean
  showAddForm: boolean
  currentTabAssignee: LineItemNoteAssignee
}) {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border rounded-lg bg-background hover:bg-muted/30 transition-colors">
      {/* 한 줄 요약 (항상 표시) */}
      <div
        className="flex items-center gap-2 px-4 py-2.5 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="text-xs text-muted-foreground">{expanded ? '▲' : '▼'}</span>
        <button
          onClick={(e) => { e.stopPropagation(); navigate(`/orders/${note.order_id}`) }}
          className="font-mono text-sm font-medium hover:underline shrink-0"
        >
          {note.order_name ?? `주문 #${note.order_id}`}
        </button>
        {note.assignee && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded border font-medium shrink-0 ${
              ASSIGNEE_COLORS[note.assignee as LineItemNoteAssignee] ?? 'bg-gray-100 text-gray-700 border-gray-200'
            }`}
          >
            {note.assignee}
          </span>
        )}
        {note.note_type && (
          <span className="text-xs px-1.5 py-0.5 rounded border font-medium bg-gray-100 text-gray-700 border-gray-200 shrink-0">
            {note.note_type}
          </span>
        )}
        <span className="text-sm truncate max-w-[200px] shrink-0">{note.content}</span>
        <span className="text-muted-foreground shrink-0">|</span>
        <span className="text-sm text-muted-foreground truncate flex-1 min-w-0">
          {note.line_item_title ?? note.line_item_sku ?? ''}
        </span>
        <span className="text-xs text-muted-foreground shrink-0">{formatDate(note.created_at)}</span>
        <button
          onClick={(e) => { e.stopPropagation(); onResolve(note.id) }}
          disabled={isResolving}
          className="shrink-0 text-sm border rounded px-3 py-1 font-medium hover:bg-green-50 hover:border-green-400 hover:text-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          해결
        </button>
      </div>

      {/* 펼쳐진 상세 */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t space-y-1">
          {(note.line_item_title || note.line_item_sku) && (
            <p className="text-xs text-muted-foreground">
              {note.line_item_title ?? '-'}
              {note.line_item_sku && <span className="ml-2 font-mono">{note.line_item_sku}</span>}
            </p>
          )}
          {note.author_username && (
            <p className="text-xs text-muted-foreground">작성자: {note.author_username}</p>
          )}
          <p className="text-sm whitespace-pre-wrap text-foreground">{note.content}</p>
          <NoteHistory lineItemId={note.line_item_id} excludeNoteId={note.id} />
          {showAddForm && (
            <InlineNoteForm
              lineItemId={note.line_item_id}
              orderId={note.order_id}
              currentNoteId={note.id}
              currentTabAssignee={currentTabAssignee}
              onResolve={onResolve}
            />
          )}
        </div>
      )}
    </div>
  )
}

// @MX:ANCHOR: [AUTO] LineItem notes page — tab UI for CS / 발주 / 타출판사 with Excel export
// @MX:REASON: Fan-in >= 3 — routed from router, linked from Sidebar, and used via useUnresolvedLineItemNotes hook
export function LineItemNotesPage() {
  const [activeTab, setActiveTab] = useState<Tab>('CS')
  const [downloading, setDownloading] = useState<string | null>(null)
  const { data, isPending, isError } = useUnresolvedLineItemNotes()
  const { mutate: resolveNote, isPending: isResolving } = useResolveLineItemNote()
  const queryClient = useQueryClient()

  const tabNotes = data ? filterNotes(data, activeTab) : []

  async function handleExport(publisher: 'agape' | 'sungseoyunion' | 'other') {
    setDownloading(publisher)
    try {
      await downloadLineItemNotesExcel(publisher)
      queryClient.invalidateQueries({ queryKey: LINE_ITEM_NOTES_QUERY_KEY })
    } finally {
      setDownloading(null)
    }
  }

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

  const tabs: Tab[] = ['CS', '발주', '타출판사']
  const countByTab = (tab: Tab) => (data ? filterNotes(data, tab).length : 0)

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold">미해결 품목 메모</h1>
        <p className="text-sm text-muted-foreground mt-0.5">전체 {data?.length ?? 0}건</p>
      </div>

      {/* 탭 */}
      <div className="flex gap-1 border-b">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab
                ? 'border-foreground text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab}
            <span className="ml-1.5 text-xs text-muted-foreground">({countByTab(tab)})</span>
          </button>
        ))}
      </div>

      {/* 타출판사 엑셀 다운로드 */}
      {activeTab === '타출판사' && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-muted-foreground">엑셀 다운로드:</span>
          {(
            [
              { publisher: 'agape' as const, label: '아가페' },
              { publisher: 'sungseoyunion' as const, label: '성서유니온' },
              { publisher: 'other' as const, label: '기타' },
            ] as const
          ).map(({ publisher, label }) => (
            <button
              key={publisher}
              onClick={() => handleExport(publisher)}
              disabled={downloading !== null}
              className="text-sm border rounded px-3 py-1.5 font-medium hover:bg-blue-50 hover:border-blue-400 hover:text-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {downloading === publisher ? '다운로드 중...' : label}
            </button>
          ))}
        </div>
      )}

      {tabNotes.length === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          미해결 품목 메모가 없습니다.
        </div>
      )}

      <div className="space-y-2">
        {tabNotes.map((note) => (
          <NoteCard
            key={note.id}
            note={note}
            onResolve={resolveNote}
            isResolving={isResolving}
            showAddForm={activeTab === 'CS' || activeTab === '발주'}
            currentTabAssignee={activeTab === '발주' ? '발주' : 'CS'}
          />
        ))}
      </div>
    </div>
  )
}
