import type { OutboundForceCandidate, OutboundUnmatchedItem } from '@/services/outboundApi'
import { LOGISTICS_STATUS_LABELS } from './logisticsStatusLabels'

// SPEC-ORDER-016 REQ-FORCE-001/019: a row may be force-outbounded iff its
// matching-failure reason is exactly `line_item_not_found` AND its requested
// quantity is positive. Every other reason (order_not_found,
// multiple_line_items, invalid_total, invalid_row) and every non-positive
// quantity is ineligible, regardless of how the row otherwise looks. This is
// entirely a client-side judgement (설계 결정 J) — the server never
// re-derives a row's original matching-failure reason.
// eslint-disable-next-line react-refresh/only-export-components
export function isForceEligible(item: OutboundUnmatchedItem): boolean {
  return item.reason === 'line_item_not_found' && item.total > 0
}

// SPEC-ORDER-016 설계 결정 G: the client-side selection key is
// (order identifier, sku) — never an array index. Kept as a plain string so
// it can key a Set/Record without a custom equality function.
// eslint-disable-next-line react-refresh/only-export-components
export function buildForceSelectionKey(name: string, sku: string): string {
  return `${name} ${sku}`
}

export interface UnmatchedForceSectionProps {
  items: OutboundUnmatchedItem[]
  reasonLabels: Record<string, string>
  candidatesByOrder: Map<string, OutboundForceCandidate[]>
  selectedKeys: Set<string>
  targetByKey: Record<string, number>
  onToggleSelect: (key: string) => void
  onToggleSelectAll: () => void
  onAssignTarget: (key: string, lineItemId: number | undefined) => void
}

// @MX:NOTE: [AUTO] Deliberately NOT built on the shared `ResultSection`
// row renderer (frontend/src/pages/OutboundPage/index.tsx) — its row
// contract is `cells: string[]`, which has no slot for a checkbox or a
// target picker, and widening that contract would touch every consumer of
// that renderer for a need specific to this one section. This component
// reproduces the section's title/count/tone/column-header treatment by hand
// instead, so the unmatched section stays visually consistent with the
// matched/quantity-exceeded sections it sits next to (설계 결정 M).
export function UnmatchedForceSection({
  items,
  reasonLabels,
  candidatesByOrder,
  selectedKeys,
  targetByKey,
  onToggleSelect,
  onToggleSelectAll,
  onAssignTarget,
}: UnmatchedForceSectionProps) {
  const eligibleKeys = items
    .filter(isForceEligible)
    .map((item) => buildForceSelectionKey(item.name, item.sku))
  const allEligibleSelected =
    eligibleKeys.length > 0 && eligibleKeys.every((key) => selectedKeys.has(key))

  return (
    <section
      data-testid="outbound-unmatched"
      aria-label="매칭 실패"
      className="rounded border border-amber-300 bg-amber-50 p-3 space-y-2"
    >
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">매칭 실패</h3>
        <span className="text-sm text-muted-foreground">{`${items.length}건`}</span>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">해당 항목이 없습니다.</p>
      ) : (
        <div className="overflow-x-auto rounded border bg-background">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="py-2 px-3 text-left w-10">
                  <input
                    type="checkbox"
                    checked={allEligibleSelected}
                    onChange={onToggleSelectAll}
                    aria-label="전체 선택"
                    className="cursor-pointer"
                  />
                </th>
                <th className="py-2 px-3 text-left font-medium">주문번호</th>
                <th className="py-2 px-3 text-left font-medium">SKU</th>
                <th className="py-2 px-3 text-left font-medium">요청 수량</th>
                <th className="py-2 px-3 text-left font-medium">사유</th>
                <th className="py-2 px-3 text-left font-medium">대상 지정</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                const key = buildForceSelectionKey(item.name, item.sku)
                const eligible = isForceEligible(item)
                const candidates = candidatesByOrder.get(item.name) ?? []
                return (
                  <tr
                    key={`${item.name}-${item.sku}-${index}`}
                    className="border-b last:border-0"
                  >
                    <td className="py-2 px-3">
                      {eligible && (
                        <input
                          type="checkbox"
                          checked={selectedKeys.has(key)}
                          onChange={() => onToggleSelect(key)}
                          aria-label={`${item.name} ${item.sku} 선택`}
                          className="cursor-pointer"
                        />
                      )}
                    </td>
                    <td className="py-2 px-3 font-mono text-xs">{item.name}</td>
                    <td className="py-2 px-3 font-mono text-xs">{item.sku}</td>
                    <td className="py-2 px-3 font-mono text-xs">{String(item.total)}</td>
                    <td className="py-2 px-3 font-mono text-xs">
                      {reasonLabels[item.reason] ?? item.reason}
                    </td>
                    <td className="py-2 px-3">
                      {eligible && (
                        <select
                          aria-label={`${item.name} ${item.sku} 대상 지정`}
                          value={targetByKey[key] ?? ''}
                          onChange={(e) =>
                            onAssignTarget(
                              key,
                              e.target.value === '' ? undefined : Number(e.target.value)
                            )
                          }
                          className="border rounded px-2 py-1 text-xs"
                        >
                          <option value="">대상 선택</option>
                          {candidates.map((candidate) => (
                            <option key={candidate.line_item_id} value={candidate.line_item_id}>
                              {`${candidate.title ?? ''} / ${candidate.sku} / 주문 ${candidate.quantity ?? 0} / 기출고 ${candidate.shipped_quantity} / ${LOGISTICS_STATUS_LABELS[candidate.logistics_status] ?? candidate.logistics_status}${candidate.no_remaining_capacity ? ' / 잔여 용량 없음' : ''}`}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
