import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { useProcessOutboundManual, useUploadOutbound } from '@/hooks/useOutboundQueries'
import type { OutboundProcessResponse, OutboundUnmatchedReason } from '@/services/outboundApi'
import { parseManualRows } from './parseManualRows'

// REQ-OUTBOUND-017: each backend `reason` code gets its own Korean label so a
// failed row tells the operator *why* it failed, not just that it did.
// Record (not Partial) so adding a reason code to the union without a label
// here is a compile error rather than a raw snake_case string in the UI.
const UNMATCHED_REASON_LABELS: Record<OutboundUnmatchedReason, string> = {
  order_not_found: '주문 없음',
  line_item_not_found: 'SKU 불일치',
  multiple_line_items: '동일 SKU 복수 품목',
  invalid_total: '수량 오류',
  invalid_row: '행 형식 오류',
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

          <ResultSection
            testId="outbound-unmatched"
            title="매칭 실패"
            count={result.unmatched_count}
            toneClassName="border-amber-300 bg-amber-50"
            columns={['주문번호', 'SKU', '요청 수량', '사유']}
            rows={result.unmatched.map((item, index) => ({
              key: `${item.name}-${item.sku}-${index}`,
              cells: [
                item.name,
                item.sku,
                String(item.total),
                UNMATCHED_REASON_LABELS[item.reason] ?? item.reason,
              ],
            }))}
          />

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
