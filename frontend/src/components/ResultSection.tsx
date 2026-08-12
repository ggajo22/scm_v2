// REQ-OUTBOUND-017 / REQ-LOGI-017: shared titled, colour-toned result table
// used by any upload-processing screen that reports a per-row breakdown
// (matched / unmatched / quantity-exceeded, etc.). Originally a private
// component of OutboundPage/index.tsx (SPEC-ORDER-015); extracted so
// LogisticsStatusTab's warehouse-receipt upload card (REQ-LOGI-017) can
// reuse it without duplicating the table markup. Pure move — no behavior
// change from the OutboundPage version.
export interface ResultRow {
  key: string
  cells: string[]
}

export function ResultSection({
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
