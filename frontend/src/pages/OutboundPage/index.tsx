import { useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  useProcessOutboundManual,
  useUploadOutbound,
  useOutboundForceCandidates,
  useProcessOutboundForce,
} from '@/hooks/useOutboundQueries'
import type {
  OutboundForceCandidate,
  OutboundForceRowInput,
  OutboundProcessResponse,
  OutboundUnmatchedReason,
} from '@/services/outboundApi'
import { parseManualRows } from './parseManualRows'
import {
  UnmatchedForceSection,
  buildForceSelectionKey,
  isForceEligible,
} from './UnmatchedForceSection'

// REQ-OUTBOUND-017: each backend `reason` code gets its own Korean label so a
// failed row tells the operator *why* it failed, not just that it did.
// Record (not Partial) so adding a reason code to the union without a label
// here is a compile error rather than a raw snake_case string in the UI.
// Exported so UnmatchedForceSection (SPEC-ORDER-016) can reuse the same
// labels instead of duplicating this map (REQ-FORCE-021).
// eslint-disable-next-line react-refresh/only-export-components
export const UNMATCHED_REASON_LABELS: Record<OutboundUnmatchedReason, string> = {
  order_not_found: '주문 없음',
  line_item_not_found: 'SKU 불일치',
  multiple_line_items: '동일 SKU 복수 품목',
  invalid_total: '수량 오류',
  invalid_row: '행 형식 오류',
}

// SPEC-ORDER-016 REQ-FORCE-024/설계 결정 N: merges a successful force-execute
// response into the existing single result slot instead of appending to it
// (which would let the same physical shipment be recorded twice on a
// resubmit) or replacing it wholesale (which would silently discard
// unselected eligible rows and any pre-existing matched/quantity_exceeded
// entries — rejected alternatives recorded in 설계 결정 N). Only the value
// passed to the existing single `setResult` slot changes; the slot itself
// and its update mechanism are unchanged from the two existing submit paths.
function mergeForceOutboundResult(
  prev: OutboundProcessResponse,
  submittedRows: OutboundForceRowInput[],
  forceResult: OutboundProcessResponse
): OutboundProcessResponse {
  const submittedKeys = new Set(
    submittedRows.map((row) => buildForceSelectionKey(row.name, row.sku))
  )
  const unmatched = prev.unmatched.filter(
    (item) => !submittedKeys.has(buildForceSelectionKey(item.name, item.sku))
  )
  const matched = [...prev.matched, ...forceResult.matched]
  const quantity_exceeded = [...prev.quantity_exceeded, ...forceResult.quantity_exceeded]

  return {
    matched,
    matched_count: matched.length,
    unmatched,
    unmatched_count: unmatched.length,
    quantity_exceeded,
    quantity_exceeded_count: quantity_exceeded.length,
  }
}

// SPEC-ORDER-015: standalone outbound processing page (REQ-OUTBOUND-015).
// Deliberately shares nothing with /rack-number (SPEC-ORDER-013/014) — no tab
// shell, no RackNumberPage/rackNumberApi/useRackNumberQueries import — so the
// two features can evolve independently.
// @MX:ANCHOR: [AUTO] OutboundPage — entry point for the /outbound route
// @MX:REASON: Lazy-loaded from router via named export destructure
// (`const { OutboundPage } = await import('@/pages/OutboundPage')`) — this
// export name and the folder+index.tsx module resolution must not change
// without also updating router/index.tsx.
export function OutboundPage() {
  const [rawInput, setRawInput] = useState('')
  // REQ-OUTBOUND-018: one result slot shared by both submit paths, cleared by
  // the reset control so a new run needs no page reload.
  const [result, setResult] = useState<OutboundProcessResponse | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const processMutation = useProcessOutboundManual()
  const uploadMutation = useUploadOutbound()

  const handleSubmit = () => {
    const rows = parseManualRows(rawInput)
    if (rows.length === 0) return
    processMutation.mutate(rows, { onSuccess: setResult })
  }

  const handleUploadChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)
    uploadMutation.mutate(formData, {
      onSuccess: setResult,
      onSettled: () => {
        // Clear the input so re-picking the same file fires change again.
        if (fileInputRef.current) fileInputRef.current.value = ''
      },
    })
  }

  const handleReset = () => {
    setRawInput('')
    setResult(null)
  }

  const isBusy = processMutation.isPending || uploadMutation.isPending

  // SPEC-ORDER-016 설계 결정 G/H/K: force-outbound selection state lives
  // here as local `useState` (RackNumberPage/tabs/SearchTab.tsx convention),
  // never the global order store. The selection key is (order identifier,
  // sku) — NOT an array index; the render key `${name}-${sku}-${index}`
  // used below is a separate, purely presentational key. This selection key
  // exists only for client-side bookkeeping: the SERVER's own
  // aggregation/response key for a force request is different again — the
  // operator-designated target LineItem id (설계 결정 K) — so this key is
  // never sent in the request body. Both maps reset whenever a new result
  // lands, which also satisfies REQ-FORCE-024(e)'s "clear selection"
  // requirement after a successful force merge. Reset happens during render
  // (React's "adjusting state when a prop changes" pattern), not inside a
  // useEffect — an effect here would fire an extra, avoidable render:
  // https://react.dev/learn/you-might-not-need-an-effect#adjusting-state-when-a-prop-changes
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set())
  const [targetByKey, setTargetByKey] = useState<Record<string, number>>({})
  const [prevResult, setPrevResult] = useState(result)
  if (result !== prevResult) {
    setPrevResult(result)
    setSelectedKeys(new Set())
    setTargetByKey({})
  }

  const eligibleItems = useMemo(
    () => (result?.unmatched ?? []).filter(isForceEligible),
    [result]
  )
  // REQ-FORCE-003: the full, de-duplicated set of eligible rows' order
  // identifiers — recomputed only when the settled result changes, so the
  // candidate query below fires once per result, never per row.
  const eligibleOrderNames = useMemo(
    () => Array.from(new Set(eligibleItems.map((item) => item.name))),
    [eligibleItems]
  )
  const { data: candidateGroups } = useOutboundForceCandidates(eligibleOrderNames)
  const candidatesByOrder = useMemo(() => {
    const map = new Map<string, OutboundForceCandidate[]>()
    for (const group of candidateGroups ?? []) {
      map.set(group.order_name, group.candidates)
    }
    return map
  }, [candidateGroups])

  const toggleSelect = (key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const toggleSelectAll = () => {
    const eligibleKeys = eligibleItems.map((item) => buildForceSelectionKey(item.name, item.sku))
    const allSelected =
      eligibleKeys.length > 0 && eligibleKeys.every((key) => selectedKeys.has(key))
    setSelectedKeys(allSelected ? new Set() : new Set(eligibleKeys))
  }

  const assignTarget = (key: string, lineItemId: number | undefined) => {
    setTargetByKey((prev) => {
      const next = { ...prev }
      if (lineItemId === undefined) delete next[key]
      else next[key] = lineItemId
      return next
    })
  }

  // REQ-FORCE-022/023: only rows that are simultaneously eligible, selected
  // and target-assigned are ever included in the force-execute payload.
  const forceExecutableRows = useMemo<OutboundForceRowInput[]>(() => {
    const rows: OutboundForceRowInput[] = []
    for (const item of eligibleItems) {
      const key = buildForceSelectionKey(item.name, item.sku)
      if (!selectedKeys.has(key)) continue
      const lineItemId = targetByKey[key]
      if (lineItemId === undefined) continue
      rows.push({ name: item.name, sku: item.sku, total: item.total, line_item_id: lineItemId })
    }
    return rows
  }, [eligibleItems, selectedKeys, targetByKey])

  const forceMutation = useProcessOutboundForce()

  const handleForceExecute = () => {
    if (forceExecutableRows.length === 0) return
    forceMutation.mutate(forceExecutableRows, {
      onSuccess: (forceResult) => {
        setResult((prev) =>
          prev ? mergeForceOutboundResult(prev, forceExecutableRows, forceResult) : prev
        )
      },
    })
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">출고 처리</h1>
        <p className="text-sm text-muted-foreground">
          주문번호 / SKU / 수량을 직접 붙여넣거나 Excel 파일을 올려 출고 수량을 반영합니다.
        </p>
      </div>

      {/* REQ-OUTBOUND-016: manual entry and Excel upload are both available
          on the same screen — neither is behind a tab or a mode switch. */}
      <div className="space-y-2">
        <label htmlFor="outbound-rows" className="text-sm font-medium">
          수동 입력
        </label>
        <textarea
          id="outbound-rows"
          aria-label="출고 처리 행 입력"
          value={rawInput}
          onChange={(e) => setRawInput(e.target.value)}
          rows={8}
          placeholder={'주문번호\tSKU\t수량 (한 줄에 한 건, 탭 또는 쉼표 구분)\n#37349\tISBN001\t4'}
          className="w-full border rounded px-3 py-2 text-sm font-mono whitespace-pre"
        />
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={handleSubmit} disabled={isBusy}>
            출고 처리 실행
          </Button>

          <div className="ml-auto flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={isBusy}
            >
              Excel 업로드
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              aria-label="Excel 파일 선택"
              className="hidden"
              onChange={handleUploadChange}
            />
          </div>
        </div>
      </div>

      {/* REQ-OUTBOUND-017: all three categories render together, each with its
          own count, so an empty category is visibly empty rather than absent. */}
      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">처리 결과</h2>
            {/* REQ-OUTBOUND-018 */}
            <Button size="sm" variant="outline" onClick={handleReset}>
              다시 처리하기
            </Button>
          </div>

          <ResultSection
            testId="outbound-matched"
            title="성공"
            count={result.matched_count}
            toneClassName="border-green-300 bg-green-50"
            columns={['주문번호', 'SKU', '출고 수량', '누적/주문 수량', '상태']}
            rows={result.matched.map((item) => ({
              key: `${item.line_item_id}`,
              cells: [
                item.name,
                item.sku,
                String(item.total),
                `${item.shipped_quantity} / ${item.quantity ?? 0}`,
                item.logistics_status,
              ],
            }))}
          />

          {/* SPEC-ORDER-016: unmatched rows whose failure reason is
              line_item_not_found and whose quantity is positive can be
              force-outbounded against an operator-designated target
              (REQ-FORCE-001/019~021). */}
          <UnmatchedForceSection
            items={result.unmatched}
            reasonLabels={UNMATCHED_REASON_LABELS}
            candidatesByOrder={candidatesByOrder}
            selectedKeys={selectedKeys}
            targetByKey={targetByKey}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            onAssignTarget={assignTarget}
          />
          {/* REQ-FORCE-022/023: enabled only once at least one row is
              simultaneously eligible, selected and target-assigned; the
              payload carries exactly those rows (REQ-FORCE-015). */}
          <div className="flex justify-end">
            <Button
              size="sm"
              onClick={handleForceExecute}
              disabled={forceExecutableRows.length === 0 || forceMutation.isPending}
            >
              강제 출고 처리 실행
            </Button>
          </div>

          <ResultSection
            testId="outbound-quantity-exceeded"
            title="수량초과"
            count={result.quantity_exceeded_count}
            toneClassName="border-red-300 bg-red-50"
            columns={['주문번호', 'SKU', '요청 수량', '누적/주문 수량']}
            rows={result.quantity_exceeded.map((item) => ({
              key: `${item.line_item_id}`,
              cells: [
                item.name,
                item.sku,
                String(item.total),
                `${item.shipped_quantity} / ${item.quantity ?? 0}`,
              ],
            }))}
          />
        </div>
      )}
    </div>
  )
}

interface ResultRow {
  key: string
  cells: string[]
}

function ResultSection({
  testId,
  title,
  count,
  toneClassName,
  columns,
  rows,
}: {
  testId: string
  title: string
  count: number
  toneClassName: string
  columns: string[]
  rows: ResultRow[]
}) {
  return (
    <section
      data-testid={testId}
      aria-label={title}
      className={`rounded border ${toneClassName} p-3 space-y-2`}
    >
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        <span className="text-sm text-muted-foreground">{`${count}건`}</span>
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">해당 항목이 없습니다.</p>
      ) : (
        <div className="overflow-x-auto rounded border bg-background">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-muted/50">
                {columns.map((column) => (
                  <th key={column} className="py-2 px-3 text-left font-medium">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key} className="border-b last:border-0">
                  {row.cells.map((cell, index) => (
                    <td key={columns[index]} className="py-2 px-3 font-mono text-xs">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
