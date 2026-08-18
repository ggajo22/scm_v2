import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { useRackNumberSummary } from '@/hooks/useRackNumberQueries'
import { LOGISTICS_STATUS_OPTIONS } from '@/services/purchaseOrderApi'
import type { RackNumberSummaryGroup } from '@/services/rackNumberApi'
import { cn } from '@/lib/utils'

// Local label map reusing the shared LOGISTICS_STATUS_OPTIONS source of
// truth — same construction pattern as OrderDetailPage.tsx's
// LOGISTICS_STATUS_LABELS (that file is not modified, only the pattern is
// reused here).
const LOGISTICS_STATUS_LABELS: Record<string, string> = LOGISTICS_STATUS_OPTIONS.reduce(
  (acc, opt) => ({ ...acc, [opt.value]: opt.label }),
  {} as Record<string, string>
)

// SPEC-ORDER-014: read-only "렉번호 요약" tab (REQ-RACKSUM-010/011/011a/012/013).
// @MX:NOTE: [AUTO] Tab2 is intentionally read-only — no checkbox, bulk-apply,
// or inline-edit input is rendered anywhere in this file (REQ-RACKSUM-014/015).
// The only way to change `rack_number` remains SearchTab (Tab1).
export function SummaryTab() {
  const { data, isPending } = useRackNumberSummary()
  const groups = data?.groups ?? []

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">렉번호 요약</h1>
        <p className="text-sm text-muted-foreground">
          미출고 품목을 렉번호 기준으로 전체 주문에 걸쳐 집계합니다.
        </p>
      </div>

      {isPending && (
        <div role="status" aria-label="로딩 중" className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-muted animate-pulse rounded" />
          ))}
        </div>
      )}

      {/* REQ-RACKSUM-013: empty-state message instead of an empty table. */}
      {!isPending && groups.length === 0 && (
        <p className="text-sm text-muted-foreground">미출고 품목이 없습니다.</p>
      )}

      {!isPending &&
        groups.map((group) => (
          <RackNumberSummaryGroupSection
            key={group.is_unassigned ? '__unassigned__' : group.rack_number}
            group={group}
          />
        ))}
    </div>
  )
}

function RackNumberSummaryGroupSection({ group }: { group: RackNumberSummaryGroup }) {
  // REQ-RACKSUM-011/011a: unassigned group uses a label distinct from every
  // named rack_number group.
  const label = group.is_unassigned ? '미지정' : group.rack_number

  // SPEC-ORDER-014 UX improvement: each group is collapsed by default and
  // toggled independently — no shared/cross-group state.
  const [expanded, setExpanded] = useState(false)

  // Alternate row shading whenever order_name changes vs. the previous row,
  // so visually adjacent line items from different orders are distinguishable.
  let previousOrderName: string | null = null
  let shadeToggle = false
  const rows = group.line_items.map((item) => {
    if (item.order_name !== previousOrderName) {
      shadeToggle = !shadeToggle
      previousOrderName = item.order_name
    }
    return { item, shaded: shadeToggle }
  })

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        className={cn(
          'w-full flex items-center gap-2 rounded-md px-1 py-1 text-left',
          'cursor-pointer hover:bg-muted/50 transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
      >
        <ChevronDown
          className={cn('h-3.5 w-3.5 transition-transform duration-200 shrink-0', !expanded && '-rotate-90')}
          aria-hidden="true"
        />
        <h2 className="text-sm font-semibold">{label}</h2>
        {/* SPEC-ORDER-027 REQ-RACKRECV-008/009/012: both values come straight
            from the API — no client-side arithmetic, guard, or reclamping.
            Kept as a single text node (not split into separate <span>s) so it
            does not collide with the exact-match "입고" assertion on the
            expanded row's logistics_status cell (D5). */}
        <span className="text-sm text-muted-foreground">
          입고 {group.received_quantity} / 총 {group.total_quantity}권
        </span>
      </button>

      {expanded && (
        <div className="overflow-x-auto rounded border">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-2 px-3 text-left font-medium">주문번호</th>
                <th className="py-2 px-3 text-left font-medium">SKU</th>
                <th className="py-2 px-3 text-left font-medium">도서명</th>
                <th className="py-2 px-3 text-left font-medium">수량</th>
                <th className="py-2 px-3 text-left font-medium">물류상태</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ item, shaded }) => (
                <tr
                  key={item.id}
                  className={cn('border-b last:border-0 hover:bg-muted/30', shaded && 'bg-muted/50')}
                >
                  <td className="py-2 px-3">{item.order_name ?? '-'}</td>
                  <td className="py-2 px-3 font-mono text-xs">{item.sku}</td>
                  <td className="py-2 px-3 max-w-xs truncate" title={item.title ?? undefined}>
                    {item.title}
                  </td>
                  <td className="py-2 px-3">{item.quantity}</td>
                  <td className="py-2 px-3">
                    {LOGISTICS_STATUS_LABELS[item.logistics_status] ?? item.logistics_status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
