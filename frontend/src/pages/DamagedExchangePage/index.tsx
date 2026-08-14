import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  useSearchDamagedExchange,
  useSubmitDamagedExchange,
} from '@/hooks/useDamagedExchangeQueries'
import type { DamagedExchangeSearchResultRow } from '@/services/damagedExchangeApi'

// SPEC-PURCHASE-ORDER-011: standalone damaged-exchange intake page
// (REQ-DEX-002/003). Deliberately shares nothing with /outbound or
// /rack-number (SPEC-ORDER-013/014/015) — no OutboundPage/RackNumberPage
// component, no outboundApi/rackNumberApi/useOutboundQueries/
// useRackNumberQueries import (REQ-DEX-002, AC-DEX-002). Only shared
// primitives (ui/button, lib/axios via the service layer) are reused.
// @MX:ANCHOR: [AUTO] DamagedExchangePage — entry point for the /damaged-exchange route
// @MX:REASON: Lazy-loaded from router via named export destructure
// (`const { DamagedExchangePage } = await import('@/pages/DamagedExchangePage')`)
// — this export name and the folder+index.tsx module resolution must not
// change without also updating router/index.tsx.
export function DamagedExchangePage() {
  const [searchInput, setSearchInput] = useState('')
  const [submittedSku, setSubmittedSku] = useState<string | null>(null)

  const { data, isFetching, isError } = useSearchDamagedExchange(submittedSku)
  const submitMutation = useSubmitDamagedExchange()

  const results = data?.results ?? []
  const searched = submittedSku !== null
  const notFound = searched && !isFetching && !isError && results.length === 0

  const handleSearch = () => {
    const trimmed = searchInput.trim()
    if (!trimmed) return
    setSubmittedSku(trimmed)
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">파손 교환 접수</h1>
        <p className="text-sm text-muted-foreground">
          ISBN으로 미출고 품목을 검색해 파손/교환 수량을 접수합니다.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSearch()
          }}
          placeholder="ISBN 검색"
          aria-label="ISBN 검색"
          className="border rounded px-2 py-1 text-sm"
        />
        <Button size="sm" onClick={handleSearch}>
          검색
        </Button>
        {isFetching && <span className="text-sm text-muted-foreground">검색 중...</span>}
      </div>

      {isError && <p className="text-sm text-destructive">검색 중 오류가 발생했습니다.</p>}

      {notFound && (
        <p className="text-sm text-muted-foreground">일치하는 품목을 찾을 수 없습니다.</p>
      )}

      {searched && results.length > 0 && (
        <div className="overflow-x-auto rounded border">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-2 px-3 text-left font-medium">주문번호</th>
                <th className="py-2 px-3 text-left font-medium">SKU</th>
                <th className="py-2 px-3 text-left font-medium">도서명</th>
                <th className="py-2 px-3 text-right font-medium">주문 수량</th>
                <th className="py-2 px-3 text-left font-medium">오늘 출고 가능 여부</th>
                <th className="py-2 px-3 text-right font-medium">전체 출고 수량</th>
                <th className="py-2 px-3 text-left font-medium">상태</th>
                <th className="py-2 px-3 text-left font-medium">파손 수량 접수</th>
              </tr>
            </thead>
            <tbody>
              {results.map((row) => (
                <DamagedExchangeRow
                  key={row.id}
                  row={row}
                  isSubmitting={submitMutation.isPending}
                  onSubmit={(damagedQuantity) =>
                    submitMutation.mutate({ id: row.id, damagedQuantity })
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// REQ-DEX-008: damage-quantity input pre-filled with `1`. Client-side range
// validation (1..row.quantity inclusive) only disables the submit button
// early — the server enforces the same range authoritatively either way
// (AC-DEX-008), so a bypassed/disabled client check alone cannot corrupt
// data.
function DamagedExchangeRow({
  row,
  isSubmitting,
  onSubmit,
}: {
  row: DamagedExchangeSearchResultRow
  isSubmitting: boolean
  onSubmit: (damagedQuantity: number) => void
}) {
  const [value, setValue] = useState('1')
  const maxQuantity = row.quantity ?? 0
  const parsed = parseInt(value, 10)
  const isValid = !isNaN(parsed) && parsed >= 1 && parsed <= maxQuantity

  return (
    <tr className="border-b last:border-0 hover:bg-muted/30">
      <td className="py-2 px-3 font-mono text-xs">{row.order_name ?? '-'}</td>
      <td className="py-2 px-3 font-mono text-xs">{row.sku}</td>
      <td className="py-2 px-3 max-w-xs truncate" title={row.title}>
        {row.title}
      </td>
      <td className="py-2 px-3 text-right">{row.quantity ?? '-'}</td>
      <td className="py-2 px-3">
        {/* REQ-DEX-006/AC-DEX-005a: 3-state — true/false/null rendered
            distinctly; null must never collapse into "출고불가". */}
        {row.order_ready_to_ship === true && (
          <span className="text-xs px-2 py-1 rounded border border-emerald-300 text-emerald-700 bg-emerald-50 font-medium">
            출고가능
          </span>
        )}
        {row.order_ready_to_ship === false && (
          <span className="text-xs px-2 py-1 rounded border border-red-300 text-red-700 bg-red-50 font-medium">
            출고불가
          </span>
        )}
        {row.order_ready_to_ship === null && (
          <span className="text-xs text-muted-foreground">미확정</span>
        )}
      </td>
      <td className="py-2 px-3 text-right">{row.order_total_quantity}</td>
      <td className="py-2 px-3">
        {/* REQ-DEX-005a: badge distinguishing rows already at damaged_exchange. */}
        {row.is_damaged_exchange && (
          <span className="text-xs bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">
            파손/교환 접수됨
          </span>
        )}
      </td>
      <td className="py-2 px-3">
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={maxQuantity || undefined}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            aria-label={`${row.sku} 파손 수량`}
            className="border rounded px-2 py-1 text-sm w-20"
          />
          <Button size="sm" disabled={!isValid || isSubmitting} onClick={() => onSubmit(parsed)}>
            접수
          </Button>
        </div>
      </td>
    </tr>
  )
}
