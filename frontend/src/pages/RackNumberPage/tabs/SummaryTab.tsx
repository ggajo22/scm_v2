import { useRackNumberSummary } from '@/hooks/useRackNumberQueries'
import { LOGISTICS_STATUS_OPTIONS } from '@/services/purchaseOrderApi'
import type { RackNumberSummaryGroup } from '@/services/rackNumberApi'

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

  return (
    <div className="space-y-2">
      <div className="flex items-baseline gap-2">
        <h2 className="text-sm font-semibold">{label}</h2>
        <span className="text-sm text-muted-foreground">총 {group.total_quantity}권</span>
      </div>

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
            {group.line_items.map((item) => (
              <tr key={item.id} className="border-b last:border-0 hover:bg-muted/30">
                <td className="py-2 px-3">{item.order_number ?? '-'}</td>
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
    </div>
  )
}
