import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useOrderDetail, ORDER_DETAIL_QUERY_KEY } from '@/features/order/hooks/useOrderDetail'
import type { AxiosError } from 'axios'
import { api } from '@/lib/axios'

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

  const isRefundStatus =
    data.has_refund ||
    data.financial_status === 'refunded' ||
    data.financial_status === 'partially_refunded'

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
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
                <th className="py-2 px-3 text-right font-medium">수량</th>
                <th className="py-2 px-3 text-right font-medium">단가</th>
                <th className="py-2 px-3 text-right font-medium">할인</th>
                <th className="py-2 px-3 text-right font-medium">소계</th>
              </tr>
            </thead>
            <tbody>
              {data.line_items.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-muted-foreground text-xs">
                    상품 없음
                  </td>
                </tr>
              )}
              {data.line_items.map((item) => {
                const subtotal =
                  Number(item.price ?? 0) * (item.quantity ?? 0) -
                  Number(item.total_discount ?? 0)
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
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 3: 결제 정보 */}
      <section className="border rounded-lg p-4 space-y-2">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">결제 정보</h2>
        <div className="text-sm space-y-1 max-w-xs ml-auto">
          <div className="flex justify-between">
            <span className="text-muted-foreground">소계</span>
            <span>{formatPrice(data.subtotal_price, data.currency)}</span>
          </div>
          {data.total_discounts && Number(data.total_discounts) > 0 && (
            <div className="flex justify-between text-red-600">
              <span>할인</span>
              <span>-{formatPrice(data.total_discounts)}</span>
            </div>
          )}
          {shippingTotal > 0 && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">배송비</span>
              <span>{shippingTotal.toLocaleString()}</span>
            </div>
          )}
          {data.total_tax && Number(data.total_tax) > 0 && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">세금</span>
              <span>{formatPrice(data.total_tax)}</span>
            </div>
          )}
          <div className="flex justify-between font-semibold border-t pt-1 mt-1">
            <span>합계</span>
            <span>{formatPrice(data.total_price, data.currency)}</span>
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

      {/* Section 6: 환불 내역 (conditional) */}
      {data.has_refund && data.refunds.length > 0 && (
        <section className="border rounded-lg p-4 space-y-3 border-red-200">
          <h2 className="text-sm font-semibold text-red-600 uppercase tracking-wide">환불 내역</h2>
          <div className="space-y-3">
            {data.refunds.map((refund) => (
              <div
                key={refund.shopify_refund_id}
                className="text-sm border-b last:border-0 pb-2"
              >
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    {formatDate(refund.shopify_created_at)}
                  </span>
                  <span className="font-medium">{formatPrice(refund.subtotal)}</span>
                </div>
                {refund.note && (
                  <p className="text-muted-foreground mt-1">{refund.note}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
