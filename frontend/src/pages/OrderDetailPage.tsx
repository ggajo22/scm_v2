import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useOrderDetail, ORDER_DETAIL_QUERY_KEY } from '@/features/order/hooks/useOrderDetail'
import { useCreateLineItemNote, useResolveLineItemNote } from '@/features/order/hooks/useLineItemNotes'
import type { AxiosError } from 'axios'
import type { LineItemNote, LineItemNoteAssignee } from '@/types/order'
import { ASSIGNEE_NOTE_TYPES } from '@/types/order'
import { api } from '@/lib/axios'

const ASSIGNEE_CHOICES: LineItemNoteAssignee[] = ['CS', '발주', '한국창고', '미국창고']

const ASSIGNEE_COLORS: Record<LineItemNoteAssignee, string> = {
  CS: 'bg-blue-100 text-blue-700',
  발주: 'bg-orange-100 text-orange-700',
  한국창고: 'bg-green-100 text-green-700',
  미국창고: 'bg-purple-100 text-purple-700',
}

const FINANCIAL_STATUS_LABELS: Record<string, string> = {
  paid: '결제완료',
  pending: '결제대기',
  refunded: '환불',
  partially_refunded: '부분환불',
  authorized: '승인',
  partially_paid: '부분결제',
  voided: '취소',
}

const FULFILLMENT_STATUS_LABELS: Record<string, string> = {
  fulfilled: '출고완료',
  partial: '부분출고',
  restocked: '재입고',
  unfulfilled: '미출고',
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatPrice(value: string | null, currency?: string | null): string {
  if (!value) return '-'
  const num = Number(value).toLocaleString()
  return currency ? `${num} ${currency}` : num
}

// @MX:ANCHOR: [AUTO] OrderDetailPage — entry point for order detail route /orders/:id
// @MX:REASON: Lazy-loaded from router; exported name must stay stable for dynamic import
export function OrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const orderId = Number(id)
  const { data, isPending, isError, error, refetch } = useOrderDetail(orderId)

  const queryClient = useQueryClient()
  const [syncError, setSyncError] = useState<string | null>(null)
  const [expandedNotes, setExpandedNotes] = useState<Set<number>>(new Set())
  const [noteContents, setNoteContents] = useState<Record<number, string>>({})
  const [noteAssignees, setNoteAssignees] = useState<Record<number, LineItemNoteAssignee>>({})
  const [noteTypes, setNoteTypes] = useState<Record<number, string>>({})

  const { mutate: resolveLineItemNote } = useResolveLineItemNote()

  const { mutate: resync, isPending: isSyncing } = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/api/orders/${orderId}/sync/`)
      return res.data
    },
    onSuccess: () => {
      setSyncError(null)
      queryClient.invalidateQueries({ queryKey: [...ORDER_DETAIL_QUERY_KEY, orderId] })
    },
    onError: (err: unknown) => {
      const axiosErr = err as AxiosError<{ error?: string }>
      setSyncError(
        axiosErr.response?.data?.error ?? '동기화에 실패했습니다.',
      )
    },
  })

  if (isPending) {
    return (
      <div className="p-6 space-y-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-8 bg-muted animate-pulse rounded" />
        ))}
      </div>
    )
  }

  // error is unknown; narrow via AxiosError for HTTP status check
  if (isError && (error as AxiosError)?.response?.status === 404) {
    return (
      <div className="p-6 text-center space-y-4">
        <p className="text-muted-foreground">주문을 찾을 수 없습니다.</p>
        <button
          onClick={() => navigate('/orders')}
          className="text-sm text-primary underline"
        >
          주문 목록으로 돌아가기
        </button>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6 text-center space-y-4">
        <p className="text-destructive">주문 정보를 불러오는데 실패했습니다.</p>
        <button
          onClick={() => refetch()}
          className="text-sm border rounded px-3 py-1.5 hover:bg-muted"
        >
          다시 시도
        </button>
      </div>
    )
  }

  if (!data) return null

  const storeLabel = data.store_type === 'gimssine' ? 'GIMSSINE' : 'Etoile'
  const orderTitle = data.name ?? `#${data.order_number}`

  const shippingTotal = data.shipping_lines.reduce(
    (sum, sl) => sum + (sl.price ? Number(sl.price) : 0),
    0,
  )

  const totalRefunded = data.refunds.reduce(
    (sum, r) => sum + Number(r.subtotal ?? 0) + Number(r.total_tax ?? 0),
    0,
  )
  const netPaidAmount = Number(data.total_price ?? 0) - totalRefunded

  const isRefundStatus =
    data.has_refund ||
    data.financial_status === 'refunded' ||
    data.financial_status === 'partially_refunded'

  const refundedLineItemIds = new Set(
    data.refunds
      .filter(r => r.line_item_id != null)
      .map(r => r.line_item_id as number)
  )
  const normalItems = data.line_items.filter(
    item => !refundedLineItemIds.has(item.shopify_line_item_id)
  )
  const refundedItems = data.line_items.filter(
    item => refundedLineItemIds.has(item.shopify_line_item_id)
  )
  const unmatchedRefunds = data.refunds.filter(
    r => r.line_item_id == null || !refundedLineItemIds.has(r.line_item_id)
  )

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <button
            onClick={() => navigate('/orders')}
            className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
          >
            ← 주문 목록
          </button>
          <h1 className="text-xl font-semibold">{orderTitle}</h1>
          <span className="text-sm text-muted-foreground">{storeLabel}</span>
        </div>
        <div className="flex gap-2 items-start flex-col">
          <div className="flex gap-2">
            {data.financial_status && (
              <span
                className={`text-xs px-2 py-1 rounded border font-medium ${
                  isRefundStatus
                    ? 'border-red-300 text-red-700 bg-red-50'
                    : data.financial_status === 'paid'
                      ? 'border-green-300 text-green-700 bg-green-50'
                      : 'border-gray-300 text-gray-700 bg-gray-50'
                }`}
              >
                {FINANCIAL_STATUS_LABELS[data.financial_status] ?? data.financial_status}
              </span>
            )}
            {data.fulfillment_status && (
              <span className="text-xs px-2 py-1 rounded border border-blue-300 text-blue-700 bg-blue-50 font-medium">
                {FULFILLMENT_STATUS_LABELS[data.fulfillment_status] ?? data.fulfillment_status}
              </span>
            )}
            <button
              onClick={() => resync()}
              disabled={isSyncing}
              className="text-xs px-2 py-1 rounded border border-gray-300 text-gray-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSyncing ? '동기화 중...' : '다시 동기화'}
            </button>
          </div>
          {syncError && (
            <p className="text-xs text-destructive">{syncError}</p>
          )}
        </div>
      </div>

      {/* Section 1: 주문 정보 */}
      <section className="border rounded-lg p-4 space-y-2">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">주문 정보</h2>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-muted-foreground">주문번호</div>
          <div className="font-mono">{data.order_number ?? '-'}</div>
          <div className="text-muted-foreground">주문일시</div>
          <div>{formatDate(data.shopify_created_at)}</div>
          <div className="text-muted-foreground">결제수단</div>
          <div>{data.gateway ?? '-'}</div>
          {data.note && (
            <>
              <div className="text-muted-foreground">메모</div>
              <div className="whitespace-pre-wrap">{data.note}</div>
            </>
          )}
        </div>
      </section>

      {/* Section 2: 상품 목록 */}
      <section className="border rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">상품 목록</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-2 px-3 text-left font-medium">도서명</th>
                <th className="py-2 px-3 text-left font-medium">SKU</th>
                <th className="py-2 px-3 text-left font-medium">위치</th>
                <th className="py-2 px-3 text-right font-medium">수량</th>
                <th className="py-2 px-3 text-right font-medium">단가</th>
                <th className="py-2 px-3 text-right font-medium">할인</th>
                <th className="py-2 px-3 text-right font-medium">소계</th>
                <th className="py-2 px-3 text-right font-medium">확정 단가</th>
                <th className="py-2 px-3 text-left font-medium">확정 발주처</th>
              </tr>
            </thead>
            <tbody>
              {normalItems.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-4 text-center text-muted-foreground text-xs">
                    상품 없음
                  </td>
                </tr>
              )}
              {normalItems.map((item) => {
                const subtotal =
                  Number(item.price ?? 0) * (item.quantity ?? 0) -
                  Number(item.total_discount ?? 0)
                const isExpanded = expandedNotes.has(item.id)
                const notes: LineItemNote[] = item.notes ?? []
                const noteCount = notes.length
                return (
                  <>
                    <tr key={item.id} className="border-b">
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-2">
                          <div>{item.title ?? '-'}</div>
                          <button
                            onClick={() =>
                              setExpandedNotes((prev) => {
                                const next = new Set(prev)
                                if (next.has(item.id)) next.delete(item.id)
                                else next.add(item.id)
                                return next
                              })
                            }
                            className={`text-xs px-1.5 py-0.5 rounded font-medium transition-colors ${
                              noteCount > 0
                                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                                : 'bg-muted text-muted-foreground hover:bg-muted/80'
                            }`}
                          >
                            노트 {noteCount}
                          </button>
                        </div>
                        {item.variant_title && (
                          <div className="text-xs text-muted-foreground">{item.variant_title}</div>
                        )}
                      </td>
                      <td className="py-2 px-3 font-mono text-xs text-muted-foreground">
                        {item.sku ?? '-'}
                      </td>
                      <td className="py-2 px-3">
                        {item.location
                          ? <span className="text-xs font-mono">{item.location}</span>
                          : <span className="text-xs text-muted-foreground">-</span>}
                      </td>
                      <td className="py-2 px-3 text-right">{item.quantity ?? '-'}</td>
                      <td className="py-2 px-3 text-right">{formatPrice(item.price)}</td>
                      <td className="py-2 px-3 text-right text-red-600">
                        {item.total_discount && Number(item.total_discount) > 0
                          ? `-${formatPrice(item.total_discount)}`
                          : '-'}
                      </td>
                      <td className="py-2 px-3 text-right font-medium">
                        {subtotal.toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {item.confirmed_price !== null
                          ? `${Number(item.confirmed_price).toLocaleString()}원`
                          : '—'}
                      </td>
                      <td className="py-2 px-3">
                        {item.confirmed_distributor !== null ? item.confirmed_distributor : '—'}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${item.id}-notes`} className="border-b bg-muted/20">
                        <td colSpan={9} className="py-3 px-4">
                          <LineItemNotePanel
                            lineItemId={item.id}
                            orderId={orderId}
                            notes={notes}
                            noteContent={noteContents[item.id] ?? ''}
                            noteAssignee={noteAssignees[item.id] ?? 'CS'}
                            noteType={noteTypes[item.id] ?? ''}
                            onContentChange={(v) =>
                              setNoteContents((prev) => ({ ...prev, [item.id]: v }))
                            }
                            onAssigneeChange={(v) => {
                              setNoteAssignees((prev) => ({ ...prev, [item.id]: v }))
                              setNoteTypes((prev) => ({ ...prev, [item.id]: '' }))
                            }}
                            onNoteTypeChange={(v) =>
                              setNoteTypes((prev) => ({ ...prev, [item.id]: v }))
                            }
                            onResolve={(noteId) => resolveLineItemNote(noteId)}
                          />
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 2-B: 환불 목록 */}
      {(refundedItems.length > 0 || unmatchedRefunds.length > 0) && (
        <section className="border rounded-lg p-4 space-y-3 border-red-200">
          <h2 className="text-sm font-semibold text-red-600 uppercase tracking-wide">환불 목록</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b bg-red-50/50">
                  <th className="py-2 px-3 text-left font-medium">도서명</th>
                  <th className="py-2 px-3 text-left font-medium">SKU</th>
                  <th className="py-2 px-3 text-right font-medium">수량</th>
                  <th className="py-2 px-3 text-right font-medium">환불금액</th>
                  <th className="py-2 px-3 text-left font-medium">메모</th>
                </tr>
              </thead>
              <tbody>
                {refundedItems.map((item) => {
                  const refund = data.refunds.find(
                    r => r.line_item_id === item.shopify_line_item_id
                  )
                  return (
                    <tr key={item.id} className="border-b last:border-0">
                      <td className="py-2 px-3">
                        <div>{item.title ?? '-'}</div>
                        {item.variant_title && (
                          <div className="text-xs text-muted-foreground">{item.variant_title}</div>
                        )}
                      </td>
                      <td className="py-2 px-3 font-mono text-xs text-muted-foreground">
                        {item.sku ?? '-'}
                      </td>
                      <td className="py-2 px-3 text-right">{refund?.quantity ?? item.quantity ?? '-'}</td>
                      <td className="py-2 px-3 text-right font-medium text-red-600">
                        {refund?.subtotal ? formatPrice(refund.subtotal) : '-'}
                      </td>
                      <td className="py-2 px-3 text-muted-foreground text-xs">
                        {refund?.note ?? '-'}
                      </td>
                    </tr>
                  )
                })}
                {unmatchedRefunds.map((refund) => (
                  <tr key={refund.shopify_refund_id} className="border-b last:border-0">
                    <td className="py-2 px-3 text-muted-foreground italic" colSpan={2}>
                      상품 정보 없음
                    </td>
                    <td className="py-2 px-3 text-right">-</td>
                    <td className="py-2 px-3 text-right font-medium text-red-600">
                      {refund.subtotal ? formatPrice(refund.subtotal) : '-'}
                    </td>
                    <td className="py-2 px-3 text-muted-foreground text-xs">
                      {refund.note ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Section 3: 결제 정보 */}
      <section className="border rounded-lg p-4 space-y-2">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">결제 정보</h2>
        <div className="text-sm space-y-1 max-w-xs ml-auto">
          <div className="flex justify-between font-semibold">
            <span>최종 결제 금액</span>
            <span>{netPaidAmount.toLocaleString()}{data.currency ? ` ${data.currency}` : ''}</span>
          </div>
          <div className="flex justify-between text-muted-foreground">
            <span>마진</span>
            <span>
              {data.margin_amount !== null
                ? `${Number(data.margin_amount).toLocaleString()} USD`
                : '—'}
            </span>
          </div>
          <div className="flex justify-between text-muted-foreground">
            <span>마진율</span>
            <span>
              {data.margin_rate !== null ? `${data.margin_rate}%` : '—'}
            </span>
          </div>
        </div>
      </section>

      {/* Section 4: 배송 정보 */}
      {data.shipping_address && (
        <section className="border rounded-lg p-4 space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">배송 정보</h2>
          <div className="text-sm space-y-1">
            <p className="font-medium">
              {data.shipping_address.name ??
                `${data.shipping_address.last_name ?? ''}${data.shipping_address.first_name ?? ''}`.trim()}
            </p>
            <p className="text-muted-foreground">
              {[data.shipping_address.address1, data.shipping_address.address2]
                .filter(Boolean)
                .join(' ')}
            </p>
            <p className="text-muted-foreground">
              {[
                data.shipping_address.city,
                data.shipping_address.province,
                data.shipping_address.zip,
              ]
                .filter(Boolean)
                .join(' ')}
            </p>
            {data.shipping_address.phone && (
              <p className="text-muted-foreground">{data.shipping_address.phone}</p>
            )}
          </div>
        </section>
      )}

      {/* Section 5: 고객 정보 */}
      {data.customer && (
        <section className="border rounded-lg p-4 space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">고객 정보</h2>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-muted-foreground">이름</div>
            <div>
              {`${data.customer.last_name ?? ''}${data.customer.first_name ?? ''}`.trim() || '-'}
            </div>
            <div className="text-muted-foreground">이메일</div>
            <div>{data.customer.email ?? '-'}</div>
            <div className="text-muted-foreground">연락처</div>
            <div>{data.customer.phone ?? '-'}</div>
          </div>
        </section>
      )}

    </div>
  )
}

// ---------------------------------------------------------------------------
// LineItemNotePanel — inline note list + add form for a single line item
// ---------------------------------------------------------------------------

interface LineItemNotePanelProps {
  lineItemId: number
  orderId: number
  notes: LineItemNote[]
  noteContent: string
  noteAssignee: LineItemNoteAssignee
  noteType: string
  onContentChange: (v: string) => void
  onAssigneeChange: (v: LineItemNoteAssignee) => void
  onNoteTypeChange: (v: string) => void
  onResolve: (noteId: number) => void
}

function LineItemNotePanel({
  lineItemId,
  orderId,
  notes,
  noteContent,
  noteAssignee,
  noteType,
  onContentChange,
  onAssigneeChange,
  onNoteTypeChange,
  onResolve,
}: LineItemNotePanelProps) {
  const { mutate: createNote, isPending } = useCreateLineItemNote(lineItemId, orderId)
  const availableTypes = ASSIGNEE_NOTE_TYPES[noteAssignee] ?? []

  const handleSubmit = () => {
    if (!noteContent.trim()) return
    createNote(
      { content: noteContent.trim(), assignee: noteAssignee, note_type: noteType || undefined },
      { onSuccess: () => onContentChange('') },
    )
  }

  return (
    <div className="space-y-3">
      {notes.length === 0 && (
        <p className="text-xs text-muted-foreground">노트 없음</p>
      )}
      {notes.map((note) => (
        <div key={note.id} className="flex items-start justify-between gap-3 text-sm">
          <div className="flex-1 space-y-0.5">
            <div className="flex items-center gap-2">
              {note.assignee && (
                <span
                  className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                    ASSIGNEE_COLORS[note.assignee as LineItemNoteAssignee] ?? 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {note.assignee}
                </span>
              )}
              {note.note_type && (
                <span className="text-xs px-1.5 py-0.5 rounded border font-medium bg-gray-100 text-gray-700 border-gray-200">
                  {note.note_type}
                </span>
              )}
              {note.author_username && (
                <span className="text-xs text-muted-foreground">{note.author_username}</span>
              )}
              <span className="text-xs text-muted-foreground">
                {new Date(note.created_at).toLocaleDateString('ko-KR')}
              </span>
            </div>
            <p className="whitespace-pre-wrap">{note.content}</p>
          </div>
          {!note.is_resolved && (
            <button
              onClick={() => onResolve(note.id)}
              className="shrink-0 text-xs border rounded px-2 py-1 hover:bg-green-50 hover:border-green-400 hover:text-green-700 transition-colors"
            >
              해결
            </button>
          )}
        </div>
      ))}

      {/* Add note form */}
      <div className="flex gap-2 pt-2 border-t">
        <select
          value={noteAssignee}
          onChange={(e) => onAssigneeChange(e.target.value as LineItemNoteAssignee)}
          className="text-xs border rounded px-2 py-1.5 bg-background"
        >
          {ASSIGNEE_CHOICES.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        {availableTypes.length > 0 && (
          <select
            value={noteType}
            onChange={(e) => onNoteTypeChange(e.target.value)}
            className="text-xs border rounded px-2 py-1.5 bg-background"
          >
            <option value="">유형 선택</option>
            {availableTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        )}
        <textarea
          value={noteContent}
          onChange={(e) => onContentChange(e.target.value)}
          placeholder="노트 추가..."
          rows={2}
          className="flex-1 text-sm border rounded px-2 py-1.5 resize-none bg-background focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <button
          onClick={handleSubmit}
          disabled={isPending || !noteContent.trim()}
          className="shrink-0 text-sm border rounded px-3 py-1.5 font-medium hover:bg-blue-50 hover:border-blue-400 hover:text-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          추가
        </button>
      </div>
    </div>
  )
}
